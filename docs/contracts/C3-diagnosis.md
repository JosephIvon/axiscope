# C3 — 诊断输出契约（agent 的最终产物）

> **本例数据的采样率前提**：示例中的 1181 Hz 谐振要求 `fs ≥ 8 kHz`（见 C2 规则 7 频带门禁）。
> 我们手上的 DaRUS 真实数据是 `fs = 1 kHz`，奈奎斯特 500 Hz——**在该数据上这类判据必须进
> `differential.not_evaluable`，而不是输出"未发现共振"**。
> 低频段（<400 Hz）在绳索/皮带/减速器传动轴上是真实存在的，故本例的结构仍然适用，
> 只是频点要按实际 `freq_limits` 缩放。
>
> **本例的事件流前提**（规则 18 / A-99）：两份示例共用**同一个前提**——没有 `events.jsonl`，
> 载体是 `examples/c2_example_a_no_events.json`（C2 例 A 的无事件孪生），由
> `inputs.features_snapshot` + `inputs.event_context_available: false` 声明并被校验器逐字段核对。
> 同一份特征若**带**事件（`examples/c2_example_a.json`），KB4 §2.9 字典序会把软件族排到谐振前面，
> 头条与 `overall` 都不同（实测 `overall = 0.42`）——两份输入都进了测试，别把这两个数当同一场景。
> 前提相同而 `case_id` 不同，是因为 E1/E2 的**假设数**不同（规则 20 / A-107 ③），见下。

**示例分两份（A-107 ③ / 规则 20）——同一份前提，两种假设数：**

- **E1 `case_id = AX1-20260311-01`**：只有一条假设（机械谐振，S3、C=0.65），`overall = 0.59`。
  它的存在是为了保住 KB4 §2.3 算例 A 的逐格锚点——单假设下没有排序可演示，也就没有把 0.59
  误当成"两条并存时的头条"的风险。fixture：`tests/fixtures/c3_example_resonance_059.json`。
- **E2 `case_id = AX1-20260311-02`**：两条假设并存且**按 KB4 §2.9 字典序排**——前馈失配（S2）
  列 rank 1 当头条、谐振（S3）列 rank 2，`overall = 0.43 = C(H1) 0.4818 × (1 − 0.05×2)`。
  C(H1) < C(H2) 而 rank 相反，正是规则 20 要演示的那件事：**头条由 severity 档决定，不由置信度决定**。
  fixture：`tests/fixtures/c3_example_ranked_pair.json`。

两份的内联副本与各自 fixture 必须深相等（`tests/test_c3validate.py` 逐字段比对），
并且都必须被本契约自己的校验器以零 gap 通过（KB0 §6 检查 26，含规则 20）。

