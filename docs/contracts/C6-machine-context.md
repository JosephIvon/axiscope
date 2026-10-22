# C6 — 机器状态与事件上下文契约

## 0. 为什么必须有这一层

C1 只有波形。但有一整类成因**在波形里长得和机械故障一模一样，只有对齐的事件流能区分**：

| 成因 | 波形表现 | 需要的上下文 |
|---|---|---|
| 上位机线程调度抖动 | 跟随误差出现无规律尖峰 | `source=host` 的 GC/线程停顿事件 + 尖峰时刻对齐 |
| 插补缓冲欠载 | 路径段速度骤降、停顿 | `source=interp` 的 buffer_underrun 事件 |
| EtherCAT 丢周期 / WKC 错误 | 单周期指令保持、位置跳变 | `source=network` 的 missed_cycle / wkc_error |
| 视觉结果晚到 3 ms | 轴等待后突进 | `source=vision` 的 result 事件时间戳 |
| 工艺步骤冲突 | 轴在错误的配方下运动 | `machine_context.recipe/step` |

这正是草案 B 提出的**机械 / 电气 / 软件三方归因**中"软件"一支的唯一证据来源，
也是伺服厂商调谐工具（只看驱动器内部通道）根本看不到的一层。
没有 C6，`software_induced_error` 判据族就只能靠猜——那是不诚实的。

## 1. 文件

放在 C1 样本包内：`sample/events.jsonl`（可选，一行一事件）。

```jsonl
{"t": 0.089120, "level": "info",    "source": "motion",   "code": "move_started", "axis": "X1", "detail": {"target": 14.0111, "vel": -2.0}, "raw": "…"}
{"t": 0.140033, "level": "info",    "source": "motion",   "code": "move_done",    "axis": "X1", "detail": {"settled": true}}
{"t": 0.201500, "level": "warn",    "source": "interp",   "code": "buffer_underrun", "axis": null, "detail": {"buffer_level": 0, "lookahead_ms": 12}}
{"t": 0.201870, "level": "error",   "source": "drive",    "code": "A.8101",       "axis": "X1", "detail": {"raw": "position deviation too large"}}
{"t": 0.300000, "level": "debug",   "source": "network",  "code": "wkc_error",    "axis": null, "detail": {"expected": 6, "actual": 5}}
{"t": 0.412000, "level": "info",    "source": "vision",   "code": "result",       "axis": null, "detail": {"dx": 2.1, "dy": -0.4, "latency_ms": 31.2}}
```

### `source` 词表
`host`（上位机进程：GC、线程、内存）、`interp`（插补/前瞻缓冲）、`motion`（指令下发与完成）、
`drive`（驱动器报警/状态字）、`io`（限位、真空、传感器电平）、`network`（总线周期、WKC、超时）、
`vision`（视觉结果与耗时）、`process`（工艺步骤：加热、出胶、固化、寻光）、`mes`（上位系统交互）。

### `level` 词表
`debug` `info` `warn` `error` `alarm`。

## 2. 机器语境

放在 C1 的 `meta.json` 里新增：

```json
{
  "machine_context": {
  "machine_type": "die_attach | dispenser | coupler | testbed | unknown",
  "control_card": "googol GTS-800 | leisai DMC3000 | zmotion ZMC | beckhoff TC3 | unknown",
  "recipe": "AuSn_280C_die4",
  "step": "pick_up",
  "step_sequence": ["home", "pick_up", "flux_inspect", "place", "bond", "verify"],
  "axis_group": "XYθ",
  "operator_notes": "冷机正常，运行 40 分钟后变差"
}
}
```

`step` 与 `step_sequence` 让"同样的波形在不同工艺步骤下含义不同"可被判定。
例：点胶轴在 `dispense` 段的稳态偏差是工艺特征，在 `travel` 段才是故障。

**扫描/寻光轨迹参数不在本契约声明**（裁决 A-28 / A-41）：螺距、线距、爬山步长、驻留时长的
权威载体是 C7 的 `scan_program`，本契约**不新增** `motion_program` 字段。同一信息只能有一个权威载体；
需要时 `machine_context` 通过 `process.json` 的引用指向它，避免两处漂移。
`scan_program.source == "inferred_from_waveform"` 时依赖步长的判据置信度封顶（用波形反推的步长
去验证波形是循环论证）。

