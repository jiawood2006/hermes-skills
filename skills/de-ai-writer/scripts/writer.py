#!/usr/bin/env python3
"""
De-AI Writer — 写作引擎统一入口
================================
把 AI 文案/小说/营销文改写成自然、有真人味的文本，并提供风格克隆、变体、语气调节、质量评分。

用法:
  python3 writer.py check -t "文本" / 文件.txt         # AI味体检（免key：命中报告+指数）
  python3 writer.py demo                                # 免key本地演示（内置示例，无需API Key）
  python3 writer.py demo -t "文本" / 文件.txt           # 免key处理自己的文本
  python3 writer.py deai 输入.txt -o 输出.txt          # 去 AI 味（核心，需 LLM key 深度改写）
  python3 writer.py stylize 输入.txt --sample 样本.txt  # 风格克隆：模仿样本风格改写
  python3 writer.py variants 输入.txt -n 3              # 生成 3 个变体（A/B 测试）
  python3 writer.py tone 输入.txt --tone casual         # 语气调节: casual/formal/marketing/humor/direct
  python3 writer.py review 输入.txt                     # 8 维度质量评分（0-100）
  python3 writer.py deai -t "文本"                      # 直接传文本
  echo "文本" | python3 writer.py deai -                 # 管道输入
  python3 writer.py deai 输入.txt --prompt-only         # 只输出提示词（无 API key 时用）

配置:
  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL（环境变量或 ~/.deai_writer.conf [llm] 段）
  demo 子命令不需要任何配置 —— 本地规则引擎，零依赖。
"""
import sys, os, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import call_llm, read_text, write_out

# ---------- 核心提示词（产品核心资产 · 中文 AI 味模式库） ----------
DEAI_RULES = """你是资深中文编辑，专长是去除 AI 味、恢复真人写作。中文 AI 味 ≠ 英文 AI 味：
英文看 delve/em-dash，中文看"赋能/闭环/首先其次/综上所述/翻译腔"。
按 8 类清除（每类给高频实例，命中同类自行扩展）：

【1. 空洞拔高】
- 句式："不仅...更是"（→"不光…也"）"标志着"（→"意味着"）"彰显了"（→"体现了"）
- 词："至关重要""不可或缺""毋庸置疑""深远影响""举足轻重""前所未有的"
- 自夸式拔高："值得信赖的选择""实力见证""品质保证"

【2. 万能机械连接（句首连接词当装饰品时删）】
- "首先/其次/再次/最后"（列表感）"总而言之/综上所述/总的来说/由此可见/不难发现"
- "值得注意的是/需要注意的是/值得一提的是"（后文无真正"值得注意"内容就删）
- "此外/与此同时/另外"（删后直接接下一句更利落）

【3. 官方腔黑话（换人话）】
- 词表：赋能(→支持)、闭环、抓手、颗粒度、底层逻辑、方法论、对齐、心智、破圈、
  护城河、赛道、打法、红利、生态位、组合拳、沉淀、拉通、共建、复用、联动、反哺
- 公文副词堆叠：进一步/切实/着力/大力/积极/持续/不断——只留一个必要的

【4. 形容词堆砌 / 夸张词】
- "极致""巅峰""完美""卓越""顶级""一流""超凡""颠覆性""革命性""史无前例"
- 空泛的"非常非常""极其""无比"连用

【5. 翻译腔（欧化句式）】
- 名词化动词："进行了讨论/调查/分析"（→"讨论了/调查了/分析了"）
- "被"字句滥用："被认为/被视为"（→ 主动）
- "之一"句式："最重要的事情之一"（→ 直接说最重要的事）
- "在...中扮演着重要角色"（→ 直接说做什么）
- "关于...的问题"（→ 直接说问题）
- "随着...的发展，..."（AI 万能开场，删"随着"句）
- "不仅仅...而且...更是..."叠加

【6. 模板化结尾 / 空话】
- "未来可期""让我们拭目以待""让我们一起携手共创美好未来"
- "开启/谱写新的篇章""砥砺前行""共创美好明天"
- "希望对您有帮助""欢迎随时联系""如有任何问题请随时..."

【7. 排比三连 / 工整病】
- "创新、卓越、领先"式强制三连（该几个就几个）
- 每段三句、句长均匀、结构对称到假——打破节奏，长短交错

【8. 重复主语 / 过度客套 / chatbot 腔】
- 反复用"该产品/此方案/其"替代（用"它"或直接重复名词）
- "我相信/我们有信心"开场自我表态过多
- "当然""确实""值得注意的是"高频口头禅
- 删除"希望以上对您有帮助""如有任何疑问请随时联系我"式客服尾

【写作要求】
- 保留原意、事实、数据，只改表达
- 短句长句交错，自然呼吸感；允许轻微不完美
- 可以有一点个人态度（"说实话""我个人觉得"），但不要过度
- 中文优先，专有名词保留原文
- 输出 ONLY 改写后的文本，不要任何解释、前言、后记"""

