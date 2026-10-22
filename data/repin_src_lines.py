"""按 `### R-nn` 标题行重钉 `rule_table.json` 的 `src_line`（检查 27 的机械性副作用处置）。

KB3 增删行 ⟹ 行号漂移 ⟹ `tests/test_registration.py::test_rule_table_citations_land_on_their_kb3_headings`
当场抓红。本脚本只做一件事：把每条规则的 `src_line` 改成它自己的 `### R-nn` 标题所在行号。

用法：`python data/repin_src_lines.py`（就地改 `src/axiscope/rule_table.json` 并打印逐条位移）。
"""
import io
import json
import re

KB3 = "docs/kb/KB3-tuning-rules.md"
JT = "src/axiscope/rule_table.json"

lines = io.open(KB3, encoding="utf-8").read().split("\n")
head = {}
for i, ln in enumerate(lines, 1):
    m = re.match(r"^###\s+(R-\d{2})\b", ln)
    if m:
        head.setdefault(m.group(1), i)

rows = json.load(io.open(JT, encoding="utf-8"))
rules = rows["rules"]
pairs = ([(k, v) for k, v in rules.items()] if isinstance(rules, dict)
         else [(r.get("rule_id") or r.get("id"), r) for r in rules])
text = io.open(JT, encoding="utf-8").read()
moved = 0
for rid, r in pairs:
    tgt = head.get(rid)
    if tgt is None or "src_line" not in r:
        continue
    if r["src_line"] != tgt:
        old = r["src_line"]
        frag = '"src_line": %d' % old
        assert text.count(frag) == 1, "%s: 定位串 %r 在 JSON 里不唯一" % (rid, frag)
        text = text.replace(frag, '"src_line": %d' % tgt, 1)
        print("%s %s -> %s" % (rid, old, tgt))
        moved += 1

io.open(JT, "w", encoding="utf-8", newline="\n").write(text)
print("repinned rules=%d | headings known=%d" % (moved, len(head)))
