"""C3 诊断输出契约的机器可判定校验器（不可协商规则 1–21 + KB4 §0 不变式）。

纪律：`validate` 只做结构 / 数值 / 措辞判定，不调 LLM、不联网；诊断以 dict 传入。
唯一的例外是规则 17/18：它们要把契约里声明的**仓内产物**（外置台账、`examples/` 特征快照）
解析出来核对，这正是「断言须挂仓内可重跑产物」（KB0 §6 检查 27）的落法。
规则 3/15 的 confidence 复算一律走 `confidence.py` 的 §2.1/§2.2
**权威实现**（`evidence_strength` / `aggregate` / `check_refutation`），从报告的**原始证据字段**
（`feature`/`value`/`operator`/`threshold`/`n`/`n_ref`/`conf`/`freq_hz`/`band_floor_hz`）独立复算，
而不是把报告自报的 `strength` 当既成事实重新聚合——那样只能复述报告的自洽、抓不出报告本身
与 §2.1 公式不符的缺陷（见 `_recompute_detail`）。
"""
from __future__ import annotations

import json
import os
from typing import NamedTuple

from . import assertions

try:  # 权威 KB4 §2 算术层（规则 3/15 复算的唯一口径）
    from . import confidence as _conf
except ImportError:  # pragma: no cover - 平铺导入回退
    import confidence as _conf  # type: ignore

try:  # 规则 19：`audit.assumptions` 的锚定词表（与 C1 接入层同源）
    from .anchors import anchor_kind
except ImportError:  # pragma: no cover - 平铺导入回退
    from anchors import anchor_kind  # type: ignore

try:  # 规则 21：哈希核的唯一落点（与 `engine` 共用同一份实现，规则 21 不许两侧各自发明）
    from . import core_hash as _core_hash
except ImportError:  # pragma: no cover - 平铺导入回退
    import core_hash as _core_hash  # type: ignore

# ---- 权威 slug（KB0 §2 全量 22 个）----
MECHANICAL_SLUGS = {
    "mechanical_resonance", "mechanical_backlash", "mechanical_friction_stiction",
    "mechanical_crawling", "mechanical_encoder_periodic_error", "mechanical_loose_structure",
    "mechanical_thermal_drift", "mechanical_double_inertia",
}
ELECTRICAL_SLUGS = {
    "electrical_current_loop_bandwidth", "electrical_velocity_pi_detune",
    "electrical_position_pi_detune", "electrical_feedforward_mismatch",
    "electrical_torque_ripple", "electrical_motor_heating", "electrical_resolution_quantization",
}
SOFTWARE_SLUGS = {
    "software_induced_host_thread_jitter", "software_induced_interp_buffer_underrun",
    "software_induced_bus_cycle_miss", "software_induced_late_vision_result",
    "software_induced_pulse_eq_overwritten", "software_induced_settle_window_too_short",
    "software_induced_polling_latency",
}
FAULT_MODE_SLUGS = MECHANICAL_SLUGS | ELECTRICAL_SLUGS | SOFTWARE_SLUGS
FAMILY_LABELS = {"mechanical", "electrical", "software_induced_error"}

# ---- 门禁 / 边规则（KB4 §0 INV-16 / C3 规则 11，family: null，永不产叶）----
GATE_RULE_IDS = {
    "R-25", "R-26", "R-27", "R-28", "R-29", "R-30",  # KB3
    "R-37", "R-49", "R-50",                          # KB6
}

# ---- 反证扣分档位（KB4 §2.4 v_j，离散，penalty 只能是其一）----
PENALTY_TIERS = {0.20, 0.10, 0.05, 0.00}

BASIS_VALUES = {"simulation_validated", "rule_heuristic", "unverified"}
EXTERNAL_REFERENCES = {"memory", "public-doc", "official-artifact", "vendor_reply"}
VERIFIED_BY = {"self", "third_party_report"}

# ---- 规则 14 / INV-13：强措辞词表（模块常量，可审计）----
STRONG_CLAIM_PHRASES = (
    "已核对", "已验证", "现场确认", "手册原文确认", "实测通过",
    "已经核对", "经过核对", "已实测", "实测确认", "已现场",
)
# ---- 规则 9 / INV-11 / INV-15：把"看不见"写成"没有"的禁用措辞 ----
UNOBSERVED_PHRASES = (
    "未发现", "没有找到", "无异常", "未检出",
    "无热漂移", "未发现谐振", "未发现共振", "带宽充足",
)

# ---- 规则 16 / A-73：blocked_by 稳定键名词表 ----
# 锚定来源：C1 通道清单（assertions.C1_VOCAB）、C6 文件清单（events.jsonl/calibration.jsonl）、
# KB3 R-25/R-30 的 band_gate / sync_unverified。契约未给封闭清单，此处取最保守的可枚举集。
# 通道名一律取 assertions.C1_VOCAB（C1 的唯一权威清单），本模块不再另抄一份——
# 两处各抄一遍时 C1 加通道不会同步，闭集就会悄悄漏键。
_BLOCKED_BY_CHANNEL = {f"absent_{c}_channel" for c in assertions.C1_VOCAB}
_BLOCKED_BY_FILE = {"absent_events_jsonl", "absent_calibration_jsonl"}
_BLOCKED_BY_OTHER = {
    "band_gate_fs_1k", "band_gate_pass_channel_gate_fail", "sync_unverified",
    "absent_cold_warm_pair", "absent_step_labels", "absent_recipe",
    "absent_reverse_segment", "absent_motor_rev_counts",
    # A-97（无 counts 刻度 ⟹ 绝对阈值不可比）/ A-106（未做原点对齐 ⟹ 分歧幅值不可比）
    # A-105 ④（未做列间恒等式核对 ⟹ 独立测量数不可信，互证类结论不可评估）
    "absent_counts_scale", "absent_datum_alignment", "derived_column_unchecked",
}
ALLOWED_BLOCKED_BY = _BLOCKED_BY_CHANNEL | _BLOCKED_BY_FILE | _BLOCKED_BY_OTHER

# 第二个名字（unverified_signature / extraction）不得进 JSON（A-54 单一名字律）
FORBIDDEN_EXTERNAL_KEYS = {"unverified_signature", "extraction", "clause_or_line",
                           "model_source", "model_version"}

# 规则 3 / 15 重算容差（KB4 §2.2 常数）
W_SMAX, W_SREST = 0.55, 0.45
ACON_CAP = 0.5
DEDUCT_PER_REASON = 0.05
MAX_REASONS = 4
TOL = 0.011
# 单条 strength 的复算容差（与 confidence.py 的 §2.1 复算比对，序列化层为 2 位小数）
STRENGTH_TOL = 0.011
# §2.1(c) 样本量因子的文档下限（n = n_ref 时）；低于它 ⟹ 该 strength 结构上不可能由 §2.1 复现
N_FACTOR_FLOOR = _conf.N_FACTOR_AT_REF

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Check(NamedTuple):
    check_id: str
    passed: bool
    detail: str


