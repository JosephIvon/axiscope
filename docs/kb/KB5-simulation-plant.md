# KB5 — 仿真被控对象与合成数据规范

本文件是 **C4 验证门控**所依赖的被控对象（plant）模型规范，也是 **C5 的 T3 层**唯一认可的
合成数据来源。它是规范，不是代码：本期**不写产品代码**（KB0 §6.6），只给出方程、参数表、
伪代码与自检不变量。KB0 §6.4 要求"KB5 生成的合成样本必须能被 C1 loader 原样读入"，
本文 §5 就是这条检查的落地定义。

> **命名说明**：`C4-validation.md` 曾引用 `docs/kb/KB5-servo-simulation.md`，实际落盘路径为
> `docs/kb/KB5-simulation-plant.md`。**已由裁决 A-22 收口**（统一 `KB4-attribution-model.md` /
> `KB5-simulation-plant.md`），C4 现文已改为正确路径（`C4-validation.md` L45），本条不再是待决项，
> 记账见 §7 #1。

## 0. 三条不可协商的纪律

1. **T3 只证明管线连着。** 本文生成的任何样本，其指标只能进入 C5 §1 的"流程正确性"章节，
   章节标题必须写"合成集，不用于能力主张"；任何 Top-1/Top-3 命中率、准确率、召回数字
   **不得**来自 T3（C5 硬规则）。本文的模型设计（§1–§4）与验收方式（§5 预检）都必须
   在服务这条纪律的前提下才被允许。
2. **合成数据与真实数据走同一个 `features()` / `rules()` 代码路径**（C4 末段）。
   §5.7 把这条写成硬要求并给出实现级禁止项与验收测试。
3. **`truth.json` 只存在于合成样本。** C1 的目录结构就是这么定义的，而且**这条已是 C1 的加载规则**
   （不是本文的建议）：真实样本包内出现 `truth.json` 即为污染，loader 必须拒收并报错（§5.4 / §7 #5）。
   这是防"自造真值冒充实测"的结构性闸门。

派生的反向要求：**规则代码不得读取 `truth.json`**。`features()` 与 `rules()` 的输入签名里
只有 C1 样本包的 `meta.json` + `waveform.tsv`（+ 可选 `events.jsonl`）。注入真值与判据之间
的唯一通道是"真值→物理量→波形→C2 特征→规则"，不存在"真值→规则"的捷径。

---

## 1. 被控对象模型

### 1.0 信号流总图（注入点编号 = §3 的 INJ-xx 落点）

```
 上位机/插补器              运动指令生成器(§4)
 [INJ-15,16,18,19,21,22]        │
        └──pos_cmd──→  ┌────────┴───────┐
                       │ 7 段 jerk 受限  │  vel_ff, accel_ff[kff]  [INJ-09]
                       │ 轨迹 (§4)      │──┬────────────────┐
                       └────────────────┘  v                v
   位置环 P/PI/PID (T_pos) [INJ-13]  [INJ-21 整定窗口]   [INJ-29 陷波/低通]
        ┌──────────────────────────────────────────────────────────────┐
        │ Σ → 位置环 → 速度环 PI (T_vel) [INJ-12] → 电流环 PI (T_cur) [INJ-08] → τ_m
        │        ↑量化/速度估计 [INJ-10]     ↑PWM 延迟 + 转矩脉动 [INJ-11,20]
        └──────────────────────────────────────────────────────────────┘
   被控对象：双惯量弹性传动 [INJ-01,02,03,07] + 摩擦 [INJ-04,23] + τ_ext [INJ-24]
             +（可选）第三惯量/并联结构模态分支 [INJ-26 反例用]
        ↓                                             ↓
   电机侧编码器 θ_m（整数 counts，±0.5 count）[INJ-05]   负载侧标尺 x_l [INJ-30 非共置]
   参数随时间漂移 [INJ-06 热] / [INJ-14 电机发热]              │
        └──────── 各环采样与保持 → waveform.tsv (§5.2) ────────┘
   采样时刻抖动 [INJ-17,22]   定标覆盖 [INJ-19]   视觉通道 [INJ-18]
   events.jsonl —— 每个软件族注入必须同时产事件，否则因果门禁生效
```

### 1.1 单位与换算链（内部基准恒为 counts）

定义**脉冲当量**（pulse equivalency）为唯一的物理↔数字桥梁：

```
counts_per_mm = counts_per_rev_motor · N / x_per_motor_rev        [counts / mm]
```

其中 `N` = 传动比（电机转速 : 负载转速），`x_per_motor_rev` = 电机转一圈对应的**负载直线位移**（mm）：

| 传动形式 | `x_per_motor_rev` |
|---|---|
| 滚珠丝杠（导程 `lead` mm/rev） | `lead / N`；直驱丝杠 N=1 时即 `lead` |
| 齿轮 + 卷筒（绳索/带状） | `2π · r_drum · 1000 / N` |
| 直线电机 + 光栅尺 | 不适用此式：`counts_per_mm = 1 / grating_pitch_mm` |
| 旋转轴（dd 马达） | 用 `counts_per_deg = counts_per_rev·N/360`，直线量不得混用 |

**校验例（用公开数据复算，T2 出处：DaRUS `CableActuatorTestbed.xml`，KB7）**：
卷筒版 `r_drum = 0.049 m`、`N = 5.0` ⇒ `x_per_motor_rev = 2π·49/5 = 61.575 mm`；
发布的比例因子 `wegaufz/wegaufn = 1000000/171388 = 5.8349` ⇒ 取作 `counts_per_mm`，
反推 `counts_per_rev_motor = 5.8349 × 61.575 = 359.3`。
直驱版 `N = 1`、`100000000/85694000 = 1.16695` ⇒ `counts_per_mm = 1.16695`，
`x_per_motor_rev = 2π·49 = 307.876 mm`，反推 `counts_per_rev_motor = 359.3` ——
**两套独立发布数据闭合到同一个电机侧刻度**，且两值之比恰为传动比 `5.8349/1.16695 = 5.0`。
这构成 `counts_per_mm` 换算链的**可复算算术自洽检查（解析层，非本项目实测）**，
也是 §3 的 INJ-19（脉冲当量被换型流程覆盖）最小的可构造证明——"构造性成立"不等于"实测通过"（A-31）。

两点必须同时写下来的推论：

1. 若按上式取值，该试验台的位置刻度量子 ≈ **0.171 mm**（`position_quantum_mm = 1/counts_per_mm`，
   C2 规则 11 / 裁决 A-13），`quantization_step_counts = 1`
   意味着 µm 级跟随误差在该数据上**根本不可表示**；
   ★ **数量级对照（必须保留，这是本文件最有说服力的数值事实之一）**：
   P-B 的 `counts_per_mm = 50000` ⟹ 量子 `0.00002 mm = 0.02 µm`，
   与 P-A 的 `0.1714 mm` **相差 4 个量级**。同一句"亚微米级残差"在 P-B 上勉强可判、
   在 P-A 上自相矛盾（量子就有 171 µm，对齐 C2 例 B 的 `position_quantum_mm = 0.1714`）。
   因此任何精度声明都必须先报 `position_quantum_mm`，再由 C2 规则 11 把低于半个量子的声明
   改写为"低于本数据分辨率，无法判定"；
2. 但 `359.3 counts/rev` 对 MSK061C-0600 那一级绝对编码器明显过粗，
   说明 `wegauf*` 更可能是**控制器内部位置单位**（TwinCAT DCAX 缩放值）而非原始传感器刻度。
   在这一点未经原始工程文件核实之前，**禁止**把 5.8349 当作"每毫米传感器计数"来印 µm 数值；
   它只能作为"比例关系（两版本之比 = 传动比）成立"的证据。这恰好是 C1 单位纪律存在的理由：
   定标链的每一环都必须可复算，任何一环含糊就退回 `[counts]`。

**硬约束（C1 单位规则的展开）**：

1. 模型内部一律以 counts 积分；**落盘单位由 `meta.units_are` 决定**（裁决 A-4）：
   `counts` 时列值就是 counts，物理量只在报告层经 `counts_per_mm` 换算；
   `si_native`（P-A 默认，DaRUS 真实数据是 m / m/s / N·m）时列值按源 SI 单位写，
   C2 侧相应给 `*_m` / `*_mps` / `*_nm`，同样"缺定标不得臆造其它单位"。两种情形都不许在
   同一列里混单位，且 `units_are` 必须逐样本显式写出（不靠默认值）。
2. `counts_per_mm == null` 时：`fe_rms_mm`、`corner_error_mm` 等一律为 `null`，报告只印 `[counts]`；
   **禁止**输出 µm 数值（C1、C2 硬约定 3）。合成端必须能主动生成这种"缺定标"变体（§5.6）。
3. 转矩/电流侧同理：**`cur_q` 恒存 A，`cur_q.unit = "A"`；`cur_cmd`/`torque` 存 %（归一化 −100..100）
   或按 `torque.unit` 存 N·m**（裁决 A-4 / A-14：C1 的 `units_are`、`channels.*.unit` 是单位唯一权威）。
   额定电流必须来自 `meta.rated_current_a`，**缺失时不得假设**：`cur_q_rms_pct` / `cur_q_peak_abs_pct`
   一律 `null` 并进 `unavailable`（C2 规则 3 + 裁决 A-14 的 `_a` / `_pct` 双字段）。
   ★ 本文裁定（对应 §7 #9）：**`Kt` 与额定电流构成的标定链任一环缺失时，`cur_q ↔ %` 的换算必须为
   `null`，不得用"典型电机量级"估算**。P-B 的 `rated_current_a = 4.6` 是从 DaRUS 的 MSK061C-0600
   借来的（本文件 §2.0），对 P-B 那台直线轴而言是 **`assumed`**，不是发布值——凡引用 `%` 数值
   必须带这句限定；`torque_max = 32` 一类的厂商量同样一律标 `assumed`（A-27，§7 #3）。
   ★ 转矩侧百分比的分母**现已有契约载体**：`meta.drive.rated_torque_N_m` + `rated_torque_source`
   （裁决 A-70，§7 #14 就此收口）；四档合法性与 `assumed` 档封顶 T2 的口径见 §5.3 纪律 12，
   字段为 `null` 时转矩侧 `*_pct` 恒 `null`、只有 `N_m` 分支成立。
4. 换算链的每一环必须在 `meta.json` 或 `truth.json` 里留下可复算的输入（`N`、`lead` 或 `r_drum`、
   `counts_per_rev_motor`），合成样本不得只给一个孤立的 `counts_per_mm` 数字。

### 1.2 双惯性弹性传动模型

坐标约定：全部**折算到电机侧角坐标**（下标 `m` 电机、`l` 负载折算量）。

```
J_l' = J_l / N²            负载惯量折算到电机侧
k    折算到电机侧的等效扭转刚度 [N·m/rad]
c    折算到电机侧的等效黏性阻尼 [N·m·s/rad]
λ    = J_l' / J_m          惯量比（C1 的 drive.inertia_ratio）
```

**折算位置必须写明**：若柔顺元件在齿轮的高速侧，`k` 就是它本身；若在低速侧，则 `k_eff = k_phys / N²`。
`k` 不带折算说明的数值等于没有数值（这是一个常见 5×/25× 量级事故点）。

状态方程（τ_ext 为负载外力/外力矩，折算到电机侧）：

```
J_m θ̈_m = τ_m − [ k(θ_m − θ_l) + c(θ̇_m − θ̇_l) ]
J_l θ̈_l =       [ k(θ_m − θ_l) + c(θ̇_m − θ̇_l) ] − τ_ext
τ_s = k(θ_m − θ_l) + c(θ̇_m − θ̇_l)                传动轴传递转矩
```

传递函数（τ_ext = 0，分母 `D(s) = s²[ J_m J_l s² + (J_m+J_l) c s + (J_m+J_l) k ]`）：

```
P_mm(s) = θ_m/τ_m = (J_l s² + c s + k) / D(s)      电机侧（共置）——有谐振峰 + 反谐振谷
P_lm(s) = θ_l/τ_m = (c s + k)          / D(s)      负载侧——只有谐振峰，无复零点
```

解析特征频率（阻尼较轻时的一阶近似，及精确阻尼比）：

```
f_m = (1/2π)·√( k (J_m+J_l) / (J_m J_l) ) = (1/2π)·√(k / J_r)      谐振（极点对）
      J_r = J_m J_l/(J_m+J_l)   约化惯量
      ζ_m = c / (2√(k J_r))

f_a = (1/2π)·√( k / J_l )                                           反谐振（零点对，仅在 P_mm）
      ζ_a = c / (2√(k J_l))          复零点存在条件：c < 2√(k J_l)

f_m / f_a = √( 1 + λ )                                              ★ 配对间距只由惯量比决定
```

峰/谷可分辨条件：`|P_mm|` 出现局部极大需 `ζ_m < 1/√2`；出现局部极小需 `ζ_a < 1/√2`。
`ζ_m ≳ 0.5` 时峰被抹平——此时 R-03 应不触发，R-04 更不应触发。

#### 什么参数组合产生 KB3 的 R-04「谐振-反谐振配对」

R-04 的**充分必要条件组**（KB5 侧的可生成性定义，阈值数值归 KB3）：

| 条件 | 表达式 | 说明 |
|---|---|---|
| (i) 存在复零点对 | `c < 2√(k J_l)` 且 `ζ_a < 1/√2` | 只有电机侧共置 FRF 才有谷 |
| (ii) 存在欠阻尼极点 | `ζ_m < 1/√2` | 否则峰不可分辨 |
| (iii) 配对分离 > 频率分辨 | `f_m − f_a = f_a·(√(1+λ)−1) ≥ 2·Δf`，`Δf = 1/T_window`；**判据口径以 C2 规则 10 为准**：`resonance.estimation.pair_separation_bins ≥ 2` | 短窗下 `f_a≈f_m`，退化为单惯量外观（**不是**单惯量结论，见下） |
| (iv) 两者都在可评估频带内 | `f_m ≤ reliable_band_hz = fs/2.5`（C2 硬约定 7） | 超带的峰一律不得声明 |
| (v) 谷底相对宽带本底的抬升 | `amplitude_ratio_vs_broadband ≥ KB3 阈值` | 否则是噪声 |

λ 与配对间距的量化关系（这是 `resonance.candidates[].is_double_inertia_pair` 的物理来源）：

| λ = J_l'/J_m | √(1+λ) | f_m−f_a 相对间距 | 可分辨性 |
|---|---|---|---|
| 0.01 | 1.005 | 0.5% | **不可**——与单惯量无法区分，R-04 必须不触发 |
| 0.2 | 1.095 | 9.5% | 需 `Δf/f_m ≲ 4.7%`（即 `T_window ≥ f_m/21`）才勉强 |
| 1.0 | 1.414 | 41% | 良好 |
| 6.2（C3 示例） | 2.683 | 168% | 明显 |

**谱估计参数必须与候选一起产出（裁决 A-12，口径归 C2 规则 10）**：本文不再自带
"配对分离 ≥ 2 bins"这条私有判据；`resonance.candidates[]` 的每一个条目都必须由同一次
Welch 估计产生，并在**同一份 features JSON** 里带出五元组
`resonance.estimation.{window, nperseg, noverlap, method, pair_separation_bins}`
（连同 `resonance.resolution_hz`、`resonance.nyquist_hz` 与顶层 `fs_hz` 自洽，C2 规则 12）。
合成侧的三条纪律：

1. **生成端**：任何写入 `resonance.candidates[]` 的样本，`truth.json` 必须同时记录这次估计的
   五元组取值；`expected_feature_changes` 里凡是谱类字段都以"五元组 + 候选"成对声明。
2. **不可分辨的语义**：`pair_separation_bins < 2` ⟹ 该峰-谷组合一律判**不可分辨**，
   `is_double_inertia_pair` 必须为 `false`，并且**禁止**反推成"只有一个峰所以是单惯量"。
   正确表述只有三种：`不可分辨（分辨率不足）` / `该频段被 freq_limits 阻塞（unavailable）` /
   `检出单峰、配对判据不适用`。三者都不能进 `hypotheses[].cause = mechanical_double_inertia`。
3. **带外样本**：P-A（fs=1000）与 C2 例 B 一样写 `pair_separation_bins: null` +
   `candidates: []` + 同条目进 `unavailable`（C2 规则 7/13），`resolution_hz` 仍必须给值。

**顺序判据（本文件提出的实质修正，已由裁决 A-1 采纳并回写 C1/C2/C3）**：
对**共置**（执行器与传感器同在电机侧）的两惯量系统，极点/零点交替（positive-real 性质）
意味着 **`f_a` 必然低于 `f_m`**。`P_lm`（负载侧标尺输出）只有峰没有谷。因此
`resonance.candidates[].antiresonance_freq_hz > freq_hz`（旧示例写作 1181 峰 / 1420 谷，
现已按 A-1 改为 440 谷 / 1181 峰，`f_m/f_a = sqrt(1+λ) = 2.68 ⟹ λ ≈ 6.2`，与 §2.2 P-B 自洽）
在本模型下**不可能由纯两惯量产生**，它只能是：
(1) 非共置测量（电机编码器 + 负载光栅尺，两套通道分别估出的峰/谷被拼到一起）；
(2) ≥3 个惯量/≥2 个柔顺分支（此时交替规律使第二个峰可携带更高频的谷）；
(3) 陷波器/低通在闭环里造的人为谷；
(4) 混叠伪峰。
**结论**：R-04 的触发条件里必须含 `antiresonance_freq_hz < freq_hz`（或显式声明传感器构型）。
出现"峰 + 更高频谷"的组合时，若无 (1)/(2) 的构型证据，规则**必须拒绝**判双惯量配对，
转而怀疑 (3)/(4)。合成端则必须能分别生成这 4 类，用作 R-04 的**反例集**。

**构型声明的契约载体 = `meta.sensor_config ∈ {motor_side, load_side, mixed, unknown}`**
（A-1 建立该字段；第四轮裁决 A-68 把值域由三值扩为四值，并给 C1 位置类通道加了可选
`channels.<pos>.sensor_side ∈ {motor, load, unspecified}`——缺省 `unspecified`，只有 `mixed`
时必须逐通道填写；行为权威在 C1 派生规则 7 / C2 规则 9）。
`unknown` **或** `mixed` ⟹ 顺序项**不参与判定**，只按幅值与相位条件评，且结论置信度封顶
——两者行为相同，区别在**记录的原因**：`unknown`＝"不知道装在哪侧"；`mixed`＝"知道这条曲线
不是同一传递函数的响应——峰由电机侧通道估、谷由负载侧通道估，两套通道各自估出的极零点被拼到
一起，峰谷对不承载零极点交替信息，所以顺序约束对它不适用"。`mixed` 比 `unknown` 更诚实：
它把已经掌握的事实写进契约，而不是统一成一句"不知道"（这正是 A-68 判"临时 `unknown` 处置作废"
的理由）。本文件的取值约定：P-A / P-B 母样本 `motor_side`；负载侧标尺单独估谱的变体
`load_side`；**P-B2 / INJ-30 这类混合构型写 `sensor_config = "mixed"` + 逐通道 `sensor_side`**
（原先"一律写 `unknown` 并在 `audit.assumptions` 登记混合来源"的临时处置已按 A-68 作废，
收口账见 §7 #12）；`unknown` 在本文件只出现于 §5.6 的 `unknown_config` 投影（故意把已知构型
重标掉，用来考 A-1 那个具体错误）。

可选扩展（仅在参数集需要时启用，且在 `truth.json` 里标注为启用项）：

