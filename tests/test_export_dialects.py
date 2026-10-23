"""导出方言分派器的正向 + 负向用例（KB0 §6 检查 22：断言在跑 ≠ 断言能抓）。

每条方言都有一组「这个检查声称能自曝哪类缺陷」的负向用例：把该方言的判别特征
（ISO 时间戳 / `X (ms)` 列名 / 欧洲小数逗号 / 段名续行 / 非数值单元 / 侧车佐证）
**故意破坏**，断言真的抛 `ScopeFormatError`。负向用例失败 ⟹ 对应判据对自己声称拦住的
那件事零证明力。

    python -m pytest tests/test_export_dialects.py -q
"""
from __future__ import annotations

import io
import math
import os
import shutil
import sys

import pytest


# 原始数据按 A-131 口径不入库；缺件时本文件整份 loud SKIP
# （口径见 tests/conftest.py；跳过 ≠ 通过，原因会写在 skip 理由里）
REQUIRES_DATA = (
    "data/raw/Export10_244531.csv",
    "data/raw/参数分析仪波形_PMU_1t1r_CVSV导出样例.csv",
    "data/incoming/2563_LDD_Transfer_function_Force_controlled.csv",
    "data/incoming/6114_lsmc.csv",
    "data/incoming/6114_ObserverTestSet.tab",
    "data/incoming/current-hunt/3900_const_vel_110.tab",
)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from axiscope import c1, features                      # noqa: E402
from axiscope.twincat import ScopeFormatError, read_scope, timebase_stats  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D1 = os.path.join(ROOT, "data", "raw", "Export10_244531.csv")
D2 = os.path.join(ROOT, "data", "incoming", "6114_lsmc.csv")
D3 = os.path.join(ROOT, "data", "incoming", "current-hunt", "3900_const_vel_110.tab")
D4 = os.path.join(ROOT, "data", "incoming", "6114_ObserverTestSet.tab")
D5 = os.path.join(ROOT, "data", "incoming", "2563_LDD_Transfer_function_Force_controlled.csv")
D6 = os.path.join(ROOT, "data", "raw", "参数分析仪波形_PMU_1t1r_CVSV导出样例.csv")


# ------------------------------------------------------------------ 小工具

def _stage(src: str, tmp_path, name: str = "x.csv", sidecar: bool = False) -> str:
    p = tmp_path / name
    shutil.copyfile(src, str(p))
    if sidecar and os.path.exists(src + ".source.txt"):
        shutil.copyfile(src + ".source.txt", str(p) + ".source.txt")
    return str(p)


def _rewrite(src: str, tmp_path, fn, name: str = "x.csv", sidecar: bool = False) -> str:
    """按行改写一份副本（换行符原样保留），可一并带上侧车。"""
    text = io.open(src, encoding="utf-8").read()
    lines = text.split("\r\n") if "\r\n" in text[:4096] else text.split("\n")
    lines = fn(lines)
    p = tmp_path / name
    io.open(str(p), "w", encoding="utf-8", newline="").write("\r\n".join(lines))
    if sidecar and os.path.exists(src + ".source.txt"):
        shutil.copyfile(src + ".source.txt", str(p) + ".source.txt")
    return str(p)


def _set_cell(line: str, col: int, value: str, delim: str = ",") -> str:
    cells = line.split(delim)
    cells[col] = value
    return delim.join(cells)


def _fs(table) -> float:
    return 1.0 / timebase_stats(table.sample_index, table.sample_time_ms)["dt_median_s"]


# ------------------------------------------------------------------ D1 回归

def test_d1_scope_view_path_is_untouched():
    """D1 的行为不能因加了分派器而变：仍是 Scope View、32 列、声明周期 1 ms、行序号索引。"""
    t = read_scope(D1)
    assert t.dialect == "twincat_scope_view"
    assert t.time_column is None and t.unit_source is None
    assert t.n_columns == 32
    assert t.sample_time_ms == 1.0
    assert t.sample_index[:3] == [0.0, 1.0, 2.0]
    meta, _ = c1.build_meta(t, sample_id="Export10_244531")
    assert meta["present_channels"] == ["vel_cmd", "vel_fb", "torque"]
    assert meta["sample_rate_hz"] == 1000.0
    assert meta["provenance"]["trigger_gate"]["channel"] == "bTrigger_Record"


# ------------------------------------------------------------------ D2

