#!/usr/bin/env python3
"""
Memory Manager — Agent 记忆健康检查
====================================
扫描 Hermes 记忆文件，统计占用、找过期/冗余/矛盾条目，给出整理建议。
额外提供两项能力：
  · 从会话历史里挖掘「用户纠正/长期要求」→ 提示哪些还没进记忆（对标 claude-reflect 的 Learn from Corrections）
  · 会话库（state.db）体检：体积、行数、可回收空间（VACUUM 建议）

用法:
  python3 memcheck.py                     # 全面检查（默认 ~/.hermes/memories/）
  python3 memcheck.py --dir 自定义路径     # 指定记忆目录
  python3 memcheck.py --state-db          # 检查 state.db 体积（含明细）
  python3 memcheck.py --corrections       # 从会话历史挖掘纠正/要求（默认近 30 天）
  python3 memcheck.py --corrections-days 90 --corrections-limit 800
  python3 memcheck.py --full              # 完整报告（含每条记忆分析）

说明:
  Hermes 记忆分两层：MEMORY.md（个人笔记）+ USER.md（用户档案）
  记忆会注入每个会话的 system prompt——太大 = 每轮浪费 token
"""
import os, sys, re, argparse, datetime, sqlite3, time

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


# ═══════════════════════════════════════════════════════════
# 从会话历史挖掘「纠正 / 长期要求」（对标 claude-reflect）
# ═══════════════════════════════════════════════════════════
CORRECTION_PATTERNS = [
    (r"不是|不对|错了|搞错|弄错|胡编|幻觉|编的", "否定/纠错"),
    (r"我(要求|说过|强调|讲过|提过)|跟你(说|讲)过|我(早|已)就说过", "重复强调"),
    (r"记住|记下来|别忘了|要记得|存(到)?记忆", "显式要求记住"),
    (r"不要|别再|不准|禁止|不能(再)?", "禁止类"),
    (r"以后(都|要|必须|别)|每次(都|要)|下次(要|别)|从来", "长期规则"),
    (r"必须|应该(是|要)|一定要|务必", "强约束"),
    (r"你怎么|谁让你|为什么还|又(这样|犯)|说了多少", "不满/追问"),
]


def scan_corrections(db_path, limit=400, days=30):
    """扫会话库中近 N 天的用户消息，挑出纠正/长期要求 → 候选记忆条目。"""
    if not os.path.exists(db_path):
        print(f"⚠️ 会话库不存在: {db_path}")
        return []
    cutoff = time.time() - days * 86400
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        rows = con.execute(
            "SELECT content, timestamp FROM messages "
            "WHERE role='user' AND content IS NOT NULL "
            "AND length(content) BETWEEN 6 AND 600 AND timestamp > ? "
            "ORDER BY id DESC LIMIT ?",
            (cutoff, limit),
        ).fetchall()
        con.close()
    except Exception as e:
        print(f"⚠️ 读取会话库失败: {e}")
        return []

    cands = []
    for content, ts in rows:
        text = (content or "").strip()
        if not text or text.startswith("[OUT-OF-BAND") or text.startswith("#"):
            continue
        hits = [label for pat, label in CORRECTION_PATTERNS if re.search(pat, text)]
        if not hits:
            continue
        # 打分：命中的类别数 + 长度加成（长句更可能是明确要求）
        score = len(set(hits)) * 2 + min(len(text) / 60, 2)
        cands.append({
            "text": text,
            "ts": ts,
            "hits": sorted(set(hits)),
            "score": score,
        })

    # 去重（前 24 字相同视为同一条要求的重复表达）
    seen, deduped = {}, []
    for c in sorted(cands, key=lambda x: (-x["score"], -x["ts"])):
        key = c["text"][:24]
        if key in seen:
            continue
        seen[key] = 1
        deduped.append(c)
    return deduped


def corrections_report(db_path, mem_dir, limit, days, full=False):
    cands = scan_corrections(db_path, limit=limit, days=days)
    print(f"\n🔎 从会话历史挖掘「纠正 / 长期要求」（近 {days} 天，扫描上限 {limit} 条）")
    print("=" * 50)
    if not cands:
        print("   未发现明显候选（可能没对话，或都已在记忆里）")
        return
    # 读现有记忆做覆盖判断
    mem_text = ""
    for name in ("MEMORY.md", "USER.md"):
        p = os.path.join(mem_dir, name)
        if os.path.exists(p):
            mem_text += open(p, encoding="utf-8").read()

    def covered(t):
        """粗判：记忆里是否已有高度相似内容（用关键词/片段命中）"""
        for n in (12, 16):
            for i in range(0, max(1, len(t) - n), n):
                frag = t[i:i + n]
                if len(frag) >= 8 and frag in mem_text:
                    return True
        return False

    todo = []
    for c in cands:
        c["covered"] = covered(c["text"])
        if not c["covered"]:
            todo.append(c)

    print(f"   候选 {len(cands)} 条，其中 **{len(todo)} 条疑似未进记忆**\n")
    show = cands if full else (todo[:12] or cands[:12])
    for c in show:
        d = datetime.datetime.fromtimestamp(c["ts"]).strftime("%Y-%m-%d")
        tag = "已在记忆" if c["covered"] else "未记录  "
        excerpt = re.sub(r"\s+", " ", c["text"])[:88]
        print(f"   [{tag}] {d} ({'/'.join(c['hits'])}) {excerpt}…")
    if not full and len(todo) > 12:
        print(f"   … 另有 {len(todo)-12} 条未记录候选（--full 看全部）")
    print("\n   💡 用法：把「未记录」里**属于长期偏好/规则**的挑出来写进记忆；")
    print("      一次性的任务要求**不要**写（那是任务，不是偏好）。")


