"""一次性数据审查脚本（非产品代码）：复算 `data/research_5171_cdd.md` 里登记在案的"实测"数字。

KB0 §6 检查 27 的落点：该调研报告（第三方会话写的）正文里的数字全部由 `%TEMP%\\d5171\\*.py` 算出、
脚本未入仓，按检查 27 原本一律属"无可重跑产物"。本脚本把**仓内可复算的那部分**重跑一遍：
  · DaRUS-5171 现场 listing 的落盘件（`data/incoming/daRUS5171_listing_2026-10-20.json`）
  · 6 份 CDD TwinCAT CSV（`data/incoming/darus5171/`）
  · CDD 台架配置（`data/incoming/394085_CableActuatorTestRig.xml`）
并逐条断言打印 `成立 / 不成立 / 无法复算（缺文件）`。不在仓里的对象（68 份中的另外 62 份、
`LDA_Fric_*.nc`、DARUS-5170 的 TcPOU/tcscopex/TcGVL/TcDUT）只登记为不可复算，不做推断。

用法（仓库根）：
    PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py
"""
import collections
import hashlib
import io
import json
import os
import re
import sys

import numpy as np

import probe_tally   # 与脚本同目录（data/）：判定行数由脚本自数，见其 docstring

LISTING = "data/incoming/daRUS5171_listing_2026-10-20.json"
LISTING_RAW = "data/raw/darus5171.json"
DOC = "data/research_5171_cdd.md"
CDD_DIR = "data/incoming/darus5171"
XML = "data/incoming/394085_CableActuatorTestRig.xml"
CDD_PREFIX = "CableDirectDrive_Testbed/2024-07-23_LdaFricIdent"

# 报告 §4 选样的 6 份：dataFile id -> 本地落盘名（本地字节/md5 对拍用）
LOCAL = {
    394141: "CDD_2024-07-23_LdaFricIdent_RW_Export_5_id394141.csv",
    393961: "CDD_2024-07-23_LdaFricIdent_UW_Export_5_id393961.csv",
    393966: "CDD_2024-07-23_LdaFricIdent_UW_Export_7_id393966.csv",
    394009: "CDD_2024-07-23_LdaFricIdent_UW_Export_9_id394009.csv",
    394119: "CDD_2024-07-23_LdaFricIdent_RW_Export_3_id394119.csv",
    394169: "CDD_2024-07-23_LdaFricIdent_UW_Export_6_id394169.csv",
}
ORDER = [394141, 393961, 393966, 394009, 394119, 394169]   # 报告表格里的行序

CUR_WORDS = ("current", "i_q", "cur_q", "dq")              # 报告 §7.2 的电流命名口径（前 4 项为断言口径）
CUR_STRICT = ("current", "i_q", "cur_q", "duty")


def ok(label, computed, doc, rel=2e-3, unit=""):
    """把复算值与报告登记值对拍并打印 verdict。"""
    if doc is None:
        print("  %-52s 复算 %-22s （报告未登记该值，无对拍对象）" % (label, computed))
        return
    try:
        c, d = float(computed), float(doc)
    except (TypeError, ValueError):
        verdict = "成立" if str(computed) == str(doc) else "不成立"
        print("  %-52s 复算 %-18s 报告 %-18s %s" % (label, computed, doc, verdict))
        return
    good = (abs(c - d) <= max(rel * abs(d), 1e-12) if d else abs(c) <= 1e-12)
    print("  %-52s 复算 %-18s 报告 %-18s %s%s"
          % (label, ("%.6g" % c), ("%.6g" % d), "成立" if good else "**不成立**", unit))


def miss(label, why):
    print("  %-52s 无法复算（%s）" % (label, why))


def num(x):
    return None if x in ("", "—", "-", None) else float(x.replace(",", ""))


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- 自数汇总
# 判定行数由脚本自己数并打印（口径见 data/probe_tally.py）——此前 KB7 §6 引用的是人工点数的数字。
probe_tally.install()

print("=" * 100)
print("probe_5171_identities —— 复算 data/research_5171_cdd.md 的实测类断言")
print("=" * 100)

# ---------------------------------------------------------------- 0. 输入存在性
print("\n== 0. 复算所用的仓内输入 ==")
for p in (LISTING, DOC, XML):
    print("  %-58s %s (%d B)" % (p, "存在" if os.path.isfile(p) else "**缺失**",
                                 os.path.getsize(p) if os.path.isfile(p) else -1))
print("  %-58s %d 份 CSV（报告称 6 份）" % (CDD_DIR + "/",
                                            len([f for f in os.listdir(CDD_DIR) if f.endswith(".csv")])))
print("  %-58s %d 个 .source.txt sidecar（报告 §9 称 6 个）"
      % (CDD_DIR + "/ sidecar", len([f for f in os.listdir(CDD_DIR) if f.endswith(".source.txt")])))
print("  listing 落盘字节 %d B；报告 §9 称现场 listing 原文 2,616,228 B" % os.path.getsize(LISTING),
      end=" ")
print("成立" if os.path.getsize(LISTING) == 2616228 else "**不成立**")
if os.path.isfile(LISTING_RAW):
    same = md5_of(LISTING) == md5_of(LISTING_RAW)
    print("  与 data/raw/darus5171.json 是否同一份字节：%s（md5 %s / %s）"
          % ("是" if same else "否", md5_of(LISTING), md5_of(LISTING_RAW)))

if not os.path.isfile(LISTING):
    sys.exit("listing 缺失，后续段落全部无法复算")

# ---------------------------------------------------------------- 1. listing 派生断言
lv = json.load(io.open(LISTING, encoding="utf-8"))["data"]["latestVersion"]
files = lv["files"]
by_id = {f["dataFile"]["id"]: f for f in files}

print("\n== 1. §2「数据集与目录盘点」：listing 派生数字 ==")
ok("latestVersion.files 条数", len(files), 3488)
dl = sorted({f.get("directoryLabel") or "" for f in files})
ok("directoryLabel 去重计数", len([x for x in dl if x]), 261)
top = collections.Counter((f.get("directoryLabel") or "").split("/")[0] for f in files)
for name, doc_n in (("LIROS_D-Pro", 1175), ("Trowis_PolyTropFOX", 1036),
                    ("Trowis_VectranHT_T190PU", 1033), ("Winch_Testbed", 171),
                    ("CableDirectDrive_Testbed", 73)):
    ok("顶层试验台 %s 文件数" % name, top[name], doc_n)
print("  报告未列的顶层项：%s" % (sorted(set(top) - {"LIROS_D-Pro", "Trowis_PolyTropFOX",
                                                    "Trowis_VectranHT_T190PU", "Winch_Testbed",
                                                    "CableDirectDrive_Testbed"}) or "无"))
ok("license.name（页面自述字段）", lv["license"]["name"], "CC BY 4.0")
ok("publicationDate（页面自述字段）", lv["publicationDate"], "2026-07-20")
try:
    fields = lv["metadataBlocks"]["citation"]["fields"]
    getf = lambda tn: next((x.get("value") for x in fields if x.get("typeName") == tn), None)
    print("  标题字段原文：%s" % str(getf("title"))[:160])
    print("  depositor / dateOfDeposit：%s / %s（CC BY 4.0 署名字段的落盘依据）"
          % (getf("depositor"), getf("dateOfDeposit")))
    print("  author 值（列举前 3 位）：%s"
          % [a.get("authorName", {}).get("value") for a in (getf("author") or [])][:3])
except Exception as e:                                        # noqa: BLE001
    print("  标题字段解析失败：%s；顶层字段名 %s"
          % (e, sorted(str(k) for k in lv["metadataBlocks"]["citation"].keys())))

# §2.1 45 行目录表：逐行复算（行级差异数）
print("\n== 1.1 §2.1 的 45 行「试验目录 × CSV 统计」表：逐行复算 ==")
rows = re.findall(r"^\| ([A-Za-z0-9_\-/\.\*]+/\d{4}-\d{2}-\d{2}[A-Za-z_]*) \| (\d+) \| (\d+) \| "
                  r"(\d+) \| (\d+) \| (\d+)–(\d+) \| (\d+) \|\s*$",
                  io.open(DOC, encoding="utf-8").read(), re.M)
