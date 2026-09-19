#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""替换某一段成片的音轨为我方 TTS 旁白（用于模型自己多说乱码句的段落）。

适用：该段画面**没有清晰人脸**（手部/产品/环境特写）→ 直接铺旁白，不需要口型对齐。
有正脸说话镜头才需要 videoretalk（0.08 元/秒）。

用法：
    python3 replace_segment_audio.py in.mp4 out.mp4 \
        --line "全身水洗，冲一冲就干净。@0.3" \
        --line "充一次电，能用九十天。@4.8" \
        [--voice zh-CN-YunyangNeural] [--rate +8%]

两个必踩的坑（本脚本已规避，改脚本时别改回去）：
  ① `apad` 不带参数 = 无限静音流 → 编码器挂死。必须 apad=whole_dur=<段长>。
  ② 混音输出加了 `-shortest` 会把**视频**截到音轨长度（实测 10.03s 被截成 7.18s）→ 补满段长 + 去 -shortest。

退出码：0 成功（并核过输出时长）；1 失败
"""
import argparse
import os
import re
import subprocess
import sys

EDGE_TTS = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/edge-tts")
FFMPEG = os.path.expanduser("~/video-tools/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/video-tools/bin/ffprobe")


def duration(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def tts(text, voice, rate, out_mp3, attempts=3):
    for i in range(attempts):
        r = subprocess.run([EDGE_TTS, "--voice", voice, f"--rate={rate}", "--text", text,
                            "--write-media", out_mp3], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 1000:
            return True
        # edge-tts 偶发 NoAudioReceived（网络抖动），重试即可
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--line", action="append", required=True,
                    help='格式 "台词@起始秒"，可多次；起始秒省略=0')
    ap.add_argument("--voice", default="zh-CN-YunyangNeural")
    ap.add_argument("--rate", default="+8%")
    ap.add_argument("--workdir", default="/tmp/replace_audio")
    a = ap.parse_args()

    os.makedirs(a.workdir, exist_ok=True)
    seg_dur = duration(a.src)
    if seg_dur <= 0:
        print(f"❌ 读不到 {a.src} 时长"); return 1
    print(f"源段时长 = {seg_dur:.2f}s  音色 = {a.voice}")

    lines = []
    for spec in a.line:
        m = re.match(r"^(.*?)(?:@([0-9.]+))?$", spec.strip())
        text, start = m.group(1).strip(), float(m.group(2) or 0)
        mp3 = f"{a.workdir}/vo{len(lines)}.mp3"
        if not tts(text, a.voice, a.rate, mp3):
            print(f"❌ TTS 失败: {text[:30]}（edge-tts 网络抖动，重跑一次通常就好）"); return 1
        lines.append((text, start, mp3, duration(mp3)))
        print(f"  vo{len(lines)-1}: {start:5.2f}s → {start + duration(mp3):5.2f}s  {text}")

    inputs, fc = [], []
    for i, (text, start, mp3, _) in enumerate(lines):
        inputs += ["-i", mp3]
        fc.append(f"[{i}:a]adelay={int(start*1000)}|{int(start*1000)}[a{i}]")
    mix = "".join(f"[a{i}]" for i in range(len(lines)))
    # 混音 → 裁到段长 → 补满段长（防 -shortest 截视频）
    fc.append(f"{mix}amix=inputs={len(lines)}:duration=longest:normalize=0,"
              f"atrim=0:{seg_dur},apad=whole_dur={seg_dur}[aout]")
    wav = f"{a.workdir}/vo_track.wav"
    r = subprocess.run([FFMPEG, "-loglevel", "error", "-y"] + inputs +
                       ["-filter_complex", ";".join(fc), "-map", "[aout]",
                        "-ar", "44100", "-ac", "2", wav], capture_output=True, text=True)
    if r.returncode:
        print("❌ 混音失败:", r.stderr[-800:]); return 1

    r = subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", a.src, "-i", wav,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", a.dst], capture_output=True, text=True)
    if r.returncode:
        print("❌ 换轨失败:", r.stderr[-800:]); return 1

    d = duration(a.dst)
    ok = abs(d - seg_dur) < 0.15
    print(f"{'✅' if ok else '❌'} 输出 {a.dst} 时长={d:.2f}s（源 {seg_dur:.2f}s）大小={os.path.getsize(a.dst)}")
    if not ok:
        print("   时长不一致 → 检查是否漏了 apad=whole_dur，或误加了 -shortest")
        return 1
    print("   下一步：STT 复核只剩我们写的句子（scripts/stt_dialogue_check.py）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
