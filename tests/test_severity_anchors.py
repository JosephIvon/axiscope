"""A-100 的验收：KB4 §2.9 补齐 `software_induced_*` 严重度锚点后——
①字典序保留（头条与档内序不因 R-26 跨档改写）；②锚点表有软件族行且规则表指向表行；
③R-26 只在同档内决定解释优先；④有序链缺支即登记（含第三支的补集第 6 支）。
文档侧检查读的是**本轮改后的 docs/kb 原文**，防止表行与规则表漂移。
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from axiscope import engine  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
EXAMPLES = os.path.join(ROOT, "examples")
CASE_A_COUNTS = {"welch_segments": 8, "band_bins": 96}


def _load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return json.load(fh)


def _hyp(report, fault_mode):
    for h in report["hypotheses"]:
        if h["fault_mode"] == fault_mode:
            return h
    raise AssertionError("报告中没有 %s" % fault_mode)


def _kb4_section_2_9():
    with open(os.path.join(ROOT, "docs", "kb", "KB4-attribution-model.md"), encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("## 2.9 ")
    end = text.index("## 2.10 ")
    return text[start:end]


def _kb3_r26_block():
    with open(os.path.join(ROOT, "docs", "kb", "KB3-tuning-rules.md"), encoding="utf-8") as fh:
        text = fh.read()
    start = text.index("### R-26 ")
    end = text.index("### R-27 ")
    return text[start:end]


# ---------------------------------------------------------------- 裁决②：锚点表补软件族行

def test_kb4_anchor_table_now_covers_software_family():
    sec = _kb4_section_2_9()
    s2 = next(line for line in sec.splitlines() if line.startswith("| S2 "))
    s3 = next(line for line in sec.splitlines() if line.startswith("| S3 "))
    # R-19（轨迹中断/超差）与 R-21（节拍损失）→ S2；R-18（仅表现为尖峰）与 R-24（轮询延迟）→ S3
    assert "R-19" in s2 and "R-21" in s2 and "R-20 无告警支" in s2
    assert "R-18" in s3 and "R-24" in s3
    # R-20 既有 S0 支维持不动
    s0 = next(line for line in sec.splitlines() if line.startswith("| S0 "))
    assert "n_alarm ≥ 1" in s0 and "R-20" in s0


def test_rule_table_r19_points_to_anchor_row_not_assumed():
    prov = engine.rule("R-19")["severity_provenance"]
    assert not prov.startswith("assumed")
    assert prov.startswith("classified:")
    assert "KB4 §2.9 S2" in prov
    assert engine.rule("R-19")["severity"] == 2


def test_kb3_r26_block_and_family_header_point_to_anchor_rows():
    r26 = _kb3_r26_block()
    assert "R-26 有序链无命中" in r26
    assert "静默挑一支或改序" in r26
    assert "不重排" in r26 and "severity 序" in r26
    with open(os.path.join(ROOT, "docs", "kb", "KB3-tuning-rules.md"), encoding="utf-8") as fh:
        fam = fh.read()
    header = fam[fam.index("### 族三"):fam.index("### R-18 ")]
    assert "R-19/R-21→S2" in header and "R-18/R-24→S3" in header


# ---------------------------------------------------------------- 裁决⑤：推断留痕机制保留，措辞换成分类锚点

def test_anchored_severity_still_leaves_assumption_trace():
    """R-19 的 severity 现在指向 §2.9 表行，但那是"按后果类型归档"的分类锚点，
    报告仍须带 audit.assumptions 行且不得写成唯一结论（A-100 ⑤ 的机制不许推翻）。"""
    report = engine.analyze(_load("kb4_case_b_features.json"))
    rows = report["audit"]["assumptions"]
    # 锚 = KB4 叶名（C1 §audit.assumptions 的第五种形式），散文里再说明是哪一档
    assert any(a["anchor"] == "software_induced_interp_buffer_underrun"
               and "severity" in a["statement"] for a in rows)
    assert any("分类锚点" in a["statement"] and "不得写成唯一结论" in a["statement"] for a in rows)
    assert not any("无 KB4 §2.9 锚点" in a["statement"] for a in rows)  # 锚已补上，旧措辞必须退场


# ---------------------------------------------------------------- 裁决①③：字典序保留、R-26 不跨档

def test_case_a_headline_remains_software_family_after_anchors():
    """补完锚点后 C2 例 A 的头条仍是软件族：R-19 的 S2（登记值）数值小于 R-03 的 S3。"""
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    sevs = [h["severity"] for h in report["hypotheses"]]
    assert sevs == sorted(sevs)  # 字典序第一键就是 severity，档位非递减
    assert report["hypotheses"][0]["fault_mode"] == "software_induced_interp_buffer_underrun"
    assert _hyp(report, "software_induced_interp_buffer_underrun")["severity"] == 2
    assert _hyp(report, "mechanical_resonance")["severity"] == 3
    assert report["verdict"]["primary"] == "H1"


def test_r26_in_scope_hit_does_not_override_severity_order():
    """把例 A 改成 R-26 第 2 支命中（abs(A_s)<1.5）：链判"机械谐振优先"只作用于档内解释，
    S2 的软件族仍排在 S3 的谐振之前——跨档排序归 §2.9，R-26 不得覆盖（A-100 ③）。"""
    features = _load("c2_example_a.json")
    features["ff_mismatch"]["asymmetry_ratio"] = 1.26  # abs(A_s)=1.26 < 1.5，dwell==true、coh=0.86
    report = engine.analyze(features, sample_counts=CASE_A_COUNTS)
    assert any("R-26#2：判机械谐振" in n for n in report["audit"]["arbitration_notes"])
    assert report["hypotheses"][0]["fault_mode"] == "software_induced_interp_buffer_underrun"
    assert report["hypotheses"][0]["severity"] == 2


def test_r26_no_hit_on_example_a_is_registered():
    """例 A 原状：第 2 支（abs(A_s)<1.5，实际 2.26）与第 3 支（dwell==false，实际 true）
    同时不成立，第 6 支补集同样不命中 ⟹ 有序链无命中必须登记，不得静默。"""
    report = engine.analyze(_load("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    notes = report["audit"]["arbitration_notes"]
    assert any("R-26 有序链无命中" in n for n in notes)
    assert not any("R-26#6" in n for n in notes)


def test_r26_branch6_complement_registers_no_reorder():
    """第三支的补集（A-100 ④）：dwell==true 且 abs(A_s)<1.5，但相干性不足使第 2 支不成立
    ⟹ 登记「R-26#6 ⟹ 不重排」，按 §2.9 原序，禁止静默挑一支。"""
    features = _load("c2_example_a.json")
    features["ff_mismatch"]["asymmetry_ratio"] = 1.26
    features["resonance"]["candidates"][0]["coherence_torque_velocity"] = 0.5  # < 0.7 ⟹ 第 2 支不成立
    notes = engine.arbitrate_r26(features, {"mechanical_resonance": None})
    assert any("R-26#6" in n and "不重排" in n for n in notes)
    assert not any("有序链无命中" in n for n in notes)
