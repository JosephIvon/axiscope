#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_crops.py —— 裁剪件生成器（**一件**，合并版）。

本脚本是 `book/crops/裁剪版.md` 的**唯一生成器**：
  · 各章「可验证主张」与「讲师 90 分钟」两段从当前 `book/chapters/` **原样裁出**，一字不改；
  · 编者按语（怎么用 / 授课顺序与依赖 / 组合方案）在本文件里，是编者的。

仓根从 `__file__` 反推（本文件在 `<book>/tools/`），不写死绝对路径。
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass

BOOK = Path(__file__).resolve().parents[1]
SRC = BOOK / "chapters"
OUT = BOOK / "crops"
CROP_NAME = "裁剪版.md"

CHAPTERS = [
    ("ch01", "ch01-这是什么.md", "这是什么"),
    ("ch02", "ch02-契约先行.md", "契约先行"),
    ("ch03", "ch03-知识库.md", "知识库"),
    ("ch04", "ch04-外部证据与归属.md", "外部证据与归属"),
    ("ch05", "ch05-引擎.md", "引擎"),
    ("ch06", "ch06-特征与归因.md", "特征与归因"),
    ("ch07", "ch07-评估协议.md", "评估协议"),
    ("ch08", "ch08-数据与脱敏.md", "数据与脱敏"),
    ("ch09", "ch09-诚实账与停机点.md", "诚实账与停机点"),
]


# ---------------------------------------------------------------- 抽取

def extract_claim(text: str) -> list[str]:
    """取「可验证主张」块：所有 '> **可验证主张**' 块中字符数最长者
    （章头的指针行是短块）；若该章以「可验证主张」小节给出且标题不是
    '**可验证主张**'，回退取小节内的引文块。"""
    lines = text.splitlines()
    blocks, cur = [], []
    for ln in lines:
        if ln.startswith("> **可验证主张**"):
            if cur:
                blocks.append(cur)
            cur = [ln]
            continue
        if cur:
            if ln.startswith(">"):
                cur.append(ln)
            else:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    if blocks:
        best = max(blocks, key=lambda b: sum(len(x) for x in b))
        if sum(len(x) for x in best) >= 120 and "见 §" not in best[0]:
            return best
    for i, ln in enumerate(lines):
        if re.match(r"^#+\s.*可验证主张", ln):
            quote = []
            j = i + 1
            while j < len(lines) and not (lines[j].startswith("#") or lines[j].strip() == "---"):
                if lines[j].startswith(">"):
                    quote.append(lines[j])
                j += 1
            if quote:
                return quote
    return blocks[0] if blocks else []


def extract_teacher(text: str) -> list[str]:
    """取讲师切分段：'**讲师 90 分钟**' 行优先；否则取 '讲师切分' 小节/标签及其后的表格。"""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("**讲师 90 分钟**"):
            out = [ln]
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].startswith("**") \
                    and not lines[j].startswith("#"):
                out.append(lines[j])
                j += 1
            return out
    for i, ln in enumerate(lines):
        if re.match(r"^#+\s.*讲师", ln):
            lvl = len(ln) - len(ln.lstrip("#"))
            out = [ln]
            j = i + 1
            while j < len(lines):
                x = lines[j]
                if (x.startswith("#") and (len(x) - len(x.lstrip("#"))) <= lvl) or x.strip() == "---":
                    break
                out.append(x)
                j += 1
            out = _strip_claim(out)
            if len(out) >= 2:
                return out
    for i, ln in enumerate(lines):
        if "讲师切分" in ln and not ln.startswith("> ") and not ln.startswith("#"):
            out = [ln]
            j = i + 1
            while j < len(lines):
                x = lines[j]
                if x.startswith("#") or x.strip() == "---":
                    break
                out.append(x)
                j += 1
            if len(out) >= 2:
                return out
    return []


def _strip_claim(lines: list[str]) -> list[str]:
    """从切分块里剔掉主张引文与其小标题（切分件只留切分，不重复主张）。"""
    out = []
    for ln in lines:
        if not ln.startswith("> ") and not ("可验证主张" in ln and ln.startswith("#")):
            out.append(ln)
    return out


# ---------------------------------------------------------------- 编者按语

HEAD = """\
# 裁剪版：九章的可验证主张与 90 分钟课切分

> **来源**：各章「可验证主张」与「讲师 90 分钟」两段**原样裁剪，一字未改**
> （正文改动后请重跑 `book/tools/build_crops.py`）。
> **规格**（`book/OUTLINE.md`）：每章两件——一句可验证主张（带锚点）+ 90 分钟课的切分点。
> 大纲模板预算为 概念 20' / 动手 40' / 习题复盘 30'（上限骨架）；各章实切见下，
> 动手预算不得被讲解侵占——每章都有现场跑真命令的环节。

## 为什么只有一版

一件就够：读者要的是**一句带锚点、当场可复核的主张**与**这一章怎么讲**。
开源项目面对的是**一类读者**，所以裁剪件只给这两件：
可验证的主张，与可照着排的课表。
"""

RULES = """\
## 怎么用（先读这条再用）

1. **可验的含义**：锚点 = 仓库@commit + 路径，对有仓库访问权的人当场可验
   （`git clone` 后开文件即对上数字）。
2. **数字全部有坐标**：主张句里没有任何形容词撑场的数字——每个都挂在
   `axiscope@<commit>` 或工件路径上，追问到底就是本书对应章节。
3. **主张与切分是两件事**：主张说明"这一章主张了什么、能验到哪"，
   切分说明"90 分钟怎么排"。按需取用，不必两样都读。
"""

DEPS = """\
## 授课顺序与依赖（编者加注）

- **先讲 ch02**：契约先行是全书地基，ch05/ch06 的实现都以它为前提。
- **ch03 → ch05/ch06**：知识库里的判据族是引擎实现与归因口径的来源。
- **ch04 独立成章**：外部证据怎么算、复用什么怎么标，是任何一方数据
  都要先立的规矩；跳过这一章，后面的"可核对"就只是本项目内部的默契。
"""

COMBOS = """\
## 组合方案（编者加注）

| 方案 | 组成 | 适合 |
|---|---|---|
| 单章课 ×9 | 任一章 90' | 企业内训切片 |
| 契约线全天（6h） | ch01 → ch02 → ch03 → ch04 | 数据/算法团队 |
| 引擎线半天（4.5h） | ch05 → ch06 → ch07 | 工程团队 |
| 两日全课（9h+机动） | 九章全排 + 60' 结算工作坊（用 ch09 动手收全课） | 完整方法论培训 |
"""


# ---------------------------------------------------------------- 生成

def build() -> str:
    parts = [HEAD, RULES, DEPS, COMBOS, "---"]
    for idx, (k, fn, title) in enumerate(CHAPTERS, 1):
        text = (SRC / fn).read_text(encoding="utf-8")
        claim = extract_claim(text)
        teacher = extract_teacher(text)
        parts.append(f"\n## {k} {title}（第{idx}章）\n")
        parts.append("\n".join(claim) if claim else "> （本章可验证主张缺失——待补）")
        parts.append("")
        parts.append("\n".join(teacher) if teacher else "**讲师 90 分钟**：待补")
        parts.append("")
    return "\n".join(parts)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / CROP_NAME
    body = build()
    with io.open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    n = len(body.splitlines())
    print(f"   {target}: {n} 行")
    print("裁剪件已重建（单件合并版；各章主张与切分从当前 chapters/ 原样重抽）")


if __name__ == "__main__":
    main()
