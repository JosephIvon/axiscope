# C2 — 特征向量契约

`features()` 的纯函数输出：只读 C1 样本包，只产出**确定性可复现**的数值特征。
规则引擎（C3）只能读 C2，不允许自己再做 FFT——保证"证据"与"判断"分离。

## 例 A —— fs = 8 kHz、有电流通道、电机侧反馈（完整可诊断场景）

```json
{
  "schema": "axiscope.features/1",
  "ref": {"sample_id": "AX1-20260311", "sha256": "…"},
  "fs_hz": 8000.0,
  "present_channels": ["pos_cmd", "pos_fb", "fe", "cur_q"],
  "freq_limits": {
    "fs_hz": 8000.0, "nyquist_hz": 4000.0, "reliable_band_hz": 3200.0,
    "blocked_rules": [], "reason": null
  },
  "position_quantum_mm": 0.00002,
  "global": {
    "fe_rms_counts": 412.6,
    "fe_rms_mm": 0.00825,
    "fe_p999_counts": 1380.0,
    "fe_max_counts": 2104.0,
    "fe_mean_counts": -56.0,
    "fe_sign_change_rate_hz": 612.0,
    "cur_q_rms_a": 0.85, "cur_q_rms_pct": 18.4,
    "cur_q_peak_abs_a": 3.4, "cur_q_peak_abs_pct": 74.0,
    "cur_q_saturation_ratio": 0.012,
    "thermal_drift_counts_per_min": 3.1,
    "thermal_fe_correlation_r": null,
    "reversal_error_counts": 268.0,
    "backlash_estimate_counts": 268.0,
    "friction_stiction_ratio": 1.9
  },
  "spectral": {
    "fe": {"freq_hz": [0, 1.95, 3.91, 5.86], "psd": [0, 1, 2, 3], "npy": "features/fe_psd.npy",
            "dominant_freq_hz": 1181.0, "dominant_psd_ratio": 0.34, "tonality_index": 0.62},
    "cur_q": {"freq_hz": [0, 1.95, 3.91, 5.86], "psd": [0, 0.4, 1.1, 0.7], "npy": "features/curq_psd.npy",
               "dominant_freq_hz": 1183.0, "dominant_psd_ratio": 0.41, "tonality_index": 0.71,
               "harmonic_ratios": [2.0, 3.0]},
    "vel_fb": {"dominant_freq_hz": null}
  },
  "resonance": {
    "candidates": [
      {"freq_hz": 1181.0,
       "coherence_torque_velocity": 0.86,
       "antiresonance_freq_hz": 440.0,
       "present_in_dwell": true,
       "present_in_rest": false,
       "tracks_command_frequency": false,
       "amplitude_ratio_vs_broadband": 8.4,
       "quality_factor_estimate": 27.0,
       "three_db_width_bins": 22,
       "is_double_inertia_pair": true}
    ],
    "nyquist_hz": 4000.0,
    "resolution_hz": 1.95,
    "estimation": {"window": "hann", "nperseg": 4096, "noverlap": 2048,
                    "method": "welch", "pair_separation_bins": 380,
                    "n_segments": 8, "bins_in_band": 96}
  },
  "sensor_disagreement": {
    "pairs": [{"a": "pos_fb", "b": "laser_ref", "a_role": "canonical", "b_role": "extra",
                "unit": "counts", "rms_counts": 51.0,
                "max_counts": 240.0, "datum_offset": 12.0, "corr": 0.998,
                "dominant_order_per_rev": 1.0, "direction": "b_a"}],
    "note": "多余反馈经 C1 `cross_validation.pairs` 引入；分歧本身是证据，不是噪声。rms/max 已扣原点常偏（规则 16 / A-106），常偏登记在 `datum_offset`；`*_counts` 的后缀是历史名，真实单位看 `unit`（A-97）"
  },
  "feedback_integrity": {
    "corr_pos_fb_vs_pos_cmd": 0.983,
    "fe_zero_ratio": 0.021,
    "pos_fb_static_on_move_ratio": 0.0,
    "identity_check": {"performed": true, "reason": null},
    "second_feedback_available": true,
    "masquerade_suspected": false,
    "note": "C1 派生规则 2 的 fe 假朋友自检正式化（A-5）：corr >= 0.99 且 fe 几乎恒零 ⟹ pos_fb 很可能是指令位置（DPOS）被适配器冒充成反馈。这与「反馈通道本身坏了」在波形上同形，区分只能靠 second_feedback_available（A-46 / KB4 CP-11）。`second_feedback_available` 只统计**过了恒等式核对**的列（规则 18 / A-105 ②③）；本示例只演示 `identity_check` 的 `performed`/`reason` 两键形态，计数键集见 C1 派生规则 9 与规则 18"
  },
  "ripple": {
    "probing": [
      {"segment_id": 5, "vel_mean_counts_s": 52000.0,
       "ripple_pp_counts": 340.0, "ripple_rms_counts": 78.0,
       "dominant_order_per_rev": 1.0,
       "ripple_over_velocity_pct_per_rev": 0.65,
       "correlated_with_cur_q": 0.88}]
  },
  "crawling": {
    "low_speed_segments": [
      {"segment_id": 2, "vel_mean_counts_s": 120.0,
       "is_sawtooth": true, "sawtooth_freq_hz": 6.4,
       "vel_min_ratio": 0.0, "stall_count": 3,
       "corr_vel_vs_curq": 0.79}]
  },
  "ff_mismatch": {
    "accel_regime_rms_counts": 690.0,
    "decel_regime_rms_counts": 305.0,
    "asymmetry_ratio": 2.26,
    "fe_vs_accel_corr": 0.83,
    "residual_slope_vs_jerk_corr": 0.44
  },
  "encoder": {
    "per_rev_periodic_present": true,
    "per_rev_amplitude_counts": 96.0,
    "harmonics_per_rev": 1,
    "detrended_r2": 0.62,
    "phase_locked_to_pos_modulo": true
  },
  "quality_ref": {"quantization_step_counts": 1.0, "motor_rev_counts": 524288,
                   "dt_jitter_ratio": 0.02, "nan_ratio": 0.0, "gap_max_s": 0.00025,
                   "source": "C1 meta.quality（镜像进 C2，规则证据只能走 C2 路径，A-10）"},
  "step_response": [
    {"segment_id": 1, "overshoot_pct": 18.4,
     "settling_time_ms": 42.0, "settle_band_counts": 20.0,
     "settle_band_pct_of_move": 0.04,
     "ringing_cycles_to_settle": 3.5, "damping_ratio_estimate": 0.28,
     "rise_time_ms": 11.0, "limit_cycle_present": false,
     "limit_cycle_amplitude_counts": null, "limit_cycle_freq_hz": null}],
  "tracking": {
    "path_segments": [
      {"segment_id": 8, "kind": "path",
       "fe_rms_counts": 1520.0, "fe_max_counts": 3100.0,
       "corner_error_counts": 420.0,
       "velocity_feedforward_pct_applied": null,
       "acceleration_feedforward_pct_applied": null,
       "corr_fe_vs_accel": 0.91, "corr_fe_vs_jerk": 0.32}]
  },
  "bandwidth": {
    "position_loop_crossover_hz": 42.0,
    "phase_margin_deg": 38.0, "gain_margin_db": 7.2,
    "method": "command_response_h1",
    "confidence": 0.6,
    "note": "由 pos_cmd/pos_fb 的 H1 估计，非注入激励，仅供定性"
  },
  "event_context": {
    "available": true,
    "n_events": 1204,
    "n_by_source": {"motion": 640, "drive": 3, "interp": 12, "network": 5,
                     "host": 2, "vision": 480, "process": 62},
    "n_alarm": 3,
    "host_pause_max_ms": 41.2,
    "interp_underrun_count": 12,
    "interp_underrun_during_path": 11,
    "network_cycle_miss_count": 5,
    "bus_cycle_hold_max_ms": 2.1,
    "vision_result_latency_p95_ms": 31.2,
    "fe_spike_count": 17,
    "fe_spike_aligned_to_host_pause": 2,
    "fe_spike_aligned_to_underrun": 11,
    "fe_spike_aligned_to_network_miss": 4,
    "fe_spike_aligned_to_vision_result": 3,
    "fe_spike_aligned_to_recipe_change": 0,
    "alignment_residual_ms": 0.25,
    "sync": {"method": "trigger_edge", "verified": true, "uncertainty_ms": 0.5},
    "causal_claims_permitted": true,
    "step_labels": [{"t0": 0.400, "t1": 0.470, "step": "place", "recipe": "AuSn_280C_die4"}]
  },
  "segment_coverage": {
    "rest": 2, "move": 6, "settling": 6, "dwell": 3,
    "probing": 1, "path": 1, "homing": 0, "scanning": 0, "curing": 0
  },
  "unavailable": [
    {"feature": "freq_limits.reason",
     "reason": "blocked_rules 为空（reliable_band_hz = 3200 Hz 覆盖本包全部判据声明的频点）⟹ 没有越带事由可写；KB3 §1.11 该行的「算不出的条件」是 —（文本槽），但 C2 规则 2 的逐路口径覆盖包内每个 null，故照样登记一行"},
    {"feature": "spectral.vel_fb.dominant_freq_hz",
     "reason": "present_channels 无 vel_fb ⟹ 该路谱从未算过（C2 规则 2：null 不是 0）"},
    {"feature": "global.thermal_fe_correlation_r",
     "reason": "本样本 present_channels 无 temp ⟹ FE 与温度相关性不可算（值为 null，不是 0）"},
    {"feature": "step_response[0].limit_cycle_amplitude_counts",
     "reason": "limit_cycle_present = false ⟹ 极限环未判定，无幅值可登记（KB3 §1.8 该行「算不出的条件」：present ∈ {null, false} ⟹ null，不得当 0）"},
    {"feature": "step_response[0].limit_cycle_freq_hz",
     "reason": "同上：present = false ⟹ 没有极限环峰频可登记；峰在 [f_min, f_b] 内与否无从谈起（KB3 §1.8）"},
    {"feature": "tracking.path_segments[0].velocity_feedforward_pct_applied",
     "reason": "反演回归的自变量 vel_cmd 不在 present_channels ⟹ 前馈比例无从反演（KB3 §1.9 该行「算不出的条件」：vel_cmd 缺失 ⟹ null，C2 示例正是 null）"},
    {"feature": "tracking.path_segments[0].acceleration_feedforward_pct_applied",
     "reason": "回归量为 a，本包无 vel_cmd 也无 pos_cmd 二阶差分的登记来源 ⟹ a 不可辨；cur_q 虽在位，但它是交叉核验的另一半（KB3 §1.9 该行「算不出的条件」：cur_q 缺失或 a 不可辨 ⟹ null）"}
  ]
}
```

