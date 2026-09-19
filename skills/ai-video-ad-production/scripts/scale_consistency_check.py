#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨镜头产品尺寸一致性检查（抽帧→统一高度→红网格→并排拼图，供肉眼/vision 读格数）。

用法：
  python3 scale_consistency_check.py out.jpg [grid=38] <panel1> <panel2> ...
  panel 写法：  图片路径              例：官方拉页图-2.jpg
                视频路径@秒           例：v5_seg1.mp4@8.5

判读基准（把"官方实拍"放第一格当分母）：
  产品可见高度 ÷ 人物头高         真机 74mm / 头高 ~230mm ≈ 0.32~0.40
  产品直径 ÷ 手指宽                ≈ 2.0（39mm / 19mm）
  产品长 ÷ 手掌宽                  ≈ 0.87
  物理可容性：握着时手掌能否整个包住机身、五指能否合拢绕过背面（模型对这条最敏感）
"""
import os, subprocess, sys, tempfile

FF = os.path.expanduser("~/video-tools/bin/ffmpeg")
if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

out = sys.argv[1]
rest = sys.argv[2:]
grid = 38
if rest and rest[0].isdigit():
    grid = int(rest.pop(0))
items = rest
H = 747  # 统一高度，保证格数可比
tmp = tempfile.mkdtemp()
vf = f"scale=-1:{H},drawgrid=w={grid}:h={grid}:t=1:c=red@0.55"
panels = []
for n, it in enumerate(items):
    p = f"{tmp}/p{n}.jpg"
    if "@" in it:
        f, t = it.rsplit("@", 1)
        cmd = [FF, "-loglevel", "error", "-y", "-ss", t, "-i", f, "-frames:v", "1", "-vf", vf, p]
    else:
        cmd = [FF, "-loglevel", "error", "-y", "-i", it, "-vf", vf, p]
    subprocess.run(cmd, check=True)
    panels.append(p)

ins = []
for p in panels:
    ins += ["-i", p]
fc = "".join(f"[{i}]" for i in range(len(panels))) + f"hstack=inputs={len(panels)}"
subprocess.run([FF, "-loglevel", "error", "-y"] + ins + ["-filter_complex", fc, out], check=True)
print("OUT", out, os.path.getsize(out), "bytes |", len(panels), "panels | grid", grid, "px")
