# C1 — 规范波形契约（canonical waveform）

所有上游解析器的输出、所有下游分析器的输入，都必须落在这个格式上。
诊断内核**不认识**任何厂商格式，只认识本契约。

## 目录结构

一个可分析的样本是一个目录（下称 *样本包*）：

```
sample/
  meta.json          # 必需：元数据 + 通道表 + 分段
  waveform.tsv       # 必需：制表符分隔，UTF-8，首行表头
  raw/               # 可选：原始厂商文件，仅用于溯源
  events.jsonl       # 可选：机器状态与事件层，见 C6
  process.json       # 可选：工艺/标定/节拍侧特征载体，见 C7
  calibration.jsonl  # 可选：标定批次序列，见 C7
  truth.json         # **仅合成数据可有**：故障真值标签，用于评测
```

**真实样本包内出现 `truth.json` 即为污染**：加载器必须拒收并报错。
真值标签一旦和真实测量混放，评测就会在不知不觉中被答案污染（C5 反自验证纪律）。

## waveform.tsv

- 第 1 列固定为 `t`，单位 **秒**，从 0 开始，必须单调递增。
- 其余每列是一个通道，列名必须取自下方 `channel` 词表。
- 缺失通道直接不出现在表头中（不要写空列）。诊断覆盖度由 `present_channels` 决定。
- 数值为浮点；坏点写 `nan`。

## 通道词表

| canonical | 中文名 | 单位 | 说明 |
|---|---|---|---|
| `pos_cmd` | 位置指令 | counts | 上位机/插补器下发的指令位置 |
| `pos_fb` | 位置反馈 | counts | 编码器实际位置 |
| `fe` | 跟随误差 | counts | `pos_cmd - pos_fb`；若原始数据未提供则由加载器派生 |
| `vel_cmd` | 速度指令 | counts/s | |
| `vel_fb` | 速度反馈 | counts/s | |
| `cur_q` | 转矩电流 | A（或 %） | q 轴电流，含噪声，是共振识别的主通道；单位取 `channels.cur_q.unit` |
| `cur_cmd` | 电流指令 | % | 归一化 -100..100 |
| `torque` | 转矩 | % 或 N·m | 单位取 `channels.torque.unit`，见下 |
| `temp` | 电机温度 | °C | |
| `laser_power` | 光功率 | µW 或 dBm | 耦合设备专用，通道语义与采样门禁见 **C7** |
| `io` | 数字状态字 | int | 位解码后写入 `meta.io_bits` |
| `vision_x` `vision_y` `vision_angle` | 视觉测量值 | counts / ° | 视觉通道按 15-60Hz 降采样 |

**厂商布尔列不是通道**：`bTrigger_Record` / `bMovingForward` 这类独立布尔列由解析器用作
**门控与定符号的内部输入**，不写入 `waveform.tsv`（KB2 §七.4）。理由：它们一旦进波形表，
就会被频谱类特征误当信号处理。

**单位规则**：`meta.units_are ∈ {counts, si_native}`，默认 `counts`。
- `counts`：内部基准为编码器 counts，物理换算只通过 `meta.counts_per_mm` / `counts_per_deg`
  在报告层进行。未提供换算系数时 `counts_per_mm = null`，所有物理量标注 `[counts]`
  且**不得**在报告里伪造 µm 数值——没有定标系数就不知道是不是微米级。
- `si_native`：源数据本身就是 SI 量纲（实测教训：DaRUS 两份真实数据的位置/速度/转矩是 m、m/s、N·m，
  根本没有 counts 刻度）。此时按真实单位标注，但**同一条纪律换个形式仍然生效**：
  缺定标不得臆造**其它**单位（例如把 m 冒充 µm 级精度）。
- `torque.unit ∈ {percent_of_rated, N_m}`：DaRUS 的 `dTorque_*` 是 N·m，且原作者脚本另有 ×10 修正，
  旧版把 `torque` 锁死为「额定百分比」会直接错一个量级。
