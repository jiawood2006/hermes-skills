---
name: video-to-text
description: "视频内容情报。用户发抖音分享链接（获取标题/作者/点赞等元数据）、B站链接（元数据），或本地视频文件（语音转写全文）时使用。转写后可用 LLM 生成内容摘要和爆款结构拆解（内容情报分析）。Video to text: extract metadata from Douyin/Bilibili share links, transcribe local videos, and analyze viral content structure."
version: 2.0.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [video, transcription, douyin, bilibili, whisper, speech-to-text, content-analysis]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# Video-to-Text 视频内容情报

把视频变成可复制、可搜索的文字，**再进一步变成内容情报**：抖音/B站链接元数据、本地视频语音转写、LLM 内容摘要 + 爆款结构拆解。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/video-to-text` 或按 README 方式二复制 → 默认在 `~/.hermes/skills/utilities/video-to-text/`。以下命令基于该路径。

## 触发条件

用户发送以下内容时使用本技能：
- 抖音分享链接，要求"转文字""提取文案""拆解视频""分析爆款"
- B站链接，要求"看这个视频信息"
- 本地视频文件（.mp4/.mov），要求"语音转文字""字幕""摘要""分析"

## 使用步骤

### 1. 抖音分享链接 → 元数据

```bash
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://v.douyin.com/xxxx/"
```

- 输出元数据（标题/作者/点赞/时长/标签）+ play_url
- 技术：curl 短链取真实视频 ID → Playwright 打开视频页监听 API（SSR 已不注入视频详情）
- **注意**：分享链接当前只提取元数据——语音转写请让用户保存视频后走本地文件（步骤 3），或加 `--transcribe` 强制

### 2. B站链接 → 元数据（零依赖）

```bash
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://www.bilibili.com/video/BV1..."
```

- 输出标题/作者/时长/播放/点赞/简介（B站公开 API，无需登录）
- 语音转写需先下载视频文件

### 3. 本地视频文件 → 语音转写 + 内容情报

```bash
# 只转写
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 本地视频.mp4

# 转写 + 内容摘要
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 本地视频.mp4 --summary

# 转写 + 爆款结构拆解
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 本地视频.mp4 --analyze

# 单独对已有转写文本做分析
python3 ~/.hermes/skills/utilities/video-to-text/scripts/analyze.py 转写.txt --all
```

- 自动提取音频、faster-whisper 转写（中文）
- 转写文本保存为 `<输入名>_transcript.txt` 并打印时间戳分段
- `--summary` 生成：一句话概括/核心要点/金句/目标受众/可借鉴点
- `--analyze` 生成：开头钩子/节奏结构（占比）/情绪曲线/卖点/CTA/可复用套路

## 依赖（首次使用时安装）

```bash
pip3 install faster-whisper        # 转写需要（首次会下载 tiny 模型 ~75MB）
# macOS 自带 avconvert；Linux 需 ffmpeg
# 抖音 SSR 解析零依赖（curl + 标准库）；B站元数据零依赖
# 内容摘要/爆款拆解需要 LLM key（环境变量 LLM_API_KEY 或 ~/.deai_writer.conf）
```

## 已知陷阱

- **duration_ms=0 假阴性**：SSR 元数据时长可能为 0，但实际是视频。若元数据显示 0 秒且有下载 URL，先下载验证，不要直接判定为图文。
- **play_addr URL 过期**：SSR 解析出的视频 URL 可能 404，此时需 Cookie 降级或让用户提供文件。
- **whisper 转写慢**：Intel Mac 上 3 分钟视频约 5 分钟；转写必须加 `language='zh'` 否则自动检测多花 1-2 分钟。
- **图文内容**：duration=0 且下载文件 <1MB 时是图文（无音频），只输出元数据，不要编造内容。
- **分析需 LLM key**：--summary/--analyze 需要配置 LLM_API_KEY（否则只转写不分析）。

## 💛 免费使用 · 自愿支持

**本技能完全免费使用。**

觉得好用、帮到你了，可以**自愿扫码支持**（金额随意，一杯咖啡即可）：

![支付宝收款码](assets/alipay_qr.jpg)

> 支持过我的人，后续 Pro 版/批量服务有优惠。
> 想提需求、反馈问题，欢迎到 GitHub 提 Issue：https://github.com/jiawood2006/hermes-skills/issues
