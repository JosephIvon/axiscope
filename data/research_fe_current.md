# 实测核验：跟随误差（fe）× 电流通道 —— incoming 候选盘点（2026-10-20）

> 本文所有数字均为本会话在 `data/incoming/` 实体文件上亲自执行 `md5sum` / Python(numpy/scipy/h5py/openpyxl/csv) 测得；
> 上游元数据为本会话用 `curl` 实时抓取（DaRUS Dataverse REST API、Zenodo REST API）。
> 凡未亲自跑出的数字一律标「未实测」。判据：KB2 §5.1 六条硬拒（行数≥2000、时长≥0.5 s、
> dt_jitter_ratio=std(dt)/median(dt)≤0.2、NaN 占比≤0.05、存在动态分段、fe/电流类角色不全缺）。

## 0. 总体结论（先说答案）

**本批 12 个候选中，没有任何一份同时具备 (a) 真实的位置跟随误差（cmd≠fb）与 (b) 电流通道。**

- 有 fe、无电流：DaRUS 全部样本（darus-6114 三个文件、darus-2563 两个 .mat、darus-3003、darus-3252、darus-4224 四个 .xlsx）。
  它们与电流最接近的通道是 `M_KGT_act` / `*_tau_m`（转矩/转矩类命名），**上游未随数据集发布其单位与逐列语义**，不得当作电流使用。
- 有电流、无位置角色：KUKA 机器人电机实测电流（Zenodo 21456277，真机、过全部时基硬拒）；
  拉丝机电流+振动（Zenodo 21526135，真机，但作为单一时序过硬拒 3 抖动、分段后又过硬拒 1，见 §11）。
- 两头都没有：2563_LDD CSV（时长也不足）、17622448（运行日志类，非波形）、generator_data0001（无表头无时间列、来源未登记）。

最接近"两全"的组合是：**darus-3003/2563 的 fe + 转矩通道**（若上游论文能证 `M_KGT_act` 与 i_q 成正比可折算）或
**KUKA 电流 + 其位置由 A2 角度循环推断**（但文件内无位置列）。均需向"部分可用"降级处理。

### 上游核对方法（全部本会话执行）
- DaRUS：`curl https://darus.uni-stuttgart.de/api/datasets/:persistentId/?persistentId=doi:10.18419/darus-<ID>`
  取 license 字段与 files[] 的 `dataFile.id / filesize / md5`，逐条 vs 我方 `md5sum` 重算值。
- Zenodo：`curl https://zenodo.org/api/records/<recid>` 取 `license / files[].checksum(md5) / size`。
- ObserverTestSet.tab 另做了**字节级重抓**：`https://darus.uni-stuttgart.de/api/access/datafile/548615`。

---

## 1. 6114_x_velSweep_s0_n150_dir_pos.csv

- 数据集：**DaRUS doi:10.18419/darus-6114**「Replication Data for: Evaluation of Sliding-Mode Position Controllers
  on Multi-Axis Machine Tools with Compliant Mechanics」（五轴铣床，非 3109！本地 `3152_Readme.md` 实为 darus-3109 的
  Readme（其文首标题即 darus-3109），**不适用于本文件**）。上游文件表：`01_sysid_freq/x_axis/x_velSweep_s0_n150_dir_pos.csv`，dataFile id=548584。
- 许可证：API `license` 字段 = **CC BY 4.0**（本会话抓取核实，可再分发）。
- 字节数：6,487,193；我方 md5 重算：`8934cf9f15861aa8281484791aa8caf7`；上游 API md5：`8934cf9f15861aa8281484791aa8caf7`（filesize 6487193）→ **逐字节一致 SUPPORTED**。
- 表头（抄原文，52 列，首列为空表头的行号索引，另有 t 与 id；除索引/时间/id 外测量列 49 个）：
  `,t,id,acc_x_spindle,acc_x_table,acc_y_spindle,acc_y_table,acc_z_spindle,acc_z_table,b_tau_m,b_tau_m_add,b_v_d,b_v_d_add,b_v_m,b_x_d,b_x_l,b_x_m,c_tau_m,c_tau_m_add,c_v_d,c_v_d_add,c_v_m,c_x_d,c_x_l,c_x_m,temp_spindle,temp_table,x_tau_m,x_tau_m_add,x_v_d,x_v_d_add,x_v_m,x_x_d,x_x_l,x_x_m,y_tau_m,y_tau_m_add,y_v_d,y_v_d_add,y_v_m,y_x_d,y_x_l,y_x_m,z_tau_m,z_tau_m_add,z_v_d,z_v_d_add,z_v_m,z_x_d,z_x_l,z_x_m,e_3d`
