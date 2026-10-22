# 独立核对存证（2026-10-20 · 本会话自行执行）

对象：另一会话交付的《波形来源存证 sidecar 27 份》报告与两个 zip。
本文件只登记**本会话亲自跑出来的结果**；对方会话的自述对本仓库仍是
`public-doc`（A-89：核对主体不可转借），凡此处未列出的断言一律维持"未由我方核实"。

复现命令均在 Git Bash 下执行，输出原样粘贴，不做美化。

## 一、交付完整性（本地可查）

| 断言 | 本会话实测 | 结论 |
|---|---|---|
| "写了 27 份 `.source.txt`" | `find data/sidecar_in/sidecar27 -name '*.source.txt' \| wc -l` = **27**（9 DaRUS + 6 .mat + 6 派生 CSV + 4 仪器样例 + 2 zip） | 数量相符 |
| 27 份 sidecar 与我方安装的副本一致 | 25 份与 `data/raw`、`data/staging`、`data/staging/原始mat` 逐字节 `cmp` 全部 SAME；2 份目标 zip 未安装（目标在 `<本机下载目录>`） | 交付未被事后改动 |
| 两个 zip 存在 | `波形来源存证sidecar_27份.zip` md5 `9ed064cdc39c5d9c4ba2bb752ce7dfc3`；`DaRUS原始文件_含sidecar.zip` md5 `7ea1736f01f1d61c2aed41885819c128` | 已记录（无外部对照值，仅自证） |

## 二、外部来源：本会话亲自重新抓取并比对字节

| 样本 | 上游 | 本会话独立核对方式 | 结果 |
|---|---|---|---|
| `示波器波形_普源Rigol…csv`（原名 RigolDS0.csv） | `cdn.jsdelivr.net/gh/Chutian-Wang/cswave@main/example_csv/` | curl 重下 + `md5sum` | **aa3362d39952dc48f505615359776ca6 双向一致** |
| `参数分析仪波形_PMU_1t1r_CVSV…csv`（原名 1t1r_set_read_0P1V.csv） | 同上 | curl 重下 + `md5sum` | **402d84bcdff08a61eae1341446a0dab4 双向一致** |
| `示波器波形_泰克…csv`（原名 Test Samples/TEK0003.CSV） | codeload `admk/Tektronix-Waveform-Converter` master tarball，解包后取该文件 | `md5sum` 全仓 TEK*.CSV 对比 | **55faacd40232eb995b12553c1ce46fea 与 TEK0003.CSV 一致**（同目录另有 TEK0000/1/2，md5 各不相同） |
| `示波器波形_SEFRAM_5062DS…csv`（原名 inductor/DS0001.CSV） | codeload `s-leroux/SEFRAM-5062DC-CSV` master tarball | 同上 | **bfc57ef042a7096ab69cf4a95a30a8e7 与 DS0001.CSV 一致** |
| 许可证：cswave = MIT；另两仓"未声明 LICENSE" | GitHub REST | `GET /repos/Chutian-Wang/cswave` → `license.spdx_id = MIT`；`/search/repositories` → `admk/Tektronix-Waveform-Converter` **license: null**；`/repos/s-leroux/SEFRAM-5062DC-CSV` → **license: null**，pushed_at 2012-05-22 | 三条全部与 sidecar 相符 |

⚠️ 踩坑记录：直接 `GET /repos/admk/Tektronix-Waveform-Converter` 返回的是
**rate limit / 伪 404**，不是仓库不存在。判"某 URL 查无此物"之前必须换一条路径复验。

## 三、DaRUS：对出版方 API 现场取证

`GET https://darus.uni-stuttgart.de/api/datasets/:persistentId/?persistentId=doi:10.18419/DARUS-3600`
→ status OK，datasetId 240277，**393 个文件**；`…DARUS-5171` → **3488 个文件**。

