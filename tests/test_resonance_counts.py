"""A-102 ②/④：resonance 样本量三字段是「显式登记的量」，不是反推的产物。

正向：`resonance.estimation.n_segments` / `resonance.estimation.bins_in_band` /
`resonance.candidates[].three_db_width_bins` 在 C2 两处示例、真实管线（Export10）与
引擎逐格复算三处必须同数（KB4 §2.3 算例 A 的 n=8/96/22 即 §2.1(c) 表行的出处）。
负向：缺键、填 0、拿反推值冒充（1641）都要被 `check_resonance_counts` 拦下（KB0 §6 检查 22）。

    python -m pytest tests/test_resonance_counts.py -q
"""
from __future__ import annotations

import copy
import json
import os
import sys

import pytest


# 原始数据按 A-131 口径不入库；缺件时本文件整份 loud SKIP
# （口径见 tests/conftest.py；跳过 ≠ 通过，原因会写在 skip 理由里）
REQUIRES_DATA = ("data/raw/Export10_244531.csv",)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from axiscope import engine, features            # noqa: E402
from axiscope.__main__ import run as cli_run     # noqa: E402

EXAMPLES = os.path.join(ROOT, "examples")
RAW = os.path.join(ROOT, "data", "raw", "Export10_244531.csv")

# 与 tests/test_engine.CASE_A_COUNTS 同一过渡口径（A-102 ③）：规则表消费 C2 载体之前，
# 侧车必须显式带这两个键；本文件不改它，只核对新字段与它的逐格同数。
CASE_A_COUNTS = {"welch_segments": 8, "band_bins": 96}


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return json.load(fh)


def _resonance_hyp(diag):
    for h in diag["hypotheses"]:
        if h["fault_mode"] == "mechanical_resonance":
            return h
    raise AssertionError("报告里没有 mechanical_resonance")


# ---------------------------------------------------------------- 裁决 ①/②：示例值 = 引擎实算值

def test_example_a_three_fields_equal_engine_recomputed_n():
    """KB4 §2.3 算例 A 的 Welch 8 / 带内 bin 96 / 3 dB 宽 22 三格与示例 JSON 同数。"""
    f = _load("c2_example_a.json")
    est = f["resonance"]["estimation"]
    c0 = f["resonance"]["candidates"][0]
    assert (est["n_segments"], est["bins_in_band"], c0["three_db_width_bins"]) == (8, 96, 22)
    diag = engine.analyze(f, sample_counts=CASE_A_COUNTS)
    ev = {e["condition_index"]: e for e in _resonance_hyp(diag)["supporting_evidence"]}
    assert ev[2]["n"] == est["n_segments"] and ev[2]["n_ref"] == 4
    assert ev[3]["n"] == est["bins_in_band"] and ev[3]["n_ref"] == 15
    assert ev[7]["n"] == c0["three_db_width_bins"] and ev[7]["n_ref"] == 8


def test_example_a_three_db_width_bins_recomputes_from_registered_quantities():
    """22 不是手填：rule_table 配方 round(freq_hz/quality/resolution) 当场可复算（A-76 同纪律）。"""
    f = _load("c2_example_a.json")
    c0 = f["resonance"]["candidates"][0]
    assert round(c0["freq_hz"] / c0["quality_factor_estimate"]
                 / f["resonance"]["resolution_hz"]) == c0["three_db_width_bins"] == 22


def test_both_examples_pass_resonance_counts_selfcheck():
    for name in ("c2_example_a.json", "c2_example_b.json"):
        features.check_resonance_counts(_load(name))


# ---------------------------------------------------------------- 裁决 ②：算不了的登记形状（例 B）

