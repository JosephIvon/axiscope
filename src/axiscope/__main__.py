"""CLI：厂商 CSV → C1 样本包 → C2 特征 → C3 归因 → HTML 报告。

    python -m axiscope --in data/raw/Export10_244531.csv --out build/Export10_244531
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

from . import assertions as asrt
from . import c1, c3validate, engine, features, report
from .twincat import ScopeFormatError, read_scope


def run(inp: str, outdir: str, sample_id: str | None = None) -> int:
    table = read_scope(inp)
    sid = sample_id or os.path.splitext(os.path.basename(inp))[0]
    meta, ingest = c1.build_meta(table, sample_id=sid)
    pack = c1.write_pack(meta, ingest, outdir)
    ingest["sample_id"] = sid
    ingest["sha256"] = pack["sha256"]
    feats = features.compute(meta, ingest, outdir)
    report.write_features(os.path.join(outdir, "features.json"), feats)

    if meta["provenance"].get("trigger_gate") is None:
        # KB2 §8.3 的断言层与 HTML 报告逐条针对 Scope View 的触发门控样本
        #（`provenance.trigger_gate`）；非 Scope View 方言没有这个槽位 ⟹ 不给它造一个，
        # 也不用「恒真」冒充通过。样本包与 C2 特征已落盘，诊断链路到此为止。
        print(f"样本包 {outdir}")
        print(f"  {meta['quality']['n_samples']} 行 @ {meta['sample_rate_hz']:g} Hz"
              f"（母本 {table.n_rows_raw} 行）")
        print(f"  导出方言 {meta['source']['export_format']} · 时间列 "
              f"{meta['provenance']['time_column']}（{meta['provenance']['unit_source']}）")
        print(f"  canonical {meta['present_channels']} / extra {len(meta['extra_channels'])}")
        print(f"  blocked_rules {feats['freq_limits']['blocked_rules']}")
        print(f"  unavailable {len(feats['unavailable'])} 条")
        print("  拒收：KB2 §8.3 断言层与报告层只覆盖 Scope View 触发门控样本，"
              "本方言无该槽位", file=sys.stderr)
        return 2

    # C3：规则表子集只在样本真能喂饱 §2.1 原始输入时才产假设；样本量侧车缺失时
    # 引擎按规则记 skip 而不是补默认 n_factor（rule_table.evidence_policy.sample_scale）。
    diag = engine.analyze(feats, meta=meta, source_tier=meta["source"]["tier"],
                          case_id=sid)
    contract_results = c3validate.validate(diag)
    diag["contract_checks"] = [c._asdict() for c in contract_results]
    io.open(os.path.join(outdir, "diagnosis.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(diag, ensure_ascii=False, indent=2) + "\n")

    checks = asrt.run(meta, feats, ingest, outdir,
                      {"n_columns": table.n_columns})
    report.write_report(os.path.join(outdir, "report.html"),
                        report.render(meta, feats, ingest, checks, diag))

    failed = [n for n, ok, _ in checks if not ok]
    contract_failed = [c.check_id for c in contract_results if not c.passed]
    print(f"样本包 {outdir}")
    print(f"  门控后 {meta['quality']['n_samples']} 行 @ "
          f"{meta['sample_rate_hz']:g} Hz（母本 {table.n_rows_raw} 行）")
    print(f"  canonical {meta['present_channels']} / extra {len(meta['extra_channels'])}")
    print(f"  blocked_rules {feats['freq_limits']['blocked_rules']}")
    print(f"  unavailable {len(feats['unavailable'])} 条")
    print(f"  归因：主假设 {diag['verdict']['primary']} · "
          f"overall_confidence {diag['verdict']['overall_confidence']} · "
          f"命中 {diag['audit']['rules_fired']} · 跳过 {len(diag['audit']['rules_skipped'])} 条")
    print(f"  断言 {len(checks) - len(failed)}/{len(checks)} 通过 · "
          f"C3 契约 {len(diag['contract_checks']) - len(contract_failed)}"
          f"/{len(diag['contract_checks'])} 通过")
    for n in failed:
        print(f"  FAIL {n}", file=sys.stderr)
    for cid in contract_failed:
        print(f"  C3 FAIL {cid}", file=sys.stderr)
    return 1 if (failed or contract_failed) else 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="axiscope", description="离线伺服波形接入与特征抽取")
    ap.add_argument("--in", dest="inp", required=True, help="厂商导出 CSV")
    ap.add_argument("--out", dest="outdir", required=True, help="样本包输出目录")
    ap.add_argument("--sample-id", default=None)
    args = ap.parse_args(argv)
    try:
        return run(args.inp, args.outdir, args.sample_id)
    except FileNotFoundError as exc:
        # 缺输入是**拒收**，不是崩溃：契约是「拒收即退 2」，
        # 抛栈会让调用方以为程序崩了（干净克隆里原始数据不在位，必踩）。
        print(f"拒收：输入文件不存在（{getattr(exc, 'filename', None) or exc}）", file=sys.stderr)
        return 2
    except (c1.PackError, features.FeatureError, ScopeFormatError) as exc:
        print(f"拒收：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())