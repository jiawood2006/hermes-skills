#!/usr/bin/env python3
"""
Doc-OCR — 文档文字识别（版面还原版）
=====================================
PDF / 图片 → 可编辑文字。支持扫描件 OCR（macOS Vision 自带，中英文）。

版面还原：多栏 PDF / 复杂排版按阅读顺序重排（bbox 坐标排序），不是裸按行输出。
区域过滤：可剔除页眉/页脚/水印带（对标 Umi-OCR 的"忽略区域"）。
可搜索 PDF：把识别结果作为隐形文字层写回 PDF，扫描件变可搜索/可复制（对标 OCRmyPDF 核心功能）。

用法:
  python3 dococr.py 文件.pdf              # PDF → 文字（有文字层直接提取，扫描件自动OCR）
  python3 dococr.py 文件.png              # 图片 → OCR
  python3 dococr.py 目录/ -o 输出.txt     # 批量处理目录（逐文件容错，坏文件不中断）
  python3 dococr.py 文件.pdf --md         # 输出 Markdown
  python3 dococr.py 扫描件.pdf --ignore-region top=8%,bottom=6%   # 剔除页眉页脚带
  python3 dococr.py 扫描件.pdf --searchable-pdf                   # 生成可搜索 PDF
  python3 dococr.py 文件.png --lang zh-Hans,en,ja                 # 指定识别语言

输出:
  <输入名>_ocr.txt（或 --md 输出 .md）；批量时输出 <输出>_summary.txt 汇总
  --searchable-pdf 额外输出 <输入名>_searchable.pdf

依赖:
  macOS 自带 Vision（无需安装）；PDF 用 pymupdf: pip install pymupdf
"""
import sys, os, argparse, glob

# Vision 坐标系是归一化、原点在左下。阅读顺序 = 从上(y大)到下，同行内从左(x小)到右。
def _sort_by_layout(items):
    """items: [(text, y_top, x_left)] → 按阅读顺序排序后的文本行列表。"""
    if not items:
        return []
    items.sort(key=lambda t: (-t[1], t[2]))
    # 行分组：y 差小于容差视为同一行（Vision 行高约 0.02-0.05，容差取 0.015）
    rows = []
    cur = [items[0]]
    for it in items[1:]:
        if abs(it[1] - cur[-1][1]) < 0.015:
            cur.append(it)
        else:
            rows.append(cur)
            cur = [it]
    rows.append(cur)
    lines = []
    for row in rows:
        row.sort(key=lambda t: t[2])
        lines.append("".join(t[0] for t in row))
    return lines


# ── 区域过滤（页眉/页脚/水印）──────────────────────────────────────────
def parse_ignore_region(spec: str):
    """'top=8%,bottom=6%' → [('top', 0.08), ('bottom', 0.06)]；支持 left/right 同理。"""
    bands = []
    if not spec:
        return bands
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise SystemExit(f"❌ --ignore-region 格式错误: '{part}'（应为 top=8%,bottom=6%）")
        side, val = part.split("=", 1)
        side = side.strip().lower()
        if side not in ("top", "bottom", "left", "right"):
            raise SystemExit(f"❌ --ignore-region 边只能是 top/bottom/left/right，收到 '{side}'")
        val = val.strip().rstrip("%")
        try:
            ratio = float(val)
        except ValueError:
            raise SystemExit(f"❌ --ignore-region 数值不合法: '{val}'")
        if ratio <= 0 or ratio >= 1:
            ratio = ratio / 100.0          # 视为百分数
        if not 0 < ratio < 1:
            raise SystemExit(f"❌ --ignore-region 比例须在 0~100% 之间，收到 '{val}'")
        bands.append((side, ratio))
    return bands


def in_ignored_band(box, bands):
    """box = (x0, y0, x1, y1) 归一化（原点左下）。命中任一忽略带 → True。"""
    if not bands:
        return False
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2.0
    cx = (x0 + x1) / 2.0
    for side, ratio in bands:
        if side == "top" and cy > 1.0 - ratio:
            return True
        if side == "bottom" and cy < ratio:
            return True
        if side == "left" and cx < ratio:
            return True
        if side == "right" and cx > 1.0 - ratio:
            return True
    return False