| 断言 | 本会话实测（现场 API，非本地 json） | 结论 |
|---|---|---|
| Export10 来自 DARUS-3600（对方自行纠偏：不是 5171） | 3600 内 dataFile **244531** = `Export 10.csv`，md5 `8cba13df…dadb`，filesize 9,175,989，directoryLabel `Data/Torque_based/WF125_F120000/Rewind`；本地文件 `md5sum` **等于该值**；5171 中该 md5 **0 命中** | 升格为 **official-artifact + 本会话字节级核实** |
| DD_head.csv "查无此文件"（对方记「来源未登记」） | 本地 `md5sum` = `995d0d916f872520025a1d57e685ab9f`，在 3600 与 5171 的现场 listing 中 **均 0 命中**；5171 中 filesize=400,001 的文件 **0 个** | 「来源未登记」写对了，**不得**改成"疑为 DaRUS 某文件截断" |
| 文件名是否可作标识 | 3600 内名为 `Export 10.csv` 的文件有 **18 个**，md5 各不相同（WF70/125/180 × F30000/120000/300000 × Rewind/Unwind）；5171 内另有 6 个同名文件 | **仅凭文件名无法定位，dataFile id + md5 是硬性字段**（已写入模板） |
| 目录即试验参数 | 3600：`Torque_based` 193 / `Velocity_based` 191 个文件 + `Settings`、`Cablerobot_profile`；5171 出现 `Winch_Testbed/2023-10-12_ViscousFrictionIdent`、`CableDirectDrive_Testbed/2024-07-23_LdaFricIdent` | 控制模式/试验日期/试验名可原样登记为 C6 机器与事件上下文；**WF/F 的含义未证实，只登记字符串** |

## 四、ScienceDB（电机位置公开数据集）

| 断言 | 本会话实测 | 结论 |
|---|---|---|
| DOI 10.57760/sciencedb.04148 | `https://doi.org/10.57760/sciencedb.04148` → 302 跳到 `www.scidb.cn/detail?dataSetId=7e95fb54…` | DOI 真实、非编造 |
| 标题/作者/单位/许可/发布日 | 页面元数据：*Raw data of motor position in several cases*；Huayuan Huang, Hongtao Pan, Yong Cheng；Institute of Plasma Physics, Hefei Institutes of Physical Science, USTC；Science Data Bank；**CC BY 4.0**；2022-10-24 | 五条全部与 sidecar 相符 |
| 数据集描述原文 | 页面原文：*"This dataset contains both the point-to-point trajectory and periodic trajectory of two different robot joints under three controllers."* 关键词 periodic trajectory / Point-to-point trajectory / position error / robot | sidecar 引文逐字相符 |
| **变量语义缺口** | 页面**不含**任何采样率、传感器、控制器型号、逐列单位说明 | 缺口由**出版方侧证据**证实：`variable_semantics` 必须记「来源未登记」，500 Hz 只是我们自己的 `tout` 步长实测 |
| zip 的 MD5 `c7506f625dde69a131333d6002f5e6a2` | 本地 `md5sum` 该 zip **等于**该值；但"与页面公布值一致"无法核实——`china.scidb.cn` 403，`www.scidb.cn` 页面为 JS 壳，**取不到文件表** | 只能说"本地算出此值"。**该 md5 与被下载者是同一只手写出（同源），不构成外部来源证据**（A-88） |
| 来源性质 | 单位是等离子体所的中子/维护机器人方向，**不是半导体封装产线** | 作品集叙述里禁止把它包装成产线数据 |

## 五、这一节改变了什么、没改变什么

已改变：4 份仪器样例 + Export10 的**外部来源**由"第三方会话转述"升为"本会话独立重抓取且字节一致"；
DD_head 的"查无此文件"、ScienceDB 的语义缺口都拿到了出版方侧的独立证据。

未改变（仍是缺口，别在作品集里越级措辞）：
1. ScienceDB 原始包的**页面公布 MD5** 未取得 ⟹ 该数据集来源等级停在 public-doc。
2. 全部样本仍**缺电流通道**（`cur_q`），共振/频域类判据按 KB2 §5.2 保持软降级。
3. Export10（DaRUS 244531）**没有可用的跟随误差信号**，逐列实测（18,651 行）：
   `dPosition_load_tar` 与 `dPosition_load`、`dPosition_test_tar` 与 `dPosition_test`
   **逐行完全相等（差异行数 0）** ⟹ 位置指令≡位置反馈，`fe = cmd − fb ≡ 0`；
   `dPosition_diff` 是 −0.13281 mm ±0.00251 mm 的近常数偏置（不是 cmd−fb，残差恰好等于它本身）；
   `p_asco_enc − p_test` = −0.95353 mm ±0.01755 mm，与 `catanalyze.m` 里
   `p_diff_asco = p_asco_enc − p_test` 的定义一致 ⟹ DaRUS 的 `*_diff` 是**编码器−基准系偏置**，
   **不得**当 C1 的 `fe` 角色用。速度侧另有信号：`dVelocity_test_tar` vs `dVelocity_test`
   17,442/18,651 行不等，`dVelocity_asco` vs `dVelocity_asco_enc` 9,759 行不等。
   ⟹ 该样本只能算力/功率/速度侧判据，跟随误差与位置侧共振用它做不了；接入卡必须写明。
