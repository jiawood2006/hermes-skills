#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产品「真实尺寸 / 长径比」核验三件套（2026-09-17 实测可用）

用法:
  measure_product_truth.py truth <官方白底产品图> [...]       # 真机基准：非白阈值取包围盒 → 长径比 + 逐行宽度剖面
  measure_product_truth.py grid  <渲染帧.png> [...]           # 给帧叠 5% 网格标尺（洋红竖线/青横线+百分比），供肉眼读数
  measure_product_truth.py cmp   <渲染帧.png> <官方白底图>    # 同高并排对比（渲染 vs 真机），一眼看出比例差

为什么渲染帧不做自动分割：暗像素阈值会把背景暗部算进直径、把手挡处截短长度；
泛洪填充会从种子串到背景；金色检测会把皮肤判成金色。
三种都实测给出过与事实相反的结论（报 1.55 正常，实际 2.45 太长）。
⇒ **真机用本脚本自动量，渲染帧一律网格/并排肉眼读**。

HSQ1 真机基准（正面图.png / 左侧图.png 均一致）：
  产品框 626x1207 ⇒ 全长 / 机身直径 = 1.93，且逐行宽度恒定 = 上下等粗直筒
  全长 / 金色刀网直径 = 2.62（金网在黑环内部，约 0.73x 环径）
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

TRUTH_REF = "HSQ1: 全长/机身直径=1.93 ; 全长/金网直径=2.62"


def truth(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    lum = a.mean(2)
    sat = a.max(2) - a.min(2)
    mask = (lum < 238) | (sat > 18)          # 白底上的产品（含浅色描边）
    ys, xs = np.nonzero(mask)
    if len(ys) < 100:
        print(f"{path}: 检出像素太少({len(ys)})，确认是白底产品图吗？")
        return
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    hh, ww = y1 - y0 + 1, x1 - x0 + 1
    print(f"{path}: 图{im.size} 产品框 {ww}x{hh} -> 长径比 {hh / ww:.2f}   (基准 {TRUTH_REF})")
    prof = []
    for yy in range(y0, y1 + 1, max(1, hh // 10)):
        idx = np.nonzero(mask[yy])[0]
        w = (idx.max() - idx.min() + 1) if len(idx) else 0
        prof.append(f"{(yy - y0) * 100 // hh}%:w={w}")
    print("    逐行宽度:", " | ".join(prof), "（宽度恒定=上下等粗直筒）")


def grid(paths, scale=0.62):
    tiles = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        for i in range(1, 20):
            x, y = int(im.width * i / 20), int(im.height * i / 20)
            d.line([(x, 0), (x, im.height)], fill=(255, 0, 255), width=1)
            d.line([(0, y), (im.width, y)], fill=(0, 255, 255), width=1)
            if i % 2 == 0:
                d.text((x + 2, 4), str(i * 5), fill=(255, 255, 0))
                d.text((4, y + 2), str(i * 5), fill=(255, 255, 0))
        tiles.append((im, os.path.basename(p)))
    h = max(i.height for i, _ in tiles) + 30
    w = sum(i.width for i, _ in tiles) + 10 * len(tiles)
    c = Image.new("RGB", (w, h), (12, 12, 12))
    d = ImageDraw.Draw(c)
    x = 0
    for im, lab in tiles:
        c.paste(im, (x, 30))
        d.rectangle([x, 0, x + 300, 26], fill=(170, 0, 0))
        d.text((x + 6, 7), lab, fill=(255, 255, 0))
        x += im.width + 10
    out = paths[0].rsplit(".", 1)[0] + "_grid.jpg"
    c.save(out)
    print(out, c.size, "(洋红=竖线5% 青=横线5%，数字为画面百分比；")
    print("  读数后按 画面宽1080 / 高1920 换算像素：全长 ÷ 机身直径 应≈1.93，全长 ÷ 金网直径 应≈2.62)")


def cmp_side(frame, real, out=None, H=700):
    f = Image.open(frame).convert("RGB")
    r = Image.open(real).convert("RGB")
    f = f.resize((int(f.width * H / f.height), H), Image.LANCZOS)
    r = r.resize((int(r.width * H / r.height), H), Image.LANCZOS)
    out = out or (frame.rsplit(".", 1)[0] + "_vs_real.jpg")
    tiles = [(f, "渲染帧: " + os.path.basename(frame)), (r, "真机: " + os.path.basename(real))]
    w = sum(i.width for i, _ in tiles) + 8 * len(tiles)
    c = Image.new("RGB", (w, H + 30), (12, 12, 12))
    d = ImageDraw.Draw(c)
    x = 0
    for im, lab in tiles:
        c.paste(im, (x, 30))
        d.rectangle([x, 0, x + 340, 26], fill=(170, 0, 0))
        d.text((x + 6, 7), lab, fill=(255, 255, 0))
        x += im.width + 8
    c.save(out)
    print(out, c.size)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    if cmd == "truth" and args:
        for p in args:
            truth(p)
    elif cmd == "grid" and args:
        grid(args)
    elif cmd == "cmp" and len(args) >= 2:
        cmp_side(args[0], args[1])
    else:
        print(__doc__)
