# axiscope Code Wiki · 04 校验 / 报告 / CLI 层

覆盖 `c3validate.py`、`assertions.py`、`anchors.py`、`report.py`、`__main__.py`。

## 1. `src/axiscope/c3validate.py` — C3 契约机器可判定校验器

docstring 纪律原文：「`validate` 只做结构 / 数值 / 措辞判定，不调 LLM、不联网」；唯一例外是规则 17/18——它们把契约声明的**仓内产物**（外置台账、`examples/` 特征快照）解析出来核对。

- 类型：`Check = NamedTuple(check_id, passed, detail)`；`validate(diag) -> list[Check]`；`assert_ok()` 把失败抛成 `ValidationError`；`C3-R14-REFUSE` 单独抛 `RefuseReportError`。
- **检查集按报告内容展开**（逐证据 `[i]`、逐反证 `[j]`、逐 not_evaluable `[i]`，且部分为条件检查），所以条数不是常量——CLI 输出的「C3 契约 N/N 通过」就是当次实跑数（Export10 实跑为 71 条口径，见 07 运行指南）。
- 复算纪律：confidence 相关检查（规则 3/15）一律走 `confidence.py` 的**权威实现**从报告原始证据字段独立复算，不把报告自报 `strength` 当既成事实——「那样只能复述报告的自洽、抓不出报告本身的缺陷」（docstring 原句）。字段不足时记 gap，不冒充通过。
- 按契约规则分组（节选）：R01 字段 / R02 词表 / R03+R15 复算族 / R04 仿真-实测分层 / R05 低置信披露 / R06 安全两键 / R09 空报告与措辞 / R10–R11 差分与不可评估行 / R16 blocked_by 闭集与 overall / **R17–R18 仓内产物对账** / R19 assumption 形状 / R20 rank 三连（contiguous / monotonic / primary-is-rank1）/ **R21 core-hash 三连** / INV-1…16 不变式 / CAP 能力封顶。

`deterministic_core_hash` 三形态判定（规则 21）：

| 字段值 | `-format` | `-recompute` | `-empty-is-gap` |
|---|---|---|---|
| 占位符 `"…"` | **红**（待清零） | pass（不参与） | pass（不参与） |
| 空串 `""` | pass | pass（无从比对） | pass 但 detail 记 gap（不阻塞） |
| `sha256:<hex>` | pass | 仅当 `declared == core_hash(diagnosis)` 才 pass | pass |
| 其他非法形态 | 三条全红 | | |

并列带（R20-monotonic）与引擎共用 `confidence.rank_band_c`：两侧都读**产物里的两位显示值**，±0.01 队长锚定——只改一侧会把另一侧既有示例判红（A-121 纪律）。

## 2. `src/axiscope/assertions.py` — KB2 §8.3 端到端断言

- `run(meta, feats, ingest, pack_dir, raw_columns)`：**24 条不同名断言**（25 个调用点，`fe ≡ pos_cmd − pos_fb` 按有无 fe 二分支其一）。
- `C1_VOCAB` 恰 14 个通道名——它同时是 `registration`/`c3validate` 的 `absent_<c>_channel` 闭集派生源（单源，A-122）。
- 「断言须挂仓内可重跑产物」（KB0 §6 检查 27）的落法：断言不只看内存对象，而是**独立复读磁盘产物**——重读 `waveform.tsv`（列名/时基单调/逐点回算）、把 `meta.json` + waveform 拼 blob 做脱敏与 DOI 扫描、`provenance.trigger_gate.rows_kept` 对账 `quality.n_samples`、`ingest.series` 逐点回算差恒 0、末条调 `features.check_self_consistency`。
- 每条断言在 `tests/test_slice.py` 有对应负向注入例（检查 22：检测力须有病例）。

## 3. `src/axiscope/anchors.py` — 稳定锚（叶子模块）

`ANCHOR_FORMS` 六种合法锚（meta 字段 / 通道 / C2 特征点分路径 / 规则判据 / KB 叶名 / 文档锚）；`anchor_kind()` 判型；`assumption_row(anchor, statement)` 构造 `audit.assumptions` 行；形状不合法抛 `AnchorNotStable`。被 `c1` 与 `engine` 共用且自己无依赖——防 import 环。

## 4. `src/axiscope/report.py` — HTML 报告

公开函数：`render(...)`、`diagnosis_section(diag)`、`write_report(path, html)`、`write_features(path, feats)`。段次固定：一、这份数据是什么（来源卡）；二、频带门禁 blocked_rules；三、通道能力矩阵；四、实测 findings（互证对 / sign_check / masquerade / identity，条件出现）；五、C2 特征与分段；六、unavailable 结构化事实；七、端到端断言表；八（有诊断时）、C3 归因（verdict 卡、假设排序表、逐假设证据/反证/建议/补数据、差分诊断、审计留痕、contract_checks、安全条）；末节「必须随报告一起读的限定」。**无绘图依赖**——手写 html/io，不生成 SVG/图片。

## 5. `src/axiscope/__main__.py` — CLI 编排

调用序列：`read_scope → c1.build_meta → c1.write_pack →（回填 sha256/sample_id）→ features.compute → write_features →` **拒收检查** `→ engine.analyze → c3validate.validate（结果附入 diagnosis.json）→ assertions.run → report.write_report → 打印摘要`。

- **拒收分支 A**：`meta.provenance.trigger_gate is None`（非 Scope View 方言没有触发门控槽位）——样本包与特征已落盘，但断言层/报告层只覆盖 D1 门控样本，不造恒真前提，打「拒收」到 stderr，`return 2`。
- **拒收分支 B**：`main()` 捕获 `(c1.PackError, features.FeatureError, twincat.ScopeFormatError)` 打「拒收：{exc}」`return 2`（`ScopeFormatError` 是 A-130 补进元组的——此前 D4 无时间列拒收走的是未捕获崩溃 + 退出码 1，还会把内部表头列名泄进 stderr）。
- 参数：`--in <厂商CSV> --out <样本包目录> [--sample-id]`；stdout/stderr 先 `reconfigure(encoding="utf-8")`（Windows 中文输出）。
- 退出码：0 全过 / 1 有 FAIL（stderr 逐条，产物仍写出）/ 2 拒收。

## 6. 两层自检的分工（读代码时别混）

| 层 | 对象 | 判定源 | 失败语义 |
|---|---|---|---|
| `assertions.run` | **接入与特征产物**（样本包、特征包） | KB2 §8.3 断言集 + 磁盘复读 | 计入退出码 1 的 FAIL |
| `c3validate.validate` | **诊断报告**（diagnosis.json） | C3 契约 21 条硬性规则 + KB4 不变式 | 计入退出码 1 的 C3 FAIL；`C3-R14` 可升级为拒收异常 |
