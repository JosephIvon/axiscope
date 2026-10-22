# T1 真实测量数据集 — DaRUS（斯图加特大学）+ ScienceDB（合肥物质院）

核验日期：2026-10-19 / 2026-10-20 补核。全部结论来自实际下载与解析，非页面描述转述。
ScienceDB（B 组）一族的核验方法与逐项数字见 `data/VERIFICATION-2026-10-20.md` 第八节。

## 出处与许可

| | DARUS-3600 | DARUS-5171 |
|---|---|---|
| 标题 | Measurement data for: Development of a Cable Actuator Test Rig for Identification of Dynamic Running Properties of Synthetic Fiber Ropes | Measurement Data for Experimental Modeling of Synthetic Fiber Ropes for Slip Compensation for Application in Cable |
| 作者 | Reichenbach, Thomas — University of Stuttgart (ROR 04vnq7t77) | 同 |
| 发布 | 2023-10-17，v1 | 2026-07-20，v1 |
| 许可 | **CC BY 4.0** | **CC BY 4.0** |
| 文件数 | 393 | **3488** |
| DOI | 10.18419/DARUS-3600 | 10.18419/DARUS-5171 |

署名要求：引用须注明 Reichenbach/University of Stuttgart + DOI + CC BY 4.0。

### 追加数据集（2026-10-20 台账化时新登记，全部 CC BY 4.0，本会话现场核过 API `license` 字段）

| DOI | 标题（API 字段原文） | 文件数 | 关键 fs | 本项目用途 |
|---|---|---|---|---|
| `10.18419/DARUS-2563` | Identification data for Linear Direct Drive Forces compensation | 12 | **4 kHz 测量栅格** + 1 kHz 轨迹栅格 | **真 fe + 4 kHz**（`e_x_T` 恒等式实测成立）→ A-94 频带松绑的样本基础 |
| `10.18419/DARUS-3003` | Identification data for plant and friction identification | 100 | 4 kHz / 1 kHz | 同上（`e_x_T` 偏差 5.8e-15） |
| `10.18419/DARUS-3252` | Replication Data for: Robust µ parameterization … cascaded control for feed drives | 66 | 4 kHz / 1 kHz | 同上（无 `e_x_*` 通道，须自算 `cmd − fb`） |
| `10.18419/DARUS-4224` | Replication Data for: Automatic Preload Adaptation for Rack-and-Pinion Drives | 17 | 2 kHz（`dt = 0.5 ms`，xlsx 表内实测） | `x_d`/`x_T`/`d_x_T` fe 对 + 预载自适应对照；**上游无 README，逐列语义未发布** |
| `10.18419/DARUS-6114` | Replication Data for: Evaluation of Sliding-Mode Position Controllers on Multi-Axis Machine Tools with Compliant Mechanics | 50 | 1 kHz（ISO 时间戳列） | 五轴铣床 `*_x_d`/`*_x_l`/`*_x_m` + `e_3d`；**`b_x_d ≡ b_x_m` 逐行相等（命令镜像，不可当反馈）** |
| `10.18419/DARUS-3759` | （Path errors 实验数据集，见 KB2 §4 族卡与 `data/incoming`） | — | **2 kHz / 40,000 行** | **当前最干净的真 fe**：`e_x ≡ x_d − x_T` 实测偏差 4e-13 |
| `10.18419/DARUS-4152` | （Dynamixel 伺服 ASCII 波形） | — | 250 Hz / 14,993 行 | **当前唯一的真机实测电流**：`Goal/Pres. Current [mA]` |
| `10.5281/zenodo.21456277` | Motor-Current Dataset for Cycle-Level Payload Estimation on Two KUKA KR3 Robots（VSB – TU Ostrava） | 1 zip（128 × `collector_*.csv`） | **时基自相矛盾，见下** | 唯一的**单位明写安培**的真机电流（`Iststrom_A1..A6 (A)`），但无位置通道 |
| `10.5281/zenodo.21526135` | Multi-Block Vibration and Motor-Current Dataset from an Industrial Wire-Drawing Machine | — | 30 s/样本 | 8 路块电流真实，但 `dt_jitter_ratio = 192.9` ⟹ **硬拒**，本项目不接入 |
| **`10.57760/sciencedb.04148`** | Raw data of motor position in several cases（Science Data Bank，中国科学院合肥物质科学研究院 等离子体研究所） | 1（zip 母包 50,493,558 B） | **500 Hz**（`tout` 步长恒 2.0 ms，实测） | **时基最干净的一批**：400.000 s / 200.000 s，`dt_jitter_ratio` 实测 7.6e-12 / 4.5e-12 ⟹ 实质为 0，严格单调；**无电流列**；`*_eq` / `*_etheta_pos` 误差列存在但逐列语义未实测 ⟹ 角色判定待人工复判 |

★ **ScienceDB 这一份的标识与许可是本会话独立核过的（不是转述 sidecar）**：
`curl https://api.datacite.org/dois/10.57760/sciencedb.04148` → HTTP 200，DataCite 记录逐字给出
`doi = 10.57760/sciencedb.04148`、`titles = ["Raw data of motor position in several cases"]`、
`publisher = Science Data Bank`、`publicationYear = 2022`、`version = V1`、`state = findable`、
`rightsList = [Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/legalcode]`、
`url = https://www.scidb.cn/detail?dataSetId=7e95fb543e3f407d84fe19150a7e1305`、`sizes = ["50493558 bytes", "1 files"]`。
创作者逐字：`Huayuan Huang`（Institute of Plasma Physics, Hefei Institutes of Physical Science, **University of Science and Technology of China**）、
`Hongtao Pan`、`Cheng, Yong`（后二者同属等离子体研究所）。
`subjects` 逐字含 `periodic trajectory` / `Point-to-point trajectory` / **`position error`** / `robot`；
`descriptions` 摘要逐字："This dataset contains both the point-to-point trajectory and periodic trajectory
of two different robot joints under three controllers."；`relatedIdentifiers`：`IsSupplementTo → doi:10.1002/acs.3276`。
★ **检查 27 挂产物**：上方 ★ 块的全部 DataCite 逐字字段（含本行 `relatedIdentifiers`）现可在仓内重跑复核——
`PYTHONIOENCODING=utf-8 python data/probe_kb7_b_group.py` 读 `data/datacite_sciencedb_04148_2026-10-20.json`（9,623 B）
逐字段打印对拍，本轮打印 `[('IsSupplementTo', 'doi:10.1002/acs.3276')]` 与登记值逐字一致（其余字段同轮全部命中），
**打印出来的数字即本仓可重跑产物**（本轮快照 `build/probe_kb7_b_group.out`）。
★ 该 `position error` 主题词是**上游独立证据**，可支持"这批样本含位置误差"这一**数据集级**陈述；
但它**不构成逐列定义**，`q / theta / qd / eq / etheta` 各列的角色与单位仍记「未实测」（KB2 §三）。
★ **母包已按字节核过**：`https://china.scidb.cn/download?fileId=634e4983934f5e4e97ace801`
本会话重下 **50,493,558 B**（与 DataCite 登记 `sizes` 的 50493558 bytes 逐位一致），本地
`md5 = c7506f625dde69a131333d6002f5e6a2`；zip 内 7 个条目、`data/` 下 6 个 `.mat` **全部与本地实体逐字节一致**（见文件级台账 B 组）。

> **2026-10-21 复算注（检查 27）**：母包 zip **未落盘**，本仓没有可重跑产物来复核这条"按字节核过"——
> `probe_kb7_b_group.py` §0 用 glob `data/**/*.zip` 找母包，命中的那 1 份实为 `data/incoming/KUKA_payload_dataset.zip`
> （25,857,481 B，md5 `efe9394bf2579f380832eed6d501c614`，另一对象），⟹ "zip 份数 1" 是**误命中，不构成母包证据**；
> probe §6 已把「母包 50,493,558 B 字节 / md5 c7506f… / zip 内 7 条目 / 6 个 `.mat` 与母包逐字节一致」列为**无法复算**。
> 仓内可复算的只有：DataCite 记录 `sizes` 字段声明值 50493558 bytes（本轮复算成立，字段值非字节实证）。
> ⟹ 本段母包断言降为**未核验**；本地 6 个 `.mat` 实体的字节身份改以 probe §0 打印的各自 B 大小 + md5 为准（可重跑）。
★ **归属提醒（措辞纪律，A-31/A-87）**：这是**机器人关节轨迹实验**（等离子体研究所的机构动力学实验），
**不是半导体产线数据**；对外叙述不得包装成封装设备现场数据。