- 六条硬拒实测：
  1. 行数 = **11,000** ≥2000 ✓
  2. `t` 为 ISO 时间戳（2025-04-15，带 +00:00），dt_median=0.00099993 s ⇒ 时长 = **10.9990 s** ≥0.5 s ✓（fs≈1 kHz，与"4 kHz"类 README 无关，本文件属 6114）
  3. dt_jitter_ratio = **1.10e-4** ≤0.2 ✓；严格单调 ✓
  4. NaN 占比 = **0**（52 列全满）✓
  5. 动态分段：`x_x_d` 相邻差分非零占比 **0.909**；`x_tau_m` std=0.0899（非恒值）✓
  6. 角色：位置 cmd=`x_x_d`、fb=`x_x_l`/`x_x_m` 均在且 **不等** ✓；电流通道 **无**（列表中无电流语义列）→ 硬拒 6 判「fe 在、电流缺」，未全缺，不触发硬拒但达不到两全。
- cmd vs fb 差异行数（vs 总行数 11,000）：
  - `x_x_d` vs `x_x_l`：**11000/11000 行不等**（|Δ|max=7.71e-5 m，mean=5.59e-5）
  - `x_x_d` vs `x_x_m`：11000/11000 不等（|Δ|max=5.48e-5）
  - `b/c/y/z` 各帧 `*_x_d` vs `*_x_l`：均 11000/11000 不等（|Δ|max 分别 2.84e-3 / 2.08e-3 / 2.39e-5 / 9.14e-6）
  - 注意：`b_x_d` vs `b_x_m` **0 行不等**（逐行完全相等）——b 帧 `_m` 是命令镜像，不可当反馈。
  - 直接误差通道 `e_3d`：min=2.51e-5, max=8.10e-5, std=1.47e-5（非零）
- 电流类通道：**无**。转矩类（语义未随数据集发布，单位未实测）：`x_tau_m` min=-0.305 max=0.522 std=0.0899；`z_tau_m` min=-0.006 max=0.259 std=0.0310；其余 |tau|<0.012。
- 结论：**部分可用**——fe 真实且逐行不等、六条硬拒全过；**缺电流通道**。列物理含义（b/c/x/y/z 帧、tau 单位）上游未发布 ⟹ 语义「未实测」。

## 2. 6114_lsmc.csv

- 同一上游：darus-6114，文件表 `02_single_axis_tracking/lsmc.csv`，dataFile id=548600；许可证 **CC BY 4.0**（API 抓取）。
- 字节数：2,037,002；我方 md5：`936627ef7aee1c518deaf7c0b891af9f`；上游 API md5 相同、filesize 相同 → **一致 SUPPORTED**。
- 表头：与 §1 同一 52 列（抄原文见 §1）。
- 六条硬拒实测：
  1. 行数 = **3,000** ✓
  2. 时长 = **2.9990 s**（dt_median=0.00099993 s，t=2025-11-05）✓
  3. dt_jitter_ratio = **1.10e-4** ✓，严格单调 ✓
  4. NaN = **0** ✓
  5. 动态分段：`e_3d` std=2.52e-6 非零、tau 通道均非常值 ✓
  6. 角色：fe 在（下）；**无电流列** ⟹ 部分可用。
- cmd vs fb 差异行数（/3,000）：`b`: 3000/3000；`c`: 3000/3000；`x`: 3000/3000（|Δ|max=1.34e-5）；`y`: **2994/3000**；`z`: **2984/3000**。均存在差异，非逐行相等。
- `e_3d`：min=1.75e-8 max=1.34e-5 std=2.52e-6。`x_tau_m`：min=-0.540 max=0.543 std=0.261。
- 结论：**部分可用**（缺电流；y/z 帧差异行数少但 >0）。

## 3. 6114_ObserverTestSet.tab

- 上游：darus-6114 `05_observer/ObserverTestSet.tab`，dataFile id=548615；**CC BY 4.0**。
- 字节数：367,419；我方 md5：`fd18abe49bf122f6f293289444e20adb`。
  本会话自 `api/access/datafile/548615` **重抓字节**：367,419 B、md5 `fd18abe49bf122f6f293289444e20adb` → **与本地逐字节一致**；
  但 API files[] 元数据里该文件的 `md5=56b18a8729803f71deae031a04445cad`、`filesize=367389`（比实体小 30 B）——**登记值与出版方实发字节不一致（疑换行符处理）**，如实记录。
