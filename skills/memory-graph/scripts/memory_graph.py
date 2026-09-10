#!/usr/bin/env python3
"""
Memory Graph — 长文记忆图谱（通用版）
=======================================
基于 MAGMA 四图思想，为任何长文/系列内容（小说、连载、剧本、系列教程、世界观设定）提供记忆管理：
  实体图谱  → 人物/地点/物品关系网
  时间图谱  → 事件时间线
  因果图谱  → 事件因果链
  语义图谱  → 概念/设定/主题

用法:
  python3 memory_graph.py init --name 项目名 --dir ./data      # 初始化项目图谱
  python3 memory_graph.py ingest 章节.txt --dir ./data          # 摄入文本（LLM 提取实体/事件/关系）
  python3 memory_graph.py ingest 章节.txt --dir ./data --ch 5   # 标注来源章节/文档编号
  python3 memory_graph.py query 人物名 --dir ./data             # 查询实体信息+关系网
  python3 memory_graph.py timeline --dir ./data                 # 事件时间线
  python3 memory_graph.py status --dir ./data                   # 图谱统计
  python3 memory_graph.py check --dir ./data                    # 一致性检查（矛盾/重复/时间倒挂）
  python3 memory_graph.py export --dir ./data -o 导出.json      # 导出全量

配置（LLM 提取需要）:
  LLM_API_KEY / LLM_BASE_URL / LLM_MODEL（环境变量或 ~/.deai_writer.conf）
  无 LLM key 时可用 --entities "人名,地名" 手动指定实体，规则提取事件。
"""
import sys, os, json, re, argparse, datetime

# ═══════════════════════════════════════════════════════════
# 存储结构（零依赖，dict 图）
# ═══════════════════════════════════════════════════════════

STRUCT = {
    "meta": {"name": "", "created": "", "docs": 0},
    "entities": {},   # id -> {name, type, aliases[], tags{}, first_seen, status, relations[{to,type,note,ch}]}
    "timeline": [],   # [{time, event, entities[], ch, note}]
    "causal": [],     # [{from, to, reason, confidence, ch}]
    "semantic": {},   # concept -> {definition, references[]}
}

TYPES = {"character": "人物", "location": "地点", "object": "物品", "faction": "组织/派系", "concept": "概念"}

# ═══════════════════════════════════════════════════════════

def load_graph(dir_path):
    p = os.path.join(dir_path, "memory_graph.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(STRUCT))

def save_graph(dir_path, graph):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, "memory_graph.json"), "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

def norm_name(s):
    return re.sub(r"\s+", "", s or "").strip()

# ═══════════════════════════════════════════════════════════
# LLM 提取（推荐）
# ═══════════════════════════════════════════════════════════

EXTRACT_PROMPT = """你是内容记忆分析师。从下面的文本中提取结构化记忆，输出 JSON。

【提取内容】
1. entities: 文本中出现的重要实体（人物/地点/物品/组织），每个含 name/type(character|location|object|faction)/aliases(别名)/tags(属性如职业、性格)
2. relations: 实体间关系，每个含 from/to/type(如'认识''敌对''父子''居住')/note
3. events: 重要事件，每个含 time(故事内时间，如"第3天""2024年5月""未知")/event(一句话)/entities(涉及实体)
4. causal: 事件因果关系，每个含 from/to(事件描述)/reason
5. concepts: 文本中的设定/概念，每个含 key/definition

【要求】只提取文本中明确出现或强暗示的信息，不要编造。JSON 格式：
{{"entities": [{{"name": "", "type": "", "aliases": [], "tags": {{}}, }}],
  "relations": [{{"from": "", "to": "", "type": "", "note": ""}}],
  "events": [{{"time": "", "event": "", "entities": []}}],
  "causal": [{{"from": "", "to": "", "reason": ""}}],
  "concepts": [{{"key": "", "definition": ""}}]}}

【文本】
{text}"""

