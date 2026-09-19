#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2V 带货片后期装配器（1080x1920）：多段拼接 + 定时花字/字幕/价格/参数条 + 15s 裁切 + 同步核验图。

为什么有这个脚本：2026-09-16 那轮是手搓 ffmpeg 命令现拼的，中间踩了
「花字文件命名不一致 / overlay 时间窗写错 / 抽帧拼图误判字幕不同步」三个坑。
这里把已验证的作法固定下来，下次直接改 JSON 跑。

用法
----
1) 装配：  python3 assemble_r2v_overlays.py cfg.json
2) 同步核验：python3 assemble_r2v_overlays.py --sync out.mp4 2.0,5.5,15.0,18.0,22.0,25.0
   → 按**精确时间点**单帧抽样（-ss 在 -i 前）拼成 sync_sheet.jpg。
   ⚠️ 不要用 `fps=1/3.75,tile` 抽样图判断字幕同步：抽样帧时间标签与实际时间不对应，
      本脚本作者据此误判过一次「字幕早了 1 秒」。必须用 --sync 这种精确抽帧。

cfg.json 字段
-------------
{
  "out": "/tmp/r2v/hsq1_30s.mp4",
  "total": 30.0,                       // 输出总长（秒）；配合每段 trim 用
  "vo": "/tmp/r2v/vo30_yunxi.mp3",     // 可选：整条画外旁白。给了就替换段内音频（R2V 段内只有环境音）
                                       // 旁白用 build_vo30.py 生成，落点=字幕 start，天生对齐
  "segments": [                        // 顺序拼接；trim=该段只取前 N 秒（15s 版就从长片裁）
    {"path": "/tmp/r2v/r2v_seg1.mp4"},
    {"path": "/tmp/r2v/seg2.mp4"},
    {"path": "/tmp/r2v/seg3.mp4", "trim": 4.97}
  ],
  "subs":   [{"text": "早上起晚了，胡子都没来得及刮。", "start": 0.1, "end": 4.1}],
  "chips":  [{"text": "全身水洗 · 刀头可拆洗", "start": 20.6, "end": 25.0}],
  "price":  {"text": "¥169", "start": 27.0, "end": 30.2},   // 可选；用户口径=价格常变，成片默认不放
  "spec":   {"items": ["74×39mm", "70g", "Type-C"], "start": 27.0, "end": 30.2},
  "compliance": "AI 生成内容 · 广告"
}
字幕/花字落点必须来自 STT 的词级时间（见 stt_dialogue_check.py --words），不要凭猜。
整机编排（plan→submit→fetch→verify→assemble→deliver 一条命令）见 make_ad.py。
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FF = os.environ.get("FFMPEG", os.path.expanduser("~/video-tools/bin/ffmpeg"))
FFPROBE = os.environ.get("FFPROBE", os.path.expanduser("~/video-tools/bin/ffprobe"))
FONT = os.environ.get("AD_FONT", "/System/Library/Fonts/PingFang.ttc")
TMP = os.environ.get("AD_TMP", "/tmp/r2v")


def _font(size, idx=1):  # idx=1 = Medium 字重，白字更挺
    return ImageFont.truetype(FONT, size, index=idx)


def _new():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def layer_subtitle(text, out):
    """底部字幕条：圆角半透明黑底 + 白字（避开最底部合规标）"""
    im, d = _new(), None
    d = ImageDraw.Draw(im)
    ft = _font(50)
    tw = d.textlength(text, font=ft)
    pad = 34
    x0 = (W - (tw + pad * 2)) / 2
    y0, h = 1560, 96
    d.rounded_rectangle([x0, y0, x0 + tw + pad * 2, y0 + h], radius=20, fill=(0, 0, 0, 150))
    d.text((W / 2, y0 + h / 2), text, font=ft, fill=(255, 255, 255, 255), anchor="mm")
    im.save(out)
    return out


