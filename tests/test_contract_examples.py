"""C2 契约示例的算术纪律复算（C2 规则 7/8/10/11 + INV-3 + A-76/A-79/A-83）。

C2 末尾原文："两份示例都必须能被 JSON.parse 直接解析——契约示例解析不了，就说明没人校验过它。"
本文件就是那层校验。示例里的数值不是示意：凡契约自己声明了派生式的量，都必须按该式重算。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from axiscope import features  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = {"A": os.path.join(ROOT, "examples", "c2_example_a.json"),
            "B": os.path.join(ROOT, "examples", "c2_example_b.json"),
            "CASE_B": os.path.join(ROOT, "examples", "kb4_case_b_features.json"),
            "A_NO_EVENTS": os.path.join(ROOT, "examples", "c2_example_a_no_events.json")}


@pytest.mark.parametrize("key", ["A", "B", "CASE_B"])
def test_examples_parse(key):
    with open(EXAMPLES[key], encoding="utf-8") as fh:
        assert json.load(fh)["schema"] == "axiscope.features/1"


def load(key):
    with open(EXAMPLES[key], encoding="utf-8") as fh:
        return json.load(fh)


def case_b():
    return load("CASE_B")


# --- 例 A：谱类参数的派生式必须可复算（C2 规则 10 / A-76、预览前缀 / A-83）---

def test_a_resolution_is_fs_over_nperseg():
    f = load("A")
    est = f["resonance"]["estimation"]
    exact = f["fs_hz"] / est["nperseg"]
    assert abs(f["resonance"]["resolution_hz"] - round(exact, 2)) < 1e-9


def test_a_preview_is_contiguous_prefix_bins():
    f = load("A")
    est = f["resonance"]["estimation"]
    step = f["fs_hz"] / est["nperseg"]
    for name in ("fe", "cur_q"):
        block = f["spectral"][name]
        assert block["freq_hz"][0] == 0
        for i, freq in enumerate(block["freq_hz"]):
            assert abs(freq - round(i * step, 2)) < 1e-9, f"spectral.{name} 第 {i} 个预览 bin"
        assert len(block["psd"]) == len(block["freq_hz"])


def test_a_pair_separation_bins():
    """A-76 声明的口径是 `round((f_res - f_anti) / resolution_hz)`，分母用**写在示例里**的 1.95。

    用全精度 `fs/nperseg = 1.953125` 会得到 379 而不是 380——契约没写清分母取整还是全精度，
    两种读法差一个 bin。这里按契约自己的算式（`(1181 − 440)/1.95 = 380`）断言，
    并把另一种读法留成显式断言，免得实现悄悄选了一个。
    """
    f = load("A")
    c = f["resonance"]["candidates"][0]
    sep = c["freq_hz"] - c["antiresonance_freq_hz"]
    stated = f["resonance"]["resolution_hz"]
    assert round(sep / stated) == f["resonance"]["estimation"]["pair_separation_bins"] == 380
    assert round(sep / (f["fs_hz"] / f["resonance"]["estimation"]["nperseg"])) == 379


# --- 例 A：INV-3 峰谷顺序与 sqrt(1+λ) ---

def test_a_double_inertia_pair_satisfies_inv3():
    f = load("A")
    c = f["resonance"]["candidates"][0]
    assert c["antiresonance_freq_hz"] < c["freq_hz"]
    lam = (c["freq_hz"] / c["antiresonance_freq_hz"]) ** 2 - 1.0
    assert abs(lam - 6.2) < 0.1
    assert 1.05 <= c["freq_hz"] / c["antiresonance_freq_hz"] <= 2.7


# --- C2 规则 8：因果三元组 + G5 时基分辨 ---

def test_a_causal_triple_is_equivalent():
    f = load("A")
    ec = f["event_context"]
    expect = ec["sync"]["verified"] and ec["alignment_residual_ms"] <= ec["sync"]["uncertainty_ms"]
    assert ec["causal_claims_permitted"] == expect


def test_a_gate_g5_time_resolution_holds():
    """KB4 §1.3 N6 门 G5：`1/fs ≤ τ_u/2`。例 A 若违反，R-18 就必须 skip，算例 A 的登记会不同。"""
    f = load("A")
    tau_u = f["event_context"]["sync"]["uncertainty_ms"]
    assert 1000.0 / f["fs_hz"] <= tau_u / 2.0


# --- 例 B：频带门禁自洽 + A-79 的 blocked_rules ↔ unavailable 双向对账 ---

def test_b_freq_limits_self_consistent():
    f = load("B")
    fl = f["freq_limits"]
    assert fl["nyquist_hz"] == f["fs_hz"] / 2.0
    assert fl["reliable_band_hz"] == pytest.approx(fl["nyquist_hz"] / 1.25)
    assert f["resonance"]["nyquist_hz"] == fl["nyquist_hz"]


def test_b_unavailable_branch_rows_match_blocked_rules():
    f = load("B")
    blocked = set(f["freq_limits"]["blocked_rules"])
    rows = {(u["rule"] + "#" + u["branch"]) if "branch" in u else u.get("rule")
            for u in f["unavailable"] if u.get("rule")}
    orphan = blocked - rows
    assert "R-11#switching_freq" in rows
    # 契约 A-79 要求"每个条目必须在 unavailable[] 里有一条 rule/branch 与之对应的行"。
    # 例 B 的 R-03/R-04 只有 `resonance.candidates` 一行且不带 rule 键 ⟹ 对不上账。
    assert orphan == {"R-03", "R-04"}, "示例缺陷已修复的话本断言应随之失败，见下面的 known_defect 测试"


def test_b_blocked_rules_never_contain_always_on_rules():
    f = load("B")
    for rid in f["freq_limits"]["blocked_rules"]:
        assert not rid.startswith("R-25"), "R-25 是频带门禁本身，不能被自己阻塞（C2 规则 7）"
        assert not rid.startswith("R-10"), "R-10 是伪峰检测器，低采样率数据上恰恰最需要它运行"


def test_b_quantum_blocks_precision_claims():
    """C2 规则 11：量子的唯一用途是拦住吹牛。171 µm 的量子下任何亚微米声明自相矛盾。"""
    f = load("B")
    assert f["position_quantum_mm"] * 1000.0 > 1.0


def test_b_null_not_zero():
    f = load("B")
    rows = {u["feature"] for u in f["unavailable"]}
    # 规则 2 要求**点分全路径**：短名 `cur_q_rms_a` 与证据路径逐字比对永不命中（CAP-5 假绿），
    # 例 B 原先正是这么写的，任务 #42 改为 `global.cur_q_rms_a`。
    assert "global.cur_q_rms_a" in rows
    assert f["global"]["cur_q_rms_a"] is None
    assert f["global"]["cur_q_rms_pct"] is None


def test_a_thermal_correlation_is_null_and_registered():
    f = load("A")
    assert f["global"]["thermal_fe_correlation_r"] is None
    assert any(u["feature"] == "global.thermal_fe_correlation_r" for u in f["unavailable"])


def test_a_and_b_event_context_shapes_differ_by_availability():
    a, b = load("A"), load("B")
    assert a["event_context"]["available"] is True
    assert b["event_context"]["available"] is False
    assert b["event_context"]["causal_claims_permitted"] is False
    assert "reason" in b["event_context"]


def test_example_a_spectral_vel_fb_shape_is_not_engine_consumable():
    """`spectral.vel_fb` 只有 `dominant_freq_hz`，没有规则 1 要求的 `freq_hz`/`psd` 预览；
    `features.check_self_consistency()` 无条件读这两个键。示例演示的是 null 语义，
    但它不能喂给引擎——把示例当输入向量跑之前要先补这个形状。"""
    f = load("A")
    assert "freq_hz" not in f["spectral"]["vel_fb"]
    assert "psd" not in f["spectral"]["vel_fb"]


# --- KB4 算例 B 夹具：门与仲裁必须在进引擎之前就成立，否则 C=0.44 无从复现 ---

def test_case_b_causal_triple_and_gates():
    f = case_b()
    ec = f["event_context"]
    tau_u = ec["sync"]["uncertainty_ms"]
    assert ec["sync"]["verified"] is True
    assert ec["alignment_residual_ms"] <= tau_u
    assert ec["causal_claims_permitted"] is True
    # G3：对齐窗必须严格大于 τ_u（窗比钟差不分辨率，匹配就是抽签）
    assert max(tau_u, 2.0) > tau_u
    # G5：R-18 的时基分辨不成立，但 R-19 只需 fs ≥ 500
    assert 1000.0 / f["fs_hz"] > tau_u / 2.0
    assert f["fs_hz"] >= 500.0


def test_case_b_r28_arbitration_picks_interp_underrun():
    """R-28：`max ≥ 0.5 ∧ (max − second) ≥ 0.2`。缺事件源的臂是**计算出的 0**，不是 null
    ——写成 null 会让 INV-4 把整条仲裁判为不可通行，与 KB4 自己算出的 `C = 0.44` 矛盾。"""
    ec = case_b()["event_context"]
    spikes = ec["fe_spike_count"]
    scores = sorted((ec["fe_spike_aligned_to_underrun"] / spikes,
                     ec["fe_spike_aligned_to_host_pause"] / spikes,
                     ec["fe_spike_aligned_to_network_miss"] / spikes,
                     ec["fe_spike_aligned_to_vision_result"] / spikes), reverse=True)
    assert scores[0] >= 0.5
    assert scores[0] - scores[1] >= 0.2
    assert ec["interp_underrun_during_path"] / max(ec["interp_underrun_count"], 1) >= 0.7


def test_case_b_resonance_family_is_band_blocked():
    f = case_b()
    assert f["resonance"]["candidates"] == []
    assert {"R-03", "R-04"} <= set(f["freq_limits"]["blocked_rules"])
    rows = {(u["feature"], u.get("rule")) for u in f["unavailable"]}
    assert ("resonance.candidates", "R-03") in rows
    assert ("resonance.candidates", "R-04") in rows


# --- C2 规则 2 的逐路账务：契约示例必须先过自己的检查，才有资格当验收锚点 ---

@pytest.mark.parametrize("key", ["A", "B", "CASE_B", "A_NO_EVENTS"])
def test_every_example_books_its_own_nulls(key):
    """示例演示的就是"把算不了写成结构化事实"，它自己欠账就是自我打脸（规则 2）。"""
    features.check_null_accounting(load(key))


@pytest.mark.parametrize("key", ["A", "B", "CASE_B", "A_NO_EVENTS"])
def test_every_example_carries_the_sample_scale_keys(key):
    """A-102 ②：`n_segments`/`bins_in_band`/`three_db_width_bins` 必须**键在场**，缺键是契约缺陷
    而不是「没有这个量」。此前只有接入产物过这道检查（`assertions.py` 调 `check_self_consistency`），
    手抄示例不过 ⟹ `kb4_case_b_features.json` 缺两键而机器看不见（本轮补的载体）。"""
    features.check_resonance_counts(load(key))


@pytest.mark.parametrize("key", ["A", "B", "CASE_B", "A_NO_EVENTS"])
def test_no_example_has_a_value_and_a_row_on_the_same_path(key):
    """C2 规则 14 的互斥：同一路径不得既有值又有 `unavailable` 行（引擎口径 `_dig`+`_has_value`）。"""
    f = load(key)
    both = [r["feature"] for r in f["unavailable"] if features._has_value(features._dig(f, r["feature"]))]
    assert not both, "既有值又记账的路径：%s" % both


def test_case_b_dropped_sample_scale_key_is_caught():
    """负向（检查 22）：删掉 `n_segments` 键 ⟹ 检查必须翻红并指名那把尺子。"""
    f = load("CASE_B")
    del f["resonance"]["estimation"]["n_segments"]
    with pytest.raises(features.FeatureError, match="n_segments"):
        features.check_resonance_counts(f)


def test_example_b_pair_separation_bins_is_booked_not_guessed():
    """规则 2 的合法 null 清单**不**豁免 `pair_separation_bins`（与 n_segments 同族，A-102 ②）。"""
    f = load("B")
    assert f["resonance"]["estimation"]["pair_separation_bins"] is None
    rows = {u["feature"]: u for u in f["unavailable"]}
    assert "resonance.estimation.pair_separation_bins" in rows
    assert "反推" in rows["resonance.estimation.pair_separation_bins"]["reason"]


def test_example_a_twin_books_the_same_nulls():
    """孪生只差 `event_context`，账务也同步差同一块：非 event_context 的行两边逐字相同。"""
    a, t = load("A"), load("A_NO_EVENTS")
    assert a["unavailable"] == t["unavailable"]


def test_short_name_row_is_rejected_on_the_example():
    """负向（检查 22）：把例 B 的一行改回它原来的短名写法 ⟹ 检查必须翻红。"""
    f = load("B")
    f["unavailable"][0]["feature"] = "cur_q_rms_a"      # 例 B 历史上的写法（缺 `global.`）
    with pytest.raises(features.FeatureError, match="点分全路径"):
        features.check_null_accounting(f)


def test_dropped_row_is_rejected_on_the_example():
    """负向（检查 22）：从例 B 抹掉一条应有的行 ⟹ 检查必须翻红并指名那条 null 路径。"""
    f = load("B")
    f["unavailable"] = [u for u in f["unavailable"]
                        if u["feature"] != "global.cur_q_rms_pct"]
    assert f["global"]["cur_q_rms_pct"] is None
    with pytest.raises(features.FeatureError, match="global.cur_q_rms_pct"):
        features.check_null_accounting(f)

