# 配音一致性 + 字幕时间轴 + 音色验证（本篇是配音/字幕的唯一口径）

**这篇管什么**：整片旁白（VO）怎么定音色、怎么按字幕落点生成、怎么验音色、字幕时间轴从哪来、交付前核对什么。
**什么时候读**：写/改旁白、换音色、怀疑「配音换人」、改字幕时间轴、交付前最后一次核对 —— 动到配音或字幕层就通读一遍。

**一句话定稿口径**：分段生成会各自换嗓音，所以**全片必须统一画外旁白**（云希 `zh-CN-YunxiNeural`，`rate +5%`），
**不做口型对齐**；旁白按字幕 `start` 排 TTS（`scripts/build_vo30.py`），`VO_DURATION` 必须等于成片总长，
`amix` 必须 `normalize=0`；分段成片**必须做两道音色检查**（只量基频会得出「已收敛」的错误结论）；交付前必须核对字幕时间轴与旁白落点。

❌ 已作废（2026-09-17）：R2V 自带人声 + `videoretalk` 重对口型（旧文档称「口型严丝合缝」是卖点）→ 现：全片统一画外旁白，**不做口型对齐**。
❌ 已作废（2026-09-16）：给人物参考图挂 `reference_voice` 让模型「模仿」即可统一音色 → 现：分段模仿不可信（只让基频接近，音色仍各段不同），全片换我方 TTS 旁白。

## 一、统一旁白策略

**病根**：r2v/t2v **每提交一段就独立生成一次配音**，模型每次都换一个嗓音 —— 单看每段都正常，连起来"像换了三个人"。
用户听出来了，原话「**配音要考虑好**」。

**关键洞察：「对口型」本身就是最大的"假感"来源。** 用户自己的标杆样片走的是
**画外旁白（VO）＋生活抓拍**，全片**没有人对着镜头念台词**（样片音频转写是"每天最治愈的十分钟是给女儿吹头发…"）；
我们 v11 的错法是全程对着镜头说话＋对口型。

做法：
- **一条贯穿全片的旁白轨**，不要逐段换音轨、不要跑 videoretalk —— 旁白天然连贯（不会像逐段配音那样"换人"），也彻底省掉对口型环节。
- **视频 prompt 里把台词拿掉**：R2V 只要看到引号里的台词就会开口型。旁白版只在 prompt 里写动作、不写台词，并写死
  「【人物】全程不说话、不做口型、不面对镜头念台词；神情自然放松（低头微笑或专注手上动作），像被抓拍到的生活瞬间」。
- **无正脸镜头**（水洗/充电/收包/纯产品特写）**不需要口型对齐**，直接铺旁白；旧路线里"有正脸说话镜头才走 videoretalk"的分支已被统一旁白取代。
- 音色取向：生活化第一人称旁白用**年轻声线**（云希）更贴；但**两条都要发用户听再定**，别自己拍板。

## 二、TTS 生成与落点（`scripts/build_vo30.py`）

```bash
python3 scripts/build_vo30.py zh-CN-YunxiNeural "+5%" vo30.mp3   # 逐句 TTS 按字幕落点拼成整条音轨
```

- 默认值就是 `voice=zh-CN-YunxiNeural` / `rate=+5%` / `out=vo30.mp3`；`make_ad.py` 以自己的配置调用它
  （`cfg.get("vo_voice","zh-CN-YunxiNeural")`、`cfg.get("vo_rate","+5%")`）。
- **前提**：`<workdir>/overlay_cfg.json` 里有 `{"subs":[{"text":…,"start":…}, …]}`。
  脚本**用字幕的 `start` 当旁白落点**（实际 `adelay` 比字幕起点晚 50ms，听感更自然）→ 旁白与字幕**天生对齐**。
  所以：**旁白落点 = 字幕 `start`，不要凭猜改时间轴。**
- 环境变量：`VO_WORKDIR`（默认 `/tmp/r2v`）、`VO_DURATION`（默认 30，**成片总时长**；`make_ad.py` 传 `cfg["total"]`）、
  `FFMPEG`（默认 `~/video-tools/bin/ffmpeg`）、`EDGE_TTS`（默认 `~/.hermes/hermes-agent/venv/bin/edge-tts`）。
  **`VO_DURATION` 必须等于成片总长**，短了旁白被截、长了成片尾巴多一段静音。
