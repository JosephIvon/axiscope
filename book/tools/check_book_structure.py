#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_book_structure.py —— 本卷结构体检。

逐章检查必备件：
  标题 / **本章承接**（须在章首 12 行内）/ **学完你会** / **前置** / 素材坐标 / 已验算 /
  证据与坐标区 / 可验证主张 / 讲师切分 / 习题 / 尾注坐标
检查导读页：标题 / 写给读者的建议 / 章速查表 / 证据与坐标区指引。
检查书级前后言：标题 / 主张块 / 尾注坐标。
并扫描违禁项：会话坐标、裸行号坐标。

**外加一条跨文件核对**：正文里写的锚点字符串（`axiscope@<commit>`）
必须与 `tools/_anchor.py` 里的 `ANCHOR_LABEL` **逐字一致**。
  为什么：书里说的锚与工具实际读的锚若是两个，坐标审计照样全绿——
  那就是"0 失败"变成假话的形状。锚点只该有一处定义，另一处必须被核对。
"""
from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _anchor import ANCHOR_COMMIT, ANCHOR_LABEL, VOLUME_NAME  # noqa: E402

BOOK = Path(__file__).resolve().parents[1]
SRC = BOOK / "chapters"
WANT_CHAPTERS = 9
BAD_PATTERNS = [
    # 「不设会话坐标」是正文里的否定用法，不是违禁项 → 一并排除
    (re.compile(r"(?<![禁不无])(?<!不设)会话坐标|本轮对话|上文提到|前面说过"), "会话坐标"),
    (re.compile(r"（`:\d+"), "裸行号坐标"),
]

bad = 0

guide = SRC / "00-导读.md"
files = sorted(x for x in os.listdir(SRC) if x.endswith(".md") and x != "00-导读.md")
print(f"[章节] 章数 {len(files)} / 预期 {WANT_CHAPTERS}", "OK" if len(files) == WANT_CHAPTERS else "❌")
if len(files) != WANT_CHAPTERS:
    bad += 1

if guide.is_file():
    g = io.open(guide, encoding="utf-8").read()
    gneed = {
        "标题": g.startswith("# "),
        "读者建议": "写给读者的建议" in g,
        "章速查": "速查" in g,
        "证据区指引": "证据与坐标" in g,
    }
    gmiss = [k for k, v in gneed.items() if not v]
    ghits = [lbl for pat, lbl in BAD_PATTERNS if pat.search(g)]
    if gmiss or ghits:
        bad += 1
        print(f"  ❌ 00-导读.md：缺 {gmiss or '无'}{' ｜ ' + ', '.join(ghits) if ghits else ''}")
    else:
        print(f"  ✅ 00-导读.md（{len(g.splitlines())} 行）")
else:
    bad += 1
    print("  ❌ 00-导读.md：不存在")

for fn in files:
    text = io.open(SRC / fn, encoding="utf-8").read()
    lines = text.splitlines()
    head = "\n".join(lines[:12])
    need = {
        "标题": text.startswith("# "),
        "承接段": "**本章承接**" in head,
        "学完你会": "**学完你会**" in head,
        "前置": "**前置**" in head,
        "素材坐标": "**素材坐标**" in text,
        "已验算": "**已验算**" in text,
        "证据与坐标区": "## 证据与坐标" in text,
        "可验证主张": "可验证主张" in text,
        "讲师切分": ("**讲师 90 分钟**" in text) or ("讲师切分" in text),
        "尾注坐标": "事实性句子坐标" in text,
        "习题": "习题" in text,
    }
    miss = [k for k, v in need.items() if not v]
    hits = []
    for pat, label in BAD_PATTERNS:
        for m in pat.finditer(text):
            hits.append(f"{label}@L{text[:m.start()].count(chr(10)) + 1}")
    if miss:
        bad += 1
        print(f"  ❌ {fn}：缺 {miss}")
    elif hits:
        bad += 1
        print(f"  ❌ {fn}：{' ｜ '.join(hits)}")
    else:
        print(f"  ✅ {fn}（{len(lines)} 行）")

# ---- 书级前后言体检 ----
for fn in ("前言.md", "尾声.md"):
    path = BOOK / fn
    if not path.is_file():
        print(f"  ❌ {fn}：文件不存在")
        bad += 1
        continue
    text = io.open(path, encoding="utf-8").read()
    need = {
        "标题": text.startswith("# "),
        "主张块": "> **" in text,
        "尾注坐标": "事实性句子坐标" in text,
    }
    miss = [k for k, v in need.items() if not v]
    hits = []
    for pat, label in BAD_PATTERNS:
        for m in pat.finditer(text):
            hits.append(f"{label}@L{text[:m.start()].count(chr(10)) + 1}")
    if miss or hits:
        bad += 1
        print(f"  ❌ {fn}：缺 {miss or '无'}{' ｜ ' + ', '.join(hits) if hits else ''}")
    else:
        print(f"  ✅ {fn}（{len(text.splitlines())} 行）")

# ---- 锚点跨文件核对：正文里写的锚点字符串必须与 _anchor.py 一致 ----
all_book = []
for base in (SRC,):
    for fn in sorted(os.listdir(base)):
        if fn.endswith(".md"):
            all_book.append((fn, io.open(base / fn, encoding="utf-8").read()))
for fn in ("前言.md", "尾声.md", "ASSETS.md", "OUTLINE.md"):
    p = BOOK / fn
    if p.is_file():
        all_book.append((fn, io.open(p, encoding="utf-8").read()))

declared = set()
for fn, text in all_book:
    for m in re.finditer(r"axiscope@([0-9a-f]{6,40})", text):
        declared.add((fn, m.group(1)))
wrong = [(fn, h) for fn, h in declared if h != ANCHOR_COMMIT]
if wrong:
    bad += 1
    print(f"  ❌ 锚点字符串与 tools/_anchor.py 不一致（_anchor.py = {ANCHOR_COMMIT}）：")
    for fn, h in sorted(set(wrong)):
        print(f"      {fn}: axiscope@{h}")
else:
    print(f"  ✅ 锚点字符串一致（全书 {len(declared)} 处，均为 axiscope@{ANCHOR_COMMIT}）")

# ---- 卷名核对：本书自称的名字必须是本册的 ----
_readme = BOOK / "README.md"
if _readme.is_file():
    _rt = io.open(_readme, encoding="utf-8").read()
    if VOLUME_NAME in _rt:
        print(f"  ✅ 卷名与 tools/_anchor.py 一致：{VOLUME_NAME}")
    else:
        bad += 1
        _seen = re.findall(r"《[^》]+卷》", _rt)
        print(f"  ❌ README 里没有本册的正式名 {VOLUME_NAME}；出现了 {sorted(set(_seen)) or '无卷名'}")

print("问题章数：", bad)
sys.exit(1 if bad else 0)
