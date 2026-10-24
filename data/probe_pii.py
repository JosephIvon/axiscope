#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PII / 内网标识扫描：KB2 §4.10、§4.11 的「发布前必做」计数由本脚本打印，不得人工点数。

    PYTHONPATH=src python data/probe_pii.py                 # 扫 data/raw 与 build 产物
    PYTHONPATH=src python data/probe_pii.py 目录1 目录2      # 自定义扫描根

口径（写死在这里，文档只抄打印行）：
- 计数单位 = **正则命中次数**（一次出现记一行），不是"含该串的文件数"，也不是行数；
  同一行重复出现多次全部计入（`NetID` 在 Export10 第 11 行就重复了 32 次）。
- 只读文本，按 utf-8 + errors=replace 解码；二进制不会给出可信计数，本仓的 raw 全是文本。
- 扫描范围分三组打印：
  ① `data/raw/`（母本，发布前须脱敏）；
  ② `build/`（引擎产物，应当 0 命中）；
  ③ **仓内文档与代码**（除原始数据与构建产物外全仓）——标识值不得以"机器标识"的
     具体形态留在仓里（见下方 DOC_PATTERNS 的口径说明）。

**退出码**：①+② 的三个**值类** token（Versuchsstand 路径 / 内网 IP / 绝对盘符路径）
与 ③ 的全部计数必须为 0，否则 exit 1。
`NetID` 标签不参与判定——它是**字段名**（"NetID" 这个词），
KB2 §4.10 的 32 与侧车的 1 都是它，属"叙述文字"，不是标识值。
"""
import io
import os
import re
import sys

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATTERNS = [
    ("Versuchsstand 路径", r"Versuchsstand"),
    ("NetID 标签", r"NetID"),
    ("内网 IP 141.58. 网段", r"141\.58\.\d{1,3}\.\d{1,3}"),
    ("绝对盘符路径 C:" + chr(92), r"[A-Za-z]:" + chr(92) * 2),
]

# 值类 token：必须为 0（`NetID` 标签是字段名，不在其中）。
VALUE_TOKENS = ("Versuchsstand 路径", "内网 IP 141.58. 网段", "绝对盘符路径 C:" + chr(92))

# ③ 仓内文档与代码：标识值不得以"机器标识"的具体形态留在仓里。
#   口径照 KB2 §六 的三类——主机路径 / ADS NetID / 绝对墙钟，三类在**仓内任何文件**里
#   都不得留具体值；`141.58.`（网段前缀）除外：它是代码里既有的检测 token
#   （src/axiscope/assertions.py:18 的 REDACT_TOKENS），公开是设计。
#   禁掉更具体的两档：4 段内网地址（那台机器的地址）、6 段完整 ADS NetID（可路由标识）。
#   **口径与数据侧一致**：数据侧的口径是"连 4 段都不留"（下面打印的内网 IP 合计恒为 0），
#   文档侧与代码侧照同一口径——口径不一致就是漏。
#   扫描对象是 **git 跟踪的文件**（= 会被发布出去的那些），
#   不是工作树：暂存区的本地母本按 A-131 不入库，扫它只会天天报同一个已知的本地事实。
DOC_PATTERNS = [
    ("主机路径 C:\\Versuchsstand", r"C:\\Versuchsstand"),
    ("绝对墙钟 ticks（18 位）", r"\b1\d{17}\b"),
    ("绝对墙钟（德语日期时刻）",
     r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag), \d{1,2}\. \w+ \d{4}"),
    # **日期+时刻**才算绝对墙钟：只有时刻（如某次自检的时刻）不定位任何一次实验，
    # 带着日期才是"这次采集发生在什么时候"——那是要清的。
    # 这一档是 2026-10-24 重写历史时才发现的：两份侧车的「导出时刻」带着日期，
    # 之前的门只认 ticks 与德语日期，没认出「YYYY-MM-DD HH:MM:SS.mmm」这一种。
    ("绝对墙钟（日期+时刻）", r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\.\d{3}"),
    ("完整 ADS NetID（6 段）", r"141\.58\.\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    ("内网 IP（4 段）", r"141\.58\.\d{1,3}\.\d{1,3}"),
]

#: 形状对、语义不对的命中：**登记豁免，但只豁免到上限**。
#:
#: 「日期+时刻」这一档的形状是通用的——DOI 注册局自己的登记时刻、
#: 另一份公开数据集的首列时间戳、测 ISO epoch 解析的合成夹具，
#: 长得一模一样，却都不是**本数据集导出**的墙钟（KB2 §6.1 那一行是字段级的：
#: 说的是 L3/L4 导出起始/结束时刻，不是仓里所有 ISO 时间戳）。
#:
#: 所以这里按「文件 + 类别 + 上限 + 理由」登记：
#: 命中数**不超过上限**才豁免；**多出一处就判失败**——
#: 豁免是"这几处我知道为什么无害"，不是"这个文件从此免检"。
#: 理由必须写清楚，否则下一个来的人只能靠猜。
DOC_EXEMPTIONS = {
    "data/datacite_sciencedb_04148_2026-10-20.json": (
        "绝对墙钟（日期+时刻）", 3,
        "DOI 注册局自己的登记/更新时刻（公开元数据，非本数据集的导出墙钟）"),
    "data/research_current_channel.md": (
        "绝对墙钟（日期+时刻）", 1,
        "另一份公开数据集的首列时间戳（本仓只引用它，不导出它）"),
    "tests/test_validate_raw_intake.py": (
        "绝对墙钟（日期+时刻）", 3,
        "合成夹具：测 ISO epoch 解析，人造时间，与任何一次实验无关"),
}

# 原始数据与构建产物：各自单列成组，不进 ③。
SKIP_DIR_NAMES = {".git", "__pycache__", "build", "node_modules", ".pytest_cache"}
SKIP_REL_PREFIXES = ("data" + os.sep + "raw", "data" + os.sep + "incoming",
                      "data" + os.sep + "staging")


def scan(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    return {name: len(re.findall(pat, text)) for name, pat in PATTERNS}


def scan_doc(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    return {name: len(re.findall(pat, text)) for name, pat in DOC_PATTERNS}


def walk(d):
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            out.append(p)
    return out


def tracked_files():
    """**git 跟踪**的文件——即会被发布出去的那些。

    用 `git ls-files` 而不是扫工作树：暂存区里按 A-131 放着本地母本
    （未入库是设计，不是问题），扫它只会天天报同一个已知的本地事实；
    而"仓里发了什么"这件事，只由跟踪文件回答。
    非 git 环境（导出的源码包）退回全目录扫描。
    """
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", ROOT, "-c", "core.quotepath=false", "ls-files", "-z"],
            capture_output=True, text=True, encoding="utf-8").stdout
        names = [n for n in out.split("\0") if n]
        if names:
            return [os.path.join(ROOT, n.replace("/", os.sep)) for n in names]
    except Exception:
        pass
    return walk_repo()


def walk_repo():
    """仓内全部文本文件（原始数据与构建产物除外）——非 git 环境的兜底。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in sorted(dirnames) if d not in SKIP_DIR_NAMES]
        rel_dir = os.path.relpath(dirpath, ROOT)
        if rel_dir != "." and any(rel_dir.startswith(p) for p in SKIP_REL_PREFIXES):
            dirnames[:] = []
            continue
        for name in sorted(filenames):
            out.append(os.path.join(dirpath, name))
    return out


