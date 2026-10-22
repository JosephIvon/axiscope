"""登记层：把"看不见 / 算不了 / 不许断因果"写成结构化事实，而不是写成"未发现"。

义务来自 KB4 §0 的 INV-1/INV-2/INV-5/INV-6/INV-7/INV-11/INV-16 与 KB3 的 R-25/R-30：
门与边只产登记义务，永不产假设（A-51）。`why` 一律取原文措辞，不得自造（KB4 §1.5 第 3 条）。
"""
from __future__ import annotations

from .anchors import assumption_row
from . import c3validate
from .features import BAND_FLOOR, BRANCH_FLOOR, WHY_NO_COUNTS, WHY_NO_DATUM

# KB4 §1.1 的 22 叶表（slug → 主锚点规则 / 采样率下限）。
# 频带下界一律取 features.BAND_FLOOR / BRANCH_FLOOR（KB3 §2.1 的唯一真值），此处不重复登记。
LEAVES: dict[str, dict] = {
    "mechanical_resonance": {"rules": ["R-03", "R-04"], "feature": "resonance.candidates"},
    "mechanical_double_inertia": {"rules": ["R-09"], "feature": "resonance.candidates"},
    "mechanical_backlash": {"rules": ["R-08"], "feature": "global.reversal_error_counts"},
    "mechanical_friction_stiction": {"rules": ["R-06"], "feature": "global.friction_stiction_ratio"},
    "mechanical_crawling": {"rules": ["R-05"], "feature": "crawling.low_speed_segments"},
    "mechanical_encoder_periodic_error": {"rules": ["R-07"], "feature": "encoder.per_rev_amplitude_counts"},
    "mechanical_loose_structure": {"rules": ["R-02"], "feature": "global.fe_p999_counts"},
    "mechanical_thermal_drift": {"rules": ["R-01"], "feature": "global.thermal_drift_counts_per_min"},
    "electrical_torque_ripple": {"rules": ["R-11"], "feature": "spectral.cur_q.dominant_freq_hz",
                                 "branch_features": {"R-11#switching_freq":
                                                     "spectral.cur_q.dominant_freq_hz"}},
    "electrical_current_loop_bandwidth": {"rules": ["R-12"],
                                          "feature": "spectral.fe.dominant_freq_hz"},
    "electrical_velocity_pi_detune": {"rules": ["R-13"], "feature": "bandwidth.phase_margin_deg"},
    "electrical_position_pi_detune": {"rules": ["R-14"],
                                      "feature": "step_response[0].limit_cycle_freq_hz"},
    "electrical_feedforward_mismatch": {"rules": ["R-15"], "min_fs_hz": 500.0,
                                        "feature": "ff_mismatch.asymmetry_ratio"},
    "electrical_motor_heating": {"rules": ["R-16"], "feature": "global.cur_q_rms_pct"},
    "electrical_resolution_quantization": {"rules": ["R-17"], "feature": "spectral.fe.tonality_index"},
    "software_induced_host_thread_jitter": {"rules": ["R-18"], "min_fs_hz": 1000.0,
                                            "feature": "event_context.fe_spike_aligned_to_host_pause"},
    "software_induced_interp_buffer_underrun": {"rules": ["R-19"], "min_fs_hz": 500.0,
                                                "feature": "event_context.interp_underrun_during_path"},
    "software_induced_bus_cycle_miss": {"rules": ["R-20"],
                                        "feature": "event_context.network_cycle_miss_count"},
    "software_induced_late_vision_result": {"rules": ["R-21"], "min_fs_hz": 500.0,
                                            "feature": "event_context.vision_result_latency_p95_ms"},
    "software_induced_pulse_eq_overwritten": {"rules": ["R-22"],
                                              "feature": "event_context.step_labels"},
    "software_induced_settle_window_too_short": {"rules": ["R-23"], "min_fs_hz": 200.0,
                                                 "feature": "step_response[0].settling_time_ms"},
    "software_induced_polling_latency": {"rules": ["R-24"], "min_fs_hz": 200.0,
                                         "feature": "event_context.n_by_source.motion"},
}