def test_d2_comma_iso8601_rowindex(tmp_path):
    t = read_scope(D2)
    assert t.dialect == "csv_iso8601_rowindex"
    assert t.time_column == "t" and t.time_col_source == "column_name"
    assert t.unit_source == "iso8601_text:epoch_seconds"
    assert t.n_rows_raw == 3000 and t.n_rows_shape_mismatch == 0
    assert t.n_columns == 49                       # 52 格 − 行号列 − t − id
    assert "" not in [c.name for c in t.columns] and "t" not in t.data and "id" not in t.data
    tb = timebase_stats(t.sample_index, t.sample_time_ms)
    assert tb["strictly_monotonic"] is True
    assert abs(_fs(t) - 1000.07) < 0.01
    assert t.sample_time_ms == 1.0                 # 毫秒→秒的换算载体，不是声明周期
    _generic_pack_ok(t, tmp_path / "d2")


def test_d2_rejects_corrupted_iso_timestamp(tmp_path):
    """破坏该方言的判别特征：把一行 ISO 时间戳换成非 ISO 文本 ⟹ 必须拒读，不得当等间隔。"""
    p = _rewrite(D2, tmp_path,
                 lambda ls: ls[:1] + [_set_cell(ls[500], 1, "2025/11/05 09:30:34.446")]
                 + ls[501:])
    with pytest.raises(ScopeFormatError) as ei:
        read_scope(p)
    assert "ISO-8601" in str(ei.value)


# ------------------------------------------------------------------ D3

def test_d3_tab_iso8601(tmp_path):
    t = read_scope(D3)
    assert t.dialect == "tsv_iso8601"
    assert t.time_column == "t" and t.unit_source == "iso8601_text:epoch_seconds"
    assert t.n_rows_raw == 2701 and t.n_columns == 40     # 42 格 − t − id
    tb = timebase_stats(t.sample_index, t.sample_time_ms)
    assert tb["strictly_monotonic"] is True
    assert abs(tb["dt_jitter_ratio"] - 0.0384) < 0.002   # 与 KB2 §4.12 R-3 登记的 0.038 同量
    _generic_pack_ok(t, tmp_path / "d3")


def test_d3_rejects_reversed_timestamp_order(tmp_path):
    """时间列身份已证实 ⟹ 非严格单调要判「时基非严格单调」，而不是退回等间隔。"""
    p = _rewrite(D3, tmp_path,
                 lambda ls: ls[:2] + [ls[1]] + ls[3:])   # 第 2 行复制第 1 行 ⟹ Δt = 0
    with pytest.raises(ScopeFormatError) as ei:
        read_scope(p)
    assert "非严格单调" in str(ei.value)


# ------------------------------------------------------------------ D4

def test_d4_without_time_column_is_refused():
    """无时间基就没有 fs：正确结局是带理由的拒收（KB0 §1 / KB2 §4.12 R-7）。"""
    with pytest.raises(ScopeFormatError) as ei:
        read_scope(D4)
    msg = str(ei.value)
    assert "该导出无时间列，无法确定采样率，按 C1 拒收" in msg
    assert "等间隔" in msg


def test_d4_never_promotes_an_increasing_channel_to_the_time_column(tmp_path):
    """把 `x_act` 改成严格递增 ⟹ 仍然拒收：R-7 明令「递增启发列」不配当时基。"""
    def bump(ls):
        out = list(ls)
        for i in range(1, len(out)):
            cells = out[i].split("\t")
            if len(cells) < 5:                       # 跳过末尾空行之类
                continue
            cells[4] = repr(i * 1e-3)
            out[i] = "\t".join(cells)
        return out
    p = _rewrite(D4, tmp_path, bump, name="x.tab")
    with pytest.raises(ScopeFormatError) as ei:
        read_scope(p)
    assert "无时间列" in str(ei.value)


# ------------------------------------------------------------------ D5

def test_d5_semicolon_european_decimal(tmp_path):
    t = read_scope(D5)
    assert t.dialect == "semicolon_european_decimal"
    assert t.time_column == "X (ms)" and t.unit_source == "column_name:ms"
    assert t.n_rows_raw == 2047 and t.n_columns == 2
    assert abs(_fs(t) - 16000.0) < 1e-6                # 步长 0.0625 ms
    assert abs(t.data["C0:Lineardirektantrieb.r77"][0] - 19.999996) < 1e-9
    assert abs(t.data["C0:Lineardirektantrieb.r77"][1] + 19.999996) < 1e-9
    assert t.file_meta["decimal_comma"] == "true"
    _generic_pack_ok(t, tmp_path / "d5")


def test_d5_rejects_file_without_the_unit_in_the_column_name(tmp_path):
    """把 `X (ms)` 改成 `X`（单位没了）：又没有侧车可佐证 ⟹ 必须拒读，不许默认按秒/毫秒。"""
    p = _rewrite(D5, tmp_path, lambda ls: ["X;" + ls[0].split(";", 1)[1]] + ls[1:],
                 name="y.csv")
    with pytest.raises(ScopeFormatError):
        read_scope(p)