```json
{
  "schema": "axiscope.diagnosis/1",
  "case_id": "AX1-20260311-01",
  "generated_at": "2026-03-11T15:02:31+08:00",
  "engine_version": "0.1.0",
  "inputs": {
    "sample_id": "AX1-20260311",
    "present_channels": [
      "pos_cmd",
      "pos_fb",
      "fe",
      "cur_q"
    ],
    "missing_channels": [
      "vel_fb",
      "temp"
    ],
    "counts_per_mm": 50000.0,
    "drive_params_known": [
      "rigidity_level"
    ],
    "context_complaint": "高速取片后末端抖动，节拍被迫从 1.8s 放宽到 2.6s",
    "features_snapshot": "c2_example_a_no_events",
    "event_context_available": false
  },
  "verdict": {
    "primary": "H1",
    "summary": "X 轴在 1.18 kHz 存在机械谐振（反共振谷在 440 Hz，λ≈6.2 的双惯量对），加减速瞬态在 settling 段 [0.089, 0.140] s 内激励该模态、以 ζ≈0.28 衰减，使整定时间被拉长到 42 ms（C2 示例同值）。建议在该频点加二阶陷波并对速度指令做 ZV 输入整形。预期 fe_rms_counts 由 412.6 降到约 155（−62%），依据层级 = 仿真验证（V1，P-B 双惯量反拟合），不是现场实测；共振频率 −20% 扰动下最坏改进量 28.7%。置信度 0.59 已对反证（阻尼 0.28 不算极低）与 3 条不可评估项扣分。",
    "overall_confidence": 0.59,
    "confidence_note": "逐格可重算（KB4 §2.2/§2.3 算例 A，规则 16）：H1 六条支持证据 S = 0.459/0.768/0.765/0.779/0.680/0.609 ⟹ Smax = 0.779、Srest = 0.656、A_sup = 0.55×0.779 + 0.45×0.656 = 0.724；反证 rho_prime = 1.867 ∈ [1,2) ⟹ v_j = 0.10 ⟹ A_con = 0.10、C_mid = 0.724×0.90 = 0.652；CAP-1/3/5/7 均未触发 ⟹ C(H1) = 0.65。本示例只有这一条假设，无并列可排（排序演示见 `c3_example_ranked_pair`）。verdict = 0.652 × (1 − 0.05×2) = 0.59，其中扣减因子是 **2 个独立缺席原因**（`absent_temp_channel`、`absent_events_jsonl`），不是 3 条 `not_evaluable` 行——族级标签与它覆盖的叶共享同一原因，只计一次（规则 17）。早期草稿写 0.78：未对反证、样本量与缺席扣分，已作废（A-20）。",
    "actionable": true
  },
  "hypotheses": [
    {
      "id": "H1",
      "fault_mode": "mechanical_resonance",
      "display_name": "机械谐振（结构模态被瞬态激励）",
      "rank": 1,
      "confidence": 0.65,
      "severity": 3,
      "supporting_evidence": [
        {
          "feature": "resonance.candidates[0].coherence_torque_velocity",
          "value": 0.86,
          "operator": ">=",
          "threshold": 0.7,
          "strength": 0.459,
          "condition_index": 2,
          "rule_id": "R-03a",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "window": {
            "t0": 0.089,
            "t1": 0.14,
            "segment_id": 1
          },
          "plot": "evidence/resonance_coherence.png",
          "n": 8.0,
          "n_ref": 4.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].amplitude_ratio_vs_broadband",
          "value": 8.4,
          "operator": ">=",
          "threshold": 4.0,
          "strength": 0.768,
          "condition_index": 3,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 96.0,
          "n_ref": 15.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].quality_factor_estimate",
          "value": 27.0,
          "operator": ">=",
          "threshold": 10.0,
          "strength": 0.765,
          "condition_index": 7,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 22.0,
          "n_ref": 8.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].present_in_dwell",
          "value": true,
          "operator": "==",
          "threshold": true,
          "strength": 0.779,
          "condition_index": 4,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 3.0,
          "n_ref": 1.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].present_in_rest",
          "value": false,
          "operator": "==",
          "threshold": false,
          "strength": 0.68,
          "condition_index": 5,
          "rule_id": "R-03b",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 2.0,
          "n_ref": 1.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].tracks_command_frequency",
          "value": false,
          "operator": "==",
          "threshold": false,
          "strength": 0.609,
          "condition_index": 6,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 6.0,
          "n_ref": 4.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        }
      ],
      "contradicting_evidence": [
        {
          "feature": "step_response[0].damping_ratio_estimate",
          "value": 0.28,
          "operator": ">",
          "threshold": 0.15,
          "rho_prime": 1.867,
          "penalty": 0.1,
          "rule_id": "R-03c",
          "note": "阻尼不算极低，说明谐振峰不算尖锐，与 Q≈27 一致但削弱'严重共振'的判断。`penalty` 不是自由参数：rho_prime 落在 [1,2) ⟹ 取 KB4 §2.4 的 v_j = 0.10（规则 16）"
        }
      ],
      "ruled_out_alternatives": [
        {
          "fault_mode": "mechanical_encoder_periodic_error",
          "display_name": "编码器每转周期误差（偏心/刻线误差）",
          "why": "ripple.probing[].dominant_order_per_rev 未与每转周期锁定，且 encoder.per_rev_amplitude_counts 仅占 global.fe_rms_counts 的 23%",
          "rule_id": "R-07"
        }
      ],
      "recommendation": {
        "action_id": "A1",
        "class": "notch_filter",
        "params": {
          "center_hz": 1181.0,
          "width_hz": 470.0,
          "q": 2.5,
          "depth_db": -20.0,
          "cascade_second_notch_at_2f": true
        },
        "rationale": "峰频 1181 Hz，按 峰频/2.5 取宽度以避免过度削相位；第二陷波针对 2f 谐波（≈2362 Hz），不是针对反共振谷——共置构型下反共振谷在峰下方（440 Hz，f_m/f_a = sqrt(1+λ)，λ≈6.2），在谷上加陷波只会进一步削掉可用带宽（A-1）。",
        "risk": "陷波会削弱该频段的指令跟踪带宽；若实际为电气噪声而非结构模态，将导致位置环响应变钝。",
        "reversibility": "参数级，写入驱动器寄存器即可，可回读原值",
        "requires_offline": false,
        "expected_effect": {
          "metric": "fe_rms_counts",
          "from": 412.6,
          "to": 155.1,
          "improvement_pct": 62.4,
          "basis": "simulation_validated",
          "validation_id": "V1",
          "derivation": "to = 实测 412.6 × (V1.candidate 152.3 / V1.baseline 405.1)。V1 基线是仿真复现值，与实测 412.6 的差是复现残差（fit_residual_pct 8.4），不是笔误；两者必须分列，否则读者会把仿真当实测。",
          "caveat": "改进量来自 P-B 双惯量仿真，非现场实测；共振频率 −20% 扰动下最坏改进量 28.7%（见 V1.sensitivity）"
        },
        "field_procedure": [
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 1. 备份当前 Pn 参数表并截图（参数名与单位口径未经手册核对）",
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 2. 先只加第一陷波，做 3 次全行程定位，观察 1181 Hz 峰是否下降 >10 dB",
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 3. 若在 2f（≈2362 Hz）出现新峰抬升，补第二陷波；若 440 Hz 反共振谷附近的响应被一起削平，说明陷波带过宽、正在吃掉有效带宽，回退一档",
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 4. 每次改动后重新测量 settling_time_ms，超过 30 ms 则回退一档增益（30 ms 属机台验收限，非手册已核对值）"
        ]
      },
      "next_data_to_collect": [
        {
          "ask": "补采 0-2 kHz 的 Bode 图（位置环开频响应）",
          "why": "当前带宽为命令响应间接估计，置信度 0.6，不足以确认陷波后相位裕度",
          "unlocks": [
            "R-03d 相位裕度校验",
            "陷波深度上限判定"
          ]
        },
        {
          "ask": "导出 temp 通道，或提供冷机/热机各一组同轨迹波形",
          "why": "操作员备注'运行 40 分钟后变差'，当前无法区分谐振漂移与温漂",
          "unlocks": [
            "H3 热漂移假设的判定"
          ]
        }
      ]
    }
  ],
  "differential": {
    "considered": [
      "mechanical_resonance",
      "electrical_feedforward_mismatch",
      "mechanical_crawling",
      "mechanical_encoder_periodic_error",
      "mechanical_thermal_drift",
      "electrical_position_pi_detune",
      "mechanical_backlash",
      "software_induced_pulse_eq_overwritten",
      "software_induced_host_thread_jitter"
    ],
    "considered_display_names": {
      "electrical_feedforward_mismatch": "前馈失配（旧示例写作 feedforward_mismatch）",
      "mechanical_encoder_periodic_error": "编码器每转周期误差（旧：encoder_eccentricity）",
      "mechanical_thermal_drift": "热漂移（旧：thermal_drift）",
      "electrical_position_pi_detune": "增益过高自激（旧：gain_too_high_hunting / limit_cycle）",
      "mechanical_crawling": "摩擦爬行（旧：friction_crawling）"
    },
    "not_evaluable": [
      {
        "fault_mode": "mechanical_thermal_drift",
        "blocked_by": "absent_temp_channel",
        "why": "缺 temp 通道，且无冷热机对比（结构性真空，A-64：本案例族无对外正例来源）"
      },
      {
        "fault_mode": "software_induced_host_thread_jitter",
        "blocked_by": "absent_events_jsonl",
        "why": "本样本无 events.jsonl ⟹ 跟随误差尖峰与上位机调度抖动在结构上不可分"
      },
      {
        "family": "software_induced_error",
        "blocked_by": "absent_events_jsonl",
        "why": "事件层缺席使整族降级为不可评估。族级标签只在这里出现，不进 hypotheses（A-18）"
      }
    ]
  },
  "validation": [
    {
      "id": "V1",
      "action_id": "A1",
      "method": "two_inertia_sim",
      "verification_level": "L1",
      "plant_id": "P-B",
      "plant_source": "docs/kb/KB5-simulation-plant.md#P-B",
      "plant_fit": {
        "inertia_ratio_fitted": 6.2,
        "resonance_hz": 1181.0,
        "antiresonance_hz": 440.0,
        "damping_fitted": 0.28,
        "fit_residual_pct": 8.4,
        "sensor_config_used": "motor_side"
      },
      "replay_check": {
        "passed": true,
        "max_normalized_error": 0.061
      },
      "baseline": {
        "fe_rms_counts": 405.1,
        "settling_time_ms": 41.6,
        "overshoot_pct": 9.8,
        "dominant_peak_db": 18.3
      },
      "candidate": {
        "fe_rms_counts": 152.3,
        "settling_time_ms": 18.9,
        "overshoot_pct": 3.1,
        "dominant_peak_db": 4.6
      },
      "improvement": {
        "fe_rms_pct": 62.4,
        "settling_pct": 54.6
      },
      "stability": {
        "phase_margin_deg": 41.2,
        "gain_margin_db": 8.7,
        "new_peak_check": "候选频谱未出现基线没有的 >50% 主峰峰 ⟹ 未激发新模态"
      },
      "sensitivity": [
        {
          "param": "inertia_ratio",
          "perturbation_pct": -20,
          "fe_rms_improvement_pct": 44.1
        },
        {
          "param": "inertia_ratio",
          "perturbation_pct": 20,
          "fe_rms_improvement_pct": 51.0
        },
        {
          "param": "resonance_hz",
          "perturbation_pct": -20,
          "fe_rms_improvement_pct": 28.7
        },
        {
          "param": "resonance_hz",
          "perturbation_pct": 20,
          "fe_rms_improvement_pct": 33.9
        },
        {
          "param": "damping",
          "perturbation_pct": -20,
          "fe_rms_improvement_pct": 47.5
        },
        {
          "param": "damping",
          "perturbation_pct": 20,
          "fe_rms_improvement_pct": 55.2
        }
      ],
      "sensitivity_worst_improvement_pct": 28.7,
      "fragile": false,
      "caveats": [
        "仿真模型由本波形反拟合，改进量是模型内推值，非实测",
        "未建模热效应与导轨磨损",
        "陷波深度在 −20% 共振频率扰动下改进量降到 28.7%，现场须按步骤 2 复测"
      ],
      "plots": [
        "validation/V1_compare.png",
        "validation/V1_spectral.png"
      ]
    }
  ],
  "safety": {
    "writes_to_device": false,
    "requires_human_approval": true,
    "hard_blocks": [
      "禁止在带工件/带负载状态下直接下发增益",
      "限位与安全回路未验证前不得关闭陷波"
    ],
    "disclaimer": "本输出为辅助诊断，参数下发前须由设备工程师现场确认。"
  },
  "audit": {
    "rules_fired": [
      "R-03a",
      "R-03b",
      "R-03c",
      "R-07",
      "R-11"
    ],
    "rules_skipped": [
      {
        "rule_id": "R-05",
        "reason": "依赖 crawling.low_speed_segments，本样本无恒低速段"
      }
    ],
    "assumptions": [
      {
        "anchor": "global.fe_rms_counts",
        "statement": "本示例的幅值一律以 counts 呈现，与 KB3 阈值逐格对齐；`inputs.counts_per_mm = 50000` 已知 ⟹ 可换算为 µm，但换算不改变判据档位（A-97 ①：`*_counts` 是历史名而非单位）"
      }
    ],
    "tier_ledger": [
      {
        "claim_id": "verdict.summary",
        "source_tier": "T1-a",
        "wording_ceiling": "实测支持该结论"
      },
      {
        "claim_id": "H1",
        "source_tier": "T1-a",
        "wording_ceiling": "实测支持现象，改进量为仿真验证",
        "validation_id": "V1"
      },
      {
        "claim_id": "recommendation.A1",
        "source_tier": "T3",
        "wording_ceiling": "改进量来自 P-B 仿真（T3），非现场实测；参数名口径未经外部核对",
        "validation_id": "V1"
      }
    ],
    "external_ledger": [
      {
        "claim_id": "recommendation.A1.field_procedure",
        "assertion_class": "3a",
        "external_reference": "memory",
        "verified_against": {
          "manual_id": null,
          "revision": null,
          "clause": null
        },
        "verified_by": "self",
        "artifact_path": null,
        "extracted": false,
        "note": "Pn 参数名/单位口径与 30 ms 验收限均未对厂商工件核对；未标档即默认 memory（规则 17a）。手册 8.9 那类可查事实由第三方会话读过，对我们是 public-doc、不计 k（规则 17b）"
      }
    ],
    "external_counts": {
      "verified": 0,
      "total": 1
    },
    "llm_calls": [
      {
        "stage": "verdict_narrative",
        "model": "…",
        "input_features_only": true
      }
    ],
    "deterministic_core_hash": "sha256:7615393524d62ea28a7ec607a173fad1ac4d9c6aa178242ee6f3657c37791f83",
    "human_review_checklist": [
      "确认 1181 Hz 不是编码器/电流采样噪声混叠",
      "确认机械结构近期无拆装"
    ]
  },
  "freq_limits": {
    "fs_hz": 8000.0,
    "nyquist_hz": 4000.0,
    "reliable_band_hz": 3200.0,
    "blocked_rules": [],
    "reason": null
  }
}
```