- `cur_q.unit ∈ {A, percent_of_rated}`：归一化只在 `meta.rated_current_a` 存在时才允许，
  否则 C2 的 `*_pct` 类字段必须为 `null`。
- `torque` 的百分比归一化对称地要求分母有来源（A-70）：`meta.drive.rated_torque_N_m` 存在，
  且 `rated_torque_source ∈ {measured, manual, nameplate, assumed}`。四档的合法性递减：
  `assumed` 仍允许算 `*_pct`，但**证据层级最高只能到 T2**，且报告 caveats 必须写
  "额定转矩为假定值，百分比类判据的绝对刻度不可信"。该字段为 `null` 时 `*_pct` 恒 `null`
  ——这是 KB5 §7 上报的"`cur_q_saturation_ratio` 一类比值判据没有合法分母"的收口。

**位置通道的装在哪一侧**（A-68）：`meta.channels.<pos_channel>.sensor_side ∈ {motor, load, unspecified}`
（可选，缺省视为 `unspecified`）。它存在的唯一理由：当 `sensor_config == "mixed"` 时，
"峰"可能来自电机侧编码器、"谷"来自负载侧光栅尺，两套通道各自估出的极零点被拼成一条曲线，
此时 KB3 R-04 的 `f_anti < f_res` 顺序判据**不适用**（它只对同一传递函数成立）。

## meta.json

```json
{
  "schema": "axiscope.waveform/1",
  "source": {
    "vendor": "beckhoff",
    "drive_model": "TwinCAT3 ScopeView",
    "export_format": "csv",
    "original_filename": "AX1_20260311_1422.csv",
    "tier": "T3",
    "ingest_confidence": 0.9
  },
  "sample_rate_hz": 8000.0,
  "sample_rate_source": "inferred",
  "units_are": "counts",
  "counts_per_mm": 50000.0,
  "encoder_lines": 16777216,
  "rated_current_a": 4.6,
  "axis": {"name": "X1", "type": "linear", "motor_rev_counts": 524288,
           "travel_limit_neg_mm": null, "travel_limit_pos_mm": null},
  "sensor_config": "motor_side",
  "cross_validation": {
    "pairs": [["pos_fb", "laser_ref"], ["pos_fb", "scale_fb"]],
    "note": "多余的位置反馈经 extra_channels 保留，分歧本身是证据（C2 `sensor_disagreement`）"
  },
  "drive": {
    "position_loop_period_us": null,
    "velocity_loop_gain_hz": null,
    "current_loop_bandwidth_hz": null,
    "rigidity_level": null,
    "notch_filters": [],
    "inertia_ratio": null,
    "rated_torque_N_m": null,
    "rated_torque_source": null,
    "current_limit_a": null,
    "current_limit_source": null
  },
  "present_channels": ["pos_cmd", "pos_fb", "cur_q"],
  "time_bases": [
    {"id": "tb0", "role": "primary", "n_samples": 12000,
     "dt_median_s": 0.000125, "sample_rate_hz": 8000.0,
     "dt_jitter_ratio": 0.02, "strictly_monotonic": true, "unit_source": "measured"}
  ],
  "primary_time_base": "tb0",
  "resample": [],
  "channels": {
    "pos_cmd": {"raw_column": "S.T.0:[Axis1] CmdPos", "unit": "counts", "sensor_side": "unspecified",
                 "sign": 1, "offset": 0, "inferred": true, "confidence": 0.95,
                 "time_base_ref": null},
    "cur_q":   {"raw_column": "S.T.0:[Axis1] It", "unit": "A", "sensor_side": "motor",
                 "sign": -1, "offset": 0, "inferred": false, "confidence": 1.0,
                 "time_base_ref": null}
  },
  "extra_channels": {
    "laser_ref": {"raw_column": "dPosition_test", "unit": "m"},
    "scale_fb":  {"raw_column": "dPosition_load", "unit": "m"}
  },
  "io_bits": {"0": "home_sensor", "1": "limit_neg", "2": "limit_pos", "8": "settled"},
  "segments": [
    {"id": 0, "kind": "move",     "t0": 0.012, "t1": 0.089, "axis": "X1"},
    {"id": 1, "kind": "settling", "t0": 0.089, "t1": 0.140, "axis": "X1"},
    {"id": 2, "kind": "dwell",    "t0": 0.140, "t1": 0.400, "axis": "X1"},
    {"id": 3, "kind": "move",     "t0": 0.400, "t1": 0.470, "axis": "X1", "note": "反向"}
  ],
  "quality": {
    "n_samples": 12000,
    "dt_median_s": 0.000125,
    "dt_jitter_ratio": 0.02,
    "gap_max_s": 0.00025,
    "nan_ratio": 0.0,
    "nan_ratio_by_channel": {"pos_cmd": 0.0, "pos_fb": 0.001, "cur_q": 0.0},
    "quantization_step_counts": 1.0,
    "nyquist_hz": 4000.0,
    "flags": ["time_column_relative"]
  },
  "context": {
    "machine": "共晶贴片机 DA-300 / X 轴",
    "complaint": "高速取片后末端抖动，节拍被迫从 1.8s 放宽到 2.6s",
    "operator_notes": "冷机正常，运行 40 分钟后变差"
  },
  "audit": {
    "assumptions": [
      {
        "anchor": "meta.drive.current_limit_a",
        "statement": "限流值未给（drive.current_limit_a = null）⟹ cur_q_saturation_ratio 的分母按 1.0·rated_current_a 兜底，该比值层级封顶 T2、只作定性支路（A-80）"
      },
      {
        "anchor": "meta.quality.dt_median_s",
        "statement": "时间列是相对毫秒（quality.flags ∋ time_column_relative）⟹ 绝对时钟对齐未知，跨源事件对齐一律按 uncertainty_ms 门禁处理（C6 规则 3）"
      }
    ]
  }
}
```