- 表头（tab 分隔，5 列，抄原文）：`v_des	a_des	j_des	x_des	x_act`
- 六条硬拒实测：
  1. 行数 = **9,978** ✓
  2. **无时间列** ⟹ 采样率/时长无法从文件实测；若按同数据集 CSV 实测的 1 kHz 推断则约 9.98 s——该推断标「未实测」。时长判据按 KB2 口径不能凭推断开硬拒，也不能凭推断放行：**判「时长未实测」**。
  3. dt_jitter_ratio：**未实测（文件无时间列）**
  4. NaN = **0** ✓
  5. 动态分段：`x_act` 差分非零占比 0.956、`x_des` 0.079（存在停顿段+运动段）✓
  6. 角色：cmd=`x_des`、fb=`x_act` 均在且不等 ✓；**无电流列**。
- cmd vs fb 差异行数：**9978/9978 行不等**；误差 x_des−x_act：min=-6.98e-5, max=7.16e-5, std=7.50e-6。
- 结论：**部分可用**——fe 逐行真实；缺电流；且**时基不可实测**（使用时必须先解决采样率来源，见 notes）。

## 4. 2563_validate_SP_s0_720_v10_LDAComp.mat（DaRUS darus-2563）

- DOI：**10.18419/darus-2563**「Identification data for Linear Direct Drive Forces compensation」；本地 `2563_Readme.md` 与该数据集上游 Readme.md（dataFile id=168002，size 3151）同名同尺寸。
- 许可证：**CC BY 4.0**（API license 字段，本会话抓取）。
- 上游文件表：`validate_SP_s0_720_v10_LDAComp.mat`，dataFile id=144244，filesize 13,088,305，md5 `00ddbdf342e2f5b18c2f1c2c084a5ee0`。
- 我方：13,088,305 B，md5 `00ddbdf342e2f5b18c2f1c2c084a5ee0` → **一致 SUPPORTED**。
- 格式：.mat v7.3/HDF5，dSPACE struct `rec_dSPACE521`（h5py 读取）。VarNames（34 通道，抄原文）：
  `F_des_LDD, F_nut_sum, M_KGT_act, isKGTmoving, isLDDmoving, lastError, traj_KGT[0], traj_KGT[1], traj_KGT[2], traj_KGT[3], e_v_mot, e_v_obsv, e_x_T, e_x_obsv, sigEnable, x_hat[0], x_hat[1], x_hat[2], u_motor [rot], v_ref, v_ref_FF, tau_des_add, F_des_LDA, v_meas_motor, v_meas_table, x_meas_motor, x_meas_table, F_nut_1, F_nut_2, F_nut_3, F_nut_4, control.zr.lambda[0], control.zr.lambda[1], control.zr.lambda[2]`
- 六条硬拒实测（两条主时基）：
  1. 行数：1 kHz 栅格 **73,020**、4 kHz 栅格 **292,080** ✓
  2. 时长：X0(declared "1 ms") = **73.0199 s**；X1("HostService") = **73.0206 s** ✓
  3. jitter：X0 = **2.62e-7**、X1 = **1.00e-6** ✓（均严格单调）；注：X2("OnChange") 仅 26 点、jitter=0.2206>0.2，但它是离散事件栅格（control.zr.lambda 所在），不是波形载体——若按「任一时间基超阈即拒」口径则该条成立，如实列出。
  4. NaN 占比（全部 34 通道最差值）= **0** ✓
  5. 动态分段：`traj_KGT[0]` 0→0.72 m 单调递增行程、差分非零占比 0.986；`isKGTmoving` 为 1 的占比 0.986 ✓
  6. 角色：cmd=`traj_KGT[0]`、fb=`x_meas_table`/`x_meas_motor` 均在且不等，且**存在显式跟踪误差通道 `e_x_T`、`e_x_obsv`**（README 原文：定位误差 `traj_KGT[0] - x_meas_table`）；**电流通道无**。