def test_d5_rejects_comma_as_delimiter(tmp_path):
    """把 `;` 换成 `,` ⟹ 切分发生在小数逗号之前，每行被切成 6 格 ⟹ 形状与数值同时崩。"""
    p = _rewrite(D5, tmp_path, lambda ls: [l.replace(";", ",") for l in ls], name="z.csv")
    with pytest.raises(ScopeFormatError):
        read_scope(p)


# ------------------------------------------------------------------ D6

def test_d6_csv_segment_index_bom_and_nan_cells(tmp_path):
    t = read_scope(D6)
    assert t.dialect == "csv_segment_index"
    assert t.bom is True and t.newline == "\r\n"
    assert t.time_column == "TimeOutput" and t.time_col_source == "column_name"
    assert t.unit_source == "sidecar_attested:s"     # 秒：单位来自侧车声称，不是代码里的默认值
    assert t.n_rows_raw == 22260 and t.n_rows_shape_mismatch == 0
    assert t.n_columns == 10                         # 11 格 − TimeOutput
    assert abs(_fs(t) - 2e8) < 1e4                  # 步长 5.0000E-9
    assert t.data["VMeasCh1"][0] == -21.0833e-6
    # 段内续行（首格为空）必须整行留下，且尾随逗号造成的空尾字段只能是 NaN
    assert t.data["VMeasCh1"][1] == 4.2875e-3
    assert math.isnan(t.data["R_AV"][1])
    assert math.isnan(t.data["StatusCh1"][0])        # 门控标志位，不是数值通道
    _generic_pack_ok(t, tmp_path / "d6")


def test_d6_rejects_non_numeric_cell(tmp_path):
    """制造非数值单元 ⟹ 拒读，不许静默当 NaN 混进包里。"""
    p = _rewrite(D6, tmp_path,
                 lambda ls: ls[:2] + [_set_cell(ls[9000], 1, "oops")] + ls[9001:],
                 sidecar=True)
    with pytest.raises(ScopeFormatError) as ei:
        read_scope(p)
    assert "非数值单元" in str(ei.value)


def test_d6_without_sidecar_has_no_time_unit_source(tmp_path):
    """侧车不在 ⟹ `TimeOutput` 的单位无任何来源 ⟹ 拒收：证明「秒」不是代码里写死的假设。"""
    p = _stage(D6, tmp_path, sidecar=False)
    with pytest.raises(ScopeFormatError) as ei:
        read_scope(p)
    assert "单位无来源" in str(ei.value)


def test_d6_same_file_with_sidecar_is_accepted(tmp_path):
    """同字节、带侧车 ⟹ 走 sidecar 佐证支路通过（上面的拒收不是因为文件坏了）。"""
    p = _stage(D6, tmp_path, sidecar=True)
    assert read_scope(p).unit_source == "sidecar_attested:s"


# ------------------------------------------------------------------ 通用接入

def _generic_pack_ok(table, outdir) -> None:
    """C1 契约字段齐全、C2 自检过：方言只影响「怎么读」，不影响下游消费方式。"""
    meta, ingest = c1.build_meta(table, sample_id="dialect")
    assert meta["source"]["ingest_profile"] == "dialect_generic"
    assert meta["present_channels"] == []            # 无语义映射 ⟹ 不猜 canonical 角色
    assert len(meta["extra_channels"]) == table.n_columns
    assert meta["channels"] == {} and meta["cross_validation"]["pairs"] == []
    assert meta["primary_time_base"] == "tb0" and len(meta["time_bases"]) == 1
    assert meta["quality"]["n_samples"] == len(table.data[table.columns[0].name])
    assert abs(meta["sample_rate_hz"] - _fs(table)) < 1e-6
    assert meta["sample_rate_source"] == "measured"
    assert all(r["anchor"] and r["statement"] for r in meta["audit"]["assumptions"])

    outdir = str(outdir)
    pack = c1.write_pack(meta, ingest, outdir)
    ingest["sample_id"] = "dialect"
    ingest["sha256"] = pack["sha256"]
    feats = features.compute(meta, ingest, outdir)
    assert feats["present_channels"] == []
    assert feats["global"]["fe_rms_counts"] is None
    assert abs(feats["freq_limits"]["fs_hz"] - _fs(table)) < 1e-6
    assert any(u["feature"] == "global.fe_rms_counts" for u in feats["unavailable"])
    features.check_null_accounting(feats)          # 每个 null 都有同名行（规则 2）