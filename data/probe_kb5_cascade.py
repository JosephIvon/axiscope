"""KB5 §1.5：按用户裁定「先建全级联再判」，把速度环并进位置环复算稳定性。

与前一份 `probe_kb5_stability.py` 的区别：那份把位置环直接驱矩（刚体单惯量），
**没有建 KB5 §1.4 自己规定的速度环**。本份并入速度 PI，并按 §1.4 的下界
「速度环假定带宽 ≥ 3ω_n」推导 kv / kvi（§2.2 的构造式同形：kv = J·ω_v，
kvi = kv·ω_v/5）——**规格没给 kv/kvi 数值，这条推导是本实现自选的解读，须登记**。

级联结构（KB5 §1.4 第 317–319 行）：
  位置 PID（周期 T_pos）→ u_pd
  v_ref = u_pd / Kt'，本实现按 `Kt' ≡ kv` 读（量纲自洽：力矩 ÷ (力矩/速度) = 速度）
  速度 PI（周期 T_vel）→ τ_cmd = kv·(v_ref − ω) + kvi·Σ(v_ref − ω)·T_vel
  被控对象（刚体单惯量 J_tot）
电流环按 §1.4 第 319 行是「一阶滞后 + PWM 延迟」，本份**尚未并入** ⟹ 结果偏乐观。

判据（§1.5 第 379 行）：全部 |z| < 1，最坏 |z| ≤ 0.995。
"""
import numpy as np

WN = 2 * np.pi * 85.0
J = 8.11e-6
KP, KI, KD = WN**2 * J, WN**2 * J * WN / 5.0, WN**2 * J * 5.0 / WN


def vel_gains(wn):
    """按 §1.4「速度环带宽 ≥ 3ω_n」取下界 3ω_n，构造式照 §2.2 位置环同形。"""
    wv = 3.0 * wn
    kv = J * wv
    kvi = kv * wv / 5.0
    return kv, kvi


def A_cascade(T, kp, ki, kd, kv, kvi):
    """单速率级联（T_pos == T_vel）。状态 [theta, omega, Ip, ep_prev, Iv]。"""
    c = kp + kd / T
    M = np.zeros((5, 5))
    M[0, 0] = 1.0 - (T * T / (2.0 * J)) * c
    M[0, 1] = T - (T * T / (2.0 * J)) * kv
    M[0, 2] = (T * T / (2.0 * J)) * ki
    M[0, 3] = -(T / (2.0 * J)) * kd
    M[0, 4] = (T * T / (2.0 * J)) * kvi
    M[1, 0] = -(T / J) * c
    M[1, 1] = 1.0 - (T / J) * kv
    M[1, 2] = (T / J) * ki
    M[1, 3] = -(1.0 / J) * kd
    M[1, 4] = (T / J) * kvi
    M[2, 0] = -T
    M[2, 2] = 1.0
    M[3, 0] = -1.0
    M[4, 0] = -T * c / kv
    M[4, 1] = -T
    M[4, 2] = T * ki / kv
    M[4, 3] = -kd / kv
    M[4, 4] = 1.0
    return M


print("kp=%.4f ki=%.4f kd=%.6f   ω_n=%.4f rad/s   J_tot=%.3e" % (KP, KI, KD, WN, J))
kv, kvi = vel_gains(WN)
print("速度环（按 §1.4 下界 3ω_n 推导）：ω_v=%.1f rad/s  kv=%.5f  kvi=%.5f"
      % (3 * WN, kv, kvi))
print()
print("=== 并入速度环后（单速率，刚体单惯量，**未含电流环 ⟹ 偏乐观**） ===")
print("   %-6s %-10s %-10s %-12s %-12s" % ("工况", "T_pos", "T_vel", "单环 |z|", "级联 |z|"))
for name, T in (("P-A", 1.0e-3), ("P-B", 250e-6)):
    from_previous = {"P-A": 1.215697, "P-B": 0.986924}[name]
    casc = np.abs(np.linalg.eigvals(A_cascade(T, KP, KI, KD, kv, kvi))).max()
    print("   %-6s %-10.4g %-10.4g %-12.6f %-12.6f  %s" % (
        name, T, T, from_previous, casc, "合格" if casc <= 0.995 else "★超判据"))
print()
print("=== P-A 若把速度环提速（T_vel 独立于 T_pos）能否救回 ===")
print("   注意：单速率模型只在 T_vel == T_pos 时成立，下面改用多速率前先看趋势——")
print("   速度环带宽 ω_v 提高 ⟹ kv 增大 ⟹ 位置环到速度环的增益下降。")
for ratio in (3.0, 6.0, 10.0, 20.0):
    wv = ratio * WN
    kv2, kvi2 = J * wv, J * wv * wv / 5.0
    m = np.abs(np.linalg.eigvals(A_cascade(1.0e-3, KP, KI, KD, kv2, kvi2))).max()
    print("   ω_v=%4.0f·ω_n (%7.0f rad/s)  kv=%8.4f  级联最坏 |z| = %.6f  %s" % (
        ratio, wv, kv2, m, "合格" if m <= 0.995 else "★超判据"))
print()
print("=== 反过来：降 P-A 的 ω_n（增益随之按 §2.2 构造式重算）===")
for f in (85, 60, 40, 30, 20):
    wn = 2 * np.pi * f
    kp, ki, kd = wn**2 * J, wn**2 * J * wn / 5.0, wn**2 * J * 5.0 / wn
    kvv, kvii = J * 3 * wn, J * 3 * wn * 3 * wn / 5.0
    m = np.abs(np.linalg.eigvals(A_cascade(1.0e-3, kp, ki, kd, kvv, kvii))).max()
    print("   f_n=%4d Hz (ω_n=%6.1f)  ω_n·T=%.4f  级联最坏 |z| = %.6f  %s" % (
        f, wn, wn * 1e-3, m, "合格" if m <= 0.995 else "★超判据"))