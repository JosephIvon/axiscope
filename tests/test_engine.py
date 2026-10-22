"""C3 引擎编排的验收：三个向量的数值必须与 KB4 §2.3 手核算例逐格一致，
且引擎产出的报告要能通过 C3 契约校验器（规则 3/15 的独立复算路径）。
"""
import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from axiscope import anchors, c3validate, confidence, core_hash, engine, report  # noqa: E402

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")

# 算例 A 的两条样本量：A-102 ② 已把载体落进 C2（`resonance.estimation.n_segments` /
# `bins_in_band`），但引擎按 A-102 ③ 的过渡口径仍只吃侧车 ⟹ 由调用方按 KB4 §2.3
# 表格里写明的数显式带入，并在 `audit.assumptions` 留一行痕。
CASE_A_COUNTS = {"welch_segments": 8, "band_bins": 96}


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return json.load(fh)


def _hyp(report, fault_mode):
    for h in report["hypotheses"]:
        if h["fault_mode"] == fault_mode:
            return h
    raise AssertionError("报告中没有 %s（假设=%s）" % (fault_mode, [h["fault_mode"] for h in report["hypotheses"]]))


def _fails(report):
    return [c for c in c3validate.validate(report) if not c.passed]


# ---------------------------------------------------------------- 向量 1：KB4 算例 A

def test_case_a_resonance_reproduces_kb4_strengths():
    """六条 S(e) 与 KB4 §2.3 算例 A 的表格逐格同数（数值集合，不依赖行的排列）。"""
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    h = _hyp(report, "mechanical_resonance")
    assert sorted(e["strength"] for e in h["supporting_evidence"]) == sorted(
        [0.459, 0.768, 0.765, 0.779, 0.680, 0.609])
    assert h["confidence"] == 0.65
    assert [e["condition_index"] for e in h["supporting_evidence"]] == [2, 3, 4, 5, 6, 7]
    assert h["severity"] == 3


def test_case_a_resonance_refuter_is_r03c_with_declared_tier():
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    h = _hyp(report, "mechanical_resonance")
    assert [(r["rule_id"], r["rho_prime"], r["penalty"]) for r in h["contradicting_evidence"]] == [
        ("R-03c", 1.867, 0.10)]


def test_case_a_without_events_is_the_contract_verdict_059():
    """C3 示例的 0.59 前提是"无 events.jsonl"，其载体是 `examples/c2_example_a_no_events.json`
    （A-99 ①：前提要有文件，不能只在测试里就地改内存字典）。孪生本体与两条前提的比对归
    tests/test_snapshot_premises.py；这里只认引擎在该快照上的判决。"""
    report = engine.analyze(_load("c2_example_a_no_events.json"), sample_counts=CASE_A_COUNTS)
    assert report["verdict"]["primary"] == _hyp(report, "mechanical_resonance")["id"]
    assert report["verdict"]["overall_confidence"] == 0.59
    keys = sorted({r["blocked_by"] for r in report["differential"]["not_evaluable"]})
    assert keys == ["absent_events_jsonl", "absent_temp_channel"]
    assert not _fails(report)


def test_case_a_engine_report_recomputes_independently():
    """规则 15：报告自带的原始字段（n/n_ref/conf）要能撑起独立复算，不留 gap。"""
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    h = _hyp(report, "mechanical_resonance")
    det = c3validate._recompute_detail(
        h, c3validate._confidence_ctx(report))
    assert det.gap is None
    assert det.strength_violations == [] and det.refutation_violations == []
    assert round(det.c, 3) == 0.652


# ---------------------------------------------------------------- 向量 2：KB4 算例 B

def test_case_b_underrun_reproduces_kb4():
    report = engine.analyze(_load("kb4_case_b_features.json"))
    h = _hyp(report, "software_induced_interp_buffer_underrun")
    assert [e["strength"] for e in h["supporting_evidence"]] == [0.597, 0.593, 0.304, 0.357]
    assert [e["condition_index"] for e in h["supporting_evidence"]] == [2, 3, 4, 6]
    assert h["confidence"] == 0.44
    assert [(r["rho_prime"], r["penalty"]) for r in h["contradicting_evidence"]] == [
        (1.507, 0.10), (0.836, 0.05)]


def test_case_b_leaf_granularity_r18_skipped_but_r19_runs():
    """同一份数据上软件族内部可评估性不同：族级判断不能代替叶级判断（KB4 §2.3 算例 B）。"""
    report = engine.analyze(_load("kb4_case_b_features.json"))
    skipped = {s["rule_id"]: s["reason"] for s in report["audit"]["rules_skipped"]}
    assert "R-18" in skipped and "time_resolution" in skipped["R-18"]
    assert "R-19" in report["audit"]["rules_fired"]
    assert not [h for h in report["hypotheses"]
                if h["fault_mode"] == "software_induced_host_thread_jitter"]


