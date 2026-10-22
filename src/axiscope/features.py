"""C2 特征向量：只读 C1 样本包，只产确定性数值（契约 C2）。

纪律：C2 只算 KB3 §1 已登记的路径；算不出的一律 null + unavailable（规则 2），
「看不见」不得写成「没有」（规则 7）。频带门禁按 A-96 逐通道所在栅格判定，
本切片样本是单栅格，故主栅格口径即全体通道口径。
"""
from __future__ import annotations

import io
import json
import math
import os
import re

import numpy as np
from scipy.signal import welch

from . import c1
from .anchors import assumption_row

SCHEMA = "axiscope.features/1"
NPERSEG_MAX = 2048
NYQUIST_SAFETY = 1.25
FMIN_FLOOR_HZ = 1.0

# KB3 §2.1 逐条 band⊥（Hz）。元规则 R-25 与检测器 R-10 不在此列（A-79）。
BAND_FLOOR = {
    "R-02": 100.0, "R-03": 2000.0, "R-04": 2000.0, "R-05": 20.0, "R-06": 50.0,
    "R-07": 20.0, "R-08": 50.0, "R-09": 150.0, "R-11": 150.0, "R-12": 200.0,
    "R-13": 100.0, "R-14": 100.0,
}
BRANCH_FLOOR = {"R-11#switching_freq": 2000.0}

SEGMENT_KINDS = ["rest", "move", "settling", "dwell", "probing", "path",
                 "homing", "scanning", "curing"]

# A-97 / A-106 / A-98 ③ 的固定 reason 句式。唯一定义在本模块：C2 侧的 `unavailable` 与
# C3 侧的 `not_evaluable` 必须逐字同文，否则两侧对不上账（registration 从这里引）。
WHY_NO_COUNTS = "无 counts 刻度，绝对阈值不可比"
WHY_NO_DATUM = "未做原点对齐，分歧幅值不可比"
WHY_NO_IDENTITY = "接入层未做列间恒等式核对，独立测量数不可信"
WHY_MASQUERADE = "指令轨与候选反馈逐行全等，二者非独立测量"

#: C2 `feedback_integrity.identity_check` 镜像 C1 `audit.identity_check` 的这组键（A-105 ①）。
#: 键集由 C1 单点定义，这里只引用——两处的"核对做没做"必须是同一个答案。
IDENTITY_MIRROR = c1.AUDIT_IDENTITY_KEYS


def counts_scale_missing(meta: dict) -> bool:
    """A-97：`*_counts` 的后缀是历史名，真实单位由 `meta.units_are` 决定。

    `units_are == "counts"` ⟹ 原生刻度就是 counts；`si_native` 且 `counts_per_mm` 非 null
    ⟹ counts 刻度可折算（C2 例 B），绝对阈值可用但报告须注明来源；两者皆无 ⟹ 没有可比的分母，
    **绝对** counts 阈值一律不可套用（把 m 当 counts 判是静默量纲替换，比写 null 危险一个量级）。
    """
    if meta.get("units_are") == "counts":
        return False
    return meta.get("counts_per_mm") is None


#: A-110 ② 的**特征侧**定标表：C1 单位词表里登记为**长度刻度**的原生单位 → 毫米的纯换算因子。
#: `m → mm = ×1000` 是单位定义（国际单位制里 milli 的字面意义），不是本项目的物理容差，
#: 故不引入新数字（A-110 的尺子：这一改要不要新造一个数字？不要）。速度 `m/s`、转矩 `N_m`、
#: 电流 `A` 都**不是**长度刻度——拿非长度通道乘 1000 是量纲错误，一律不产 `*_mm`。
#: 键取值来自 `mapping` 的 C1 单位词表（位置类通道 `unit="m"`），本表只做长度↔mm 的定义换算。
LENGTH_UNIT_TO_MM = {"m": 1000.0, "mm": 1.0, "um": 1e-3, "µm": 1e-3, "nm": 1e-6}

#: A-110 ②/③：si_native 直接定标支强制留痕——锚 `meta.units_are`、句式固定（deliverable 3）。
SI_NATIVE_MM_ANCHOR = "meta.units_are"
SI_NATIVE_MM_STATEMENT = "`*_mm` 由 C1 原生 SI 刻度直接定标，非 counts/counts_per_mm 路径"


def si_native_length_scale(meta: dict, unit) -> bool:
    """A-110 ②：`*_mm` 能否由原生值**纯定标**直接得到（特征侧门禁）。

    与 `counts_scale_missing()`（绝对阈值侧）分权，互不覆盖：
    - 本谓词只管「si_native 且通道在 C1 单位词表里登记为长度刻度」时放开 `*_mm` 定标；
    - `counts_scale_missing()` 继续独立拦绝对 counts 阈值（A-110 ② 阈值维持缺席，
      `20 counts`/`50 counts/s`/`2.0 counts/min` 不折算成 m 级常数），语义原样不动。
    """
    return meta.get("units_are") == "si_native" and unit in LENGTH_UNIT_TO_MM


def _emit_si_native_mm_assumption(meta: dict) -> None:
    """si_native 直接定标支每填一次 `*_mm`，就在 `audit.assumptions` 落**且只落**一行。

    去重保证幂等（同一 meta 上重复 compute 也只有一行），句式与锚固定，读者据此判定
    「这条定标作废时哪条 `*_mm` 跟着塌」。落 `meta.audit.assumptions`（C1 §audit.assumptions
    六式之一，`assertions.py` 会逐行校验锚与 statement）。

    ⚠ 已知边界（登记 A-113，未在此轮修）：`__main__.py` 的顺序是 `c1.build_pack` **先**写
    `meta.json`、`features.compute` **后**跑 ⟹ 本行只存在于内存的 `meta`（与 C2/报告侧），
    **不会**回写盘上的 `meta.json`。当前任何样本都还没走进这支（无 si_native + fe 的仓内样本），
    所以是潜伏缺陷；真有该形态的样本接入时，要么调整写盘顺序、要么在 compute 后补一次 meta 重写。
    """
    rows = meta.setdefault("audit", {}).setdefault("assumptions", [])
    r = assumption_row(SI_NATIVE_MM_ANCHOR, SI_NATIVE_MM_STATEMENT)
    if r not in rows:
        rows.append(r)


def _fe_native_series(ingest: dict):
    """取 fe 的原生刻度序列（si_native 下即米）。C1 无 fe 时返回 None，不猜、不派生。"""
    for src in (ingest.get("canon_series") or {}, ingest.get("series") or {}):
        if "fe" in src:
            return [float(x) for x in src["fe"] if x == x]
    return None


def _ac_rms(xs):
    """波动 RMS（先减均值）。C4 指标表把 `fe_rms_counts` 定义为「全样本 `fe` **去均值** RMS」、
    KB3 §1.1 与 §1.12 的同名特征同口径，而本函数在 A-114 之前算的是原始 RMS（差一个常偏）。
    口径必须是波动量：R-02 的 `fe_p999/fe_rms ≥ 4` 分子是 median 中心的波动量，分母若含常偏
    ⟹ 有稳态误差的样本比值被系统性压低、该判据更容易漏报。被减掉的常偏不是被丢掉，而是另登记在
    `global.fe_mean_counts`（A-106 ② 的同一条纪律：减了必须记，否则把证据当噪声抹掉；
    R-22 签名 ④/⑤ 消费的就是这个均值）。"""
    if not xs:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((v - m) ** 2 for v in xs) / len(xs))


class FeatureError(Exception):
    pass


