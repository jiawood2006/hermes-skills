# 百炼视频模型货架：清单 / 单价 / 统一请求式 / 开通要求（2026-09-16 实测）

来源：① 官方文档页 firecrawl 抓取的价格表 ② 对本账号真实提交+轮询的实测结果。
价格是**官方原价**（元/秒，视频按秒计费），限时折扣未计。

## 一、本账号可枚举的模型（先看货架再选型）
```bash
# page_size 上限 100，超出报 "Pagination parameter page_size exceeds the length limit"
curl -s -H "Authorization: Bearer $KEY" \
  "https://dashscope.aliyuncs.com/api/v1/quotas?page_size=100&page_no=1"
```
返回 `output.total`（本账号 500）+ 每条 `{model, workspace_id, model_limit}`。
**该接口在账号欠费时仍可调**，是盘点货架最省事的入口。

## 二、视频模型对比（1080P 官方单价）

| 模型 id | 1080P 单价 | 关键能力 | 电商用法 |
|---|---|---|---|
| `wan2.7-r2v`（现用） | **1.0 元/秒**（720P 0.6） | 最多 **5 个**图/视频混合参考 + 音频音色参考 | 人物剧情 + 对白口型（本技能主线） |
| `wan3.0-video`（自家新版） | **1.2 元/秒**（720P 0.6 / 480P 0.3） | **全能参考 All-in-One**：文本/图像/视频/音频/文件/链接输入；**最长 30 秒** | 一条成片的长镜头叙事（30s≈36 元） |
| `vidu/viduq3-ad_reference2video` | **0.9375 元/秒**（720P 0.78125） | **广告专用**的参考生视频：1-7 张参考图；**声画同出 + 口型同步**；自带粒子/流体/运镜/光影特效 | 带货口播 + 产品展示（首选替代品） |
| `pixverse/pixverse-v6-r2v` | **0.68 元/秒**（有声）/ **0.53**（无声）；720P 0.36/0.27 | **多主体参考 2-7 图**（'r2v 全球第二'）；**15 秒**长素材；原生音乐；官方文档点名"电商产品特写" | 产品/场景 B-roll，批量试错最便宜 |
| `kling/kling-v3-video-generation`（另有 `-turbo` / `-omni`） | **1.2 元/秒**（有声）/ **0.8**（无声）；720P 0.9/0.6；**4K 3 元/秒** | 真人身段/动作自然度口碑最好、中文 prompt 友好、快手生态 | 真人剧情镜头 |

Vidu 家族还有 `viduq3-drama_reference2video`（短剧）/ `viduq3-mix_reference2video`（均衡）等变体。

## 三、统一请求式（4 家都吃同一套，别按厂商分叉写）
```bash
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
Header: Authorization: Bearer $KEY ; Content-Type: application/json ; X-DashScope-Async: enable
{
  "model": "<vendor/model 或 自研模型名>",
  "input": { "prompt": "…", "images": ["https://…/ref1.jpg", "https://…/ref2.jpg"] },
  "parameters": { "resolution": "1080P", "duration": 5, "watermark": false }
}
# → output.task_id ；轮询 GET https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}
```
- 参考图字段就是 **`input.images`**（数组，公网 URL）——4 家实测都受理，不用猜 `reference_urls` / `img_urls`。
- 参数就用 `resolution:"1080P"` + `duration:5`（4 家都通过）；不要写 `size:"1080*1920"`（那是 wan2.6-flash 系的口径）。
- 字段名不确定时**用坏参数反推**（发空 input 看 `Field required: …`），比翻文档快且不花钱。

## 四、🔴 铁律：入口受理 ≠ 模型可用（本次实测踩到）
提交返回 `task_id` **只代表请求格式被接受**，权限判在执行阶段：
```
Vidu / PixVerse / 可灵 未开通 → task_status: FAILED
InvalidParameter: The product is not activated, please confirm that you have activated
products and try again after activation.
```
- 结果：我先报"4 家可调"，实际 3 家跑不了，只能回头修正 → **对用户下"可用"结论前必须真跑一条最低规格任务看到 `SUCCEEDED`**。
- 修复路径：百炼控制台 →「模型广场」→ 搜模型 → 开通该产品（免费/需同意条款；个别厂商模型要求企业认证）。
- 自研模型（wan 系列）无需开通；第三方（`vendor/model` 命名）才需要。

## 五、辅助能力（同账号可调，直击电商制作痛点）
| 用途 | 模型 |
|---|---|
| **把已生成镜头里的产品替换成真机**（比 prompt 约束彻底） | `wan2.7-videoedit`、`wan2.1-vace-plus` |
| 口型对齐我们的配音 | `pixverse/pixverse-lipsync`、`videoretalk`、`wan2.2-s2v` |
| 运镜/肢体控制、换人 | `pixverse/pixverse-motioncontrol`、`wan2.2-animate-mix`、`wan2.2-animate-move` |
| 超分/提质 | `pixverse/pixverse-upscale` |
| 生图/改图（做参考图、场景图） | `qwen-image-3.0-pro`、`qwen-image-edit-max`、`wan2.7-image-pro`、`z-image-turbo` |

## 七、🔴 2026-09-18 产品保真横评结论：**产品镜改用 wan3.0-video**

同一段产品锁 prompt（2603 字）+ 同 5 张参考图（刀网微距/正面/底部/真手/男主）+ 5s/720P，5 家同题对比
（图：`/tmp/cmp_engines/cmp_full.jpg`、`multiframe.jpg`）：