```
第三惯量分支：  J_2 θ̈_2 = k_1(θ_1−θ_2) + c_1(θ̇_1−θ̇_2) − k_2(θ_2−θ_3) − c_2(θ̇_2−θ̇_3)
平行结构模态：  τ_add = −k_s(θ_m − θ_s) − c_s θ̇_s,   J_s θ̈_s = k_s(θ_m−θ_s) + c_s(θ̇_m−θ̇_s)
                （把机身/卷筒/夹具模态当作并联二阶支路，用于产生第二个峰-谷对）
间隙/齿隙：     传递转矩经死区 φ_b：τ_s = k·sat(θ_m−θ_l−θ_dead) + c(...)，
                θ_dead 在换向后重新咬合 → 直接生成 C2 的 backlash_estimate_counts
```

两个及以上**并联**谐振支路（额外的结构模态分支）**不允许**在没有拟合依据时被生成——
它们会与 INJ-01 的单一共振峰互相混淆，而我们无法声称真实机器上存在那些模态（§6.1）。

### 1.3 摩擦模型

两族候选，本项目**默认用 Armstrong 双模态（one-step）**，LuGre 作为可选变体。

#### (A) Armstrong 双模态（Armstrong 1995 型；本文采用式）

稳态 Stribeck 曲线 + 一个一阶内部状态（近似预滑动弹性）：

```
τ_sl(v) = [ τ_c + (τ_s − τ_c)·exp( −(|v|/v_s)^α ) ]·sign(v) + b·v          滑动目标
dτ_f/dt = ( τ_sl(v) − τ_f ) / T_d            当 |v| < v_0 或静止（预滑动段）
τ_f 直接跟随 τ_sl(v)                          当 |v| ≥ v_0
```
参数：`τ_s` 突破静摩擦、`τ_c` 库仑、`v_s` Stribeck 速度、`α` 曲线形状、`b` 黏性、
`T_d` 动态（bristle 时间常数）、`v_0` 模态切换速度阈值。

#### (B) LuGre

```
dz/dt = v − |v|·z / g(v),        g(v) = τ_c + (τ_s − τ_c)·exp( −(v/v_s)² )
τ_f   = σ0·z + σ1·dz/dt + σ2·v
```
稳态还原为 `τ_f → sign(v)·g(v) + σ2·v`；`z(0⁺)` 记忆静止时的 bristle 形变 ⇒ 有
**预滑动位移**与**应力松弛**（A 只近似具备）。

#### 选择与代价

| 维度 | Armstrong one-step | LuGre |
|---|---|---|
| 参数量 | 6（每个都有可观测签名） | 7–8（σ0/σ1/σ2 与 τ_s/τ_c 高度耦合） |
| 从 1–8 kHz 采样位置/速度可辨识性 | 可（τ_s→起动迟滞与爬行，b→斜率，v_s→低速抖振频率） | **差**：σ1/σ2 分裂在采样带宽内几乎不可分 |
| 数值刚性 | 弱（`T_d` 主导，指数更新即稳） | 强：预滑动段等效刚度 σ0，显式积分需 `h_int ≲ 0.2/√(σ0/J)`，典型 µs 级 |
| 能再现的 C2 特征 | `friction_stiction_ratio`、`crawling.*`、`global.reversal_error_counts`（配合死区） | 同上 + 更真实的 `thermal_*` 型力松弛（本项目**不需要**） |
| 预滑动滞后回线 | 近似 | 真 |
| **自验证风险** | 参数可辨识 → 拟合残差有物理意义 | 用自己模型辨识自己生成数据 = 纯同义反复 |

**决定**：默认 (A)。(B) 仅在工况明确需要 bristle 记忆（例如演示"静止后起始位移回弹"）时开启，
且此时**必须**同时产出一个 (A) 的对照样本，否则拒绝入库。代价明写：(A) 不产生真实的
应力松弛与摩擦记忆 ⇒ **本项目不得用任何 T3 样本去支撑热漂移、蠕变、"冷机/热机差异"类判据**。

**T2 校准锚点（不是我们的真值）**：DaRUS 公开了 `LdaFricIdent`（`tau_T` 从 7→60 N·m 线性爬升、
`v_T≈0`，即突破摩擦辨识）、`PreloadedLuGreFrictionIdent/Validation`、
`PreloadedViscousFrictionIdent`（WC80…WC180 多预载）战役与参数（KB7）。
用法限制：

1. 只允许用来设定 τ_s/τ_c/b/v_s 的**量级区间**与曲线形状，逐参数标注
   `{"param_source": "T2: DaRUS-5171 PreloadedLuGreFrictionIdent", "provenance": "literature"}`；
2. **不得**写进 `meta.drive` 或 `context` 冒充被测设备的参数；
3. 由这些参数生成的样本，其 tier 仍是 T3（真值来自我们的注入），**不得**在 C5 里当 T2 案例计。

#### 摩擦的解析预言（可直接在 T1-a 上核对，属于解析层而非自证）

粘滑（stick-slip）自激的充分条件与振荡频率：

```
自激条件： dτ_f/dv |_{v=v_work} < 0  且  |斜率| > b_crit ≈ 2√(k_eff J_r)·ζ_margin
粘滑频率： f_ss ≈ (1/2π)·√( k_eff/J_r − (c_eff/J_r)²/4 )    （库仑激励的衰减回归）
静止时长： T_stick ≈ 2/(c_eff/J_r) · ln(Δv/v_res)            （指数衰减到重新咬合）
```
这条给出 `crawling.sawtooth_freq_hz` 的**闭式预测**：注入摩擦参数后可直接算出预期锯齿频率，
再与同一个 `features()` 的输出比对（§5.7 的自检之一）。

### 1.4 控制器结构与实现非理想性

三环嵌套（各自独立周期，全部为离散控制器 + ZOH）：

```
位置环  e = pos_cmd − pos_fb
        u_ff   = kff_a · accel_cmd · J_tot' + kff_v · vel_cmd · b'      （前馈）
        u_pd   = kp·e + ki·Σe·T_pos + kd·(Δe/Δt)      （P / PI / PID 三种变体，kd 需一阶低通）
速度环  v_ref = (u_pd + u_ff)/Kt'    →   τ_cmd = Kt·(kv·(v_ref − vel_fb) + kvi·Σ(...)·T_vel)
电流环  τ_cmd → i_ref；  i 受带宽为一阶滞后 + PWM 延迟的一阶模型约束
```

| 项 | 取值约定 | 备注 |
|---|---|---|
| `T_pos` | 1 ms（DaRUS 种子）/ 2 ms / 4 ms | 与 `SampleTime` 一致时最贴近 TwinCAT 实测 |
| `T_vel` | 250 µs – 1 ms | |
| `T_cur` | 50 – 125 µs | 决定电流环带宽 `f_i ≈ Kpwm/(4πL)`；**该值必须写进 `meta.drive.current_loop_bandwidth_hz`**（裁决 A-42，C1 `drive` 已落地该字段）。厂商/发布值未给出时一律 `null`，此时 KB3 R-12 的支路 A 不可用、走支路 B 并降 `unverified`（P-A 就是这种情形，见 §2.1） |
| 环内延迟 | 每个环 **1 个整周期 ZOH + 0.5 周期采样-保持** | 合计相位损失 ≈ `(T_pos+T_vel+T_cur)·f`；这是增益上限的主因 |
| 陷波器 | 二阶 notch `(s²+2ζ_z ω_z s+ω_z²)/(s²+2ζ_p ω_z s+ω_z²)`，可级联 | 深度 dB、宽度（峰频/Q） |
| 指令滤波 | DaRUS 发布"低通 0.02 s" ⇒ `f_c = 1/(2π·0.02) ≈ 8.0 Hz` | 见下方红字 |
| 编码器量化 | 位置取整到 1 count（±0.5 count 均匀） | `meta.quality.quantization_step_counts` |
| 速度估计 | 差分 `Δθ/T` 或 M/T 法 | 差分噪声 `σ_v = Δ/(√12·T)`；T=1 ms、Δ=1 count → **σ_v ≈ 0.29 counts/ms** |
| PWM/电流噪声 | `τ = τ_cmd·(1 + Σ_n r_n sin(n θ_e + φ_n))`，`n = 6k±1`（三相）+ 槽齿谐波 `n = Q_s·p` | INJ-11 / INJ-20 的落点 |
| 测量噪声 | 带限白噪声 + 少量 1/f | 采样后叠加，不得叠加在连续解上再采样（否则低估噪声） |
| 转矩标定 | `Kt [N·m/A]`、`rated_current_a`、`cur_q` 满度 = `rated_current_a × Kt` | `meta.rated_current_a` 缺失时 `%` 通道不得派生；转矩侧 `%` 的分母按 A-70 走 `drive.rated_torque_N_m` + `rated_torque_source`（四档口径见 §5.3 纪律 12） |

**红字（单位/换算纪律）**：DaRUS 发布的是 **8 Hz 的指令滤波 + 1 kHz 采样 + 绳索卷筒传动**。
在该配置下任何 kHz 级谐振都**不可能**是机械结构模态；若波形里出现 >400 Hz 的"峰"，
唯一诚实的解释是混叠伪峰或高频量化噪声。合成端在参数集 (a) 上**禁止**声明任何 ≥400 Hz 的共振工况。

### 1.5 离散化、积分步长与稳定性判据

**三个时间尺度必须分开**（这是本节的唯一主题）：

```
h_int   连续被控对象的积分步长
T_cyc   数字控制器周期（三环各自）
T_log   波形写出周期 = 1/fs（= DaRUS 的 SampleTime）
约束： T_log 必须是 T_cyc 的整数倍；h_int ≤ T_cyc / K，K ≥ 10；h_int ≤ T_log / 10
```

为什么**不能**用与数据采样率相同的步长做积分（即 `h_int = T_log = 1 ms`）：

1. **数值可解性**：被控对象里必须积分的最高频率不是指令带宽，而是**谐振极点 + bristle 极点**。
   `f_m = 1181 Hz → ω = 7415 rad/s`，无阻尼谐振在 RK4 下的稳定上限约 `ω·h ≲ 2.8`
   ⇒ `h ≲ 0.38 ms`；取 `h = 1 ms` 时 `ω·h = 7.4`，**数值发散或产生虚假相位滞后**，
   与物理无关。加上 LuGre 的预滑动刚度，`h` 需要 µs 级。
2. **采样定理与抗混叠**：`f_m > fs/2` 的模态若被积分出来，写出后**必然折返**成一个低频假峰。
   此时 C2 会报出一个根本不存在的共振，而 `truth.json` 又"证明"它存在——
   这正是自验证循环的数值实现形式。所以正确做法是：**要么让 fs ≥ 2.5·f_m（生成合法工况），
   要么拒绝生成该工况（§5.5 预检 P-1）**，绝不允许"积分出来再折返"。
3. **环内相位滞后**：`e^{-sT}` 的一拍延迟在 1 ms 采样点上用 `h = 1 ms` 的粗积分无法准确表示，
   稳定性裕度会被系统性高估 5–15°。

**推荐积分方案（按优先级）**：

```
方案 1（首选）：把线性部分做精确离散化 —— 状态空间 x[k+1] = A_d x[k] + B_d u[k]
                A_d = expm(A·h_int)，B_d 由 expm 增广矩阵或双精度级数求得（ZOH 精确）
                摩擦与死区等非线性项用 h_int 的显式子步处理
方案 2：RK4，子步 h_int = T_cyc / K，K ≥ 10（K 记入 truth.json 以便复算）
方案 3：LuGre 开启时，bristle 状态用解析指数更新 z ← z_ss + (z−z_ss)·exp(−h_int·|v|/g(v))
        避免显式刚性失稳
```

**稳定性判据（仿真启动前与启动后各一次）**：

| 检查 | 判据 | 失败动作 |
|---|---|---|
| 离散闭环极点 | 全部 `abs(z) < 1`，且最坏 `abs(z) ≤ 0.995`（等效衰减裕度） | 拒绝生成该参数集，报 `unstable_config` |
| 开环相位/增益裕度 | `PM ≥ 30°`、`GM ≥ 6 dB`（含 ZOH 与一拍延迟） | 允许生成，但标注"临界"，只用于演示自激 |
| 延迟建模 | `e^{-sT}` 用二阶 Padé 近似做频域校核；时域用精确整数拍延迟 | 不得用 `1/(1+sT)` 冒充纯延迟 |
| 数值能耗散 | 无阻尼自由振荡 100 周期内幅值漂移 <1% | 说明 `h_int` 太大，加倍重跑 |
| 能量守恒核对 | `∫τ_m θ̇_m dt = Δ动能 + Δ弹性势能 + ∫τ_f θ̇ dt + ∫τ_ext θ̇ dt`，残差 <0.5% | 摩擦/传动功率记账错误，禁止入库 |

能量核对是本模型最重要的独立正确性检查：**它不需要任何外部真值**，也不经过规则层，
因此不会被自验证循环污染。任何合成批次必须报告该残差的分布（均值/最大/p95）。

**措辞纪律（A-31）**：本节的极点判据、`ω·h ≲ 2.8` 稳定上限与能量核对都是**解析 / 数值自洽校验**
（只在模型内部成立），不是对真机的实测，也不是对已运行代码的实测记录。实现期真正跑完之前，
本文对这些判据的合法说法只有"待执行 / 按构造应满足"；跑完之后也只能写
"数值稳定性判据满足、能量残差分布为 …（合成侧自洽校验）"，**不得**写成
"数值稳定性已实测验证 / 实测通过"。S 曲线的位移闭合（§4.5 I1、I5）同理：那是恒等式校验，不是验证。

---

## 2. 参数集

### 2.0 公开参数种子（全部有出处，禁止当成我们的实测）

| 项 | 值 | 出处 |
|---|---|---|
| 控制器参数 | `kff=1.5, kp=0.01, ki=0.1, kd=0.0005` | DaRUS `CableActuatorTestbed.xml`（torque-cable-force 环） |
| 速度环（对照） | `kp=0.001, ki=0, kd=0` | 同上（velocity-cable-force 环） |
| 指令低通 | `0.02 s` → `f_c ≈ 8.0 Hz` | 同上 |
| 电机 | Bosch Rexroth **MSK061C-0600-NN**，`n_max=6000 rpm`，`torque_max=32`（**无量纲**，疑为齿轮输出侧量，惯量/额定转矩均未发布 ⟹ 使用方一律标 `assumed`，裁决 A-27 / §7 #3；A-70 落地档 = `drive.rated_torque_source = "assumed"`，见 §5.3 纪律 12） | 同上 |
| 传动 | `gear ratio = 5.0`，`wegaufz/wegaufn = 1000000/171388` | 同上 |
| 卷筒 | `r_drum = 0.049 m` | 同上 |
| 采样 | `SampleTime = 1 ms`（fs=1000 Hz，奈奎斯特 500 Hz，可靠带 400 Hz） | DaRUS **发布数据**的 CSV 头（T1-a 侧事实，由数据集作者实测；**不是**本项目采集/核对的结果，A-31） |
| 位移传感器 | Micro-Epsilon ASCOspeed ASP5500-300，`INCFactor=50`，`CONTtrolt 0.15 s`，`FIlter 16`，`HAVOn 1`，`MINRate 0`，`EROn 1` | `data/raw/ASCOspeed_Settings.md` |

两个必须写下来的推论：

* `ASCOspeed` 的 `MINRate 0` = 静止时仍出数、不做速度下限保持 ⇒ 静止段的噪声是**真实噪声**
  而非插值。本模型的静止噪声底由此标定（INJ-11 的量级下限），
  `CONTtrolt 0.15`（约 6.7 Hz）是该传感器自身的更新/控制时间常数。
* XML 的 `inertia="0.000"`、`mass="0.0"` —— **惯量与刚度在原始数据里没有发布**。
  因此 §2.1–2.3 的 `J_m / J_l / k / c / Kt` 全部是**假设值**，必须逐项写进
  `truth.json.plant.params[].provenance = "assumed"`，并在任何引用它们的报告里保留这句限定。
  `torque_max=32` 与被借用的 `rated_current_a = 4.6`（P-B 并不装 MSK061C）同属这一类：
  **一律 `assumed`**（A-27），且 `%` 类换算在标定链缺失时必须为 `null`（§1.1 硬约束 3 / §7 #9）。
  A-70 之后转矩侧的 `assumed` 有了正式载体：`meta.drive.rated_torque_N_m` + `rated_torque_source`
  四档（`measured / manual / nameplate / assumed`），本文件全部落在 `assumed` 档，
  逐参数集取值见 §5.3 纪律 12。
* **禁止措辞**：本文件没有任何参数集"已被真实数据验证"。P-A 只是**与 DaRUS 公开试验台同构**
  的锚点集（T2 发布值 + 我们自己的假设），P-B 是**虚构的半导体贴片轴**工况；
  两者都不得被描述成半导体产线数据或被测设备实测。

### 2.1 参数集 (a) P-A：线缆驱动试验台（有外部锚点）

定位：与 DaRUS 同构（绳索 + 卷筒 + 外部负载/预紧锚点）。**这不是半导体设备数据**，
所有 `machine_context.machine_type` 一律写 `testbed`。
标题里的"外部锚点"指**机械上的绳索锚点**（它产生行程相关张力 `τ_ext`，INJ-24 / P-C1 的非 LTI 来源），
**不是**"有外部数据把本参数集验证过"——本集没有任何一条被真实数据验证过（§2.0 禁止措辞）。

```
fs = 1000 Hz（= SampleTime），T_pos = 1 ms，T_vel = 1 ms，T_cur = 0.125 ms
h_int = 50 µs（K = 20）
counts_per_mm = 5.8349（复算见 §1.1，含"可能是控制器内部单位"的限定）
quantization_step_counts = 1 → 位置刻度量子 ≈ 0.171 mm
N = 5.0，r_drum = 0.049 m，x_per_motor_rev = 61.575 mm
J_m = 3.0e-4 kg·m²（假设：MSK061C-0600 电机侧量级）
J_l' = 9.0e-4 kg·m² → λ = J_l'/J_m = 3.0（绳索+卷筒+预紧载荷折算）
J_r = J_m J_l'/(J_m+J_l') = 1.875e-4 kg·m²
k = 15.0 N·m/rad（折算到电机侧，绳索+卷筒等效，柔）
   → f_m = (1/2π)√(k/J_r) = (1/2π)√(8.0e4) = 45.0 Hz
   → f_a = f_m/√(1+λ) = 45.0/2.00 = 22.5 Hz          ★√(1+3.0)=2.0，配对间距 22.5 Hz
c = 2 ζ_m √(k J_r) = 2(0.12)(0.0530) = 1.27e-2 N·m·s/rad（ζ_m = 0.12，绳索阻尼大，Q ≈ 4.2）
摩擦：τ_s = 0.9 N·m（折算）、τ_c = 0.45、v_s = 0.05 rad/s、α = 1、b = 0.8 N·m·s/rad、
      T_d = 4 ms，Armstrong 模型。参数区间锚定 T2: DaRUS LdaFricIdent/ViscousFrictionIdent
      力矩核对：a_l = 200 mm/s² → α_m = (0.2/0.061575)·2π = 20.4 rad/s²；
      τ_acc = (J_m+J_l')α = 1.2e-3 × 20.4 = 0.0245 N·m ≪ τ_c → 本工况是**摩擦主导**型
外部锚点：绳索经负载轮锚于机架 ⇒ 存在行程相关张力 τ_ext(x)（分段线性，非 LTI，见 INJ-24）
控制器：kff=1.5, kp=0.01, ki=0.1, kd=0.0005 + 8.0 Hz 指令低通（全部为发布值；
        ★这些增益是 TwinCAT 归一化口径，不能直接代入本文件的 SI 公式；
          合成器必须先把自己的 SI 增益换算到同一口径再写进 meta，否则就是
          AUDIT 记录的"照抄增益差 1000 倍且不报错"事故模式）
噪声：cur_q 白噪声 0.02 A rms；静止噪声底按 ASCOspeed `MINRate 0` 设为真实底噪（§2.0）；
      vel_fb 由 pos_fb 差分派生 → channels.vel_fb.derived = true（σ_v ≈ 0.29 counts/ms）
指令：S 曲线（§4）距离 120 mm，v_max 40 mm/s，a_max 200 mm/s²，j_max 4000 mm/s³；
      往复 12 次 + dwell + rest；含 1 段 probing（恒速 30 mm/s，供纹波/爬行判据）
```