def _welch(y: np.ndarray, fs: float, f_b: float):
    nperseg = min(NPERSEG_MAX, len(y))
    if nperseg < 16:
        return None
    noverlap = nperseg // 2
    freq, psd = welch(y, fs=fs, window="hann", nperseg=nperseg,
                      noverlap=noverlap, scaling="density")
    df = fs / nperseg
    # A-102 ②：Welch 段数是 KB4 §2.1(c) 样本量行的 `n`，必须显式登记而不是事后反推。
    # scipy 的段数 = (len − noverlap) // (nperseg − noverlap)，短于 nperseg 时补零成 1 段，
    # max(1, …) 与 scipy 行为对齐；登记的是**本次实跑**用掉的段数。
    n_segments = max(1, (len(y) - noverlap) // (nperseg - noverlap))
    keep = freq <= f_b + 1e-9
    return freq[keep], psd[keep], df, nperseg, n_segments


def _spectral_block(series: np.ndarray, fs: float, f_b: float, npy_rel: str) -> tuple[dict, "int | None"]:
    """返回 (降采样预览块, Welch 段数)。段数只在谱真跑出来时非 None（A-102 ②）。"""
    blank = {"freq_hz": [], "psd": [], "npy": npy_rel, "dominant_freq_hz": None,
             "dominant_psd_ratio": None, "tonality_index": None}
    got = _welch(series, fs, f_b)
    if got is None:
        return blank, None
    freq, psd, df, _nperseg, n_segments = got
    band = freq >= max(2.0 * df, FMIN_FLOOR_HZ)
    fb, pb = freq[band], psd[band]
    if len(fb) < 8:
        return blank, None
    f0 = float(fb[int(np.argmax(pb))])
    half = max(2.0 * df, 0.02 * f0)
    sel = (fb >= f0 - half) & (fb <= f0 + half)
    ratio = float(pb[sel].sum() / pb.sum()) if pb.sum() > 0 and sel.any() else None
    tonality = None
    if len(pb) >= 32 and pb.min() > 0:
        sf = math.exp(float(np.mean(np.log(pb)))) / float(np.mean(pb))
        tonality = 1.0 - sf
    n = min(len(freq), 2048)
    return {
        "freq_hz": [round(float(x), 6) for x in freq[:n]],
        "psd": [float(x) for x in psd[:n]],
        "npy": npy_rel,
        "dominant_freq_hz": f0,
        "dominant_psd_ratio": ratio,
        "tonality_index": tonality,
    }, n_segments


def _blocked(f_b: float) -> list[str]:
    out = [r for r, floor in BAND_FLOOR.items() if floor > f_b]
    out += [b for b, floor in BRANCH_FLOOR.items() if floor > f_b]
    return sorted(out)


# ---- C6 事件流读取（C6 §1 词表 / §3 sync / §4 特征组）----
C6_SOURCES = frozenset({"host", "interp", "motion", "drive", "io",
                        "network", "vision", "process", "mes"})
C6_LEVELS = frozenset({"debug", "info", "warn", "error", "alarm"})
C6_SYNC_METHODS = frozenset({"ntp", "host_clock", "trigger_edge",
                             "manual_offset", "unknown"})


def _read_events(pack_dir: str) -> list[dict] | None:
    """读样本包内的 `events.jsonl`（C6 §1）。缺失返回 None；词表越界按边界输入拒收。

    事件流来自现场进程日志，`source`/`level` 拼错会让按 source 分组的计数静默归零，
    所以这里按 C6 §1 的封闭词表校验而不是照单全收。
    """
    path = os.path.join(pack_dir, "events.jsonl")
    if not os.path.isfile(path):
        return None
    rows: list[dict] = []
    for lineno, line in enumerate(io.open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise FeatureError(f"events.jsonl 第 {lineno} 行不是合法 JSON：{exc}") from exc
        src, lvl, t = row.get("source"), row.get("level"), row.get("t")
        if src not in C6_SOURCES:
            raise FeatureError(f"events.jsonl 第 {lineno} 行 source={src!r} 不在 C6 §1 词表内")
        if lvl not in C6_LEVELS:
            raise FeatureError(f"events.jsonl 第 {lineno} 行 level={lvl!r} 不在 C6 §1 词表内")
        if not isinstance(t, (int, float)):
            raise FeatureError(f"events.jsonl 第 {lineno} 行缺数值 t，无法参与任何时间对齐")
        rows.append(row)
    return rows


def _read_sync(meta: dict) -> dict:
    """C6 §3 的 sync 块。§2 把 `machine_context` 放进 meta.json，§3 紧接其后给同一上下文的
    时间同步字段，故按 `meta.sync` 读；缺失时三项一律 null，占位值不由特征层制造（A-103 ③）。"""
    raw = meta.get("sync") or {}
    method = raw.get("method")
    if method is not None and method not in C6_SYNC_METHODS:
        raise FeatureError(f"sync.method={method!r} 不在 C6 §3 词表内")
    tau = raw.get("uncertainty_ms")
    return {"method": method, "verified": raw.get("verified"),
            "uncertainty_ms": tau if isinstance(tau, (int, float)) else None}


def _detail_ms(ev: dict, key: str) -> float | None:
    v = (ev.get("detail") or {}).get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _event_context(events: list[dict], sync: dict, meta: dict,
                   unavail) -> dict:
    """C6 §4 的特征组。计数类只依赖事件流本身，算得出就算；算不出的登记 null 并写明理由。

    `fe_spike_*` 与 `alignment_residual_ms` 不在此列：前者缺权威的 fe 尖峰判据口径
    （rule_table 只消费 `fe_spike_count`，从未定义它怎么数，`fe_p999` 本身也按 C2 规则 2
    刻意未算），后者缺「事件与波形特征如何配对」的定义。按 KB0 §1 不臆造阈值，
    故这两族登记 null 并说明——它们是口径债，不是实现遗漏。
    """
    by_source: dict[str, int] = {}
    for ev in events:
        by_source[ev["source"]] = by_source.get(ev["source"], 0) + 1

    def pick(source: str, codes: tuple[str, ...]) -> list[dict]:
        return [e for e in events if e["source"] == source and e.get("code") in codes]

    host = pick("host", ())
    underrun = pick("interp", ("buffer_underrun",))
    missed = pick("network", ("missed_cycle", "wkc_error"))
    vision = pick("vision", ("result",))
    steps = pick("process", ("step_started", "step_changed"))

    path_spans = [(s["t0"], s["t1"]) for s in meta.get("segments", [])
                  if s.get("kind") == "path"]

    def _max_detail(rows: list[dict], key: str) -> float | None:
        vals = [d for d in (_detail_ms(e, key) for e in rows) if d is not None]
        return max(vals) if vals else None

    lat = sorted(d for d in (_detail_ms(e, "latency_ms") for e in vision) if d is not None)
    p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))] if lat else None

    step_labels = []
    for e in steps:
        d = e.get("detail") or {}
        # 契约要求 step_labels 带 t0/t1/step/recipe 四键，但源事件只给了它有的那些。
        # 缺键一律不补 null：C2 规则 2 下每个 null 都要有一条 unavailable 登记，
        # 而「这段 step 何时结束」源里根本没写，登记成不可评估才是真话。
        row = {"t0": e["t"]}
        for k in ("t1", "step", "recipe"):
            if d.get(k) is not None:
                row[k] = d[k]
        step_labels.append(row)

    # 事件流里根本没有这类事件 ⟹「最大值」在空集上无定义，是 null 不是 0；
    # 反过来「一次都没发生」是实测 0，两者不能混（C1：null ≠ 0）。
    for path, value, why in (
        ("event_context.host_pause_max_ms", _max_detail(host, "duration_ms"),
         "事件流无 source=host 事件（或其 detail 未给 duration_ms）⟹ 空集上无最大值"),
        ("event_context.bus_cycle_hold_max_ms", _max_detail(missed, "hold_ms"),
         "事件流无网络丢周期事件（或其 detail 未给 hold_ms）⟹ 空集上无最大值"),
        ("event_context.vision_result_latency_p95_ms", p95,
         "事件流无 source=vision/result 事件（或其 detail 未给 latency_ms）⟹ p95 无分母"),
    ):
        if value is None:
            unavail(path, why)
    if sync["method"] is None:
        for field, why in (
            ("method", "样本包未登记 sync.method ⟹ 无对齐方式可登记"),
            ("verified", "样本包未登记 sync.verified ⟹ 时钟核验从未发生；填 false 是替现场下结论"),
            ("uncertainty_ms", "无实测时钟不确定度；5 ms 兜底只在门禁处生效并记 audit.assumptions"),
        ):
            unavail(f"event_context.sync.{field}", why)
    if step_labels and any("t1" not in r for r in step_labels):
        unavail("event_context.step_labels[].t1",
                "源事件未给 step 结束时刻 ⟹ 该区间未闭合，不补 null 充数")

    for path, why in (
        ("event_context.fe_spike_count",
         "C2 未定义 fe 尖峰判据口径（rule_table 只消费该字段，从未定义如何数；"
         "fe_p999 本身按 C2 规则 2 刻意未算）⟹ 不臆造阈值"),
        ("event_context.alignment_residual_ms",
         "缺「事件与波形特征如何配对成匹配对」的定义，无权威口径不产残差（A-82 方向）"),
    ):
        unavail(path, why)
    for path in ["event_context.fe_spike_aligned_to_host_pause",
                 "event_context.fe_spike_aligned_to_underrun",
                 "event_context.fe_spike_aligned_to_network_miss",
                 "event_context.fe_spike_aligned_to_vision_result",
                 "event_context.fe_spike_aligned_to_recipe_change"]:
        unavail(path, "对齐计数依赖 fe_spike_count，而该字段口径未定义（C2 不臆造阈值）")

    # C6 §3 规则 2：对齐残差必须 ≤ uncertainty_ms 才允许因果声明。残差为 null 时该不等式
    # 无从判定，故即便 sync.verified=true 也不放行因果——「未核」不得读成「已核且合格」。
    tau = sync.get("uncertainty_ms")
    residual = None
    causal = bool(sync.get("verified") is True and tau is not None and residual is not None
                  and residual <= tau)

    return {
        "available": True,
        "n_events": len(events),
        "n_by_source": dict(sorted(by_source.items())),
        "n_alarm": sum(1 for e in events if e["level"] == "alarm"),
        "host_pause_max_ms": _max_detail(host, "duration_ms"),
        "interp_underrun_count": len(underrun),
        "interp_underrun_during_path": sum(
            1 for e in underrun if any(a <= e["t"] <= b for a, b in path_spans)),
        "network_cycle_miss_count": len(missed),
        "bus_cycle_hold_max_ms": _max_detail(missed, "hold_ms"),
        "vision_result_latency_p95_ms": p95,
        "fe_spike_count": None,
        "fe_spike_aligned_to_host_pause": None,
        "fe_spike_aligned_to_underrun": None,
        "fe_spike_aligned_to_network_miss": None,
        "fe_spike_aligned_to_vision_result": None,
        "fe_spike_aligned_to_recipe_change": None,
        "alignment_residual_ms": residual,
        "sync": sync,
        "causal_claims_permitted": causal,
        "step_labels": step_labels,
    }


