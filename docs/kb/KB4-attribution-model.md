# KB4 — 故障归因树 + 置信度/证据模型 + 混淆对与证伪设计

本文件是三件事的**唯一登记处**：(1) 症状 → cause slug 的归因树（**已裁口径**，KB0 §6 检查 3：叶子集合 =
KB0 §2 的 22 个 slug，规则 = 到达叶子的**边/门**而非叶子本身；与 KB3 `R-01…R-30`、KB6 `R-31…R-50` 对齐，A-17/D-13）；
(2) `hypotheses[].confidence` 的**确定性**加权公式（即 C3 不可协商规则 3 所指向的"见 KB4 的加权公式"）；
(3) 混淆对的决定性区分判据与「反事实自检」的可判定检查项。

**权威边界**（越界即视为本文档缺陷）：slug/规则号/路径拼写以 **KB0 §1–§3** 为准；特征字段名与算不出的
条件以 **C2 + KB3 §1** 为准；阈值字面量与 `[L]/[P]` 合法性以 **KB3 §2/§3** 为准（本文**只引用规则号**，不自造阈值）；
输出结构以 **C3** 为准；tier/ECE/冻结切分以 **C5** 为准；验证门控以 **C4** 为准；事件词表与同步纪律以 **C6** 为准。

**确定性铁律**：LLM 只能改写 `display_name` / `rationale` / `note` / `verdict.summary` 的**文字**；
`S`、`A_sup`、`A_con`、`C`、`rank`、`severity` 由规则引擎写入（C3 规则 3）。本文不含产品代码（KB0 §6 检查 6）。

---

## 0. 全局不变式（树与模型共用；结构强制，不是口头约定）

`f_b = freq_limits.reliable_band_hz`，`f_N = freq_limits.nyquist_hz`，`τ_u = event_context.sync.uncertainty_ms`（缺失按 5 ms 并记 `audit.assumptions`，KB3 纪律 6）。

| 不变式 | 陈述 | 违反时**唯一**合法动作 |
|---|---|---|
| INV-1 频带门禁 | 任何声明频点的边，其频点必须 `≤ f_b` 且 `f_b ≥` 该规则 `band⊥`（KB3 §2.1） | 该边**剪枝**：`unavailable` 追加 + `freq_limits.blocked_rules ∪= {R-NN}` + `not_evaluable` 登记；禁写"未检出"（C2 规则 7、R-25） |
| INV-2 近奈奎斯特 | `f0 ≥ 0.8·f_N` 的候选一律先过 R-10 伪峰支 | 未经 R-10 排除不得进入 `mechanical_*` 叶 |
| INV-3 **顺序判据** | 共置测量构型的两惯量系统：`antiresonance_freq_hz < freq_hz` 是**必要条件**（极点/零点交替；KB3 R-04 / KB5 §1.2），且比值服从 `f_res / f_anti = sqrt(1 + λ)`（C2 规则 9；C2 示例 A 为 `440 / 1181`，λ≈6.2 ⟹ 比值 ≈ 2.68）。顺序期望由 `meta.sensor_config` 的**四值** `{motor_side, load_side, mixed, unknown}` 决定（C1 派生规则 7；A-1 立三值，**A-68 增第四值 `mixed`**） | `f_a > f_0` ⟹ **拒绝**双惯量配对，转 R-10 伪谷支 + 把该组合写入 `contradicting_evidence`；**`unknown`（不知道传感器装在哪侧）与 `mixed`（已知本曲线的峰与谷来自两套通道、不是同一传递函数的响应）行为一致**：顺序项一律**不参与判定**、双惯性配对置信度**封顶**（C1 派生规则 7、C2 规则 9、A-68）。两者**只差记录的原因**：`unknown` = 构型未知；`mixed` = 构型已知且**已知零极点交替信息不存在**（峰谷跨两套通道），所以 `mixed` 不是"待查"而是"这条曲线天生不带顺序证据"，不得再靠 `assumptions` 补。**逐通道落点**：C1 `meta.channels.<pos_channel>.sensor_side ∈ {motor, load, unspecified}`（A-68）——`mixed` 应能由两条 pos 通道的 `sensor_side` 取值直接解释。`f_a > f_m` 的解释权：`mixed` ⟹ 归"非共置拼接"（已成立），`unknown` ⟹ 归陷波伪谷/混叠（KB3 R-04 反向情形清单）。**KB5 原先"混合构型临时写 `unknown` + `assumptions`"的处置已作废**（A-68） |
| INV-4 null ≠ false ≠ 0 | 边判据任一依赖为 null ⟹ 该边不可通行 | `rules_skipped += {rule_id, reason:"dependency_null:<path>"}`；若该边是唯一通路 ⟹ 该叶进 `not_evaluable` |
| INV-5 因果开关 | `causal_claims_permitted == false` ⟹ `software_induced_*` 7 叶全部不可达 | 降级为共现观察（写 `considered` + note "时钟未对齐，共现不等于因果"）+ 全族登记 `not_evaluable`（C2 规则 8） |
| INV-6 事件可用性 | `event_context.available == false` ⟹ 软件族叶不可达 | 逐条登记 `not_evaluable`（R-30，措辞取 C6 §4）+ `overall_confidence` 按 CAP-2 下调 |
| INV-7 时基分辨 | 尖峰-事件对齐类边要求 `1/fs ≤ τ_u/2`（R-18 必要上下文） | 该边剪枝，`rules_skipped` 写 `reason:"time_resolution"`；**不得**放宽对齐窗 |
| INV-8 分段前置 | 每条边的 `seg=` 前置必须在 `segment_coverage` 有对应计数 ≥ 该规则下限 | 该边不可通行 + `unavailable` 追加 `reason:"segment_absent:<kind>"`；缺失语义按 INV-4 |
| INV-9 估计类降级 | 依赖 `bandwidth.*` 的结论置信**恒 ≤ 0.6**（KB3 §1.10 锁定） | CAP-1 封顶；`basis` 不得为 `simulation_validated`（无 V* 时） |
| INV-10 归因下限 | 进 `hypotheses[]` 的叶须 ≥2 条 `supporting_evidence`（C3 规则 1） | 移入 `considered`；数量不足是**结构违规**，不得靠补弱证据凑数 |
| INV-11 无"未发现" | 不可观测只允许表述为 `not_evaluable` 条目 | 见 C3 规则 9；`not_evaluable` 为空须真的全部可评估 |
| INV-12 不写设备 | 任何叶的动作都是"写入建议 + 离线仿真 + 人工审批" | `safety.writes_to_device` 恒 `false`（C3 规则 6） |
| INV-13 **措辞 ≤ 证据等级**（A-31，C3 规则 14） | 叙述层（`verdict.summary` / `rationale` / `display_name` / `note`）的措辞强度**不得高于**该结论 `audit` 里登记的 `source_tier`；本文所有"现场/手册/实测"级表述只在 T1（C5 §1）证据上才允许 | 出现「已核对 / 已验证 / 现场确认 / 手册原文确认 / 实测通过」而 `source_tier < T1` ⟹ **拒绝出报告**（不是降级成一句 disclaimer）；详见 §2.10 |
| INV-14 **百分比判据的分母纪律**（A-70） | 凡本文件出现的转矩刻度类百分比量（`cur_q_rms_pct`、`cur_q_peak_abs_pct`、`cur_q_saturation_ratio`、任何"饱和/余量比"阈值），其分母必须来自 C1 `meta.drive.rated_torque_N_m` 且 `meta.drive.rated_torque_source ∈ {measured, manual, nameplate, assumed}`。运动学百分比（`overshoot_pct`、`settle_band_pct_of_move`）分母是 `move_amplitude`，**不受**本条约束 | `assumed` ⟹ 该判据的 `source_tier` **封顶 T2** + caveats 必写原文"额定转矩为假定值，百分比类判据的绝对刻度不可信"（§2.5 CAP 表与 §2.9 证据表须同步标注）；`rated_torque_N_m == null` ⟹ `*_pct` 恒 `null` ⟹ 按 INV-4 该边不可通行，**只允许走 `N_m` 绝对值支路** |
| INV-15 **能力声明真空**（A-64/A-65） | `mechanical_thermal_drift`（叶 8 / R-01）、`electrical_motor_heating`（叶 14 / R-16）与 **kHz 量级共振 / 电流环带宽**类判据（叶 1 / R-03·R-04、叶 9 kHz 支 / R-11、叶 10 / R-12）**在 T1-a 上没有正例来源**：T1-a `fs = 1 kHz` ⟹ 奈奎斯特 500 Hz ⟹ `reliable_band_hz = 400 Hz`（kHz 判据在数据层面不可达）；热族另缺 `temp` 通道与冷/热机配对样本。这几条**只有 T2 文献正当性** | 报告侧一律 `unavailable` + `freq_limits.blocked_rules` / `not_evaluable` 登记（INV-1/INV-11）；**禁止**输出"未发现谐振 / 未发现异常 / 无热漂移 / 带宽充足"；命中率/能力主张**不得**引 T1-a，以 T3 合成作能力证据者一律降级为**"管线跑通（合成自洽）"**级主张（A-64，见 §2.6/§4.4） |
| INV-16 **门/边只产登记义务**（A-51） | `R-25/26/27/28/29/30`（KB3）与 `R-37/49/50`（KB6）是 `family: null` 的**边与门**：它们写入的是 `audit.rules_fired` + `differential.not_evaluable`（计入 C5 拒答正确率），**永不进 `hypotheses`**，也不参与 §2.2 加权 | 登记键式二选一并按粒度同时给：**族级** `{"family": <族名或 `software_induced_error`>, "why": …}`、**逐模式** `{"fault_mode": <KB0 §2 slug>, "why": …}`（C3 另要求 `blocked_by` 稳定键名，C3 规则 16/A-73）；`software_induced_error` **禁入** `fault_mode` 键（A-18/A-19）。凡本文把门/边写成"产出假设"的句子都是缺陷，须按本条改 |

---

# 第一部分 — 故障归因树

## 1.1 叶集合与规则锚点（无孤儿叶子检查表）

22 个叶 = KB0 §2 全部 slug。每叶有 KB3 主锚点；KB6（`R-31…R-50`）给出**同一 slug** 在耦合寻光/标定语境（`scanning`/`curing`/残差场）下的交叉锚点。仲裁与元规则不产叶。

| # | 叶（slug） | KB3 主锚点 | KB6 交叉锚点 | `band⊥` | 主要分段前置 |
|---|---|---|---|---|---|
| 1 | `mechanical_resonance` | R-03, R-04, R-10(证伪支), R-25(元) | R-36 | 2000 Hz | `dwell≥1`,`rest≥1`,`move≥4`；**T1-a 无正例来源（INV-15 / A-64/A-65）：`band⊥ = 2000 Hz` > 本项目 `f_b = 400 Hz` ⟹ 在 T1-a 上此叶只能由 INV-1 剪枝，产物是 `unavailable` + `blocked_rules`，禁写"未发现谐振"；低频双惯性另有叶 2（`mechanical_double_inertia` / R-09，`band⊥ = 150 Hz`）可达** |
| 2 | `mechanical_double_inertia` | R-09 | R-36 | 150 Hz | `probing`/`move`，`vel_fb` 或 `fe` 代理 |
| 3 | `mechanical_backlash` | R-08, R-27(仲裁) | R-32 | 50 Hz | `move≥2` 含反向 |
| 4 | `mechanical_friction_stiction` | R-06 | R-39 | 50 Hz | `move≥3` 完整起步+恒速区 |
| 5 | `mechanical_crawling` | R-05 | R-39 | 20 Hz | 低速段 ≥1，时长 ≥2 s |
| 6 | `mechanical_encoder_periodic_error` | R-07 | R-40 | 20 Hz 且 `k·f_rev ≤ f_b` | `probing` ≥2 整转 |
| 7 | `mechanical_loose_structure` | R-02 | R-35, R-44, R-46 | 100 Hz | `move≥4` 含正反 |
| 8 | `mechanical_thermal_drift` | R-01 | R-33, R-43, R-48 | n/a（时域） | `dwell+rest≥2`，跨度 ≥20 min，需 `temp`；**T1-a 无正例来源（INV-15 / A-64）：本样本无 `temp`、无冷/热机配对 ⟹ 只能 `not_evaluable`，禁写"无热漂移"（C2 例 A 的 `unavailable` 条目即此）** |
| 9 | `electrical_torque_ripple` | R-11 | — | 150 Hz；kHz 支 2000 Hz | `rest≥1`,`dwell≥1` |
| 10 | `electrical_current_loop_bandwidth` | R-12 | — | 200 Hz | `probing`（`correlated_with_cur_q`） |
| 11 | `electrical_velocity_pi_detune` | R-13 | — | 100 Hz | `settling≥3` |
| 12 | `electrical_position_pi_detune` | R-14 | — | 100 Hz | `dwell/rest` 累计 ≥2 s |
| 13 | `electrical_feedforward_mismatch` | R-15, R-26(仲裁) | — | n/a（`fs ≥ 500 Hz`） | `move≥3`，加/减速样本各 ≥50 |
| 14 | `electrical_motor_heating` | R-16 | R-48 | n/a（时域） | 冷/热机配对样本 |
| 15 | `electrical_resolution_quantization` | R-17 | R-38 | n/a | `settling≥1` |
| 16 | `software_induced_host_thread_jitter` | R-18, R-28(仲裁), R-30(元) | — | `fs≥1 kHz` 且 `1/fs ≤ τ_u/2` | `move≥1` + host 事件 |
| 17 | `software_induced_interp_buffer_underrun` | R-19, R-28 | — | 软件族（下限 `fs ≥ 500 Hz`） | `path≥1` + interp 事件 |
| 18 | `software_induced_bus_cycle_miss` | R-20, R-28 | R-41 | `fs ≥ 2×` 总线周期 | network 事件；**可达性另受 §1.3 N6.c 三条件 + CAP-11 约束**（A-45） |
| 19 | `software_induced_late_vision_result` | R-21 | R-34 | 同软件族 | `vision≥20` + `step_labels` |
| 20 | `software_induced_pulse_eq_overwritten` | R-22, R-27 | R-45, R-47 | n/a | `step_labels.recipe` ≥2 组 |
| 21 | `software_induced_settle_window_too_short` | R-23, R-29(衍生) | R-42 | n/a（`fs ≥ 200 Hz`） | `settling≥3` + `move_started/done` |
| 22 | `software_induced_polling_latency` | R-24 | R-31 | n/a（`fs ≥ 200 Hz`） | `motion ≥ 10` 事件 |

非叶：`R-25`（频带不可见元规则）、`R-26`/`R-27`/`R-28`（有序仲裁器）、`R-29`（节拍衍生）、`R-30`（软件族登记义务）、KB6 `R-37`/`R-49`/`R-50`（门禁 `family: null`，A-17；其分数只进 `differential`，KB6 §G-2）。这九条**都是边或门**：它们的输出是"剪枝 / 择优 / 登记义务 / 封顶"，永远不产生 `hypotheses[].fault_mode`（KB0 §6 检查 3 已裁口径，D-13 → A-17）。

**slug / `display_name` 分工（A-19，D-8 已收口）**：本文所有出现在 `hypotheses[].fault_mode`、
`ruled_out_alternatives[].fault_mode` 与树正文 `LEAF(...)` 位置的名字，**一律是 KB0 §2 的 22 个 slug 之一**；
自由文本显示名只允许出现在 `display_name` 与 `differential.considered`（C3 规则 10）。
C3 示例早期写法的对应关系（供核对，旧名不得再进 `fault_mode`）：
`feedforward_mismatch` → `electrical_feedforward_mismatch`；`friction_crawling` → `mechanical_crawling`
（静摩擦另计 `mechanical_friction_stiction`）；`encoder_eccentricity` → `mechanical_encoder_periodic_error`；
`thermal_drift` → `mechanical_thermal_drift`；`gain_too_high_hunting` / `limit_cycle` → `electrical_position_pi_detune`
（自激/极限环是其签名）；`following_error Compensation`（含空格/大写）在 22 个 slug 中**无对应项**，
它至多是 `electrical_feedforward_mismatch` 的显示名，且必须作为 `considered` 文本出现。

## 1.2 根节点：按 C2 顶层块分诊

`inputs.context_complaint` 只用于 `verdict.summary` 措辞，**不参与路由**。一个样本可同入多根（多故障叠加是
C5 §2 `difficulty` 的显式类别）；各根之间**不合并**证据——同一特征在不同根下按其上下文前提重新解读（§1.4）。

```
N1 global.fe_rms_counts 高（误差预算整体超支）
N2 ff_mismatch.* 或 global.reversal_error_counts 非 null 且高（瞬态集中于加减速/反向）
N3 resonance.candidates 非空 或 spectral.*.tonality_index ≥ 0.6（窄带谱峰存在）
N4 step_response[].limit_cycle_present ≠ false 或 thermal_drift 非 null（静止/保持期异常）
N5 ripple.probing 非空 或 crawling.low_speed_segments 非空（恒速/低速纹理）
N6 event_context.fe_spike_count ≥ 3（离散尖峰 ⟹ 软件族唯一入口）
N7 step_response[].settling_time_ms 非 null 且大（到位/节拍不达标）
N8 误差-行程回归斜率 或 recipe 间偏差阶跃（尺度/标定异常；需 step_labels）
```

## 1.3 树正文

记法：`─[边] 判据 · seg=… · band=… · evt=…`；`⇒ LEAF(slug, R-NN)`；`⊘` = 该边不可通行时的处置；阈值写成 `R-NN#k`，值是 KB3 原文（`[L]` 文献可证 / `[P]` 本项目自定）。

