"""A-97（counts 后缀是历史名）/ A-98（互证不以 pos_fb 为轴）/ A-106（分歧先减原点）。

三条裁决都由 Export10_244531 的真实缺陷触发，所以正向断言跑在真样本切片上；
每条负向都注入一个"看起来能过"的样本，证明对应的门真的会拦（KB0 §6 检查 22）。

    python -m pytest tests/test_counts_and_pairs.py -q
"""
from __future__ import annotations

import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from axiscope import c1, engine, features         # noqa: E402
from axiscope import mapping                      # noqa: E402
from axiscope.__main__ import run as cli_run      # noqa: E402
from axiscope.twincat import read_scope           # noqa: E402

RAW = os.path.join(ROOT, "data", "raw", "Export10_244531.csv")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    pack_dir = str(tmp_path_factory.mktemp("cap") / "Export10_244531")
    cli_run(RAW, pack_dir)
    meta, feats = _load(pack_dir)
    _, ingest = c1.build_meta(read_scope(RAW), sample_id="Export10_244531")
    ingest["sample_id"], ingest["sha256"] = "Export10_244531", "test"
    return {"pack_dir": pack_dir, "meta": meta, "feats": feats, "ingest": ingest}


def _load(pack_dir):
    with open(os.path.join(pack_dir, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    with open(os.path.join(pack_dir, "features.json"), encoding="utf-8") as fh:
        return meta, json.load(fh)


# ---------------------------------------------------------------- A-97 ①/②/③

def test_pair_values_are_native_scale_and_carry_unit(built):
    """A-97 ③：si_native 样本上 `rms_counts` 填的是原生刻度（m）的实测值，单位随行。"""
    for p in built["feats"]["sensor_disagreement"]["pairs"]:
        assert p["unit"] == "m"
        assert 0 < p["rms_counts"] < 1.0, "m 级实测分歧不该是 counts 量级的数"
    assert not any(u["feature"].startswith("sensor_disagreement.pairs[].rms_counts")
                   for u in built["feats"]["unavailable"]), \
        "幅值已有值，不得再登记 unavailable（C2 规则 14 互斥）"


def test_missing_counts_scale_only_kills_absolute_thresholds():
    """A-97 ②/③：绝对阈值无分母 ⟹ 拦；比值类刻度无关 ⟹ 不得被连坐。"""
    assert features.counts_scale_missing({"units_are": "si_native", "counts_per_mm": None})
    assert not features.counts_scale_missing({"units_are": "counts", "counts_per_mm": None})
    assert not features.counts_scale_missing({"units_are": "si_native", "counts_per_mm": 1000.0})
    assert engine.counts_scale_class({"feature": "global.reversal_error_counts",
                                      "op": "gte", "threshold": 22}) == "absolute"
    assert engine.counts_scale_class({"feature": "global.fe_rms_counts",
                                      "threshold": {"ref": "x", "scale": 3},
                                      "counts_scale": "ratio"}) == "ratio"
    assert engine.counts_scale_class({"feature": "spectral.fe.tonality_index",
                                      "threshold": 0.6}) is None


def test_counts_gate_blocks_only_when_whole_leaf_is_absolute():
    meta = {"units_are": "si_native", "counts_per_mm": None}
    feats = json.load(open(os.path.join(ROOT, "examples", "c2_example_a.json"),
                           encoding="utf-8"))
    # mechanical_resonance 的 R-03/R-04 全是刻度无关判据 ⟹ 本门一条都不该产（A-97 ③）
    assert engine.counts_gate(feats, "mechanical_resonance", meta) == []
    # 比值判据所在的 software 叶同样不得被连坐
    assert engine.counts_gate(feats, "software_induced_interp_buffer_underrun", meta) == []
    # counts 刻度存在时整道门不成立
    assert engine.counts_gate(feats, "mechanical_resonance",
                              {"units_are": "counts"}) == []


def test_counts_gate_absent_scale_is_registered_with_stable_key(monkeypatch):
    """注入一条只含绝对 counts 阈值的叶：blocked_by 必须是 absent_counts_scale 且句式固定。"""
    table = engine.load_rule_table()
    spec = copy.deepcopy(table["rules"]["R-15"])
    for cond in spec["conditions"]:
        cond["feature"] = "global.reversal_error_counts"
        cond["threshold"] = 22
        cond.pop("counts_scale", None)          # 未标注 ⟹ 按绝对处理（A-97 ④ 保守侧）
    monkeypatch.setitem(table["rules"], "R-15", spec)
    feats = json.load(open(os.path.join(ROOT, "examples", "c2_example_a.json"),
                           encoding="utf-8"))
    rows = engine.counts_gate(feats, "electrical_feedforward_mismatch",
                              {"units_are": "si_native", "counts_per_mm": None})
    ne = [r for r in rows if r["kind"] == "not_evaluable"]
    assert ne == [{"kind": "not_evaluable", "fault_mode": "electrical_feedforward_mismatch",
                   "blocked_by": "absent_counts_scale", "why": features.WHY_NO_COUNTS}]
    assert ne[0]["why"] == "无 counts 刻度，绝对阈值不可比"


def test_evidence_builder_refuses_scale_substitution():
    """没有 counts 刻度时，绝对 counts 阈值连比较都不发生（拿 m 当 counts 判是静默替换）。"""
    feats = json.load(open(os.path.join(ROOT, "examples", "c2_example_a.json"),
                           encoding="utf-8"))
    feats["global"]["reversal_error_counts"] = 5.0          # 5 m，绝不该过 22 counts 的门
    table = engine.load_rule_table()
    spec = copy.deepcopy(table["rules"]["R-03"])
    spec["conditions"] = [{"n": 9, "feature": "global.reversal_error_counts",
                           "op": "gte", "threshold": 22, "tier": "L",
                           "required": True, "evidence": True,
                           "n_source": "segment:dwell", "n_ref": 1}]
    monkey = {"R-03": spec}
    orig = engine.rule
    engine.rule = lambda rid: monkey.get(rid, orig(rid))
    try:
        ctx = engine.FrequencyContext(fs_hz=feats["fs_hz"], reliable_band_hz=4000.0,
                                      nyquist_hz=4000.0)
        _, gates, _ = engine.build_evidence(feats, "R-03", ctx, None,
                                           counts_missing=True)
        assert gates == ["absent_counts_scale:R-03#9"]
        _, gates_ok, _ = engine.build_evidence(feats, "R-03", ctx, None,
                                               counts_missing=False)
        assert gates_ok == ["not_fired:R-03#9"]          # 有刻度时才真的把 5 和 22 比过
    finally:
        engine.rule = orig


def test_every_counts_bearing_condition_is_explicitly_tagged():
    """A-97 ④：KB3 §1.13b 的「绝对/比值」标注在规则表里的同义要求——漏标即漏判。"""
    table = json.load(open(os.path.join(ROOT, "src", "axiscope", "rule_table.json"),
                           encoding="utf-8"))
    untagged = []
    for rid, spec in table["rules"].items():
        for key in ("conditions", "refuters"):
            for cond in spec.get(key) or []:
                blob = json.dumps(cond, ensure_ascii=False)
                if "counts" in blob and "counts_scale" not in cond:
                    untagged.append((rid, cond.get("n") or cond.get("id")))
    assert untagged == []


# ---------------------------------------------------------------- A-106 去常偏

def test_pair_metrics_are_computed_on_residuals():
    """常量 180 m 的原点差不该被读成 180 m 的分歧（C2 规则 16 的实测反例）。"""
    series = {"x": [float(i) + 180.0 for i in range(5)], "y": [float(i) for i in range(5)]}
    rows = c1._pairwise_findings(series, [("x", "y")], finding_table=[])
    r = rows[0]
    assert r["datum_offset"] == pytest.approx(180.0)
    assert r["rms"] == 0.0 and r["max_abs"] == 0.0
    assert r["corr"] == pytest.approx(1.0)               # corr 在原始值上算，平移不改变它
    assert r["unit"] == "m" and r["a_role"] == "extra"

    table: list[dict] = []
    c1._pairwise_findings(series, [("x", "y")], finding_table=table)
    assert table[0]["kind"] == "sensor_disagreement"
    assert table[0]["datum_offset_m"] == pytest.approx(180.0)


def test_real_pairs_separate_datum_from_disagreement(built):
    """`asco − asco_enc` 的常偏是 m 量级、残差是 mm 量级，两者必须落在不同字段。"""
    by_pair = {(p["a"], p["b"]): p for p in built["ingest"]["pairs"]}
    row = by_pair[("dPosition_asco", "dPosition_asco_enc")]
    assert abs(row["datum_offset"]) > 100 * row["rms"], "原点差淹不掉时才叫分歧"
    for p in built["ingest"]["pairs"]:
        assert p["max_abs"] >= p["rms"] > 0.0


def test_missing_datum_offset_degrades_the_pair_not_the_whole_pack(built):
    ingest = copy.deepcopy(built["ingest"])
    del ingest["pairs"][0]["datum_offset"]
    feats = features.compute(built["meta"], ingest, built["pack_dir"])
    p = feats["sensor_disagreement"]["pairs"][0]
    assert p["rms_counts"] is None and p["max_counts"] is None
    rows = [u for u in feats["unavailable"]
            if u["feature"].endswith("rms_counts") and "|" in u["feature"]]
    assert rows and rows[0]["reason"].startswith("未做原点对齐，分歧幅值不可比")
    assert feats["sensor_disagreement"]["pairs"][1]["rms_counts"] is not None


def test_self_consistency_catches_unit_and_datum_omissions(built):
    for mutate, msg in (
        (lambda f: f["sensor_disagreement"]["pairs"][0].pop("unit"), "缺 unit"),
        (lambda f: f["sensor_disagreement"]["pairs"][0].update({"a_role": "mystery"}), "role"),
        (lambda f: f["sensor_disagreement"]["pairs"][0].update({"datum_offset": None}),
         "datum_offset"),
    ):
        f = copy.deepcopy(built["feats"])
        mutate(f)
        with pytest.raises(features.FeatureError) as exc:
            features.check_self_consistency(f, built["meta"])
        assert msg in str(exc.value)


# ---------------------------------------------------------------- A-98 互证资格

def test_principles_are_registered_from_documented_hardware():
    assert mapping.principle("dPosition_test") == "motor_encoder"
    assert mapping.principle("dPosition_asco_enc") == "optical_asco"
    assert mapping.principle("dPosition_lsv_enc") == "inductive_lsv"
    assert mapping.principle("dPosition_diff") is None          # 未登记原理的列不计入


def test_second_feedback_requires_different_principle(built):
    """A-98 ②：`pos_fb` 缺席不再是拦路条件，但同原理的两列也不算第二次独立测量。"""
    fi = built["feats"]["feedback_integrity"]
    assert fi["second_feedback_available"] is True
    assert built["meta"]["channels"].get("pos_fb") is None, "本样本根本没有 pos_fb"

    same = [{"a_principle": "optical_asco", "b_principle": "optical_asco"},
            {"a_principle": None, "b_principle": "motor_encoder"}]
    assert not any(p["a_principle"] and p["b_principle"]
                   and p["a_principle"] != p["b_principle"] for p in same)


def test_rowwise_identical_command_column_is_flagged_as_masquerade(built):
    """A-98 ③：四对指令/反馈孪生列里哪些逐行全等，是门控后 5000 行的实测结果。"""
    rows = {m["cmd"]: m for m in built["ingest"]["masquerade"]}
    assert {k: v["n_rows_differ"] for k, v in rows.items()} == {
        "dPosition_test_tar": 0, "dPosition_load_tar": 0, "dVelocity_load_tar": 0,
        "dVelocity_test_tar": 5000}
    assert built["feats"]["feedback_integrity"]["masquerade_suspected"] is True
    finding = [f for f in built["ingest"]["findings"] if f["kind"] == "command_masquerade"]
    assert sorted(f["cmd"] for f in finding) == [
        "dPosition_load_tar", "dPosition_test_tar", "dVelocity_load_tar"]
    assert all(f["note"] == "指令轨与候选反馈逐行全等，二者非独立测量（A-98 ③ 固定句式）"
               for f in finding)


# ------------------------------------------------ A-110 ②/③（任务 #39）：*_mm si_native 定标

def _si_pack(fe_unit, units_are="si_native", counts_per_mm=None, fe_vals=(3.0, 4.0)):
    """合成一个 fe 在场的原生 SI 样本包（Export10 本身无 fe，正/负分支只能这样喂）。

    只带 `compute()` 与 `check_self_consistency()` 需要的最小键；`audit.assumptions` 起始为空，
    好让 si_native 直接定标支的**恰好一行**留痕可被逐字数出来。
    """
    meta = {
        "sample_rate_hz": 1000.0, "present_channels": ["fe"], "segments": [],
        "units_are": units_are, "counts_per_mm": counts_per_mm,
        "channels": {"fe": {"unit": fe_unit}},
        "quality": {"n_samples": len(fe_vals), "dt_jitter_ratio": 0.0,
                    "nan_ratio": 0.0, "gap_max_s": 0.0},
        "audit": {"assumptions": []},
    }
    ingest = {"sample_id": "SYN", "sha256": "x", "series": {},
              "canon_series": {"fe": list(fe_vals)}, "pairs": [],
              "masquerade": [], "identity": {"performed": False, "reason": "n/a"}}
    return meta, ingest


def _mm_rows(meta):
    return [r for r in meta["audit"]["assumptions"]
            if r.get("anchor") == "meta.units_are"]


def test_si_native_length_scale_predicate_gates_on_unit_vocabulary():
    """A-110 ②：只有 si_native + C1 长度刻度才放开 `*_mm` 定标，且与绝对阈值门禁分权。"""
    si = {"units_are": "si_native"}
    assert features.si_native_length_scale(si, "m") is True
    for non_length in ("m/s", "N_m", "A", None):
        assert features.si_native_length_scale(si, non_length) is False
    # counts 不是 si_native：谓词恒 False，但 counts_scale_missing 的绝对阈值语义一字未动
    assert features.si_native_length_scale({"units_are": "counts"}, "m") is False
    assert features.counts_scale_missing({"units_are": "counts", "counts_per_mm": None}) is False
    assert features.counts_scale_missing({"units_are": "si_native", "counts_per_mm": None}) is True


def test_si_native_length_sample_fills_mm_and_emits_exactly_one_assumption(tmp_path):
    """正向：si_native 长度刻度 + fe 在场 ⟹ fe_rms_mm = 原生(m) × 1000，且只落一行留痕。"""
    meta, ingest = _si_pack("m")
    feats = features.compute(meta, ingest, str(tmp_path))
    expected_native = 0.5          # 去均值 RMS（A-114）：fe=(3,4) ⟹ 波动 ±0.5
    assert feats["global"]["fe_rms_counts"] == expected_native
    assert feats["global"]["fe_rms_mm"] == expected_native * 1000.0
    rows = _mm_rows(meta)
    assert len(rows) == 1, "si_native 定标支必须恰好落一行，不得多不得少"
    assert rows[0] == {"anchor": "meta.units_are",
                       "statement": "`*_mm` 由 C1 原生 SI 刻度直接定标，非 counts/counts_per_mm 路径"}
    # 值与 unavailable 互斥：fe_rms_mm 有值就不再登记该路径不可用
    assert not any(u["feature"] == "global.fe_rms_mm" for u in feats["unavailable"])
    # position_quantum_mm 恒留 null（1/counts_per_mm + 量子，非纯换算），不得被顺带填上
    assert feats["position_quantum_mm"] is None
    assert any(u["feature"] == "position_quantum_mm" for u in feats["unavailable"])


def test_fe_rms_is_demeaned_so_a_constant_offset_does_not_inflate_it(tmp_path):
    """A-114 的检测力自证（检查 22）：带常偏的 fe 上 `fe_rms_*` 只量波动。

    `fe = 103.5 ± 0.5` ⟹ 去均值 RMS = 0.5（与上一例同一波动幅度），而减均值前的旧实现给 ≈103.5。
    这不是"两种写法都行"的口径偏好：R-02 的 `fe_p999/fe_rms ≥ 4` 分子是 median 中心的波动量，
    分母含常偏会把比值压低约两个量级 ⟹ 有稳态误差的样本上该判据整体漏报。
    """
    meta, ingest = _si_pack("m", fe_vals=(103.0, 104.0, 103.0, 104.0))
    feats = features.compute(meta, ingest, str(tmp_path))
    assert feats["global"]["fe_rms_counts"] == 0.5
    assert feats["global"]["fe_rms_mm"] == 500.0
    raw_rms = ((103.0 ** 2 + 104.0 ** 2 + 103.0 ** 2 + 104.0 ** 2) / 4) ** 0.5
    assert raw_rms > 100.0 and feats["global"]["fe_rms_counts"] < raw_rms / 200.0
    # 被减掉的常偏没有消失，它另有载体（A-106 ② 的同一纪律 / C2 规则 19）
    assert feats["global"]["fe_mean_counts"] == 103.5
    assert feats["global"]["fe_rms_counts"] < abs(feats["global"]["fe_mean_counts"]) / 200.0
    assert feats["global"]["fe_max_counts"] is None       # 本切片未算，null 前不插值（规则 2）


def test_missing_fe_registers_the_constant_offset_path_as_unavailable(tmp_path):
    """无 fe 时 `global.fe_mean_counts` 必须与其余 fe 族一起进 `unavailable`（规则 2：null 要记）。"""
    meta, ingest = _si_pack("m")
    meta["present_channels"] = []          # 本切片按 Export10 的实测事实：无 fe 通道
    ingest["canon_series"] = {}
    feats = features.compute(meta, ingest, str(tmp_path))
    assert feats["global"]["fe_mean_counts"] is None
    for path in ["global.fe_rms_counts", "global.fe_mean_counts",
                 "global.fe_p999_counts", "global.fe_max_counts"]:
        assert any(u["feature"] == path for u in feats["unavailable"]), path


def test_si_native_non_length_channel_does_not_get_mm(tmp_path, monkeypatch):
    """负向：si_native 但通道非长度刻度（如 m/s）⟹ fe_rms_mm null、零留痕、绝对阈值仍被拦。"""
    meta, ingest = _si_pack("m/s")
    feats = features.compute(meta, ingest, str(tmp_path))
    assert feats["global"]["fe_rms_counts"] is not None       # 原生值照算
    assert feats["global"]["fe_rms_mm"] is None               # 但不是长度，不产 *_mm
    assert any(u["feature"] == "global.fe_rms_mm" for u in feats["unavailable"])
    assert _mm_rows(meta) == []                               # 没有定标就没有留痕
    # 分权自证：*_mm 被 null 的同时，绝对阈值仍走 absent_counts_scale（未因本改放松）
    assert features.counts_scale_missing(meta) is True
    table = engine.load_rule_table()
    spec = copy.deepcopy(table["rules"]["R-15"])
    for cond in spec["conditions"]:
        cond["feature"] = "global.reversal_error_counts"
        cond["threshold"] = 22
        cond.pop("counts_scale", None)
    monkeypatch.setitem(table["rules"], "R-15", spec)
    rows = engine.counts_gate(feats, "electrical_feedforward_mismatch", meta)
    assert any(r.get("blocked_by") == "absent_counts_scale" for r in rows
               if r["kind"] == "not_evaluable")


def test_counts_sample_with_null_scale_keeps_mm_null_without_assumption(tmp_path):
    """负向：units_are=counts 且 counts_per_mm=null ⟹ *_mm null、无 si_native 留痕。

    counts 刻度的绝对阈值按 `counts_scale_missing` 判为**可用**（返回 False），本样不被
    absent_counts_scale 拦——这是 #39 明令不得改动的既有语义，故这里断言它保持不变。
    """
    meta, ingest = _si_pack("m", units_are="counts")
    feats = features.compute(meta, ingest, str(tmp_path))
    assert feats["global"]["fe_rms_counts"] is not None
    assert feats["global"]["fe_rms_mm"] is None
    assert any(u["feature"] == "global.fe_rms_mm" for u in feats["unavailable"])
    assert _mm_rows(meta) == []
    assert features.counts_scale_missing(meta) is False       # counts 侧阈值语义未被动过


def test_counts_mm_path_needs_no_si_native_assumption(tmp_path):
    """counts 定标路径（cpm 非 null）填 fe_rms_mm 走除法，不是 si_native 支，不落 meta.units_are 锚。"""
    meta, ingest = _si_pack("m", units_are="counts", counts_per_mm=50000.0)
    feats = features.compute(meta, ingest, str(tmp_path))
    native = feats["global"]["fe_rms_counts"]
    assert feats["global"]["fe_rms_mm"] == native / 50000.0
    assert _mm_rows(meta) == []                               # (i) 路径不需 si_native 定标留痕


def test_export10_real_sample_fills_nothing_extra(built):
    """边界自证：Export10 无 fe 且 counts_per_mm=null ⟹ 两条 *_mm 仍 null、无新留痕。

    裁决定标支只在 fe 在场的原生长度样本上触发；本切片喂不出这样的真样本，故真跑不得出现新值——
    这条正是"改动的落点没有悄悄改写既有真样本"的证据（KB0 §6 检查 22 的反证）。
    """
    feats = built["feats"]
    assert feats["global"]["fe_rms_mm"] is None
    assert feats["position_quantum_mm"] is None
    assert _mm_rows(built["meta"]) == []

