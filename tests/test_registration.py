"""登记层的义务测试：INV-1/2/5/6/7/11/16 与 R-25/R-30 的三分支退出。

这些测试钉的是**措辞与键名**——登记义务一旦自造 `why` 或 `blocked_by`，
C5 的拒答正确率就对不上分母，而散文里看不出问题。
"""
from __future__ import annotations

import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from axiscope import registration as reg  # noqa: E402


def features_example_b():
    with open(os.path.join(ROOT, "examples", "c2_example_b.json"), encoding="utf-8") as fh:
        return json.load(fh)


def features_case_b():
    with open(os.path.join(ROOT, "examples", "kb4_case_b_features.json"), encoding="utf-8") as fh:
        return json.load(fh)


def features_example_a():
    with open(os.path.join(ROOT, "examples", "c2_example_a.json"), encoding="utf-8") as fh:
        return json.load(fh)


# --- INV-1 频带门禁 ---

def test_band_gate_prunes_resonance_at_1khz():
    rows = reg.band_gate(features_example_b(), "mechanical_resonance")
    kinds = {r["kind"] for r in rows}
    assert kinds == {"blocked_rules", "not_evaluable", "rules_skipped"}
    blocked = next(r for r in rows if r["kind"] == "blocked_rules")
    assert blocked["rule_ids"] == ["R-03", "R-04"]
    assert blocked["feature"] == "resonance.candidates"
    assert blocked["reason"] == "f_b=400 Hz < 需要的 2000 Hz"
    ne = next(r for r in rows if r["kind"] == "not_evaluable")
    # R-25 原文措辞，不得改写（KB4 §1.5 第 3 条）
    assert ne["why"] == "fs 不足，该频段无信息（不代表不存在）"
    assert ne["blocked_by"] == "band_gate_fs_1k"


def test_band_gate_never_blocks_always_on_rules():
    """R-10 是伪峰检测器、R-25 是频带门禁本身，在低采样率数据上恰恰最需要运行。"""
    for leaf in reg.LEAVES:
        for row in reg.band_gate(features_example_b(), leaf):
            for rid in row.get("rule_ids", []):
                assert rid not in reg.GATE_RULES


def test_band_gate_is_noop_at_8khz():
    assert reg.band_gate(features_example_a(), "mechanical_resonance") == []


def test_band_gate_is_leaf_specific():
    """同一份 f_b = 400 Hz 的数据：R-03/R-04（2000 Hz）被剪，R-09（150 Hz）不受影响。"""
    f = features_example_b()
    assert reg.band_gate(f, "mechanical_double_inertia") == []
    assert reg.band_gate(f, "mechanical_crawling") == []


def test_band_gate_branch_granularity_matches_a79():
    """R-11 的 150 Hz 谐波主判据在 400 Hz 带内仍可评，只有 `switching_freq` 支路越带：
    此时叶**不**登记 not_evaluable，仅按 `R-11#switching_freq` 支路登记（A-79）。"""
    rows = reg.band_gate(features_example_b(), "electrical_torque_ripple")
    assert {r["kind"] for r in rows} == {"blocked_rules", "rules_skipped"}
    blocked = [r for r in rows if r["kind"] == "blocked_rules"]
    assert blocked[0]["rule_ids"] == ["R-11#switching_freq"]
    assert blocked[0]["feature"] == "spectral.cur_q.dominant_freq_hz"
    assert blocked[0]["reason"] == "f_b=400 Hz < 支路需要的 2000 Hz"


def test_branch_and_whole_granularity_never_collapsed():
    """`R-11` 整条进 blocked_rules 就是谎报"纹波判据全不可用"（C2 规则 7 支路限定）。"""
    for row in reg.band_gate(features_example_b(), "electrical_torque_ripple"):
        assert "R-11" not in row.get("rule_ids", [])


# --- INV-2 近奈奎斯特 ---

def test_near_nyquist_prunes_instead_of_registering_absence():
    f = copy.deepcopy(features_example_a())
    f["resonance"]["candidates"][0]["freq_hz"] = 3400.0
    rows = reg.near_nyquist(f)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"rules_skipped", "consider"}
    assert "f0=3400 Hz >= 0.8*f_N，须先过 R-10" in rows[0]["reason"]
    assert rows[1]["slug"] == "mechanical_resonance"


