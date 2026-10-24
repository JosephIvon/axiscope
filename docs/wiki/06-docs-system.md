# axiscope Code Wiki · 06 文档体系：契约 / 知识库 / 台账 / 数据出处

本仓「文档比代码重」：docs 共 27 份 md（含本 Wiki 七页），生产代码 15 个 py。文档不是注释，而是**被测试和探针引用的规范本体**——改代码前先改契约，改契约必须过台账。

## 1. `docs/contracts/` — C1–C7 数据/产物契约（行数实测）

| 契约 | 行数 | 管什么 | 编号规则条数 | 产物形状 |
|---|---|---|---|---|
| C1-canonical-waveform | 362 | 唯一内部波形格式；内核不认识厂商格式 | 16（多速率栅格 7 + 派生 9）+ 质量红线 5 | 样本包：`meta.json` + `waveform.tsv`（可带 `events.jsonl` 等） |
| C2-features | 530 | 确定性特征向量；规则引擎只能读它 | 19 | `features.json` + `features/*.npy` 旁路 |
| C3-diagnosis | 1205 | 诊断产物 schema | **21 条「不可协商规则」** | `diagnosis.json`（含 `contract_checks[]`） |
| C4-validation | 93 | 建议必须先在仿真 plant 跑一遍 | 0（全 bullet） | C3 的 `validation[]` 记录 |
| C5-evaluation-protocol | 166 | 防自我验证的评测协议 §0–§9 | 4（仅 §9 结构性真空） | `bench/cases.jsonl` → `build/c5-eval/` |
| C6-machine-context | 170 | 机器状态与事件层 | 3（§3 时间同步） | `events.jsonl`（封闭词表） |
| C7-process-context | 417 | 工艺/标定/节拍侧载体 | 64（纪律 53 + 冲突清单 11，全部已裁决） | `process.json` + `calibration.jsonl` |

**如实声明**：C7 **没有代码实现**——`src/` 里只有 3 处 token 引用（blocked 名单与 `absent_calibration_jsonl` 键），全仓无 `process.json`/`calibration.jsonl` 实体与解析代码。`docs/contracts/examples/`、`docs/research/` 为空目录。

## 2. `docs/kb/` — KB0–KB8 知识库（KB1 是保留空号，KB0 明写）

| 库 | 行数 | 主题 |
|---|---|---|
| KB0-conventions | 603 | 命名空间、跨文档唯一权威、§6 引用完整性检查、§7 裁决台账 |
| KB2-waveform-formats | 957 | 波形格式与解析器需求（入口质量闸门，含 §8.3 断言集） |
| KB3-tuning-rules | 2307 | 特征索引表 + 判据库 R-01…R-30 + 阈值合法化 |
| KB4-attribution-model | 985 | 归因树 + 置信度/证据模型（§2.1/§2.2 公式、§2.9 排序）+ 混淆对 |
| KB5-simulation-plant | 1454 | 仿真被控对象与合成数据规范 |
| KB6-coupling-and-calibration | 796 | 耦合寻光/标定工艺外壳 |
| KB7-dataset-da-rus-cat | 524 | T1 真实数据集台账（逐文件 DOI/许可/能力格/verification_level） |
| KB8-benchmark-cases | 515 | C5 评测案例目录规范（含规模下限 N=120） |

## 3. 裁决台账机制（KB0 §7）——本仓的过程资产

- 每条争议落一条 **`A-NN`** 行（4 列：事项 / 裁决+理由 / 落点与实测），编号**唯一且连续**（§6 检查 18：取最大号 +1，不跳号不复用）。当前连续至 **A-132**（本页撰写时）。
- 「新增条目只能追加，不得改写已引用的编号语义」（KB0 开头「唯一命名权威」段）；跨文件一致性**不外包**——§6 标题原文即「引用完整性检查（主线程负责，跨文件一致性不外包）」。
- **§6 检查**：编号列表 1–26 条 + 负向样例表补齐至最大号 **28**。关键几条：检查 22（自称能检测某缺陷的检查器必须附「注入该缺陷、真的触发」的负向用例）、检查 23（纪律不能「散文有、载体无」）、检查 27（实测数字必须挂仓内可重跑产物）、检查 28（Markdown 表成形）。
- 「当时的打印值」口径（A-118）：写台账/文档这一动作本身会改变被核对象计数，旧数保留原样加注「现读作当时打印值」，不回头改写。

## 4. 探针即守卫（文档改动的门禁）

`data/probe_md_tables.py` 与 `data/probe_doc_line_refs.py` 由 `tests/test_md_tables.py`、`tests/test_doc_line_refs.py` 接入套件——**任何文档改动后跑全套件即得门禁验收**。裸行号指针（`:NNN`、`KB7:10` 形态）会被判病例，引用一律用节锚（如「KB2 §六」）或「第 N 行」散文形态。

## 5. 数据出处体系（provenance）

- **侧车机制**：每个数据文件配同名 `.source.txt`（模板 `data/PROVENANCE-TEMPLATE.md`），一行一项、字段 19 项（`url / retrieved_at / retrieved_by / publisher / license / dataset_doi / original_filename / format_family / device_or_software / sampling_rate / rows / channels / variable_semantics / derived_from / upstream_id / md5 / verified_against / verified_by / notes`）。全仓实测 **117 份**。
- 四条硬规则：派生件哈希只是自证；文件名不是标识（须 `upstream_id + md5 + directoryLabel` 三件套）；URL 打不开不等于不存在；核对判据要匹配文件形态。
- `validate_raw.py` 把侧车自述数字 vs 实测，不符标 `CONTRADICTED`；`make_sidecars.py` 纪律：DOI/标题/许可只从 API 留档搬运，md5/行列一律现算，**核不出写「未核」，不编造**（A-67/A-123）。
- 许可：DaRUS 各集 CC BY 4.0 署名（README §1/§4）、ScienceDB `10.57760/sciencedb.04148` 独立署名（§2）；Zenodo `10.5281/zenodo.21526135` 为**硬拒不接入**（§3）。DOI 主登记处是 KB7（31 处），契约七份为 0 处。
- 数据集本体（`data/raw`、`data/incoming`、`data/staging`，约 596 MB）**不入 git**——均有 DOI 可重下（A-131 口径，见 `.gitignore`）。

## 6. `docs/` 其余文件与 git

- `AUDIT-minimax-mcopilot.md` / `AUDIT-minimax-round3.md` / `AUDIT-glm-code-factory.md`：对三家外部模型交付物的实跑审计与逐条裁决（其中外部绝对路径是 provenance 记录，不是本仓引用）。
- `DECISION-2026-10-19-方向裁决.md`：三方向冲突的根基裁决（「录下来的波形就是闭环反馈的完整记录」），定契约先行。
- `项目回顾与收尾_20261022.md`：账面规模、六条纪律资产、三笔诚实账、停机宣告。
- **git 历史**：仓库 2026-10-22 由 `git init` 建立（初始提交 `d5717fb`＝迁址后全仓快照，身份 `axiscope-bot`），当日后续提交含 KB2 脱敏清偿与行锚修正。**init 之前的开发过程不在 git 里**，其编年史在 KB0 台账 A-1…A-132。
