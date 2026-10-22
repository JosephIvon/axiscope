# C7 — 工艺上下文契约（耦合寻光 / 标定 / 节拍）

## 0. 为什么需要它

KB6 的寻光与标定判据需要一整类**不属于伺服波形**的证据：功率计采样元数据、"功率—位置"曲线形态、
跨扫描趋势、扫描—运动互斥、标定残差矢量场、SPC 分段。全部塞进 C2 会把通用诊断内核与工艺外壳耦合，
且 C2 规则 4（"每个特征必须可追溯到公式或文献"）在**缺光学真值**的工艺侧无法满足。故独立成契约，
物理载体为样本包内的 `process.json` 与 `calibration.jsonl`。C7 的全部新语义只有一条：**采样栅格决定
可声明的分辨率上限**。功率计比伺服环慢 2–3 个数量级（1–20 Hz vs 1–8 kHz），所以工艺侧最危险的失效模式
不是判错，而是拿一条分辨不出峰形的曲线去断言"峰位在 X counts"。本文件把它写成门禁（§3），不是抱怨。
C1 词表 `laser_power` 行的"见 C7"由此兑现。

## 1. 定位与边界

### 1.1 文件与时间轴
```
sample/
  meta.json  waveform.tsv     # C1，必需
  process.json                # C7，**可选**：功率元数据 + 寻光曲线形态 + scan_program + cycle_stats
  calibration.jsonl           # C7，**可选**：一行一个标定批次（B1–B5）
  events.jsonl                # C6，可选
  features/process/*.npy      # C7 数组旁路
```

1. `process.json` / `calibration.jsonl` 的所有 `t` / `timestamp_s` 使用 C1 `waveform.tsv` 第 1 列的时间基准（秒、从 0 起、单调递增）。**共用时间轴，不共用采样栅格**：工艺样本按自身稀疏栅格记录，栅格比由 `power_channel.ratio_to_servo_fs` 声明。设备绝对时间戳须先经 C6 `event_context.sync` 折算，残差写 `power_channel.align_residual_ms`；`|Δt| <= sync.uncertainty_ms` 的对齐不得作为证据（C6 硬规则 2）。
2. **稀疏读数不写进 `waveform.tsv`**（否则撞 C1 红线 `nan_ratio > 0.05`）：只有"模拟监视输出 → 与伺服同时钟采集"（KB6 §A.1.2 表第 3 行）才允许 `laser_power` 作为等间隔列，此时 `transport == "analog_daq"` 且 `timestamp_source == "device"`。
3. 数组字段（曲线序列、逐点残差矢量）按 C2 规则 1 同构：JSON 存降采样版（≤2048 点），全量写 `features/process/<path>.npy`（路径中 `.`→`_`），JSON 给 `*_npy` 相对路径。
4. **C2 不因本文件新增任何字段**。规则引擎对两个证据源有同等读取权，但 C7 判据不得改写 C2 输出，反之亦然；两边 `unavailable` 各自登记、由 C3 汇总。

### 1.2 缺档纪律（硬性，与 C2 规则 7/8 同强度）
1. `process.json` **缺失** ⇒ KB6 A 组（R-31 … R-42）加载期全部判 `blocked`，理由文本 `"process.json absent (C7)"`，逐条写 `audit.rules_skipped`，并把每条对应 fault_mode 逐条写 C3 `differential.not_evaluable`。**绝不允许**在任何字段输出"未发现工艺异常""耦合曲线形态正常""无采样伪影"——那是把"没有读数"说成"没有异常"，与 C2 规则 7 禁止的"未发现共振"同一种造假，并违反 C3 硬规则 9。
2. `calibration.jsonl` 缺失 ⇒ B 组（R-43 … R-50）全部 `blocked`，登记"无标定批次记录"。
3. `power_channel.present == false` ⇒ 声明"本机台本次未采功率"，按第 1 条同等登记；此情形与文件缺失**必须在报告里区分**（前者可补采，后者是解析覆盖度问题）。
4. `scan_program` 或其 `source` 缺失 ⇒ 所有依赖步长的判据（`step_over_fwhm_ratio`、`point_step_counts <= 0.1 × fwhm_counts`、R-38c、R-42c/d）一律 `not_evaluable`，**不得**用 `light_curve.scans[].point_step_counts`（波形派生）顶替声明值（§5 硬规则 1、2）。
5. `cycle_stats.available == false` ⇒ 节拍类结论不启用，**禁止**输出"节拍正常"。
6. 文件存在但依赖字段为 `null` ⇒ 该判据放弃并追加 `unavailable`（C2 规则 2 同构），不得插值、不得取默认值。

### 1.3 范围纪律（继承 C6 §5，不得弱化）
C7 只服务**诊断证据**。不实现：寻光/爬山执行引擎、峰值锁定与 dither 解调、标定参数求解（3×3 仿射、
`AX=XB`、运动学补偿表）、SPC 引擎与在线报警、配方回滚、任何写设备动作（C3 硬规则 6：
`safety.writes_to_device` 恒 `false`）。`calibration.series.control_limits` 与 `cycle_stats.segments[]`
只是**已算好事实的陈述**，用于判定"这次分析是否合法"，不驱动恢复；恢复只以 C3
`recommendation.field_procedure`（人执行文本）存在。

## 2. `process.json`

### 2.1 示例（量级取自 8 Hz 串口功率计 + 8 kHz 波形的真实档）
```json
{
  "schema": "axiscope.process/1",
  "ref": {"sample_id": "CPL-20260417-03", "waveform_sha256": "…", "time_base": "c1:waveform.tsv.t", "servo_fs_hz": 8000.0},
  "power_channel": {"present": true, "unit": "dBm", "transport": "serial", "sample_rate_hz": 8.0, "n_samples": 964, "nan_ratio": 0.0, "integration_time_ms": 180.0, "poll_period_ms": 125.0, "timestamp_source": "host_poll", "dt_jitter_ratio": 0.09, "ratio_to_servo_fs": 1000.0, "reliable_band_hz": 6.4, "noise_dominant_freq_hz": null, "quantization_step_db": 0.1, "align_residual_ms": 62.0},
  "light_curve": {
    "scans": [{"segment_id": 7, "scan_kind": "spiral", "axis": "X2", "direction_sequence": ["+"], "t0": 1.204, "t1": 16.402, "n_points": 121, "point_step_counts": 640.0, "sweep_span_counts": 77440.0, "curve_npy": "features/process/light_curve_scans_0.npy", "peak_index": 74, "peak_power": -8.42, "peak_position_counts": 46080.0, "fwhm_counts": 2100.0, "plateau_ratio": 0.34, "n_local_maxima": 2, "secondary_peak_over_peak_ratio": 0.41, "local_maxima_separation_counts": 690.0, "asymmetry_ratio": 1.12, "edge_peak_flag": false, "noise_floor_std": 0.031, "snr_ratio": 4.2, "gaussian_fit_r2": 0.88, "dither_amplitude_counts": null, "step_count": 0, "step_spacing_counts": null, "step_spacing_std_counts": null, "step_height_db": null, "repeat_read_delta_db": 0.05, "cross_axis_drift_counts": 180.0, "vision_angle_excursion_ratio": null}],
    "series_stats": {"n_scans": 7, "peak_power_cv": 0.06, "peak_power_drop_pct_vs_ref": 3.1, "fwhm_growth_pct_vs_ref": 62.0, "noise_floor_trend_ratio": 2.4, "peak_position_drift_counts": 5400.0, "drift_slope_counts_per_scan": 810.0, "drift_p_value": 0.004, "spearman_rho": 0.93, "asymmetry_vs_travel_spearman_rho": 0.12, "ref_scan_ids": [0, 1]},
    "motion_sampling_conflict": {"samples_in_motion": 41, "in_motion_sample_ratio": 0.28, "settle_gap_ms": 95.0, "required_settle_ms": 415.0, "step_over_fwhm_ratio": 0.30, "peak_never_sampled_flag": false, "direction_reversal_count": 6, "apparent_peak_lag_counts": -211.0, "apparent_peak_lag_over_step_ratio": -0.33, "lock_track_noise_ratio": 1.9},
    "scan_integrity": {"expected_point_count": 121, "actual_point_count": 121, "truncated_flag": false, "truncation_reason": null, "tail_gap_ms": null, "host_pause_during_scan": 0.0, "event_overlap_sources": [], "edge_slope_ratio": 0.08},
    "vision_write_back": {"power_timestamp_source": "host_poll", "write_back_delay_ms": 260.0, "vel_at_write_back_counts_s": 3400.0, "stale_coord_mismatch_counts": 430.0},
    "encoder_masquerade": {"residual_period_counts": 524288.0, "residual_period_ratio_to_per_rev": 1.0, "residual_amplitude_counts": 240.0, "amplitude_ratio_vs_encoder_per_rev": 1.3, "agrees_with_second_sensor": null}
  },
  "scan_program": { "…": "见 §5" }, "cycle_stats": { "…": "见 §6" },
  "blocked_claims": [{"claim": "peak_position_counts @ scan 7", "why": "step_over_fwhm_ratio=0.30 → fwhm 仅 3.3 个栅格点", "gate": "C7-§3.3-1"}],
  "unavailable": [
    {"feature": "power_channel.noise_dominant_freq_hz", "reason": "sample_rate_hz=8.0 < 20：奈奎斯特 4 Hz，频率声明无效（§3.4）"},
    {"feature": "light_curve.encoder_masquerade.agrees_with_second_sensor", "reason": "仅一套位置测量，交叉验证不可做"}]
}
```

