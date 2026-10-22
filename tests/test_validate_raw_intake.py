"""台账 #15：R-5（KB2 §4.12）token 化角色判定 + R-3 ISO-8601 时基解析 + R-6 小数逗号布局。

R-5 的三处误报是 `data/VERIFICATION-2026-10-20.md` §8.7 的实测数字
（`OilLevel_L` 命中 le**vel**、`FailureRate` 命中 **rate**、`Timestamp` 命中 timest**amp**），
这里按 KB0 §6 检查 22 落成负向回归。修法按裁定走 token 化（复用 `name_tokens` 的分词），
不继续加正则补丁。
R-3 只补**解析**（ISO 文本时间戳 → epoch 秒），严格单调门原样作用于转换后的序列——
非单调的 ISO 注入必须仍然被拒。
R-6（2026-10-21 主线程复算 #20 时发现）补的是**布局判定**：分号 + 逗号小数此前判 `unparsed`，
取值路径 `fnum` 一直认逗号小数，缺的只是 `is_num` 的嗅探 ⟹ 台账「时长 0.128 s」没有载体。
`guess_role_from_name` 与 `name_tokens` 共用 `split_name_tokens`：分词逻辑只此一份（A-54 单名律）。

    PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m pytest tests/test_validate_raw_intake.py -q
"""
from __future__ import annotations

import datetime
import importlib.util
import io
import math
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "validate_raw", os.path.join(ROOT, "data", "validate_raw.py"))
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)

LSMC = os.path.join(ROOT, "data", "incoming", "6114_lsmc.csv")


# ---------------------------------------------------------------- R-5：子串误报 → token 判定

def test_r5_measured_false_positives_are_gone():
    """§8.7 三处实测误报：token 化后必须整体落 unmapped（不猜语义，KB2 §三）。"""
    for name in ("OilLevel_L", "FailureRate", "Timestamp"):
        role = vr.guess_role_from_name(name)
        assert role == (None, None, False), name
        qty, d, is_diff = role
        # parse_table 同口径：qty 为空则不产规范名（不产出虚假的「已识别」角色）
        canon = vr.canonical_role(qty, d, name, is_diff) if qty else None
        assert canon is None, name


def test_r5_substring_traps_do_not_reappear():
    """同一误报形态的其他样本名：level/amp/rate 作为词内部片段一律不得命中。"""
    for name in ("oil_level", "amplifier_gain", "failurerate", "template_out",
                 "separate_ctrl", "high_level"):
        assert vr.guess_role_from_name(name) == (None, None, False), name


def test_r5_rate_dropped_as_bare_vel_token():
    """裸 "rate" 留在整词表里则 FailureRate 照样命中（token 化也分不开）——按剔除处置；
    `Rate_asco/dRate_asco` 因此落 unmapped，属命名族缺口（R-4 同族待办），不得反过来
    当作「数据里确无速度列」的证据。"""
    assert vr.guess_role_from_name("dRate_asco") == (None, None, False)
    assert vr.guess_role_from_name("Rate_asco") == (None, None, False)


def test_r5_keeps_documented_correct_roles():
    """既有正确判定不得弄丢：单字母量名、粘连指令后缀、e_<单字母> 误差族、[mA]/[V] 单位词。"""
    assert vr.guess_role_from_name("x_Ltar") == ("pos", "cmd", False)
    assert vr.guess_role_from_name("v_L") == ("vel", "fb", False)
    assert vr.guess_role_from_name("dVelocity_test_tar") == ("vel", "cmd", False)
    assert vr.guess_role_from_name("f_diff") == ("force", "na", True)
    assert vr.guess_role_from_name("x_diff") == ("pos", "fb", True)
    assert vr.guess_role_from_name("e_x") == ("pos", "fb", True)
    assert vr.guess_role_from_name("e_3d") == (None, None, False)      # 数字下标不在 e_x 族口径内
    assert vr.guess_role_from_name("Goal Current [mA]") == ("cur", "fb", False)
    assert vr.canonical_role("cur", "fb", "iq_motor", False) == "cur_q"
    assert vr.guess_role_from_name("tau_L") == ("torque", "fb", False)
    assert vr.guess_role_from_name("bEnable") == ("io", "na", False)
    assert vr.guess_role_from_name("f_no") == ("meta", "na", False)


def test_r4_untouched_robotics_family_stays_name_blind():
    """R-4 明确不在本轮范围：机器人学 q/theta/qd/eq 不得因本轮改动获得新角色。"""
    for name in ("q1", "q2", "theta1", "j1_qd", "j1_eq", "tout"):
        assert vr.guess_role_from_name(name) == (None, None, False), name


