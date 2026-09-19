#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尺寸一致性读数面板：把"官方真值 + 成片各镜头"抽帧并排拼图，叠红色网格供读格数。

为什么要它：用户会追问「这个镜头的产品尺寸和那个镜头不一致/偏大偏小」，
凭观感争论没用，必须像这样量化。同事先画网格再读格数——本项目已手工做过 4 次，故脚本化。

判据（HSQ1 真机 74×39mm 换算的"相对人体比例"锚点）：
    产品长度 ≈ 头高(发际线→下巴)的 1/3 ≈ 手掌宽度的 0.9 ≈ 手指宽度的 3.9 倍
读法：数每格里产品/手/头各占几格，跨面板比「产品 ÷ 手(或头)」的比值是否一致。

用法：
    python3 scale_panel_check.py out.jpg \
        --panel "official:/path/拉页图-2.jpg" \
        --panel "shave:/tmp/r2v/v4_seg1.mp4@8.5" \
        --panel "wash:/tmp/r2v/v4_seg3_vo.mp4@21.5" \
        [--cell 380] [--grid 38]

panel 格式： "标签:图片路径"  或  "标签:视频路径@秒"（视频会抽该时刻的帧）
输出：out.jpg（各面板等高并排，每格 --grid 像素画红线）
"""
import argparse
import os
import subprocess
import sys

FFMPEG = os.path.expanduser("~/video-tools/bin/ffmpeg")


def extract(spec, workdir):
    """'label:path' 或 'label:video@t' → (label, jpg_path)"""
    label, _, rest = spec.partition(":")
    if not rest:
        raise SystemExit(f"面板格式错误: {spec}（应为 标签:路径[@秒]）")
    path, _, ts = rest.rpartition("@")
    if path and ts:                      # 视频抽帧
        out = os.path.join(workdir, f"p_{label}.jpg")
        subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-ss", ts, "-i", path,
                        "-frames:v", "1", out], check=True)
        return label, out
    return label, rest                  # 直接是图片


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--panel", action="append", required=True)
    ap.add_argument("--cell", type=int, default=380, help="每格显示宽（等比缩放后）")
    ap.add_argument("--grid", type=int, default=38, help="网格边长像素（读格数用）")
    ap.add_argument("--workdir", default="/tmp/scale_panel")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)

    made = []
    for spec in a.panel:
        label, img = extract(spec, a.workdir)
        out = os.path.join(a.workdir, f"g_{label}.jpg")
        # 等比缩到 cell 宽 → 补白到统一高度 → 叠网格（网格在缩放后画，格数才可读）
        subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", img, "-vf",
                        f"scale={a.cell}:{a.cell * 2}:force_original_aspect_ratio=decrease,"
                        f"pad={a.cell}:{a.cell * 2}:(ow-iw)/2:(oh-ih)/2:white,"
                        f"drawgrid=w={a.grid}:h={a.grid}:t=1:c=red@0.45", out], check=True)
        made.append(out)
        print(f"  面板 {label}: {out}")

    ins = []
    for p in made:
        ins += ["-i", p]
    fc = "".join(f"[{i}]" for i in range(len(made))) + f"hstack={len(made)}"
    r = subprocess.run([FFMPEG, "-loglevel", "error", "-y"] + ins +
                       ["-filter_complex", fc, "-frames:v", "1", a.out],
                       capture_output=True, text=True)
    if r.returncode:
        print("❌ 拼图失败:", r.stderr[-600:]); return 1
    print(f"✅ {a.out}  （{len(made)} 面板 · 网格 {a.grid}px · 每格 {a.cell}px 宽）")
    print("   下一步：看图读格数（产品÷手或头的比值），跨面板比较是否一致；"
          "再用 vision 复核一遍，别只凭格数下结论。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
