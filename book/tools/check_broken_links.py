#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_broken_links.py —— 文档里提到的仓内路径是不是真的存在。

口径以 **HEAD** 为准（`git ls-files`）：工作树里有而 HEAD 没有的，
公开后读者同样拿不到——那不是断链，是"还没入库"，但也得说出来。

分七类，**只有第一类判失败**：
  ① 真断链        —— HEAD 与工作树都没有 ⟹ 读者点不开 ⟹ 必须清偿
  ② 仅工作树有    —— 生成物或未入库；公开后拿不到，要补入库或补指针
  ③ 仓外原件      —— 按设计不在仓内（数据/快照），登记在册的不算断链
  ④ 相对路径      —— 相对**所在文件目录**解析，命中即算通
  ⑤ 记录性引用    —— 校验报告里的历史 path/file 字段（记录当时的事实）
  ⑥ 反例引用      —— 行内明说该路径不存在（教材式举反例）
  ⑦ 不入库区      —— .gitignore 声明的目录（如 `data/raw/`）
  ⑧ 外部项目引用  —— **关于别的项目**的校验报告里提到的那个项目的文件
                    （`docs/AUDIT-*.md` 记的是 mcopilot / GLM 会话产物，
                      它们从来就不该出现在本仓；这与"本仓的链接坏了"是两件事）

**为什么反例与记录性要单列**：它们长得跟断链一模一样。若不分开，
这门禁会天天报假警，几周之后没人再看它的输出——**一个天天误报的门禁，
等于没有门禁**。这跟"一个只说好话的门禁"是同一种病的两面。
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass

BOOK = Path(__file__).resolve().parents[1]
REPO = BOOK.parent

TOP = (r"(?:docs|scripts|src|tests|data|bench|synth|examples|knowledge|book|tools|"
       r"\.github)")
EXT = r"(?:jsonl|json|yaml|yml|html|toml|ipynb|md|csv|py|ps1|js|ts|exe|dll|txt|ini|log)"
# 前置不许是词字符、斜杠**或连字符**：连字符前的是"仓名"的一部分
# （forensics-learning-book/decision-lists/... 指向的是另一个仓，不是本仓的路径）
PATH = re.compile(r"((?<![\w/-])" + TOP + r"/[A-Za-z0-9_\-./{}*]*\." + EXT + r"(?::[\d,\-]+)?)")
LINESUF = re.compile(r":[\d,\-]+$")


def git(*args) -> str:
    p = subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip()


def expand_braces(p: str) -> list[str]:
    m = re.search(r"\{([^{}]*)\}", p)
    if not m:
        return [p]
    out = []
    for opt in m.group(1).split(","):
        out += expand_braces(p[:m.start()] + opt.strip() + p[m.end():])
    return out


def norm(raw: str) -> list[str]:
    cands = []
    for one in expand_braces(raw):
        one = LINESUF.sub("", one).strip().replace("\\", "/")
        if not one or "*" in one or "<" in one or ">" in one or one.endswith("/"):
            continue
        cands.append(one)
    return cands


def ignored_prefixes() -> set[str]:
    out = set()
    gi = REPO / ".gitignore"
    if gi.is_file():
        for ln in io.open(gi, encoding="utf-8", errors="replace"):
            ln = ln.strip()
            if not ln or ln.startswith("#") or ln.startswith("!"):
                continue
            ln = ln.split("#")[0].strip().rstrip("/")
            if not ln:
                continue
            if "*" in ln or "?" in ln:
                ln = ln.split("*")[0].split("?")[0]
            ln = ln.rstrip("/")
            if not ln:
                continue
            out.add(ln + "/" if "/" not in ln else ln)
    return out


COUNTER = re.compile(
    r"不存在|一个都|从未|未进|未入库|不入库|缺失|不在仓|没有.*(?:进|在)仓|已被清|清理|删除|已删|"
    r"拆成|取代|不再|过期|草稿|曾引用|实际落盘路径|复算脚本未入库|本地.*产物.*不入库|"
    r"更名为|已更名|改名|原名|曾名|旧名|原为|落点|不落盘|未落盘")

# ⑧ 外部项目引用：`docs/AUDIT-*.md` 是**关于别的项目**的校验报告。
#    判据两条，都必须成立才算"引用他项目"：
#      (a) 路径的首段目录在本仓根本不存在（`knowledge/` 之类）；或
#      (b) 文件名里带着被审计项目的名字（`test_mcopilot.py`）。
#    只放宽到这两条，不做整文件豁免——整文件豁免会把报告里真正的本仓笔误
#    一起放过，那才是"一个不报警的门禁"。
EXTERNAL_REPORT = re.compile(r"^docs/AUDIT-")
OTHER_PROJECT = re.compile(r"mcopilot|glm|minimax", re.IGNORECASE)