**例 A 的两处"短"是刻意的**：`spectral.*.freq_hz/psd` 只内联 PSD 的前 4 个 bin
（步长 = `resolution_hz = 8000/4096 = 1.953125`），整条曲线在 `npy` 里；
`dominant_freq_hz = 1181` 是在**整条**曲线上取的峰，不受预览截断约束（规则 14 第二条）。
`global.thermal_drift_counts_per_min = 3.1` 有值而 `temp` 不在 `present_channels` 里也不是矛盾：
按 KB3 §1.1 该行定义，它回归的是 `fe_dwell` 对**时间轴**的斜率，只需 `dwell`/`rest` 累计 ≥ 120 s、
跨度 ≥ 20 min；缺 `temp` 只让**温度归因**（`thermal_fe_correlation_r`）不可做，后者已进 `unavailable`。

## 例 B —— fs = 1 kHz、无电流通道（DaRUS 类真实场景，展示"看不见"该怎么写）

```json
{
  "schema": "axiscope.features/1",
  "ref": {"sample_id": "DA-RUS-LdaFricIdent-01", "sha256": "…"},
  "fs_hz": 1000.0,
  "present_channels": ["pos_cmd", "pos_fb", "fe", "vel_cmd", "vel_fb", "torque"],
  "freq_limits": {
    "fs_hz": 1000.0, "nyquist_hz": 500.0, "reliable_band_hz": 400.0,
    "blocked_rules": ["R-03", "R-04", "R-11#switching_freq"],
    "reason": "kHz 级机械谐振与开关频率类判据不可评估：奈奎斯特以下无该频段信息"
  },
  "position_quantum_mm": 0.1714,
  "resonance": {"candidates": [], "nyquist_hz": 500.0, "resolution_hz": 0.49,
                 "estimation": {"window": "hann", "nperseg": 1024, "noverlap": 512,
                                 "method": "welch", "pair_separation_bins": null,
                                 "n_segments": null, "bins_in_band": null}},
  "global": {"cur_q_rms_pct": null, "cur_q_rms_a": null},
  "quality_ref": {"quantization_step_counts": 1.0, "motor_rev_counts": null,
                   "dt_jitter_ratio": 0.03, "nan_ratio": 0.004, "gap_max_s": 0.002,
                   "source": "C1 meta.quality 镜像；本样本 units_are = si_native（A-4），counts 由 1/counts_per_mm 折算，不是原生编码器刻度"},
  "feedback_integrity": {
    "corr_pos_fb_vs_pos_cmd": 0.941,
    "fe_zero_ratio": 0.003,
    "pos_fb_static_on_move_ratio": 0.0,
    "identity_check": {"performed": true, "reason": null},
    "second_feedback_available": true,
    "masquerade_suspected": false,
    "note": "本示例演示的是**核对已跑成**的形态（`performed = true`）；若接入层跑不了核对，`identity_check.performed = false`、`second_feedback_available` 只能是 `null` 并把相关判据送进 `unavailable` + `blocked_by = derived_column_unchecked`（规则 18 / A-105 ④），不得留一个乐观的 `true`"
  },
  "sensor_disagreement": {
    "pairs": [{"a": "pos_fb", "b": "laser_ref", "a_role": "canonical", "b_role": "extra",
                "unit": "counts", "rms_counts": 118.0, "max_counts": 960.0,
                "datum_offset": 40.0, "corr": 0.994,
                "dominant_order_per_rev": null, "direction": "b_a"}],
    "note": "本样本 units_are = si_native 且 position_quantum_mm = 0.1714（非 null）⟹ counts 刻度由 1/counts_per_mm 折算得到，绝对 counts 阈值在此可用，但报告必须注明该折算来源；若 counts_per_mm 为 null，这些值一律 null + absent_counts_scale（A-97）"},
  "ripple": {"probing": [{"segment_id": 3, "vel_mean_counts_s": 2.0,
             "ripple_pp_counts": 1.6, "ripple_rms_counts": 0.4,
             "dominant_order_per_rev": null,
             "ripple_over_velocity_pct_per_rev": null,
             "correlated_with_cur_q": null}]},
  "event_context": {"available": false, "reason": "样本包无 events.jsonl",
                     "sync": {"method": null, "verified": null, "uncertainty_ms": null},
                     "causal_claims_permitted": false},
  "segment_coverage": {"rest": 4, "move": 9, "settling": 0, "dwell": 2,
                        "probing": 5, "path": 0, "homing": 1, "scanning": 0, "curing": 0},
  "unavailable": [
    {"feature": "global.cur_q_rms_a", "reason": "源数据无电流通道（present_channels 无 cur_q）"},
    {"feature": "global.cur_q_rms_pct", "reason": "无 cur_q；且本包未登记 meta.rated_current_a ⟹ *_pct 支路关闭（C2 规则 3：归一化量只有额定值在场时才允许非 null）"},
    {"feature": "spectral.vel_fb.dominant_freq_hz", "reason": "vel_fb 由 pos_fb 差分派生，噪声底高于频段"},
    {"feature": "resonance.candidates", "reason": "整条判据带被 freq_limits 阻塞"},
    {"feature": "resonance.estimation.n_segments", "reason": "样本包未承载 Welch 实跑的记录长度 ⟹ 段数无实测来源；该量是 A-102 ② 的显式登记项，禁止由 nperseg/noverlap 猜长度反推，只能 null + 登记（C2 规则 2）"},
    {"feature": "resonance.estimation.bins_in_band", "reason": "无候选峰（resonance.candidates 为空，带被整条阻塞）⟹ 峰邻域带内 bin 数无定义；同为 A-102 ② 显式登记项，不得由 reliable_band_hz/resolution_hz 反推"},
    {"feature": "resonance.estimation.pair_separation_bins", "reason": "无候选峰（resonance.candidates 为空，带被整条阻塞）⟹ 峰间距 (freq_hz − antiresonance_freq_hz)/resolution_hz 无输入、无定义；与 n_segments/bins_in_band 同族、同为 A-102 ② 显式登记项，不得由 resolution_hz 反推（C2 规则 2/10）"},
    {"feature": "spectral.cur_q.dominant_freq_hz", "rule": "R-11", "branch": "switching_freq",
     "reason": "R-11 的开关频率支路要求的 kHz 量级频点在 400 Hz 可靠带之外（且本样本无 cur_q 通道，该支路双重不可用）；但 R-11 的 150 Hz 谐波支路仍可评 ⟹ 整条规则不进 blocked_rules，只按支路登记（A-79）"},
    {"feature": "encoder.per_rev_amplitude_counts", "reason": "无方向反向段，无法分离一阶项"},
    {"feature": "quality_ref.motor_rev_counts", "reason": "接入侧 meta.axis.motor_rev_counts 未登记 ⟹ CPR（counts/rev）无来源（KB3 §1.13b 该行「算不出的条件」）"},
    {"feature": "ripple.probing[0].dominant_order_per_rev", "reason": "CPR 无来源（同上一条：quality_ref.motor_rev_counts = null）⟹「每转」无定义（KB3 §1.4 该行「算不出的条件」）"},
    {"feature": "ripple.probing[0].ripple_over_velocity_pct_per_rev", "reason": "该比值须在整转窗口上求值，CPR = null ⟹ 无整转窗口；本段 vel_mean_counts_s = 2.0 > 0，挡它的是「每转」而不是速度支路（KB3 §1.4 该行「算不出的条件」）"},
    {"feature": "ripple.probing[0].correlated_with_cur_q", "reason": "present_channels 无 cur_q ⟹ 纹波与电流的 Pearson r 无第二路输入（KB3 §1.4 该行「算不出的条件」：无 cur_q ⟹ null）"},
    {"feature": "event_context.sync.method", "reason": "无事件 ⟹ 无对齐方式可登记；填 unknown 会把「未做」读成「做过并对不上」（A-103 ③）"},
    {"feature": "event_context.sync.verified", "reason": "无事件 ⟹ 时钟核验从未发生；填 false 是替现场下结论（A-103 ③）"},
    {"feature": "event_context.sync.uncertainty_ms", "reason": "无实测时钟不确定度；5 ms 兜底只在门禁处生效并记 audit.assumptions（A-103 ③）"}
  ]
}
```