- 实现：逐句 `edge-tts --voice V --rate=R --text T --write-media p` → `aresample=44100,adelay={ms}|{ms}`
  → 叠到 `anullsrc=r=44100:cl=stereo -t DUR` 静音底上 → `amix=inputs=N+1:normalize=0:duration=first` → `-t DUR` 输出 `libmp3lame -b:a 192k`。
- ⚠️ **`amix` 必须 `normalize=0`，否则电平被压小。**
- 装配：三段视频 concat（**不要** concat 它们的音频），音频单独 map 这条 VO：
  `[vo:a]aresample=44100,apad=whole_dur=30.5[aout]`，最后 `-shortest`。
- 复核建议：用 `voice_stt_local.py` 转写这条音轨，确认 6 句都在、没有静音段。

### 音色基频参考（edge-tts，两批实测都保留）

| voice | 基频 | 性格 |
|---|---|---|
| `zh-CN-YunjianNeural` 云健 | 122 Hz | 低沉磁性 |
| `zh-CN-YunyangNeural` 云扬 | 136 Hz | 专业播报（商务题材默认） |
| `zh-CN-YunxiNeural` 云希 | 182 Hz | 年轻清亮 |

另一批实测（`build_vo30.py` 头注 / 写实旁白路线）：云希 `zh-CN-YunxiNeural` ≈ **168Hz**（年轻自然）/ 云扬 `zh-CN-YunyangNeural` ≈ **129Hz**（成熟播报）。
→ 两批数值有差，判定时**用同轮自己量出来的基准**比，不要跨文档套绝对数。
定音色做法：**同一条台词**分别合成 → 量基频 → **发样本给用户挑**（用户偏好先看样本再定；换音色重跑成本很低，别自己拍板不说）。

### 坑

- **edge-tts 会间歇性 `NoAudioReceived`**（连续快速请求被限流网络抖动）。必须**重试**：`build_vo30.py` 单句最多 6 次、
  退避 `4 + attempt*3` 秒（4~7s）；实测 6 句里会有 1~2 句首次失败，重试后全部成功。用 `capture_output=True` 把 stderr 收下来打日志，
  否则只看到 exit 1 不知道原因；重试后校验产物 **>2KB**。
- ⚠️ **`--rate` 必须用等号形式**：`--rate=+5%` ✓；`--rate "+5%"` ✗（直接非零退出，报参数错）。
- **多产品并行必须各用各的 `workdir`**：`AD_TMP` / `VO_WORKDIR` 要跟随 workdir，否则 overlay PNG 落到同一个 `/tmp/r2v` 互相覆盖，15s 版会复用错图。
- **VO 输入必须追加在 overlay 输入之后**：overlay 的输入序号靠 `len(inputs)//2` 定位，中间插一个音频会让后面所有 overlay 索引错位。
- **用 VO 时不要生成段内音频链**：未消费的 filter 输出会被 ffmpeg 判为未连接而报错。

## 三、音色校验两道关（基频一致 ≠ 音色一致）

分段生成的成片，**必须做两道音色检查**。只量基频会得出"已收敛"的**错误结论**：

- ① **基频（F0）中位数**：段间差 >15% 报警 → `scripts/voice_consistency_check.py <seg1.mp4> <seg2.mp4> …`
- ② **谱相似度（LTAS cosine）**：对"我方真 TTS 配音" ≥0.94 = 同一把嗓子；0.85~0.92 = 实际换了个人
  → `scripts/voice_timbre_similarity.py`

### 实测数据（HSQ1 30s，万相 `wan2.7-r2v`，3×10s 段）

| 对比 | 谱相似度 | 判读 |
|---|---|---|
| 云扬 vs 云扬（同人上限，不同文本/批次） | 0.948 | 基准上限 |
| 云健 vs 云扬（不同人） | 0.898 | 不同人基准 |
| 云希 vs 云扬（不同人） | 0.801 | 不同人基准 |
| seg1（prompt 挂 `reference_voice`，模型"模仿"） | 0.892 | ≈ 云健 → **换了个人** |
| seg2（同上） | 0.836 | 介于两人之间 → **又一个人** |
| seg3（我方 edge-tts 真配音） | 0.986 | ✓ 同一把嗓子 |

同一轮基频：旧版 125 / 168 / 154 Hz（段间差 23~35%）→ 锁音色后 130 / 146 / 137 Hz（差 ≤12%）。
**结论：基频已经"看起来收敛"，音色其实还是三把嗓子。**

### 判定尺度