### 补登记数据集（2026-10-21 补 `.source.txt` 时现场核出，此前台账漏登）

> 发现路径：给 `data/incoming/` 补来源侧车时，按文件名数字前缀反查 DOI，发现**七个此前未登记的
> DaRUS 数据集**在本地已有实体。全部 16 个候选 DOI 于 2026-10-21 逐个现场
> `GET https://darus.uni-stuttgart.de/api/datasets/:persistentId/?persistentId=doi:<DOI>` 复核，
> 落盘 `build/darus_provenance.json`（可重跑：`PYTHONIOENCODING=utf-8 python data/probe_darus_provenance.py`）。
> 下表 `标题/作者/许可/文件数` 全部取自该次实测响应，本会话**未重新下载实体**。

| DOI | 标题（API `citation.fields.title` 逐字） | 作者（逐字） | 上游文件数 | 本地实体 |
|---|---|---|---|---|
| `10.18419/DARUS-3109` | PI velocity controllers comparison | Hinze, Christoph；Zeh, Lukas | 47 | `data/incoming/3152_Readme.md`（**README 正文自称 3109**） |
| `10.18419/DARUS-3152` | Validation data for comparison of SMC-PI controllers vs. P-PI controller | Hinze, Christoph；Zeh, Lukas | 114 | 无（本地只有 3109 的 README） |
| `10.18419/DARUS-3292` | Replication Data for: Increasing the Dynamic Accuracy of Ball Screw Drives with Quasi-Sliding-Mode (qSMC) Position Control | Hinze, Christoph | 51 | `3292_PRBS.mat` / `3292_vel_sweep_s_0_dir_pos.mat` / `3292_params.txt` / `3292_Readme.md` |
| `10.18419/DARUS-3900` | Identification and Validation Data for Robust Inverse Feedforward with Hybrid Modeling | Xu, Haijia；Hinze, Christoph | 47 | `current-hunt/3900_const_vel_110.tab` + 2 个 `.head` |
| `10.18419/DARUS-4075` | Replication Data for: Adaptive Preload Control of Cable-Driven Parallel Robots for Handling Task | Reichenbach, Thomas；Clar, Johannes；Pott, Andreas；Verl, Alexander | 14 | `current-hunt/4075_experiment_{apc,std}.csv` |
| `10.18419/DARUS-5160` | Replication Data for: Compensation of the Transmission Errors in Electrically Preloaded Rack-and-Pinion Drives | Steinle, Lukas | 11 | `current-hunt/5160_Fig6_Path_errors.{head,tab}` |
| `10.18419/DARUS-6333` | Replication Data for: Compensating for Backlash in Rack-and-Pinion Drives Using Gain-Scheduled Cascade Control | Lehner, Jannik | 6 | `current-hunt/6333_figure3_data.{head,tab}` |

★ **一处必须记在案的文件名陷阱**：`data/incoming/3152_Readme.md` 的**文件名前缀是 3152，
正文首行却是 `# Dataset: PI velocity controllers comparison, https://doi.org/10.18419/darus-3109`**。
两者指向**两个不同的数据集**（3152 是 SMC-PI vs P-PI 的验证数据）。本项目按**正文内容**归到 3109。
若按文件名归 3152，侧车就会把 README 挂到错误的数据集上——而 README 正是别人复核的第一入口。

★ **本轮新增的口径纪律（A-123）**：侧车 `original_filename` 一律照本地文件名写并注明「未改名」，
**不再反推上游原名**。理由：`DARUS-5171` 现场 listing 有 3,488 个文件、其中名为 `Export 10.csv`
的不止一个，文件名在上游**不是标识**；反推原名等于把猜测写成事实。标识只认 `dataFile id` / DOI。

★ **仍未核到正式标识的本地实体（如实登记，不猜）**：
`data/incoming/generator_data0001.csv`（无表头 9 列小数，表名含 generator，疑仿真器中间产物，本仓无任何清单指向它）、
`data/incoming/current-hunt/zen3929384_documentation.pdf`（PDF 内嵌 Title 逐字为
`Microsoft PowerPoint - Umrechnung.pptx`、Producer 为 `Microsoft: Print To PDF`，是德语换算讲义，
与伺服波形无关；**文件名暗示的 Zenodo 3929384 本仓未核到对应记录，不据文件名断言 DOI**）、
`data/incoming/17622448_*` 四件（元数据逐字题名 `Industrial Machine Condition Monitoring Dataset`，
作者 Roni Prasetyo 等，为预测性维护表非伺服波形；`17622448_README.txt` 的内容逐字是上游
`404 Record '17622448' has no file 'README.md'` 的失败留存，不是数据集内容）。
以上四类的侧车字段写「未核」并注明已试过什么，**不编造 DOI**（A-67）。

★ DaRUS 系列的 CC BY 4.0 署名要求与上方 Reichenbach 一致；**Zenodo 两个数据集的署名要求不同**：
`10.5281/zenodo.21456277` 作者 Bátrla Adam / Hercík Radim / Byrtus Radek / Majidzadeh Gorjani Ojan（VSB – TU Ostrava），
引用须带该 DOI + CC BY 4.0，**不得**并入 "Reichenbach / University of Stuttgart" 一行。

★ **Zenodo 21456277 的时基不可判定（本会话实测 + 上游原文冲突）**：readme 第 36 行写
`Sample`: controller timestamp in **milliseconds**，第 44–45 行写 "The sampling period is **12 ms** …
approximately **83.3 Hz**"；而本地文件实测 `Sample` 步长**恒为 4**（0 → 21,464，jitter = 0，严格单调）。
⟹ 两个读法：`1 tick = 1 ms ⟹ 250 Hz`（则"12 ms"错）或 `1 tick = 3 ms ⟹ 83.3 Hz`（则"milliseconds"不精确）。
两读法**都不能由本会话证实** ⟹ 该样本的 `fs` 记 `unresolved`，接入前必须由作者或原始工程文件裁定；
在此之前其上任何频域判据（R-11/R-12/R-13 等）一律 `unavailable`，报告只写"时基单位待裁定"，
**禁止**二选一后当成实测值用（呼应硬规则 4「核对判据要匹配文件形态」）。时基矛盾**不影响**它的
硬拒结论：两读法下时长都 ≥ 0.5 s、jitter = 0，行数 5,367，两条口径都过。


## 硬件真值（来自随数据发布的 `CableActuatorTestbed.xml`）

- 电机：Bosch Rexroth **MSK061C-0600-NN**，源文件属性逐字为 `torque_max="32"`（**XML 里无单位属性**，A-78），`n_max=6000 rpm`
- 卷筒版：`gear ratio=5.0`，`r_drum=0.049 m`，编码器换算 `wegaufz/wegaufn = 1000000/171388`
- 直驱版：**无减速器**（`ratio=1.0`，`100000000/85694000`）→ 动态特性接近精密平台

> **A-27 注记（证据纪律，裁决落点 KB7）**：`torque_max=32 Nm` **疑为齿轮输出侧限值**而非电机轴转矩上限，
> 且**电机转动惯量未发布**。使用方凡引用该 `32`（或任何由 `32` 派生的额定量）一律标 `assumed`，
> **不得当实测值**（对齐 C1 `drive.*` 禁默认值冒充实测纪律）。
> 惯量 / 齿轮比缺失时的置信度处理：依赖惯性比的前馈失配、双惯性配对（KB3 R-04）、`inertia_ratio` 类判据
> 一律降 `unverified` 且置信度封顶，只可定性、不得据 `assumed` 值下量化结论；卷筒版 `ratio=5.0` 与直驱版 `ratio=1.0`
> 属数据集发布的构型量，仍可按实测引用。