**例 B 的重点不是"算得少"，而是把"算不了"写成结构化事实**：
`resonance.candidates` 为空是"被阻塞"，必须同时出现在 `blocked_rules` 与 `unavailable` 里；
报告层若因此写"未检出谐振"就是撒谎。`position_quantum_mm = 0.1714` 也在告诉读者：
这份数据上任何"µm 级精度"的说法都不成立（量子就有 171 µm）。

例 B 的**数值是示意值**（结构、门控与 `null` 的分布才是要演示的东西）；真实样本一律以引擎输出为准。
两份示例都必须能被 `JSON.parse` 直接解析——契约示例解析不了，就说明没人校验过它。

## 硬性约定

1. **所有数组特征必须降采样**：`spectral.*.psd` 之类在 JSON 里存降采样后的版本
   （≤ 2048 点），完整数组写入样本包旁的 `features/` 二进制 `.npy`，JSON 里给 `npy` 相对路径。
   报告与 LLM 层只读降采样版。
2. **null 不是 0**。任何算不出的特征写 `null` 并同步追加到 `unavailable`，带 `reason`。
   `unavailable[]` 的元素形状：`feature` 与 `reason` 必填；`rule`（规则号）与 `branch`（支路名，
   与 `blocked_rules` 的 `#` 后缀同名）**仅在频带/支路门禁造成的不可用中出现**（A-79），
   用于让 `blocked_rules` 与 `unavailable` 两侧逐条对得上。
   规则引擎遇到依赖的输入为 null 必须放弃该判据，不得插值。
   **本条的边界：null 分两类，只有第一类欠一行账。**
   - **算不出的 null**（缺通道、缺分段、被频带/支路门禁阻塞、本特征切片/本算例没填这条路径）
     ⟹ **逐路**记一行：包里每一个 `null` 的 JSON 路径对应一行 `unavailable`，`feature` 写
     **点分全路径、含顶层块名前缀**（`global.cur_q_rms_a`，不是 `cur_q_rms_a`）。数组元素里
     `null` 的归属路径可写具体下标（`tracking.path_segments[0].corner_error_counts`）或整族模板
     （`step_response[].overshoot_pct`）——两种写法都与 KB3 §1 特征索引、`features._dig()` 认的
     `[]` 口径同源，逐路核对时按同一条路径归一。
     短名行**不是风格问题而是缺陷**：C3 侧 CAP-5（`c3validate.py` 把 `unavailable[].feature` 收成
     集合、与证据的 feature 路径**逐字**比对）与 `assertions.py` 的 `blocked_rules`↔`unavailable`
     对账都是字符串集合比对，对不上全路径的行**永远不会命中** ⟹ 该项检查在这条路径上是假绿。
   - **本契约自己定义的合法 null**（不是"算不出"，而是"按定义就该为 null"）⟹ **不要求行**，
     但只有下列**逐条点名**的三处算豁免，清单外一律按上一条记账（豁免不得由实现侧自行扩张）：
     ① `feedback_integrity.identity_check.reason`——`performed = true` 时它按 C1 派生规则 9 的
        形状就是 `null`（该槽承载的是"核对为什么跑不了"，核对跑成了就没有内容可写）；
     ② 各块的 `note` 说明字段（路径最后一段为 `note`，如 `sensor_disagreement.note` /
        `feedback_integrity.note` / `bandwidth.note`）——它们是叙述槽，不是特征；
     ③ `sensor_disagreement.pairs[].dominant_order_per_rev`——规则 17 原句
        「`dominant_order_per_rev` 无 CPR 时为 `null`」。
     ★ `resonance.estimation.pair_separation_bins` **不在**豁免清单里：它与 `n_segments`、
     `bins_in_band` 同族（规则 10 / A-102 ② 的显式登记项），无候选峰 ⟹ 按上一条逐路记一行，
     不得由 `resolution_hz` 反推。
     这条边界由加载期检查 `features.check_null_accounting()` 机器判（`check_self_consistency()` 调用它），
     四份契约示例（例 A / 例 A 的无事件孪生 / 例 B / KB4 §2.3 算例 B）也各跑一遍，三处负向例
     （抹行、改短名、抹 `resonance.estimation` 的样本量键）钉在 `tests/test_contract_examples.py`
     与 `tests/test_slice.py`（KB0 §6 检查 22）。
   - **账目粒度 = `(feature, rule/branch)`，不是 `feature` 单独**：上面「逐路」说的是
     **每一个 null 路径至少有一行**，**不是**「一个路径只能有一行」。同一条路径出现多行是契约**要求**的：
     A-79 的 `blocked_rules` ↔ `unavailable` 一一对账按 `(feature, rule/branch)` 逐条比，一条判据带被
     阻塞就要一行，`examples/kb4_case_b_features.json` 的 `resonance.candidates` 因 R-03、R-04 两条
     被 `freq_limits` 阻塞而**必须**各有一行（`tests/test_contract_examples.py::test_case_b_resonance_family_is_band_blocked`
     钉住这两行同时在）。把「重复行」当缺陷去清理，会直接破掉 A-79 的对账——本条（A-119）就是为
     拦这个记的。反过来，`rule`/`branch` 只在门禁造成的不可用里出现这一点仍然成立（见上）。
