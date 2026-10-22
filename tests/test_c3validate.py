"""c3validate 的契约测试：C3 不可协商规则 1–20 与 KB4 §0 不变式。

正向：C3 契约的两份示例（E1 单假设 / E2 排序对）+ 规则 12 的诚实真空文档必须通过。
负向：每条硬规则至少一个注入样本证明检查器真的报错（KB0 §6 检查 22）。

A-107 ③ 之后示例有**两份**，测试的基准夹具是 E2（两条假设，能同时钉排序与算术），
只有一条假设的锚点场景（KB4 §2.3 算例 A 的 `overall = 0.59`）用 E1。
夹具里的下标会随排序漂移，故按 `fault_mode` 取假设、用其自身 `id` 拼检查 id，不写死 H1/H2。

    python -m pytest tests/test_c3validate.py -q
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from axiscope import c3validate, core_hash  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C3_DOC = os.path.join(ROOT, "docs", "contracts", "C3-diagnosis.md")


def _load(name):
    return json.load(io.open(os.path.join(FIX, name), encoding="utf-8"))


E1_RESONANCE = "c3_example_resonance_059.json"
E2_RANKED_PAIR = "c3_example_ranked_pair.json"
RESONANCE = "mechanical_resonance"
FEEDFORWARD = "electrical_feedforward_mismatch"


def _example():
    """E2 = 两条假设并存、按 KB4 §2.9 排序的那份，也是所有注入测试的变异基准。"""
    return copy.deepcopy(_load(E2_RANKED_PAIR))


def _example_resonance():
    """E1 = 只有机械谐振一条假设、`overall = 0.59` 的那份（KB4 §2.3 算例 A 的锚点）。"""
    return copy.deepcopy(_load(E1_RESONANCE))


def _hyp(diag, leaf):
    """按 `fault_mode` 取假设（id 随排序漂移，写死 H1/H2 会在拆示例后静默失准）。"""
    return next(h for h in diag["hypotheses"] if h["fault_mode"] == leaf)


def failed_ids(diag):
    return {c.check_id for c in c3validate.validate(diag) if not c.passed}


def has_fail(diag, prefix):
    return any(cid.startswith(prefix) for cid in failed_ids(diag))


# 契约示例的 §2.1 复算字段（n/n_ref/conf/freq_hz/band_floor_hz）取值以 KB4 §2.3 算例 A 为准
# （Welch 8/4、带内 bin 96/15、3dB 宽 22/8、dwell 3/1、rest 2/1、move 6/4）。A-101 ① 之后这五个
# 字段已进示例 JSON 本身，故测试只需**剥掉**它们来演示缺口路径，不再往里补。
_RAW_KEYS = ("n", "n_ref", "conf", "freq_hz", "band_floor_hz")


def _strip_h1_raw(diag):
    """把 E2 rank 1 假设的 §2.1 原始字段抹掉，回到 A-101 之前的欠规范形状。"""
    for e in diag["hypotheses"][0]["supporting_evidence"]:
        for k in _RAW_KEYS:
            e.pop(k, None)
    return diag


def _restamp(diag):
    """按 C3 规则 21 重算并写回确定性核心哈希。

    供"只想验某一条检查"的变异测试使用：证据行在哈希核内，抹掉 `n/n_ref/conf` 这类字段
    必然改指纹，若不重盖，`C3-R21-core-hash-recompute` 会与被测检查一起翻红，测试就同时
    验了两件事、失败时也说不清是哪一件。反方向（"改动必须改哈希"）由规则 21 自己的
    负向例单独钉，不靠这里顺带证明。
    """
    diag["audit"]["deterministic_core_hash"] = core_hash.core_hash(diag)
    return diag


# ---------------------------------------------------------------- 正向

def test_c3_contract_example_is_fully_recomputable():
    """A-101 ①/④ + A-107 ③：E2 自带 §2.1 五字段 ⟹ 两条假设都能零 gap 独立复算，
    反证 ρ′ 方向不自相矛盾（前馈 C=0.48、谐振 C=0.65），且 `overall = 0.43` 按去重缺席原因数复算。"""
    diag = _example()
    checks = {c.check_id: c for c in c3validate.validate(diag)}
    assert not [c for c in checks.values() if not c.passed], [
        (c.check_id, c.detail) for c in checks.values() if not c.passed]
    for hid in ("H1", "H2"):
        assert f"C3-R15-recompute-gap/{hid}" not in checks
        assert checks[f"C3-R03-recompute/{hid}"].passed, checks[f"C3-R03-recompute/{hid}"].detail
    assert diag["verdict"]["overall_confidence"] == 0.43


def test_c3_resonance_only_example_recomputes_the_059_anchor():
    """E1 的唯一职责：保住 KB4 §2.3 算例 A 的 `overall = 0.59` 锚点。
    单假设 ⟹ 规则 20 无并列可排，因此该数不再可能被读成"两条并存时的头条"（A-107 ①）。"""
    diag = _example_resonance()
    checks = {c.check_id: c for c in c3validate.validate(diag)}
    assert not [c for c in checks.values() if not c.passed], [
        (c.check_id, c.detail) for c in checks.values() if not c.passed]
    assert "C3-R15-recompute-gap/H1" not in checks
    assert len(diag["hypotheses"]) == 1
    assert diag["hypotheses"][0]["id"] == diag["verdict"]["primary"] == "H1"
    assert diag["verdict"]["overall_confidence"] == 0.59


def test_c3_example_refutation_direction_is_now_self_consistent():
    """A-101 ②：前馈那条反证 operator `<` ⟹ §2.1(a) 的 ρ′ = threshold/value = 412.6/690 = 0.598 ⟹ v_j=0.05。
    旧示例写 ρ′=1.672 / penalty=0.10（把 `<` 当 `>=`），当时必须翻红；现在与声明一致。
    反把 penalty 退回 0.10 必须再次翻红——证明这条检查不是摆设。"""
    diag = _example()
    hid = _hyp(diag, FEEDFORWARD)["id"]
    assert not has_fail(diag, "C3-R15-refut/%s" % hid)
    _hyp(diag, FEEDFORWARD)["contradicting_evidence"][0]["penalty"] = 0.10
    assert has_fail(diag, "C3-R15-refut/%s" % hid)


def test_gap_path_still_fires_when_raw_fields_are_missing():
    """gap 检查保持**非阻塞**（缺字段是上游契约的欠规范，不是本报告的错），但绝不能沉默：
    抹掉原始字段后必须显式标注「不可复算，需补字段」，且不进 failed 集合。"""
    diag = _restamp(_strip_h1_raw(_example()))
    checks = {c.check_id: c for c in c3validate.validate(diag)}
    gap = checks.get("C3-R15-recompute-gap/H1")
    assert gap is not None and gap.passed, gap
    assert "不可复算" in gap.detail and "需补字段" in gap.detail
    assert not [c for c in checks.values() if not c.passed]


def _doc_blocks():
    """契约文档里的示例内联副本，按 `case_id` 建表（A-107 ③ 之后有两份，先后顺序不可依赖）。"""
    text = io.open(C3_DOC, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"```json\n(.*?)\n```", text, re.S):
        try:
            obj = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(obj, dict) and "hypotheses" in obj and "case_id" in obj:
            assert obj["case_id"] not in out, "同一 case_id 在文档里有两份内联副本"
            out[obj["case_id"]] = obj
    return out


def test_c3_doc_inline_copies_and_fixtures_are_the_same_objects():
    """每份示例有两个载体（契约内联副本 + fixture）。KB4 算例 A 的锚点、检查 26 的零 gap
    复算、以及 C5/KB8 里引用该示例数字的地方，此前会因为两份载体各自漂移而互相打脸——
    A-101 的修复就是先发现 fixture 与文档不同步。深比对是唯一不靠人眼的办法。
    A-107 拆成两份后，比对必须**逐份**做，并且数量也要钉住（少一份即示例被回退合并）。"""
    blocks = _doc_blocks()
    assert sorted(blocks) == sorted([_example()["case_id"], _example_resonance()["case_id"]])
    assert blocks[_example()["case_id"]] == _example()
    assert blocks[_example_resonance()["case_id"]] == _example_resonance()


def test_c3_doc_inline_copies_validate_with_zero_gap():
    """§6 检查 26：契约示例必须被该契约自己的校验器以**零 gap** 复算，否则不得作验收锚点。
    规则 20 加入后"零 gap"的含义扩到排序——内联副本连 rank 序也必须可判。"""
    for case_id, obj in _doc_blocks().items():
        checks = c3validate.validate(obj)
        assert not [c for c in checks if not c.passed], (
            case_id, [(c.check_id, c.detail) for c in checks if not c.passed])
        assert not [c for c in checks if "recompute-gap" in c.check_id], case_id


def test_honest_vacuum_passes():
    diag = _load("c3_honest_vacuum.json")
    assert not [c for c in c3validate.validate(diag) if not c.passed]
    c3validate.assert_ok(diag)


def test_resonance_worked_example_recomputes_0652():
    """KB4 §2.3 算例 A 的逐格复算 C=0.652 必须**两份示例都给得出**：
    E1 的唯一假设、以及 E2 里 rank 2 的那条。拆示例拆的是前提与排序演示，不是算例锚点。"""
    for diag in (_example_resonance(), _example()):
        ctx = c3validate._confidence_ctx(diag)
        det = c3validate._recompute_detail(_hyp(diag, RESONANCE), ctx)
        assert det.gap is None and det.strength_violations == [], (det.gap, det.strength_violations)
        assert abs(det.c - 0.652) <= 0.005, det.c


def test_feedforward_worked_example_recomputes_0482():
    """前馈假设的两条支持（ρ=1.507/1.383、n=100 vs n_ref=50 ⟹ n_factor=0.8）复算 C=0.482。
    示例声明的 scaffolded n 与 KB3 R-15 的必要上下文在 `scaffolding_note` 里已声明为假定值。"""
    diag = _example()
    ctx = c3validate._confidence_ctx(diag)
    det = c3validate._recompute_detail(_hyp(diag, FEEDFORWARD), ctx)
    assert det.gap is None and det.strength_violations == [] and det.refutation_violations == []
    assert abs(det.c - 0.482) <= 0.005, det.c


def test_example_confidence_recomputes():
    """规则 3/15：rank 1 假设复算走原始证据，不是自报 strength 的复述聚合。
    篡改声明 strength（原始 n/n_ref/conf 不变）⟹ §2.1 复算值与声明不符 ⟹ C3-R15-strength 翻红；
    聚合出的 C 只依赖原始证据，故 confidence 仍与复算一致（旧代码会把 0.999 当真相重聚合）。"""
    diag = _example()
    h1 = diag["hypotheses"][0]
    hid = h1["id"]
    ctx = c3validate._confidence_ctx(diag)
    rc = c3validate._recompute_confidence(h1, ctx)
    assert abs(round(rc, 2) - h1["confidence"]) <= c3validate.TOL
    h1["supporting_evidence"][1]["strength"] = 0.999
    assert has_fail(diag, "C3-R15-strength/%s[1]" % hid)


def test_rule15_strength_inconsistent_with_formula():
    """(a) 声明 strength 与 §2.1 给定原始证据不符 ⟹ 规则 15 违规。"""
    diag = _example()
    hid = _hyp(diag, RESONANCE)["id"]
    _hyp(diag, RESONANCE)["supporting_evidence"][2]["strength"] = 0.99  # 复算 S(e)≈0.765
    assert has_fail(diag, "C3-R15-strength/%s[2]" % hid)


def test_hand_typed_strength_is_caught():
    """(b) 回归钉：示例草稿曾在前馈的两条支持上手写 S=0.41/0.36。给定契约现在的 n=100/n_ref=50
    （n_factor=0.8）与 conf=1.0，§2.1 复算只能是 0.518/0.494；0.36 反解要 n_factor=0.583
    < 文档下限 0.6，即**结构上不可能**由 §2.1 产生（手写数的指纹）。A-101 ① 已把示例改成复算值，
    这里钉两件事：退回手写值须翻红；抹掉原始字段则降级为**已标注的缺口**，不得静默通过。"""
    diag = _example()
    hid = _hyp(diag, FEEDFORWARD)["id"]
    _hyp(diag, FEEDFORWARD)["supporting_evidence"][1]["strength"] = 0.36
    assert has_fail(diag, "C3-R15-strength/%s[1]" % hid)
    diag = _example()
    for e in _hyp(diag, FEEDFORWARD)["supporting_evidence"]:
        e["strength"] = 0.41
        for k in _RAW_KEYS:
            e.pop(k, None)
    gap = {c.check_id: c for c in c3validate.validate(diag)}.get("C3-R15-recompute-gap/%s" % hid)
    assert gap is not None and gap.passed and "需补字段" in gap.detail, gap



# ---------------------------------------------------------------- 负向：逐条硬规则

def test_rule10_display_name_in_fault_mode():
    diag = _example()
    diag["hypotheses"][0]["fault_mode"] = "friction_crawling"
    assert has_fail(diag, "C3-R10/H1")


def test_rule1_single_evidence_hypothesis():
    diag = _example()
    diag["hypotheses"][1]["supporting_evidence"] = [diag["hypotheses"][1]["supporting_evidence"][0]]
    assert has_fail(diag, "C3-R01/H2")


def test_rule15_penalty_inconsistent_with_rho():
    diag = _example()
    ce = diag["hypotheses"][0]["contradicting_evidence"][0]
    ce["rho_prime"] = 2.5          # ρ′≥2 应为 0.20
    ce["penalty"] = 0.10
    assert has_fail(diag, "C3-R15-fn/H1[0]")


def test_rule15_penalty_not_a_tier():
    diag = _example()
    diag["hypotheses"][0]["contradicting_evidence"][0]["penalty"] = 0.18
    assert has_fail(diag, "C3-R15-tier/H1[0]")


def test_rule15_penalty_without_rho():
    diag = _example()
    ce = diag["hypotheses"][0]["contradicting_evidence"][0]
    del ce["rho_prime"]
    assert has_fail(diag, "C3-R15/H1[0]")


def test_rule6_writes_to_device_true():
    diag = _example()
    diag["safety"]["writes_to_device"] = True
    assert has_fail(diag, "C3-R06-writes")
    with pytest.raises(c3validate.ValidationError):
        c3validate.assert_ok(diag)


def test_rule14_t2_claim_worded_as_verified_refuses_report():
    diag = _example()
    hid = _hyp(diag, FEEDFORWARD)["id"]
    _hyp(diag, FEEDFORWARD)["display_name"] = "加速度前馈失配（已核对厂商阈值）"  # 该假设台账为 T2 < T1
    assert "C3-R14-REFUSE" in failed_ids(diag)
    with pytest.raises(c3validate.RefuseReportError):
        c3validate.assert_ok(diag)
    assert hid == "H1"  # 前馈失配在 §2.9 序里排 rank 1（A-107 ③ 的正题）


def test_rule14_missing_tier_row_defaults_to_T3():
    """台账缺行按最保守档 T3 处理，不得当作『没标注就豁免』。"""
    diag = _example()
    hid = _hyp(diag, RESONANCE)["id"]
    diag["audit"]["tier_ledger"] = [r for r in diag["audit"]["tier_ledger"] if r["claim_id"] != hid]
    _hyp(diag, RESONANCE)["display_name"] = "机械谐振（实测通过）"
    assert "C3-R14-REFUSE" in failed_ids(diag)


def test_rule4_simulation_validated_without_validation_record():
    diag = _example()
    hid = _hyp(diag, RESONANCE)["id"]      # 带 recommendation 的是谐振那条
    _hyp(diag, RESONANCE)["recommendation"]["expected_effect"]["validation_id"] = "VX"
    assert has_fail(diag, "C3-R04-sim/%s" % hid)


def test_rule4_basis_missing():
    diag = _example()
    hid = _hyp(diag, RESONANCE)["id"]
    del _hyp(diag, RESONANCE)["recommendation"]["expected_effect"]["basis"]
    assert has_fail(diag, "C3-R04/%s" % hid)


def test_rule4_unverified_must_not_carry_numbers():
    diag = _example()
    hid = _hyp(diag, RESONANCE)["id"]
    ee = _hyp(diag, RESONANCE)["recommendation"]["expected_effect"]
    ee["basis"] = "unverified"
    assert has_fail(diag, "C3-R04-unver/%s" % hid)


def test_rule5_low_confidence_needs_next_data():
    diag = _example()
    h2 = diag["hypotheses"][1]
    h2["confidence"] = 0.5
    h2["next_data_to_collect"] = []
    assert has_fail(diag, "C3-R05/H2")


def test_rule11_gate_rule_as_hypothesis():
    diag = _example()
    diag["hypotheses"][0]["fault_mode"] = "R-28"
    assert has_fail(diag, "C3-R11/H1")
    assert has_fail(diag, "C3-R10/H1")


def test_gate_rule_as_support_backing_hypothesis():
    diag = _example()
    diag["hypotheses"][0]["supporting_evidence"][0]["rule_id"] = "R-30"
    assert has_fail(diag, "INV-16/H1")


def test_rule9_inv11_unobserved_wording():
    diag = _example()
    diag["hypotheses"][0]["display_name"] = "加速度前馈失配（未发现其它异常）"
    assert has_fail(diag, "INV-11-wording")


def test_rule16_duplicate_blocked_by_counted_once():
    """3 行 not_evaluable 只有 2 个 distinct blocked_by。primary（前馈，C=0.4818）若按行数惩罚
    会得 0.4818×0.85≈0.41；按去重原因数是 0.4818×0.90≈0.43 ⟹ 写 0.41 必须翻红。"""
    diag = _example()
    diag["verdict"]["overall_confidence"] = 0.41  # 若错误地数 3 行 ⟹ 0.4818×0.85≈0.41
    assert has_fail(diag, "C3-R16-overall")


def test_rule16_family_and_leaf_share_blocked_by():
    """族级行与它覆盖的叶同源 ⟹ 去重后仍为 2，distinct 计数正确时示例通过。"""
    diag = _example()
    keys = {ne.get("blocked_by") for ne in diag["differential"]["not_evaluable"]}
    assert keys == {"absent_temp_channel", "absent_events_jsonl"}
    assert not has_fail(diag, "C3-R16-overall")


def test_rule16_invented_blocked_by_key_rejected():
    diag = _example()
    diag["differential"]["not_evaluable"][0]["blocked_by"] = "we_dont_have_temp_bro"
    assert has_fail(diag, "C3-R16-vocab[0]")


# ---------------------------------------------------------------- 规则 19：assumptions 的形状

def test_rule19_prose_row_is_rejected():
    """散文行没有锚 ⟹ 无法被引用，也无法回答"这条假定作废时哪些结论跟着塌"（#25）。"""
    diag = _example()
    diag["audit"]["assumptions"][0] = "限流值没给，我们按额定电流兜底了"
    assert has_fail(diag, "C3-R19-assumption-shape[0]")


