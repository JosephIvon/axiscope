"""KB5 §1.5 位置环稳定性：把「子代理说 P-A、P-B 都不行」这句话拆开逐条验。

两版建模都错过，记在册免得后人重犯：
  v1  e_prev 那行写成 e_prev' = e_prev − theta ⟹ 多出一个假的 z=+1 积分极点
  v2  kd 低通接成独立积分环节、没接回 u_k ⟹ 扫出一排 |z|=1.000000
本版：无滤波走 4 状态（微分 = kd·Δe/T），有滤波走 5 状态（y_f 由 a·Δe 驱动并进 u_k）。

  x_k = [theta, omega, I, e_prev]            e_k = −theta_k（阶跃后）
  u_k = kp·e_k + ki·I_k + kd·(e_k − e_prev_k)/T
  theta_{k+1} = theta_k + T·omega_k + (T²/2J)·u_k
  omega_{k+1} = omega_k + (T/J)·u_k
  I_{k+1}     = I_k + T·e_k
  e_prev_{k+1} = e_k
滤波版把最后一项换成  y_{k+1} = (1−a)·y_k + a·(e_k − e_prev_k)，a = ω_f·T/(2+ω_f·T)，
u_k 里的微分项用 kd·y_k。
"""
import numpy as np

WN = 2 * np.pi * 85.0
J = 8.11e-6
kp, ki, kd = WN**2 * J, WN**2 * J * WN / 5.0, WN**2 * J * 5.0 / WN


def A_plain(T, kp, ki, kd):
    M = np.zeros((4, 4))
    d = kd / T
    M[0, 0] = 1.0 - (kp + d) * T * T / (2.0 * J)
    M[0, 1] = T
    M[0, 2] = ki * T * T / (2.0 * J)
    M[0, 3] = -d * T * T / (2.0 * J)
    M[1, 0] = -(kp + d) * T / J
    M[1, 1] = 1.0
    M[1, 2] = ki * T / J
    M[1, 3] = -d * T / J
    M[2, 0] = -T
    M[2, 2] = 1.0
    M[3, 0] = -1.0
    return M


def A_filt(T, kp, ki, kd, wf):
    a = wf * T / (2.0 + wf * T)
    M = np.zeros((5, 5))
    M[0, 0] = 1.0 - kp * T * T / (2.0 * J)
    M[0, 1] = T
    M[0, 2] = ki * T * T / (2.0 * J)
    M[0, 4] = kd * T * T / (2.0 * J)
    M[1, 0] = -kp * T / J
    M[1, 1] = 1.0
    M[1, 2] = ki * T / J
    M[1, 4] = kd * T / J
    M[2, 0] = -T
    M[2, 2] = 1.0
    M[3, 0] = -1.0
    M[4, 0] = -a
    M[4, 3] = -a
    M[4, 4] = 1.0 - a
    return M


def worst(A):
    return float(np.abs(np.linalg.eigvals(A)).max())


print("ω_n=%.4f rad/s  kp=%.4f  ki=%.4f  kd=%.6f  J=%.3e" % (WN, kp, ki, kd, J))
print()
print("=== 自洽性：无滤波、T→0 应回到连续域 PID 根 −53.3105±95.0881j ===")
for T in (1e-3, 1e-4, 1e-5):
    z = np.linalg.eigvals(A_plain(T, kp, ki, kd))
    d = min(abs(r - (-53.3105 + 95.0881j)) for r in z)
    print("   T=%-8.0e 最小根差 = %.3e   最坏 |z| = %.6f" % (T, d, np.abs(z).max()))
print()
print("=== (2) 无 kd 滤波，刚体单惯量，未含速度/电流内环 ===")
for name, T in (("P-A", 1.0e-3), ("P-B", 250e-6)):
    m = worst(A_plain(T, kp, ki, kd))
    print("   %-4s T=%-8.4g 最坏 |z| = %.6f  %s" % (
        name, T, m, "合格" if m <= 0.995 else "★超判据"))
print()
print("=== (3) 补上规格要求的 kd 一阶低通：ω_f 是决定项，而 KB5 没给这个数 ===")
print("   %-16s %-12s %-12s" % ("ω_f", "P-A |z|", "P-B |z|"))
print("   %-16s %-12.6f %-12.6f" % ("不滤波", worst(A_plain(1e-3, kp, ki, kd)),
                                    worst(A_plain(250e-6, kp, ki, kd))))
for wf in (20 * WN, 10 * WN, 5 * WN, 3 * WN, 2 * WN, WN):
    print("   %-16s %-12.6f %-12.6f" % ("%.0f rad/s" % wf,
                                       worst(A_filt(1e-3, kp, ki, kd, wf)),
                                       worst(A_filt(250e-6, kp, ki, kd, wf))))