### 2.2 A 组逐字段口径（**本表即工艺侧特征索引**；语义源自 KB6，权威载体已移交 C7，见裁决 A-36/A-40）
**A1 `power_channel.*`** —— §3 全部门禁的输入。

| 字段 | 口径 | tier |
|---|---|---|
| `present` `unit` `transport` | 三者全必填。`unit ∈ {µW, dBm, V_raw}`，`V_raw` ⇒ 禁用 dB 类判据（R-38b），且 µW↔dBm 换算不得由本层做（单位切换是 R-37 排除项）；`transport ∈ {serial, gpib, analog_daq, unknown}`，`analog_daq` 是唯一可做曲线形态级判据的形态 | T2 |
| `sample_rate_hz` `n_samples` `nan_ratio` | 读数速率中位 / 有效读数个数 / 缺口占比。`sample_rate_hz == null` ⇒ A 组全部 `not_evaluable`；`n_samples < 20` 禁判量化台阶；`nan_ratio` 口径**独立于 C1**（功率序列本就稀疏，见 §X-1） | T2 / C1 |
| `integration_time_ms` `poll_period_ms` | 单次读数积分窗（手册档位；R-31a、`required_settle_ms` 右半）/ 轮询周期（R-34a 分母；`host_poll` 时对齐不确定度 ≥ `poll_period_ms/2`） | T2 |
| `timestamp_source` `dt_jitter_ratio` | M-d 检查项，非 `device` ⇒ 因果降级（§4.3）；`dt_jitter_ratio` **同 C1 定义**、按读数间隔计算，`> 0.2` 时噪声底升高不可归因于运动 | T2 / C1 |
| `ratio_to_servo_fs` | **`= servo_fs / sample_rate_hz`**（`servo_fs` 取 C1 `meta.sample_rate_hz`）；A 组第一门禁参数（§3.2） | 派生 |
| `reliable_band_hz` `noise_dominant_freq_hz` | **`= sample_rate_hz / 1.25`**（沿用 C2 规则 7 余量式）；后者**仅当 `sample_rate_hz >= 20` 才允许非 null** | C2 规则 7 / T2 |
| `quantization_step_db` `align_residual_ms` | 读数分辨率，`null` ⇒ R-38 不启用（不得改判"无台阶"）；折算到 C1 时间轴的对齐残差，`<= uncertainty_ms` 即作废（C6 硬规则 2） | T2 / C6 |

**A2 `light_curve.scans[]`**（一扫描一条；曲线几何形态）

| 字段 | 口径 |
|---|---|
| `segment_id` `scan_kind` `axis` `direction_sequence` `t0` `t1` `n_points` | `segment_id` 必须能在 C1 `segments` 解析到且 `kind ∈ {scanning, probing, dwell}`；`scan_kind` 与 `scan_program.scan_type` 一致（不一致见 §5 硬规则 5） |
| `point_step_counts` `sweep_span_counts` | 相邻读数间的**实际位移**（取 `pos_fb`；扫描期不得用 `pos_cmd` 反推，KB6 §A.1.3-4）/ 总行程跨度 |
| `peak_index` `peak_power` `peak_position_counts` | 峰的栅格分辨率下界 = `point_step_counts`（§3.3）；`peak_index ∈ {0,1,2,n-3,n-2,n-1}` 触发 R-41b；`peak_power` 单位随 `power_channel.unit` |
| `fwhm_counts` `plateau_ratio` | FWHM（counts 域）；`fwhm_counts < 3 × point_step_counts` ⇒ 不可分辨，一切以 `fwhm_counts` 归一的判据拒收；平顶占比（R-31c ≥ 0.3） |
| `n_local_maxima` `secondary_peak_over_peak_ratio` `local_maxima_separation_counts` | R-32 三元组；间距与 C2 `global.backlash_estimate_counts` 比较，纯 counts ⇒ 缺 `counts_per_mm` 仍成立 |
| `asymmetry_ratio` `gaussian_fit_r2` `noise_floor_std` `snr_ratio` | 峰两侧半峰斜率之比（无量纲，R-35a）/ 单扫描高斯拟合优度（与 C2 `encoder.detrended_r2` 同类不同域，§X-7）/ 本底标准差 / 信噪比（`<= 6` 为劣化档，R-36b） |
| `edge_peak_flag` `dither_amplitude_counts` | 边缘峰标志（R-41）；无 dither 段 ⇒ `null`，`≈ 0.1 × fwhm_counts` 为陷阱 4 设计档 |
| `step_count` `step_spacing_counts` `step_spacing_std_counts` `step_height_db` | R-38 等间距台阶四元组；`step_height_db` 与 `power_channel.quantization_step_db` 同阶才判量化 |
| `repeat_read_delta_db` `cross_axis_drift_counts` `vision_angle_excursion_ratio` | 同位置、逼近段与退离段各一次读数之差（R-39d，需 `direction_sequence` 含反向对）；**垂直轴漂移取第二轴 `pos_fb` 或 `vision_y` 的窗内漂移量**（不自选好看的）；角度偏移**相对该轴自身角度噪声底归一**（R-35c） |

**A3 `light_curve.series_stats`** —— 跨扫描统计，**趋势类判据的唯一证据来源**

| 字段 | 口径 |
|---|---|
| `n_scans` `ref_scan_ids` | `< 5` ⇒ 斜率检验不可信，**禁止**输出单调性结论；`ref_scan_ids` 为空 ⇒ 全部趋势判据上限 0.5（KB6 §C.3 第 8 行），`null` **不等于**"无漂移" |
| `peak_power_cv` `peak_power_drop_pct_vs_ref` `fwhm_growth_pct_vs_ref` `noise_floor_trend_ratio` | 全部为对 `ref_scan_ids` 的比值/百分比形式 ⇒ 缺 `counts_per_mm` 时依然可用 |
| `peak_position_drift_counts` `drift_slope_counts_per_scan` `drift_p_value` `spearman_rho` | 漂移量 / 逐扫描斜率（同号性）/ 趋势显著性 / 秩相关（R-33b） |
| `asymmetry_vs_travel_spearman_rho` | **不对称量对扫描起止位置的秩相关**，与对时间的 `spearman_rho` 分别报（R-35d 用它排除 R-33） |

**A4 `light_curve.motion_sampling_conflict`** —— KB6 §A.3 M-a…M-e 的落地