```json
{
  "schema": "axiscope.diagnosis/1",
  "case_id": "AX1-20260311-02",
  "generated_at": "2026-03-11T15:02:31+08:00",
  "engine_version": "0.1.0",
  "inputs": {
    "sample_id": "AX1-20260311",
    "present_channels": [
      "pos_cmd",
      "pos_fb",
      "fe",
      "cur_q"
    ],
    "missing_channels": [
      "vel_fb",
      "temp"
    ],
    "counts_per_mm": 50000.0,
    "drive_params_known": [
      "rigidity_level"
    ],
    "context_complaint": "高速取片后末端抖动，节拍被迫从 1.8s 放宽到 2.6s",
    "features_snapshot": "c2_example_a_no_events",
    "event_context_available": false
  },
  "verdict": {
    "primary": "H1",
    "summary": "首要解释是速度/位置前馈失配（S2、C=0.48）：`differential.asymmetry_ratio` 由 3 个 `move` 段给出、fe_rms 412.6 counts 在换向处不对称，反证是「本应出现的对称性未出现」。1.18 kHz 机械谐振（S3、C=0.65；反共振谷 440 Hz、λ≈6.2 的双惯量对，加减速瞬态在 settling 段 [0.089, 0.140] s 内激励该模态、ζ≈0.28 衰减）列 rank 2。**按 KB4 §2.9 字典序，第一排序键是 severity，S2 < S3 ⟹ 前馈居首**，其置信度反而更低（0.48 < 0.65）是证据强度与样本量所致，不是排序错误。下一步先做同一轨迹正反各 5 次重复，把方向性与工艺相关性分开，再评估是否在该频点加二阶陷波——改进量来自 P-B 仿真（V1），非现场实测；共振频率 −20% 扰动下最坏改进量 28.7%。置信度 0.43 = C(H1) 0.4818 × (1 − 0.05×2)，扣减按 2 个去重缺席原因（`absent_temp_channel`、`absent_events_jsonl`）。",
    "overall_confidence": 0.43,
    "confidence_note": "逐格可重算（KB4 §2.2/§2.3，规则 16/20）：H1（前馈失配，S2）两条支持 S = 0.518/0.494（`n/n_ref = 100/50` ⟹ `n_factor = 0.8`，样本量口径见 H1.scaffolding_note）⟹ A_sup = 0.507；反证 operator 是 `<` ⟹ rho_prime = 412.6/690 = 0.598 < 1 ⟹ v_j = 0.05（KB4 §2.4「本应出现的形态未出现」档；改判前的 1.672/0.10 是把 `<` 当 `>=` 取 value/threshold 的方向错值，A-101 ②）⟹ A_con = 0.05 ⟹ C(H1) = 0.48。H2（机械谐振，S3）六条支持 S = 0.459/0.768/0.765/0.779/0.680/0.609 ⟹ Smax = 0.779、Srest = 0.656、A_sup = 0.55×0.779 + 0.45×0.656 = 0.724；反证 rho_prime = 1.867 ∈ [1,2) ⟹ v_j = 0.10 ⟹ C(H2) = 0.65（逐格等于 KB4 算例 A）。**头条由 §2.9 的第一排序键 severity 决定**：S2 < S3 ⟹ H1 列 rank 1 且是 primary，尽管 C(H1) < C(H2)。verdict = 0.4818 × (1 − 0.05×2) = 0.43，扣减因子是 **2 个独立缺席原因**（`absent_temp_channel`、`absent_events_jsonl`），不是 3 条 `not_evaluable` 行（规则 17：族级标签与它覆盖的叶共享同一原因，只计一次）。",
    "actionable": true
  },
  "hypotheses": [
    {
      "id": "H1",
      "fault_mode": "electrical_feedforward_mismatch",
      "display_name": "加速度前馈失配（加/减速段跟随误差不对称）",
      "rank": 1,
      "confidence": 0.48,
      "severity": 2,
      "supporting_evidence": [
        {
          "feature": "ff_mismatch.asymmetry_ratio",
          "value": 2.26,
          "operator": ">=",
          "threshold": 1.5,
          "strength": 0.518,
          "rule_id": "R-15a",
          "source": "docs/kb/KB3-tuning-rules.md#R-15",
          "n": 100.0,
          "n_ref": 50.0,
          "conf": 1.0,
          "freq_hz": null,
          "band_floor_hz": null
        },
        {
          "feature": "ff_mismatch.fe_vs_accel_corr",
          "value": 0.83,
          "operator": ">=",
          "threshold": 0.6,
          "strength": 0.494,
          "rule_id": "R-15b",
          "source": "docs/kb/KB3-tuning-rules.md#R-15",
          "n": 100.0,
          "n_ref": 50.0,
          "conf": 1.0,
          "freq_hz": null,
          "band_floor_hz": null
        }
      ],
      "contradicting_evidence": [
        {
          "feature": "ff_mismatch.accel_regime_rms_counts",
          "value": 690.0,
          "operator": "<",
          "threshold": 412.6,
          "rho_prime": 0.598,
          "penalty": 0.05,
          "rule_id": "R-15c",
          "note": "加速区 RMS 未超过全局 fe RMS ⟹ 不对称主要来自减速侧，与纯前馈不足的典型形态不完全吻合；扣分项，非否决项。operator 是 `<` ⟹ §2.1(a) 的 ρ′ = threshold/value = 412.6/690 = 0.598 < 1，落 §2.4 的「本应出现的形态未出现」档 ⟹ v_j = 0.05。原写 rho_prime = 1.672 是把 `<` 当 `>=` 取 value/threshold 的方向错值，penalty 0.10 随之错（A-101 ②）"
        }
      ],
      "recommendation": null,
      "ruled_out_alternatives": [],
      "next_data_to_collect": [
        {
          "ask": "同一轨迹、同一方向重复 5 次，另加 5 次反向",
          "why": "当前 `asymmetry_ratio` 只有 3 个 `move` 段样本，方向性与工艺相关性分不开",
          "unlocks": [
            "R-15 的 kff 分支判定（A-26：该量有符号，必须镜像）",
            "R-08 间隙的分离（无反向段时不可分）"
          ]
        }
      ],
      "scaffolding_note": "本假设的样本量是**示例自己声明的脚手架**：C2 没有承载加/减速区样本数的字段（与 `rule_table.open_gaps` 记的 Welch 段数、带内 bin 数同族，A-102 ② 只补了 resonance 侧）⟹ 故 `n = 100` 是示例给定的假定值，`n_ref = 50` 取 KB3 R-15 必要上下文「加减速区样本各 ≥ 50」。两条 `strength` 因此是 KB4 §2.1 的复算值，不是文档抄来的数——引擎在本快照上不 fire R-15（缺 n/n_ref ⟹ `rules_skipped`），本示例展示的是「样本量补齐之后」的形状。"
    },
    {
      "id": "H2",
      "fault_mode": "mechanical_resonance",
      "display_name": "机械谐振（结构模态被瞬态激励）",
      "rank": 2,
      "confidence": 0.65,
      "severity": 3,
      "supporting_evidence": [
        {
          "feature": "resonance.candidates[0].coherence_torque_velocity",
          "value": 0.86,
          "operator": ">=",
          "threshold": 0.7,
          "strength": 0.459,
          "condition_index": 2,
          "rule_id": "R-03a",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "window": {
            "t0": 0.089,
            "t1": 0.14,
            "segment_id": 1
          },
          "plot": "evidence/resonance_coherence.png",
          "n": 8.0,
          "n_ref": 4.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].amplitude_ratio_vs_broadband",
          "value": 8.4,
          "operator": ">=",
          "threshold": 4.0,
          "strength": 0.768,
          "condition_index": 3,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 96.0,
          "n_ref": 15.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].quality_factor_estimate",
          "value": 27.0,
          "operator": ">=",
          "threshold": 10.0,
          "strength": 0.765,
          "condition_index": 7,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 22.0,
          "n_ref": 8.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].present_in_dwell",
          "value": true,
          "operator": "==",
          "threshold": true,
          "strength": 0.779,
          "condition_index": 4,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 3.0,
          "n_ref": 1.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].present_in_rest",
          "value": false,
          "operator": "==",
          "threshold": false,
          "strength": 0.68,
          "condition_index": 5,
          "rule_id": "R-03b",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 2.0,
          "n_ref": 1.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        },
        {
          "feature": "resonance.candidates[0].tracks_command_frequency",
          "value": false,
          "operator": "==",
          "threshold": false,
          "strength": 0.609,
          "condition_index": 6,
          "rule_id": "R-03",
          "source": "docs/kb/KB3-tuning-rules.md#R-03",
          "n": 6.0,
          "n_ref": 4.0,
          "conf": 1.0,
          "freq_hz": 1181.0,
          "band_floor_hz": 2000.0
        }
      ],
      "contradicting_evidence": [
        {
          "feature": "step_response[0].damping_ratio_estimate",
          "value": 0.28,
          "operator": ">",
          "threshold": 0.15,
          "rho_prime": 1.867,
          "penalty": 0.1,
          "rule_id": "R-03c",
          "note": "阻尼不算极低，说明谐振峰不算尖锐，与 Q≈27 一致但削弱'严重共振'的判断。`penalty` 不是自由参数：rho_prime 落在 [1,2) ⟹ 取 KB4 §2.4 的 v_j = 0.10（规则 16）"
        }
      ],
      "ruled_out_alternatives": [
        {
          "fault_mode": "mechanical_encoder_periodic_error",
          "display_name": "编码器每转周期误差（偏心/刻线误差）",
          "why": "ripple.probing[].dominant_order_per_rev 未与每转周期锁定，且 encoder.per_rev_amplitude_counts 仅占 global.fe_rms_counts 的 23%",
          "rule_id": "R-07"
        }
      ],
      "recommendation": {
        "action_id": "A1",
        "class": "notch_filter",
        "params": {
          "center_hz": 1181.0,
          "width_hz": 470.0,
          "q": 2.5,
          "depth_db": -20.0,
          "cascade_second_notch_at_2f": true
        },
        "rationale": "峰频 1181 Hz，按 峰频/2.5 取宽度以避免过度削相位；第二陷波针对 2f 谐波（≈2362 Hz），不是针对反共振谷——共置构型下反共振谷在峰下方（440 Hz，f_m/f_a = sqrt(1+λ)，λ≈6.2），在谷上加陷波只会进一步削掉可用带宽（A-1）。",
        "risk": "陷波会削弱该频段的指令跟踪带宽；若实际为电气噪声而非结构模态，将导致位置环响应变钝。",
        "reversibility": "参数级，写入驱动器寄存器即可，可回读原值",
        "requires_offline": false,
        "expected_effect": {
          "metric": "fe_rms_counts",
          "from": 412.6,
          "to": 155.1,
          "improvement_pct": 62.4,
          "basis": "simulation_validated",
          "validation_id": "V1",
          "derivation": "to = 实测 412.6 × (V1.candidate 152.3 / V1.baseline 405.1)。V1 基线是仿真复现值，与实测 412.6 的差是复现残差（fit_residual_pct 8.4），不是笔误；两者必须分列，否则读者会把仿真当实测。",
          "caveat": "改进量来自 P-B 双惯量仿真，非现场实测；共振频率 −20% 扰动下最坏改进量 28.7%（见 V1.sensitivity）"
        },
        "field_procedure": [
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 1. 备份当前 Pn 参数表并截图（参数名与单位口径未经手册核对）",
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 2. 先只加第一陷波，做 3 次全行程定位，观察 1181 Hz 峰是否下降 >10 dB",
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 3. 若在 2f（≈2362 Hz）出现新峰抬升，补第二陷波；若 440 Hz 反共振谷附近的响应被一起削平，说明陷波带过宽、正在吃掉有效带宽，回退一档",
          "[L1|真值来源=③a 手册可查|核对=memory|执行者=人工] 4. 每次改动后重新测量 settling_time_ms，超过 30 ms 则回退一档增益（30 ms 属机台验收限，非手册已核对值）"
        ]
      },
      "next_data_to_collect": [
        {
          "ask": "补采 0-2 kHz 的 Bode 图（位置环开频响应）",
          "why": "当前带宽为命令响应间接估计，置信度 0.6，不足以确认陷波后相位裕度",
          "unlocks": [
            "R-03d 相位裕度校验",
            "陷波深度上限判定"
          ]
        },
        {
          "ask": "导出 temp 通道，或提供冷机/热机各一组同轨迹波形",
          "why": "操作员备注'运行 40 分钟后变差'，当前无法区分谐振漂移与温漂",
          "unlocks": [
            "H3 热漂移假设的判定"
          ]
        }
      ]
    }
  ],
  "differential": {
    "considered": [
      "mechanical_resonance",
      "electrical_feedforward_mismatch",
      "mechanical_crawling",
      "mechanical_encoder_periodic_error",
      "mechanical_thermal_drift",
      "electrical_position_pi_detune",
      "mechanical_backlash",
      "software_induced_pulse_eq_overwritten",
      "software_induced_host_thread_jitter"
    ],
    "considered_display_names": {
      "electrical_feedforward_mismatch": "前馈失配（旧示例写作 feedforward_mismatch）",
      "mechanical_encoder_periodic_error": "编码器每转周期误差（旧：encoder_eccentricity）",
      "mechanical_thermal_drift": "热漂移（旧：thermal_drift）",
      "electrical_position_pi_detune": "增益过高自激（旧：gain_too_high_hunting / limit_cycle）",
      "mechanical_crawling": "摩擦爬行（旧：friction_crawling）"
    },
    "not_evaluable": [
      {
        "fault_mode": "mechanical_thermal_drift",
        "blocked_by": "absent_temp_channel",
        "why": "缺 temp 通道，且无冷热机对比（结构性真空，A-64：本案例族无对外正例来源）"
      },
      {
        "fault_mode": "software_induced_host_thread_jitter",
        "blocked_by": "absent_events_jsonl",
        "why": "本样本无 events.jsonl ⟹ 跟随误差尖峰与上位机调度抖动在结构上不可分"
      },
      {
        "family": "software_induced_error",
        "blocked_by": "absent_events_jsonl",
        "why": "事件层缺席使整族降级为不可评估。族级标签只在这里出现，不进 hypotheses（A-18）"
      }
    ]
  },
  "validation": [
    {
      "id": "V1",
      "action_id": "A1",
      "method": "two_inertia_sim",
      "verification_level": "L1",
      "plant_id": "P-B",
      "plant_source": "docs/kb/KB5-simulation-plant.md#P-B",
      "plant_fit": {
        "inertia_ratio_fitted": 6.2,
        "resonance_hz": 1181.0,
        "antiresonance_hz": 440.0,
        "damping_fitted": 0.28,
        "fit_residual_pct": 8.4,
        "sensor_config_used": "motor_side"
      },
      "replay_check": {
        "passed": true,
        "max_normalized_error": 0.061
      },
      "baseline": {
        "fe_rms_counts": 405.1,
        "settling_time_ms": 41.6,
        "overshoot_pct": 9.8,
        "dominant_peak_db": 18.3
      },
      "candidate": {
        "fe_rms_counts": 152.3,
        "settling_time_ms": 18.9,
        "overshoot_pct": 3.1,
        "dominant_peak_db": 4.6
      },
      "improvement": {
        "fe_rms_pct": 62.4,
        "settling_pct": 54.6
      },
      "stability": {
        "phase_margin_deg": 41.2,
        "gain_margin_db": 8.7,
        "new_peak_check": "候选频谱未出现基线没有的 >50% 主峰峰 ⟹ 未激发新模态"
      },
      "sensitivity": [
        {
          "param": "inertia_ratio",
          "perturbation_pct": -20,
          "fe_rms_improvement_pct": 44.1
        },
        {
          "param": "inertia_ratio",
          "perturbation_pct": 20,
          "fe_rms_improvement_pct": 51.0
        },
        {
          "param": "resonance_hz",
          "perturbation_pct": -20,
          "fe_rms_improvement_pct": 28.7
        },
        {
          "param": "resonance_hz",
          "perturbation_pct": 20,
          "fe_rms_improvement_pct": 33.9
        },
        {
          "param": "damping",
          "perturbation_pct": -20,
          "fe_rms_improvement_pct": 47.5
        },
        {
          "param": "damping",
          "perturbation_pct": 20,
          "fe_rms_improvement_pct": 55.2
        }
      ],
      "sensitivity_worst_improvement_pct": 28.7,
      "fragile": false,
      "caveats": [
        "仿真模型由本波形反拟合，改进量是模型内推值，非实测",
        "未建模热效应与导轨磨损",
        "陷波深度在 −20% 共振频率扰动下改进量降到 28.7%，现场须按步骤 2 复测"
      ],
      "plots": [
        "validation/V1_compare.png",
        "validation/V1_spectral.png"
      ]
    }
  ],
  "safety": {
    "writes_to_device": false,
    "requires_human_approval": true,
    "hard_blocks": [
      "禁止在带工件/带负载状态下直接下发增益",
      "限位与安全回路未验证前不得关闭陷波"
    ],
    "disclaimer": "本输出为辅助诊断，参数下发前须由设备工程师现场确认。"
  },
  "audit": {
    "rules_fired": [
      "R-03a",
      "R-03b",
      "R-03c",
      "R-07",
      "R-11"
    ],
    "rules_skipped": [
      {
        "rule_id": "R-05",
        "reason": "依赖 crawling.low_speed_segments，本样本无恒低速段"
      }
    ],
    "assumptions": [
      {
        "anchor": "global.fe_rms_counts",
        "statement": "本示例的幅值一律以 counts 呈现，与 KB3 阈值逐格对齐；`inputs.counts_per_mm = 50000` 已知 ⟹ 可换算为 µm，但换算不改变判据档位（A-97 ①：`*_counts` 是历史名而非单位）"
      },
      {
        "anchor": "R-15",
        "statement": "H1（前馈失配）的 severity 取 KB4 §2.9 的 S2 行（按后果类型归档），属裁决分类锚点、非独立观测锚 ⟹ 不得写成唯一结论（A-100 ⑤）"
      },
      {
        "anchor": "R-03",
        "statement": "H2（机械谐振）的 severity 取 §2.9 的 S3 行；rank 1/2 的先后由 severity 这一第一排序键决定（规则 20），与 C(H1)=0.48 < C(H2)=0.65 不矛盾"
      }
    ],
    "tier_ledger": [
      {
        "claim_id": "verdict.summary",
        "source_tier": "T1-a",
        "wording_ceiling": "实测支持该结论"
      },
      {
        "claim_id": "H1",
        "source_tier": "T2",
        "wording_ceiling": "按 <出处> 的阈值",
        "validation_id": null
      },
      {
        "claim_id": "H2",
        "source_tier": "T1-a",
        "wording_ceiling": "实测支持现象，改进量为仿真验证",
        "validation_id": "V1"
      },
      {
        "claim_id": "recommendation.A1",
        "source_tier": "T3",
        "wording_ceiling": "改进量来自 P-B 仿真（T3），非现场实测；参数名口径未经外部核对",
        "validation_id": "V1"
      }
    ],
    "external_ledger": [
      {
        "claim_id": "recommendation.A1.field_procedure",
        "assertion_class": "3a",
        "external_reference": "memory",
        "verified_against": {
          "manual_id": null,
          "revision": null,
          "clause": null
        },
        "verified_by": "self",
        "artifact_path": null,
        "extracted": false,
        "note": "Pn 参数名/单位口径与 30 ms 验收限均未对厂商工件核对；未标档即默认 memory（规则 17a）。手册 8.9 那类可查事实由第三方会话读过，对我们是 public-doc、不计 k（规则 17b）"
      }
    ],
    "external_counts": {
      "verified": 0,
      "total": 1
    },
    "llm_calls": [
      {
        "stage": "verdict_narrative",
        "model": "…",
        "input_features_only": true
      }
    ],
    "deterministic_core_hash": "sha256:7f986a75c0c96c935d464f56032e92694817d44d48a55f7b4d79feb804e186f8",
    "human_review_checklist": [
      "确认 1181 Hz 不是编码器/电流采样噪声混叠",
      "确认机械结构近期无拆装"
    ]
  },
  "freq_limits": {
    "fs_hz": 8000.0,
    "nyquist_hz": 4000.0,
    "reliable_band_hz": 3200.0,
    "blocked_rules": [],
    "reason": null
  }
}
```