3. **单位**：`*_counts` 的后缀是**历史名，不是单位**（A-97）。它的字面含义是"该通道
   **原生刻度**下的数值"，真实单位由 `meta.units_are` 唯一决定（`counts` ⟹ 编码器 counts；
   `si_native` ⟹ 源单位，本例为 m）。字段**不改名**：C2 已冻结，KB3/KB4 与两份算例逐字引用
   这些路径，改名会让三处手算锚点同时失配。由这个改名派生两条硬约束：
   - **绝对 counts 阈值**（形如 `≥ 22 counts`）在 `units_are != "counts"` 且
     `meta.counts_per_mm == null` 时**不得直接套用**——把 m 当 counts 判是静默量纲替换，
     比写 `null` 危险一个量级。该判据一律进 `unavailable`，C3 侧以
     `blocked_by = absent_counts_scale` 登记，reason 固定句式「无 counts 刻度，绝对阈值不可比」。
   - **比值 / 相关 / 相干类判据与刻度无关**（分子分母同单位）⟹ 照算，**不得**被上一条连坐。
     一份 si_native 样本里 `fe_p999/fe_rms ≥ 4`、`coherence ≥ 0.7` 都应当能算出来；把它们一起
     堵掉就是上一条犯的反面错误。
   这两条的分界由 KB3 §1.13b 逐条标注「绝对 / 比值」承载（规则表里同名为 `scale`），
   **未标注者规则引擎按绝对处理**（保守侧）。
   `*_mm`（A-110 ② 已裁，**A-113 = 任务 #39 已落地**）是纯单位换算、不是新的物理数字，故有两条合法来源：
   (i) **counts 定标路径**：`counts_per_mm != null` 时 `*_mm = 原生 counts 值 / counts_per_mm`
   （`fe_rms_mm = fe_rms_counts / counts_per_mm`，例 A/B 走此路）；
   (ii) **si_native 直接定标路径**：`counts_per_mm == null` 但 `meta.units_are == "si_native"`
   且该通道在 C1 单位词表里登记为**长度刻度**（`unit = "m"`）时，`*_mm = 原生长度值 × 1000`——
   `m → mm` 是单位定义（milli 的字面意义），不替本项目决定任何物理容差，故**应当填而非留 null**
   （留 null 丢掉真实信息）。走 (ii) 时**必须**向 `audit.assumptions` 落且只落一行，锚 `meta.units_are`、
   句式固定「`*_mm` 由 C1 原生 SI 刻度直接定标，非 counts/counts_per_mm 路径」（A-110 ③：随 #39
   可给 µm 级**实测幅值**，随行单位、锚 `meta.units_are`；µm 级**容差/目标**数字本仓无来源，仍禁，
   不得由实测幅值反推）。**速度 `m/s`、转矩 `N_m`、电流 `A` 都不是长度刻度**——拿非长度通道乘 1000
   是量纲错误，一律不产 `*_mm`。本契约的 `*_mm` 字段只有两处，各自的 null 条件：
   `global.fe_rms_mm`（无 fe，或既有 counts_per_mm=null 又不是 si_native 长度刻度 ⟹ null 并 `unavailable`）；
   `position_quantum_mm` **在 si_native 且 counts_per_mm=null 的样本上恒留 null**——它由 `1/counts_per_mm`
   加量化步长定义（规则 11），**不是**纯长度换算，硬填等于凭空造一个 counts 量子（A-110 的尺子：造数即禁）。
   `*_mm` 的门禁与绝对 counts 阈值的 `absent_counts_scale` 门禁**分权**（`counts_scale_missing` 语义不动）：
   放开 (ii) 的定标绝不放松绝对阈值侧——`20 counts`/`50 counts/s`/`2.0 counts/min` 仍不得折算成 m 级常数。
   除上述外，`meta.units_are == "si_native"` 时按源单位给 `*_m` / `*_mps` / `*_nm`，
   同样不得臆造换算。归一化量（`*_pct`）只有当 `meta.rated_current_a`（电流）或
   `meta.drive.rated_torque_N_m`（转矩，A-70）存在时才允许非 null，否则为 `null` 并进 `unavailable`
   ——一份 A 为单位的电流数据被写成"18.4%"是凭空发明额定值。
   转矩分母的合法性看 `meta.drive.rated_torque_source`：`measured`/`manual` 正常；
   `nameplate` 可用但报告须带限定语；`assumed` 可用但**证据层级封顶 T2** 并强制 caveat
   "额定转矩为假定值，百分比类判据的绝对刻度不可信"（DaRUS 的 `torque_max = 32` 即此档，A-27）。
   没有这条纪律，`cur_q_saturation_ratio` 一类比值判据会带着一个来源不明的分母被当成实测。
