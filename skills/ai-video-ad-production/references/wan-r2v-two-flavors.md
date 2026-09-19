# 万相「参考生视频」两个版本入参完全不同（2026-09-15 实测踩坑）

⚠️ **最容易踩的坑**：把 2.7 的 `media` 格式发给 2.6-r2v-flash，会立刻返回
`InvalidParameter: please provide reference_video_urls or reference_urls.`
（在参数校验阶段失败，**不扣费**，但要白等一轮。）

| | **wan2.6-r2v-flash**（便宜/优先试） | **wan2.7-r2v**（贵/音色可控） |
|---|---|---|
| 参考素材入参 | `input.reference_urls` = **字符串数组**（图0-5、视频0-3，合计≤5） | `input.media` = **对象数组**，元素 `{type, url}`，type=`reference_image`/`reference_video`/`first_frame` |
| prompt 里怎么指代 | **`character1`、`character2`**（第1个URL=character1） | **`图1`、`图2`、`视频1`** |
| 分辨率参数 | `parameters.size` = **具体数值** `"1080*1920"`（9:16）／`"1920*1080"`／`"720*1280"`；**不能写 `1080P` 或 `9:16`** | `parameters.resolution`=`1080P` + `parameters.ratio`=`9:16` |
| 时长 | `duration` 2-10 整数 | `duration` 2-15（含参考视频时2-10） |
| 有声 | `parameters.audio` = true（**仅 flash 支持此参数**，默认 true，模型自己配音） | **默认有声**，无需 audio 参数 |
| 音色参考 | ❌ 不支持 `reference_voice`（音色由模型自选） | ✅ `media` 元素内加 `reference_voice`（mp3，1-10s）锁音色 |
| 镜头数 | `shot_type` = `multi`（多镜头）/ `single`（默认单镜头） | 同左 |
| prompt 长度上限 | 1500 字符 | 5000 字符 |

## 结论：选型策略
1. **先用 `wan2.6-r2v-flash`** —— 便宜（有免费额度），`audio:true` 会按 prompt 里引号内的台词自动配音，口型同步。
   代价：**音色由模型定，不能克隆**（要女主固定音色就得用 2.7）。
2. 音色/情绪有硬要求时才升级 **`wan2.7-r2v`**（1080P 约 1元/秒，贵 10 倍以上）。
3. 多个参考图指同一主体（如产品正/侧两个角度）时，**必须在 prompt 里写明"character1 和 character2 是同一个主体"**，否则模型可能当成两个角色生成两份。

## 可复用调用骨架（flash）
```python
body = {
  "model": "wan2.6-r2v-flash",
  "input": {"prompt": PROMPT, "reference_urls": [REF1, REF2, REF3]},   # 顺序 = character1/2/3
  "parameters": {"size": "1080*1920", "duration": 10, "audio": True,
                 "shot_type": "multi", "watermark": False},
}
# POST https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
# Header: Authorization: Bearer $KEY / Content-Type: application/json / X-DashScope-Async: enable
```