> **A-70 落档（与 A-27 同一事实链，KB5 §7 #14 的收口在数据集侧的对偶）**：
> `torque_max = 32` 使用方登记为 `meta.drive.rated_torque_N_m = 32.0` + `drive.rated_torque_source = "assumed"`——
> `assumed` 档允许转矩侧 `*_pct` 计算，但**证据层级封顶 T2**，且报告 caveats 必须逐字含
> "额定转矩为假定值，百分比类判据的绝对刻度不可信"（C1 单位规则 / C2 规则 3）；若不接受该解释口径，
> 改写 `null` ⟹ `*_pct` 恒 `null`，只有 `N_m` 分支成立。
> ★ **口径矛盾已裁（A-78）**：本文件上方硬件真值行曾把 `torque_max=32` 写作 `Nm`，而 KB5 §2.0（同源于
> `CableActuatorTestbed.xml` 的解析）记该属性**无量纲**。裁决取 KB5 的读法为**逐字事实**：源文件就是一个
> 没有单位的 `32`，`Nm` 是一种解释而非引用；硬件真值行已改写为 `torque_max="32"`（无单位属性）。
> 使用方若采用 `N_m` 解释，只能在 `meta.drive.rated_torque_N_m` + `rated_torque_source = "assumed"` 下采用
> （⟹ 层级封顶 T2 + 强制 caveat，A-70）；不采用则写 `null`。两读法同归 `assumed`，**任何一侧都不得印成实测额定转矩**（A-27 / A-31）。
- 控制器参数**明文发布**：
  - `velocity-cable-force`：`kp=0.001 ki=0 kd=0`，低通 `0.02 s`
  - `torque-cable-force`：`kff=1.5 kp=0.01 ki=0.1 kd=0.0005`，低通 `0.02 s`
  - **`kff=1.5` 是大于 1 的前馈增益**，是研究前馈失配的天然样本
- 测量设备：Micro-Epsilon **ASCOspeed ASP5500-300**（光学位置测量，`INCFactor=50`）
  + **LSV-2100-30**（电感式编码器）+ 力传感器 + 温度

## 关键：三套独立位置测量

`x_T`（电机轴编码器）、`x_asco_enc`/`x_asco_serial`（光学）、`x_lsv_enc`（电感）。
→ 可直接做**传感器交叉验证**与**绳索滑移/伸长检测**（`x_diff`、`v_diff` 已是现成的差值通道）。
这是 C2 里 `sensor_disagreement` 类特征的真实数据来源。

> **`meta.sensor_config` 归属（A-1 建立，A-68 扩为四值，裁决落点 KB7）**：C1 `sensor_config ∈ {motor_side, load_side, mixed, unknown}`
> （A-68 起为四值，并给位置类通道加可选 `sensor_side ∈ {motor, load, unspecified}`，仅 `mixed` 时必填），
> 它决定谐振/反谐振的先后顺序期望 `f_anti < f_res` 是否成立。本数据集**同时**有电机轴编码器 `x_T`（motor 侧）
> 与负载侧光学 ASCO / 电感 LSV 测量，但**没有任何数据集文档明确声明试验台整体是 motor_side 还是 load_side 构型**。
> → 使用方一律填 `unknown` / 待核，**不得仅因 `x_T` 存在就断言 motor_side**；在拿到文档依据之前也**不得**
> 自封 `mixed`——`mixed` 要求按 C1 派生规则 7 逐通道登记 `sensor_side` 及其来源，本数据集没有这份依据。
> `unknown` 时 KB3 R-04 的顺序项不参与判定、只按幅值与相位评，且结论置信度封顶（与 `mixed` 行为相同，原因不同）。
> （补充：本数据集 fs=1000 Hz、奈奎斯特 500 Hz，kHz 级谐振本就不可见，`f_anti < f_res` 顺序项在这些样本上多为不评估。）

## 实验战役（DARUS-5171 的目录即元数据）

| 战役 | 含义 | 对本项目的用途 |
|---|---|---|
| `2024-07-23_LdaFricIdent`（直驱） | 摩擦辨识，`tau_T` 从 7→60 N·m 线性爬升、`v_T≈0` | **静摩擦/突破摩擦（stiction）判据的真实样本** |
| `PreloadedLuGreFrictionIdent/Validation` | LuGre 摩擦模型参数辨识与验证 | 摩擦模型真值，可反拟合 |
| `PreloadedViscousFrictionIdent` | 粘性摩擦（多预载 WC80…WC180） | 摩擦随预载的系统性变化 |
| `DynCapstanFrictionIdent` | 动态卡普顿（绳-轮）摩擦 | 非线性摩擦 |
| `TempSlip` | **温度相关滑移** | **热漂移判据的真实样本** |
| `StatSlipIdentLda` / `DynSlipIdentLda` / `SlipIdent` | 静/动滑移辨识 | 指令-实际偏差归因 |
| `StatCompensationValid` / `VelDynCompValid` / `PowerDynCompValid` | **补偿有效性的验证实验** | 与本项目"验证门控"同构，可对照 |
| `CableRobotProfileFullIdent` | 绳索机器人轨迹辨识 | 多轴/路径语境 |

`WC70/WC80/WC105/WC125/WC130/WC155/WC180` = 卷筒摩擦工况；
`F30000/F120000/F300000` = CNC 进给 mm/min → 0.5 / 2 / 5 m/s。
控制模式分 `Torque_based` 与 `Velocity_based` 两套目录 —— **同一工况、两种控制结构**，
是"结构差异如何改变跟随误差"的天然对照实验。

## TwinCAT Scope View CSV 的真实结构（实测）

```
行 1   Name<TAB>Measurement
行 2   File<TAB>[REDACTED_HOST_PATH]\Export 10.csv      ← 原始路径泄露，须脱敏
行 3   Starttime of export<TAB>[REDACTED_WALLCLOCK]<TAB>[REDACTED_WALLCLOCK]<TAB>[REDACTED_WALLCLOCK]
行 4   Endtime of export<TAB>...
行 5-6 空
行 7   表头：Name<TAB><符号名> 交替
行 8   SampleTime[ms]<TAB>1  交替
行 9   SymbolBased<TAB>True
行 10  SymbolName<TAB>Measurement_Connector.dForce_load   （DARUS-3600）
       或 Data-Type<TAB>REAL64                             （DARUS-5171）
行 11  NetID<TAB>[REDACTED_ADS_NETID]
行 12  Port<TAB>851
行 13  空
行 14+ 数据：col0=SampleTime，之后 (SampleTime, value) 成对交替
       ⇒ names[k] 的真实列号 = 2k+1
```

- 分隔符：TAB；编码：UTF-8；数值行数示例 18650 行 / 64 列 / 32 通道
- **两套命名规范并存**：`dPosition_test`（3600）vs `x_T`（5171）→ 解析器必须双词表映射
- `Starttime of export` 是 .NET ticks + 德语本地化日期，**时区未标注** → 只能当相对时基用

## 已实测的能力边界（硬约束，写报告必须遵守）

1. **`SampleTime` 恒为 1 ms → fs=1000 Hz，奈奎斯特 500 Hz，`reliable_band_hz = 400 Hz`（C2 规则 7 频段门禁）。**
   ★**已裁 A-94（本条由"数据集级"收窄为"样本级"）**：以上**只适用于 TwinCAT Scope View 样本**
   （DARUS-3600 / DARUS-5171 的 `Export NN.csv`，本会话逐份实测 `SampleTime[ms] = 1`）。
   频带门禁一律按**样本自身 `fs`** 判定，**禁止**按数据集名整体标 blocked。
   反例（本会话实测）：DarUS-2563 / 3003 / 3252 的 dSPACE `.mat` 样本内含 **4 kHz 测量栅格**
   （`Raster = "HostService"`，292,080 / 44,001 / 8,556 点，jitter ≤ 1.2e-6，严格单调），
   其 `reliable_band_hz = 3.2 kHz` ⟹ **R-03/R-04 的 `band⊥ = 2000 Hz` 在这些样本上门禁通过**。
   但通过频带门禁**不等于**能给归因：这批样本同样**没有 `cur_q`**（12 份候选逐列名扫描无一命中电流语义），
   故两条规则在这些样本上落 `unavailable[]`（`reason = "band_gate_pass_channel_gate_fail"`），
   **禁止**写成"未发现共振"。 DARUS-4224 的 xlsx 为 2 kHz（`dt = 0.5 ms`），DARUS-3759 为 2 kHz。
   对 `fs ≤ 1 kHz` 的样本（含 3600/5171 全部 Scope View 样本），A-65 原文照旧：
   这类判据在 T1-a 数据层面**不可达**，报告只能写"该判据在 T2 文献上成立，本数据集频段不足以检验"
   （`unavailable` + `blocked_rules`），**禁止**写成"未发现异常"。
   C3 示例里那条"1181 Hz 机械谐振"的样例在 1 kHz 样本上物理不可见——
   必须换成 <400 Hz 的例子，或明确标注该例来自更高采样率的其它来源（2 kHz / 4 kHz 样本上可见）。
   **多速率栅格的接入约束（A-94 派生）**：`.mat` 样本的 `fe` 通道在 1 kHz 栅格、测量通道在 4 kHz 栅格，
   跨栅格比较必须显式重采样并登记方法（本项目默认 nearest；实测 `e_x_T ≡ traj_KGT[0] − x_meas_table(nearest)`
   在 2563 偏差 2.6e-10、3003 偏差 5.8e-15、2563_SP_v100 恰为 0.0 ⟹ nearest 不引入语义误差）。
   `OnChange` 栅格是**离散事件栅格**（2563 只有 26 点、jitter 0.221），**不是**波形载体，
   不得当作第三条时基参与 `fs`/时长/抖动判定，也**不得**用它去触发"时基非严格单调"的硬拒。
