# axiscope Code Wiki · 02 接入/解析层

覆盖 `twincat.py`、`dialects.py`、`mapping.py`、`c1.py`。这一层的承诺是「只把文件读成结构化表并装进 C1 契约包」，不认识故障、不做诊断。

## 1. `src/axiscope/twincat.py` — D1（TwinCAT 3 Scope View）读表器

docstring 原文口径：「只做『读成结构化表』这一件事，语义映射在 mapping.py，契约装包在 c1.py」。

| 符号 | 形状 | 职责 |
|---|---|---|
| `read_scope(path: str) -> ScopeTable` | 公开入口 | Scope View 形态则解析 TAB 键值表头 + 数据区；非 Scope View 转交 `dialects.read_table`（函数内延迟 import 防环） |
| `class ScopeFormatError(Exception)` | 异常 | 「结构定位失败：宁可拒读，不得按猜测解析」。四个抛出点：无 `Name` 表头行、表头列数为奇数（非键值交替）、通道名重复、通道含非数值单元 |
| `@dataclass Column` | 结构 | `name, symbol, unit, col_index, meta` |
| `@dataclass ScopeTable` | 结构 | `path, encoding, newline, bom, n_header_rows, n_columns, columns, sample_time_ms, n_rows_raw, n_rows_shape_mismatch, sample_index, data, file_meta, redaction_hits`，另四个只由 dialects 填的槽：`dialect`（默认 `"twincat_scope_view"`）、`time_column`、`time_col_source`、`unit_source`；方法 `column(name) -> Column`（找不到抛 `KeyError(name)`） |
| `gate_episodes(flags) -> list[tuple[int, int]]` | 函数 | 触发门控为真的极大连续区间（NaN/0 视为假）——D1 取「最长一次门控」样本的依据 |
| `timebase_stats(index, dt_ms) -> dict` | 函数 | 键 `dt_median_s, dt_jitter_ratio, strictly_monotonic`（`dts` 非空时另有 `gap_max_s`） |

内部细节：`REDACT_PATTERNS = ("Versuchsstand", "141.58.", r"C:\\")`，命中计数进 `redaction_hits`（脱敏纪律的读数口）；`_to_float` 把空串/`nan`/`na`/`#NAN` 折成 NaN。

## 2. `src/axiscope/dialects.py` — 非 D1 方言分派器

docstring 口径：「只回答三件事：有哪些列、每列多少行、时间轴从哪来」。**时间轴是唯一硬门槛**：ISO 文本列→epoch 秒；列名带单位→`column_name:<unit>`；否则只认同名侧车 `<file>.source.txt` 的 `sampling_rate` 声称且「有且仅有一种」单位假设能复现→`sidecar_attested:<unit>`；都不成立→拒读（D4 形态）。

| 符号 | 职责 |
|---|---|
| `is_scope_view(lines)` | 入口判据：前 200 行出现 `Name<TAB>非空` 即 D1 |
| `sniff_delimiter` / `sniff_decimal_comma` | TAB>分号>逗号；逗号数 ≥20 且 > 4 倍点数判欧洲小数逗号 |
| `iso_epoch_s` | ISO-8601 文本→epoch 秒（裸时间按 UTC），不合返回 NaN |
| `sidecar_fields` / `sidecar_sampling_rate_hz` | 读侧车，键闭集 `publisher, license, dataset_doi, original_filename, url, sampling_rate` |
| `read_table(path, *, text, newline, bom) -> ScopeTable` | 归一化主函数；产 `file_meta` 键：`axiscope.dialect, delimiter, decimal_comma, time_column, time_col_source, time_unit_source, row_index_column, id_column, header_columns_total, encoding` + `sidecar.<key>` 前缀项 |

方言常量（代码里就这四个字符串）：

| 常量 | 值 | 触发形态 |
|---|---|---|
| `DIALECT_TSV_ISO` | `"tsv_iso8601"` | TAB 分隔 + ISO 时间列 |
| `DIALECT_SEMICOLON_EURO` | `"semicolon_european_decimal"` | 分号分隔 + 欧洲小数逗号 |
| `DIALECT_CSV_ISO` | `"csv_iso8601_rowindex"` | 首列空名行索引、次列 ISO 时间 |
| `DIALECT_CSV_SEGMENT` | `"csv_segment_index"` | 首列段名的其余形态 |