**P-A 的 meta 侧取值（对标 DaRUS，A-4 使 SI 原生成为默认）**：

| C1 字段 | P-A 取值 | 说明 / provenance |
|---|---|---|
| `units_are` | **`"si_native"`（默认）** | DaRUS 的位置/速度/转矩真实单位是 m、m/s、N·m，根本没有 counts 刻度（A-4）；`torque.unit = "N_m"`。若某变体刻意将 `wegauf*` 缩放当作 counts 刻度，必须显式改写 `units_are = "counts"` 并在 `audit.assumptions` 登记该解释未被原始工程文件核实 |
| `sensor_config` | `"motor_side"` | 45 Hz 模态的峰/谷若被声明，顺序期望按 C1 派生 7；本集该模态带外/未激励，顺序项实际不参与（见下） |
| `counts_per_mm` | `5.8349`（`assumed`，可能是控制器内部缩放单位） | §1.1 的两条推论都适用；报告层据此换算的 mm 数值必须带这条限定 |
| `position_quantum_mm`（C2 规则 11，A-13） | `0.1714` | 由 `counts_per_mm` 派生；µm 级声明在本集一律判"无法判定" |
| `drive.current_loop_bandwidth_hz`（A-42） | **`null`** | DaRUS 未发布电流环带宽 ⇒ 依赖它的 KB3 R-12 走支路 B 并降 `unverified`；**禁止**用 `T_cur = 0.125 ms` 反算一个数冒充发布值 |
| `drive.rated_torque_N_m` + `rated_torque_source`（A-70） | `32.0`（附"XML 原值无量纲、疑为齿轮输出侧量"限定，A-27）+ `"assumed"` | 本集的额定转矩来源档位：`assumed` ⟹ 转矩 `*_pct` 可算但**证据层级封顶 T2** 且强制 caveat"额定转矩为假定值，百分比类判据的绝对刻度不可信"（C1 单位规则 / C2 规则 3）；宁缺毋滥的 `null` 分支留给 INJ-28 变体（§5.3 纪律 12） |
| `cross_validation.pairs` + `extra_channels`（A-6） | `pairs = [["pos_fb","rope_pos"],["pos_fb","lsv_pos"]]`；`extra_channels = {rope_pos:{unit:"m"}, lsv_pos:{unit:"m"}}` | 对应 DaRUS 的三路位置反馈（电机编码器 / 绳长 / 线性传感器）；`pos_fb` 之外的两路按 C1 词表**不是**通道名，必须走 `extra_channels`，分歧本身由 C2 `sensor_disagreement` 承载。任何"看起来像 fe"的候选列（如 `dPosition_diff`）未过 `corr > 0.99` 自检前也只能进 `extra_channels`（C1 派生 2 / A-5） |
| `resonance.estimation`（A-12） | `candidates = []`、`pair_separation_bins = null`、`resolution_hz = 0.49`、`{window:"hann", nperseg:1024, noverlap:512, method:"welch"}` | 与 C2 例 B 同形：45 Hz 模态在 plant 里但未被激励，kHz 模态在带外 |
| `quality_ref` 来源（A-10） | `quality.quantization_step_counts = 1`、`axis.motor_rev_counts` | C2 的 `quality_ref` 由这两个 meta 字段供给，合成端不得只把量化台阶写在叙述里 |

预期 C2 特征签名：

| C2 字段路径 | 预期 | 理由 |
|---|---|---|
| `freq_limits.blocked_rules` | `["R-03","R-04"]`，`reason` 含 `fs<4kHz` | KB0 §1 要求 `reliable_band ≥ 2000 Hz`，此处 400 Hz |
| `resonance.candidates[]` | **空数组**（且报告**不得**写"无共振"，只能写"该频段不可评估"） | C2 硬约定 7 |
| `global.friction_stiction_ratio` | 1.5–2.2 | τ_s/τ_c = 2.0，被 b 与 T_d 稀释 |
| `crawling.low_speed_segments[]` | 存在，`is_sawtooth=true`，`sawtooth_freq_hz` ≈ 由 §1.3 闭式预测 | 低速段 + Stribeck 负斜率 |
| `ripple.probing[].correlated_with_cur_q` | 0.8–0.95（绳索刻度 0.171 mm → 纹波以"刻度台阶"为主） | 量化主导 |
| `ff_mismatch.*` | `asymmetry_ratio` 显著 > 1，且 `fe_vs_accel_corr` **为正**（本工况摩擦主导，`kff=1.5` 的符号翻转被掩盖，见 §4.4 预言 2′） | §4.4 + §2.1 力矩核对 |
| `global.thermal_drift_counts_per_min` | 有值（temp 通道在 DaRUS 里存在，本模型用脚本化漂移） | 仅作 `temp` 通道可用性演示 |
| `sensor_disagreement`（三位置通道） | `x_T`/`x_asco_enc`/`x_lsv_enc` 之差给出滑移带 | 与 T1-a 直接同构 |

**P-A 的两种"看不见"必须分开记账（这是 §5.5 P-1 的实质内容）**：

* 45 Hz 绳索弹性模态**在**本模型的 plant 里（`k = 15.0 N·m/rad`），但它**高于 8.0 Hz 指令低通**
  约 5.6 倍（−15 dB/dec 以上衰减），常规 S 曲线指令几乎没有能量把它激励起来
  ⇒ 该注入项必须标 `declared_detectable = false`，理由 `"not_exited (command filter 8 Hz)"`；
  只有摩擦起动瞬态（INJ-04）与外力阶跃（INJ-24）能弱激励它。
* kHz 级模态则是**频段外**（`reliable_band = 400 Hz`）⇒ `freq_limits.blocked_rules` 记账。

两者的报告措辞完全不同：前者是"该工况在此激励方式下不会被激发"，
后者是"该频段不可评估"。**都不得写成"未发现共振"**（C2 硬约定 7）。

### 2.2 参数集 (b) P-B：半导体贴片轴（共晶贴片机 X 轴）

定位：短行程、高惯量比、紧整定窗口、**高采样率**。`machine_type = die_attach`。
用"旋转等效 + 虚拟导程"表示直线轴：等效半径 `r_eff = lead/2π`，取 `lead = 8 mm/rev`
⇒ `r_eff = 1.273e-3 m`，`r_eff² = 1.621e-6 m²`。所有旋转量都能除回直线量，避免单位口径漂移。

```
fs = 8000 Hz → nyquist 4000 Hz，reliable_band = 3200 Hz（对齐 C2 示例的 nyquist_hz 4000）
T_pos = 250 µs，T_vel = 125 µs，T_cur = 62.5 µs，h_int = 6 µs（K ≈ 20；T_log = 2·T_pos）
counts_per_mm = 50000（直线光栅尺 20 nm 刻度，1 count/刻度）；quantization_step_counts = 1
电机侧绝对编码器 counts_per_rev = 524288（仅填 meta.axis，非共置通道，见变体 P-B2）

旋转等效量（逐项 provenance = assumed，见 §2.0 与 §7 #9 / #3）：
J_m  = 1.126e-6 kg·m²  → 等效电机侧质量 J_m/r_eff² = 0.694 kg
J_l' = 6.960e-6 kg·m²  → 等效负载质量 4.30 kg
J_tot = 8.11e-6 kg·m²，λ = J_l'/J_m = 6.18 ≈ 6.2（与 C3 示例一致）
J_r = J_m J_l'/J_tot = 9.66e-7 kg·m²
k = ω_p² J_r = (7420)² × 9.66e-7 = 53.2 N·m/rad → 直线等效刚度 k/r_eff² = 3.28e7 N/m
c = 2 ζ_m √(k J_r) = 2(0.019)(7.17e-3) = 2.72e-4 N·m·s/rad，ζ_m = 0.019
   ★ 代数复算（同一组 assumed 参数下的自洽校验，**不是**验证）：
     f_m = (1/2π)√(k/J_r) = 1181 Hz；f_a = f_m/√(1+λ) = 1181/√7.18 = 440 Hz
     （f_m/f_a = √(1+λ) = 2.68，配对间距 741 Hz；`resolution_hz = 1.95`（fs 8000 / nperseg 4096）
      ⟹ `pair_separation_bins = 741/1.95 ≈ 380 ≥ 2` ⟹ §1.2 条件 (iii) 按 C2 规则 10 判**可分辨**；
      C2 例 A 在同一组参数上曾写 382——**不是取整口径差异而是缺陷**，已按 A-76 统一为 380）。合成端必须把五元组
      `resonance.estimation = {window:"hann", nperseg:4096, noverlap:2048, method:"welch",
      pair_separation_bins:380}` 与候选一起写出，缺则谱结论不得被引用（A-12））
   ★ Q 核对：1/(2ζ_m) = 26.3 ≈ C2 示例的 quality_factor_estimate = 27（同一物理量两种表述）。
     而 amplitude_ratio_vs_broadband = 8.4（18.5 dB）是 PSD 相对**宽带本底**之比，
     与 Q 不可直接划等号（分母含环内滤波/陷波衰减）→ 两个量的估计口径**已由裁决 A-12 契约化**，
     权威在 C2 规则 10（本文 §7 #7 已闭环，不再自设判据）。
摩擦（直线导轨/滚珠级，assumed）：τ_s = 0.06, τ_c = 0.035, v_s = 0.02 rad/s, b = 0.02,
      T_d = 1 ms，Armstrong；导轨死区 φ_b = 0（默认关闭，INJ-02 打开）
电流环带宽 f_i = 1.2 kHz（**必须写进 `meta.drive.current_loop_bandwidth_hz = 1200.0`**，
  本集为 assumed；裁决 A-42 已把该字段落进 C1 `drive`，KB3 R-12 支路 A 依赖它）；PWM 延迟 0.5·T_cur
   ★ f_i 与 f_m = 1181 Hz **同量级**：电流环相位滞后正好压在机械谐振上。
     这是"谐振无法靠降增益推开、只能陷波"的真实工况，也是 INJ-13 让交越逼近 f_a 时
     极易自激的原因。
控制器（SI，N·m 口径；速度环假定带宽 ≥ 3ω_n）：位置环 PID，取 ω_n = 2π·85 = 534 rad/s
      kp = ω_n² J_tot = 2.31          （f_m/ω_n = 13.9 ≫ 3 → 谐振在增益交越带之外）
      ki = kp·ω_n/5 = 247             （积分零点 107 rad/s）
      kd = kp·5/ω_n = 0.0217          （微分零点 5ω_n + 一阶滤波）
      加速度前馈 kff = 1.0（INJ-09 扫描 0/0.5/1/1.5/2）
      ★ 增益必须带单位与折算侧；跨侧照抄 kp 会差 N² 倍（此处 N=1 直驱，但仍需声明）
力矩核对：a_max = 30000 mm/s² = 30 m/s² → α = a_max/r_eff = 2.36e4 rad/s²
      τ_acc = J_tot α = 0.191 N·m，加摩擦约 0.25 N·m；按 assumed Kt = 1.5 N·m/A → 0.17 A
      （≪ rated_current_a = 4.6 → 峰值裕度充足。`rated_current_a` 与 `Kt` 都是 **assumed**
        （4.6 A 是从 MSK061C-0600 借来的，P-B 并不装这台电机）；**Kt 未经手册核实前不得据此印
        % 转矩**——`cur_q.unit = "A"` 恒真，`cur_q_rms_pct` / `cur_q_peak_abs_pct` 在标定链缺失时
        一律 `null` 并进 `unavailable`，不得估算（§1.1 硬约束 3、C2 规则 3、A-14、§7 #9）。）
指令：S 曲线（§4）距离 3.2 mm（取片→贴片短行程），v_max = 1500 mm/s，
      a_max = 30000 mm/s²，j_max = 1e7 mm/s³
      → 判据：`a_max²/j_max = 9e8/1e7 = 90 mm/s`，故只要 `v_p > 90` 就进入**梯形加速**分支；
        而 D = 3.2 mm 不足以跑到 v_max ⇒ **情形 III-b**（达到 a_max、无匀速段，需 Newton 反解 v_p）。
        预期解：t1 = t3 = a/j = 3.0 ms，v_p ≈ 269 mm/s，t2 ≈ 5.97 ms，
        T_total = 2(t1+t2+t3) ≈ 23.9 ms，x_h ≈ 1.6 mm（位移闭合到 3.2 mm）。
        ★ 这条工况专门选在 III-b，因为它是 §4.2 里唯一需要数值反解的分支，
          也是最容易静默出错（短行程被当成"够长"而截断指令）的一支。
      settle 窗口 20 ms（实际需要 ≈42 ms，对齐 C2/C3 示例 → INJ-21 的落点）
      四分支覆盖：P-A 的长行程走情形 I；P-B 走 III-b；
      另需各生成一条 II（jerk 主导，例如 j=5e5、a=3e4、v_p=1500）与 III-a
      （无匀速、纯 jerk，例如 D 极短）的黄金向量（§4.5）。
```

预期 C2 特征签名：`resonance.candidates[0].freq_hz ≈ 1181`、
`antiresonance_freq_hz ≈ 440`（**低于**峰，符合 §1.2 顺序判据）、
`is_double_inertia_pair=true`、`quality_factor_estimate ≈ 26`、
`present_in_dwell=true`、`present_in_rest=false`、`tracks_command_frequency=false`
—— 恰好是 C2 硬约定 6 要求的四条件齐全正例。
另加 `step_response[].damping_ratio_estimate ≈ 0.02–0.05`、`ringing_cycles_to_settle ≥ 3`、
`settle_band_pct_of_move ≈ 0.04`（C2 示例值），以及
`freq_limits.reliable_band_hz = 3200`、`blocked_rules = []`。
**以上都是"按构造应检出"**：本集从未与任何真实数据比对过，不得写成"已验证"（A-31）。

**P-B 的 meta 侧取值（counts 基准集，与 P-A 的 SI 原生形成对照）**：

| C1 字段 | P-B 取值 | 说明 / provenance |
|---|---|---|
| `units_are` | **`"counts"`**（本项目基准；A-4） | `cur_q.unit = "A"`、`torque.unit = "percent_of_rated"`（仅在 `drive.rated_torque_N_m` 存在且 `rated_torque_source` 已声明时合法，A-70；本集为 `assumed`，见下行） |
| `sensor_config` | `"motor_side"` | P-B 母样本是共置构型 ⟹ `f_anti < f_res` 参与判定（A-1 / C2 规则 9） |
| `counts_per_mm` | `50000.0`（`assumed`：光栅尺 20 nm 刻度 × 4× 细分） | 换算链见 §1.1；`starved_scale` 变体改写为 `null` |
| `position_quantum_mm`（A-13） | `0.00002`（= 2e-5 mm = 0.02 µm，与 P-A 的 `0.1714` 差 4 个量级） | `counts_per_mm = null` 的分支里本字段 `null`，报告只印 `[counts]` |
| `drive.current_loop_bandwidth_hz`（A-42） | `1200.0`（`assumed`） | 与 `f_m = 1181 Hz` 同量级是本集的叙事要点；INJ-08 把它降到 300 Hz 时必须同步改写 `meta`，否则 meta 与波形互相矛盾 |
| `drive.rated_torque_N_m` + `rated_torque_source`（A-70） | `6.9`（= assumed `rated_current_a` 4.6 A × assumed `Kt` 1.5 N·m/A，§2.2 力矩核对）+ `"assumed"` | `cur_q_saturation_ratio` 一类百分比判据自此有**可追溯分母**（§7 #14 收口）；`assumed` 档 ⟹ 封顶 T2 + 强制 caveat；两输入任一为 `null` 的变体（INJ-28）里本行改写 `null` + `null` |
| `cross_validation.pairs` / `extra_channels`（A-6） | 母样本 `pairs = []`、无 `extra_channels`（单路反馈）；P-B2 变体 `pairs = [["pos_fb","scale_fb"]]`、`extra_channels = {scale_fb:{unit:"counts"}}` | 无第二路反馈时 C2 `sensor_disagreement.pairs` 必须为空数组，**禁止**臆造分歧；这也正是 A-46 里"无第二路反馈不得归因"的合成侧对应物 |
| `resonance.estimation`（A-12） | `{window:"hann", nperseg:4096, noverlap:2048, method:"welch", pair_separation_bins:380}` + `resolution_hz = 1.95` | 与 C2 例 A 同形；缺五元组的样本不得被规则引用谱结论 |
| `quality_ref` 来源（A-10） | `quality.quantization_step_counts = 1`、`axis.motor_rev_counts = 524288` | INJ-10 把台阶投到 16 counts 时，`meta` 与 `truth` 必须同时改 |
| `meta.sync`（C6 §3） | 母样本 `verified = true, method = "trigger_edge", uncertainty_ms = 0.0`；孪生样本 `verified = false, method = "unknown"` | 见 §3.3 孪生表与 §5.5 P-12 |


**变体 P-B2（非共置对照）**：同参数，但共振峰由电机侧编码器估计、谷由负载侧光栅尺估计
（`extra_channels.scale_fb` + `cross_validation.pairs`，A-6）。
这是唯一能合法产生"`f_a > f_m`"外观的构型，专门作为 R-04 顺序判据（§1.2）的正反例对。
★ meta 侧必须写 `sensor_config = "mixed"`，并给位置类通道逐通道填 `sensor_side`
（峰来源的电机侧编码器通道 `motor`、谷来源的 `extra_channels.scale_fb` `load`；A-68 已把 C1
值域扩为四值并落地 per-channel `sensor_side`，缺省 `unspecified`、仅 `mixed` 时必填）。
旧临时处置（写 `unknown` + `audit.assumptions`，本文历史版本与 §7 #12 事项列留痕）已作废。
行为后果与 `unknown` 相同——顺序项不参与判定、双惯量配对置信度封顶（C1 派生 7 / C2 规则 9）——
但记录的原因不同，案例意图也不同：见 §5.6 的 `mixed_config` / `unknown_config` 投影对（A-62）。

### 2.3 参数集 (c) P-C：病态案例（专门用来检查 C4 门控是否真的会拦）

三个子案例，各自的**期望结果是"门控失败即本文件失败"**：

**P-C1 模型无法表示（拟合残差门）**
线缆驱动 + **绳索松弛-张紧切换**（外部锚点导致负载侧刚度在松弛/张紧间双向跳变）
+ 齿轮侧隙 12 counts + Stribeck。对象本质非 LTI。
```
期望：C4 的 plant_fit 用两惯量+摩擦去拟合观测波形 →
     fit_residual_pct > 25% → basis 强制降级 rule_heuristic，
     caveats 必须出现"仿真模型无法复现观测波形，改进量不可信"。
     若本案例跑出了 simulation_validated，说明门控是假的（C5 §3「无依据成功声明」= 0 次的硬门禁）。
     注意分工：本案例在 P-A 的 fs=1000 上，R-03/R-04 本就被 freq_limits 频带门拦下；
     P-C1 要测的是 C4 的【拟合残差门】，不是频带门。同时 f_m 在松弛/张紧切换点跳变，
     若在高采样率变体（fs=8000 的 P-A-HS）上重跑，峰应显著宽化、Q 估计失真 → R-04 仍不得触发。
```

