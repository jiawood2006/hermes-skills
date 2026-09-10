---
name: doc-ocr
description: "文档识别+结构化。用户提供 PDF/扫描件/图片（合同、发票、书页、截图），需要提取文字、转成可编辑文本、生成可搜索 PDF、剔除页眉页脚水印、或抽取结构化字段（发票号码/合同金额/表格）时使用。扫描件自动 OCR（macOS Vision，中英文），OCR 后可接 LLM 抽取发票/合同关键字段或转表格。Document OCR: extract editable text from PDFs, scans, images — plus searchable-PDF output, header/footer/watermark region filtering, and structured field extraction (invoices, contracts, tables) via LLM."
version: 2.1.0
author: 涛哥
license: MIT
metadata:
  hermes:
    tags: [ocr, pdf, document, text-extraction, scan, invoice, contract, table]
    category: utilities
    homepage: https://github.com/jiawood2006/hermes-skills
---

# Doc-OCR 文档识别 + 结构化

PDF / 扫描件 / 图片 → 可编辑文字 → **结构化数据**。有文字层的 PDF 直接提取，扫描件自动 OCR（macOS Vision 自带，中英文），**版面还原**（多栏/复杂排版按阅读顺序重排，不是裸行输出），**区域过滤**（剔除页眉/页脚/水印），**可搜索 PDF**（扫描件写隐形文字层，可 Ctrl+F / 复制），OCR 后可用 LLM 抽取发票/合同字段、转表格。

> **与同类工具的关系**：跨平台批量 OCR 可以看 Umi-OCR / PaddleOCR，生成可搜索 PDF 可以看 OCRmyPDF——本技能覆盖这两者的**核心高频用途**，且**文件全程本机处理、零上传**（仅在结构化抽取时调用 LLM API）。

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

### 2. 批量目录（逐文件容错，坏文件不中断）

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py ./扫描件/ -o 全部.txt
# 批量完成输出汇总：成功 N/M + 失败清单（坏文件单独记录不中断整批）
```

### 3. Markdown 输出 / 多栏 PDF 强制版面还原

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 书.pdf --md
# 多栏 PDF 文字层乱序时，强制走 Vision OCR 版面还原：
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 双栏论文.pdf --md --force-ocr
```

### 4. 剔除页眉/页脚/水印带（`--ignore-region`）

扫描件常带页眉、页脚、水印、骑缝章文字，污染提取结果。按**归一化比例**剔除，不需要知道具体坐标：

```bash
# 去掉顶部 8% 和底部 6% 的文字带
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 合同.pdf --ignore-region "top=8%,bottom=6%"

# 也可组合 left= / right=（去掉左侧装订线区域的花边/水印）
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 扫描件.pdf --ignore-region "top=7%,bottom=5%,left=4%"
```

- 支持 `top` / `bottom` / `left` / `right` 四边，比例为**页面尺寸的百分比**（也可写小数 `0.08`）
- 判定依据是文字块的**中心点**落在忽略带内
- 运行时打印 `↳ 忽略区域剔除 N 块文字`，可确认生效

### 5. 生成可搜索 PDF（`--searchable-pdf`）

扫描件变**可搜索 / 可复制**的 PDF：在原页面上写入**隐形文字层**，版面观感完全不变（对标 OCRmyPDF 的核心价值，本地零上传）：

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 扫描合同.pdf --searchable-pdf
# 输出：扫描合同_searchable.pdf（可在阅读器里 Ctrl+F 搜索、可选中复制）

# 配合区域过滤：把页眉页脚也排除在文字层之外
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 扫描合同.pdf \
        --searchable-pdf --ignore-region "top=8%,bottom=6%"
```

- 文字块用 CJK 内置字体写入，中文可正常检索（已实测）
- **仅 PDF 输入适用**（图片输入会跳过并提示）
- 原文件不动，另存 `_searchable.pdf`

### 6. 指定识别语言（`--lang`）

```bash
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 日文.pdf --lang ja,en
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 繁体.pdf --lang zh-Hant,en
```

缺省 `zh-Hans,en`（简体中文 + 英文）。

### 7. 结构化抽取（发票/合同/表格，需 LLM key）

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
- **版面还原**：Vision OCR 按文字框坐标重排（从上到下、同行从左到右）；双栏印刷体会被当成"先左栏再右栏"处理，适合论文/报告，杂志花式排版可能仍乱序——用 `--force-ocr` + 目测。
- **手写体**：Vision 对印刷体/清晰手写效果好，潦草手写不保证。
- **隐私卖点**：文件在本机处理，不上传第三方（结构化抽取会调 LLM API，注意敏感文件）。
- **字段缺失**：docstruct 对缺失字段填 null 不编造，OCR 质量差时字段会少。
- **批量容错**：目录模式单文件失败会记录进汇总，不会中断整批。
- **区域过滤是"按比例"不是"按内容"**：`--ignore-region` 剔除的是**版面带**，不是识别特定文字。如果页眉只占 3% 就别设 top=8%，会误删正文首行。先跑一次不带过滤的，看清页眉/页脚位置再定比例。
- **可搜索 PDF 依赖原图质量**：文字层是按 OCR 结果写的，OCR 认错的字**搜索时也认错**（字形和原图仍一致）。要更高准确率就换更清晰的扫描源。
- **可搜索 PDF 是另存新文件**：原 PDF 不会被改动；`_searchable.pdf` 体积略增（多了一层文字）。

## 快速验证 / Smoke Test

```bash
# 安装验证（无文档在手也能跑）
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py --help
# 有任意 PDF/图片时的真实验证
python3 ~/.hermes/skills/utilities/doc-ocr/scripts/dococr.py 任意文档.pdf --md
# 期望：输出 *_ocr.md，含可编辑文字
```
