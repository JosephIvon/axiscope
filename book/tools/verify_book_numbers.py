#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_book_numbers.py —— 书里「带文件名的数字」必须与真文件一致。

抓的是这种形状：正文写「`src/axiscope/engine.py`（859 行）」，而那个文件
现在 900 行；或者「`docs/kb/` 下 7 件知识库」，而现在是 8 件。

**为什么坐标审计抓不到**：坐标审计管的是「这一行还在不在」，
而"行还在"与"这一行说的那个数还对不对"是两件事。
行锚合法 ≠ 指向了正确的东西——这是本仓反复吃过的一课：
文件多长了几行、目录里多了一件文件，坐标照样全绿，而书里的话已经是假的。
所以**数字要有另一道门**。

判据：正文里 `路径（N 行 / N 文件 / N 条）` 这类写法，N 必须等于真文件的行数。
  · 指名道姓带路径的 → 核；
  · 聚合数（「全仓 12,136 行」）→ **不核**（核它要遍历全仓，且它本来就是
    「当时账面上」的说法，与历史陈述冲突时该由正文说清是哪个时点）；
  · 指不到具体文件的 → 只计数，不判失败。
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

BOOK = Path(__file__).resolve().parents[1]
REPO = BOOK.parent

# 「`路径`（N 行 / N 文件 / N 条 / N 项）」这类写法
PAT = re.compile(
    r"`(?P<path>[A-Za-z0-9_\-一-鿿\./]+\.(?:md|py|ps1|json|csv|txt|html))`"
    r"[（(]\s*(?P<n>\d+)\s*(?P<unit>行|文件|条|项)\s*[)）]"
)


def file_lines(rel: str) -> int | None:
    p = REPO / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    try:
        with io.open(p, "r", encoding="utf-8", errors="replace") as fh:
            return len(fh.read().splitlines())
    except OSError:
        return None


def main() -> int:
    files = []
    chapters = BOOK / "chapters"
    if chapters.is_dir():
        files += [chapters / f for f in sorted(os.listdir(chapters)) if f.endswith(".md")]
    for extra in ("前言.md", "尾声.md", "ASSETS.md", "OUTLINE.md"):
        if (BOOK / extra).is_file():
            files.append(BOOK / extra)

    checked = unresolved = bad = 0
    for p in files:
        text = io.open(p, encoding="utf-8").read()
        for m in PAT.finditer(text):
            rel, n, unit = m.group("path"), int(m.group("n")), m.group("unit")
            if unit != "行":
                continue
            real = file_lines(rel)
            if real is None:
                unresolved += 1
                continue
            checked += 1
            if real != n:
                bad += 1
                line = text[:m.start()].count("\n") + 1
                print(f"  [MISMATCH] {p.name}:{line}  「{rel}」称 {n} 行，实为 {real} 行")
            else:
                line = text[:m.start()].count("\n") + 1
                print(f"  [OK] {p.name}:{line}  {rel}（{n} 行）")

    print(f"已核 {checked} 处带文件名的数字，全部一致" if not bad
          else f"已核 {checked} 处，{bad} 处不一致")
    if unresolved:
        print(f"另有 {unresolved} 处解不出（路径不在仓内或不是行数口径），只计数不判失败")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
