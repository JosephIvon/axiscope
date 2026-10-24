# KB2 — 波形数据格式规范与解析器需求

> 定位：axiscope 整条诊断链路的**入口质量闸门**。C2 特征内核只读 C1 规范样本包，
> 绝不接受任何厂商原始格式；因此解析器（本文件规范的对象）一旦把语义或时基搞错，
> 下游所有诊断输出都是幻觉。本文件**只写规范、判定规则与校验断言，不写产品代码**。
>
> 事实来源：所有关于真实数据的断言，均来自已下载核验的
> DaRUS（斯图加特大学）Beckhoff TwinCAT Scope View 原生导出 CSV 及其原作者 MATLAB 脚本，
> 具体为 `data/raw/Export10_244531.csv`（DARUS-3600，`dXxx` 命名）、
> `data/raw/catcsv2cell.m`、`data/raw/catanalyze.m`、`data/raw/main.m`、
> `data/probe_cat.py`（一次性审计脚本，非产品代码）与 `docs/kb/KB7-dataset-da-rus-cat.md` 的实测结论。
> 凡未在上述文件中直接观测/推导出的细节，一律显式标注 **「未核验，需实测」**，不凭印象补全。
>
> 命名与单位纪律以 `docs/kb/KB0-conventions.md` 为准；契约以
> `docs/contracts/C1-canonical-waveform.md`、`docs/contracts/C6-machine-context.md` 为准。

---

## 〇、样本包回顾与解析器职责边界

解析器的**唯一输出**是一个 C1 规范样本包目录：

```
sample/
  meta.json        # 必需：元数据 + 通道表 + segments + quality + provenance
  waveform.tsv     # 必需：UTF-8 制表符，首列表头，第 1 列 t（秒，单调递增）
  raw/             # 必需（本项目）：原始厂商文件，脱敏后入包，仅溯源
  events.jsonl     # 可选：C6 事件流；本项目 Scope View 导出**不含**事件流 → 见 §五 影响
  truth.json       # 仅合成数据有；真实数据不产出
```

职责边界（越界即视为解析器缺陷）：

- 解析器**负责**：表头结构定位、时基推断与抖动度量、触发门控、方向符号修正、
  通道语义映射（厂商名 → C1 词表）、`fe` 派生、单位/定标登记、`segments` 生成、
  `quality.*` 全部指标计算、脱敏、以及 §五 的拒入判定与错误输出。
- 解析器**不负责**：任何频谱/共振/摩擦判据计算（属 C2）；任何归因（属 C3/KB4）。
- 解析器**禁止**：用默认值冒充实测值（C1 `drive.*` 纪律）；猜测未映射通道的语义（§三）；
  对不可映射项假装成功（§四）。

---

## 一、TwinCAT Scope View 原生 CSV 逐行解剖

以真实文件 `Export10_244531.csv`（32 通道 / 64 列 / 18650 数据行；KB7 实测）为标本。
下列**行号仅用于讲述结构，不得作为解析器的硬编码常量**（原因见本节末）。

| 物理行 | 首字段（field[0]） | 含义 | 示例值（实测） | 解析动作 |
|---|---|---|---|---|
| 1 | `Name` | 导出集标题 | `Name<TAB>Measurement` | 存 `provenance.export_title`；仅 2 字段 |
| 2 | `File` | 原始导出文件的**本机绝对路径** | `[REDACTED_HOST_PATH]\Export 10.csv` | **PII**：脱敏（§六）；只留 basename 或占位 |
| 3 | `Starttime of export` | 导出起始墙钟 | `[REDACTED_WALLCLOCK]`（.NET ticks，100 ns 单位 + 德语日期 + 时刻；原值已按 §六 令牌化） | 存 `provenance`，**仅溯源**；时区未标注（KB7）→ 不作为绝对时基，不参与 C6 对齐 |
| 4 | `Endtime of export` | 导出结束墙钟 | `[REDACTED_WALLCLOCK]` + 德语日期 + 时间（原值已令牌化） | 同上；可用于算导出总时长（≈18.65 s = 18650 行 × 1 ms，自洽） |
| 5 | （空） | 分隔 | — | 跳过 |
| 6 | （空） | 分隔 | — | 跳过 |
| 7 | `Name` | **通道名表头行（约定 A：Scope 别名）** | `Name<TAB>dForce_load<TAB>Name<TAB>dPower_load<TAB>…` | 定位 names；通道数 `N = 奇数列个数`；见下 |
| 8 | `SampleTime[ms]` | 每通道声明的采样周期 | `SampleTime[ms]<TAB>1<TAB>…`（奇数列恒为 `1`） | `dt_ms = field[1]`；与数据列 col0 差分交叉校验 |
| 9 | `SymbolBased` | 引用方式 | `SymbolBased<TAB>True<TAB>…` | 元数据；`True` 表示按符号名引用 |
| 10 | `SymbolName` | **完整 ADS 符号路径（约定 B）** | `SymbolName<TAB>Measurement_Connector.dForce_load<TAB>…` | 写入 `channels[k].raw_column`；DARUS-5171 变体**无本行**，其第 8 行为 `Data-Type<TAB>REAL64`（**2026-10-20 已实测核验**，见 §4.11——本表其余行同理只描述 3600 变体，表头总行数 3600=13 / 5171=10） |
| 11 | `NetID` | 目标 PLC 的 ADS 路由 | `NetID<TAB>[REDACTED_ADS_NETID]<TAB>…` | **PII/网络标识**：脱敏（§六） |
| 12 | `Port` | ADS 端口 | `Port<TAB>851<TAB>…` | 存 `provenance`（851 = TC3 标准运行时端口，非 PII，可留） |
| 13 | （空） | 分隔 | — | 跳过 |
| 14+ | 数字 | **数据区** | `0<TAB>150.6<TAB>0<TAB>-4<TAB>0<TAB>4<TAB>…` | 见下 |

### 1.1 `(SampleTime, value)` 交替列的成因与取列方式

- Scope View 把**每个通道的时间基准都单独成列**导出：数据区是 `N` 组 `(t_ms, value)` 交替，
  组内偶列为该通道的时间戳、奇列为该通道的值。因为本数据集所有通道共用同一等间隔时基
  （`SampleTime=1 ms`），**每一行的所有偶列彼此相等，且等于行计数器**。
  实测：第 14 行（row 0）偶列全为 `0`；第 15 行全为 `1`；第 16 行全为 `2`……即偶列 = 样本序号 = `t_ms`。
- 取列规则（`probe_cat.py` 实测正确，作为权威）：
  - `names = [tok for i,tok in enumerate(header_row.split("\t")) if i % 2 == 1]`（取第 7 行**奇数列**）；
  - 第 `k` 个通道的值列 `value_col(k) = 2*k + 1`（0 基）；时间列取 col0（`2*k` 均可，等间隔下恒等）；
  - 原作者 `catcsv2cell.m` 用 MATLAB 1 基 `A(:,iD*2-2)`（`iD≥2`），等价于 0 基 `2*(iD-2)+1`，**两者一致**；
  - 时间轴（秒）：`t = col0 * dt_ms / 1000`（`catcsv2cell.m` 第 20 行 `A(:,1)*SampleTime`，`SampleTime=0.001`）。

### 1.2 两套命名约定如何同时存在

同一批通道有两套名字，逐列并存：

| 约定 | 出处行 | 例（本文件，DARUS-3600） | 例（DARUS-5171，KB7） |
|---|---|---|---|
| A：Scope 别名 | 第 7 行 `Name` 奇数列 | `dPosition_test` | `x_T` |
| B：ADS 符号路径 | 第 10 行 `SymbolName` 奇数列 | `Measurement_Connector.dPosition_test` | 未在本文件实测→**未核验** |

- 解析器**按列位置索引（`2k+1`）取数**，绝不按名字字符串匹配取数（名字跨战役会变）。
- 两套名字都要登记进 `meta`：`channels[k].raw_column = <约定A别名>`，
  `channels[k].symbol = <约定B符号路径>`（缺符号路径时置 null，不得伪造）。
- 语义映射必须**双词表**（KB7 第 75 行）：别名词表与符号末段词表各一份，任一命中即可，
  因为 3600 用 `dXxx`、5171 用 `x_T` 风格，单词表会漏。

### 1.3 分隔符 / 编码 / 换行 / 小数点（实测）

- 字段分隔符：**TAB**（`probe_cat.py` 以 `split("\t")`）。
- 编码：**UTF-8**，读取用 `errors="replace"`（存在非 ASCII：`ä`、`Versuchsstand`、德语月份）。
- 换行：CRLF 倾向，读取时 `rstrip("\r\n")`（`probe_cat.py` 第 13 行）。
- 小数点：数据区用 **`.`**（美式），例如 `-0.0034129177991999923`、`149.9`；
  **只有日期字段是德语本地化文本**。→ 解析器不得按德语逗号小数解析数据区，也不得因
  日期是德语就切换整个文件的 locale。缺失值/坏点：空串 `""` 与字面 `NaN` 均记为 `nan`
  （`probe_cat.py` 第 24 行把 `""`/`"NaN"` 转 `nan`）。

### 1.4 表头行数不许硬编码 —— 结构特征定位数据起始行

反例证据：`catanalyze.m` 第 14/24 行对 Scope 导出传 `NumHeaderLines=14`，而 `main.m` 第 80 行
对另一文件 `cablerobot_profile.csv` 传 `NumHeaderLines=13`（KB7：该文件无 `Name/Measurement`
表头、纯数字、首列时间 ms）。同为 DaRUS 数据，表头行数不同 → 硬编码 14 会把纯数字文件的前一行
当表头丢掉，或把元数据行当数据。

**判定规则（伪代码，数据起始行 = 靠结构特征定位，不靠常数）：**

```
# 1) 定位“命名表头行” header_row：
#    满足 field[0] == "Name" 且 field[2] == "Name" 且奇数列均为非纯数字标识符
header_row = first line L where L.f[0]=="Name" and L.f[2]=="Name"
if header_row exists:
    N = count of odd-index fields in header_row          # 通道数
    # 2) 元数据块 = 从 header_row 起、连续若干行，其偶数列均为“标签字符串”（非数字）
    #    已知标签集：{Name, SampleTime[ms], SymbolBased, SymbolName, NetID, Port, Data-Type}
    block_end = last line whose even fields all ∈ label_strings
    # 3) 数据起始 = block_end 之后、跳过空行，第一个“偶列可解析为整数且列数 >= 2N”的行
    data_start = first line after block_end where f[0] is int and len(fields) >= 2*N
else:
    # 纯数字 CSV（cablerobot_profile 型）：无 Name 行
    data_start = first line where all fields parse as float and field[0] is monotonically increasing counter
    N = (number of fields in data_start) - 1              # 首列为时间/计数器
```

可判定校验断言（见 §二 各坑末尾统一列出）：`data_start` 行的列数 `>= 2*N`；
`header_row` 唯一；元数据块的每一行偶列标签都属于已知标签集，否则报 `unexpected_metadata_label`。

---

## 二、实测 5 个坑：症状 → 根因 → 正确处置 → 校验断言

每条附**可判定**断言；断言式子写成 `assert(...)` 形式，但不落地为产品代码。

> **证据等级说明（A-31 正面案例）**：本节 5 坑与 §一 的 14 行头结构，均为**本项目对 DaRUS 真实文件
> （`Export10_244531.csv` 等）的直接实测结论，证据 tier = T1-a**，其强度**高于** §四 各厂商卡的
> `public-doc` 二手转录。叙述强度与数据层 tier 对齐（C3 硬性规则 14）正是这里要做到的：实测得到的
> 事实（fs≡1 ms、触发门控比例、方向符号）可用强措辞；§四 那些没有手册 PDF 支撑的签名只能标 `public-doc`。

### 坑 1 — `SampleTime` 恒 1 ms → fs=1000 Hz、奈奎斯特 500 Hz

- **症状**：对这份数据做 FFT/共振检测，任何 kHz 级峰都看不见；若报告写「未检出共振」，
  是错的（物理上不可见，而非无共振）。
- **根因**：Scope View 导出采样周期恒为 1 ms（实测 `SampleTime[ms]=1`；KB7 两份数据皆 1000 Hz）
  → `fs = 1000 Hz`，`nyquist = 500 Hz`。kHz 级机械谐振判据在此时基上**不可评估**。
