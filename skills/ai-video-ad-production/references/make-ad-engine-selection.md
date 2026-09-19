# make_ad 换引擎 / 多引擎字段 / 分段重做（2026-09-18 落地）

## 1) 换引擎 = 项目 json 加一行 `model`

```json
{ "runid": "wh", "model": "wan3.0-video", "resolution": "720P", "duration": 5, "ratio": "9:16" }
```

`make_ad.py` 的 `step_submit` 会**按模型自动切换 input 形态**（2026-09-18 补丁）：

| 引擎 | 参考图字段 | 备注 |
|---|---|---|
| `wan3.0-video`（产品镜主力） | `input.images = [url, ...]` | 自动带 `parameters.watermark = false`（默认可能烧水印） |
| `wan2.7-r2v`（纯人物戏） | `input.media = [{"type":"reference_image","url":...}]` | 不写 `model` 时的默认值 |

补丁位置（别重复踩）：`step_submit` 里先算 `model = proj.get("model", "wan2.7-r2v")`，
再 `if "3.0" in model:` 分支决定 `inp` 与是否加 `watermark`。

## 2) 一次提交只能有一个 `duration` → 按时长拆项目

`duration` 是**项目级**字段（`parameters.duration`），所以**5s 段和 10s 段不能放同一个项目**。
段时长混排时拆成两个配置，顺序跑（本轮：`project_w30_hooks.json` = 3×5s，`project_w30_body.json` = 2×10s），
每个配置照常 `--steps plan,submit,fetch`。拆开还能**分别核验、失败只重跑一半**。

## 3) 分段重做（只重跑有问题的段，不重抽全片）

核验后**逐段给放行/重做结论**，然后：

1. 新起 runid（如 `w2h` / `w2b`），只放要重做的段 → `plan,submit,fetch`（只花这几段的钱）
2. 旧成片先**归档**再覆盖：`_停用_<原因>版/`（如 `_停用_R2V产品镜版/`）—— **别让用户分不清哪版是新的**
3. 改 `variants/*.json` 与主片 json 的 **`assembly.order[].file` 引用**指向新段（纯本地，0 元）
4. 跑 `--steps assemble,deliver` 重建；交付文件名**带引擎/版本标识**（如 `hsq1_wan30版_30s.mp4`），
   不要沿用会误导的旧名（旧名写着 `R2V版` 却塞 wan3.0 的片）

## 4) 轮次成本怎么报

按「本轮花了多少 + 累计」报给用户，并说清**失败/重跑部分是否计费**：
实测本轮 = 第一轮 21 元（3 钩子 9 + 正片/车内 12）→ 核验后定点重做 4 段 18 元，
**累计 39 元**；装配/重建/交付全 0 元。用户接受"先花小钱验证、再定点重做"，不接受"闷头重抽整片"。

## 5) 顺手固定的两条工程习惯

- **省钱先行**：`--steps plan` 免费，先看拼装出的 prompt 字数与结构，再提交。
- **核验先于装配**：装配 0 元但会覆盖交付文件；**未通过核验不装配**（返工花的是生成费）。