2. **触发门控是真实陷阱**：`Export 10.csv`（id 244531）18650 行中
   `bTrigger_Record` 仅 **26.8%** 为真，`bTrigger_Export` 仅 **2.7%**。
   不处理触发列会把 4 倍于有效数据的垃圾算进 RMS/频谱。
   作者自己的 `catcsv2cell.m` 正是靠 `trig_record~=0` 过滤——这条必须复刻。
3. **`bMovingForward` 符号修正**：编码器速度需乘方向符号才是带符号速度（作者脚本第 41-45 行）。
   漏掉会得到"速度恒正"的假象。
4. **数据行数 ≠ 有效行数**：末尾有空行；列数校验要用 `>= 2*len(names)` 而非 `+2`。
5. 部分文件首段 `trig_rec=0`（如直驱文件前 809 行）——是预触发/静止段，不是解析错误。

## 文件级台账 A 组（DaRUS + Zenodo；2026-10-20 逐文件实测；`verified_by` 一律 self，未经复验的数字不入表）

**登记纪律**：本表每行的 `fs / 行数 / 差异行数 / 恒等式偏差` 都是主线程在本地实体文件上亲自跑出来的；
上游 `md5 / filesize / license` 由主线程现场 `curl` DaRUS `api/datasets/:persistentId/versions/:latest`
与 Zenodo `api/records/<id>` 取得并与本地 `md5sum` 对拍。**子智能体/第三方会话的报告对我们只是 `public-doc`，
`verified_by ≠ self` 的数字不计入本表**（A-88/A-89）；本轮对 `data/research_fe_current.md` 的 12 份候选
做了独立复验，**其中 load-bearing 结论全部复现**（详见 `data/VERIFICATION-2026-10-20.md` 第七节），
唯一新发现的独立事实是 6114 `ObserverTestSet.tab` 的**上游登记值与实发字节不一致**（见表下注）。
★ 本组「对拍」列一律指**主线程实测**；有 7 行对应的 incoming 文件**无 sidecar**（见「核对主体分级」），
主线程实测不代偿 sidecar 缺口，二者是两件事。
★ **检查 27 挂产物（A-104 先例）**：本组所引 DaRUS-5171/CDD 会话数字（`data/research_5171_cdd.md` 一系）
现挂仓内可重跑产物：`PYTHONIOENCODING=utf-8 python data/probe_5171_identities.py`，在 `data/incoming/` 实体与
`data/incoming/daRUS5171_listing_2026-10-20.json` 上逐条打印 成立 / 不成立 / 无法复算——**打印出来的数字即本仓可重跑产物**
（本轮快照 `build/probe_5171.out`（552 行）**末尾由脚本自数并打印**：对拍判定 **成立 206 ‖ 不成立 9 ‖
无法复算 12**，另有脚本自设的子判定 12 行（不是文档断言，勿引用为对拍数）——判定行口径与对拍/子判定的
分界定义在 `data/probe_tally.py`；此前正文手点的「219/24/12」是混合口径（把关键字出现在行中、以及子判定行
一并计入），2026-10-21 起一律改引脚本自己打印的那三行，不再人工点数。不符项已在该报告各节就地挂
「本仓复算更正」引文块，未带产物的数字按检查 27 一律按 `public-doc` 处置、不计入 k）。

| # | 本地文件 | 上游标识 | fs（实测） | 行数 | fe | cur_q | vel_fb | 上游 md5 对拍 | 硬拒 | 结论 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `raw/Export10_244531.csv` | 3600 / 244531 | 1000 Hz | 18,651 | **无**（`*_tar ≡ *_fb`） | 无 | 有 | ✔ | 过 | 解析/触发门控真值；有速度+力误差 |
| 2 | `raw/DD_head.csv` | 5171 / 394008 前 400,001 B | 1000 Hz | 813 | 母本有 | 无 | 有 | ✔（前缀逐字节） | **拒**（行数<2000） | 只作表头/词表回归，接母本 |
| 3 | `incoming/393964_Export34_LdaFric_RW.csv` | 5171 / 393964 | 1000 Hz | 16,754 | 有（4,945 行差） | 无 | 有 | ✔ | 过 | 真 fe |
| 4 | `incoming/394008_Export10_CDD_RW.csv` | 5171 / 394008 | 1000 Hz | 75,858 | **有**（64,284 行差 84.7%，峰值 1.6 mm） | 无 | 有 | ✔ | 过 | **直驱台架真 fe 最强样本** |
| 5 | `incoming/current-hunt/3759_Fig4_Path_errors_50mm.tab` | 3759 | **2000 Hz** | 40,000 | **有**（`e_x ≡ x_d − x_T`，偏差 4e-13） | 无 | 无 | ✔ | 过 | **当前最干净的真 fe** |
| 6 | `incoming/4152_Sine_0_output_00.txt` | 4152 | 250 Hz | 14,993 | 无 | **有**（mA，249 列名） | 无 | ✔ | 过 | **唯一真机实测电流** |
| 7 | `incoming/2563_validate_…LDAComp.mat` | 2563 / 144244 | 1 kHz + **4 kHz** | 73,020 / 292,080 | **有**（`e_x_T` 恒等式偏差 2.6e-10） | 无 | 有（4 kHz） | ✔ | 过 | A-94 频带松绑样本 |
| 8 | `incoming/2563_SP_v100_forw.mat` | 2563 / 134116 | 1 kHz + **4 kHz** | 8,310 / 33,240 | **有**（偏差恰 0.0） | 无 | 有 | ✔ | 过 | 同上 |
| 9 | `incoming/3003_vel_sweep_s_400_dir_pos.mat` | 3003 / 134473（3252 / 168731 同字节） | 1 kHz + **4 kHz** | 11,001 / 44,001 | **有**（偏差 5.8e-15） | 无 | 有 | ✔ | 过 | 同上 |
| 10 | `incoming/3252_dist_milling_PPI.mat` | 3252 / 168767 | 1 kHz + **4 kHz** | 2,139 / 8,556 | 有（自算，2,139/2,139 行差） | 无 | 有 | ✔ | 过 | 无 `e_x_*` 通道 |
| 11 | `incoming/4224_Fig_3…` | 4224 / 294888 | 2000 Hz | 8,001 ×6 sheet | **有**（`d_x_T` 全非零） | 无 | 无 | ✔ | 过 | 上游无 README ⟹ 逐列语义未发布 |
| 12 | `incoming/4224_Fig_5_and_6…` | 4224 / 294896 | 2000 Hz | 36,001 ×3 | 有 | 无 | 无 | ✔ | 过 | 同上 |
| 13 | `incoming/4224_Fig_7…` | 4224 / 294889 | 2000 Hz | 16,001 ×3 | 有 | 无 | 无 | ✔ | 过 | 同上 |
| 14 | `incoming/4224_Fig_8_P2P…` | 4224 / 314445 | 2000 Hz | 4,500 ×3 | 有 | 无 | 无 | ✔ | 过 | 同上 |
| 15 | `incoming/6114_x_velSweep…csv` | 6114 / 548584 | 1000 Hz（ISO 列） | 11,000 | **有**（`x_x_d` vs `x_x_l` 11,000/11,000） | 无 | 有 | ✔ | 过 | ⚠ `b_x_d ≡ b_x_m` 镜像陷阱 |
| 16 | `incoming/6114_lsmc.csv` | 6114 / 548600 | 1000 Hz（ISO 列） | 3,000 | 有 | 无 | 有 | ✔ | 过 | — |
| 17 | `incoming/6114_ObserverTestSet.tab` | 6114 / 548615 | **不可实测（无时间列）** | 9,978 | 有（9,978/9,978 行差） | 无 | 无 | **✘ 见注** | 时基未实测 | 用前须解决 fs 来源 |
| 18 | `incoming/KUKA_payload_dataset.zip` → `Robot_R2/collector_1014_5.csv` | zenodo 21456277 | **unresolved**（250 Hz / 83.3 Hz 两读法） | 5,367 | **无位置列** | **有**（`Iststrom_A1..A6 (A)`） | 无 | ✔（母包） | 过 | 电流单位明写安培；时基须裁定 |
| 19 | `incoming/wiredrawing_dataset.xlsx` | zenodo 21526135 | 30 s/样本 | 47,706 | 无 | 有（8 路块电流） | 无 | ✔ | **拒**（jitter 192.9；分段后仍拒） | 不接入 |
| 20 | `incoming/2563_LDD_Transfer_function…csv` | 2563 / 144246 | 16,000 Hz（`;` 分隔 + 逗号小数，`column_name:ms`） | 2,047 | 无 | 无 | 无 | ✔ | **拒**（时长 0.1279 s + 角色全缺，两数现由工具自印） | 不接入 |
| 21 | `incoming/17622448_dataset.csv` | zenodo 17622448 | — | 38,390 | 无 | 无 | 无 | 上游无 md5 | **拒**（时基非严格单调；`dt_jitter_ratio` 实测 534.895＝epoch 秒差分口径，旧登记 1.62 不可复现，见注 21R） | 不接入 |
| 22 | `incoming/generator_data0001.csv` | **未登记** | **不可实测（无时间列、无表头）** | 3,789 | 不可认定 | 不可认定 | 不可认定 | — | **拒**（来源未登记） | 不接入 |