| 字段 | 派生式 / 口径 |
|---|---|
| `samples_in_motion` `in_motion_sample_ratio` `settle_gap_ms` `required_settle_ms` | M-a 静止判据：读数窗内 `vel_fb` 全程 `< 0.1% ×` 该点逼近速度 ∧ `abs(fe) < step_response[].settle_band_counts`；M-e 占比上限 0.1；**`required_settle_ms = step_response[].settling_time_ms + power_channel.integration_time_ms`**（两侧任缺即 `null`）；`settle_gap_ms` = 最后一次速度指令归零到读数开始的实测间隔 |
| `step_over_fwhm_ratio` | **`= point_step_counts / fwhm_counts`**；`> 0.15` 已越可辩护界（R-42c），`> 1/3` 触发 §3.3 拒收 |
| `peak_never_sampled_flag` `direction_reversal_count` | 无任何读数落在 `[peak − fwhm/2, peak + fwhm/2]`；反转数持续增长而 `peak_power` 不提高 ⇒ 步进档位错误，**不是"没有峰"** |
| `apparent_peak_lag_counts` `apparent_peak_lag_over_step_ratio` | 匀速扫一阶近似 **`≈ -v · τ_int / 2`**；**`= apparent_peak_lag_counts / point_step_counts`**，`∈ [0.3, 0.7]` 是 R-42d 的半窗特征 |
| `lock_track_noise_ratio` | 锁定后功率相对标准差 ÷ 扫描期功率相对标准差；`> 1.5` ⇒ 锁峰在追噪声（`δx_eq = σ_noise/\|dP/dx\|`，峰附近发散） |

**A5–A7（一扫描/一批次一条）**

| 组 · 字段 | 口径 |
|---|---|
| A5 · `expected_point_count` `actual_point_count` `truncated_flag` `truncation_reason` `tail_gap_ms` `host_pause_during_scan` `event_overlap_sources[]` | R-41 数据完整性；`expected_point_count` 的权威出处是 `scan_program.segments[].n_points_expected`（**不得由实际点数反填**）；`event_overlap_sources[]` 只能取 C6 `source` 词表值 |
| A5 · `edge_slope_ratio` | **= 窗口边缘斜率 ÷ 峰侧最大斜率**，无量纲 ⇒ 缺定标系数也可判（R-41c ≥ 0.5） |
| A6 · `power_timestamp_source` `write_back_delay_ms` `vel_at_write_back_counts_s` `stale_coord_mismatch_counts` | `vel_at_write_back_counts_s > 0` 即"回写发生在运动中"；**`stale_coord_mismatch_counts` = 锁存位置与积分窗中心位置之差**（KB6 §A.1.3-2） |
| A7 · `residual_period_counts` `residual_period_ratio_to_per_rev` `residual_amplitude_counts` `amplitude_ratio_vs_encoder_per_rev` `agrees_with_second_sensor` | 比值 `∈ {1, 1/2, 1/3}` 才属每转族（R-40a）；**`amplitude_ratio_vs_encoder_per_rev = residual_amplitude_counts / encoder.per_rev_amplitude_counts`**；无第二传感器 ⇒ `null`，**不得填 `true`** |

### 2.3 复用而非重定义（硬约束）
| C7 需要 | 必须引用的既有路径 | 禁止 |
|---|---|---|
| 视觉延迟 / 对齐残差 / 因果开关（A6 侧） | C2 `event_context.{vision_result_latency_p95_ms, alignment_residual_ms, causal_claims_permitted}` + `event_context.sync.{method, verified, uncertainty_ms}`（C6 §3） | 在 C7 复制同义字段或再造布尔 |
| 编码器周期误差交叉比值（A7 侧） | C2 `encoder.{phase_locked_to_pos_modulo, detrended_r2, per_rev_periodic_present, per_rev_amplitude_counts}` | 重定义 R² 或相位锁定 |
| 稳定时间 / 保持带宽 / 间隙 / 反向失动 / 摩擦比 / 爬行 / 共振 / 纹波 / 温漂 / 环带宽 | C2 `step_response[].{settling_time_ms, settle_band_counts, limit_cycle_present}`、`global.{backlash_estimate_counts, reversal_error_counts, friction_stiction_ratio, thermal_drift_counts_per_min, thermal_fe_correlation_r}`、`crawling.*`、`ripple.probing[]`、`resonance.candidates[]`、`bandwidth.*`、`freq_limits.*` | 在 C7 再造一份 |
| 时基抖动 / 量化步长 / 样本数 / 分段 / `settled` 位 / 定标系数 | C1 `quality.*`、`segments`、`meta.counts_per_mm`、`meta.io_bits` | 把 C1 门禁字段写进 `supporting_evidence[].feature`（KB6 §0.3-2） |
| 扫描运动速度 | C1 `vel_fb`，或 `pos_fb` 差分（须带 `channels.vel_fb.derived`，置信度 ×0.7，C1 派生规则 4） | 自设微分/平滑口径 |

去重同 KB6 §C.4：`light_curve.*` 与被复用 C2 组表达同一现象时只允许一条主证据，另一条转
`contradicting_evidence` 或注记；C7 内部 `power_channel.*` 与 `light_curve.*` **不算两个独立特征组**。

## 3. 采样率—运动带宽门禁（本契约的核心纪律）

### 3.1 必填元数据
`power_channel.{sample_rate_hz, integration_time_ms, poll_period_ms, timestamp_source, dt_jitter_ratio}`
五项**全部必填非 null**。任一缺失使"曲线上的一点代表什么"无法界定 ⇒ A 组按 §1.2-1 同等登记
`not_evaluable`，**不得**输出"未见采样伪影"。

### 3.2 `ratio_to_servo_fs` 分档：它决定"一点是 1 个位置还是几千个位置的平均"
| `ratio_to_servo_fs` | 含义（`servo_fs` = 8 kHz） | 允许的声明 |
|---|---|---|
| `< 10` | 与伺服同时钟（`analog_daq`） | A 组全部曲线形态判据可评估；多数 `software_induced_*` 分支结构性不成立 ⇒ `skipped` |
| `10–100` | 百 Hz 级 | 曲线形态可评估，但 `integration_time_ms`、`dt_jitter_ratio` 必须非 null |
| `100–1000` | 1–10 Hz 串口轮询（最常见） | **单扫描峰形判据（`fwhm_counts` / `asymmetry_ratio` / `gaussian_fit_r2`）仅当 §3.3 全通过才可评估**，否则只允许 A3 跨扫描统计 |
| `> 1000` | < 8 Hz，含亚 Hz / GPIB | 单扫描峰形判据**一律拒收**；只允许 `peak_power` 标量趋势与 R-37 门禁侧 |

界值 10 / 100 / 1000 为**本项目自定（`[P]`，仿 KB3 §3.2 口径），必须在 T1/T2 数据上重标定**；工艺侧没有
可重标定的 T1 ⇒ 重标定只在 T3 合成集上做，结果**不得**外推为现场精度（§9）。分档的定性依据是 KB6
§A.1.2 的仪器速率类别（`T2`，仪器手册档位）。

### 3.3 空间分辨率拒收红线
任一成立 ⇒ 该扫描上**一切"功率峰位/峰宽在某 counts 处"的空间分辨率声明必须被拒**，并必须在顶层
`blocked_claims[]` 自陈（见 §2.1）+ `audit.rules_skipped` + `differential.not_evaluable`——报告不得只写结论、不写被拒的声明：

1. `fwhm_counts < 3 × point_step_counts`（等价 `step_over_fwhm_ratio > 1/3`）：FWHM 由不足 3 个栅格点测得，
   是外推不是测量。以 `× fwhm_counts` 归一的子条件（R-31d/32c/33a/34b/35c/37b/40b/42c）随之全部失效。