def main() -> int:
    heads = {f for f in git("ls-files", "-z").split("\0") if f}
    worktree = set()
    for dp, dns, fns in os.walk(str(REPO)):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__", ".pytest_cache")]
        for fn in fns:
            worktree.add(os.path.relpath(os.path.join(dp, fn), str(REPO)).replace("\\", "/"))
    ignored = ignored_prefixes()

    true_gaps, only_wt, rel_ok, record, counter_ex, ignored_hits = [], [], [], [], [], []
    external_refs = []
    top_dirs = {f.split("/")[0] for f in heads if "/" in f} | {f for f in heads if "." not in f}
    docs = sorted(f for f in heads if f.lower().endswith((".md", ".json")) and not f.startswith("data/raw/"))
    for rel in docs:
        p = REPO / rel.replace("/", os.sep)
        if not p.is_file():
            continue
        try:
            text = io.open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            ctx = line + ("\n" + lines[i] if i < len(lines) else "")
            for m in PATH.finditer(line):
                for ref in norm(m.group(1)):
                    if ref in heads:
                        continue
                    rel_dir = os.path.dirname(rel)
                    if rel_dir:
                        cand = (rel_dir + "/" + ref).replace("//", "/")
                        if cand in heads or cand in worktree:
                            rel_ok.append((rel, i, ref))
                            continue
                    if re.search(r'"(?:path|file|raw_file|original)"\s*:\s*"' + re.escape(ref) + r'"', line):
                        record.append((rel, i, ref))
                        continue
                    if any(ref.startswith(pfx) for pfx in ignored):
                        ignored_hits.append((rel, i, ref))
                        continue
                    if ref in worktree:
                        only_wt.append((rel, i, ref))
                        continue
                    if COUNTER.search(ctx):
                        counter_ex.append((rel, i, ref))
                        continue
                    # ⑧ 外部项目引用：报告里提到的**他项目**的文件
                    if EXTERNAL_REPORT.match(rel):
                        head = ref.split("/")[0]
                        if head not in top_dirs or OTHER_PROJECT.search(ref.split("/")[-1]):
                            external_refs.append((rel, i, ref))
                            continue
                    true_gaps.append((rel, i, ref))

    print("=" * 92)
    print("【一】真断链（HEAD 与工作树都没有）——必须清偿")
    print("=" * 92)
    for rel, i, ref in true_gaps:
        print(f"  ✗ {rel}:{i}  →  {ref}")
    print(f"  小计：{len(true_gaps)} 处")

    print("\n" + "=" * 92)
    print("【二】仅工作树有（生成物 / 未入库）——公开后读者拿不到")
    print("=" * 92)
    for rel, i, ref in only_wt[:40]:
        print(f"  · {rel}:{i}  →  {ref}")
    print(f"  小计：{len(only_wt)} 处")

    print("\n" + "=" * 92)
    print("【三】相对路径（相对所在目录解析，命中）——不算断链")
    print("=" * 92)
    print(f"  小计：{len(rel_ok)} 处")

    print("\n" + "=" * 92)
    print("【四】记录性引用（历史 path 字段）——不算断链")
    print("=" * 92)
    print(f"  小计：{len(record)} 处")

    print("\n" + "=" * 92)
    print("【五】反例引用（行内明说不存在）——不算断链，供人工确认")
    print("=" * 92)
    for rel, i, ref in counter_ex[:40]:
        print(f"  ○ {rel}:{i}  →  {ref}")
    print(f"  小计：{len(counter_ex)} 处")

    print("\n" + "=" * 92)
    print("【六】不入库区路径（.gitignore 声明）——不是断链")
    print("=" * 92)
    print(f"  小计：{len(ignored_hits)} 处")

    print("\n" + "=" * 92)
    print("【七】外部项目引用（校验报告提到他项目的文件）——不是断链")
    print("=" * 92)
    for rel, i, ref in external_refs[:40]:
        print(f"  ○ {rel}:{i}  →  {ref}")
    print(f"  小计：{len(external_refs)} 处")

    print(f"\n真断链 {len(true_gaps)} ｜ 仅工作树 {len(only_wt)} ｜ 相对路径 {len(rel_ok)} "
          f"｜ 记录性 {len(record)} ｜ 反例 {len(counter_ex)} ｜ 不入库区 {len(ignored_hits)}"
          f" ｜ 外部项目 {len(external_refs)}")
    return 1 if true_gaps else 0


if __name__ == "__main__":
    sys.exit(main())
