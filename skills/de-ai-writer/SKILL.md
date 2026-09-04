---
name: de-ai-writer
description: '写作引擎（Writing Engine）。用户提供文本，需要去AI味、风格克隆、多版本变体、语气调节、质量评分时使用。内置免key demo 模式（无需 API Key 即可看效果）。De-AI Writer: remove AI-smell, clone style, variants, tone, quality score — full Chinese writing engine.'
version: 2.0.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [writing, editing, humanize, de-ai, copywriting, style-clone, review]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# De-AI Writer 写作引擎

把 AI 生成的文字改写成自然、有真人味的中文——**不止去味**，是一个完整的中文写作引擎：去AI味、风格克隆、变体生成、语气调节、质量评分。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/de-ai-writer` 或按 README 方式二复制 → 默认在 `~/.hermes/skills/utilities/de-ai-writer/`。以下命令基于该路径。

## 触发条件

用户提供一段文字（粘贴或文件），要求：
- "去AI味""改得像人写的""太官方了改自然点"
- "模仿我的风格写""按这个文风改"（风格克隆）
- "给我几个版本""多写几个说法"（变体生成）
- "写得更接地气/更正式/更有营销味"（语气调节）
- "看看这篇写得怎么样""打分"（质量评分）

## 使用步骤

### 0. 免 key 演示（第一次用，推荐先跑这个）

没配 API Key 也能**立刻看到去 AI 味效果**——内置本地规则引擎（纯规则、零依赖、不联网）：

```bash
# 跑内置示例（30 秒看效果）
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py demo
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/demo.py            # 同上

# 处理自己的文本
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py demo -t "首先，这款产品不仅性能卓越，更是彰显了..."
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/deai.py demo -t "文本"   # 简版入口
```

输出 before/after 对照 + 清除统计（"共清除 N 处 AI 味表达"）。这是**轻度去味**（只删口水词/机械连接/空话模板，语义零损伤）；深度改写见下一步。

### 1. 去 AI 味（核心，LLM 深度改写）

```bash
# 有 API Key（推荐，效果好）
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py deai 稿子.txt -o 改好.txt
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py deai -t "直接传文本"

# 无 API Key（零成本模式：输出完整改写提示词，粘贴到任意 AI 助手即可）
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py deai 稿子.txt --prompt-only
```

### 2. 风格克隆（模仿样本文风）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py stylize 稿子.txt --sample 风格样本.txt -o 仿写.txt
```

- `--sample` 提供风格参考文件（可以是小说片段、你的旧文章、喜欢的作者文风）
- 引擎严格模仿样本的句式/用词/节奏/口语比例，但保留用户文本的内容

### 3. 变体生成（A/B 测试）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py variants 稿子.txt -n 3
```

- 生成 2-6 个明显不同风格的版本（短促有力版/口语松弛版/画面感版…）
- 适合公众号标题测试、电商文案 A/B、广告投放多素材

### 4. 语气调节

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py tone 稿子.txt --tone marketing
```

- `--tone` 可选：`casual`（口语）/ `formal`（正式）/ `marketing`（营销）/ `humor`（幽默）/ `direct`（直接）

### 5. 质量评分（8 维度）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py review 稿子.txt
```

- 8 维度评分：Hook（开篇吸引力）/ Pacing（节奏）/ Emotion（情绪）/ AI Smell（AI味）/ Clarity（清晰度）/ Persuasion（说服力）/ Structure（结构）/ Readability（可读性）
- 输出总分 + 每维度分数条 + 3 条具体改进建议
- 设计吸收自小说流水线评审体系（novel-writing-system 8 维度评分）

## 配置（API Key）

```bash
# 方式一：环境变量
export LLM_API_KEY="你的key"
export LLM_BASE_URL="https://api.deepseek.com/v1"  # 任意 OpenAI 兼容接口
export LLM_MODEL="deepseek-chat"

# 方式二：配置文件 ~/.deai_writer.conf
# [llm]
# key = sk-xxx
# base_url = https://api.deepseek.com/v1
# model = deepseek-chat
```

不配置也能用 `--prompt-only` 模式（零成本）。

## 文件结构

```
scripts/
├── writer.py    # 统一入口（demo/deai/stylize/variants/tone/review 子命令）
├── demo.py      # 免key本地规则引擎（demo 模式，零依赖）
├── engine.py    # LLM 调用 + 配置加载
└── deai.py      # 简版入口（demo 子命令 + 去味，保留兼容）
```

## 已知陷阱

- **风格克隆样本要精炼**：样本太长（>4000 字）会自动截断；样本选 3-5 段最能代表风格的文字最有效
- **变体数量**：`-n` 最大 6，太多版本质量会下降
- **review 输出**：依赖 LLM 返回 JSON，个别模型格式不稳时直接打印原文
- **中文优先**：专有名词/品牌名保留原文不翻译

## 💛 免费使用 · 自愿支持

**本技能完全免费使用。**

觉得好用、帮到你了，可以**自愿扫码支持**（金额随意，一杯咖啡即可）：

> 支持过我的人，后续 Pro 版/批量服务有优惠。
> 想提需求、反馈问题，欢迎到 GitHub 提 Issue：https://github.com/jiawood2006/hermes-skills/issues
