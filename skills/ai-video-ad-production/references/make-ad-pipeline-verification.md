# 整机（make_ad）状态与「改流水线后自证」方法（2026-09-18 实测）

> 配套阅读：**投放指标 / 完播率基准 / 素材批量测试打法** 见同目录
> `retention-and-ad-metrics-optimization.md`（那份是唯一的指标口径来源，本文不重复）。
> 用法与项目配置字段见 SKILL.md 的「🚀 怎么跑」章节。

## 1. 整机状态：缺口已补齐（勿再按「待补」理解）
- **入口 = `scripts/make_ad.py`**：一条命令出片，六步都可单跑 ——
  `plan`（免费出 prompt）/ `submit` / `fetch` / `verify` / `assemble`(30s+15s) / `deliver`。
- **产品档案已打通**：`ecommerce-material-studio/references/product_profiles.json` 新增 `haier_hsq1_shaver`
  （`physical / key_selling_points / assets / video_lock / video / image` 段）。
  生图读 `image`，视频读 `video` + `video_lock` → **改档案一处，图/视频同时生效**。
- **产品锁措辞抽成共用模板** `templates/product_lock_head.txt`（`{{字段}}` 由档案 `video_lock` 填）；
  可直接跑的完整样例 = `templates/ad_project.hsq1.json`（复刻已交付的 v23）。
- `ecommerce-material-studio`（素材工厂）= **仍只做图**（12 脚本，0 处视频代码），已在它 SKILL.md 加了指路。
- `video-composer-v4` 仍是旧路线（示例脚本是空壳），**别用它做 R2V 出片**。

## 2. 改流水线 / 加功能后必须自证（铁律：别只靠嘴说「没改坏」）
1. **复刻**：拿上一版交付件当输入 → `make_ad.py <项目.json> --steps assemble,deliver`
2. **比对 md5**：`md5(新) == md5(已交付)`，**30s / 15s 双双一致**才算没改坏
   （2026-09-18 实测一致：30s `86f3da96…`、15s `0b67686b…`；不一致 = 动了不该动的层）
3. **单段冒烟**：生成链路（submit→fetch→verify）用**一段**真跑即可确认（10 秒 ≈ 6 元），
   别等整片跑通才验，也别为了"完整"整片重跑烧钱
4. **老路径回归**：跑一次「没人走的分支」——**老 bug 就藏在那里**：
   - 2026-09-18 发现装配器音频链把 `asetpts` 写成 `setpts`（`setpts` 是**视频**滤镜）→
     ffmpeg 报 `Media type mismatch ... atrim(audio) 与 setpts(video)`；
     **该路径从上线起就是坏的**，因为所有成片都走旁白，从没人碰过段内音频
   - 同日发现 `xstack` 布局被**按字符**截断（`"...".join(items)[:n]` 应写成 `"|".join(items[:n])`）→
     段数少时 9 格拼图直接写不出文件（`Nothing was written into output file`）
   → 回归用例：**不带旁白的装配 + 带 trim + 不带 trim**，各跑一次

## 3. 工程约束（写新功能时别踩）
- **多产品并行必须各用各的 `workdir`**：`AD_TMP` / `VO_WORKDIR` 要跟随 workdir，
  否则 overlay PNG 落到同一个 `/tmp/r2v` 互相覆盖，15s 版会复用错图。
- **VO 输入必须追加在 overlay 输入之后**：overlay 的输入序号靠 `len(inputs)//2` 定位，
  中间插一个音频会让后面所有 overlay 索引错位。
- **用 VO 时不要生成段内音频链**：未消费的 filter 输出会被 ffmpeg 判为未连接而报错。
- **生成一律 720P**：同 prompt 跑 1080P 会把产品画坏（长径比 1.25 矮胖罐 + 金网消失）。
- **旁白落点 = 字幕 `start`**（`build_vo30.py` 按它排 TTS）→ 天然对齐，不要凭猜改时间轴。