def test_rule19_anchor_must_be_one_of_the_six_forms():
    diag = _example()
    diag["audit"]["assumptions"][1]["anchor"] = "H2 的 severity 是自己推断的"
    assert has_fail(diag, "C3-R19-assumption-shape[1]")
    diag = _example()
    diag["audit"]["assumptions"][1]["anchor"] = "src/axiscope/engine.py"
    assert has_fail(diag, "C3-R19-assumption-shape[1]")


def test_rule19_empty_statement_is_rejected():
    diag = _example()
    diag["audit"]["assumptions"][1]["statement"] = "   "
    assert has_fail(diag, "C3-R19-assumption-shape[1]")


def test_rule19_carriers_exist_in_both_examples():
    """检查 23（字段须有载体）：两份示例都得挂上合法假定行，否则规则 19 只在一份里被验过。
    E1 单假设只挂 1 行，E2 挂 3 行（severity 归档锚按规则拆成 `R-15`/`R-03` 两条规则形锚）。"""
    e1 = _example_resonance()["audit"]["assumptions"]
    e2 = _example()["audit"]["assumptions"]
    assert len(e1) == 1 and len(e2) == 3
    assert {r["anchor"] for r in e1} == {"global.fe_rms_counts"}
    assert {r["anchor"] for r in e2} == {"global.fe_rms_counts", "R-15", "R-03"}