2. `peak_never_sampled_flag == true`：峰从未被真正采到，任何峰位声明都是虚构。
3. 判据阈值的绝对量小于栅格分辨率 ⇒ **判据分辨率下界 = `max(point_step_counts, 2 × v_sweep × τ_int)`**
   （右项是积分窗内的空间涂抹量）；低于下界的比较**不启用**，不得"照判但降置信度"。本节门禁量
   （`ratio_to_servo_fs`、`step_over_fwhm_ratio`、`fwhm/point_step` 界）**全部无量纲** ⇒ 缺 `counts_per_mm`
   时依然生效（KB6 §0.3-1）；µW/dBm/µm 量纲阈值在单位或定标缺失时不启用。
4. `edge_slope_ratio >= 0.5` 或 `peak_index` 落在首末 3 点 ⇒ 峰是窗口边缘（R-41），先按数据完整性处理。
5. 可辩护界（与 `scan_program` 交叉校验用）：`point_step_counts <= 0.1 × fwhm_counts`，来自单模高斯耦合的
   几何推导 `ΔP/P₀ = 1 - exp(-2(step/2)²/w²)`、`FWHM = 2√(2 ln 2)·w ≈ 1.1774·w`（`0.1` ⇒ ≈1.4% 损失、
   `0.2` ⇒ 5.4% 边缘、`0.5` ⇒ 30% 不可接受）；推导自足可复算，tier = `T2`。
6. C7 不新增 `R-NN`（§8）；本节条款引用形式 `C7-§3.3-1`。

### 3.4 频带纪律（继承 C2 规则 7，不得弱化）
1. 功率域频率声明必须 `< power_channel.reliable_band_hz`，否则进 `unavailable` 并列入
   `freq_limits.blocked_rules`，**不得**输出"没有噪声""噪声底正常"。
2. `noise_dominant_freq_hz` 仅 `sample_rate_hz >= 20` 时允许非 null；`< 20` 时只报本底**相对量级**并标
   `[ratio]`（R-36 适用边界）。
3. **混叠折叠禁止**：伺服侧 kHz 级谐振在低频功率栅格上必然折叠成"慢速功率波动"，把折叠分量说成
   "找到低频共振"是结构性错误；R-36e 的同频比较仅当
   `power_channel.sample_rate_hz >= 2 × resonance.candidates[].freq_hz` 时可评估，否则 `not_evaluable`。
4. `meta.quality.dt_jitter_ratio > 0.2` 时 C1 已整体拒绝诊断，C7 不得绕过；
   `power_channel.dt_jitter_ratio > 0.2` 时功率域频率类判据不启用。

## 4. `calibration.jsonl`

### 4.1 记录与路径映射（一行一记录）
```jsonl
{"record_type":"session","cal_id":"CAL-2026-0411-2","kind":"nine_point_grid","n_points":9,"layout":"3x3","axis_group":"XYθ","recipe":"AuSn_280C_die4","step":"place","machine_temp_c":26.4,"fixture_id":"FX-07","plate_grade":"class_B","operator":"lz","timestamp_s":1842.310,"residual_vectors_counts_npy":"features/process/calibration_sessions_0_vectors.npy","residual_vectors_counts":[[-12.4,3.1],[8.9,-2.2]],"mean_residual_counts":{"mx":-1.8,"my":0.7,"mag":1.9,"dir_deg":159.0},"rms_residual_counts":14.6,"systematic_share_pct":13.0,"isotropic_ratio":1.4,"residual_rms_first_half_counts":9.1,"residual_rms_second_half_counts":17.8,"radial_slope_ratio":0.0081,"tangential_mean_ratio":0.0012,"radial_sign_pattern":[2.1,1.9,-1.8,-2.3,1.7,-1.6,2.0,-1.9,1.8],"tangential_sign_pattern":null,"split_shift_counts":8.7,"split_p_value":0.031,"split_ci_counts":[1.4,16.0],"trend_slope_counts_per_index":1.12,"trend_p_value":0.02,"spearman_rho":0.78,"oos_point_ratio":0.111,"direction_pair_diff_counts":{"u_pos":11.2,"u_neg":10.8,"d_pos":12.0,"d_neg":9.9},"field_pattern":{"dominant_pattern":"linear_gradient","linear_fit_r2":0.71,"low_order_coefficients":{"k11":0.0081,"k12":-0.0012,"k21":0.0009,"k22":0.0078,"tx":-1.8,"ty":0.7},"morans_i":0.42,"quadrant_sign_consistency":0.78},"spec":{"rms_counts":20.0,"max_counts":35.0,"source":"设备验收标准 WA-117 附录 C","version":"2025-09"}}
{"record_type":"series","n_sessions":2,"rms_cv_pct":18.4,"oos_ratio":0.06,"worst_subgroup_share_pct":22.0,"slow_tail_ratio":1.31,"chart_type":"I-MR","subgroup_size":1,"control_limits":[{"segment_id":0,"mean_counts":14.6,"sigma_counts":2.7,"ucl_counts":22.7,"lcl_counts":6.5,"n":9}],"violation_rules_fired":["1"],"segment_break_points":[{"t":1842.310,"reason":"recalibration","evidence":"cal_id CAL-2026-0411-2"}],"violations_before_resegmentation":4,"violations_after_resegmentation":0,"correlation_screen":{"with_temp_r":0.74,"with_temp_ci":[0.31,0.96],"with_fixture_batch":{"groups":["FX-07","FX-09"],"welch_p":0.04,"effect_over_rms":1.2},"with_plate_grade":null,"with_operator":null,"with_time_since_last_cal_r":0.41}}
```

1. `record_type == "session"` 一行 = 一个标定批次 ⇒ **C3 引用写作 `calibration.sessions[].*`**，
   数组下标按 `timestamp_s` **升序**重排（不是文件顺序）；`calibration.field_pattern`（B2）是同名行内对象。
2. `calibration.series`（B3）与 `calibration.correlation_screen`（B5）是跨批次累计量 ⇒ 由**唯一一条**
   `record_type == "series"` 行承载；其 `n_sessions` 必须等于 session 行数，不等即拒绝整份文件。
   **为什么不搬进 `process.json`**（裁决 A-37）：series 的生命周期跨批次，而 `process.json` 与单次
   waveform 同生死；把跨批次统计塞进单样本文件，等于给"这个结论可复现到这一次测量"制造假象。
3. `calibration.spec`（B4）为批次级外部输入，允许每行回显，但全文件取值必须一致；不一致 ⇒ R-49
   `skipped` 并登记"验收限版本冲突"。
4. `calibration.field_pattern`（B2）**每批次一份**（裁决 A-39：**段 = 批次**）。任何"分段后比较"的判据
   （如 KB6 R-44b）一律引用 `calibration.series` 的分段统计字段，禁止在单个 `field_pattern` 对象上再切段；
   "按 recipe 切"与"按时间半段切"只是批次的两种归组方式，不是新的实体。

