# 配音音色验证：基频一致 ≠ 音色一致（2026-09-16 实测）

## 先看这条
分段生成的成片，**必须做两道音色检查**。只量基频会得出"已收敛"的**错误结论**：
- ① 基频（F0）中位数：段间差 >15% 报警 → `scripts/voice_consistency_check.py`
- ② **谱相似度（LTAS cosine）**：对"我方真 TTS 配音"≥0.94 = 同一把嗓子；0.85~0.92 = 实际换了个人
  → `scripts/voice_timbre_similarity.py`

## 实测数据（HSQ1 30s，万相 `wan2.7-r2v`，3×10s 段）

| 对比 | 谱相似度 | 判读 |
|---|---|---|
| 云扬 vs 云扬（同人上限，不同文本/批次） | 0.948 | 基准上限 |
| 云健 vs 云扬（不同人） | 0.898 | 不同人基准 |
| 云希 vs 云扬（不同人） | 0.801 | 不同人基准 |
| seg1（prompt 挂 `reference_voice`，模型"模仿"） | 0.892 | ≈ 云健 → **换了个人** |
| seg2（同上） | 0.836 | 介于两人之间 → **又一个人** |
| seg3（我方 edge-tts 真配音） | 0.986 | ✓ 同一把嗓子 |

同一轮基频：旧版 125 / 168 / 154 Hz（段间差 23~35%）→ 锁音色后 130 / 146 / 137 Hz（差 ≤12%）。
**结论：基频已经"看起来收敛"，音色其实还是三把嗓子。** 用户听出来的原话是「配音要考虑好」。

## 判定尺度
谱相似度对"同性别男声"是**弱判别**：一定要和**同轮测出的"不同人基准"**比，不要用绝对阈值。
真配音（同一 TTS 引擎 + 近似文本）能到 0.98+；模型"模仿"很难超 0.90。

## 正确收口做法（2026-09-16 定型）
1. **音色先定死**：同一条台词用各候选音色合成一遍 → 量基频 → **发样本给用户挑**（别自己默认）
   —— edge-tts 男声实测基频：云健 122Hz（低沉磁性）/ 云扬 136Hz（专业播报·商务题材默认）/ 云希 182Hz（年轻清亮）
2. **三段全部换我方 edge-tts 配音**（`scripts/replace_segment_audio.py`：按时间轴铺 VO + `apad=whole_dur` 补满段长）
3. **有正脸说话镜头的段**再走 `videoretalk` 重对口型（`scripts/videoretalk_submit.py`，0.08 元/秒，1800s 免费）
4. 复核：`ffprobe` 段长恢复原值 + STT 只剩我们写的句子 + 上面两道音色检查

## videoretalk 要点（实测）
- `POST /api/v1/services/aigc/image2video/video-synthesis`，`model=videoretalk`，
  `input:{video_url, audio_url}`，`parameters:{video_extension:false}`，头 `X-DashScope-Async: enable`
- **`video_url` / `audio_url` 都必须是公网可访问 URL**（本项目先 `scp ... yunvela:/opt/yunvela-site/dh/`，
  再 `curl -o /dev/null -w '%{http_code}'` 确认 200）
- `audio_url` 传**纯旁白轨**（我方 TTS），并按该段**精确段长**用 `apad=whole_dur=<段长>` 补满，
  否则输出时长会被音频截短
- 输出 720P；**连续提交会 429 `Throttling.RateQuota`** → 等 ~45s 重试即可（不是配额用完）
- **无正脸的段**（纯手部/产品特写）**不需要 videoretalk**，直接铺旁白

## 相关
- `references/voice-consistency-and-subtitle-sync.md` — `reference_voice` 字段用法、≤10s 硬限制、字幕时间轴、换音轨配方