4. 6 份 ScienceDB CSV 的 `verdict` 仍受命名族缺口阻挡（task #15），红线只能记"未识别"，不能记"数据缺失"。

---

## 六、同日 20:00 追加：一次自我纠正 + 缺口 hunt 的实测结果

### 6.1 纠正：本文第三节对 `DD_head.csv` 的「查无此文件」结论**方法有误**

第三节用的判据是「本地 md5 与 filesize 在 DaRUS 两库的 `dataFile.md5 / filesize` 字段里 0 命中」。
这个判据对**整文件**成立，对**前缀切片**在结构上不可能命中——切片自己的 md5 与大小天然不等于母本。
本会话随后改用**逐字节前缀比对**（对候选母本发 `Range: bytes=0-400000`）：

| 候选母本 | 结果 |
|---|---|
| dataFile **394008**（`CableDirectDrive_Testbed/2024-07-23_LdaFricIdent/Data/RW/Export 10.csv`，43,700,198 B） | **前 400,001 字节与 `DD_head.csv` 完全相等**；全量落盘 md5 `62326eb83e0d31396c1d0d422254b5fe` = 发布方 API 登记值 |
| dataFile 394122（同库 `Data/UW/Export 10.csv`） | 第 **156** 字节即分歧（墙钟 14:37:13.764 vs [REDACTED_WALLCLOCK]），排除 |

⟹ `DD_head.csv` 的来源**已登记**，母本身份 `official-artifact`、`verified_by = self`。
第三节其余结论不受影响（4 份仪器样例与 Export10 的取证都是整文件级的）。
教训落进 `PROVENANCE-TEMPLATE.md`：**核对判据必须匹配文件的形态**——派生/切片件要按前缀或结构比，
不能拿整文件哈希冒充"查无"。

### 6.2 「缺真 fe + 真电流通道」这条到底闭合了没有——逐个实测

用户给的路线是「去 DaRUS-5171 的 `CableDirectDrive_Testbed` 找 `*_tar ≠ *_fb` 的记录」。
现场 API 核实该目录**确实存在**（`Data/RW` + `Data/UW` 各 36 个 Export + `.svdx` + `.nc` + 1 个 Settings XML）。
取回两个实物并自己算：

| 样本 | 实测 | 结论 |
|---|---|---|
| `incoming/393964_Export34_LdaFric_RW.csv`（9,135,420 B，md5 与 API 登记一致） | 1000 Hz / 16,754 行 / 40 通道 / 抖动 0.000 / 六条硬拒全过；`x_T` vs `x_Ttar` 差 4,945/16,754 行，峰值 **10.7 mm**，RMS 0.56 mm | **有真实位置跟随误差**（5171 路线成立）；`x_diff` 实测 ≡ `(-x_L) - x_T`（残差 mean=0 std=0），**不是 fe** |
| `incoming/394008_Export10_CDD_RW.csv`（母本全量，md5 与 API 一致） | 1000 Hz / 75,858 行 / 75.857 s；`x_T` vs `x_Ttar` 差 **64,284/75,858（84.7%）**，峰值 1.6 mm，RMS 35 µm；`v_T` vs `v_Ttar` 差 99.8% | 同上；且**无电流通道**（只有 `tau_L/tau_T` 力矩量，单位未标定） |
| `incoming/current-hunt/3759_Fig4_Path_errors_50mm.tab`（DARUS-3759，Steinle, Lukas，CC BY 4.0，dataFile 286569） | 2000 Hz / 40,000 行 / 20.000 s / 抖动 0.000；发布方 README 逐字定义 `e_x = x_d − x_l`；实测 `e_x ≡ x_d − x_T`（最大残差 4.0e-13）；`x_d ≠ x_T` **39,136/40,000** 行；`e_x` std 1.592e-6 m、峰值 5e-6 m；`T_M` 1.049–2.007 N·m | **目前手上最干净的真 fe 样本**，且 fs=2 kHz ⟹ 奈奎斯特 1 kHz，绕开了 500 Hz 顶不动 kHz 共振的老问题。仍**无电流**（只有力矩） |
| `incoming/current-hunt/4152_Sine_0_output_00.txt`（DARUS-4152，四连杆 Dynamixel XH430 真机） | 250 Hz / 14,993 行 / 59.996 s / 抖动 0.013 / 六条硬拒全过；首行原文含 `Goal Current [mA]`、`Pres. Current [mA]` | **目前唯一有实测电流的 accept 样本**。但**无位置指令** ⟹ 无 fe；250 Hz 也低于 §4.10 的 1 kHz 需求 |

