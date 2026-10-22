# KB8 — C5 评测案例目录规范（benchmark cases）

本文件是 **C5 评测协议**（`docs/contracts/C5-evaluation-protocol.md`）的**案例侧配套**。
C5 只定义了指标（ECE、拒答正确率、无依据成功声明、反事实通过率背离指数…）与 dev/hidden 划分要求，
但没有回答三个可执行的问题：**案例从哪来、每个案例长什么样、覆盖够不够**。本文件补这三件事。

> **本文件不重定义任何指标**。指标的口径以 C5 §3 为唯一权威；本文件只规定"喂给这些指标的数据
> 必须满足什么结构"。凡两处口径可能打架，以 KB0 裁决为准——本文件曾上报的 14 条**已全部落裁**
> （KB0 §7.3，**A-54…A-67**），本文件已按裁决回写、原始问题留痕见 §7；今后新冲突仍先进 §7。

边界与纪律（逐条对齐 KB0）：

- **命名以 KB0 为唯一权威**：22 个 cause slug 见 KB0 §2（机械 8 / 电气 7 / 软件诱导 7）；证据 tier 见
  KB0 §4（**字段权威名 = `source_tier`，A-54 已裁**），值域 `T1-a`/`T1-b`/`T2`/`T3`，`T1-c` 由 C5 §1 与 A-24 追加；
  91 条裁决（A-1…A-91，编号只承诺唯一与连续、不承诺时序，见 KB0 §6 检查 18）见
  KB0 §7/§7.1/§7.2/§7.3——本文件上报的 14 条全部落裁（A-54…A-67），
  KB5 上报的 A-68/A-69/A-70 亦落在本文件（⟹ §1.1/§1.5/§3），本文件全部案例的期望判定与裁决一致；
  第六轮的 **A-82**（残差与差值两个方向）与 **A-86**（KB6 门禁三例进配额表）直接改到本文件正文；
  **A-87**（约定/接线真值层无覆盖）落到本文件 **G-9** + §6 配额表末行 + "通过数口径"段；
  **A-89**（③ 类拆 ③a 文档可查 / ③b 批次与现场，接口事实走 `external_reference` 且核对主体不可转借）
  落到 **G-9 的第 ③ 类考核形状** + §6 配额表末行的"分档形 ≥2"（本文件的 `basis`/配额口径不因此改动）；
  **A-90**（`verification_level` 三档：自洽/模型级/物理级）与 **A-91**（裁决新字段必须有契约载体）
  对本文件只有一处影响：本文件"通过数口径"段要求的**执行 N / 跳过 M 分列**现在有了评测侧载体
  （**C5 §3 的"案例执行分列"行**），而案例行将来要带的 `verification_level` 属**实现期字段**——
  本期不新增列，只在此登记："合成案例（`T3`）恒 `L1`，DaRUS/CWRU 记录属 `L3`（真值产自物理世界，
  与本 agent 不上机不冲突）"，缺这一档时案例行按 `L1` 处理，**不得**因"跑过就算验证"往上写。
- **R-03 / R-04 的 `reliable_band ≥ 2000 Hz` 门槛取自 KB0 §1 的表**，这是本文件唯一直接引用的判据频带下界；
  其余规则号（R-05/R-07/R-11/R-12/R-15/R-20/R-22/R-25/R-30）只从 KB0 §6/§7 出现过的引用中取，
  不臆造 KB3 阈值。
- **字段名逐字取自 C1 / C2 / C3**：`sample_rate_hz`、`sensor_config`、`counts_per_mm`、`present_channels`、
  `segments[].kind`、`quality.*`、`event_context.*`、`freq_limits.reliable_band_hz`、`position_quantum_mm` 等。
- **T3 铁律**（C5 §1 / KB5 §0.1 / §3 T3 纪律）：合成案例只证明管线连着，**不构成任何准确率/命中率声明**，
  不进对外能力指标。本文件所有 T3 行的 `expected_verdict_class` 只服务"管线可达 + 拒答纪律"两类考核。
- **措辞纪律**（A-31 / C3 规则 14 / **A-67 已裁**）：本文件不写"已验证/已核对/已下载核验"类断言，不编造 DOI、不编造实测数值。
  外部数据集标识按 KB7 登记：DaRUS 两包有可核实标识 —— `doi:10.18419/DARUS-3600`、`doi:10.18419/DARUS-5171`
  （Reichenbach, Thomas — University of Stuttgart，CC BY 4.0，署名规则见 KB7）；CWRU / Paderborn / Aalto / MFPT
  在 KB7 未登记可核实标识 ⟹ `origin.id` 一律 `[待核]`，**不凭记忆填 DOI、不猜 URL**（仓库红线）。
  示意数值一律显式标 `示意值，非实测`（对齐 C3 规则 13）。

---

## 1. 案例目录 schema（JSONL，一行一案例）

一个案例 = 一个可被 C1 loader 读入的样本包（目录）+ 一条评测元数据（`cases.jsonl` 的一行）。
评测元数据是**旁挂**的，绝不写进样本包内部——尤其不得把真值塞进真实样本包（见 §4 污染红线）。

### 1.1 字段表

| 字段 | 类型 | 口径 / 取值 | 来源契约（逐字字段名） |
|---|---|---|---|
| `case_id` | str | 见 §1.2 命名规范 | C5 §2 的 `case_id`；KB5 §5.4 `c5_case.case_id` |
| `source_tier` | enum | `T1-a` / `T1-b` / `T1-c` / `T2` / `T3`（**恰好**这五个） | KB0 §4 表；**A-54 已裁：权威名 = `source_tier`**，C5 §2 旧名 `evidence_tier` 就地作废（已回写） |
| `origin` | obj | `{"source_tier":…, "repo":…, "id":…}` 三键（**A-67 已裁形状**）。`repo`＝数据集发布简称或 `KB5:<参数集ID>`（T1-a=`DaRUS`；T1-b=`CWRU`/`Paderborn`/`Aalto`/`MFPT`；T2/T3=`KB5:P-A`/`KB5:P-B`/`KB5:P-C1..C3`）。`id`＝**仅 KB7 已登记的可核实标识**：DaRUS 为 `doi:10.18419/DARUS-3600` / `doi:10.18419/DARUS-5171`（署名⟹§3 T1-a 行）；CWRU/Paderborn/Aalto/MFPT 写 `[待核]`——**不凭记忆填 DOI、不猜 URL**；T2/T3 写 KB5 参数集/注入登记号（仓库内可核实） | KB7（登记依据）；C5 §1 数据集列；KB0 §7.3 A-67 |
| `sha256` | str | 样本包冻结摘要计算口径见 §1.4；**A-60 已裁：覆盖输入样本原始字节**，不是 C2 特征快照；本字段只登记格式（64 位十六进制），**不在文档内计算** | C5 §2 `bench/hidden.sha256`；KB5 §5.7 逐字节一致 |
| `features_sha256` | str\|null | **附加字段（A-60 已裁）**：KB5 §5.4 `self_check.features_sha256`，只用于"特征管线变了"的回归定位（哪个案例的特征输出需要重新基线），**不作案例身份**——身份随管线变＝允许看着管线输出挑案例（⟹§1.4） | KB5 §5.4 `self_check.features_sha256` |
| `split` | enum | `dev` / `hidden`（仅此二值） | C5 §2 "开发集/隐藏测试集 = 60/40" |
| `fs_hz` | float | 波形采样率，等于 `meta.sample_rate_hz`，亦即 C2 顶层 `fs_hz` | C1 `sample_rate_hz`；C2 `fs_hz` |
| `reliable_band_hz` | float | 等于 C2 `freq_limits.reliable_band_hz`（= nyquist/1.25，C2 规则 7）。用于比对判据下界（KB0 §1） | C2 `freq_limits.reliable_band_hz` |
| `present_channels` | list | 逐字取 C1 `meta.present_channels`（缺失通道不出现，C1 §waveform）；值域＝C1 §通道词表列名 | C1 `present_channels`（**A-55 已裁：权威名即此**，C5 旧倒装词 `channels_present[]` 作废） |
| `sensor_config` | enum | **四值**（A-68 已裁，旧三值作废）：`motor_side` / `load_side` / `mixed` / `unknown`（C1 派生规则 7 / C2 规则 9）。`mixed`（峰由电机侧估、谷由负载侧估，如 P-B2/INJ-30）行为与 `unknown` 同——**顺序项不评＋置信度封顶**——但**记录原因不同**：`unknown`＝"不知道装在哪侧"，`mixed`＝"知道这条曲线不是同一传递函数的响应，峰谷对不承载零极点交替信息"。位置类通道另有可选 `sensor_side ∈ {motor, load, unspecified}`（C1，缺省 `unspecified`） | C1 `meta.sensor_config`（A-68） |
| `counts_per_mm` | float\|null | 逐字取 C1 `meta.counts_per_mm`；可为 `null`（**仅真缺定标变体**）。**A-75 已裁**：`si_native` **不**自动等于 `null`——取值按"有没有可复算推导链"分岔，本目录 T1-a/KB5 §2.1 的 P-A 即 `si_native` 且有 §1.1 推导链 ⟹ 写 `5.8349`（`provenance = "assumed"`），一律写 `null` 会把 A-13 的 0.1714 mm vs 0.00002 mm 四量级对照抹掉。**A-56 已裁**：布尔口径 `counts_per_mm_known` 作废——布尔丢了"是多少"，而 `position_quantum_mm = 1/counts_per_mm`（C2 规则 11）要的就是数值，写 `null` 才让 A-13 的定标缺口在案例层可见。**A-66 已裁**：`position_quantum_mm` 保持由本字段派生、目录**不单列**（两载体必打架：`counts_per_mm=2000` 配 `position_quantum_mm=0.0005`），A-13 的"0.1714 mm vs 0.00002 mm 四量级对照"正是靠单一来源才成立。**关联 A-69 已裁**：`meta.axis.travel_limit_{neg,pos}_mm`（可选，缺省 `null`）本目录不单列、经样本包引用，⟹§1.5；`unit_scale_mismatch` **不是**特征路径或证据字段，只是 `truth.json` 侧记账标签（其可观测形式＝已登记的 `*_mm`/`*_counts` 比值跳变特征），本文件不得把它当证据引用 | C1 `counts_per_mm` |
| `events_present` | bool | 样本包内是否存在 `events.jsonl`；等价于 C2 `event_context.available` | C1 目录结构；C2 `event_context.available` |
| `sync_verified` | bool\|null | `events_present=false` 时为 `null`；否则取 C1 `meta.sync.verified` / C2 `event_context.sync.verified` | C1 `sync.verified`；C2 `event_context.sync.verified` |
| `segments_kinds` | list | `meta.segments[].kind` 去重集合，**严格取 C1 词表** `rest`/`move`/`settling`/`dwell`/`probing`/`path`/`homing`/`scanning`/`curing`（`unknown` 只作 loader 兜底，目录里禁止主动写） | C1 `segments[].kind` 词表 |
| `injected_fault` | obj\|null | `{"kb5_inj":"INJ-01","kb0_slug":"mechanical_resonance"}`；`kb5_inj` 引用 KB5 §3 注入编号，`kb0_slug` 引用 KB0 §2；无故障/拒答类案例此字段为 `null` | KB5 §3 INJ-xx；KB0 §2 slug；KB5 §5.4 `injected[].{id,slug}` |
| `expected_verdict_class` | enum | 五值：`<该 slug>`（= `injected_fault.kb0_slug`） / `family`（**仅 T1-b 案例**：机械↔电气二分类粒度，gold 取 KB0 §2 族名，**禁止映射到 22 slug**——A-63 已裁，⟹§2.3 G-2/§3） / `none_of_the_above` / `refuse_insufficient_data` / `co_occurrence_only` | C3 期望判定形状（`verdict` + `differential`）；C5 §2 `gold_root_cause`；KB0 §7.3 A-63 |
| `expected_not_evaluable_min` | int | 该案例下 agent **必须**在 C3 `differential.not_evaluable[]` 里登记的最少条目数（≥0）。见 §1.5 推导规则 | C3 规则 9；C2 规则 7/8；A-17 |
| `counterfactual_variants` | list | 每项 `{"改哪个参数":"→ 目标值","期望结论翻转":"<新 expected_verdict_class>"}`；用于 C5 §3 反事实通过率背离指数。取值须可被 KB5 生成 | C5 §3；KB5 §1.2/§1.3/§4.4 |
| `gold_params_ref` | obj | **只写引用、不复制数值**（A-58 已裁）：`gold_params` 权威载体＝样本包 `truth.json.c5_case.gold_params`（KB5 §5.4），本字段填 `{"path":"<样本包>/truth.json#c5_case.gold_params","sha256":"<64hex>"}`。理由：真值必须跟样本走，抄进表格后改仿真参数不会同步改表，而 `f_m_hz` 一类还带容差 | KB5 §5.4 `c5_case.gold_params`（载体）；C5 §2（目录行已按 A-58 改引用式） |
| `forbidden_conclusions` | list | **必填**（A-59 已裁，不再是隐含）：本案例禁语清单，取值自 KB5 §5.4 `c5_case.forbidden_conclusions` 与 KB5 §6.3 禁止措辞表（含"未发现异常/未发现谐振"类越级措辞）。`expected_verdict_class` 只判"说对没有"，禁语才判"**有没有说过分的话**"——C3 硬性规则 14 的评测侧对偶，A-31 的自动检查正是靠禁语表落地 | KB5 §5.4/§6.3；C5 §2 `forbidden_conclusions[]`（已按 A-59 升必填）；C3 规则 14 |
| `human_baseline_labels` | obj | `{"status":"pending"}` 起步。≥2 名伺服工程师独立标注后才回填；**当前全部为 pending**（见 §5） | C5 §5 人工基线 |

