#!/usr/bin/env python3
"""逐镜头审计：场景切分 → 每镜头取中段帧 → 拼成带时间码的网格图。

用途：用户说"某个镜头的产品失真太明显"时，先定位到底是哪几个镜头，再只重做坏的，
不要整片重来（用户原话：你的失真也不是全部失真，部分镜头的部分产品细节失真太明显）。

用法：
  python3 audit_shots.py 视频.mp4 [视频2.mp4 ...] [--out /tmp/audit] [--thresh 0.25] [--cols 4] [--per-page 12]

产出：
  <out>/audit_<tag>_p0.jpg …   每页最多 <per-page> 格，每格左上角烧「#序号 起-止 s」
  <out>/audit.json            每支片子的镜头边界清单（后续只重做 ❌ 镜头时直接引用）

依赖：ffmpeg/ffprobe（PATH 上，或用 FFMPEG=/path/to/ffmpeg FFPROBE=... 指定）、Pillow
"""
import argparse, json, os, re, shutil, subprocess, sys

from PIL import Image, ImageDraw, ImageFont

FFMPEG = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE") or shutil.which("ffprobe") or "ffprobe"
FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font(size=26):
    for p in FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def dur(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def scene_cuts(path, thresh=0.25):
    r = subprocess.run([FFMPEG, "-i", path, "-filter:v", f"select='gt(scene,{thresh})',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True)
    return sorted({float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)})


def shot_frames(path, tag, out, thresh=0.25, min_len=0.25):
    d = dur(path)
    cuts = [0.0] + [c for c in scene_cuts(path, thresh) if min_len < c < d - 0.2] + [d]
    shots = []
    for i in range(len(cuts) - 1):
        a, b = cuts[i], cuts[i + 1]
        if b - a < min_len:
            continue
        mid = (a + b) / 2
        frame = f"{out}/{tag}_s{len(shots):02d}_{mid:.1f}.jpg"
        subprocess.run([FFMPEG, "-y", "-v", "error", "-ss", str(mid), "-i", path,
                        "-frames:v", "1", "-vf", "scale=420:-1", frame], capture_output=True)
        shots.append({"idx": len(shots), "start": round(a, 1), "end": round(b, 1),
                      "mid": round(mid, 1), "frame": frame})
    return shots, d


def grid(shots, tag, out, cols=4):
    ims = [Image.open(s["frame"]) for s in shots]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    G = Image.new("RGB", (cols * w, rows * h), (20, 20, 20))
    dr, f = ImageDraw.Draw(G), font()
    for i, im in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * h
        G.paste(im, (x, y))
        dr.rectangle([x, y, x + 250, y + 34], fill=(0, 0, 0))
        s = shots[i]
        dr.text((x + 6, y + 3), f"#{s['idx']} {s['start']}-{s['end']}s", fill=(255, 220, 0), font=f)
    p = f"{out}/audit_{tag}.jpg"
    G.save(p, quality=88)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="/tmp/audit")
    ap.add_argument("--thresh", type=float, default=0.25)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--per-page", type=int, default=12)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    report = {}
    for v in a.videos:
        if not os.path.exists(v):
            print("MISS", v)
            continue
        tag = os.path.splitext(os.path.basename(v))[0][:32]
        shots, d = shot_frames(v, tag, a.out, a.thresh)
        if not shots:
            print(f"{tag}: 未切出镜头")
            continue
        pages = []
        for i in range(0, len(shots), a.per_page):
            pages.append(grid(shots[i:i + a.per_page], f"{tag}_p{i // a.per_page}", a.out, a.cols))
        report[tag] = {"path": v, "duration": round(d, 2), "shots": shots, "pages": pages}
        print(f"{tag}: {d:.2f}s, {len(shots)} 镜头 → {len(pages)} 页")
        for s in shots:
            print(f"   #{s['idx']} {s['start']}-{s['end']}s")
        for p in pages:
            print("   PAGE", p)
    with open(f"{a.out}/audit.json", "w") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"\n清单: {a.out}/audit.json")
    print("下一步：把 PAGE 图交给视觉逐格问「产品可见吗 / 失真吗 / 失真具体是什么」，只重做 ❌ 的镜头。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
