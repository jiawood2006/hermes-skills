#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产品细节 2 倍放大核对（交付前必做，别用缩小的拼图代替）。

用法：
  python3 product_fidelity_zoom.py out.jpg <视频@秒> [<视频@秒> ...] [--box=l,t,r,b]

--box 用分数坐标圈定产品所在区域（默认 0.22,0.30,0.78,0.80 = 画面中下部）。
输出等高并排的 2 倍放大拼图，用来核对 5 项：充电口位置 / Haier 数量与位置 /
直筒外形（无收腰台阶锥形）/ 刀网是否浅金色蜂窝 / 产品相对手的尺寸。
"""
import os, subprocess, sys, tempfile
from PIL import Image

FF = os.path.expanduser("~/video-tools/bin/ffmpeg")
box = (0.22, 0.30, 0.78, 0.80)
items = []
for a in sys.argv[1:]:
    if a.startswith("--box="):
        box = tuple(float(x) for x in a.split("=", 1)[1].split(","))
    else:
        items.append(a)

out, items = items[0], items[1:]
tmp = tempfile.mkdtemp()
panels = []
for n, it in enumerate(items):
    f, t = it.rsplit("@", 1)
    raw = f"{tmp}/r{n}.jpg"
    subprocess.run([FF, "-loglevel", "error", "-y", "-ss", t, "-i", f, "-frames:v", "1", raw], check=True)
    im = Image.open(raw)
    W, H = im.size
    c = im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))
    c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
    p = f"{tmp}/p{n}.jpg"
    c.save(p, quality=95)
    panels.append(p)

ims = [Image.open(p) for p in panels]
hh = min(i.height for i in ims)
ims = [i.resize((int(i.width * hh / i.height), hh)) for i in ims]
Wt = sum(i.width for i in ims) + 20 * (len(ims) - 1)
cv = Image.new("RGB", (Wt, hh), (15, 15, 15))
x = 0
for i in ims:
    cv.paste(i, (x, 0))
    x += i.width + 20
cv.save(out, quality=93)
print("OUT", out, cv.size, "panels", len(panels))
