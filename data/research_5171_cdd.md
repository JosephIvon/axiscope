# DARUS-5171 · CableDirectDrive_Testbed 候选样本核验：跟随误差（fe）与电流/力矩类通道

- 核验日期：2026-10-20（DaRUS 现场 GET，未使用任何本地缓存 listing）
- 执行：Qoder 子智能体（本会话亲自执行 → sidecar `verified_by: self`）
- 对象：`doi:10.18419/DARUS-5171`，目录 `CableDirectDrive_Testbed/2024-07-23_LdaFricIdent`
- 一句话结论：**有**。CDD 的 68 份 TwinCAT CSV 全部是「指令 ≠ 反馈」的闭环记录（与 DARUS-3600 的 0 差异完全不同），实测 6 份六条硬拒全 PASS；驱动侧**力矩/力实际值**通道（`tau_T`、`tau_L`）真实存在且带动态，但**没有任何** Current/I_q/Duty 命名的电流通道 → 严格按 `cur_q` 口径仍是缺口。

---

## 0. 边界与口径

- 本次只写入：`data/incoming/darus5171/`（6 份 CSV + 6 份 `.source.txt`）与 `data/research_5171_cdd.md`（本文件）。
  未触碰 `data/raw/`、`data/staging/`、`data/sidecar_in/`、`data/incoming/` 既有文件、`data/validate_raw.py`、
  `data/PROVENANCE-TEMPLATE.md`、`data/VERIFICATION-2026-10-20.md`、`data/research_fe_current.md`、`data/research_current_channel.md`（只读过模板）。
- 全部脚本落在 `%LOCALAPPDATA%\Temp\d5171`（Git Bash 里即 `/tmp/d5171`），项目内没有新增 `.py`。
- 下载总量 **263,184,242 B = 263.2 MB（251.0 MiB）**，在 300 MB 预算内。
- >200 MB 的对象一律跳过（见 §4 末）。不访问、不控制任何真实设备。
- 文中「实测」= 本会话对已落盘字节的计算；「页面自述」= DaRUS API 元数据字段 / 同作者软件的源码文本，两者不混列。

> **2026-10-21 本仓复算补记（KB0 §6 检查 27 · 台账 A-108）**：本报告的「实测」数字全部由第三方会话的
> `%TEMP%\d5171\*.py` 算出、脚本当时未入仓 ⟹ 对本仓而言这些数字属 `public-doc`（第三方会话产物，
> `verified_by ≠ self`，不计入独立核对 k），正文按检查 27 原本全部缺可重跑产物。
> 现补上仓内可重跑产物：`PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`
> —— 在仓内实体（`data/incoming/daRUS5171_listing_2026-10-20.json`、6 份 CDD CSV、`394085_CableActuatorTestRig.xml`）
> 上逐条复算本报告数字并打印 成立 / 不成立 / 无法复算；**打印出来的数字即本仓可重跑产物**（本轮输出快照 `build/probe_5171.out`）。
> 本轮实跑汇总由**脚本自己数并打印在输出末尾**（口径定义 `data/probe_tally.py`）：**对拍判定 成立 206 ‖
> 不成立 9（9 类，见各节「本仓复算更正」引文块）‖ 无法复算 12**（对象未落盘 / 需现场 GET，一律降为未核验），
> 另有脚本自设的子判定 12 行（不是本报告登记的断言）。此前此处手点的「219 / 24 / 12」是混合口径——
> 把判词出现在行中的叙述行与子判定一并计入，且「24 个断言行」与「9 类」是两个数，2026-10-21 起改引打印行。
> 以下引文块**不改正文原句**，只就地挂复算值与命令。

> **2026-10-21 本仓复算更正（§2.1 的 45 行表）**：逐行复算（probe §1.1，命令同上，快照 `build/probe_5171.out`）：
> CSV 数 / 目录内文件总数 / 最小-最大 CSV 字节 / 目录总字节 各列均未见行级不一致；
> 差异全部集中在 `id 范围` 列——按「目录内全部件」口径 **24/45 行不一致**（id 下界 14 行、上界 17 行），
> 按「目录内 CSV 件」口径 **45/45 行一致** ⟹ 该列口径可复现但表头未标注口径，须读作「目录内 CSV 件的 id 区间」。
> 本报告数字属第三方会话产物（`public-doc`，`verified_by ≠ self`，不计 k）。

---

## 1. 方法（逐条命令，可复跑）

```bash
# 1) 现场拉 listing（不用缓存）—— 响应 2,616,228 B，data.latestVersion.files = 3488
curl -sL "https://darus.uni-stuttgart.de/api/datasets/:persistentId/?persistentId=doi:10.18419/DARUS-5171" \
     -o /tmp/d5171/ds5171.json

# 2) 目录盘点（python 解析 listing）：5 个顶层试验台 + 261 个 directoryLabel
#    /tmp/d5171/{mktables.py, pick_other.py}

# 3) 证明访问端点支持 Range（可只读表头，避免动辄 44 MB 全量下载）
curl -sL -r 0-4000 -D - "https://darus.uni-stuttgart.de/api/access/datafile/394141"
#   -> HTTP/1.1 206 Partial Content, content-length: 4001, server: StorageGRID/11.9.0.14

# 4) 68 份 CDD CSV 逐个只取前 20 KB 表头（总流量 1.4 MB），提通道名/SampleTime/导出跨度
for id in <68 个 dataFile id>; do curl -sL -r 0-20000 ".../api/access/datafile/$id" -o heads/$id.bin; done  # xargs -P 6

# 5) 同样只读取每个试验目录最大 CSV 的前 30 KB（45 个目录，共 1.35 MB）→ §7 通道名盘点

# 6) 选样（filesize 降序前 6）后全量下载，3 并发
curl -sL "https://darus.uni-stuttgart.de/api/access/datafile/394141" -o CDD_2024-07-23_LdaFricIdent_RW_Export_5_id394141.csv

# 7) 字节核对
md5sum CDD_*.csv          # vs listing 的 dataFile.md5

# 8) 实测：六条硬拒 + 指令/反馈逐行差 + 通道量化/恒等式
python /tmp/d5171/analyze.py      # 逐行流式解析，全通道
python /tmp/d5171/verify.py       # 量化步长、运动段、恒等式（单样本）
python /tmp/d5171/ident.py        # 6/6 全量：恒等式残差 + x_Ltar/f_tar 恒值确认 + 运动/静止分段 fe
python /tmp/d5171/ratio.py        # 6/6 全量：f_Lm/tau_L 比值唯一性 + tau_T≡f_Tm
# 9) 语义外部取证（只读，兄弟数据集 DARUS-5170 控制软件）
curl -sL ".../api/datasets/:persistentId/?persistentId=doi:10.18419/DARUS-5170" -o ds5170.json
curl -sL ".../api/access/datafile/392319" -o src5170/Measurement_Connector_Ch2.TcPOU     # 变量赋值原文
curl -sL ".../api/access/datafile/392278" -o src5170/Measurement_Ch2.tcscopex            # SymbolName/Comment 原文
curl -sL ".../api/access/datafile/392290" -o src5170/Measurement_IOs.TcGVL               # 驱动 Istwert/Sollwert 声明
curl -sL ".../api/access/datafile/392409" -o src5170/DB_LOGGER_Data.TcDUT
curl -sL ".../api/access/datafile/394085" -o src5170/CableActuatorTestRig.xml            # 5171 内 CDD 配置原文
```

时基/抖动/NaN 的判据口径与项目 `data/validate_raw.py` 一致：`dt_jitter_ratio = pstdev(dt)/|median(dt)|`（KB2 §5.1 硬拒 3，C2 quality 口径），
NaN 看总体占比与最差通道占比（硬拒 4 上界 0.05）。

---

## 2. 数据集与目录盘点（现场 listing 实测）

实测：`latestVersion.files` = **3488** 条；`directoryLabel` 去重后 261 个；顶层试验台计数：

| 试验台 | 文件数（实测计数） |
|---|---|
| LIROS_D-Pro | 1175 |
| Trowis_PolyTropFOX | 1036 |
| Trowis_VectranHT_T190PU | 1033 |
| Winch_Testbed | 171 |
| **CableDirectDrive_Testbed** | **73** |

页面自述（API 元数据字段，非实测）：标题 `Measurement Data for Experimental Modeling of Synthetic Fiber Ropes for Slip Compensation for Application in Cable`；作者/存盘人 Reichenbach, Thomas（ORCID 0009-0005-2550-9289，Univ. Stuttgart）；
license **CC BY 4.0**（`latestVersion.license.name`，实测字段值）；发布日期 2026-07-20；
关联出版物 DOI `10.18419/opus-18505`（Fraunhofer Verlag 博士论文，2026）；资助 DFG 470674716；
描述把数据指向姊妹数据集 `10.18419/DARUS-5172`（分析工具箱）与 `10.18419/DARUS-5170`（台架控制软件），
并称「运动剖面以 NC 文件存放」。

### 2.1 CDD 之外的关键词目录（LdaFric / FrictionIdent / Slip / Comp / TempSlip 等，备查）

实测：45 个含 CSV 的试验目录（`45` 行含全部）：

