# 电流通道检索报告（current-channel hunt）

日期：2026-10-20 ｜ 检索智能体：current-hunt 子智能体 ｜ 工作目录：`data/incoming/current-hunt/`
检索口径：KB2 §5.1 六条硬拒 + 缺口两角色（①电流通道 ②位置跟随误差 pos_cmd≠pos_fb 或直接 fe 通道）。
本报告所有「实测」数值均为本会话亲自下载样本后用 `C:/tmp/an2.py` / `h5py` / `numpy` 跑出的结果；未跑出的标注「未实测」。

---

## 一句话结论 + 排行榜

**一句话结论**：公开可再分发的**真机**数据里，「电流通道」与「位置跟随误差」几乎从不同时出现在同一份样本中——斯图加特 ISW/MEKAT 的位移控台架（3759/3292/5160/6333/3900）有干净的 `e_x` 跟随误差但**只记录力矩/电压、无电流**；唯一记录**实测相/电枢电流**且过得了六条硬拒的新样本是 **DARUS-4152（四连杆 Dynamixel 伺服）**，但它是**电流驱动**、没有位置设定值，故缺 FE 角色。同时具备两角色且真机的候选（Zenodo 7240050 协作机器人 joint-position + motor-current）是 788 MB ROS `.bag`，超单文件 150 MB 上限**未实测**。下载总量 27.5 MB。

按对「缺口」的可用度排行（电流=最稀缺，优先）：

| # | 候选 / 样本 | 电流通道(①) | 位置FE(②) | 六条硬拒 | 结论 |
|---|---|---|---|---|---|
| 1 | **DARUS-4152** `4152_Sine_0_output_00.txt` | ✅ 实测电流(mA) | ❌ 无 pos_cmd（电流驱动） | ✅ 全过 | **部分可用（缺②）/ 电流缺口=可用** |
| 2 | **DARUS-3759** `3759_Fig4_Path_errors_50mm.tab` | ❌ 只有力矩 T_M | ✅ e_x，x_d≠x_M 逐行 | ✅ 全过 | **部分可用（缺①）** |
| 3 | **DARUS-3292** `3292_vel_sweep_s_0_dir_pos.mat` | ❌ 力矩+电压 | ✅ e_x_T | ✅ 全过(1 kHz) | **部分可用（缺①）** |
| 4 | **DARUS-5160** `5160_Fig6_Path_errors.tab` | ❌ 力矩 T_M1/2 | ✅ e_x，逐行≠ | ⚠️ 多段拼接致 jitter 超标 | **需分段后可用（仍缺①）** |
| 5 | **DARUS-6333** `6333_figure3_data.tab` | ❌ 无 | ✅ x_Sdes≠x_S | ⚠️ 3 段 time 归零致 dt 中位数=0 | **需分段（缺①，且无力矩）** |
| 6 | **DARUS-3900** `3900_const_vel_110.tab` | ❌ 力矩 tau_m | ✅ 多轴 x_?_d vs _m | ✅ 六条全过（2026-10-21 R-3 修 ISO 文本列解析后逐行差分：fs 1000.1 Hz、抖动 0.038、时长 2.702 s、2,701 行） | **已实测（缺①=无电流）** |
| 7 | **DARUS-4075** `4075_experiment_std.csv` | ❌ 无 | 仅位置 x[i]，无电流 | ❌ 硬拒#1（10 Hz，约 520 行 <2000） | **不可用** |
| — | **Zenodo 7240050**（协作机器人 joint+current）| ✅（自述） | ✅（自述） | 未实测（788 MB .bag，超限） | **未实测** |
| — | **Zenodo 3929384**（电动缸 ZeMA，相电流1-3+速度）| ✅（自述，相电流）| ❌（无位置设定，仅速度） | 未实测（1.1 GB .h5，超限） | **未实测** |
| — | **Zenodo 21456277 / 本地 KUKA** | ✅ 实测 Iststrom_A1..A6 | ❌ 无位置列 | 本地已核验表头 | **电流only，缺②（且属他方数据）** |

---

## 逐候选实测

### 1. DARUS-4152 — Motion and Motor-Current Data of a Four-Bar Linkage（**电流缺口的首选**）

- DOI：`10.18419/DARUS-4152`（V1，2024）｜ 许可：**CC BY 4.0** ｜ 作者：Röder, Benedict; Ebel, Henrik; Eberhard, Peter
- 台架：Dynamixel XH430-W350-R 伺服驱动四连杆，**电流控制**（对关节施加力矩），真机。
- 表头原文（首行 `%`）：
  `Time [s], Goal Current [mA], Pres. Current [mA], Pres. Voltage [V], Pres. Position [rad], Pres. Velocity [rad/s]`
