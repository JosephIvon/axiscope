# KB6 — 耦合寻光与标定诊断模块规范

> **定位**：KB6 是 KB3 通用伺服波形内核之上的**工艺外壳**：不新增诊断方法论，只把半导体封装设备里
> 两个"只有这类设备才有"的环节——自动耦合寻光（light-seeking）与标定结果统计诊断——变成可用同一套
> 证据/归因纪律判定的子模块。作品集价值在于**能读工艺时序 + 能对标定结果做统计诊断**，而不是谁都能
> 做的通用波形库。
> 依赖：KB0（命名与 tier）、C1（波形与分段）、C2（**伺服侧**特征唯一来源）、**C7（工艺/标定/扫描程序/节拍特征唯一来源，裁决 A-15）**、
> C3（输出契约）、C4（验证门控）、C5（分层评测）、C6（事件与时间同步纪律）。
> 本期**不写产品代码**：只允许判据表达式、统计式子与伪代码。

## 0. 范围纪律 / 编号 / 规则块格式

### 0.1 明确不做（写了就是范围膨胀）

| 不做 | 原因与归属 |
|---|---|
| 运动状态机执行引擎、工艺步骤调度、流程编排 | C6 §5 明文划出；本模块只**读** `segments` 与 `event_context.step_labels` |
| 报警管理、异常恢复执行、自动重试寻光 | C6 §5。恢复只以 C3 `recommendation.field_procedure` 的**人执行文本**存在 |
| MES / 配方服务器 / 良率数据库 | 无数据可得性（DECISION §3 方案四的批评有效），且与诊断无关 |
| 标定参数求解（3×3 仿射、手眼矩阵 AX=XB、运动学补偿表生成） | 那是标定引擎不是诊断；本模块只判定"标定结果作为证据说明了什么" |
| 在线整定、自动下发任何参数/坐标 | C3 硬性规则 6：`safety.writes_to_device` 恒为 `false` |
| 把 KB6 建成耦合工艺专家系统（光学设计、模场仿真、器件选型） | 无数据、无真值，判据不可证伪 |

**KB6 的每条判据必须能被"波形 + 事件 + 标定记录"三者之一证伪。** 证伪不了的工艺常识不写进规则块，只写进 §A.1/§B.1 的时序语境。

### 0.2 编号段

`R-31+` 由 KB0 §1 保留给 KB6。本文分配（只追加，不改已引用编号语义）：**A 耦合寻光 `R-31 … R-42`（12 条）**、**B 标定诊断 `R-43 … R-50`（8 条）**、`R-51 …` 预留。
`family` 一律取 KB0 §2 的 slug；工艺侧与几何侧需要的新 slug 集中在文末 **G-1**，**已被裁决为不采纳（A-16）**，故正文**不出现**任何未登记 slug：这些现象只以自然语言出现在 `differential.considered` / `differential.not_evaluable`（这两个字段不是 `cause`，允许非 slug 文本，与 C3 示例 `gain_too_high_hunting` 用法一致）。三条**门禁规则**（R-37 / R-49 / R-50）无 cause，统一写作 **`family: null`**（裁决 A-17；旧版写作 `family: —`，本文已全部改为 `null`），其形式合法性见 **G-2**。

### 0.3 规则块格式（与 KB3 同构）与三条本地纪律

KB3（task #2）**已落盘**，字段顺序与本文一致：`family` / `断言` / `判据` / `必要上下文` / `排除项` / `建议动作` / `期望效果依据` / `出处 tier` / `适用边界`，判据子条件带 `R-NNa/b/c` 后缀。出入之处以 KB3 为准、由主线程统一改写（**M-7 已裁：KB0 §6 检查 7 已加**）。

1. **阈值命名域**：µW/dBm/µm 量纲阈值只在 `meta.counts_per_mm != null`（位置类）且功率单位已知时生效；否则必须改用**无量纲比值形式**并在报告里标 `[ratio]` 或 `[counts]`；没有比值形式的判据，在缺定标系数/缺单位时**不启用**并进 `not_evaluable`。
2. **`判据` 只能是已登记的点号路径**：伺服侧走 **C2**，工艺/标定/节拍侧走 **C7**（`power_channel.*` / `light_curve.*` / `calibration.*` / `scan_program.*` / `cycle_stats.*`；裁决 A-15/A-34/A-36，逐字段口径在 **C7 §2.2 / §4.2 的"口径"列**，该列即工艺侧索引，裁决 A-40）。规则引擎不许自己 FFT/拟合。C1 的 `meta.*` / `quality.*` / `segments` / `counts_per_mm` 属**门禁条件**，写在 `必要上下文`，**不得**出现在 C3 `supporting_evidence[].feature` 里。
3. **效应量与显著性同时出现**：既要有 `>= k × <自身尺度>`（工程意义），也要有 `p <= 0.05` 或 CI 不含 0（显著性）。只有显著性、效应量可忽略的结论一律拒收。

## 1. 特征扩展总则

- 本文**不修改 C2**；KB6 的全部工艺/标定特征已**登记于 C7**（物理载体 `process.json` + `calibration.jsonl`，裁决 **A-15**），文末 **G-3** 只保留与 C7 §2.2/§4.2 一致的对照表，权威字段名与口径以 C7 为准（原"待并入 C2"清单**机制作废**，裁决 **A-36**）。**旧机制"引用未并入 C2 的 KB6-NEW 路径 ⇒ 加载期 `blocked`"已消失**；取而代之的是 **C7 §1.2 缺档纪律**：`process.json` 缺失 ⇒ A 组（R-31…R-42）、`calibration.jsonl` 缺失 ⇒ B 组（R-43…R-50）逐条 `blocked` 并**逐条**登记 `differential.not_evaluable`（C3 硬规则 9：**不允许沉默跳过**），**绝不允许**输出"未发现工艺异常""耦合曲线形态正常"。未登记于 C2 **或** C7 的路径仍按结构性缺失显式登记（理由文本 `"feature path not registered in C2 or C7 (C7-NEW)"`，KB0 §3/§6 检查 7），与 C2 频带门禁（规则 7 + `freq_limits.blocked_rules`）同构。
- 复用的 C2 既有组按原名使用、**不重定义不改语义**（复用清单与禁止项已契约化在 **C7 §2.3**）：`global.*`、`spectral.*`、`resonance.candidates[]`、`ripple.probing[]`、`crawling.low_speed_segments[]`、`ff_mismatch.*`、`encoder.*`、`step_response[]`、`tracking.*`、`bandwidth.*`、`freq_limits.*`、`event_context.*`、`segment_coverage.*`、`unavailable`。
- C2 **没有** `cycle_jitter`，裁决 **A-25** 明确**不新增**（M-6 已裁）：节拍统计一律归 **C7 `cycle_stats`**、不进 C2（C2 只做波形特征）。本文只借用其**设计模式**（按工况分组 + 比值形式 + 对右尾敏感），在 §B.3 独立论证，不引用不存在的路径。

---

# A. 耦合寻光子模块（光纤/激光器耦合贴装工序）

## A.1 工艺时序与通道

### A.1.1 寻光在工艺时序里的位置

```
pick → place → [coupling: coarse search 粗定位（示教/视觉引导）
                 → scanning 寻光扫描（光栅 raster / 阿基米德螺旋 / 蛇形）
                 → fine search 单轴线性扫（probing 恒速 或 逐点 dwell）
                 → hill_climb 比较式爬山（前进—停—读数—比前值—继续或反向）
                 → peak_lock 峰值锁定（dither + lock-in 解调，或静态锁峰）] → cure 胶固化（UV/热）→ verify
curing 之后仍可能复扫：固化收缩与温升把峰位拽走（R-33 的时间锚）
```

对应 `segments.kind`（沿用 C1 词表，**不新增 kind**）：`scanning`（扫描轨迹）、`probing`（恒速线性扫，
与 KB3 纹波判据同一段）、`dwell`（逐点测量驻留）、`settling`（提供 τ_axis）、`curing`（固化跟随）。
`segment_coverage.scanning` 或 `.probing` 任一 > 0 是 A 组可评估的**硬前提**；`curing` 是否被单独切出，
决定 R-33 能否把漂移归为"热/固化"而非随机漂移。扫描**模式**（螺距、线距、爬山步长、驻留时长）是轨迹
参数而非运动语境，权威载体是 **C7 `scan_program`**（`scan_program.segments[].{kind, scan_type, step_counts, pitch_counts, dwell_ms, n_points_expected, feedrate_counts_s}`；裁决 **A-28/A-41**，**M-2 已闭合**——**不给** C6 `machine_context` 加 `motion_program`，以免双载体），曲线侧只以 `light_curve.scans[].scan_kind` 与之交叉校验（不一致时以 `scan_program` 为准并登记冲突，C7 §5 硬规则 5）；此举同时避免把 C1 的 segments 词表撑成第二套状态机。

### A.1.2 `laser_power` 从哪来，以及为什么它本身就是诊断约束

| 采集方式 | 典型速率 | 时间戳来源 | 对本模块的后果 |
|---|---|---|---|
| 功率计 + 串口（RS-232/USB）SCPI 轮询 | 1–10 Hz，慢的 <1 Hz | 主机轮询循环 | 抖动大、被上位机线程抢占；一次读数 ≈ 一个积分窗 |
| GPIB（IEEE-488）轮询 | 亚 Hz – 几 Hz | 总线交互之后 | 单次 `READ?` 往返数十 ms；总线错误吃掉整拍 |
| 功率计模拟监视输出 → 采集卡 | 可达 kHz | 与伺服同时钟 | 唯一能做"曲线形态级"判据的形态 |

伺服位置环 1–8 kHz、波形 fs 常见 8–20 kHz（C1 示例 8 kHz），功率读数慢 2–3 个数量级。
`power_channel.ratio_to_servo_fs` 因此是 A 组的**第一门禁参数**：它决定"曲线上的一点"到底是 1 个位置
还是几千个位置的平均。**把这件事写成判据而不是抱怨**——峰形退化、噪声底上升、双峰这些"光学症状"，
在 `power_channel.ratio_to_servo_fs` **很大**（采样粗）时**首先是采样器现象**（R-31/R-42 的职责）。
**方向口径（裁决 A-35，本文旧版方向反了，已按 C7 纠正）**：`power_channel.ratio_to_servo_fs = servo_fs / power_channel.sample_rate_hz`，
**比值越大采样越粗**；档位语义与"允许什么声明"的唯一权威是 **C7 §3.2 四档表**（`<10 / 10–100 / 100–1000 / >1000`，单调），
本文**不得自设比值阈值**。

### A.1.3 时间对齐要求（C6 `sync` 纪律的耦合版）

1. **功率时间戳必须可溯源**：`power_channel.timestamp_source == "host_poll"` 时对齐不确定度至少为轮询周期（`power_channel.poll_period_ms`）的一半，再叠 `event_context.sync.uncertainty_ms`（C6：缺省按 5 ms 保守取值并记 `audit.assumptions`）。
2. **位置回写用积分窗中心，不用读数时刻**：轮询形态下两者系统性不重合，`light_curve.vision_write_back.vel_at_write_back_counts_s` 就是量这个错配的。
3. **每个测量点要能证明"采样时轴停住了"**：`meta.io_bits` 的 `settled` 位，或 `vel_fb` 与 `fe` 同时进带（`step_response[].settle_band_counts`）。
4. **扫描期间位置一律取 `pos_fb`**，不得用 `pos_cmd` 反推（跟随误差本身非零）；只有 `dwell` 段允许以 `pos_cmd` 为参考。
5. 对齐残差 `|Δt| <= sync.uncertainty_ms` 的对齐**不得作为证据**（C6 硬规则 2）；`event_context.causal_claims_permitted == false` 时 A 组所有 `software_induced_*` 归因降级为时间共现（C2 规则 8）。
6. 视觉通道按 C1 的 15–60 Hz 降采样，`vision_x/y/angle` 与功率样本**不在同一栅格**；比较两者只能做窗口聚合（窗内均值 + 方差），禁止逐点插值后再比较。

## A.2 可编码判据 R-31 … R-42

**A 组通用采样门禁（先于任何子条件生效，权威在 C7）**
1. **采样率档位**：**C7 §3.2** 四档表（`power_channel.ratio_to_servo_fs` = `<10 / 10–100 / 100–1000 / >1000`，比值越大采样越粗）决定"允许什么声明"；`> 1000` 档单扫描峰形判据一律拒收。**本文不自设比值阈值**（裁决 A-35）。
2. **空间分辨率拒收红线**：**C7 §3.3** —— `light_curve.scans[].fwhm_counts < 3 × light_curve.scans[].point_step_counts` 时，本文所有以 `× fwhm_counts` 归一的子条件（**R-31d / R-32c / R-33a / R-34b / R-35c / R-37b / R-40b / R-42c**）随之失效；判据分辨率下界 = `max(light_curve.scans[].point_step_counts, 2 × v_sweep × τ_int)`（C7 §3.3-3，无量纲 ⇒ 缺 `counts_per_mm` 依然生效）；被拒声明必须写顶层 `blocked_claims[]` + `audit.rules_skipped` + `differential.not_evaluable`。
3. **频带纪律**：**C7 §3.4**（功率域频率声明 `< power_channel.reliable_band_hz`；`noise_dominant_freq_hz` 仅 `sample_rate_hz >= 20` 可非 null；混叠折叠禁止；`power_channel.dt_jitter_ratio > 0.2` 时功率域频率类判据不启用）。
4. **缺档纪律**：**C7 §1.2**（文件缺失 / `present == false` / 依赖字段为 `null` ⇒ 逐条 `blocked` + `not_evaluable`，禁止"未发现工艺异常""耦合曲线形态正常""节拍正常"）。

### R-31 峰形展宽 + 平顶 + 峰值下降同时出现，而峰位几乎不动
- **family**: `software_induced_polling_latency`
- **断言**：功率计积分窗与轴运动重叠，单点读数成为"沿轨迹的空间平均"，表观峰被涂抹——展宽、平顶、峰降三者同时出现而峰位不动，是采样器症状而非模场劣化。
- **判据**：R-31a `power_channel.integration_time_ms >= 50`；**R-31b（裁决 A-35：本文旧版写 `power_channel.ratio_to_servo_fs < 20 ⟹ 积分窗涂抹`、`>= 100 ⟹ 结构性排除`，方向反了——`ratio_to_servo_fs = servo_fs / sample_rate_hz`，比值越大采样越粗。已按 C7 口径纠正，本文不得自设比值阈值）**：`power_channel.ratio_to_servo_fs` 落在 **C7 §3.2 四档表**（`<10 / 10–100 / 100–1000 / >1000`，档位唯一权威在 C7 §3.2）的 `100–1000` 或 `>1000` 档 **且** 积分窗的空间涂抹量进入 **C7 §3.3-3** 的**无量纲分辨率下界** `max(light_curve.scans[].point_step_counts, 2 × v_sweep × τ_int)` 的右项，即 `2 × v_sweep × τ_int >= light_curve.scans[].point_step_counts`（τ_int = `power_channel.integration_time_ms`；`v_sweep` 取 C1 `vel_fb`，恒速 `probing` 段可用 `scan_program.segments[].feedrate_counts_s`）⇒ "一个读数"是积分窗内的空间平均，该扫描上以 `light_curve.scans[].fwhm_counts` 归一的空间分辨率声明按 C7 §3.3 拒收并写顶层 `blocked_claims[]`。**"积分窗涂抹"不由采样率单独决定**：比值大但 `2 × v_sweep × τ_int` 可忽略（读数时轴已停稳）时本分支不成立；R-31c `light_curve.series_stats.fwhm_growth_pct_vs_ref >= 50` ∧ `light_curve.scans[].plateau_ratio >= 0.3`；R-31d `abs(light_curve.series_stats.peak_position_drift_counts) < light_curve.scans[].point_step_counts`（形变而峰不动 ⇒ 排除真实对准偏移）。a∧b∧c 触发，d 为必要条件。
- **必要上下文**：`scanning` 或 `dwell` 段；`power_channel.present == true` 且无 C1 时基红线；`power_channel.integration_time_ms` 与 `power_channel.ratio_to_servo_fs` 均非 null（五项采样元数据全必填，C7 §3.1）；`step_response[].settling_time_ms` 已知（否则退化为 T2 经验值并按 §C.3 第 7 行截断）。
- **排除项**：模场失配/离焦也展宽 FWHM，但采样时可证明静止（`light_curve.motion_sampling_conflict.in_motion_sample_ratio ≈ 0`）→ 本条不成立；**光学解释无可用 slug（G-1 未被采纳，裁决 A-16）**，只记 `differential.considered`"模场失配/离焦候选"，并在 `differential.not_evaluable` 登记"模场失配/离焦：无可用 cause slug（KB6 G-1 未采纳）"；采样线程被抢占（`event_context.host_pause_max_ms` 与展宽扫描共现 ∧ `power_channel.dt_jitter_ratio >= 0.2`）→ 转 `software_induced_host_thread_jitter`；逐点驻留的时序窗错误另有 R-42（两条共享 `light_curve.motion_sampling_conflict.*` 证据，不得各自独立计权 → §C.4）。
- **建议动作**：`change_measurement_procedure`（可回退的测量步骤变更）——每点停稳后再触发读数；或改用模拟监视输出采集；或把扫描速度降到"窗内移动量 < FWHM/10"档位。
- **期望效果依据**：`unverified`，只给方向（展宽消失）。**禁止**给改进百分比——C4 的被控对象（KB5）里没有光学耦合效率曲面。
- **出处 tier**：`T2`（功率计手册：响应时间/积分窗/读数速率档位）+ `T3`（合成功率曲面上复现采样器伪影）。
- **适用边界**：缺 `power_channel.integration_time_ms` 时本条**不启用**并进 `not_evaluable`（不得说"未见采样伪影"）；`power_channel.transport == "analog_daq"` 且 `power_channel.ratio_to_servo_fs < 10`（C7 §3.2 第 1 档：与伺服同时钟）时被**结构性排除**，应显示 `skipped` 而非"未检出"；`> 1000`（C7 §3.2 第 4 档）时**单扫描峰形判据一律拒收**，R-31c/R-31d 不可评估，只允许 `light_curve.series_stats.*` 跨扫描统计与 R-37 门禁侧。

