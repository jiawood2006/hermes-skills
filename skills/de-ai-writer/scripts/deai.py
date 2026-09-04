#!/usr/bin/env python3
"""
De-AI Writer — AI 文案去味器（通用版 CLI）
============================================
把 AI 生成的文本改写成自然、有真人味的中文。

用法:
  python3 deai.py demo                                # 免key本地演示（内置示例，30秒看效果）
  python3 deai.py demo -t "要改写的文本"               # 免key处理自己的文本
  python3 deai.py 输入文件.txt -o 输出文件.txt     # 处理文件（需 LLM key 深度改写）
  cat 文本.txt | python3 deai.py -o 输出.txt       # 管道输入
  python3 deai.py -t "要改写的文本"                 # 直接传文本
  python3 deai.py 输入.txt --prompt-only           # 只输出 prompt（无API key时用）

配置（环境变量）:
  LLM_API_KEY    API Key（OpenAI 兼容）
  LLM_BASE_URL   接口地址，默认 https://api.openai.com/v1
  LLM_MODEL      模型名，默认 gpt-4o-mini
  不配置也能用：--prompt-only 模式输出可直接粘贴到任意 AI 助手的提示词

示例:
  python3 deai.py draft.txt -o polished.txt
  python3 deai.py -t "此外，该产品不仅性能卓越，更是彰显了创新精神。" 
"""
import sys, os, json, argparse, urllib.request

# ---------- 核心提示词（产品核心资产 · 中文 AI 味模式库） ----------
CORE_PROMPT = """你是资深中文编辑，专长是去除 AI 味、恢复真人写作。中文 AI 味 ≠ 英文 AI 味：英文看 delve/em-dash，中文看"赋能/闭环/首先其次/翻译腔"。按 8 类清除：

【1. 空洞拔高】"不仅...更是"（→不光…也）"标志着"（→意味着）"彰显了"（→体现了）；至关重要/不可或缺/毋庸置疑/深远影响
【2. 万能机械连接】句首"首先/其次/最后/总而言之/综上所述/总的来说/值得注意的是/此外"——后文没有真内容承接就当装饰删掉
【3. 官方腔黑话】赋能(→支持)/闭环/抓手/颗粒度/底层逻辑/方法论/对齐/心智/破圈/护城河/赛道/打法/红利/沉淀/拉通/共建；公文副词"进一步/切实/着力/大力/积极"只留必要
【4. 形容词堆砌】极致/巅峰/完美/卓越/顶级/一流/超凡/颠覆性/革命性/史无前例
【5. 翻译腔（欧化）】"进行了讨论"（→讨论了）"被广泛认为"（→主动句）"最重要的事情之一"（→最重要的事）"在...中扮演着重要角色""随着...的发展，..."万能开场
【6. 模板化结尾】未来可期/让我们拭目以待/开启谱写新的篇章/砥砺前行/共创美好未来/希望对您有帮助/欢迎随时联系
【7. 排比三连/工整病】"创新、卓越、领先"式强制三连；句长句构均匀到假——长短交错、允许轻微不完美
【8. 重复主语/客套/chatbot腔】反复"该产品/此方案/其"（用"它"）；"我相信/我们有信心"表态过多；"希望以上对您有帮助"式客服尾

【写作要求】保留原意事实数据只改表达；短句长句交错自然；可有一点个人态度但不过度；中文优先专名保留；输出 ONLY 改写文本，无任何解释前言后记

【用户文本】
"""

def build_prompt(text: str) -> str:
    return CORE_PROMPT + text

def load_config():
    """读取配置：参数优先，其次 ~/.deai_writer.conf 配置文件。
    配置示例 (~/.deai_writer.conf):
        [llm]
        key = sk-xxx
        base_url = https://api.deepseek.com/v1
        model = deepseek-chat
    """
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(os.path.expanduser("~/.deai_writer.conf"))
    key = cfg.get("llm", "key", fallback="")
    base = cfg.get("llm", "base_url", fallback="https://api.openai.com/v1")
    model = cfg.get("llm", "model", fallback="gpt-4o-mini")
    return key, base, model

def call_llm(prompt: str, api_key: str = "", base_url: str = "", model: str = "") -> str:
    if not api_key:
        api_key, base_url, model = load_config()
    base = base_url.rstrip("/")
    if not api_key:
        raise SystemExit("❌ 未配置 API Key。用 --api-key 参数，或写 ~/.deai_writer.conf（见 load_config 注释），或用 --prompt-only 模式。")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()

def main():
    # ── check 快捷模式：deai.py check [文件] | -t "文本"（AI味体检，免key）──
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from demo import show_check
        ap_c = argparse.ArgumentParser(description="deai.py check — AI味体检（免key）")
        ap_c.add_argument("input", nargs="?", help="输入文件")
        ap_c.add_argument("-t", "--text", help="直接传入文本")
        ap_c.add_argument("--no-color", action="store_true", help="关闭彩色输出")
        c = ap_c.parse_args(sys.argv[2:])

        text = c.text
        if not text and c.input:
            with open(c.input, encoding="utf-8") as f:
                text = f.read()
        if not text:
            print("用法: python3 deai.py check -t \"你的文本\" 或 deai.py check 文件.txt")
            raise SystemExit(1)
        show_check(text, no_color=c.no_color)
        return

    # ── demo 快捷模式：deai.py demo [文件] | -t "文本"（免key本地演示）──
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from demo import DEMO_TEXT, show_result
        ap_d = argparse.ArgumentParser(description="deai.py demo — 免key本地去AI味演示")
        ap_d.add_argument("input", nargs="?", help="输入文件（缺省跑内置示例）")
        ap_d.add_argument("-t", "--text", help="直接传入要改写的文本")
        ap_d.add_argument("--no-color", action="store_true", help="关闭彩色输出")
        d = ap_d.parse_args(sys.argv[2:])

        text = d.text
        if not text and d.input:
            with open(d.input, encoding="utf-8") as f:
                text = f.read()
        if not text:
            text = DEMO_TEXT
            print("（未传文本 → 用内置示例演示；处理自己的文本：python3 deai.py demo 你的文件.txt）\n")
        show_result(text, no_color=d.no_color)
        return

    # ── 正常去味模式（LLM 深度改写）──
    ap = argparse.ArgumentParser(description="De-AI Writer — AI 文案去味器")
    ap.add_argument("input", nargs="?", help="输入文件（缺省读 stdin）")
    ap.add_argument("-t", "--text", help="直接传入要改写的文本")
    ap.add_argument("-o", "--output", help="输出文件（缺省打印 stdout）")
    ap.add_argument("--prompt-only", action="store_true", help="只输出提示词（不调用 API）")
    ap.add_argument("--api-key", default="", help="API Key（优先于配置文件）")
    args = ap.parse_args()

    # 读输入
    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    if not text.strip():
        raise SystemExit("❌ 没有输入内容")

    if args.prompt_only:
        result = build_prompt(text)
    else:
        try:
            print("⏳ 正在改写...", file=sys.stderr)
            result = call_llm(build_prompt(text), api_key=args.api_key)
        except SystemExit:
            print("\n💡 没配 API Key？先跑 python3 deai.py demo 免key看效果（本地规则版）；\n"
                  "   或写 ~/.deai_writer.conf 配 key 后用 LLM 深度改写。", file=sys.stderr)
            raise

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"✅ 已保存到 {args.output}", file=sys.stderr)
    else:
        print(result)

if __name__ == "__main__":
    main()
