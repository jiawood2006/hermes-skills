# 百炼四家视频模型对比实测（2026-09-16）

同一 prompt / 同一组参考图（`hsq1_front.jpg`+`hsq1_side.jpg`+`hsq1_girl.jpg`）/ 5s / 竖屏 9:16 / 影棚影调。
端点统一：`POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`
头部：`Authorization: Bearer $DASHSCOPE_API_KEY` + `X-DashScope-Async: enable`

## 结论（电商广告片场景）
**⚠️ 产品保真必须放大逐帧核对，不能看整体观感下结论**（2026-09-16 踩坑：首轮凭"影棚感+整体像"把万相 3.0 误判为保真最好，放大后发现它把剃须刀画成了**理发推子**——顶部梳齿状刀头+机身圆钮）。

产品形态核对（同一 prompt/参考图，4 帧放大）：

| 模型 | 高宽比 1.9:1 | 顶部=平整金网 | Haier 字 | 材质真实感 | 帧间稳定 |
|---|---|---|---|---|---|
| **PixVerse V6** | ✓ | **唯一正确**✓✓ | ✓ | 好 | 稳 |
| 可灵 V3 | ✓✓ | ✗ 凸起金圆盘 | ✓ | 好 | 稳 |
| Vidu Q3-Ad | ✗ 矮胖罐 | ✗ 小凸金顶 | ✓ | **最好**✓✓ | 稳 |
| 万相 3.0 | ✗ | ✗ 梳齿状（像推子） | ✗ | 一般 | — |

**两个维度要分开看**：①**形态准确度** → PixVerse V6 第一；②**材质/真实感**（哑光反射、真人融合自然度）→ Vidu Q3-Ad 与可灵最好。

| 排名 | 模型 | 强项 | 弱项 | 价格(1080P) |
|---|---|---|---|---|
| 🥇 | **PixVerse-V6-r2v-omni** | **多镜头推进切镜**+影棚布光+真人+**产品形态最准**（平面金网+logo+修长）+1080×1920 竖屏 | 字段最刁（3 次才通） | 带参考图 **1.36 元/秒** |
| 🥈 | **Kling Video 3.0** | **多镜头切镜**+影棚感强+真人+比例/logo✓ | 刀头画成凸金盘；竖屏只有 720×1280（`mode:std`=720P，1080P 要 `mode:pro`） | 1.2 元/秒 |
| 🥉 | **ViduQ3-Ad_reference2video** | **材质真实感最好**、帧间最稳、logo✓ | 形态矮胖罐+小凸金顶；出**横屏 1914×1084**；无视影棚 prompt | 0.906 元/秒 |
| 4 | **万相 3.0**（阿里自研） | **免开通直调**+1080×1920 | 单镜头；本次产品形态画错（推子） | 1.2 元/秒 |

**选型**：主打 **PixVerse V6-r2v-omni**（竖屏+切镜+产品准）；要最强产品保真且可接受单镜头 → **万相 3.0**；要 1080P 竖屏+切镜 → 可灵改 `mode:"pro"`。

## ⭐ 参考图「正确用法」— 产品失真的头号根因（2026-09-16 官方文档核实）

**症状**：产品被画成"细长笔形迷你剃须刀"（先验），无论怎么加负面约束都没用。
**根因**：参考图**根本没被模型接收到**（字段写错/模型选错），模型只能走训练先验。**不是提示词不够强，是参考图没生效。**

