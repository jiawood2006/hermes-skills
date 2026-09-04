#!/usr/bin/env python3
"""
Video-to-Text — 视频内容提取器（端到端闭环版）
==============================================
抖音/B站链接 或 本地视频 → 元数据 + 自动下载 + 语音转写 + 内容分析，一条命令跑完。

用法:
  python3 vtt.py "https://v.douyin.com/xxx/"            # 抖音：元数据+下载+转写（默认全自动）
  python3 vtt.py "https://v.douyin.com/xxx/" --all      # 再叠加 LLM 摘要+爆款拆解
  python3 vtt.py "https://v.douyin.com/xxx/" --meta-only  # 只要元数据
  python3 vtt.py 本地视频.mp4                            # 本地视频转写
  python3 vtt.py 本地视频.mp4 --summary                 # 本地视频转写+摘要

输出:
  <标题>_transcript.md   — 结构化转写（YAML frontmatter + 元数据 + 时间戳分节正文）
  <标题>_transcript.txt  — 纯文本转写（--format txt）
  元数据/分析摘要打印到终端

引擎:
  默认 faster-whisper 本地转写（免费、隐私不出本机）
  --engine sensevoice 走硅基流动 SenseVoice 在线 API（中文口语/带噪更准，需 SILICONFLOW_API_KEY，失败自动回退本地）

依赖:
  avconvert (macOS自带) 或 ffmpeg    提取音频
  faster-whisper:  pip install faster-whisper
  抖音链接需 playwright chromium（douyin_extract 内部使用）
"""
import sys, os, re, subprocess, json, argparse, tempfile, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


# ─────────────────────────── 抖音：元数据+下载 ───────────────────────────
def fetch_douyin_meta(url: str, want_download: bool):
    """抖音链接 → 元数据 + 可选下载。返回 (meta_dict, video_path or None)"""
    import douyin_extract
    r = douyin_extract.fetch_douyin(url, download=want_download, out_dir=tempfile.gettempdir())
    if not r.get("ok"):
        return None, None, r.get("error", "解析失败")
    meta = r["meta"]
    # 下载失败但拿到了 meta → 仍可提示
    if want_download and not r.get("video_path"):
        return meta, None, "视频下载失败（可手动保存后转写本地文件）"
    return meta, r.get("video_path"), None


# ─────────────────────────── B站：元数据 ───────────────────────────
def extract_bilibili(url: str) -> dict:
    """B站链接 → 元数据 dict（零依赖公开 API）"""
    import urllib.request
    m = re.search(r"(BV[0-9A-Za-z]+)", url)
    if not m:
        return {"error": "无法识别 B站视频 ID"}
    bvid = m.group(1)
    api = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        d = data.get("data", {})
        return {
            "platform": "bilibili", "url": url,
            "title": d.get("title", ""),
            "author": (d.get("owner") or {}).get("name", ""),
            "duration_s": d.get("duration", 0),
            "view": (d.get("stat") or {}).get("view", 0),
            "like": (d.get("stat") or {}).get("like", 0),
            "desc": (d.get("desc") or "")[:200],
        }
    except Exception as e:
        return {"error": f"B站解析失败: {e}"}


# ─────────────────────────── 转写引擎 ───────────────────────────
def extract_audio(video_path: str) -> str:
    """视频 → 音频文件（m4a）。返回音频路径"""
    base = os.path.splitext(os.path.basename(video_path))[0]
    audio = os.path.join(tempfile.gettempdir(), base + ".m4a")
    if os.path.exists(audio):
        os.remove(audio)
    if shutil.which("avconvert"):
        subprocess.run(["avconvert", "--source", video_path, "--preset", "PresetAppleM4A",
                        "--output", audio, "--replace"], check=True, timeout=600)
    elif shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "aac", audio],
                       check=True, timeout=600)
    else:
        raise SystemExit("❌ 需要 avconvert (macOS) 或 ffmpeg 提取音频")
    return audio