> `human_baseline_labels` 在冻结前对**每一条**案例都是 `{"status":"pending"}`。这不是占位偷懒：C5 §5
> 的人工基线是整个评测最贵的一步，截至本文件落盘**尚未招募标注者、尚未产出任何人标**，
> 因此 §3 指标表里凡"附人工基线"的单元格目前都无数据可比（对齐 A-31：不得暗示已有基线）。

> `difficulty(1-5)` **不进本目录行**（A-57 已裁）：它是 C5 §2 侧的排序/配额属性，本文件用
> `expected_verdict_class`＋§6 配额表达难度——同一属性两处可变，早晚会与配额表互相打脸。

### 1.2 `case_id` 命名规范

```
<tier>-<origin>-<INJ或control>-<4位序号>
  tier   ∈ {T1a,T1b,T1c,T2,T3}
  origin ∈ {DARUS, CWRU, Paderborn, Aalto, MFPT, selfrig, PB, PA, PC1, PC2, PC3, ...}
  INJ    ∈ KB5 §3 的 INJ-01..INJ-30，或控制类 CTL（none_of_the_above / 过频带 / 缺定标 / 缺事件）
序号在各 (tier,origin,INJ) 分组内单调，用于同批次多投影（KB5 §5.6 每个工况 ≥3 投影）。
```

与 KB5 注入清单一一对应（**引用其编号，不另造语义**）：

| KB0 slug（KB0 §2） | 主判据注入（KB5 §3） | 备注 |
|---|---|---|
| `mechanical_resonance` | INJ-01 | kHz 档只在 P-B(fs=8000)；P-A 的 45 Hz 峰因 8 Hz 指令低通 `declared_detectable=false`（KB5 §2.1） |
| `mechanical_backlash` | INJ-02 | 需换向段 |
| `mechanical_friction_stiction` | INJ-04 | τ_s/τ_c 扫描 |
| `mechanical_crawling` | INJ-04 | 与 stiction 同源 INJ，靠 `crawling.*` 分岔 |
| `mechanical_encoder_periodic_error` | INJ-05 | 1/转 + 3/转 |
| `mechanical_loose_structure` | INJ-03 (+INJ-20 耦合) | 并联低刚度支路 |
| `mechanical_thermal_drift` | INJ-06 | **T3 不得支撑**（KB5 §6.1），只测 temp 缺失→unavailable；**A-64 已裁：能力层结构性真空，不造正例**（⟹G-4） |
| `mechanical_double_inertia` | INJ-07 (+INJ-30 P-B2) | 配对判据 R-04 需 fs≥5000 |
| `electrical_current_loop_bandwidth` | INJ-08 | f_i 1200→300 Hz |
| `electrical_velocity_pi_detune` | INJ-12 | 极限环 |
| `electrical_position_pi_detune` | INJ-13 | 自激啸叫，rest 段仍在 |
| `electrical_feedforward_mismatch` | INJ-09 | kff 扫描，含 DaRUS 1.5 |
| `electrical_torque_ripple` | INJ-11 (6k±1) | INJ-20 cogging 若不耦合结构则也归此 |
| `electrical_motor_heating` | INJ-14 | 与 INJ-06 靠 `cur_q_rms_pct` 同向区分；**A-64 已裁：不造正例**，该判别只存活在拒答纪律叙述里（⟹G-4）。`cur_q_rms_pct` 分母另受 A-70 约束（⟹§1.5） |
| `electrical_resolution_quantization` | INJ-10 | Δ 1→16 counts |
| `software_induced_host_thread_jitter` | INJ-15 | 事件流必写 |
| `software_induced_interp_buffer_underrun` | INJ-16 | 事件流必写 |
| `software_induced_bus_cycle_miss` | INJ-17 | 事件流必写；A-9/A-45 升级条件见 §2.2 |
| `software_induced_late_vision_result` | INJ-18 | 事件流必写 |
| `software_induced_pulse_eq_overwritten` | INJ-19 | 事件流必写（指含事件母样本）；**无事件/未同步孪生同批必产（A-61 已裁，豁免作废）⟹§2.2** |
| `software_induced_settle_window_too_short` | INJ-21 | 事件流必写（同上；孪生同批必产，A-61 ⟹§2.2） |
| `software_induced_polling_latency` | INJ-22 | `dt_jitter_ratio>0.2` 时应落 C1 红线→期望 refuse |

控制类（KB5 §3.4）不映射单一 slug，专测纪律：
INJ-23（LuGre 对照）、INJ-24（非 LTI 外载，P-C1 拟合残差门）、INJ-25（健康对照→`none_of_the_above`）、
INJ-26（谐振↔前馈失配混淆对，C5 §6）、INJ-27（多故障叠加；difficulty 5 属 C5 侧属性，本目录不带——A-57）、
INJ-28（缺通道/缺定标）、INJ-29（陷波人为谷，R-04 反例）、INJ-30（非共置构型，`sensor_config=mixed`，A-68）。

### 1.3 与 C5 §2 字段清单的映射（原冲突已全部落裁：A-54…A-59、A-67，本文件与 C5 均已按裁决回写）

C5 §2 曾列出的案例字段与 C1/C2 权威字段名**不完全一致**，本文件当时采 C1/C2 名并上报 §7——
主线程已在 KB0 §7.3 逐条裁决（A-54…A-59），C5 §2 就地改名**已落地**（其现文标注"旧名作废"）。
下表"处理"列现为**裁决结果**，不是待办：