### R-32 多峰伪像：回程差把同一真峰画成两个峰
- **family**: `mechanical_backlash`
- **断言**：一条扫描上的多个局部峰中，有一部分不是光学模场结构，而是反向间隙造成的位置偏移把同一真峰在曲线上画了两次。
- **判据**：R-32a `light_curve.scans[].n_local_maxima >= 2`；R-32b `light_curve.scans[].secondary_peak_over_peak_ratio >= 0.3` ∧ 次峰位于方向反转点 `± 2 × light_curve.scans[].point_step_counts` 内；R-32c `abs(light_curve.scans[].local_maxima_separation_counts) <= 1.5 × global.backlash_estimate_counts`（间距与间隙同为纯 counts ⇒ 缺 `meta.counts_per_mm` 仍成立，C7 §2.2 A2）；R-32d `global.reversal_error_counts > 0` ∧ `step_response[].limit_cycle_present == false`（排除自激极限环画出的等距峰）。
- **必要上下文**：`light_curve.scans[].direction_sequence` 可解析（轨迹含反向点）；`scanning`/`probing` 段；`global.backlash_estimate_counts != null`（否则该值来自本条自身 → 循环论证，KB0 §6 检查 1）。
- **排除项**：真偏振/双模劈裂的两峰**间距由光学决定、与反向点无关**且在单向扫描里仍复现，间距 `>= light_curve.scans[].fwhm_counts` 时**禁止**机械归因，改记 `differential.considered`"偏振/双模劈裂候选"（**G-1 未采纳，裁决 A-16** ⇒ 无归因出口，逐条记 `differential.not_evaluable`"偏振/双模劈裂：无可用 cause slug（KB6 G-1 未采纳）"，**禁止**用近似 slug 顶包）；`step_response[].limit_cycle_present == true` → 共振族优先（R-36）；工件边缘/胶线遮挡的台阶不等间距 → R-38 排除项。
- **建议动作**：`change_measurement_procedure` —— 单向趋近（每次从同一方向进入最优点），并在 `field_procedure` 要求复测机械间隙。本模块**不给**间隙补偿数值。
- **期望效果依据**：`unverified`；仅做单向趋近时可给 `metric: light_curve.scans[].n_local_maxima, to: 1`，`basis: rule_heuristic`。
- **出处 tier**：`T1-a`（DaRUS 真实反向误差/间隙，**仅"特征可存在"这一子事实**，不含耦合外推）+ `T2` + `T3`。
- **适用边界**：`meta.counts_per_mm == null` 时 R-32c 仍成立（阈值随 `global.backlash_estimate_counts` 缩放，纯 counts 比较，标 `[counts]`），**不得**换算 µm。

### R-33 峰位单调漂移：固化收缩/温漂，而不是"轴不准"
- **family**: `mechanical_thermal_drift`
- **断言**：峰位随扫描序次单调漂移、漂移速率与 `curing` 窗/温升同步 ⇒ 锁定发生在收缩完成之前，是工艺时序问题。
- **判据**：R-33a `light_curve.series_stats.peak_position_drift_counts >= 3 × light_curve.scans[].fwhm_counts`（漂出 3 倍峰宽 ⇒ 锁定点必然不在峰上）；R-33b `light_curve.series_stats.drift_slope_counts_per_scan` 同号 ∧ `light_curve.series_stats.spearman_rho >= 0.7` ∧ `light_curve.series_stats.drift_p_value <= 0.05`；R-33c `global.thermal_fe_correlation_r >= 0.6` 且漂移符号与 `global.thermal_drift_counts_per_min` 一致；R-33d `segment_coverage.curing > 0` 且漂移集中在固化窗结束后前 N 次扫描（N 由 `curing` 窗长与扫描间隔推出）。
- **必要上下文**：`light_curve.series_stats.n_scans >= 5` 的跨扫描序列（`< 5` ⇒ 斜率检验不可信，C7 §2.2 A3）；`scanning` + `curing` 分段；`temp` 通道或室温记录可用。
- **排除项**：漂移与配方/换型事件（`event_context.step_labels[].recipe`）对齐 → 归 `software_induced_pulse_eq_overwritten`（R-47）；只在换向时出现、单向序列不漂 → `mechanical_backlash`（R-32）；只出现在 `light_curve.vision_write_back.vel_at_write_back_counts_s > 0` 的样本 → `software_induced_late_vision_result`（R-34）；不对称随行程变化 → R-35。
- **建议动作**：`change_measurement_procedure` —— `field_procedure` 给出"固化后等待至热稳态再寻光/复扫"的人执行步骤与终止判据（`global.thermal_drift_counts_per_min` 收敛进带宽）。本模块**不实现**收缩补偿曲线、不生成补偿参数。
- **期望效果依据**：`unverified`；只给 `light_curve.series_stats.peak_position_drift_counts` 的方向下降。
- **出处 tier**：`T2`（封装工艺文献：固化收缩与温漂引起的耦合位移是已知失效模式，**方向性、不给数值**）+ `T3`（合成收缩曲线）；`T1-a` **不可**用于本条的耦合结论（DaRUS 无固化、无功率通道）。
- **适用边界**：`curing` 缺失 → R-33d 进 `not_evaluable`、整条降级；`light_curve.series_stats.n_scans < 5` → 斜率检验不可信，**禁止**输出单调性结论；`light_curve.series_stats.ref_scan_ids` 为空 ⇒ 上限 0.5（§C.3 第 8 行，C7 §2.2 A3；`null` **不等于**"无漂移"）；`meta.counts_per_mm == null` 时**禁止**把 `3 × fwhm` 说成"约 X µm"。

### R-34 视觉/功率结果迟到，使"最优点"被回写到过期坐标
- **family**: `software_induced_late_vision_result`
- **断言**：功率读数与回写所用位置来自两个时刻，且回写发生在轴已离开驻留点之后 ⇒ 记录到的最优点是一个假点，复现时"找不到峰"。
- **判据**：R-34a `light_curve.vision_write_back.write_back_delay_ms > 2 × power_channel.poll_period_ms`；R-34b `light_curve.vision_write_back.vel_at_write_back_counts_s > 0` ∧ `light_curve.vision_write_back.stale_coord_mismatch_counts >= 0.5 × light_curve.scans[].fwhm_counts`（`stale_coord_mismatch_counts` = 锁存位置与积分窗中心位置之差，C7 §2.2 A6）；R-34c `event_context.vision_result_latency_p95_ms` 相对历史基线同阶增大；R-34d 峰位偏移方向与扫描运动方向一致（滞后特征，非热漂移特征）。
- **必要上下文**：`event_context.available == true`；`power_channel.transport ∈ {serial, gpib}`；`event_context.sync.verified == true` ∧ `event_context.causal_claims_permitted == true`；`light_curve.vision_write_back.power_timestamp_source` 已声明（非 `device` ⇒ 因果降级，C7 §2.2 A6/§4.3）。
- **排除项**：`event_context.sync.verified == false` → 强制写 `differential.not_evaluable`，文本记"时钟未对齐，无法区分回写滞后与真实峰位偏移"；`light_curve.vision_write_back.vel_at_write_back_counts_s == 0`（采样时确实静止）→ 排除，转 R-33（漂移）或 R-31（涂抹）；`event_context.alignment_residual_ms` 已超 `event_context.sync.uncertainty_ms` → 证据作废（C6 硬规则 2）。
- **建议动作**：`change_measurement_procedure` —— 读数触发与位置锁存用同一信号/同一时刻，或在驻留窗内读完数再移动；`requires_human_approval: true`。
- **期望效果依据**：`rule_heuristic`（方向明确，不给百分比）。
- **出处 tier**：`T2` + `T3`（合成"迟到 + 回写错位"样本）。
- **适用边界**：`power_channel.transport == "analog_daq"` 且 `power_channel.timestamp_source == "device"`（同源时钟，C7 §3.2 第 1 档）时本条**结构性不成立**，应显示 `skipped` 而非"未检出"。

### R-35 曲线不对称且**随行程位置**变化：几何误差串扰，不是真像散
- **family**: `mechanical_loose_structure`
- **断言**：峰形左右不对称且不对称量随扫描起止位置变化、伴随垂直轴/角度同步漂移 ⇒ 采样轨迹不是纯单轴切割，而被几何误差（直线性、俯仰偏摆）带偏。
- **判据**：R-35a `light_curve.scans[].asymmetry_ratio >= 1.8`（峰两侧半峰斜率之比）；R-35b `light_curve.scans[].gaussian_fit_r2 <= 0.90`（A-38 命名 `<domain>.<fit_name>_r2`）且不对称方向在序列内**反号**；R-35c 垂直轴漂移 `light_curve.scans[].cross_axis_drift_counts >= 0.3 × light_curve.scans[].fwhm_counts`（取第二轴 `pos_fb` 或 `vision_y` 的窗内漂移量，不自选好看的），或 `light_curve.scans[].vision_angle_excursion_ratio >= 3`（相对该轴自身角度噪声底归一）；R-35d 不对称量与扫描起止位置相关（`light_curve.series_stats.asymmetry_vs_travel_spearman_rho >= 0.6`）而与时间不相关（排除 R-33）。
- **必要上下文**：至少两轴 `pos_cmd/pos_fb` 同步记录或视觉通道可用；`scanning` 段；阈值全部用比值或该轴自身 FWHM 归一，故 `counts_per_mm` 可缺。
- **排除项**：真像散/倾斜入射的不对称**与扫描位置无关、与 Z 离焦量相关**，此时禁止 `mechanical_*`，`considered` 记"像散/倾斜入射候选"、`not_evaluable` 记"像散/倾斜入射：无可用 cause slug（KB6 G-1 未采纳，裁决 A-16）"；`resonance.candidates[].present_in_dwell == true` → 先按 R-36；单轴记录、缺垂直轴与视觉 → `not_evaluable`；**"直线性/俯仰偏摆"无 slug（G-1 未采纳）**，故本条只在证据确实指向**紧固/松动**时才用 `mechanical_loose_structure`，纯几何直线性证据**不得**顶包成该 slug（C7 §7.2-4：近似 slug 顶包按归因造假处理），差额逐条记 `differential.not_evaluable`"直线性/俯仰偏摆：无可用 cause slug（KB6 G-1 未采纳）"。
- **建议动作**：`schedule_verification`（停机态人工检查）——导轨/镜架紧固复查、直线性复测；不给扭矩值、不生成补偿表。
- **期望效果依据**：`unverified`。
- **出处 tier**：`T2` + `T3`（合成含直线性误差的功率曲面）。**没有 T1**：DaRUS 是绳索驱动健康试验台，既无功率通道也无线性度真值。
- **适用边界**：`light_curve.scans[].n_points < 15` 时不对称比不可信 → `skipped`。

### R-36 噪声底上升与驻留段残余振动同源（含混叠警告）
- **family**: `mechanical_resonance`
- **断言**：功率曲线噪声底上升跟随伺服驻留段的残余振动；不是探测器本底，也不是接地/共模。
- **判据**：R-36a `light_curve.series_stats.noise_floor_trend_ratio >= 2`（相对基线）；R-36b `light_curve.scans[].snr_ratio <= 6`（`<= 6` 为劣化档）；R-36c `resonance.candidates[].present_in_dwell == true` ∧ `present_in_rest == false` ∧ `amplitude_ratio_vs_broadband >= 4`；R-36d 候选频点 `< freq_limits.reliable_band_hz`（C2 规则 7）**且**功率域频点声明 `< power_channel.reliable_band_hz`（**C7 §3.4-1**，`= power_channel.sample_rate_hz / 1.25`，沿用 C2 规则 7 余量式）；R-36e `abs(spectral.vel_fb.dominant_freq_hz − power_channel.noise_dominant_freq_hz) <= 0.05 × spectral.vel_fb.dominant_freq_hz`（同频；比值形式跨设备可比），**本条仅在 `power_channel.sample_rate_hz >= 2 × resonance.candidates[].freq_hz` 时可评估**（C7 §3.4-3 混叠折叠禁止），否则 `not_evaluable`。
- **必要上下文**：`dwell` 与 `rest` 段对比样本；`power_channel.dt_jitter_ratio` 可评估（否则噪声底升高可能来自采样抖动，见 R-31；`> 0.2` 时功率域频率类判据不启用，C7 §3.4-4）。
- **排除项**：电气共模/接地——功率噪声与 `global.cur_q_rms_a` 共模同相且频点是电流采样/开关频率的别名 → `electrical_current_loop_bandwidth`（另案，KB3）；探测器散粒/热噪声与运动无关，`resonance.candidates[].present_in_rest == true` 时本条不成立；上位机采样线程抖动（`event_context.host_pause_max_ms` + `power_channel.dt_jitter_ratio`）→ `software_induced_host_thread_jitter`。**混叠警告（C7 §3.4-3）**：功率通道 fs 极低，kHz 级机械谐振会**折叠**进低频、表现为"慢速功率波动"，`power_channel.reliable_band_hz` / `freq_limits.reliable_band_hz` 之外的频率一律 `not_evaluable`，**绝不允许**把折叠分量说成"找到了低频共振"。
- **建议动作**：`change_measurement_procedure`（先在 `rest` 态复测功率噪声底以分离探测器本底），随后走 KB3 的陷波/整形流程。
- **期望效果依据**：`rule_heuristic`（KB3 共振侧有仿真，耦合侧没有）。
- **出处 tier**：`T1-a`（DaRUS 真实低频驻留纹波/爬行，**仅机械侧形态**，不含耦合）+ `T2` + `T3`。
- **适用边界**：`power_channel.noise_dominant_freq_hz` 仅当 `power_channel.sample_rate_hz >= 20` 才允许非 null（C7 §2.2 A1）；`< 20` 时**不给任何频率结论**，只给噪声底相对量级（标 `[ratio]`，C7 §3.4-2）。

### R-37 只有峰值功率下降、峰形与峰位都稳定 → 禁止运动归因（门禁）
- **family**: `null`（**门禁/拒答规则类**，裁决 A-17；形式合法性见 **G-2**。本条**产出登记义务而非假设**：触发时写 `audit.rules_fired` + `differential.not_evaluable`，**永不产生 `hypotheses[]` 条目**）
- **断言**：FWHM、峰位、不对称度、噪声底都稳定而只有峰高下降时，运动侧**没有可解释该症状的自由度**（位置与形状都没变，能量不可能由位置误差丢失），此时任何机械/电气/软件归因都是幻觉。
- **判据**：R-37a `light_curve.series_stats.peak_power_drop_pct_vs_ref >= 30`；R-37b `light_curve.series_stats.fwhm_growth_pct_vs_ref < 20` ∧ `abs(light_curve.series_stats.peak_position_drift_counts) < 0.2 × light_curve.scans[].fwhm_counts`；R-37c `abs(light_curve.scans[].asymmetry_ratio - 1) < 0.2` ∧ `light_curve.series_stats.noise_floor_trend_ratio < 1.5`。三条同时成立才触发门禁。（`light_curve.scans[].fwhm_counts` 若撞 C7 §3.3-1 拒收红线，则 R-37b 不可评估 ⇒ 本条按"结构性不可评估"登记，与门禁触发**分开呈现**，C7 §8-3。）
- **必要上下文**：跨扫描序列；**Z 轴 `pos_fb` 与 `vision_angle` 在序列内无显著变化**（C1 通道级门禁，故写在此处而非判据，遵守 §0.3-2）；功率单位与量程在序列内一致（单位/量程切换会伪装成功率下降；`power_channel.unit == "V_raw"` ⇒ dB 类判据禁用，R-38b 不启用，C7 §2.2 A1）。
- **排除项**（逐项排除后才出门禁）：单位切换（µW ↔ dBm）、量程自动换挡、探测器污染（对照人为清洁记录）、光源/器件衰减（**`optical_device_degradation` 属 G-1，裁决 A-16 未采纳** ⇒ 无归因出口，只记 `considered`"器件/光源衰减候选"并在 `not_evaluable` 登记"器件功率衰减：无可用 cause slug（KB6 G-1 未采纳）"）、参考基线本身是坏点（`light_curve.series_stats.ref_scan_ids` 指向被截断扫描 → 先跑 R-41）。
- **建议动作**：`verdict.summary` 写"功率量级异常，运动侧证据不足"；填 `next_data_to_collect`（光路目检、换已知好的探测器/光源交叉、补 `temp` 通道）；`considered` 记自然语言候选；`overall_confidence <= 0.45`、`actionable: false`；**不得**输出 `hypotheses[]`；动作只允许 `rerun_step` / `request_data` / `schedule_verification`（C7 §8-2）。
- **期望效果依据**：`unverified`（无数字）。
- **出处 tier**：方法论依据 `C5 §2`（`none_of_the_above` 配额 ≥15%）+ `C3 硬性规则 9`；内容依据 `T2`。**本条是"拒答正确率"指标的耦合侧载体**（裁决 A-17 计入该指标），价值在于它**故意不产出结论**。
- **适用边界**：`light_curve.series_stats.ref_scan_ids` 为空（无基线）时 `skipped` 并登记覆盖度问题，不得当作"已排除"，也不得与门禁触发混写。

