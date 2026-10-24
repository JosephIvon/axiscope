#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_coords.py —— 本卷坐标审计：把每处「文件:行号」引用解析回源文件，
打印被引行的**真实内容**，供人工核对"挂的那一行是不是真说了那句话"。

判据（三档，全绿才算过）：
  · 引用可解析（文件找到 + 行号存在）→ [OK]，附被引行原文
  · 行号超出文件行数 → [MISSING-LINE]（行锚腐烂 / 指向未来行）→ **判失败**
  · 文件根本找不到 → [MISSING-FILE] → **判失败**
    （例外：登记在 `book/evidence/REGISTRY.json` 里的**仓外原件**——
     它们按设计不在仓内，指针 + size + sha256 留在仓里。这类**必须有登记**，
     没登记的"仓外原件"一律判失败：否则拼错一个文件名也会被放过，
     门禁就成了只会说"通过"的摆设。）

**按锚点读源文件**：源文件内容从**锚点 commit** 取（`git show`），不在工作树取。
  锚点冻结 = 坐标含义冻结。工作树里改了行号，坐标不动；
  锚点往后挪，正文里的锚点字符串与本工具的 ANCHOR_COMMIT 一起改（见 `_anchor.py`）。

**书是活物，读工作树；只有代码读锚点。**
  `book/` 落在锚点根下面，若也按锚点读，书里对 `book/evidence/` 的引用
  会被拿上一次提交的文字去核——核的是旧行号、报的是假结果。

**行锚断言（可选但推荐）**：`book/checks.json` 里可以给关键坐标登记
"这一行必须含有哪几个词"。登记了就**当硬门**：那一行不含登记词 → 判失败。
  理由：「行还在」不等于「行在说那句话」。只验行号存在的那种审计，
  能挡住行锚腐烂，挡不住**指错行**——而指错行恰好是更常见也更危险的那一种。
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# 控制台编码不是 UTF-8 时 print 会抛 UnicodeEncodeError —— 脚本崩在打印上，
# 而不是给出判定。GitHub Actions runner 的控制台是 cp1252，本机是 UTF-8：
# 于是本机绿、runner 红。所以 stdout 一律按 UTF-8 走。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _anchor import ANCHOR_COMMIT, ANCHOR_LABEL  # noqa: E402

BOOK_DIR = Path(__file__).resolve().parents[1]          # <repo>/book
REPO_ROOT = BOOK_DIR.parent                             # <repo>

# 短名 → 相对路径（书里允许写 `KB0:80` 这种简写）
ALIAS = {
    "KB0": ["docs/kb/KB0-conventions.md"],
    "KB2": ["docs/kb/KB2-waveform-formats.md"],
    "KB3": ["docs/kb/KB3-tuning-rules.md"],
    "KB4": ["docs/kb/KB4-attribution-model.md"],
    "KB5": ["docs/kb/KB5-simulation-plant.md"],
    "KB6": ["docs/kb/KB6-coupling-and-calibration.md"],
    "KB7": ["docs/kb/KB7-dataset-da-rus-cat.md"],
    "KB8": ["docs/kb/KB8-benchmark-cases.md"],
    "C1": ["docs/contracts/C1-canonical-waveform.md"],
    "C2": ["docs/contracts/C2-features.md"],
    "C3": ["docs/contracts/C3-diagnosis.md"],
    "C4": ["docs/contracts/C4-validation.md"],
    "C5": ["docs/contracts/C5-evaluation-protocol.md"],
    "C6": ["docs/contracts/C6-machine-context.md"],
    "C7": ["docs/contracts/C7-process-context.md"],
    "README": ["README.md"],
    "NOTICE": ["NOTICE.md"],
    "LICENSE": ["LICENSE"],
    "DECISION": ["docs/DECISION-2026-10-19-方向裁决.md"],
    "回顾": ["docs/项目回顾与收尾_20261022.md"],
}

