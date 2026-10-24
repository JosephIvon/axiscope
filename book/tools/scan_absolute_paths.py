#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_absolute_paths.py —— 公开前脱敏扫描（书 + 仓内文档）。

抓三类东西：
  ① **家目录 / 用户名**：机器上有、换台机器就没有，且能反推是谁的机器。
  ② **本机工作区路径**：写进书里，读者按它去找文件必然落空。
  ③ **本项目自己的脱敏标识值**（`src/axiscope/assertions.py` 里的 `REDACT_TOKENS`）：
     厂区名、ADS NetID 前缀、盘符。**这三样在仓内数据侧已经令牌化**，
     文档侧就不许再出现——出现了就等于"数据脱敏了、文档没脱"。

第 ③ 条是本仓特有的：通用脱敏扫描抓不到它，因为 `141.58.` 与
`Versuchsstand` 在**语法上就是普通字符串**。只有把 `REDACT_TOKENS`
当黑名单扫，才能抓住"同一批标识值在文档侧漏出来"这件事。

判据：命中即判失败。第 ③ 类**工具链路径**（如 Python 安装位置）不在此列——
那是通用安装位置，不是谁的隐私。

**③ 类的语境豁免**：脱敏 token 本身是**公开的**——它就写在
`src/axiscope/assertions.py` 的 `REDACT_TOKENS` 常量里（那是要被代码匹配的），
策略文件也必须写明"要抹哪几个字"，否则门禁无法被人复核。
所以 token **出现在策略/计量语境里不是泄露**，出现在数据里才是。
本工具据上下文判定：命中行的**同段上下文**里带策略标记（脱敏/令牌/token/
REDACT/计数/实测/归零…）的，记入「策略语境（已豁免）」，**不计失败**；
不带标记的**判失败**。

为什么必须分这一档：一个把策略文本也判成泄露的门禁，第二次运行就会被人
加白名单绕过——**加了白名单的门禁，就只剩"看起来在查"这一层了**。
"""
from __future__ import annotations

import io
import json
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

# ① 家目录 / 用户名
HOME_PAT = re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"'`]+")
# ② 本机工作区 / CI 落点
WS_PAT = re.compile(r"[A-Za-z]:\\(?:workspace|a|ci_test|ci_sim|tmp|home)[\\/][^\s\"'`]*")
# ③ 本仓自己的脱敏标识值（与 src/axiscope/assertions.py 的 REDACT_TOKENS 同源）
REDACT_PAT = re.compile(r"Versuchsstand|141\.58\.")

# ③ 的语境豁免：命中处附近出现这些标记 = 在讲脱敏**策略/计量**，不是在泄露数据
POLICY_CTX = re.compile(
    r"脱敏|令牌|token|REDACT|归零|实测|命中|计数|标识值|PII|not in serialized_bundle|"
    r"probe_pii|替换为|正则清除|清除|不留|不出现|被抹|抹掉",
    re.IGNORECASE,
)
CTX_LINES = 3   # 上下文窗口：命中行上下各 3 行

# 扫哪些目录
TARGET_DIRS = ["book", "docs", "README.md", "NOTICE.md"]

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "data", "bench", "synth"}


def iter_files():
    for rel in TARGET_DIRS:
        p = REPO / rel.replace("/", os.sep)
        if p.is_file():
            yield p
        elif p.is_dir():
            for dp, dns, fns in os.walk(p):
                dns[:] = [d for d in dns if d not in SKIP_DIRS]
                for fn in fns:
                    if fn.endswith((".md", ".json", ".txt", ".py")):
                        yield os.path.join(dp, fn)


def load_known() -> dict:
    """读登记在册的已知项（`book/known_findings.json`）。"""
    p = BOOK / "known_findings.json"
    if not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {f.get("id"): f for f in d.get("findings", []) if f.get("id")}


def disclosed_ids(book_text: str) -> set[str]:
    """全书文本里出现过的登记项 id。"""
    return set(re.findall(r"\bK-\d+\b", book_text))


def main() -> int:
    known = load_known()
    book_text = "\n".join(
        io.open(p, encoding="utf-8", errors="replace").read()
        for p in sorted(BOOK.rglob("*.md"))
    )
    seen_known = set()

    hits = []
    exempt = []
    for path in iter_files():
        try:
            text = io.open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            ctx = "\n".join(lines[max(0, i - 1 - CTX_LINES): i + CTX_LINES])
            for pat, label in ((HOME_PAT, "家目录/用户名"), (WS_PAT, "本机工作区路径"),
                               (REDACT_PAT, "脱敏标识值")):
                for m in pat.finditer(line):
                    rec = (label, os.path.relpath(path, str(REPO)).replace("\\", "/"),
                           i, m.group(0))
                    if label == "脱敏标识值":
                        # 登记在册的已知项：命中即查登记
                        # **已清偿的登记项不提供豁免**——它当初值就长在那个位置，
                        # 现在那个位置必须干净；值再出现就是复发，判失败。
                        registered = False
                        for kid, f in known.items():
                            if str(f.get("state", "open")) == "cleared":
                                continue
                            if (f.get("file") == rec[1] and int(f.get("line", -1)) == rec[2]
                                    and rec[3] in str(f.get("token", ""))):
                                seen_known.add(kid)
                                exempt.append(rec + (kid,))
                                registered = True
                                break
                        if registered:
                            continue
                        if POLICY_CTX.search(ctx):
                            exempt.append(rec)
                            continue
                    hits.append(rec)

    # 登记了但没在书里披露的 → 判失败（护栏：登记表不得变成沉默的白名单）
    # 已清偿的项不再要求「在扫描里被命中」——值已经不在仓里了，
    # 命中不到才是对的；但**披露**这一条照旧要求（不许悄悄销账）。
    undisclosed = []
    for kid, f in known.items():
        if kid not in disclosed_ids(book_text):
            undisclosed.append((kid, f.get("file"), f.get("line")))
        elif str(f.get("state", "open")) != "cleared" and kid not in seen_known:
            undisclosed.append((kid, f.get("file"), f.get("line")))

    cleared = [k for k, f in known.items() if str(f.get("state", "open")) == "cleared"]
    if cleared:
        print(f"已清偿的登记项（**不再豁免扫描**——值若重新出现即判失败）：{'、'.join(sorted(cleared))}")
        print()

    if exempt:
        print("策略语境 / 登记在册（不计失败）——这些 token 出现在脱敏策略、计量文本或已登记的已知项里：")
        for rec in exempt:
            kid = rec[4] if len(rec) > 4 else None
            tail = f"（登记项 {kid}）" if kid else ""
            print(f"  ○ [{rec[0]}] {rec[1]}:{rec[2]}  →  {rec[3][:40]}{tail}")
        print()

    if undisclosed:
        print("登记在册但**未在书中披露**（登记表不得变成沉默的白名单）：")
        for kid, f, i in undisclosed:
            print(f"  ✗ {kid}  {f}:{i}")
        print()

    if hits or undisclosed:
        if hits:
            print("命中（公开前必须清零）：")
            for label, f, i, frag in hits:
                print(f"  ✗ [{label}] {f}:{i}  →  {frag[:60]}")
        print(f"\n合计 {len(hits)} 处未清（豁免/登记 {len(exempt)} 处）；"
              f"登记未披露 {len(undisclosed)} 处；已清偿登记 {len(cleared)} 条。")
        return 1
    print(f"合计 0 处（豁免/登记 {len(exempt)} 处）；"
          f"已清偿登记 {len(cleared)} 条；必改项清零才算公开就绪。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