# ═══════════════════════════════════════════════════════════
# 会话库体检
# ═══════════════════════════════════════════════════════════
def state_db_report(db_path):
    if not os.path.exists(db_path):
        return
    size = os.path.getsize(db_path)
    print(f"\n🗄️ state.db（会话历史）: {fmt_size(size)}")
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    except Exception as e:
        print(f"   ⚠️ 打不开: {e}")
        return
    try:
        pc = con.execute("PRAGMA page_count").fetchone()[0]
        ps = con.execute("PRAGMA page_size").fetchone()[0]
        fl = con.execute("PRAGMA freelist_count").fetchone()[0]
        reclaim = fl * ps
        print(f"   页: {pc}×{ps}B | 空闲页: {fl} | 可直接回收: 约 {fmt_size(reclaim)}")
    except Exception:
        pass
    # 最大表（需要 dbstat 支持）
    top_rows = []
    try:
        rows = con.execute(
            "SELECT name, SUM(pgsize) AS sz FROM dbstat GROUP BY name ORDER BY sz DESC LIMIT 5"
        ).fetchall()
        if rows:
            top_rows = rows
            print("   体积占比 Top 表:")
            for name, sz in rows:
                print(f"     {fmt_size(sz):>9}  {name}")
    except Exception:
        pass
    # 行数 + 会话跨度
    try:
        msg = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        ses = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        print(f"   消息 {msg:,} 条 | 会话 {ses:,} 个")
        try:
            row = con.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM sessions"
            ).fetchone()
            if row and row[0]:
                a = datetime.datetime.fromtimestamp(row[0]).strftime("%Y-%m-%d")
                b = datetime.datetime.fromtimestamp(row[1]).strftime("%Y-%m-%d")
                print(f"   时间跨度: {a} → {b}")
        except Exception:
            pass
    except Exception:
        pass
    con.close()

    # 对症建议：先看体积是大在"正文"还是"索引"
    fts_bytes = sum(sz for n, sz in (top_rows or []) if "fts" in n)
    if size > 500 * 1024 * 1024:
        print("   🔴 超过 500MB")
        if fts_bytes > size * 0.4:
            print(f"   ⚠️ 其中 FTS 全文索引占 {fmt_size(fts_bytes)}（{fts_bytes/size:.0%}）——"
                  "索引比正文还大，先处理索引，别急着删会话：")
            print("      1) 备份：cp state.db state.db.bak")
            print("      2) 重建索引（碎片整理，常能显著瘦身）：")
            print("         sqlite3 state.db \"INSERT INTO messages_fts(messages_fts) VALUES('rebuild');\"")
            print("      3) 若仍大，且不需要三元组模糊搜索，可整表重建去掉 trigram：")
            print("         sqlite3 state.db \"DELETE FROM messages_fts_trigram;\" 然后 VACUUM")
            print("      4) 回收空间：sqlite3 state.db 'VACUUM;'（需 2 倍磁盘空闲）")
        else:
            print("   🔴 主要是正文体积：建议清理旧会话 + VACUUM")
            print("      1) 先备份：cp state.db state.db.bak")
            print("      2) 清理：DELETE FROM messages WHERE session_id IN "
                  "(SELECT id FROM sessions WHERE timestamp < strftime('%s','now','-30 day'));")
            print("      3) 回收空间：sqlite3 state.db 'VACUUM;'")
    else:
        print("   🟢 体积正常")


def main():
    p = argparse.ArgumentParser(description="Hermes 记忆健康检查")
    p.add_argument("--dir", default=os.path.expanduser("~/.hermes/memories"), help="记忆目录")
    p.add_argument("--state-db", action="store_true", help="检查 state.db 体积")
    p.add_argument("--full", action="store_true", help="完整报告（逐条分析）")
    p.add_argument("--corrections", action="store_true",
                   help="从会话历史挖掘用户纠正/长期要求（对标 claude-reflect）")
    p.add_argument("--corrections-days", type=int, default=30, help="回溯天数（默认 30）")
    p.add_argument("--corrections-limit", type=int, default=400, help="最多扫描多少条用户消息")
    p.add_argument("--db", default=os.path.expanduser("~/.hermes/state.db"), help="会话库路径")
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

    if args.corrections:
        corrections_report(args.db, args.dir, args.corrections_limit,
                           args.corrections_days, full=args.full)

    if args.state_db or os.path.exists(args.db):
        state_db_report(args.db)

    print("\n💡 建议操作：")
    print("  1. 过期信息（日期类）→ 删除或改为'历史'记录")
    print("  2. 超长条目 → 压缩成要点（保留关键事实，去掉过程）")
    print("  3. 会话细节 → 用 session_search 回忆，不占记忆")
    print("  4. 可复用流程 → 存为 skill，不存记忆")
    print("  5. 反复出现的纠正（--corrections）→ 升级为记忆里的长期偏好")


if __name__ == "__main__":
    main()