# ---------------------------------------------------------------- 负向：规则 20（rank = §2.9 字典序）

def test_rule20_positive_both_examples_are_in_severity_order():
    """规则 20 的正例：E2 的 rank 序等于 `(severity↑, −C, fault_mode)`，且 primary 就是 rank 1——
    **即便 rank 1 的置信度更低**（0.48 < 0.65）。这正是 A-107 要演示的反直觉之处。"""
    e2 = _example()
    assert not has_fail(e2, "C3-R20")
    order = sorted(e2["hypotheses"], key=lambda h: h["rank"])
    assert [h["fault_mode"] for h in order] == [FEEDFORWARD, RESONANCE]
    assert [h["severity"] for h in order] == [2, 3]
    assert [h["confidence"] for h in order] == [0.48, 0.65]
    assert e2["verdict"]["primary"] == order[0]["id"]
    assert not has_fail(_example_resonance(), "C3-R20")  # 单假设无并列可排，检查须不误报


def test_rule20_rank_swap_is_rejected():
    """把两条假设的 rank 对调（即旧示例的"置信度高者当头条"写法）⟹ 必须翻红。"""
    diag = _example()
    ff, res = _hyp(diag, FEEDFORWARD), _hyp(diag, RESONANCE)
    ff["rank"], res["rank"] = res["rank"], ff["rank"]
    assert has_fail(diag, "C3-R20-rank-monotonic")