- **正确处置**：
  1. `meta.sample_rate_hz = 1000.0`，`sample_rate_source ∈ {declared, inferred}`
     （declared 取第 8 行 `SampleTime[ms]`；inferred 取 col0 差分中位数；两者不一致时**取更保守值并记录**）。
  2. `meta.quality.nyquist_hz = 500.0`。
  3. 解析器**到此为止**：它只写 `meta.sample_rate_hz` 与 `meta.quality.nyquist_hz`。
     ~~`meta` 写入 `freq_limits.blocked_rules`~~ —— `freq_limits` 是 **C2 的输出**，不在 C1 `meta` 里
     （C1 无该块；**A-84** 已裁归属），把它写成解析器职责会让"证据"变成"元数据"，
     且解析器无法知道每条规则的声明频点（那在 KB3 §2.1 的 `band⊥` 表里）。
  4. C2 特征内核按规则 7 推导 `freq_limits.reliable_band_hz = nyquist_hz/1.25 = 400.0`，
     并把声明频点越带的规则写入 `freq_limits.blocked_rules`；对本数据集 ⟹ 至少含
     `["R-03","R-04"]`（KB0 §1：二者要求 `reliable_band ≥ 2000 Hz`）。报告层对 R-03/R-04
     必须输出 `not_evaluable`（频带不足），**禁止**输出「未发现共振」。
- **校验断言**：
  - `assert meta.sample_rate_hz == 1000.0 and meta.quality.nyquist_hz == 500.0`
  - `assert set(["R-03","R-04"]) ⊆ set(features.freq_limits.blocked_rules)`（断言对象是 **C2 输出**，不是 `meta`）
  - `assert report.rules["R-03"].status == "not_evaluable"`（对本 fs 数据集恒真；若出现 `clear/no_resonance` 判为缺陷）
  - `assert declared_dt == inferred_dt`（不一致则 `sample_rate_source="inferred"` 且记 `audit.assumptions`）
  - 关联任务 #11（500 Hz 奈奎斯特与 kHz 共振判据冲突）。

### 坑 2 — 触发门控陷阱：大量行未被真正记录

- **症状**：RMS/频谱把未记录（触发无效）的行也算进去，能量被稀释/污染，
  4 倍于有效数据的垃圾参与统计。
- **根因**：真实文件 18650 行中 `bTrigger_Record` 仅 **26.8%** 为真、
  `bTrigger_Export` 仅 **2.7%**（KB7 实测）。Scope 连续采集但只在触发有效窗口落库。
- **正确处置**：
  1. **只保留 `bTrigger_Record != 0` 的行**（复刻 `catcsv2cell.m` 第 29 行
     `Exp.Raw.trig_record ~= 0`）。`bTrigger_Record` 值列 = `value_col(别名=="bTrigger_Record")`。
  2. `n_samples` 红线守卫（C1 `n_samples >= 2000`）按**过滤后**的行数计，不是文件行数。
     本文件过滤后 ≈ `18650 × 0.268 ≈ 5000` 行（**未逐行核验具体计数，需实测**；量级由 26.8% 得来）。
  3. 不要用 `bTrigger_Export` 做门控，除非语义明确是「仅落盘子集」；它比 Record 更稀疏，误用会砍掉大部分数据。
  4. 过滤在重采样/统计**之前**完成；被丢弃行数记入 `provenance.trigger_gate`。
- **校验断言**：
  - `assert retained_ratio == mean(bTrigger_Record != 0)`，且 `retained_ratio ≈ 0.268`（容差待实测收紧）
  - `assert meta.quality.n_samples == len(retained_rows)`（绝不用文件总行数）
  - `assert all(row.bTrigger_Record != 0 for row in retained)`
  - `assert not any(analysis_uses(bTrigger_Record==0 row))`
  - `assert meta.quality.n_samples >= 2000` 否则进 §五 拒入。

### 坑 3 — `bMovingForward` 方向符号修正

- **症状**：编码器速度「恒正」，无法区分进/退绕（unwind/rewind），差分/纹波特征方向失真。
- **根因**：外部编码器速度通道（光学 `dVelocity_asco_enc`、电感 `dVelocity_lsv_enc`）导出的是
  **幅值**，方向由布尔 `bMovingForward` 给出；`catcsv2cell.m` 第 41 行把 `mfw<=0 → -1`，
  第 44-45 行 `v_asco_enc .* mfw`、`v_lsv_enc .* mfw`。注意作者**只对外部编码器速度乘方向**，
  电机侧 `v_test` 未乘（本身即带符号）→ 需带符号的是**编码器类幅值通道**，不能一律乘。
- **正确处置**：
  1. 方向乘子 `dir = +1 if bMovingForward > 0 else -1`（`catcsv2cell.m`：`<=0 → -1`，含 0）。
  2. 仅对**登记为 `needs_direction_sign = true`** 的通道应用（默认：外部编码器速度类）。
     哪些通道需要，是数据集属性 → 从映射表（§三）逐通道声明，不得全表一刀切。
  3. 位置侧的符号约定：`catcsv2cell.m` 第 54 行对负载侧位置取负
     `p_load = -(p_load - p_load[0])`；两卷筒反向运动，负载位置要翻号才能与测试侧同向比较。
     翻号是**位置/编码器差分的符号约定**的一部分，必须与 `fe`/差值通道定义联动（见坑 §三 fe 自检）。
  4. 零时基复位 `t = t - t[1]`（第 50 行）在方向修正之后、写 `waveform.tsv` 之前。
- **校验断言**：
  - `assert dir ∈ {+1,-1}` 且 `dir` 只在 `bMovingForward` 跳变处翻转：
     `count(i: dir[i] != dir[i-1]) == count(i: sign(bMovingForward[i]) != sign(bMovingForward[i-1]))`
  - `assert |corrected_ch[i]| == |raw_ch[i]|`（乘子只改符号不改幅值）
  - `assert (sign(corrected_v_enc) == dir) or raw_v_enc == 0`（幅值通道符号必须跟随 dir）
  - `assert corrected_v_test == raw_v_test`（电机侧未被误乘）

### 坑 4 — 行数 ≠ 有效行数（列数参差 / 缺列 / 尾部空行）

- **症状**：解析器假设每行 64 列，遇到列数不足的行崩溃或错位；末尾空行被当成数据。
- **根因**：KB7 第 90 行——末尾有空行、列数参差。列数校验须用 `>= 2*len(names)`，
  **不是 `+2`**（`probe_cat.py` 第 22 行 `if len(c) < 2*len(names): continue`）。
- **正确处置**：
  1. 数据行守卫：`len(fields) >= 2*N` 才纳入；不足则整行跳过（不补零、不前向填充）。
  2. 逐值 `try float() / except → 跳过该行`（`probe_cat.py` 第 25 行）；空串与 `"NaN"` 记 `nan`，
    但整行无法解析（列数不足或非数值首列）则丢弃。
  3. `nan_ratio` 基于**纳入行 × 通道数**的网格统计（`probe_cat.py` 第 79 行分母 `n*len(names)`）。
- **校验断言**：
  - `assert parsed_rows + skipped_rows == total_lines_after_data_start`（账目闭合，无静默丢失）
  - `assert all(len(r) >= 2*N for r in data_rows)`
  - `assert len(set(len(r) for r in data_rows)) <= 1 or ragged accounted`（列数一致或被显式记账）
  - `assert n_channels == N`（每通道数组等长 == 纳入行数，过滤触发后）

### 坑 5 — 前导 `trig_rec=0` 是预触发数据，不是解析错误

- **症状**：文件开头一段（如直驱文件前 809 行，KB7）`bTrigger_Record` 全为 0，
  看着像解析器把数据读错了。
- **根因**：触发-记录门控天然丢弃预触发段（trigger 前的缓冲）；这是有效数据，只是语境为
  静止/预触发（`rest`/`dwell`），不是损坏。
- **正确处置**：
  1. 与坑 2 一致：丢弃 `bTrigger_Record==0` 行是**符合语义**的，但必须
     (a) 记入 `provenance.trigger_gate.dropped_head`，(b) 不得当作错误抛出。
  2. 触发 0→1 的跳变是天然的 **segment 边界**：C1 里被丢弃的头部对应 `segments` 之前的 `rest`
     语境（不写进 `segments`，因为在过滤后的时间轴上已不存在），保留段起点即时间零点。
  3. 时间零点对齐：过滤 + `t = t - t[0]`（`catcsv2cell.m` 第 50 行）后，`waveform.tsv` 的 `t`
     从 0 单调递增（C1 首列要求）。丢弃头部不改变 `t` 的连续性（因为整段头部本就被删除）。
  4. 若产品要保留预触发段作上下文：那需要**另一套时间轴与 `segments` 定义**，本期按坑 2 只留
     触发有效段；预触发仅作 `provenance` 计数，不入 `waveform.tsv`。
- **校验断言**：
  - `assert wave.t[0] == 0.0 and monotonic(wave.t)`
  - `assert provenance.trigger_gate.dropped_head == count(leading bTrigger_Record==0)`
  - `assert segments[0].t0 == 0.0`（保留段首即零点）
  - `assert "pretrigger_head" ∈ provenance.notes`（说明丢弃是语义性的，非错误）

---

## 三、通道语义映射表（厂商名 → C1 规范通道）

C1 词表：`pos_cmd` `pos_fb` `fe` `vel_cmd` `vel_fb` `cur_q` `cur_cmd` `torque` `temp`
`laser_power` `io` `vision_x|y|angle`。下表针对本文件（DARUS-3600 `dXxx` 别名）；
DARUS-5171 的 `x_T` 风格别名列（KB7）在**未在本文件实测**的通道上标 **未核验**。

### 3.1 主映射

| 厂商别名（约定A） | ADS 末段（约定B） | C1 canonical | 单位（实测） | 处置 | 备注 |
|---|---|---|---|---|---|
| `dPosition_test_tar` | `.dPosition_test_tar` | `pos_cmd` | **m** | 直映 | 测试轴指令位置；**非 counts**（见 3.4） |
| `dPosition_test` | `.dPosition_test` | `pos_fb` | **m** | 直映 | 电机轴编码器实际位置 |
| `dVelocity_test_tar` | `.dVelocity_test_tar` | `vel_cmd` | m/s | 直映 | |
| `dVelocity_test` | `.dVelocity_test` | `vel_fb` | m/s | 直映（本身带符号，不乘 dir） | 电机侧速度 |
| `dPosition_asco_enc` | `.dPosition_asco_enc` | `pos_fb`（外部光学编码器） | m | 作交叉验证参考，不入主 `pos_fb` | Micro-Epsilon ASCO（KB7 硬件真值） |
| `dVelocity_asco_enc` | `.dVelocity_asco_enc` | 外部速度（需 dir 乘） | m/s | 交叉验证；`needs_direction_sign` | `catcsv2cell.m` 第 44 行乘 mfw |
| `dPosition_lsv_enc` | `.dPosition_lsv_enc` | 外部电感编码器 | m | 交叉验证 | LSV-2100（KB7） |
| `dVelocity_lsv_enc` | `.dVelocity_lsv_enc` | 外部速度（需 dir 乘） | m/s | 交叉验证；`needs_direction_sign` | 第 45 行乘 mfw |
| `dTorque_test` / `dTorque_load` | `.dTorque_*` | `torque` | Nm（且作者注 **×10 修正**，`catanalyze.m` 第 100-102 行） | 映射但标 `unit="Nm"` 非 `%` | C1 `torque` 定义是「额定%」→ **契约不一致**（§七-3） |
| `dPosition_diff` | `.dPosition_diff` | *绳长守恒残差*（计算列） | m | **不入 `fe`** | 实测 18,651/18,651 行：`≡ -(p_test + p_load)`（行级最大残差 3.55e-15）⟹ **PLC 算出来的列，不是第三套测量**（假朋友，见 3.2） |
| `dVelocity_diff` | `.dVelocity_diff` | *滑移率*（绳速差，计算列） | m/s | **不入 vel 误差** | 实测 18,651/18,651 行：`≡ -(v_test + v_load)`（行级最大残差 4.44e-16），非 `v_cmd - v_fb` |
| `bMovingForward` | `.bMovingForward` | —（方向旗标） | 0/1 | 仅作 dir 乘子输入；**不作为分析通道** | C6/C1 无布尔通道类型（§七-4） |
| `bTrigger_Scope/Record/Export` | `.bTrigger_*` | —（门控旗标） | 0/1 | 仅作触发门控（坑 2）；**不入 waveform** | 同上 |

