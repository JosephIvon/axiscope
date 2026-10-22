# examples/ — 引擎验收向量的输入夹具

这里的三份手抄 JSON + 一份孪生快照**不是引擎产物**，是 C2 形状夹具，用来喂 C3 规则引擎做端到端验收。
每份都标明"哪些数字是文档原文、哪些只为让门通过"，因为本项目的红线是
**禁止编造实测数值**——夹具里出现的每个数必须能指回一行文档，或明确声明为非证据性脚手架。

四份夹具对应 KB4/C3 的四个验收向量：

| 夹具 | 来源 | 期望的引擎输出 |
|---|---|---|
| `c2_example_a.json` | 逐字转录 `docs/contracts/C2-features.md` 例 A（第 8–158 行），`event_context.available = true` | **KB4 算例 A**：`mechanical_resonance` `C=0.65`，但按 KB4 §2.9 锚点，S2 的软件族 `software_induced_interp_buffer_underrun` `C=0.44` 抢 primary ⟹ `overall=0.42` |
| `c2_example_a_no_events.json` | 上一份的**无事件孪生**（A-99 ①）：除 `event_context` 与 `ref.note` 外逐字段相同，孪生同构由 `tests/test_snapshot_premises.py` 钉住 | 软件族 9 条规则全部 `dependency_null:event_context` ⟹ 只剩谐振：`mechanical_resonance` primary、`C=0.65`、`overall=0.59`（= **C3 契约示例 E1** 的判决，见 `tests/fixtures/c3_example_resonance_059.json`） |
| `kb4_case_b_features.json` | **KB4 §2.3 算例 B**（第 411–449 行）+ KB3 `### R-19 插补缓冲区欠载` 的判据示例值（`src_line` 以 `rule_table.json` 为准，别抄行号） | `software_induced_interp_buffer_underrun` `C=0.44`、`rules_skipped ∋ R-18 (time_resolution)` |
| `c2_example_b.json` | 逐字转录 `docs/contracts/C2-features.md` 例 B（第 171–217 行） | 谐振族被 `blocked_rules` 剪枝 ⟹ "诚实真空"形状（C3 规则 12） |

**为什么需要孪生**：C3 契约示例曾宣称"0.59 是没有 events.jsonl 的场景"，而它引用的例 A 快照里
`event_context.available = true`（A-99 起因）。前提现在有了文件载体，并且被 C3 校验器规则 18
逐字段比对（`present_channels` 与事件可用性），翻转前提会让示例翻红。
`c2_example_a.json` 因此**不再**是 C3 示例的输入。

**但本目录不是 C3 示例的全部输入**：C3 的第二份示例 E2
（`tests/fixtures/c3_example_ranked_pair.json`，A-107 ③）声明的是**同一个**快照前提
（`inputs` 与 E1 逐字段相同，由 `tests/test_snapshot_premises.py::test_both_examples_declare_the_same_premise`
钉住），只是另加一条前馈假设来演示 KB4 §2.9 的排序——它是手写的契约示例，**不是**本目录任何一份
夹具的引擎输出。引擎在母本上的真实输出（软件族抢头条、`overall=0.42`）由表里第一行单独钉。

另有一个不在本目录的真实向量：`build/Export10_244531/features.json`（引擎自己算出来的 C2），
它应当同样落到"零假设 + 逐条 `not_evaluable`"，且是 T1-a 数据（见 KB7、INV-15）。

## 脚手架字段的声明

`kb4_case_b_features.json` 里，KB4 与 KB3 **没有**给值、但门/仲裁必须读到的字段如下，
它们的取值只保证"不改变算例 B 的结论"，不构成任何证据：

- `event_context.n_by_source.*` 除 `interp: 12`（R-19 必要上下文要求 `source=interp`）、
  `host: 2`（由 `fe_spike_aligned_to_host_pause = 2` 反推）外全部为 0；
- `fe_spike_aligned_to_network_miss = 0`、`fe_spike_aligned_to_vision_result = 0`
  ——R-28 的族内择优取 `max(s_host, s_intp, s_net, s_vision)`，缺事件源时该臂是
  **计算出的 0**（`0/fe_spike_count`）而不是 `null`；写成 `null` 会让 INV-4 把整条仲裁边判为不可通行，
  与算例 B 仍能得出 `C=0.44` 矛盾。**这是 KB4 §1.5/R-28 的规范缺口**，见下；
- `network_cycle_miss_count = 0`、`n_alarm = 0`：R-20 要求 `≥ 1`，置 0 使它自然不触发；
- `position_quantum_mm = 0.02`、`quality_ref.*`、`global.fe_rms_counts`/`fe_p999_counts` 之外的
  `global.*` 一律 `null` 并进 `unavailable`。

`global.fe_rms_counts = 412.6`、`fe_p999_counts = 1380.0`、`ff_mismatch.asymmetry_ratio = 2.26`
是 KB4 算例 B 的**反证行**原文（第 440–441 行）；
`tracking.path_segments[0]` 的四个值是 R-19 判据示例原文（`3100/1520 = 2.04`、`corr 0.91`、`jerk 0.32`）。

## 夹具暴露出来的两处契约缺口

1. **`blocked_rules` ↔ `unavailable` 双向对账在例 B 上不成立**（A-79）。
   C2 规则 2 要求"每个条目必须在 `unavailable[]` 里有一条 `rule`/`branch` 与之对应的行，反之亦然"，
   但例 B 的 `R-03`/`R-04` 只有 `{"feature": "resonance.candidates", "reason": "整条判据带被…阻塞"}`
   一行且**不带 `rule` 键** ⟹ 两个 blocked 条目没有对应行。
   `tests/test_contract_examples.py::test_b_unavailable_branch_rows_match_blocked_rules`
   当前把这一事实钉成断言，示例补上 `rule` 键后该测试会转为失败提醒。
2. **算例 B 的 R-28 择优隐含"缺事件源 ⟹ 该臂为 0"，但 KB4 没写**。
   按 INV-4 的字面读法（"边判据任一依赖为 null ⟹ 该边不可通行"），
   一份没有 `network` 事件的样本会让整条 R-28 仲裁不可通行，
   于是 R-19 的叶也拿不到，与 KB4 自己算出的 `C = 0.44` 冲突。
   本目录按"计算出的 0"实现，并在引擎里把"缺该源的事件计数"与"null"区分开。

另：C3 契约文档示例里的**前馈假设**（A-107 ③ 之后在 E2 排 rank 1、id `H1`；旧示例把它写成 `H2`）
曾写 `strength: 0.41 / 0.36`，按 KB4 §2.1 复算不出来
（0.36 反解要 `n_factor = 0.583` < 文档下限 0.6，是手写数的指纹）。A-101 ① 之后示例自带
§2.1 五字段并改用复算值（0.518 / 0.494），零 gap 复算由
`tests/test_c3validate.py::test_c3_contract_example_is_fully_recomputable` 钉住。