**P-C2 建议激发新共振峰（否决门）**
在 P-B 基础上叠加第三惯量分支（夹具/吸嘴模态 `f = 2400 Hz`、`ζ = 0.03`，幅值仅为基线主峰的 20%）。
建议 = 提高位置环增益 30%（或加第一陷波后移相）。
```
期望：baseline+建议 的 cur_q/fe 谱在 2400 Hz 出现新峰，幅值 > 基线主峰的 50%
     → C4「直接否决该建议」分支触发，报告须给出否决理由，而不是给出改进百分比。
     truth.json 记录 expected_gate_action = "reject_candidate"。
```

**P-C3 参数不可辨识（降级门）**
fs = 1000 Hz（沿用 P-A 采样）、但注入 `f_m = 1181 Hz` 的谐振。
```
期望：该模态被奈奎斯特折返 → 合成端预检 P-1 必须在生成前【拒绝】这个工况组合
     （而不是"生成一个折返假峰然后由规则去识别"）。
     若拒绝逻辑失效，会产出一个 truth.json 写着 1181 Hz、C2 却报 181 Hz 的自相矛盾样本，
     这正是不诚实数据生成的典型形态。本案例的 gold 答案是 insufficient_data / 频段不可评估。
```

---

## 3. 扰动 / 故障注入协议

### 3.0 注入项的规范格式（每一项都必须填满这张表）

```
INJ-xx  名称
  落点         : §1.0 总图上的信号线/方程（不是"加噪声"这种含糊说法）
  数学形式     : 闭式或伪代码
  量级参数     : 数值 + 单位（counts / A / Hz / ms），并给 baseline 与 perturbed 两档
  生效段 kind : 取 C1 词表（rest|move|settling|dwell|probing|path|homing|scanning|curing）之一或若干
  事件流       : 是否写 events.jsonl（软件族：必须）
  预期 C2 变化 : 精确点名字段路径 + 方向/量级
  cause slug   : KB0 §2 之一（snake_case，逐字）
  可检测性     : declared_detectable(bool) + 依赖的最低 fs + 依赖的最低通道
  truth 字段   : injected[].{id,slug,magnitude,t_window,segments_kind,expected_features,detectable}
```

`declared_detectable = false` 是**允许且必要**的：注入一个本数据集 fs 下不可见的故障，
用来测 agent 是否会**拒绝下结论**。这类案例是 C5 §2 的 `none_of_the_above` 与"拒答正确率"来源。

### 3.1 `mechanical_*` 族

| ID | 注入 | 量级 | kind | 预期 C2 变化 | cause slug |
|---|---|---|---|---|---|
| INJ-01 | 双惯量谐振峰（调 `k,c`） | `f_m` 按参数集；`ζ_m` 0.02/0.15/0.5 三档 | `move`,`settling`,`dwell` | `resonance.candidates[0].{freq_hz,quality_factor_estimate,amplitude_ratio_vs_broadband,coherence_torque_velocity}`；`spectral.cur_q.dominant_freq_hz` | `mechanical_resonance` |
| INJ-02 | 传动间隙（死区 φ_b） | 8 / 40 / 268 counts 等效 | `move`(反向),`settling` | `global.backlash_estimate_counts`、`reversal_error_counts`；`step_response[].overshoot_pct` 微升 | `mechanical_backlash` |
| INJ-03 | 松动结构（并联二阶低刚度支路） | `f=35 Hz, ζ=0.02`，刚度占比 15% | `move`,`dwell` | `resonance.candidates[]` 出现第二个低 Q 候选；`spectral.fe.tonality_index` 下降 | `mechanical_loose_structure` |
| INJ-04 | 摩擦（τ_s/b/v_s 扫描） | τ_s/τ_c ∈ {1.0,1.5,2.0}；`v_s` 3 档 | `probing`(恒速),`dwell`,`move` 起动 | `global.friction_stiction_ratio`；`crawling.low_speed_segments[].{is_sawtooth,sawtooth_freq_hz,stall_count,vel_min_ratio}` | `mechanical_friction_stiction` / `mechanical_crawling` |
| INJ-05 | 每转周期误差（编码器偏心/刻线误差） | 幅值 3 档，以 counts 记（P-B 定标下 25/100/500 counts）；1 次/转 + 3 次/转 | `probing`,`path` | `encoder.{per_rev_periodic_present, per_rev_amplitude_counts, harmonics_per_rev, detrended_r2, phase_locked_to_pos_modulo}`；`ripple.probing[].dominant_order_per_rev`（原 `dominant_period_counts_per_rev`，量纲为**阶次**，A-11） | `mechanical_encoder_periodic_error` |
| INJ-06 | 热漂移（参数随时间一阶漂移） | `pos_offset` 3 counts/min + `k` 漂移 0.5%/10min，时间常数 30 min | `rest`,`dwell` | `global.thermal_drift_counts_per_min`、`thermal_fe_correlation_r` | `mechanical_thermal_drift` |
| INJ-07 | 惯量比失配（负载质量变化，如吸嘴取/丢片） | λ: 6.2 → 2.0 / 12.0 阶跃，发生在 `move` 中途 | `move`,`settling` | `bandwidth.position_loop_crossover_hz` 偏移；`resonance.candidates[].freq_hz` 前后不一致；`step_response[].{overshoot_pct,ringing_cycles_to_settle}` | `mechanical_double_inertia` |
| INJ-20 | 转矩脉动（机械侧 cogging，每转槽数谐波） | 槽数 `Q_s=12`，`p` 极对数，幅值 3% τ | `probing`,`path` | `ripple.probing[].{ripple_pp_counts,ripple_over_velocity_pct_per_rev,correlated_with_cur_q}` | `mechanical_loose_structure`（若与结构共振耦合）→ 否则归 `electrical_torque_ripple` |

（INJ-04 的 LuGre 变体见 §3.4 的 INJ-23。`crawling.*.sawtooth_freq_hz` 由 §1.3 的粘滑闭式预测
预先算出并写进 `truth.json`，再与同一个 `features()` 的输出比对；偏差 >20% 即判定
"注入器与模型不自洽"，整批作废。）

### 3.2 `electrical_*` 族

| ID | 注入 | 量级 | kind | 预期 C2 变化 | cause slug |
|---|---|---|---|---|---|
| INJ-08 | 电流环带宽下降（L/R 增大、采样延迟加倍） | `f_i` 1200 → 300 Hz | 全段 | `bandwidth.{position_loop_crossover_hz,phase_margin_deg}` 下降；`spectral.fe.dominant_freq_hz` 移到环内高频 | `electrical_current_loop_bandwidth` |
| INJ-09 | 加速度/速度前馈失配（kff 扫描，含 DaRUS 的 1.5） | `kff` ∈ {0, 0.5, 1.0, 1.5, 2.0} | `move` 加速 vs 减速 | `ff_mismatch.{accel_regime_rms_counts,decel_regime_rms_counts,asymmetry_ratio,fe_vs_accel_corr,residual_slope_vs_jerk_corr}`；**`kff<1 ⇒ R>1`、`kff>1 ⇒ R<1`，`corr` 符号由 `1−kff` 决定**（§4.4 预言 2/3） | `electrical_feedforward_mismatch` |
| INJ-10 | 编码器分辨率/量化 | Δ: 1 → 16 counts；或 `vel_fb` 由差分派生 | `rest`,`probing` | `global.fe_sign_change_rate_hz` 上升；`quality.quantization_step_counts`；`spectral.*.tonality_index` 出现宽带抬升；`fe_rms` 地板抬高 | `electrical_resolution_quantization` |
| INJ-11 | 电磁转矩纹动（三相 6k±1，来自电流采样/标定误差） | 3%、8% τ，`n=5,7` | `dwell`,`probing` | `spectral.cur_q.harmonic_ratios = [2,3]` 型结构；`resonance.candidates[].tracks_command_frequency=false` | `electrical_torque_ripple` |
| INJ-12 | 速度环 PI 失谐（积分饱和/带宽过高） | `kvi` ×0.3 / ×4 | `move`,`settling` | `step_response[].{limit_cycle_present,limit_cycle_amplitude_counts,limit_cycle_freq_hz}`；`cur_q_saturation_ratio` | `electrical_velocity_pi_detune` |
| INJ-13 | 位置环 P/PI/PID 增益过高自激 | kp ×1.5/×2.5（使增益交越逼近 `f_a`） | `settling`,`dwell` | `bandwidth.phase_margin_deg` ≤ 10；`cur_q` 出现环内持续啸叫且**在 rest 段也存在** | `electrical_position_pi_detune` |
| INJ-14 | 电机发热（绕组 R 与 Kt 漂移，非机械热） | `R` +15%、`Kt` −8%，随 `temp` 通道一阶相关 | 全程（时间尺度 10–30 min） | `global.thermal_fe_correlation_r`（与 INJ-06 的关键区别：`cur_q_rms_pct` 同向漂移）；`fe_rms` 随时间上升而位置零偏不漂移 | `electrical_motor_heating` |

### 3.3 `software_induced_*` 族（差异化能力；每条都必须真实可注入）

这一族**不是**"给波形加个尖峰"，而是从控制回路/上位机数据流的真实断点注入。
每条都必须同时写 `events.jsonl`（C6 §1 的 `source` 词表），否则 C2 的
`causal_claims_permitted` 门禁会让归因合法地不可用——这是设计意图，不是缺陷。

| ID | 注入（落点 + 数学形式） | 量级 | kind | events.jsonl | 预期 C2 变化 | cause slug |
|---|---|---|---|---|---|---|
| INJ-15 | **上位机线程阻塞 → 一个控制周期无新指令**：`pos_cmd` 在 `[t, t+T_stall]` 冻结为常值（ZOH），`vel_cmd=0` 而 `pos_fb` 继续运动，阻塞结束后指令阶跃恢复 | 单次 1/2/4 个位置周期（P-B: 0.25 / 0.5 / 1.0 ms；P-A: 1 / 2 / 4 ms），另设一档 41.2 ms 对齐 C2 示例的 `host_pause_max_ms`；到达过程取泊松，率 0.5/s | `path`,`move` | `source=host`, `code=thread_stall`（`level=warn`） | `event_context.{host_pause_max_ms,n_by_source.host,fe_spike_count,fe_spike_aligned_to_host_pause,alignment_residual_ms,sync.{method,verified,uncertainty_ms},causal_claims_permitted,step_labels}`（不设 `host_pause_count`，A-8；`alignment_residual_ms` 必须与 `sync.uncertainty_ms` **成对**给出，`alignment_residual_ms` 不大于 `uncertainty_ms` 的对齐不得作证据（C2 规则 8 / A-45））；`global.fe_p999_counts` ≫ `fe_rms`；尖峰段 `fe` 一阶差分跳变 | `software_induced_host_thread_jitter` |
| INJ-16 | **插补缓冲欠载**：前瞻队列长度 `L(t)` 以速率消耗、以批（16 段/40 ms）补充；`L=0` 时把当前轨迹的剩余段全部冻结一拍并强制 `vel_cmd` 骤降到 0 | `L` 阈值 0/1；补充批 8/16；`lookahead_ms ∈ {6,12}`（C2 示例 12） | `path`（仅路径段可发生） | `source=interp`, `code=buffer_underrun`, `detail={buffer_level:0, lookahead_ms}` | `event_context.{interp_underrun_count,interp_underrun_during_path,fe_spike_aligned_to_underrun,alignment_residual_ms,n_by_source.interp,step_labels}`；`tracking.path_segments[].{fe_rms_counts,fe_max_counts,corner_error_counts}` 抬升；`corr_fe_vs_jerk` 异常（指令 jerk 被人为打断） | `software_induced_interp_buffer_underrun` |
| INJ-17 | **总线周期丢失 / WKC 错误**：第 n 拍的 `pos_cmd`、`vel_fb`、`cur_q` 三通道同时**重复上一拍值**（保持），并产生一拍的时间栅格不规则（`dt[k] = 2·T` 或 `T+δ`） | 单次丢 1/2 拍；比率 0.1%–2% | 全段 | `source=network`, `code=missed_cycle` / `wkc_error`, `detail={expected:6,actual:5,hold_ms}`（`hold_ms` = 该拍指令/反馈被保持的时长，是 C2 `bus_cycle_hold_max_ms` 的唯一来源） | `event_context.{network_cycle_miss_count,bus_cycle_hold_max_ms,fe_spike_aligned_to_network_miss,alignment_residual_ms,n_by_source.network,sync.{method,verified,uncertainty_ms},causal_claims_permitted,step_labels}`（A-9 已把这些字段落进 C2，本文不再写"待增补"）；`quality.dt_jitter_ratio` 与 `gap_max_s`（C1 红线 0.2/0.05 是关键阈值）；`global.fe_sign_change_rate_hz` 跳变；`resonance` 谱出现单根宽带线（时基不规则的直接后果，此时 `resonance.estimation.pair_separation_bins` 仍必须随五元组写出，A-12） | `software_induced_bus_cycle_miss` |
| INJ-18 | **视觉结果迟到 → 轴等待后突进**：`vision_x/y/angle` 通道以 15–60 Hz 更新；结果时刻 `t_v = t_trig + latency`，`latency ∈ {5, 31.2, 120} ms`；等待期间轴保持 `rest/dwell`，结果到达后**立即**下发一个短距 `move`（含 `pos_cmd` 阶跃） | `latency_p95 = 31.2 ms`（对齐 C2 示例） | `rest`,`dwell`,`move` | `source=vision`, `code=result`, `detail={dx,dy,latency_ms}` | `event_context.{n_by_source.vision,vision_result_latency_p95_ms,fe_spike_count,fe_spike_aligned_to_vision_result,alignment_residual_ms,sync.verified,causal_claims_permitted,step_labels}`（`fe_spike_aligned_to_vision_result` 已由 A-9 落进 C2，不再是"待增补字段"）；`segments` 出现"长 dwell + 短 move"的固定配对；`step_response[].overshoot_pct` 在等待后突进段偏高 | `software_induced_late_vision_result` |
| INJ-19 | **换型时脉冲当量被覆盖**：在工艺步骤 `step` 边界处把 `counts_per_mm` 从正确值改为 `错误值 = 正确值 × r`，`r ∈ {1/1000, 1/10, 10, 1000}`（直接对应 AUDIT 里"照抄速度参数可能差 1000 倍且机器不报错"的事故模式） | 单次；`r=10`（可检测）与 `r=1000`（应表现为限位/报警或被检出为定标错误） | `move`（覆盖后全部段） | `source=mes`/`process`, `code=scale_changed` + `machine_context.step` 切换, `detail={r, recipe_old, recipe_new}`（配方/步骤边界时间戳是 C2 `fe_spike_aligned_to_recipe_change` 的唯一来源） | `global.fe_rms_counts` 阶跃；`position_quantum_mm` 与 `global.fe_rms_mm` / `tracking.path_segments[].corner_error_counts` 随 `counts_per_mm` **同比例跳变而 counts 域形状不变**（A-13 / C2 规则 11 的合法用法：`*_mm` 与 `*_counts` 的比值就是被覆盖的比例因子，这是本注入唯一可靠的波形侧签名）；`meta.counts_per_mm` 与 `truth.unit_provenance.counts_per_mm.value` 的不一致记在 `truth.json.injected[].detail.scale_mismatch_ratio`。★ 两项已由裁决 A-69 分开收口：(a) `unit_scale_mismatch` **不是 C2 特征**、永远不得当证据路径引用——它只是 `truth.json` 侧的记账标签与叙述用词，其唯一可观测形式就是上文已登记的 `*_mm`/`*_counts` **比值跳变**（KB8 侧同步降级）；(b) 行程限位已登记进 C1：`meta.axis.travel_limit_neg_mm` / `travel_limit_pos_mm`（可选，缺省 `null`，C1 派生规则 8），"目标位置换算成 mm 后超出机械行程"引用该字段——本文 P-A / P-B 母样本缺省写 `null` ⟹ 依赖行程边界的判据一律 `unavailable` + 登记 `blocked_rules`，**禁止**从"波形里位置曾停住"反推限位值再当已知参数用；只有显式给出限位值的变体才允许讨论撞限位分支（旧文"`travel_limit` 未在任何契约登记"的处置随 §7 #13 收口） | `software_induced_pulse_eq_overwritten` |
| INJ-21 | **整定窗口过短**：`io_bit.settled` 由 `abs(fe) ≤ settle_band` 判出，并把 `settling` 段的 `t1` 截断在真正进入 ±band 之前；工件释放/下一步在窗口内被允许 | 截断 20 ms（真需 42 ms，对齐 C3 示例）、band 由配方给出 | `settling` | `source=motion`, `code=move_done`, `detail={settled:true}`（**与真实残振矛盾**） | `step_response[].{settling_time_ms, ringing_cycles_to_settle, limit_cycle_present}` 与实际不符；`event_context.step_labels` 显示下一 `step` 在残振未消时开始 | `software_induced_settle_window_too_short` |
| INJ-22 | **轮询延迟（非周期采集/软件读数路径）**：分析侧或上位机以轮询而非周期中断取数 ⇒ 有效采样时刻抖动 `t[k] = kT + U(−d, +d)`，`pos_cmd` 由软件路径注入（分段常值，非插补） | `d = 0.05/0.15/0.3 · T`；指令阶梯高度 1 count | 全段 | `source=host`, `code=polling_jitter` | `quality.{dt_jitter_ratio, gap_max_s}`；**`dt_jitter_ratio > 0.2` 时必须落进 C1 红线 → 期望 `insufficient_data`**（这正是"注入一个不可检测案例"的合法用法） | `software_induced_polling_latency` |

> `software_induced_*` 7 个 KB0 slug **全部有对应注入项**（INJ-15…19, 21, 22）。
> 其中 5 项是任务点名的核心：线程阻塞（INJ-15）、插补欠载（INJ-16）、总线丢周期（INJ-17）、
> 视觉迟到（INJ-18）、脉冲当量被覆盖（INJ-19）。

**本族的一条硬设计约束**：INJ-15/16/17/18/22 的波形外观与 INJ-01（机械共振）、
INJ-13（自激）、INJ-02（间隙）**部分重叠**。区分它们**唯一的**依据是事件对齐 +
`segments.kind` 语境。因此：
(a) 每个软件注入样本必须同时产出一个"同外观但无事件流"的**孪生样本**（去掉 `events.jsonl`），
    用来验证规则是否会**拒绝**软件侧归因并把它写进 `differential.not_evaluable`（C2 硬约定 8）；
(b) 每个软件注入样本还必须产出一个"有事件流但 `sync.verified=false`"的孪生样本，
    用来验证 `causal_claims_permitted=false` 时只报共现不报因果（C6 §3）。
没有这两对孪生，软件族就退化成了"我们造了个尖峰然后自己认出来"——正是 AUDIT 戳穿 mcopilot 的那个坑。

**`software_induced_bus_cycle_miss` 的分级（裁决 A-45，本文唯一判据口径）**：
本项目的合成侧没有驱动器 WKC 通道，`bus_cycle_hold_max_ms` 与丢拍时刻都是从**单通道 `pos_cmd`
的保持段**推断的，所以期望标签分两档，缺任一条件就不得升级：

