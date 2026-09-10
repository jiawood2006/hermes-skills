---
name: memory-manager
description: "Agent记忆健康管理（Memory Manager）。用户说'记忆太乱''整理记忆''检查记忆''记忆清理'时使用。扫描 Hermes 记忆文件（MEMORY.md/USER.md），统计 token 占用、找过期/冗余/超长条目、体检会话库（state.db 体积与索引占比）、并从会话历史挖掘用户纠正与长期要求（提示哪些还没进记忆）。Memory health check for AI agents: token cost per turn, stale/redundant entries, session-DB size diagnosis, and correction mining from chat history."
version: 1.1.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [memory, health, cleanup, token-efficiency, agent-management]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# Memory Manager 记忆健康管理

Agent 的记忆会**注入每个会话的 system prompt**——太大 = 每轮浪费 token、挤占上下文、还可能存过期信息误导判断。本技能定期检查记忆健康，保持记忆精简有效。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/memory-manager` 或按 README 方式二复制 → 默认在 `~/.hermes/skills/utilities/memory-manager/`。

## 触发条件

- "检查记忆""记忆清理""整理记忆"
- 发现 Agent 回答变慢 / 上下文被挤占
- 定期记忆健康检查（建议每月一次）

## 使用步骤

### 1. 记忆健康检查

```bash
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --full   # 完整报告（逐条分析）
```

输出：
- 每条记忆文件的 token 占用/条目数
- 超长条目（>800 字，建议精简）
- 含 30 天前日期的条目（可能是过期信息）
- state.db 体积（>500MB 建议清理，见第 2 节）
- 每轮记忆注入总 tokens（建议 <2000）

### 2. 会话库体检（`--state-db`）

不只是报体积——会**拆到表级**告诉你是"正文大"还是"索引大"，给出对症方案：

```bash
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --state-db
```

实测样例（1.2GB 的库）：

```
🗄️ state.db（会话历史）: 1.2GB
   页: 316858×4096B | 空闲页: 2770 | 可直接回收: 约 10.8MB
   体积占比 Top 表:
       478.1MB  messages_fts_trigram_data
       331.8MB  messages
       162.7MB  messages_fts_trigram_content
       162.7MB  messages_fts_content
   ⚠️ 其中 FTS 全文索引占 872.6MB（71%）——索引比正文还大，先处理索引，别急着删会话
```

- **索引占大头**（常见）→ 先 `rebuild` 索引 / 去掉 trigram，再 VACUUM，**不用删历史**
- **正文占大头** → 才清理旧会话
- 无 `dbstat` 支持时自动降级（只报体积与行数），不会报错

### 3. 从纠正中学习（`--corrections`）

**重复两次的纠正 = 该进记忆的长期偏好。** 扫描会话历史，把用户的纠正/长期要求挖出来，并标记哪些疑似还没进记忆：

```bash
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --corrections
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --corrections --corrections-days 90
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --corrections --full   # 看全部候选
```

输出示例：

```
   候选 30 条，其中 **30 条疑似未进记忆**
   [未记录  ] 2026-09-06 (否定/纠错/禁止类/长期规则) 这个工作以后必须在类似工作中你来主动开展，不要让我提醒…
   [已在记忆] 2026-08-24 (禁止类) 公开仓库 demo 图禁止品牌产品图…
```

识别 7 类信号：否定/纠错、重复强调、显式要求记住、禁止类、长期规则、强约束、不满追问。

> ⚠️ **这是候选清单，不是自动写入**——必须人工判断：属于**长期偏好/规则**的写进记忆；**一次性的任务要求不要写**（那是任务，不是偏好）。"未记录"是关键词粗判，措辞不同但意思已记的情况会误报，以人工判断为准。

### 4. 记忆分层原则（什么时候该存/不该存）

| 该存（事实/偏好） | 不该存（过程/临时） |
|:---|:---|
| 用户偏好、纠正、习惯 | 任务进度、完成日志 |
| 环境事实（路径/凭证位置） | PR 号、commit sha、临时状态 |
| 工具怪癖、踩坑教训 | 会话细节（用 session_search 回忆）|
| 稳定的约定/规范 | 可复用流程（应存为 skill）|

### 5. 压缩技巧

- **过期信息**：日期类（"当前余额"）→ 删除或改为历史
- **超长条目**：压缩成要点（保留关键事实，去掉过程描述）
- **合并**：同主题多条 → 合并成一条
- **迁移**：方法论 → skill；会话细节 → session_search

## 已知陷阱

- **记忆工具限流**：写前先删/合并（memory 工具按最终字符数检查，批量操作一次完成）
- **凭证纪律**：token/密码/API key 一律不落记忆明文
- **记忆 vs skill**：流程类知识存 skill（按需加载），事实类存记忆（每轮注入）——放错地方都浪费

## 快速验证 / Smoke Test

```bash
# 1) 记忆健康 + 会话库体检（无 LLM key 也可跑）
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --state-db
# 期望：token 统计 + 冗余建议 + state.db 表级体积与对症方案

# 2) 纠正挖掘（需要 ~/.hermes/state.db 有历史）
python3 ~/.hermes/skills/utilities/memory-manager/scripts/memcheck.py --corrections --corrections-days 7
# 期望：列出候选纠正/长期要求，并标 [未记录] / [已在记忆]
```
