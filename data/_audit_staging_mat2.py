import glob, os, csv
import numpy as np
from scipy.io import loadmat
import sys

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


MAT = "data/staging/原始mat"
CSVS = sorted(glob.glob("data/staging/*.csv"))

# 1) CSV header inventory
print("### CSV headers")
for p in CSVS:
    with open(p, "r", encoding="utf-8-sig") as f:
        head = f.readline().rstrip("\n").rstrip("\r")
    print(" ", os.path.basename(p))
    print("    ", head)
print("   n_csv =", len(CSVS))

print("\n### mat channel list")
for p in sorted(glob.glob(MAT + "/*.mat")):
    m = loadmat(p)
    ks = [k for k in m if not k.startswith("__") and k != "tout"]
    print(" ", os.path.basename(p), len(ks), ks)

# 2) candidate exact identities
print("\n### candidate identity residuals (max|resid| over full record)")
combos = [
    ("j1_etheta_pos", "theta1", "q1"),
    ("j1_etheta_pos", "theta1", "j1_qd"),
    ("j1_eq", "q1", "j1_qd"),
    ("j1_eq", "theta1", "q1"),
    ("j1_eq", "theta1", "j1_qd"),
    ("j2_eq", "q2", "j2_qd"),
    ("j2_etheta_pos", "theta2", "q2"),
]
for p in sorted(glob.glob(MAT + "/*.mat")):
    m = loadmat(p)
    print(" ", os.path.basename(p))
    for tgt, a, b in combos:
        if not all(k in m for k in (tgt, a, b)):
            continue
        t = np.asarray(m[tgt], float).ravel()
        x = np.asarray(m[a], float).ravel()
        y = np.asarray(m[b], float).ravel()
        r1 = np.max(np.abs(t - (x - y)))
        r2 = np.max(np.abs(t - x))          # direct
        scale = max(np.ptp(x), np.ptp(y))
        print("    %-14s vs (%s-%s): max|resid|=%.3e   scale=%.3e   | vs %s direct max=%.3e"
              % (tgt, a, b, r1, scale, a, r2))

# 3) does CSV row k equal mat row k for shared channels?
print("\n### CSV vs MAT per-row equality (first matching pair by name)")
pairs = [("Controller1Periodic", "Controller1周期"), ("Controller1Point2Point", "Controller1点位")]
for matname, prefix in pairs:
    mp = os.path.join(MAT, matname + ".mat")
    if not os.path.exists(mp):
        print("  skip", mp)
        continue
    m = loadmat(mp)
    csvp = [p for p in CSVS if prefix in os.path.basename(p)]
    if not csvp:
        print("  no csv for", prefix)
        continue
    with open(csvp[0], "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    hdr = rows[0]
    n_csv = len(rows) - 1
    print("  %s: csv rows=%d  mat rows=%d" % (prefix, n_csv, len(np.asarray(m["tout"]).ravel())))
    for c in hdr:
        if c not in m:
            print("    col %-14s NOT IN MAT" % c)
            continue
        mv = np.asarray(m[c], float).ravel()
        k = min(n_csv, len(mv))
        a = np.array([float(r[hdr.index(c)]) for r in rows[1:1 + k]])
        d = np.max(np.abs(a - mv[:k]))
        print("    col %-14s max|csv-mat| = %.3e" % (c, d))