- cmd vs fb 差异行数（fb 按最近邻插值到 cmd 栅格）：**73020/73020 行不等**（|Δ|max=7.95e-5 m，median=1.93e-6；vs x_meas_motor：73020/73020，|Δ|max=6.74e-5）。
- 误差恒等式复算：`e_x_T − (traj_KGT[0] − x_meas_table插值)` 最大偏差 **2.6e-10** → 通道语义 SUPPORTED（我方复算）。
- `e_x_T`：min=-5.33e-5, max=7.95e-5, std=3.96e-6；`e_x_obsv`：min=-4.63e-3, max=1.91e-3, std=1.75e-4。
- 转矩/电流相近通道：`M_KGT_act`（4 kHz）min=**-1.096** max=**5.762** std=**0.386**（单位上游未发布 ⟹ 未实测；命名 M_ 属转矩类，不当电流）。
- 结论：**部分可用**——fe（含直接误差通道）+ 真机实测 + 时长充分；**缺电流**。

## 5. 2563_SP_v100_forw.mat（darus-2563）

- 上游 dataFile id=134116，filesize 1,652,923，md5 `8b45044e1ff09e46062d065259c8a6dd`；我方重算 `8b45044e1ff09e46062d065259c8a6dd` → **一致**。CC BY 4.0。
- VarNames（30 通道）：同上表去掉 `F_nut_1..4`。
- 六条硬拒实测：行数 1kHz=**8,310**、4kHz=33,240 ✓；时长 X0=**8.3091 s** ✓；jitter X0=1.15e-6 / X1=1.52e-6 ✓；NaN 最差 **0** ✓；动态：`traj_KGT[0]` 0→0.72 m ✓；角色：cmd/fb/误差通道在，电流无。
- cmd vs fb：`traj_KGT[0]` vs `x_meas_table` **8310/8310 行不等**（|Δ|max=1.82e-4, median=1.45e-5）；恒等式 `e_x_T ≡ traj−fb` 最大偏差 **0.0**（逐点相等，SUPPORTED）。
- `e_x_T`：min=-1.23e-4 max=1.82e-4 std=2.71e-5。`M_KGT_act`：min=**-1.794** max=**7.837** std=**1.623**。
- 结论：**部分可用**（缺电流）。

## 6. 2563_LDD_Transfer_function_Force_controlled.csv（darus-2563）

- 上游 dataFile id=144246，filesize 64,274，md5 `bdd94f225701508ab70e7a4ecccc231d`；我方重算一致 → **一致**。CC BY 4.0。SIEMENS Starter 导出（分号分隔、逗号小数，README 原文）。
- 表头（抄原文，3 列）：`X (ms);C0:Lineardirektantrieb.r77;C1:Lineardirektantrieb.r78[0]`
  （r77/r78 逐列语义上游未发布，README 只指向西门子参数手册 ⟹「未实测」。r77 实测为 ±20 方波、r78 为其响应，判为力指令/力响应类，**不是电流**。）
- 六条硬拒实测：
  1. 行数 = **2,047** ✓（勉强）
  2. 时长 = X 从 0→127.875 ms = **0.1279 s** < 0.5 s → **硬拒 2 触发**
  3. jitter = **0**（dt 恒 0.0625 ms）✓
  4. NaN = **0** ✓
  5. 动态：两列均大幅值交变 ✓
  6. 角色：**无位置 cmd/fb、无电流** → fe 与电流双双缺失（硬拒 6 角度角色全缺）。
- 通道统计：r77 min=-20.000 max=20.000 std=20.000；r78 min=-20.398 max=21.063 std=8.101。
- 结论：**不可用**（硬拒 2：有效时长 0.128 s；且 fe/电流角色全缺）。

## 7. 3003_vel_sweep_s_400_dir_pos.mat（darus-3003）

- DOI：**10.18419/darus-3003**「Identification data for plant and friction identification」；上游 dataFile id=134473，filesize 2,271,904，md5 `4677bac4e932de5c5a03d0ba4dea778b`；我方重算一致 → **一致**。CC BY 4.0（本地 `3003_Readme.md` 上游 id=168722）。
  注：同名同 md5 文件亦在 darus-3252 `Identification/VelocitySweeps/`（id=168731）——两数据集共用字节，登记 upstream_id 时写明主归属 3003。