CITE = re.compile(
    r"(?P<file>[A-Za-z0-9_\-一-鿿\./]+\.(?:md|py|ps1|json|jsonl|csv|txt|html|exe))"
    r"[:：](?P<line>\d+)(?:[-–](?P<line2>\d+))?"
)
ALIAS_CITE = re.compile(
    r"(?<![A-Za-z0-9_\-/\.])(?:KB(?P<kn>\d)|C(?P<cn>[1-7]))[:：](?P<line>\d+)"
    r"(?:[-–](?P<line2>\d+))?"
)

_cache: dict[str, list[str] | None] = {}


# ---------------------------------------------------------------- 锚点读

def _git_show(rel: str) -> list[str] | None:
    """从锚点 commit 读仓内文件内容；不在锚点里 → None。"""
    r = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{ANCHOR_COMMIT}:{rel}"],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace").splitlines()


def load(abs_path: str) -> list[str] | None:
    """取文件内容：**代码读锚点，书读工作树**。"""
    if abs_path in _cache:
        return _cache[abs_path]
    ap = os.path.abspath(abs_path)
    book_abs = os.path.abspath(str(BOOK_DIR))
    if ap.startswith(book_abs + os.sep):
        try:
            with io.open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                _cache[abs_path] = fh.read().splitlines()
        except OSError:
            _cache[abs_path] = None
        return _cache[abs_path]
    try:
        rel = os.path.relpath(abs_path, str(REPO_ROOT)).replace(os.sep, "/")
    except ValueError:
        rel = ""
    anchored = _git_show(rel) if rel else None
    if anchored is not None:
        _cache[abs_path] = anchored
        return anchored
    try:
        with io.open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            _cache[abs_path] = fh.read().splitlines()
    except OSError:
        _cache[abs_path] = None
    return _cache[abs_path]


# ---------------------------------------------------------------- 解析

def resolve(rel: str) -> tuple[str | None, list[str] | None]:
    """把书里写的路径解析成仓内绝对路径 + 内容。找不到返回 (None, None)。"""
    rel = rel.replace("/", os.sep)
    cands = [os.path.join(str(REPO_ROOT), rel)]
    if os.sep not in rel:
        # 只给文件名时按 basename 全仓找
        for dirpath, dirs, files in os.walk(str(REPO_ROOT)):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
            if os.path.basename(rel) in files:
                cands.append(os.path.join(dirpath, os.path.basename(rel)))
    for c in cands:
        if os.path.isfile(c):
            lines = load(c)
            if lines is not None:
                return c, lines
    return None, None


def registered_external(rel: str) -> bool:
    """仓外原件登记表里有的路径 → 允许"不在仓内"。"""
    reg = BOOK_DIR / "evidence" / "REGISTRY.json"
    if not reg.is_file():
        return False
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    tail = rel.replace("\\", "/")
    for item in data.get("externals", []):
        p = str(item.get("path", "")).replace("\\", "/")
        if not p:
            continue
        if tail == p or tail.endswith("/" + p) or p.endswith("/" + tail):
            return True
    return False


# ---------------------------------------------------------------- 行锚断言

def load_checks() -> dict:
    p = BOOK_DIR / "checks.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"  [CHECKS-UNREADABLE] {p}：{exc}")
        return {}


def check_keywords(coord: str, lines: list[str], ln: int, ln2: int, want) -> list[str]:
    """被引行必须含有登记词——否则"行还在"但"行没说那句话"，照样判失败。"""
    seg = " ".join(lines[i - 1] for i in range(ln, min(ln2, len(lines)) + 1)) if ln <= len(lines) else ""
    miss = [w for w in want if w not in seg]
    return miss


# ---------------------------------------------------------------- 主流程