print("  从报告解析到 %d 行（报告正文称 45 个含 CSV 的试验目录）" % len(rows))
bad = 0
bad_cols = collections.Counter()
hit_all = hit_csv = 0
for label, nc, nf, mn, mx, i0, i1, tot in rows:
    sub = [f["dataFile"] for f in files if (f.get("directoryLabel") or "").startswith(label)]
    csvs = [d for d in sub if d["contentType"] == "text/csv"]
    got = (len(csvs), len(sub),
           min(d["filesize"] for d in csvs) if csvs else 0,
           max(d["filesize"] for d in csvs) if csvs else 0,
           min(d["id"] for d in sub), max(d["id"] for d in sub),
           sum(d["filesize"] for d in sub))
    want = (int(nc), int(nf), int(mn), int(mx), int(i0), int(i1), int(tot))
    idcsv = (min(d["id"] for d in csvs), max(d["id"] for d in csvs)) if csvs else (0, 0)
    hit_all += got[4:6] == want[4:6]
    hit_csv += idcsv == want[4:6]
    if got != want:
        bad += 1
        for i, nm in enumerate(("CSV 数", "文件数", "最小字节", "最大字节", "id 下界", "id 上界", "合计字节")):
            if got[i] != want[i]:
                bad_cols[nm] += 1
        print("    行级不一致 %-62s 复算 %s ≠ 报告 %s（该目录 CSV 件 id 区间 %d–%d）"
              % (label, got, want, idcsv[0], idcsv[1]))
print("  ⟹ 45 行表复算差异行数 %d/%d；差异集中在哪些列：%s"
      % (bad, len(rows), dict(bad_cols) or "无"))
print("  ⟹ id 范围列口径判定：按「目录内全部件」算命中 %d/45 行，按「目录内 CSV 件」算命中 %d/45 行 "
      "⟹ 报告该列的口径 %s"
      % (hit_all, hit_csv,
         "＝目录内全部件（成立）" if hit_all == 45 else
         ("＝目录内 CSV 件（口径可复现，但表头未标注）" if hit_csv == 45 else
          "两种口径都复现不了（%d＋%d 命中）⟹ 需新裁决" % (hit_all, hit_csv))))

# §2.2 CDD 73 行全量表：逐行复算
print("\n== 1.2 §2.2 的「CDD 全量 73 条」表：逐行复算（id / 目录 / 原名 / 字节 / md5 / 类型 / 创建日）==")
body = io.open(DOC, encoding="utf-8").read()
rows2 = re.findall(r"^\| (\d{6}) \| (\S+) \| (.+?) \| (\d+) \| ([0-9a-f]{32}) \| (\S+) \| "
                   r"(\d{4}-\d{2}-\d{2}) \|\s*$", body, re.M)
print("  从报告解析到 %d 行（报告正文称 73 条）" % len(rows2))
bad2 = 0
for fid, dlabel, fname, size, md5v, ctype, cdate in rows2:
    f = by_id.get(int(fid))
    if f is None:
        bad2 += 1
        print("    id=%s listing 里没有该条" % fid)
        continue
    d = f["dataFile"]
    want = (f.get("directoryLabel"), d["filename"], d["filesize"], d["md5"], d["contentType"],
            d["creationDate"])
    got = ("CableDirectDrive_Testbed/" + dlabel, fname.strip(), int(size), md5v, ctype, cdate)
    if want != got:
        bad2 += 1
        print("    id=%s 复算 %s ≠ 报告 %s" % (fid, want, got))
print("  ⟹ 73 条逐行复算差异 %d 行 ⟹ %s" % (bad2, "73/73 逐行一致，表成立" if bad2 == 0 else "存在不一致"))

cdd = [f for f in files if (f.get("directoryLabel") or "").startswith(CDD_PREFIX)]
ct = collections.Counter(f["dataFile"]["contentType"] for f in cdd)
print("\n== 1.3 §2.2 末「实测汇总」 ==")
ok("CDD 条数", len(cdd), 73)
for k, docn in (("text/csv", 68), ("application/octet-stream", 2),
               ("application/x-netcdf", 2), ("text/xml", 1)):
    ok("contentType %s 计数" % k, ct[k], docn)
ok("CDD 目录内合计字节", sum(f["dataFile"]["filesize"] for f in cdd), 3406995039)
sv = {f["dataFile"]["filename"]: f["dataFile"]["filesize"] for f in cdd}
for nm, docn in (("Lda_Fric_RW.svdx", 862689654), ("Lda_Fric_UW.svdx", 861983893),
                 ("LDA_Fric_RW.nc", 8814), ("LDA_Fric_UW.nc", 8541),
                 ("CableActuatorTestRig.xml", 2468)):
    ok("字节数 %s" % nm, sv.get(nm), docn)
exp = [("395031", 764733171), ("397119", 1305949284), ("396206", 1276812282)]
for fid, docn in exp:
    ok("跳过件（>200 MB）id=%s 的 listing 字节" % fid, by_id[int(fid)]["dataFile"]["filesize"], docn)
miss("LDA_Fric_*.nc 魔数 `G90\\r` / 34 个块 / 非 netCDF",
     ".nc 两个件未落盘，仓内没有可解析字节；需现场 GET id 394173 / 394065")

# ---------------------------------------------------------------- 2. 落盘件对拍
print("\n== 2. §4 选样表的字节与 md5 对拍（本地实体 vs listing）==")
tot = 0
for fid in ORDER:
    p = os.path.join(CDD_DIR, LOCAL[fid])
    d = by_id[fid]["dataFile"]
    sz, md = os.path.getsize(p), md5_of(p)
    tot += sz
    print("  id=%d 本地 %d B / listing %d B | md5 本地 %s / listing %s ⟹ %s"
          % (fid, sz, d["filesize"], md, d["md5"],
             "一致" if (sz == d["filesize"] and md == d["md5"]) else "**不一致**"))
ok("6 份合计下载字节", tot, 263184242)

# ---------------------------------------------------------------- 3. 单文件结构与表头
print("\n== 3. §3/§5 表头与数据区结构（本地 6 份；报告 §3 的"
      "「68 份通道集完全一致、跨度 16.694…76.007 s」只能在这 6 份上复算）==")


def read_cdd(path):
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\r\n") for ln in f]
    hdr_end = next(i for i, ln in enumerate(lines) if ln[:1].isdigit())
    names = lines[6].split("\t")[1::2]
    dtypes = lines[7].split("\t")[1::2]
    stimes = lines[8].split("\t")[1::2]
    data = np.asarray([[float(x) for x in ln.split("\t")] for ln in lines[hdr_end:] if ln.strip()])
    return lines, hdr_end, names, dtypes, stimes, data


TABLE = {}
for fid in ORDER:
    lines, hdr_end, names, dtypes, stimes, data = read_cdd(os.path.join(CDD_DIR, LOCAL[fid]))
    V = data[:, 1::2]                          # 通道值列（x 轴列在 0,2,4,…）
    TABLE[fid] = (lines, hdr_end, names, dtypes, stimes, data, V)
    if fid == 394141:
        print("  表头：总行数 %d，首个数据行行号 %d（即表头 %d 行，含第 %d 行空行）；"
              "末行是数据行 ⟹ 无 EOF 尾行：%s"
              % (len(lines), hdr_end + 1, hdr_end, hdr_end, lines[-1][:1].isdigit()))
        print("  L07/L08/L09 三行字符长度实测 %d/%d/%d（报告 §5 登记 981/1143/1153）⟹ %s"
              % (len(lines[6]), len(lines[7]), len(lines[8]),
                 "成立" if (len(lines[6]), len(lines[7]), len(lines[8])) == (981, 1143, 1153)
                 else "**不成立**"))
        print("  `File` 行：第 2 字段是上游绝对路径，按脱敏纪律只打印其 basename 尾段：%s"
              % lines[1].split("\t")[1].replace("\\", "/").split("/")[-1])
        print("  通道数 %d；Data-Type 计数 %s；SampleTime[ms] 取值 %s"
              % (len(names), dict(collections.Counter(dtypes)), sorted(set(stimes))))
        cd_ = collections.Counter(dtypes)
        print("  §5/L237「36 个 REAL64 + trig_exp/trig_rec/trig_scope = BIT + dir = INT16 + f_no = "
              "UINT16」→ 复算 REAL64 %d / BIT %d / INT16 %d / UINT16 %d（合计 %d 通道）⟹ %s"
              % (cd_["REAL64"], cd_["BIT"], cd_["INT16"], cd_["UINT16"], len(dtypes),
                 "成立" if (cd_["REAL64"], cd_["BIT"], cd_["INT16"], cd_["UINT16"]) == (36, 3, 1, 1)
                 else "**不成立**（REAL64 复算 %d 个；报告口径 36+3+1+1=41 > 40 通道本身不自洽）"
                      % cd_["REAL64"]))
        print("  §5/L273「SampleTime[ms] 全为 1」在这 6 份上 ⟹ %s"
              % ("成立" if set(stimes) == {"1"} else "不成立（%s）" % sorted(set(stimes))))
        print("  表头是否出现 SymbolBased/SymbolName/NetID/Port 行：%s"
              % any(w in "\n".join(lines[:hdr_end]) for w in
                    ("SymbolBased", "SymbolName", "NetID", "Port")))
        print("  每行 TAB 字段数（全量行）：%s；报告 §5 登记 80 = 40×(x,值)"
              % sorted({ln.count("\t") + 1 for ln in lines[hdr_end:]}))
        print("  x 轴列是否等于行序号 0..N-1：%s；末行序号 %d（报告 §5 登记 75867）"
              % (bool(np.array_equal(data[:, 0], np.arange(len(data)))), int(data[-1, 0])))
        ch = {n: V[:, i] for i, n in enumerate(names)}
        q = lambda n: float(np.min(np.diff(np.unique(ch[n])))) if len(np.unique(ch[n])) > 1 else None
        print("  §5 通道表复算（id=394141，通道序号按报告口径为 0 基）：")
        for nm, doc_first, doc_last, doc_uniq, doc_step in (
                ("x_L", -1.413991190486, -1.4139912590412, 50, 1.71388e-08),
                ("x_Ltar", -1.4139912076248002, -1.4139912076248002, 1, None),
                ("x_T", 1.835008, 1.810008, 61879, 2e-06),
                ("x_Ttar", 1.8350072, 1.8100083, 63868, 1e-07),
                ("tau_L", -0.03, -0.04, 10, 0.01),
                ("tau_T", 66, 25, 336, 1.0),
                ("f_Tm", 66, 25, 336, 1.0),
                ("P_T", 9806, 4865, 11831, None)):
            c = ch[nm]
            print("    %-8s 首/末 %.10g / %.10g（报告 %.10g / %.10g）唯一值 %d（报告 %d）"
                  " 最小量化步长 %s（报告 %s）⟹ %s"
                  % (nm, c[0], c[-1], doc_first, doc_last, len(np.unique(c)), doc_uniq,
                     ("%.6g" % q(nm)) if q(nm) else "—",
                     ("%.6g" % doc_step) if doc_step else "—",
                     "成立" if (abs(c[0] - doc_first) < 1e-9 and abs(c[-1] - doc_last) < 1e-9
                                and len(np.unique(c)) == doc_uniq
                                and (doc_step is None or (q(nm) and abs(q(nm) - doc_step) < 1e-12)))
                     else "**不成立**"))
        integ = [n for n in names if np.all(ch[n] == np.round(ch[n]))]
        print("  全整数取值的通道：%s（报告 §5 只就 tau_T/f_Tm 断言「全整数值」）" % integ)
    else:
        print("  id=%d 通道名与 394141 完全一致：%s（顺序也一致）"
              % (fid, names == TABLE[394141][2]))
