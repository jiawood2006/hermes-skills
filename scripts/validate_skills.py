#!/usr/bin/env python3
"""校验仓库内所有 SKILL.md 的 frontmatter 是否合规。

用法:
    python3 scripts/validate_skills.py            # 校验 skills/ 下全部技能
    python3 scripts/validate_skills.py --quiet    # 只输出结果一行

规则:
  1. 每个 skills/<name>/SKILL.md 必须存在
  2. frontmatter 必须能被 YAML 解析，且以 --- 包裹
  3. name 必须存在、全小写、与目录名一致
  4. description 必须存在且 >= 20 字符
  5. 提到的引用文件（references/、scripts/、assets/ 下的路径）必须真实存在
"""
import os, re, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, "skills")
OK, FAIL = "\033[92m✓\033[0m", "\033[91m✗\033[0m"

try:
    import yaml
except ImportError:
    print("需要 pyyaml: pip install pyyaml")
    sys.exit(2)


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except Exception:
        return "YAML_PARSE_ERROR"


def check_skill(skill_dir, name):
    errors, warnings = [], []
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return [f"{name}: 缺少 SKILL.md"], []

    text = open(path, encoding="utf-8").read()
    fm = parse_frontmatter(text)
    if fm is None:
        errors.append(f"{name}: 缺少 frontmatter（--- 包裹的 YAML）")
        return errors, warnings
    if fm == "YAML_PARSE_ERROR":
        errors.append(f"{name}: frontmatter YAML 解析失败")
        return errors, warnings

    nm = fm.get("name")
    if not nm:
        errors.append(f"{name}: frontmatter 缺少 name")
    elif nm != name:
        errors.append(f"{name}: name='{nm}' 与目录名不一致")
    elif not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", nm):
        errors.append(f"{name}: name 格式不合规（须小写字母/数字/连字符）")

    desc = fm.get("description")
    if not desc:
        errors.append(f"{name}: frontmatter 缺少 description")
    elif len(str(desc).strip()) < 20:
        errors.append(f"{name}: description 过短（<20 字符），Agent 无法判断触发时机")

    # 检查正文提到的相对资源路径是否存在
    for rel in set(re.findall(r"`((?:references|scripts|assets|templates)/[\w./\-]+)`", text)):
        if not os.path.exists(os.path.join(skill_dir, rel)):
            warnings.append(f"{name}: 正文引用了不存在的文件 '{rel}'")

    return errors, warnings


def main():
    quiet = "--quiet" in sys.argv
    if not os.path.isdir(SKILLS_DIR):
        print("找不到 skills/ 目录")
        sys.exit(1)

    names = sorted(
        d for d in os.listdir(SKILLS_DIR)
        if os.path.isdir(os.path.join(SKILLS_DIR, d)) and not d.startswith(".")
    )
    total_err, total_warn = [], []
    if not quiet:
        print(f"\n校验 {len(names)} 个技能 / Validating {len(names)} skills\n" + "-" * 56)

    for n in names:
        errs, warns = check_skill(os.path.join(SKILLS_DIR, n), n)
        total_err += errs
        total_warn += warns
        if not quiet:
            if errs:
                print(f"{FAIL} {n}")
                for e in errs:
                    print(f"    - {e}")
            else:
                note = f"  ({len(warns)} 条提示)" if warns else ""
                print(f"{OK} {n}{note}")
            for w in warns:
                print(f"    ⚠ {w}")

    status = "PASS" if not total_err else "FAIL"
    print("-" * 56)
    print(f"结果 / Result: {status}  |  错误 {len(total_err)}  |  提示 {len(total_warn)}")
    if total_err and quiet:
        for e in total_err:
            print("  -", e)
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