**表下五注**（注 20 / 注 21R / 注 17 的 R-6·R-7·R-3 三条解析器修复合并登记为 KB0 **A-112**）：
- **注 20（"时长 0.128 s"此前没有工具载体）**：该文件是 `;` 分隔 + **逗号作小数点**
  （`0,000000;19,999996;-20,172794`），`validate_raw.py` 的取值路径一直认逗号小数、**布局判定**只认点十进制
  ⟹ 2026-10-21 复算时整份判 `layout=unparsed`，台账那句实测因此重跑不出来（检查 27）。补
  `sniff_decimal_comma()`（即 KB2 的 R-6）后工具自印：**2,047 行 / fs 16,000 Hz / 抖动 0.000 /
  时长 0.127875 s / 单调 Y / 2 列全未映射**，红线「有效时长<0.5s」+「cur_q/vel_fb/fe 未识别」——
  **与台账原句同向、数值同一**（0.128 s 那句一直是对的，缺的只是载体）。回归载体：
  `tests/test_validate_raw_intake.py::test_real_2563_ledger_numbers_are_self_printed` +
  快照 `build/validate_incoming_after_r7.txt`。
- **注 21R（撤销一个 jitter 数字，不撤销结论）**：原登记「jitter 1.62」**不可复现**——本仓现口径是
  `dt_jitter_ratio = pstdev(dt)/|median(dt)|`，而 R-3 之后该文件的 ISO 文本时间列被转成 epoch 秒参与差分，
  工具打印 **534.895**（`data/validate_raw.py data/incoming/17622448_dataset.csv`，见
  `build/validate_incoming_after_r7.txt`）。1.62 出自哪套口径无从考证，按 A-104 ② 的纪律**只登记"不可复现"、不猜成因**。
  **结论方向不变**：该文件另有「时基非严格单调」独立成立（38,390 行 epoch 差分 `dt_min = −65,293,440 s`、
  `dt_max = +65,269,080 s`、`dt 中位 = 50,820 s ≈ 14.1 h`、跨度 28,051,020 s ≈ 324.7 天），照旧硬拒、不接入；
  且 17/17 列未映射（`MachineCode/OilLevel_L/LoadPercent` 这类是设备状态与统计列，不是波形量）。
  ★ **这组数字顺带把拒因升级得更根本**：中位步长 14 小时、正负步长同量级 ⟹ 那一列是**不等间隔的状态记录时刻**，
  本就不是采样栅格，"抖动超阈"只是它的表象。原句尾注「构造数据」本轮**未复算**（无上游文档佐证），
  按检查 27 降为**未核验**，不作为契约或规则的依据。
  ⚠ 口径说明：`dt_jitter_ratio` 本身无量纲（`pstdev(dt)/|median(dt)|`），单位换算不会改变它——
  ⟹ 1.62 与 534.895 的差**只能**来自"哪一列、哪一套差分序列"，而不是 ms↔s。既然 1.62 的序列无法考证，
  两个数就**不是同一个量的两次读数**，不得并列成"变差了/变好了"，也不得拿本行的 534.895 去和别的行的
  抖动数横比（那需要先确认两侧都是本工具现行口径打印的）。
- **注 17（上游登记值 ≠ 实发字节）**：6114 `ObserverTestSet.tab` 的 API 登记为
  `filesize = 367,389 / md5 = 56b18a8729803f71deae031a04445cad`，而本地实体为
  `367,419 B / md5 = fd18abe49bf122f6f293289444e20adb`（主线程两侧都实测过：`md5sum` 复算 + 现场 API）。
  差 30 B，疑为换行符处理。**处置**：登记为 `upstream_checksum_mismatch`，`source_tier` 不因对拍失败而下调
  （文件名/大小/目录三项都指向同一上游文件），但**任何引用该文件 bytes 的哈希结论都不得外推到上游原始件**。
  ★ **2026-10-21（KB2 R-7）本行的"时基未实测"现在由工具自印且措辞改对**：该件表头只有
  `v_des / a_des / j_des / x_des / x_act` 五列、无一像时间 ⟹ 现在打印
  「时基：无时间列（fs/时长/抖动/单调一律不作结论）」+ 拒因「无时间列可解析（时基不可得，不作单调性结论）」。
  在此之前它报的是「时基非严格单调」——**那是把"无从判定"写成了"判定不合格"**（对一列数值下了时基判决），
  C1 §`time_bases` ⑤ 明令禁止这种写法。verdict 仍 reject、行数 9,978 与 fs 来源待解决两格不变。
- **注 5/6 的编号列数与语义**：`4152_Sine_0_output_00.txt` 逐列名为 `Time [s] | Goal Current [mA] |
  Pres. Current [mA] | Pres. Voltage [V] | Pres. Position [rad] | Pres. Velocity [rad/s]`（抄自文件首行原文）。
  `Goal Current` 是**设定值**、`Pres. Current` 是**实测**——两者都算"电流通道"时必须标明角色，
  否则会把设定值当反馈证据（A-87 真值三分法）。
- **注 22**：`generator_data0001.csv` 无表头、9 列、来源未登记；检索线索指向仿真/生成数据，
  按 A-67 **不得**凭线索写成任何正式标识。

## B 组台账：ScienceDB 机器人关节样本（2026-10-20 主会话全量核验，`verified_by = self`）

登记纪律：本组 12 个文件的 `fs / 行数 / 时长 / 抖动 / 通道清单 / 统计量 / 母包对拍`
**全部由主线程在本会话亲自跑出**（`data/_audit_staging_mat.py` 用 `scipy.io.loadmat` 读 MATLAB v5；
`data/validate_raw.py` 读派生 CSV；母包按字节重抓比对），**不含任何转述数字**。
6 个 `.mat` 是上游 zip 的原始成员（`original_filename` 逐字对应；**「与母包逐字节一致」2026-10-21 起降为未核验：母包 zip 未落盘、无重跑产物，见 ★DataCite 块下复算注**）；
6 个 CSV 是**本地从 .mat 转换的派生件**（sidecar 明写 `original_filename: NONE（…转换而来）`），
按 A-88 同源派生，**哈希相符不计入独立核对 k**。

