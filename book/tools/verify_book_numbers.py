#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_book_numbers.py —— 书里的数字必须与实跑一致。

抓的是这种形状：正文写「`src/axiscope/engine.py`（859 行）」，而那个文件
现在 900 行；或者「`docs/kb/` 下 7 件知识库」，而现在是 8 件。

**为什么坐标审计抓不到**：坐标审计管的是「这一行还在不在」，
而"行还在"与"这一行说的那个数还对不对"是两件事。
行锚合法 ≠ 指向了正确的东西——这是本仓反复吃过的一课：
文件多长了几行、目录里多了一件文件，坐标照样全绿，而书里的话已经是假的。
所以**数字要有另一道门**。

本工具判三件事：

  ① **带文件名的行数**：正文里 `路径（N 行）` 这类写法，N 必须等于真文件的行数。
     · 指名道姓带路径的 → 核；
     · 聚合数（「全仓 12,136 行」）→ **不核**（核它要遍历全仓，且它本来就是
       「当时账面上」的说法，与历史陈述冲突时该由正文说清是哪个时点）；
     · 指不到具体文件的 → 只计数，不判失败。

  ② **本卷清单的行数**：`ASSETS.md` 的资产表里每件东西的「行」，
     以及「全卷合计：N 件 / M 行」——必须与 `book/` 目录的现状一致。
     理由同上：资产表会随编辑漂移，漂了就是一张**假清单**。
     （字节数不核——**写下一个数字会改变文件大小**，那是无法自洽的引用。）

  ③ **本卷自报的门禁数字**：书里写「引用 743 ｜ 可解析 743 ｜ 失败 0 ｜
     行锚断言核对 365」，这些数**必须等于当场实跑的结果**。
     理由：书里最容易被自己写旧的，恰恰是**关于它自己**的那几行——
     改一次正文，坐标数就变，而正文里那句"引用 743"没人会去核对。
     本项把「自己说的」和「实跑的」绑在一起。

判据：任一项不符 → exit 1。
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


# ---- ② 本卷清单：ASSETS.md 的资产表行数 + 全卷合计 ------------------------------

# 表格行：| `路径` | N | …… |   （路径相对 book/）
ROW_PAT = re.compile(r"^\|\s*`(?P<path>[^`]+)`\s*\|\s*(?P<n>\d+)\s*\|", re.M)
ASSET_ROW = re.compile(r"^\|\s*`(?P<path>[^`]+)`\s*\|\s*(?P<n>\d+)\s*\|", re.M)
# 合计行：全卷合计：N 件 / M 行
# 千位逗号必须算进字符类：合计写成 `6,625` 时，`[\d\s]+` 匹配不上，
# 于是「合计核对」整条**空转**——总行数写错了也照样绿（2026-10-24 真踩到）。
TOTAL_ROW = re.compile(r"全卷合计：\s*(?P<files>\d+)\s*件\s*/\s*(?P<lines>[\d,\s]+)\s*行")


def book_files() -> list[Path]:
    out = []
    for p in sorted(BOOK.rglob("*")):
        if p.is_dir() or p.name.startswith(".") or "__pycache__" in p.parts:
            continue
        if p.suffix.lower() in (".md", ".json", ".py"):
            out.append(p)
    return out