def layer_chip(text, out, y=250, size=44):
    """顶部卖点 chip —— 放顶部是铁律：产品在画面中部/下部，底部还可能被模型自带字幕占"""
    im = _new()
    d = ImageDraw.Draw(im)
    ft = _font(size)
    tw = d.textlength(text, font=ft)
    pad = 30
    x0 = (W - (tw + pad * 2)) / 2
    d.rounded_rectangle([x0, y, x0 + tw + pad * 2, y + size + 44], radius=18, fill=(0, 0, 0, 145))
    d.text((W / 2, y + (size + 44) / 2), text, font=ft, fill=(255, 255, 255, 255), anchor="mm")
    im.save(out)
    return out


def layer_price(out, text="¥169", sub="到手价"):
    im = _new()
    d = ImageDraw.Draw(im)
    ft = _font(150)
    tw = d.textlength(text, font=ft)
    x0 = (W - (tw + 60)) / 2
    y0, h = 1160, 230
    d.rounded_rectangle([x0, y0, x0 + tw + 60, y0 + h], radius=32, fill=(196, 30, 58, 232))
    d.text((W / 2, y0 + h / 2 - 14), text, font=ft, fill=(255, 255, 255, 255), anchor="mm")
    d.text((W / 2, y0 + h - 52), sub, font=_font(38), fill=(255, 240, 240, 240), anchor="mm")
    im.save(out)
    return out


def layer_spec(out, items=("74×39mm", "70g", "Type-C")):
    """底部参数条（数值取自官方物料，属画面证据，不进话术）"""
    im = _new()
    d = ImageDraw.Draw(im)
    ft = _font(40)
    y0 = 1730
    d.rounded_rectangle([60, y0, W - 60, y0 + 92], radius=18, fill=(0, 0, 0, 150))
    step = (W - 120) / len(items)
    for i, t in enumerate(items):
        d.text((60 + step * (i + 0.5), y0 + 46), t, font=ft, fill=(255, 255, 255, 245), anchor="mm")
        if i:
            d.line([60 + step * i, y0 + 22, 60 + step * i, y0 + 70], fill=(255, 255, 255, 90), width=2)
    im.save(out)
    return out


def layer_compliance(out, text="AI 生成内容 · 广告"):
    """AI 生成内容合规标注：全程常驻、左下角小字"""
    im = _new()
    ImageDraw.Draw(im).text((54, H - 92), text, font=_font(30), fill=(255, 255, 255, 205))
    im.save(out)
    return out


def build_overlays(cfg):
    """把所有文字层渲染成 PNG，返回 [(path, start, end)] 时间窗列表"""
    ov = []
    for i, s in enumerate(cfg.get("subs", []), 1):
        p = f"{TMP}/ov_sub{i}.png"
        ov.append((layer_subtitle(s["text"], p), s["start"], s["end"]))
    for i, c in enumerate(cfg.get("chips", []), 1):
        p = f"{TMP}/ov_chip{i}.png"
        ov.append((layer_chip(c["text"], p), c["start"], c["end"]))
    if cfg.get("price"):
        p = cfg["price"]
        ov.append((layer_price(f"{TMP}/ov_price.png", p.get("text", "¥169")), p["start"], p["end"]))
    if cfg.get("spec"):
        s = cfg["spec"]
        ov.append((layer_spec(f"{TMP}/ov_spec.png", tuple(s.get("items", ()))), s["start"], s["end"]))
    ov.append((layer_compliance(f"{TMP}/ov_comp.png", cfg.get("compliance", "AI 生成内容 · 广告")), 0, 999))
    return ov


