#!/usr/bin/env python3
"""配音音色验证：基频(F0) + 谱相似度 —— 判定"锁音色"是否真的锁住了。

用法:
  python3 voice_timbre_similarity.py <参照音色.mp3|wav> <待测1.mp4|mp3> [待测2 ...]

为什么需要两个指标（2026-09-16 实测教训）:
  只量基频会得出"已收敛"的错误结论 —— 实测三段基频 130/146/137Hz(差≤12%)看起来一致，
  但谱相似度显示模型"模仿"的两段只有 0.892 / 0.836（我方真配音 0.986），听感仍是三把嗓子。
  ⚠️ 谱相似度对同性别声音是弱判别：必须**同一轮**再量一次"不同人基准"（如另两个音色互比）再下结论。

判读经验（配合同轮的不同人基准）: >=0.94 同一把嗓子 / 0.85~0.92 实际换了个人 / <0.85 明显不同人
"""
import os
import subprocess
import sys
import wave

import numpy as np

FF = os.environ.get("FFMPEG", os.path.expanduser("~/video-tools/bin/ffmpeg"))
SR = 16000


def to_mono(src, dst):
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", src, "-vn",
                    "-ar", str(SR), "-ac", "1", dst], check=True)
    with wave.open(dst) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0


def analyze(path, tmp="/tmp/_vtm"):
    os.makedirs(tmp, exist_ok=True)
    wav = os.path.join(tmp, os.path.basename(path) + ".wav")
    x = to_mono(path, wav)
    fl, hop = int(0.04 * SR), int(0.02 * SR)
    win = np.hanning(fl)
    lo, hi = int(SR / 400), int(SR / 70)
    specs, f0s = [], []
    for i in range(0, len(x) - fl, hop):
        s = x[i:i + fl]
        if np.sqrt((s ** 2).mean()) < 0.02:      # 只取有声帧
            continue
        sm = s - s.mean()
        c = np.correlate(sm, sm, "full")[fl - 1:]
        if hi < len(c):
            p = int(c[lo:hi].argmax()) + lo
            if c[p] > 0.3 * c[0]:
                f0s.append(SR / p)
        specs.append(np.abs(np.fft.rfft(s * win)))
    spec = np.mean(specs, axis=0) if specs else np.zeros(2)
    freq = np.fft.rfftfreq(fl, 1 / SR)
    centroid = float((spec * freq).sum() / spec.sum()) if spec.sum() else 0.0
    return {"spec": spec,
            "f0": float(np.median(f0s)) if f0s else 0.0,
            "centroid": centroid,
            "voiced": len(f0s)}


def sim(a, b):
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na and nb else 0.0


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    ref = analyze(argv[1])
    print(f"参照 {os.path.basename(argv[1])}: F0={ref['f0']:.0f}Hz  谱重心={ref['centroid']:.0f}Hz  有声帧={ref['voiced']}")
    print("-" * 78)
    for p in argv[2:]:
        a = analyze(p)
        s = sim(a["spec"], ref["spec"])
        if s >= 0.94:
            v = "✅ 同一把嗓子"
        elif s >= 0.85:
            v = "⚠️ 疑似换了个人（与'不同人基准'同量级）"
        else:
            v = "❌ 明显不同人"
        print(f"{os.path.basename(p):36s} F0={a['f0']:5.0f}Hz 谱重心={a['centroid']:5.0f}Hz 相似度={s:.3f} {v}")
    print("-" * 78)
    print("提醒: 再跑一次'不同人基准'（如 云健 vs 云扬 = 0.898、云希 vs 云扬 = 0.801）作为标尺。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
