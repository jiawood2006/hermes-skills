#!/usr/bin/env python3
"""同题对比多家视频模型（百炼）：同参考图 + 同 prompt + 同规格 → 出片 → ffprobe 回验。

用法:
    python3 compare_video_models.py --out /tmp/cmp [--duration 5] [--prompt-file p.txt]
    # 默认跑 4 家; 用 --models kling,wan30 只跑指定几家

设计要点（都是实测踩出来的）:
  * 各家 input/parameters 字段**不同**，BODY 里按模型构造，别写一套通用模板。
  * 失败的提交**不计费**，所以字段不确定就多试变体、读报错逐层反推。
  * 未知参数会被**静默忽略**、不报错 → 每条件必须 ffprobe 回验宽高/时长。
  * "提交受理(task_id)" ≠ "可用": 第三方模型未开通会先返回 task_id 再 FAILED。
"""
import argparse, json, os, subprocess, sys, time

KEY = open(os.path.expanduser("~/.hermes/.dashscope_key")).read().strip()
EP = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
FFPROBE = os.path.expanduser("~/video-tools/bin/ffprobe")

REFS = ["https://yunvela.com/dh/hsq1_front.jpg",
        "https://yunvela.com/dh/hsq1_side.jpg",
        "https://yunvela.com/dh/hsq1_girl.jpg"]
PROMPT = ("电影感商业广告，摄影棚布光：大柔光箱主光+侧逆光勾边，浅景深背景虚化，低饱和暖调，肤色通透真实。"
          "【产品硬约束】图1、图2是同一把迷你电动剃须刀的官方照片：修长圆柱形机身（高约为直径的1.9倍），深灰哑光金属；"
          "顶部端面是平整的金色金属网面刀头，外圈一圈黑色环带；机身正面印 Haier 字母。"
          "严禁画成矮胖杯状/罐状，严禁改变比例、颜色与 logo。"
          "【画面】图3的女主角穿米白色针织衫，在浅灰摄影棚中把产品举到胸前展示，微笑开口说话，镜头缓慢推近。"
          "不要出现任何文字、字幕、水印。")


def media_obj():
    return [{"type": "image", "url": u} for u in REFS]


def media_image_url():
    return [{"type": "image_url", "url": u} for u in REFS]


# 每家 = (model_id, 输入构造, 参数构造)  —— 字段差异见 references/third-party-video-model-fields-and-prices.md
SPECS = {
    "wan30":    ("wan3.0-video",
                 lambda p: {"prompt": p, "images": REFS},
                 lambda d: {"duration": d, "ratio": "9:16", "resolution": "1080P", "watermark": False}),
    "kling":    ("kling/kling-v3-video-generation",
                 lambda p: {"prompt": p, "images": REFS},
                 # mode:std=720P / pro=1080P；只传 resolution 会被静默忽略
                 lambda d: {"mode": "pro", "duration": d, "aspect_ratio": "9:16", "watermark": False}),
    "vidu":     ("vidu/viduq3-ad_reference2video",
                 lambda p: {"prompt": p, "media": media_obj()},
                 lambda d: {"resolution": "1080P", "duration": d, "watermark": False}),
    "pixverse": ("pixverse/pixverse-v6-r2v-omni",
                 lambda p: {"prompt": p, "media": media_image_url()},
                 # aspect_ratio 必填，否则 Required field aspect_ratio are missing or empty
                 lambda d: {"resolution": "1080P", "duration": d, "aspect_ratio": "9:16", "watermark": False}),
}


def post(body):
    r = subprocess.run(["curl", "-s", "--max-time", "60", "-X", "POST", EP,
                        "-H", f"Authorization: Bearer {KEY}", "-H", "Content-Type: application/json",
                        "-H", "X-DashScope-Async: enable", "-d", json.dumps(body, ensure_ascii=False)],
                       capture_output=True, text=True).stdout
    try: return json.loads(r)
    except Exception: return {"_raw": r[:300]}


def status(tid):
    r = subprocess.run(["curl", "-s", "--max-time", "30", "-H", f"Authorization: Bearer {KEY}",
                        f"https://dashscope.aliyuncs.com/api/v1/tasks/{tid}"], capture_output=True, text=True).stdout
    try: return json.loads(r).get("output", {}) or {}
    except Exception: return {}


def probe(path):
    o = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip()
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/cmp")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--models", default=",".join(SPECS))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    tasks = {}
    for tag in [t.strip() for t in a.models.split(",") if t.strip()]:
        model, mk_in, mk_pa = SPECS[tag]
        body = {"model": model, "input": mk_in(PROMPT), "parameters": mk_pa(a.duration)}
        d = post(body); o = d.get("output") or {}
        if o.get("task_id"):
            print(f"✅ 提交 {tag:9s} {model:34s} → {o['task_id']}")
            tasks[tag] = o["task_id"]
        else:
            print(f"❌ 提交失败 {tag}: {d.get('code')} | {str(d.get('message'))[:160]}")
    json.dump(tasks, open(f"{a.out}/tasks_compare.json", "w"), indent=1)

    done = {}
    for tag, tid in tasks.items():
        for _ in range(90):
            o = status(tid); st = o.get("task_status")
            if st == "SUCCEEDED":
                url = o.get("video_url", ""); break
            if st == "FAILED":
                print(f"❌ {tag} FAILED {o.get('code')} {str(o.get('message'))[:160]}"); url = ""; break
            time.sleep(15)
        else:
            url = ""
        if url:
            out = f"{a.out}/{tag}.mp4"
            subprocess.run(["curl", "-s", "-o", out, "--max-time", "300", url])
            print(f"✅ {tag} → {out}  {probe(out)}   # 必看: 宽高/时长是否符合请求")
            done[tag] = out
    json.dump(done, open(f"{a.out}/done_compare.json", "w"))
    print("\n拿到:", json.dumps(done, ensure_ascii=False))
    print("下一步: 抽帧拼图 ffmpeg -vf fps=1.2,scale=300:-1,tile=3x2 后按四维评分"
          "（影棚感/真人感/产品保真/是否多镜头）")


if __name__ == "__main__":
    sys.exit(main())
