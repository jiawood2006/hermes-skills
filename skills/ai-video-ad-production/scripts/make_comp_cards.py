#!/usr/bin/env python3
"""合成式产品卡生成器（产品像素不经过任何 AI）

产品 = 官方抠图 PNG，只做几何变换 + 光影/水流/线缆叠加；背景 = 真运动场景视频的重虚化版
（虚化同时把 AI 画错的产品抹掉）。输出 1080x1920@25fps mp4，可直接进成片时间轴。

用法: python3 make_comp_cards.py <产品抠图.png> <背景视频.mp4> <kind: hero|wash|charge> <时长s> <输出.mp4> [角标文字]
"""
import os, sys, subprocess
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import numpy as np

FF = os.environ.get("FFMPEG") or os.path.expanduser("~/video-tools/bin/ffmpeg")
PING = "/System/Library/Fonts/PingFang.ttc"
W, H, FPS = 1080, 1920, 25

prod_path, bg_src, kind, dur, out_path = sys.argv[1:6]
corner = sys.argv[6] if len(sys.argv) > 6 else ""
dur = float(dur)
PROD = Image.open(prod_path).convert("RGBA")
TMP = "/tmp/comp_cards"
os.makedirs(TMP, exist_ok=True)


def bg_frames(n):
    for f in os.listdir(TMP):
        os.remove(os.path.join(TMP, f))
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          "gblur=sigma=22,eq=brightness=-0.24")
    subprocess.run([FF, "-loglevel", "error", "-i", bg_src, "-vf", vf, "-frames:v", str(n),
                    "-start_number", "0", "-q:v", "3", "-y", f"{TMP}/bg_%04d.jpg"], check=True)


def place(bg, sc, ycenter, dy=0, pw0=640):
    pw = int(pw0 * sc)
    ph = int(PROD.height * pw / PROD.width)
    p = PROD.resize((pw, ph), Image.LANCZOS)
    px, py = int(W / 2 - pw / 2), int(ycenter - ph / 2 + dy)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([px + 40, py + ph - 26, px + pw - 40, py + ph + 26],
                                  fill=(0, 0, 0, 120))
    bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))
    bg.alpha_composite(p, (px, py))
    return bg, p, px, py, pw, ph


def masked_overlay(bg, layer, alpha_mask, pos):
    m = Image.new("L", (W, H), 0)
    m.paste(alpha_mask, pos)
    bg.alpha_composite(Image.composite(layer, Image.new("RGBA", (W, H), (0, 0, 0, 0)), m))
    return bg


def sweep(bg, p, pos, t):
    sx = int(-400 + (W + 800) * ((t * 0.8) % 1.0))
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(sx, 0), (sx + 150, 0), (sx + 40, H), (sx - 110, H)],
                              fill=(255, 255, 255, 26))
    return masked_overlay(bg, gl, p.split()[3], pos)


def water(bg, p, pos, pw, ph, t):
    wl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(wl)
    px, py = pos
    for k in range(9):                       # 竖直水膜
        x = px + pw * (0.08 + 0.105 * k)
        off = (t * 900 + k * 170) % (ph + 200) - 100
        d.line([x, py + off, x + 6, py + off + 150], fill=(235, 245, 255, 60), width=7)
    for k in range(22):                      # 下落水珠
        dx = px + (k * 97) % pw
        dy = py + ((t * 1250 + k * 210) % (ph + 160)) - 80
        r = 4 + (k % 3) * 3
        d.ellipse([dx, dy, dx + r * 2, dy + r * 3], fill=(240, 250, 255, 95))
    return masked_overlay(bg, wl, p.split()[3], pos)


def cable(bg, px, py, pw, ph, t):            # 充电线 + 呼吸灯
    d = ImageDraw.Draw(bg)
    x0, y0 = px + pw * 0.62, py + ph - 6
    for i in range(60):
        u = i / 59
        d.ellipse([x0 + u * (W - x0 + 80), y0 + 120 * u ** 2 + 16 * np.sin(u * 6 + t * 2),
                   x0 + u * (W - x0 + 80) + 15, y0 + 120 * u ** 2 + 16 * np.sin(u * 6 + t * 2) + 15],
                  fill=(38, 38, 42, 255))
    g = int(120 + 100 * np.sin(t * 4))
    d.ellipse([px + pw * 0.52, py + ph - 96, px + pw * 0.52 + 26, py + ph - 70],
              fill=(255, 250, 210, g))
    return bg


n = int(dur * FPS)
bg_frames(n)
for i in range(n):
    t = i / FPS
    g = Image.open(f"{TMP}/bg_{i:04d}.jpg").convert("RGBA")
    sc = 0.95 + 0.05 * min(1.0, t / dur)                 # 缓慢放大（真动效）
    g, p, px, py, pw, ph = place(g, sc, 960, dy=int(9 * np.sin(t * 1.7)))
    if kind == "wash":
        g = water(g, p, (px, py), pw, ph, t)
    elif kind == "charge":
        g = cable(g, px, py, pw, ph, t)
    else:
        g = sweep(g, p, (px, py), t)
    if corner:                                           # 角标用 PIL 直画（矢量清晰）
        f = ImageFont.truetype(PING, 40, index=1)
        d = ImageDraw.Draw(g)
        d.text((W / 2 - d.textlength(corner, font=f) / 2, 150), corner, font=f,
               fill=(255, 255, 255, 225))
    g.convert("RGB").save(f"{TMP}/out_{i:04d}.jpg", quality=95)
subprocess.run([FF, "-loglevel", "error", "-framerate", str(FPS), "-i", f"{TMP}/out_%04d.jpg",
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-y", out_path], check=True)
print("ok", out_path, n, "帧")