def test_far_from_nyquist_needs_no_vetting():
    assert reg.near_nyquist(features_example_a()) == []


# --- §1.5 软件族三分支 ---

def test_e1_no_events_registers_seven_slugs_plus_family():
    ledger = reg.Ledger()
    branch = reg.software_family(features_example_b(), ledger)
    assert branch == "E1"
    modes = [r["fault_mode"] for r in ledger.not_evaluable if "fault_mode" in r]
    assert sorted(modes) == sorted(reg.SOFTWARE_SLUGS)
    family_rows = [r for r in ledger.not_evaluable if "family" in r]
    assert family_rows == [{"family": "software_induced_error",
                            "blocked_by": "absent_events_jsonl",
                            "why": "无事件上下文，无法区分机械尖峰与调度抖动"}]
    assert "software_induced_error" not in modes
    skipped = {s["rule_id"] for s in ledger.rules_skipped}
    assert {"R-18", "R-19", "R-20", "R-21", "R-22", "R-23", "R-24", "R-28"} <= skipped
    assert "R-30" in ledger.rules_fired
    assert ledger.considered == []


def test_e2_unverified_sync_degrades_to_co_observation():
    f = copy.deepcopy(features_case_b())
    f["event_context"]["sync"]["verified"] = False
    f["event_context"]["causal_claims_permitted"] = False
    ledger = reg.Ledger()
    assert reg.software_family(f, ledger) == "E2"
    assert sorted(ledger.considered) == sorted(reg.SOFTWARE_SLUGS)
    assert ledger.notes["software_induced_interp_buffer_underrun"] == "时钟未对齐，共现不等于因果"
    assert {r["blocked_by"] for r in ledger.not_evaluable} == {"sync_unverified"}


def test_e3_is_leaf_granular_not_family_granular():
    """算例 B 的核心：同一份 fs=1 kHz 数据上 R-18 被时基剪枝，R-19 仍可运行。
    族级判断代替叶级判断就会把整族一起否掉，KB4 §1.3 明文禁止。"""
    f = features_case_b()
    gates = reg.event_gates(f)
    assert gates["G1"] and gates["G2"] and gates["G3"] and gates["G4"]
    assert gates["G5"] is False
    ledger = reg.Ledger()
    assert reg.software_family(f, ledger) == "E3"
    reasons = {s["rule_id"]: s["reason"] for s in ledger.rules_skipped}
    assert set(reasons) == {"R-18"}
    assert reasons["R-18"].startswith("time_resolution")
    assert "1/fs=1 ms > τ_u/2=0.5 ms" in reasons["R-18"]
    assert ledger.not_evaluable == []


def test_g5_passes_on_8khz_sample():
    gates = reg.event_gates(features_example_a())
    assert gates["G5"] is True
    assert gates["tau_u_ms"] == 0.5


def test_missing_tau_u_falls_back_to_5ms_and_records_assumption():
    f = copy.deepcopy(features_case_b())
    f["event_context"]["sync"]["uncertainty_ms"] = None
    assert reg.event_gates(f)["tau_u_ms"] == 5.0
    ledger = reg.Ledger()
    reg.software_family(f, ledger)
    assert [a["anchor"] for a in ledger.assumptions] == ["event_context.sync.uncertainty_ms"]
    assert "KB3 纪律 6" in ledger.assumptions[0]["statement"]


# --- 热族（INV-15）---

def test_thermal_family_without_temp_channel():
    ledger = reg.Ledger()
    reg.thermal_family(features_example_b(), ledger)
    rows = {r["fault_mode"]: r for r in ledger.not_evaluable}
    assert rows["mechanical_thermal_drift"]["why"] == "缺 temp 通道，且无冷热机对比"
    assert rows["electrical_motor_heating"]["blocked_by"] == "absent_temp_channel"
    assert ledger.distinct_blocked_by == ["absent_temp_channel"]


def test_thermal_family_is_silent_when_temp_present():
    f = copy.deepcopy(features_example_b())
    f["present_channels"] = f["present_channels"] + ["temp"]
    ledger = reg.Ledger()
    reg.thermal_family(f, ledger)
    assert ledger.not_evaluable == []


