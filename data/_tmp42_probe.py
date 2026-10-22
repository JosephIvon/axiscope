import json
from pathlib import Path
from axiscope import features as fm

files = [
    "examples/c2_example_a.json",
    "examples/c2_example_a_no_events.json",
    "examples/c2_example_b.json",
    "examples/kb4_case_b_features.json",
    "build/Export10_244531/features.json",
]

def rule14_conflicts(f):
    rows = {r["feature"] for r in f["unavailable"]}
    conflicts = []
    for path in sorted(rows):
        val = fm._dig(f, path)
        if fm._has_value(val):
            conflicts.append(path)
    return conflicts

def dup_paths(f):
    seen = {}
    for u in f["unavailable"]:
        seen.setdefault(u["feature"], []).append(u.get("rule"))
    return {k: v for k, v in seen.items() if len(v) > 1}

for fp in files:
    p = Path(fp)
    if not p.exists():
        print(f"{fp}: MISSING")
        continue
    f = json.loads(p.read_text(encoding="utf-8"))
    rows = len(f.get("unavailable", []))
    na = ok_na = None
    try:
        fm.check_null_accounting(f)
        ok_na = "OK"
    except Exception as e:
        ok_na = f"FAIL: {e}"
    try:
        fm.check_resonance_counts(f)
        ok_rc = "OK"
    except Exception as e:
        ok_rc = f"FAIL: {e}"
    c14 = rule14_conflicts(f)
    dups = dup_paths(f)
    print(f"=== {fp}")
    print(f"  rows={rows}")
    print(f"  check_null_accounting: {ok_na}")
    print(f"  check_resonance_counts: {ok_rc}")
    print(f"  rule14 conflicts={len(c14)} {c14}")
    print(f"  dup paths={dups}")