| 条件（必须同时成立） | 已登记字段（C2 / C6） |
|---|---|
| ① 两个 event_context 字段均非 null | `event_context.bus_cycle_hold_max_ms != null` **且** `event_context.fe_spike_aligned_to_network_miss != null`（后者为计数，非 null 且 `≥ 1`） |
| ② 同步已验证且因果开关为真 | `event_context.sync.verified == true` **且** `event_context.causal_claims_permitted == true` |
| ③ 对齐残差落在同步不确定度之内 | `event_context.alignment_residual_ms ≤ event_context.sync.uncertainty_ms`（**A-82 方向**，更正 A-50；残差是匹配对 `abs(Δt)` 的中位数，越小越可信。`uncertainty_ms` 缺失时按 C6 取 5 ms 保守值。被声称的**差值** `bus_cycle_hold_max_ms` 要 > `τ_u` 才可分辨，那是纪律 6 的另一半，不写在残差上） |

* 三条**齐**⟹ 该注入案例（INJ-17 母样本）的期望标签可以是 `software_induced_bus_cycle_miss`，
  但 **agent 置信度上限 0.6**（单通道推断，无第二来源佐证；与 C2 规则 12 给 `bandwidth.confidence`
  的同一条"估计类不许更自信"纪律同形）。`truth.json` 侧写
  `injected[].expected.confidence_cap = 0.6`。
* 缺任一 ⟹ 期望标签只能是 `co_occurrence_only`（只进 `differential.considered`）或**拒归因**：
  禁止进 `hypotheses[].cause`，禁止任何"因为丢周期导致该尖峰"的因果句（C2 规则 8 / C6 §3 硬规则 1）。
* ③ 的边界档必须造样本：`alignment_residual_ms` 分别落在 `uncertainty_ms` 的**内侧**与**外侧**，
  内侧那份的 gold 答案是"共现级"——这是 C5 拒答/降级正确率的来源之一。

**"无事件"与"未同步"孪生样本对照表（本项目的核心设计，每个软件族注入都必须有这两份孪生；
裁决 A-61 定版：7 个软件 slug × 3 份 = **7×3 全覆盖**，INJ-19 与 INJ-21 的"无事件孪生"**不接受豁免**——
C2 规则 8 的门禁恰恰是全 7 个，豁免任何一个都等于承认"该 slug 的'没有事件流就不许归因'从未被测过"）**：

| 注入 | 母样本（有事件 + `sync.verified=true`）期望判定 | `no_events` 孪生（删 `events.jsonl`）期望判定 | `unsynced` 孪生（`sync.verified=false` / `method="unknown"`）期望判定 |
|---|---|---|---|
| INJ-15 `host_thread_jitter` | `hypotheses[].cause = software_induced_host_thread_jitter`；`event_context.available=true` | **不许下任何软件侧结论**：`software_induced_error` 必须登记进 `differential.not_evaluable`（C2 规则 8 末句），机械/电气候选照常评 | 只允许时序共现：`fe_spike_aligned_to_host_pause` 可报数，但 `causal_claims_permitted=false` ⟹ **禁因果句**，进 `considered` |
| INJ-16 `interp_buffer_underrun` | 同上（`software_induced_interp_buffer_underrun`） | 同上一条：无 `interp` 事件 ⟹ `interp_underrun_count` 为 null ⟹ 该支路不评估；`tracking.path_segments` 异常只能作为现象 | 只报共现：`fe_spike_aligned_to_underrun` 不得升级成归因 |
| INJ-17 `bus_cycle_miss` | **A-45 三条件齐**才可进 `hypotheses`，且置信度 ≤ 0.6 | `bus_cycle_hold_max_ms = null` ⟹ 条件 ① 不成立 ⟹ 期望 `co_occurrence_only`/拒归因；同时 `quality_ref.dt_jitter_ratio`（A-49 镜像路径）侧现象仍可报 | 条件 ③ 不成立（**A-82**：`alignment_residual_ms > τ_u` ⟹ 对齐残差超出时基预算）⟹ 期望标签 `co_occurrence_only`，禁因果句 |
| INJ-18 `late_vision_result` | `software_induced_late_vision_result`（`vision_result_latency_p95_ms` 非 null） | `event_context.available=false` ⟹ 视觉迟到只能作为"长 dwell + 短 move"的形态描述，**不得**归因 | 只报共现：`fe_spike_aligned_to_vision_result` 计数可给，因果句禁止 |
| INJ-19 `pulse_eq_overwritten` | `software_induced_pulse_eq_overwritten`（`step_labels` + `fe_spike_aligned_to_recipe_change ≥ 1`） | 无配方/步骤事件 ⟹ 期望改为 `electrical_resolution_quantization` 或 `not_evaluable`，**不得**判软件侧（这正是本案例的价值：同一波形，有无事件流的结论不同） | 只报共现，禁"因为换型覆盖导致该阶跃" |
| INJ-21 `settle_window_too_short` | `software_induced_settle_window_too_short`（`step_labels` 显示下一步在残振未消时开始） | 无 `move_done` 事件 ⟹ 只能报 `step_response[].settling_time_ms` 短，**不得**断言窗口被人为截断 | 只报共现 |
| INJ-22 `polling_latency` | `software_induced_polling_latency`；`dt_jitter_ratio > 0.2` 档必须落 `insufficient_data`（C1 红线优先于归因） | 无事件 ⟹ 抖动只能由 `quality.*` 描述，不得归因到软件读数路径 | 只报共现；红线分支结论不变 |

> 三份样本（母 / `no_events` / `unsynced`）的 **`waveform.tsv` 必须逐字节相同**（同种子、同注入时刻），
> 唯一差别是 `events.jsonl` 与 `meta.sync`。这样"结论的差异只能来自上下文"就是可回归验证的；
> 若波形也变了，这组对照就废了（预检 P-12 负责把这条钉住）。
> **A-61 核对结论（本文自查已完成）**：上表现已覆盖全部 7 个软件 slug（INJ-15/16/17/18/19/21/22）×
> 三份（母 / `no_events` / `unsynced`）= 7×3，每行的"无事件孪生"列均有取值；
> INJ-19/21 的孪生**生成依据**由 A-61 定版（KB8 曾报"缺显式生成依据"并申请豁免，裁决不接受豁免）。

### 3.4 组合与对照注入

| ID | 内容 | 目的 |
|---|---|---|
| INJ-23 | LuGre 摩擦（仅"预滑动回弹"演示，必须同批产出 Armstrong 对照） | §1.3 的模型选择必须可被数据推翻 |
| INJ-24 | 外部负载力阶跃 `τ_ext`（锚点/张力切换，绳索场景） | P-C1 的非 LTI 来源；测拟合残差门 |
| INJ-25 | **无故障对照**（健康机器 + 合理噪声） | gold 答案 = `none_of_the_above`，支撑 C5 拒答正确率 ≥80% |
| INJ-26 | **共振 ↔ 前馈失配混淆对**：同一条 `move` 上同时开 INJ-01 与 INJ-09 | C5 §6 点名的最高频混淆对；判别的唯一依据是 `corr_fe_vs_accel` 与"指令静止的 dwell 段峰是否仍在"（C1/R-03） |
| INJ-27 | 多故障叠加（INJ-02 + INJ-10 + INJ-21） | `difficulty` 5 档；测是否给出 Top-3 而非 Top-1 过度自信 |
| INJ-28 | 缺通道 / 缺定标变体（同一物理工况的 3 个投影） | C5 §2 的 difficulty 必需项；测 C1 红线与 `unavailable` 机制 |
| INJ-29 | 陷波器/低通在闭环里造出**人为谷**：在 `f_a` 附近加 notch，使估计出的"反谐振"落在 `f_m` 之上 | §1.2 顺序判据的反例：R-04 **不得**把它判成双惯量配对；其母样本（`motor_side`）同时是 §5.6 `unknown_config` 投影的母样本之一（A-62）——重标为 `unknown` 后"拒绝配对"也不许做，只能"不评" |
| INJ-30 | **非共置传感器构型**（P-B2）：峰由电机侧编码器估、谷由负载侧标尺估 | §1.2 结论"峰+更高频谷只能来自非共置或 ≥3 惯量"的正例；也是 C2 `antiresonance_freq_hz` 语义必须绑定 FRF 构型的理由。meta 写 `sensor_config = "mixed"` + 逐通道 `sensor_side`（A-68，§2.2 P-B2），与 §5.6 `unknown_config` 投影构成"知道是拼的 / 不知道构型"的案例意图对（A-62） |

**T3 纪律（本节的结论，必须逐字出现在合成批次清单里）**：
以上所有注入只证明"**从波形到归因**的这条链在代码上是连着的"，
即：注入 → 物理响应 → C1 → `features()` → C2 → 规则 → C3 假设 → `truth.json` 里的 slug 对得上。
它**不证明**任何真实设备上的诊断准确率（C5 §1）。任何把这些结果写成"检出率/命中率"的
文档、幻灯片或 README 都必须视为缺陷并修正。

**证据层级分配（裁决 A-43，软件族的条件性开禁）**：本文件已把事件注入建模到
host 停顿 / 插补欠载 / 丢周期，并按上表强制产出"无事件"与"未同步"孪生，因此——

| 结论类别 | 允许的 `basis` / tier | 约束 |
|---|---|---|
| **检出类**（"这类形态在给定上下文下可被检出/可被区分"） | 软件族判据可标 `simulation_validated`；T3 tier | 只有孪生三件套齐全（母样本 + `no_events` + `unsynced`）且 P-12 通过的批次才计入；缺孪生的批次降级为 `rule_heuristic` |
| **改进量 / 参数建议**（`expected_effect`、"提高增益 X% 后 fe_rms 降 Y%"） | **一律 `rule_heuristic`**，永不因仿真升级 | 报告不得给出改进百分比数字（§6.3 禁令 + C3 规则 4） |
| 引用仿真的任何叙述 | — | **必须写 caveat**：`"仿真不含真实调度器与总线仲裁"`（与"仿真模型由本波形反拟合，改进量是模型内推值"并列，缺一不可） |

理由说白：本模型的"停顿/丢拍"是**确定性或泊松到达的人为时序**（§6.1），
既没有 OS 调度器也没有 EtherCAT 主站的仲裁与重试，所以它能证明"管线走到哪条支路"，
不能证明"真机上这样调会好多少"。A-43 开的是**检出类**的口子，不是效果类的口子。

---

## 4. S 曲线 / 运动指令生成规范

### 4.1 出处与实现边界

**参考来源（设计思路，非代码）**：`motion_lab.py` 的七段 jerk 受限轨迹生成器，
路径
`C:\Users\admin\.minimax\sessions\mvs_838bec01bb00476594f48711e6b172d0\workspace\mcopilot\src\mcopilot\agents\motion_lab.py`
（`_accel_phase` / `build_profile` / `Segment` 的段状态传播结构）。
依据 `docs/AUDIT-minimax-mcopilot.md` §三（"`motion` 模块进 C4 轨迹发生器"）与 §三后的
归属纪律（"复用部分必须标注来源，不得以'我写的'呈现"）：

* **借鉴**：七段对称结构（+j / 0 / −j | 匀速 | −j / 0 / +j）、`a_eff = min(a_max, √(v·j))`
  的加速度受 jerk 约束这一物理上限、峰值速度不足时用二分回解、以及用黄金向量做回归。
* **自己重写**：退化情形的**闭式**解法（本文件用解析式替代纯二分）、jerk 受限系统的
  `e ≈ a/ω_n²` 前向预测（改为带 kff 与摩擦的修正项）、分段必须对齐采样栅格（§4.4）、
  以及全部自检不变量（§4.5）。
* 不复制任何代码行。本文件的伪代码是规范描述，不是移植。

### 4.2 七段时序与解析式

记 `j = j_max > 0`，`a = a_max > 0`，`v = v_max > 0`，行程 `D > 0`（方向符号 `s = sign(D)` 最后乘入）。
半程（加速半边）由 3 段组成，减速半边镜像对称。

```
段 1: jerk = +j,   时长 t1,   a: 0 → a_e,          v: 0 → v1 = a_e t1/2,        x: x1 = j t1³/6
段 2: jerk =  0,   时长 t2,   a = a_e 常值,          v: v1 → v2 = v1 + a_e t2,   x: x2 = v1 t2 + a_e t2²/2
段 3: jerk = −j,   时长 t3,   a: a_e → 0,           v: v2 → v_p,                x: x3 = v2 t3 + a_e t3²/2 − j t3³/6
段 4: jerk =  0,   时长 tv,   a = 0, v = v_p,       x: x4 = v_p tv
段 5: jerk = −j,   时长 t5,   a: 0 → −a_e'
段 6: jerk =  0,   时长 t6,   a = −a_e'
段 7: jerk = +j,   时长 t7,   a: −a_e' → 0, v → 0
```

半程一般关系（`t1 = t3`，对称）：

```
a_e = min( a, √(v_p j) )            ★ 若 v_p < a²/j，加速度根本碰不到 a_max（jerk 主导）
t1 = t3 = a_e / j
v1  = a_e t1 / 2 = a_e²/(2j)
t2  = max(0, (v_p − 2 v1) / a_e)
x_h = x1 + x2 + x3                  半程位移
```

三种退化情形（必须全部实现，否则短行程工况会静默出错）：

```
I   梯形速度（v_p = v_max，t2 > 0，tv > 0）
      条件：2 x_h(v_max) ≥ D 且 v_max ≥ a²/j
II  纯 jerk 三角（t2 = 0，a_e = √(v_p j)，tv > 0）
      t1 = t3 = √(v_p / j)，v_p = 2 v1 = a_e t1
      半程位移闭式：x_h = j t1³ = v_p t1 = v_p √(v_p / j) = v_p^{3/2}/√j
      ★ 干净恒等式 x_h = v_p·t1 —— 用作 §4.5 不变量 I5 的解析校验
III 无匀速（tv = 0，D = 2 x_h）—— 反解 v_p：
      情形 III-a（v_p < a²/j）：由闭式 D = 2 v_p^{3/2}/√j ⇒ v_p = (D √j / 2)^{2/3}
      情形 III-b（a²/j < v_p < v_max）：x_h(v_p) = v_p(a/j) + a((v_p − a²/j)/a)²/2 + a³/(6j²)...
        该式单调 ⇒ 用 Newton（初值取 III-a 闭式解，或 [0, v_max] 上二分 60 次；
        AUDIT 记录里该反解在 4 组工况下端点误差 < 1e-6 mm（**二手转录**，A-32 的署名纪律；
        本文只把它当作黄金向量的**参照量级**，不据此声称本文的反解已核对通过——
        真正的判定权在 §4.5 的黄金向量重跑，实现期之前它只是"待执行"）
```

总时间与一致性：

```
T_total = 2(t1 + t2 + t3) + tv
D_calc  = s · (2 x_h + v_p tv)         必须 ≡ D
```

### 4.3 采样栅格对齐（诊断侧的关键要求）

`pos_cmd` 必须**在数据采样时刻 `t_k = k/fs` 上被求值**，因此段边界 `t_i` 与 `t_k` 不重合时，
落盘的 `pos_cmd[k]` 是"段解析式在该时刻的真值"（连续公式求值），而不是段平均。由此：

* 段边界与采样时刻的错位 `ε_k = min |t_i − t_k|` 必须记入 `truth.json`（`boundary_residual_ms`）；
* 若要求 `segments[].kind` 的边界精确可辨（C1 分段是"必需"的），则应让 `1/fs` 整除段边界：
  把 `t1,t2,t3,tv` 各自**取整到最近采样拍**，然后**重解 `v_p`/`tv` 以保证位移闭合**
  （优先保 `D`，允许 `T_total` 有 ±0.5 拍变化）；
* 不允许"把段边界之后的第一拍"归给前一段——分段归属错误会让 `ff_mismatch` 的
  加速/减速分域统计串味（C2 的 `accel_regime_rms` 与 `decel_regime_rms` 会互相污染）。

### 4.4 为什么诊断器需要**已知**的指令形状

只有指令形状已知，才能把"**应有**的跟随误差"算出来，从而把观测误差与理论误差做差。

低频（远低于 `f_m`）时传动可视为刚性：`J_tot θ̈ = τ_m − τ_f·sign(θ̇)`。
控制器 `τ_m = kp·e + kff·J_tot·a_c`（`a_c = θ̈_c` 为指令加速度，速度前馈归入内环）。
令 `e = θ_c − θ` 在恒定 `a_c` 下为常值，得**闭式稳态跟随误差**：

```
ω_n² = kp / J_tot                              闭环自然频率（速度/电流环视为理想）

        (1 − kff)·a_c          τ_f(v)
e_theory = ─────────────  +  ──────────        ★ 摩擦项除 kp，惯性项除 ω_n²，不可混
                 ω_n²              kp
```

记 `A = (1−kff)·a/ω_n²`（可负），`B = τ_f/kp ≥ 0`。加速段 `v>0, a_c>0` ⇒ `e_a = A + B`；
减速段 `v>0, a_c<0` ⇒ `e_d = −A + B`。据此得到**四条可在 T1-a 上直接核对、且能推翻本模型的预言**
（属于"模型 + 代数"，不是自证）：

1. **纯 P 环、无前馈、无摩擦** ⇒ `e = a/ω_n²`，`corr_fe_vs_accel → +1`，比例系数就是 `1/ω_n²`。
   这给出 ω_n 的**免激励估计**：`ω_n² ≈ a/e`。
2. **`kff = 1.5`（DaRUS 发布值）⇒ `A < 0`** ⇒ `corr_fe_vs_accel` 应为**负**
   （在一整条 `move` 内 `sign(v)` 不变 ⇒ 摩擦项是常量偏移，不参与相关，因此**符号只由 `1−kff`
   决定**，摩擦只把 `|corr|` 往 0 稀释而不翻转它）。
   → 若在 T1-a 上该相关为正，唯一诚实的解释是：那个 `kff` 不是加速度前馈（而是速度前馈）、
   或符号约定相反、或窗口里几乎没有加速度变化。**这是一个能被真实数据否证的预言，写它的价值
   正在于此。**
3. **不对称方向能直接读出 kff 在 1 的哪一边**（`asymmetry_ratio = accel_regime_rms/decel_regime_rms`）：

   ```
   kff < 1 ⇒ R = (A+B)/(A−B) > 1        加速段偏差更大
   kff = 1 ⇒ R = 1                      纯摩擦，对称
   kff > 1 ⇒ R = |B−|A||/(B+|A|) < 1     减速段偏差更大  ★ 方向本身就是判据
   ── 反解： B/A = (R−1)/(R+1) ⇒  τ_f = [(R−1)/(R+1)]·(1−kff)·J_tot·a
   ```
   **自洽核对**：C2 示例 `R = 2.26` ⇒ `B/A = 0.386`。取 P-B 参数（`kff=0.5`、
   `J_tot = 8.11e-6 kg·m²`、`a = 2.36e4 rad/s²`）⇒ `τ_f ≈ 3.7e-2 N·m`，
   与本参数集设定的 `τ_c = 0.035` 同量级 —— 说明 C2 的示例数值在物理上自洽，
   也说明 `asymmetry_ratio` 不是"越大越严重"，而是**带方向的量**。
   （若某条规则写成"asymmetry > 1 即前馈不足"，它在 `kff>1` 的设备上会**系统性漏判**。）
4. **共振与前馈失配的分离依据**：机械共振（INJ-01）的纹波与 `a(t)` 形状无关，
   且在 `dwell`（指令静止）段**继续存在**；前馈失配（INJ-09）的纹波**只在 `|a|>0` 的窗口存在**，
   `rest`/`dwell` 段为 0。→ 这就是 `resonance.candidates[].present_in_rest`
   与 `tracking.*.corr_fe_vs_accel` 能把 C5 §6 点名的混淆对分开的机理，也是 INJ-26 存在的理由。

