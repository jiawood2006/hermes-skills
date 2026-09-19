# 百炼视频引擎与模型总纲：货架 / 字段 / 价格 / 选型（2026-09-19 合并版）

本文合并 7 篇「百炼视频模型货架 / 横评 / 字段与价格」的 reference，是本技能**唯一**的引擎选型与报价口径来源。
读它当你要：① 选引擎（产品镜 / 纯人物戏 / 最便宜档）；② 写请求（各家 `input` / `parameters` 字段不同，**不能一套通用**）；③ 报预算（元/秒价格表）；④ 解释报错（未开通 / 参数被静默忽略）。
**现行唯一主线：产品镜 = `wan3.0-video`；`wan2.7-r2v` 产品镜已退役。** 与本文冲突的旧文一律以本文为准。
模型 id / 单价 / 字段名 / 报错原文均一字未改；被推翻的旧结论用「❌ 已作废（日期）」单行标注。

---

## 一、货架清单（先盘货，再选型）

**枚举本账号可用模型（欠费时仍可调，最省事的入口）：**
```bash
# page_size 上限 100，超出报 "Pagination parameter page_size exceeds the length limit"
curl -s -H "Authorization: Bearer ***" \
  "https://dashscope.aliyuncs.com/api/v1/quotas?page_size=100&page_no=1"
```
返回 `output.total`（本账号 500）+ 每条 `{model, workspace_id, model_limit}`。

**对比货架（1080P 官方单价；价格为官方原价，限时折扣未计）：**

| 模型 id | 1080P 单价 | 关键能力 | 电商用法 |
|---|---|---|---|
| `wan3.0-video`（自家新版 / 现用产品镜） | **1.2 元/秒**（720P 0.6 / 480P 0.3） | **全能参考 All-in-One**：文本/图像/视频/音频/文件/链接输入；**最长 30 秒** | 一条成片的长镜头叙事；**产品出现/特写镜首选**（30s≈36 元） |
| `kling/kling-v3-video-generation`（另有 `-turbo` / `-omni`） | **1.2 元/秒**（有声）/ **0.8**（无声）；720P 0.9/0.6；**4K 3 元/秒** | 真人身段/动作自然度口碑最好、中文 prompt 友好、快手生态 | 真人剧情镜头 |
| `vidu/viduq3-ad_reference2video` | **0.9375 元/秒**（720P 0.78125） | **广告专用**参考生视频：1-7 张参考图；**声画同出 + 口型同步**；自带粒子/流体/运镜/光影特效 | 带货口播 + 产品展示（首选替代品） |
| `pixverse/pixverse-v6-r2v` | **0.68 元/秒**（有声）/ **0.53**（无声）；720P 0.36/0.27 | **多主体参考 2-7 图**（'r2v 全球第二'）；**15 秒**长素材；原生音乐；官方文档点名"电商产品特写" | 产品/场景 B-roll，批量试错最便宜 |
| `wan2.7-r2v`（原产品镜，已退役） | **1.0 元/秒**（720P 0.6） | 最多 **5 个**图/视频混合参考 + 音频音色参考 | 只留不挑产品的镜头（产品镜退役） |

Vidu 家族还有 `viduq3-drama_reference2video`（短剧）/ `viduq3-mix_reference2video`（均衡）等变体。

**辅助能力（同账号可调，直击电商制作痛点）：**

| 用途 | 模型 |
|---|---|
| **把已生成镜头里的产品替换成真机**（比 prompt 约束彻底） | `wan2.7-videoedit`、`wan2.1-vace-plus` |
| 口型对齐我们的配音 | `pixverse/pixverse-lipsync`、`videoretalk`、`wan2.2-s2v` |
| 运镜/肢体控制、换人 | `pixverse/pixverse-motioncontrol`、`wan2.2-animate-mix`、`wan2.2-animate-move` |
| 超分/提质 | `pixverse/pixverse-upscale` |
| 生图/改图（做参考图、场景图） | `qwen-image-3.0-pro`、`qwen-image-edit-max`、`wan2.7-image-pro`、`z-image-turbo` |

**海外模型（`Veo 3.1` / `Sora 2` / `Runway Gen-4`）**：画面质感天花板，但大陆接入需海外网络 + 外币支付，投放端还有 AI 内容标识合规要求 → **只当"看片学审美"的参考，不做生产主线**。向用户说明时讲清这三条门槛，别只夸质量。

