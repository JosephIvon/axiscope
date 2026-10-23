"""垂直切片 #1 的端到端测试。

正向：真样本走完 KB2 §8 → C1 → C2 → HTML，§8.3 全部断言通过。
负向：每条「本检查能抓 X 类缺陷」都必须有注入样本证明它真的报错（KB0 §6 检查 22：
断言在跑 ≠ 断言能抓）。负向测试失败 ⟹ 对应断言对自己声称保护的那件事零证明力，
按 A-88 首段处理。

    python -m pytest tests/test_slice.py -q
"""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import sys

import pytest


# 原始数据按 A-131 口径不入库；缺件时本文件整份 loud SKIP
# （口径见 tests/conftest.py；跳过 ≠ 通过，原因会写在 skip 理由里）
REQUIRES_DATA = ("data/raw/Export10_244531.csv",)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from axiscope import assertions as asrt          # noqa: E402
from axiscope import c1, features                 # noqa: E402
from axiscope.__main__ import run as cli_run      # noqa: E402
from axiscope.twincat import read_scope           # noqa: E402

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "raw", "Export10_244531.csv")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("slice")
    pack_dir = str(out / "Export10_244531")
    rc = cli_run(RAW, pack_dir)
    meta, feats = asrt.load_pack(pack_dir)
    table = read_scope(RAW)
    _, ingest = c1.build_meta(table, sample_id="Export10_244531")
    ingest["sha256"] = "test"
    return {"rc": rc, "pack_dir": pack_dir, "meta": meta, "feats": feats,
            "ingest": ingest, "n_columns": table.n_columns}


def _results(built, meta=None, feats=None, pack_dir=None):
    rows = asrt.run(meta or built["meta"], feats or built["feats"], built["ingest"],
                    pack_dir or built["pack_dir"], {"n_columns": built["n_columns"]})
    return {name: (ok, detail) for name, ok, detail in rows}


# --------------------------------------------------------------------------
# 正向
# --------------------------------------------------------------------------

def test_cli_exits_zero(built):
    assert built["rc"] == 0


def test_all_end_to_end_assertions_pass(built):
    failed = [n for n, (ok, _) in _results(built).items() if not ok]
    assert not failed, f"失败的断言：{failed}"


def test_pack_artifacts_exist(built):
    for name in ("meta.json", "features.json", "waveform.tsv", "report.html"):
        assert os.path.isfile(os.path.join(built["pack_dir"], name)), name


def test_report_html_is_self_contained(built):
    html = io.open(os.path.join(built["pack_dir"], "report.html"), encoding="utf-8").read()
    assert html.lstrip().startswith("<")
    assert "<script src=" not in html and "<link rel=\"stylesheet\"" not in html
    assert "Versuchsstand" not in html and "141.58." not in html


def test_diagnosis_is_wired_into_the_report(built):
    """C3 接入后：CLI 必须落 diagnosis.json、契约校验零失败、报告第八节把缺席键印出来。"""
    diag = json.load(io.open(os.path.join(built["pack_dir"], "diagnosis.json"), encoding="utf-8"))
    assert diag["schema"] == "axiscope.diagnosis/1"
    assert diag["safety"]["writes_to_device"] is False
    assert diag["safety"]["requires_human_approval"] is True
    assert all(c["passed"] for c in diag["contract_checks"]), \
        [c["check_id"] for c in diag["contract_checks"] if not c["passed"]]
    html = io.open(os.path.join(built["pack_dir"], "report.html"), encoding="utf-8").read()
    assert "<h2>八、C3 归因" in html
    assert "<h2>九、必须随报告一起读的限定</h2>" in html
    for row in diag["differential"]["not_evaluable"]:
        assert f"<code>{row['blocked_by']}</code>" in html, row["blocked_by"]


# --------------------------------------------------------------------------
# 负向：触发门控（KB3 纪律 8 / KB2 §8.3）
# --------------------------------------------------------------------------

def test_n_samples_mismatch_with_gate_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    meta["quality"]["n_samples"] += 7
    ok, detail = _results(built, meta=meta)["quality.n_samples == len(wave) == 触发门控后行数"]
    assert ok is False
    assert "+7" in detail or "门控保留" in detail


def test_gate_applied_is_not_optional(built):
    """未过滤触发的母本行数必须大于门控后行数——否则纪律 8 的门根本没跑。"""
    n_gate = built["meta"]["provenance"]["trigger_gate"]["rows_kept"]
    assert n_gate < built["meta"]["provenance"]["n_rows_raw"]