### 必填 / 选填

- 必填：`schema`、`sample_rate_hz`、`present_channels`、`quality.n_samples`
- 强烈建议：`segments`、`context.complaint`（诊断的问题锚点）
- `drive.*` 任何字段缺失时，规则引擎必须把依赖该字段的判据降级为 `unverified`，
  **不允许**用默认值冒充实测值。
- `drive.rated_torque_N_m` / `rated_torque_source`（A-70）与 `axis.travel_limit_*_mm`（A-69）
  都是**可选**：缺省 `null`。`rated_torque_source == "assumed"` 是合法值，但它把该样本所有
  百分比类判据的层级压到 T2 并强制写 caveat——登记假定值比隐瞒假定值好，
  隐瞒会让 `cur_q_saturation_ratio` 之类的判据看起来有绝对刻度。
- `drive.current_limit_a` / `current_limit_source`（A-80）同为**可选**，值域与四档合法性同 A-70。
  它是 `global.cur_q_saturation_ratio` 的**唯一合法分母**（"电流是否打到驱动器限流"是判据 R-06/R-12
  饱和支路的核心，用额定电流冒充限流值会把比值系统性抬高——`rated_current_a` 是连续允许值，
  限流值通常更高）。缺该字段时 KB3 §1.1 的 `1.0·rated_current_a` 兜底**必须**同时写进
  `audit.assumptions` 并在特征行标 `denominator_basis: "assumed_rated_current"`；
  此时该比值只允许作**定性**支路判据（层级封顶 T2，同 A-70），不得单独触发归因。
- `channels.<pos>.sensor_side`（A-68）可选，缺省 `unspecified`；只有当
  `sensor_config == "mixed"` 时才必须逐通道填写（否则无法说明"峰和谷不是同一传递函数"）。

### `audit.assumptions` 的元素形状（#25；C3 规则 19 的唯一真值）