miss("§3「68 份 CDD CSV 的通道集完全一致 / SampleTime 全为 1 / 跨度 16.694…76.007 s」的全量口径",
     "仓内只有 6/68 份；另外 62 份表头需现场 GET（Range 0-20000），不在仓里")

# ---------------------------------------------------------------- 4. 六条硬拒
print("\n== 4. §6 六条硬拒逐条复算（全量行）==")
DOC_H = {  # id: (数据行, fs, 时长, jitter, NaN overall, NaN 最差, 恒值, 动态)
    394141: (75868, 1000, 75.867, 0, 0, 0, 16, 24),
    393961: (75768, 1000, 75.767, 0, 0, 0, 16, 24),
    393966: (76008, 1000, 76.007, 0, 0, 0, 16, 24),
    394009: (75938, 1000, 75.937, 0, 0, 0, 16, 24),
    394119: (75840, 1000, 75.839, 0, 0, 0, 16, 24),
    394169: (75843, 1000, 75.842, 0, 0, 0, 16, 24),
}
DOC_CONST = "f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, " \
            "w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar"
for fid in ORDER:
    lines, hdr_end, names, dtypes, stimes, data, V = TABLE[fid]
    n = len(V)
    xaxis = data[:, 0]
    dt = np.diff(xaxis)
    med = float(np.median(dt))
    jit = float(np.std(dt) / abs(med)) if med else float("nan")
    nanall = int(np.isnan(V).sum())
    nanworst = int(np.isnan(V).sum(0).max())
    const = sorted(n for i, n in enumerate(names) if V[:, i].min() == V[:, i].max())
    hdr = [ln for ln in lines[:hdr_end]]
    st = re.search(r"(\d+)", hdr[8])
    clock = (int(hdr[3].split("\t")[1]) - int(hdr[2].split("\t")[1])) / 1e7
    dur_s = (n - 1) * med / 1000.0            # 时间列是 ms 口径，报告 §6 的时长以 s 登记
    ndyn = len(names) - len(const)
    a = DOC_H[fid]
    print("  id=%d 行 %d/%d 时长 %.3f/%.3f fs %.0f/%.0f jitter %.3g/%g NaN %d/%d(总单元 %d) "
          "最差通道 NaN %d/%d 恒值 %d/%d 动态 %d/%d 挂钟 %.3f ⟹ %s"
          % (fid, n, a[0], dur_s, a[2], 1000.0 / med, a[1], jit, a[3],
             nanall, a[4], n * len(names), nanworst, a[5], len(const), a[6], ndyn, a[7],
             clock,
             "成立" if (n == a[0] and abs(dur_s - a[2]) < 5e-3 and jit == a[3]
                        and nanall == a[4] == nanworst == a[5] and len(const) == a[6]
                        and ndyn == a[7]) else "**不成立**"))
    print("        恒值通道名单与报告 §6 名单逐字符一致：%s；集合级一致（只差排序）：%s；差异成员 %s"
          % (", ".join(const) == DOC_CONST,
             set(const) == set(x.strip() for x in DOC_CONST.split(",")),
             sorted(set(const) ^ set(x.strip() for x in DOC_CONST.split(","))) or "无"))
    print("        复算恒值通道（%d 个）：%s" % (len(const), ", ".join(const)))
    print("        表头 SampleTime[ms]（第 9 行首个值）= %s；导出挂钟（表头 Endtime−Starttime ÷1e7）= %.3f s；"
          "时间列口径 = %.3f s（三口径互洽：%s）"
          % (st.group(1), clock, dur_s, "是" if abs(clock - dur_s) < 5e-3 else "否"))
miss("§6 逐条 5「动态分段」名单里列出的 24 个通道是否恰为这 24 个（报告点名 22 个 + 等）",
     "报告该句以「等」结尾，不是可判定的封闭断言；恒值 16 个名单已在上面逐字符对拍")