# --------------------------------------------------------------------------
# 负向：频带门禁与 blocked_rules（A-79）
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rule", ["R-03", "R-04"])
def test_dropping_required_blocked_rule_is_caught(built, rule):
    feats = copy.deepcopy(built["feats"])
    feats["freq_limits"]["blocked_rules"] = [
        b for b in feats["freq_limits"]["blocked_rules"] if not b.startswith(rule)]
    ok, _ = _results(built, feats=feats)["blocked_rules ⊇ {R : band⊥ > nyquist}"]
    assert ok is False


def test_orphan_blocked_rule_without_unavailable_row_is_caught(built):
    feats = copy.deepcopy(built["feats"])
    feats["freq_limits"]["blocked_rules"].append("R-13")
    ok, detail = _results(built, feats=feats)["blocked_rules 与 unavailable 的 rule/branch 一一对账（A-79）"]
    assert ok is False and "无对应 unavailable" in detail


def test_unavailable_rule_row_without_blocked_rule_is_caught(built):
    feats = copy.deepcopy(built["feats"])
    feats["unavailable"].append({"feature": "spectral.cur_q.dominant_freq_hz",
                                 "rule": "R-14", "branch": "hf",
                                 "reason": "注入的孤儿行"})
    ok, detail = _results(built, feats=feats)["blocked_rules 与 unavailable 的 rule/branch 一一对账（A-79）"]
    assert ok is False and "无对应 blocked_rules" in detail


def test_branch_granularity_is_respected(built):
    """R-11 只锁支路：整条 R-11 不得进 blocked_rules。"""
    blocked = built["feats"]["freq_limits"]["blocked_rules"]
    assert "R-11#switching_freq" in blocked
    assert "R-11" not in blocked


# --------------------------------------------------------------------------
# 负向：通道不丢弃（KB2 §3.6）
# --------------------------------------------------------------------------

def test_dropping_a_channel_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    victim = next(iter(meta["extra_channels"]))
    del meta["extra_channels"][victim]
    ok, detail = _results(built, meta=meta)["N_mapped + N_extra == N_header（无通道既不映射也不入 extra）"]
    assert ok is False and str(built["n_columns"]) in detail


def test_out_of_vocabulary_channel_name_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    head = ["t"] + ["pos_fb_typo"] + list(meta["present_channels"])
    body = "\n".join("\t".join(["0.0"] * len(head)) for _ in range(2))
    with open(os.path.join(built["pack_dir"], "waveform.tsv"), "w", encoding="utf-8") as fh:
        fh.write("\t".join(head) + "\n" + body + "\n")
    try:
        ok, detail = _results(built, meta=meta)["canonical 列名 ⊆ C1 词表"]
        assert ok is False and "pos_fb_typo" in detail
    finally:
        _rewrite_wave(built)


def _rewrite_wave(built):
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_golden_wave.tsv")
    shutil.copyfile(src, os.path.join(built["pack_dir"], "waveform.tsv"))


@pytest.fixture(scope="module", autouse=True)
def _golden_wave(built):
    """先存一份未被负向测试改坏的 waveform.tsv，供还原。"""
    src = os.path.join(built["pack_dir"], "waveform.tsv")
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_golden_wave.tsv")
    shutil.copyfile(src, dst)
    yield dst
    if os.path.exists(dst):
        os.remove(dst)


# --------------------------------------------------------------------------
# 负向：包内数值 ≡ 母本（回算）
# --------------------------------------------------------------------------

def test_perturbing_one_waveform_value_is_caught(built):
    path = os.path.join(built["pack_dir"], "waveform.tsv")
    rows = io.open(path, encoding="utf-8").read().split("\n")
    cells = rows[3].split("\t")
    cells[2] = repr(float(cells[2]) + 1.0)
    rows[3] = "\t".join(cells)
    io.open(path, "w", encoding="utf-8").write("\n".join(rows))
    try:
        ok, detail = _results(built)["包内数值 ≡ 母本数值（门控后逐点回算，|Δ| == 0）"]
        assert ok is False and "max|Δ|" in detail
    finally:
        _rewrite_wave(built)