| 原 C5 §2 写法 | 本文件 / C1 权威写法 | 处理（裁决后） |
|---|---|---|
| `evidence_tier` | `source_tier` | **已裁（A-54）**：权威名＝`source_tier`，C5 §2 已就地改名；中文说"证据层级"不算违反——只有**字段名**要求唯一 |
| `source_ref` | `origin` | 同义对应；A-67 另裁对象形 `{"source_tier","repo","id"}`，标识登记 ⟹§1.1/§7-N |
| `channels_present[]` | `present_channels[]` | **已裁（A-55）**：C5 逐字改用 C1 的 `present_channels`——目录行必须能与 loader 产出的 `meta.present_channels` 逐字对拍，否则冒充检测（C2 规则 15）与频段门禁（C1）都失去参照 |
| `counts_per_mm_known(bool)` | `counts_per_mm(float\|null)` | **已裁（A-56）**：可空数值、与 C1 同型，直接喂 `position_quantum_mm=1/counts_per_mm`（C2 规则 11） |
| `segments[]` | `segments_kinds[]` | 目录行只存 kind 去重集；完整段以样本包 `meta.segments` 为准（本文件简化，未过 §7，无需裁决） |
| `difficulty(1-5)` | **不并入**（本文件无此字段） | **已裁（A-57）**：`difficulty` 留在 C5 §2 作排序/配额属性；KB8 用 `expected_verdict_class`+配额表达难度 |
| `gold_params[]` | `gold_params_ref`（只写引用） | **已裁（A-58）**：权威载体＝样本包 `truth.json.c5_case.gold_params`（KB5 §5.4），目录行只写路径+`sha256`，**不复制数值** |
| `forbidden_conclusions[]` | `forbidden_conclusions`（**升必填**） | **已裁（A-59）**：必填，取值自 KB5 §5.4/§6.3；与 C3 硬性规则 14 成对偶（缺它则规则 14 在评测侧无对偶） |

### 1.4 `sha256` 的计算口径（A-60 已裁：覆盖**输入样本原始字节**；只写口径，不算值）

裁决（A-60）：hidden 切片的 `sha256` 冻结覆盖的是**输入样本原始字节**，**不是** C2 特征快照；
KB5 §5.4 `self_check.features_sha256` 保留为 §1.1 的**附加**字段，只用于"特征管线变了"的回归定位，
**不作案例身份**。理由必须写清：案例身份由"喂的是什么数据"定义，不由"我们的管线在它上面看到什么"定义——
**若身份随管线变，等于允许看着管线输出挑案例**：换一版解析器、改一条特征公式，全体案例身份就变，
就能把"对我们不利的案例"洗出冻结集，dev/hidden 划分与 A-31 的防自证双双落空。反过来，
特征快照哈希变了不影响任何案例身份，只提示"这些案例的期望特征需要重新基线"。两个哈希，各司其职，不可混：

```
digest = SHA256( bytes(meta.json) || 0x00 || bytes(waveform.tsv) || 0x00 || bytes(events.jsonl 若有，否则空) )
  - 三段按固定顺序拼接，0x00 作分隔；缺 events.jsonl 时空段（保证"无事件孪生"与"有事件孪生"是不同摘要）。
  - meta.json / events.jsonl 按 JSON 键的字节原文参与（不做重排序），复现性靠"同一份落盘文件"而非"等价 JSON"。
  - 冻结后写入 bench/hidden.sha256（C5 §2）。追加任一案例 => 全量重划 + 版本号 +1（见 §4）。
```

`[P]`：拼接顺序/分隔符仍是本文件自定（契约未固定字节级配方）——A-60 裁的是**哈希覆盖什么**，
字节配方仍是本文件的落盘约定；"确认覆盖输入还是特征快照"的旧疑问**已裁**（见上，原 §7-G 留痕）。

### 1.5 `expected_not_evaluable_min` 推导规则（对齐 C3 规则 9 / C2 规则 7/8）

- 案例 `reliable_band_hz < 2000`（KB0 §1 的 R-03/R-04 下界）⟹ `min ≥ 1`：整个 kHz 谐振/双惯量配对族必须登记
  `not_evaluable`（C2 规则 7"不得输出未发现共振"），且 `audit.rules_fired` 含 `blocked_rules=["R-03","R-04"]`。
- 案例 `events_present=false` ⟹ `min ≥ 1`：`software_induced_error`（族级标签，KB0 §6/§87 行）必须逐条或合并登记
  （C2 规则 8"available==false 时必须登记，不得沉默"）。
- 案例缺 `cur_q` 且某判据依赖它 ⟹ `min += 1`（C2 规则 2 null→unavailable）。
- 案例 `counts_per_mm=null` ⟹ 不必然加计数（µm 声明是被"改写为无法判定"，C2 规则 11，不是 not_evaluable 条目）；
  但若该案例本应给精度声明，则 `forbidden_conclusions` 必须含 `sub_quantum_mm_claim`（见示例行；该数组现为**必填**，A-59）。
- 案例 `meta.axis.travel_limit_{neg,pos}_mm = null`（C1 `axis` 字段，A-69 已裁登记，可选、缺省 `null`）⟹
  依赖行程边界的判据必须 `unavailable` 并登记进 `blocked_rules`；**不许**从"波形里位置曾停住"反推限位值再当已知参数用
  （软限位是厂商手册明列的**上下文**，不是波形特征；⟹§1.1 注、§2.1 INJ-19 行）。
- 凡 `*_pct` 转矩类判据：分母权威＝`meta.drive.rated_torque_N_m` + `rated_torque_source`（C1，A-70 已裁，
  从此比值判据有可追溯分母）。合法性阶梯：`measured`/`manual` ⟹ 正常；`nameplate` ⟹ 可用但带限定语；
  **`assumed` ⟹ 可用但证据层级封顶 T2 + 强制 caveat"额定转矩为假定值，百分比类判据的绝对刻度不可信"**
  （A-27 的 DaRUS `torque_max=32` 正是 `assumed` 档）；字段 `null` ⟹ `*_pct` 恒 `null`，只有 `N_m` 分支成立。
  这两条走 `unavailable`/caveat 通道，**不**额外增加 `expected_not_evaluable_min` 计数（缺 caveat 才是违例，按禁语处理）。

### 1.6 一条完整示例行（示意值，非实测；T3 管线案例）

两例均为**合法 JSON**（A-52：本文件任何 ```json 块必须能被 `JSON.parse` 解析——对自己产物用同一把尺子）。
`gold_params_ref`/`forbidden_conclusions` 的取值与本案例在 KB5 §5.4 的 `truth.json.c5_case` 示例逐字对得上
（禁语 token：`field_effective`/`thermal_drift`/`kHz_absent`）：

```json
{"case_id":"T3-PB-INJ01-0007","source_tier":"T3",
 "origin":{"source_tier":"T3","repo":"KB5:P-B","id":"KB5 参数集 P-B / 注入 INJ-01（仓库内可核实，A-67）"},
 "sha256":"<64hex，冻结时填；覆盖输入样本原始字节，A-60/§1.4>","split":"dev",
 "features_sha256":"<64hex，KB5 §5.4 self_check；附加字段，只作管线回归定位，非案例身份>",
 "fs_hz":8000.0,"reliable_band_hz":3200.0,
 "present_channels":["pos_cmd","pos_fb","fe","vel_cmd","vel_fb","cur_q","temp"],
 "sensor_config":"motor_side","counts_per_mm":50000.0,
 "events_present":false,"sync_verified":null,
 "segments_kinds":["move","settling","dwell","probing","rest"],
 "injected_fault":{"kb5_inj":"INJ-01","kb0_slug":"mechanical_resonance"},
 "expected_verdict_class":"mechanical_resonance",
 "expected_not_evaluable_min":0,
 "gold_params_ref":{"path":"<样本包目录>/truth.json#c5_case.gold_params","sha256":"<64hex，冻结时填>","note":"只写引用不复制数值（A-58）；载体=KB5 §5.4"},
 "forbidden_conclusions":["field_effective","thermal_drift","kHz_absent"],
 "counterfactual_variants":[
   {"zeta_m":"0.02 → 0.5","期望结论翻转":"refuse_insufficient_data","出处":"KB5 §1.2 ζ_m≳0.5 峰被抹平，R-03 应不触发"},
   {"lambda":"6.2 → 0.01","期望结论翻转":"refuse_insufficient_data","出处":"KB5 §1.2 配对间距 0.5%，pair_separation_bins<2 判不可分辨（C2 规则 10）"}],
 "human_baseline_labels":{"status":"pending"}}
```

对应**孪生的过频带案例**（同注入、换到 P-A 的 fs=1000）期望完全不同：

```json
{"case_id":"T3-PA-INJ01-0007","source_tier":"T3",
 "origin":{"source_tier":"T3","repo":"KB5:P-A","id":"KB5 参数集 P-A / 注入 INJ-01（仓库内可核实，A-67）"},
 "sha256":"<64hex，覆盖输入样本原始字节（A-60）>","split":"dev",
 "features_sha256":"<64hex，附加字段，非案例身份（A-60）>",
 "fs_hz":1000.0,"reliable_band_hz":400.0,
 "present_channels":["pos_cmd","pos_fb","fe","vel_fb","temp"],
 "sensor_config":"motor_side","counts_per_mm":5.8349,
 "events_present":false,"sync_verified":null,
 "segments_kinds":["move","settling","dwell","probing","rest"],
 "injected_fault":{"kb5_inj":"INJ-01","kb0_slug":"mechanical_resonance"},
 "expected_verdict_class":"refuse_insufficient_data",
 "expected_not_evaluable_min":1,
 "gold_params_ref":{"path":"<样本包目录>/truth.json#c5_case.gold_params","sha256":"<64hex>","note":"只引用不复制（A-58）"},
 "forbidden_conclusions":["field_effective","thermal_drift","kHz_absent","sub_quantum_mm_claim"],
 "counterfactual_variants":[],
 "human_baseline_labels":{"status":"pending"},
 "_note":"kHz 峰在此 fs 下进 blocked_rules=[R-03,R-04]；声明 45 Hz 绳索模态的另一种『看不见』须写成 not_exited(指令低通 8 Hz)；两者都禁写『未发现谐振』（KB5 §2.1 红字 / C2 规则 7 / A-65 正面红线）。counts_per_mm=5.8349 → position_quantum_mm=0.1714 mm（派生不单列，A-66），µm 级声明被禁，故禁语含 sub_quantum_mm_claim（§1.5）。"}