class ValidationError(Exception):
    pass


class RefuseReportError(ValidationError):
    """规则 14 / INV-13 的专用拒绝：措辞越级不是可降级 disclaimer，而是拒绝出报告。"""


def validate(diagnosis: dict, repo_root: str = REPO_ROOT) -> list[Check]:
    checks: list[Check] = []

    def chk(cid: str, ok: bool, detail: str) -> None:
        checks.append(Check(cid, bool(ok), detail))

    hypotheses = diagnosis.get("hypotheses") or []
    differential = diagnosis.get("differential") or {}
    considered = differential.get("considered") or []
    not_evaluable = differential.get("not_evaluable") or []
    verdict = diagnosis.get("verdict") or {}
    audit = diagnosis.get("audit") or {}
    safety = diagnosis.get("safety") or {}

    blocked_rules = _as_set((diagnosis.get("freq_limits") or {}).get("blocked_rules"))
    unavailable_paths = {str(u.get("feature")) for u in _as_list(diagnosis.get("unavailable"))}
    freq_ctx = _confidence_ctx(diagnosis)

    # ---- 规则 1 + 13 + INV-10：每条假设 ≥2 条支持证据，且证据字段齐全、strength 必填数值 ----
    for h in hypotheses:
        ev = _as_list(h.get("supporting_evidence"))
        hid = h.get("id", "?")
        strong_ok = [e for e in ev if isinstance(e.get("strength"), (int, float)) and not isinstance(e.get("strength"), bool)]
        chk(f"C3-R01/{hid}", len(ev) >= 2,
            f"{hid} 仅 {len(ev)} 条 supporting_evidence，<2 是结构违规，须降级到 considered（规则 1 / INV-10）")
        missing = [i for i, e in enumerate(ev)
                   if not (e.get("feature") and e.get("rule_id") and e.get("source") and "value" in e)]
        chk(f"C3-R01-fields/{hid}", not missing,
            f"{hid} 缺『特征路径+实测值+规则ID+出处』的证据下标={missing}（规则 1）")
        chk(f"C3-R13-strength/{hid}", len(strong_ok) == len(ev),
            f"{hid} strength 必须为必填数值，不得用文字凑数（规则 13）")
        # INV-4：null 不得作为支持证据的值
        nulls = [i for i, e in enumerate(ev) if e.get("value") is None]
        chk(f"INV-4/{hid}", not nulls, f"{hid} 支持证据值为 null 不得立假设（INV-4 null≠false≠0）下标={nulls}")

        # ---- 规则 2：contradicting_evidence 必须显式填写（可为空数组）----
        chk(f"C3-R02/{hid}", "contradicting_evidence" in h,
            f"{hid} 必须显式给出 contradicting_evidence（哪怕空数组）（规则 2）")

        # ---- 规则 15 / INV-? ：每条反证必须同时带 rho_prime 与 penalty，penalty 是 rho_prime 的函数 ----
        for j, ce in enumerate(_as_list(h.get("contradicting_evidence"))):
            chk(f"C3-R15/{hid}[{j}]", "rho_prime" in ce and "penalty" in ce,
                f"{hid} 反证[{j}] 必须同时带 rho_prime 与 penalty（规则 15）")
            rho, pen = ce.get("rho_prime"), ce.get("penalty")
            chk(f"C3-R15-tier/{hid}[{j}]", pen in PENALTY_TIERS,
                f"{hid} 反证[{j}] penalty={pen!r} 不在离散档位 {sorted(PENALTY_TIERS)}（规则 15 / KB4 §2.4）")
            chk(f"C3-R15-fn/{hid}[{j}]", _penalty_consistent(rho, pen),
                f"{hid} 反证[{j}] penalty={pen!r} 与 rho_prime={rho!r} 的区间不符（规则 15：penalty 须是 rho_prime 的函数）")

        # ---- 规则 10：fault_mode 与 ruled_out_alternatives[].fault_mode 必须是 KB0 §2 slug ----
        chk(f"C3-R10/{hid}", h.get("fault_mode") in FAULT_MODE_SLUGS,
            f"{hid}.fault_mode={h.get('fault_mode')!r} 不是 KB0 §2 的 22 个 slug（规则 10，显示名禁入）")
        for k, alt in enumerate(_as_list(h.get("ruled_out_alternatives"))):
            chk(f"C3-R10-alt/{hid}[{k}]", alt.get("fault_mode") in FAULT_MODE_SLUGS,
                f"{hid}.ruled_out_alternatives[{k}].fault_mode={alt.get('fault_mode')!r} 不是 KB0 §2 slug（规则 10）")

        # ---- 规则 11 + INV-16：门禁/边规则永不作为 fault_mode 或产出假设 ----
        chk(f"C3-R11/{hid}", h.get("fault_mode") not in GATE_RULE_IDS,
            f"{hid} 以门禁/边规则 {h.get('fault_mode')!r} 作为假设（规则 11 / INV-16：family:null 只产登记义务）")
        gate_backed = [i for i, e in enumerate(ev) if e.get("rule_id") in GATE_RULE_IDS]
        chk(f"INV-16/{hid}", not gate_backed,
            f"{hid} 的门/边规则 ID 出现在支持证据下标={gate_backed}，不得据此产出假设（INV-16）")

        rec = h.get("recommendation") or {}

        # ---- 规则 5：confidence<0.6 ⟹ next_data_to_collect 非空且每条有 ask/why/unlocks ----
        conf = h.get("confidence")
        ndc = _as_list(h.get("next_data_to_collect"))
        if isinstance(conf, (int, float)) and conf < 0.6:
            chk(f"C3-R05/{hid}", len(ndc) > 0,
                f"{hid} confidence={conf}<0.6 时 next_data_to_collect 不得为空（规则 5）")
        ndc_bad = [i for i, d in enumerate(ndc) if not (d.get("ask") and d.get("why") and d.get("unlocks"))]
        chk(f"C3-R05-struct/{hid}", not ndc_bad,
            f"{hid} next_data_to_collect 缺 ask/why/unlocks 的下标={ndc_bad}（规则 5）")

        # ---- 规则 3 / 13 / 15：confidence 与每条 strength 必须由原始证据经 §2.1/§2.2 独立复算 ----
        det = _recompute_detail(h, freq_ctx)
        for i, msg in det.strength_violations:
            chk(f"C3-R15-strength/{hid}[{i}]", False, msg)
        for j, msg in det.refutation_violations:
            chk(f"C3-R15-refut/{hid}[{j}]", False, msg)
        if det.c is not None and isinstance(conf, (int, float)) and not isinstance(conf, bool):
            chk(f"C3-R03-recompute/{hid}", abs(round(det.c, 2) - conf) <= TOL,
                f"{hid} confidence={conf} 与按 §2.1/§2.2 从原始证据独立复算的 C={round(det.c, 4)} 不符"
                f"（规则 3/15：不得手填、不得自报 strength 复述）")
        elif det.gap is not None:
            # 复算所需的原始字段不足：显式标注「不可复算，需补字段」，不冒充通过、也不臆造可算值。
            chk(f"C3-R15-recompute-gap/{hid}", True, f"{hid} {det.gap}")

        # ---- severity / confidence 必填数值（规则 13）----
        chk(f"C3-R13-severity/{hid}", isinstance(h.get("severity"), (int, float)) and not isinstance(h.get("severity"), bool),
            f"{hid}.severity 必填确定性数值（规则 13），实得={h.get('severity')!r}")

        # ---- INV-9 / CAP-1：依赖 bandwidth.* 的结论恒 ≤0.6，basis 不得 simulation_validated ----
        bw_chain = [i for i, e in enumerate(ev) if str(e.get("feature", "")).startswith("bandwidth")
                    or "bandwidth" in str(e.get("feature", ""))]
        if bw_chain:
            chk(f"INV-9/{hid}", isinstance(conf, (int, float)) and conf <= 0.6 + 1e-9,
                f"{hid} 支持链含 bandwidth.* 但 confidence={conf}>0.6（INV-9/CAP-1 封顶）")
            if (rec.get("expected_effect") or {}).get("basis") == "simulation_validated":
                chk(f"INV-9-basis/{hid}", False,
                    f"{hid} bandwidth 依赖链上 basis 不得为 simulation_validated（INV-9）")

        # ---- INV-1 / CAP-5：blocked_rules 或 unavailable 的特征/规则不得立假设 ----
        for i, e in enumerate(ev):
            rid = str(e.get("rule_id"))
            feat = str(e.get("feature"))
            chk(f"CAP-5-rule/{hid}[{i}]", rid not in blocked_rules,
                f"{hid} 证据[{i}] rule_id={rid} 命中 freq_limits.blocked_rules，不得支持假设（INV-1/CAP-5；#-后缀按独立 id 计）")
            chk(f"CAP-5-feat/{hid}[{i}]", feat not in unavailable_paths,
                f"{hid} 证据[{i}] feature={feat} 在 unavailable 内，不得支持假设（INV-1/CAP-5）")

    # ---- 规则 4（顶层遍历 recommendation）----
    for h in hypotheses:
        rec = h.get("recommendation")
        if not rec:
            continue
        ee = rec.get("expected_effect")
        action_id = rec.get("action_id")
        if ee is not None:
            basis = ee.get("basis")
            chk(f"C3-R04/{h.get('id')}", basis in BASIS_VALUES,
                f"{h.get('id')} expected_effect.basis={basis!r} 非三合法值之一（规则 4）")
            if basis == "simulation_validated":
                found = _validation_matches(diagnosis, action_id, ee.get("validation_id"))
                chk(f"C3-R04-sim/{h.get('id')}", found,
                    f"{h.get('id')} basis=simulation_validated 但无同 action_id/validation_id 的 validation[] 记录（规则 4）")
            if basis == "unverified":
                nums = _has_numbers(ee)
                chk(f"C3-R04-unver/{h.get('id')}", not nums,
                    f"{h.get('id')} basis=unverified 却携带数字 {nums}（规则 4：unverified 只给方向）")

    # ---- INV-5 / INV-6 / CAP-2：因果开关 / 事件可用性 ----
    # `inputs.event_context_available` 是**契约示例**声明前提的位置（A-99 ①）：引擎产出的报告
    # 直接带 `event_context` 块，示例没有，若只认后者，示例里那句前提就只是一句装饰。
    event_ctx = diagnosis.get("event_context") or {}
    permitted = diagnosis.get("causal_claims_permitted", event_ctx.get("causal_claims_permitted"))
    available = event_ctx.get("available",
                              (diagnosis.get("inputs") or {}).get("event_context_available",
                                                                  diagnosis.get("event_context_available")))
    sw_hyps = [h.get("id") for h in hypotheses if str(h.get("fault_mode", "")).startswith("software_induced_")]
    if permitted is False:
        chk(f"INV-5/{sw_hyps}", not sw_hyps,
            f"causal_claims_permitted=false 时仍有 software_induced 假设={sw_hyps}（INV-5/CAP-2）")
    if available is False:
        chk(f"INV-6/{sw_hyps}", not sw_hyps,
            f"event_context.available=false 时仍有 software_induced 假设={sw_hyps}（INV-6）")
        registered = _software_registered_not_evaluable(not_evaluable)
        chk(f"INV-6-reg/{sw_hyps}", registered,
            f"event_context.available=false 须把软件族逐条登记 not_evaluable（INV-6/R-30）")

    # ---- 规则 18（A-99 ③）：示例声明的特征快照必须与 premises 判定同构 ----
    _check_snapshot_premises(diagnosis, repo_root, chk)

    # ---- 规则 19（#25）：audit.assumptions 的元素形状 ----
    _check_assumption_rows(audit, chk)

    # ---- 规则 20（A-107 ③）：rank 序必须等于 KB4 §2.9 字典序 ----
    _check_rank_monotonic(diagnosis, chk)

    # ---- 规则 21（#43 后半）：确定性核心哈希的形态与复算 ----
    _check_core_hash(diagnosis, chk)

    # ---- 规则 8：三方归因族必须同时出现 ----
    families = _families_present(hypotheses, considered, not_evaluable)
    chk("C3-R08", {"mechanical", "electrical", "software_induced"} <= families,
        f"三族未同时出现，缺失={sorted({'mechanical', 'electrical', 'software_induced'} - families)}（规则 8：缺任一族为设计缺陷）")

    # ---- 规则 10/16 + INV-16：not_evaluable 键式与 blocked_by ----
    chk("C3-R09-empty", _not_evaluable_ok(diagnosis, not_evaluable),
        "存在缺失通道/阻塞判据却 not_evaluable 为空——沉默让报告比实际更有把握（规则 9 / INV-11）")
    seen_keys: set[str] = set()
    for i, ne in enumerate(not_evaluable):
        has_fault = "fault_mode" in ne and ne.get("fault_mode") is not None
        has_family = "family" in ne and ne.get("family") is not None
        # 门/拒答行（family:null，如 CP-11）可两者皆 null，但必须带 rule_id 表明登记义务来源
        gate_row = (not has_fault) and (not has_family) and bool(ne.get("rule_id"))
        chk(f"C3-R11-ne[{i}]", (has_fault ^ has_family) or gate_row,
            f"not_evaluable[{i}] 须二选一给 fault_mode(slug)/family，或作为门/拒答行带 rule_id，实得={ne!r}（INV-16 键式）")
        if has_fault:
            chk(f"INV-16-nofam[{i}]", ne.get("fault_mode") != "software_induced_error",
                f"not_evaluable[{i}] 用 fault_mode 键放族级标签 software_induced_error（A-18/INV-16：禁入 fault_mode，须用 family 键）")
        chk(f"C3-R10-ne[{i}]", (not has_fault) or ne.get("fault_mode") in FAULT_MODE_SLUGS,
            f"not_evaluable[{i}].fault_mode={ne.get('fault_mode')!r} 不是 KB0 §2 slug（规则 10）")
        bk = ne.get("blocked_by")
        chk(f"C3-R16-bk[{i}]", bool(bk), f"not_evaluable[{i}] 缺 blocked_by 稳定键名（规则 16 / A-73）")
        chk(f"C3-R16-vocab[{i}]", bk is None or bk in ALLOWED_BLOCKED_BY,
            f"not_evaluable[{i}].blocked_by={bk!r} 不在 C1/C2 通道与文件清单锚定的键表内（规则 16：不许自由造）")
        if bk:
            seen_keys.add(bk)

    # ---- 规则 16 / A-73：overall_confidence 的缺席扣减按去重 blocked_by 个数，族级同源只计一次 ----
    primary = verdict.get("primary")
    overall = verdict.get("overall_confidence")
    c_primary = _primary_recomputed(hypotheses, primary, freq_ctx)
    distinct = min(MAX_REASONS, len(seen_keys))
    if c_primary is not None and isinstance(overall, (int, float)):
        exp = c_primary * (1 - DEDUCT_PER_REASON * distinct)
        chk("C3-R16-overall", abs(round(exp, 2) - overall) <= TOL,
            f"overall_confidence={overall} 与 C(H_primary)×(1−0.05×min(4,{distinct}))={round(exp, 4)} 不符（规则 16：按去重原因数，非行数）")

    # ---- 规则 6 + INV-12：不写设备 ----
    chk("C3-R06-writes", safety.get("writes_to_device") is False,
        f"safety.writes_to_device={safety.get('writes_to_device')!r} 必须恒为 false（规则 6 / INV-12）")
    chk("C3-R06-approval", safety.get("requires_human_approval") is True,
        f"safety.requires_human_approval={safety.get('requires_human_approval')!r} 必须恒为 true（规则 6 / INV-12）")

    # ---- 规则 7：verdict.summary 信息量下限（仅在给出了阳性结论时适用；规则 12 的诚实真空无阳性结论可要求）----
    summary = str(verdict.get("summary", ""))
    if hypotheses:
        chk("C3-R07-info", _summary_has_info(summary),
            f"verdict.summary 信息量不足（规则 7：须含频点/时间窗/量级+建议动作+预期效果依据；禁无信息表述）")
    else:
        chk("C3-R07-info", True, "无阳性假设（规则 12 诚实真空），summary 信息量下限不适用")

    # ---- 规则 11 + INV-16：门/边规则只能落在 rules_fired / not_evaluable，不得作为假设的支持链 ----
    hyp_rule_ids = {str(e.get("rule_id")) for h in hypotheses for e in _as_list(h.get("supporting_evidence"))}
    gate_in_hyp = GATE_RULE_IDS & hyp_rule_ids
    chk("INV-16-notleaf", not gate_in_hyp,
        f"门/边规则 {sorted(gate_in_hyp)} 出现在假设支持链，应只在 rules_fired/not_evaluable（INV-16）")

    # ---- 规则 9 / INV-11 / INV-15：叙述层无"未发现"式表述 ----
    offending = _scan_unobserved(diagnosis)
    chk("INV-11-wording", not offending,
        f"叙述出现『未发现/无异常/未检出』式措辞={offending}，不可观测须写成 not_evaluable 条目（规则 9 / INV-11）")

    # ---- 规则 14 / INV-13：措辞不得强于 source_tier —— 越级即拒绝出报告 ----
    refuse = _check_wording_vs_tier(diagnosis)
    if refuse:
        chk("C3-R14-REFUSE", False,
            f"措辞越级（强断言而 source_tier<T1 或台账缺行按 T3）={refuse} —— 拒绝生成报告，非降级 disclaimer（规则 14 / INV-13）")
    else:
        chk("C3-R14-REFUSE", True, "叙述层措辞未越过 source_tier（规则 14 / INV-13）")

    # ---- 规则 17 / A-88/A-89：外部核对台账 ----
    _check_external_ledger(diagnosis, repo_root, chk)

    return checks


