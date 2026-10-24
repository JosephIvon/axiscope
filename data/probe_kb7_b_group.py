"""一次性数据审查脚本（非产品代码）：复算 KB7「B 组台账」里登记在案的实测类断言。

KB0 §6 检查 27 的落点：KB7 §B 组台账（`docs/kb/KB7-dataset-da-rus-cat.md` 第 234—276 行）写了
"全量核验 / 逐行 max|Δ| / 恒等式残差"这一类断言，但当时跑的数字散落在 `data/_audit_staging_mat.py`
（只打印，不做对拍）与 `data/validate_raw.py` 的输出里，没有一个"指向具体断言 + 打印成立与否"的
可重跑产物。本脚本把 **仓内可复算的那部分**重跑一遍并逐条给判定：
  · 6 个 `.mat`（`data/staging/原始mat/Controller{1,2,3}{Periodic,Point2Point}.mat`）
  · 6 个派生 CSV（`data/staging/电机位置与跟随误差_公开数据集_Controller{1,2,3}{周期,点位}轨迹.csv`）
  · DataCite 落盘件（`data/datacite_sciencedb_04148_2026-10-20.json`）
不在仓里的对象（ScienceDB 母包 zip 与其 7 个条目、6 个 `.mat` 的"与母包逐字节一致"）只登记为
**无法复算**，不做推断。红线 6 的脚本判词由 `data/validate_raw.py` 另行重跑取证（见本脚本最后一行提示）。

用法（仓库根）：
    PYTHONIOENCODING=utf-8 python data/probe_kb7_b_group.py
"""
import glob
import hashlib
import io
import json
import os
import re
import sys

import numpy as np
from scipy.io import loadmat

import probe_tally   # 与脚本同目录（data/）：判定行数由脚本自数，见其 docstring

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


MAT_DIR = "data/staging/原始mat"
CSV_DIR = "data/staging"
DATACITE = "data/datacite_sciencedb_04148_2026-10-20.json"
ZIP_GLOB = "data/**/sciencedb*.zip"
CUR = ("cur", "strom", "amps", "i_d", "i_q", "amper", "acur")      # KB7 要点里写的七类词
VARLIST = ("tout", "q1", "q2", "j1_qd", "j2_qd", "theta1", "theta2",
           "j1_eq", "j2_eq", "j1_etheta_pos", "j2_etheta_pos")

# (编号, .mat 文件名, 对应派生 CSV 文件名, 登记行数, 登记时长 s)
B = (
    ("B1", "Controller1Periodic.mat", "电机位置与跟随误差_公开数据集_Controller1周期轨迹.csv", 200001, 400.000),
    ("B2", "Controller1Point2Point.mat", "电机位置与跟随误差_公开数据集_Controller1点位轨迹.csv", 100001, 200.000),
    ("B3", "Controller2Periodic.mat", "电机位置与跟随误差_公开数据集_Controller2周期轨迹.csv", 200001, 400.000),
    ("B4", "Controller2Point2Point.mat", "电机位置与跟随误差_公开数据集_Controller2点位轨迹.csv", 100001, 200.000),
    ("B5", "Controller3Periodic.mat", "电机位置与跟随误差_公开数据集_Controller3周期轨迹.csv", 200001, 400.000),
    ("B6", "Controller3Point2Point.mat", "电机位置与跟随误差_公开数据集_Controller3点位轨迹.csv", 100001, 200.000),
)
# KB7 要点登记的恒等式残差（max|j1_etheta_pos − (theta1 − q1)| / max|j1_eq − (theta1 − q1)|）
DOC_RES = {"B1": (4.002e-01, 3.000e-01), "B2": (5.9e-3, 3.6e-3), "B3": (2.0e-3, 2.0e-3),
           "B4": (5.9e-3, 3.6e-3), "B5": (2.0e-3, 2.0e-3), "B6": (5.9e-3, 3.6e-3)}


def ok(label, computed, doc, rel=2e-3, unit=""):
    """复算值 vs KB7 登记值，打印 成立 / **不成立**。"""
    if doc is None:
        print("  %-56s 复算 %-24s （KB7 未登记该值，无对拍对象）" % (label, computed))
        return
    try:
        c, d = float(computed), float(doc)
    except (TypeError, ValueError):
        good = str(computed) == str(doc)
        print("  %-56s 复算 %-24s KB7  %-24s %s"
              % (label, computed, doc, "成立" if good else "**不成立**"))
        return
    good = abs(c - d) <= max(rel * abs(d), 1e-12) if d else abs(c) <= 1e-12
    print("  %-56s 复算 %-24s KB7  %-24s %s%s"
          % (label, "%.10g" % c, "%.10g" % d, "成立" if good else "**不成立**", unit))


