"""PII / 内网标识扫描：KB2 §4.10、§4.11 的「发布前必做」计数由本脚本打印，不得人工点数。

    PYTHONPATH=src python data/probe_pii.py                 # 扫 data/raw 与 build 产物
    PYTHONPATH=src python data/probe_pii.py 目录1 目录2      # 自定义扫描根

口径（写死在这里，文档只抄打印行）：
- 计数单位 = **正则命中次数**（一次出现记一行），不是"含该串的文件数"，也不是行数；
  同一行重复出现多次全部计入（`NetID` 在 Export10 第 11 行就重复了 32 次）。
- 只读文本，按 utf-8 + errors=replace 解码；二进制不会给出可信计数，本仓的 raw 全是文本。
- 扫描范围分两组打印：`data/raw/`（母本，发布前须脱敏）与 `build/`（引擎产物，应当 0 命中）。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATTERNS = [
    ("Versuchsstand 路径", r"Versuchsstand"),
    ("NetID 标签", r"NetID"),
    ("内网 IP [REDACTED_INTERNAL_IP]", r"141\.58\.102\.56"),
    ("绝对盘符路径 C:" + chr(92), r"[A-Za-z]:" + chr(92) * 2),
]


def scan(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    return {name: len(re.findall(pat, text)) for name, pat in PATTERNS}


def walk(d):
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            out.append(p)
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


def main(argv):
    roots = argv[1:] or [os.path.join(ROOT, "data", "raw"),
                         os.path.join(ROOT, "build", "Export10_244531")]
    for r in roots:
        report(os.path.relpath(r, ROOT), walk(r))
    print("== 说明 ==")
    print("  KB2 §4.10/§4.11 的「发布前必做」计数按本脚本打印值引用（KB0 §6 检查 27：")
    print("  汇总计数须由脚本自数并打印，文档抄打印行）。")


if __name__ == "__main__":
    main(sys.argv)