def llm_extract(text, system=""):
    sys.path.insert(0, os.path.expanduser("~/.hermes/skills/utilities/de-ai-writer/scripts"))
    try:
        from engine import call_llm
        out = call_llm(EXTRACT_PROMPT.format(text=text[:12000]),
                       system="你是内容记忆分析师，输出 JSON。", temperature=0.2)
        start, end = out.find("{"), out.rfind("}")
        return json.loads(out[start:end+1]) if start >= 0 else {}
    except Exception as e:
        print(f"⚠️ LLM 提取失败: {e}", file=sys.stderr)
        return {}

def rule_extract(text, manual_entities):
    """无 LLM 时的规则提取：手动实体 + 简单事件句"""
    data = {"entities": [], "relations": [], "events": [], "causal": [], "concepts": []}
    for name in manual_entities or []:
        data["entities"].append({"name": name, "type": "character", "aliases": [], "tags": {}})
    # 事件：按句号切分，含实体的句子作为事件
    for sent in re.split(r"[。！？\n]", text):
        sent = sent.strip()
        if len(sent) > 5 and any(n in sent for n in (manual_entities or []) if n):
            data["events"].append({"time": "未知", "event": sent[:80], "entities": [n for n in (manual_entities or []) if n in sent]})
    return data

# ═══════════════════════════════════════════════════════════
# 摄入
# ═══════════════════════════════════════════════════════════

def ingest(graph, text, ch, manual_entities, use_llm=True):
    # 1. 提取
    data = llm_extract(text) if use_llm else rule_extract(text, manual_entities)
    if not data:
        data = rule_extract(text, manual_entities)

    added = {"entities": 0, "relations": 0, "events": 0, "causal": 0, "concepts": 0}

    # 2. 实体去重合并
    for ent in data.get("entities", []):
        name = norm_name(ent.get("name", ""))
        if not name:
            continue
        if name in graph["entities"]:
            # 补充别名/标签，不重复建
            e = graph["entities"][name]
            for a in ent.get("aliases", []):
                if a and a not in e["aliases"]:
                    e["aliases"].append(a)
            e["tags"].update(ent.get("tags", {}))
            if ch and ch < e.get("first_seen", 999):
                e["first_seen"] = ch
        else:
            graph["entities"][name] = {
                "name": name, "type": ent.get("type", "character"),
                "aliases": ent.get("aliases", []), "tags": ent.get("tags", {}),
                "first_seen": ch or 1, "status": "active", "relations": [],
            }
            added["entities"] += 1

    # 3. 关系去重合并
    seen_rel = set()
    for rel in data.get("relations", []):
        f, t = norm_name(rel.get("from", "")), norm_name(rel.get("to", ""))
        if not f or not t or f == t:
            continue
        key = (f, t, rel.get("type", ""))
        if key in seen_rel:
            continue
        seen_rel.add(key)
        if f in graph["entities"] and t in graph["entities"]:
            graph["entities"][f]["relations"].append({"to": t, "type": rel.get("type", ""), "note": rel.get("note", ""), "ch": ch})
            added["relations"] += 1

    # 4. 事件
    for ev in data.get("events", []):
        graph["timeline"].append({
            "time": ev.get("time", "未知"), "event": ev.get("event", ""),
            "entities": ev.get("entities", []), "ch": ch, "note": "",
        })
        added["events"] += 1

    # 5. 因果
    for ca in data.get("causal", []):
        if ca.get("from") and ca.get("to"):
            graph["causal"].append({"from": ca["from"], "to": ca["to"], "reason": ca.get("reason", ""), "confidence": 0.7, "ch": ch})
            added["causal"] += 1

    # 6. 语义概念
    for c in data.get("concepts", []):
        key = norm_name(c.get("key", ""))
        if key:
            if key in graph["semantic"]:
                graph["semantic"][key]["references"].append(ch or 0)
            else:
                graph["semantic"][key] = {"definition": c.get("definition", ""), "references": [ch or 0]}
            added["concepts"] += 1

    graph["meta"]["docs"] += 1
    return added

# ═══════════════════════════════════════════════════════════
# 查询
# ═══════════════════════════════════════════════════════════