# --- Ledger 本身：去重、闭集、独立缺席原因计数 ---

def test_ledger_dedups_identical_rows():
    ledger = reg.Ledger()
    row = {"fault_mode": "mechanical_thermal_drift", "blocked_by": "absent_temp_channel",
           "why": reg.WHY_NO_TEMP}
    ledger.register(row)
    ledger.register(dict(row))
    assert len(ledger.not_evaluable) == 1


def test_distinct_blocked_by_counts_reasons_not_rows():
    """C3 规则 16 / A-73：族级行与它覆盖的叶同源，只扣一次。"""
    ledger = reg.Ledger()
    reg.thermal_family(features_example_b(), ledger)
    reg.software_family(features_example_b(), ledger)
    assert len(ledger.not_evaluable) == 10
    assert ledger.distinct_blocked_by == ["absent_events_jsonl", "absent_temp_channel"]


def test_invented_blocked_by_key_is_rejected():
    ledger = reg.Ledger()
    with pytest.raises(reg.BlockedByKey):
        ledger.register({"fault_mode": "mechanical_backlash",
                         "blocked_by": "we_did_not_like_this_run", "why": "?"})


def test_all_emitted_keys_are_declared():
    """把闭集变成可验证的：跑一遍所有会登记的分支，产出的键必须都在表里。"""
    emitted = set()
    for fn, feat in [(reg.software_family, features_example_b()),
                     (reg.thermal_family, features_example_b()),
                     (reg.software_family, features_case_b())]:
        ledger = reg.Ledger()
        fn(feat, ledger)
        emitted |= {r["blocked_by"] for r in ledger.not_evaluable}
    for row in reg.band_gate(features_example_b(), "mechanical_resonance"):
        if "blocked_by" in row:
            emitted.add(row["blocked_by"])
    for row in reg.near_nyquist(features_example_a()):
        emitted.add(row["blocked_by"])
    assert emitted <= reg._BLOCKED_BY


def test_registration_and_validator_share_one_blocked_by_vocabulary():
    """生产者与校验器必须认同一个闭集。

    两处各抄一份时，`c3validate` 许可而 `registration` 抛 `BlockedByKey` 这类反向矛盾
    不会被任何既有测试发现——`test_all_emitted_keys_are_declared` 只查「产出的 ⊆ 登记层」，
    查不到「登记层 ⊆ 校验器」。这个断言补的就是那条缺失的方向。
    """
    assert reg._BLOCKED_BY == set(reg.c3validate.ALLOWED_BLOCKED_BY)


def test_every_c1_channel_has_a_blocked_by_key():
    """C1 加了通道却没人能登记「该通道缺失」，KB8 §1.5 的原因义务在这一类上就落空。"""
    from axiscope import assertions

    for channel in assertions.C1_VOCAB:
        assert f"absent_{channel}_channel" in reg._BLOCKED_BY


def test_invented_channel_shaped_key_is_rejected():
    """通道形键只有 C1 词表里的那些算数，形似不是许可。"""
    ledger = reg.Ledger()
    with pytest.raises(reg.BlockedByKey):
        ledger.register({"fault_mode": "mechanical_backlash",
                         "blocked_by": "absent_torque_cmd_channel", "why": "?"})

def test_rule_table_citations_land_on_their_kb3_headings():
    """`src_line` 是引用完整性的载体（KB0 §6）：KB3 一插行，行号就漂，散文里看不出来。
    A-100 补 R-26 第 6 支后把 9 条全部核对并重钉；R-26 的 chain 须与 KB3 的 1–6 支同数。"""
    with open(os.path.join(ROOT, "src", "axiscope", "rule_table.json"), encoding="utf-8") as fh:
        table = json.load(fh)
    with open(os.path.join(ROOT, "docs", "kb", "KB3-tuning-rules.md"), encoding="utf-8") as fh:
        kb3 = fh.read().split("\n")
    for rid, row in table["rules"].items():
        line = kb3[row["src_line"] - 1]
        assert line.startswith("### " + rid + " "), (rid, line[:48])
    assert [c["n"] for c in table["rules"]["R-26"]["chain"]] == [1, 2, 3, 4, 5, 6]