### R-38 平滑峰上叠加等间距台阶：量化，不是工件边缘
- **family**: `electrical_resolution_quantization`
- **断言**：高斯峰上叠加等间距台阶，台阶高度等于读数分辨率或位置分辩率对应的光功率增量 ⇒ 量化伪影而非真实功率阶跃。
- **判据**：R-38a `light_curve.scans[].step_count >= 3`（峰两侧斜率区间的等间距拐点数）∧ `light_curve.scans[].step_spacing_std_counts <= 0.2 × light_curve.scans[].step_spacing_counts`；R-38b `abs(light_curve.scans[].step_height_db − power_channel.quantization_step_db) <= 0.5 × power_channel.quantization_step_db`（台阶与读数分辨率同阶，比值判定；`power_channel.unit == "V_raw"` ⇒ 本条 dB 类判据禁用，C7 §2.2 A1）；R-38c 台阶间距与 `light_curve.scans[].point_step_counts × k` 一致（k ∈ {1,2,4}；步长权威出处 `scan_program.segments[].step_counts`，见 §C.3 第 14 行的循环论证封顶）；R-38d `crawling.low_speed_segments[].is_sawtooth == false`（否则转 R-39 爬行分支）。
- **必要上下文**：`dwell`/`probing` 段；`power_channel.quantization_step_db != null`（为 null ⇒ R-38 不启用，**不得**改判"无台阶"，C7 §2.2 A1）；扫描速度低于爬行阈值（否则台阶来源不唯一）；`meta.quality.quantization_step_counts` 仅作为轴指令量化存在的**门禁确认**，不作证据路径（§0.3-2）。
- **排除项**：机械爬行 → `mechanical_crawling`（R-39）；工件边缘/胶线遮挡 → 台阶**不等间距**且与 `vision_x/y` 边缘检测位置一致，记 `differential.considered`"工件遮挡候选"（**`process_workpiece_occlusion` 属 G-1，裁决 A-16 未采纳** ⇒ 差额记 `differential.not_evaluable`"工件遮挡：无可用 cause slug（KB6 G-1 未采纳）"）；`power_channel.n_samples < 20` → 分辨率不足，禁止判量化。
- **建议动作**：`change_measurement_procedure` —— 改用更高位数的模拟采集或提高读数平均次数；驱动器指令分辩率属设备侧，建议交回 KB3，本模块只给方向。
- **期望效果依据**：`unverified`。
- **出处 tier**：`T1-a`（DaRUS 真实量化步长与低速爬行，**不含耦合**）+ `T2` + `T3`。
- **适用边界**：`meta.counts_per_mm == null` 时 R-38c 仍可评估（纯 counts，C7 §3.3-3 门禁量全部无量纲），但**不得**把台阶换算成"nm 级分辩率不足"。

### R-39 迟滞回线：同一物理位置在曲线上出现两个读数
- **family**: `mechanical_crawling`
- **断言**：突破摩擦使小步进不产生位移、位移被累积后一次跳出，于是"功率—位置"在逼近段与退离段不重合（同一位置两个功率，或一段平台）。
- **判据**：R-39a `crawling.low_speed_segments[].stall_count >= 2`；R-39b `global.friction_stiction_ratio >= 1.5`；R-39c `crawling.low_speed_segments[].vel_min_ratio == 0` ∧ `crawling.low_speed_segments[].corr_vel_vs_curq <= 0.3`（电流在动、位置不动）；R-39d `light_curve.scans[].repeat_read_delta_db >= 2 × light_curve.scans[].noise_floor_std`（同一位置、逼近段与退离段各一次读数的差；需 `light_curve.scans[].direction_sequence` 含反向对，C7 §2.2 A2）。
- **必要上下文**：`scanning`/`probing` 低速段；`cur_q` 可用；需要 `vel_cmd`，或由 `pos_fb` 差分派生（带 `channels.vel_fb.derived`）并按 C1 派生规则 4 把置信度乘 0.7（C7 §2.3）。
- **排除项**：`ripple.probing[].correlated_with_cur_q >= 0.7` → `electrical_torque_ripple`；读数重复性差（探测器噪声）使 `light_curve.scans[].repeat_read_delta_db <= light_curve.scans[].noise_floor_std` → 转 R-36；步进指令本身不均（前瞻缓冲欠载，与 `event_context.interp_underrun_during_path > 0` 对齐）→ 转 `software_induced_interp_buffer_underrun`，且要求 `event_context.causal_claims_permitted == true`。
- **建议动作**：`change_measurement_procedure` —— 单向趋近 + 把步进加大到突破位移之上；机械侧处置（预紧/润滑/清洁）由 KB3 摩擦族给出。
- **期望效果依据**：`rule_heuristic`。
- **出处 tier**：`T1-a`（**DaRUS 的 `LdaFricIdent` / PreloadedLuGre 摩擦辨识是本条最强真实锚点**：stiction 与低速爬行在真实数据上可判）+ `T2` + `T3`；可验证的仅是"爬行可判"，**不含**耦合工序中的爬行后果。
- **适用边界**：`scanning` 与 `probing` 皆无 → `skipped`；无 `cur_q` → R-39c 不可评估。

### R-40 编码器每转周期误差伪装成功率曲线的周期性起伏
- **family**: `mechanical_encoder_periodic_error`
- **断言**：功率曲线上叠加的等周期起伏，其空间周期**锁定于编码器每转周期**，且用第二位置传感器交叉验证时位置误差存在、功率起伏仍在 ⇒ 位置**测量**误差被写进了"位置—功率"关系，看起来像光斑畸变。
- **判据**：R-40a `light_curve.encoder_masquerade.residual_period_ratio_to_per_rev ∈ {1, 1/2, 1/3}`（比值属"每转族"才成立，C7 §2.2 A7）；R-40b `light_curve.encoder_masquerade.residual_amplitude_counts >= 0.15 × light_curve.scans[].fwhm_counts`；R-40c `encoder.per_rev_periodic_present == true` ∧ `encoder.phase_locked_to_pos_modulo == true` ∧ `encoder.detrended_r2 >= 0.5`；R-40d `light_curve.encoder_masquerade.amplitude_ratio_vs_encoder_per_rev = residual_amplitude_counts / encoder.per_rev_amplitude_counts ∈ [0.5, 2]`；R-40e 周期与 `bandwidth.position_loop_crossover_hz` 无关（低频 ⇒ 非伺服环极限环）。
- **必要上下文**：`scanning`/`probing` 段；丝杠导程/减速比元数据（否则每转周期不可知，降级为"每 `quality_ref.motor_rev_counts` 周期"并截断置信度）；至少两套位置测量可交叉验证（`meta.encoder_lines` + 光栅/第二编码器，或 `vision_x/y`）；**无第二传感器时 `light_curve.encoder_masquerade.agrees_with_second_sensor` 必须为 `null`，不得填 `true`**（C7 §2.2 A7）。
- **排除项**：伺服自激（`step_response[].limit_cycle_present == true` 且频率与环带宽相当）→ `electrical_position_pi_detune` 叙事由 KB3 处理；丝杠螺距误差的周期 = 导程 ≠ 每转编码器周期，此时 R-40a 不成立 → `differential.considered` 记"丝杠周期误差候选"（**G-1 未采纳，裁决 A-16** ⇒ 无归因出口时记 `differential.not_evaluable`）；无第二传感器 → `confidence <= 0.5` 并填 `next_data_to_collect`。
- **建议动作**：`request_data`（补采第二位置传感器）+ `schedule_verification`（螺距/编码器误差补偿表由设备侧流程重建，本模块不生成）。
- **期望效果依据**：`unverified`。
- **出处 tier**：`T1-a`（**DaRUS 的三套独立位置测量是"伪装"类判据的真实检验台**，见 KB7：可在真实数据上量化并复刻该假象）+ `T2` + `T3`。
- **适用边界**：A 组唯一有较强真实锚点的规则，但锚点验证的是**传感器不一致的形态**，不是耦合工序。

### R-41 扫描被中断/超时截断：记录里的"峰"只是窗口边缘
- **family**: `software_induced_bus_cycle_miss`
- **断言**：序列未按预期点数完成（丢拍或超时中止）、曲线在边缘被切断，于是"峰值"出现在扫描窗边缘——这是数据完整性问题，不是工艺现象。
- **判据**：R-41a `light_curve.scan_integrity.truncated_flag == true` ∨ `light_curve.scan_integrity.actual_point_count < light_curve.scan_integrity.expected_point_count`；R-41b `light_curve.scans[].peak_index ∈ {0,1,2, n_points-3, n_points-2, n_points-1}`（首末 3 点 ⇒ C7 §3.3-4 按数据完整性处理）；R-41c `light_curve.scan_integrity.edge_slope_ratio >= 0.5`（= 窗口边缘斜率 ÷ 峰侧最大斜率，**无量纲** ⇒ 缺定标系数也可判；边缘仍有斜率 ⇒ 真峰在窗外）；R-41d `event_context.network_cycle_miss_count > 0` ∨ `process` 源超时事件落在该 `scanning` 窗内（`light_curve.scan_integrity.event_overlap_sources[]` 非空，且只能取 C6 `source` 词表值，C7 §2.2 A5）。
- **必要上下文**：`event_context` 可用；`scanning` 段有预期点数——**`light_curve.scan_integrity.expected_point_count` 的权威出处是 `scan_program.segments[].n_points_expected`，不得由实际点数反填**（C7 §2.2 A5 / §5 硬规则 1）；事件—波形对齐 `event_context.sync.verified == true`；`light_curve.scan_integrity.host_pause_during_scan` 与 `tail_gap_ms` 可用。
- **排除项**：真工艺最优恰在边缘——必须**两次**独立扫描都落在同一边缘 ∧ `light_curve.scan_integrity.actual_point_count == expected_point_count`（无丢拍证据）；否则本条**首先怀疑数据**，因为它比"光斑刚好贴在扫描窗边界"常见得多。
- **建议动作**：`change_measurement_procedure` —— 扩大扫描窗、补齐丢拍后复扫。本条**不触发任何恢复动作**（C6 §5：恢复 = `field_procedure` 文本，由人执行）。
- **期望效果依据**：`unverified`；首要动作是把该样本标为 `insufficient_data`，而不是给根因。
- **出处 tier**：`T2` + `T3`（合成丢拍/截断样本）。
- **适用边界**：`event_context.sync.verified == false` 时事件与截断时刻只能作共现，本条**不得**写 `software_induced_bus_cycle_miss` 进 `hypotheses[]`——改按 `family: null` 的门禁类登记义务处理（裁决 A-17：进 `audit.rules_fired` + `differential.not_evaluable`），或降级为 `insufficient_data`。

### R-42 采样—运动互斥检查失败：settle 窗不足，读数采到运动中的值
- **family**: `software_induced_settle_window_too_short`
- **断言**：驻留窗短于"轴稳定时间 + 功率计积分时间"，读数落在仍在衰减的振铃期内 ⇒ 采到的是运动中的功率，表观峰位系统性偏向扫描反方向，且峰可能从未被真正采到。与 R-31 的分工：R-31 是连续扫的空间平均，本条是**逐点驻留测量的时序窗设计错误**。
- **判据**：R-42a `light_curve.motion_sampling_conflict.samples_in_motion > 0`；R-42b `light_curve.motion_sampling_conflict.settle_gap_ms < required_settle_ms`，其中 **`required_settle_ms = step_response[].settling_time_ms + power_channel.integration_time_ms`**（两侧任缺即 `null`；定义式已契约化于 C7 §2.2 A4，§A.3 陷阱 2）；R-42c `light_curve.motion_sampling_conflict.step_over_fwhm_ratio > 0.15`（`= point_step_counts / fwhm_counts`，步进档位已越过可辩护界；`> 1/3` 触发 C7 §3.3-1 拒收）；R-42d `light_curve.motion_sampling_conflict.peak_never_sampled_flag == true` ∨ `apparent_peak_lag_over_step_ratio ∈ [0.3, 0.7]`（滞后≈半个窗 ⇒ 平均中心被拉回）。a∧b 触发，c/d 决定归因强度。
- **必要上下文**：`dwell` 段存在且能与 `settling` 区分；步进/驻留/预期点数的权威出处是 **`scan_program.segments[].{step_counts, dwell_ms, n_points_expected, feedrate_counts_s}`**（C7 §5 硬规则 1；`scan_program` 或其 `source` 缺失 ⇒ 依赖步长的子条件一律 `not_evaluable`，C7 §1.2-4；`source == "inferred_from_waveform"` 时按 §C.3 第 14 行封顶）；`step_response[].settling_time_ms` 为**同方向同幅度**实测值（缺失时本条退化为 T2 经验值并按 §C.3 第 7 行截断）。
- **排除项**：`light_curve.motion_sampling_conflict.samples_in_motion == 0` ∧ `light_curve.motion_sampling_conflict.settle_gap_ms >= required_settle_ms` → 采样时序无缺陷，转 R-31（若仍在动扫）或 R-35（形变）；时基本身不稳（`meta.quality.dt_jitter_ratio > 0.2`，C1 红线）→ 先 `insufficient_data`；读数时刻来自 `power_channel.timestamp_source == "host_poll"` → M-d 失败，只能作共现（§A.3 表）；声明步长与实测位移交叉校验 `abs(scan_program.segments[].step_counts − light_curve.scans[].point_step_counts) / light_curve.scans[].point_step_counts > 0.2` ⇒ 先质疑**分段质量或采样元数据**，不得强行套本条（C7 §5 硬规则 4）。
- **建议动作**：`change_measurement_procedure` —— 把驻留窗加长到 `required_settle_ms` 以上，或减小步进使同一驻留窗内残余位移可忽略；整定变更后必须重估 `required_settle_ms`（§A.3 陷阱 3）。
- **期望效果依据**：`rule_heuristic`；可检验量 `light_curve.motion_sampling_conflict.in_motion_sample_ratio → <= 0.1`、`apparent_peak_lag_over_step_ratio → <= 0.15`（合成曲面上可定量验证）。
- **出处 tier**：`T2`（稳定时间与仪器积分窗的定义）+ `T3`（几何推导 + 采样复现，见 §A.3）。
- **适用边界**：`scanning` 有而 `dwell` 无（逐点测量被误标成扫描）→ R-42b 不可评估，并把"分段质量"本身作为发现上报（§C.2 双向原则）。

## A.3 爬山寻峰与伺服整定的耦合陷阱

这一节不是判据，而是判据背后的**可辩护物理**；每条都落到一个可判定的检查项。

### 陷阱 1：步进过大跳过最优点

单模光纤耦合效率近似为高斯（基模）：

```
P(x) = P₀ · exp(-2·(x - x₀)² / w²)     w = 模场半径，FWHM = 2√(2·ln2)·w ≈ 1.1774·w
峰被跳过、锁定点落在 x₀ ± step/2（最坏情况，等步长）：ΔP/P₀ = 1 - exp(-2·(step/2)² / w²)
  step/FWHM = 0.5 → ΔP ≈ 30%   不可接受        step/FWHM = 0.2 → ΔP ≈ 5.4%  边缘（与探测器噪声同阶）
  step/FWHM = 0.1 → ΔP ≈  1.4% 可辩护（≈0.06 dB）
工程结论（可判定）：point_step_counts <= 0.1 × fwhm_counts
  步长权威出处 = scan_program.segments[].step_counts（C7 §5 硬规则 1）；本界已契约化为 C7 §3.3-5
```

比较式爬山在 `step > fwhm/4` 时越过峰顶、反向后在另一侧又越过，形成围绕峰值的**极限环式来回**：
`light_curve.motion_sampling_conflict.direction_reversal_count` 持续增长而 `light_curve.scans[].peak_power` 不提高 ⇒ 判"步进档位错误"，
而不是"没有峰"（这正是新手最常犯的误读）。

### 陷阱 2：settle 窗不足采到运动中的值

每个测量点必须"**先停稳，再积分**"，且积分窗整体落在驻留窗内：

```
t_move_end = 该点最后一次速度指令归零的时刻；τ_axis = step_response[].settling_time_ms；τ_int = power_channel.integration_time_ms
要求：t_read_start >= t_move_end + τ_axis   且   t_read_start + τ_int <= 下一运动段起点
不满足：读数 = 积分窗内功率的空间平均，偏差量 ~ (dP/dx)·v·τ_int；匀速扫段表观峰位偏移（一阶近似）apparent_peak_lag ≈ -v·τ_int/2
```

**可判定的「采样—运动」互斥检查项**（**C7 §2.2 A4** 已把这 5 个子条件落成 `light_curve.motion_sampling_conflict.*` 字段）：

| 检查项 | 通过条件 | 失败时归因方向 |
|---|---|---|
| M-a 静止判据 | 读数窗内 `vel_fb` 全程 `< 0.1% ×` 该点逼近速度，且 `abs(fe) < step_response[].settle_band_counts` | R-42 `software_induced_settle_window_too_short` |
| M-b 积分窗包含 | `t_read_start >= t_move_end + τ_axis`（τ_axis 与 `scan_program.segments[].dwell_ms` 一起决定 M-b/M-c，C7 §2.2 A4） | R-42 |
| M-c 读数落在驻留内 | 读数时刻位于同一 `dwell` 段 `[t0,t1]` | R-31 `software_induced_polling_latency` |
| M-d 时间戳语义 | `power_channel.timestamp_source == "device"`，否则按 `±poll_period/2` 计入不确定度（`power_channel.align_residual_ms <= event_context.sync.uncertainty_ms` 即作废，C6 硬规则 2） | `sync` 降级、禁因果（C2 规则 8） |
| M-e 窗内运动占比 | `light_curve.motion_sampling_conflict.in_motion_sample_ratio <= 0.1` | R-31，或 `insufficient_data` |