### 3.2 `fe := pos_cmd - pos_fb` 的推导与符号约定（含自检）

- **定义**：C1 规则 1 —— 若给 `pos_cmd`/`pos_fb` 而无 `fe`，则 `fe := pos_cmd - pos_fb`。
  本数据集无现成跟随误差通道，故 `fe = dPosition_test_tar - dPosition_test`（= `tar - act`）。
- **符号约定风险**：不同厂商对 `fe` 定义相反（`cmd - fb` vs `fb - cmd`）。本数据集按
  `cmd - fb`（`catcsv2cell.m` 全程以 `_tar - act` 计算差值，如 `p_diff_asco = p_asco_enc - p_test`）。
  `meta.channels.fe.sign = +1` 记录该约定；换厂商时符号可能要置 `-1`。
- **自检（若原始自带跟随误差通道）**：C1 要求「用来自检推导方向」。本文件的陷阱是
  `dPosition_diff` **名字像跟随误差、实际不是**：18,651 行全量实测
  `dPosition_diff ≡ -(dPosition_test + dPosition_load)`（行级最大残差 3.55e-15，corr 1.000000；
  `dVelocity_diff ≡ -(v_test + v_load)` 同族，残差 4.44e-16）——
  **它是 PLC 现场算出的列，零独立信息**，物理含义是两绳总长的守恒残差
  （`p_test + p_load` 全程守在 0.12753…0.13541 m，即 7.88 mm 摆动，而两列自身各走 17 m 量级）；
  而 `dPosition_test_tar - dPosition_test` 在 dwelling 段 ≈ 0（row0 两者同为 `18.00204…`）。
  → 自检式子（对任意自带 fe 通道 `fe_raw`）：
  `assert corr(fe_raw, pos_cmd - pos_fb) > 0.99` 才允许把 `fe_raw` 当 `fe`；
  `corr < 0` 说明该厂商定义反了 → 置 `fe.sign = -1`；
  `|corr|` 低（如 `dPosition_diff`）→ **判定 `fe_raw` 不是跟随误差**，改由 `pos_cmd - pos_fb` 派生，
  并把 `dPosition_diff` 归入 `extra_channels`（role=slip_residual）。
  **本样本上这条自检退化**：`pos_cmd ≡ pos_fb`（0/18,651 行有差）⟹ `fe ≡ 0`、方差为零、corr 无定义，
  拒 `dPosition_diff` 当 `fe` 只能靠恒等式与「两绳守恒」这条物理判读，不能靠相关系数（A-104）。
  （以上关系已升级为**全 18,651 行实测**，不再是 row0/row1 抽样；原「未核验」标注于 2026-10-21 清除。）

### 3.3 `vel_fb` 派生的 ×0.7 责任链

- 当只有 `pos_fb`、`vel_fb` 由 `pos_fb` 差分得到时，C1 规则 4：
  `channels.vel_fb.derived = true` 且**频谱类判据置信度 × 0.7**（差分放大噪声）。
- **责任划分（写清是哪条链路）**：
  1. **解析器（KB2）**：负责在只能差分得到 `vel_fb` 时置 `channels.vel_fb.derived = true`。
     本数据集**有** `dVelocity_test` → 直接映 `vel_fb`，`derived = false`，**不触发 ×0.7**。
  2. **C2 特征内核**：读到 `derived == true` 的通道，对一切频域/纹波特征乘 0.7 置信度。
  3. **C3/KB3 规则**：引用这些特征时不得声称满置信；证据 `source.tier` 照 KB0 §4 标注。
  → 即：KB2 只**打标记**，×0.7 的**数值惩罚在 C2**，报告的置信表述在 **C3**。

### 3.4 三套独立位置测量的交叉验证（分歧即证据）

- 三源：电机编码器 `dPosition_test`(=`x_T`型) / 光学 ASCO `dPosition_asco_enc` / 电感 LSV `dPosition_lsv_enc`
  （KB7「三套独立位置测量」）。
- 做法：主 `pos_fb` 取电机编码器；另两源进入 `meta.extra_channels` 但被 `meta.cross_validation` 引用，
  计算残差：`resid_asco = p_asco_enc - p_test`、`resid_lsv = p_lsv_enc - p_test`
  （作者已提供 `p_diff_asco` / `p_diff_lsv`，`catanalyze.m` 第 67-76 行）。
- 分歧本身作证据：残差幅值/漂移 → C2 `sensor_disagreement` 类特征的真实来源（KB7 第 34 行）；
  在绳索执行器上残差=绳滑移/伸长（T1-a 语境），在精密平台上应近零。**不得**把分歧当噪声抹掉。
- **配对的资格线（A-105）**：只有**独立测量**才许进 `cross_validation.pairs`。本文件 8 条位置列里
  独立测量只有 5 条（`test`/`load`/`asco`/`asco_enc`/`lsv_enc`）：`*_tar` 两列与对应反馈**逐行全等**（0/18,651），
  `dPosition_diff ≡ −(test + load)`（残差 3.55e-15）是 PLC 计算列——把它配进"互证"会凭空造出两路假分歧。
- **分歧先减原点（A-106）**：三套测量的**起点不同**（`asco` 从 180.111 m 起、`test` 从 1.000 m 起、
  `asco_enc`/`lsv_enc` 从 0.00 m 起），行程却几乎等长（17.010 / 17.045 / 16.998 / 17.002 / 16.997 m）——
  差的是安装基准，不是被测对象。`corr` 用原始值算（平移不影响它），**幅值必须在去常偏后的残差上算**：
  `asco − asco_enc ∈ [179.562, 180.150] m`（均值 179.813、std 0.270、corr 0.999483）里 179.81 是原点，
  剩下的 0.270 m 才是分歧（`dPosition_asco` 只有 846 个离散值 vs `dPosition_asco_enc` 的 8,760 个，
  量化粗是其主要成因）；对照 `lsv_enc − asco_enc` std 0.0145 m、`test − lsv_enc` std 0.0056 m。
  不减原点，180 m 的"分歧"会把 `sensor_disagreement` 的全部判据淹掉（KB3 该族阈值是 m 级小量）。
- 断言：`assert len(meta.cross_validation.pairs) >= 2`；
  每个 pair 有 `{"a":..,"b":..,"residual_channel":..,"interpret":"slip|disagreement"}`。

### 3.5 单位/counts 纪律（KB0 §5）与本数据集的现实冲突

- KB0 §5 + C1：内部基准单位恒为**编码器 counts**；`counts_per_mm == null` 时报告只印 `[counts]`，
  禁止伪造 µm。
- **实测冲突**：本文件位置通道量级 ~`18.0`、速度 ~`±0.03`、作者图轴 `m`/`m/s`/`N`/`Nm`
  （`main.m` xlabel `$l_d$ /m`、ylabel `$/mm` 由 `*1000` 得来）→ **物理量本就是 SI（m, m/s, N），
  根本不是 counts**。没有 `counts_per_mm`，也没有 count 刻度。
- **处置**：`meta.units_are = "si_native"`；把各通道 `unit` 如实记为 `m`/`m/s`/`N`/`Nm`；
  `counts_per_mm = null`；报告层对 DaRUS 样本印 `[m]` 等真实 SI 单位并注明来自 T1-a 试验台。
  **禁止**把它伪装成 counts 或反推 count 刻度。→ 即 §七-1，**已裁 A-4**（C1 已落 `meta.units_are`）。

### 3.6 映射表未覆盖的通道怎么办（不丢弃、不猜语义）

进入 `extra_channels`（原样保留数值 + 登记，不做语义断言）的有：
`dForce_load` `dForce_test` `dForce_tar` `dForce_diff` `dForce_colinear` `dForce_orthogonal`
（力，N，C1 无 force 通道）、`dPower_load` `dPower_test`（功率，C1 无）、`dRate_asco`（ASCO 计数率）、
`dForceSensorNo`（传感器编号，int）、`dPosition_asco`（光学串行读，与 `dPosition_asco_enc` 近重复，
关系 **未核验**）。

规则：
- 每个未映射通道 → `meta.extra_channels[] = {raw_column, symbol, native_unit_or_null,
  role:"unmapped", confidence:0.0}`，其数值列**原样落 `raw/` 供溯源**，且可选择性写入
  `waveform.tsv` 的扩展列（列名前缀 `x_` 以免与 canonical 混淆）。
- **绝不**猜测语义或塞进近似 canonical 通道（例：不许因为带 `Force` 就映成 `torque`）。
- 断言：`assert N_mapped + N_extra == N`（表头奇数列总数被完整二分）；
  `assert all(c.role in {"mapped","unmapped"} for c in channels)`；无通道既不在 mapped 也不在 extra。

---

## 四、跨品牌适配层需求（接入需求卡）

> JD 提及生态：固高 GTS/GSN/GEN、雷赛 DMC/EMC、正运动 ZMC、软赢、高川、ACS，
> 以及 Beckhoff/CODESYS。**除 Beckhoff Scope View 外，本仓库无已核验导出样本**，
> 故下列卡的「格式细节」列均为**需实测确认的假设**，标注「未核验」，不作为事实断言。
> 卡的目的是把「接入一份新厂商数据前必须先拿到/先确认什么」写成可执行需求。

每张卡字段：`典型导出形态` / `时基（精度、是否等间隔）` / `通道语义差异` / `无法映射的能力` /
`适配优先级` / `适配代价`。`无法映射能力` 是产品主张的一部分，见 §4.8。

### 接入卡模板（九项字段结构）

> **该九项字段结构参考第三方智能体（minimax）《厂商手册索取清单》的工程做法，不是本项目原创**
> （用户定的引用纪律：借用其可执行骨架，须注明出处、不得当作我们自己的发明）。
> 本项目只吸收其**格式**，不采用其任何 SDK 签名作为事实来源（见本节末「事实来源纪律」）。
> 下列九项是 §4.1–§4.9 每张接入卡都应填写的字段模板：

1. **要什么** —— 具体到某个 SDK 函数 / 参数 / 寄存器 / 手册表号（例：`HwPswitch2` 的比较点模式参数、
   某型号 IO 位号↔物理端子对照）。**填写前先判档（A-89 / KB0 §6 检查 21）**：方向位号编码、停止方式编码、
   错误码与停止原因表、某函数是否存在一类，属 **③a 文档可查**——手册或官方绑定里有答案，
   **不得写进本清单向厂商索要**（例：`dmc_vmove` 的正负方向编码原为本项示例，A-89 后撤下，改为"待逐字核对"条目）。
   只有 ③b（随接线盒型号/现场接线/批次固件而定、或属机器安全动作不由 API 决定）才可列入，且须写明"手册为什么答不了"。
2. **为什么必须要** —— 这个字段决定解析/接入结果里的哪一个量；不给会退化成什么。
3. **卡住哪段代码 / 哪个接口** —— 缺它时解析器或 P/Invoke 封装停在哪一步、无法落地。
4. **已核对到哪一步 + 证据等级** —— 明确标注 `external_reference` 档（KB0 §4 阶梯：`memory` / `public-doc` /
   `official-artifact` / `vendor_reply` / 真机）。**未标档的接口断言默认按最低档 `memory` 处理**（A-71 同调）。
   厂商 SDK 签名 / 参数在核出官方工件原文前**一律 `public-doc`**（二手公开资料转录，含**第三方会话的转述**——
   别人读了手册告诉我们，对本仓库仍是 `public-doc`，`verified_by ≠ self` 不计入核对数，A-89/KB0 §6 检查 20），
   **禁止**写「已对照官方手册原文确认」「已核对」。
5. **缺它时的处理方式（显式失败，不猜）** —— 走 §五 拒入或 §三「不猜语义」；绝不以默认值冒充（C1 `drive.*` 纪律），也不「调用待核对函数时静默跑猜值」。
6. **猜错的代价方向** —— 例：点动方向反了 / 撞限位时保护不动作 / 飞拍每片都偏。方向性、安全性的猜测代价高于量值猜测，须单列。
7. **首次上机最小验证动作** —— 一条能在真机或仿真器上把该字段**证伪**的最小操作（如单轴点动 ±、观察限位是否触发）。
8. **SDK 版本与位数** —— 版本号 + x86/x64。**位数不匹配会 `EntryPointNotFound`**（运行时崩溃，而非解析错误），是接入期最常见且最难查的坑。
9. **厂商答复位** —— 留空待 FAE 书面回填；回填并附手册页码后，相应条目方可升格。

