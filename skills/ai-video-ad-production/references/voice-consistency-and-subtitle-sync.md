# 配音一致性 + 字幕时间轴（2026-09-16 用户指出「配音要考虑好」）

## 1. 病根：分段生成 = 每段随机换嗓

r2v/t2v **每提交一段就独立生成一次配音**，模型每次都换一个嗓音 —— 单看每段都正常，
连起来"像换了三个人"。用户听出来了，原话「配音要考虑好」。

**可量化取证**（项目实测，各段中位基频）：

| 段 | 旧版 | 锁音色后 |
|---|---|---|
| seg1 | 125 Hz | 130 Hz |
| seg2 | 168 Hz | 146 Hz |
| seg3 | 154 Hz | 137 Hz |
| 段间差 | **23~35%**（人耳必然听出不连贯） | **≤12%**（参考音 136Hz） |

跑 `scripts/voice_consistency_check.py <seg1.mp4> <seg2.mp4> ...` 自动量 + 判定（>15% 报警）。

## 2. 修法：`reference_voice` 锁音色

给**人物那张参考图**的 media 项挂 `reference_voice`，三段共用同一份 mp3：

```json
{"type": "reference_image", "url": "<人物图>", "reference_voice": "https://<公网>/voice_man.mp3"}
```

- ⚠️ **硬限制：mp3 时长 ≤10 秒**。超了异步任务直接被拒：
  `InvalidParameter: <url> duration should be at most 10s, got 12.384s`（实测）。
  生成参考音时控制在 **8~9 秒**（edge-tts 读 4 句 ~8.7s 正好）。
- 参考音内容无所谓（只取音色），但要是**平静陈述句**，别用喊的。

### 音色先定死再出片，别默认

用 edge-tts 可选男声（实测基频）：

| voice | 基频 | 性格 |
|---|---|---|
| `zh-CN-YunjianNeural` 云健 | 122 Hz | 低沉磁性 |
| `zh-CN-YunyangNeural` 云扬 | 136 Hz | 专业播报（商务题材默认） |
| `zh-CN-YunxiNeural` 云希 | 182 Hz | 年轻清亮 |

做法：**同一条台词**分别合成 → 量基频 → **发样本给用户挑**（用户偏好是先看样本再定；
换音色重跑成本很低，别自己拍板不说）。edge-tts 偶发 `NoAudioReceived`（网络抖动）→ 重试 2~3 次即可。

## 3. 段内出现"模型自己多说"的乱码句 → 换我方配音

实测：3 段里 seg3 除了我们的台词，还多说了「早上洗是在」「乘梯电圣人宋史诗」等乱码句
（prompt 写了"台词只说一遍"仍会出现）。做法：

- 判据：**跑 STT 逐段反查**，出现我们没写的句子 = 乱码 → 该段音频要换掉。
- 适用条件：**该段画面里没有清晰人脸**（HSQ1 seg3 全是手部特写）→ 直接铺旁白，**不需要口型对齐**。
  有正脸说话镜头才需要 `videoretalk`（0.08 元/秒，1800s 免费）。
- 现成脚本：`scripts/replace_segment_audio.py`（见第 4 节配方）。

## 4. 替换段音轨的标准配方（含两个必踩的坑）

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

- **坑①** `apad` 不带参数 = 无限静音流 → 编码器挂死。必须 `apad=pad_dur=X` 或 `apad=whole_dur=X`。
- **坑②** 加了 `-shortest` 会把**视频**截到音轨长度：实测音轨只到 7.18s（amix 取最长句末），
  视频 10.03s 被截成 7.18s ✗。先 `apad=whole_dur=<段长>` 补满，再**去掉 `-shortest`**。
- 换完必须复核：`ffprobe` 段长是否恢复 10.00s + STT 是否只剩我们写的句子。

## 5. 字幕时间轴（别靠猜）

1. STT 取真实句子边界：
   `WhisperModel("small").transcribe(wav, language="zh", word_timestamps=True, vad_filter=False)`
   → 用 `words[0].start / words[-1].end` 定句起止（`vad_filter=True` 会把相邻句**并成一大段**，别用它定时轴）。
