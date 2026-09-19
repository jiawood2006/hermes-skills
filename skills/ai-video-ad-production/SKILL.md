---
name: ai-video-ad-production
description: AI 电商视频广告生产线：一条命令出带货短视频（产品锁 / 多引擎选型 / 官方真像素产品镜 / 自动装配）。One-command product ad video pipeline: product lock, multi-engine selection, official-pixel product inserts, auto overlay assembly.
category: ecommerce
---

# AI 生成带货短视频（真人剧情 / 口播）

## When to Use
用户要"短视频 / 带货片 / 口播片 / 样片标准"，或抱怨之前的成片"没有真实感、像图片拼接"时。
**先做路径判断（见下），不要把素材拼接当成交付。**

## 🚀 怎么跑（2026-09-18 起：一条命令出片）

**整机 = `scripts/make_ad.py`** —— 把原先散在 /tmp 的 6 个手工脚本串成一条命令，
后面所有零件脚本按需被它调用。

```bash
S=~/.hermes/skills/ecommerce/ai-video-ad-production

# ① 先看 prompt（免费、不提交；确认产品锁+分镜再花钱）
python3 $S/scripts/make_ad.py $S/templates/ad_project.hsq1.json --steps plan

# ② 全自动一条龙：提交→轮询→下载→抽帧核验→装配 30s/15s→交付桌面
python3 $S/scripts/make_ad.py $S/templates/ad_project.hsq1.json --steps all

# ③ 分段已下载，只重跑后期（改字幕/换旁白/重切 15s —— 不花钱，最常用）
python3 $S/scripts/make_ad.py <项目.json> --steps assemble,deliver

# ④ 只处理某几段 / 临时换 runid、分辨率
python3 $S/scripts/make_ad.py <项目.json> --steps fetch,verify --seg 3 --runid v24 --res 720P
```
每步都查退出码 + 产物存在/大小，不达标直接报 FAIL 原文并列出，**不静默继续**。

**项目配置**（`templates/ad_project.hsq1.json` 是可直接跑的真实样例，改它就能出新片）：

| 字段 | 说明 |
|---|---|
| `product` | 指向产品档案 `product_profiles.json` 的键 —— **生图/视频共用同一份档案** |
| `refs` | 参考图顺序 = 图1..图N，**必须与产品锁模板里的图号描述一一对应**；本地图自动 scp 到公网 |
| `segments` | 每段分镜正文（**只写"拍什么"**；产品锁由 make_ad 自动拼在前面） |
| `assembly.vo` | 旁白（edge-tts）；落点 = 字幕 `start`，天生对齐 |
| `assembly.subs/chips/spec/compliance` | 字幕 / 花字 / 参数条 / AI 生成内容标注 |
| `assembly.cut15` | 15s 版：取哪几段、旁白切哪几刀、每个 overlay 在 15s 轴上的新时间窗 |
| `deliver` | 交付目录 + 文件名（默认 `~/Desktop/电商素材/<产品>/视频/`） |

**产品锁**（所有产品共用一份，别新建）：`templates/product_lock_head.txt` + 档案里的 `video_lock` 字段。
"占比 ≤ 画面高 1/6、机头直径当尺子算 1.9 倍、底部端面是平的圆面、线沿轴线插、全程不直视镜头…"
这些血泪措辞都在那儿 —— **分镜里不要重复写，也不要手写新模板**。

**实测证据（2026-09-18）**：用 `ad_project.hsq1.json` 跑 `--steps assemble,deliver` 复刻出来的成片，
与 2026-09-17 当晚手工交付版 **md5 完全一致**（30s `86f3da96…`、15s `0b67686b…`）；
`--steps plan,submit,fetch,verify` 单段冒烟测真实跑通（提交→轮询→下载→抽帧核验）。

### 零件清单（`scripts/` 25 个，按用途分组）