> 说明：本项目原有六字段（`典型导出形态 / 时基 / 通道语义差异 / 无法映射能力 / 适配优先级 / 适配代价`）
> 与本九项模板并存——九项偏 **SDK 接入核对**，六字段偏 **波形解析接入**；各卡按适用项填写，
> 签名/参数类条目一律受本模板第 4 项 `public-doc` 纪律约束。

### 4.1 Beckhoff TwinCAT Scope View（**已核验**，本项目基线）

- 典型导出形态：示波器 Scope 导出 CSV（TAB、UTF-8、`(t_ms,value)` 交替、14 行元数据块，§一）。
- 时基：`SampleTime` 声明常值（本例 1 ms / 1000 Hz）；**等间隔**，抖动可测（`probe_cat.py` dt 统计）。
- 通道语义差异：三位置源、方向布尔、触发三重布尔；位置为 SI(m) 非 counts（§3.5）。
- 无法映射：`力/功率/绳滑移残差` 无 C1 对应（入 extra）；**无电流环反馈 `cur_q`**（本数据集无电流通道）。
- 优先级：P0（基线，已实现解析口径）。代价：低（已做完）。
- **证据等级**：`T1-a`（本项目对 DaRUS 真实文件的**直接实测**，§一/§二）。这是全表唯一一档实测证据，
  高于 §4.2–§4.8 的 `public-doc` 二手转录；措辞强度可与该 tier 匹配（A-31 正面案例）。
- **样本级实证卡**：本族的两个实物样本已各自建档——**§4.10**（`Export10_244531.csv`，DARUS-3600 卷筒台架，
  13 行表头变体，**位置目标≡实际 → 无 `fe`**）、**§4.11**（`DD_head.csv`，DARUS-5171 直驱台架的 813 行前缀切片，
  10 行表头变体，**母本有真实 `fe`**）。族级断言与样本级断言冲突时，**以样本卡实测为准**。

### 4.2 CODESYS Scopeview / 视图记录（同生态不同壳）

- 形态：多为 CSV/parquet；表头键值风格可能类似 Scope View 但**字段名不同**。未核验。
- 时基：通常等间隔、可声明周期；需确认是否含触发门控列。未核验。
- 语义差异：变量命名随工程走，需双词表（沿用 §1.2 机制）。
- 无法映射：视工程而定；若工程只记录 `axisPos/axisVel` 则 `fe`/`cur_q` 缺。
- 优先级：P1（复用 Scope View 结构定位器，改词表）。代价：中低。
- **证据等级**：`public-doc`（二手公开资料转录，需手册核对）。本仓库无该厂商手册 PDF / 摘录 / 截图；**禁止**写「官方手册原文确认」「已核对」这类越级措辞。
- **要升格需要什么**：厂商手册 PDF 的具体页码/表号 + 存证文件路径（入包内 `raw/` 或 `docs/evidence/`）+ 厂商 FAE 书面确认；三者齐备前，本卡签名/参数条目一律维持 `public-doc`。

### 4.3 固高 GTS / GSN / GEN（控制卡，运动 API 为主）

- 形态：**多为逻辑分析仪/示波器式采样导出** 或 自研 txt/binary dump；亦常见「只有报警码/状态字」而无波形。具体导出扩展名未核验。
- 时基：卡内缓冲区采样，常见等间隔但**周期需实测**；GTS 的采样时钟抖动需按 §二坑 1/4 度量。未核验。
- 语义差异：位置多为**编码器脉冲计数（真 counts）**，与 DaRUS 的 SI(m) 相反 → `counts_per_mm` 若给定则可换算；跟随误差多为独立通道。
- 无法映射：低端型号可能**无 `cur_q`/无速度反馈**，仅有位置与报警 → 触发 §五「cur_q/vel_fb/fe 全缺」拒入。
- 优先级：P1（JD 点名，国产主力卡）。代价：中高（格式未核验、可能是二进制）。
- **证据等级**：`public-doc`（二手公开资料转录，需手册核对）。本仓库无该厂商手册 PDF / 摘录 / 截图；「多为真 counts」「跟随误差为独立通道」等签名/参数断言**不得**写成「官方手册原文确认」「已核对」。
- **要升格需要什么**：厂商手册 PDF 的具体页码/表号 + 存证文件路径（`raw/` 或 `docs/evidence/`）+ 厂商 FAE 书面确认；三者齐备前维持 `public-doc`。

### 4.4 雷赛 DMC / EMC

- 形态：控制卡；示波器功能弱，多为「寄存器快照 / 自研 txt 日志」，非标准波形 CSV。未核验。
- 时基：手动/轮询采样 → **很可能不等间隔**，`dt_jitter_ratio` 高风险超 0.2（§五红线）。未核验。
- 语义差异：脉冲当量给位置，`counts_per_mm` 常可得；跟随误差寄存器可读。
- 无法映射：**大概率无高速波形**（只有低频轮询位置/报警码）→ 很多工况直接落 §五「无动态分段/样本不足」。
- 优先级：P2。代价：高（时基不稳 + 可能无连续波形）。
- **证据等级**：`public-doc`（二手公开资料转录，需手册核对）。本仓库无该厂商手册 PDF / 摘录 / 截图；「脉冲当量给位置」「跟随误差寄存器可读」等签名/参数条目一律 `public-doc`，**禁止**「官方手册原文确认」「已核对」。
- **要升格需要什么**：厂商手册 PDF 的具体页码/表号 + 存证文件路径（`raw/` 或 `docs/evidence/`）+ 厂商 FAE 书面确认；三者齐备前维持 `public-doc`。

### 4.5 正运动 ZMC

- 形态：ZMC 控制器 + 上位软件；可能有示波器导出 CSV/日志。未核验。
- 时基：插补周期相关，等间隔性未核验。
- 语义差异：位置单位（counts/当量）与跟随误差定义需实测确认符号（§3.2 自检）。
- 无法映射：电流环反馈是否可见未核验。
- 优先级：P2。代价：中高。
- **证据等级**：`public-doc`（二手公开资料转录，需手册核对）。本仓库无该厂商手册 PDF / 摘录 / 截图；单位/符号、跟随误差定义等签名/参数条目一律 `public-doc`，**禁止**「官方手册原文确认」「已核对」。
- **要升格需要什么**：厂商手册 PDF 的具体页码/表号 + 存证文件路径（`raw/` 或 `docs/evidence/`）+ 厂商 FAE 书面确认；三者齐备前维持 `public-doc`。

### 4.6 软赢（未核验，信息不足）

- 本仓库无该厂商任何样本，且其导出形态**未核验**。接入前必须先索取：一份真实导出样例 + 通道清单 + 时基文档。
- 在拿到样例前，**不写任何格式断言**（遵守硬约束 #2）。
- 优先级：P3（样例缺失）。代价：未知（需先做样例外呼）。
- **证据等级**：无（样例缺失，本卡**未做任何**签名/参数断言；不得凭空写「已核对」「官方手册」）。一旦依据公开资料形成对照条目，即刻记为 `public-doc` 并署名。
- **要升格需要什么**：先索取真实样例 + 通道清单 + 时基文档；此后仍需厂商手册 PDF 页码/表号 + 存证路径 + FAE 书面确认，方可升格。

### 4.7 高川（未核验，信息不足）

- 同软赢：无样本、导出形态未核验。仅登记为适配层「待接入槽位」，需样例外呼后才能评估。
- 优先级：P3。代价：未知。
- **证据等级**：无（样例缺失，本卡**未做任何**签名/参数断言；不得写「已核对」「官方手册」）。一旦依据公开资料形成对照条目，即刻记为 `public-doc` 并署名。
- **要升格需要什么**：先索取真实样例 + 通道清单 + 时基文档；此后仍需厂商手册 PDF 页码/表号 + 存证路径 + FAE 书面确认，方可升格。

### 4.8 ACS（高端运动控制，SPB/ACSMotion）

- 形态：ACS 常有较完善的示波器/`s` 变量连续采样导出（如 `.csv`/二进制 trace），但**本仓库未核验**。
- 时基：通常支持高采样率（可能远超 1 kHz）→ 对 §二坑 1 反而是**好消息**（能评估 kHz 共振），但需实测确认真实 `fs`，不得假设。
- 语义差异：`s` 变量命名（`s1`…`s80`）需映射词表；跟随误差/电流原生可见性未核验。
- 无法映射：若用户只导出报警/状态而非 trace → 无波形（§五）。
- 优先级：P1（JD 点名、且可能补上 kHz 频段空白）。代价：中（格式未核验但生态规范）。
- **证据等级**：`public-doc`（二手公开资料转录，需手册核对）。「支持高采样率（可能远超 1 kHz）」「`s` 变量命名映射」等签名/参数条目一律 `public-doc`；**禁止**「官方手册原文确认」「已核对」，真实 `fs` 须实测确认不得假设（§二坑 1）。
- **要升格需要什么**：厂商手册 PDF 的具体页码/表号 + 存证文件路径（`raw/` 或 `docs/evidence/`）+ 厂商 FAE 书面确认；三者齐备前维持 `public-doc`。

### 4.9 诚实主张：「不可映射项清单」就是卖点（对齐 C5 §8）

- 适配层**不承诺一切都能标准化**。把每个来源的「无法映射能力」固化成一张**跨厂商能力矩阵**
  （C5 §8 兜底方向），逐格标注 `可映射 / 需换算 / 不可映射(原因)`。
- 核心卖点是**不可映射项清单**：只有报警码没有波形、没有电流环反馈（`cur_q`）、只有位置无速度、
  时基不等间隔（雷赛轮询型风险）、SI-vs-counts 单位现实（本数据集）等——
  诚实标注「这类数据本就无法下这类结论」，比假装能诊断更有价值，也是 §五 拒答正确率的输入。
- 断言：`assert capability_matrix covers all §4.x`；每格 `status ∈ {mapped, convertible, not_mappable}`；
  `not_mappable` 格必须带 `reason` 与「缺什么数据能救」。

### 4.10 样本级接入卡 · `raw/Export10_244531.csv`（DaRUS **DARUS-3600**，dataFile 244531）

> 本卡与 §4.1–§4.8 的**厂商族**卡不同层级：它是**单个样本文件**的接入结论，用来给族卡（§4.1）
> 供实证。族卡讲「这类导出长什么样」，本卡讲「我们手上这一份能支撑哪些断言、不能支撑哪些」。
> 全部数字为 2026-10-20 本会话对本地实体文件与 DaRUS 现场 API 的**直接实测**（`python data/validate_raw.py`），
> 不是任何第三方会话的转述。sidecar：`raw/Export10_244531.csv.source.txt`（v2 模板四项齐备）。

- **典型导出形态**：TwinCAT 3 Scope 导出 CSV；TAB / UTF-8 / CRLF / 无 BOM；
  `(t_idx, value)` 交替 **64 列 = 32 通道**；**表头 13 行**，数据自第 14 行起；尾部 1 行列数与主形状不符（已按 §二坑 4 计 `n_rows_shape_mismatch`）。
  本变体的元数据行为 `Name / SampleTime[ms] / SymbolBased / SymbolName / NetID / Port`（ADS 符号路径 + 路由信息齐备）。
- **时基**：`SampleTime[ms]=1` → fs 实测 **1000.0 Hz**，`dt_jitter_ratio=0.000`，严格单调，
  时长 **18.650 s**，与墙钟（`Starttime/Endtime` 之差）比值 **1.0000** —— 两把独立的尺子对得上，
  故本样本的 t_i 可进 C2 频谱类判据；奈奎斯特 **500 Hz**（§二坑 1，kHz 共振频段仍不可评估）。