### 4.2 B 组逐字段口径（标定侧特征索引；语义源自 KB6 §B.1.2 / §B.3 / §B.4，权威载体为 C7，见 A-36/A-40）
| 字段 | 口径 / 派生式 |
|---|---|
| `cal_id` `kind` `n_points` `layout` `axis_group` `recipe` `step` `machine_temp_c` `fixture_id` `plate_grade` `operator` `timestamp_s` | 批次元数据。`step`/`recipe` 必须与 C6 `machine_context` 同源；`timestamp_s` 用 C1 时间基准；`plate_grade` 粗于工艺要求 ⇒ 禁止把残差归因于系数（R-45 排除项） |
| `residual_vectors_counts[]` `residual_vectors_counts_npy` | **必须记录矢量场**（每点 `(dx,dy)`）；只存标量 RMS 即毁掉方向信息（§B.1.2）。JSON 存降采样版，全量走 `.npy` |
| `mean_residual_counts{mx,my,mag,dir_deg}` `rms_residual_counts` | `mag = ‖mean(dx,dy)‖`、`dir_deg` 主方向（R-46a/d）；RMS 单位 counts，缺 `counts_per_mm` 禁 µm |
| `systematic_share_pct` `isotropic_ratio` | **`= ‖mean(dx,dy)‖ / rms_residual × 100`**（把"偏"与"散"分开，R-45d/46b）；**`= σ_major / σ_minor`**（R-46c），`n_points < 12` 时不稳 ⇒ `skipped` |
| `residual_rms_first_half_counts` `residual_rms_second_half_counts` | 比值是 R-43d / R-47a 的量；**R-47 的"两组"定义 = 配方边界，不是时间中点** |
| `radial_slope_ratio` `tangential_mean_ratio` `radial_sign_pattern` `tangential_sign_pattern` | 前两者为**无量纲**尺度 / 角度误差 ⇒ 缺定标系数仍可判（R-45a/c），但报告禁 µm；符号序全同号 ⇔ 尺度问题而非局部缺陷，异号 ⇔ 高阶畸变候选（无 slug，只记 `considered`） |
| `split_shift_counts` `split_p_value` `split_ci_counts` `trend_slope_counts_per_index` `trend_p_value` `spearman_rho` | 分组均值差 + Welch t + CI（R-44a，**只看"均值变大"不合法**）；趋势三元组（R-43c）——效应量与显著性必须同时出现（KB6 §0.3-3） |
| `oos_point_ratio` `direction_pair_diff_counts{u_pos,u_neg,d_pos,d_neg}` | 超差点占比（R-49c，需 `spec` 非 null）；单向/反向趋近成对差（R-32/R-39 的标定侧对应物） |
| `field_pattern.{dominant_pattern, linear_fit_r2, low_order_coefficients, morans_i, quadrant_sign_consistency}` | `dominant_pattern ∈ {random, linear_gradient, step, radial, tangential, mixed}`；**`linear_fit_r2 = 1 - ‖残差 − 低阶拟合‖² / ‖残差‖²`**；系数 `{k11,k12,k21,k22,tx,ty}` 只用于**形态分类**，不反解标定系数、不生成补偿（§1.3）；`morans_i` 为网格最近邻空间自相关（`≈ 0` ⇔ 随机散布） |
| `series.{n_sessions, rms_cv_pct, oos_ratio, worst_subgroup_share_pct, slow_tail_ratio}` | **`CV = σ/μ`（无量纲）**；**`slow_tail_ratio` = 最差 10% 子组均值 ÷ 全体均值**（右尾 / 稀释免疫）；`n_sessions < 8` ⇒ B 组统计判据上限 0.5 |
| `series.{chart_type, subgroup_size, control_limits[]}` | 图型选择规则（§B.4，可判定）：`n_points >= 9` 且网格间距 >> 残差 ⇒ `Xbar-R`，否则 `I-MR`（`σ_within = MR̄/d2`）；**控制限按段独立重算**，禁用换型前的限卡换型后的点 |
| `series.violation_rules_fired[]` | 只取 Western Electric 前 3 条（`1` 超 3σ、`2` 连续 9 点同侧、`3` 连续 6 点单调）；第 4 条以后在 `n_sessions < 30` 假阳率过高，**明确不用** |
| `series.{segment_break_points[], violations_before_resegmentation, violations_after_resegmentation}` | 断点 `{t, reason ∈ {recipe_change, recalibration, fixture_change, operator_change}, evidence}`，报告必须打印断点与每段 n；前 `> 0` ∧ 后 `== 0` ⇒ 唯一正确结论是"分段错误造成的假失控"（R-50b/c） |
| `spec.{rms_counts, max_counts, source, version}` | 外部验收限；单位**必须已折算成 counts**；`null` ⇒ R-49 `skipped` |
| `correlation_screen.{with_temp_r, with_fixture_batch, with_plate_grade, with_operator, with_time_since_last_cal_r}` | 相关系数 **+ CI**（R-48a）；分组差异 = Welch t ∧ 效应量 `>= 1 × rms`；**本组不新增任何因果布尔**（开关只复用 `event_context.causal_claims_permitted`） |

### 4.3 `sync` 与因果开关：继承 C6，不得弱化
1. `calibration.jsonl` **不定义自己的 `sync`**。因果开关唯一来源是 C2 `event_context.causal_claims_permitted`（条件 `sync.verified == true` ∧ `alignment_residual_ms ≤ sync.uncertainty_ms`，C2 规则 8 / C6 §3 硬规则 2；方向由 **A-82** 锁定，旧文本此处写 `|Δt| > sync.uncertainty_ms` 是把"残差要小"与"被声称的差值要大"混成了一个不等号）。
2. `events.jsonl` 缺失、或 `sync.verified == false`、或 `sync.method == "unknown"` 时：**R-47（换型后残差突变）与 R-48（残差与温度/工装/操作者相关）只能报共现与相关，不得报因果**，不得把 cause 写入 `hypotheses[]`；固定措辞"相关性已量化，因果未确立"。标定记录若无 `event_context`，因果开关**默认取 `false`**（KB6 R-48 必要上下文 / M-3）。
3. 两个方向分开用（**A-82**，与 C6 硬规则 2 同调）：批次—事件对齐的**残差**若 `alignment_residual_ms > sync.uncertainty_ms`，
   说明两个钟还有没被建模的偏差，该对齐不得作为因果证据（只报共现）；而**被声称的时序差**
   （换型事件与该批首件采集时刻之间的间隔，由 `step_labels` 与标定记录时间戳相减得到）若 `≤ sync.uncertainty_ms`，
   在时基上根本分辨不出来，同样不得作证据。
   `uncertainty_ms` 缺失按 5 ms 保守取值并记 `audit.assumptions`（C6 硬规则 3）。
4. 温度序列与标定时间戳**必须同源**；异源时 `with_temp_r` 只作共现，该假设须写进 `audit.assumptions`。

### 4.4 `spec` 缺失与单位纪律（硬性）
1. `calibration.spec == null` ⇒ **R-49 必须 `skipped`**，理由"无外部验收限"。**禁止**用内部统计限（`3σ`、p95、历史最好值）冒充客户限后宣称"超标/合格"——那是把"较大"偷换成"超规"；此时只允许 B 组形态类判据（R-43…R-46、R-48）。
2. `meta.counts_per_mm == null` ⇒ 残差、斜率、限值一律报 **counts 或像素**，报告印 `[counts]`，**禁止 µm**（C1 单位红线 / KB0 §5）。`spec` 只有 µm 而未折算 ⇒ R-49 **结构性不可评估**，报告须写"缺定标系数，验收限无法应用"，不得偷偷换算。
3. 尺度类结论优先走无量纲形式（`radial_slope_ratio`、`tangential_mean_ratio`、`systematic_share_pct`、`CV`、`slow_tail_ratio` 缺定标系数时依然可用）——这是本组的设计要点。
4. `oos_ratio` 只是良率损失的**上界型代理**，禁止给出与良率的任何定量换算（§B.4）。

## 5. `scan_program`：寻光扫描参数声明（回应 KB6 M-2）

```json
{
"scan_program": {
  "units": {"distance": "counts", "angle": "deg", "time": "ms"},
  "source": "exported_from_motion_program", "confidence": 0.95,
  "segments": [
    {"segment_id": 7, "kind": "scanning", "scan_type": "spiral", "step_counts": 640.0, "pitch_counts": 800.0, "dwell_ms": null, "n_points_expected": 121, "raster_line_count": null, "feedrate_counts_s": 5120.0},
    {"segment_id": 8, "kind": "dwell", "scan_type": "hill_climb", "step_counts": 220.0, "pitch_counts": null, "dwell_ms": 95.0, "n_points_expected": 40, "raster_line_count": null, "feedrate_counts_s": null},
    {"segment_id": 9, "kind": "dwell", "scan_type": "peak_hold", "step_counts": null, "pitch_counts": null, "dwell_ms": 300.0, "n_points_expected": null, "raster_line_count": null, "feedrate_counts_s": null, "dither_freq_hz": null, "dither_amplitude_counts": null}
  ]
}
}
```