- VarNames（30 通道）：与 §5 同一组（`traj_KGT[0..3]`、`e_x_T`、`e_x_obsv`、`x_meas_table/motor`、`M_KGT_act`、`F_des_LDD/LDA`、`F_nut_sum`、`u_motor [rot]` 等）。
- 六条硬拒实测：行数 1kHz=**11,001**、4kHz=44,001 ✓；时长 X0=**10.9999 s** ✓；jitter X0=6.65e-7 / X1=1.17e-6 ✓（X2 OnChange 6 点 jitter 大，同 §4 说明）；NaN 最差 **0** ✓；动态：`traj_KGT[0]` 0.399→0.499 m 叠加正弦激励（`traj_KGT[3]` std=1706）✓；角色：cmd/fb/误差通道在，**无电流**。
- cmd vs fb：`traj_KGT[0]` vs `x_meas_table` **11001/11001 行不等**（|Δ|max=3.83e-4, median=3.45e-4）；恒等式 `e_x_T ≡ traj−fb` 最大偏差 **5.8e-15**（SUPPORTED）。
- `e_x_T`：min=4.81e-6 max=3.83e-4 std=4.47e-5；`M_KGT_act`：min=**-2.313** max=**4.700** std=**0.311**。
- 结论：**部分可用**（缺电流）。

## 8. 3252_dist_milling_PPI.mat（darus-3252）

- DOI：**10.18419/darus-3252**「Replication Data for: Robust µ parameterization with low tuning complexity of cascaded control for feed drives」；上游 `Validation/TimeDomain/disturbance_milling/dist_milling_PPI.mat`，dataFile id=168767，filesize 519,328，md5 `e47ebda6690c6670f84db6ade387eedf`；我方重算一致 → **一致**。CC BY 4.0。上游无 Readme.md，本地 `3252_parameters_dist.txt` 对应 `parameters.txt` 类文件（内容：s 50→150 mm、v_max 8 mm/s、扰动 2000 N 阶跃）。
- VarNames（21 通道，抄原文）：`F_des_LDD, M_KGT_act, isKGTmoving, isLDDmoving, traj_KGT[0], traj_KGT[1], traj_KGT[2], traj_KGT[3], x_hat[0], x_hat[1], x_hat[2], u_motor [rot], v_ref, v_ref_FF, u_rsmc, F_des_LDA, v_meas_motor, v_meas_table, x_meas_motor, x_meas_table, F_Hammer`
- 六条硬拒实测：行数 1kHz 栅格=**2,139**、4kHz=**8,556** ✓；时长 X0=**2.1380 s**、X1=2.1388 s ✓；jitter X0=1.81e-7 / X1=5.25e-7 ✓；NaN 最差 **0** ✓；动态：`traj_KGT[0]` std=0.2347 且 `F_Hammer`（锤击扰动）存在 ✓；角色：cmd=`traj_KGT[0]`、fb=`x_meas_table/motor` 在且不等（本文件**无** `e_x_*` 误差通道），**无电流**。
- cmd vs fb（最近邻插值到 1 kHz 栅格）：**2139/2139 行不等**（|Δ|max=2.75e-4, median=1.99e-6）。
- `M_KGT_act`：min=**-23.54** max=**32.26** std=**7.69**（幅值远大于 §4/§7，符合切削扰动工况）；`F_des_LDD`：min=-94.4 max=2064 std=842。
- 结论：**部分可用**（缺电流；无现成误差通道需自算 cmd−fb）。

## 9. 4224_Fig_3 / Fig_5_and_6 / Fig_7 / Fig_8_P2P 四个 .xlsx（darus-4224）

- DOI：**10.18419/darus-4224**「Replication Data for: Automatic Preload Adaptation for Rack-and-Pinion Drives to Maximize Performance and Energy Efficiency」。上游 dataFile ids：Fig_3=294888、Fig_5_and_6=294896、Fig_7=294889、Fig_8=314445；license **CC BY 4.0**（API 抓取）。
- 我方 md5 vs 上游 API md5（逐文件比对，全部一致 SUPPORTED）：
  - `4224_Fig_3_Measurement_Data.xlsx` 1,523,376 B `db51941d2c02cbac8abfa81fb4668ce2`
  - `4224_Fig_5_and_6_Measurement_Data.xlsx` 4,545,637 B `4bc61d8bf48c585ea85c5bae0ec8445b`
  - `4224_Fig_7_Measurement_Data.xlsx` 1,791,257 B `49c00e004fb0f40e00cf83f115656291`
  - `4224_Fig_8_P2P_Motion.xlsx` 508,941 B `11ba6e527e7bd204ce2d10b5f82cbecc`
