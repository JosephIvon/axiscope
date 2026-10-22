"""生成 bench/samples/<case_id>/、bench/cases.jsonl、bench/hidden.sha256。

    PYTHONPATH=src PYTHONIOENCODING=utf-8 python bench/build_cases.py

可重跑：同一份输入 CSV ⟹ 同一批样本包字节 ⟹ 同一份 cases.jsonl 与 hidden.sha256。
"""
from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import casebuild as cb  # noqa: E402

BENCH = os.path.dirname(os.path.abspath(__file__))
CASES_JSONL = os.path.join(BENCH, "cases.jsonl")
HIDDEN = os.path.join(BENCH, "hidden.sha256")


def _expect(rows, case_id):
    for r in rows:
        if r["case_id"] == case_id:
            return r.get("expected_verdict_class")
    return None


def main() -> int:
    cb.assign_source_tier_and_origin()
    rows = []
    for case in cb.CASES:
        outdir = os.path.join(cb.SAMPLES_DIR, case["case_id"])
        built = cb.materialize(case, outdir)
        row = cb.case_row(case, built["meta"], built["features"], built["truth"])
        rows.append(row)
        print("[build] %-26s tier=%s split=%-6s fs=%gHz f_b=%gHz ch=%s digest=%s" % (
            case["case_id"], row["source_tier"], row["split"], row["fs_hz"],
            row["reliable_band_hz"], ",".join(row["present_channels"]), row["sha256"][:16]))

    with io.open(CASES_JSONL, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")

    hidden = [r for r in rows if r["split"] == "hidden"]
    with io.open(HIDDEN, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# C5 §2 冻结文件 —— 隐藏测试集输入样本字节摘要（KB8 §1.4 口径）\n")
        fh.write("# digest = SHA256( bytes(meta.json) || 0x00 || bytes(waveform.tsv) || 0x00 || bytes(events.jsonl 或空) )\n")
        fh.write("# 冻结后追加任一案例 => 全量重划 + 版本号 +1（KB8 §4 红线 2）\n")
        for row in sorted(hidden, key=lambda r: r["case_id"]):
            fh.write("%s  bench/samples/%s\n" % (row["sha256"], row["case_id"]))

    # 孪生一致性（A-61 / KB5 §5.5 P-12）：孪生两份的 waveform.tsv 必须逐字节相同。
    # 孪生设计本身合法（INJ19 带事件流 / CTL-0002 不带，靠 events.jsonl 分出两种判定），
    # 但那要求两份**整包**确有差别；只比波形会漏掉「整包也相同却挂了不同期望」这种真矛盾。
    for row in rows:
        if row.get("twin_of"):
            a = os.path.join(cb.SAMPLES_DIR, row["twin_of"], "waveform.tsv")
            b = os.path.join(cb.SAMPLES_DIR, row["case_id"], "waveform.tsv")
            same = open(a, "rb").read() == open(b, "rb").read()
            print("[twin]  %s <-> %s waveform 逐字节相同: %s" % (row["twin_of"], row["case_id"], same))
            if not same:
                return 1

    # 硬门禁：整包逐字节相同却期望不同 ⟹ 基准集按构造有一方永远判不对，必须构建失败。
    digests = {r["case_id"]: r["sha256"] for r in rows}
    seen: dict[str, str] = {}
    for r in rows:
        prior = seen.get(r["sha256"])
        if prior and digests[prior] == r["sha256"] and \
                prior != r["case_id"] and _expect(rows, prior) != _expect(rows, r["case_id"]):
            print("[gate] 整包相同但期望不同：%s(%s) vs %s(%s) —— 基准集自相矛盾，构建失败"
                  % (prior, _expect(rows, prior), r["case_id"], _expect(rows, r["case_id"])),
                  file=sys.stderr)
            return 1
        seen[r["sha256"]] = r["case_id"]

    print("[build] cases.jsonl  %d 行（dev=%d hidden=%d）" % (
        len(rows), sum(1 for r in rows if r["split"] == "dev"), len(hidden)))
    print("[build] hidden.sha256 %d 行" % len(hidden))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())