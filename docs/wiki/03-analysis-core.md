# axiscope Code Wiki · 03 特征计算与归因核心层

覆盖 `features.py`、`confidence.py`、`rule_table.json`、`registration.py`、`engine.py`、`core_hash.py`。

## 1. `src/axiscope/features.py` — C2 特征层

入口 `compute(meta, ingest, pack_dir)`。首行分流：`meta.source.ingest_profile == "dialect_generic"` 走 `_compute_generic`（只保留时基与频带门禁，其余特征全 null + 逐路登记）；否则主路径。`events.jsonl` 按 C6 封闭词表校验，越界抛 `FeatureError`。

**输出特征包顶层恰 22 键**（`schema` = `"axiscope.features/1"`）：`ref, fs_hz, present_channels, freq_limits, position_quantum_mm, global, spectral, resonance, sensor_disagreement, feedback_integrity, ripple, crawling, ff_mismatch, encoder, quality_ref, step_response, tracking, bandwidth, event_context, segment_coverage, unavailable`（加 `schema` 共 22）。

| 特征族 | 算什么 | 关键实现 |
|---|---|---|
| `spectral` / `resonance` | PSD 主峰、`dominant_psd_ratio`、`tonality_index` | `_welch`（scipy `welch`，hann 窗，`nperseg=min(2048, N)`，`noverlap=nperseg//2`），并把谱落盘 `features/vel_fb_psd.npy` |
| `global` | 跟随误差波动 | `_ac_rms`（去均值波动 RMS，A-114 口径）+ `fe_mean_counts`（常偏另记，不混进 RMS） |
| `sensor_disagreement.pairs` | 原理间互证 | 镜像 C1 配对；规则 16：幅值只在有 `datum_offset` 时填 |
| `feedback_integrity` | 第二反馈、镜像伪装、列间恒等式 | `second_feedback_available`（仅当 identity performed 才计数否则 null）、`masquerade_suspected`（逐点相同 ⟹ 疑似） |
| `event_context` | 事件计数与同步残差 | `causal_claims_permitted = verified ∧ residual ≤ τ`——当前 residual 恒 null，故**恒 false**（诚实真空，不是 bug） |
| `segment_coverage` | 段种覆盖 | 按 `meta.segments[].kind` 计数 |

**频带门机制**：`f_b = fs/2/NYQUIST_SAFETY`（`NYQUIST_SAFETY=1.25`）；`BAND_FLOOR` 12 条规则下限 + `BRANCH_FLOOR`（`R-11#switching_freq` = 2000）中高于 `f_b` 者进 `freq_limits.blocked_rules`，且每个被阻 id/branch **逐条产 `unavailable` 行**（形状 `{feature, reason, rule?, branch?}`，feature 必须点分全路径）。`check_null_accounting` 强制「每个 null 路径至少一行账目」（豁免三条：`identity_check.reason`、`*.note`、`pairs[].dominant_order_per_rev`）；`check_self_consistency` 收尾（值与账目互斥、fs 三处自洽、bandwidth confidence ≤ 0.6 等）。

## 2. `src/axiscope/confidence.py` — KB4 §2.1/§2.2 权威实现

纪律原文：「内部一律全精度，只在 `display()`（序列化层）取 2 位小数（C3 硬性规则 15）」；`display(x)` 的 docstring：「唯一的 2 位小数出口（序列化/展示层）；计算链上不得取整。」