---

## 二、各家字段差异（endpoint 统一，`input` / `parameters` 按模型写）

**统一 endpoint（4 家都一样）：**
```bash
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
Header: Authorization: Bearer *** ; Content-Type: application/json ; X-DashScope-Async: enable
# → output.task_id ；轮询 GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
```

**总表（全部实测跑出 `SUCCEEDED`）：**

| 模型 id | 参考图字段 | 关键参数 | 实测输出 |
|---|---|---|---|
| `wan3.0-video` | `input.images: [url…]` | `{duration, ratio:"9:16"}` 或 `{size:"1080*1920"}` | 1080×1920 竖屏 ✓（`aspect_ratio` 被静默忽略） |
| `kling/kling-v3-video-generation` | `input.images: [url…]` | `{mode:"std"\|"pro", duration, aspect_ratio:"9:16"}` | **`mode:"std"` → 720×1280**（同时传 `resolution:"1080P"` 也无效） |
| `vidu/viduq3-ad_reference2video` | **`input.media: [{type:"image", url}]`** | `{resolution:"1080P", duration:5}` | **1914×1084 横屏** |
| `pixverse/pixverse-v6-r2v-omni` | **`input.media: [{type:"image_url", url}]`**（`url` 为顶层字段） | **`aspect_ratio` 必填** | 按 aspect_ratio 出片 |

> ❌ 已作废（2026-09-16）：「4 家都吃 `input.images`」+「参数统一用 `resolution`+`duration` 4 家都通过」→ 现：**字段按模型写，不能一套通用**。

### `wan3.0-video`（阿里自研，免开通）
模型名 **`wan3.0-video`**（⚠️ 写 `wan3.0-video-generation` 会返回 `Model not exist.`）。
```json
{"model":"wan3.0-video","input":{"prompt":"...","images":["url1","url2"]},
 "parameters":{"ratio":"9:16","resolution":"1080P","duration":5}}
```
竖屏参数实测（4 组对照，同 prompt/素材）：

| 参数写法 | 实际输出 | 结论 |
|---|---|---|
| `ratio:"9:16"` | 720×1280 | ✅ 生效 |
| `size:"720*1280"` | 720×1280 | ✅ 生效 |
| `size:"1080x1920"`（小写x） | 1080×1920 | ✅ 生效 |
| `aspect_ratio:"9:16"` | 1280×720（横屏） | ❌ 被忽略 |

- 参考图字段用 **`input.images`**（数组，公网 URL）；`input.images` 传坏 URL 时请求仍被受理 → 字段被识别 ≠ 会用，必须出片回看产品。
- ✅ 吃**长 prompt**（2603 字一次通过）。
- ❌ 已作废（2026-09-16）：万相 3.0 参考图用 `input.media:[{"type":"reference_image","url":...}]` → 现：**实测正解 `input.images` 字符串数组**（`reference_image` 那套是错误推断）。

### `kling/kling-v3-video-generation`（可灵 V3）
```json
{"model":"kling/kling-v3-video-generation","input":{"prompt":"...","images":["url..."]},
 "parameters":{"mode":"std","duration":5,"resolution":"1080P","aspect_ratio":"9:16"}}
```
- 首提即通 ✓；`mode:"std"` → 实际出 **720×1280**（std=720P，pro=1080P）。
- 控制台卡片真名 **Kling Video 3.0**（搜中文"可灵"= 零结果，必须搜英文 **`Kling`**）。

### `kling/kling-v3-omni-video-generation`（可灵 omni，横评用的就是它）
- ⚠️ 早前实测称 `kling-v3-video-generation` **不支持参考生视频**（只能 `first_frame` / `first_frame+last_frame`），须换 `kling/kling-v3-omni-video-generation`：`media:[{"type":"refer","url":...}]`，提示词用 **`<<<image_1>>>`/`<<<image_2>>>`**（按 media 数组顺序，且 refer 场景 `aspect_ratio` 必填）；负面写进 `negative_prompt` 字段。
  （两组实测口径并存：本文以「omni + `media` / refer」为产品保真横评所用形式。）