- 样本 `4152_Sine_0_output_00.txt`（dataFile id 290225），实测：
  - 数据行数 **14,993**（≥2000 ✅）；时长 **60.00 s**（≥0.5 ✅）；fs = **250 Hz**（dt 中位数 0.004 s）。
  - `dt_jitter_ratio = 0.0133`（std(dt)/median(dt)，≤0.2 ✅，时基很稳）。
  - `nan_ratio = 0.00000`（0/89958 ✅）。
  - 动态分段：速度 >0.05 rad/s 占 **70.7%**，move/dwell 切换 **5 次**（有动态段 ✅）；规则#6：cur+vel 在场 ✅。
  - **电流通道实测**（角色①）：`Pres. Current` 稳健区间 p0.1≈0、p50=8.07、p99.9=21.5 mA，std≈7 mA（含 6 个 >1000 mA 的寄存器毛刺，max 见 1.76e5 mA，属个别坏点、非 NaN，不触发#4）。`Goal Current` 0–18.83 mA。
  - Goal vs Present 电流逐行 52.8% 不等（中位差 2.69 mA）——这是**电流跟踪残差**，不是位置跟随误差。
- 角色②（位置跟随误差）：**缺失**。无 `pos_cmd`；位置只有实测 `Pres. Position`（-π..π rad），设定值是电流而非位置。故无法构造 pos_cmd≠pos_fb。
- **结论**：**部分可用**——对「电流通道」缺口（本项目最缺、共振/频域判据非它不可）是**目前最干净、过得了六条硬拒的真机电流样本**；缺角色②位置跟随误差。`4152_Sine_0_output_00.txt.source.txt` 已配。

### 2. DARUS-3759 — Learning Compensation of the State-Dependent Transmission Error（**FE 最干净的实测**）

- DOI：`10.18419/DARUS-3759`（2024）｜ 许可：**CC BY 4.0** ｜ 作者：Steinle, Lukas ｜ 台架：预紧消隙进给轴，真机。
- 样本 `3759_Fig4_Path_errors_50mm.tab`（dataFile id 286569），表头原文：
  `time  x_d  x_T  x_M  T_M  e_x  e_x.sim`（制表符分隔）
- 实测：数据行 **40,000** ✅；时长 **20.0 s** ✅；fs = **2000 Hz**；`dt_jitter_ratio = 1.88e-12`（等间隔，极稳）；`nan_ratio = 0`。
- 角色②（位置跟随误差）：✅ **`x_d`（设定）vs `x_M`（电机反馈）逐行差异 = 40000/40000 行**（absdiff 中位 1.76e-5 m）；并自带 `e_x` 通道（min -4.1e-6, max 5.0e-6, std 1.59e-6 m）。**不是**逐行相等的退化情形（对照被排除的 3600/5171）。
- 角色①（电流）：❌ 只有 `T_M`（电机力矩 1.05–2.01 Nm）与位置，**无相/d-q/电枢电流**。
- **结论**：**部分可用（缺电流）**。六条硬拒全过，是位置 FE 角色的高质量样本；不填电流缺口。`3759_Fig4_Path_errors_50mm.tab.source.txt` 已配。

### 3. DARUS-3292 — Increasing dynamic accuracy of ball screw drives with qSMC（FE 干净，dSPACE/HDF5）

- DOI：`10.18419/DARUS-3292` ｜ README 自述：滚珠丝杠 + SIEMENS 电机 + 下方 LDD 扰扰台架，真机；4 kHz（部分降到 1 kHz）。
- 样本 `3292_vel_sweep_s_0_dir_pos.mat`（dataFile id 172414，2,311,064 B，与 API filesize **字节精确相等**），dSPACE `rec_dSPACE452` 结构，30 通道。
- 通道名（原文，节选）：`e_x_T, e_x_obsv, x_meas_motor, x_meas_table, v_meas_motor, v_meas_table, M_KGT_act, u_motor [rot], tau_des_add, F_des_LDD …`
- 实测：`X` 时间轴 **11,000 行 / 10.999 s / 1000 Hz / jitter = 1.05e-6**；`e_x_T`（跟踪误差，min 7.7e-6、max 3.8e-4、std 4.1e-5 m）✅ 角色②。`x_meas_table`/`x_meas_motor` 为 4 kHz（44,000 行）需重采样对齐。
- 角色①（电流）：❌ 通道名电流检索命中 = `[]`（**无电流**）；电气量仅 `M_KGT_act`（力矩）与 `u_motor [rot]`（电压）。README 提到逆变器内有「current setpoint filter」，但**电流本身不落盘**。
- **结论**：**部分可用（缺电流）**。FE 高质量、六条硬拒全过。

