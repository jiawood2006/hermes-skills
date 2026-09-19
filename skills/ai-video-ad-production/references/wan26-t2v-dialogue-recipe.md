# 万相 wan2.6-t2v：AI 真人剧情带货片配方（2026-09-15 实测跑通）

用户样片标准 = **AI 生成的真人剧情口播片**（两位女性对话 → 展示产品 → 花字关键词）。
下面这条链路实测能复现该观感：真人 + 真实家居场景 + 多镜头 + 中文台词口型，全部由模型生成。

## 1. 账号与模型
- Key：`~/.hermes/.dashscope_key`（阿里云百炼，北京地域）
- 端点（老域名对新账号仍可用）：
  `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`
- 模型：`wan2.6-t2v`（全球，720P/1080P）、`wan2.6-t2v-us`（美国节点）
  新协议还有 `wan2.7-t2v`（默认有声、prompt 控制多镜头，无 `shot_type` 参数）
- 权限实测：本账号 `wan2.6-t2v` 可直接调用，无需开通额外服务

## 2. 计费与免费额度（官方价格页实测）
| 模型 | 分辨率 | 单价 | 免费额度 |
|---|---|---|---|
| wan2.6-t2v | 720P | **0.6 元/秒** | **50 秒** |
| wan2.6-t2v | 1080P | 1 元/秒 | 50 秒 |
| wan2.5-t2v-preview | 480P / 720P / 1080P | 0.3 / 0.6 / 1 元/秒 | 50 秒 |
| wan2.2-t2v-plus | 480P | 0.14 元/秒 | 50 秒 |

→ **首条 30 秒 720P 片可用 50 秒免费额度跑完，0 元**。失败不计费、不占额度。
按秒计费：`费用 = 单价(分辨率) × duration`。

## 3. 请求体（逐字可用）
```json
{
  "model": "wan2.6-t2v",
  "input": {
    "prompt": "写实风格家庭短剧，竖屏手机拍摄质感，自然光，真实皮肤质感。第1个镜头[0-4秒]中景：……第2个镜头[4-10秒]近景：……画面中不要出现任何文字、字幕、水印。",
    "audio_url": "https://yunvela.com/dh/seg1.mp3"
  },
  "parameters": {
    "size": "720*1280",
    "duration": 10,
    "shot_type": "multi",
    "prompt_extend": true
  }
}
```
- 头：`Authorization: Bearer <KEY>`、`Content-Type: application/json`、`X-DashScope-Async: enable`
- `size` 必须写具体数值，不能写 `9:16`：
  480P `480*832`｜720P `1280*720` / **`720*1280`(9:16)** / `960*960`｜1080P `1080*1920`(9:16)
- `duration`：枚举 5 / 10
- `shot_type:"multi"` → 一个任务内多镜头切换

## 4. 自定义台词配音（关键，决定卖点是否准确）
- 不传 `audio_url`：模型自动配音效/BGM，**并且自己编台词**（实测生成的是"…新出的剃须刀…迷你款…"——方向对但文案不可控）
- 传 `audio_url`：模型按这段音频做口型与节奏 → 卖点完全由我们掌控
- 音频限制：wav/mp3，**3~30s**，≤15MB；音频比 duration 短则剩余部分无声
- 公网托管（本机既有通路）：
  ```bash
  ~/video-tools/mpt-venv/bin/python -m edge_tts --voice zh-CN-XiaoyiNeural \
      --text "台词" --write-media /tmp/ad_ai/seg2.mp3
  scp /tmp/ad_ai/segN.mp3 yunvela:/tmp/
  ssh yunvela "sudo mv /tmp/segN.mp3 /opt/yunvela-site/dh/ && sudo chmod 644 /opt/yunvela-site/dh/segN.mp3"
  curl -s -o /dev/null -w '%{http_code}' --max-time 25 https://yunvela.com/dh/segN.mp3   # 必须 200
  ```
- 一段视频一个音轨；同一段里多人对话可用 ffmpeg `concat` 拼不同音色的 mp3（实测 8~10s 一段合适）
- 音色：`zh-CN-XiaoyiNeural`(年轻女活泼) / `zh-CN-XiaoxiaoNeural`(成熟女/阿姨) / `zh-CN-YunxiNeural`(男)

## 5. 轮询与下载
```bash
curl -s -H "Authorization: Bearer $KEY" https://dashscope.aliyuncs.com/api/v1/tasks/<task_id>
# output.task_status: PENDING → RUNNING → SUCCEEDED；成片在 output.video_url
# usage 返回 {duration, size, output_video_duration, video_count, SR}（用于核对计费）
curl -sL --retry 3 --retry-all-errors --max-time 300 -o segN.mp4 "<video_url>"   # 下载必须带 retry，易截断
```

## 6. 验片（交付前必做）
```bash
~/video-tools/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 out.mp4   # 时长
~/video-tools/bin/ffmpeg -i out.mp4 -af volumedetect -f null - 2>&1 | grep mean_volume  # 有声否
~/video-tools/bin/ffmpeg -y -i out.mp4 -vf "fps=2,scale=330:-1,tile=5x2" -frames:v 1 sheet.jpg  # 抽帧肉眼
~/video-tools/bin/ffmpeg -y -i out.mp4 -vn -ar 16000 -ac 1 a.wav
~/.hermes/hermes-agent/venv/bin/python3 ~/.hermes/scripts/voice_stt_local.py a.wav --model small --language zh --output_dir /tmp/stt
```
STT 反查是唯一能证明"说的就是我们的文案"的手段（转写有同音字误差属正常：T恤刀=剃须刀）。
本次 5 秒试片实测：画面=真人阿姨 + 年轻女性拆箱拿迷你剃须刀；音频=中文台词，转写成功。

## 7. 剧本模板（30 秒 = 3 段 × 10 秒）
- **段1 钩子**：家里客厅，阿姨抱着快递箱要给二弟 → 儿媳"那是我给老公买的，海尔新出的迷你款"
- **段2 产品**：拆箱拿出剃须刀，举到镜头前：整机70mm小巧/口袋一塞就走/8500转马达+旋转三叶刀片/硬胡茬一遍过
- **段3 收尾 CTA**：水洗干湿双剃/90天续航/智能旅行锁/海尔品牌出品 169/点下方链接
（卖点照实写；设计阶段不因"缺证据"删卖点）

## 8. 已知坑
- 提示词不写"不要出现文字"，模型可能在画面里生成乱码文字，和后期花字打架
- 多镜头段落里人物一致性会有漂移：同一段内保持同一机位/同一人物描述；跨段靠"同一人设描述"尽量对齐
- 素材拼接方案（clipforge/MPT）输出的"图+运镜"成品**会被用户判为图片拼接**，不要当 AI 视频交付