| 试验目录 (top/2nd) | CSV 数 | 目录内文件总数 | 最小 CSV (B) | 最大 CSV (B) | id 范围 | 目录总字节 |
|---|---|---|---|---|---|---|
| CableDirectDrive_Testbed/2024-07-23_LdaFricIdent | 68 | 73 | 9106034 | 43939834 | 393961–394203 | 3406995039 |
| LIROS_D-Pro/2024-02-05_TempSlip | 181 | 185 | 4107918 | 764733171 | 394225–395094 | 4886999320 |
| LIROS_D-Pro/2024-04-15_PreloadedViscousFrictionIdent | 380 | 408 | 10067181 | 65621592 | 394219–395099 | 26348751799 |
| LIROS_D-Pro/2024-05-06_DynCapstanFrictionIdent | 40 | 54 | 12477763 | 28480885 | 394237–395093 | 1364968785 |
| LIROS_D-Pro/2024-05-23_PreloadedLuGreFrictionValidation | 9 | 18 | 22619169 | 48852347 | 394279–395071 | 574314102 |
| LIROS_D-Pro/2025-03-06_PreloadedLuGreFrictionIdent | 15 | 27 | 43608386 | 44118579 | 394305–394964 | 1444928687 |
| LIROS_D-Pro/2025-03-07a_StatSlipIdentLda | 154 | 181 | 8838640 | 35017919 | 394229–395097 | 4108511487 |
| LIROS_D-Pro/2025-03-07b_DynSlipIdentLda | 5 | 8 | 32341083 | 32742641 | 394344–394991 | 303805065 |
| LIROS_D-Pro/2025-03-11a_SlipIdent | 125 | 157 | 17569454 | 47750497 | 395103–395394 | 6341314190 |
| LIROS_D-Pro/2025-03-11b_CableRobotProfileFullIdent | 5 | 9 | 54088878 | 58210604 | 395175–395328 | 573068879 |
| LIROS_D-Pro/2025-03-11c_VelDynCompensationValid | 5 | 9 | 53895021 | 58004587 | 395242–395362 | 572097441 |
| LIROS_D-Pro/2025-03-11d_PowerDynCompensationValid | 5 | 9 | 54927932 | 58164771 | 395129–395382 | 573742484 |
| LIROS_D-Pro/2025-03-11f_StatCompensationValid | 72 | 92 | 8436328 | 35040196 | 395108–395392 | 2915735019 |
| LIROS_D-Pro/2025-03-12a_VelDynCompValidLda | 5 | 9 | 39414648 | 39695778 | 395102–395351 | 363975760 |
| LIROS_D-Pro/2025-03-12b_PowerDynCompValidLda | 5 | 9 | 39647614 | 39953901 | 395140–395323 | 365240380 |
| Trowis_PolyTropFOX/2025-01-22_PreloadedLuGreFrictionIdent | 15 | 27 | 40137751 | 44153490 | 396450–396824 | 1436956170 |
| Trowis_PolyTropFOX/2025-01-23_PreloadedViscousFrictionIdent | 380 | 402 | 16680374 | 73752029 | 396430–396867 | 32603106125 |
| Trowis_PolyTropFOX/2025-01-30a_PreloadedLuGreFrictionValidation | 5 | 9 | 27466457 | 28077264 | 396529–396862 | 306525831 |
| Trowis_PolyTropFOX/2025-01-30b_DynCapstanFrictionIdent | 40 | 50 | 13521578 | 30954758 | 396868–397135 | 1688936928 |
| Trowis_PolyTropFOX/2025-02-12e_TempSlip | 61 | 65 | 6364053 | 1305949284 | 396869–397139 | 3779580132 |
| Trowis_PolyTropFOX/2025-02-21_SlipIdent | 125 | 157 | 17804252 | 47706644 | 396870–397136 | 6336067624 |
| Trowis_PolyTropFOX/2025-02-25b_CableRobotProfileFullIdent | 5 | 9 | 53967950 | 58175642 | 397177–397373 | 572763680 |
| Trowis_PolyTropFOX/2025-03-03a_StatCompensationValid | 72 | 92 | 8351076 | 34974413 | 397141–397464 | 2910450820 |
| Trowis_PolyTropFOX/2025-03-03b_VelDynCompensationValid | 5 | 9 | 53826665 | 57988219 | 397176–397442 | 571888129 |
| Trowis_PolyTropFOX/2025-03-03c_PowerDynCompensationValid | 5 | 9 | 54072422 | 58221719 | 397167–397405 | 573106947 |
| Trowis_PolyTropFOX/2025-03-12a_StatSlipIdentLda | 154 | 183 | 7099019 | 38336335 | 397140–397460 | 4389048063 |
| Trowis_PolyTropFOX/2025-03-12b_DynSlipIdentLda | 5 | 8 | 35514186 | 35994974 | 397333–397436 | 344693982 |
| Trowis_PolyTropFOX/2025-03-12c_VelDynCompValidLda | 5 | 8 | 39478833 | 39887568 | 397351–397447 | 364459261 |
| Trowis_PolyTropFOX/2025-03-12d_PowerDynCompValidLda | 5 | 8 | 39766531 | 40287219 | 397252–397462 | 365969581 |
| Trowis_VectranHT_T190PU/2025-02-14a_PreloadedLuGreFrictionIdent | 15 | 27 | 43695212 | 47130330 | 395398–396107 | 1452588572 |
| Trowis_VectranHT_T190PU/2025-02-14b_PreloadedLuGreFrictionValidation | 5 | 9 | 27466680 | 28105768 | 395486–396056 | 306657258 |
| Trowis_VectranHT_T190PU/2025-02-14c_PreloadedViscousFrictionIdent | 380 | 402 | 16715697 | 74841959 | 395397–396142 | 32701683898 |
| Trowis_VectranHT_T190PU/2025-02-15a_DynCapstanFrictionIdent | 40 | 50 | 13503089 | 30923158 | 395408–396118 | 1688434572 |
| Trowis_VectranHT_T190PU/2025-02-15b_SlipIdent | 125 | 157 | 17667524 | 48269004 | 395412–396141 | 6353290082 |
| Trowis_VectranHT_T190PU/2025-02-20a_CableRobotProfileFullIdent | 5 | 9 | 54031056 | 57704262 | 395557–395693 | 570946703 |
| Trowis_VectranHT_T190PU/2025-02-20b_StatCompensationValid | 72 | 92 | 8313733 | 36525983 | 395402–396140 | 2902870553 |
| Trowis_VectranHT_T190PU/2025-02-21a_TempSlip | 61 | 65 | 6211142 | 1276812282 | 396143–396426 | 3721396042 |
| Trowis_VectranHT_T190PU/2025-02-21b_VelDynCompensationValid | 5 | 8 | 54565581 | 57847766 | 396174–396383 | 572058822 |
| Trowis_VectranHT_T190PU/2025-02-21c_PowerDynCompensationValid | 5 | 9 | 53714082 | 57931489 | 396185–396379 | 571486652 |
| Trowis_VectranHT_T190PU/2025-03-21_StatSlipIdentLda | 154 | 182 | 7062539 | 38327005 | 396144–396422 | 4118087449 |
| Trowis_VectranHT_T190PU/2025-03-25a_DynSlipIdentLda | 5 | 7 | 37124185 | 37625015 | 396193–396342 | 352714911 |
| Trowis_VectranHT_T190PU/2025-03-25b_VelDynCompValidLda | 5 | 8 | 39329814 | 39834735 | 396243–396427 | 363755278 |
| Trowis_VectranHT_T190PU/2025-03-25c_PowerDynCompValidLda | 5 | 8 | 39865951 | 40157213 | 396214–396334 | 366268238 |
| Winch_Testbed/2023-10-12_ViscousFrictionIdent | 152 | 158 | 10852322 | 37242904 | 393962–394204 | 3736021261 |
| Winch_Testbed/2023-12-06_LuGre_PeakSignal_AccMin | 10 | 13 | 20998931 | 25598900 | 394002–394189 | 245189590 |

> 说明：5171 内**没有**名字含 `Position`/`ClosedLoop`/`Tracking` 的目录；闭环位置控制的线索全部落在上表的
> `*SlipIdent* / *FrictionIdent / *CompensationValid / *Lda / *TempSlip` 试验里，通道集见 §7。

### 2.2 CableDirectDrive_Testbed 全量 73 条记录（现场 listing 原文，按目录+大小排序）

