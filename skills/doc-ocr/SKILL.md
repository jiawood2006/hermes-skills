---
name: doc-ocr
description: "文档识别+结构化。用户提供 PDF/扫描件/图片（合同、发票、书页、截图），需要提取文字、转成可编辑文本、或抽取结构化字段（发票号码/合同金额/表格）时使用。扫描件自动 OCR（macOS Vision，中英文），OCR 后可接 LLM 抽取发票/合同关键字段或转表格。Document OCR: extract editable text from PDFs, scans, images — plus structured field extraction (invoices, contracts, tables) via LLM."
version: 2.0.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [ocr, pdf, document, text-extraction, scan, invoice, contract, table]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# Doc-OCR 文档识别 + 结构化

PDF / 扫描件 / 图片 → 可编辑文字 → **结构化数据**。有文字层的 PDF 直接提取，扫描件自动 OCR（macOS Vision 自带，中英文），OCR 后可用 LLM 抽取发票/合同字段、转表格。

> 📁 **安装**：`hermes skills install jiawood2006/hermes-skills/skills/doc-ocr` 或按 README 方式二复制 → 默认在 `~/.hermes/skills/utilities/doc-ocr/`。以下命令基于该路径。

## 触发条件

用户提供 PDF/图片文件，要求：
- "提取文字""转文字""OCR"
- 处理扫描件、合同、发票、书页、截图
- "提取发票信息""合同要点""转成表格"（结构化）

## 使用步骤

### 1. 单个文件 → 文字

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 合同.pdf
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 发票.jpg
```

输出保存为 `<输入名>_ocr.txt`。

### 2. 批量目录

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py ./扫描件/ -o 全部.txt
```

### 3. Markdown 输出

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 书.pdf --md
```

### 4. 结构化抽取（发票/合同/表格，需 LLM key）

```bash
# 先 OCR，再抽取字段
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 发票.jpg
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/docstruct.py 发票_ocr.txt --type invoice

# 合同字段（甲方/乙方/金额/工期/违约条款）
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/docstruct.py 合同_ocr.txt --type contract

# 表格 → CSV
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/docstruct.py 表格_ocr.txt --type table -o 表格.csv
```

- `--type invoice`：发票号码/日期/金额/税额/价税合计/购买方/销售方/税号
- `--type contract`：合同名称/甲乙双方/签订日期/金额/付款方式/工期/违约条款
- `--type table`：自动识别行列结构 → CSV
- 输出友好显示 + 可保存 JSON/CSV（`-o`）

## 依赖（首次使用时安装）

```bash
pip3 install pymupdf pyobjc-framework-Vision
# 结构化抽取需 LLM key（环境变量 LLM_API_KEY 或 ~/.deai_writer.conf）
```

**注意**：OCR 依赖 macOS Vision（仅 macOS 可用）。Linux 需另装 tesseract 等引擎。

## 已知陷阱

- **扫描件判定**：PDF 文字层 <20 字自动走 OCR，正常 PDF 直接提取。
- **手写体**：Vision 对印刷体/清晰手写效果好，潦草手写不保证。
- **隐私卖点**：文件在本机处理，不上传第三方（结构化抽取会调 LLM API，注意敏感文件）。
- **字段缺失**：docstruct 对缺失字段填 null 不编造，OCR 质量差时字段会少。