def _resolve(graph, name):
    """名字/别名 → 实体 id；找不到返回 None。"""
    name = norm_name(name)
    if not name:
        return None
    if name in graph["entities"]:
        return name
    for eid, e in graph["entities"].items():
        if name in e.get("aliases", []):
            return eid
    return None


def _print_hops(graph, start, hops):
    """多跳展开：从 start 出发 BFS，逐跳打印可达实体（对标 HippoRAG 的 multi-hop 检索）。"""
    seen = {start}
    frontier = [start]
    for depth in range(1, hops + 1):
        nxt = []
        lines = []
        for src in frontier:
            e = graph["entities"].get(src)
            if not e:
                continue
            for r in e["relations"]:
                tgt = r["to"]
                if tgt in seen or tgt not in graph["entities"]:
                    continue
                seen.add(tgt)
                nxt.append(tgt)
                te = graph["entities"][tgt]
                dead = "（已弃用）" if te.get("status") == "retired" else ""
                note = f" — {r['note']}" if r.get("note") else ""
                lines.append(f"   {src} --{r['type']}--> {tgt}{dead}{note}")
            # 反向边也算一跳（关系网的完整可达性）
            for other, oe in graph["entities"].items():
                if other in seen:
                    continue
                for r in oe["relations"]:
                    if r["to"] == src:
                        seen.add(other)
                        nxt.append(other)
                        dead = "（已弃用）" if oe.get("status") == "retired" else ""
                        lines.append(f"   {other} --{r['type']}--> {src}{dead}")
                        break
        if lines:
            print(f"   🔗 第 {depth} 跳（{len(lines)} 条）:")
            for ln in lines[:20]:
                print(ln)
            if len(lines) > 20:
                print(f"   … 另有 {len(lines)-20} 条")
        else:
            print(f"   🔗 第 {depth} 跳: 无新实体")
            break
        frontier = nxt
        if not frontier:
            break


def query_entity(graph, name, hops=1):
    eid = _resolve(graph, name)
    if not eid:
        print(f"❌ 未找到实体: {norm_name(name)}")
        return
    e = graph["entities"][eid]
    flag = "   ⛔ 已弃用" if e.get("status") == "retired" else ""
    print(f"📌 {e['name']}（{TYPES.get(e['type'], e['type'])}）{flag}")
    print(f"   别名: {', '.join(e['aliases']) or '无'} | 首次出现: 第{e['first_seen']}处 | 状态: {e['status']}")
    if e.get("retired_reason"):
        print(f"   弃用原因: {e['retired_reason']}（第{e.get('retired_ch', 0)}处）")
    if e["tags"]:
        print(f"   属性: {json.dumps(e['tags'], ensure_ascii=False)}")
    print("   关系:")
    for r in e["relations"]:
        note = f"（{r['note']}）" if r.get("note") else ""
        dead = "  ⛔" if graph["entities"].get(r["to"], {}).get("status") == "retired" else ""
        print(f"     - {r['type']} → {r['to']}{dead}{note}")
    # 反向关系
    rev = [(k, v) for k, v in graph["entities"].items() if any(r["to"] == eid for r in v["relations"])]
    for k, v in rev[:10]:
        for r in v["relations"]:
            if r["to"] == eid:
                print(f"     - {k} {r['type']} 了 TA")
    # 相关事件
    evs = [t for t in graph["timeline"] if eid in t.get("entities", [])]
    if evs:
        print(f"   相关事件 ({len(evs)}):")
        for t in evs[-5:]:
            print(f"     [{t['time']}] {t['event'][:60]}")
    # 多跳展开
    if hops > 1:
        print(f"   ── 多跳展开（{hops} 跳）──")
        _print_hops(graph, eid, hops)


