#!/usr/bin/env python3
"""
Doc-OCR — 文档文字识别（版面还原版）
=====================================
PDF / 图片 → 可编辑文字。支持扫描件 OCR（macOS Vision 自带，中英文）。

版面还原：多栏 PDF / 复杂排版按阅读顺序重排（bbox 坐标排序），不是裸按行输出。

用法:
  python3 dococr.py 文件.pdf              # PDF → 文字（有文字层直接提取，扫描件自动OCR）
  python3 dococr.py 文件.png              # 图片 → OCR
  python3 dococr.py 目录/ -o 输出.txt     # 批量处理目录（逐文件容错，坏文件不中断）
  python3 dococr.py 文件.pdf --md         # 输出 Markdown

输出:
  <输入名>_ocr.txt（或 --md 输出 .md）；批量时输出 <输出>_summary.txt 汇总

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


def ocr_image(path: str) -> str:
    """用 macOS Vision 识别图片文字，按版面（阅读顺序）还原。"""
    import Quartz
    from Foundation import NSURL
    import Vision
    url = NSURL.fileURLWithPath_(path)
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(["zh-Hans", "en"])
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    ok, err = handler.performRequests_error_([request], None)
    if not ok:
        return f"[OCR失败: {err}]"
    results = request.results() or []
    items = []
    for r in results:
        cand = r.topCandidates_(1)[0].string()
        bb = r.boundingBox()  # origin 在左下
        # y_top = origin.y + height（取框顶做行定位）；x_left = origin.x
        y_top = bb.origin.y + bb.size.height
        items.append((cand, y_top, bb.origin.x))
    return "\n".join(_sort_by_layout(items))


def ocr_pdf_pages(path: str) -> str:
    """PDF 逐页转图片后 OCR。"""
    import fitz  # pymupdf
    doc = fitz.open(path)
    parts = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        tmp = f"/tmp/dococr_p{i}.png"
        pix.save(tmp)
        try:
            text = ocr_image(tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        parts.append(f"--- 第{i+1}页 ---\n{text}")
    return "\n\n".join(parts)


def extract_pdf_text(path: str) -> str:
    """优先提取 PDF 文字层；几乎无文字则走 OCR。
    多栏 PDF 文字层乱序时也可 --force-ocr 强制走 Vision 版面还原。"""
    import fitz
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    if len(text.strip()) > 20:
        return text
    print("⚠️ 文字层为空（扫描件），启动 OCR...", file=sys.stderr)
    return ocr_pdf_pages(path)


def to_markdown(text: str) -> str:
    """普通文本 → 简单 Markdown：页分隔符变二级标题，行间空行。"""
    out = []
    for line in text.splitlines():
        if line.startswith("--- "):
            out.append("\n## " + line.strip("--- ") + "\n")
        else:
            out.append(line)
    return "\n\n".join(out) if False else "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Doc-OCR — 文档文字识别（版面还原）")
    ap.add_argument("input", help="PDF/图片文件 或 目录")
    ap.add_argument("-o", "--output", help="输出文件（缺省 <输入名>_ocr.txt）")
    ap.add_argument("--md", action="store_true", help="输出 Markdown")
    ap.add_argument("--force-ocr", action="store_true", help="PDF 强制走 OCR（多栏乱序时用）")
    args = ap.parse_args()

    files = []
    if os.path.isdir(args.input):
        files = sorted(glob.glob(os.path.join(args.input, "*.pdf")) +
                       glob.glob(os.path.join(args.input, "*.png")) +
                       glob.glob(os.path.join(args.input, "*.jpg")) +
                       glob.glob(os.path.join(args.input, "*.jpeg")) +
                       glob.glob(os.path.join(args.input, "*.tif")) +
                       glob.glob(os.path.join(args.input, "*.tiff")))
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
                text = ocr_pdf_pages(f)
            elif ext == "pdf":
                text = extract_pdf_text(f)
            else:
                text = ocr_image(f)
            ok_files.append(f)
            all_text.append(f"# {os.path.basename(f)}\n{text}")
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