## 不可协商的规则

1. **每条 `hypothesis` 至少 2 条 `supporting_evidence`**，每条证据必须是
   `C2 特征路径 + 实测值 + 规则 ID + 出处链接`。
   任何不满足此条件的假设必须降级到 `differential.considered`，不得进入 `hypotheses`。
   这是防 LLM 幻觉的结构性约束——LLM 只能引用已存在的特征路径，不能自己造数值。
2. **`contradicting_evidence` 必须显式填写**，哪怕是空数组。规则引擎必须对每个 top-3 假设
   主动跑一遍反证判据。只报支持证据的诊断报告在内行眼里等于没做。
3. **`confidence` 的计算是确定性的**（见 `KB4-attribution-model.md` 的加权公式），
   LLM 只能改写 `display_name` 与 `rationale` 的措辞，**不能改数值**。
4. **`expected_effect.basis` 只有三个合法值**：
   - `simulation_validated` — 有 V* 记录支撑
   - `rule_heuristic` — 仅经验规则推断，无仿真
   - `unverified` — 不给数字，只给方向
   禁止出现无 `basis` 的改进百分比。这是本项目的核心差异化，不能含糊。
5. **`next_data_to_collect` 是 agent 的迭代接口**：置信度低于 0.6 时该字段不得为空，
   必须明确"还缺什么数据、补上后能解锁哪条判据"。
