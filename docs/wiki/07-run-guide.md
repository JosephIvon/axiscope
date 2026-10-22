# axiscope Code Wiki · 07 运行指南

## 1. 环境

- **Python ≥ 3.11**（KB0 口径；本仓实测跑在 3.14）。
- 第三方依赖只有 **numpy + scipy**（`scipy.signal.welch`；synth 另用 `scipy.linalg.expm`）；开发期加 **pytest**。**没有** `requirements.txt`/`pyproject.toml`——安装即 `pip install numpy scipy pytest`。
- 代码是包布局（`src/axiscope`），无安装步骤：所有命令带 `PYTHONPATH=src`。
- Windows 终端建议 `PYTHONIOENCODING=utf-8`（CLI 自身已把 stdout/stderr reconfigure 成 UTF-8，但探针输出不保证）。

## 2. 主链路（一条命令端到端）

```bash
cd /d/workspace/axiscope
PYTHONPATH=src PYTHONIOENCODING=utf-8 \
  python -m axiscope --in data/raw/Export10_244531.csv --out build/Export10_244531
```

参数：`--in` 厂商导出文件、`--out` 样本包目录、`--sample-id`（缺省取文件名）。当前唯一全链路样本是 **Export10_244531.csv**（D1 Scope View，TwinCAT，DaRUS-3600）；其余方言只走「样本包 + 特征」两节后按设计拒收。

预期成功输出（实测）末两行：

```
  归因：主假设 None · overall_confidence None · 命中 ['R-30'] · 跳过 14 条
  断言 24/24 通过 · C3 契约 71/71 通过
```

主假设 None 不是 bug：Export10 的可用证据不足以过 §2.1 门，诚实真空输出（`causal_claims_permitted` 恒 false 同）。

## 3. 退出码合同

| 码 | 含义 | 例子 |
|---|---|---|
| 0 | 断言 + 契约检查全过 | 上面 Export10 |
| 1 | 有 FAIL（stderr 逐条列 `FAIL`/`C3 FAIL`，产物仍写出） | 人为改坏 diagnosis 字段后跑校验 |
| 2 | 拒收（stderr 首词「拒收」） | `--in data/incoming/6114_ObserverTestSet.tab`（D4 无时间列）；非 D1 方言止步 |

## 4. 测试与门禁

```bash
PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m pytest tests -q        # 全量（346 个 test 函数，展开后 403 项）
PYTHONPATH=src python -m pytest tests/test_offline_discipline.py -q    # 离线纪律门禁
python data/probe_md_tables.py                                        # 表形探针（病例则退出码 1）
python data/probe_doc_line_refs.py                                    # 行号指针探针；--selftest 自证
python data/probe_doc_line_refs.py --multiline --quote-backtick       # 放宽口径复跑
```

**改任何文档后必跑**：全量套件（内含两探针的接入用例）。数字请按「当时的打印值」口径引用。

## 5. 基准评测（C5）

```bash
PYTHONPATH=src python bench/build_cases.py                 # 从母本重建 7 案例（含构建期硬门禁）
PYTHONPATH=src PYTHONIOENCODING=utf-8 python bench/run_eval.py > build/c5-eval/run.log 2>&1
```

产物 `build/c5-eval/`（`metrics.json`、`per_case.json`、`diagnoses/` 7 份）。当前指标基线：dev 4 + T1-a 7 例，`top1_hit = 0`、`ece = null`、严格拒答 7/7——**样本量远低于 KB8 下限 120，任何准确率声明都无分母**。

## 6. 其他常用工具

| 命令 | 用途 |
|---|---|
| `python data/validate_raw.py --selftest` / `python data/validate_raw.py <文件或目录>` | 批量校验与侧车比对 |
| `PYTHONPATH=src python data/probe_dialects.py` | 各方言支持度实跑表 |
| `python data/make_sidecars.py --dry` | 侧车缺口预览（去掉 `--dry` 才写） |
| `python data/repin_src_lines.py` | KB3 增删行后重钉 `rule_table.json` 的 src_line（会写文件） |
| `python data/cite.py` | DaRUS API 留档元数据打印（署名核对用） |

## 7. 输出产物（一次成功运行的全部文件）

```
build/Export10_244531/
  meta.json            C1 样本包元数据（24 顶层键）
  waveform.tsv         门控后波形（UTF-8 / LF / TAB）
  features.json        C2 特征包（22 顶层键）
  features/vel_fb_psd.npy   PSD 数组旁路
  diagnosis.json       C3 报告（含 contract_checks 与 deterministic_core_hash）
  report.html          人读报告（一~九节）
```

## 8. 数据获取（数据集不在 git 里）

`data/raw`（13 实体文件）、`data/incoming`（32 数据件）、`data/staging` 经 `.gitignore` 排除，重下途径与许可逐项登记在 **KB7 台账**（DaRUS 各 DOI + ScienceDB），署名义务在 README §1–§4。每个数据文件应带 `.source.txt` 侧车；缺失时用 `make_sidecars.py` 按 API 留档补齐。

## 9. 已知文档漂移（如实在册）

- KB0 某节写的入口形态是 `python -m axiscope <sample_dir>`，与实际 argparse（`--in/--out/--sample-id`）不一致——以代码为准，本页 §2 是可跑的。
- 「9 个规则族」旧说法与 `rule_table.json` 实况（9 条目、3 个 leaf family）不符，正确口径见 03 §3。
- ~~D1–D6 方言编号与 `dialects.py` 四个 `DIALECT_*` 字符串没有显式对应表~~——**已闭合（A-133）**：实测对应表落在 02 §2，每格来自 probe 现跑与测试断言原文；保留的口径提醒是——D 编号只是记法，产品载体始终是 `dialect` 字段字符串。