STYLE_PROMPT_TMPL = """你是一位擅长风格模仿的资深写手。请把用户文本改写成【参考风格】的样子。

【参考风格样本】
{style_sample}

【改写要求】
- 严格模仿样本的：句式长短、用词习惯、语气节奏、段落结构、口语/书面比例
- 保留用户文本的原意、事实、数据
- 不要写成样本的复制品——是"用样本的方式讲用户的内容"
- 中文优先，专有名词保留
- 输出 ONLY 改写后的文本"""

TONE_MAP = {
    "casual": "口语化、松弛、像朋友聊天（可以带语气词，如'嘛''呗''说实话'）",
    "formal": "正式、克制、专业，用书面语但不要官方腔",
    "marketing": "有煽动力、有钩子、短促有力，适合营销文案/朋友圈/小红书",
    "humor": "轻松幽默，可以有俏皮话，但不要尬梗",
    "direct": "直接、干脆、少修饰，句句有用，删掉一切废话",
}

REVIEW_SYSTEM = """你是严格的写作质量评审。请对文本做 8 维度评分（每项 0-100），并给出总分和 3 条最具体的改进建议。

评分维度：
1. Hook（开篇吸引力）：开头抓不抓人
2. Pacing（节奏）：推进是否拖沓、信息密度是否合理
3. Emotion（情绪）：能不能打动人
4. AI Smell（AI味）：像不像人写的（低分=AI味重）
5. Clarity（清晰度）：语句通顺、逻辑清楚
6. Persuasion（说服力）：观点/卖点是否有力度
7. Structure（结构）：段落组织、起承转合
8. Readability（可读性）：长句/短句配比，是否容易读

输出 JSON 格式：
{"scores": {"Hook": 80, "Pacing": 70, "Emotion": 60, "AI_Smell": 45, "Clarity": 85, "Persuasion": 65, "Structure": 75, "Readability": 88}, "total": 71, "summary": "一句话总评", "suggestions": ["建议1", "建议2", "建议3"]}"""


def cmd_deai(args):
    text = read_text(args.input)
    if args.prompt_only:
        print(DEAI_RULES + "\n\n【用户文本】\n" + text)
        return
    prompt = DEAI_RULES + "\n\n【用户文本】\n" + text
    out = call_llm(prompt, system="你是一位资深中文编辑，专长是去除 AI 味、恢复真人写作风格。", temperature=0.7)
    write_out(out, args.output)


def cmd_stylize(args):
    text = read_text(args.input)
    sample = read_text(args.sample)
    prompt = STYLE_PROMPT_TMPL.format(style_sample=sample[:4000]) + "\n\n【用户文本】\n" + text
    out = call_llm(prompt, system="你是一位擅长风格模仿的资深中文写手。", temperature=0.8)
    write_out(out, args.output)


def cmd_variants(args):
    text = read_text(args.input)
    n = max(1, min(args.count, 6))
    prompt = (f"请对下面的文本生成 {n} 个不同风格的改写版本，每个版本用【版本1】【版本2】... 分隔。\n"
              "版本之间要有明显差异（如：一个更短促有力、一个更口语松弛、一个更有画面感）。\n"
              f"保留原意、事实、数据。\n\n【用户文本】\n{text}")
    out = call_llm(prompt, system="你是一位资深中文编辑，擅长同一内容的多风格变体创作。", temperature=0.9)
    write_out(out, args.output)


def cmd_tone(args):
    text = read_text(args.input)
    tone_desc = TONE_MAP.get(args.tone, TONE_MAP["casual"])
    prompt = (f"请把下面的文本改写成【{args.tone}】语气。\n"
              f"语气定义：{tone_desc}\n"
              "保留原意、事实、数据，输出 ONLY 改写后的文本。\n\n【用户文本】\n" + text)
    out = call_llm(prompt, system="你是一位擅长语气转换的中文写作专家。", temperature=0.8)
    write_out(out, args.output)


