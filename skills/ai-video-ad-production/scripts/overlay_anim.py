#!/usr/bin/env python3
"""花字动画层：在基础视频帧上叠加 PIL 动画文字（弹入 / 淡入 / 错峰 / 尺寸徽标）。

为什么不用 drawtext：drawtext 只能做位移与透明度，做不出缩放弹入、渐变遮罩条、圆形徽标。
本脚本抽帧 → PIL 逐帧绘制 → 重新编码，动效与排版完全可控。

用法: python3 overlay_anim.py <基础视频> <输出视频> <场景: C|D>
  C = 尺寸徽标层（圈内数字 + 圈下标签，逐条浮现 + 底部一行结论）
  D = 价格花字层（顶部标题 + 底部遮罩条 + 卖点错峰淡入 + ¥169 弹入）

⚠️ 实测踩过的坑（改脚本时别再犯）
1. **静图 + 推近 = 用户判「贴图」**（2026-09-16 原话「最新的又成贴图了」）——
   本脚本叠的是**文字动效**，只能给真运动镜头加信息层，**不能拿它顶镜头运动**。
   交付前跑 `scripts/verify_motion.py` 确认冻结区间为 0。
2. **圈线穿字**：把「鸡蛋大小」四个字塞进圆环会被圈线穿过 → 必须"圈内放短数字（7cm/70g/1h）+ 圈下放标签"。
3. **字压产品不可读**：满画幅产品帧没有留白，写字前先铺 `scrim()` 半透明黑渐变条。
4. **字体**：`ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size, index=1)`
   —— index=1 取粗体；不传 index 可能拿到细体；PingFang 是 .ttc 集合，缺 index 也可能直接抛异常。
5. PIL 画中文必须给 `fill=(r,g,b,a)` 四元组（RGBA 图上三元组会丢失透明度）。
6. 逐帧处理 100+ 帧需要几十秒，别放在前台超时命令里跑——落成脚本后台跑或给足 timeout。
"""
import os, subprocess, sys, glob, shutil
from PIL import Image, ImageDraw, ImageFont

FF = os.environ.get("FFMPEG") or os.path.expanduser("~/video-tools/bin/ffmpeg")
PING = "/System/Library/Fonts/PingFang.ttc"
GOLD = (255, 215, 94)


def F(size, index=1):
    try:
        return ImageFont.truetype(PING, size, index=index)
    except Exception:
        return ImageFont.truetype(PING, size)


def ease_out(t):
    return 1 - (1 - t) ** 3


def draw_center(dr, text, font, cx, cy, fill, alpha=255, border=True):
    """居中绘制（可选黑描边，保证压在任何背景上都可读）"""
    fill = fill + (alpha,)
    bb = dr.textbbox((0, 0), text, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    x, y = cx - w / 2, cy - h / 2 - bb[1]
    if border:
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                if dx or dy:
                    dr.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, int(alpha * 0.55)))
    dr.text((x, y), text, font=font, fill=fill)


def badge(dr, cx, cy, r, big, small, alpha):
    """官方同款：圈内大数字 + 圈下小标签（避免圈线穿字）"""
    if alpha <= 0:
        return
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, alpha), width=3)
    draw_center(dr, big, F(int(r * 0.80)), cx, cy, (255, 255, 255), alpha, border=False)
    draw_center(dr, small, F(34), cx, cy + r + 34, (255, 255, 255), int(alpha * 0.92))


def scrim(img, y0, y1, max_alpha, invert=False):
    """渐变遮罩条：让文字压在画面上依然清晰（满画幅产品帧必备）"""
    w = img.size[0]
    ov = Image.new("RGBA", (w, y1 - y0), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    n = y1 - y0
    for i in range(n):
        t = i / max(1, n - 1)
        d.line([(0, i), (w, i)], fill=(0, 0, 0, int(max_alpha * (t if invert else 1 - t))))
    img.alpha_composite(ov, (0, y0))


def render(kind, fps=25):
    def scene_C(img, i):
        """尺寸徽标：7cm/70g/1h 逐条浮现 + 底部一行结论"""
        t = i / fps
        dr = ImageDraw.Draw(img)
        for k, (t0, big, small) in enumerate([(1.00, "7cm", "长度"), (1.55, "70g", "重量"),
                                              (2.10, "1h", "充满电")]):
            a = max(0, min(1, (t - t0) / 0.35))
            if a > 0:
                badge(dr, 862, 520 + k * 330, 96, big, small, int(255 * a))
        a2 = max(0, min(1, (t - 2.60) / 0.4))
        if a2 > 0:
            draw_center(dr, "鸡蛋大小 · 可放入口袋", F(40), 540, 1560, (255, 255, 255), int(240 * a2))
        return img

    def scene_D(img, i):
        """价格花字：顶部标题 + 底部遮罩条 + 卖点错峰 + ¥169 弹入"""
        t = i / fps
        scrim(img, 0, 150, 150)
        scrim(img, 1180, 1920, 205, invert=True)
        dr = ImageDraw.Draw(img)
        for k, s in enumerate(["全新mini机身 · 70g", "镀钛刀网 · 8500转/分", "充电1小时 · 续航90天"]):
            a = max(0, min(1, (t - (0.10 + k * 0.16)) / 0.35))
            if a > 0:
                draw_center(dr, s, F(40), 540, 1330 + k * 62, (255, 255, 255), int(238 * a))
        t0 = 0.55
        if t >= t0:
            p = min(1, (t - t0) / 0.45)
            s = 0.55 + 0.5 * ease_out(p) - (0.05 if p > 0.75 else 0)   # 带过冲的弹入
            draw_center(dr, "¥169", ImageFont.truetype(PING, int(150 * s), index=1),
                        420, 1700, GOLD, 255)
            a2 = max(0, min(1, (t - t0 - 0.25) / 0.3))
            if a2 > 0:
                draw_center(dr, "到手价", F(38), 660, 1720, (255, 255, 255), int(230 * a2))
        a3 = max(0, min(1, (t - 1.0) / 0.4))
        if a3 > 0:
            draw_center(dr, "海尔迷你便携剃须刀", F(50), 540, 78, (255, 255, 255), int(245 * a3))
        return img

    return {"C": scene_C, "D": scene_D}[kind]


def main():
    if len(sys.argv) < 4:
        raise SystemExit("用法: python3 overlay_anim.py <基础视频> <输出视频> <C|D>")
    src, dst, kind = sys.argv[1], sys.argv[2], sys.argv[3]
    work = "/tmp/_ov_" + kind
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work + "/in", exist_ok=True)
    os.makedirs(work + "/out", exist_ok=True)
    subprocess.run([FF, "-loglevel", "error", "-y", "-i", src, "-vf", "fps=25",
                    work + "/in/%04d.png"], check=True)
    frames = sorted(glob.glob(work + "/in/*.png"))
    fn = render(kind)
    for i, p in enumerate(frames, start=1):
        Image.open(p).convert("RGBA")
        img = fn(Image.open(p).convert("RGBA"), i - 1)
        img.convert("RGB").save(work + "/out/%04d.png" % i)
    subprocess.run([FF, "-loglevel", "error", "-y", "-framerate", "25",
                    "-i", work + "/out/%04d.png", "-c:v", "libx264", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-r", "25", dst], check=True)
    print("✅ 花字动画完成:", dst, len(frames), "帧")


if __name__ == "__main__":
    main()
