#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""男主候选生成器（写实＋干净＋带笑）—— 2026-09-17 实测版

用途：用户要"换男主 / 挑一个演员 / 人物太假"时，一次性出 3~4 个候选，拼图发飞书让他挑。
为什么要有这个脚本：候选图的**面部状态会被成片原样复刻**（参考图带胡子 → 全片长胡子；
视频 prompt 里写"不要胡须/不要皱眉"**压不住**）。所以下面 COMMON 的六条是硬约束，别删。

用法:
  python3 gen_character_candidates.py --out /tmp/chars --n 4
  python3 gen_character_candidates.py --tag P_年轻商务28 --desc "28岁中国男性，戴黑色细框眼镜，白衬衫配深色西裤，站在办公室窗边，午后窗光从侧前方照进来"
  python3 gen_character_candidates.py --sheet /tmp/chars       # 已有图 → 拼 4 格带标签图

依赖：~/.hermes/.dashscope_key（阿里云百炼 key）；模型 wan2.6-t2i。
实测：连续请求会被限流（Read timed out / NoAudioReceived 同类）→ 必须重试（本脚本内置 4 次 + sleep）。
"""
import argparse, json, os, sys, time, urllib.request

KEY = open(os.path.expanduser("~/.hermes/.dashscope_key")).read().strip()
API = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

# ⚠️ 六条硬约束（2026-09-17 实证）：缺任何一条都会让成片出现胡子/皱眉/发绿色块
COMMON = (
    "真实摄影照片，半身人像，不是影棚商业模特照。"
    "上唇必须完全光洁：上唇上方没有任何毛发、没有小胡子、没有胡子阴影；下巴和下颌也剃得干干净净。"
    "下巴、上唇、下颌的肤色必须和脸部完全一致：是干净的肤色，绝不能出现发绿、发青、发灰的胡须阴影或色块。"
    "看着镜头自然地笑：嘴角上扬、露出一点牙齿、眼睛因为笑微微眯起；"
    "眉毛放松舒展、不皱眉、不浓眉，眼神温和亲切。"
    "看起来年轻：面部紧致、不超过30岁的样子，发量正常不秃。"
    "半身构图：能看到肩膀和胸部以上，头顶留一点空间，不要只拍脸部特写。"
    "皮肤是真实皮肤：可见毛孔、细纹、肤色不完全均匀；不要磨皮、不要塑料感、不要网红脸。"
    "光线是室内自然光或真实实用灯（窗光/台灯/吊灯），有明确方向、有明暗过渡与真实阴影，不要平光、不要打光板感。"
    "背景是真实生活/办公空间（有生活道具、轻微杂乱），有景深虚化。"
    "画面中不要出现任何文字、水印、logo。"
)

DEFAULT = {
    "P_年轻商务28": "28岁中国男性，戴黑色细框眼镜，白衬衫配深色西裤，站在办公室窗边，午后窗光从侧面照进来，像工作间隙随手拍到。",
    "U_窗边28": "28岁中国男性，戴黑色细框眼镜，白衬衫配深色西裤，站在办公室落地窗边，午后窗光从侧前方照进来，像工作间隙随手拍到。",
    "V_车内30": "30岁中国男性，戴黑色半框眼镜，浅蓝色衬衫袖子挽到小臂，坐在汽车驾驶座（中控与方向盘在背景里），白天自然光从车窗照进来。",
    "W_咖啡桌29": "29岁中国男性，戴黑框眼镜，白衬衫外面套藏青针织开衫（商务休闲），坐在咖啡馆桌边，暖色吊灯从上方偏侧照下，桌上有咖啡杯。",
}


def gen(tag, desc, outdir, size="720*1280"):
    os.makedirs(outdir, exist_ok=True)
    payload = {"model": "wan2.6-t2i",
               "input": {"messages": [{"role": "user", "content": [{"text": COMMON + desc}]}]},
               "parameters": {"prompt_extend": True, "watermark": False, "n": 1, "size": size}}
    for attempt in range(4):
        try:
            req = urllib.request.Request(API, data=json.dumps(payload).encode(), headers=H)
            d = json.load(urllib.request.urlopen(req, timeout=180))
            url = d["output"]["choices"][0]["message"]["content"][0]["image"]
            p = os.path.join(outdir, f"{tag}.png")
            urllib.request.urlretrieve(url, p)
            print("OK", tag, os.path.getsize(p))
            return p
        except Exception as e:
            print("ERR", tag, str(e)[:160], flush=True)
            time.sleep(8)
    return None


def sheet(outdir, out="grid.jpg", w=520):
    """拼带标签候选图，发给用户挑（回一个字母）"""
    from PIL import Image, ImageDraw
    ps = sorted(f for f in os.listdir(outdir) if f.endswith(".png"))
    ims = []
    for f in ps:
        im = Image.open(os.path.join(outdir, f)).convert("RGB")
        W, Hh = im.size
        im = im.crop((int(0.06 * W), int(0.01 * Hh), int(0.94 * W), int(0.60 * Hh)))  # 半身裁切
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im); d.rectangle([0, 0, 215, 32], fill=(180, 0, 0))
        d.text((6, 9), f.replace(".png", ""), fill=(255, 255, 0))
        ims.append(im)
    cw = w; rh = max(i.height for i in ims)
    c = Image.new("RGB", (cw * len(ims) + 10 * (len(ims) - 1), rh), (15, 15, 15))
    x = 0
    for i in ims:
        c.paste(i, (x, 0)); x += i.width + 10
    p = os.path.join(outdir, out); c.save(p); print("SHEET", p, c.size)
    return p


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/r2v/chars")
    ap.add_argument("--tag"); ap.add_argument("--desc")
    ap.add_argument("--n", type=int, default=0, help="只出前 n 个默认候选")
    ap.add_argument("--sheet", help="只拼图：给一个已存在的候选目录")
    a = ap.parse_args()
    if a.sheet:
        sheet(a.sheet); sys.exit(0)
    if a.tag and a.desc:
        gen(a.tag, a.desc, a.out)
    else:
        items = list(DEFAULT.items())[: a.n or len(DEFAULT)]
        for tag, desc in items:
            gen(tag, desc, a.out); time.sleep(3)
        sheet(a.out)
    print("提醒：出图后必须 2 倍放大看【上唇/眉毛/表情】三处，不合格就重出（1 分钟 1 张，别省）")