| 环节 | 脚本 | 用途 |
|---|---|---|
| **整机** | `make_ad.py` | 一条命令出片（plan / submit / fetch / verify / assemble / deliver） |
| 生成 | `videoretalk_submit.py` / `probe_model_availability.py` / `compare_video_models.py` | 口型替换提交 / 模型可用性探针（提交成功≠可用）/ 同题多家模型横评 |
| 核验·产品 | `product_fidelity_zoom.py` / `scale_consistency_check.py` / `scale_panel_check.py` / `measure_product_truth.py` / `check_reference_image.py` / `locate_reported_frame.py` / `audit_shots.py` | 产品 2 倍放大 / 跨镜尺寸一致性 / 真值+成片读格面板 / 真机长径比真值 / 参考图体检 / 用户截图反查时间码 / 逐镜审计 |
| 核验·声音 | `stt_dialogue_check.py` / `voice_consistency_check.py` / `voice_timbre_similarity.py` / `tts_fit.py` | 台词 STT 反查（字幕落点来源）/ 换嗓检测 / 锁音色验证 / 配音调速对齐镜头 |
| 核验·画面 | `verify_motion.py` | 运动量检测 —— 判断成片是不是"静图贴图" |
| 后期 | `assemble_r2v_overlays.py` / `build_vo30.py` / `overlay_anim.py` / `replace_segment_audio.py` / `gen_ass.py` | 装配（支持 `vo` 整条旁白）/ 旁白轨 / 花字动画 / 替换段内音频 / ASS 花字 |
| 零失真路线 | `compose_official_material_ad.py` / `cutout_product.py` / `make_comp_cards.py` | 官方物料动效成片（产品 100% 等于真机）/ 官方图抠透明 PNG / 产品像素不经 AI 的合成卡 |
| 人物 | `gen_character_candidates.py` | 男主候选生成（一次出 3-4 个拼图给用户挑） |

## 路径判断（最重要 · 血泪教训，2026-09-15；2026-09-18 更新）

| 路径 | 效果 | 何时用 |
|---|---|---|
| **① R2V 多参考图（`wan2.7-r2v`，最多 5 张参考图）** ✅ **当前主线** | 产品形制/颜色/接口锁得住 + 真人生活情景，**已交付 v23**；参考图=金网微距/正面/真手/底部端面/主角 | 有官方产品图、要求"产品必须像真机" |
| ② 文生视频（`wan2.6-t2v`，台词走 `input.audio_url`） | 真人 + 场景 + 中文口型，但**产品每段会变一点** | 无官方素材、或只做人物剧情 |
| ③ 素材拼接（clipforge / MoneyPrinterTurbo：图或片段 + 运镜 + TTS + 字幕） | **用户判定=「图片拼接、缺乏真实感、和样片差距很大」** | 无剧情的信息流合集、或先出草稿占位 |
| ④ 数字人对口型（wan2.2-s2v / EMO / videoretalk：图或视频 + 音频 → 说话视频） | 单人口播，环境真实感弱 | 没条件生成、只要口播讲解 |

**铁律**：
- 用户给的"样片标准"如果是真人剧情对话，**不要断言"只能实拍"**——用户明确纠正过：他的样片本身就是 AI 生成的。
- 素材拼接（②）永远追不上①的真实感，**别把它当成 AI 视频的交付**。
- 直接走①，用用户自己的台词和配音。

## ① 主线配方：wan2.6-t2v
完整参数、JSON、计费、配音托管、验片命令见 `references/scene-drama-and-candid-style.md`。

要点速览：
- `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis`
  `model=wan2.6-t2v`，头 `X-DashScope-Async: enable`
- `parameters`: `size:"720*1280"`(9:16) 或 `"1080*1920"`、`duration:5|10`、`shot_type:"multi"`、`prompt_extend:true`
- `input.audio_url`：传**我们自己写的台词配音**（3~30s mp3/wav 公网 URL）→ 模型按音频做口型；
  不传则模型自动配音效并**自己编台词**（不可控，卖点会跑偏）
- 价格：**720P 0.6 元/秒、1080P 1 元/秒**；账号带 **50 秒免费额度** → 首条 30 秒片可用额度 0 元跑
- 台词音色：edge-tts `zh-CN-XiaoyiNeural`（年轻女）/ `zh-CN-XiaoxiaoNeural`（阿姨）/ `zh-CN-YunxiNeural`（男）
- 提示词里用 `第1个镜头[0-4秒]…第2个镜头[4-10秒]…` 描述多镜头；末尾加"画面中不要出现任何文字、字幕、水印"

## 标准生产流程
1. **剧本**：3 段 × 10 秒（或 6 段 × 5 秒）：剧情钩子 → 产品出场 + 真实卖点 → 收尾 + CTA
2. **配音**：edge-tts 生成每段台词 mp3 → `scp yunvela:/tmp/` → `sudo mv` 到 `/opt/yunvela-site/dh/` →
   `curl -o /dev/null -w '%{http_code}' https://yunvela.com/dh/segN.mp3` 必须 200