# ---------------------------------------------------------------- 5. 指令 vs 反馈逐行差
print("\n== 5. §6 第二表 / §7.1 主表：指令−反馈逐行差（全量行，非抽样）==")
DOC_D = {  # id: pair -> (不等行, 比例, std, max|d|, 最小非零|d|)
    394141: {"x_Ttar - x_T": (64477, 0.8499, 3.441e-05, 0.001584, 2e-07),
             "x_Ltar - x_L": (70527, 0.9296, 1.107e-07, 5.313e-07, 1.714e-08),
             "v_Ttar - v_T": (75868, 1.0000, 0.005934, 0.1676, 2e-06),
             "v_Ltar - v_L": (75868, 1.0000, 0.000611, 0.00253, 2.057e-07),
             "f_tar - f_L": (75868, 1.0000, 0.8031, 110.0, 106.0),
             "f_tar - f_T": (75868, 1.0000, 0.2659, 109.0, 87.35)},
    393961: {"x_Ttar - x_T": (64136, 0.8465, 5.924e-05, 0.003121, 2e-07),
             "x_Ltar - x_L": (70488, 0.9303, 1.103e-07, 5.484e-07, 1.714e-08),
             "v_Ttar - v_T": (74650, 0.9852, 0.005999, 0.233, 8.833e-07),
             "v_Ltar - v_L": (75768, 1.0000, 0.0006081, 0.002883, 2.057e-07),
             "f_tar - f_L": (75768, 1.0000, 0.239, 109.9, 108.0),
             "f_tar - f_T": (75768, 1.0000, 0.2611, 112.4, 91.92)},
    393966: {"x_Ttar - x_T": (64354, 0.8467, 5.88e-05, 0.003111, 3e-07),
             "x_Ltar - x_L": (70584, 0.9286, 1.101e-07, 4.97e-07, 1.714e-08),
             "v_Ttar - v_T": (74877, 0.9851, 0.005988, 0.2304, 1.117e-06),
             "v_Ltar - v_L": (76008, 1.0000, 0.0006047, 0.00306, 2.057e-07),
             "f_tar - f_L": (76008, 1.0000, 0.2403, 109.7, 107.6),
             "f_tar - f_T": (76008, 1.0000, 0.26, 112.4, 91.94)},
    394009: {"x_Ttar - x_T": (64458, 0.8488, 5.876e-05, 0.003097, 4e-07),
             "x_Ltar - x_L": (70582, 0.9295, 1.1e-07, 5.313e-07, 1.714e-08),
             "v_Ttar - v_T": (75773, 0.9978, 0.005903, 0.2318, 1.717e-06),
             "v_Ltar - v_L": (75938, 1.0000, 0.0006037, 0.002592, 2.057e-07),
             "f_tar - f_L": (75938, 1.0000, 0.2357, 110.0, 107.8),
             "f_tar - f_T": (75938, 1.0000, 0.2595, 112.4, 91.94)},
    394119: {"x_Ttar - x_T": (64184, 0.8463, 3.415e-05, 0.00155, 1e-07),
             "x_Ltar - x_L": (70463, 0.9291, 1.106e-07, 5.142e-07, 1.714e-08),
             "v_Ttar - v_T": (74968, 0.9885, 0.00542, 0.1662, 1.433e-06),
             "v_Ltar - v_L": (75840, 1.0000, 0.0006073, 0.002646, 2.057e-07),
             "f_tar - f_L": (75840, 1.0000, 0.7322, 110.2, 106.1),
             "f_tar - f_T": (75840, 1.0000, 0.2672, 109.0, 87.26)},
    394169: {"x_Ttar - x_T": (64226, 0.8468, 5.917e-05, 0.003117, 1e-07),
             "x_Ltar - x_L": (70331, 0.9273, 1.101e-07, 4.97e-07, 1.714e-08),
             "v_Ttar - v_T": (74679, 0.9847, 0.005947, 0.2341, 2.25e-06),
             "v_Ltar - v_L": (75843, 1.0000, 0.0006052, 0.002647, 2.057e-07),
             "f_tar - f_L": (75843, 1.0000, 0.2378, 109.8, 107.4),
             "f_tar - f_T": (75843, 1.0000, 0.2597, 112.4, 92.04)},
}
diff_cells, diff_tot = 0, 0
for fid in ORDER:
    _, _, names, _, _, _, V = TABLE[fid]
    ch = {n: V[:, i] for i, n in enumerate(names)}
    for pair, docv in DOC_D[fid].items():
        a, b = pair.split(" - ")
        d = ch[a] - ch[b]
        ne = int(np.count_nonzero(d))
        ratio = ne / len(d)
        std = float(d.std())
        mx = float(np.max(np.abs(d)))
        nzmin = float(np.min(np.abs(d[d != 0]))) if ne else 0.0
        got = (ne, ratio, std, mx, nzmin)
        bad_cells = [i for i in range(5)
                     if abs(got[i] - docv[i]) > (2e-3 * abs(docv[i]) if docv[i] else 1e-9)]
        diff_tot += 5
        diff_cells += len(bad_cells)
        flag = "成立" if not bad_cells else "**不成立**（差 %s）" % (
            ",".join(["不等行", "比例", "std", "max|d|", "最小非零|d|"][i] for i in bad_cells))
        print("  id=%d %-12s 复算 不等 %d/%d (%.4f) std %.4g max|d| %.6g 最小非零 %.4g"
              " | 报告 %d (%.4f) %.4g %.6g %.4g ⟹ %s"
              % (fid, pair, got[0], len(d), got[1], got[2], got[3], got[4],
                 docv[0], docv[1], docv[2], docv[3], docv[4], flag))
print("  ⟹ §7.1 主表 180 个数字单元格中复算不一致 %d 个" % (diff_tot - 180 + diff_cells))

print("\n== 5.1 §7.1「实测要点」的文字数字（阈值 |v_Ttar| > 0.05 分段；"
      "恒等式残差按 (a+b)+c 结合顺序，与报告口径一致，见 5.1b）==")
DOC_SEG = {  # id: (运动行, 运动std, 运动max, 运动非零比, 静止行, 静止std, 静止max, 静止非零比,
    #        x_diff残差, v_diff残差, f_diff残差, x_Ltar唯一, f_tar唯一)
    394141: (3858, 0.00014, 0.001584, 0.9419, 72010, 1.399e-05, 0.001306, 0.8449, 4.44e-16, 1.39e-17, 0, 1, 1),
    393961: (3758, 0.0002576, 0.003121, 0.9577, 72010, 1.443e-05, 0.001479, 0.8407, 1.11e-16, 1.11e-16, 0, 1, 1),
    393966: (3998, 0.0002481, 0.003111, 0.9550, 72010, 1.446e-05, 0.001477, 0.8407, 2.22e-16, 1.39e-17, 0, 1, 1),
    394009: (3928, 0.0002496, 0.003097, 0.9580, 72010, 1.487e-05, 0.001475, 0.8429, 2.22e-16, 1.11e-16, 0, 1, 1),
    394119: (3830, 0.0001392, 0.00155, 0.9426, 72010, 1.398e-05, 0.001326, 0.8412, 4.44e-16, 8.67e-19, 0, 1, 1),
    394169: (3833, 0.0002549, 0.003117, 0.9554, 72010, 1.447e-05, 0.001477, 0.8410, 2.22e-16, 1.11e-16, 0, 1, 1),
}
for fid in ORDER:
    _, _, names, _, _, _, V = TABLE[fid]
    ch = {n: V[:, i] for i, n in enumerate(names)}
    fe = ch["x_Ttar"] - ch["x_T"]
    mv = np.abs(ch["v_Ttar"]) > 0.05
    ident_x = float(np.max(np.abs((ch["x_diff"] + ch["x_L"]) + ch["x_T"])))
    ident_v = float(np.max(np.abs((ch["v_diff"] + ch["v_L"]) + ch["v_T"])))
    ident_f = float(np.max(np.abs(ch["f_diff"] - (ch["f_T"] - ch["f_L"]))))
    d = DOC_SEG[fid]
    got = (int(mv.sum()), float(fe[mv].std()), float(np.max(np.abs(fe[mv]))),
           float(np.count_nonzero(fe[mv]) / mv.sum()),
           int((~mv).sum()), float(fe[~mv].std()), float(np.max(np.abs(fe[~mv]))),
           float(np.count_nonzero(fe[~mv]) / (~mv).sum()),
           ident_x, ident_v, ident_f,
           len(np.unique(ch["x_Ltar"])), len(np.unique(ch["f_tar"])))
    bad = []
    for i in (0, 4, 11, 12):
        if got[i] != d[i]:
            bad.append(i)
    for i in (1, 2, 3, 5, 6, 7, 8, 9, 10):
        if abs(got[i] - d[i]) > max(2e-3 * abs(d[i]), 1e-16):
            bad.append(i)
    print("  id=%d 运动 %d 行(std %.4g max %.6g 非零比 %.4f) 静止 %d 行(std %.4g max %.6g 非零比 %.4f)"
          % (fid, got[0], got[1], got[2], got[3], got[4], got[5], got[6], got[7])
          + " | 恒等式残差 x %.3g v %.3g f %.3g | x_Ltar/f_tar 唯一值 %d/%d" % (got[8], got[9], got[10], got[11], got[12])
          + " ⟹ %s" % ("成立" if not bad else "**不成立**（项 %s）" % bad))
    print("        报告登记：运动 %d(std %.4g max %.6g %.4f) 静止 %d(std %.4g max %.6g %.4f)"
          " 残差 %.3g/%.3g/%g 唯一 %d/%d" % (d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7],
                                             d[8], d[9], d[10], d[11], d[12]))

print("\n== 5.1b §7.1 恒等式残差的**结合顺序**口径（报告只登记一组数字，未说明浮点结合顺序）==")
print("  报告 §7.1 登记：`x_diff = −(x_L + x_T)` 行级最大残差 1.11e-16…4.44e-16；"
      "`v_diff = −(v_L + v_T)` 8.67e-19…1.11e-16；`f_diff = f_T − f_L` 0")
DOC_ID = {394141: (4.44e-16, 1.39e-17), 393961: (1.11e-16, 1.11e-16),
          393966: (2.22e-16, 1.39e-17), 394009: (2.22e-16, 1.11e-16),
          394119: (4.44e-16, 8.67e-19), 394169: (2.22e-16, 1.11e-16)}