# ---------------------------------------------------------------- helpers

def assert_ok(diagnosis: dict, repo_root: str = REPO_ROOT) -> None:
    checks = validate(diagnosis, repo_root)
    refuse = [c for c in checks if not c.passed and c.check_id.startswith("C3-R14-REFUSE")]
    if refuse:
        raise RefuseReportError("\n".join(f"[{c.check_id}] {c.detail}" for c in refuse))
    failed = [c for c in checks if not c.passed]
    if failed:
        raise ValidationError("\n".join(f"[{c.check_id}] {c.detail}" for c in failed))


def _as_list(x) -> list:
    return x if isinstance(x, list) else []


def _as_set(x) -> set:
    return {str(v) for v in x} if isinstance(x, list) else set()


def _penalty_consistent(rho, pen) -> bool:
    if pen not in PENALTY_TIERS:
        return False
    if pen == 0.00:
        return rho is None  # 0.00 只在依赖为 null（INV-4）时合法
    if not isinstance(rho, (int, float)) or isinstance(rho, bool):
        return False
    if rho >= 2:
        return pen == 0.20
    if rho >= 1:
        return pen == 0.10
    return pen == 0.05


class RecomputeResult(NamedTuple):
    """规则 3/15 复算的三态输出（绝不返回『靠自报 strength 聚合』的伪复算值）。

    - c：仅当**全部**支持证据都能由原始字段独立复算、且 `freq_limits` 齐备时，才是 §2.2 的 C；否则 None。
    - strength_violations：[(证据下标, 说明)] —— 声明 strength 与 §2.1 复算不符 / 不可复现 / 规则未命中。
    - refutation_violations：[(反证下标, 说明)] —— penalty 与自身重算 ρ′ 的档位不符（§2.4）。
    - gap：字段不足以复算时的显式标签「不可复算，需补字段」；None 表示证据侧全部可复算。
    """
    c: "float | None"
    strength_violations: list
    refutation_violations: list
    gap: "str | None"


