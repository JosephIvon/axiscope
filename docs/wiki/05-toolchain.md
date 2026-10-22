# axiscope Code Wiki · 05 工具链：synth / bench / tests / data

## 1. `synth/` — KB5 仿真被控对象（进行中，任务 #46）

- `integrator.py`：**双惯量弹性系统，4 状态 [θm, ωm, θl, ωl]**（电机侧坐标），线性部分**精确 ZOH**（增广矩阵指数法，`scipy.linalg.expm`，A 奇异也能处理）；三环串级：位置 PID → 速度 PI → 电流一阶滞后（P-A 无 `f_i` 不建模、记缺口）；PWM 延迟 1.5·T_pos 非整数拍不进极点、只进 Padé(2,2) + 精确 e^{−sT} 频域校核。稳定性判据（KB5 §1.5）：离散极点 |z| ≤ 0.995（剔内部积分极点）、相位裕度 ≥ 30°、幅值裕度 ≥ 6 dB 或无穷、自由振荡能量漂移 < 1%、能量残差 ≤ 0.5%；`EnergyAudit` 是独立正确性检查。
- `params.py`：P-A / P-B 两个 frozen `ParamSet`，值逐项指回 KB5 §2 种子；派生量 J_r/λ/c/f_m/f_a 解析式；`ASSUMED_REGISTRY` 登记 3 处 assumed 参数；`calibrate_omega_n` 按 f_m/ω_n 比值族扫参。
- `scurve.py`：七段 jerk 受限 S 曲线（情形 I / II / III-a / III-b），栅格对齐只量化 t1=t3、优先保 D、错位记 `boundary_residual_ms`；`invariants()` 12 条（I1–I12）任一失败**拒生样本**；`golden_vectors()` 6 组标准向量。
- **状态如实**：无 CLI 入口、无注入器/写出器——驱动探针在 `build/_synth_probe/`（p1…p9）；p3 输出记录 P-A 全部候选 `poles_le_0p995=False`（`InstabilityError`），即 P-A 参数组的稳定性校核**尚未通过**。产出样本的 `source_tier` 只能是 T3，不得表述为诊断准确。

## 2. `bench/` — C5 基准集（评测协议防自我验证）

- 构建：`casebuild.CASES` 共 **7 条**（dev 4 / hidden 3）→ `build_cases.py` 对每条从**唯一母本** `data/raw/Export10_244531.csv` 走生产链路落 `bench/samples/<case_id>/`（meta.json + waveform.tsv [+ events.jsonl]），产 `cases.jsonl` 与 `hidden.sha256`。期望类分布：`refuse_insufficient_data` 4、`co_occurrence_only` 2、`none_of_the_above` 1；真值只来自写死的注入数学（INJ-01/04/11/15/19），唯一非同源真值是 CTL-0001（受试对象健康对照）。
- **两条构建期硬门禁**：同波形孪生样本的 `waveform.tsv` 必须逐字节相同核验；「同整包摘要但期望标签不同」直接构建失败（任务 #52 / A-61——防「拿同一份数据既算对又算错」）。
- `hidden.sha256`：注释 3 行 + 数据 3 行，锁 hidden 样本的整包摘要 `SHA256(meta.json ‖ 0x00 ‖ waveform.tsv ‖ 0x00 ‖ events.jsonl 或空)`。
- `forbidden_patterns.json`：**6 个 token**（`kHz_absent`、`no_anomaly_claim`、`field_effective`、`thermal_drift`、`sub_quantum_mm_claim`、`simulation_validated_claim`）编成正则，挡「把不可观测写成没有」「无依据成功声明」「µm 臆造精度」类措辞；`run_eval` 只扫叙述字段。
- `run_eval.py` 指标（JSON 键名原文）：`top1_hit`/`top3_hit`（分母 `in_hit_denominator`：slug 级 gold 且 tier ∈ {T1-a, T2}）、`refusal_correct`、`refusal_correct_strict`、`ece`（10 桶置信-准确率差）、`evidence_rows_checked`/`evidence_rows_bad`、`forbidden_hits`、`unsupported_success_claims`、`expected_blocked_by_covered`、`band_gate_r03_r04_blocked`、`contract_checks_total`/`failed`、`traceable`。当前实测 `top1 = 0`、`ece = null`（分母为 0 时拒绝给数——诚实真空）。**KB8 规模下限 N=120 vs 实际 7**，文档明写「不缩表凑数」，引用评测数时必须带这个差距。

## 3. `tests/` — 测试体系（18 个 py + `fixtures/` 3 份 C3 快照）

合计 **346 个 `def test_`**（`grep -c "^def test_" tests/*.py` 实测），parametrize 展开后**当前全量 403 项**。逐文件：