**D1–D6 ↔ `dialect` 字段实测对应表**（A-133 补；每格都来自现跑核对：`data/probe_dialects.py` 全量输出、`tests/test_export_dialects.py` 的逐条 `t.dialect ==` 断言、`twincat.py` 缺省值。D 编号本身只是台账 A-126 与测试的记法，**产品载体始终是 `dialect` 字段字符串**）：

| 编号 | `ScopeTable.dialect` 实际值 | 实样文件（仓内相对路径） | 读数（probe_dialects 现跑） | 时间单位来源（测试断言值） | 载体测试与它验证的断言 |
|---|---|---|---|---|---|
| D1 | `"twincat_scope_view"`（`ScopeTable` 字段缺省值） | `data/raw/Export10_244531.csv` | 32 列 · fs=1000 Hz · 5000 样本 | `None`（周期由元数据块声明，不走列名） | `test_d1_scope_view_path_is_untouched`：加分派器后 D1 行为零变化，`time_column is None` |
| D2 | `"csv_iso8601_rowindex"` | `data/incoming/6114_lsmc.csv` | 3000 行 · 49 列 · fs≈1000.07 Hz | `"iso8601_text:epoch_seconds"` | `test_d2_comma_iso8601_rowindex` + 负向例：破坏一行 ISO 时间戳 ⟹ 拒读（报文中含「ISO-8601」） |
| D3 | `"tsv_iso8601"` | `data/incoming/current-hunt/3900_const_vel_110.tab` | 2701 行 · 40 列 · fs≈1000.07 Hz | `"iso8601_text:epoch_seconds"` | `test_d3_tab_iso8601`（`dt_jitter_ratio`≈0.0384 与 KB2 §4.12 R-3 同量）+ 负向例：复制一行制造 Δt=0 ⟹ 「时基非严格单调」拒读 |
| D4 | **无 dialect 值**——`_resolve_time_column` 失败即抛 `ScopeFormatError`，发生在赋值之前，所以产物里根本不存在 D4 的方言字符串 | `data/incoming/6114_ObserverTestSet.tab` | 拒读：「该导出无时间列，无法确定采样率，按 C1 拒收」 | 不适用（未走到单位判定） | `test_d4_without_time_column_is_refused` + 负向例：把 `x_act` 改成严格递增仍拒收（R-7：启发列不配当时基）；CLI 层 D4 样本退出码 **2** |
| D5 | `"semicolon_european_decimal"` | `data/incoming/2563_LDD_Transfer_function_Force_controlled.csv` | 2047 行 · 2 列 · fs=16000 Hz | `"column_name:ms"`（`X (ms)`） | `test_d5_semicolon_european_decimal`（欧洲小数逗号解析正确）+ 两条负向例：列名去掉单位 ⟹ 拒读；`;` 换成 `,` ⟹ 形状与数值同时崩 |
| D6 | `"csv_segment_index"` | `data/raw/参数分析仪波形_PMU_1t1r_CVSV导出样例.csv` | 22260 行 · 10 列 · fs=2e8 Hz（BOM+段内续行） | `"sidecar_attested:s"`（唯一来自侧车声称的单位） | `test_d6_csv_segment_index_bom_and_nan_cells` + 两条负向例：非数值单元 ⟹ 拒读；**无侧车 ⟹ 「单位无来源」拒收**（证明「秒」不是写死的默认值） |

对应的 D 编号判据在 `c1._build_meta_generic` 的 docstring 声称覆盖 D2/D3/D5/D6（D1 走专有路径、D4 到不了 packing 层）——与本表一致。

拒读条件（`ScopeFormatError` 抛出点摘录）：文件无内容、未识别为任何已知方言、表头列名重复、表头之后无数据行、无时间列无法确定采样率、时间列非 ISO 文本/非数值/含空单元、时间列只有 1 行、时基非严格单调、时间单位无来源、通道含非数值单元、除时间与结构列外没有任何测量通道。

`time_col_source` 值域：`"column_name"` / `"iso8601_content"` / `"none"`；`unit_source` 值域：`"iso8601_text:epoch_seconds"` / `"column_name:<unit>"` / `"sidecar_attested:<unit>"`。

## 3. `src/axiscope/mapping.py` — DARUS-3600 列名 → C1 通道

静态映射表模块，无状态。docstring 口径：冲突以样本卡实测为准；**拒映的列也必须逐条登记理由**（KB2 §3.6 要求 N_mapped + N_extra == N_header）。