def _op_of(e: dict):
    return e.get("operator") or e.get("op")


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _confidence_ctx(diagnosis: dict):
    fl = diagnosis.get("freq_limits") or {}
    fs = fl.get("fs_hz")
    rb = fl.get("reliable_band_hz")
    if not _is_num(fs) or not _is_num(rb):
        return None
    nyq = fl.get("nyquist_hz")
    try:
        return _conf.FrequencyContext(float(fs), float(rb),
                                      float(nyq) if _is_num(nyq) else None)
    except Exception:
        return None


def _recompute_detail(h: dict, ctx) -> RecomputeResult:
    """从报告的原始证据字段独立复算，不信自报 strength；见 `RecomputeResult`。"""
    hid = str(h.get("id", "?"))
    strength_violations: list = []
    refutation_violations: list = []
    gap_fields: dict = {}
    recomputed_evidence: list = []
    full_recomputable = True

    for i, e in enumerate(_as_list(h.get("supporting_evidence"))):
        feature = str(e.get("feature") or "")
        op = _op_of(e)
        value = e.get("value")
        threshold = e.get("threshold")
        eps = e.get("eps")
        conf = e.get("conf", e.get("confidence"))
        n = e.get("n")
        n_ref = e.get("n_ref")
        freq_hz = e.get("freq_hz")
        band_floor = e.get("band_floor_hz", e.get("band_floor"))
        rule_id = str(e.get("rule_id") or "")
        declared = e.get("strength")

        # (a) 裕度倍数 ρ / categorical ⟹ g（§2.1(a)），顺带判「规则是否真的命中」
        g = None
        try:
            if op in _conf.COMPARATORS_CAT:
                if value is None or threshold is None:
                    raise _conf.DependencyNull(feature, "value/threshold")
                matched = bool(value) == bool(threshold)
                fired = matched if op == "==" else not matched
                if not fired:
                    raise _conf.RuleNotFired(feature, rule_id, None)
                g = _conf.G_CATEGORICAL
            elif op in _conf.COMPARATORS_UP + _conf.COMPARATORS_DOWN:
                rho = _conf._ratio(feature, value, op, threshold, eps)
                if rho < 1.0:
                    raise _conf.RuleNotFired(feature, rule_id, rho)
                g = _conf.saturation_g(rho)
            else:
                raise _conf.ConfidenceError(f"未知 operator {op!r}")
        except _conf.RuleNotFired as ex:
            strength_violations.append(
                (i, f"{hid} 支持证据[{i}] 按 §2.1(a) 规则未命中（{ex}），却声明为支持证据（规则 15）"))
            full_recomputable = False
            continue
        except (_conf.DependencyNull, _conf.MissingFeatureScale, _conf.ConfidenceError) as ex:
            gap_fields.setdefault(f"证据[{i}] {feature}：{ex}", []).append(i)
            full_recomputable = False
            continue

        # (b) conf(f)（§2.1(b)：bandwidth 上界锁 0.6）
        try:
            conf_eff = _conf.feature_confidence(feature, conf)
        except _conf.ConfidenceError as ex:
            gap_fields.setdefault(f"证据[{i}] {feature}：{ex}", []).append(i)
            full_recomputable = False
            continue
        except _conf.DependencyNull:
            gap_fields.setdefault(f"证据[{i}] {feature}：缺 conf（§2.1(b) 要求逐条给出实测/估计档位）", []).append(i)
            full_recomputable = False
            continue

        # (d) band_factor（§2.1(d)；非频域⟹1.0；越带为 INV-1 阻塞，此处仅登记缺口，CAP-5 另有专检）
        band_factor = None
        try:
            band_probe = _conf.Evidence(feature=feature, value=bool(value), operator=">=", threshold=1.0,
                                        rule_id=rule_id, freq_hz=freq_hz, band_floor_hz=band_floor)
            if ctx is not None:
                band_factor = _conf.band_factor(band_probe, ctx)
            elif freq_hz is None:
                band_factor = 1.0  # 非频域判据与 ctx 无关
        except _conf.BandBlocked:
            gap_fields.setdefault(
                f"证据[{i}] {feature}：频带阻塞（INV-1/CAP-5），本不应作为支持证据复算", []).append(i)
            full_recomputable = False
            continue
        except _conf.MissingFeatureScale:
            gap_fields.setdefault(f"证据[{i}] {feature}：频域判据缺 band⊥/freq_hz（§2.1(d)）", []).append(i)
            full_recomputable = False
            continue
        if band_factor is None:
            gap_fields.setdefault(
                f"证据[{i}] {feature}：频域判据但缺 freq_limits 上下文，无法求 band_factor", []).append(i)
            full_recomputable = False
            continue

        # (c) 样本量因子：n/n_ref 齐 ⟹ 独立复算 S(e)；缺 ⟹ 用声明 strength 反解所需 n_factor 判其可行性
        if not _is_num(n) or not _is_num(n_ref):
            if _is_num(declared) and g > 0:
                nf_required = declared / (g * conf_eff * band_factor)
                if nf_required < _conf.N_FACTOR_AT_REF - 1e-6 or nf_required > 1.0 + 1e-6:
                    strength_violations.append(
                        (i, f"{hid} 支持证据[{i}] 声明 strength={declared} 在 §2.1 下不可复现："
                            f"需 n_factor={round(nf_required, 3)}"
                            f"（g={round(g, 3)}×conf={conf_eff}×band={band_factor}），"
                            f"越出文档下限 {N_FACTOR_FLOOR}~1.0（§2.1(c)：n≥n_ref，n_factor 不可能更低）（规则 15）"))
                else:
                    gap_fields.setdefault(
                        f"证据[{i}] {feature}：缺 n/n_ref，声明 strength 可行但未独立复算（需补样本量）", []).append(i)
            else:
                gap_fields.setdefault(f"证据[{i}] {feature}：缺 n/n_ref 且 strength 非数值", []).append(i)
            full_recomputable = False
            continue
        try:
            n_factor = _conf.sample_factor(float(n), float(n_ref), feature)
        except (_conf.MissingFeatureScale, _conf.SampleBelowReference) as ex:
            strength_violations.append(
                (i, f"{hid} 支持证据[{i}] n/n_ref 违反 §2.1(c)（{ex}）（规则 15）"))
            full_recomputable = False
            continue
        s_recomputed = g * conf_eff * n_factor * band_factor
        if _is_num(declared) and abs(s_recomputed - declared) > STRENGTH_TOL:
            strength_violations.append(
                (i, f"{hid} 支持证据[{i}] 声明 strength={declared} 与按 §2.1 从原始证据复算的 "
                    f"S(e)={round(s_recomputed, 4)} 不符（规则 15：strength 须由证据复现，不得手填）"))
        try:
            recomputed_evidence.append(
                _conf.Evidence(feature=feature, value=value, operator=op, threshold=threshold,
                               rule_id=rule_id, n=float(n), n_ref=float(n_ref), conf=conf,
                               freq_hz=freq_hz, band_floor_hz=band_floor, eps=eps))
        except _conf.ConfidenceError as ex:
            gap_fields.setdefault(f"证据[{i}] {feature}：{ex}", []).append(i)
            full_recomputable = False

    # 反证侧：penalty 必须等于由自身 (value, op, threshold) 重算 ρ′ 后落到的 §2.4 档位
    valid_refutations: list = []
    for j, ce in enumerate(_as_list(h.get("contradicting_evidence"))):
        pen = ce.get("penalty")
        op = _op_of(ce)
        rp = ce.get("rho_prime")
        if not _is_num(pen) or op not in (_conf.COMPARATORS_UP + _conf.COMPARATORS_DOWN + _conf.COMPARATORS_CAT):
            continue
        rf = _conf.Refutation(
            feature=str(ce.get("feature") or ""), value=ce.get("value"), operator=op,
            threshold=ce.get("threshold"), rule_id=str(ce.get("rule_id") or ""), penalty=float(pen),
            rho_prime=float(rp) if _is_num(rp) else None, eps=ce.get("eps"))
        try:
            _conf.check_refutation(rf)
        except _conf.RefutationPenaltyViolation as ex:
            refutation_violations.append((j, f"{hid} 反证[{j}]：{ex}（规则 15）"))
            continue
        except _conf.ConfidenceError:
            continue
        valid_refutations.append(rf)

    # 只有证据侧全部可独立复算 + ctx 齐备才聚合出 C（§2.2）
    c_value = None
    if full_recomputable and ctx is not None and len(recomputed_evidence) >= 2:
        ceilings = [x for x in _as_list(h.get("ceilings")) if _is_num(x)]
        mult = [x for x in _as_list(h.get("multiplicative")) if _is_num(x)]
        try:
            hyp = _conf.Hypothesis(fault_mode=h.get("fault_mode"),
                                   supporting_evidence=recomputed_evidence,
                                   contradicting_evidence=valid_refutations,
                                   ceilings=ceilings, multiplicative=mult)
            c_value = _conf.aggregate(hyp, ctx).c
        except (_conf.InsufficientEvidence, _conf.NotALeaf):
            c_value = None
        except _conf.RefutationPenaltyViolation as ex:
            refutation_violations.append((None, f"{hid}：{ex}（规则 15）"))
            c_value = None
        except _conf.ConfidenceError:
            c_value = None

    gap = None
    if gap_fields:
        gap = "不可复算，需补字段（" + "；".join(sorted(gap_fields.keys())) + "）"
    elif full_recomputable and ctx is None:
        gap = "不可复算，需补字段（缺 freq_limits 的 fs_hz/reliable_band_hz 上下文，无法执行 §2.1(d)/§2.2）"

    return RecomputeResult(c_value, strength_violations, refutation_violations, gap)