### 陷阱 3：伺服整定与寻光互相打架

- 峰值附近 `dP/dx → 0`，所以功率噪声换算成位置噪声会**发散**：`δx_eq = σ_noise / |dP/dx|`，锁定抖动 `σ_lock ≈ δx_eq`。整定越"软"（振铃衰减慢）或 `light_curve.scans[].noise_floor_std` 越高，`peak_lock` 跟随误差越大 ⇒ 表现为"锁定不稳"，根子却在采样时刻或整定，不在光路。**可判定**：`light_curve.motion_sampling_conflict.lock_track_noise_ratio`（锁定后功率相对标准差 ÷ 扫描期功率相对标准差）`> 1.5` → 锁定在追噪声，不是追峰。
- 提高刚性以求"更快稳定"会把高频微振放进功率通道（R-36）；加低通/陷波延长等效稳定时间 → `light_curve.motion_sampling_conflict.required_settle_ms` 变大。只调整定而不重估采样窗，就会得到"整定变好但耦合变差"的假矛盾。**任何 `step_response[].settling_time_ms` 变化都必须触发 `required_settle_ms` 重估**——这是本模块最内行、且在合成数据上完全可检验的一条陈述。
- 因此 KB6 与 KB3 的接口不是"各说各话"：整定类动作（KB3）与测量步骤类动作（KB6）在同一次建议里必须互相声明对方的前置条件，否则互相抵消。

### 陷阱 4：dither 锁峰频率与机械周期混淆

调制—解调（dither）本身给功率一个激励频率 `f_dither`，`light_curve.scans[].dither_amplitude_counts`（与 `scan_program.segments[].dither_amplitude_counts` 交叉校验）应 ≈ `0.1 × light_curve.scans[].fwhm_counts`。当 `f_dither` 接近丝杠周期/编码器每转周期/伺服环带宽时，锁峰会停在系统相位误差处——峰位偏，但**偏移量与 `f_dither` 相关、与配方无关**。可判定：两次不同 `f_dither` 的锁定峰位差 `>= 0.3 × light_curve.scans[].fwhm_counts` ⇒ 优先怀疑 dither 频率选择而非机械（与 R-40 的区分靠 `light_curve.encoder_masquerade.residual_period_ratio_to_per_rev`）。**`peak_hold` 段缺 `scan_program.segments[].dither_freq_hz` / `dither_amplitude_counts` 时，本混淆分支不启用**（C7 §2.2 `scan_program` 口径）。

## A.4 数据可得性诚实声明与合成检验设计

### A.4.1 诚实声明

**本项目没有真实耦合产线数据。** 具体边界：

1. **T1-a（DaRUS）不含 `laser_power`**、不含耦合工序，是绳索驱动/直驱健康试验台（fs = 1 kHz）。因此 A 组**没有任何一条规则**能在 T1-a 上验证其"耦合结论"。T1-a 只支撑三类**子事实**：(a) 低速爬行与 stiction 可被判出（R-39）；(b) 多传感器不一致/编码器每转周期误差可被量化并复刻为"伪装"（R-40）；(c) 驻留段残余振动与纹波可被量化（R-36 的机械侧形态）。
2. **T1-b（CWRU / Paderborn / Aalto / MFPT）无位置环、更无功率通道**，只用于"机械 vs 电气归因分类器"的通用性，**不用于** A 组任何阈值。
3. **A 组阈值的主要来源是 T2**，且当前档位一律是 **`public-doc`（公开手册/文献数值，未经现场核对）**，
   不是"已核对的参数类别"（A-31：措辞强度不得高于 `source_tier`；本文件没有任何一条 A 组数值
   被真实功率计或产线数据核对过）。要升格需要的是**实测**，不是再读一遍手册。各条现状：
   功率计手册的积分时间/读数速率档位（R-31/R-34/R-42，`public-doc` + 待厂商确认）、
   单模耦合的高斯模场近似与 `step/FWHM` 关系（陷阱 1，**几何推导、自足可复算、不依赖厂商数值**，
   这条不受本档约束）、固化收缩/温漂的已知效应类别（R-33，只给方向不给数值，`literature`）、
   伺服侧摩擦与周期误差（R-39/R-40，KB3 已登记出处）。
4. **T3（KB5 合成）只证明管线跑通**：C5 硬规则"指标按层分别报告、禁止合并成总数"对 KB6 的含义是 A 组规则**永远不得**出现在"根因 Top-3 命中率"的 T1+T2 报告里。
5. **禁用表述**（文档与作品集都不许出现）："在客户产线验证"、"现场诊断案例"、"耦合良率提升 X%"、"真实光功率数据"、"与厂商工程师确认"。允许的最强表述：**"判据阈值取自文献并给出推导；可检验性在合成数据上演示；机械/电气侧子事实用公开真实数据集交叉验证。"**

### A.4.2 合成检验设计（T3；防自验证循环）

AUDIT §二：minimax 栽在"自己造格式 → 自己写解析 regex → 静态查表得根因 → 宣布全部检出"。KB6 必须**结构性**避免同源，而不是口头承诺：

1. **参数不写进 detector**：合成参数空间独立于规则阈值——`step/fwhm ∈ {0.05, 0.1, 0.2, 0.5, 1.0}`、`τ_int/τ_axis ∈ {0.1, 0.3, 1, 3, 10}`、`直线性误差 ∈ {0, 0.05, 0.2} × fwhm`、`每转周期误差 ∈ {0, 0.15, 0.4} × fwhm`、`write_back_delay/poll_period ∈ {0.2, 1, 3}`、`丢拍率 ∈ {0, 2%, 10%}`、`dither 频比 ∈ {0.8, 1, 1.25}`；阈值在冻结前不得看结果调（C5 §2 冻结纪律）。
2. **真值由参数空间给出，不由文本映射给出**：`truth.json` 记录植入的误差参数与 `forbidden_conclusions[]`（C5 §2 字段），不是"缺陷号 → 原因"的静态查表。
3. **必含对抗性案例**：**双故障**（采样窗过长 + 每转周期误差 → 期望**两条** `hypotheses` 且第二条带 `contradicting_evidence`，不是二选一）；**none_of_the_above**（只有器件功率衰减、峰降形不变 → 正确答案是 R-37 门禁触发 + 不下运动归因，若编出机械原因即判错，此类 ≥15%）；**sync 未验证**（`sync.verified = false` → 所有 `software_induced_*` 应进 `not_evaluable`）；**缺 `counts_per_mm`**（阈值必须走 counts/ratio、报告印 `[counts]`，出现 µm 数字即判失败）。
4. **分层报告**：`T2 阈值合法性` / `T3 管线跑通 + 对抗性拒答` / `真实数据仅覆盖子事实 (a)(b)(c)` 三块分开，不合并成一个分数。

---

# B. 标定诊断子模块

> **本组 tier 纪律（裁决 A-24，收口 M-4）**：本项目**不新增 T0 词汇**，采用 **T1-c「自采真实测量（非产线）」**——
> 仅当同时具备**自建工装 + 相机 + 轴实测 + 自记温度**时才可登记 T1-c；**拿不到就明说标定模块只有 `T2 + T3`**。
> T1-c **禁止**与 T1-a / T1-b 混算任何能力指标（分母分开、分层报告，C5 §1）。本文 B 组规则的 `出处 tier`
> 一律按此口径写，正文不把 T2 方向性依据包装成实测。

## B.1 标定链路与残差的形态学

### B.1.1 链路

```
① 像素 ↔ 物理：九点 / N 点网格标定 → 仿射或单应系数（比例、旋转、错切、平移）
② 手眼标定：相机固连于轴（eye-in-hand）或固定（eye-to-hand）→ AX = XB 求解变换
③ 旋转中心：θ 轴回转中心 (x_c, y_c)，由多角位打点拟合圆
④ 镜头支架温漂：倍率随温度变化（支架/镜筒 CTE 失配 + 焦距漂移）→ 比例系数缓慢漂移
⑤ 上述系数写入控制器/上位机 → 折算成 C1 的 meta.counts_per_mm / counts_per_deg
```

**闭环是本模块的骨架**：标定系数 → 决定 `meta.counts_per_mm` → 决定"能不能说 µm"（C1 单位红线、KB0 §5）→ 而标定残差本身又是诊断证据。即**标定既是被诊断对象，也是单位结论的前提**：一条残差趋势判据的结论是"这套系数在漂"，动作是"热稳态后重标 + 查温漂"，同一件事同时也在说"这批 µm 结论不可信"。这层自反性是本模块最有辨识度的地方。

### B.1.2 "标定残差"在数据里的形态

残差 = 标定后实测位置与预测位置之差。**必须记录矢量场**（每点 `(dx_i, dy_i)`）；只存标量 RMS 会毁掉方向信息。

| 形态 | 场特征 | 主要指向 |
|---|---|---|
| 随机散布 | 无空间相关（`calibration.field_pattern.morans_i ≈ 0`）、各向同性 | 重复性/噪声（视觉、照明、工件摆放、量化） |
| 线性梯度 | 沿某轴单调变号或同向增大，低阶拟合 `r²` 高 | 比例/错切/旋转系数错，或尺度随时间漂移（温漂） |
| 台阶/分段 | 前后子组均值显著跳变、段内平坦 | 松动、拆装后未复标、换型覆盖参数 |
| 符号模式 | 径向分量同号 / 切向分量同号 | 比例错（径向同向）vs 角度错（切向同向）vs 中心偏（整体平移） |

`calibration.field_pattern.dominant_pattern` 就是把这四类落成可计算标签（字段口径权威在 **C7 §4.2**；纯文档伪代码）：

```
残差场 ≈ 平移 t=(t_x,t_y)（中心偏/零点偏）+ 线性 [[k11,k12],[k21,k22]]·(x,y)（比例+错切+小旋转的复合）+ 高阶多项式残差（真实畸变/安装误差）
calibration.field_pattern.linear_fit_r2 = 1 - ‖残差 − 低阶拟合‖² / ‖残差‖²          // A-38 命名 <domain>.<fit_name>_r2
calibration.field_pattern.morans_i      = 空间自相关系数（邻域取网格最近邻，≈ 0 ⇔ 随机散布）
calibration.field_pattern.dominant_pattern ∈ {random, linear_gradient, step, radial, tangential, mixed}
calibration.sessions[].systematic_share_pct = ‖mean(dx,dy)‖ / rms_residual_counts × 100（把"偏"与"散"分开）
calibration.sessions[].isotropic_ratio      = σ_major / σ_minor（散布是否有方向；n_points < 12 不稳 ⇒ skipped）
```

**载体与粒度（裁决 A-39）**：`calibration.field_pattern` 是 `calibration.jsonl` 里**每个标定批次一份**的同名行内对象（**段 = 批次**）；"按 recipe 切"与"按时间半段切"只是批次的两种归组方式，跨段统计一律走 `calibration.series`。低阶系数 `{k11,k12,k21,k22,tx,ty}` 只用于形态分类，不反解标定系数、不生成补偿（§0.1 边界 + C7 §1.3）。

## B.2 可编码判据 R-43 … R-50

**B 组通用纪律（先于任何子条件生效，权威在 C7 §4）**
1. **载体与路径**：`calibration.jsonl` 一行一个批次（`record_type == "session"`），C3 引用一律写 **`calibration.sessions[].*`**（数组下标按 `timestamp_s` **升序**重排，不是文件顺序）；跨批次累计量由**唯一一条** `record_type == "series"` 尾行承载 ⇒ **`calibration.series.*`** / **`calibration.correlation_screen.*`**（C7 §4.1，裁决 A-37；**不移进 `process.json`**，否则制造假的样本级可复现性）。
2. **段 = 批次（裁决 A-39）**：每批次一份 `calibration.field_pattern`；分段统计只走 `calibration.series`，**禁止**在单个 `field_pattern` 对象上再切段。
3. **因果开关**：唯一来源是 C2 `event_context.causal_claims_permitted`；`calibration.jsonl` **不定义自己的 `sync`**；无 `events.jsonl`、`sync.verified == false` 或 `sync.method == "unknown"` 时 R-47/R-48 **只能报共现与相关、不得报因果**，且标定记录若无 `event_context` 因果开关**默认 `false`**（C7 §4.3，收口 M-3）。
4. **`spec` 与单位**：`calibration.spec == null` ⇒ R-49 `skipped`，**禁止**用内部统计限冒充客户限；`meta.counts_per_mm == null` ⇒ 一律 counts/像素、报告印 `[counts]`、**禁止 µm**（C7 §4.4）。`calibration.spec.*` 是**门禁字段，禁入 `supporting_evidence[]`**（C7 §7.1 #8–12）。
5. **缺档**：`calibration.jsonl` 缺失 ⇒ B 组全部 `blocked` 并登记"无标定批次记录"（C7 §1.2-2）。

### R-43 残差场存在线性梯度且随温度单调
- **family**: `mechanical_thermal_drift`
- **断言**：残差沿某坐标单调变化（低阶几何模型可解释大部分方差）且与温度相关 ⇒ 镜头支架温漂/机械尺度漂移，而不是"标定没做好"。
- **判据**：R-43a `calibration.field_pattern.linear_fit_r2 >= 0.6`（A-38 命名；定义式 `= 1 - ‖残差 − 低阶拟合‖² / ‖残差‖²`，C7 §4.2）；R-43b `calibration.correlation_screen.with_temp_r >= 0.7`（∧ `event_context.causal_claims_permitted == true`，否则只报共现）；R-43c `calibration.sessions[].trend_slope_counts_per_index` 同号 ∧ `calibration.sessions[].spearman_rho >= 0.7` ∧ `calibration.sessions[].trend_p_value <= 0.05`（效应量与显著性必须同时出现，§0.3-3）；R-43d `calibration.sessions[].residual_rms_second_half_counts / residual_rms_first_half_counts >= 1.5`。
- **必要上下文**：温度通道或室温记录；标定时间戳与换型标签（`calibration.sessions[].timestamp_s` 用 C1 时间基准）；`calibration.sessions[].n_points >= 9`；同一配方、同一工装、同一操作者（否则混杂变量不可分）。
- **排除项**：梯度只在单次标定内出现、跨标定不重复 → 是**畸变未建模（高阶项）**、非时变（**`calibration_model_unmodeled_distortion` 属 G-1，裁决 A-16 未采纳** ⇒ 只记 `differential.considered`，并在 `differential.not_evaluable` 登记"高阶畸变未建模：无可用 cause slug（KB6 G-1 未采纳）"）；主方向随执行者变化 → 执行差异；台阶与配方事件对齐 → 转 R-47；`r >= 0.7` 但因果开关为 false → **只报共现，不下 cause**。
- **建议动作**：`change_measurement_procedure` —— `field_procedure` 给出"热稳态后重标 + 记录标定时的温度"；不做温补曲线（§0.1）。
- **期望效果依据**：`unverified`。
- **出处 tier**：`T2`（镜头/支架温漂与 CTE 失配是光学工程已知效应，**方向性**）+ `T3`（合成含温漂比例的网格）；有自建工装实测时可加 **T1-c**（A-24，禁止与 T1-a/T1-b 混算）。**无 T1-a/T1-b。**
- **适用边界**：`meta.counts_per_mm == null` 时残差与斜率一律报 counts 或像素；**禁止**输出"每 °C 漂 X nm"；温度序列与标定时间戳**异源**时 `calibration.correlation_screen.with_temp_r` 只作共现，该假设写进 `audit.assumptions`（C7 §4.3-4）。

### R-44 残差场出现台阶且无温度关联：紧固/松动或拆装未复标
- **family**: `mechanical_loose_structure`
- **断言**：同一配方/工装下残差场在两个子组之间均值显著位移、段内平坦、无温度证据 ⇒ 机械松动或拆装后未复标。
- **判据**：R-44a `calibration.sessions[].split_shift_counts >= 2 × calibration.sessions[].rms_residual_counts` ∧ Welch t（不等方差）`split_p_value <= 0.05` ∧ `calibration.sessions[].split_ci_counts` 不含 0（**只看"均值变大"不合法**，C7 §4.2）；**R-44b（裁决 A-39：段 = 批次）**：各**批次**的 `calibration.field_pattern.linear_fit_r2` 在其所属段内均 `< 0.3`（段内无梯度 ⇒ 纯平移台阶）——"按 recipe 切"与"按时间半段切"只是**批次的两种归组方式**，分段统计一律引用 `calibration.series`（`calibration.series.segment_break_points[]` / `control_limits[]` 按段），**禁止**在单个 `calibration.field_pattern` 对象上再切段；R-44c `calibration.correlation_screen.with_temp_r < 0.5` 或温度在两段间无显著差；R-44d 无 recipe 变更事件（否则归 R-47），可选 `event_context.step_labels[]` 中有该轴冲击/手动 jog 记录共现。
- **必要上下文**：`calibration.series.n_sessions >= 2` 的可配对标定，同一配方/工装/操作者；分组标签可用（`calibration.sessions[].{recipe, fixture_id, operator}`）。
- **排除项**：**`calibration.series.n_sessions == 1` 时"分前后半"不是松动证据**（那是一次标定内部的空间梯度 → R-43 或高阶畸变）——这条必须写进规则，因为它是最容易犯的过度解读；台阶与维护/拆装记录共现 → 归"未复标"（**G-1 未采纳，裁决 A-16** ⇒ 只写自然语言 `considered` 并登记 `not_evaluable`）。
- **建议动作**：`schedule_verification`（停机态人工复紧/复标）；`writes_to_device: false`。
- **期望效果依据**：`unverified`。
- **出处 tier**：`T2` + `T3`（有自建工装实测时可加 **T1-c**，A-24）。
- **适用边界**：分组均值必须用 Welch t 或 bootstrap CI，不许只看"均值变大"；样本量不足 → `skipped`，**不得**说"无松动"。