| dataFile id | directoryLabel（去掉 CableDirectDrive_Testbed/ 前缀） | filename | filesize (B) | md5 | contentType | 创建日期 |
|---|---|---|---|---|---|---|
| 393995 | 2024-07-23_LdaFricIdent/Data/RW | Lda_Fric_RW.svdx | 862689654 | 920a7e92232840db6fa2d05626f6d1be | application/octet-stream | 2025-07-22 |
| 394141 | 2024-07-23_LdaFricIdent/Data/RW | Export 5.csv | 43939834 | 7f4c54ded42716c5330eccc5acd0215c | text/csv | 2025-07-22 |
| 394119 | 2024-07-23_LdaFricIdent/Data/RW | Export 3.csv | 43840132 | 712ce88cb9a723dd16c07e61445e4eca | text/csv | 2025-07-22 |
| 394158 | 2024-07-23_LdaFricIdent/Data/RW | Export 7.csv | 43786718 | e8b3a84e1e71d66e8cab69c85c1916a8 | text/csv | 2025-07-22 |
| 394111 | 2024-07-23_LdaFricIdent/Data/RW | Export 6.csv | 43771311 | fbfd35e74a238826423d092bb0b4e177 | text/csv | 2025-07-22 |
| 393969 | 2024-07-23_LdaFricIdent/Data/RW | Export 9.csv | 43739218 | 78fe0347190820a35f365ee2a9252dad | text/csv | 2025-07-22 |
| 394117 | 2024-07-23_LdaFricIdent/Data/RW | Export 11.csv | 43714378 | 7d33d0be44d4ea1af2a9afa2e392eba1 | text/csv | 2025-07-22 |
| 394008 | 2024-07-23_LdaFricIdent/Data/RW | Export 10.csv | 43700198 | 62326eb83e0d31396c1d0d422254b5fe | text/csv | 2025-07-22 |
| 394071 | 2024-07-23_LdaFricIdent/Data/RW | Export 8.csv | 43365286 | b00149cfdd75194195960d9d8bc7bdb4 | text/csv | 2025-07-22 |
| 393997 | 2024-07-23_LdaFricIdent/Data/RW | Export 12.csv | 42982812 | b9098066f7aa43904232a8c53c3739b6 | text/csv | 2025-07-22 |
| 393981 | 2024-07-23_LdaFricIdent/Data/RW | Export 13.csv | 42872347 | dfc171bdea414b3ba18f068ea8b7b7ec | text/csv | 2025-07-22 |
| 393993 | 2024-07-23_LdaFricIdent/Data/RW | Export 2.csv | 42618369 | db1dfa1b6864980db95d7972abd9e847 | text/csv | 2025-07-22 |
| 394028 | 2024-07-23_LdaFricIdent/Data/RW | Export 4.csv | 41870952 | 9154474e2d23f81fd9d41996079bba8b | text/csv | 2025-07-22 |
| 394088 | 2024-07-23_LdaFricIdent/Data/RW | Export 14.csv | 37343842 | 303c8a255ef8c715418f237e21c81182 | text/csv | 2025-07-22 |
| 394081 | 2024-07-23_LdaFricIdent/Data/RW | Export 1.csv | 30471218 | b34b6490fe7e0cdf4f9a3cd99c33b499 | text/csv | 2025-07-22 |
| 394121 | 2024-07-23_LdaFricIdent/Data/RW | Export 15.csv | 30110533 | 5528b9ce7db87a8bd5282ef1d0872ef4 | text/csv | 2025-07-22 |
| 394132 | 2024-07-23_LdaFricIdent/Data/RW | Export 16.csv | 22891218 | 7b2cac19dea819338397c2c17ce215f0 | text/csv | 2025-07-22 |
| 394077 | 2024-07-23_LdaFricIdent/Data/RW | Export 17.csv | 19236354 | 1956f915dc3ffbb0e5b0ba9585a39af7 | text/csv | 2025-07-22 |
| 394107 | 2024-07-23_LdaFricIdent/Data/RW | Export 18.csv | 17118449 | 632534300ea9020e19fc52926d3dce42 | text/csv | 2025-07-22 |
| 393967 | 2024-07-23_LdaFricIdent/Data/RW | Export 19.csv | 15804586 | d8ddc995ef96478782a41a823f1b3a0f | text/csv | 2025-07-22 |
| 394044 | 2024-07-23_LdaFricIdent/Data/RW | Export 20.csv | 12886696 | 57e2621cd83bc135961400b934d40f8d | text/csv | 2025-07-22 |
| 394074 | 2024-07-23_LdaFricIdent/Data/RW | Export 21.csv | 11416349 | 848062fae33aa752a74d9a1fbea686ac | text/csv | 2025-07-22 |
| 394053 | 2024-07-23_LdaFricIdent/Data/RW | Export 22.csv | 10702744 | 73dce400d9f1b62cb836fcb2f3734367 | text/csv | 2025-07-22 |
| 394195 | 2024-07-23_LdaFricIdent/Data/RW | Export 23.csv | 10255802 | 61fd7667f69f59efd1d2e91026d579e2 | text/csv | 2025-07-22 |
| 394056 | 2024-07-23_LdaFricIdent/Data/RW | Export 24.csv | 9973064 | db21f39d0949b9ab06df48dfecfc0782 | text/csv | 2025-07-22 |
| 394023 | 2024-07-23_LdaFricIdent/Data/RW | Export 25.csv | 9791274 | 2dd1efc87aa170deb8b0e5ba4919c87b | text/csv | 2025-07-22 |
| 394118 | 2024-07-23_LdaFricIdent/Data/RW | Export 26.csv | 9628923 | 6abad005adaa09d3bf990b9bead7414e | text/csv | 2025-07-22 |
| 394005 | 2024-07-23_LdaFricIdent/Data/RW | Export 27.csv | 9516824 | 6965e55ea8bc71532b96910be5fb0e9d | text/csv | 2025-07-22 |
| 394143 | 2024-07-23_LdaFricIdent/Data/RW | Export 28.csv | 9417626 | d9526559173558a03a9f340faa4b0b80 | text/csv | 2025-07-22 |
| 394203 | 2024-07-23_LdaFricIdent/Data/RW | Export 29.csv | 9313943 | beba2d3d77d5ebcf6c9fbf25d564886d | text/csv | 2025-07-22 |
| 394165 | 2024-07-23_LdaFricIdent/Data/RW | Export 30.csv | 9260106 | e1614bf15c6d41c7d37240827230fc75 | text/csv | 2025-07-22 |
| 394098 | 2024-07-23_LdaFricIdent/Data/RW | Export 31.csv | 9199736 | 7426550d9bf2cf5e06cd4d1f9da1d693 | text/csv | 2025-07-22 |
| 394087 | 2024-07-23_LdaFricIdent/Data/RW | Export 32.csv | 9157554 | e8e2d56ce85b3477deb4960ed4f36bef | text/csv | 2025-07-22 |
| 393964 | 2024-07-23_LdaFricIdent/Data/RW | Export 33.csv | 9135420 | 670a26a05374d462d6ed9bb6d8904fb1 | text/csv | 2025-07-22 |
| 394050 | 2024-07-23_LdaFricIdent/Data/RW | Export 34.csv | 9106034 | ac90287d2a10913161fa385bcbdc8bfd | text/csv | 2025-07-22 |
| 394173 | 2024-07-23_LdaFricIdent/Data/RW | LDA_Fric_RW.nc | 8814 | f611a464bea721343d98e8f6139f249e | application/x-netcdf | 2025-07-22 |
| 394015 | 2024-07-23_LdaFricIdent/Data/UW | Lda_Fric_UW.svdx | 861983893 | ffa64388a6d341ed1036e0630911145b | application/octet-stream | 2025-07-22 |
| 393961 | 2024-07-23_LdaFricIdent/Data/UW | Export 5.csv | 43868904 | 70d70a6cf33a624f6982c1c373c775ba | text/csv | 2025-07-22 |
| 393966 | 2024-07-23_LdaFricIdent/Data/UW | Export 7.csv | 43852861 | 430856dc908923e603837f4953a450b3 | text/csv | 2025-07-22 |
| 394009 | 2024-07-23_LdaFricIdent/Data/UW | Export 9.csv | 43847854 | 805b0659e5e5246ceb580aea466d3606 | text/csv | 2025-07-22 |
| 394169 | 2024-07-23_LdaFricIdent/Data/UW | Export 6.csv | 43834657 | 4b46f86877fb82050c9b6ceacc283742 | text/csv | 2025-07-22 |
| 393987 | 2024-07-23_LdaFricIdent/Data/UW | Export 3.csv | 43788937 | f2646977f3e910375261663597322180 | text/csv | 2025-07-22 |
| 394122 | 2024-07-23_LdaFricIdent/Data/UW | Export 10.csv | 43772282 | ea6ab04f835a79ea4f13e112b22c7267 | text/csv | 2025-07-22 |
| 394083 | 2024-07-23_LdaFricIdent/Data/UW | Export 8.csv | 43485058 | 2f70f918bafd8e3caa23c11ef5434014 | text/csv | 2025-07-22 |
| 394001 | 2024-07-23_LdaFricIdent/Data/UW | Export 11.csv | 43401347 | 917709aba21ad9a2f5f7054956e093e3 | text/csv | 2025-07-22 |
| 394136 | 2024-07-23_LdaFricIdent/Data/UW | Export 13.csv | 42752771 | 96d96d8cb2b3d29debf290037d14966b | text/csv | 2025-07-22 |
| 394016 | 2024-07-23_LdaFricIdent/Data/UW | Export 12.csv | 42711356 | d8cca4da4433547aa68a213668af52fa | text/csv | 2025-07-22 |
| 394199 | 2024-07-23_LdaFricIdent/Data/UW | Export 2.csv | 42619096 | fd095d340302a5ab986a45f513d4d251 | text/csv | 2025-07-22 |
| 394174 | 2024-07-23_LdaFricIdent/Data/UW | Export 4.csv | 41887699 | 9df3d50fd9928eca3b97385182819425 | text/csv | 2025-07-22 |
| 394162 | 2024-07-23_LdaFricIdent/Data/UW | Export 14.csv | 37294312 | f41668a4d2da9f36db6e4cc961a8d20e | text/csv | 2025-07-22 |
| 394010 | 2024-07-23_LdaFricIdent/Data/UW | Export 15.csv | 30125288 | daf276f99cf181d08b9db07b05d67cf5 | text/csv | 2025-07-22 |
| 394201 | 2024-07-23_LdaFricIdent/Data/UW | Export 1.csv | 28332240 | 99083eef8b3e3d967efe84208d6d30a9 | text/csv | 2025-07-22 |
| 394160 | 2024-07-23_LdaFricIdent/Data/UW | Export 16.csv | 22888104 | a30c6b5f37abf1e1bf4781215adca5e6 | text/csv | 2025-07-22 |
| 394159 | 2024-07-23_LdaFricIdent/Data/UW | Export 17.csv | 19291044 | 0c3bc2b65681724dba39fa9437dcb58e | text/csv | 2025-07-22 |
| 394025 | 2024-07-23_LdaFricIdent/Data/UW | Export 18.csv | 17192783 | d67b78b8a60518c13bf1bfb995027131 | text/csv | 2025-07-22 |
| 394004 | 2024-07-23_LdaFricIdent/Data/UW | Export 19.csv | 15875778 | c240d023812458f9933aab3c17e200a3 | text/csv | 2025-07-22 |
| 393982 | 2024-07-23_LdaFricIdent/Data/UW | Export 20.csv | 12946471 | d091cdb48e6d74180420b775ddb5bd9f | text/csv | 2025-07-22 |
| 394123 | 2024-07-23_LdaFricIdent/Data/UW | Export 21.csv | 11484144 | 7fdb09afdbe931b3fd3db113bead3d62 | text/csv | 2025-07-22 |
| 394021 | 2024-07-23_LdaFricIdent/Data/UW | Export 22.csv | 10758805 | c7a02361d120032a778eb56c7a674571 | text/csv | 2025-07-22 |
| 394104 | 2024-07-23_LdaFricIdent/Data/UW | Export 23.csv | 10316721 | de0ce8e0dd20f04583e3a6dfa7f302ad | text/csv | 2025-07-22 |
| 394151 | 2024-07-23_LdaFricIdent/Data/UW | Export 24.csv | 10040084 | 832a9751a16a1864de3bdf57159bc735 | text/csv | 2025-07-22 |
| 393988 | 2024-07-23_LdaFricIdent/Data/UW | Export 25.csv | 9827270 | 610b290053b782b1f7729aa8e7bb1a1b | text/csv | 2025-07-22 |
| 394197 | 2024-07-23_LdaFricIdent/Data/UW | Export 26.csv | 9670448 | 582d8bccfa6145591948af51f3b8c61e | text/csv | 2025-07-22 |
| 394073 | 2024-07-23_LdaFricIdent/Data/UW | Export 27.csv | 9552171 | 29d32b0302e99cf2319a140178f29ce2 | text/csv | 2025-07-22 |
| 394089 | 2024-07-23_LdaFricIdent/Data/UW | Export 28.csv | 9460246 | aa5f83458dd8556dd6770136652b6459 | text/csv | 2025-07-22 |
| 394069 | 2024-07-23_LdaFricIdent/Data/UW | Export 29.csv | 9378644 | 6889ee3e9a69da9e56bd847d01e3592c | text/csv | 2025-07-22 |
| 394068 | 2024-07-23_LdaFricIdent/Data/UW | Export 30.csv | 9316817 | 810fbf177159f34176ec31aad23d2745 | text/csv | 2025-07-22 |
| 394179 | 2024-07-23_LdaFricIdent/Data/UW | Export 31.csv | 9259421 | ea890ef0a0d9158d41fac9fbce8d1787 | text/csv | 2025-07-22 |
| 394147 | 2024-07-23_LdaFricIdent/Data/UW | Export 32.csv | 9217428 | 2b0c3e08cfceae7ea4bc4c2bdd4b5832 | text/csv | 2025-07-22 |
| 394012 | 2024-07-23_LdaFricIdent/Data/UW | Export 33.csv | 9171856 | a031b1d3254121e562a621e8375c0d76 | text/csv | 2025-07-22 |
| 394170 | 2024-07-23_LdaFricIdent/Data/UW | Export 34.csv | 9138922 | 52a336ead2faf1f1e550652aa7a8b2b6 | text/csv | 2025-07-22 |
| 394065 | 2024-07-23_LdaFricIdent/Data/UW | LDA_Fric_UW.nc | 8541 | c060215091f135480847ae779168b1fa | application/x-netcdf | 2025-07-22 |
| 394085 | 2024-07-23_LdaFricIdent/Settings | CableActuatorTestRig.xml | 2468 | 67eeb6e33abacfaa7572b6b5ac82d812 | text/xml | 2025-07-22 |

实测汇总：73 条 = 68 份 `text/csv` + 2 份 `application/octet-stream`（`Lda_Fric_RW.svdx` 862,689,654 B、`Lda_Fric_UW.svdx` 861,983,893 B，
TwinCAT Scope 原始二进制）+ 2 份 `application/x-netcdf`（`LDA_Fric_RW.nc` 8814 B、`LDA_Fric_UW.nc` 8541 B）+ 1 份 `text/xml`
（`CableActuatorTestRig.xml` 2468 B）；目录内合计 3,406,995,039 B。
CSV 全部是 `Export <N>.csv`，N=1…34，RW / UW 两侧各一份，**同名不同 id 不同 md5**（例如 `Export 10.csv` 在本数据集里至少 4 个不同 id），
再次证实「文件名不是标识」：本目录的唯一标识是 `dataFile id + md5 + directoryLabel`。

> 只读实测（前 4 KB）：`LDA_Fric_*.nc` 的魔数是 `G90\r`，**不是 netCDF**，而是 CNC G 代码程序；
> 内含 34 个块 `==== 1: F9 ====` … `==== 34: F240000 ====`，与 `Export 1.csv … Export 34.csv` 一一对应
> （每块：先 `G01 WT=… F60000` 走位、`G04 2`、`M92=1` 触发记录、以 `F<feed>` 走完再返回）。
> 也就是说：**一份 CSV = 一个给定进给速度的摩擦辨识段**，RW/UW 成对。这是「页面自述（NC 文件=运动剖面）」与实际字节（G 代码文本）不一致的一处，需注意。

> **2026-10-21 本仓复算更正（§2.2）**：73 行表逐行复算（id/目录/原名/字节/md5/类型/创建日）**0 行差异，73/73 一致 ⟹ 成立**；末「实测汇总」（68 CSV + 2 octet-stream + 2 x-netcdf + 1 xml、目录合计 3,406,995,039 B、5 个单件字节）复算均成立。两处需更正/降级：① `Export 10.csv`「在本数据集里至少 4 个不同 id」按**全数据集**口径复算成立（125 条 / 125 个不同 id），但在 §2.2 表所辖 **CDD 目录**口径下只有 2 个 id（394008/394122）⟹ 目录口径下**不成立**，原句须读作「全数据集」口径；② `.nc` 魔数 `G90\r` / 34 个块 / 非 netCDF：两件（8814/8541 B）未落盘 ⟹ **无法复算**（需现场 GET id 394173/394065），按检查 27 降为未核验。复算命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）；以上复算值为本轮打印，原报告数字属第三方会话产物（`verified_by ≠ self`，`public-doc`，不计入 k）。

---

## 3. 68 份 CDD CSV 的表头普查（只读 Range，前 20 KB）

实测：68 份的通道集**完全一致**（40 通道，顺序也一致），`SampleTime[ms]` 全为 **1**，表头 `Endtime−Starttime` 跨度 16.694…76.007 s。
40 通道原文（抄自 `Name` 行，L07）：

`f_kistler1 | f_kistler2 | f_L | f_T | f_tar | f_Tm | f_Lm | f_diff | x_L | x_Ltar | x_T | x_Ttar | x_diff | v_L | v_Ltar | v_T | v_Ttar | v_diff | tau_L | tau_T | trig_exp | trig_rec | trig_scope | dir | f_no | x_asco_enc | x_asco_serial | Rate_asco | w_asco_serial | v_asco_enc | v_asco_serial | dx_asco_serial | P_L | P_T | x_lsv_enc | v_lsv_enc | a_Ltar | a_Ttar | theta_L | theta_T`

`Data-Type` 行（L08）：36 个 `REAL64` + `trig_exp/trig_rec/trig_scope` = `BIT` + `dir` = `INT16` + `f_no` = `UINT16`。
**该变体没有 `SymbolBased` / `SymbolName` / `NetID` / `Port` 行，也没有 `EOF` 尾行**（与已确认的 DARUS-3600 布局不同，14 行表头 → 这里是 10 行）。

> **2026-10-21 本仓复算更正（§3）**：在仓内落盘 6 份复算：40 个通道名与顺序 6/6 一致、`SampleTime[ms]` 全 = 1 ⟹ **成立**；
> `Data-Type` 行复算 **REAL64 = 35**（35 + BIT 3 + INT16 1 + UINT16 1 = 40 通道）⟹ 原句「36 个 `REAL64`」**不成立**（且原句口径 36+3+1+1=41>40 本身不自洽）；
> 「**68 份** CDD CSV 的通道集完全一致 / 跨度 16.694…76.007 s」的全量口径：仓内只有 6/68 份，另 62 份表头需现场 GET（Range 0-20000）⟹ **无法复算**，按检查 27 降为未核验。
> 「这里是 10 行」与复算一致（§6 逐样本块的「表头行 11」与之矛盾，见该节更正块）。复算命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）；
> 本轮打印值为证，原报告数字属第三方会话产物（`verified_by ≠ self`，`public-doc`，不计入 k）。

---