```
N1 误差预算整体超支
│ 进入：global.fe_rms_counts 非 null 且 ≥ 同批基线中位；前置 present_channels ⊇ {pos_cmd,pos_fb,fe}
│
├─[N1.a ∧N3] 窄带峰存在
│  ├─[N1.a.1] band= f_b ≥ 2000（R-03#前置，需 fs ≥ 8 kHz）
│  │  ├─ freq_hz ∈ [1000,6000] ∧ coherence_torque_velocity ≥ 0.7 ∧ amplitude_ratio_vs_broadband ≥ 4 ∧ quality_factor_estimate ≥ 10
│  │  │  · seg= dwell≥1,rest≥1,move≥4
│  │  │  ├─ 再核布尔三件 present_in_dwell==true ∧ present_in_rest==false ∧ tracks_command_frequency==false
│  │  │  │     · C2 规则 6：三布尔+相干缺一不可 ⇒ LEAF(mechanical_resonance, R-03)
│  │  │  └─ 任一为 null ⇒ CAP-3 封顶 0.55，不得用其余三项替代（KB3 §1.3 末段）
│  │  ├─ 峰谷成对：另加 antiresonance_freq_hz < freq_hz（INV-3 必要）∧ freq_hz/antiresonance_freq_hz ∈ [1.05,2.7]
│  │  │  ∧ (freq_hz−antiresonance_freq_hz) ≥ 2·resonance.resolution_hz ∧ is_double_inertia_pair==true ∧ 峰/谷 ≥ 6 dB
│  │  │  ⇒ LEAF(mechanical_resonance, R-04) ← kHz 双惯性仍归 resonance 族（KB3 family 锁定）
│  │  │  ⊘ notch_filters 覆盖 antiresonance_freq_hz ⇒ 谷是滤波造成的 ⇒ R-04 **否决**（非扣分）
│  │  └─ 否决支 R-10：present_in_rest==true ∨ tracks_command_frequency==true ∨ freq_hz ≥ 0.8·f_N（INV-2）
│  │     ∨ notch_filters 覆盖 freq_hz ∨ (fe_sign_change_rate_hz ≥ 0.4·fs ∧ spectral.fe.tonality_index ≥ 0.6)
│  │     ⇒ 判"伪峰"，阻断 R-03，改路由 N3 电气/观测层
│  │  ⊘ 若 f_b < 2000：整支剪枝 ⇒ blocked_rules ∪= {"R-03","R-04"} + not_evaluable{mechanical_resonance,
│  │     why:"fs 不足，该频段无信息（不代表不存在）"}（R-25 原文措辞，禁写"未发现共振"）
│  └─[N1.a.2] band= f_b ≥ 150 ∧ 150 ≤ freq_hz ≤ f_b（R-09#1,#2）
│     ├─ is_double_inertia_pair==true ∧ antiresonance_freq_hz < freq_hz（INV-3）∧ 比值 ∈ [1.1,2.0]
│     │  ∧ 相干 ≥ 0.7 ∧ 峰/宽带 ≥ 4 · seg= probing/move ⇒ LEAF(mechanical_double_inertia, R-09)
│     │  ⊘ meta.drive.inertia_ratio == null ⇒ 降级 unverified，不得进 verdict.primary（KB3 纪律 3，CAP-6）
│     └─ 电气竞争：spectral.cur_q.tonality_index ≥ 0.6 ∧ harmonic_ratios 全整/半整数 ⇒ N3 叶 9
│
├─[N1.b ∧N6] 尖峰型：fe_p999_counts/fe_rms_counts ≥ 4 ∧ reversal_error_counts ≥ 3·fe_rms
│  ∧ spectral.fe.tonality_index ≤ 0.5（R-02#2,#1,#4）· seg= move≥4 含正反
│  ⇒ LEAF(mechanical_loose_structure, R-02)；evt 可用时先走 N6（软件族按事件源独占性优先）
│
└─[N1.c] 无峰无尖峰，误差"每转重复"
   ├─ per_rev_periodic_present==true ∧ phase_locked_to_pos_modulo==true
   │  ∧ per_rev_amplitude_counts ≥ 0.2·fe_rms_counts ∧ detrended_r2 ≥ 0.5（R-07）· band= k·f_rev ≤ f_b
   │  · seg= probing ≥2 整转 ⇒ LEAF(mechanical_encoder_periodic_error, R-07)
   │  ⊘ CPR==null ∨ 转数<2 ⇒ unavailable + not_evaluable（KB3 R-07 备注：禁写"无编码器误差"）
   └─ tonality_index ≤ 0.25 ∧ fe_sign_change_rate_hz ≥ 0.25·fs（R-17）
      ⇒ LEAF(electrical_resolution_quantization, R-17)

N2 瞬态集中
│ 进入：ff_mismatch.asymmetry_ratio 或 reversal_error_counts 非 null
│ 前置：`quality_ref.dt_jitter_ratio ≤ 0.05`（否则 `ff_mismatch.*` 为 null，INV-4；A-49 已把该量由 C1
│ `meta.quality` 镜像进 C2 `quality_ref`，证据路径走 C2，R-5 由此收口）；方向符号已修正（KB3 纪律 9）
│
├─[N2.a] asymmetry_ratio ≥ 1.5（R-15#1）∧ fe_vs_accel_corr ≥ 0.6 ∧ residual_slope_vs_jerk_corr ≤ 0.6
│        ∧ damping_ratio_estimate ≥ 0.5 ∧ ¬(friction_stiction_ratio ≥ 1.5) ∧ ¬(backlash_estimate ≥ 3·fe_rms)
│   ⇒ 交 **R-26 有序仲裁**（不直接成叶）：① present_in_rest==true ⇒ 转 N3 电气/伪峰；② present_in_dwell==true
│     ∧ 相干≥0.7 ∧ asymmetry<1.5 ⇒ mechanical_resonance（按频带走 R-03/R-09）；③ present_in_rest==false ∧
│     present_in_dwell==false ∧ asymmetry≥1.5 ⇒ LEAF(electrical_feedforward_mismatch, R-15)；④ ②③同成立 ⇒
│     谐振 primary、前馈 rank2 且互相写入对方 contradicting_evidence；⑤ present_in_rest==null ⇒ 双方 CAP-3 = 0.55
│   ├─ 竞争支：asymmetry_ratio ∈ [0.9,1.2]（滞后对称，R-12 支路B）∧ fe_vs_accel_corr ≥ 0.6
│   │  ∧ cur_q.tonality_index ≤ 0.3 ∧ correlated_with_cur_q ≥ 0.7
│   │  ⇒ LEAF(electrical_current_loop_bandwidth, R-12-B)；⊘ drive.* 缺失 ⇒ 一律 unverified + CAP-6
│   └─ 支路A（有 drive.*）：current_loop_bandwidth_hz < 10·velocity_loop_gain_hz 被违反 ⇒ 同叶（R-12#A）
│
├─[N2.b] 偏差只在**反向**时刻重现
│   ├─ backlash_estimate_counts ≥ 3·fe_rms ∧ reversal_error_counts ≥ 3·fe_rms ∧ 跨反向 CV ≤ 0.3
│   │  ∧ 平台条件 abs(db_i/dt) < 0.1·vel_mean（KB3 §1.1）· seg= move≥2 含反向
│   │   ⇒ **R-27 仲裁**：IF abs(β) ≥ 0.002（误差/行程斜率）∧ 偏差随 recipe 阶跃 ≥ 3·σ_err（R-22#1,#6）
│   │     ⇒ LEAF(software_induced_pulse_eq_overwritten, R-22)；ELIF 仅反向后出现 ∧ 与行程无关 ∧ CV ≤ 0.3
│   │     ⇒ LEAF(mechanical_backlash, R-08)；ELSE ⇒ 二者均不入 hypotheses，只进 differential.considered
│   │   ⊘ 两者互斥执行：同一证据不得既开机械工单又开数据治理工单（R-27 建议动作原文）
│   └─ 尖峰幅值 CV > 0.4 ∧ fe_p999/fe_rms ≥ 4 ∧ 无平台 ⇒ LEAF(mechanical_loose_structure, R-02)
│
└─[N2.c] 起步瞬间转矩峰（非全程不对称）
    ├─ friction_stiction_ratio ≥ 1.5 ∧ 起步窗内 abs(cur_q) 峰 ≥ 2·cur_q_rms_pct
    │  ∧ fe_vs_accel_corr ≤ 0.5 ∧ cur_q_peak_abs_pct < 90（R-06）· seg= move≥3 含 ≥50 ms 静止前置
    │  ⇒ LEAF(mechanical_friction_stiction, R-06)（时刻语义：起动 vs 反向，R-06 排除项）
    └─ cur_q_peak_abs_pct ≥ 90 ∨ cur_q_saturation_ratio 高 ⇒ 先判限流/R-12，不得先判摩擦

N3 窄带谱峰的电气/观测层落点（INV-2 与 R-10 否决后的去向）
├─ cur_q.dominant_freq_hz ∈ [f_min,f_b] ∧ tonality_index ≥ 0.6 ∧ dominant_psd_ratio ≥ 0.30
│  ∧ harmonic_ratios 全整/半整数 ±5% ∧ (present_in_rest==true ∨ 相干 < 0.7)
│  ∧ correlated_with_cur_q ≤ 0.5（机械侧未响应）· band= 低频 150 / kHz 支 2000（否则只能 blocked）
│  ⇒ LEAF(electrical_torque_ripple, R-11)；⊘ harmonic_ratios==null ⇒ 放弃（null ≠ "无谐波"）
├─ phase_margin_deg < 45 ∧ gain_margin_db ≥ 6 ∧ damping_ratio_estimate ≤ 0.2 ∧ ringing ≥ 5
│  ∧ resonance.candidates[].freq_hz < 100（R-13）· seg= settling≥3
│  ⇒ LEAF(electrical_velocity_pi_detune, R-13)；⚠ CAP-1（bandwidth 在链上，恒 ≤ 0.6）
│  ⊘ gain_margin_db < 6 ⇒ 转 R-14 支，动作改降增益；⊘ arg L 无 −180° 穿越 ⇒ 裕度 null，**不得**报"裕度足够"
└─ limit_cycle_present==true ∧ limit_cycle_freq_hz ∈ [20,f_b]
   ∧ abs(limit_cycle_freq_hz/f_pos − 1) ≤ 0.5 ∧ limit_cycle_amplitude_counts ≥ 0.5·settle_band_counts
   ∧ (crawling 为空 ∨ is_sawtooth==false)（R-14）⇒ LEAF(electrical_position_pi_detune, R-14)

N4 静止/保持期异常（dwell / rest 语义主导）
├─ abs(thermal_drift_counts_per_min) ≥ 2.0 ∧ thermal_fe_correlation_r ≥ 0.6 ∧ dwell+rest ≥ 2
│  ∧ 漂移起始后无新谐振峰（R-01）· seg= 累计 ≥120 s、跨度 ≥20 min · 需 temp 通道
│  ⇒ LEAF(mechanical_thermal_drift, R-01)
│  ⊘ temp 缺失 ⇒ thermal_fe_correlation_r null ⇒ not_evaluable{mechanical_thermal_drift, why:"缺 temp 通道，且无冷热机对比"}（禁写"无热漂移"）
├─ abs(drift) < 2.0 ∧ 冷热机配对 cur_q_rms_pct 单调升 ≥15% ∧ saturation_ratio ≥ 0.02
│  ∧ overshoot_pct 随温度下降（R-16）⇒ LEAF(electrical_motor_heating, R-16)
│  （R-01 与 R-16 可同成立 ⇒ R-01 primary、R-16 rank2，rationale 写耦合方向）
└─ settling_time_ms==null ∧ limit_cycle_present==true ⇒ 回 N3 的 R-14（真自激，永不入带）
   settling_time_ms!=null ∧ median(settling_time_ms) ≥ 1.2×(t_done − t_start) ∧ ringing ≥ 2
   ∧ 到位时刻 abs(fe) ≥ settle_band_counts（R-23）
   ⇒ LEAF(software_induced_settle_window_too_short, R-23)（须过 §1.5 软件门）

N5 恒速/低速纹理
├─ low_speed_segments 非空 ∧ is_sawtooth==true ∧ vel_min_ratio ≤ 0.15 ∧ stall_count ≥ 1
│  ∧ sawtooth_freq_hz ∈ [0.1, min(50,f_b)] ∧ abs(corr_vel_vs_curq) ≥ 0.6
│  ∧ per_rev_periodic_present==false ∧ 跨速度段 sawtooth_freq_hz CV ≤ 0.3（频率近常数，R-05）
│  ⇒ LEAF(mechanical_crawling, R-05)；⊘ 方向符号未修正 ⇒ 锯齿语义不成立 ⇒ 放弃（纪律 9），不是"无爬行"
└─ ripple.probing 非空（probing ≥1 且 ≥2 整转）
   ├─ 阶次 k 与 CPR 成整分数 ∧ 相位锁定 ⇒ 叶 6（R-07）
   ├─ correlated_with_cur_q ≥ 0.7 ∧ 无固定阶次 ⇒ 叶 10/11（R-12-B / R-13）
   └─ ripple_over_velocity_pct_per_rev 随速度非单调 ⇒ 转 N4

N6 离散尖峰 —— 软件族唯一入口
│ 门（全必查）：G1 available==true ∧ G2 causal_claims_permitted==true ∧ G3 对齐窗 > τ_u 且
│ alignment_residual_ms ≤ τ_u（A-82：残差在不确定度预算内才算同步可信）∧ G4 sync.verified==true ∧ sync.method ∈ {trigger_edge, ntp}
│ ∧ G5 fs ≥ 1 kHz ∧ 1/fs ≤ τ_u/2
├─[N6.a] fe_spike_count ≥ 3 ∧ fe_spike_aligned_to_host_pause/fe_spike_count ≥ 0.7
│        ∧ host_pause_max_ms ≥ 20 ∧ host_pause_max_ms ≥ 5·位置环周期 ∧ alignment_residual_ms ≤ τ_u
│        ∧ present_in_dwell==false ∧ asymmetry_ratio < 1.5（R-18）
│        ⇒ LEAF(software_induced_host_thread_jitter, R-18)；⊘ `host_pause_count` **不新增**（A-8：
│        C6 侧已停止引用），计数一律改用 C2 的 `event_context.n_by_source.host`
│        ⇒ 计数用 n_by_source.host ≥ 1 ∧ host_pause_max_ms
├─[N6.b] interp_underrun_during_path/interp_underrun_count ≥ 0.7
│        ∧ fe_spike_aligned_to_underrun/fe_spike_count ≥ 0.5 ∧ path.fe_max ≥ 2.0·path.fe_rms
│        ∧ corr_fe_vs_accel ≥ 0.7 ∧ corr_fe_vs_jerk < corr_fe_vs_accel · seg= path ≥ 1（R-19）
│        ⇒ LEAF(software_induced_interp_buffer_underrun, R-19)
├─[N6.c] network_cycle_miss_count ≥ 1 ∧ n_alarm ≥ 1 ∧ quality_ref.dt_jitter_ratio ≤ 0.05（R-20；A-49：走 C2 镜像路径）
│        ⇒ LEAF(software_induced_bus_cycle_miss, R-20)
│        **升级三条件（A-45，D-6 已收口；原"C2 无专属特征"缺口已由 A-9 补齐）**：
│        ① `event_context.bus_cycle_hold_max_ms` 与 `event_context.fe_spike_aligned_to_network_miss` 均非 null；
│        ② `event_context.sync.verified == true` 且 `event_context.causal_claims_permitted == true`；
│        ③ 对齐残差在不确定度预算之内，即 `event_context.alignment_residual_ms ≤ event_context.sync.uncertainty_ms`
│        （**A-82 更正 A-50 的方向**，本条与本文 N6.a/N6.e/G3/CAP-8 与 C2 规则 8 现已同向；
│         A-45 原文的 `>` 会写成"对齐越差越允许归因"，物理上不成立。本文不再需要"上限取 min"
│         的临时补丁：③ 与 CAP-8 是同一条件的两面，CAP-11 的 0.60 与 CAP-8 的 0.40 不会同时触发。）
│        三条**同时**成立 ⇒ 本叶可进 `hypotheses[]`，但 `confidence` 受 **CAP-11** 封顶 **0.60**
│        （`pos_cmd` 单通道推断，无驱动器 WKC/DC 逐周期通道，结构上不可能更自信）；
│        缺任一 ⇒ **停在共现级**：禁入 `hypotheses[]`，只进 `differential.considered`
│        + note "丢周期与尖峰同窗，但保持时长/对齐残差不足以排除时基本身不稳"
│        ⊘ `bus_cycle_hold_max_ms == null` ⇒ INV-4 生效，`rules_skipped += {R-20, reason:"dependency_null:..."}`
├─[N6.d] vision_result_latency_p95_ms ≥ 20 ∧ n_by_source.vision ≥ 20 ∧ vision/n_events ≥ 0.1
│        ∧ 该步 path.fe_max ≥ 2.0·fe_rms ∧ 误差阶跃与该步 vision/result **对齐**（`abs(Δt) ≤ max(τ_u, 2 ms)`；
│         本叶要 > τ_u 的是 `vision_result_latency_p95_ms` 这个被声称的时延，不是对齐残差，A-82/R-21）（R-21）
│        ⇒ LEAF(software_induced_late_vision_result, R-21)
└─[N6.e] 族内择优仲裁 R-28：s_host = aligned_to_host_pause/fe_spike_count，s_intp = aligned_to_underrun/
         fe_spike_count，s_net = fe_spike_aligned_to_network_miss/fe_spike_count（A-9 已落 C2，
         **参与择优**，但其命中受 CAP-11 封顶），s_vision = fe_spike_aligned_to_vision_result/fe_spike_count
         成立 ⟺ max ≥ 0.5 ∧ (max − second) ≥ 0.2 ∧ alignment_residual_ms ≤ τ_u ∧ permitted==true
         否则 ⇒ 全族候选进 considered + not_evaluable{family:"software_induced_error", why:"对齐区分度不足"}
         同一尖峰集合不得同时归因多个软件成因（R-28 断言）

N7 到位/节拍
├─ n_by_source.motion ≥ 10 ∧ T_poll = median(diff(t_motion)) 的 CV ≤ 0.2
│  ∧ 到位时刻散布 std(t_done − t_enter) ≥ 0.5·T_poll ∧ 额外位移 ≈ T_poll × vel（以 counts 表述）
│  ∧ ¬(R-23 成立且主因是窗口过短)（R-24）⇒ LEAF(software_induced_polling_latency, R-24)
│  （R-23 与 R-24 同成立 ⇒ 判定链路整体不健康 ⇒ 合并成一条建议）
└─ median(settling_time_ms) ≥ 1.2·t_s_min，t_s_min = 4/(ζ·ωn)，ωn = 2π·f_pos（R-29，衍生不判故障）
   ⇒ 因 ωn 来自 bandwidth ⇒ 结论上限 unverified（CAP-1）；在 T1-a 上不可评估 ⟹ not_evaluable

N8 尺度/标定
├─ step_labels 非空 ∧ abs(β) ≥ 0.002 ∧ 同一 step 重复定位散布 ≤ 3·量化台阶 ∧ 偏差随 recipe 阶跃 ≥ 3·σ_err
│  ∧ per_rev_periodic_present==false ∧ backlash_estimate_counts ≤ fe_rms_counts（R-22）
│  ⇒ LEAF(software_induced_pulse_eq_overwritten, R-22)（与 N2.b 的 R-27 同一条链，**不得重复计权**）
│  ⊘ 无 recipe ⇒ 退化为 R-08 单独判据 + audit.assumptions 记录退化（R-27 适用边界，不得静默）
└─ KB6 交叉锚点（同 slug）：R-45/R-47→叶20；R-46/R-44→叶7；R-43/R-48→叶8；R-31→叶22；R-32→叶3；
   R-33→叶8；R-34→叶19；R-35→叶7；R-36→叶1/2；R-38→叶15；R-39→叶5；R-40→叶6；R-41→叶18；R-42→叶21；
   R-37/R-49/R-50 是门禁（`family: null`，A-17）⇒ 只影响 differential/not_evaluable，不进 hypotheses[]
```

