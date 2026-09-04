#!/usr/bin/env python3
"""
Video-To-Text Analyzer — 视频内容情报分析
==========================================
把视频转写文字 → LLM 生成内容情报（摘要 / 爆款结构拆解）。

用法:
  python3 analyze.py 转写.txt --summary        # 生成摘要（要点+金句+话题）
  python3 analyze.py 转写.txt --analyze        # 爆款结构拆解（钩子/节奏/卖点/CTA）
  cat 转写.txt | python3 analyze.py --summary  # 管道输入
  python3 analyze.py 转写.txt --all            # 两者都出

配置（环境变量或 ~/.deai_writer.conf）:
  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 自包含：优先同目录 engine.py
try:
    from engine import call_llm, load_config
except ImportError:
    # 兼容旧安装（de-ai-writer 提供 engine.py）
    sys.path.insert(0, os.path.expanduser("~/.hermes/skills/utilities/de-ai-writer/scripts"))
    from engine import call_llm, load_config

SUMMARY_PROMPT = """你是短视频内容分析师。请对下面的视频转写文本生成内容情报摘要。

输出格式：
【一句话概括】不超过 30 字
【核心要点】3-5 条，每条一句话
【金句】视频中最有传播力的 1-3 句原话
【目标受众】这个视频是给谁看的
【可借鉴点】这个视频值得学习的 2-3 个地方

【转写文本】
{text}"""

ANALYZE_PROMPT = """你是爆款短视频结构分析师。请对下面的视频转写文本做结构拆解。

输出格式：
【开头钩子(0-10s)】用什么方式抓住注意力（悬念/反差/提问/画面冲击...）+ 原话摘录
【节奏结构】视频怎么推进的（痛点→方案→案例→煽动→CTA 等），各阶段占比
【情绪曲线】观众情绪如何被调动（高潮在哪）
【卖点/观点】视频传递的核心观点或卖点
【CTA/结尾】怎么引导关注/转化
【可复用套路】这个视频的套路如何复用到其他内容（2-3 条具体建议）

【转写文本】
{text}"""


def read_text(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    import argparse
    p = argparse.ArgumentParser(description="视频内容情报分析")
    p.add_argument("input", nargs="?", default="-", help="转写文本文件或 - (stdin)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--summary", action="store_true", help="生成摘要")
    g.add_argument("--analyze", action="store_true", help="爆款结构拆解")
    g.add_argument("--all", action="store_true", help="两者都出")
    args = p.parse_args()

    text = read_text(args.input)
    if len(text) > 12000:
        text = text[:12000] + "\n...(截断)"

    if args.summary or args.all:
        print("📋 内容摘要")
        print("=" * 40)
        print(call_llm(SUMMARY_PROMPT.format(text=text), system="你是短视频内容分析师，输出简洁中文。", temperature=0.4))
        print()
    if args.analyze or args.all:
        print("🔍 爆款结构拆解")
        print("=" * 40)
        print(call_llm(ANALYZE_PROMPT.format(text=text), system="你是爆款短视频结构分析师，输出简洁中文。", temperature=0.4))


if __name__ == "__main__":
    main()