```

---

## 2. 覆盖矩阵：22 slug × 最低通道/频带/事件条件

每格标注该 (slug, tier) 是否有**至少一个**可生成案例。图例：
`✅` 有案例；`⚠` 条件性/仅纪律类（不计入能力命中）；`—` **空格（无案例可填）**；
`⛔` **结构性真空（已裁）**——A-64/A-65 裁"不造案例、不假装覆盖"，空格是**裁决结果**不是待闭合的缺口，
补它需要的是**数据**（见 G-4/G-5），不是实现期工程。

列含义：**通道需求**=判据所依赖的 C2 特征需要哪些 C1 通道；**频带**=需要的最低 `reliable_band_hz`；
**事件/构型**=是否要求 `events.jsonl`/`sync.verified`/`sensor_config` 具体值。

### 2.1 主矩阵

| slug | 通道需求（C2 依赖） | 最低 reliable_band | 事件/构型需求 | T3 | T2(文献参数) | T1-a(DaRUS) | T1-b(外部故障) |
|---|---|---|---|---|---|---|---|
| mechanical_resonance | cur_q+vel_fb+fe（resonance.candidates 四条件） | ≥2000（R-03/R-04，KB0 §1）；低频<400另计 | `sensor_config ∈ {motor_side,load_side}` 才用顺序项；`unknown`/`mixed` 不评＋置信度封顶（A-68） | ✅ P-B | ⚠ 文献阈值合法 | — | ⚠ 仅 family 级（A-63，⟹G-2） |
| mechanical_backlash | pos_cmd+pos_fb（reversal/换向段） | 无特殊 | 需含反向 move/settling | ✅ | ⚠ | ⚠ 门控/方向符号可验，非故障真值 | — |
| mechanical_friction_stiction | fe+vel_cmd（friction_stiction_ratio） | 无 | 需 probing/dwell 起动 | ✅ | ⚠ DaRUS LdaFricIdent 锚 | ⚠ 特征层验证 | — |
| mechanical_crawling | fe+vel_fb（crawling.low_speed_segments） | 无 | 需 probing 恒低速 | ✅ | ⚠ | ⚠ 特征层验证 | — |
| mechanical_encoder_periodic_error | pos_fb+probing/path（encoder.*） | 无 | 需每转信息(motor_rev_counts) | ✅ | ⚠ | ⚠ 三位置通道→sensor_disagreement | — |
| mechanical_loose_structure | cur_q+fe（第二低Q候选） | 视模态频率 | 并联支路；KB5 §1.2 禁无依据生成 | ✅ INJ-03 | — | — | — |
| mechanical_thermal_drift | temp（thermal_drift/…_correlation_r） | 无 | 需长 dwell+temp（**手头无 ≥30 min 冷→热机 `temp`+`fe` 同采**，A-64） | ⚠ 只测temp缺失→unavailable | ⛔ 结构性真空(已裁A-64) | ⚠ 热相关漂移（非归因） | ⛔ 同上(A-64) |
| mechanical_double_inertia | cur_q+vel_fb+两路反馈 | ≥2000（R-04） | sensor_config 决定顺序项（C1 派生规则 7；P-B2/INJ-30 改标 `mixed`，A-68） | ✅ P-B/P-B2 | ⚠ | — | — |
| electrical_current_loop_bandwidth | cur_q+vel_fb（bandwidth.*） | 需覆盖 f_i≈1.2k→300 | drive.current_loop_bandwidth_hz（A-42） | ✅ INJ-08 | ⚠ | — | ⚠ 无位置通道，仅电流侧 |
| electrical_velocity_pi_detune | fe+cur_q（limit_cycle*） | 无（环内<400多） | 需 move/settling | ✅ INJ-12 | ⚠ | — | — |
| electrical_position_pi_detune | cur_q（rest 段持续啸叫） | 需覆盖交越频点 | 需 rest 段 | ✅ INJ-13 | ⚠ | — | — |
| electrical_feedforward_mismatch | fe+pos_cmd+accel 已知 | 无 | 需已知指令形状（KB5 §4.4） | ✅ INJ-09 | ⚠ | ⚠ kff=1.5 前馈失配特征 | — |
| electrical_torque_ripple | cur_q（spectral.cur_q.harmonic_ratios） | 需覆盖 6k±1 | probing/dwell | ✅ INJ-11/20 | ⚠ | — | ⚠ 三相电流真值可分 |
| electrical_motor_heating | temp+cur_q_rms_pct（…_correlation_r；`*_pct` 分母受 A-70 ⟹§1.5） | 无 | 需全程温升时间尺度（**缺 ≥30 min 冷→热同采数据**，A-64） | ⚠ 只测降级 | ⛔ 结构性真空(已裁A-64) | ⚠ | ⛔ 同上(A-64) |
| electrical_resolution_quantization | pos_fb（quality.quantization_step_counts） | 无 | 需 rest/probing | ✅ INJ-10 | ⚠ | ⚠ DaRUS 量子 0.171mm | — |
| software_induced_host_thread_jitter | fe+events（event_context.host_pause*） | 无 | **events必写**（区分唯一依据） | ⚠ 管线+拒答 | — | — | — |
| software_induced_interp_buffer_underrun | fe+events（interp_underrun*） | 无 | events必写；仅 path 段 | ⚠ | — | — | — |
| software_induced_bus_cycle_miss | pos_cmd/vel_fb/cur_q+events | 无 | events必写；A-45 三条件才可进 hypotheses | ⚠ | — | — | — |
| software_induced_late_vision_result | vision_*+events | 无 | events必写 | ⚠ | — | — | — |
| software_induced_pulse_eq_overwritten | counts_per_mm+events(scale_changed) | 无 | events必写（孪生 ⟹§2.2/A-61）；`unit_scale_mismatch` **只作 `truth.json` 侧记账标签**（A-69 已裁），可观测形式＝已登记的 `*_mm`/`*_counts` 比值跳变，本行不得把它当特征路径/证据字段 | ⚠ | — | — | — |
| software_induced_settle_window_too_short | fe+io_bit.settled+events | 无 | events必写；settling截断 | ⚠ | — | — | — |
| software_induced_polling_latency | quality.dt_jitter_ratio | 无 | events必写；>0.2落红线→refuse | ⚠ | — | — | — |

**读表要点**：软件诱导族整行 T1-a/T1-b 都是 `—`。这是本项目的诚实命门——**差异化能力（软件族）没有外部真值**，
只由 T3 管线 + 拒答纪律考核，因此按 C5 §1 硬规则（能力指标只能来自 T1+T2）**软件族不得进任何对外命中率**。
主线程已把这一类连同"kHz 判据在 T1-a 上无正例"**裁定为结构性真空、写进拒答纪律而不是造案例**（A-53 ⟹ A-64/A-65），
所以整行 `⚠/—/⛔` 是设计事实，不再是"待闭合缺口"。

### 2.2 硬性配额检查

| 硬性要求（任务点名） | 满足方式 | 状态 |
|---|---|---|
| 7 个 `software_induced_*` 各配"含事件流"+"无事件流"孪生，无事件那份期望=`co_occurrence_only` 或 `refuse`（**不得归因**） | **已裁（A-61，原 §7-H/G-6）：不豁免，7 个软件 slug 全部产孪生**（含 INJ-19/INJ-21）。KB5 §3.3 已把孪生表扩成 **7×3**：每 slug 三份——含事件（母）/ 无事件（`no_events`）/ 未同步（`unsynced`），**三份波形 sha256 必须相同**（只改元数据与事件流，不改波形）。豁免 INJ-19/21 ＝承认"这两个 slug 的'没有事件流就不许归因'从未被测过"，而 C2 规则 8 的门禁恰恰是全 7 个 | **7/7 有据**（旧"5/7，INJ-19/21 见 §7-H"作废；孪生缺失三份 ⟹ 该案例整批作废，KB5 §5.5 P-12） |
| ≥15% 案例期望=`none_of_the_above` | INJ-25（健康对照）+ 全部 `starved_*` 投影 + `declared_detectable=false` 注入 + **T1-a DaRUS 健康受试对象**（C5 §1"非故障数据"天然 none_of_the_above） | 可满足；比例在 `manifest.jsonl` 统计核验（KB5 §5.6 目标 15–20%） |
| ≥4 例"仅有波形、无事件上下文" | T1-a DaRUS（TwinCAT Scope 原始导出无 events.jsonl）⟹ 每条都是 waveform-only；再叠 T3 软件族无事件孪生 | 可满足且富余 |
| ≥3 例超频带（reliable_band 低于判据下界，期望=拒答+登记 blocked_rules，**禁止**"未发现谐振"） | T1-a DaRUS fs=1000→reliable_band=400<2000（天然 3+ 条）；T3 P-A 同；P-C3 是守门案例（KB5 §2.3） | 可满足；A-65 已裁：kHz 类判据的这类案例是**结构性真空的正面红线落地形态**（`unavailable`+`blocked_rules`），不是待补的能力例 |
| ≥3 例 `counts_per_mm == null`（考 µm 臆造，对应 C2 规则 11 / `position_quantum_mm`） | KB5 §5.6 `starved_scale` 变体（INJ-28 家族） | 可满足 |
| ≥2 例 `sensor_config == unknown`（考不知构型时硬用 `f_anti<f_res` 顺序判双惯量，A-1） | **已裁（A-62，原 §7-I/G-7）：KB5 §5.6 增补 `unknown_config` 投影变体**——把 P-B / P-B2 / INJ-29 的已知构型**重标为 `unknown`**，**数据与 sha256 不变、只改元数据**；考的就是"不知构型时硬用顺序判双惯量"这一具体错误（A-1）。与 A-68 的 `mixed` 投影**同批生成**（P-B2/INJ-30 从临时 `unknown` 改标 `mixed`） | 已裁闭合（生成侧）：旧"部分缺口：需显式生成，见 G-7"作废；KB5 §5.6/P-14 的回写落地见 §7 末尾跟踪 |

### 2.3 空格清单（矩阵里没有案例可填的格 / 配额未闭合项）

编号 `G-*`，逐条给出为何为空与所需外部动作（**本文件不去改别人的文件，只登记**）：

- **G-1（软件族 7 slug × T1-a/T1-b/T2 = 21 格全空）**：**结构性事实，已由 A-53 裁认定**——无任何外部真值数据能标注软件诱导缺陷；
  T2 亦空——`host_thread_jitter`/`interp_buffer_underrun`/`bus_cycle_miss`/`late_vision_result`/
  `polling_latency` 这类**调度/总线/上位机**故障缺少可复算的公开故障模型参数（不像摩擦/谐振有文献模型）。
  唯一有 T2 影子的是 `pulse_eq_overwritten`（换算链可被 §1.1 DaRUS 复算佐证，KB5 §1.1）。
  ⟹ 结论：软件族只能进拒答纪律考核，不能进能力命中（C5 §1）。这是设计事实，不是遗漏——写进拒答纪律，不造案例。
- **G-2（T1-b 机械↔电气分类的"具体 slug"未定）**：CWRU/Aalto 是**轴承/齿轮**故障，Paderborn 是**电机三相电流**，
  与本项目 22 个"伺服轴控制级"slug **不是一一映射**（轴承外圈缺陷 ≠ `mechanical_encoder_periodic_error`，也 ≠
  `mechanical_loose_structure`）。⟹ T1-b 目前只能支撑"机械 vs 电气"的**二分类维度**（C5 §1 T1-b 明示），
  映射到哪个 slug 曾悬置上报（§7-J），否则 §3 的 Top-1 分母会静默错位（对齐 A-19）。
  **已裁：A-63 —— T1-b 只计"机械↔电气"二分类命中率，禁止映射到 22 个 slug**；T1-b 案例的
  `expected_verdict_class` 取 `family` 级（⟹§1.1/§3），轴承内圈点蚀的真值**不是** `mechanical_backlash`，硬挂钩必错位分母；
  T1-b 的对外角色是"本族判据的通用故障检测力有外部数据支撑"，**不是**"22 个 slug 都有外部真值"。
- **G-3（mechanical_loose_structure 无 T1/T2）**：KB5 §1.2 禁止无拟合依据生成 ≥2 并联支路，且无现场模态 survey
  （KB5 §6.1）⟹ 只有 T3 INJ-03 一条管线例，能力层为空。
- **G-4（mechanical_thermal_drift / electrical_motor_heating 的 T3 正例被禁）**：KB5 §6.1"不得用任何 T3 样本支撑热漂移/
  蠕变/冷热机差异"⟹ 这两 slug 的 T3 只能测"temp 缺失→unavailable"，正例只能来自 T1-a 热相关漂移（仍非归因，⚠）。
  **已裁：A-64 —— 结构性真空，不造案例、不假装覆盖**。三条通路都堵：T3 被 KB5 §6.1 禁用于能力主张；T1-a 只给
  热相关漂移而无归因真值；T2 落地需 **≥30 min 冷→热机 `temp`+`fe` 同采**（手头无）。⟹ 这两 slug 只出现在
  `differential.not_evaluable` 与拒答表里（**禁止"未发现异常"**），`in-capability` 声明不得出现；
  要补的是**数据**（长期数据缺口），**不是实现期能修的债**——与 G-1/G-5 同批由 A-53 裁认定。
- **G-5（kHz 级 mechanical_resonance / mechanical_double_inertia 无 T1 正例）**：DaRUS fs=1000 无法表 kHz（C5 §1 T1-a、
  KB5 §1.4 红字）；T1-b 无位置通道。⟹ R-03/R-04 的合法性"只能来自 T1-b/文献"（KB5 §6.1），但 T1-b 又不映射（G-2），
  原以为二者直接冲突。
  **已裁：A-65 —— 同为结构性真空，并转成一条正面红线**：T1-a 是 1 kHz ⟹ Nyquist 500 Hz ⟹ `reliable_band_hz = 400 Hz`，
  电流环带宽/换刀频率类 kHz 判据**在数据层面不可达**——这不是阈值松紧问题。报告只能说"该判据在 T2 文献上成立，
  本数据集频段不足以检验"（`unavailable` + `blocked_rules`），**禁止**说"未发现异常"——这正是频段门禁存在的理由
  （A-11/任务 #11 收口，C5 §9 kHz 类行同款纪律）。与 G-2 的"冲突"由 A-63 消解：T1-b 改 family 级二分类后，
  kHz 判据**不再试图借 T1-b 出 slug 级正例**，对外只剩 T2 文献合法性叙事，无静默错位。
- **G-6（INJ-19/INJ-21 的无事件孪生缺显式生成依据）**：**已裁：A-61 —— 不豁免，KB5 §3.3 孪生表已扩成 7×3**
  （含事件/无事件/未同步三份，波形 sha256 必须相同）⟹ §2.2 首行。
- **G-7（sensor_config=unknown 显式变体缺）**：**已裁：A-62 —— KB5 §5.6 增补 `unknown_config` 投影变体**
  （P-B/P-B2/INJ-29 已知构型重标 `unknown`，数据与哈希不变只改元数据），与 A-68 的 `mixed` 同批 ⟹ §2.2 末行。
- **G-8（electrical_current_loop_bandwidth 的 T1 覆盖空）**：Paderborn 无位置环信息、DaRUS 发布 `current_loop_bandwidth`
  未知（C1 `drive.current_loop_bandwidth_hz` 常 null，A-42 支路 B 降 unverified）⟹ 只有 T3 INJ-08 + T2（若厂商手册给 f_i）。
- **G-9（约定/接线真值类：本数据集结构性无覆盖，A-87；分档与闭合路径按 A-89 修订）**：
  方向位号编码（`dmc_vmove` 的 0/1 哪个是正）、停止方式编码、IO 位号↔端子、PSO 比较源（cmd 还是 fb）、
  锁存来源、手册未明写的占位填法——
  这些量的真值**不在波形里、不在仿真里**，在厂商手册与现场接线表里。KB5 按约定 A 造模型、再用同一条约定自检
  ⟹ 同义反复，**跑通多少条都不算覆盖**（与 G-1/G-4 不同族：那两格是"数据假"，这格是"真值压根不在数据层"）。
  ⟹ 本文件的处置：**不造正例**（造了就是拿自家约定当外部真值，A-87 违规），改为**三类可考核的形状**——
  ①"约定真值缺失 ⟹ 期望 `not_evaluable`/`refuse`"的案例（配额见 §6 表末行，走 `family: null` 的门禁路径，
  与 A-86 的门禁三例同机制）；②**执行/跳过分开计数**的红线（§6 表末行下方的口径段）：
  任何"需真机/需外部输入"的用例被 skipped 时不得计入通过数；
  ③**（A-89 新增）③a/③b 分档正确性**——给定一条接口事实，考核的是它被判成
  "文档可查（该去查工件，不该等回信）"还是"批次与现场（该问厂商，且要举证手册为什么答不了）"，
  以及引用是否落到 `external_reference = official-artifact:<工件@版本 clause>` 而非"一般常识"。
  这一类**有正例可考核**（判档与引用格式是确定性的），但正例的答案键来自 KB0 §4 阶梯，不来自波形数据。
  对外能力主张里第 ③ 层只能出现在**拒答与待确认清单**中；R-22 签名表末列的 L1→L6 动作属于 C6 §5 的人工流程，
  不是本 agent 的执行范围（`safety.writes_to_device` 恒 false）。

---

## 3. 三层证据数据集映射表

对齐 KB0 §4 tier 表与 C5 §1 表；每行写清"能支撑哪几条判据、不能支撑什么、发布许可/署名要求"。

| tier | 数据集/来源（简称，不写 DOI） | 能支撑的判据（本项目） | 不能支撑（必须拒答/进 not_evaluable） | 发布许可 / 署名要求 |
|---|---|---|---|---|
| `T1-a` | **DaRUS**（斯图加特大学；`doi:10.18419/DARUS-3600` + `doi:10.18419/DARUS-5171`，两包均 CC BY 4.0，KB7 已登记 ⟹**A-67 回填**；绳索驱动+直驱试验台，32/40 通道，三套独立位置测量，fs=1 kHz） | 解析器正确性、触发门控、方向符号、`ripple.probing`恒速纹波、`friction_stiction_ratio`、`crawling.*`、`ff_mismatch.*`（kff=1.5）、`sensor_disagreement`交叉验证、滑移、热相关漂移；**过频带拒答纪律的活教材**（fs=1k ⟹ R-03/R-04 天然 blocked） | **kHz 级共振（奈奎斯特 500 Hz，物理不可能表 kHz 峰，C2 规则 7；A-65 已裁结构性真空：只写 `unavailable`+`blocked_rules`，禁"未发现异常"）**；故障归因（受试对象健康，非故障数据）；半导体设备外推；µm 级精度（`position_quantum_mm=0.171 mm`，C2 规则 11）；热**归因**（A-64：热相关漂移 ≠ 归因真值，该二 slug 能力层结构性真空） | CC BY 4.0：署名 **Reichenbach, Thomas — University of Stuttgart（ROR 04vnq7t77）+ DOI + 许可**（KB7 署名规则）；引用 `counts_per_mm=5.8349` 等只作"比例关系成立"证据，**禁止**印 µm（KB5 §1.1 限定）；`torque_max=32` 一律按 `assumed` 引用（A-27 ⟹ A-70 分母纪律，§1.5） |
| `T1-b` | **CWRU 轴承 / Paderborn CM 三相电流 / Aalto 齿轮 / MFPT**（外部故障真值，有论文与试验台背书，C5 §1） | 频谱特征提取、模态识别、**机械 vs 电气故障归因的二分类能力（A-63 已裁：T1-b 案例的 `expected_verdict_class` 取 `family` 级，命中率的 T1-b 分母只按"机械↔电气"二分类计，不进 22-slug 的 slug 级 Top-1 分母）** | 位置环/跟随误差/整定建议（无位置通道）；具体 22-slug 映射（**A-63 禁止**——轴承内圈点蚀的真值不是 `mechanical_backlash`，硬挂钩必让 Top-1 分母静默错位，A-19；⟹G-2）；kHz 之外的伺服控制参数类判据 | KB7 **未登记** CWRU/Paderborn/Aalto/MFPT 的可核实标识 ⟹ `origin.id` 一律 `[待核]`，**不凭记忆填 DOI、不猜 URL**（A-67 红线）；各数据集按其原发布条款引用，取得可核实标识前不得对外成文 |
| `T1-c` | **自采标定台（有条件，A-24 / C5 §1）**：自建网格工装+真实相机+真实轴+自记温度序列（属标定/耦合域，载体为 C7 `calibration.jsonl`/`process.json`，非 C1 波形） | 标定残差场形态、方向性分量、温漂相关性——**仅标定/几何子域** | **不是产线数据**；不得与 T1-a/T1-b 混算能力指标（A-24）；伺服波形判据一律不适用 | 自采：本项目署名；**若拿不到工装则该 tier 整行作废**，标定模块必须如实声明"只有 T2+T3"（A-24）。**截至落盘：尚未取得，条件行悬空，禁止计入任何指标分母** |
| `T2` | **文献/厂商阈值**（判据阈值与故障模型参数取自公开文献/厂商手册，不取本项目仿真器默认值，C5 §1；摩擦/陷波 T2 锚点战役名见 KB5 §1.3/§7.6） | 阈值合法性、能力指标分母（T1+T2 才有命中率资格）；换算链复算合法性（KB5 §1.1）；kHz 判据**唯一合法的对外叙事来源**（A-65：数据层不可达，只能说"判据在 T2 文献上成立、本数据集频段不足以检验"） | 现场有效性；任何 µm/绝对量级真值；转矩百分比判据的**绝对刻度**——分母须有 `rated_torque_source`（A-70）：`assumed` 档 ⟹ 证据层级封顶 T2 + 强制 caveat（⟹§1.5），"T2 合法"不等于百分比刻度可信。**T2 案例波形仍多为合成，只是参数出处=文献**（`provenance="T2: …"`，KB5 §5.4） | 引用文献须逐参数 `param_source`/`provenance` 标注（KB5 §1.3）；厂商签名一律标 `public-doc`，**不得**写"已对照官方手册原文核对"（A-31/A-32） |
| `T3` | **本项目合成（KB5）**，带 `truth.json` | **仅**端到端流程跑通、回归不退化、覆盖率、拒答纪律（无事件孪生、超频带、缺定标、缺通道的"该怎么写'看不见'"） | **任何"诊断准确/检出率/命中率"主张**（C5 §1 / KB5 §0.1）；热/蠕变/结构模态/总线抖动统计（KB5 §6.1/§6.2；热型两 slug 即 A-64 结构性真空，只以 `not_evaluable`+拒答出现，禁"未发现异常"） | 内部基准；`claims_forbidden` 字段 + `source_tier=="T3"` 让 CI 机器式拒绝把 T3 计入能力指标（KB5 §5.4；truth.json 侧现仍写作旧名 `evidence_tier`，A-54 后统一，KB5 侧回写跟踪见 §7 末） |

`[P]` T1-a↔T3 的直接对话仅两处合法（KB5 §6.4 明写）：`ff_mismatch.fe_vs_accel_corr` 在 kff=1.5 时应为负（KB5 §4.4 预言2）、
`asymmetry_ratio<1` 在 kff>1 时（预言3，比预言2 更稳）。除此之外**不得**用 T3 结果去"印证"T1-a 结论。

**命中率分母的定义（A-63 落点，防止分母静默错位）**：slug 级 Top-1/Top-3 分母只收"gold 是具体 slug"的案例
（T1-a/T1-c/T2/T3；T3 只进"流程正确性"章节不进对外数字，红线 4）；**T1-b 案例一律走 family 级（机械↔电气）
二分类分母**，不进 slug 级分母、也不得被折算成"≈某个 slug 的命中"。两套分母分开报告、禁止合并总数（C5 §1 同款纪律）。

---

## 4. 污染红线（违反即拒收 / 重划）

1. **真实样本包内出现 `truth.json` 即为污染 ⟹ loader 拒收并报错**（C1 §目录结构；KB5 §0.3/§5.4）。
   校验式：`truth.json` 存在 ⇔ `meta.source.vendor == "axiscope-synth"`（KB5 §5.4）。真值一旦与真实测量混放，
   评测会在不知不觉中被答案污染——这是反自验证的结构性闸门，不是可选检查。
2. **dev/hidden 划分 + sha256 冻结后不得追加案例**。追加即全量重划、版本号 +1、公开前后差异
   （C5 §2"针对隐藏集失败案例改规则 ⟹ 追加新版本号并重跑全量"）。目的：**防止调完参数再拿同一批 hidden 案例报成绩**
   ——这正是 C5 §0 点名的循环论证。`bench/hidden.sha256` 冻结的是 §1.4 定义的**输入样本字节摘要**。
3. **`features()`/`rules()` 代码路径禁止读 `truth.json`**（KB5 §0 反向要求 + §5.7 等价性测试）：注入真值到判据之间
   的唯一通道是"真值→物理量→波形→C2 特征→规则"，不存在"真值→规则"捷径。案例目录行（`cases.jsonl`）与样本包分离存放，
   评测比对只在**事后**进行，且结果只进"流程正确性"章节（C5 §1）。
4. **T3 合成案例禁止进入任何对外准确率声明**（C5 §1 硬规则）：报告首页的"证据层级声明表"须让每个数字标出来自哪一层；
   T3 数字只允许出现在标题写明"合成集，不用于能力主张"的章节。
5. **规则阈值/参数改动与 hidden 集解耦**：调提示词、调规则阈值、挑模型一律不得看 hidden（C5 §2）。
   若必须为 hidden 失败案例改规则 ⟹ 触发红线 2 的重划，不允许原地复用。

---

## 5. 人工基线协议（C5 §5；最贵的一步，**尚未完成**）

> **诚实声明**：截至本文件落盘，人工基线**尚未招募标注者、尚未产出任何人标结果**。以下只是协议，
> 不是已完成事项。`cases.jsonl` 中每一条的 `human_baseline_labels` 现为 `{"status":"pending"}`。
> C5 §5 的降级方案（找不到 2 位工程师时"只报 agent 自身指标 + 明确写无人工基线、绝对数值不可横向比较"）
> 目前是**默认状态**。禁止给出任何"已有基线"的暗示（A-31）。

流程图（协议，非实现）：

```
[1] 冻结案例集(dev+hidden, sha256) ──► [2] 抽样人工核查用案例子集（T1+T2 为主，含波形图/C2快照）
                                              │
        招募 ≥2 名做过伺服调试的工程师 ───────┤（找不到→走降级：不做人标，报告首页声明无基线）
                                              ▼
