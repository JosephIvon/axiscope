"""一次性数据审查脚本（非产品代码）。
读 DaRUS-3600 的真实 TwinCAT Scope View 导出，验证 C1 契约假设。

TwinCAT Scope View 列布局：col0 = SampleTime，之后 (SampleTime, value) 成对交替，
故 names[k] 的真实列号 = 2*(k+1)。
"""
import io, math, statistics as st
import sys

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


PATH = "data/raw/Export10_244531.csv"
N_HEADER = 14

with io.open(PATH, "r", encoding="utf-8", errors="replace") as f:
    lines = [ln.rstrip("\r\n") for ln in f]

names = [t for i, t in enumerate(lines[6].split("\t")) if i % 2 == 1]
idx = {nm: 2 * k + 1 for k, nm in enumerate(names)}

data = []
for ln in lines[N_HEADER:]:
    c = ln.split("\t")
    if len(c) < 2 * len(names):
        continue
    try:
        data.append([float(x) if x not in ("", "NaN") else math.nan for x in c])
    except ValueError:
        continue

n = len(data)
col = lambda nm: [r[idx[nm]] for r in data]
tsample = [r[0] for r in data]

print(f"rows={n}  channels={len(names)}  (cols per row = {len(data[0])})")
print(f"SampleTime col: min={min(tsample)} max={max(tsample)} distinct={len(set(tsample))}")

for nm in ("bTrigger_Scope", "bTrigger_Record", "bTrigger_Export"):
    v = col(nm)
    print(f"{nm:16s} distinct={sorted(set(v))[:6]}  nonzero_ratio={sum(1 for x in v if x)/n:.3f}")

rec = [i for i, x in enumerate(col("bTrigger_Record")) if x != 0]
print(f"recorded samples = {len(rec)} / {n} ({len(rec)/n:.1%})")

def stats(nm):
    if nm not in idx:
        print(f"{nm:22s} MISSING"); return None
    v = [col(nm)[i] for i in (rec or range(n))]
    v = [x for x in v if not math.isnan(x)]
    if not v:
        print(f"{nm:22s} all-NaN"); return None
    return (min(v), st.mean(v), st.pstdev(v), max(v), v[0], v[-1])

print("\nchannel                 min        mean        std        max       first       last")
for nm in ("dPosition_test", "dPosition_test_tar", "dPosition_diff", "dVelocity_test",
           "dVelocity_test_tar", "dTorque_test", "dForce_load", "dForce_test",
           "dPosition_asco", "dPosition_lsv_enc", "dPosition_load", "dPosition_load_tar"):
    s = stats(nm)
    if s:
        print(f"{nm:22s} " + "  ".join(f"{x:9.4f}" for x in s))

tar, act, dif = col("dPosition_test_tar"), col("dPosition_test"), col("dPosition_diff")
res = [dif[i] - (tar[i] - act[i]) for i in (rec or range(n))]
res = [x for x in res if not math.isnan(x)]
print(f"\nFE identity  diff-(tar-act): mean={st.mean(res):+.6f} std={st.pstdev(res):.6f} max|.|={max(map(abs,res)):.6f}")
# 本样本 tar ≡ act（A-104 ⑤）⟹ 右端恒定、Pearson 无定义，故显式判退化而不是抛异常：
# KB2 §2/§4 将本脚本列为可重跑产物（KB0 §6 检查 27），抛异常会让后半段全部拿不到。
_tma = [tar[i] - act[i] for i in range(n)]
if st.pstdev(_tma) == 0.0:
    print("corr(diff, tar-act) = 无定义（tar − act 恒定 ⟺ 两列逐行全等，A-104 ⑤）")
else:
    print(f"corr(diff, tar-act) = {st.correlation(dif, _tma):.4f}")

dts = [tsample[i + 1] - tsample[i] for i in range(n - 1)]
med = st.median(dts) or 1
print(f"\ndt ms: median={st.median(dts)} distinct={len(set(dts))} jitter_ratio={st.pstdev(dts)/abs(med):.4f}")
print(f"elapsed={(tsample[-1]-tsample[0])/1000:.2f} s -> fs={1000/med:.1f} Hz  Nyquist={500/med:.1f} Hz")

mfw = col("bMovingForward")
print(f"bMovingForward distinct={sorted(set(mfw))[:5]} direction_changes={sum(1 for i in range(1,n) if mfw[i]!=mfw[i-1])}")
print(f"dForceSensorNo distinct={sorted(set(col('dForceSensorNo')))[:8]}")
print("NaN ratio =", f"{sum(1 for r in data for x in r[2:] if math.isnan(x))/(n*len(names)):.4f}")