- **通道语义差异（实测，非页面描述）**：
  - **位置目标 ≡ 位置实际**：`dPosition_load ≡ dPosition_load_tar`、`dPosition_test ≡ dPosition_test_tar`
    —— 逐行比对 **0/18,651 行有差异** ⟹ **本样本给不出位置跟随误差 `fe`**，
    且 `dPosition_diff` 也不是 `fe`——它 **逐行恒等于** `-(dPosition_test + dPosition_load)`
    （行级最大残差 3.55e-15，corr 1.000000；`dVelocity_diff ≡ -(v_test+v_load)`，残差 4.44e-16）
    ⟹ **`*_diff` 是 PLC 现场计算列，不是第三套测量**，不得进交叉验证证据链（A-104 / A-105）。
    **§3.2 的 `fe := pos_cmd - pos_fb` 在本样本上不可派生**，解析器不得由 `_tar` 列名反推出「有指令轨」。
    > **2026-10-21 更正（本卡自我证伪）**：本卡原写「恒等式残差/幅度 = 100% 已实测证伪」，
    > 任务台账另记 `dPosition_diff ∈ −0.133…−0.128 m` 而恒等式右端 `−0.035…−28.343 m`、`corr = −0.9809`。
    > 复测三条**全部不成立**：右端实测就是 `−0.13541…−0.12753 m`（与左端同一条曲线），
    > corr = +1.000000；`−0.035…−28.343` 与 `−0.9809` 在本仓任何现存产物与两份 DaRUS 样本上都不可复现
    > （穷举 8 条位置列的全部 28 个配对：没有任何 `-(a+b)` 落在 `[−28.343, −0.035]`，
    > 最近的是 `-(asco_enc + lsv_enc) ∈ [−34.039, 0.003]`；与 `dPosition_diff` 的 corr 最负只到 −0.9624，
    > 来源是 `-(load + load_tar)`——同一物理列重复计数，不是恒等式右端）。
    > ⟹ 原结论方向反了：恒等式不是「差两个量级」，而是**精确成立到浮点舍入**（残差 3.55e-15）。
    > 复现命令：`PYTHONPATH=src python data/probe_diff_identity.py`。
  - **速度目标 ≠ 速度实际**：`dVelocity_load` vs `_tar` 差 **9,397/18,651** 行（峰值 0.0585）、
    `dVelocity_test` vs `_tar` 差 **17,442/18,651** 行（峰值 0.1270）⟹ 速度环跟踪误差**真实存在**，本样本可撑 `vel_err` 类判据。
  - **力目标 ≠ 力实际**：`dForce_load` vs `dForce_tar` **18,651/18,651 全行有差**（峰值 97.5）⟹ 力控工况。
  - 三套位置测量互不一致：`dPosition_asco_enc` vs `dPosition_asco` 全行不等（峰值 180.15）→ 按 §3.4 作交叉验证输入，**分歧即证据**，不得择一当真理。
  - 恒值/枚举列已识别：`dForceSensorNo`、`bMovingForward`、`bTrigger_Scope`、`dForce_tar` 恒值；
    `bTrigger_Record/Export` 为 0/1 枚举（§二坑 2/5 的触发门控在此样本上无截断）。
- **无法映射的能力**：**无任何电流通道**（`cur_q` 缺）→ 共振/摩擦的电流主通道判据一律软降级（§5.2）；
  力/功率/绳滑残差无 C1 对应 → 入 `extra_channels`（§二坑 6）；无 `events.jsonl` → §5.4 连带拒答。
- **适配优先级 / 代价**：P0 已完成（族卡 §4.1 的解析口径即以本文件建立）。本卡的净收益是**把「能撑什么」写到通道级**：
  可用于速度/力跟踪与多传感器交叉验证的回归；**不可**用于位置跟随误差类诊断。
- **证据等级**：`T1-a` + `official-artifact`，`verified_by = self`。
  母本身份为现场取证：`GET /api/access/datafile/244531` 落盘 md5 `8cba13dfae7d1a3cdf48d3e20851dadb`
  与发布方登记一致；`rows/channels/fs_hz/hash` 四条自述 **4/4 与实体核过，证伪 0**。
  许可 CC BY 4.0，署名 Reichenbach, Thomas — University of Stuttgart，DOI `10.18419/DARUS-3600`。
- **发布前必做**：计数由 `python data/probe_pii.py` 打印（口径=**正则命中次数**，不是行数也不是文件数；
  KB0 §6 检查 27 要求文档抄打印行）。本文件实测：`Versuchsstand` **1**（第 2 行 `File` 的原机绝对路径）、
  `NetID` **32** 与内网地址（`141.58.` 网段）**32**（集中在第 11 元数据行的重复标签对）、`C:` + 反斜杠 **1**。
  两个 `.source.txt` 侧车各再带 1 次 `Versuchsstand` ⟹ `data/raw` 合计 `Versuchsstand` **4**、盘符路径 **3**，
  脱敏范围必须含侧车。此前此行的 `NetID（×6）`/`Versuchsstand（×9）` 是人工点数、在本仓任何一份样本上
  都不可复现，已撤销（A-110）。引擎产物 `build/Export10_244531/` 实测 `Versuchsstand` **0**、IP **0**、
  盘符路径 **0**；那里的 4 次 `NetID` 命中全部是本仓**关于脱敏的叙述文字**（"ADS NetID"），不是标识值。
- **不得由本样本得出的断言**：线缆试验台 ≠ 半导体产线；本仓无该设备现场/产线验证，叙述措辞不得高于 `T1-a 实测`。

### 4.11 样本级接入卡 · `raw/DD_head.csv`（DaRUS **DARUS-5171** dataFile 394008 的前缀切片）

> 2026-10-20 本会话把这份文件从「来源未登记」**升级为母本确立**，同时**纠正同日早先的一次错误结论**
> （曾判「两个 DaRUS 库查无此文件」——用整文件 md5/filesize 去匹配一个前缀切片，方法上不可能命中；
> 纠正记录见 `data/VERIFICATION-2026-10-20.md` 第六节）。

- **典型导出形态**：同族 TwinCAT Scope View，但**表头只 10 行**，元数据行为
  `Name / Data-Type(REAL64) / SampleTime[ms]`，**无 `SymbolBased / SymbolName / NetID / Port`**
  —— 这是 §1.4「表头行数不许硬编码」的第二个实测变体，也是 §一 表格里原先标「未核验」的
  `Data-Type<TAB>REAL64` 假设，**现已核验**（族卡措辞可升格）。
  交替 **80 列 = 40 通道**，通道名族为 `x_T / x_Ttar / f_kistler1 / tau_L / theta_T …`（与 3600 的 `dXxx_…` 族不同名）
  → §1.2「双词表」由**假设**升为**两族实物**。
- **它是什么**：母本 `Export 10.csv`（`CableDirectDrive_Testbed/2024-07-23_LdaFricIdent/Data/RW/`，43,700,198 B）
  的**前 400,001 字节逐字节前缀**（本会话 Range 取回母本后逐字节比对确认，非仅比哈希）；
  同目录同名候选 394122（`Data/UW/`）在第 156 字节即分歧，已排除。
- **时基**：`SampleTime[ms]=1` → fs 实测 **1000.0 Hz**，抖动 **0.000**，严格单调，但切片内时长仅 **0.812 s / 813 行**。
- **红线判定**：**硬拒**（KB2 §5.1 硬拒 1，`n_samples=813 < 2000`）。
  用途因此被限死：只可用于**表头结构定位、词表族对照、解析器回归**；
  **不可**据此文件下任何诊断断言，也不可用于「厂商格式代表性」（A-88：切片自身哈希与本地派生同源，不计入 k）。
- **通道语义差异（在母本全量上实测，非切片）**：`x_T` vs `x_Ttar` 差 **64,284/75,858** 行（84.7%，峰值 1.6 mm，RMS 35 µm）、
  `v_T` vs `v_Ttar` 差 99.8% 行 → **直驱台架是有真实跟踪误差的**，与 §4.10 的 3600 卷筒样本形成互补；
  但 `x_diff` **不是** `fe`——母本上实测 `x_diff ≡ (-x_L) - x_T`（逐行残差 mean=0、std=0），
  与 3600 的 `*_diff` 同一性质（基准间量，不是指令-实际差）。切片里 `f_tar / x_Ltar / dir / f_no` 等恒值，
  813 行不足以判定母本的动态段。
- **无法映射的能力**：无电流通道（`tau_L/tau_T` 是力矩量，单位未标定）；逐通道物理单位**发布方未提供**
  → 数值可算、量纲不可断言（KB0 §5 单位纪律）；无 `events.jsonl`。
- **适配优先级 / 代价**：P1，代价低——**要用的话接母本而不是切片**（母本 43.7 MB，`GET /api/access/datafile/394008`，
  本会话已现场核得 md5 `62326eb83e0d31396c1d0d422254b5fe` 与发布方登记一致；副本暂存 `data/incoming/`）。
- **证据等级**：切片内容 `T1-a 实测`；母本身份 `official-artifact`，`verified_by = self`；
  自述核对 **3/4 计入 k**（rows/channels/fs 相符；哈希按同源派生剔除）。
  许可 CC BY 4.0（本会话读 5171 `latestVersion.license`），署名 Reichenbach, Thomas — University of Stuttgart，DOI `10.18419/DARUS-5171`。
- **发布前必做**：同一脚本实测本文件 `Versuchsstand` **1**（`File` 行）、`C:` + 反斜杠 **1**、
  `NetID`/`141.58.` 网段 **0** ⟹ 本变体**不含 ADS 路由标识**，与 §4.10 的脱敏清单不同，勿照抄。
  侧车 `DD_head.csv.source.txt` 另带 `Versuchsstand` **1**，脱敏须一并处理。
  此前此行的 `Versuchsstand（×3）` 是人工点数、不可复现，已撤销（A-110）。

### 4.12 未接入样本卡 · ScienceDB 机器人关节电机位置（`data/staging/`，**接入前置未满足**）

> 本卡**不是**接入卡：按 §3.6 的"不丢弃、不猜语义"与 §5.1 红线 6，这 12 个文件当前**不得**进 `data/raw/`。
> 逐项实测数字见 KB7「B 组台账」与 `data/VERIFICATION-2026-10-20.md` 第八节（`verified_by = self`）。

- **上游**：`doi:10.57760/sciencedb.04148`（Science Data Bank；本会话 DataCite REST 现场核过
  标题/publisher/年份/V1/`cc-by-4.0`/三位创作者/摘要/主题词）；署名 Huayuan Huang（含 USTC）、
  Hongtao Pan、Cheng Yong（Institute of Plasma Physics, Hefei Institutes of Physical Science）。
  **不得**并入 Reichenbach / Stuttgart 一行。母包 50,493,558 B 已按字节重抓、6 个 `.mat` 成员逐字节一致。
- **形态**：MATLAB v5 `.mat`（`Platform: PCWIN64`），每文件 11 个变量（`tout` + 10 数据列）；
  另有本地派生的同名 CSV（表头 11 列，与 `.mat` 逐行 max|Δ| = 5.0e-8）。
  → **CSV 是派生件，接入应引 `.mat`**（§3.6 同源派生不计入独立核对 k）。
- **时基**：`dt` 恒 `0.002 s` ⟹ `fs = 500.000 Hz`；`dt_jitter_ratio` 实测 7.6e-12 / 4.5e-12，严格单调；
  时长 400.000 s（周期，200,001 行）/ 200.000 s（点位，100,001 行）。⟹ §5.1 硬拒 1–5 **全过**。
- **能力矩阵（§4.9 口径）**：

  | 能力 | status | reason / 缺什么数据能救 |
  |---|---|---|
  | 位置命令 `pos_cmd` | `not_mappable` | 列名族 `q / theta` 未经上游定义裁定，不得按命名指定 |
  | 位置反馈 `pos_fb` | `not_mappable` | 同上；实测 `j1_etheta_pos` 量程（−3.4e-3…0.400）与 `theta1`（−6.7e-7…0.599）**不同**，不支持当 `pos_fb` |
  | 跟随误差 `fe` | `not_mappable` | 候选恒等式在 6 个文件间**不自洽**（残差 B1 3.0e-1…4.0e-1 vs B2–B6 2.0e-3…5.9e-3）；缺**上游逐列定义** |
  | 速度反馈 `vel_fb` | `not_mappable` | 无速度语义列名；`j*_qd` 是否速度**未实测** |
  | 电流 `cur_q` | `not_mappable(数据中确无)` | 电流七类词零命中——这一格是**缺席**（可证），非词表缺口 |

- **频带**：`reliable_band_hz = 500/1.25 = 400 Hz` < `band⊥ = 2000 Hz` ⟹ R-03/R-04 走 `unavailable`
  （A-94 的**样本级**判定，不是数据集级）。