### R-45 残差随半径线性放大：比例/脉冲当量系数错（可无量纲判定）
- **family**: `software_induced_pulse_eq_overwritten`
- **断言**：残差矢量呈**径向**分布且幅值随离参考中心的距离线性增长 ⇒ 网格真实间距与软件系数不一致（比例错 / `counts_per_mm` 被覆盖）。
- **判据**：R-45a `abs(calibration.sessions[].radial_slope_ratio) >= 0.005`（0.5% 尺度误差；**无量纲** ⇒ 缺定标系数也能判，但报告禁 µm，C7 §4.2/§4.4-3）；R-45b `calibration.sessions[].radial_sign_pattern` 全同号（⇒ 尺度问题而非局部缺陷；异号 ⇒ 高阶畸变候选，**无 slug**，只记 `considered`，A-16）；R-45c `abs(calibration.sessions[].tangential_mean_ratio) <= 0.3 × abs(radial_slope_ratio)`（排除旋转系数错）；R-45d `calibration.sessions[].systematic_share_pct >= 60`（方向性显著，定义式 `= ‖mean(dx,dy)‖ / rms_residual × 100`，见 §B.1.2 / C7 §4.2）。
- **必要上下文**：`calibration.sessions[].n_points >= 9` 且网格覆盖 `>= 2 ×` 视场半径；`meta.counts_per_mm` 与系数来源可追溯；配方标签（`calibration.sessions[].recipe` 必须与 C6 `machine_context` 同源，C7 §4.2）。
- **排除项**：台阶与 recipe/换型事件对齐 → **优先 R-47**（同 family，但事件对齐给出更强的软件归因，两者不得各自独立计权）；同时存在明显旋转分量（`calibration.sessions[].tangential_mean_ratio` 显著）→ 比例 + 角度复合（`calibration.field_pattern.dominant_pattern == "mixed"`）；`calibration.sessions[].isotropic_ratio > 3` → X/Y 单轴比例错而非统一尺度；标定板等级不足（`calibration.sessions[].plate_grade` 粗于工艺要求）→ **禁止**把残差归因于系数（记 `differential.not_evaluable`，C7 §4.2）。
- **建议动作**：`rerun_step`（重跑标定，先校验脉冲当量）；`field_procedure` 明确要求"复测一次并对比 `meta.counts_per_mm` 是否被换型流程覆盖"。跨厂商单位口径差 1000 倍的事故模式（AUDIT §一：`pulse/s` vs `单位/秒`）是本条的真实动机，**但只借用其记录的现象，不借用其任何检出率声明**。**A-87 的分界**："`_unit`/口径混用必然差 1000 倍"属第 ② 类（逻辑自洽，可作判据）；"这台设备当前用的是哪一套口径、当量值是多少"属第 ③ 类（约定真值，只能进待确认清单，恒 `rule_heuristic`）。
- **期望效果依据**：`rule_heuristic`（重标后残差回落方向，不给百分比）。
- **出处 tier**：`T2`（跨厂商控制卡手册单位/分频口径对比）+ `T3`。
- **适用边界**：本条的设计要点是**尺度误差可无量纲判定**——缺 `meta.counts_per_mm` 时仍可评估，但报告**不得**换算 µm。

### R-46 残差有系统性方向分量（非各向同性）：角度系数/安装角/偏心
- **family**: `mechanical_loose_structure`
- **断言**：残差均值向量显著非零且主方向集中 ⇒ 不是重复性差，而是有确定性方向偏差。
- **判据**：R-46a `calibration.sessions[].mean_residual_counts.mag >= 0.5 × calibration.sessions[].rms_residual_counts`；R-46b `calibration.sessions[].systematic_share_pct >= 40`；R-46c `calibration.sessions[].isotropic_ratio >= 2.5`（`σ_major / σ_minor`，`n_points < 12` 时不稳 ⇒ `skipped`）；R-46d 主方向 `calibration.sessions[].mean_residual_counts.dir_deg` 在多次标定间稳定（极差 `< 15°`）。
- **必要上下文**：**矢量**残差 `calibration.sessions[].residual_vectors_counts[]`（每点 `(dx,dy)`；只存标量 RMS 即毁掉方向信息，C7 §4.2；全量走 `.npy` 旁路）；`meta.counts_per_deg` 可用；所有 session 使用同一坐标系定义与同一 `calibration.sessions[].axis_group`。
- **排除项**：`calibration.sessions[].tangential_mean_ratio` 显著且与半径成正比 → 旋转系数错（R-45 复合分支）；低阶模型以平移为主 → 零点/中心偏（交给 R-49 作验收判定即可，不必强给根因）；`dir_deg` 每次标定都变 → 工装/工件定位随机性主导 → 转 R-48 的相关性筛查，**cause 留空**：`calibration_fixture_repeatability` 属 **G-1，裁决 A-16 未采纳** ⇒ 记 `differential.considered`"工装/工件定位重复性候选"并逐条登记 `differential.not_evaluable`"工装/标定板批次效应：无可用 cause slug（KB6 G-1 未采纳）"；**禁止**用 `mechanical_loose_structure` 顶包（C7 §7.2-4 按归因造假处理）。
- **建议动作**：`rerun_step`（重标）+ `schedule_verification`（相机/镜头安装角人工复查）。
- **期望效果依据**：`unverified`。
- **出处 tier**：`T2` + `T3`。
- **适用边界**：`calibration.sessions[].n_points < 12` 时 `σ_major/σ_minor` 不稳 → `skipped`。

### R-47 换型/换配方后残差突变：与 C6 事件对齐
- **family**: `software_induced_pulse_eq_overwritten`
- **断言**：残差统计量在配方切换点前后构成两个统计上不同的总体 ⇒ 换型流程覆盖了标定派生的运动参数，而不是设备逐渐变差。
- **判据**：R-47a `calibration.sessions[].residual_rms_second_half_counts / residual_rms_first_half_counts >= 2.0`（**R-47 的"两组"定义 = 配方边界，不是时间中点**，C7 §4.2；组间比较即"批次归组"，裁决 A-39）；R-47b Mann-Whitney U（双侧）`p <= 0.01`，两组各 `n >= 5`；R-47c 台阶位置与 `event_context.step_labels[]` 的 recipe 变化同一时刻 ∧ `|Δt| > event_context.sync.uncertainty_ms`（对齐可分辨才算证据；断点须登记进 `calibration.series.segment_break_points[]`，`reason == "recipe_change"`）。
- **必要上下文**：`event_context.available == true` 且配方标签存在；否则只能按时间分半 → 结论必须降级为"配方变更候选"，且 cause 不得写入 `hypotheses[]`（C7 §4.3-2）。
- **排除项**：温度台阶（转 R-43）；换型同时换工装/标定板（混杂不可分 → `not_evaluable`）；样本量不足；`|Δt| <= event_context.sync.uncertainty_ms`（对齐不可信，C6 硬规则 2；`uncertainty_ms` 缺失按 5 ms 保守取值并记 `audit.assumptions`）。
- **建议动作**：`rerun_step`（按标准流程重新下发标定系数）；`field_procedure` 要求人工核对换型前后 `meta.counts_per_mm` 与配方表一致。本模块**不实现**配方回滚（C7 §1.3）。
- **期望效果依据**：`rule_heuristic`。
- **出处 tier**：`T2` + `T3`（"脉冲当量被换型流程覆盖"的缺陷形态可借用，其检出率声明不采信，必须在本项目合成集上独立复现）。
- **适用边界**：`event_context.step_labels[]` 缺失 → `skipped` 并写 `not_evaluable`；因果开关为 false 时**只报共现**（C7 §4.3-2）。

### R-48 残差与标定板/工装/温度相关：相关性 ≠ 因果的呈现纪律
- **family**: `mechanical_thermal_drift`
- **断言**：观察到残差与某协变量相关时，**除非** `causal_claims_permitted == true` 且有领先—滞后结构，否则只允许呈现"相关"，不允许呈现"因为"。
- **判据**：R-48a `calibration.correlation_screen.with_temp_r ∈ [0.5, 0.9]`（**相关系数必须与 CI 同时出现**：`with_temp_ci`，C7 §4.2），或 `calibration.correlation_screen.with_fixture_batch` / `with_plate_grade` / `with_operator` 的分组差异显著（Welch t `welch_p <= 0.05` ∧ 效应量 `effect_over_rms >= 1`）；R-48b 滞后互相关：温度变化领先残差变化 `>= 2 × event_context.sync.uncertainty_ms`；R-48c `event_context.causal_claims_permitted == true`。**R-48b/c 任一不成立 → 本条唯一合法输出是"相关性已量化，因果未确立"。**
- **必要上下文**：温度序列与标定时间戳**同源**（异源时 `calibration.correlation_screen.with_temp_r` 只作共现，假设写进 `audit.assumptions`，C7 §4.3-4）；`event_context.sync.verified == true`；工装/标定板批次与操作者标签（`calibration.sessions[].{fixture_id, plate_grade, operator}`）。**标定记录若无 `event_context`，因果开关默认取 `false`**（**M-3 已裁**：C7 §4.3-2——`calibration.jsonl` 不定义自己的 `sync`，因果开关唯一来源是 C2 `event_context.causal_claims_permitted`）。
- **排除项（混杂变量清单，逐项列出）**：换型时同时换工装；换型时同时换操作者；室温与生产负荷同向变化（**共因**）；单次标定内温度基本不变；小样本使 `r` 的 CI 覆盖 0。**工装批次效应**不是任何 `mechanical_*` / `electrical_*` / `software_induced_*` slug 可表达的原因（**G-1 请求的 `calibration_fixture_repeatability` 未被采纳，裁决 A-16**）⇒ 此时 **cause 留空**、只写相关、`overall_confidence <= 0.5`，并逐条登记 `differential.not_evaluable`"工装/标定板批次效应：无可用 cause slug（KB6 G-1 未采纳）"；**本组不新增任何因果布尔**（开关只复用 `event_context.causal_claims_permitted`，C7 §4.2）。
- **建议动作**：`request_data`（补采温度/批次/操作者记录）+ 报告固定措辞"相关性已量化，因果未确立"。
- **期望效果依据**：`unverified`（无数字）。
- **出处 tier**：方法论依据 `C2 规则 8` + `C6 §3` + `C5 §1`；内容依据 `T2`。
- **适用边界**：若模型试图把本条写成因果结论，即违反 C3 硬规则 1（不得造因果）。本条镜像 C2 规则 8 的因果开关——这是本模块**刻意保留的一道刹车**。

### R-49 残差超过外部验收限 → 拒收判定（门禁）
- **family**: `null`（**门禁/拒答规则类**，裁决 A-17；见 **G-2**。产出**登记义务**：触发写 `audit.rules_fired` + `differential.not_evaluable`，**永不产生 `hypotheses[]`**，计入 C5 拒答正确率）
- **断言**：残差超过**规范限值**时，正确动作是"拒收/复标"而不是给根因——根因分析在这里既不必要也无证据。
- **判据**：R-49a `calibration.sessions[].rms_residual_counts >= calibration.spec.rms_counts`；R-49b 或 `max(abs(dx_i), abs(dy_i)) >= calibration.spec.max_counts`（**逐点极值**，取自 `calibration.sessions[].residual_vectors_counts[]`，不用平均规避）；R-49c `calibration.sessions[].oos_point_ratio > 0` ∧ `calibration.sessions[].n_points >= 9`（`oos_point_ratio` 只是良率损失的**上界型代理**，禁止换算成良率，C7 §4.4-4）。超标即触发，不要求统计显著性（合规判定不是假设检验）。
- **必要上下文**：**必须有外部规范限值** —— `calibration.spec.{rms_counts, max_counts, source, version}` 由设备验收标准给定，载体是 `calibration.jsonl` 每行回显的批次级外部输入，**全文件取值必须一致**，不一致 ⇒ 本条 `skipped` 并登记"验收限版本冲突"（**M-3 已裁**：C7 §4.1-3）；`calibration.spec == null` 时本条 `skipped`（无规范就没有"超标"，只有"较大"；**禁止**用 `3σ`、p95、历史最好值冒充客户限，C7 §4.4-1）。`calibration.spec.*` 是**门禁字段，禁入 `supporting_evidence[]`**（§0.3-2 / C7 §7.1）。
- **排除项**：规范来自旧配方/旧视野 → 先核 `calibration.spec.version`；超标但形态完全随机、重复性好 → 优先怀疑标定板/工装（R-48；**工装批次无 slug，G-1 未采纳** ⇒ 只写 `considered` / `not_evaluable`）而非运动链。
- **建议动作**：`rerun_step`（复标/复检）；**`actionable: false`、`overall_confidence <= 0.45`**（对齐 C7 §8-2 的门禁类形状；复标只以 `recommendation.field_procedure` 的人执行文本存在），**不得**下发任何基于本残差的补偿参数（§0.1），**不得**写 `hypotheses[]`。
- **期望效果依据**：`unverified`。
- **出处 tier**：**方法与限值分开记 tier**（A-85，收口原"具体条目待主线程核对"）：
  - **方法**部分是 `T2`，出处为 `ISO 230-2:2014+A1:2016, Test code for machine tools — Part 2:
    Determination of accuracy and repeatability of positioning of numerically controlled axes`
    （中国采用版 `GB/T 17421.2-2023《机床检验通则 第 2 部分：数控轴线的定位精度和重复定位精度的确定》`）；
    热效应对应 `ISO 230-3`（与 KB3 §1.1 `thermal_drift` 行同源）。三者**只按标准号引用**，
    这些标准是付费文本、没有开放 DOI，写 DOI 或写"论文标题"就是编造（KB0 §4 出处纪律）。
  - **限值**部分（`calibration.spec.{rms_counts, max_counts}`）**没有 tier**：它是设备验收时客户与
    设备方约定的**外部输入**，不是文献结论。报告里把超标写成"违反 ISO 230-2"是**错的**——
    ISO 230-2 规定**怎么测**、给的是 `A`/`B`/`C` 各项的计算方法，**不替你定验收门限**。
    正确措辞："按 `ISO 230-2` 方法评定的定位残差为 `X`，超出 `calibration.spec`（来源：`spec.source`，
    版本 `spec.version`）给定的验收限 `Y`"。
- **适用边界**：`meta.counts_per_mm == null` 时 `calibration.spec` 必须**已折算成 counts**；若只有 µm 规范而无定标系数 → 本条**结构性不可评估**，报告须写"缺定标系数，验收限无法应用"（C7 §4.4-2 / C1 红线，不许偷偷换算）。**"结构性不可评估"与"门禁触发"必须分开呈现**（C7 §8-3：前者是覆盖度问题、可补数据；后者是结论边界问题、正确拒答）。

### R-50 SPC 控制图必须在换型/重标定处分段，否则换型本身被误判失控（门禁）
- **family**: `null`（**门禁/拒答规则类**，裁决 A-17；约束的是**统计方法**，不是设备。产出**登记义务**，永不产生 `hypotheses[]`，计入 C5 拒答正确率；见 **G-2**）
- **断言**：控制限由历史同分布样本算出；跨越换型/重标定点的控制图会把"过程均值的合法移动"误判成失控 ⇒ 那次报警是对统计方法的误用，不是对设备的诊断。
- **判据**：R-50a 任一子组跨越 `event_context.step_labels[].recipe` 变更点或 `calibration.sessions[].timestamp_s` 重标定点 → 该图**作废**，须在断点分段后重算控制限（**控制限按段独立重算，禁用换型前的限卡换型后的点**，C7 §4.2）；R-50b `calibration.series.violations_before_resegmentation > 0` ∧ `violations_after_resegmentation == 0` ⇒ 结论 = "分段错误造成的假失控"（这才是唯一正确输出）；R-50c `calibration.series.violations_after_resegmentation > 0` ⇒ 才是真实失控信号，允许进入归因规则（R-43/R-44/R-45/R-47）；R-50d 子组内方差远大于子组间（`calibration.series.rms_cv_pct` 大但组间均值稳定）⇒ 提示 I-MR 被误用，应改用 Xbar-R（§B.4，图型选择规则已契约化于 C7 §4.2）。
- **必要上下文**：`calibration.series.n_sessions >= 8`（`< 8` ⇒ B 组统计判据上限 0.5，§C.3 第 10 行）；控制限计算窗口与分段标签（`calibration.series.{control_limits[], segment_break_points[]}`，断点必打印 `{t, reason, evidence}` 与每段 n）；图型与子组大小已声明（`calibration.series.chart_type`、`subgroup_size`）；失控规则只取 Western Electric 前 3 条（`calibration.series.violation_rules_fired[]` ∈ {1,2,3}，第 4 条以后在 `n_sessions < 30` 假阳率过高，**明确不用**）。
- **排除项**：过程本身连续单调漂移（R-43）而非台阶 → 属漂移，不是分段问题；分段后每段 `n < 8` → 控制限不稳，本条降级为"不可评估"，**不得**说"过程受控"。
- **建议动作**：`change_measurement_procedure`（重新分段后重评）；`field_procedure` 文本给出分段规则与最小样本数。
- **期望效果依据**：`rule_heuristic`（依据是统计方法本身，不是设备模型）。
- **出处 tier**：`T2`（SPC 阶段化/分段是标准实践，具体条目待核对）+ `T3`（合成含合法均值移动的序列，检验本条能否**避免假报警**——这是可判定的阴性对照）。
- **适用边界**：本条**不作为设备根因**出现；它出现在 `audit.rules_fired` 与报告的"分析纪律"段，并在 `differential.not_evaluable` 履行登记义务（裁决 A-17）。**同一纪律对节拍统计同构生效**：节拍序列存在可证的 recipe 变更/重标定点而 `cycle_stats.segment_break_points[]`（或 `calibration.series.segment_break_points[]`）为空 ⇒ **未分段本身是必须登记的诊断缺陷，不是通过**（C7 §6 硬性约定 1；禁止输出"节拍受控""无慢拍异常"）。