def cmd_review(args):
    text = read_text(args.input)
    out = call_llm(text[:6000], system=REVIEW_SYSTEM, temperature=0.3)
    # 尝试解析 JSON，友好显示
    try:
        import json
        data = json.loads(out[out.find("{"): out.rfind("}") + 1])
        print(f"📊 总分: {data.get('total', '?')}/100")
        print(f"总评: {data.get('summary', '')}")
        print("\n维度评分:")
        for k, v in data.get("scores", {}).items():
            bar = "█" * max(1, v // 10)
            print(f"  {k:<14} {v:>3} {bar}")
        print("\n改进建议:")
        for s in data.get("suggestions", []):
            print(f"  • {s}")
    except Exception:
        print(out)


def cmd_check(args):
    """AI 味体检：writer.py check [文件] | -t 文本"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from demo import show_check
    text = args.text
    if not text and args.input and args.input != "-":
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    if not text:
        print("用法: python3 writer.py check -t \"你的文本\" 或 writer.py check 文件.txt")
        raise SystemExit(1)
    show_check(text, no_color=args.no_color)


def cmd_demo(args):
    """免 key 本地演示：writer.py demo [文件] | -t 文本"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from demo import DEMO_TEXT, show_result
    text = args.text
    if not text and args.input and args.input != "-":
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    if not text:
        text = DEMO_TEXT
        print("（未传文本 → 用内置示例演示；处理自己的文本：python3 writer.py demo 你的文件.txt）\n")
    show_result(text, no_color=args.no_color)


def main():
    p = argparse.ArgumentParser(description="De-AI Writer 写作引擎")
    sub = p.add_subparsers(dest="cmd", required=True)

    # check（免 key AI 味体检）
    p_check = sub.add_parser("check", help="AI味体检（免key：命中报告+指数）")
    p_check.add_argument("input", nargs="?", default=None)
    p_check.add_argument("-t", "--text", help="直接传文本")
    p_check.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    p_check.set_defaults(func=cmd_check)

    # demo（免 key）
    p_demo = sub.add_parser("demo", help="免key本地演示（无需API Key）")
    p_demo.add_argument("input", nargs="?", default=None)
    p_demo.add_argument("-t", "--text", help="直接传文本")
    p_demo.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    p_demo.set_defaults(func=cmd_demo)

    # deai
    p_deai = sub.add_parser("deai", help="去 AI 味")
    p_deai.add_argument("input", nargs="?", default=None, help="输入文件或 - (stdin)")
    p_deai.add_argument("-o", "--output", help="输出文件")
    p_deai.add_argument("-t", "--text", help="直接传文本")
    p_deai.add_argument("--prompt-only", action="store_true", help="只输出提示词（无API key）")
    p_deai.set_defaults(func=cmd_deai)

    # stylize
    p_st = sub.add_parser("stylize", help="风格克隆")
    p_st.add_argument("input", nargs="?", default=None)
    p_st.add_argument("-t", "--text", help="直接传文本")
    p_st.add_argument("--sample", required=True, help="风格样本文件")
    p_st.add_argument("-o", "--output")
    p_st.set_defaults(func=cmd_stylize)

    # variants
    p_va = sub.add_parser("variants", help="变体生成")
    p_va.add_argument("input", nargs="?", default=None)
    p_va.add_argument("-t", "--text", help="直接传文本")
    p_va.add_argument("-n", "--count", type=int, default=3)
    p_va.add_argument("-o", "--output")
    p_va.set_defaults(func=cmd_variants)

    # tone
    p_to = sub.add_parser("tone", help="语气调节")
    p_to.add_argument("input", nargs="?", default=None)
    p_to.add_argument("-t", "--text", help="直接传文本")
    p_to.add_argument("--tone", choices=list(TONE_MAP.keys()), default="casual")
    p_to.add_argument("-o", "--output")
    p_to.set_defaults(func=cmd_tone)

    # review
    p_re = sub.add_parser("review", help="质量评分")
    p_re.add_argument("input", nargs="?", default=None)
    p_re.add_argument("-t", "--text", help="直接传文本")
    p_re.set_defaults(func=cmd_review)

    args = p.parse_args()
    # -t 直接传文本 → 转为 stdin 字符串
    if getattr(args, "text", None):
        import io
        args.input = "-"
        sys.stdin = io.StringIO(args.text)
    args.func(args)


if __name__ == "__main__":
    main()