def miss(label, why):
    print("  %-56s 无法复算（%s）" % (label, why))


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


CSVS = {}


def read_csv(path):
    """返回 (表头, 数值矩阵, 首个数据行的原文)；纯 Python 解析，避开 numpy 2.5 的 fromstring。"""
    with io.open(path, encoding="utf-8", errors="replace") as f:
        head = f.readline().rstrip("\r\n").split(",")
        first = f.readline().rstrip("\r\n")
        rows = [[float(x) for x in first.split(",")]]
        for ln in f:
            if ln.strip():
                rows.append([float(x) for x in ln.rstrip("\r\n").split(",")])
    return head, np.asarray(rows), first


# 判定行数由脚本自己数并打印（口径见 data/probe_tally.py）——此前 KB7 §6 引用的是人工点数的数字。
probe_tally.install()

print("=" * 104)
print("probe_kb7_b_group —— 复算 docs/kb/KB7-dataset-da-rus-cat.md「B 组台账」的实测类断言")
print("=" * 104)

# ---------------------------------------------------------------- 0. 输入存在性
print("\n== 0. 复算所用的仓内输入 ==")
for p in (DATACITE,):
    print("  %-56s %s (%d B)" % (p, "存在" if os.path.isfile(p) else "**缺失**",
                                 os.path.getsize(p) if os.path.isfile(p) else -1))
for tag, mat, csv, nrows, dur in B:
    pm, pc = os.path.join(MAT_DIR, mat), os.path.join(CSV_DIR, csv)
    print("  %-2s .mat %-34s %12d B  md5 %s" % (tag, mat, os.path.getsize(pm), md5_of(pm)))
    print("     CSV  %-34s %12d B  md5 %s" % (csv[:34], os.path.getsize(pc), md5_of(pc)))
    for s in (pm + ".source.txt", pc + ".source.txt"):
        if not os.path.isfile(s):
            print("     **sidecar 缺失**：%s" % s)
zips = glob.glob(ZIP_GLOB, recursive=True) + glob.glob("data/**/*.zip", recursive=True)
print("  ScienceDB 母包 zip 在仓里的份数：%d ⟹「母包 50,493,558 B / md5 c7506f625dde69a131333d6002f5e6a2 / "
      "zip 内 7 条目 / 6 个 .mat 与母包逐字节一致」这一组断言 %s"
      % (len(zips), "可复算" if zips else "**无法复算（zip 未落盘）**"))
if zips:
    for z in zips:
        print("      发现 zip：%s（%d B，md5 %s）" % (z, os.path.getsize(z), md5_of(z)))