4. **每个特征必须可追溯到公式或文献出处**，登记在 `docs/kb/KB3-tuning-rules.md` 的特征索引表里，
   字段名与本文件严格一致。**C2 只收伺服波形特征**：耦合寻光、标定残差、节拍统计一律归 C7，
   引用时走 `process.*` / `calibration.*` / `cycle_stats.*` 路径；把工艺特征塞进 C2
   会让通用内核与工艺外壳耦合，而工艺侧根本没有满足本条纪律的真值数据。
5. **估计类特征必须带 `method` 与 `confidence`**（如 `bandwidth`），
   实测类（如 `fe_rms_counts`）不需要。
6. `resonance.candidates` 是诊断的核心证据结构，四个布尔/数值条件
   （`present_in_dwell`、`present_in_rest`、`tracks_command_frequency`、`is_double_inertia_pair`）
   共同决定归因方向，缺一不可。
7. **频带门禁**：`freq_limits.reliable_band_hz = nyquist_hz / 1.25`（留抗混叠余量）。
   任何判据声明的频点若超出该带，该判据必须进 `unavailable` 并列入 `freq_limits.blocked_rules`，
   **不得**输出"未发现共振"——那是把"看不见"说成"没有"。
   ★ **多栅格样本（A-96）**：上面这套的 `fs_hz` / `nyquist_hz` / `reliable_band_hz` 取的是
   **C1 `meta.primary_time_base` 口径**。若某判据的输入通道挂在 `secondary` 栅格上，
   须**按该通道自己的栅格重算**一遍门禁，并把两条口径都写进 `unavailable[]` 的 `reason`
   （形如 `band_gate_fs=4000 (tb1)` vs `band_gate_fs=1000 (tb0)`）；
   参与同一判据的通道**不在同一栅格**、或其 C1 `meta.resample[].band_effect ∈ {band_lost, aliased_risk}`
   时，该判据（尤其**相干 / 相位类**）一律 `unavailable`，禁止在降采样序列上给相干结论。
   `role = "event"` 的离散事件栅格**不参与**本门禁的 `fs` 取值。
   实测教训：DaRUS 两份真实数据 `SampleTime` 恒为 1 ms（fs=1000 Hz，奈奎斯特 500 Hz），
   在其上报告"1.18 kHz 机械谐振"是物理不可能的。
   **`blocked_rules` 的粒度是"规则或规则支路"，不是"规则表"**（A-79）：
   条目要么是裸规则号（整条规则不可用，如 `R-03`），要么是 `R-<nn>#<branch>` 形式的**支路限定**
   （如 `R-11#switching_freq`——R-11 的 150 Hz 谐波支路在 400 Hz 带内仍可评，把整条 R-11 写进
   `blocked_rules` 会谎报"纹波判据全不可用"）。每个条目必须在 `unavailable[]` 里有一条
   `rule`/`branch` 与之对应的行，反之亦然（两侧对不上 = 门禁清单与不可用清单脱钩）。
   **恒运行的规则永远不得出现在 `blocked_rules` 里**：`R-25` 是频带门禁本身（它没有声明频点，
   不能被自己阻塞，正确落点是 C3 `audit.rules_fired`），`R-10` 是采样的/混叠假峰的**检测器**，
   在 `fs = 1 kHz` 的数据上恰恰最需要它运行。