| # | 本地文件 | 上游标识 | fs（实测） | 行数 / 时长 | fe | cur_q | vel_fb | 上游对拍 | 硬拒 | 结论 |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | `staging/原始mat/Controller1Periodic.mat` | sciencedb.04148 / `data/Controller1Periodic.mat` | **500.000 Hz** | 200,001 / **400.000 s** | **待人工复判** | 无 | 无 | 未核验（母包未落盘、无重跑产物，见 ★DataCite 块下 2026-10-21 复算注） | 1–5 过，**6 开** | 时基合规；红线 6 因命名族缺口开火 |
| B2 | `staging/原始mat/Controller1Point2Point.mat` | 同上 / `Controller1Point2Point.mat` | 500.000 Hz | 100,001 / **200.000 s** | 待人工复判 | 无 | 无 | 未核验（母包未落盘，同 B1 注） | 同上 | 同上 |
| B3 | `staging/原始mat/Controller2Periodic.mat` | 同上 / `Controller2Periodic.mat` | 500.000 Hz | 200,001 / 400.000 s | 待人工复判 | 无 | 无 | 未核验（母包未落盘，同 B1 注） | 同上 | 同上 |
| B4 | `staging/原始mat/Controller2Point2Point.mat` | 同上 / `Controller2Point2Point.mat` | 500.000 Hz | 100,001 / 200.000 s | 待人工复判 | 无 | 无 | 未核验（母包未落盘，同 B1 注） | 同上 | 同上 |
| B5 | `staging/原始mat/Controller3Periodic.mat` | 同上 / `Controller3Periodic.mat` | 500.000 Hz | 200,001 / 400.000 s | 待人工复判 | 无 | 无 | 未核验（母包未落盘，同 B1 注） | 同上 | 同上 |
| B6 | `staging/原始mat/Controller3Point2Point.mat` | 同上 / `Controller3Point2Point.mat` | 500.000 Hz | 100,001 / 200.000 s | 待人工复判 | 无 | 无 | 未核验（母包未落盘，同 B1 注） | 同上 | 同上 |
| B7–B12 | `staging/电机位置与跟随误差_公开数据集_Controller{1,2,3}{周期,点位}轨迹.csv` | **无上游对应件**（本地由 B1–B6 转换） | 500.000 Hz | 同 B1–B6 | 待人工复判 | 无 | 无 | 与母 `.mat` 逐行比对 max\|Δ\| = **5.0e-8**（`tout` 5.7e-14） | 同上 | 派生件；**接入应引 .mat 而非 CSV** |

**B 组实测要点（全部 `verified_by = self`；母包对拍一项除外，2026-10-21 降为未核验）**：
★ **检查 27 挂产物**：以下要点数字现可在仓内重跑对拍——`PYTHONIOENCODING=utf-8 python data/probe_kb7_b_group.py`
（读 6 个本地 `.mat` + 6 份派生 CSV + `data/datacite_sciencedb_04148_2026-10-20.json`，逐字段打印 成立 / 不成立 / 无法复算；
本轮快照 `build/probe_kb7_b_group.out`（356 行）**末尾由脚本自数并打印**：对拍判定 **成立 86 ‖ 不成立 7 ‖
无法复算 6**，另有脚本自设的子判定 26 行（「差一个常数」一类，不是本组登记的断言，勿引用为对拍数）；
每个文件的每条恒等式还另印一行「成因口径」（`|残差| > 1e-3` 的行数与 argmax 行号，无判词、不计入判定）。
判定行口径与对拍/子判定的分界定义在 `data/probe_tally.py`——此前此处手点的「106/7/6」把子判定行
错计进了「成立」（`…「差一个常数」不成立` 行尾也含「成立」二字），2026-10-21 起一律改引脚本自己打印的那三行），
**打印出来的数字即本仓可重跑产物**。
- **时基是全库最干净的一批**：6 个 `.mat` 的 `dt` 恒为 `0.002 s`（复算：按 9 位打印口径恒 0.002 成立；按 17 位口径 `dt ∈ [0.0019999999999527063, 0.0020000000000095497]`，非逐位恒定，打印口径未标注），`dt_min = dt_max = 0.002`（同打印口径），
  `dt_jitter_ratio` 实测 **7.557e-12**（周期，200,001 行）与 **4.505e-12**（点位，100,001 行），
  严格单调 ⟹ 实质为 0，远优于 KB2 §5.1 的 ≤0.2 门限。`tout` 覆盖 `[0, 400.000]` / `[0, 200.000]` s。
- **通道**：每个文件 11 个变量（`tout` + 10 个数据列，逐字）：
  `tout, q1, q2, j1_qd, j2_qd, theta1, theta2, j1_eq, j2_eq, j1_etheta_pos, j2_etheta_pos`，
  全部 `float64`、`shape = (N,1)`、**NaN 计数 0**。CSV 表头与 `.mat` 变量名**完全一致**（11 列，派生无损）。
- **电流语义扫描**：`cur / strom / amps / i_d / i_q / amper / acur` 七类词在 10 个数据列上**零命中**
  ⟹ `cur_q` 确定**不在**这些文件里（这一条是"缺席"，由列名穷举支撑，不是猜测）。
- **误差列身份未能证实（关键）**：命名暗示 `*_eq`（关节位置误差）与 `*_etheta_pos`（电机角度位置误差），
  DataCite 主题词也含 `position error`，但主线程穷举 90 个有序列差 × 6 个文件后，
  **原文试过的 `theta1 − q1` 这一组候选没有一条成立**（成立的是另一条，见下方 ★）：
  `j1_etheta_pos ≡ theta1 − q1` 的 max\|残差\| 在 B3/B5/B2/B4/B6 为 2.0e-3 ~ 5.9e-3（复算值 **3.134e-3 ~ 5.948e-3**；下界 2.0e-3 复算未触及、上界原值口径 5.948e-3 略超，原句未标注区间口径），
  而在 **B1 为 4.002e-01**（复算 0.4002006184 命中；与信号同量级 5.99e-1）；`j1_eq ≡ theta1 − q1` 在 **B1 为 3.000e-01**（复算 0.3000006714 命中）、其余 3.6e-3 ~ 2.0e-3（复算值 **1.998e-3 ~ 4.329e-3**；上限 3.6e-3 被复算值 B2 4.329e-3、B3 3.679e-3、B6 3.878e-3 超过，原登记上限偏低）。
  **同一恒等式在 6 个文件间不自洽 ⟹ 不能把 `*_etheta_pos` 认定为 `theta1 − q1`**，
  故 `fe` 角色记 **待人工复判**（须按上游文档逐列定义裁定），**不得**按命名直接当 `fe` 用。
  同理，`j1_etheta_pos` 的量程（min/max ≈ −3.4e-3 / 0.400）与 `theta1`（≈ −6.7e-7 / 0.599）**不同**（复算证实"不同"成立；这两个端点数是 **B1** 的实测值——B1 `theta1 [-6.714e-7, 0.5986]`、`j1_etheta_pos [-3.392e-3, 0.4002]`，原句未标注所属文件），
  也**不支持**把它当 `pos_fb` —— `validate_raw.py` 依命名把它映射为 `pos_fb` 属**词表猜测**，本台账不采纳。
  ★ **B1 的大残差不是首行伪影（2026-10-21 复算改判）**：上一轮 probe 的 §3 结论行曾写「B1 的 4.002e-01 / 3.000e-01
  全部来自首行的常数偏置」，**与它自己打印的数字矛盾**（去掉 median 常数偏置后 max\|残差\| 仍有 0.3998 / 0.2995）。
  现按打印口径改判为**整段瞬态差异**：`|残差| > 1e-3` 的行数在 `j1_etheta_pos` 为 **115,786 / 200,001**、
  `j1_eq` 为 **93,551 / 200,001**（B1，见「成因口径」行）；脚本已删除那句无载体的成因，改为打印行数与 argmax 行号。
  ★ **`j1_eq ≡ j1_qd − q1` 成立（2026-10-21 裁决，上一轮只挂证据未裁）**：穷举 90 个有序列差 × 6 文件，
  `j1_eq` 的最小行级 max\|残差\| 在 **B1–B6 全为 0**，且每名之后立刻跳到 ≥ 1.1e-3 ⟹ 六件文件里**恰有这一条**成立恒等式。
  按 A-105 ②/③ 的口径，`j1_eq` 是 `j1_qd` 与 `q1` 的**线性组合、零独立信息**：接入时**不得计入独立测量数**、
  不得充当 `pos_fb` 的互证第二路（把它当第二次测量会凭空造出一路"分歧证据"）。
  `j2_eq` 命名同构但脚本未对其穷举 ⟹ 记**未复算**，接入前须同法核。`fe` 角色**维持待人工复判不变**
  （`j1_etheta_pos` 没有任何 0 残差候选，其身份仍未由上游逐列定义证实）。