6. **`safety.writes_to_device` 恒为 false**。本智能体永不直接下发参数到真机。
   面试叙事里这是加分项而非限制。
7. `verdict.summary` 面向工程师，必须包含：定位到的频点/时间窗/量级、建议动作、预期效果及其依据层级。
   禁止"可能是多种因素共同作用"这类无信息表述。
8. **三方归因族必须同时存在**：`fault_mode` 取自三个并列家族，缺任一家族即视为设计缺陷——
   - `mechanical_*`：谐振、摩擦爬行、偏心、导轨磨损、松动、热漂移
   - `electrical_*`：增益过高自激、限流饱和、编码器噪声、接线/屏蔽、电流采样混叠
   - `software_induced_*`：上位机线程调度抖动、插补缓冲欠载、总线丢周期、视觉结果晚到、
     脉冲当量/单位口径被换型流程覆盖

   第三族是本项目的差异化所在：伺服厂商调谐工具只看驱动器内部通道，**结构上看不到软件侧**。
   它的缺席不是"少了一类故障"，而是让前两类被系统性误判——
   调度抖动造成的跟随误差尖峰在波形上与机械冲击难以区分。
9. **`differential.not_evaluable` 不得为空数组除非真的全部可评估**。
   每个因缺通道、缺事件流、超频带、缺定标系数而无法评估的故障模式，
   都必须逐条列出并写明缺什么。沉默会让报告看起来比实际更有把握，
   这是工业诊断 agent 最危险的失效模式（对应 C5 的"拒答正确率"指标）。