#: C1 `meta.source.ingest_profile` 的非 Scope View 取值（`c1.GENERIC_PROFILE`）。
GENERIC_INGEST_PROFILE = "dialect_generic"


def _generic_why(path: str, meta: dict) -> str:
    """非 Scope View 方言的 `unavailable` 原因文本：逐条指向本样本实测到的缺失。

    刻意不复述 Scope View 样本的实测事实（`_tar ≡ _fb`、`bMovingForward` 恒 0、门控后 5 s…）——
    那些对别的导出既不成立也不可核，写进通用路径就是凭空造证据（KB0 §六 检查 23）。
    """
    dialect = (meta.get("source") or {}).get("export_format", "unknown")
    if path.startswith("event_context."):
        return "样本包无 events.jsonl：事件计数/对齐类字段无来源（null ≠ 0，C2 规则 2）"
    if path.startswith("feedback_integrity.identity_check."):
        return ("接入层未执行列间恒等式核对（原因见 meta.audit.identity_check.reason）"
                "⟹ 独立测量计数无本地可复算来源，只能 null 并登记（A-105 ④）")
    if path.startswith("feedback_integrity."):
        return f"本方言（{dialect}）无 canonical 通道映射 ⟹ {path} 无输入（C2 规则 2）"
    if path.startswith("resonance."):
        return ("本方言无 canonical 通道 ⟹ 无谱峰输入，共振候选不可构造；"
                "null 不得读作「未检出谐振」（C2 规则 7）")
    if path.startswith("quality_ref."):
        return ("该量在 meta 中无来源：units_are 与 counts_per_mm 均未定、编码器刻度上游未发布"
                "⟹ 无定标基准（C2 规则 11）")
    if path == "position_quantum_mm":
        return "units_are 与 counts_per_mm 均未定 ⟹ 1/counts_per_mm 无定义（C2 规则 11）"
    return (f"本方言（{dialect}）未经语义映射，present_channels 为空 ⟹ {path} 无输入；"
            "缺输入不等于该现象不存在（C2 规则 2 / 7）")


def _compute_generic(meta: dict, ingest: dict, pack_dir: str) -> dict:
    """D2/D3/D5/D6 的 C2：时基与频带门禁照常算，其余全部 null + unavailable。

    存在的量只有从导出本身直接可得的那些（fs / dt / 抖动 / nan 占比 / 频带门禁）；
    一切需要「列的物理含义」才能算的特征一律 null 并逐路登记理由。
    """
    fs = float(meta["sample_rate_hz"])
    nyq = fs / 2.0
    f_b = nyq / NYQUIST_SAFETY
    blocked = _blocked(f_b)
    present = list(meta["present_channels"])
    q = meta["quality"]
    identity = ingest.get("identity") or {}
    n_samples = q["n_samples"]
    nperseg = min(NPERSEG_MAX, n_samples)

    unavailable: list[dict] = []

    def unavail(feature: str, reason: str, rule: str | None = None, branch: str | None = None):
        row = {"feature": feature, "reason": reason}
        if rule is not None:
            row["rule"] = rule
        if branch is not None:
            row["branch"] = branch
        unavailable.append(row)

    f_b_txt = f"reliable_band_hz = {f_b:.6g} Hz（fs {fs:.6g} Hz、奈奎斯特 {nyq:.6g} Hz）"
    for rid in sorted(r for r in BAND_FLOOR if r in blocked):
        floor = BAND_FLOOR[rid]
        if rid == "R-03":
            unavail("resonance.candidates",
                    f"频带门禁：{f_b_txt} < band⊥ {floor:g} Hz，kHz 量级机械谐振频点在本采样率下"
                    "不可观测；不得读作「未检出谐振」（C2 规则 7 / R-25）", rule=rid)
        elif rid == "R-04":
            unavail("resonance.candidates[].is_double_inertia_pair",
                    f"频带门禁：{f_b_txt} < band⊥ {floor:g} Hz，谐振-反谐振配对在本采样率下不可判；"
                    "且 sensor_config=unknown 使顺序项本就不参与判定（A-68）", rule=rid)
        else:
            unavail(f"freq_limits.blocked_rules#{rid}",
                    f"band⊥ {floor:g} Hz > {f_b_txt}", rule=rid)
    for br in sorted(b for b in BRANCH_FLOOR if b in blocked):
        rid, branch = br.split("#", 1)
        unavail("spectral.cur_q.dominant_freq_hz",
                f"{rid} 的 {branch} 支路要求 f_b ≥ {BRANCH_FLOOR[br]:g} Hz，实得 {f_b:.6g} Hz；"
                "本样本另无 cur_q 通道，该支路双重不可用。R-11 的 150 Hz 谐波支路仍在带内可评，"
                "故只登记支路、不封锁整条规则（A-79）", rule=rid, branch=branch)

    features = {
        "schema": SCHEMA,
        "ref": {"sample_id": ingest["sample_id"], "sha256": ingest["sha256"]},
        "fs_hz": fs,
        "present_channels": present,
        "freq_limits": {
            "fs_hz": fs, "nyquist_hz": nyq, "reliable_band_hz": f_b,
            "blocked_rules": blocked,
            "reason": f"频带门禁按本样本自身的 fs 判定（A-94）：{f_b_txt}；"
                      "blocked_rules 由 band⊥ 与该带宽逐条对账",
        },
        "position_quantum_mm": None,
        "global": {
            "fe_rms_counts": None, "fe_rms_mm": None, "fe_mean_counts": None,
            "fe_p999_counts": None, "fe_max_counts": None, "fe_sign_change_rate_hz": None,
            "cur_q_rms_pct": None, "cur_q_rms_a": None,
            "cur_q_peak_abs_pct": None, "cur_q_peak_abs_a": None,
            "cur_q_saturation_ratio": None,
            "thermal_drift_counts_per_min": None, "thermal_fe_correlation_r": None,
            "reversal_error_counts": None, "backlash_estimate_counts": None,
            "friction_stiction_ratio": None,
        },
        "spectral": {},
        "resonance": {
            "candidates": [], "nyquist_hz": nyq,
            "resolution_hz": fs / nperseg,
            "estimation": {"window": "hann", "nperseg": nperseg, "noverlap": nperseg // 2,
                           "method": "welch", "pair_separation_bins": None,
                           "n_segments": None, "bins_in_band": None},
        },
        "sensor_disagreement": {
            "pairs": [],
            "note": "无 canonical 通道映射 ⟹ 无可配对的两路独立测量，C2 不自配对新列（A-98 ①）",
        },
        "feedback_integrity": {
            "corr_pos_fb_vs_pos_cmd": None, "fe_zero_ratio": None,
            "pos_fb_static_on_move_ratio": None,
            "second_feedback_available": None,
            "masquerade_suspected": None,
            "identity_check": {k: identity.get(k) for k in IDENTITY_MIRROR},
            "note": "本方言未经语义映射：pos_cmd/pos_fb/fe 均未登记，"
                    "identity_check 镜像 C1 的核对摘要（A-105 ①③）",
        },
        "ripple": {"probing": []},
        "crawling": {"low_speed_segments": []},
        "ff_mismatch": {"accel_regime_rms_counts": None, "decel_regime_rms_counts": None,
                        "asymmetry_ratio": None, "fe_vs_accel_corr": None,
                        "residual_slope_vs_jerk_corr": None},
        "encoder": {"per_rev_periodic_present": None, "per_rev_amplitude_counts": None,
                    "harmonics_per_rev": None, "detrended_r2": None,
                    "phase_locked_to_pos_modulo": None},
        "quality_ref": {
            "quantization_step_counts": None, "motor_rev_counts": None,
            "dt_jitter_ratio": q["dt_jitter_ratio"], "nan_ratio": q["nan_ratio"],
            "gap_max_s": q["gap_max_s"],
            "source": "C1 meta.quality 镜像（A-49）；前两项的刻度基准在本样本未定 ⟹ 留 null",
        },
        "step_response": [],
        "tracking": {"path_segments": []},
        "bandwidth": {"position_loop_crossover_hz": None, "phase_margin_deg": None,
                      "gain_margin_db": None, "method": "command_response_h1",
                      "confidence": 0.0,
                      "note": "H1 估计需 pos_cmd 作输入、pos_fb 作输出；本方言两者皆未映射，"
                              "未做任何估计"},
        "event_context": {
            "available": False, "reason": "样本包无 events.jsonl",
            "n_events": None, "n_by_source": None, "n_alarm": None,
            "host_pause_max_ms": None, "interp_underrun_count": None,
            "interp_underrun_during_path": None, "network_cycle_miss_count": None,
            "bus_cycle_hold_max_ms": None, "vision_result_latency_p95_ms": None,
            "fe_spike_count": None, "fe_spike_aligned_to_host_pause": None,
            "fe_spike_aligned_to_underrun": None, "fe_spike_aligned_to_network_miss": None,
            "fe_spike_aligned_to_vision_result": None, "fe_spike_aligned_to_recipe_change": None,
            "alignment_residual_ms": None,
            "sync": {"method": None, "verified": None, "uncertainty_ms": None},
            "causal_claims_permitted": False,
            "step_labels": [],
        },
        "segment_coverage": {k: 0 for k in SEGMENT_KINDS},
        "unavailable": unavailable,
    }

    known = {u["feature"] for u in unavailable}
    for path, value in _feature_paths(features):
        if value is not None or path.startswith("unavailable"):
            continue
        if _is_contract_legal_null(path, features):
            continue
        if path in known or _INDEX_SUFFIX.sub("[]", path) in known:
            continue
        unavail(path, _generic_why(path, meta))

    check_self_consistency(features, meta)
    return features