- **红线判定**：1（行数）2（时长）3（抖动）4（NaN）5（动态分段）**全过**；
  **第 6 条开火**，脚本判词逐字为
  `cur_q/vel_fb/fe 未识别（8/10 列未映射，疑为命名族缺口而非数据缺失，须按数据集文档人工复判）`
  ⟹ `verdict = reject`。**该 reject 的成因是"我方词表认不出这套命名"，不是"数据里没有"**
  （A-88：不得把我们没证明的缺席写成事实）。
- **频带**：`fs = 500 Hz` ⟹ `reliable_band_hz = 400 Hz`，低于 R-03/R-04 的 `band⊥ = 2000 Hz`
  ⟹ 该族样本上共振类判据走 `unavailable`，属 A-94 的**样本级**判定（不是数据集级）。

**本组归属说明**：12 个 staging 文件目前**不进 `data/raw/`**，停在 staging。
理由：红线 6 的成因是词表缺口，而词表补全属 KB2 解析器待办（见下「R-4」），不是数据问题；
先把词表与逐列定义补上再决定接入，可在接入卡上少写一次「待人工复判」。

## 核对主体分级（`verified_by` 不可转借，A-89）

本项目对"谁核的"与"核了什么"分两栏，**sidecar 里写的 `verified_by` 只能算该 sidecar 作者的陈述**，
主线程台账另设一栏独立记「主线程核对」：

| 标记 | 含义 | 计入独立核对 k |
|---|---|---|
| ✔ 全项复测 | 主线程在本地实体上重跑了该行**全部**登记数字（fs/行数/时长/抖动/NaN/角色/对拍） | 是 |
| ✔ 载荷项复测 | load-bearing 结论（能否接入、硬拒与否、fe/cur 角色、fs）已复测，其余数字转述 sidecar | 仅载荷项 |
| — 转述 | 主线程未跑，数字来自 sidecar 或第三方会话 | 否 |

**现状盘点（2026-10-20）**：
- `data/raw/` 13 个文件 + 13 个 sidecar：`Export10_244531.csv`、`DD_head.csv`、4 个仪器导出件
  （PMU / SEFRAM / Rigol / Tektronix）的 sidecar `verified_by` 写 `self（…本会话…）`，
  其中 4 个仪器件**明写**核对记录落在 `data/VERIFICATION-2026-10-20.md`；记为 **✔ 载荷项复测**。
- `data/incoming/` 12 个 v2 sidecar：`verified_by` 同样写 `self（…本会话亲自执行…）`，但其中
  "本会话"是**并行智能体的会话**——它们在 `retrieved_by` 里写明"本地字节的初次下载由并行智能体会话完成"，
  在 `verified_by` 里写明"并行智能体的初次下载不记入 self"。
  ⟹ **主线程台账不得转借这个 `self`**。这 12 份的 load-bearing 结论（时基、fe/cur 角色、硬拒、md5）
  已由主线程独立复测（见 A 组表与 `data/VERIFICATION-2026-10-20.md` 第七节），记 **✔ 载荷项复测**。
- B 组 12 个 ScienceDB 文件：母包按字节重抓、6 个 `.mat` 逐字节对拍、6 个 CSV 与 `.mat` 逐行比对，
  全部主线程亲自执行 ⟹ 记 **✔ 全项复测**（唯一一组）。
  ★ **2026-10-21 复算注（检查 27）**：其中「母包按字节重抓 / 与母包成员逐字节」两项因母包 zip 未落盘、无重跑产物，
  **降为未核验**（B1–B6 对拍格已改）；其余项（本地 `.mat`/CSV 的时基、通道、统计量与 DataCite 字段对拍）已挂
  `PYTHONIOENCODING=utf-8 python data/probe_kb7_b_group.py`（见 ★B 组实测要点）——**✔ 全项复测按此口径执行**，母包部分不再背书。
- **12 个 incoming 文件无 sidecar**（`393964_Export34_LdaFric_RW.csv`、`394008_Export10_CDD_RW.csv`、
  `394085_CableActuatorTestRig.xml`、`KUKA_payload_dataset.zip`、`wiredrawing_dataset.xlsx`、
  `17622448_dataset.csv`、`2563_LDD_Transfer_function_Force_controlled.csv`、`generator_data0001.csv`
  及 4 个 Readme/JSON 辅助件）⟹ 按"无 sidecar 不可进接入卡"的纪律，它们**暂时不能进 KB2 §4 接入卡**；
  A 组表中 #3 #4 #18 #19 #20 #21 #22 的"对拍"列因此记为**主线程实测**而非 sidecar 支撑，
  其 sidecar 缺口是**独立的待办**，不因主线程已实测而自动补齐。

**由此产生的解析器待办（KB2 §4 族卡侧）**：
- **R-4 机器人学命名族**：新增 `tout / q / theta / qd / eq / etheta` 词表，
  但**必须配上游逐列定义才能定角色**——本轮实测已证明"按名字猜"会猜错
  （`j1_etheta_pos` 被猜成 `pos_fb`，实测量程与 `theta1` 不符）。
- **R-5 `rate` / `amp` 子串误报 —— 已修（2026-10-21，任务 #15）**：原句三条实测误报（`OilLevel_L → vel_fb`、
  `FailureRate → vel_fb`、`Timestamp → cur_other`）改为**整词 token 判定**后实测全部 `(None, None, False)`；
  `--selftest` 由 22 → **29 通过 / 0 失败**（含 R-6/R-7 的新用例，汇总由脚本自数），
  `tests/test_validate_raw_intake.py` **15 例**。修法按裁定走 token 化（与 `name_tokens` 共用
  `split_name_tokens`），**没有再加正则补丁**。
  ⚠ **改名（A-54 单一名字律）**：接入层的猜测器原名 `channel_role`，与引擎侧
  `src/axiscope/mapping.py::channel_role`（审计**之后**定 canonical/extra、返回字符串）同名不同物，
  现改名 **`guess_role_from_name`**（审计**之前**按列名猜量名/方向、返回三元组）。
  **连带如实登记两处**：①裸 "rate" 已从 vel 整词表剔除（留在表内则 `FailureRate` 的整词 "rate" 照样命中），
  `Rate_asco / dRate_asco` 因此落 unmapped——vel_fb 角色仍由各 `velocity` 列给出，硬拒结论不受影响，
  但**不得**把"未映射"读成"数据里没有速度"；②`dRate_asco` 在引擎侧 `mapping.py` 仍登记为 `vel`
  「速率（单位存疑）」，而 KB2 §3.1 称其为 **ASCO 计数率** ⟹ 同列两名互斥，**待人工复判**（不得由脚本挑一个）。

## 能力格：`f(fe, cur_q)` —— 本项目最想要、公开数据给不了的那一格

| | **有真 `cur_q`（实测电流）** | **无 `cur_q`** |
|---|---|---|
| **有真 `fe`（cmd ≠ fb 或现成误差通道）** | **`not_mappable(公开数据无此样本)`** | 12 份：#4 #5 #7 #8 #9 #10 #11–#16（+ #17 待解决时基） |
| **`fe` 待人工复判（列名暗示有、恒等式不成立）** | — | **B1–B6（+ 派生 B7–B12）** ScienceDB 机器人关节 500 Hz 样本 |
| **无 `fe`** | #6 4152（250 Hz）、#18 KUKA（时基 unresolved） | #19 #20 #21 #22（硬拒） |

**结论（措辞按 A-31，不得升格）**：截至 2026-10-20，本会话已核验的 **28 份独立公开样本**
（对应 34 个本地文件；B 组 6 个 CSV 是同一批 `.mat` 的本地派生件，不另计样本）中，**没有一份
同时携带真实位置跟随误差与真实电流通道**。这不是"没找到"，是**核验范围内的判定**：每个样本的
列名/通道名我都扫过电流语义词表（`cur / strom / amps / amper / acur / i_d / i_q`），
DaRUS 与 ScienceDB 两族全部样本最接近的是 `M_KGT_act`（转矩类，**上游未发布单位**）与 `F_*`（力），
两者都**不得**当电流用；B 组的 10 个数据列更是**七类电流词零命中**；
唯一单位明写安培的两个样本（KUKA、wire-drawing）都没有位置通道。
⟹ KB8 案例集里"真 fe + 真电流"这一格写 `not_mappable`，理由栏逐字写
"公开数据无此样本（2026-10-20 主会话核验 28 份独立样本 / 34 个本地文件，见 KB7 文件级台账 A+B 组）"，
**禁止**写成"该能力已验证"或"暂未找到合适数据"（后者把已完成的核验说成未完成）。