def test_applying_a_sign_flip_instead_of_declaring_it_is_caught(built):
    """把 sign 改成 -1 而不改包内数值 ⟹ 回算立即失败：方向修正必须落到数据上。"""
    meta = copy.deepcopy(built["meta"])
    victim = next(n for n, c in meta["channels"].items() if c["offset"] == 0)
    meta["channels"][victim]["sign"] = -1
    ok, _ = _results(built, meta=meta)["包内数值 ≡ 母本数值（门控后逐点回算，|Δ| == 0）"]
    assert ok is False


# --------------------------------------------------------------------------
# 负向：脱敏与署名（KB2 §六）
# --------------------------------------------------------------------------

def test_leaked_host_path_is_caught(built):
    path = os.path.join(built["pack_dir"], "meta.json")
    blob = io.open(path, encoding="utf-8").read()
    io.open(path, "w", encoding="utf-8").write(
        blob.replace('"units_are"', '"note": "C:\\\\Versuchsstand\\\\log", "units_are"', 1))
    try:
        ok, detail = _results(built)["包内不含主机路径 / ADS NetID（KB2 §6.3）"]
        assert ok is False and "Versuchsstand" in detail
    finally:
        io.open(path, "w", encoding="utf-8").write(blob)


def test_leaked_ads_netid_is_caught(built):
    path = os.path.join(built["pack_dir"], "meta.json")
    blob = io.open(path, encoding="utf-8").read()
    io.open(path, "w", encoding="utf-8").write(blob.replace('"units_are"', '"net": "[REDACTED_ADS_NETID]", "units_are"', 1))
    try:
        ok, detail = _results(built)["包内不含主机路径 / ADS NetID（KB2 §6.3）"]
        assert ok is False and "141.58." in detail
    finally:
        io.open(path, "w", encoding="utf-8").write(blob)


def test_citation_doi_survives_redaction(built):
    cite = built["meta"]["provenance"]["citation"]
    assert cite["doi"] == "10.18419/DARUS-3600"
    assert cite["license"] == "CC BY 4.0"
    assert "Reichenbach" in cite["author"]


# --------------------------------------------------------------------------
# 负向：fe 派生分支不得空转
# --------------------------------------------------------------------------

def test_fe_present_without_cmd_and_fb_is_caught(built):
    """本样本 fe 不在 present ⟹ 该断言恒真；构造一个 fe 在列而 pos_cmd/pos_fb 不在列的包，
    证明它不是一条永远为真的装饰断言。"""
    meta = copy.deepcopy(built["meta"])
    meta["present_channels"] = list(meta["present_channels"]) + ["fe"]
    meta["channels"]["fe"] = {"raw_column": "dPosition_diff", "sign": 1, "offset": 0.0,
                              "derived": True, "role": "mapped", "time_base_ref": None}
    ok, detail = _results(built, meta=meta)["fe ≡ pos_cmd - pos_fb"]
    assert ok is False and "pos_cmd" in detail


# --------------------------------------------------------------------------
# 负向：A-96 多栅格
# --------------------------------------------------------------------------

def test_two_primary_time_bases_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    meta["time_bases"].append(dict(meta["time_bases"][0], id="tb1"))
    ok, _ = _results(built, meta=meta)["time_bases 中 primary 恰一条且被指名"]
    assert ok is False


def test_event_grid_cannot_be_primary_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    meta["time_bases"].append({"id": "ev0", "role": "event", "sample_rate_hz": None,
                               "time_origin": "sample_index", "note": "注入"})
    meta["primary_time_base"] = "ev0"
    ok, _ = _results(built, meta=meta)["事件栅格不得作主栅格"]
    assert ok is False


def test_dangling_time_base_ref_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    meta["channels"][next(iter(meta["channels"]))]["time_base_ref"] = "tb9"
    ok, detail = _results(built, meta=meta)["channels[].time_base_ref ∈ time_bases[].id 或 null（null=继承 primary）"]
    assert ok is False and "tb9" in detail


def test_sample_rate_anchor_drift_is_caught(built):
    meta = copy.deepcopy(built["meta"])
    prim = next(tb for tb in meta["time_bases"] if tb["role"] == "primary")
    prim["sample_rate_hz"] *= 1.001
    ok, _ = _results(built, meta=meta)["sample_rate_hz == time_bases[primary].sample_rate_hz（向后兼容锚点自洽）"]
    assert ok is False


# --------------------------------------------------------------------------
# 负向：C2 自检（规则 8 / 12 / 14，A-82 方向）
# --------------------------------------------------------------------------

def _drop_unavailable(feats, prefix):
    feats["unavailable"] = [u for u in feats["unavailable"]
                            if not u["feature"].startswith(prefix)]
    return feats