## 4. 选样、下载与字节一致性

按 filesize 从大到小取前 6（全部 43.7–43.9 MB，同一试验、同一 40 通道集；RW 侧 2 份 + UW 侧 4 份，含 E5 的 RW/UW 配对）：

| dataFile id | DaRUS 目录 / 原始 filename | 本地落盘名 | listing filesize (B) | 磁盘字节 (B) | listing md5 | 实测 md5sum | 字节一致 |
|---|---|---|---|---|---|---|---|
| 394141 | RW / Export 5.csv | CDD_2024-07-23_LdaFricIdent_RW_Export_5_id394141.csv | 43939834 | 43939834 | 7f4c54ded42716c5330eccc5acd0215c | 7f4c54ded42716c5330eccc5acd0215c | 一致 |
| 393961 | UW / Export 5.csv | CDD_2024-07-23_LdaFricIdent_UW_Export_5_id393961.csv | 43868904 | 43868904 | 70d70a6cf33a624f6982c1c373c775ba | 70d70a6cf33a624f6982c1c373c775ba | 一致 |
| 393966 | UW / Export 7.csv | CDD_2024-07-23_LdaFricIdent_UW_Export_7_id393966.csv | 43852861 | 43852861 | 430856dc908923e603837f4953a450b3 | 430856dc908923e603837f4953a450b3 | 一致 |
| 394009 | UW / Export 9.csv | CDD_2024-07-23_LdaFricIdent_UW_Export_9_id394009.csv | 43847854 | 43847854 | 805b0659e5e5246ceb580aea466d3606 | 805b0659e5e5246ceb580aea466d3606 | 一致 |
| 394119 | RW / Export 3.csv | CDD_2024-07-23_LdaFricIdent_RW_Export_3_id394119.csv | 43840132 | 43840132 | 712ce88cb9a723dd16c07e61445e4eca | 712ce88cb9a723dd16c07e61445e4eca | 一致 |
| 394169 | UW / Export 6.csv | CDD_2024-07-23_LdaFricIdent_UW_Export_6_id394169.csv | 43834657 | 43834657 | 4b46f86877fb82050c9b6ceacc283742 | 4b46f86877fb82050c9b6ceacc283742 | 一致 |

- `md5sum` 与现场 listing 的 `dataFile.md5` **6/6 全等**，落盘字节数与 `filesize` 全等 → 6 份均 **official-artifact**（上游对象核对，非同源自证）。
  > **2026-10-21 本仓复算（§4）**：6 件的本地字节数与 md5 vs `data/incoming/daRUS5171_listing_2026-10-20.json` 全部复算**一致（6/6）**，
  > 6 份合计 263,184,242 B 复算成立，>200 MB 跳过件（395031/397119/396206）的 listing 字节亦复算成立；本节无不符项。
  > 命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）。
- 跳过（>200 MB 上限）：同目录 `Lda_Fric_RW.svdx` = 862,689,654 B、`Lda_Fric_UW.svdx` = 861,983,893 B；
  其它目录的 `TempSlip.csv` 更大（实测 listing：395031 = 764,733,171 B；397119 = 1,305,949,284 B；396206 = 1,276,812,282 B），同样只取表头未下载。
- 落盘改名：`CDD_2024-07-23_LdaFricIdent_<RW|UW>_Export_<N>_id<dataFileId>.csv`，改名理由是本目录内 `Export <N>.csv` 同名不唯一；
  原名保留在各 `.source.txt` 的 `original_filename` 与 `upstream_id` 字段里。

---

## 5. 表头原文（实测落盘字节，id=394141 为例）

> `Name <TAB> Measurement_Ch2 <TAB> `
> `File <TAB> [REDACTED_HOST_PATH] 5.csv <TAB> `
> `Starttime of export <TAB> [REDACTED_WALLCLOCK] <TAB> [REDACTED_WALLCLOCK] <TAB> [REDACTED_WALLCLOCK]`
> `Endtime of export <TAB> [REDACTED_WALLCLOCK] <TAB> [REDACTED_WALLCLOCK] <TAB> [REDACTED_WALLCLOCK]`

（`L07/L08/L09` 三行为 40 组 `Name/Data-Type/SampleTime[ms]` 交替字段，上面截断显示；完整长度实测 981/1143/1153 字符。）

> **2026-10-21 本仓复算更正（§5）**：`L07/L08/L09` 三行字符长度在 id394141 落盘字节上复算为 **507/669/679**（原登记 981/1143/1153）⟹ **不成立**。
> 本节其余复算全部成立：表头共 10 行（首个数据行为 1 基第 11 行）、无 `EOF` 尾行、每行 80 个 TAB 字段、x 轴列 = 行序号 0…75867、
> 通道表 8 行（x_L/x_Ltar/x_T/x_Ttar/tau_L/tau_T/f_Tm/P_T 的首末行值、唯一值数、最小量化步长）逐字段命中；`File` 行第 2 字段为上游绝对路径（按脱敏纪律不复述，probe 只打印其 basename 尾段 `Export 5.csv`）。
> 复算命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）；本轮打印值为证，原报告数字属第三方会话产物（`verified_by ≠ self`，`public-doc`，不计入 k）。

数据区实测：每行 **80 个 TAB 字段** = 40 × (x 轴, 通道值)；第 k 通道值在第 2k+1 列，其 x 轴列实测等于行序号（0,1,2,…），
`SampleTime[ms]=1` → x 轴即 ms 口径的时间列。末行实测序号 75867，无 `EOF` 尾行。

解析用的列映射（实测首/末行值对照，节选，可据此复核 §6/§7 的角色归属）：

| 通道序号 | 名 | 首行值 | 末行值 | 实测唯一值数 | 最小量化步长 |
|---|---|---|---|---|---|
| 8 | `x_L` | -1.413991190486 | -1.4139912590412 | 50 | 1.71388e-08 |
| 9 | `x_Ltar` | -1.4139912076248002 | -1.4139912076248002 | **1（恒值）** | — |
| 10 | `x_T` | 1.835008 | 1.810008 | 61879 | 2e-06 |
| 11 | `x_Ttar` | 1.8350072 | 1.8100083 | 63868 | 1e-07 |
| 18 | `tau_L` | -0.03 | -0.04 | 10 | 0.01 |
| 19 | `tau_T` | 66 | 25 | 336 | 1.0（全整数值） |
| 5 | `f_Tm` | 66 | 25 | 336 | 1.0 |
| 33 | `P_T` | 9806 | 4865 | 11831 | 整数 |

---

## 6. 六条硬拒实测（KB2 §5.1）

| dataFile id | 目录 / 原始文件名 | 数据行 | fs (Hz) | 时长 (s) | dt_jitter_ratio | NaN overall | NaN 最差通道 | 恒值通道 | 动态通道 |
|---|---|---|---|---|---|---|---|---|---|
| 394141 | RW / Export 5.csv | 75868 | 1000 | 75.867 | 0 | 0 | 0 | 16 | 24 | PASS |
| 393961 | UW / Export 5.csv | 75768 | 1000 | 75.767 | 0 | 0 | 0 | 16 | 24 | PASS |
| 393966 | UW / Export 7.csv | 76008 | 1000 | 76.007 | 0 | 0 | 0 | 16 | 24 | PASS |
| 394009 | UW / Export 9.csv | 75938 | 1000 | 75.937 | 0 | 0 | 0 | 16 | 24 | PASS |
| 394119 | RW / Export 3.csv | 75840 | 1000 | 75.839 | 0 | 0 | 0 | 16 | 24 | PASS |
| 394169 | UW / Export 6.csv | 75843 | 1000 | 75.842 | 0 | 0 | 0 | 16 | 24 | PASS |

**6/6 全部通过**，逐条：

1. 数据行 ≥ 2000 → 实测 75,768…76,008 行；
2. 有效时长 ≥ 0.5 s → 实测 75.767…76.007 s（时间列 ms 口径 ÷1000）；时基三口径互洽：
   时间列跨度 = 表头 `SampleTime[ms]=1` × (行数−1) = 表头 `Endtime−Starttime`（100 ns 记号 ÷1e7），例如 id394141 三者同为 75.867 s；
3. `dt_jitter_ratio` ≤ 0.2 → 实测 **0**（dt 恒为 1，min=max=1，std=0，严格单调）；
4. NaN 占比 ≤ 0.05 → 实测 **0**（0 非数值单元 / 3,034,720 单元；最差通道亦 0）；
5. 存在动态分段 → 实测 40 通道中 **24 个非恒值**（`f_kistler1/2, f_L, f_T, f_diff, x_L, x_T, x_Ttar, x_diff, v_L, v_Ltar, v_T, v_Ttar, v_diff, tau_T, P_T, theta_L, theta_T, a_Ttar, trig_exp, trig_rec, f_Lm, f_Tm` 等）；
   恒值 16 个：`f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar`
   —— 其中 ASCOspeed / LSV 两套线性编码器与 `P_L` 全程恒值（`x_asco_*`、`v_asco_*` 恒 0，`x_lsv_enc` 恒 5e-06），
   属「该段未使能/未接」的死通道，接入时要显式降级，不能当第三位置反馈用；
6. 位置指令/反馈/电流三类角色不全缺 → 实测存在位置指令（`x_Ttar`, `x_Ltar`）、位置反馈（`x_T`, `x_L`）、速度指令/反馈（`v_*tar` / `v_*`）与驱动侧力矩/力实际值（`tau_T`, `tau_L`）；**无电流命名通道**。

| id | side/file | rows | fs (Hz) | 时长 (s) | dt_jitter_ratio | NaN(overall) | NaN(worst ch) | 恒值通道数 | x_Ttar−x_T 不等行 | std | max\|d\| | x_Ltar−x_L 不等行 | std | max\|d\| | v_Ttar−v_T 不等行 | max\|d\| |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| id394141 | RW_Export_5_id394141 | 75868 | 1000 | 75.867 | 0 | 0 | 0 | 16 | 64477/75868 (0.8499) | 3.441e-05 | 0.001584 | 70527/75868 (0.9296) | 1.107e-07 | 5.313e-07 | 75868/75868 | 0.1676 |
| id393961 | UW_Export_5_id393961 | 75768 | 1000 | 75.767 | 0 | 0 | 0 | 16 | 64136/75768 (0.8465) | 5.924e-05 | 0.003121 | 70488/75768 (0.9303) | 1.103e-07 | 5.484e-07 | 74650/75768 | 0.233 |
| id393966 | UW_Export_7_id393966 | 76008 | 1000 | 76.007 | 0 | 0 | 0 | 16 | 64354/76008 (0.8467) | 5.88e-05 | 0.003111 | 70584/76008 (0.9286) | 1.101e-07 | 4.97e-07 | 74877/76008 | 0.2304 |
| id394009 | UW_Export_9_id394009 | 75938 | 1000 | 75.937 | 0 | 0 | 0 | 16 | 64458/75938 (0.8488) | 5.876e-05 | 0.003097 | 70582/75938 (0.9295) | 1.1e-07 | 5.313e-07 | 75773/75938 | 0.2318 |
| id394119 | RW_Export_3_id394119 | 75840 | 1000 | 75.839 | 0 | 0 | 0 | 16 | 64184/75840 (0.8463) | 3.415e-05 | 0.00155 | 70463/75840 (0.9291) | 1.106e-07 | 5.142e-07 | 74968/75840 | 0.1662 |
| id394169 | UW_Export_6_id394169 | 75843 | 1000 | 75.842 | 0 | 0 | 0 | 16 | 64226/75843 (0.8468) | 5.917e-05 | 0.003117 | 70331/75843 (0.9273) | 1.101e-07 | 4.97e-07 | 74679/75843 | 0.2341 |

> **2026-10-21 本仓复算更正（§6）**：六条硬拒在 6 份落盘件全量行复算：数据行 75,768…76,008、时长/挂钟/`SampleTime` 三口径互洽、`dt_jitter_ratio` 0、NaN 0（各件 3,030,720…3,040,320 单元）、恒值通道 16 个（名单**集合级一致**，仅排序不同）、动态 24 ⟹ 两张表与逐条列举的数字**全部成立**。两处标注：① 动态 24 名单原句点名 22 个后以「等」收尾，不是封闭断言 ⟹ **无法复算**（不构成不成立）；② 下方「逐样本补充数值」6 个块各写的「表头行 **11**」复算为 **10**（首个数据行是 1 基第 11 行；与 §3 原句「这里是 10 行」一致、与本句矛盾，复算支持 10）⟹ **不成立（×6）**；6 个块的其余解析字段（数据行、尾行 0、NaN、各差列 mean/min/max/std、抽查 nuniq/范围/std、`tau_L−f_Lm` max|d| 区间）复算 **0 项不一致**。复算命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）；本轮打印值为证，原报告数字属第三方会话产物（`verified_by ≠ self`，`public-doc`，不计入 k）。