- 列名（openpyxl 读表头原文）：Fig_3 各 sheet `time, x_d, d_x_M1, d_x_T`；Fig_5_and_6、Fig_8 `time, x_d, x_T, T_pl`；Fig_7 `time, x_d, x_T, F_LDD`。
  逐列物理语义：上游文件表中**无 README/变量定义**（本会话查 API files[] 与 per-file metadata，`/api/files/{id}/metadata` 返回空）⟹ 列含义「未实测」；命名 `x_d`（cmd）/`x_T`（fb）/`d_x_*`（误差）与 3109/2563 家族惯例一致，仅作弱推断标注。
- 六条硬拒实测（按 sheet；time 列单位 s，dt=0.0005 s）：
  | 文件 | sheet | 行数 | 时长 s | jitter | NaN 最差 | cmd-vs-fb 差异行数 |
  |---|---|---|---|---|---|---|
  | Fig_3 | 6 个 preload 组 | 8,001 | 4.000 | 5.2e-13 | 0 | 无 x_T 列；`d_x_T` 非零 **8001/8001**（每 sheet） |
  | Fig_5_and_6 | Min/Max/Adaptive | 36,001 | 18.000 | 1.8e-12 | 0 | x_d≠x_T **36001/36001**（\|Δ\|max 3.5e-4 / 2.3e-4 / 2.3e-4） |
  | Fig_7 | Min/Max/Adaptive | 16,001 | 8.000 | 8.6e-13 | 0 | x_d≠x_T **15999/16001**、16001/16001、16001/16001（\|Δ\|max ≤1.2e-5） |
  | Fig_8 | Min/Max/Adaptive | 4,500 | 2.2495 | 2.0e-13 | 0 | x_d≠x_T **4500/4500**、4399/4500、4433/4500 |
  全部 sheet 严格单调、动态分段存在（x_d 幅值变化>0）。
- 电流类通道：**无**。伴随列为 `T_pl`（preload 转矩类命名）与 `F_LDD`（力）。实测：Fig_7 `F_LDD` Min/Max/Adaptive 三 sheet 分别为 min=-93.28/max=97.08/std=56.22、min=-414.73/max=415.19/std=281.13、min=-412.46/max=422.32/std=281.03；Fig_5_and_6 `T_pl` 三 sheet min/max/std 分别为 -0.548/1.700/0.277、8.898/11.176/0.272、0.341/11.093/2.738。均**不是电流语义**（单位上游未发布）。
- 结论：四个文件均 **部分可用**——fe 真实（Fig_3 为现成误差通道 d_x_T/d_x_M1；其余为 x_d/x_T 对）；**缺电流**；列语义上游未发布（未实测）。

## 10. KUKA_payload_dataset.zip → kuka_extract/Robot_R2/collector_1014_5.csv

- 上游：**Zenodo record 21456277**「Motor-Current Dataset for Cycle-Level Payload Estimation on Two KUKA KR3 Robots」，
  DOI **10.5281/zenodo.21456277**，发布 2026-07-20，许可证 **CC BY 4.0**（本会话 `zenodo.org/api/records/21456277` 抓取：license id=cc-by-4.0）。
  记录页描述（本会话 API 抄录）：两台名义相同的 KUKA KR3 R540 真机、A2 单轴往复、载荷约 0.4–2.6 kg、以 KUKA Trace 记录、**声明采样周期 12 ms**；作者 Bátrla Adam / Hercík Radim / Byrtus Radek / Majidzadeh Gorjani Ojan（VSB – Technical University of Ostrava）。
- zip 实体：25,857,481 B，我方 md5 `efe9394bf2579f380832eed6d501c614`；Zenodo API files[] checksum **md5:efe9394bf2579f380832eed6d501c614**、size 25857481 → **一致 SUPPORTED**。
  zip 内含 `Robot_R1/` + `Robot_R2/` 两目录共 128 个 `collector_*.csv` + `readme.md`（本会话 `unzip -l` 实测：131 个条目，未压缩合计 89,407,403 B）；本地仅解压 1 个成员。
