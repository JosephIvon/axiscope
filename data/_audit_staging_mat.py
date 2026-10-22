import glob, os, hashlib
import numpy as np
from scipy.io import loadmat

CUR = ("cur", "strom", "amps", "i_d", "i_q", "amper", "acur", "ampere")

for p in sorted(glob.glob("data/staging/原始mat/*.mat")):
    b = open(p, "rb").read()
    print("=" * 78)
    print(os.path.basename(p), len(b), "B  md5", hashlib.md5(b).hexdigest())
    print("  header:", b[:80].decode("latin1").replace("\n", " | "))
    m = loadmat(p)
    keys = [k for k in m if not k.startswith("__")]
    print("  keys:", keys)
    tout = np.asarray(m.get("tout"), dtype=float).ravel()
    dt = np.diff(tout)
    med = float(np.median(dt))
    jit = float(np.std(dt) / abs(med)) if med else float("nan")
    print("  rows=%d  t0=%.6f  tN=%.6f  dur=%.6f s" % (len(tout), tout[0], tout[-1], tout[-1] - tout[0]))
    print("  dt_median=%.9g  dt_min=%.9g  dt_max=%.9g  jitter=%.3e  mono=%s"
          % (med, dt.min(), dt.max(), jit, bool(np.all(dt > 0))))
    print("  fs=%.6f Hz" % (1.0 / med if med else float("nan")))
    names = []
    for k in keys:
        if k == "tout":
            continue
        a = np.asarray(m[k], dtype=float).ravel()
        names.append(k)
        print("    %-14s n=%-7d min=%-14.6g max=%-14.6g std=%-13.6g nan=%d"
              % (k, len(a), a.min(), a.max(), a.std(), int(np.isnan(a).sum())))
    print("  cur-name hits:", [n for n in keys if any(t in n.lower() for t in CUR)])
    # cmd vs fb candidate pairs
    for c, f in (("theta1", "j1_etheta_pos"), ("theta2", "j2_etheta_pos")):
        if c in m and f in m:
            a = np.asarray(m[c], float).ravel()
            b2 = np.asarray(m[f], float).ravel()
            d = a - b2
            nz = int(np.count_nonzero(d))
            print("  %s - %s : nonzero %d/%d  |d|max=%.6g  std=%.6g"
                  % (c, f, nz, len(d), np.max(np.abs(d)), d.std()))
    for q, qd in (("q1", "j1_qd"), ("q2", "j2_qd")):
        if q in m and qd in m:
            a = np.asarray(m[q], float).ravel()
            b2 = np.asarray(m[qd], float).ravel()
            d = a - b2
            print("  %s - %s : nonzero %d/%d  |d|max=%.6g"
                  % (q, qd, int(np.count_nonzero(d)), len(d), np.max(np.abs(d))))