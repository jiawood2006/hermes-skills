---
name: video-to-text
description: '视频内容情报。用户发抖音分享链接（自动下载+语音转写全文）、B站链接、或本地视频文件时使用。转写后可用 LLM 生成内容摘要和爆款结构拆解。Video to text: Douyin link → auto download → transcribe → viral-content analysis in one command.'
version: 3.0.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [video, transcription, douyin, bilibili, whisper, sensevoice, speech-to-text, content-analysis]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# Video-to-Text — 抖音/本地视频 → 文字 → 内容情报（一条命令闭环）

**抖音分享链接 → 自动下载 → 语音转写 → 结构化 Markdown → 爆款拆解，一条命令跑完。** 不用手动存视频、不用第三方 API key、隐私不出本机（默认本地 faster-whisper）。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/video-to-text` 或 `./install.sh`（一键装+全局命令 `vtt`）→ 脚本在 `~/.hermes/skills/utilities/video-to-text/scripts/`。

## 触发条件

用户发送以下内容时使用本技能：
- 抖音分享链接（v.douyin.com / www.douyin.com/video/…），要"转文字/提取文案/拆解/分析爆款/看内容"
- B站链接，要"看视频信息"
- 本地视频文件（.mp4/.mov/.m4a），要"语音转文字/字幕/摘要/分析"

## 使用步骤

### 1. 抖音链接 → 全自动闭环（默认行为）

```bash
# 一条命令：元数据 + 自动下载 + 本地转写
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://v.douyin.com/xxxx/"

# 全流程 + LLM 摘要 + 爆款结构拆解
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://v.douyin.com/xxxx/" --all

# 只要元数据（不下不转）
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://v.douyin.com/xxxx/" --meta-only

# 转写引擎换硅基 SenseVoice（中文口语/带噪更准，需 SILICONFLOW_API_KEY，失败自动回退本地）
SILICONFLOW_API_KEY=sk-xxx python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://v.douyin.com/xxxx/" --engine sensevoice
```

技术链路：curl 短链取真实视频 ID → Playwright 监听 aweme/detail API 拿元数据+无水印 play_url → 自动下载 → 提取音频 → 转写。

### 2. 本地视频文件 → 转写 + 内容情报

```bash
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 视频.mp4                 # 只转写
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 视频.mp4 --summary       # + 内容摘要
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 视频.mp4 --analyze       # + 爆款结构拆解
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py 视频.mp4 --engine sensevoice  # 换 SenseVoice
```

### 3. B站链接 → 元数据（零依赖公开 API）

```bash
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "https://www.bilibili.com/video/BV1..."
```

输出标题/作者/时长/播放/点赞/简介；转写请下载后走本地文件。

### 4. 输出产物（结构化 Markdown）

默认保存 `<标题>_transcript.md`，可直接进 Obsidian/知识库：

```markdown
---
platform: douyin
url: https://v.douyin.com/xxx
title: 视频标题
author: 作者名
duration_s: 42
digg: 12345
date: 2026-09-04
tags: ["话题1", "话题2"]
---

# 视频标题

| 字段 | 值 |
|:---|:---|
| duration_s | 42 |
...

## 转写全文

[00:00] 大家好今天给大家…
[00:05] 这款产品…
```

### 5. 对已有转写文本做分析

```bash
python3 ~/.hermes/skills/utilities/video-to-text/scripts/analyze.py 转写.md --all
```

- `--summary` 输出：一句话概括/核心要点/金句/目标受众/可借鉴点
- `--analyze` 输出：开头钩子(0-10s)/节奏结构占比/情绪曲线/卖点/CTA/可复用套路
- `--format txt` 输出纯文本（旧格式兼容）；`--out-dir` 指定目录

## 验证（安装后自测）

```bash
# 本地文件快速自测：没有视频？用 macOS 自带语音合成一段
say -v "Ting-Ting" "大家好，这是一段测试语音" -o /tmp/t.m4a   # Linux 可跳过
python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py /tmp/t.m4a --out-dir /tmp/vtt_test
# 期望：/tmp/vtt_test 出现 *_transcript.md 且含"测试语音"附近文本
```

## 依赖（首次使用时安装）

```bash
pip3 install faster-whisper        # 默认本地转写（首次下载 tiny 模型 ~75MB）
# macOS 自带 avconvert；Linux 需 ffmpeg
# 抖音解析需 playwright + chromium（douyin_extract 内部使用）
# 内容摘要/爆款拆解需 LLM key（LLM_API_KEY 环境变量 或 ~/.deai_writer.conf）
# SenseVoice 引擎可选：SILICONFLOW_API_KEY（硅基流动，有免费额度）
```

## 已知陷阱

- **duration_ms=0 假阴性**：SSR 元数据时长可能为 0 但实际是视频。有下载 URL 先下载验证，勿直接判图文。
- **play_addr URL 过期**：SSR 解析出的视频 URL 可能 404，此时下载失败会提示手动提供文件（自动降级不中断）。
- **图文内容**：duration=0 且下载文件 <1MB 是图文（无音频），只输出元数据，不编造内容。
- **whisper 转写慢**：Intel Mac 3 分钟视频约 5 分钟；已自动 `language='zh'` + VAD 过滤静音。要更快/更准用 `--engine sensevoice`。
- **分析需 LLM key**：--summary/--analyze 需 LLM_API_KEY；未配置时只转写不分析（明确降级不报错）。