⟹ **缺口状态**：真 fe ✅（3759 与 5171 CDD 母本两处，均本会话实测）；真电流 ✅（4152，同一台 Dynamixel 的目标/实测电流）；
**"同一份数据里既有真 fe 又有真 cur_q" ❌ 仍未闭合**——两个候选各缺一半，且电流侧那台是 250 Hz 的四连杆原型机，
不是进给轴伺服。诚实写法：能力矩阵里 `cur_q` 与 `fe` 两格分别标 `mapped`，但**组合格标 not_mappable(公开数据无此样本)**。

### 6.3 第三方会话（子智能体）报告的数字：哪些我核上了，哪些没有

| 它的断言 | 我的实测 | 判定 |
|---|---|---|
| 6114（`incoming/6114_x_velSweep_s0_n150_dir_pos.csv`）行数 33,901 | `wc -l` = 11,001，可解析 11,000 行；且**时间列是 ISO-8601 字符串**，单调性实测 True、dt 恒 1 ms（fs 1000 Hz、抖动 0.000）；`x_x_d` vs `x_x_l` **11,000/11,000 全差**，`\|e\|` 中位 6.1e-5 | **行数证伪**；文件本身另有价值（真 fe，激光干涉作参考）。校验器一度判它"时基非单调"是**解析器把 ISO 时间列当数值列**的产物，不是数据缺陷——记入 task #15 |
| `doi:10.18419/DARUS-4963` 是"96 通道 fe+电流"候选 | 现场 `GET /api/datasets/:persistentId/?persistentId=doi:10.18419/DARUS-4963` → `{"status":"ERROR","message":"User :guest is not permitted…"}`，而同格式的 3600/5171 调用均 OK | **未取得任何证据**，该 DOI 不得进 KB7，也不得写进任何卡片 |
| 3759 "x_d≠x_M 逐行 40000/40000" | 实测 `x_d≠x_T` = **39,136/40,000**；`x_d−x_M` 峰值 3.547e-5、RMS 1.995e-5 | 数字**偏差一档但方向正确**；引用时改用我的实测值 |
| 27 份 sidecar 交付、`retrieved_by` 不记 self | 已在本文一~四节复核（25/27 字节一致） | 采信 |

### 6.4 为此改动的一件工具（非产品代码，属用户点名的数据审计脚本）

`data/validate_raw.py` 四处，均由上述实测逼出，且每处都配了负向测试（`--selftest` 现 **21 条全执行、0 失败**）：
① 后缀表补 `.tab`——原来把 2.8 MB 的 3759 真 fe 候选整件当"非波形存证"跳过；
② 误差词表补 `e_x` 族——原来按"fe 全缺"把 3759 硬拒，而它的 fe 是发布方文档逐字定义的；
③ 派生判定补"截取/截断"，同时**排除否定语境**（`NONE（未转换/未截断…）` 曾被当成派生，把 4152 的哈希错剔除）；
④ `derived_from` 以 `NONE/无` 开头时不再进关键词扫描。

## 七、2026-10-20 20:30 追加：incoming 12 份候选的独立复验（主线程亲自执行）