def test_rule20_primary_must_be_rank1():
    diag = _example()
    diag["verdict"]["primary"] = _hyp(diag, RESONANCE)["id"]
    diag["verdict"]["overall_confidence"] = 0.59   # 跟着改成"谐振当头条"的算术，排序检查仍须独立翻红
    assert has_fail(diag, "C3-R20-primary-is-rank1")


def test_rule20_rank_must_be_contiguous():
    diag = _example()
    _hyp(diag, RESONANCE)["rank"] = 3
    assert has_fail(diag, "C3-R20-rank-contiguous")


def test_rule20_catches_the_pre_split_merged_example():
    """检查 22 的钉：A-107 之前那份示例把两条假设挤在同一个 `case_id` 里，并让 C=0.65 的谐振
    当 rank 1 头条、`overall = 0.59`。它的**算术全绿**——规则 3/15/16 逐格复算都对，
    矛盾只存在于排序与散文的自我声明里。这里按旧形状重建它：排序必须翻红，且**只有排序类
    检查**翻红（否则这条钉抓不到"算术对、排序错"这一类）。

    规则 21 落码后翻红的是 3 项而不是 2 项：`-rank-monotonic` + `-primary-is-rank1` +
    `-core-hash-recompute`。哈希核含 `rank` 序而不含散文，所以"序错"同时撞上两张网；
    这是加了一面网，不是放宽了口径——`C3-R16-overall` 与两条 `C3-R03-recompute` 仍然必须全绿，
    那才是"算术对"的证据。"""
    diag = _example()
    ff, res = _hyp(diag, FEEDFORWARD), _hyp(diag, RESONANCE)
    ff["rank"], res["rank"] = 2, 1
    diag["verdict"]["primary"] = res["id"]
    diag["verdict"]["overall_confidence"] = 0.59
    failed = failed_ids(diag)
    assert any(cid.startswith("C3-R20-rank-monotonic") for cid in failed), failed
    assert any(cid.startswith("C3-R20-primary-is-rank1") for cid in failed), failed
    assert any(cid.startswith("C3-R21-core-hash-recompute") for cid in failed), failed
    assert not any(cid.startswith("C3-R16-overall") for cid in failed), failed
    assert not any(cid.startswith("C3-R03-recompute") for cid in failed), failed
    assert all(cid.startswith("C3-R20") or cid == "C3-R21-core-hash-recompute"
               for cid in failed), failed