- `@dataclass(frozen=True) Mapped` / `Extra`：条目形状 `canonical/raw_column/unit/sign/offset/inferred/confidence/basis/note/unit_unresolved`。
- `MAPPED` 恰 3 条：`vel_cmd ← dVelocity_test_tar`、`vel_fb ← dVelocity_test`（SI `m/s`）、`torque ← dTorque_test`（`N_m`，`unit_unresolved=True`）。
- `EXTRAS` 29 条（`dPosition_*` 8 列、`dVelocity_*` 6 列、`dRate_asco`、`dForce_*` 6 列、`dTorque_load`、`dPower_*` 2 列、布尔 `b*` 4 列——布尔列不入 waveform.tsv）。
- 辅助表：`CROSS_VALIDATION_PAIRS`（3 对位置互证）、`PRINCIPLE`（`motor_encoder / optical_asco / inductive_lsv`）、`CMD_FB_TWINS`（4 对 `_tar`↔反馈）、`DECLARED_COMPUTED`（`dPosition_diff`、`dVelocity_diff` 声明为派生列）。
- `check_coverage(header_columns)`：表头有列既未映射也未入 extra、或一列同时被映为两种角色 ⟹ 抛 **`AssertionError`**（注意不是 ScopeFormatError）。

## 4. `src/axiscope/c1.py` — C1 样本包装配

docstring 口径：「任何超出契约的推断一律不写进包，改写进 `meta.audit.assumptions`」。

关键常量：`SCHEMA = "axiscope.waveform/1"`；`VOCAB_ORDER` 恰 14 个 canonical 通道（`pos_cmd, pos_fb, fe, vel_cmd, vel_fb, cur_q, cur_cmd, torque, temp, laser_power, io, vision_x, vision_y, vision_angle`）；`SEGMENT_KINDS` 10 种（`rest, move, settling, dwell, probing, path, homing, scanning, curing, unknown`）；`CITATION`（DARUS-3600，DOI `10.18419/DARUS-3600`）；恒等式容差组 `IDENTITY_REL_TOL=1e-12` 等；`AUDIT_IDENTITY_KEYS` 8 键。

| 符号 | 职责 |
|---|---|
| `build_meta(table, *, sample_id) -> (meta, ingest)` | 按 `table.dialect` 分派：D1 走门控取最长 episode + `_identity_scan` / `_pairwise_findings` / `_masquerade_check` / `_velocity_sign_check` / `_segments`；其余方言走 `_build_meta_generic`（profile 标 `dialect_generic`） |
| `write_pack(meta, ingest, outdir) -> dict` | 只写两个文件：`waveform.tsv`（UTF-8、LF、TAB，首列 `t`，`b` 前缀布尔列排除）与 `meta.json`；返回 `{"dir", "sha256", "n_rows", "n_cols"}`，`sha256` 是 waveform 字节 + meta body 的联合哈希 |
| `class PackError(Exception)` | D1：门控全程为 0、无 `SampleTime[ms]`、无 move/settling/probing 段（C1 红线 4）；generic：无采样周期来源、时间列只有 1 行、dt 中位数算不出 |

meta 顶层键（两条路径同构，实测 24 键，`c1.build_meta(read_scope("data/raw/Export10_244531.csv"), sample_id=…)` 现数）：`schema, source, sample_rate_hz, sample_rate_source, units_are, counts_per_mm, encoder_lines, rated_current_a, axis, sensor_config, cross_validation, drive, present_channels, time_bases, primary_time_base, resample, channels, extra_channels, io_bits, segments, quality, context, provenance, audit` 等；`quality` 含 `n_samples, dt_median_s, dt_jitter_ratio, gap_max_s, nan_ratio, nan_ratio_by_channel, quantization_step_counts, nyquist_hz, flags`；`audit` 含 `assumptions, identity_check`。

ingest 顶层键 9 个：`wave_columns, series, t, canon_series, findings, pairs, masquerade, identity, sign_check`（只在内存里传给 C2，不落盘）。

**注意**：DARUS-3600 样本实际只映出 3 个 canonical 通道；`pos_cmd/pos_fb/fe/cur_q` 等 11 个词表名只存在于 `VOCAB_ORDER`——「词表」是契约全集，「已映射」是当前样本子集，Wiki 使用本仓时不得混用这两个数。
