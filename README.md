# 🧰 Hermes Skills · 中文实用技能包 / Practical Chinese Agent Skills

> **你的 Agent 很聪明，但它搞不定中文世界的活儿。**
> 抖音文案要手抄？扫描合同要肉眼敲？AI 写的稿子一股机器味？电商主图一张张 P？
> 这里就是给 Agent 装的 **中文生存技能包**——7 个开箱即用的实用技能，免费开源，复制即用。
>
> *Your agent is smart — but useless on Chinese real-world tasks. Douyin video→text, Chinese OCR, de-AI writing, e-commerce images. This is its Chinese survival kit.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Hermes Agent](https://img.shields.io/badge/Hermes-Agent%20Skills-blue)](https://hermes-agent.nousresearch.com)
[![agentskills.io](https://img.shields.io/badge/agentskills.io-Compatible-8A2BE2)](https://agentskills.io)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/jiawood2006/hermes-skills/pulls)

> 🎯 **定位 / Positioning**：GitHub 技能市场 99% 是英文开发工具——这里是稀缺的**中文场景实用技能**。**Practical Chinese-language agent skills** — the rare gems in a market full of English dev tools.

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

### 🎬 video-to-text：抖音链接 → 自动转写（一条命令）

```
$ vtt "https://v.douyin.com/xxxx/"
🎬 视频元数据        title: 3个超实用的生活小技巧
📼 已下载视频        author: 生活达人小李
✅ 转写已保存: 3个超实用的生活小技巧_transcript.md（12 段 / 380 字）
[00:00] 大家好，今天分享三个超实用的生活小技巧
[00:07] 第一个，用牙膏清洁银饰…
```

*不用手动存视频：链接 → 自动下载 → 本地转写 → 结构化 Markdown，一条命令跑完*
*One command: Douyin link → auto-download → local transcription (privacy-safe, no API key)*

---

## 🎬 30 秒体验（零安装 · 无需 Key）/ Try it in 30s

**去 AI 味** —— 不用装任何东西，直接跑（内置示例，纯本地规则引擎）：

```bash
curl -sL https://raw.githubusercontent.com/jiawood2006/hermes-skills/main/skills/de-ai-writer/scripts/demo.py | python3 -
# 处理你自己的文本:
curl -sL https://raw.githubusercontent.com/jiawood2006/hermes-skills/main/skills/de-ai-writer/scripts/demo.py -o demo.py \
  && python3 demo.py -t "首先，这款产品不仅性能卓越，更是彰显了我们的创新精神。"
```

输出 before/after 对照 + "共清除 N 处 AI 味表达"——效果立现。

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

### 1️⃣ video-to-text · 抖音视频一键转文字
- **中文**：**抖音分享链接 → 自动下载 → 本地转写**（一条命令闭环）+ 结构化 Markdown + 内容摘要/爆款结构拆解
- **English**: **Douyin link → auto-download → transcribe in ONE command** + structured Markdown + viral analysis
- **适用**：短视频文案采集、内容情报、爆款拆解
- **依赖**：macOS/Linux；转写需 `pip3 install faster-whisper`（可选 SenseVoice 更准）；分析需 LLM key

### 2️⃣ de-ai-writer · 中文去 AI 味写作引擎
- **中文**：去 AI 味 + **免key demo 演示** + 风格克隆 + 变体生成 + 语气调节 + 8 维度评分
- **English**: De-AI + **no-key demo** + style cloning + variants + tone control + quality scoring
- **适用**：公众号、小红书、电商文案、小说文风模仿
- **依赖**：demo 模式**零依赖免 key**；深度改写需 LLM key（`--prompt-only` 零成本模式也可用）

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

**支持任何 Agent / host**——SKILL.md 遵循 agentskills.io 开放标准（Claude Code / Codex / Cursor / Gemini CLI / OpenCode / Hermes / npx skills…）：

```bash
# 方式一：一键安装脚本（装全部 + 全局命令 deai-demo/vtt/dococr/v2t 等）
git clone https://github.com/jiawood2006/hermes-skills.git
cd hermes-skills && ./install.sh

# 方式二：skills CLI（支持 50+ Agent 生态: Claude Code/Codex/Cursor…）
npx skills add jiawood2006/hermes-skills --global     # 装全部
npx skills add jiawood2006/hermes-skills/skills/video-to-text -g   # 装单个

# 方式三：Claude Code / 任意 Agent（手动复制到技能目录）
mkdir -p ~/.claude/skills && cp -r skills/* ~/.claude/skills/

# 方式四：Hermes 官方命令（自动按分类安装）
hermes skills install jiawood2006/hermes-skills/skills/de-ai-writer
hermes skills install jiawood2006/hermes-skills/skills/video-to-text
hermes skills install jiawood2006/hermes-skills/skills/doc-ocr
hermes skills install jiawood2006/hermes-skills/skills/ecommerce-material-studio
hermes skills install jiawood2006/hermes-skills/skills/memory-manager
hermes skills install jiawood2006/hermes-skills/skills/memory-graph
hermes skills install jiawood2006/hermes-skills/skills/ai-project-advisor

# 方式五：复制目录（纯手动，路径与各技能 SKILL.md 保持一致）
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