## 3. 时间同步元数据（本契约的核心纪律）

事件流与波形几乎必然来自**不同进程、不同时钟**。因此：

```json
{
  "sync": {
  "method": "ntp | host_clock | trigger_edge | manual_offset | unknown",
  "offset_s": 0.0,
  "uncertainty_ms": 2.0,
  "verified": true,
  "evidence": "共用一次 bTrigger_Scope 上升沿对齐，残差 0.4 ms"
}
}
```

硬规则：

1. `sync.verified` 为 `false` 或 `method == "unknown"` 时，
   **禁止输出任何因果性结论**（"因为 GC 停顿导致该尖峰"）。
   只能输出时间共现，并在报告里写明"时钟未对齐，共现不等于因果"。
2. 两个方向不要混（A-82，更正 A-50）：
   - **被声称的时延/差值**（`vision_result_latency_p95_ms`、`bus_cycle_hold_max_ms`、两次到位时刻之差）
     必须**大于** `sync.uncertainty_ms`，否则这个差值在时基上根本分辨不出来，判据不启用；
     尖峰-事件的对齐窗同理，也必须严格大于 `sync.uncertainty_ms`。
   - **对齐残差** `alignment_residual_ms`（匹配对 `|Δt|` 的中位数，C2 规则 8）必须**不大于**
     `sync.uncertainty_ms` 才允许因果声明：残差超出不确定度预算，说明两个钟之间还有没被建模的系统偏差，
     此时"尖峰落在事件附近"可能只是钟差，只能降级为时间共现（C2 规则 8/14、KB4 CAP-8）。
   旧文本把这两条写成了同一个不等号（"任何 `|Δt| < uncertainty_ms` 的对齐都不得作为证据"），
   方向对残差而言是反的：它会禁止掉最紧的巧合、放行最松的对齐。
3. `uncertainty_ms` 缺失时按 5 ms 保守取值，并记入 `audit.assumptions`。

> 这一条是本契约存在的全部理由。多源日志分析最容易犯的错就是拿两个没对齐的时钟讲因果故事。
> 主动把它写成门禁，是作品集里最能体现工程判断的部分。

## 4. 对下游的影响

- **C2 新增特征组**（依赖 `events.jsonl` 存在才计算）：
  ```
  event_context: {
    n_events, n_by_source{}, n_alarm,
    host_pause_max_ms,
    interp_underrun_count, interp_underrun_during_path,
    network_cycle_miss_count, bus_cycle_hold_max_ms,
    vision_result_latency_p95_ms,
    fe_spike_count, fe_spike_aligned_to_host_pause,
    fe_spike_aligned_to_underrun, fe_spike_aligned_to_network_miss,
    fe_spike_aligned_to_vision_result, fe_spike_aligned_to_recipe_change,
    alignment_residual_ms,
    step_labels: [{t0,t1,step,recipe}]
  }
  ```
  不另设 `host_pause_count`：`n_by_source.host` 已是同一件事（KB0 §7 A-8）。
- **C3 新增判据族** `software_induced_error`（见 KB3/KB4），与 `mechanical_*`、`electrical_*` 并列。
- **C3 新增字段** `differential.not_evaluable`：
  当 `events.jsonl` 缺失时，必须显式写入
  `{"family": "software_induced_error", "why": "无事件上下文，无法区分机械尖峰与调度抖动"}`。
  这里用 `family` 而不是 `fault_mode`——族级标签不是 slug（KB0 §7 A-18/A-19）。
  **不允许沉默跳过**——沉默会让报告看起来比实际更有把握。
- **C7 承接工艺侧**：寻光扫描参数、标定批次与节拍统计一律进 C7（`scan_program` /
  `calibration.jsonl` / `cycle_stats`），`machine_context` 只声明 `recipe`/`step`/`step_sequence`
  与指向 C7 的引用，不在本契约里重复定义。
- **C5 评测**：`none_of_the_above` 案例中加入"仅有波形、无事件上下文"一类，
  考核 agent 是否拒绝下软件侧结论。

## 5. 范围纪律

本契约只服务**诊断证据**。不实现设备状态机引擎、不实现异常恢复执行、不做报警管理。
恢复动作只以 C3 里 `recommendation.field_procedure`（人执行的文字步骤）存在。