## B.3 统计口径（可辩护的工程统计）

**目标**：让"某一段时间变差"在数字上活下来，不被全程平均稀释。

| 量 | 定义 | 用于 | 为什么必须存在 |
|---|---|---|---|
| 分组均值 | 按 recipe/操作者/时间半段分组 + Welch t 或 bootstrap CI；**段 = 批次（裁决 A-39）**："按 recipe 切"与"按时间半段切"是 `calibration.sessions[]` 批次的两种**归组方式**，跨段统计写 `calibration.series` | R-44/R-47 | 总体均值是不同总体的混合，混合均值无物理意义 |
| 变异系数 `CV = σ/μ` | 无量纲（`calibration.series.rms_cv_pct`；节拍侧 `cycle_stats.cv_pct`） | R-45/R-47 | 跨配方、跨视野、跨量级时只有比值可比 |
| 均值向量 `mag/dir_deg` | `calibration.sessions[].mean_residual_counts{mx,my,mag,dir_deg}` = `‖mean(dx,dy)‖` 与主方向 | R-46 | 矢量信息；标量 RMS 看不到"有系统性偏移" |
| `systematic_share_pct` | `‖mean‖ / rms × 100`（`calibration.sessions[].systematic_share_pct`） | R-45/R-46 | 把"**偏**"与"**散**"分开的唯一简单可辩护指标 |
| `isotropic_ratio` | `σ_major / σ_minor`（`calibration.sessions[].isotropic_ratio`） | R-46 | 判断散布是否有方向 |
| p95 / max | 逐点分位与极值 | R-49（验收） | 装配看的是最差点，不是平均点 |
| 尾部敏感指标 | `p99`、`calibration.series.oos_ratio` / `calibration.sessions[].oos_point_ratio`、`slow_tail_ratio` = 最差 10% 子组均值 ÷ 全体均值（`calibration.series.slow_tail_ratio`；节拍侧同名指标 `cycle_stats.slow_tail_ratio`） | R-47/R-49 | **稀释免疫**：一小段劣化直接抬高占比与右尾 |

**为什么 P95 / 中位数单独不够**（三点，各自可检验）：

1. **分位数是序统计量**：只保留顺序、丢掉配对方向信息，因此丢掉标定诊断最关心的东西。同样 `|r| = 10 counts`，重复测出 +10（系统偏差，要重标）与 ±10 随机（重复性问题，要查工装）的 `p95` 与中位数**完全相同** —— 分位数区分不了两类完全不同的处置动作。
2. **小 n 上分位数不稳**：标定 `n = 9~49`；n=9 时 p95 由最高一两个点插值而来、CI 宽到支撑不了任何判定，中位数在该样本量下等价于"任意第 5 点"。小样本的正确工具是 CI + 非参数检验（Mann-Whitney / Welch），不是分位数阈值。
3. **尾部指标也会稀释"局部时段变差"**：某配方 10000 循环里只有 3% 变差时，`p95` 勉强落在被影响点上、中位数完全不动，而**全程平均**把 3% 的劣化摊成 0.3% 的均值差 ⇒ 看不出。故必须同时报 `calibration.series.oos_ratio`（及 `calibration.sessions[].oos_point_ratio`）与 `slow_tail_ratio`。

**借用 `cycle_jitter` 的设计模式，但独立论证**（C2 **无**该字段且裁决 **A-25/M-6 已裁：不新增**；节拍统计一律归 **C7 `cycle_stats`**，见 §G-3 表末两行与 C7 §6）：借的不是字段，而是三条设计选择——**按工况分组 + 比值形式 + 对右尾敏感**。节拍诊断的核心不是平均节拍，而是"分布右尾 + 离散度"，因为节拍变慢只在少数循环发生、平均把它摊平，所以 `cycle_stats.slow_tail_ratio` 必须按 `cycle_stats.grouping_keys[]`（至少含 `step` + `recipe`）分组计算；快循环占比看 `cycle_stats.slow_cycle_share_pct`。但**统计纪律不能照搬**：`cycle_stats.cycle_time_median_ms` / `cycle_time_p95_ms` 是**快过程变量**（一循环一个点，n 上万），分位数有意义；`calibration.sessions[].rms_residual_counts` 是**慢过程变量**（一次标定一个点，每配方每天一两个），分位数无意义。这条区分写在正文里是为了防一个常见错误："拿 SPC 的分位数阈值去卡一天只有两次的标定残差"——**不成立**（C7 §6 硬性约定 2），慢变量必须用分组均值 + CI + 分段控制图。节拍类建议的动作只允许 `change_measurement_procedure` / `schedule_verification` / `request_data`，且**禁止**"节拍缩短 X%"的数字（C7 §6-3）；`cycle_stats.available == false` 时**禁止**输出"节拍正常"（C7 §1.2-5）。

## B.4 SPC / 良率视角的最小可用形式

**图型选择规则**（可判定，是 R-50d 的依据；结论已契约化为 `calibration.series.{chart_type, subgroup_size, control_limits[]}`，`σ_within = MR̄/d2`，C7 §4.2）：

```
IF 一次标定含 calibration.sessions[].n_points >= 9 且网格间距 >> 残差
   THEN 网格点视为同一标定内的"子组" → Xbar-R（子组内极差 = 工装/视觉重复性噪声）
ELSE 每次标定只给一个标量残差 → I-MR（MR = 相邻两次标定 rms 的 |Δ|）
```

Xbar-R 更灵敏，因为它把"子组内散布"与"子组间漂移"分开；I-MR 的 `σ_within` 由 `MR̄/d2` 估计（子组大小 2），所以**若标定顺序被打乱、相邻两次来自不同配方，`MR̄` 就被污染** —— 这是 R-50 必须分段的**统计理由**，不是流程洁癖。

**失控规则（Western Electric，本模块只取前 3 条，落在 `calibration.series.violation_rules_fired[]` ∈ {`"1"`,`"2"`,`"3"`}，C7 §4.2）**：(1) 任一点超出 `mean ± 3σ`；(2) 连续 9 点同侧（缓慢漂移 → 与 R-43 联动）；(3) 连续 6 点单调（趋势 → 与 R-43 联动）。第 4 条以后（2/3 点超 2σ 等）在 `calibration.series.n_sessions < 30` 时假阳率过高，**明确不用**。

**硬纪律：控制限必须由同段数据算出。** `禁止`用换型前数据算的限去卡换型后的点然后报警"过程失控"；`必须`在 recipe / 重标定边界断图、每段独立重算 mean 与 σ、并在报告打印 `calibration.series.segment_break_points[]`（`{t, reason ∈ {recipe_change, recalibration, fixture_change, operator_change}, evidence}`）与每段 n。

**与良率的最小联系**：标定残差的 `calibration.series.oos_ratio`（超差占比）只是良率损失的**上界型代理**（残差超差 → 贴装偏差可能超规 → 该件可能失效）。**不得**声称与良率有定量关系（C7 §4.4-4）：残差是"能力"不是"实际贴装误差"，缺工艺窗口与不良真值 ⇒ 没有可辩护的换算系数（C5 §1 的"不能证明"栏）。

---

# C. 与主诊断内核（KB3/C3）的接口

## C.1 证据路径纪律

1. `hypotheses[].supporting_evidence[].feature` **必须**是 (a) **C2** 已登记的伺服侧路径，或 (b) **C7** 已登记的工艺/标定/程序/节拍侧路径（`power_channel.*` / `light_curve.*` / `calibration.*` / `scan_program.*` / `cycle_stats.*`；对照表见文末 **G-3**，字段口径权威在 C7 §2.2/§4.2/§7.1）。**没有第三种**：规则引擎不自行 FFT/拟合/降采样；未登记于 C2 **或** C7 的路径不允许出现在证据里（KB0 §3，裁决 A-34/A-36/A-40）。C7 与 C2 算**不同特征组**，但 C7 内部 `power_channel.*` 与 `light_curve.*` **不算两个独立特征组**（C7 §2.3 / §7.1）。
2. **原"KB6-NEW 路径并入 C2 之前引用即 `blocked`"机制作废（裁决 A-36）**：KB6 的 A/B 两组特征已由 **C7** 承载，`blocked` 不再由"未并入 C2"触发。现存的两种 `blocked`/`not_evaluable` 来源是：① 引用**未登记于 C2 或 C7** 的路径 ⇒ 加载期拒绝，理由文本 `"feature path not registered in C2 or C7 (C7-NEW)"`，逐条写 `audit.rules_skipped` 并把对应 fault_mode 写进 `differential.not_evaluable`；② **C7 §1.2 缺档纪律** ⇒ 按 §1 的分组（A 组 R-31…R-42 / B 组 R-43…R-50）逐条登记。规则文本**可以先冻结在文档里**（便于评审判据逻辑），但缺档/未登记时其结论不得进入 `hypotheses[]`。
3. 每条假设仍受 C3 硬规则 1 约束：**≥2 条 supporting_evidence** 且**两条来自不同特征组**（如 `light_curve.*` + `global.*`，或 `calibration.*` + `event_context.*`）；同组两条证据只是同一现象的两面，不构成独立支持。
4. `rule_id` 沿用 C3 示例风格（`R-03a`）：KB6 写 `R-31a`…`R-50d`；`source` 指向本文件锚点（`docs/kb/KB6-coupling-and-calibration.md#R-31`）。**`R-51+` 仍保留给 KB6/后续工艺规则，C7 不占用任何 `R-NN`**（C7 §8-1）；C7 条款以 `C7-§<节>-<序>` 形式引用。
5. `rules_skipped` / `not_evaluable` 义务：触发 C1 拒诊断条件、依赖特征为 `null`（C2 规则 2）、超出 `freq_limits.reliable_band_hz`（C2 规则 7）**或** `power_channel.reliable_band_hz`（C7 §3.4-1）、`segment_coverage` 不满足、撞 C7 §3.3 空间分辨率拒收红线（须同时写顶层 `blocked_claims[]`）、**C7 §1.2 缺档**（`process.json` / `calibration.jsonl` 缺失、`power_channel.present == false`、`cycle_stats.available == false`、`scan_program` 缺失）、或引用未登记于 C2/C7 的路径 —— **必须逐条列出并写明缺什么**。沉默 = 让报告显得比实际更有把握（C3 硬规则 9，最危险的失效模式）；**绝不允许**"未发现工艺异常""耦合曲线形态正常""无采样伪影""节拍正常"这类把"没有读数"说成"没有异常"的输出。
6. `overall_confidence` = 各假设 `confidence` 最大值（C3 语义）；C.3 的截断是**归一化之后的上界裁剪**，不重新分配权重，也不得被 LLM 改写（C3 硬规则 3）。

## C.2 `segment_coverage` 的角色（scanning / probing / dwell / curing）

| 段 | 参与方式 | 缺失后果 |
|---|---|---|
| `scanning` | A 组所有 `light_curve.*` 判据的作用窗；峰形/不对称/噪声底/截断只在扫描窗内有意义 | R-31/35/37/38/40/41/42 → `skipped` |
| `probing` | 恒速线性扫，与 KB3 纹波/速度类判据同一段；用于区分"匀速扫"与"逐点驻留" | R-32/39/40 → `skipped` |
| `dwell` | 逐点测量点所在；M-a…M-e 全部在 dwell 窗内判定 | R-31/34/36/42 → 不可评估 |
| `curing` | R-33 的时间锚：漂移应发生在固化窗内及其后；决定"收缩补偿窗口"是否可谈 | R-33d 不可评估，整条降级 `not_evaluable` |
| `settling` | 为陷阱 2 提供 `τ_axis = step_response[].settling_time_ms` | `light_curve.motion_sampling_conflict.required_settle_ms` 推不出（该侧任缺即 `null`，C7 §2.2 A4）→ R-31/R-42 退化为 T2 经验值并按 C.3 第 7 行截断 |
| `path` | 寻光轨迹一般**不**标 `path`；若上游误标 → 分段质量存疑 | **不得**强行套 A 组判据，报告先质疑分段 |

**双向原则**：分段是判据的前提，判据也校验分段质量。`segment_coverage` 全为 0（无任何运动语境）时
**KB6 整体不可评估**，但 KB3 的 `global`/`spectral` 静态类判据仍可能有效；反之 `scanning` 存在而
`dwell` 缺失，说明采样点被误标为扫描 → **"分段质量本身"成为发现**，而不是静默把判据降级。

## C.3 置信度截断（工艺缺真值时如何封顶）

KB4 加权公式（未写）产出原始分 `c_raw`，KB6 的上界裁剪在其后按**取最小值**顺序生效，结果写回
`confidence` 与 `overall_confidence`；裁剪只降不升，每条触发都要在 `audit.assumptions` 打印原因。

| 序 | 条件 | 上限/处置 | 依据 |
|---|---|---|---|
| 1 | 判据证据仅来自 T3（无 T1/T2） | **不得进入 `hypotheses[]`** | C5 §1 + KB0 §4 |
| 2 | 引用**未登记于 C2 或 C7** 的路径（原"引用 KB6-NEW 未并入 C2 的特征 ⇒ `blocked`"机制作废，裁决 A-36；KB6 特征已全部落在 C7） | `blocked`，不打分；理由文本 `"feature path not registered in C2 or C7 (C7-NEW)"` | C.1-2、C7 §7.1、KB0 §3 |
| 3 | `event_context.available == false` | `software_induced_*` 不打分，强制 `not_evaluable` | C2 规则 8 |
| 4 | `sync.verified == false` 或 `sync.method == "unknown"` | `software_induced_*` 上限 **0.40**，只能共现叙述 | C6 §3 硬规则 1 |
| 5 | 证据对齐残差 `\|Δt\| <= uncertainty_ms`（缺省 5 ms） | 该证据作废；无其他支持则假设移出 `hypotheses[]` | C6 §3 硬规则 2 |
| 6 | `meta.counts_per_mm == null` | µm 类阈值不启用；结论禁 µm；上限 **0.55** | C1 / KB0 §5 |
| 7 | `power_channel.integration_time_ms` 为 null，或 `power_channel.ratio_to_servo_fs` 落在 C7 §3.2 的 `100–1000` / `>1000` 档（采样粗、积分窗涂抹不可排除；**本文旧版此处写 `ratio_to_servo_fs < 20`，方向反了，已按裁决 A-35 改为引用 C7 §3.2 档位表**），或 `step_response[].settling_time_ms` 为 null | 采样器伪影不可排除 → R-31/R-34/R-42 上限 **0.45** | C1"驱动器字段缺失必须降级，不得用默认值冒充实测" + C7 §3.2 |
| 8 | `light_curve.series_stats.ref_scan_ids` 为空 | 所有趋势/跨扫描判据上限 **0.5**（`null` **不等于**"无漂移"） | 无基线 + C7 §2.2 A3 |
| 9 | R-37 / R-49 / R-50 门禁触发 | 上限 **0.45**；action 只允许 `rerun_step`/`request_data`/`schedule_verification` | 缺外部真值 |
| 10 | `calibration.series.n_sessions < 8` 或 `calibration.sessions[].n_points < 9` | B 组统计判据上限 **0.5** | §B.3 小样本 |
| 11 | 该规则在 `freq_limits.blocked_rules` | 不打分（**不得**说"未发现"） | C2 规则 7 |
| 12 | 任一依赖特征为 `null` | 该判据放弃，不得插值 | C2 规则 2 |
| 13 | **C7 §1.2 缺档**：`process.json` 缺失（A 组 R-31…R-42 全量）、`calibration.jsonl` 缺失（B 组 R-43…R-50 全量）、`power_channel.present == false`、`cycle_stats.available == false`、`scan_program` 或其 `source` 缺失 | 相关规则一律 `blocked` / `not_evaluable`，**不打分、不输出**；逐条写 `audit.rules_skipped` + `differential.not_evaluable`。**禁止**任何形式的"工艺异常未见面""耦合曲线形态正常""节拍正常"表述 | C7 §1.2 第 1–6 条、C3 硬规则 9 |
| 14 | `scan_program.source == "inferred_from_waveform"`（步长由波形反推） | 所有**依赖步长**的判据（R-31b、R-38c、R-42c/d、`light_curve.motion_sampling_conflict.step_over_fwhm_ratio`）上限 **0.40**；`scan_program.source == "operator_entered"` 上限 **0.55**；`cycle_stats.cycle_source == "segment_edges"` 上限 **0.5**。取最小值不连乘，原因写 `audit.assumptions`（用波形反推的步长去验证波形是循环论证，A-28） | C7 §5 硬规则 1/2/4/5、A-28/A-41 |

**冲突处理**：多条同时触发 → 取最小上限（不连乘，避免压成无意义的极小数）。**禁止**把截断实现成
"LLM 觉得证据不足就降 0.1"——截断是确定性表，LLM 只能改 `display_name` 与 `rationale` 措辞。

## C.4 与 KB3 既有规则的复用与去重