def main() -> int:
    checks = load_checks()
    total = ok = bad = 0
    checked = 0
    per_file: dict[str, list] = defaultdict(list)
    files: list[str] = []
    chapters = BOOK_DIR / "chapters"
    if chapters.is_dir():
        files += [str(chapters / f) for f in sorted(os.listdir(chapters)) if f.endswith(".md")]
    for extra in ("前言.md", "尾声.md"):
        if (BOOK_DIR / extra).is_file():
            files.append(str(BOOK_DIR / extra))

    print("=" * 92)
    print(f"坐标审计：锚点 {ANCHOR_LABEL}（代码按锚点读，书读工作树）")
    print("=" * 92)

    for path in files:
        fn = os.path.basename(path)
        text = io.open(path, encoding="utf-8").read()
        cites: list[tuple[str, int, int, str]] = []
        for m in CITE.finditer(text):
            cites.append((m.group("file"), int(m.group("line")),
                          int(m.group("line2")) if m.group("line2") else int(m.group("line")),
                          "FILE"))
        for m in ALIAS_CITE.finditer(text):
            key = ("KB%s" % m.group("kn")) if m.group("kn") else ("C%s" % m.group("cn"))
            cites.append((key, int(m.group("line")),
                          int(m.group("line2")) if m.group("line2") else int(m.group("line")),
                          "ALIAS"))
        if not cites:
            continue
        print(f"\n—— {fn} ——")
        for raw, ln, ln2, kind in cites:
            total += 1
            if kind == "ALIAS":
                rel = None
                for cand in ALIAS.get(raw, []):
                    ap, lines = resolve(cand)
                    if lines is not None:
                        rel, lines = cand, lines
                        break
                if rel is None:
                    bad += 1
                    print(f"  [MISSING-FILE] {raw}:{ln}（别名未解析）")
                    continue
                abs_p = os.path.join(str(REPO_ROOT), rel.replace("/", os.sep))
                label = raw
            else:
                rel = raw
                abs_p, lines = resolve(raw)
                label = raw
                if lines is None:
                    if registered_external(raw):
                        print(f"  [EXTERNAL] {raw}:{ln}（仓外原件，已登记：指针+size+sha256 留在仓内）")
                        continue
                    bad += 1
                    print(f"  [MISSING-FILE] {raw}:{ln}（仓内找不到；未登记为仓外原件）")
                    continue
            if ln < 1 or ln > len(lines):
                bad += 1
                print(f"  [MISSING-LINE] {label}:{ln}（该文件共 {len(lines)} 行）")
                continue
            if ln2 > len(lines) or ln2 < ln:
                bad += 1
                print(f"  [MISSING-LINE] {label}:{ln}-{ln2}（该文件共 {len(lines)} 行）")
                continue
            ok += 1
            per_file[abs_p].append((fn, ln, ln2))
            seg = " ".join(lines[i - 1].strip() for i in range(ln, min(ln2, ln + 1) + 1))
            if len(seg) > 160:
                seg = seg[:160] + "…"
            # 行锚断言
            want = checks.get(f"{rel}:{ln}") or checks.get(f"{rel}:{ln}-{ln2}") \
                or checks.get(f"{label}:{ln}")
            if want:
                checked += 1
                miss = check_keywords(f"{rel}:{ln}", lines, ln, ln2, want)
                if miss:
                    bad += 1
                    print(f"  [WRONG-LINE] {label}:{ln} 行在，但不含登记词 {miss} → {seg}")
                    continue
            print(f"  [OK] {label}:{ln}{'-' + str(ln2) if ln2 != ln else ''} → {seg}")

    print()
    print("=" * 92)
    print(f"坐标审计合计：引用 {total} ｜ 可解析 {ok} ｜ 失败 {bad}"
          + (f" ｜ 行锚断言核对 {checked} 处" if checked else ""))
    print("=" * 92)
    multi = 0
    for abs_p, cites in per_file.items():
        byfile = defaultdict(set)
        for fn, a, b in cites:
            byfile[fn].add((a, b))
        if len(byfile) > 1:
            multi += 1
            print(f"[多章引用同一文件] {os.path.relpath(abs_p, str(REPO_ROOT))}")
            for fn, ls in byfile.items():
                print(f"    {fn}: {sorted(ls)}")
    if multi:
        print("  （同一文件被多章引用不同行号——人工确认是否有意为之）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