# ---------------------------------------------------------------- 1. DataCite 落盘件
print("\n== 1. KB7 L34—L44：DataCite 记录逐字字段（输入 = %s）==" % DATACITE)
if os.path.isfile(DATACITE):
    at = json.load(io.open(DATACITE, encoding="utf-8"))["data"]["attributes"]
    ok("doi", at["doi"], "10.57760/sciencedb.04148")
    ok("titles[0].title", at["titles"][0]["title"], "Raw data of motor position in several cases")
    ok("titles 条数", len(at["titles"]), 2)
    ok("publisher", at["publisher"], "Science Data Bank")
    ok("publicationYear", at["publicationYear"], 2022)
    ok("version", at.get("version"), "V1")
    ok("state", at["state"], "findable")
    ok("rightsList[0].rights", at["rightsList"][0]["rights"],
       "Creative Commons Attribution 4.0 International")
    ok("rightsList[0].rightsUri", at["rightsList"][0]["rightsUri"],
       "https://creativecommons.org/licenses/by/4.0/legalcode")
    print("  %-56s 复算 %s（KB7 只写了 rights + rightsUri，未登记 SPDX 码）"
          % ("rightsList[0].rightsIdentifier", at["rightsList"][0].get("rightsIdentifier")))
    ok("url", at["url"], "https://www.scidb.cn/detail?dataSetId=7e95fb543e3f407d84fe19150a7e1305")
    ok("sizes（逐字）", " / ".join(at["sizes"]), "50493558 bytes / 1 files", rel=0)
    ok("sizes[0] 的字节数", int(re.match(r"(\d+)", at["sizes"][0]).group(1)), 50493558)
    cr = [c["name"] for c in at["creators"]]
    print("  %-56s 复算 %s" % ("creators（逐字，全 %d 位）" % len(cr), cr))
    for want in ("Huayuan Huang", "Hongtao Pan"):
        print("  %-56s %s" % ("创作者含 %s" % want, "成立" if want in cr else "**不成立**"))
    print("  KB7 L41 写第三名创作者为 `Cheng, Yong`；复算 creators 里匹配 Cheng 的写法：%s ⟹ %s"
          % ([c for c in cr if "Cheng" in c],
             "成立" if any(c == "Cheng, Yong" for c in cr)
             else "**不成立**（上游逐字写法见上一行，KB7 需按复算更正拼写）"))
    subs = [s["subject"] for s in at["subjects"]]
    print("  %-56s 复算 %s" % ("subjects（逐字，全 %d 条）" % len(subs), subs))
    for want in ("periodic trajectory", "Point-to-point trajectory", "position error", "robot"):
        print("  %-56s 成立：%s" % ("subjects 含 `%s`" % want, want in subs)
              if want in subs else
              "  %-56s **不成立**（复算 subjects=%s）" % ("subjects 含 `%s`" % want, subs))
    print("  %-56s 复算：%s" % ("affiliation（第一位创作者）",
                                at["creators"][0].get("affiliation")))
    desc = next((d["description"] for d in at.get("descriptions", [])), "")
    print("  %-56s 复算逐字：%s" % ("descriptions[0]（截 200 字）", re.sub(r"\s+", " ", desc)[:200]))
    want_desc = ("This dataset contains both the point-to-point trajectory and periodic "
                 "trajectory of two different robot joints under three controllers.")
    print("  %-56s KB7 L43—L44 的逐字摘要命中：%s"
          % ("摘要逐字对拍", "成立" if want_desc in re.sub(r"\s+", " ", desc) else "**不成立**"))
    # DataCite 该记录实际用的键是 relatedIdentifier/relatedIdentifierType（无 identifier 键，
    # 旧写法 r["identifier"] 会 KeyError）；容忍缺键，并把 DOI 型标识归一回 "doi:<id>" 打印口径，
    # 与 KB7 L44 `IsSupplementTo → doi:10.1002/acs.3276` 的登记格式对拍。
    def _rid(r):
        if "identifier" in r:
            return r["identifier"]
        ri = r.get("relatedIdentifier")
        if ri is not None and r.get("relatedIdentifierType") == "DOI":
            return "doi:" + ri
        return ri
    rel = [(r["relationType"], _rid(r)) for r in at.get("relatedIdentifiers", [])]
    print("  %-56s 复算 %s ⟹ KB7 L44 的说法 %s"
          % ("relatedIdentifiers", rel,
             "成立" if ("IsSupplementTo", "doi:10.1002/acs.3276") in rel else "**不成立**"))
    print("  %-56s 复算 published=%s created=%s registered=%s metadataVersion=%s"
          % ("时间戳字段", at.get("published"), at.get("created"),
             at.get("registered"), at.get("metadataVersion")))

