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


def _pack_words(words) -> list:
    """词级时间戳 → 字幕条。按标点/字数/时长打包，避免一条字幕横跨十几秒。

    words: [(start, end, text)] → [(start, end, text)]
    """
    import re as _re
    max_chars = int(os.environ.get("VTT_MAX_CHARS", "18"))
    max_dur = float(os.environ.get("VTT_MAX_DUR", "7"))
    cues, cur = [], []

    def flush():
        if cur:
            txt = "".join(w[2] for w in cur).strip()
            if txt:
                cues.append((cur[0][0], cur[-1][1], txt))
            cur.clear()

    for w in words:
        cur.append(w)
        txt = "".join(x[2] for x in cur).strip()
        dur = cur[-1][1] - cur[0][0]
        ends = bool(_re.search(r"[。！？!?；;]$", txt))
        if ends or len(txt) >= max_chars or dur >= max_dur:
            flush()
    flush()
    return cues


def _split_by_chars(seg) -> list:
    """无词级时间戳时的兜底：按字符数等比切分（时间按占比分配）。"""
    s, e, t = seg
    max_chars = int(os.environ.get("VTT_MAX_CHARS", "18"))
    if len(t) <= max_chars:
        return [seg]
    import re as _re
    parts = [p for p in _re.split(r"(?<=[。！？!?；;，,])", t) if p.strip()]
    # 再把超长片段按字数切块
    chunks = []
    for p in parts:
        while len(p) > max_chars:
            chunks.append(p[:max_chars]); p = p[max_chars:]
        if p.strip():
            chunks.append(p)
    if not chunks:
        return [seg]
    total = sum(len(c) for c in chunks) or 1
    span = e - s
    out, acc = [], 0
    for c in chunks:
        cs = s + span * acc / total
        acc += len(c)
        ce = s + span * acc / total
        out.append((cs, ce, c.strip()))
    return out