10. **`hypotheses[].fault_mode` 与 `ruled_out_alternatives[].fault_mode` 必须取 KB0 §2 的
    全量 slug**（`mechanical_*` / `electrical_*` / `software_induced_*`）。
    本文件示例早期写作 `feedforward_mismatch`、`encoder_eccentricity`、`friction_crawling`、
    `thermal_drift`、`gain_too_high_hunting`、`limit_cycle` 等**显示名**，它们只能是
    `display_name` 字段的内容，绝不能再出现在 `fault_mode` 里——否则 C5 的真值标签对不上，
    评测分母会静默错位。`differential.considered` 允许显示名，因为它是给人读的清单。
11. **门禁 / 拒答规则是一等公民**：`R-25`（频带不可见性）、`R-30`（软件族登记义务）、
    KB6 的 `R-37`/`R-49`/`R-50`、C7 的采样率门禁都没有 `fault_mode`（`family: null`），
    它们的输出是"登记义务"而不是假设：进 `differential.not_evaluable` 与
    `audit.rules_fired`，**不进** `hypotheses[]`，且计入 C5 的拒答正确率。
    缺了这一类，"没有真值时拒答"的设计在报告结构里无处安放。
12. **`differential` 允许"只有 `not_evaluable`、`considered` 为空"的形状**，
    且必须原样呈现（例 B 类数据上整条谐振族被阻塞时，这就是唯一诚实的输出）。
13. `hypotheses[].severity`、`supporting_evidence[].strength`、`contradicting_evidence[].penalty`
    为**必填的确定性数值**，由 KB4 §2 的公式产出，参与排序链，不得只在 `rationale` 里用文字描述。
    本示例的 `0.65 / 0.59` 是按 KB4 §2.3 重算后的值（早期草稿写 `0.78`，未对反证、样本量与
    `not_evaluable` 扣分，已作废）。报告里一律以引擎输出为准，实现以 KB4 为准。
14. **叙述层措辞不得强于数据层证据等级**（机器可判定，非口号）。
    每条结论在 `audit.tier_ledger[]` 里带 `source_tier`（A-54：权威名，旧称 `evidence_tier` 已废；
    与 C1 `meta.source.tier`、C5/KB8 案例行的 `source_tier` 同一值域）；报告文本里出现
    「已核对 / 已验证 / 现场确认 / 手册原文确认 / 实测通过」类措辞而该结论 `source_tier < T1` 时，
    **生成期直接拒绝出报告**，而不是降级成一句 disclaimer。
    检查器读的是 `tier_ledger`，不是散文——所以每条面向外的结论都必须有一行台账；
    缺行 ⟹ 该结论视为 `T3`（最保守档），这比"没标注就当没这事"安全。
    这条规则有一个真实的外部失效案例作依据：第三方实现的数据层诚实标着 `verified: "public-doc"`
    （62 处），而其**面向外部的两份文档**却写成"已对照厂商官方手册原文核对"
    （见 `docs/AUDIT-minimax-round3.md` §二）。措辞升格只发生在被读到的那一层，
    审计者读到那句话就会停止怀疑——这是最难发现、也最贵的一类失效模式。
15. **示例数字必须逐格可重算，`penalty` 只能取档位值**（A-72，规则 13 的可执行化；A-101 扩）。
    早期草稿把 `strength`/`penalty` 当自由小数写（`0.11`、`0.18`），而 KB4 §2.4 的 `v_j`
    是**离散档位** `{0.20, 0.10, 0.05, 0.00}`，由 `rho_prime` 落在哪个区间决定。
    现在：每条反证必须同时给 `rho_prime` 与 `penalty`，且 `penalty` 是 `rho_prime` 的函数——
    给不出 `rho_prime` 的扣分就是拍出来的扣分。**`rho_prime` 的取向跟着 `operator`**（A-101 ②）：
    `>=` 类条件取 `value/threshold`，`<` 类条件取 `threshold/value`；本示例 H2 早期写 `1.672 / 0.10`
    就是把 `<` 当 `>=` 的方向错值，正确值 `412.6/690 = 0.598` 落 `ρ′ < 1` 档 ⟹ `v_j = 0.05`。
    同理 `confidence` 不得手填：示例 H1 的 `0.65` 由六条支持证据的 `S(e)`（逐格等于 KB4 算例 A）
    经 §2.2 公式得出，本文件任何改动若让重算结果与标注值不符，视为缺陷而非"示意"。
    **`strength` 也不是自由数**（A-101 ①）：每条 `supporting_evidence` 必须自带 §2.1 的五个原始字段
    `n` / `n_ref` / `conf` / `freq_hz` / `band_floor_hz`（比值类判据 `freq_hz`/`band_floor_hz` 可为
    `null`），校验器据此**独立复算** `S(e)`，不吃自报 `strength`。缺字段不判失败，但必须显式落一条
    非阻塞检查 `C3-R15-recompute-gap/<H#>`（缺字段是上游契约的欠规范，不是这条报告的错），
    且该示例**不得**再被引用为验收锚点（KB0 §6 检查 26）。反面证据：H2 草稿值 `0.36` 反解要
    `n_factor = 0.583`，低于 KB4 §2.1(c) 的下限 `0.6` ⟹ 在任何 `n/n_ref` 下都复算不出来，
    "手写"这件事本身现在是可判定的。
16. **`overall_confidence` 的缺席扣减按"独立缺席原因"计，不按登记行数**（A-73）。
    每条 `not_evaluable` 必须带 `blocked_by`（缺失输入的稳定键名，如 `absent_temp_channel`、
    `absent_events_jsonl`），扣减因子取 **`blocked_by` 去重后的个数**：
    `verdict.overall_confidence = C(H_primary) × (1 − 0.05 × min(4, |distinct blocked_by|))`。
    为什么不能数行数：族级标签（A-18 的 `software_induced_error`）与它覆盖的每个叶
    源于**同一个缺席输入**，一行一条会让"缺一路通道"的惩罚随该族叶子数线性膨胀——
    本例 3 行 = 2 个原因 ⟹ ×0.90，若按行数则 ×0.85，同一份数据因描述粒度不同而给出不同置信度，
    校准（C5 的 ECE）就失去意义。键名由 C1/C2 的通道与文件清单锚定，不许自由造。
17. **接口事实的核对状态要有台账，且"谁核的"不可转借**（A-88/A-89；与规则 4 的 `basis`、规则 14 的
    `source_tier` **三方正交**，不得互相抵扣）。`audit.tier_ledger` 只管"数据是哪一档"，管不了
    "这句话的外部依据是哪一档"，故新增：

    ```json
    "external_ledger": [
      {"claim_id": "R-22-signature-table[2]", "assertion_class": "3a",
       "external_reference": "official-artifact",
       "verified_against": {"manual_id": "ZMotion PC 函数库编程手册", "revision": "V2.1.4", "clause": "8.9"},
       "verified_by": "self", "artifact_path": "docs/evidence/…", "extracted": true}
    ],
    "external_counts": {"verified": 0, "total": 0}
    ```

    五条口径，全部机器可判定：
    (a) **未标档 ⟹ 按最低档 `memory`**（A-71 同调：缺行按最低档，不是按"没标注就当没这事"）。
    (b) `external_reference = official-artifact` 时 `artifact_path` **必须在本仓库内可解析**；
        文件不在库里就降为 `public-doc`，措辞天花板随之下降。存证的读手册动作也算：
        `verified_by ∈ {self, third_party_report}`，**只有 `self` 计入 `external_counts.verified`**（A-89）。
    (c) `extracted: true`（机器抽取）优先于手读；抽取覆盖不到的行用 **`extracted: false`** 表示，
        文档侧对它的称呼是 `unverified_signature`——**JSON 里不出现第二个字段名**（A-54"只有一个名字"同律）。
        参数顺序/语义、调用序列前提、"该不该写 `0x6040`"这三类**天然不可抽取**，永远只能是 `extracted: false`。
    (d) `external_counts.verified == 0` 且 `total > 0` ⟹ 相关叙述封顶
        **"样板就绪，签名与位号未经外部核对"**；"清单已生成"不得抵扣上机工时（A-88）。
    (e) `assertion_class = "3b"`（批次与现场）**只有** `external_reference = vendor_reply`
        （书面答复 + 日期 + 适用型号）能使其离开待确认态；`official-artifact` 不行。
        登记为 3b 时必须举证"手册为什么答不了"，否则判缺陷（KB0 §6 检查 21）。

    为什么这条要进硬性规则而不是注释：本仓库此前把 `dmc_vmove` 的正负编码登记成"只能问厂商"，
    而手册 8.9 里有答案——**登记错误的代价不是措辞不雅，是白付等待成本 + 挂一条永远闭不了的
    `field_procedure`**（A-89）。台账让"未知"变成可数的量，才算得出哪些未知其实可自查。