def _recompute_confidence(h: dict, ctx=None):
    """向后兼容包装：仅在能**独立复算**时返回 §2.2 的 C，否则返回 None（不再吃自报 strength）。"""
    return _recompute_detail(h, ctx).c


def _primary_recomputed(hypotheses, primary_id, ctx=None):
    for h in hypotheses:
        if h.get("id") == primary_id:
            rc = _recompute_detail(h, ctx).c
            return rc if rc is not None else (
                h.get("confidence") if isinstance(h.get("confidence"), (int, float))
                and not isinstance(h.get("confidence"), bool) else None)
    return None


def _validation_matches(diagnosis, action_id, validation_id) -> bool:
    for v in _as_list(diagnosis.get("validation")):
        if v.get("id") == validation_id and v.get("action_id") == action_id:
            return True
    return False


def _has_numbers(ee: dict) -> list:
    out = []
    for k in ("from", "to", "improvement_pct"):
        v = ee.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append((k, v))
    return out


def _families_present(hypotheses, considered, not_evaluable) -> set:
    fams: set[str] = set()

    def add(name):
        s = str(name or "")
        if s.startswith("mechanical"):
            fams.add("mechanical")
        elif s.startswith("electrical"):
            fams.add("electrical")
        elif s.startswith("software_induced"):
            fams.add("software_induced")

    for h in hypotheses:
        add(h.get("fault_mode"))
    for c in considered:
        add(c if isinstance(c, str) else c.get("fault_mode"))
    for ne in not_evaluable:
        add(ne.get("fault_mode") or ne.get("family"))
    return fams