| 文件 | 用例数 | 钉住什么 |
|---|---|---|
| `test_slice.py` | 48 | KB2 §8 端到端正向 + 每条 §8.3 断言的负向注入 |
| `test_c3validate.py` | 61 | 契约示例正向 + 每条硬规则注入负向 |
| `test_confidence.py` | 43 | KB4 算例 A/B 逐格复算（§2.1/§2.2 手算可追） |
| `test_contract_examples.py` | 26 | C2 契约内联示例可 parse 且派生式重算、null 账目过引擎自检 |
| `test_registration.py` | 23 | blocked_by 闭集单源、why 键名与固定措辞、src_line 引用落点 |
| `test_engine.py` | 25 | 引擎产出可过 c3validate 复算路径 |
| `test_counts_and_pairs.py` | 21 | A-97/98/106 计数后缀与全 extra 互证口径 |
| `test_validate_raw_intake.py` | 15 | 批量校验器 intake 回归（R-5 误报消除等） |
| `test_export_dialects.py` | 14 | 五方言判别特征自曝负向 |
| `test_identity_scan.py` | 13 | A-105 列间恒等式/派生列核对，独立位置列计数 |
| `test_event_context.py` | 10 | C6 事件词表越界必须触发 FeatureError |
| `test_snapshot_premises.py` | 10 | 规则 18 孪生快照前提同构 |
| `test_md_tables.py` | 3 | Markdown 表形四病例的检测力（注入即红） |
| `test_offline_discipline.py` | 8 | 离线纪律门禁（见下） |
| `test_resonance_counts.py` | 8 | A-102 resonance 承载字段在示例与真管线一致 |
| `test_severity_anchors.py` | 8 | §2.9 字典序 + R-26 同档仲裁 |
| `test_doc_line_refs.py` | 7 | 行号指针探针接入套件（严格/放宽双口径 0 病例） |
| `test_anchors.py` | 3 | 六种稳定锚正向 + 「散文不是锚」负向 |

**`test_offline_discipline.py`（A-130 的门禁）**：静态扫描 `src/axiscope` 与 `synth` 全部模块（glob 现点现算，新模块自动入闸；不足 10 文件直接红，防空转）——禁网络栈（socket/urllib/httpx/…）、LLM SDK（openai/anthropic/langchain/…）、训练框架（torch/sklearn/…）三类 import，禁 `__import__`/`importlib.import_module`/裸 `eval`/`exec`/`compile`/`os.system`/`os.popen` 动态逃逸；负向注入按检查 22 落锚（锚点缺失时 harness 响亮失败），特异性对照（合法 `import json` 与 `re.compile` 必须零命中），另含 CLI 两档退出码例（D4 拒收 2 无 Traceback、D1 正常 0）。

## 4. `data/` — 探针与工具（「可重跑产物」的家）

### 4.1 三个门禁探针（文档与账目的守卫）

- **`probe_md_tables.py`**（检查 28 载体）：扫 `docs/` 与 `README.md` 的全部 Markdown 表；核四类病例——裸竖线（单元格内 `\|` 未转义）、跨行拆行、列数与表头不符、空行截断/无表头碎表片段；退出码非 0 即有病例，末行打印自数（`scanned rows=… 合计病例=…`）。
- **`probe_doc_line_refs.py`**（检查 23/24 载体，`--selftest` 自带用例）：扫全仓 `path:NNN` 形态指针，分桶 `missing-file` / `range-out-of-bounds` / `stale`（引文不在所指行段）/ `partial-quote` / `no-quote`（无引文不判病例）/ `external-target`（引用方为 `docs/AUDIT-*.md` 且目标不在本仓——豁免但单独打印）；`--multiline --quote-backtick` 放宽口径复跑一次，两口径都必须 0 病例。
- **`probe_tally.py`**：判定行自数器（检查 26/27 口径）——以 Tee 挂 stdout，行尾「成立/不成立/无法复算」自数，退出时打汇总，防「打印数与声称数两张皮」。

### 4.2 其余脚本（一行一个）

| 脚本 | 用途 |
|---|---|
| `validate_raw.py`（1691 行） | data/raw 批量校验：时基三方交叉、通道映射、运动特征、六条硬拒红线、`.source.txt` 自述比对（SUPPORTED/CONTRADICTED/UNVERIFIABLE）；`--selftest` 负向例 |
| `repin_src_lines.py` | 按 KB3 `### R-nn` 标题行重钉 `rule_table.json` 的 `src_line` 并打印逐条位移（**会写文件**） |
| `make_sidecars.py` | 从 `build/darus_provenance.json` 搬运 DOI/标题/许可、现算 md5/行列生成缺失侧车；`--dry`；核不出写「未核」 |
| `cite.py` | 读 `data/raw/darus3600.json`/`darus5171.json` API 留档打印权威元数据 |
| `probe_dialects.py` | 各导出方言喂 `axiscope.run` 打异常首行（方言支持度实跑表） |
| `probe_pii.py` | 脱敏计数（正则命中次数，分 raw/build 两组） |
| `probe_cat.py` / `probe_diff_identity.py` / `probe_5171_identities.py` / `probe_kb7_b_group.py` | 各项调研数字的复算探针（KB7 台账、A-104 恒等式、5171 复算、B 组台账） |
| `probe_kb5_stability.py` / `probe_kb5_cascade.py` | KB5 §1.5 稳定性两版建模探针 |
| `probe_darus_provenance.py` | 在线 GET DaRUS API 打权威元数据（全仓唯一联网脚本，**不在**离线纪律扫描集内，属 provenance 工具） |
| `redact_pii_20261022.py` | 一次性脱敏脚本（KB2 令牌化，2026-10-22 执行完留档） |
| `_tmp42_blocks.py` / `_tmp42_probe.py` / `_audit_staging_mat*.py` | 任务 #42 期间的对拍/审计临时脚本 |
