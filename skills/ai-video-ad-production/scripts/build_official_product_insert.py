#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官方真机插入镜 v2 —— 修三处：①拉页7 裁掉底部文案 ②白底抠成透明（不再露矩形）③3.png 自动定位待抠区域
"""
import os
import subprocess

from PIL import Image, ImageFilter

D = os.path.expanduser("~/Desktop/电商素材/剃须刀")
FF = os.path.expanduser("~/video-tools/bin/ffmpeg")
W, H = 1350, 2400
OUT = "/tmp/r2v/off"
os.makedirs(OUT, exist_ok=True)


def knockout_white(im, thr=238, fade=16):
    """白底 → 透明（边缘羽化，避免生硬矩形）"""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            m = min(r, g, b)
            if m >= thr:
                px[x, y] = (r, g, b, 0)
            elif m >= thr - fade:
                k = (thr - m) / fade
                px[x, y] = (r, g, b, int(a * k))
    return im


def content_bbox(im):
    """非白内容的包围盒"""
    im = im.convert("RGBA")
    a = im.split()[3]
    bb = a.getbbox()
    if bb:
        return bb
    from PIL import ImageChops
    white = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im.convert("RGB"), white).convert("L").point(lambda v: 255 if v > 18 else 0)
    return diff.getbbox()


def dark_bg():
    bg = Image.new("RGB", (W, H), (26, 28, 30))
    light = Image.new("L", (W, H), 0)
    px = light.load()
    cx, cy = W // 2, int(H * 0.42)
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            dx, dy = (x - cx) / (W * 0.75), (y - cy) / (H * 0.6)
            v = max(0, 1 - (dx * dx + dy * dy)) ** 1.6
            c = int(v * 150)
            for yy in range(y, min(y + 4, H)):
                for xx in range(x, min(x + 4, W)):
                    px[xx, yy] = c
    return Image.composite(Image.new("RGB", (W, H), (86, 92, 98)), bg,
                           light.filter(ImageFilter.GaussianBlur(60)))


def place(canvas, im, width_frac, y_frac):
    tw = int(W * width_frac)
    th = int(im.height * tw / im.width)
    im = im.resize((tw, th), Image.LANCZOS)
    canvas.paste(im, ((W - tw) // 2, int(H * y_frac) - th // 2), im)
    return canvas


# ---- 镜1 刀网微距（裁掉左侧文案 + 底部标注）----
src = Image.open(f"{D}/拉页图/拉页图-7.jpg").convert("RGB")
m1 = src.crop((118, 480, 556, 1105)).resize((W, H), Image.LANCZOS)
m1.save(f"{OUT}/p1.png")
print("p1 crop 118,480,556,1105")

# ---- 镜2 正面全身（抠白底 → 深灰底）----
prod = knockout_white(Image.open(f"{D}/产品图/正面图_cropped.png"))
bb = content_bbox(prod)
print("正面图 内容框:", bb)
prod = prod.crop(bb)
m2 = place(dark_bg(), prod, 0.62, 0.45)
m2.save(f"{OUT}/p2.png")

# ---- 镜3 底部端面（自动定位 → 抠白底 → 深灰底）----
raw = Image.open(f"{D}/产品图/3.png")
bb3 = content_bbox(raw)
print("3.png 内容框:", bb3)
pad = 0.06
x0, y0, x1, y1 = bb3
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
hh = (y1 - y0) * (1 + pad * 2)
ww = hh * 9 / 16
base = knockout_white(raw.crop((int(cx - ww / 2), int(cy - hh / 2),
                               int(cx + ww / 2), int(cy + hh / 2))))
m3 = place(dark_bg(), base, 0.70, 0.45)
m3.save(f"{OUT}/p3.png")

# ---- 合成 3s ----
v, fc = [], []
for i in range(1, 4):
    v += ["-loop", "1", "-t", "1.0", "-i", f"{OUT}/p{i}.png"]
    fc.append(f"[{i-1}:v]scale=1350:2400,zoompan=z='min(zoom+0.0006,1.06)':d=30:s=1080x1920:fps=30,setsar=1[v{i-1}]")
fc.append("[v0][v1]xfade=transition=fade:duration=0.15:offset=0.85[x1]")
fc.append("[x1][v2]xfade=transition=fade:duration=0.15:offset=1.85[x2]")
out = "/tmp/r2v/official_product.mp4"
subprocess.run([FF, "-y", "-v", "error", *v, "-filter_complex", ";".join(fc), "-map", "[x2]",
                "-t", "3.0", "-r", "30", "-pix_fmt", "yuv420p", out], check=True)
print("✅", out, os.path.getsize(out), "B")

# ---- 预览帧 ----
for t in (0.4, 1.4, 2.5):
    subprocess.run([FF, "-y", "-v", "error", "-ss", str(t), "-i", out, "-frames:v", "1", f"{OUT}/v2_{t}.png"], check=True)
ims = [Image.open(f"{OUT}/v2_{t}.png").convert("RGB").resize((330, 587)) for t in (0.4, 1.4, 2.5)]
c = Image.new("RGB", (330 * 3, 587))
for i, im in enumerate(ims):
    c.paste(im, (i * 330, 0))
c.save(f"{OUT}/preview2.jpg", quality=92)
print("preview2:", c.size)