### `vidu/viduq3-ad_reference2video`
```json
{"model":"vidu/viduq3-ad_reference2video","input":{"prompt":"...","media":[{"type":"image","url":"..."}]},
 "parameters":{"resolution":"1080P","duration":5}}
```
- 首提即通 ✓；出片 **1914×1084（横屏）**；无视影棚 prompt。
- 要竖屏须给 **`parameters.size:"1080*1920"`**（只给 `resolution` → 出横屏）；prompt 可写「商品是…」（官方广告示例写法），支持 `(图1)(图2)` 指代。

### `pixverse/pixverse-v6-r2v-omni`（字段最刁，按序踩坑）
```json
{"model":"pixverse/pixverse-v6-r2v-omni",
 "input":{"prompt":"...","media":[{"type":"image_url","url":"https://..."}]},
 "parameters":{"resolution":"1080P","duration":5,"aspect_ratio":"9:16","watermark":false}}
```
报错递进（每步修一个，失败不计费）：
1. `input.images` → `input.media is an empty array. It must contain at least one item.`
2. `media:[{type:"image",url}]` → `input.media.type must be image_url or video_url`
3. `media:[{type:"image_url","image_url":{"url":…}}]` → `input.media[0].url are missing or empty`
4. ✅ 正解：`"media": [{"type": "image_url", "url": "https://…"}]` + `parameters.aspect_ratio`
（缺 `aspect_ratio` 时另报 `Required field aspect_ratio are missing or empty`）
- 提示词绑定：`media:[{"type":"image_url","url":...,"ref_name":"剃须刀"}]`，prompt 用 **`@剃须刀 `** 绑定（`ref_name` 全局唯一、`@` 后必须有空格）；不绑则模型自动全局解析。

### 万相「参考生视频」两个版本入参完全不同（`wan2.6-r2v-flash` / `wan2.7-r2v`）
⚠️ 把 2.7 的 `media` 格式发给 2.6-r2v-flash，会立刻返回
`InvalidParameter: please provide reference_video_urls or reference_urls.`（参数校验阶段失败，**不扣费**，但白等一轮。）

| | **`wan2.6-r2v-flash`**（便宜/优先试） | **`wan2.7-r2v`**（贵/音色可控） |
|---|---|---|
| 参考素材入参 | `input.reference_urls` = **字符串数组**（图0-5、视频0-3，合计≤5） | `input.media` = **对象数组**，元素 `{type, url}`，type=`reference_image`/`reference_video`/`first_frame` |
| prompt 里怎么指代 | **`character1`、`character2`**（第1个URL=character1） | **`图1`、`图2`、`视频1`** |
| 分辨率参数 | `parameters.size` = **具体数值** `"1080*1920"`（9:16）／`"1920*1080"`／`"720*1280"`；**不能写 `1080P` 或 `9:16`** | `parameters.resolution`=`1080P` + `parameters.ratio`=`9:16` |
| 时长 | `duration` 2-10 整数 | `duration` 2-15（含参考视频时2-10） |
| 有声 | `parameters.audio` = true（**仅 flash 支持此参数**，默认 true，模型自己配音） | **默认有声**，无需 audio 参数 |
| 音色参考 | ❌ 不支持 `reference_voice`（音色由模型自选） | ✅ `media` 元素内加 `reference_voice`（mp3，1-10s）锁音色 |
| 镜头数 | `shot_type` = `multi`（多镜头）/ `single`（默认单镜头） | 同左 |
| prompt 长度上限 | 1500 字符 | 5000 字符 |

- 选型：**先用 `wan2.6-r2v-flash`** —— 便宜（有免费额度），`audio:true` 会按 prompt 里引号内的台词自动配音，口型同步（代价：音色由模型定，**不能克隆**）；音色/情绪有硬要求时才升级 `wan2.7-r2v`（1080P 约 1 元/秒，贵 10 倍以上）。
- 多个参考图指同一主体（如产品正/侧两个角度）时，**必须在 prompt 里写明"character1 和 character2 是同一个主体"**，否则模型可能当成两个角色生成两份。
- flash 调用骨架：
```python
body = {
  "model": "wan2.6-r2v-flash",
  "input": {"prompt": PROMPT, "reference_urls": [REF1, REF2, REF3]},   # 顺序 = character1/2/3
  "parameters": {"size": "1080*1920", "duration": 10, "audio": True,
                 "shot_type": "multi", "watermark": False},
}
```

