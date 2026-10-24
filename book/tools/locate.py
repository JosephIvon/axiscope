#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""locate.py —— 写书时用的查行工具：给一句原文，打印它落在哪个文件的第几行。

用法：
    python book/tools/locate.py "轴是一个离线的伺服"      # 全仓找
    python book/tools/locate.py --file docs/kb/KB0-conventions.md "规则编号"

为什么要有这个工具：书里每一处坐标都是「文件 + 行号」。行号是**写的时候**的
事实，而文件会变——所以坐标必须能被机器复核，也必须能被机器**重新定位**。
人肉翻文件数行号既慢又容易数错；这个工具把"数行号"变成一次检索。

它按**锚点 commit** 读源文件（与坐标审计同一口径），
所以它给出的行号与审计器认的行号是同一个——**同一把尺子**。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _anchor import ANCHOR_COMMIT  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def files_at_anchor() -> dict[str, list[str]]:
    # core.quotepath=false：中文路径默认会被 git 转义成 "\344\270\226" 这种形式，
    # 那样 `git show <rev>:<path>` 拿不到文件——**带中文名的文件会整批消失**。
    out = subprocess.run(["git", "-C", str(REPO), "-c", "core.quotepath=false",
                          "ls-tree", "-r", "--name-only", ANCHOR_COMMIT],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    names = [n for n in (out.stdout or "").splitlines() if n.strip()]
    res = {}
    for n in names:
        if not n.lower().endswith((".md", ".py", ".json", ".txt", ".ps1", ".csv", ".html")):
            continue
        r = subprocess.run(["git", "-C", str(REPO), "show", f"{ANCHOR_COMMIT}:{n}"],
                           capture_output=True)
        if r.returncode == 0:
            res[n] = r.stdout.decode("utf-8", "replace").splitlines()
    return res


def main(argv: list[str]) -> int:
    only = None
    if argv and argv[0] == "--file":
        only = argv[1]
        argv = argv[2:]
    if not argv:
        print(__doc__)
        return 2
    needle = argv[0]
    files = files_at_anchor()
    if only:
        files = {k: v for k, v in files.items() if k.endswith(only)}
    hits = 0
    for name, lines in sorted(files.items()):
        for i, ln in enumerate(lines, 1):
            if needle in ln:
                hits += 1
                print(f"{name}:{i}: {ln.strip()[:150]}")
    if not hits:
        print(f"没找到：{needle!r}（锚点 {ANCHOR_COMMIT}）")
        return 1
    print(f"— 共 {hits} 处 —")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