def _drop_causal_rows(feats):
    """只摘因果三元组自己的行（`sync.*` 与 `alignment_residual_ms`），因为这几路马上要被填上值，
    规则 14 的互斥检查会先撞它们。

    **不**顺手摘 `event_context` 其余计数行：那些字段仍为 null，行必须在场
    （C2 规则 2 的逐路口径由 `features.check_null_accounting()` 机器判，抹掉别的行
    就是抹掉别的账）。
    """
    for prefix in ("event_context.sync.", "event_context.alignment_residual_ms"):
        _drop_unavailable(feats, prefix)
    return feats


def _expect_feature_error(built, feats, needle):
    with pytest.raises(features.FeatureError) as ei:
        features.check_self_consistency(feats, built["meta"])
    assert needle in str(ei.value), f"期望错误含 {needle!r}，实得 {ei.value}"


def test_value_and_unavailable_row_together_is_caught(built):
    feats = copy.deepcopy(built["feats"])
    feats["quality_ref"]["quantization_step_counts"] = 1e-6
    _expect_feature_error(built, feats, "互斥失败")


def test_non_null_in_absent_channel_is_caught(built):
    feats = copy.deepcopy(built["feats"])
    feats["present_channels"] = feats["present_channels"] + ["temp"]
    feats["global"]["thermal_fe_correlation_r"] = 0.71
    _expect_feature_error(built, feats, "互斥失败")


def test_fs_drift_between_freq_limits_and_top_level_is_caught(built):
    feats = copy.deepcopy(built["feats"])
    feats["freq_limits"]["fs_hz"] = 2000.0
    _expect_feature_error(built, feats, "不自洽")


def test_reliable_band_must_be_nyquist_over_1_25(built):
    feats = copy.deepcopy(built["feats"])
    feats["freq_limits"]["reliable_band_hz"] = feats["freq_limits"]["nyquist_hz"] * 0.99
    _expect_feature_error(built, feats, "reliable_band_hz")


def test_empty_spectral_preview_with_nonnull_peak_is_caught(built):
    feats = copy.deepcopy(built["feats"])
    feats["spectral"]["vel_fb"]["freq_hz"] = []
    feats["spectral"]["vel_fb"]["psd"] = []
    feats["spectral"]["vel_fb"]["dominant_freq_hz"] = 120.0
    _expect_feature_error(built, feats, "预览为空")


def test_a82_direction_large_residual_forbids_causal_claim(built):
    """A-82：残差**大**于不确定度时必须禁止因果；旧 A-50 的方向被显式作废。"""
    feats = _drop_causal_rows(copy.deepcopy(built["feats"]))
    feats["event_context"].update({
        "available": True, "sync": {"method": "trigger_edge", "verified": True,
                                    "uncertainty_ms": 0.5},
        "alignment_residual_ms": 4.0, "causal_claims_permitted": True})
    _expect_feature_error(built, feats, "causal_claims_permitted")


def test_small_residual_does_permit_causal_claim(built):
    feats = _drop_causal_rows(copy.deepcopy(built["feats"]))
    feats["event_context"].update({
        "available": True, "sync": {"method": "trigger_edge", "verified": True,
                                    "uncertainty_ms": 0.5},
        "alignment_residual_ms": 0.25, "causal_claims_permitted": True})
    features.check_self_consistency(feats, built["meta"])


def test_missing_residual_cannot_enable_causal_claims(built):
    """缺残差不是残差合格：available=false 时 causal_claims_permitted 必须为 false。"""
    feats = copy.deepcopy(built["feats"])
    feats["event_context"]["causal_claims_permitted"] = True
    _expect_feature_error(built, feats, "causal_claims_permitted")


def test_unverified_sync_cannot_enable_causal_claims(built):
    feats = _drop_causal_rows(copy.deepcopy(built["feats"]))
    feats["event_context"].update({
        "available": True, "sync": {"method": "unknown", "verified": False,
                                    "uncertainty_ms": 5.0},
        "alignment_residual_ms": 0.1, "causal_claims_permitted": True})
    _expect_feature_error(built, feats, "causal_claims_permitted")


def test_engine_product_books_every_null_path(built):
    """正向基线：引擎自己的产物上 60 个 null 叶子全部有账（或属规则 2 点名的合法 null）。"""
    nulls = [p for p, v in features._feature_paths(built["feats"]) if v is None]
    assert nulls, "本切片样本上确有 null 路径，否则这条正向例没有检测力"
    features.check_null_accounting(built["feats"])