[3] 独立标注（每人单独，互不可见）：
      输入 = 该案例在 split 定义下的**同一份**样本包
        · events_present=true  的案：标注者可见 events.jsonl（否则无法判软件族）
        · events_present=false 的案：标注者也不给 events —— 与 agent 看到的东西逐字一致
        （这是"agent vs 工程师"可比的前提；两侧输入不同 ⟹ C5 §3/§5 的差值无意义）
      产出 = 根因排序（用 KB0 §2 的 22 slug，禁止显示名，A-19）+ 每个的置信度 + 记录耗时
                                              ▼
[4] 分歧仲裁：
      · 两名标注者对"primary slug"不一致 ⟹ 第三名资深工程师裁决（不参与第3步，避免锚定）
      · 三方仍无法就 gold 达成一致的案例 ⟹ 移出 hidden（退回 dev）并标 ambiguous，不得用于命中率
      · gold_params 容差按 KB5 §1.2 解析式（如 f_m/f_a=√(1+λ)）核，不按人记忆核
                                              ▼
[5] 回填 human_baseline_labels.{labels[], adjudicated_gold, inter_rater_agreement, time_s}
      status: pending → done（仅当第4步完成）
                                              ▼
[6] 比较：agent 与工程师在同一批案例上用**同一指标**（Top-1/Top-3 命中率、拒答正确率、ECE，C5 §3），
      报告命中率差 / ECE 差 / 单位案例耗时比（C5 §5）