## 1.4 分段上下文翻转：同一特征值在不同 `kind` 下的不同解读

引擎求值任何边之前必须先解析窗口 `kind` 与 `segment_coverage`；**同一数值跨 kind 不可复用为同一条证据**。

| # | 特征 + 值 | 在 A kind 下 | 在 B kind 下 | 机制/后果 |
|---|---|---|---|---|
| F1 | `tracking.path_segments[].fe_max_counts` = 3100 | `path`（插补连续路径）：突进签名 ⟹ N6.b（R-19 欠载，配 `interp` 事件） | `homing`：撞限位/压缩是**设计使然** ⟹ 不作故障证据 | 只有 `path` 段内 `fe_max ≥ 2.0·fe_rms` 才是欠载签名；误用会把正常回零判成软件故障 |
| F2 | `spectral.cur_q.dominant_freq_hz` = 1181，`tonality_index` = 0.71 | `dwell`（指令恒定、闭环保持）仍在 ⟹ `present_in_dwell==true` ⟹ 结构模态（R-03） | `rest`（使能关闭）仍在 ⟹ `present_in_rest==true` ⟹ 伪峰/电气（R-10/R-11），阻断 R-03 | 靠的是**哪种静止**：`dwell` 仍有保持力、`rest` 驱动器不出力（KB3 §1.3 两行定义严格分开） |
| F3 | `step_response[].limit_cycle_present == true` | `dwell/rest`：频率 ≈ `f_pos` 且幅值 ≥ 0.5·`settle_band_counts` ⟹ R-14 自激 | `settling`：`settling_time_ms == null`（从未入带）才算 R-14；"再等一会就进带" ⟹ R-23 | 区分量是**是否会终归进带**（R-23 排除项原文）；混用会把判定错误报成自激并建议无谓降增益 |
| F4 | `global.reversal_error_counts ≥ 3·fe_rms` | `move` 含方向翻转对（`move≥2`）⟹ R-08 间隙 / R-02 松动（看 CV 与平台） | `probing` 恒速：无反向语义 ⟹ 该特征 null（INV-4），只能走 N5 | 无反向对时该字段算不出；把 0 当"无间隙"违反 C2 规则 2 ⟹ 禁写"未发现间隙" |
| F5 | `vision_result_latency_p95_ms` = 31.2 | `step_labels` 含视觉步骤（`flux_inspect`/`verify`）且 `vision/n_events ≥ 0.1` ⟹ R-21 | `curing`/`scanning` 等无视觉步骤：延迟与运动无时间耦合 ⟹ 只记录不归因 | R-21 排除项：必须能画出"视觉时间线 vs 运动时间线" |
| F6 | `crawling.low_speed_segments` 非空（`vel_mean ≈ 120 counts/s`，锯齿 true） | `move`（工艺定位运动）中的低速 ⟹ R-05 爬行 | `homing`/`scanning`：低速寻零/步进是**控制策略** ⟹ 不构成爬行 | `v_ls` 入选阈值只在 `move/probing` 有意义（KB3 §1.5 已限定 kind） |
| F7 | `thermal_drift_counts_per_min` = 3.1 | `dwell+rest` 累计 ≥120 s、跨度 ≥20 min ⟹ R-01 可判 | `move/path` 为主：漂移被运动瞬态淹没 ⟹ 该叶 `not_evaluable`（"静止样本不足"） | 定义本身要求 kind（KB3 §1.1 该行） |

补充：`segment_coverage.probing == 0` 时 `ripple.probing` 必须为空数组（KB3 §1.4）；反之数组非空而覆盖为 0 ⟹ C2 输出自相矛盾 ⟹ 解析层缺陷，整样本拒诊断（KB3 §1.14 精神）。

## 1.5 `software_induced_*` 的进入与**退出**条件

进入（AND 全部）：`G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5`（§1.3 N6 门）∧ 该叶自身的事件源计数与形态条件。
退出（三分支穷尽；不存在"悬而未判"）：

| 情形 | 唯一合法输出形态 | 依据 |
|---|---|---|
| E1 `available == false` | 7 个软件 slug **逐条**登记 `not_evaluable{family:"software_induced_error", why:"无事件上下文，无法区分机械尖峰与调度抖动"}`；`rules_skipped ∪= {R-18…R-24, R-28, R-29(依赖 step_labels 时)}`；`overall_confidence` 按 CAP-2 下调；`next_data_to_collect` 必填（导 `events.jsonl` + 共用触发沿/NTP 对齐证据 + 时钟源说明，`unlocks` = R-18…R-24、R-28） | R-30、C2 规则 8、C6 §4、C3 规则 5/9 |
| E2 `available == true` 但 `causal_claims_permitted == false` | 整族**降级为共现观察**：写 `differential.considered` + note "时钟未对齐，因果不可断"；`fe_spike_aligned_to_*` 只以共现呈现；同时登记 `not_evaluable`（措辞"时钟未对齐，因果不可断"） | C2 规则 8、KB3 纪律 5、R-30 第二触发路径 |
| E3 门内但逐叶失效（`G3`/`G5` 不满足或 R-28 区分度不足） | **按叶粒度**退出：不满足 `G5` 者（典型 `fs = 1 kHz` 且 `τ_u = 1 ms` ⟹ `1/fs > τ_u/2`）走 R-18 ⟹ `rules_skipped` 写 `reason:"time_resolution"`；区分度不足则全族进 `considered` + `not_evaluable{why:"对齐区分度不足"}` | INV-7、R-28 末支 |

结构提示：软件族与 `mechanical_loose_structure` 在波形上同为"非周期尖峰"，二者靠**事件源独占性 + 对齐质量**分开，不靠形态拟合。
缺事件流时的正确输出不是"疑似机械"，而是：机械侧按 R-02 自身判据走（其 `fe_spike_count/move` 项跳过、置信降至 ≤ 0.5，R-02 必要上下文原文），软件侧登记 `not_evaluable`。

**族级标签纪律（A-18，D-7 已收口）**：`software_induced_error` **不是** KB0 §2 的 slug，而是**族级标签**，
在全文只允许出现在 `differential.not_evaluable` 与 `differential.considered` 里，且：

1. 族级登记项的 JSON 键是 `family`（**照 C6 §4 原文** `{"family": "software_induced_error", "why": "…"}`），
   **不是** `fault_mode`——`fault_mode` 位置只放 22 个 slug 之一（C3 规则 10）。E1 的"逐条登记"指 7 个软件
   slug 各写一条 `not_evaluable{fault_mode:"software_induced_*", why:"…"}`，族级那条 `family` 项**额外**存在、
   不替代它们（两者语义不同：族级=整体不可评估，叶级=该具体成因不可评估）。
2. 禁止以 `software_induced_error` 作为**叶子**出现在 `hypotheses[].fault_mode` /
   `ruled_out_alternatives[].fault_mode` / `verdict.primary`——出现即为结构违规，报告不得下发。
3. `considered` 是给人读的清单，允许显示名；`not_evaluable` 的 `why` 措辞取 C6 §4 / R-30 原文，不得自造。

> ~~残余跨文件不一致（本文无权改）~~ **已裁 A-18 / A-51，本文与 C2/KB3/C6 现已同调**：族级标签
> `software_induced_error` 只能出现在 `differential.not_evaluable[].family`，`fault_mode` 位置只放
> KB0 §2 的 22 个 slug（C3 规则 10）。C2 规则 8、KB3 纪律 5 与 R-30、C6 §4 与本文 §1.5 逐字一致；
> 唯一残余在 KB2 §7（第 538 行），本轮已改。

---

# 第二部分 — 置信度与证据模型（确定性）

## 2.1 单条证据强度 `S(e)`

一条证据 = `(feature, value, operator, threshold, rule_id, source)`，强度 `S(e) = g(ρ) × conf(f) × n_factor(n/n_ref) × band_factor(f0) ∈ [0,1]`。

**(a) 裕度倍数 ρ 与饱和函数 g**

```
operator ∈ {>=,>}   ⟹ ρ = value/threshold（threshold ≤ 0 时 ρ = (value − threshold)/ε_f）
operator ∈ {<=,<}   ⟹ ρ = threshold/max(value, ε)
operator ∈ {==,!=}（布尔/枚举）⟹ 不走 ρ，取 g_cat = 0.85（categorical 无裕度）
g(ρ) = 0.5 + 0.5·min(1, log10(ρ)/log10(4))；ρ < 1 ⟹ 规则未命中，不产生该证据
```

锚点（可手核）：`ρ = 1.0 → 0.500｜1.2 → 0.566｜1.5 → 0.646｜2.0 → 0.750｜2.7 → 0.858｜≥4.0 → 1.000`。选 4 作饱和点是因为 KB3 全库通用 **6 dB ≈ 4 倍** 尺度；恰好触阈给 0.5（"仅够触发"不应等同强证据）。

**(b) `conf(f)`**：实测类 = 1.0（C2 规则 5）；估计类取该特征自带 `confidence`（`bandwidth.confidence` 由
KB3 §1.10 **锁定上界 0.6**，实现不得提高）；`coherence_torque_velocity` 在 `method == "fe_proxy"` 时 ×0.7；
`channels.vel_fb.derived == true` 时频谱类整体 ×0.7（KB3 纪律 10，且不得放宽门限）。依赖为 null ⟹ 规则放弃（INV-4），**绝不把 null 当 0 或 1**。

**(c) 样本量因子**：`n_ref` **逐判据登记**（A-102 ①：原一刀切「带内 bin ≥ 32」与 §2.3 算例 A 的 `n_ref = 15` 打架，已**删除**——§2.3 手算表是 §6 检查 5「手算例逐格可复算」的唯一锚点，与本节冲突时**以算例为准**）：

| 样本量 | `n_ref` | 载体（C2 路径；括号内为过渡侧车键） | 用该行的判据 |
|---|---|---|---|
| Welch 段数 | 4 | `resonance.estimation.n_segments`（`sample_counts.welch_segments`） | R-03#2、R-04#6（同为相干判据） |
| 带内 bin（峰邻域） | 15 | `resonance.estimation.bins_in_band`（`sample_counts.band_bins`） | R-03#3、R-04#3/#5（峰谷间距与峰谷功率比读同一条峰邻域带） |
| 3 dB 带宽 bin | 8 | `resonance.candidates[].three_db_width_bins` | R-03#7 |
| `dwell` 段 | 1 | `segment_coverage.dwell` | R-03#4 |
| `rest` 段 | 1 | `segment_coverage.rest` | R-03#5 |
| `move` 段 | 4 | `segment_coverage.move` | R-03#6、R-04#4（配对判定读运动段） |
| 事件计数 | 3 | `event_context.interp_underrun_count` / `event_context.fe_spike_count` | R-19#2/#3 |
| `path` 段 | 1 | `segment_coverage.path` | R-19#4/#6 |
| 加/减速 regime 样本（各） | 50 | **C2 尚无载体**（见下方过渡口径） | R-15#1/#2/#3（A-102 ④ 补行，沿用 KB3「必要上下文」的既有口径，不是新数） |

其余非谐振族下限仍按 KB3「必要上下文」（`ripple` ≥ 2 整转；`settling ≥ 3`；`vision` 事件 ≥ 20；对齐匹配对 ≥ 3）。
表首三行是**显式登记的量**（A-102 ②，C2 `resonance.*` 已补载体）：**不得反推**——`reliable_band_hz / resolution_hz` 得 ≈1641，与算例 A 的 96 差一个量级，说明算例用的是另一套峰邻域带定义，缺载体时只能 `null` + `unavailable`，不许猜；`three_db_width_bins` 的复算式取 rule_table `n_source_recipes` 登记的 `round(freq_hz / quality_factor_estimate / resolution_hz)`（算例 A：`round(1181/27/1.95) = 22`，与第 3 行 `n` 同数）。
`n_factor = min(1, 0.6 + 0.4·log10(n/n_ref)/log10(4))` ⟹ `n = n_ref → 0.60｜2×→0.80｜4×及以上 → 1.00`，
即"刚够下限只给 6 分，够 4 倍才给满分"；`n < n_ref` 时 C2 本该输出 null，故不出现 `n_factor < 0.6`。
**过渡口径（A-102 ③，规则表消费这三个载体之前持续有效）**：缺 `n`/`n_ref` **禁止**默认 `n_factor = 1`，一律 `MissingSampleScale` 记 `rules_skipped`；侧车注入必须显式带 `welch_segments` / `band_bins` 键。R-04 与 R-15 在本表已有 `n_ref` 行，但 `rule_table` 尚未给它们登记 `n_source` 配方，引擎仍按整条规则不可评分处理，并**同时**在 `audit.assumptions` 落一行，句式固定：「R-04/R-15 的样本量下限已在 KB4 §2.1(c) 登记，但 rule_table 未登记 n_source 配方 ⟹ 本引擎不默认 n_factor=1，该两条不可评分（A-102 ③ 过渡口径）」。

**(d) 频带削弱 `band_factor`**（与"阻塞"分工：阻塞走 INV-1/CAP-5，削弱只发生在带内靠上沿）：
非频域判据 ⟹ 1.00｜f0 ≤ 0.5·f_b 且 f_b ≥ band⊥ ⟹ 1.00｜0.5·f_b < f0 ≤ f_b ⟹ 0.80（须在报告写明削弱原因）；
f0 > f_b ∨ f_b < band⊥ ⟹ 不是削弱而是**阻塞**：S(e) 不存在（INV-1）｜f0 ≥ 0.8·f_N ⟹ 先过 R-10（INV-2）。

## 2.2 聚合 `A_sup` / `A_con` / `C`

```
k = supporting_evidence 条数（k < 2 ⟹ INV-10 ⟹ 移到 considered，不计算 C）
Smax = max_i S(e_i)；Srest = mean_{i ≠ argmax} S(e_i)
A_sup = 0.55·Smax + 0.45·Srest                       ∈ [0,1]
A_con = min(0.5, Σ_j v_j)（v_j 见 §2.4）
C_mid = A_sup · (1 − A_con)
C(h)  = min(C_mid, 命中的各 CAP ceiling)              ← 封顶取 min，不叠乘两个 ceiling
verdict.overall_confidence = C(H_primary) · (1 − 0.05·min(4, |distinct blocked_by|))
```

`max` 承载决定性证据（工业判据常单条一票，如 `present_in_rest`），`mean_{其余}` 承载广度——于是 C3 规则 1 的"≥2 条"
从布尔门槛变成**连续收益**；`overall_confidence` 的 5%/独立缺席原因扣减把 R-30 的"必须相应下调"变成可计算量。
**分母是去重后的 `blocked_by` 个数，不是 `not_evaluable` 的行数**（A-73，C3 规则 16）：族级标签与它所覆盖的叶
常源于同一个缺席输入（本例 `absent_events_jsonl` 同时挡住 `software_induced_host_thread_jitter` 与整族），
按行数惩罚会让同一份数据"多写一行就掉 5% 置信"，ECE（C5 §3）随之失去意义。
常数 0.55/0.45/0.6/0.4 由本文固定；改动须升版本号并重跑全量（C5 §2）。

## 2.3 算例（两个，可逐格手核）

### 算例 A — `mechanical_resonance`（`fs = 8 kHz ⟹ f_N = 4000, f_b = 3200`；数值逐条对齐 **C2 示例 A**，场景即 C3 示例 H1）

前提（与 C2 示例 A 一致，A-1/A-2/A-3 收口后的版本）：`segment_coverage = {rest 2, move 6, settling 6, dwell 3, probing 1, path 1}`
（`probing = 1` 才与 C2 示例 A 的 `ripple.probing` 含 `segment_id 5` 自洽，C2 规则 13；原稿写 0 已按 D-5 → A-3 修正），
`resonance.candidates[0] = {freq_hz 1181.0, antiresonance_freq_hz 440.0, coherence_torque_velocity 0.86,
amplitude_ratio_vs_broadband 8.4, quality_factor_estimate 27.0, present_in_dwell true, present_in_rest false,
tracks_command_frequency false, is_double_inertia_pair true}`——峰/谷 = `1181/440 ≈ 2.68 = sqrt(1 + λ)`，λ≈6.2，
满足 INV-3（A-1：共置两惯量谷必在峰之下，早期"1181 峰 + 1420 谷"物理不成立）；
`resonance.resolution_hz = 1.95`（= fs/nperseg = 8000/4096）、`resonance.estimation = {hann, 4096, 2048, welch, pair_separation_bins 380, n_segments 8, bins_in_band 96}`（380 = (1181−440)/1.95，A-76：原写 382 无任何取整口径能得，已改；`n_segments`/`bins_in_band` 为 A-102 ② 补的显式登记载体，值即下表第 1/2 行的 `n`）、`candidates[0].three_db_width_bins = 22`（= `round(1181/27/1.95)`，rule_table 配方自 C2 已登记量导出，A-102 ②）
（C2 规则 10：谱类结论必须带估计参数，否则本文拒绝引用）；`vel_fb` 非派生，`bandwidth` 不在支持链（只在建议链，见 CAP-1）。