- 解压样本：`kuka_extract/Robot_R2/collector_1014_5.csv` 706,394 B，我方 md5 `d90e7ff0351cefdb399ceb6d77955931`（母包哈希已对上游，成员哈希与 Zenodo 无独立对照值——记录为「母包对齐、成员未独立外部对照」）。
- 表头（抄原文，7 列，`;` 分隔）：`Iststrom_A1 (A);Iststrom_A2 (A);Iststrom_A3 (A);Iststrom_A4 (A);Iststrom_A5 (A);Iststrom_A6 (A);Sample`
- 六条硬拒实测：
  1. 行数 = **5,367** ✓
  2. 时长：`Sample`（readme 称毫秒）首 0 → 末 21,464，若单位为 ms 则 **21.464 s** ✓（单位见下条矛盾项）
  3. jitter = **0**（dt 恒 4 tick、严格单调）✓；**但 Sample 的单位口径上游自相矛盾**：readme 一处称 `Sample: controller timestamp in milliseconds`（则 dt=4 ms ⟹ 250 Hz、总时长 21.464 s），另一处称「sampling period is 12 ms ≈ 83.3 Hz」（则 1 tick 须为 3 ms、总时长 64.39 s）。两读法不能同时成立 ⟹ 时基单位「待人工裁决」，本会话不据任何一种读法宣称已核实 fs；若按 12 ms/83.3 Hz 口径，行数 5,367 与时长仍过硬拒，若按 250 Hz 口径同样过硬拒（时长 21.464 s）。
  4. NaN = **0** ✓
  5. 动态：`Iststrom_A2` min=-2.162 max=1.463 std=0.474（往复载荷电流，非常值）✓
  6. 角色：**电流 6 列均在**（真机电流 ✓）；**无位置 cmd/fb、无速度反馈**（`position_columns_present: false`）→ fe 缺。
- 电流 min/max/std（A，本会话实测）：A1 -0.0091/0.0443/0.0027；A2 -2.162/1.463/0.474；A3 -0.821/0.0017/0.087；A4 -0.0171/0.105/0.0124；A5 -0.0306/0.122/0.050；A6 -0.0284/0.0669/0.0226。
- 结论：**部分可用**——真机实测电流齐全（6 轴）、时基均匀无抖动；**缺位置角色（fe）**；且上游对 `Sample` 的单位自述内部矛盾（毫秒 vs 12 ms 周期），接入前必须先裁决时间单位。

## 11. wiredrawing_dataset.xlsx

- 上游：**Zenodo record 21526135**「Multi-Block Vibration and Motor-Current Dataset from an Industrial Wire-Drawing Machine」，
  DOI **10.5281/zenodo.21526135**，发布 2026-07-24，许可证 **CC BY 4.0**（本会话 API 抓取；本地 README 亦写 CC BY 4.0，两处一致）。
- 实体：10,164,476 B，我方 md5 `d38d88e474b40e791b96290ad6565295`；Zenodo API checksum **md5:d38d88e474b40e791b96290ad6565295**、size 10164476 → **一致 SUPPORTED**。
- 表头：35 列（`Date Detailed, Date, 2..9. Block Current (A), True Speed, 2..9. Block RMS Velocity Value, 2..9. Block RMS Acceleration Value, 2..9. Block Analog Peak Acceleration` 及各自状态列，本地 README 有全表）。
- 六条硬拒实测：
  1. 总行数 = **47,706** ✓
  2. 挂钟跨度 = 4,321,740 s（50 天）✓
  3. dt：median=30 s 恒定，但生产停机造成大间隔：dt_max=**1,219,680 s**，**dt_jitter_ratio = 192.9 ≫ 0.2 → 硬拒 3 触发**（严格单调 ✓）。
     按连续段拆分：共 **1,196 段**，最长连续段 **666 行**（≈5.55 h 墙钟，但连续 dt=30 s 的行数 666 < 2000）→ 拆分后每段又触发**硬拒 1**。
  4. NaN = **0**（README 自述无缺失，实测一致）✓
  5. 动态：`True Speed` min=0 max=18 std=3.69、非零占比 0.990 ✓
  6. 角色：电机电流 8 列均在（如 2. Block Current (A) min=11.94 max=72.76 std=6.79；9. Block min=11.53 max=102.14 std=9.14）✓；**无任何位置/速度伺服反馈列**（`True Speed` 是产线线速，非轴反馈）→ fe 缺。
- 结论：**不可用**（作为伺服波形样本：硬拒 3 抖动 192.9 触发；连续段口径硬拒 1 触发。且无 fe）。电流通道本身真实、量大，若将来 KB 允许"分段台账类"电流可再议，本任务口径下拒。

## 12. 17622448（Zenodo "Industrial Machine Condition Monitoring Dataset"）