| 字段 | 口径 |
|---|---|
| `segments[].segment_id` `kind` | `kind` **只能取 C1 `segments.kind` 词表**（`scanning`/`probing`/`dwell`/`settling`/`curing`），C7 不新增 kind（KB6 §A.1.1：避免把 C1 分段撑成第二套状态机） |
| `segments[].scan_type` | `spiral` \| `raster` \| `hill_climb` \| `peak_hold`——轨迹**模式**属参数而非运动语境，故在此声明 |
| `step_counts` `pitch_counts` `raster_line_count` `feedrate_counts_s` | 相邻测量点位移 / 螺旋螺距 / 光栅线距（counts）/ 恒速扫进给速度（`probing` 段必填，`step_over_fwhm_ratio` 分母来源）；`probing` 时 `step_counts = feedrate_counts_s / 读数速率` |
| `dwell_ms` `n_points_expected` `dither_freq_hz` `dither_amplitude_counts` | 驻留窗长（与 `integration_time_ms` 一起决定 M-b/M-c）/ R-41a `expected_point_count` 的**权威出处** / 陷阱 4 输入（`peak_hold` 段缺后两项时 dither 混淆分支不启用） |
| `units` | 声明域单位；`distance` 恒为 counts（填 mm 而 `counts_per_mm == null` ⇒ 整块视为不可用） |
| `source` `confidence` | `exported_from_motion_program`（典型 0.9–1.0）\| `operator_entered`（≤ 0.7）\| `inferred_from_waveform`（见硬规则 2 的循环论证封顶） |

**硬性约定**

1. `scan_program` 是 KB6 §A.3 的 `step/FWHM` 与 `required_settle_ms` 的**唯一权威步长出处**；M-2 由此闭合
   （裁决：放 C7，不放 C6 `machine_context`）。依赖步长的判据在缺对应段时**不启用**并进 `not_evaluable`。
2. **`source == "inferred_from_waveform"` 时，所有依赖步长的判据 `confidence` 封顶 0.40**（与 KB6 §C.3 表
   逐条取最小值，不连乘），并在 `audit.assumptions` 打印原因。理由：用波形反推的步长去验证同一条波形的峰形
   是**循环论证**——防自验证纪律（C5 §0/§2、KB6 §A.4.2）明令禁止证据与结论同源；此类子条件须在
   `supporting_evidence[]` 标 `circular: true`，且**不计入 `audit.rules_fired`** 的主证据。
   **本条是 A-88 的特例**（KB0 §7.3）：不限于"步长来自波形"，凡**核对物与其被核对的来源同源**（同一份规则库、
   同一份 `scan_program` 推断结果、同一份生成器知识库）一律零证明力；`source_independence` 与外部输入槽位
   的通用口径见 KB0 §6 检查 20、KB3 §0 纪律 16，本文件的 0.40 封顶值不因一般化而改动。
3. `source == "operator_entered"` ⇒ 同一判据上限 0.55，且 `next_data_to_collect` 必须请求运动程序导出。
4. 声明步长与实测位移必须交叉校验：`abs(step_counts − light_curve.scans[].point_step_counts) /
   point_step_counts > 0.2`（本项目自定 `[P]`）⇒ 先质疑**分段质量或采样元数据**（KB6 §C.2 双向原则），把
   "分段可疑"作为发现上报，不得强行套 A 组判据，也不得静默降级。
5. `light_curve.scans[].scan_kind` 与 `scan_program.segments[].scan_type` 不一致时以 `scan_program` 为准并登记冲突。

## 6. `cycle_stats`：节拍/良率统计的归属（回应 KB6 M-6）

裁决：节拍统计**不进 C2**（C2 只做波形特征，通用内核不因工艺外壳长字段），归 C7 `cycle_stats`，
并与 `calibration.series` 一样按换型/重标定点**强制分段**。

```json
{
"cycle_stats": {
  "available": true, "cycle_source": "event_pair", "units": "ms", "ref_cycle_time_ms": 1800.0,
  "n_cycles": 412, "n_by_step": {"pick_up": 200, "place": 198, "verify": 14},
  "cycle_time_median_ms": 1810.0, "cycle_time_p95_ms": 2605.0, "cv_pct": 12.4,
  "slow_tail_ratio": 1.9, "slow_cycle_share_pct": 3.1, "grouping_keys": ["step", "recipe", "operator"],
  "segments": [{"id": 0, "t0": 0.0, "t1": 355.6, "n": 200, "median_ms": 1780.0, "cv_pct": 5.1, "chart_type": "I-MR", "subgroup_size": 1, "violations": 0, "control_limits": {"mean_ms": 1780.0, "sigma_ms": 91.0, "ucl_ms": 2053.0, "lcl_ms": 1507.0}}],
  "segment_break_points": [{"t": 355.6, "reason": "recipe_change", "evidence": "event_context.step_labels[3].recipe"}, {"t": 612.4, "reason": "recalibration", "evidence": "calibration.sessions[4].timestamp_s"}],
  "violations_before_resegmentation": 7, "violations_after_resegmentation": 1
}
}
```

| 字段 | 口径 |
|---|---|
| `available` `cycle_source` | `false` 时其余全 `null`。`cycle_source ∈ {event_pair, segment_edges, host_log}`：优先 C6 事件对 `motion.move_started → move_done`；退化为 `segment_edges` 时 `confidence` 封顶 **0.5**（分段本身可能错标，与 §5 硬规则 2 的同源风险同级） |
| `n_cycles` `n_by_step` `ref_cycle_time_ms` `grouping_keys[]` | `ref_cycle_time_ms` 为外部标称节拍（`T2`/客户文档），`null` ⇒ 禁说"节拍超差"，只报相对量；分组键至少含 `step` + `recipe`（"按工况分组"设计模式；KB6 §1 关于 `cycle_jitter`：C2 无该字段，只借设计模式，不引用不存在路径） |
| `cycle_time_median_ms` `cycle_time_p95_ms` `cv_pct` | `CV = σ/μ`；节拍是**快过程变量**（一循环一点，n 上万），分位数在此才有意义——与 `residual_rms`（**慢过程变量**，一次标定一点）严格区分（§B.3） |
| `slow_tail_ratio` `slow_cycle_share_pct` | **右尾与占比才是节拍变慢的真信号**：`slow_cycle_share_pct` = 最差 10% 循环占比，`slow_tail_ratio` = 最差 10% 子组均值 ÷ 全体均值；3% 的慢循环被全程平均摊成 0.3% 的均值差 ⇒ 看不出，故平均值**不得**作为唯一结论 |
| `segments[]` `segment_break_points[]` `violations_before/after_resegmentation` | 与 `calibration.series` 同构：控制限必须由同段数据算出、报告打印断点与每段 n；前 `> 0` ∧ 后 `== 0` ⇒ 唯一合法结论是"分段错误造成的假失控"，不是设备失控 |

**硬性约定**

1. **未分段的最坏情况是必须登记的诊断缺陷，不是通过。** 若序列内存在可证的 recipe 变更
   （`event_context.step_labels[]`）或重标定点（`calibration.sessions[].timestamp_s`），而
   `cycle_stats.segment_break_points[]`（或 `calibration.series.segment_break_points[]`）为空，则 C3 必须：
   `audit.rules_skipped` 登记 R-50 与节拍类判据（理由 `"unsegmented series (C7-§6-1)"`）、
   `differential.not_evaluable` 逐条写明"统计分段缺失"、并把该项写进 `verdict.summary` 的"分析纪律"段。
   **禁止**在此情形下输出"节拍受控""无慢拍异常"。
2. 慢变量禁用心跳分位数阈值：`residual_rms` 类（每配方每天一两个点）只能用分组均值 + CI + 分段控制图，**不得**用 p95/p99 卡它（KB6 §B.3 明文）。
3. 节拍类建议的动作只允许 `change_measurement_procedure` / `schedule_verification` / `request_data`；`expected_effect.basis` 恒为 `unverified` 或 `rule_heuristic`，**禁止**"节拍缩短 X%"的数字。
4. `n_cycles < 30` ⇒ 控制限不稳，本节判据 `skipped` 并登记，不得说"过程受控"（R-50 边界同）。

