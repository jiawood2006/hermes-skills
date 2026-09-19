# 生成前预检 + 质量门禁（2026-09-15 实测）

## 一、参考图：公网托管 + 比例实测（产品失真的真根因）
### 1. 必须公网可访问
r2v 的 `reference_urls` / `media[].url` 只吃**公网 URL**。本项目托管：
`https://yunvela.com/dh/` ↔ 服务器 `/opt/yunvela-site/dh/`

```bash
scp a.jpg yunvela:/opt/yunvela-site/dh/ && ssh yunvela 'chmod 644 /opt/yunvela-site/dh/a.jpg'
# 回读校验（不许跳过）：字节数 + md5 必须一致
curl -s -o /tmp/dl.jpg "https://yunvela.com/dh/a.jpg?t=$(date +%s)"
[ "$(md5 -q a.jpg)" = "$(md5 -q /tmp/dl.jpg)" ] && echo ✅ || echo ❌
```

### 2. 上传前先量「产品实体 高:宽」
```python
a = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
solid = a.min(axis=2) < 200            # 产品实体（排除白底与浅灰阴影）
ys, xs = np.where(solid); print((ys.max()-ys.min())/(xs.max()-xs.min()))
```
实测（HSQ1 迷你剃须刀，官方 74×39×39mm）：
| 文件 | 实测高:宽 | 判定 |
|---|---|---|
| `正面图.png` | 625×1206 → **1.93:1** | ✅ 可用 |
| `左侧图.png` | 627×1213 → **1.93:1** | ✅ 可用 |
| 服务器旧 `hsq1_side.jpg` | **0.94:1（底面断面图：按键+Type-C 那面）** | ❌ 就是它把产品害成"矮胖罐" |

**根因**：两张参考一张修长、一张圆胖 → 模型把两者**平均**。所以"产品每段都变形"**不是 prompt 写得不狠，是参考图自带矛盾**。
→ 换参考图前先量比例；两张必须**同向（都竖立）+ 同比例**。

参考图制作：按主体 bbox 居中裁方形（外扩 ~72%）→ 贴正方形**纯白**画布 → 缩到 1280×1280、quality 95。

## 二、百炼账号门禁（`Arrearage`）定位流程
1. **区分「key 错」与「账号欠费」**：最便宜的文本模型探一次
   `POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` `model=qwen-turbo`
   - `Arrearage / overdue payment` → **整个账号**欠费（key 有效，不是模型权限问题，换模型也没用）
   - `Incorrect API key provided` → key 本身无效/复制不全
2. `/api/v1/quotas` **在欠费状态下仍可用**，能读到 `workspace_id`（本项目 `ws-1cv1h3gyburi5v9v`、业务空间 6034154），
   但**不含手机号/账号 ID** → **从 key 反查不出是哪个阿里云账号注册的**，别向用户承诺能查。
3. 用户说"已充值"但复测仍欠费，三个高频原因：
   ① 充到了**另一个阿里云账号**（另一家公司／另一个手机号／国际站 alibabacloud.com）
   ② 该账号有**未结清账单**（欠费状态要先结清，充值不一定自动抵扣）
   ③ 到账延迟（先等 1–2 分钟再复测，别急着下结论）
4. **解套办法（不必折腾退款）**：在**充了钱的那个账号**里开通百炼 → 建业务空间 → 生成新 key 交给助手，
   本机只改 `~/.hermes/.dashscope_key` 一行即可接着干。
5. 汇报口径：这是**账号计费状态**，充值/结清后**立即恢复**（同日已发生过一次恢复）。
   不要说成"万相不能用了/工具坏了"——那会把一次可修复的计费问题固化成拒绝服务。

## 三、质量目标（用户口径）
- 用户 2026-09-15 对 v9 的评语：**「很好…质量还是不如样片那些，感觉那些画面更高级，有影棚的感觉，人物也更真实」**
- 拆解成可执行的下一档目标：**影棚布光（柔光箱主光 + 侧逆光勾边）／浅景深背景虚化／专业妆发的人物真实感**
- 只有**万相 r2v（1080P，1 元/秒）**能给这种观感；硅基流动 I2V 只能"锁首帧产品 + 加运动"，
  给不了人物真实感，别拿它冒充"样片级"
- 「影棚感版」提交参数（脚本备好即可发）：参考图 = 两张 1.93:1 官方图 + 人物图；
  `duration:10 / resolution:1080P / ratio:9:16 / watermark:false / prompt_extend:false`；
  prompt 三段式 = ①影棚布光风格 ②产品硬约束（**写真实比例 1.9:1 / 74×39mm**）③分镜+台词
- 成本口径：10s × 1080P = 10 元/段；两段 ≈ 20 元。花钱前先报单价（用户对成本敏感但不接受为省钱牺牲观感）

## 四、静图不能当镜头（重要修正）
曾写进 SKILL.md 的"产品特写用官方真机图做 Ken Burns"**已被用户否掉两次**：抠图/羽化/满画面都露灰带
（"那张裁剪的静态图太难看了"），整屏官方贴图+大字被判"图文 PPT"。
详见 `references/shot-level-fix-and-studio-still.md` 第四节。
