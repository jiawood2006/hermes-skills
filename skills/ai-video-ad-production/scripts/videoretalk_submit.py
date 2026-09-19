#!/usr/bin/env python3
"""提交 videoretalk 口型替换：视频 + 纯旁白音轨 → 重对口型的视频。

用法:
  python3 videoretalk_submit.py <video_url> <audio_url> [--fetch 输出路径]

要点（2026-09-16 实测）:
  * video_url / audio_url **都必须公网可访问**。本脚本只接受 http(s) URL，本地文件请先
    `scp xxx yunvela:/opt/yunvela-site/dh/` 再 `curl -o /dev/null -w '%{http_code}' <url>` 确认 200。
  * audio_url 传**纯旁白轨**（我方 edge-tts 合成），并用 `apad=whole_dur=<该段精确段长>` 补满，
    否则输出时长会被音频长度截短。
  * 输出 720P；价格 0.08 元/秒（1800 秒免费额度）。
  * **连续提交第 2 条起会 429 Throttling.RateQuota** → 脚本自动退避 45s 重试（不是配额用尽）。
  * 无正脸的段（纯手部/产品特写）**不需要**本步骤，直接铺旁白即可。
"""
import json
import os
import sys
import time
import urllib.request

KEY = open(os.path.expanduser("~/.hermes/.dashscope_key")).read().strip()
API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis"
TASK = "https://dashscope.aliyuncs.com/api/v1/tasks/"


def submit(video_url, audio_url, tries=5):
    body = {"model": "videoretalk",
            "input": {"video_url": video_url, "audio_url": audio_url},
            "parameters": {"video_extension": False}}
    for i in range(tries):
        req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + KEY,
                                              "Content-Type": "application/json",
                                              "X-DashScope-Async": "enable"}, method="POST")
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=90).read())
            return (d.get("output") or {}).get("task_id") or print(
                "提交失败:", json.dumps(d, ensure_ascii=False)[:300])
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code == 429:                 # 限流：等一会儿再提交
                print(f"429 限流，45s 后重试（{i + 1}/{tries}）")
                time.sleep(45)
                continue
            print("HTTP", e.code, msg)
            return None
    return None


def fetch(task_id, out, interval=10, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(interval)
        r = json.loads(urllib.request.urlopen(urllib.request.Request(
            TASK + task_id, headers={"Authorization": "Bearer " + KEY}), timeout=30).read())
        o = r.get("output") or {}
        st = o.get("task_status")
        if st == "SUCCEEDED":
            urllib.request.urlretrieve(o["video_url"], out)
            print("OK", out, os.path.getsize(out), "bytes")
            return out
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            print("FAIL", json.dumps(r, ensure_ascii=False)[:300])
            return None
    print("TIMEOUT")
    return None


if __name__ == "__main__":
    args = sys.argv[1:]
    fetch_to = args[args.index("--fetch") + 1] if "--fetch" in args else None
    positional = [a for a in args if not a.startswith("--") and a != fetch_to]
    if len(positional) < 2:
        print(__doc__)
        raise SystemExit(1)
    for p in positional[:2]:
        if not p.startswith("http"):
            print(f"⚠️ {p} 不是公网 URL —— 先 scp 到 /opt/yunvela-site/dh/ 并 curl 确认 200")
            raise SystemExit(2)
    tid = submit(positional[0], positional[1])
    print("videoretalk →", tid)
    if tid and fetch_to:
        fetch(tid, fetch_to)