SOFTWARE_SLUGS = [s for s in LEAVES if s.startswith("software_induced_")]

FAMILY_OF = {}
for _slug in LEAVES:
    if _slug.startswith("software_induced_"):
        FAMILY_OF[_slug] = "software_induced_error"
    elif _slug.startswith("mechanical_"):
        FAMILY_OF[_slug] = "mechanical_error"
    else:
        FAMILY_OF[_slug] = "electrical_error"

# 门/边/仲裁/元规则：`family: null`，永不进 hypotheses（INV-16，A-51）。
GATE_RULES = frozenset({"R-10", "R-25", "R-26", "R-27", "R-28", "R-29", "R-30",
                        "R-37", "R-49", "R-50"})

WHY_BAND = "fs 不足，该频段无信息（不代表不存在）"
WHY_NO_EVENTS = "无事件上下文，无法区分机械尖峰与调度抖动"
WHY_CLOCK_UNVERIFIED = "时钟未对齐，因果不可断"
WHY_NO_TEMP = "缺 temp 通道，且无冷热机对比"
WHY_NO_COLD_HOT = "无冷/热机配对样本，单调升温趋势不可观测"
# A-97 / A-106 的固定句式（WHY_NO_COUNTS / WHY_NO_DATUM）由 features 单点定义、在文件头引入：
# C2 侧的 unavailable 与 C3 侧的 not_evaluable 必须逐字同文，本层不该有第二份副本。

SKIPPED_BAND = "band_gate: f_b < band_floor"
SKIPPED_TIME_RESOLUTION = "time_resolution"

# C3 规则 16：`blocked_by` 是锚在 C1/C2 通道与文件清单上的稳定键名，不许自由造。
# 契约只给过四个例子、没有闭集，所以本层用"注册即声明"的方式把闭集固定在代码里：
# 新增一个键必须同时改这张表，否则登记会被拒。
# 闭集本体在 c3validate（校验器），本层直接引用而非另抄一份：两处各抄一遍时
# 「校验器许可、登记层抛异常」这种反向矛盾不会被任何测试发现（A-122）。
_BLOCKED_BY = set(c3validate.ALLOWED_BLOCKED_BY)


class BlockedByKey(Exception):
    pass


def blocked_by_band(fs_hz: float) -> str:
    return "band_gate_fs_%dk" % int(round(fs_hz / 1000.0))


def event_gates(features: dict) -> dict:
    """KB4 §1.3 N6 的 G1…G5。逐叶粒度：族级判断不能代替叶级判断。"""
    ec = features.get("event_context") or {}
    sync = ec.get("sync") or {}
    tau_u = sync.get("uncertainty_ms")
    # 未核时的钟给出的 τ_u 与没给一样都是占位值，两者的假设都必须留痕（KB3 纪律 6）；
    # 但留痕不改算术——门禁用报告里的那个 τ_u，免得把一个实测 0.5 ms 当 5 ms 用。
    assumed_tau = tau_u is None or sync.get("verified") is not True
    if tau_u is None:
        tau_u = 5.0
    fs_hz = features["fs_hz"]
    residual = ec.get("alignment_residual_ms")
    return {
        "G1": ec.get("available") is True,
        "G2": ec.get("causal_claims_permitted") is True,
        "G3": residual is not None and residual <= tau_u,
        "G4": sync.get("verified") is True and sync.get("method") in ("trigger_edge", "ntp"),
        "G5": fs_hz >= 1000.0 and 1000.0 / fs_hz <= tau_u / 2.0,
        "tau_u_ms": tau_u,
        "tau_u_assumed": assumed_tau,
    }