def _software_registered_not_evaluable(not_evaluable) -> bool:
    for ne in not_evaluable:
        if ne.get("family") == "software_induced_error":
            return True
        if str(ne.get("fault_mode", "")).startswith("software_induced_"):
            return True
    return False


def _not_evaluable_ok(diagnosis, not_evaluable) -> bool:
    """非真空形状下，有缺席输入就必须登记；规则 12 的诚实真空（considered 空、只登记）不在此拦。"""
    inputs = diagnosis.get("inputs") or {}
    missing = _as_list(inputs.get("missing_channels"))
    blocked = _as_set((diagnosis.get("freq_limits") or {}).get("blocked_rules"))
    signals = bool(missing) or bool(blocked)
    if not not_evaluable and signals:
        return False
    return True


def _iter_narrative(diagnosis):
    """产出叙述层字段 (path, text)：verdict.summary / rationale / display_name / note。"""
    v = diagnosis.get("verdict") or {}
    yield ("verdict.summary", str(v.get("summary", "")))
    yield ("verdict.confidence_note", str(v.get("confidence_note", "")))
    for h in _as_list(diagnosis.get("hypotheses")):
        hid = str(h.get("id", "?"))
        yield (f"{hid}.display_name", str(h.get("display_name", "")))
        rec = h.get("recommendation") or {}
        yield (f"{hid}.rationale", str(rec.get("rationale", "")))
        ee = rec.get("expected_effect") or {}
        yield (f"{hid}.derivation", str(ee.get("derivation", "")))
        for ce in _as_list(h.get("contradicting_evidence")):
            yield (f"{hid}.note", str(ce.get("note", "")))


def _scan_unobserved(diagnosis) -> list:
    hits = []
    for path, text in _iter_narrative(diagnosis):
        for p in UNOBSERVED_PHRASES:
            if p in text:
                hits.append((path, p))
    return hits


def _summary_has_info(summary: str) -> bool:
    if not summary.strip():
        return False
    if "可能是多种因素" in summary or "多种因素共同" in summary:
        return False
    digits = sum(c.isdigit() for c in summary)
    return digits >= 2


def _is_t1(tier) -> bool:
    return bool(tier) and str(tier).startswith("T1")


def _tier_for_claim(tier_ledger, claim_id):
    for row in _as_list(tier_ledger):
        if row.get("claim_id") == claim_id:
            return row.get("source_tier")
    return None


