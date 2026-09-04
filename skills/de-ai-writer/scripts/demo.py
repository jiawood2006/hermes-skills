#!/usr/bin/env python3
"""
De-AI Writer Demo Engine — 免 API Key 本地去 AI 味演示引擎
============================================================
纯规则、零依赖、不联网——用正则把最常见的 AI 味口水词/机械连接词/
空话模板删掉，让你在 30 秒内看到"去 AI 味"的真实效果。

为什么有它：
  完整版 deai（writer.py deai）用 LLM 深度改写，效果好但需要 API Key。
  很多人第一次用没有 key —— 先用 demo 引擎看效果，再决定配不配 key。
  规则引擎是"轻度去味"：只删安全的口水词，不重写句子，保证语义不变。

用法:
  python3 demo.py                     # 跑内置示例（推荐第一次用）
  python3 demo.py 输入.txt            # 处理文件
  python3 demo.py -t "要改写的文本"   # 直接传文本
  echo "文本" | python3 demo.py -     # 管道输入
"""
import sys, os, re, argparse

# ---------- 内置示例：一段典型 AI 味文本（公众号/小红书风） ----------
DEMO_TEXT = """今天给大家推荐一款非常不错的产品。首先，这款扫地机器人的外观设计非常出色，采用了极简的白色配色，彰显了高端大气的品质感。其次，它搭载了行业领先的激光导航技术，能够实现精准的建图定位，赋能用户更加智能的清洁体验。此外，它的续航能力也相当优秀，一次充电可以使用长达两个小时。最后，值得一提的是，这款产品还支持手机App远程控制，让你随时随地都能掌握家中情况。总的来说，这是一款性价比很高的产品，相信一定会成为你家居清洁的好帮手！"""

# ---------- 规则表：每项 = (正则, 替换, 标签) ----------
# 规则按"删了绝对安全"设计：口水词、空话模板、机械连接词
RULES = [
    # ── 模板化空话结尾（整段删除，含标点）──
    (r"让我们?一起?拭目以待[！!。]?", "", "空话结尾"),
    (r"(?:我们|大家)一起?拭目以待[！!。]?", "", "空话结尾"),
    (r"未来可期[！!。]?", "", "空话结尾"),
    (r"希望对您(能)?有帮助[！!。]?", "", "空话结尾"),
    (r"欢迎随时联系(我们)?[！!。]?", "", "空话结尾"),
    (r"如有任何疑问[，,]请(随时|及时).{0,12}?[。！!]", "", "空话结尾"),
    (r"在未来的日子里[，,]", "", "空话结尾"),
    (r"让我们共同期待[^。！!]*[。！!]", "", "空话结尾"),

    # ── 万能机械连接词（句首删掉，后面内容保留）──
    (r"(?:^|(?<=[。！!？?]))\s*(?:总而言之|综上所述|总的来说|总体而言|综上|总的来说)[，,]\s*", "", "机械连接"),
    (r"(?:^|(?<=[。！!？?]))\s*(?:值得注意的是|需要注意的是|值得一提的是|不可否认的是)[，,]\s*", "", "机械连接"),
    (r"(?:^|(?<=[。！!？?]))\s*(?:此外|与此同时|另外|再者|除此之外)[，,]\s*", "", "机械连接"),
    (r"(?:^|(?<=[。！!？?]))\s*(?:首先|其次|再次|最后|第一|第二|第三)[，,]\s*", "", "机械连接"),

    # ── 空洞拔高词（换成平实说法）──
    (r"不仅\s*性能\s*卓越\s*，?\s*更是", "不光好用，也", "空洞拔高"),
    (r"彰显(?:了|出)?", "体现了", "空洞拔高"),
    (r"标志着", "意味着", "空洞拔高"),
    (r"毋庸置疑", "不用多说", "空洞拔高"),
    (r"不言而喻", "不用多说", "空洞拔高"),
    (r"至关重要", "很重要", "空洞拔高"),
    (r"不可或缺", "离不开", "空洞拔高"),
    (r"弥足珍贵", "很珍贵", "空洞拔高"),
    (r"深远影响", "影响", "空洞拔高"),
    (r"举足轻重", "很重要", "空洞拔高"),
    (r"完美无缺", "没什么毛病", "空洞拔高"),
    (r"精益求精", "反复打磨", "空洞拔高"),

    # ── 官方腔黑话（换人话）──
    (r"赋能用户", "给用户", "官方黑话"),
    (r"赋能", "支持", "官方黑话"),
    (r"抓手", "办法", "官方黑话"),
    (r"闭环", "循环", "官方黑话"),
    (r"颗粒度", "细致程度", "官方黑话"),
    (r"底层逻辑", "根本道理", "官方黑话"),
    (r"心智", "想法", "官方黑话"),
    (r"打法", "做法", "官方黑话"),
    (r"方法论", "方法", "官方黑话"),
    (r"反哺", "回报", "官方黑话"),
    (r"对齐", "沟通", "官方黑话"),
    (r"破圈", "出圈", "官方黑话"),
    (r"联动", "配合", "官方黑话"),

    # ── 形容词堆砌（删掉不影响语义的夸张词）──
    (r"极致的", "", "夸张词"),
    (r"极致", "", "夸张词"),
    (r"巅峰", "", "夸张词"),
    (r"完美的", "", "夸张词"),
    (r"卓越的?", "出色的", "夸张词"),
    (r"超凡的?", "", "夸张词"),
    (r"颠覆性的?", "", "夸张词"),
    (r"革命性的?", "", "夸张词"),
    (r"史无前例的?", "", "夸张词"),
    (r"空前的?", "", "夸张词"),
    (r"顶级的?", "", "夸张词"),
    (r"一流的?", "", "夸张词"),

    # ── 反复替代主语 → 恢复自然指代 ──
    (r"该产品", "它", "重复主语"),
    (r"该方案", "它", "重复主语"),
    (r"本产品", "它", "重复主语"),
    (r"此方案", "它", "重复主语"),

    # ── 其他常见 AI 味 ──
    (r"总而言之", "", "口水词"),
    (r"毫无疑问", "显然", "口水词"),
    (r"众所周知", "大家都清楚", "口水词"),
    (r"深入浅出", "讲得明白", "口水词"),
]

