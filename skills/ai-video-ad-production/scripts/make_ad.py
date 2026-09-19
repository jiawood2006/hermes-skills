#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_ad.py —— 电商带货片「一条命令出片」总入口（原 24 个零件脚本的整机）

一条龙六步，每步都能单独跑（失败不用从头来，也不重复烧钱）：

  plan      由 产品档案 + 分镜脚本 生成每段完整 prompt（不花钱，先看先审）
  submit    提交百炼 wan2.7-r2v → 落 tasks json
  fetch     轮询 + 下载分段 mp4（带存在性/大小校验，失败明确报错）
  verify    ffprobe + 抽帧核验图（9格全景 + 产品2倍特写），供人眼/vision 读
  assemble  旁白(edge-tts) + 字幕/花字/参数条/合规 → 30s 成片 → 再切 15s 版
  deliver   按配置拷到 ~/Desktop/电商素材/<产品>/视频/

用法
----
  python3 make_ad.py <project.json> --steps plan
  python3 make_ad.py <project.json> --steps all
  python3 make_ad.py <project.json> --steps assemble,deliver        # 复用已下载的分段
  python3 make_ad.py <project.json> --steps fetch,verify --seg 3    # 只处理某几段
  python3 make_ad.py <project.json> --steps plan --runid v24 --res 720P

设计约束（血泪踩出来的，别改）
- 生成一律 720P：同一 prompt 跑 1080P 会把产品画坏（长径比 1.25 矮胖罐 + 金网消失）
- 产品锁措辞必须走 templates/product_lock_head.txt（调过很多轮的措辞，不要手写）
- 旁白落点 = 字幕 start（build_vo30.py 按它排 TTS）→ 天生对齐；不要凭猜改时间
- 每步都查退出码 + 产物存在/大小；不达标就报 FAIL 并说明原因，绝不静默继续
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TEMPLATES = os.path.join(SKILL, "templates")

FF = os.environ.get("FFMPEG", os.path.expanduser("~/video-tools/bin/ffmpeg"))
FFPROBE = os.environ.get("FFPROBE", os.path.expanduser("~/video-tools/bin/ffprobe"))
EDGE_TTS = os.environ.get("EDGE_TTS", os.path.expanduser("~/.hermes/hermes-agent/venv/bin/edge-tts"))
DASHSCOPE_KEY_FILE = os.environ.get("DASHSCOPE_KEY_FILE", os.path.expanduser("~/.hermes/.dashscope_key"))
PROFILES = os.environ.get("MATERIAL_PROFILES", os.path.expanduser(
    "~/.hermes/skills/utilities/ecommerce-material-studio/references/product_profiles.json"))
API_SUBMIT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
API_TASK = "https://dashscope.aliyuncs.com/api/v1/tasks/"
DH_DIR = "/opt/yunvela-site/dh"          # 公网参考图目录（yunvela.com/dh/）
DH_BASE = "https://yunvela.com/dh/"
SSH_HOST = os.environ.get("DH_SSH_HOST", "yunvela")

FAILED = []


def log(msg):
    print(msg, flush=True)


def fail(step, why):
    FAILED.append((step, why))
    log(f"  ❌ {step} FAIL: {why}")


def ok(step, msg=""):
    log(f"  ✅ {step} {msg}")


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    """返回 (时长秒, 宽, 高, 字节)；文件不存在返回 None"""
    if not path or not os.path.exists(path):
        return None
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration,size",
             "-show_entries", "stream=width,height", "-of", "json", path])
    try:
        d = json.loads(r.stdout)
        st = next((s for s in d.get("streams", []) if s.get("width")), {})
        return (float(d["format"]["duration"]), st.get("width"), st.get("height"),
                int(d["format"]["size"]))
    except Exception:
        return None


def key():
    with open(os.path.expanduser(DASHSCOPE_KEY_FILE)) as f:
        return f.read().strip()


