"""A-99 的四条落地：示例前提必须在 `inputs` 层可判定同构，且孪生快照不是装饰。

钉三件事：
1. `examples/c2_example_a_no_events.json` 与 `c2_example_a.json` 只差 event_context（孪生）；
2. 引擎在这两份夹具上的 primary **不同**——这正是 A-99 登记的互斥，现在它有了载体；
3. C3 示例点名的快照真实可解析，前提翻转会翻红（C3 规则 18）。
"""
from __future__ import annotations

import copy
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from axiscope import c3validate, engine  # noqa: E402

EXAMPLES = os.path.join(ROOT, "examples")
FIX = os.path.join(ROOT, "tests", "fixtures")
CASE_A_COUNTS = {"welch_segments": 8, "band_bins": 96}


def _ex(name):
    with io.open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return json.load(fh)


def _fix(name):
    with io.open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return json.load(fh)


def _example():
    """A-107 ③ 之后示例有两份（同一前提、两种假设数），规则 18 的核对对两份都要成立。"""
    return copy.deepcopy(_fix("c3_example_ranked_pair.json"))


def _example_single():
    return copy.deepcopy(_fix("c3_example_resonance_059.json"))


# ---------------------------------------------------------------- 孪生本体

def test_twin_differs_only_in_event_context():
    base, twin = _ex("c2_example_a.json"), _ex("c2_example_a_no_events.json")
    assert base["event_context"]["available"] is True
    assert twin["event_context"]["available"] is False
    b = copy.deepcopy(base)
    t = copy.deepcopy(twin)
    note = t["ref"].pop("note", None)
    assert isinstance(note, str) and "events.jsonl" in note
    b.pop("event_context")
    t.pop("event_context")
    assert b == t, "孪生只能差 event_context 一块；其余字段须与母本逐字段相同"


def test_twin_has_no_event_counts():
    """无事件 ⟹ 计数字段**不存在**，而不是填 0（填 0 会被规则读成「已核对且为零」）。"""
    ec = _ex("c2_example_a_no_events.json")["event_context"]
    assert set(ec) == {"available", "reason"}


# ---------------------------------------------------------------- 引擎侧的两个前提

def test_engine_on_twin_reproduces_contract_verdict():
    report = engine.analyze(_ex("c2_example_a_no_events.json"), sample_counts=CASE_A_COUNTS)
    assert report["verdict"]["primary"] == next(
        h["id"] for h in report["hypotheses"] if h["fault_mode"] == "mechanical_resonance")
    assert report["verdict"]["overall_confidence"] == 0.59
    keys = sorted({r["blocked_by"] for r in report["differential"]["not_evaluable"]})
    assert keys == ["absent_events_jsonl", "absent_temp_channel"]
    assert not [c for c in c3validate.validate(report) if not c.passed]


def test_engine_on_mother_snapshot_is_not_the_contract_case():
    """母本（有事件）走的是另一条线：软件族抢占 primary。两份示例因此必须换 case_id。"""
    report = engine.analyze(_ex("c2_example_a.json"), sample_counts=CASE_A_COUNTS)
    primary = next(h for h in report["hypotheses"] if h["id"] == report["verdict"]["primary"])
    assert primary["fault_mode"].startswith("software_induced_")
    assert report["verdict"]["overall_confidence"] != 0.59


# ---------------------------------------------------------------- C3 规则 18

def test_c3_example_snapshot_premises_resolve():
    """两份示例（E1 单假设 / E2 排序对）声明的是**同一个前提**——同一快照 `c2_example_a_no_events`，
    所以规则 18 的五项核对必须逐份都过（A-107 ③ 拆的是假设数，不是前提）。"""
    for diag in (_example(), _example_single()):
        checks = {c.check_id: c for c in c3validate.validate(diag)}
        for cid in ("C3-R18-name", "C3-R18-exists", "C3-R18-parse", "C3-R18-channels", "C3-R18-events"):
            assert cid in checks, f"缺 {cid}"
            assert checks[cid].passed, checks[cid].detail
        assert not [c for c in c3validate.validate(diag) if not c.passed], [
            (c.check_id, c.detail) for c in c3validate.validate(diag) if not c.passed]


def test_both_examples_declare_the_same_premise():
    """拆成两个 `case_id` 的代价是"两份材料悄悄分叉"，这里把前提层的等同性钉住：
    快照、通道、事件前提三处必须逐字段相同；不同的只有 `case_id` 与假设数（A-77 / A-99）。"""
    pair, single = _example(), _example_single()
    assert pair["case_id"] != single["case_id"]
    assert pair["inputs"] == single["inputs"]
    assert len(pair["hypotheses"]) == 2 and len(single["hypotheses"]) == 1


def test_r18_fails_when_snapshot_missing():
    diag = _example()
    diag["inputs"]["features_snapshot"] = "c2_example_a_that_does_not_exist"
    assert any(c.check_id == "C3-R18-exists" and not c.passed
               for c in c3validate.validate(diag))


def test_r18_rejects_path_escape():
    diag = _example()
    diag["inputs"]["features_snapshot"] = "../src/axiscope/engine"
    assert any(c.check_id == "C3-R18-name" and not c.passed
               for c in c3validate.validate(diag))


def test_r18_catches_premise_flip():
    """把示例声明的前提翻成"有事件"，而快照仍是无事件孪生 ⟹ 必须翻红，不许靠叙述蒙过。"""
    diag = _example()
    diag["inputs"]["event_context_available"] = True
    assert any(c.check_id == "C3-R18-events" and not c.passed
               for c in c3validate.validate(diag))


def test_r18_catches_channel_mismatch():
    diag = _example()
    diag["inputs"]["present_channels"] = ["pos_cmd", "pos_fb", "fe", "cur_q", "vel_fb"]
    assert any(c.check_id == "C3-R18-channels" and not c.passed
               for c in c3validate.validate(diag))
