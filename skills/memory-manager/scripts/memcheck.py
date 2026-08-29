#!/usr/bin/env python3
"""
Memory Manager — Agent 记忆健康检查
====================================
扫描 Hermes 记忆文件，统计占用、找过期/冗余/矛盾条目，给出整理建议。

用法:
  python3 memcheck.py                    # 全面检查（默认 ~/.hermes/memories/）
  python3 memcheck.py --dir 自定义路径    # 指定记忆目录
  python3 memcheck.py --state-db         # 检查 state.db 体积
  python3 memcheck.py --full             # 完整报告（含每条记忆分析）

说明:
  Hermes 记忆分两层：MEMORY.md（个人笔记）+ USER.md（用户档案）
  记忆会注入每个会话的 system prompt——太大 = 每轮浪费 token
"""
import os, sys, re, argparse, datetime

def fmt_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"

def scan_memory_file(path):
    """返回 {entries: [{text, chars, has_date, dates, lines}], total_chars}"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    entries = []
    parts = re.split(r"\n§\s*\n", content) if content.strip() else []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        dates = re.findall(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})", p)
        entries.append({
            "text": p,
            "chars": len(p),
            "dates": dates,
            "lines": p.count("\n") + 1,
        })
    return {"entries": entries, "total_chars": len(content), "path": path}

def find_old_dates(entries, today, days=30):
    """找超过 N 天的日期引用（可能是过期信息）"""
    old = []
    for e in entries:
        for d in e["dates"]:
            try:
                dt = datetime.datetime.strptime(d.replace("/", "-").replace(".", "-"), "%Y-%m-%d")
                age = (today - dt).days
                if age > days:
                    old.append({"text": e["text"][:120], "date": d, "age": age})
            except Exception:
                pass
    return old

def main():
    p = argparse.ArgumentParser(description="Hermes 记忆健康检查")
    p.add_argument("--dir", default=os.path.expanduser("~/.hermes/memories"), help="记忆目录")
    p.add_argument("--state-db", action="store_true", help="检查 state.db 体积")
    p.add_argument("--full", action="store_true", help="完整报告（逐条分析）")
    args = p.parse_args()

    today = datetime.date.today()
    print("🧠 Hermes 记忆健康检查")
    print("=" * 50)

    total_tokens_est = 0
    for name in ["MEMORY.md", "USER.md"]:
        path = os.path.join(args.dir, name)
        data = scan_memory_file(path)
        if not data:
            print(f"\n⚠️ {name}: 不存在")
            continue
        n = len(data["entries"])
        chars = data["total_chars"]
        tokens = chars // 2  # 中文约 1 字 ≈ 1 token；保守估计 2 char/token
        total_tokens_est += tokens
        print(f"\n📄 {name}: {fmt_size(chars)} | {n} 条 | 约 {tokens} tokens/轮")
        if args.full:
            for i, e in enumerate(data["entries"][:20], 1):
                print(f"  [{i}] {e['chars']}字 {' '.join('📅' + d for d in e['dates'][:3])} | {e['text'][:60]}...")
        # 超长条目
        long_entries = [e for e in data["entries"] if e["chars"] > 800]
        if long_entries:
            print(f"  ⚠️ 超长条目（>800字，建议精简）: {len(long_entries)} 条")
            for e in long_entries[:3]:
                print(f"    - {e['chars']}字: {e['text'][:70]}...")
        # 过期日期
        old = find_old_dates(data["entries"], today, days=30)
        if old:
            print(f"  ⚠️ 含 30 天前日期的条目（可能是过期信息）: {len(old)} 处")
            for o in old[:5]:
                print(f"    - [{o['date']} {o['age']}天前] {o['text'][:60]}...")

    print(f"\n📊 每轮对话记忆注入: 约 {total_tokens_est} tokens（建议 <2000）")
    if total_tokens_est > 2000:
        print("   🔴 超过建议上限！记忆太长会浪费 token，需要压缩精简")
    else:
        print("   🟢 记忆体量正常")

    if args.state_db or os.path.exists(os.path.expanduser("~/.hermes/state.db")):
        db = os.path.expanduser("~/.hermes/state.db")
        if os.path.exists(db):
            size = os.path.getsize(db)
            print(f"\n🗄️ state.db（会话历史）: {fmt_size(size)}")
            if size > 500 * 1024 * 1024:
                print("   🔴 超过 500MB！建议清理（删除 7 天前 cron 会话 + VACUUM）")
            else:
                print("   🟢 体积正常")

    print("\n💡 建议操作：")
    print("  1. 过期信息（日期类）→ 删除或改为'历史'记录")
    print("  2. 超长条目 → 压缩成要点（保留关键事实，去掉过程）")
    print("  3. 会话细节 → 用 session_search 回忆，不占记忆")
    print("  4. 可复用流程 → 存为 skill，不存记忆")


if __name__ == "__main__":
    main()