8. **`event_context` 的因果纪律**：`causal_claims_permitted` 是唯一的因果开关，
   当且仅当 `sync.verified == true` **且** `alignment_residual_ms ≤ sync.uncertainty_ms` 时为 `true`。
   残差**缺键或为 `null`**（示例 B：无 `events.jsonl`）⟹ 视同不成立，开关只能为 `false`——
   "没算出残差"不是"残差合格"，缺证据一侧永远落在禁用侧。
   **`alignment_residual_ms` 是"对齐得好不好"，不是"因果证据强不强"**（A-82，更正 A-50 的方向）：
   它是匹配对 `abs(Δt)` 的中位数，即事件时钟折算到波形时间轴后**剩下**的错位，越**小**越好。
   残差落在时钟不确定度预算**之内**，说明这份同步真的做到了它声称的精度；残差**超出**预算，
   说明两个钟之间还有没被建模的系统偏差——此时任何"尖峰与事件对齐"都可能只是钟差，
   只能降级为共现（CAP-8 正是据此封顶 0.40，与本条同向）。
   而"**大于** `τ_u`"是另一种要求，它作用在**被声称的量**上（延迟、保持时长、两次到位之差），
   不是作用在残差上：一个小于时基不确定度的差值根本无法分辨（KB3 纪律 6）。
   **`available == false` 时 `sync` 三字段一律 `null`，并各记一条 `unavailable`**（A-103 ③）：
   特征层不得用 `{"method": "unknown", "verified": false, "uncertainty_ms": 5.0}` 这类占位值填空——
   `false` 是替现场下"核验过但没通过"的结论，而 `5.0` 一旦被写死就会悄悄参与 G3/G5 门禁却从不留痕。
   `τ_u` 的 5 ms 保守兜底属于**门禁层**（KB3 纪律 6），由其在 `audit.assumptions` 记一笔，
   不许前移到特征层预填。
   这两个方向曾被当成同一个量的同一个不等号，写出过"对齐越差越允许下因果结论"的反物理判据，A-82 已拆开。
   对齐窗本身仍必须严格大于 `τ_u`（窗比钟差不分辨率，匹配就是抽签）；窗内是否"太挤"
   不由本条管，由 R-28 的族内区分度和 `fe_spike_aligned_to_* / fe_spike_count` 比例管。
   例 A 取 `alignment_residual_ms = 0.25`、`uncertainty_ms = 0.5`（硬件触发沿同步可到亚 ms 级；
   `0.25 ms = 2 × 1/fs`，`fs = 8 kHz`），两条同时成立 ⟹ `causal_claims_permitted = true`。
   曾被写成 `residual = 0.4` / `uncertainty = 0.15`（A-50），那个组合违反 KB4 门 G5
   （`1/fs = 0.125 ms > τ_u/2 = 0.075 ms`），且把一个 8 kHz 采样的中位残差压到了半个样本以下，
   数值上也不可表示——已由 A-82 一并更正。
   为 `false` 时，`fe_spike_aligned_to_*` 只允许作为**时间共现**呈现，
   规则引擎禁止据此输出任何 `software_induced_error` 归因。
   `available == false`（无 `events.jsonl`）时，规则引擎**必须**在 C3 的
   `differential.not_evaluable` 中显式登记该族（用 `family` 键，**不是** `fault_mode`——
   `software_induced_error` 是族级标签不是 slug，A-18），不得沉默。
9. **谐振/反谐振顺序是物理约束，不是可调参数**：共置两惯量（C1 `sensor_config == "motor_side"`）
   必有 `antiresonance_freq_hz < freq_hz`，且 `f_res / f_anti = sqrt(1 + λ)`。
   旧版示例把谷写在峰之上（1181 峰 / 1420 谷），那组数值在共置构型下**物理不成立**，已改为
   `440 / 1181`（λ ≈ 6.2，与 KB5 参数集 P-B 自洽）。
   `sensor_config == "unknown"`（不知道传感器装在哪侧）或 `"mixed"`（电机侧与负载侧两套通道拼成
   一条曲线，峰谷不是同一传递函数的响应）时，顺序项**不参与判定**，双惯性配对的置信度封顶
   （C1 派生规则 7、裁决 A-68）。两者的区别只在记录的原因，行为一致。
10. **估计参数必须随结果一起落盘**：`resonance.estimation.{window,nperseg,noverlap,method}` 与
    `resolution_hz` 决定 `amplitude_ratio_vs_broadband`、`quality_factor_estimate`、
    `pair_separation_bins` 的可信度；缺这些参数，谱类结论不可复现，规则引擎必须拒绝引用。
    `pair_separation_bins < 2` 时"峰谷配对"一律判不可分辨。
    **派生式必须可复算**（A-76，与 C3 规则 15 同纪律）：`resolution_hz = fs / nperseg`，
    `pair_separation_bins = (freq_hz − antiresonance_freq_hz) / resolution_hz` 取整。
    例 A：`8000/4096 = 1.95`、`(1181 − 440)/1.95 = 380`。示例里写一个推导不出来的数（曾写 382）
    不是"取整口径差异"，而是缺陷——它让读者无法用同一套参数复现配对判定。
    **样本量三兄弟是显式登记的量，不是反推的产物**（A-102 ②，KB4 §2.1(c) 逐判据行的 `n` 由此承载）：
    `resonance.estimation.n_segments`（Welch 实跑段数，`n_ref = 4` 行）、`resonance.estimation.bins_in_band`
    （峰邻域带内 bin 数，`n_ref = 15` 行）、`resonance.candidates[].three_db_width_bins`
    （谐振峰 3 dB 带宽 bin 数，`n_ref = 8` 行；登记值必须等于 rule_table `n_source_recipes` 的
    `round(freq_hz / quality_factor_estimate / resolution_hz)`，例 A：`round(1181/27/1.95) = 22`）。
    `bins_in_band` **不得**由 `reliable_band_hz / resolution_hz` 反推——那会得到 ≈1641，与算例 A 的 96 差一个量级，
    说明算例用的是另一套峰邻域带定义；缺载体条件时三个字段一律 `null` + `unavailable`（规则 2），
    规则引擎侧相应判据按 `MissingSampleScale` 记 `rules_skipped`，禁止默认 `n_factor = 1`（A-102 ③ 过渡口径，
    侧车注入须显式带 `welch_segments` / `band_bins` 键并落 `audit.assumptions`）。