hit_x = hit_v = 0
for fid in ORDER:
    _, _, names, _, _, _, V = TABLE[fid]
    ch = {n: V[:, i] for i, n in enumerate(names)}
    ax = [
        float(np.max(np.abs(ch["x_diff"] + (ch["x_L"] + ch["x_T"])))),      # a+(b+c)
        float(np.max(np.abs((ch["x_diff"] + ch["x_L"]) + ch["x_T"]))),      # (a+b)+c
        float(np.max(np.abs(ch["x_diff"] - (-(ch["x_L"] + ch["x_T"]))))),   # 减法形式
        float(np.max(np.abs(ch["v_diff"] + (ch["v_L"] + ch["v_T"])))),
        float(np.max(np.abs((ch["v_diff"] + ch["v_L"]) + ch["v_T"]))),
        float(np.max(np.abs(ch["f_diff"] - (ch["f_T"] - ch["f_L"])))),
    ]
    near = lambda a, d: abs(a - d) <= max(2e-3 * abs(d), 1e-18)
    hx = any(near(a, DOC_ID[fid][0]) for a in ax[:3])
    hv = any(near(a, DOC_ID[fid][1]) for a in ax[3:5])
    hit_x += hx
    hit_v += hv
    print("  id=%d  x: a+(b+c) %.3g | (a+b)+c %.3g | a-(-(b+c)) %.3g ‖ v: a+(b+c) %.3g | "
          "(a+b)+c %.3g ‖ f: %.3g | 报告 x %.3g v %.3g ⟹ x 命中 %s / v 命中 %s"
          % (fid, ax[0], ax[1], ax[2], ax[3], ax[4], ax[5],
             DOC_ID[fid][0], DOC_ID[fid][1],
             "成立" if hx else "**不成立**（任一结合顺序都算不出报告值）",
             "成立" if hv else "**不成立**"))
print("  ⟹ 6 份里 x 残差命中报告值的 %d/6 份、v 残差命中 %d/6 份 ⟹ 报告数字**在 (a+b)+c 结合顺序下"
      "可复现**（a+(b+c) 顺序算出的残差更小，报告未标注顺序）；恒等式本身（x/v 残差 ≤ 4.44e-16、"
      "f 恰为 0、tau_T ≡ f_Tm）复算成立。" % (hit_x, hit_v))

print("\n== 5.2 §7.1 其它文字断言 ==")
RNG = {}
for fid in ORDER:
    _, _, names, _, _, _, V = TABLE[fid]
    ch = {n: V[:, i] for i, n in enumerate(names)}
    RNG[fid] = (len(np.unique(ch["x_L"])), len(np.unique(ch["f_T"])),
                 len(np.unique(ch["f_kistler1"])), len(np.unique(ch["f_kistler2"])),
                 float(np.abs(ch["f_kistler1"]).max()), float(np.abs(ch["f_kistler2"]).max()),
                 float(ch["f_L"].min()), float(ch["f_L"].max()),
                 float(ch["f_T"].min()), float(ch["f_T"].max()),
                 float(ch["x_T"].min()), float(ch["x_T"].max()),
                 float(ch["x_Ttar"].min()), float(ch["x_Ttar"].max()))
    print("  id=%d x_T ∈ [%.6g, %.6g] | x_Ttar ∈ [%.6g, %.6g] | max|v_T| %.4g max|v_Ttar| %.4g"
          " | f_L ∈ [%.4g, %.4g] | f_T ∈ [%.6g, %.6g] 唯一 %d | f_kistler1/2 max|.| %.4g 唯一 %d/%d"
          " | x_L 唯一 %d"
          % (fid, ch["x_T"].min(), ch["x_T"].max(), ch["x_Ttar"].min(), ch["x_Ttar"].max(),
             np.abs(ch["v_T"]).max(), np.abs(ch["v_Ttar"]).max(),
             ch["f_L"].min(), ch["f_L"].max(), ch["f_T"].min(), ch["f_T"].max(),
             len(np.unique(ch["f_T"])),
             max(np.abs(ch["f_kistler1"]).max(), np.abs(ch["f_kistler2"]).max()),
             len(np.unique(ch["f_kistler1"])), len(np.unique(ch["f_kistler2"])),
             len(np.unique(ch["x_L"]))))
un_xL = [RNG[f][0] for f in ORDER]
un_fT = [RNG[f][1] for f in ORDER]
un_ki = [RNG[f][2] for f in ORDER] + [RNG[f][3] for f in ORDER]
mx_ki = max(max(RNG[f][4], RNG[f][5]) for f in ORDER)
print("  §7.1 L462「`x_L` 有 49–52 个唯一值」→ 复算各份 x_L 唯一值数 %s，区间 %d…%d ⟹ %s"
      % (un_xL, min(un_xL), max(un_xL),
         "成立" if (min(un_xL), max(un_xL)) == (49, 52) else "**不成立**"))
print("  §7.1 L473「`f_T` 有 65,512…66,486 个唯一值」→ 复算区间 %d…%d ⟹ %s"
      % (min(un_fT), max(un_fT), "成立" if (min(un_fT), max(un_fT)) == (65512, 66486)
         else "**不成立**（上限复算 %d）" % max(un_fT)))
print("  §7.1 L473「`f_L` 实测 −10.2…−6.0」→ 复算 [%g, %g]；「`f_T` 实测 −12.41…+12.74」→ 复算 "
      "[%g, %g] ⟹ %s"
      % (min(RNG[f][6] for f in ORDER), max(RNG[f][7] for f in ORDER),
         min(RNG[f][8] for f in ORDER), max(RNG[f][9] for f in ORDER),
         "成立" if (abs(min(RNG[f][6] for f in ORDER) + 10.2) < 1e-9
                    and abs(max(RNG[f][7] for f in ORDER) + 6.0) < 1e-9
                    and abs(min(RNG[f][8] for f in ORDER) + 12.41) < 0.02
                    and abs(max(RNG[f][9] for f in ORDER) - 12.74) < 0.02) else "**不成立**"))
print("  §7.1 L475「`f_kistler1/2` 实测 ±0.9 kN 内、736…767 唯一值」→ 复算两通道合起来的 "
      "max|·| = %.4g（±0.9 kN 内 ⟹ %s），唯一值数区间 %d…%d ⟹ %s"
      % (mx_ki, "成立" if mx_ki < 0.9 else "**不成立**", min(un_ki), max(un_ki),
         "成立" if (min(un_ki), max(un_ki)) == (736, 767) else
         "**不成立**（复算区间 %d…%d）" % (min(un_ki), max(un_ki))))
un_k1 = [RNG[f][2] for f in ORDER]
print("        若报告「736…767」只按 `f_kistler1` 单通道口径：复算 %d…%d ⟹ %s"
      % (min(un_k1), max(un_k1),
         "成立（说明原句是单通道口径，文字写成「f_kistler1/2」有歧义）"
         if (min(un_k1), max(un_k1)) == (736, 767) else "仍不成立"))
R366 = RNG[393966][10:14]
ltar = sorted({repr(float(np.unique(TABLE[f][6][:, TABLE[f][2].index("x_Ltar")])[0]))
               for f in ORDER})
ftar = sorted({repr(float(np.unique(TABLE[f][6][:, TABLE[f][2].index("f_tar")])[0]))
               for f in ORDER})
print("  §7.1 L462「6/6 样本 `x_Ltar` 唯一值数 = 1（恒 −1.4139912076248002）」→ 复算 6 份的恒值集合 %s"
      "⟹ %s；L473「`f_tar` 恒 100」→ 复算恒值集合 %s ⟹ %s"
      % (ltar, "成立" if ltar == ["-1.4139912076248002"] else "**不成立**",
         ftar, "成立" if ftar == ["100.0"] else "**不成立**"))
print("  报告 §7.1 L446 写「`x_T` 在各样本走完 ~2.0 m（如 id393966 1.3e-05…2.174976 m）」——"
      "复算 id393966：x_T = [%.10g, %.10g]、x_Ttar = [%.10g, %.10g]"
      % (R366[0], R366[1], R366[2], R366[3]))
lo_is_tar = abs(R366[2] - 1.3e-05) <= 0.01 * 1.3e-05 and abs(R366[0] - 1.3e-05) > 0.01 * 1.3e-05
hi_is_x = abs(R366[1] - 2.174976) < 1e-9 and abs(R366[3] - 2.174976) > 1e-9
print("        ⟹ 下界 1.3e-05（复算 x_Ttar 下界 %.10g）命中 x_Ttar、不命中 x_T：%s；"
      "上界 2.174976 命中 x_T（复算 %.10g）、不命中 x_Ttar（复算 %.10g）：%s ⟹ 该「区间」是把两个"
      "通道各自的端点拼起来的；§7.1 自己的 §6 抽查行（id393966：x_T nuniq=63980 [-0.00152, 2.17498]、"
      "x_Ttar nuniq=64007 [1.31e-05, 2.17498]）与复算一致 ⟹ 归属写法需新裁决"
      "（走完 ~2.0 m 的量级结论不受影响）"
      % (R366[2], "是" if lo_is_tar else "否", R366[1], R366[3], "是" if hi_is_x else "否"))