# ---------------------------------------------------------------- 配置装载
def load_project(path):
    proj = json.load(open(path, encoding="utf-8"))
    pkey = proj.get("product")
    prof = None
    if pkey and os.path.exists(os.path.expanduser(PROFILES)):
        all_p = json.load(open(os.path.expanduser(PROFILES), encoding="utf-8")).get("products", {})
        prof = all_p.get(pkey)
        if prof is None:
            log(f"  ⚠️ 产品档案里没有 '{pkey}'（可用：{list(all_p)}），只用项目内定义")
    proj["_profile"] = prof or {}
    proj["_profile_key"] = pkey
    return proj


def resolve_refs(proj, workdir):
    """把 refs 配成真正可访问的 URL，并按顺序（图1..图N）返回；本地图自动推公网。"""
    prof = proj["_profile"]
    assets = prof.get("assets", {})
    urls, notes = [], []
    for r in proj.get("refs", []):
        if "url" in r:
            urls.append(r["url"]); notes.append(r.get("note", r["url"]))
            continue
        if "local" in r:
            src = os.path.expanduser(r["local"])
            if not os.path.exists(src):
                fail("refs", f"本地参考图不存在 {src}")
                continue
            name = r.get("as") or os.path.basename(src)
            dst = f"{SSH_HOST}:{DH_DIR}/{name}"
            cp = run(["scp", "-q", src, dst])
            if cp.returncode:
                fail("refs", f"scp 失败 {src} -> {dst}: {cp.stderr[-200:]}")
                continue
            urls.append(DH_BASE + name); notes.append(r.get("note", name) + "(本地已推)")
            continue
        k = r.get("key")
        u = assets.get(k) or (k if str(k).startswith("http") else None)
        if not u:
            fail("refs", f"档案 assets 里没有参考图键 '{k}'")
            continue
        urls.append(u); notes.append(r.get("note", k))
    return urls, notes


def load_head(proj):
    """产品锁模板 + 档案字段 → HEAD 段。模板里的 {{x}} 用档案字段填。"""
    tpl_path = os.path.join(TEMPLATES, proj.get("head_template", "product_lock_head.txt"))
    if not os.path.exists(tpl_path):
        sys.exit(f"没有产品锁模板: {tpl_path}")
    tpl = open(tpl_path, encoding="utf-8").read()
    tpl = "\n".join(l for l in tpl.splitlines() if not l.strip().startswith("#")).strip()
    fields = {}
    fields.update(proj.get("_profile", {}))
    fields.update(proj.get("_profile", {}).get("video_lock", {}))
    fields.update(proj.get("prompt_fields", {}))          # 项目可覆盖/补字段
    miss = []
    out = []
    i = 0
    while i < len(tpl):
        j = tpl.find("{{", i)
        if j < 0:
            out.append(tpl[i:]); break
        out.append(tpl[i:j])
        k2 = tpl.find("}}", j)
        name = tpl[j + 2:k2].strip()
        v = fields.get(name)
        if v is None:
            miss.append(name); v = ""
        out.append(str(v))
        i = k2 + 2
    if miss:
        fail("plan", f"产品档案缺字段: {sorted(set(miss))}（在 product_profiles.json 的 video_lock 里补）")
    return "".join(out).strip()


def build_prompts(proj, only_segs):
    head = load_head(proj)
    segs = proj.get("segments", {})
    out = {}
    for s in only_segs:
        if s not in segs:
            fail("plan", f"项目配置里没有分镜 '{s}'")
            continue
        out[s] = head + "\n" + segs[s].strip()
    return out


def parse_segs(proj, argv_seg):
    if argv_seg:
        vals = [x.strip() for x in argv_seg.split(",") if x.strip()]
    else:
        vals = list(proj.get("segments", {}).keys()) or list(proj.get("assembly", {}).get("order_plain", []))
    out = []
    for v in vals:
        out.append("seg" + v if v.isdigit() else v)
    return out


