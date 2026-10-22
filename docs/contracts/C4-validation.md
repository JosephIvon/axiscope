# C4 — 验证门控契约（validation gate）

这是本项目区别于"LLM 生成建议"的核心机制：**任何参数建议必须先在仿真被控对象上跑一遍，
拿到量化改进后，才允许以 `simulation_validated` 层级写入报告**。

> 例外（裁决 A-43）：`software_induced_*` 一族的**改进量**一律 `rule_heuristic`——
> KB5 的事件注入不含真实调度器与总线仲裁，仿真能证明"这个形态可被检出"，
> 证不了"改了就变好"。检出类判据仍可用 `simulation_validated`，引用时必须带该 caveat。

## 流程

```
建议 A ──┐
         ├─→ 拟合被控对象 P̂（用观测波形反参数：惯量比、共振频率、阻尼、摩擦）
观测波形 ┘        │
                  ├─→ 复现校验：P̂ 在相同指令下重放，误差 < tol ？
                  │     否 → basis = rule_heuristic，报告标注"模型不可信，未验证"
                  │
                  └─→ 在 P̂ 上分别跑 {基线控制器} 与 {基线+建议 A}
                        │
                        ├─→ 指标对比（fe_rms / settling / overshoot / 频谱峰）
                        ├─→ 稳定性校验（相位裕度、增益裕度、是否激发新模态）
                        └─→ 敏感性扫描（±20% 参数扰动下改进是否仍成立）
```

## 记录结构

见 `C3-diagnosis.md` 的 `validation[]`。补充约束：

- `plant_fit.fit_residual_pct` > 25% 时，`basis` 必须降级为 `rule_heuristic`，
  并在 `caveats` 里写明"仿真模型无法复现观测波形，改进量不可信"。
- **约定真值不得走本门控**（A-87，分档按 A-89 更正）：`basis = simulation_validated` 要求被验证的量在**波形里可复算**。
  方向位号（`dmc_vmove` 的 0/1 到底哪个是正）、停止方式编码、IO 位号↔端子、PSO 比较源（cmd 还是 fb）、
  锁存来源、手册未明写的占位填法——这些真值在厂商手册与接线表里，**仿真里没有它们**：
  仿真器按约定 A 建模、自检再查"是不是 A"是同义反复，跑通多少次都不构成证据。
  这类建议**恒为 `rule_heuristic`**，且 `caveats` 必须写"真值来源 = 厂商手册/接线表，未经外部确认"，
  确认动作只以 `recommendation.field_procedure` 存在（C6 §5 的 L1→L6 分级，本 agent 不执行）。
  与 A-43 的分工：A-43 管的是"**改进量**仿真算不准"（同一真值，量级不确定），
  A-87 管的是"**真值本身不在数据里**"（再怎么仿真也换不来一台机器的位号定义）。
- **A-89 的两点收窄（不改本门控的形状）**：
  **(a) ③a 文档可查类可以闭合，但闭合不经过本门控**——方向位号、停止方式编码、错误码表、
  某函数是否存在，厂商手册或官方绑定里有答案；一经 `external_reference = official-artifact`
  （工件存证在库 + `clause` + `verified_by = self`）该条即从"待确认"转为"已核对"，
  **`basis` 仍是 `rule_heuristic`/`unverified`，不得升为 `simulation_validated`**——手册定的是接口定义，
  定不死"改了会不会变好"。所以本门控**不因手册到手而放行**（把 `basis` 加第四值的提议已作废，见 KB0 §7.3 A-89）。
  ③b 批次与现场类（IO 位号↔端子、使能归属、编码器是否并接、从站 PDO/ESI、SDK↔固件矩阵、位数）
  手册答不了，只能 `vendor_reply`（书面答复 + 日期 + 适用型号），且登记时必须举证"手册为什么答不了"（KB0 §6 检查 21）。
  **(b) 核对主体不可转借**：第三方会话/别的 agent 报的"手册 X 页写了 Y"，对本仓库只是 `public-doc`，
  **不计入 `已核对 k`、不抬高措辞天花板**，只能改变该条目的 ③a/③b 归类（KB0 §6 检查 20）。