### 4. DARUS-5160 — Compensation of the Transmission Errors in Electrically Preloaded Anti-Backlash Drives

- 样本 `5160_Fig6_Path_errors.tab`（id 388387，12.9 MB），表头：`time x_d x_T x_M1 x_M2 T_M1 T_M2 e_x e_x_sim`。
- 实测：解析 **86,666** 行；单文件里是多次测量拼接，`time` 在段末回落 → **`dt_jitter_ratio = 163`（>0.2）**，直接当整段载入触发**硬拒#3**；需按 `time` 复位点分段后逐段评估（分段后 fs=2000 Hz、时长≈10 s）。
- 角色②：✅ `x_d` vs `x_M1` 逐行差异 = 86666/86666；自带 `e_x`（std 1.24e-6）。角色①：❌ 仅力矩 `T_M1/T_M2`。
- **结论**：**需分段后才可用（仍缺电流）**；以未分段原样命中硬拒#3。

### 5. DARUS-6333 — Compensating for Backlash in Rack-and-Pinion Drives

- 样本 `6333_figure3_data.tab`（id 639696，1.7 MB），表头：`meas_idx  time  x_Sdes  x_M  x_S`。
- 实测：解析 **33,239** 行；含 `meas_idx`=1/2/3 三段，`time` 每段从 0 起 → **dt 中位数=0**，整段载入抖动不合法（硬拒#3），需按 `meas_idx` 分段。单段时长≈2 s、fs=2000 Hz（各段是否≥2000 行未逐段复核）。
- 角色②：✅ `x_Sdes` vs `x_S` 逐行差异 = 30,239/33,239（absdiff 中位 3.6e-5、max 3.7e-4）。角色①：❌ **既无电流也无力矩**，只有位置。
- **结论**：**需分段（缺电流，且电气量全无）**；作 FE 可用但信息量小。

### 6. DARUS-3900 — Robust Inverse Feedforward with Hybrid Motion（多轴）

- 样本 `3900_const_vel_110.tab`（id 286320，1.2 MB），44 列：`t(ISO datetime)  id  *_tau_m  *_v_d  *_x_d  *_x_l  *_x_m`（x/y/z 多轴，`_d`=设定、`_m`=电机、`_l`=光栅）。
- 角色②：✅ 有 `x_?_d` 设定与 `x_?_m`/`x_?_l` 反馈可构造 FE。角色①：❌ 电气量仅 `*_tau_m`（力矩），无电流。
- 实测限制：首列 `t` 是带时区文本（`2024-01-15 15:04:31.483000+00:00`），我的差分脚本按数值解析失败 → **行数/时长/jitter/FE 逐行差「未实测」**，仅表头与通道语义已核。相邻样本时间步看起来是 1 ms。

> **本仓复算更正（2026-10-21，KB0 §6 检查 27；正文原句不改）**：解析器补上 ISO-8601 文本列的
> epoch 秒转换（R-3）后，`data/validate_raw.py data/incoming/current-hunt/3900_const_vel_110.tab`
> 实测 **2,701 数据行 / 41 个数据列 / fs 1000.1 Hz / 抖动 0.038 / 时长 2.702 s / 严格单调 Y / 六条全过**，
> 打印快照在 `build/validate_incoming_after_r7.txt`。⟹ 上面那句「未实测」的**成因是解析器不是数据**
> （"看起来是 1 ms" 现已差分确认）。**另一处更正**：本行原写「44 列」，实体表头逐字段计数为
> **42 个字段 = 1 个 `t` + 41 个数据列**（`head -1 … | tr '\t' '\n' | wc -l` = 42），44 不可复现。
> 结论列的「缺①=无电流」不受影响（41 列里确无电流语义列）。
- **结论**：**部分实测（缺电流）**；如需可用样本，须补一段 datetime 解析后再测六条硬拒。

### 7. DARUS-4075 — Adaptive Preload Control of Cable-Driven Parallel Robots

- 样本 `4075_experiment_std.csv`（id 285257，665 KB），COPacabana-Scope 导出（LABVIEW），列 `x[0..7]  v_add[…]`（位置/速度变量，无电流、无位置设定值）。
- 实测：`SampleTime[ms]=100`（**10 Hz**），起止跨度约 52 s → **约 520 行 < 2000 → 命中硬拒#1**。无电流。
- **结论**：**不可用**（样本不足 + 缺两角色之一）。