11. **`position_quantum_mm = 1 / counts_per_mm`**（缺定标时为 `null`）。
    它的唯一用途是拦住吹牛：任何精度/残差声明若小于该量子的一半，必须改写为"低于本数据分辨率，
    无法判定"。DaRUS 类数据量子 = 0.171 mm，在这种数据上说"亚微米"是自相矛盾。
12. **加载期校验**：`bandwidth.confidence` 上界 0.6（非注入激励的 H1 估计不该更自信）；
    `freq_limits.fs_hz`、顶层 `fs_hz`、`resonance.nyquist_hz` 三者必须自洽，
    违反即拒绝该样本包并记 `audit.assumptions`——示例值被照抄进实现是最隐蔽的越界方式。
13. `segment_coverage[kind] == 0` 时，所有以该 kind 为必要上下文的数组必须为**空数组**；
    覆盖度与数组内容矛盾属于解析缺陷，按 C1 红线拒诊断，而不是"就当没有那段"。
14. **自洽性校验（加载期，违反即拒样本）** —— 这三条都是本契约自己的示例曾经犯过的错，
    写出来是为了让实现无法回避：
    - **特征值与 `unavailable` 互斥**：同一特征不得既有非 null 值又出现在 `unavailable` 里（规则 2 的另一半）。
      特征值为非 null ⟹ 它的输入通道必须在 `present_channels` 里；`temp` 缺席却给 `thermal_fe_correlation_r = 0.71`
      这类值，是编造，不是估计。
    - **内联预览数组非空**：`spectral.*.freq_hz/psd` 若为 `[]`，同层统计量（`dominant_freq_hz` 等）必须为 `null`；
      空数组配非 null 主频等于"我看不到谱，但我知道了峰频"。全量数组走 `npy`（规则 1），预览可以短，不能空。
      预览必须是**从 0 起的连续前缀 bin**，相邻差 = `resolution_hz = fs/nperseg`（A-83）：
      例 A 为 `8000/4096 = 1.953125` ⟹ `0 / 1.95 / 3.91 / 5.86`。曾写成 `0 / 1.2 / 2.5 / 3.7`，
      那组步长既不是任何 `nperseg` 的结果，又与同层的 `dominant_freq_hz = 1181` 处在同一个数组里读不通——
      写预览数组的人必须假设读者会拿 `resolution_hz` 去验它。
    - **因果三元组一致**：`causal_claims_permitted` 必须与 `sync.verified == true` 且
      `alignment_residual_ms ≤ sync.uncertainty_ms` 的合取等价（方向由 A-82 锁定：残差要**小**，
      而"必须大于 `τ_u`"只作用于被声称的时延/差值，不是残差）；
      `available == false` 时三个对齐计数字段一律 `null`。
15. **`feedback_integrity` 是数据完整性筛查，不是故障假设**（回应 A-5 / A-46）：
    `corr_pos_fb_vs_pos_cmd ≥ 0.99 [P]` **且** `fe_zero_ratio ≥ 0.9 [P]` ⟹ `masquerade_suspected = true`，
    含义是"这份 `pos_fb` 可能就是指令位置本身被适配器冒充"。此时：
    - `second_feedback_available == true` ⟹ 用 `sensor_disagreement` 判哪一路在说话，可进 `hypotheses`；
    - `second_feedback_available == false` ⟹ **不得**归因（与"通道恒零/未接"在单路数据上不可区分），
      必须登记 `differential.not_evaluable`，并说明缺哪一路反馈。
    该组字段本身不得作为 `supporting_evidence[].feature` 之外的"结论"出现在报告标题里。
    **判据不以 `pos_fb` 为轴**（A-98）：一条 `pos_fb` 都没有的样本（Export10 三套位置测量全部落
    `extra_channels`）照样有多传感器互证，把这些分歧留在 ingest 叙述层等于规则层永远看不见它们。
    - `second_feedback_available := sensor_disagreement.pairs 中至少有一对`**分属不同物理原理**
      （原理取 C1 通道卡 / KB7 硬件真值：电机轴编码器 / 光学 ASCO / 电感 LSV）。
      **同原理的两列分歧不算第二次独立测量**——它只说明这套传感器内部不稳。任一侧原理未登记
      （`unknown`）⟹ 该对不计入，不得拿"未知"与"已知"判成不同。
      **计数只在过了恒等式核对的列上做**（A-105 ②③，口径见规则 18）：派生列与逐行全等孪生的
      丢弃侧都不是一路测量。
    - **无 `pos_fb` 时的冒充分支**改判据：`pos_cmd` 候选与某条反馈**逐行全等**（本样本实测
      `dPosition_test_tar ≡ dPosition_test`、`dPosition_load_tar ≡ dPosition_load`，0/18,651 行有差）
      ⟹ 该"反馈"是指令冒充，仍走 `differential.not_evaluable`，reason 固定句式
      「指令轨与候选反馈逐行全等，二者非独立测量」。
17. **`sensor_disagreement.pairs[]` 的字段形状**（A-98 ① + A-97 ③ + A-106 ②）：
    - `a` / `b` 的值域是**任意两条 C1 已登记通道**（canonical 或 extra 均可），
      并各带必填 `a_role` / `b_role ∈ {canonical, extra}`；分歧对的**来源**仍只有 C1
      `cross_validation.pairs`，**不许 C2 自己配对新列**；
    - `unit` **必填**，值域取 C1 通道单位词表（`counts` / `m` / `m/s` / `A` / …）；
      `rms_counts` / `max_counts` 填的是该单位下的实测值，报告层**禁止裸印**不携单位的数值；
    - `datum_offset` / `corr` 必填，口径见规则 16；`dominant_order_per_rev` 无 CPR 时为 `null`。