因此指令形状的已知性有三个具体用途：`e_theory` 对照、`accel/decel` 分域
（C2 的 `accel_regime_rms_counts` / `decel_regime_rms_counts` 字段名本身就依赖它）、
以及 `residual_slope_vs_jerk_corr`（需要已知 jerk 段）。
**任何 `pos_cmd` 未知（只有 `fe` + `pos_fb`）的样本，上述四条必须整体失效并登记进
`unavailable` + `differential.not_evaluable`**（C1 派生规则 3 的下游后果）。

### 4.5 轨迹生成器的自检不变量（全部必须通过才能写文件）

```
I1 位移闭合   |D_calc − D| ≤ 0.05 count（在 counts_per_mm 已知时同时报 mm）
I2 速度端点   |v(0)| = 0 且 |v(T_total)| ≤ 1e-9·v_max
I3 加速度端点 |a(0)| = |a(T)| ≤ 1e-9·a_max
I4 各段边界连续（C²） |Δx|,|Δv|,|Δa| ≤ 1e-9 相对量（jerk 允许按设计跳变，且只允许在 7 个边界跳）
I5 恒等式     情形 II 下 x_h == v_p·t1（解析校验，相对误差 < 1e-12）
I6 jerk 分段和 Σ ∫j dt = 0（净加速度变化为零）
I7 限幅遵守  |a(t)| ≤ a_max(1+1e-9)，|v(t)| ≤ v_max(1+1e-9)，|j| = j_max（不"软超"）
I8 jerk 段数 实际生成的非零 jerk 段数 ∈ {2,4,6}，退化段（时长 0）不出现在 truth 的 segment 列表
I9 时间栅格   段边界残差 boundary_residual_ms 已记录；若要求整除则全部为 0
I10 符号      pos_cmd 单调（单向移动内 dpos_cmd ≥ 0）；反向移动用 s=−1 整条镜像，不得用镜像后再差分
I11 量级      T_total 与 tv/tv 的比值合理（tv<0 时报错，不允许静默改 D）
I12 位移-分段一致 meta.segments 的每个 move 段边界与 §4.3 的采样对齐边界逐点一致
```

失败即**拒绝生成样本**（不是"记录警告继续"）。理由：轨迹的位移不闭合会让
`truth.json` 里的目标位置与实际指令不一致，从而污染整个评测链——这种污染恰好是本文件要防的。

**I1–I12 的证据层级（措辞纪律，A-31）**：这十二条全是**解析 / 自洽校验**——
位移闭合（I1）、情形 II 的恒等式 `x_h = v_p·t1`（I5）、 jerk 段和为零（I6）、
段边界连续（I4）都是代数恒等式或构造性质，它们既不是实测，也不能证明轨迹生成器"已验证正确"。
本文与任何由本文生成的报告里，允许的说法只有：
"按构造成立 / 由闭式解保证 / 待实现期重跑（黄金向量）"；
"实测通过""已核对无误""稳定性已验证"一类措辞**一律禁止**。
§1.5 的数值稳定性判据同理：`ω·h ≲ 2.8` 是 RK4 的教科书稳定域边界推导，不是本文跑出来的数。

黄金向量（回归基准，非产品代码）：至少 4 组，覆盖情形 I / II / III-a / III-b 与 `D<0`；
每组登记 `(D,v,a,j) → (t1,t2,t3,tv,v_p,T_total)` 的 9 位有效数字，与 §4.2 闭式解逐一比对。
**本期只登记黄金向量的结构与出处，不产出数值结果**（不写产品代码，KB0 §6.6）；
它们纳入 `bench/` 是 §7 #8 的实现期任务，本文不声称已完成。

---

## 5. 合成数据输出规范

### 5.1 样本包

```
synth/<batch>/<sample_id>/
  meta.json        # C1 schema 原样，不加新顶层键（除 truth-only 信息不进这里）
  waveform.tsv     # C1：TAB 分隔，UTF-8，首行表头，第 1 列 t（秒，从 0，单调递增）
  events.jsonl     # C6：软件族注入必写；无事件样本刻意缺失（INJ-28）
  truth.json       # 仅合成有；§5.4
  truth/notes.md   # 可选：本批次的出处/种子/版本
synth/<batch>/manifest.jsonl        # 一行一样本，含 tier 与预检结果
synth/<batch>/selfcheck.json        # §5.5 预检清单的逐条 PASS/FAIL + 统计
```

### 5.2 waveform.tsv 列命名

列名**逐字**取 C1 通道词表；缺失通道**不出现在表头**（不写空列）：

```
t  pos_cmd  pos_fb  fe  vel_cmd  vel_fb  cur_q  cur_cmd  torque  temp  io
vision_x  vision_y  vision_angle
```

* `fe` 建议**同时**由生成器写出并自检：`fe ≡ pos_cmd − pos_fb`（残差 ≤ 1e-9 counts）。
  C1 的派生规则 1 允许 loader 重算，两者必须一致——不一致就是 loader 或生成器的 bug。
* `vel_fb` 若由位置差分派生（INJ-22/17 的抖动栅格下常见），`meta.channels.vel_fb.derived=true`
  且接受"频谱类判据置信度 ×0.7"（C1 派生规则 4）。生成器不得为了"好看"而偷偷写解析速度。
* 坏点写 `nan`；`nan` 的比例由预检 P-4 控制。
* 视觉通道按 C1 要求降采样到 15–60 Hz（在 T_log 的整数倍栅格上出数，别用非栅格时刻）。

### 5.3 meta.json（合成侧要点，完整字段以 C1 为准）

```jsonc
{
  "schema": "axiscope.waveform/1",
  "source": {"vendor": "axiscope-synth", "drive_model": "KB5 two-inertia plant P-B",
             "export_format": "synth-tsv", "original_filename": "P-B__INJ01_s0007.tsv",
             "ingest_confidence": 1.0},
  "sample_rate_hz": 8000.0, "sample_rate_source": "declared",
  "units_are": "counts",             // A-4；P-A 默认写 "si_native"（DaRUS 是 m / m/s / N·m）
  "counts_per_mm": 50000.0,          // 或 null（INJ-28 的缺定标变体）→ C2 的 position_quantum_mm 随之为 null
  "encoder_lines": 16777216, "rated_current_a": 4.6,   // 4.6 = assumed（借自 MSK061C，§2.0）
  "axis": {"name": "X1", "type": "linear", "motor_rev_counts": 524288,
           "travel_limit_neg_mm": null, "travel_limit_pos_mm": null},  // A-69/C1 axis；母样本缺省 null ⟹ 行程类判据 unavailable+blocked_rules
  "sensor_config": "motor_side",     // A-1 / A-68 / C1 派生 7；{motor_side|load_side|mixed|unknown} 四值；mixed 时逐通道 sensor_side 必填
  "cross_validation": {              // A-6；P-B 母样本单路反馈 ⟹ pairs 为空数组
    "pairs": [],                     // P-B2 变体：[["pos_fb","scale_fb"]]
    "note": "无第二路反馈时不得臆造分歧；C2 sensor_disagreement.pairs 随之为空"
  },
  "extra_channels": {},              // A-6；P-A 写三路位置反馈（§2.1 表）；P-B2 写 scale_fb:{unit:"counts"}
  "drive": {"position_loop_period_us": 250, "velocity_loop_gain_hz": 300.0,
            "current_loop_bandwidth_hz": 1200.0,   // A-42；未发布时一律 null（P-A 即 null）
            "rated_torque_N_m": 6.9,               // A-70；P-B 档 = assumed 4.6 A × assumed Kt 1.5（§2.2）；P-A 档 = 32.0（A-27 限定语）
            "rated_torque_source": "assumed",      // {measured|manual|nameplate|assumed}；assumed ⟹ *_pct 封顶 T2 + 强制 caveat（§5.3 纪律 12）
            "rigidity_level": 12, "notch_filters": [], "inertia_ratio": 6.18},
  "present_channels": ["pos_cmd","pos_fb","fe","vel_cmd","vel_fb","cur_q","temp"],
  "channels": { "...": "raw_column 写 <解析器无关的合成变量名>；unit; sign; offset; inferred; confidence" },
  "io_bits": {"0":"home_sensor","1":"limit_neg","2":"limit_pos","8":"settled"},
  "segments": [{"id":0,"kind":"move","t0":0.012,"t1":0.089,"axis":"X1"}, ...],
  "quality": {"n_samples": 16000, "dt_median_s": 0.000125, "dt_jitter_ratio": 0.0,
               "gap_max_s": 0.000125, "nan_ratio": 0.0, "quantization_step_counts": 1.0,
               "nyquist_hz": 4000.0, "flags": ["synthetic","time_column_relative"]},
  "context": {"machine": "共晶贴片机 X 轴", "complaint": "...", "operator_notes": "..."},
  "machine_context": {"machine_type": "die_attach", "control_card": "beckhoff TC3",
                       "recipe": "AuSn_280C_die4", "step": "place", "step_sequence": [...]},
  "sync": {"method": "trigger_edge", "offset_s": 0.0, "uncertainty_ms": 0.0,
            "verified": true, "evidence": "合成侧同一时钟，构造性成立（孪生样本可置 false）"}
}
```

**本例是 P-B（counts 基准）**；P-A 的 meta 侧取值（`units_are = "si_native"`、
`drive.current_loop_bandwidth_hz = null`、`counts_per_mm = 5.8349` ⟹ C2 侧
`position_quantum_mm = 0.1714`、三路位置反馈走
`extra_channels`）见 §2.1 的表，两者必须能由同一份写出代码按参数集切换。
`channels.cur_q.unit = "A"` 与 `channels.torque.unit ∈ {percent_of_rated, N_m}` **必须显式写**
（A-4 / A-14），不得靠 C1 的默认值。

（`sync` 块由 C6 §3 定义。合成侧默认 `verified=true` 是构造性的；
§3.3 要求**必须**另有 `verified=false` / `method="unknown"` 的孪生样本，用来测因果门禁。）

必须遵守的取值纪律：

1. `source.vendor` 恒为 `axiscope-synth`，`quality.flags` 必含 `"synthetic"`。
   **任何**让合成样本看起来像厂商导出的字段（伪造 `original_filename` 时间戳、伪造
   `ingest_confidence<1`）都禁止。
2. `segments[].kind` **严格取 C1 词表的 9 个值**：
   `rest` `move` `settling` `dwell` `probing` `path` `homing` `scanning` `curing`
   （`unknown` 只作为 loader 的兜底，生成器**不得**主动写 `unknown`）。
3. 合成样本**应当**填满 `drive.*`（否则 C1 的"依赖该字段的判据降级为 unverified"会让每条
   规则都降级，测不到想测的东西）。但**必须**另外产出 `drive` 字段逐个缺失的 INJ-28 变体，
   专门验证降级路径真的存在。
   ★ 唯一的例外是**没有依据可填**的字段：`drive.current_loop_bandwidth_hz` 在 P-A 上必须是 `null`
   （DaRUS 未发布电流环带宽），此时 KB3 R-12 走支路 B 并降 `unverified` 就是**期望行为**，
   不得为了"填满"而编一个数（A-42）。
4. `counts_per_mm` 缺失变体（`starved_scale`）里，**同时**禁止生成任何 `*_mm` 字段（C2 硬约定 3），
   并且 C2 侧 `position_quantum_mm` 必为 `null`（A-13）、报告只印 `[counts]`（C1 单位规则）。
   `si_native` 的 P-A 变体同理：缺定标不得臆造**任何**其它单位（例如把 m 冒充 µm 级精度，A-4）。
5. `context.machine` 的措辞按参数集固定：P-A 一律写"线缆驱动试验台/绳索卷筒"，
   P-B 一律写"共晶贴片机 X 轴"。**禁止把 P-A 的样本描述成半导体产线数据**——它是线缆驱动
   试验台锚点（§2.1），两个参数集都不构成"真实设备实测"。
6. `units_are`（A-4）必须逐样本显式写：P-A → `"si_native"`，P-B → `"counts"`；
   `channels.cur_q.unit` / `channels.torque.unit` 同步显式写，`*_pct` 类字段在 `rated_current_a`
   /`Kt` 标定链缺失时必须为 `null`（A-14、§1.1 硬约束 3）。
7. `sensor_config`（A-1 / A-68）必填，值域四值 `{motor_side, load_side, mixed, unknown}`：
   P-A / P-B 母样本 `motor_side`；负载侧单独估谱的变体 `load_side`；P-B2 / INJ-30 混合构型写
   `mixed` **且位置类通道必须逐通道填 `sensor_side`**（峰来源 `motor`、谷来源 `load`；C1 派生 7，
   缺省 `unspecified` 只在非 `mixed` 时合法）——旧"写 `unknown` + `audit.assumptions`"处置已随
   A-68 作废（§7 #12）；`unknown` 在本文件只出现于 §5.6 `unknown_config` 投影（故意重标，A-62）。
   `mixed` 与 `unknown` 行为相同（顺序项不评、置信度封顶），登记原因不同：前者记录"峰谷来自两套
   通道、不是同一传递函数的零极点交替"，后者记录"不知道装在哪侧"。
8. `cross_validation.pairs` 与 `extra_channels`（A-6）必须成对出现：凡写出 `pairs` 里第二元素名的，
   该名字**必须**存在于 `extra_channels` 且**不得**占用 C1 通道词表名；无第二路反馈时 `pairs` 写
   空数组而不是省略整个块。
9. **单一载体纪律**：`position_quantum_mm` / `quality_ref`（A-13 / A-10）是 **C2 侧派生字段**，
   合成端**不得**把它们写进 `meta.json`（§5.1 的"不加新顶层键"），只在 `meta` 里留下派生输入：
   `counts_per_mm`、`quality.quantization_step_counts`、`axis.motor_rev_counts`。双载体必然漂移。
10. `meta` 与 `truth` 的同一物理量必须一致（`counts_per_mm`、`f_m`、`f_a`、`quantization_step_counts`、
    `current_loop_bandwidth_hz`）；INJ-19 是唯一被允许制造不一致的注入，且不一致量必须记在
    `truth.json.injected[].detail` 里而不是靠读者猜。
11. **loader 兼容即验收**（KB0 §6 检查 4）：每个批次必须有样本被 C1 loader **原样**读入并通过
    C1 红线；`schema`、通道列名、`segments.kind` 词汇、单位规则都属契约面，违反就是写出侧的 bug，
    不允许"loader 改一改就能读"。
12. **额定转矩分母（裁决 A-70，§7 #14 就此收口）**：`drive.rated_torque_N_m`（可空）+
    `drive.rated_torque_source ∈ {measured, manual, nameplate, assumed}` 是转矩侧百分比归一化的
    唯一合法分母（C1 单位规则 / C2 规则 3）。本文件**没有任何** `measured`/`manual` 来源，
    逐参数集档位（与 §2.1 / §2.2 两张 meta 表同口径）：
    P-A → `32.0` + `assumed`（附"XML 原值无量纲、疑为齿轮输出侧量"限定，A-27 同一事实的另一面；
    DaRUS / KB7 侧 `torque_max = 32` 落**同一档**）；
    P-B / P-B2 → `6.9` + `assumed`（= assumed `rated_current_a` 4.6 A × assumed `Kt` 1.5 N·m/A，
    §2.2 力矩核对，换算链逐环可复算）；
    INJ-28 / `starved_*` 变体 → `null` + `null`（⟹ 转矩 `*_pct` 恒 `null`，只有 `N_m`/`A` 分支成立）。
    凡 `assumed` 档样本：百分比类判据（`cur_q_saturation_ratio`、`*_pct` 阈值类）**证据层级封顶 T2**，
    且报告 caveats 必须逐字含"额定转矩为假定值，百分比类判据的绝对刻度不可信"（C1/C2 现文）；
    `rated_torque_N_m` 与 `rated_current_a`/`Kt` 的不一致（乘积对不上）由写出侧自检拦截。

### 5.4 truth.json（合成专属；真实数据严禁有）

```jsonc
{
  "schema": "axiscope.truth/1",
  "generator": {"doc": "docs/kb/KB5-simulation-plant.md", "impl_sha": "<git sha>",
                 "param_set": "P-B", "seed": 20261019, "solver": "expm-zoh",
                 "h_int_s": 6e-6, "K_substeps": 20},
  "source_tier": "T3",
  "claims_permitted": ["pipeline_reachable", "regression_non_degradation"],
  "claims_forbidden": ["accuracy", "top1_hit_rate", "field_effective", "simulated==real_validity"],
  "unit_provenance": {"counts_per_mm": {"value": 50000.0, "derivation": "grating_pitch 20nm",
                        "provenance": "assumed"}},
  "plant": {"model": "two_inertia_plus_friction",
            "params": [{"name":"J_m","value":1.126e-6,"unit":"kg m^2","provenance":"assumed"},
                       {"name":"J_l_ref","value":6.96e-6,"unit":"kg m^2","provenance":"assumed"},
                       {"name":"lambda","value":6.18,"provenance":"assumed"},
                       {"name":"k","value":53.2,"unit":"N m/rad (referred to motor)","provenance":"assumed"},
                       {"name":"c","value":2.72e-4,"derived_from":"zeta_m=0.019","provenance":"derived"},
                       {"name":"f_m","value":1181.0,"provenance":"derived"},
                       {"name":"f_a","value":440.0,"provenance":"derived"},
                       {"name":"friction_model","value":"armstrong_one_step"},
                       {"name":"tau_s","value":0.06,"provenance":"T2: DaRUS-5171 LdaFricIdent"}],
            "optional_branches": [], "non_lti_elements": []},
  "controller": {"structure":"pos_pid+vel_pi+cur_pi","T_pos_s":2.5e-4,"T_vel_s":1.25e-4,
                  "T_cur_s":6.25e-5,"kff":1.0,"kp":2.31,"ki":247.0,"kd":0.0217,
                  "gain_unit":"N m per rad (motor-side referred)","notch":[],"cmd_filter_hz":null},
  "command_profile": {"type":"s_curve_7seg","D_mm":3.2,"v_max":1500.0,"a_max":30000.0,
                       "j_max":1e7,"regime":"III-b","v_peak_mm_s":269.0,
                       "T_total_s":0.0239,"displacement_closure_counts":0.018,
                       "boundary_residual_ms":0.0,"invariants_passed":["I1","I2","…","I12"],
                       "segments":[{"jerk":+1e7,"dur":3.0e-3},{"jerk":0,"dur":5.97e-3},
                                   {"jerk":-1e7,"dur":3.0e-3},{"jerk":-1e7,"dur":3.0e-3},
                                   {"jerk":0,"dur":5.97e-3},{"jerk":+1e7,"dur":3.0e-3}]},
  "injected": [
    {"id":"INJ-01","slug":"mechanical_resonance","magnitude":{"f_m_hz":1181.0,"zeta_m":0.02},
     "segments_kind":["move","settling","dwell"],
     "t_window":[0.089,0.140],
     "expected_feature_changes":[{"path":"resonance.candidates[0].freq_hz","op":"~","value":1181.0},
                                  {"path":"resonance.candidates[0].antiresonance_freq_hz","op":"<","ref":"resonance.candidates[0].freq_hz"},
                                  {"path":"resonance.candidates[0].present_in_rest","op":"==","value":false},
                                  {"path":"resonance.estimation.method","op":"==","value":"welch"},
                                  {"path":"resonance.estimation.pair_separation_bins","op":">=","value":2}],
     "spectrum_estimation":{"window":"hann","nperseg":4096,"noverlap":2048,"method":"welch",
                             "pair_separation_bins":380,"resolution_hz":1.95},
     "declared_detectable": true,
     "requires":{"fs_hz_min":5000,"channels":["cur_q","vel_fb"],"event_source":null}}
  ],
  "expected_gate_behavior": {"c4_fit_residual_pct_max":25.0,
                              "basis":"simulation_validated",
                              "reject_candidate":false},
  "self_check": {"features_sha256":"…","n_channels":7,"energy_residual_pct":0.31,
                  "loaded_by_c1_loader":true, "features_from_same_kernel_as_real":true},
  "c5_case": {"case_id":"T3-PB-INJ01-0007","difficulty":3,
               "present_channels":["pos_cmd","pos_fb","fe","vel_cmd","vel_fb","cur_q","temp"],
               "counts_per_mm":50000.0,
               "gold_root_cause":"mechanical_resonance",
               "gold_params":[{"name":"f_m_hz","value":1181.0,"tol":0.05}],
               "forbidden_conclusions":["field_effective","thermal_drift","kHz_absent"]}
}
```