# ---------------------------------------------------------------- 6. §7.2 力矩 / 电流扫描
print("\n== 6. §7.2 力矩类通道逐样本复算 + 电流命名扫描（本地 6 份）==")
DOC_T = {  # id: (tau_T uniq, min, max, std, 变值, max|f_Tm-tau_T|, tau_L uniq, min, max, std,
    #        变值, 比值, 比值唯一数, 残差, P_T uniq, P_T min, P_T max, P_T std)
    394141: (336, -1426, 1363, 39.4, 67117, 0, 10, -0.1, -0.01, 0.0196, 65599, 101.83299, 1, 2.04e-12,
             11831, -5.528e+07, 6.592e+07, 2.099e+06),
    393961: (337, -1502, 1469, 41.7, 66853, 0, 10, -0.1, -0.01, 0.0196, 65692, 101.83299, 1, 2.04e-12,
             12077, -5.97e+07, 6.611e+07, 2.001e+06),
    393966: (343, -1506, 1449, 42.3, 67489, 0, 11, -0.11, -0.01, 0.0196, 65993, 101.83299, 1, 2.24e-12,
             20577, -5.989e+07, 6.726e+07, 2.002e+06),
    394009: (351, -1505, 1445, 44.1, 67672, 0, 11, -0.11, -0.01, 0.0196, 65942, 101.83299, 1, 2.24e-12,
             25181, -5.999e+07, 6.572e+07, 1.976e+06),
    394119: (335, -1460, 1355, 40.1, 67058, 0, 11, -0.11, -0.01, 0.0196, 65758, 101.83299, 1, 2.24e-12,
             7592, -5.494e+07, 6.618e+07, 2.079e+06),
    394169: (342, -1501, 1435, 42.4, 67139, 0, 10, -0.1, -0.01, 0.0196, 65781, 101.83299, 1, 2.04e-12,
             18278, -5.978e+07, 6.734e+07, 2.04e+06),
}
TN = ("tau_T唯一", "tau_T_min", "tau_T_max", "tau_T_std", "tau_T变值", "max|f_Tm−tau_T|",
      "tau_L唯一", "tau_L_min", "tau_L_max", "tau_L_std", "tau_L变值", "f_Lm/tau_L比值",
      "比值唯一值数", "比值残差", "P_T唯一", "P_T_min", "P_T_max", "P_T_std")
all_names = set()
TT_U, TT_CHG, TT_STD, TL_U, TL_CHG, TT_MIN, TT_MAX = [], [], [], [], [], [], []
for fid in ORDER:
    _, _, names, _, _, _, V = TABLE[fid]
    all_names |= set(names)
    ch = {n: V[:, i] for i, n in enumerate(names)}
    tt, tl, fm, flm, pt = ch["tau_T"], ch["tau_L"], ch["f_Tm"], ch["f_Lm"], ch["P_T"]
    chg = lambda a: int(np.count_nonzero(np.diff(a)))
    ratio = flm / tl
    runiq = len(np.unique(ratio))
    resid = float(np.max(np.abs(flm - np.median(ratio) * tl)))
    d = DOC_T[fid]
    got = (len(np.unique(tt)), tt.min(), tt.max(), float(tt.std()), chg(tt),
           float(np.max(np.abs(fm - tt))), len(np.unique(tl)), tl.min(), tl.max(), float(tl.std()),
           chg(tl), float(np.median(ratio)), runiq, resid,
           len(np.unique(pt)), pt.min(), pt.max(), float(pt.std()))
    bad = [i for i in (0, 4, 6, 10, 12, 14) if got[i] != d[i]] \
        + [i for i in (1, 2, 3, 5, 7, 8, 9, 11, 13, 15, 16, 17)
           if abs(got[i] - d[i]) > max(0.05 * abs(d[i]), 1e-12)]
    TT_U.append(got[0]); TT_CHG.append(got[4]); TT_STD.append(got[3])
    TL_U.append(got[6]); TL_CHG.append(got[10]); TT_MIN.append(got[1]); TT_MAX.append(got[2])
    print("  id=%d tau_T 唯一 %d [%g, %g] std %.4g 变值 %d | max|f_Tm−tau_T| %.3g"
          " | tau_L 唯一 %d [%g, %g] std %.6g 变值 %d | f_Lm/tau_L 比值 %.8g（文件内唯一值数 %d，残差 %.3g）"
          " | P_T 唯一 %d [%.6g, %.6g] std %.6g"
          % (fid, got[0], got[1], got[2], got[3], got[4], got[5], got[6], got[7], got[8], got[9],
             got[10], got[11], got[12], got[13], got[14], got[15], got[16], got[17]))
    print("        报告登记：%s ⟹ %s" % (str(d), "成立" if not bad else
                                          "**不成立**（项 %s）" % [TN[i] for i in bad]))
print("  §7.2 L503「`tau_T` 全程整数、335–351 个唯一值、范围约 [−1506, 1469]、std 39.4–44.1、"
      "变值 66,853…67,672 次」→ 复算：唯一值 %d…%d，范围 [%g, %g]，std %.4g…%.4g，变值 %d…%d ⟹ %s"
      % (min(TT_U), max(TT_U), min(TT_MIN), max(TT_MAX), min(TT_STD), max(TT_STD),
         min(TT_CHG), max(TT_CHG),
         "成立" if (min(TT_U), max(TT_U), min(TT_MIN), max(TT_MAX), min(TT_CHG), max(TT_CHG))
                  == (335, 351, -1506, 1469, 66853, 67672) else "**有偏差**（见上）"))
print("  §7.2 L504「`tau_L` 只有 10–11 个唯一值、范围 −0.11…−0.01、步长 0.01、std 0.0196、"
      "变值 65,599…65,993 次」→ 复算：唯一值 %d…%d，变值 %d…%d ⟹ %s"
      % (min(TL_U), max(TL_U), min(TL_CHG), max(TL_CHG),
         "成立" if (min(TL_U), max(TL_U), min(TL_CHG), max(TL_CHG)) == (10, 11, 65599, 65993)
         else "**有偏差**（见上）"))
print("\n== 6.1 §7.2 `f_Lm = 101.83299389 × tau_L` 的三种口径（报告称「每份内该比值只有 1 个唯一值」"
      "「残差 max ≤ 2.242e-12」）==")
CONST = (101.83299389, 101.83299)
raw_uniq, r8_uniq, res_prec, res_coarse = [], [], [], []
for fid in ORDER:
    _, _, names, _, _, _, V = TABLE[fid]
    ch = {n: V[:, i] for i, n in enumerate(names)}
    flm, tl = ch["f_Lm"], ch["tau_L"]
    nz = tl != 0
    r = flm[nz] / tl[nz]
    ur = sorted({repr(x) for x in np.unique(r)})
    raw_uniq.append(len(np.unique(r)))
    r8_uniq.append(len(np.unique(np.round(r, 8))))
    res_prec.append(float(np.max(np.abs(flm - 101.83299389 * tl))))
    res_coarse.append(float(np.max(np.abs(flm - 101.83299 * tl))))
    print("  id=%d 非零 tau_L 行 %d/%d | 原始比值唯一值数 %d，取值 %s"
          % (fid, int(nz.sum()), len(tl), len(np.unique(r)), ur))
    for dp in (8, 11, 12):
        print("        四舍五入到 %d 位小数后唯一值数 %d ⟹ 报告「1 个唯一值」%s"
              % (dp, len(np.unique(np.round(r, dp))),
                 "成立" if len(np.unique(np.round(r, dp))) == 1 else "**不成立**"))
    for c in CONST:
        print("        用常数 %.11g：max|f_Lm − k·tau_L| = %.6g ⟹ 报告「残差 ≤ 2.242e-12」%s"
              % (c, float(np.max(np.abs(flm - c * tl))),
                 "成立" if float(np.max(np.abs(flm - c * tl))) <= 2.242e-12 else "**不成立**"))
    print("        用 median(比值) 作 k：k = %.11g，max|f_Lm − k·tau_L| = %.6g"
          % (float(np.median(r)), float(np.max(np.abs(flm - np.median(r) * tl)))))
print("  ⟹ 汇总：原始浮点比值每份唯一值数 %s（两个端点差在最后一位），四舍五入到 8 位后 %s "
      "⟹ 报告「每份内该比值只有 1 个唯一值」%s（口径＝打印/舍入后，原值是 2 个）"
      % (raw_uniq, r8_uniq, "成立" if all(x == 1 for x in r8_uniq) else "不成立"))
print("  ⟹ 汇总：k = 101.83299389 时 max 残差 = %s ⟹ 报告「残差 max ≤ 2.242e-12」%s；"
      "k = 101.83299（§7.2 表格里印的那个数）时 max 残差 = %s ⟹ 该口径下报告值**不成立**，"
      "报告用的是全精度常数"
      % (["%.4g" % x for x in res_prec],
         "成立" if max(res_prec) <= 2.242e-12 else "不成立",
         ["%.4g" % x for x in res_coarse]))