- **接入前置条件（两条，缺一不可）**：
  1. **上游逐列定义文档**（`q / theta / qd / eq / etheta` 各是什么、单位是什么）——
     这是把 `fe` 从"待人工复判"升为"真 fe"的**唯一**依据，更多数值复算解决不了；
  2. **词表补全（R-4）**——但词表只能登记"这列进入了 `extra_channels`"，**不能**代替第 1 条来指定角色。
- **归属纪律**：这是**机器人关节轨迹实验**，不是半导体产线数据；对外叙述不得包装成封装设备现场数据。

**解析器待办（R-4 仍开放；R-5 / R-3 于 2026-10-21 随任务 #15 修，同日复算追加并修 R-6 / R-7；四条合并登记为 KB0 A-112）**：
- **R-4 机器人学命名族**（`tout / q / theta / qd / eq / etheta`）：先按 §3.6 全部落
  `extra_channels{role:"unmapped", confidence:0.0}`，**角色待上游定义裁定后再映射**。
  ⚠ 本轮已实测证明"按名字猜"会猜错：`validate_raw.py` 的词表把 `j1_etheta_pos` 映成 `pos_fb`，
  而实测量程对不上 ⟹ 词表不得把"名字像误差"当成"就是误差"。
  **R-5 修后追加三族实测（同一条缺口的不同书写）**：`Rate_asco` / `dRate_asco`（Export10 第 28 列）
  落 unmapped——裸 "rate" 已从 vel 整词表**剔除**（留着则 `FailureRate` 的整词 "rate" 照样命中，
  token 化也分不开），而引擎侧 `mapping.py` 仍把 `dRate_asco` 登记为 `vel`「速率（ASCO 侧，单位存疑）」，
  **与本卡 §3.1 那句「ASCO 计数率」互斥 ⟹ 待人工复判**，两侧不得各说一套；
  `PMU_SegArb_ExampleB` / `VMeasCh*` / `IMeasCh*`（参数分析仪件 10/10 列 unmapped）同属命名族缺口，
  其中 `IMeasCh1` 实测量级 0.00225 是**电流**、旧子串口径与新 token 口径都没认出来。
- **R-5 `rate` / `amp` 子串误报 —— 已修（2026-10-21，任务 #15）**：原句的三处误报
  （`OilLevel_L → vel_fb`、`FailureRate → vel_fb`、`Timestamp → cur_other`）改为**整词 token 判定**后
  实测均为 `(None, None, False)`（未映射）。修法就是原句要求的 token 化，复用与 `name_tokens`
  **同一份** `split_name_tokens`，**没有再加正则补丁**。
  ⚠ **改名一处（A-54 单一名字律）**：该猜测器原名 `channel_role`，与
  `src/axiscope/mapping.py::channel_role`（审计**之后**回答"canonical 还是 extra"、返回字符串）
  **同名不同物**——本函数在审计**之前**按列名猜量名/方向、返回三元组。现已改名 **`guess_role_from_name`**，
  引擎侧那一名不动；两处各带对比注释，读代码的人不会再拿错那一份。
- **R-3 ISO-8601 文本时间列 —— 已修（同一批）**：6114 两 CSV 的 `t` 列是 ISO 文本，此前 `fnum` 全判 NaN
  ⟹ 无时间列可解析 ⟹ 被「时基非严格单调」**误拒**。修法只补**解析**（`iso_epoch()` 转 epoch 秒，
  裸时间按 UTC；单调性/抖动门槛原样作用于差分序列，不放松）。复算实测（`build/validate_incoming_after_r7.txt`）：
  `6114_lsmc.csv` **accept**（fs 1000.1 Hz、抖动 0.000、时长 2.999 s、3,000 行、51 列、六条全过）、
  `6114_x_velSweep_s0_n150_dir_pos.csv` **accept**（同 fs、时长 10.999 s、11,000 行）、
  `current-hunt/3900_const_vel_110.tab` **accept**（fs 1000.1 Hz、抖动 0.038、时长 2.702 s、2,701 行、41 列、
  sidecar ABSENT）。⟹ **这批"被拒"是解析器缺陷而非数据缺陷**，KB7 台账 15/16 行的「过」才是对的。
- **R-6 小数逗号布局 —— 已修（2026-10-21 主线程复算 KB7 台账 20 行时发现）**：
  `2563_LDD_Transfer_function_Force_controlled.csv` 是 `;` 分隔 + `,` 作小数点
  （`0,000000;19,999996;-20,172794`）。取值路径 `fnum` **一直**认逗号小数，缺的只是**布局判定**
  （`is_num` 只认点十进制）⟹ 整份判 `layout=unparsed`，台账那句「时长 0.128 s」因此**没有工具载体**。
  补 `sniff_decimal_comma()`（逗号小数够多**且**点小数/整数不占多数才算，防千分位误判）后实测：
  2,047 数据行、fs 16,000 Hz、抖动 0.000、时长 0.127875 s、单位来源 `column_name:ms`、
  红线开火「有效时长<0.5s (实测 0.1279s)」+「cur_q/vel_fb/fe 未识别（2/2 列未映射）」⟹ **verdict 仍是 reject**，
  与台账口径一致；`data/raw` 全量切片六件的 `小数逗号` 一律 `False`、accept/reject 计数一字未动（无回归）。
- **R-7「无时间列」被写成「时基非严格单调」 —— 已修（同一批）**：`redlines()` 此前只看
  `strictly_monotonic` 缺省 `False`，于是**没有时基**的文件会得到一条**单调性不合格**的拒因；
  而列名/ISO 形态都认不出时，解析器还会退化成"抓第一个前 50 点递增的数值列"当时间列——
  该列整体不单调时，报的就是"某个数值通道不单调"，而不是"没有可用的时基列"。
  C1 §`time_bases` 第 ⑤ 条对 `role == "event"` 栅格**明令禁止**这种写法，检查 22 要求拒因指向实测缺陷。
  现在时基列带 `time_col_source` 出处（`format_family:twincat` / `column_name` / `iso8601_content` /
  `monotonic_heuristic`），两种形态分别判：`无时间列可解析（时基不可得，不作单调性结论）` 与
  `无时间列可解析（列名/ISO 形态均不识别，递增启发列不成立）`，启发列不单调时**不再**叠加抖动红线。
  复算：`6114_ObserverTestSet.tab`（真无时间列）现在打印「时基：无时间列…」+ 该拒因，
  与 KB7 台账 17 行的「不可实测（无时间列）」对齐；**verdict 不变**（仍 reject）。

**★ 连带发现：§3.6 的"不丢弃"断言此前没有实现，工具因此丢过一列。**
§3.6 与 §8.3 早已写死 `assert N_mapped + N_extra == N_header and no channel unmapped-and-dropped`，
但 `data/validate_raw.py` 未实现该断言，且 `parse_table()` 的 plain_matrix 分支
**用 `names[n]` 取通道名而 `n` 是剔除时间列后的 `val_cols` 下标** ⟹ 名实错位一列且**末列被静悄悄丢弃**
（4 列文件只报 3 个通道）。本轮已修（按列号取名）并补**负向回归断言**（时间列在首位时不错位、不丢列）。
`--selftest` 现打印 **29 通过 / 29 执行 / 0 失败**（22 → 26 随 R-5/R-3，26 → 29 随 R-6 的 accept 用例
与 R-7 的两条形态断言；汇总数由脚本自数，检查 27）。
⟹ 教训登记：**契约里的断言必须落到工具里并有负向测试**，否则"规范已写"不等于"行为已守"（KB0 §6 检查 22/23）。

### 事实来源纪律（A-32 / A-31 / A-33）

> 本节是 §四 全表的**证据 tier 权威约束**，落盘依据见 `docs/AUDIT-minimax-round3.md` 与 KB0 §7 A-31/A-32/A-33。

1. **不把第三方转录的 SDK 签名当我们的事实来源（A-32）**。外部智能体（minimax 三轮）的 C#/Python 适配器把
   P/Invoke 签名做成了「二手网络转录」——其仓库内**当时没有任何厂商手册 PDF、摘录或截图**，来源字段只有两条
   CSDN 链接，自己的知识 JSON 仍有 62 处标 `verified: "public-doc"`、README 仍建议人工复核。
   因此 KB2 §4 **不得**以其签名作为 source of truth；至多作为「二手转录，需手册核对」的**线索**引用并署名。
   **状态更正（A-89）**：该会话第四轮已取得官方手册与官方 SDK 绑定，并把绑定源文件抽取成函数清单
   （它称正运动 402 / 雷赛 1391 个函数），据此抓出三个真机即崩缺陷（`ZAux_*` 的 DLL 归属指错、
   `ZAux_Direct_SetAxisParam` 与 `dmc_set_home_profile` **官方根本不存在**）。⟹ 上面"其仓库内没有任何厂商工件"
   这句**对它已过期**，本 KB 引用它时必须带上这一轮的时点；但**对本仓库仍成立**——那些手册与绑定不在我们的
   `data/raw/` 或 `docs/evidence/` 里，所以它的核对结论对我们**只是 `public-doc`**（`verified_by = third_party_report`，
   不计入 `k`），我们不得借它把自己的措辞升到"已按手册核对"。
2. **公开资料形成的对照表一律 `public-doc`**。§4.2–§4.8 所有签名/参数条目的证据等级即此，见各卡「证据等级」行。
3. **对外可转发的口径是「我们按公开资料形成了下表，请厂商指出不符项」，而不是「已确认」**。
   把「已对照官方手册」这类措辞发给 FAE，一旦对方翻出手册发现某条不符（如 `HwPswitch2` 的模式参数口径），
   损失的是整份清单的可信度（`AUDIT-minimax-round3.md` §二）。
4. **叙述强度不得高于数据层 tier（A-31 / C3 硬性规则 14）**。§一/§二 的 Beckhoff 14 行头结构与 5 个实测陷阱
   是**本项目自己实测（T1-a）**，可用强措辞；§4.2–§4.8 的 `public-doc` 二手转录只能用弱措辞。这正是 A-31
   所记外部失效案例的反面——数据层诚实定级与叙述层强措辞并存，会让审计者读到「已对照官方手册」就停止怀疑。
5. **六个软件诱导缺陷形态的引用口径（A-33）**：DPOS 冒充反馈、`_unit` 双重换算（已是 mm 再除以当量必差 1000 倍）、
   IO 电平当错误码、PSO 比较点口径、回零后 MPOS 未同步、锁存源选错——这些**缺陷形态**成立不依赖手册哪一版，
   属逻辑自洽的失败模式；但一律表述为「**第三方实现审计中出现的缺陷形态**」，
   **禁止**写「手册确认的错误」或「我们的发现」。
6. **抽取式核对优先于手读（A-89 / KB3 §0 纪律 16 ④）**。凡厂商工件或数据集原始文件里**可机器抽取**的字段
   （函数名是否存在、DLL 归属、参数个数、CSV 列名与列序、XML 属性有无单位），一律由抽取脚本重生成后再写入本表，
   **禁止凭记忆书写**；抽取未覆盖的行标 `unverified_signature`。本仓库现成可抽取的工件就在 `data/raw/`
   （`CableActuatorTestbed.xml`、`catanalyze.m`、`darus3600.json`、`darus5171.json`）——§一/§二 那 14 行头结构与
   5 个实测陷阱应当由脚本产出而不再依赖人眼读一次（A-78 那次"把 `32` 写成 `Nm`"正是手读的产物）。
7. **"要升格需要什么"按 A-89 拆两路**（本节各卡原写的"手册页码 + 存证路径 + FAE 书面确认**三者齐备**"由此收窄）：
   - **接口事实类（③a：函数存在性、DLL 归属、参数个数、方向/停止方式编码、错误码表）**
     ⟹ 只需 `official-artifact`：工件存证进 `raw/` 或 `docs/evidence/` + `clause` + `verified_by = self`，
     **不必等厂商回信**；
   - **现场/批次类（③b：IO 位号↔端子、SERVO ON 归属、编码器是否并接、从站 PDO/ESI、SDK↔固件矩阵、位数）**
     ⟹ 才需要 `vendor_reply`（书面答复 + 日期 + 适用型号，注明不跨批次套用）。
   两类都不升 `basis`（C3 规则 4 三值与 `external_reference` 正交，KB0 §4）。

---

## 五、拒入清单与错误输出契约