def test_example_b_registers_estimation_counts_as_unavailable_not_guessed():
    f = _load("c2_example_b.json")
    est = f["resonance"]["estimation"]
    assert est["n_segments"] is None and est["bins_in_band"] is None
    rows = {u["feature"]: u for u in f["unavailable"]}
    for path in ("resonance.estimation.n_segments", "resonance.estimation.bins_in_band"):
        assert path in rows, f"{path} 值为 null 却无 unavailable 行（C2 规则 2）"
        assert "反推" in rows[path]["reason"]
        # A-79：rule/branch 键只属于频带/支路门禁行；登记形状不得给对账制造孤儿
        assert "rule" not in rows[path] and "branch" not in rows[path]


# ---------------------------------------------------------------- 负向：自检必须拦得住

def test_selfcheck_refuses_missing_keys_zero_and_back_fabricated():
    f = _load("c2_example_a.json")
    g = copy.deepcopy(f)
    del g["resonance"]["estimation"]["n_segments"]
    with pytest.raises(features.FeatureError, match="n_segments"):
        features.check_resonance_counts(g)

    g = copy.deepcopy(f)
    g["resonance"]["estimation"]["bins_in_band"] = 0
    with pytest.raises(features.FeatureError, match="bins_in_band"):
        features.check_resonance_counts(g)

    g = copy.deepcopy(f)
    del g["resonance"]["candidates"][0]["three_db_width_bins"]
    with pytest.raises(features.FeatureError, match="three_db_width_bins"):
        features.check_resonance_counts(g)

    # 1641 = reliable_band_hz/resolution_hz 的反推值（A-102 ② 明令禁止当口径的数）
    g = copy.deepcopy(f)
    g["resonance"]["candidates"][0]["three_db_width_bins"] = 1641
    with pytest.raises(features.FeatureError, match="round"):
        features.check_resonance_counts(g)


def test_unavailable_and_value_are_mutually_exclusive_for_new_fields():
    """新字段既有值又出现在 unavailable（或反之缺登记）都要被既有互斥自检拒掉（C2 规则 14）。"""
    g = _load("c2_example_a.json")
    g["unavailable"].append({"feature": "resonance.estimation.bins_in_band",
                             "reason": "假装不可算（负向注入）"})
    with pytest.raises(features.FeatureError, match="互斥"):
        features.check_self_consistency(g, {"present_channels": g["present_channels"]})


# ---------------------------------------------------------------- 真实管线（Export10）

@pytest.fixture(scope="module")
def real_pack(tmp_path_factory):
    pack_dir = str(tmp_path_factory.mktemp("rc") / "Export10_244531")
    cli_run(RAW, pack_dir)
    with open(os.path.join(pack_dir, "features.json"), encoding="utf-8") as fh:
        return json.load(fh)


def test_real_pipeline_registers_welch_segments_and_null_bins(real_pack):
    est = real_pack["resonance"]["estimation"]
    # 5000 行 @ nperseg 2048、noverlap 1024 ⟹ (5000−1024)//1024 = 3 段，Welch 实跑段数登记在案
    assert est["n_segments"] == 3
    assert est["bins_in_band"] is None
    assert any(u["feature"] == "resonance.estimation.bins_in_band"
               for u in real_pack["unavailable"])
    features.check_resonance_counts(real_pack)


def test_real_pipeline_still_requires_explicit_sidecar_keys(real_pack):
    """A-102 ③ 过渡口径不因新字段失效：无侧车时 welch/band 判据仍 MissingSampleScale，禁默认 1。"""
    plain = engine.analyze(real_pack)  # 不注入侧车
    assert not [h for h in plain["hypotheses"]
                if h["fault_mode"] == "mechanical_resonance"]
    partial = engine.analyze(_load("c2_example_a.json"),
                             sample_counts={"welch_segments": 8})
    skipped = {s["rule_id"]: s["reason"] for s in partial["audit"]["rules_skipped"]}
    assert any("MissingSampleScale" in r and "band_bins" in r for r in skipped.values()), \
        "侧车缺 band_bins 键时必须显式报错，而不是退回默认 n_factor=1"
    assert not [h for h in partial["hypotheses"]
                if h["fault_mode"] == "mechanical_resonance"]