def _check_wording_vs_tier(diagnosis) -> list:
    audit = diagnosis.get("audit") or {}
    ledger = audit.get("tier_ledger")
    offending = []

    def claim_id_for(path):
        if path.startswith("verdict.summary") or path.startswith("verdict.confidence_note"):
            return "verdict.summary"
        head = path.split(".", 1)[0]
        if "rationale" in path or "derivation" in path:
            for h in _as_list(diagnosis.get("hypotheses")):
                if str(h.get("id")) == head:
                    aid = (h.get("recommendation") or {}).get("action_id")
                    return f"recommendation.{aid}"
        return head  # display_name / note 归属假设 id

    for path, text in _iter_narrative(diagnosis):
        if not any(p in text for p in STRONG_CLAIM_PHRASES):
            continue
        claim = claim_id_for(path)
        tier = _tier_for_claim(ledger, claim)
        if not _is_t1(tier):
            offending.append({"path": path, "claim_id": claim,
                              "source_tier": tier if tier is not None else "T3(缺行按最低档)"})
    return offending


def _check_external_ledger(diagnosis, repo_root, chk) -> None:
    audit = diagnosis.get("audit") or {}
    ledger = _as_list(audit.get("external_ledger"))
    counts = audit.get("external_counts") or {}

    computed_verified = 0
    for i, row in enumerate(ledger):
        ref = row.get("external_reference")
        chk(f"C3-R17-ref[{i}]", ref is None or ref in EXTERNAL_REFERENCES,
            f"external_ledger[{i}].external_reference={ref!r} 非阶梯档位（未标档按 memory）（规则 17a）")
        vb = row.get("verified_by")
        chk(f"C3-R17-vb[{i}]", vb in VERIFIED_BY,
            f"external_ledger[{i}].verified_by={vb!r} 必须 ∈ {sorted(VERIFIED_BY)}（规则 17b）")
        chk(f"C3-R17-extracted[{i}]", isinstance(row.get("extracted"), bool),
            f"external_ledger[{i}].extracted 必须是布尔（规则 17c），实得={row.get('extracted')!r}")
        extra = [k for k in row if k in FORBIDDEN_EXTERNAL_KEYS]
        chk(f"C3-R17-name[{i}]", not extra,
            f"external_ledger[{i}] 出现第二个字段名={extra}（A-54 单一名字：unverified_signature 不进 JSON）（规则 17c）")

        effective = ref
        if ref == "official-artifact":
            path = row.get("artifact_path")
            resolved = _artifact_resolvable(path, repo_root)
            chk(f"C3-R17-artifact[{i}]", resolved,
                f"external_ledger[{i}] 声明 official-artifact 但 artifact_path={path!r} 不在本仓库可解析"
                f"——须降为 public-doc，不得按 official-artifact 计入（规则 17b）")
            if not resolved:
                effective = "public-doc"

        # 3b：只有 vendor_reply 能使其离开待确认态；official-artifact 不行；且须举证手册为什么答不了
        if row.get("assertion_class") == "3b":
            leaves_pending = effective in {"official-artifact", "vendor_reply"}
            if leaves_pending:
                chk(f"C3-R17-3b[{i}]", effective == "vendor_reply",
                    f"external_ledger[{i}] assertion_class=3b 却以 {effective} 出待确认态（规则 17e：只有 vendor_reply 可以）")
            chk(f"C3-R17-3b-why[{i}]", bool(row.get("note") or row.get("why")),
                f"external_ledger[{i}] 登记为 3b 必须举证『手册为什么答不了』（规则 17e / KB0 §6 检查 21）")

        if vb == "self" and effective == "official-artifact" and _artifact_resolvable(row.get("artifact_path"), repo_root):
            computed_verified += 1

    stated_verified = counts.get("verified")
    if isinstance(stated_verified, (int, float)) and not isinstance(stated_verified, bool):
        chk("C3-R17-count", stated_verified == computed_verified,
            f"external_counts.verified={stated_verified} 与重算值 {computed_verified} 不符"
            f"（规则 17b：third_party_report / 未解析 official-artifact 不计 k）")
    total = counts.get("total")
    if isinstance(total, (int, float)) and not isinstance(total, bool):
        chk("C3-R17-total", total == len(ledger),
            f"external_counts.total={total} 与台账行数 {len(ledger)} 不符（规则 17）")


def _artifact_resolvable(path, repo_root) -> bool:
    if not isinstance(path, str) or not path.strip():
        return False
    ap = os.path.normpath(os.path.join(repo_root, path))
    inside = os.path.commonpath([os.path.normpath(repo_root), ap]) == os.path.normpath(repo_root)
    return inside and os.path.exists(ap)


def _check_snapshot_premises(diagnosis, repo_root, chk) -> None:
    """C3 规则 18（A-99 ③）：契约示例点名的特征快照必须真实存在，且其前提与 `inputs` 一致。

    示例在 `inputs` 里写「本例无事件上下文」是不够的——前提要能被机器判定同构，否则同一个
    `case_id` 下「有事件」与「无事件」两份示例又能靠手写叙述互相矛盾（A-99 起因于此）。
    快照缺失即 FAIL：声明了不可解析的前提来源，等于该断言没有仓内可重跑产物（检查 27）。
    引擎产出的报告不带 `features_snapshot`（它有真的 `event_context`），此检查自然跳过。
    """
    inputs = diagnosis.get("inputs") or {}
    name = inputs.get("features_snapshot")
    if name is None:
        return
    bare = name[:-5] if isinstance(name, str) and name.endswith(".json") else name
    safe = (isinstance(bare, str) and bare.strip() != ""
            and os.path.basename(bare) == bare and "/" not in bare and "\\" not in bare)
    chk("C3-R18-name", safe,
        f"inputs.features_snapshot={name!r} 必须是 examples/ 下的裸文件名（禁路径分隔符与 ..）")
    if not safe:
        return
    path = os.path.join(repo_root, "examples", bare + ".json")
    if not os.path.exists(path):
        chk("C3-R18-exists", False,
            f"示例声明的特征快照 examples/{bare}.json 在仓内不存在（规则 18 / A-99 ③：前提须可解析）")
        return
    chk("C3-R18-exists", True, f"examples/{bare}.json 可解析")
    try:
        with open(path, encoding="utf-8") as fh:
            snap = json.load(fh)
    except (OSError, ValueError) as exc:
        chk("C3-R18-parse", False, f"examples/{bare}.json 读取失败：{exc}")
        return
    chk("C3-R18-parse", True, f"examples/{bare}.json 解析成功")

    want = inputs.get("present_channels")
    got = snap.get("present_channels")
    if isinstance(want, list) and isinstance(got, list):
        chk("C3-R18-channels", sorted(map(str, want)) == sorted(map(str, got)),
            f"inputs.present_channels={sorted(map(str, want))} 与快照 {bare} 的 "
            f"present_channels={sorted(map(str, got))} 不同构（规则 18：前提不同就换 case_id）")

    declared = inputs.get("event_context_available")
    ctx = snap.get("event_context")
    if declared is not None and isinstance(ctx, dict) and "available" in ctx:
        chk("C3-R18-events", bool(declared) == bool(ctx.get("available")),
            f"inputs.event_context_available={declared} 与快照 {bare} 的 "
            f"event_context.available={ctx.get('available')} 矛盾（规则 18 / A-99 ①）")


