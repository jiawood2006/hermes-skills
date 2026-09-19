#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配音一致性检查：量各段音频的中位基频(F0)，判断分段生成是否"换了嗓"。

用法：
    python3 voice_consistency_check.py seg1.mp4 seg2.mp4 seg3.mp4
    python3 voice_consistency_check.py --ref voice_ref.mp3 seg1.mp4 seg2.mp4   # 带参考音对比

判据（2026-09-16 实测标定）：
    段间差 >15%  → 人耳能听出不连贯，必须锁 reference_voice 重跑
    实测：未锁 = 125/168/154Hz（差 23~35%，用户当场指出「配音要考虑好」）
          锁后 = 130/146/137Hz（差 ≤12%，参考音 136Hz）

退出码：0 = 一致；1 = 不一致（需重跑）；2 = 输入/依赖问题
"""
import os
import subprocess
import sys
import wave

import numpy as np

FFMPEG = os.path.expanduser("~/video-tools/bin/ffmpeg")
THRESHOLD_PCT = 15.0
# 人声基频搜索范围：70~400Hz
F0_MIN, F0_MAX = 70, 400
SR = 16000
FRAME = int(0.04 * SR)
HOP = int(0.02 * SR)
ENERGY_GATE = 0.02
CORR_GATE = 0.3


def to_wav(src, dst):
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", src,
                    "-vn", "-ar", str(SR), "-ac", "1", dst], check=True)
    return dst


def median_f0(wav_path):
    """40ms 帧自相关 + 能量门限 → 有声帧的基频中位数。"""
    w = wave.open(wav_path)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    voiced = []
    lo, hi = int(SR / F0_MAX), int(SR / F0_MIN)
    for i in range(0, len(x) - FRAME, HOP):
        s = x[i:i + FRAME]
        if float(np.sqrt((s ** 2).mean())) < ENERGY_GATE:
            continue
        s = s - s.mean()
        c = np.correlate(s, s, "full")[FRAME - 1:]
        if hi >= len(c):
            continue
        p = int(c[lo:hi].argmax()) + lo
        if c[p] > CORR_GATE * c[0]:
            voiced.append(SR / p)
    return (float(np.median(voiced)) if voiced else 0.0), len(voiced)


def main(argv):
    ref = None
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--ref":
            ref = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if len(args) < 2:
        print(__doc__)
        return 2

    tmpdir = "/tmp/voice_consistency"
    os.makedirs(tmpdir, exist_ok=True)

    ref_f0 = None
    if ref:
        ref_f0, n = median_f0(to_wav(ref, f"{tmpdir}/_ref.wav"))
        print(f"[参考音] {os.path.basename(ref):28s} 中位F0={ref_f0:6.1f}Hz  有声帧={n}")

    results = []
    for idx, path in enumerate(args, 1):
        wav = to_wav(path, f"{tmpdir}/seg{idx}.wav")
        f0, n = median_f0(wav)
        # 段长（顺带核一下有没有被 -shortest 之类截断）
        dur = subprocess.run([os.path.expanduser("~/video-tools/bin/ffprobe"), "-v", "error",
                              "-show_entries", "format=duration", "-of", "csv=p=0", path],
                             capture_output=True, text=True).stdout.strip()
        results.append((path, f0, n, float(dur or 0)))
        delta = "" if ref_f0 is None else f"  (vs 参考音 {100*abs(f0-ref_f0)/ref_f0:+.1f}%)"
        print(f"  {os.path.basename(path):28s} 中位F0={f0:6.1f}Hz  有声帧={n:4d}  时长={dur}s{delta}")

    f0s = [r[1] for r in results if r[1] > 0]
    if len(f0s) < 2:
        print("有声帧不足，无法比较（检查是否有音轨）")
        return 2
    base = min(f0s)
    worst = 100.0 * (max(f0s) - base) / base
    print(f"\n段间最大差 = {worst:.1f}%  (阈值 {THRESHOLD_PCT}%)")
    if worst > THRESHOLD_PCT:
        print("❌ 不一致 → 每段随机换嗓。修法：给人物参考图挂 reference_voice（同一份 mp3，≤10s）后重跑。")
        return 1
    print("✅ 音色一致（分段生成已锁音色）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