全仓有约 30 处义务写着"记入 `audit.assumptions`"（本契约派生规则 6/8、C2 规则、C6 规则 3、
C7 规则 3/4、KB3 纪律 6、KB4 §2.9、KB6 §6），而这个字段**长什么样从没定义过**：接入层与引擎
各写散文，报告只能整段打印，于是"这条假定作废时哪些结论跟着塌"在契约层无法回答，
C5 的拒答正确率也没法引用某一条假定。现定死为**两键对象**，不多不少：

```json
{"anchor": "<稳定锚>", "statement": "<缺的是什么 ⟹ 于是按什么值/口径继续>"}
```

- **`anchor` 必须落在六种稳定形式之内**，词表的唯一实现是 `src/axiscope/anchors.py`
  （C1 接入层与 C3 引擎层共用一份，A-54"只有一个名字"同律）：
  ① `meta.<字段路径>`（如 `meta.drive.current_limit_a`）；② 通道（`channels.<名>`、
  `extra_channels.<名>`）；③ C2 特征路径（如 `event_context.sync.uncertainty_ms`）；
  ④ 规则/判据（`R-<nn>`，指到支路时 `R-<nn>#<支>`）；⑤ KB4 叶名（即 `hypotheses[].cause`
  的取值，如 `electrical_feedforward_mismatch`）；⑥ 文档锚 `KB<n>§<节>`——**只留给"假定来自
  文档缺口而非某个字段"的情形**（例：`sample_counts` 侧车键在 C2 没有载体时锚 `KB4§2.1(c)`）。
- **散文不是锚**：以中文句子起头、含空格、或写成仓内路径（`../`、`src/…`）的 anchor
  一律由 `C3-R19-assumption-shape[<i>]` 判失败。这条不是措辞洁癖——锚的唯一用途是被引用，
  `verdict.caveats`、`next_data_to_collect` 与 C5 的评分都要能指回"哪一行假定"。
- **`statement` 非空**，且必须同时说清两件事：缺的是什么、于是按什么值或口径继续。
  只写"已作相应假设"不合格（它没有可作废的内容）。
- 本条只管 `assumptions`。`audit.arbitration_notes` 记的是仲裁过程、不是假定，
  保持散文行，不得顺手同构化（没有读者需要引用其中某一条）。
- 载体两侧各两行：本契约示例的 `meta.audit.assumptions`、C3 契约示例的 `audit.assumptions`
  （检查 23"字段须有载体"）；生产者是 `c1.py::build_meta` 与 `registration.Ledger.assume`
  / `engine.analyze`，`tests/test_engine.py::test_every_assumption_row_has_a_stable_anchor`
  逐行过词表。

### 多速率栅格（A-96）

一条记录里可能挂着**不止一条时间栅格**（dSPACE MDF 一类：轨迹栅格与测量栅格不同速，
另有离散事件栅格）。C1 用 `time_bases[]` 表达这件事，而不是靠 `sample_rate_hz` 猜。

```json
"time_bases": [
  {"id": "tb0", "role": "primary",   "n_samples": 73020, "dt_median_s": 0.001,
   "sample_rate_hz": 1000.0, "dt_jitter_ratio": 2.6e-07, "strictly_monotonic": true,
   "unit_source": "measured"},
  {"id": "tb1", "role": "secondary", "n_samples": 292080, "dt_median_s": 0.00025,
   "sample_rate_hz": 4000.0, "dt_jitter_ratio": 1.0e-06, "strictly_monotonic": true,
   "unit_source": "measured"},
  {"id": "tb2", "role": "event",     "n_samples": 26,    "dt_median_s": null,
   "sample_rate_hz": null, "dt_jitter_ratio": 0.2206, "strictly_monotonic": false,
   "unit_source": "measured"}
],
"primary_time_base": "tb0",
"resample": [
  {"op": "nearest", "from": "tb1", "to": "tb0", "channels": ["x_meas_table"],
   "band_effect": "band_lost",
   "note": "4 kHz 测量通道投到 1 kHz 主栅格用于 fe 恒等式核对；4 kHz 频带内容在此运算中不可保留"}
]
```

