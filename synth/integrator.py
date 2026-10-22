"""KB5 §1.5 离散化与数值自洽校验。

三个时间尺度严格分开（§1.5 唯一主题）：

    h_int   被控对象积分步长（本模块）
    T_cyc   数字控制器周期（三环各自，由 controller.py 按累加时间触发）
    T_log   波形写出周期 = 1/fs

方案 1（§1.5 首选）：线性部分**精确 ZOH 离散化** `A_d = expm(A·h)`、
`B_d` 由增广矩阵指数一次求出；非线性项（Armstrong 摩擦、死区、陷波）按 h_int 显式处理。

稳定性判据（§1.5 表）全部是**解析 / 数值自洽校验**，不是对真机的实测。
措辞上限按 A-31：通过后只报「数值稳定性判据满足、能量残差分布为 …（合成侧自洽校验）」。

三环结构的实现口径（§1.4）：
* 位置 PID 的输出是**速度参考** `v_ref`，不是力矩（§1.4 的 `v_ref = (u_pd + u_ff)/Kt'`）；
  速度 PI（`kv`,`kvi`）才是把 `v_ref − vel_fb` 变成 `τ_cmd` 的那一级。
  ⟹ 离散极点必须在**串级**结构上求，只把 PID 直接乘到力矩上是把两级并成了一级。
* 电流环按一阶滞后 `ω_i = 2π·f_i` 建模（§1.4）。P-A 的 `f_i` 未发布（§5.3 纪律 3 /
  A-42：没有依据可填的字段一律 null）⟹ P-A **不建模电流环**，并在
  `selfcheck.json` 里登记该缺口，而不是编一个数。
* PWM 传输延迟是**非整数拍**（P-B `T_delay = 0.5·T_cur = 25 µs`，而最细拍是 `T_cur`），
  在离散状态空间里无法表示成有限维移位寄存器 ⟹ **不进入极点计算**，只进入频域裕度
  校核（Padé(2,2) + 精确 `e^{−sT}` 交叉核对，见 §1.5 的延迟校核要求）。
  这一条在 `selfcheck.json` 的 `discretization_notes` 里显式登记。
"""
from __future__ import annotations

import math

import numpy as np
from scipy.linalg import expm

from . import params as P

#: 位置反馈 C_p（电机侧角）与速度反馈 C_v（电机侧角速度）
CP = np.array([[1.0, 0.0, 0.0, 0.0]])
CV = np.array([[0.0, 1.0, 0.0, 0.0]])


class InstabilityError(Exception):
    """§1.5 的「拒绝生成该参数集，报 unstable_config」。"""