### 逐样本补充数值

#### dataFile id=id394141  (CDD_2024-07-23_LdaFricIdent_RW_Export_5_id394141.csv)
- 数据行 75868，表头行 11，尾行 0（无 EOF）；时间列首/末 = 0 / 75867，dt 中位 1、最小 1、最大 1、std 0 → dt_jitter_ratio = 0
- 时长（时间列，ms 口径）= 75867 → 75.867 s；表头 SampleTime[ms] = 1 → fs = 1000 Hz；导出挂钟（表头 Starttime/Endtime 之差 / 1e7）= 75.867 s（三方互洽）
- 非数值/NaN 单元 0 / 3034720 → overall = 0，最差通道 = 0
- 恒值通道 16 个：f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar
- x_Ltar - x_L：比对 75868 行，不等 70527 行 (0.9296)，std 1.107e-07，mean -7.92e-09，min -4.456e-07，max 5.313e-07，max|d| 5.313e-07，最小非零|d| 1.714e-08
- x_Ttar - x_T：比对 75868 行，不等 64477 行 (0.8499)，std 3.441e-05，mean 2.312e-07，min -0.001297，max 0.001584，max|d| 0.001584，最小非零|d| 2e-07
- v_Ltar - v_L：比对 75868 行，不等 75868 行 (1.0000)，std 0.000611，mean -2.489e-06，min -0.002528，max 0.00253，max|d| 0.00253，最小非零|d| 2.057e-07
- v_Ttar - v_T：比对 75868 行，不等 75868 行 (1.0000)，std 0.005934，mean -0.0009929，min -0.1557，max 0.1676，max|d| 0.1676，最小非零|d| 2e-06
- f_tar - f_L：比对 75868 行，不等 75868 行 (1.0000)，std 0.8031，mean 108.5，min 106，max 110，max|d| 110，最小非零|d| 106
- f_tar - f_T：比对 75868 行，不等 75868 行 (1.0000)，std 0.2659，mean 100.5，min 87.35，max 109，max|d| 109，最小非零|d| 87.35
- 动态量抽查：tau_T nuniq=336 [-1426, 1363] std=39.4365；tau_L nuniq=10 [-0.1, -0.01] std=0.0196436；P_T nuniq=11831 [-5.52773e+07, 6.59237e+07] std=2.09934e+06；x_T nuniq=61879 [1.81001, 3.80125]；x_Ttar nuniq=63868 [1.81001, 3.79999]；f_T nuniq=65512 std=0.265936；theta_L nuniq=230 [23.37,27.48]
- 恒等式复算（vs 5170 现行版 Measurement_Connector_Ch2 源码）：x_diff 与 −(x_L+x_T) 的行级最大残差、v_diff 与 −(v_L+v_T)、f_diff 与 f_T−f_L、tau_T 与 f_Tm、tau_L 与 f_Lm：见正文；tau_T−f_Tm 在本文件 max|d|=[0.0, 0.0]，tau_L−f_Lm max|d|=[1.0083299389002038, 10.083299389002038]

#### dataFile id=id393961  (CDD_2024-07-23_LdaFricIdent_UW_Export_5_id393961.csv)
- 数据行 75768，表头行 11，尾行 0（无 EOF）；时间列首/末 = 0 / 75767，dt 中位 1、最小 1、最大 1、std 0 → dt_jitter_ratio = 0
- 时长（时间列，ms 口径）= 75767 → 75.767 s；表头 SampleTime[ms] = 1 → fs = 1000 Hz；导出挂钟（表头 Starttime/Endtime 之差 / 1e7）= 75.767 s（三方互洽）
- 非数值/NaN 单元 0 / 3030720 → overall = 0，最差通道 = 0
- 恒值通道 16 个：f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar
- x_Ltar - x_L：比对 75768 行，不等 70488 行 (0.9303)，std 1.103e-07，mean -7.654e-09，min -5.484e-07，max 4.97e-07，max|d| 5.484e-07，最小非零|d| 1.714e-08
- x_Ttar - x_T：比对 75768 行，不等 64136 行 (0.8465)，std 5.924e-05，mean 1.065e-06，min -0.001654，max 0.003121，max|d| 0.003121，最小非零|d| 2e-07
- v_Ltar - v_L：比对 75768 行，不等 75768 行 (1.0000)，std 0.0006081，mean -6.324e-07，min -0.002883，max 0.002706，max|d| 0.002883，最小非零|d| 2.057e-07
- v_Ttar - v_T：比对 75768 行，不等 74650 行 (0.9852)，std 0.005999，mean -0.0007643，min -0.1703，max 0.233，max|d| 0.233，最小非零|d| 8.833e-07
- f_tar - f_L：比对 75768 行，不等 75768 行 (1.0000)，std 0.239，mean 108.8，min 108，max 109.9，max|d| 109.9，最小非零|d| 108
- f_tar - f_T：比对 75768 行，不等 75768 行 (1.0000)，std 0.2611，mean 100.5，min 91.92，max 112.4，max|d| 112.4，最小非零|d| 91.92
- 动态量抽查：tau_T nuniq=337 [-1502, 1469] std=41.6842；tau_L nuniq=10 [-0.1, -0.01] std=0.0195505；P_T nuniq=12077 [-5.9704e+07, 6.61073e+07] std=2.00097e+06；x_T nuniq=61682 [-0.001524, 1.94999]；x_Ttar nuniq=63768 [1.31e-05, 1.94999]；f_T nuniq=66486 std=0.261056；theta_L nuniq=240 [23.83,28]
- 恒等式复算（vs 5170 现行版 Measurement_Connector_Ch2 源码）：x_diff 与 −(x_L+x_T) 的行级最大残差、v_diff 与 −(v_L+v_T)、f_diff 与 f_T−f_L、tau_T 与 f_Tm、tau_L 与 f_Lm：见正文；tau_T−f_Tm 在本文件 max|d|=[0.0, 0.0]，tau_L−f_Lm max|d|=[1.0083299389002038, 10.083299389002038]

#### dataFile id=id393966  (CDD_2024-07-23_LdaFricIdent_UW_Export_7_id393966.csv)
- 数据行 76008，表头行 11，尾行 0（无 EOF）；时间列首/末 = 0 / 76007，dt 中位 1、最小 1、最大 1、std 0 → dt_jitter_ratio = 0
- 时长（时间列，ms 口径）= 76007 → 76.007 s；表头 SampleTime[ms] = 1 → fs = 1000 Hz；导出挂钟（表头 Starttime/Endtime 之差 / 1e7）= 76.007 s（三方互洽）
- 非数值/NaN 单元 0 / 3040320 → overall = 0，最差通道 = 0
- 恒值通道 16 个：f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar
- x_Ltar - x_L：比对 76008 行，不等 70584 行 (0.9286)，std 1.101e-07，mean -7.939e-09，min -4.456e-07，max 4.97e-07，max|d| 4.97e-07，最小非零|d| 1.714e-08
- x_Ttar - x_T：比对 76008 行，不等 64354 行 (0.8467)，std 5.88e-05，mean 1.107e-06，min -0.001602，max 0.003111，max|d| 0.003111，最小非零|d| 3e-07
- v_Ltar - v_L：比对 76008 行，不等 76008 行 (1.0000)，std 0.0006047，mean -2.637e-06，min -0.002703，max 0.00306，max|d| 0.00306，最小非零|d| 2.057e-07
- v_Ttar - v_T：比对 76008 行，不等 74877 行 (0.9851)，std 0.005988，mean -0.0007823，min -0.1714，max 0.2304，max|d| 0.2304，最小非零|d| 1.117e-06
- f_tar - f_L：比对 76008 行，不等 76008 行 (1.0000)，std 0.2403，mean 108.8，min 107.6，max 109.7，max|d| 109.7，最小非零|d| 107.6
- f_tar - f_T：比对 76008 行，不等 76008 行 (1.0000)，std 0.26，mean 100.4，min 91.94，max 112.4，max|d| 112.4，最小非零|d| 91.94
- 动态量抽查：tau_T nuniq=343 [-1506, 1449] std=42.3142；tau_L nuniq=11 [-0.11, -0.01] std=0.0196208；P_T nuniq=20577 [-5.98921e+07, 6.72618e+07] std=2.00213e+06；x_T nuniq=63980 [-0.00152, 2.17498]；x_Ttar nuniq=64007 [1.31e-05, 2.17498]；f_T nuniq=66395 std=0.259955；theta_L nuniq=232 [23.83,28.2]
- 恒等式复算（vs 5170 现行版 Measurement_Connector_Ch2 源码）：x_diff 与 −(x_L+x_T) 的行级最大残差、v_diff 与 −(v_L+v_T)、f_diff 与 f_T−f_L、tau_T 与 f_Tm、tau_L 与 f_Lm：见正文；tau_T−f_Tm 在本文件 max|d|=[0.0, 0.0]，tau_L−f_Lm max|d|=[1.0083299389002038, 11.091629327902242]

#### dataFile id=id394009  (CDD_2024-07-23_LdaFricIdent_UW_Export_9_id394009.csv)
- 数据行 75938，表头行 11，尾行 0（无 EOF）；时间列首/末 = 0 / 75937，dt 中位 1、最小 1、最大 1、std 0 → dt_jitter_ratio = 0
- 时长（时间列，ms 口径）= 75937 → 75.937 s；表头 SampleTime[ms] = 1 → fs = 1000 Hz；导出挂钟（表头 Starttime/Endtime 之差 / 1e7）= 75.937 s（三方互洽）
- 非数值/NaN 单元 0 / 3037520 → overall = 0，最差通道 = 0
- 恒值通道 16 个：f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar
- x_Ltar - x_L：比对 75938 行，不等 70582 行 (0.9295)，std 1.1e-07，mean -7.986e-09，min -5.313e-07，max 4.799e-07，max|d| 5.313e-07，最小非零|d| 1.714e-08
- x_Ttar - x_T：比对 75938 行，不等 64458 行 (0.8488)，std 5.876e-05，mean 1.052e-06，min -0.001602，max 0.003097，max|d| 0.003097，最小非零|d| 4e-07
- v_Ltar - v_L：比对 75938 行，不等 75938 行 (1.0000)，std 0.0006037，mean 2.526e-08，min -0.002413，max 0.002592，max|d| 0.002592，最小非零|d| 2.057e-07
- v_Ttar - v_T：比对 75938 行，不等 75773 行 (0.9978)，std 0.005903，mean -0.0007253，min -0.1724，max 0.2318，max|d| 0.2318，最小非零|d| 1.717e-06
- f_tar - f_L：比对 75938 行，不等 75938 行 (1.0000)，std 0.2357，mean 108.9，min 107.8，max 110，max|d| 110，最小非零|d| 107.8
- f_tar - f_T：比对 75938 行，不等 75938 行 (1.0000)，std 0.2595，mean 100.5，min 91.94，max 112.4，max|d| 112.4，最小非零|d| 91.94
- 动态量抽查：tau_T nuniq=351 [-1505, 1445] std=44.1359；tau_L nuniq=11 [-0.11, -0.01] std=0.0195769；P_T nuniq=25181 [-5.99935e+07, 6.57247e+07] std=1.97577e+06；x_T nuniq=63905 [-0.001518, 2.34995]；x_Ttar nuniq=63938 [1.31e-05, 2.34996]；f_T nuniq=66300 std=0.259547；theta_L nuniq=236 [23.69,28.03]
- 恒等式复算（vs 5170 现行版 Measurement_Connector_Ch2 源码）：x_diff 与 −(x_L+x_T) 的行级最大残差、v_diff 与 −(v_L+v_T)、f_diff 与 f_T−f_L、tau_T 与 f_Tm、tau_L 与 f_Lm：见正文；tau_T−f_Tm 在本文件 max|d|=[0.0, 0.0]，tau_L−f_Lm max|d|=[1.0083299389002038, 11.091629327902242]