def test_rule20_is_in_the_contract_text():
    """规则 20 的检查 id 必须同时出现在契约正文里（散文与实现不得各说各话，A-104 同源纪律）。"""
    text = io.open(C3_DOC, encoding="utf-8").read()
    for cid in ("C3-R20-rank-contiguous", "C3-R20-rank-monotonic", "C3-R20-primary-is-rank1"):
        assert cid in text, cid


def test_cap5_blocked_rule_used_as_support():
    diag = _example()
    diag["freq_limits"] = {"blocked_rules": ["R-03"]}
    assert has_fail(diag, "CAP-5-rule/%s[1]" % _hyp(diag, RESONANCE)["id"])  # R-03 证据落在 blocked_rules
    assert not has_fail(diag, "CAP-5-rule/%s[" % _hyp(diag, FEEDFORWARD)["id"])  # 前馈用 R-15，不受影响


def test_cap5_branch_id_is_distinct_from_bare_id():
    """R-11#switching_freq 与裸 R-11 视为不同 id（features.py 已建立的粒度）。"""
    diag = _example()
    hid = _hyp(diag, FEEDFORWARD)["id"]
    _hyp(diag, FEEDFORWARD)["supporting_evidence"][1]["rule_id"] = "R-11"
    diag["freq_limits"] = {"blocked_rules": ["R-11#switching_freq"]}
    assert not has_fail(diag, "CAP-5-rule/%s[1]" % hid)  # 裸 R-11 不被 branch 级阻塞命中
    diag["freq_limits"] = {"blocked_rules": ["R-11"]}
    assert has_fail(diag, "CAP-5-rule/%s[1]" % hid)      # 裸 R-11 被阻塞


