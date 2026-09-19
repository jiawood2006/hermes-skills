# 交付前核验手册：字幕同步 / 台词反查 / 混音 / 送达回读（2026-09-16 实拍轮次沉淀）

> 配套 `references/r2v-multi-reference-ad-pipeline.md`（生产路线）使用。
> 本文只讲**怎么验**、以及**哪些"发现问题"其实是假警报** —— 本轮为此白改过时间轴、白紧张过发送失败。

## 1. 字幕↔语音同步：只用精确抽帧，不要用抽样拼图

**假警报**：用 `ffmpeg -i out.mp4 -vf "fps=1/3.75,scale=360:-1,tile=4x2" -frames:v 1 grid.jpg`
看拼图判断"字幕早了 1 秒多" ✗ —— 抽样帧的时间标签与实际时间并不对应，据此改时间轴 = 白改。

**正解**：按精确时间点逐帧抽（`-ss` 必须放在 `-i` **前面**才是精确定位），再拼图逐格核对：
```bash
for t in 2.0 5.5 15.0 18.0 22.0 25.0; do
  ffmpeg -loglevel error -y -ss $t -i out.mp4 -frames:v 1 -vf scale=360:-1 f_$t.jpg
done
# 再用 xstack 拼成一张，逐格读字幕文字 ↔ 与 STT 时间轴比对
```
现成实现：`scripts/assemble_r2v_overlays.py --sync out.mp4 2.0,5.5,15.0,18.0,22.0,25.0`
（本轮 6 个时间点核验 6/6 对齐 ✓ 而抽样拼图给出的结论是错的）。

## 2. 字幕落点的时间轴从哪来

- `vad_filter=True`（默认）会把**相邻两句并成一个 span**：本轮 seg2 的两句台词被报成一个 `[10.0-19.7]`，
  拿不到断句位置 ✗ → 无法定字幕起止。
- 正解：`vad_filter=False, word_timestamps=True` 读**词级**时间，取该句首词的 start 作字幕起点
  （实测：seg2 第一句实际 4.36s 起说，整段前 4.3s 是纯动作无台词）。
- 现成实现：`scripts/stt_dialogue_check.py --words seg2.mp4`。

## 3. 台词反查：判据是语义，不是字面

- r2v 自带人声会**读错**：本轮 seg3 前 5 秒转写成乱码（「恩师温喜年 冲一冲 皆胜利冲」），后 5 秒才说对
  → **该段重跑**（把读错的句子挪到最前 + prompt 加「台词只说一遍，不要重复」），重跑一次即通过。
- 但**同音字属正常**（刮→挂、八千五百→8500、几下就要干净→几下就干净），
  **只有整句语义乱掉才算失败**；别为同音字反复重跑烧钱。

## 4. 混音/装配的硬坑

- `apad` 不带参数 = **无限静音流** → ffmpeg 挂死数分钟、写出十几 MB 无 moov 的文件；`-t`/`-shortest` 不必然终止。
  正解：`apad=pad_dur=0.4` + `-t <总长>` +（静音视频串）`-map 0:v -c:v copy` 一步出片。
- 多段拼接时每段都要 `scale=1080:1920,setsar=1` 再 `concat`；裁短版（15s）用
  `trim=0:<秒>,setpts=PTS-STARTPTS`（视频）与 `atrim=0:<秒>,asetpts=PTS-STARTPTS`（音频）配对，否则音画错位。
- 花字层用 PIL 画成 1080×1920 透明 PNG 再 `overlay=0:0:enable='between(t,a,b)'` 定时显示，
  比 `drawtext` 稳（中文字体、多行、圆角底都好控）。**命名要统一**（本轮 `ov_sub1.png` vs `ov_sub_1.png` 不一致导致一次空跑）。

## 5. 送飞书：回读才算送达，且别误读返回码

- 脚本输出形如 `文字: 0 success` / `视频: 0 success` —— `0` 是**返回码 0 = 成功**，
  `success` 是飞书 `msg` 字段，**不是"0 条成功"**（本轮差点误判成发送失败 ✗）。
- 真正判定靠**回读消息列表**：`GET im/v1/messages?container_id_type=chat&container_id=<chat>&sort_type=ByCreateTimeDesc`，
  视频/文件类消息在列表里显示为 `nonsupport` 属**正常**，说明已送达 ✓。
- 微信端发大视频会被 iLink 限流静默失败 → 媒体一律走飞书。