def compute(meta: dict, ingest: dict, pack_dir: str) -> dict:
    if (meta.get("source") or {}).get("ingest_profile") == GENERIC_INGEST_PROFILE:
        return _compute_generic(meta, ingest, pack_dir)

    fs = float(meta["sample_rate_hz"])
    nyq = fs / 2.0
    f_b = nyq / NYQUIST_SAFETY
    blocked = _blocked(f_b)
    present = list(meta["present_channels"])
    series = ingest["series"]
    has = lambda c: c in present

    f_dir = os.path.join(pack_dir, "features")
    os.makedirs(f_dir, exist_ok=True)

    spectral: dict = {}
    resonance_n_segments: int | None = None
    if has("vel_fb"):
        rel = "features/vel_fb_psd.npy"
        block, nseg = _spectral_block(np.asarray(series["dVelocity_test"], dtype=float),
                                      fs, f_b, rel)
        resonance_n_segments = nseg
        freq = np.asarray(block["freq_hz"], dtype=float)
        psd = np.asarray(block["psd"], dtype=float)
        np.save(os.path.join(pack_dir, rel), np.stack([freq, psd]) if len(freq) else np.zeros((2, 0)))
        spectral["vel_fb"] = block

    unavailable: list[dict] = []

    def unavail(feature: str, reason: str, rule: str | None = None, branch: str | None = None):
        row = {"feature": feature, "reason": reason}
        if rule is not None:
            row["rule"] = rule
        if branch is not None:
            row["branch"] = branch
        unavailable.append(row)

    # —— 频带门禁（A-79 双向对账：blocked_rules 与 unavailable 的 rule/branch 必须一一对应）——
    f_b_txt = f"reliable_band_hz = {f_b:.6g} Hz（fs {fs:.6g} Hz、奈奎斯特 {nyq:.6g} Hz）"
    for rid in sorted(r for r in BAND_FLOOR if r in blocked):
        floor = BAND_FLOOR[rid]
        if rid == "R-03":
            unavail("resonance.candidates",
                    f"频带门禁：{f_b_txt} < band⊥ {floor:g} Hz，kHz 量级机械谐振频点在本采样率下"
                    "不可观测；不得读作「未检出谐振」（C2 规则 7 / R-25）", rule=rid)
        elif rid == "R-04":
            unavail("resonance.candidates[].is_double_inertia_pair",
                    f"频带门禁：{f_b_txt} < band⊥ {floor:g} Hz，谐振-反谐振配对在本采样率下不可判；"
                    f"且 sensor_config=unknown 使顺序项本就不参与判定（A-68）", rule=rid)
        else:
            unavail(f"freq_limits.blocked_rules#{rid}",
                    f"band⊥ {floor:g} Hz > {f_b_txt}", rule=rid)
    for br in sorted(b for b in BRANCH_FLOOR if b in blocked):
        rid, branch = br.split("#", 1)
        unavail("spectral.cur_q.dominant_freq_hz",
                f"{rid} 的 {branch} 支路要求 f_b ≥ {BRANCH_FLOOR[br]:g} Hz，实得 {f_b:.6g} Hz；"
                "本样本另无 cur_q 通道，该支路双重不可用。R-11 的 150 Hz 谐波支路仍在带内可评，"
                "故只登记支路、不封锁整条规则（A-79）", rule=rid, branch=branch)

    # —— 通道缺失导致的不可算：逐条指向实测事实 ——
    # A-110 ② 特征侧：fe 存在且刻度可定标时 `fe_rms_*` 不再一律 null。fe 缺失（本切片
    # Export10 的实测事实：_tar 与 _test 逐行全等 ⟹ 无独立指令轨）时行为与此前逐字一致。
    fe_vals = _fe_native_series(ingest) if has("fe") else None
    fe_rms_counts = _ac_rms(fe_vals) if fe_vals else None
    fe_mean_counts = (sum(fe_vals) / len(fe_vals)) if fe_vals else None
    fe_rms_mm = None
    if fe_rms_counts is not None:
        cpm = meta.get("counts_per_mm")
        fe_unit = (meta.get("channels", {}).get("fe") or {}).get("unit")
        if cpm is not None:
            # C2 规则 3 原式（counts 定标路径）：*_mm = 原生 counts / counts_per_mm，无需额外假设
            fe_rms_mm = fe_rms_counts / cpm
        elif si_native_length_scale(meta, fe_unit):
            # A-110 ②：si_native 且通道登记为长度刻度 ⟹ 纯定标 *_mm = 原生长度 × 单位定义因子
            fe_rms_mm = fe_rms_counts * LENGTH_UNIT_TO_MM[fe_unit]
            _emit_si_native_mm_assumption(meta)
    if fe_rms_counts is None:
        for path in ["global.fe_rms_counts", "global.fe_mean_counts",
                     "global.fe_p999_counts", "global.fe_max_counts"]:
            unavail(path, "无 fe：dPosition_test_tar 与 dPosition_test 逐行全等（0/18,651 行有差）⟹ "
                          "无独立指令轨，C1 派生规则 1 的两个输入缺一（KB2 §4.10）")
        unavail("global.fe_rms_mm", "无 fe ⟹ 两支定标来源都没有输入（C2 规则 3：counts 支需 counts_per_mm，"
                                    "si_native 支需 fe 的原生长度值；A-113）")
    else:
        # fe 已有值：本特征切片算 fe_rms（去均值，A-114）与 fe_mean（常偏，A-114），p999/max 未算（规则 2）
        for path in ["global.fe_p999_counts", "global.fe_max_counts"]:
            unavail(path, "fe 有值，但本特征切片未算 fe_p999/fe_max（C2 规则 2：null 前不得插值）")
        if fe_rms_mm is None:
            unavail("global.fe_rms_mm",
                    "counts_per_mm=null 且通道未登记为长度刻度 ⟹ 无 *_mm 定标来源（C2 规则 3 / A-110 ②）")
    unavail("global.fe_sign_change_rate_hz",
            "无 fe；且量化步长未知，无法判断符号翻转是否由量化决定（KB3 §1.1 该行条件）")
    for path in ["global.cur_q_rms_pct", "global.cur_q_rms_a",
                 "global.cur_q_peak_abs_pct", "global.cur_q_peak_abs_a",
                 "global.friction_stiction_ratio"]:
        unavail(path, "源数据 32 列无任何电流通道（KB2 §4.10 实测：`cur`/`i_q`/`amps` 类列名零命中）")
    unavail("global.cur_q_saturation_ratio",
            "无 cur_q；且 drive.current_limit_a 与 rated_current_a 均为 null ⟹ 无合法分母"
            "（A-80 禁止拿额定电流冒充限流值）")
    unavail("global.thermal_drift_counts_per_min",
            "无 fe；且 dwell/rest 累计时长 ≪ 120 s（触发门控后仅 5.000 s 单一恒速段）")
    unavail("global.thermal_fe_correlation_r", "无 temp 通道")
    unavail("global.reversal_error_counts",
            "无反向段：bMovingForward 全程恒 0、速度通道全程同号 ⟹ 全程单向（KB3 §1.1 该行条件）；"
            "另无 pos_cmd")
    unavail("global.backlash_estimate_counts",
            "无反向段（同上）；且无 pos_cmd ⟹ 滞回带窗口无法定义")
    unavail("position_quantum_mm", "counts_per_mm=null ⟹ 无定标，1/counts_per_mm 无定义（C2 规则 11）")
    unavail("resonance.candidates[].freq_hz",
            "候选定义要求 cur_q（主）与 fe（辅）两路谱峰（KB3 §1.3），本样本两者皆无；"
            "vel_fb 单路不足以构成共振候选（它也可只是速度环自身的动态）")
    unavail("resonance.candidates[].coherence_torque_velocity",
            "相干需 cur_q 与 vel_fb 两路；无 cur_q ⟹ 幅值平方相干不可算（Bendat & Piersol 的 H1 定义）")
    # A-102 ②：`bins_in_band`（KB4 §2.1(c)「带内 bin」行的分母）是**显式登记的量**，
    # 禁止拿 reliable_band_hz / resolution_hz 反推当口径（那会得到 ≈1641，与 KB4 算例 A 的
    # 96 差一个量级——算例用的是峰邻域带，另一套定义）。本切片不产候选峰 ⟹ 无峰邻域窗口，
    # 只能 null + 登记（C2 规则 2），不得猜。
    unavail("resonance.estimation.bins_in_band",
            "resonance.candidates 为空（候选定义需 cur_q（主）与 fe（辅）两路谱峰，本样本两者皆无）"
            "⟹ 峰邻域带内 bin 数无定义；该量为 A-102 ② 显式登记项，不反推")
    # C2 规则 2 的合法 null 清单**不**豁免 `pair_separation_bins`：它与 `n_segments`/`bins_in_band`
    # 同族（规则 10 / A-102 ② 的显式登记项），无候选峰 ⟹ `(freq_hz − antiresonance_freq_hz)
    # /resolution_hz` 没有输入，只能 null + 逐路登记，不得由 resolution_hz 反推。
    unavail("resonance.estimation.pair_separation_bins",
            "无候选峰（resonance.candidates 为空，候选定义需 cur_q（主）与 fe（辅）两路谱峰，"
            "本样本两者皆无）⟹ 峰谷间距 (freq_hz − antiresonance_freq_hz)/resolution_hz 无输入、"
            "峰间距无定义；该量与 n_segments/bins_in_band 同族，属 A-102 ② 显式登记项，"
            "不得由 resolution_hz 反推（C2 规则 2/10）")
    if resonance_n_segments is None:
        unavail("resonance.estimation.n_segments",
                "Welch 谱未跑成（vel_fb 缺失或段长不足）⟹ 无实跑段数可登记；"
                "该量为 A-102 ② 显式登记项，无来源时只能 null + 登记，不反推")
    unavail("spectral.fe.dominant_freq_hz", "无 fe 通道，无谱可取（§4.10：本样本给不出位置跟随误差）")
    unavail("spectral.fe.freq_hz", "无 fe 通道，无谱可取")
    unavail("ripple.probing[]", "需 pos_fb 与 CPR（§1.4）；本样本位置通道全部按 §4.10 拒映为 pos_fb，"
                                 "且 motor_rev_counts=null ⟹ 「每转」无定义")
    unavail("crawling.low_speed_segments[]",
            "触发门控后为单一 2 m/s 恒速段，vel_mean ≫ v_ls = 0.01·vel_cmd_max（该不等式对任何正比例"
            "刻度不变）⟹ 无低速段；另 `*_counts_s` 路径受 counts 刻度缺失影响")
    for path in ["encoder.per_rev_periodic_present", "encoder.per_rev_amplitude_counts",
                 "encoder.harmonics_per_rev", "encoder.detrended_r2",
                 "encoder.phase_locked_to_pos_modulo"]:
        unavail(path, "需 pos_fb；且 CPR 与 encoder_lines 均 null ⟹ 阶次类判据无定义")
    for path in ["step_response[].overshoot_pct", "step_response[].settling_time_ms",
                 "step_response[].rise_time_ms", "step_response[].damping_ratio_estimate",
                 "step_response[].ringing_cycles_to_settle", "step_response[].settle_band_counts",
                 "step_response[].settle_band_pct_of_move"]:
        unavail(path, "无 settling 段（segment_coverage.settling=0，C2 规则 13 要求数组空）；"
                      "且无 pos_cmd/fe，运动学特征不可算")
    for path in ["tracking.path_segments[].fe_rms_counts", "tracking.path_segments[].fe_max_counts",
                 "tracking.path_segments[].corner_error_counts",
                 "tracking.path_segments[].corr_fe_vs_accel",
                 "tracking.path_segments[].corr_fe_vs_jerk",
                 "tracking.path_segments[].velocity_feedforward_pct_applied",
                 "tracking.path_segments[].acceleration_feedforward_pct_applied"]:
        unavail(path, "无 path 段（segment_coverage.path=0）且无 fe；加速度前馈反演另需 cur_q 交叉核验")
    for path in ["ff_mismatch.accel_regime_rms_counts", "ff_mismatch.decel_regime_rms_counts",
                 "ff_mismatch.asymmetry_ratio", "ff_mismatch.fe_vs_accel_corr",
                 "ff_mismatch.residual_slope_vs_jerk_corr"]:
        unavail(path, "需 fe 与 pos_cmd/vel_cmd 的二阶差分；本样本无 fe ⟹ R-15/R-12 支路 B 放弃"
                      "（纪律 1：null 前件不得插值）")
    for path in ["bandwidth.position_loop_crossover_hz", "bandwidth.phase_margin_deg",
                 "bandwidth.gain_margin_db"]:
        unavail(path, "H1 估计需 pos_cmd 作输入、pos_fb 作输出，本样本两者皆无 ⟹ 环路带宽不可估；"
                      "缺输入不等于带宽不足（不得报「裕度足够」）")
    unavail("feedback_integrity.corr_pos_fb_vs_pos_cmd",
            "%s（A-98 ③ 实测：dPosition_test_tar 与 dPosition_test 逐行全等）⟹ 无 pos_cmd，"
            "本字段无两路可算（§4.10 样本卡拒映 _tar 列）" % WHY_MASQUERADE)
    unavail("feedback_integrity.fe_zero_ratio", "无 fe")
    unavail("feedback_integrity.pos_fb_static_on_move_ratio", "无 pos_fb 且无 move 段")
    unavail("sensor_disagreement.pairs[].dominant_order_per_rev", "无 CPR ⟹ 「每转」无定义")
    unavail("quality_ref.quantization_step_counts",
            "A-97 后该字段的刻度是**原生单位**（本例 m），不是臆造的 counts；但接入层没有该列"
            "编码器量子的实测来源——导出文本的最小可分辨差只是打印精度下限，不等于量化步长，"
            "不据以填值（C2 规则 11：量子的唯一用途是拦住亚刻度精度的吹牛，来源不明时它自己就该是 null）")
    unavail("quality_ref.motor_rev_counts", "meta.axis.motor_rev_counts=null（试验台无电机轴刻度）")

    events = _read_events(pack_dir)
    if events is None:
        for path in ["event_context.n_events", "event_context.n_by_source",
                     "event_context.n_alarm", "event_context.host_pause_max_ms",
                     "event_context.interp_underrun_count", "event_context.interp_underrun_during_path",
                     "event_context.network_cycle_miss_count", "event_context.bus_cycle_hold_max_ms",
                     "event_context.vision_result_latency_p95_ms"]:
            unavail(path, "样本包无 events.jsonl：事件计数类字段无来源（不是 0，null ≠ 0）")
        unavail("event_context.fe_spike_count", "无 fe ⟹ 尖峰判据无被检信号")
        for path in ["event_context.fe_spike_aligned_to_host_pause",
                     "event_context.fe_spike_aligned_to_underrun",
                     "event_context.fe_spike_aligned_to_network_miss",
                     "event_context.fe_spike_aligned_to_vision_result",
                     "event_context.fe_spike_aligned_to_recipe_change"]:
            unavail(path, "available=false 时对齐计数字段一律 null（C2 规则 8/14）；"
                          "且 causal_claims_permitted=false，即便有事件也只能作时间共现，不得作因果")
        unavail("event_context.alignment_residual_ms",
                "无事件时钟可与波形时间轴对齐 ⟹ 无匹配对；缺残差不是残差合格（A-82 方向）")
        # A-103 ③：无事件上下文时 sync 三字段一律 null，占位值（`unknown`/`false`/`5.0`）
        # 不该由特征层制造——5 ms 一旦被写死就悄悄参与了 G3/G5 门禁却从不留痕。
        # τ_u 的保守兜底属于门禁层（KB3 §0 纪律 6），由 registration.event_gates 记假设。
        for field, why in (
            ("method", "无事件 ⟹ 无对齐方式可登记；填 unknown 会把「未做」读成「做过并对不上」"),
            ("verified", "无事件 ⟹ 时钟核验从未发生；填 false 是替现场下结论"),
            ("uncertainty_ms", "无实测时钟不确定度；5 ms 兜底只在门禁处生效并记 audit.assumptions"),
        ):
            unavail(f"event_context.sync.{field}", why)
        event_ctx = {
            "available": False, "reason": "样本包无 events.jsonl",
            "n_events": None, "n_by_source": None, "n_alarm": None,
            "host_pause_max_ms": None, "interp_underrun_count": None,
            "interp_underrun_during_path": None, "network_cycle_miss_count": None,
            "bus_cycle_hold_max_ms": None, "vision_result_latency_p95_ms": None,
            "fe_spike_count": None, "fe_spike_aligned_to_host_pause": None,
            "fe_spike_aligned_to_underrun": None, "fe_spike_aligned_to_network_miss": None,
            "fe_spike_aligned_to_vision_result": None, "fe_spike_aligned_to_recipe_change": None,
            "alignment_residual_ms": None,
            "sync": {"method": None, "verified": None, "uncertainty_ms": None},
            "causal_claims_permitted": False,
            "step_labels": [],
        }
    else:
        event_ctx = _event_context(events, _read_sync(meta), meta, unavail)

    coverage = {k: 0 for k in SEGMENT_KINDS}
    for s in meta["segments"]:
        coverage[s["kind"]] = coverage.get(s["kind"], 0) + 1

    pairs = []
    for p in ingest["pairs"]:
        # C2 规则 16（A-106）：幅值类字段只在去常偏残差上算，被减掉的常偏必须另立字段。
        # 缺 datum_offset 的接入（#36 之前的旧包）不得让"180 m 的原点差"冒充成分歧幅值。
        aligned = p.get("datum_offset") is not None
        tag = "%s|%s" % (p["a"], p["b"])
        if not aligned:
            # 规则 2 的逐路口径：`datum_offset` 自己也是这一对的 null 路径，不只 rms/max。
            unavail(f"sensor_disagreement.pairs[{tag}].datum_offset",
                    f"{WHY_NO_DATUM}（C2 规则 16：接入层未登记 pairs[].datum_offset，"
                    "被减掉的常偏因此没有载体）")
            unavail(f"sensor_disagreement.pairs[{tag}].rms_counts",
                    f"{WHY_NO_DATUM}（C2 规则 16：接入层未登记 pairs[].datum_offset）")
            unavail(f"sensor_disagreement.pairs[{tag}].max_counts", WHY_NO_DATUM)
        if p.get("corr") is None:
            unavail(f"sensor_disagreement.pairs[{tag}].corr",
                    "C1 `cross_validation.pairs` 未给出该对的 Pearson r ⟹ 无来源可镜像"
                    "（规则 17 的必填字段只能 null + 登记）")
        pairs.append({"a": p["a"], "b": p["b"], "a_role": p["a_role"], "b_role": p["b_role"],
                      "unit": p["unit"], "datum_offset": p.get("datum_offset"),
                      "rms_counts": p["rms"] if aligned else None,
                      "max_counts": p["max_abs"] if aligned else None,
                      "corr": p.get("corr"),
                      "dominant_order_per_rev": None, "direction": p["direction"]})

    # A-98 ②：第二路反馈 = 至少一对**分属不同物理原理**的通道。同原理的两列分歧只说明
    # 这套传感器内部不稳；原理任一侧未登记（None）也不计入——"未知"与"已知"判成"不同"
    # 是无据推断（mapping.PRINCIPLE 的取值来源：KB7 §硬件真值 + KB2 §3.5 通道卡）。
    # A-105 ④：恒等式核对没跑成（列数/行数不足）时这个计数没有资格存在——
    # 派生列与自己的原料各配一对就能凭空造出"两路分歧"，数出来的独立性是幻觉。
    identity = ingest.get("identity") or {}
    # C2 规则 2 的逐路口径同样作用在 `identity_check` 的镜像上：C1 摘要缺键（旧包，或侧车只给了
    # `performed`/`reason`）时镜像出来的是整数个 null 计数，规则 18 把它们读作「核对没跑成」，
    # 每个 null 都得有自己的行。`reason` 是规则 2 点名的合法 null（`performed = true` 时按
    # C1 派生规则 9 的形状就是 null），反过来 performed != true 而无原因文本才是欠账。
    for k in IDENTITY_MIRROR:
        if k == "reason":
            continue
        if identity.get(k) is None:
            unavail(f"feedback_integrity.identity_check.{k}",
                    "C1 `audit.identity_check` 摘要未承载该计数（旧包缺键或侧车只给 performed/reason）"
                    "⟹ 镜像只能 null；规则 18：摘要整块缺键视同 performed = false")
    if identity.get("performed") is not True and identity.get("reason") is None:
        unavail("feedback_integrity.identity_check.reason",
                "performed != true 却无原因文本（A-105 ④ 要求写清核对为什么跑不了）⟹ null 并登记；"
                "C2 规则 2 的合法 null 豁免只在 performed = true 时成立")
    checked = identity.get("performed") is True
    second_fb = any(p["a_principle"] and p["b_principle"]
                    and p["a_principle"] != p["b_principle"] for p in ingest["pairs"]) \
        if checked else None
    if not checked:
        unavail("feedback_integrity.second_feedback_available",
                "%s（C1 `audit.identity_check.performed=false`：%s）（A-105 ④）"
                % (WHY_NO_IDENTITY, identity.get("reason") or "接入层未提供 identity 结果"))
    masquerade = any(m["n_rows_differ"] == 0 for m in ingest.get("masquerade", []))

    q = meta["quality"]
    features = {
        "schema": SCHEMA,
        "ref": {"sample_id": ingest["sample_id"], "sha256": ingest["sha256"]},
        "fs_hz": fs,
        "present_channels": present,
        "freq_limits": {
            "fs_hz": fs, "nyquist_hz": nyq, "reliable_band_hz": f_b,
            "blocked_rules": blocked,
            "reason": "kHz 级机械谐振与开关频率类判据不可评估：" + f_b_txt
                      + "，奈奎斯特以下无该频段信息",
        },
        "position_quantum_mm": None,
        "global": {
            "fe_rms_counts": fe_rms_counts, "fe_rms_mm": fe_rms_mm,
            "fe_mean_counts": fe_mean_counts, "fe_p999_counts": None,
            "fe_max_counts": None, "fe_sign_change_rate_hz": None,
            "cur_q_rms_pct": None, "cur_q_rms_a": None,
            "cur_q_peak_abs_pct": None, "cur_q_peak_abs_a": None,
            "cur_q_saturation_ratio": None,
            "thermal_drift_counts_per_min": None, "thermal_fe_correlation_r": None,
            "reversal_error_counts": None, "backlash_estimate_counts": None,
            "friction_stiction_ratio": None,
        },
        "spectral": spectral,
        "resonance": {
            "candidates": [], "nyquist_hz": nyq,
            "resolution_hz": fs / min(NPERSEG_MAX, meta["quality"]["n_samples"]),
            "estimation": {"window": "hann", "nperseg": min(NPERSEG_MAX, meta["quality"]["n_samples"]),
                           "noverlap": min(NPERSEG_MAX, meta["quality"]["n_samples"]) // 2,
                           "method": "welch", "pair_separation_bins": None,
                           # A-102 ② 三个显式登记量之二：n_segments 取本次 Welch 实跑段数；
                           # bins_in_band 无候选峰 ⟹ null + unavailable（见上）。
                           "n_segments": resonance_n_segments, "bins_in_band": None},
        },
        "sensor_disagreement": {
            "pairs": pairs,
            "note": "三对分歧全部来自 C1 `cross_validation.pairs`（C2 不自配对新列，A-98 ①）；"
                    "rms/max 在去常偏残差上算，被减掉的原点差登记在 `datum_offset`（规则 16 / A-106）；"
                    "`*_counts` 后缀是历史名，真实单位取 `unit` = m（A-97 ①）",
        },
        "feedback_integrity": {
            "corr_pos_fb_vs_pos_cmd": None, "fe_zero_ratio": None,
            "pos_fb_static_on_move_ratio": None,
            "second_feedback_available": second_fb,
            "masquerade_suspected": masquerade,
            "identity_check": {k: identity.get(k) for k in IDENTITY_MIRROR},
            "note": "second_feedback_available 由「至少一对分属不同物理原理」推出（A-98 ②：电机轴编码器 "
                    "× 光学 ASCO × 电感 LSV，KB7 §硬件真值）；masquerade_suspected 由指令候选与反馈"
                    "逐行全等实测推出（A-98 ③），二者都不再依赖 `pos_fb` 是否被映射。"
                    "`identity_check` 是 C1 `audit.identity_check` 的镜像（A-105 ①③）：派生列与全等"
                    "孪生的丢弃侧已在 C1 配对时剔除，此处的计数与分歧都是核对之后的口径",
        },
        "ripple": {"probing": []},
        "crawling": {"low_speed_segments": []},
        "ff_mismatch": {"accel_regime_rms_counts": None, "decel_regime_rms_counts": None,
                        "asymmetry_ratio": None, "fe_vs_accel_corr": None,
                        "residual_slope_vs_jerk_corr": None},
        "encoder": {"per_rev_periodic_present": None, "per_rev_amplitude_counts": None,
                    "harmonics_per_rev": None, "detrended_r2": None,
                    "phase_locked_to_pos_modulo": None},
        "quality_ref": {
            "quantization_step_counts": None, "motor_rev_counts": None,
            "dt_jitter_ratio": q["dt_jitter_ratio"], "nan_ratio": q["nan_ratio"],
            "gap_max_s": q["gap_max_s"],
            "source": "C1 meta.quality 镜像（A-49）；本样本 units_are=si_native 且 counts_per_mm=null "
                      "⟹ 绝对 *_counts 路径无分母、置 null（A-97 ②）；刻度无关的比值/相关判据与"
                      "带单位的 pairs 幅值不受影响（A-97 ③）",
        },
        "step_response": [],
        "tracking": {"path_segments": []},
        "bandwidth": {"position_loop_crossover_hz": None, "phase_margin_deg": None,
                      "gain_margin_db": None, "method": "command_response_h1",
                      "confidence": 0.0,
                      "note": "由 pos_cmd/pos_fb 的 H1 估计，非注入激励，仅供定性；"
                              "本样本两个输入皆无，未做任何估计"},
        "event_context": event_ctx,
        "segment_coverage": coverage,
        "unavailable": unavailable,
    }
    check_self_consistency(features, meta)
    return features


