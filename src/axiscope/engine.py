"""C3 规则引擎的最小可运行编排层。

链路：C2 特征 → 登记层门（`registration`）→ 判据求值（`rule_table.json`）→
置信度（`confidence`，KB4 §2.1/§2.2）→ 仲裁与排序（KB3 R-26/R-28 + KB4 §2.9）→ C3 报告。

本层只读 C2 特征、只写报告字段：不碰设备（C3 规则 6），不改数值口径（规则 3——
`confidence` 一律由 §2.2 重算，LLM 只能改措辞）。未登记的规则一律不猜：
求值遇到本层没有口径的组合时，产出 `audit.assumptions` 或显式报错，而不是选一个"看起来对"的值。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from .confidence import (
    Evidence,
    FrequencyContext,
    Hypothesis,
    NotALeaf,
    Refutation,
    aggregate,
    display,
    evidence_strength,
    overall_confidence,
    rank_band_c,
    refutation_penalty,
)
from .features import WHY_NO_COUNTS, _dig, counts_scale_missing
from . import core_hash
from . import registration as reg

RULE_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rule_table.json")
KB3 = "docs/kb/KB3-tuning-rules.md"

# KB3 纪律 10 + CAP-7：派生通道的置信乘性惩罚。
DERIVED_MULTIPLICATIVE = 0.70
# KB3 R-10 / R-26 第 5 支：缺 `rest` 段时谐振侧的置信上限。
CAP_NO_REST = 0.55


class EngineError(Exception):
    pass


class MissingSampleScale(EngineError):
    """KB4 §2.1(c) 的样本量配方或下限缺失 ⟹ 该判据不可复算，不得默认 n_factor=1。"""


class NoRhoDefinition(EngineError):
    """§2.1(a) 没有给该类比较的 ρ 口径（例如 `between`），引擎不自造。"""


_TABLE: dict | None = None


def load_rule_table(path: str | None = None) -> dict:
    global _TABLE
    if _TABLE is None or path is not None:
        with open(path or RULE_TABLE_PATH, encoding="utf-8") as fh:
            table = json.load(fh)
        if path is None:
            _TABLE = table
        return table
    return _TABLE


def rule(rid: str) -> dict:
    rules = load_rule_table()["rules"]
    if rid not in rules:
        raise EngineError(f"规则 {rid} 不在最小可运行子集内（rule_table.json）")
    return rules[rid]


# ---------------------------------------------------------------- 特征求值

def dig(features: dict, path: str):
    """支持 `a.b[0].c` 形态的点号路径（`features._dig` 只认 `a.b[].c` 的逐元素形态）。"""
    cur = features
    for part in path.split("."):
        name, _, idx = part.partition("[")
        if not isinstance(cur, dict) or name not in cur:
            return None
        cur = cur[name]
        if idx:
            if not isinstance(cur, list):
                return None
            try:
                cur = cur[int(idx[:-1])]
            except (ValueError, IndexError):
                return None
    return cur


def _split(expr: str, head: str) -> tuple[str, str] | None:
    if expr.startswith(head + "(") and expr.endswith(")"):
        inner = expr[len(head) + 1:-1]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) == 2:
            return parts[0], parts[1]
    return None


def value_of(features: dict, path: str):
    """判据左值。允许 `ratio(A, B)` / `delta(A, B)` / `signed_asymmetry(path)` 三种派生式。"""
    m = _split(path, "ratio")
    if m:
        a, b = (dig(features, p) for p in m)
        if a is None or b is None:
            return None
        # KB3 原文的分母是 max(<计数>, 1)；频率比不做该钳制。
        return a / (max(b, 1) if _is_count(features, m[1]) else b)
    m = _split(path, "delta")
    if m:
        a, b = (dig(features, p) for p in m)
        if a is None or b is None:
            return None
        return a - b
    if path.startswith("signed_asymmetry("):
        r = dig(features, path[len("signed_asymmetry("):-1])
        if r is None:
            return None
        return r if r >= 1 else -1.0 / r
    return dig(features, path)


def _is_count(features: dict, path: str) -> bool:
    return path.startswith("event_context.") and ("count" in path or "_count" in path.split(".")[-1])


def threshold_of(features: dict, cond: dict):
    thr = cond.get("threshold")
    if isinstance(thr, dict):
        ref = dig(features, thr["ref"])
        if ref is None:
            return None
        return ref * float(thr.get("scale", 1.0))
    return thr


_COMPARATOR = {"gte": ">=", "lte": "<=", "gt": ">", "lt": "<", "is_true": "==", "is_false": "=="}
_COMPARATORS_PY = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
                   ">": lambda a, b: a > b, "<": lambda a, b: a < b,
                   "==": lambda a, b: a == b, "!=": lambda a, b: a != b}


def hits(value, op: str, threshold) -> bool | None:
    if value is None:
        return None
    if op == "between":
        lo, hi = threshold
        if value is None:
            return None
        return lo <= value <= hi
    if op == "is_true":
        return value is True
    if op == "is_false":
        return value is False
    if threshold is None:
        return None
    fn = _COMPARATORS_PY[_COMPARATOR.get(op, op)]
    return bool(fn(value, threshold))


def sample_n(features: dict, cond: dict, sample_counts: dict | None):
    """按 KB4 §2.1(c) 的配方取样本量。配方缺失 ⟹ 显式报错（不默认 1.0）。"""
    n_ref = cond.get("n_ref")
    recipe = cond.get("n_source")
    if recipe is None or n_ref is None:
        raise MissingSampleScale(
            f"{cond['feature']} 的样本量配方/下限未在 rule_table 登记"
            "（KB4 §2.1(c) 无对应行）⟹ 该判据不可复算")
    if recipe.startswith("segment:"):
        n = dig(features, "segment_coverage." + recipe.split(":")[1])
    elif recipe.startswith("event:"):
        n = dig(features, "event_context." + recipe.split(":")[1])
    elif recipe == "three_db_width_bins":
        f0 = dig(features, "resonance.candidates[0].freq_hz")
        q = dig(features, "resonance.candidates[0].quality_factor_estimate")
        res = dig(features, "resonance.resolution_hz")
        n = round(f0 / q / res) if None not in (f0, q, res) else None
    elif recipe in ("welch_segments", "band_bins"):
        key = "%s:%s" % (recipe, cond["n"])
        n = (sample_counts or {}).get(key, (sample_counts or {}).get(recipe))
        if n is None:
            raise MissingSampleScale(
                f"{recipe} 不是 C2 已登记字段（见 rule_table.open_gaps），"
                f"须由 sample_counts 侧车显式带入键 {key!r}")
    else:
        raise EngineError(f"未知 n_source 配方 {recipe!r}")
    if n is None:
        raise MissingSampleScale(f"{cond['feature']} 的样本量算不出来（配方 {recipe}）")
    return float(n), float(n_ref)


def counts_scale_class(cond: dict) -> str | None:
    """A-97 ④：以 counts 表述的判据分「绝对 / 比值」，**未标注者按绝对处理**（保守侧）。

    `*_counts` 后缀是历史名而非单位（A-97 ①），所以只有**绝对**阈值需要 counts 刻度；
    比值 / 相关 / 相干类判据分子分母同单位、与刻度无关，被绝对阈值那道门连坐正是 A-97 ③
    禁止的错误。非 counts 路径返回 `None`（与刻度无关，不参与本判定）。
    """
    blob = "%s %s" % (cond.get("feature", ""),
                      json.dumps(cond.get("threshold"), ensure_ascii=False))
    if "counts" not in blob:
        return None
    return cond.get("counts_scale", "absolute")


def counts_gate(features: dict, leaf: str, meta: dict) -> list[dict]:
    """A-97 ②：无 counts 刻度 ⟹ 依赖绝对 counts 阈值的规则不得做比较（不是判条件为假）。

    与 `band_gate` 同形（`blocked_rules` + `rules_skipped`；整叶都卡在绝对阈值上时才加
    `not_evaluable`）。缺的东西不同：那里缺的是频段内的信息，这里缺的是可比的分母。
    """
    if not counts_scale_missing(meta):
        return []
    table = load_rule_table()["rules"]

    def _absolute(spec: dict) -> bool:
        # 反证与主判据同口径：一条绝对 counts 反证同样没有可比的分母，不能只挡正向判据。
        return any(counts_scale_class(c) == "absolute"
                   for key in ("conditions", "refuters") for c in spec.get(key, []))

    scored = [r for r in reg.LEAVES[leaf]["rules"] if r not in reg.GATE_RULES and r in table]
    hit = [r for r in scored if _absolute(table[r])]
    if not hit:
        return []
    rows = [{"kind": "blocked_rules", "rule_ids": hit, "feature": reg.LEAVES[leaf]["feature"],
             "reason": "绝对 counts 阈值无分母（counts_per_mm=null 且 units_are != counts）"},
            {"kind": "rules_skipped", "rule_ids": hit, "reason": "absent_counts_scale"}]
    if len(hit) == len(scored):
        # 整个叶都卡在没有分母的绝对阈值上才登记成缺席；只中一条时其余规则的比值判据
        # 照跑——A-97 ③ 明文禁止把刻度无关的判据连坐。
        rows.insert(1, {"kind": "not_evaluable", "fault_mode": leaf,
                        "blocked_by": "absent_counts_scale", "why": WHY_NO_COUNTS})
    return rows


# ---------------------------------------------------------------- 假设构建

@dataclass
class LeafResult:
    leaf: str
    rule_ids: list[str]
    status: str                      # fired | vetoed | insufficient | blocked
    scored_rules: list[str] = field(default_factory=list)   # 真正产出证据的规则才进 rules_fired
    hypothesis: Hypothesis | None = None
    scores: list = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _band_of(rid: str) -> float | None:
    from .features import BAND_FLOOR
    return BAND_FLOOR.get(rid)


def build_evidence(features: dict, rid: str, ctx: FrequencyContext,
                   sample_counts: dict | None,
                   counts_missing: bool = False) -> tuple[list[Evidence], list[str], list[str]]:
    """返回 (支持证据, 门未过原因, 否决原因)。"""
    spec = rule(rid)
    ev: list[Evidence] = []
    gates: list[str] = []
    vetoes: list[str] = []
    for cond in spec.get("conditions", []):
        if counts_missing and counts_scale_class(cond) == "absolute":
            # A-97 ②：先问分母再问大小——没有 counts 刻度时，把 m 拿去和 counts 阈值比
            # 是静默量纲替换，比放弃这条判据危险一个量级。
            gates.append("absent_counts_scale:%s#%d" % (rid, cond["n"]))
            continue
        val = value_of(features, cond["feature"])
        thr = threshold_of(features, cond)
        if val is None:
            if cond.get("required"):
                gates.append("dependency_null:%s" % cond["feature"])
            continue
        if cond["op"] == "branch":
            a_s = value_of(features, "signed_asymmetry(%s)" % cond["feature"])
            branch = _branch_hit(a_s, spec.get("branches", []))
            ok = branch is not None
            cond_value, cond_thr = a_s, branch[1] if ok else None
            op = ">=" if ok and cond_value > 0 else "<="
            if not ok:
                gates.append("branch_miss:%s" % cond["feature"])
                continue
        else:
            cond_value, cond_thr = val, thr
            op = _COMPARATOR.get(cond["op"], cond["op"])
            if not hits(val, cond["op"], thr):
                if cond.get("veto_on_fail"):
                    vetoes.append("%s 排除项不成立（%s %r 对 %r）"
                                  % (cond["feature"], cond["op"], val, thr))
                elif cond.get("required"):
                    gates.append("not_fired:%s#%d" % (rid, cond["n"]))
                continue
        if not cond.get("evidence"):
            continue
        if cond["op"] == "between":
            raise NoRhoDefinition(
                "%s#%d 用 `between`，KB4 §2.1(a) 未给双边条件的 ρ 口径 ⟹ 引擎不自造"
                % (rid, cond["n"]))
        n, n_ref = sample_n(features, cond, sample_counts)
        cat = cond["op"] in ("is_true", "is_false")
        ev.append(Evidence(
            feature=cond["feature"],
            value=cond_value,
            operator="==" if cat else op,
            threshold=(True if cond["op"] == "is_true" else False) if cat else cond_thr,
            rule_id=cond.get("rule_id", rid),
            n=n, n_ref=n_ref, conf=1.0,
            freq_hz=_candidate_freq(features) if cond["feature"].startswith("resonance.candidates") else None,
            band_floor_hz=_band_of(rid),
            source="%s#%s" % (KB3, rid),
        ))
    return ev, gates, vetoes


def _candidate_freq(features: dict):
    return dig(features, "resonance.candidates[0].freq_hz")


def _branch_hit(a_s, branches):
    if a_s is None:
        return None
    for b in branches:
        if "A_s_gte" in b and a_s >= b["A_s_gte"]:
            return (b["id"], b["A_s_gte"])
        if "A_s_lte" in b and a_s <= b["A_s_lte"]:
            return (b["id"], b["A_s_lte"])
    return None


def build_refuters(features: dict, rid: str) -> list[Refutation]:
    """反证一律显式登记：命中给强档，形态未出现给 0.05，依赖为 null 则不入列（INV-4）。"""
    out = []
    for spec in rule(rid).get("refuters", []):
        val = value_of(features, spec["feature"])
        thr = spec.get("threshold")
        if isinstance(thr, dict):
            thr = threshold_of(features, spec)
        op = _COMPARATOR.get(spec["op"], spec["op"])
        if val is None:
            continue
        rho = _rho_prime(val, op, thr)
        out.append(Refutation(feature=spec["feature"], value=val, operator=op, threshold=thr,
                              rule_id=spec["id"], penalty=refutation_penalty(rho),
                              rho_prime=rho, source="%s#%s" % (KB3, spec["id"].split("#")[0])))
    return out


def _rho_prime(value, op: str, threshold) -> float:
    if op in (">=", ">"):
        return value / threshold if threshold else float("inf")
    if op in ("<=", "<"):
        return threshold / value if value else float("inf")
    raise EngineError("反证不支持比较符 %r（§2.4 的 ρ′ 只对上下界定义）" % op)


def ceilings_for(features: dict, rid: str, meta: dict) -> tuple[list[float], list[float]]:
    caps: list[float] = []
    mult: list[float] = []
    if rid in ("R-03", "R-04"):
        rest = dig(features, "segment_coverage.rest")
        cand_rest = dig(features, "resonance.candidates[0].present_in_rest")
        if cand_rest is None or (rest or 0) < 1:
            caps.append(CAP_NO_REST)          # CAP-3：缺 rest 段，不是 rest 段为 false
    chans = (meta.get("channels") or {})
    for ch in chans.values():
        if isinstance(ch, dict) and ch.get("derived"):
            mult.append(DERIVED_MULTIPLICATIVE)   # CAP-7（KB3 纪律 10）
            break
    return caps, mult


def evaluate_leaf(features: dict, leaf: str, ctx: FrequencyContext,
                  sample_counts: dict | None, meta: dict) -> LeafResult:
    spec = reg.LEAVES[leaf]
    scored = [r for r in spec["rules"] if r not in reg.GATE_RULES and r in load_rule_table()["rules"]]
    if not scored:
        return LeafResult(leaf, [], "blocked", reasons=["no_scoreable_rule_in_subset"])
    all_ev: list[Evidence] = []
    all_rf: list[Refutation] = []
    contrib: list[str] = []          # 实际产出证据的规则
    caps: list[float] = []
    mult: list[float] = []
    reasons: list[str] = []
    blocked = False
    for row in reg.band_gate(features, leaf):
        if row["kind"] == "not_evaluable":
            blocked = True
        reasons.append(row["kind"])
    for row in counts_gate(features, leaf, meta):
        if row["kind"] == "not_evaluable":
            blocked = True
        reasons.append(row["kind"])
    if blocked:
        return LeafResult(leaf, scored, "blocked", reasons=reasons)
    counts_missing = counts_scale_missing(meta)
    for rid in scored:
        try:
            ev, gates, vetoes = build_evidence(features, rid, ctx, sample_counts,
                                               counts_missing=counts_missing)
        except (MissingSampleScale, NoRhoDefinition) as exc:
            reasons.append("%s:%s" % (type(exc).__name__, exc))
            continue
        if vetoes:
            reasons.append("vetoed:%s" % "; ".join(vetoes))
            continue
        if ev:
            contrib.append(rid)
        all_ev.extend(ev)
        all_rf.extend(build_refuters(features, rid))
        c, m = ceilings_for(features, rid, meta)
        caps += c
        mult += m
        if gates:
            reasons.extend("%s %s" % (rid, g) for g in gates)
    if len(all_ev) < 2:
        return LeafResult(leaf, scored, "insufficient", scored_rules=contrib,
                          reasons=reasons or ["k<2（C3 规则 1）"])
    hyp = Hypothesis(fault_mode=leaf, supporting_evidence=all_ev,
                     contradicting_evidence=all_rf, ceilings=caps, multiplicative=mult)
    score = aggregate(hyp, ctx)
    return LeafResult(leaf, scored, "fired", scored_rules=contrib,
                      hypothesis=hyp, scores=[score], reasons=reasons)


# ---------------------------------------------------------------- 仲裁与排序

def severity_of(rid_list: list[str], features: dict) -> tuple[int, str]:
    """§2.9：`severity` 取主规则登记级；多规则并发取最高级（数值最小）。

    返回 (级, provenance)，provenance ∈ {"", "assumed", "classified", "no_row"}：
    - "assumed"    —— 规则表写 `assumed:` 前缀（§2.9 无锚点，同族推断）；
    - "classified" —— 规则表写 `classified:` 前缀（A-100 补的软件族分类行：按后果类型
                      归入 §2.9 现有档，是裁决锚点但不是独立观测锚）；
    - "no_row"     —— 规则在本包规则表没有 severity 行，只能按保守档处理。
    三种都必须写 `audit.assumptions` 留痕，不得写成唯一结论。"""
    levels = []
    provenance = ""
    for rid in rid_list:
        spec = rule(rid)
        cond = spec.get("severity_when")
        lvl = spec.get("severity")
        if cond:
            ok = _eval_simple(features, cond)
            lvl = spec["severity"] if ok else spec.get("severity_default", lvl)
        prov = str(spec.get("severity_provenance", ""))
        if prov.startswith("assumed"):
            provenance = "assumed"
        elif prov.startswith("classified"):
            provenance = "classified"
        if lvl is not None:
            levels.append(int(lvl))
    if not levels:
        return 4, "no_row"
    return min(levels), provenance


def _eval_simple(features: dict, expr: str) -> bool:
    for op in (">=", "<=", "!=", "==", ">", "<"):
        if op in expr:
            lhs, rhs = [p.strip() for p in expr.split(op)]
            v = dig(features, lhs)
            if v is None:
                return False
            return _COMPARATORS_PY[op](v, float(rhs))
    return False


def arbitrate_r26(features: dict, fired: dict[str, LeafResult]) -> list[str]:
    """KB3 R-26 有序链。返回说明行；链无命中时**必须**显式登记，不得静默回落到排序。"""
    notes: list[str] = []
    if "mechanical_resonance" not in fired and "electrical_feedforward_mismatch" not in fired:
        return notes
    cand = (features.get("resonance") or {}).get("candidates") or []
    c0 = cand[0] if cand else {}
    a_s = value_of(features, "signed_asymmetry(ff_mismatch.asymmetry_ratio)")
    rest, dwell = c0.get("present_in_rest"), c0.get("present_in_dwell")
    coh = c0.get("coherence_torque_velocity")
    corr = dig(features, "ff_mismatch.fe_vs_accel_corr")
    step2 = dwell is True and coh is not None and coh >= 0.7 and a_s is not None and abs(a_s) < 1.5
    step3 = rest is False and dwell is False and corr is not None and corr >= 0.6 \
        and a_s is not None and abs(a_s) >= 1.5
    # 第 6 支（A-100 补第三支的补集）：dwell == true 且不对称不显著，但第 2 支因相干性不足未成立
    step6 = dwell is True and a_s is not None and abs(a_s) < 1.5
    if rest is None:
        notes.append("R-26#5：present_in_rest 为 null ⟹ 仲裁失效，两侧上限压至 0.55")
    elif step2 and step3:
        notes.append("R-26#4：谐振为 primary、前馈 rank 2，互相写入对方的 contradicting_evidence")
    elif step2:
        notes.append("R-26#2：判机械谐振")
    elif step3:
        notes.append("R-26#3：判前馈失配")
    elif step6:
        notes.append("R-26#6（第三支的补集，A-100）：dwell == true AND abs(A_s) < 1.5 且第 2 支未成立"
                     "（相干性 < 0.7 或为 null）⟹ 不重排，登记后按 KB4 §2.9 原序输出 rank")
    else:
        # 登记行只报本样本的实际链状态：把例 A 的措辞硬编码进通用路径就是措辞越级（KB4 §2.10 同律）。
        notes.append("R-26 有序链无命中（含第 6 支补集在内各支均不成立；本样本 dwell=%r、rest=%r、"
                     "abs(A_s)=%s、coherence=%s、corr=%s）"
                     "⟹ 禁止静默挑一支或改序，按 KB4 §2.9 字典序输出 rank，见 A-100"
                     % (dwell, rest, "null" if a_s is None else round(abs(a_s), 3), coh, corr))
    return notes


def arbitrate_r28(features: dict) -> tuple[list[str], list[str]]:
    """R-28 择优。返回 (胜出的 fault_mode 列表, 说明)。"""
    ec = features.get("event_context") or {}
    spikes = ec.get("fe_spike_count")
    names = {"s_host": "software_induced_host_thread_jitter",
             "s_intp": "software_induced_interp_buffer_underrun",
             "s_net": "software_induced_bus_cycle_miss",
             "s_vision": "software_induced_late_vision_result"}
    fields = {"s_host": "fe_spike_aligned_to_host_pause",
              "s_intp": "fe_spike_aligned_to_underrun",
              "s_net": "fe_spike_aligned_to_network_miss",
              "s_vision": "fe_spike_aligned_to_vision_result"}
    scores: dict[str, float] = {}
    notes: list[str] = []
    for key, fld in fields.items():
        aligned = ec.get(fld)
        if aligned is None or not spikes:
            notes.append("%s 一路为 null ⟹ 不参与择优并登记 not_evaluable" % key)
            continue
        scores[key] = aligned / max(spikes, 1)
    if not scores:
        return [], notes + ["R-28 无可择优路"]
    order = sorted(scores.items(), key=lambda kv: -kv[1])
    best_key, best = order[0]
    second = order[1][1] if len(order) > 1 else 0.0
    tau_u = (ec.get("sync") or {}).get("uncertainty_ms")
    residual = ec.get("alignment_residual_ms")
    ok = [best >= 0.5, best - second >= 0.2,
          tau_u is not None and residual is not None and residual <= tau_u,
          ec.get("causal_claims_permitted") is True]
    if all(ok):
        return [names[best_key]], notes + ["R-28 择优胜出 %s（max=%.3f, margin=%.3f）"
                                           % (best_key, best, best - second)]
    return [], notes + ["R-28 区分度不足（%s）⟹ 软件族全部候选只进 considered"
                        % [i for i, v in enumerate(ok) if not v]]


# ---------------------------------------------------------------- 报告

#: `sample_counts` 侧车键 → C2 里承载同一件事的特征路径（A-102 ② 落的载体）。
#: 表外的键锚到 KB4 §2.1(c)：那条假定来自"配方未登记"，不是来自某个字段。
SIDECAR_ANCHOR = {"welch_segments": "resonance.estimation.n_segments",
                  "band_bins": "resonance.estimation.bins_in_band"}

# A-102 ④ 的固定留痕：R-04/R-15 的样本量下限已在 KB4 §2.1(c) 登记，但 rule_table 未为这两条
# 登记 `n_source` 配方 ⟹ 本引擎不默认 n_factor=1、该两条不可评分（A-102 ③ 的过渡口径，本行
# 只补登记、不改动 MissingSampleScale / rules_skipped 的门语义，也不把这两条变可评分）。
#   锚：缺的是"配方未登记"这一**文档事实**、不是某个字段 ⟹ 取 C1 §audit.assumptions 第⑥式
#   文档锚 `KB4§2.1(c)`，与 `SIDECAR_ANCHOR` 表外键同一锚；
#   行数：固定句子同时点名两条（"该两条不可评分"），而锚必须是单一稳定串 ⟹ **一行覆盖两条**，
#   拆挂到 R-04 或 R-15 任一单锚都会错报其范围（与侧车"一键一行"并列：分组键是"缺配方"这一
#   文档缺口，两条共享，故折成一行）。
NSOURCE_GAP_ANCHOR = "KB4§2.1(c)"
NSOURCE_GAP_SENTENCE = ("R-04/R-15 的样本量下限已在 KB4 §2.1(c) 登记，"
                        "但 rule_table 未登记 `n_source` 配方 ⟹ 本引擎不默认 `n_factor=1`，"
                        "该两条不可评分")
# `sample_n` 有两条不可复算路径：其一 n_source 为 null（"未在 rule_table 登记"）——这才是
# A-102 ④ 的配方缺口；其二 welch/band 侧车键缺失——那属 A-102 ③ 的侧车留痕，不进本行。
NSOURCE_RECIPE_GAP_MARK = "未在 rule_table 登记"
NSOURCE_GAP_RULES = ("R-04", "R-15")


def analyze(features: dict, meta: dict | None = None, *, sample_counts: dict | None = None,
            case_id: str = "AX1-LOCAL", source_tier: str = "T3") -> dict:
    meta = meta or {}
    ledger = reg.Ledger()
    ctx = FrequencyContext(fs_hz=features["fs_hz"],
                           reliable_band_hz=features["freq_limits"]["reliable_band_hz"],
                           nyquist_hz=features["freq_limits"].get("nyquist_hz"))
    fired: dict[str, LeafResult] = {}
    blocked_rows: list[dict] = []
    if sample_counts:
        # 外部注入的样本量不是本包可复算的量，必须留痕（A-102 / A-103 同源纪律）
        for key in sorted(sample_counts):
            ledger.assume(
                SIDECAR_ANCHOR.get(key, "KB4§2.1(c)"),
                "样本量 %s=%s 由 sample_counts 侧车外部注入，C2 未承载该字段"
                "（rule_table.open_gaps）⟹ 相关 S(e) 不是本包可独立复算量"
                % (key, sample_counts[key]))
    # 族级门先跑：它们决定哪些叶是「输入缺失不可评」，逐叶循环才不至于又把同一叶
    # 登记成「候选但未成立」（KB4 §1.5 逐叶粒度）。
    reg.software_family(features, ledger)
    reg.thermal_family(features, ledger)
    n_source_gap = False
    for leaf in reg.LEAVES:
        for rows in (reg.band_gate(features, leaf), counts_gate(features, leaf, meta)):
            for row in rows:
                if row["kind"] == "not_evaluable":
                    ledger.register({k: v for k, v in row.items() if k != "kind"})
                elif row["kind"] == "rules_skipped":
                    for rid in row.get("rule_ids", []):
                        ledger.skip(rid, row["reason"])
                elif row["kind"] == "blocked_rules":
                    blocked_rows.append(row)
        res = evaluate_leaf(features, leaf, ctx, sample_counts, meta)
        for r in res.reasons:
            if r.startswith(("MissingSampleScale", "NoRhoDefinition", "vetoed", "dependency_null")):
                ledger.skip(",".join(res.rule_ids), r)
            # A-102 ④：R-04/R-15 因 rule_table 未登记 `n_source` 配方（n_source 为 null 那一支）
            # 而不可评分时留痕——门语义不变（照旧 skip），只是补一条可引用的登记。
            if (r.startswith("MissingSampleScale") and NSOURCE_RECIPE_GAP_MARK in r
                    and set(NSOURCE_GAP_RULES) & set(res.rule_ids)):
                n_source_gap = True
        if res.status == "fired":
            fired[leaf] = res
        elif res.status != "blocked":
            ledger.consider(leaf, "; ".join(res.reasons) or res.status)
    if n_source_gap:
        ledger.assume(NSOURCE_GAP_ANCHOR, NSOURCE_GAP_SENTENCE)
    for row in reg.near_nyquist(features):
        if row["kind"] == "consider":
            ledger.consider(row["slug"], row["note"])
        else:
            for rid in row.get("rule_ids", []):
                ledger.skip(rid, row["reason"])
    winner28, notes28 = arbitrate_r28(features)
    if winner28 == []:
        for leaf in [l for l in list(fired) if l.startswith("software_induced_")]:
            fired.pop(leaf)
            ledger.consider(leaf, "R-28 未胜出：" + "; ".join(notes28))
    notes26 = arbitrate_r26(features, fired)

    ranked = _rank(features, fired, ledger, notes26)
    hypotheses = []
    for i, (leaf, res) in enumerate(ranked, start=1):
        score = res.scores[0]
        sev, prov = severity_of(res.scored_rules, features)
        if prov == "assumed":
            ledger.assume(leaf, "%s 的 severity 无 KB4 §2.9 锚点，按同族推断取 %d" % (leaf, sev))
        elif prov == "classified":
            ledger.assume(leaf,
                          "%s 的 severity 取 KB4 §2.9 软件族分类行（按后果类型归入 S%d），"
                          "属裁决分类锚点、非独立观测锚，不得写成唯一结论" % (leaf, sev))
        elif prov == "no_row":
            ledger.assume(leaf,
                          "%s 的 severity 在本包规则表无 severity 行，按 §2.9 观测层保守取 %d"
                          % (leaf, sev))
        c_val = display(score.c)
        hyp = {
            "id": "H%d" % i,
            "fault_mode": leaf,
            "display_name": _DISPLAY.get(leaf, leaf),
            "rank": i,
            "confidence": c_val,
            "severity": sev,
            "supporting_evidence": _evidence_rows(features, res, ctx),
            "contradicting_evidence": _refuter_rows(res),
            "recommendation": _recommendation(leaf, res),
        }
        if c_val < 0.6:
            hyp["next_data_to_collect"] = _next_data(leaf)
        hypotheses.append(hyp)
        for rid in res.scored_rules:
            ledger.fire(rid)
        for ev in hyp["supporting_evidence"]:
            ledger.fire(ev["rule_id"])

    primary = hypotheses[0]["id"] if hypotheses else None
    ne_rows = ledger.not_evaluable
    if hypotheses:
        overall = display(overall_confidence(fired[ranked[0][0]].scores[0], ne_rows))
    else:
        overall = None
    blocked_ids = sorted({b for row in blocked_rows for b in row["rule_ids"]})

    report = {
        "schema": "axiscope.diagnosis/1",
        "case_id": case_id,
        "engine_version": "0.1.0",
        "inputs": _inputs(features),
        "freq_limits": features["freq_limits"],
        "unavailable": features.get("unavailable", []),
        "event_context": {k: features.get("event_context", {}).get(k) for k in
                          ("available", "causal_claims_permitted")} if
                         features.get("event_context") else {},
        "causal_claims_permitted": (features.get("event_context") or {}).get("causal_claims_permitted"),
        "verdict": {
            "primary": primary,
            "summary": _summary(hypotheses, ranked, overall, source_tier),
            "overall_confidence": overall,
            "confidence_note": _confidence_note(
                ranked, [e["strength"] for e in hypotheses[0]["supporting_evidence"]] if hypotheses else [],
                ledger),
            "actionable": bool(hypotheses),
        },
        "hypotheses": hypotheses,
        "differential": {
            "considered": ledger.considered,
            "not_evaluable": ne_rows,
        },
        "validation": [],
        "safety": {"writes_to_device": False, "requires_human_approval": True,
                   "hard_blocks": ["禁止在带工件/带负载状态下直接下发增益"],
                   "disclaimer": "本输出为辅助诊断，参数下发前须由设备工程师现场确认。"},
        "audit": {
            "rules_fired": ledger.rules_fired,
            "rules_skipped": ledger.rules_skipped,
            "assumptions": list(ledger.assumptions),
            "arbitration_notes": notes26 + notes28,
            "tier_ledger": _tier_ledger(hypotheses, source_tier),
            "external_counts": {"verified": 0, "total": 0},
            "deterministic_core_hash": "",
        },
    }
    if blocked_ids:
        report["freq_limits"]["blocked_rules"] = blocked_ids
    # C3 规则 21：哈希核含 `freq_limits`，所以必须等 `blocked_rules` 落进产物之后再算，
    # 否则校验器从 JSON 重算时会把这一项算成缺键。
    report["audit"]["deterministic_core_hash"] = core_hash.core_hash(report)
    return report


def _rank(features: dict, fired: dict[str, LeafResult], ledger: reg.Ledger,
          notes26: list[str]) -> list[tuple[str, LeafResult]]:
    """KB4 §2.9 字典序 (severity, C↓, coverage↓, tiebreak)，C 的并列带 ±0.01。

    第二键用 `display(c)`（两位显示值）而不是链上原始 C：本函数与
    `c3validate._check_rank_monotonic` 是同一套序的两侧，校验器只能读产物里的两位值，
    引擎若按原始 C 排，同带内就会分出两种序，规则 20 只能对其中一种判红——那是假红不是缺陷。

    第三键落 `fault_mode` 而不是 §2.9 写的 `rule_id`：`rule_id` 在假设级没有载体（A-115
    裁为"不补"），引擎按它排出来的序校验器无法复算。§2.9 要的是"序可复现"，`fault_mode`
    在报告里唯一且稳定，达成同一目的且两侧同源；等 C2 侧给出窗口出处、`rule_id` 有了假设级
    载体，再把这一键换回去并同步扩规则 20。
    """
    items = [(leaf, res, severity_of(res.rule_ids, features)[0], display(res.scores[0].c))
             for leaf, res in fired.items()]
    leaders = rank_band_c([(i, sev, c) for i, (_, _, sev, c) in enumerate(items)])

    def key(pair):
        i, (leaf, res, sev, _c) = pair
        return (sev, -leaders[i], -_coverage(features, res), leaf)
    return [(leaf, res) for _, (leaf, res, _sev, _c)
            in sorted(enumerate(items), key=key)]


def _coverage(features: dict, res: LeafResult) -> float:
    cov = features.get("segment_coverage") or {}
    total = sum(v for v in cov.values() if isinstance(v, (int, float)))
    return 1.0 if total else 0.0


def _evidence_rows(features: dict, res: LeafResult, ctx: FrequencyContext) -> list[dict]:
    table = load_rule_table()["rules"]
    out = []
    for ev in res.hypothesis.supporting_evidence:
        rid = re.match(r"R-\d+", ev.rule_id).group(0)
        cond_no = next((c["n"] for c in table.get(rid, {}).get("conditions", [])
                        if c["feature"] == ev.feature), None)
        out.append({
            "feature": ev.feature,
            "value": round(ev.value, 6) if isinstance(ev.value, float) else ev.value,
            "operator": ev.operator,
            "threshold": ev.threshold,
            "strength": round(evidence_strength(ev, ctx), 3),
            "n": ev.n, "n_ref": ev.n_ref, "conf": ev.conf,
            "freq_hz": ev.freq_hz, "band_floor_hz": ev.band_floor_hz,
            "condition_index": cond_no,
            "rule_id": ev.rule_id,
            "source": ev.source,
        })
    return out


def _refuter_rows(res: LeafResult) -> list[dict]:
    return [{"feature": rf.feature, "value": round(rf.value, 6) if isinstance(rf.value, float) else rf.value,
             "operator": rf.operator, "threshold": rf.threshold,
             "rho_prime": round(rf.rho_prime, 3) if rf.rho_prime is not None else None,
             "penalty": rf.penalty, "rule_id": rf.rule_id, "source": rf.source}
            for rf in res.hypothesis.contradicting_evidence]


_DISPLAY = {
    "mechanical_resonance": "机械谐振（结构模态被瞬态激励）",
    "software_induced_interp_buffer_underrun": "插补缓冲区欠载导致路径速度骤降",
    "electrical_feedforward_mismatch": "加速度前馈失配（加/减速跟随误差不对称）",
}


def _recommendation(leaf: str, res: LeafResult) -> dict:
    return {
        "action_id": "A%s" % res.scored_rules[0].replace("R-", ""),
        "action": "见 %s#%s 的建议动作（本最小实现不生成参数值）" % (KB3, res.scored_rules[0]),
        "expected_effect": {"basis": "rule_heuristic",
                            "direction": "见 KB3 该条『期望效果与其依据』"},
        "requires_human_approval": True,
        "reversible": True,
    }


def _next_data(leaf: str) -> list[dict]:
    return [{"ask": "补采同一工况 ≥2 个独立样本",
             "why": "KB4 §2.1(c)：当前样本量使 n_factor 低于 1",
             "unlocks": "该叶的全部判据"}]


_C1_CHANNELS = ("pos_cmd", "pos_fb", "fe", "vel_cmd", "vel_fb", "cur_q", "cur_cmd",
                "torque", "temp")


def _inputs(features: dict) -> dict:
    present = list(features.get("present_channels") or [])
    ref = features.get("ref") or {}
    return {"sample_id": ref.get("sample_id", ""),
            "present_channels": present,
            "missing_channels": [c for c in _C1_CHANNELS if c not in present],
            "counts_per_mm": None, "drive_params_known": [], "context_complaint": ""}


def _tier_ledger(hypotheses: list[dict], source_tier: str) -> list[dict]:
    # KB4 §2.10：T2/T3 的上限由文档给定；T1-a 的"改进量"那一半取决于有没有 C4 仿真记录，
    # 本引擎不产 validation[]，所以不得沿用契约示例里带 validation_id 的那句措辞。
    ceiling = {"T1-a": "实测支持现象；改进量无仿真验证记录（C4 未接入）",
               "T2": "按 <出处> 的阈值",
               "T3": "管线上跑通（合成自洽）"}
    if not hypotheses:
        return [{"claim_id": "verdict.summary", "source_tier": source_tier,
                 "wording_ceiling": "零条假设可评分：只登记缺席与不可算，不做归因"}]
    rows = [{"claim_id": "verdict.summary", "source_tier": source_tier,
             "wording_ceiling": ceiling.get(source_tier, "")}]
    for h in hypotheses:
        rows.append({"claim_id": h["id"], "source_tier": source_tier,
                     "wording_ceiling": ceiling.get(source_tier, ""), "validation_id": None})
    return rows


def _summary(hypotheses: list[dict], ranked, overall, source_tier: str) -> str:
    if not hypotheses:
        return ("本样本不足以给出归因：可见性门与缺席项见 differential.not_evaluable，"
                "未成立的候选见 differential.considered。")
    leaf, res = ranked[0]
    score = res.scores[0]
    # KB4 §2.10：叙述强度跟着 source_tier 走，不能对 T1 样本写"管线跑通级"、也不能对 T3 写实测
    level = {"T3": "管线上跑通的结论（合成自洽）"}.get(source_tier) or (
        "%s 级证据上的结论" % source_tier)
    return ("%s：由 %s 的支持证据（A_sup=%.3f、A_con=%.2f）得到置信度 %.2f，"
            "本条为%s，改进量未做仿真验证，故只给方向。"
            % (_DISPLAY.get(leaf, leaf), ", ".join(res.scored_rules), score.a_sup,
               score.a_con, score.c, level))


def _confidence_note(ranked, strengths: list[float], ledger: reg.Ledger) -> str:
    distinct = ledger.distinct_blocked_by
    if not ranked:
        return "无阳性假设，不适用逐格重算。"
    s = ranked[0][1].scores[0]
    return ("KB4 §2.2 逐格：S(e) = %s ⟹ Smax=%.3f、Srest=%.3f、A_sup=%.3f；"
            "A_con=%.2f ⟹ C_mid=%.3f；CAP/乘性 ⟹ C=%.3f。"
            "overall = C×(1−0.05×%d 个独立缺席原因 %s)。"
            % ("/".join("%.3f" % x for x in strengths), s.s_max, s.s_rest, s.a_sup,
               s.a_con, s.c_mid, s.c, len(distinct), ",".join(distinct) or "无"))