def check_assets(book_texts: dict[str, str]) -> tuple[int, int]:
    """核 ASSETS.md 里的资产表行数与全卷合计。返回 (核过几处, 不符几处)。"""
    checked = bad = 0
    assets = BOOK / "ASSETS.md"
    if not assets.is_file():
        return 0, 0
    text = book_texts.get("ASSETS.md", "")
    for m in ASSET_ROW.finditer(text):
        rel, n = m.group("path"), int(m.group("n"))
        p = BOOK / rel.replace("/", os.sep)
        if not p.is_file():
            continue
        real = file_lines(str(p.relative_to(REPO)).replace("\\", "/"))
        if real is None:
            continue
        checked += 1
        if real != n:
            bad += 1
            line = text[:m.start()].count("\n") + 1
            print(f"  [MISMATCH] ASSETS.md:{line}  清单称「{rel}」{n} 行，实为 {real} 行")
    if "全卷合计" in text and TOTAL_ROW.search(text) is None:
        print("  [FAIL] ASSETS.md 里有「全卷合计」但解析不出来——格式与正则脱节，"
              "这一项等于没核（不许静默跳过）")
        return 0, 1
    m = TOTAL_ROW.search(text)
    if m:
        files = book_files()
        real_files = len(files)
        real_lines = sum(len(p.read_text(encoding="utf-8", errors="replace").splitlines())
                         for p in files)
        want_files = int(m.group("files"))
        want_lines = int(m.group("lines").replace(",", "").replace(" ", "").replace("\u3000", ""))
        checked += 1
        if want_files != real_files or want_lines != real_lines:
            bad += 1
            line = text[:m.start()].count("\n") + 1
            print(f"  [MISMATCH] ASSETS.md:{line}  合计称 {want_files} 件 / {want_lines} 行，"
                  f"实为 {real_files} 件 / {real_lines} 行")
    return checked, bad


# ---- ③ 本卷自报的门禁数字：必须等于当场实跑 -------------------------------------

# 自报数字有两种排法，**两种都收**：
#   A「引用 N ｜ 可解析 N ｜ 失败 N ｜ 行锚断言核对 N[ 处]」
#   B「坐标审计 N 引用 ｜ N 可解析 ｜ N 失败 ｜ 行锚断言核对 N」
# 「处」可有可无（ASSETS 表格里那一处没有它，README 那一处用的是 B 排法）。
#
# **为什么写成两个正则而不是一个**：只写一种排法，就是**给假绿开后门**——
# 排法一变，正则匹配 0 处，门照样全绿，却一个字也没核对。
# 本仓自己写过这条纪律：门要对着「我发出去的东西」清（ch08 §8.5.2）。
# 每次改这里的正则，必须当场确认**匹配到的处数 > 0**（main() 里有这条断言）。
SELF_CLAIM_A = re.compile(
    r"引用\s*\**(\d+)\**\s*｜\s*(?:\*\*)?可解析\s*\**(\d+)\**\s*｜\s*"
    r"(?:\*\*)?失败\s*\**(\d+)\**\s*｜\s*(?:\*\*)?行锚断言核对\s*\**(\d+)\**\s*处?")
SELF_CLAIM_B = re.compile(
    r"坐标审计\s*\**(\d+)\**\s*引用\s*｜\s*\**(\d+)\**\s*可解析\s*｜\s*"
    r"\**(\d+)\**\s*失败\s*｜\s*(?:\*\*)?行锚断言核对\s*\**(\d+)\**")


