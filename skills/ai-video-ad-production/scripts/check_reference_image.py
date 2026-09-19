#!/usr/bin/env python3
"""参考图体检：白底产品图入池前必跑（防"参考图污染"与"比例不对"）

用途：给 AI 视频模型喂参考图前，先客观量一遍：
  · 产品在画面里的外接框尺寸/占比（太小 → 模型没像素可依，必然走先验）
  · 实测"高:宽"比例，与期望比例（如 HSQ1 真机 1.93:1）对比，超差就报警
  · 四个方向的留白是否均匀（判断是否已裁好）
  · 非白底像素占比（>15% 提示：画面里有背景/其它主体 → 可能污染产品形态，需裁掉）

用法：
  python3 check_reference_image.py <图1> [图2 ...] [--expect 1.93] [--tol 0.15] [--white 235]

要点：
  · 只对**白底产品图**有效（背景必须是纯白/接近白）。场景照/人物照请人工看图。
  · 比例必须在**同一张图内**量（不要把不同视角的图混着量）；俯视图/断面图的比例无意义，
    这类图**本来就不该入池**（会把修长和矮胖平均，实测生成矮胖杯状）。
  · 想要更细的判断，输出还带每张图的"是否需要裁掉某主体"提示，配合人眼确认。

依赖：Pillow 必需；numpy 可选（有则更快）。
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow: pip install pillow")


def measure(path, white_thresh=235):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    small = im
    if max(W, H) > 1600:                      # 控内存，比例不变
        k = 1600 / max(W, H)
        small = im.resize((max(1, int(W * k)), max(1, int(H * k))), Image.LANCZOS)
    w2, h2 = small.size
    try:
        import numpy as np
        a = np.asarray(small).astype(int)
        nonwhite = (a.sum(axis=2) < white_thresh * 3)
        ys, xs = np.where(nonwhite)
        total = w2 * h2
        if len(xs) == 0:
            return None
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        nw = int(nonwhite.sum())
    except ImportError:                       # 无 numpy 时用 PIL
        mask = small.convert("L").point(lambda v: 255 if v < white_thresh else 0)
        bbox = mask.getbbox()
        if bbox is None:
            return None
        nw = sum(mask.histogram()[128:])
        total = w2 * h2
    k = W / w2                                # 还原到原图尺度
    x0, y0, x1, y1 = [int(v * k) for v in bbox]
    bw, bh = x1 - x0, y1 - y0
    return {
        "size": (W, H),
        "box": (bw, bh),
        "ratio": (bh / bw) if bw else 0.0,
        "h_frac": bh / H,
        "w_frac": bw / W,
        "pad": (x0, W - x1, y0, H - y1),
        "nonwhite_frac": nw / total,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--expect", type=float, default=None,
                    help="期望高:宽比例（如 HSQ1 = 1.93）")
    ap.add_argument("--tol", type=float, default=0.15, help="允许偏差（比例值，默认 0.15）")
    ap.add_argument("--white", type=int, default=235, help="白底阈值（默认 235）")
    a = ap.parse_args()

    bad = 0
    for p in a.images:
        try:
            m = measure(p, a.white)
        except Exception as e:
            print(f"❌ {p}: 读取失败 {e}")
            bad += 1
            continue
        if not m:
            print(f"⚠️ {p}: 全白/未检出主体（白底阈值 {a.white} 可能不对）")
            bad += 1
            continue
        flags = []
        if m["h_frac"] < 0.45:
            flags.append(f"产品只占画面高 {m['h_frac']:.0%} → 太小，建议裁到 ~60-70%")
        if m["nonwhite_frac"] > 0.15:
            flags.append(f"非白像素 {m['nonwhite_frac']:.0%} → 画面里有其它内容，"
                         f"**看图确认是否混入形态冲突的主体（污染源），需要就裁掉**")
        l, r, t, b = m["pad"]
        if max(l, r, t, b) - min(l, r, t, b) > 0.12 * max(m["size"]):
            flags.append("四边留白不均 → 未居中裁切")
        if a.expect:
            d = abs(m["ratio"] - a.expect)
            ok = d <= a.tol
            flags.append(("✅" if ok else "❌") +
                         f" 比例 {m['ratio']:.2f}:1 vs 期望 {a.expect:.2f}:1（偏差 {d:.2f}）")
            if not ok:
                bad += 1
        print(f"{p}")
        print(f"   画幅 {m['size'][0]}x{m['size'][1]} | 产品外接框 {m['box'][0]}x{m['box'][1]}px"
              f" | 占宽 {m['w_frac']:.0%} 占高 {m['h_frac']:.0%}"
              f" | 实测高:宽 {m['ratio']:.2f}:1")
        print(f"   留白 左{l} 右{r} 上{t} 下{b} | 非白像素 {m['nonwhite_frac']:.0%}")
        for f in flags:
            print("   - " + f)
    print(f"\n{'❌ 有 ' + str(bad) + ' 项需要处理' if bad else '✅ 全部通过'} "
          f"（提醒：俯视/断面/异角度图不要入池；成片交前还要放大逐帧核对产品形态）")


if __name__ == "__main__":
    main()