| i | feature（C2 路径） | value | op | threshold（KB3 原值） | ρ | g | conf | n/n_ref | n_factor | band | **S(e)** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `resonance.candidates[0].coherence_torque_velocity` | 0.86 | ≥ | 0.7（R-03#2 [P]） | 1.229 | 0.574 | 1.0 | Welch 8/4=2 | 0.80 | 1.0 | **0.459** |
| 2 | `…[0].amplitude_ratio_vs_broadband` | 8.4 | ≥ | 4（R-03#3 [L]） | 2.100 | 0.768 | 1.0 | 带内 bin 96/15=6.4 | 1.00 | 1.0 | **0.768** |
| 3 | `…[0].quality_factor_estimate` | 27 | ≥ | 10（R-03#7 [P]） | 2.700 | 0.858 | 1.0 | 3 dB 宽 22/8=2.75 | 0.892 | 1.0 | **0.765** |
| 4 | `…[0].present_in_dwell` | true | == | true（R-03#4） | cat 0.85 | 0.85 | 1.0 | dwell 3/1=3 | 0.917 | 1.0 | **0.779** |
| 5 | `…[0].present_in_rest` | false | == | false（R-03#5） | cat 0.85 | 0.85 | 1.0 | rest 2/1=2 | 0.80 | 1.0 | **0.680** |
| 6 | `…[0].tracks_command_frequency` | false | == | false（R-03#6） | cat 0.85 | 0.85 | 1.0 | move 6/4=1.5 | 0.717 | 1.0 | **0.609** |

> **表格注（A-102 ①/②）**：本表 `n/n_ref` 六行的取值（Welch 8/4、带内 bin 96/15、3 dB 宽 22/8、dwell 3/1、rest 2/1、move 6/4）就是 §2.1(c) 逐判据行的**出处**——两处现已同数，冲突以本表为准。三个非 `segment_coverage` 的 `n`（8、96、22）已由 C2 显式登记承载：`resonance.estimation.n_segments`、`resonance.estimation.bins_in_band`、`resonance.candidates[0].three_db_width_bins`（C2 示例 A 与 `examples/c2_example_a.json` 已补，值与引擎逐格复算同数；引擎消费载体前的过渡口径见 §2.1(c) 表注与 rule_table `open_gaps`）。

`Smax = 0.779`；`Srest = (0.459+0.768+0.765+0.680+0.609)/5 = 3.281/5 = 0.656`
`A_sup = 0.55×0.779 + 0.45×0.656 = 0.428 + 0.295 = 0.724`

反证（C3 规则 2：top-3 必跑）：

| j | feature | value | op | threshold | ρ′ | v_j | 说明 |
|---|---|---|---|---|---|---|---|
| 1 | `step_response[0].damping_ratio_estimate` | 0.28 | > | 0.15（R-03c 反证支） | 1.867 | 0.10 | 阻尼不算极低 ⟹ 削弱"严重共振"但不足以否决 |

`A_con = 0.10 ⟹ C_mid = 0.724 × 0.90 = 0.652`。CAP 检查：CAP-3 未触发（`present_in_rest = false`，**不是** `null`；
本例有 `rest` 段，CAP-3 只在缺 `rest` 段时封顶 0.55）、CAP-5 未触发（`f_b = 3200 ≥ 2000`）、
CAP-7 未触发（非派生）⟹ **`C(H1) = 0.652 ⟹ 0.65`**；
`verdict.overall_confidence = 0.652 × (1 − 0.05 × 2) = 0.586 ⟹ 0.59`
（`not_evaluable` 共 **3 行 = 2 个独立缺席原因**：`absent_temp_channel`（叶级 `mechanical_thermal_drift`）与
`absent_events_jsonl`（叶级 `software_induced_host_thread_jitter` + 族级 `{family:"software_induced_error"}`——
后两行同一个 `blocked_by`，**只扣一次**，A-73/C3 规则 16）。
键名纪律见 §1.5 / A-18；族级那条的 `why` 取 R-30 原文，因为本例只有 `pos_cmd` 一路位置指令、无驱动器 WKC 通道，
N6.c 三条件不齐 ⟹ 总线叶停在共现级，见 **CAP-11** 与文末 R-1。）

> ✅ **与 C3 示例逐格一致（A-72 已闭环）**：本算例的六条 `S(e)`、`ρ′ = 1.867 ⟹ v_j = 0.10`、
> `C(H1) = 0.65`、`verdict = 0.59` 与 C3 `verdict`/H1 块**同数**，且可由 C3 自己列出的证据逐格复算
> （C3 硬性规则 15）。曾经的 `0.78` 是早期草稿的示意值，它未对反证扣分、未乘 `n_factor`、未做缺席扣减；
> **D-1 → A-20 → A-72** 三步的最终处置是"改示例本身使其可复算"，而不是留一句"示意值"免责声明。
> 建议侧不变：R-03d 相位裕度校验依赖 `bandwidth` ⟹ CAP-1 使**建议层**置信 ≤ 0.60，
> 无 V* 时 `basis` 只能 `rule_heuristic`（不得给 62.2% 这类数字）。

### 算例 B — `software_induced_interp_buffer_underrun`（`fs = 1 kHz ⟹ f_N = 500, f_b = 400`，`τ_u = 1.0 ms`）

前提：`segment_coverage = {path 1, move 6, settling 6, dwell 3, rest 2}`，`available = true`，
`sync = {trigger_edge, verified: true, uncertainty_ms: 1.0}`，`causal_claims_permitted = true`，
`interp_underrun_count = 12`（`during_path = 11`），`fe_spike_count = 17`（`to_underrun = 11`，`to_host_pause = 2`），`alignment_residual_ms = 0.4`。
> 本算例是**另一份** `fs = 1 kHz` 的合成样本，不是 C2 例 A（例 A 为 `fs = 8 kHz`、`τ_u = 0.5`、
> `alignment_residual_ms = 0.25`）。事件计数刻意与例 A 同量级，好让"只有时基变差"这一个变量能被隔离；
> 两个样本的 `sync` 数值不同，不要跨样本抄数（A-72/A-76 的可复算纪律同样适用于前提）。

门检查（先于任何证据）：G1 ✓ G2 ✓ G3 ✓（对齐窗 `max(τ_u, 2) = 2 ms > 1.0 ms` 且残差 `0.4 ≤ τ_u = 1.0`）G4 ✓、
G5：`fs ≥ 1 kHz` ✓ 但 `1/fs = 1.0 ms > τ_u/2 = 0.5 ms` ✗ ⟹ **R-18 必须 skip**（`rules_skipped += {R-18,
reason:"time_resolution: 1.0 ms > 0.5 ms"}`）；而 R-19 只需 `fs ≥ 500 Hz`（R-19 必要上下文）⟹ 本叶仍可运行。这就是"同一份数据上软件族内部可评估性不同"——禁止用族级判断代替叶级判断。

| i | feature | value | op | threshold | ρ | g | conf | n/n_ref | n_factor | **S(e)** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `event_context.interp_underrun_during_path / interp_underrun_count` | 11/12 = 0.917 | ≥ | 0.7（R-19#2 [P]） | 1.310 | 0.597 | 1.0 | 匹配对 12/3=4 | 1.00 | **0.597** |
| 2 | `event_context.fe_spike_aligned_to_underrun / fe_spike_count` | 11/17 = 0.647 | ≥ | 0.5（R-19#3 [P]） | 1.294 | 0.593 | 1.0 | 尖峰 17/3=5.7 | 1.00 | **0.593** |
| 3 | `tracking.path_segments[0].fe_max_counts / .fe_rms_counts` | 3100/1520 = 2.039 | ≥ | 2.0（R-19#4 [P]） | 1.020 | 0.507 | 1.0 | `path` 段 1/1=1 | 0.60 | **0.304** |
| 4 | `tracking.path_segments[0].corr_fe_vs_accel` | 0.91 | ≥ | 0.7（R-19#6） | 1.300 | 0.595 | 1.0 | `path` 段 1/1=1 | 0.60 | **0.357** |

（`corr_fe_vs_jerk < corr_fe_vs_accel` 与 `causal_claims_permitted == true` 是**门**，不计入 `A_sup`——门禁条件计入支持证据会构成"因为我能看所以我相信"的自证，见 §2.7 反自证条款。）

`Smax = 0.597`；`Srest = (0.593+0.304+0.357)/3 = 1.254/3 = 0.418`
`A_sup = 0.55×0.597 + 0.45×0.418 = 0.328 + 0.188 = 0.516`

反证：

| j | feature | value | op | threshold | ρ′ | v_j | 说明 |
|---|---|---|---|---|---|---|---|
| 1 | `ff_mismatch.asymmetry_ratio` | 2.26 | ≥ | 1.5（R-15#1，竞争解释） | 1.507 | 0.10 | 前馈主判据同时命中 ⟹ 必须并列呈现 |
| 2 | `global.fe_p999_counts / global.fe_rms_counts` | 1380/412.6 = 3.34 | ≥ | 4（尖峰集中度，R-02#2 同源） | 0.835 | 0.05 | 阈值方向未达标：尖峰集中度不如预期 |

`A_con = 0.15 ⟹ C_mid = 0.516 × 0.85 = 0.439`。CAP：CAP-2 未触发（`permitted == true`）；CAP-5 触发于
**谐振族**（`f_b = 400 < 2000` ⟹ R-03/R-04 阻塞、`mechanical_resonance` 进 `not_evaluable`），对本叶无 ceiling。
**`C = 0.44 < 0.60`** ⟹ 按 C3 规则 5 `next_data_to_collect` **不得为空**：
①`interp` 事件补 `detail.buffer_level`/`lookahead_ms` 时间序列（欠载深度可量化）；
②同一 G 代码做"插补前瞻加倍/减半"A/B 激励并采 `path 段 ≥ 5`（仅此把 i3/i4 的 `n_factor` 从 0.6 提到 1.0，
`A_sup` 约升至 0.55、`C` 约 0.47 ⟹ 仍低于 0.6，说明单靠加样本救不回来，必须换激励）；
③`fs ≥ 2 kHz` 以满足 `1/fs ≤ τ_u/2`，解锁 R-18 与 R-28 完整择优。

变体 B′（`sync.verified == false ⟹ causal_claims_permitted == false`）：INV-5/INV-6 生效 ⟹ 本叶**不可达**；
输出 `considered` + note "时钟未对齐，共现不等于因果"，`not_evaluable += {family:"software_induced_error",
why:"时钟未对齐，因果不可断"}`（族级键名纪律见 §1.5，A-18）；若报告仍需一个共现强度，取 `min(C_mid, 0.40)`（CAP-2）并标注为观察值、非归因置信。

## 2.4 反证扣分 `v_j`，以及为什么矛盾证据必须并存呈现

```
v_j = 0.20（反证自身 ρ′ ≥ 2，强反证）｜0.10（1 ≤ ρ′ < 2）｜0.05（ρ′ < 1，本应出现的形态未出现）
      0.00（反证依赖为 null ⟹ 走 INV-4，不算反证）；A_con ≤ 0.5
```

**否决 ≠ 扣分**：若反证命中 KB3 该规则"排除项"里的**否决条件**（例：R-04 的"`notch_filters` 覆盖
`antiresonance_freq_hz` ⟹ 谷是滤波造成"；R-10 的任一 OR 项；R-04 的 `f_a > f_0`；R-15 的
`NOT(friction_stiction_ratio ≥ 1.5)`），则**直接判该假设不成立**（不入 `hypotheses`，改登 `considered`
并写明被哪条排除项否决），不得降级为 `v = 0.2` 继续存活。

并存呈现（而非平均掉）的四条理由：
1. **可反驳性是产品**：工程师要用**一条**现场观察推翻假设；反证被平均进标量后他不知道该看什么（C3 规则 2 原文："只报支持证据的诊断报告在内行眼里等于没做"）。
2. **平均抹平决定性/边缘性**：`A_sup` 的 `max` 项与 `A_con` 的强项都可能是一票级，算术平均把两者压回噪声区。
3. **防数量淹没**：若把反证并入 `mean(S)`，堆 6 条弱支持即可稀释 1 条强反证；本文支持侧与反对侧分池聚合，稀释在结构上不可能。
4. **自验证循环的探针**：T3 合成集上反证几乎恒空（生成器只注一个故障），故"反证非空率"必须**分层**
   报告；若 T3 ≪ T1/T2，则 T3 上调出的任何置信度不适用于现场。

## 2.5 封顶（CAP）表——按依赖链自动生效

| ID | 触发条件 | ceiling | 作用对象 | 依据 |
|---|---|---|---|---|
| CAP-1 | 支持链或建议链含 `bandwidth.*`（含 `t_s_min = 4/(ζ·ωn)` 类衍生） | **0.60** | 该假设的建议/结论置信 | KB3 §1.10；R-13"不得作为增益上调唯一支撑"；R-29 上限 `unverified` |
| CAP-2 | `available == false` ⟹ 软件族 **0**；`causal_claims_permitted == false` ⟹ **0.40** 且降级共现 | 同左 | `software_induced_*` 7 叶 | C2 规则 8；KB3 纪律 5；R-30 |
| CAP-3 | `resonance.candidates[].present_in_rest == null`（无 `rest` 段） | **0.55** | `mechanical_resonance` 与 `electrical_feedforward_mismatch` 双方 | R-03 必要上下文；R-26 第 5 支 |
| CAP-4 | C4 `validation[].plant_fit.fit_residual_pct > 25%` | **0.65** 且 `basis` 必须降 `rule_heuristic`（无数字） | 该 `action_id` 的 `recommendation` | C4（>25% 必降级）；C5 §3"无依据成功声明 = 0" |
| CAP-5 | `rule_id ∈ freq_limits.blocked_rules` 或 `feature ∈ unavailable` | **0**（禁入 `hypotheses`） | 越带叶 | C2 规则 7；INV-1；R-25 |
| CAP-6 | `drive.*` 依赖缺失（`inertia_ratio`/`notch_filters`/`rigidity_level`/`velocity_loop_gain_hz`） | **0.55** 且 `basis = unverified` | R-09 / R-12-B / R-13 / R-14 / R-18 第 5 判据 | KB3 纪律 3 |
| CAP-7 | `channels.vel_fb.derived == true` | 频谱类 **×0.70**（乘性惩罚，与 ceiling 并列写明） | R-10/R-11/R-13/R-17/R-20 | KB3 纪律 10（C1 派生规则 4） |
| CAP-8 | `alignment_residual_ms > τ_u` 或对齐窗 ≤ τ_u | **0.40** + 呈现为共现 | 软件族对齐类证据 | KB3 纪律 6；C6 §3 |
| CAP-9 | 反事实检查项（§4）判为 UNRESOLVED | **0.60** | 该假设 + `not_evaluable` 副本 | 本文定义 |
| CAP-10 | 同族 `not_evaluable` ≥ 3 条 | `overall_confidence` 额外 −0.05/条（与 §2.2 合并计，总扣 ≤20%） | 顶层 | C3 规则 9；R-30 |
| **CAP-11** | `software_induced_bus_cycle_miss` 通过 §1.3 N6.c 的**三条件升级**（`bus_cycle_hold_max_ms` 与 `fe_spike_aligned_to_network_miss` 均非 null ∧ `sync.verified == true` ∧ `causal_claims_permitted == true` ∧ `alignment_residual_ms ≤ sync.uncertainty_ms`，方向由 **A-82** 更正 A-50） | **0.60**（三条件齐 ⟹ 可进 `hypotheses`；缺任一 ⟹ 本表不适用，该叶停共现级、禁入 `hypotheses`，只进 `differential.considered`） | 该叶的归因置信 | **A-45**（D-6 收口）+ **A-82**（方向）；KB0 §7.1；字段侧 A-9 已落 C2 `event_context` |
| **CAP-12** | 软件族（`software_induced_*` 7 叶）的结论层级 | **检出类**可由 KB5 事件注入支撑标 `simulation_validated`；**改进量 / 参数建议**（`expected_effect`）**恒为 `rule_heuristic`** 且不给数字，引用仿真必须带 caveat 原文"仿真不含真实调度器与总线仲裁" | 该假设的 `expected_effect.basis` 与 `recommendation` | **A-43**（G-12 有条件开禁）；C3 规则 4；C4（`fit_residual_pct` > 25% 必降级的门仍在） |

实现要点：CAP 只读 C2 字段（`freq_limits`/`segment_coverage`/`event_context`/`unavailable`/`bandwidth`/
`sensor_disagreement`/`quality_ref`）与 C4 记录，**不看规则结论**，因此不会形成"用结论给结论封顶"的自指。
CAP-11 读 `event_context` 的三个对齐/保持字段（A-9 已落地），CAP-12 读样本 tier（C5 §1）与 C4 的 V* 记录，
两者与其它行同强度：命中即封顶，不得由 `rationale` 文字豁免。

## 2.6 ECE 在此模型下的测量

C5 §3 把 ECE 列为最重要指标（≤ 0.10）。评测用 `primary` 假设的 `C` 对 `gold_root_cause`：

- **分箱**：等宽 5 箱 `[0,0.2) [0.2,0.4) [0.4,0.6) [0.6,0.8) [0.8,1]`；箱内 `conf̄_b = mean(C)`、`acc_b = Top-1 命中率`。选 5 而非 10 是因为 T1+T2 案例数有限。
- **样本量**：每箱 `n_b ≥ 10` 才单独计；不足则与**相邻箱合并**并注明合并了哪两箱（不许悄悄丢箱）；该层总数 `N ≥ 80` 才允许报 ECE，否则只报分箱原始表 + "样本不足，ECE 不可解释"。
- **禁止跨 tier 合并**（C5 §1）：`T1-a`/`T1-b`/`T2`/`T3` 各一条曲线；能力主张只取 T1+T2；T3 的 ECE 只出现在"流程正确性"章节，标题写明"合成集，不用于能力主张"。
- **再按族切片**：三族各一条。第三族样本天然少、CAP-2/3/8 密集，最易系统性过度自信，混在总数里看不见。

示例层（`N = 96`）：