### `wan2.1-vace-plus`（VACE，换真机路线）
同一 video-synthesis 端点，`input.function` 只接受这 5 个：**`image_reference`**（参考图生视频，字段 `ref_images_url` 数组 + `prompt`）、`video_repainting`、`video_edit`（`video_url` + `mask_image_url`/`mask_video_url` + `ref_images_url`）、`video_extension`、`video_outpainting`。
`video_edit` 才是"把已生成画面里的产品换成真机"的正路，但需要先有产品区域的 mask。
字段反推法有效：先发空 input → `prompt must contain words` → 再补 prompt → 才报 `function not supported!`（顺序报错，一次只报一个缺失项）→ **别一次塞全，逐个补**。

### `make_ad.py` 换引擎（项目 JSON 加一行 `model`）
```json
{ "runid": "wh", "model": "wan3.0-video", "resolution": "720P", "duration": 5, "ratio": "9:16" }
```
`make_ad.py` 的 `step_submit` **按模型自动切换 input 形态**（2026-09-18 补丁）：

| 引擎 | 参考图字段 | 备注 |
|---|---|---|
| `wan3.0-video`（产品镜主力） | `input.images = [url, ...]` | 自动带 `parameters.watermark = false`（默认可能烧水印） |
| `wan2.7-r2v`（纯人物戏） | `input.media = [{"type":"reference_image","url":...}]` | **不写 `model` 时的默认值** |

补丁位置（别重复踩）：`step_submit` 里先算 `model = proj.get("model", "wan2.7-r2v")`，再 `if "3.0" in model:` 分支决定 `inp` 与是否加 `watermark`。

⚠️ **`duration` 是项目级字段**（`parameters.duration`）→ **5s 段和 10s 段不能放同一个项目**。段时长混排时拆成两个配置，顺序跑（本轮：`project_w30_hooks.json` = 3×5s，`project_w30_body.json` = 2×10s），每个配置照常 `--steps plan,submit,fetch`；拆开还能**分别核验、失败只重跑一半**。

### 参考图指代语法速查

| 引擎 | 指代写法 |
|---|---|
| `wan3.0-video` / 万相 3.0 | `图1` / `图片1`（图片/视频/音频**分别计数**；最多 10 张） |
| `wan2.7-r2v` | `图1` / `图2` / `视频1` |
| `wan2.6-r2v-flash` | `character1` / `character2` |
| `kling-v3-omni` | `<<<image_1>>>` / `<<<image_2>>>`（按 media 数组顺序） |
| PixVerse | `@剃须刀 `（`ref_name`，全局唯一、`@` 后必须有空格） |
| Vidu Q3-Ad | `(图1)(图2)` 或「商品是…」 |

---

## 三、价格表（元/秒，控制台详情页 / 官方文档实测）

| 模型 id | 1080P | 720P | 其他档 | 备注 |
|---|---|---|---|---|
| `wan3.0-video` | 1.2 | 0.6 | 480P 0.3 | 最长 30 秒；1080P 30s ≈ 36 元 |
| `kling/kling-v3-video-generation` | 1.2（无声 0.8） | 0.9（无声 0.6） | 4K 3.0 | |
| `vidu/viduq3-ad_reference2video` | **0.90625** | 0.75 | — | 官方定位"上传商品图直出 16 秒广告" |
| `pixverse/pixverse-v6-r2v-omni` | **带参考视频 1.36**／不带参考 0.68（无声 0.53） | 带参考 0.72／不带参考 0.36（无声 0.27） | 360P 0.21、540P 0.27 | |
| `pixverse/pixverse-v6-r2v` | 0.68（有声）/ 0.53（无声） | 0.36 / 0.27 | — | |
| `wan2.7-r2v` | 1.0 | 0.6 | — | 产品镜已退役 |
| `wan2.1-vace-plus` | 0.733924（std） | 0.734 | — | 本账号服务端不可用 |

❌ 已作废（2026-09-16）：Vidu 单价 `0.9375`／720P `0.78125` → 现：**`0.90625`／720P `0.75`**（控制台详情页实测）。

