import json, re, io
from pathlib import Path
import sys

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


ROOT = Path(".")
text = (ROOT / "docs/contracts/C2-features.md").read_text(encoding="utf-8")

blocks = []
for m in re.finditer(r"```json\n(.*?)\n```", text, re.S):
    raw = m.group(1)
    try:
        obj = json.loads(raw)
        blocks.append((m.start(), obj))
    except ValueError as e:
        # try to note the shape
        first = raw.strip().splitlines()[0] if raw.strip() else ""
        blocks.append((m.start(), f"PARSE-FAIL: {e}  firstline={first[:60]!r}"))

print(f"num json fenced blocks = {len(blocks)}")
for pos, obj in blocks:
    if isinstance(obj, str):
        print(f"  @{pos}: {obj}")
    else:
        keys = list(obj.keys()) if isinstance(obj, dict) else type(obj)
        schema = obj.get("schema") if isinstance(obj, dict) else None
        has_unavail = isinstance(obj, dict) and "unavailable" in obj
        print(f"  @{pos}: schema={schema!r} unavailable_rows={len(obj['unavailable']) if has_unavail else 'N/A'} topkeys={keys if isinstance(obj,dict) else obj}")

# compare to example files
examples = {
    "A": ROOT/"examples/c2_example_a.json",
    "A_NO_EVENTS": ROOT/"examples/c2_example_a_no_events.json",
    "B": ROOT/"examples/c2_example_b.json",
    "CASE_B": ROOT/"examples/kb4_case_b_features.json",
}
loaded = {k: json.loads(p.read_text(encoding="utf-8")) for k,p in examples.items()}
objs = [o for _,o in blocks if isinstance(o, dict)]
for k, ex in loaded.items():
    matched = [i for i,o in enumerate(objs) if o == ex]
    print(f"example {k}: exact-match inline block indices = {matched}")
    if not matched:
        # find nearest by schema
        same = [i for i,o in enumerate(objs) if o.get("schema")==ex.get("schema")]
        print(f"    same-schema blocks = {same}")
        for i in same:
            o = objs[i]
            allkeys = set(list(o.keys())+list(ex.keys()))
            diffs = [kk for kk in allkeys if o.get(kk)!=ex.get(kk)]
            print(f"    block {i} vs {k}: differing top keys = {sorted(diffs)}")