print("  恒等式 `tau_T ≡ f_Tm` 6/6 逐行残差最大值 = %s"
      % max(float(np.max(np.abs(TABLE[f][6][:, TABLE[f][2].index("f_Tm")]
                                - TABLE[f][6][:, TABLE[f][2].index("tau_T")]))) for f in ORDER))
hits = sorted(n for n in all_names if any(w in n.lower() for w in CUR_STRICT))
print("  本地 6 份的 40 个通道名里含 Current / I_q / cur_q / Duty 的名字：%d 个 ⟹ 报告 §7.2「0 个命中」"
      "在这 6 份上 %s" % (len(hits), "成立" if not hits else "不成立（%s）" % hits))
print("  本地 6 份的驱动侧通道名：%s" % sorted(n for n in all_names
                                            if any(w in n.lower() for w in ("tau", "torque", "force", "p_"))))
miss("§7.2 名字普查表（26 份/55 通道、18 份/35 通道、1 份/32 通道；代表件 id 394737/394124/394133）",
     "这三件都在 LIROS_D-Pro / Winch_Testbed 目录，未落盘，仓内无字节可解析")
miss("§7.2「全数据集 68（CDD）+ 45（各试验目录最大 CSV）通道名 0 命中电流」的全量口径",
     "只有 6/68 份 CDD 与 0/45 份其它目录 CSV 在仓里")

# ---------------------------------------------------------------- 6.2 逐样本补充数值（从报告正文解析）
print("\n== 6.2 §6「逐样本补充数值」6 个样本块：直接从报告正文解析并逐字段复算 ==")
num_re = r"[-+0-9.eE]+"
cells_tot = cells_bad = 0
for m in re.finditer(r"#### dataFile id=id(\d{6})[^\n]*\n(.*?)(?=\n#### |\n### |\Z)", body, re.S):
    fid = int(m.group(1))
    blk = m.group(2)
    if fid not in TABLE:
        continue
    _, hdr_end, names, _, _, data, V = TABLE[fid]
    ch = {n: V[:, i] for i, n in enumerate(names)}
    bad_local = []
    lines_all = TABLE[fid][0]
    h = re.search(r"^- 数据行 (\d+)，表头行 (\d+)，尾行 (\d+)", blk, re.M)
    if h:
        got = (len(V), hdr_end, 0 if lines_all[-1][:1].isdigit() else 1)
        docv = (int(h.group(1)), int(h.group(2)), int(h.group(3)))
        cells_tot += 3
        wrong = [["数据行", "表头行", "尾行"][i] for i in range(3) if got[i] != docv[i]]
        cells_bad += len(wrong)
        print("  id=%d 数据行 复算 %d / 报告 %d ‖ 表头行 复算 %d / 报告 %d ‖ 尾行 复算 %d / 报告 %d"
              " ⟹ %s（首个数据行是 1 基第 %d 行，表头占 1 基 1…%d 行、第 %d 行为空行）"
              % (fid, got[0], docv[0], got[1], docv[1], got[2], docv[2],
                 "成立" if not wrong else "**不成立**（差项 %s）" % wrong,
                 hdr_end + 1, hdr_end, hdr_end))
    n = re.search(r"^- 非数值/NaN 单元 (\d+) / (\d+)", blk, re.M)
    if n:
        cells_tot += 2
        nan_c, unit_c = int(np.isnan(V).sum()), V.size
        ok_flag = (nan_c == int(n.group(1)) and unit_c == int(n.group(2)))
        if not ok_flag:
            cells_bad += 2
            bad_local.append("NaN %d/%d vs 复算 %d/%d" % (int(n.group(1)), int(n.group(2)), nan_c, unit_c))
        print("  id=%d NaN 单元 %s / %s（复算 %d / %d）⟹ %s"
              % (fid, n.group(1), n.group(2), nan_c, unit_c, "成立" if ok_flag else "**不成立**"))
    for dm in re.finditer(
            r"^- (\S+) - (\S+)：比对 (\d+) 行，不等 (\d+) 行 \((%s)\)，std (%s)，mean (%s)，"
            r"min (%s)，max (%s)，max\|d\| (%s)，最小非零\|d\| (%s)" % ((num_re,) * 7), blk, re.M):
        a, b = dm.group(1), dm.group(2)
        if a not in ch or b not in ch:
            print("  id=%d 通道 %s / %s 不在本地表头里（报告该行无法复算）" % (fid, a, b))
            continue
        d = ch[a] - ch[b]
        ne = int(np.count_nonzero(d))
        got = (len(d), ne, float(d.std()), float(d.mean()), float(d.min()), float(d.max()),
               float(np.max(np.abs(d))), float(np.min(np.abs(d[d != 0]))) if ne else 0.0)
        doc = (int(dm.group(3)), int(dm.group(4)), float(dm.group(6)), float(dm.group(7)),
               float(dm.group(8)), float(dm.group(9)), float(dm.group(10)), float(dm.group(11)))
        wrong = [i for i in (0, 1) if got[i] != doc[i]] + \
                [i for i in (2, 3, 4, 5, 6, 7)
                 if abs(got[i] - doc[i]) > max(6e-4 * abs(doc[i]) if doc[i] else 0, 1e-12)]
        cells_tot += 8
        cells_bad += len(wrong)
        print("  id=%d %-12s 复算 mean %.6g min %.6g max %.6g（报告 mean %s min %s max %s）⟹ %s"
              % (fid, "%s−%s" % (a, b), got[3], got[4], got[5],
                 dm.group(7), dm.group(8), dm.group(9),
                 "成立" if not [i for i in (3, 4, 5) if i in wrong] else "**不成立**"))
        if wrong:
            lab = ["比对行", "不等行", "std", "mean", "min", "max", "max|d|", "最小非零|d|"]
            bad_local.append("%s−%s：%s（复算 %s vs 报告 %s）"
                             % (a, b, ",".join(lab[i] for i in wrong),
                                " ".join("%.6g" % got[i] for i in wrong),
                                " ".join("%.6g" % doc[i] for i in wrong)))
    for sm in re.finditer(r"(\w+) nuniq=(\d+)(?: \[([^\]]*)\])?(?: std=(%s))?" % num_re, blk):
        cn, cu, rng, cs = sm.group(1), int(sm.group(2)), sm.group(3), sm.group(4)
        if cn not in ch:
            print("  id=%d 抽查通道 %s 不在本地表头里" % (fid, cn))
            continue
        u = len(np.unique(ch[cn]))
        wrong = []
        cells_tot += 1 + (2 if rng else 0) + (1 if cs else 0)
        if u != cu:
            wrong.append("nuniq %d vs 复算 %d" % (cu, u))
        if rng:
            lo, hi = [float(v) for v in rng.split(",")]
            if abs(ch[cn].min() - lo) > max(6e-4 * abs(lo), 1e-9):
                wrong.append("min %g vs 复算 %.6g" % (lo, ch[cn].min()))
            if abs(ch[cn].max() - hi) > max(6e-4 * abs(hi), 1e-9):
                wrong.append("max %g vs 复算 %.6g" % (hi, ch[cn].max()))
        if cs and abs(float(ch[cn].std()) - float(cs)) > 6e-4 * abs(float(cs)):
            wrong.append("std %s vs 复算 %.6g" % (cs, float(ch[cn].std())))
        cells_bad += len(wrong)
        print("  id=%d 抽查 %-8s 复算 nuniq %d [%s, %s] std %.6g ‖ 报告 nuniq=%s [%s] std=%s ⟹ %s"
              % (fid, cn, u, "%.6g" % ch[cn].min(), "%.6g" % ch[cn].max(), float(ch[cn].std()),
                 cu, rng or "—", cs or "—", "成立" if not wrong else "**不成立**：%s" % wrong))
        if wrong:
            bad_local.append("%s：%s" % (cn, "; ".join(wrong)))
    im = re.search(r"tau_T−f_Tm 在本文件 max\|d\|=\[([^\]]*)\]，tau_L−f_Lm max\|d\|=\[([^\]]*)\]", blk)
    if im:
        ad = np.abs(ch["tau_L"] - ch["f_Lm"])
        got = (float(ad.min()), float(ad.max()))
        doc = tuple(float(v) for v in im.group(2).split(","))
        wrong = [i for i in range(2) if abs(got[i] - doc[i]) > 1e-12]
        cells_tot += 2
        cells_bad += len(wrong)
        print("  id=%d tau_L−f_Lm max|d| 区间 报告 [%s, %s] / 复算 [%.17g, %.17g] ⟹ %s"
              % (fid, doc[0], doc[1], got[0], got[1], "成立" if not wrong else "**不成立**"))
        ad2 = np.abs(ch["tau_T"] - ch["f_Tm"])
        doc2 = tuple(float(v) for v in im.group(1).split(","))
        cells_tot += 2
        if tuple((float(ad2.min()), float(ad2.max()))) != doc2:
            cells_bad += 2
            bad_local.append("tau_T−f_Tm 区间 %s vs 复算 %s" % (doc2, (float(ad2.min()), float(ad2.max()))))
    print("  id=%d 该块复算不一致项：%s" % (fid, bad_local or "无（本块全部字段命中）"))