| bin | n_b | conf̄_b | acc_b | \|acc−conf\| | 贡献 |
|---|---|---|---|---|---|
| [0,0.2) | 18 | 0.12 | 0.11 | 0.01 | 0.0019 |
| [0.2,0.4) | 22 | 0.31 | 0.27 | 0.04 | 0.0092 |
| [0.4,0.6) | 20 | 0.52 | 0.45 | 0.07 | 0.0146 |
| [0.6,0.8) | 16 | 0.71 | 0.69 | 0.02 | 0.0033 |
| [0.8,1] | 20 | 0.88 | 0.80 | 0.08 | 0.0167 |
| **ECE** | 96 | | | | **0.0457** |

达标（≤0.10），但贡献集中在 bin3（0.4–0.6 高估 7 点）与 bin5（`conf̄ = 0.88` 的 20 例只命中 16，高置信段最不可信）——回溯优先查这两箱。

## 2.7 "宁可低置信多要数据"的量化权衡

两个门槛分工不同，不可混用：

- **披露门槛 0.60**（C3 规则 5）：`C < 0.60 ⟹ next_data_to_collect` 不得为空 ⟹ 强制**表达**不确定性。
- **行动门槛 τ\***：是否值得让工程师动手。设 `G` = 一次正确诊断的收益（归一 1.0 人日）、`c_wrong` = 按错误建议改参数的代价、`c_ask` = 补采一轮代价：

```
EV_act = C·G − (1−C)·c_wrong ；EV_ask = −c_ask + p↑·G
EV_act = EV_ask ⟹ τ* = (c_wrong − EV_ask)/(c_wrong + G)
```

`EV_ask = 0` 时：`c_wrong:G = 1:1 → τ* = 0.50｜2:1 → 0.667｜3:1 → 0.750｜6:1 → 0.857`。
本项目的合理区间是 3:1 ~ 6:1（陷波放错频段会侵蚀相位裕度，R-03 风险原文），故 **τ\* ≈ 0.75–0.86，
显著高于披露门槛 0.60**。算例 A（0.65）在 3:1 下不动手、算例 B（0.44）在任何比值下都不动手。
一句话口径：**"C3 的 0.6 不是'可以下手'的许可，是'必须说清还缺什么'的义务。"**

**反自证条款**：门禁类条件（`available`、`causal_claims_permitted`、`f_b ≥ band⊥`、`fs ≥ …`、
`segment_coverage > 0`）**一律不计入 `A_sup`**，只作门/CAP 生效（算例 B 已示范）。否则"数据齐了"会同时抬高命中率与置信度，形成同义反复，ECE 必然在高置信箱出现结构性伪影。

## 2.8 ECE 恶化时的回溯定位（按 §2.6 分层结果执行）

| 步 | 动作 | 判据/产出 |
|---|---|---|
| 1 | 把 ECE 拆到 **bin × slug × rule-set** 三维 | 定位贡献最大的单元（例：bin5 + `mechanical_resonance` + {R-03a,R-03b}） |
| 2 | 单元内分"命中/未命中"两组，逐证据对比 `S(e)` 分布 | 找"在未命中组普遍偏高、在命中组不更高"的证据 ⟹ 该判据在**假阳方向**失效 |
| 3 | 查 `g(ρ)` 是否因 `[P]` 阈值过松而虚高 | 对照 KB3 §3.2 的 `[P]` 初值与标定方法；回 KB3 补合法化，不在本文改数 |
| 4 | 重放 C2 快照查 CAP 漏触发 | 优先 CAP-1（bandwidth 上链）、CAP-3（`present_in_rest == null`）、CAP-4（`fit_residual_pct > 25%`）、CAP-8（对齐残差）；漏触发是实现缺陷，不改阈值 |
| 5 | 查 `n_ref` 是否定得过低 | 症状：小样本组（`n_factor ≤ 0.6`）命中率明显更低，但 `C` 分布无差异 |
| 6 | 最差单元在 `software_induced_*` 时 | 专项查 `1/fs ≤ τ_u/2`（INV-7）、`τ_u` 是否取保守 5 ms 而未记 `assumptions`、R-28 的 `max − second ≥ 0.2` 是否被绕过 |
| 7 | 只改 KB3 阈值/本文常数并升版本号 | 全量重跑 + 公开前后差异；**禁止**针对隐藏集失败案例改规则（C5 §2）；ECE 与拒答正确率同报（防靠整体压置信换 ECE） |

三种恶化指纹：(i) 高置信箱 `acc` 低 ⟹ CAP 漏触发或反证未跑；(ii) 中置信箱 `acc` 高 ⟹ 过度自信的反面
（过度保守），拒答率好看但可用性下降；(iii) 软件族整族偏高 ⟹ 门禁条件被误当证据（§2.7 反自证条款被破坏）。

## 2.9 排序口径：严重度优先、次数次之（字典序）

`rank` 由字典序键 `(severity, C, tie2, tie3, rule_id)` 逐位比较，**不是** `证据强度 × 次数`。

| 级 | 语义 | 锚点（全部为已登记判据；与出现次数、样本量无关） |
|---|---|---|
| S0 | 安全/不可逆 | `n_alarm ≥ 1`（R-20）；`cur_q_peak_abs_pct ≥ 90` 或 `cur_q_saturation_ratio` 高（R-06 排除项/限流）；R-14 自激且 `phase_margin_deg < 30`；KB6 R-49 残差超外部验收限 |
| S1 | 工件报废/机械整改 | R-02（`fe_p999/fe_rms ≥ 4` 且冲击 CV > 0.4）；R-22/R-45（比例错 ⟹ 系统性错位）；R-04 判 `inertia_ratio > 10` ⟹ 参数对策无效、需机械整改（不可逆） |
| S2 | 节拍/精度不达标 | R-23/R-29（`settling_time_ms` 拉长）；`corner_error_counts` 大；R-15（`asymmetry_ratio ≥ 1.5`）；R-19（插补欠载 ⟹ 轨迹中断/超差）；R-21（视觉结果迟到 ⟹ 节拍损失）；R-20 无告警支（`n_alarm == 0`，欠载/迟到的节拍档，A-100） |
| S3 | 质量退化边缘 | R-03/R-09 峰存在但 ζ 不低；`ripple_over_velocity_pct_per_rev`；R-07（`per_rev_amplitude ≥ 0.2·fe_rms`）；R-18（主机线程抖动，仅表现为尖峰）；R-24（轮询延迟）（后两条 A-100 补，按"后果类型"归入现有档） |
| S4 | 观测/测量层（只报告不派工单） | R-10 伪峰；R-17 量化主导（动作是硬件级"参数不可解决"）；KB6 R-48 相关性≠因果的呈现纪律 |

`severity` 取该假设主规则登记级；多规则并发取**最高级**并在 `rationale` 说明。tie-break：`severity` 同 ⟹ 比 `C`；
`C` 同（±0.01）⟹ 比受影响面（证据窗口覆盖的 `segment_coverage` 占比）；仍同 ⟹ `rule_id` 字典序小者在前。四个键均来自确定性数据，保证 `deterministic_core_hash` 可复现（C3 `audit`）。

> **A-116（2026-10-21）对本段的两处收窄——原文不改写，按证据等级降级措辞**：
> ①**±0.01 的并列带两侧都没实现**。`engine.py::_rank` 用**未取整**的 `score.c` 排（`confidence.py::display` 是
> 「唯一的 2 位小数出口（序列化/展示层）；计算链上不得取整」⟹ 引擎按原始值排是对的纪律），
> 而 `c3validate.py::_check_rank_monotonic` 只能读产物里**已取整**的 `confidence` 重建序 ⟹
> 两条假设的原始 C 若落在同一个 2 位格内（如 0.4414 与 0.4446，都显示 0.44），引擎的序与校验器重建的序
> 可以不一致，且该不一致**目前没有任何实测样本能触发**（E2 的 0.48 与 0.65 相距 0.17）
> ⟹ 本段的「`C` 同（±0.01）」是**尚未落码的口径**，不是现状描述。
> ②**`deterministic_core_hash` 此刻没有生产者，也没有定义**。引擎在 `engine.py:708` 恒写空串 `""`，
> C3 契约的两份示例与三份夹具里写的是占位符 `"…"`，而本句断言它"可复现"——一个从未被算过、
> 也没有"哈希哪些字段"定义的字段，撑不起这句断言（措辞强度不得高于证据等级）
> ⟹ 本句现读作「**四个键均来自确定性数据，这是 `deterministic_core_hash` 将来可复现的前提**」，
> 哈希核（哪些字段进、怎么规范化）与实现另立任务；在它有定义之前，任何报告不得声称本节的序"已被哈希锁定"。
> **A-118（同日）更新这一句的前半**：哈希核**现已有定义**——`docs/contracts/C3-diagnosis.md` **规则 21**
> 唯一规定了纳入字段、排除的四类（自由叙述 / 时钟与版本 / 派生冗余 / 哈希自身）、四步规范化与合法值三形态；
> 但**实现仍缺位**（`engine.py:708` 恒写空串、校验器无对应检查、5 处占位符未清零）⟹ 本句末段"没有生产者"
> 与"不得声称已被哈希锁定"**继续成立**，落码随 #43 后半。
> 另与 A-115 对上：本段的第三个键（受影响面）在实现里是**恒等量**（`_coverage` 不看假设），
> 所以"四键"当前实际起作用的是三键。
>
> **A-121（同日）把上面 ① ② 两条一并结清——本段的排序口径现已有实现，且两侧同源**。
> ①**±0.01 并列带已落码**（`confidence.rank_band_c`，队长锚定的划分）。落码时定死三件事，
> 都是原文没写、但两侧必须一致才不打架的：**(i) 第二键读两位显示值**——引擎不再按未取整的
> `score.c` 排（那条纪律对**算术**是对的，对**排序**是错的：校验器只能读产物里的两位值，
> 两把尺子量同一条带就会分出两种序）；**(ii) 带的划分取队长锚定**，不取链式扩张——
> 0.50/0.495/0.49 在链式下三行并成一带，队长锚定下同样并带，但 0.50/0.495/0.47 就分得开，
> 只有队长锚定能写成一句话让人照着重算；**(iii) 并列落 `fault_mode`，不落本段写的 `rule_id`**
> ——`rule_id` 在假设级没有载体（A-115 裁为"不补"），引擎若按它排，校验器复算不出这个序，
> 规则 20 会对一份合法报告判红，那是假红不是缺陷。本段要的是"序可复现"，`fault_mode` 在报告里
> 唯一且稳定，达成同一目的；等 C2 侧给出窗口出处、`rule_id` 有了假设级载体，再把这一键换回去
> 并同步扩规则 20。
> ②**`deterministic_core_hash` 现已有生产者、已有校验器、占位符已清零**（C3 规则 21 落码，
> 定义与实现的落点见 `docs/contracts/C3-diagnosis.md` 规则 21 与 `src/axiscope/core_hash.py`）。
> 覆盖到本段末句那句"可复现"：**现在成立，但只在规则 21 划定的范围内成立**——哈希吃的是两位显示值，
> 区分不了带内两位显示相同的两种序，而那正是 ① 刚补上的那一层。两者合起来才是本段末句要的那个保证：
> 带外改排序/改算术 ⟹ 哈希变；带内改排序 ⟹ 规则 20 按 `fault_mode` 判。两层都各有机器载体
> （`C3-R21-core-hash-recompute` / `C3-R20-rank-monotonic`），不靠散文承诺。

**本节现在是被机器判的，不只是散文口径**（A-107 ③）：C3 新增硬性规则 20，`hypotheses[].rank` 必须等于本表的字典序、
`verdict.primary` 必须等于 rank 1 的那条（检查 id `C3-R20-rank-monotonic` / `-rank-contiguous` / `-primary-is-rank1`）。
**载体缺口（KB0 §6 检查 23 的形状）**：四键里只有前两键在 `hypotheses[]` 有字段（`severity`、`confidence`），
`segment_coverage` 与 `rule_id` 只活在引擎内部、没写进产物 ⟹ 规则 20 按 `(severity↑, −C±0.01 并列带, fault_mode)`
严格判，**引擎与校验器两侧用同一个三元组**（A-121：引擎原按 `rule_id` 收尾，会排出校验器复算不出的序）；
`coverage` 是恒等量（A-115）、`rule_id` 无假设级载体（A-115 裁为"不补"），故实际起作用的是三键；
四键全序要等 C3 给这两键补字段后再扩。

**`software_induced_*` 一族的锚点与仲裁分工（A-100）**：本表原先只有 R-22→S1、R-23/R-29→S2 与 R-20 的
`n_alarm ≥ 1`→S0 三条覆盖软件族，其余成员在表内**无行**，引擎只能把 severity 写成推断值——而 `verdict.primary`
的第一排序键就是 severity，一个推断值因此决定整份报告的头条，这是本节的口径漏洞。现按**后果类型**补齐锚点：
R-19（轨迹中断/超差）与 R-21（节拍损失）入 S2，R-18（仅表现为尖峰）与 R-24（轮询延迟）入 S3，
R-20 维持 `n_alarm ≥ 1`→S0、无告警时为 S2。补齐后 C2 例 A 的头条**仍是软件族**（R-19 的 S2 数值小于 R-03 的
S3 ⟹ 排前），这是字典序的既定结果，不再依赖任何推断值。**分工写死**：R-26 只在**同一 severity 档内**决定
哪条规则的解释优先；跨档排序一律归本节，R-26 **不得**覆盖 severity 序。R-26 有序链**缺支即登记**：链上无命中时
写 `audit.arbitration_notes`「R-26 有序链无命中」，禁止静默挑一支或改序（补集支见 KB3 R-26 第 6 支）。
"按后果类型归档"是**裁决分类锚点**而非独立观测锚：`rule_table.json` 的 `severity_provenance` 以
`classified:` 前缀指向本表行，引擎仍须在 `audit.assumptions` 留一行痕，报告不得将其写成唯一结论。

为什么用字典序（独立论证，不借用 AUDIT 的叙述）：
1. **排序对象是工单序列，不是后验概率**。乘积隐含"每次误判损失相等"，而本领域损失函数强非线性：S0 类一次就该停线，S4 类一百次也不派工单。
2. **保序性与校准一致性**。C5 用 ECE 检验"`C` 单调对应命中率"；字典序在 `severity` 相同处仍按 `C` 保序，
   `C` 语义不被污染。乘积排序使"排序 ≠ 按 C 排序"，同一 `C` 区间在不同案例得到不同被选中概率，ECE 的分箱含义随之失效，校准曲线不再是可解释对象。
3. **避免对样本量双重计分**。`n_factor` 已按样本量惩罚每条证据；再乘次数等于同一统计量用两次，
   系统性偏袒高频工况（长行程、多次定位）——那恰是最容易采到数据、最不需要 agent 提醒的部分。
4. **对阈值标定误差稳健**。`severity` 是**区间归属**、`C` 是连续量：字典序下 `[P]` 阈值的标定误差最多
   造成同级内换位、不跨级；乘积模型下同样误差能直接翻转首名假设，进而翻转 `verdict.primary`。
5. **堵住合成集上的奖励黑客路径**。排名若含"次数"，在 T3 上"注入多起轻微故障"即可抬高排名类指标而
   命中率不变——这是自验证循环最容易长出的形状；严重度由物理后果决定、与注入数量无关，无法刷分。
6. **复核动线同构**：工程师复核顺序就是"先看后果、再看证据"，字典序使 `audit.rules_fired` 与人类复核
   一一对应，乘积模型则要求复核者反推一个未登记的代价换算。

## 2.10 叙述层措辞与证据分级同调（A-31，C3 规则 14；对应 INV-13）

置信度只约束**数值**，本节约束**文字**——两者必须同调，否则一份 0.59 的报告读起来像 0.95 的承诺。

- 每条结论在 `audit.tier_ledger[]` 里带 `source_tier`（A-71 定的载体，检查器读它不读散文；取值同 C5 §1
  与 KB0 §4：`T1-a`/`T1-b`/`T2`/`T3`，A-24 的 `T1-c` 只给标定模块；**缺行 ⟹ 该结论按 `T3` 处理**）。
- **叙述层措辞强度不得高于数据层 `source_tier`**：报告文本（`verdict.summary` / `rationale` / `note` /
  `display_name`）里出现「已核对 / 已验证 / 现场确认 / 手册原文确认 / 实测通过」类措辞，而该结论的
  `source_tier < T1` ⟹ **拒绝出报告**（生成期硬拦，不是降级成一句 disclaimer，也不是把措辞改成"待确认"后放行）。
- `T3`（KB5 合成）证据的合法措辞上限是"管线上跑通 / 该形态可被检出"，**永不**写成"实测/已验证"；
  `T2`（文献/厂商手册阈值）上限是"按 `<出处>` 的阈值"，**永不**写成"手册原文确认"（我们手上没有原文）。
- 本文档自身遵守该纪律：凡引用未在手册原文核对过的厂商行为，一律写"第三方实现审计中出现的缺陷形态"并标
  `public-doc`（A-32/A-33），不得写成我们的发现。

**为什么把这条写进归因模型而不是只写进契约**：措辞升格只发生在"被读到的那一层"——数据层一直诚实地标着
`verified: "public-doc"`（62 处），而面向外部的两份文档写成"已对照厂商官方手册原文核对"（外部真实失效案例，
`docs/AUDIT-minimax-round3.md` §二）。审计者读到那句话就会停止怀疑，所以这一类失效最难发现、也最贵。
`C` 算得再准，配上越级的动词仍然是一份过度自信的报告：本节把它变成可机器判定的拒绝条件。

---

# 第三部分 — 混淆对与证伪设计

每对给出：(a) 为什么会混（重叠 C2 路径）；(b) **决定性判据**（路径 + 阈值 + `seg=`/`band=`/`evt=` 前置）；
(c) 数据不足时的**具体输出**（`not_evaluable` 措辞 + `next_data_to_collect` 的通道与激励设计）。

### CP-1 `mechanical_resonance ↔ electrical_feedforward_mismatch`（C5 §6 预期的 Top 混淆对）
- **为何混**：两者都在加减速时刻抬高误差；`ff_mismatch.asymmetry_ratio ≥ 1.5`、`ff_mismatch.fe_vs_accel_corr ≥ 0.6`
  与 `resonance.candidates[].amplitude_ratio_vs_broadband ≥ 4` 可同时成立。