谱相似度对"同性别男声"是**弱判别**：一定要和**同轮测出的"不同人基准"**比，不要用绝对阈值。
真配音（同一 TTS 引擎 + 近似文本）能到 0.98+；模型"模仿"很难超 0.90。

### 方法论坑（踩过）

**跨段不同台词做"谱相似度"比对无效** —— 差异由台词内容主导，不是音色，会得出"音色不一致"的错误结论。
必须**同一句话**分别合成/抽取后比对才有判据意义。

## 四、字幕时间轴与交付核对

### 时间轴从哪来

1. STT 取真实句子边界：`WhisperModel("small").transcribe(wav, language="zh", word_timestamps=True, vad_filter=False)`
   → 用 `words[0].start / words[-1].end` 定句起止。
   ⚠️ `vad_filter=True` 会把相邻句**并成一大段**（实测 seg2 两句被报成一个 `[10.0-19.7]`），**别用它定时轴**。
   现成实现：`scripts/stt_dialogue_check.py --words seg2.mp4`。
2. 全局时间 = 段起始偏移 + 段内时间。
3. 花字层：PIL 生成 1080×1920 **透明 PNG**（字幕条/卖点 chip/价格块/参数条/合规标注），
   ffmpeg `overlay=0:0:enable='between(t,a,b)'` 逐层叠加（比 `drawtext` 稳/好排版，合成后放大没锯齿）。**PNG 命名要统一**。
4. 复核：按新时间轴中点 `-ss` 精确抽 **6 帧**拼图肉眼确认（每次都要做，别省）。
   `-ss` 必须放在 `-i` **前面**才是精确定位。现成实现：`scripts/assemble_r2v_overlays.py --sync out.mp4 2.0,5.5,15.0,18.0,22.0,25.0`。

**假警报**：用 `fps=1/3.75` 抽样拼图判断"字幕早了 1 秒多"是**错的** —— 抽样帧的时间标签与实际时间并不对应，
据此改时间轴 = 白改。**只用精确抽帧。**

### 台词反查的判据

- 跑 STT 逐段反查：出现我们没写的句子 = 乱码 → 该段音频要换掉。
  实测 3 段里 seg3 除了我们的台词还多说了「早上洗是在」「乘梯电圣人宋史诗」等乱码句（prompt 写了"台词只说一遍"仍会出现）。
- **同音字属正常**（刮→挂、八千五百→8500），**只有整句语义乱掉才算失败**；别为同音字反复重跑烧钱。

### 交付前必查清单（v3 实测通过）

| 项 | 判据 |
|---|---|
| 台词 | 逐段 STT = 我们写的句子，**没有模型自己多说的乱码句** |
| 音色 | 各段音频 vs 我方 TTS **同内容**相似度 ≥0.99（配合第三节两道关） |
| 字幕 | **旁白落点 = 字幕 `start`** 已核对；时间轴随配音变化 → **必须重做**，再按新时间轴中点抽 6 帧拼图肉眼确认 |
| 口型 | 仅旧 videoretalk 路线适用：抽帧确认嘴部无重绘痕迹、产品仍清晰在场景里；统一旁白路线无此步 |

### 发飞书（媒体交付）

- mp4 → `msg_type=media` ✓；**mp3 → 只有 `msg_type=file` 能发成功**（`audio` / `media` 均 HTTP 400，实测）。
  `~/.hermes/scripts/feishu_send_media.py` 已按扩展名自动选 `file_type`（mp4/stream）与 `msg_type`。
- 发完**回读消息列表**确认送达（脚本回显 ≠ 送达）：`im/v1/messages?container_id_type=chat&…&sort_type=ByCreateTimeDesc`，
  媒体消息在列表里显示为 `nonsupport`（正常，代表视频/音频已送达）。
- ⚠️ **读日志别读错**：`文字: 0 success` / `视频: 0 success` 里 **`0` 是飞书成功码**（`msg=success`），不是"0 条成功"。
  判成功看 `dict.get("code") == 0`。

## 旧路线存档（已被统一旁白覆盖，仅排查历史成片时用）

### `reference_voice` 锁音色

```json
{"type": "reference_image", "url": "<人物图>", "reference_voice": "https://<公网>/voice_man.mp3"}
```

- ⚠️ **硬限制：mp3 时长 ≤10 秒**。超了异步任务直接被拒：
  `InvalidParameter: <url> duration should be at most 10s, got 12.384s`（实测）。生成参考音控制在 **8~9 秒**（edge-tts 读 4 句 ~8.7s 正好）。
