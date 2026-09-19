#!/usr/bin/env python3
"""官方物料成片器（AI 画不准产品时的「零失真」路线）

用途：当 AI 生视频反复把产品画错（形制/比例/颜色对不上真机）时，**不再重 roll**，
改用官方物料（官方产品图 / 官方拉页图）做动效成片：产品 100% 等于真机。

用法：
  1) 写一个 JSON 清单（顺序即镜头顺序）：
     [
       {"image": "/path/拉页图-3.jpg", "line": "七厘米机身，只有七十克。", "mode": "cover"},
       {"image": "/path/prod1.png",    "line": "一百六十九，点下方链接。",  "mode": "white"}
     ]
     mode: "cover" = 官方拉页/场景图（自动模糊填充，**保证官方文案不被裁**）
           "white" = 官方产品图（白底留白，产品不裁）
  2) python3 compose_official_material_ad.py --spec spec.json --out /tmp/ad --cta "到手169元·点下方链接"

产出：<out>/official_material_ad.mp4（1080x1920，段长=配音时长+0.9s，字幕=配音原文，
      末段叠 CTA 花字，右下常驻「官方物料·广告」）

⚠️ 实测踩过的坑（改脚本时别再犯）
1. **滤镜输入下标必须与 -i 顺序一致**：音频输入（anullsrc/配音/BGM）放前面、视频片段放后面，
   否则 `Stream specifier ':a' matches no streams`。
2. **混音必须加 `-t 总时长`**：BGM 是整首歌，amix 默认取最长输入 → 不截断会输出 180s 的片子。
3. **`-loop 1` + zoompan**：每段用 `-t 段长` 限时，`d=帧数` 用 int(段长*30)。
4. **字幕别压在官方文案上**：SUB 样式用 BorderStyle=3 + 半透明底条（&H78000000）+ 小 MarginV，
   官方拉页自带的文字才是主信息。
5. 段长按配音实际时长算（edge-tts 生成后 ffprobe 测），不要写死 4s —— 否则配音被切或拖。
"""
import argparse, json, os, subprocess, sys

FF = os.path.expanduser("~/video-tools/bin/ffmpeg")
FP = os.path.expanduser("~/video-tools/bin/ffprobe")
TTS = os.path.expanduser("~/video-tools/mpt-venv/bin/python")
BGM_DEFAULT = os.path.expanduser("~/video-tools/MoneyPrinterTurbo/resource/songs/output000.mp3")
PAD = 0.9

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: SUB,MicrosoftYaHeiBold.ttc,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,3,3,1,2,50,50,78,134
Style: HUA,MicrosoftYaHeiBold.ttc,72,&H0000E5FF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,2,8,60,60,132,134
Style: TAG,MicrosoftYaHeiBold.ttc,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,3,30,40,40,134

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def dur(p):
    o = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    try:
        return float(o.strip())
    except Exception:
        return 0.0


def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def vf_for(mode, frames):
    zp = (f"zoompan=z='min(zoom+0.0006,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s=1080x1920:fps=30")
    if mode == "white":
        return "-vf", f"scale=1000:-1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:white,{zp}"
    return "-filter_complex", (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=22:2,eq=brightness=-0.08[bg];"
        "[0:v]scale=1040:1840:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{zp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default="/tmp/official_ad")
    ap.add_argument("--voice", default="zh-CN-XiaoyiNeural")
    ap.add_argument("--rate", default="-6%")
    ap.add_argument("--bgm", default=BGM_DEFAULT)
    ap.add_argument("--cta", default="")
    ap.add_argument("--tag", default="官方物料·广告")
    A = ap.parse_args()
    os.makedirs(A.out, exist_ok=True)
    clips = json.load(open(A.spec))

    voices = []
    for i, c in enumerate(clips):
        p = f"{A.out}/v{i}.mp3"
        subprocess.run([TTS, "-m", "edge_tts", "--voice", A.voice, f"--rate={A.rate}",
                        "--text", c["line"], "--write-media", p], capture_output=True, text=True)
        voices.append((p, dur(p)))
        print(f"配音{i+1}: {len(c['line'])}字 {voices[-1][1]:.2f}s  {c['line']}")

    segs, starts, acc = [], [], 0.0
    for _, d in voices:
        segs.append(round(d + PAD, 2)); starts.append(acc); acc = round(acc + segs[-1], 2)
    total = acc
    print("段长:", segs, "总时长:", total)

    for i, (c, s) in enumerate(zip(clips, segs)):
        key, vf = vf_for(c.get("mode", "cover"), int(s * 30))
        r = subprocess.run([FF, "-y", "-loop", "1", "-i", c["image"], key, vf, "-t", str(s),
                            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
                            f"{A.out}/c{i}.mp4"], capture_output=True, text=True)
        print(f"片段{i+1} {os.path.basename(c['image'])} {s}s: "
              f"{'✅' if r.returncode == 0 else '❌ ' + r.stderr[-160:]}")

    E = [ASS_HEAD]
    for i, (c, (vp, d)) in enumerate(zip(clips, voices)):
        st = starts[i] + 0.25
        E.append(f"Dialogue: 0,{ts(st)},{ts(st+d+0.35)},SUB,,0,0,0,,{{\\fad(120,120)}}{c['line']}")
    if A.cta:
        E.append(f"Dialogue: 0,{ts(starts[-1]+0.4)},{ts(total-0.4)},HUA,,0,0,0,,{{\\fad(150,150)}}{A.cta}")
    if A.tag:
        E.append(f"Dialogue: 1,{ts(0)},{ts(total)},TAG,,0,0,0,,{A.tag}")
    open(f"{A.out}/ad.ass", "w").write("\n".join(E) + "\n")

    NV = len(voices)
    ainputs = ["-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo"]
    for p, _ in voices:
        ainputs += ["-i", p]
    ainputs += ["-i", A.bgm]
    fc = [f"[{i+1}:a]adelay={int((starts[i]+0.25)*1000)}|{int((starts[i]+0.25)*1000)},volume=1.0[a{i}]"
          for i in range(NV)]
    fc.append("[0:a]" + "".join(f"[a{i}]" for i in range(NV)) +
              f"amix=inputs={NV+1}:normalize=0[amixed]")
    fc.append(f"[{NV+1}:a]volume=0.10[bg]")
    fc.append("[amixed][bg]amix=inputs=2:normalize=0,alimiter=limit=0.95[aout]")

    cin = []
    for i in range(len(clips)):
        cin += ["-i", f"{A.out}/c{i}.mp4"]
    base = NV + 2
    vfc = "".join(f"[{base+i}:v]" for i in range(len(clips))) + \
          f"concat=n={len(clips)}:v=1:a=0[vcat];[vcat]subtitles={A.out}/ad.ass[vout]"

    out = f"{A.out}/official_material_ad.mp4"
    r = subprocess.run([FF, "-y"] + ainputs + cin +
                       ["-filter_complex", vfc + ";" + ";".join(fc),
                        "-map", "[vout]", "-map", "[aout]",
                        "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                        "-t", str(total), out], capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ 合成失败:", r.stderr[-600:]); sys.exit(1)
    print(f"✅ {out}  {dur(out):.2f}s（核对：应≈{total:.2f}s，宽高 1080x1920）")


if __name__ == "__main__":
    main()