#### dataFile id=id394119  (CDD_2024-07-23_LdaFricIdent_RW_Export_3_id394119.csv)
- 数据行 75840，表头行 11，尾行 0（无 EOF）；时间列首/末 = 0 / 75839，dt 中位 1、最小 1、最大 1、std 0 → dt_jitter_ratio = 0
- 时长（时间列，ms 口径）= 75839 → 75.839 s；表头 SampleTime[ms] = 1 → fs = 1000 Hz；导出挂钟（表头 Starttime/Endtime 之差 / 1e7）= 75.839 s（三方互洽）
- 非数值/NaN 单元 0 / 3033600 → overall = 0，最差通道 = 0
- 恒值通道 16 个：f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar
- x_Ltar - x_L：比对 75840 行，不等 70463 行 (0.9291)，std 1.106e-07，mean -8.294e-09，min -5.142e-07，max 4.799e-07，max|d| 5.142e-07，最小非零|d| 1.714e-08
- x_Ttar - x_T：比对 75840 行，不等 64184 行 (0.8463)，std 3.415e-05，mean 2.247e-07，min -0.001297，max 0.00155，max|d| 0.00155，最小非零|d| 1e-07
- v_Ltar - v_L：比对 75840 行，不等 75840 行 (1.0000)，std 0.0006073，mean -2.505e-06，min -0.002646，max 0.002535，max|d| 0.002646，最小非零|d| 2.057e-07
- v_Ttar - v_T：比对 75840 行，不等 74968 行 (0.9885)，std 0.00542，mean -0.0008269，min -0.1529，max 0.1662，max|d| 0.1662，最小非零|d| 1.433e-06
- f_tar - f_L：比对 75840 行，不等 75840 行 (1.0000)，std 0.7322，mean 108.7，min 106.1，max 110.2，max|d| 110.2，最小非零|d| 106.1
- f_tar - f_T：比对 75840 行，不等 75840 行 (1.0000)，std 0.2672，mean 100.5，min 87.26，max 109，max|d| 109，最小非零|d| 87.26
- 动态量抽查：tau_T nuniq=335 [-1460, 1355] std=40.0774；tau_L nuniq=11 [-0.11, -0.01] std=0.019597；P_T nuniq=7592 [-5.49366e+07, 6.61796e+07] std=2.07915e+06；x_T nuniq=33846 [1.85501, 3.80125]；x_Ttar nuniq=63837 [1.855, 3.79999]；f_T nuniq=65707 std=0.267178；theta_L nuniq=242 [23.78,27.5]
- 恒等式复算（vs 5170 现行版 Measurement_Connector_Ch2 源码）：x_diff 与 −(x_L+x_T) 的行级最大残差、v_diff 与 −(v_L+v_T)、f_diff 与 f_T−f_L、tau_T 与 f_Tm、tau_L 与 f_Lm：见正文；tau_T−f_Tm 在本文件 max|d|=[0.0, 0.0]，tau_L−f_Lm max|d|=[1.0083299389002038, 11.091629327902242]

#### dataFile id=id394169  (CDD_2024-07-23_LdaFricIdent_UW_Export_6_id394169.csv)
- 数据行 75843，表头行 11，尾行 0（无 EOF）；时间列首/末 = 0 / 75842，dt 中位 1、最小 1、最大 1、std 0 → dt_jitter_ratio = 0
- 时长（时间列，ms 口径）= 75842 → 75.842 s；表头 SampleTime[ms] = 1 → fs = 1000 Hz；导出挂钟（表头 Starttime/Endtime 之差 / 1e7）= 75.842 s（三方互洽）
- 非数值/NaN 单元 0 / 3033720 → overall = 0，最差通道 = 0
- 恒值通道 16 个：f_tar, x_Ltar, trig_scope, dir, f_no, x_asco_enc, x_asco_serial, Rate_asco, w_asco_serial, v_asco_enc, v_asco_serial, dx_asco_serial, P_L, x_lsv_enc, v_lsv_enc, a_Ltar
- x_Ltar - x_L：比对 75843 行，不等 70331 行 (0.9273)，std 1.101e-07，mean -7.308e-09，min -4.627e-07，max 4.97e-07，max|d| 4.97e-07，最小非零|d| 1.714e-08
- x_Ttar - x_T：比对 75843 行，不等 64226 行 (0.8468)，std 5.917e-05，mean 1.041e-06，min -0.001656，max 0.003117，max|d| 0.003117，最小非零|d| 1e-07
- v_Ltar - v_L：比对 75843 行，不等 75843 行 (1.0000)，std 0.0006052，mean 3.592e-06，min -0.002471，max 0.002647，max|d| 0.002647，最小非零|d| 2.057e-07
- v_Ttar - v_T：比对 75843 行，不等 74679 行 (0.9847)，std 0.005947，mean -0.000764，min -0.1664，max 0.2341，max|d| 0.2341，最小非零|d| 2.25e-06
- f_tar - f_L：比对 75843 行，不等 75843 行 (1.0000)，std 0.2378，mean 108.8，min 107.4，max 109.8，max|d| 109.8，最小非零|d| 107.4
- f_tar - f_T：比对 75843 行，不等 75843 行 (1.0000)，std 0.2597，mean 100.5，min 92.04，max 112.4，max|d| 112.4，最小非零|d| 92.04
- 动态量抽查：tau_T nuniq=342 [-1501, 1435] std=42.3675；tau_L nuniq=10 [-0.1, -0.01] std=0.0196159；P_T nuniq=18278 [-5.97848e+07, 6.73371e+07] std=2.04037e+06；x_T nuniq=63856 [-0.00152, 2.09998]；x_Ttar nuniq=63843 [1.31e-05, 2.09998]；f_T nuniq=66494 std=0.259682；theta_L nuniq=223 [24.17,27.99]
- 恒等式复算（vs 5170 现行版 Measurement_Connector_Ch2 源码）：x_diff 与 −(x_L+x_T) 的行级最大残差、v_diff 与 −(v_L+v_T)、f_diff 与 f_T−f_L、tau_T 与 f_Tm、tau_L 与 f_Lm：见正文；tau_T−f_Tm 在本文件 max|d|=[0.0, 0.0]，tau_L−f_Lm max|d|=[1.0083299389002038, 10.083299389002038]

---

## 7. 最关键两条：逐行指令≠反馈 + 电流/力矩类通道

### 7.1 位置/速度 指令 vs 反馈（逐行实测，全量行，不是抽样）

| 逐行差（全量行，非抽样） | 指标 | 394141 | 393961 | 393966 | 394009 | 394119 | 394169 |
|---|---|---|---|---|---|---|---|
| `x_Ttar - x_T` 位置 T 侧（tar=设定 / 无 tar=反馈） | 不等行数 / 全行数（比例） | 64477/75868 (0.8499) | 64136/75768 (0.8465) | 64354/76008 (0.8467) | 64458/75938 (0.8488) | 64184/75840 (0.8463) | 64226/75843 (0.8468) |
| `x_Ttar - x_T` 位置 T 侧（tar=设定 / 无 tar=反馈） | std | 3.441e-05 | 5.924e-05 | 5.88e-05 | 5.876e-05 | 3.415e-05 | 5.917e-05 |
| `x_Ttar - x_T` 位置 T 侧（tar=设定 / 无 tar=反馈） | max\|d\| | 0.001584 | 0.003121 | 0.003111 | 0.003097 | 0.00155 | 0.003117 |
| `x_Ttar - x_T` 位置 T 侧（tar=设定 / 无 tar=反馈） | 最小非零 \|d\| | 2e-07 | 2e-07 | 3e-07 | 4e-07 | 1e-07 | 1e-07 |
| `x_Ltar - x_L` 位置 L 侧（`x_Ltar` 实测恒值） | 不等行数 / 全行数（比例） | 70527/75868 (0.9296) | 70488/75768 (0.9303) | 70584/76008 (0.9286) | 70582/75938 (0.9295) | 70463/75840 (0.9291) | 70331/75843 (0.9273) |
| `x_Ltar - x_L` 位置 L 侧（`x_Ltar` 实测恒值） | std | 1.107e-07 | 1.103e-07 | 1.101e-07 | 1.1e-07 | 1.106e-07 | 1.101e-07 |
| `x_Ltar - x_L` 位置 L 侧（`x_Ltar` 实测恒值） | max\|d\| | 5.313e-07 | 5.484e-07 | 4.97e-07 | 5.313e-07 | 5.142e-07 | 4.97e-07 |
| `x_Ltar - x_L` 位置 L 侧（`x_Ltar` 实测恒值） | 最小非零 \|d\| | 1.714e-08 | 1.714e-08 | 1.714e-08 | 1.714e-08 | 1.714e-08 | 1.714e-08 |
| `v_Ttar - v_T` 速度 T 侧 | 不等行数 / 全行数（比例） | 75868/75868 (1.0000) | 74650/75768 (0.9852) | 74877/76008 (0.9851) | 75773/75938 (0.9978) | 74968/75840 (0.9885) | 74679/75843 (0.9847) |
| `v_Ttar - v_T` 速度 T 侧 | std | 0.005934 | 0.005999 | 0.005988 | 0.005903 | 0.00542 | 0.005947 |
| `v_Ttar - v_T` 速度 T 侧 | max\|d\| | 0.1676 | 0.233 | 0.2304 | 0.2318 | 0.1662 | 0.2341 |
| `v_Ttar - v_T` 速度 T 侧 | 最小非零 \|d\| | 2e-06 | 8.833e-07 | 1.117e-06 | 1.717e-06 | 1.433e-06 | 2.25e-06 |
| `v_Ltar - v_L` 速度 L 侧 | 不等行数 / 全行数（比例） | 75868/75868 (1.0000) | 75768/75768 (1.0000) | 76008/76008 (1.0000) | 75938/75938 (1.0000) | 75840/75840 (1.0000) | 75843/75843 (1.0000) |
| `v_Ltar - v_L` 速度 L 侧 | std | 0.000611 | 0.0006081 | 0.0006047 | 0.0006037 | 0.0006073 | 0.0006052 |
| `v_Ltar - v_L` 速度 L 侧 | max\|d\| | 0.00253 | 0.002883 | 0.00306 | 0.002592 | 0.002646 | 0.002647 |
| `v_Ltar - v_L` 速度 L 侧 | 最小非零 \|d\| | 2.057e-07 | 2.057e-07 | 2.057e-07 | 2.057e-07 | 2.057e-07 | 2.057e-07 |
| `f_tar - f_L` 力 L 侧（`f_tar` 实测恒 100） | 不等行数 / 全行数（比例） | 75868/75868 (1.0000) | 75768/75768 (1.0000) | 76008/76008 (1.0000) | 75938/75938 (1.0000) | 75840/75840 (1.0000) | 75843/75843 (1.0000) |
| `f_tar - f_L` 力 L 侧（`f_tar` 实测恒 100） | std | 0.8031 | 0.239 | 0.2403 | 0.2357 | 0.7322 | 0.2378 |
| `f_tar - f_L` 力 L 侧（`f_tar` 实测恒 100） | max\|d\| | 110 | 109.9 | 109.7 | 110 | 110.2 | 109.8 |
| `f_tar - f_L` 力 L 侧（`f_tar` 实测恒 100） | 最小非零 \|d\| | 106 | 108 | 107.6 | 107.8 | 106.1 | 107.4 |
| `f_tar - f_T` 力 T 侧（同上） | 不等行数 / 全行数（比例） | 75868/75868 (1.0000) | 75768/75768 (1.0000) | 76008/76008 (1.0000) | 75938/75938 (1.0000) | 75840/75840 (1.0000) | 75843/75843 (1.0000) |
| `f_tar - f_T` 力 T 侧（同上） | std | 0.2659 | 0.2611 | 0.26 | 0.2595 | 0.2672 | 0.2597 |
| `f_tar - f_T` 力 T 侧（同上） | max\|d\| | 109 | 112.4 | 112.4 | 112.4 | 109 | 112.4 |
| `f_tar - f_T` 力 T 侧（同上） | 最小非零 \|d\| | 87.35 | 91.92 | 91.94 | 91.94 | 87.26 | 92.04 |

实测要点：

- **`x_Ttar` ≠ `x_T`（动态位置段）**：不等行占 84.6–85.0%（64,136…64,477 / 75,768…76,008 行），std 3.415e-05…5.924e-05，max|d| 1.550e-03…3.121e-03；
  最小非零 |d| 实测 1.0e-07…4.0e-07（= 打印量化步长量级，但绝大多数行的差远大于它）→ 差异不是打印截断，是真实的设定/反馈两条独立数值。
  位置本身的动态幅度（实测范围）：`x_T` 在各样本走完 ~2.0 m（如 id393966 1.3e-05…2.174976 m），`x_Ttar` 覆盖同一区间但曲线不同；
  `v_T` 达 ±1.13…±1.19 m/s、`v_Ttar` ±1.04…±1.10 m/s。