def test_case_b_low_confidence_requires_next_data():
    report = engine.analyze(_load("kb4_case_b_features.json"))
    h = _hyp(report, "software_induced_interp_buffer_underrun")
    assert h["confidence"] < 0.6
    assert h["next_data_to_collect"]
    for row in h["next_data_to_collect"]:
        assert row["ask"] and row["why"] and row["unlocks"]


def test_case_b_band_gate_registers_absence_not_silence():
    report = engine.analyze(_load("kb4_case_b_features.json"))
    ne = {(r.get("fault_mode") or r.get("family")): r["blocked_by"]
          for r in report["differential"]["not_evaluable"]}
    assert ne["mechanical_resonance"] == "band_gate_fs_1k"
    assert "R-03" in report["freq_limits"]["blocked_rules"]
    assert not _fails(report)


# ---------------------------------------------------------------- 向量 3：真实样本的诚实真空

def test_export10_is_honest_vacuum():
    path = os.path.join(os.path.dirname(__file__), "..", "build",
                        "Export10_244531", "features.json")
    if not os.path.exists(path):
        pytest.skip("先跑 python -m axiscope --in data/raw/Export10_244531.csv --out build/…")
    report = engine.analyze(json.load(open(path, encoding="utf-8")), source_tier="T1-a")
    assert report["hypotheses"] == []
    assert report["verdict"]["primary"] is None
    reasons = {r["blocked_by"] for r in report["differential"]["not_evaluable"]}
    assert {"band_gate_fs_1k", "absent_events_jsonl", "absent_temp_channel"} <= reasons
    assert not _fails(report)


# ---------------------------------------------------------------- 不可复算时不得静默放行

def test_unscoreable_rule_is_reported_as_skip_not_invented_number():
    """R-15 的样本量参考在 KB4 §2.1(c) 没有对应行 ⟹ 只能记 skip，不能编一个 n_factor。"""
    report = engine.analyze(_load("kb4_case_b_features.json"))
    skipped = {s["rule_id"]: s["reason"] for s in report["audit"]["rules_skipped"]}
    assert "R-15" in skipped and "MissingSampleScale" in skipped["R-15"]
    assert "electrical_feedforward_mismatch" in report["differential"]["considered"]


def test_r26_no_hit_is_registered_not_silently_reordered():
    """例 A 同时把 R-26 第 2 支（abs(A_s)<1.5）和第 3 支（dwell==false）否掉：有序链无命中。"""
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    assert any("R-26 有序链无命中" in n for n in report["audit"]["arbitration_notes"])


def test_assumed_severity_is_written_to_assumptions():
    """KB4 §2.9 的 S0…S4 锚点里没有 software_induced_* 一族，取值只能是推断，须留痕。"""
    report = engine.analyze(_load("kb4_case_b_features.json"))
    assert any("severity" in a["statement"] for a in report["audit"]["assumptions"])


def test_every_assumption_row_has_a_stable_anchor():
    """规则 19 / #25：散文不是锚。引擎产的每一行都必须过 C1 §audit.assumptions 的词表。"""
    for name in ("kb4_case_b_features.json", "c2_example_a.json", "c2_example_a_no_events.json"):
        rows = engine.analyze(_load(name), sample_counts=CASE_A_COUNTS)["audit"]["assumptions"]
        assert rows, name
        for a in rows:
            assert anchors.anchor_kind(a["anchor"]) is not None, (name, a)
            assert a["statement"].strip(), (name, a)


# A-102 ④ 的固定句式（逐字取自 KB0 §7.4 A-102 落点句），测试钉死它以防与台账漂移。
NSOURCE_GAP_SENTENCE = ("R-04/R-15 的样本量下限已在 KB4 §2.1(c) 登记，但 rule_table 未登记 "
                        "`n_source` 配方 ⟹ 本引擎不默认 `n_factor=1`，该两条不可评分")


def _r19_fails(diag):
    return [c for c in c3validate.validate(diag)
            if not c.passed and c.check_id.startswith("C3-R19-assumption-shape")]