def report(label, files):
    print("== %s（%d 个文件）==" % (label, len(files)))
    totals = {name: 0 for name, _ in PATTERNS}
    hit_files = 0
    for p in files:
        counts = scan(p)
        if any(counts.values()):
            hit_files += 1
            print("  %-52s %s" % (os.path.relpath(p, ROOT),
                                  " ".join("%s=%d" % (k, v) for k, v in counts.items() if v)))
        for k, v in counts.items():
            totals[k] += v
    print("  命中文件数 %d / %d" % (hit_files, len(files)))
    for k, v in totals.items():
        print("  合计 %-24s %d" % (k + ":", v))
    return totals


def report_docs():
    files = tracked_files()
    print("== 仓内跟踪文件（= 会被发布出去的那些）==")
    totals = {name: 0 for name, _ in DOC_PATTERNS}
    hit_files = 0
    exempted = []
    for p in files:
        try:
            counts = scan_doc(p)
        except OSError:
            continue
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        ex = DOC_EXEMPTIONS.get(rel)
        if ex:
            cls, cap, why = ex
            if counts.get(cls, 0) <= cap:
                counts[cls] = 0
                exempted.append((rel, cls, cap, why))
        if any(counts.values()):
            hit_files += 1
            print("  %-52s %s" % (rel,
                                  " ".join("%s=%d" % (k, v) for k, v in counts.items() if v)))
        for k, v in counts.items():
            totals[k] += v
    print("  命中文件数 %d / %d" % (hit_files, len(files)))
    for k, v in totals.items():
        print("  合计 %-24s %d" % (k + ":", v))
    for rel, cls, cap, why in exempted:
        print("  豁免 %-46s %s ≤ %d 处：%s" % (rel, cls, cap, why))
    return totals


def main(argv):
    roots = argv[1:] or [os.path.join(ROOT, "data", "raw"),
                         os.path.join(ROOT, "build", "Export10_244531")]
    bad = 0
    for r in roots:
        totals = report(os.path.relpath(r, ROOT), walk(r))
        for tok in VALUE_TOKENS:
            if totals.get(tok):
                print("  [FAIL] 值类 token %r 合计 %d ≠ 0（脱敏未清偿）" % (tok, totals[tok]))
                bad += 1
    doc_totals = report_docs()
    for k, v in doc_totals.items():
        if v:
            print("  [FAIL] 仓内文档与代码里还有机器标识：%s %d 处" % (k, v))
            bad += 1
    print("== 说明 ==")
    print("  KB2 §4.10/§4.11 的「发布前必做」计数按本脚本打印值引用（KB0 §6 检查 27：")
    print("  汇总计数须由脚本自数并打印，文档抄打印行）。")
    print("  `NetID` 标签是**字段名**，不参与判定；禁的是标识**值**。")
    if bad:
        print("  判定：红（%d 项未清偿）" % bad)
        return 1
    print("  判定：绿（值类 token 归零；仓内文档与代码无机器标识）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