18. **示例声明的前提必须有仓内载体，且与 `inputs` 层可判定同构**（A-99 ③，机器可判定）。
    凡契约附带的示例引用一份特征快照，必须在 `inputs.features_snapshot` 里点名 `examples/` 下的
    裸文件名（禁路径分隔符与 `..`），并把它的前提写进 `inputs`：`present_channels` 与
    `event_context_available`。校验器逐字段比对二者（`C3-R18-name/-exists/-parse/-channels/-events`），
    **快照文件缺失即判失败**——声明了不可解析的前提来源，等于该断言没有可重跑产物（检查 27 同律）。
    引擎自己产出的报告不带 `features_snapshot`（它手里就有真的 `event_context`），本条自然跳过。
    为什么这条要硬化：本示例曾宣称"0.59 是没有 events.jsonl 的场景"，而它引用的 C2 例 A 快照
    `event_context.available = true`；同一 `case_id` 下三份材料（C2 例 A、KB4 算例 A、C3 示例）
    两两互斥，靠散文互相"解释"了很久都没人发现（A-99）。前提现在有了文件
    （`examples/c2_example_a_no_events.json`，母本的无事件孪生，除 `event_context` 一块外逐字段相同），
    **前提不同就换 `case_id`**，A-77 的 `case_id` 唯一性由此从命名纪律扩到示例层。
    配套事实（同一轮实测）：`engine.analyze(c2_example_a)` 的头条是软件族（S2 排 S3 之前，`overall=0.42`），
    `engine.analyze(c2_example_a_no_events)` 才只剩谐振、`overall` 恰为 0.59——两份输入都进了测试，
    这条区分不再只存在于文档里。

19. **`audit.assumptions[]` 是 `{anchor, statement}` 行——散文不是锚**（#25，机器可判定；
    形状的唯一真值在 C1 §audit.assumptions，本条只核 C3 侧，两处共用 `anchors.py` 的一张词表）。
    `anchor` 必须落在六种稳定形式之一（`meta.<字段路径>` / 通道（`channels.<名>`、
    `extra_channels.<名>`）/ C2 特征路径 / `R-<nn>[#支]` / KB4 叶名 / `KB<n>§<节>`），
    `statement` 必须非空；校验器逐行判 `C3-R19-assumption-shape[<i>]`，元素是字符串即失败。
    本条只管 `assumptions`：`audit.arbitration_notes` 是仲裁过程记录、不是假定，仍是散文行，
    不得顺手改成对象（改了就没有生产者读它）。
    为什么要硬化：全仓有约 30 处"记入 `audit.assumptions`"的义务（C1/C2/C6/C7/KB3/KB4/KB6），
    却从未定义过元素的形状——接入层与引擎各自产散文，报告只能整段打印，于是
    **"这条假定作废时哪些结论跟着塌"在契约层无法回答**，C5 的拒答正确率也没法引用某一条假定。
    两侧示例各挂两行做载体（KB0 §6 检查 23；C3 侧随 A-107 ③ 拆示例后为 **E1 1 行 / E2 3 行**，
    由 `test_rule19_carriers_exist_in_both_examples` 逐份核对），实测（含 A-102 ④ 的缺 `n_source` 配方留痕：R-04/R-15
    因 rule_table 未登记配方而不可评分时，引擎补一行锚 `KB4§2.1(c)` 的登记）：
    `meta.audit.assumptions` 恒 6 行（C1 侧，引擎改动不触及）；引擎报告 1–4 行——c2 例 A、其无事件孪生
    与 KB4 算例 B 上 R-15 实际触发缺配方的不可评分，无侧车 2 行、带 `sample_counts` 侧车各再加两行 = 4 行；
    c2 例 B 与 Export10 不触发该留痕，仍无侧车 1 行（τ_u 或一条 severity）/ 带侧车 3 行；全部过词表。

20. **`hypotheses[].rank` 必须等于 KB4 §2.9 的字典序，`verdict.primary` 必须等于 rank 1 的那条**
    （A-107 ③，机器可判定：`C3-R20-rank-monotonic` / `C3-R20-rank-contiguous` / `C3-R20-primary-is-rank1`）。
    排序键按 §2.9 是 `(severity↑, −C, coverage↓, rule_id)`，S0 最严重 ⟹ 数值小者在前。
    **报告里四键只有两键有载体**：`hypotheses[]` 带 `severity` 与 `confidence`，没有 `coverage`
    也没有 `rule_id`（引擎内部用它们排序，但没写进产物）⟹ 本检查按可判前缀 `(severity↑, −C)` 严格判，
    并列时用 `fault_mode`（报告里唯一稳定的第三键）兜底，序仍然可复现；
    `coverage`/`rule_id` 的载体缺失另记台账，补齐后本条即扩成四键全序。
    **缺口已由 A-115（2026-10-21）复算并裁为"不补"**：引擎 `engine.py::_coverage(features, res)`
    虽然存在，但它**完全不看 `res`**，只取 `segment_coverage` 的计数总和是否非零 ⟹ 对同一份特征包
    的所有假设返回同一个 `1.0`（无段时 `0.0`）；即"受影响面"这把尺子在实现里是**恒等量、不参与区分**，
    所以 §2.9 的四键实际只有三键在起作用（`(severity↑, −C, rule_id)`）。本仓复算：Export10 包、c2 例 A
    的无事件孪生与 c2 例 B 的 `hypotheses[]` 均为空（0 条，无假设可排），c2 例 A 与 KB4 算例 B 各只
    排出 1 条（rank 1、S2、C=0.44）⟹ **仓内现有样本没有任何并列，这把恒等键在当前数据上不可观测**；
    唯一排两条以上的是 `tests/test_c3validate.py::test_rule20_catches_the_pre_split_merged_example`
    重建的 E2，而它按本条的可判前缀判序。**本条原句"没有 `coverage` 也没有 `rule_id`"要收窄一档**：
    `rule_id` 在产物里是**逐证据**存在的（`hypotheses[].supporting_evidence[]` 实测 13 键：
    `feature/value/operator/threshold/strength/n/n_ref/conf/freq_hz/band_floor_hz/condition_index/rule_id/source`），
    缺的只是"假设级"那个聚合排序键；真正**全产物无载体**的是 `coverage`——它只在
    `unavailable[].reason` 的散文里以 `segment_coverage.<kind>` 的字样出现，没有任何结构化字段。
    补齐的前提是**每条证据行带它来自哪个窗口/段 kind**——`engine.py::_evidence_rows` 现在的字段是
    `feature/value/operator/threshold/strength/n/n_ref/conf/freq_hz/band_floor_hz/condition_index/rule_id/source`，
    没有窗口，"覆盖占比"的分母因此无出处；硬造一个分母属 A-110 尺子里的"造数"，A-102 也禁止反推凑载体
    ⟹ **本条维持 `(severity↑, −C, fault_mode)` 的可判前缀 + 兜底第三键，不改检查、不扩键**；
    待 C2 侧给出窗口出处后，再按本条末句扩成四键全序。
    为什么要立这一条：排序此前**只存在于散文里**。E2 的前身（两条并存的旧示例）把 S3 的谐振写成
    rank 1、`overall = 0.59`，算术全部正确，矛盾只在示例内部自我声明了一句
    （A-107：第一条"示例算术对、排序错"而校验器全绿的条目）。检查 26 的"零 gap 复算"当时只覆盖
    数值不覆盖顺序，所以本条把顺序也纳入示例必须自证的范围内。
    这一条的检测力由可重跑产物钉住（检查 27）：`tests/test_c3validate.py::test_rule20_catches_the_pre_split_merged_example`
    按旧形状重建那份示例并实测——重建体共 **93 项检查**，翻红的是
    `C3-R20-rank-monotonic` + `C3-R20-primary-is-rank1` + `C3-R21-core-hash-recompute`
    **3 项、其余 90 项全绿**（含 `C3-R16-overall` 与两条 `C3-R03-recompute`，即"算术对、排序错"确实抓得住）。
    **规则 21 落码后这条检测由两道网兜住**（2026-10-21）：排序错既被规则 20 的字典序判红，也被
    规则 21 的哈希复算判红（`rank` 序在哈希核里、叙述层不在）⟹ E2 的检查总数由 90 涨到 93、
    重建体的翻红数由 2 涨到 3，两处都是规则 21 新增的三项检查所致，不是口径放宽。