**计费常识与报价纪律：**
- ⚠️ **电商 r2v 必然落在"带参考视频"档**（`pixverse-v6-r2v-omni` 1080P 1.36 元/秒 → 5s = 6.8 元）。**报预算别用不带参考的 0.68**（第一次就报错价）。
- ⚠️ **三方直供模型不支持免费额度**（详情页写明"免费额度：不支持开启"）；自研 `wan*` 免开通可直调。
- **提交失败不计费**（prompt 超限 / 模型 id 写错 / 参数校验失败这类错误是 0 成本，可放心先探测）。
- 轮次成本口径：报「本轮花了多少 + 累计」，并说清失败/重跑部分是否计费。实测本轮 = 第一轮 21 元（3 钩子 9 + 正片/车内 12）→ 核验后定点重做 4 段 18 元，**累计 39 元**；装配/重建/交付全 0 元。同规格四家对比做一版 ≈ 17 元（Vidu 4.5 + PixVerse 6.8 + 可灵 6.0）。
- 省钱：`--steps plan` 免费（先看拼装出的 prompt 字数与结构，再提交）；核验先于装配（装配 0 元但会覆盖交付文件，未通过核验不装配）。

---

## 四、选型结论（2026-09-18 定稿，不再重议）

**引擎分工（同题横评 + 复跑验证）：**

| 用途 | 引擎 | 关键限制 |
|---|---|---|
| **产品镜**（画面里有产品） | **`wan3.0-video`** ✅ 主力 | 0.6 元/秒；免开通；支持 30s；产品一次就对、整段不掉金 |
| **纯人物戏**（不出产品） | `kling-v3-omni` ✅ 真人质感最好 | **prompt 硬上限 2500 字符**；产品整段会崩 |
| 最便宜档（非产品镜） | `pixverse-v6-r2v-omni` | 0.27 元/秒；但把产品画成超大罐子 |
| ✗ | `vidu-q3-ad` | 720P 下吐横屏（字段不吃 9:16） |
| ✗ 服务端不可用 | `wan2.1-vace-plus` | `Failed to invoke scheduler`（换真机路线暂不可用） |

**产品保真横评（同一段产品锁 prompt 2603 字 + 同 5 张参考图 + 5s/720P，5 家同题）：**

| 引擎 | 产品形态 | 刀网金色 | logo | 整段稳定 | 结论 |
|---|---|---|---|---|---|
| **`wan3.0-video`** | ✅ 等粗直筒、长径比≈2 | ✅✅ 同心圆+放射菱形网格+宽黑环（3.5s 特写几乎等于官方真值） | ✅ Haier 干净 | ✅ 全程不掉金、不变形 | **产品镜首选**（自研免开通、720P 0.6 元/秒、支持 30s） |
| `kling/kling-v3-omni-video-generation` | ✗ 偏胖偏短，3.5s 后机头变胶囊、4.5s 金网消失 | ✗ 会丢 | ✅ | ✗ **产品整段崩坏** | 真人质感最好 → **只用于不出产品的纯人物戏** |
| `pixverse/pixverse-v6-r2v-omni` | ✗✗ 产品被画成超大罐子 | △ 有金 | ✗ | ✗ | 暂不用 |
| `vidu/viduq3-ad_reference2video` | 产品太小看不清；**resolution=720P 时吐出横屏**（字段没吃 9:16） | 不可评 | — | — | 暂不用；要用得给 aspect 字段 |
| `wan2.7-r2v`（原主线） | ✗ 产品小、常看不清、反复返工 | ✗ 易洗成银白 | △ | ✗ | **产品镜退役**（人物戏仍可用） |
| `wanx2.1-vace-plus`（参考/换产品） | — | — | — | — | ⚠️ **两次都 `InternalError: Failed to invoke scheduler!`** → 本账号/地域目前**不可用**，别押在这条路上 |

**落地分工（写进分镜规范）**：产品出现/特写镜 → `wan3.0-video`（同价 0.6 元/秒，但产品一次就对）；不出现产品的纯人物镜 → `kling-v3-omni`；产品镜仍必须放大核（刀网是否饱和香槟金 / 机头是否等粗 / logo 是否乱码）。

**四维质量实测（同参考图 + 同 prompt + 5s）：**

