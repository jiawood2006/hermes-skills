---
name: de-ai-writer
description: '写作引擎（Writing Engine）。用户提供文本，需要去AI味、风格克隆、多版本变体、语气调节、质量评分时使用。内置免key demo/check（AI味体检）无需 API Key。De-AI Writer: remove AI-smell, AI-smell check, clone style, variants, tone, quality score — full Chinese writing engine.'
version: 2.1.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [writing, editing, humanize, de-ai, copywriting, style-clone, review, ai-smell]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# De-AI Writer — 中文 AI 味写作引擎

**中文 AI 味 ≠ 英文 AI 味。** 英文看 delve / em-dash，中文看"赋能/闭环/首先其次/翻译腔"——这是按**中文语感**设计的去 AI 味引擎，不是英文 humanizer 的翻译版。

不止去味，是一个完整中文写作引擎：**AI味体检 → 去味改写 → 风格克隆 → 变体 → 语气 → 评分**。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/de-ai-writer` 或按 README 方式二复制 → 默认在 `~/.hermes/skills/utilities/de-ai-writer/`。以下命令基于该路径。

## 触发条件

用户提供一段文字（粘贴或文件），要求：
- "去AI味""改得像人写的""太官方了改自然点" → `deai`
- "看看这段AI味多重""这段是不是AI写的" → `check`（体检）
- "模仿我的风格写""按这个文风改" → `stylize`（风格克隆）
- "给我几个版本""多写几个说法" → `variants`（变体）
- "写得更接地气/更正式/更有营销味" → `tone`（语气）
- "看看这篇写得怎么样""打分" → `review`（评分）

## 使用步骤

### 0. AI 味体检 check（免key，先看问题在哪）

扫描文本 → 命中报告（分类+位置）+ **AI味指数 0-100**：

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py check -t "首先，这款产品不仅性能卓越，更是彰显了..."
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/deai.py check 稿子.txt      # 简版入口
```

输出示例：
```
📋 AI 味体检报告
总字数 77 ｜ 命中模式 8 处 ｜ AI味指数 100/100（AI味重，一眼假）
机械连接 ×3   官方黑话 ×2   空洞拔高 ×2   夸张词 ×1
💡 修复：deai.py demo -t "文本" 免key改写；配 key 后 writer.py deai 深度改写
```

### 1. 免 key 演示/改写 demo（无 API Key 也能立刻用）

内置**本地规则引擎**（纯规则、零依赖、不联网）——安全清除 60+ 高频中文 AI 味模式：

```bash
# 内置示例（30 秒看效果）
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py demo
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/deai.py demo -t "你的AI味文本"   # 处理自己的
```

输出 before/after 对照 + "共清除 N 处 AI 味表达"。轻度去味（只删口水词，语义零损伤）；深度改写见下一步。

### 2. 去 AI 味 deai（核心 · LLM 深度改写，8 类模式库）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py deai 稿子.txt -o 改好.txt
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/deai.py -t "直接传文本"

# 无 API Key 时：输出完整改写提示词，粘贴到任意 AI 助手即可
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py deai 稿子.txt --prompt-only
```

### 3. 风格克隆 stylize（模仿样本文风）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py stylize 稿子.txt --sample 风格样本.txt -o 仿写.txt
```

`--sample` 可以是小说片段、旧文章、喜欢的作者文风——引擎严格模仿句式/用词/节奏/口语比例。

### 4. 变体 variants（A/B 测试）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py variants 稿子.txt -n 3
```

生成 2-6 个明显不同风格版本（短促有力/口语松弛/画面感…），适合标题测试、文案 A/B、投放多素材。

### 5. 语气调节 tone

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py tone 稿子.txt --tone marketing
```

`--tone`：`casual`（口语）/ `formal`（正式）/ `marketing`（营销）/ `humor`（幽默）/ `direct`（直接）

### 6. 质量评分 review（8 维度）

```bash
python3 ~/.hermes/skills/utilities/de-ai-writer/scripts/writer.py review 稿子.txt
```

Hook/Pacing/Emotion/**AI Smell**/Clarity/Persuasion/Structure/Readability 8 维评分 + 3 条改进建议。

## 中文 AI 味模式库（8 类）

| # | 类别 | 高频实例（→ 人话） |
|---|------|------|
| 1 | 空洞拔高 | 不仅…更是（→不光…也）、标志着（→意味着）、彰显了（→体现了）、至关重要、毋庸置疑 |
| 2 | 机械连接 | 首先/其次/综上所述/总的来说/值得注意的是/由此可见/此外——装饰性句首连接删掉 |
| 3 | 官方黑话 | 赋能(→支持)、闭环、抓手、颗粒度、底层逻辑、方法论、对齐、心智、破圈、护城河、赛道、沉淀、拉通 |
| 4 | 形容词堆砌 | 极致、巅峰、完美、卓越、顶级、颠覆性、革命性、史无前例 |
| 5 | 翻译腔 | 进行了讨论（→讨论了）、被广泛认为、最重要之一、在…扮演重要角色、随着…的发展 |
| 6 | 模板结尾 | 未来可期、拭目以待、开启/谱写新的篇章、砥砺前行、共创美好未来、希望对您有帮助 |
| 7 | 排比工整 | "创新、卓越、领先"强制三连、句句等长结构对称 |
| 8 | 客套chatbot | 该产品/此方案反复指代（→它）、我相信表态过多、客服式尾句 |

本地引擎（demo/check）执行其中可安全正则化的部分；LLM 深度改写（deai）执行全部 8 类含句式语义层。

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

**check/demo 完全不需要 key。** 只有 stylize/variants/tone/review/deai 深度改写需要；`--prompt-only` 零成本替代。

## 文件结构

```
scripts/
├── writer.py    # 统一入口（check/demo/deai/stylize/variants/tone/review）
├── demo.py      # 中文AI味本地引擎（check体检+改写，60+规则，零依赖）
├── engine.py    # LLM 调用 + 配置加载
└── deai.py      # 简版入口（check/demo + 深度改写）
```

## 已知陷阱

- **本地引擎是轻度处理**：只清安全的口水词/连接词/模板句，复杂句式（翻译腔重构、排比破势）交给 LLM 深度版
- **check 指数是启发式**：基于命中密度估算，用于快速感知，不是科学检测
- **风格克隆样本要精炼**：样本太长（>4000 字）自动截断；选 3-5 段最能代表风格的文字最有效
- **变体数量**：`-n` 最大 6
- **review 输出**：依赖 LLM 返回 JSON，个别模型格式不稳时直接打印原文
- **中文优先**：专有名词/品牌名保留原文不翻译

## 💛 免费使用 · 自愿支持

**本技能完全免费使用。**

觉得好用、帮到你了，可以**自愿扫码支持**（金额随意，一杯咖啡即可）：

> 支持过我的人，后续 Pro 版/批量服务有优惠。
> 想提需求、反馈问题，欢迎到 GitHub 提 Issue：https://github.com/jiawood2006/hermes-skills/issues