| KB6 位置 | 借用哪一族 | 去重纪律 |
|---|---|---|
| R-32/R-45/R-46 用 `global.backlash_estimate_counts`、`reversal_error_counts` | KB3 间隙/反向族 | KB6 只当**辅助排除项**（`contradicting_evidence`），不当主证据；否则同一现象计两次票、置信度虚高 |
| R-36 用 `resonance.candidates[].present_in_dwell` | KB3 驻留共振族 | 共振族主导；R-36 只提供"功率通道也受影响"的跨域证据 |
| R-39 用 `crawling.*` | KB3 摩擦/爬行族 | 同一 cause 只允许一个主归属规则，另一侧记为出处 |
| R-40 用 `encoder.*` | KB3 编码器周期误差族 | KB6 的新意仅在"伪装成功率曲线起伏"这一跨域效应 |
| R-31 与 R-42 共享 `light_curve.motion_sampling_conflict.*` | KB6 内部 | 两条同时触发时只计一条主证据，另一条转注记 |
| R-45 与 R-47 同属 `software_induced_pulse_eq_overwritten` | KB6 内部 | 事件对齐（R-47）优先；形态证据（R-45）不重复计权 |
| R-43/R-44/R-48 用 `global.thermal_*`；全部 `event_context.*` | KB3 温漂族 / C6 软件族 | 复用不重定义；KB6 **不得**为软件族另造特征 |

`audit.rules_fired` 需同时列出 KB3 与 KB6 规则号，跨域证据标 `cross_domain: true`，以便 C5 消融实验
单独统计"工艺外壳的边际贡献"。

## C.5 与 C4 验证门控的接口

- C4 的被控对象（KB5）是伺服/机械模型，**不含光学耦合效率曲面**，因此 A 组涉及峰形/功率的建议，
  `expected_effect.basis` 只能是 `rule_heuristic` 或 `unverified`。
- 唯一允许 `simulation_validated` 的情形是**伺服参数类建议**（陷波、前馈、整定，KB3 已定义动作）；
  此时 `validation[].plant_fit` 只拟合伺服侧，且必须在 `caveats` 写"仿真不含光学耦合效率模型，
  峰功率改进量未经验证"；`fit_residual_pct > 25%` 仍按 C4 降级，±20% 敏感性与"新峰否决"照常生效。
- 标定侧建议（重标、复紧、重新分段）全部 `unverified` 或 `rule_heuristic`；**禁止**给出"重标后残差
  下降 X%"的数字（无可复现真值来源）。
- "验证不得替被验证对象说话"在 KB6 的落地：合成集上的检出率**不能**被引用为产线有效性证据；若未来
  引入 T3 功率曲面（§A.4.2），可声称的是"**判据按构造检出植入误差、且在对抗案例上正确拒答**"，
  而不是"诊断准确"。二者不可混用（C5 §1 硬规则）。

## C.6 输出形状示例（KB6 侧一条假设）

```
hypotheses[0]:
  cause: "mechanical_encoder_periodic_error"          # KB0 §2 现有 slug；G-1 的 8 个候选**未采纳**（A-16），不新增
  display_name: "编码器每转周期误差伪装成光斑形状劣化"
  supporting_evidence:
    - {feature: "light_curve.encoder_masquerade.residual_period_ratio_to_per_rev", value: 1.0,
       operator: "==", threshold: 1, rule_id: "R-40a", window: {segment_id: 7, kind: "probing"}}  # 已登记于 C7（§7.1 #1，KB6 A7）
    - {feature: "encoder.per_rev_amplitude_counts", value: 180.0, operator: ">=", threshold: 120.0, rule_id: "R-40d"}  # C2 现有
  contradicting_evidence:
    - {feature: "bandwidth.position_loop_crossover_hz", value: 42.0, rule_id: "R-40e", note: "周期远离环带宽，排除伺服自激"}
  ruled_out_alternatives:
    - {cause: "丝杠螺距周期误差", why: "周期恰为每转而非每导程", rule_id: "R-40a"}
    - {cause: "共振（极限环）", why: "present_in_rest == false 且频率不随负载变", rule_id: "R-36"}
  differential:
    considered: ["双折射/双模功率起伏（光学，自然语言候选，无 slug 可落）", "胶线遮挡造成的工件边缘效应"]
    not_evaluable: [
      {"fault_mode": "mechanical_encoder_periodic_error",
       "why": "R-31 分支不可评估：power_channel.integration_time_ms 为 null（C7 §1.2 第 6 条，依赖字段缺失 ≠ 无伪影）"},
      "偏振/双模峰劈裂：无可用 cause slug（KB6 §G-1 未采纳，A-16 / C7 §7.2 第 3 条的字符串登记形）",
      "直线性/俯仰偏摆：无可用 cause slug（KB6 §G-1 未采纳）"
    ]   # 键形口径（A-51 + C7 §7.2-3）：**有** slug 的条目用 {fault_mode|family, why}；**缺** slug 而无归因出口的差额用纯文本，禁止为它造 slug 名
  next_data_to_collect:
    - {ask: "同一扫描重复两次并从反方向趋近", why: "真峰应复现；回程伪像随方向移动", unlocks: ["R-32","R-40"]}
    - {ask: "独立于被测编码器的第二位置传感器", why: "区分测量误差与真实运动误差", unlocks: ["R-40 交叉验证"]}
  confidence: 0.48            # KB4 原始分；C.3 上界裁剪取 min（第 6 行 0.55、第 8 行 0.50）⟹ 0.50，未被裁剪
  recommendation: {class: "schedule_verification", writes_to_device: false, basis: "unverified",
                   field_procedure: ["停机态复测螺距/编码器误差曲线…"]}
audit:
  rules_fired: ["R-40a","R-40c","R-40d","R-40e"]
  rules_skipped: [{"rule_id":"R-31","reason":"power_channel.integration_time_ms == null → C7 §1.2 第 6 条，判据放弃并追加 unavailable（不得写成'无采样伪影'）"},
                  {"rule_id":"R-41","reason":"segment_coverage.scanning == 0"},
                  {"rule_id":"R-40f","reason":"feature path not registered in C2 or C7 (C7-NEW)：light_curve.encoder_masquerade.residual_phase_deg"}]
  assumptions: [{anchor: "event_context.sync.uncertainty_ms",
                 statement: "未给出可核时时钟不确定度 → 按 5 ms 计（KB3 纪律 6）"},
                {anchor: "meta.counts_per_mm",
                 statement: "刻度未标定 → 全部结论以 counts 呈现，禁 µm（A-97 ②）"},
                {anchor: "R-40",
                 statement: "encoder_masquerade.* 走 C7（process.json），非 C2；R-40 与 C2 encoder.* 构成两个不同特征组（C7 §2.3）"}]
```

**这一份形状的四个要点**：① A7 路径**已登记于 C7**，因此不再有"KB6-NEW ⇒ `blocked`"这一说（A-36）；
② `rules_skipped` 的理由只能是 **C7 §1.2 缺档 / 依赖字段 null / `segment_coverage` 不足 / 引用未登记路径**
四类，不得写"未发现问题"；③ 缺 slug 的现象一律落 `differential.not_evaluable`，**不吸收**（A-16）；
④ 键形按 **A-51**：族级 `{family, why}`、逐模式 `{fault_mode, why}`，仅"无 slug 可用"的差额允许纯文本
（C7 §7.2 第 3 条），**不得**为差额发明 slug 名。

---

# D. 裁决回写状态与残余待办（原"待主线程裁决"清单）

> 本节原为**请求**（跨文件一致性检查与契约修改由主线程负责，KB0 §6）。主线程已逐条裁决，裁决记录在
> **KB0 §7/§7.1/§7.2/§7.3（A-1…A-91）**；本节按裁决结果改写为"**已裁状态 + 原文留痕**"，正文规则已据此对齐。
> 契约侧唯一新增事实是 **C7 已建立**（`docs/contracts/C7-process-context.md`）。
> 第六轮落到本文件的两条：**A-85**（R-49/R-50 的出处按"方法 = `T2` 按标准号引用、限值 = 外部输入无 tier"分开记）、
> **A-86**（本文件 `R-31…R-50` 与 KB8 案例集**零交集**这一事实被登记，KB8 §6 先补门禁三例配额）、
> **A-87**（真值来源三分：R-45 的"1000 倍口径差"属逻辑自洽可判据，"这台设备当前用哪套口径/当量是多少"属约定真值，
> 只能进待确认清单且恒 `rule_heuristic`；见 **§B.2 R-45** 建议动作处的落点分界）。
> **A-89**（A-87 的第 ③ 类再分档）对本文件的口径不改动规则内容，只改**登记方式**：本文件里凡"需厂商确认"的格
> （`counts_per_mm` 当量口径、编码器并联与倍率、SDO/字典参数地址、标定常数来源）须在 C6 §5 前缀里标出属于
> **③a 手册可查** 还是 **③b 批次与现场**。`T2`（按标准号引用）不受影响——标准原文是可存的官方工件，但
> **核对主体仍不可转借**（A-89：第三方会话读过标准不等于我们把标准存进了 `docs/evidence/`）。

## G-1 需要新增的 KB0 §2 slug —— **已裁：不采纳（A-16；C7 §7.2 第 2 条）**

**裁决原文口径**：C7 不新增任何 cause slug，KB0 §2 的三族（`mechanical_*` / `electrical_*` /
`software_induced_*`）是唯一合法集合；下表 8 个候选**全部不予采纳**。
**理由（不是"覆盖面小一点"）**：本项目**无耦合产线数据、无光学真值、无工装批次的独立标签来源**；
采纳这些族名等于允许 agent 用**没有证据支撑的家族名**下结论——slug 一旦存在就会被填，填了就在报告里
长得像真归因，而它的证据 tier 只有 T2 方向性 + T3 合成。这正是本项目最不能犯的那类错（C5 §0、AUDIT §二）。

**原请求留痕**（下表**仅作出处追溯**，任何规则不得把这些名字写进 `cause`）：

| 候选 slug（**不采纳**） | 覆盖现象 | 原申报的"为何必须新增"（现由 `differential` 承接） |
|---|---|---|
| `optical_mode_mismatch` | 模场失配 / 离焦 / 像散 / 倾斜入射 | KB0 §2 无光学族；R-31/R-35 的**真光学解释**只能写进 `differential.considered` 的自然语言候选。强行借用 `mechanical_thermal_drift` = **归因造假**（C7 §7.2 第 4 条） |
| `optical_device_degradation` | 器件功率衰减（激光器/PD/胶老化） | R-37 门禁的归因出口缺失 → 现由 R-37 直接**拒答**（`family: null`）+ `not_evaluable` 表达 |
| `optical_polarization_mode_split` | 偏振/双模导致的双峰劈裂 | R-32 排除项 → 落 `considered`（"偏振/双模劈裂候选"） |
| `mechanical_axis_straightness_error` | 轴直线性误差（横向串扰） | R-35 主归因出口 → 落 `considered`（"像散/倾斜入射候选"）+ `not_evaluable`（"直线性：无可用 cause slug（G-1 未采纳）"） |
| `mechanical_pitch_yaw_wobble` | 俯仰/偏摆姿态误差随行程变化 | R-35/R-40 的角度侧解释 → 同上 |
| `process_workpiece_occlusion` | 工件边缘/胶线/气泡遮挡 | R-38 排除项 → 落 `considered`（"工件遮挡候选"） |
| `calibration_fixture_repeatability` | 工装/标定板批次与重复性 | R-46/R-48 主归因出口 → 缺它只能写"方向性未确立"；**禁止**顶包为 `mechanical_loose_structure` |
| `calibration_model_unmodeled_distortion` | 高阶畸变未建模（镜头/安装） | R-43/R-44 排除项出口 → 落 `considered` |

**差额的处置（已生效，写进正文）**：
1. KB6 的合法结论集合**明显小于**现象集合，差额**必须明示、不得吸收**（A-16 / C7 §7.2 第 3 条）：
   能用自然语言写的现象 → `differential.considered`；因缺 slug 而无归因出口的 → `differential.not_evaluable`，
   文本形如 `"偏振/双模峰劈裂：无可用 cause slug（KB6 §G-1 未采纳）"`。
2. `ruled_out_alternatives[].cause` **允许**非 slug 自然语言（它表达"排除了什么"，不是"下结论"）。
3. **禁止用近似 slug 顶包**（光学 → `mechanical_thermal_drift`、工装 → `mechanical_loose_structure`、
   模场失配 → `electrical_*`）：出现一次即与 C5"无依据成功声明"同级失败。宁缺（`not_evaluable`）勿假。
4. `verdict.primary` 不得指向只有 `considered` 支撑的假设；若 A/B 组结论全部退化为
   `considered`/`not_evaluable`，正确输出是 `actionable: false` + `next_data_to_collect` 非空（C3 硬规则 5）。

**正文自检结论**：R-31 … R-50 的 `cause` 全部落在 KB0 §2 三族内或标注 `family: null`；正文只在
**排除项/差额登记**处点名上表名字，且每次都是"属 G-1，裁决 A-16 未采纳 ⇒ 记 `considered` /
`not_evaluable`"的口径，**没有任何规则把它们写进 `cause`**。

## G-2 `family: null` 的三条门禁规则（R-37 / R-49 / R-50）—— **已裁：采纳（A-17；C7 §8-2）**

这三条**无 cause**：R-37 是拒答规则；R-49 的结论是"复标/拒收"而非根因；R-50 约束的是统计方法。
KB0 §6 检查 2 原按字面（"每条规则的 `cause` 在 §2 表内"）会把这三条判为非法。**裁决已采纳**：
KB0 §2/§6 检查 2 放宽为"在 §2 表内 **或** 标注 `family: null` 的门禁/拒答类"，本文正文一律写
**`family: null`**（旧版写 `family: —`，已全部替换；`null` 是可机读的缺失表达，`—` 是排版符）。

**该类在本项目的输出形状（权威在 C7 §8-2，本文按此对齐三条规则正文）**：
1. **登记义务优先**：触发即写 `audit.rules_fired`（门禁被触发是事实，必须可统计、可被 C5 打分）。
2. `differential` 侧双登记：`not_evaluable` 写明"**缺什么才能下结论**"；`considered` 写自然语言候选。
3. **永不产生 `hypotheses[]` 条目**：`overall_confidence <= 0.45`、`actionable: false`，
   动作只允许 `rerun_step` / `request_data` / `schedule_verification`（本文 **§C.3 第 9 行**）。
4. 计入 C5 的**拒答正确率**指标：`none_of_the_above` 配额 ≥ 15%（C5 §2），三条各至少一个案例；
   agent 在这些案例里编一个机械原因就是错。

**呈现纪律（C7 §8-3，已写进 §C.3）**：`light_curve.series_stats.ref_scan_ids` 为空、`calibration.spec` 为 `null`、`scan_program`
缺失、`events.jsonl` 缺失这四类是**覆盖度问题**（可补数据），与门禁触发（**结论边界问题**，正确拒答）
**必须分开呈现**，不得混写成同一条"数据不足"。

**形式定义归属**：C3/KB4 需给出 `family: null` 类的完整 schema（本文件只声明引用，不代 C3/KB4 定义；
C7 §8-2 亦只声明引用约定）。

## G-3 已登记于 C7 的特征（**已裁：A-36 —— 原"待并入 C2"清单，该机制作废**）

**裁决口径**：KB6 的工艺侧特征**不并入 C2**，而由独立契约 **C7**（`docs/contracts/C7-process-context.md`）
承载，物理载体是样本包内的 `process.json`（A 组 + `scan_program` + `cycle_stats`）与
`calibration.jsonl`（B 组）。C7 §1.1-4 明文"C2 不因本文件新增任何字段"。因此：

1. **原"引用未并入 C2 的 KB6-NEW 特征 ⇒ `blocked`"机制作废**（不再有 KB6-NEW 状态；A-34 已把 KB0 §3
   的排他句改为"C2 或已登记的 C7 路径"）。
2. 现在生效的是 **C7 §7.1**：**未登记路径引用即无效** —— 加载期解析不到 ⇒ `blocked`，理由文本
   `"feature path not registered in C2 or C7 (C7-NEW)"` ⇒ 逐条 `audit.rules_skipped` ⇒ 对应 fault_mode
   写 `differential.not_evaluable`（与 `freq_limits.blocked_rules` 同构）。
3. **C7 §1.2 缺档纪律**（文件级缺失）与上一条并存：`process.json` 缺 ⇒ A 组全量 `blocked`；
   `calibration.jsonl` 缺 ⇒ B 组全量 `blocked`；`power_channel.present == false` / `cycle_stats.available == false` /
   `scan_program` 或其 `source` 缺失 ⇒ 对应判据 `not_evaluable`（见 **§C.3 第 13 行**）。
4. 下表**逐行对齐 C7 的登记表**（C7 §7.1 #1–15），字段口径权威在 **C7 §2.2 / §4.2 / §5 / §6**；
   本表只保留"KB6 正文哪条规则用哪一组"的索引作用，**不再私改 C2**。

**登记表**（前缀 → 使用规则 → tier；权威载体列 = C7 落点）