- **决定性判据**（R-26 有序链，禁止并列成两个等权假设）：① `present_in_rest == true` ⟹ 电气/伪峰；
  ② `present_in_dwell == true ∧ coherence_torque_velocity ≥ 0.7 ∧ asymmetry_ratio < 1.5` ⟹ 机械；
  ③ `present_in_rest == false ∧ present_in_dwell == false ∧ asymmetry_ratio ≥ 1.5 ∧ fe_vs_accel_corr ≥ 0.6` ⟹ 前馈；
  ④ ②③同成立 ⟹ 谐振 primary、前馈 rank2 并互记 `contradicting_evidence`；⑤ `present_in_rest == null` ⟹ 双方 CAP-3 = 0.55。
  `seg=` `rest ≥ 1` **且** `dwell ≥ 1` 且 `move ≥ 3`（加/减速各 ≥ 50 样本）；`band=` R-03 需 `f_b ≥ 2000` 否则候选改 R-09（`f_b ≥ 150`）；`evt=` 不需要。
- **不足时输出**：`not_evaluable{mechanical_resonance, why:"fs 不足，kHz 频段无信息（不代表不存在）"}`；
  `next_data_to_collect`：①补**静止使能 ≥ 1 s**（`rest`）+ **闭环保持 ≥ 0.5 s**（`dwell`）解锁 R-26 全链；
  ②`fs ≥ 8 kHz`（推荐 20 kHz）≥ 2 s 解锁 R-03/R-04/R-10-kHz/R-11-kHz；③激励：**同轨迹重复 ≥ 6 次，其中 3 次
  加速度减半**——结构模态峰频不随 `a` 变（`tracks_command_frequency == false`），前馈失配误差随 `a` 近似线性缩放
  （`e ≈ a/ωn²`），比较两组的 `asymmetry_ratio` 与 `freq_hz` 稳定性即可分离。

### CP-2 `mechanical_resonance ↔ electrical_torque_ripple`
- **为何混**：`spectral.cur_q.dominant_freq_hz` 高窄峰 + `tonality_index ≥ 0.6` 在 `cur_q` 上都像"共振"。
- **决定性判据**：`present_in_rest == true`（静止使能仍在）∨ `coherence_torque_velocity < 0.7` ⟹ R-11/R-10；
  `spectral.cur_q.harmonic_ratios` 全为整数/半整数 ±5%（R-11#4）；`ripple.probing[].correlated_with_cur_q ≤ 0.5`（机械侧未响应）。
  `band=` 低频支 `f_b ≥ 150`、开关频率支 `f_b ≥ 2000`（否则只能 blocked）；`seg=` `rest≥1, dwell≥1`。
- **不足时输出**：无 `rest` ⟹ 双方 CAP-3；`harmonic_ratios == null` ⟹ R-11 放弃（null ≠ "无谐波"）；
  `next_data_to_collect`：驱动器开关频率与 `meta.drive.notch_filters`/`torque_filter` 清单 + `rest`/`dwell` 对照段。

### CP-3 `mechanical_backlash ↔ mechanical_friction_stiction`
- **为何混**：`global.reversal_error_counts ≥ 3·fe_rms`；起步与反向瞬间都有大 `abs(fe)`。
- **决定性判据**：**时刻语义 + 平台条件**。摩擦峰在**由静止起动**时刻且 `friction_stiction_ratio ≥ 1.5`（R-06#1）
  + 起步窗内 `abs(cur_q)` 峰 ≥ 2·`cur_q_rms_pct`；间隙峰在**方向翻转**时刻且有平台（`abs(db_i/dt) < 0.1·vel_mean`）
  + 跨反向 `CV ≤ 0.3`（R-08#4）。`seg=` 间隙需 `move ≥ 2` 含反向、摩擦需 `move ≥ 3` 含 ≥ 50 ms 静止前置与恒速区。
- **不足时输出**：全程单向 ⟹ `backlash_estimate_counts` null（C2 示例 `unavailable` 原文）⟹
  `not_evaluable{mechanical_backlash, why:"无反向段，失动不可测"}`；补采**正反双向小行程往复 ≥ 20 次**
  （步距 ≥ 5×量化台阶）+ `cur_q` 通道。

### CP-4 `mechanical_crawling ↔ mechanical_encoder_periodic_error`
- **为何混**：恒速/低速位置残差的周期性起伏，`corr_vel_vs_curq` 与 `correlated_with_cur_q` 都可能高。
- **决定性判据（唯一可靠区分量，R-05 排除项原文）**：**频率—速度关系**。编码器 `f = k·v/CPR` 随速度线性变
  且 `phase_locked_to_pos_modulo == true`、`harmonics_per_rev` 与 `encoder_lines` 对应；爬行
  `sawtooth_freq_hz` 近常数（跨速度段 CV ≤ 0.3，R-05#7）且 `vel_min_ratio ≤ 0.15`、`stall_count ≥ 1`。
  `band=` 编码器支还需 `k·f_rev ≤ f_b`；`seg=` ≥ 2 整转 `probing` / 低速段 ≥ 2 s。
- **不足时输出**：`CPR == null` ⟹ `not_evaluable{mechanical_encoder_periodic_error, why:"缺 meta.axis.motor_rev_counts，每转阶次无定义"}`
  （禁写"无编码器误差"）；补采 **3 档恒速（v, 2v, 4v）各 ≥ 2 整转** + `encoder_lines` +（若可得）第二独立测量通道。

### CP-5 `mechanical_backlash ↔ software_induced_pulse_eq_overwritten`（软件族）
- **为何混**：都是"重复定位有固定偏差"，`backlash_estimate_counts` 与 `fe_rms_counts` 同量级异常。
- **决定性判据**（R-27 三段）：`abs(β) ≥ 0.002`（误差/行程斜率）**且** 偏差随 `recipe` 阶跃 `≥ 3·σ_err`
  （R-22#1,#6）⟹ 软件；仅反向出现且与行程无关且 `CV ≤ 0.3` ⟹ 间隙；皆不成立 ⟹ 均不入 `hypotheses`。
  `evt=` `step_labels[].recipe` ≥ 2 组；`seg=` `move ≥ 2`。**两者互斥执行**（R-27：同一证据不得既判机械又判软件）。
- **不足时输出**：无 `step_labels` ⟹ 退化为 R-08 + `audit.assumptions` 记录退化（不得静默），并登记
  `not_evaluable{family:"software_induced_error", why:"无工艺/换型事件，标定覆盖与间隙不可分"}`；补采：换型前后各一组**同轨迹**
  样本 + `counts_per_mm` 变更历史 + **跨行程 ≥ 5 个位置 × ≥ 10 次重复**（使斜率 `β` 与 recipe 阶跃可同估）。

### CP-6 `mechanical_loose_structure ↔ software_induced_host_thread_jitter`（软件族）
- **为何混**：同为非周期尖峰，`fe_p999/fe_rms ≥ 4` 双方都能命中；调度抖动的跟随误差尖峰在波形上与机械冲击
  难以区分（C3 规则 8 原文，这是本项目差异化的立论点）。
- **决定性判据**：共用"与运动相关"证据 `fe_spike_count/max(move,1) ≥ 0.8`（R-02#3）；分叉在
  ①事件对齐：`fe_spike_aligned_to_host_pause/fe_spike_count ≥ 0.7 ∧ host_pause_max_ms ≥ 20 ∧ alignment_residual_ms ≤ τ_u` ⟹ R-18；
  ②时刻锁定：对齐比 < 0.3 而尖峰**锁反向时刻**且 `tonality_index ≤ 0.5` ⟹ R-02（R-02 排除项原文："抖动尖峰与反向时刻不相关"）。
  `evt=` G1..G5 全通；`band=` R-02 需 `f_b ≥ 100`；`seg=` `move ≥ 4` 含正反。
- **不足时输出**：无 `events.jsonl` ⟹ `not_evaluable{family:"software_induced_error", why:"无事件上下文，无法区分机械尖峰与调度抖动"}`
  （R-30 原文）；机械侧可继续判但该项跳过、置信 ≤ 0.5。补采：上位机日志导 `events.jsonl`（`source=host` 的 `pause`/`gc`
  含 `detail.duration_ms`）+ 共用 `bTrigger_Scope` 触发沿以置 `sync.verified = true`；激励 = **在 PC 上主动加负载**
  （开 IDE/备份）提高 host 停顿概率而不动机械——这是本对唯一的强证伪实验（对应 §4 反事实）。

### CP-7 `software_induced_interp_buffer_underrun ↔ electrical_feedforward_mismatch`（软件族）
- **为何混**：路径/加速期误差都抬高，`tracking.path_segments[].corr_fe_vs_accel ≥ 0.7` 与
  `ff_mismatch.fe_vs_accel_corr ≥ 0.6` 同时成立，都"看起来像前馈没给够"。
- **决定性判据**：**分布形态 + 事件对齐**。欠载是**离散突进**：`path.fe_max ≥ 2.0·path.fe_rms`（R-19#4）
  ∧ `interp_underrun_during_path/count ≥ 0.7` ∧ `fe_spike_aligned_to_underrun/fe_spike_count ≥ 0.5`；
  前馈失配是**连续不对称**：`asymmetry_ratio ≥ 1.5` 而 `fe_max/fe_rms` 不显著、无 `interp` 事件对应。
  `evt=` `source=interp` 带 `detail.buffer_level`/`lookahead_ms`；`seg=` `path ≥ 1`（理想 ≥ 5）；`causal_claims_permitted == true`，否则本对**只能**给共现描述。
- **不足时输出**：`segment_coverage.path == 0` ⟹ `interp_underrun_during_path` null ⟹
  `not_evaluable{family:"software_induced_error", why:"无 path 段，插补欠载语境不存在"}`；补采：连续路径 `kind = path` 含拐角 ≥ 5 段；
  **同一 G 代码做插补前瞻加倍/减半 A/B**（欠载对前瞻敏感、前馈失配不敏感）；补 `vel_cmd` 使 `velocity_feedforward_pct_applied` 可估。

### CP-8 `electrical_current_loop_bandwidth ↔ electrical_feedforward_mismatch`
- **为何混**：都造成加速段误差且 `fe_vs_accel_corr ≥ 0.6` 共有；`e ≈ a/ωn²` 使**幅值无法区分**（R-12 排除项原文）。
- **决定性判据**：`asymmetry_ratio` —— 前馈 `≥ 1.5` vs 带宽不足 `∈ [0.9,1.2]`（滞后对称，R-12 支路B）；
  辅判据 `ripple.probing[].correlated_with_cur_q ≥ 0.7` + `cur_cmd` 与 `cur_q` 的显著滞后；支路A（有 `drive.*`）
  `current_loop_bandwidth_hz < 10·velocity_loop_gain_hz` 被违反。`band=` R-12 需 `f_b ≥ 200`；`seg=` `probing ≥ 1`。
- **不足时输出**：`drive.*` 缺失 ⟹ 支路B 命中一律 `unverified`（纪律 3）+ CAP-6 ≤ 0.55；补采：`cur_cmd` 与 `cur_q`
  同采样率导出 + **电流指令阶跃激励**（恒速 `probing` + 小幅转矩扰动）测一阶时间常数。

### CP-9 `software_induced_settle_window_too_short ↔ software_induced_polling_latency ↔ electrical_position_pi_detune`
- **为何混**：都表现为"到位后仍有误差/抖"，`settling_time_ms` 与 `ringing_cycles_to_settle ≥ 2` 共用。
- **决定性判据**：**是否会进带 + 散布形状**。`settling_time_ms == null ∧ limit_cycle_present == true` ⟹ R-14（真自激）；
  `settling_time_ms != null ∧ median(settling_time_ms) ≥ 1.2×(t_done − t_start)` ⟹ R-23（判太早）；
  `n_by_source.motion ≥ 10 ∧ T_poll 的 CV ≤ 0.2 ∧ 到位时刻散布 ≥ 0.5·T_poll` ⟹ R-24（采样太晚、系统性偏后）。
  `evt=` `motion/move_started`、`move_done`（含 `detail.settled`）；`seg=` `settling ≥ 3`；`fs ≥ 200 Hz`。
- **不足时输出**：无 `move_done` ⟹ `t_done` 不可得 ⟹ `not_evaluable{software_induced_settle_window_too_short, why:"无 move_done 事件，判定窗与实际整定不可比"}`；
  补采：位置比较/`settled` 位翻转的原始时刻（`io` 通道，与 `fe` 入带时刻差须 `> τ_u` 才作证据，纪律 6）+ 同一 `settling`
  段重复 ≥ 10 次的到位散布分布。R-23 与 R-24 同成立 ⟹ 合并为一条建议（R-24 排除项原文）。

### CP-10 `software_induced_bus_cycle_miss ↔ software_induced_host_thread_jitter ↔ software_induced_interp_buffer_underrun`
- **为何混**：同一批 `fe` 尖峰、同一族、都靠 `event_context` 对齐——R-28 的存在就是为它而设。
- **决定性判据**：**事件源独占性 + 波形形态**。`network` 丢周期 ⟹ `pos_cmd` 上**单周期保持平台**
  （现由 C2 `event_context.bus_cycle_hold_max_ms` 承载，A-9）；`interp` 欠载 ⟹ **速度骤降/停顿**；
  `host` 抖动 ⟹ 与工况无关（`move` 与 `dwell` 均匀出现）且 `host_pause_max_ms ≥ 20`。
  数值择优：`s_host`、`s_intp`、**`s_net = fe_spike_aligned_to_network_miss / fe_spike_count`**、
  `s_vision = fe_spike_aligned_to_vision_result / fe_spike_count`（后两条**已可参与择优**，原
  "G-5/G-9 恒 null、不参与"的口径随 A-9 落地作废）；成立条件仍是
  `max ≥ 0.5 ∧ max − second ≥ 0.2 ∧ alignment_residual_ms ≤ τ_u ∧ permitted == true`。
- **总线叶的可达性升级（A-45，D-6 已收口）**：本叶不再"只能共现级"。§1.3 N6.c 的三条件
  （① `bus_cycle_hold_max_ms` 与 `fe_spike_aligned_to_network_miss` 均非 null；② `sync.verified == true` 且
  `causal_claims_permitted == true`；③ `alignment_residual_ms ≤ sync.uncertainty_ms`，方向见 **A-82**）**齐** ⟹ 可进
  `hypotheses[]` 且 `confidence ≤ 0.6`（**CAP-11**）；**缺任一** ⟹ 共现级，禁入 `hypotheses[]`，只进
  `differential.considered`。上限来自结构：只有 `pos_cmd` 单通道可推断，没有驱动器 WKC 通道。
- **不足时输出**：区分度不足 ⟹ 全族进 `considered` + `not_evaluable{family:"software_induced_error",
  why:"对齐区分度不足"}`（R-28 末支），**不得**因 `network_cycle_miss_count ≥ 1` 就直接归因总线；
  补采：①`fs ≥ 2 kHz` 满足 `1/fs ≤ τ_u/2`（否则任何尖峰级对齐都不可分辨，INV-7）；②WKC/DC 同步逐周期日志；
  ③在 `path` 段做"故意给上位机加负载"的对照激励（提高 `host` 停顿率而不动网络与插补）。

### CP-11 「适配器把指令位置 DPOS 冒充反馈」↔「反馈通道本身恒零/未接」（采集/适配层门，A-46 新增）

**本对不产叶**：两侧都不是 KB0 §2 的 22 个 slug（属采集/适配层缺陷，非机械-电气-软件三类成因），
因此按 A-17 的门禁规则类处理——输出**登记义务**（`family: null`），进 `differential.not_evaluable` 与
`audit.rules_fired`，计入 C5 的拒答正确率，**永不**进 `hypotheses[]`。签名口径按 A-33：这是"第三方实现审计中
出现的缺陷形态"（逻辑自洽的失败模式），不得写成厂商手册确认的错误，也不得写成我们的发现。

- **为何混**：两者在波形上都表现为 **`pos_fb` 不响应实际运动**——一个是"它只跟着指令走、不跟负载走"，
  一个是"它压根不动"。此时 `fe = pos_cmd − pos_fb`（C1 派生规则 2）在两种情形下都能算出来，
  且形态截然不同（前者恒 ≈0、后者与 `pos_cmd` 同形），于是所有以 `fe` 为轴的判据（R-01…R-24）都在读一个
  伪量：**整条轴看起来"完美"或"跟随误差 = 指令本身"**。这是比误判更糟的失效，因为它让报告没有任何异常可报。
- **决定性判据**（按可判别性排序，全部只引用已登记路径）：
  1. **`sensor_disagreement.pairs[]`**（C2）——存在第二路独立反馈时是决定性的：
     `a == "pos_fb"`、`b ∈ {laser_ref, scale_fb}`（经 C1 `cross_validation.pairs` / `extra_channels` 引入）。
     DPOS 冒充 ⟹ `pos_fb` 与外部反馈**分歧大**（`rms_counts` 与运动幅值同量级、`max_counts` 大）
     而 `pos_fb` 自身形态光滑无纹波；恒零/未接 ⟹ `pos_fb` 方差为 0，`rms_counts` ≈ 外部反馈自身的运动幅度。
  2. **`quality_ref.quantization_step_counts`**（C2）——DPOS 是整数 counts 指令，`pos_fb` 台阶与 `pos_cmd`
     同源同值（`== 1.0` 且与 `position_quantum_mm` 一致）；恒零通道没有台阶统计量，该字段应为 `null`
     并进 `unavailable`（C2 规则 2：null 不是 0）。
  3. **阶跃响应处 `pos_fb` 是否完全无变化**——在 `step_response[]` 对应的 `move`/`settling` 窗内做
     `pos_fb` 逐样本差分：恒零/未接 ⟹ 差分**恒为 0**（真正的平线，连量化噪声都没有）；
     DPOS 冒充 ⟹ 差分逐点等于 `pos_cmd` 的差分（含梯形速度形状）。
     ✅ 该判据已有 C2 路径（**A-48**，R-6 由此收口）：`feedback_integrity.pos_fb_static_on_move_ratio`
     = "`move` 段内 `pos_fb` 完全不变而 `pos_cmd` 在动的样本占比"（定义见 KB3 §1.13b，恒零/未接 ⟹ ≈ 1.0，
     DPOS 冒充 ⟹ 0.0 因为差分逐点等于 `pos_cmd` 差分）。故第 3 条**可以**写成
     `supporting_evidence[].feature`，但只能引用该 C2 路径，不得引用"原始波形差分"这种不存在的字段名；
     无 `move` 段时该字段为 `null`（KB3 同表），第 3 条回到定性核对并按 INV-4 放弃。
  4. **是否存在第二路反馈**——C1 `cross_validation.pairs` 非空 ⟺ 第 1/2 条可求值；为空 ⟹ 本对**不可判**。