def test_cap5_unavailable_feature_used_as_support():
    diag = _example()
    diag["unavailable"] = [{"feature": "resonance.candidates[0].amplitude_ratio_vs_broadband"}]
    assert has_fail(diag, "CAP-5-feat/%s[1]" % _hyp(diag, RESONANCE)["id"])


def test_inv5_causal_false_forbids_software_hypothesis():
    diag = _example()
    diag["hypotheses"][0]["fault_mode"] = "software_induced_host_thread_jitter"
    diag["causal_claims_permitted"] = False
    assert has_fail(diag, "INV-5/")


def test_inv6_event_unavailable_forbids_software_hypothesis():
    diag = _example()
    diag["hypotheses"][0]["fault_mode"] = "software_induced_bus_cycle_miss"
    diag["event_context"] = {"available": False}
    assert has_fail(diag, "INV-6/")


def test_rule8_missing_family():
    diag = _example()
    diag["hypotheses"][0]["fault_mode"] = "mechanical_double_inertia"
    diag["differential"]["considered"] = [c for c in diag["differential"]["considered"]
                                          if not c.startswith("software_induced")]
    for ne in list(diag["differential"]["not_evaluable"]):
        if str(ne.get("fault_mode", "")).startswith("software_induced") or ne.get("family"):
            diag["differential"]["not_evaluable"].remove(ne)
    assert has_fail(diag, "C3-R08")


# ---------------------------------------------------------------- 负向：规则 17

def _set_external(diag, rows, counts):
    diag["audit"]["external_ledger"] = rows
    diag["audit"]["external_counts"] = counts
    return diag


def test_rule17_official_artifact_missing_path():
    diag = _example()
    row = {"claim_id": "x", "assertion_class": "3a", "external_reference": "official-artifact",
           "verified_against": {"manual_id": "M", "revision": "1", "clause": "8.9"},
           "verified_by": "self", "artifact_path": "docs/evidence/NO-SUCH-MANUAL.md", "extracted": True}
    _set_external(diag, [row], {"verified": 1, "total": 1})
    assert has_fail(diag, "C3-R17-artifact[0]")   # 路径不可解析
    assert has_fail(diag, "C3-R17-count")          # 降为 public-doc ⟹ 不计 k


def test_rule17_official_artifact_resolves_when_present():
    diag = _example()
    row = {"claim_id": "x", "assertion_class": "3a", "external_reference": "official-artifact",
           "verified_against": {"manual_id": "M", "revision": "1", "clause": "8.9"},
           "verified_by": "self", "artifact_path": "docs/kb/KB4-attribution-model.md", "extracted": True}
    _set_external(diag, [row], {"verified": 1, "total": 1})
    assert not has_fail(diag, "C3-R17-artifact")
    assert not has_fail(diag, "C3-R17-count")