| 引擎 | 产品形态 | 刀网金色 | logo | 整段稳定 | 结论 |
|---|---|---|---|---|---|
| **`wan3.0-video`** | ✅ 等粗直筒、长径比≈2 | ✅✅ 同心圆+放射菱形网格+宽黑环（3.5s 特写几乎等于官方真值） | ✅ Haier 干净 | ✅ 全程不掉金、不变形 | **产品镜首选**（自研免开通、720P 0.6 元/秒、支持 30s） |
| `kling/kling-v3-omni-video-generation` | ✗ 偏胖偏短，3.5s 后机头变胶囊、4.5s 金网消失 | ✗ 会丢 | ✅ | ✗ **产品整段崩坏** | 真人质感最好 → **只用于不出产品的纯人物戏** |
| `pixverse/pixverse-v6-r2v-omni` | ✗✗ 产品被画成超大罐子 | △ 有金 | ✗ | ✗ | 暂不用 |
| `vidu/viduq3-ad_reference2video` | 产品太小看不清；**resolution=720P 时吐出横屏**（字段没吃 9:16）| 不可评 | — | — | 暂不用；要用得给 aspect 字段 |
| `wan2.7-r2v`（原主线） | ✗ 产品小、常看不清、反复返工 | ✗ 易洗成银白 | △ | ✗ | **产品镜退役**（人物戏仍可用） |
| `wanx2.1-vace-plus`（参考/换产品） | — | — | — | — | ⚠️ **两次都 `InternalError: Failed to invoke scheduler!`** → 本账号/地域目前**不可用**，别押在这条路上 |

**落地分工（写进分镜规范）**：产品出现/特写镜 → `wan3.0-video`（同价 0.6 元/秒，但产品一次就对）；
不出现产品的纯人物镜 → `kling-v3-omni`；产品镜仍必须放大核（刀网是否饱和香槟金/机头是否等粗/logo 是否乱码）。

## 六、海外模型的定位

### 六·补 A：2026-09-18 实测补充（产品保真横评时踩到的硬事实）

- ⚠️ **可灵 prompt 硬上限 2500 字符**：超了直接 `InvalidParameter input.prompt: size must be between 0 and 2500`
  （我们的产品锁 2340 字 + 分镜 ≈2600 字 → **给可灵必须压缩锁**；失败提交不计费）。
- ✅ **wan3.0-video 吃长 prompt**（2603 字一次通过），720P 档 5s = 3 元。
- **VACE-Plus（`wanx2.1-vace-plus`）接口**（官方指南 `help.aliyun.com/zh/model-studio/wan-vace-guide`）：
  - 同一 video-synthesis 端点，`input.function` 只接受这 5 个：**`image_reference`**（参考图生视频，
    字段 `ref_images_url` 数组 + `prompt`）、`video_repainting`、`video_edit`（`video_url` + `mask_image_url`
    /`mask_video_url` + `ref_images_url`）、`video_extension`、`video_outpainting`。
  - 价格 **0.733924 元/秒**（std；官方页 help.aliyun.com/zh/model-studio/wan2-1-vace-plus）。
  - **`video_edit` 才是"把已生成画面里的产品换成真机"的正路**，但需要先有产品区域的 mask。
  - 字段反推法有效：先发空 input → `prompt must contain words` → 再补 prompt → 才报 `function not supported!`
    （顺序报错，一次只报一个缺失项）→ **别一次塞全，逐个补**。
  - ⚠️ 计费限流：短时间连发会 `Throttling.RateQuota`（横评时全组同时提交要留间隔）。

Veo 3.1 / Sora 2 / Runway Gen-4：画面质感天花板，但大陆接入需海外网络+外币支付，投放端还有 AI 内容标识合规要求
→ **只当"看片学审美"的参考，不做生产主线**。向用户说明时讲清这三条门槛，别只夸质量。

### 六·补 B：2026-09-18 夜 · wan3.0-video 实跑三小时的关键行为

1. 🚨 **wan3.0-video 会把「参考图1」直接当成画面首帧**。我们把图1 设成"刀网微距校准图"，
   结果**每一条片子的开头 0.8 秒都是同一张金网微距**（三个不同 hook 的开场完全一样，
   prompt 里写"开场第 1 秒就是他本人"完全无效）。→ 想控制开场，**先换图1**（换成人物或场景图；
   代价：少一个金色校准锚点，需重核刀网颜色）。这类"参考图即首帧"的行为是引擎级特性，改 prompt 无效。
2. **真机刀头 = 向上拱起的金色球面网罩（穹顶状）**，不是平的圆盘、也不是平的黑色盖子 ——
   这是从官方 `拉页图-7.jpg` 对照出来的。之前锁里只写"黑环＋金色网面"，AI 就画成**平的黑色盖子**。
   已写进 `product_profiles.json` 的 `video_lock.mesh/form` 与锁模板【机头与机身】。
3. **手持镜片的比例下限写错了会反向伤害**：真机 74mm ≈ **手掌长度的 0.7~0.8 倍**（比手掌略短）。
   早前为了治"产品太小"写了"≈手掌长 1.1~1.3 倍"→ AI 把机器画成**比手掌还长**，看起来就是**保温杯**。
   正确写法：`0.7~0.8 倍`+「不少于画面高 1/8」+「绝不许比手掌还长」。
4. **产品镜的终极解 = 官方真像素插入镜（0 API 成本）**：脚本
   `scripts/build_official_product_insert.py` —— 裁官方图（刀网微距 / 正面全身 / 底部端面）合成 3s 竖屏缓推特写，
   片内结构改为「钩子 5s(AI) + 官方真机 3s + 正片 7s(AI) = 15s」，字幕/花字整体 +3s、旁白按字幕 start 自动重排。
   **产品 100% 保真、认得出是什么东西**，这是"AI 画不像"时唯一不返工的路线。