class Ledger:
    """C3 `differential` / `audit` 中由登记层负责的那部分。"""

    def __init__(self) -> None:
        self.not_evaluable: list[dict] = []
        self.considered: list[str] = []
        self.rules_fired: list[str] = []
        self.rules_skipped: list[dict] = []
        self.assumptions: list[dict] = []
        self.notes: dict[str, str] = {}
        self._seen: set[tuple] = set()

    def assume(self, anchor: str, statement: str) -> None:
        """C1 §audit.assumptions 的形状（C3 规则 19）：稳定锚 + 散文，缺一不可。"""
        self.assumptions.append(assumption_row(anchor, statement))

    def register(self, row: dict) -> None:
        key = row.get("blocked_by")
        if key is not None and key not in _BLOCKED_BY and not key.startswith("band_gate_fs_"):
            raise BlockedByKey(f"blocked_by 键 {key!r} 未在本层声明（C3 规则 16：不许自由造）")
        ident = tuple(sorted((k, str(v)) for k, v in row.items() if k != "why"))
        if ident in self._seen:
            return
        self._seen.add(ident)
        self.not_evaluable.append(row)

    def fire(self, rule_id: str) -> None:
        if rule_id not in self.rules_fired:
            self.rules_fired.append(rule_id)

    def skip(self, rule_id: str, reason: str) -> None:
        if not any(s["rule_id"] == rule_id for s in self.rules_skipped):
            self.rules_skipped.append({"rule_id": rule_id, "reason": reason})

    def consider(self, slug: str, note: str | None = None) -> None:
        # 已经登记成「输入缺失、不可评估」的叶不再当成候选（E2 的共现观察是本层显式
        # consider-then-register，不受此守卫影响）。
        if any(r.get("fault_mode") == slug for r in self.not_evaluable):
            return
        if slug not in self.considered:
            self.considered.append(slug)
        if note:
            self.notes[slug] = note

    @property
    def distinct_blocked_by(self) -> list[str]:
        return sorted({r["blocked_by"] for r in self.not_evaluable if "blocked_by" in r})


def band_gate(features: dict, leaf: str) -> list[dict]:
    """INV-1：`f_b < band⊥` ⟹ 该叶只能产出 `blocked_rules` + `unavailable` + `not_evaluable`。

    粒度按 A-79 分两层：整条规则越带才把叶登记为不可评估；只有支路越带时叶仍然可评，
    仅按 `R-<nn>#<branch>` 登记（把整条 R-11 写进 blocked_rules 会谎报"纹波判据全不可用"）。
    恒运行的门（R-10 伪峰检测、R-25 频带门禁本身）永不进 `blocked_rules`（C2 规则 7）。
    """
    spec = LEAVES[leaf]
    f_b = features["freq_limits"]["reliable_band_hz"]
    fs_hz = features["fs_hz"]
    rules = [r for r in spec["rules"] if r not in GATE_RULES]
    whole = [r for r in rules if BAND_FLOOR.get(r) is not None and f_b < BAND_FLOOR[r]]
    branches = [b for b, floor in BRANCH_FLOOR.items()
                if b.split("#")[0] in rules and f_b < floor]
    rows: list[dict] = []
    if whole:
        rows.append({"kind": "blocked_rules", "rule_ids": whole, "feature": spec["feature"],
                     "reason": "f_b=%.0f Hz < 需要的 %.0f Hz"
                               % (f_b, max(BAND_FLOOR[r] for r in whole))})
        rows.append({"kind": "not_evaluable", "fault_mode": leaf,
                     "blocked_by": blocked_by_band(fs_hz), "why": WHY_BAND})
        rows.append({"kind": "rules_skipped", "rule_ids": whole, "reason": SKIPPED_BAND})
    for b in branches:
        rows.append({"kind": "blocked_rules", "rule_ids": [b],
                     "feature": spec["branch_features"][b],
                     "reason": "f_b=%.0f Hz < 支路需要的 %.0f Hz" % (f_b, BRANCH_FLOOR[b])})
        rows.append({"kind": "rules_skipped", "rule_ids": [b], "reason": SKIPPED_BAND})
    min_fs = spec.get("min_fs_hz")
    if min_fs is not None and fs_hz < min_fs:
        # INV-7 口径：采样率下限不成立是"该边剪枝 + rules_skipped"，不是新的缺席原因。
        # 契约没有为这类下限给过 `blocked_by` 键，自由造就违反 C3 规则 16。
        rows.append({"kind": "rules_skipped",
                     "reason": "fs_below_rule_floor: fs=%g Hz < %g Hz" % (fs_hz, min_fs)})
    return rows