def retire_entity(graph, name, reason="", ch=0, revive=False):
    """弃用/恢复实体（对标 Cognee 的 forget()）。

    改稿后旧设定不能直接删（历史章节引用过），而是标记失效：
    一致性检查会跳过它，查询时明确标注，历史信息仍保留。
    """
    eid = _resolve(graph, name)
    if not eid:
        print(f"❌ 未找到实体: {norm_name(name)}")
        return False
    e = graph["entities"][eid]
    if revive:
        if e.get("status") != "retired":
            print(f"ℹ️ 「{eid}」本来就是 active，无需恢复")
            return False
        e["status"] = "active"
        e.pop("retired_reason", None)
        e.pop("retired_ch", None)
        print(f"♻️ 已恢复「{eid}」为 active")
    else:
        if e.get("status") == "retired":
            print(f"ℹ️ 「{eid}」已是 retired")
            return False
        e["status"] = "retired"
        if reason:
            e["retired_reason"] = reason
        if ch:
            e["retired_ch"] = ch
        print(f"⛔ 已弃用「{eid}」" + (f"：{reason}" if reason else "")
              + "（一致性检查将跳过；历史关系与事件保留）")
    return True


def show_timeline(graph, limit=30):
    if not graph["timeline"]:
        print("时间线为空")
        return
    for t in graph["timeline"][-limit:]:
        ents = ", ".join(t.get("entities", [])[:5]) or "-"
        print(f"[{t.get('time','?')}] (第{t.get('ch',0)}处) {t['event'][:70]}")

def show_status(graph):
    ents = graph["entities"]
    by_type = {}
    for e in ents.values():
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    print(f"📊 图谱统计")
    print(f"   文档摄入: {graph['meta']['docs']} 处")
    print(f"   实体: {len(ents)} ({', '.join(f'{TYPES.get(k,k)}×{v}' for k,v in by_type.items())})")
    print(f"   关系: {sum(len(e['relations']) for e in ents.values())} 条")
    print(f"   事件: {len(graph['timeline'])} 条")
    print(f"   因果链: {len(graph['causal'])} 条")
    print(f"   概念: {len(graph['semantic'])} 个")
    retired = [k for k, e in ents.items() if e.get("status") == "retired"]
    if retired:
        print(f"   ⛔ 已弃用: {len(retired)} 个（{', '.join(retired[:8])}{'...' if len(retired) > 8 else ''}）")
    print(f"\n   实体列表: {', '.join(sorted(ents.keys())[:25])}{'...' if len(ents)>25 else ''}")

def check_consistency(graph):
    issues = []
    # 1. 时间倒挂（事件时间排序异常——简单检测）
    times = [t for t in graph["timeline"] if t["time"] not in ("未知", "")]
    for i in range(1, len(times)):
        t1, t2 = times[i-1]["time"], times[i]["time"]
        # 只检测纯数字/日期格式
        m1, m2 = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", t1), re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", t2)
        if m1 and m2 and m1.group(1) > m2.group(1):
            issues.append(f"⚠️ 时间倒挂: [{m1.group(1)}] {times[i-1]['event'][:40]} → [{m2.group(1)}] {times[i]['event'][:40]}")
    # 2. 未回收线索（causal 中的 from 没有对应 to）
    causal_to = set(c["to"] for c in graph["causal"])
    for c in graph["causal"]:
        if c["from"] not in causal_to:
            issues.append(f"🧵 线索未回收: 「{c['from'][:40]}」没有后续结果")
    # 3. 同名冲突（实体别名冲突——简化：不同实体同名）
    names = {}
    for eid, e in graph["entities"].items():
        if e.get("status") == "retired":      # 已弃用实体不参与冲突判定
            continue
        for a in e.get("aliases", []):
            if a in names and names[a] != eid:
                issues.append(f"⚠️ 别名冲突: 「{a}」同时指向 {names[a]} 和 {eid}")
            names[a] = eid
    # 4. 已弃用实体仍被引用（改稿后遗留——提醒确认是否要一并处理）
    for eid, e in graph["entities"].items():
        if e.get("status") == "retired":
            users = [k for k, v in graph["entities"].items()
                     if k != eid and v.get("status") != "retired"
                     and any(r["to"] == eid for r in v["relations"])]
            if users:
                issues.append(f"⛔ 已弃用实体「{eid}」仍被引用: {', '.join(users[:5])}"
                              f"{'...' if len(users) > 5 else ''}（确认是否需改稿或恢复）")
    if not issues:
        print("✅ 一致性检查通过，未发现问题")
    else:
        for i in issues:
            print(i)
    return issues