def test_dropping_a_required_row_turns_the_check_red(built):
    """负向（检查 22）：抹掉一条**应有**的行 ⟹ 逐路记账必须翻红并指名那条路径。

    这正是主线程四处产物里实测到的缺陷形态：`global.cur_q_saturation_ratio` 值为 null，
    而账上没有它——C3 的 CAP-5 拿 `unavailable[].feature` 集合逐字比证据路径，少一行
    ⟹ 该特征被当成"可用"放行进假设。
    """
    feats = copy.deepcopy(built["feats"])
    before = [u for u in feats["unavailable"]
              if u["feature"] == "global.cur_q_saturation_ratio"]
    assert before, "基线里这一行必须在，否则本例测的是别的东西"
    feats["unavailable"] = [u for u in feats["unavailable"]
                            if u["feature"] != "global.cur_q_saturation_ratio"]
    _expect_feature_error(built, feats, "global.cur_q_saturation_ratio")


def test_short_name_row_turns_the_check_red(built):
    """负向（检查 22）：把行的 `global.` 前缀去掉（例 B 原来的写法）⟹ 必须报错并指名该行。"""
    feats = copy.deepcopy(built["feats"])
    row = next(u for u in feats["unavailable"] if u["feature"] == "global.cur_q_rms_a")
    row["feature"] = "cur_q_rms_a"
    _expect_feature_error(built, feats, "点分全路径")


def test_identity_reason_exemption_is_conditional_on_performed(built):
    """合法 null 清单①的边界：豁免只在 `performed = true` 时成立。

    翻成 `false` 而 `reason` 仍为 null ⟹ 同一行必须变红（"核对没跑成"却不写为什么，
    正是 A-105 ④ 要求登记的形态），免得豁免清单被读成"这条路径永远不用记账"。
    """
    feats = copy.deepcopy(built["feats"])
    ic = feats["feedback_integrity"]["identity_check"]
    assert ic["performed"] is True and ic["reason"] is None, "基线：performed=true 时 reason 合法为 null"
    features.check_null_accounting(feats)          # 基线不报
    ic["performed"] = False
    _expect_feature_error(built, feats, "feedback_integrity.identity_check.reason")


def test_bandwidth_confidence_cap_is_respected(built):
    feats = copy.deepcopy(built["feats"])
    feats["bandwidth"]["confidence"] = 0.85
    _expect_feature_error(built, feats, "confidence")


def test_present_channels_must_match_c1(built):
    feats = copy.deepcopy(built["feats"])
    feats["present_channels"] = [c for c in feats["present_channels"] if c != "torque"]
    _expect_feature_error(built, feats, "present_channels")


def test_zero_coverage_requires_empty_array(built):
    feats = _drop_unavailable(copy.deepcopy(built["feats"]), "step_response")
    feats["segment_coverage"]["settling"] = 0
    feats["step_response"] = [{"segment_id": 1, "overshoot_pct": 1.0}]
    _expect_feature_error(built, feats, "settling=0 却有 step_response")


def test_zero_probing_coverage_requires_empty_ripple(built):
    feats = _drop_unavailable(copy.deepcopy(built["feats"]), "ripple")
    feats["segment_coverage"]["probing"] = 0
    feats["ripple"]["probing"] = [{"segment_id": 3, "ripple_pp_counts": 1.6}]
    _expect_feature_error(built, feats, "probing=0 却有 ripple.probing")


# --------------------------------------------------------------------------
# 负向：读取器（表头定位 / KV 扫描终止 / 列序）
#
# 真实 Scope View CSV 的行布局是 (键, 值) 成对交替：键在偶数格、值在奇数格。
# 下面三例刻意照抄该布局，否则测的是我臆想的格式而不是厂商格式。
# --------------------------------------------------------------------------

def _scope_csv(names, kv, rows):
    """照抄真实布局：Name 行在前、KV 行紧随其后、数据行在空行之后。"""
    head = []
    for n in names:
        head += ["Name", n]
    lines = ["\t".join(head)]
    for key, val in (kv or []):
        cells = []
        for _ in names:
            cells += [key, val]
        lines.append("\t".join(cells))
    lines.append("")
    for i, vals in enumerate(rows):
        cells = []
        for v in vals:
            cells += [str(i), str(v)]
        lines.append("\t".join(cells))
    return "\r\n".join(lines) + "\r\n"