def near_nyquist(features: dict) -> list[dict]:
    """INV-2：`f0 ≥ 0.8·f_N` 的候选必须先过 R-10 伪峰支，未经排除不得进机械族叶。

    这是**剪枝**不是缺席：缺的是"R-10 的排除结论"这个中间量，不是某路通道，
    所以落 `rules_skipped` + `considered`，不落 `not_evaluable`（那里只放缺失输入的键）。
    """
    f_n = features["freq_limits"]["nyquist_hz"]
    rows = []
    for cand in features.get("resonance", {}).get("candidates", []):
        f0 = cand.get("freq_hz")
        if f0 is not None and f0 >= 0.8 * f_n:
            rows.append({"kind": "rules_skipped", "rule_ids": ["R-03", "R-04"],
                         "reason": "near_nyquist: f0=%.0f Hz >= 0.8*f_N，须先过 R-10" % f0})
            rows.append({"kind": "consider", "slug": "mechanical_resonance",
                         "note": "候选频点在奈奎斯特近区，未经 R-10 排除前只作观察"})
    return rows


def software_family(features: dict, ledger: Ledger) -> str:
    """KB4 §1.5 的进入/退出：E1/E2/E3 三分支穷尽，不存在"悬而未判"。返回走过的分支。"""
    gates = event_gates(features)
    ledger.fire("R-30")
    if gates["tau_u_assumed"]:
        ledger.assume("event_context.sync.uncertainty_ms",
                      "未给出可核时时钟不确定度（缺失，或 verified=false 时报告值仍是占位）"
                      "⟹ 按 5 ms 计（KB3 纪律 6）")
    if not gates["G1"]:
        for slug in SOFTWARE_SLUGS:
            ledger.register({"fault_mode": slug, "blocked_by": "absent_events_jsonl",
                             "why": WHY_NO_EVENTS})
            ledger.skip(slug_rule(slug), "dependency_null:event_context")
        ledger.register({"family": "software_induced_error", "blocked_by": "absent_events_jsonl",
                         "why": WHY_NO_EVENTS})
        ledger.skip("R-28", "dependency_null:event_context")
        if not (features.get("event_context") or {}).get("step_labels"):
            ledger.skip("R-29", "dependency_null:event_context.step_labels")
        return "E1"
    if not gates["G2"] or not gates["G4"]:
        for slug in SOFTWARE_SLUGS:
            ledger.consider(slug, "时钟未对齐，共现不等于因果")
            ledger.register({"fault_mode": slug, "blocked_by": "sync_unverified",
                             "why": WHY_CLOCK_UNVERIFIED})
        ledger.register({"family": "software_induced_error", "blocked_by": "sync_unverified",
                         "why": WHY_CLOCK_UNVERIFIED})
        return "E2"
    if not gates["G5"]:
        ledger.skip("R-18", "%s: 1/fs=%.3g ms > τ_u/2=%.3g ms"
                    % (SKIPPED_TIME_RESOLUTION, 1000.0 / features["fs_hz"],
                       gates["tau_u_ms"] / 2.0))
        return "E3"
    return "in"


def slug_rule(slug: str) -> str:
    return LEAVES[slug]["rules"][0]


def thermal_family(features: dict, ledger: Ledger) -> None:
    """缺 temp 与冷/热机配对时，R-01/R-16 只能是 not_evaluable，禁写"无热漂移"（INV-15）。"""
    if "temp" in (features.get("present_channels") or []):
        return
    ledger.register({"fault_mode": "mechanical_thermal_drift",
                     "blocked_by": "absent_temp_channel", "why": WHY_NO_TEMP})
    ledger.skip("R-01", "dependency_null:global.thermal_fe_correlation_r")
    ledger.register({"fault_mode": "electrical_motor_heating",
                     "blocked_by": "absent_temp_channel", "why": WHY_NO_COLD_HOT})
    ledger.skip("R-16", "dependency_null:global.cur_q_rms_pct")
