"""KB5 §2 参数集（P-A / P-B）与 P-C 守门案例。

**出处纪律**：本文件的每个数值都必须能指到 KB5 §2.0 的公开种子或 §1 的公式。
指不到的（本文件末尾 `ASSUMED_REGISTRY` 登记的三处）在 `truth.json` 里标
`provenance = "assumed"`，并在报告的「需要登记进 KB0 的事项」里列拟的裁决文字。

坐标约定（KB5 §1.2）：全部折算到**电机侧角坐标**；位置/速度在写出层经
`x_per_motor_rev` 与 `counts_per_mm` 换算成 counts（KB5 §1.1 换算链）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class FrictionParams:
    """KB5 §1.3 (A) Armstrong 双模态（one-step）。

    规范给了 `v_0`（模态切换速度阈值）这个符号，但 §2.1/§2.2 **没有给它的值**。
    本实现不使用 `v_0`：预滑动段的 ODE `dτ_f/dt = (τ_sl(v) − τ_f)/T_d` 在
    "子步内 τ_sl 常值" 的前提下有**解析指数解** `τ_f ← τ_sl + (τ_f − τ_sl)·e^{−h/T_d}`，
    它在 `|v| < v_0` 与 `|v| ≥ v_0` 两支上连续且给出同一个稳态极限，故
    「两支切换」退化为「一步指数更新」，不需要引入一个规范没有的阈值。
    """
    tau_s: float
    tau_c: float
    v_s: float
    alpha: float
    b: float
    T_d: float
    model: str = "armstrong_one_step"
    source: str = "T2: DaRUS-5171 LdaFricIdent / PreloadedViscousFrictionIdent"

    def tau_sl(self, v: float) -> float:
        a = abs(v)
        av = a / self.v_s
        static = self.tau_c + (self.tau_s - self.tau_c) * math.exp(-(av ** self.alpha))
        sgn = 1.0 if v > 0.0 else (-1.0 if v < 0.0 else 0.0)
        return sgn * (static + self.b * a)


@dataclass(frozen=True)
class ControllerParams:
    """KB5 §1.4 三环结构（离散控制器 + ZOH）。

    §1.4 写作 `v_ref = (u_pd + u_ff)/Kt'` 而下一行是 `τ_cmd = Kt·(kv·(v_ref − vel_fb) + …)`。
    只有把 `Kt'` 读成 `kv`（速度环刚度 [N·m·s/rad]，与下行同一个符号）时量纲才自洽
    （力矩 ÷ 力矩-每-速度 = 速度）。本实现按 `Kt' ≡ kv` 落地，因此**不需要**任何
    规范未发布的力矩常数就能跑通速度环；电流通道另按 §2.2 的 `Kt` 换算，P-A 无 Kt ⟹ 不出 cur_q。
    """
    T_pos: float
    T_vel: float
    T_cur: float
    kp: float
    ki: float
    kd: float
    kff_a: float
    kff_v: float
    kv: float
    kvi: float
    wn: float
    d_filter_hz: float          # 微分项一阶低通（§2.2：微分零点 5ω_n + 一阶滤波）
    current_bandwidth_hz: float | None   # None ⟹ §5.3 纪律 3 的「无依据可填」分支
    pwm_delay_s: float
    cmd_filter_hz: float | None
    vel_bandwidth_hz: float | None = None   # None ⟹ §1.4 的下界 `3·ω_n`；P-B 固定 300 Hz

    @property
    def d_filter_rad(self) -> float:
        return TWO_PI * self.d_filter_hz


def controller_for(pset: "ParamSet", wn: float) -> ControllerParams:
    """按给定的 `ω_n` 重建三环增益。

    构造式全部出自 KB5 §2.2（`kp = ω_n²·J_tot`、`ki = kp·ω_n/5`、`kd = kp·5/ω_n`）
    与 §1.4（速度环带宽下界 `3·ω_n`）；`ctrl.vel_bandwidth_hz` 非 None 时速度环带宽固定。
    `integrator.calibrate_omega_n` 用它在 §1.5 的判据下标定 P-A 的 `ω_n`
    （规范未给该量）。
    """
    from dataclasses import replace

    c0 = pset.ctrl
    J_tot = pset.J_tot
    kp = wn * wn * J_tot
    ki = kp * wn / 5.0
    kd = kp * 5.0 / wn
    fv = c0.vel_bandwidth_hz if c0.vel_bandwidth_hz is not None else 3.0 * wn / TWO_PI
    wv = TWO_PI * fv
    kv = J_tot * wv
    kvi = kv * wv / 5.0
    return replace(c0, wn=wn, kp=kp, ki=ki, kd=kd, kv=kv, kvi=kvi,
                   d_filter_hz=5.0 * wn / TWO_PI)


@dataclass(frozen=True)
class ParamSet:
    name: str
    fs: float
    h_int: float
    J_m: float
    J_l: float
    k: float
    zeta_m: float
    x_per_motor_rev_mm: float   # 电机转一圈对应的**负载直线位移**
    counts_per_mm: float | None
    counts_per_rev_motor: float | None
    gear_ratio_N: float
    r_drum_m: float | None
    lead_mm: float | None
    friction: FrictionParams
    ctrl: ControllerParams
    Kt: float | None
    rated_current_a: float | None
    rated_torque_N_m: float | None
    rated_torque_source: str | None
    units_are: str
    machine_type: str
    control_card: str
    machine_name: str
    complaint: str
    operator_notes: str
    recipe: str
    step: str
    step_sequence: tuple[str, ...]
    quantization_step_counts: float
    encoder_lines: int | None
    motor_rev_counts: int | None
    gear_ratio_r_eff_m: float | None      # 直线轴的旋转等效半径
    inertia_ratio_meta: float | None
    J_r_explicit: float | None = None    # §2.1 直接给出的折算惯量（见下方歧义说明）
    thermal_drift_counts_per_min: float = 0.0
    notes: tuple[str, ...] = ()

    # ---- 派生量（KB5 §1.2 的解析式，不是拟合值）-----------------------------
    @property
    def J_tot(self) -> float:
        return self.J_m + self.J_l

    @property
    def J_r(self) -> float:
        """折算（reduced）惯量。

        ★ **规范歧义，已在报告的「遇到规范歧义的地方」登记**：KB5 §2.1 写
        `J_r = J_m J_l'/(J_m+J_l') = 1.875e-4`，但按它给的 `J_m = 3.0e-4`、
        `J_l' = 9.0e-4` 代进去得 `2.25e-4`。同段还把 `f_m = 45.0 Hz`、`f_a = 22.5 Hz`、
        `c = 2(0.12)(0.0530) = 1.27e-2`、`Q ≈ 4.2` 全部挂在 `J_r = 1.875e-4` 上。
        本实现取 **§2.1 明写的 `J_r = 1.875e-4`**（`J_r_explicit`），因为下游判据
        （INJ-01 的 `f_m = 45.0`、配对间距 22.5 Hz、`c = 1.27e-2`）都以它为准；
        另一支读法（坚持 `J_m J_l'/(J_m+J_l')`）会把 `f_m` 拉到 41.1 Hz、`f_a` 20.5 Hz，
        与 §2.1 声明的 45.0 / 22.5 / 22.5 Hz 配对间距不符。
        P-B 未给 `J_r`，故走代数式（`9.692e-7`，与 §2.2 的 `f_m = 1181 Hz` 自洽到 0.2%）。
        """
        if self.J_r_explicit is not None:
            return self.J_r_explicit
        return self.J_m * self.J_l / self.J_tot

    @property
    def lam(self) -> float:
        return self.J_l / self.J_m

    @property
    def c(self) -> float:
        return 2.0 * self.zeta_m * math.sqrt(self.k * self.J_r)

    @property
    def f_m_hz(self) -> float:
        return math.sqrt(self.k / self.J_r) / TWO_PI

    @property
    def f_a_hz(self) -> float:
        # §2.1 明写 `f_a = f_m / √(1+λ)`，且 λ 与 f_m 是同一段里成对给出的 ⟹ 走这一支。
        # （走 `√(k/J_l')` 会得到与 `f_m/√(1+λ)` 不相容的值，见 `J_r` 的歧义说明。）
        return self.f_m_hz / math.sqrt(1.0 + self.lam)

    @property
    def zeta_a(self) -> float:
        return self.c / (2.0 * math.sqrt(self.k * self.J_l))

    @property
    def q_estimate(self) -> float:
        return 1.0 / (2.0 * self.zeta_m)

    @property
    def counts_per_rad(self) -> float:
        """counts = θ[rad] × x_per_motor_rev[mm]/(2π) × counts_per_mm。"""
        return self.x_per_motor_rev_mm / TWO_PI * (self.counts_per_mm or 0.0)

    @property
    def mm_per_rad(self) -> float:
        return self.x_per_motor_rev_mm / TWO_PI

    @property
    def pos_quantum_mm(self) -> float | None:
        return None if self.counts_per_mm is None else 1.0 / self.counts_per_mm

    def with_zeta(self, zeta_m: float, name_suffix: str = "") -> "ParamSet":
        from dataclasses import replace
        return replace(self, zeta_m=zeta_m, name=self.name + name_suffix)


def _pa_controller() -> ControllerParams:
    """P-A 的 SI 环增益 —— **占位值**，真值由 `integrator.calibrate_omega_n` 在
    §1.5 的三条判据下标定（规范没给 P-A 的 SI 环带宽）。

    KB5 §2.1 只给了 DaRUS **发布**的归一化增益（kff=1.5, kp=0.01, ki=0.1, kd=5e-4）
    并明文警告「不能直接代入本文件的 SI 公式」。这里的 `ratio = 13.9` 是 §2.2 原文
    「f_m/ω_n = 13.9 ≫ 3」的同一个比值，作为**扫描起点**；标定过程与被否掉的候选
    全部记进 `selfcheck.json`，标定结论进 `ASSUMED_REGISTRY`。
    """
    f_m = 45.0158      # = PA.f_m_hz（§2.2 的 45.0 Hz 同式复算）
    ratio = 13.9       # §2.2 原文「f_m/ω_n = 13.9 ≫ 3」的同一个比值
    return _pa_ctrl_from_wn(TWO_PI * f_m / ratio)


def _pa_ctrl_from_wn(wn: float) -> ControllerParams:
    """`_pa_controller` 的实现体（避免与 `controller_for` 的前向依赖）。"""
    wv = 3.0 * wn                      # §1.4「速度环假定带宽 ≥ 3ω_n」的下界取等
    ctrl = ControllerParams(
        T_pos=1e-3, T_vel=1e-3, T_cur=1.25e-4,
        kp=0.0, ki=0.0, kd=0.0, kff_a=1.5, kff_v=0.0, kv=0.0, kvi=0.0, wn=wn,
        d_filter_hz=5.0 * wn / TWO_PI,
        current_bandwidth_hz=None,        # §2.1：DaRUS 未发布 ⟹ meta 里必须是 null（A-42）
        pwm_delay_s=0.5 * 1.25e-4,
        cmd_filter_hz=1.0 / TWO_PI / 0.02,   # §2.0 种子：低通 0.02 s ⟹ f_c ≈ 8.0 Hz
        vel_bandwidth_hz=None,
    )
    return _fill_gains(ctrl, wn)


def _fill_gains(ctrl: ControllerParams, wn: float, J_tot: float = 1.2e-3) -> ControllerParams:
    from dataclasses import replace

    kp = wn * wn * J_tot
    ki = kp * wn / 5.0
    kd = kp * 5.0 / wn
    fv = ctrl.vel_bandwidth_hz if ctrl.vel_bandwidth_hz is not None else 3.0 * wn / TWO_PI
    wv = TWO_PI * fv
    kv = J_tot * wv
    kvi = kv * wv / 5.0
    return replace(ctrl, kp=kp, ki=ki, kd=kd, kv=kv, kvi=kvi)


def _pb_controller() -> ControllerParams:
    """P-B 的 SI 环增益：§2.2 逐项给定，无一项需要假设。"""
    wn = TWO_PI * 85.0
    J_tot = 1.126e-6 + 6.960e-6
    kp = wn * wn * J_tot
    ki = kp * wn / 5.0
    kd = kp * 5.0 / wn
    f_v = 300.0                                # §5.3 示例 meta：velocity_loop_gain_hz = 300.0
    wv = TWO_PI * f_v
    kv = J_tot * wv
    kvi = kv * wv / 5.0
    return ControllerParams(
        T_pos=2.5e-4, T_vel=1.25e-4, T_cur=6.25e-5,
        kp=kp, ki=ki, kd=kd, kff_a=1.0, kff_v=0.0, kv=kv, kvi=kvi, wn=wn,
        d_filter_hz=5.0 * wn / TWO_PI,
        current_bandwidth_hz=1200.0,           # §2.2：必须写进 meta.drive（A-42）
        pwm_delay_s=0.5 * 6.25e-5,
        cmd_filter_hz=None,                    # §5.4 示例：P-B 的 cmd_filter_hz = null
        vel_bandwidth_hz=300.0,
    )


def pa_f_m_hz() -> float:
    return math.sqrt(15.0 / 1.875e-4) / TWO_PI


PA = ParamSet(
    name="P-A",
    fs=1000.0,
    h_int=5e-5,
    J_m=3.0e-4,
    J_l=9.0e-4,
    k=15.0,
    zeta_m=0.12,
    x_per_motor_rev_mm=61.575,              # = 2π·r_drum·1000/N（§1.1 表）
    counts_per_mm=5.8349,
    counts_per_rev_motor=359.3,
    gear_ratio_N=5.0,
    r_drum_m=0.049,
    lead_mm=None,
    friction=FrictionParams(tau_s=0.9, tau_c=0.45, v_s=0.05, alpha=1.0, b=0.8, T_d=4e-3),
    ctrl=_pa_controller(),
    Kt=None,                                  # §2.0 未发布 P-A 的 Kt ⟹ 不得估算（§7 #9）
    rated_current_a=None,                     # §2.0：4.6 A 是借给 P-B 的 MSK061C 额定值
    rated_torque_N_m=32.0,                    # §2.1 表：assumed，XML 原值无量纲（A-27）
    rated_torque_source="assumed",
    units_are="si_native",
    machine_type="testbed",
    control_card="beckhoff TC3",
    machine_name="线缆驱动试验台/绳索卷筒",
    complaint="起动迟滞与低速爬行，空载往复时行程末端有拖滞感",
    operator_notes="线缆驱动试验台锚点集（非产线数据）；惯量与刚度未在原始数据中发布，"
                   "本样本的 J_m/J_l'/k/c 全部为假设值",
    recipe="cable_test_profile_A",
    step="reciprocate",
    step_sequence=("home", "reciprocate", "probing", "reciprocate"),
    quantization_step_counts=1.0,
    encoder_lines=None,
    motor_rev_counts=None,
    gear_ratio_r_eff_m=None,
    inertia_ratio_meta=3.0,
    J_r_explicit=1.875e-4,               # §2.1 明写值（与 f_m=45.0 / c=1.27e-2 同源）
    thermal_drift_counts_per_min=0.0,
    notes=(
        "counts_per_mm = 5.8349 是控制器内部缩放单位的可能性未被原始工程文件核实（§1.1 推论 2）",
        "45 Hz 绳索弹性模态高于 8.0 Hz 指令低通约 5.6 倍 ⟹ declared_detectable = false",
    ),
)

PB = ParamSet(
    name="P-B",
    fs=8000.0,
    h_int=6e-6,
    J_m=1.126e-6,
    J_l=6.960e-6,
    k=53.2,                                    # §2.2 给定；代数复算 ω_p²J_r = 53.18
    zeta_m=0.02,
    x_per_motor_rev_mm=8.0,                    # lead = 8 mm/rev，N = 1 直驱
    counts_per_mm=50000.0,
    counts_per_rev_motor=None,                 # 电机侧绝对编码器仅填 meta.axis（§2.2）
    gear_ratio_N=1.0,
    r_drum_m=None,
    lead_mm=8.0,
    friction=FrictionParams(tau_s=0.06, tau_c=0.035, v_s=0.02, alpha=1.0, b=0.02, T_d=1e-3),
    ctrl=_pb_controller(),
    Kt=1.5,                                    # assumed（§2.2）
    rated_current_a=4.6,                       # assumed，借自 MSK061C-0600（§2.0）
    rated_torque_N_m=6.9,                      # = 4.6 A × 1.5 N·m/A（§5.3 纪律 12）
    rated_torque_source="assumed",
    units_are="counts",
    machine_type="die_attach",
    control_card="beckhoff TC3",
    machine_name="共晶贴片机 X 轴",
    complaint="取片后末端抖动，settle 窗口内的残振明显",
    operator_notes="额定电流 4.6 A 与力矩常数 1.5 N·m/A 均为假定值（借自 MSK061C，"
                   "P-B 并不装这台电机）；百分比类判据的绝对刻度不可信",
    recipe="AuSn_280C_die4",
    step="place",
    step_sequence=("home", "pick_up", "flux_inspect", "place", "bond", "verify"),
    quantization_step_counts=1.0,
    encoder_lines=16777216,
    motor_rev_counts=524288,
    gear_ratio_r_eff_m=8.0 / TWO_PI,
    inertia_ratio_meta=6.18,
    thermal_drift_counts_per_min=0.0,
    notes=(
        "r_eff = lead/2π = 1.273e-3 m；旋转量除回直线量（§2.2）",
        "f_i = 1200 Hz 与 f_m = 1181 Hz 同量级：电流环相位滞后压在机械谐振上（§2.2）",
    ),
)

#: 三处规范没有给值、本合成器必须自备的量。全部 `provenance = "assumed"`，
#: 报告的「需要登记进 KB0 的事项」给出拟的裁决文字。
ASSUMED_REGISTRY = (
    ("P-A 的 SI 位置环带宽 ω_n",
     "KB5 §2.1 只给了 DaRUS 发布的归一化增益并明文禁止直接代入 SI 公式，未给 P-A 的 SI 环带宽。"
     "本合成器取 ω_n = 2π·f_m/13.9（f_m = 45.0195 Hz 为 §2.2 给定值的同式复算，"
     "比值 13.9 出自 §2.2 原文「f_m/ω_n = 13.9 ≫ 3」），kp/ki/kd 由 §2.2 的构造式"
     "（kp = ω_n²·J_tot、ki = kp·ω_n/5、kd = kp·5/ω_n）生成。标 assumed。"),
    ("P-B 的电流测量噪声 0.02 A rms",
     "KB5 §2.2 未给 P-B 的电流噪声量级。取 §2.1 给出的 0.02 A rms（同为借用的 MSK061C 电机族假设），"
     "标 assumed。若要独立取值需 KB5 §2.2 补一行。"),
    ("Armstrong 预滑动段用解析指数更新而非 v_0 切换",
     "KB5 §1.3 引入 v_0（模态切换速度阈值）但 §2.1/§2.2 未给其值，且 §1.5 方案 1 要求"
     "「非线性项用 h_int 的显式子步处理」。本实现对 dτ_f/dt = (τ_sl − τ_f)/T_d 取"
     "子步内 τ_sl 常值下的解析解 τ_f ← τ_sl + (τ_f − τ_sl)·e^{−h/T_d}，"
     "该式在两支上连续且极限一致，故不需要 v_0。若 KB5 要求显式两支，需补 v_0 的取值来源。"),
)