- **验证结论的环境层级（A-90）**：`validation[]` 每条结果须带 `verification_level ∈ {L1, L2, L3}`
  （KB0 §4 第三阶梯；模型来源**读 C3 既有字段 `plant_source`/`plant_id`**——A-91 按检查 23 的反向条款收口，
  不新增 `model_source`/`model_version` 这组同义名）。本门控跑在 KB5 合成被控对象上
  ⟹ 恒为 `L1`（模型与被验管线同源），故 `simulation_validated` 的对外措辞封顶
  "管线跑通 + 在合成对象上成立"；将来接入独立来源的 HIL 模型时，`plant_source` 指向本仓库之外且
  `plant_id` 带版本标识，否则不得标 `L2`（L2 同源降级条款）；用 T1 真实记录数据做回放验证属 `L3`，仍须带数据集 DOI + 日期
  （L3 不豁免条款，KB0 §6 检查 24）。
- **文档级真值的双标注（A-92）**：`validation[]` 或自检若以公开标准测试向量 / 协议一致性向量 /
  手册示例输出为期望值（如 CRC16 标准向量 `"123456789"⟹0x4B37`），`verification_level` 仍按执行环境
  如实记（通常 `L1`），**期望值侧**同时挂 `audit.external_ledger[]` 的 `official-artifact` 行
  （标准号 + 向量条目 + `verified_by`）。措辞上限为"与〈标准@条目〉一致"的**窄命题**——
  过标准向量不得表述为"驱动可用 / 通信正确 / 协议已验证"（环境级结论仍须 L2/L3；
  KB0 §6 检查 24 文档级真值条款）。
- `sensitivity` 必填：至少 3 个参数（惯量比、共振频率、阻尼）各 ±20% 扫描，
  记录改进量的最坏值。最坏值 < 10% 则建议标记为 `fragile`。
- `validation[]` 必须回显 `plant_fit.sensor_config_used ∈ {motor_side, load_side, mixed, unknown}`
  （A-68 四值）。写 `mixed`/`unknown` 时，`plant_fit` 的峰/谷配对不得作为双惯量零极点证据——
  拟合出来的 P̂ 若是从两套通道拼出的曲线反推的，它本身就混了两个传递函数，
  验证门控会给出"改进有效"的假信号（这正是 KB5 P-B2/INJ-30 那类样本要单独成案例的原因）。
- 若建议会激发新的共振峰（`candidate` 频谱中出现基线没有的、幅值 > 基线主峰 50% 的峰），
  必须**否决该建议**并在报告中说明——这是内行会立刻检查的点。

## 指标定义

| 指标 | 定义 |
|---|---|
| `fe_rms_counts` | 全样本 `fe` **去均值** RMS（**A-114**：载体 `src/axiscope/features.py::_ac_rms`；实现此前算的是原始 RMS，已改判为服从本定义） |
| `fe_max_counts` | 全样本**原始** `max\|fe\|`（不减均值）——与上一行是「最坏幅值」与「波动」两个并列口径，**不得互相代用**（A-114） |
| `fe_mean_counts` | 全样本**原始** `mean(fe)`（有符号常偏）——A-114：`fe_rms_counts` 去均值后被减掉的常偏必须有独立载体（C2 规则 16 的"减了必须记"在同一条轴的同一路信号上同样成立）；消费者是 KB3 R-22 签名表 ④/⑤ 两行 |
| `settling_time_ms` | 每个 `settling` 段：进入并保持在 ±settle_band 内的最早时刻 |
| `overshoot_pct` | 每 `move` 段：`max(fe 同号超出量)/move_amplitude ×100` |
| `dominant_peak_db` | `cur_q` Welch PSD 主峰相对宽带本底的比值 |
| `stability.phase_margin_deg` | 开环传递函数 `-180°` 交越处增益裕度换算 |

**凡用额定值做分母的指标（`*_pct`、饱和比、余量类）继承额定值来源的层级**（A-70）：
`meta.drive.rated_torque_source == "assumed"` 时，改进量的 `basis` 不得高于 `rule_heuristic`，
且必须带 caveat"额定转矩为假定值，百分比类改进量的绝对刻度不可信"——
门控比较的是两个用同一假定分母算出的数，比值看似无害，绝对值却全是造出来的。

## 仿真内核

被控对象模型规范见 `docs/kb/KB5-simulation-plant.md`（双惯量 + 摩擦 + 量化噪声 + 三环控制）。
仿真必须与真实数据走同一套 `features()` 与 `rules()` 代码路径——
即"合成数据也要被同一个 agent 诊断出来"，这既是验证门控，也是评测集。