- **硬结论（A-46 原文，不可放宽）**：**没有第二路独立反馈时不得归因**——既不能判"适配器冒充反馈"，
  也不能判"反馈通道恒零/未接"，只能登记 `differential.not_evaluable` 并**写明缺哪一路**（门/拒答类条目按
  A-17 无 slug，`family: null`），措辞取：
  `{"fault_mode": null, "family": null, "rule_id": "R-22 签名表 / CP-11",
    "why": "cross_validation.pairs 为空，无第二路独立位置反馈（如 laser_ref/scale_fb），
    pos_fb 的真实性无法交叉验证；既不判定通道恒零，也不判定指令回灌冒充"}`。
  与之配套：`next_data_to_collect` 必须请求一路**与驱动器无关**的位置测量（激光干涉仪 / 光栅尺读头 /
  直线编码器另一路），并说明补上后解锁的正是第 1/2 条。
- **禁止项**：① 不得因为"看起来 `fe` 太小、控制太好"而输出"无故障"（INV-11，把看不见说成没有）；
  ② 不得用 `pos_cmd` 与 `pos_fb` 的高相关（`corr ≈ 1`）当作"反馈正常"的证据——冒充情形下这个相关性是**定义成立**的，
  用它自证即 §2.7 的反自证条款；③ 不得把本对任一侧改写成 `software_induced_pulse_eq_overwritten` 的叶子上报，
  那是**另一个**成因（系数被覆盖，通道本身仍是真反馈）。
- **与 KB3 的衔接**：判据落在 KB3 R-22 的缺陷签名表（A-33/A-46 落点），本文只登记混淆关系与输出纪律，
  不重复阈值。

**覆盖检查**：必含 CP-1（Top 混淆对，C5 §6）✓；含 `software_induced_*` 的 CP-5/6/7/9/10/11 共 6 对 ≥ 2 ✓；
总数 **11 对**（CP-11 为 A-46 回写的采集/适配层门，不产叶）。

---

## 4. 反事实自检（归因前必跑）

### 4.1 机制

每个假设写入 `hypotheses[]` **之前**，引擎执行其反事实检查项：**"若 h 不成立，我在没有用来立 h 的那部分数据上还应看到什么？看到了吗？"**

三态判定（逐项独立）：**PASS**（反事实预期未出现，`C` 不变）；**FAIL**（预期"不该看到"的东西出现了 ⟹
按 §2.4 记 `v_j`；若命中 KB3 排除项的否决条件则直接出局）；**UNRESOLVED**（依赖 null/越带/缺段无法求值 ⟹
CAP-9 封顶 0.60 + 在 `not_evaluable` 追加"反事实项 `<id>` 不可求值"，INV-11 禁沉默）。

**held-out 约束（关键）**：检查项求值的 `kind`/通道必须与形成该假设的证据**不相交**——假设由 `move` 段的
谱峰立起，反事实就必须在 `dwell`/`rest`/`probing` 求值；假设由 `fe`/`cur_q` 立起，反事实优先在 `vel_fb` 或
`pos_cmd` 侧求值。同窗自检等于用同一份残差既拟合又验证，是拟合优度幻觉的来源。

### 4.2 检查项表（可判定式，只引用已登记路径与 KB3 阈值）

| 假设 | 若 h 不成立还应看到 | 求值面（held-out） | FAIL 后果 |
|---|---|---|---|
| `mechanical_resonance` | 结构模态为主因则**无激励也应余振**：`present_in_dwell == true` 且 `ringing_cycles_to_settle ≥ 3`；若 h 不成立则 `dwell` 无峰而 `asymmetry_ratio ≥ 1.5` | `dwell`/`settling`（假设由 `move` 峰立起） | 与 R-26 ②/③ 一致化：改判 `electrical_feedforward_mismatch` |
| `mechanical_resonance`（R-04 配对支） | `antiresonance_freq_hz > freq_hz`（INV-3 被破坏）则"双惯量配对"必不成立，还应看到 `notch_filters` 覆盖该谷或存在双测量构型 | `abs(H1)`；负载侧第二测量 | **否决**（不扣分），转 R-10 伪谷支 + 写 `contradicting_evidence` |
| `electrical_feedforward_mismatch` | 不成立则 `tracking…corr_fe_vs_accel` 与 `ff_mismatch.fe_vs_accel_corr` 应不一致（一 ≥0.6 一 ≤0.3）；且 `a_max/2` 配对样本上 `asymmetry_ratio` 应基本不变 | `path` vs `move` 互查；加速度 A/B 配对 | `v = 0.10`；两组无显著差异 ⟹ 改判欠载（CP-7） |
| `mechanical_backlash` | 不成立则偏差应**随行程增长**（`abs(β) ≥ 0.002`）且 `CV ≤ 0.3` 被破坏 | 短/长行程配对 | 交 R-27 ⟹ 改判 `software_induced_pulse_eq_overwritten` |
| `software_induced_pulse_eq_overwritten` | 不成立则同一 `step` 重复定位散布 `> 3·量化台阶`（不可重复）且两 `recipe` 偏差差 `< 3·σ_err` | 跨 `recipe` 配对 | `v = 0.20`（本叶的强反证） |
| `software_induced_host_thread_jitter` | OS 调度不分工况 ⟹ 不成立则尖峰只出现在特定 `kind`，且 `dwell` 段 `aligned_to_host_pause/count ≈ 0` | `dwell` vs `move` 分层对齐比 | 尖峰锁反向时刻 ⟹ 改走 R-02/R-08（CP-6） |
| `software_induced_interp_buffer_underrun` | 不成立则欠载随机分布于非 `path` 段（`during_path/count < 0.4`），且 `corr_fe_vs_jerk ≥ corr_fe_vs_accel` | 非 `path` 段事件分布 + jerk 侧 | `v = 0.10`；两项同 FAIL ⟹ 移出 `hypotheses` |
| `software_induced_bus_cycle_miss` | 不成立则 `n_alarm == 0` **且** `event_context.bus_cycle_hold_max_ms` 无异常抬升 **且** `event_context.fe_spike_aligned_to_network_miss` 相对 `fe_spike_count` 占比 ≈ 丢周期在时间窗上的随机占比（两字段 A-9 已落 C2，原"C2 无该特征 ⟹ UNRESOLVED"的口径作废，D-6 → A-45） | `drive`/`network` 事件 + `pos_cmd` 侧（`fe` 侧的证据不用于自证，§4.1 held-out） | 三条件齐（§1.3 N6.c）⟹ `v = 0.20/0.10` 照常扣分、命中后受 **CAP-11 ≤ 0.60**；条件不齐 ⟹ 停共现级 + CAP-9 |
| `software_induced_late_vision_result` | 不成立则该步 `path.fe_max/fe_rms < 2.0` 且 `vision/n_events < 0.1` | 无视觉步骤的 `scanning`/`curing` | `v = 0.10` + 要求补 `vision` 计数 |
| `software_induced_settle_window_too_short` | 不成立则 `settling_time_ms < 1.2×(t_done−t_start)` 应不成立，且到位时刻 `abs(fe) < settle_band_counts` | 与 `limit_cycle_present`、`ringing ≥ 2` 互查 | 与 R-14 分叉（CP-9） |
| `mechanical_crawling` | 不成立则 `sawtooth_freq_hz` 应随 `vel_mean` 线性变化（`f ∝ v`）即跨速段 CV > 0.3 且 `phase_locked_to_pos_modulo == true` | 多速度段互查 | 改判 `mechanical_encoder_periodic_error`（CP-4） |
| `mechanical_thermal_drift` | 不成立则冷/热机配对 `dwell` 段 `fe` 斜率差 `< 2 counts/min`，且去时间趋势后 `thermal_fe_correlation_r` 不再显著 | 冷/热机同轨迹配对 | `v = 0.20`；`temp` 缺失 ⟹ UNRESOLVED（与原 `not_evaluable` 并存，两条独立登记） |
| `electrical_torque_ripple` | 不成立则 `harmonic_ratios` 非整/半整数（或 null）且 `present_in_rest == false` | `rest` 段 `cur_q` 谱 | `v = 0.10`；null 走 INV-4 而非"无谐波" |
| `electrical_position_pi_detune` | 不成立则降一档 `meta.drive.rigidity_level` 的对照样本上 `limit_cycle_present` 应仍 `true`（自激对增益敏感） | 增益阶梯配对（无 ⟹ UNRESOLVED） | 要求补 `next_data_to_collect`（`rigidity_level` ×3 档阶梯） |

### 4.3 它如何防住自验证循环

自验证循环有两条通路，反事实自检各断一条：① **同窗自证**（用自己拟合的残差验证自己）——held-out 约束使
"能算出峰"不再等于"别处也自洽"；② **干净数据幻觉**（合成器只注入单一故障，于是任何假设都没有反例），
用可度量的分层背离指标对付它：

```
CF_pass_rate(tier) = 该 tier 上 PASS / (PASS + FAIL)          （UNRESOLVED 单列，不入分母）
CF_Tier_Divergence = CF_pass_rate(T3) − CF_pass_rate(T1+T2)
```

| 观察 | 结论 | 动作 |
|---|---|---|
| `CF_pass_rate(T3) < 1.0` | **管线有 bug**（T3 按构造必须全 PASS，故障是它自己注入的） | 停下补信号处理层，不往下堆 agent（对应 C5 §7 的 W+7 止损） |
| `CF_pass_rate(T3) = 1` 且 `CF_Tier_Divergence ≤ 0.05` | 合成集与真实集同等"不干净" ⟹ KB5 故障注入足够丰富，判据未过拟合 | 可继续；T3 仍只做流程主张（C5 §1） |
| `CF_pass_rate(T3) = 1` 且 `CF_Tier_Divergence > 0.15` | **判据太松 / 生成器太理想**：真实数据里大量反事实 FAIL 被 T3 的干净性掩盖 | 禁止用 T3 调阈值；回 KB5 补噪声与叠加故障（多故障同注、`temp` 漂移、量化台阶、丢事件流），每条 FAIL 落 `bench/failures/`（C5 §6） |

命名纪律（A-47）：本量只叫 `CF_Tier_Divergence`（T3 与 T1+T2 的**分层背离**）；
C5 §3 那个"命中案例 vs 错判案例"的差叫 `CF_Discrimination`（**区分度**）。两者同族不同量，
早期草稿共用 `Divergence_Index` 一名，已改名消歧。

这条指标不检查"我答对了吗"（那是自证），而检查"我在合成数据上的自信在真实数据上是否同样成立"——
把 C5 §1 的层级切分变成一个可监控数值。建议与 ECE 分层表放在一起，构成"我如何证明自己没骗自己"的那一页。

### 4.4 软件族与 `simulation_validated` 的范围（A-43，G-12 有条件开禁）

反事实自检在 `software_induced_*` 上有别的族没有的特权：KB5 能**主动注入**故障事件（host 停顿 / 插补欠载 /
总线丢周期，且含"无事件"与"未同步"两个孪生样本），因此"若 h 不成立我该看到什么"可以在受控对照样本上求值，
而不必等现场复现。据此把层级划清（CAP-12 是它的机器判定形式）：

| 结论类型 | 允许的 `expected_effect.basis` / 证据层级 | 条件与措辞上限 |
|---|---|---|
| **检出类**（"这类形态能否被管线检出 / 该叶是否成立 / 反事实项 PASS"） | 可由 KB5 事件注入支撑，标 **`simulation_validated`** | 必须成对给出孪生样本（注入 vs 未注入、`sync.verified` true vs false）；措辞上限仍是"在该合成构型下可检出"（T3 不支撑任何能力/准确率声明，C5 §1、KB0 §4） |
| **改进量 / 参数建议**（`expected_effect` 的数字、"改 X 后 fe_rms 降 N%"） | **恒 `rule_heuristic`**（或方向性的 `unverified`），**不给数字** | 与 C3 规则 4 的三值枚举一致；软件族的"改进"依赖真实调度器与总线仲裁行为，仿真给不出 |
| 任何引用仿真的段落 | — | **必须**带 caveat 原文：**"仿真不含真实调度器与总线仲裁"**；缺 caveat 即视为 §2.10/INV-13 的措辞越级，拒绝出报告 |

对照 §4.1：软件族反事实的 held-out 面天然落在"另一组注入配置"上，而不是同一窗口的另一条特征——这既是它的
优势（可实验），也是它的天花板（结论层级到此为止）。**开禁的只是措辞层级，不是置信上限**：CAP-2（无因果开关
⟹ 共现）、CAP-8（对齐残差）、CAP-11（总线叶 ≤ 0.60）一律照常生效。

---

## 5. 落地自查（供主线程做跨文件一致性，KB0 §6）

1. 22 个叶 = KB0 §2 全部 slug，无孤儿，每叶有 KB3 主锚点（§1.1）✓；**叶/门口径为已裁口径**（KB0 §6 检查 3，
   D-13 → A-17）：`R-25/26/27/28/29/30` + KB6 `R-37/49/50`（`family: null`）在本文中一律表述为**边/门**，
   出现在 §1.1"非叶"段、树正文的仲裁/剪支行与 §1.3 N8 交叉锚点末行，无任何一处作为 `LEAF(...)` 出现 ✓
2. 特征路径：伺服侧全部走 C2，未新增字段；工艺/标定侧本文**未引用**（A-34/A-36 后如需引用走 C7
   `process.*`/`calibration.*`/`cycle_stats.*`，口径在 C7 §2.2/§4.2）✓；
   阈值一律写成 `R-NN#k` 引用，无自造字面量 ✓；
   ~~例外两处~~ **两处已收口**（原 D 表"残余登记项" R-5 / R-6）：`quality_ref.dt_jitter_ratio` 由 A-49
   镜像进 C2，CP-11 第 3 条判据由 A-48 走 `feedback_integrity.pos_fb_static_on_move_ratio` ⟹
   本文引用路径 100% 在 C2/C7，无 C1-only 路径、无自造路径 ✓
3. 频带门禁在 INV-1/INV-2/CAP-5 三处**强制执行**（阻塞 ≠ 削弱 ≠ 封顶，语义已分离）✓；
   因果开关在 INV-5/INV-6/E1/E2/CAP-2 强制执行 ✓；总线叶另有 CAP-11（A-45）、软件族层级另有 CAP-12（A-43）✓
4. INV-3（`f_a < f_0`，且 `f_res/f_anti = sqrt(1+λ)`）作为树级约束写进 N1.a.1、§4.2 第二行、算例 A 前提与
   CAP 逻辑 ✓；`meta.sensor_config == "unknown"` 的顺序不判 + 封顶已进 INV-3 违反列（A-1）✓
5. 全文无"未发现/无 X"式表述，不可评估一律落 `not_evaluable`（INV-11）✓；未修改 KB3/C2/C3/C5/C6/C7 任何内容 ✓
6. 命名纪律（A-18/A-19，C3 规则 10）：`fault_mode`/`LEAF()` 位置全为 KB0 §2 slug；`software_induced_error`
   只以 `family` 键出现在 `not_evaluable`/`considered`（§1.5 族级标签纪律）✓
7. 措辞纪律（A-31，C3 规则 14）：INV-13 + §2.10 已把"叙述层不得高于 `source_tier`，越级 ⟹ 拒绝出报告"
   写成可机器判定的拒绝条件 ✓
8. 混淆对总数 **11**（含 A-46 新增的 CP-11，不产叶）✓；D 表 **13 行全部带 A-xx 裁决标注**，
   本文侧无未收口条目（A-30）✓

## D 类裁决回写（已收口）

本表原为"**待主线程裁决（D-1 … D-13）**"。KB0 §7/§7.1/§7.2/§7.3（A-1…A-91）已逐条裁决，故转为**回写记录**：
原始冲突描述与本文当时的临时口径**原样保留**以便追溯，新增"裁决"与"状态"两列。状态取值限定为
`已裁-契约侧已改` / `已裁-KB4 侧本文件已改` / `不采纳`（两种都成立时并列写）。**未删任何行**
（A-30 纪律：实现期前清单须清空 = 每行必须带裁决标注，而不是把行删掉）。