| 模型 | 影棚感 | 真人感 | 产品保真 | 多镜头/广告感 |
|---|---|---|---|---|
| **Kling V3**（mode:std 720×1280） | ✓✓ 灰无缝背景 + 棚灯入画 | ✓✓ | ✓✓ 修长圆柱 + **Haier logo 清晰** + **平面金网** | ✓✓ **自动分镜切镜（中景→面部→产品特写）** |
| `wan3.0-video`（1080×1920） | ✓✓ | ✓ | ✓✓ **最佳**（1.93:1 修长 / 平面金网 / logo 正确） | ✗ 单镜头 |
| `vidu/viduq3-ad`（1914×1084） | ✗ 自然家居窗光（未遵循影棚 prompt） | ✓✓ | ◐ 修长黑筒 + 顶部金圈，logo 不明显 | ✗ 单镜头 |
| PixVerse V6-r2v-omni | 待验 | 待验 | 待验 | 待验 |

- 要"广告感 / 分镜切镜" → **Kling V3（`mode:"pro"` 出 1080P）**；要"产品 1:1 保真" → **`wan3.0-video`**；Vidu 广告版适合接受横屏 + 自然场景的口播。
- 两个维度要分开看：①**形态准确度** → PixVerse V6 第一；②**材质/真实感**（哑光反射、真人融合自然度）→ Vidu Q3-Ad 与可灵最好。
- **影棚质感 prompt 语汇（实测有效）**：「影棚白色无缝背景 + 柔光箱主光 + 侧逆光勾边 + 浅景深 + 女主持产品展示」→ 干净的棚拍感、真人真实（无塑胶感）、手指正常。
- **提示词纪律**：不要用「修长」形容圆柱（会把产品推向笔形先验），用客观几何 + 参照图编号：「图1、图2 是同一件产品的正面和侧面照，画面中的商品必须严格按图1、图2 还原：高度只有直径的约 1.9 倍（74×39mm）的矮宽圆柱…」

**分辨率口径（全流程锁 720P）**：生成一律 720P，成片由装配器升到 1080×1920。产品特写要清晰的正解是**官方真像素图做动效**，不是花 1.8 倍钱把整片 1080P 重跑一遍。（`wan3.0-video` 实测：720P 0.6 元/秒；1080P 1.2 元/秒 ≈ ×2。）

---

## 五、踩坑（踩过的，别再踩）

1. **🔴 入口受理 ≠ 模型可用**。提交返回 `task_id` 只代表请求格式被接受，权限判在执行阶段：
   ```
   Vidu / PixVerse / 可灵 未开通 → task_status: FAILED
   InvalidParameter: The product is not activated, please confirm that you have activated
   products and try again after activation.
   ```
   （也见于空参数探测："受理"返回 task_id，随后执行态 FAILED。）→ **对用户下"可用"结论前必须真跑一条最低规格任务看到 `SUCCEEDED`**。