`data/research_fe_current.md` 是**子智能体**交付的报告。按 A-88/A-89，它对我们只是 `public-doc`，
`verified_by ≠ self` 的数字不计入 `k`，因此 KB7 台账化之前由主线程独立复验了它的 load-bearing 结论。
**结论：load-bearing 数字全部复现；发现 1 项它没提到的独立事实（上游登记值 ≠ 实发字节）；并由此推出 A-94。**

### 7.1 复验方法（全部本会话执行）

| 手段 | 对象 | 结果 |
|---|---|---|
| `md5sum` 本地重算 | 12 份候选中 11 份有实体字节的 | 全部与上游 API 登记值逐字节一致 |
| `curl api/datasets/:persistentId/versions/:latest` | darus-2563 / 3003 / 3252 / 4224 / 6114 | 全部 HTTP 成功；`license = CC BY 4.0`；md5/filesize 见下表 |
| `curl zenodo.org/api/records/21456277` | KUKA zip | DOI/标题/`cc-by-4.0`/`files[].checksum` 与本地一致 |
| h5py 解 `rec_dSPACE521.{X,Y}`（`MATLAB_class=struct`，`XIndex` 为 **1 基**） | 3 份 `.mat` | 时基/通道/恒等式全部自行复算 |
| 逐列名电流语义扫描（`cur\|strom\|amps?\|i_[dq]\|amper\|acur`） | 12 份候选全部列名 | **命中电流语义的只有 4152 与 KUKA 两份** |
| 读上游 readme 原文 | KUKA | 时基单位自相矛盾（见 KB7） |

### 7.2 逐份复验结论（括号内为报告声称 → 我的实测）

| 样本 | 报告声称 | 主线程实测 | 判定 |
|---|---|---|---|
| 2563 validate `.mat` | 73,020@1k / 292,080@4k，jitter 2.62e-7 / 1.00e-6，`e_x_T` 恒等式偏差 2.6e-10 | **全部一致**（另确认第三栅格 `OnChange` 仅 26 点、jitter 0.2206） | ✔ SUPPORTED |
| 2563 `SP_v100_forw.mat` | 8,310 / 33,240，恒等式偏差 0.0 | 一致 | ✔ |
| 3003 `.mat` | 11,001 / 44,001，偏差 5.8e-15 | 一致 | ✔ |
| 3252 `.mat` | 2,139 / 8,556，2139/2139 行差 | 一致 | ✔ |
| 4224 四份 xlsx | md5 全对、无 README、`x_d`/`x_T`/`d_x_T` | md5 四份全对；上游 17 个文件里确无 README | ✔ |
| 6114 x_velSweep | 11,000 行、ISO 1 kHz、fe 全行不等、无电流 | 一致（`t` 列 ISO、fs=1000.07、jitter 1.097e-4；`b_x_d ≡ b_x_m` **0 行不等**） | ✔ |
| 6114 lsmc.csv | 3,000 行 | 一致 | ✔ |
| 6114 ObserverTestSet.tab | 5 列、无时间列、fe 真实 | 一致（9,978 行 × 5 列 `v_des/a_des/j_des/x_des/x_act`） | ✔ |
| KUKA csv | 6 路 `Iststrom (A)`、Sample dt 恒 4、时基矛盾 | 一致（A2 min/max/std = -2.1623/1.4626/0.4739；readme 第 36 行 vs 第 44–45 行矛盾原文） | ✔ |
| wiredrawing / 17622448 / generator | 硬拒 | 未逐项复算（结论为"拒"，不影响任何接入） | 采纳为拒 |

### 7.3 独立发现（报告未提）

**6114 `ObserverTestSet.tab` 的上游登记值与实发字节不一致**：API `files[]` 记
`filesize = 367,389 / md5 = 56b18a8729803f71deae031a04445cad`；本地实体 `367,419 B / md5 = fd18abe49bf122f6f293289444e20adb`。
两侧都由主线程实测（`md5sum` 复算 + 现场 API），差 30 B，疑换行符处理。
⟹ 登记为 `upstream_checksum_mismatch`：**不**据此下调 `source_tier`（文件名/大小/目录三项一致），
但**不得**把本地哈希结论外推到上游原始件（呼应硬规则 4：核对判据要匹配文件形态）。