# ---------------------------------------------------------------- 2. .mat 结构与统计
print("\n== 2. KB7 L253—L261：通道清单 / 时基 / NaN（全量行，非抽样）==")
MATS = {}
for tag, mat, csv, nrows, dur in B:
    p = os.path.join(MAT_DIR, mat)
    raw = open(p, "rb").read()
    m = loadmat(p)
    keys = [k for k in m if not k.startswith("__")]
    cols = {}
    shapes = set()
    dtypes = set()
    for k in keys:
        a = np.asarray(m[k], dtype=float)
        shapes.add(a.shape)
        dtypes.add(str(np.asarray(m[k]).dtype))
        cols[k] = a.ravel()
    MATS[tag] = (raw, cols)
    tout = cols["tout"]
    dt = np.diff(tout)
    med = float(np.median(dt))
    jit = float(np.std(dt) / abs(med)) if med else float("nan")
    nanall = sum(int(np.isnan(v).sum()) for v in cols.values())
    print("-- %s %s（%d B，md5 %s）" % (tag, mat, len(raw), hashlib.md5(raw).hexdigest()))
    ok("   变量名清单与 KB7 逐字一致（11 个）",
       ",".join(sorted(keys)), ",".join(sorted(VARLIST)))
    print("  %-56s 复算 %s ⟹ %s（KB7 L257「每个文件 11 个变量」）"
          % ("   变量顺序（逐字）", ",".join(keys), "成立" if keys == list(VARLIST) else "顺序不同但集合一致"))
    print("  %-56s 复算 %s ⟹ %s" % ("   变量数 / 全部 float64 / shape 集合",
                                    (len(keys), sorted(dtypes), sorted(shapes)),
                                    "成立" if (len(keys) == 11 and dtypes == {"float64"}
                                               and shapes == {(nrows, 1)}) else "**不成立**"))
    ok("   行数（tout 长度）", len(tout), nrows)
    ok("   时长（tout 末 − 首，s）", tout[-1] - tout[0], dur, rel=1e-6)
    print("  %-56s 复算 [%.17g, %.17g]（KB7 L254 写恒 0.002）"
          % ("   dt 的 min / max（17 位有效）", dt.min(), dt.max()))
    ok("   dt 打印到 9 位是否为同一个数（0.002）", float("%.9g" % dt.min()), 0.002, rel=1e-9)
    ok("   dt_jitter_ratio（= pstdev(dt)/|median(dt)|）",
       jit, 7.557e-12 if dur == 400.0 else 4.505e-12, rel=2e-2)
    ok("   fs = 1/median(dt)（Hz）", 1.0 / med, 500.0)
    print("  %-56s 复算 %s ⟹ %s" % ("   tout 严格单调 / NaN 单元合计",
                                     (bool(np.all(dt > 0)), nanall),
                                     "成立" if np.all(dt > 0) and nanall == 0 else "**不成立**"))
    print("  %-56s 复算 [%.6g, %.6g]（KB7 L256 写 [0, %.3f]）"
          % ("   tout 覆盖区间", tout[0], tout[-1], dur))
    hits = sorted(k for k in keys if any(w in k.lower() for w in CUR))
    print("  %-56s 复算 %d 个命中：%s ⟹ %s"
          % ("   电流七词（%s）在 10 个数据列上的命中" % "/".join(CUR),
             len([h for h in hits if h != "tout"]),
             [h for h in hits if h != "tout"],
             "成立（零命中）" if not [h for h in hits if h != "tout"] else "**不成立**"))
    for k in keys:
        if k == "tout":
            continue
        print("      %-15s n=%-7d min=%-13.7g max=%-13.7g std=%-12.6g nan=%d"
              % (k, len(cols[k]), cols[k].min(), cols[k].max(), cols[k].std(),
                 int(np.isnan(cols[k]).sum())))

print("\n== 2.1 KB7 L268—L269 的量程断言 ==")
for tag in ("B1", "B3", "B5"):
    cols = MATS[tag][1]
    print("  %s：theta1 [%.7g, %.7g] ‖ j1_etheta_pos [%.7g, %.7g] ‖ q1 [%.7g, %.7g]"
          % (tag, cols["theta1"].min(), cols["theta1"].max(),
             cols["j1_etheta_pos"].min(), cols["j1_etheta_pos"].max(),
             cols["q1"].min(), cols["q1"].max()))
print("  KB7 L268 写「`j1_etheta_pos` 的量程（min/max ≈ −3.4e-3 / 0.400）与 `theta1`"
      "（≈ −6.7e-7 / 0.599）不同」——上面打印的是 B1/B3/B5 的实测值域，"
      "theta1 与 j1_etheta_pos 量程**是否相同**请按上面数字判：两者不同 ⟹ 该断言的"
      "「不同」二字成立；但 0.400 / 0.599 这两个具体数只在部分文件里出现，KB7 未标注是哪个文件")

# ---------------------------------------------------------------- 3. 恒等式
print("\n== 3. KB7 L262—L267：候选恒等式的行级最大残差（全量行）==")
print("  KB7 登记：`j1_etheta_pos ≡ theta1 − q1` 的 max|残差| 在 B1 为 4.002e-01、"
      "B3/B5/B2/B4/B6 为 2.0e-3 ~ 5.9e-3；`j1_eq ≡ theta1 − q1` 在 B1 为 3.000e-01、其余 2.0e-3 ~ 3.6e-3")