def transcribe_faster_whisper(audio: str) -> list:
    """faster-whisper 本地转写 → [(start_sec, text)]"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("❌ 需要 faster-whisper: pip install faster-whisper")
    print("⏳ 本地转写（faster-whisper，首次会下载模型）...", file=sys.stderr)
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, language="zh", beam_size=3, vad_filter=True)
    return [(float(s.start), s.text.strip()) for s in segments if s.text.strip()]


def transcribe_sensevoice(audio: str) -> list:
    """硅基流动 SenseVoice 在线转写（中文口语更准）。失败抛异常 → 调用方回退本地。"""
    import urllib.request
    import io
    key = os.environ.get("SILICONFLOW_API_KEY", "")
    if not key:
        raise RuntimeError("未配置 SILICONFLOW_API_KEY")
    # OpenAI 兼容 /v1/audio/transcriptions，multipart 上传
    boundary = "----vtt" + os.urandom(8).hex()
    with open(audio, "rb") as f:
        audio_bytes = f.read()
    def field(name, value):
        return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n").encode()
    body = b""
    body += field("model", "FunAudioLLM/SenseVoiceSmall")
    body += field("language", "zh")
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
             f"filename=\"audio.m4a\"\r\nContent-Type: audio/mp4\r\n\r\n").encode() + audio_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "https://api.siliconflow.cn/v1/audio/transcriptions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = (data.get("text") or "").strip()
    if not text:
        raise RuntimeError("SenseVoice 返回空")
    # SenseVoice 返回无时间戳 → 整体当一段
    return [(0, text)]


def transcribe(video_path: str, engine: str = "faster-whisper") -> list:
    """视频 → [(start_sec, text)]。engine: faster-whisper | sensevoice"""
    audio = extract_audio(video_path)
    if engine == "sensevoice":
        try:
            return transcribe_sensevoice(audio)
        except Exception as e:
            print(f"⚠️ SenseVoice 失败（{e}）→ 回退 faster-whisper 本地转写", file=sys.stderr)
    return transcribe_faster_whisper(audio)


def fmt_ts(sec: float) -> str:
    return f"[{int(sec)//60:02d}:{int(sec)%60:02d}]"


# ─────────────────────────── 输出 ───────────────────────────
def write_output(meta: dict, segments: list, out_dir: str, fmt: str = "md"):
    """meta: {platform,url,title,author,...}; segments: [(sec,text)] → 写文件"""
    if not meta.get("title"):
        meta["title"] = meta.get("_file_stem", "video")
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", str(meta["title"]))[:60] or "video"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, safe + "_transcript")

    body_lines = []
    # 相同时间戳段合并（SenseVoice 单段）
    for sec, text in segments:
        body_lines.append(f"{fmt_ts(sec)} {text}")

    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    meta["date"] = ts

    if fmt == "txt":
        path = base + ".txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(body_lines))
    else:
        path = base + ".md"
        fm = []
        for k in ["platform", "url", "title", "author", "duration_s", "digg", "view", "like", "share", "date", "tags"]:
            if k in meta and meta[k] not in (None, "", 0):
                v = meta[k]
                if isinstance(v, (list,)):
                    v = "[" + ", ".join(f'"{x}"' for x in v) + "]"
                fm.append(f"{k}: {v}")
        md = ["---"] + fm + ["---", "", f"# {meta['title']}", "",
                             "| 字段 | 值 |", "|:---|:---|"] + \
             [f"| {k} | {v} |" for k, v in meta.items()
              if k not in ("title", "platform", "url", "date", "tags", "_file_stem") and v not in (None, "", 0)] + \
             ["", "## 转写全文", ""] + body_lines
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
    print(f"✅ 转写已保存: {path}（{len(segments)} 段 / {sum(len(s) for _, s in segments)} 字）", file=sys.stderr)
    return path


def run_analysis(transcript_path: str, mode: str):
    """调用 analyze.py 生成内容情报"""
    script = os.path.join(HERE, "analyze.py")
    flag = "--summary" if mode == "summary" else "--analyze" if mode == "analyze" else "--all"
    try:
        r = subprocess.run([sys.executable, script, transcript_path, flag],
                           capture_output=True, text=True, timeout=300)
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("⏳ 分析超时（LLM 调用慢）", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Video-to-Text — 视频内容提取器（端到端闭环）")
    ap.add_argument("input", help="抖音/B站链接 或 本地视频文件路径")
    ap.add_argument("--meta-only", action="store_true", help="只要元数据，不下载不转写")
    ap.add_argument("--no-transcribe", action="store_true", help="下载视频但跳过转写（只存文件）")
    ap.add_argument("--engine", choices=["faster-whisper", "sensevoice"], default="faster-whisper",
                    help="转写引擎（默认本地 faster-whisper）")
    ap.add_argument("--summary", action="store_true", help="转写后生成内容摘要（需 LLM key）")
    ap.add_argument("--analyze", action="store_true", help="转写后爆款结构拆解（需 LLM key）")
    ap.add_argument("--format", choices=["md", "txt"], default="md", help="输出格式")
    ap.add_argument("--out-dir", default="", help="输出目录（默认当前目录）")
    args = ap.parse_args()

    out_dir = args.out_dir or os.getcwd()
    analysis_mode = "all" if (args.summary and args.analyze) else ("summary" if args.summary else ("analyze" if args.analyze else None))

    # ── 链接模式 ──
    if is_url(args.input):
        # B站
        if "bilibili.com" in args.input or "b23.tv" in args.input:
            meta = extract_bilibili(args.input)
            if meta.get("error"):
                raise SystemExit(f"❌ {meta['error']}")
            print("🎬 B站视频元数据")
            print("=" * 50)
            for k, v in meta.items():
                if v not in (None, ""):
                    print(f"  {k}: {v}")
            print("\n⚠️ B站语音转写：请先下载视频文件，再对本地文件运行：python3 vtt.py 视频.mp4")
            return

        # 抖音（默认闭环：元数据+下载+转写）
        print("📥 抖音视频链接，解析元数据...", file=sys.stderr)
        meta, video_path, warn = fetch_douyin_meta(args.input, want_download=not args.meta_only)
        if meta is None:
            raise SystemExit(f"❌ {warn or '抖音解析失败'}")
        print("=" * 50)
        print("🎬 视频元数据")
        print("=" * 50)
        for k, v in meta.items():
            if v not in (None, "", 0):
                print(f"  {k}: {v}")
        if warn:
            print(f"  ⚠️ {warn}")
        if args.meta_only or not video_path:
            return
        print(f"\n📼 已下载: {video_path}", file=sys.stderr)
        if args.no_transcribe:
            print(f"✅ 视频已保存（跳过转写）: {video_path}", file=sys.stderr)
            return
        segments = transcribe(video_path, engine=args.engine)
        transcript_path = write_output(meta, segments, out_dir, args.format)
        if analysis_mode:
            print(f"\n🔎 内容情报分析（{analysis_mode}）...", file=sys.stderr)
            run_analysis(transcript_path, analysis_mode)
        return

    # ── 本地视频模式 ──
    if not os.path.exists(args.input):
        raise SystemExit(f"❌ 文件不存在: {args.input}")
    print("🎬 本地视频，提取语音转文字...", file=sys.stderr)
    segments = transcribe(args.input, engine=args.engine)
    meta = {"platform": "local", "title": os.path.splitext(os.path.basename(args.input))[0],
            "author": "", "_file_stem": os.path.splitext(os.path.basename(args.input))[0]}
    transcript_path = write_output(meta, segments, out_dir, args.format)
    if analysis_mode:
        print(f"\n🔎 内容情报分析（{analysis_mode}）...", file=sys.stderr)
        run_analysis(transcript_path, analysis_mode)


if __name__ == "__main__":
    main()