def live_gate_numbers() -> tuple[int, int, int, int] | None:
    """实跑坐标审计，取它的四个数（引用/可解析/失败/行锚断言）。"""
    import subprocess
    p = subprocess.run([sys.executable, str(BOOK / "tools" / "audit_coords.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for ln in (p.stdout or "").splitlines():
        if "坐标审计合计" in ln:
            nums = [int(x) for x in re.findall(r"\d+", ln)]
            if len(nums) >= 4:
                return nums[0], nums[1], nums[2], nums[3]
    return None


def check_self_numbers(book_texts: dict[str, str]) -> tuple[int, int]:
    live = live_gate_numbers()
    if live is None:
        print("  [WARN] 坐标审计没跑出合计行，自报数字无法核对")
        return 0, 0
    checked = bad = 0
    for name, text in sorted(book_texts.items()):
        for m in SELF_CLAIM_A.finditer(text):
            checked += 1
            got = tuple(int(x) for x in m.groups())
            if got != live:
                bad += 1
                line = text[:m.start()].count("\n") + 1
                print(f"  [MISMATCH] {name}:{line}  自报 {got}，实跑 {live}")
            else:
                print(f"  [OK] {name}  自报门禁数字与实跑一致：{live}")
        for m in SELF_CLAIM_B.finditer(text):
            checked += 1
            got = tuple(int(x) for x in m.groups())
            if got != live:
                bad += 1
                line = text[:m.start()].count("\n") + 1
                print(f"  [MISMATCH] {name}:{line}  自报 {got}，实跑 {live}")
            else:
                print(f"  [OK] {name}  自报门禁数字与实跑一致：{live}")
    return checked, bad


def check_assets_coverage() -> tuple[int, int]:
    """ASSETS 的表格必须覆盖 `book/` 下每个文件。

    只核**已有的行**是不够的：少一行，`check_assets()` 照样绿。
    本卷就漏过 `OUTLINE.md`（29 个文件只列了 28 个），而门禁全绿。
    所以这里反过来查：**仓里有、表里没有**的，判失败。
    """
    p = BOOK / "ASSETS.md"
    if not p.is_file():
        return 0, 0
    rows = set()
    for ln in io.open(p, encoding="utf-8").read().splitlines():
        m = ROW_PAT.match(ln)
        if m:
            rows.add(m.group("path").replace("\\", "/"))
    root = BOOK.parent
    try:
        tracked = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false",
                                  "ls-files", "-z", "--", "book"],
                                 capture_output=True).stdout.decode("utf-8", "replace")
        files = {f[len("book/"):] for f in tracked.split("\0") if f.startswith("book/")}
    except Exception:  # pragma: no cover - 环境相关
        files = {pp.relative_to(BOOK).as_posix() for pp in BOOK.rglob("*") if pp.is_file()}
    files = {f for f in files if not f.endswith(".pyc") and "__pycache__" not in f}
    miss = sorted(files - rows)
    if miss:
        print(f"  [MISSING] ASSETS.md 的清单漏了 {len(miss)} 个文件（只核在场行 = 默认漏的不重要）：")
        for m in miss[:10]:
            print(f"      · {m}")
        if len(miss) > 10:
            print(f"      …另 {len(miss) - 10} 个")
        return len(miss), len(miss)
    print(f"  [OK] ASSETS 覆盖性：{len(files)} 个文件全部在清单里")
    return len(files), 0


def main() -> int:
    files = []
    chapters = BOOK / "chapters"
    if chapters.is_dir():
        files += [chapters / f for f in sorted(os.listdir(chapters)) if f.endswith(".md")]
    for extra in ("前言.md", "尾声.md", "ASSETS.md", "OUTLINE.md", "README.md"):
        if (BOOK / extra).is_file():
            files.append(BOOK / extra)

    book_texts: dict[str, str] = {}
    for p in files:
        book_texts[p.name] = io.open(p, encoding="utf-8").read()

    checked = unresolved = bad = 0
    for p in files:
        text = book_texts[p.name]
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

    # ② 本卷清单
    a_checked, a_bad = check_assets(book_texts)
    c_n, c_bad = check_assets_coverage()
    checked += c_n
    bad += c_bad
    checked += a_checked
    bad += a_bad
    if a_checked:
        print(f"  资产表与合计：核 {a_checked} 处，{a_bad} 处不符")

    # ③ 本卷自报的门禁数字
    s_checked, s_bad = check_self_numbers(book_texts)
    checked += s_checked
    bad += s_bad
    # **匹配到 0 处 = 门失效，不是门通过。**
    # 这一条是本文件自己的护栏：正则一旦与书里的排法脱节，
    # ③ 就会「一个数也没核」却照样全绿——那正是本书 §8.5.2 讲的假绿形状。
    if s_checked == 0:
        print("  [FAIL] 自报门禁数字一处也没匹配到：正则与书里的排法脱节了，"
              "③ 现在是**空转**，不能算通过")
        bad += 1

    print(f"已核 {checked} 处数字，{bad} 处不一致" if bad
          else f"已核 {checked} 处数字，全部一致")
    if unresolved:
        print(f"另有 {unresolved} 处解不出（路径不在仓内或不是行数口径），只计数不判失败")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