## 7. 与 KB0 命名空间的对齐

### 7.1 登记请求清单（**已裁**：A-34 把 KB0 §3 排他句改为"C2 或已登记的 C7 路径"；本清单即 C7 侧登记表，不再请求并入 C2）
| # | 路径前缀 | 权威载体 | 备注 |
|---|---|---|---|
| 1–7 | `power_channel.*`；`light_curve.{scans[], series_stats, motion_sampling_conflict, scan_integrity, vision_write_back, encoder_masquerade}.*` | `process.json` | KB6 §G-3 的 A1–A7，原样沿用（含 `ratio_to_servo_fs`、`required_settle_ms`、`apparent_peak_lag_over_step_ratio`、`stale_coord_mismatch_counts`、`edge_slope_ratio` 等派生式） |
| 8–12 | `calibration.{sessions[], field_pattern, series, spec, correlation_screen}.*` | `calibration.jsonl` | KB6 §G-3 的 B1–B5；`calibration.spec.*` 是**门禁字段，禁入 `supporting_evidence[]`**（KB6 §0.3-2） |
| 13–14 | `scan_program.*`、`cycle_stats.*` | `process.json` | **C7 新增**（§G-3 未登记） |
| 15 | `blocked_claims[]`、`unavailable[]`（顶层）、`ref.*`、`*_npy`、`t0/t1`、`reliable_band_hz`、`align_residual_ms`、`nan_ratio` | `process.json` | 结构性 / 自陈字段：不承载判据语义，但须登记以免拼写漂移 |

**未登记路径引用即无效**：加载期解析不到 ⇒ 规则状态 `blocked`（理由文本
`"feature path not registered in C2 or C7 (C7-NEW)"`）⇒ 逐条 `audit.rules_skipped` ⇒ 对应 fault_mode 写进
`differential.not_evaluable`。这与 `freq_limits.blocked_rules` 同构：结构性缺失必须显式登记，不能伪装成
"没发现问题"。每条假设仍需 C3 硬规则 1 的 ≥2 条证据且来自**不同特征组**（`light_curve.*` + `global.*`，
或 `calibration.*` + `event_context.*`）：C7 与 C2 算不同组，C7 内部 `power_channel.*` 与 `light_curve.*` 不算两族。

### 7.2 C7 不新增 cause slug（措辞从硬）
1. **C7 不新增任何 cause slug**；KB0 §2 的三族（`mechanical_*` / `electrical_*` / `software_induced_*`）是唯一合法集合。
2. **KB6 §G-1 请求的 8 个候选一律不予采纳**：`optical_mode_mismatch`、`optical_device_degradation`、
   `optical_polarization_mode_split`、`process_workpiece_occlusion`、`calibration_model_unmodeled_distortion`、
   `mechanical_axis_straightness_error`、`mechanical_pitch_yaw_wobble`、`calibration_fixture_repeatability`。
   **理由（写死在此）**：本项目无耦合产线数据、无光学真值、无工装批次的独立标签来源；采纳这些族名等于允许
   agent 用**没有证据支撑的家族名**下结论——slug 一旦存在就会被填，填了就在报告里长得像真归因，而它的证据
   tier 只有 T2 方向性 + T3 合成。这不是"覆盖面小一点"，这正是本项目最不能犯的那类错（C5 §0、AUDIT §二）。
3. 采纳差额必须**明示、不得吸收**：已用自然语言写的现象进 `differential.considered`（R-32 "偏振/双模劈裂候选"、
   R-35 "像散/倾斜入射候选"、R-38 "工件遮挡候选"、R-40 "丝杠周期误差候选"）；因缺 slug 而无归因出口的逐条进
   `differential.not_evaluable`，文本形如 `"直线性/俯仰偏摆：无可用 cause slug（KB6 G-1 未采纳）"`。
   `ruled_out_alternatives[].cause` 允许非 slug 自然语言（它表达"排除了什么"，不是"下结论"）。
4. **禁止用近似 slug 顶包**：光学解释写 `mechanical_thermal_drift`、工装重复性写 `mechanical_loose_structure`、
   模场失配写 `electrical_*` —— 一律按**归因造假**处理，出现一次即与 C5 "无依据成功声明"同级失败。
   宁缺（`not_evaluable`）勿假。
5. `verdict.primary` 不得指向只有 `considered` 支撑的假设；若 A/B 组结论全部退化为 `considered`/`not_evaluable`，
   正确输出是 `actionable: false` + `next_data_to_collect` 非空（C3 硬规则 5）。

## 8. 规则编号保留与门禁规则类

1. **`R-51+` 继续保留给 KB6 / 后续工艺规则。** KB6 已用至 R-50（A 组 R-31…R-42，B 组 R-43…R-50）；**本文件不占用任何 `R-NN`**，条款以 `C7-§<节>-<序>` 引用，以免侵占保留段。KB0 §1 的"R-01…R-30 归 KB3、R-31+ 归 KB6"分工不变。
2. **门禁/拒答规则（`family: null`）合法**——采纳 KB6 §G-2 诉求，本契约引用该约定：R-37（只有峰降、形位俱稳 ⇒
   禁止运动归因）、R-49（残差超外部限 ⇒ 拒收/复标）、R-50（SPC 必须分段）三条**无 cause**，其输出是：
   ① `audit.rules_fired` 记规则号（门禁被触发是事实，须可统计）；② `differential` 侧登记义务（`not_evaluable`
   写明"缺什么才能下结论"、`considered` 写自然语言候选）；③ **永不产生 `hypotheses[]` 条目**，
   `overall_confidence <= 0.45`、`actionable: false`，动作只允许 `rerun_step` / `request_data` /
   `schedule_verification`（KB6 §C.3 第 9 行）；④ 计入 C5 的**拒答正确率**指标（`none_of_the_above` 配额 ≥15%，
   C5 §2），三条各至少一个案例，agent 编出机械原因就是错。
   KB0 §6 检查 2（"`cause` 必须在 §2 表内"）需据此放宽为"在表内 **或** 标注 `family: null` 的门禁类"；C3/KB4
   需给出该类的形式定义（本文件只声明引用，不代 C3/KB4 定义）。
3. `ref_scan_ids` 为空、`spec` 为 null、`scan_program` 缺失、`events.jsonl` 缺失这四类"结构性不可评估"必须与
   门禁触发**分开呈现**：前者是覆盖度问题（可补数据），后者是结论边界问题（正确拒答）。

## 9. tier 纪律与禁用表述

1. 本契约阈值 tier 只有 **`T2`**（文献/仪器手册类别）与 **`T3`**（本项目合成，仅证明管线跑通）。`T1-a`（DaRUS）
   **不含 `laser_power`、不含耦合工序、不含标定网格**，只支撑三类子事实（爬行/stiction 可判 R-39；多传感器
   不一致与编码器每转周期误差可量化并复刻为"伪装" R-40；驻留残余振动与纹波可量化 R-36 机械侧形态），
   边界权威在 KB6 §A.4.1，本文件不重述。
2. 本文件全部 `[P]`（本项目自定）数值：`ratio_to_servo_fs` 分档界 10/100/1000、`fwhm < 3 × point_step`、步长
   交叉校验 0.2、`inferred_from_waveform` 上限 0.40、`operator_entered` 上限 0.55、`segment_edges` 上限 0.5、
   `n_cycles < 30`。**均须按 KB3 §3.2 的统一协议在 T1/T2 上重标定**；工艺侧无可重标定的 T1 ⇒ 只在 T3 合成集上
   做（参数空间与阈值不共享常数，KB6 §A.4.2），结果**只允许**表述为"判据按构造检出植入误差、且在对抗案例上
   正确拒答"，**不得**表述为诊断准确（C5 §1 硬规则）。