def test_name_tokens_and_splitter_single_source():
    """分词只此一份（A-54）：guess_role_from_name 与 name_tokens 共用 split_name_tokens。"""
    assert vr.split_name_tokens("OilLevel_L") == ["oil", "level", "l"]
    assert vr.split_name_tokens("dPosition") == ["d", "position"]
    assert vr.name_tokens("dPosition_test_tar") == ["test"]
    assert vr.name_tokens("x_Ltar") == vr.name_tokens("x_L")   # 同轴归组不回归


# ---------------------------------------------------------------- R-3：ISO-8601 时基解析

def _iso(ms):
    s = datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")
    return f"{s}.{int(ms % 1000):03d}000+00:00"


def _iso_variant_file(tmp_path, name, rewind_at=None, offset_hours=None):
    """把 synth_good 的 ms 时间列改写成 6114 形态的 ISO-8601 文本列（列名 t）。"""
    src = os.path.join(str(tmp_path), name + ".src.tsv")
    vr.synth_good(src)
    lines = io.open(src, encoding="utf-8").read().split("\n")
    out = []
    for i, ln in enumerate(lines):
        if not ln.strip():
            out.append(ln)
            continue
        c = ln.split("\t")
        if i == 0:
            c[0] = "t"
        else:
            ms = float(c[0])
            if rewind_at and i == rewind_at:
                ms -= 60000.0
            stamp = _iso(ms)
            if offset_hours:
                dt = datetime.datetime.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S") \
                    + datetime.timedelta(hours=offset_hours)
                stamp = dt.strftime("%Y-%m-%d %H:%M:%S") + stamp[19:23] + f"+{offset_hours:02d}:00"
            c[0] = stamp
        out.append("\t".join(c))
    dst = os.path.join(str(tmp_path), name + ".tsv")
    io.open(dst, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    return dst


def test_iso_epoch_parsing_and_offsets(tmp_path):
    a = vr.iso_epoch("2025-11-05 09:30:33.946000+00:00")
    b = vr.iso_epoch("2025-11-05 11:30:33.946000+02:00")
    c = vr.iso_epoch("2025-11-05T09:30:33.946Z")
    assert a == b == c
    assert vr.iso_epoch("2024-09-29 00:03:00") == vr.iso_epoch("2024-09-29T00:03:00Z")
    assert math.isnan(vr.iso_epoch("not-a-timestamp"))
    assert math.isnan(vr.iso_epoch("2025-02-30 09:30:33+00:00"))   # 非法日期不入账


def test_iso_timebase_accepted(tmp_path):
    rep = vr.validate(_iso_variant_file(tmp_path, "iso_ok"))
    assert rep["verdict"] == "accept", rep["redlines_fired"]
    tb = rep["timebase"]
    assert tb["strictly_monotonic"] is True
    assert tb["unit_source"] == "iso8601_text:epoch_seconds"
    assert abs(tb["fs_hz"] - 1000.0) < 1e-6
    assert abs(tb["duration_s"] - 2.999) < 1e-3
    assert tb["dt_jitter_ratio"] < 0.2


def test_iso_nonmonotonic_still_rejected(tmp_path):
    """R-3 修的是解析，不是门槛：ISO 列注入回拨后严格单调门必须照常开火。"""
    rep = vr.validate(_iso_variant_file(tmp_path, "iso_back", rewind_at=10))
    assert rep["verdict"] == "reject"
    assert any("时基非严格单调" in x for x in rep["redlines_fired"])


def test_iso_mixed_offset_still_ordered(tmp_path):
    """整体 +2h 偏移（同一时区）不改变差分——判定不受时区写法影响。"""
    rep = vr.validate(_iso_variant_file(tmp_path, "iso_off", offset_hours=2))
    tb = rep["timebase"]
    assert tb["strictly_monotonic"] is True
    assert abs(tb["fs_hz"] - 1000.0) < 1e-6


@pytest.mark.skipif(not os.path.exists(LSMC), reason="仓内 6114_lsmc.csv 不在")
def test_real_6114_lsmc_now_accepted():
    """KB7 台账 15/16 行口径：6114 两 CSV 此前被「时基非严格单调」误拒，修复后 accept。
    （同形态的 x_velSweep 文件与 3900_const_vel_110.tab 由 data/validate_raw.py 全量复跑核对，
    此处只跑 3000 行件保持测试快。）"""
    rep = vr.validate(LSMC)
    assert rep["verdict"] == "accept", rep["redlines_fired"]
    assert rep["n_data_rows"] == 3000
    tb = rep["timebase"]
    assert tb["strictly_monotonic"] is True
    assert 999.0 < tb["fs_hz"] < 1001.0
    assert tb["dt_jitter_ratio"] < 0.2
    roles = {c["canonical"] for c in rep["channels"] if c["canonical"]}
    assert "vel_fb" in roles                                  # 速度语义列在（*_v_*）
    assert "cur_q" not in roles                               # 上游无电流语义列


# ---------------------------------------------------------------- R-6：小数逗号（2563 形态）

LDD = os.path.join(ROOT, "data", "incoming",
                   "2563_LDD_Transfer_function_Force_controlled.csv")
DT_MS = 0.0625                    # 16 kHz：KB7 台账 20 行「时长 0.128 s」的出处


def _numeric_file(tmp_path, name, delimiter, decimal, n_rows=40):
    """同一组数值，两种书写（`,` 分隔+点小数 / `;` 分隔+逗号小数），用来对拍小数点嗅探。"""
    def w(v):
        s = f"{v:.6f}"
        return s if decimal == "dot" else s.replace(".", ",")
    d = delimiter
    lines = [d.join(["X (ms)", "C0:Lineardirektantrieb.r77", "C1:Lineardirektantrieb.r78[0]"])]
    lines += [d.join([w(i * DT_MS), w(19.999996), w(-20.172794)]) for i in range(n_rows)]
    p = os.path.join(str(tmp_path), name)
    io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return p


def test_r6_comma_decimal_layout_is_parsed_and_measured(tmp_path):
    """R-6：`0,000000;19,999996` 这类分号 + 逗号小数此前整份判 `layout=unparsed`
    ⟹ 台账那句「时长 0.128 s」没有工具载体。补的是**判定**，门槛不动：短件照旧硬拒。"""
    rep = vr.validate(_numeric_file(tmp_path, "semicolon_comma.csv", ";", "comma"))
    assert rep["format"]["layout"] == "plain_matrix", rep["redlines_fired"]
    assert rep["format"]["decimal_comma"] is True
    tb = rep["timebase"]
    assert tb["strictly_monotonic"] is True
    assert abs(tb["fs_hz"] - 1000.0 / DT_MS) < 1e-6
    assert abs(tb["duration_s"] - 39 * DT_MS / 1000.0) < 1e-6    # 报告侧保留 6 位小数
    assert any("有效时长<0.5s" in x for x in rep["redlines_fired"])
    assert len(rep["channels"]) == 2


def test_r6_comma_delimited_dot_decimal_file_is_not_flipped(tmp_path):
    """负向：逗号做**分隔符**、点做小数的文件不得被嗅成小数逗号（否则 `1,234` 千分位形态
    会被当成一个数，列数与数值占比全带偏——静默量纲/结构替换）。"""
    rep = vr.validate(_numeric_file(tmp_path, "comma_dot.csv", ",", "dot"))
    assert rep["format"]["decimal_comma"] is False
    assert rep["format"]["layout"] == "plain_matrix"
    assert abs(rep["timebase"]["fs_hz"] - 1000.0 / DT_MS) < 1e-6


def test_r6_sniff_requires_majority_comma_decimals():
    """嗅探的成立条件写死：逗号小数够多**且**点小数/整数不占多数。"""
    assert vr.sniff_decimal_comma([["1,5", "2,75"], ["3,0", "4,25"]] * 12) is True
    assert vr.sniff_decimal_comma([["1.5", "2.75"], ["12", "75"]] * 12) is False
    assert vr.sniff_decimal_comma([["1,000", "2"], ["3,500", "4"]] * 12) is False


@pytest.mark.skipif(not os.path.exists(LDD), reason="仓内 2563_LDD_*.csv 不在")
def test_real_2563_ledger_numbers_are_self_printed():
    """KB7 台账 20 行的「时长 0.128 s / 2 047 行 / 角色全缺」三个数由本工具打印（检查 27）。"""
    rep = vr.validate(LDD)
    assert rep["verdict"] == "reject"
    assert rep["format"]["decimal_comma"] is True
    assert rep["n_data_rows"] == 2047
    tb = rep["timebase"]
    assert abs(tb["fs_hz"] - 16000.0) < 1e-6
    assert abs(tb["duration_s"] - 0.127875) < 1e-6
    assert tb["dt_jitter_ratio"] == 0.0
    assert any("有效时长<0.5s" in x for x in rep["redlines_fired"])
    assert any("未识别" in x for x in rep["redlines_fired"])