2. **🔴 开通路径**：百炼控制台 →「模型广场」→ 搜模型 → 开通该产品（免费/需同意条款；个别厂商模型要求企业认证）。**自研（`wan*`）无需开通；第三方（`vendor/model` 命名，模型卡片标"三方直供"）才需要**；API 层无法开通。
3. **🔴 控制台真名 ≠ 常用叫法**：搜中文"可灵"= **零结果**，必须搜英文 **`Kling`**（卡片名 **Kling Video 3.0**）。同理 Vidu / PixVerse 用英文搜（卡片名 `ViduQ3-Ad_reference2video`、`PixVerse-V6-r2v-omni`）。**让用户去开通前，先自己搜一遍确认卡片名，别给中文名。**
4. 💡 **模型广场/详情页无需登录即可浏览**：`https://bailian.console.aliyun.com/cn-beijing/model/market` → 直接拿到模型真名、id、单价表、三方直供标签；详情页 URL 形如 `…/model/market/detail/<urlencode(vendor/model)>`（可当深链发给用户，省去搜索）。
5. **🔴 静默忽略：不报错 ≠ 参数生效**。未知/不支持的参数不报错、被直接丢掉。实测：可灵同时传 `resolution:"1080P"` 与 `mode:"std"` → 出来仍是 **720×1280**。⇒ 任何出片后**必须 `ffprobe` 回验宽高/时长**，不能凭"提交成功"下结论。
6. **🚨 `wan3.0-video` 会把「参考图1」直接当成画面首帧**。图1 设成"刀网微距校准图"，结果每条片子开头 0.8 秒都是同一张金网微距（三个不同 hook 的开场完全一样，prompt 里写"开场第 1 秒就是他本人"完全无效）。→ 想控制开场，**先换图1**（换成人物或场景图；代价：少一个金色校准锚点，需重核刀网颜色）。这是引擎级特性，改 prompt 无效。**核验抽帧必须含首帧（0.2~0.5s）**，只看中后段会漏掉这类系统性问题。
7. ⚠️ **可灵 prompt 硬上限 2500 字符**：超了直接 `InvalidParameter input.prompt: size must be between 0 and 2500`（产品锁 2340 字 + 分镜 ≈2600 字 → **给可灵必须压缩锁**；失败提交不计费）。
8. ⚠️ **计费限流**：短时间连发会 `Throttling.RateQuota`（横评时全组同时提交要留间隔）。
9. **🔴 参考图失真头号根因 = 参考图根本没被模型接收到**（字段写错/模型选错），模型只能走训练先验 → 产品被画成"细长笔形迷你剃须刀"。**不是提示词不够强，是参考图没生效。**
10. **产品保真必须放大逐帧核对，不能看整体观感下结论**（首轮凭"影棚感+整体像"把万相 3.0 误判为保真最好，放大后发现它把剃须刀画成了**理发推子**——顶部梳齿状刀头 + 机身圆钮）。
11. **产品镜的终极解 = 官方真像素插入镜（0 API 成本）**：脚本 `scripts/build_official_product_insert.py` —— 裁官方图（刀网微距 / 正面全身 / 底部端面）合成 3s 竖屏缓推特写，片内结构改为「钩子 5s(AI) + 官方真机 3s + 正片 7s(AI) = 15s」，字幕/花字整体 +3s、旁白按字幕 start 自动重排。**产品 100% 保真、认得出是什么东西**，这是"AI 画不像"时唯一不返工的路线。
12. **⚠️ SKILL.md 过期表述**：SKILL.md「路径判断」表①写的 **`wan2.7-r2v` ✅ 当前主线** 已过期 → 现行：**产品镜 = `wan3.0-video`**。

**可复用的同题对比法（选型/评测都用这套）：**
1. **同一组素材**（同参考图）+ **同一 prompt** + **同一规格**（5s / 1080P / 9:16）分别提交各家；
2. 逐条 `ffprobe` **回验宽高与时长**（别信请求参数）；
3. `ffmpeg -vf fps=1.2,scale=300:-1,tile=3x2` 抽帧拼图 → 逐张按**四维**判读（影棚感 / 真人感 / 产品保真 / 是否多镜头）；
4. 产品细节要看**放大裁切**（机身比例、刀网平面还是凸面、logo 是否乱码）；
5. 结果落表 + 报**本轮花费与累计花费**（用户成本敏感，主动报）。
6. 对比片合成：`/tmp/cmp/build_cmp.py`（2×2 xstack + ASS 标签；`force_original_aspect_ratio=decrease`+pad 保留横屏原帧，不裁切）。
7. **字段探测方法论（省钱）**：失败不计费，可放心用「提交 → 读报错 → 补字段」反推 schema，比啃动态渲染的控制台文档快 10 倍。

---

## 六、已作废条目（见到这些做法，停）

| 位置 | 作废内容 | 作废于 |
|---|---|---|
| 本组旧文 | 「4 家都吃 `input.images`」+「参数统一 `resolution`+`duration`」 | 2026-09-16（各家字段不同） |
| 本组旧文 | 万相 3.0 参考图 `input.media:[{"type":"reference_image"}]` | 2026-09-16（正解 `input.images`） |
| 本组旧文 | Vidu 单价 `0.9375`／720P `0.78125` | 2026-09-16（现 `0.90625`／`0.75`） |
| SKILL.md「路径判断」 | `wan2.7-r2v` ✅ 当前主线 | 2026-09-18（产品镜改为 `wan3.0-video`） |
| 本组旧文 | 产品镜 = `wan2.7-r2v` | 2026-09-18（产品小／看不清／洗成银白＝返工根因） |
| 本组旧文 | `kling-v3-video-generation` 只支持 `first_frame`、不支持参考生视频 | 2026-09-16（该 id + `input.images` 实测 SUCCEEDED；omni 变体才走 `media`/refer） |
