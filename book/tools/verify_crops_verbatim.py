#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_crops_verbatim.py —— 裁剪件逐字核验。

裁剪件里的每一段主张与切分，必须与 `chapters/` 里**当前**的原文**逐字一致**。
不一致就判红。

为什么要有这道：裁剪件是**生成物**，但它会被单独发出去、被人引用。
一旦它在正文改过之后没重新生成，它就是一份"看着完整、其实落后"的材料——
而它的样子与正文一模一样，读者分不出新旧。**凡是会被单独引用的产物，
都要有一道"它与源还一致吗"的门。**
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_crops import (CHAPTERS, CROP_NAME, OUT, SRC, extract_claim,  # noqa: E402
                         extract_teacher)

crop_path = OUT / CROP_NAME
if not crop_path.exists():
    print(f"[FAIL] 裁剪件不存在：{crop_path}")
    sys.exit(1)
crops = io.open(crop_path, encoding="utf-8").read()

bad = 0
for fn in sorted(x for x in os.listdir(SRC) if x.endswith(".md") and x != "00-导读.md"):
    text = io.open(SRC / fn, encoding="utf-8").read()
    for label, block in (
        ("可验证主张", extract_claim(text)),
        ("讲师切分", extract_teacher(text)),
    ):
        if not block:
            print(f"[SKIP] {fn} {label}：章内无可抽取块")
            continue
        missing = [l for l in block if l.strip() and l.strip() not in crops]
        if not missing:
            print(f"[OK] {CROP_NAME} ← {fn} {label}：{len(block)} 行逐字命中")
        else:
            bad += 1
            print(f"[DIFF] {CROP_NAME} ← {fn} {label}：{len(missing)} 行未原样出现")
            for l in missing[:5]:
                print(f"        缺：{l.strip()[:100]}")

# 裁剪件里不许出现求职口径（开源后不服务"一个人的投递"）
for leftover in ("简历", "求职", "投递", "岗位要求"):
    if leftover in crops:
        bad += 1
        print(f"[DIFF] 裁剪件里仍有求职口径：{leftover}")

# crops/ 下应当只有一件裁剪件
if OUT.is_dir():
    others = [p.name for p in OUT.iterdir() if p.name != CROP_NAME]
    if others:
        bad += 1
        print(f"[DIFF] crops/ 下应当只有一件裁剪件，还多出：{others}")

print("不一致条数：", bad)
sys.exit(1 if bad else 0)