### 7.4 由此产生的两条裁决

- **A-94**：`.mat` 的 4 kHz 测量栅格把 A-65 的「kHz 判据在 T1-a 不可达」从**数据集级**收窄为**样本级**；
  频带门禁改按样本 `fs` 判。`fs = 4 kHz` 样本上门禁通过，但因 `cur_q` 全库缺失，
  R-03/R-04 仍落 `unavailable`（`band_gate_pass_channel_gate_fail`），**不得**写成"未发现共振"。
- **KB2 §七 新增第 7 条**：C1 单栅格契约遇上多速率文件的两难，给出 (a) 两字段 / (b) 保守降采样
  两个处置，默认按 (b) 登记，不按 (a) 声称已接入 4 kHz。

### 7.5 能力格终判

22 份已核验样本里，**0 份**同时具备真 `fe` 与真 `cur_q` ⟹ KB8 该格
`not_mappable(公开数据无此样本)`（措辞按 A-31：写"核验范围内无此样本"，不写"暂未找到"）。

---

## 八、本会话补核：ScienceDB 机器人关节样本（B 组 12 个文件）

> 本节全部数字由主线程在本会话亲自跑出（`data/_audit_staging_mat.py`、`data/validate_raw.py`、
> `md5sum`、`curl` + DataCite REST、按字节重抓母包），**不含任何转述**。

### 8.1 上游标识独立核验（不采信 sidecar）

sidecar 只写了 DOI/许可/作者，本会话**独立**去 DataCite 核对：

`curl https://api.datacite.org/dois/10.57760/sciencedb.04148` → **HTTP 200**，9623 B

| 字段 | 实测值（逐字） |
|---|---|
| `doi` | `10.57760/sciencedb.04148` |
| `titles` | `Raw data of motor position in several cases` |
| `publisher` | `Science Data Bank` |
| `publicationYear` / `version` / `state` | `2022` / `V1` / `findable` |
| `rightsList` | `Creative Commons Attribution 4.0 International` · `https://creativecommons.org/licenses/by/4.0/legalcode` |
| `url` | `https://www.scidb.cn/detail?dataSetId=7e95fb543e3f407d84fe19150a7e1305` |
| `sizes` | `["50493558 bytes", "1 files"]` |
| `creators` | `Huayuan Huang`（含 USTC 署名）、`Hongtao Pan`、`Cheng, Yong`（后二者属 Institute of Plasma Physics, Hefei Institutes of Physical Science） |
| `subjects` | `Mechanical engineering` / `periodic trajectory` / `Point-to-point trajectory` / **`position error`** / `robot` |
| `descriptions` | "This dataset contains both the point-to-point trajectory and periodic trajectory of two different robot joints under three controllers." |
| `relatedIdentifiers` | `IsSupplementTo → doi:10.1002/acs.3276` |

⟹ sidecar 的 DOI、许可（CC BY 4.0）、三位作者、机构**全部为真**。
ScienceDB 的数据集 API 端点本会话试过 3 个路径**全部 404**（`/api/sdb/dataset/doi/…`、
`/detail?dataSetId=…`、`/get?id=…`），故**逐文件校验和无法从 API 取**，改走字节对拍。

### 8.2 母包按字节对拍（本会话重抓，非转述）

`https://china.scidb.cn/download?fileId=634e4983934f5e4e97ace801`

- `Range: bytes=0-63` 探针 → HTTP 206，首 4 字节 `PK\x03\x04`（确认是 zip）
- 全量重下 **50,493,558 B**（与 DataCite 登记的 `50493558 bytes` **逐位一致**）
- 本地 `md5 = c7506f625dde69a131333d6002f5e6a2`
- zip 内 **7 个条目**：`data/` + 6 个 `.mat`，未压缩合计 **51,987,952 B**
- **6 个 `.mat` 成员与本地实体全部逐字节一致**：

| 成员 | md5（zip 内 = 本地） |
|---|---|
| `Controller1Periodic.mat` | `d49d42242d00d07b8e40453e2d02d52a` |
| `Controller1Point2Point.mat` | `ac6fc87a3504e3d3203dfedd14475893` |
| `Controller2Periodic.mat` | `794747ac523029ae0ab9a613a719ea53` |
| `Controller2Point2Point.mat` | `63240318fbe1cabefa4cf43963b9a86d` |
| `Controller3Periodic.mat` | `87221dcc7c7a64df5d8391381bec989f` |
| `Controller3Point2Point.mat` | `17bbe47041036604f77aca7d09cb5020` |

