#!/usr/bin/env python3
"""运动量 / 贴图 检测：判断成片"是不是静图贴图"。

背景（2026-09-16 用户纠偏）：用户对"静图 + Ken Burns 推近"充镜头的成片判「贴图」：
  - 2026-09-15「像PPT / 露灰框」
  - 2026-09-16「最新的又成贴图了」
所以**交付前必须量化验运动**，肉眼"看着还行"不算验过。

用法：
  python3 verify_motion.py 成片.mp4 [--shots a.mp4 b.mp4 ...] [--freeze-db -60] [--freeze-dur 0.8]

产出：
  1) 全片冻结区间清单（freezedetect）→ **必须为 0**
  2) 逐镜头帧间差均值（tblend=difference + signalstats YAVG）→ 越大越有动感
  3) 判定：冻结区间 > 0 → ❌ 有静止段（贴图嫌疑），列出区间让用户确认

实测参考（15s v2 通过验收）：冻结区间 0；帧间差均值 3.45 / 2.59 / 4.37 / 1.57
（末位是产品英雄慢推镜：运动本身很轻，靠花字动效补，但仍 > 1 才不算糊）。
注意：帧间差均值会受画质/噪点影响，**它只是辅证，冻结区间才是硬指标**。
"""
import argparse, os, re, shutil, subprocess, sys

FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or os.path.expanduser("~/video-tools/bin/ffmpeg")
FP = os.environ.get("FFPROBE") or shutil.which("ffprobe") or os.path.expanduser("~/video-tools/bin/ffprobe")


def run(args):
    return subprocess.run(args, capture_output=True, text=True).stdout + \
           subprocess.run(args, capture_output=True, text=True).stderr


def freezes(path, db, dur):
    r = subprocess.run([FF, "-hide_banner", "-i", path, "-vf",
                        f"freezedetect=n={db}dB:d={dur}", "-map", "0:v", "-f", "null", "-"],
                       capture_output=True, text=True)
    log = r.stderr
    starts = [float(m) for m in re.findall(r"freeze_start:\s*([0-9.]+)", log)]
    ends = [float(m) for m in re.findall(r"freeze_end:\s*([0-9.]+)", log)]
    if len(ends) < len(starts):
        ends.append(float("inf"))
    return list(zip(starts, ends))


def motion(path, tail=40):
    r = subprocess.run([FF, "-hide_banner", "-i", path, "-vf",
                        "tblend=all_mode=difference,signalstats,"
                        "metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                       capture_output=True, text=True)
    vals = [float(v) for v in re.findall(r"YAVG=([0-9.]+)", r.stderr)][-tail:]
    return sum(vals) / len(vals) if vals else 0.0


def dur(path):
    o = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(o.strip())
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--shots", nargs="*", default=[])
    ap.add_argument("--freeze-db", type=float, default=-60)
    ap.add_argument("--freeze-dur", type=float, default=0.8)
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print("MISS", a.video); return 2
    fz = freezes(a.video, a.freeze_db, a.freeze_dur)
    print(f"=== {os.path.basename(a.video)}  {dur(a.video):.2f}s ===")
    print(f"运动量(帧间差均值): {motion(a.video):.2f}")
    if not fz:
        print("冻结区间: 0  ✅ 全片都有运动（无贴图嫌疑）")
    else:
        print(f"冻结区间: {len(fz)}  ❌ 存在静止段（贴图嫌疑）")
        for s, e in fz:
            e_s = "到片尾" if e == float("inf") else f"{e:.2f}s"
            print(f"   {s:.2f}s → {e_s}（静止 {e - s:.2f}s）")
        print("   → 这些镜头是静图/冻结，必须换成首帧法真运动视频（见 "
              "references/product-scale-and-firstframe-method.md）")

    for s in a.shots:
        if os.path.exists(s):
            print(f"  [{os.path.basename(s)}] {dur(s):.2f}s  运动量 {motion(s):.2f}")
        else:
            print(f"  [{s}] MISS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