---

## 检索到但无法核验的候选（**均未实测**）

> 以下只列可复核的上游记录与「为何未取到样本」，数值一律「未实测」，不得当证据引用。

1. **Zenodo 7240050 — High Payload Collaborative Robot — Joint States / Motor Current / TCP Force-Torque**（CC BY 4.0，2022，Katsampiris Salgado; Haninger）。
   自述含 **机器人关节位置 + 电机电流 + TCP 位姿/力矩**，是唯一「两角色同时在场」的真机候选。
   **未实测原因**：唯一数据文件 `data.zip = 788,355,579 B`，超任务单文件 150 MB 上限；且内为 ROS `.bag`，需 rosbag/rosbags 解析器。**这是最该后续投入核验的目标**（若能拆包取一段）。
2. **Zenodo 3929384 / 3929385 — Sensor data set, electromechanical(电动缸) at ZeMA testbed (2 kHz)**（CC BY 4.0，Klein, Steffen）。
   已核 `documentation.pdf`（本会话下载 568 KB，md5 `a7b654478e41e4dfc707d2fb0732231f`）：11 页 = microphone / 3×acceleration / axial force / pressure / velocity / active current / **motor current phase 1/2/3**。→ 有**三相电流**（角色①），但**只有速度、无位置设定值**，故大概率**缺角色② FE**。
   **未实测原因**：数据文件 `Sensor_data_2kHz.h5 = 1,107,393,400 B`（>150 MB）跳过；数组级行数/抖动/FE 未跑。
3. **Zenodo 21456277 — Motor-Current Dataset … Two KUKA KR3 Robots**（CC BY 4.0，2026-07，KUKA Trace，12 ms 周期）。
   = 本地 `data/incoming/KUKA_payload_dataset.zip`（他方智能体已取）。本会话仅读本地解压样本表头核验：列 = `Iststrom_A1..A6 (A); Sample` → **实测六轴电枢电流（角色①）**，但**无位置设定/反馈列（缺角色②）**；12 ms→约 83 Hz。数值细节属他方数据，此处不重推。
4. **Harvard Dataverse 公共搜索 API**（`api.dataverse.org/v1/search`）：直连与 `-G` 编码两种写法均返回 `http 000`（本机代理到该域无响应），**未取得任何样本，未实测**。Zenodo/DaRUS 可达故不受影响。
5. **IEEE DataPort / Kaggle / CWRU / PHM C-MAP**：均**未取到可匿名直连下载的真机样本**（CWRU 为轴承振动+电流、无运动位置设定；C-MAP/PCoE 为 NASA **仿真**退化数据，不满足「真机实测」）。**未实测，未纳入**。

---

## 备注 / 处理痕迹

- 全部下载落在 `data/incoming/current-hunt/`，合计约 **27.5 MB**（< 400 MB 上限）。未触碰 `data/raw|staging|sidecar_in` 与 incoming 顶层既有文件（KUKA 表头为只读查看）。
- 4152 / 3292 下载字节与 DaRUS API `filesize` **精确相等**；3759/5160/6333/3900 下载字节较 API 值多 ≤0.03%（传输换行/收尾差异），以本地 md5 为准（见 sidecar 与下表）。
- 本地样本 md5sum：
  `831e2475849dd02634a89b63ef5c177e  4152_Sine_0_output_00.txt`
  `a49c9d0b9475d13fb3b96b44eba7f40f  3759_Fig4_Path_errors_50mm.tab`
  `52242ae7a732e9217e77c40f49935305  3292_vel_sweep_s_0_dir_pos.mat`
  `3bc7964c5ecc9ab9aff56ca7b2c898c5  5160_Fig6_Path_errors.tab`
  `f571b52c3f3d0d8a97e0d2b89f40d37e  6333_figure3_data.tab`
  `db0d5f82d53eca85fa8d760e4c5c243d  3900_const_vel_110.tab`
  `5852f0620fd446d30af70e1e6e7d7f98  4075_experiment_std.csv`
- 关键判断（供主智能体裁决）：**电流缺口的最优可落地样本 = DARUS-4152**（真机电流、六条硬拒全过、共振/频域类判据可用）；「电流 + 位置 FE 同框」目前**无 ≤150 MB 可直接实测的公开真机样本**，唯一强候选 Zenodo 7240050 需专门拆 ROS `.bag`。