def test_n_source_recipe_gap_emits_one_anchored_assumption_row():
    """正向（A-102 ④）：R-04/R-15 因 rule_table 未登记 `n_source` 配方而不可评分时，
    引擎产恰好一行 {anchor=KB4§2.1(c), statement=固定句}。锚过词表（C1 第⑥式文档锚）、
    一行覆盖两条不拆行；且门语义不变——两条仍进 rules_skipped，不被这行登记变成可评分。"""
    for name in ("c2_example_a.json", "kb4_case_b_features.json"):
        diag = engine.analyze(_load(name), sample_counts=CASE_A_COUNTS)
        rows = diag["audit"]["assumptions"]
        gap = [a for a in rows if a["anchor"] == "KB4§2.1(c)"]
        assert len(gap) == 1, (name, gap)                       # 单行覆盖两条
        assert anchors.anchor_kind(gap[0]["anchor"]) == "文档锚", gap[0]
        assert gap[0]["statement"] == NSOURCE_GAP_SENTENCE, gap[0]
        assert all(anchors.anchor_kind(a["anchor"]) for a in rows), (name, rows)
        skipped = {s["rule_id"]: s["reason"] for s in diag["audit"]["rules_skipped"]}
        assert any("R-15" in rid and "MissingSampleScale" in r
                   for rid, r in skipped.items()), skipped       # 仍不可评分，未变可评分


def test_n_source_recipe_gap_row_absent_without_missing_recipe_skip():
    """负向控制：c2 例 B 上 R-04/R-15 不产生"缺配方"的 MissingSampleScale（特征为 null），
    引擎不得凭空登记该行——留痕只跟着实际观测到的不可评分走。"""
    rows = engine.analyze(_load("c2_example_b.json"),
                          sample_counts=CASE_A_COUNTS)["audit"]["assumptions"]
    assert not [a for a in rows if a["anchor"] == "KB4§2.1(c)"]


def test_prose_or_wrong_anchor_assumption_is_caught_by_rule_19():
    """负向（规则 19 有检测力）：往引擎报告的 assumptions 注入一行散文、一行越界锚，
    c3validate 必须以 C3-R19-assumption-shape 翻红；干净报告（含 A-102 ④ 行）则该道全绿。"""
    base = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    assert _r19_fails(base) == []
    prose = copy.deepcopy(base)
    prose["audit"]["assumptions"].append("这是一句没有锚的散文假定")
    assert _r19_fails(prose), "散文行未被规则 19 抓住"
    wrong = copy.deepcopy(base)
    wrong["audit"]["assumptions"].append(
        {"anchor": "kb4 2.9 缺样本量配方", "statement": "越界锚（含空格、不在六种形式内）"})
    assert _r19_fails(wrong), "越界锚未被规则 19 抓住"


def test_engine_never_writes_to_device():
    report = engine.analyze(_load("kb4_case_b_features.json"))
    assert report["safety"]["writes_to_device"] is False
    assert report["safety"]["requires_human_approval"] is True


def test_expected_effect_never_claims_simulation_without_validation_record():
    """C4 未实现 ⟹ 引擎一律 rule_heuristic，不得给出改进百分比（A-64）。"""
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    assert report["validation"] == []
    for h in report["hypotheses"]:
        assert h["recommendation"]["expected_effect"]["basis"] == "rule_heuristic"


# ---------------------------------------------------------------- 互斥登记

def test_injected_sample_counts_are_registered_as_assumption():
    """侧车里的 n 不是本包可复算的量，必须进 `audit.assumptions`（A-102 与 A-103 同源纪律）。

    每个侧车键一行，锚 = C2 里承载同一件事的特征路径（规则 19：锚要能指回一个字段）。
    """
    diag = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    rows = {a["anchor"]: a["statement"] for a in diag["audit"]["assumptions"]}
    assert rows["resonance.estimation.n_segments"].count("welch_segments") == 1
    assert "band_bins" in rows["resonance.estimation.bins_in_band"]
    plain = engine.analyze(_load("kb4_case_b_features.json"))
    assert not any("sample_counts" in a["statement"] for a in plain["audit"]["assumptions"])


def test_considered_and_not_evaluable_are_disjoint():
    """同一叶既进「候选但未成立」又进「输入缺失不可评」是自相矛盾（KB4 §1.5 逐叶粒度）。"""
    features = _load("c2_example_a.json")
    features["event_context"] = {"available": False}
    rep = engine.analyze(features, sample_counts=CASE_A_COUNTS)
    registered = {r.get("fault_mode") for r in rep["differential"]["not_evaluable"]}
    assert "software_induced_interp_buffer_underrun" in registered
    assert not (set(rep["differential"]["considered"]) & registered)


# ---------------------------------------------------------------- 报告接入（第八节）

def _section(diag):
    return "".join(report.diagnosis_section(diag))


