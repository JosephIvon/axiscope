"""KB5 §4 七段 jerk 受限 S 曲线 + §4.3 采样栅格对齐 + §4.5 自检不变量 I1–I12。

来源纪律（§4.1）：借鉴 `motion_lab.py` 的**七段对称结构**与
`a_eff = min(a_max, √(v·j))` 的加速度受 jerk 约束这一物理上限；
段状态传播、闭式解法、栅格对齐与全部自检不变量都是本文件自己写的。
不复制任何代码行。

§4.3 的读法（本文件采用，已在报告的歧义清单里登记）：
「把 `t1,t2,t3,tv` 各自取整到最近采样拍」是**条件句**（「若要求整除则」），
它前面挂着前提「若要求 `segments[].kind` 的边界精确可辨」。本文件的取舍是
**只把 `t1 = t3` 量化到采样拍**（jerk 斜坡边界 —— 这正是 C2 的
`accel_regime_rms` / `decel_regime_rms` 分域所依赖的边界），
`t2` / `tv` 由「优先保 D」连续解出，栅格错位按 §4.3 的**明确要求**记进
`boundary_residual_ms`（不变量 I9）。本合成器自己写 `meta.segments`，
分段不靠从波形反推，所以「边界精确可辨」这个前提不成立。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

TWO_PI = 2.0 * math.pi

REGIME_I = "I"            # 梯形速度（t2 > 0, tv > 0）
REGIME_II = "II"          # 纯 jerk 三角（t2 = 0, tv > 0）
REGIME_III_A = "III-a"    # 无匀速、jerk 主导（a_e < a_max）
REGIME_III_B = "III-b"    # 无匀速、a_max 主导


@dataclass
class Segment:
    """一段 jerk 恒值的段（§4.2 的七段）。终值由 `advance()` 从初值推出。"""

    jerk: float
    dur: float
    t0: float
    a0: float
    v0: float
    x0: float

    @property
    def t1(self) -> float:
        return self.t0 + self.dur

    @property
    def a1(self) -> float:
        return self.a0 + self.jerk * self.dur

    @property
    def v1(self) -> float:
        return self.v0 + self.a0 * self.dur + 0.5 * self.jerk * self.dur ** 2

    @property
    def x1(self) -> float:
        return (self.x0 + self.v0 * self.dur + 0.5 * self.a0 * self.dur ** 2
                + self.jerk * self.dur ** 3 / 6.0)


@dataclass
class SCurve:
    D: float                 # 行程（带符号，mm）
    v_max: float
    a_max: float
    j_max: float
    fs: float
    sign: float = 1.0
    t1: float = 0.0
    t2: float = 0.0
    t3: float = 0.0
    tv: float = 0.0
    v_p: float = 0.0
    a_e: float = 0.0
    T_total: float = 0.0
    D_calc: float = 0.0
    regime: str = REGIME_I
    segments: list[Segment] = field(default_factory=list)
    boundary_residual_ms: float = 0.0
    cruise_t0: float = 0.0
    cruise_t1: float = 0.0

    # ---- 解析求值（§4.3：落盘值是「段解析式在该时刻的真值」，不是段平均）----
    def state(self, t: float) -> tuple[float, float, float]:
        tt = max(0.0, min(t, self.T_total))
        for s in self.segments:
            if tt <= s.t1 + 1e-15 or s is self.segments[-1]:
                dt = max(0.0, tt - s.t0)
                x = s.x0 + s.v0 * dt + 0.5 * s.a0 * dt * dt + s.jerk * dt ** 3 / 6.0
                v = s.v0 + s.a0 * dt + 0.5 * s.jerk * dt ** 2
                a = s.a0 + s.jerk * dt
                return x, v, a
        return self.D, 0.0, 0.0

    def pos(self, t: float) -> float:
        return self.state(t)[0]

    def vel(self, t: float) -> float:
        return self.state(t)[1]

    def acc(self, t: float) -> float:
        return self.state(t)[2]

    def jerk_segments(self) -> list[dict]:
        return [{"jerk": s.jerk, "dur": s.dur, "t0": s.t0} for s in self.segments
                if s.dur > 0.0]

    def boundaries(self) -> list[float]:
        out: list[float] = []
        acc = 0.0
        for s in self.segments:
            acc += s.dur
            out.append(acc)
        return out


# ------------------------------------------------------------------ 半程解析式

def _x_half(v_p: float, a_e: float, t1: float, j: float) -> tuple[float, float]:
    """给定 `(v_p, a_e, t1)` 的半程：返回 `(t2, x_h)`（§4.2 的 x1+x2+x3）。

    `t2` 由 `v_p` 闭式给出（`max(0, (v_p − 2v1)/a_e)`），不做迭代。
    """
    v1 = a_e * t1 / 2.0
    t2 = max(0.0, (v_p - 2.0 * v1) / a_e) if a_e > 0.0 else 0.0
    v2 = v1 + a_e * t2
    x1 = j * t1 ** 3 / 6.0
    x2 = v1 * t2 + a_e * t2 ** 2 / 2.0
    x3 = v2 * t1 + a_e * t1 ** 2 / 2.0 - j * t1 ** 3 / 6.0
    return t2, x1 + x2 + x3


def _x_half_free_t1(v_p: float, a: float, j: float) -> tuple[float, float, float, float]:
    """**未对齐栅格**的半程：`(a_e, t1, t2, x_h)`，按 §4.2 的 `a_e = min(a, √(v_p j))`。"""
    a_e = min(a, math.sqrt(max(v_p, 0.0) * j))
    t1 = a_e / j if j > 0 else 0.0
    t2, x_h = _x_half(v_p, a_e, t1, j)
    return a_e, t1, t2, x_h


def solve_vp(D_half: float, a: float, j: float, v_hi: float) -> tuple[float, float, float]:
    """无匀速（III）情形的 `v_p` 反解：解 `x_h(v_p) = D_half`（该式单调 ⟹ 二分）。

    返回 `(v_p, a_e, t1)`。二分 80 次 ⟹ 端点相对误差 ≲ 2⁻⁸⁰。
    §4.2 把 AUDIT 的「4 组工况端点误差 <1e-6 mm」标成**二手转录**（A-32），
    因此本函数**不据此声称已核对**；判定权在 §4.5 的不变量与黄金向量。
    """
    lo, hi = 1e-15, max(v_hi, 1.0)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _x_half_free_t1(mid, a, j)[3] < D_half:
            lo = mid
        else:
            hi = mid
    v_p = 0.5 * (lo + hi)
    a_e, t1, _t2, _xh = _x_half_free_t1(v_p, a, j)
    return v_p, a_e, t1


# ------------------------------------------------------------------ 轨迹构造

def build(D: float, v_max: float, a_max: float, j_max: float, fs: float,
          grid_align_t1: bool = True) -> SCurve:
    """构造一条七段轨迹（§4.2 + §4.3）。

    步骤：
      1. 先按未对齐的解析式解一次（拿到 `a_e`、`t1`、情形分类）；
      2. 把 `t1 = t3` 量化到最近采样拍，`a_e = j·t1`（**上界侧硬约束**：`a_e ≤ min(a_max, √(v_max j))`）；
      3. 若量化后的 `t1` 使最小可达半程 `j·t1³` 超过 `D/2`（行程太短），逐步减拍；
         减到 1 拍仍不可行 ⟹ 放弃栅格对齐走解析解，并把错位记进 `boundary_residual_ms`；
      4. 重解 `v_p`（无匀速）或 `tv`（有匀速）**保证位移闭合**（§4.3「优先保 D」）。

    情形判定（§4.2）：
      I   `v_p = v_max`、`t2 > 0`、`tv > 0`
      II  `t2 = 0`（`a_e = √(v_p j) < a_max`）、`tv > 0`
      III 无匀速（`tv = 0`）：`v_p < a²/j` ⟹ III-a；否则 III-b
    """
    if D == 0.0:
        raise ValueError("D = 0 不是移动；静止段不生成 S 曲线")
    s = 1.0 if D > 0 else -1.0
    Dabs = abs(D)
    Ts = 1.0 / fs
    a_e_cap = min(a_max, math.sqrt(v_max * j_max))

    aligned = bool(grid_align_t1)
    a_e = t1 = 0.0
    if aligned:
        a_e0, t1_0, _t2_0, _xh0 = _peak_profile(Dabs, v_max, a_max, j_max)
        n1 = max(1, int(round(t1_0 / Ts)))
        while n1 > 1:
            t1c = n1 * Ts
            a_ec = min(j_max * t1c, a_e_cap)
            # 可行性：该 t1 下最小可达的半程 = a_e·t1 = j·t1³，且峰值速度 a_e·t1 不得超 v_max
            if a_ec * t1c <= Dabs / 2.0 and a_ec * t1c <= v_max:
                break
            n1 -= 1
        t1 = n1 * Ts
        a_e = min(j_max * t1, a_e_cap)
        if a_e * t1 > Dabs / 2.0 or a_e * t1 > v_max:
            aligned = False                      # 1 拍也不可行 ⟹ 放弃对齐（残差如实记录）
    if not aligned:
        a_e, t1, v_p, t2, _xh = _peak_profile_full(Dabs, v_max, a_max, j_max)
        _t2, x_h = _x_half(v_p, a_e, t1, j_max)
        tv = max(0.0, (Dabs - 2.0 * x_h) / v_p)
        regime = REGIME_I if t2 > 0.0 else REGIME_II
        return _assemble(D, s, v_max, a_max, j_max, fs, a_e, t1, t2, t1, tv, v_p, regime)

    v_lo = a_e * t1                     # 该 t1 下可达的最小峰值速度（2·v1 = a_e·t1）
    t2_at_max, x_h_at_max = _x_half(v_max, a_e, t1, j_max)

    if 2.0 * x_h_at_max <= Dabs:
        # v_max 处可以匀速：梯形（t2>0）或纯 jerk 三角（t2 == 0）
        v_p = v_max
        t2, x_h = t2_at_max, x_h_at_max
        tv = (Dabs - 2.0 * x_h) / v_p
        regime = REGIME_I if t2 > 0.0 else REGIME_II
    else:
        # 无匀速：反解 v_p（受 v_lo 夹逼 ⟹ 保证 t2 ≥ 0 且峰值不超调）
        D_half = Dabs / 2.0
        v_hi = max(v_lo, v_max)
        v_p = _bisect_vp_fixed_t1(D_half, a_e, t1, j_max, v_lo, v_hi)
        t2, x_h = _x_half(v_p, a_e, t1, j_max)
        tv = 0.0
        regime = REGIME_III_B if a_e >= a_max * (1.0 - 1e-12) else REGIME_III_A

    t3 = t1
    return _assemble(D, s, v_max, a_max, j_max, fs, a_e, t1, t2, t3, tv, v_p, regime)


def _peak_profile_full(Dabs: float, v_max: float, a_max: float, j_max: float
                       ) -> tuple[float, float, float, float, float]:
    """**未对齐栅格**的完整解析解：返回 `(a_e, t1, v_p, t2, x_h)`。

    情形 II 在此路径下是可达的：`a_e = √(v_p j)` 且 `v_p = v_max` ⟹ `t2 = 0`。
    （★ 见模块 docstring：情形 II 与 §4.3 的**严格栅格对齐**在离散栅格上一般不可同时满足，
    故黄金向量 GV-3 走这条路径，`boundary_residual_ms` 如实记录。）
    """
    v_pj = a_max * a_max / j_max
    a_e0 = min(a_max, math.sqrt(v_max * j_max))
    t1_0 = a_e0 / j_max
    t2_0, xh_0 = _x_half(v_max, a_e0, t1_0, j_max)
    if 2.0 * xh_0 <= Dabs:
        return a_e0, t1_0, v_max, t2_0, xh_0
    if v_max < v_pj:
        v_p = v_max
    else:
        v_p, a_e0, t1_0 = solve_vp(Dabs / 2.0, a_max, j_max, v_max)
    t2_0, xh_0 = _x_half(v_p, a_e0, t1_0, j_max)
    return a_e0, t1_0, v_p, t2_0, xh_0


def _assemble(D: float, s: float, v_max: float, a_max: float, j_max: float,
              fs: float, a_e: float, t1: float, t2: float, t3: float, tv: float,
              v_p: float, regime: str) -> SCurve:
    """把时序装配成七段 + 逐段状态传播（§4.2 的段状态传播，镜像由 `s` 一次性给出）。"""
    T_total = 2.0 * (t1 + t2 + t3) + tv
    segs: list[Segment] = []
    for jerk, dur in ((+j_max, t1), (0.0, t2), (-j_max, t3), (0.0, tv),
                      (-j_max, t1), (0.0, t2), (+j_max, t3)):
        if dur > 0.0:
            segs.append(Segment(jerk=jerk * s, dur=dur, t0=0.0, a0=0.0, v0=0.0, x0=0.0))
    x_acc = v_acc = a_acc = t_acc = 0.0
    for q in segs:
        q.t0, q.x0, q.v0, q.a0 = t_acc, x_acc, v_acc, a_acc
        x_acc, v_acc, a_acc = q.x1, q.v1, q.a1
        t_acc += q.dur

    sc = SCurve(D=D, v_max=v_max, a_max=a_max, j_max=j_max, fs=fs, sign=s,
                t1=t1, t2=t2, t3=t3, tv=tv, v_p=v_p * s, a_e=a_e * s, T_total=T_total,
                D_calc=x_acc, regime=regime, segments=segs)
    sc.cruise_t0 = t1 + t2
    sc.cruise_t1 = t1 + t2 + tv
    sc.boundary_residual_ms = boundary_residual(segs, fs)
    return sc


def _peak_profile(Dabs: float, v_max: float, a_max: float, j_max: float
                  ) -> tuple[float, float, float, float]:
    """未对齐栅格下的 `(a_e, t1, t2, x_h)`（给栅格量化挑起点用）。"""
    a_e, t1, _vp, t2, xh = _peak_profile_full(Dabs, v_max, a_max, j_max)
    return a_e, t1, t2, xh


def _bisect_vp_fixed_t1(D_half: float, a_e: float, t1: float, j: float,
                        lo: float, hi: float) -> float:
    """固定 `t1` 的 III 反解（II-b 的分段结构：区间 `[v_lo, v_hi]` 上二分 80 次）。"""
    if _x_half(lo, a_e, t1, j)[1] >= D_half:
        return lo
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _x_half(mid, a_e, t1, j)[1] < D_half:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def boundary_residual(segs: list[Segment], fs: float) -> float:
    """段边界与采样时刻的最大错位 `ε = max |t_i − t_k|`（§4.3）。"""
    Ts = 1.0 / fs
    worst = 0.0
    for q in segs:
        for b in (q.t0, q.t1):
            worst = max(worst, abs(b - round(b / Ts) * Ts))
    return worst * 1000.0


# ------------------------------------------------------------------ §4.5 不变量

def invariants(sc: SCurve, fs: float, quant_counts_per_mm: float | None = None,
               meta_move_boundaries: list[float] | None = None) -> list[dict]:
    """§4.5 的 I1–I12。任一失败即**拒绝生成样本**（不是「记录警告继续」）。

    这十二条是**解析 / 自洽校验**（A-31）：位移闭合、情形 II 的恒等式、jerk 段和为零、
    段边界连续都是代数恒等式或构造性质，通过后只报「按构造成立」。
    """
    out: list[dict] = []
    D_target = sc.D
    D_calc = sc.D_calc
    scale = max(abs(D_target), abs(sc.v_max), sc.a_max)

    # I1 位移闭合
    tol_counts = 0.05
    resid_counts = abs(D_calc - D_target)
    if quant_counts_per_mm:
        out.append(_iv("I1", resid_counts <= tol_counts,
                       f"|D_calc − D| = {resid_counts:.3e} mm = "
                       f"{resid_counts * quant_counts_per_mm:.3e} counts"
                       f"（容差 {tol_counts} counts）"))
    else:
        rel = resid_counts / max(1e-30, abs(D_target))
        out.append(_iv("I1", rel <= 1e-9,
                       f"|D_calc − D| = {resid_counts:.3e} mm，counts_per_mm=null ⟹ "
                       f"按相对容差 1e-9 判定（实测 {rel:.3e}）"))

    # I2 速度端点
    v0_end = abs(sc.vel(0.0))
    v_end = abs(sc.vel(sc.T_total))
    out.append(_iv("I2", v0_end <= 1e-12 and v_end <= 1e-9 * sc.v_max,
                   f"|v(0)| = {v0_end:.3e}；|v(T_total)| = {v_end:.3e} ≤ 1e-9·v_max = "
                   f"{1e-9 * sc.v_max:.3e}"))

    # I3 加速度端点
    a0_end = abs(sc.acc(0.0))
    a_end = abs(sc.acc(sc.T_total))
    out.append(_iv("I3", max(a0_end, a_end) <= 1e-9 * sc.a_max,
                   f"|a(0)| = {a0_end:.3e}，|a(T)| = {a_end:.3e} ≤ 1e-9·a_max = "
                   f"{1e-9 * sc.a_max:.3e}"))

    # I4 各段边界连续（C²，jerk 按设计跳变）
    worst = 0.0
    for q1, q2 in zip(sc.segments, sc.segments[1:]):
        worst = max(worst, abs(q1.x1 - q2.x0), abs(q1.v1 - q2.v0), abs(q1.a1 - q2.a0))
    out.append(_iv("I4", worst <= 1e-9 * scale,
                   f"段边界最大不连续 = {worst:.3e}（相对量级 {worst / scale:.3e}，门限 1e-9）；"
                   f"jerk 只在 {len(sc.segments) - 1} 个内部边界跳变（设计允许）"))

    # I5 恒等式：t2 == 0 时 x_h == v_p·t1（解析校验，相对误差 < 1e-12）
    if sc.t2 == 0.0:
        _t2, x_h = _x_half(abs(sc.v_p), abs(sc.a_e), sc.t1, sc.j_max)
        lhs, rhs = abs(x_h), abs(sc.v_p) * sc.t1
        rel = abs(lhs - rhs) / max(abs(rhs), 1e-30)
        out.append(_iv("I5", rel < 1e-12,
                       f"x_h = {lhs:.12g}，v_p·t1 = {rhs:.12g}，相对误差 {rel:.3e}（门槛 1e-12）"
                       f"｜情形 {sc.regime}，t2 = 0 ⟹ 恒等式适用"))
    else:
        out.append(_iv("I5", True,
                       f"情形 {sc.regime}（t2 = {sc.t2:.6g} s > 0），x_h = v_p·t1 的恒等式"
                       f"按 §4.2 只对 t2 = 0 的情形（II / III）成立 ⟹ 不适用，按构造成立"))

    # I6 jerk 分段和 ∫j dt = 0
    net = sum(q.jerk * q.dur for q in sc.segments)
    out.append(_iv("I6", abs(net) <= 1e-9 * sc.a_max,
                   f"Σ∫j dt = {net:.3e}（净加速度变化），容差 1e-9·a_max = {1e-9 * sc.a_max:.3e}"))

    # I7 限幅遵守
    peak_a = max(max(abs(q.a0) for q in sc.segments), max(abs(q.a1) for q in sc.segments))
    peak_v = max(max(abs(q.v0) for q in sc.segments), max(abs(q.v1) for q in sc.segments))
    jerks = sorted({round(abs(q.jerk), 12) for q in sc.segments if q.dur > 0.0})
    ok7 = (peak_a <= sc.a_max * (1 + 1e-9) and peak_v <= sc.v_max * (1 + 1e-9)
           and len(jerks) == 1 and jerks[0] <= sc.j_max * (1 + 1e-9))
    out.append(_iv("I7", ok7,
                   f"peak|a| = {peak_a:.6g} ≤ a_max = {sc.a_max:.6g}；"
                   f"peak|v| = {peak_v:.6g} ≤ v_max = {sc.v_max:.6g}；"
                   f"|j| 取值集合 = {jerks}（应恰为 [j_max] = [{sc.j_max:g}]）"))

    # I8 jerk 段数 ∈ {2,4,6}
    n_jerk = len([q for q in sc.segments if abs(q.jerk) > 0 and q.dur > 0])
    out.append(_iv("I8", n_jerk in (2, 4, 6),
                   f"非零 jerk 段数 = {n_jerk}（允许 {{2,4,6}}）；"
                   f"总段数 = {len(sc.segments)}，退化段（时长 0）不进入 segment 列表"))

    # I9 时间栅格
    on_grid = sum(1 for b in (sc.t1, sc.t3)
                  if abs(b - round(b * sc.fs) / sc.fs) < 1e-12)
    out.append(_iv("I9", True,
                   f"boundary_residual_ms = {sc.boundary_residual_ms:.6f}（已记录于 "
                   f"truth.command_profile.boundary_residual_ms）；t1/t3 中 {on_grid}/2 "
                   f"条落在采样栅格上；t2/tv 为「优先保 D」的连续解（§4.3 允许）"))

    # I10 符号：单向移动内单调（反向用 s = −1 整条镜像，不做「镜像后再差分」）
    mono = True
    prev = sc.pos(0.0)
    n_probe = 4000
    for k in range(1, n_probe + 1):
        x = sc.pos(sc.T_total * k / n_probe)
        if (x - prev) * sc.sign < -1e-12:
            mono = False
            break
        prev = x
    out.append(_iv("I10", mono,
                   f"sign = {sc.sign:+.0f}，{n_probe + 1} 点采样上 d(pos_cmd) 与 sign 同号；"
                   f"反向移动用整条镜像构造，未做镜像后差分"))

    # I11 量级
    ratio_ok = 0.0 <= sc.tv <= sc.T_total + 1e-15
    out.append(_iv("I11", ratio_ok and sc.T_total > 0.0,
                   f"tv = {sc.tv:.6g} s，0 ≤ tv ≤ T_total = {sc.T_total:.6g} s"
                   f"（tv/T_total = {sc.tv / sc.T_total:.4f}）；情形 = {sc.regime}；"
                   f"tv < 0 会直接报错，不静默改 D"))

    # I12 位移-分段一致：meta.segments 的 move 边界与本轨迹的采样对齐边界逐点一致
    if meta_move_boundaries is None:
        out.append(_iv("I12", True,
                       "未传入 meta 边界（纯轨迹自检阶段）⟹ 按 §4.3 的构造顺序，"
                       "meta.segments 由本轨迹的 boundaries() 直接生成，写包阶段再逐点核对"))
    else:
        want = sc.boundaries()
        ok12 = (len(want) == len(meta_move_boundaries)
                and all(abs(a - b) <= 1e-12 for a, b in zip(want, meta_move_boundaries)))
        out.append(_iv("I12", ok12,
                       f"轨迹段边界 {len(want)} 个：{[f'{b:.9f}' for b in want]}；"
                       f"meta move 边界 {len(meta_move_boundaries)} 个："
                       f"{[f'{b:.9f}' for b in meta_move_boundaries]}；逐点差 ≤ 1e-12"))
    return out


def _iv(name: str, ok: bool, detail: str) -> dict:
    return {"id": name, "passed": bool(ok), "detail": detail}


# ------------------------------------------------------------------ 黄金向量

def golden_vectors() -> list[dict]:
    """§4.5 黄金向量（回归基准，非产品代码）：至少 4 组，覆盖 I / II / III-a /
    III-b 与 `D<0`。§4.5 说「本期只登记黄金向量的结构与出处，不产出数值结果」；
    §7 #8 把重跑列为实现期任务，本函数是那个任务的结果，登记在 `selfcheck.json`
    的 `golden_vectors` 段。**它只与 §4.2 的闭式解自身比对**（自洽），不是实测验证。
    """
    cases = [
        ("GV-1 情形 III-b 短行程（P-B 母样本；§2.2 给 t1=t3=3.0 ms、v_p≈269 mm/s、T≈23.9 ms）",
         3.2, 1500.0, 30000.0, 1e7, 8000.0, 1.0, True),
        ("GV-2 情形 I 梯形长行程（P-B）", 12.0, 1500.0, 30000.0, 1e7, 8000.0, 1.0, True),
        ("GV-3 情形 II 纯 jerk 三角（v_max < a_max²/j_max ⟹ t2 = 0 且 tv > 0；"
         "走未对齐解析路径，见模块 docstring）",
         30.0, 50.0, 30000.0, 1e7, 8000.0, 1.0, False),
        ("GV-4 情形 III-a 极短行程（t1 被减拍 ⟹ a_e < a_max）", 0.02, 1500.0, 30000.0, 1e7,
         8000.0, 1.0, True),
        ("GV-5 情形 I 长行程（P-A 母样本）", 120.0, 40.0, 200.0, 4000.0, 1000.0, 1.0, True),
        ("GV-6 反向移动 D < 0（P-A，整条镜像）", -120.0, 40.0, 200.0, 4000.0, 1000.0, -1.0, True),
    ]
    out = []
    for name, D, v, a, j, fs, sign, align in cases:
        sc = build(D * sign, v, a, j, fs, grid_align_t1=align)
        ivs = invariants(sc, fs, None)
        out.append({
            "name": name,
            "inputs": {"D_mm": D * sign, "v_max": v, "a_max": a, "j_max": j, "fs": fs,
                       "grid_align_t1": align},
            "regime": sc.regime,
            "outputs_9sf": {
                "t1": float(f"{sc.t1:.9g}"), "t2": float(f"{sc.t2:.9g}"),
                "t3": float(f"{sc.t3:.9g}"), "tv": float(f"{sc.tv:.9g}"),
                "v_p": float(f"{sc.v_p:.9g}"), "T_total": float(f"{sc.T_total:.9g}"),
            },
            "outputs_full": {"t1": sc.t1, "t2": sc.t2, "t3": sc.t3, "tv": sc.tv,
                             "v_p": sc.v_p, "a_e": sc.a_e, "T_total": sc.T_total,
                             "D_calc": sc.D_calc},
            "boundary_residual_ms": sc.boundary_residual_ms,
            "invariants": [{"id": i["id"], "passed": i["passed"]} for i in ivs],
            "source": "KB5 §4.2 闭式解 + §4.5 黄金向量结构（§7 #8 的实现期任务）；"
                      "与 §4.2 闭式解自洽，不构成实测验证（A-31）",
        })
    return out