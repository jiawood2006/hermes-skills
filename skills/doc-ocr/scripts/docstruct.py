#!/usr/bin/env python3
"""
Doc-OCR Structure — 文档结构化抽取
====================================
OCR 文本 → 结构化数据（发票/合同/表格）。LLM 从识别出的文字里抽取关键字段。

用法:
  python3 docstruct.py 合同_ocr.txt --type contract      # 合同字段抽取
  python3 docstruct.py 发票_ocr.txt --type invoice       # 发票字段抽取
  python3 docstruct.py 表格_ocr.txt --type table         # 表格 → CSV
  cat 扫描件_ocr.txt | python3 docstruct.py --type contract

配置（环境变量或 ~/.deai_writer.conf）:
  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
"""
import sys, os, json, csv, io

sys.path.insert(0, os.path.expanduser("~/.hermes/skills/utilities/de-ai-writer/scripts"))
from engine import call_llm

TYPES = {
    "invoice": {
        "desc": "发票字段抽取",
        "fields": "发票号码、开票日期、金额（不含税）、税额、价税合计、购买方名称、购买方税号、销售方名称、销售方税号、发票类型（专票/普票/电子）",
        "extra": "若字段缺失填 null，不要编造。",
    },
    "contract": {
        "desc": "合同字段抽取",
        "fields": "合同名称、甲方、乙方、签订日期、合同金额、付款方式、工期/交付期限、主要条款摘要（3-5条）、违约条款摘要",
        "extra": "若字段缺失填 null，不要编造。金额只写数字（如 500000，单位元）。",
    },
    "table": {
        "desc": "表格结构化",
        "fields": "识别表格的行列结构，输出为 CSV 格式（第一行表头，后续行数据）",
        "extra": "只输出 CSV 内容，不要解释。列名用原文字。",
    },
}

PROMPT_TMPL = """你是文档结构化专家。请从下面的 OCR 文本中抽取 {desc}。

【需要抽取的字段】
{fields}

【要求】
{extra}
输出 JSON：
{{"fields": {{"字段名": 值}}, "notes": "补充说明"}}

【OCR 文本】
{text}"""


def read_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    import argparse
    p = argparse.ArgumentParser(description="文档结构化抽取（发票/合同/表格）")
    p.add_argument("input", nargs="?", default="-", help="OCR 文本文件或 - (stdin)")
    p.add_argument("--type", choices=list(TYPES.keys()), default="contract")
    p.add_argument("-o", "--output", help="输出文件（.json 或 .csv）")
    args = p.parse_args()

    text = read_text(args.input)
    if len(text) > 15000:
        text = text[:15000] + "\n...(截断)"
    t = TYPES[args.type]
    prompt = PROMPT_TMPL.format(desc=t["desc"], fields=t["fields"], extra=t["extra"], text=text)
    out = call_llm(prompt, system="你是文档结构化专家，输出简洁 JSON。", temperature=0.2)

    # 解析 JSON
    try:
        data = json.loads(out[out.find("{"): out.rfind("}") + 1])
    except Exception:
        # 表格类型直接输出 CSV 文本
        if args.type == "table":
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(out)
                print(f"✅ CSV 已保存: {args.output}")
            else:
                print(out)
            return
        print("⚠️ 无法解析为 JSON，原文如下：")
        print(out)
        return

    fields = data.get("fields", {})
    # 表格 → CSV 文件
    if args.type == "table" and isinstance(fields, list):
        if args.output:
            with open(args.output, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                for row in fields:
                    w.writerow(row if isinstance(row, list) else [row])
            print(f"✅ 表格已保存: {args.output}")
        else:
            for row in fields:
                print(",".join(str(c) for c in (row if isinstance(row, list) else [row])))
        return

    # 普通字段 → 友好显示 / JSON 保存
    print(f"📄 {t['desc']}")
    print("=" * 40)
    for k, v in fields.items():
        print(f"{k}: {v}")
    if data.get("notes"):
        print(f"\n备注: {data['notes']}")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已保存: {args.output}")


if __name__ == "__main__":
    main()