| # | 点号路径 | 权威载体（C7） | 使用规则 | tier |
|---|---|---|---|---|
| A1 | `power_channel.{present, unit, transport, sample_rate_hz, n_samples, integration_time_ms, poll_period_ms, timestamp_source, dt_jitter_ratio, ratio_to_servo_fs, reliable_band_hz, noise_dominant_freq_hz, quantization_step_db, align_residual_ms, nan_ratio}` | `process.json`（C7 §2.2 A1；§3 全部门禁的输入） | R-31/34/36/38/42 的门禁与判据 | T2 定义 |
| A2 | `light_curve.scans[].{segment_id, scan_kind, axis, direction_sequence, t0, t1, n_points, point_step_counts, sweep_span_counts, curve_npy, peak_index, peak_power, peak_position_counts, fwhm_counts, plateau_ratio, n_local_maxima, secondary_peak_over_peak_ratio, local_maxima_separation_counts, asymmetry_ratio, edge_peak_flag, noise_floor_std, snr_ratio, gaussian_fit_r2, dither_amplitude_counts, step_count, step_spacing_counts, step_spacing_std_counts, step_height_db, repeat_read_delta_db, cross_axis_drift_counts, vision_angle_excursion_ratio}` | `process.json` + `features/process/*.npy`（C7 §2.2 A2；全量曲线走 `.npy`，C2 规则 1/3 同构） | R-31…R-36/38/42 | T2+T3 |
| A3 | `light_curve.series_stats.{n_scans, peak_power_cv, peak_power_drop_pct_vs_ref, fwhm_growth_pct_vs_ref, noise_floor_trend_ratio, peak_position_drift_counts, drift_slope_counts_per_scan, drift_p_value, spearman_rho, asymmetry_vs_travel_spearman_rho, ref_scan_ids}` | `process.json`（C7 §2.2 A3，**趋势类判据的唯一证据来源**） | R-31/33/35/36/37 | T2+T3 |
| A4 | `light_curve.motion_sampling_conflict.{samples_in_motion, in_motion_sample_ratio, settle_gap_ms, required_settle_ms, step_over_fwhm_ratio, peak_never_sampled_flag, direction_reversal_count, apparent_peak_lag_counts, apparent_peak_lag_over_step_ratio, lock_track_noise_ratio}` | `process.json`（C7 §2.2 A4；**`required_settle_ms = step_response[].settling_time_ms + power_channel.integration_time_ms`，两侧任缺即 `null`**） | R-31/42 + §A.3 M-a…M-e | T3（几何推导） |
| A5 | `light_curve.scan_integrity.{expected_point_count, actual_point_count, truncated_flag, truncation_reason, tail_gap_ms, host_pause_during_scan, event_overlap_sources[], edge_slope_ratio}` | `process.json`（C7 §2.2 A5；`expected_point_count` 权威出处 = `scan_program.segments[].n_points_expected`，**不得反填**） | R-37/41 | T3 |
| A6 | `light_curve.vision_write_back.{power_timestamp_source, write_back_delay_ms, vel_at_write_back_counts_s, stale_coord_mismatch_counts}` | `process.json`（C7 §2.2 A6；**复用** C2 `event_context.{vision_result_latency_p95_ms, alignment_residual_ms, causal_claims_permitted}`，不重定义） | R-33/34 | T2+T3 |
| A7 | `light_curve.encoder_masquerade.{residual_period_counts, residual_period_ratio_to_per_rev, residual_amplitude_counts, amplitude_ratio_vs_encoder_per_rev, agrees_with_second_sensor}` | `process.json`（C7 §2.2 A7；**复用** C2 `encoder.{phase_locked_to_pos_modulo, detrended_r2}`） | R-36/40 | T1-a 形态级 + T3 |
| B1 | `calibration.sessions[].{cal_id, kind, n_points, layout, axis_group, recipe, step, machine_temp_c, fixture_id, plate_grade, operator, timestamp_s, residual_vectors_counts[], residual_vectors_counts_npy, mean_residual_counts{mx,my,mag,dir_deg}, rms_residual_counts, systematic_share_pct, isotropic_ratio, residual_rms_first_half_counts, residual_rms_second_half_counts, radial_slope_ratio, tangential_mean_ratio, radial_sign_pattern, tangential_sign_pattern, split_shift_counts, split_p_value, split_ci_counts, trend_slope_counts_per_index, trend_p_value, spearman_rho, oos_point_ratio, direction_pair_diff_counts{u_pos,u_neg,d_pos,d_neg}}` | `calibration.jsonl`，`record_type == "session"` 一行一批次（C7 §4.1/§4.2 B1；数组下标按 `timestamp_s` **升序**重排；逐点矢量走 `.npy`，JSON 存降采样版） | R-43…R-49 | T2+T3 |
| B2 | `calibration.field_pattern.{dominant_pattern, linear_fit_r2, low_order_coefficients, morans_i, quadrant_sign_consistency}` | 同名 session 行内对象（C7 §4.2；**每批次一份**，A-39 **段 = 批次**） | R-43/44/45/46 | T3 |
| B3 | `calibration.series.{n_sessions, rms_cv_pct, oos_ratio, worst_subgroup_share_pct, slow_tail_ratio, chart_type, subgroup_size, control_limits[], violation_rules_fired[], segment_break_points[], violations_before_resegmentation, violations_after_resegmentation}` | 唯一一条 `record_type == "series"` 尾行（C7 §4.1 第 2 条，裁决 **A-37**：跨批次统计不入 `process.json`） | R-44/47/49/50 + §B.3/§B.4 | T2 |
| B4 | `calibration.spec.{rms_counts, max_counts, source, version}` | session 行回显，全文件取值必须一致（C7 §4.1 第 3 条 / §4.4） | R-49 —— **门禁字段，禁入 `supporting_evidence[]`**（KB0 §3 / KB6 §0.3-2） | T2 |
| B5 | `calibration.correlation_screen.{with_temp_r, with_fixture_batch, with_plate_grade, with_operator, with_time_since_last_cal_r}` | `record_type == "series"` 行（C7 §4.2；**本组不新增因果布尔**，开关只复用 `event_context.causal_claims_permitted`，C7 §4.2/§4.3） | R-43/48 | T2 |
| S1 | `scan_program.{units, source, confidence, segments[].{segment_id, kind, scan_type, step_counts, pitch_counts, dwell_ms, n_points_expected, raster_line_count, feedrate_counts_s, dither_freq_hz, dither_amplitude_counts}}` | `process.json`（**C7 新增**，C7 §7.1 #13 / §5；正文旧稿无此登记行，M-2 由此闭合） | §A.1.1 / §A.3 陷阱 1–2 / R-31b / R-38c / R-41a / R-42c/d；缺档见 §C.3 第 13–14 行 | T2 声明 |
| C1x | `cycle_stats.{available, cycle_source, units, ref_cycle_time_ms, n_cycles, n_by_step, cycle_time_median_ms, cycle_time_p95_ms, cv_pct, slow_tail_ratio, slow_cycle_share_pct, grouping_keys[], segments[], segment_break_points[], violations_before_resegmentation, violations_after_resegmentation}` | `process.json`（**C7 新增**，C7 §7.1 #14 / §6；KB6 §1 已声明**不向 C2 加** `cycle_jitter`，M-6 由此闭合） | §B.3 快/慢变量纪律 / §B.4 / R-50 分段义务 | T2 |
| X | 结构性字段：顶层 `blocked_claims[]`、`unavailable[]`、`ref.*`、`*_npy`、`t0/t1`、`reliable_band_hz`、`align_residual_ms`、`nan_ratio` | `process.json` / `calibration.jsonl`（C7 §7.1 #15） | 不承载判据语义，登记以免拼写漂移 | 不适用（结构字段） |

**残余登记缺口（本文件不自造 C7 字段，只登记）**：正文 R-48a 用到
`calibration.correlation_screen.with_temp_ci` 与 `with_fixture_batch.{welch_p, effect_over_rms}` 三个**子键**。
它们出现在 **C7 §4.1 的 JSONL 示例**里、语义也在 C7 §4.2 的口径列中（"相关系数 **+ CI**""分组差异 =
Welch t ∧ 效应量 `>= 1 × rms`"），但 **C7 §4.2 的 B5 字段清单与 §7.1 登记表只列到父键**
（`with_temp_r` / `with_fixture_batch` / …）。按 KB0 §6 检查 1"字段名逐字一致"的口径，这三处属
**示例已含、清单未逐字登记**的缺口，需主线程在 C7 §7.1（或 §4.2 B5 行）补子键；本文**不擅自扩张 C7 字段表**，
R-48a 也**不得**因缺口而改判为"未发现问题"——缺档时按 §C.3 第 2/13 行登记 `not_evaluable`。

**R² 命名（已裁：A-38 采纳）**：命名约定 `<domain>.<fit_name>_r2` 的权威在 **KB0 §3**；本文相应字段写作
`light_curve.scans[].gaussian_fit_r2`（域 = `light_curve.scans[]`、拟合名 = `gaussian`）与
`calibration.field_pattern.linear_fit_r2`（域 = `calibration.field_pattern`、拟合名 = `linear`），
与 C2 既有 `encoder.detrended_r2` 同构、**不改任何既有字段名**；拟合不可用时在 `unavailable[]` 给理由
（C7 §2.2 A2 / §4.2），避免 R² 语义分裂。


## M 类：契约与文档缺口 —— **逐行已裁状态（原文留痕；除 M-5 外全部闭合）**

| 项 | 问题 | 原请求 | 已裁 |
|---|---|---|---|
| M-1 | C1 通道词表里 `laser_power` 一行写"见 C7"，但 `docs/contracts/` **没有 C7** | 新建 C7（耦合/工艺通道契约）或把引用改指 KB6 §A.1.2；否则是悬空引用 | **已裁：C7 已建立**（`docs/contracts/C7-process-context.md`，§0 末句兑现 C1 的"见 C7"）。本文全部工艺路径改按 C7 口径，见 **G-3** |
| M-2 | 寻光扫描轨迹参数（螺距、线距、爬山步长、驻留时长）无处声明，导致 §A.3 的 `step/FWHM`、`required_settle_ms` 没有权威出处；C6 `machine_context` 只有 `recipe/step/step_sequence` | 在 C6 `machine_context` 增 `motion_program: {…}`，或明确由 C7 承载 | **已裁：A-28 + A-41** —— 权威载体 = **C7 `scan_program`**（C7 §5），**不给 C6 加字段**（双载体已消除，C6 §2 只留一句指向）；`inferred_from_waveform` 的循环论证封顶落在本文 **§C.3 第 14 行** |
| M-3 | `calibration.sessions[]` / `calibration.spec` 的物理载体未定（独立 `calibration.jsonl`？其 `event_context` 与因果开关从哪来？温度序列与标定时间戳是否同源？） | 在 C6/C7 定载体与校验规则，并写明"无 `event_context` 时因果开关默认 false" | **已裁：C7 §4.1/§4.3** —— 载体 `calibration.jsonl`（一行一批次 + 唯一 `record_type == "series"` 尾行，**A-37**）；因果开关唯一来源是 C2 `event_context.causal_claims_permitted`，无 `event_context` ⇒ **默认 `false`**（C7 §4.3-2）；温度序列与标定时间戳**必须同源**，异源只作共现（C7 §4.3-4）。本文 §B 组通用纪律已对齐 |
| M-4 | 标定数据不在 T1-a/T1-b 中；B 组真实锚点只剩形态级且只覆盖尺度/方向两类（R-45/R-46），其余 6 条完全依赖 T2+T3 | 建议新增 **T0** 层：本项目**自行执行**的标定实验（自建网格工装 + 真实相机 + 真实轴 + 自记温度）——它是真实测量但**不是产线**，须在 C5 §1 单列并禁止与 T1 混算 | **已裁：A-24 —— 不新增 T0**，改为**有条件**采纳 **T1-c「自采真实测量（非产线）」**：只有自建工装 + 相机 + 轴实测才登记；拿不到则 B 组声明只有 T2+T3；**禁止**与 T1-a/T1-b 混算能力指标。本文 §B 组 tier 前言已按此写 |
| M-5 | KB5 尚无"合成标定数据 + 耦合效率曲面"生成器规范（§A.4.2 与 B 组的 T3 检验都依赖它） | 请 KB5 增节；参数空间与 §A.4.2 对齐，且**不得与规则阈值共享常数**（防同源自证） | **仍开放**（本文唯一未闭合项）：KB5 至今不含耦合效率曲面/标定网格生成器，也未引用 KB6。§A.4.2 的 T3 设计自足可复算，实现排在实现期；按 **A-30**"待裁决清单实现期前必须清空"，此条须由 KB5 侧回写 |
| M-6 | 任务书要求引用 C2 的 `cycle_jitter`，但 C2 现有草案中**不存在**该字段 | 请确认是否新增。本文按"只借用设计模式（分组 + 比值 + 右尾敏感）"处理，未引用不存在的路径 | **已裁：A-25** —— 节拍统计**不进 C2**，归 **C7 `cycle_stats`**（C7 §6）并与 `calibration.series` 一样**强制分段**，未分段本身登记为诊断缺陷；本文 §1/§B.3 **只借设计模式**，未引用不存在的 `cycle_jitter` 路径 |
| M-7 | KB3 尚未落盘，本文规则块字段是其**预测形状** | KB3 定稿后由主线程统一本文字段顺序；并在 KB0 §6 增检查："KB6 每条规则的证据路径必须在 C2（含已并入的 KB6-NEW）存在；`cause` 必须在 §2 表内或标注 `—`(gate)" | **已裁：KB3 已落盘**（R-01…R-30，规则块字段顺序与本文同构）；**KB0 §6 检查 1** 已写成"路径在 **C2（伺服侧）或 C7 §7.1（工艺/标定侧）**存在、字段名逐字一致"（**A-34**，"已并入的 KB6-NEW"这一表述作废）；**检查 2** 已放宽为"在 §2 表内 **或** 为 `null`（门禁/拒答类，A-17）"——**`null` 而非 `—`** |
| M-8 | C3 的 `differential` 示例未演示"有 `not_evaluable`、无 `considered`"的形状 | 本文 R-37/R-44/G-1 都需要该形状，请在 C3 示例里补齐 | **已裁：C3 硬性规则 11 + 12** —— 规则 11 把"门禁/拒答规则（`family: null`）"列为一等公民（明确点名 KB6 R-37/R-49/R-50：进 `audit.rules_fired` + `differential.not_evaluable`，**不进** `hypotheses[]`，计入 C5 拒答正确率）；规则 12 允许"只有 `not_evaluable`、`considered` 为空"的形状并要求原样呈现 |


## 待办（不在本文件范围）

- ~~KB4 归因树需为 A/B 两组加叶子并与 `R-31 … R-50` 一一对应~~ **已闭环**：KB0 §6 检查 3 改写为
  "叶集合 = KB0 §2 的 22 个 slug，每叶至少被一条 KB3 主判据锚定"（**A-17**），KB6 规则一律以
  **同 slug 的交叉锚点**进入 KB4 §1.1 表与 §1.3 N8（`R-45/R-47→叶 20；R-46/R-44→叶 7；R-43/R-48→叶 8；
  R-31→叶 22；R-32→叶 3`），门禁/元规则（`family: null`）不产叶——**不新增 slug** 正是 A-16 的结论。
- C5 案例集：`R-37 / R-49 / R-50` 三条门禁各至少一个 `none_of_the_above`/`refuse` 案例（计入 ≥15% 配额）。
  **部分闭环（A-86）**：KB8 §6 配额表已加"KB6 门禁类三例 ≥3"一行；本文件此前与基准集**零交集**这一事实由
  该轮自查发现并登记。其余 `R-31…R-48` 的案例不在本期配额内，实现期再补。
- 作品集叙事：§A.3 的"采样—运动互斥 5 项检查"与 §B.3 的"为什么不能只用 P95/中位数"最能体现工程判断，建议作为技术答辩主讲页；§A.4.1 的"没有产线数据"必须同页呈现。

## 引用与出处（T2；标"待核对"者为方向性依据，不得当精确引用使用）

- 伺服/机械侧阈值出处沿用 KB3 的 T2 条目（摩擦、背隙、编码器周期误差、共振）。
- 功率计积分时间/响应时间/读数速率限制：仪器手册类（**待核对具体型号与档位**）。
- 高斯模场耦合近似与 `step/FWHM` 关系：光学耦合通行近似；本文推导**自足可复算**（`FWHM = 2√(2 ln 2)·w ≈ 1.1774·w` 为标准定义），不依赖具体文献数值。
- 固化收缩与温漂造成耦合位移：封装工艺文献（方向性，**本文未给数值阈值**）。
- 跨厂商单位/分频口径不一致（`pulse/s` vs `单位/秒`，1000 倍量纲差）：控制卡手册口径对比，素材见 `docs/AUDIT-minimax-mcopilot.md` §一（**仅借用现象，不借用检出率声明**）。
- SPC 阶段化/分段与 Western Electric 规则：`ISO 7870-1`（控制图总则）+ `ISO 7870-2:2013, Control charts —
  Part 2: Shewhart control charts`（**A-85** 收口原"条目待核对"；这些标准是付费文本，**只按标准号引用、不写 DOI**）。
  Western Electric 规则 1–4 的原始出处是 Western Electric 1931 年的检验手册，本项目只用到规则 1–3，
  并说明小样本下为何不用后续规则（R-50 的"分段先于判异"纪律不依赖任何一条具体规则编号）。
- T1-a 锚点：`docs/kb/KB7-dataset-da-rus-cat.md`（DaRUS，CC BY 4.0，署名 Reichenbach / University of Stuttgart，DOI 10.18419/DARUS-3600、10.18419/DARUS-5171）；**仅用于**摩擦/爬行（R-39）、多传感器不一致与编码器周期误差（R-40）、低频纹波与驻留残余振动（R-36）的**形态级**验证；不含耦合、不含标定网格、不含 µm 结论。
- 防自验证纪律：`docs/DECISION-2026-10-19-方向裁决.md` §5 与 `docs/AUDIT-minimax-mcopilot.md` §二；本文 §A.4.2 是其在 KB6 的落地。
