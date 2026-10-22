"""KB4 §2 置信度与证据模型：确定性数值层。

纪律：本模块只做 §2.1–§2.5 的算术，不读 C2 快照、不做规则路由、不产假设（INV-16）。
内部一律全精度，只在 `display()`（序列化层）取 2 位小数（C3 硬性规则 15）。
`n_ref` / `conf(f)` / `band⊥` 由调用方逐条显式带入，本模块不查规则表（避免与
`rule_table.json` 的形成过程耦合）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# —— §2.1 / §2.2 固定的常数（改动须升版本号并重跑全量，KB4 §2.2 末段）——
RHO_SATURATION = 4.0          # g 的饱和点：KB3 全库通用 6 dB ≈ 4 倍
G_CATEGORICAL = 0.85          # 布尔/枚举无裕度
W_SMAX = 0.55
W_SREST = 0.45
A_CON_CEILING = 0.5           # §2.2 `A_con = min(0.5, Σ v_j)`
N_FACTOR_AT_REF = 0.6         # n = n_ref
N_FACTOR_FULL_RATIO = 4.0     # 4 倍及以上满分
BANDWIDTH_CONF_CEILING = 0.6  # KB3 §1.10 锁定，实现不得提高（§2.1(b)）
NEAR_NYQUIST_RATIO = 0.8      # INV-2：f0 ≥ 0.8·f_N 先过 R-10
BAND_WEAK_START_RATIO = 0.5   # §2.1(d)：0.5·f_b < f0 ≤ f_b
BAND_WEAK_FACTOR = 0.80
VJ_STRONG = 0.20              # ρ′ ≥ 2
VJ_HIT = 0.10                 # 1 ≤ ρ′ < 2
VJ_SHAPE_ABSENT = 0.05        # ρ′ < 1
VJ_DEPENDENCY_NULL = 0.00     # INV-4：不算反证
VJ_STRONG_RHO = 2.0
ABSENT_DEDUCTION_PER_REASON = 0.05
ABSENT_DEDUCTION_MAX_REASONS = 4  # §2.2 的 min(4, ·)
ABSENT_DEDUCTION_TOTAL_MAX = 0.20  # CAP-10 与 §2.2 合并后的总扣上限（§2.5 行 487）

RHO_PRIME_TOL_FLOOR = 5e-4        # 小 ρ′ 的绝对容差
RHO_PRIME_TOL_RELATIVE = 0.01     # KB 表格的 ρ′ 常由上一格的 3 位取整值再除（算例 B 反证 2）

FAMILY_LABELS = frozenset({"software_induced_error"})
SLUG_PREFIXES = ("mechanical_", "electrical_", "software_induced_")

COMPARATORS_UP = (">=", ">")
COMPARATORS_DOWN = ("<=", "<")
COMPARATORS_CAT = ("==", "!=")


class ConfidenceError(Exception):
    """KB4 §2 的结构违规：一律大声失败，不静默降级。"""


class DependencyNull(ConfidenceError):
    """INV-4：依赖为 null ⟹ 该边不可通行；null 既不当 0 也不当 1。"""

    def __init__(self, feature: str, what: str = "value"):
        self.feature = feature
        super().__init__(f"依赖为 null（INV-4）：{feature} 的 {what} 缺失，规则放弃，不得代入 0/1")


class BandBlocked(ConfidenceError):
    """INV-1 / CAP-5：越带 ⟹ 该证据**不存在**（剪枝 + 登记），不是 `S = 0`。"""

    def __init__(self, feature: str, rule_id: str, reason: str, detail: str):
        self.feature = feature
        self.rule_id = rule_id
        self.reason = reason
        super().__init__(f"频带阻塞（INV-1/CAP-5，{reason}）：{feature} [{rule_id}] —— {detail}；"
                         "正确处置是 unavailable + blocked_rules 登记，禁写「未检出」")


class RuleNotFired(ConfidenceError):
    """§2.1(a)：ρ < 1 ⟹ 规则未命中，不产生该支持证据（反证侧同 ρ′<1 走 −0.05 档，见 §2.4）。"""

    def __init__(self, feature: str, rule_id: str, rho: float | None):
        self.feature = feature
        self.rho = rho
        detail = "形态未出现" if rho is None else f"ρ = {rho:.6g} < 1"
        super().__init__(f"规则未命中（{detail}）：{feature} [{rule_id}] 不构成支持证据")


class SampleBelowReference(ConfidenceError):
    """§2.1(c)：`n < n_ref` 时 C2 本该输出 null，故模型里不该出现该状态。"""

    def __init__(self, feature: str, n: float, n_ref: float):
        super().__init__(f"样本量低于 KB3 必要上下文下限：{feature} n={n:g} < n_ref={n_ref:g}"
                         "（C2 应给 null，不得反算 n_factor < 0.6）")


class RefutationPenaltyViolation(ConfidenceError):
    """C3 规则 15：`penalty` 是 `rho_prime` 的离散档位函数，不是自由参数。"""

    def __init__(self, feature: str, rho_prime: float | None, expected: float, declared: float,
                 note: str):
        self.feature = feature
        self.expected_penalty = expected
        self.declared_penalty = declared
        super().__init__(f"反证扣分与自身 ρ′ 不符（规则 15）：{feature} ρ′={rho_prime!r} ⟹ "
                         f"档位 v_j = {expected:.2f}，声明 penalty = {declared:.2f}（{note}）")


class InsufficientEvidence(ConfidenceError):
    """INV-10：进 `hypotheses[]` 的叶须 ≥2 条支持证据；不足是结构违规，不得凑数。"""

    def __init__(self, fault_mode: str, k: int):
        self.fault_mode = fault_mode
        super().__init__(f"INV-10：{fault_mode} 只有 {k} 条支持证据（k<2），移入 considered，不计算 C")


class NotALeaf(ConfidenceError):
    """INV-16 / A-18：门与边只产登记义务；族级标签不是叶子。"""


class MissingFeatureScale(ConfidenceError):
    """§2.1(a) 的 ε_f（threshold ≤ 0 支）与 §2.1(d) 的 band⊥ 必须由调用方登记，不得默认。"""


@dataclass(frozen=True)
class FrequencyContext:
    """`freq_limits` 中与 §2.1(d)/INV-1/INV-2 相关的三个量（KB4 §0 行 19）。"""

    fs_hz: float
    reliable_band_hz: float                    # f_b = freq_limits.reliable_band_hz
    nyquist_hz: float | None = None            # f_N，缺省按 fs/2（定义，非假定值）

    @property
    def nyquist(self) -> float:
        return self.fs_hz / 2.0 if self.nyquist_hz is None else float(self.nyquist_hz)


@dataclass(frozen=True)
class Evidence:
    """一条支持证据 = `(feature, value, operator, threshold, rule_id, source)` + §2.1 的四个因子输入。"""

    feature: str
    value: float | bool | None
    operator: str
    threshold: float | bool | None
    rule_id: str
    n: float | None = None                 # 该特征的样本量（C2 侧事实）
    n_ref: float | None = None             # KB3「必要上下文」下限，调用方逐条带入
    conf: float | None = None              # §2.1(b)：实测类 1.0；估计类取特征自带 confidence
    freq_hz: float | None = None           # f0；非频域判据为 None
    band_floor_hz: float | None = None     # 该规则的 band⊥
    eps: float | None = None               # §2.1(a) 的 ε_f，仅 threshold ≤ 0 / value ≤ 0 支需要
    source: str = ""

    def __post_init__(self) -> None:
        if self.operator not in COMPARATORS_UP + COMPARATORS_DOWN + COMPARATORS_CAT:
            raise ConfidenceError(f"未知 operator：{self.operator!r}")


@dataclass(frozen=True)
class Refutation:
    """一条反证：`rho_prime` 由 `(value, operator, threshold)` 按 §2.1(a) 重算，`penalty` 取其档位。"""

    feature: str
    value: float | bool | None
    operator: str
    threshold: float | bool | None
    rule_id: str
    penalty: float
    rho_prime: float | None = None
    eps: float | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if self.operator not in COMPARATORS_UP + COMPARATORS_DOWN + COMPARATORS_CAT:
            raise ConfidenceError(f"未知 operator：{self.operator!r}")


@dataclass(frozen=True)
class Hypothesis:
    """一个待评假设及其 CAP 命中结果。CAP 触发判定在规则引擎侧（只读 C2 字段），本层只吃算术后果。"""

    fault_mode: str
    supporting_evidence: list[Evidence] = field(default_factory=list)
    contradicting_evidence: list[Refutation] = field(default_factory=list)
    ceilings: list[float] = field(default_factory=list)     # min 语义，§2.2 行 352
    multiplicative: list[float] = field(default_factory=list)  # CAP-7 类乘性惩罚（×0.70）

    def __post_init__(self) -> None:
        if self.fault_mode in FAMILY_LABELS:
            raise NotALeaf(f"族级标签 {self.fault_mode!r} 不是 KB0 §2 的 slug，禁入 hypotheses（A-18/INV-16）")
        if not self.fault_mode.startswith(SLUG_PREFIXES):
            raise NotALeaf(f"{self.fault_mode!r} 不属于三方归因族的 slug 形态（C3 规则 10/11）")


@dataclass(frozen=True)
class Score:
    """§2.2 的全链中间量，一律全精度；2 位小数只在 `display()` 里发生。"""

    s_max: float
    s_rest: float
    a_sup: float
    a_con: float
    c_mid: float
    c: float
    k: int


# ---------------------------------------------------------------- §2.1 单条证据强度

def _ratio(feature: str, value, operator: str, threshold, eps: float | None) -> float:
    """§2.1(a) 的裕度倍数 ρ（反证侧同式，得 ρ′）。"""
    if value is None:
        raise DependencyNull(feature, "value")
    if operator in COMPARATORS_UP:
        if threshold is None:
            raise DependencyNull(feature, "threshold")
        if threshold > 0:
            return float(value) / float(threshold)
        if eps is None:
            raise MissingFeatureScale(f"{feature} 的 threshold ≤ 0 支需要 ε_f（§2.1(a)）")
        return (float(value) - float(threshold)) / float(eps)
    if operator in COMPARATORS_DOWN:
        if threshold is None:
            raise DependencyNull(feature, "threshold")
        denom = float(value)
        if denom <= 0:
            if eps is None:
                raise MissingFeatureScale(f"{feature} 的 ≤ 向判据值为 0/负，需要 §2.1(a) 的 ε_f 作分母下限")
            denom = max(denom, float(eps))
        return float(threshold) / denom
    raise ConfidenceError(f"{feature} 的 operator {operator!r} 不属于 ρ 型判据")


def saturation_g(rho: float) -> float:
    return 0.5 + 0.5 * min(1.0, math.log10(rho) / math.log10(RHO_SATURATION))


def sample_factor(n: float, n_ref: float, feature: str) -> float:
    if n_ref is None or n is None:
        raise MissingFeatureScale(f"{feature} 的 n/n_ref 未登记（§2.1(c) 要求逐条给出样本量与下限）")
    if n < n_ref:
        raise SampleBelowReference(feature, n, n_ref)
    ratio = n / n_ref
    return min(1.0, N_FACTOR_AT_REF
                + (1.0 - N_FACTOR_AT_REF) * math.log10(ratio) / math.log10(N_FACTOR_FULL_RATIO))


def feature_confidence(feature: str, conf: float | None) -> float:
    """§2.1(b)：实测类 1.0；估计类取自带 confidence；`bandwidth.*` 上界 0.6 不可抬高。"""
    if conf is None:
        raise DependencyNull(feature, "conf")
    if not 0.0 <= conf <= 1.0:
        raise ConfidenceError(f"{feature} 的 conf = {conf!r} 越出 [0,1]")
    if feature.startswith("bandwidth.") or ".bandwidth." in feature:
        return min(conf, BANDWIDTH_CONF_CEILING)
    return float(conf)


def band_factor(ev: Evidence, ctx: FrequencyContext) -> float:
    """§2.1(d) 只算「削弱」；「阻塞」按 INV-1 抛错，由规则引擎登记为 unavailable + blocked_rules。"""
    if ev.freq_hz is None:
        return 1.0
    if ev.band_floor_hz is None:
        raise MissingFeatureScale(f"{ev.feature} 是频域判据，band⊥ 未登记则无法执行 INV-1 门禁")
    if ctx.reliable_band_hz < ev.band_floor_hz:
        raise BandBlocked(ev.feature, ev.rule_id, "reliable_band_below_band_floor",
                          f"f_b = {ctx.reliable_band_hz:g} Hz < band⊥ = {ev.band_floor_hz:g} Hz")
    if ev.freq_hz > ctx.reliable_band_hz:
        raise BandBlocked(ev.feature, ev.rule_id, "above_reliable_band",
                          f"f0 = {ev.freq_hz:g} Hz > f_b = {ctx.reliable_band_hz:g} Hz")
    if ev.freq_hz >= NEAR_NYQUIST_RATIO * ctx.nyquist:
        raise BandBlocked(ev.feature, ev.rule_id, "near_nyquist_r10_vetting",
                          f"f0 = {ev.freq_hz:g} Hz ≥ 0.8·f_N = {NEAR_NYQUIST_RATIO * ctx.nyquist:g} Hz，"
                          "未经 R-10 伪峰排除不得进入 mechanical_* 叶")
    if ev.freq_hz <= BAND_WEAK_START_RATIO * ctx.reliable_band_hz:
        return 1.0
    return BAND_WEAK_FACTOR


def evidence_strength(ev: Evidence, ctx: FrequencyContext) -> float:
    """`S(e) = g(ρ) × conf(f) × n_factor(n/n_ref) × band_factor(f0)` ∈ [0,1]（§2.1）。"""
    if ev.operator in COMPARATORS_CAT:
        if ev.value is None or ev.threshold is None:
            raise DependencyNull(ev.feature, "value/threshold")
        matched = bool(ev.value) == bool(ev.threshold)
        fired = matched if ev.operator == "==" else not matched
        if not fired:
            raise RuleNotFired(ev.feature, ev.rule_id, None)
        g = G_CATEGORICAL
    else:
        rho = _ratio(ev.feature, ev.value, ev.operator, ev.threshold, ev.eps)
        if rho < 1.0:
            raise RuleNotFired(ev.feature, ev.rule_id, rho)
        g = saturation_g(rho)
    return g * feature_confidence(ev.feature, ev.conf) \
        * sample_factor(ev.n, ev.n_ref, ev.feature) * band_factor(ev, ctx)


def margin_ratio(ev: Evidence) -> float | None:
    """供报告层回填 `rho` 列；categorical 与 null 依赖不给 ρ。"""
    if ev.operator in COMPARATORS_CAT or ev.value is None:
        return None
    return _ratio(ev.feature, ev.value, ev.operator, ev.threshold, ev.eps)


# ---------------------------------------------------------------- §2.4 反证扣分

def refutation_penalty(rho_prime: float | None) -> float:
    if rho_prime is None:
        return VJ_DEPENDENCY_NULL
    if rho_prime >= VJ_STRONG_RHO:
        return VJ_STRONG
    if rho_prime >= 1.0:
        return VJ_HIT
    return VJ_SHAPE_ABSENT


def _rho_prime_agrees(declared: float, recomputed: float) -> bool:
    return abs(declared - recomputed) <= max(RHO_PRIME_TOL_FLOOR,
                                             RHO_PRIME_TOL_RELATIVE * abs(recomputed))


def check_refutation(rf: Refutation) -> float:
    """返回 `v_j`；`penalty` 必须等于由自身 `(value, op, threshold)` 重算 ρ′ 后落到的档位。"""
    if rf.value is None or rf.threshold is None:
        if rf.penalty != VJ_DEPENDENCY_NULL:
            raise RefutationPenaltyViolation(rf.feature, None, VJ_DEPENDENCY_NULL, rf.penalty,
                                             "依赖为 null ⟹ 不算反证（INV-4）")
        return VJ_DEPENDENCY_NULL
    rho_prime = _ratio(rf.feature, rf.value, rf.operator, rf.threshold, rf.eps)
    if rf.rho_prime is not None and not _rho_prime_agrees(rf.rho_prime, rho_prime):
        raise RefutationPenaltyViolation(
            rf.feature, rho_prime, refutation_penalty(rho_prime), rf.penalty,
            f"声明 rho_prime = {rf.rho_prime:g} 与重算 ρ′ = {rho_prime:.6g} 不符，"
            "penalty 也就不是自身 ρ′ 的档位")
    expected = refutation_penalty(rho_prime)
    if abs(expected - rf.penalty) > 1e-9:
        raise RefutationPenaltyViolation(rf.feature, rho_prime, expected, rf.penalty,
                                         "v_j 只能取 {0.20, 0.10, 0.05, 0.00}")
    return expected


# ---------------------------------------------------------------- §2.2 聚合

def aggregate(h: Hypothesis, ctx: FrequencyContext) -> Score:
    k = len(h.supporting_evidence)
    if k < 2:
        raise InsufficientEvidence(h.fault_mode, k)

    strengths = [evidence_strength(ev, ctx) for ev in h.supporting_evidence]
    s_max = max(strengths)
    rest = [s for i, s in enumerate(strengths) if i != strengths.index(s_max)]
    s_rest = sum(rest) / len(rest)
    a_sup = W_SMAX * s_max + W_SREST * s_rest

    a_con = min(A_CON_CEILING, sum(check_refutation(rf) for rf in h.contradicting_evidence))
    c_mid = a_sup * (1.0 - a_con)
    c = min([c_mid, *h.ceilings])
    for factor in h.multiplicative:
        c *= factor
    return Score(s_max=s_max, s_rest=s_rest, a_sup=a_sup, a_con=a_con, c_mid=c_mid, c=c, k=k)


# ---------------------------------------------------------------- §2.2 / CAP-10 顶层扣减

def distinct_blocked_by(not_evaluable_rows: list[dict]) -> list[str]:
    """A-73 / C3 规则 16：分母是去重后的独立缺席原因，不是登记行数。

    族级行（`family`）与它覆盖的叶行（`fault_mode`）通常同一个 `blocked_by`，因此天然只计一次；
    族级行不是假设（INV-16），这里只做键名结构检查。
    """
    reasons: list[str] = []
    for row in not_evaluable_rows:
        has_family = "family" in row
        has_fault = "fault_mode" in row
        if has_family == has_fault:
            raise NotALeaf("not_evaluable 行的登记键二选一：族级写 `family`、逐模式写 `fault_mode`"
                           f"（A-51），本行={sorted(row)}")
        if has_fault and row["fault_mode"] in FAMILY_LABELS:
            raise NotALeaf(f"族级标签 {row['fault_mode']!r} 只能写在 `family` 键（A-18）")
        blocked_by = row.get("blocked_by")
        if not blocked_by:
            raise ConfidenceError("not_evaluable 行缺 `blocked_by` 稳定键名，无法按独立原因去重（规则 16）")
        if blocked_by not in reasons:
            reasons.append(blocked_by)
    return reasons


def absent_deduction_factor(not_evaluable_rows: list[dict]) -> float:
    """§2.2 与 CAP-10 的合并式：每独立缺席原因 −5%，同族额外行不重复计，总扣 ≤ 20%。"""
    reasons = distinct_blocked_by(not_evaluable_rows)
    deduction = ABSENT_DEDUCTION_PER_REASON * min(ABSENT_DEDUCTION_MAX_REASONS, len(reasons))
    return 1.0 - min(ABSENT_DEDUCTION_TOTAL_MAX, deduction)


def overall_confidence(primary: Score | float, not_evaluable_rows: list[dict]) -> float:
    c_primary = primary.c if isinstance(primary, Score) else float(primary)
    return c_primary * absent_deduction_factor(not_evaluable_rows)


def display(x: float) -> float:
    """唯一的 2 位小数出口（序列化/展示层）；计算链上不得取整。"""
    return round(x, 2)


# —— KB4 §2.9 tie-break：`C` 同（±RANK_TIE_BAND）即按并列，落下一键 ——

RANK_TIE_BAND = 0.01
# 0.45 − 0.44 在二进制浮点里是 0.010000000000000009；带宽判等必须留一点余量，
# 否则同带的两个值会因为浮点尾数被判成不同带，并列带就变成了"大多数时候不并列"。
_BAND_EPS = 1e-9


def rank_band_c(rows) -> dict:
    """把 (index, severity, c_display) 列表压成 {index: 该行所在并列带的队长 C}。

    §2.9 原文「`C` 同（±0.01）⟹ 比受影响面」是成对表述，实现里必须先落成**划分**才可排序。
    划分取队长锚定：同 severity 内按 C 降序扫，本行当队长时把其后所有 `C ≥ 队长C − 0.01` 的行
    收进同一带，遇到第一条差过带宽的即停（后面只会更远）。不取链式扩张——0.441/0.445/0.449
    在链式下会并成一带，队长锚定下 0.449 另起一带，两种划法都自洽，但只有队长锚定能写成
    一句话让人照着重算。

    返回队长 C 而非带号，是因为队长 C 本身就单调可排序：不同带按队长 C 降序即得带序，
    同带取同一个值即得并列。排序键因此仍是普通元组，不需要比较器。

    `c_display` 必须传**产物里的两位显示值**（`display()` 的出口），引擎与校验器才在同一刻度上：
    引擎若拿未取整的原始 C 划带、校验器拿两位值划带，同一对假设会落进不同的带，
    正是 A-116 ① 记的那处两侧不一致。
    """
    grouped: dict = {}
    for index, severity, c in rows:
        grouped.setdefault(severity, []).append((index, c))
    leaders: dict = {}
    for members in grouped.values():
        members.sort(key=lambda t: (-t[1], t[0]))
        start = 0
        while start < len(members):
            leader_c = members[start][1]
            end = start
            while end < len(members) and leader_c - members[end][1] <= RANK_TIE_BAND + _BAND_EPS:
                leaders[members[end][0]] = leader_c
                end += 1
            start = end
    return leaders
