"""C5 评测 runner：对 bench/cases.jsonl 的每个案例跑完整生产链路并算 C5 §3 的指标。

    PYTHONPATH=src PYTHONIOENCODING=utf-8 python bench/run_eval.py

产物（可重跑，同一输入 ⟹ 同一产物）：
  build/c5-eval/metrics.json     指标总表（按 split 分列 + 合计）
  build/c5-eval/per_case.json    逐案例明细
  build/c5-eval/diagnoses/<case_id>.json  每个案例的 C3 输出与契约检查
  build/c5-eval/run.log          本 runner 的完整 stdout（由 shell 重定向生成，见下）

    PYTHONPATH=src PYTHONIOENCODING=utf-8 python bench/run_eval.py \
        > build/c5-eval/run.log 2>&1

口径纪律：
* 命中率分母只收 `expected_verdict_class` 是**具体 slug** 且 `source_tier ∈ {T1-a, T2}` 的案例
  （C5 §3 / A-63：T1-b 一律不进 slug 分母）。
* 拒答正确率的分母是 `none_of_the_above` / `refuse_insufficient_data` / `co_occurrence_only`
  三类（C5 §3 + §9 结构性真空能力项的拒答案例）。
* 分母为 0 的指标一律打印「未测（分母 0）」并写明原因，**不填 0、不留空**。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import traceback
import unicodedata

BENCH = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BENCH)
for p in (os.path.join(REPO, "src"), BENCH):
    if p not in sys.path:
        sys.path.insert(0, p)

import casebuild as cb  # noqa: E402
from axiscope import c3validate, engine  # noqa: E402

CASES_JSONL = os.path.join(BENCH, "cases.jsonl")
HIDDEN_SHA = os.path.join(BENCH, "hidden.sha256")
PATTERNS_JSON = os.path.join(BENCH, "forbidden_patterns.json")
OUT = os.path.join(REPO, "build", "c5-eval")
DIAG_DIR = os.path.join(OUT, "diagnoses")

SLUGS = set(cb.__dict__.get("_SLUGS", set()))  # 由 main 注入
REFUSAL_CLASSES = {"none_of_the_above", "refuse_insufficient_data", "co_occurrence_only"}
HIT_DENOM_TIERS = {"T1-a", "T2"}


def load_rows() -> list[dict]:
    rows = []
    with io.open(CASES_JSONL, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_patterns() -> dict:
    with io.open(PATTERNS_JSON, encoding="utf-8") as fh:
        raw = json.load(fh)
    out = {}
    for tok, spec in raw.items():
        if tok.startswith("_"):
            continue
        out[tok] = [re.compile(p) for p in spec["patterns"]]
    return out


def narrative_strings(diag: dict) -> list[tuple[str, str]]:
    """参与禁语扫描的叙述性文本。**只扫叙述文本**，不扫 slug / 键名——
    `differential.not_evaluable[].fault_mode == "mechanical_thermal_drift"` 是登记，不是断言。"""
    out: list[tuple[str, str]] = []
    v = diag.get("verdict") or {}
    for k in ("summary", "confidence_note"):
        if v.get(k):
            out.append(("verdict." + k, v[k]))
    for i, h in enumerate(diag.get("hypotheses") or []):
        for k in ("narrative", "summary", "display_name"):
            if isinstance(h, dict) and h.get(k):
                out.append(("hypotheses[%d].%s" % (i, k), h[k]))
    audit = diag.get("audit") or {}
    for i, a in enumerate(audit.get("assumptions") or []):
        if a.get("statement"):
            out.append(("audit.assumptions[%d].statement" % i, a["statement"]))
    for i, e in enumerate(audit.get("external_ledger") or []):
        if e.get("note"):
            out.append(("audit.external_ledger[%d].note" % i, e["note"]))
    for i, c in enumerate(audit.get("human_review_checklist") or []):
        out.append(("audit.human_review_checklist[%d]" % i, str(c)))
    for i, n in enumerate(diag.get("next_data_to_collect") or []):
        for k in ("ask", "why"):
            if isinstance(n, dict) and n.get(k):
                out.append(("next_data_to_collect[%d].%s" % (i, k), n[k]))
    for i, val in enumerate(diag.get("validation") or []):
        for j, cv in enumerate((val.get("caveats") or [])):
            out.append(("validation[%d].caveats[%d]" % (i, j), str(cv)))
    saf = diag.get("safety") or {}
    if saf.get("disclaimer"):
        out.append(("safety.disclaimer", saf["disclaimer"]))
    return out


def scan_forbidden(diag: dict, tokens: list[str], patterns: dict) -> list[dict]:
    hits = []
    for field, text in narrative_strings(diag):
        for tok in tokens:
            for rx in patterns.get(tok, []):
                if rx.search(text):
                    hits.append({"token": tok, "field": field, "match": rx.pattern,
                                 "excerpt": text[:120]})
    return hits


def unsupported_success_claims(diag: dict) -> list[dict]:
    """C5 §3「无依据成功声明」：`expected_effect.basis == simulation_validated`
    却无对应 V* 记录，或 V* 的 fit_residual_pct > 25% 却未降级。"""
    bad = []
    hyp_recs = {}
    for h in diag.get("hypotheses") or []:
        if isinstance(h, dict) and h.get("recommendation"):
            hyp_recs[h.get("id")] = h["recommendation"]
    recs = []
    if isinstance(diag.get("recommendation"), dict):
        recs.append(("recommendation", diag["recommendation"]))
    for hid, rec in hyp_recs.items():
        recs.append(("hypotheses[%s].recommendation" % hid, rec))
    valid_ids = {v.get("id") for v in (diag.get("validation") or [])}
    for where, rec in recs:
        ee = rec.get("expected_effect") or {}
        if ee.get("basis") == "simulation_validated":
            vid = rec.get("validation_id")
            if not vid or vid not in valid_ids:
                bad.append({"kind": "simulation_validated_without_validation",
                            "where": where, "validation_id": vid})
    for v in diag.get("validation") or []:
        fr = (v.get("plant_fit") or {}).get("fit_residual_pct")
        if isinstance(fr, (int, float)) and fr > 25.0:
            downgraded = any("fragile" in str(x).lower() or "downgrade" in str(x).lower()
                             for x in (v.get("caveats") or []))
            if not downgraded:
                bad.append({"kind": "fit_residual_over_25_not_downgraded",
                            "where": "validation[%s]" % v.get("id"), "fit_residual_pct": fr})
    return bad


def check_evidence_accuracy(diag: dict, feats: dict) -> dict:
    """C5 §3「证据准确率」：每条 supporting_evidence 的 feature 路径能在 C2 JSON 里解析到，
    且 value 与之一致。结构上由 features/rules 只引用路径保证，这里是独立复算。"""
    checked = 0
    mismatched = []
    unresolved = []

    def resolve(node, parts):
        for part in parts:
            if node is None:
                return (False, None)
            if isinstance(node, list):
                idx = part
                try:
                    i = int(idx)
                except ValueError:
                    return (False, None)
                if i >= len(node):
                    return (False, None)
                node = node[i]
            elif isinstance(node, dict):
                if part not in node:
                    return (False, None)
                node = node[part]
            else:
                return (False, None)
        return (True, node)

    for h in diag.get("hypotheses") or []:
        for kind in ("supporting_evidence", "contradicting_evidence"):
            for i, e in enumerate((h.get(kind) or [])):
                path = e.get("feature")
                checked += 1
                parts = re.split(r"\.(?![^\[]*\])", path)
                parts = [p for chunk in parts for p in re.findall(r"[^\[\]]+|\[\d+\]", chunk)]
                ok, got = resolve(feats, parts)
                if not ok:
                    unresolved.append({"hypothesis": h.get("id"), "kind": kind, "i": i,
                                       "feature": path})
                    continue
                if isinstance(got, list):
                    got = got[0] if got else None
                if isinstance(got, (int, float)) and isinstance(e.get("value"), (int, float)):
                    if abs(float(got) - float(e["value"])) > 1e-9 * max(1.0, abs(float(got))):
                        mismatched.append({"hypothesis": h.get("id"), "kind": kind, "i": i,
                                           "feature": path, "declared": e.get("value"),
                                           "in_features": got})
    return {"checked": checked, "unresolved": unresolved, "value_mismatches": mismatched}


def dig_path(node, path: str):
    cur = node
    for part in re.findall(r"[^\[\].]+|\[\d+\]", path):
        if isinstance(part, str) and part.startswith("[") and part.endswith("]"):
            i = int(part[1:-1])
            if not isinstance(cur, list) or i >= len(cur):
                return (False, None)
            cur = cur[i]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return (False, None)
            cur = cur[part]
    return (True, cur)


def judge(row: dict, diag: dict, feats: dict) -> dict:
    """把一条案例的期望判定与实际输出对拍。返回每项检查的布尔与细节。"""
    exp = row["expected_verdict_class"]
    hyps = diag.get("hypotheses") or []
    verdict = diag.get("verdict") or {}
    diff = diag.get("differential") or {}
    ne = diff.get("not_evaluable") or []
    considered = set(diff.get("considered") or [])
    hyp_slugs = [h.get("fault_mode") for h in hyps]
    refused = (len(hyps) == 0) and verdict.get("primary") in (None, "") \
        and verdict.get("overall_confidence") in (None, "")
    actual_blocked_by = {r.get("blocked_by") for r in ne if r.get("blocked_by")}
    out = {
        "expected_verdict_class": exp,
        "actual_hypothesis_slugs": hyp_slugs,
        "actual_primary": verdict.get("primary"),
        "actual_overall_confidence": verdict.get("overall_confidence"),
        "refused": refused,
        "n_not_evaluable": len(ne),
        "n_distinct_blocked_by": len(actual_blocked_by),
        "actual_blocked_by": sorted(actual_blocked_by),
        "blocked_rules": list((diag.get("freq_limits") or {}).get("blocked_rules") or []),
    }
    # —— 管线缺陷：事实与登记不符时，「输出碰巧对」不等于「做对了」——
    defects = []
    if row["events_present"] and (feats.get("event_context") or {}).get("available") is not True:
        defects.append("events.jsonl 已落盘，但 features.event_context.available=false"
                       "（features.py 把 event_context 整块硬编码为不可用，C6 §1 未接入特征层）")
    if defects:
        out["pipeline_defects"] = defects
    else:
        out["pipeline_defects"] = []
    # —— Top-1 / Top-3（只对 slug 级 gold 且 T1-a/T2 计分）——
    if exp in SLUGS and row["source_tier"] in HIT_DENOM_TIERS:
        out["in_hit_denominator"] = True
        out["top1_hit"] = bool(hyps) and hyp_slugs[0] == exp
        out["top3_hit"] = exp in hyp_slugs[:3]
    else:
        out["in_hit_denominator"] = False
        out["top1_hit"] = None
        out["top3_hit"] = None
    # —— 拒答正确率 ——
    if exp in REFUSAL_CLASSES:
        out["in_refusal_denominator"] = True
        ok = refused
        if exp == "co_occurrence_only":
            fam = {r.get("family") for r in ne} | {r.get("fault_mode") for r in ne}
            ok = refused and any(f and f.startswith("software_induced") for f in fam | considered)
        out["refusal_correct"] = bool(ok)
        # 输出对但理由错（管线缺陷）⟹ 该条不算「做对了」，另列
        out["refusal_correct_strict"] = bool(ok) and not defects
    else:
        out["in_refusal_denominator"] = False
        out["refusal_correct"] = None
        out["refusal_correct_strict"] = None
    # —— expected_not_evaluable_min（KB8 §1.5）——
    out["not_evaluable_min_required"] = row["expected_not_evaluable_min"]
    out["not_evaluable_min_met"] = len(ne) >= row["expected_not_evaluable_min"]
    # —— expected_blocked_by：KB8 §1.5 要求的**具体** blocked_by 键是否真的登记了 ——
    want = set(row.get("expected_blocked_by") or [])
    out["expected_blocked_by"] = sorted(want)
    out["expected_blocked_by_covered"] = bool(want) and want.issubset(actual_blocked_by)
    out["unimplementable_blocked_by"] = list(row.get("unimplementable_blocked_by") or [])
    # —— 频带门禁：A-65 的正面红线（f_b < 2000 ⟹ blocked_rules 必须含 R-03/R-04）——
    if row["reliable_band_hz"] < 2000:
        br = set(out["blocked_rules"])
        out["band_gate_r03_r04_blocked"] = {"R-03", "R-04"}.issubset(br)
    else:
        out["band_gate_r03_r04_blocked"] = None
    return out


def ece(pairs: list[tuple[float, int]], n_bins: int = 10) -> float | None:
    """C5 §3 ECE：分桶 |acc_b − conf_b| 的样本量加权平均。pairs = [(confidence, correct01)]。"""
    if not pairs:
        return None
    tot = float(len(pairs))
    e = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        sub = [(c, y) for (c, y) in pairs if (lo <= c < hi or (b == n_bins - 1 and c <= hi))]
        if not sub:
            continue
        acc = sum(y for _, y in sub) / len(sub)
        conf = sum(c for c, _ in sub) / len(sub)
        e += (len(sub) / tot) * abs(acc - conf)
    return e


def fmt_pct(num: int, den: int) -> str:
    if den == 0:
        return "未测（分母 0）"
    return "%.1f%% (%d/%d)" % (100.0 * num / den, num, den)


def pad(text: str, width: int, align: str = "<") -> str:
    """按**显示宽度**补空格（CJK 记 2 列），否则终端里中文表格会错行。"""
    w = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(text))
    fill = " " * max(0, width - w)
    return fill + str(text) if align == ">" else str(text) + fill


def main() -> int:
    global SLUGS
    from axiscope.registration import LEAVES
    SLUGS = set(LEAVES)
    cb.assign_source_tier_and_origin()
    rows = load_rows()
    patterns = load_patterns()
    os.makedirs(DIAG_DIR, exist_ok=True)

    per_case = []
    executed = 0
    skipped = []

    for row in rows:
        cid = row["case_id"]
        pack_dir = os.path.join(cb.SAMPLES_DIR, cid)
        rec = {"case_id": cid, "source_tier": row["source_tier"], "split": row["split"],
               "present_channels": row["present_channels"],
               "fs_hz": row["fs_hz"], "reliable_band_hz": row["reliable_band_hz"],
               "counts_per_mm": row["counts_per_mm"],
               "expected_verdict_class": row["expected_verdict_class"],
               "injected_fault": row.get("injected_fault"),
               "blocked_by_distinct": None}
        try:
            # —— 完整生产链路重跑（不看 cases.jsonl 的真值；真值只在事后比对）——
            case = next(c for c in cb.CASES if c["case_id"] == cid)
            built = cb.materialize(case, pack_dir)
            meta, feats = built["meta"], built["features"]
            diag = engine.analyze(feats, meta=meta,
                                  source_tier=row["source_tier"], case_id=cid)
            checks = c3validate.validate(diag)
            diag["contract_checks"] = [c._asdict() for c in checks]
            diag["_provenance"] = {
                "source_csv": os.path.relpath(cb.SOURCE_CSV, REPO).replace("\\", "/"),
                "pack_sha256_kb8_1_4": row["sha256"],
                "features_sha256": row["features_sha256"],
            }
            with io.open(os.path.join(DIAG_DIR, cid + ".json"), "w", encoding="utf-8",
                         newline="\n") as fh:
                fh.write(json.dumps(diag, ensure_ascii=False, indent=2) + "\n")

            j = judge(row, diag, feats)
            ev = check_evidence_accuracy(diag, feats)
            forb = scan_forbidden(diag, row["forbidden_conclusions"], patterns)
            unsup = unsupported_success_claims(diag)
            rec.update(j)
            rec["executed"] = True
            rec["n_evidence_rows"] = ev["checked"]
            rec["evidence_unresolved"] = len(ev["unresolved"])
            rec["evidence_value_mismatches"] = len(ev["value_mismatches"])
            rec["forbidden_hits"] = forb
            rec["n_forbidden_hits"] = len(forb)
            rec["unsupported_success_claims"] = len(unsup)
            rec["unsupported_success_claim_detail"] = unsup
            rec["contract_checks_total"] = len(checks)
            rec["contract_checks_failed"] = [c.check_id for c in checks if not c.passed]
            rec["external_counts"] = (diag.get("audit") or {}).get("external_counts")
            rec["rules_fired"] = (diag.get("audit") or {}).get("rules_fired")
            rec["n_unavailable"] = len(feats.get("unavailable") or [])
            rec["traceable"] = bool(
                os.path.exists(os.path.join(DIAG_DIR, cid + ".json"))
                and (diag.get("audit") or {}).get("deterministic_core_hash")
                and isinstance(feats, dict) and feats.get("schema"))
            executed += 1
        except Exception as exc:                       # 单案例失败不进通过数（A-87）
            rec["executed"] = False
            rec["error"] = "%s: %s" % (type(exc).__name__, exc)
            rec["traceback"] = traceback.format_exc()
            skipped.append({"case_id": cid, "reason": rec["error"]})
        per_case.append(rec)

    # ------------------------------------------------------------------ 汇总
    def agg(sel):
        hit = [r for r in sel if r.get("in_hit_denominator")]
        ref = [r for r in sel if r.get("in_refusal_denominator")]
        pairs = []
        for r in hit:
            conf = r.get("actual_overall_confidence")
            if isinstance(conf, (int, float)):
                pairs.append((float(conf), 1 if r.get("top1_hit") else 0))
        ev_rows = sum(r.get("n_evidence_rows", 0) for r in sel)
        ev_bad = sum(r.get("evidence_unresolved", 0) + r.get("evidence_value_mismatches", 0)
                     for r in sel)
        return {
            "n_cases": len(sel),
            "top1_hits": sum(1 for r in hit if r.get("top1_hit")),
            "top3_hits": sum(1 for r in hit if r.get("top3_hit")),
            "hit_denominator": len(hit),
            "refusal_correct": sum(1 for r in ref if r.get("refusal_correct")),
            "refusal_correct_strict": sum(1 for r in ref if r.get("refusal_correct_strict")),
            "refusal_denominator": len(ref),
            "cases_with_pipeline_defects": sum(1 for r in sel if r.get("pipeline_defects")),
            "expected_blocked_by_covered": sum(1 for r in sel if r.get("expected_blocked_by_covered")),
            "expected_blocked_by_n": sum(1 for r in sel if r.get("expected_blocked_by")),
            "ece": ece(pairs),
            "ece_n": len(pairs),
            "evidence_rows_checked": ev_rows,
            "evidence_rows_bad": ev_bad,
            "forbidden_hits": sum(r.get("n_forbidden_hits", 0) for r in sel),
            "unsupported_success_claims": sum(r.get("unsupported_success_claims", 0)
                                              for r in sel),
            "not_evaluable_min_met": sum(1 for r in sel if r.get("not_evaluable_min_met")),
            "band_gate_ok": sum(1 for r in sel if r.get("band_gate_r03_r04_blocked") is True),
            "band_gate_n": sum(1 for r in sel if r.get("band_gate_r03_r04_blocked") is not None),
            "contract_checks_total": sum(r.get("contract_checks_total", 0) for r in sel),
            "contract_checks_failed": sum(len(r.get("contract_checks_failed", []) or [])
                                          for r in sel),
            "traceable": sum(1 for r in sel if r.get("traceable")),
        }

    done = [r for r in per_case if r.get("executed")]
    splits = {
        "dev": agg([r for r in done if r["split"] == "dev"]),
        "hidden": agg([r for r in done if r["split"] == "hidden"]),
        "all": agg(done),
    }
    by_tier = {}
    for tier in sorted({r["source_tier"] for r in per_case}):
        by_tier[tier] = agg([r for r in done if r["source_tier"] == tier])

    # ------------------------------------------------------------------ stdout
    P = print
    P("=" * 78)
    P("C5 评测 runner —— 实测输出（PYTHONPATH=src PYTHONIOENCODING=utf-8 python bench/run_eval.py）")
    P("=" * 78)
    P("")
    P("[0] 案例目录统计")
    P("    总案例数        : %d" % len(per_case))
    tier_counts = {}
    for r in per_case:
        tier_counts[r["source_tier"]] = tier_counts.get(r["source_tier"], 0) + 1
    P("    按 tier 分层    : %s" % ", ".join("%s=%d" % kv for kv in sorted(tier_counts.items())))
    slug_counts = {}
    for r in per_case:
        s = (r.get("injected_fault") or {}).get("kb0_slug") or "（无注入：健康对照）"
        slug_counts[s] = slug_counts.get(s, 0) + 1
    P("    按 slug 分布    :")
    for s, n in sorted(slug_counts.items()):
        P("        %s %d" % (pad(s, 54), n))
    P("    期望判定分布    :")
    vc = {}
    for r in per_case:
        vc[r["expected_verdict_class"]] = vc.get(r["expected_verdict_class"], 0) + 1
    for s, n in sorted(vc.items()):
        P("        %s %d" % (pad(s, 54), n))
    P("    执行 N / 跳过 M : 执行 %d / 跳过 %d" % (executed, len(skipped)))
    for s in skipped:
        P("        跳过 %s —— %s" % (s["case_id"], s["reason"]))
    P("")
    covered = {r["injected_fault"]["kb0_slug"] for r in per_case if r.get("injected_fault")}
    gaps = sorted(SLUGS - covered)
    P("    KB8 §2.3 空格清单（22 个 KB0 slug 中**没有**任何案例的 %d 个）：" % len(gaps))
    P("        —— 这些一律**不填凑数案例**，命中率分母因此缺这些 slug ——")
    for i in range(0, len(gaps), 3):
        P("        " + "  ".join(pad(s, 40) for s in gaps[i:i + 3]))
    P("    已有案例的 slug（%d 个）：%s" % (len(covered), ", ".join(sorted(covered))))
    P("    KB8 §6 规模下限 N=%d，本轮实际 %d，缺口 %d；**不缩表凑数、不改口径**。"
      % (120, len(per_case), 120 - len(per_case)))
    P("")

    P("[1] 案例执行分列（C5 §3「案例执行分列」行；A-87：跳过项不进通过数）")
    hdr = ("case_id", "split", "expected_verdict_class", "执行", "假设", "拒绝",
           "严格", "禁语", "blocked", "契约")
    P("    " + " ".join(pad(h, 30 if i == 2 else (24 if i == 0 else 8)) for i, h in enumerate(hdr)))
    for r in per_case:
        cells = (
            r["case_id"], r["split"], r["expected_verdict_class"],
            "是" if r.get("executed") else "否",
            "-" if not r.get("executed") else len(r.get("actual_hypothesis_slugs") or []),
            {True: "对", False: "错", None: "-"}.get(r.get("refusal_correct"), "-"),
            {True: "对", False: "错", None: "-"}.get(r.get("refusal_correct_strict"), "-"),
            r.get("n_forbidden_hits", "-"),
            "-" if not r.get("executed")
            else ("全覆盖" if r.get("expected_blocked_by_covered") else "缺键"),
            "%d/%d" % (r["contract_checks_total"] - len(r["contract_checks_failed"] or []),
                       r["contract_checks_total"]) if r.get("executed") else "-")
        P("    " + " ".join(pad(c, 30 if i == 2 else (24 if i == 0 else 8))
                            for i, c in enumerate(cells)))
    P("")
    P("    「严格」= 拒答结论对**且**登记的不可评估理由与样本事实一致；")
    P("    「blocked」= KB8 §1.5 要求的 blocked_by 键是否真的出现在 C3 的 not_evaluable 里。")
    P("")

    P("[2] C5 §3 指标（分母为 0 一律写「未测」并给原因，不填 0）")
    for name in ("dev", "hidden", "all"):
        a = splits[name]
        P("  --- split=%s（n=%d）---" % (name, a["n_cases"]))
        P("    Top-1 根因命中率 (T1-a+T2 slug 级) : %s" % fmt_pct(a["top1_hits"], a["hit_denominator"]))
        P("    Top-3 根因命中率 (T1-a+T2 slug 级) : %s" % fmt_pct(a["top3_hits"], a["hit_denominator"]))
        P("    机械↔电气二分类 (T1-b family 级)  : 未测（分母 0 —— 本轮无任何 T1-b 案例）")
        P("    拒答正确率                          : %s" % fmt_pct(a["refusal_correct"], a["refusal_denominator"]))
        P("    拒答正确率（严格）                  : %s  ← 输出对 **且** 理由与样本事实一致"
          % fmt_pct(a["refusal_correct_strict"], a["refusal_denominator"]))
        P("    带管线缺陷的案例                    : %d / %d" % (a["cases_with_pipeline_defects"], a["n_cases"]))
        P("    blocked_by 义务全覆盖              : %s" % fmt_pct(
            a["expected_blocked_by_covered"], a["expected_blocked_by_n"]))
        if a["ece"] is None:
            P("    置信度校准误差 ECE                 : 未测（分母 %d —— 没有任何案例产出可评分假设与置信度）" % a["ece_n"])
        else:
            P("    置信度校准误差 ECE                 : %.4f（n=%d，目标 ≤0.10）" % (a["ece"], a["ece_n"]))
        if a["evidence_rows_checked"] == 0:
            P("    证据准确率                         : 未测（分母 0 —— 0 条 supporting_evidence 产出，"
              "该指标在本轮是空集，不是 100%）")
        else:
            P("    证据准确率                         : %s" % fmt_pct(
                a["evidence_rows_checked"] - a["evidence_rows_bad"], a["evidence_rows_checked"]))
        P("    无依据成功声明                     : %d 次（硬门禁 = 0）" % a["unsupported_success_claims"])
        P("    禁语违例                           : %d 次（硬门禁 = 0）" % a["forbidden_hits"])
        P("    可追溯率                           : %s" % fmt_pct(a["traceable"], a["n_cases"]))
        P("    C3 契约检查                        : %d/%d 通过" % (
            a["contract_checks_total"] - a["contract_checks_failed"], a["contract_checks_total"]))
        P("")

    P("[3] 纪律行逐项（KB8 §1.5 / A-65 正面红线）")
    for r in done:
        bg = r.get("band_gate_r03_r04_blocked")
        bg_txt = "未适用" if bg is None else ("达标" if bg else "**未达标**")
        P("    %-26s f_b=%5.0f Hz  not_evaluable %2d 行（要求 ≥%d → %s）  "
          "R-03/R-04 进 blocked_rules → %s  blocked_rules=%s" % (
              r["case_id"], r["reliable_band_hz"], r["n_not_evaluable"],
              r["not_evaluable_min_required"],
              "达标" if r["not_evaluable_min_met"] else "**未达标**",
              bg_txt, r["blocked_rules"]))
    P("")
    P("    —— KB8 §1.5「具体不可评估原因」的 blocked_by 键覆盖情况 ——")
    for r in done:
        P("    %-26s 期望 %s" % (r["case_id"], r.get("expected_blocked_by") or []))
        P("    %-26s 实际 %s  →  %s" % ("", r.get("actual_blocked_by") or [],
                                       "全覆盖" if r.get("expected_blocked_by_covered")
                                       else "**缺键**"))
        if r.get("unimplementable_blocked_by"):
            P("    %-26s 登记层**无键**、因此 C3 根本不可能登记的原因：%s" % (
                "", r["unimplementable_blocked_by"]))
    P("")
    P("    —— 管线缺陷（输出碰巧对 ≠ 做对了）——")
    anydef = [r for r in done if r.get("pipeline_defects")]
    if not anydef:
        P("    无")
    for r in anydef:
        for d in r["pipeline_defects"]:
            P("    %-26s %s" % (r["case_id"], d))
    P("")

    P("[4] 外部核对计数 external_counts（C5 §3；k=0 时叙述封顶「样板就绪，签名与位号未经外部核对」）")
    ec = {"verified": 0, "total": 0}
    for r in done:
        e = r.get("external_counts") or {}
        ec["verified"] += int(e.get("verified") or 0)
        ec["total"] += int(e.get("total") or 0)
    P("    audit.external_counts = verified %d / total %d" % (ec["verified"], ec["total"]))
    P("")

    P("[5] 人工基线（C5 §5）")
    P("    human_baseline_labels 全部为 {\"status\":\"pending\"}；未招募标注者 ⟹ 无人工基线，")
    P("    绝对数值不可横向比较（C5 §5 降级方案，此为当前默认状态）。")
    P("")

    P("[6] 同源限制（A-88）")
    P("    本轮 %d/%d 案例的真值是**本项目自己注入**的（bench/casebuild.py 里的注入数学），" %
      (sum(1 for r in per_case if r.get("injected_fault")), len(per_case)))
    P("    检出方是本项目自己的规则 ⟹ 对「规则阈值选得对不对」**零证明力**，只能证明")
    P("    「判据能检出按我们设计植入的误差」。唯一非同源的真值是 CTL-0001（DaRUS 受试")
    P("    对象健康、非故障数据），它支撑的是**拒答纪律**，不支撑任何命中率。")
    P("    拒答正确率的高分尤其要打折：拒答的**内容**正确只说明系统不敢下结论，")
    P("    其**理由**是否登记对，由「拒答正确率（严格）」与 [3] 的 blocked_by 覆盖行单列。")
    P("")

    # ------------------------------------------------------------------ 落盘
    os.makedirs(OUT, exist_ok=True)
    payload = {"splits": splits, "by_tier": by_tier, "executed": executed,
               "skipped": len(skipped), "skip_detail": skipped,
               "kb8_quota_N": 120, "n_cases_actual": len(per_case)}
    with io.open(os.path.join(OUT, "metrics.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    with io.open(os.path.join(OUT, "per_case.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(per_case, ensure_ascii=False, indent=2) + "\n")

    P("[7] 产物")
    for f in ("metrics.json", "per_case.json", "diagnoses/"):
        p = os.path.join(OUT, f)
        n = (len(os.listdir(p)) if os.path.isdir(p)
             else (sum(1 for _ in io.open(p, encoding="utf-8")) if f.endswith(".jsonl") else 1))
        P("    build/c5-eval/%-18s %s" % (f, ("%d 个文件" % n) if os.path.isdir(p) else "已写"))
    P("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())