21. **`audit.deterministic_core_hash` 的哈希核由本条唯一定义**（#43 前半；A-116 ② 的处置 = 先定契约、后落码，
    不许为了圆 KB4 §2.9 那句话随手实现一个哈希）。动机一句：KB4 §2.9 写"四个键均来自确定性数据，保证
    `deterministic_core_hash` 可复现"，而 A-116 实测该字段**无生产者**（`engine.py:708` 恒写空串）、
    **无定义**（全仓 0 处定义"哪些字段进哈希"），且 §2.9 的第三键在实现里是恒等量（A-115）⟹
    本条把「哪些字段进哈希 / 怎么规范化 / 什么时候允许空」一次写死，落码侧与校验器复算侧必须按本条，不得各自发明。

    **纳入哈希核的字段（唯一清单）**：`schema`、`case_id`、`inputs` 的**全部键**、
    `verdict.primary`、`verdict.overall_confidence`、`verdict.actionable`、
    每条 `hypotheses[]` 的 `id`/`fault_mode`/`rank`/`confidence`/`severity`/`next_data_to_collect`
    加其 `supporting_evidence[]` 与 `contradicting_evidence[]` 的**全部结构化键**（13 键全在，含 `rule_id`——
    A-115 收窄过：证据级 `rule_id` 是有载体的）、`differential`（含 `considered`/`not_evaluable` 的
    `fault_mode` 与固定句式 `reason`）、`validation` 的断言结果、`safety`、`freq_limits`、
    `audit.rules_fired`、`audit.rules_skipped`（`rule_id` + 原因键）、`audit.assumptions[].anchor`。

    **排除的四类，各带一条理由**：①**自由叙述**——`verdict.summary`、`verdict.confidence_note`、
    `hypotheses[].recommendation`、`hypotheses[].display_name`、`hypotheses[].scaffolding_note`、
    `ruled_out_alternatives[]`、`assumptions[].statement`、`human_review_checklist`、`llm_calls[].model`：
    由 LLM 或人工撰写，同输入可以不同文本，纳入就等于把哈希当成"文案改动探测器"；
    固定句式的可复现性由测试钉（A-111 已把 `NSOURCE_GAP_SENTENCE` 逐字钉死），不由哈希钉。
    ②**时钟与版本**——`generated_at`、`engine_version`：跨版本对拍正是哈希的主要用途，版本 bump 就改指纹
    会让回归对拍失效，版本信息由这两个字段自己承载，不需要哈希代持。③**派生冗余**——凡可由已纳入字段
    推出的值（`display_name` 由 `fault_mode` 过映射表得到）：纳入只添噪声。④**哈希字段自身**：不自指。

    **规范化（四步，逐字照此实现）**：(1) 按上面的清单把产物**裁成一棵树**（只留 `dict/list/str/int/float/bool/None`）；
    (2) `json.dumps(tree, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`；
    (3) UTF-8 编码后取 SHA-256；(4) 值写成 `sha256:<64 位小写 hex>`。
    三条不可省的细节：**(i) 数组顺序保留**——`hypotheses[]` 的 `rank` 序正是被锁定的对象，
    若连数组也排序，A-107 那个"算术全对、序错"的形状就从哈希里溜走了；
    **(ii) `null` 保留为 `null`、不得省略键**——省略键会让"这个字段没实现"与"这个字段值为 null"哈希相同，
    而那正是 C2 规则 2 花了一整轮才分开的两件事；**(iii) 不做任何二次取整**——哈希吃的是产物里已经
    `display()` 到 2 位的 `confidence`（`confidence.py:391-393` 是链上唯一取整出口），
    因此**本哈希区分不了 ±0.01 并列带内、两位显示相同的两种序**（A-116 ① 的同一带）；
    该带由 `engine._rank` 与 `c3validate._check_rank_monotonic` **两侧同步**实现；在那之前任何报告
    不得声称"排序已被哈希锁定"。**（已落码，A-121）** 带本身在 `confidence.rank_band_c`
    （队长锚定的 ±0.01 划分，两侧共用同一份），两侧的第二键统一读**产物里的两位显示值**——
    引擎不再用未取整的 `score.c` 排序，否则两侧会用两把尺子量同一条带，分歧照旧。

    **合法值与过渡期**：只允许三种形态——`""`（生产者尚未计算）、`sha256:<hex>`（已计算）、
    `"…"`（示例占位符）。落码批必须**同批**清零占位符并让校验器实算，否则规则 21 本身就是检查 23
    反对的那个形状（字段有、载体无）。**（已落码，A-121）**：5 处占位符（本文件两份内联示例 + `tests/fixtures/` 三份夹具）已同批清零为
    实算值，`engine.py` 的恒空串也改为实算（空串是合法形态但"未计算"，不是占位符，两者本条分列）；
    引擎在 `blocked_rules` 落进 `freq_limits` **之后**才计算（哈希核含 `freq_limits`，
    早一步算会把该项算成缺键）。

    **机器判定**：`C3-R21-core-hash-recompute`（按本条清单从产物重算并与字段比对）、
    `C3-R21-core-hash-format`（非空必须匹配 `sha256:<64 位小写 hex>`，`"…"` 判为未清零）、
    `C3-R21-core-hash-empty-is-gap`（空串记 **gap** 不记红）。三条各管一件事、不合并：若复算对
    空串直接判红，过渡期产物会被整片判红，而那不是本报告的错。
    **落地位置**：清单与四步规范化的唯一代码落点是 `src/axiscope/core_hash.py`，`engine` 与
    `c3validate` 都从它 import——规则 21 的"不得各自发明"是**结构性**约束的，不靠纪律靠 import。
    检测力按检查 22 要求两条负向例，缺任一条本条不算落了载体：
    (a) 交换两条 `hypotheses[]` 的 `rank`（数组顺序变化）而哈希不变 ⟹ 必须翻红；
    (b) 重写 `verdict.summary` 的措辞 ⟹ 哈希**不变**且不报警（证明排除侧真的在排除）。
    两条都钉在 `tests/test_c3validate.py`（`test_rule21_rank_swap_is_caught_by_the_recompute` /
    `test_rule21_narrative_rewrite_leaves_the_hash_alone`），生产者侧另钉
    `tests/test_engine.py::test_engine_report_hash_recomputes_and_the_halves_agree`。

    **清单落码时被迫定的两处口径（契约原文未点名，按"最小且可复算"取舍，写此备查）**：
    ①`not_evaluable` 的**原因键在仓内叫 `why`**（`rules_skipped` 那边才叫 `reason`），本条的
    "固定句式 `reason`"按"两处都认"实现；②`blocked_by` **不进核**——契约点名的是
    `fault_mode` 与原因键，而 `blocked_by` 对结论的唯一作用是喂 §2.2 的缺席扣减，
    `verdict.overall_confidence` 已在核内 ⟹ 换 `blocked_by` 若改变不了结论就不该改指纹。
    这两处若判错方向，判据是负向例 (a)(b) 与 `tests/test_c3validate.py::test_rule21_*` 里的其余各条。

    **为什么不走另一条路（把未取整的 C 塞进产物喂哈希）**：那要求产物承载链上值，违反 C2/C3 的"唯一取整出口"
    纪律（`display()` 的 docstring 明写"计算链上不得取整"是为了**算得准**，不是为了**印得全**）；
    而且它按 A-110 的尺子属于"新造一个数字"——新增一条对外可见的数值口径，对判定却零增量，
    因为真正的增量在 ±0.01 并列带那一侧，不在哈希这一侧。
