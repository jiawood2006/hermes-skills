---
name: memory-manager
description: "Agent记忆健康管理（Memory Manager）。用户说'记忆太乱''整理记忆''检查记忆''记忆清理'时使用。扫描 Hermes 记忆文件（MEMORY.md/USER.md），统计 token 占用、找过期/冗余/超长条目、检查 state.db 体积，给出压缩精简建议。Memory health check for AI agents: scan memory files, estimate token cost per turn, find stale/redundant entries, suggest compaction."
version: 1.0.0
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
- state.db 体积（>500MB 建议清理）
- 每轮记忆注入总 tokens（建议 <2000）

### 2. 记忆分层原则（什么时候该存/不该存）

| 该存（事实/偏好） | 不该存（过程/临时） |
|:---|:---|
| 用户偏好、纠正、习惯 | 任务进度、完成日志 |
| 环境事实（路径/凭证位置） | PR 号、commit sha、临时状态 |
| 工具怪癖、踩坑教训 | 会话细节（用 session_search 回忆）|
| 稳定的约定/规范 | 可复用流程（应存为 skill）|

### 3. 压缩技巧

- **过期信息**：日期类（"当前余额"）→ 删除或改为历史
- **超长条目**：压缩成要点（保留关键事实，去掉过程描述）
- **合并**：同主题多条 → 合并成一条
- **迁移**：方法论 → skill；会话细节 → session_search

## 已知陷阱

- **记忆工具限流**：写前先删/合并（memory 工具按最终字符数检查，批量操作一次完成）
- **凭证纪律**：token/密码/API key 一律不落记忆明文
- **记忆 vs skill**：流程类知识存 skill（按需加载），事实类存记忆（每轮注入）——放错地方都浪费

## 💛 免费使用 · 自愿支持

**本技能完全免费使用。**

> 想提需求、反馈问题，欢迎到 GitHub 提 Issue：https://github.com/jiawood2006/hermes-skills/issues