3. **生成**：逐段提交（可并行），轮询 `GET /api/v1/tasks/<id>`，`curl -sL --retry 3 --retry-all-errors` 下载
4. **后期**：拼接 + 花字（白字黑描边 + 黄色关键词框）+ emoji 贴纸 + BGM → 9:16 成片
5. **验片（不许跳过）**：`ffprobe` 时长/分辨率/有无音轨 + `volumedetect` 确认有声 + 抽帧拼图肉眼 +
   **STT 反查台词**（`~/.hermes/scripts/voice_stt_local.py`）确认说的就是我们的文案
6. **交付**：微信发大视频被 iLink 限流 → `~/.hermes/scripts/feishu_send_media.py <视频> "说明"`

## 用户偏好（本项目内已确认）
- 🔴 **产品特写别交给 AI——用官方真机图做动效**（2026-09-15 实测结论）：
  AI 生成的人物剧情镜头里，产品每段都会"变一点"（本项目实测：同 prompt 下一段是等直径圆柱、另一段变成锥形杆+网头，
  还会出现重复 logo）。**正确做法**：人物场景交给 AI，**产品特写用官方产品图做 Ken Burns 缓慢推近**
  （`scale=1080:-1,pad=1080:1920:(w-h)/2:(w-h)/2:white,zoompan=z='min(zoom+0.0007,1.10)':d=<帧数>`），
  并把该段**原配音接到官方图动效上**（不断句）。这样产品 100% 与真机一致，也符合"产品必须真实融入"的甲方红线。
- 🔴 **参考图两张必须"同向同形态"**：给 r2v 的 2 张产品参考图都必须是**竖立视角**（本项目实测：把一张"底面断面圆视图"
  当参考图2后，模型把修长和圆胖平均，生成出矮胖杯状产品）。**禁止**混入俯视/仰视/断面图当参考。
  参考图做法：裁到主体外接框 → 贴到白底方形画布、主体占画面高 ~60%。
- ⚠️ **AI 会自己烧字幕**：wan2.6-r2v-flash 即使 prompt 写"不要文字"也常自带底部字幕。
  所以**我方花字放顶部**（Alignment=8 + 大 MarginV），别在底部再叠一层 → 否则双字幕重叠。
- **形制按真实尺寸算，不许目测**（2026-09-15 实测教训）：prompt 里的"高:直径"必须由官方尺寸算出
  （HSQ1 = 74×39mm → **高:宽 1.93:1 修长圆柱**；我曾目测写成"矮胖杯状 1.2:1"，生成结果客户判"还是不准确"）。
  写法示例：`机身是修长圆柱形，高约74毫米、直径约39毫米（高度约为直径的1.9倍），黑色哑光缎面…`
- **话术口径铁律**（2026-09-15 用户纠偏）：台词/口播/花字**只许引官方宣传物料原文**（拉页图、主图上的字）。
  ❌ 属性表"卖点"字段 ≠ 话术（内部描述）；❌ 参考样片/竞品片里听来的说法不得当话术（HSQ1 实测：禁用"鸡蛋大小"）；
  🟡 尺寸类参照词（如"拇指高度"）**只能用于画面比例/对比物，禁入话术**。
  → 写台词前先按 `product-spec-extraction` 取话术口径，别凭印象写卖点。
- **效果优先**（用户 2026-09-15 定）：视频制作以效果为准，不为省钱牺牲观感
- 有产出必须主动汇报；长流程分段报进度，别等追问
- 设计阶段写全真实卖点，不因"没证据"删卖点（证明属投放阶段）；极限词/功效只提示不拦截
- 成本敏感：免费额度/低价先跑通再放量；花钱前说明单价

## 相关技能
- `clipforge-video-pipeline`：素材拼接方案（clipforge / MoneyPrinterTurbo）的完整配方 = 路径②，
  含环境安装坑、逐镜头挂图、本地素材模式，以及 0 成本"真机动态片段库"

## 📚 知识库索引（8 篇总纲）

| 什么时候读 | 文档 |
|:---|:---|
| 产品长得不像 / 变形掉色 / 尺寸比例 / 刀网 | `references/product-fidelity.md` |
| 选引擎 / 模型字段 / 价格 | `references/engines-and-models.md` |
| 分辨率 / 计费 / 欠费排查 / 预检 | `references/resolution-cost-and-arrearage.md` |
| 整机流水线 / 装配 / 交付核验 | `references/pipeline-assembly-and-qc.md` |
| 完播率 / 钩子变体 / 投放指标 | `references/hooks-and-ad-metrics.md` |
| 配音 / 字幕 / 音色 | `references/voice-and-subtitles.md` |
| 肖像权 / 合规红线 / 参考图规范 | `references/compliance-portrait-and-references.md` |
| 场景剧情片 / 真实感拍法 / 分镜措辞 | `references/scene-drama-and-candid-style.md` |