| 函数 | 公式口径（全精度） |
|---|---|
| `evidence_strength(ev, ctx) -> float` | `S(e) = g(ρ) × conf(f) × n_factor(n/n_ref) × band_factor(f0)`；`saturation_g = 0.5 + 0.5·min(1, log10(ρ)/log10(4))`（`RHO_SATURATION=4.0`）；categorical（==/!=）命中取 `G_CATEGORICAL=0.85`；样本因子 `min(1, 0.6 + 0.4·log10(n/n_ref)/log10(4))`；`bandwidth.*` 特征 conf 封顶 0.6 |
| `aggregate(h, ctx) -> Score` | k<2 抛 `InsufficientEvidence`；`a_sup = 0.55·s_max + 0.45·s_rest`；`a_con = min(0.5, Σ v_j)`；`c = min(a_sup·(1−a_con), 各封顶) × 乘性因子` |
| `check_refutation(rf) -> float` | 由 (value, op, threshold) **重算** ρ′ 取罚档：ρ′≥2 ⟹ 0.20、1≤ρ′<2 ⟹ 0.10、ρ′<1 ⟹ 0.05、null ⟹ 0.00（INV-4）；自报 penalty 与档位不符抛 `RefutationPenaltyViolation` |
| `distinct_blocked_by` / `absent_deduction_factor` | 缺席扣减 `1 − min(0.20, 0.05 × min(4, 去重独立缺席原因数))` |
| `overall_confidence(primary, ne_rows)` | 首名胜者 C × 缺席扣减因子 |
| `rank_band_c(rows)` | **±0.01 并列带**（`RANK_TIE_BAND=0.01`、`_BAND_EPS=1e-9`），队长锚定：同 severity 内按 C 降序扫，队长吸收 `C ≥ 队长C − 0.01 − eps` 的连续后续行；输入必须是产物里的两位显示值（引擎与校验器同刻度） |

剪枝语义（INV-1/INV-2，不是 S=0）：带外特征抛 `BandBlocked`、ρ<1 抛 `RuleNotFired`、`n < n_ref` 抛 `SampleBelowReference`。

## 3. `src/axiscope/rule_table.json` — KB3 判据的结构化抽取

顶层 **13 键**：`schema, source_of_truth, scope, numbering_convention, band_floor_source, evidence_policy, n_source_recipes, open_gaps, ops, threshold_ref_form, scale_discipline, null_discipline, rules`。

`rules` 下 **9 个条目**：R-03、R-04、R-10、R-15、R-19、R-25、R-26、R-28、R-30。可求值 leaf 的 `conditions` 子判据合计 **33**（R-03/R-04/R-15/R-19 各 7、R-10 5），另有 refuters 3、veto 2、R-26 仲裁链 6 支、R-28 胜者条件 4、meta triggers 5。

**必须澄清的口径**：「9 个规则族」的说法不准确——9 是条目数；leaf 的 `family`（fault_mode）在本文件只出现 3 个值：`mechanical_resonance`（R-03/04）、`electrical_feedforward_mismatch`（R-15）、`software_induced_interp_buffer_underrun`（R-19），其余 5 条 family 为 null（1 gate、2 arbiter、2 meta）。22 个叶的完整 fault_mode 清单在 `registration.LEAVES`，不在本文件。

leaf 条目字段集：`title, kind, family, leaf, severity(+severity_default/severity_when), severity_provenance, src_line, gate[], conditions[], refuters[], veto[], branches[], signed_asymmetry, segment_prereqs, quality_prereqs, min_fs_hz, arbitrated_by, falsified_by, sync_prereqs, combining, _note`。`src_line` 指向 KB3 的 `### R-nn` 标题行，由 `data/repin_src_lines.py` 重钉、`tests/test_registration.py` 核落点。

## 4. `src/axiscope/registration.py` — 登记层（门与账目）

`Ledger` 公开方法：`assume(anchor, statement)`、`register(row)`、`fire(rule_id)`、`skip(rule_id, reason)`、`consider(slug, note=None)`、property `distinct_blocked_by`；状态容器 `not_evaluable / considered / rules_fired / rules_skipped / assumptions / notes`。