- 逐样本运动/静止分段（全量行实测，阈值 `|v_Ttar| > 0.05`）：

| dataFile id | 全量行 | 运动段行数（fe std / max\|d\| / 非零比） | 静止段行数（fe std / max\|d\| / 非零比） | max\|`x_diff`+(`x_L`+`x_T`)\| | max\|`v_diff`+(`v_L`+`v_T`)\| | max\|`f_diff`−(`f_T`−`f_L`)\| | `x_Ltar` 唯一值 | `f_tar` 唯一值 |
|---|---|---|---|---|---|---|---|---|
| 394141 | 75868 | 3858 (std 0.00014, max 0.001584, 非零 0.9419) | 72010 (std 1.399e-05, max 0.001306, 非零 0.8449) | 4.44e-16 | 1.39e-17 | 0 | 1 | 1 |
| 393961 | 75768 | 3758 (std 0.0002576, max 0.003121, 非零 0.9577) | 72010 (std 1.443e-05, max 0.001479, 非零 0.8407) | 1.11e-16 | 1.11e-16 | 0 | 1 | 1 |
| 393966 | 76008 | 3998 (std 0.0002481, max 0.003111, 非零 0.9550) | 72010 (std 1.446e-05, max 0.001477, 非零 0.8407) | 2.22e-16 | 1.39e-17 | 0 | 1 | 1 |
| 394009 | 75938 | 3928 (std 0.0002496, max 0.003097, 非零 0.9580) | 72010 (std 1.487e-05, max 0.001475, 非零 0.8429) | 2.22e-16 | 1.11e-16 | 0 | 1 | 1 |
| 394119 | 75840 | 3830 (std 0.0001392, max 0.00155, 非零 0.9426) | 72010 (std 1.398e-05, max 0.001326, 非零 0.8412) | 4.44e-16 | 8.67e-19 | 0 | 1 | 1 |
| 394169 | 75843 | 3833 (std 0.0002549, max 0.003117, 非零 0.9554) | 72010 (std 1.447e-05, max 0.001477, 非零 0.8410) | 2.22e-16 | 1.11e-16 | 0 | 1 | 1 |

  实测：每份的静止段都恰好 72,010 行（72.010 s，同一保持时长），运动段 3,758…3,998 行；
  运动段 fe 明显更大（std 1.392e-04…2.576e-04、max|d| 1.550e-03…3.121e-03、非零比 94.2–95.8%），
  静止段仍有 84.1–84.3% 的行不相等（std 1.398e-05…1.487e-05）→ 两段都可算 fe，动态 fe 取运动段。
- **`x_Ltar` 恒值（本组样本全程位置保持）**：6/6 样本 `x_Ltar` 唯一值数 = 1（恒 −1.4139912076248002），而 `x_L` 有 49–52 个唯一值 →
  不等行仍占 92.7–93.0%，但幅度只有 std 1.0996e-07…1.1067e-07、max|d| 4.970e-07…5.484e-07；
  `x_L` 的最小量化步长实测 1.71388e-08 → **L 侧的 fe 只有编码器量化噪声量级（~0.5 µm）**，
  是「零速位置保持」的静态误差，不是动态跟随误差段。要 fe 的动态段只能用 T 侧。
- **速度对**：`v_Ttar−v_T` 不等行 98.5–100%，std 5.420e-03…5.999e-03，max|d| 0.1662…0.2341；
  `v_Ltar−v_L` 不等行 **100%**，std 6.037e-04…6.110e-04，max|d| 2.530e-03…3.060e-03。
- 量化形态与「指令/反馈」之分互相印证：`*_tar` 步长细（`x_Ttar` 1e-07）且平滑、无反馈抖动；反馈 `x_T` 步长粗（2e-06）并带 ± 抖动。
- 恒等式复算（**6/6 样本全量行**实测，用于证明解析对齐正确 + 通道语义自洽；见上表后三列）：
  `x_diff = −(x_L + x_T)` 最大残差 1.11e-16…4.44e-16；`v_diff = −(v_L + v_T)` 最大残差 8.67e-19…1.11e-16；
  `f_diff = f_T − f_L` 最大残差 0；`tau_T ≡ f_Tm` 残差 0（6/6，见 §7.2）。
  → 所以 `x_diff/v_diff` 是「两侧绳长/速度合成量」，**不是**跟随误差列；本项目要用的 fe 必须由 `*_tar − *` 自行计算。
- `f_tar` 恒 100（6/6 样本唯一值数 = 1），而 `f_L` 实测 −10.2…−6.0、`f_T` 实测 −12.41…+12.74（`f_T` 有 65,512…66,486 个唯一值，是真动态）；
  逐行差 `f_tar − f_L` 落在 106.0…110.2、`f_tar − f_T` 落在 87.26…112.41 → **不能**把 `f_tar − f_*` 当成可用的力跟随误差，`f_tar` 是恒定的设定值列。
  另：`f_kistler1/2`（Kistler 力传感器，实测 ±0.9 kN 内、736…767 唯一值）是第三方测量通道，可作力的独立复核源。

> **2026-10-21 本仓复算更正（§7.1）**：主表 **180 个数字单元格复算不一致 0 个**；运动/静止分段表 6 行（阈值 `|v_Ttar|>0.05`、静止段 72,010 行、运动段 3,758…3,998 行及 std/max/非零比）复算全部成立；`x_L` 49–52、`x_Ltar` 恒 −1.4139912076248002、`f_tar` 恒 100.0、`f_L` −10.2…−6.0、`f_T` −12.41…+12.74 复算成立。四处需标注/更正：
> ① 「`f_T` 有 65,512…66,486 个唯一值」复算区间 **65512…66494**（上限出自 id394169，本文 §6 抽查行自己就印了 66494）⟹ 原句**不成立**；
> ② 「`f_kistler1/2` …736…767 唯一值」按**两通道合计**口径复算区间 **734…767** ⟹ 合计口径**不成立**；按 `f_kistler1` 单通道口径复算 736…767 成立 ⟹ 原句是单通道口径但写成了「f_kistler1/2」，有歧义；±0.9 kN 内复算 max|·| = 0.8752 成立；
> ③ `x_diff = −(x_L+x_T)` / `v_diff = −(v_L+v_T)` 的残差（1.11e-16…4.44e-16 / 8.67e-19…1.11e-16）**在 (a+b)+c 结合顺序下 6/6 复现**（改 `a+(b+c)` 顺序残差更小），原句未标注结合顺序——恒等式本身（含 `f_diff` 残差恰 0、`tau_T ≡ f_Tm`）复算成立；
> ④ 归属标注：L446「`x_T` …走完 ~2.0 m（如 id393966 1.3e-05…2.174976 m）」复算显示下界 1.31e-05 是 `x_Ttar` 的下界（`x_T` 复算下界 −0.00152）、上界 2.174976 是 `x_T` 的上界（`x_Ttar` 为 2.1749787）⟹ 该「区间」是两通道端点拼接；~2.0 m 量级结论不受影响，归属写法留待主线程裁决。
> 复算命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）；本轮打印值为证，原报告数字属第三方会话产物（`verified_by ≠ self`，`public-doc`，不计入 k）。

### 7.2 电流 / 力矩 / 驱动量类通道盘点

名字普查（不采信名字本身，先列全）：

| 同类文件数 | 通道数 | 通道名里含 current/iq/duty/tau/torque/force/power 的名字 | 代表文件 |
|---|---|---|---|
| 26 | 55 | tau_L, tau_Ladd, tau_T, tau_Tadd | 394737=LIROS_D-Pro/2025-03-06_PreloadedLuGreFrictionIdent/Data/WC80/Export 1.csv 等 |
| 18 | 35 | tau_L, tau_T | 394124=Winch_Testbed/2023-12-06_LuGre_PeakSignal_AccMin/W7/Export 4.csv 等 |
| 1 | 32 | dForceSensorNo, dForce_colinear, dForce_diff, dForce_load, dForce_orthogonal, dForce_tar, dForce_test, dPower_load, dPower_test, dTorque_load, dTorque_test | 394133=Winch_Testbed/2023-10-12_ViscousFrictionIdent/Data/W7/Unwind/Export 17.csv |

- 全数据集 68（CDD）+ 45（各试验目录最大 CSV）实测通道名里，**含 `Current` / `I_q` / `cur_q` / `Duty` 的名字：0 个**。
- 驱动侧（放大器出来的量）在 CDD 变体里只有：`tau_L`, `tau_T`, `P_L`, `P_T`（+ 2025 版多出 `tau_Tadd`, `tau_Ladd`, `v_Tadd`, `v_Ladd`，见上表；Winch_Testbed/2023 变体改名 `dTorque_load/dTorque_test`）。
- 逐样本实测：

| dataFile id | `tau_T` 唯一值 | `tau_T` 范围 | `tau_T` std | `tau_T` 变值次数 | max\|`f_Tm`−`tau_T`\| | `tau_L` 唯一值 | `tau_L` 范围 | `tau_L` std | `tau_L` 变值次数 | `f_Lm`/`tau_L` 比值（每份内唯一值数=1） | max\|`f_Lm`−比值×`tau_L`\| | `P_T` 唯一值 | `P_T` 范围 | `P_T` std |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 394141 | 336 | [-1426, 1363] | 39.4 | 67117 | 0 | 10 | [-0.1, -0.01] | 0.0196 | 65599 | 101.83299 | 2.04e-12 | 11831 | [-5.528e+07, 6.592e+07] | 2.099e+06 |
| 393961 | 337 | [-1502, 1469] | 41.7 | 66853 | 0 | 10 | [-0.1, -0.01] | 0.0196 | 65692 | 101.83299 | 2.04e-12 | 12077 | [-5.97e+07, 6.611e+07] | 2.001e+06 |
| 393966 | 343 | [-1506, 1449] | 42.3 | 67489 | 0 | 11 | [-0.11, -0.01] | 0.0196 | 65993 | 101.83299 | 2.24e-12 | 20577 | [-5.989e+07, 6.726e+07] | 2.002e+06 |
| 394009 | 351 | [-1505, 1445] | 44.1 | 67672 | 0 | 11 | [-0.11, -0.01] | 0.0196 | 65942 | 101.83299 | 2.24e-12 | 25181 | [-5.999e+07, 6.572e+07] | 1.976e+06 |
| 394119 | 335 | [-1460, 1355] | 40.1 | 67058 | 0 | 11 | [-0.11, -0.01] | 0.0196 | 65758 | 101.83299 | 2.24e-12 | 7592 | [-5.494e+07, 6.618e+07] | 2.079e+06 |
| 394169 | 342 | [-1501, 1435] | 42.4 | 67139 | 0 | 10 | [-0.1, -0.01] | 0.0196 | 65781 | 101.83299 | 2.04e-12 | 18278 | [-5.978e+07, 6.734e+07] | 2.04e+06 |

  实测事实：`tau_T` 与 `f_Tm` **逐行完全相同（6/6 样本 max|d| = 0）**，是同一信号的两份拷贝；
  `tau_L` 与 `f_Lm` 不恒等，但满足 `f_Lm = 101.83299389 × tau_L`——实测每份文件内该比值只有 **1 个唯一值**（75,768…76,008 行全对），
  残差 max ≤ 2.242e-12（浮点打印级）；
  `tau_T` 全程整数、335–351 个唯一值、范围约 [−1506, 1469]、std 39.4–44.1、变值 66,853…67,672 次 → **有真实动态**；
  `tau_L` 只有 10–11 个唯一值、范围 −0.11…−0.01、步长 0.01、std 0.0196 → 虽然逐行也在抖（65,599…65,993 次变值），
  但幅度全在 ±0.1 的量化噪声里，**没有可用动态**（L 侧本段是零速保持，力矩实际值≈常数）。

