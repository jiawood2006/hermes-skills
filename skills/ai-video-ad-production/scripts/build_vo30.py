#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成整片旁白轨（VO）：每条台词按字幕落点逐句 TTS，拼成一条贯穿全片的音轨。

用法:
    build_vo30.py [voice] [rate] [outname]
    build_vo30.py zh-CN-YunxiNeural "+5%" vo30.mp3

前提: <workdir>/overlay_cfg.json 里有 {"subs":[{"text":..., "start":...}, ...]}
（本脚本用字幕的 start 当旁白落点，保证旁白与字幕对齐）

实测要点:
- edge-tts 会间歇性 NoAudioReceived（连续请求被限流）→ 必须重试（下面最多 6 次，退避 4~7s）
- amix 必须 normalize=0，否则电平被压小
- 音色基频参考: 云希 YunxiNeural≈168Hz(年轻) / 云扬 YunyangNeural≈129Hz(成熟播报)
"""
import os, subprocess, sys, json, time

D = os.environ.get("VO_WORKDIR", "/tmp/r2v")          # 改这里或用 VO_WORKDIR 指到你的工程目录
FF = os.environ.get("FFMPEG", os.path.expanduser("~/video-tools/bin/ffmpeg"))
TTS = os.environ.get("EDGE_TTS", os.path.expanduser("~/.hermes/hermes-agent/venv/bin/edge-tts"))
DUR = float(os.environ.get("VO_DURATION", "30"))       # 成片总时长（秒）

voice = sys.argv[1] if len(sys.argv) > 1 else "zh-CN-YunxiNeural"
rate = sys.argv[2] if len(sys.argv) > 2 else "+5%"
out = sys.argv[3] if len(sys.argv) > 3 else "vo30.mp3"
if not os.path.isabs(out):
    out = os.path.join(D, out)

cfg = json.load(open(f"{D}/overlay_cfg.json"))
lines = [(s["text"], s["start"]) for s in cfg["subs"]]
work = f"{D}/vo_parts"
os.makedirs(work, exist_ok=True)

mp3s = []
for i, (text, start) in enumerate(lines):
    p = f"{work}/l{i}.mp3"
    ok = False
    for attempt in range(6):
        try:
            subprocess.run([TTS, "--voice", voice, f"--rate={rate}", "--text", text, "--write-media", p],
                           check=True, capture_output=True, text=True)
            ok = True
            break
        except subprocess.CalledProcessError as e:
            print(f"  retry{i}.{attempt}: {(e.stderr or '')[-160:]}")
            time.sleep(4 + attempt * 3)
    if not ok:
        raise SystemExit(f"TTS failed for line{i}: {text}")
    mp3s.append((p, start))
    print(f"  line{i} @{start}s : {text}")

inputs = ["-f", "lavfi", "-t", str(int(DUR)), "-i", "anullsrc=r=44100:cl=stereo"]
for p, _ in mp3s:
    inputs += ["-i", p]

fc, mix = [], []
for i, (_, start) in enumerate(mp3s, start=1):
    ms = int(round((start + 0.05) * 1000))               # 比字幕起点晚 50ms，听感更自然
    fc.append(f"[{i}:a]aresample=44100,adelay={ms}|{ms}[a{i}]")
    mix.append(f"[a{i}]")
fc.append("[0:a]" + "".join(mix) + f"amix=inputs={len(mp3s)+1}:normalize=0:duration=first[aout]")

cmd = [FF, "-loglevel", "error", "-y"] + inputs + ["-filter_complex", ";".join(fc),
      "-map", "[aout]", "-t", str(int(DUR)), "-c:a", "libmp3lame", "-b:a", "192k", out]
r = subprocess.run(cmd, capture_output=True, text=True)
print("EXIT", r.returncode)
print(r.stderr[-1200:] if r.returncode else f"OUT {out} {os.path.getsize(out)} bytes")

# 复核建议：voice_stt_local.py 转写这条音轨，确认 6 句都在、没有静音段