规则（**违反任一条即不是合法 C1**）：

1. `role == "primary"` **有且仅有一条**，`meta.primary_time_base` 必须指名它；
   `secondary` / `event` 可有 0..n 条。`id` 在包内唯一。
2. `channels.<name>.time_base_ref` 指向 `time_bases[].id`，缺省 `null` = 继承 primary。
   `extra_channels` 同样适用（`extra_channels.<name>.time_base_ref`）。
3. **跨栅格比较必须显式重采样并登记**：每执行一次跨栅格运算，就在 `meta.resample[]` 追加一条，
   `band_effect ∈ {none, band_lost, aliased_risk}` **必填**。
   `band_lost` = 高栅格降到低栅格（高于新奈奎斯特的内容不可保留）；
   `aliased_risk` = 低栅格插值到高栅格（凭空造出高频，易被误当真峰）。
   **留空等同「不影响频带」是禁止的。**
4. **向后兼容**：`sample_rate_hz` / `sample_rate_source` / `quality.*` / `quality.nyquist_hz`
   一律定义为**主栅格**口径。单栅格文件补一条 `{id:"tb0", role:"primary", …}` 即可，
   解析器与规则引擎**不需要为单栅格新增任何分支**。
5. `role == "event"`（如 `OnChange`）是**离散事件栅格**，**禁止**参与
   `fs` / 时长 / 抖动判定，**不得**触发「时基非严格单调」硬拒，
   也不得作为相干/相位类判据的时间轴。
6. **频带门禁按「被比较通道各自所在栅格」判定**（A-94 的样本级精神在多栅格下的细化）：
   参与同一判据的通道若不在同一栅格，或其重采样登记为 `band_lost` / `aliased_risk`，
   则相干/相位类结论一律 `unavailable` 并写明 reason——**不得**在降采样后的序列上给相干结论。
7. `unit_source` 语义同 `sample_rate_source`：单位无来源时**不得**据推断开硬拒（KB2 §5.2）。

## segments.kind 词表

`rest` `move` `settling` `dwell` `probing`（恒速测量段）`path`（插补连续路径）
`homing` `scanning`（寻光扫描）`curing`（固化跟随）`unknown`

分段是**必需**的：几乎所有诊断判据都要求"在特定运动语境下"才成立。
例如"高频恒定啸叫"只在 `dwell` 段仍出现才判机械共振；"位置指令静止时不出现的峰"
是区分机械共振与前馈失配的关键条件（见 C3 规则 R-03）。

## 派生规则

加载器必须保证以下不变式，违反则报错而非静默修正：

1. 若给了 `pos_cmd` 和 `pos_fb` 而没给 `fe`：`fe := pos_cmd - pos_fb`。
2. **自带"看起来像跟随误差"的通道不得直接改名叫 `fe`**（实测陷阱：DaRUS 的 `dPosition_diff`
   名为 diff，实为 `= -(p_test + p_load)` 的绳长守恒残差——18,651 行行级最大残差 3.55e-15，
   **是 PLC 现场计算列，与 `pos_cmd - pos_fb` 无关**；A-104 把它从 `≈` 升格为 `=`）。
   `fe` 只允许两条来源：由 1 派生，或候选通道通过 `corr(fe_derived, candidate) > 0.99` 自检；
   未通过自检就按候选原名放进 `extra_channels`，并在 `audit.assumptions` 登记。
   **自检退路的两条硬性补充**（A-104）：① `corr` 需要两侧都有方差——若 `pos_cmd ≡ pos_fb`
   （本样本即如此，0/18,651 行有差）则 `fe ≡ 0`、corr 无定义，此时**不得**因"自检跑不了"而放行改名，
   只能判 `unavailable`；② 恒等式核对（候选列 ≡ 同文件另两列的线性组合）一旦成立即**独立于** corr
   地否决该候选，因为零信息列不可能承载跟随误差。
   **符号约定**：不同厂商 `fe` 定义相反，若两者都有则用派生式校验方向，不许猜。