```

协议要点（可核验）：

- **标注什么**：22 slug 内的根因排序 + 置信度 + `none_of_the_above` 判定；不允许自由文本命根因（否则对不上 C5 分母，A-19）。
- **分歧怎么仲裁**：第三人裁决、不可调和者退集标 ambiguous（防止把"我们自己没共识的案例"算进 hidden 打分）。
- **是否允许看事件流**：按案例 `events_present` 锁定，且**必须与喂给 agent 的输入一致**——事件流是软件族判别的
  唯一依据（KB5 §3.3），人/机看的不是同一份东西就毁掉可比性。
- **同指标比较**：人标结果与 agent 结果都只算 T1+T2 层（C5 §1），绝不与 T3 混算（红线 4）。
- **成本与耗时**：记录工程师耗时是 C5 §5 的明确产出（"单位案例耗时比"），本文件要求第3步就登记时间戳。

---

## 6. 规模与配额建议

C5 §2 定了 60/40，但未定绝对数量。以下给出**能自圆其说**的配额，全部 `[P]`（本项目自定；
§2.3 空格中"可闭合类"（G-6/G-7 等生成侧缺口）按裁决闭合后不再调整，"结构性真空类"（G-1/G-4/G-5，A-53/A-64/A-65）
**不参与闭合**——它们在配额里的正确形态就是拒答/降级专项行，而不是正例）。

**建议总规模 `N = 120`：dev = 72，hidden = 48。** 分解（下限，非精确分布；已按 A-63/A-64 修正旧版"22 slug 正例 ≥44"的自相矛盾——该单元格写 44、依据列公式却算出 30+7=37，且"每 slug 都有正例"与 A-64"热型两 slug 不造正例"、A-63"T1-b 无 slug 级正例"打架）：

| 组成 | 案例数下限 | 依据 |
|---|---|---|
| **13 个机械/电气 slug** 正例 ≥2 档（机械 8 + 电气 7 = 15，剔除热型两 slug——A-64 不造正例；KB5 §5.6 每工况 ≥3 投影取 2 档进目录） | ≥26（13×2） | KB5 §3 注入矩阵；热型两格改由拒答纪律例覆盖（下表） |
| 软件族 **slug 级纪律例** 7（INJ-15..19/21/22 母样本，期望=归因或拒归因） | ≥7 | G-1 设计事实：软件族无能力正例，这 7 条只进"管线+拒答"考核（A-53） |
| 软件族孪生另两态（`no_events` + `unsynced`）补 **7×2=14**，全族共 **7×3=21** | ≥14 | **A-61 已裁：7 slug 全部产孪生、豁免作废**；三份波形 sha256 相同（KB5 §3.3 孪生表 + §5.5 P-12）；无事件那份期望 co_occurrence/refuse |
| `none_of_the_above`（INJ-25 + starved_* + declared_detectable=false + **DaRUS 健康**） | ≥18（≥15%）| C5 §2/§4；KB5 §5.6 目标 15–20% |
| 过频带（reliable_band<判据下界）≥3 | ≥3 | C5 §2；DaRUS/P-A/P-C3 天然；判据按 A-65 正面红线：`unavailable`+`blocked_rules`，禁"未发现异常" |
| 仅有波形无事件上下文 ≥4 | ≥4 | DaRUS waveform-only + 软件族无事件孪生 |
| `counts_per_mm=null` ≥3 | ≥3 | KB5 starved_scale |
| `sensor_config=unknown` ≥2 | ≥2 | **A-62 已裁**：KB5 §5.6 `unknown_config` 投影（P-B/P-B2/INJ-29 重标，数据/哈希不变）；`mixed`（P-B2/INJ-30，A-68）同批生成 |
| 混淆/叠加专项（INJ-26 谐振↔前馈、INJ-27 多故障叠加、INJ-29/30 R-04 反例——后者按 A-68 走 `mixed` 语义） | ≥8 | C5 §6 点名混淆对；KB5 §3.4 |
| **热型两 slug 的拒答/降级专项**（`mechanical_thermal_drift`/`electrical_motor_heating`：temp 缺失→unavailable、`not_evaluable` 登记、禁"未发现异常"；**非正例，不进任何命中分母**） | ≥2 | **A-64 已裁结构性真空的落地形态**；能力层数据缺口（≥30 min 冷→热同采）另行登记 ⟹G-4 |
| **KB6 门禁类三例**（`R-37` 无产线数据外推 / `R-49` 残差超验收限 / `R-50` SPC 未分段，均 `family: null`） | ≥3 | C3 硬性规则 11/12（门禁是一等公民，进 `audit.rules_fired` + `not_evaluable`，**不进** `hypotheses[]`）；期望形状 `none_of_the_above` 或 `refuse`，计入 C5 拒答正确率。**A-86**：本文件此前**完全没有** `R-31…R-50` 的任何案例行——KB6 的 20 条工艺/标定规则与基准集零交集，等于"门禁纪律从未被考核"。现先补门禁三例（它们是最容易被 agent 越权下结论的三条），其余 `R-31…R-48` 的案例归属实现期，登记在 **KB6 §D 待办**（不在本文件的本期配额内） |
| **约定/接线真值缺失专项**（方向位号、停止方式编码、IO 位号↔端子、PSO 比较源、锁存来源、手册未明写的占位填法；均 `family: null`，对应空格 **G-9**） | ≥4（拒答形）+ ≥2（**A-89 新增**：③a/③b 分档形） | **A-87 + A-89**。这类格**不造波形正例**——波形正例只能来自厂商手册/接线表，用自家约定的仿真造一个"方向反了"的案例再让规则去检出，等于把约定当外部真值（同义反复）。可考核的形状有三种：**(1) 拒答**——期望 `not_evaluable`/`refuse`，报告必须写"该判据依赖厂商手册/接线表中的位号定义，未经外部确认"，`basis` 封顶 `rule_heuristic`（C4 补充约束、KB3 §0 纪律 15）；**(2) 分档（A-89）**——给定一条接口事实，期望输出把它判成 ③a（文档可查，该去核工件、**不该写进向厂商索要的清单**）或 ③b（批次与现场，该问厂商且须举证手册为什么答不了），KB0 §6 检查 21；**(3) 引用格式**——升格声明必须落到 `external_reference = official-artifact:<工件@版本 clause>` + `verified_by = self`，落不到即维持 `public-doc`，第三方会话的转述**不计入 `已核对 k`**。上述三种形状均计入 C5 拒答/措辞正确率，**不进任何命中分母**。（A-89 的经验依据：第三方实现取得官方手册与绑定后，把绑定抽成清单即机器抓出三个"真机即崩"缺陷，并把"必须问厂商"的条目从 9 项收缩到 3 项——说明 ③a 的闭合路径真实存在，把 ③a 挂在等待里是登记错误） |

**通过数口径（A-87，与上表配套）**：本文件的案例执行统计必须**分列**"执行 N / 跳过 M"，
凡标注"需真机 / 需厂商手册原文 / 需现场接线表 / `skipped` / `pending`"的用例**不得计入通过数**。
触发这条纪律的事实来自第三方实现的一轮自审：它把唯一能抓适配器方向写反的那条用例（需真机执行）
并进了"74 项测试全绿"——绿色数字里含从未执行的格子，等于把缺证据落在启用侧（同 A-71"缺行按最低档"）。
作品集里这一条要显式呈现，不许合并汇总。

按 family 的**能力配额下限**（进 T1+T2 命中率分母的资格；分母定义见 §3 末"A-63 落点"段）：
`electrical_torque_ripple` 的 T1-b 三相电流影子**只支撑 family 级（机械↔电气）二分类资格，不作它 slug 级
Top-1 配额的依据**（A-63 已裁——旧写法"T1-b 影子，≥1"混用了两套分母，已修正；其 slug 级资格回落
T2 文献参数 + T1-a 特征层 ⚠）；`mechanical_resonance`/`mechanical_double_inertia` 的低频段
（<400 Hz，DaRUS 可行，≥1）；其余 slug 能力层暂依赖 T2 文献参数（§3 T2 行）。**软件族能力配额=0**（G-1，设计事实，
A-53 确认）；**`mechanical_thermal_drift`/`electrical_motor_heating` 的 slug 级能力配额=0**（A-64：结构性真空，
只能以拒答/降级专项出现）。**T1-b 案例整体只进 family 级分母，不占 slug 级配额**（A-63）。

**为什么 hidden 集要小但要冻结**：
- hidden 是**唯一诚实的留出集**。它越大，dev 侧可调的数据越少；且大 hidden 让人有动机反复"看失败→改规则→重跑"，
  每一次都在偷看答案（C5 §0 的循环论证）。48 条已足够覆盖 13 个正例 slug 各 ≥2 + 软件族 7 纪律例 +
  T1-b family 级例 + 全部拒答/超频带/缺定标专项（旧写法"22 slug 各 ≥2"与 A-64/A-63 打架，已修正——
  热型两 slug 的正例**不存在**，T1-b 也不按 slug 计），统计噪声用
  "按 tier 分层报告、禁止合并总数"（C5 §1）来控制，而非靠堆样本量。
- "小"必须配"冻结"才成立：一旦冻结，`bench/hidden.sha256` 锁死，任何追加触发全量重划（红线 2）。
  冻结的价值不在条数，而在"调完参数不能再拿同一批 hidden 报成绩"这条纪律——**条数少反而让"重跑全量、公开前后差异"可负担**，
  纪律才落得了地。dev=72 承担迭代，hidden=48 只承担一次性诚实评估。

---

## 7. 曾提交的跨文件裁决项（14 条，**已全部落裁**：KB0 §7.3，A-54…A-67；本 section 保留原文留痕）

裁决结论已回写进正文各节（逐处标注 A-NN）。下表"原事项"列保留当初提出的问题描述——**不抹掉提出问题时的
思路**是本仓库惯例；"裁决"列为 KB0 §7.3 结论与本文件落点。本文件未改任何他人文件，其他文件的回写状态见本节末"跟踪"。

| # | 原事项（留痕） | 裁决（A-NN）——结论 ⟹ 本文件落点 |
|---|---|---|
| §7-A | C5 §2 用 `evidence_tier`，KB0 §4/本文件用 `source_tier`。命名需统一 | **已裁：A-54 —— 权威名 = `source_tier`**，值域不变（T1-a/T1-b/T1-c/T2/T3）；C5 §2 已就地改名（现文标注旧名作废），中文说"证据层级"不算违反 ⟹§1.1/§1.3 |
| §7-B | C5 §2 `channels_present[]` vs C1/C2 权威 `present_channels[]` 词序相反 | **已裁：A-55 —— 通道清单逐字用 C1 的 `present_channels`**；目录行必须能与 loader 产出的 `meta.present_channels` 逐字对拍，否则冒充检测（C2 规则 15）与频段门禁失去参照 ⟹§1.1/§1.3 |
| §7-C | C5 §2 `counts_per_mm_known(bool)` vs C1 `counts_per_mm(float\|null)`；本文件用后者以直接喂 `position_quantum_mm` | **已裁：A-56 —— 可空数值 `counts_per_mm`，与 C1 同型**；布尔丢了"是多少"，写 `null` 才让 A-13 定标缺口在案例层可见。注：A-56 原文的"`si_native` 样本写 `null`"分岔已被后续 **A-75 修正**——按"有没有可复算推导链"取值，有链写数值（`5.8349`+`provenance`），**真缺定标才 `null`** ⟹§1.1 |
| §7-D | `difficulty(1-5)` 是否并入 KB8 案例行（C5 §2 有、本文件 §1.1 未列） | **已裁：A-57 —— 不并入**。`difficulty` 留在 C5 §2 作排序/配额属性；KB8 用 `expected_verdict_class`+配额表达难度——同一属性两处可变，早晚会与配额表互相打脸 ⟹§1.1 注/§1.3 |
| §7-E | C5 §2 `gold_params[]` 与本文件 `injected_fault`/`counterfactual_variants` 重叠 | **已裁：A-58 —— 权威载体 = 样本包 `truth.json.c5_case.gold_params`**（KB5 §5.4）；目录行只写引用（`gold_params_ref`：路径+sha256），**不复制数值**——真值必须跟样本走 ⟹§1.1/§1.3/§1.6 |
| §7-F | C5 §2 `forbidden_conclusions[]` 本文件仅隐含 | **已裁：A-59 —— 升为 KB8 必填**，取值自 KB5 §5.4/§6.3；`expected_verdict_class` 判"说对没有"，禁语判"有没有说过分的话"，C3 规则 14 的评测侧对偶 ⟹§1.1/§1.6 |
| §7-G | §1.4 sha256 冻结的是**输入样本字节**，而 KB5 §5.4 `features_sha256` 是 **C2 输出字节**；两者关系未契约化 | **已裁：A-60 —— 冻结哈希覆盖输入样本原始字节**；`features_sha256` 保留为附加字段（只用于特征管线回归定位），**不作案例身份**——身份随管线变＝允许看着管线输出挑案例，A-31 防自证落空 ⟹§1.1/§1.4/§4 红线 2 |
| §7-H | 软件族"无事件孪生"：KB5 §3.3(a)/(b) 只点名 5 项，但 P-12 与任务硬要求覆盖全 7 项（含 INJ-19/21），或豁免并说明理由 | **已裁：A-61 —— 不豁免，7 个软件 slug 全部产孪生**；KB5 §3.3 已把孪生表扩成 **7×3**（含事件/无事件/未同步三份，波形 sha256 必须相同）；豁免＝两个 slug 的"无事件不许归因"从未被测，而 C2 规则 8 门禁是全 7 个 ⟹§2.2/§2.3 G-6 |
| §7-I | `sensor_config == unknown` 的显式案例变体：C1 默认才是 unknown，KB5 未把"已知构型重标为 unknown"列为变体矩阵项 | **已裁：A-62 —— KB5 §5.6 增补 `unknown_config` 投影变体**（P-B/P-B2/INJ-29 重标 `unknown`，数据与哈希不变只改元数据），考"不知构型硬用 `f_anti<f_res` 顺序判双惯量"（A-1）；与 A-68 的 `mixed` 同批生成 ⟹§2.2/§2.3 G-7 |
| §7-J | T1-b（CWRU/Aalto/Paderborn/MFPT）到 22 slug 的映射未定（G-2）：轴承/齿轮/三相电流真值 ≠ 伺服轴控制级 slug | **已裁：A-63 —— T1-b 只计"机械↔电气"二分类命中率，禁止映射到 22 个 slug**；`expected_verdict_class` 取 `family` 级；硬挂钩会让 Top-1 分母静默错位（A-19）；T1-b 对外角色＝"本族判据通用检测力有外部支撑" ⟹§1.1/§2.3 G-2/§3 分母定义段 |
| §7-K | thermal_drift / motor_heating 的能力层真空（G-4）：T3 被 §6.1 禁、T1-a 只给热相关漂移非归因、T2 需长时温漂真值 | **已裁：A-64 —— 结构性真空，不造案例、不假装覆盖**：只出现在 `not_evaluable` 与拒答表（`in-capability` 声明不得出现，禁"未发现异常"）；要补的是**数据**（≥30 min 冷→热机 `temp`+`fe` 同采），列为长期缺口而非实现期可修的债 ⟹§2.1/§2.3 G-4/§6 |
| §7-L | R-03/R-04 的对外合法性"只能来自 T1-b/文献"与 G-2、G-5 直接冲突 | **已裁：A-65 —— 同为结构性真空，转成正面红线**：T1-a=1 kHz ⟹ `reliable_band=400 Hz` ⟹ kHz 类判据数据层不可达；报告只能说"判据在 T2 文献成立、本数据集频段不足以检验"（`unavailable`+`blocked_rules`），**禁**"未发现异常"；与 §7-J 的冲突由 A-63 消解 ⟹§2.3 G-5/§3 T2 行 |
| §7-M | KB5 §7.11/A-13 要求 C5 案例元数据同步 `position_quantum_mm`；本文件 §1.1 未单列该字段 | **已裁：A-66 —— 保持由 `counts_per_mm` 派生、目录不单列**：两载体必打架（`counts_per_mm=2000` 配 `position_quantum_mm=0.0005`），A-13 四量级对照靠单一来源才成立 ⟹§1.1 |
| §7-N | DaRUS/CWRU `origin` 正式标识曾留 `[待核]`（当时未读 KB7），禁止 KB8 编造 DOI | **已裁：A-67 —— 按 KB7 回填，禁止编造**：DaRUS 两包 `doi:10.18419/DARUS-3600`/`doi:10.18419/DARUS-5171`（Reichenbach, Thomas — University of Stuttgart，CC BY 4.0）；CWRU/Paderborn/Aalto/MFPT 在 KB7 无可核实标识 ⟹ `origin={"source_tier","repo","id":"[待核]"}`，**不凭记忆填 DOI、不猜 URL** ⟹§1.1/§3 |

**旁批裁决（KB5 §7 上报 #12–#14，KB0 §7.3 A-68/A-69/A-70，非本节提出但落在本文件）**：
`sensor_config` 四值化（`mixed` 行为＝顺序项不评＋置信度封顶，但记录原因与 `unknown` 不同）⟹§1.1/§2.1/§2.2；
`unit_scale_mismatch` 降级为 `truth.json` 侧记账标签、可观测形式＝已登记的 `*_mm`/`*_counts` 比值跳变，`travel_limit`
进 C1 `meta.axis.travel_limit_{neg,pos}_mm`（`null` ⟹ 依赖判据 unavailable+`blocked_rules`）⟹§1.1/§2.1/§1.5；
转矩百分比判据分母＝`meta.drive.rated_torque_N_m`+`rated_torque_source`（`assumed` ⟹ 层级封顶 T2+强制 caveat）⟹§1.5/§3。

**跨文件回写跟踪（他文件落点，主线程/其他代理负责，本文件无权改）**：
**本段所列各项已全部闭环（主线程复核于本轮清扫，逐条实读他文件确认，不采信汇报）**——
C5 §2（A-54…A-59 字段名与必填项已回写、新增 §9 承载 A-64/65）；
C1（A-68/69/70：四值 `sensor_config` + 逐通道 `sensor_side`、`axis.travel_limit_{neg,pos}_mm`、
`drive.rated_torque_N_m`+`rated_torque_source`、派生规则 7/8）；
KB5 §3.3 孪生表 7×3（A-61）、§5.5 **P-14 已是四值**、§5.6 已有 `mixed_config`/`unknown_config`
两行投影（A-62/A-68）、§5.4 `c5_case` 示例已随 A-54…A-56 改名（`source_tier`/`present_channels`/可空
`counts_per_mm`）——**truth 侧同样改名**，理由：本目录的对拍基准虽是 C1 `meta.present_channels`，
但"truth 用旧名、meta 用新名"会让同一个概念在一份样本包里有两个键，正是 A-54 要避免的形状。

**本节回写中新发现的第 15 条（已裁 A-77）**：`case_id` 曾两处拼法不同（本文件 §1.2 `T3-PB-INJ01-0007`
vs KB5 §5.4 `T3-P-B-INJ01-0007`）。裁为**本文件 §1.2 语法权威**（四段、`-` 分隔、组内单调序号），
参数集进键名时去连字符写 `PA`/`PB`/`PC1`，叙述文字仍写 `P-A`/`P-B`；KB5 示例已改。

> **总结：本节 14 条（§7-A…§7-N）已全部落裁（A-54…A-67），其中 2 条——§7-K/§7-L（G-4/G-5：热漂·电机发热
> 与 kHz 量级判据）——裁为结构性真空，进拒答纪律与数据缺口清单，不造案例。**

> 交付一致性自检：本文件所有 slug 逐字取自 KB0 §2；tier 取自 KB0 §4 + C5 §1；期望判定形状取自 C3
> （`fault_mode`=slug、`differential.not_evaluable[].blocked_by`、`source_tier`+`audit.tier_ledger[]`、硬性规则 14/15/16）；案例 ID 一一对应 KB5 §3 注入编号。
> 未创建任何 `.py`/`.cs`；清单/伪代码均为说明性（KB0 §6.6 本期不写产品代码）。
