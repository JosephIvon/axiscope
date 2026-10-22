# axiscope Code Wiki · 01 总览与架构

> 本页是全仓 Code Wiki 的入口。Wiki 只描述盘上真实存在的内容（KB0 A-67 禁编造纪律同样适用于本目录）；
> 所有标识符均为代码原文，引用一律给「文件 + 符号名」而不给行号（行号会随增行漂移，KB0 A-117 口径）。

## 1. 这个项目是什么

**axiscope 是一个离线的伺服/过程波形接入、确定性特征抽取、规则归因与契约自检引擎。**

- 输入：厂商运动控制器/示波器的导出文件（首个支持方言是 TwinCAT 3 Scope View 的 CSV）。
- 输出：样本包（`meta.json` + `waveform.tsv`）→ 特征包（`features.json`）→ 诊断报告（`diagnosis.json`）→ 人读的 `report.html`。
- 安全边界（代码级承诺，非口头）：`safety.writes_to_device` 恒为 `false`、`requires_human_approval` 恒为 `true`（C3 契约硬性规则 6，校验器 `C3-R06-writes`/`C3-R06-approval` 强制）；数值链上没有模型调用——离线纪律由 `tests/test_offline_discipline.py` 门禁扫描 `src/axiscope` 与 `synth` 全部模块（禁网络栈、LLM SDK、训练框架 import 与 `eval`/`__import__` 类动态逃逸）。
- 置信度纪律：`confidence.py` 内部全精度，`display()` 是唯一的 2 位小数出口（序列化/展示层）；诊断报告里每条 `confidence` 都必须能被校验器从**原始证据字段**独立复算（C3 规则 3/15），不接受报告自报值。

## 2. 端到端数据流

```
厂商 CSV / TAB / TXT（data/raw、data/incoming）
        │
        ▼  twincat.read_scope（D1 Scope View）或 dialects.read_table（其余方言）
   ScopeTable（结构化表：列、单位、时基、原始行数）
        │
        ▼  c1.build_meta + mapping（列→C1 通道词表）+ c1.write_pack
   样本包  meta.json + waveform.tsv          ←—— 契约 C1（唯一内部波形格式）
        │
        ▼  features.compute（频带门禁 + 特征族 + null 账目）
   features.json + features/*.npy           ←—— 契约 C2（确定性特征，规则引擎只读它）
        │
        ▼  registration.Ledger → rule_table.json 判据 → confidence 打分 → engine.analyze
   diagnosis.json                            ←—— 契约 C3（诊断产物 schema，21 条硬性规则）
        │
        ├─▶ c3validate.validate(diag)        契约自检（结构/数值/措辞复算）
        ├─▶ assertions.run(...)              端到端断言（挂仓内可重跑产物）
        ▼
   report.html + 进程退出码（0 全过 / 1 有 FAIL / 2 拒收）
```

`__main__.run` 就是这条链的编排者；非 Scope View 方言没有触发门控槽位时在 C2 之后**有意止步**（拒收、退出码 2），不给断言层与报告层造一个恒真前提。

## 3. 目录地图

| 目录 | 内容 | 详页 |
|---|---|---|
| `src/axiscope/` | 全部生产代码（15 个 py，接入→特征→归因→校验→报告） | 02/03/04 |
| `synth/` | KB5 仿真被控对象落码（双惯量 + S 曲线规划，进行中） | 05 |
| `tests/` | 18 个测试文件、346 个 test 函数（parametrize 展开后 403 项） | 05 |
| `bench/` | C5 基准集构建与评测（7 案例、指标、违禁措辞正则） | 05 |
| `data/` | 数据侧车 + 全部 `probe_*.py` 门禁探针 + 校验器 | 05/06 |
| `docs/contracts/` | C1–C7 七份数据/产物契约 | 06 |
| `docs/kb/` | KB0–KB8 知识库（KB1 为保留空号）与 A-NN 裁决台账 | 06 |
| `examples/` | 4 份 C2 特征快照（契约内联示例的仓内副本） | 06 |
| `build/` | 运行产物（git 忽略） | 07 |

## 4. 分层与依赖方向（谁允许 import 谁）

```
        twincat ── dialects ── mapping ── c1 ──── features
          （接入层：只认文件形态与列语义，不知道「故障」为何物）
                     anchors（叶子：稳定锚形状，防成环共用）
                          │
   rule_table.json ── registration ── engine ── core_hash
          （归因层：判据求值、门与账目、置信度、排序与哈希）
        confidence ──┘        c3validate ──┘
   assertions ── report ── __main__
          （校验与呈现层：复算报告、渲染 HTML、编排 CLI）
```

要点（均从 import 语句实测）：

- **单向依赖**：接入层不 import 归因层；`features` 不 import `engine`；`c3validate` 读 `core_hash`/`confidence`/`anchors` 做独立复算，`engine` 也读同一批实现——「落码侧与复算侧不得各自发明」靠 import 同源保证。
- **防环手法**：`twincat.read_scope` 对 `dialects` 用函数内延迟 import；`anchors` 是无人依赖它的叶子模块。
- **第三方依赖只有两个**：`numpy`（c1 恒等式核对、features 数值）与 `scipy.signal.welch`（PSD）。`synth` 另用 `scipy.linalg.expm`。校验/报告/归因层全部是标准库。matplotlib、pandas 在代码中 **0 处 import**。
- **没有** `requirements.txt` / `pyproject.toml` / `setup.py`；唯一依赖口径写在 KB0（Python ≥ 3.11，numpy + scipy.signal 为唯一数值依赖）。

## 5. 三档退出码（进程级合同）

| 退出码 | 条件 | 出处 |
|---|---|---|
| 0 | 端到端断言与 C3 契约检查全部通过 | `__main__.run` 末行 |
| 1 | 存在 FAIL 断言或未通过的契约检查（产物仍写出，stderr 逐条列） | 同上 |
| 2 | 拒收：`c1.PackError` / `features.FeatureError` / `twincat.ScopeFormatError`（打「拒收：{原因}」），或非 Scope View 方言无 `trigger_gate` 时链路止步 | `__main__.main` 捕获 + `run` 内分支 |

## 6. Wiki 页面索引

| 页 | 主题 |
|---|---|
| `02-integration-layer.md` | twincat / dialects / mapping / c1：读表、方言分派、通道映射、样本包装配 |
| `03-analysis-core.md` | features / confidence / rule_table / registration / engine / core_hash |
| `04-validation-report-cli.md` | assertions / anchors / c3validate / report / __main__ |
| `05-toolchain.md` | synth 仿真、bench 基准、tests 清单、data 探针与工具 |
| `06-docs-system.md` | 契约 C1–C7、知识库 KB0–KB8、裁决台账机制、数据出处与 git |
| `07-run-guide.md` | 环境、命令、产物、数据获取、已知文档漂移 |
