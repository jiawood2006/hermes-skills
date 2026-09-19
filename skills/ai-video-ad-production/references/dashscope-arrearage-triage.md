# `Arrearage` 欠费排查（提交全失败时先看这里 · 2026-09-18 实测）

现象：一批分段提交**全部**返回
`{"code":"Arrearage","message":"Access denied, please make sure your account is in good standing"}`
—— 看起来像 prompt/模型 id 写错，其实是**账号余额不足**。别去改 prompt ✗。

## 免费探测（先做这个，再决定改什么）

```bash
K=$(tr -d '\n' < ~/.hermes/.dashscope_key)
# 空 input 探测：Arrearage = 欠费被拦；InvalidParameter = 已放行（只是字段/模型不对）
curl -s --max-time 40 -X POST "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis" \
 -H "Authorization: Bearer $K" -H "Content-Type: application/json" -H "X-DashScope-Async: enable" \
 -d '{"model":"wan3.0-video","input":{},"parameters":{"resolution":"720P","duration":5}}'
```

顺带一起探文本与图像（区分"整账号欠费"还是"某种模态"）：

```bash
# 文本：欠费时可能仍通（免费额度内）
curl -s -X POST "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation" \
 -H "Authorization: Bearer $K" -H "Content-Type: application/json" \
 -d '{"model":"qwen-turbo","input":{"messages":[{"role":"user","content":"OK"}]},"parameters":{"max_tokens":5}}'
```

## 判断与处置

| 探测结果 | 含义 | 处置 |
|---|---|---|
| 视频 `Arrearage`；文本/图像通 | **整账号余额不足**（文本/图像还在免费额度内，别被误导） | 充值，别改代码 |
| 视频 `InvalidParameter` | 已放行，只是字段/模型名不对 | 去修 payload |
| 全部 `Arrearage` | 账号级欠费/停用 | 充值（或检查是否充错账号） |

要点：
1. **换引擎没用** —— 可灵 / pixverse / vidu / VACE 全部跑在**同一个阿里云账号**下，一样 `Arrearage`。**不要浪费轮次换模型。**
2. 直达充值：`https://usercenter2.aliyun.com/finance/fund-management/recharge`
   （确认账号 = 你自己那个阿里云主账号——名下不止一个账号，**别充错**）。
3. **失败不计费**：欠费期间的 400 提交全部 0 元 → 充值后**原样重跑**即可，不用改配置。
4. 空 input 任务会被受理成 PENDING，随后 `InvalidParameter` 快速失败（实测 0.2s），**不计费**。
5. **同步延迟不一定 30 分钟**（本次充值后**立刻**放行）→ 充完马上探测一次，通过就续跑，别空等。
6. 汇报口径：**结论 + 为什么（探测证据）+ 直达链接 + 建议充值额 + "充完回我一声，我自动自检并续跑"**。
   用户接受"你告诉我怎么开通我自己来"，但必须给他**直达链接 + 精确步骤**。
7. 纪律：消息/日志里**不贴 key**，`$K` 从文件读；探测命令里的 token 一律不外发。
