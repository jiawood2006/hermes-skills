#!/usr/bin/env python3
"""edge-tts 配音 → 自动调速逼近目标时长（配音与镜头对齐用）。

为什么需要：AI 生成的片段自带音频"含混不可用"（用户评："配音不好"），成片一律改用我方 TTS；
但镜头长度是固定的，配音太长会被截断、太短会空档 → 必须按目标秒数反向调速。

用法：
  python3 tts_fit.py --text "镀钛刀网，三叶刀片，8500转" --target 3.28 --out /tmp/vo1.mp3
  python3 tts_fit.py --text "试试海尔这个，全新迷你机身，轻巧便携" --target 3.76 --out /tmp/vo0.mp3 --tries 6

参数：
  --voice  默认 zh-CN-XiaoxiaoNeural（另有 zh-CN-XiaoyiNeural 温柔女 / zh-CN-YunxiNeural 男）
  --target 目标秒数（= 该镜头预留的配音窗口）
  --tol    允许误差，默认 0.2s
  --tts-python 跑 edge-tts 的解释器（本机为 ~/video-tools/mpt-venv/bin/python）；默认当前解释器
  --probe  ffprobe 路径（默认 PATH 上的 ffprobe）

实测收敛示例：18字/目标3.76s → rate=+18%；15字/目标3.28s → +16%；18字/目标4.62s → +0%。
退出码：0=已逼近目标；2=未能在次数内逼近（输出仍会生成，用于人工判断）。
"""
import argparse, os, shutil, subprocess, sys


def dur(path, probe):
    out = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def synth(py, voice, rate, text, out):
    return subprocess.run([py, "-m", "edge_tts", "--voice", voice, f"--rate={rate:+d}%",
                           "--text", text, "--write-media", out],
                          capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--target", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--tol", type=float, default=0.2)
    ap.add_argument("--tries", type=int, default=6)
    ap.add_argument("--tts-python", default=sys.executable)
    ap.add_argument("--probe", default=os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe")
    a = ap.parse_args()

    rate = 0
    d = 0.0
    for i in range(a.tries):
        r = synth(a.tts_python, a.voice, rate, a.text, a.out)
        if r.returncode != 0:
            print(f"❌ edge-tts 失败 (rate={rate:+d}%): {r.stderr[-200:]}")
            return 1
        d = dur(a.out, a.probe)
        if d <= 0:
            print("❌ 生成文件无时长")
            return 1
        if abs(d - a.target) <= a.tol:
            break
        # 目标越长→语速越慢；用 90% 步长避免震荡
        rate = max(-40, min(60, rate + int(round((d / a.target - 1) * 90))))
    ok = abs(d - a.target) <= a.tol
    print(f"{'✅' if ok else '⚠️'} {len(a.text)}字 目标{a.target:.2f}s → 实际{d:.2f}s "
          f"(rate={rate:+d}%) {a.out}")
    if not ok:
        print("提示：差得较多就改台词字数（经验值 ~4.5 字/秒），别硬拉语速")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