C1「数据质量红线」→ 解析器端**可判定检查**。红线**按过滤后（坑 2）的有效行**评估。
每条规定「拒绝时返回什么」：缺什么 / 为什么这些不足以下结论 / 补什么数据能救。
这是 C5「拒答正确率 ≥80%」的落地位置——正确拒答比多给一个结论更有价值。

### 5.1 红线 → 判定

| 红线（C1） | 判定式（解析器端） | 类型 |
|---|---|---|
| `n_samples < 2000` | `n_filtered < 2000`（过滤+去坏行后） | 硬拒 |
| 有效时长 `< 0.5 s` | `t[-1] - t[0] < 0.5` | 硬拒 |
| `dt_jitter_ratio > 0.2` | `std(dt)/median(dt) > 0.2`（dt 由 col0 差分） | 硬拒 |
| `nan_ratio > 0.05` | 纳入网格中 nan 占比 > 0.05 | 硬拒 |
| 无动态分段 | 无任何 `move/settling/probing` 段（全 `rest/dwell`） | 硬拒 |
| `cur_q`/`vel_fb`/`fe` 全缺 | `not any(c in present for c in {cur_q,vel_fb,fe})` | 硬拒 |

### 5.2 硬拒 vs 软降级（不要过度拒入）

- **硬拒**（整样本 `insufficient_data`）：上面六条红线任一命中。
- **软降级**（样本可用但某判据 `unavailable/unverified`，**不整包拒**）：
  - 只有 `fe`+`pos_fb` 缺 `pos_cmd` → C1 规则 2 派生 `pos_cmd`，运动学特征不降级。
  - 只有 `fe` → C1 规则 3：`move` 段超调/稳定时间标 `unavailable`，但纹波/稳态判据仍可跑。
  - `drive.*` 缺字段 → 依赖该字段的规则降 `unverified`（C1 明文），**不用默认值冒充**。
  - `fe` 存在但 `cur_q` 缺 → 共振主通道弱，`freq` 类判据降级并提示需电流通道。

### 5.3 错误输出契约（`insufficient_data` 信封，伪 JSON）

```json
{
  "status": "insufficient_data",
  "sample_ref": "<redacted original_filename>",
  "violated_redlines": ["dt_jitter_ratio>0.2", "cur_q_missing_and_only_fe"],
  "measured": {
    "n_file_rows": 18650, "n_after_trigger_gate": 5003, "trigger_record_ratio": 0.268,
    "dt_median_ms": 1.0, "dt_jitter_ratio": 0.31, "nan_ratio": 0.012,
    "present_channels": ["pos_cmd","pos_fb","fe","vel_cmd","vel_fb"],
    "missing_critical": ["cur_q"],
    "segments": {"n_move": 0, "n_settling": 0, "note": "全程 dwelling"}
  },
  "why_not_conclusive": {
    "dt_jitter_ratio>0.2": "时基不稳→频谱峰位置不可信，任何频率类判据（含纹波、共振）都不能下结论",
    "no_move_segment": "无动态段→无法区分静态偏差与动态跟随误差，C1 要求几乎所有判据带运动语境",
    "cur_q_missing": "无电流环反馈→机械共振与电气纹波的主通道缺失，只能给位置类弱结论"
  },
  "what_would_make_it_analyzable": {
    "dt_jitter_ratio": "改用等间隔采集或提供硬件时间戳；或降采样到稳定周期后重导",
    "no_move_segment": "记录包含一次完整 move+settling 循环（触发点落在运动前后）",
    "cur_q_missing": "在 Scope 里加入驱动器 q 轴电流变量后重新导出",
    "n_after_trigger_gate": "延长记录时长或放宽触发阈值，使触发有效样本 ≥ 2000"
  },
  "partial_output": {
    "can_report": ["position-only dwell 漂移趋势"],
    "cannot_report": ["共振", "前馈失配", "软件诱导尖峰（无 events.jsonl，见 C6 §4）"]
  },
  "provenance": {"source.tier": "T1-a", "attribution": "见 §六 CITATION"}
}
```

### 5.4 缺 events.jsonl 的连带拒答（C6 一致性）

- Scope View 导出**不含事件流** → 本类样本 `events.jsonl` 缺失。
- 按 C6 §4：C3 必须显式写 `differential.not_evaluable = {family:"software_induced_error",
  why:"无事件上下文，无法区分机械尖峰与调度抖动"}`；**禁止**沉默跳过。
  （★ 键名口径 **A-18 / A-51**：族级标签只能进 `family`，`fault_mode` 位置只放 KB0 §2 的 22 个 slug，
  本行旧写法 `{fault_mode:"software_induced_error"}` 会直接违反 C3 规则 10。）
- 解析器在此的角色：**不伪造** `events.jsonl`——包内没有就不建，C2 据"包内有无该文件"产出
  `event_context.available = false`（C2 例 B 就是这个形状），其余对齐计数一律 `null`。
  ~~在 `provenance`/`meta` 标注 `events_available = false`~~ 该字段从未登记进 C1，属于自造路径（KB0 §6 检查 1），
  载体就是 C2 `event_context.available`；C2/C3 的门禁据此把 `software_induced_*` 判据族整体降级为不可评估。

### 5.5 拒入相关断言

- `assert (n_filtered >= 2000) or status == "insufficient_data"`（红线违反必拒，不得静默放行）
- `assert (dt_jitter_ratio <= 0.2) or status == "insufficient_data"`
- `assert (nan_ratio <= 0.05) or status == "insufficient_data"`
- `assert any(s.kind in {"move","settling","probing"} for s in segments) or status == "insufficient_data"`
- `assert ({"cur_q","vel_fb","fe"} & set(present_channels)) or status == "insufficient_data"`
- `assert for each violated_redline: why + fix non-empty`（拒答信息完整率 → C5 ≥80% 的实现点）

---

## 六、脱敏要求（发布作品集前必做）

真实表头含个人/网络标识（§一 L2/L3/L11）。发布前按字段级规则清除，**同时保留 CC BY 4.0 署名**。

### 6.1 字段级脱敏规则

| 位置 | 内容 | 处置 | 保留? |
|---|---|---|---|
| L2 `File` | `[REDACTED_HOST_PATH]\Export 10.csv` | 只留 basename `Export 10.csv`，路径整体替换为 `[REDACTED_HOST_PATH]`；`raw/` 内原文件同步改 | 否（路径 PII） |
| L3/L4 `Starttime/Endtime` | .NET ticks + 德语墙钟（时区未标注，KB7） | ticks 与墙钟**均**替换为 `[REDACTED_WALLCLOCK]`；仅保留「相对时长 ≈ 18.65 s」这类不含绝对时刻的量 | 否 |
| L11 `NetID` | 目标 PLC 的 ADS 路由（完整 NetID；原值按 §六 令牌化，此处不复述） | 替换为 `[REDACTED_ADS_NETID]`；正则 `NetID` 奇数列整列抹掉 | 否（网络标识） |
| L12 `Port` | `851` | 保留（协议常识，非 PII）；可选统一为 `[PORT]` | 可选 |
| L10 `SymbolName` | `Measurement_Connector.dPosition_test` 等 | **保留**（符号名不含主机路径/PII）；是语义映射输入 | 是 |
| L1 `Name`/标题 | `Measurement` | 保留 | 是 |
| 数据区数值 | 物理量 | 保留（这是作品集核心证据） | 是 |
| 任何 `Versuchsstand`/用户名/机名列 | — | 正则清除 `C:\\...`、`\\\\...`、含本地用户名的串 | 否 |

### 6.2 署名（CC BY 4.0）必须保留

在 `meta.provenance` 或包内 `CITATION` 写死：

- 作者：Reichenbach, Thomas — University of Stuttgart（ROR 04vnq7t77）
- DOI：`10.18419/DARUS-3600` 与 `10.18419/DARUS-5171`
- 许可：**CC BY 4.0**；引用须注明作者 + 机构 + DOI + 许可（KB7 署名要求）。
- 脱敏**只清除主机路径 / ADS NetID / 绝对墙钟时刻**，绝不清除署名与 DOI，也不改动数值。

### 6.3 脱敏断言

- `assert "Versuchsstand" not in serialized_bundle and "141.58." not in serialized_bundle`
- `assert all(meta.provenance.doi in {"10.18419/DARUS-3600","10.18419/DARUS-5171"})`（署名在包）
- `assert raw/*.csv 的 L2/L3/L4/L11 已按 6.1 替换`
- `assert license == "CC BY 4.0" and author == "Reichenbach, Thomas"`
- **口径（KB0 §6 检查 27）**：上面四条是**发布门**，不是"当前有多少处待清"的计数——计数一律抄
  `python data/probe_pii.py` 的打印行（§4.10/§4.11 已按该口径引用）。该脚本还给出一个容易被误读的事实：
  发布产物 `build/Export10_244531` 侧 `Versuchsstand`/内网 IP/盘符路径均 **0**，而 `NetID` 字样命中 **4**——
  这 4 次是本仓**关于脱敏的叙述文字**（`meta.source.note` 一句 + `report.html` 的署名行与 redaction 自检行），不是标识值。
  ⟹ 门的判据是 `assertions.REDACT_TOKENS = ("Versuchsstand", "141.58.", "C:\\")` 三个**标识值 token** 不出现，
  不是"某个词一次都不出现"；把后者写进断言会把自己写的说明文字判成泄漏，下一轮就会去删证据而不是删标识。

---

## 七、与 C1 契约不一致之处（本文件发现，**六条已全部裁决**，2026-10-20）

> 这些是解析真实数据时**与 C1 现有条文对不齐**的点，比文档本身更重要。原为"待主线程统一"，
> 现逐条带 A-xx 裁决与契约落点；保留原文是为了让读者看到"真实数据是怎么打断纸面契约的"。

1. **单位现实 vs counts 基准（C1 单位规则 / KB0 §5）**：C1 强制「内部基准 = 编码器 counts，
   `counts_per_mm=null` 时只印 `[counts]`、禁造 µm」。但 DaRUS 位置/速度/力**本就是 SI(m, m/s, N)**，
   根本没有 counts 刻度。`[counts]` 纪律对这份数据既不适用也误导。
   → 建议：C1 增补 `meta.units_are ∈ {counts, si_native}`，当 `si_native` 时按真实单位印、
   把「禁造 µm」改述为「无定标则不臆造**其它**单位」。
   **已裁：A-4（契约侧已改）** —— C1 单位规则已落 `meta.units_are ∈ {counts, si_native}`、`si_native` 分支按真实单位标注、
   「缺定标不得臆造其它单位」已写进 C1；本 KB2 §3.5 的 `units_are="si_native"` 处置即据此生效，不再只是建议。

2. **`fe` 命名陷阱（C1 派生规则 1）**：C1 假设「自带跟随误差」是好事，但真实数据里
   `dPosition_diff` 名为 diff、实为两绳总长的守恒残差（`≡ -(p_test + p_load)`，18,651 行行级最大残差
   3.55e-15，A-104 把本条从 `≈` 升格为 `=`），**不是** `pos_cmd - pos_fb`。
   若解析器按名字映射 `dPosition_diff → fe` 即产幻觉。→ 建议：C1/KB2 强调 `fe` 只能由
   `pos_cmd - pos_fb` 派生，除非对**自带候选通道**跑通 §3.2 相关性自检（`corr>0.99`）。
   **已裁：A-5（契约侧已改）** —— C1 派生规则 2 已定：`fe` 只允许「派生」或候选通道过 `corr>0.99` 自检，
   未过自检按原名进 `extra_channels`；`dPosition_diff` 这类「假朋友」不再被允许直接改名 `fe`。
   **A-104/A-105 追加两处**：①本样本 `pos_cmd ≡ pos_fb` ⟹ `fe ≡ 0`、方差为零，`corr` 自检**无定义**，
   契约已补"自检跑不了不得放行改名，只能判 `unavailable`"；②恒等式精确成立意味着这一列**零独立信息**，
   C1 派生规则 9 由此规定接入层必须做列间恒等式核对，派生列不得计入独立测量。