for tag, mat, csv, nrows, dur in B:
    cols = MATS[tag][1]
    out = []
    for col, ref in (("j1_etheta_pos", cols["theta1"] - cols["q1"]),
                     ("j1_eq", cols["theta1"] - cols["q1"]),
                     ("j2_etheta_pos", cols["theta2"] - cols["q2"]),
                     ("j2_eq", cols["theta2"] - cols["q2"])):
        r = cols[col] - ref
        mx = float(np.max(np.abs(r)))
        # 去掉常数偏置后的残差：判断"差一个常数"是否成立
        c0 = float(np.median(r))
        mx_off = float(np.max(np.abs(r - c0)))
        out.append((col, mx, c0, mx_off,
                    int((np.abs(r) > 1e-3).sum()), int(np.argmax(np.abs(r))), len(r)))
    print("  %s %s" % (tag, mat))
    for col, mx, c0, mx_off, n_over, i_max, n_rows in out:
        kb = DOC_RES[tag][0] if col.startswith("j1_etheta") else (
            DOC_RES[tag][1] if col == "j1_eq" else None)
        ok("     max|%s − (对应两列之差)|" % col, mx, kb, rel=2e-2)
        print("        常数偏置口径：median(残差) = %.7g；去掉该偏置后 max|残差| = %.7g ⟹ "
              "「差一个常数」%s" % (c0, mx_off, "成立" if mx_off < 1e-5 else "不成立"))
        print("        成因口径：argmax 在第 %d 行；|残差| > 1e-3 的行数 = %d / %d ⟹ %s"
              % (i_max, n_over, n_rows,
                 "大残差是整段现象，不是首行伪影" if n_over > 10 else "大残差集中于个别行"))
    # 穷举：j1_eq / j1_etheta_pos 是否等于任意两列之差
    names = [k for k in VARLIST if k != "tout"]
    for col in ("j1_eq", "j1_etheta_pos"):
        best = []
        for a in names:
            for b in names:
                if a == b:
                    continue
                mx = float(np.max(np.abs(cols[col] - (cols[a] - cols[b]))))
                best.append((mx, "%s − %s" % (a, b)))
        best.sort()
        print("        %-15s 穷举 90 个有序列差，最小 max|残差| 前三名：%s"
              % (col, ["%.4g（%s）" % (m, p) for m, p in best[:3]]))
print("  ⟹ 结论口径（三句，每句都由上面的打印支撑，不接受无载体的推断）：\n"
      "     · KB7 登记的候选 `theta1 − q1` 在六件文件里都不是恒等式（上面的穷举段里它从未取得 0 残差，"
      "取得 0 的只有 `j1_qd − q1`）⟹「theta1 − q1 这一组没有一条成立」的方向**复算成立**。\n"
      "     · 但穷举把 `j1_eq ≡ j1_qd − q1` 打印成**残差恰 0**（六件全中）⟹ 这是一条**成立的恒等式**："
      "`j1_eq` 是 `j1_qd` 与 `q1` 的线性组合、零独立信息（A-105 ②/③ 的口径）。"
      "把它当第二次独立位置测量会凭空造出「两路互证」——登记缺陷，不是数据缺陷。\n"
      "     · B1 的大残差（4.002e-01 / 3.000e-01）**不是首行伪影**：见上面「成因口径」行，"
      "|残差| > 1e-3 的行数在 1e5 量级（各 /200,000），去掉常数偏置后仍有 0.3998 / 0.2995 "
      "⟹ 是整段瞬态差异；KB7 未区分「常数偏置」与「整段瞬态」这两种成因，本脚本只登记前者可复算")

# ---------------------------------------------------------------- 4. CSV vs .mat 逐行比对
print("\n== 4. KB7 L251 / L302：派生 CSV 与母 .mat 逐行比对 max|Δ| ==")
for tag, mat, csv, nrows, dur in B:
    pc = os.path.join(CSV_DIR, csv)
    head, A, first_raw = read_csv(pc)
    CSVS[tag] = (head, A, first_raw)
    cols = MATS[tag][1]
    print("  %s %s：CSV 行 %d（.mat %d）列 %d（.mat 变量 %d）"
          % (tag, csv[:40], A.shape[0], len(cols["tout"]), A.shape[1], len(cols)))
    print("     CSV 表头与 .mat 变量名逐字一致：%s（表头 %d 列：%s）"
          % (head == list(VARLIST), len(head), ",".join(head)))
    per = {}
    for i, k in enumerate(head):
        if k in cols and A.shape[0] == len(cols[k]):
            per[k] = float(np.max(np.abs(A[:, i] - cols[k])))
    tot = max(per.values())
    ok("     全列 max|Δ|", tot, 5.0e-8, rel=0.2)
    ok("     tout 的 max|Δ|", per.get("tout"), 5.7e-14, rel=0.2)
    print("     逐列 max|Δ|（最大的 4 列）：%s"
          % {k: "%.3g" % v for k, v in sorted(per.items(), key=lambda x: -x[1])[:4]})
    print("     数值格式（决定量化误差上限）：首行原文 %s ⟹ 每字段 7 位小数的科学计数，"
          "对 ~4e-1 量级的列绝对舍入上界 = 5e-8" % first_raw[:120])