3. **禁用表述**（文档、报告、作品集、答辩一处都不许）："在客户产线验证"、"现场诊断案例"、"现场/产线验证通过"、
   "耦合良率提升 X%"、"真实光功率数据"、"与厂商工程师确认"。允许的最强表述："判据阈值取自文献并给出推导；
   可检验性在合成数据上演示；机械/电气侧子事实用公开真实数据集交叉验证。"
4. `expected_effect.basis` 在 C7 侧只能是 `rule_heuristic` 或 `unverified`（C4 的被控对象 KB5 不含光学耦合效率
   曲面）；唯一允许 `simulation_validated` 的是伺服参数类建议，且 `caveats` 必须写"仿真不含光学耦合效率模型，
   峰功率改进量未经验证"（KB6 §C.5）。

## §X 冲突清单与裁决回写（**11 条已全部裁决**，原文保留供读者看"契约是怎么互相撞到的"）

> 本文件不修改、不评价任何其他契约的条文。以下是写 C7 时撞到的、需要主线程裁定的不一致；
> **状态以上表为准**，下方条目是原始描述（其中"需裁定/若更希望"等措辞均属历史原文，不再开放）。

**主线程裁决回写（2026-10-20，条目号对应下表）**：

| # | 裁决 | 状态 |
|---|---|---|
| 1 | A-29 + **A-44**：红线只对伺服栅格通道生效；C1 `quality` 新增可选 `nan_ratio_by_channel`，仅 `analog_daq`+`device` 的等间隔 `laser_power` 列进 `waveform.tsv` 时逐通道判 | 已裁，**C1 侧已改** |
| 2 | **A-36**：KB6 的"待并入 C2"机制作废，特征登记于 C7；`blocked` 消失，改走 §1.2 缺档纪律 + 强制 `not_evaluable` | 已裁，KB6 侧回写中（任务 #12） |
| 3 | **A-34**：判 KB0 错。§3 排他句已改为"C2 或已登记的 C7 路径"，工艺侧口径权威在 C7 §2.2/§4.2 | 已裁，**KB0 侧已改** |
| 4 | **A-35**：判 **KB6** 错。采样率档位门禁以本文件 §3.2 为唯一权威；"积分窗涂抹"归一为 §3.3-3 的无量纲下界 `max(point_step_counts, 2·v_sweep·τ_int)`，KB6 不得自设比值阈值 | 已裁，KB6 侧回写中 |
| 5 | C1 样本包结构已含 `process.json` / `calibration.jsonl`（数组旁路 `features/process/` 见本文件 §1.1） | **已闭环**，无需裁决 |
| 6 | **A-37**：维持"唯一一条 `record_type == "series"` 尾行"。理由：series 跨批次，搬进 `process.json` 会给单次 waveform 制造假的样本级可复现性 | 已裁，**本文件不改**（§4.1 补理由注） |
| 7 | **A-38**：`<domain>.<fit_name>_r2` 写进 **KB0 §3**（命名权威），不写进 C2——C2 不该为 C7 字段立法 | 已裁，**KB0 侧已改** |
| 8 | **A-39**：**段 = 批次**。每批次一份 `calibration.field_pattern`；按 recipe / 时间半段只是批次的两种归组，判据引用 `calibration.series` 的分段统计 | 已裁，KB6 侧回写中 |
| 9 | **A-40**：**不增设**"工艺特征索引"章节；本文件 §2.2/§4.2 的"口径"列即工艺侧索引，KB3 §1 加指针 | 已裁，KB3 侧回写中 |
| 10 | **A-41**：不给 C6 加 `motion_program`；C6 §2 已加指向句与"唯一权威载体"声明 | 已裁，**C6 侧已改** |
| 11 | **A-24**：采纳 **T1-c**「自采真实测量（非产线）」，**不新增 T0 词汇**。无自建工装 ⟹ 标定模块必须明说只有 T2+T3；禁止与 T1-a/T1-b 混算能力指标 | 已裁，**C5 侧已改**；本文件 §9 的 `T2+T3` 表述在拿到 T1-c 前保持 |

1. **C1 `laser_power` 行 vs C1 稀疏列红线**：C1 词表把它当 waveform.tsv 的等间隔列，而 1–20 Hz 轮询读数写进去会造成 >99% 空值，直接撞 C1 红线 `nan_ratio > 0.05` ⇒ 整体拒绝诊断。C7 的处理是"稀疏读数进 `process.json`，仅 `analog_daq`+`device` 同源时钟才进 waveform.tsv"，需 C1 加注口径，或把 `nan_ratio` 改为按通道分别计算。
2. **KB6 §1 / §C.1-1 / §C.1-2 / §C.3 第 2 行的"待并入 C2"机制失效**：改由 C7 承载后，"引用未并入 C2 的 KB6-NEW 路径 ⇒ `blocked`"须改写为"未登记于 C2 **或 C7**"；C7 落地后 blocked 应消失，改按 §1.2 缺档纪律。
3. **KB0 §3 的排他句**（"C2 里没有的路径不允许出现在规则证据里"）与本契约直接冲突，需改为"C2 或 KB0 已登记的 C7 路径"；KB0 §6 检查 1、检查 2 措辞同步。
4. **KB6 R-31b 的方向可疑**：`ratio_to_servo_fs < 20`（功率采样**最细**）触发"积分窗涂抹"，而适用边界说 `ratio_to_servo_fs >= 100`（采样**最粗**）时"结构性排除"，与 §3.2 的单调性（比值越大越不可分辨）相反。C7 未改写 KB6 判据，但 §3.3 红线会把 R-31 的可用区间收窄到与其边界冲突的位置——需裁定谁让谁。
5. **C1 样本包结构未含 C7 的两个文件**：需把 `process.json`、`calibration.jsonl`、`features/process/` 加入 C1 结构表，否则 KB5 合成样本规范与 KB0 §6 检查 4（合成样本必须能被 C1 loader 原样读入）不认识它们。
6. **`calibration.jsonl` 的 B3/B5 承载方式**：JSONL 一行一记录 与 "series / correlation_screen 是单个跨批次对象"天然冲突，C7 选了"唯一一条 `record_type == "series"` 尾行"。若更希望它们在 `process.json`（与 waveform 同生命周期），§4.1 的映射需改。
7. **R² 命名口径**：C2 `encoder.detrended_r2`、KB6 A2 `light_curve.scans[].gaussian_fit_r2`、B2 `calibration.field_pattern.linear_fit_r2`。KB6 §G-3 请求统一为 `<domain>.<fit_name>_r2`；C7 已按该形式落字段名，但"约定写进 C2 还是 KB0"未定。
8. **KB6 R-44b 需要分段后的 `linear_fit_r2`**（"两段内均 `< 0.3`"），而 §G-3 只把 `field_pattern` 登记为**单个对象**。C7 按每批次一份落地后，"段"（按 recipe / 时间半段）与"批次"的对应关系仍需 KB6 明确。
9. **C2 规则 4 的登记位置**："每个特征必须可追溯到公式或文献，登记在 KB3 特征索引表"——C7 工艺特征无 T1 真值，且 KB3 索引表只覆盖 C2。C7 已在 §2.2/§4.2 自带口径列；是否增设"工艺特征索引（指向 C7）"一节待定。
10. **C6 `machine_context` 的指向**：KB6 M-2 原请求在 `machine_context` 增 `motion_program`，裁决改为 C7 的 `scan_program`。C6 §2 需加一句指向，否则同一信息有两个候选权威载体（C7 不擅自给 C6 加条文）。
11. **KB6 M-4 的 T0 层请求仍未裁决**：本项目自行执行的标定实验（自建网格工装 + 真实相机 + 真实轴 + 自记温度）是真实测量但非产线。本文件**未**新增 tier 词汇（只用 T1-a/T1-b/T2/T3），故 §4 的标定证据目前只能标 `T2+T3`；若采纳 T0，须在 C5 §1 单列并禁止与 T1 混算。
