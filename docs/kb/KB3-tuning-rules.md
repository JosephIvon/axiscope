# KB3 — 特征索引表 + 诊断规则库 R-01…R-30 + 阈值合法化

本文件是 C2 特征向量的**唯一登记处**（C2 硬性规则 4），也是 C3 规则引擎的**唯一判据来源**。
规则引擎不允许自带 FFT、不允许自带未经本文件登记的字面量阈值。

编号语义遵守 KB0 §1：`R-03` / `R-04` 的标题、family、频带下界已锁定；此外
`C3-diagnosis.md` 的示例已经占用了三条语义——`R-05` 必须依赖 `crawling.low_speed_segments`
（见其 `audit.rules_skipped`）、`R-07` 必须用于排除 `encoder_eccentricity`
（见其 `ruled_out_alternatives`）、`R-11` 必须在"仅 `pos_cmd/pos_fb/fe/cur_q`、`cur_q` 有 1182 Hz 主峰
加 2/3 次谐波、无 `temp`"的案例中可触发（见其 `audit.rules_fired`）。
本文件遵守这三条，新增条目只追加（KB0 §1）。

---

## 0. 全局纪律（对本文件所有规则生效，优先级高于任何单条判据）

1. **null ≠ 0**。规则前件依赖的特征若为 `null`，该规则**放弃**，记入
   `audit.rules_skipped[{rule_id, reason:"dependency_null:<path>"}]`；不得插值、不得均值填充、
   不得把 null 当作 0 参与比较（C2 硬性规则 2）。
   特别注意三处"null 与 false 语义不同"的字段：
   `resonance.candidates[].present_in_rest`（缺 `rest` 段时为 null，**不可**当作"静止时无峰"）、
   `spectral.*.harmonic_ratios`、`tracking.path_segments[].*`。
2. **频带门禁**。任何在频率轴上声明频点的判据，其声明频点必须落在
   `freq_limits.reliable_band_hz`（= `nyquist/1.25`，C2 规则 7）之内。越带 ⟹ 该判据进
   `unavailable` 并列入 `freq_limits.blocked_rules`，同时进 C3 `differential.not_evaluable`。
   **绝对禁止把"看不见"写成"没有"**。在 fs = 1 kHz（奈奎斯特 500 Hz、可靠带 400 Hz）的
   DaRUS 真实数据上（KB7 §已实测能力边界 1：两份数据 `SampleTime` 恒为 1 ms），
   `R-03`/`R-04` 与 `R-11` 的开关频率分支**只能进 `blocked_rules`**（写法 `R-11#switching_freq`，
   A-79 定支路粒度），不得输出"未检出机械谐振""无转矩纹波"。在该数据上报告"1.18 kHz 机械谐振"是物理不可能的（C2 规则 7 实测教训）。
   ★ **`R-10` 不在此列**（A-79，修正本纪律早期版本把 `R-10` 一并列入的错误）：R-10 是采样/混叠假峰的
   **检测器**，`fs = 1 kHz` 的数据恰恰最需要它运行——把它标成 blocked 等于在唯一需要它的场景里关掉它。
   同理 **`R-25` 不得进 `blocked_rules`**：它就是门禁本身，无声明频点，正确落点是 C3 `audit.rules_fired`。
   ★ **已裁 A-96（多栅格细化）**：一条记录挂多条时间栅格时，`reliable_band_hz` **按被比较通道各自所在的
   `time_base_ref` 逐条判定**，不能拿主栅格的 `f_b` 覆盖全部通道。参与同一判据的通道若不在同一栅格，
   或其跨栅格重采样在 C1 `meta.resample[].band_effect` 记为 `band_lost` / `aliased_risk` ⟹
   该判据进 `unavailable`，reason 写明栅格与 band_effect。**禁止**在降采样序列上给相干/相位结论
   （C1「多速率栅格」规则 6）。`role = "event"` 的离散事件栅格**不参与**本门禁的 `fs` 取值。
3. **`drive.*` 缺失即降级**。C1 明文：`drive.*` 任一字段缺失时，依赖它的判据必须降级为
   `unverified`，不允许用默认值冒充实测值。本文件凡引用 `meta.drive.velocity_loop_gain_hz`、
   `meta.drive.inertia_ratio`、`meta.drive.notch_filters`、`meta.drive.rigidity_level` 的规则，
   都在"必要上下文"里写明缺失时的降级路径。
4. **单位纪律**。内部基准恒为编码器 counts（KB0 §5、C1 单位规则）。`meta.counts_per_mm == null` 时：
   (a) 所有 `*_mm` 特征为 null；(b) 报告只印 `[counts]`；
   (c) 规则的建议动作**禁止**给出 µm/µrad 数字，只能给 counts 或 counts/rev 量级；
   (d) 以物理单位表述的工艺容差（如 mm/min 进给）一律改写为 counts/s 等价形式（KB7：`F30000/F120000/F300000`
   = 0.5/2/5 m/s 的换算只用于数据分类，不用于报告结论）。
   **(A-97 更正)** 本条 (b)(c)(d) 三支写于 A-4/A-97 之前，它们在 `units_are = si_native` 的样本上指向一个
   **根本不存在的 counts 刻度**，原句不删、按 A-97 ①/③ 收窄如下：`*_counts` 是**后缀历史名**，其值 = 该通道
   **原生刻度**下的数值，真实单位由 `meta.units_are` 唯一决定；(b) 的正确口径是"印原生刻度 + 单位随行"，
   **禁止裸印 `*_counts` 数值**（`sensor_disagreement.pairs[].unit` 必填）；(c) 建议动作在 si_native 样本上给
   原生刻度数字并随行单位，仍**禁止**臆造 `*_mm` 折算链；(d) 改写为 counts/s 等价形式**仅当
   `counts_per_mm != null`**，无刻度时保留 SI 原表述。**三条都不得被用来给绝对阈值"补一个刻度"**——
   以 counts 字面常数为阈值的判据在无刻度时一律走 §1.13b 的标注约定
   （`blocked_by = absent_counts_scale`）。
   该悬案**已裁 A-110 ②/③**（尺子：这一改要不要新造数字），裁文当时登记的生效条件是
   「**#39 落地前 (b)(c)(d) 照旧全文有效**」——**该条件已于 2026-10-21 满足（#39 落码 = A-113），生效注如下**：
   ① **(a) 的适用范围收窄**：「`counts_per_mm == null` ⟹ 所有 `*_mm` 特征为 null」此后**只对
   `units_are = counts` 的无刻度样本成立**；`units_are = si_native` 且通道在 C1 单位词表里登记为长度时，
   `*_mm` 由随行单位**直接定标**（`×1000`，纯换算、不造数），并强制一行锚 `meta.units_are` 的假设。
   ② **(c) 的禁令范围收窄为「禁止给出 µm/µrad 级容差·目标数字」**，不是禁止一切 µm 数字：
   实测幅值可给（须随行单位），容差/目标仍须来自外部工艺容差表，缺失即 `not_evaluable`，
   **不得由实测幅值反推容差**。③**阈值侧一条不动**：`20 counts`/`50 counts/s`/`2.0 counts/min`
   仍以 `blocked_by = absent_counts_scale` 缺席，不折算成 m 级常数（A-110 ② 的裁决原样维持）。
   ④ (b)(d) 的 A-97 更正口径不变。落点均在 C2 契约层（字段定义式属契约层，本文件只裁方向）：
   C2 规则 3 已增 si_native 支、`features.py::si_native_length_scale` 按随行单位换算。
   本条**首句**"内部基准恒为编码器 counts"同属历史口径（KB0 §5 的那句基线由 A-97 覆盖）：它成立与否
   取决于样本是否真有 counts 刻度，`units_are = si_native` 时**内部基准就是该通道原生 SI 刻度**，
   counts 只是另一种采样设备（`counts_per_mm != null`）下的特例。
5. **因果门禁（软件族唯一开关）**。`event_context.causal_claims_permitted == false` 时，
   `software_induced_*` 规则**不得**产出归因，只能以"时间共现"形式呈现，且报告必须写明
   "时钟未对齐，共现不等于因果"（C2 规则 8、C6 §3 硬规则 1）。
   `event_context.available == false`（无 `events.jsonl`）时，整族必须逐条登记进
   C3 `differential.not_evaluable`：**族级**用 `{"family":"software_induced_error",
   "why":"无事件上下文，无法区分机械尖峰与调度抖动"}`，**逐模式**用 `{"fault_mode":"<KB0 §2 slug>", "why":…}`
   （**A-51 已裁**：`software_induced_error` 是族级标签，只能出现在 `family` 键上，禁入 `fault_mode`，见 KB0 §6），
   **不得沉默**（C6 §4）。
6. **对齐残差与差值的方向要分开**（A-82，更正 A-50）。两个不等号作用在两个不同的量上：
   - 任何 `fe_spike_aligned_to_*` 类判据的**匹配窗口**必须严格大于 `event_context.sync.uncertainty_ms`
     （窗比钟差还小就是在抽签），且被声称的**时延/差值**（`vision_result_latency_p95_ms`、
     `bus_cycle_hold_max_ms`、两次到位时刻之差）必须大于 `τ_u`，否则该差值在时基上分辨不出来。
   - **对齐残差** `event_context.alignment_residual_ms`（匹配对 `abs(Δt)` 的中位数）必须
     **不大于** `sync.uncertainty_ms` 才允许因果声明（C6 §3 硬规则 2、C2 规则 8、KB4 CAP-8 同向）。
     旧文与 A-50 曾把它写成"残差必须**大于**不确定度才算对齐"，方向是反的：那条判据会
     禁止最紧的巧合、放行最松的对齐。A-50 关于"`alignment_residual_ms` 就是匹配对 `abs(Δt)` 的中位数"
     的**语义**裁定保留，**方向**作废。
   `uncertainty_ms` 缺失时按 5 ms 保守取值并记入 `audit.assumptions`（C6 §3 规则 3）。
7. **出处纪律**。每条规则至少一个非 T3 出处（KB0 §4：`T1-a`/`T1-b`/`T2`）。
   只有 T3（本项目合成，KB5）支撑的规则不得进入 C3 报告。
   `expected_effect.basis` 只允许三个值（C3 不可协商规则 4）：`simulation_validated`
   （须有 C4 `validation[]` 的 V* 记录且 `fit_residual_pct ≤ 25%`，C4 补充约束）、
   `rule_heuristic`（只给方向，不给数字）、`unverified`。
   本项目 `safety.writes_to_device` 恒为 false（C3 规则 6），因此本文件所有"参数级动作"一律表示为
   **写入建议 + 离线仿真验证 + 人工审批**，`requires_offline` 按 C4 门控流程决定。
8. **触发门控（T1-a 真实数据专属前置）**。KB7 §已实测 2：DaRUS `Export 10.csv` 18650 行中
   `bTrigger_Record` 仅 26.8% 为真、`bTrigger_Export` 仅 2.7%。任何在 T1-a 上运行的规则，其样本集
   必须是过滤后的触发段（复刻作者 `catcsv2cell.m` 的 `trig_record ~= 0`）。未过滤会把 4 倍于有效的
   数据算进 RMS 与频谱，本文件全部阈值随之失效（并且会造出假谱峰，见 R-10）。
9. **方向符号（T1-a 专属前置）**。KB7 §已实测 3：编码器速度必须乘 `bMovingForward` 方向符号才是带符号速度。
   若上游未修正，`vel_fb` 恒正，则 `R-05`/`R-06`/`R-08`/`R-15`/`R-24` 中"反向""减速"语义全部不成立——
   这些规则必须检查 `meta.channels.vel_fb.sign`/`derived` 并在未修正时**放弃**，而不是给出看起来合理的结论。
10. **派生通道置信惩罚**。C1 派生规则 4：`vel_fb` 由 `pos_fb` 差分派生时，频谱类判据置信度 ×0.7。
    因此 `R-10`/`R-11`/`R-13`/`R-17`/`R-20` 在 `channels.vel_fb.derived == true` 时
    置信度上限自动降至 0.7×原值，且**不得放宽门限**。
11. **每条 hypothesis ≥2 条 supporting_evidence**（C3 不可协商规则 1）。故本文件每条主判据规则
    都给出 ≥2 个可独立成证据的特征路径；单特征规则（如 R-20）必须与 R-28 联合使用才能进入 `hypotheses`，
    否则只能进 `differential.considered`。
12. **反证义务**。每个 top-3 假设必须跑一遍反证判据（C3 不可协商规则 2）。本文件每条规则的
    "排除项"就是反证判据的登记处。
13. **百分比类判据的分母纪律（A-70）**。凡判据里出现 `*_pct`、`cur_q_saturation_ratio`
    或任何"饱和/余量比"阈值（R-06/R-11/R-12/R-16/R-17 及 §1.1 对应行），其转矩侧分母必须来自
    C1 `meta.drive.rated_torque_N_m` **且** `meta.drive.rated_torque_source ∈ {measured, manual, nameplate, assumed}`：
    - `rated_torque_source == "assumed"` ⟹ 该判据的出处层级**封顶 T2**（不得写 T1-x），
      且报告 caveats **必须**原文写出"额定转矩为假定值，百分比类判据的绝对刻度不可信"；
      四档合法性递减 `measured > manual > nameplate > assumed`。
    - `rated_torque_N_m == null` ⟹ 相关 `*_pct` 恒 `null`（纪律 1 生效：判据放弃），
      **只有 `N_m` 绝对值支路可用**。
    本条同时约束 C2 规则 3 的电流侧归一（`meta.rated_current_a`），两套分母不得混写。（已裁 A-70）
14. **能力声明真空纪律（A-64/A-65）**。`mechanical_thermal_drift`、`electrical_motor_heating`
    与 **kHz 量级共振 / 电流环带宽**类判据（R-01/R-03/R-04/R-09 的高频支、R-11、R-12）**在 T1-a 上没有正例来源**：
    T1-a `fs = 1 kHz` ⟹ 奈奎斯特 500 Hz ⟹ `reliable_band_hz = 400 Hz`，kHz 判据在数据层面不可达；
    热漂移/电机发热类还缺 `temp` 通道配对样本。因此这类判据**只有 T2 文献正当性**，报告侧只能
    `unavailable` + 把规则号登记进 `blocked_rules`，**禁止**输出"未发现谐振 / 未发现异常 / 无热漂移"。
    任何以 T3 合成（KB5）当"能力证据"的表述一律降级为**"管线跑通（合成自洽）"**级主张（A-64）。
15. **真值来源三分法（A-87）**。一条判据能立住，依据只有三类，必须在 `basis`/`出处` 里对号入座：
    ① **波形可算**——C2/C7 已登记路径可复算（⟹ 才允许 `simulation_validated`，仍须 C4 的 V* 记录）；
    ② **逻辑自洽**——不依赖任何手册版本的结构必然性（如 A-33 的"`_unit` 已是 mm 再除脉冲当量必然差 1000 倍"），
    可断言**形态**会发生，但措辞仍是"第三方实现审计中出现的缺陷形态"；
    ③ **约定与接线**——这类真值**不在数据里，也不在仿真里**，在厂商手册与现场接线表里。**A-89 把它拆成两档**
    （两档都恒 `rule_heuristic`：文档定的是接口定义，定不死改进量，所以**不得因"手册查到了"给 `basis` 升档**）：
    **③a 文档可查**——方向位号（0 是正还是负）、停止方式编码、错误码与停止原因表、回零 mode 语义、
    某个 SDK 函数**是否存在**、其 DLL 归属与参数个数。这些**手册或官方绑定里有答案**，我们只是没查；
    一经 `external_reference = official-artifact`（工件存证在库 + `clause` + `verified_by = self`）即**闭合**。
    **③b 批次与现场**——IO 位号↔物理端子、伺服使能走哪个输出位、CMP 通道↔端子、轴编码器是否与伺服编码器并接、
    从站 PDO/ESI 映射、SDK↔固件版本矩阵、目标进程位数。手册正文答不了（随接线盒型号/批次/现场接线而变），
    只能 `vendor_reply`（FAE 书面答复 + 日期 + 适用型号）或现场核对，且**必须写明"手册为什么答不了"**（KB0 §6 检查 21）。
    第 ③ 类**禁止标 `simulation_validated`**：模型按约定 A 造、自检再查"是不是 A"
    是同义反复，跑一百遍绿也不增加一分证据。它只能写成"待外部确认项"（`audit.assumptions` +
    `recommendation.field_procedure` 的对应层级），由人在真机上按 L1→L6 逐级确认——**本 agent 不上机**
    （`safety.writes_to_device` 恒 false，纪律 7 尾）。
    **②与③的边界要咬死**："`_unit` 双重换算必然差 1000 倍"是逻辑问题，可以进判据；
    "这台机器的 `dmc_vmove` 方向位写 0 还是 1"是文档问题，只能进待确认清单。混淆二者即为 A-87 违规。
    **就地更正（A-89 自我适用）**：本条原把 `dmc_vmove` 的 0/1 当作"只能等厂商回答"的标准例子——方向没错
    （它是文档问题），但**档归错了**：第三方会话按官方手册 8.9 查到该编码并有官方绑定可校验，说明它是 ③a。
    在我们自己拿到那本手册之前，它对本仓库仍是 `public-doc`（读手册的不是我们，`verified_by = third_party_report`
    不计入核对数，KB0 §6 检查 20），但**不得再登记为"必须问厂商"**——正确处置是"手册 8.9 可查，待逐字核对并存证"。
16. **同源核对物无证明力（A-88）**。由本文件/契约/代码派生出来的核对物——待核对清单、自检用例、
    契约测试的期望值、快照、评审意见——对**它自己那个来源**的证明力记 **0**：签名若凭记忆写错，
    会被原样抄进清单，于是"清单全过"读起来像"核对已完成"，实际只证明"生成器按自己的记忆自洽"。
    **与纪律 15 的分工**：15 管*真值属于哪一类*（来源分类），16 管*这份派生物算不算证据*（证据资格）——
    同一份派生物对第 ③ 类零证明力，对第 ② 类也**不增加**证明力（第 ② 类靠推导链可查，不靠清单打勾）。
    三条可执行口径：
    ① 本文件凡属"上机核对/待外部确认"性质的表列（R-22 签名表末列为唯一一处），须逐行留
      `verified_against = {manual_id, revision, clause}` 槽位；填不出 ⟹ `已核对` 计数不增。
    ② 完成度一律写成 `已核对 k / 总 n`；**`k = 0` 时禁止**"可用 / 已核对 / 可直接上机 / 零接入成本"，
      措辞封顶"**样板就绪，签名与位号未经外部核对**"。
    ③ 清单**不抵扣工时**：省下的是判据、单位换算与线程结构的样板，对照厂商手册的全量比对一分没省
      （把"清单已生成"写成"核对只要 0.5–1 天"即为违规，A-88(c)）。
    ④ **抽取式核对优先于手读（A-89）**：凡厂商工件（官方绑定源文件、头文件、手册 PDF）或数据集原始工件
      （本仓库 `data/raw/` 的 XML/MAT/CSV）里**可机器抽取**的字段——函数名是否存在、DLL 归属、参数个数、
      列名与列序、属性名与有无单位——一律由抽取脚本重生成，**禁止凭记忆书写**；抽取未覆盖的行标
      `unverified_signature`（这是**文档侧称呼**，报告侧载体是 C3 规则 17 台账的 `extracted: false`，
      不再新增第二个字段名——A-54"只有一个名字"同律），其 `external_reference` 按最低档 `memory` 处理（未标档即默认 `memory`）。
      理由：记忆是这一族错误的唯一载体，把它留在回路里，清单再全也只是把错误抄一遍。
      边界也要说死：抽取管得住**存在性/归属/参数个数**，管不住**参数顺序与语义、调用序列前提、
      以及"主机该不该写某个对象字典项"这类机器安全动作**——后者仍属 ③b，不因工件到手而降格为已解。
    ⑤ **自称能自曝的断言必须有负向测试（A-89，KB0 §6 检查 22）**：本文件若写下"某检查能抓 X 类缺陷"，
      必须同时给出"故意注入 X 类缺陷后该检查真的报错"的样例；没有负向测试的断言按纪律 16 首段处理——
      对它声称保护的那件事没有证明力（"断言在跑"≠"断言能抓"）。
    **自我适用**：本仓库的 12/12 `JSON.parse`、A-72/A-76/A-83 的逐格复算、KB0 §6 各条 grep 检查，
    证明的是内部一致性与可复算性，**不是**外部正确性，不得写成"已验证/验证通过"级证据（KB0 §6 检查 20 末段）。

### 0.1 记号（本文件唯一一次定义）

| 记号 | 含义 |
|---|---|
| `f_b` | `freq_limits.reliable_band_hz` |
| `f_N` | `freq_limits.nyquist_hz` |
| `Δf` | `resonance.resolution_hz`（= `fs/nperseg`） |
| `T_s` | `1/fs` |
| `CPR` | `meta.axis.motor_rev_counts`（电机轴每转 counts） |
| `I`, `I_seg` | 全样本集 / 某分段样本集 |
| `M(·)` | 中位数；`E(·)` 去均值能量；`RMS(·)` 去均值均方根 |
| `abs(x)` | 绝对值（表格里用此写法避免与表格分隔符冲突） |
| `τ_u` | `event_context.sync.uncertainty_ms` |
| `⟹` | 蕴含；其左侧所有特征非 null 是隐式前置条件（纪律 1） |
| `[L]` / `[P]` | 阈值来源：文献可证 / 本项目自定（见第三部分逐条合法化） |
| `band⊥` | 该规则对 `freq_limits.reliable_band_hz` 的硬下界 |

---

## 1. 特征索引表（C2 硬性规则 4）

点号路径 + 数组 `[]`（KB0 §3）。**本表 = C3 证据允许引用的路径集合**（只覆盖 **C2** 伺服波形特征）；
未登记于 C2 **或** C7 的路径不允许出现在规则证据里，违反者在加载期抛异常（C5 §3 "结构上无法造假"；裁决 A-34）。
**工艺/标定侧特征索引不在本表**：`process.*` / `calibration.*` / `cycle_stats.*` / `scan_program.*` /
`power_channel.*` 的逐字段口径以 **C7 §2.2 / §4.2 的"口径"列**为唯一权威（裁决 A-40），本表不复制、不另设"工艺特征索引"。
凡引用 `meta.*` / `drive.*` / `quality.*`（非 C2 特征路径）的量，写入"输入通道"栏并显式标注来源，且不得作为
`supporting_evidence[].feature` 引用——只能作为 `necessary_context` 出现在报告叙述里。

### 1.1 `global.*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件（→ null + 进 `unavailable`） | 出处 |
|---|---|---|---|---|---|
| `global.fe_rms_counts` | `RMS(fe) = sqrt(mean((fe - mean(fe))²))`，`I` 全样本（C4 指标定义：去均值 RMS）。载体 `src/axiscope/features.py::_ac_rms`——**A-114（2026-10-21）：实现此前算的是原始 RMS（不减均值），与本式差一个常偏；已改判为实现服从本式**（R-02 的 `fe_p999/fe_rms ≥ 4` 分子是 median 中心的波动量，分母含常偏会把比值压低约两个量级 ⟹ 有稳态误差的样本上该判据漏报，故这不是口径偏好而是判据正确性） | `fe`；若无则由 C1 派生规则 1 `fe := pos_cmd - pos_fb` | 任意 | 无 `fe` 且 `pos_cmd`/`pos_fb` 不全 | C4-validation.md §指标定义 |
| `global.fe_rms_mm` | `fe_rms_counts / counts_per_mm`（**支①**）；或 `fe_rms_(m) × 1000`（**支②**，C2 规则 3 A-113） | 支①同 + `meta.counts_per_mm`；支②需 `meta.units_are = si_native` 且通道单位在 C1 长度词表 | 任意 | `counts_per_mm == null` **且 `units_are = counts`**（C2 规则 3 支①）；此时报告禁 µm **容差/目标**（纪律 4(c)，A-113 起禁令已按 A-110 ③ 收窄，实测幅值可给）；**si_native 样本上 `*_mm` 能否改由原生 SI 刻度直接填：已裁 A-110 ②，并已随 #39 落地（A-113，2026-10-21）——`units_are = si_native` 且 C1 单位词表登记为长度的通道由随行单位直接定标（`×1000`，纯定标不造数，随行一行 `meta.units_are` 假设）；`units_are = counts` 且 `counts_per_mm == null` 时仍为 null** | 同上 |
| `global.fe_p999_counts` | `quantile_0.999( abs(fe - median(fe)) )` | `fe` | 任意 | 无 `fe`；有效样本 < 1000（分位数不稳；C1 红线 `n_samples<2000` 已整体拒诊断） | 同上 |
| `global.fe_max_counts` | `max abs(fe)`（nan 剔除）——**原始、不减均值**：最坏瞬时误差含常偏，正是要它；本行与 `fe_rms_counts` 是两个并列口径（最坏幅值 / 波动 RMS），**不得互相代用**（A-114） | `fe` | 任意 | 无 `fe` | 同上 |
| `global.fe_mean_counts` | `mean(fe)`（nan 剔除），**原始、不减任何东西**——A-114：`fe_rms_counts` 改为去均值 RMS 后，被减掉的那个常偏必须有独立载体（KB0 §7 A-106 ② 的纪律：减了必须记，否则等于把证据当噪声抹掉）。消费者是 R-22 签名表 ④/⑤ 两行的「均值偏差 / 大非零均值」；本行是**有符号**量，判据用 `abs()` 时须写清 | `fe` | 任意 | 无 `fe`（C1 派生规则 1 的两个输入缺一） | 本项目自定（A-114 为承载常偏而登记，非外部文献定义） |
| `global.fe_sign_change_rate_hz` | `#{i : sgn(fe_i - M(fe)) ≠ sgn(fe_{i-1} - M(fe))} / (t_end - t_start)`，单位 次/s（换 Hz 需再除 2） | `fe` | 任意 | 无 `fe`；`quantization_step_counts ≥ RMS(fe)`（符号翻转完全由量化决定）——该比较 **`【比值·刻度无关】`**：两侧同为 `fe` 原生刻度量，同乘同除不变号向 | 零交叉率，Oppenheim & Schafer（DTSP） |
| `global.cur_q_rms_pct` | `100 · sqrt(mean(cur_q²)) / rated_current_a`（归一化 %）。**命名冲突提示**：C1 的 `cur_q` 单位是 A、`torque`/`cur_cmd` 单位是 %，而本字段名带 `_pct` ⇒ 定义一律以 `rated_current_a` 归一（见 §5 缺口 G-1）。**A-70 分母纪律**：凡与转矩刻度挂钩的 `*_pct`（含 `torque`/`cur_cmd` 侧）分母必须来自 C1 `meta.drive.rated_torque_N_m`，且 `rated_torque_source ∈ {measured, manual, nameplate, assumed}`；`assumed` ⟹ 本字段支撑的判据**出处层级封顶 T2** + caveats 必写"额定转矩为假定值，百分比类判据的绝对刻度不可信"；字段为 `null` ⟹ `*_pct` 恒 `null`，只允许走 `N_m` 绝对值支路 | `cur_q`, `meta.rated_current_a`（转矩侧：`meta.drive.rated_torque_N_m`） | 任意 | 无 `cur_q` 或 `rated_current_a == null`；转矩侧 `rated_torque_N_m == null` ⟹ 转矩类 `*_pct` 恒 null（A-70） | C1 通道词表；C1 §drive A-70 分母纪律；T2 驱动器转矩百分比惯例 |
| `global.cur_q_peak_abs_pct` | `100 · max abs(cur_q) / rated_current_a`（**A-70 分母纪律同上**：转矩刻度侧的 `_pct` 一律以 `meta.drive.rated_torque_N_m` 为分母，`rated_torque_source == "assumed"` 时相关判据层级封顶 T2 并强制 caveat，`null` 时 `_pct` 恒 `null`） | `cur_q`, `meta.rated_current_a` | 任意 | 同上 | 同上 |
| `global.cur_q_saturation_ratio` | `mean over i of 1[ abs(cur_q_i) ≥ I_lim ]`；`I_lim` 取 `meta.drive.current_limit_a`（**A-80 已登记进 C1**，可选、缺省 `null`，值域同 A-70 四档）；缺失时取 `1.0·rated_current_a` 并记 `audit.assumptions` + 特征行 `denominator_basis: "assumed_rated_current"`。★ **偏差方向必须写清**（A-80 修正原句"系统性低估"的歧义）：驱动器限流通常是额定连续值的 2–3 倍，拿额定当代 ⟹ `I_lim` **偏小** ⟹ 本比值**偏高**（把正常满载误判成饱和），不是"低估该比值"。**A-70**：本量是"饱和/余量比"判据，凡其阈值以百分比表达（转矩侧）时分母必须是 `meta.drive.rated_torque_N_m` + `rated_torque_source`；`assumed` ⟹ 饱和判据层级封顶 **T2** + 强制 caveat"额定转矩为假定值，百分比类判据的绝对刻度不可信"；`null` ⟹ 百分比支路关闭，只用 `N_m` 绝对值支路。兜底分母下本量**只作定性支路、不得单独触发归因**（A-80） | `cur_q` + `drive.current_limit_a`/`rated_current_a`（转矩侧 `drive.rated_torque_N_m`/`rated_torque_source`） | 任意 | 无 `cur_q`；`rated_current_a == null` → null；转矩侧 `rated_torque_N_m == null` → 百分比判据 null（A-70） | 本项目自定（定义不完备，见 G-1）；C1 A-70/A-80 纪律 |
| `global.thermal_drift_counts_per_min` | 对 `dwell`/`rest` 段的保持误差 `fe_dwell` 做去均值线性回归：`β = cov(fe_dwell, t)/var(t)`，输出 `60·β`；**其阈值 `2.0` 属【绝对】**（比较量带 counts/min 量纲，见 §1.13b 绝对支索引） | `fe`,`pos_fb`,时间轴 | `dwell`,`rest`（累计 ≥ 120 s，跨度 ≥ 20 min） | 静止/保持段不足；`temp` 缺失时本字段**仍可算**，但温度归因不可做（C2 示例的 `unavailable.reason="缺少 temp 通道"` 指后者） | KB7 `TempSlip` 战役；ISO 230-3 |
| `global.thermal_fe_correlation_r` | Pearson `r`(分箱后的 `temp` 序列, 同箱 `fe_dwell` 统计量序列) | `temp`, `fe` | `dwell`,`rest` | 无 `temp`；分箱数 < 8；`var(temp) < 0.2 °C`（无热激励，r 无意义） | KB7 `TempSlip` |
| `global.reversal_error_counts` | 每个"反向 move"（`sign(vel_cmd)` 相对上一 move 翻转）段内 `max abs(fe)` 在窗口 `[t_r, t_r + τ_r]` 的中位数；`τ_r = max(20 ms, 1/f_pos)`，`f_pos = bandwidth.position_loop_crossover_hz`（null 时取 30 ms 固定窗并记 assumption）；**本字段在规则层只以 `reversal_error / fe_rms` 形式被用，属【比值·刻度无关】（R-02/R-08 两支分列文本；字面常数一叶见 §1.13b 绝对支索引）** | `fe`,`pos_cmd`/`vel_cmd` | `move` ≥ 2 且含反向 | 无反向对（`segment_coverage.move < 2` 或全程单向）；`vel_cmd` 缺失且 `pos_cmd` 无法判向；KB7 方向符号未修正（纪律 9） | KB0 §3 示例判据引用该路径；ISO 230-3 |
| `global.backlash_estimate_counts` | 反向滞回带宽度：对每对反向，令 `x=pos_fb`、`c=pos_cmd`，取反向时刻后 `abs(c)` 已移动 `δ = max(3·量化步长, 0.02·行程)` 的窗内 `b_i = max abs(c - x)`；要求 `b_i` 窗内呈**平台**（`abs(db_i/dt) < 0.1·vel_mean`）；输出 `median(b_i)`。平台条件是间隙与摩擦的分水岭。**入选窗 `δ` 与平台条件都属【比值·刻度无关】**：`3·量化步长`、`0.02·行程`、`0.1·vel_mean` 全部是"同刻度实测量 × 无量纲系数"，量纲相消 | `pos_cmd`,`pos_fb`,`fe` | `move` ≥ 2（含反向） | 无反向段（C2 示例 `reason="无方向反向段"`）；`pos_cmd` 缺失；平台条件不满足（转 R-06/R-15 处理） | ISO 10791 系列 / ISO 230-3（反向失动 lost motion） |
| `global.friction_stiction_ratio` | `mean_i( cur_q_break,i / cur_q_cruise,i )`：`cur_q_break = max abs(cur_q)` 于 `[t_start, t_start+T_b]` 且 `abs(vel_fb) < v_th`（突破峰值）；`cur_q_cruise = median abs(cur_q)` 于中段恒速区；`T_b = max(50 ms, 3/(2π·f_pos))`，`v_th = 0.02·vel_mean` | `cur_q`,`vel_fb`/`vel_cmd`,`pos_fb` | `move`（含完整起步 + 恒速区） | 无 `cur_q`；无恒速区（短行程三角速度轮廓）；`vel_fb` 派生且量化步长 > `v_th` | KB7 `LdaFricIdent`（`tau_T` 7→60 N·m、`v_T≈0` 即突破摩擦真值）；Olsson 1998 |

### 1.2 `spectral.<channel>.*`

三通道共用的计算前提：Welch 周期图，Hann 窗，`nperseg = min(2048, N_seg)`，重叠 50%，
单边 PSD 单位 `量²/Hz`；频率轴截到 `f_b`；JSON 存降采样版（≤ 2048 点），全量写 `features/*.npy`
（C2 规则 1）。`f_min := max(2Δf, 1 Hz)` 用于排除直流。

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `spectral.fe.freq_hz[]`, `spectral.fe.psd[]` | 上述 Welch 输出（降采样） | `fe` | `I` | 无 `fe`；`dt_jitter_ratio > 0.2`（C1 红线，时基不稳则频谱不可信） | Oppenheim & Schafer |
| `spectral.fe.dominant_freq_hz` | `argmax_{f ∈ [f_min, f_b]} psd(f)` | `fe` | `I` | 有效带内 bin 数 < 8 ⟹ null 且**必须**登记 blocked（不得说"无主峰"） | C2 规则 7 |
| `spectral.fe.dominant_psd_ratio` | `∫_{f0 ± max(2Δf, 0.02·f0)} psd df / ∫_{f_min}^{f_b} psd df` ∈ [0,1]（主峰带内能量占比） | `fe` | `I` | 同上 | ISO 10843:1997（纯音成分检测） |
| `spectral.fe.tonality_index` | `1 - SF`，`SF = exp(mean_b log psd_b) / mean_b psd_b`（谱平坦度/Wiener 熵），`b` 遍历 `[f_min, f_b]` 的 bins。`SF→1`（白噪声）⟹ 指标→0；单根谱线 ⟹ 指标→1。C2 示例 fe 0.62 / cur_q 0.71 与"存在明显纯音"一致 | `fe` | `I` | 带内 < 32 bin ⟹ null（平坦度统计量不可靠） | Vattino et al. 2016（Acta Acust. united with Acust. 101(1)，纯音检测）；ISO 10843 |
| `spectral.fe.band_energy[]` | **不在 C2**，规则不得引用（见 G-6） | — | — | — | — |
| `spectral.cur_q.*` | 同上，通道换 `cur_q`（C1 明文 `cur_q` 是共振识别主通道） | `cur_q` | `I` | 无 `cur_q` | 同上 |
| `spectral.cur_q.harmonic_ratios[]` | 取 prominence ≥ 6 dB 于局部中位的 PSD 局部极大 `f_1 < f_2 < …`（`f_1` 为基频），输出 `[f_2/f_1, f_3/f_1, …]` | `cur_q` | `I` | 峰数 < 2 ⟹ null（**不得**把 null 当空数组再当 0；纪律 1） | 阶次分析范式（T1-b 旋转机械） |
| `spectral.vel_fb.dominant_freq_hz` | 同上 | `vel_fb` | `I` | 无 `vel_fb` ⟹ null（C2 示例即此） | — |

### 1.3 `resonance.*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `resonance.candidates[].freq_hz` | `cur_q` PSD 在 `[f_min, f_b]` 的峰（主），合并 `fe`/`vel_fb` 峰并去重（±2Δf 内合并） | `cur_q`,`fe` | `I` | 带内无峰或带为空 ⟹ 候选为空数组，且 `blocked_rules` 必须已登记（R-25） | Butler（在线版）；Yaskawa Σ-7 机械系统调整手册陷波条目 |
| `resonance.candidates[].coherence_torque_velocity` | 幅值平方相干 `γ²(f0) = abs(S_xy(f0))² / (S_xx·S_yy)` ∈ [0,1]；`x = cur_q`、`y = vel_fb`（无 `vel_fb` 时 `y = fe` 并置 `method="fe_proxy"`）；Welch 互谱，段数 ≥ 4 | `cur_q`,`vel_fb`(或 `fe`) | `move`,`dwell` | 无 `cur_q`；段数 < 4 ⟹ null；`vel_fb.derived == true` 时 ×0.7（C1 规则 4） | Bendat & Piersol, *Random Data*（相干作为 FRF 可信度判据） |
| `resonance.candidates[].antiresonance_freq_hz` | 在 `[0.4·f0, f0]`（**`sensor_config == "motor_side"` 共置构型下谷必低于峰**，KB5 §1.2 顺序判据；`load_side` 取镜像窗 `[f0, 1.6·f0]`；`unknown`/`mixed` 不设顺序窗，A-68）内对平滑 PSD（或 `abs(H1(f)) = abs(S_yx/S_xx)`）取局部极小 `f_a`；要求 `psd(f0)/psd(f_a) ≥ 6 dB` 且 `f0 − f_a ≥ 2Δf`。若在 `[f0, 2·f0]` 才找到谷，该值只可记为"候选谷"，**不得**直接用于双惯性判定 | `cur_q`,`vel_fb`/`fe` + `meta.sensor_config` | `move` | 无 6 dB 谷 ⟹ null；`f_a > f_b` ⟹ null **且**登记 blocked（正是 R-04 在 fs=1k 的情形） | 双惯性理论：Leonhard 1996；Kempf 1993；KB5 §1.2（极点/零点交替） |
| `resonance.candidates[].present_in_dwell` | `1[ E(f0±Δf, dwell)/E_total(dwell) ≥ 0.05 且 psd 峰/局部中位 ≥ 6 dB ]`；`dwell` = 指令恒定、驱动器使能、闭环保持 | `cur_q`,`fe` | `dwell`（≥1 个，累计 ≥ 0.5 s） | `segment_coverage.dwell == 0` ⟹ null | C1 §segments 说明（"高频恒定啸叫只在 dwell 仍出现才判机械共振"）；T1-b 工况相关性 |
| `resonance.candidates[].present_in_rest` | 同上，段类型 `rest`（使能关闭或零指令且无保持动作） | `cur_q`,`fe` | `rest` | `segment_coverage.rest == 0` ⟹ null。**null ≠ false**（纪律 1）：此 null 使 R-10/R-26 降级并把 R-03 置信上限压到 0.55 | 同上 |
| `resonance.candidates[].tracks_command_frequency` | 各 `move` 段主节律 `f_seg = 1/T_move`；若 `f0/f_seg` 的变异系数 < 0.1 ⟹ true（峰跟随指令而非结构固有属性） | `pos_cmd` + 峰频 | `move` ≥ 4 | `segment_coverage.move < 4` ⟹ null | 阶次跟踪范式（T2） |
| `resonance.candidates[].amplitude_ratio_vs_broadband` | `psd(f0) / M(psd over [0.8·f0, 1.25·f0] 去掉 ±3Δf)`（峰/本地中位，线性比；6 dB ≈ 4） | `cur_q` 或 `fe` | `I` | 带内 bin 数 < 15 ⟹ null | ISO 10843（峰值-均值比） |
| `resonance.candidates[].quality_factor_estimate` | `Q = f0 / Δf_(−3dB)`，`Δf_(−3dB)` 为功率降至 `psd(f0)/2` 的两侧宽度；等价 `Δf = f0/Q`；可用 `abs(H1)` 的相位斜率一致性交叉核验 | `cur_q`/`fe` PSD（或 `abs(H1)`） | `I` | `Δf_(−3dB) < 2Δf`（峰被分辨率窗淹没）⟹ null；`Q > 200` 视为测量伪影并记 assumption | Dorf & Bishop（谐振峰与阻尼）；Yaskawa 陷波宽度条目 |
| `resonance.candidates[].is_double_inertia_pair` | `1[ antiresonance_freq_hz != null 且 顺序条件成立 且 f_0/f_a ∈ [1.05, 2.7]（等于 sqrt(1+λ)，λ 为惯量比）且 γ²(f_0) ≥ 0.7 且 峰/谷 ≥ 6 dB ]`；**顺序条件按 `meta.sensor_config` 四值取**（A-68）：`motor_side` ⟹ `f_a < f_0`；`load_side` ⟹ `f_a > f_0`（镜像）；`unknown`（不知在哪侧）与 `mixed`（峰/谷跨两套通道、非同一传递函数）**一律不参与顺序判定** ⟹ 本字段只能由幅值/相位条件给出，且 R-04 置信度封顶（两者差别仅在记录原因，`mixed` 的原因是"已知零极点交替信息不存在"）。 | `cur_q`,`vel_fb`/`fe` + `meta.sensor_config` | `move` | 任一依赖 null ⟹ null；`sensor_config ∈ {unknown, mixed}` 时顺序项不计、结论封顶（**已裁 A-68**） | 双惯性理论；Beckhoff 机械谐振/陷波文档；KB5 §1.2 |
| `resonance.nyquist_hz` | `fs/2` | — | — | — | 采样定理 |
| `resonance.resolution_hz` | `fs / nperseg` | — | — | — | 同上 |

C2 规则 6 明确：`present_in_dwell`、`present_in_rest`、`tracks_command_frequency`、
`is_double_inertia_pair` **四个条件共同决定归因方向，缺一不可**。因此 R-03/R-04/R-26 任一字段
为 null 即放弃或降级，不得用其余三个替代。

### 1.4 `ripple.probing[].*`（恒速 `probing` 段纹波）

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `ripple.probing[].segment_id` | C1 `segments` 的 id | — | `probing` | — | C1 |
| `ripple.probing[].vel_mean_counts_s` | `mean(vel_fb)` over 整数转窗口 | `vel_fb` | `probing` ≥ 1（≥2 整转） | `segment_coverage.probing == 0` ⟹ 数组为空，R-05/R-07/R-12 依赖处进 `rules_skipped` | KB7 恒速摩擦/滑移辨识段 |
| `ripple.probing[].ripple_pp_counts` | 位置残差 `r(t) = pos_fb − fit(pos_fb; t)`（按每转折叠去趋势），`max(r) − min(r)`，跨整转取中位 | `pos_fb` | `probing` | 转数 < 2；去趋势 `R² < 0.9`（非真恒速） | ISO 230-3 |
| `ripple.probing[].ripple_rms_counts` | `sqrt(mean(r²))` | `pos_fb` | `probing` | 同上 | 同上 |
| `ripple.probing[].dominant_order_per_rev` | 以"每转角度 `θ = pos_fb mod CPR`"为自变量对 `r` 做阶次谱，主峰**阶次 `k`**（每转周期数，无量纲）；物理周期长度 = `CPR/k` counts。**裁决 A-11：原字段名 `dominant_period_counts_per_rev` 量纲错（`counts/rev` 不可能为 1.0），C2 已改名为 `dominant_order_per_rev`，语义即阶次 `k`**；C2 示例值 `1.0` 表示"每转 1 个周期"。规则一律用阶次 `k` 判定，不得把这个字段当 counts 数值比较（旧缺口 G-3 已裁）。**阶次 `k` 本身无量纲 ⟹ 【比值·刻度无关】；但本特征的 folding 基 `CPR` 量纲是 counts/rev，`si_native` + `counts_per_mm == null` 时"每转"在位置通道上无定义** ⟹ **已裁 A-110 ①**（归 `absent_counts_scale`，不自造配对常数）| `pos_fb`, `meta.axis.motor_rev_counts` | `probing` | `CPR == null` ⟹ null（"每转"无定义）；峰 prominence < 6 dB ⟹ null | Bao/Meng/Tsai/Lee 1993（伺服周期误差谐波建模）；Heidenhain 误差补偿 |
| `ripple.probing[].ripple_over_velocity_pct_per_rev` | `100 · ripple_pp_counts / vel_mean_counts_s`（整数转窗口上求值，`_per_rev` 表示按整转归一以消除分数转伪影）；C2 示例 `100·340/52000 = 0.65` 一致。**`【比值·刻度无关】`**：分子分母同为位置原生刻度量（counts 与 counts/s），换刻度同乘同除 ⟹ 与 `counts_per_mm` 无关；"整转窗口"这一前置受上一条 `CPR` 复判项约束 | `pos_fb`,`vel_fb` | `probing` | `vel_mean ≤ 0`；无整转窗口 ⟹ null | KB7（`x_T`/`x_asco`/`x_lsv` 三传感器交叉验证思路） |
| `ripple.probing[].correlated_with_cur_q` | Pearson `r`(带通后的 `r(t)`, `cur_q − mean`)，带 `[k/(2πT), 3k/(2πT)]` | `pos_fb`,`cur_q` | `probing` | 无 `cur_q` ⟹ null | T1-b（帕德博恩电流-振动归因） |

### 1.5 `crawling.low_speed_segments[].*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `crawling.low_speed_segments[].segment_id` | C1 段 id | — | `move`/`probing` | — | C1 |
| `crawling.low_speed_segments[].vel_mean_counts_s` | `mean(abs(vel_fb))`；入选条件 `vel_mean < v_ls`，`v_ls` **按 A-97 分两支**（§1.13b）：`【绝对】` 支 `= 50 counts/s`（字面 counts/s 常数，`counts_per_mm == null` 时该支不可比 ⟹ `blocked_by = absent_counts_scale`，reason「无 counts 刻度，绝对阈值不可比」）；`【比值·刻度无关】` 支 `= 0.01·vel_cmd_max`（与被测量同刻度，量纲相消）⟹ `v_ls := 绝对支可用时取 max(两支)，绝对支不可比时只取比值支` `[P]` | `vel_fb`,`vel_cmd` | `move`,`probing` | 无低速段 ⟹ 数组为空（C3 示例对 R-05 的 skip 原因正是"本样本无恒低速段"）；只剩比值支时须记 `audit.assumptions`"低速窗退化为行程相对窗" | KB7 低速摩擦段；Olsson 1998 |
| `crawling.low_speed_segments[].is_sawtooth` | `1[ 自相关峰 ≥ 0.5 且 上升/下降时间比 ≥ 2 且 一阶差分符号游程长度分布显著偏斜 ]`（黏滑速度的锯齿形态） | `vel_fb` | 同上 | 段时长 < 2 s 或周期数 < 3 ⟹ null | Olsson 1998（stick-slip）；Armstrong 1994 |
| `crawling.low_speed_segments[].sawtooth_freq_hz` | 该段 `vel_fb` 谱主峰，必须在 `[0.1 Hz, min(50, f_b)]` | `vel_fb` | 同上 | 带内 bin < 8 ⟹ null | 同上 |
| `crawling.low_speed_segments[].vel_min_ratio` | `min(vel_fb) / vel_mean_counts_s`（仅取指令同向样本）；0.0 = 完全停住（C2 示例即 0.0，`stall_count = 3`）。**`【比值·刻度无关】`**：分子分母同为速度原生刻度，相消 ⟹ R-05 的 `≤ 0.15` 与刻度无关 | `vel_fb`,`vel_cmd` | 同上 | 段内无有效速度样本 | 同上 |
| `crawling.low_speed_segments[].stall_count` | 不相交区间数：`abs(vel_fb) < 0.01·abs(vel_cmd)` 且 `abs(vel_cmd) > 0` 且持续 ≥ `max(3T_s, 5 ms)`。**`【比值·刻度无关】`**：`0.01·abs(vel_cmd)` 与被测量同刻度，量纲相消 | `vel_fb`,`vel_cmd` | 同上 | `vel_cmd` 缺失 ⟹ null | KB7 `v_T≈0` 真值；T2 |
| `crawling.low_speed_segments[].corr_vel_vs_curq` | Pearson `r`(带通 `vel_fb`, `cur_q`)；黏滑典型强相关（C2 示例 0.79） | `vel_fb`,`cur_q` | 同上 | 无 `cur_q` ⟹ null | T1-b；Olsson 1998 |

### 1.6 `ff_mismatch.*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `ff_mismatch.accel_regime_rms_counts` | `a(t) = d(vel_cmd)/dt`（或 `pos_cmd` 二阶差分后低通 `f_b/4`）；`Ω_acc = {i ∈ I_move : a_i ≥ a_min}`，`a_min = 0.05·max abs(a)` `[P]`（**`【比值·刻度无关】`**：加速度窗门限取自身最大值的 5%，无字面量纲常数）；输出 `RMS(fe abs Ω_acc)` | `pos_cmd`/`vel_cmd`,`fe` | `move` | 无 `pos_cmd` ⟹ 无 `a`；`abs(Ω_acc) < 50` ⟹ null | Butler；Rockwell《Strictly Servo》 |
| `ff_mismatch.decel_regime_rms_counts` | 同上，`Ω_dec = {i : a_i ≤ −a_min 且 sign(a_i) ≠ sign(vel_cmd_i)}`（`a_min` 同上属**`【比值·刻度无关】`**） | 同上 | `move` | `abs(Ω_dec) < 50` ⟹ null | 同上 |
| `ff_mismatch.asymmetry_ratio` | `accel_regime_rms_counts / decel_regime_rms_counts`（C2 示例 2.26）。**`【比值·刻度无关】`**：分子分母同为 `fe` 原生刻度 RMS，刻度一进一出 ⟹ R-15/R-02 用它不构成绝对判据。**该比值是有向量的模**（裁决 A-26）：`>1` ⟹ 加速段误差占优（欠补偿一侧），`<1` ⟹ 减速段误差占优（过补偿一侧，镜像）；R-15 判据必须对两支分别给符号+幅值条件，不得只判 `>1` 一侧。有符号形式 `A_s` 见 R-15 | 同上 | `move` | 任一 null | 同上 |
| `ff_mismatch.fe_vs_accel_corr` | Pearson `r(fe, a)`，`fe` 去均值、`a` 低通 `f_b/4`（C2 示例 0.83） | `fe`,`pos_cmd` | `move` | `abs(Ω) < 50`；`dt_jitter_ratio > 0.05` ⟹ null | 同上 |
| `ff_mismatch.residual_slope_vs_jerk_corr` | `j = d(a)/dt`；Pearson `r(d(fe)/dt 的残差斜率, j)`（C2 示例 0.44） | `pos_cmd`,`fe` | `move`,`path` | `dt_jitter_ratio > 0.05`（二阶导对时基抖动极敏感）⟹ null | 本项目自定 |

### 1.7 `encoder.*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `encoder.per_rev_periodic_present` | `1[ 位置残差按 CPR 折叠后的阶次 k 峰 prominence ≥ 6 dB 且 跨转相位一致 ]` | `pos_fb`（有第二套独立测量更佳，见 G-7） | `probing` 或恒速 `move` | 无 ≥2 整转；`CPR == null` | Heidenhain 插值误差补偿文献；Bao 1993 |
| `encoder.per_rev_amplitude_counts` | 一阶谐波最小二乘幅值 `A_1 = sqrt(a_1² + b_1²)`，回归基为 `cos(2πθ/CPR)`、`sin(2πθ/CPR)`，`θ = pos_fb` 去趋势。**R-07 用它做的比较（`≥ 0.2·fe_rms`）属【比值·刻度无关】**（与 `fe_rms` 同刻度）；但回归基里的 `CPR` 是 counts/rev 常数 ⟹ `si_native` + `counts_per_mm == null` 时该特征**算不算得出**已裁 A-110 ①（无 counts 刻度 ⟹ 阶次族 `not_evaluable` + `absent_counts_scale`，不自造配对常数） | `pos_fb` | 同上 | 同上 | 同上 |
| `encoder.harmonics_per_rev` | prominence ≥ 6 dB 的显著阶次数；插值误差典型阶次 = 每转刻线数（数十~数百），偏心/安装误差典型 `k = 1` | `pos_fb`, `meta.encoder_lines` | 同上 | 同上 | Heidenhain（单刻距周期误差）；C1 `encoder_lines` |
| `encoder.detrended_r2` | 用 `Σ_{k=1..5} A_k·sin(kθ + φ_k)` 拟合位置残差后的决定系数（C2 示例 0.62） | `pos_fb` | 同上 | 转数 < 2 ⟹ null | 同上 |
| `encoder.phase_locked_to_pos_modulo` | `1[ 残差峰与 (pos_fb mod CPR)/CPR 的相位关系在各转一致，相位散布 < 30° ]` | `pos_fb` | 同上 | `CPR == null`；跨转数 < 4 ⟹ null | 同上 |

### 1.8 `step_response[].*`（每 `settling` 段一条）

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `step_response[].segment_id` | C1 段 id | — | `settling` | — | C1 |
| `step_response[].overshoot_pct` | C4 定义：`max(同号超出量) / move_amplitude × 100`，`move_amplitude = abs(pos_cmd(end) − pos_cmd(start))`。**`【比值·刻度无关】`**（分子分母同为位置原生刻度，相消） | `pos_cmd`,`pos_fb` | `settling` | 只有 `fe`（C1 派生规则 3 ⟹ 运动学特征标 `unavailable`）；`move_amplitude < 20·量化步长`（量化主导；`20×量化步长` 与被测量同刻度 ⟹ **`【比值·刻度无关】`**，量化步长取 `quality_ref.quantization_step_counts` 的原生刻度读数） | Nise；Dorf & Bishop |
| `step_response[].settling_time_ms` | 进入并**保持**在 `±settle_band_counts` 内的最早时刻到段末（C4 定义） | `pos_cmd`,`pos_fb`,`fe` | `settling` | 段内从未入带 ⟹ null（不是"很大"） | 同上 |
| `step_response[].settle_band_counts` | 判稳带宽（counts），来自 `meta.drive`/工艺容差；本项目默认 `[P]` **按 A-97 分两支**：`【绝对】` 支 `20 counts`（字面 counts 常数 ⟹ `counts_per_mm == null` 时该支不可比，`blocked_by = absent_counts_scale`，reason「无 counts 刻度，绝对阈值不可比」）/ `【比值·刻度无关】` 支 `0.02·fe_rms`（与 `fe` 同刻度，相消）⟹ 默认式写作 `max(绝对支, 比值支)`，绝对支缺席时**只取比值支**，不得把 20 当作 m 用 | 同上 | `settling` | `counts_per_mm == null` 时禁止换算 µm（纪律 4，A-97 更正口径见 §1.13b）；两支皆不可得（无工艺容差且 `fe_rms == null`）⟹ 本字段 null | 同上 |
| `step_response[].settle_band_pct_of_move` | `100·settle_band_counts / move_amplitude`（C2 示例 0.04%）。**`【比值·刻度无关】`**：分子分母同刻度相消 ⟹ 与 `counts_per_mm` 无关，R-08/R-29 用它是安全的一支 | 同上 | `settling` | `move_amplitude == 0` | 本项目自定 |
| `step_response[].ringing_cycles_to_settle` | 相对终值的过零次数 / 2 | `pos_fb` | `settling`,`move` | 无过零 ⟹ 整数 0（真 0，与 null 不同） | 同上 |
| `step_response[].damping_ratio_estimate` | 对数衰减率：`ζ ≈ (1/(2π))·ln(x_1/x_2)`（相邻同号峰比）；或包络指数拟合 `ζ = σ/ω_d`（C2 示例 0.28，C3 用它做反证 R-03c） | `pos_fb` | `settling` | 峰数 < 2 ⟹ null（**不得**给保守默认值） | Dorf & Bishop §二阶系统 |
| `step_response[].rise_time_ms` | 10% → 90% | `pos_fb` | `settling` | 噪声底 > 量程 10% ⟹ null | 同上 |
| `step_response[].limit_cycle_present` | `1[ dwell/保持残差谱存在单峰且峰/本底 ≥ 6 dB 且 频率与 f_pos 相当 ]` | `fe`,`pos_fb` | `dwell`,`rest`,`settling` | 段缺失 ⟹ null（不得当 false） | Olsson 1998（摩擦+积分器极限环）；T1-b |
| `step_response[].limit_cycle_amplitude_counts` | 该极限环的时域幅值（C2 示例 null，即未判定）。规则层只用它的**比值形式**（R-14 `≥ 0.5·settle_band`、R-17 `≤ 3·量化台阶`，均属 **`【比值·刻度无关】`**），本字段自身的裸幅值不挂任何字面 counts 常数 | 同上 | 同上 | `present ∈ {null,false}` ⟹ null | 同上 |
| `step_response[].limit_cycle_freq_hz` | 峰频，必须在 `[f_min, f_b]` 内（纪律 2） | 同上 | 同上 | 越带 ⟹ null + blocked | 同上 |
| `step_response[].limit_cycle_waveform` | 极限环波形形状，词表 `{sinusoidal, sawtooth, other}`；判据：过零间隔变异系数 ≤ 0.25 ⟹ `sinusoidal`，≥ 0.5 且存在"停-走" ⟹ `sawtooth`，否则 `other` | `fe`,`pos_fb`,`vel_fb` | `dwell`,`rest`,`settling` | `limit_cycle_present != true` ⟹ null（**不得**当 `other`） | **已裁 A-95 新增**（C2 字段载体）：本项目自定 `[P]`，无文献背书；它只服务于 R-05/R-14 的形状分界 |

### 1.9 `tracking.path_segments[].*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `tracking.path_segments[].segment_id` / `.kind` | C1 段 id；`kind` 恒为 `"path"`（插补连续路径） | — | `path` | 无 `path` 段 ⟹ 数组空 | C1 词表 |
| `tracking.path_segments[].fe_rms_counts` | 段内去均值 RMS | `fe` | `path` | 无 `fe` | C4 |
| `tracking.path_segments[].fe_max_counts` | 段内 `max abs(fe)` | `fe` | `path` | 同上 | C4 |
| `tracking.path_segments[].corner_error_counts` | 拐角事件（`abs(a) > 0.3·max abs(a)` 或曲率局部极大）后窗 `T_c = max(50 ms, 1/f_pos)` 内 `max abs(fe)` 减段基线中位（C2 示例 420） | `pos_cmd`,`fe` | `path` | 无拐角事件 ⟹ null | FANUC AI contour control / SINUMERIK APC（前瞻与拐角减速；T2 条目号需复核） |
| `tracking.path_segments[].velocity_feedforward_pct_applied` | **反演估计**：`vel_cmd` 对 `d(pos_fb)/dt` 回归，扣除反馈支路（增益×误差）后的等效前馈比例；C2 示例为 null | `vel_cmd`,`pos_fb` | `path` | `vel_cmd` 缺失 ⟹ null（C2 示例正是 null）；`f_pos` 未知 ⟹ 无法扣反馈支路 ⟹ null | 本项目反演法（合法性见 §3.2） |
| `tracking.path_segments[].acceleration_feedforward_pct_applied` | 同上，回归量为 `a`；需 `cur_q` 作为转矩侧交叉核验 | `pos_cmd`,`vel_cmd`,`cur_q` | `path` | `cur_q` 缺失或 `a` 不可辨 ⟹ null | 同上 |
| `tracking.path_segments[].corr_fe_vs_accel` | Pearson `r(fe, a)`（C2 示例 0.91） | `fe`,`pos_cmd` | `path` | `dt_jitter_ratio > 0.05` ⟹ null | Butler |
| `tracking.path_segments[].corr_fe_vs_jerk` | Pearson `r(fe, j)`（C2 示例 0.32） | `fe`,`pos_cmd` | `path` | 同上（`j` 更敏感） | 同上 |

### 1.10 `bandwidth.*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `bandwidth.position_loop_crossover_hz` | **H1 估计**：`H1(f) = S_yx(f)/S_xx(f)`，`x = pos_cmd`（输入）、`y = pos_fb`（输出）⟹ 得到闭环互补灵敏度 `T(jω)`。取 `abs(T) = 1/sqrt(2)` 的频点 `f_(−3dB)`；在 `[f_min, f_b]` 内，由 `T` 反解环路 `L = T/(1−T)`（高频段 `abs(T) < 0.1` 时数值发散，取 `abs(T) ≥ 0.15` 的最低频率点为有效区间）。高环路增益下一阶近似 `f_pos ≈ f_(−3dB)`，报告需同时给两者 | `pos_cmd`,`pos_fb` | `move`,`path`（须含宽带激励） | `S_xx` 在 `f_(−3dB)` 低于 `S_yy`（激励枯竭）⟹ null；`f_(−3dB) ≥ f_b` ⟹ null + blocked；指令谱在观测带滚降 > 20 dB/dec ⟹ null | Oppenheim & Schafer；Bendat & Piersol（H1/H2/H∞ 偏差讨论） |
| `bandwidth.phase_margin_deg` | 在 `abs(L) = 1` 处 `PM = 180° + arg L(f_gc)` | 同上 | 同上 | 带内无 `abs(L)=1` 交越 ⟹ null | Franklin & Powell；Dorf & Bishop |
| `bandwidth.gain_margin_db` | 在 `arg L = −180°` 处 `GM = −20·log10 abs(L)` | 同上 | 同上 | `arg L` 因陷波/非最小相位而单调递增（无 −180° 穿越）⟹ null（**此时不得报"裕度足够"**） | 同上 |
| `bandwidth.method` | 固定 `command_response_h1`（C2 规则 5：估计类必带 `method`+`confidence`） | — | — | — | C2 |
| `bandwidth.confidence` | **本文件锁定上界 0.6**（与 C2 示例一致），任何实现不得给它更高值。理由五条：(1) 非注入激励，指令频谱在高频能量枯竭，`S_xx→0` 使 H1 方差爆炸；(2) 闭环中 `pos_cmd` 与输出噪声通过反馈相关 ⟹ H1 **系统性有偏**（应使用 H2/H∞，但那需要开环侧信息）；(3) 未知陷波/滤波人为改变局部 `abs(T)`，`meta.drive.notch_filters` 常为 null（C1 示例即为 `[]`）；(4) 量化与差分噪声放大；(5) 若 `vel_fb`/`fe` 为派生，还要 ×0.7（C1 规则 4）。结论：只能定性，**不得作为增益上调的唯一支撑** | — | — | — | C2 示例 + 上述理论依据 |
| `bandwidth.note` | 必须复述"由 pos_cmd/pos_fb 的 H1 估计，非注入激励，仅供定性" | — | — | — | C2 |

### 1.11 `freq_limits.*`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `freq_limits.fs_hz` | `1 / quality.dt_median_s` | 时间轴 | — | `dt_jitter_ratio > 0.2` ⟹ C1 红线整体拒诊断 | C1 |
| `freq_limits.nyquist_hz` | `fs/2` | — | — | — | 采样定理 |
| `freq_limits.reliable_band_hz` | `nyquist / 1.25`（留抗混叠余量） | — | — | — | C2 规则 7 |
| `freq_limits.blocked_rules[]` | 所有声明频点越带的规则 id 集合；fs = 1 kHz 时**至少**含 `["R-03","R-04"]`（C2/C3 示例），并按 §2.1 的 `band⊥` 表动态追加 | — | — | — | KB0 §1；C2 规则 7 |
| `freq_limits.reason` | 文本，必须含"奈奎斯特以下无该频段信息"，禁写"无共振" | — | — | — | C2 |

### 1.12 `event_context.*`（软件族唯一证据来源）

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `event_context.available` | `events.jsonl` 存在且可解析、且 `t` 有样本落入波形时间窗 | 事件流 | — | 无文件 ⟹ `false`，触发整族 `not_evaluable`（C6 §4） | C6 §1 |
| `event_context.n_events` | 过滤后行数 | — | — | — | C6 |
| `event_context.n_by_source.motion/.drive/.interp/.network/.host/.vision/.process` | 按 C6 `source` 词表计数 | — | — | 某源为 0 ⟹ 整数 0（真 0），与"字段缺失"不同；但**规则依赖该源的细节字段时仍要放弃** | C6 §1 |
| `event_context.n_alarm` | `level ∈ {alarm,error}` 计数 | — | — | — | C6 |
| `event_context.host_pause_max_ms` | `max(detail.duration_ms)` over `source=host` 的 `pause`/`gc` 事件；无 `duration_ms` 时用相邻 `host` 事件间隔减模型周期估计，并记 `audit.assumptions` | `host` 事件 | 任意 | 无 `host` 事件 ⟹ null（**不是 0**）；`interp` 事件不得计入（源混用即假归因） | C6 §0 行 1 |
| `event_context.host_pause_count` | **不新增（裁决 A-8/G-2 已收口）**：C6 §4 曾列该字段，裁决为**不引入**，`n_by_source.host` 已覆盖计数语义 ⟹ 规则一律不引用，计数走 `n_by_source.host` + `host_pause_max_ms` | — | — | — | A-8（已裁） |
| `event_context.interp_underrun_count` | `count(source=interp, code=buffer_underrun)` | `interp` | — | `n_by_source.interp == 0` ⟹ null | C6 §0 行 2 |
| `event_context.interp_underrun_during_path` | 同上且 `t ∈` 某 `path` 段 | `interp` | `path` | 无 `path` 段 ⟹ null | KB0 §3 示例路径 |
| `event_context.network_cycle_miss_count` | `count(source=network, code ∈ {missed_cycle, wkc_error, timeout})` | `network` | — | 无 `network` 事件 ⟹ null | C6 §0 行 3 |
| `event_context.vision_result_latency_p95_ms` | `quantile_0.95(detail.latency_ms)` over `source=vision, code=result` | `vision` | — | 无 `vision` 事件或 `latency_ms` 字段缺失 ⟹ null | C6 §0 行 4 |
| `event_context.fe_spike_count` | `fe` 上滑动窗内 `abs(fe − M(fe)) > max(5·MAD, 0.25·fe_p999_counts)` 的不相交事件数（MAD = 中位绝对偏差，稳健尺度）。**`【比值·刻度无关】`**：两支门限都是"`fe` 自身尺度的倍数"（MAD 与 `fe_p999` 同为 `fe` 刻度），量纲相消；计出的尖峰**个数**本身无量纲 | `fe` | `move`,`path`,`settling` | 无 `fe` ⟹ null | 本项目自定 |
| `event_context.fe_spike_aligned_to_host_pause` | 上述尖峰中 `min abs(t_spike − t_pause) ≤ max(τ_u, 2 ms)` 的个数；**窗口必须 > τ_u**（纪律 6） | `fe`,`host` | 任意 | `available == false` 或无 `host` 事件 ⟹ null；`causal_claims_permitted == false` 时只能作共现呈现（纪律 5） | C6 §3；C2 规则 8 |
| `event_context.fe_spike_aligned_to_underrun` | 同上，对齐目标为 `interp` 欠载事件（C2 示例 11/17） | `fe`,`interp` | `path` 优先 | 同上 | 同上 |
| `event_context.bus_cycle_hold_max_ms` | 丢周期/网络异常期间"单周期指令保持（pos_cmd 平台）"的最长时长（ms）；A-9 新落 C2（旧 G-5 收口），R-20 升级归因条件① | `pos_cmd`,`network` | 任意 | 无 `network` 事件或无平台可辨 ⟹ null | C2 `event_context`；A-9 |
| `event_context.fe_spike_aligned_to_network_miss` | 尖峰中对齐到 `network` 丢周期事件的个数；窗口 > τ_u（纪律 6）。A-9 新落 C2，R-20 升级归因条件① | `fe`,`network` | 任意 | `available == false` 或无 `network` 事件 ⟹ null；`causal_claims_permitted == false` 时只作共现 | C2；A-9 |
| `event_context.fe_spike_aligned_to_vision_result` | 尖峰中对齐到 `vision` 结果事件的个数（A-9 新落 C2，旧 G-6/G-9 收口，R-21/R-28 用） | `fe`,`vision` | 任意 | 无 `vision` 事件 ⟹ null | C2；A-9 |
| `event_context.fe_spike_aligned_to_recipe_change` | 尖峰中对齐到 recipe 变更（`process` 事件）的个数（A-9 新落 C2，R-22 签名表与 A-46 CP-11 用） | `fe`,`process` | 任意 | 无 recipe 变更事件 ⟹ null（C2 示例为 0，整数 0 ≠ null） | C2；A-9 |
| `event_context.alignment_residual_ms` | `median` over 匹配对的 `abs(Δt)`；作为对齐质量自陈 | — | — | 匹配对 < 3 ⟹ null | C6 §3 |
| `event_context.sync.method` | 词表：`ntp`、`host_clock`、`trigger_edge`、`manual_offset`、`unknown`（表格内不用竖线分隔以免破坏表格） | — | — | 缺 ⟹ `unknown` | C6 §3 |
| `event_context.sync.verified` | 是否有对齐证据（如共用一次 `bTrigger_Scope` 上升沿、残差已报） | — | — | 缺 ⟹ `false`（保守） | C6 §3 |
| `event_context.sync.uncertainty_ms` | 对齐不确定度；缺失取 5 ms（C6 §3 规则 3） | — | — | — | C6 |
| `event_context.causal_claims_permitted` | `sync.verified == true` **且** `alignment_residual_ms ≤ τ_u`（C2 规则 8 定义的唯一开关；方向见纪律 6 / **A-82**，不是旧文写的"存在 `abs(Δt) > τ_u` 的匹配对"） | — | — | 任何依赖为 null ⟹ `false` | C2 规则 8 |
| `event_context.step_labels[].t0/.t1/.step/.recipe` | 由 `source ∈ {process, motion}` 事件切分，与 `meta.machine_context.step_sequence`/`recipe` 对齐 | 事件 + C6 `machine_context` | 任意 | 无工艺事件 ⟹ 数组空（R-22/R-23 依赖 ⟹ 放弃） | C6 §2 |

### 1.13 `segment_coverage.*` 与 `unavailable[]`

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `segment_coverage.rest/.move/.settling/.dwell/.probing/.path/.homing/.scanning/.curing` | 该 `kind` 的分段**计数**；9 个键必须全部存在，无则为整数 0 | `meta.segments` | — | `segments` 缺失 ⟹ 全 0 并触发 C1 红线（无 `move/settling/probing` 段 ⟹ 拒诊断） | C1 §segments 词表 |
| `unavailable[].feature` | 无法计算的特征路径（与 §1 各表"算不出的条件"一一对应） | — | — | — | C2 规则 2 |
| `unavailable[].reason` | 人读原因（缺通道 / 缺定标 / 无反向段 / 频带不足 / 段缺失） | — | — | — | C2 规则 2 |

### 1.13b `quality_ref.*` 与 `sensor_disagreement.*`（A-10 / A-6 已落 C2；A-49 补齐 `quality_ref` 全值域）

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `quality_ref.quantization_step_counts` | 位置反馈相邻可读值的最小间隔（counts），由 C1 `quality.quantization_step_counts` 透传进 C2（裁决 A-10/G-4：量化台阶是证据，不能只写在叙述里）；C2 示例 `1.0`。**（A-97 更正）**"（counts）"是后缀历史名：`units_are = si_native` 的样本上它就是**该通道原生刻度的最小可读间隔**（本例量级是 m），不得当 1 个编码器脉冲用。规则层凡以"几倍量化台阶"表达的门限（R-07/R-08/R-17、§1.1 `δ`、§1.8 `20·量化步长`）都属 **`【比值·刻度无关】`**——两侧同刻度相消 ⟹ 无 `counts_per_mm` 也照算 | `pos_fb`（读自 C1 质量元数据） | 任意 | 单值/无重复读数 ⟹ null | C1 `quality`；C2 `quality_ref` |
| `quality_ref.motor_rev_counts` | 电机轴每转 counts（`CPR` 的 C2 侧镜像，供阶次类判据引用），C2 示例 `524288`。**本字段是 counts/rev 常数**，与位置通道的原生刻度之间**需要一个换算**才连得起来 ⟹ `si_native` + `counts_per_mm == null` 时阶次族能否成立**已裁 A-110 ①**（不得把 524288 当 counts/mm 用；无 counts 刻度 ⟹ 阶次族不可评估） | `meta.axis.motor_rev_counts` | 任意 | `meta.axis.motor_rev_counts == null` ⟹ null | C1 / C2 `quality_ref` |
| `sensor_disagreement.pairs[].a` / `.b` | 参与比对的两路**独立位置反馈**通道名。**A-98 ① 已放开值域**：canonical 与 extra 通道都可入对（Export10 一条 `pos_fb` 都没有，三套独立位置测量全在 `extra_channels`），配对来源仍只有 C1 `cross_validation.pairs`；C2 侧必填 `a_role/b_role ∈ {canonical, extra}`（C2 规则 17）。**A-105 ②③ 再加一道资格线**：入对的列必须是**过了 C1 恒等式核对**的列（C1 派生规则 9 / C2 规则 18）——派生列与逐行全等孪生中被丢弃的那一侧都不是第二次测量；计数口径与 A-98 ③ 同一个（全等两列只算一路）。门控后 5000 行切片实测：位置列见 8 条，扣掉其中 1 条派生列（`dPosition_diff`）与 2 条 `_tar` 全等孪生 ⟹ **独立位置测量 5 条**（`dPosition_asco_enc`/`dPosition_asco`/`dPosition_load`/`dPosition_test`/`dPosition_lsv_enc`；全表口径是 `n_derived = 2`、`n_duplicate_groups = 3`，多出的那两条属速度族）；母本全量 18,651 行的两条恒等式残差（3.55e-15 / 4.44e-16）是同一结论的母本证据，两套口径不得混写 | 任意两路**已过核对的**已登记通道 | 任意 | 无可互证对 ⟹ 数组空；接入层未做核对（`feedback_integrity.identity_check.performed == false`）⟹ 整组 `not_evaluable` + `blocked_by = derived_column_unchecked`，固定句式「接入层未做列间恒等式核对，独立测量数不可信（A-105 ④）」 | C1 `cross_validation` / 派生规则 9；A-6；**A-98 ①**；**A-105 ②③④** |
| `sensor_disagreement.pairs[].unit` | 该对幅值字段的真实单位（A-97 ③：`*_counts` 后缀是历史名，单位由 C1 决定，值域取 C1 单位词表；本样本 `m`）。**必填**，缺键 ⟹ `check_self_consistency` 失败 | 元数据 | 任意 | — | **A-97 ③**；C2 规则 17 |
| `sensor_disagreement.pairs[].datum_offset` | 被 `rms/max` 减掉的常偏 `mean(a−b)`（**A-106 ②**：字段名不带单位后缀，数值随 `unit`）。原点差是安装/标定证据（KB6 寻光标定族要用），减了必须记；**必填**，缺失 ⟹ 该对幅值整组 `null` + `blocked_by = absent_datum_alignment`，固定句式「未做原点对齐，分歧幅值不可比」 | 同上 | 任意 | 接入层未登记常偏 ⟹ 幅值 `null` | **A-106**；C2 规则 16/17 |
| `sensor_disagreement.pairs[].corr` | 两路的 Pearson 相关，**在原始值上算**（A-106 ③：平移与定标不改变相关系数，无须去偏）。刻度无关 ⟹ 无 `counts_per_mm` 时照算 | 同上 | 任意 | 任一路方差为 0 ⟹ `null`（本样本 `pos_cmd ≡ pos_fb` 就是该支，见 A-104 ⑤） | **A-106 ③**；A-104 |
| `sensor_disagreement.pairs[].dominant_order_per_rev` | 两路分歧的主阶次（每转周期数，语义同 §1.4，A-11 阶次命名）。**阶次无量纲 ⟹ `【比值·刻度无关】`**；其"每转"成立条件同 §1.4 `CPR` 复判项。**实现现状**：引擎侧恒 `null` 并登记缺席（阶次谱需要 `CPR` 与整转数据，Export10 两者皆无） | 同上 | `probing`/恒速 `move` | 无整转 ⟹ null | A-6/A-11 |
| `sensor_disagreement.pairs[].rms_counts` / `.max_counts` | 两路反馈逐点差的去均值 RMS / 峰值（counts），**分歧本身是证据不是噪声**。**（A-97 更正 + 标注）**后缀是历史名、真实单位随行（C2 已给 `pairs[].unit` 必填）：裸幅值 `rms/max` 属 **`【绝对】`**（带位置量纲的实测幅值，凡将来给它挂字面 counts 常数都要 `blocked_by = absent_counts_scale`），而它的**比值/相关写法**——`rms/max` 之比、`corr`、`dominant_order_per_rev`、`ripple_over_velocity_pct_per_rev`——属 **`【比值·刻度无关】`**，照算、不得被绝对侧连坐。本文件现有引用全部是定性形态（畸大/比例 1000:1/固定偏置），**未挂任何字面 counts 阈值**。**入对资格先于幅值**（A-105 ②③，口径见上面 `.a`/`.b` 行）：派生列（如 `dPosition_diff ≡ -(dPosition_test + dPosition_load)`）与全等孪生的丢弃侧都不算第二路，拿它们配出来的"分歧"是零信息；接入层未做核对时这两个幅值 `null` + `blocked_by = derived_column_unchecked`，固定句式「接入层未做列间恒等式核对，独立测量数不可信（A-105 ④）」 | 同上 | 任意 | 任一路缺失 ⟹ null | A-6/G-7；A-97；**A-105**；KB7 三传感器交叉验证 |
| `sensor_disagreement.pairs[].direction` | 分歧方向标记（如 `b_a`），用于区分"哪一路偏高" | 同上 | 任意 | — | A-6 |

**`quality_ref` 的其余四行（A-49 新增：`quality_ref` 是 C1 `meta.quality` 的镜像，
证据路径一律走 C2，`source` 字段就是这条镜像关系的自述）（已裁 A-49）**：

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `quality_ref.dt_jitter_ratio` | 采样时基抖动比（`std(dt)/mean(dt)`，C1 `meta.quality` 定义原样镜像）；> 0.2 时噪声底升高、不可归因于运动（C1 红线）；> 0.05 时二阶差分/丢周期类判据放弃（R-15/R-20） | 时间轴 | 任意 | `sample_interval` 不可得 ⟹ null | C1 `meta.quality`；C2 `quality_ref`；A-49 |
| `quality_ref.nan_ratio` | 全通道 NaN 占比（C1 镜像）；C2 例 B 为 `0.004` | 全通道 | 任意 | — | C1；A-49 |
| `quality_ref.gap_max_s` | 时间轴最大连续断档秒数（C1 镜像）；决定 `segment_coverage` 可信度与 R-19/R-24 的段边界 | 时间轴 | 任意 | 无断档时为最短值（例 A `0.00025` = 一个采样周期） | C1；A-49 |
| `quality_ref.source` | 镜像来源自述字符串（形如"C1 meta.quality（镜像进 C2，规则证据只能走 C2 路径，A-10）"）；**标识字段，不进证据** | — | — | — | C2 `quality_ref`；A-49/A-10 |

**阈值刻度标注约定（A-97 ④ 在本文件的落地；本节是该约定的唯一登记处，§0 纪律 4 只留指针）**

> **前提（真实样本实测，非假设）**：`data/raw/Export10_244531.csv` 的 `meta.units_are = si_native`
> 且 `counts_per_mm = null` ⟹ 该样本**根本没有 counts 刻度**；按 A-97 ①，`*_counts` 后缀是**历史名**，
> 字面含义 = 该通道**原生刻度**下的数值，真实单位由 `meta.units_are` 唯一决定。

1. **标注要求**：本文件凡以 counts（含 `counts/s`、`counts/min`、`counts/rev`，以及由 `*_counts` 路径承载的
   位置幅值）表述的阈值，必须在其判据行**显式标注** `【绝对】` 或 `【比值·刻度无关】`，并各带一句判定理由；
   **未标注的一律按 `【绝对】` 处理**（保守侧，A-97 ④）。标注范围 = 比较量落在位置/角度量纲上的全部判据
   （`fe_*`、`reversal_error`、`backlash_estimate`、`ripple_*`、`settle_band`、`quantization_step`、
   `thermal_drift`、`sensor_disagreement.pairs[].rms/max`、`*_counts_s` 速度幅值）；
   转矩侧百分比/带宽类阈值不在此列（归纪律 13 / A-70 管）。
2. **两类怎么分**：
   - `【绝对】` ⟹ 阈值一侧是**字面 counts 常数**，其量纲就是 counts（例：`settle_band` 默认的 `20 counts`、
     `v_ls` 的 `50 counts/s`、R-01/R-16 的 `2.0 counts/min`）⟹ 比较量与常数**不在同一刻度下就无法比**。
   - `【比值·刻度无关】` ⟹ 分子分母同为**同一原生刻度**下的实测量，换刻度时同乘同除 ⟹ 量纲相消
     （比值 / 百分比 / 变异系数 / Pearson 相关 / 相干 / 阶次 / "几倍量化台阶"）。
3. **为什么要标注**（A-97 ② 的理由，本文件按自己口径复述）：在 `units_are = si_native` 且
   `counts_per_mm = null` 的样本上，把 m 当 counts 去套字面常数是一次**静默的量纲替换**——它不报错、
   不留 `unavailable` 痕迹，只是把整条结论挪走一个量级；**这比记 `null` 危险一个量级**。
   标注的意义是把"这条判据依不依赖刻度"写死在规则文本里，让引擎按支路处置，而不是靠实现侧猜。
4. **处置（稳定键与固定 reason 句式）**：
   - `【绝对】` 支在 `counts_per_mm == null` 时**不可比** ⟹ 该支 `unavailable`，
     `blocked_by = absent_counts_scale`（词表在 C3 规则 16），
     reason **固定句式**：「无 counts 刻度，绝对阈值不可比」；
   - `【比值·刻度无关】` 支**照算**，且**不得被同一条规则里的绝对支连坐**（A-97 ③）；
   - 一条规则既有绝对支又有比值支时，`blocked_rules` 只写**支路粒度**（`R-08#绝对支_报告口径` 一类，
     粒度写法依 C2 规则 7 / A-79），**绝对支缺席不作废整条规则**（R-02 / R-08 已按此在规则文本里分支）；
   - 绝对支作为**排除项**（反证叶）使用时，不可比**不等于**该排除项成立 ⟹ 缺席 ≠ 通过（纪律 1），
     该反证记 `not_evaluable` 而不是放行归因。
5. **报告层**（A-97 ③，与纪律 4 的更正是同一件事）：`*_counts` 数值**禁止裸印**，单位必须随行
   （`sensor_disagreement.pairs[].unit` 必填，值域取 C1 单位词表）。

**绝对支索引（引擎按此挂 `absent_counts_scale`；本表逐行都在原文判据处有同名标记，可 grep）**

| 位置 | 阈值原文（摘录） | 标注 | 判定理由（一句） |
|---|---|---|---|
| §1.5 `crawling.low_speed_segments[].vel_mean_counts_s` | `v_ls := max(50 counts/s, 0.01·vel_cmd_max)` | 双支：`【绝对】`(50 counts/s) + `【比值·刻度无关】`(0.01·vel_cmd_max) | 前者是字面 counts 常数，后者与被测量同刻度、量纲相消 ⟹ 无刻度时只走比值支 |
| §1.8 / §3.2 `step_response[].settle_band_counts` 默认 | `max(20 counts, 0.02·fe_rms)` | 双支：`【绝对】`(20 counts) + `【比值·刻度无关】`(0.02·fe_rms) | 同上；`counts_per_mm == null` ⟹ 默认带宽只剩 `0.02·fe_rms` 一支可用（或改由工艺容差直接给原生刻度值） |
| R-01 判据① | `abs(global.thermal_drift_counts_per_min) ≥ 2.0 [P]` | `【绝对】` | 常数 `2.0` 的量纲就是 counts/min，无刻度即没有可比对象 |
| R-16 判据⑤（排除 R-01） | `abs(global.thermal_drift_counts_per_min) < 2.0 [P]` | `【绝对】` | 与 R-01 同一个常数 ⟹ 不可比时该排除项**不得**当作"位置侧漂移不显著"放行 |
| R-14 排除项（↔ R-17） | 「量化极限环幅值 ≈ 1–2 counts」 | `【绝对】` | 字面 counts 幅值描述；刻度无关侧的对应表述是 R-17 的 `limit_cycle_amplitude ≤ 3·量化台阶`，两者不得互推 |
| R-08 建议动作② | 补偿值取 `backlash_estimate_counts / 2 [L]` | `【绝对】`（动作量，非判据阈值） | 数值随实测刻度：有 counts 刻度给 counts，si_native 给原生刻度并随行单位；它**不**导致该叶降级 |
| R-02 判据（全部叶） | `reversal_error_counts ≥ 3·fe_rms_counts`、`fe_p999/fe_rms ≥ 4` 等 | `【比值·刻度无关】` | 本条判据**没有**字面 counts 常数叶；绝对侧只剩报告层的反向误差幅值读数（须随行单位），不构成 blocked 支 |
| R-22 签名表② 末列 | 核 `*_counts` 与 `*_mm` 比值是否 = `position_quantum_mm`（1000× 核对） | `【绝对】`（上机核对动作，非引擎判据） | 该核对式两支都经 `counts_per_mm`（纪律 4(a)：无刻度时 `*_mm` 恒 null）⟹ 无刻度时此格只能标"待外部确认" |
| R-24 判据⑤ / 建议动作③ | 额外位移贡献 `≈ T_poll × vel` | `【比值·刻度无关】`（口径已按 A-97 更正） | 该项要与 `settle_band` 同刻度互比才成为判据；旧口径"以 counts 表达"在 si_native 样本上没有落点 |

**待人工复判清单（本清单名保留只为让既有引用不悬空；五条已于 2026-10-21 由 A-110 全部裁完，不得再读作悬案。判不了的不猜，登记后等主线程裁决；本清单不构成判据）**

> **2026-10-21 主线程裁决 A-110**：本表五条全部落判。判据只有一条尺子——**这一改要不要新造一个数字**：
> 不要 ⟹ 本文件当场裁（①④⑤）；要 ⟹ 那是 C2 契约层的字段语义/换算问题，裁方向、落点另立任务（②③，任务 #39
> ——**#39 已由 A-113 于 2026-10-21 落码，故 ②③ 两行的"落地前维持现状"条件已解除**，见各行的生效注）。
> 裁完的本表**保留原文摘录**（它是 A-97 的边界证据），但状态从"待复判"改为"已裁"，不得再被读成悬案。

| 位置 | 原文摘录 | 为什么判不了 ⟹ 裁决 |
|---|---|---|
| §1.4 `dominant_order_per_rev` / `ripple_over_velocity_pct_per_rev`、§1.7 `encoder.per_rev_*`、R-07 判据④与必要上下文 | 「以"每转角度 `θ = pos_fb mod CPR`"为自变量对 `r` 做阶次谱」「`CPR == null` ⟹ null（"每转"无定义）」 | 阶次/比值写法本身量纲相消（该归比值支），但**特征的 folding 基**是 `CPR = meta.axis.motor_rev_counts`，量纲是 counts/rev；`units_are = si_native` + `counts_per_mm = null` 时位置通道（m）与"转"之间没有换算 ⟹ "每转"无定义。A-97 只裁了"counts 阈值"，未裁"counts/rev 常数与原生刻度位置通道如何配对"，也不得自造第二个 `blocked_by` 键 ⟹ **已裁 A-110 ①：不新增键、不自造换算。** `counts/rev` 常数的落点前提就是"该通道有 counts 刻度"，`units_are = si_native` + `counts_per_mm == null` ⟹ 前提不成立，**归 `absent_counts_scale`**（词表既有键，语义正是"无 counts 刻度"）。固定句式登记：「无 counts 刻度，`counts/rev` 常数与原生刻度位置通道无法配对，阶次族不可评估」。**禁止**实现侧自造配对常数（例如把 `motor_rev_counts = 524288` 当 counts/mm 用）——那是凭空引入一个换算系数，比判 null 危险；阶次族一律 `differential.not_evaluable`，不得写成"未发现每转周期误差"（纪律 1）。|
| §0 纪律 4(a)、§1.1 `global.fe_rms_mm`、R-22 签名表② | 「`meta.counts_per_mm == null` 时：(a) 所有 `*_mm` 特征为 null」 | 绝对支若改用 **SI 字面常数**（`units_are = si_native` 时 m 本身就是已知刻度）是否合法，A-97 没有裁；它只裁了"绝对 counts 阈值不可比 ⟹ unavailable"。本文件现按 unavailable 一律处理，**不**擅自把 `20 counts` 之类改写成 m 级常数（那需要一个新的数字） ⟹ **已裁 A-110 ②：把"特征"和"阈值"分开裁，尺子是要不要新造数字。** ① **阈值侧维持缺席**：`20 counts`、`50 counts/s`、`2.0 counts/min` 换成 m/m·s⁻¹ 级常数，等于替本项目决定"这机台的物理容差是多少"⟹ 那是造数，本文件不裁、引擎不得自行换算，绝对支照旧 `absent_counts_scale`。② **特征侧允许直接由原生刻度填**：`fe_rms_mm = fe_rms_(m) × 1000` 是纯定标（不引入任何新物理常数、不引入新数字），`units_are = si_native` 且 C1 单位词表把该通道登记为长度时**应当**填，而不是留 null——留 null 丢掉的是真实信息。落点是 C2 规则 3（字段定义式属契约层，本文件只裁方向）：**任务 #39**——C2 规则 3 增 si_native 支、`features.py` 按随行单位换算、并强制一行 `audit.assumptions`（锚 `meta.units_are`，句式「`*_mm` 由 C1 原生 SI 刻度直接定标，非 counts/counts_per_mm 路径」）。**在此之前本文件与引擎维持现状（`*_mm` 为 null），不得半途各写各的。** **（A-113 生效注，2026-10-21：该"在此之前"已结束——C2 规则 3 已增 si_native 支、`features.py::si_native_length_scale` 按随行单位 `×1000` 定标并强制一行 `meta.units_are` 假设；本节上方 §1.1 该行与 §0 纪律 4(a) 同步收窄。阈值侧一条未动：`20 counts`/`50 counts/s`/`2.0 counts/min` 仍走 `absent_counts_scale`，未折算成 m 级常数，本行 ① 的裁决原样成立。**）|
| §0 纪律 4(b)、§1.1 `global.fe_rms_mm`、R-23 建议动作（风险段）、R-24 判据⑤、R-29 必要上下文/判据末支 | 「规则的建议动作**禁止**给出 µm/µrad 数字，只能给 counts 或 counts/rev 量级」及"（`counts_per_mm == null` 时不得声称'仍在 ±X µm 内'）""`counts_per_mm == null` ⟹ 用 counts 判定""µm 级容差结论"各句 | 这些句子的共同前提是"没有 `counts_per_mm` 就没有 SI 量级信息"，A-97 ① 已否定该前提（`units_are = si_native` 时读数量纲已知）；但**是否允许**由此直接给出 µm 级动作数字/容差结论，取决于 C2 里 `*_mm` 特征的定义式（`fe_rms_counts / counts_per_mm`）能否改由原生刻度直接填——那是 C2 契约层的裁决，KB3 只能标注冲突、不能改字段语义，也不能自己引入换算系数 ⟹ **已裁 A-110 ③：把"实测幅值"与"容差/目标"分开裁，尺子同 ②。** **实测幅值**（本条样本的误差读数）随 ② 的特征侧放开：`units_are = si_native` 时它是直接读出来的量，#39 落定后报告可以给 µm 级幅值，必须随行单位并锚在 `meta.units_are`。**容差/目标数字**（"仍在 ±X µm 内""放宽到 Y µm"）本仓没有任何来源，只能引用外部工艺容差表（KB6 外部验收限同一条路径）⟹ **仍然禁止**，容差表缺失时该结论 `not_evaluable`，不得由实测幅值反推容差。据此**纪律 4(b) 的禁令范围收窄为「禁止给出 µm/µrad 级容差·目标数字」**，不是禁止一切 µm 数字；收窄只在 #39 落地后生效，在那之前 4(b) 照旧全文有效。 **（A-113 生效注，2026-10-21：#39 已落码 ⟹ 该收窄自此生效，纪律 4 现读作「禁 µm/µrad 级**容差·目标**数字」，实测幅值可给且须随行单位 + 锚 `meta.units_are`；容差表缺失仍 `not_evaluable`，仍不得由实测幅值反推容差。另登记一处编号笔误：本行与本表 ② 行沿用的"纪律 4(b)"实为 **4(c)**——(b) 管"报告印什么单位"，(c) 才管"建议动作给不给 µm 数字"，被收窄的是 (c)，(b) 的 A-97 更正口径不变。台账原文不改写，笔误在此钉正。）|
| R-22 签名表① | 「若有第二路反馈则 `sensor_disagreement.pairs[].rms_counts`（pos_fb vs laser_ref）**反而畸大**」 | 句中既无数字阈值也无比较对象，"畸大"是定性词 ⟹ 无法归入绝对/比值任一类；要标注需先给它一个阈值，而本文件禁止造数 ⟹ **已裁 A-110 ④：定性签名不编码**，见本表末的三条处置。|
| R-22 签名表⑥ | 「`sensor_disagreement.pairs[].rms_counts` **低**但存在**恒定 mean 偏置**」 | 同上：两个签名都是定性词（低 / 恒定），没有可比阈值 ⟹ 两类都套不上；给它"低到多少"或"偏置大于多少"都属造数，登记待复判 ⟹ **已裁 A-110 ⑤：同上，两条签名共三条定性词（`畸大`/`低`/`恒定 mean 偏置`）一律不编码。**|

**A-110 ④⑤ 的三条定性签名处置（裁完即为本文件的最终口径，不再是悬案）**：
`畸大`、`低`、`恒定 mean 偏置` **永不进 `rule_table.json`**——给它们任何阈值都是凭空造数，
而阈值一旦造出来就参与成立判定，等于用编造的数字做诊断结论。三条只保留在 R-22 签名表里作为
**人读的方向提示**，该表这两格的刻度标注已就地写明「定性、不可编码、不进 rule_table、不参与成立判定」；
实现侧**不得**为其新增特征字段或阈值。它们能出现的唯一位置是叙述层的"待人工核实方向"，
且不得写成结论；当 `feedback_integrity.second_feedback_available` 为 `false`/`null` 时按
A-105 ④ 整条 `not_evaluable`，此时连方向性叙述也不给（纪律 1：不可评不得写成"未发现"）。

### 1.13c `feedback_integrity.*`（A-48 新增：数据完整性筛查组，不是故障假设）

| 特征路径 | 定义/公式 | 输入通道 | 所需分段 kind | 算不出的条件 | 出处 |
|---|---|---|---|---|---|
| `feedback_integrity.corr_pos_fb_vs_pos_cmd` | `pos_fb` 与 `pos_cmd` 的去均值 Pearson 相关；`≥ 0.99` **且** `fe_zero_ratio ≥ 0.9` ⟹ `masquerade_suspected = true`（C2 规则 15 门限）。**`【比值·刻度无关】`**：相关系数对定标与平移/缩放不变（A-97 ③ 点名的一类），无 `counts_per_mm` 时照算。**A-98 ③ 的无 `pos_fb` 支**：`pos_cmd` 与某条反馈列**逐行全等**（行级差异数 = 0）⟹ 同判冒充，reason 固定句式「指令轨与候选反馈逐行全等，二者非独立测量」；该支不需要 `pos_fb` 命名成立，也**不引入任何刻度常数**。Export10 门控后 5000 行实测：`dPosition_test_tar`/`dPosition_load_tar`/`dVelocity_load_tar` 三对差异行数为 0，`dVelocity_test_tar` 为 5000（`src/axiscope/c1.py::_masquerade_check`） | `pos_fb`,`pos_cmd`（或 A-98 ③ 的同名孪生列对） | 任意（含 `move`） | 无 `pos_cmd` 且无孪生列 ⟹ null | C2 规则 15；A-46/A-48/**A-98** |
| `feedback_integrity.fe_zero_ratio` | `fe` 落在 ±量化台阶内的样本占比。**`【比值·刻度无关】`**：判定窗以**该通道自己的量化台阶**为半径（同刻度相消），不是字面 counts 常数 | `fe` | 任意 | 无 `fe` 且 `pos_cmd`/`pos_fb` 不全 ⟹ null | C2；A-48 |
| `feedback_integrity.pos_fb_static_on_move_ratio` | `move` 段内 `pos_fb` 完全不变（导数 ≈ 0）而 `pos_cmd` 在动的样本占比（死通道签名）。**`【比值·刻度无关】`**：占比无量纲，"完全不变"按逐行相等判，不引入刻度常数 | `pos_fb`,`pos_cmd` | `move` ≥ 1 | 无 `move` 段 ⟹ null | C2；A-46/A-48 |
| `feedback_integrity.identity_check` | C1 `meta.audit.identity_check` 摘要的**镜像**（`src/axiscope/c1.py::_identity_scan`，C1 派生规则 9 / **A-105 ①③④**，C2 规则 18）：`performed` / `n_numeric_columns` / `n_rows_checked` / `n_derived` / `n_duplicate_groups` / `n_constant_columns` / `n_independent_position` / `reason`；关系全文与逐列方向在接入侧车 `ingest.identity` 与 findings（`derived_column` / `duplicate_column` / `linear_dependency_unattributed` / `measurement_independence`），不进 C2。**它是计数类判据的前置资格证明，自身不作证据、不进 `supporting_evidence`**（同 `quality_ref.source` 的标识字段处置）。门控后 5000 行切片实测：`n_independent_position = 5`（位置列见 8 条，扣掉 `dPosition_diff` 这条派生列与 `dPosition_test_tar`/`dPosition_load_tar` 两条 `_tar` 孪生；全表另有 `n_derived = 2`、`n_duplicate_groups = 3`、`n_constant_columns = 2`——多出的那条派生列与那组孪生属速度族，两个常数列属力族）；母本全量 18,651 行实测的两条恒等式残差 3.55e-15 / 4.44e-16 是同一结论的母本证据 | 元数据（接入层核对结果） | — | 数值列 < 3 或有限值行 < 100 ⟹ `performed = false`、`n_independent_position = null`；摘要整块缺键（旧包）按 `performed = false` 处置 | C1 派生规则 9；C2 规则 18；**A-105** |
| `feedback_integrity.second_feedback_available` | 是否存在**第二路独立位置反馈**：**A-98 ② 已改判据**——`sensor_disagreement.pairs` 里存在 ≥1 对**分属不同物理原理**的通道才为 `true`；pairs 非空但两列同原理（或原理任一侧未登记）只说明这套传感器内部不稳，不算第二次独立测量。原理表来源 KB7 §硬件真值 + KB2 §3.5 通道卡（`src/axiscope/mapping.PRINCIPLE`），实现侧不再要求 `pos_fb` 存在。**A-105 ②③ 补的资格线在计数之前**：该对是否存在是在**过了恒等式核对的列**上数的（派生列、全等孪生的丢弃侧都不算一路；计数口径与 A-98 ③ 同一个）——门控后 5000 行切片实测的位置列计数是"见 8 条、扣 1 条派生列与 2 条 `_tar` 孪生 ⟹ **5 条独立**"，全表的 `n_derived = 2` / `n_duplicate_groups = 3` 还含速度族那两条 | 元数据 + `identity_check` | — | `cross_validation` 未知 ⟹ null（按 false 处理并记 assumption）；`identity_check.performed == false` 或该键整块缺席 ⟹ **null**（不得留乐观的 `true`），相关判据 `not_evaluable` + `blocked_by = derived_column_unchecked`，固定句式「接入层未做列间恒等式核对，独立测量数不可信（A-105 ④）」 | C1；A-48；**A-98 ②**；**A-105 ②③④** |
| `feedback_integrity.masquerade_suspected` | 上述两条门限的合取布尔（指令冒充反馈） | 同上 | — | 依赖 null ⟹ false 且登记 | C2 规则 15；A-48 |

**A-48 纪律（已裁，KB0 §7.2）**：本组是**数据完整性筛查**，`family: null` 级别，
**永不进 `hypotheses`**。`second_feedback_available == false` 时，"冒充"与"通道恒零/未接"
在单路数据上**不可区分** ⟹ **不得归因**，只按 A-51 键式登记 `differential.not_evaluable`
（逐模式 `{"fault_mode": <KB0 §2 slug>, "why": …}`；整族时另加族级 `{"family": …, "why": …}`）。
`second_feedback_available == true` 时才允许用 `sensor_disagreement.pairs[].*` 判"哪一路在说话"，
这也是 **KB4 CP-11 第 3 条判据**第一次有了真实路径（旧文写"在 C2 尚无路径"已作废）。
**但那个 `true` 只在恒等式核对跑成时有意义**（A-105 ②③④）：`feedback_integrity.identity_check.performed == false`
（或整块缺键）⟹ 本组所有以"两路独立测量分歧"为前提的判据（本纪律、R-22 签名①⑥、CP-11 第 3 条）
一律 `not_evaluable` + `blocked_by = derived_column_unchecked`，固定句式
「接入层未做列间恒等式核对，独立测量数不可信（A-105 ④）」。理由就是 A-105 的触发形态：
`dPosition_diff` 是 `dPosition_test` 与 `dPosition_load` 的线性函数，拿它配任一路都能"造出"一对
分歧，而它零独立信息——未核对的列数不是第二路反馈。

### 1.14 顶层标识字段

`schema`（`axiscope.features/1`）、`ref.sample_id`、`ref.sha256`（波形 + meta 内容哈希，满足 C5
"可追溯率 100%"）、`fs_hz`、`present_channels[]`：透传/标识字段，无公式。
一致性要求：`fs_hz == freq_limits.fs_hz`，且 `nyquist_hz == fs_hz/2`，
`reliable_band_hz == nyquist_hz/1.25`；不一致视为解析缺陷 ⟹ 拒诊断（C1 数据质量红线精神）。
`present_channels` 必须与 C1 `meta.present_channels` 一致，诊断覆盖度由它决定（C1）。

### 1.15 规则 ↔ 特征依赖倒排（KB0 §6 检查 1 的自查表）

| 规则 | 依赖的 C2 路径（全部已在本节登记） |
|---|---|
| R-01 | `global.thermal_drift_counts_per_min`, `global.thermal_fe_correlation_r`, `segment_coverage.dwell`, `segment_coverage.rest` |
| R-02 | `global.reversal_error_counts`, `global.fe_rms_counts`, `global.fe_p999_counts`, `ff_mismatch.asymmetry_ratio`, `spectral.fe.tonality_index`, `resonance.candidates[].amplitude_ratio_vs_broadband`, `event_context.fe_spike_count`, `segment_coverage.move` |
| R-03 | `freq_limits.reliable_band_hz`, `resonance.candidates[].*`（全部）, `step_response[].damping_ratio_estimate`, `segment_coverage.dwell/rest` |
| R-04 | `resonance.candidates[].is_double_inertia_pair/.antiresonance_freq_hz/.coherence_torque_velocity`, `spectral.cur_q.psd`（峰谷比）, `freq_limits.reliable_band_hz` |
| R-05 | `crawling.low_speed_segments[].*`, `encoder.per_rev_periodic_present` |
| R-06 | `global.friction_stiction_ratio`, `global.cur_q_rms_pct`, `segment_coverage.move`, `ff_mismatch.fe_vs_accel_corr`, `step_response[].overshoot_pct` |
| R-07 | `encoder.*`（全部）, `global.fe_rms_counts`, `ripple.probing[].dominant_order_per_rev` |
| R-08 | `global.backlash_estimate_counts`, `global.fe_rms_counts`, `segment_coverage.move`, `step_response[].settle_band_pct_of_move`, `global.reversal_error_counts` |
| R-09 | `resonance.candidates[].*`, `freq_limits.reliable_band_hz`, `spectral.cur_q.*` |
| R-10 | `resonance.candidates[].present_in_rest/.tracks_command_frequency/.freq_hz`, `spectral.fe.tonality_index`, `global.fe_sign_change_rate_hz`, `freq_limits.reliable_band_hz/.nyquist_hz`, `spectral.cur_q.harmonic_ratios` |
| R-11 | `spectral.cur_q.dominant_freq_hz/.tonality_index/.dominant_psd_ratio/.harmonic_ratios`, `resonance.candidates[].present_in_rest/.coherence_torque_velocity`, `ripple.probing[].correlated_with_cur_q` |
| R-12 | `ff_mismatch.fe_vs_accel_corr`, `ripple.probing[].correlated_with_cur_q`, `spectral.cur_q.tonality_index`, `global.cur_q_rms_pct` |
| R-13 | `bandwidth.position_loop_crossover_hz/.phase_margin_deg`, `step_response[].damping_ratio_estimate/.ringing_cycles_to_settle`, `resonance.candidates[].freq_hz` |
| R-14 | `step_response[].limit_cycle_present/.limit_cycle_freq_hz/.limit_cycle_amplitude_counts/.settle_band_counts`, `bandwidth.position_loop_crossover_hz/.phase_margin_deg`, `crawling.low_speed_segments[].*` |
| R-15 | `ff_mismatch.*`（全部）, `tracking.path_segments[].corr_fe_vs_accel/.corr_fe_vs_jerk`, `resonance.candidates[].present_in_rest/.present_in_dwell`, `global.friction_stiction_ratio`, `global.backlash_estimate_counts`, `step_response[].damping_ratio_estimate` |
| R-16 | `global.thermal_fe_correlation_r`, `global.cur_q_rms_pct`, `global.cur_q_saturation_ratio`, `step_response[].overshoot_pct` |
| R-17 | `global.fe_sign_change_rate_hz`, `spectral.fe.tonality_index`, `step_response[].limit_cycle_present/.limit_cycle_amplitude_counts/.settle_band_counts`, `encoder.per_rev_periodic_present` |
| R-18 | `event_context.available/.causal_claims_permitted/.fe_spike_count/.fe_spike_aligned_to_host_pause/.host_pause_max_ms/.alignment_residual_ms/.sync.uncertainty_ms/.n_by_source.host`, `resonance.candidates[].present_in_dwell`, `ff_mismatch.asymmetry_ratio` |
| R-19 | `event_context.interp_underrun_count/.interp_underrun_during_path/.fe_spike_aligned_to_underrun/.causal_claims_permitted`, `tracking.path_segments[].fe_max_counts/.fe_rms_counts/.corr_fe_vs_accel/.corr_fe_vs_jerk`, `segment_coverage.path` |
| R-20 | `event_context.network_cycle_miss_count/.n_alarm/.causal_claims_permitted/.bus_cycle_hold_max_ms/.fe_spike_aligned_to_network_miss/.alignment_residual_ms/.sync.verified/.sync.uncertainty_ms`, `quality_ref.dt_jitter_ratio`（A-49：C2 镜像路径） |
| R-21 | `event_context.vision_result_latency_p95_ms/.n_by_source.vision/.step_labels/.causal_claims_permitted`, `tracking.path_segments[].fe_max_counts/.fe_rms_counts` |
| R-22 | `event_context.step_labels/.available/.fe_spike_aligned_to_recipe_change`, `encoder.per_rev_periodic_present`, `global.backlash_estimate_counts`, `global.fe_rms_counts`, `global.fe_max_counts`, `global.fe_p999_counts`, `global.fe_rms_mm`, `quality_ref.quantization_step_counts`, `quality_ref.motor_rev_counts`, `position_quantum_mm`, `sensor_disagreement.pairs[].rms_counts/.max_counts/.direction`, `feedback_integrity.{corr_pos_fb_vs_pos_cmd,fe_zero_ratio,pos_fb_static_on_move_ratio,identity_check,second_feedback_available,masquerade_suspected}`（适配器口径缺陷签名表，A-33/A-46 + **A-48 已裁**：签名①的 `feedback_integrity` 路径已在 C2；**A-105**：签名①⑥ 的比较对象必须先过 `identity_check`，`performed == false` ⟹ 该两支 `not_evaluable` + `blocked_by = derived_column_unchecked`） |
| R-23 | `event_context.step_labels/.available`, `step_response[].settling_time_ms/.ringing_cycles_to_settle/.settle_band_counts`, `global.fe_p999_counts` |
| R-24 | `event_context.n_by_source.motion/.step_labels/.available`, `step_response[].settling_time_ms` |
| R-25 | `freq_limits.reliable_band_hz/.blocked_rules/.nyquist_hz`, `spectral.*.dominant_freq_hz` |
| R-26 | `resonance.candidates[].present_in_rest/.present_in_dwell/.coherence_torque_velocity`, `ff_mismatch.asymmetry_ratio/.fe_vs_accel_corr` |
| R-27 | `global.backlash_estimate_counts`, `global.fe_rms_counts`, `encoder.per_rev_periodic_present`, `event_context.step_labels` |
| R-28 | `event_context.fe_spike_aligned_to_host_pause/.fe_spike_aligned_to_underrun/.network_cycle_miss_count/.alignment_residual_ms/.causal_claims_permitted/.sync.method` |
| R-29 | `step_response[].settling_time_ms/.settle_band_pct_of_move`, `segment_coverage.settling`, `event_context.step_labels` |
| R-30 | `event_context.available`（及整族软件规则），`freq_limits.blocked_rules` |

---

## 2. 诊断规则库 R-01 … R-30

判据里 `AND`/`OR`/`NOT` 是布尔运算；每条规则的隐式前置条件是"其引用的所有特征非 null"（纪律 1）。
`[L]` = 文献可证阈值（第三部分逐条给出处），`[P]` = 本项目自定阈值（第三部分给初值与标定方法）。

### 2.1 频带下界汇总（决定 `freq_limits.blocked_rules` 的动态内容）

| 规则 | `band⊥`（`f_b` 下限） | fs=1 kHz（`f_b`=400 Hz，DaRUS）上可否评估 | 备注 |
|---|---|---|---|
| R-01 | n/a（时域） | 频带可，**但 T1-a 无正例来源**（A-64：本样本无 `temp`、无冷热机配对）⟹ 实际输出 `unavailable` | 需 `temp` + ≥20 min 跨度；禁止写"无热漂移"（A-65） |
| R-02 | 100 Hz | 可 | |
| **R-03** | **2000 Hz**（KB0 锁定） | **不可 ⟹ blocked**（`fs ≤ 1 kHz` 样本） | 需 `fs ≥ 8 kHz`；**已裁 A-64/A-65**：T1-a 无正例来源，只有 T2 正当性，产物只能是 `unavailable` + `blocked_rules`。★**已裁 A-94（收窄 A-65）**：频带门禁改按**样本自身 `fs`** 判，不按数据集名判。DarUS-2563/3003/3252 的 `.mat` 含 **4 kHz 测量栅格**（本会话实测 292,080 / 44,001 / 8,556 点，jitter ≤ 1.2e-6，严格单调），`f_b = 3.2 kHz ≥ 2000 Hz` ⟹ 这些样本上门禁**通过**，规则从"频带不可达"改判为"**通道门禁**"：`cur_q` 全库缺失 ⟹ 仍不给归因，落 `unavailable[]` 且 `reason = "band_gate_pass_channel_gate_fail"`，**禁止**写成"未发现共振" |
| **R-04** | **2000 Hz**（KB0 锁定） | **不可 ⟹ blocked**（`fs ≤ 1 kHz` 样本） | 反谐振峰也在带外；**已裁 A-64/A-65** 同上；顺序判据按 `sensor_config` **四值**（**已裁 A-68**）。★**A-94 同上**：4 kHz 样本上门禁通过，转为通道门禁（无 `cur_q` ⟹ 相干项与转矩相关判据不可算 ⟹ 不给归因） |
| R-05 | 20 Hz | 可 | DaRUS 摩擦战役为真值来源 |
| R-06 | 50 Hz | 可 | `cur_q_*_pct` 侧受 A-70 分母纪律约束 |
| R-07 | 20 Hz **且** 阶次 `k·f_rev ≤ f_b` | 部分可（低阶次可，高刻线插值误差不可） | 必须写 unavailable 而非"无编码器误差" |
| R-08 | 50 Hz | 可 | DaRUS 无反向间隙样本 ⟹ 该数据集上 skip |
| R-09 | 150 Hz | 可 | fs=1k 上唯一可评估的双惯性分支；顺序按 `sensor_config` 四值（A-68） |
| R-10 | n/a（含 `≥0.8·f_N` 分支） | 可（且**必须**运行） | 500 Hz 附近假峰的来源。**已裁 A-79**：C2 例 B 原先把 `R-10` 写进 `blocked_rules` 是缺陷（R-10 无 `band⊥`，且在低采样率数据上正是靠它抓假峰），示例已删该条；G-14 闭环 |
| R-11 | 150 Hz；kHz 分支 2000 Hz | 低频分支可，开关频率分支 blocked | **已裁 A-79**：C2 例 B 原先整条列 `R-11` 为 blocked 与"低频分支可"矛盾；现按支路粒度写 `R-11#switching_freq`，并在 `unavailable[]` 配一行同 `rule`/`branch`；G-14 闭环 |
| R-12 | 200 Hz | 勉强可（`drive.*` 常缺失 ⟹ unverified） | **已裁 A-64/A-65**：电流环行为在 400 Hz 带内不可观测，T1-a 无正例来源；饱和支路的百分比受 A-70 约束 |
| R-13 | 100 Hz | 可 | 受 H1 置信 0.6 限制 |
| R-14 | 100 Hz | 可 | |
| R-15 | n/a（时域，需 `fs ≥ 500 Hz`） | 可 | DaRUS `kff=1.5` 为标定样本 |
| R-16 | n/a（时域） | 频带可，**但 T1-a 无正例来源**（A-64，同 R-01）⟹ 实际 `unavailable` | **已裁 A-64/A-65 / A-70** |
| R-17 | n/a | 可 | |
| R-18…R-24 | 需 `fs ≥ 1 kHz` 且 `1/fs ≤ τ_u/2` | **DaRUS 无 `events.jsonl` ⟹ 整族 not_evaluable**（R-30） | |
| R-25 | 恒运行 | 是 | 本行的存在就是纪律 2 的执行。**已裁 A-79**：C2 例 B 原先把 `"R-25"` 列进 `blocked_rules`（门禁阻塞自己），该条已删；R-25 的落点是 C3 `audit.rules_fired`；G-14 闭环 |
| R-26 | 恒运行 | 是（但依赖 R-03/R-10 的可评估性） | |
| R-27 | n/a | 是（需 step_labels） | |
| R-28 | `fs ≥ 1 kHz` | 需事件流 | |
| R-29 | n/a | 需事件流 | |
| R-30 | 恒运行 | 是 | |

### 族一：`mechanical_*`（R-01 … R-10）

### R-01 热漂移：闭环保持位置随温度单调漂移
- family: `mechanical_thermal_drift`
- 断言: 存在与电机/结构温度同步、方向一致的慢漂移（保持位置或 `fe` 均值漂移），而非高频误差恶化。
- 判据: `abs(global.thermal_drift_counts_per_min) ≥ 2.0 [P]` **`【绝对】`**（§1.13b：`2.0` 的量纲就是 counts/min，
  `counts_per_mm == null` 时本叶 `unavailable` + `blocked_by = absent_counts_scale`，reason「无 counts 刻度，绝对阈值不可比」）
  `AND global.thermal_fe_correlation_r ≥ 0.6 [P]` **`【比值·刻度无关】`**（Pearson 相关，与刻度无关，不得被上一条连坐）
  `AND (segment_coverage.dwell + segment_coverage.rest) ≥ 2`
  `AND NOT (resonance.candidates[].freq_hz 出现在漂移起始之后且 amplitude_ratio_vs_broadband ≥ 6)`（漂移不是新谐振事件）
- 必要上下文: `temp` 通道；`dwell`/`rest` 累计 ≥ 120 s 且记录跨度 ≥ 20 min；
  强烈建议冷/热机各一组同轨迹样本；`meta.context.operator_notes`（C1 示例："冷机正常，运行 40 分钟后变差"）。
  `temp` 缺失 ⟹ `thermal_fe_correlation_r` 为 null ⟹ 本规则放弃，并登记
  `not_evaluable[{fault_mode:"mechanical_thermal_drift", why:"缺 temp 通道，且无冷热机对比"}]`
  （这正是 C3 示例 `differential.not_evaluable` 的那一条）。
- 排除项（易混淆）:
  - **R-16**（电机发热致 `k_t`/电阻漂移）：R-01 看位置侧慢漂，R-16 看电流侧需求上升。
    区分量：`thermal_fe_correlation_r` 高而 `cur_q_rms_pct` 温度斜率≈0 ⟹ R-01；反之 R-16。
  - **R-08**（间隙）：间隙每次反向重现、与温度无关；热漂是单向累积、与时间/温度相关。
  - **R-22**（换型覆盖脉冲当量）：后者是阶跃不连续且与 `recipe` 相关，不是单调斜坡。
- 建议动作: 顺序 (1) 排除工艺/定标问题（先跑 R-22 仲裁）；(2) 热机后重新归零/二次定标（操作规程级，可逆）；
  (3) 启用丝杠/螺距热补偿表（参数级，**离线**拟合 ⟹ `requires_offline: true`）；
  (4) 禁止用"提高位置环增益"掩盖漂移——增益提高会把同一漂移转成更大的保持误差（R-14 风险）。
  风险：补偿表拟合窗口不足会把真实工件位移当热漂补掉，造成系统性定位偏差（不可由参数恢复）。
- 期望效果与其依据: `unverified`（不给数字，只给方向：`thermal_drift_counts_per_min → 0`）。
- 出处: `T1-a` DaRUS `TempSlip` 战役（温度相关滑移，KB7 战役表）+ 数据集含温度测量（KB7 测量设备节）；
  `T2` ISO 230-3:1996 机床试验编码（摩擦/热相关效应）——**具体条款号需复核**。
  **A-64/A-65 能力声明（已裁）**：本条 `mechanical_thermal_drift` 在 **T1-a 上没有正例来源**——
  上面那条 `T1-a` 只是"数据集里存在该战役/该测量能力"，**不等于**本 agent 拿到的 T1-a 样本
  （DaRUS `Export 10.csv`）含 `temp` 通道或有冷/热机配对轨迹；本项目自有样本上判据依赖为 null。
  因此本条的**判据正当性只有 T2**，命中率的正面口径不得写进 `audit`/报告结论；
  样本无 `temp` 时报告侧是 `unavailable` + 逐模式登记 `not_evaluable`（见必要上下文），
  **禁止**写成"未发现热漂移 / 位置无漂移 / 未见异常"——缺通道 ≠ 无漂移。（已裁 A-64 / A-65）
- 适用边界: 时域低频判据，`fs ≥ 20 Hz` 即可；不适用于 <20 min 记录；
  不适用于直驱无丝杠轴（漂移主因不同，应以 `temp` + 光栅差分为准）。
  **A-64**：本条的期望效果保持 `unverified`，不得因 KB5 合成样本能造出热漂移而升为
  `simulation_validated`——合成支撑的只是"管线跑通"级主张，不是真实检出能力。

### R-02 结构松动：反向瞬态重复冲击 + 非周期尖峰
- family: `mechanical_loose_structure`
- 断言: 传动链/安装面存在松动，表现为每次方向反向都重复出现瞬态冲击尖峰，尖峰时刻与反向时刻强相关但幅值散布大。
- 判据（A-97 落地：**比值支与绝对支分列**，比值支不得被绝对侧连坐）:
  **比值支 `【比值·刻度无关】`**（`counts_per_mm == null` 的 si_native 样本上**照算**）：
  `global.reversal_error_counts ≥ 3·global.fe_rms_counts [P]`（两侧同为 `fe` 原生刻度量，量纲相消）
  `AND global.fe_p999_counts / global.fe_rms_counts ≥ 4 [P]`（尖峰型分布，非高斯；同刻度相消）
  `AND event_context.fe_spike_count / max(segment_coverage.move,1) ≥ 0.8 [P]`（事件数 / 段数，无量纲）
  `AND spectral.fe.tonality_index ≤ 0.5 [P]`（无稳定单峰 ⟹ 非谐振；谱平坦度无量纲）
  `AND (resonance.candidates 为空 OR max(resonance.candidates[].amplitude_ratio_vs_broadband) < 4)`（峰/本地中位比，无量纲）
  `AND ff_mismatch.asymmetry_ratio ≥ 1.8 [P]`（加减速不对称，但必须先过 R-26 仲裁；两支 RMS 之比、同刻度相消）
  **绝对侧 `【绝对】`（本条没有字面 counts 常数叶 ⟹ 无判据支需要降级）**：本条唯一的绝对量纲暴露是
  `reversal_error_counts` / `fe_p999_counts` 的**裸幅值读数**（带位置量纲）。它在 si_native 样本上按原生刻度
  填值并随行单位（A-97 ③，报告层禁止裸印 `*_counts`）；**不得**把该读数套进任何 counts 字面常数——
  若将来给本条补一条"反向误差 ≥ N counts"式叶，该叶须单独标 `【绝对】` 并走
  `blocked_by = absent_counts_scale`（§1.13b），届时**只降级该叶，其余六条比值叶照算**。
- 必要上下文: `segment_coverage.move ≥ 4` 且含正反两个方向；`pos_cmd`,`pos_fb`,`fe`；
  `event_context.fe_spike_count`（若 `available == false` 则该项跳过、只用其余条件并降置信至 ≤0.5）；
  `spectral.fe.tonality_index` 非 null。
- 排除项（易混淆）:
  - **R-08**（纯间隙）：间隙是幅值一致的**平台**（`backlash` 散布 CV ≤ 0.3），松动是幅值散布大
    （尖峰幅值 CV > 0.4）的**冲击**。用重复性区分。
  - **R-18**（上位机线程抖动）：抖动尖峰与反向时刻**不相关**，且需 `event_context` 对齐才可归因（纪律 5）。
  - **R-03**（谐振）：谐振有稳定谱峰（`tonality_index ≥ 0.6`），本规则要求 `≤ 0.5`。
- 建议动作: 归为"需机械检查"类，**不建议任何增益动作**（提高增益会放大冲击）。
  给出复检清单：联轴器顶丝、导轨滑块预压、丝杠螺母轴向间隙、负载锁紧面扭矩复紧（按设备手册扭矩值）。
  `requires_offline: true`（现场整改）；可逆性：**非参数级、不可由参数恢复** ⟹
  `requires_human_approval: true`，且报告须写明"本条无参数解"。
- 期望效果与其依据: `rule_heuristic`（方向：消除反向尖峰、`fe_p999/fe_rms` 比回落）。不给数字。
- 出处: `T1-b` CWRU 轴承故障数据（缺陷 ⟹ 冲击 + 非谐波边带，特征分类范式）；
  `T2` ISO 230-3:1996；`T2` Beckhoff 机械状态/耦合刚度检查类文档条目。
- 适用边界: `band⊥ = 100 Hz`；不适用于 `segment_coverage.move < 4`；
  不适用于只有 `fe` 无位置通道的样本（无法建立"反向"语境）；
  单方向往复（如 `scanning`）不适用。

### R-03 kHz 级机械谐振检出（双惯性/结构模态）  【KB0 §1 锁定：标题 / family / band⊥ = 2000 Hz】
- family: `mechanical_resonance`
- 断言: 在 1–6 kHz 存在被加减速瞬态激励的结构模态，能量集中于窄带、与转矩通道高度相干、静止使能时仍可持续、且与指令节律无关。
- 判据: **前置硬门禁** `freq_limits.reliable_band_hz ≥ 2000 [L]`；不满足则本规则**不得运行**（走 R-25，
  进 `blocked_rules`，禁止输出"未发现共振"）。满足时：
  `resonance.candidates[].freq_hz ∈ [1000, 6000] [L]`
  `AND resonance.candidates[].coherence_torque_velocity ≥ 0.7 [P]`
  `AND resonance.candidates[].amplitude_ratio_vs_broadband ≥ 4 [L]`（= 6 dB 峰/本地中位）
  `AND resonance.candidates[].present_in_dwell == true`
  `AND resonance.candidates[].present_in_rest == false`
  `AND resonance.candidates[].tracks_command_frequency == false`
  `AND resonance.candidates[].quality_factor_estimate ≥ 10 [P]`
  子证据 id（C3 示例已使用，保持兼容）：`R-03a` = 相干 ≥ 0.7；`R-03b` = `present_in_rest == false`；
  `R-03c` = `step_response[].damping_ratio_estimate`（反证支，见下）；`R-03d` = 相位裕度校验（需补 Bode）。
- 必要上下文: `cur_q`（C1 明文共振主通道）；`vel_fb` 或 `fe` 作相干参考；
  `segment_coverage.dwell ≥ 1` 且 `segment_coverage.rest ≥ 1`（任一缺失 ⟹ 对应布尔为 null ⟹
  本规则降级为 `unverified` 且置信上限 0.55，见 R-26 第 5 支）；
  `resonance.resolution_hz ≤ 5 Hz [P]`（否则 `quality_factor_estimate` 不可信）；`fs ≥ 8 kHz`；
  `meta.drive.notch_filters`（若已存在覆盖该频点的陷波，说明已被处理，须改为报告"陷波有效/不足"）。
- 排除项（易混淆）:
  - **R-10**（采样/混叠/陷波伪峰）与 **R-11**（转矩纹波）：用 `present_in_rest`（伪峰/电气峰在静止使能时仍在）
    与 `spectral.cur_q.harmonic_ratios`（纹波峰落在采样/开关频率的整数/半整数关系上）区分。
  - **R-15**（前馈失配）：C5 §6 认定的最高频混淆对，用 R-26 的有序仲裁链判定。
  - **R-14**（增益过高自激）：自激频率与 `f_pos` 相当且静止时也持续、幅值收敛于极限环；本规则频率远高于带宽。
  - 反证 `R-03c`：`step_response[].damping_ratio_estimate > 0.15` 说明阻尼不低、峰不算尖锐，
    削弱"严重共振"判断（C3 示例原文），必须写入 `contradicting_evidence`（C3 规则 2）。
- 建议动作: 二阶陷波。`center_hz = freq_hz`（取峰频，不取整）；
  `width_hz ∈ [f0/3, f0/2] [L]`（Panasonic FQ/FRQ 语义）；
  若驱动器用 Q 参数化（Yaskawa 转矩滤波器），**从 Q = 30 [P] 起**逐步放宽直到振动抑制，
  并在报告里显式写出所采用的定义 `Δf = f0/Q`，**禁止**把两种参数化的数值直接互比；
  `depth_db = −20 [P]`；`cascade_second_notch_at_2f = true` 仅当 R-04 判定为双惯性对。
  顺序（与 C3 `field_procedure` 同构）：①备份当前参数表；②只加第一陷波，做 3 次全行程定位，
  看峰是否下降 > 10 dB；③若出现新的第二峰抬升（反共振谷被激发）补第二陷波；
  ④每次改动后复测 `settling_time_ms`，超阈值则回退一档。
  风险：陷波削减该频段指令跟踪带宽并侵蚀相位裕度；若实为电气噪声而非结构模态，会使位置环变钝。
  `requires_offline: true`（须过 C4 门控：`plant_fit` 复现 + ±20% 敏感性扫描 + 新峰激发否决，C4 补充约束）。
  可逆性：参数级、可回读原值。**本项目不写入设备**（`safety.writes_to_device = false`）。
- 期望效果与其依据: `simulation_validated` **仅当** C4 `validation[]` 存在对应 V* 且
  `fit_residual_pct ≤ 25%`（C4 补充约束，否则必须降 `rule_heuristic`）；
  `rule_heuristic` 时只给方向：`fe_rms_counts` 与 `settling_time_ms` 下降，不给百分比。
- 出处: `T2` H. Butler, *Considerations in the Servo Drive Feedback Design for Machine Tools*
  （1987/2008 在线版；双惯性、陷波与带宽分离章节）——**章节页码需复核**；
  `T2` Beckhoff TwinCAT 机械谐振/振荡抑制与陷波器文档（TF5100 / TE5960 Scope 系列）；
  `T2` Yaskawa Σ-7《机械系统调整手册 / Mechanical System Tuning Manual》陷波条目（`Pn1101` 频率、`Pn1102` 深度）；
  `T2` Panasonic MINAS A5/A6 手册 `FP1`（陷波频率）/`FQ1`（衰减）/`FRQ1`（宽度）条目；
  `T1-b` CWRU / Paderborn CM（结构模态峰与工况相关的真值范式）。
  **A-64/A-65 出处能力声明**：`band⊥ = 2000 Hz`（kHz 量级）**在 T1-a 上没有正例来源**
  ——T1-a `fs = 1 kHz` ⟹ 奈奎斯特 500 Hz ⟹ `reliable_band_hz = 400 Hz`，
  本条的全部频率判据在数据层面不可达，**只有 T2 文献正当性**；
  在 T1-a 样本上报告侧必须写 `unavailable` 并把 `R-03` 登记进 `blocked_rules`，
  **禁止**输出"未发现谐振峰 / 未发现异常"（C2 例 B 已把 `R-03` 列入 `blocked_rules`，同一口径）。（已裁 A-64 / A-65）
- 适用边界: `band⊥ = 2000 Hz`（KB0 锁定）；`fs ≥ 8 kHz`；
  **不适用于 fs = 1 kHz 的 DaRUS 数据**（C3 文档头已声明该例的 1181 Hz 谐振在此数据上物理不可见）；
  不适用于无 `cur_q` 的样本（相干无从定义 ⟹ 放弃）；
  不适用于直驱无柔性环节（应走电气族）。
  **A-65**：数据面不可达时本条的产物只有 `unavailable` + `blocked_rules` 登记义务两种，
  "看不见"不得写成"没有"。

### R-04 谐振-反谐振配对判定（双惯性负载）  【KB0 §1 锁定：标题 / family / band⊥ = 2000 Hz】
- family: `mechanical_resonance`
- 断言: 观测到的峰与谷构成一对机械谐振-反谐振，证明电机侧惯量与负载侧惯量经柔性环节耦合（双惯性），单靠增益整定不可解。
- 判据: 前置 `freq_limits.reliable_band_hz ≥ 2000 [L]`（不满足 ⟹ R-25 阻塞，**不得**说"无双惯性特征"）。
  **顺序判据（采纳 KB5 §1.2 对 C2/C3 示例的实质修正，必须遵守）**：
  顺序期望由 **`meta.sensor_config ∈ {motor_side, load_side, mixed, unknown}`**（C1 派生规则 7，
  裁决 A-1 立三值、**A-68 增第四值 `mixed`**）决定：
  `sensor_config == "motor_side"`（共置：执行器与传感器同在电机侧）时，两惯量系统极点/零点交替
  （positive-real 性质）⟹ 反谐振频率 `f_a` **必然低于**谐振频率 `f_m`，此时
  `resonance.candidates[].antiresonance_freq_hz < resonance.candidates[].freq_hz` 是**强制必要条件**；
  `sensor_config == "load_side"`（负载侧反馈）时顺序相反，本必要条件按镜像处理；
  **`sensor_config == "unknown"`（不知道传感器装在哪一侧）与 `sensor_config == "mixed"`
  （已知本曲线的峰与谷来自两套通道、不是同一传递函数的输出）时，顺序项一律不参与判定**，
  只按幅值与相位条件评，且双惯性配对结论**置信度封顶**（顺序本身就是"哪个传感器在说话"的证据，
  不能拿来反推又不声明）。**两者的行为完全相同，差别只在记录的原因**（A-68）：
  `unknown` = 构型未知，无法确定该反馈来自电机侧还是负载侧；
  `mixed` = 构型已知且已知不成立 —— 峰/谷对不是同一条传递函数的零极点，
  因此**不承载任何零点-极点交替信息**，即便两侧各自顺序正确也不能拼成"配对"证据。
  逐通道落点：C1 `meta.channels.<pos_channel>.sensor_side ∈ {motor, load, unspecified}`（A-68），
  它是 `sensor_config` 的按通道登记面；`mixed` 应当能由两条 pos 通道的 `sensor_side` 取值直接解释，
  解释不了则回到 `unknown`。
  **KB5 早先把"混合构型临时写 `unknown` + `assumptions`"的处置已作废**（A-68）：
  混合构型必须写 `mixed`，原因记在 `sensor_config` 本身，不再借用 `assumptions` 补偿。
  `AND freq_hz / antiresonance_freq_hz ∈ [1.05, 2.7] [L]`
  （理论关系 `f_m/f_a = sqrt(1 + λ)`，`λ = J_l'/J_m` [L]，KB5 §1.2：`λ = 6.2`（C3 示例值）
  ⟹ `f_m/f_a = 2.683`；`λ = 0.01` ⟹ 1.005，与单惯量不可区分 ⟹ 本规则**必须不触发**）
  `AND (freq_hz − antiresonance_freq_hz) ≥ 2·resonance.resolution_hz [L]`（配对分离必须超过频率分辨）
  `AND resonance.candidates[].is_double_inertia_pair == true`
  `AND 峰/谷功率比 ≥ 6 dB [L]`（用 `spectral.cur_q.psd` 或 `abs(H1)`）
  `AND coherence_torque_velocity ≥ 0.7`
  `AND` 若 `meta.drive.notch_filters` 非空且覆盖 `antiresonance_freq_hz` ⟹ **谷是滤波造成的，不是反谐振** ⟹ 本规则否决
  `AND` 若 `meta.drive.inertia_ratio != null` ⟹ `inertia_ratio ≥ 5 [L]` 作为一致性佐证；
  `inertia_ratio == null` ⟹ 该支路降级 `unverified` 并写入 `next_data_to_collect`。
  **反向情形（`antiresonance_freq_hz > freq_hz`，如 C2/C3 示例的 1181 → 1420）在本模型下不可能由纯两惯量产生**，
  只能来自：(1) 非共置测量（电机编码器 + 负载光栅尺，两套通道分别估出的峰/谷被拼到一起）；
  (2) ≥3 惯量 / ≥2 柔顺分支；(3) 陷波/低通在闭环里造的人为谷；(4) 混叠伪峰。
  ⟹ 无 (1)/(2) 的构型证据（`meta.axis`/传感器构型未知）时，本规则**必须拒绝**判双惯量配对，
  转由 R-10（混叠/陷波伪谷）与 R-04 的否决支处理，并把该组合写入 `contradicting_evidence`。
  **`sensor_config == "mixed"` 时 (1) 已成立**（两套通道），反向情形不再需要额外证据即可归 (1)；
  `unknown` 时 (1) 只是候选解释，须写进 `contradicting_evidence` 并计入 `next_data_to_collect`
  （要求补两侧位置通道的 `sensor_side` 声明）。
- 必要上下文: `cur_q` + `vel_fb`/`fe` 的 `abs(H1)` 或 PSD 可辨峰谷；
  **传感器构型声明 `meta.sensor_config ∈ {motor_side, load_side, mixed, unknown}`**
  （C1 派生规则 7 / 裁决 A-1 + **A-68**）：
  `motor_side` ⟹ `f_anti < f_res` 强制；`load_side` ⟹ 镜像；
  `unknown`（不知在哪侧）与 `mixed`（已知峰/谷跨两套通道、非同一传递函数）⟹ **顺序项一律不判且置信封顶**，
  两者只在选择"记录哪条原因"时不同（A-68），此时 `f_a > f_m` 的解释权：`mixed` 归 (1)，`unknown` 归 (3)/(4)；
  逐通道落点为 C1 `meta.channels.<pos_channel>.sensor_side ∈ {motor, load, unspecified}`；
  `resonance.resolution_hz` 足够细（≤ 5 Hz）；`segment_coverage.move ≥ 2`；
  `meta.drive.notch_filters`（用于否决支，C1 示例为 `[]`，空数组 ≠ 未知，需区分）。
- 排除项（易混淆）:
  - **R-03**：只判"有结构模态峰"；R-04 判"峰谷成对 ⟹ 双惯性"（KB0 两条标题语义不同，不可互换）。
  - **R-09**：同一物理、不同频带（<400 Hz 传动链）。KB0 已把 R-04 锁在 2000 Hz，故低频双惯性**必须**用 R-09。
  - **陷波伪谷**：见判据第 5 条。
  - **R-13**（速度环失谐）：无峰谷配对、`tonality_index` 低。
- 建议动作: 顺序 ①在 `f_res` 加陷波；②在 `f_anti`（或 `2·f_c`）加第二陷波 [L]（双惯性需第二陷波）；
  ③若 `inertia_ratio > 10 [L]` 则判定"参数对策无效"，报告**机械整改**：提高联轴器/底座刚度、
  缩短悬臂、增大柔性环节刚度、减小负载惯量；④低带宽需求场景可改用 ZV 输入整形
  （`t = 0.5/f_d`、`K = exp(−ζπ/sqrt(1−ζ²))`、幅值 `1:K:1` [L]，见 §3.1），代价是响应延迟 `t_d` 且对
  `f_d` 漂移敏感。风险：把陷波放在反谐振处会失去相位支撑，可能引发自激（C4 稳定性校验必查）。
  `requires_offline: true`；可逆性：陷波参数级可回读，机械整改不可逆。
- 期望效果与其依据: `simulation_validated`（C4 `plant_fit.inertia_ratio_fitted`，KB5 双惯性内核）；
  无 V* 则 `rule_heuristic`（方向：峰谷比压缩、`settling_time_ms` 下降）。
  **A-64 降级**：本条 `simulation_validated` 只来自 **T3 合成数据**，而合成内核本身就是按双惯量模型造的，
  它**不能**充当"本管线能在真实数据上检出 kHz 级双惯性配对"的能力证据；
  因此该效果的对外措辞上限为**"管线跑通（合成自洽）"级**，不得写成"已验证可消除 kHz 谐振"。
- 出处: `T2` W. Leonhard, *Control of Electrical Drives*, 3rd ed., Springer, 1996（级联控制与双质量系统）；
  `T2` C. Kempf, W. Kobayashi, H. Tanaka, T. Yamada, "Resonance Control of a Dual-Mode Composite
  Structure", IEEE Control Systems Magazine 13(3), 1993；
  `T2` Panasonic MINAS A5/A6（双质量系统：在谐振频率设 `FP1`，反谐振处用第二陷波）；
  `T2` Yaskawa Σ-7（`Pn1101.1` 第二陷波/反谐振频率条目）——**子索引号需复核**。
  **A-64/A-65 出处能力声明**：`band⊥ = 2000 Hz` 属 kHz 量级，**在 T1-a 上没有正例来源**
  （T1-a `fs = 1 kHz` ⟹ 奈奎斯特 500 Hz ⟹ `reliable_band_hz = 400 Hz`，2000 Hz 判据在数据层面不可达），
  本条**只有 T2 文献正当性**；在 T1-a 样本上报告侧必须是 `unavailable` 并把 `R-04` 登记进 `blocked_rules`，
  **禁止**输出"未发现双惯性特征 / 未发现谐振 / 未发现异常"这类把"看不见"写成"没有"的结论。（已裁 A-64 / A-65）
- 适用边界: `band⊥ = 2000 Hz`；`fs ≥ 8 kHz`；不适用于直驱/无柔性环节；
  不适用于 PSD 分辨率不足（`Δf > f0/20`）的样本。
  **A-68**：`sensor_config` 为四值 `{motor_side, load_side, mixed, unknown}`，
  `mixed`（跨两套通道拼出的峰谷）与 `unknown` 一样**顺序项不参与判定、置信度封顶**，
  仅记录原因不同；`mixed` ⟹ `f_anti < f_res` 的强制关系**不适用**（C1 已同样声明）。

### R-05 低速爬行（粘滑极限环）  【语义受 C3 `audit.rules_skipped` 锚定】
- family: `mechanical_crawling`
- 断言: 恒低速指令下速度呈周期性锯齿并出现完全停止，其频率几乎不随速度变化，是摩擦负斜率段引起的粘滑极限环。
- 判据: `crawling.low_speed_segments` 非空（**入选窗 `v_ls` 有绝对支与比值支两支，见 §1.5 / §1.13b**：
  无 `counts_per_mm` 时只按 `0.01·vel_cmd_max` 一支入选，`50 counts/s` 一支记
  `blocked_by = absent_counts_scale`，本条不因此整条作废）
  **（主判别键，必须成立）** `is_sawtooth == true AND stall_count ≥ 1 [P] AND vel_min_ratio ≤ 0.15 [P]`
  ——三条均 **`【比值·刻度无关】`**（形态布尔 / 事件个数 / 速度自比 `min(vel_fb)/vel_mean`，无 counts 字面常数）
  `AND abs(corr_vel_vs_curq) ≥ 0.6 [P]`（C2 示例 0.79；Pearson 相关 ⟹ **`【比值·刻度无关】`**）
  `AND encoder.per_rev_periodic_present == false`（否则先判 R-07）
  **（频率只作辅证，已裁 A-95）** `AND sawtooth_freq_hz ∈ [0.1, min(50, f_b)] [P]`
  `AND` 跨不同 `vel_mean_counts_s` 的多段中，`sawtooth_freq_hz` 的变异系数 ≤ 0.3 [P]（频率近似常数 ⟹ 极限环固有；
  CV 是同一量的自比，**`【比值·刻度无关】`**，与各段速度幅值用什么刻度无关）
  - 上界窗的**优先口径**：`bandwidth.position_loop_crossover_hz != null` 时改用 `sawtooth_freq_hz ≤ 2.0·f_pos [P]`
    （A-95：频率归属交给相对窗；此时不再受绝对 50 Hz 约束）；
  - `position_loop_crossover_hz == null` 时**才**回退到 `[0.1, 50] Hz` 绝对窗，且该分支整体记 `unverified`、
    置信封顶 0.55（频率无从归属），C3 须写明"使用绝对回退窗"。

- 必要上下文: `vel_fb`（非差分派生；若派生需 `quantization_step_counts` 足够小，纪律 10）；
  `vel_cmd`；`cur_q`；`probing` 或恒低速 `move` 段 ≥ 1 且时长 ≥ 2 s；
  `meta.segments.kind` 正确（C1 词表）；**KB7 方向符号修正已完成**（纪律 9，否则锯齿判据失真）。
- 排除项（易混淆）:
  - **R-07**（编码器周期误差）：其频率**随速度线性变化**（`f = k·v/CPR`）且 `phase_locked_to_pos_modulo == true`；
    本规则频率近常数。**这是唯一可靠的区分量**。
  - **R-06**（stiction）：R-06 只判起步一次的突破转矩峰；本规则判运动中途**重复停走**。
  - **R-18**（线程抖动）：抖动锯齿无固定周期、需事件对齐才可归因。
  - **R-14**（自激极限环）：**已裁 A-95 —— 改用形状键分界，不用频率分界。**
    R-14 专属键 = 正弦型 + `present_in_rest/dwell == true` + 幅值 ≥ `0.5·settle_band`
    （**`【比值·刻度无关】`**，极限环幅值与判稳带宽同刻度相消）；
    本规则专属键 = 锯齿 + `stall_count ≥ 1`。两者互斥。
    绝对频率"本规则 < 2 Hz / R-14 > 20 Hz"**只保留为 `f_pos == null` 时的回退口径**；
    `f_pos` 已知时以相对窗为准（R-05 上界 `2.0·f_pos`，R-14 下界 `0.5·f_pos`）。
    落在 `2 Hz < f_lc < 20 Hz` 且两侧形状键**都不满足** ⟹ **两条规则都不触发**，
    登记 `audit.rules_skipped` + `verdict = insufficient_evidence`，禁止在灰区里硬套一条。

- 建议动作: 顺序 ①低速爬行抑制 / 摩擦补偿（LuGre 型或厂家"crawl suppression"参数，参数级、可逆）；
  ②提高速度环积分作用前先确认不会转成 R-14；③提高位置环采样率、减小量化（R-17 联动）；
  ④机械：导轨预压与润滑复检、检查密封件摩擦。风险：单纯提高增益会把爬行转为自激极限环。
  `requires_offline: true`。
- 期望效果与其依据: `rule_heuristic`（方向：`stall_count → 0`、`vel_min_ratio` 上升、`is_sawtooth → false`）。
  **不得**标 `simulation_validated`：DaRUS 有真实摩擦样本但**无本故障样本**（KB7：受试对象健康，
  不得声称"在真实产线故障样本上验证过"），除非 KB5 合成 + C4 V* 记录（那也只是 T3 流程验证）。
- 出处: `T1-a` DaRUS `2024-07-23_LdaFricIdent`（`tau_T` 7→60 N·m、`v_T≈0`）与
  `PreloadedLuGreFrictionIdent/Validation`（LuGre 真值）——KB7 明确列为 stiction/摩擦判据的真实样本；
  `T2` H. Olsson, K. J. Åström, C. Canudas de Wit, M. Gäfvert, P. Lischinsky,
  "Friction Models and Friction Compensation", IEEE Control Systems Magazine 18(3):65–79, 1998；
  `T2` B. Armstrong-Hélouy, P. Dupont, C. Canudas de Wit, "A survey of models, analysis tools and
  compensation methods for the control of machines with friction", Automatica 30(7):1083–1123, 1994。
- 适用边界: `band⊥ = 20 Hz`（`fs ≥ 100 Hz`）；DaRUS 的 fs = 1 kHz 上**可评估**；
  不适用于无速度反馈的样本；不适用于行程 < 3 个锯齿周期的段。

### R-06 静摩擦突破（stiction）与预载相关摩擦
- family: `mechanical_friction_stiction`
- 断言: 每次由静止起动都出现超出稳态摩擦所需的转矩尖峰，突破转矩/维持转矩比显著大于 1。
- 判据: `global.friction_stiction_ratio ≥ 1.5 [P]`（DaRUS `LdaFricIdent` 的 τ/τ_s 跨度支持 >2 量级，故 1.9 为可信区间）
  `AND segment_coverage.move ≥ 3`
  `AND` 起步后 `T_b` 窗内存在 `abs(cur_q)` 局部峰 ≥ `2·global.cur_q_rms_pct [P]`
  `AND ff_mismatch.fe_vs_accel_corr ≤ 0.5 [P]`（否则属前馈族）
  `AND global.cur_q_peak_abs_pct < 90 [L]`（未触及限流，否则应先判 R-12/限流饱和）
- 必要上下文: `cur_q`；含 ≥50 ms 静止前置的完整起步段；`meta.rated_current_a`；
  `meta.drive.notch_filters` / `meta.drive.torque_filter`（若起步峰被陷波衰减，本比值会**低估**，
  必须把该偏差方向写入报告）；`vel_fb` 或 `vel_cmd` 用以定义"尚未运动"。
- 排除项（易混淆）:
  - **R-08**：间隙峰出现在**反向**时刻，静摩擦峰出现在**由静止起动**时刻（时间顺序 + 段起始关系区分）。
  - **R-12**（电流环带宽不足）：后者在任意电流水平都滞后，不只起步瞬间。
  - **R-15**（前馈失配）：后者是加减速两段的 RMS 不对称（`asymmetry_ratio`），不是瞬时峰。
  - **R-11**（转矩纹波）：纹波峰在频域稳定存在，摩擦峰在时域起步窗内。
- 建议动作: 顺序 ①静摩擦/突破补偿（起动前馈表，参数级、可逆）；②提高速度环带宽（有 R-14 风险，
  必须先在 C4 仿真上验相位裕度 ≥ 45° [L]）；③若判定为**工艺性预载摩擦**（密封、预压导轨）
  ⟹ 报告必须写"设计特征而非故障"并**停止**给调参建议（对应 C5 `none_of_the_above` 案例设计，
  拒答正确率指标）。风险：把预载摩擦当故障补偿会在反向点造成过冲。
- 期望效果与其依据: `rule_heuristic`（方向：`friction_stiction_ratio → 1`，起步 `cur_q` 峰下降）。
- 出处: `T1-a` DaRUS `LdaFricIdent` + `PreloadedViscousFrictionIdent`（多预载 WC80…WC180，
  摩擦随预载的系统性变化）——KB7 战役表；`T1-a` `DynCapstanFrictionIdent`（动态卡普顿非线性摩擦）；
  `T2` Olsson 1998（stiction / 预滑动位移）；`T2` ISO 230-3:1996（摩擦效应试验编码）。
  **A-70 分母纪律（已裁）**：本条第 3、4 判据把 `abs(cur_q)`（单位 A）与 `global.cur_q_rms_pct`、
  `global.cur_q_peak_abs_pct`（单位 %）并列比较，**必须同一刻度**；百分比侧的分母为
  C1 `meta.drive.rated_torque_N_m` 且 `rated_torque_source ∈ {measured, manual, nameplate, assumed}`。
  `rated_torque_source == "assumed"` ⟹ 本条层级**封顶 T2**，caveats 必写
  "额定转矩为假定值，百分比类判据的绝对刻度不可信"（`cur_q_peak_abs_pct < 90` 这类门限的绝对刻度直接失义，
  须改走 `abs(cur_q)` 对 `rated_current_a` 的 A 侧判据）；
  `rated_torque_N_m == null` ⟹ `*_pct` 恒 `null` ⟹ 纪律 1：本条放弃并登记，只保留 `N_m`/A 绝对值支路。
- 适用边界: `band⊥ = 50 Hz`；需要 `cur_q`；不适用于无静止前置的连续路径段（`path`）；
  不适用于 `Torque_based` 与 `Velocity_based` 混合的样本（KB7：两种控制结构改变 `fe` 含义，须分组）；
  不适用 A/% 混算（A-70）。

### R-07 编码器一周一转周期误差  【语义受 C3 `ruled_out_alternatives` 锚定】
- family: `mechanical_encoder_periodic_error`
- 断言: 位置误差含锁定于电机轴/标尺旋转周期的周期分量（每转固定周期数），其时间频率与速度成正比。
- 判据: `encoder.per_rev_periodic_present == true`
  `AND encoder.per_rev_amplitude_counts ≥ 0.2·global.fe_rms_counts [P]`
  （**`【比值·刻度无关】`**：幅值与 `fe_rms` 同为位置原生刻度量，相消 ⟹ 无 `counts_per_mm` 也照算；
  但**特征本身**要不要 `CPR` 才能算出来，已裁 A-110 ①（无 counts 刻度 ⟹ 本特征 `not_evaluable`，不自造配对常数）
  （与 C3 示例的排除表述一致：原文以"`per_rev_amplitude` 仅占 `fe_rms` 的 23%"配合
  "未与每转周期锁定"来**排除** `encoder_eccentricity`，故本规则的门限必须落在 0.2 量级才自洽）
  `AND encoder.phase_locked_to_pos_modulo == true`
  `AND encoder.detrended_r2 ≥ 0.5 [P]`（C2 示例 0.62；解释度，无量纲）
  `AND` 主阶次 `k` 满足 `ripple.probing[].dominant_order_per_rev` 与 `CPR` 成整分数关系
  （A-11 已把该字段正名为阶次 `dominant_order_per_rev`，以阶次 `k` 判定，不做 counts 数值比较；
  **阶次 `k` 无量纲 ⟹ `【比值·刻度无关】`**，其"每转"成立条件同 §1.13b 复判项）
- 必要上下文: `meta.axis.motor_rev_counts`（null ⟹ "每转"无定义 ⟹ 放弃）；
  `meta.encoder_lines`（判断插值误差阶次是否可能越带）；≥2 整转的 `probing` 或恒速 `move`；
  `quality_ref.quantization_step_counts ≤ 0.25·encoder.per_rev_amplitude_counts [P]`
  （**`【比值·刻度无关】`**：台阶与幅值同刻度相消）；`fs ≥ 100 Hz`。
- 排除项（易混淆）:
  - **R-05**：见 R-05 的频率-速度关系判据（本规则 `f ∝ v`，爬行 `f ≈ const`）。
  - **R-08**：间隙只在反向出现、非周期。
  - **R-22**（换型覆盖脉冲当量）：后者是**比例偏差**（误差与行程成正比、无每转周期结构），
    仲裁见 R-27。
  - **R-11**：`ripple.probing[].correlated_with_cur_q ≥ 0.7` ⟹ 转矩扰动源（电气），不是编码器。
- 建议动作: 顺序 ①启用周期误差/插值误差补偿（Heidenhain 式谐波补偿表，阶数 `≤ 5 [P]`）；
  ②机械复检：刻线脏污、读数头气隙与安装挠曲、联轴器偏心与倾斜；
  ③全环/半环轴另查偏心与安装倾斜（`harmonics_per_rev` 判据）。
  `requires_offline: true`（补偿表拟合需离线）；可逆性：补偿表可清除。
  风险：补偿表只在拟合工况有效，外推到高速/反向会引入新误差；补偿幅值大于真实误差会形成反向死区
  （必须同时检查 `global.backlash_estimate_counts` 是否被"造"出来）。
- 期望效果与其依据: `rule_heuristic`（方向：`per_rev_amplitude_counts` 下降 ⟹ `fe_rms_counts` 下降）。
- 出处: `T2` J. Bao, S. Meng, C. Tsai, C. C. Lee, "Error analysis of digital servo systems with
  correction through computation", IEEE Trans. Ind. Electron. 40(2), 1993——**卷期/页码需复核**；
  `T2` Heidenhain 光栅插值误差补偿文献（P. H. Lehwehe）与 TNC 长度误差补偿（DRWA）文档；
  `T1-b` CWRU（阶次谱分析范式，非编码器真值）。
  声明限制：DaRUS **无编码器偏心样本**（KB7 "不能证明"清单），故本规则在 T1-a 上不可验证。
- 适用边界: `band⊥ = 20 Hz`，但物理要求 `k·f_rev ≤ f_b`。fs = 1 kHz（`f_b` = 400 Hz）时，
  `encoder_lines` 大 ⟹ 插值误差基频上百阶 ⟹ 在 `f_b` 之外 ⟹ **必须**登记
  `unavailable[{feature:"encoder.per_rev_periodic_present", reason:"插值误差阶次超出 reliable_band 400 Hz"}]`，
  而**不得**输出"未发现编码器周期误差"（纪律 2）。

### R-08 反向间隙 / 失动（lost motion）
- family: `mechanical_backlash`
- 断言: 方向反转时存在与行程无关的固定死区（平台），其值等于机械失动量，且每次反向重复。
  **（A-97 更正）** 原句写作"固定 **counts** 死区"：`counts` 在此是后缀历史名（A-97 ①），
  死区的宽度是**该通道原生刻度**下的位置量，si_native 样本上它就是 m 级宽度。
- 判据（A-97 落地：**比值支与绝对支分列**，绝对支缺席不作废本条）:
  **比值支 `【比值·刻度无关】`**（si_native + `counts_per_mm == null` 时**照算**，不得被绝对支连坐）：
  `global.backlash_estimate_counts ≥ 3·global.fe_rms_counts [P]`（两侧同为位置原生刻度量，量纲相消）
  （KB0 §3 给出的示例判据原文：`global.reversal_error_counts > 3*global.fe_rms_counts`；
  本规则同时要求两路证据满足 C3 规则 1 的"≥2 条 supporting_evidence"）
  `AND global.reversal_error_counts ≥ 3·global.fe_rms_counts`（同上，同刻度相消）
  `AND segment_coverage.move ≥ 2`（含反向；段数，无量纲）
  `AND` `backlash_estimate_counts` 的跨反向散布 `CV ≤ 0.3 [P]`（重复性：随工况变的是摩擦，不是间隙；CV 无量纲）
  `AND` 平台条件成立（§1.1 `backlash_estimate_counts` 定义中的 `abs(db_i/dt) < 0.1·vel_mean`，同刻度相消）
  `AND` 间隙估计**不得小于 3 个量化台阶**（§1.13b 必要上下文那条 `[P]` 门限，`3·量化台阶` 与被测量同刻度 ⟹ 相消）
  `AND NOT step_response[].settle_band_pct_of_move 异常`（间隙不改带宽，只偏置零位；`%` 与刻度无关）
  **绝对支 `【绝对】`（本条判据叶内**无**字面 counts 常数，绝对侧只落在下面两处）**：
  ①**建议动作②**的反向补偿值 `backlash_estimate_counts / 2` 是一个**带位置量纲的动作量**；
  ②**报告口径**（本条适用边界）。二者在 `counts_per_mm == null` 时的处置是"按原生刻度给值 + 单位随行"
  （A-97 ③），而**不是** `unavailable`；只有将来若在本条补一条"失动 ≥ N counts"式叶，该叶才需要
  `blocked_by = absent_counts_scale` + reason「无 counts 刻度，绝对阈值不可比」，并且**只降级该叶**
  （C2 规则 7 / A-79 的支路粒度，写法如 `R-08#绝对支_报告口径`）。
- 必要上下文: `pos_cmd` + `pos_fb`（只有 `fe` 时可算但会与摩擦/前馈混淆 ⟹ 降置信至 ≤0.5）；
  ≥2 对反向；`quality_ref.quantization_step_counts`（间隙估计不得小于 3 个量化台阶 [P]，**`【比值·刻度无关】`**：
  台阶取该通道原生刻度读数，与被测量同刻度）；
  `meta.counts_per_mm`（仅报告层，纪律 4；缺席时报告口径按 §1.13b 第 5 条走原生刻度 + 随行单位）；
  KB7 方向符号修正（纪律 9）。
- 排除项（易混淆）:
  - **R-02**：幅值一致（本规则）vs 幅值散布大 + 冲击（松动）；
    用 `fe_p999/fe_rms` 比与 CV 双重量区分。
  - **R-06**：间隙是**位置侧先出现平台**，摩擦是**电流侧先出现峰**（时序判据）。
  - **R-17**：量化误差与位置台阶相关，不随反向重复出现固定宽度。
  - **R-22**：见 R-27 仲裁（随 `recipe` 阶跃、与行程成正比 ⟹ 归软件侧标定）。
- 建议动作: 位置环增益**无法**补偿间隙。顺序 ①机械整改（螺母预压、消隙联轴器、导轨预压）——
  不可逆、需审批；②软件反向补偿：补偿值取 `backlash_estimate_counts / 2 [L]`（失动分半到两个方向），
  **该动作量属 `【绝对】`（带位置量纲，随实测刻度）**：有 `counts_per_mm` 时给 counts，
  si_native 且 `counts_per_mm == null` 时给**原生刻度数值 + 单位随行**（A-97 ③），两者都不是 µm 折算链，
  并在 T1/T2 数据上重标定（`[P]` 允许 0.5–2× 实测值范围内搜索）。
  风险：补偿过大在反向点形成三角波极限环 ⟹ 必须复测 `step_response[].limit_cycle_present`；
  补偿引入反向点位置跳变，对点胶/贴片落点精度不利（须给出"补偿开启后的 `fe_max` 变化"预估方向）。
  `requires_offline: true`。
- 期望效果与其依据: `rule_heuristic`（方向：`reversal_error_counts` 下降）。
  **不得**用 DaRUS 声明验证（无反向间隙样本）。
- 出处: `T2` ISO 10791 系列（单轴定位精度/失动试验）与 ISO 230-3:1996——**具体 part 号需复核**；
  `T2` Beckhoff/固高·雷赛类运动控制手册中"反向间隙补偿（backlash compensation）"参数条目；
  `T2` Heidenhain TNC 逆向间隙补偿（`reverse gap`）条目。
- 适用边界: `band⊥ = 50 Hz`；`segment_coverage.move ≥ 2` 且含反向；
  不适用于连续 `path` 段（无明确反向点）；`counts_per_mm == null` 时只报 counts，禁 µm。
  **（A-97 更正）**上一句的旧口径在 `units_are = si_native` 的样本上无处落地——那里既没有 counts 刻度，
  也不存在"只报 counts"这一说：正确处置是**按原生刻度印数值 + 单位随行**（`meta.units_are` 决定单位，
  A-97 ①/③），仍**禁止**臆造 µm 折算链；本条判据全是比值支 ⟹ 无刻度时**照算**，不因报告口径而 `unavailable`。
  **（A-113 生效注，2026-10-21）**上一句"臆造 µm 折算链"自此只剩**自造换算系数**这一种：C2 规则 3 支②给了
  唯一合法定义式（`*_mm = 该通道原生 SI 长度值 × 1000`，须随行单位并落一行 `meta.units_are` 假设），
  除该式以外的任何 counts↔mm 关系仍属臆造。本条不受影响（比值支，量纲相消）。

### R-09 低频传动链双惯性（皮带/绳/减速器；fs=1 kHz 上唯一可评估的双惯性分支）
- family: `mechanical_double_inertia`
- 断言: 在 <400 Hz 存在由柔性传动环节（绳、皮带、减速器、联轴器）构成的谐振-反谐振对。
- 判据: `f_b ≥ 150 [P]`
  `AND resonance.candidates[].freq_hz ∈ [150, f_b]`
  `AND resonance.candidates[].is_double_inertia_pair == true`
  `AND antiresonance_freq_hz < freq_hz [L]`（共置构型的顺序约束，同 R-04）
  `AND freq_hz / antiresonance_freq_hz ∈ [1.1, 2.0] [P]`
  `AND amplitude_ratio_vs_broadband ≥ 4 AND coherence_torque_velocity ≥ 0.7`
  `AND (meta.drive.inertia_ratio != null AND inertia_ratio ≥ 5 [L])`
  ⟹ `inertia_ratio == null` 时本条降级 `unverified`（纪律 3），仍可作为候选但不得进 `verdict.primary`。
- 必要上下文: `vel_fb`（或 `fe` 代理并标 `method="fe_proxy"`，置信 ×0.7）；`probing`/`move` 段；
  `CPR`；在 T1-a 上**必须已完成触发门控过滤**（纪律 8）与方向符号修正（纪律 9）；
  `resonance.resolution_hz ≤ f0/20`。
- 排除项（易混淆）:
  - **R-04**（KB0 锁定 kHz 语义，本规则不得复用于 kHz 峰）。
  - **R-13**（速度环 PI 失谐）：无峰谷配对 + `tonality_index` 低 + `phase_margin_deg < 45`。
  - **R-15**（前馈）：误差只在 |a| 大处、静止段无峰。
  - **R-05**（摩擦爬行）：<2 Hz 锯齿，且频率近常数；本规则峰在 150 Hz 以上。
- 建议动作: ①在 `f0` 加陷波（参数化同 R-03）；②`inertia_ratio` 高 ⟹ 机械整改（同 R-04 第 ③ 步）；
  ③低频段可用 ZV 整形替代陷波（`t_d = 0.5/f_d`，`K = exp(−ζπ/sqrt(1−ζ²))`，幅值 `1:K:1` [L]）。
  风险：低频陷波直接吃掉可用跟踪带宽，对贴装/点胶设备必须与节拍预算联评；
  ZV 整形使到位时间增加 `t_d`，且对 `f_d` 温漂敏感（`f_d` 变化 >5% 时抑制效果显著退化 [P]）。
  `requires_offline: true`。
- 期望效果与其依据: `simulation_validated`（C4 `plant_fit`：`inertia_ratio_fitted`/`resonance_hz`/`damping_fitted`）
  或 `rule_heuristic`。
- 出处: `T1-a` DaRUS 硬件真值：卷筒版 `gear ratio = 5.0`、`r_drum = 0.049 m` 与直驱版 `ratio = 1.0`
  的**同工况对照**（KB7 硬件真值节）；`T1-a` `CableRobotProfileFullIdent`（绳索路径语境）；
  `T2` Leonhard 1996；`T2` Kempf 1993；`T2` C3 文档头（"低频段 <400 Hz 在绳索/皮带/减速器传动轴上真实存在"）。
- 适用边界: `band⊥ = 150 Hz`；`fs ≥ 500 Hz`；不适用于直驱无柔性环节（走 R-04）。

### R-10 结构模态 vs 采样/混叠/陷波/量化伪峰判别（R-03 的证伪支）
- family: `mechanical_resonance`
- 断言: 若峰由采样/混叠、陷波或量化造成，则**不得**判为机械谐振；本规则只产证伪与降置信，不产调参动作。
- 判据（任一成立即判"伪峰"并阻断 R-03）:
  `resonance.candidates[].present_in_rest == true`（静止使能时仍在）
  `OR resonance.candidates[].tracks_command_frequency == true`（跟随指令节律）
  `OR resonance.candidates[].freq_hz ≥ 0.8·freq_limits.nyquist_hz [P]`（近奈奎斯特，混叠高度可疑）
  `OR (meta.drive.notch_filters 覆盖 freq_hz)`（已知陷波中心出现在峰位）
  `OR (global.fe_sign_change_rate_hz ≥ 0.4·fs [P] AND spectral.fe.tonality_index ≥ 0.6)`（量化/白噪声谱线）
- 必要上下文: `segment_coverage.rest ≥ 1`；`meta.drive.notch_filters`；
  `quality_ref.quantization_step_counts`；`segment_coverage.move ≥ 4`；
  `channels.vel_fb.derived`（派生 ⟹ 置信 ×0.7，纪律 10）。
  ★ 本规则若把 `sensor_disagreement.pairs[].rms_counts / .max_counts` 当"位置侧有没有响应"的旁证，
  这两个量按 **C2 规则 16 / A-106** 定义在 `resid = (a−b) − mean(a−b)` 上（**去常偏后**）——
  拿原始逐行差比较会把安装原点当响应（Export10 实测：某对常偏 180.106 m 而残差 RMS 0.0073 m，
  相差约 2.5e4 倍）；`datum_offset` 缺失时该对为 `null`（`blocked_by = absent_datum_alignment`），
  `null ≠ false`，不得当作"两路一致"。
- 排除项（易混淆）: 与 **R-11** 高度易混（都看 `cur_q` 峰）。区分：本规则的伪峰与 `vel_fb`
  相干性低、且与 `ripple.probing[].correlated_with_cur_q` 无位置侧响应；
  真电气纹波与 `cur_q` 强相关而与位置残差不相关。
  与 **R-17**：R-17 是"量化主导整个误差预算"，本规则是"量化造出一根谱线"。
- 建议动作: **无参数动作**。仅产生拒答/降置信：把该峰写入 `contradicting_evidence`（C3 规则 2），
  并把 R-03 置信压至 ≤0.55。若 `present_in_rest == null`（无 `rest` 段）⟹ 本规则放弃，
  且 R-03 置信上限 0.55（null ≠ false，纪律 1）——该情形必须写入 `next_data_to_collect`
  "补采静止使能 ≥1 s 段"（C3 规则 5）。
- 期望效果与其依据: `rule_heuristic`；对应 C5 指标"无依据成功声明 = 0"与"拒答正确率 ≥ 80%"。
- 出处: `T2` Oppenheim & Schafer, *Discrete-Time Signal Processing*（混叠、谱泄漏、窗效应）；
  `T1-a` KB7 §已实测 2（未处理触发列会造出假谱峰）与 §已实测 4/5（空行、预触发静止段易被误当数据）；
  `T2` C2 规则 7（fs=1 kHz 上报告 1.18 kHz 谐振是物理不可能）。
- 适用边界: 恒运行（`band⊥ = n/a`）；在 fs = 1 kHz 上"近奈奎斯特"分支阈值即 400 Hz，
  **必须运行**（DaRUS 上 400–500 Hz 的峰默认按伪峰对待）。

### 族二：`electrical_*`（R-11 … R-17）

### R-11 转矩纹波（cur_q 窄带峰与谐波阶次结构）  【语义受 C3 `audit.rules_fired` 锚定】
- family: `electrical_torque_ripple`
- 断言: `cur_q` 存在窄带峰及其整数/半整数阶次结构，来源是电流采样/开关/磁阻转矩脉动；
  位置侧未产生相应响应，说明它没有被结构模态放大。
  （C2 示例即此形态：`cur_q.dominant_freq_hz = 1182.0`、`tonality_index = 0.71`、
  `dominant_psd_ratio = 0.41`、`harmonic_ratios = [2.0, 3.0]`，而 `fe` 主峰仅 0.34/0.62。）
- 判据（低频分支，fs=1 kHz 可运行）:
  `spectral.cur_q.dominant_freq_hz ∈ [f_min, f_b]`
  `AND spectral.cur_q.tonality_index ≥ 0.6 [P]`
  `AND spectral.cur_q.dominant_psd_ratio ≥ 0.30 [P]`
  `AND spectral.cur_q.harmonic_ratios 全为整数或半整数（±5% 容差）[P]`
  `AND (resonance.candidates[].present_in_rest == true OR coherence_torque_velocity < 0.7)`
  `AND ripple.probing[].correlated_with_cur_q ≤ 0.5 [P]`（机械侧未响应）
  kHz 分支（开关/采样相关）额外前置 `f_b ≥ 2000 [L]`，否则**只能 blocked**。
- 必要上下文: `cur_q`；`segment_coverage.rest ≥ 1` 且 `dwell ≥ 1`；
  `spectral.cur_q.harmonic_ratios` 非 null（为 null ⟹ 本规则放弃，不得把 null 当"无谐波"）；
  `meta.drive.notch_filters`/`torque_filter`；`meta.rated_current_a`；`fs` 与开关频率关系（未知时kHz 分支不可用）。
- 排除项（易混淆）:
  - **R-03/R-04**：`coherence_torque_velocity ≥ 0.7` 且 `present_in_rest == false` ⟹ 归机械。
  - **R-17**：量化噪声无阶次结构（`harmonic_ratios` 为 null）且与位置相关而非时间周期。
  - **R-12**：电流环带宽不足表现为**滞后幅值**（时域），无稳定谱峰。
  - **R-07**：编码器误差在 `pos_fb` 侧有强周期、在 `cur_q` 侧弱。
- 建议动作: ①转矩滤波器/陷波（参数化同 R-03；注意 `Δf = f0/Q` 定义必须写明）；
  ②确认电流采样时刻与 PWM 中心对齐（固件/配置级，标注"参数不可解决"）；
  ③屏蔽与接地复检（对应 C3 `differential.considered` 里的"接线/屏蔽"项）。
  风险：对非周期噪声加陷波无效且削减相位裕度；若峰源于采样混叠（R-10），陷波会掩盖问题。
  `requires_offline: true`；可逆：参数级。
- 期望效果与其依据: `rule_heuristic`（方向：`cur_q.tonality_index`、`cur_q_rms_pct` 下降）。
  **不得**给改进百分比：DaRUS 无本故障样本（KB7），T1-b 提供的是分类能力验证而非本项目的效果验证。
- 出处: `T1-b` **Paderborn Condition Monitoring 数据集（电机三相电流故障真值）**——KB7/C5 已指定它
  承担"机械 vs 电气归因分类"的验证；`T2` J. Holtz, "Pulsewidth Modulation for Power Electronic
  Converters", IEEE Trans. Power Electron. 24(12):2889–2899, 2009；
  `T2` Holmes & Lipo, *Pulse Width Modulation for Power Converters*, Wiley-IEEE, 2003
  （开关频率与电流环带宽/纹波关系）；`T1-a` 说明：DaRUS **不提供**本故障样本。
  **A-64/A-65 能力声明（已裁）**：上一句"DaRUS 不提供本故障样本"就是本条的 T1-a 状态——
  **本条在 T1-a 上没有正例来源**，可核验的正面证据只有 `T1-b`（Paderborn CM，分类能力）与 `T2` 文献；
  报告/自评里**不得**把 T1-a 写进本条的命中率来源，也不得用 T3 合成主张"已能检出转矩纹波"，
  合成只支持"管线跑通"级主张（A-64）。kHz 分支在 T1-a 上另受数据层面不可达约束
  （`fs = 1 kHz ⟹ reliable_band_hz = 400 Hz`）⟹ 必须 `unavailable` + `blocked_rules` 登记。
  **A-70（已裁）**：期望效果引用的 `global.cur_q_rms_pct` 是百分比量，
  转矩侧分母取 C1 `meta.drive.rated_torque_N_m` + `rated_torque_source ∈ {measured, manual, nameplate, assumed}`；
  `assumed` ⟹ 本条层级封顶 **T2** 且 caveats 必写"额定转矩为假定值，百分比类判据的绝对刻度不可信"；
  `rated_torque_N_m == null` ⟹ `*_pct` 恒 `null`，只保留 A/`N_m` 绝对值支路（纪律 1）。
- 适用边界: 低频分支 `band⊥ = 150 Hz`；kHz 分支 `band⊥ = 2000 Hz`。在 fs = 1 kHz 上，
  与开关频率相关的纹波（通常数千 Hz）**必须**进 `blocked_rules` 并在 `not_evaluable` 写明
  "开关频率纹波在本采样率下不可观测"，**禁止**输出"未见转矩纹波"（纪律 2，**已裁 A-65**）。

### R-12 电流环带宽不足
- family: `electrical_current_loop_bandwidth`
- 断言: 电流环交越相对速度环过低，高频转矩指令跟踪滞后，误差随频率单调增大且无机械谱峰。
- 判据: 支路 A（有驱动器参数时，首选）:
  `meta.drive.current_loop_bandwidth_hz ≥ 10·meta.drive.velocity_loop_gain_hz [L]` **被违反**
  （即 `current_loop_bandwidth_hz < 10·velocity_loop_gain_hz`）⟹ 命中。
  支路 B（`drive.*` 缺失，C1 示例中 `velocity_loop_gain_hz = null`）:
  `ff_mismatch.fe_vs_accel_corr ≥ 0.6 [P]`
  `AND ff_mismatch.asymmetry_ratio ∈ [0.9, 1.2] [P]`（滞后是对称的，这点把它与前馈失配分开）
  `AND spectral.cur_q.tonality_index ≤ 0.3 [P]`（无峰）
  `AND ripple.probing[].correlated_with_cur_q ≥ 0.7 [P]`
  ⟹ 支路 B 命中一律标 `unverified`（纪律 3），并要求补数据。
- 必要上下文: `cur_cmd` + `cur_q`（滞后/比值判据需要指令与实测两侧，C1 词表都有）；
  `vel_cmd`；`meta.drive.velocity_loop_gain_hz`、`meta.drive.current_loop_bandwidth_hz`
  （裁决 A-42/G-8：`current_loop_bandwidth_hz` **已在 C1 `drive` 块登记**；为 `null` 时支路 A 前件依赖 null
  ⟹ 自动走支路 B 并降 `unverified`（纪律 1/3），不得用默认值冒充实测）。
- 排除项（易混淆）:
  - **R-15**（前馈失配）：**这是本规则最关键的混淆**。两者都造成加速段误差；
    通用近似 `e ≈ a/ωn²`（§3.1）说明误差幅值无法区分。区分量：
    `asymmetry_ratio`（前馈 ≥1.5、带宽不足 ≈1）+ `cur_cmd` 与 `cur_q` 的滞后（带宽不足显著）。
  - **R-11**：纹波有谱峰，本规则无。
  - **R-06**：摩擦只在起动瞬间。
  - **限流饱和**（C3 `differential.considered` 的"限流饱和"项）：
    `cur_q_saturation_ratio` 高 ⟹ 先判饱和，不判带宽（该量的分母纪律见适用边界，A-70）。
- 建议动作: 电流环带宽受开关频率与采样延迟物理限制，**通常不可靠增益提高**（乱提电流环增益会振荡）。
  顺序 ①确认电流反馈滤波时间常数是否过大（参数级、可逆，先减小说明依据）；
  ②若确需提高带宽 ⟹ 提高开关频率/改采样同步 ⟹ 硬件固件层，报告标注"超出参数可解范围"；
  ③临时缓解：把速度环带宽降到电流环的 1/10 以下 [L]（牺牲节拍，须与工艺联评）。
  `requires_offline: true`；`requires_human_approval: true`（涉及电流环参数）。
- 期望效果与其依据: `rule_heuristic`（方向：`cur_cmd`-`cur_q` 滞后下降、`fe_rms` 在高速段下降）。
- 出处: `T2` H. Butler（级联环带宽分离原则：内环显著快于外环）；`T2` Leonhard 1996（级联结构）；
  `T2` Holmes & Lipo 2003（PWM 对可实现电流环带宽的约束）；
  `T2` I. J. Busada, S. R. Suh, B. D. Arnett, "Optimal Bandwidth and Harmonic Distortion
  Prediction for a PWM Boost Rectifier", IEEE Trans. Power Electron. 1999——**标题/卷期需复核**（原始
  Busada & Suh, IEEE PESC/APEC "Optimal bandwidth current control for AC power supplies", 1988/1990）。
  **A-64/A-65 能力声明（已裁）**：电流环带宽属 kHz/数百 Hz 量级判据，**在 T1-a 上没有正例来源**
  （DaRUS 数据既无该故障真值，`fs = 1 kHz` ⟹ 奈奎斯特 500 Hz ⟹ `reliable_band_hz = 400 Hz`
  也看不到电流环本身的行为），本条**只有 T2 文献正当性**（本条出处里没有 T1-x，正是这个意思）；
  因此"能检出电流环带宽不足"这类主张只能是**"管线跑通"级**（A-64）。
  频带侧的后果按 §2.1：本条 `band⊥ = 200 Hz` 本身不被 R-25 阻塞，但**支路 B 的谱证据在 400 Hz 带上是"带内无峰"这一弱断言**，
  命中后仍标 `unverified`（纪律 3）；`next_data_to_collect` 必须写"补 `fs ≥ 8 kHz` 的电流环激励样本"。
  **禁止**输出"未发现电流环问题 / 带宽充足 / 未见异常"——看不见 ≠ 没有（A-65）。
  **A-70 分母纪律（已裁）**：本条排除项里的"限流饱和"支路用 `global.cur_q_saturation_ratio`，
  该百分比的分母取 C1 `meta.drive.rated_torque_N_m` 且 `rated_torque_source ∈ {measured, manual, nameplate, assumed}`；
  `assumed` ⟹ 饱和判据层级**封顶 T2**，caveats 必写"额定转矩为假定值，百分比类判据的绝对刻度不可信"；
  `rated_torque_N_m == null` ⟹ `*_pct`/饱和比恒 `null`，只走 A/`N_m` 绝对值支路。
- 适用边界: `band⊥ = 200 Hz`；需要 `cur_cmd` 通道；不适用于仅提供 `torque %` 的样本（可用但降级，
  且其 `%` 刻度受 A-70 分母纪律约束）；
  fs = 1 kHz 上电流环本身的行为不可观测（奈奎斯特 500 Hz），支路 A 若声明带宽数值必须交叉核对采样率
  （**已裁 A-65**：此时是 `unavailable` + `blocked_rules`，不是"无问题"）。

### R-13 速度环 PI 失谐
- family: `electrical_velocity_pi_detune`
- 断言: 速度环交越/相位裕度落在稳定裕度之外，谐振峰位于远低于 `f_b` 的低频，衰减慢。
- 判据: `bandwidth.position_loop_crossover_hz != null`
  `AND bandwidth.phase_margin_deg < 45 [L]`
  `AND bandwidth.gain_margin_db ≥ 6 [L]`（GM 违反 ⟹ 优先判 R-14 自激风险，动作改为降增益）
  `AND step_response[].damping_ratio_estimate != null AND ζ ≤ 0.2 [P]`（C2 示例 0.28 恰在未命中侧）
  `AND step_response[].ringing_cycles_to_settle ≥ 5 [P]`
  `AND (meta.drive.velocity_loop_gain_hz != null ⟹ velocity_loop_gain_hz ≥ 10·bandwidth.position_loop_crossover_hz [L]，
        违反则该比值违规作为第二条证据)`
  `AND resonance.candidates[].freq_hz < 100 [P]`（峰在低频）
- 必要上下文: `bandwidth.*`（**置信恒 ≤ 0.6**，§1.10）⟹ 本规则**不得**作为增益上调的唯一支撑；
  `segment_coverage.settling ≥ 3`；`vel_fb` 非派生（派生 ⟹ 置信 ×0.7，纪律 10）；
  `meta.drive.rigidity_level`（C1 示例为 null ⟹ 缺失即降级 `unverified`）。
- 排除项（易混淆）:
  - **R-14**：位置环失谐/自激发生在**静止保持**时；本规则发生在**运动/整定**时。
    区分：`step_response[].limit_cycle_present` + 是否有 `dwell` 段振荡。
  - **R-09**：机械柔性造成的低峰，特征是 `is_double_inertia_pair == true` + 相干高。
  - **R-05**：摩擦极限环是锯齿（`is_sawtooth`），本规则是正弦衰减振铃。
- 建议动作: 顺序 ①减小速度环 P 增益（每 −20% 复测 `phase_margin_deg` 与 `settling_time_ms`）；
  ②增大积分时间常数 `Ti`（降低低频相位侵蚀）；③若 `ζ < 0.1` ⟹ **禁止**直接改增益，
  先加滤波/整形（同 R-03/R-09）。风险：降增益直接恶化节拍（`settling_time_ms` 上升），
  必须与工艺时间预算联评（对应 C1 `context.complaint` 的节拍诉求）。
  `requires_offline: true`；可逆：参数级。
- 期望效果与其依据: `simulation_validated`（若 C4 `plant_fit.damping_fitted` 存在且
  `fit_residual_pct ≤ 25%`）；否则 `rule_heuristic`（方向：`overshoot_pct`、`ringing_cycles_to_settle` 下降）。
- 出处: `T2` Franklin, Powell & Emami-Naeini, *Feedback Control of Dynamic Systems*（增益/相位裕度判据）；
  `T2` Dorf & Bishop, *Modern Control Engineering*（`t_s ≈ 4/(ζωn)`、二阶指标）；
  `T2` Rockwell Automation, *Strictly Servo — Understanding and Using the Servo Systems in
  ControlLogix and FlexLogix Motion Controllers*（N. Emery；级联整定与带宽分配经验值）；
  `T2` SIEMENS AG, *SINAMICS S120 Closed-Loop Control Function Manual*（速度环 P/I 与滤波时间常数条目，
  `p1460`/`p1461`）——**参数号需复核**；`T2` Yaskawa Σ-7（`Pn29001`/刚性等级相关条目）——**需复核**。
- 适用边界: `band⊥ = 100 Hz`；`fs ≥ 1 kHz`（DaRUS 上**可评估**，但受 H1 激励充分性限制）；
  不适用于只有 `fe` 的样本；不适用于低带宽液压/绳索执行器（`f_pos` 可能 < 5 Hz，落在校验带外）。

### R-14 位置环 PI 失谐 / 增益过高自激（hunting）
- family: `electrical_position_pi_detune`
- 断言: 静止保持位置时出现窄带极限环，其频率与位置环带宽相当，不是低速爬行也不是 kHz 机械啸叫。
- 判据: `step_response[].limit_cycle_present == true`
  **（主判别键，已裁 A-95）** `AND limit_cycle_waveform == "sinusoidal"`（**非**锯齿）
  `AND present_in_rest == true AND present_in_dwell == true`（静止时也在 ⟹ 非摩擦、非插补欠载）
  **（频率：相对优先）** `AND abs(limit_cycle_freq_hz / bandwidth.position_loop_crossover_hz − 1) ≤ 0.5 [P]`
  优先分支：`position_loop_crossover_hz != null` ⟹ 用上式（等价于 `f_lc ∈ [0.5, 2.0]·f_pos`）；
  **回退分支**：`position_loop_crossover_hz == null` ⟹ 才用绝对窗 `limit_cycle_freq_hz ∈ [20, f_b] [P]`，
  且该分支整体记 `unverified` + 置信封顶 0.55，C3 须写明"使用绝对回退窗，频率归属不可判定"
  `AND step_response[].limit_cycle_amplitude_counts ≥ 0.5·settle_band_counts [P]`
  （**`【比值·刻度无关】`**：极限环幅值与判稳带宽同为位置原生刻度量，相消。⚠ 但 `settle_band_counts` 的
  **默认值**含一条 `20 counts` 绝对支（§1.8）——无 `counts_per_mm` 时默认带宽只剩 `0.02·fe_rms` 一支，
  这是**上游特征**的降级，不是本叶降级，本叶仍照算）
  `AND (bandwidth.phase_margin_deg != null ⟹ phase_margin_deg < 30 [P])`
  `AND (crawling.low_speed_segments 为空 OR is_sawtooth == false)`（排除摩擦）
  `AND NOT (encoder.per_rev_periodic_present == true AND limit_cycle_freq_hz 随速度变化)`（排除 R-07）

- 必要上下文: `dwell`/`rest` 累计 ≥ 2 s；`bandwidth.*`（低置信，见 §1.10）；
  `meta.drive.notch_filters`（陷波可能把峰压掉 ⟹ 漏判方向必须说明）；
  `meta.drive.rigidity_level`（存在才可用其数值，缺失 ⟹ `unverified`）；
  `quality_ref.quantization_step_counts`（与 R-17 分工）；`segment_coverage.settling ≥ 1`。
- 排除项（易混淆）:
  - **R-05**：**已裁 A-95 —— 改用形状键分界**。R-05 专属键 = 锯齿 + `stall_count ≥ 1` + 低速段；
    本规则专属键 = 正弦型 + 静止时也存在 + 幅值 ≥ `0.5·settle_band`。
    频率"本规则 > 20 Hz / R-05 < 2 Hz"仅作 `f_pos == null` 时的回退口径（见 §1.8 `limit_cycle_waveform`）。

  - **R-17**：量化极限环幅值 ≈ 1–2 counts、频率与采样/量化相关而与带宽无关。
    **`【绝对】`**（"1–2 counts"是字面 counts 常数）⟹ `counts_per_mm == null` 时**本句不得用作区分量**，
    区分改走 R-17 的刻度无关形式（`limit_cycle_amplitude ≤ 3·量化台阶`），二者不互推。
  - **R-03**：kHz 啸叫；本规则频率在带宽量级。
  - **R-23**：本规则是"永远进不了带"；R-23 是"再等一会儿就进带但判定太早"。
- 建议动作: 顺序 ①降低位置环增益 / 降低刚性等级（仅当 `meta.drive.rigidity_level != null`，
  否则降级为方向性建议）；②减小或移除积分作用（检查抗积分饱和）；③复检测量噪声链路（编码器脏污、
  速度反馈滤波）。风险：**C3 `safety.hard_blocks` 明文禁止在带工件/带负载状态下直接下发增益**；
  降增益会使载荷下跟踪误差增大，可能比自激更糟。`requires_offline: true`（须 C4 稳定性校验：
  相位裕度、增益裕度、是否激发新模态，C4 流程第 3 步）。
- 期望效果与其依据: `rule_heuristic`；若经 KB5 三环内核 + C4 复现 ⟹ `simulation_validated`。
- 出处: `T2` Olsson 1998（摩擦 + 积分器造成的极限环）；
  `T2` Franklin & Powell（极限环与量化/死区关系章节）；
  `T2` Yaskawa Σ-7 / Panasonic A6 关于"增益过高导致振荡（hunting）"与刚性等级下调的手册条目；
  `T1-b` 限制说明：CWRU/帕德博恩**无位置通道**（C5 §T1-b "不能证明"列），故本规则在 T1 上不可验证，
  只能用 T2 合成案例（阈值取自本手册条目）验证 ⟹ 报告须标 `rule_heuristic`。
- 适用边界: `band⊥ = 100 Hz`；`fs ≥ 1 kHz`；不适用于无保持/静止段样本；
  **相对判别需要 `bandwidth.position_loop_crossover_hz != null`**（`null` 时走绝对回退窗，整体 `unverified` + 置信封顶 0.55，A-95），
  不适用于无保持/静止段样本（重复条款以本行为准）。

### R-15 前馈失配（核心判据：加/减速段跟随误差不对称）
- family: `electrical_feedforward_mismatch`
- 断言: 加速度前馈（或速度前馈/转矩折算系数）增益或方向失配，导致加速段跟随误差显著大于减速段（或反之），
  误差与指令加速度强相关，而静止与恒速时几乎无误差。
- 判据（`ff_mismatch.asymmetry_ratio` 为**有向**量，裁决 A-26：`kff>1` 与 `kff<1` 两支必须严格镜像，
  否则只判加速段占优会**系统性漏判减速段占优那一侧**）:
  按 C2 定义 `asymmetry_ratio = accel_regime_rms / decel_regime_rms`，取其**有符号不对称** `A_s`：
  `asymmetry_ratio ≥ 1` 时 `A_s = +asymmetry_ratio`（加速段误差占优），
  `asymmetry_ratio < 1` 时 `A_s = −1/asymmetry_ratio`（减速段误差占优）。命中条件 = **两支之一**：
  - **分支①（欠补偿，`kff` 偏小 ⟹ 加速段占优）**：符号条件 `A_s > 1`（即 `asymmetry_ratio > 1`）
    `AND` 幅值条件 `A_s ≥ 1.5 [P]`（等价 `asymmetry_ratio ≥ 1.5`；C2 示例 2.26、C3 示例 E2 的前馈假设即此类）；
  - **分支②（过补偿，`kff` 偏大 ⟹ 减速段占优，与分支①镜像）**：符号条件 `A_s < −1`（即 `asymmetry_ratio < 1`）
    `AND` 幅值条件 `A_s ≤ −1.5 [P]`（等价 `asymmetry_ratio ≤ 1/1.5 ≈ 0.667`）。

  任一支命中后，再 `AND` 以下共同条件：
  `AND ff_mismatch.fe_vs_accel_corr ≥ 0.6 [P]`（示例 0.83；`tracking.path_segments[].corr_fe_vs_accel` 0.91）
  `AND ff_mismatch.residual_slope_vs_jerk_corr ≤ 0.6 [P]`（jerk 侧残差不显著 ⟹ 非轮廓/jerk 问题）
  `AND (resonance.candidates 为空 OR (present_in_rest == false AND spectral.cur_q.tonality_index ≤ 0.5))`
  `AND NOT (global.friction_stiction_ratio ≥ 1.5)`（排除 R-06）
  `AND NOT (global.backlash_estimate_counts ≥ 3·global.fe_rms_counts)`（排除 R-08；**`【比值·刻度无关】`**，
  两侧同刻度相消 ⟹ 无 counts 刻度时该反证照样能跑）
  `AND step_response[].damping_ratio_estimate ≥ 0.5 [P]`（环路整定本身不异常）
- 必要上下文: `pos_cmd`（算 `a`）；`fe`；`vel_cmd`；`segment_coverage.move ≥ 3` 且加减速区样本各 ≥ 50；
  `quality_ref.dt_jitter_ratio ≤ 0.05`（二阶差分对时基抖动极敏感；A-49：走 C2 镜像路径，原写 C1 `quality.*`）；
  `tracking.path_segments[].acceleration_feedforward_pct_applied`（可估则作为第二条证据）；
  **KB7 方向符号已修正**（否则 `Ω_dec` 集合定义错误，纪律 9）；
  若样本分属 `Torque_based` / `Velocity_based` 两种控制结构（KB7），必须**分组**估计 `asymmetry_ratio`，
  不得混算。
- 排除项（易混淆）:
  - **R-03 / R-26**（机械谐振）：C5 §6 认定的最高频混淆对，"两者都在加减速时刻出现纹波"。
    判别：谐振在 `dwell` 段仍振、`cur_q` 有相干峰；前馈失配在 `a → 0` 后误差立即回落、
    静止段无任何谱峰（C1 §segments 明文）。
  - **R-12**（电流环带宽不足）：两支都不显著 ⟹ `abs(A_s)` 接近 1（`asymmetry_ratio ≈ 1`，滞后对称）。
  - **R-02**（松动）：冲击型尖峰 vs 平滑的与 `a` 成比例的误差。
  - **R-21/R-19**（软件侧）：软件侧是阶跃/突进，本规则是连续比例误差；必须有 `event_context` 才能判前者。
- 建议动作: 顺序 ①以**有符号** `A_s` 为标尺调整加速度前馈增益，方向由命中的分支决定（勿只写一支，A-26）：
  `kff_new = kff_old · (1 − sign(A_s)·(abs(A_s) − 1)·0.5) [P]`，每步 ±10%。
  即：分支①（`A_s > 1`，加速段占优）与分支②（`A_s < −1`，减速段占优）的修正**符号相反**；
  每步复测目标 `A_s → ±1`（`asymmetry_ratio → 1.0`）、`fe_vs_accel_corr → 0`。
  ②检查前馈的**符号与单位口径**（转矩→加速度换算依赖总惯量 `J_total` 与 `counts/rev`、`rad/s²` 口径，
  与 `inertia_ratio` 同源）；③若 `residual_slope_vs_jerk_corr` 高 ⟹ 加 jerk 限制 / 输入整形，
  而不是继续动前馈；④若 `counts_per_mm == null` ⟹ 建议值只给**相对比例**（±%），不给绝对数值。
  **（A-97 更正 / 标注）**本句②里的 `counts/rev` 口径在 `units_are = si_native` + `counts_per_mm == null`
  时同样没有落点（"转 ↔ 原生刻度"缺换算，**已裁 A-110 ①**），检查项应读作"该反馈通道的
  每转当量（counts 或 SI 导程/传动比）"；本句④"只给相对比例"与本文件其余比值支一致（**`【比值·刻度无关】`**），
  保留不动——它是**保守下界**，不是"绝对数值不可得"的断言：能否给原生刻度的绝对建议值属第 3 条待裁事项。
  风险：前馈过高会在指令结束时出现反向过冲（`overshoot_pct` 上升）并冲击机构；
  DaRUS 发布的 `kff = 1.5 [L]`（KB7 控制器参数明文）说明**大于 1 的前馈增益在真实系统中确实存在**，
  故报告不得把 `kff > 1` 直接当故障，必须依赖误差形态。
  `requires_offline: true`；可逆：参数级、可回读。
- 期望效果与其依据: `simulation_validated`（KB5 内核含前馈支路 + C4 V*）；否则 `rule_heuristic`
  （方向：`asymmetry_ratio → 1`、`fe_rms_counts` 下降）。
- 出处: `T1-a` DaRUS 控制器参数明文 `torque-cable-force: kff=1.5 kp=0.01 ki=0.1 kd=0.0005`，低通 0.02 s
  （KB7 硬件真值节；KB7 原文即称其为"研究前馈失配的天然样本"）；
  `T2` H. Butler（acceleration feedforward 与跟踪误差关系）；`T2` Rockwell《Strictly Servo》
  （velocity/acceleration feedforward 条目）；`T1-a` `StatCompensationValid`/`VelDynCompValid`/
  `PowerDynCompValid`（**补偿有效性验证实验**，与本项目验证门控同构，KB7 战役表）；
  `T3` KB5（仅流程跑通，不得单独支撑，KB0 §4）。
- 适用边界: 时域判据（`band⊥ = n/a`），要求 `fs ≥ 500 Hz` 以分辨加减速时刻；
  不适用于恒速段与静止段；不适用于无 `pos_cmd` 的样本（无法定义 `a`）；
  不适用于梯形速度轮廓中无恒速平台的极短行程（`a` 与 `v` 共线，回归不可辨）。

### R-16 电机发热 / 转矩常数漂移
- family: `electrical_motor_heating`
- 断言: 温升使绕组电阻与 `k_t` 漂移，表现为同等位移指令下电流需求上升、输出能力下降，且与温度单调相关。
- 判据: `global.thermal_fe_correlation_r ≥ 0.6 [P]`
  `AND` 冷/热机配对样本上 `global.cur_q_rms_pct` 单调上升 ≥ 15% [P]（无配对样本时本条不可判）
  `AND global.cur_q_saturation_ratio ≥ 0.02 [P]`
  `AND step_response[].overshoot_pct` 随温度呈**下降**方向变化 [P]（等效阻尼增大）
  `AND abs(global.thermal_drift_counts_per_min) < 2.0 [P]`（位置侧漂移不显著 ⟹ 排除 R-01）
  **`【绝对】`**（§1.13b：与 R-01 同一个 counts/min 字面常数）⟹ `counts_per_mm == null` 时本排除项
  `blocked_by = absent_counts_scale` + reason「无 counts 刻度，绝对阈值不可比」，且**缺席 ≠ 通过**（纪律 1）：
  不得把"不可比"读成"位置侧漂移不显著"来放行本条归因，该反证只能记 `not_evaluable`。
- 必要上下文: `temp` 通道（缺失 ⟹ `unavailable` ⟹ 本规则**放弃**，见 C2 示例的 `unavailable` 条目）；
  冷/热机同轨迹配对样本；`meta.rated_current_a`；温度跨度 ≥ 5 °C 且 `var(temp) ≥ 0.2`；
  `meta.context.operator_notes` 或 `machine_context.operator_notes`。
- 排除项（易混淆）:
  - **R-01**：见判据第 5 条（位置侧 vs 电流侧）。二者可同时成立（热-机-电耦合），
    此时 R-01 为 primary，R-16 为 rank 2 并在 `rationale` 说明耦合方向。
  - **R-12**：带宽不足与温度无关（无单调性）。
  - **R-06**：摩擦也随温度变，但峰在起动瞬间且伴随 `vel_min_ratio`/`stall_count` 变化。
- 建议动作: 归为"热设计/负载复检"类。参数侧仅建议降低连续电流密度（降速度曲线陡度、
  延长驻留、增加空闲散热行程）；**不**建议提高增益"压住"温漂。
  风险：持续高温导致永磁体不可逆退磁 ⟹ 必须标为安全级问题，
  `requires_human_approval: true`，并列入 `safety.hard_blocks`。`requires_offline: true`。
- 期望效果与其依据: `unverified`（不给数字；方向：`thermal_fe_correlation_r` 与 `cur_q_rms_pct`
  的温度斜率下降）。
- 出处: `T1-a` DaRUS `TempSlip`（温度相关）与数据集含温度测量（KB7 测量设备节：Micro-Epsilon
  ASCOspeed + LSV-2100-30 + 力传感器 + 温度）；
  `T2` SIEMENS SINAMICS S120 电机热模型/温度保护（I²t）功能手册条目；
  `T2` Kollmorgen 伺服选型与热设计/连续转矩-温度关系技术文档；
  `T2` Leonhard 1996（电机时间常数与热约束章节）——**具体条目需复核**。
  **A-64/A-65 能力声明（已裁）**：`electrical_motor_heating` 与 R-01 一样**在 T1-a 上没有正例来源**——
  上面那条 `T1-a` 只说明"试验台具备温度测量、数据集存在 `TempSlip` 战役"，
  **不等于**本项目手上的 T1-a 样本含 `temp` 通道或冷/热机配对轨迹（实际不含，见 C2 示例的 `unavailable` 条目）；
  故本条判据的正当性只有 **T2**，命中率/正面检出主张不得引用 T1-a，也不得用 T3 合成冒充能力证据
  （合成只支持"管线跑通"级主张，A-64）。无 `temp` 时报告侧为 `unavailable` + `not_evaluable` 逐模式登记，
  **禁止**输出"未发现电机发热 / 转矩常数无漂移 / 未见异常"（看不见 ≠ 没有）。
  **A-70 分母纪律（已裁）**：本条第 2、3 判据 `global.cur_q_rms_pct`、`global.cur_q_saturation_ratio`
  都是百分比/比值类，转矩侧分母必须来自 C1 `meta.drive.rated_torque_N_m` 且
  `rated_torque_source ∈ {measured, manual, nameplate, assumed}`；
  `assumed` ⟹ 本条层级**封顶 T2**（即便文献支路成立也不得写 T1-x），且 caveats 必写
  "额定转矩为假定值，百分比类判据的绝对刻度不可信"——本条的"≥15% 上升"与"≥0.02 饱和比"
  都是绝对刻度敏感的阈值；`rated_torque_N_m == null` ⟹ 两个百分比量恒 `null`
  ⟹ 纪律 1：本条放弃，只允许 `cur_q`（A）与 `N_m` 绝对值支路。
- 适用边界: 时域低频（`band⊥ = n/a`）；需 ≥30 min 温度跨度；不适用于无 `temp` 样本；
  不适用于风冷/水冷恒定的直驱（温升路径不同）；`rated_torque_source == "assumed"` 时
  只给方向不给百分比（A-70，已裁）。

### R-17 分辨率 / 量化噪声主导
- family: `electrical_resolution_quantization`
- 断言: 位置测量量化台阶相对容差过大，误差呈"台阶 + 小幅极限环 + 高频低幅抖动"，属测量链路而非机械/控制故障。
- 判据: `step_response[].settle_band_counts != null`
  `AND 有效量化台阶 ≥ 0.3·settle_band_counts [P]`（量化台阶取 C2 路径 `quality_ref.quantization_step_counts`；
  裁决 A-10 已把它落进 C2 `quality_ref` ⟹ 可作为 `supporting_evidence[].feature`，不再只写在叙述里，见 G-4。
  **`【比值·刻度无关】`**：台阶与判稳带宽同为该通道原生刻度量，相消 ⟹ 本条是"量化 vs 容差"的相对判据，
  **不依赖 `counts_per_mm`**，不得因无 counts 刻度而记 unavailable）
  `AND global.fe_sign_change_rate_hz ≥ 0.25·fs [P]`（近零乱的符号翻转 ⟹ 白噪声型抖动；
  **`【比值·刻度无关】`**：翻转率对 `fs` 归一，两个量都是 1/s，与位置刻度无关）
  `AND spectral.fe.tonality_index ≤ 0.25 [P]`（谱平坦；**`【比值·刻度无关】`**，PSD 几何均值/算术均值之比）
  `AND (step_response[].limit_cycle_present == true ⟹ limit_cycle_amplitude_counts ≤ 3·量化台阶 [P])`
  （**`【比值·刻度无关】`**：幅值对量化台阶取比，同刻度相消——这是 R-14 排除项里"≈ 1–2 counts"
  那句绝对表述的**刻度无关替身**，两者不得互推）
  `AND encoder.per_rev_periodic_present == false`
- 必要上下文: `meta.encoder_lines`、`meta.axis.motor_rev_counts`、`meta.counts_per_mm`、
  `quality_ref.quantization_step_counts`、`quality_ref.dt_jitter_ratio ≤ 0.1`（A-49：dt_jitter 已在 C2 有镜像）；
  若 `channels.vel_fb.derived == true` 必须在报告中说明差分对量化噪声的放大（噪声增益 `≈ 2/T_s`）
  并置信 ×0.7（C1 规则 4）。
- 排除项（易混淆）: **R-07**（周期误差有确定阶次，本规则无）；
  **R-14**（自激极限环频率 ≈ `f_pos`，本规则幅值 ≈ 量化台阶）；**R-10**（量化可造伪峰，二者互证）；
  **R-05**（爬行幅值远大于量化台阶且为锯齿）。
- 建议动作: ①提高分辨率（电子细分、更高线数光栅、更高速 ADC）⟹ 硬件级，标注"参数不可解决"；
  ②参数侧唯一能做的是**放宽 `settle_band`**（若工艺容差允许）——报告必须明写
  "这是放宽到位判据，不改善物理精度"，并与 R-29 的节拍余量联合评估；
  ③增加测量滤波（直接牺牲带宽，须与 R-13/R-15 联评）。
  风险：把量化问题当机械问题去加陷波或补偿，会引入反向死区。
- 期望效果与其依据: `rule_heuristic`。
- 出处: `T2` D. A. Neyer, "Effects of quantization noise on high-resolution optical encoders",
  IEEE Trans. Ind. Electron. 36(2), 1989——**卷期需复核**；
  `T2` Bao et al. 1993；`T2` Franklin & Powell（量化极限环章节）；
  `T2` KB0 §5 / C1 单位规则（counts 为唯一内部基准，`quantization_step_counts = 1.0` 的语义）。
  **（A-97 更正）**原句把 counts 当"唯一内部基准"：A-97 ① 已定 `*_counts` 后缀是**历史名**，
  其值是该通道**原生刻度**下的读数、真实单位由 `meta.units_are` 唯一决定 ⟹ `quantization_step_counts = 1.0`
  在 si_native 样本上的含义是"最小可读间隔 = 1 个原生刻度步（本例量级为 m）"，不是"1 个编码器脉冲"。
  本条判据全是"台阶 ÷ 容差"的相对形式，⟹ **刻度无关，照算**（§1.13b）。
- 适用边界: `band⊥ = n/a`；要求 `fs` 已知且 `dt_jitter_ratio ≤ 0.1`；
  `quality_ref.quantization_step_counts` 为 null ⟹ 整条放弃（纪律 1）。

### 族三：`software_induced_*`（R-18 … R-24）——差异化能力所在

本族 7 个 slug（KB0 §2）各一条主判据：`host_thread_jitter`(R-18)、`interp_buffer_underrun`(R-19)、
`bus_cycle_miss`(R-20)、`late_vision_result`(R-21)、`pulse_eq_overwritten`(R-22)、
`settle_window_too_short`(R-23)、`polling_latency`(R-24)；另有 R-28（族内互斥仲裁）、
R-29（节拍余量衍生规则）、R-30（不可评估登记义务）。
**族级严重度锚点（A-100 已裁，落点 KB4 §2.9）**：R-19/R-21→S2、R-18/R-24→S3、R-20 维持
`n_alarm ≥ 1`→S0 且无告警时为 S2（R-22→S1、R-23→S2 原已在表）；锚点按"后果类型"归入现有档，
`rule_table.json` 的 `severity_provenance` 以 `classified:` 前缀指向 §2.9 表行，引擎仍须在
`audit.assumptions` 留痕（分类锚点、非独立观测锚，不得写成唯一结论）。跨档排序归 KB4 §2.9，
R-26/R-28 均不得覆盖 severity 序。
**族级纪律**（重申，优先于任何单条）：
`event_context.available == false` ⟹ 7 条全部放弃 + 整族登记 `differential.not_evaluable`（R-30）；
`event_context.causal_claims_permitted == false` ⟹ 7 条全部**不得**产出归因，只允许"时间共现"表述，
并把共现统计写入 `audit.assumptions` + `contradicting_evidence`；
任何 `alignment_residual_ms > sync.uncertainty_ms` 的对齐不得作为因果证据（纪律 6 / **A-82**：
残差超预算 ⟹ 对齐不可信，只能共现）；而另一方面被声称的**时延/差值**若 `≤ τ_u` 也不可分辨，同样不得作证据。

**族级 `expected_effect.basis` 纪律（裁决 A-43，取代旧"本族一律 rule_heuristic"的写法，回应 G-12）**：
KB5 内核已建模**事件注入**（host 停顿 / 插补欠载 / 丢周期，并含"无事件"与"未同步"两类孪生样本），
故本族（R-18…R-24）的 `expected_effect.basis` 分两类处理：
1. **检出类判据**（判断该成因是否存在，如 `fe_spike_aligned_to_* / fe_spike_count` 的比例门限）——
   事件注入仿真可复现 ⟹ **允许**标 `simulation_validated`（仍须有 C4 `validation[]` 的 V* 记录、
   `fit_residual_pct ≤ 25%`，纪律 7）；
2. **改进量**（"整改后某指标下降多少"的量化承诺）——真实收益依赖上位机调度与总线仲裁，仿真不建模，
   **一律** `rule_heuristic`（只给方向不给数字），`unverified` 为其降级态。
凡引用仿真支撑本族任一判据，报告**必须**附 caveat：**"仿真不含真实调度器与总线仲裁"**；缺此 caveat 即视为措辞越级（KB0 §4 / C3 规则 14）。

### R-18 上位机线程调度抖动造成跟随误差尖峰
- family: `software_induced_host_thread_jitter`
- 断言: 跟随误差尖峰与上位机进程（GC / 线程抢占 / 内存）停顿事件以优于同步不确定度的精度相关，
  且无机械或电气成因特征。
- 判据: `event_context.available == true AND event_context.causal_claims_permitted == true`
  `AND event_context.fe_spike_count ≥ 3 [P]`
  `AND event_context.fe_spike_aligned_to_host_pause / event_context.fe_spike_count ≥ 0.7 [P]`
  `AND event_context.host_pause_max_ms ≥ 20 ms [P]`
  `AND event_context.host_pause_max_ms ≥ 5·(位置环周期) [P]`（停顿须长到足以错过多个控制周期；
  位置环周期取 `meta.drive.position_loop_period_us`，C1 示例为 null ⟹ 本条降级 `unverified`）
  `AND event_context.alignment_residual_ms ≤ event_context.sync.uncertainty_ms`
  （**A-82 已裁方向，更正 A-50**：`alignment_residual_ms` 是匹配对 `abs(Δt)` 的中位数＝对齐**残差**，
  残差落在不确定度预算**之内**才说明这份同步真的做到了它声称的精度（与上一行的断言"以优于同步
  不确定度的精度相关"、以及 C2 规则 8 的 `causal_claims_permitted`、KB4 CAP-8 同向）。
  残差**超出**预算 ⟹ 两个钟之间还有未建模的系统偏差，尖峰"落在事件附近"可能只是钟差 ⟹ 只报共现。
  A-50 曾把方向定成 `>`，那条判据禁止最紧的巧合、放行最松的对齐，已在 C2 规则 8/14、C6 §3 硬规则 2、
  本族纪律与 R-18/R-20/R-28 逐处改回。）
  `AND resonance.candidates[].present_in_dwell == false`
  `AND ff_mismatch.asymmetry_ratio 的有符号幅值 abs(A_s) < 1.5`（两侧均不显著，非前馈；`A_s` 见 R-15/A-26）
  注：C6 §4 列出的 `host_pause_count` 未落在 C2 JSON 中（G-2），故计数类判据改用
  `event_context.n_by_source.host ≥ 1` 与 `host_pause_max_ms` 组合。
- 必要上下文: `events.jsonl` 含 `source=host` 事件且带 `detail.duration_ms`；
  `sync.method ∈ {trigger_edge, ntp}` 且 `sync.verified == true`；`τ_u` 已知；
  `fs ≥ 1 kHz` 且 `1/fs ≤ τ_u/2`（否则尖峰时刻分辨不出）；`segment_coverage.move ≥ 1`。
- 排除项（易混淆）:
  - **R-02**（松动）：机械冲击尖峰与**反向时刻**相关、与 `host` 事件无关。
  - **R-19**（插补欠载）：尖峰与 `interp` 事件相关且集中在 `path` 段。
  - **R-20**（总线丢周期）：与 `network` 事件相关且 `pos_cmd` 呈单周期保持。
  三者的择优见 **R-28**。
  - **反证支**：`causal_claims_permitted == false` 时本规则必须改写为
    "X/Y 个尖峰与 host 停顿同窗（时钟未对齐，共现不等于因果）"，
    写入 `contradicting_evidence`/`audit.assumptions`，且**不得**出现在 `hypotheses[].cause`。
- 建议动作: 参数侧无解。建议 ①把运动控制线程设为实时优先级 / CPU 绑核 / 隔离核，
  禁用控制线程内的动态内存与 GC；②把位置环下沉到硬实时核或协处理器（运动控制卡）；
  ③加大指令前瞻与插补缓冲深度（与 R-19 动作同源，注意两者可能相互抵消：缓冲变深会增大延迟）。
  风险：优先级设置不当引起**优先级反转**（须用优先级继承/天花板协议）；
  绑核可能与视觉/IO 线程争抢。`requires_offline: false`（上位机软件配置）；可逆；
  `requires_human_approval: true`（涉操作系统配置）。
- 期望效果与其依据: `rule_heuristic`（方向：`fe_spike_aligned_to_host_pause / fe_spike_count → 0`、
  `fe_spike_count` 下降、`fe_p999/fe_rms` 比下降）。
  按族级 A-43 纪律：**检出类**判据（KB5 host 停顿事件注入 + 孪生样本可复现，且有 C4 V*）可标
  `simulation_validated`；**改进量**（"整改后尖峰数下降多少"）仍恒 `rule_heuristic`，
  引用仿真必须附 caveat"仿真不含真实调度器与总线仲裁"（KB0 §4，仅 T3 不构成能力声明）。
- 出处: `T2` L. Sha, R. Rajkumar, J. P. Lehoczky, "Priority inheritance protocols: An approach to
  real-time synchronization", IEEE Trans. Computers 39(9):1175–1185, 1990；
  `T2` G. C. Buttazzo, *Hard Real-Time Computing Systems: Predictable Scheduling Algorithms and
  Applications*, Springer（任务抖动 jitter 与其对控制性能影响章节）——**章节需复核**；
  `T2` A. Cervin, *Systems Modeling and Real-Time Control*, PhD thesis, Lund Institute of Technology,
  2003（传感-作动延迟与调度对闭环性能的影响）；
  `T2` Beckhoff TwinCAT 3（Windows 分区与实时控制线程配置文档）；
  `T2` C6 §0 表格第 1 行（本项目对该成因的定义）；
  `T1-a` 限制：DaRUS 无 C6 事件流 ⟹ 本规则在 T1-a 上**不可评估**（由 R-30 登记）。
- 适用边界: 需 `fs ≥ 1 kHz` 与 `τ_u` 有界；不适用于无 `host` 事件源的数据；
  不适用于上位机与控制器同进程（无独立 host 停顿可观测）的架构。

### R-19 插补缓冲区欠载
- family: `software_induced_interp_buffer_underrun`
- 断言: 连续路径段的跟随误差阶跃与 `interp` 侧 `buffer_underrun` 事件对齐，且事件集中在 `path` 段内。
- 判据: `event_context.available == true AND causal_claims_permitted == true`
  `AND event_context.interp_underrun_during_path ≥ 1`
  `AND interp_underrun_during_path / max(interp_underrun_count, 1) ≥ 0.7 [P]`（C2 示例 11/12 = 0.92；
  事件数之比，无量纲 ⟹ **`【比值·刻度无关】`**）
  `AND fe_spike_aligned_to_underrun / max(fe_spike_count, 1) ≥ 0.5 [P]`（示例 11/17 = 0.65；同为事件计数比，
  **`【比值·刻度无关】`**；注意其分母 `fe_spike_count` 的检出阈也属刻度无关，见 §1.12）
  `AND tracking.path_segments[].fe_max_counts ≥ 2.0·tracking.path_segments[].fe_rms_counts [P]`
  （**`【比值·刻度无关】`**：段内峰值与段内 RMS 同为 `fe` 原生刻度量，相消 ⟹ si_native 样本上照算，
  A-97 ③ 点名的正是这一族，不得被任何绝对 counts 判据连坐）
  （示例 3100/1520 = 2.04 ⟹ 该门限按示例定标，见 §3.2）
  `AND segment_coverage.path ≥ 1`
  `AND tracking.path_segments[].corr_fe_vs_accel ≥ 0.7`（示例 0.91）
  `AND tracking.path_segments[].corr_fe_vs_jerk < corr_fe_vs_accel`（示例 0.32）
- 必要上下文: `path` 段（C1 词表"插补连续路径"）；`events.jsonl` 含 `source=interp`
  且 `detail.buffer_level`/`lookahead_ms`（C6 示例）；`pos_cmd` 的分块边界（判断插补块）；
  `sync.verified == true`；`fs ≥ 500 Hz`。
- 排除项（易混淆）:
  - **R-20**：总线丢周期在 `pos_cmd` 上呈单周期**保持平台**，欠载呈**速度骤降/停顿**；
    事件源也不同（`network` vs `interp`）。
  - **R-21**：视觉迟到与 `vision` 事件对齐且与特定 `step` 绑定。
  - **R-15**：前馈失配的误差与 `a` **平滑成比例**，不是阶跃；且 `interp` 无事件。
  - **R-23**：欠载发生在路径中段，R-23 发生在段末判定。
- 建议动作: 上位机侧：①增大前瞻深度 / 插补缓冲块数；②降低单块路径复杂度（合并小线段、
  减小微观段数量）；③把工艺等待（加热、出胶、固化）移出路径生成线程；
  ④必要时降低路径速度上限。参数侧无解。
  风险：**加大缓冲会增大响应延迟**，与急停/中断路径冲突 ⟹ 必须在报告中与安全逻辑联评，
  `requires_human_approval: true`；可逆（软件配置）；`requires_offline: false`。
- 期望效果与其依据: `rule_heuristic`（方向：`interp_underrun_during_path → 0`、
  `path` 段 `fe_max/fe_rms` 比下降）。
- 出处: `T2` FANUC "AI contour control"（前瞻块缓冲与拐角/加减速处理）说明条目；
  `T2` SIEMENS SINUMERIK "Advance Prediction Control (APC)"；
  `T2` Beckhoff TF5000/TF5100 前瞻与插补缓冲文档；
  `T2` C6 §0 表格第 2 行；
  `T1-a` 限制：DaRUS 无 `interp` 事件（KB7 未发布事件流）⟹ 不可评估。
  **三份 CNC 手册的具体章节/文档编号均需复核**（本项目只引用其"前瞻缓冲 ⟹ 路径速度骤降"的机制描述）。
- 适用边界: `fs ≥ 500 Hz`；需 `path` 段（`probing`/`move` 上的欠载另论，语义不同）；
  无 `events.jsonl` 时不可评估（R-30）。

### R-20 现场总线丢周期 / WKC 异常
- family: `software_induced_bus_cycle_miss`
- 断言: 现场总线出现丢周期或 WKC 校验失败，导致指令单周期保持、反馈不连续跳变，且与 `network` 事件对齐。
- 判据: `event_context.available == true`
  `AND event_context.network_cycle_miss_count ≥ 1 [L]`（存在即异常；WKC 校验失败在 EtherCAT 中是硬错误）
  `AND event_context.n_alarm ≥ 1`
  `AND quality_ref.dt_jitter_ratio ≤ 0.05`（时基本身不稳则无法区分丢周期与时基抖动；
  A-49：该量已由 C1 `meta.quality` 镜像进 C2 `quality_ref`，证据路径走 C2）
  `AND` 尖峰与该 network 事件的对齐 `abs(Δt) ≤ max(τ_u, 2 ms)` 计入、且整体
  `alignment_residual_ms ≤ τ_u`（用 `alignment_residual_ms` 与 `fe_spike_count` 组合；方向见 **A-82**）。

  **升级规则（裁决 A-45：不再是"只能停在共现级"；本段与 KB4 §1.3 N6.c / CP-10 / §2.5 CAP-11
  **逐字同调**，任一文件改动必须同步另一文件，A-45 已裁）**。归因（进 `hypotheses[]`）的充分必要条件是下列
  **三条件同时成立**——相关 C2 字段 `bus_cycle_hold_max_ms`、`fe_spike_aligned_to_network_miss` 已随 A-9
  落进 C2 `event_context`（旧缺口 G-5 就此收口）：
  1. `event_context.bus_cycle_hold_max_ms != null` **且** `event_context.fe_spike_aligned_to_network_miss != null`
     （即"单周期指令保持时长"与"尖峰对齐丢周期计数"两路专属证据都在）；
  2. `event_context.sync.verified == true` **且** `event_context.causal_claims_permitted == true`；
  3. 对齐残差 `event_context.alignment_residual_ms ≤ event_context.sync.uncertainty_ms`。
  （三条件为 canonical 文本，KB4 §1.3 N6.c / CP-10 / §2.5 CAP-11 与本条 R-28 必须**逐字一致**；
  方向由 **A-82** 锁定（更正 A-50）：`alignment_residual_ms` 是匹配对 `abs(Δt)` 的中位数＝对齐**残差**，
  越**小**越好，落在不确定度预算内才算同步可信。"必须**大于** `τ_u`"那条纪律作用的是
  `bus_cycle_hold_max_ms`、`vision_result_latency_p95_ms`、两次到位时刻之差这类**被声称的差值**
  ——差值小于时基不确定度就分辨不出来——不作用于残差。二者混用会写成"对齐越差越允许归因"。）
  ⟹ 三条件齐：**可进 `hypotheses[]`，但 `confidence ≤ 0.6`**（本结论是单通道 `pos_cmd` 平台推断，
  无驱动器侧 WKC 计数通道佐证，不得更自信）。
  ⟹ 缺任一条件：**只到共现级**，**禁入 `hypotheses[]`**，该 fault_mode 只进
  `differential.considered`，并由 R-28 在四路 `s_*` 之间择优（择优结果不得写成归因）；报告措辞"共现，因果未确立"。（已裁 A-45 / A-50，方向由 **A-82** 更正）
- 必要上下文: `events.jsonl` 含 `source=network`（`missed_cycle`/`wkc_error`/`timeout`）；
  `meta.io_bits`（C1：限位/真空/状态字）与 `drive` 事件；
  `sample_rate_source`（`inferred` 时需谨慎）；DC 同步机制已知；`fs ≥ 2×` 总线周期频率。
- 排除项（易混淆）: **R-19**（无 `pos_cmd` 平台，是速度骤降）；**R-17**（量化台阶非跳变）；
  **R-02**（冲击尖峰非保持）；**R-18**（`host` 事件而非 `network`）。择优见 **R-28**。
- 建议动作: ①网络物理层复检：屏蔽层单端/双端接地、拓扑与末端匹配、远离驱动器动力线缆的 EMI 源、
  线缆长度与连接器；②提高周期余量（降低 DC/DC 转换频率、减少从站数、关闭调试流量如 Scope 采样）；
  ③增加 WKC 监控与报警联动（属安全相关）——**本 agent 只报告，不写任何配置**（纪律 7、C6 §5 范围纪律）。
  `requires_offline: true`；`requires_human_approval: true`；可逆：配置级。
- 期望效果与其依据: `rule_heuristic`。
- 出处: `T2`（**条目未核对**，方向性依据）W. Steiner, "EtherCAT Technology and Performance — A Real Time
  Ethernet Overview"（ETG 年会论文）——主题成立，**标题与年份未逐字核到**（原标"年份需复核"，**A-81**）；
  `T2` H. Kopetz, *Real-Time Systems: Designing for Predictable Performance*, Springer, 2011
  （丢帧/周期完整性对控制回路的影响）；
  `T2` EtherCAT Technology Group, ETG.1000.2 *EtherCAT System Specification Part 1000.2*
  （**条目未核对**：规范分卷标题与"分布式时钟/周期同步"的章节归属未逐字核到，只按规范号引用、不写 DOI）；
  `T2`（**条目未核对**，方向性依据）网络化控制系统（NCS）综述一类文献，主题＝丢包/时延对闭环稳定性的
  理论结论。**原写法 `G. Nair, F. L.? / J. P. Hespanha et al., Proc. IEEE 95(2):139–162, 2007` 已撤回**：
  作者串里的 `F. L.?` 是当时留下的占位符，卷期页码亦未经逐字核对即写入（**A-81**）。本条不使用该文任何
  数值或结论，只使用"时延与丢包会侵蚀闭环稳定性"这一共识命题 ⟹ 撤下猜测条目不影响 R-20 判据。
  引用登记见 KB0 §7.3 **A-81**；本条 `basis` 恒为 `rule_heuristic`（见上一行），**不得**因存在 `T2` 出处
  而升格为可外发的能力主张。
  `T2` C6 §0 表格第 3 行。
- 适用边界: `fs ≥ 1 kHz` 且 `fs ≥ 2 / 总线周期`；`quality_ref.dt_jitter_ratio > 0.05` 时放弃（A-49 镜像路径）；
  不适用于非总线架构（板卡直连脉冲式控制卡 ⟹ 丢周期语义不同，改判 R-18/R-19）。

### R-21 视觉测量结果迟到
- family: `software_induced_late_vision_result`
- 断言: 视觉结果到达时刻晚于轴运动消费它的需要时刻，导致"轴等待后突进"型误差；证据是 `vision` 事件的
  延迟分布与该工艺步内误差阶跃的时间关系。
- 判据: `event_context.available == true AND causal_claims_permitted == true`
  `AND event_context.vision_result_latency_p95_ms ≥ 20 [P]`（C2/C6 示例 31.2 ms）
  `AND event_context.n_by_source.vision ≥ 20 [P]`（分位数样本量下限）
  `AND` 存在 `step_labels` 步，其内 `tracking.path_segments[].fe_max_counts ≥ 2.0·fe_rms_counts [P]`
  （**`【比值·刻度无关】`**：同一段内峰值对自身 RMS 取比，量纲相消，与 R-19 同一条式）
  `AND` 该步的误差阶跃时刻与该步 `vision/result` 事件**对齐**：`abs(Δt) ≤ max(τ_u, 2 ms)`，
  窗口本身 > τ_u（纪律 6）；本条要 > τ_u 的是 `vision_result_latency_p95_ms` 这个**被声称的时延**，
  不是阶跃与事件的对齐残差（A-82。旧文此处写 `abs(Δt) > τ_u`，等于要求"必须不对齐才算对齐证据"，已改）
  `AND event_context.n_by_source.vision / max(event_context.n_events,1) ≥ 0.1 [P]`（视觉在该节拍中是主要事件源）
- 必要上下文: `events.jsonl` 含 `source=vision, code=result` 且带 `detail.latency_ms`（C6 示例）；
  `meta.machine_context.step_sequence` 含视觉步骤（示例 `flux_inspect`、`verify`）与 `recipe`；
  C1 视觉通道 `vision_x/vision_y/vision_angle`（15–60 Hz 降采样）；
  `segment_coverage.path` 或该步内 `move` 段；`sync.verified == true`。
- 排除项（易混淆）:
  - **R-19**：欠载在路径生成侧，与视觉事件无时间关系。
  - **R-22**：若视觉标定**值**错（不是迟到），表现为偏置/比例误差 ⟹ 走 R-22/R-27。
  - **R-06/R-05**：低速等待时的摩擦停滞，无 `vision` 事件对应且速度是锯齿而非突进。
  区分量：本规则误差形态是"静止后突进"，且必须能画出一条"视觉结果时间线 vs 运动时间线"。
- 建议动作: ①视觉结果消费改为到位后锁存 + 坐标变换（把视觉从运动关键路径移出）；
  ②缩短相机曝光-触发-识别串行链路（并行化、降 ROI、提高帧率）；
  ③工艺上把视觉步移出路径窗口或改为在线视觉伺服（架构级，标注"参数不可解决"）。
  风险：预测/前视补偿在目标真实移动时失效 ⟹ 必须标注"需人工确认"；
  `requires_offline: false`；可逆（软件流程配置）。
- 期望效果与其依据: `rule_heuristic`（方向：`vision_result_latency_p95_ms` 与该步 `fe_max` 相关强度下降）。
- 出处: `T2` S. Hutchinson, G. F. Hager, P. I. Corke, "Tutorial: Visual servo control [positioning
  and navigation of robotic manipulators using visual feedback]", IEEE Trans. Robot. Autom. 12(1), 1996
  （视觉延迟对闭环的影响与手眼/静态视觉引导分类）；
  `T2` ISO 9283:1998 *Manipulating industrial robots — Performance criteria and related test methods*
  （位姿获取/稳定时间相关条款）；
  `T2` C6 §0 表格第 4 行；`T2` C1 通道词表（视觉通道 15–60 Hz 降采样的原生限制）。
- 适用边界: `fs ≥ 200 Hz` 即可（视觉为 15–60 Hz 低频源）；不适用于无视觉事件/无视觉通道的样本；
  不适用于在线视觉伺服闭环（那时延迟是控制回路的一部分，须按 R-12/R-13 带宽判据重新建模）。

### R-22 换型流程覆盖脉冲当量 / 标定系数
- family: `software_induced_pulse_eq_overwritten`
- 断言: 同一物理运动在不同 `recipe`/`step` 下呈现**比例性**位置偏差（误差与行程成正比、与方向无关、
  无每转周期结构），根因是换型流程改写了 `counts_per_mm`、螺距补偿或标定系数。
- 判据: `event_context.available == true AND event_context.step_labels 非空`
  `AND` 同一步骤集合内 `abs(fe)` 对行程的回归斜率 `abs(β) ≥ 0.002 [P]`（即 0.2% 的比例误差，
  由 `pos_cmd`/`pos_fb` 跨步比对得到。**`【比值·刻度无关】`**：斜率是"误差 ÷ 行程"，分子分母同刻度相消 ⟹
  本条比例判据在 si_native 样本上照算，不需要 `counts_per_mm`）
  `AND encoder.per_rev_periodic_present == false`
  `AND global.backlash_estimate_counts ≤ global.fe_rms_counts`（间隙不随行程增长；
  **`【比值·刻度无关】`**，两侧同为位置原生刻度量）
  `AND` 同一 `step` 的重复定位一致（散布 `≤ 3·量化台阶` ⟹ 可重复 ⟹ 排除随机成因；
  **`【比值·刻度无关】`**，散布与台阶同刻度相消）
  `AND` 偏差随 `recipe` **阶跃**改变：`abs(M(err | recipe=A) − M(err | recipe=B)) ≥ 3·σ_err [P]`
- 必要上下文: `event_context.step_labels[].recipe`；
  `meta.machine_context.recipe/step_sequence/axis_group`（C6 §2）；
  `meta.counts_per_mm`（并需其在样本包 meta 与驱动器侧一致的说明）；
  `counts_per_mm` 的变更历史（若无则记入 `audit.assumptions`）；
  跨 recipe 的配对样本（至少 2 个 recipe 或换型前后各一组）。
- 排除项（易混淆）:
  - **R-08**（间隙）：随方向、不随行程 ⟹ 由 R-27 仲裁。
  - **R-01**（热漂）：随时间单调、与 recipe 无关。
  - **R-07**（编码器周期误差）：有每转周期结构。
  - **R-17**（量化）：无比例增长趋势。
- 建议动作: **不调整任何伺服增益**。动作是数据治理：
  ①recipe ⟶ `counts_per_mm`/标定系数映射表版本化并冻结（禁止现场随手改）；
  ②换型后强制执行标定验证序列（已知量块 / 已知步距 / 已知编码器转数），
  验证通过前禁止生产（写入 `field_procedure`，人执行）；
  ③报告必须显式声明："本报告所有 µm 数字依赖 `counts_per_mm`；该值在 recipe 间已发生变化，
  故只有 counts 基准可信"（纪律 4）；若 `counts_per_mm == null` ⟹ 只报 counts 与比例斜率。
  **（A-97 更正）**原句的后半支在 `units_are = si_native` 样本上是空转（那里既无 counts 刻度、也没有 µm 折算链）：
  正确声明改为"本报告数字一律按**该通道原生刻度**印，单位随行；`counts_per_mm` 若存在则只用于 counts↔mm 换算"。
  本条的**判据**侧不受影响——比例斜率 `β`、`3·量化台阶`、`backlash/fe_rms` 全是刻度无关写法（见上），
  换型覆盖的证据强度不依赖定标是否存在；依赖定标的只有 ②的"已知步距/量块"验证动作。
  `requires_human_approval: true`；可逆（配置级）；`requires_offline: false`。
- 期望效果与其依据: `unverified`（本规则的目的是阻止错误归因与错误定标，不给改进数字）。
- 出处: `T2` C6 §0 表格第 5 行（"轴在错误的配方下运动"，需 `machine_context.recipe/step`）；
  `T2` C6 §2（"同样的波形在不同工艺步骤下含义不同"）；
  `T2` KB0 §5 / C1 单位规则（无定标系数即不知是否微米级）；
  `T2` ISO 230-2（定位精度与重复性试验，跨条件重复性作为归属依据的思路）。
- 适用边界: 需 ≥2 个 recipe 或换型前后配对样本；不适用于单配方单一轨迹样本；
  与 `fs` 无关（几何/时域判据）；不适用于无 `step_labels` 的样本（放弃并登记 not_evaluable）。

**R-22 扩展 · 适配器口径缺陷签名表（裁决 A-33，混淆对 A-46 / CP-11）**

> **措辞纪律（硬性）**：下表六个形态一律表述为**"第三方实现审计中出现的缺陷形态"**。
> 它们是逻辑自洽的失败模式（如 `_unit` 已是 mm 再除脉冲当量必然差 1000 倍），其成立**不依赖任何手册版本**；
> 但**没有任何官方手册原文可存证**。因此**禁止**写成"手册确认的错误""官方手册原文"或"我们的发现"
> （违反即触发 C3 规则 14 的措辞越级拦截）。证据路径**只用 C2 已登记字段**（见 §1）。
>
> **末列"首次上机的验证动作"是什么性质（A-87）**：那一列不属于本表的判据，而是**约定真值的确认动作**——
> 它要确认的是"这台机器的位号/编码/换算链到底怎么接"（②④⑥行还额外依赖 `meta.counts_per_mm` 口径、
> PSO 比较源、锁存来源这些**手册/接线表事实**）。这些格**永远拿不到 `simulation_validated`**：
> KB5 注入的是我们按约定造出来的形态，用它自检只能证明管线自洽。因此本表的六个形态里，
> **中间三列（签名/混淆对/还需通道）是判据，末列是待外部确认清单**，两者在报告里不得混写；
> 末列未执行 ⟹ 相关 `recommendation` 的 `basis` 保持 `rule_heuristic` 并写 `audit.assumptions`。
>
> **本表对签名正确性没有证明力（A-88）**：末列与中间三列同源于本文件的记忆性整理，同源派生物不能反过来
> 给来源背书。故末列每行必须能填 `verified_against = {manual_id, revision, clause}`（纪律 16 ①），
> 报告侧统计 `已核对 k / 总 n`；`k = 0` 时措辞封顶"样板就绪，签名与位号未经外部核对"，
> 且**不得**用"清单已生成"抵扣上机前的工时（纪律 16 ②③）。
>
> **为什么本表不写任何厂商函数名（A-89）**：签名列只用 C2 已登记字段路径，这是纪律 16 ④ 的落地形态——
> 要写函数名 / DLL 归属 / 参数个数，先抽取（`external_reference = official-artifact`），抽不到就不写。
> 凭记忆拼出的厂商签名（`AUDIT-glm-code-factory.md` §一 列的那类：`ZAux_Direct_GetIdle/Servo`、
> `GT_GetSts(out int, …)`）属最低档 `memory`，它的危险不在"看起来不专业"，而在**不报错、不写日志、真机才炸**
> （建连即 `EntryPointNotFound`、`Open()` 第一步调一个官方不存在的函数）。本表因此把厂商接口细节一律留在
> 待核对清单里（末列），**正文判据不出现厂商函数名**——不留记忆性断言的位置，比事后核对更省代价。
> 借自 minimax 第四轮的 L1 读值→L2 低速点动→L3 单轴定位→L4 停止语义→L5 回零→L6 插补/飞拍
> 这个**分级顺序**（上级不过不进下级）写进 C6 §5，本 agent 不执行任何一级，只标注建议属于哪一级、由谁执行。

| # | 缺陷形态（第三方实现审计中出现的缺陷形态） | 波形上的可观测签名（仅用 C2 已登记路径） | 最易混淆的 KB0 §2 slug | 区分还需要的通道/元数据 | 首次上机的验证动作 |
|---|---|---|---|---|---|
| ① | 指令位置 DPOS 冒充反馈 | **第一路证据已在 C2：`feedback_integrity.{corr_pos_fb_vs_pos_cmd ≥ 0.99, fe_zero_ratio ≥ 0.9} ⟹ masquerade_suspected = true`（C2 规则 15，A-48 已裁）**；再叠加 `pos_fb` 实为指令 ⟹ 派生 `fe` 恒 ≡ 0：`global.fe_rms_counts`、`global.fe_max_counts`、`global.fe_p999_counts` 均低于 `quality_ref.quantization_step_counts`，阶跃处 `pos_fb` 与 `pos_cmd` 完全同步、无任何跟随滞后；死通道形态看 `feedback_integrity.pos_fb_static_on_move_ratio`；若有第二路反馈则 `sensor_disagreement.pairs[].rms_counts`（pos_fb vs laser_ref）反而畸大。**刻度标注（A-97/§1.13b）**：本行三个比较（`fe_rms/fe_max/fe_p999` 低于量化台阶、`corr ≥ 0.99`、`fe_zero_ratio ≥ 0.9`）全是 **`【比值·刻度无关】`**——同为该通道原生刻度量或与刻度无关的相关/占比 ⟹ si_native 样本照判；但句中"反而**畸大**"是定性词、**没有数字阈值**，两类都套不上 ⟹ **已裁 A-110 ④：`畸大` 是定性签名，不可编码、不进 `rule_table.json`、不参与成立判定**（处置见 §1.13b 表末），不在此猜一个数 | `electrical_resolution_quantization`（R-17，同样 fe≈0）；并与 A-46 CP-11「通道恒零/未接」成对（两者在单路数据上不可区分，A-48） | 第二路独立反馈（`feedback_integrity.second_feedback_available`，其源为 C1 `cross_validation.pairs` ⟹ `sensor_disagreement`）+ `present_channels` 与 `channels.*.raw_column`（判断 pos_fb 源列是不是 CmdPos） | 使能后手推轴/走一小段恒速，看 `pos_fb` 是否**完全无变化**地等于 `pos_cmd`；有 laser_ref 就比 `sensor_disagreement`。**`second_feedback_available == false` ⟹ 不得归因**，只按 A-51 键式登记 `not_evaluable`（A-46 + **A-48**，CP-11 第 3 判据由此可走通） |
| ② | `_unit` 后缀函数双重换算（已是 mm 再除脉冲当量，必然差 1000 倍） | `global.fe_rms_counts` 正常，但 `global.fe_rms_mm` 与 `global.fe_rms_counts × position_quantum_mm` 相差 1000×；`sensor_disagreement.pairs[]`（pos_fb vs 未双重换算的第二路）呈**固定 1000:1 比例**偏差（非加性、方向恒定） | `software_induced_pulse_eq_overwritten`（R-22 主判据，同为比例性偏差） | `meta.counts_per_mm` 口径 + `channels.*.unit`/换算链元数据（counts→mm 被应用两次） | 走已知物理行程（量块 / 已知转数 × `quality_ref.motor_rev_counts`），核 `*_counts` 与 `*_mm` 比值是否 = `position_quantum_mm`；差 1000× 即坐实。区分 R-22：本形态是全 recipe 恒定的 1000× 因子，R-22 是随 `event_context.step_labels[].recipe` 阶跃的斜率。**刻度标注（A-97/§1.13b）**：本行的 1000× 是**无量纲因子**（写法属比值族），但它的两个被比较对象 `*_mm` 与 `position_quantum_mm` 都**只在 `counts_per_mm != null` 时才存在**（纪律 4(a)）⟹ 该核对该列按 **`【绝对】`** 处置：无 counts 刻度时此格标"待外部确认（缺定标，1000× 核对不可执行）"，**不得**用 `counts_per_mm = 1` 之类默认值凑一个刻度出来 |
| ③ | 把 IO 电平返回值当错误码解释 | 波形侧无签名，仅在事件层暴露：`event_context.n_alarm`、`event_context.n_by_source.drive`/`.network` 与真实运动不符（电平恒高 ⟹ 持续"报警"计数，或真错误码却计 0）；`event_context.fe_spike_aligned_to_*` 与 `event_context.network_cycle_miss_count` 对不上（对齐窗内几乎没有匹配对、`alignment_residual_ms` 远超 τ_u ⟹ 计数却报"持续报警"） | `software_induced_bus_cycle_miss`（R-20，被假报警误导） | `meta.io_bits` 位定义 + 事件解析器对 IO 读数的语义（电平 vs 错误码）+ 原始 `io` 通道 | 让某 IO 位保持恒定电平，观察 `n_alarm`/事件计数是否随之错误增减；与驱动器面板/示教器实际报警态对照 |
| ④ | PSO/硬件比较输出的比较点取了 DPOS 而非反馈位置（飞拍触发点系统性偏一个跟随误差） | 触发位置记的是指令 ⟹ 触发点相对真实 `pos_fb` 系统性偏移 ≈ 触发时刻的 `fe`：`sensor_disagreement.pairs[]`（PSO 锁存位 vs pos_fb/laser_ref）的**均值**偏差量级 ≈ `abs(global.fe_mean_counts)`（恒速段的常值分量），其**波动**部分才 ≈ `global.fe_rms_counts`——`sensor_disagreement.pairs[].rms_counts` 本身是去常偏口径（A-106 ②），拿它比均值会把两个口径混掉，**A-114 就地更正**，在 `global.fe_p999_counts` 峰（减速/拐角）处偏得最多；恒速段偏差稳定、静止段（`event_context.step_labels` dwell）偏差归零。**刻度标注**：本行全部比较（均值偏差 ≈ `abs(fe_mean_counts)`、波动 ≈ `fe_rms_counts`、随 `fe_p999_counts` 增大）都是**同刻度互比** ⟹ **`【比值·刻度无关】`**，无 `counts_per_mm` 照判 | `mechanical_backlash`（R-08，固定偏置）；`software_induced_late_vision_result`（R-21） | PSO/硬件比较配置元数据（比较源 = cmd 还是 fb）+ 触发时刻 `fe` 窗 + `event_context.step_labels` | 跑一个 fe 显著增大的工况（提速 / 加重惯量），看"触发点 vs 反馈"偏差是否随 `global.fe_mean_counts`（恒速段的常值分量）与 `global.fe_rms_counts`（波动分量）同步增大——随 fe 走即口径取错，与方向相关才是间隙 |
| ⑤ | 回零后测量反馈位置未与指令位置同步（零点差一整段行程） | 回零后 `pos_fb` 与 `pos_cmd` 常量错位一整段 ⟹ `fe` 出现一个**大非零均值**（是平移不是波动）：`abs(global.fe_mean_counts)` ≈ 错位量，而 `global.fe_rms_counts`/`global.fe_p999_counts` 仍是减中心后的波动量、停在噪声地板（对纯平移**不敏感**，这正是"平移不是波动"的可观测含义），`global.fe_max_counts`（原始 `max abs(fe)`）随常偏抬升 ⟹ `fe_max ≈ abs(fe_mean) ≫ fe_rms`；**原句「`fe_max ≈ fe_p999` 且都 ≈ 错位量」把 median 中心的 `fe_p999` 也算进错位量、与 §1.1 定义自相矛盾，已按 A-114 就地更正**；`segment_coverage.homing ≥ 1` 且错位只在 homing 段之后出现；`sensor_disagreement.pairs[].direction` 指明哪一路偏高。**刻度标注**：本行的比较对象（`fe_max ≈ abs(fe_mean)`、二者 ≈ 错位量、错位"一整段"）全部是**同刻度互比或以行程为分母的相对量** ⟹ **`【比值·刻度无关】`**，无 `counts_per_mm` 照判。**段级分支没有载体**：「错位只在 homing 段之后出现」要的是**分段** `fe` 均值，而 C2 `tracking.path_segments[]` 只有 `fe_rms_counts`/`fe_max_counts`（§1.2）、没有段级 `fe_mean_counts` ⟹ 该半句在现有契约下不可编码，按 A-110 ④ 同类处置（无载体签名不进 `rule_table.json`、不参与成立判定），**不得**拿全局 `fe_mean_counts` 冒充段级均值（A-102：缺载体补载体，不许反推凑数） | `electrical_position_pi_detune`（R-14，保持误差偏置）；`mechanical_thermal_drift`（R-01，但热漂随时间渐变） | 回零事件 + `meta.io_bits.home_sensor` 位 + 第二路零点基准（laser_ref）+ homing 段内 cmd/fb 对齐检查 | homing 完成瞬间比对 `pos_fb` 跳变是否与 `pos_cmd` 同步；随后测一个已知机械 datum，用 `sensor_disagreement` 坐实零点是否差一整段 |
| ⑥ | 锁存源选错（锁到了但不是那路信号，视觉定位稳定偏一个固定量） | 锁存了另一路信号 ⟹ 视觉/锁存坐标相对真实反馈**稳定偏一个固定量**（与速度、逼近方向无关）：`sensor_disagreement.pairs[].rms_counts` 低但存在恒定 mean 偏置；`event_context.vision_result_latency_p95_ms` 正常、`event_context.fe_spike_aligned_to_vision_result` 不随之升高（说明不是"迟到"而是"错源"）。**刻度标注（A-97/§1.13b）**：本行两个签名都是定性表述（"低""恒定偏置"），文中**没有数字阈值** ⟹ 绝对/比值两类都套不上，**已裁 A-110 ⑤：`低`/`恒定 mean 偏置` 与 ④ 的 `畸大` 同为定性签名，不可编码、不进 `rule_table.json`、不参与成立判定**（处置见 §1.13b 表末）；另注意 `rms_counts`/mean 偏置后缀是历史名，真机印出按原生刻度 + 随行单位（A-97 ③） | `software_induced_late_vision_result`（R-21，同为视觉定位偏，但偏量随写回时刻速度变化） | 锁存/PSO 通道来源元数据（哪一路被锁）+ 第二路位置参考 + `event_context.step_labels` | 变换进给速度与逼近方向：偏差**恒为同一固定量**（不随 v 缩放）⟹ 锁存源选错；偏差 ∝ v（滞后 × 速度）⟹ 判 R-21。无第二路参考时只登记 `not_evaluable`（A-46） |

> 说明：本表把六个形态变成**可观测判据**，不改变 R-22 自身的主判据；表中每一路与"还需的通道/元数据"
> 即 `next_data_to_collect` 的来源。凡缺一路反馈而无法区分的形态，一律按 KB0 §6/C3 规则 9 走
> `not_evaluable`，**禁止**用单路 `pos_fb` 反推（循环论证）。

### R-23 到位判定窗口过短
- family: `software_induced_settle_window_too_short`
- 断言: 上位机"到位"判定的时间窗短于轴的实际整定需要，导致报告到位时轴仍在衰减振铃；
  表现为节拍被迫放宽（操作员诉求）而非机械故障。
- 判据: `event_context.available == true AND event_context.step_labels 非空`
  `AND median(step_response[].settling_time_ms) ≥ 1.2 × (t_done − t_start) [P]`
  （`t_done` 来自 `events.jsonl` `source=motion, code=move_done`，`t_start` 来自 `move_started`；
  该比较是"判定窗口 < 实际整定"的直接表述）
  `AND step_response[].ringing_cycles_to_settle ≥ 2 [P]`
  `AND` 到位时刻的 `abs(fe) ≥ step_response[].settle_band_counts [P]`（用 C2 路径 `global.fe_max_counts`
  与判定时刻窗对应；若窗内 `fe` 无法定位则降级 `unverified`。
  **刻度标注**：本叶是"到位时刻误差 vs 判稳带宽"的**同刻度互比** ⟹ **`【比值·刻度无关】`**；
  ⚠ 唯一继承的绝对侧风险来自 `settle_band_counts` 的**默认值**含 `20 counts` 绝对支（§1.8）——
  无 `counts_per_mm` 时默认带宽只剩 `0.02·fe_rms` 比值支，或改由工艺容差按原生刻度直接给）
  `AND step_response[].settling_time_ms != null`
- 必要上下文: `events.jsonl` 的 `motion/move_started` 与 `move_done`（C6 示例，含 `detail.settled`）；
  `step_response[]` 与 `settle_band_counts`；`meta.io_bits`（示例 `"8": "settled"`）；
  `meta.context.complaint`（示例："高速取片后末端抖动，节拍被迫从 1.8 s 放宽到 2.6 s"）；
  `segment_coverage.settling ≥ 3`；`fs ≥ 200 Hz`。
- 排除项（易混淆）:
  - **R-14**（真极限环）：`fe` 永不进入 `settle_band`；本规则是"再等一会儿就进带"。
    区分：`limit_cycle_present == true` 且 `settling_time_ms == null`（从未入带）⟹ R-14。
  - **R-24**（轮询滞后）：方向相反——R-24 判定**太晚**，本规则**太早**。两者可同时成立
    （则必须合并为一条"到位判定策略"建议）。
  - **R-03/R-09**（残余振铃由谐振激励）：需先过频带检查（R-25）；若谐振不可评估，
    本规则仍可作为**节拍侧**结论，但不得声称振铃原因是谐振。
- 建议动作: 顺序 ①提高到位判定的**条件质量**而非缩短窗口：双条件判据（带宽 + 持续时长），
  或用硬件位置比较/锁存输出替代软件判定（联动 R-24）；
  ②若工艺容差允许，增大 `settle_band`——报告必须明写这是**放宽判据**、不改善物理精度，
  并与 R-29 的余量结论联合给出；③优先降低 `settling_time_ms` 本身（陷波 R-03/R-09、整形 §3.1）。
  风险：直接放宽窗口 = 用精度换节拍，对共晶贴片落点/点胶位置这类工艺敏感项**必须**与工艺容差联评
  （`counts_per_mm == null` 时不得声称"仍在 ±X µm 内"）。
  **（A-97 更正）**本句的前提在 `units_are = si_native` 的样本上要重述：null 只代表"没有 counts 换算链"，
  不代表"不知道物理量级"⟹ 该风险联评**不能**被这一句自动免除；能否给出 µm 级容差结论受纪律 4(a) 与
  §1.13b **已裁 A-110 ②/③**约束（实测幅值可随 #39 给 µm，容差/目标数字仍禁；**该限定已于 2026-10-21 解除——#39 落码 = A-113，故本条现在可以给 µm 级实测幅值、"仍在 ±X µm 内"这类容差结论仍禁**）。无论刻度有无，本条的实质要求不变：**放宽判定窗口 = 用
  精度换节拍**，必须与工艺容差联评，只是"以 µm 数字联评"还是"以该通道原生刻度联评、单位随行"的选择
  问题（纪律 4 / A-97 ③）。
  `requires_offline: false`；可逆；`requires_human_approval: true`。
- 期望效果与其依据: `rule_heuristic`（方向：到位时刻 `abs(fe) < settle_band` 成立）；
  若经 C4 仿真证明"到位即振铃未消"并给出节拍收益 ⟹ `simulation_validated`。
  理论依据：标准二阶系统 `t_s ≈ 4/(ζωn)`（2% 判据）[L]，故窗口 < `t_s` 必然判不准。
- 出处: `T2` Dorf & Bishop, *Modern Control Engineering*（二阶系统整定时间/调节时间公式）；
  `T2` Nise, *Control Systems Engineering*（同）；
  `T2` Rockwell Automation, *Logix 5000 Motion Instructions Reference Manual*（`MC_MoveAbsolute`
  等指令的 done/位置状态判定条件）——**文档编号需复核**；
  `T2` C6 §5（恢复动作只以人执行的 `field_procedure` 存在）。
- 适用边界: 要求 `1/fs < 0.1 ×`（`fe` 首次入带到段末的时间）；不适用于无 `move_done` 事件的样本；
  不适用于连续路径运动（无"到位"概念，走 R-19）。

### R-24 到位判定靠轮询带来的叠加误差
- family: `software_induced_polling_latency`
- 断言: 到位状态由上位机按固定周期轮询读取，检测滞后与状态采样量化被叠加进定位误差预算，
  表现为到位时刻的 `pos_fb` 分布被轮询周期截断成台阶。
- 判据: `event_context.available == true`
  `AND event_context.n_by_source.motion ≥ 10 [P]`
  `AND` 轮询周期 `T_poll` = `motion` 事件间隔的中位数（`median(diff(t))`），且其 CV ≤ 0.2 [P]（说明是周期轮询而非事件驱动）
  `AND` 到位时刻散布 `std(t_done − t_enter)` ≥ `0.5·T_poll [P]`
  （`t_enter` 由 `step_response[].settling_time_ms` 与 `move_started` 时刻反推）
  `AND` 额外位移贡献 `≈ T_poll × vel`（以 counts 表达；`counts_per_mm == null` 时**不**换算 µm，纪律 4）。
  **刻度标注 +（A-97 更正）**：原句"以 counts 表达"在 `units_are = si_native` 的样本上没有落点（那里没有
  counts 刻度）⟹ 现按 A-97 ①/③ 读作"**以该通道原生刻度表达、单位随行**"；该贡献量要与 `settle_band`
  同刻度互比才成为判据 ⟹ 属 **`【比值·刻度无关】`**，本条判据**不需要** `absent_counts_scale` 降级；
  括号里"`counts_per_mm == null` 时**不**换算 µm"仍按纪律 4(a) 保留（换算链确实不存在），但它**不是**
  "该项不可评估"的理由，两者别混（µm **实测幅值**能否直接给：已裁 A-110 ②/③，随 #39 放开；µm **容差/目标**数字仍禁）
  `AND NOT (R-23 成立且其主因是窗口过短)`（否则由 R-23 主导，本规则作为次要贡献列出）
- 必要上下文: `events.jsonl` 中 `motion` 事件密集且节律等于轮询周期；
  `meta.io_bits` 的 `settled` 位（若有 `io` 通道可直接对比翻转时刻与 `fe` 入带时刻，
  差值须 > `τ_u` 才作证据，纪律 6）；`step_response[].settle_band_counts`；`fs ≥ 200 Hz`。
- 排除项（易混淆）: **R-23**（判太早 vs 采样太晚）；**R-18**（抖动是随机尖峰，本规则是**系统性偏后**，
  散布有界且等于 `T_poll`）；**R-06**（起步摩擦与到位时刻无关）。
  与 R-23 同时成立 ⟹ 上位机判定链路整体不健康，报告必须合并成一条建议。
- 建议动作: ①到位信号改事件驱动（硬件位置比较输出 / 中断锁存），从根上消除 `T_poll` 贡献；
  ②若控制卡不支持，提高轮询频率或改为两次采样一致性判定；③在误差预算表中**显式列出**
  `T_poll × vel` 这一项（counts），让工程师自行判断能否忽略；
  （**A-97 更正**：括号里的"counts"在 `units_are = si_native` 的样本上没有落点 ⟹ 按 A-97 ①/③ 读作
  "该通道原生刻度下的数值、印出须随行单位"；该动作量与 `settle_band` 同刻度互比 ⟹ 【比值·刻度无关】，
  不受 `absent_counts_scale` 阻塞，但报告层不得裸印 `T_poll × vel` 这个数字）
  ④禁止用"提高增益让轴更快入带"来掩盖采样滞后。
  `requires_offline: false`；可逆；风险低（软件侧）。
- 期望效果与其依据: `rule_heuristic`（方向：到位时刻散布 < 1 个控制周期）。
- 出处: `T2` C6 §0/§5 与 C1 `io` 位解码；
  `T2` Rockwell *Logix 5000 Motion Instructions* / Position Compare 指令文档；
  `T2` Beckhoff TwinCAT 位置比较（LCMP/CM 类）文档；
  `T2`（**条目未核对**，方向性依据，A-81）J. P. Hespanha 等的 NCS 综述（§10 第 24 条；采样保持 + 时延对闭环性能影响的理论结论）。
- 适用边界: 需 `fs` 与 `T_poll` 可比（`T_poll ≥ 2/fs`）；`n_by_source.motion < 10` 时放弃（统计量不足）；
  不适用于事件驱动架构（此时 `T_poll` 无定义，应判 R-23 或软件配置正确）。

### 交叉判别与门禁规则（R-25 … R-30）

### R-25 kHz 判据的频带不可见性与拒答义务（元规则，无参数动作）
- family: `null`（频带门禁/拒答元规则，产出登记义务而非假设 ⟹ 非叶子；KB0 §6 检查 2/3 + 裁决 A-17）
- 断言: 当 `reliable_band_hz` 不足以覆盖某判据声明的频点时，该判据必须进 `unavailable` +
  `freq_limits.blocked_rules` + C3 `differential.not_evaluable`；报告不得出现
  "未发现机械谐振/转矩纹波/高频振荡/双惯性对"一类表述。
- 判据（这是**触发**条件而非归因条件）:
  `freq_limits.reliable_band_hz < rule.band⊥` ⟹ 该规则 `skipped(reason = "band_gate: f_b < band_floor")`
  ⟹ `blocked_rules ∪= {rule_id}` ⟹ `not_evaluable ∪= {…}`，登记键按 **A-51** 两种形式取其一：
  **逐模式** `{"fault_mode": "<KB0 §2 slug>", "why": "fs 不足，该频段无信息（不代表不存在）"}`，
  **族级** `{"family": "<mechanical|electrical|software_induced_error>", "why": …}`
  （族级只在整族不可评时使用；`software_induced_error` **只能**出现在 `family` 键上，禁入 `fault_mode`。
  两种键式都必须再带 C3 规则 16（A-73）要求的 `blocked_by` 稳定键名，如 `band_gate_fs_1k`、`absent_events_jsonl`）。
  同时 `audit.rules_fired ∪= {rule_id}`（本条的产物是**登记义务**，不是假设）。
  补充触发：`spectral.*.dominant_freq_hz == null` **且** 带内 bin 数 < 8 也走同一路径（区别于"有带内数据但无峰"）。
  **A-65 数值口径（已裁）**：T1-a `fs = 1 kHz` ⟹ 奈奎斯特 500 Hz ⟹ `reliable_band_hz = 400 Hz`
  ⟹ 一切 `band⊥ = 2000 Hz` 类判据（R-03/R-04/R-10-kHz/R-11-kHz/R-12 支路 A）在本项目唯一真实数据上
  **必然**走本条路径；这是数据层面的不可达，不是"未发现"。
- 必要上下文: `freq_limits.reliable_band_hz/.nyquist_hz/.fs_hz/.blocked_rules/.reason`；
  §2.1 的 `band⊥` 表；`resonance.resolution_hz`。
- 排除项（易混淆）: 与 C1 的"数据质量红线拒答"（`insufficient_data`）不同——那是**样本不足**，
  本规则是**物理不可观测**；两者的 `not_evaluable.why` 必须措辞区分。
  与 **R-10** 不同：R-10 是"看到了但判为伪峰"，本规则是"看不到"。
- 建议动作: 无参数动作。`next_data_to_collect` 必须给出：重新采集 `fs ≥ 8 kHz`（推荐 20 kHz），
  时长 ≥ 2 s，必须包含 `dwell` 与 `rest` 各 ≥ 1 段，说明补采后解锁 `R-03`/`R-04`/`R-10-kHz`/`R-11-kHz`
  （C3 不可协商规则 5：置信 < 0.6 时该字段不得为空）。
- 期望效果与其依据: `rule_heuristic`；对应 C5 指标 **拒答正确率 ≥ 80%** 与 **无依据成功声明 = 0**。
- 出处: `T1-a` KB7 §已实测能力边界 1（两份 DaRUS 数据 `SampleTime` 恒 1 ms，"因此绝对不能用它们验证
  kHz 级机械共振判据"）；`T2` C2 硬性规则 7；`T2` C3 文档头（该例要求 `fs ≥ 8 kHz`）；
  `T2` Oppenheim & Schafer（奈奎斯特限制，无信息不可恢复）。
- 适用边界: 元规则，恒运行（`band⊥ = n/a`）；对本文件所有规则生效。
  **A-51（已裁）**：本条与 R-26/R-27/R-28/R-29/R-30 同属 `family: null` 的**边/门**，
  产物只有**登记义务**（`audit.rules_fired` + `differential.not_evaluable`，计入 C5 拒答正确率），
  **永不进 `hypotheses`**；任何把它当作假设来源的下游描述都是错的（KB4 已同步）。

### R-26 谐振 ↔ 前馈失配仲裁（C5 §6 预测的头号混淆对）
- family: `null`（仲裁器/边，只改写 R-03/R-15 的 rank 与置信上限、自身不产独立叶子；KB0 §6 检查 3 + A-17）
- 断言: 当"加减速时刻的纹波样误差"与"谱峰"同时出现时，必须按有序判据链得出唯一归属，
  禁止把两条并列成两个等权假设。
- 判据（有序链）:
  1. `resonance.candidates[].present_in_rest == true` ⟹ 电气/伪峰支（交 R-10、R-11）；
  2. `present_in_dwell == true AND coherence_torque_velocity ≥ 0.7 AND abs(A_s) < 1.5`
     （`A_s` 为 R-15 定义的有符号不对称；两侧都不显著才排除前馈 ⟹ 机械谐振（R-03 或 R-09，按频带选择））；
  3. `present_in_rest == false AND present_in_dwell == false AND ff_mismatch.fe_vs_accel_corr ≥ 0.6
     AND abs(A_s) ≥ 1.5`（**加速侧或减速侧任一占优均算前馈失配，A-26 镜像**）⟹ 前馈失配（R-15）；
  4. 2 与 3 同时成立 ⟹ 谐振为 primary、前馈为 rank 2，且**互相写入对方的 `contradicting_evidence`**；
  5. `present_in_rest == null`（无 `rest` 段）⟹ 仲裁失效，两假设置信度上限同时压至 0.55，
     `next_data_to_collect` 要求"补采静止使能 ≥1 s 段"。
     **求值顺序（A-100 附注）**：本支是**前置门**而非链尾——`rest == null` 时整条仲裁失效，
     引擎先于 1–4/6 判定它；写"自上而下首个命中即止"时不含本支的位次含义。
  6. **（A-100 补第三支的补集）** `present_in_dwell == true AND abs(A_s) < 1.5`（第 2 支因
     `coherence_torque_velocity < 0.7` 或为 null 而不成立时才走到本支）⟹ **不重排**：写
     `audit.arbitration_notes`「R-26#6：dwell == true 且不对称不显著 ⟹ 不重排」，登记后按 KB4 §2.9
     原序输出 `rank`。**缺支即登记**同样约束整条链：1–6 支全部无命中时（例 A：`dwell == true` 且
     `abs(A_s) ≥ 1.5`，两侧同时被否）写「R-26 有序链无命中」，**禁止**静默挑一支或改序。
- **分工（A-100，已裁）**：本条只在**同一 severity 档内**决定哪条规则的解释优先（有序链）；
  跨档排序一律归 KB4 §2.9 的锚点表，本条**不得**覆盖 severity 序。
- 必要上下文: `resonance.candidates` 的四个布尔/数值条件（C2 规则 6："缺一不可"）；
  `segment_coverage.rest ≥ 1 AND dwell ≥ 1`；`ff_mismatch.*` 非 null；
  `freq_limits.reliable_band_hz`（决定候选是 R-03 还是 R-09）。
- 排除项（易混淆）: 本规则就是仲裁器，**不得**单独产出建议动作；
  它只能改写 R-03/R-15 的 `rank` 与置信上限，且置信度**数值**由 KB4 加权公式决定
  （C3 不可协商规则 3：LLM 只能改措辞不能改数值）。
- 建议动作: 无参数动作。输出为排序 + 置信上限 + `contradicting_evidence` 互记。
- 期望效果与其依据: `rule_heuristic`；评测目标：C5 §6 混淆矩阵中该混淆对占比下降。
- 出处: `T2` C5 §6（明文预测该混淆对并要求单独强化判别条件）；
  `T2` C1 §segments 说明（"位置指令静止时不出现的峰是区分机械共振与前馈失配的关键条件"）；
  `T2` C2 规则 6；`T1-a` DaRUS `kff = 1.5`（前馈支路的真实样本，但该数据无谐振故障，
  故本仲裁的谐振侧只能由 T1-b/T2 支撑）。
- 适用边界: 恒运行；`band⊥ = n/a`；`rest` 或 `dwell` 段缺失时失效（第 5 支）。
  **A-51（已裁）**：`family: null` 的**边/门（仲裁器）**，只改写被仲裁叶子的 `rank`/置信上限并登记
  （`audit.rules_fired`、必要时 `not_evaluable`），**自身永不进 `hypotheses`**。

### R-27 间隙 ↔ 换型覆盖脉冲当量仲裁
- family: `null`（仲裁器/边，把偏差改判到 R-22 或 R-08 叶，自身不是叶子；KB0 §6 检查 3 + A-17）
- 断言: 反向出现的固定偏差默认由机械间隙解释；仅当该偏差随 `recipe` 阶跃变化且与行程成正比时，
  必须改判软件侧标定覆盖，不得开机械整改单。
- 判据:
  `IF (encoder.per_rev_periodic_present == false AND 误差/行程回归斜率 abs(β) ≥ 0.002 [P]
      AND 偏差随 recipe 阶跃（R-22 判据第 6 条）) ⟹ 归 R-22（software_induced_pulse_eq_overwritten）`
  `ELSE IF (偏差仅在反向后出现 AND 与行程无关 AND 幅值重复 CV ≤ 0.3) ⟹ 归 R-08（mechanical_backlash）`
  `ELSE ⟹ 两者均不成立 ⟹ 进 differential.considered，hypotheses 不得含二者`
- 必要上下文: `event_context.step_labels[].recipe`；`counts_per_mm` 及其跨样本变化；
  `global.backlash_estimate_counts` 的平台条件（§1.1）；`segment_coverage.move ≥ 2`；
  `meta.machine_context.recipe`。
- 排除项（易混淆）: **R-01**（热漂随时间、与 recipe 无关）；**R-07**（有周期结构）；
  **R-17**（量化台阶，无比例增长）。
- 建议动作: 归 R-22 ⟹ 数据治理动作（冻结映射表 + 换型后标定验证，见 R-22）；
  归 R-08 ⟹ 机械整改 / 反向补偿 `backlash/2`（见 R-08）。
  **两者互斥执行**，报告不得同时给两种工单（这是可复核性的关键：同一证据不能既判机械又判软件）。
- 期望效果与其依据: `unverified`（仲裁规则，只给方向）。
- 出处: `T2` KB0 §2（两 slug 并列、语义正交）；`T2` C6 §0 表格第 5 行；
  `T2` ISO 10791 / ISO 230-2（跨条件重复性作为归属依据的试验思路）；
  `T2` C1 单位规则（无定标系数不得下 µm 结论）。
- 适用边界: 需 `event_context.step_labels`；无 recipe 信息时退化为 R-08 单独判据
  并在 `audit.assumptions` 记录该退化（不得静默）。
  **A-51（已裁）**：`family: null` 的**边/门（仲裁器）**，产物是"归谁"的改写 + 登记义务，
  **本条自身永不进 `hypotheses`**。第 3 支（两者均不成立）的登记形式：
  `differential.considered` 是**字符串数组**（只放 KB0 §2 slug 或显示名，不带动作），故写
  `"mechanical_backlash"`, `"software_induced_pulse_eq_overwritten"`；
  若因缺 `step_labels` 而整支不可评，才进 `differential.not_evaluable`，按 A-51 两种键式（并带 C3 规则 16 / A-73 的 `blocked_by`）：
  逐模式 `{"fault_mode": "<KB0 §2 slug>", "blocked_by": …, "why": …}`、
  族级 `{"family": "<族名或 software_induced_error>", "blocked_by": …, "why": …}`。

### R-28 软件族内互斥仲裁（线程抖动 / 插补欠载 / 总线丢周期 / 视觉迟到）
- family: `null`（族内互斥仲裁器/边，择优到某 `software_induced_*` 叶，自身不是叶子；KB0 §6 检查 3 + A-17）
- 断言: 同一尖峰集合不能同时归因于多个软件成因；必须按事件源独占性与对齐质量择优，
  区分度不足时"无法区分"是合法结论。
- 判据: 定义（全部来自 C2 已登记路径）
  `s_host = fe_spike_aligned_to_host_pause / max(fe_spike_count, 1)`
  `s_intp = fe_spike_aligned_to_underrun / max(fe_spike_count, 1)`
  `s_net = fe_spike_aligned_to_network_miss / max(fe_spike_count, 1)`
  `s_vision = fe_spike_aligned_to_vision_result / max(fe_spike_count, 1)`
  —— 四路对齐计数已随 **A-9** 全部落进 C2 `event_context`（旧文写 `s_net = null`/`s_vision` 同理为 null、
  只能两路择优，那是 G-5/G-9 未收口时的状态，**已作废，已裁 A-9**）；
  两个字段为 `null` 时（计数无从算，如 `events.jsonl` 无对应 source）该路不参与择优并登记 `not_evaluable`。
  择优：`max(s_host, s_intp, s_net, s_vision) ≥ 0.5 [P]` **AND** `max − second ≥ 0.2 [P]` **AND**
  `alignment_residual_ms ≤ sync.uncertainty_ms`（即 τ_u）（**A-82 方向，更正 A-50**：残差是匹配对
  `abs(Δt)` 的中位数，**落在**不确定度预算内才算同步可信；残差超出预算的对齐按 C6 §3 硬规则 2 /
  纪律 6 **不得作因果证据**，只能共现）**AND** `causal_claims_permitted == true`。
  **`software_induced_bus_cycle_miss` 一路还须满足 R-20 的三条件（A-45）**，与 KB4 §1.3 N6.c / CP-10 /
  §2.5 CAP-11 **逐字同调**（canonical 文本即 R-20 判据内的那一段，四处必须完全一致）：
  1. `event_context.bus_cycle_hold_max_ms != null` **且** `event_context.fe_spike_aligned_to_network_miss != null`
     （即"单周期指令保持时长"与"尖峰对齐丢周期计数"两路专属证据都在）；
  2. `event_context.sync.verified == true` **且** `event_context.causal_claims_permitted == true`；
  3. 对齐残差 `event_context.alignment_residual_ms ≤ event_context.sync.uncertainty_ms`。
  ⟹ 三条件齐：**可进 `hypotheses[]`，但 `confidence ≤ 0.6`**（本结论是单通道 `pos_cmd` 平台推断，
  无驱动器侧 WKC 计数通道佐证，不得更自信；**这一路上限就是 0.6，不会因为本仲裁器择优胜出而抬高**）。
  ⟹ 缺任一条件：**只到共现级**，**禁入 `hypotheses[]`**，该 fault_mode 只进
  `differential.considered`；本仲裁器仍照常给出 `s_*` 排序，但排序结果只能作为"哪一路更像"的说明，
  不得据此写成归因。报告措辞"共现，因果未确立"。
  （已裁 A-45 / A-50，方向由 **A-82** 更正）
  否则：本族**不得**产出任何归因，`software_induced_*` 全部候选进 `differential.considered`，
  并在 `not_evaluable` 登记"对齐区分度不足"。
- 必要上下文: `event_context.sync.method != "unknown"`；`n_by_source.{host,interp,network,vision}`；
  `segment_coverage.path`（欠载语境）；`fs ≥ 1 kHz`；`τ_u <` 尖峰间最小间隔。
- 排除项（易混淆）: 与 **R-02**（机械冲击，无事件对应 ⟹ `s_*` 全低时应考虑机械族，
  但不得因此直接归机械，须走 R-02 自身判据）；与 **R-15**（与 `a` 平滑相关）。
- 建议动作: 输出为"上位机侧整改候选"而非参数动作；`requires_human_approval: true`、
  `requires_offline: false`、可逆（软件配置）。
- 期望效果与其依据: `rule_heuristic`。
- 出处: `T2` C6 §0 表格（三类成因的波形表现与所需上下文一一对应）；
  `T2` C6 §3（同步纪律是"本契约存在的全部理由"）；`T2` Kopetz 2011；`T2` Sha 等 1990；
  `T2` Cervin 2003。
  **A-51**：本条 `family: null`，是**边/门（仲裁器）**，产物是择优结果与**登记义务**
  （`audit.rules_fired` + `differential.not_evaluable`，计入 C5 拒答正确率），
  **自身永不进 `hypotheses`**；被本条压回的候选按 A-51 键式登记：族级
  `{"family": "software_induced_error", "why": …}`、逐模式 `{"fault_mode": <KB0 §2 slug>, "why": …}`。
- 适用边界: `fs ≥ 1 kHz` 且 `τ_u` 有界；无 `events.jsonl` 时不运行（由 R-30 登记）；
  `s_net`/`s_vision` **已可用**（A-9），但仍受 A-45 三条件与 `confidence ≤ 0.6` 封顶约束，
  不得因 C2 增补了字段就默认升级到高置信。

### R-29 节拍可压缩性评估（衍生规则，不判故障）
- family: `null`（衍生/评估类，不产 `hypotheses[].fault_mode` ⟹ 非叶子；KB0 §6 检查 3 + A-17）
- 断言: 报告"节拍可压缩量"之前，必须证明压缩后到位时刻误差仍在容差内；
  即整定时间由物理约束决定，而非由判定窗口决定。
- 判据: `segment_coverage.settling ≥ 3 AND median(step_response[].settling_time_ms) != null`
  `AND` 理论整定下限 `t_s_min = 4/(ζ·ωn)`（2% 判据 [L]）；`ζ = step_response[].damping_ratio_estimate`，
  `ωn = 2π·bandwidth.position_loop_crossover_hz`（H1 估计，`confidence ≤ 0.6` ⟹ 本规则结论**上限 `unverified`**）
  `AND median(step_response[].settling_time_ms) ≥ 1.2·t_s_min [P]`（存在可压缩空间）
  `AND step_response[].settle_band_pct_of_move` 在工艺容差内（`counts_per_mm == null` ⟹ 用 counts 判定）
  （**A-97 更正**：括号里的"用 counts 判定"在 `units_are = si_native` 的样本上不成立 ⟹ 那里根本没有 counts
  刻度可判；`settle_band_pct_of_move` 分子分母同刻度相消，本就是 **`【比值·刻度无关】`** 的一支，
  **不需要** `counts_per_mm` 存在即可判；真正需要 counts 刻度的是 `settle_band_counts` 的绝对阈那一支，
  它在 `counts_per_mm == null` 时按 §1.13b 记 `blocked_by = absent_counts_scale` 单独降级）
- 必要上下文: `step_response[].damping_ratio_estimate`、`bandwidth.*`、
  `meta.counts_per_mm`（若为 null，禁止输出 µm 级容差结论，纪律 4）
  （**A-97 更正**：本句把 `counts_per_mm == null` 当成"刻度缺失"来禁止 SI 结论，前提在该样本上不成立 ⟹
  该样本 `units_are = si_native`，读数本身就有确定 SI 量纲（A-97 ①），null 表示的是"没有 counts 换算"
  而**不是**"不知道物理量级"；null 真正阻塞的是**绝对 counts 阈**那一支与"裸印 `*_counts` 当作 counts"
  的报告口径，见 §1.13b。至于本报告能否据此直接印 µm 级数字：受纪律 4(a)（`*_mm` 特征在 null 时恒 null）
  与 §1.13b **已裁 A-110 ②/③**（实测幅值随 #39 可给 µm、容差/目标数字仍禁）这一约束，落点 C2 规则 3、不在本文件
  （**A-113：该落点已于 2026-10-21 落码 ⟹ 上一行的"纪律 4(a) null 时恒 null"此后只对 `units_are = counts` 成立，
  si_native 长度通道由 C2 规则 3 支②直接定标；容差/目标数字的禁令不变**）⟹ 结论仍是"µm 级容差结论要么有工艺容差
  直接给的原生刻度值、要么不下"，不得自己造换算）、
  `event_context.step_labels`（把整定时间折进节拍预算）。
- 排除项（易混淆）: **R-23**（判据窗太短，是判定错误）；本规则是"物理上还能多快"的预算问题。
  **R-03/R-09**（振铃由谐振主导 ⟹ 压缩空间必须靠陷波/整形取得，不能靠放宽判定）；
  **R-17**（量化主导 ⟹ `t_s` 下限被测量噪声决定）。
- 建议动作: 优先级 ①先取机械/前馈收益（R-03/R-09/R-15）；②再考虑 ZV 整形（`t_d = 0.5/f_d`，
  代价是净延迟 `+t_d`，须从收益里扣 [L]）；③最后才考虑放宽 `settle_band`（并注明是判据放宽）。
  每条建议必须给出**净节拍变化**的方向与依据层级；数字仅在 `simulation_validated` 时给出。
  `requires_offline: true`；本规则不产生任何下发行为（`safety.writes_to_device = false`）。
- 期望效果与其依据: `unverified`（因 `bandwidth.confidence ≤ 0.6`）；
  有 C4 V* 时可 `simulation_validated`。
- 出处: `T2` Dorf & Bishop / Nise（`t_s ≈ 4/(ζωn)`）；
  `T2` Singer & Seering 1990 与 Singhose 2000（输入整形的净延迟代价）；
  `T1-a` 限制：DaRUS 无 `settling` 段语义与节拍概念（绳索试验台），本规则在 T1-a 上**不可评估**。
- 适用边界: 需 `fs ≥ 200 Hz` 与 ≥3 个 `settling` 段；不适用于连续路径（`path`）为主的设备。
  **A-70 说明（已裁）**：本条出现的 `step_response[].settle_band_pct_of_move` 与 `overshoot_pct`
  分母是**行程幅值** `move_amplitude`（运动学百分比），与额定转矩无关，
  因此**不受** A-70 的 `rated_torque_N_m` / `rated_torque_source` 分母纪律约束；
  只有转矩刻度类 `*_pct`（`cur_q_*_pct`、`cur_q_saturation_ratio`、`torque`/`cur_cmd` 的 %）受约束。
  **A-51（已裁）**：`family: null` 的衍生/评估门，产物是预算结论 + 登记义务，
  **不产 `hypotheses[].fault_mode`**，自身永不进 `hypotheses`。

### R-30 软件族不可评估的登记义务（元规则）
- family: `null`（登记义务元规则，产出 `not_evaluable` 登记而非假设 ⟹ 非叶子；KB0 §6 检查 3 + A-17）
- 断言: 缺 `events.jsonl`（或 `available == false`）时，`software_induced_*` 全族必须逐条登记进
  C3 `differential.not_evaluable`，并在报告首页的"能力/边界"块出现；沉默是违规。
- 判据: `event_context.available == false`（或 `event_context` 整体为 null）
  ⟹ `not_evaluable` 按 **A-51** 两种键式**同时**登记：
  **族级** `{"family": "software_induced_error", "blocked_by": "absent_events_jsonl", "why": …}`
  （**用 `family` 键**：族级标签不是 slug，A-18/A-51），`why` 取 C6 §4 原文
  "无事件上下文，无法区分机械尖峰与调度抖动"；
  **逐模式** 对 R-18…R-24 每条叶各写一行
  `{"fault_mode": "<KB0 §2 slug，如 software_induced_bus_cycle_miss>", "blocked_by": "absent_events_jsonl", "why": …}`；
  ⟹ 同时 `rules_skipped ∪= {R-18,…,R-24,R-28,R-29(若依赖 step_labels)}`、`audit.rules_fired ∪= {R-30}`；
  ⟹ `verdict.overall_confidence` 必须相应下调（下调因子按 C3 规则 16 / A-73 取
  **去重后的 `blocked_by` 个数**，不是登记行数；族级行与它覆盖的叶同源，只计一次），
  不得保持"看起来更有把握"（C3 不可协商规则 9）。
  第二条触发路径：`available == true BUT causal_claims_permitted == false`
  ⟹ 全族**降为共现报告**，`not_evaluable` 仍须登记（措辞改为"时钟未对齐，因果不可断"，
  `blocked_by` 换稳定键名如 `sync_unverified`）。
  **A-51（已裁）**：本条与 R-25/26/27/28/29 一样是 `family: null` 的**门**，
  产物是**登记义务**（`audit.rules_fired` + `differential.not_evaluable`，计入 C5 拒答正确率），
  **永不进 `hypotheses`**；KB4 描述"边/门"时若写成"产出假设"即为错，须按本条口径。
- 必要上下文: `event_context.available`、`sync.verified`、`sync.method`、`sync.uncertainty_ms`；
  `differential.considered` 的完整性；C5 评测的 `none_of_the_above` 案例类（"仅有波形、无事件上下文"）。
- 排除项（易混淆）: 与 **R-25**（频带不可见）同为元规则，但不可见对象不同：一个是频率，一个是成因。
  两者必须**同时**登记，不得以其中一个代替另一个。
  与 **R-10**（有数据但判为伪峰）不同。
- 建议动作: `next_data_to_collect`：①导出上位机/控制器日志为 `events.jsonl`（C6 §1 词表，
  一行一事件）；②提供共用触发沿或 NTP 对齐证据以置 `sync.verified = true`；
  ③说明时钟源与不确定度。补上后解锁 R-18…R-24、R-28（C3 规则 5 的"unlocks"字段）。
- 期望效果与其依据: `rule_heuristic`；对应 C5 指标"拒答正确率"与"无依据成功声明 = 0"。
- 出处: `T2` C2 硬性规则 8（`available == false` 必须显式登记，不得沉默）；
  `T2` C6 §4（同一义务与登记文本）；`T2` C3 不可协商规则 9（`not_evaluable` 不得为空数组）；
  `T2` C5 §2/§3（`none_of_the_above` 案例 ≥15%，专测过度自信）。
- 适用边界: 恒运行；`band⊥ = n/a`。

---

## 3. 阈值合法化

### 3.1 文献可证阈值（`[L]`）

| 阈值 | 陈述 | 出处（书/论文/手册，可检索条目） | 复核状态 |
|---|---|---|---|
| 陷波中心频率 | `f_c` = 实测峰频（不做整数化、不做名义值替代） | Yaskawa Σ-7《机械系统调整手册》陷波条目（`Pn1101` 陷波 1 频率）；Panasonic MINAS A5/A6 `FP1`（陷波频率） | 条目名可信，**参数号需复核** |
| 陷波宽度 | `Δf ∈ [f_c/3, f_c/2]` | Panasonic `FQ1`（衰减）/`FRQ1`（宽度/Q）条目 + 通用双惯性陷波实践；Beckhoff 机械谐振抑制文档 | **需复核**：厂商文档多用"带宽比"而非 `f_c/3`；本文件把它写成显式带宽并要求复述定义 |
| 陷波 Q 起点 | 用 Q 参数化时 `Q = 30` 起，逐步放宽 | Yaskawa 转矩滤波器（`Pn1120` 频率 / `Pn1121` Q）实践："从窄（高 Q）开始" | 见 §3.2 说明：**两种参数化不可互比**（`Δf = f0/Q` ⟹ Q=30 对应宽 `f0/30`，与 `f_c/3` 相差 10 倍）；报告必须写明所采用定义 |
| 陷波深度 | −20 dB（起点） | 无通用文献值 ⟹ 实际归 `[P]`，此处仅说明"深度过大会显著削减相位裕度"的定性依据来自 Franklin & Powell（非最小相位/陷波的相位代价） | **不列为文献阈值** |
| 双惯性第二陷波 | 双惯性系统需在 `2·f_c`（或反谐振频点）加第二陷波 | Leonhard, *Control of Electrical Drives*, 3rd ed., §级联控制/双质量；Kempf et al., IEEE Control Systems Magazine 13(3), 1993；Yaskawa/Panasonic 双质量陷波条目 | 条目名可信，**章节需复核** |
| 谐振/反谐振比与**顺序** | 共置（电机侧执行器+电机侧反馈）两惯量系统 `f_anti < f_res`，且 `f_res/f_anti = sqrt(1 + J_l'/J_m)`；本文件采用 `f_res/f_anti ∈ [1.05, 2.7]`（对应 λ ∈ [0.01, 6.3]，λ < 0.2 时配对不可分辨 ⟹ 不得判双惯性） | 两惯量传递函数的极点/零点交替（positive-real / Stodola）性质：Leonhard, *Control of Electrical Drives*（双质量章节）；Kempf 1993；本项目推导见 KB5 §1.2（`f_m/f_a = sqrt(1+λ)`） | 顺序结论可信且**必须采纳**；本文件已按它改写 R-04/R-09。**C2/C3 示例的 `antiresonance_freq_hz = 1420 > freq_hz = 1181` 与该物理矛盾**，见 §5 G-13 |
| 电流环带宽 | `f_i ≥ 10·f_v`（电流环 ≥ 10× 速度环） | H. Butler, "Considerations in the Servo Drive Feedback Design for Machine Tools"（级联环带宽分离）；Vienna Power Electronics 电流控制讲义；I. J. Busada & S. R. Suh（最优电流控制带宽） | 10× 是工程通则，**具体出处段落需复核** |
| 速度环带宽 | `f_v ≥ 10·f_pos`（速度环 ≥ 10× 位置环） | Butler；Rockwell《Strictly Servo》级联分配实践 | **需复核** |
| 位置环带宽 | `f_pos ≈ Kv/5 ~ Kv/8`（`Kv` = 速度环路增益，单位 s⁻¹）；对称最优（Symmetrisches Optimum）给出 `f_pos ≈ Kv/4` 的下界形式，取 5~8 是噪声/谐振余量的保守化 | 对称最优整定：A. Kaudewig / R. Gattermayer 传统，工程化表述见 Leonhard 1996 及 SIEMENS SINAMICS S120 闭环手册 | **需复核**：`Kv/5~Kv/8` 是制造商实践数值带，未见单一权威页码 |
| 稳定裕度 | `PM ≥ 45°`、`GM ≥ 6 dB` | Franklin, Powell & Emami-Naeini, *Feedback Control of Dynamic Systems*（PM 典型 30–60°，工程取 ≥45°）；Dorf & Bishop, *Modern Control Engineering* | 教科书共识，可信 |
| 惯量比 | `< 5` 理想、`5–10` 需陷波/整形、`> 10` 参数整定不可靠 | Yaskawa / Beckhoff / Kollmorgen 调谐指南（惯量比与可调带宽关系）；C3 示例 `inertia_ratio_fitted = 6.2` 落在"需陷波"档 | **需复核**：不同厂商阈值不同（部分写 5、10、20）；本项目取 5/10 并要求逐台标定 |
| 阻尼与整定 | `t_s ≈ 4/(ζωn)`（2% 判据）；`ζ ≈ (1/2π)·ln(x_1/x_2)`（对数衰减率） | Nise, *Control Systems Engineering*；Dorf & Bishop | 教科书，可信 |
| ZV 输入整形 | `K = exp(−ζπ/sqrt(1−ζ²))`，脉冲间隔 `t_d = 0.5/f_d`，幅值比 `1 : K : 1`（归一 `1/(1+K) : K/(1+K)`） | N. Singer, W. E. Seering, "Preshaping Command Inputs to Reduce System Vibration", ASME J. Dyn. Syst. Meas. Control 112(1), 1990；W. E. Singhose, "Command generation for flexible systems", Automatica 36(4):595–611, 2000 | 可信（ZV 标准公式） |
| 加速段误差 | `e ≈ a/ωn²`（`a` 恒定加速段准稳态跟随误差，`ωn` 位置环自然频率） | 由一阶近似推导：`T(s) ≈ ωn²/(s² + 2ζωn s + ωn²)`，对 `a` 分量的低频频响 `≈ a/ωn²`；同类表述见 Butler 与《Strictly Servo》的前馈讨论 | 推导可自证（**允许用 C4 仿真核验**，属 `[L]` 的近似条件：`ζ ≲ 0.7` 且加速时长 `> 3/ωn`） |
| 峰/本底 6 dB | 纯音/模态可辨识度门限（`amplitude_ratio_vs_broadband ≥ 4` = 6 dB） | ISO 10843:1997（离散纯音成分检测，峰值-均值比）；Vattino et al. 2016 | 声学领域标准，跨用到伺服谱判定属类比，**需复核**其在本领域的适用性表述 |
| 相干门限 | `γ² ≥ 0.7`（FRF/相干可信） | Bendat & Piersol, *Random Data: Analysis and Measurement Procedures*（相干作为传递函数可信度判据；`γ² < 0.5` 视为不可信） | 可信（0.7 是本项目在 0.5 之上的收紧，见 §3.2） |
| H1 有偏性 | 输入含噪/闭环时 H1 系统低估，需 H2/H∞ | Bendat & Piersol；Stroebe（频率响应估计的偏差族） | 可信（这是 `bandwidth.confidence ≤ 0.6` 的核心依据） |
| 摩擦：突破/维持比 | stiction 比、Stribeck 速度、预滑动位移的形态学依据 | Olsson et al. 1998；Armstrong-Hélouy et al. 1994；LuGre（Canudas de Wit et al., *The Art of Motor Control in the Presence of Friction*, IEEE Control Systems Magazine 2001） | 可信；具体 `1.5` 门限属 `[P]` |
| 编码器误差 | 一阶/多阶谐波建模、每转锁定相位 | Bao et al. 1993；Heidenhain（Lehwehe）插值误差补偿；Heidenhain TNC DRWA 长度误差补偿 | 谐波建模可信；`0.2·fe_rms` 门限属 `[P]` |
| 失动/摩擦试验 | 反向失动与摩擦效应的测量方法 | ISO 230-3:1996；ISO 10791 系列 | 标准存在可信，**part 号需复核** |
| 采样/混叠 | `f_b = f_N/1.25`、近奈奎斯特谱不可信 | Oppenheim & Schafer, DTSP；C2 规则 7 | 可信 |
| 实时/抖动 | 任务抖动、优先级反转对控制性能的退化机制 | Sha, Rajkumar & Lehoczky 1990；Buttazzo, *Hard Real-Time Computing Systems*；Cervin 2003（博士论文） | 机制可信；`20 ms`/`0.7` 等数值属 `[P]` |
| 网络控制系统 | 丢包/丢周期对稳定域的收缩 | Hespanha 等的 NCS 综述（§10 第 24 条）；Kopetz 2011 | 机制可信，**条目未核对**（卷期页码已撤，A-81） |
| EtherCAT | 分布式时钟、周期完整性、WKC | ETG.1000.2 系统规范；Steiner（ETG 论文） | 规范号需复核 |
| 视觉伺服 | 视觉延迟的闭环影响、静态视觉制导 vs 视觉伺服 | Hutchinson, Hager & Corke, IEEE Trans. Robot. Autom. 12(1), 1996 | 可信 |
| 机器人性能试验 | 位姿获取/稳定时间测试方法 | ISO 9283:1998 | 标准存在可信 |

### 3.2 本项目自定阈值（`[P]`）——初值 + 标定方法

下列数值**没有**文献直接背书，是"按 C2/C3 示例数据反量定的初值"，**必须在 T1/T2 数据上重标定**。
标定协议（统一）：①在开发集（60%，C5 §2）上以 ROC/Youden 选点；②隐藏集（40%，冻结
`bench/hidden.sha256`）只做一次评估，**不得**针对其失败案例回调阈值（C5 §2 明文）；
③每个阈值记录 `hit / false_hit / miss` 三计数并进入 C5 混淆矩阵；④阈值变化必须升版本号并公开前后差异。

| 阈值 | 初值 | 定标依据 / 标定方法 |
|---|---|---|
| `reversal_error_counts / fe_rms` | 3.0 | KB0 §3 示例判据锁定为 3 倍；在 T2（合成，间隙参数取自厂商手册）上扫 2–5 选 F1 峰值。**`【比值·刻度无关】`**：分子分母同为位置原生刻度 ⟹ 相消，`counts_per_mm == null` 时照算（§1.13b 约定，A-97 ④） |
| `backlash` 重复性 CV | ≤ 0.3 | 按 ISO 10791 的重复性思路；在有多反向段的 T1-a/T2 上取反向估计量的 CV 分布 50 分位。**`【比值·刻度无关】`**（CV 无量纲） |
| `friction_stiction_ratio` | ≥ 1.5 | DaRUS `LdaFricIdent` 给出 τ 从 7→60 N·m 的真实跨度、C2 示例 1.9；取 1.5 为"低于典型健康机台"的保守下界，需在 T1-a 全战役上算正常分布的 P95 后重定 |
| `tonality_index`（谐振/纹波侧） | ≥ 0.6 | 锚点：C2 示例 0.62/0.71。方法：在 KB5 合成上以"注入单模态 vs 不注入"做两类分布，取等错误率点 |
| `tonality_index`（非谐振侧） | ≤ 0.5 | 与上条互补，保留 0.1 灰区（灰区内两判据都不给归因，交 R-26） |
| `dominant_psd_ratio` | ≥ 0.30 | 锚点 C2 示例 0.41；需在 fs=1 kHz 与 fs=8 kHz 两组上分别标定（能量占比随带宽变化，跨采样率不可共用） |
| `coherence_torque_velocity` | ≥ 0.7 | Bendat & Piersol 建议 >0.5 才可信；本项目收紧到 0.7 以配合 C3"每条假设 ≥2 证据"；在 T1-b 上验证收紧不损失召回 |
| `quality_factor_estimate` | ≥ 10 | 由 `Δf_(−3dB) ≤ f0/10` 反推，保证峰宽 > 2× `Δf`（分辨率约束）；与 `resolution_hz ≤ 5 Hz` 联立标定 |
| `fe_p999 / fe_rms`（尖峰性） | ≥ 4 | 高斯时约 3.3；取 4 表示显著重尾。在 T1-a 触发过滤后的 `fe` 上先算健康分布基线再定。**`【比值·刻度无关】`** |
| 尖峰幅值 CV（松动） | > 0.4 | 与 R-08 的 CV ≤ 0.3 配对，中间 0.3–0.4 为灰区（不给归因）。**`【比值·刻度无关】`**（CV 无量纲） |
| 尖峰/反向 move 比 | ≥ 0.8 | 按"每次反向都该有"的物理预期定，需在 `segment_coverage.move ≥ 4` 的样本上统计。**`【比值·刻度无关】`**（计数之比，与刻度无关） |
| `爬行频率带` | `[0.1, 50] Hz` | 上界 50 Hz 取自常见黏滑固有频率经验（**不是文献值**）；需按设备类别分档：滚珠丝杠 / 直线电机 / 绳索各一档。★**已裁 A-95**：本窗降级为**回退值**——`position_loop_crossover_hz != null` 时改用 `≤ 2.0·f_pos` |
| 爬行频率常数性 CV | ≤ 0.3 | R-05 与 R-07 的分水岭；在 KB5 上分别注入摩擦与编码器误差，比较两组 CV |
| `vel_min_ratio` | ≤ 0.15 | 与 `stall_count ≥ 1` 冗余，避免单次采样噪声误判。**`【比值·刻度无关】`**（`vel` 与 `vel_cmd` 同刻度相消） |
| `stall` 定义 | `<0.01·abs(vel_cmd)` 持续 ≥ `max(3T_s, 5 ms)` | 与量化底噪相关；在 T1-a（DaRUS 恒速段）上按噪声地板重定。**`【比值·刻度无关】`**：速度门限是比值；持续时长属时间刻度，与本约定无关 |
| `asymmetry_ratio` | ≥ 1.5 | 锚点 C2 示例 2.26；需在 T1-a 的 `kff = 1.5` 真实工况上标定"正常不对称"分布（KB7：`kff=1.5` 是研究前馈失配的天然样本），取分布 P90。**`【比值·刻度无关】`**（加/减速段同类量的比） |
| `fe_vs_accel_corr` | ≥ 0.6 | 在 T1-a 上 `Torque_based` / `Velocity_based` 两套目录分别标定（KB7：同一工况两种控制结构，相关系数天然不同，**不得混标**）。**`【比值·刻度无关】`**（Pearson r 与刻度无关） |
| `Ω_acc`/`Ω_dec` 最小样本 | 50 | 统计功效约束（相关系数估计的标准误 ≈ `1/sqrt(n-3)`）；`a_min = 0.05·max abs(a)` 同源（**`【比值·刻度无关】`**：`0.05` 乘的是同一加速度序列自身的峰值） |
| `per_rev_amplitude / fe_rms` | ≥ 0.2 | 锚点：C3 示例的排除逻辑用了"23%"，故 0.2 是本项目的通过/排除分界；需在 T2（合成编码器误差幅值已知）上重定。**`【比值·刻度无关】`**；但"每转"这一分转基准（CPR/分辨率是否相符）⟹ **已裁 A-110 ①**：`si_native` + 无 `counts_per_mm` 时分转基准无定义，本比值算不出来，按 `absent_counts_scale` 登记而非猜一个 CPR |
| `detrended_r2` | ≥ 0.5 | 5 阶谐波拟合的解释度下限；在 KB5 上以"仅量化噪声"样本为负例设定 |
| 相位锁散布 | ≤ 30° | 与跨转数 ≥4 联立；负例为 R-05（相位不锁定） |
| `ringing_cycles_to_settle` | ≥ 5（R-13）/ ≥ 2（R-23） | 前者判失谐、后者判节拍，两条分开标定 |
| `damping_ratio_estimate` | ≤ 0.2（失谐）/ ≥ 0.5（前馈规则要求） | 教科书 ζ 分档 + C3 示例 0.28 作为"不命中失谐"的锚点 |
| `limit_cycle_freq / f_pos` | 偏差 ≤ 0.5 | 频率归属容差；受 H1 估计置信 0.6 限制，本条只能作必要条件不作充分条件。★**已裁 A-95**：本条升为 R-14 频率归属的**主判据**（等价写法 `f_lc ∈ [0.5, 2.0]·f_pos`）；原绝对窗 `≥ 20 Hz` 降为 `f_pos == null` 时的回退值 |
| `limit_cycle_waveform` 判别（R-05 ↔ R-14） | 过零间隔 CV ≤ 0.25 ⟹ `sinusoidal`；CV ≥ 0.5 且有停-走 ⟹ `sawtooth` | **已裁 A-95 新增**，本项目自定 `[P]`，无文献背书。它是 R-05/R-14 的**主判别键**（形状键），频率只作辅证；灰区（形状键两侧都不满足）不给归因 |
| `limit_cycle_amplitude / settle_band` | ≥ 0.5 | 与工艺容差耦合；`counts_per_mm == null` 时只按 counts 比。**`【比值·刻度无关】`**（同刻度相消）。 ★**A-97 更正**：原句"`counts_per_mm == null` 时只按 counts 比"在 `units_are = si_native` 的样本上无落点（那里没有 counts 刻度）⟹ 应读作"只按**该通道原生刻度**比、单位随行"；比值照算，不因缺刻度而作废 |
| 量化台阶相关（R-17） | `≥0.3·settle_band`、`sign_change ≥ 0.25·fs`、`tonality ≤ 0.25` | 三条联立；在 KB5 上以 `encoder_lines` 扫描生成 ROC。**`【比值·刻度无关】`** 三条皆然：`0.3·settle_band` 与被测量同刻度（但**跟随 `settle_band` 所取那一支**——若取默认**绝对**支且该支被 `absent_counts_scale` 阻塞，则本条只降这一支，不整条作废）、`sign_change` 是率÷`fs`、`tonality` 无量纲 |
| 反谐振比（R-09 低频，`f_res/f_anti`） | `[1.1, 2.0]` | 低频传动链的收紧（kHz 档 R-04 用 `[1.05, 2.7]`，且两者都要求 `f_anti < f_res`）；需在 DaRUS 卷筒版（`ratio=5.0`）与直驱版（`ratio=1.0`）对照上重标 |
| `f_rms` 门限（`f_min`） | `max(2Δf, 1 Hz)` | 分辨率驱动，非物理选择 |
| `fe_spike` 检出 | `> max(5·MAD, 0.25·fe_p999)` | 稳健尺度 5σ 等价；在 T1-a 触发过滤数据上按假阳性率 ≤ 1/s 重标。**`【比值·刻度无关】`**：两个门限都是同一 `fe` 序列自身尺度的倍数，与 `counts_per_mm` 无关 |
| `s_host/s_intp` 择优 | `≥0.5` 且差 `≥0.2` | 区分度门限；无文献值，靠 KB5 注入两类事件做混淆矩阵标定 |
| `host_pause_max_ms` | ≥ 20 ms | 依赖 `meta.drive.position_loop_period_us`（C1 示例为 null）；一旦有真实周期值，改为 `≥ 5×周期` 为主判据 |
| `vision_result_latency_p95_ms` | ≥ 20 ms | 锚点 C2/C6 示例 31.2 ms；需按相机帧率分档（15/30/60 fps 各一档） |
| `n_by_source.vision` | ≥ 20 | 分位数估计的样本量下限（与 C1 `n_samples ≥ 2000` 红线同精神） |
| 比例误差斜率（R-22） | `abs(β) ≥ 0.002` | 0.2% 比例偏差对应"换型后必查"级别；需按目标设备（贴片/点胶/耦合）分别设定，**当前值无依据**。**`【比值·刻度无关】`**（β 是无量纲斜率：分子分母同刻度相消） |
| recipe 阶跃 | `≥ 3·σ_err` | 3σ 惯例（非文献条目）。**`【比值·刻度无关】`**（门限取该序列自身的 σ 尺度） |
| 判定窗 vs 整定 | `settling_time ≥ 1.2×(t_done − t_start)` | 20% 余量；与 `t_s = 4/(ζωn)` 联合验证 |
| 轮询散布 | `std ≥ 0.5·T_poll`；`T_poll CV ≤ 0.2` | 前者判"被轮询截断"，后者判"确为周期轮询"；在 T1-a 无对应数据 ⟹ 只能 T2 标定 |
| `kff` 调整步长 | `kff_new = kff_old·(1 − (asymmetry_ratio − 1)·0.5)`，每步 ±10% | **线性启发式，非文献**；必须在 KB5 内核上做闭环验证后才可写入报告，否则仅给方向（`rule_heuristic`） |
| 反向补偿量 | `backlash_estimate_counts / 2`（搜索范围 0.5–2× 实测） | 失动分半的常规做法（属工程实践，无标准页码）；需 C4 仿真验证不诱发极限环。**`【绝对】`但属"动作量"不是"判据阈"** ⟹ 不受 `absent_counts_scale` 阻塞：实测 `backlash` 与 `fe` 同刻度，除 2 后仍是该原生刻度下的数；报告须随行单位、不得裸印 `*_counts`（§1.13b 约定第 5 条） |
| `settle_band` 默认 | `max(20 counts, 0.02·fe_rms)` | 纯项目默认；报告须写明"默认值，非实测定标"。**两支必须分开处理（A-97 ④，与 §1.8 同一口径）**：`20 counts` 是 **`【绝对】`** 字面 counts 常数 ⟹ `counts_per_mm == null` 时**不得**当作 20 m 用、该支记 `blocked_by = absent_counts_scale`（理由固定句「无 counts 刻度，绝对阈值不可比」）；`0.02·fe_rms` 是 **`【比值·刻度无关】`** ⟹ 照算。默认取 max 时若绝对支缺席，按"缺席 ≠ 通过"（纪律 1）只用比值支并显式声明窗口来源 |
| 反演式前馈估计（`*feedforward_pct_applied`） | 见 §1.9 公式 | **本项目提出的反演估计，无文献背书**：它依赖"反馈支路可分离"假设，而闭环中该假设仅在 `f_pos` 已知时成立。因此该字段默认 null，且任何引用它的证据必须 `unverified` |

**参数化冲突的显式处理**（必须保留在报告模板里）：
陷波宽度有两条互不通用的表述——`Δf = f_c/3 ~ f_c/2`（带宽比参数化）与 `Δf = f_c/Q, Q = 30`（Q 参数化），
数值上相差一个数量级。任何输出必须写明采用哪一种、并给出等价的 `Δf`（Hz）绝对值，
否则"宽度 470 Hz、Q 2.5"（C3 示例）与"Q 30"会被内行一眼看出不自洽
（C3 示例的 `470/1181 ≈ 0.40` 对应 `Q ≈ 2.5`，属**带宽比参数化**，与 Q=30 不矛盾但必须写清）。

### 3.3 `blocked_rules` 生成的机器可读形式（说明性伪代码，非产品实现）

```
# 文档级伪代码（说明性，非产品实现，KB0 §6 检查 6）
for rule in R:
    if rule.band_floor == None: continue
    if freq_limits.reliable_band_hz < rule.band_floor:
        blocked_rules.add(rule.id)
        unavailable.append({feature: rule.asserted_frequency_feature,
                            reason: "f_b=%.0f Hz < 需要的 %.0f Hz" % (f_b, rule.band_floor)})
        not_evaluable.append({fault_mode: rule.owner_slug, blocked_by: "band_gate_fs_1k",
                              why: "采样率不足，该频段无信息（不代表不存在）"})
        # A-51 键式：逐模式用 {"fault_mode": <KB0 §2 slug>, "why": …}；
        # 整族被门禁时另加一条族级 {"family": <机械/电气/software_induced_error>, "why": …}；
        # 族级标签 software_induced_error 绝不允许出现在 fault_mode 上（A-18/A-51）。
        audit.rules_fired.add(rule.id)   # 门/边的产物是登记义务，永不进 hypotheses（A-51）
        forbid_text("未发现"/"无"/"未见")   # 措辞门禁
```

---

## 4. 出处登记表（按 tier 汇总，供 C5 报告首页"证据层级声明表"直接引用）

**T1-a（DaRUS 真实测量，fs = 1 kHz，CC BY 4.0，须署名 Reichenbach / University of Stuttgart + DOI）**
- `LdaFricIdent`、`PreloadedLuGreFrictionIdent/Validation`、`PreloadedViscousFrictionIdent`、
  `DynCapstanFrictionIdent` ⟹ R-05、R-06、R-15。
- `TempSlip` ⟹ R-01、R-16 ——**注意（A-64/A-65，已裁）**：这里只是"数据集里存在该战役、试验台具备温度测量"，
  **本项目拿到的 T1-a 样本（`Export 10.csv`）无 `temp` 通道、也无冷/热机配对轨迹**，
  所以 R-01（`mechanical_thermal_drift`）与 R-16（`electrical_motor_heating`）在 T1-a 上**没有正例来源**，
  `TempSlip` 不得作为这两条的命中率/验证层引用，只能作为"该成因真实存在"的背景说明。
- 明文控制器参数 `kff = 1.5`、`kp/ki/kd`、低通 0.02 s ⟹ R-15、R-12、R-13（阈值合法化的对照）。
- 卷筒版 `gear ratio = 5.0` vs 直驱版 `ratio = 1.0` ⟹ R-04、R-09（惯量/柔性环节对照）。
- 三套独立位置测量（`x_T` / `x_asco_enc` / `x_lsv_enc`）与现成差值通道（`x_diff`、`v_diff`）
  ⟹ 传感器交叉验证类特征（**当前 C2 无对应字段**，见 G-7）。
- 恒速段（`F30000/F120000/F300000` = 0.5/2/5 m/s）⟹ R-07、R-11、R-12 的 `ripple.probing[]`。
- **不能证明**：kHz 共振（`f_b` = 400 Hz）、电流环带宽（同属高频）、故障归因（受试对象健康）、
  半导体设备外推、编码器偏心 / 接线错误 / 增益过高自激（KB7 明文）、
  **热漂移 `mechanical_thermal_drift` 与电机发热 `electrical_motor_heating`（无 `temp` 通道、无冷热机配对）**。
  ⟹ 因此 R-03/R-04/R-08/R-11(kHz)/R-12/R-14/R-18…R-24 **不得**引用 T1-a 作为验证层；
  R-01/R-16 不得引用 T1-a 作为**正例来源**（出处里那条 `T1-a` 仅指数据集能力，见上一小节）。
  **A-65 报告侧口径（已裁）**：这类"数据层面不可达"的判据在 T1-a 样本上的产物只能是
  `unavailable` + `freq_limits.blocked_rules` 登记（R-25 路径），
  **禁止**输出"未发现谐振 / 未发现异常 / 无热漂移 / 带宽充足"。

**T1-b（外部故障真值：CWRU 轴承 / Paderborn CM 三相电流 / Aalto 齿轮 / MFPT）**
- ⟹ R-02、R-11（电气 vs 机械分类）、R-07（阶次谱范式）、R-10（谱特征真伪辨识范式）。
- **不能证明**：位置环/跟随误差/整定建议能力（无位置通道，C5 §T1-b）。

**T2（文献 / 厂商手册）**：见 §3.1 全表 + §4.1。

**T3（本项目合成，KB5）**：仅证明管线跑通，**不构成任何准确率或有效性声明**（KB0 §4、C5 §1）。
**A-64（已裁）**：对 kHz 量级共振/电流环带宽（R-03/R-04/R-10-kHz/R-11-kHz/R-12）与
`mechanical_thermal_drift`/`electrical_motor_heating`（R-01/R-16）这几族，
凡原先以 T3 合成结果充当"能力证据"的表述（如"仿真已验证可消除 1181 Hz 谐振"），
一律降级为**"管线跑通（合成自洽）"级**主张；合成内核按被测模型造，不构成外部正例。
本文件中没有任何一条规则以 T3 作为唯一出处（若有，即为违规，须删除）。

### 4.1 文献与手册清单（本文件引用到的全部条目）

1. H. Butler, *Considerations in the Servo Drive Feedback Design for Machine Tools*（1987；2008 修订在线版）。
2. W. Leonhard, *Control of Electrical Drives*, 3rd ed., Springer, 1996。
3. C. Kempf, W. Kobayashi, H. Tanaka, T. Yamada, "Resonance Control of a Dual-Mode Composite Structure",
   *IEEE Control Systems Magazine* 13(3), 1993。
4. N. Singer, W. E. Seering, "Preshaping Command Inputs to Reduce System Vibration",
   *ASME J. Dynamic Systems, Measurement, and Control* 112(1), 1990。
5. W. E. Singhose, "Command generation for flexible systems", *Automatica* 36(4), 2000。
6. H. Olsson, K. J. Åström, C. Canudas de Wit, M. Gäfvert, P. Lischinsky,
   "Friction Models and Friction Compensation", *IEEE Control Systems Magazine* 18(3), 1998。
7. B. Armstrong-Hélouy, P. Dupont, C. Canudas de Wit, "A survey of models, analysis tools and
   compensation methods for the control of machines with friction", *Automatica* 30(7), 1994。
8. C. Canudas de Wit, A. Olsson, K. J. Åström, "A new model for friction control", 及
   *The Art of Motor Control in the Presence of Friction*, IEEE Control Systems Magazine, 2001。
9. G. F. Franklin, D. Powell, A. Emami-Naeini, *Feedback Control of Dynamic Systems*, 8th ed., Pearson。
10. R. C. Dorf, R. H. Bishop, *Modern Control Engineering*, Pearson。
11. S. D. Nise, *Control Systems Engineering*, Wiley。
12. A. V. Oppenheim, R. W. Schafer, *Discrete-Time Signal Processing*, Pearson。
13. J. S. Bendat, A. G. Piersol, *Random Data: Analysis and Measurement Procedures*, Wiley。
14. J. Bao, S. Meng, C. Tsai, C. C. Lee, "Error analysis of digital servo systems with correction
    through computation", *IEEE Trans. Ind. Electron.* 40(2), 1993。【卷期需复核】
15. D. A. Neyer, "Effects of quantization noise on high-resolution optical encoders",
    *IEEE Trans. Ind. Electron.* 36(2), 1989。【卷期需复核】
16. P. H. Lehwehe / HEIDENHAIN, 光栅插值误差与长度误差补偿（DRWA / TNC 文档）。
17. J. Holtz, "Pulsewidth Modulation for Power Electronic Converters",
    *IEEE Trans. Power Electronics* 24(12), 2009。
18. D. M. Holmes, T. A. Lipo, *Pulse Width Modulation for Power Converters*, Wiley-IEEE, 2003。
19. I. J. Busada, S. R. Suh, "Optimal Bandwidth Current Control for AC Power Supplies"
    （及后续 PWM 整流最优带宽论文）。【标题/卷期需复核】
20. L. Sha, R. Rajkumar, J. P. Lehoczky, "Priority inheritance protocols: An approach to real-time
    synchronization", *IEEE Trans. Computers* 39(9), 1990。
21. G. C. Buttazzo, *Hard Real-Time Computing Systems: Predictable Scheduling Algorithms and
    Applications*, Springer。
22. A. Cervin, *Systems Modeling and Real-Time Control*, PhD thesis, Lund Institute of Technology, 2003。
23. H. Kopetz, *Real-Time Systems: Designing for Predictable Performance*, Springer, 2011。
24. J. P. Hespanha 等，网络化控制系统综述一类文献（"A survey of recent results in networked control
    systems", *Proceedings of the IEEE*）。【标题/年份/卷期均未逐字核对 ⟹ **条目未核对**，方向性依据；
    原写 `95(2)` 与作者串 `G. Nair, F. L.?` 占位符无支撑，已撤（**A-81**）】
25. W. Steiner, "EtherCAT Technology and Performance", ETG 年会论文。【标题/年份未逐字核对 ⟹
    **条目未核对**，方向性依据（A-81）】
26. EtherCAT Technology Group, ETG.1000.2 *EtherCAT System Specification Part 1000.2*。【编号需复核】
27. S. Hutchinson, G. F. Hager, P. I. Corke, "Tutorial: Visual servo control",
    *IEEE Trans. Robotics and Automation* 12(1), 1996。
28. ISO 9283:1998, *Manipulating industrial robots — Performance criteria and related test methods*。
29. ISO 230-3:1996, *Test code for machine tools — Determination of effects of friction*。【part 号需复核】
30. ISO 10791 系列, *Acceptance test code for computer numerical control machine tools*。【part 号需复核】
31. ISO 10843:1997, *Acoustics — Method for detecting and analysing discrete tonal components*。
32. E. Vattino et al., "A comparison between time and frequency domain techniques for the detection
    of tonal components in noise", *Acta Acustica united with Acustica* 101(1), 2016。【作者列表需复核】
33. YASKAWA, Σ-7 / ΣW-3 *Mechanical System Tuning Manual*（陷波 `Pn1101/Pn1102`、
    转矩滤波 `Pn1120/Pn1121`、振动抑制控制 `Pn1140/Pn1141/Pn1142`、刚性等级）。【参数号需复核】
34. PANASONIC, MINAS A5/A6 *伺服电机设置手册*（`FP1/FQ1/FRQ1`、双质量陷波、刚性等级 No.19）。【需复核】
35. BECKHOFF, TwinCAT 3 TF5100 / TE5960（Motion Scopes / 机械谐振与振荡抑制、陷波配置、
    惯量比与调谐指南）。【模块号/章节需复核】
36. ROCKWELL AUTOMATION, N. Emery, *Strictly Servo — Understanding and Using the Servo Systems in
    ControlLogix and FlexLogix Motion Controllers*；*Logix 5000 Motion Instructions Reference Manual*。【编号需复核】
37. SIEMENS AG, *SINAMICS S120 Closed-Loop Control Function Manual*（三环结构、速度环 P/I、位置环 CAS）；
    *SINUMERIK Advance Prediction Control (APC)*。【参数号需复核】
38. FANUC, *AI Contour Control*（前瞻缓冲块、拐角减速）。【文档号需复核】
39. KOLLMORGEN, 伺服选型与调试/热设计技术文档。【编号需复核】
40. Reichenbach, T., *Measurement data for: Development of a Cable Actuator Test Rig…*
    (DARUS-3600, DOI 10.18419/DARUS-3600) 与 *Measurement Data for Experimental Modeling of
    Synthetic Fiber Ropes…* (DARUS-5171, DOI 10.18419/DARUS-5171)，CC BY 4.0（KB7 已核验）。

---

## 5. 已知缺口与需主线程裁决的不一致（不许静默处理）

| 编号 | 冲突/缺口 | 本文件的处置 | 需要的裁决 | 收口（第二轮裁决，逐行标注；行不删） |
|---|---|---|---|---|
| G-1 | C1 的 `cur_q` 单位是 **A**，而 C2 的字段名是 `cur_q_rms_pct`（%） | §1.1 用 `rated_current_a` 归一并如实登记；报告须说明口径 | 主线程决定：改 C2 字段名，或在 C1 加 `cur_q_norm_pct` | 已裁：A-14（契约侧已改：C1/C2 采双字段 `cur_q_rms_a` + `cur_q_rms_pct`，`_pct` 需 `meta.rated_current_a` 才非 null，C2 规则 3） |
| G-2 | C6 §4 列 `event_context.host_pause_count`，C2 JSON 未落字段 | 本文件所有规则**不引用** `host_pause_count`（KB0 §3：C2 里没有的路径不允许出现在证据里），改用 `n_by_source.host` + `host_pause_max_ms` | 在 C2 增补该字段，或从 C6 删除 | 已裁：A-8（**不采纳新增**：`n_by_source.host` 已覆盖，C6 侧停止引用；本文件维持不引用，§1.12 该行仍标"规则不得引用"） |
| G-3 | `ripple.probing[].dominant_period_counts_per_rev = 1.0` 与 `motor_rev_counts = 524288` 量纲不合（`counts/rev` 不可能为 1） | 判据一律用**阶次 `k`**（每转周期数）表达，不把这个字段当 counts 数值比较；§1.4 已写明 | 确认该字段语义是"阶次"并改名（如 `dominant_order_per_rev`），或给出真实 counts 数值 | 已裁：A-11（契约侧已改：C2 改名 `dominant_order_per_rev`，语义即阶次；KB3 侧本文件 §1.4、§1.15、R-07 已逐处改引用） |
| G-4 | `quality.quantization_step_counts` 在 C1 `quality` 里，**不在 C2**；但 R-17/R-07/R-08 都需要它 | 作为 `necessary_context`（可写叙述），**不作为** `supporting_evidence[].feature`；已在 §1.7 / §1.8 / §1.13 处标注 | 在 C2 增补 `quality_ref` 或把量化台阶登记为正式特征 | 已裁：A-10（契约侧已改：C2 落 `quality_ref.quantization_step_counts`；KB3 侧本文件 §1.13b 已登记，R-07/R-08/R-14/R-17 证据路径已从 `quality.` 改为 `quality_ref.`） |
| G-5 | R-20 需要的"总线单周期指令保持"特征在 C2 不存在 | ~~R-20 判据被限制为**共现级**，显式禁止归因（见 R-20 判据第 3 条与 R-28 的 `s_net = null`）~~（旧处置随 A-9/A-45 作废：`s_net` 已可算） | 在 C2 增补 `bus_cycle_hold_count` / `fe_spike_aligned_to_bus_miss` | 已裁：A-9 + A-45 + **A-50**（契约侧已改：C2 已落 `bus_cycle_hold_max_ms`、`fe_spike_aligned_to_network_miss`；KB3 侧 R-20 已改为**三条件升级规则**——齐则进 hypotheses 且 confidence ≤ 0.6，缺任一回到共现级；R-28 的 `s_net` 已按 A-9 恢复为可算量并把三条件原文写入，方向按 **A-82**（更正 A-50）取 `alignment_residual_ms ≤ sync.uncertainty_ms`） |
| G-6 | `event_context` 缺"尖峰对齐 recipe 变更 / 视觉步"的专属字段 | R-22/R-21 只能用 `step_labels` + `latency_p95` 间接判 | 增补 `fe_spike_aligned_to_recipe_change`、`fe_spike_aligned_to_vision_result` | 已裁：A-9（契约侧已改：C2 已落 `fe_spike_aligned_to_recipe_change`、`fe_spike_aligned_to_vision_result`；本文件 §1.12 已登记，R-22 签名表已引用） |
| G-7 | KB7 强调 DaRUS 三套独立位置测量可做 `sensor_disagreement` 类特征，但 **C2 无该字段** | 本文件不引用；在 §4 T1-a 处标注为"待落契约" | 在 C2 增补 `sensor_disagreement`（`x_T` vs `x_asco` vs `x_lsv`）后，R-07/R-17 可获得更强证据 | 已裁：A-6（契约侧已改：C1 `cross_validation.pairs`/`extra_channels` + C2 `sensor_disagreement`；本文件 §1.13b 已登记，R-22 签名表以 `sensor_disagreement` 为主判据） |
| G-8 | R-12 需要 `meta.drive.current_loop_bandwidth_hz`，C1 `drive` 块未列该字段 | R-12 支路 A 在该字段缺失时自动走支路 B 并降 `unverified` | 在 C1 `drive` 增补该字段 | 已裁：A-42（契约侧已改：C1 `drive.current_loop_bandwidth_hz` 已增；KB3 R-12 必要上下文已改述为"字段已在 C1，为 null 时走支路 B 并降 unverified"） |
| G-9 | `fe_spike_aligned_to_vision` / `…to_bus_miss` 缺失（同 G-5/G-6），使 R-28 的四路择优退化为两路 | 已在 R-28 明文限制 | 同上 | 已裁：A-9（四路对齐字段已落 C2 ⟹ R-28 可恢复四路择优；但 `s_net`/`s_vision` 的归因仍受 A-45 三条件与因果开关约束，未自动升级） |
| G-10 | C2 规则 8 与 C3 示例使用的 fault_mode 词表不完全一致：C3 的 `differential.considered` 里有 `feedforward_mismatch`、`friction_crawling`、`encoder_eccentricity`、`thermal_drift`、`gain_too_high_hunting`、`limit_cycle`、`following_error Compensation` 等**非 KB0 §2 slug** 的写法 | 本文件一律用 KB0 §2 的 `mechanical_*/electrical_*/software_induced_*` 全量 slug；C3 示例的旧词视为"显示名"，须由 KB4 建立别名映射 | 主线程在 KB0/KB4 加"显示名 ↔ slug"别名表，否则 C5 的真值标签会对不上 | 已裁：A-19（C3 规则 10：`hypotheses[].fault_mode` **强制 KB0 §2 slug**，显示名只进 `display_name`/`considered`；`software_induced_error` 为族级标签，禁入 fault_mode，见 §6） |
| G-11 | R-05/R-14 的频率分界（2 Hz / 20 Hz）是本项目自定的连续分档，边界样本会翻转结论 | **已裁 A-95**：主判别键改为形状键（`limit_cycle_waveform` + `stall_count` / `present_in_rest` + 幅值比），频率降为辅证；`f_pos != null` 时频率归属只用相对窗（R-14 `[0.5,2.0]·f_pos`、R-05 `≤2.0·f_pos`），`f_pos == null` 时才回退绝对窗 `[20,f_b]` / `[0.1,50]` 且整体 `unverified` + 置信封顶 0.55；`2<f_lc<20` 且形状键两侧都不满足 ⟹ 两条都不触发，`verdict = insufficient_evidence`；已在两条规则里互写排除项，并保留灰区（不给归因） | 若需更严，可改为"按 `f_pos` 与 `f_rev` 动态定义"而非固定 Hz | **已裁：A-95**（KB0 §7）。真实病灶是 20–50 Hz **重叠区**而非"固定 Hz"本身：绝对下限在 `f_pos` 低的机器上误拒、在 `f_pos` 高的机器上过松，与 R-14 自带的相对判据重复 |
| G-12 | `expected_effect.basis = simulation_validated` 在软件族上原则上不可获得（KB5 若未建模 host 停顿/欠载） | R-18…R-24 一律 `rule_heuristic`；已在族级纪律里写明 | 决定是否在 KB5 内核加入"事件注入"（停顿/欠载/丢周期）以支持仿真验证 | 已裁：A-43（KB5 已建模事件注入 + 孪生样本 ⟹ 检出类判据**可** `simulation_validated`，改进量恒 `rule_heuristic` + caveat"仿真不含真实调度器与总线仲裁"；已写入族三族级纪律，R-18 期望效果已同步） |
| G-13 | **反谐振/谐振顺序冲突**：C2 与 C3 的示例数值给 `antiresonance_freq_hz = 1420 > freq_hz = 1181`，而 KB5 §1.2（以及 Leonhard / Kempf 的两惯量极点-零点交替结论）要求共置（电机侧执行器 + 电机侧反馈）时 `f_anti < f_res`，且 `f_res/f_anti = sqrt(1+λ) ≥ 1`。示例数值只能由"负载侧反馈/非共置构型"解释，但 C1/C2 没有传感器构型字段 | 本文件已按物理事实取 `f_anti < f_res` 为**强制**判据（R-04 第 2 条、R-09、§1.3 搜索窗 `[0.4·f0, f0]`、`is_double_inertia_pair` 定义、§3.1 行）；"峰 + 更高频谷"的组合在 R-04 排除项里列了 4 种非两惯量解释（结构局部模态、测点反相、数字低通附加相位、估计伪峰），一律**不得**判双惯性 | 主线程二选一：(a) 把 C2/C3 示例的 `1181/1420` 改为满足 `f_anti < f_res` 的数值（如 `antiresonance_freq_hz = 940`，此时 `f_res/f_anti = 1.26 ⟹ λ ≈ 0.58`，与"带宽比 0.40 的双陷波对"仍能自洽）；(b) 在 C1 增加 `meta.sensor_config ∈ {colocated, load_side_feedback}`，并让 R-04 在 `load_side_feedback` 下允许反向顺序。当前示例若无 (b)，会被 R-04 直接判为不配对 | 已裁：A-1（契约侧已改：C1 增 `meta.sensor_config ∈ {motor_side, load_side, unknown}`、C2 规则 9；C2/C3 示例改 `440/1181`（λ≈6.2，与 KB5 P-B 自洽）；KB3 侧 R-04 已引用 `meta.sensor_config`，`unknown` 时顺序项不判且置信封顶。**追加已裁：A-68** —— `sensor_config` 由三值升为**四值** `{motor_side, load_side, mixed, unknown}`，`mixed` 表示"已知本曲线的峰与谷来自两套通道、不是同一传递函数"，行为与 `unknown` 相同（顺序项不参与判定、置信度封顶）但**记录的原因不同**（`mixed` = 已知零极点交替信息不存在）；逐通道落点是 C1 `meta.channels.<pos>.sensor_side ∈ {motor, load, unspecified}`；KB5 原先"混合构型临时写 `unknown` + `assumptions`"的处置**作废**。已同步到 R-04（判据/必要上下文/适用边界）与 §1.3 `antiresonance_freq_hz`、`is_double_inertia_pair` 两行。） |
| G-14 | **已裁：A-79（契约侧已改）** —— C2 规则 7 定为"规则或规则支路"粒度：裸规则号 = 整条不可用，`R-11#switching_freq` = 仅该支路，且每个条目须在 `unavailable[]` 有对应 `rule`/`branch` 行；例 B 改为 `["R-03","R-04","R-11#switching_freq"]`，`R-10`（假峰检测器，必须运行）与 `R-25`（门禁自身，落点在 `audit.rules_fired`）移出。本文件纪律 2 同步删去 `R-10`。**原冲突描述保留如下**：：示例值为 `["R-03","R-04","R-10","R-11","R-25"]`，但 §2.1 里 R-10 是"n/a、必须运行"、R-11 只有 kHz 分支 blocked（低频分支 150 Hz 可评）、R-25 是**门禁本身**（无 `band⊥`，不该被自己阻塞，正确落点是 `audit.rules_fired`） | 本文件按 §2.1 的 `band⊥` 表动态生成 `blocked_rules`，实现期以本表为准；已在 §2.1 的 R-10/R-11/R-25 三行就地标注出入 | 主线程把 C2 例 B 改为 `["R-03","R-04","R-11"]`（或按分支粒度写 `R-11kHz`），并把 `R-25` 移到 `audit.rules_fired`；同时补 `R-12` 的支路 A | **已裁：A-79（契约侧已改，本行原"待主线程"作废）** —— C2 例 B 现为 `["R-03","R-04","R-11#switching_freq"]`，`R-25` 已移出到 `audit.rules_fired`；`R-12` 支路粒度按 §2.1 `band⊥` 表在实现期生成，不在示例里硬写 |
| G-15 | **已裁：A-80（契约侧已改）** —— C1 `meta.drive` 已增 `current_limit_a` + `current_limit_source`（可选、缺省 `null`、来源四档同 A-70），它是该比值的**唯一合法分母**；`1.0·rated_current_a` 兜底保留但须 (i) 进 `audit.assumptions`、(ii) 特征行标 `denominator_basis: "assumed_rated_current"`（不用 `method`，该键已被 C2 规则 5 占用为估计方法）、(iii) 只作定性支路、层级封顶 T2、**不得单独触发归因**。★ **本行原描述的偏差方向已修正**：额定当代 ⟹ `I_lim` 偏小 ⟹ 比值**偏高**（把正常满载误判成饱和），原写"低估方向"含糊。原始缺口描述保留如下：A-70 已给 `meta.drive.rated_torque_N_m` + `rated_torque_source`，但 `cur_q_saturation_ratio` 的另一半分母 `meta.drive.current_limit_a` **曾不在 C1 `drive` 块**里 | §1.1 该行原写"C1 无此字段 ⟹ 取 `1.0·rated_current_a` + `audit.assumptions`"；A-70 的层级封顶只约束转矩百分比侧，电流侧曾按 A-14/C2 规则 3 | 在 C1 `drive` 增 `current_limit_a`（已落，A-80） | **已裁：A-80**（契约侧已改 + 本文件 §1.1 行已改） |
| G-16 | **A-97 遗留的四族判不了**（不是本文件能自裁的）：①阶次族的**折叠基**（"每转"要以 `CPR = meta.axis.motor_rev_counts`（counts/rev）为自变量，而位置通道在 `si_native` 样本上是原生 SI 刻度且 `counts_per_mm == null` ⟹ 两者之间没有换算）；②`*_mm` 特征定义式（`fe_rms_counts / counts_per_mm`）能否改由原生 SI 刻度直接填，关系到纪律 4(b)、R-23 建议动作、R-24 判据⑤、R-29 必要上下文里"无刻度禁 µm 结论"这一族的存废；③R-22 签名表①/⑥ 两处**只有定性词、没有数字阈值**的签名（"反而畸大""rms 低但恒定 mean 偏置"）无法归类；④绝对支能否改用 SI 字面常数表达（本文件不自造新数字） | 全部登记在 §1.13b **待人工复判清单**（4 族 / 5 行），本文件按 A-97 ④ 就低处置：比值支照算、绝对支一律 `blocked_by = absent_counts_scale`、判不了的一律**不猜**（不新增 `blocked_by` 键、不新增数字、不改 C2 字段语义） | 主线程待办（**A-110 已逐条答复**）：(a) 给"每转基准缺换算"一个词表键 ⟹ **不新增键**，归既有 `absent_counts_scale`；(b) 裁 `*_mm` 的定义式 ⟹ 特征侧允许由原生 SI 刻度直接定标（纯定标不造数），落点 C2 规则 3 = **#39**；(c) ③ 若要成为判据，数字须由外部基准/工艺容差给出，不能由 KB3 造 ⟹ 维持该口径：实测幅值可给、容差/目标数字仍禁 | **已裁 A-110（2026-10-21 主线程，尺子＝要不要新造数字）**：①④⑤ 当场裁（不新增 `blocked_by` 键、三条定性签名永不进 `rule_table.json`）；②③ 裁方向、落点 C2 规则 3 ⟹ **任务 #39**，#39 落地前本文件与引擎行为不变。本轮未改任何既有判据语义。**A-113 补记（2026-10-21）：#39 已落码 ⟹ "行为不变"只描述 A-110 那一轮；自此特征侧 `*_mm` 由原生 SI 刻度直接定标、纪律 4(a)/(c) 按 ②/③ 收窄，**阈值与既有判据语义仍未变**（`absent_counts_scale` 的门与句式原样）。|

---

## 6. KB0 §6 引用完整性自查结果（本文件级，按 KB0 §6 现行 7 条重跑）

1. **KB3 引用的每个特征路径在 C2 存在（KB0 §6 检查 1）**：§1 全部表格行 + §1.15 倒排表逐条对照 C2 JSON。
   本轮已把三处"叙述里的量"升格为正式 C2 证据路径并登记：`quality_ref.quantization_step_counts`/`quality_ref.motor_rev_counts`、
   `sensor_disagreement.pairs[].*`（A-10/A-6，见 §1.13b）、`event_context.{bus_cycle_hold_max_ms,
   fe_spike_aligned_to_network_miss, fe_spike_aligned_to_vision_result, fe_spike_aligned_to_recipe_change}`（A-9，见 §1.12）。
   **追加（A-49）**：`quality_ref` 是 C1 `meta.quality` 的**镜像**，其完整值域为
   `{quantization_step_counts, motor_rev_counts, dt_jitter_ratio, nan_ratio, gap_max_s, source}`；
   证据路径**一律走 C2 `quality_ref.*`**，不得写 C1 的 `quality.*`（后者只作 `necessary_context` / 输入通道）。
   §1.13b 已按此补齐三行，R-15/R-17/R-20 与 §1.15 的 `quality.dt_jitter_ratio` 已改 `quality_ref.dt_jitter_ratio`（已裁 A-49）。
   `ripple.probing[].dominant_period_counts_per_rev` 已按 A-11 全量改名 `dominant_order_per_rev`（§1.4/§1.15/R-07）。
   仍**禁用**、只作 `necessary_context` 的量：`host_pause_count`（A-8，不新增）、`spectral.*.band_energy`（不在 C2）；
   `meta.*`/`drive.*`（如 `meta.drive.*`、`meta.sensor_config`、`meta.counts_per_mm`）
   一律走"输入通道/necessary_context"栏，不作 `supporting_evidence[].feature`。
   **例外随 A-49 收口**：`quality.*` 三量（`dt_jitter_ratio`/`nan_ratio`/`gap_max_s`）原先只能作 C1 叙述，
   现已有 C2 镜像 `quality_ref.*`，**可以**作证据路径（走 C2 路径名，不写 C1 路径）。
   R-22 签名表逐格路径已核对存在于 C2。
   **本轮新增核对（第四轮 A-48/A-49/A-68/A-70）**：`feedback_integrity.{corr_pos_fb_vs_pos_cmd,
   fe_zero_ratio, pos_fb_static_on_move_ratio, second_feedback_available, masquerade_suspected}`
   与 `quality_ref.*` 五量 + `source` 均在 C2 例 A/B 中逐字存在；
   **A-105 增补的 `feedback_integrity.identity_check` 同步在例 A/B 中出现**（其计数键集权威在
   C1 派生规则 9 与 C2 规则 18，示例只演示 `performed`/`reason` 两键——检查 23 的"字段须有载体"按此满足）；
   `meta.drive.rated_torque_N_m`/`rated_torque_source`、`meta.channels.<pos>.sensor_side`
   均在 C1 中逐字存在（A-70/A-68）。
2. **每条规则的 `family` 在 KB0 §2 的 22 个 slug 表内，或为 `null`（KB0 §6 检查 2）**：
   叶子规则 **R-01…R-24** 的 family 依次为 `mechanical_thermal_drift`, `mechanical_loose_structure`,
   `mechanical_resonance`, `mechanical_resonance`, `mechanical_crawling`, `mechanical_friction_stiction`,
   `mechanical_encoder_periodic_error`, `mechanical_backlash`, `mechanical_double_inertia`,
   `mechanical_resonance`, `electrical_torque_ripple`, `electrical_current_loop_bandwidth`,
   `electrical_velocity_pi_detune`, `electrical_position_pi_detune`, `electrical_feedforward_mismatch`,
   `electrical_motor_heating`, `electrical_resolution_quantization`, `software_induced_host_thread_jitter`,
   `software_induced_interp_buffer_underrun`, `software_induced_bus_cycle_miss`,
   `software_induced_late_vision_result`, `software_induced_pulse_eq_overwritten`,
   `software_induced_settle_window_too_short`, `software_induced_polling_latency` —— 全部命中，无自造 slug。
   元规则/仲裁器 **R-25…R-30** 本轮已按 A-17 把 `family` 改为 **`null`**（不再占 slug，见下条）。
3. **KB4 归因树叶集合 = KB0 §2 的 22 个 slug（KB0 §6 检查 3）**：
   **叶集合就是 KB0 §2 的 22 个 slug**（`mechanical_*` 8 + `electrical_*` 7 + `software_induced_*` 7），
   每个叶至少被一条 R-01…R-24 主判据锚定；`mechanical_double_inertia` 由 R-09、
   `mechanical_resonance` 由 R-03/R-04/R-10 共享。**`R-25/26/27/28/29/30` 是边与门（`family: null`）不是叶子**——
   R-25 频带拒答、R-30 登记义务是元规则，R-26/R-27/R-28 是仲裁器（择优/排序到别的名下），R-29 是衍生评估（不判故障）；
   KB6 侧的 `R-37/49/50` 同理为边与门，不在本文件。**`software_induced_error` 是族级标签，不是 slug**：
   只允许出现在 `differential.not_evaluable`/`considered`（见纪律 5、R-30），
   **禁止**出现在 `hypotheses[].fault_mode`（A-19，逐条 hypothesis 必须写具体 `software_induced_*` slug）。
   —— 本轮自查未发现正文违反此条；R-30 的登记义务文本已明确写 `not_evaluable`，未把族标签写入 hypotheses。
4. **KB5 合成样本可读入 C1（KB0 §6 检查 4）**：本文件不新增分段词表、不新增通道名
   （只用 `probing/path/dwell/rest/move/settling/homing/scanning/curing` 词表内值）。
5. **`blocked_rules` 与频带下界自洽（KB0 §6 检查 5）**：§2.1 表；C2 示例 B 现为
   `["R-03","R-04","R-11#switching_freq"]`（fs=1 kHz），运行时按 §2.1 的 `band⊥` 表动态生成，
   支路级越带用 `R-<nn>#<branch>` 写法（A-79）。
   **G-14 已闭环（A-79）**：本文件自查时 C2 例 B 还写着 `["R-03","R-04","R-10","R-11","R-25"]`，
   三处矛盾——`R-11` 整条阻塞与"150 Hz 谐波支路可评"冲突（改支路粒度）、
   `R-25` 是门禁本身无 `band⊥` 不该阻塞自己（移出，落点 `audit.rules_fired`）、
   **`R-10` 更是必须运行**（它是在低采样率数据上抓混叠假峰的那一道；把它标成 blocked
   等于在唯一需要它的场景关掉它——纪律 2 早期版本的同一错误已一并修正）。
6. **不含产品代码（KB0 §6 检查 6）**：全文只有说明性公式、布尔判据与一段文档级伪代码（§3.3），
   无可运行实现；R-22 签名表、R-15 有符号判据、R-20 三条件升级均为说明性表达；入口约束（`python -m axiscope`）未被违反。
7. **工艺/标定/节拍侧证据走 C7，不混入 C2（KB0 §6 检查 7，A-34/A-36/A-40）**：
   本文件 §1 只登记 C2 伺服波形特征；`process.*`/`calibration.*`/`cycle_stats.*`/`scan_program.*`/`power_channel.*`
   一律不在本表，口径权威在 **C7 §2.2/§4.2**（§1 已加指针声明）。本文件未引用任何未登记于 C2/C7 的 C7 路径。
   （KB3 不含工艺侧判据；工艺/标定规则在 KB6，其证据路径须走 C7，不得混入 C2。）

### 6.1 第四/五/六轮裁决与 A-87/A-88/A-89 在本文件的落点清单（A-54…A-97 中与 KB3 有关者）

| 裁决 | 本文件落点 | 状态 |
|---|---|---|
| **A-68**（`sensor_config` 第四值 `mixed`） | R-04 判据（顺序判据段）/ 必要上下文 / 适用边界；§1.3 `antiresonance_freq_hz`、`is_double_inertia_pair` 两行；§2.1 R-04/R-09 行备注；§5 G-13 追加行 | 已裁，已写入；KB5 旧处置（混合构型写 `unknown` + `assumptions`）标注作废 |
| **A-70**（转矩百分比分母） | §0 新增纪律 13；§1.1 `global.cur_q_rms_pct`/`cur_q_peak_abs_pct`/`cur_q_saturation_ratio` 三行；R-06、R-11、R-12、R-16 的出处/适用边界；R-29 说明"运动学 `%` 不受约束" | 已裁，已写入；`meta.drive.current_limit_a` 缺口另登记 G-15 |
| **A-45 ↔ R-20/R-28**（升级三条件同调） | R-20 判据（canonical 三条件原文 + `confidence ≤ 0.6` 理由）；R-28 判据（原文重复同一三条件并声明 canonical 在 R-20）；`s_net` 由 `null` 改为可算（A-9）；§5 G-5/G-9 收口行 | 已裁；与 KB4 §1.3 N6.c / CP-10 / §2.5 CAP-11 逐字一致（本轮已核） |
| **A-50**（残差方向，**已被 A-82 更正**） | §0 纪律 6（现写"残差 `≤ τ_u` 才算同步可信；被声称的差值要 `> τ_u` 才可分辨"，两个方向分给两个量）；R-18 判据（A-50 改成 `>`，A-82 改回 `≤`）；R-20 条件③；R-21 阶跃-视觉事件对齐（原写 `abs(Δt) > τ_u`，现为窗内对齐）；R-24 必要上下文（不变）；R-28 择优前置；§3 族级纪律 | A-50 只对了语义（`alignment_residual_ms` = 匹配对 `abs(Δt)` 的中位数），方向定反了 ⟹ 本文件现**没有任何**"残差大于不确定度才算对齐有效"的写法；反过来的旧写法（"残差 `≤` 不得作证据"）也已全部删除 |
| **A-87**（真值来源三分：波形可算 / 逻辑自洽 / 约定与接线） | §0 新增纪律 15（本文件所有 `basis` 取值受它约束：第 ③ 类恒 `rule_heuristic`）；R-22 签名表前言（末列"首次上机的验证动作"是**待外部确认清单**，不是判据，与中间三列不得混写）；R-22 ②④⑥ 行依赖的口径/比较源/锁存源属第 ③ 类 | 已裁；触发者是 minimax 第四轮问答的自审（承认仿真器未建模点动、点动用例为零，补的自检却拿自家约定当证据）。**A-33 未被推翻**：六个缺陷**形态**仍是逻辑自洽、可判据化；被限制的是"这台机器具体编码"这类文档事实（纪律 15 末段划界） |
| **A-88**（同源核对物无证明力） | §0 新增纪律 16（证据资格，与纪律 15 的来源分类正交）；R-22 签名表前言末段（末列每行须能填 `verified_against = {manual_id, revision, clause}`、统计 `已核对 k / 总 n`、`k = 0` 措辞封顶"样板就绪，签名与位号未经外部核对"、清单不抵扣工时） | 已裁；触发者是 GLM 代码工厂的第四轮自审（它承认签名凭记忆生成、`ApiChecklist.md` 又由同一份知识库派生 ⟹ 只能索引"去哪里核对"，发现不了"生成错了"）。**它改了主张与工件、没改机制**，本条补的正是机制；槽位书写口径沿用 C6 §5 的 `field_procedure` 前缀（A-89 后为 `[层级\|真值来源=③a/③b\|核对=<档位>:<工件或答复标识>\|执行者=人工/厂商]`），本文件不新增载体字段 |
| **A-89**（③ 类拆 ③a/③b + 核对主体不可转借 + 抽取式优先 + 断言要负向测试） | §0 纪律 15 第 ③ 类拆两档，并**就地更正本文件自己的 `dmc_vmove` 示例**（原写作"只能进待确认清单"，实为 ③a：官方手册可查，对本仓库暂记 `public-doc`，但不得再登记为"必须问厂商"）；纪律 16 新增 ④（可抽取字段禁止凭记忆书写，未覆盖行标 `unverified_signature`，未标档默认 `memory`）与 ⑤（断言须负向测试）；R-22 签名表前言加"本表不写厂商函数名"的理由段 | 已裁；**本条推翻的是本仓库的登记口径而非判据**：六个缺陷形态（A-33）与纪律 15 的三分法都保留，改的是"文档可查"与"批次才定"不得混列。触发者是 minimax 拿到官方手册+官方绑定后做的抽取式校验（抓出三个真机即崩缺陷）与 GLM 把 `verified_against`/一致性断言落进工具并做负向测试；`basis` 三值**不增档**——上一轮我提议加 `documented_external`，复核后作废（接口事实走 `external_reference`，改进量仍由 C3 规则 4 三值管） |
| **A-51**（门/边只产登记义务 + 两种登记键式） | §0 纪律 5（族级/逐模式两式）；R-25 判据与适用边界；R-26/R-27/R-28/R-29/R-30 各加"永不进 `hypotheses`"；§3.3 伪代码键式改正 | 已裁 |
| **A-81**（出处带占位符 / 未核对条目） | R-20 出处块（撤下 `G. Nair, F. L.? … Proc. IEEE 95(2):139–162, 2007` 的猜测作者串与卷期页码，Steiner/ETG.1000.2 就地标 **条目未核对**）；R-22 出处行的同一条 NCS 综述；§5 汇总表"网络控制系统"行由"可信"改"机制可信，条目未核对"；§10 第 24/25 条的标注口径；R-20 适用边界的 `dt_jitter_ratio` → `quality_ref.`（A-49 残留） | 已裁；`T2` 出处存在与否不改变 `basis = rule_heuristic`，也不抬高措辞天花板（KB0 §6 检查 17） |
| **A-48/A-49**（`feedback_integrity` 组、`quality_ref` 全值域） | 新增 §1.13c；§1.13b 补 `dt_jitter_ratio`/`nan_ratio`/`gap_max_s`/`source` 四行；R-15/R-17/R-20 与 §1.15 的 `quality.` → `quality_ref.`；R-22 签名表①改引 `feedback_integrity.*` | 已裁 |
| **A-64/A-65**（能力声明真空） | §0 新增纪律 14；R-01、R-03、R-04、R-11、R-12、R-16 的出处/适用边界；R-04 期望效果按 A-64 降级；§2.1 表 R-01/R-03/R-04/R-11/R-12/R-16 行；§4 T1-a/T3 登记表；R-25 补 T1-a 数值口径 | 已裁 |
| **A-54**（`source_tier` 权威名） | 本文件 `出处` 字段一直用 tier 值（`T1-a`/`T1-b`/`T2`/`T3`）而未使用 `evidence_tier` 字段名；无需改名 | 无需改动（记录） |
| **A-97**（无 counts 刻度 ⟹ 绝对阈值不可比；`*_counts` 是后缀历史名） | §0 纪律 4 的 **(A-97 更正)** 段（(b)(c)(d) 三支收窄 + 指向 §1.13b）；§1.13b 新增「阈值刻度标注约定」（本节为唯一登记处，含绝对支索引表与待人工复判清单）；§1.1/§1.4/§1.5/§1.6/§1.7/§1.8/§1.12/§1.13b/§1.13c 各行标注；R-01/R-02/R-05/R-07/R-08/R-14/R-15/R-16/R-17/R-19/R-21/R-22/R-23/R-24/R-29 的判据/排除项/建议动作/适用边界标注；§3.2 `[P]` 表逐行标注 | 已裁（本轮）；真实样本 `Export10_244531.csv` 为 `units_are = si_native` + `counts_per_mm = null` ⟹ 绝对支一律 `blocked_by = absent_counts_scale`（固定 reason 句式「无 counts 刻度，绝对阈值不可比」），比值/相关/占比/阶次支照算且不连坐；R-02 与 R-08 已在规则文本内**按支路分开写**（绝对支缺席不作废整条）；四个判不了的族登记在 §1.13b 待人工复判清单（每转/CPR 折叠基、`*_mm` 定义式与 µm 级结论、两处定性无阈值签名）；**未新增任何数字**；该四族已由 **A-110** 全部裁完（①④⑤ 当场裁、②③ 落点任务 #39；**#39 已由 A-113 于 2026-10-21 落码 ⟹ ②③ 的"落地前"限定词解除，见 §0 纪律 4 与 §1.13b 的 A-113 生效注**） |