def _dig(obj: dict, path: str):
    """点号路径取值。`x[]` 表示对数组逐元素取后续路径，返回元素值列表。"""
    parts = path.split(".")
    has_array = any(p.endswith("[]") for p in parts)
    cur = [obj]
    for part in parts:
        nxt = []
        for c in cur:
            if part.endswith("[]"):
                name = part[:-2]
                if not isinstance(c, dict) or name not in c or not isinstance(c[name], list):
                    return None
                nxt.extend(c[name])
            else:
                if not isinstance(c, dict) or part not in c:
                    return None
                nxt.append(c[part])
        cur = nxt
        if not cur:
            return []
    if has_array:
        return cur
    return cur[0] if cur else None


def _has_value(val) -> bool:
    if val is None or val == [] or val == {}:
        return False
    if isinstance(val, list):
        return any(_has_value(v) for v in val)
    if isinstance(val, dict):
        return any(_has_value(v) for v in val.values())
    return True


def check_resonance_counts(features: dict) -> None:
    """A-102 ②：三个「显式登记的样本量」必须键在场，有值则必须可复算。

    KB4 §2.1(c) 的样本量行（Welch 段 / 带内 bin / 3 dB 宽）由这三处承载；键缺失不是
    「没有这个量」而是契约缺陷——侧车注入只是过渡口径（A-102 ③），载体本身必须在 C2。
    `three_db_width_bins` 的复算式取 rule_table `n_source_recipes.three_db_width_bins`
    登记的 `round(freq_hz / quality_factor_estimate / resolution_hz)`（A-76 同纪律）；
    **`bins_in_band` 不适用该式**——它登记的是峰邻域窗口，禁止由频带上下沿反推（A-102 ②）。
    """
    est = features["resonance"]["estimation"]
    for k in ("n_segments", "bins_in_band"):
        if k not in est:
            raise FeatureError(f"resonance.estimation 缺 {k} —— A-102 ②：KB4 §2.1(c) 样本量行的 "
                               "n 必须有 C2 载体，缺键是契约缺陷，不是『没有这个量』")
        v = est[k]
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 1):
            raise FeatureError(f"resonance.estimation.{k}={v!r}：有值必须是 ≥1 的整数段/计数"
                               "（null 表示未登记并须伴随 unavailable，0 不是合法值）")
    res = features["resonance"]
    for i, c in enumerate(res.get("candidates") or []):
        if "three_db_width_bins" not in c:
            raise FeatureError(f"resonance.candidates[{i}] 缺 three_db_width_bins 键（A-102 ②）")
        v, f0 = c["three_db_width_bins"], c.get("freq_hz")
        q, r = c.get("quality_factor_estimate"), res.get("resolution_hz")
        if v is not None and None not in (f0, q, r) and v != round(f0 / q / r):
            raise FeatureError(f"resonance.candidates[{i}].three_db_width_bins={v} 与 rule_table "
                               f"配方 round(freq_hz/quality_factor_estimate/resolution_hz)="
                               f"{round(f0 / q / r)} 不符（A-76：登记值必须逐格可复算）")