| ID | 冲突/缺口（原文保留） | 证据位置 | 本文临时口径（历史） | 裁决 | 状态 |
|---|---|---|---|---|---|
| D-1 | **C3 示例置信度与本文公式不一致**：示例 H1 `overall_confidence = 0.78`，按 §2.3 重算得 `C(H1) = 0.65`、`verdict = 0.59`（示例未对反证/样本量/`not_evaluable` 扣分） | C3 `verdict` + H1 vs 本文 §2.2–§2.3 | 以本文（更保守）为实现口径；建议把示例数值标注为"示意值，非引擎输出"或同步修正 | **A-20**（C3 规则 13） | `已裁-契约侧已改` + `已裁-KB4 侧本文件已改`：C3 规则 13 已把示例数字定为示意值并写出重算值；本文 §2.3 算例 A 注记同步改为"D-1 → A-20 已收口"，实现以本文 §2.2–§2.3 为准。**该收口又被 A-72 推翻一步**：把不一致"标注成示意值"仍是把不可复算的数字留在文档里；现已把 C3 示例改成**可由其自身列出的证据逐格复算**（`C(H1) = 0.652 ⟹ 0.65`、`verdict = 0.586 ⟹ 0.59`、`penalty` 取 `rho_prime` 档位），并立 **C3 规则 15** 禁止此类不一致再现 |
| D-2 | **INV-3 顺序判据 vs 契约示例**：C2 示例 `resonance.candidates[0]` = 峰 `1181 Hz` + `antiresonance_freq_hz = 1420 Hz`，C3 示例同值。共置两惯量必有 `f_a < f_res`，**该组合物理不成立** | C2 `resonance.candidates`、C3 H1；KB3 R-04#1、KB5 §1.2 | 本文已把 `f_a < f_0` 写成树级 INV-3；**契约示例需修正**（按 `λ = 6.2 ⟹ f_m/f_a ≈ 2.68` 把谷移到峰下方，或改用低 `λ` 配对并声明单惯量不可分） | **A-1** | `已裁-契约侧已改` + `已裁-KB4 侧本文件已改`：C2 示例 A 已改为 `440 / 1181`（λ≈6.2，`f_res/f_anti = sqrt(1+λ) ≈ 2.68`），并新增 `meta.sensor_config`（C1 派生规则 7、C2 规则 9）；本文 INV-3 与算例 A 前提已按该组数值逐条核对（峰 1181、谷 440） |
| D-3 | **C2 示例内部 fs 自相矛盾**：顶层 `fs_hz = 8000.0`、`resonance.nyquist_hz = 4000.0`，但 `freq_limits.fs_hz = 1000.0`、`nyquist_hz = 500.0`、`reliable_band_hz = 400.0`、`blocked_rules = ["R-03","R-04"]`；KB3 §1.14 要求三者一致 | C2 顶层 vs `freq_limits` vs `resonance` | 本文两个算例分别按纯 8 kHz / 纯 1 kHz 计算，未混用；示例需统一（若取 1 kHz，则 1181 Hz 峰本身必须进 `blocked`） | **A-2** | `已裁-契约侧已改`：C2 拆为例 A（8 kHz 完整可诊断）与例 B（1 kHz，把"看不见"写成结构化事实）；本文算例 A 取 8 kHz、算例 B 取 1 kHz，与两例分别对齐，无混用 |
| D-4 | **C2 示例 `unavailable` 与字段值并存**：`thermal_drift_counts_per_min = 3.1`、`backlash_estimate_counts = 268.0` 同时出现在 `unavailable`；另 `spectral.cur_q.freq_hz/psd = []` 却给出 `dominant_freq_hz = 1182.0` | C2 `global.*` vs `unavailable[]`、`spectral.cur_q` | 本文按 INV-4 处理，未采用这些值作证据；示例需消除自相矛盾 | **A-3** | 部分收口：`已裁-契约侧已改`（`thermal_drift_counts_per_min`/`backlash_estimate_counts` 已从 `unavailable` 移除，矛盾情形升格为 C2 规则 13）+ `已裁-KB4 侧本文件已改`（本文 INV-4 口径保持：依赖为 null 即放弃，不把 null 当 0）。**仍有两处同类的活矛盾**，见 R-7：`global.thermal_fe_correlation_r = 0.71` 与 `unavailable` 里同字段并存；`spectral.cur_q.freq_hz/psd = []` 却给 `dominant_freq_hz = 1183.0` |
| D-5 | **C2 示例分段覆盖与数组矛盾**：`segment_coverage.probing = 0` 但 `ripple.probing` 含 `segment_id 5`（KB3 §1.4 要求此时数组为空） | C2 `ripple.probing` vs `segment_coverage` | 本文 §1.4 末段把该情形定为解析缺陷 ⟹ 拒诊断；示例需补 `probing ≥ 1` 或清空数组 | **A-3**（→ C2 规则 13） | `已裁-契约侧已改` + `已裁-KB4 侧本文件已改`：C2 示例 A 现为 `segment_coverage.probing = 1`（与 `ripple.probing` 非空自洽）；本文 §2.3 算例 A 前提随之从 `probing 0` 改为 `probing 1`（不影响任何一行 `S(e)` 计算，算例用的 `n_ref` 均取 Welch/dwell/rest/move） |
| D-6 | **`software_induced_bus_cycle_miss` 达不到归因级**：C2 无"单周期保持"专属特征（KB3 G-5）、`s_net = null`（R-28），R-20 明文只能共现 | KB3 R-20/R-28；本文 N6.c、CP-10 | 本文已标注"共现级"；需 C2 增补（如 `pos_cmd` 单周期保持计数/最大保持时长、`fe_spike_aligned_to_network_miss`）后方可进 `hypotheses` | **A-9**（字段侧）+ **A-45**（分级侧） | `已裁-契约侧已改` + `已裁-KB4 侧本文件已改`：C2 已增 `event_context.bus_cycle_hold_max_ms`、`fe_spike_aligned_to_{network_miss,vision_result,recipe_change}`；本文 §1.3 N6.c 改写为**三条件升级规则**（①两字段均非 null；②`sync.verified == true` 且因果开关为真；③`alignment_residual_ms ≤ sync.uncertainty_ms`，方向由 **A-82** 更正 A-50 ⟹ 可进 `hypotheses` 且 `confidence ≤ 0.6`；缺任一 ⟹ 共现级、禁入 `hypotheses`、只进 `differential.considered`），并在 CAP 表新增 **CAP-11**；CP-10 的 `s_net`/`s_vision` 已恢复参与 R-28 择优；§4.2 对应行的 UNRESOLVED 口径作废。**残余 R-1/R-2 已在下方"残余登记项"裁决闭环** |
| D-7 | **`software_induced_error` 不是 KB0 §2 的 slug**，但 C2 规则 8 / KB3 纪律 5 / R-30 都要求用它登记 `not_evaluable` | C2 规则 8、KB3 纪律 5 与 R-30 | 本文口径：它是**族级标签**，只允许出现在 `differential.not_evaluable` / `considered`，禁止出现在 `hypotheses[].cause`；建议 KB0 §2 正式收录并声明其域 | **A-18** | `已裁-KB4 侧本文件已改`：KB0 §2/§6 已把它定为族级标签（域见 KB0 §6 上方说明）；本文 §1.5 新增"**族级标签纪律（A-18）**"，E1 行与 §1.3 N6.e、算例 B 变体、CP-5/6/7/10 的登记一律用 `family` 键（照 C6 §4 原文），并明文禁止它作为叶子出现在 `hypotheses[].fault_mode`。**残余见 R-3** |
| D-8 | **C3 示例的 `fault_mode` 命名与 KB0 §2 不一致**：`feedforward_mismatch`、`encoder_eccentricity`、`friction_crawling`、`thermal_drift`、`gain_too_high_hunting`、`limit_cycle`、`following_error Compensation`（含空格/大写） | C3 H2、`ruled_out_alternatives`、`differential.considered` | 本文全用 KB0 slug；建议 `hypotheses[].fault_mode` 强制 KB0 slug，自由文本只允许在 `considered`/`not_evaluable`（与 KB6 §28 声明一致） | **A-19**（C3 规则 10） | `已裁-契约侧已改` + `已裁-KB4 侧本文件已改`：C3 规则 10 已强制 `fault_mode` 取 KB0 slug、显示名只进 `display_name`/`considered`；本文正文原本即全 slug 写法（旧名只出现在本行对 C3 示例的引用里，故保留），§1.1 新增"**slug / `display_name` 分工**"逐条给出旧名 → slug 对应，并说明 `following_error Compensation` 无对应 slug |
| D-9 | **C5 指标表无"反事实通过率分层背离"**（本文 §4.3 的 `Divergence_Index`） | C5 §3、§4 消融表 | 本文已定义并给出三条判读规则，供 C5 追加；建议同时进消融实验 | 无独立 A 编号（A-30 家族） | `已裁-契约侧已改`：C5 §3 已列"反事实通过率背离指数"指标。**残余见 R-4**（两处定义的不是同一个量） |
| D-10 | **C3 缺字段承载本文确定性输出**：无 `hypotheses[].severity`、无 `supporting_evidence[].strength`、无 `contradicting_evidence[].penalty` | C3 `hypotheses[]` 结构 | 本文只在 `rationale`/`audit.rules_fired` 表述这些量，不进入可校验的 `rank` 链；建议 C3 追加三个可选字段 | **A-21**（C3 规则 13） | `已裁-契约侧已改`：三字段已定为**必填确定性数值**并进排序链；本文 §2.9 字典序 `rank` 与 §2.4 `v_j` 与之同调，本文侧无需改动（已核对） |
| D-11 | **文件名引用不一致**：C3 规则 3 指向 `KB4-attribution-tree.md`，本文件为 `KB4-attribution-model.md`（KB0 §5 命名式） | C3 不可协商规则 3 | 建议主线程二选一并全局改引用 | **A-22** | `已裁-契约侧已改`：统一为 `KB4-attribution-model.md`（C3 规则 3 现指向本文件名，已 grep 核对全库无 `KB4-attribution-tree` 残留引用） |
| D-12 | **`bandwidth.confidence` 上界 0.6 与 C2 示例值恰好相等**，实现若直接照抄示例值会掩盖"试图给更高值"的越界 | C2 `bandwidth.confidence` vs KB3 §1.10 | 本文按 KB3 锁定上界执行 CAP-1；建议加加载期校验 `bandwidth.confidence ≤ 0.6`，违反即拒该样本 | **A-23**（C2 规则 12） | `已裁-契约侧已改`：加载期校验 `≤ 0.6` 与三项 `fs` 自洽校验已写入 C2 规则 12，越界拒样本；本文 CAP-1 保持不变 |
| D-13 | **KB0 §6 检查 3 要求"KB4 归因树的叶子 = KB3 规则集合"**，但 KB3 的 `R-25`/`R-26`/`R-27`/`R-28`/`R-29`/`R-30` 是无独立 cause 的元规则/仲裁器（其 `family` 借用某个 slug） | KB0 §6；KB3 §2 末段；本文 §1.1 末段 | 本文把"叶 = slug 集合、规则 = 到达叶的边/门"作为解释口径；建议 KB0 §6 检查 3 改写为"叶集合 = KB0 §2 slug，且每叶至少被一条 KB3 主判据规则锚定" | **A-17** + KB0 §6 检查 3 改写 | `已裁-契约侧已改` + `已裁-KB4 侧本文件已改`：该口径**不再临时**——KB0 §6 检查 3 已按建议改写；本文文件头、§1.1"非叶"段与 §5 检查 1 均已写成"已裁口径"，并把 KB6 `R-37/49/50` 的标注从 `family: —` 统一为 **`family: null`**（A-17 原文），门禁只进 `not_evaluable`/`audit.rules_fired` |

### 本轮 KB0 §7.1 直接落到本文的条目（无 D 编号）

| 裁决 | 落点（本文件） |
|---|---|
| **A-45** | §1.3 N6.c 三条件升级 + §1.3 N6.e 与 CP-10 的 `s_net`/`s_vision` 恢复择优 + §2.5 **CAP-11** + §4.2 总线叶行 |
| **A-46** | 第三部分新增 **CP-11**（含硬结论：无第二路独立反馈不得归因，只登记 `not_evaluable` 并写明缺哪一路）；覆盖检查改 11 对 |
| **A-43** | §2.5 **CAP-12** + §4.4 新节（检出类可 `simulation_validated`；改进量恒 `rule_heuristic`；caveat 原文强制） |
| **A-31**（C3 规则 14） | §0 **INV-13** + 新节 **§2.10**（措辞越级 ⟹ 拒绝出报告） |
| **A-17** | §1.1 非叶段与 §1.3 N8 交叉锚点行的 `family: null` 表述；§5 检查 1 |
| **A-18 / A-19** | §1.5 族级标签纪律、§1.1 slug/`display_name` 分工、§5 检查 6 |

### 残余登记项（本轮全部裁决完毕，2026-10-20）

> 本表引用的 **A-82 / A-83**（以及同轮出处的 **A-81**、块归属的 **A-84**、tier 的 **A-85**、
> 案例覆盖的 **A-86**）**已在 KB0 §7.3 成行**，事项/裁决+理由/落点三列齐全；
> KB0 §6 检查项 16–18 是这三类缺陷的可执行版本（残差与差值不得共用一个不等号、
> 出处不得带占位符、`A-NN` 唯一且连续）。本表保留"提出问题时的原描述"，不抹掉留痕。

| # | 事项 | 处置 |
|---|---|---|
| **R-1** | A-45 的升级条件③写作 `alignment_residual_ms > sync.uncertainty_ms`，与本文 N6.e / CP-10 / CAP-8 的 `alignment_residual_ms ≤ τ_u`（C2 规则 8 的 `causal_claims_permitted` 定义也在此方向）**方向相反**。本文按字面落地 A-45，同时执行"上限取 min"（③与 CAP-8 同时触发时生效封顶 0.40），因此不构成自相矛盾，但两条判据的意图需确认：是"残差可分辨才算对齐有效"还是"残差小于不确定度才算对齐有效"。 **具体后果**：在 C2 示例 A 上——按 A-45 字面，③ 成立与否取决于 `uncertainty_ms` 的取值；两种读法输出不同，本文算例 A 取保守的那个。 | **已裁 A-82（更正 A-50 的方向，保留其语义）**：`alignment_residual_ms` 是匹配对 `abs(Δt)` 的**中位数＝对齐残差**，越**小**越好；因果声明要求 `≤ τ_u`。"**大于** `τ_u`"那条纪律作用在**被声称的差值**（`vision_result_latency_p95_ms`、`bus_cycle_hold_max_ms`、两次到位时刻之差）与**对齐窗**上，不作用在残差上——两者曾被写成同一个不等号，其后果是"对齐越差越允许归因"，物理上不成立。本文 N6.c ③、N6.e、CP-10、CAP-11、门 G3、算例 B 的 G3 检查已同向；"上限取 min"的临时补丁删除（③与 CAP-8 现为同一条件的两面）。落点另见 C2 规则 8/14、C6 §3 硬规则 2、KB3 纪律 6/R-18/R-20/R-21/R-28、KB5 §7 表。**连带发现**：A-50 当时为凑 `>` 方向把 C2 示例 A 的 `uncertainty_ms` 从 1.0 改成 0.15，使该样本违反本文门 G5（`1/fs = 0.125 ms > τ_u/2 = 0.075 ms`），且 0.4 ms 的中位残差在 8 kHz 采样上小于三个样本、`0.15` 更是一个样本都不到；现例 A 取 `residual 0.25 / τ_u 0.5`（`0.25 = 2×1/fs`，`1/fs = 0.125 ≤ 0.25` ⟹ G5 ✓，残差 ✓）。 |
| **R-2** | KB3 R-20 / R-28 仍是"本叶只能共现级、`s_net = null` 不参与择优"的原口径（A-45 落点含 KB3 R-20，但 KB3 由另一会话在改）。 | **已闭环**：KB3 R-20 已改成三条件升级规则、R-28 的 `s_net`/`s_vision` 已恢复参与择优。本轮逐字复核了 canonical 三条件在 **KB3 R-20、KB3 R-28、KB4 §1.3 N6.c、KB4 CP-10/§2.5 CAP-11** 四处的文本，条件 ③ 已随 A-82 统一为 `≤`。 |
| **R-3** | C2 规则 8、KB3 R-30 与 KB3 §1 示例仍用 `{"fault_mode": "software_induced_error"}` 的键名登记族级不可评估，与 C6 §4 的 `{"family": ...}` 冲突；而 C3 规则 10 要求 `fault_mode` 位置只放 22 个 slug ⟹ 按 C2/KB3 的写法会直接违反 C3。 | **已裁 A-18 / A-51**：族级标签只能进 `family` 键。C2 规则 8、KB3 §0 纪律 5 与 R-30、本文 N6.e/CP-10 均已用 `family`。**残余一处**：KB2 §7 末尾（第 538 行）仍写 `{fault_mode:"software_induced_error", …}`，本轮已改。 |
| **R-4** | ~~两个不同量共用 `Divergence_Index` 一名~~ | **已裁 A-47**：本文量改名 `CF_Tier_Divergence`（T3 vs T1+T2 分层背离），C5 §3 那个改名 `CF_Discrimination`（命中 vs 错判的区分度），两处均已就地改名 |
| **R-5** | 本文两处引用 `quality.dt_jitter_ratio`（§1.3 N2 前置、N6.c），该字段只在 **C1 `meta.quality`**，C2 无镜像、C7 只有语境不同的 `power_channel.dt_jitter_ratio`。按 KB0 §3（A-34/A-36）它**不能**作为 `supporting_evidence[].feature` 出现。 | **已裁 A-49**：C2 `quality_ref` 扩为 C1 `meta.quality` 的**镜像**（含 `dt_jitter_ratio`），证据路径一律走 C2。本文两处已改 `quality_ref.dt_jitter_ratio`；§5 检查 2 的"例外两处"已随 R-5/R-6 双双收回。 |
| **R-6** | CP-11 第 3 条判据（阶跃窗内 `pos_fb` 逐样本差分是否**完全为 0**）在 C2 无对应特征路径。本文已声明该条只作定性核对、不写成证据，并要求第 1/2 条（已有路径）承担判定。 | **已裁 A-48**：C2 新增 `feedback_integrity` 特征组，其中 `pos_fb_static_on_move_ratio`（KB3 §1.13b 定义："move 段内 `pos_fb` 完全不变而 `pos_cmd` 在动的样本占比"）正是第 3 条的路径。本文 CP-11 第 3 条已改为引用该路径、可作 `supporting_evidence[].feature`；无 `move` 段时字段 `null` ⟹ 回到定性核对。C2 规则 15 同时禁止把该组字段当结论。 |
| **R-7** | C2 示例 A 仍有两处 D-4 类活矛盾：① `global.thermal_fe_correlation_r = 0.71` 与 `unavailable[]` 里同字段（"相关性样本 < 8"）并存；② `spectral.cur_q.freq_hz = []`、`psd = []` 却给 `dominant_freq_hz = 1183.0`。本文算例 A 因此**只**引用 `unavailable` 未覆盖的字段，并把 `mechanical_thermal_drift` 记进 `not_evaluable`（与 `unavailable` 同调），0.71 未用作任何证据。 | **已裁并清理（①→ C2 规则 14 第一条；②→ A-83）**：① `thermal_fe_correlation_r` 现为 `null` 且该字段在 `unavailable[]` 里有一行 ⟹ 互斥解除；`thermal_drift_counts_per_min = 3.1` 无 `temp` 仍合法（KB3 §1.1 该行定义它回归 `fe_dwell` 对**时间轴**的斜率，`temp` 只影响温度归因），C2 例 A 下已加说明防读者误判。② 空数组已换成非空预览，但**新写法又暴露出第三处不可复算**：预览数组 `0 / 1.2 / 2.5 / 3.7` 的步长不等于同层 `resolution_hz = 1.953125` ⟹ A-83 规定预览必须是"从 0 起的连续前缀 bin"，例 A 现为 `0 / 1.95 / 3.91 / 5.86`。本文算例 A 的引用纪律（只引 `unavailable` 未覆盖字段）保持不变，现在它与 C2 逐格对得上。 |
