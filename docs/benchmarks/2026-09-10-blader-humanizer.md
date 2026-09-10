# 对标档案：blader/humanizer

**对标日期**：2026-09-10
**对标对象**：https://github.com/blader/humanizer
**我方**：https://github.com/jiawood2006/hermes-skills （skills/de-ai-writer）
**结论一句话**：45.4k★ 的差距主要在**分发渠道与受众基数**，不在技能质量；但其**内容深度（模式清单）确实强于我们**，本轮已吸收。

---

## 1. 数据快照（2026-09-10 实测）

| 项目 | blader/humanizer | 我方 hermes-skills (de-ai-writer) |
|:--|:--|:--|
| ★ / fork | **45,995 / 3,770** | 0 / 0 |
| 建仓 | 2026-01-18（8 个月） | 2026-08-09（1 个月） |
| 最近推送 | 2026-09-06（活跃） | 2026-09-10 |
| License | MIT | MIT |
| 语言 | 英文 | 中文 |
| 正文体量 | SKILL.md **28.7KB / 374 行** | SKILL.md 11.7KB + 模式清单 23.3KB |
| 内容结构 | 25 个模式，5 组，每条含 Watch for / Problem / Before / After | 35 个模式，5 组，同结构 + 本地规则引擎 |
| 运行方式 | 纯 Markdown（scripts 仅打包校验） | Python 脚本 + 免 key 本地规则引擎 |
| 安装路径 | **4 条**：`npx skills add` / Claude 插件市场 / Claude Desktop ZIP / 手抄 SKILL.md | 5 条（本次补齐 Claude 插件后） |
| README | 16.1KB，带安装量徽章 / 4 平台安装 / 完整示例 / 来源 / 版本历史 | 12.2KB，带徽章 / 5 平台安装 / 示例 |
| 主题标签 | agent-skills, ai-writing, claude-code, codex, cursor, prompt-engineering, writing-tools | agent-skills, ai-writing, chinese, ecommerce, hermes, ... |

## 2. 为什么它 ★ 这么多（逐条）

1. **分发渠道差一个数量级**：它一句话装进 Claude Code / Codex / Cursor **任何** agent；我们只能 Hermes 用户装 → 受众基数差几十上百倍。
2. **英语 + 全球受众**：全球写作者都在用 Claude Code；中文 Hermes 用户是小众。
3. **时机**：2026 年初"AI 味"成全民话题，吃到早期曝光红利。
4. **README 当营销物料**：安装量徽章、4 平台安装、完整示例、来源引用、版本历史（2.9.1，显得活跃可信）。
5. **纯 Markdown 零门槛**：不用 key、不用 Python，复制就用。

## 3. 它确实更强的地方（诚实评估）

| 维度 | 它的做法 | 我们原来的问题 |
|:--|:--|:--|
| **模式颗粒度** | 25 条**命名模式**，每条给"识别特征 + 为什么假 + 改前改后" | 只有 8 类粗分类，靠关键词表，缺"病因"和对照示例 |
| **Before/After 对照** | 每条都有真实改写示例 | 没有成体系的对照库 |
| **判定纪律** | 明确标注"单条不算证据（weak alone）"，并给出"什么时候不要动手" | 无此纪律，容易过度改写 |
| **保留人味清单** | 列出必须原样保留的真人细节 | 无 |
| **来源标注** | 明确标注模式源自 Wikipedia Signs of AI writing | 无 |

## 4. 本轮采纳项（已落地）

- ✅ **补齐模式清单**：新建 `references/ai-patterns-zh.md`，**35 条**（本土化其 25 条 + 新增中文特有 10 条：公文套话 / 互联网黑话 / 排比口号体 / "随着…的发展" 开头 / 假坦诚开场 / emoji 当序号 / 结束语套话 等），每条含识别特征 → 病因 → 改前/改后
- ✅ **引入判定纪律**：标注 `弱证据` 条目（破折号 / 限定词 / 被动 / "的"字堆叠 / 引号），须同段落凑够 2 条以上才动手
- ✅ **引入"什么时候不要动手"** + **"必须保留的人味细节"** 两节
- ✅ **SKILL.md 挂接**：加"30 秒快检"表（最常命中 8 条）、"三套去味机制怎么选"、推荐工作流（体检 → 扫清单 → 改写 → 复检）
- ✅ **来源标注**：SKILL.md 末尾加"来源与致谢"，注明 Wikipedia + blader/humanizer（MIT）
- ✅ **版本升级** 2.1.0 → 2.2.0

## 5. 本轮分发改动（偷打法）

- ✅ 新增 `.claude-plugin/plugin.json` + `marketplace.json` → 可被 Claude Code 插件市场安装（对齐它的插件分发）
- ✅ 新增 `scripts/validate_skills.py` + `.github/workflows/validate-skills.yml` → 每次推送自动校验全部 SKILL.md frontmatter（质量信号 + CI 绿标）
- ✅ README 补齐：技能数 7 → 8、Claude 插件安装方式、de-ai-writer 35 条模式说明

## 6. 下次待办（复看用）

- [ ] 观察 30 天：`npx skills add` 与 Claude 插件两条新路径是否带来安装量（skills.sh 徽章数据）
- [ ] 给 `video-to-text` / `doc-ocr` 各做一次同赛道高星对标（参考对象：yt-dlp 生态、OCR 类技能仓库）
- [ ] 考虑出**英文版** `ai-patterns-en.md` 以覆盖英文写作场景（对标它的英文语料优势）
- [ ] 长期：把 `check`（免 key 体检）做成可单文件 curl 执行的入口，进一步降低"先看效果"的门槛

---

## 附：对标方法论（沉淀）

> 技能上架不是终点——**定期与同领域高星同类对标，提炼做法落地优化，不能闭门造车**。
> 四步：取料（读正文） → 逐项比 → 提炼（能偷的做法 / 能强化的内容） → 落地 + 归档。
> 边界：**只借鉴做法与模式框架，不安装对方技能（安装须用户同意）**；引用注明来源；不抄文案。
> 关键判断：**先分清星数差距来自"分发/受众/时机"还是"内容深度"**——前者偷打法，后者强内容。