⟹ 这是**本次台账化中唯一一组做到「全项复测」的文件**。

### 8.3 6 个 `.mat` 的实测指标

- 文件头逐字：`MATLAB 5.0 MAT-file, Platform: PCWIN64, Created on: Mon Oct 17 15:08:07 2022`（各文件时间不同）
- 变量：**11 个**（`tout` + 10 数据列），全部 `float64`、`shape=(N,1)`、**NaN 计数 0**
- 列名逐字：`tout, q1, q2, j1_qd, j2_qd, theta1, theta2, j1_eq, j2_eq, j1_etheta_pos, j2_etheta_pos`
- 周期轨迹：`N = 200,001`，`tout ∈ [0, 400.000] s`，**400.000 s**
- 点位轨迹：`N = 100,001`，`tout ∈ [0, 200.000] s`，**200.000 s**
- `dt` 恒 `0.002`（`dt_min = dt_max = 0.002`），**`fs = 500.000 Hz`**，
  `dt_jitter_ratio` = **7.557e-12**（周期）/ **4.505e-12**（点位），严格单调
  ⟹ KB2 §5.1 的 1/2/3/4/5 条**全过**，且是全库时基最干净的一批
- 电流词表七类（`cur / strom / amps / amper / acur / i_d / i_q`）在 10 个数据列上**零命中**
- 频带：`reliable_band_hz = 500/1.25 = 400 Hz` < `band⊥ = 2000 Hz`
  ⟹ A-94 的**样本级**判定下，R-03/R-04 在这一族上 `unavailable`

### 8.4 关键否证：`*_eq` / `*_etheta_pos` 不是任何两列之差

命名 + DataCite 的 `position error` 主题词都指向"误差通道"，主线程把候选恒等式逐条复算（`max|残差|`）：

| 文件 | `j1_etheta_pos − (theta1−q1)` | `j1_eq − (theta1−q1)` | `j2_eq − (q2−j2_qd)` | 信号量程 |
|---|---|---|---|---|
| B1 Controller1Periodic | **4.002e-01** | **3.000e-01** | 6.000e-01 | 5.99e-01 |
| B2 Controller1Point2Point | 5.948e-03 | 4.329e-03 | 5.908e-03 | 6.00e-01 |
| B3 Controller2Periodic | 3.765e-03 | 3.679e-03 | **6.000e-01** | 6.00e-01 |
| B4 Controller2Point2Point | 3.809e-03 | 3.648e-03 | 6.963e-03 | 6.05e-01 |
| B5 Controller3Periodic | 3.134e-03 | 1.998e-03 | **6.000e-01** | 6.00e-01 |
| B6 Controller3Point2Point | 5.681e-03 | 3.878e-03 | 2.355e-03 | 6.00e-01 |

同一恒等式在 B1/B3/B5 上残差与信号**同量级**、在 B2/B4/B6 上差两个数量级 ⟹ **不自洽**，
不能认定为「某两列之差」。另：`j1_etheta_pos` 量程（≈ −3.4e-3 … 0.400）与 `theta1`（≈ −6.7e-7 … 0.599）**不同**，
不支持把它当 `pos_fb`。
⟹ `fe` 角色记 **待人工复判**（需上游逐列定义文档裁定），**不按命名直接采信**（KB2 §三 / A-87）。

### 8.5 派生 CSV 与 `.mat` 的关系

6 个 `电机位置与跟随误差_公开数据集_Controller{1,2,3}{周期,点位}轨迹.csv` 是**本地转换件**
（sidecar 明写 `original_filename: NONE（由 data/….mat 转换而来，非原始导出）`）。

