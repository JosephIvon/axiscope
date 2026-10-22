"""A-105：接入层的列间恒等式核对 —— 算出来的列不是第二次测量。

正向跑在 Export10_244531 的门控切片上（本样本 8 条位置列里只有 5 条是独立测量，
A-105 ⑤ 要求的就是这个落档数）；负向用合成列构造「关系确实在，但文档没声明方向」
的情形，证明归因门真的在拦而不是写在注释里（KB0 §6 检查 22）。

    python -m pytest tests/test_identity_scan.py -q
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from axiscope import c1, features, mapping        # noqa: E402
from axiscope.__main__ import run as cli_run      # noqa: E402
from axiscope.twincat import read_scope           # noqa: E402

RAW = os.path.join(ROOT, "data", "raw", "Export10_244531.csv")


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    pack_dir = str(tmp_path_factory.mktemp("ident") / "Export10_244531")
    cli_run(RAW, pack_dir)
    with open(os.path.join(pack_dir, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    with open(os.path.join(pack_dir, "features.json"), encoding="utf-8") as fh:
        return {"meta": meta, "feats": json.load(fh)}


@pytest.fixture(scope="module")
def identity():
    _, ingest = c1.build_meta(read_scope(RAW), sample_id="Export10_244531")
    return ingest["identity"]


# ---------------------------------------------------------------- A-105 ①：核对与归因

def test_only_documented_computed_columns_get_a_derived_label(identity):
    """①：恒等式本身不指认方向，只有 KB2 §4.10 声明过的列才允许贴派生标签。"""
    assert sorted(d["column"] for d in identity["derived"]) == \
        ["dPosition_diff", "dVelocity_diff"]
    for d in identity["derived"]:
        assert d["max_abs_residual"] <= d["tolerance"], "被判派生的列必须过它自己那行的容差"
        assert sorted(d["basis"]) == sorted(mapping.DECLARED_COMPUTED[d["column"]])


def test_identity_directions_are_one_constraint_not_three(identity):
    """同一恒等式的三个书写方向是一条约束：`n_relations` 数关系，不数写法。

    旧实现按「每列取最佳关系」记账，把 `dPosition_test` 与自己原料的关系当成三条，
    于是 9 列被判派生、独立位置测量剩 4 —— 比 A-105 想防的漏洞更糟。
    """
    assert identity["n_relations"] == 3
    assert identity["n_derived"] == 2
    assert identity["n_unattributed"] == 1


def test_undocumented_relation_is_counted_but_not_attributed(identity):
    """力族那条关系：约束是真的（残差贴零），方向无据 ⟹ 只扣自由度、不贴标签。"""
    force = [c for c in identity["unattributed_columns"] if c == ["dForce_diff",
                                                                  "dForce_load", "dForce_test"]]
    assert len(force) == 1
    labelled = {d["column"] for d in identity["derived"]}
    assert not labelled & {"dForce_diff", "dForce_load", "dForce_test"}


# ---------------------------------------------------------------- A-105 ③：计数口径

def test_rowwise_identical_twins_drop_the_command_side(identity):
    assert sorted(identity["duplicate_dropped"]) == [
        "dPosition_load_tar", "dPosition_test_tar", "dVelocity_load_tar"]
    assert len(identity["duplicates"]) == identity["n_duplicate_groups"] == 3


def test_independent_position_columns_are_exactly_five(identity):
    """A-105 ⑤：8 条位置列去掉 1 派生 + 2 全等孪生 ⟹ 5 条独立测量，逐名列档。"""
    assert len(identity["position_columns_seen"]) == 8
    assert sorted(identity["independent_position_columns"]) == sorted([
        "dPosition_asco", "dPosition_asco_enc", "dPosition_load",
        "dPosition_lsv_enc", "dPosition_test"])
    assert identity["n_independent_position"] == 5
    assert identity["n_unattributed_among_position"] == 0


def test_constant_columns_are_registered_separately(identity):
    """常数列既不是测量也不是派生列，但它同样会让独立计数虚增（KB2 §517 互证）。"""
    assert sorted(identity["constants"]) == ["dForceSensorNo", "dForce_tar"]


def test_extras_carry_derived_from(identity, pack):
    """①的载体义务：`extras[].derived_from` 必须由核对填上，不是空字段。"""
    extras = pack["meta"]["extra_channels"]
    assert sorted(extras["dPosition_diff"]["derived_from"]) == ["dPosition_load",
                                                                "dPosition_test"]
    assert extras["dPosition_lsv_enc"]["derived_from"] is None


# ---------------------------------------------------------------- A-105 ④：没核对就没有资格

def test_audit_and_features_give_the_same_answer(pack):
    """C2 是 C1 摘要的镜像：两处对「核对做没做」必须逐键同值。"""
    audit = pack["meta"]["audit"]["identity_check"]
    mirror = pack["feats"]["feedback_integrity"]["identity_check"]
    assert sorted(mirror) == sorted(c1.AUDIT_IDENTITY_KEYS)
    assert mirror == audit


def test_second_feedback_survives_only_when_the_scan_ran(pack):
    fi = pack["feats"]["feedback_integrity"]
    assert fi["identity_check"]["performed"] is True
    assert fi["second_feedback_available"] is True


def test_unchecked_summary_forbids_an_optimistic_count(pack):
    """performed=false 却填了 second_feedback_available ⟹ 自检必须拒（A-105 ④）。

    翻转 `performed` 之后包就换了形态：`identity_check.reason` 不再属规则 2 的合法 null
    （豁免只在 `performed = true` 时成立），而 `second_feedback_available` 转为 null 也要
    有自己的 `unavailable` 行——两处都按 C2 规则 2 补齐，让本例测的是 A-105 ④ 而不是记账。
    """
    bad = json.loads(json.dumps(pack["feats"]))
    bad["feedback_integrity"]["identity_check"]["performed"] = False
    bad["feedback_integrity"]["identity_check"]["reason"] = "注入形态：数值列 < 3（A-105 ④）"
    bad["feedback_integrity"]["second_feedback_available"] = True
    with pytest.raises(features.FeatureError, match="A-105 ④"):
        features.check_self_consistency(bad, pack["meta"])
    ok = json.loads(json.dumps(pack["feats"]))
    ok["feedback_integrity"]["identity_check"]["performed"] = False
    ok["feedback_integrity"]["identity_check"]["reason"] = "注入形态：数值列 < 3（A-105 ④）"
    ok["feedback_integrity"]["second_feedback_available"] = None
    ok["unavailable"].append({"feature": "feedback_integrity.second_feedback_available",
                              "reason": "注入形态：performed = false ⟹ 该计数无资格存在（A-105 ④）"})
    features.check_self_consistency(ok, pack["meta"])


def test_scan_refuses_when_rows_are_too_few_to_solve():
    series = {f"x{i}": [float(r + i) for r in range(20)] for i in range(6)}
    out = c1._identity_scan(series, finding_table=[])
    assert out["performed"] is False and out["n_independent_position"] is None
    assert "A-105 ④" in out["reason"]


# ---------------------------------------------------------------- 配对与方向的正反例

def test_pairs_containing_a_derived_column_are_dropped():
    """②：派生列进配对就是给同一路信号记两票 ⟹ 整对剔除并留痕。"""
    _, ingest = c1.build_meta(read_scope(RAW), sample_id="Export10_244531")
    s = ingest["series"]
    table: list[dict] = []
    out = c1._pairwise_findings(s, [("dPosition_test", "dPosition_diff")], table,
                                not_independent={"dPosition_diff"})
    assert out == []
    assert table[0]["kind"] == "pair_excluded_by_identity"
    assert table[0]["excluded"] == "dPosition_diff"


def _synthetic(rows: int = 400):
    base = [float(r) * (1.0 + 1e-3 * (r % 7)) for r in range(rows)]
    other = [float(r % 11) * 3.0 - 5.0 + (r // 3) for r in range(rows)]
    combo = [2.0 * a - 0.5 * b + 1.25 for a, b in zip(base, other)]
    return {"xSpeed": base, "xTorque": other, "xSlip": combo,
            "xRaw": [a + 2.0 * b for a, b in zip(base, other)]}


def test_direction_needs_a_documentation_license():
    """同一组数据：没有声明 ⟹ 一条派生列都判不出；有声明 ⟹ 只判得出被声明的那一列。

    四列落在「两条真测量 + 常数」张成的三维空间里 ⟹ 三元组关系共 C(4,3)=4 条，全部实测成立；
    归因表为空时四条都只能记 `linear_dependency_unattributed`——关系是数据给的，方向不是。
    """
    series = _synthetic()
    out = c1._identity_scan(series, finding_table=[])
    assert out["derived"] == []
    assert out["n_relations"] == 4
    assert out["n_unattributed"] == 4
    assert sorted(out["unattributed_columns"]) == [
        ["xRaw", "xSlip", "xSpeed"], ["xRaw", "xSlip", "xTorque"],
        ["xRaw", "xSpeed", "xTorque"], ["xSlip", "xSpeed", "xTorque"]]
    assert out["n_independent_position"] == 0   # 与位置族无关的合成列不进出数

    with monkeypatched_declared({"xSlip": ("xSpeed", "xTorque")}):
        hit = c1._identity_scan(series, finding_table=[])
    d = [x for x in hit["derived"] if x["column"] == "xSlip"]
    assert len(d) == 1
    assert hit["n_derived"] == 1
    assert hit["n_unattributed"] == 3
    assert d[0]["coefficients"][0] == pytest.approx(2.0, rel=1e-9)
    assert d[0]["coefficients"][1] == pytest.approx(-0.5, rel=1e-9)
    assert d[0]["gamma"] == pytest.approx(1.25, rel=1e-9, abs=1e-9)
    assert d[0]["max_abs_residual"] <= d[0]["tolerance"]


class monkeypatched_declared:
    """临时改 `mapping.DECLARED_COMPUTED`：归因表的来源是 KB2 §4.10，测试不许永久改它。"""

    def __init__(self, table):
        self.table = table

    def __enter__(self):
        self.saved = dict(mapping.DECLARED_COMPUTED)
        mapping.DECLARED_COMPUTED.clear()
        mapping.DECLARED_COMPUTED.update(self.table)

    def __exit__(self, *exc):
        mapping.DECLARED_COMPUTED.clear()
        mapping.DECLARED_COMPUTED.update(self.saved)