★ **B 组为什么不进"有真 fe"格**：上游 DataCite 主题词含 `position error`、列名含 `*_eq` / `*_etheta_pos`，
按命名像是误差通道；但主线程复算的候选恒等式在 6 个文件间**不自洽**（B1 残差 3.0e-1 ~ 4.0e-1，
B2–B6 残差 2.0e-3 ~ 5.9e-3），**证明力不足**。按 A-87 真值三分法，误差通道属**真值**，
只有"现成误差通道"或"cmd ≠ fb"被实测坐实才能算真 ⟹ 归入中间行「待人工复判」，
**既不升为真 fe，也不贬为无 fe**。裁定所需的是上游逐列定义文档，不是更多数值复算。

**要填上这一格需要什么**（供后续取数时按图索骥，缺一不可）：
① 同一份记录里同时有 `pos_cmd` 与 `pos_fb`（或上游直接给的跟踪误差通道）；
② 同一份记录里有**实测**电流（不是设定值、不是转矩、不是力），且单位随数据发布；
③ 电流通道的时间栅格与位置通道**一致**（否则按 A-94 只能做跨栅格重采样，相干/相位类判据不可信）；
④ 上游给出逐列语义或 README（否则 `variable_semantics` 只能写"未发布"，C1 无法闭环）。

## 这批数据能证明什么、不能证明什么

**能**：解析器正确性、触发门控、方向符号、跟随误差构造、恒速段纹波、摩擦/爬行/stiction、
前馈失配（kff=1.5）、三传感器交叉验证、滑移检测、热相关漂移、报告管线。

**不能**：
- 不是故障数据。这是摩擦/滑移辨识实验，**受试对象健康**。
  不得声称"在真实产线故障样本上验证过"。
- 不是半导体设备。绳索驱动卷筒执行器，摩擦与绳弹性主导，与空气轴承/滚珠丝杠精密平台不同。
  不得包装成"封装设备实测数据"。
- ~~无 1 kHz 以上频响信息。~~ **★已裁 A-94 后此条按样本改写**：`fs ≤ 1 kHz` 的样本（3600/5171 全部 Scope View
  样本）无 1 kHz 以上频响信息；**但 4 kHz 样本（2563/3003/3252）`reliable_band_hz = 3.2 kHz`**，
  2 kHz 样本（3759/4224）为 1.6 kHz。仍无的信息是 **kHz 级机械谐振的正例与相干项**——
  频带虽打开，但这些样本没有 `cur_q`，`coherence_torque_velocity` 算不出来，
  故 R-03/R-04 仍**不给归因**（`band_gate_pass_channel_gate_fail`）。
- **全库无 `cur_q` 与 `fe` 同时具备的样本**（见上「能力格」）：28 份独立核验样本里 0 份 ⟹ KB8 该格
  `not_mappable(公开数据无此样本)`。B 组（ScienceDB 机器人关节）新增了 6 份样本，但它们**仍无电流列**，
  且 `fe` 角色待人工复判 ⟹ 不改变该格的结论。
- 无编码器偏心/接线错误/增益过高自激等样本。

→ 因此 C5 的 T1 层拆成两支：
**T1-a 真实测量（DaRUS + ScienceDB，本文件）— 验证解析与摩擦/滑移/热/轨迹误差类判据**；
**T1-b 外部故障真值（CWRU / Paderborn CM / Aalto / MFPT）— 只计机械 ↔ 电气二分类命中率，
禁止映射到具体 28 个 slug（A-63）**。
两者都不得外推为"半导体设备现场验证"。
★ ScienceDB B 组按 A-67 纪律**独立登记**（它既不是 DaRUS 也不是 T1-b 机械故障库）：
`doi:10.57760/sciencedb.04148`，CC BY 4.0，署名 Huang Huayuan / Pan Hongtao / Cheng Yong
（Hefei Institutes of Physical Science 等离子体研究所），引用须带该 DOI + CC BY 4.0，
**不得**并入 "Reichenbach / University of Stuttgart" 一行；且它**是机器人关节实验，不是半导体产线数据**。

## T1-b 外部数据集登记（正式标识与 `[待核]` 纪律 — 裁决 A-67）

本节给 KB8 的 `origin` 字段提供**可核实**的正式标识；登记状态截至本文件核验日期。
硬红线：**本文不编造 DOI、论文标题、文件名、采样率或任何数值**——凡未走"实际下载与解析"
核验流程（见文件头核验纪律）的，一律登记 `[待核]`，不得凭记忆填 DOI、不得猜 URL（A-67）。

| 数据集 | tier | 正式标识 | 说明 |
|---|---|---|---|
| DaRUS-3600 | T1-a | `doi:10.18419/DARUS-3600` | 本文件"出处与许可"表已实测核验（作者、发布日、文件数、许可 CC BY 4.0）；KB8 按此逐字回填 |
| DaRUS-5171 | T1-a | `doi:10.18419/DARUS-5171` | 同上；署名要求：Reichenbach, Thomas — University of Stuttgart (ROR 04vnq7t77) + DOI + CC BY 4.0 |
| CWRU | T1-b | `[待核]` | **本文无可核实 DOI**；采样率、文件名、工况数值一律不登记——未经实际下载解析，凭记忆填写违反 A-67 |
| Paderborn CM | T1-b | `[待核]` | 同上 |
| Aalto | T1-b | `[待核]` | 同上 |
| MFPT | T1-b | `[待核]` | 同上 |
| zenodo 21456277（KUKA KR3 电机电流） | **非 T1-b**，单列 | `doi:10.5281/zenodo.21456277`（**本会话现场核过 API**：标题/DOI/`cc-by-4.0`/`files[].checksum` 与本地 zip md5 逐字节一致） | 真机实测电流、单位明写安培；但**无位置通道**且**时基单位上游自相矛盾** ⟹ 只能进"电流"单维能力格，见文件级台账 #18 |
| zenodo 21526135（拉丝机电流+振动） | 非 T1-b，单列 | `doi:10.5281/zenodo.21526135`（同上，本会话核过） | 硬拒（`dt_jitter_ratio = 192.9`），不接入 |
| ScienceDB 机器人关节电机位置 | **T1-a**，单列 | `doi:10.57760/sciencedb.04148`（**本会话现场核过 DataCite**：`https://api.datacite.org/dois/10.57760/sciencedb.04148` → HTTP 200；标题/publisher/年份/版本/`cc-by-4.0`/创作者/摘要/主题词逐字抄录；并按字节重抓母包 50,493,558 B 与 DataCite 登记 size 一致、6 个 `.mat` 成员逐字节一致） | 机器人关节轨迹实验（等离子体研究所）；500 Hz、时基极干净、无电流列、`fe` 待人工复判 ⟹ **红线 6 开火，暂不接入 `raw/`** |

**`[待核]` 四项为何本轮仍未补齐**（A-67 的纪律，不是遗漏）：CWRU / Paderborn CM / Aalto / MFPT 要补正式标识，
就得走"实际下载 + 解析 + 核对"的同一套流程（注册 DOI、核对 md5、确认列语义），
而本轮的任务范围是"把 KB3 阈值与 KB7 台账定完"，不是新开一轮四库下载；
凭记忆填 DOI 违反 A-67、把 `[待核]` 换成"文献常见写法"违反 A-31。
⟹ 维持原判：**实现期核验任务**，不是现在能补上的空。

KB8 侧登记形态（A-67 逐字）：四个 T1-b 数据集的 `origin` 一律写
`{"source_tier": "T1-b", "repo": "<公开仓库名>", "id": "[待核]"}`——`id` 保持 `[待核]`
直到有人完成实际核验，**不得**用"文献常见写法"顶替占位符。
T1-b 的对外角色只是"机械 ↔ 电气二分类"（A-63），不依赖正式标识补齐；但面向外部的叙述
引用这些数据集时必须给可核实标识或明写 `[待核]`，措辞强度不得高于登记状态（A-31）。
补齐 `[待核]` 的义务是实现期的**核验任务**（下载、解析、核对后回填本表），不是可以现在
补上的空。