16. **`sensor_disagreement` 的分歧必须在去常偏后的残差上算**（A-106）：同一条轴的多套测量各带
    **自己的安装原点**。实测反例（DaRUS Export10，18,651 行）：`dPosition_asco − dPosition_asco_enc`
    逐行差 ∈ `[179.56197, 180.14952] m`（均值 179.813、std 0.270、corr 0.999483），而两套测量的
    行程几乎等长（17.010 / 17.045 m）——量到的 180 m "分歧"全是原点，不是被测对象。口径：
    - `resid := (a − b) − mean(a − b)`；`rms_counts` / `max_counts`（A-97：后缀是历史名，
      真实单位取 `pairs[].unit`）**一律在 `resid` 上计算**；
    - `pairs[].datum_offset`（**必填**）登记被减掉的那个常偏，单位同 `unit`。原点差本身是
      安装/标定证据（KB6 寻光标定族要用），**减了不记等于把证据当噪声抹掉**；
    - `corr` 用**原始值**算（平移不改变相关系数），无须去偏；
    - `datum_offset` 缺失 ⟹ 该对整组 `not_evaluable` + `blocked_by = absent_datum_alignment`，
      reason 固定句式「未做原点对齐，分歧幅值不可比」；
    - 有资格进 `pairs[]` 的只有**独立测量**：逐行全等的两列只算一路，恒等式派生列
      （C1 派生规则 9 / A-105）不得进 `pairs[]`。
    两处示例的 `pairs[]` 已随 #22（A-97）/#23（A-98、A-106）补上 `unit` / `datum_offset` / `corr` /
    `a_role` / `b_role`（`examples/c2_example_a.json`、`examples/c2_example_b.json` 与本文同步）；
    示例里这四个字段的具体数值是示意值，**口径**才是本节的内容。
18. **`feedback_integrity.identity_check`：第二次测量必须先过恒等式核对**（A-105 ②③④，与规则 15/16 同族）：
    该对象是 C1 `meta.audit.identity_check` 摘要的**镜像**，键集逐字同 C1 派生规则 9
    （`performed` / `n_numeric_columns` / `n_rows_checked` / `n_derived` / `n_duplicate_groups` /
    `n_constant_columns` / `n_independent_position` / `reason`）；逐条关系的全文**不进 C2**，
    留在接入侧车 `ingest.identity` 与 findings（kind `derived_column` / `duplicate_column` /
    `linear_dependency_unattributed` / `measurement_independence`）——本契约只镜像规则层要读的计数
    （同 `quality_ref` 的镜像纪律，A-10）。两处示例只演示 `performed` / `reason` 两键的形态，
    计数键的值一律以引擎输出为准（检查 23 的载体义务由本条与 C1 派生规则 9 共同满足）。
    - **计数资格线**：`second_feedback_available` **必须**在过了核对的列上算——
      `identity_check` 判出的派生列、以及逐行全等孪生中被丢弃的那一侧（保留侧恒为反馈列，
      丢掉的是 `_tar` 指令列）都**不是**第二次测量（A-105 ②③，与规则 16 末条、A-98 ③ 同一计数口径）。
      Export10 实测两栏分开记：**母本全量 18,651 行**给出 `dPosition_diff ≡ -(dPosition_test + dPosition_load)`
      残差 3.55e-15、`dVelocity_diff ≡ -(dVelocity_test + dVelocity_load)` 残差 4.44e-16；
      **门控后 5000 行切片**（28 个数值列、关系去重后 3 条）给出 2 条派生列（8.16e-15 m / 容差 1.33e-13；
      2.83e-14 m/s / 容差 5.91e-14）、3 组全等孪生、2 个常数列；位置列见 8 条，扣掉 `dPosition_diff`
      这条派生列与 `dPosition_test_tar`/`dPosition_load_tar` 两条 `_tar` 孪生 ⟹ **`n_independent_position = 5`**。
      力族那条关系（`dForce_diff ≡ dForce_load − dForce_test`）登记为 `linear_dependency_unattributed`：
      恒等式的书写方向数据给不出，只有 `mapping.DECLARED_COMPUTED`（KB2 §4.10）唯一命中才允许贴派生标签，
      未命中只扣一个自由度、不指认哪一列是算出来的（A-105 ①）。
    - **跑不了核对 = 不可评估，不是零关系**：`identity_check.performed == false`
      （数值列 < 3 或有限值行 < 100）时 `second_feedback_available` 一律 `null`，
      一切以"两路独立测量分歧"为前提的判据（`sensor_disagreement` 各支、KB3 R-22 签名①⑥、CP-11 第 3 条）
      进 `unavailable` / `differential.not_evaluable`，`blocked_by = derived_column_unchecked`，
      reason 固定句式「接入层未做列间恒等式核对，独立测量数不可信（A-105 ④）」。
      **摘要整块缺键**（旧包）视同 `performed = false`——缺证据一侧永远落在禁用侧（A-71/A-82 同向），
      不得把一个未核对的列数当成独立测量数报出去。
19. **`global.fe_*` 是三个并列口径，缺一即丢信息**（A-114，与规则 16 同族）：
    - `fe_rms_counts` = **去均值** RMS（`sqrt(mean((fe-mean(fe))²))`，C4 指标定义 / KB3 §1.1）；
      `fe_p999_counts` = `median` 中心的 0.999 分位；两者都是**波动量**，对纯平移不敏感。
      R-02 的 `fe_p999/fe_rms ≥ 4` 两侧必须同为波动量才成比值——分母若含常偏，有稳态误差的样本
      比值被系统性压低约两个量级、该判据静默漏报，故本条不是口径偏好而是判据正确性。
    - `fe_max_counts` = **原始** `max|fe|`（不减均值）：最坏瞬时误差含常偏，正是要它。
    - `fe_mean_counts` = **原始** `mean(fe)`（有符号）：规则 16 的纪律在此同样成立——
      RMS 减掉的那个常偏**必须有独立载体**，减了不记等于把证据当噪声抹掉。它的消费者是
      KB3 R-22 签名表 ④（触发点系统性偏一个跟随误差的**均值**分量）与 ⑤（回零零点差一整段 ⟹
      **大非零均值**）；两处原句都拿 `fe_rms_counts`/`fe_p999_counts` 去比常偏，口径错位，
      已随 A-114 就地更正。
    - 三条都是全样本量，**没有段级对应物**：`tracking.path_segments[]` 只有 `fe_rms_counts`/
      `fe_max_counts`，任何"某段常值分量"的判据在现有契约下不可编码，**不得**拿全局值冒充段级值
      （A-102：缺载体补载体，不许反推凑数）。
    - null 条件同规则 2：无 `fe`（且 C1 派生规则 1 的两个输入缺一）时三者一律 `null` 并各记一条
      `unavailable`。`fe_mean_counts` 在例 A 里的数值是示意值，**口径**才是本条的内容。