3. **`torque` 单位（C1 词表：`torque` = 额定转矩 %）**：DaRUS 的 `dTorque_*` 是 **Nm**，且作者脚本
   注明有 ×10 修正（`catanalyze.m` 第 100-102 行）。C1 把 `torque` 锁死为「%」容不下 Nm 原生转矩。
   → 建议：`torque` 允许 `unit ∈ {percent_of_rated, Nm}`，或新增 `torque_nm`。
   **已裁：A-4（契约侧已改）** —— C1 单位规则已把 `torque.unit ∈ {percent_of_rated, N_m}` 显式化
   （DaRUS 的 `dTorque_*` 是 N·m、另有原作者 ×10 修正），不再锁死为「额定百分比」；无需新增 `torque_nm`。

4. **无布尔/数字旗标通道类型（C1 只有 `io` 打包 int 状态字）**：真实数据的方向与触发是**独立布尔列**
   （`bMovingForward`、`bTrigger_Record` 等），不是 packed `io` 位。C1 没有「布尔通道」概念。
   → 建议：允许这些作为**解析器内部输入（门控/定符号）不入 `waveform.tsv`**（本 KB2 采此法），
   或 C1 增补 `bool_channels` 声明区。
   **已裁：A-7（契约侧已改）** —— C1 已采纳「厂商布尔列是解析器内部输入，不写入 `waveform.tsv`」并加词表注；
   采本 KB2 现法，未增补 `bool_channels` 声明区。

5. **单值 `pos_fb` vs 多反馈传感器（C1 词表只一个 `pos_fb`）**：DaRUS 有三套独立位置
   （电机编码器 + ASCO 光学 + LSV 电感，KB7）。C1 无法同时表达多 `pos_fb`。
   → 建议：C1/KB2 定义 `meta.cross_validation.pairs`，主 `pos_fb` 之外经 `extra_channels` 引用，
   分歧作为 `sensor_disagreement` 证据而非丢弃。
   **已裁：A-6（契约侧已改）** —— C1 已落 `cross_validation.pairs` + `extra_channels`（多余位置反馈经此保留），
   C2 侧对应 `sensor_disagreement`；三套独立反馈的语义在契约内可表达，见 C1 示例 `pairs: [["pos_fb","laser_ref"],["pos_fb","scale_fb"]]`。

6. **C1 示例假设 `cur_q` 常见可得**：这份 T1-a 真实数据**没有电流通道**（`probe_cat.py` 通道清单无 `I`/`It`），
   共振主通道缺。C1 红线「cur_q/vel_fb/fe 全缺」才拒，本例有 fe/vel_fb 故不拒，但 §二坑 1 + §五 叠加后，
   这份数据对共振类判据几乎整体不可评估。→ 建议：报告层明确「位置/速度可跑、电流类判据需另补数据」。
   **已裁：契约侧未新增字段** —— `cur_q.unit ∈ {A, percent_of_rated}` 的显式化归 A-4/A-14；
   「三者全无才拒」C1 数据质量红线本已覆盖，本例有 `fe`/`vel_fb` 故不整包拒。本项「位置/速度可跑、电流类判据需另补」
   属 §二坑 1（频带）+ §五 的**报告层表述**，不改 C1 字段，按现有红线执行即可。

7. **一个文件里有两条以上时间栅格（C1 原为单栅格契约）** ← **2026-10-20 发现，** **已裁 A-96：采纳 (a)**
   触发样本：DaRUS-2563 / 3003 / 3252 的 dSPACE `.mat`（MDF struct，`Y[i].XIndex` 显式登记每条通道挂在哪条栅格上）。
   主线程实测：2563 三栅格 = 73,020 @ 1 kHz（`Raster="1 ms"`）/ 292,080 @ 4 kHz（`Raster="HostService"`）/
   26 点 `Raster="OnChange"`（jitter 0.221）；3003 = 11,001 / 44,001；3252 = 2,139 / 8,556。
   问题：C1 只有一组 `fs / t`，KB2 §8.1 的映射表也只按单一 `SampleTime` 写 ⟹
   ① 4 kHz 测量通道按 1 kHz 接入会**静默降采样**（丢掉 A-94 刚松绑的频带）；
   ② 反过来按 4 kHz 接入则 `traj_KGT[0]`/`e_x_T` 要被外插 ⟹ 违反 KB0「不猜语义」与 C2 的 `fe` 定义纪律；
   ③ `OnChange` 是**离散事件栅格**（26 点、jitter 0.221），若被当成第三条波形时基参与判定，
   会同时踩中"时基抖动超阈"与"行数不足"两条假拒。
   **处置（**已裁 A-96：采纳 (a)**，2026-10-20 主线程一句话裁定，取代此前临时的 (b) 登记）**：
   - **(a) 采纳两字段方案（已裁，本项目执行口径）**：C1 增 `meta.time_bases[]`
     （每条 `{id, role ∈ {primary, secondary, event}, n_samples, dt_median_s, sample_rate_hz,
     dt_jitter_ratio, strictly_monotonic, unit_source}`，`primary` 有且仅有一条、由
     `meta.primary_time_base` 指名）与 `channels[].time_base_ref`（指向 `time_bases[].id`，
     缺省 `null` = 继承 primary）；`sample_rate_hz` / `quality.*` / `nyquist_hz` 一律取**主栅格**口径
     ⟹ 单栅格样本只需补一条 `{id:"tb0", role:"primary"}`，解析器与规则引擎**不新增分支**（向后兼容）。
     跨栅格比较必须显式重采样并登记 `meta.resample[] = {op, from, to, channels, band_effect}`
     （`band_effect ∈ {none, band_lost, aliased_risk}`，**必填**；`op` 默认 `nearest`——
     实测 `e_x_T ≡ traj_KGT[0] − x_meas_table(nearest)` 在 2563 偏差 2.6e-10、3003 偏差 5.8e-15、
     2563_SP_v100 恰为 0.0 ⟹ nearest 不引入语义误差）。
     `OnChange` 栅格标 `role = "event"`，**禁止**参与 `fs`/时长/抖动判定，也**不得**触发硬拒。
     完整条文见 C1「多速率栅格（A-96）」小节。
   - **(b) 不采纳**（历史备选，留档）：一律按 1 kHz 主栅格接入，4 kHz 通道进 `extra_channels`
     并标 `downsample_risk = "band_lost"`，报告中频带一律按 1 kHz 写（即 A-94 的松绑在这些样本上不生效）。
   **采纳 (a) **不改变**结论的升格边界**：(a) 只是让 4 kHz 通道**可用**，
   `cur_q` 仍缺 ⟹ R-03/R-04 仍不给归因（A-94 的 `band_gate_pass_channel_gate_fail` 原样成立）；
   跨栅格的相干/相位类判据在 `band_effect ∈ {band_lost, aliased_risk}` 时一律 `unavailable`（A-96 规则 6）。
   **禁止**因为「现在能读到 4 kHz 了」就把频带结论写成实测归因。

---

## 八、解析器输出映射与整体校验断言（收口）

### 8.1 Scope View → `meta.json` 字段映射

| meta 字段 | 取值来源 |
|---|---|
| `schema` | 常量 `"axiscope.waveform/1"` |
| `source.vendor` | `"beckhoff"`（Scope View 原生） |
| `source.drive_model` | `"TwinCAT3 ScopeView"`（851 端口佐证，§一 L12） |
| `source.export_format` | `"csv"` |
| `source.original_filename` | L2 basename，脱敏后 |
| `source.ingest_confidence` | 结构定位器全绿=0.9；任一 `audit.assumptions` 非空则下调 |
| `sample_rate_hz` / `_source` | 第 8 行 `SampleTime[ms]` → declared；col0 差分 → inferred（坑 1） |
| `axis.type` / `counts_per_mm` | 试验台为绳索卷筒，`counts_per_mm=null`、`units_are="si_native"`（§3.5） |
| `drive.*` | 除 XML 明文发布的控制器参数（KB7 `kff=1.5` 等）外多为 null；**禁默认值** |
| `present_channels` | 映射成功的 canonical 通道集 |
| `channels[k]` | `{raw_column(别名), symbol(路径), native_unit, sign, derived, confidence}` |
| `io_bits` | Scope View 非 packed int → 留空；布尔另作内部输入（§七-4） |
| `segments` | 触发 0→1 边界 + dwelling/move 划分（坑 5）；DaRUS 恒速段可标 `probing` |
| `quality.*` | `n_samples`(过滤后)、`dt_median_s`、`dt_jitter_ratio`、`nan_ratio`、`nyquist_hz` 等（§二/§五）；**口径 = 主栅格**（A-96 规则 4） |
| `time_bases[]` / `primary_time_base` | Scope View 单栅格 ⟹ 恒为**一条** `{id:"tb0", role:"primary", n_samples, dt_median_s, sample_rate_hz, dt_jitter_ratio, strictly_monotonic, unit_source}`，`primary_time_base="tb0"`；`channels[k].time_base_ref` 全部 `null`。**多栅格来源（dSPACE MDF）才展开 `secondary` / `event`**（A-96） |
| `resample[]` | Scope View 无跨栅格运算 ⟹ `[]`。**禁止**为空数组却声称做过降采样/插值（A-96 规则 3） |
| `freq_limits.blocked_rules` | **不是 meta 字段**（A-84）：由 C2 按规则 7 从 `meta.quality.nyquist_hz` 推导，fs<4000 时含 `R-03`/`R-04`（坑 1）；解析器只保证 `nyquist_hz` 正确。**多栅格样本另须按各通道所在栅格逐条判**（A-96 规则 6） |
| `provenance` | 触发门控计数、丢弃头计数、CITATION（§五/§六） |

### 8.2 → `waveform.tsv`

- 第 1 列 `t`（秒，`col0*dt_ms/1000`，过滤+复位后从 0 单调递增）。
- 其余列为**映射成功的 canonical 通道**（列名取自 C1 词表），`fe` 为派生列（§3.2）。
- 缺失 canonical 通道**不出现在表头**（C1「不要写空列」）。
- 可选 `x_` 前缀扩展列承载 `extra_channels`（§3.6），但 `present_channels` 只数 canonical。

### 8.3 端到端断言（样本包自检，入库前）

- `assert wave.t[0]==0 and strictly_monotonic(wave.t)`
- `assert wave.n_cols == 1 + len(present_channels) (+ n_extended)`
- `assert meta.quality.n_samples == len(wave) == n_after_trigger_gate`
- `assert set(wave.headers[1:canonical]) ⊆ C1_vocab and disjoint with {"","t"}`
- `assert "fe" in present ⇒ fe == pos_cmd - pos_fb (within tol)`（派生一致性，坑 §3.2）
- `assert direction-signed channels satisfy |signed|==|raw| and sign==dir`（坑 3）
- `assert features.freq_limits.blocked_rules ⊇ {R: R.needs_reliable_band_hz > meta.quality.nyquist_hz}`（坑 1；左侧是 C2 输出，A-84）
- **多栅格断言（A-96）**：
  - `assert sum(tb.role == "primary" for tb in meta.time_bases) == 1` 且
    `assert meta.primary_time_base == next(tb.id for tb in meta.time_bases if tb.role == "primary")`
  - `assert len({tb.id for tb in meta.time_bases}) == len(meta.time_bases)`（`id` 唯一）
  - `assert all(c.get("time_base_ref") in {tb.id for tb in meta.time_bases} for c in meta.channels.values())`（`null` 视为继承 primary）
  - `assert all(r.band_effect in {"none", "band_lost", "aliased_risk"} for r in meta.resample)` —— **必填**，`None` 即失败
  - `assert not [tb for tb in meta.time_bases if tb.role == "event" and tb.id == meta.primary_time_base]`（事件栅格不得作主栅格）
  - `assert meta.sample_rate_hz == meta.time_bases[meta.primary_time_base].sample_rate_hz`（向后兼容锚点自洽）
  - `assert "OnChange" 之类事件栅格未参与 dt_jitter_ratio / n_samples / duration`（不可直接断言数值，须在解析器侧由 `role` 分支保证并单测）
- `assert N_mapped + N_extra == N_header and no channel unmapped-and-dropped`（§3.6）
- 脱敏断言见 §6.3；拒入断言见 §5.5。
- 引用完整性（KB0 §6）：本 KB2 提及的 R-03/R-04 在 KB0 §1 存在；`units_are`/`cross_validation.pairs`/
  `extra_channels`/`sensor_disagreement`/`quality_ref.*` 等**均已在 C1/C2 登记**（§七 六条全部已裁，
  A-4/A-5/A-6/A-7 + A-49），本文件不再处于"等登记"状态；唯一例外是 `freq_limits`，它本就不是 C1 字段（A-84）。