def assemble(cfg):
    segs = cfg["segments"]
    ov = build_overlays(cfg)
    inputs = []
    for s in segs:
        inputs += ["-i", s["path"]]
    for p, _a, _b in ov:
        inputs += ["-i", p]

    # 整条旁白（VO）可选：给了就用它替换段内音频（R2V 段内是环境音，成片统一画外旁白）
    # ⚠️ VO 必须放在所有 overlay 之后追加，否则 overlay 的输入序号会错位
    vo = cfg.get("vo")
    vo_idx = None
    if vo:
        if not os.path.exists(vo):
            sys.exit(f"assemble: cfg.vo 不存在 {vo}")
        vo_idx = len(inputs) // 2
        inputs += ["-i", vo]

    fc, vparts, aparts = [], [], []
    for i, s in enumerate(segs):
        trim = s.get("trim")
        pre = f"trim=0:{trim},setpts=PTS-STARTPTS," if trim else ""
        fc.append(f"[{i}:v]{pre}scale=1080:1920,setsar=1[v{i}]")
        if vo_idx is None:      # 用 VO 时不接段内音频（未消费的音频链会被 ffmpeg 报未连接）
            # ⚠️ 音频链必须用 asetpts（setpts 是视频滤镜）。老版本写成 setpts → ffmpeg 报
            #    "Media type mismatch ... atrim(audio) 与 setpts(video)"（2026-09-18 回归测试发现，
            #    之前所有成片都走 VO，所以没人碰过这条音频链）
            a_pre = f"atrim=0:{trim}," if trim else ""
            fc.append(f"[{i}:a]{a_pre}asetpts=PTS-STARTPTS[a{i}]")
        vparts.append(f"[v{i}]")
        aparts.append(f"[a{i}]")
    fc.append(f"{''.join(vparts)}concat=n={len(segs)}:v=1:a=0[vbase]")
    if vo_idx is None:
        fc.append(f"{''.join(aparts)}concat=n={len(segs)}:v=0:a=1[aout]")
    else:
        pad = float(cfg.get("total") or 30) + 0.5
        fc.append(f"[{vo_idx}:a]aresample=44100,apad=whole_dur={pad}[aout]")

    cur, idx = "vbase", len(segs)
    for n, (p, a, b) in enumerate(ov):
        fc.append(f"[{idx}:v]format=rgba[ov{n}]")
        fc.append(f"[{cur}][ov{n}]overlay=0:0:enable='between(t,{a},{b})'[vx{n}]")
        cur, idx = f"vx{n}", idx + 1

    cmd = [FF, "-loglevel", "error", "-y"] + inputs + [
        "-filter_complex", ";".join(fc), "-map", f"[{cur}]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    if cfg.get("total"):
        cmd += ["-t", str(cfg["total"])]
    cmd.append(cfg["out"])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print("EXIT", r.returncode)
        print(r.stderr[-2500:])
        sys.exit(1)
    probe = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration,size",
                            "-show_entries", "stream=width,height", "-of", "default=nw=1",
                            cfg["out"]], capture_output=True, text=True).stdout.strip()
    print(f"OK {cfg['out']} {os.path.getsize(cfg['out'])} bytes\n{probe}")


def sync_sheet(video, times, out=None):
    """精确时间点抽帧拼图（字幕↔语音同步核验的唯一可信做法）"""
    out = out or f"{TMP}/sync_sheet.jpg"
    tiles = []
    for t in times:
        p = f"{TMP}/f_{t}.jpg"
        subprocess.run([FF, "-loglevel", "error", "-y", "-ss", str(t), "-i", video,
                        "-frames:v", "1", "-vf", "scale=360:-1", p], check=True)
        tiles.append(p)
    n = len(tiles)
    cols = 3 if n % 3 == 0 else n
    rows = (n + cols - 1) // cols
    layout = "|".join(
        (f"{'0' if c == 0 else '+'.join(f'w{j}' for j in range(c))}_"
         f"{'0' if r == 0 else '+'.join(f'h{j}' for j in range(r))}")
        for r in range(rows) for c in range(cols))[:n]
    inputs = []
    for p in tiles:
        inputs += ["-i", p]
    subprocess.run([FF, "-loglevel", "error", "-y"] + inputs + [
        "-filter_complex", f"xstack=inputs={n}:layout={layout}",
        "-frames:v", "1", out], check=True)
    print("sync sheet:", out, "times:", times)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--sync":
        sync_sheet(sys.argv[2], [float(x) for x in sys.argv[3].split(",")])
    elif len(sys.argv) == 2:
        assemble(json.load(open(sys.argv[1])))
    else:
        sys.exit(__doc__)