- **准入闭集**：`_BLOCKED_BY = set(c3validate.ALLOWED_BLOCKED_BY)`（单源在校验器，共 27 键 = 14 个 `absent_<c>_channel`（由 `assertions.C1_VOCAB` 派生）+ 13 个其他）。不在集内且不以 `band_gate_fs_` 开头 ⟹ 抛 `BlockedByKey`（A-122：闭集曾两处各抄一份，现改单源）。
- **行形状**：`not_evaluable` 行 = `{fault_mode, blocked_by, why}`（叶级）或 `{family, blocked_by, why}`（族级，键二选一）；band_gate 被阻产三处联动：`blocked_rules` 收集 + `not_evaluable`（`blocked_by = "band_gate_fs_<k>Hz"`）+ `rules_skipped`。
- 族级门函数：`software_family`（R-30 三分支 E1/E2/E3、τ_u 缺省兜底 5.0 并 `tau_u_assumed` 留痕）、`thermal_family`、`near_nyquist`（剪枝走 skip+consider，不落 not_evaluable）、`event_gates`（G1–G5）。

## 5. `src/axiscope/engine.py` — 编排与排序

`analyze(features, meta=None, source_tier=…, case_id=…)` 执行序列（按代码顺序）：

1. 建 `Ledger` 与 `FrequencyContext`（fs、f_b、nyquist 取自特征包）。
2. 样本计数侧车存在则逐键 `assume`（锚 `SIDECAR_ANCHOR`）。
3. 族级门先跑（software_family → thermal_family）。
4. 逐叶循环 `reg.LEAVES`：band_gate/counts_gate 行分流 → `evaluate_leaf`（内部再过门、`build_evidence`/`build_refuters`/ceilings → `confidence.aggregate`）→ fired 入表，否则 consider。
5. n_source 配方缺口（R-04/R-15）补 `NSOURCE_GAP` assumption 行。
6. near_nyquist 行落 consider/skip。
7. **R-28 仲裁** `arbitrate_r28`：四路 s_* 择优，需 best≥0.5、margin≥0.2、residual≤τ_u、causal 四条件全真；无胜者 ⟹ fired 中的 software_induced_* 叶弹出转 considered。
8. **R-26** `arbitrate_r26` 只产说明行（notes），当前最小实现**不改 rank**。
9. `_rank`：排序键实际表达式 `key = (sev, -leaders[i], -_coverage(features, res), leaf)`——severity 升序、并列带队长 C 降序（`rank_band_c`，输入是 `display(score.c)` 两位值）、coverage 降序（**注意：`_coverage` 不区分假设，是恒等键**，A-115 在册）、fault_mode 字典序兜底。
10. 逐名次建 hypothesis（`id = H1/H2/…`、`confidence = display(c)`、severity_provenance 留痕、证据/反证行、`recommendation`、C<0.6 附 `next_data_to_collect`）。
11. `primary = hypotheses[0].id 或 None`；`overall = display(overall_confidence(...))`。
12. 组报告（`schema = "axiscope.diagnosis/1"`），`blocked_ids` 非空时回写 `freq_limits.blocked_rules`。
13. **最后一步**才算 `core_hash.core_hash(report)`——哈希核含 `freq_limits`，早算会把该项算成缺键（代码注释原句）。

## 6. `src/axiscope/core_hash.py` — C3 规则 21 的哈希核

清单常量（代码原文）：`VERDICT_KEYS = ("primary", "overall_confidence", "actionable")`；`HYPOTHESIS_KEYS = ("id", "fault_mode", "rank", "confidence", "severity", "next_data_to_collect")` + 两侧证据数组全部 13 个结构化键逐字进核；`DIFF_ROW_KEYS`、`RULE_SKIPPED_KEYS`；树顶还含 `schema, case_id, inputs, differential.considered, validation, safety, freq_limits, audit.rules_fired, audit.assumptions[].anchor`。`blocked_by` 明确**不在核内**（注释给出理由）。

四步规范化（模块 docstring）：按清单裁树（缺席键补 `null` 不省键）→ `json.dumps(tree, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)` → UTF-8 → SHA-256 → 写成 `sha256:<64 位小写 hex>`。数组顺序保留（rank 序正是被锁定对象）。辅助形态常量：`EMPTY_HASH = ""`、`PLACEHOLDER_HASH = "…"`，配 `is_computed`/`is_placeholder`。