# ── OCR 核心 ─────────────────────────────────────────────────────────
def ocr_image_boxes(path: str, langs=("zh-Hans", "en")):
    """用 macOS Vision 识别图片 → [(text, x0, y0, x1, y1)]（归一化，原点左下）。"""
    import Vision
    from Foundation import NSURL
    url = NSURL.fileURLWithPath_(path)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(list(langs))
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"Vision OCR 失败: {err}")
    out = []
    for r in (request.results() or []):
        cand = r.topCandidates_(1)[0].string()
        bb = r.boundingBox()
        x0, y0 = bb.origin.x, bb.origin.y
        out.append((cand, x0, y0, x0 + bb.size.width, y0 + bb.size.height))
    return out


def ocr_image(path: str, ignore=None, langs=("zh-Hans", "en")) -> str:
    """识别图片文字，按版面（阅读顺序）还原；可选剔除忽略带。"""
    boxes = ocr_image_boxes(path, langs=langs)
    kept = [b for b in boxes if not in_ignored_band(b[1:], ignore)]
    dropped = len(boxes) - len(kept)
    if dropped:
        print(f"   ↳ 忽略区域剔除 {dropped} 块文字", file=sys.stderr)
    items = [(t, y1, x0) for (t, x0, y0, x1, y1) in kept]
    return "\n".join(_sort_by_layout(items))


def ocr_pdf_pages(path: str, ignore=None, langs=("zh-Hans", "en")) -> str:
    """PDF 逐页转图片后 OCR。"""
    import fitz  # pymupdf
    doc = fitz.open(path)
    parts = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        tmp = f"/tmp/dococr_p{i}.png"
        pix.save(tmp)
        try:
            text = ocr_image(tmp, ignore=ignore, langs=langs)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        parts.append(f"--- 第{i+1}页 ---\n{text}")
    return "\n\n".join(parts)


def make_searchable_pdf(src: str, out: str, ignore=None, langs=("zh-Hans", "en"), dpi=200) -> int:
    """扫描件 PDF → 可搜索 PDF：把 OCR 结果作为**隐形文字层**写回原页面。

    对标 OCRmyPDF 的核心价值：扫描件可被搜索/复制，且不改变原版面观感。
    返回写入的文字块数。
    """
    import fitz
    doc = fitz.open(src)
    total = 0
    for i, page in enumerate(doc):
        W, H = page.rect.width, page.rect.height
        big = page.get_pixmap(dpi=dpi)
        tmp = f"/tmp/dococr_sp{i}.png"
        big.save(tmp)
        try:
            boxes = ocr_image_boxes(tmp, langs=langs)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        for text, x0, y0, x1, y1 in boxes:
            if in_ignored_band((x0, y0, x1, y1), ignore):
                continue
            fs = max(4.0, (y1 - y0) * H * 0.85)          # 用框高估字号
            baseline_y = y0 * H + (y1 - y0) * H * 0.22    # 基线略高于框底
            try:
                page.insert_text((x0 * W, baseline_y), text, fontname="china-s",
                                 fontsize=fs, render_mode=3)   # 3 = 隐形（仅文字层）
                total += 1
            except Exception:
                continue
    doc.save(out, garbage=3, deflate=True)
    doc.close()
    return total


def extract_pdf_text(path: str, ignore=None, langs=("zh-Hans", "en")) -> str:
    """优先提取 PDF 文字层；几乎无文字则走 OCR。
    多栏 PDF 文字层乱序时也可 --force-ocr 强制走 Vision 版面还原。"""
    import fitz
    doc = fitz.open(path)
    text = "".join(page.get_text() for page in doc)
    if len(text.strip()) > 20:
        return text
    print("⚠️ 文字层为空（扫描件），启动 OCR...", file=sys.stderr)
    return ocr_pdf_pages(path, ignore=ignore, langs=langs)