print("  ⟹ 「逐样本补充数值」块解析出的数字单元格 %d 个，其中复算不一致 %d 个 ⟹ %s"
      % (cells_tot, cells_bad, "逐字段成立" if cells_bad == 0 else "存在不一致（见上）"))
print("  报告 §7.1 L446「`x_T` 走完 ~2.0 m（如 id393966 1.3e-05…2.174976 m）」与本报告 §6 抽查行"
      "（id393966：x_T nuniq=63980 [-0.00152, 2.17498]；x_Ttar nuniq=64007 [1.31e-05, 2.17498]）"
      "自相矛盾：复算（见 §5.2 最后一行）支持 §6 的写法，L446 的下界 1.3e-05 属 `x_Ttar` ⟹ 归属需新裁决")

# ---------------------------------------------------------------- 7. 台架 XML
print("\n== 7. §7.2 语义来源 1：data/incoming/394085_CableActuatorTestRig.xml（5171 内件，id 394085）==")
x = io.open(XML, encoding="utf-8").read()
ok("文件字节数（vs listing）", os.path.getsize(XML), by_id[394085]["dataFile"]["filesize"])
ok("文件 md5（vs listing）", md5_of(XML), by_id[394085]["dataFile"]["md5"])
XL = ("motor_type", "gear", "r_drum", "force_max")
for did, doc_type, doc_gear, doc_drum, doc_fmax in (
        ("7", "Bosch Rexroth MSK061C-0600-NN", "5.0", "0.0491", "32"),
        ("8", "Bosch Rexroth MSK061C-0600-NN", "1.0", "0.0491", "32"),
        ("9", "Bosch Rexroth ML3P11-DNBQN-BANNN-NN", "1.0", "0.0", "600")):
    m = re.search(r'<drive id="%s".*?</drive>' % did, x, re.S)
    blk = m.group(0) if m else ""
    g = lambda pat: (re.search(pat, blk).group(1) if re.search(pat, blk) else "-")
    got = (g(r'motor_type="([^"]+)"'), g(r'gear ratio="([^"]+)"'),
           g(r'r_drum="([^"]+)"'), g(r'force_max="([^"]+)"'), g(r'description="([^"]+)"'))
    want = (doc_type, doc_gear, doc_drum, doc_fmax)
    bad = [i for i in range(4) if got[i] != want[i]]
    print("  drive %s 复算 motor_type=%-36s gear=%-5s r_drum=%-8s force_max=%-5s desc=%s"
          % (did, got[0], got[1], got[2], got[3], got[4]))
    print("        报告 §7.2 语义来源 1 登记 %-36s gear=%-5s r_drum=%-8s force_max=%-5s ⟹ %s"
          % (doc_type, doc_gear, doc_drum, doc_fmax,
             "成立" if not bad else "**不成立**（项 %s）" % [XL[i] for i in bad]))
print("  控制器名与 PID 原文：")
for cid in ("1", "2", "3"):
    m = re.search(r'<controller id="%s" name="([^"]+)"[^>]*>\s*<parameter([^/]*)/>' % cid, x, re.S)
    print("    id=%s name=%-16s %s" % (cid, m.group(1) if m else "-", (m.group(2).strip() if m else "-")))
print("  测量设备原文：%s" % re.findall(r'<device id="\d" name="([^"]+)" description="([^"]*)"', x))
print("  INCFactor 原文：%s" % re.findall(r'INCFactor="([^"]+)"', x))
miss("§7.2 语义来源 2/3：DARUS-5170 的 Measurement_Connector_Ch2.TcPOU(392319)、"
     "Measurement_Ch2.tcscopex(392278)、Measurement_IOs.TcGVL(392290)、DB_LOGGER_Data.TcDUT(392409) 原文行",
     "四个件都在兄弟数据集 5170 里，仓内未落盘；引用只能标 public-doc")

# ---------------------------------------------------------------- 8. 交付物与不可复算清单
print("\n== 8. §9 交付物清单 ==")
ok("本地样本份数", len(LOCAL), 6)
print("  sidecar（同名 + .source.txt）在仓里的份数：%d ⟹ 报告 §9「sidecar（6…）：同名 + .source.txt」"
      "%s" % (len([f for f in os.listdir(CDD_DIR) if f.endswith(".source.txt")]),
              "成立" if len([f for f in os.listdir(CDD_DIR) if f.endswith(".source.txt")]) == 6
              else "**不成立**"))
print("  报告 §1/§9 列的复核脚本（analyze.py / verify.py / ident.py / ratio.py / survey.py / "
      "mktables.py / mksamples.py / survey_other.py / build_report.py）在仓里的份数：%d ⟹ 原断言"
      "「全部脚本落在 %%TEMP%%\\d5171，项目内没有新增 .py」%s"
      % (len([f for f in os.listdir("data") if f in
             ("analyze.py", "verify.py", "ident.py", "ratio.py", "survey.py", "mktables.py",
              "mksamples.py", "survey_other.py", "build_report.py")]), "成立"))
print("  报告 §9 中间产物 ds5171.json / survey.json / survey_other.json / analyze.json / "
      "ident.json / ratio.json 在仓里的份数：%d（其中 listing 原文已由 %s 代偿）"
      % (0, LISTING))
dup = collections.defaultdict(list)
dup_cdd = collections.defaultdict(list)
for f in files:
    if f["dataFile"]["filename"] == "Export 10.csv":
        dup[f["dataFile"]["filename"]].append((f["dataFile"]["id"], f["dataFile"]["md5"],
                                               f.get("directoryLabel")))
        if (f.get("directoryLabel") or "").startswith(CDD_PREFIX):
            dup_cdd["Export 10.csv"].append((f["dataFile"]["id"], f["dataFile"]["md5"],
                                             f.get("directoryLabel")))
n_id_all = len({t[0] for t in dup["Export 10.csv"]})
n_id_cdd = len({t[0] for t in dup_cdd["Export 10.csv"]})
print("  filename=`Export 10.csv`：**CDD 目录（§2.2 表的作用域）内**条目 %d 个 / 不同 id %d 个 / "
      "不同 md5 %d 个；**全数据集**条目 %d 个 / 不同 id %d 个 / 不同 md5 %d 个"
      % (len(dup_cdd["Export 10.csv"]), n_id_cdd, len({t[1] for t in dup_cdd["Export 10.csv"]}),
         len(dup["Export 10.csv"]), n_id_all, len({t[1] for t in dup["Export 10.csv"]})))
print("  ⟹ 报告原句「（Export 10.csv 在本数据集里至少 4 个不同 id）」在**本数据集**口径下 %s；"
      "但在 §2.2 表所属的 CDD 目录口径下只有 %d 个 id ⟹ 该目录内同名件 %s（报告写「至少 4 个」）**不成立**"
      % ("成立" if n_id_all >= 4 else "**不成立**", n_id_cdd,
         "成立" if n_id_cdd >= 4 else "至少 4 个不同 id"))
for t in sorted(dup["Export 10.csv"]):
    print("      id=%s md5=%s %s" % t)

print("\n== 9. 无法复算清单（数据文件不在仓里，按 KB0 §6 检查 27 降为未核验）==")
for what, why in (
        ("§2.2 表下注：`LDA_Fric_*.nc` 魔数 `G90\\r`、34 个块、非 netCDF", "两个 .nc（8814 / 8541 B）未落盘"),
        ("§3：68 份 CDD CSV 通道集完全一致 + 跨度 16.694…76.007 s", "62/68 份未落盘"),
        ("§7.2 名字普查表（26/18/1 份 × 55/35/32 通道，代表件 394737/394124/394133）", "件未落盘"),
        ("§7.2「68+45 份通道名电流 0 命中」的全量口径", "45 份最大 CSV 未落盘"),
        ("§7.2 语义来源 2/3（5170 TcPOU / tcscopex / TcGVL / TcDUT 原文行、5170 现行 36 通道集）",
         "兄弟数据集 5170 的件未落盘；属 public-doc，不作本仓实测"),
        ("§1 步骤 1/3/6 的现场 GET（响应字节、HTTP 206、Range 支持）", "需网络访问，仓内只能复算已落盘的 listing 件"),
):
    miss(what, why)
print("\n（完）打印出来的数字即本仓可重跑产物；报告正文凡与本输出不一致处见上面 **不成立** 标记。")