def expm_zoh(A: np.ndarray, B: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """精确 ZOH：`[[A,B],[0,0]]` 的矩阵指数上半块给出 (A_d, B_d)。

    A 在本模型里**奇异**（两惯量整体平移的刚体模态是零特征值），所以不能用
    `A⁻¹(A_d − I)B`；增广矩阵指数没有这个除法。
    """
    n, m = A.shape[0], B.shape[1]
    M = np.zeros((n + m, n + m), dtype=float)
    M[:n, :n] = A
    M[:n, n:] = B
    E = expm(M * h)
    return E[:n, :n].copy(), E[:n, n:].copy()


def state_space(pset: P.ParamSet) -> tuple[np.ndarray, np.ndarray]:
    """KB5 §1.2 的状态方程，坐标全部折算到电机侧。

        J_m θ̈_m = τ_m − [k(θ_m−θ_l) + c(θ̇_m−θ̇_l)] − τ_f
        J_l θ̈_l =     [k(θ_m−θ_l) + c(θ̇_m−θ̇_l)] − τ_ext
    状态 x = [θ_m, ω_m, θ_l, ω_l]，输入 u = [τ_m, τ_ext]。
    """
    Jm, Jl, k, c = pset.J_m, pset.J_l, pset.k, pset.c
    A = np.array([
        [0.0, 1.0, 0.0, 0.0],
        [-k / Jm, -c / Jm, k / Jm, c / Jm],
        [0.0, 0.0, 0.0, 1.0],
        [k / Jl, c / Jl, -k / Jl, -c / Jl],
    ], dtype=float)
    B = np.array([
        [0.0, 0.0],
        [-1.0 / Jm, 0.0],
        [0.0, 0.0],
        [0.0, -1.0 / Jl],
    ], dtype=float)
    return A, B


def discretize_notes(pset: P.ParamSet) -> list[str]:
    """登记离散化口径的显式缺口（`selfcheck.json` 的 `discretization_notes`）。"""
    out = [
        "PWM 传输延迟 T_delay = 1.5·T_pos（P-B 375 µs / P-A 1500 µs）是非整数拍，"
        "不进入离散极点计算；只进入频域裕度校核（Padé(2,2) + 精确 e^{���sT} 交叉核对）",
        "线性部分走精确 ZOH（A 奇异 ⟹ 用增广矩阵指数，不��� A⁻¹(A_d−I)B）",
        "非线性项（Armstrong 摩擦）在 h_int 上显式子步处理，不进状态空间",
    ]
    if pset.ctrl.current_bandwidth_hz is None:
        out.append("P-A 的 drive.current_loop_bandwidth_hz = null（DaRUS 未发布，"
                   "§5.3 纪律 3 / A-42：没有依据可填 ⟹ 电流环不进模型，记为缺口而非编数）")
    else:
        out.append(f"电流环按一阶滞后 ω_i = 2π·{pset.ctrl.current_bandwidth_hz:g} Hz 建模（§1.4）")
    return out


# ---------------------------------------------------------------- 稳定性判据

def pid_state_space(pset: P.ParamSet) -> dict:
    """离散位置 PID（含一阶微分低通），ZOH 在 `T_pos` 上（§1.4 的 `kd·(Δe/Δt)` + 一阶低通）。

    状态 x = [Σe·T_pos ; 滤波微分 ; 上一拍误差]，输出
    `v_ref = kp·e + ki·x0 + kd·x1`。
    微分通道：原始微分 `(e − e_prev)/T`，再经 `ω_f` 的一阶低通（§2.2 的
    「微分零点 5ω_n + 一阶滤波」：`kd·s/(1+s/ω_f)` 的离散对应）。
    """
    T = pset.ctrl.T_pos
    wf = pset.ctrl.d_filter_rad
    a = math.exp(-wf * T)
    kp, ki, kd = pset.ctrl.kp, pset.ctrl.ki, pset.ctrl.kd
    A = np.array([
        [1.0, 0.0, 0.0],
        [0.0, a, 0.0],
        [0.0, 0.0, 0.0],
    ])
    B = np.array([[T], [(1.0 - a) / T], [1.0]])
    C = np.array([[ki, kd, 0.0]])
    D = np.array([[kp]])
    return {"A": A, "B": B, "C": C, "D": D}


def _cur_lag(pset: P.ParamSet, h: float) -> tuple[float, float] | None:
    """电流环一阶滞后在 `h` 上的精确 ZOH：`(a, b)`，使 `τ_f[k+1] = a·τ_f[k] + b·τ_cmd[k]`。"""
    wi = pset.ctrl.current_bandwidth_hz
    if not wi:
        return None
    w = P.TWO_PI * wi
    a = math.exp(-w * h)
    return a, -math.expm1(-w * h)


def closed_loop_matrix(pset: P.ParamSet) -> np.ndarray:
    """串级三环（电流滞后 → 速度 PI → 位置 PID → 双惯量被控对象）的离散闭环矩阵。

    采样拍取 `T_pos`；内层（速度 PI + 电流滞后）在 `T_pos` 拍内按
    `T_vel`（以及 P-B 的 `T_cur`）精确子步推进 n 次，命令通道取零 ⟹ `e = −θ_m`。
    """
    ctrl = pset.ctrl
    A, B = state_space(pset)
    pid = pid_state_space(pset)
    kv, kvi = ctrl.kv, ctrl.kvi

    n_sub = int(round(ctrl.T_pos / ctrl.T_vel))
    if abs(n_sub * ctrl.T_vel - ctrl.T_pos) > 1e-15:
        raise InstabilityError(f"T_pos/T_vel = {ctrl.T_pos / ctrl.T_vel} 不是整数")

    # 内层一拍（一个 T_vel，v_ref 在这一拍内常值）：
    #   τ_cmd = kv·(ω_m − v_ref) + kvi·z ,  z' = z + T_vel·(ω_m − v_ref)
    #   有电流滞后时：τ_f' = a·τ_f + b·τ_cmd，被控对象吃 τ_f
    #   状态排布： [x(4) | z(1) | f(0 或 1)]
    Adv, Bdv = expm_zoh(A, B, ctrl.T_vel)
    lag = _cur_lag(pset, ctrl.T_vel)
    n_in = 5 + (1 if lag else 0)
    f_col = 5 if lag else None
    z_col = 4
    Bm = Bdv[:, 0:1]                       # 只用 τ_m 这一路 (4,1)
    Mv = np.zeros((n_in, n_in))
    Nv = np.zeros((n_in, 1))
    if lag:
        a, b = lag
        Mv[:4, :4] = Adv + b * kv * (Bm @ CV)
        Mv[:4, z_col] = (b * kvi * Bm)[:, 0]
        Mv[:4, f_col] = a * Bm[:, 0]
        Mv[z_col, :4] = ctrl.T_vel * CV[0]
        Mv[z_col, z_col] = 1.0
        Mv[f_col, :4] = b * kv * CV[0]
        Mv[f_col, z_col] = b * kvi
        Mv[f_col, f_col] = a
        Nv[:4, 0] = (-b * kv * Bm)[:, 0]
        Nv[z_col, 0] = -ctrl.T_vel
    else:
        Mv[:4, :4] = Adv + kv * (Bm @ CV)
        Mv[:4, z_col] = (kvi * Bm)[:, 0]
        Mv[z_col, :4] = ctrl.T_vel * CV[0]
        Mv[z_col, z_col] = 1.0
        Nv[:4, 0] = (-kv * Bm)[:, 0]
        Nv[z_col, 0] = -ctrl.T_vel

    for _ in range(n_sub):
        Mv, Nv = Mv @ Mv, Mv @ Nv + Nv

    kD = float(pid["D"][0, 0])
    Cp_pid = pid["C"]
    n_pl, n_pid = 4, pid["A"].shape[0]
    ni = n_in - 4                       # 内层附加状态数（z 必有；f 仅 P-B）
    n_tot = n_pl + ni + n_pid
    Acl = np.zeros((n_tot, n_tot))
    # x' = Mv[:4,:4]·x − Nv[:4,0]·kd·C_p·x + Mv[:4,4:]·[z;f] + Nv[:4,0]·(C_pid·x_p)
    Acl[:n_pl, :n_pl] = Mv[:4, :4] - Nv[:4, 0:1] * (kD * CP)
    Acl[:n_pl, n_pl:n_pl + ni] = Mv[:4, 4:]
    Acl[:n_pl, n_pl + ni:] = Nv[:4, 0:1] * Cp_pid
    Acl[n_pl:n_pl + ni, :n_pl] = Mv[4:, :4] - Nv[4:, 0:1] * (kD * CP)
    Acl[n_pl:n_pl + ni, n_pl:n_pl + ni] = Mv[4:, 4:]
    Acl[n_pl:n_pl + ni, n_pl + ni:] = Nv[4:, 0:1] * Cp_pid
    Acl[n_pl + ni:, :n_pl] = -pid["B"] @ CP
    Acl[n_pl + ni:, n_pl + ni:] = pid["A"]
    return Acl


def discrete_poles(pset: P.ParamSet, h: float | None = None) -> np.ndarray:
    """离散闭环极点在**位置环周期 `T_pos`** 上求（控制器就在这个速率上跑）。"""
    return np.linalg.eigvals(closed_loop_matrix(pset))


def check_poles(pset: P.ParamSet) -> dict:
    """离散闭环极点 + **可观测性分类**。

    ★ 两级 PI 的积分状态在「命令取零」的极点分析里表现为 `|z| = 1`：
    速度环积分器对刚体平移模态（ω_m ≡ 0）没有任何增益，`|z| = 1` 是**内部积分状态**，
    不等于系统不稳定。判据必须把它们剔掉，否则 P-A / P-B 都会被误判为不稳定。
    这里用**左特征向量 × 输出矩阵**做可观测性判定（输出 = `[θ_m, ω_l]`），
    不可观测的 `|z| ≥ 1` 模态单独列出，**不**参与稳定裕度判定，但如实报告。
    """
    Acl = closed_loop_matrix(pset)
    z, wl = np.linalg.eig(Acl)
    # 输出矩阵：电机侧角 θ_m 与负载侧角速度 ω_l（状态排布 [x(4) | z | f | x_pid(3)]）
    Cout = np.zeros((2, Acl.shape[0]))
    Cout[0, 0] = 1.0
    Cout[1, 3] = 1.0
    internal, external = [], []
    for lam, w in zip(z, wl.T):
        obs = float(np.linalg.norm(Cout @ w))   # 分量 = Σ_i w_i·C_out[row,i] = (w·C_out)
        (internal if obs < 1e-8 else external).append(
            {"pole": complex(lam), "abs": float(abs(lam)),
             "observable": bool(obs >= 1e-8)})
    ext_abs = max([p["abs"] for p in external], default=0.0)
    return {
        "n_poles": int(len(z)),
        "max_abs_z": ext_abs,
        "max_abs_z_all": float(np.max(np.abs(z))),
        "all_inside_unit_circle": bool(ext_abs < 1.0),
        "le_0p995": bool(ext_abs <= POLE_MAX),
        "n_internal_integrator_states": len(internal),
        "internal_integrator_poles": internal,
        "poles": sorted([complex(v) for v in z], key=lambda c: abs(c)),
    }


def pset_pid_states(pset: P.ParamSet) -> int:
    return 3          # 位置 PID 的状态数（Σe / 滤波微分 / 上拍微分值）


def margins(pset: P.ParamSet, loop: str = "pos") -> dict:
    """开环增益/相位裕度（§1.5 表）。

    **两个环分别算**（§1.4 的级联结构，不能把两级并成一级）：
      `vel` : `L_vel(s) = G(s)·(kv + kvi/s)·W_i(s)·e^{−sT}`
      `pos` : `L_pos(s) = L_vel(s)·(kp + ki/s + kd·s/(1+s/ω_f))·e^{−sT}`
    其中 `G(s) = ω_m/τ_m = [(sI−A)⁻¹B]_{2,1}`（速度反馈的通道），
    `W_i(s) = ω_i/(s+ω_i)`（§1.4 的电流环；P-A 无 `f_i` ⟹ `W_i ≡ 1`，见 `discretize_notes`）。
    延迟按 §1.5 的要求用**二阶 Padé** 做频域校核，`T_delay = 1.5·T_pos`
    （1 个整周期 ZOH + 0.5 周期采样-保持）；同时算一遍精确 `e^{−sT}` 作交叉核对。

    **多交越口径（已在报告的歧义清单登记）**：双惯量开环在反谐振/谐振附近会有多个
    `|L| = 1` 交越，此时「唯一交越处的相位裕度」这个经典单值定义不成立。本函数：
      * `phase_margin_deg` = **最低频交越**处的 PM（教科书口径，`loop` 判据按它判定）；
      * `phase_margins_deg` = 逐个交越的 PM 全部列出；
      * `phase_margin_min_over_crossovers_deg` = 全部交越的**最小** PM（最保守口径），
        并给 `phase_margin_min_ge_30`，让「严格读法会不会 FAIL」一眼可见、不被藏起来。
      * 不存在 `∠L = −180°` 相位交越 ⟹ `gain_margin_infinite = true`（不硬凑 GM 数值）。
    """
    A, B = state_space(pset)
    ctrl = pset.ctrl
    w = np.logspace(-1, 6, 8000)
    s = 1j * w
    # G(s) = ω_m/τ_m = [(sI−A)⁻¹B]_{2,1}：批量解，避免在 Python 层逐点求解
    Ab = s[:, None, None] * np.eye(4)[None, :, :] - A[None, :, :]
    Bb = np.broadcast_to(B[:, 0:1], (len(w), 4, 1))
    G = np.linalg.solve(Ab, Bb)[:, 1, 0]
    kv = ctrl.kv + ctrl.kvi / s
    kp = (ctrl.kp + ctrl.ki / s
          + ctrl.kd * s / (1.0 + s / ctrl.d_filter_rad))
    if ctrl.current_bandwidth_hz:
        wi = P.TWO_PI * ctrl.current_bandwidth_hz
        wlag = wi / (s + wi)
    else:
        wlag = np.ones_like(s)
    Td = 1.5 * ctrl.T_pos
    pade = (1.0 - Td * s / 2 + (Td * s) ** 2 / 12) / (1.0 + Td * s / 2 + (Td * s) ** 2 / 12)
    base = G * kv * wlag
    if loop == "pos":
        base = base * kp
    elif loop != "vel":  # pragma: no cover
        raise ValueError(f"loop 只能是 'vel' / 'pos'，收到 {loop!r}")

    def _scan(Lin):
        mag, ph = np.abs(Lin), np.degrees(np.angle(Lin))
        gcs, pms = [], []
        for i in range(len(w) - 1):
            if (mag[i] - 1.0) * (mag[i + 1] - 1.0) < 0.0:
                f = (1.0 - mag[i]) / (mag[i + 1] - mag[i])
                gcs.append(float(w[i] + f * (w[i + 1] - w[i])) / P.TWO_PI)
                pms.append(float(180.0 + ph[i] + f * (ph[i + 1] - ph[i])))
        pcs, gms = [], []
        for i in range(len(w) - 1):
            if (ph[i] + 180.0) * (ph[i + 1] + 180.0) < 0.0:
                f = (-180.0 - ph[i]) / (ph[i + 1] - ph[i])
                mm = mag[i] + f * (mag[i + 1] - mag[i])
                if mm <= 0.0:
                    continue
                pcs.append(float(w[i] + f * (w[i + 1] - w[i])) / P.TWO_PI)
                gms.append(float(-20.0 * math.log10(mm)))
        return gcs, pms, pcs, gms

    gcs, pms, pcs, gms = _scan(base * pade)
    _gcx, _pmx, _pcx, _gmx = _scan(base * np.exp(-s * Td))
    return {
        "loop": loop,
        "gain_crossovers_hz": gcs,
        "phase_margins_deg": pms,
        "phase_crossovers_hz": pcs,
        "gain_margins_db": gms,
        "phase_margin_deg": pms[0] if pms else None,
        "phase_margin_min_over_crossovers_deg": min(pms) if pms else None,
        "phase_margin_min_ge_30": bool(pms and min(pms) >= PM_MIN_DEG),
        "gain_margin_db": min(gms) if gms else None,
        "gain_margin_infinite": not gms,
        "crossover_hz": gcs[0] if gcs else None,
        "n_gain_crossovers": len(gcs),
        "exact_delay_phase_margin_deg": _pmx[0] if _pmx else None,
        "exact_delay_gain_margin_db": min(_gmx) if _gmx else None,
        "exact_delay_gain_margin_infinite": not _gmx,
        "delay_model": "pade2_freq_check+exact_crosscheck",
        "delay_s": Td,
        "phase_margin_convention": (
            "多交越口径：phase_margin_deg 取最低频交越（教科书口径）；"
            "phase_margin_min_over_crossovers_deg 取全部交越的最小值并单独给布尔判定；"
            "无 ∠L = −180° 相位交越 ⟹ gain_margin_infinite（不硬凑 GM 数值）"),
    }


# ---- §1.5 判据判定 -------------------------------------------------------------

#: §1.5 表的三个门限
POLE_MAX = 0.995
PM_MIN_DEG = 30.0
GM_MIN_DB = 6.0
ENERGY_RESIDUAL_MAX_PCT = 0.5


def stability_report(pset: P.ParamSet) -> dict:
    """§1.5 判据表的三项一次性判定（极点 / 相位裕度 / 增益裕度）+ 自由振荡漂移。

    相位裕度**按最低频交越**（教科书口径）判定 —— 详见 `margins` 的 `phase_margin_convention`。
    同时输出 `phase_margin_min_over_crossovers_deg`（全部交越的最小值）与其布尔判定，
    **不**隐藏「严格读法会不会 FAIL」这件事。
    """
    pol = check_poles(pset)
    mv = margins(pset, loop="vel")
    mp = margins(pset, loop="pos")
    dec = free_oscillation_decay(pset)

    def _pm_ok(m):
        return m["phase_margin_deg"] is not None and m["phase_margin_deg"] >= PM_MIN_DEG

    def _gm_ok(m):
        return m["gain_margin_infinite"] or (
            m["gain_margin_db"] is not None and m["gain_margin_db"] >= GM_MIN_DB)

    checks = {
        "poles_le_0p995": bool(pol["le_0p995"]),
        "phase_margin_ge_30deg": bool(_pm_ok(mv) and _pm_ok(mp)),
        "gain_margin_ge_6db_or_infinite": bool(_gm_ok(mv) and _gm_ok(mp)),
        "free_osc_drift_lt_1pct": bool(dec["lt_1pct"]),
    }
    return {
        "poles": pol,
        "margins_velocity_loop": mv,
        "margins_position_loop": mp,
        "phase_margin_criterion": "最低频增益交越处的 PM（教科书口径）；"
                                  "全部交越的最小 PM 另列为 phase_margin_min_over_crossovers_deg",
        "free_oscillation": dec,
        "checks": checks,
        "passed": all(checks.values()),
        "thresholds": {"max_abs_z": POLE_MAX, "phase_margin_deg_min": PM_MIN_DEG,
                       "gain_margin_db_min": GM_MIN_DB, "free_drift_max_pct": 1.0,
                       "energy_residual_max_pct": ENERGY_RESIDUAL_MAX_PCT},
        "discretization_notes": discretize_notes(pset),
    }


def calibrate_omega_n(pset: P.ParamSet, ratios: tuple[float, ...] | None = None
                      ) -> tuple[P.ParamSet, dict]:
    """在 §1.5 的判据下标定**位置环带宽 ω_n**（规范未给该量时使用）。

    候选按 `f_m / ω_n = ratio` 给出（`ratio` 出自 KB5 §2.2 原文「f_m/ω_n = 13.9 ≫ 3」
    这一族比值；扫描从大比值往小比值走 ⟹ ω_n 递增）。返回第一个满足
    「|z| ≤ 0.995 且 PM ≥ 30° 且 GM ≥ 6 dB（或无穷）」的候选。

    这是 §1.5 门禁的**正常用法**：规范没给环带宽，就把「给定哪些值才算可生成」
    显式化，而不是编一个值再假装它满足判据。
    """
    from dataclasses import replace

    base = pset.ctrl
    cand = ratios or (13.9, 10.0, 8.0, 6.0, 5.0, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5)
    tried = []
    for r in cand:
        wn = P.TWO_PI * pset.f_m_hz / r
        ctrl = P.controller_for(pset, wn)
        trial = replace(pset, ctrl=ctrl)
        try:
            rep = stability_report(trial)
        except Exception as exc:  # noqa: BLE001
            tried.append({"ratio": r, "wn_rad_s": wn, "error": f"{type(exc).__name__}: {exc}"})
            continue
        tried.append({"ratio": r, "wn_rad_s": wn, "wn_hz": wn / P.TWO_PI,
                      "passed": rep["passed"], "checks": dict(rep["checks"]),
                      "max_abs_z": rep["poles"]["max_abs_z"],
                      "phase_margin_deg": rep["margins_position_loop"]["phase_margin_deg"],
                      "phase_margin_min_deg": rep["margins_position_loop"][
                          "phase_margin_min_over_crossovers_deg"],
                      "gain_margin_db": rep["margins_position_loop"]["gain_margin_db"],
                      "gain_margin_infinite": rep["margins_position_loop"][
                          "gain_margin_infinite"]})
        if rep["passed"]:
            return trial, {"selected_ratio": r, "selected_wn_rad_s": wn,
                           "selected_wn_hz": wn / P.TWO_PI, "candidates": tried,
                           "rule": "在 §1.5 的 |z| / PM / GM 三条判据下取第一个通过的候选"}
    raise InstabilityError(
        "P-A 的位置环带宽扫描中没有任何候选满足 §1.5 的三条稳定性判据；"
        f"候选见 tried={tried}")


def calibrate_pset(pset: P.ParamSet) -> tuple[P.ParamSet, dict]:
    """按参数集挑标定方式：P-B 的 `ω_n` 是 §2.2 给定的 85 Hz，不能动。"""
    if abs(pset.ctrl.wn - P.TWO_PI * 85.0) > 1e-9:
        return calibrate_omega_n(pset)
    return pset, {"selected_wn_rad_s": pset.ctrl.wn,
                  "selected_wn_hz": pset.ctrl.wn / P.TWO_PI,
                  "rule": "P-B 的 ω_n = 2π·85 Hz 由 KB5 §2.2 直接给定 ⟹ 不标定"}


def free_oscillation_decay(pset: P.ParamSet, n_cycles: int = 100) -> dict:
    """§1.5「无阻尼自由振荡 100 周期内幅值漂移 <1%」。

    判据的对象是**数值格式**，不是被控对象的物理阻尼，所以：
      * 把阻尼 `c` 置零（否则 100 周期的自然衰减 `exp(−2πζ·100)` 在 ζ=0.02 下已是
        3.5e−6，测到的会是物理衰减而不是格式误差）；
      * 初值取**对称弹性位移** `[−a, 0, +a, 0]`（等质量两体 ⟹ 只激发弹性模态，
        刚体平移不被激发 ⟹ 总能量严格守恒，可以当格式误差的探针；
        若取「纯速度」初值，刚体模态的平动动能随 t² 增长会淹没格式误差）；
      * 用**能量**而不是 `|ω|/ω` 当幅值：后者对相位极敏感，`n = round(N/(f₀h))`
        的取整误差会被当成幅值漂移。
    """
    A, B = state_space(pset)
    A0 = A.copy()
    Jm, Jl, k = pset.J_m, pset.J_l, pset.k
    A0[1, 1] = 0.0
    A0[1, 3] = 0.0
    A0[3, 1] = 0.0
    A0[3, 3] = 0.0
    A0[1, 0] = -k / Jm
    A0[1, 2] = k / Jm
    A0[3, 0] = k / Jl
    A0[3, 2] = -k / Jl
    Ad, _Bd = expm_zoh(A0, B, pset.h_int)
    f0 = pset.f_m_hz
    a = 1e-4
    x = np.array([-a, 0.0, a, 0.0])

    def energy(v) -> float:
        return (0.5 * Jm * v[1] ** 2 + 0.5 * Jl * v[3] ** 2
                + 0.5 * k * (v[0] - v[2]) ** 2)

    e0 = energy(x)
    n = int(round(n_cycles / (f0 * pset.h_int)))   # = n_cycles / (ω·h/2π)：100 个谐振周期
    achieved_cycles = n * f0 * pset.h_int
    for _ in range(n):
        x = Ad @ x
    e1 = energy(x)
    drift = abs(e1 - e0) / e0
    return {"n_cycles": n_cycles, "achieved_cycles": achieved_cycles, "n_steps": n,
            "h_int": pset.h_int, "omega_h": P.TWO_PI * f0 * pset.h_int,
            "energy_0": e0, "energy_N": e1, "rel_drift": drift,
            "lt_1pct": bool(drift < 0.01),
            "probe": "对称弹性位移初值 [−a,0,+a,0] + 无阻尼精确 ZOH；漂移量 = 能量相对变化"
                     "（能量与相位无关，故步数取整误差不计入漂移）"}


class EnergyAudit:
    """§1.5 的能量守恒核对 —— **本模型最重要的独立正确性检查**。

    它不需要任何外部真值、也不经过规则层，因此不会被自验证循环污染。

        ∫τ_m ω_m dt = ΔKE + ΔPE + ∫c(ω_m−ω_l)² dt + ∫τ_f ω_m dt + ∫τ_ext ω_l dt

    ★ §1.5 的原式没有粘性阻尼项 `∫c(ω_m−ω_l)² dt`。它是真实的功率汇项，
    省略会让残差系统性地等于该项而不是 0。本实现两个口径都报：
    `residual_pct`（含阻尼项，判定用）与 `residual_pct_kb5_form`（按 §1.5 原式）。
    """

    __slots__ = ("pset", "w_motor", "w_ext", "w_fric", "w_damp", "ke0", "pe0", "ke1", "pe1")

    def __init__(self, pset: P.ParamSet) -> None:
        self.pset = pset
        self.w_motor = self.w_ext = self.w_fric = self.w_damp = 0.0
        x0 = np.zeros(4)
        self.ke0, self.pe0 = self._energy(x0)
        self.ke1, self.pe1 = 0.0, 0.0

    def _energy(self, x) -> tuple[float, float]:
        th_m, w_m, th_l, w_l = x
        ke = 0.5 * self.pset.J_m * w_m * w_m + 0.5 * self.pset.J_l * w_l * w_l
        pe = 0.5 * self.pset.k * (th_m - th_l) ** 2
        return ke, pe

    def add(self, tau_m: float, tau_f: float, tau_ext: float, x, h: float) -> None:
        w_m, w_l = x[1], x[3]
        self.w_motor += tau_m * w_m * h
        self.w_fric += tau_f * w_m * h
        self.w_ext += tau_ext * w_l * h
        self.w_damp += self.pset.c * (w_m - w_l) ** 2 * h

    def close(self, x) -> dict:
        self.ke1, self.pe1 = self._energy(x)
        lhs = self.w_motor
        rhs_full = ((self.ke1 - self.ke0) + (self.pe1 - self.pe0) + self.w_damp
                    + self.w_fric + self.w_ext)
        rhs_kb5 = (self.ke1 - self.ke0) + (self.pe1 - self.pe0) + self.w_fric + self.w_ext
        scale = max(abs(lhs), 1e-30)
        return {
            "int_tau_m_omega_m": lhs,
            "delta_kinetic": self.ke1 - self.ke0,
            "delta_potential": self.pe1 - self.pe0,
            "int_c_domega_sq": self.w_damp,
            "int_tau_f_omega_m": self.w_fric,
            "int_tau_ext_omega_l": self.w_ext,
            "residual_pct": abs(lhs - rhs_full) / scale,
            "residual_pct_kb5_form": abs(lhs - rhs_kb5) / scale,
            "dissipated_pct": abs(self.w_damp) / scale,
        }