def test_reader_picks_widest_name_row_not_the_file_label(tmp_path):
    """文件级 'Name\\tMeasurement' 与通道级 'Name\\tch0...' 同名前缀，必须取列数最多的那行。"""
    path = tmp_path / "Scope.csv"
    path.write_text("Name\tMeasurement\r\n"
                    + _scope_csv(["ch0", "ch1"], [("SampleTime[ms]", "1.0")],
                                 [[11, 22], [33, 44]]), encoding="utf-8")
    table = read_scope(str(path))
    assert table.n_columns == 2
    assert [c.name for c in table.columns] == ["ch0", "ch1"]
    assert table.data["ch0"] == [11.0, 33.0]
    assert table.data["ch1"] == [22.0, 44.0]


def test_reader_terminates_kv_scan_at_data_rows(tmp_path):
    """数据行与 KV 行同宽时，靠「首格为数值」终止扫描——否则 1.8 万行会被当成表头。"""
    path = tmp_path / "Scope.csv"
    body = _scope_csv(["ch0", "ch1", "ch2"],
                      [("SampleTime[ms]", "1.0"), ("NetID", "140.1.1.1.1")],
                      [[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    path.write_text("Name\tMeasurement\r\n\r\n" + body, encoding="utf-8")
    table = read_scope(str(path))
    assert table.n_columns == 3
    assert table.n_rows_raw == 3
    assert table.n_rows_shape_mismatch == 0
    assert table.data["ch2"] == [3.0, 6.0, 9.0]
    assert table.sample_time_ms == 1.0
    assert table.columns[0].meta["NetID"] == "140.1.1.1.1"


def test_reader_uses_odd_column_indices(tmp_path):
    path = tmp_path / "Scope.csv"
    path.write_text(_scope_csv(["a", "b"], None, [[11, 22], [33, 44]]), encoding="utf-8")
    table = read_scope(str(path))
    assert table.column("a").col_index == 1
    assert table.column("b").col_index == 3
    assert table.data["a"] == [11.0, 33.0]
    assert table.data["b"] == [22.0, 44.0]


def test_reader_rejects_odd_width_header(tmp_path):
    path = tmp_path / "Scope.csv"
    path.write_text("Name\tMeasurement\r\nName\ta\tName\tb\tc\r\n\r\n0\t1\r\n", encoding="utf-8")
    with pytest.raises(Exception) as ei:
        read_scope(str(path))
    assert "奇数" in str(ei.value)


def test_reader_rejects_duplicate_channel_names(tmp_path):
    path = tmp_path / "Scope.csv"
    path.write_text(_scope_csv(["a", "a"], None, [[1, 2]]), encoding="utf-8")
    with pytest.raises(Exception) as ei:
        read_scope(str(path))
    assert "重复" in str(ei.value)


def test_reader_refuses_when_no_name_row(tmp_path):
    """宁可拒读，不得按猜测解析（KB2 §三）。"""
    path = tmp_path / "Scope.csv"
    path.write_text("File\tfoo.csv\r\n\r\n0\t1\r\n", encoding="utf-8")
    with pytest.raises(Exception) as ei:
        read_scope(str(path))
    assert "Name" in str(ei.value)


def test_shape_mismatch_rows_are_counted_not_guessed(tmp_path):
    body = _scope_csv(["a", "b"], None, [[1, 2], [3, 4]]) + "2\t9\r\n"
    path = tmp_path / "Scope.csv"
    path.write_text(body, encoding="utf-8")
    table = read_scope(str(path))
    assert table.n_rows_shape_mismatch == 1
    assert table.data["a"] == [1.0, 3.0]

# --------------------------------------------------------------------------
# 负向：audit.assumptions 的形状（#25 / C3 规则 19）
# --------------------------------------------------------------------------

def test_prose_assumption_row_without_anchor_is_caught(built):
    """散文行没有锚 ⟹ 报告引用不到它，也不可变废料。断言层必须翻红。"""
    name = "audit.assumptions 行形状与锚词表"
    assert all(isinstance(r, dict) and r["anchor"] for r in built["meta"]["audit"]["assumptions"])
    ok, _ = _results(built)[name]
    assert ok is True
    meta = copy.deepcopy(built["meta"])
    meta["audit"]["assumptions"][0] = "限流值没给，我们按额定电流兜底了"
    ok, _ = _results(built, meta=meta)[name]
    assert ok is False