# 清理替换产生的多余标点/空格
def _cleanup(text: str) -> str:
    text = re.sub(r"[，,]{2,}", "，", text)
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"[，,]\s*[。！!]", "。", text)      # "，。" → "。"
    text = re.sub(r"[，,]\s*[，,]", "，", text)
    text = re.sub(r"^[，,。！!\s]+", "", text)          # 句首残留标点
    text = re.sub(r"[，,]\s*$", "", text)               # 句尾残留逗号
    return text.strip()


def deai_local(text: str, verbose: bool = False):
    """本地规则去味。返回 (改写文本, 命中统计 dict)。"""
    stats = {}
    out = text
    # 跑两轮：第一轮删掉连接词后，句首规则才能在第二轮命中（如"最后，值得一提的是"）
    for _ in range(2):
        changed = False
        for pattern, repl, label in RULES:
            new, n = re.subn(pattern, repl, out)
            if n:
                stats[label] = stats.get(label, 0) + n
                out = new
                changed = True
        if not changed:
            break
    out = _cleanup(out)
    return out, stats


def fmt_stats(stats: dict) -> str:
    if not stats:
        return "未命中明显的 AI 味模式（这段已经挺像人写的了 👍）"
    total = sum(stats.values())
    detail = "、".join(f"{k}×{v}" for k, v in sorted(stats.items(), key=lambda x: -x[1]))
    return f"共清除 {total} 处 AI 味表达（{detail}）"


def show_result(text: str, no_color: bool = False) -> None:
    """处理一段文本并打印 before/after 对照（供 CLI 与 deai.py/writer.py demo 子命令复用）"""
    if not text.strip():
        raise SystemExit("❌ 没有输入内容")
    out, stats = deai_local(text)

    RED, GREEN, DIM, BOLD, END = "", "", "", "", ""
    if not no_color and sys.stdout.isatty():
        RED, GREEN, DIM, BOLD, END = "\033[31m", "\033[32m", "\033[2m", "\033[1m", "\033[0m"

    print(f"{BOLD}【去 AI 味前 / Before】{END}")
    print(f"{text.strip()}\n")
    print(f"{BOLD}【去 AI 味后 / After】{END}")
    print(f"{GREEN}{out}{END}\n")
    print(f"{DIM}{fmt_stats(stats)}{END}")
    print(f"\n{DIM}💡 这是免key的本地规则引擎（轻度去味）。配 API Key 后运行 writer.py deai 可深度改写。{END}")


def main():
    ap = argparse.ArgumentParser(description="De-AI Writer 免key演示引擎（本地规则）")
    ap.add_argument("input", nargs="?", help="输入文件（缺省跑内置示例；- 读 stdin）")
    ap.add_argument("-t", "--text", help="直接传入要改写的文本")
    ap.add_argument("--no-color", action="store_true", help="关闭彩色输出")
    args = ap.parse_args()

    # 读输入
    if args.text:
        text = args.text
    elif args.input and args.input != "-":
        with open(args.input, encoding="utf-8") as f:
            text = f.read()
    elif args.input == "-":
        text = sys.stdin.read()
    else:
        text = DEMO_TEXT
        print("（未传文本 → 用内置示例演示；想处理自己的文本：python3 demo.py 你的文件.txt）\n")

    show_result(text, no_color=args.no_color)


if __name__ == "__main__":
    main()
