# 万相 3.0（wan3.0-video）实测：能力、参数、价格、产品保真

> 实测时间 2026-09-16（HSQ1 剃须刀），账号=百炼业务空间 6034154。
> 结论一句话：**万相 3.0 是阿里云自研、无需控制台开通即可直调，产品保真明显优于 wan2.7-r2v**。

## 1. 价格（官方文档，1080P）
| 分辨率 | 单价 |
|---|---|
| 480P | 0.3 元/秒 |
| 720P | 0.6 元/秒 |
| **1080P** | **1.2 元/秒** |

- 单条最长 **30 秒** → 1080P 30s ≈ 36 元。
- 支持多模态输入（文本 / 图像 / 视频 / 音频 / 文件 / 链接）。

## 2. 参数（实测踩坑，务必照抄）
endpoint（与万相 2.x 同一个）：
`POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`
header：`Authorization: Bearer $DASHSCOPE_KEY` + `X-DashScope-Async: enable`

```json
{
  "model": "wan3.0-video",
  "input": { "prompt": "...", "images": ["https://.../a.jpg", "https://.../b.jpg"] },
  "parameters": { "duration": 5, "ratio": "9:16", "resolution": "1080P" }
}
```

**竖屏参数实测（4 组对照，同一 prompt/素材）**：
| 参数写法 | 实际输出 | 结论 |
|---|---|---|
| `ratio:"9:16"` | 720×1280 | ✅ 生效 |
| `size:"720*1280"` | 720×1280 | ✅ 生效 |
| `size:"1080x1920"`（小写x） | 1080×1920 | ✅ 生效 |
| `aspect_ratio:"9:16"` | 1280×720（横屏） | ❌ 被忽略 |

- ⚠️ **未知参数不报错、被静默忽略** → 不能靠「没报错」判断参数生效，必须 ffprobe 回验宽高。
- 参考图字段用 `input.images`（数组，实测多家第三方模型也吃这个字段）。
- `input.images` 传坏 URL 时请求会被受理 → 说明字段被识别，但不是「会用」的证明；必须出片回看产品。

## 3. 产品保真实测（同一套参考图：两张 1.93:1 竖立官方图）
| 项目 | wan2.7-r2v（v10） | **wan3.0-video（实测）** |
|---|---|---|
| 机身比例 | 约 1.5:1（偏胖） | **1.93:1 修长 ✓** |
| 刀头 | 凹面放射编织网 ❌ | **平面金色网 ✓** |
| 机身 logo | 不清晰 | **"Haier" 清晰无乱码 ✓** |

⇒ **产品保真优先选 wan3.0-video**；参考图必须同向同比例竖立图。

## 4. 影棚质感 prompt 语汇（实测有效）
「影棚白色无缝背景 + 柔光箱主光 + 侧逆光勾边 + 浅景深 + 女主持产品展示」→ 实测出片：干净的棚拍感、真人真实（无塑胶感）、手指正常。

## 5. 第三方模型（可灵/Vidu/PixVerse）在百炼上的坑
- 同账号 `/api/v1/quotas` 会列出第三方视频模型，**空参数探测也会"受理"（返回 task_id）**，
  但**真正执行时报**：`InvalidParameter: The product is not activated, please confirm that you have activated products and try again after activation.`
- ⇒ 需要在**百炼控制台 → 模型广场**分别开通（免费），**API 层无法开通**。
- ⚠️ 教训：**"入口受理" ≠ "可用"**。判定模型可用性必须真跑一条（或至少读执行态），不能只看请求被接受。
