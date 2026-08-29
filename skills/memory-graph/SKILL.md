---
name: memory-graph
description: "长文记忆图谱（Memory Graph）。写小说/连载/剧本/系列教程等长内容时使用——自动提取实体/事件/关系/因果，建立四维图谱（实体网+时间线+因果链+概念库），支持查询、伏笔追踪、一致性检查。基于MAGMA论文四图思想（小说版novel-magma-memory的通用化）。Memory graph for long-form writing: entity network, timeline, causality chain, concept base — with plot-thread tracking and consistency checks."
version: 1.0.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [memory, graph, writing, longform, novel, plot-tracking, consistency]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# Memory Graph 长文记忆图谱

写长内容（小说/连载/剧本/系列教程/世界观设定）最大的痛点是**记不住前面写了什么**——人物关系、事件顺序、埋的伏笔、前后矛盾。本技能用**四维图谱**帮你记住一切。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/memory-graph` 或按 README 方式二复制 → 默认在 `~/.hermes/skills/utilities/memory-graph/`。

## 触发条件

- 写小说/连载/剧本/系列内容，需要管理人物、时间线、伏笔
- "帮我记住前面写了什么""查一下XX在第几章出现过""检查前后有没有矛盾"
- 系列内容更新前查询已有设定（人物关系/地名/事件）

## 四维图谱

| 图谱 | 内容 | 对应能力 |
|:---|:---|:---|
| 实体图谱 | 人物/地点/物品/组织 + 关系网 | 查询"XX 和 XX 什么关系" |
| 时间图谱 | 事件按时间排序 | 时间线回顾 |
| 因果图谱 | 事件因果链 | **伏笔追踪**（线索未回收检测）|
| 语义图谱 | 概念/设定/主题 | 世界观一致性 |

## 使用步骤

### 1. 初始化项目

```bash
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py init --name "默书斋" --dir ./data
```

### 2. 每写一章/一集就摄入

```bash
# LLM 提取（推荐，需 LLM key）
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py ingest 第3章.txt --dir ./data --ch 3

# 无 LLM key：手动指定实体 + 规则提取
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py ingest 第3章.txt --dir ./data --ch 3 --entities "陈默,周晓芸,赵全发" --no-llm
```

自动提取：实体（人物/地点/物品/组织）+ 关系 + 事件 + 因果 + 概念。

### 3. 写作前查询

```bash
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py query 陈默 --dir ./data
# 输出：属性/别名/关系网（含反向关系）/相关事件
```

### 4. 时间线回顾

```bash
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py timeline --dir ./data
```

### 5. 一致性检查 + 伏笔追踪（每阶段必跑）

```bash
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py check --dir ./data
# 输出：时间倒挂 / 线索未回收 / 别名冲突
```

### 6. 统计 + 导出

```bash
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py status --dir ./data
python3 ~/.hermes/skills/utilities/memory-graph/scripts/memory_graph.py export --dir ./data -o 全量.json
```

## 配置（LLM 提取）

```bash
export LLM_API_KEY="你的key"
export LLM_BASE_URL="https://api.deepseek.com/v1"
export LLM_MODEL="deepseek-chat"
# 或写 ~/.deai_writer.conf [llm] 段
```

## 存储

- 每个项目一个目录：`<dir>/memory_graph.json`（单文件，可备份/版本管理）
- 结构：entities / timeline / causal / semantic / meta

## 已知陷阱

- **LLM 提取是异步的**：摄入时 LLM 可能偶尔失败（重试即可）；`--no-llm` 是降级方案
- **实体合并**：同一实体不同写法会合并（别名自动补充），但**强烈建议统一称呼**（"陈默" vs "陈先生"）
- **时间标注**：文本里写清故事内时间（"第3天""当晚""2024年5月"）能让时间线更有用
- **只提取明确信息**：LLM 不会编造（prompt 已限制），但过度模糊的文本提取质量会下降
- **小说专用进阶版**：长篇小说推荐用 novel-magma-memory（POV/伏笔账本/情感图更细），本技能是通用轻量版

## 💛 免费使用 · 自愿支持

**本技能完全免费使用。**

> 想提需求、反馈问题，欢迎到 GitHub 提 Issue：https://github.com/jiawood2006/hermes-skills/issues
