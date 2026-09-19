# 第三方视频模型：字段 / 参数 / 价格 / 实测质量（2026-09-16 实测修正版）

> ⚠️ **本文覆盖并修正** `bailian-video-model-catalog.md` 中的两处过时结论：
> ① "4 家都吃 `input.images`" ❌ ② "参数用 `resolution`+`duration` 4 家都通过" ❌
> 凡与本文冲突处，**以本文为准**。

## 一、🔴 各家请求字段不同（这是最大的坑）

endpoint 统一（都是一样的）：
```bash
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
Header: Authorization: Bearer $KEY ; Content-Type: application/json ; X-DashScope-Async: enable
# → output.task_id ; 轮询 GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
```

但 **input / parameters 字段按模型写，不能一套通用**（下表全部实测跑出 SUCCEEDED）：

| 模型 id | 参考图字段 | 关键参数 | 实测输出 |
|---|---|---|---|
| `wan3.0-video` | `input.images: [url…]` | `{duration, ratio:"9:16"}` 或 `{size:"1080*1920"}` | 1080×1920 竖屏 ✓（`aspect_ratio` 被静默忽略） |
| `kling/kling-v3-video-generation` | `input.images: [url…]` | `{mode:"std"\|"pro", duration, aspect_ratio:"9:16"}` | **`mode:"std"` → 720×1280**（同时传 `resolution:"1080P"` 也无效） |
| `vidu/viduq3-ad_reference2video` | **`input.media: [{type:"image", url}]`** | `{resolution:"1080P", duration:5}` | **1914×1084 横屏** |
| `pixverse/pixverse-v6-r2v-omni` | **`input.media: [{type:"image_url", url}]`**（`url` 为顶层字段） | **`aspect_ratio` 必填** | 按 aspect_ratio 出片 |

**PixVerse 的逐层报错（照这个反推最快，失败不计费）**：
1. 只发 `input.images` → `input.media is an empty array. It must contain at least one item.`
2. 发 `media:[{type:"image",url}]` → `input.media.type must be image_url or video_url`
3. 发 `media:[{type:"image_url","image_url":{"url":…}}]` → `input.media[0].url are missing or empty`
4. ✅ 正解：`"media": [{"type": "image_url", "url": "https://…"}]` + `parameters.aspect_ratio`
（缺 `aspect_ratio` 时另报 `Required field aspect_ratio are missing or empty`）

## 二、🔴 静默忽略：不报错 ≠ 参数生效

**未知/不支持的参数不报错、被直接丢掉。** 实测：可灵同时传 `resolution:"1080P"` 与 `mode:"std"` →
出来仍是 **720×1280**。⇒ 任何出片后**必须 `ffprobe` 回验宽高/时长**，不能凭"提交成功"下结论。

## 三、价格（控制台详情页实测，元/秒）

| 模型 | 1080P | 720P | 备注 |
|---|---|---|---|
| `wan3.0-video` | 1.2 | 0.6（480P 0.3） | 最长 30 秒 |
| `kling/kling-v3-video-generation` | 1.2（无声 0.8） | 0.9（无声 0.6） | 4K 3.0 |
| `vidu/viduq3-ad_reference2video` | **0.90625** | 0.75 | 官方定位"上传商品图直出 16 秒广告" |
| `pixverse/pixverse-v6-r2v-omni` | **带参考视频 1.36**／不带参考 0.68（无声 0.53） | 带参考 0.72／不带参考 0.36 | 360P 0.21、540P 0.27 |

⚠️ **电商 r2v 必然落在"带参考视频"档**（1080P 1.36 元/秒 → 5s = 6.8 元）。**报预算别用不带参考的 0.68**（本会话第一次就报错价）。
⚠️ **三方直供模型不支持免费额度**（详情页"免费额度：不支持开启"）。

## 四、开通与真名

- 自研（`wan*`）**无需开通**；第三方（`vendor/model` 命名，模型卡片标 **"三方直供"**）**必须先开通**：
  百炼控制台 → 模型广场 → 搜模型 → 开通。未开通时提交会**先返回 task_id、随后立刻 FAILED**：
  `InvalidParameter: The product is not activated, please confirm that you have activated products and try again after activation.`
  （官方错误码文档已确认此含义 = 模型服务未开通）
- 🔴 **控制台真名 ≠ 常用叫法**：搜中文"可灵" = **零结果**，必须搜英文 **`Kling`**（卡片名 **Kling Video 3.0**）。
  同理 Vidu/PixVerse 用英文搜。**让用户去开通前，先自己搜一遍确认卡片名，别给中文名。**
- 💡 **模型广场/详情页无需登录即可浏览**：`https://bailian.console.aliyun.com/cn-beijing/model/market`
  可直接拿到**模型真名、id、单价表、三方直供标签**；详情页 URL 形如
  `…/model/market/detail/<urlencode(vendor/model)>`（可当深链发给用户，省去搜索）。

## 五、实测质量（同参考图 + 同 prompt + 5s，四维评分）

| 模型 | 影棚感 | 真人感 | 产品保真 | 多镜头/广告感 |
|---|---|---|---|---|
| **Kling V3**（mode:std 720×1280） | ✓✓ 灰无缝背景 + 棚灯入画 | ✓✓ | ✓✓ 修长圆柱 + **Haier logo 清晰** + **平面金网** | ✓✓ **自动分镜切镜（中景→面部→产品特写）** |
| `wan3.0-video`（1080×1920） | ✓✓ | ✓ | ✓✓ **最佳**（1.93:1 修长 / 平面金网 / logo 正确） | ✗ 单镜头 |
| `vidu/viduq3-ad`（1914×1084） | ✗ 自然家居窗光（未遵循影棚 prompt） | ✓✓ | ◐ 修长黑筒 + 顶部金圈，logo 不明显 | ✗ 单镜头 |
| PixVerse V6-r2v-omni | 待验 | 待验 | 待验 | 待验 |

**选型建议**：要"广告感/分镜切镜"→ **Kling V3（`mode:"pro"` 出 1080P）**；要"产品 1:1 保真"→ **wan3.0**；
Vidu 广告版适合接受横屏+自然场景的口播。

## 六、可复用的同题对比法（选型/评测都用这套）

1. **同一组素材**（同参考图）+ **同一 prompt** + **同一规格**（5s / 1080P / 9:16）分别提交各家；
2. 逐条 `ffprobe` **回验宽高与时长**（别信请求参数）；
3. `ffmpeg -vf fps=1.2,scale=300:-1,tile=3x2` 抽帧拼图 → 逐张按**四维**判读（影棚感 / 真人感 / 产品保真 / 是否多镜头）；
4. 产品细节要看**放大裁切**（机身比例、刀网平面还是凸面、logo 是否乱码）；
5. 结果落表 + 报**本轮花费与累计花费**（用户成本敏感，主动报）。
