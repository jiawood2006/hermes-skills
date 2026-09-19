#!/usr/bin/env python3
"""官方产品图 → 透明 PNG（真像素，供"非生成式合成"用）

用法: python3 cutout_product.py <官方白底图.png> <输出.png>
原理: 白底按亮度阈值转 alpha —— 保留网孔/logo/渐变原像素，不做任何重绘。
"""
import sys
from PIL import Image
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
a = np.array(im).astype(np.int16)
lum = a[:, :, :3].mean(axis=2)
mask = np.clip((238 - lum) / 28.0, 0, 1)      # 238 以下开始不透明；白底(≈255)→0
a[:, :, 3] = (mask * 255).astype(np.uint8)
out = Image.fromarray(a.astype(np.uint8))
out = out.crop(out.split()[3].getbbox())      # 裁到主体外接框
out.save(dst)
print("ok", dst, out.size)