> **2026-10-21 本仓复算更正（§7.2 逐样本表与实测事实）**：6 行的 `tau_T`/`tau_L`/`P_T` 各列（唯一值数、范围、std、变值次数）、`max|f_Tm−tau_T| = 0`（复算 6/6 逐行残差最大 **0.0**，成立）均命中；两处需更正口径：
> ① 「`f_Lm`/`tau_L` 比值（每份内唯一值数=1）」：复算**原始浮点比值每份有 2 个唯一值**（101.83299389002036 / 101.83299389002038，尾一位之差），四舍五入到 8 位小数后为 1 ⟹ 「1 个唯一值」仅在打印/舍入口径下成立，原句未标注口径；
> ② 「残差 max ≤ 2.242e-12」：用**全精度常数 k=101.83299389** 复算 max|f_Lm−k·tau_L| = **2.037e-12…2.242e-12** ⟹ 成立；用 §7.2 表格里印的 **k=101.83299** 复算得 **3.89002e-07…4.27902e-07** ⟹ 该口径下**不成立** ⟹ `f_Lm = 101.83299389×tau_L` 应读作**近似比例关系**（残差量级对所取常数的打印位数敏感），**不是**行级恒等式；复算不符不等于证伪物理关系。
> 全量口径降级：「68+45 份通道名电流 0 命中」的普查表（26/18/1 行，代表件 394737/394124/394133）与 45 目录最大 CSV 均未落盘 ⟹ **无法复算**（在仓 6 份上「Current/I_q/cur_q/Duty 0 命中」复算成立，驱动侧通道名复算为 `P_L, P_T, tau_L, tau_T`）。
> 复算命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）；本轮打印值为证，原报告数字属第三方会话产物（`verified_by ≠ self`，`public-doc`，不计入 k）。

- 语义来源（**外部证据，不是名字推断**；均为 5171 之外/之内的原文抄录，属「页面自述」类）：
  1. 本数据集 `CableDirectDrive_Testbed/2024-07-23_LdaFricIdent/Settings/CableActuatorTestRig.xml`（id 394085，2468 B，本会话已读原文）：
     声明 drive 7/8 = Bosch Rexroth MSK061C-0600-NN（卷扬，gear 5.0 / 1.0，r_drum 0.0491）、drive 9 = **LDA** Bosch Rexroth ML3P11-DNBQN-BANNN-NN（直线电机，force_max 600），
     控制器 `velocity-winch / torque-winch / velocity-lda`（PID kff/kp/ki/kd 原文数值）。
  2. 兄弟数据集 **DARUS-5170**（同作者台架控制软件）`Measurement_Connector_Ch2.TcPOU`（id 392319）原文：
     ```
     // MOTOR  Position
     x_Ltar := -DINT_TO_LREAL(Measurement_IOs.Drive5_AT_LageSollwert)/10000000;
     x_L    := -DINT_TO_LREAL(Measurement_IOs.Drive5_AT_LageIstwert)/10000000;
     x_Ttar := -DINT_TO_LREAL(Measurement_IOs.Drive1_AT1_LageSollwert)/10000000;
     x_T    := -DINT_TO_LREAL(Measurement_IOs.Drive1_AT1_LageIstwert)/10000000;
     x_diff := -(x_L + x_T); // in [m]
     // Toruque in [Nm]            <-- 原文拼写即 Toruque
     tau_T := INT_TO_LREAL(Measurement_IOs.Drive1_AT1_DrehmomentIstwert)/1;
     tau_L := INT_TO_LREAL(Measurement_IOs.Drive5_AT_KraftIstwert)/1;
     // Motorforce in [N]
     f_Lm := tau_L;   f_Tm := tau_T;
     // Power in [W]
     P_T := DINT_TO_LREAL(Measurement_IOs.Drive1_AT1_Motorleistung);
     ```
     配套 `Measurement_IOs.TcGVL`（id 392290）声明 `Drive1_AT1_DrehmomentIstwert : INT`、`Drive5_AT_KraftIstwert : INT`、
     `Drive*_AT1_LageSollwert / LageIstwert : DINT`；`Measurement_Ch2.tcscopex`（id 392278）里每通道的
     `SymbolName = Measurement_Connector_Ch2.<名>`、`BaseSampleTime = 10000`（=10 µs→显示 1 ms 抽稀需按现行版复核）、
     `tau_T` 的 `<Comment>Torque</Comment>`、`x_T` 的注释 `MOTOR\n Position`、`RawUnit/Name = None`（即 CSV 里无单位）。
  3. `DB_LOGGER_Data.TcDUT`（id 392409）原文 doc-comment：`tau_m` = "Active motor torque in Nm"，位置字段 /m、速度 /(m/s)。

> **2026-10-21 本仓复算（§7.2 语义来源分级）**：来源 1 的每个字段都在仓内实体 `data/incoming/394085_CableActuatorTestRig.xml`（2,468 B，md5 `67eeb6e33abacfaa7572b6b5ac82d812`，与 listing 逐位一致）上复算**全部成立**：drive 7/8 = MSK061C-0600-NN（gear 5.0/1.0、r_drum 0.0491、force_max 32）、drive 9 = ML3P11-DNBQN-BANNN-NN（gear 1.0、r_drum 0.0、force_max 600）、控制器 `velocity-winch`(kff 0.0/kp 0.0005/ki 0.0005/kd 0.0001)、`torque-winch`(1.25/0.005/0.05/0.0001)、`velocity-lda`(0.0/0.0005/0.01/0.5)、测量设备 ASCOspeed 5500 / LSV 2100-30、INCFactor 50——本条**有仓内重跑产物**。来源 2/3（5170 的 TcPOU 392319 / tcscopex 392278 / TcGVL 392290 / TcDUT 392409 原文行）件在兄弟数据集、仓内未落盘 ⟹ **无法复算**，引用只能标 `public-doc`（同作者软件源码文本，非本仓实测）。命令 `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`）。

- **据此的角色判定（带明确告警）**：
  - `*_tar` = 驱动轴 **Sollwert（设定）**，同名无 `_tar` = **Istwert（实测反馈）** —— 这是闭环位置控制记录，fe 可算，与 3600 的「逐行相等」本质不同。
  - `tau_T` / `tau_L` 取的是 **Istwert（实际值）**，即驱动器侧的扭矩/力实际值（德文 Drehmoment=扭矩、Kraft=力，`INT` 原始计数、源码 `/1` 未做换算），
    所以它是「驱动侧测量量」，**不是设定量**；但它是**力矩/力**而非相电流，量化只有 1 个计数（CDD 里 `tau_T` 步长 1.0、`tau_L` 步长 0.01）。
  - 告警 A（版本漂移）：现行 5170 源码写 `f_Lm := tau_L`（恒等），而 CDD 实测是 `f_Lm = 101.83299389×tau_L`；
    且 5170 现行 `tcscopex` 通道集（36 个，含 `f_Tloss/x_slip/w_mech/p_mech/v_Ttar2`）与 CDD CSV 的 40 通道集**不一致**。
    → 2024-07-23 录制所用软件版本 ≢ 已发布的 5170 现行版，上述单位（m / m/s / Nm / W）只能作为**参考**，不能写成 CDD 的已证实单位。
  - 告警 B（单位与量级自相矛盾）：实测 `P_T` 落在 [−5.52773e+07, 6.59237e+07]，而源码注释称 `[W]` —— 台架电机不可能几十 MW，
    说明 `P_T` 也是未换算的原始计数（或单位另有定义）。名字/注释与量级冲突时，以「单位未证实」处理。
  - 结论口径：CDD 里的**电流类通道 = 无**；**力矩类（驱动侧实际值）通道 = 有，且带动态**（`tau_T`；`tau_L` 在本组 6 份里近似静止）。
    按 KB2 §5.1 硬拒 6「三类角色不能全缺」是满足的（位置指令+反馈+驱动侧力矩都在），
    但按 §5.2 / 项目现有「无 `cur_q` 则频域、共振类判据软降级」的既有约定，**仍须保持软降级**，不得写成「已有电流通道」。

---

## 8. 结论

1. **5171 的 CDD 目录确实可用（fe 可算）**：6/6 样本六条硬拒全 PASS，`x_Ttar − x_T` 在 84.6–85.0% 的行上不相等（std 3.4e-05…5.9e-05，max 1.55e-03…3.12e-03），
   `v_*tar − v_*` 达 100% 不等；`x_Ltar` 全程恒值，L 侧 fe 仅 1e-07 量级（编码器量化级），**动态 fe 必须用 T 侧**。
2. **电流类通道：没有**（全 68+45 采样 0 命中 Current/I_q/Duty 命名）。**力矩类驱动侧实际值：有**（`tau_T` 与 `f_Tm` 逐行恒等、335–351 个整数值、std 39.4–44.1 → 动态显著；`tau_L` 与 `f_Lm` 成固定比 101.83299389，但只有 10–11 个值、全在 ±0.1 内 → 本组样本里量化噪声级，无有效动态）。
   → 「fe + 电流」的严格双条件在 5171 CDD 里**不成立**；成立的是「fe + 力矩（扭矩/力实际值）」。
3. **最强一份（本会话实测）**：`dataFile id=394009`（UW / Export 9.csv，md5 `805b0659e5e5246ceb580aea466d3606`）
   —— 75,938 行、1000 Hz、75.937 s、dt_jitter_ratio 0、NaN 0、24 通道动态；
   `x_Ttar−x_T` 不等 64,458/75,938（0.8488）、std 5.876e-05、max|d| 3.097e-03；`v_Ttar−v_T` 不等 75,773 行、max|d| 0.2318；
   `tau_T` 351 个唯一整数值、[−1505, 1445]、std 44.1（`f_Tm` 与之逐行相同）。
   字节最大的一份是 `id=394141`（RW / Export 5），fe max|d| 1.584e-03、`tau_T` std 39.4；
   要做 RW/UW 配对（摩擦方向性）用 `394141 + 393961`（同为 Export 5，进给段相同、绕向相反）。
4. **接入建议**：CDD 可用样本按「闭环位置控制 + 力矩实际值」接入，`cur_q` 缺口维持软降级；
   单位（m、m/s、Nm）目前只有同作者源码注释支撑、且存在版本漂移证据 → 接入卡里应写「单位由兄弟数据集 5170 现行版源码注释给出，未在本数据集内登记」。
5. 若要更大 fe 幅度/更全传感器（2025 版 55 通道含 `tau_*add` 前馈力矩、`f_lugre/f_stribeck/f_Tobs` 等），
   候选在 `LIROS_D-Pro` / `Trowis_*` 的 `*SlipIdent / *CompensationValid` 目录（§2.1 表 + §7.2 普查表），本次未下载（>300 MB 预算外的定向核验可另开一轮）。

---

## 9. 交付物与 sidecar

- 样本（6，均 official-artifact）：`data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_*.csv`
- sidecar（6，模板 `data/PROVENANCE-TEMPLATE.md`）：同名 + `.source.txt`，
  `upstream_id` = DaRUS `dataFile id`，`verified_against` = 本会话现场 GET `api/datasets/:persistentId/?persistentId=doi:10.18419/DARUS-5171` 的 listing 并 `md5sum` 逐字节比对，`verified_by: self`。
- 复核脚本：`%LOCALAPPDATA%\Temp\d5171\{analyze.py, verify.py, ratio.py, ident.py, survey.py, mktables.py, mksamples.py, survey_other.py, build_report.py}`（未放入项目）。
  中间产物：`ds5171.json`（现场 listing 原文 2,616,228 B）、`survey.json`（68 份 CDD 表头）、`survey_other.json`（45 目录最大 CSV 表头）、
  `analyze.json` / `ident.json` / `ratio.json`（全部实测数值，本报告的数字即由此渲染，非手抄）。

> **2026-10-21 本仓复算更正（§9）**：本地样本 6/6 复算成立（字节数与 md5 对 listing 6/6 全等，合计 263,184,242 B）；
> 「sidecar（6，同名 + `.source.txt`）」在仓里复算 **0 份** ⟹ **不成立**——sidecar 若未随样落盘，本条交付物在仓内无实体凭证，按检查 27 降为未核验；
> 复核脚本与中间 json 在仓里复算同为 0 份 ⟹ 原句「全部脚本落在 `%LOCALAPPDATA%\Temp\d5171`，项目内没有新增 `.py`」复算**成立**（也即：本节数字原本全部缺仓内重跑产物）；
> listing 缺口的代偿件：`data/incoming/daRUS5171_listing_2026-10-20.json`（2,616,228 B，md5 与 `data/raw/darus5171.json` 同为 `9a75442677ab36ffe1aab4fb44c86c17`），
> 本报告全部 listing 派生断言自此可在仓内重跑——**产物即** `PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`（快照 `build/probe_5171.out`；见 §0 复算补记）。
