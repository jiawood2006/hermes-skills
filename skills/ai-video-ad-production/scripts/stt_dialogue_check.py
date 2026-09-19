#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STT 反查 R2V 成片台词 + 输出逐句/词级时间轴（字幕落点就用它，别凭猜）。

背景（2026-09-16 实测）：wan2.7-r2v 会按 prompt 引号里的台词自带人声+口型，
但**不是每段都读对**。那轮 3 段里 seg2 对了，seg3 前 5 秒被转写成乱码
（「恩师温喜年 冲一冲 皆胜利冲」），后 5 秒才说对 → 该段必须重跑
（重跑时把读错的句子挪到最前 + prompt 里加「台词只说一遍，不要重复」）。

用法
----
python3 stt_dialogue_check.py seg1.mp4 seg2.mp4 seg3.mp4          # 逐句反查（含跨段时间轴）
python3 stt_dialogue_check.py --words seg2.mp4                   # 词级时间（取字幕起点用）

两个坑
------
1. `vad_filter=True` 会把相邻两句**并成一个 span**（实测整段 10s 报成一段，拿不到落点）。
   要逐句精确落点 → 用 `--words`（vad_filter=False + word_timestamps=True）读词级时间。
2. 转写出现同音字属正常（刮→挂、八千五百→8500），**判断标准是语义是否对**，
   只有整句乱码才是真缺陷，别把同音字当失败去重跑烧钱。

依赖：faster-whisper（本机已验证可用：`python3 -c "import faster_whisper"`）
"""
import json
import os
import subprocess
import sys

FF = os.environ.get("FFMPEG", os.path.expanduser("~/video-tools/bin/ffmpeg"))
FFPROBE = os.environ.get("FFPROBE", os.path.expanduser("~/video-tools/bin/ffprobe"))
TMP = os.environ.get("AD_TMP", "/tmp/r2v")


def _dur(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def _wav(path, out):
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", path, "-vn",
                    "-ar", "16000", "-ac", "1", out], check=True)
    return out


def check(segs, words=False, model_size="small", dump=None):
    from faster_whisper import WhisperModel

    m = WhisperModel(model_size, device="cpu", compute_type="int8")
    rows, offset = [], 0.0
    for i, s in enumerate(segs, 1):
        wav = _wav(s, f"{TMP}/stt{i}.wav")
        dur = _dur(s)
        it, _info = m.transcribe(wav, language="zh",
                                 vad_filter=not words, word_timestamps=words)
        print(f"--- seg{i} (dur {dur:.2f}) ---")
        if words:
            for seg in it:
                for w in seg.words:
                    print(f"  {offset + w.start:6.2f}-{offset + w.end:6.2f}  {w.word}")
                    rows.append({"seg": i, "word": w.word.strip(),
                                 "start": round(offset + w.start, 2), "end": round(offset + w.end, 2)})
        else:
            for x in it:
                line = {"seg": i, "text": x.text.strip(),
                        "start": round(offset + x.start, 2), "end": round(offset + x.end, 2)}
                print(f"  [{line['start']:.1f}-{line['end']:.1f}] {line['text']}")
                rows.append(line)
        offset += dur
    print(f"--- total {offset:.2f}s ---")
    if dump:
        json.dump(rows, open(dump, "w"), ensure_ascii=False, indent=1)
        print("json:", dump)
    return rows


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    check(args, words="--words" in sys.argv, dump=os.environ.get("STT_DUMP"))