| 模型 | ❌ 错误写法（我踩过） | ✅ 官方正确写法 |
|---|---|---|
| **万相 3.0** | `input.images`（文档中无此字段） | `input.media:[{"type":"reference_image","url":...}]`，提示词用 **`图1`/`图片1`** 指代（图片/视频/音频**分别计数**；最多 10 张） |
| **可灵** | `kling-v3-video-generation` + `input.images` | ⚠️ **`kling-v3-video-generation` 根本不支持参考生视频**（只能 `first_frame` / `first_frame+last_frame`）→ 必须换 **`kling/kling-v3-omni-video-generation`**，`media:[{"type":"refer","url":...}]`，提示词用 **`<<<image_1>>>`/`<<<image_2>>>`**（按 media 数组顺序，且 refer 场景 `aspect_ratio` 必填）；负面写进 `negative_prompt` 字段 |
| **PixVerse** | media 只给 url | `media:[{"type":"image_url","url":...,"ref_name":"剃须刀"}]`，提示词用 **`@剃须刀 `** 绑定（ref_name 全局唯一、`@` 后必须有空格）；不绑则模型自动全局解析 |
| **Vidu Q3-Ad** | 只给 `resolution` → **出横屏 1914×1084** | `media:[{"type":"image","url":...}]` ＋ **`parameters.size:"1080*1920"`**；提示词可写「商品是…」（官方广告示例写法）；支持 `(图1)(图2)` 指代 |

**提示词纪律**：不要用「修长」形容圆柱（会把产品推向笔形先验），用客观几何＋参照图编号：
> 「图1、图2 是同一件产品的正面和侧面照，画面中的商品必须严格按图1、图2 还原：高度只有直径的约 1.9 倍（74×39mm）的矮宽圆柱…」

## 各家必填字段（错误反推所得，照抄即可）

### 万相 3.0（阿里自研，**免开通**）
模型名 **`wan3.0-video`**（⚠️ 写 `wan3.0-video-generation` 会返回 `Model not exist.`）
```json
{"model":"wan3.0-video","input":{"prompt":"...","images":["url1","url2"]},
 "parameters":{"ratio":"9:16","resolution":"1080P","duration":5}}
```
- `ratio:"9:16"` → 720×1280；`size` 数值法（`"1080*1920"`）→ 1080×1920 ✓；**`aspect_ratio` 被忽略**

### Kling Video 3.0
```json
{"model":"kling/kling-v3-video-generation","input":{"prompt":"...","images":["url..."]},
 "parameters":{"mode":"std","duration":5,"resolution":"1080P","aspect_ratio":"9:16"}}
```
- 首提即通 ✓；`mode:"std"` → 实际出 **720×1280**（std=720P，pro=1080P）

### ViduQ3-Ad_reference2video
```json
{"model":"vidu/viduq3-ad_reference2video","input":{"prompt":"...","media":[{"type":"image","url":"..."}]},
 "parameters":{"resolution":"1080P","duration":5}}
```
- 首提即通 ✓；出片 1914×1084（横屏）

### PixVerse-V6-r2v-omni（字段最刁，按此顺序踩坑）
```json
{"model":"pixverse/pixverse-v6-r2v-omni",
 "input":{"prompt":"...","media":[{"type":"image_url","url":"https://..."}]},
 "parameters":{"resolution":"1080P","duration":5,"aspect_ratio":"9:16","watermark":false}}
```
报错递进（每步修一个）：
1. `Required field aspect_ratio are missing or empty.` → 补 `aspect_ratio`
2. `input.media is an empty array. It must contain at least one item.` → **用 `input.media`，不是 `images`**
3. `input.media.type must be image_url or video_url` → type 写 `image_url`（不是 `image`）
4. `Required field input.media[0].url are missing or empty.` → 最终形态 `{"type":"image_url","url":"..."}`

## 探测方法论（省钱）
- **失败不计费**，可放心用「提交 → 读报错 → 补字段」反推 schema，比啃动态渲染的控制台文档快 10 倍。
- 入口放行 ≠ 已开通：未开通返回 `InvalidParameter` / `The product is not activated`。
- 控制台真实模型名：`Kling Video 3.0`、`ViduQ3-Ad_reference2video`、`PixVerse-V6-r2v-omni`（搜「可灵」中文无结果，须搜 **Kling**）。
- 对比片合成：`/tmp/cmp/build_cmp.py`（2×2 xstack + ASS 标签；`force_original_aspect_ratio=decrease`+pad 保留横屏原帧，不裁切）。

## 成本实测
本轮 17.3 元（Vidu 4.5 + PixVerse 6.8 + 可灵 6.0），失败重提 0 元。同规格对比做一版 ≈ 17 元。