def to_markdown(text: str) -> str:
    """普通文本 → 简单 Markdown：页分隔符变二级标题，行间空行。"""
    out = []
    for line in text.splitlines():
        if line.startswith("--- "):
            out.append("\n## " + line.strip("--- ") + "\n")
        else:
            out.append(line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Doc-OCR — 文档文字识别（版面还原 + 区域过滤 + 可搜索PDF）")
    ap.add_argument("input", help="PDF/图片文件 或 目录")
    ap.add_argument("-o", "--output", help="输出文件（缺省 <输入名>_ocr.txt）")
    ap.add_argument("--md", action="store_true", help="输出 Markdown")
    ap.add_argument("--force-ocr", action="store_true", help="PDF 强制走 OCR（多栏乱序时用）")
    ap.add_argument("--ignore-region", default="",
                    help='剔除页眉/页脚/水印带，如 top=8%%,bottom=6%%（可组合 left=/right=）')
    ap.add_argument("--searchable-pdf", action="store_true",
                    help="扫描件 → 可搜索 PDF（隐形文字层，OCRmyPDF 同类能力）")
    ap.add_argument("--lang", default="zh-Hans,en",
                    help="识别语言，逗号分隔（缺省 zh-Hans,en；如 zh-Hant,en,ja）")
    args = ap.parse_args()

    langs = tuple(x.strip() for x in args.lang.split(",") if x.strip()) or ("zh-Hans", "en")
    ignore = parse_ignore_region(args.ignore_region)
    if ignore:
        print("🎯 忽略区域: " + ", ".join(f"{s}={r:.0%}" for s, r in ignore), file=sys.stderr)

    files = []
    if os.path.isdir(args.input):
        files = sorted(sum((glob.glob(os.path.join(args.input, ext))
                            for ext in ("*.pdf", "*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff")), []))
    else:
        files = [args.input]

    if not files:
        raise SystemExit("❌ 没有可处理的文件")

    # 逐文件容错：坏文件记录不中断整批
    all_text, ok_files, fail_files = [], [], []
    for f in files:
        ext = f.lower().rsplit(".", 1)[-1]
        print(f"📄 处理: {os.path.basename(f)}", file=sys.stderr)
        try:
            if ext == "pdf" and args.force_ocr:
                text = ocr_pdf_pages(f, ignore=ignore, langs=langs)
            elif ext == "pdf":
                text = extract_pdf_text(f, ignore=ignore, langs=langs)
            else:
                text = ocr_image(f, ignore=ignore, langs=langs)
            ok_files.append(f)
            all_text.append(f"# {os.path.basename(f)}\n{text}")

            # 可搜索 PDF（仅 PDF 输入有意义）
            if args.searchable_pdf:
                if ext == "pdf":
                    sp = os.path.splitext(f)[0] + "_searchable.pdf"
                    n = make_searchable_pdf(f, sp, ignore=ignore, langs=langs)
                    print(f"🔍 可搜索 PDF: {sp}（写入 {n} 个文字块）")
                else:
                    print("   ↳ 跳过 --searchable-pdf（仅 PDF 输入适用）", file=sys.stderr)
        except Exception as e:
            fail_files.append((f, str(e)))
            print(f"⚠️ 失败: {os.path.basename(f)}: {e}", file=sys.stderr)

    if not ok_files:
        raise SystemExit("❌ 全部文件处理失败")

    result = "\n\n".join(all_text)
    if args.md:
        result = to_markdown(result)
    out = args.output or (os.path.splitext(files[0])[0] + "_ocr" + (".md" if args.md else ".txt"))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(result)
    print(f"✅ 已保存: {out}（{len(result)} 字）")

    # 批量汇总
    if len(files) > 1:
        summary = f"成功 {len(ok_files)}/{len(files)}"
        if fail_files:
            summary += "\n失败清单:\n" + "\n".join(f"  ❌ {f}: {e}" for f, e in fail_files)
        print(f"\n📊 {summary}")
        if args.output:
            with open(os.path.splitext(out)[0] + "_summary.txt", "w", encoding="utf-8") as fh:
                fh.write(summary + "\n")


if __name__ == "__main__":
    main()