def transcribe_faster_whisper(audio: str, lang: str = "zh") -> list:
    """faster-whisper 本地转写 → [(start_sec, end_sec, text)]

    - 中文默认注入 initial_prompt 引导输出**简体中文 + 标点**
      （否则 whisper 常输出繁体、且几乎不加标点——实测踩过的坑）
    - 开启词级时间戳并按句打包，字幕不会一条横跨十几秒
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("❌ 需要 faster-whisper: pip install faster-whisper")
    print("⏳ 本地转写（faster-whisper，首次会下载模型）...", file=sys.stderr)
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8")
    kwargs = dict(language=lang, beam_size=3, vad_filter=True, word_timestamps=True)
    if lang.startswith("zh"):
        prompt = os.environ.get("WHISPER_INITIAL_PROMPT", "以下是普通话的句子，请输出简体中文并加标点。")
        if prompt:
            kwargs["initial_prompt"] = prompt
    try:
        segments, info = model.transcribe(audio, **kwargs)
    except TypeError:
        kwargs.pop("word_timestamps", None)          # 老版本不支持则退回
        segments, info = model.transcribe(audio, **kwargs)

    out = []
    for s in segments:
        txt = (s.text or "").strip()
        if not txt:
            continue
        words = getattr(s, "words", None)
        if words:
            packed = _pack_words([(float(w.start), float(w.end), w.word) for w in words])
            if packed:
                out.extend(packed)
                continue
        out.extend(_split_by_chars((float(s.start), float(s.end), txt)))
    return [c for c in out if c[2]]


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
    # SenseVoice 返回无时间戳 → 整体当一段；按中文语速 ~4.5 字/秒 估时长
    return [(0.0, max(3.0, len(text) / 4.5), text)]


def transcribe(video_path: str, engine: str = "faster-whisper", lang: str = "zh") -> list:
    """视频 → [(start_sec, end_sec, text)]。engine: faster-whisper | sensevoice"""
    audio = extract_audio(video_path)
    if engine == "sensevoice":
        try:
            return transcribe_sensevoice(audio)
        except Exception as e:
            print(f"⚠️ SenseVoice 失败（{e}）→ 回退 faster-whisper 本地转写", file=sys.stderr)
    return transcribe_faster_whisper(audio, lang=lang)


def fmt_ts(sec: float) -> str:
    return f"[{int(sec)//60:02d}:{int(sec)%60:02d}]"


def _norm_segments(segments: list) -> list:
    """兼容 [(sec,text)] 与 [(start,end,text)] 两种入参 → [(start,end,text)]。"""
    out = []
    for seg in segments:
        if len(seg) == 3:
            s, e, t = seg
        else:
            s, t = seg
            e = None
        s = float(s)
        e = float(e) if e is not None else s + max(1.5, len(str(t)) / 4.5)
        if e <= s:
            e = s + 1.5
        out.append((s, e, str(t)))
    return out


def _sub_ts(sec: float, sep: str = ",") -> str:
    """秒 → 字幕时间戳 HH:MM:SS,mmm（VTT 用 '.'）。"""
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        ms, s = 0, s + 1
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(segments: list) -> str:
    """→ SRT 字幕文本（可导入剪映/Premiere/YouTube）。"""
    lines = []
    for i, (s, e, t) in enumerate(_norm_segments(segments), 1):
        lines += [str(i), f"{_sub_ts(s)} --> {_sub_ts(e)}", t, ""]
    return "\n".join(lines)


def to_vtt(segments: list) -> str:
    """→ WebVTT 字幕文本（网页 <track> / 播放器通用）。"""
    lines = ["WEBVTT", ""]
    for s, e, t in _norm_segments(segments):
        lines += [f"{_sub_ts(s, '.')} --> {_sub_ts(e, '.')}", t, ""]
    return "\n".join(lines)


# ─────────────────────────── 输出 ───────────────────────────
def write_output(meta: dict, segments: list, out_dir: str, fmt: str = "md", subtitles=None):
    """meta: {platform,url,title,author,...}; segments: [(start,end,text)]

    fmt: md | txt | srt | vtt（srt/vtt 只写字幕文件）
    subtitles: 额外字幕格式集合，如 {"srt"} —— 在 md/txt 之外一并输出
    """
    segments = _norm_segments(segments)
    if not meta.get("title"):
        meta["title"] = meta.get("_file_stem", "video")
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", str(meta["title"]))[:60] or "video"
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, safe + "_transcript")

    body_lines = [f"{fmt_ts(s)} {t}" for s, _e, t in segments]

    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    meta["date"] = ts

    # ── 纯字幕输出 ──
    if fmt in ("srt", "vtt"):
        path = base + "." + fmt
        with open(path, "w", encoding="utf-8") as f:
            f.write(to_srt(segments) if fmt == "srt" else to_vtt(segments))
        print(f"✅ 字幕已保存: {path}（{len(segments)} 条）", file=sys.stderr)
        return path

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

    # ── 附加字幕文件 ──
    extra = []
    for want in (subtitles or []):
        sp = base + "." + want
        with open(sp, "w", encoding="utf-8") as f:
            f.write(to_srt(segments) if want == "srt" else to_vtt(segments))
        extra.append(sp)

    print(f"✅ 转写已保存: {path}（{len(segments)} 段 / {sum(len(t) for _, _, t in segments)} 字）", file=sys.stderr)
    for sp in extra:
        print(f"✅ 字幕已保存: {sp}", file=sys.stderr)
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
    ap.add_argument("--asr-lang", default="zh",
                    help="转写语言代码（缺省 zh；en/ja/ko 等）")
    ap.add_argument("--summary", action="store_true", help="转写后生成内容摘要（需 LLM key）")
    ap.add_argument("--analyze", action="store_true", help="转写后爆款结构拆解（需 LLM key）")
    ap.add_argument("--format", choices=["md", "txt", "srt", "vtt"], default="md",
                    help="输出格式（md/txt=文字稿；srt/vtt=字幕文件）")
    ap.add_argument("--subtitles", default="",
                    help="额外输出字幕文件，如 srt 或 srt,vtt（与 md/txt 文字稿一并生成）")
    ap.add_argument("--out-dir", default="", help="输出目录（默认当前目录）")
    args = ap.parse_args()

    out_dir = args.out_dir or os.getcwd()
    subs = [x.strip().lower() for x in args.subtitles.split(",") if x.strip() in ("srt", "vtt")]
    analysis_mode = "all" if (args.summary and args.analyze) else ("summary" if args.summary else ("analyze" if args.analyze else None))
    if args.format in ("srt", "vtt"):
        analysis_mode = None      # 字幕模式下不做文字分析

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
        segments = transcribe(video_path, engine=args.engine, lang=args.asr_lang)
        transcript_path = write_output(meta, segments, out_dir, args.format, subtitles=subs)
        if analysis_mode:
            print(f"\n🔎 内容情报分析（{analysis_mode}）...", file=sys.stderr)
            run_analysis(transcript_path, analysis_mode)
        return

    # ── 本地视频模式 ──
    if not os.path.exists(args.input):
        raise SystemExit(f"❌ 文件不存在: {args.input}")
    print("🎬 本地视频，提取语音转文字...", file=sys.stderr)
    segments = transcribe(args.input, engine=args.engine, lang=args.asr_lang)
    meta = {"platform": "local", "title": os.path.splitext(os.path.basename(args.input))[0],
            "author": "", "_file_stem": os.path.splitext(os.path.basename(args.input))[0]}
    transcript_path = write_output(meta, segments, out_dir, args.format, subtitles=subs)
    if analysis_mode:
        print(f"\n🔎 内容情报分析（{analysis_mode}）...", file=sys.stderr)
        run_analysis(transcript_path, analysis_mode)


if __name__ == "__main__":
    main()