def _check_assumption_rows(audit: dict, chk) -> None:
    """C3 规则 19（#25）：`audit.assumptions[]` 必须是 `{anchor, statement}` 行。

    形状的唯一真值在 C1 §audit.assumptions，锚定词表在 `anchors.py`（叶子模块，C1 与 C3 共用）。
    没有锚的假定无法被报告引用，也就回答不了"这条假定作废时哪条结论跟着塌"。
    """
    for i, a in enumerate(_as_list(audit.get("assumptions"))):
        cid = f"C3-R19-assumption-shape[{i}]"
        if not isinstance(a, dict):
            chk(cid, False,
                f"assumptions[{i}] 是散文行而非 {{anchor, statement}} 对象（规则 19）：{a!r}")
            continue
        anchor, statement = a.get("anchor"), a.get("statement")
        kind = anchor_kind(anchor)
        ok = kind is not None and bool(str(statement or "").strip())
        chk(cid, ok,
            f"assumptions[{i}] 的 anchor={anchor!r} 不在 C1 §audit.assumptions 的六种稳定形式内"
            f"（现判为 {kind}），或 statement 为空"
            f"（statement {'非空' if str(statement or '').strip() else '为空'}）")


def _check_core_hash(diagnosis: dict, chk) -> None:
    """C3 规则 21：`audit.deterministic_core_hash` 的形态与复算。

    三个检查 id 各管一件事，不合并：形态（合法值三形态，`…` 判未清零）、复算（按规则 21 清单
    从产物重算并比对）、空串（记 gap 不记红——生产者未计算是过渡期状态，不是本报告的错）。
    复算与空串分开是必要的：若复算对空串直接判红，过渡期的包会被整片判红，而规则 21 的
    gap 语义正是让这种状态**可见但不阻塞**（gap 本身由检查 26 的"零 gap 复算"管着）。
    """
    declared = (diagnosis.get("audit") or {}).get("deterministic_core_hash")
    if _core_hash.is_placeholder(declared):
        chk("C3-R21-core-hash-format", False,
            f"deterministic_core_hash={declared!r} 是规则 21 的示例占位符，"
            f"自规则 21 立文起视为待清零——夹具与契约内联副本必须填实算值")
        chk("C3-R21-core-hash-recompute", True, "占位符形态不参与复算（见 -format）")
        chk("C3-R21-core-hash-empty-is-gap", True, "占位符形态不计 gap（见 -format）")
        return
    if declared == _core_hash.EMPTY_HASH:
        chk("C3-R21-core-hash-format", True, "空串：规则 21 写明的过渡期形态")
        chk("C3-R21-core-hash-recompute", True,
            "未计算，无从复算比对（缺口由 -empty-is-gap 显式记下，不靠沉默）")
        chk("C3-R21-core-hash-empty-is-gap", True,
            "gap：生产者尚未计算本包的确定性核心哈希（规则 21 过渡期形态，不判红）")
        return
    if not _core_hash.is_computed(declared):
        chk("C3-R21-core-hash-format", False,
            f"deterministic_core_hash={declared!r} 不在规则 21 的合法值三形态内"
            f"（空串 / sha256:<64 位小写 hex> / 占位符）")
        chk("C3-R21-core-hash-empty-is-gap", False,
            f"deterministic_core_hash={declared!r} 既非空串也非实算值，无法按过渡期处理")
        chk("C3-R21-core-hash-recompute", False,
            f"deterministic_core_hash={declared!r} 无法复算比对（形态非法）")
        return
    chk("C3-R21-core-hash-format", True, "sha256:<64 位小写 hex>")
    expected = _core_hash.core_hash(diagnosis)
    chk("C3-R21-core-hash-recompute", declared == expected,
        f"确定性核心哈希与按规则 21 清单的复算值不符：声明 {declared}，复算 {expected}"
        f"（核含 hypotheses[].rank 序与 verdict 的可判定字段；叙述层改动不该改哈希，"
        f"排序或算术改动必须改）")
    chk("C3-R21-core-hash-empty-is-gap", True, "已实算，非过渡期")


def _check_rank_monotonic(diagnosis: dict, chk) -> None:
    """C3 规则 20（A-107 ③）：`hypotheses[].rank` 必须等于 KB4 §2.9 的字典序。

    §2.9 的四个排序键在报告里只有两键有载体（severity、confidence）——coverage 与 rule_id
    在 `hypotheses[]` 上没有字段。本检查因此按**可判前缀**严格判，并列时用 `fault_mode`
    兜底（报告里唯一稳定的第三键），序仍可复现；coverage 缺载体一事另记台账缺口（A-115 裁为不补）。

    `C` 的并列带 ±0.01（A-116 ① 的落码）：产物里的 `confidence` 已是 `display()` 的两位值，
    两侧划带用的是同一把尺子（`confidence.rank_band_c`），所以「原始 C 落在同一个 2 位格内」
    这一类不再让引擎与校验器分出两种序——它们本来就只能被本报告分不出区别，带内序由 `fault_mode`
    定，而 `fault_mode` 两侧读的是同一个字段。
    """
    hyps = [h for h in _as_list(diagnosis.get("hypotheses")) if isinstance(h, dict)]
    if not hyps:
        return
    ranks = [h.get("rank") for h in hyps]
    chk("C3-R20-rank-contiguous", sorted(ranks) == list(range(1, len(hyps) + 1)),
        f"rank 不是 1…{len(hyps)} 的连续整数（§2.9 是全序，不接受跳号或重复）：实得 {ranks}")

    def _sev(h):
        v = h.get("severity")
        return v if isinstance(v, int) else 99

    leaders = _conf.rank_band_c(
        [(i, _sev(h), float(h["confidence"]) if _is_num(h.get("confidence")) else 0.0)
         for i, h in enumerate(hyps)])
    expected = [hyps[i].get("id") for i, _ in sorted(
        enumerate(hyps),
        key=lambda pair: (_sev(pair[1]), -leaders[pair[0]], str(pair[1].get("fault_mode"))))]
    got = [h.get("id") for h in sorted(hyps, key=lambda h: h.get("rank")
                                       if isinstance(h.get("rank"), int) else 99)]
    chk("C3-R20-rank-monotonic", got == expected,
        f"rank 序与 KB4 §2.9 字典序 (severity↑, −C±0.01 并列带, fault_mode) 不符："
        f"按 rank 读为 {got}，按字典序应为 {expected}（规则 20：头条由 severity 档决定，"
        f"示例不得手写排序）")
    primary = (diagnosis.get("verdict") or {}).get("primary")
    if expected:
        chk("C3-R20-primary-is-rank1", primary == expected[0],
            f"verdict.primary={primary!r} 不是 §2.9 序的第一名 {expected[0]!r}"
            f"（A-100 ③：R-26 只在同档内决定解释优先，跨档排序归 §2.9）")