def test_rule17_third_party_not_counted_as_verified():
    diag = _example()
    row = {"claim_id": "x", "assertion_class": "3a", "external_reference": "official-artifact",
           "verified_against": {"manual_id": "M", "revision": "1", "clause": "8.9"},
           "verified_by": "third_party_report", "artifact_path": "docs/kb/KB4-attribution-model.md",
           "extracted": False}
    _set_external(diag, [row], {"verified": 1, "total": 1})  # 谎报 third_party 计入 k
    assert has_fail(diag, "C3-R17-count")


def test_rule17_3b_closed_by_official_artifact():
    diag = _example()
    row = {"claim_id": "x", "assertion_class": "3b", "external_reference": "official-artifact",
           "verified_against": {"manual_id": "M", "revision": "1", "clause": "8.9"},
           "verified_by": "self", "artifact_path": "docs/kb/KB4-attribution-model.md",
           "extracted": True, "note": "手册为什么答不了：批次差异见 KB3"}
    _set_external(diag, [row], {"verified": 0, "total": 1})
    assert has_fail(diag, "C3-R17-3b[0]")  # 3b 只有 vendor_reply 能出待确认态


def test_rule17_3b_needs_manual_cant_answer_justification():
    diag = _example()
    row = {"claim_id": "x", "assertion_class": "3b", "external_reference": "vendor_reply",
           "verified_against": {"manual_id": "M", "revision": "1", "clause": "答复+日期"},
           "verified_by": "self", "artifact_path": None, "extracted": False}
    _set_external(diag, [row], {"verified": 0, "total": 1})
    assert has_fail(diag, "C3-R17-3b-why[0]")  # 无 note/why 举证


def test_rule17_second_field_name_rejected():
    diag = _example()
    row = {"claim_id": "x", "assertion_class": "3a", "external_reference": "memory",
           "verified_against": {"manual_id": None, "revision": None, "clause": None},
           "verified_by": "self", "artifact_path": None, "extracted": False,
           "unverified_signature": True}
    _set_external(diag, [row], {"verified": 0, "total": 1})
    assert has_fail(diag, "C3-R17-name[0]")  # A-54：JSON 里不出现第二个字段名


def test_rule17_counts_total_mismatch():
    diag = _example()
    diag["audit"]["external_counts"] = {"verified": 0, "total": 5}
    assert has_fail(diag, "C3-R17-total")


def _rank_checks(diag):
    """只跑规则 20 的三条检查（其它检查的变异会污染判读，见 `_restamp`）。"""
    out = {}

    def _chk(cid, ok, detail):
        out[cid] = (ok, detail)
    c3validate._check_rank_monotonic(diag, _chk)
    return out


# ---------------------------------------------------------------- 规则 21（#43 后半）

def test_rule21_every_example_carries_a_real_recomputable_hash():
    """规则 21 的五处占位符（契约两份内联副本 + 三份夹具）已在本批清零：每份都必须是
    `sha256:<64 位小写 hex>`，且按清单重算得同一个值。`is_placeholder` 单独查一遍，
    免得"格式对了但还是占位符"这种形状从缝里过去。"""
    from axiscope import core_hash as _ch
    for name in (E1_RESONANCE, E2_RANKED_PAIR, "c3_honest_vacuum.json"):
        diag = _load(name)
        declared = diag["audit"]["deterministic_core_hash"]
        assert _ch.is_computed(declared), (name, declared)
        assert not _ch.is_placeholder(declared), name
        assert declared == _ch.core_hash(diag), name
    for case_id, obj in _doc_blocks().items():
        assert obj["audit"]["deterministic_core_hash"] == _ch.core_hash(obj), case_id


def test_rule21_rank_swap_is_caught_by_the_recompute():
    """检查 22 要求的负向例 (a)：交换两条假设的 `rank` 而哈希不变 ⟹ 必须翻红。
    哈希核含 `hypotheses[]` 且**数组顺序保留**，所以这一改必然改指纹；不翻红就说明核被
    实现成了"排序无关的集合哈希"，那正好是 A-107「算术全对、序错」那个形状的藏身处。"""
    diag = _example()
    ff, res = _hyp(diag, FEEDFORWARD), _hyp(diag, RESONANCE)
    ff["rank"], res["rank"] = res["rank"], ff["rank"]
    assert has_fail(diag, "C3-R21-core-hash-recompute")