#: C2 顶层块名（=`compute()` 产出的特征块骨架，见本文件 `features` 字典）。
#: `unavailable[].feature` 必须以其中之一起头——这是 C2 规则 2「点分全路径」的机器口径。
#: 保留 `present_channels` / `segment_coverage` 两个簿记键是因为 `crawling.` / `ff_mismatch.` /
#: `bandwidth.` 三块**必须**在列：引擎自己的产物就在逐条登记它们（`report.py` 与 `c3validate.py`
#: 都按字符串集合比对这些行），漏一个就会把合规行判成违规行。
C2_TOP_BLOCKS = frozenset({
    "position_quantum_mm", "freq_limits", "global", "spectral", "resonance",
    "sensor_disagreement", "feedback_integrity", "ripple", "crawling", "ff_mismatch",
    "encoder", "quality_ref", "step_response", "tracking", "bandwidth", "event_context",
    "segment_coverage", "present_channels",
    # `ref` 也留作合法前缀：包指纹缺来源时它自己就是一个要登记的 null 路径，
    # 若不认这个前缀，(a) 要行、(b) 禁行，两处检查会互相矛盾。
    "ref",
})

#: 数组下标/模板后缀（`[0]`、`[]`、`[pos_fb|LSV_1]`）——逐路比对前统一归一成 `[]`。
_INDEX_SUFFIX = re.compile(r"\[[^\]]*\]")


