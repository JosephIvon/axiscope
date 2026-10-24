"""一次性数据审查脚本（非产品代码）：复算 Export10_244531 的 `*_diff` 恒等式与逐列差。

KB0 A-104 的实测依据。用法（仓库根）：
    PYTHONPATH=src python data/probe_diff_identity.py
"""
import itertools
import sys

sys.path.insert(0, "src")
from axiscope import twincat  # noqa: E402

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


PATH = "data/raw/Export10_244531.csv"

table = twincat.read_scope(PATH)


def col(name):
    return [float(x) for x in table.data[name]]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def absmx(a):
    return max(abs(x) for x in a)


def ptp(a):
    return max(a) - min(a)


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb)


pos = [c.name for c in table.columns if c.name.startswith("dPosition")]
print("样本：%s，通道 %d，行 %d" % (PATH, len(table.columns), len(col("dPosition_diff"))))
print("\n== 1. `*_diff` 是否恒等于两绳之和 ==")
for diff_name, pair in (("dPosition_diff", ("dPosition_test", "dPosition_load")),
                        ("dVelocity_diff", ("dVelocity_test", "dVelocity_load"))):
    d = col(diff_name)
    rhs = [-x - y for x, y in zip(col(pair[0]), col(pair[1]))]
    print("  %-16s ≡ -(%s + %s) : 行级最大残差 %.3g | corr %.6f | 值域 %.5f…%.5f"
          % (diff_name, pair[0], pair[1], absmx(sub(d, rhs)), corr(d, rhs), min(d), max(d)))

print("\n== 2. 两绳守恒：总绳长残差 vs 单绳行程 ==")
s = [x + y for x, y in zip(col("dPosition_test"), col("dPosition_load"))]
print("  p_test ∈ [%.5f, %.5f]，p_load ∈ [%.5f, %.5f]，p_test+p_load ∈ [%.5f, %.5f]（摆动 %.2f mm）"
      % (min(col("dPosition_test")), max(col("dPosition_test")),
         min(col("dPosition_load")), max(col("dPosition_load")),
         min(s), max(s), ptp(s) * 1000))

print("\n== 3. 指令轨/反馈轨逐行差（§4.10 复算） ==")
for a, b in (("dPosition_test", "dPosition_test_tar"), ("dPosition_load", "dPosition_load_tar"),
             ("dVelocity_test", "dVelocity_test_tar"), ("dVelocity_load", "dVelocity_load_tar"),
             ("dForce_load", "dForce_tar"), ("dPosition_asco", "dPosition_asco_enc")):
    x, y = col(a), col(b)
    ndiff = sum(1 for u, v in zip(x, y) if abs(u - v) > 1e-12)
    print("  %-18s vs %-20s 差异 %5d/%d 行 | 峰值 %.5f" % (a, b, ndiff, len(x), absmx(sub(x, y))))

print("\n== 4. 反向核对 A-104 撤销的数字：穷举位置列配对，看谁能给出 −0.035…−28.343 与 corr −0.9809 ==")
target = (-28.343, -0.035)
dcol = col("dPosition_diff")
scored, corrs = [], []
for a, b in itertools.combinations(pos, 2):
    rhs = [-x - y for x, y in zip(col(a), col(b))]
    scored.append((abs(min(rhs) - target[0]) + abs(max(rhs) - target[1]), a, b, min(rhs), max(rhs)))
    corrs.append((abs(corr(dcol, rhs) + 0.9809), a, b, corr(dcol, rhs)))
scored.sort()
corrs.sort()
print("  配对数 %d，值域最接近 [−28.343, −0.035] 的 3 组：" % len(scored))
for dist, a, b, lo, hi in scored[:3]:
    print("   |Δ|=%7.2f  -( %s + %s ) ∈ [%.4f, %.4f]" % (dist, a, b, lo, hi))
print("  ⟹ 无任何两列之和落在该区间（最近的一组两端合计差 %.1f）——区间不可由本文件复现。"
      % scored[0][0])
print("  与 dPosition_diff 的 corr 最接近 −0.9809 的 3 组：")
for dist, a, b, r in corrs[:3]:
    print("   corr( dPosition_diff, -(%s + %s) ) = %.4f" % (a, b, r))
print("  ⟹ 唯一与 dPosition_diff 强相关的就是它自己的两条原料列（corr +1.000000），"
      "−0.9809 同样不可复现。")

print("\n== 5. fe 自检在本样本退化 ==")
fe = sub(col("dPosition_test_tar"), col("dPosition_test"))
print("  fe = pos_cmd - pos_fb 的最大绝对值 %.3g ⟹ 方差为零，corr(fe, dPosition_diff) 无定义"
      % absmx(fe))

print("\n== 6. 交叉验证配对的资格（KB2 §3.4 / A-105 引用的数字） ==")
for a, b in (("dPosition_asco", "dPosition_asco_enc"),
             ("dPosition_lsv_enc", "dPosition_asco_enc"),
             ("dPosition_test", "dPosition_lsv_enc")):
    x, y = col(a), col(b)
    dif = sub(x, y)
    print("  %-18s vs %-20s corr %.6f | 逐行差 ∈ [%.5f, %.5f] mean %.5f std %.6f | 离散值 %d vs %d"
          % (a, b, corr(x, y), min(dif), max(dif), sum(dif) / len(dif),
             (sum((v - sum(dif) / len(dif)) ** 2 for v in dif) / len(dif)) ** 0.5,
             len(set(round(v, 9) for v in x)), len(set(round(v, 9) for v in y))))
print("  行程：", " ".join("%s ∈ [%.5f, %.5f]（span %.5f）" % (n, min(col(n)), max(col(n)),
                                                            ptp(col(n)))
                          for n in ("dPosition_asco", "dPosition_asco_enc", "dPosition_lsv_enc",
                                    "dPosition_test", "dPosition_load")))