def test_eight_section_prints_hypotheses_with_raw_recompute_inputs():
    diag = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    html_text = _section(diag)
    assert "<h2>八、" in html_text
    for h in diag["hypotheses"]:
        assert h["id"] in html_text and h["fault_mode"] in html_text
        for e in h["supporting_evidence"]:
            assert e["feature"] in html_text
            assert ("%g" % e["strength"]) in html_text
            assert ("%g" % e["n_ref"]) in html_text
    for row in diag["audit"]["tier_ledger"]:
        assert row["wording_ceiling"] in html_text


def test_eight_section_prints_refuters_and_absence_keys():
    diag = engine.analyze(_load("kb4_case_b_features.json"))
    html_text = _section(diag)
    assert "R-15#1" in html_text and "1.507" in html_text
    assert "absent_temp_channel" in html_text
    assert "writes_to_device=false" in html_text and "requires_human_approval=true" in html_text


def test_eight_section_says_indeterminate_not_clean_when_nothing_scores():
    """零假设时不得读成「没有问题」，也不得用「未检出」这类越界措辞（C2 规则 7 / INV-11）。"""
    features = _load("kb4_case_b_features.json")
    features["event_context"] = {"available": False}
    diag = engine.analyze(features)
    assert diag["hypotheses"] == []
    html_text = _section(diag)
    assert "零条假设可评分" in html_text and "不可判定" in html_text
    for banned in ("未检出", "无异常", "未发现", "已验证", "实测通过"):
        assert banned not in html_text


# ------------------------------------------------- KB4 §2.9 的 ±0.01 并列带（A-116 ①）

_TIE_FEATURES = {"segment_coverage": {"move": 1}}


def _fired(leaf, rule_id, c_raw):
    """造一条只够 `_rank` 用的叶结果：`_rank` 只读 `rule_ids`、`scores[0].c` 与 coverage。"""
    score = confidence.Score(s_max=c_raw, s_rest=0.0, a_sup=0.0, a_con=0.0,
                             c_mid=c_raw, c=c_raw, k=1)
    return engine.LeafResult(leaf=leaf, rule_ids=[rule_id], status="fired",
                             scored_rules=[rule_id], scores=[score])


def test_engine_rank_puts_the_tie_band_in_fault_mode_order():
    """引擎侧与校验器侧必须是同一套序，否则同一份报告能"引擎排得出、校验器判红"。

    两条都在 S2（KB4 §2.9：R-15 前馈失配与 R-19 插补欠载同为 S2），原始 C 0.5004 / 0.4949：
    未取整时软件族在前，两位显示后 0.50 / 0.49 也还在 ±0.01 并列带内 ⟹ 按 `fault_mode` 决序，
    `electrical_feedforward_mismatch` 排在 `software_induced_interp_buffer_underrun` 之前。

    这组数是**对着旧实现选的**：旧 `key` 用未取整的 `-c`，0.5004 > 0.4949 ⟹ 软件族在前；带落码后
    两条并带 ⟹ 序翻转。断言两侧（带内翻转 / 出带不翻转）都在，`±0.01` 才不是一句散文。"""
    ff = _fired("electrical_feedforward_mismatch", "R-15", 0.4949)
    sw = _fired("software_induced_interp_buffer_underrun", "R-19", 0.5004)
    ranked = engine._rank(_TIE_FEATURES, {sw.leaf: sw, ff.leaf: ff}, None, [])
    assert [leaf for leaf, _ in ranked] == [ff.leaf, sw.leaf]
    # 出带（0.5004 vs 0.4804，差 0.02）⟹ 回到 C 说了算，软件族在前
    sw2 = _fired("software_induced_interp_buffer_underrun", "R-19", 0.5004)
    ff2 = _fired("electrical_feedforward_mismatch", "R-15", 0.4804)
    ranked = engine._rank(_TIE_FEATURES, {sw2.leaf: sw2, ff2.leaf: ff2}, None, [])
    assert [leaf for leaf, _ in ranked] == [sw2.leaf, ff2.leaf]


def test_engine_report_hash_recomputes_and_the_halves_agree():
    """规则 21 的生产侧：引擎算出的哈希必须能被校验器按同一份实现复算出来。
    两侧共用 `core_hash` 是规则 21 的硬要求（不许各自发明），这条测试就是那道要求的载体——
    若哪天有人在校验器里另写一份实现，这里会红。"""
    features = _load("c2_example_a.json")
    diag = engine.analyze(features, sample_counts=CASE_A_COUNTS, case_id="AX-HASH")
    assert core_hash.is_computed(diag["audit"]["deterministic_core_hash"])
    assert not _fails(diag), [c.check_id for c in _fails(diag)]