3. 若只给了 `fe` 和 `pos_fb`：`pos_cmd := fe + pos_fb`。
4. 若只有 `fe`：允许，但 `move` 段的运动学特征（超调、稳定时间）标记 `unavailable`。
5. `vel_fb` 缺失时可由 `pos_fb` 差分派生，但必须写入 `channels.vel_fb.derived = true`，
   且频谱类判据的置信度乘 0.7（差分放大噪声）。
6. 重采样：所有分析在原始时间轴上做；需要等间隔时用多相重采样并记录 `resampled: true`。
7. `sensor_config ∈ {motor_side, load_side, mixed, unknown}` 决定谐振/反谐振的**先后顺序期望**：
   共置（电机侧执行器 + 电机侧反馈）两惯量系统必有 `f_anti < f_res` 且
   `f_res / f_anti = sqrt(1 + λ)`；负载侧反馈则顺序相反。缺省 `unknown` 时，
   双惯性配对判据（KB3 R-04）的顺序项**不参与判定**，只按幅值与相位条件评，
   且结论置信度封顶——顺序本身就是"哪个传感器在说话"的证据，不能拿来反推又不声明。
   `mixed`（电机侧反馈 + 负载侧反馈拼成一条曲线，或峰谷分别来自两套通道，A-68）与
   `unknown` 走同一行为（顺序项不评、置信度封顶），区别只在**记录原因**：
   `unknown` 是"不知道装在哪侧"，`mixed` 是"知道这条曲线不是同一传递函数的响应，
   因此峰谷对不承载零极点交替信息"。KB5 曾把 P-B2/INJ-30 临时写成 `unknown` + assumptions，现改 `mixed`。
8. `axis.travel_limit_neg_mm` / `axis.travel_limit_pos_mm`（可选，缺省 `null`）：软限位是厂商
   手册明列的参数，属上下文而非波形特征（A-69）。为 `null` 时依赖行程边界的判据
   （如 KB3 的撞限位/越界类）必须 `unavailable` + 登记 `blocked_rules`，
   不许从"波形里位置曾经停住"反推限位值再当作已知参数用。
