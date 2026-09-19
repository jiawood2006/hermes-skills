#!/usr/bin/env python3
"""用户发的成片截图 → 定位回成片时间码。

用户只会说「这个镜头产品高度有点高了」并甩一张截图，不给时间码。
本脚本把截图匹配回成片，输出最可能的秒数，再去抽该帧放大核验。

原理：截掉手机黑边 → 缩到 90x160 灰度 → 与成片每 <step> 秒抽的帧算 MSE → 最小者命中。
实测命中帧 MSE 6.6、次优 24.9，区分度足够。

用法:
  python3 locate_reported_frame.py 成片.mp4 截图1.jpg [截图2.jpg ...] [--out /tmp/loc] [--step 0.5]

产出:
  <out>/f_<t>.png    抽出的帧（可直接喂 vision 放大核验）
  stdout: 每张截图的最佳匹配时间码 + MSE + 次优值

依赖: ffmpeg/ffprobe（或 FFMPEG=/path FFMPEG 指定）、Pillow、numpy
"""
import argparse, os, shutil, subprocess, sys

import numpy as np
from PIL import Image

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"
SIZE = (90, 160)


def duration(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def gray(arr_img):
    return np.asarray(Image.fromarray(arr_img).convert("L").resize(SIZE, Image.LANCZOS),
                      dtype=np.float32)


def shot_payload(path):
    """截掉手机黑边：按 9:16 取垂直居中的中间区域。"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    th = int(w * 16 / 9)
    if th <= h:
        top = (h - th) // 2
        im = im.crop((0, top, w, top + th))
    return gray(np.asarray(im))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("shots", nargs="+")
    ap.add_argument("--out", default="/tmp/loc")
    ap.add_argument("--step", type=float, default=0.5)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    d = duration(a.film)
    ts = [round(i * a.step, 2) for i in range(int(d / a.step) + 1)]
    frames = {}
    for t in ts:
        f = f"{a.out}/f_{t}.png"
        if not os.path.exists(f):
            subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", str(t), "-i", a.film,
                            "-frames:v", "1", f], capture_output=True)
        if os.path.exists(f):
            frames[t] = gray(np.asarray(Image.open(f).convert("RGB")))
    print(f"成片 {d:.2f}s，抽帧 {len(frames)} 张（step={a.step}s）")

    for s in a.shots:
        if not os.path.exists(s):
            print("MISS", s); continue
        tg = shot_payload(s)
        ranked = sorted(((float(((frames[t] - tg) ** 2).mean()), t) for t in frames))[:3]
        best_m, best_t = ranked[0]
        print(f"{os.path.basename(s)} -> 命中 {best_t}s (MSE {best_m:.1f})"
              f"  次优 " + ", ".join(f"{t}s/{m:.1f}" for m, t in ranked[1:]))
    print(f"\n下一步：把 {a.out}/f_<t>.png crop 到产品/人物区域，×2 + 40px 网格，交给视觉逐项问"
          "（长:径比 / 网面色 / 黑环 / Haier 次数 / 侧面开孔 / 上唇胡须 / 是否同一人）。")
    print("⚠️ 颜色类判断必须看原始分辨率 —— 缩略拼图会产生色偏，曾据此误判'下巴发绿'。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