# ═══════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="长文记忆图谱（MAGMA 四图通用版）")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="初始化项目图谱")
    p_init.add_argument("--name", required=True)
    p_init.add_argument("--dir", default="./memory_graph_data")

    p_ing = sub.add_parser("ingest", help="摄入文本")
    p_ing.add_argument("file")
    p_ing.add_argument("--dir", default="./memory_graph_data")
    p_ing.add_argument("--ch", type=int, default=0, help="来源章节/文档编号")
    p_ing.add_argument("--entities", help="无 LLM key 时手动指定实体（逗号分隔）")
    p_ing.add_argument("--no-llm", action="store_true", help="禁用 LLM 提取（规则模式）")

    p_q = sub.add_parser("query", help="查询实体")
    p_q.add_argument("name")
    p_q.add_argument("--dir", default="./memory_graph_data")
    p_q.add_argument("--hops", type=int, default=1,
                     help="多跳展开层数（2=看朋友的朋友，对标多跳检索）")

    p_ret = sub.add_parser("retire", help="弃用实体（改稿后旧设定，不删除只标记失效）")
    p_ret.add_argument("name")
    p_ret.add_argument("--reason", default="", help="弃用原因（强烈建议填写）")
    p_ret.add_argument("--ch", type=int, default=0, help="从哪一处/章开始弃用")
    p_ret.add_argument("--dir", default="./memory_graph_data")

    p_rev = sub.add_parser("revive", help="恢复被弃用的实体")
    p_rev.add_argument("name")
    p_rev.add_argument("--dir", default="./memory_graph_data")

    p_tl = sub.add_parser("timeline", help="事件时间线")
    p_tl.add_argument("--dir", default="./memory_graph_data")

    p_st = sub.add_parser("status", help="图谱统计")
    p_st.add_argument("--dir", default="./memory_graph_data")

    p_ck = sub.add_parser("check", help="一致性检查")
    p_ck.add_argument("--dir", default="./memory_graph_data")

    p_ex = sub.add_parser("export", help="导出全量 JSON")
    p_ex.add_argument("--dir", default="./memory_graph_data")
    p_ex.add_argument("-o", "--output", default="memory_graph_export.json")

    args = p.parse_args()

    if args.cmd == "init":
        graph = json.loads(json.dumps(STRUCT))
        graph["meta"] = {"name": args.name, "created": datetime.date.today().isoformat(), "docs": 0}
        save_graph(args.dir, graph)
        print(f"✅ 已初始化图谱「{args.name}」→ {args.dir}/memory_graph.json")
        return

    graph = load_graph(args.dir)

    if args.cmd == "ingest":
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
        manual = [s.strip() for s in (args.entities or "").split(",") if s.strip()]
        use_llm = not args.no_llm
        added = ingest(graph, text, args.ch, manual, use_llm)
        save_graph(args.dir, graph)
        print(f"✅ 已摄入「{os.path.basename(args.file)}」→ 新增实体{added['entities']} 关系{added['relations']} 事件{added['events']} 因果{added['causal']} 概念{added['concepts']}")
    elif args.cmd == "query":
        query_entity(graph, args.name, hops=max(1, args.hops))
    elif args.cmd == "retire":
        if retire_entity(graph, args.name, reason=args.reason, ch=args.ch):
            save_graph(args.dir, graph)
    elif args.cmd == "revive":
        if retire_entity(graph, args.name, revive=True):
            save_graph(args.dir, graph)
    elif args.cmd == "timeline":
        show_timeline(graph)
    elif args.cmd == "status":
        show_status(graph)
    elif args.cmd == "check":
        check_consistency(graph)
    elif args.cmd == "export":
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
        print(f"✅ 已导出: {args.output}")

if __name__ == "__main__":
    main()