- 参考音内容无所谓（只取音色），但要是**平静陈述句**，别用喊的。
- ❌ 效果作废原因见第三节：模型只是在"模仿"，只让基频接近，音色仍各段不同（0.892 / 0.836）。

### videoretalk 重对口型

- `POST .../services/aigc/image2video/video-synthesis`
  `{"model":"videoretalk","input":{"video_url":<公网 mp4>,"audio_url":<公网 mp3>},"parameters":{"video_extension":false}}`，
  头 `X-DashScope-Async: enable`。
- ⚠️ **模型 id 就是 `videoretalk`**（不是 `wan2.2-videoretalk`），端点必须是 **`image2video/video-synthesis`**
  —— 写成 `video-generation/video-generation` 会返回 `InvalidParameter: Model not exist.`（2026-09-17 又踩一次）。
- 价：**0.08 元/秒，1800 秒免费额度**；输出 720P/30fps，体积约为源片 1/3（重编码，画质可接受）。
- **`video_url` / `audio_url` 都必须是公网可访问 URL**（本项目先 `scp … yunvela:/opt/yunvela-site/dh/`，
  再 `curl -o /dev/null -w '%{http_code}'` 确认 200）。
- `audio_url` 传**纯旁白轨**，并按该段**精确段长**用 `apad=whole_dur=<段长>` 补满，否则输出时长会被音频截短。
- 实测：videoretalk **原样保留我方音频**（同内容谱相似度 = **1.000**，F0 与我方配音一致），只重做口型。
- **连续提交会 429 `Throttling.RateQuota`** → 等 ~45s 重试即可（不是配额用完）。

### 替换段音轨的标准配方（`scripts/replace_segment_audio.py`）

```bash
# 1) 每句 TTS
edge-tts --voice zh-CN-YunyangNeural --rate=+8% --text "全身水洗，冲一冲就干净。" --write-media va0.mp3
# 2) 按时间轴铺开 + 补满段长
ffmpeg -y -i va0.mp3 -i va1.mp3 -filter_complex \
 "[0:a]adelay=300|300[a0];[1:a]adelay=4800|4800[a1];\
  [a0][a1]amix=inputs=2:duration=longest:normalize=0,atrim=0:10.03,apad=whole_dur=10.03[aout]" \
 -map "[aout]" -ar 44100 -ac 2 seg3_voice.wav
# 3) 换音轨（视频流直接 copy）
ffmpeg -y -i v2_seg3.mp4 -i seg3_voice.wav -map 0:v -map 1:a \
 -c:v copy -c:a aac -b:a 192k v2_seg3_vo.mp4      # ⚠️ 不要加 -shortest
```

- **坑①** `apad` 不带参数 = 无限静音流 → 编码器挂死（写出十几 MB 无 moov 文件，`-t`/`-shortest` 不必然终止）。必须 `apad=pad_dur=X` 或 `apad=whole_dur=X`。
- **坑②** 加了 `-shortest` 会把**视频**截到音轨长度：实测音轨只到 7.18s（amix 取最长句末），视频 10.03s 被截成 7.18s ✗。
  先 `apad=whole_dur=<段长>` 补满，再**去掉 `-shortest`**。
- 换完必须复核：`ffprobe` 段长是否恢复 10.00s + STT 是否只剩我们写的句子。
- 旧版音频矩阵（影棚路线遗留）：`0=anullsrc 静音底, 1..N=TTS(adelay, volume=1.2), N+1=BGM(volume=0.10)`
  → `amix=inputs=N+2:normalize=0` → `alimiter=limit=0.95`；画面取用加 `-an`（丢弃万相自带音频）。

❌ 已作废：旁白语速按镜头/段调（旧文档中的 `+10%` / `+18%`）→ 现：全片统一 `zh-CN-YunxiNeural` + `--rate=+5%`（`build_vo30.py` / `make_ad.py` 默认）。

## 相关

- 装配与项目字段：`../SKILL.md`、`scripts/make_ad.py`、`references/pipeline-assembly-and-qc.md`
- 写实旁白路线（VO＋抓拍，样片对标）：`references/scene-drama-and-candid-style.md`
- 校验脚本：`scripts/voice_consistency_check.py` / `scripts/voice_timbre_similarity.py` / `scripts/stt_dialogue_check.py` / `scripts/build_vo30.py` / `scripts/replace_segment_audio.py`