9. **算出来的列不是第二次测量**（A-104 / A-105）：接入层必须对同文件各列做逐行恒等式核对。
   该核对由 `c1._identity_scan()` 在**门控后进入样本包的切片**上执行（覆盖全部数值列，`b*` 布尔列除外），
   载体三处：`meta.audit.identity_check` 摘要（`performed` / `n_numeric_columns` / `n_rows_checked` /
   `n_derived` / `n_duplicate_groups` / `n_constant_columns` / `n_independent_position` / `reason`）、
   接入侧车 `ingest.identity` 全文（逐条关系的方向、系数、残差与容差）、以及 findings 逐列登记
   （kind 取 `derived_column` / `duplicate_column` / `linear_dependency_unattributed` /
   `measurement_independence`）。
   若某列 ≡ 同文件另几列的定系数线性组合（**行级最大残差** ≤ 1e-12 × 该列幅值），它是控制器
   **现场算出的派生列**，必须在 `extras[].derived_from` 列出原料列，并**排除**在三种用途之外：
   ① `fe` 候选（派生规则 2）；② `second_feedback_available` / 交叉验证的**计数**（C2
   `feedback_integrity`、`sensor_disagreement`）；③ 任何以"两路独立测量分歧"为前提的判据。
   同理，**逐行全等**的两列只算一路测量，保留侧恒为反馈列、丢弃侧为 `_tar` 指令列
   （母本全量 18,651 行实测：`dPosition_test ≡ dPosition_test_tar`、`dPosition_load ≡ dPosition_load_tar`，
   各 0/18,651 行有差）。
   **归因纪律**（A-105 ①）：一条恒等式有三个可书写方向，数据本身说不出控制器算的是哪一列，
   所以方向**只在**接入层的文档声明登记表 `mapping.DECLARED_COMPUTED`（来源 KB2 §4.10 通道卡）
   逐字且唯一命中该关系时才断言；未命中或多列同时可当"被算出的那一列"⟹ 该关系按
   `linear_dependency_unattributed` 登记，**只扣一个自由度、不给任何一列贴派生标签**
   （约束是实测的，因果方向不是）。
   - **母本全量 18,651 行实测**的两条派生列：`dPosition_diff ≡ -(dPosition_test + dPosition_load)`
     （残差 3.55e-15）与 `dVelocity_diff ≡ -(dVelocity_test + dVelocity_load)`（残差 4.44e-16）——
     它们作为「绳长守恒残差」可以进诊断，但**不配**作为独立反馈参与互证。
   - **门控后 5000 行切片实测**（Export10_244531，28 个数值列 / 5000 行，关系按基去重后 3 条）：
     归因的派生列 2 —— `dPosition_diff` 行级最大残差 8.16e-15 m（容差 1.33e-13）、
     `dVelocity_diff` 2.83e-14 m/s（容差 5.91e-14），方向之所以被断言是**文档声明的**，不是从数据推出的；
     全等孪生 3 组（`dVelocity_load_tar ≡ dVelocity_load`、`dPosition_load ≡ dPosition_load_tar`、
     `dPosition_test ≡ dPosition_test_tar`）；常数列 2（`dForceSensorNo`、`dForce_tar`）；
     第三条关系 `dForce_diff ≡ dForce_load − dForce_test`（最小行级最大残差 2.52e-14，
     系数 diff −1 / load +1 / test −1）**只登记未归因**，reason「文档未声明其中任何一列为计算列」。
     位置列计数：`position_columns_seen` = 8，去派生列（`dPosition_diff`）、去 `_tar` 全等孪生
     （`dPosition_test_tar`、`dPosition_load_tar`）后——本切片没有未归因关系落在位置列上，力族那条不占位置自由度——
     `independent_position_columns` = `dPosition_asco_enc`、`dPosition_asco`、`dPosition_load`、
     `dPosition_test`、`dPosition_lsv_enc`，即 **`n_independent_position = 5`**（A-105 ⑤ 要的落档）。
   - 核对跑不起来时（数值列 < 3，或有限值行 < 100）`performed = false`、`n_independent_position = null`：
     一切"两路独立测量分歧"类判据一律 `not_evaluable`，登记 `blocked_by = derived_column_unchecked`，
     reason 固定句式「接入层未做列间恒等式核对，独立测量数不可信（A-105 ④）」——
     **不得**因"没跑出关系"就给出乐观的独立测量数。

## 数据质量红线

以下情况**拒绝诊断**，返回 `insufficient_data` 并说明原因：

- `n_samples < 2000` 或有效时长 < 0.5s
- `dt_jitter_ratio > 0.2`（时基不稳，频谱不可信）
- `nan_ratio > 0.05`
- 没有任何 `move`/`settling`/`probing` 段（全程静止，无从判断动态）
- `cur_q`、`vel_fb`、`fe` 三者全无（只剩位置，可做的诊断太少，直接说明限制）

**红线适用范围**：以上阈值只约束**伺服栅格通道**。工艺侧的稀疏读数（光功率等 1–20 Hz 轮询量）
默认不进 `waveform.tsv`，而走契约 **C7** 的 `process.json`，并自带 `power_channel.nan_ratio` /
`dt_jitter_ratio`（口径独立，见 C7 §2.2）。
唯一例外：`transport == "analog_daq"` 且 `timestamp_source == "device"`（与伺服同源时钟采集）时
`laser_power` 可作为等间隔列进入本契约，此时按 `quality.nan_ratio_by_channel` **逐通道**判红线，
不用全局值——否则一个工艺通道的空洞会误杀整份伺服诊断（裁决 A-29 / A-44）。
`nan_ratio_by_channel` 缺省时回退全局 `nan_ratio`。