**`field_procedure` 的分级词汇表（A-87；档位与核对状态按 A-89 追加；结构借自第三方实现的分级上机清单，内容不是我们的）**
每条 `field_procedure` 必须标注它属于哪一级、依赖的外部真值是哪一档、核对到什么程度、由谁执行。
落点在 C3 的 `recommendation.field_procedure[]`（字符串数组，不新增字段），步骤文本以固定前缀标注：
`[L<级>|真值来源=<③a 手册可查|③b 批次与现场>|核对=<memory|public-doc|official-artifact:<工件@版本 第X条>|vendor_reply:<日期>>|执行者=<人工|厂商>]` —— 例：
`"[L2|真值来源=③a 手册可查|核对=public-doc|执行者=人工] 以 5 mm/s 点动 +X，确认 pos_fb 递增"`。
前缀缺失 ⟹ 该步视为未标注，`audit.rules_fired` 记一条 A-87 违规（与 C3 规则 14 的措辞拦截同机制）；
**标 ③a 却给不出 `official-artifact:<工件@版本 第X条>` 或 `vendor_reply`** ⟹ 按 KB0 §6 检查 21 判缺陷
（可自查的事实被登记成永久未知）；标 ③b 的必须写明**手册为什么答不了**（随接线盒型号变 / 随现场接线定 /
随批次固件定 / 属机器安全动作，不由 API 决定）。

| 级 | 内容 | 依赖的真值 | 档位（A-89） | 本 agent |
|---|---|---|---|---|
| L1 | 只读：状态字/位置/电流读数与示教器一致 | 单位口径、通道映射 | ③a（映射表在手册） | 可给建议 |
| L2 | 低速点动验方向 | **方向位号编码** | **③a**（手册函数章节有答案——原写"只能问厂商"是登记错误） | 只登记待确认，不执行 |
| L3 | 单轴定位验单位与行程 | 脉冲当量、`counts_per_mm` 口径 | ③a + 现场量块对照 | 只登记待确认 |
| L4 | 停止语义（急停是否真为急停） | 停止方式编码 | ③a（编码表在手册）＋安全动作归属属 ③b | 只登记待确认 |
| L5 | 回零与零点一致性 | 限位/原点 **IO 位号↔物理端子** | **③b**（随接线盒型号与现场接线定） | 只登记待确认 |
| L6 | 插补/飞拍触发点 | PSO 比较源、锁存来源、**CMP 通道↔端子**、手册未明写的占位填法 | 比较源/锁存源 ③a，端子对照与占位填法 ③b | 只登记待确认 |

纪律：**上一级不过不得进下一级**；方向/位号类错误的特征是**不报错、不写日志、轴直接往反方向走**，
所以 L2 之前不得解除限位保护（该提醒必须原样进报告）。本 agent `safety.writes_to_device` 恒为 `false`
（C3 规则 6），**L1 也不执行**——表里"可给建议"指的是我们能在离线报告里指出该看什么，
不是我们下发任何指令。这些格属于 A-87 的第 ③ 类（约定与接线真值）：
永远不得标 `simulation_validated`，`basis` 封顶 `rule_heuristic`，并记 `audit.assumptions`。
**A-89 补一句**：`basis` 封顶与"该条待不需要等厂商"是两件事——③a 一经官方工件核对即可闭合（措辞升到
"已按〈工件@版本〉第 X 条核对"），但 `basis` 一档都不升，因为手册定的是接口定义，定不死改进量（C4 补充约束）。

**阶梯覆盖的是"验证动作"，不是"所有上机动作"（本轮自查补）**。像"写陷波参数 / 回退一档增益"这类步骤
在 L1–L6 里没有对应级——它们是**人工在设备上执行的改动**，其风险由 C3 的 `safety.hard_blocks`
与 `requires_offline` 管，不由本阶梯管。标注时取其**依赖的验证级**（多为 L1：改前改后的读数对照），
并在文本里写清该步由人工完成。C3 §示例的 `recommendation.A1.field_procedure` 四步即按此处理
（全部标 L1，`真值来源=③a 手册可查`、`核对=memory`——因为本仓库没有厂商工件，`external_counts.verified = 0`，
措辞按 C3 规则 17(d) 封顶）。**不得**为了凑级把参数写入步标成 L2/L3，那是把"我们没执行的动作"
伪装成"分级上机清单里的一格"。