- 本地 `17622448_README.txt` 内容实为 API 报错 JSON：`{"status": 404, "message": "Record '17622448' has no file 'README.md'."}`——该记录**无 README.txt**（本地 `17622448_metadata.txt` 与上游 metadata.txt 同名）。
- 上游核实（本会话 `zenodo.org/api/records/17622448`）：标题「Industrial Machine Condition Monitoring Dataset」，
  DOI **10.5281/zenodo.17622448**，发布 2025-11-16，许可证 **CC BY 4.0**；文件：dataset.csv（HEAD 实测 content-length **6,562,286 B**）、metadata.txt、README.txt(404)。
- 本会话按 <200 MB 限额**新下载**了全量 `17622448_dataset.csv`：6,562,286 B，我方 md5 `6e7dfe098b4454c662b441528ff2cbb8`（Zenodo API 未提供该文件 md5 值可比对 → 上游校验和**未实测**）。
- 列名（抄原文）：`Timestamp,MachineCode,MachineName,Category,OT,DT,NoF,LoadPercent,CycleCount,Energy_kWh,OilLevel_L,OilTemp_C,Shift,DowntimeRatio,FailureRate,OilEfficiency,ThermalStress,FailureCause`
- 六条硬拒实测（全量文件）：
  1. 行数 = **38,390** ✓
  2. 跨度 = 65,749,680 s（≈2.09 年）✓
  3. dt：median=1,140 s，**dt_min=0（存在重复时间戳，时间列非严格单调）**，**jitter=1.62 > 0.2 → 硬拒 3 触发**；且按 validate_raw 口径「时基非严格单调」直接拒。
  4. NaN 最差列 = FailureRate **2.6e-5** ≤0.05 ✓
  5. 动态：数值列均有方差 ✓
  6. 角色：**无位置 cmd/fb、无电流列**（18 列里无安培类；上游 metadata 自述"数据系由机台日志与 CMMS 事件**构造**而成"——非真机波形）。
- 本地 `17622448_head.csv`（17 行，3,001 B，md5 `b679dd4e1b19fa1def1f3f611fc0f8c1`）：硬拒 1（行数）与硬拒 4（FailureRate NaN 0.118>0.05）双触发，仅作表头样本。
- 结论：**不可用**（硬拒 3 + 非严格单调；角色全缺；且上游自述为构造数据，不满足"真机实测"）。

## 13. generator_data0001.csv

- 上游/DOI/许可证：**未登记**。本地无任何 README/来源文件。本会话核查：GitHub 代码搜索匿名限额（伪 403/404，按规则不能据"打不开"下结论）；
  网络检索仅见其与 Syslab 传感器异常检测教程及 MathWorks 演示「Autoencoder-based anomaly detection for sensor data」同名片段
  （多为**仿真/生成**数据的用法）——均非可核验的出版记录 ⟹ 来源等级：未登记，许可证未声明。
- 实体：181,631 B，md5 `fc74558a1988e11f1641923f73350850`。
- 列名：**无表头**（首行即数值，抄原文：`-0.2,5,18,-48,0.008,0.02,-0.64,0.66,0.32`；9 列）。列语义无从抄起 → 未实测。
- 六条硬拒实测：
  1. 行数 = **3,789** ✓
  2. 时长：**无时间列**，采样率/时长未实测
  3. jitter：**未实测（无时间列）**
  4. NaN = **0** ✓
  5. 动态：9 列全部有方差 ✓
  6. 角色：9 列语义未登记，无法认定 fe/电流；无任何命名位置或电流列。
- 结论：**不可用**（来源未登记 + 时基不可实测 + 角色无法认定；检索线索显示大概率为仿真数据）。

---

## 附：判据口径备注
- dt_jitter_ratio 口径 = std(dt)/|median(dt)|（与 C2 `quality.dt_jitter_ratio`、validate_raw.py 头注一致）。
- NaN 占比按"最差通道"判 ≤0.05。
- 「cmd/fb 差异行数」：CSV/xlsx 同栅格直接逐行相减；dSPACE .mat 中 cmd(1 kHz) 与 fb(4 kHz) 栅格不同，采用 fb 最近邻插值到 cmd 栅格后逐行相减，并已用文件自带 `e_x_T` 通道复算恒等式验证（偏差 ≤2.6e-10）。
- 侧车（.source.txt）只为「可用/部分可用」样本书写：§1–§5、§7–§10 共 12 份；§6、§11–§13 判不可用不写。