语义纪律：

* `provenance` ∈ `{published, T2-literature, derived, fitted, assumed}` 逐参数必填。
  `assumed` 项在报告引用时必须带"假设值"字样。
* `claims_forbidden` 是**给 CI 用的**，不是装饰：任何把 T3 样本计入能力指标的产物，
  检查器看到 `source_tier == "T3"` 就必须失败。
* 真实样本包内出现 `truth.json` ⇒ **loader 直接拒收并报错**：这一条**已升格为 C1 的目录结构规则**
  （C1 "真实样本包内出现 `truth.json` 即为污染：加载器必须拒收并报错"），本文 §7 #5 就此闭环，
  不再是"建议"。本文侧同时自行校验：`truth.json` 存在 ⇔ `meta.source.vendor == "axiscope-synth"`，
  且 P-A（`si_native`）与 P-B（`counts`）的 `truth.unit_provenance` 都必须记录单位来源。
* `rules()`/`features()` 的代码路径里禁止出现 `truth.json` 的读取（§0 反向要求）。
* `c5_case.counts_per_mm` 是**唯一可写的那个数**（A-56/A-66）：`position_quantum_mm = 1/counts_per_mm`
  由 C2 派生，案例侧**不单列**（两处都写必打架）。A-13 的对照即由本字段单源产生：
  P-A 写 `5.8349`（⟹ 量子 `0.1714` mm；本集 `units_are = "si_native"` 但该值有 §1.1 推导链，
  故按 A-75 写数值而非 `null`）、P-B 写 `50000.0`（⟹ `0.00002` mm）、
  `starved_scale` 变体写 `null`（⟹ 量子 `null`，精度声明一律改写为"低于本数据分辨率"）。

**软件族注入的 truth 侧记账（A-9 / A-45 / 孪生，`injected[]` 元素的扩展形状）**：

```jsonc
{"id":"INJ-17","slug":"software_induced_bus_cycle_miss",
 "magnitude":{"miss_ratio":0.01,"hold_ms":2.1,"cycles_held":1},
 "segments_kind":["path","move"],"t_window":[0.2015,0.2019],
 "expected_feature_changes":[
   {"path":"event_context.bus_cycle_hold_max_ms","op":"~","value":2.1},
   {"path":"event_context.network_cycle_miss_count","op":">=","value":1},
   {"path":"event_context.fe_spike_aligned_to_network_miss","op":">=","value":1},
   {"path":"event_context.alignment_residual_ms","op":">","value":"sync.uncertainty_ms"}],
 "expected":{"label":"software_induced_bus_cycle_miss","confidence_cap":0.6,   // A-45 三条齐全才允许升级
             "caveats":["仿真不含真实调度器与总线仲裁"]},                        // A-43 强制 caveat
 "basis":"simulation_validated",   // 仅检出类；改进量一律 rule_heuristic（A-43）
 "twin_group":"TWIN-17-0007",                    // 三份样本共用同一波形与同一组注入时刻
 "context_role":"parent",                        // parent | no_events | unsynced
 "waveform_sha256_shared_by_twins":"…"}          // P-12 校验三份孪生的波形逐字节相同
```

`no_events` 孪生的 `expected.label` 必须写成 `co_occurrence_only`（或 `not_evaluable`）且
`confidence_cap` 无效；`unsynced` 孪生的 `expected.forbid_causal_phrases = true`。
**孪生缺失或三份波形哈希不一致 ⟹ 该注入案例整批作废**（§3.3 孪生表 + §5.5 P-12）。

### 5.5 合成端预检清单（写出前逐条 PASS，任一 FAIL 即拒绝该样本）

```
P-1 频带门禁（共振工况自指式检查）
    对每个在 truth 中声明的特征频率 f：要求 f ≤ fs/2.5 = reliable_band_hz（C2 硬约定 7）。
    等价地：R-03/R-04（KB0 §1 要求 reliable_band ≥ 2000 Hz）只能在 fs ≥ 2.5·2000 = 5000 Hz 上生成。
    ★ 保守下限取 fs < 4000 Hz ⇒ 一律拒绝生成任何 declared f ≥ 1000 Hz 的共振工况。
      理由：4 kHz 是"能声明 1 kHz 峰"的最低门槛（2.5·1000 = 2500 是规则门禁，
      而 4 kHz 还额外给抗混叠余量与 Welch 泄漏留出空间）。
      P-C3 就是这条的守门案例：违反时必须是【生成前拒绝】，绝不能"生成折返假峰再让规则去猜"。
    同理：若声明的模态频率远高于指令滤波截止与环带宽（激励能量进不去），
    必须把 declared_detectable 置 false 并写明理由——**不允许**"注入了但声称可检"。
    （P-A 的 8 Hz 指令低通就是这种情况：见 §1.4 红字。）
P-2 长度：n_samples ≥ 2000（C1 红线），且有效时长 ≥ 0.5 s。批次默认 n_samples ≥ 8000，
        使 Δf = fs/N ≤ 1 Hz 以便 (iii) 型配对分离可分辨（§1.2，**判据口径 = C2 规则 10 的
        pair_separation_bins ≥ 2**，不是本文私有阈值）。
P-3 时基：dt_jitter_ratio ≤ 0.2。合成默认 0（均匀栅格）；只有 INJ-17/22 明确注入抖动时才允许
        非零，且必须与 truth 的 magnitude 一致（不一致 = 注入器与记账不符，整批作废）。
        并要求存在"抖动 0.18"与"抖动 0.25"两档，用来测 C1 红线的边界行为。
P-4 缺失：nan_ratio ≤ 0.05（同上，另设 0.06 的"应被拒"档）；坏点必须写成 nan 而非 0 插值。
P-5 通道：cur_q / vel_fb / fe 三者不得全无（C1 红线）；至少含 1 个 move 或 settling 或 probing 段。
P-6 分段：segments 覆盖度必须 ≥ truth 中每条注入的 segments_kind 所需（C2 的
        segment_coverage 若显示该 kind 计数为 0，则该注入声明视为无效，样本作废）。
P-7 单位：counts_per_mm 非 null 时，mm 级数值全部可复算（§1.1 链条闭合，误差 <0.1%）；
        为 null 时确认 features 里无任何 *_mm 字段非 null，且 position_quantum_mm = null（A-13）。
        units_are 与 channels.*.unit 必须逐样本显式存在（A-4）；cur_q_rms_pct 在 rated_current_a
        缺失时确认为 null（A-14 / §7 #9）。
P-8 轨迹：§4.5 的 I1–I12 全通过（**解析/自洽校验**，通过后也只报"按构造成立"，A-31）。
P-9 稳定性：§1.5 极点/裕度/能量三项全通过（能量残差 <0.5%）。同样是自洽校验，不是实测。
P-10 门禁自指：对 P-A（fs=1000）类样本，truth 必须声明
        expected_features.freq_limits.blocked_rules ⊇ ["R-03","R-04"]，
        且 resonance.candidates 为空；若 features() 报出了 kHz 峰即为混叠，样本作废。
P-11 代码同源：features() 必须是由 C1 loader 读回后调用**同一个**内核得到（§5.7），
        并把 sha256 写入 self_check.features_sha256。
P-12 因果可用性 + 孪生完整性：每个软件族注入必须产出**三份**样本（母 / no_events / unsynced，
        §3.3 孪生表），三份的 waveform.tsv sha256 **必须相同**（同种子同注入时刻），
        差别只在 events.jsonl 与 meta.sync。缺任一孪生或哈希不一致 ⟹ 该案例整批作废，
        且其检出类结论不得标 simulation_validated（A-43）。
        ★ 本条的覆盖范围 = §3.3 孪生表的 **7×3**（全部 7 个软件 slug，含 INJ-19 / INJ-21，
        裁决 A-61：不接受任何豁免——C2 规则 8 的门禁是全 7 个，孪生生成依据就必须也是全 7 个）。
P-13 谱参数契约化（A-12）：凡 truth 声明了 resonance.candidates[] 的样本，必须同时声明
        resonance.estimation 五元组 {window,nperseg,noverlap,method,pair_separation_bins} 与
        resolution_hz；五元组与 fs_hz / nyquist 不自洽（C2 规则 12）即作废。
        pair_separation_bins < 2 的样本，其期望标签里**禁止**出现 mechanical_double_inertia，
        也**禁止**把"只见单峰"写成单惯量结论（§1.2 的三种诚实表述之一才可）。
P-14 构型与顺序声明（A-1 / A-68）：sensor_config ∈ {motor_side, load_side, mixed, unknown} 必须存在；
        motor_side 样本里若期望 antiresonance_freq_hz > freq_hz，除 INJ-29 的反例集（陷波人为谷）外一律作废；
        声明 mixed 的样本（P-B2 / INJ-30）必须逐通道带 sensor_side（峰 motor / 谷 load），缺任一 ⟹ 作废；
        mixed 与 unknown 同行为——顺序项不参与判定、置信度封顶（A-68），期望标签里**禁止**出现
        "顺序成立所以配对成立"或"顺序违反所以不是双惯量"两型判据（后者正是 §5.6 unknown_config
        投影要拦的错误，A-62）；§5.6 的 unknown_config 投影样本 sensor_config 即 unknown，不受
        motor_side 那条作废规则牵连（作废判定只对母样本构型生效）。
```

`selfcheck.json` 汇总每批 P-1…P-14 的 PASS/FAIL 计数与被拒原因分布；被拒样本**保留目录**
（改名 `rejected_*`）以便复盘，但不得进入 `manifest.jsonl`。

### 5.6 变体矩阵（每个物理工况至少 3 个投影）

```
full_meta         : 通道齐全、定标已知、事件齐全          → 测"能否归因对"
starved_channels  : 只留 pos_cmd+pos_fb（无 cur_q/vel_fb） → 测 C1 红线与 unavailable
starved_scale     : counts_per_mm = null                   → 测"是否伪造 µm 数值"
                                                          （position_quantum_mm 必须随之为 null）
no_events / unsynced : 见 P-12                              → 测因果纪律
mixed_config      : P-B2 / INJ-30 的构型声明投影：sensor_config = "mixed" + 逐通道
                   sensor_side（峰来源 motor、谷来源 load，A-68）→ 测"知道峰谷来自两套通道
                   时，是否仍拿 `f_anti < f_res` 顺序硬判双惯量"（期望：顺序项不评）
unknown_config    : A-62 新增，**只改元数据、不改数据**的投影：把已知构型（P-B 母样本的
                   motor_side、P-B2 / INJ-29 声明）重标为 "unknown"——waveform.tsv 与母样本
                   **逐字节相同（sha256 相等）**，只改 meta.sensor_config 与 audit
                   → 测"不知构型时硬用顺序判双惯量"这一具体错误（A-1）
```

★ 对**软件族**注入，"每个物理工况至少 3 个投影"具体化为 §3.3 孪生表的**三份一套**
（母 / `no_events` / `unsynced`，同一 `waveform.tsv` sha256），少于三份该案例不入 `manifest.jsonl`。
套数覆盖 = 7×3（A-61，含 INJ-19/21，无豁免）。

**`unknown_config` 投影变体的生成规则（裁决 A-62）**：

- **母样本集**：P-B 母样本（`motor_side`，1181/440 峰谷配对）、P-B2（`mixed`，峰谷来自两套通道）、
  INJ-29 母样本（`motor_side` + 陷波人为谷，唯一能合法产生"谷在峰之上"外观的数据）。
- **投影操作**：`meta.sensor_config` 改写为 `"unknown"`；P-B2 那份还必须把逐通道 `sensor_side`
  全部回收为缺省 `unspecified`（留着 motor/load 标注就构不成"不知道构型"，投影即无效）；
  `waveform.tsv`、通道数据、注入时刻、`truth.json` 的波形侧字段**一个字节都不改**——
  投影身份唯一由元数据承载。
- **`audit` 登记**（每项必填）：`projection = "unknown_config"`、`parent_sample_id`、
  `parent_sensor_config`（`motor_side` | `mixed`）、`waveform_sha256`（必须与母样本一致，
  写出侧按哈希核对而非重新生成）、`case_intent = "不知构型时硬用 f_anti < f_res 顺序判双惯量"`
  （A-1 点名的那个具体错误）。
- **期望的正确行为**：顺序项**不参与判定**，幅值/相位条件照常评（C1 派生 7 / C2 规则 9）；
  双惯性配对结论**置信度封顶**；**不得**由"顺序不可用"反推系统为单惯量（§1.2 三种诚实表述
  仍然全部适用）；可以给出双惯量候选，但必须带封顶与"构型未知"登记。
- **错误行为长什么样**（本投影存在的唯一理由就是抓它）：
  ① 接受型——在 unknown 构型下直接按 `f_anti < f_res` 成立而宣布"双惯量配对确认"且不封顶；
  ② 拒绝型（更危险）——把"谷在峰之上"（INJ-29 投影）当成"**不是**双惯量/是单惯量"的**证据**，
  把一条对自己不适用的物理约束反用成排除性结论。两型的 gold 答案相同：顺序项不评 + 封顶 +
  登记原因，区别只在数据侧配对是否真实存在。
- **与 `mixed_config` 投影的区分（A-68 vs A-62，同批必须两种都出）**：`mixed` = **知道**峰谷
  是两套通道拼的（带逐通道 `sensor_side`，考 agent 能否引用登记的原因说明顺序判据为何不适用）；
  `unknown` = **不知道**构型（来源被抹掉，考它会不会硬判）。行为相同、案例意图不同、记录原因不同。
  同一份 P-B2 波形要同时产 `mixed` 声明与 `unknown` 声明两份样本，差别纯在元数据。
- **配额口径**：`unknown_config` / `mixed_config` 是**额外**投影，不计入"每个物理工况至少 3 个投影"
  的下限；因本文件无"每 slug 配额计数表"，无需同步任何数字；`none_of_the_above` 的 15–20% 比例
  不受影响（其 gold 不是"无故障"）。预检联动见 §5.5 P-14（unknown 投影不因 motor_side 规则作废）。

C5 §2 要求 `none_of_the_above` 占 ≥15%：由 INJ-25（健康对照）+ `starved_*` +
`declared_detectable=false` 的注入共同构成，目标比例 15–20%，在 `manifest.jsonl` 里可统计核验。

### 5.7 硬要求：合成器与真实分析内核**共用同一个 `features()` / 规则代码路径**

C4 明文要求"仿真必须与真实数据走同一套 `features()` 与 `rules()` 代码路径"。落地为四条：

1. **单一实现**：数值内核只有一个入口（最终为 `python -m axiscope <sample_dir>`，KB0 §5）。
   合成数据先经 C1 loader 读入，再进同一 `features()`。**不存在**第二份"频谱算给合成看"的代码。
2. **禁止**以下形态（写出即评审不通过）：
   `synth_features.py` / `features_for_synth()` / `rules_lite` / 合成侧自带的指标模块 /
   把 `truth.json` 字段映射进 C2 的任何"快速通道"。
3. **等价性验收测试**：同一份 `waveform.tsv + meta.json` 分别经
   (i) 厂商 CSV → 解析器 → 样本包 与 (ii) 合成器 → 样本包 两条路进来，
   产出的 C2 JSON **必须逐字节一致**（`sha256` 比对）。因为 C2 只依赖样本包，
   这条等价性即"同源"的可执行证明。
4. **反馈闭环的正确方向**：合成样本被同一 agent 诊断后，`truth.json` 只用于**事后比对**，
   且比对结果只能进"流程正确性"章节（C5 §1）。若比对不一致，**修改的只能是被测管线或
   本文档的模型**，绝不允许"为了对上 truth 而改规则阈值"—— 那正是自验证循环的收口动作。

理由要说白：一旦合成侧有第二套实现，两套代码会各自"解释"同一物理量并按各自的解释打分，
差异会被两边的注释互相合理化，最终**互相欺骗**且没有任何外部约束能发现。
本文档唯一的独立约束（能量守恒 P-9、轨迹闭式恒等式 I5、频带自指 P-1/P-10）恰好都
**不经过规则层**，这是刻意设计的。

---

## 6. 模型自身的效度边界

### 6.1 本模型无法再现的现象

| 现象 | 为什么不能 | 连带后果 |
|---|---|---|
| > `fs/2.5` 的真实结构模态（kHz 以上机身/底座/夹具模态） | 我们只能"声明"注入哪些模态；没有现场模态 survey，无法知道真机有哪些 | 不得用 T3 支撑 R-03/R-04 在真机上的有效性；其外部合法性**已裁为结构性真空（A-65）**：T1-a（fs=1 kHz ⟹ `reliable_band_hz = 400 Hz`）在数据层面够不到 kHz 量级，T1-b 只承载机械↔电气二分类、给不了 kHz 类 slug 级合法性（A-63），剩下的只有 T2 文献层面"该判据成立、本数据集频段不足以检验"（`unavailable` + `blocked_rules`，C2 频段门禁/规则 7），**禁止**说成"未发现异常" |
| 热：绕组温升→参数漂移有真实时间常数与空间梯度 | 只有一阶脚本化漂移（INJ-06/14） | `thermal_fe_correlation_r` 在 T3 上是自证；只能用于测"temp 通道缺失时是否正确 unavailable"。`mechanical_thermal_drift` / `electrical_motor_heating`（含蠕变、冷热机差异类）**已裁为能力层结构性真空（A-64）**：本文件至多证明"T3 管线跑通"，能力层为真空——这两个 slug 只许进 `not_evaluable` 与拒答表，任何 `in-capability` 声明不得出现；要补的是**数据**（T2 通路需 ≥30 min 冷→热机 `temp`+`fe` 同采，手头无），属 KB8 长期缺口而非实现期能修的债 |
| 非线性间隙的温度/载荷相关性 | 死区只作常值参数 | 换向误差随温度/预紧的变化无法验证 |
| 总线拥塞的随机性与长尾相关 | INJ-16/17 是确定性/泊松到达的人为模型 | 不得声称"复现了 EtherCAT 抖动统计特性" |
| 绳索松弛-张紧切换、卡普顿摩擦非线性 | 本质非 LTI，两惯量拟合必然残差大 | 这是**特性**不是缺陷（P-C1 靠它测门），但不得用于任何"模型有效"的叙述 |
| 绳索/绳轮粘滑的完整谱（多模态耦合、绳截面接触） | 单柔性模式而已 | 不得声称能诊断绳索执行器 |
| ADC 共模/接地环路/采样保持伪影、电流采样混叠 | 噪声模型只是加性带限噪声 | `electrical_*` 里"接线/屏蔽/采样混叠"类判据不可由 T3 验证 |
| 视觉算法本身的 NG/偏移语义 | 只注入时间戳延迟与数值跳变 | 视觉"结果错误"与"结果迟到"不可混为一谈，后者才是本模型支持的 |

### 6.2 不能用来证明什么（逐条否定式清单）