def _feature_paths(node, prefix: str = ""):
    """遍历特征包，产出 (点分路径, 叶子值)。数组元素路径带 `[i]`，嵌套数组带 `[i][j]`。

    空数组/空对象不产出路径（`resonance.candidates = []` 不是"某个特征为 null"，
    它自己的登记走族级行，见 C2 规则 13）。
    """
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _feature_paths(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _feature_paths(v, f"{prefix}[{i}]")
    else:
        yield prefix, node


def _is_contract_legal_null(path: str, features: dict) -> bool:
    """C2 规则 2「合法 null 清单」的三条豁免——**逐字**对应契约原文，契约没有的豁免这里也不许有。

    契约原文（C2 §硬性约定 规则 2）：
      ① `feedback_integrity.identity_check.reason`——`performed = true` 时它按 C1 派生规则 9 的形状
         就是 `null`（该槽承载的是「核对为什么跑不了」）；
      ② 各块的 `note` 说明字段（路径最后一段为 `note`）；
      ③ `sensor_disagreement.pairs[].dominant_order_per_rev`——规则 17 原句
         「`dominant_order_per_rev` 无 CPR 时为 `null`」，故豁免只在包内 CPR（`quality_ref.motor_rev_counts`）
         确实缺席时成立。
    ★ `resonance.estimation.pair_separation_bins` 契约**显式不豁免**（它与 `n_segments`/`bins_in_band`
    同族，A-102 ② 显式登记项）⟹ 不在本函数里。
    """
    if path.split(".")[-1] == "note":
        return True
    if path == "feedback_integrity.identity_check.reason":
        return _dig(features, "feedback_integrity.identity_check.performed") is True
    if path.startswith("sensor_disagreement.pairs[") \
            and path.split(".")[-1] == "dominant_order_per_rev":
        return features.get("quality_ref", {}).get("motor_rev_counts") is None
    return False


def check_null_accounting(features: dict) -> None:
    """C2 规则 2 的逐路账务（加载期，违反即拒样本）：两类检查。

    (a) **每个 null 都要有同名行**：包里每一个 `null` 的 JSON 路径，若不属规则 2 点名的合法 null
        清单，就必须能在 `unavailable[].feature` 找到同名全路径行。
        **数组元素内的 null 纳入本条**，依据有二：①契约写的义务粒度是"任何算不出的特征……逐路"，
        而 `tracking.path_segments[].corner_error_counts` 与 `global.*` 一样是判据输入（KB3 §1 的
        特征索引就是按 `[]` 元素路径列的），把它排除等于给元素级 null 开后门；②引擎与夹具本来就
        用两种写法表达同一族（引擎产族级 `[]` 模板行、手抄夹具写下标级行），所以比对前两侧都归一
        成 `[]`——这正是 `_dig()`（规则 13/14 与 `report.py` 的 gate_reason 都在用）认的口径。
        归一只影响"这行是否算同名"，不影响 CAP-5：`c3validate.py` 仍按逐字字符串比对证据路径。
        唯一不参与扫描的子树是 `unavailable` 自身——账本就是账本，拿账本的键去销账是循环。
        本条只管**至少有一行**，不管**只有一行**：账目粒度是 `(feature, rule/branch)`（A-119），
        因为 A-79 的 `blocked_rules`↔`unavailable` 一一对账按该粒度逐条比，同一路径多行是契约要求的
        （`kb4_case_b` 的 `resonance.candidates` 因 R-03、R-04 各有一行）——本函数不把重复行判为缺陷。
    (b) **行名必须是点分全路径**：`unavailable[].feature` 的第一段（剥掉 `[…]` 后缀）必须是
        `C2_TOP_BLOCKS` 之一。短名行（`cur_q_rms_a`）不是风格问题：C3 的 CAP-5 与
        `assertions.py` 的 blocked_rules↔unavailable 对账都是字符串集合比对，短写永不命中 ⟹ 假绿。
        本条**先于** (a) 判：形状不合规的行会同时伪装成"某个 null 没记账"，先报 (a) 就会把
        两处缺陷里不相干的那一处摆到错误消息上。
    """
    rows = [str(u.get("feature")) for u in features["unavailable"]]
    bad = [r for r in rows if _INDEX_SUFFIX.sub("", r.split(".")[0]) not in C2_TOP_BLOCKS]
    if bad:
        raise FeatureError(
            "C2 规则 2：unavailable[].feature 必须是**点分全路径**（含顶层块名前缀，如 "
            "`global.cur_q_rms_a`），短写行永不命中 C3 的 CAP-5 与 blocked_rules 对账 ⟹ 假绿。"
            f"不合规的行={bad}")
    known = set(rows) | {_INDEX_SUFFIX.sub("[]", r) for r in rows}
    unrecorded = []
    for path, value in _feature_paths(features):
        if value is not None or path == "unavailable" or path.startswith("unavailable."):
            continue
        if _is_contract_legal_null(path, features):
            continue
        if path in known or _INDEX_SUFFIX.sub("[]", path) in known:
            continue
        unrecorded.append(path)
    if unrecorded:
        raise FeatureError(
            f"C2 规则 2（null 不是 0）：{len(unrecorded)} 个 null 特征路径没有同名的 unavailable 行："
            + "、".join(unrecorded)
            + " ——且不在规则 2 逐条点名的合法 null 清单（identity_check.reason / *.note / "
              "sensor_disagreement.pairs[].dominant_order_per_rev）里")


def check_self_consistency(features: dict, meta: dict) -> None:
    """C2 规则 12/14 的加载期自检：值与 unavailable 互斥、三处 fs 自洽、预览非空约束。"""
    rows = {r["feature"] for r in features["unavailable"]}
    for path in sorted(rows):
        val = _dig(features, path)
        if _has_value(val):
            raise FeatureError(f"特征 {path} 同时有值与 unavailable 行（C2 规则 14 互斥失败）")
    check_resonance_counts(features)
    check_null_accounting(features)
    fs = features["fs_hz"]
    for p in features["sensor_disagreement"]["pairs"]:
        if not p.get("unit"):
            raise FeatureError("sensor_disagreement.pairs 缺 unit —— A-97 ③：`*_counts` 是历史名，"
                               "数值不携单位就进报告等于静默量纲替换")
        if any(p.get(k) not in ("canonical", "extra") for k in ("a_role", "b_role")):
            raise FeatureError("sensor_disagreement.pairs[].a_role/b_role 取值非法（A-98 ①）")
        if (p.get("rms_counts") is not None or p.get("max_counts") is not None) \
                and p.get("datum_offset") is None:
            raise FeatureError("分歧幅值非 null 却无 datum_offset（C2 规则 16 / A-106：减了不记"
                               "等于把安装原点证据当噪声抹掉，且读者无法复核残差口径）")
    if abs(features["freq_limits"]["fs_hz"] - fs) > 1e-9:
        raise FeatureError("freq_limits.fs_hz 与顶层 fs_hz 不自洽（C2 规则 12）")
    ic = features["feedback_integrity"]["identity_check"]
    if ic.get("performed") is not True \
            and features["feedback_integrity"]["second_feedback_available"] is not None:
        raise FeatureError("恒等式核对未执行却填了 second_feedback_available（A-105 ④："
                           "没核对过列间恒等式，独立测量数就是没资格的数，只能 null）")
    if abs(features["freq_limits"]["nyquist_hz"] - fs / 2.0) > 1e-9:
        raise FeatureError("nyquist_hz != fs/2")
    if abs(features["freq_limits"]["reliable_band_hz"] - fs / 2.0 / NYQUIST_SAFETY) > 1e-9:
        raise FeatureError("reliable_band_hz != nyquist/1.25")
    if abs(features["resonance"]["nyquist_hz"] - fs / 2.0) > 1e-9:
        raise FeatureError("resonance.nyquist_hz 与主栅格不自洽（A-96 规则 4）")
    for name, block in features["spectral"].items():
        if not block["freq_hz"] and block["dominant_freq_hz"] is not None:
            raise FeatureError(f"spectral.{name} 预览为空但主频非 null（C2 规则 14）")
        if len(block["freq_hz"]) != len(block["psd"]):
            raise FeatureError(f"spectral.{name} 预览的 freq/psd 长度不一致")
    ec = features["event_context"]
    expect = bool(ec["sync"]["verified"]) and (
        ec["alignment_residual_ms"] is not None
        and ec["alignment_residual_ms"] <= ec["sync"]["uncertainty_ms"])
    if ec["causal_claims_permitted"] != expect:
        raise FeatureError("causal_claims_permitted 与 sync/残差的合取不等价（C2 规则 8）")
    if features["present_channels"] != meta["present_channels"]:
        raise FeatureError("C2 present_channels 与 C1 meta 不一致（C2 §1.14）")
    if not 0.0 <= features["bandwidth"]["confidence"] <= 0.6:
        raise FeatureError("bandwidth.confidence 上界 0.6 被越界"
                           "（C2 规则 12：非注入激励的 H1 估计不该更自信）")
    cov = features["segment_coverage"]
    if cov["move"] == 0 and features["tracking"]["path_segments"]:
        raise FeatureError("segment_coverage.move=0 却有 path_segments（C2 规则 13）")
    if cov["settling"] == 0 and features["step_response"]:
        raise FeatureError("segment_coverage.settling=0 却有 step_response（C2 规则 13）")
    if cov["probing"] == 0 and features["ripple"]["probing"]:
        raise FeatureError("segment_coverage.probing=0 却有 ripple.probing（C2 规则 13）")