2. 全局时间 = 段起始偏移 + 段内时间。
3. 花字层的做法：PIL 生成 1080×1920 **透明 PNG**（字幕条/卖点 chip/价格块/参数条/合规标注），
   ffmpeg `overlay=0:0:enable='between(t,a,b)'` 逐层叠加（合成后放大没锯齿，比 drawtext 好排版）。
4. 复核：按新时间轴中点 `-ss` 精确抽 6 帧拼图肉眼确认（每次都要做，别省）。

## 6. 全片"一把嗓子"的定稿做法（v3，2026-09-16 实测采用）

**关键认知**：`reference_voice` 只让**基频**接近，**音色仍各段不同** —— 模型只是在"模仿"，模仿不到位。
判据（**同内容**比对）：seg1 vs 云扬 = 0.892 / seg2 = 0.836，而不同人基准 云健 = 0.898、云希 = 0.801
→ 分段模仿等于"换了个人"。

定稿流水线：**三段全部换成我方 TTS 配音**，有正脸说话镜头的段再走 `videoretalk` 重对口型。

- 调用（`/tmp/cmp/submit_vt.py` 同款，见 skill scripts）：`POST .../services/aigc/image2video/video-synthesis`
  `{"model":"videoretalk","input":{"video_url":<公网 mp4>,"audio_url":<公网 mp3>},"parameters":{"video_extension":false}}`
  ⚠️ **模型 id 就是 `videoretalk`**（不是 `wan2.2-videoretalk`），端点必须是 **`image2video/video-synthesis`**
  —— 写成 `video-generation/video-generation` 会返回 `InvalidParameter: Model not exist.`（2026-09-17 又踩一次）。
  异步轮询同其它模型；**0.08 元/秒，1800 秒免费额度**。
- **实测：videoretalk 原样保留我方音频**（同内容谱相似度 = **1.000**，F0 与我方配音一致），只重做口型
  → 整片音色 = 我们的 TTS ✓✓。输出 720P/30fps，体积约为源片 1/3（重编码，画质可接受）。
- 无正脸镜头（水洗/充电/收包）直接换音轨即可，不必 videoretalk。
- ⚠️ **方法论坑（踩过）**：**跨段不同台词做"谱相似度"比对无效** —— 差异由台词内容主导，不是音色，
  会得出"音色不一致"的错误结论。必须**同一句话**分别合成/抽取后比对才有判据意义。

## 7. 交付前必查清单（v3 实测通过）

| 项 | 判据 |
|---|---|
| 台词 | 逐段 STT = 我们写的句子，**没有模型自己多说的乱码句** |
| 音色 | 各段音频 vs 我方 TTS **同内容**相似度 ≥0.99 |
| 字幕 | 时间轴随配音变化 → **必须重做**，再按新时间轴中点抽 6 帧拼图肉眼确认 |
| 口型 | videoretalk 段抽帧确认嘴部无重绘痕迹、产品仍清晰在场景里 |

## 8. 交付到飞书

- mp4 → `msg_type=media` ✓；**mp3 → 只有 `msg_type=file` 能发成功**（`audio` / `media` 均 HTTP 400，实测）。
  `~/.hermes/scripts/feishu_send_media.py` 已按扩展名自动选 `file_type`（mp4/stream）与 `msg_type`。
- 发完**回读消息列表**确认送达（脚本回显 ≠ 送达）：`im/v1/messages?container_id_type=chat&...&sort_type=ByCreateTimeDesc`，
  媒体消息在列表里显示为 `nonsupport`（正常，代表视频/音频已送达），文字 caption 会正常显示。
- ⚠️ **读日志别读错**：脚本打印的 `文字: 0 success` / `视频: 0 success` 里 **`0` 是飞书成功码**（`msg=success`），
  不是"0 条成功"。判成功看 `dict.get("code") == 0`。（2026-09-17 误读成失败，白折腾一轮。）