- 表头 **11 列**，与 `.mat` 变量名**完全一致**（早前记为"10 列"是错的，漏了 `j2_etheta_pos`，已更正）
- 逐行逐列与 `.mat` 比对：`max|Δ| = 5.000e-08`（`tout` 为 5.684e-14），即约 8 位有效数字的写出精度
- `fs` 实测 500.000 Hz，`dt_jitter_ratio` 实测 **0.0**（`n_distinct_dt = 16`，但 median 恒 0.002）
- **判 `reject`**：红线 6 开火，脚本判词逐字
  `cur_q/vel_fb/fe 未识别（8/10 列未映射，疑为命名族缺口而非数据缺失，须按数据集文档人工复判）`
- 按 A-88，这些 CSV 与 `.mat` **同源**，哈希相符**不计入**独立核对 k；接入应引 `.mat` 原件

### 8.6 ★ 本会话修掉的自测工具缺陷：`data/validate_raw.py` 名实错位

台账化过程中用 `validate_raw.py` 跑 staging CSV，报告里出现 `tout` 的统计量等于 `q1` 的值——追下去是**真缺陷**：

- 位置 `parse_table()`：plain_matrix 分支取名用 `raw_name = names[n]`，而 `n` 是 `val_cols` 的下标
  （`val_cols` **已剔除时间列**），`names` 却是**含时间列的整行表头** ⟹ **名实整体错位一列，且末列被静悄悄丢掉**
- 最小复现：4 列 `t,a,b,c` 的文件只报出 3 个通道，名 `t` 挂在 `a` 的数据上，`c` 整列消失
- 影响面：凡时间列**不在末位**的 plain_matrix CSV（即最常见形态）都中招；
  角色映射按**错名**判定、NaN/动态分段统计挂在**错名**上 ⟹ 结论可错
- TwinCAT 交错布局走 `names[n]` 的旧口径**恰好正确**，故 4 个 DaRUS Scope View 样本不受影响（已逐一复跑确认）
- 修法：plain_matrix 改按列号取名（`names[ch_idx]`），并加**负向回归断言**
  （时间列在首位时不错位、不丢列）——KB0 §6 检查 22 要求断言须有负向测试
- `--selftest` 结果：本会话跑出 **22 行 PASS / 0 行 FAIL**（末行汇总只统计负向用例那 21 条，
  回归断言与自述核对断言各自单列 PASS/FAIL，失败会计入末行的"失败"计数）
- 修后复跑本批 CSV：未映射列 **9/10 → 8/10**，`j2_etheta_pos` 不再丢失 ⟹ **台账数字已按修复后重出**

### 8.7 已登记但本轮不修的第二类误报：`rate` / `amp` 子串命中

`channel_role()` 用子串匹配量名，实测三处误报：
`OilLevel_L → vel_fb`（命中 "le**vel**"）、`FailureRate → vel_fb`（命中 "**rate**"）、`Timestamp → cur_other`（命中 "timest**amp**"）。
会把并不存在的 `vel_fb`/`cur` 算成"已识别"。**当前不影响任何硬拒结论**
（`17622448_dataset.csv` 已因时基非严格单调被拒），故本轮只登记（KB2 待办 R-5），
修法须走 token 化匹配（复用已有 `name_tokens`），不继续加正则补丁。

### 8.8 核对主体分级（A-89：不可转借 `self`）

- `data/incoming/` 12 个 v2 sidecar 的 `verified_by: self（…本会话亲自执行…）`，
  其"本会话"是**并行智能体的会话**（它们自己在 `retrieved_by`/`verified_by` 里写明了这一点）
  ⟹ KB7 台账另设「主线程核对」栏，不转借该 `self`；这 12 份的 load-bearing 结论已由主线程独立复测
- B 组 12 个文件：母包重抓 + 6 个成员逐字节对拍 + 逐列统计，全部主线程亲自执行 ⟹ **唯一「✔ 全项复测」组**
- **12 个 incoming 文件无 sidecar**（含 `393964_*`、`394008_*`、`394085_*xml`、`KUKA_payload_dataset.zip`、
  `wiredrawing_dataset.xlsx`、`17622448_dataset.csv`、`2563_LDD_Transfer_*`、`generator_data0001.csv` 及 4 个辅助件）
  ⟹ 按"无 sidecar 不可进接入卡"，它们**暂不能进 KB2 §4 接入卡**；
  A 组表里这些行的"对拍"列是**主线程实测**而非 sidecar 支撑，sidecar 缺口是独立待办
