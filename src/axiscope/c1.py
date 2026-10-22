"""C1 样本包装配：厂商 CSV → meta.json + waveform.tsv（C1 契约）。

只做契约明文要求的事；任何超出契约的推断一律不写进包，改写进 meta.audit.assumptions。
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os

import numpy as np

from . import dialects, mapping
from .anchors import assumption_row as row
from .twincat import ScopeFormatError, ScopeTable, gate_episodes, read_scope, timebase_stats

SCHEMA = "axiscope.waveform/1"
VOCAB_ORDER = ["pos_cmd", "pos_fb", "fe", "vel_cmd", "vel_fb", "cur_q", "cur_cmd",
               "torque", "temp", "laser_power", "io", "vision_x", "vision_y", "vision_angle"]
SEGMENT_KINDS = ["rest", "move", "settling", "dwell", "probing", "path",
                 "homing", "scanning", "curing", "unknown"]
CITATION = {
    "author": "Reichenbach, Thomas — University of Stuttgart",
    "doi": "10.18419/DARUS-3600",
    "license": "CC BY 4.0",
    "note": "脱敏只清主机路径/ADS NetID/绝对墙钟，不清署名与 DOI（KB2 §6.2）",
}
BOOL_PREFIX = "b"
MOVE_REL_THRESHOLD = 0.02
CONSTANT_SPEED_REL_SPREAD = 0.05
MIN_SEGMENT_S = 0.25
# C1 派生规则 9（A-105 ①）的字面判定式：行级最大残差 ≤ 1e-12 × 该列幅值。
IDENTITY_REL_TOL = 1e-12
IDENTITY_NOMINATE_REL = 1e-4        # 粗筛（相对去均值能量）：只排除明显无关的三元组，判定看逐行残差
IDENTITY_MIN_ROWS = 100             # 少于三未知数可稳解的行数 ⟹ 核对不执行（A-105 ④）


#: `meta.audit.identity_check` 的字段集（A-105 ① 的落档处）：C2 镜像同一组键，
#: 两处必须同源，否则报告与规则层会各自解释"核对做没做"。
AUDIT_IDENTITY_KEYS = ("performed", "n_numeric_columns", "n_rows_checked", "n_derived",
                      "n_duplicate_groups", "n_constant_columns",
                      "n_independent_position", "reason")


class PackError(Exception):
    pass


def _segments(t: list[float], v: list[float], fs: float) -> list[dict]:
    peak = max(abs(x) for x in v)
    if peak == 0:
        return []
    v_th = MOVE_REL_THRESHOLD * peak
    moving = [abs(x) > v_th for x in v]
    runs: list[tuple[int, int, bool]] = []
    start = 0
    for i in range(1, len(moving) + 1):
        if i == len(moving) or moving[i] != moving[start]:
            runs.append((start, i - 1, moving[start]))
            start = i
    gap = max(1, int(round(MIN_SEGMENT_S * fs)))
    merged: list[list] = []
    for r in runs:
        if merged and r[2] == merged[-1][2] and r[0] - merged[-1][1] <= gap:
            merged[-1][1] = r[1]
        else:
            merged.append([r[0], r[1], r[2]])

    out = []
    for a, b, is_move in merged:
        if (b - a + 1) < gap:
            continue
        kind = "rest"
        note = None
        if is_move:
            seg = v[a:b + 1]
            mean = sum(abs(x) for x in seg) / len(seg)
            spread = (max(seg) - min(seg)) / mean if mean else math.inf
            if spread <= CONSTANT_SPEED_REL_SPREAD:
                kind = "probing"
                note = f"恒速段：|vel| 峰峰/均值 = {spread:.4f} ≤ {CONSTANT_SPEED_REL_SPREAD}"
            else:
                kind = "move"
                note = f"变速段：|vel| 峰峰/均值 = {spread:.4f} > {CONSTANT_SPEED_REL_SPREAD}"
        out.append({"id": len(out), "kind": kind, "t0": round(t[a], 6), "t1": round(t[b], 6),
                    "axis": None, "note": note})
    return out


def _nan_ratio(xs: list[float]) -> float:
    if not xs:
        return 0.0
    return sum(1 for x in xs if x != x) / len(xs)


def _min_step(xs: list[float]) -> float | None:
    vals = sorted({x for x in xs if x == x})
    if len(vals) < 2:
        return None
    return min(b - a for a, b in zip(vals, vals[1:]))


#: 非 Scope View 方言的接入标记，落在 `meta.source.ingest_profile`。C1 契约字段一个不多一个不少，
#: 它只是告诉 C2「这份包走的是哪条接入路径」，好让 C2 不去复述 Scope View 样本的实测事实。
GENERIC_PROFILE = "dialect_generic"


def _build_meta_generic(table: ScopeTable, *, sample_id: str) -> tuple[dict, dict]:
    """D2/D3/D5/D6 的接入：时间轴来自导出自带的时间列，无触发门控、无 KV 元数据块。

    `sample_index` 装的是**相对首行的毫秒数**（不是行序号），`sample_time_ms=1.0` 只作毫秒→秒
    的换算载体，所以下游 `timebase_stats(index, dt_ms)` 不用改一个字就拿到真实 dt 与抖动。
    语义映射一概不做：`mapping.py` 只登记了 DARUS-3600 Scope View 的列，给别的方言按名字硬映
    等于凭空造语义（KB2 §三），故全部落 `extra_channels`，`present_channels` 为空。
    """
    dt_ms = table.sample_time_ms
    if dt_ms is None:
        raise PackError(f"{table.dialect}：无采样周期来源，不得据推断开样本（KB2 §5.2）")
    idx = table.sample_index
    if len(idx) < 2:
        raise PackError(f"{table.dialect}：时间列只有 {len(idx)} 行 ⟹ 无 dt、无采样率")
    t = [(x - idx[0]) * dt_ms / 1000.0 for x in idx]
    tb = timebase_stats(idx, dt_ms)
    if not tb.get("dt_median_s"):
        raise PackError(f"{table.dialect}：dt 中位数算不出来 ⟹ 无采样率，按 C1 拒收")
    fs = 1.0 / tb["dt_median_s"]

    series = {c.name: table.data[c.name] for c in table.columns}
    numeric = [c for c in table.columns if not c.name.startswith(BOOL_PREFIX)]
    side = dialects.sidecar_fields(table.path)
    citation = {
        "author": side.get("publisher", "unknown（本地无 <file>.source.txt 侧车）"),
        "doi": side.get("dataset_doi", "unknown"),
        "license": side.get("license", "unknown"),
        "note": "取自 <file>.source.txt 侧车的发布者自述；侧车缺失时本槽位为 unknown，"
                "不得沿用 DARUS-3600 的署名与 DOI（KB0 §六 检查 23：字段须有载体，无载体不得填值）",
    }

    extra = {}
    for col in table.columns:
        extra[col.name] = {
            "raw_column": col.name, "symbol": col.symbol, "native_unit": col.unit,
            "role": "unmapped", "confidence": 0.0, "time_base_ref": None,
            "derived_from": None, "derived_residual_max": None,
            "note": f"本方言（{table.dialect}）未经语义映射：mapping.py 只登记 DARUS-3600 "
                    "Scope View 的列，上游未发布逐列定义 ⟹ 原名落 extra，不猜角色"
                    "（KB2 §3.6 不丢弃不猜语义 / §4.12 R-4）",
        }

    identity = {
        "performed": False, "n_numeric_columns": len(numeric), "n_rows": len(t),
        "n_rows_checked": 0, "derived": [], "duplicates": [], "constants": [],
        "unattributed_columns": [], "duplicate_dropped": [],
        "n_derived": 0, "n_unattributed": 0, "n_duplicate_groups": 0,
        "n_constant_columns": 0, "position_columns_seen": [],
        "independent_position_columns": [],
        "n_independent_position_raw": None, "n_unattributed_among_position": None,
        "n_independent_position": None,
        "reason": "接入层未执行列间恒等式核对：mapping.DECLARED_COMPUTED 只登记 DARUS-3600 的两列，"
                  "本方言无归因依据 ⟹ 核对无处归因（A-105 ④：核对没跑成时独立测量数只能是 null）",
    }

    assumptions = [
        row("meta.sample_rate_source",
            f"采样率来自导出自带的时间列「{table.time_column}」（time_col_source="
            f"{table.time_col_source}、unit_source={table.unit_source}），由该列逐行差分独立推得 "
            f"fs={fs:.6f} Hz、dt_jitter_ratio={tb['dt_jitter_ratio']:.3e}；"
            f"Scope View 的 `SampleTime[ms]` 声明值在本方言不存在，故 sample_rate_source 记 measured "
            "而非 declared"),
        row("meta.extra_channels",
            f"本方言 {table.dialect} 的 {len(table.columns)} 个测量列全部落 extra_channels："
            "mapping.py 的语义映射只覆盖 DARUS-3600 Scope View，上游未发布这些列的逐列定义 ⟹ "
            "present_channels 为空，不按名字猜 canonical 角色（KB2 §三 / §4.12 R-4）"),
        row("meta.units_are",
            "各测量列的单位上游未发布（文件名/表头只有符号名与短码）⟹ units_are 与 "
            "counts_per_mm 均留 null，不按量纲猜 si_native 或 counts（KB2 §3.5）"),
        row("meta.axis",
            "电机型号、每转计数、行程限位均未随导出发布 ⟹ axis 六个字段留 null"),
        row("meta.segments",
            "分段需要一条已知语义的速度/位置通道，本方言未经语义映射 ⟹ segments 留空；"
            "C1 红线 4 的「无 move/settling/probing 段」在此不构成拒收理由，因为缺的是通道身份，"
            "不是段本身"),
        row("meta.audit.identity_check", identity["reason"]),
        row("meta.source.tier",
            "证据分级（source.tier）只对 DARUS-3600 Scope View 样本裁定过 ⟹ 本样本留 null，"
            "不沿用 T1-a（KB0 §六 检查 23）"),
    ]
    if table.n_rows_shape_mismatch:
        assumptions.append(row("meta.provenance",
                               f"{table.n_rows_shape_mismatch} 行与表头列数不符，已剔除且计数登记"))

    nan_by = {c.name: round(_nan_ratio(series[c.name]), 6) for c in table.columns}
    quality = {
        "n_samples": len(t),
        "dt_median_s": tb["dt_median_s"],
        "dt_jitter_ratio": tb["dt_jitter_ratio"],
        "gap_max_s": round(tb["gap_max_s"], 9),
        "nan_ratio": round(_nan_ratio(t), 6),
        "nan_ratio_by_channel": nan_by,
        "quantization_step_counts": None,
        "nyquist_hz": fs / 2.0,
        "flags": ["time_column_relative", "semantic_mapping_unregistered"],
    }
    meta = {
        "schema": SCHEMA,
        "source": {
            "vendor": "unknown",
            "drive_model": None,
            "export_format": table.dialect,
            "original_filename": os.path.basename(table.path),
            "tier": None,
            "ingest_confidence": 0.0,
            "ingest_profile": GENERIC_PROFILE,
        },
        "sample_rate_hz": fs,
        "sample_rate_source": "measured",
        "units_are": None,
        "counts_per_mm": None,
        "encoder_lines": None,
        "rated_current_a": None,
        "axis": {"name": None, "type": None, "motor_rev_counts": None,
                 "travel_limit_neg_mm": None, "travel_limit_pos_mm": None},
        "sensor_config": "unknown",
        "cross_validation": {
            "pairs": [],
            "note": "无 canonical 通道 ⟹ 无可配对的两路独立测量，C2 的 sensor_disagreement 数组为空",
        },
        "drive": {
            "position_loop_period_us": None, "velocity_loop_gain_hz": None,
            "current_loop_bandwidth_hz": None, "rigidity_level": None,
            "notch_filters": [], "inertia_ratio": None,
            "rated_torque_N_m": None, "rated_torque_source": None,
            "current_limit_a": None, "current_limit_source": None,
        },
        "present_channels": [],
        "time_bases": [{
            "id": "tb0", "role": "primary", "n_samples": len(t),
            "dt_median_s": tb["dt_median_s"], "sample_rate_hz": fs,
            "dt_jitter_ratio": tb["dt_jitter_ratio"],
            "strictly_monotonic": tb["strictly_monotonic"],
            "unit_source": table.unit_source,
        }],
        "primary_time_base": "tb0",
        "resample": [],
        "channels": {},
        "extra_channels": extra,
        "io_bits": {},
        "segments": [],
        "quality": quality,
        "context": {
            "machine": None,
            "complaint": None,
            "operator_notes": "厂商/数据集公开导出，无现场工单上下文；本包只承载结构化读表结果，"
                              "语义映射与证据分级均未裁定",
        },
        "provenance": {
            "n_rows_raw": table.n_rows_raw,
            "n_rows_shape_mismatch": table.n_rows_shape_mismatch,
            "dropped_head_rows": 0,
            "trigger_gate": None,
            "header_rows": table.n_header_rows,
            "dialect": table.dialect,
            "time_column": table.time_column,
            "time_col_source": table.time_col_source,
            "unit_source": table.unit_source,
            "file_meta": table.file_meta,
            "citation": citation,
        },
        "audit": {"assumptions": assumptions,
                  "identity_check": {k: identity[k] for k in AUDIT_IDENTITY_KEYS}},
    }
    ingest = {
        "wave_columns": ["t"] + [f"x_{c.name}" for c in numeric],
        "series": series, "t": t, "canon_series": {},
        "findings": [], "pairs": [], "masquerade": [],
        "identity": identity, "sign_check": None,
    }
    return meta, ingest


def build_meta(table: ScopeTable, *, sample_id: str) -> tuple[dict, dict]:
    if table.dialect != "twincat_scope_view":
        return _build_meta_generic(table, sample_id=sample_id)

    header = [c.name for c in table.columns]
    mapping.check_coverage(header)

    gate = table.data["bTrigger_Record"]
    eps = gate_episodes(gate)
    if not eps:
        raise PackError("bTrigger_Record 全程为 0：触发门控后无样本（KB3 纪律 8）")
    eps.sort(key=lambda e: e[1] - e[0], reverse=True)
    lo, hi = eps[0]
    dt_ms = table.sample_time_ms
    if dt_ms is None:
        raise PackError("表头无 SampleTime[ms]：时基单位无来源，不得据推断开样本（KB2 §5.2）")

    idx = table.sample_index[lo:hi + 1]
    t = [(x - idx[0]) * dt_ms / 1000.0 for x in idx]
    tb = timebase_stats(idx, dt_ms)
    fs = 1.0 / tb["dt_median_s"]

    series = {}
    for col in table.columns:
        series[col.name] = table.data[col.name][lo:hi + 1]

    findings: list[dict] = []
    identity = _identity_scan(series, finding_table=findings)
    # A-105 ②：派生列与全等孪生的丢弃侧都不是「第二次测量」，不配进互证配对。
    # 恒等式核对必须先于配对——先配好再核对，剔除就只剩注释里的自觉。
    not_independent = ({d["column"] for d in identity["derived"]}
                       | set(identity["duplicate_dropped"]))
    pairs = _pairwise_findings(series, mapping.CROSS_VALIDATION_PAIRS, finding_table=findings,
                               not_independent=not_independent)
    masquerade = _masquerade_check(series, finding_table=findings)
    sign_check = _velocity_sign_check(series, t)

    twin_diff = {r["cmd"]: (r["n_rows_differ"], r["n_rows"]) for r in masquerade}
    pos_tar = twin_diff.get("dPosition_test_tar")
    if pos_tar is None:
        tar_note = "本样本无该列，拒映依据无法实测"
    elif pos_tar[0] == 0:
        tar_note = (f"门控后 {pos_tar[1]} 行实测与 dPosition_test 有 0 行不同 ⟹ 逐行全等，"
                    "映射后会凭空造出 fe ≡ 0 的指令轨（A-98 ③ 的冒充支）")
    else:
        tar_note = (f"门控后 {pos_tar[1]} 行实测与 dPosition_test 有 {pos_tar[0]} 行不同 ⟹ "
                    "该两列并非全等，KB2 §4.10 的拒映理由需按本样本重判（登记为未复核）")
    assumptions: list[dict] = [
        row("meta.sample_rate_source",
            f"厂商在表头声明 SampleTime[ms]={dt_ms:g}；由采样序号列差分独立推得 "
            f"fs={fs:.6f} Hz，两者一致，声明值非孤证（`sample_rate_source=declared` 的依据）"),
        row("channels.pos_cmd",
            "KB2 §4.10 样本卡优先于 §4.1 族卡 ⟹ dPosition_test_tar 拒映 pos_cmd：" + tar_note),
        row("channels.vel_fb",
            "bMovingForward 全程恒 0，作者脚本的 dir = ±1 规则在本样本上不产生符号信息（KB3 纪律 9）："
            "vel_fb 按 KB2 §4.1 直映、不乘 dir，依赖方向的判据须放弃"),
        row("channels.torque",
            "dTorque_* 绝对刻度未定：KB2 §七-3 转述作者脚本有 ×10 修正，本地无该脚本可核，"
            "torque 按 ×1 原样入包（KB0 §六 检查 23：字段须有载体，无载体不得填值）"),
        row("meta.audit.identity_check",
            (f"列间恒等式核对（C1 派生规则 9 / A-105 ①）已在门控后 {identity['n_rows_checked']} 行切片上执行："
             f"派生列 {identity['n_derived']}、逐行全等组 {identity['n_duplicate_groups']}、"
             f"常数列 {identity['n_constant_columns']}；独立位置测量列 = "
             f"{identity['n_independent_position']}（{', '.join(identity['independent_position_columns'])}）"
             if identity["performed"] else
             f"列间恒等式核对未执行：{identity['reason']}（A-105 ④）")),
    ]
    if len(eps) > 1:
        dropped = len(eps) - 1
        assumptions.append(row(
            "meta.time_bases",
            f"触发门控产生 {len(eps)} 个不连续区间，只保留最长的一段"
            f"（第 {lo}–{hi} 行），其余 {dropped} 段未纳入："
            "拼接多段会破坏等间隔时间轴，而 A-96 的重采样登记只覆盖跨栅格，不覆盖行筛选"))
    if sign_check is not None:
        assumptions.append(sign_check)

    segments = _segments(t, series["dVelocity_test"], fs)
    kinds = {s["kind"] for s in segments}
    if not (kinds & {"move", "settling", "probing"}):
        raise PackError(f"无 move/settling/probing 段（实得 {sorted(kinds)}）：C1 红线 4")

    canonical = sorted((m.canonical for m in mapping.MAPPED),
                       key=lambda c: VOCAB_ORDER.index(c) if c in VOCAB_ORDER else 99)
    channels = {}
    for m in mapping.MAPPED:
        col = table.column(m.raw_column)
        channels[m.canonical] = {
            "raw_column": m.raw_column, "symbol": col.symbol, "unit": m.unit,
            "role": "mapped", "sign": m.sign, "offset": m.offset,
            "inferred": m.inferred, "confidence": m.confidence,
            "time_base_ref": None, "basis": m.basis, "note": m.note,
        }

    extra = {}
    derived_by_col = {d["column"]: d for d in identity["derived"]}
    for name, ex in mapping.EXTRAS.items():
        if name not in series:
            continue
        col = table.column(name)
        d = derived_by_col.get(name)
        extra[name] = {
            "raw_column": name, "symbol": col.symbol, "native_unit": ex.unit,
            "role": "unmapped", "confidence": 0.0, "time_base_ref": None,
            "derived_from": d["basis"] if d else None,
            "derived_residual_max": d["max_abs_residual"] if d else None,
            "note": ex.note,
        }

    wave_cols = ["t"] + canonical + [f"x_{n}" for n in extra
                                     if not n.startswith(BOOL_PREFIX)]

    nan_by = {c: round(_nan_ratio(series[m.raw_column]), 6) for c, m in
              ((x.canonical, x) for x in mapping.MAPPED)}
    quality = {
        "n_samples": len(t),
        "dt_median_s": tb["dt_median_s"],
        "dt_jitter_ratio": tb["dt_jitter_ratio"],
        "gap_max_s": round(tb["gap_max_s"], 9),
        "nan_ratio": round(_nan_ratio(t), 6),
        "nan_ratio_by_channel": nan_by,
        "quantization_step_counts": None,
        "nyquist_hz": fs / 2.0,
        "flags": ["time_column_relative", "trigger_gated:bTrigger_Record", "units_si_native"],
    }

    meta = {
        "schema": SCHEMA,
        "source": {
            "vendor": "beckhoff",
            "drive_model": "TwinCAT3 ScopeView",
            "export_format": "csv",
            "original_filename": os.path.basename(table.path),
            "tier": "T1-a",
            "ingest_confidence": 0.9,
        },
        "sample_rate_hz": fs,
        "sample_rate_source": "declared",
        "units_are": "si_native",
        "counts_per_mm": None,
        "encoder_lines": None,
        "rated_current_a": None,
        "axis": {"name": None, "type": None, "motor_rev_counts": None,
                 "travel_limit_neg_mm": None, "travel_limit_pos_mm": None},
        "sensor_config": "unknown",
        "cross_validation": {
            "pairs": [list(p) for p in mapping.CROSS_VALIDATION_PAIRS],
            "note": "三套独立位置测量互不一致（§4.10）⟹ 全部经 extra_channels 保留，"
                    "分歧本身是证据，不择一当 pos_fb（C2 sensor_disagreement）",
        },
        "drive": {
            "position_loop_period_us": None, "velocity_loop_gain_hz": None,
            "current_loop_bandwidth_hz": None, "rigidity_level": None,
            "notch_filters": [], "inertia_ratio": None,
            "rated_torque_N_m": None, "rated_torque_source": None,
            "current_limit_a": None, "current_limit_source": None,
        },
        "present_channels": canonical,
        "time_bases": [{
            "id": "tb0", "role": "primary", "n_samples": len(t),
            "dt_median_s": tb["dt_median_s"], "sample_rate_hz": fs,
            "dt_jitter_ratio": tb["dt_jitter_ratio"],
            "strictly_monotonic": tb["strictly_monotonic"], "unit_source": "measured",
        }],
        "primary_time_base": "tb0",
        "resample": [],
        "channels": channels,
        "extra_channels": extra,
        "io_bits": {},
        "segments": segments,
        "quality": quality,
        "context": {
            "machine": "缆索执行器试验台（cable-actuator-testbed，DARUS-3600）",
            "complaint": None,
            "operator_notes": "非故障工单样本：DaRUS 公开试验数据，用于验证接入链路与能力边界；"
                              "不是产线故障记录，不得当作半导体设备现场证据",
        },
        "provenance": {
            "n_rows_raw": table.n_rows_raw,
            "n_rows_shape_mismatch": table.n_rows_shape_mismatch,
            "dropped_head_rows": 0,
            "trigger_gate": {
                "channel": "bTrigger_Record",
                "rows_kept": len(t),
                "rows_in_gate": sum(hi - lo + 1 for lo, hi in eps),
                "n_episodes": len(eps),
                "rows_used": [lo, hi],
            },
            "header_rows": table.n_header_rows,
            "citation": CITATION,
        },
        "audit": {"assumptions": assumptions,
                  "identity_check": {k: identity[k] for k in AUDIT_IDENTITY_KEYS}},
    }
    ingest = {"wave_columns": wave_cols, "series": series, "t": t,
              "canon_series": {m.canonical: series[m.raw_column] for m in mapping.MAPPED},
              "findings": findings, "pairs": pairs, "masquerade": masquerade,
              "identity": identity, "sign_check": sign_check}
    return meta, ingest


def _pearson(xa, xb) -> float | None:
    ma, mb = sum(xa) / len(xa), sum(xb) / len(xb)
    da = math.sqrt(sum((v - ma) ** 2 for v in xa))
    db = math.sqrt(sum((v - mb) ** 2 for v in xb))
    if da == 0.0 or db == 0.0:
        return None
    return sum((a - ma) * (b - mb) for a, b in zip(xa, xb)) / (da * db)


def _pairwise_findings(series: dict, pairs, finding_table: list[dict],
                       not_independent=frozenset()) -> list[dict]:
    """两路分歧按 C2 规则 16（A-106）计算：先减原点，再在残差上取幅值。

    `datum_offset = mean(a-b)` 是两套编码器各自的安装/原点偏置，不是分歧；不减掉它，
    rms/max 就是在给常数偏置打分。`corr` 反过来必须在**原始值**上算（A-106：减完原点
    再算相关会把同向缓慢漂移的成分一并抹掉，相关系数量的是形状一致性）。

    `not_independent`（A-105 ②：恒等式核对认定的派生列 + 全等孪生的丢弃侧）出现在配对里
    即整对剔除——算出来的列与自己的孪生都不构成第二次测量，留着就是给同一路信号记两票。
    """
    out = []
    for a, b in pairs:
        if a in not_independent or b in not_independent:
            finding_table.append(
                {"kind": "pair_excluded_by_identity", "a": a, "b": b,
                 "excluded": a if a in not_independent else b,
                 "note": "该对有一列是派生列或全等孪生的丢弃侧 ⟹ 不是两路独立测量，"
                         "整对不进交叉验证，也不参与互证计数（A-105 ②）"})
            continue
        xa, xb = series[a], series[b]
        d = [p - q for p, q in zip(xa, xb)]
        n_diff = sum(1 for v in d if v != 0.0)
        datum = sum(d) / len(d)
        resid = [v - datum for v in d]
        mx = max(abs(v) for v in resid)
        rms = math.sqrt(sum(v * v for v in resid) / len(resid))
        corr = _pearson(xa, xb)
        sign = "b_a" if sum(1 for v in resid if v > 0) > sum(1 for v in resid if v < 0) else "a_b"
        out.append({"a": a, "b": b, "a_role": mapping.channel_role(a),
                    "b_role": mapping.channel_role(b),
                    "a_principle": mapping.principle(a), "b_principle": mapping.principle(b),
                    "n_rows_differ": n_diff, "datum_offset": datum,
                    "rms": rms, "max_abs": mx, "corr": corr,
                    "direction": sign, "unit": "m"})
        finding_table.append(
            {"kind": "sensor_disagreement", "a": a, "b": b, "n_rows_differ": n_diff,
             "datum_offset_m": datum, "rms_m": rms, "max_abs_m": mx, "corr": corr,
             "note": "分歧本身是证据，不得择一当 pos_fb（C1 cross_validation.note / A-6）；"
                     "rms/max 已扣原点偏置（C2 规则 16 / A-106），corr 在原始值上算"})
    return out


def _masquerade_check(series: dict, finding_table: list[dict]) -> list[dict]:
    """A-98 ③：指令轨候选与同名反馈候选逐行全等 ⟹ 该「反馈」是指令冒充，不是第二次测量。

    判据必须在接入层实测：KB2 §4.1 族卡允许把 `_tar` 列映成 `pos_cmd`，而 §4.10 的样本卡说
    本样本映不得 ⟹ 两者的分歧只能靠行数差来裁，拒映注释本身不是证据。
    """
    out = []
    for cmd, fb in mapping.CMD_FB_TWINS:
        if cmd not in series or fb not in series:
            continue
        n = len(series[cmd])
        n_diff = sum(1 for p, q in zip(series[cmd], series[fb]) if p != q)
        out.append({"cmd": cmd, "fb": fb, "n_rows": n, "n_rows_differ": n_diff})
        if n_diff == 0:
            finding_table.append(
                {"kind": "command_masquerade", "cmd": cmd, "fb": fb, "n_rows": n,
                 "note": "指令轨与候选反馈逐行全等，二者非独立测量（A-98 ③ 固定句式）"})
    return out


def _identity_scan(series: dict, finding_table: list[dict]) -> dict:
    """C1 派生规则 9（A-105 ①③）：同文件列间的定系数线性恒等式核对。

    覆盖范围只有 `c ≟ α·a + β·b + γ`。差分/滤波类派生列（本样本 `dRate_asco` 大概率是
    `dPosition_asco` 的差分）不在其内 ⟹ 本函数只声称"这些列里哪些是算出来的"，
    不声称"找全了派生列"。核对跑在**门控后入包的切片**上；母本全量的那条恒等式另有
    `data/probe_diff_identity.py` 承载（KB0 §6 检查 27）。
    常数列既不是测量也不是派生列，但它和派生列一样会让独立测量计数虚增，故单列登记。

    一条恒等式有多个书写方向（`test + load + diff ≡ 0` 可以解出其中任何一列），它们是
    **同一条约束**，不是三条 ⟹ 关系向量按单位模长去重。方向（哪一列是算出来的）不能从
    数据本身读出，只接受 `mapping.DECLARED_COMPUTED` 唯一命中的归因；其余关系登记为
    `linear_dependency_unattributed`，只扣自由度、不贴派生标签（A-105 ①）。
    """
    names = [n for n in series if not n.startswith(BOOL_PREFIX)]
    n_rows = len(next(iter(series.values()))) if series else 0
    if len(names) < 3 or n_rows < IDENTITY_MIN_ROWS:
        return {"performed": False, "n_numeric_columns": len(names), "n_rows": n_rows,
                "n_rows_checked": 0, "derived": [], "duplicates": [], "constants": [],
                "unattributed_columns": [], "duplicate_dropped": [],
                "n_derived": 0, "n_relations": 0, "n_unattributed": 0,
                "n_duplicate_groups": 0, "n_constant_columns": 0,
                "position_columns_seen": [], "independent_position_columns": [],
                "n_independent_position_raw": None, "n_unattributed_among_position": None,
                "n_independent_position": None,
                "reason": f"数值列 {len(names)} / 行数 {n_rows} 不足以稳定解 α/β/γ ⟹ "
                          "恒等式核对未执行，独立测量数不可信（A-105 ④）"}

    X = np.column_stack([np.asarray([float(v) for v in series[n]], dtype=float)
                         for n in names])
    X = X[np.isfinite(X).all(axis=1)]
    n_checked = int(X.shape[0])
    if n_checked < IDENTITY_MIN_ROWS:
        return {"performed": False, "n_numeric_columns": len(names), "n_rows": n_rows,
                "n_rows_checked": n_checked, "derived": [], "duplicates": [],
                "constants": [], "unattributed_columns": [], "duplicate_dropped": [],
                "n_derived": 0, "n_relations": 0, "n_unattributed": 0,
                "n_duplicate_groups": 0, "n_constant_columns": 0,
                "position_columns_seen": [], "independent_position_columns": [],
                "n_independent_position": None,
                "reason": f"有限值行仅 {n_checked} 行 ⟹ 核对未执行（A-105 ④）"}

    amp = np.max(np.abs(X), axis=0)
    std = np.std(X, axis=0)
    constants = [names[i] for i in range(len(names)) if std[i] == 0.0]
    pool = [i for i in range(len(names)) if std[i] > 0.0]
    A = np.column_stack([X[:, pool], np.ones(n_checked)])
    ci = len(pool)
    # 粗筛用的 Gram：先中心化再按幅值归一。原始列量级差到 1e2、列间又高度相关，
    # 直接 A.T@A 的法方程条件数会把残差能量估到 1e-7 相对量级，正好把真恒等式筛掉
    # （实测漏掉 `dPosition_diff ≡ -(test+load)`）。判定仍由下面的逐行残差做。
    Z = (X[:, pool] - X[:, pool].mean(axis=0)) / amp[pool]
    G = np.column_stack([Z, np.ones(n_checked)]).T @ np.column_stack([Z, np.ones(n_checked)])

    duplicates = [[names[pool[u]], names[pool[v]]]
                  for u in range(len(pool)) for v in range(u + 1, len(pool))
                  if float(np.max(np.abs(X[:, pool[u]] - X[:, pool[v]]))) == 0.0]
    cmd_twin = {c for c, _ in mapping.CMD_FB_TWINS}
    # 全等孪生只算一路；保留侧必须是反馈列，指令列（`_tar`）本就不是测量（A-98 ③ / A-105 ③）
    dup_dropped = {(a, b)[a not in cmd_twin] for a, b in duplicates}

    amp_by = {names[i]: float(amp[i]) for i in range(len(names))}
    canon = {}
    for a, b in duplicates:
        drop = (a, b)[a not in cmd_twin]
        canon[drop] = b if drop == a else a

    relations = []
    for tp, it in enumerate(pool):          # tp 是 A/G 的池内下标，it 是 names/X 的绝对下标
        tgt = canon.get(names[it], names[it])
        scale = amp_by[tgt]
        for u in range(len(pool)):
            for v in range(u + 1, len(pool)):
                if u == tp or v == tp:
                    continue
                k = [u, v, ci]
                try:
                    rough = np.linalg.solve(G[np.ix_(k, k)], G[k, tp])
                except np.linalg.LinAlgError:
                    continue
                res_e = max(float(G[tp, tp] - float(rough @ G[k, tp])), 0.0)
                if math.sqrt(res_e) > IDENTITY_NOMINATE_REL * math.sqrt(float(G[tp, tp])):
                    continue        # 粗筛只管排除，判定以下面 lstsq 的逐行残差为准
                B = A[:, k]
                coef = np.linalg.lstsq(B, X[:, it], rcond=None)[0]
                vec = np.zeros(len(pool))
                vec[tp] = 1.0
                vec[u] -= float(coef[0])
                vec[v] -= float(coef[1])
                const = -float(coef[2])
                merged = {}
                for j in range(len(pool)):
                    if abs(float(vec[j])) * amp_by[names[pool[j]]] <= 1e-9 * scale:
                        continue
                    nm = canon.get(names[pool[j]], names[pool[j]])
                    merged[nm] = merged.get(nm, 0.0) + float(vec[j])
                terms = {n: c for n, c in merged.items() if abs(c) * amp_by[n] > 1e-9 * scale}
                if len(terms) < 2 or tgt not in terms:
                    continue        # 代入全等孪生后自我抵消 ⟹ 那是 duplicate，不是恒等式
                others = sorted(n for n in terms if n != tgt)
                w = float(terms[tgt])
                gamma = float(-const / w)
                mx = float(np.max(np.abs(
                    X[:, names.index(tgt)]
                    - sum(float(-terms[n] / w) * X[:, names.index(n)] for n in others) - gamma)))
                if mx > IDENTITY_REL_TOL * scale:
                    continue
                direction = {"basis": others, "coefficients": [float(-terms[n] / w) for n in others],
                             "gamma": gamma, "max_abs_residual": mx, "column_amplitude": scale,
                             "tolerance": IDENTITY_REL_TOL * scale, "n_rows_checked": n_checked}
                key = np.array([terms[n] for n in sorted(terms)] + [const])
                big = int(np.argmax(np.abs(key)))
                if key[big] < 0:
                    key = -key
                key = key / float(np.linalg.norm(key))
                rel = next((r for r in relations
                            if sorted(r["terms"]) == sorted(terms)
                            and float(np.linalg.norm(r["key"] - key)) <= 1e-6), None)
                if rel is None:
                    relations.append({"key": key, "terms": terms, "directions": {}})
                    rel = relations[-1]
                cur = rel["directions"].get(tgt)
                if cur is None or mx < cur["max_abs_residual"]:
                    rel["directions"][tgt] = direction

    derived, unattributed = [], []
    for rel in relations:
        members = sorted(rel["terms"])
        head = [c for c in members
                if set(mapping.DECLARED_COMPUTED.get(c, ())) == set(members) - {c}
                and c in rel["directions"]]
        if len(head) != 1:
            rel["reason"] = ("文档未声明其中任何一列为计算列" if not head
                             else "声明歧义：多列可同时充当被算出的那一列")
            unattributed.append(rel)
            continue
        d = rel["directions"][head[0]]
        derived.append({"column": head[0], "basis": d["basis"], "members": d["basis"],
                        "coefficients": d["coefficients"], "gamma": d["gamma"],
                        "n_rows_checked": n_checked,
                        "max_abs_residual": d["max_abs_residual"],
                        "column_amplitude": d["column_amplitude"], "tolerance": d["tolerance"],
                        "directions_in_data": sorted(rel["directions"]),
                        "declared_by": "KB2 §4.10 通道卡行注（A-104 ① 就地更正）"
                                       "＋ C1 派生规则 9 / A-105 ① 归因纪律"})

    derived_names = {d["column"] for d in derived}
    position_pool = [names[i] for i in pool if names[i].startswith("dPosition")]
    independent = [c for c in position_pool if c not in derived_names and c not in dup_dropped]
    live = set(independent)
    unattr_position = [rel for rel in unattributed
                       if len([c for c in rel["terms"] if c in live]) >= 2]
    # 未归因的关系仍是实测约束：它只减一个自由度，不指认哪一列是算出来的
    n_independent = len(independent) - len(unattr_position)

    for d in derived:
        finding_table.append(
            {"kind": "derived_column", "column": d["column"], "basis": d["basis"],
             "members": d["members"], "coefficients": d["coefficients"], "gamma": d["gamma"],
             "max_abs_residual": d["max_abs_residual"], "tolerance": d["tolerance"],
             "declared_by": d["declared_by"],
             "directions_consistent_with_data": d["directions_in_data"],
             "note": "控制器现场算出的列，零独立信息 ⟹ 排除于 fe 候选、互证计数与"
                     "「两路独立测量分歧」类判据（C1 派生规则 9 / A-105 ①②）。"
                     "归因方向来自文档声明，不是从恒等式本身推出（A-105 ①）"})
    for rel in unattributed:
        finding_table.append(
            {"kind": "linear_dependency_unattributed", "columns": sorted(rel["terms"]),
             "relation_coefficients": {k: round(v, 9) for k, v in sorted(rel["terms"].items())},
             "directions_consistent_with_data": sorted(rel["directions"]),
             "n_rows_checked": n_checked,
             "min_max_abs_residual": min(d["max_abs_residual"]
                                         for d in rel["directions"].values()),
             "reason": rel["reason"],
             "note": "这几列之间确有定系数线性关系，但文档没有声明其中哪一列是算出来的；"
                     "数据本身给不出因果方向（三个书写方向同样成立），故只按一条独立约束"
                     "扣减自由度计数，不给任何一列贴派生标签（A-105 ①）"})
    for a, b in duplicates:
        finding_table.append(
            {"kind": "duplicate_column", "a": a, "b": b, "n_rows_checked": n_checked,
             "dropped": (a if a in dup_dropped else b),
             "note": "逐行全等的两列只算一路测量（A-105 ③，与 A-98 ③ 同一计数口径）；"
                     "若其中一列是指令轨（`_tar`）则丢指令侧，指令本就不是测量"})
    finding_table.append(
        {"kind": "measurement_independence", "n_numeric_columns": len(names),
         "n_rows_checked": n_checked, "n_relations": len(relations),
         "n_derived": len(derived), "n_unattributed": len(unattributed),
         "n_unattributed_among_position": len(unattr_position),
         "n_duplicate_groups": len(duplicates), "n_constant_columns": len(constants),
         "position_columns_seen": position_pool,
         "independent_position_columns": independent,
         "n_independent_position_raw": len(independent),
         "n_independent_position": n_independent,
         "note": "A-105 ⑤ 的计数落档：独立位置测量列按去派生列、去全等孪生、去常数列之后统计，"
                 "再按未归因的独立线性约束逐条扣减自由度"})
    return {"performed": True, "n_numeric_columns": len(names), "n_rows": n_rows,
            "n_rows_checked": n_checked, "derived": derived, "duplicates": duplicates,
            "constants": constants, "n_relations": len(relations),
            "unattributed_columns": [sorted(r["terms"]) for r in unattributed],
            "duplicate_dropped": sorted(dup_dropped),
            "n_derived": len(derived),
            "n_unattributed": len(unattributed),
            "n_duplicate_groups": len(duplicates), "n_constant_columns": len(constants),
            "position_columns_seen": position_pool,
            "independent_position_columns": independent,
            "n_independent_position_raw": len(independent),
            "n_unattributed_among_position": len(unattr_position),
            "n_independent_position": n_independent, "reason": None}


def _velocity_sign_check(series: dict, t: list[float]) -> str | None:
    names = ("dPosition_test", "dVelocity_test", "dVelocity_load")
    if not all(n in series for n in names):
        return None
    dt = t[1] - t[0]
    dp = [(series[names[0]][i + 1] - series[names[0]][i]) / dt
          for i in range(len(t) - 1)]
    res = {}
    for n in names[1:]:
        v = series[n][:-1]
        res[n] = math.sqrt(sum((a - b) ** 2 for a, b in zip(v, dp)) / len(dp))
    worst = min(res, key=res.get)
    if res[worst] > 0.5 * max(res.values()):
        return None
    other = [n for n in res if n != worst][0]
    return row("channels.vel_fb",
               f"符号一致性实测：d({names[0]})/dt 与 {worst} 的 rms 残差 {res[worst]:.4g} m/s，"
               f"与 {other} 为 {res[other]:.4g} m/s ⟹ {worst} 与位置通道同向、{other} 反向"
               "（缆索两端反向是可能解释，但本地无列语义文档可证 ⟹ 只登记实测，不改 sign）")


def write_pack(meta: dict, ingest: dict, outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    series, t = ingest["series"], ingest["t"]
    cols = ingest["wave_columns"]
    src = {"t": t, **ingest["canon_series"]}
    for name in cols:
        if name.startswith("x_"):
            src[name] = series[name[2:]]
    with io.open(os.path.join(outdir, "waveform.tsv"), "w", encoding="utf-8",
                 newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for i in range(len(t)):
            fh.write("\t".join(_fmt(src[c][i]) for c in cols) + "\n")

    meta_path = os.path.join(outdir, "meta.json")
    body = json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=False)
    io.open(meta_path, "w", encoding="utf-8", newline="\n").write(body + "\n")

    wave_bytes = io.open(os.path.join(outdir, "waveform.tsv"), "rb").read()
    digest = hashlib.sha256(wave_bytes + body.encode("utf-8")).hexdigest()
    return {"dir": outdir, "sha256": digest, "n_rows": len(t), "n_cols": len(cols)}


def _fmt(x: float) -> str:
    if x != x:
        return "nan"
    return repr(x) if x != int(x) else str(int(x))