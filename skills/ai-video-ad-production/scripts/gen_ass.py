"""生成花字/字幕 ASS（AI剧情片后期用；漂白字黑描边 + 黄色关键词 + AIGC 标注）。
改 SUBS / HUA / START 后直接跑，产出 ad.ass；再烧录：
  ffmpeg -y -i raw.mp4 -i BGM -filter_complex \
   "[0:v]ass=ad.ass[v];[0:a]volume=1.0[a0];[1:a]volume=0.12,atrim=0:30,asetpts=N/SR/TB[bg];[a0][bg]amix=inputs=2:duration=first[a]" \
   -map "[v]" -map "[a]" -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart ad_final.mp4
拼接：printf "file 'seg1.mp4'\nfile 'seg2.mp4'\nfile 'seg3.mp4'\n" > cat.txt
      ffmpeg -y -f concat -safe 0 -i cat.txt -c copy raw.mp4      # 各段同规格才能 -c copy
BGM：~/video-tools/MoneyPrinterTurbo/resource/songs/output*.mp3（180s）
字体：~/video-tools/MoneyPrinterTurbo/resource/fonts/MicrosoftYaHeiBold.ttc
"""
OUT = "/tmp/ad_ai"
FONT = "/Users/luanhaoyu/video-tools/MoneyPrinterTurbo/resource/fonts/MicrosoftYaHeiBold.ttc"
W, H = 720, 1280                     # 按成片分辨率改
START = [0.0, 10.0, 20.0]            # 每段拼接起点
TOTAL = 30.0
# (段序号, 起, 止, 文本) —— 台词字幕（\n 手动断行，与配音时长对齐）
SUBS = [
    (0, 0.3, 3.6, "这箱剃须刀我给你二弟留着了啊"),
    (0, 3.9, 8.6, "妈！那是我给老公买的\n海尔新出的迷你款！"),
]
# (段序号, 起, 止, 文本) —— 黄色花字关键词
HUA = [
    (0, 4.0, 6.4, "海尔迷你款"),
]
TAG = "AI生成·广告"                   # 右下角常驻合规标注


def ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FONT},44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,1,0,1,4,2,2,40,40,90,1
Style: Hua,{FONT},70,&H0000E5FF,&H000000FF,&H00202020,&H80000000,1,0,0,0,100,100,2,0,1,5,3,5,40,40,150,1
Style: Tag,{FONT},30,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,2,1,1,30,30,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = [f"Dialogue: 0,{ts(START[s]+a)},{ts(START[s]+b)},Sub,,0,0,0,,{t}" for s, a, b, t in SUBS]
ev += [f"Dialogue: 1,{ts(START[s]+a)},{ts(START[s]+b)},Hua,,0,0,0,,{{\\fad(150,150)}}{t}" for s, a, b, t in HUA]
ev.append(f"Dialogue: 0,{ts(0)},{ts(TOTAL)},Tag,,0,0,0,,{TAG}")
open(f"{OUT}/ad.ass", "w").write(head + "\n".join(ev) + "\n")
print("写出", f"{OUT}/ad.ass")