# ---------------------------------------------------------------- 1. plan
def step_plan(proj, workdir, runid, res, prompts):
    dst = os.path.join(workdir, f"prompts_{runid}.json")
    json.dump({"runid": runid, "resolution": res, "product": proj.get("_profile_key"),
               "prompts": prompts}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if FAILED:
        return dst
    for s, p in prompts.items():
        log(f"  {s}: {len(p)} 字 (产品锁 {len(p) - len(proj['segments'][s])} 字 + 分镜)")
    ok("plan", f"{len(prompts)} 段 → {dst}")
    return dst


# ---------------------------------------------------------------- 2. submit
def step_submit(proj, workdir, runid, res, prompts, refs):
    if not refs:
        fail("submit", "没有可用参考图"); return None
    if not prompts:
        fail("submit", "没有 prompt"); return None
    K = key()
    H = {"Authorization": f"Bearer {K}", "Content-Type": "application/json",
         "X-DashScope-Async": "enable"}
    tasks = {}
    for tag, prompt in prompts.items():
        model = proj.get("model", "wan2.7-r2v")
        # 引擎差异（2026-09-18 横评定论）：wan3.0-video 参考图走 input.images（URL 列表），
        # 且产品保真最好（产品镜首选）；wan2.7-r2v 走 input.media(reference_image)，只留人物戏。
        if "3.0" in model:
            inp = {"images": refs, "prompt": prompt}
        else:
            inp = {"media": [{"type": "reference_image", "url": u} for u in refs], "prompt": prompt}
        params = {"resolution": res,
                  "duration": int(proj.get("duration", 10)),
                  "ratio": proj.get("ratio", "9:16"),
                  "prompt_extend": bool(proj.get("prompt_extend", False))}
        if "3.0" in model:
            params["watermark"] = False      # wan3.0 默认可能带水印，显式关掉
        payload = {"model": model,
                   "input": inp,
                   "parameters": params}
        done = False
        for attempt in range(6):
            try:
                req = urllib.request.Request(API_SUBMIT, data=json.dumps(payload).encode(), headers=H)
                d = json.load(urllib.request.urlopen(req, timeout=180))
                tasks[tag] = d["output"]["task_id"]
                log(f"  {runid}_{tag} -> {d['output']['task_id']}  refs={len(refs)} res={res} dur={payload['parameters']['duration']}")
                done = True
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:400]
                log(f"  retry {tag}.{attempt} HTTP {e.code}: {body}")
                time.sleep(20)
            except Exception as e:
                log(f"  retry {tag}.{attempt}: {str(e)[:160]}")
                time.sleep(20)
        if not done:
            fail("submit", f"{tag} 提交 6 次都失败（看上面 HTTP 报错原文）")
        time.sleep(4)
    if tasks:
        dst = os.path.join(workdir, f"tasks_{runid}.json")
        json.dump({"tasks": tasks, "res": res, "refs": refs}, open(dst, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        ok("submit", f"{len(tasks)} 个任务 → {dst}")
        return dst
    return None


# ---------------------------------------------------------------- 3. fetch
def step_fetch(proj, workdir, runid, timeout_s=2700):
    tf = os.path.join(workdir, f"tasks_{runid}.json")
    if not os.path.exists(tf):
        fail("fetch", f"没有 {tf}（先跑 submit）"); return {}
    tasks = json.load(open(tf, encoding="utf-8"))["tasks"]
    H = {"Authorization": f"Bearer {key()}"}
    pending = dict(tasks)
    done = {}
    t0 = time.time()
    while pending and time.time() - t0 < timeout_s:
        for tag, tid in list(pending.items()):
            try:
                req = urllib.request.Request(API_TASK + tid, headers=H)
                d = json.load(urllib.request.urlopen(req, timeout=60))
                st = d["output"]["task_status"]
                if st == "SUCCEEDED":
                    out = os.path.join(workdir, f"{runid}_{tag}.mp4")
                    urllib.request.urlretrieve(d["output"]["video_url"], out)
                    sz = os.path.getsize(out) if os.path.exists(out) else 0
                    if sz < 100_000:
                        fail("fetch", f"{tag} 下载只有 {sz}B，当失败处理")
                    else:
                        log(f"  DONE {tag} {sz}B -> {out}")
                        done[tag] = out
                    pending.pop(tag)
                elif st in ("FAILED", "CANCELED", "UNKNOWN"):
                    fail("fetch", f"{tag} 任务 {st}: {json.dumps(d['output'], ensure_ascii=False)[:400]}")
                    pending.pop(tag)
            except Exception as e:
                log(f"  poll err {tag}: {str(e)[:120]}")
        if pending:
            time.sleep(20)
    for tag in list(pending):
        fail("fetch", f"{tag} 超时未完成（{timeout_s}s）")
    if done and not FAILED:
        ok("fetch", f"{len(done)} 段已下载 " + ", ".join(os.path.basename(p) for p in done.values()))
    return done


# ---------------------------------------------------------------- 4. verify
def step_verify(proj, workdir, runid, segs, times=(0.25, 0.5, 0.75)):
    """① ffprobe ② 9格全景 ③ 产品2倍特写。只生成图 + 打客观数字，不下审美结论。"""
    paths = []
    for s in segs:
        p = os.path.join(workdir, f"{runid}_{s}.mp4")
        if not os.path.exists(p):
            fail("verify", f"缺 {p}"); continue
        pr = probe(p)
        if not pr:
            fail("verify", f"ffprobe 读不出 {p}"); continue
        log(f"  {s}: {pr[0]:.2f}s {pr[1]}x{pr[2]} {pr[3]/1e6:.1f}MB")
        paths.append((s, p, pr[0]))
    if not paths:
        return
    tiles = []
    for s, p, dur in paths:
        for f in times:
            t = round(dur * f, 2)
            img = os.path.join(workdir, f"{runid}_{s}_f{t}.jpg")
            r = run([FF, "-loglevel", "error", "-y", "-ss", str(t), "-i", p,
                     "-frames:v", "1", "-vf", "scale=360:-1", img])
            if r.returncode == 0 and os.path.exists(img):
                tiles.append(img)
    if len(tiles) >= 2:
        sheet = os.path.join(workdir, f"{runid}_all.jpg")
        n = min(len(tiles), 9)
        ins = []
        for p in tiles[:n]:
            ins += ["-i", p]
        cols = 3 if n % 3 == 0 else n
        rows = (n + cols - 1) // cols
        # ⚠️ 对"布局条目列表"截取 n 项，绝不能对 join 后的字符串做 [:n]（那是截字符，
        #    n=3 时会截成 "0_0" → ffmpeg 报 xstack Invalid argument / 写不出文件）
        items = [("0" if c == 0 else "+".join(f"w{j}" for j in range(c))) + "_" +
                 ("0" if r2 == 0 else "+".join(f"h{j}" for j in range(r2)))
                 for r2 in range(rows) for c in range(cols)]
        lay = "|".join(items[:n])
        r = run([FF, "-loglevel", "error", "-y"] + ins +
                ["-filter_complex", f"xstack=inputs={n}:layout={lay}", "-frames:v", "1", sheet])
        if r.returncode == 0:
            ok("verify", f"9格全景 → {sheet}")
        else:
            fail("verify", f"拼图失败 {r.stderr[-200:]}")
    zoom_pairs = proj.get("verify", {}).get("zoom", [])
    if zoom_pairs:
        zs = [f"{os.path.join(workdir, runid + '_' + s + '.mp4')}@{t}" for s, t in zoom_pairs]
        zout = os.path.join(workdir, f"{runid}_zoom.jpg")
        r = run([sys.executable, os.path.join(HERE, "product_fidelity_zoom.py"), zout] + zs)
        if r.returncode == 0:
            ok("verify", f"产品2倍特写 → {zout}")
        else:
            fail("verify", f"产品特写失败 {r.stderr[-200:]}")
    log("  判读基准: 产品占画面高 ≤1/6(特写 ≤1/4)；机身长≈机头直径1.9倍；"
        "底部端面=平圆面+电源键同心环+横Type-C；长侧面无接口")


# ---------------------------------------------------------------- 5. assemble
def render_overlays_and_assemble(proj, workdir, runid, seg_paths, cfg):
    cfg_path = os.path.join(workdir, "overlay_cfg.json")
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 1) 旁白（按字幕 start 排 TTS）
    vo = cfg.get("vo")
    if vo and cfg.get("vo_build", True):
        env = dict(os.environ, VO_WORKDIR=workdir, VO_DURATION=str(cfg.get("total", 30)),
                   FFMPEG=FF, EDGE_TTS=EDGE_TTS)
        r = subprocess.run([sys.executable, os.path.join(HERE, "build_vo30.py"),
                            cfg.get("vo_voice", "zh-CN-YunxiNeural"), cfg.get("vo_rate", "+5%"),
                            os.path.basename(vo)], capture_output=True, text=True, env=env)
        if r.returncode or not os.path.exists(vo):
            fail("assemble", f"旁白生成失败: {(r.stderr or r.stdout)[-300:]}")
            return False
        ok("assemble", f"旁白 → {vo} ({os.path.getsize(vo)}B)")
    # 2) 主片（拼接 + 字幕/花字/参数条/合规）
    # ⚠️ 必须把 AD_TMP 指到本工程目录：装配器默认把 overlay PNG 写到 /tmp/r2v，
    #    多产品并行时会互相覆盖（15s 版还要复用这些 PNG）
    r = subprocess.run([sys.executable, os.path.join(HERE, "assemble_r2v_overlays.py"), cfg_path],
                       capture_output=True, text=True, env=dict(os.environ, AD_TMP=workdir))
    if r.returncode or not os.path.exists(cfg["out"]):
        fail("assemble", f"主片装配失败: {(r.stderr or r.stdout)[-500:]}")
        return False
    pr = probe(cfg["out"])
    ok("assemble", f"主片 {os.path.basename(cfg['out'])} {pr[0]:.1f}s {pr[1]}x{pr[2]} {pr[3]/1e6:.1f}MB")
    # 3) 15s 版
    c15 = proj.get("assembly", {}).get("cut15")
    if c15:
        build_cut15(proj, workdir, runid, c15, cfg)
    return True


def build_cut15(proj, workdir, runid, c15, cfg30):
    """15s 版：按 c15.order 取段(可 trim) + 旁白切片 c15.vo_ranges + 复用已渲染的 overlay PNG。"""
    out = os.path.join(workdir, f"{runid}_15s.mp4")
    total = float(c15.get("total", 15))
    inputs = []
    for it in c15["order"]:
        p = os.path.expanduser(it["file"]) if it.get("file") else os.path.join(workdir, f"{runid}_{it['seg']}.mp4")
        if not os.path.exists(p):
            fail("cut15", f"缺 {p}"); return
        inputs += ["-i", p]
    nseg = len(inputs) // 2
    # 旁白切片
    if cfg30.get("vo") and c15.get("vo_ranges"):
        vor = c15["vo_ranges"]
        vo15 = os.path.join(workdir, f"{runid}_vo15.mp3")
        fc = ";".join(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[v{i}]" for i, (a, b) in enumerate(vor))
        fc += ";" + "".join(f"[v{i}]" for i in range(len(vor))) + f"concat=n={len(vor)}:v=0:a=1[aout]"
        r = run([FF, "-loglevel", "error", "-y", "-i", cfg30["vo"], "-filter_complex", fc,
                 "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "192k", vo15])
        if r.returncode:
            fail("cut15", f"旁白切片失败 {r.stderr[-250:]}")
            return
        inputs += ["-i", vo15]
    vo_idx = nseg if cfg30.get("vo") and c15.get("vo_ranges") else None
    ov = c15.get("overlays", [])
    ov_idx = len(inputs) // 2
    for o in ov:
        p = os.path.join(workdir, o["png"])
        if not os.path.exists(p):
            fail("cut15", f"缺 overlay {p}（主片装配会渲染出来，先跑 assemble）"); return
        inputs += ["-i", p]
    fc = []
    for i, it in enumerate(c15["order"]):
        trim = it.get("trim")
        pre = f"trim=0:{trim},setpts=PTS-STARTPTS," if trim else ""
        fc.append(f"[{i}:v]{pre}scale=1080:1920,setsar=1[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(nseg)) + f"concat=n={nseg}:v=1:a=0[vbase]")
    if vo_idx is not None:
        fc.append(f"[{vo_idx}:a]aresample=44100,apad=whole_dur={total + 0.3}[aout]")
    cur = "vbase"
    for k, o in enumerate(ov):
        fc.append(f"[{ov_idx + k}:v]format=rgba[o{k}]")
        fc.append(f"[{cur}][o{k}]overlay=0:0:enable='between(t,{o['start']},{o['end']})'[vx{k}]")
        cur = f"vx{k}"
    cmd = [FF, "-loglevel", "error", "-y"] + inputs + [
        "-filter_complex", ";".join(fc), "-map", f"[{cur}]"]
    cmd += ["-map", "[aout]"] if vo_idx is not None else ["-map", "0:a?"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(total), out]
    r = run(cmd)
    if r.returncode or not os.path.exists(out):
        fail("cut15", f"15s 装配失败 {r.stderr[-400:]}"); return
    pr = probe(out)
    ok("cut15", f"{os.path.basename(out)} {pr[0]:.1f}s {pr[1]}x{pr[2]} {pr[3]/1e6:.1f}MB")


def step_assemble(proj, workdir, runid, segs):
    asm = proj.get("assembly", {})
    order = asm.get("order", [{"seg": s} for s in segs])
    segs_cfg = []
    for it in order:
        # file = 直接复用已有片段（不按 runid 找），用于「新钩子 + 老素材」这类批量变体
        p = os.path.expanduser(it["file"]) if it.get("file") else os.path.join(workdir, f"{runid}_{it['seg']}.mp4")
        if not os.path.exists(p):
            fail("assemble", f"缺分段 {p}"); return None
        d = {"path": p}
        if it.get("trim"):
            d["trim"] = it["trim"]
        if it.get("label"):
            d["label"] = it["label"]
        segs_cfg.append(d)
    total = float(asm.get("total", 30.0))
    cfg = {"out": os.path.join(workdir, f"{runid}_{int(total)}s.mp4"),
           "total": total,
           "segments": segs_cfg,
           "subs": asm.get("subs", []),
           "chips": asm.get("chips", []),
           "spec": asm.get("spec"),
           "compliance": asm.get("compliance", "AI 生成内容 · 广告")}
    if asm.get("price") is not None:          # 默认不放价格（用户：价格经常变）
        cfg["price"] = asm["price"]
    vo = asm.get("vo")
    if vo:
        cfg["vo"] = os.path.join(workdir, vo.get("file", f"vo{int(cfg['total'])}.mp3"))
        cfg["vo_build"] = vo.get("build", True)
        cfg["vo_voice"] = vo.get("voice", "zh-CN-YunxiNeural")
        cfg["vo_rate"] = vo.get("rate", "+5%")
    if render_overlays_and_assemble(proj, workdir, runid, segs_cfg, cfg):
        return cfg
    return None


# ---------------------------------------------------------------- 6. deliver
def step_deliver(proj, workdir, runid):
    d = proj.get("deliver", {})
    dst_dir = os.path.expanduser(d.get("dir", "~/Desktop/电商素材/<产品>/视频"))
    if "<" in dst_dir:
        fail("deliver", f"deliver.dir 没配好: {dst_dir}"); return
    os.makedirs(dst_dir, exist_ok=True)
    total = int(float(proj.get("assembly", {}).get("total", 30)))
    # name_main = 主片（时长由 total 决定）；name_extra = 附带的第二条（默认是 15s 版）
    pairs = []
    if d.get("name_main") or d.get("name30"):
        pairs.append((d.get("name_main") or d.get("name30"), f"{runid}_{total}s.mp4"))
    if d.get("name_extra") or d.get("name15"):
        pairs.append((d.get("name_extra") or d.get("name15"), f"{runid}_15s.mp4"))
    out = []
    for name, src_name in pairs:
        src = os.path.join(workdir, src_name)
        if not os.path.exists(src):
            if src_name.endswith("_15s.mp4"):
                continue
            fail("deliver", f"缺 {src}"); continue
        dst = os.path.join(dst_dir, name)
        with open(src, "rb") as a, open(dst, "wb") as b:
            b.write(a.read())
        pr = probe(dst)
        out.append(dst)
        log(f"  {dst}  {pr[0]:.1f}s {pr[1]}x{pr[2]} {pr[3]/1e6:.1f}MB" if pr else f"  {dst}")
    if out and not FAILED:
        ok("deliver", f"{len(out)} 个文件 → {dst_dir}")
    return out


# ---------------------------------------------------------------- main
def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        sys.exit(__doc__)
    proj_path = sys.argv[1]
    steps, seg_arg, runid_ov, res_ov = "all", None, None, None
    for a in sys.argv[2:]:
        if a.startswith("--steps="):      steps = a.split("=", 1)[1]
        elif a == "--steps":              pass
        elif a.startswith("--seg="):      seg_arg = a.split("=", 1)[1]
        elif a.startswith("--runid="):    runid_ov = a.split("=", 1)[1]
        elif a.startswith("--res="):      res_ov = a.split("=", 1)[1]
        elif steps == "all" and not a.startswith("-") and "," in a and a.replace(",", "").isalpha():
            steps = a
    argv = sys.argv[2:]
    if "--steps" in argv:
        steps = argv[argv.index("--steps") + 1]
    proj = load_project(proj_path)
    workdir = os.path.expanduser(proj.get("workdir", "/tmp/r2v"))
    os.makedirs(workdir, exist_ok=True)
    runid = runid_ov or proj.get("runid", "v1")
    res = res_ov or proj.get("resolution", "720P")
    want = ["plan", "submit", "fetch", "verify", "assemble", "deliver"] if steps == "all" else \
           [s.strip() for s in steps.split(",") if s.strip()]
    segs = parse_segs(proj, seg_arg)
    log(f"▶ make_ad  runid={runid} res={res} workdir={workdir} 段={segs} 步骤={'/'.join(want)}")
    # plan 永远先跑：提交前必须有 prompt
    prompts = build_prompts(proj, segs)
    if FAILED:
        log("\n结论：❌ 计划阶段就失败，未提交任何任务（没花钱）")
        for s, w in FAILED:
            log(f"  - {s}: {w}")
        sys.exit(1)
    if "plan" in want:
        step_plan(proj, workdir, runid, res, prompts)
    if "submit" in want:
        refs, notes = resolve_refs(proj, workdir)
        for i, (u, nt) in enumerate(zip(refs, notes), 1):
            log(f"  图{i}: {nt} -> {u}")
        step_submit(proj, workdir, runid, res, prompts, refs)
    if "fetch" in want:
        step_fetch(proj, workdir, runid)
    if "verify" in want:
        step_verify(proj, workdir, runid, segs)
    if "assemble" in want:
        step_assemble(proj, workdir, runid, segs)
    if "deliver" in want:
        step_deliver(proj, workdir, runid)
    log("")
    if FAILED:
        log("结论：❌ 有失败项，逐条如下（失败原因都是原文，未粉饰）：")
        for s, w in FAILED:
            log(f"  - {s}: {w}")
        sys.exit(1)
    log("结论：✅ 全部步骤通过（产物路径见上）")


if __name__ == "__main__":
    main()
