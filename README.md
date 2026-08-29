# 🧰 Hermes Skills · 实用技能包 / Practical Skill Pack

> **中文**：开箱即用的 Hermes/Agent 技能集——复制目录即可安装，全部免费开源。
> **English**: Ready-to-use Hermes/Agent skills — copy the folder to install, 100% free & open source.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent%20Skills-blue)](https://hermes-agent.nousresearch.com)
[![agentskills.io](https://img.shields.io/badge/agentskills.io-Compatible-8A2BE2)](https://agentskills.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/jiawood2006/hermes-skills/pulls)

**⭐ 觉得有用？点个 Star 支持一下 → [⭐ Star this repo](https://github.com/jiawood2006/hermes-skills/stargazers) — 你的支持是开源的动力！**
**⭐ If you find this useful, please Star it — it keeps the project alive!**

---

## 🖼️ 效果示例 / Demo（30 秒看懂能干什么）

### 🛒 电商素材工坊：白底图 → 使用场景图

| 输入：产品白底图 / Input | 输出：场景合成图 / Output |
|:---:|:---:|
| ![before](docs/demo/demo_product_before.jpg) | ![after](docs/demo/demo_scene_after.jpg) |

*一键把白底产品图放进真实使用场景（演示图为 AI 生成的无品牌通用产品）*
*One-click scene composition from a plain product photo (demo shows an AI-generated unbranded product)*

### ✍️ de-ai-writer：去 AI 味前后对比

| 之前（AI 味）/ Before | 之后（真人感）/ After |
|:---|:---|
| 首先，这款产品具有非常出色的性能表现。其次，它的外观设计也非常时尚。总而言之，它是一款值得推荐的产品。 | 这机器上手就俩字：顺手。性能不拖后腿，长得也拿得出手，用过的都懂。 |

*去掉"首先/其次/总而言之"，恢复真人说话的样子*
*Removes "firstly / moreover / in conclusion" — sounds like a human again*

---

## ⚡ 60 秒快速上手 / Quick Start

```bash
# 1. 安装（任选一种）
# 方式一：hermes 命令（推荐，自动装到 ~/.hermes/skills/utilities/）
hermes skills install jiawood2006/hermes-skills/skills/video-to-text
# 方式二：复制目录（任意 Agent 都可用）
mkdir -p ~/.hermes/skills/utilities && cp -r skills/* ~/.hermes/skills/utilities/

# 2. 开箱即用（示例）
# 视频转文字：python3 ~/.hermes/skills/utilities/video-to-text/scripts/vtt.py "抖音链接或视频文件"
# 文档OCR：   python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 合同.pdf
# 去AI味：    python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/deai.py 稿子.txt -o 改好.txt

# 3. 在 Agent 里直接用
# 对 Hermes/Claude Code 等 Agent 说："帮我转这个视频文字 / 这段文字去AI味 / 扫描件提取文字"
```

> 💡 **路径说明**：仓库内路径是 `skills/xxx/`，安装后路径是 `~/.hermes/skills/utilities/xxx/`（hermes 命令默认按分类安装）。两个都支持，别混淆。

---

## 🎯 解决什么问题 / What problems does this solve?

| 痛点 / Pain point | 方案 / Solution | 技能 / Skill | 平台依赖 / Platform |
|:---|:---|:---|:---|
| 😩 抖音/视频里的话想转成文字？ | 一键提取视频文案 + **内容摘要/爆款拆解** | **video-to-text** | macOS/Linux（转写需 faster-whisper）|
| 🤖 AI 写的东西一股"机器味"？ | 写作引擎：去 AI 味/风格克隆/变体/评分 | **de-ai-writer** | 全平台 · 需 LLM key |
| 📄 PDF/扫描件要抠文字？ | 本地 OCR + **发票/合同字段抽取** | **doc-ocr** | macOS（Vision 引擎）|
| 🛒 电商主图/详情图要批量做？ | 素材工坊 + **AI 场景融合**（图生图） | **ecommerce-material-studio** | 全平台 · 生图需硅基流动 key |
| 🧠 Agent 记忆太乱、token 浪费？ | 记忆健康检查 + 压缩建议 | **memory-manager** | 全平台 · 零依赖 |
| 📖 写小说/连载怕前后矛盾？ | 长文记忆图谱：实体网+时间线+**伏笔追踪** | **memory-graph** | 全平台 · 提取需 LLM key |
| 🏗️ 工程项目资料太多理不清？ | 微信对话式 AI 工程顾问（记忆图谱+多群） | **ai-project-advisor** | 需部署服务端 |

---

## 📦 技能清单 / Skill List

### 1️⃣ video-to-text · 视频内容情报
- **中文**：抖音/B站链接元数据 + 本地视频语音转写 + **内容摘要/爆款结构拆解**
- **English**: Douyin/Bilibili metadata, local video transcription, content summary & viral structure analysis
- **适用**：短视频文案采集、内容情报、爆款拆解
- **依赖**：macOS/Linux；转写需 `pip3 install faster-whisper`；分析需 LLM key

### 2️⃣ de-ai-writer · 写作引擎
- **中文**：去 AI 味 + **风格克隆 + 变体生成 + 语气调节 + 8 维度评分**
- **English**: De-AI + style cloning + variants + tone control + quality scoring
- **适用**：公众号、小红书、电商文案、小说文风模仿
- **依赖**：需 LLM key（`--prompt-only` 零成本模式可用）

### 3️⃣ doc-ocr · 文档识别 + 结构化
- **中文**：PDF/扫描件/图片 OCR + **发票/合同字段抽取 + 表格转 CSV**
- **English**: OCR for PDFs/scans/images + structured field extraction (invoices/contracts/tables)
- **适用**：合同扫描、发票归档、票据数字化
- **依赖**：**macOS**（Vision 引擎）；结构化需 LLM key

### 4️⃣ ecommerce-material-studio · 电商素材工坊
- **中文**：电商主图/详情图/场景图批量生成 + **AI 场景融合**（图生图真实融入）
- **English**: Batch e-commerce images + AI scene fusion (Qwen-Image-Edit)
- **适用**：淘宝/拼多多/快手商家素材生产
- **依赖**：`pip install Pillow numpy scipy`；AI 融合需硅基流动 key

### 5️⃣ memory-manager · 记忆健康管理
- **中文**：Agent 记忆健康检查——统计 token 占用、找过期/冗余条目、压缩建议
- **English**: Agent memory health check — token cost, stale entries, compaction tips
- **适用**：任何 Agent 的记忆维护，防止上下文被挤占
- **依赖**：**零依赖**（纯 Python 标准库）

### 6️⃣ memory-graph · 长文记忆图谱
- **中文**：四维图谱（实体网+时间线+因果链+概念库）——小说/连载写作自动提取记忆，**伏笔追踪+一致性检查**
- **English**: Four-graph memory (entity/timeline/causality/concept) for long-form writing — auto-extract, plot-thread tracking & consistency check
- **适用**：小说、连载、剧本、系列教程、世界观设定管理
- **依赖**：提取需 LLM key（`--no-llm` 规则模式可用）

### 7️⃣ ai-project-advisor · AI 工程顾问
- **中文**：微信/企微对话式工程项目顾问——记录项目事实、盯关键节点、提醒风险
- **English**: WeChat/WeCom conversational engineering project advisor — records facts, tracks milestones, alerts risks
- **适用**：工程公司老板/项目经理的项目管理助手
- **依赖**：需在服务器部署（腾讯云/任意 Linux），配企业微信机器人

---

## 🚀 安装 / Installation

```bash
# 方式一：hermes skills 命令（推荐，自动按分类安装到 ~/.hermes/skills/utilities/）
hermes skills install jiawood2006/hermes-skills/skills/video-to-text
hermes skills install jiawood2006/hermes-skills/skills/de-ai-writer
hermes skills install jiawood2006/hermes-skills/skills/doc-ocr
hermes skills install jiawood2006/hermes-skills/skills/ecommerce-material-studio
hermes skills install jiawood2006/hermes-skills/skills/memory-manager
hermes skills install jiawood2006/hermes-skills/skills/memory-graph
hermes skills install jiawood2006/hermes-skills/skills/ai-project-advisor

# 方式二：复制目录（任意 Agent 都可用，路径与 SKILL.md 保持一致）
mkdir -p ~/.hermes/skills/utilities
cp -r skills/* ~/.hermes/skills/utilities/
```

> 💡 兼容 agentskills.io 开放标准——其他支持 Skills 的 Agent 也能用。
> 📁 安装后脚本路径：`~/.hermes/skills/utilities/<技能名>/scripts/`（各技能 SKILL.md 内命令均基于此路径）。

---

## 💬 欢迎反馈 / Feedback

**用了有意见、有问题、有想法？欢迎提出来，每条都会认真看！**
**Used it and have feedback, questions, or ideas? Please share — every issue is read!**

- 🐛 发现 Bug / Found a bug → [提 Issue / Open an Issue](https://github.com/jiawood2006/hermes-skills/issues/new?template=bug_report.md)
- 💡 想要新技能 / Want a new skill → [求新技能 / Request a skill](https://github.com/jiawood2006/hermes-skills/issues/new?template=feature_request.md)
- 💬 随便聊聊 / Just chat → [Discussions](https://github.com/jiawood2006/hermes-skills/discussions)

*你的意见能让这些技能更好用——尤其是"哪里不好用"的吐槽最宝贵。*
*Your feedback makes these skills better — especially "what doesn't work well".*

---

## ⭐ 支持作者 / Support

**好用请点 Star ⭐——你的支持是开源的动力！**
**If you find this useful, please Star ⭐ — it keeps the project alive!**

- 免费使用，无需任何费用 / Free to use
- 欢迎 PR / Issues / 建议 / PRs, Issues & feedback welcome
- 想支持更多：扫码或联系（详见各技能内 SKILL.md）/ Scan QR or contact (see SKILL.md inside each skill)

---

## 📄 License

MIT — 自由使用，保留版权声明即可 / Free to use with attribution.