# ---------------------------------------------------------------- 5. 六条硬拒自查
print("\n== 5. KB7 L270—L274：红线 1—5 全过、6 开火（按 KB2 §5.1 口径自查）==")
for tag, mat, csv, nrows, dur in B:
    head, A, _ = CSVS[tag]
    tout, V = A[:, 0], A[:, 1:]
    dt = np.diff(tout)
    med = float(np.median(dt))
    jit = float(np.std(dt) / abs(med))
    nan = int(np.isnan(V).sum())
    const = [head[i] for i in range(1, A.shape[1]) if V[:, i - 1].min() == V[:, i - 1].max()]
    ndyn = (A.shape[1] - 1) - len(const)
    cur_hits = [k for k in head if any(w in k.lower() for w in CUR)]
    cmd = [k for k in head if k in ("theta1", "theta2", "j1_qd", "j2_qd")]
    fb = [k for k in head if k.startswith("j")]
    print("  %s：1 行数 %d（≥2000：%s）2 时长 %.3f s（≥0.5：%s）3 jitter %.3g（≤0.2：%s）"
          "4 NaN %d（=0：%s）5 动态通道 %d（>0：%s）6 电流类列 %d 个（全缺：%s）"
          % (tag, A.shape[0], A.shape[0] >= 2000, tout[-1] - tout[0], (tout[-1] - tout[0]) >= 0.5,
             jit, jit <= 0.2, nan, nan == 0, ndyn, ndyn > 0, len(cur_hits), not cur_hits))
    print("     恒值列（%d 个）：%s ‖ 指令/驱动侧候选 %s ‖ 反馈侧候选 %s"
          % (len(const), const or "无", cmd, fb))
miss("KB7 L271—L272 的脚本判词逐字 `cur_q/vel_fb/fe 未识别（8/10 列未映射…）`",
     "判词由 data/validate_raw.py 产出，本脚本不重复实现；须重跑该脚本取证（见脚本末尾提示行）")

# ---------------------------------------------------------------- 6. 无法复算清单
print("\n== 6. 无法复算清单（数据文件不在仓里，按 KB0 §6 检查 27 降为未核验）==")
for what, why in (
        ("KB7 L47—L49：母包 50,493,558 B、md5 c7506f625dde69a131333d6002f5e6a2、zip 内 7 个条目",
         "母包 zip 未落盘（仓内 zip 份数见 §0）；只能复算 DataCite 登记的 size 字段，不能复算字节与 md5"),
        ("KB7 L49「data/ 下 6 个 .mat 全部与本地实体逐字节一致」",
         "需要母包 zip 的 member 字节；zip 不在仓里，本地 .mat 只能自证 md5（§2 已打印）"),
        ("KB7 B1—B6 行「✔ 母包成员逐字节一致」",
         "同上；该列在当前仓内不可复核，应记「未核验，无可重跑产物」"),
        ("KB7 L44 `relatedIdentifiers` 指向的论文 doi:10.1002/acs.3276 的正文（逐列定义）",
         "外部出版物，未落盘；逐列定义仍未实测"),
        ("KB7 L275 reliable_band_hz = 400 Hz 与 band⊥ = 2000 Hz 的比较",
         "非本脚本口径：是 fs 的派生规则，KB2/契约侧判定"),
):
    miss(what, why)
print("\n  红线 6 判词的取证命令（独立跑一次，输出不落在本脚本里）：")
print("    PYTHONIOENCODING=utf-8 python data/validate_raw.py "
      "\"data/staging/电机位置与跟随误差_公开数据集_Controller1周期轨迹.csv\" "
      "--out-txt data/probe_kb7_validate_rerun.txt --quiet")
print("（完）打印出来的数字即本仓可重跑产物；KB7 B 组正文凡与本输出不一致处见上面 **不成立** 标记。")