def test_rule21_narrative_rewrite_leaves_the_hash_alone():
    """检查 22 要求的负向例 (b)：重写 `verdict.summary` 的措辞 ⟹ 哈希**不变**且不报警。
    自由叙述被排除在核外（规则 21 排除类 ①）；若这条红了，说明核把哈希当成了文案探测器，
    那它对跨版本对拍毫无用处。"""
    diag = _example()
    before = diag["audit"]["deterministic_core_hash"]
    diag["verdict"]["summary"] = "换一个说法：本次的主要结论见下。"
    assert diag["audit"]["deterministic_core_hash"] == before
    assert not has_fail(diag, "C3-R21")


def test_rule21_placeholder_is_rejected():
    diag = _example()
    diag["audit"]["deterministic_core_hash"] = "…"
    assert has_fail(diag, "C3-R21-core-hash-format")


def test_rule21_empty_string_is_a_gap_not_a_red():
    """空串是规则 21 写明的过渡期形态：记 gap、**不记红**。缺 `empty-is-gap` 这条豁免，
    规则 21 一落码就会把全仓过渡期产物整片判红，而那不是本报告的错。"""
    diag = _example()
    diag["audit"]["deterministic_core_hash"] = ""
    checks = {c.check_id: c for c in c3validate.validate(diag)}
    gap = checks["C3-R21-core-hash-empty-is-gap"]
    assert gap.passed and "gap" in gap.detail.lower() or "过渡期" in gap.detail
    assert not [c for c in checks.values() if not c.passed]


def test_rule21_check_ids_are_in_the_contract_text():
    """散文与实现不得各说各话（A-104 同源纪律）：三个检查 id 必须都在契约正文里。"""
    text = io.open(C3_DOC, encoding="utf-8").read()
    for cid in ("C3-R21-core-hash-recompute", "C3-R21-core-hash-format",
                "C3-R21-core-hash-empty-is-gap"):
        assert cid in text, cid
    assert "deterministic_core_hash" in text


# ------------------------------------------------- KB4 §2.9 的 ±0.01 并列带（A-116 ①）

def test_rank_band_c_is_leader_anchored():
    """并列带的划分本身要有可复算的定义。队长锚定 vs 链式扩张在 0.441/0.445/0.449 上
    分道扬镳：前者把 0.449 另起一带（距队长 0.008，在带内）……此处取更清楚的例子：
    0.50 / 0.49 / 0.47 —— 0.49 距队长 0.01 恰在带内、0.47 差 0.03 出带，两种划分一致；
    而 0.50 / 0.495 / 0.49 在链式下三行并成一带，队长锚定下 0.49 出带（距队长 0.01 是边界内，
    但距 0.495 也恰在带内 ⟹ 队长锚定把它收进 0.50 的带）。这里钉的是**队长说了算**。"""
    from axiscope import confidence as _cf
    leaders = _cf.rank_band_c([(0, 2, 0.50), (1, 2, 0.495), (2, 2, 0.49)])
    assert leaders == {0: 0.50, 1: 0.50, 2: 0.50}
    leaders = _cf.rank_band_c([(0, 2, 0.50), (1, 2, 0.495), (2, 2, 0.47)])
    assert leaders == {0: 0.50, 1: 0.50, 2: 0.47}
    # severity 是第一键：不同档之间不并带，哪怕 C 差 0.00
    assert _cf.rank_band_c([(0, 2, 0.44), (1, 3, 0.44)]) == {0: 0.44, 1: 0.44}


def test_rank_tie_band_is_load_bearing_on_the_validator_side():
    """同 severity、C 相差 0.01（带内）⟹ 按 `fault_mode` 决序；把带拉开到 0.02 ⟹ 同一份
    产物必须翻红。两半必须都在，否则"带存在"只是一句散文。

    这正是 A-116 ① 记的那类分歧：原始 C 0.5004/0.4949 都在同一 2 位格附近，引擎按未取整值
    与校验器按两位值能分出两种序。带上带之后两侧读同一把尺子，分歧不再产生。"""
    diag = _example()
    ff, res = _hyp(diag, FEEDFORWARD), _hyp(diag, RESONANCE)
    ff["severity"] = res["severity"] = 2
    # 带内：前馈 0.49 与谐振 0.50 算并列 ⟹ fault_mode 决序（electrical < mechanical），
    # 声明的序也写成 fault_mode 序 ⟹ 绿。
    ff["confidence"], res["confidence"] = 0.49, 0.50
    ff["rank"], res["rank"] = 1, 2
    checks = _rank_checks(diag)
    assert checks["C3-R20-rank-monotonic"][0], checks["C3-R20-rank-monotonic"][1]
    assert checks["C3-R20-primary-is-rank1"][0]  # 带内头条是 fault_mode 小的前馈那条
    ff["confidence"] = 0.48  # 拉开到 0.02 ⟹ 出带，C 说了算，同一份序就成了错的
    checks = _rank_checks(diag)
    assert not checks["C3-R20-rank-monotonic"][0], checks["C3-R20-rank-monotonic"][1]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