* 不能证明任何**准确率/命中率/召回/F1**（C5 §1 硬规则）。
* 不能证明"kHz 共振判据在真实设备上可用"——`fs`、`reliable_band`、`notch` 都由我们自己设定。
  同一结论对 **T1-a 侧**也成立且与自设无关：DaRUS fs = 1 kHz ⟹ `reliable_band_hz = 400 Hz`，
  kHz 量级判据在数据层面**不可达**（裁决 A-65），报告只能说"该判据在 T2 文献上成立、本数据集
  频段不足以检验"（`unavailable` + `blocked_rules`），不得说"未发现异常"——频段门禁（C2 规则 7）
  正是为此存在。
* 不能支撑 `mechanical_thermal_drift` / `electrical_motor_heating`（及蠕变、冷热机差异类）的
  **能力层**声明：T3 被本节禁用、T1-a 只给热相关漂移而无归因真值、T2 通路缺 ≥30 min 冷→热机
  `temp`+`fe` 同采数据，三条通路全堵 ⟹ 结构性真空（裁决 A-64）。与 T3 相关的任何热类结果
  最多是"管线跑通"，不得表述为"判据已被验证"。
* 不能证明摩擦参数的绝对量级（只有 T2 区间锚点）。
* 不能证明 `software_induced_*` 判据在真机上可检——只能证明"给了事件流，管线会走到那条支路"。
* 不能证明建议在现场有效（见 §6.3）。
* 不能把 P-A 的结果外推到 P-B，反之亦然（两套设备的传动链、频带、刻度量子完全不同）。
* 不能把 DaRUS 的任何参数当成被测设备的实测参数（它是**公开数据集的**发布值，T2/T1-a）。
* **不能声称任何参数集（P-A / P-B / P-C）"已被真实数据验证"**：P-A 对标 DaRUS 的**线缆驱动试验台**
  （`machine_type = testbed`，SI 原生单位），P-B 是虚构的半导体贴片轴工况，
  两者都不是产线数据，本文也没有任何一条真实数据比对结果可引（A-31 的措辞上限：
  合成侧只能写"按构造检出""管线跑通"）。
* 不能声称软件的"停顿/丢拍"时序统计代表真实调度器或 EtherCAT 仲裁（§6.1；引用时必带 A-43 caveat）。

### 6.3 "仿真验证过的建议"在报告里到底意味着什么

`basis = "simulation_validated"`（C3 规则 4）的**唯一合法解读**：

> 在由**本条波形反拟合**出来的模型 `P̂` 上，用同一份指令重放 `{基线}` 与 `{基线+建议}`，
> 在 ±20% 参数扰动下改进量的**最坏值**为 X%；`P̂` 复现观测波形的残差为 Y%；
> 建议未激发超过基线主峰 50% 的新峰；相位/增益裕度分别为 A°/B dB。
> **这是模型内推值，不是测量值。**

必须同时出现在报告里的三句话（缺一不可）：

1. `caveats`：至少含"仿真模型由本波形反拟合，改进量是模型内推值，非实测"与"未建模热效应/磨损/结构模态"
   （C3 `validation[].caveats` 已有此形状，逐字沿用）。**引用本文仿真做检出类结论时，
   必须再加一句 `"仿真不含真实调度器与总线仲裁"`**（裁决 A-43 的强制 caveat，
   针对 §3.3 的 host 停顿 / 插补欠载 / 丢周期一族）。
2. `plant_fit.fit_residual_pct` 与 `sensitivity` 的最坏值（`sensitivity` 缺失 = 记录不合法）。
3. `expected_effect.basis` 为 `rule_heuristic` 时，报告**不得**给出任何改进百分比数字
   （C3 规则 4 的禁令 + C4 的降级分支）。

**禁止措辞**（出现即视为 C5 §3 的"无依据成功声明"违规）：
"已验证有效"、"仿真确认问题在机械侧"、"该参数调整后现场应可改善"、
"通过仿真验证，置信度提升至 X"、把 `expected_effect` 与 T1 案例的数字混排。

**允许措辞**示例：
"在拟合残差 8.4% 的双惯量模型上，`fe_rms` 由 405→152 counts（−62%），
±20% 惯量比/共振频率/阻尼扫描下最坏改进 −38%；未激发 >50% 主峰的新模态。
此数字为模型内推值，现场有效性需按 `field_procedure` 逐条验证。"

### 6.4 与 C5 评测协议挂钩的模型设计（把纪律写进模型，而不只是写进文档）

| 自验证循环的四条边 | 本文件里的切断装置 |
|---|---|
| 自己造合成数据 | 参数种子全部来自公开发布值（§2.0）；`provenance` 逐参数标注；`assumed` 项在报告强制露出；能量守恒 + 闭式恒等式（P-9/I5）是**不经规则层**的独立正确性检查 |
| 用自己的规则诊断 | `features()`/`rules()` 不允许读 `truth.json`（§0 反向要求 + §5.7 第 3 条等价性测试）；真实包里出现 `truth.json` 由 loader 报错 |
| 用自己的仿真验证 | 验证门控的三条降级/否决分支（残差 >25%、新峰 >50%、敏感性最坏 <10% ⇒ `fragile`）是**必测项**，由 P-C1/C2/C3 专门做"门控是否真会拦"的守门案例；门控拦不住 = 本文件验收失败 |
| 自己打分 | `claims_forbidden` 字段 + `source_tier=T3` 让 CI 能机器式拒绝把 T3 计入能力指标；`none_of_the_above` 比例 15–20% 可统计核验（§5.6） |

**残余风险（诚实声明，无法用本文件消除）**：规则库（KB3/C3）与被控对象（本文）由同一批人的
同一套物理直觉写出，因此"注入 → 检出一致"最多证明**管线连着、回归不退化**，
永远不能证明**有效**。真正的外部约束只有三条：T1-a（DaRUS 真实测量）、
T1-b（CWRU/帕德博恩/MFPT 故障真值）、以及 C5 §5 的人工基线。
其中本文件对 T1-a 的贡献是**两条可被真实数据推翻的解析预言**：
§4.4 预言 2（`kff = 1.5` ⇒ `corr_fe_vs_accel` 应为负）与
预言 3（`kff > 1` ⇒ `ff_mismatch.asymmetry_ratio < 1`，即减速段偏差更大）。
预言 3 比预言 2 更稳（不依赖方差占比，只依赖符号），建议作为 T1-a 上的首选核对项。
这是本项目里少数几处"T3/解析 与 T1 真正对话"的地方，值得作为技术叙事的主轴。

---

## 7. 待决与跨文档修订清单

主线程裁决（KB0 §7 的 A-1…A-33、§7.1 第二轮 A-34…A-46、§7.2 第三轮 A-47…A-53 与
§7.3 第四轮至第六轮 A-54…A-91）回写后的收口账。本文件受第六轮影响的是 **A-82**
（三条件表③与 INJ-17 孪生行的残差方向）；本文件不引用任何标准文本，A-85 在此无落点。
**A-87/A-88/A-89 不改本文任何注入参数**：本文一切合成形态都是 `T3`，按 A-88 只能证明管线自洽，
永远不给 KB2/KB3 的判据背书。唯一受影响的是**登记方式**——#9 那类"等厂商手册"的格现在要按
KB0 §4 的 `external_reference` 标档：电机 `Kt`/`rated_current_a` 属 **③a 文档可查**（数据手册里就有，
拿到并存档 ⟹ `official-artifact` 可闭合，**不必**等 FAE），而"这台驱动器/编码器实际怎么接"才属 ③b。
**逐行保留**（不删条目），第 4 列给"已裁 / 状态"；`open` 只允许是**实现期任务**，
本期（只写规范、不写产品代码）不得把任何实现期事项声称已完成。

| # | 事项 | 需要谁改 | 已裁（状态） |
|---|---|---|---|
| 1 | C4 末行路径 `KB5-servo-simulation.md` 与实际 `KB5-simulation-plant.md` 不一致 | C4 | **已裁：A-22（已闭环）**——文件名统一为 `KB4-attribution-model.md` / `KB5-simulation-plant.md`，C4 现文（L45）已写正确路径；本文首节"命名说明"同步收口 |
| 2 | C2/C3 示例的 `antiresonance_freq_hz = 1420 > freq_hz = 1181` 与两惯量物理矛盾：需按 §1.2 顺序判据加"非共置或 ≥3 惯量"的构型标注，并在 R-04 判据里写入 `f_a < f_m` | C2、C3、KB3 | **已裁：A-1（契约侧已改）**——C1 派生规则 7 + C2 规则 9 已按 `f_anti < f_res` 与 `f_res/f_anti = √(1+λ)` 收口，示例改为 `440 / 1181`（λ≈6.2）；新增 `meta.sensor_config`，`unknown` 时顺序项不判且置信度封顶。本文 §1.2 顺序判据的措辞已是"已由 A-1 采纳"，§5.5 新增 P-14 钉住构型声明 |
| 3 | `CableActuatorTestbed.xml` 把 `torque_max="32"` 写在 `<motor>` 元素上，而 `32 ≈ 6.4 × 5`（齿轮比）像是**齿轮输出侧**量；`inertia="0.000"`/`mass="0.0"` 未发布惯量 | KB7 补注；使用方须标 `assumed` | **已裁：A-27**——KB7 侧补注由主线程回写；**本文件所有引用 `torque_max` / 额定转矩处已一律标 `assumed`**（§2.0 种子表行、§2.0 推论、§1.1 硬约束 3） |
| 4 | DaRUS `wegaufz/wegaufn` 复算出的 `counts_per_mm = 5.8349`（量子 ≈ 0.171 mm）与 C1 示例的 `50000 counts/mm` 相差 4 个量级；同一套判据在两批数据上"µm 级"含义完全不同 → C5 案例元数据需增加 `position_quantum_mm` 字段 | C1、C5 | **已裁：A-13（已闭环）**——`position_quantum_mm = 1/counts_per_mm` 已进 C2 规则 11 与例 A（2e-5 mm）/ 例 B（0.1714 mm），C5 案例元数据同步。**这个 4 个量级的对照是刻意保留的核心叙事事实**，本文 §1.1 推论 1 与 §2.1 / §2.2 两张 meta 表都显式印出 `0.1714 mm` vs `0.00002 mm` |
| 5 | "真实包内禁止 `truth.json`"需要升格为 C1 的 loader 派生规则（曾经是 §5.4 的建议） | C1 | **已裁：升格为 C1 的 loader 规则（已闭环）**——C1 目录结构节现文："真实样本包内出现 `truth.json` 即为污染：加载器必须拒收并报错"；本文 §0 纪律 3 与 §5.4 语义纪律已从"建议"改为引用该规则 |
| 6 | 摩擦参数与陷波参数的 T2 区间需在 KB3 的阈值表里逐条登记出处（本文只给锚点战役名） | KB3 | **移交 KB3**（由另一会话回写，本文件不动）；本文侧的对应义务已写清：§1.3 的 `param_source` / `provenance` 标注 + §2.0 的"不得写进 `meta.drive` 冒充被测参数" |
| 7 | `resonance.candidates[].amplitude_ratio_vs_broadband` 与 `quality_factor_estimate` 的估计方法（Welch 窗长/重叠/分辨率）**登记时尚未**契约化；本文原先只给"配对分离 ≥ 2 bins"的私有可分辨条件 | C2 | **已裁：A-12（已闭环）**——`resonance.estimation.{window,nperseg,noverlap,method,pair_separation_bins}` 已进 C2 规则 10（缺参数则规则引擎拒绝引用谱结论）。本文已把私有阈值改述为**引用 C2 规则 10**（§1.2 条件 (iii) + 新增"谱估计参数必须与候选一起产出"三条纪律 + §5.5 P-13），并明确 `pair_separation_bins < 2` 判不可分辨、**禁止**反推单惯量 |
| 8 | S 曲线黄金向量（§4.5）需在实现期作为回归基准纳入 `bench/`，并与 AUDIT 记录的 4 组工况对齐（端点误差 <1e-6 mm 量级） | C5、bench | **保持 open（实现期任务）**——本期不写产品代码，黄金向量尚未生成、尚未纳入 `bench/`；**不得**声称任何"已跑通/已对齐/已验证"。AUDIT 的 4 组数值按 A-32 只作二手参照量级（§4.2 已降级措辞） |
| 9 | 直线电机场景的 `torque常数/Kt` 与 `rated_current_a` 标定链在本文件是假设值；若无厂商手册，`cur_q ↔ %` 的换算必须保持 `null` 而非估算 | 参数集 P-B | **已裁（本文件裁定）：必须为 `null`，不得估算**——依据是 C1 `cur_q.unit` + C2 规则 3 + A-14（`_a` / `_pct` 双字段，`_pct` 需 `rated_current_a` 才非 null）。落地位置：§1.1 硬约束 3、§2.0 推论、§2.2 力矩核对、§5.5 P-7。`rated_current_a = 4.6` 与 `Kt = 1.5` 都标 `assumed` |
| 10 | `ff_mismatch.asymmetry_ratio` 是**带方向**的量（`>1` ⇔ `kff<1`，`<1` ⇔ `kff>1`，§4.4 预言 3）。KB3 里任何"asymmetry > 阈值 ⇒ 前馈不足"的单向判据必须在 `kff>1` 分支上镜像，否则系统性漏判 | KB3 | **已裁：A-26（KB3 侧回写中）**——`kff>1` 分支必须镜像；本文 §4.4 预言 3 是该裁决的出处，本文侧无需再改 |
| 11 | 需要新增 C2 特征或 C5 案例字段：`position_quantum_mm`（= `1/counts_per_mm`，缺定标时为 null），用来直接拦住"µm 级声明" | C2、C5 | **已裁：A-13（已闭环，同 #4）**——C2 规则 11 + 例 A / 例 B 已含该字段，C5 案例元数据同步；本文 `truth.json` 的 `c5_case.position_quantum_mm` 已写入（§5.4），并要求它由 loader 从 `counts_per_mm` 派生、**不在 `meta.json` 里另设载体**（§5.3 纪律 9） |
| 12 | **新增（本轮发现）**：`meta.sensor_config` 只有 `{motor_side, load_side, unknown}` 三值，表达不了 P-B2 / INJ-30 的**混合构型**（峰由电机侧估、谷由负载侧估）。本期本文的处置是写 `unknown` + `audit.assumptions`，代价是顺序项不参与判定、置信度封顶，反例集的区分度下降 | C1（增补取值或 per-channel `sensor_side`）；本文不自造字段 | **已裁：A-68（契约侧已改，本文临时处置作废）**——主线程已把 C1 `meta.sensor_config` 值域扩为 `{motor_side, load_side, mixed, unknown}`，并新增 `meta.channels.<pos>.sensor_side ∈ {motor, load, unspecified}`（缺省 `unspecified`，仅 `mixed` 时必须逐通道填写）；C1 派生规则 7 写明 `mixed` 与 `unknown` 行为相同（顺序项不评、置信度封顶），区别在记录的原因。本文同步回写：§1.2 载体段、§2.2 P-B2、§3.4 INJ-30、§5.3 纪律 7、§5.5 P-14 均改 `mixed` + 逐通道 `sensor_side`；P-B2/INJ-30 **不再写 `unknown` + `audit.assumptions`**。`mixed` 比 `unknown` 更诚实：记录了"峰谷来自两套通道、不是同一传递函数的零极点交替"这一已知事实，而非统一成"不知道"；案例意图与 `unknown` 的区分见 §5.6 投影对（A-62） |
| 13 | **新增（本轮发现）**：INJ-19 原文用到的 `unit_scale_mismatch` 与 `travel_limit` **未在任何契约登记**（`unit_scale_mismatch` 还残在 KB8 的表里）。本文已把它们降级为 `truth.json` 侧记账字段与叙述，证据路径改用已登记的 `*_mm` / `*_counts` 比值跳变 + `position_quantum_mm`（§3.3 INJ-19） | C2（若要成为特征）/ C1（若要声明行程上限 `travel_limit`）/ KB8（同步降级） | **已裁：A-69（分开裁）**——(a) `unit_scale_mismatch` **不升为 C2 特征**：它的可观测形式就是已登记的 `*_mm`/`*_counts` 比值跳变，它只作 `truth.json` 侧记账标签与叙述用词，永远不得当证据路径引用（KB8 侧同步降级由该会话回写，本文不动他人文件）；(b) `travel_limit` **已进 C1**：`meta.axis.travel_limit_neg_mm` / `travel_limit_pos_mm`（可选、缺省 `null`，权威载体在 `axis` 不在 `machine`），C1 派生规则 8：为 `null` 时依赖行程边界的判据必须 `unavailable` + 登记 `blocked_rules`，**禁止**从"波形里位置曾停住"反推限位值再当已知参数用。本文 §3.3 INJ-19 行与 §5.3 示例 `axis` 块已按此重写 |
| 14 | **新增（本轮发现）**：C2 规则 3 允许转矩归一化的前提是 `meta.drive.rated_torque`，但 C1 的 `drive` 块（示例与必填/选填节）**没有列 `rated_torque`**；A-27 又把 `torque_max` 判成 `assumed`。结果：P-A/P-B 的 `torque.unit = "percent_of_rated"` 分支在契约面上没有合法的分母来源，`*_pct` 只能恒 `null` | C1（`drive.rated_torque` + 单位口径）/ C2（规则 3 分母来源） | **已裁：A-70（契约侧已改）**——C1 `drive` 增 `rated_torque_N_m`（可空）+ `rated_torque_source ∈ {measured, manual, nameplate, assumed}`；C2 规则 3 已改写：`measured`/`manual` 正常、`nameplate` 可用带限定语、`assumed`（DaRUS `torque_max=32` 即此档，A-27）⟹ 百分比类判据**封顶 T2** 且强制 caveat"额定转矩为假定值，百分比类判据的绝对刻度不可信"、字段 `null` ⟹ `*_pct` 恒 `null`。`cur_q_saturation_ratio` 一类比值判据自此有可追溯分母。本文落地：§5.3 纪律 12 逐参数集档位表（P-A→32.0/assumed；P-B/P-B2→6.9/assumed；INJ-28/starved→null/null），§2.1/§2.2 meta 表同步，§1.1 硬约束 3 / §1.4 转矩标定行 / §2.0 已指向该口径 |

> 收口状态小结：#1 #2 #4 #5 #7 #9 #11 #10 已闭环（其中 #6 #10 的落地在 KB3 侧，本文件只登记出处）；
> **#8 是唯一保持 open 的实现期事项**（黄金向量 / `bench/`，本期不写代码）；
> #12 #13 #14 已由第四轮裁决 **A-68 / A-69 / A-70**（KB0 §7.3）落裁，主线程已回写 C1/C2，
> 本文对应临时处置已全部同步改写（混合构型改 `mixed` + 逐通道 `sensor_side`、行程限位载体为
> `meta.axis.travel_limit_*_mm`、额定转矩分母四档见 §5.3 纪律 12）——本文件始终不自造他人契约里的字段名。
> 另：§5.6 本轮按 A-62 增补 `unknown_config` 投影变体（只改元数据、不改数据，与 `mixed_config`
> 投影同批生成），§3.3 孪生表按 A-61 定版 7×3（INJ-19/21 无豁免），§6.1/§6.2 按 A-64/A-65
> 把热/蠕变类与 kHz 类明确为**结构性真空**口径。
> 另：本文已按 A-9 / A-45 使用 C2 落地字段（`bus_cycle_hold_max_ms`、
> `fe_spike_aligned_to_{host_pause,underrun,network_miss,vision_result,recipe_change}`、
> `alignment_residual_ms`、`step_labels`），并按 A-31 把合成侧的措辞上限统一到
> "按构造检出 / 管线跑通 / 解析自洽校验"。
