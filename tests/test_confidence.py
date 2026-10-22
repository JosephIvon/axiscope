"""KB4 §2.1–§2.5 置信度模型的逐格复算测试。

正向：算例 A（`mechanical_resonance`，fs 8 kHz）与算例 B（`software_induced_interp_buffer_underrun`，
fs 1 kHz）的每一格（ρ / g / conf / n_factor / band / S(e) / Smax / Srest / A_sup / A_con / C_mid / C /
overall_confidence）都对 KB4 §2.3 的表取整值断言。
负向：规则 15（`penalty` 是 ρ′ 的档位函数）、INV-10、INV-4、INV-1/§2.1(d) 的阻塞与削弱分工、
`bandwidth.confidence` 0.6 天花板、CAP-7 乘性 vs CAP 取 min、A-73 的 `blocked_by` 去重。

容差口径（C3 硬性规则 15：计算全精度，只有展示层取 2 位）：
    · `TOL3 = 1e-3` —— KB 表格给的是 3 位小数，且部分格是用上一格的 3 位取整值再算的
      （算例 A 行 1：g 印 0.574，全精度 0.574245 ⟹ S 全精度 0.459396 vs 表 0.459；
        算例 B 的 A_sup：0.55×0.597 + 0.45×0.418 = 0.516 vs 全精度 0.516593）。
      1e-3 覆盖这种「两位链式取整」，又远小于任何实质公式差异。
    · `TOL2 = 5e-3` —— 表格标注为 2 位的最终量（C、overall_confidence）。

    python -m pytest tests/test_confidence.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from axiscope import confidence as conf          # noqa: E402
from axiscope.confidence import (                # noqa: E402
    BandBlocked,
    DependencyNull,
    Evidence,
    FrequencyContext,
    Hypothesis,
    InsufficientEvidence,
    MissingFeatureScale,
    NotALeaf,
    Refutation,
    RuleNotFired,
    SampleBelowReference,
)

TOL3 = 1e-3
TOL2 = 5e-3

CTX_A = FrequencyContext(fs_hz=8000.0, reliable_band_hz=3200.0, nyquist_hz=4000.0)
CTX_B = FrequencyContext(fs_hz=1000.0, reliable_band_hz=400.0, nyquist_hz=500.0)

R03_FLOOR = 2000.0    # KB3 §2.1 / KB4 §1.1 叶 1 的 band⊥


# --------------------------------------------------------------------------
# 算例 A 的证据表（KB4 §2.3 行 376–383 逐格转写）
# --------------------------------------------------------------------------

def a_row(i: int) -> Evidence:
    return [
        Evidence("resonance.candidates[0].coherence_torque_velocity", 0.86, ">=", 0.7, "R-03",
                 n=8.0, n_ref=4.0, conf=1.0, freq_hz=1181.0, band_floor_hz=R03_FLOOR),
        Evidence("resonance.candidates[0].amplitude_ratio_vs_broadband", 8.4, ">=", 4.0, "R-03",
                 n=96.0, n_ref=15.0, conf=1.0, freq_hz=1181.0, band_floor_hz=R03_FLOOR),
        Evidence("resonance.candidates[0].quality_factor_estimate", 27.0, ">=", 10.0, "R-03",
                 n=22.0, n_ref=8.0, conf=1.0, freq_hz=1181.0, band_floor_hz=R03_FLOOR),
        Evidence("resonance.candidates[0].present_in_dwell", True, "==", True, "R-03",
                 n=3.0, n_ref=1.0, conf=1.0),
        Evidence("resonance.candidates[0].present_in_rest", False, "==", False, "R-03b",
                 n=2.0, n_ref=1.0, conf=1.0),
        Evidence("resonance.candidates[0].tracks_command_frequency", False, "==", False, "R-03",
                 n=6.0, n_ref=4.0, conf=1.0),
    ][i - 1]


# KB4 表格列：ρ, g, n_factor, S(e)（categorical 行无 ρ）
A_CELLS = [
    (1.229, 0.574, 0.80, 0.459),
    (2.100, 0.768, 1.00, 0.768),
    (2.700, 0.858, 0.892, 0.765),
    (None, 0.85, 0.917, 0.779),
    (None, 0.85, 0.80, 0.680),
    (None, 0.85, 0.717, 0.609),
]

A_REFUTATION = Refutation("step_response[0].damping_ratio_estimate", 0.28, ">", 0.15, "R-03c",
                          rho_prime=1.867, penalty=0.10)

# C3 示例 differential.not_evaluable（E1/E2 共用同一前提）：3 行 = 2 个独立缺席原因
A_NOT_EVALUABLE = [
    {"fault_mode": "mechanical_thermal_drift", "blocked_by": "absent_temp_channel",
     "why": "缺 temp 通道，且无冷热机对比"},
    {"fault_mode": "software_induced_host_thread_jitter", "blocked_by": "absent_events_jsonl",
     "why": "本样本无 events.jsonl"},
    {"family": "software_induced_error", "blocked_by": "absent_events_jsonl",
     "why": "事件层缺席使整族降级为不可评估（族级标签只在这里出现）"},
]


def b_row(i: int) -> Evidence:
    return [
        Evidence("event_context.interp_underrun_during_path / interp_underrun_count",
                 11.0 / 12.0, ">=", 0.7, "R-19", n=12.0, n_ref=3.0, conf=1.0),
        Evidence("event_context.fe_spike_aligned_to_underrun / fe_spike_count",
                 11.0 / 17.0, ">=", 0.5, "R-19", n=17.0, n_ref=3.0, conf=1.0),
        Evidence("tracking.path_segments[0].fe_max_counts / .fe_rms_counts",
                 3100.0 / 1520.0, ">=", 2.0, "R-19", n=1.0, n_ref=1.0, conf=1.0),
        Evidence("tracking.path_segments[0].corr_fe_vs_accel",
                 0.91, ">=", 0.7, "R-19", n=1.0, n_ref=1.0, conf=1.0),
    ][i - 1]


B_CELLS = [
    (1.310, 0.597, 1.00, 0.597),
    (1.294, 0.593, 1.00, 0.593),
    (1.020, 0.507, 0.60, 0.304),
    (1.300, 0.595, 0.60, 0.357),
]

B_REFUTATIONS = [
    Refutation("ff_mismatch.asymmetry_ratio", 2.26, ">=", 1.5, "R-15",
               rho_prime=1.507, penalty=0.10),
    Refutation("global.fe_p999_counts / global.fe_rms_counts", 3.34, ">=", 4.0, "R-02",
               rho_prime=0.835, penalty=0.05),
]


# --------------------------------------------------------------------------
# 算例 A：逐格
# --------------------------------------------------------------------------

@pytest.mark.parametrize("i", [1, 2, 3, 4, 5, 6])
def test_example_a_cells(i):
    ev = a_row(i)
    rho, g, n_factor, s = A_CELLS[i - 1]
    if rho is None:
        assert conf.margin_ratio(ev) is None
        assert ev.operator in conf.COMPARATORS_CAT
    else:
        assert conf.margin_ratio(ev) == pytest.approx(rho, abs=TOL3)
        assert conf.saturation_g(conf.margin_ratio(ev)) == pytest.approx(g, abs=TOL3)
    assert conf.sample_factor(ev.n, ev.n_ref, ev.feature) == pytest.approx(n_factor, abs=TOL3)
    assert conf.feature_confidence(ev.feature, ev.conf) == 1.0
    assert conf.band_factor(ev, CTX_A) == 1.0
    assert conf.evidence_strength(ev, CTX_A) == pytest.approx(s, abs=TOL3)


def test_example_a_aggregate():
    score = conf.aggregate(Hypothesis("mechanical_resonance", [a_row(i) for i in range(1, 7)],
                                      [A_REFUTATION]), CTX_A)
    assert score.k == 6
    assert score.s_max == pytest.approx(0.779, abs=TOL3)
    assert score.s_rest == pytest.approx(0.656, abs=TOL3)
    assert score.a_sup == pytest.approx(0.724, abs=TOL3)
    assert score.a_con == pytest.approx(0.10, abs=TOL2)
    assert score.c_mid == pytest.approx(0.652, abs=TOL3)
    assert score.c == pytest.approx(0.652, abs=TOL3)
    assert conf.display(score.c) == 0.65


def test_example_a_overall_confidence():
    score = conf.aggregate(Hypothesis("mechanical_resonance", [a_row(i) for i in range(1, 7)],
                                      [A_REFUTATION]), CTX_A)
    assert conf.distinct_blocked_by(A_NOT_EVALUABLE) == ["absent_temp_channel",
                                                         "absent_events_jsonl"]
    overall = conf.overall_confidence(score, A_NOT_EVALUABLE)
    assert overall == pytest.approx(0.586, abs=TOL3)
    assert conf.display(overall) == 0.59
    assert conf.absent_deduction_factor(A_NOT_EVALUABLE) == pytest.approx(0.90, abs=TOL2)


def test_example_a_refutation_rho_and_tier():
    assert conf.check_refutation(A_REFUTATION) == pytest.approx(0.10, abs=TOL2)
    recomputed = conf._ratio(A_REFUTATION.feature, A_REFUTATION.value,
                             A_REFUTATION.operator, A_REFUTATION.threshold, None)
    assert recomputed == pytest.approx(1.867, abs=TOL3)


# --------------------------------------------------------------------------
# 算例 B：逐格
# --------------------------------------------------------------------------

@pytest.mark.parametrize("i", [1, 2, 3, 4])
def test_example_b_cells(i):
    ev = b_row(i)
    rho, g, n_factor, s = B_CELLS[i - 1]
    got_rho = conf.margin_ratio(ev)
    assert got_rho == pytest.approx(rho, abs=TOL3)
    assert conf.saturation_g(got_rho) == pytest.approx(g, abs=TOL3)
    assert conf.sample_factor(ev.n, ev.n_ref, ev.feature) == pytest.approx(n_factor, abs=TOL3)
    assert conf.band_factor(ev, CTX_B) == 1.0
    assert conf.evidence_strength(ev, CTX_B) == pytest.approx(s, abs=TOL3)


def test_example_b_aggregate():
    score = conf.aggregate(Hypothesis("software_induced_interp_buffer_underrun",
                                      [b_row(i) for i in range(1, 5)], B_REFUTATIONS), CTX_B)
    assert score.k == 4
    assert score.s_max == pytest.approx(0.597, abs=TOL3)
    assert score.s_rest == pytest.approx(0.418, abs=TOL3)
    assert score.a_sup == pytest.approx(0.516, abs=TOL3)
    assert score.a_con == pytest.approx(0.15, abs=TOL2)
    assert score.c_mid == pytest.approx(0.439, abs=TOL3)
    assert score.c == pytest.approx(0.439, abs=TOL3)
    assert conf.display(score.c) == 0.44


def test_example_b_has_no_ceiling_for_this_leaf():
    """CAP-5 触发在谐振族（f_b 400 < band⊥ 2000），对本叶无 ceiling；R-18 另走 time_resolution。"""
    with pytest.raises(BandBlocked) as exc:
        conf.evidence_strength(Evidence("resonance.candidates[0].amplitude_ratio_vs_broadband",
                                        8.4, ">=", 4.0, "R-03", n=96.0, n_ref=15.0, conf=1.0,
                                        freq_hz=1181.0, band_floor_hz=R03_FLOOR), CTX_B)
    assert exc.value.reason == "reliable_band_below_band_floor"
    assert exc.value.rule_id == "R-03"

    score = conf.aggregate(Hypothesis("software_induced_interp_buffer_underrun",
                                      [b_row(i) for i in range(1, 5)], B_REFUTATIONS), CTX_B)
    assert score.c == score.c_mid


# --------------------------------------------------------------------------
# §2.1 锚点（可手核）
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rho,g", [(1.0, 0.500), (1.2, 0.566), (1.5, 0.646),
                                   (2.0, 0.750), (2.7, 0.858), (4.0, 1.000), (9.0, 1.000)])
def test_g_anchors(rho, g):
    assert conf.saturation_g(rho) == pytest.approx(g, abs=TOL3)


@pytest.mark.parametrize("ratio,n_factor", [(1.0, 0.60), (2.0, 0.80), (4.0, 1.00), (6.4, 1.00)])
def test_n_factor_anchors(ratio, n_factor):
    assert conf.sample_factor(ratio * 10.0, 10.0, "f") == pytest.approx(n_factor, abs=TOL3)


@pytest.mark.parametrize("rho_prime,v_j", [(2.0, 0.20), (5.0, 0.20), (1.0, 0.10),
                                           (1.999, 0.10), (0.999, 0.05), (None, 0.00)])
def test_v_j_is_a_discrete_tier_of_rho_prime(rho_prime, v_j):
    assert conf.refutation_penalty(rho_prime) == pytest.approx(v_j)


def test_v_j_tiers_are_the_only_four_values():
    tiers = {conf.refutation_penalty(r) for r in [0.001, 0.5, 0.999, 1.0, 1.5, 2.0, 10.0]}
    assert tiers == {0.05, 0.10, 0.20}
    assert conf.VJ_DEPENDENCY_NULL == 0.00


# --------------------------------------------------------------------------
# 负向：规则 15 —— penalty 不是自由参数
# --------------------------------------------------------------------------

def test_penalty_inconsistent_with_own_rho_prime_is_rejected():
    with pytest.raises(conf.RefutationPenaltyViolation) as exc:
        conf.check_refutation(Refutation("step_response[0].damping_ratio_estimate",
                                         0.28, ">", 0.15, "R-03c",
                                         rho_prime=1.867, penalty=0.18))
    assert exc.value.expected_penalty == 0.10
    assert exc.value.declared_penalty == 0.18
    with pytest.raises(conf.RefutationPenaltyViolation):
        conf.check_refutation(Refutation("ff_mismatch.asymmetry_ratio", 2.26, ">=", 1.5, "R-15",
                                         rho_prime=1.507, penalty=0.11))
    with pytest.raises(conf.RefutationPenaltyViolation):
        conf.check_refutation(Refutation("global.fe_p999_counts", 3.34, ">=", 4.0, "R-02",
                                         rho_prime=0.835, penalty=0.0))


def test_rho_prime_declared_from_the_wrong_side_is_rejected():
    """C3 H2 反证：op `<` 的 ρ′ 按 §2.1(a) 是 threshold/value，声明的 1.672 是反着除的。"""
    rf = Refutation("ff_mismatch.accel_regime_rms_counts", 690.0, "<", 412.6, "R-15c",
                    rho_prime=1.672, penalty=0.10)
    with pytest.raises(conf.RefutationPenaltyViolation) as exc:
        conf.check_refutation(rf)
    assert "1.672" in str(exc.value)
    assert conf.refutation_penalty(conf._ratio(rf.feature, 690.0, "<", 412.6, None)) == 0.05


def test_rho_prime_tolerance_absorbs_the_kb_display_rounding():
    """算例 B 反证 2 的 ρ′ 由 3.34（1380/412.6 的 3 位显示值）再除得到；档位不变。"""
    rf = Refutation("global.fe_p999_counts / global.fe_rms_counts",
                    1380.0 / 412.6, ">=", 4.0, "R-02", rho_prime=0.835, penalty=0.05)
    assert conf.check_refutation(rf) == pytest.approx(0.05)


def test_a_con_is_capped_at_half():
    strong = [Refutation("f%d" % i, 4.0, ">=", 1.0, "R-03", rho_prime=4.0, penalty=0.20)
              for i in range(4)]
    score = conf.aggregate(Hypothesis("mechanical_resonance",
                                      [a_row(2), a_row(4)], strong), CTX_A)
    assert score.a_con == pytest.approx(0.5, abs=TOL2)
    assert score.c == pytest.approx(score.a_sup * 0.5, abs=TOL3)


# --------------------------------------------------------------------------
# 负向：INV-10
# --------------------------------------------------------------------------

def test_single_supporting_evidence_is_rejected_not_downgraded():
    with pytest.raises(InsufficientEvidence) as exc:
        conf.aggregate(Hypothesis("mechanical_resonance", [a_row(2)], [A_REFUTATION]), CTX_A)
    assert exc.value.fault_mode == "mechanical_resonance"


def test_empty_evidence_is_rejected():
    with pytest.raises(InsufficientEvidence):
        conf.aggregate(Hypothesis("mechanical_backlash", []), CTX_A)


# --------------------------------------------------------------------------
# 负向：INV-4 —— null 既不是 false 也不是 0/1
# --------------------------------------------------------------------------

def test_null_value_is_dependency_null_not_zero():
    with pytest.raises(DependencyNull):
        conf.evidence_strength(Evidence("resonance.candidates[0].coherence_torque_velocity",
                                        None, ">=", 0.7, "R-03", n=8.0, n_ref=4.0, conf=1.0), CTX_A)


def test_null_boolean_is_dependency_null_not_false():
    """CAP-3 的触发形态：present_in_rest 为 null（缺 rest 段）⟹ 该边不可通行，不是 `false` 证据。"""
    with pytest.raises(DependencyNull):
        conf.evidence_strength(Evidence("resonance.candidates[0].present_in_rest",
                                        None, "==", False, "R-03b", n=2.0, n_ref=1.0, conf=1.0),
                               CTX_A)


def test_boolean_false_is_not_null():
    assert conf.evidence_strength(a_row(5), CTX_A) == pytest.approx(0.680, abs=TOL3)


def test_null_conf_is_not_one():
    with pytest.raises(DependencyNull):
        conf.evidence_strength(Evidence("resonance.candidates[0].quality_factor_estimate",
                                        27.0, ">=", 10.0, "R-03", n=22.0, n_ref=8.0, conf=None),
                               CTX_A)


def test_null_dependency_refutation_scores_zero_and_is_not_a_refutation():
    rf = Refutation("resonance.candidates[0].present_in_rest", None, "==", False, "R-03",
                    penalty=0.0)
    assert conf.check_refutation(rf) == 0.0
    score = conf.aggregate(Hypothesis("mechanical_resonance", [a_row(2), a_row(4)], [rf]), CTX_A)
    assert score.a_con == 0.0
    assert score.c == pytest.approx(score.a_sup, abs=TOL3)


def test_missing_sample_count_is_not_silently_full_credit():
    with pytest.raises(MissingFeatureScale):
        conf.evidence_strength(Evidence("resonance.candidates[0].amplitude_ratio_vs_broadband",
                                        8.4, ">=", 4.0, "R-03", conf=1.0), CTX_A)


def test_sample_below_reference_is_rejected():
    """§2.1(c)：n < n_ref 时 C2 本该输出 null，故 n_factor 不得小于 0.6。"""
    with pytest.raises(SampleBelowReference):
        conf.sample_factor(47.0, 50.0, "ff_mismatch.asymmetry_ratio")


# --------------------------------------------------------------------------
# 负向：§2.1(a) ρ<1 不产支持证据；categorical 形态未出现同理
# --------------------------------------------------------------------------

def test_rho_below_one_fires_no_supporting_evidence():
    with pytest.raises(RuleNotFired):
        conf.evidence_strength(Evidence("global.fe_p999_counts / global.fe_rms_counts",
                                        3.34, ">=", 4.0, "R-02", n=17.0, n_ref=3.0, conf=1.0),
                               CTX_B)


def test_boolean_shape_absent_fires_no_supporting_evidence():
    with pytest.raises(RuleNotFired):
        conf.evidence_strength(Evidence("resonance.candidates[0].present_in_rest",
                                        True, "==", False, "R-03b", n=2.0, n_ref=1.0, conf=1.0),
                               CTX_A)


# --------------------------------------------------------------------------
# 负向：INV-1 / §2.1(d) —— 阻塞（无证据）≠ 削弱（×0.80）
# --------------------------------------------------------------------------

def test_band_weakening_at_the_upper_edge():
    ev = Evidence("resonance.candidates[0].amplitude_ratio_vs_broadband", 8.4, ">=", 4.0, "R-03",
                  n=96.0, n_ref=15.0, conf=1.0, freq_hz=3000.0, band_floor_hz=R03_FLOOR)
    assert conf.band_factor(ev, CTX_A) == pytest.approx(0.80, abs=TOL2)
    assert conf.evidence_strength(ev, CTX_A) == pytest.approx(0.768 * 0.80, abs=TOL3)
    assert conf.evidence_strength(a_row(2), CTX_A) == pytest.approx(0.768, abs=TOL3)


def test_near_nyquist_candidate_is_blocked_before_it_can_score():
    """INV-2：f0 ≥ 0.8·f_N 的候选必须先过 R-10，不得直接进 mechanical_* 叶。"""
    ev = Evidence("resonance.candidates[0].amplitude_ratio_vs_broadband", 8.4, ">=", 4.0, "R-03",
                  n=96.0, n_ref=15.0, conf=1.0, freq_hz=3200.0, band_floor_hz=R03_FLOOR)
    with pytest.raises(BandBlocked) as exc:
        conf.evidence_strength(ev, CTX_A)
    assert exc.value.reason == "near_nyquist_r10_vetting"


def test_freq_above_reliable_band_is_blocked_not_weakened():
    ev = Evidence("resonance.candidates[0].freq_hz", 1181.0, ">=", 1000.0, "R-03",
                  n=96.0, n_ref=15.0, conf=1.0, freq_hz=2500.0, band_floor_hz=R03_FLOOR)
    with pytest.raises(BandBlocked) as exc:
        conf.evidence_strength(ev, FrequencyContext(fs_hz=8000.0, reliable_band_hz=2000.0,
                                                   nyquist_hz=4000.0))
    assert exc.value.reason == "above_reliable_band"


def test_blocked_leaf_has_no_score_at_all():
    """CAP-5：越带叶的正确处置是「证据不存在」，不是 S=0 / C=0 的假设。"""
    blocked = Hypothesis("mechanical_resonance",
                         [Evidence("resonance.candidates[0].amplitude_ratio_vs_broadband",
                                   8.4, ">=", 4.0, "R-03", n=96.0, n_ref=15.0, conf=1.0,
                                   freq_hz=1181.0, band_floor_hz=R03_FLOOR),
                          a_row(4)],
                         [A_REFUTATION])
    with pytest.raises(BandBlocked):
        conf.aggregate(blocked, CTX_B)


def test_band_floor_is_required_for_frequency_criteria():
    with pytest.raises(MissingFeatureScale):
        conf.band_factor(Evidence("spectral.fe.dominant_freq_hz", 100.0, ">=", 50.0, "R-07",
                                  n=4.0, n_ref=4.0, conf=1.0, freq_hz=120.0), CTX_A)


def test_epsilon_f_is_required_when_threshold_is_not_positive():
    with pytest.raises(MissingFeatureScale):
        conf.margin_ratio(Evidence("global.thermal_drift_counts_per_min", 5.0, ">=", 0.0, "R-01",
                                   n=4.0, n_ref=4.0, conf=1.0))
    ev = Evidence("global.thermal_drift_counts_per_min", 5.0, ">=", 0.0, "R-01",
                  n=4.0, n_ref=4.0, conf=1.0, eps=0.5)
    assert conf.margin_ratio(ev) == pytest.approx(10.0, abs=TOL3)


# --------------------------------------------------------------------------
# 负向：CAP-1 / KB3 §1.10 —— bandwidth.confidence 的 0.6 天花板不可抬高
# --------------------------------------------------------------------------

def test_bandwidth_feature_confidence_is_capped_at_six_tenths():
    capped = Evidence("bandwidth.position_loop_crossover_hz", 120.0, ">=", 100.0, "R-13",
                      n=6.0, n_ref=3.0, conf=0.9)
    assert conf.feature_confidence(capped.feature, 0.9) == 0.6
    assert conf.evidence_strength(capped, CTX_A) == pytest.approx(
        conf.saturation_g(1.2) * 0.6 * conf.sample_factor(6.0, 3.0, "f"), abs=TOL3)
    assert conf.evidence_strength(
        Evidence("bandwidth.position_loop_crossover_hz", 120.0, ">=", 100.0, "R-13",
                 n=6.0, n_ref=3.0, conf=0.6), CTX_A) == \
        conf.evidence_strength(capped, CTX_A)


def test_cap1_ceiling_still_applies_to_the_hypothesis():
    """支持链含 `bandwidth.*` ⟹ 特征级 conf 封顶 0.6（§2.1(b)）之外，假设级另走 CAP-1 取 min。"""
    score = conf.aggregate(Hypothesis("electrical_velocity_pi_detune", [a_row(2), a_row(4)], [],
                                      ceilings=[0.60]), CTX_A)
    assert score.c_mid > 0.60
    assert score.c == pytest.approx(0.60, abs=TOL2)


# --------------------------------------------------------------------------
# 负向：CAP-7 是乘性惩罚，其余 CAP 是取 min（§2.5 行 484 vs §2.2 行 352）
# --------------------------------------------------------------------------

def test_cap7_multiplies_while_other_caps_take_min():
    ev = [a_row(2), a_row(4)]
    base = conf.aggregate(Hypothesis("mechanical_resonance", ev), CTX_A)
    capped = conf.aggregate(Hypothesis("mechanical_resonance", ev, [], ceilings=[0.55]), CTX_A)
    derived = conf.aggregate(Hypothesis("mechanical_resonance", ev, [], multiplicative=[0.70]),
                             CTX_A)
    both = conf.aggregate(Hypothesis("mechanical_resonance", ev, [], ceilings=[0.55],
                                     multiplicative=[0.70]), CTX_A)
    assert capped.c == pytest.approx(0.55, abs=TOL3)
    assert derived.c == pytest.approx(base.c_mid * 0.70, abs=TOL3)
    assert both.c == pytest.approx(0.55 * 0.70, abs=TOL3)
    assert both.c != pytest.approx(min(base.c_mid * 0.70, 0.55), abs=1e-6)
    assert both.c != pytest.approx(base.c_mid * 0.55 * 0.70, abs=1e-6)


def test_two_ceilings_do_not_stack_multiplicatively():
    ev = [a_row(2), a_row(4)]
    score = conf.aggregate(Hypothesis("mechanical_resonance", ev, [], ceilings=[0.55, 0.65]),
                           CTX_A)
    assert score.c == pytest.approx(0.55, abs=TOL3)


# --------------------------------------------------------------------------
# 负向：A-73 / 规则 16 —— 按独立缺席原因去重；INV-16 —— 族级行不是假设
# --------------------------------------------------------------------------

def test_three_rows_two_reasons_cost_nine_percent_not_fifteen():
    assert conf.distinct_blocked_by(A_NOT_EVALUABLE) == ["absent_temp_channel",
                                                         "absent_events_jsonl"]
    assert conf.absent_deduction_factor(A_NOT_EVALUABLE) == pytest.approx(0.90, abs=TOL2)
    rows_by_kind = [dict(r, blocked_by="absent_events_jsonl") for r in A_NOT_EVALUABLE]
    assert conf.distinct_blocked_by(rows_by_kind) == ["absent_events_jsonl"]
    assert conf.absent_deduction_factor(rows_by_kind) == pytest.approx(0.95, abs=TOL2)


def test_absent_deduction_is_capped_at_twenty_percent():
    rows = [{"fault_mode": "mechanical_crawling", "blocked_by": "r%d" % i, "why": "x"}
            for i in range(7)]
    assert conf.absent_deduction_factor(rows) == pytest.approx(0.80, abs=TOL2)
    assert conf.overall_confidence(1.0, rows) == pytest.approx(0.80, abs=TOL2)


@pytest.mark.parametrize("row", [
    {"family": "software_induced_error", "why": "缺 blocked_by 键"},
    {"fault_mode": "software_induced_error", "blocked_by": "absent_events_jsonl", "why": "键位错"},
    {"blocked_by": "absent_events_jsonl", "why": "两个键都没有"},
    {"fault_mode": "mechanical_crawling", "family": "software_induced_error",
     "blocked_by": "absent_events_jsonl", "why": "两个键都写"},
])
def test_not_evaluable_row_key_discipline(row):
    with pytest.raises((NotALeaf, conf.ConfidenceError)):
        conf.distinct_blocked_by([row])


def test_family_label_never_becomes_a_hypothesis():
    with pytest.raises(NotALeaf):
        Hypothesis("software_induced_error", [a_row(2), a_row(4)])
    with pytest.raises(NotALeaf):
        Hypothesis("R-25", [a_row(2), a_row(4)])


def test_overall_confidence_of_a_float_primary():
    assert conf.overall_confidence(0.652, A_NOT_EVALUABLE) == pytest.approx(0.586, abs=TOL3)


# --------------------------------------------------------------------------
# 手写数的指纹（A-101 ① 已从契约示例里撤销）：草稿给前馈支持证据写 strength 0.41 / 0.36，
# 而 §2.1 由其声明的原始输入复算不出这两个数。契约示例现在自带 n=100/n_ref=50 的复算值
# （0.518/0.494），这里保留的是**最保守读法**（n=n_ref=下限 50）的指纹判据。
# --------------------------------------------------------------------------

FF_FLOOR = 50.0     # §2.1(c)：ff_mismatch 加/减速样本各 ≥ 50（KB3 R-15 必要上下文）


def ff_inputs():
    return [Evidence("ff_mismatch.asymmetry_ratio", 2.26, ">=", 1.5, "R-15a",
                     n=FF_FLOOR, n_ref=FF_FLOOR, conf=1.0),
            Evidence("ff_mismatch.fe_vs_accel_corr", 0.83, ">=", 0.6, "R-15b",
                     n=FF_FLOOR, n_ref=FF_FLOOR, conf=1.0)]


def test_feedforward_strengths_are_not_reproducible_from_the_stated_inputs():
    """旧草稿写 strength 0.41/0.36（⟹ A_sup 0.388、C 0.35），但按 §2.1 复算不是这两个数。

    要得到 0.41/0.36 需要 n_factor ≈ 0.633/0.583（即 n/n_ref ≈ 1.121/0.944）：
    前者不是任何登记过的样本量，后者低于 §2.1(c) 的下限（n<n_ref ⟹ C2 本该给 null）。
    取 §2.1(c) 的 ff_mismatch 下限（各 50 个样本，n = n_ref ⟹ 0.60）作最保守读法。
    """
    ev = ff_inputs()
    strengths = [conf.evidence_strength(e, CTX_B) for e in ev]
    assert strengths[0] == pytest.approx(0.3887, abs=TOL3)
    assert strengths[1] == pytest.approx(0.3702, abs=TOL3)
    score = conf.aggregate(Hypothesis("electrical_feedforward_mismatch", ev), CTX_B)
    assert score.a_sup == pytest.approx(0.3804, abs=TOL3)
    assert strengths != [0.41, 0.36]


def test_feedforward_refutation_penalty_is_not_the_tier_of_its_own_rho_prime():
    """草稿声明 rho_prime 1.672 / penalty 0.10；§2.1(a) 对 op `<` 给 412.6/690 = 0.598 ⟹ 0.05（A-101 ②）。"""
    rf = Refutation("ff_mismatch.accel_regime_rms_counts", 690.0, "<", 412.6, "R-15c",
                    rho_prime=1.672, penalty=0.10)
    with pytest.raises(conf.RefutationPenaltyViolation):
        conf.check_refutation(rf)
    corrected = Refutation("ff_mismatch.accel_regime_rms_counts", 690.0, "<", 412.6, "R-15c",
                           penalty=0.05)
    score = conf.aggregate(Hypothesis("electrical_feedforward_mismatch", ff_inputs(), [corrected]),
                           CTX_B)
    assert score.a_con == pytest.approx(0.05, abs=TOL2)
    assert score.c == pytest.approx(0.3614, abs=TOL3)
    assert conf.display(score.c) == 0.36
