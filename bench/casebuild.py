"""C5 评测案例的构建内核（bench/cases.jsonl 的生产者）。

纪律（KB8 §4 污染红线 + A-88 同源无证明力）：

* 真值只有一种来源——**本文件里写死的注入数学**（`INJECTIONS`）。真值不写进样本包，
  只写进 `cases.jsonl`（KB8 §1.1「评测元数据是旁挂的」）。
* 注入在**物理量层**（TwinCAT 原始列）落下，随后仍走生产链路
  `c1.build_meta → c1.write_pack → features.compute → engine.analyze → c3validate.validate`，
  中间没有任何一步读 `cases.jsonl`（KB8 §4 红线 3）。
* 注入真值与检出规则同源（本项目的注入器 + 本项目的规则）⟹ 只能证明「判据能检出按我们
  设计植入的误差」，**不能**证明诊断准确。这是 A-88，本文件不淡化这一点。

样本包来源：DaRUS `data/raw/Export10_244531.csv`（DARUS-3600，CC BY 4.0，
Reichenbach, Thomas — University of Stuttgart；见 `data/raw/Export10_244531.csv.source.txt`）。
本仓库当前只有这一份可被 `axiscope.twincat.read_scope` + `mapping` 吃下的真实记录。
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO, "src") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "src"))

from axiscope import c1, features, twincat  # noqa: E402

SOURCE_CSV = os.path.join(REPO, "data", "raw", "Export10_244531.csv")
SAMPLES_DIR = os.path.join(REPO, "bench", "samples")

#: KB8 §1.1 `origin`：只填 KB7 已登记的可核实标识（A-67 禁止编造 DOI）。
ORIGIN_DARUS3600 = {
    "source_tier": "T1-a",
    "repo": "DaRUS",
    "id": "doi:10.18419/DARUS-3600",
}


# --------------------------------------------------------------------------- 注入数学
# 每个注入函数就地给出 KB5 §3.0 的九项（落点 / 数学形式 / 量级 / 生效段 / 事件流 /
# 预期 C2 变化 / cause slug / 可检测性 / truth 字段），并在这里如实记 `declared_detectable`。

def _t_of(table) -> list[float]:
    """TwinCAT 导出的首列是样本索引，物理时间 = index × SampleTime[ms]。"""
    st = table.sample_time_ms
    return [v * st / 1000.0 for v in table.sample_index]


def _alias_hz(f_hz: float, fs: float) -> float:
    """把 f 折回 [0, fs/2]：先取模到 [0, fs)，再对超过奈奎斯特的部分做折叠。"""
    r = f_hz % fs
    return r if r <= fs / 2.0 else fs - r


def inj_inj01_khz_resonance(table, t, win) -> dict:
    """INJ-01：kHz 级机械谐振（在这份 fs=1 kHz 记录上**不可检测**，混叠成 300 Hz 伪峰）。

    落点   : dVelocity_test（vel_fb，m/s），只在触发门控窗口内注入（样本包只落门控后的 5000 行）
    形式   : v[n] += A·exp(-(t-t0)/τ)·sin(2π·f_k·t[n])
    量级   : A = 0.02 m/s（基线 |v| 峰值 ~2 m/s 的 1%），τ = 50 ms，t0 取窗口内
    生效段 : move（门控后的唯一段）
    事件流 : 否
    slug   : mechanical_resonance
    可检测 : declared_detectable = **false** —— f_k = 3700 Hz > f_N = 500 Hz，
             R-03/R-04 的 band⊥ = 2000 Hz（C2 规则 7）。3700 Hz 在 fs=1000 Hz 上
             折回 300 Hz 的**混叠伪峰**，正是 A-65「看不见」的真实形态。
    """
    a, tau, fk = 0.02, 0.05, 3700.0
    lo, hi = win
    t0 = t[lo + (hi - lo) // 2]
    col = table.data["dVelocity_test"]
    for i in range(lo, hi + 1):
        ti = t[i]
        if ti < t0:
            continue          # 突发起点之前不注入（否则 e^(-(t-t0)/τ) 会向外指数发散）
        col[i] += a * math.exp(-(ti - t0) / tau) * math.sin(2.0 * math.pi * fk * ti)
    return {
        "kb5_inj": "INJ-01",
        "kb0_slug": "mechanical_resonance",
        "declared_detectable": False,
        "invisible_because": "f_k=3700 Hz > f_N=500 Hz；R-03/R-04 band⊥=2000 Hz（C2 规则 7 / A-65）",
        "magnitude": {"A_m_s": a, "tau_s": tau, "f_k_hz": fk, "t0_s": t0,
                      "alias_freq_hz": _alias_hz(fk, 1000.0)},
    }


def inj_inj11_torque_ripple(table, t, win) -> dict:
    """INJ-11：三相 6k±1 电磁转矩纹动（本样本**无 cur_q**，不可检测）。

    落点   : dTorque_test（torque，N·m），只在触发门控窗口内注入
    形式   : τ[n] += A·(sin(2π·5·f_e·t) + 0.6·sin(2π·7·f_e·t))   （KB5 §3.2 的 n=5,7 结构）
    量级   : A = 0.08 × rms(窗口内 τ)，f_e = 10 Hz
    生效段 : move（门控后唯一段；KB5 原文是 dwell/probing，本样本没有那两种段）
    事件流 : 否
    slug   : electrical_torque_ripple
    可检测 : declared_detectable = **false** —— R-11 读 `spectral.cur_q.*`，
             本样本 canonical 通道只有 vel_cmd/vel_fb/torque，无 cur_q。
    注     : 6k±1 的 k 需「每转槽数 × 极对数」，而本样本 `axis.motor_rev_counts = null`
             ⟹ k 不可从数据复算。故按**可复算的代理载频** f_e = 10 Hz 注入，
             载频是代理值这一点写进 cases.jsonl 的 `injection_note`，不冒充实测 k。
    """
    lo, hi = win
    col = table.data["dTorque_test"]
    seg = col[lo:hi + 1]
    mean = sum(seg) / len(seg)
    rms = math.sqrt(sum((v - mean) ** 2 for v in seg) / len(seg))
    a = 0.08 * rms
    fe = 10.0
    for i in range(lo, hi + 1):
        ti = t[i]
        col[i] += a * (math.sin(2.0 * math.pi * 5.0 * fe * ti)
                       + 0.6 * math.sin(2.0 * math.pi * 7.0 * fe * ti))
    return {
        "kb5_inj": "INJ-11",
        "kb0_slug": "electrical_torque_ripple",
        "declared_detectable": False,
        "invisible_because": "R-11 的判据路径是 spectral.cur_q.*，本样本无 cur_q 通道",
        "magnitude": {"A_n_m": a, "f_e_hz_proxy": fe, "orders": [5, 7],
                      "tau_rms_baseline_n_m": rms},
        "injection_note": "6k±1 的 k 不可从本样本复算（axis.motor_rev_counts=null），"
                          "载频 f_e=10 Hz 是代理值，非实测 k",
    }


def inj_inj04_stiction(table, t, win) -> dict:
    """INJ-04：库仑+静摩擦粘滑（本样本**无 fe**，不可检测）。

    落点   : dVelocity_test_tar（vel_cmd）与 dVelocity_test（vel_fb），两侧同步加粘滑残差
    形式   : v[n] += A·(1 − 2·sawtooth(frac((|v[n]| − v_s)·τ_c/(A·v_s))))，sawtooth(u)=u−⌊u⌋∈[0,1)
    量级   : A = 0.005 m/s，v_s = 0.01 m/s（Stribeck 速度），τ_c = 50 µs
    生效段 : move（门控后唯一段；KB5 原文要 probing/dwell 起动段，本样本没有）
    事件流 : 否
    slug   : mechanical_friction_stiction
    可检测 : declared_detectable = **false** —— `global.friction_stiction_ratio` / `crawling.*`
             的分母要 fe（= pos_cmd − pos_fb），本样本两路位置通道皆无（C1 派生规则 1 无法起算）。
    """
    a, vs, tau_c = 0.005, 0.01, 0.00005
    lo, hi = win
    for name in ("dVelocity_test_tar", "dVelocity_test"):
        col = table.data[name]
        for i in range(lo, hi + 1):
            v = col[i]
            u = (abs(v) - vs) * tau_c / (a * vs)
            col[i] = v + a * (1.0 - 2.0 * (u - math.floor(u)))
    return {
        "kb5_inj": "INJ-04",
        "kb0_slug": "mechanical_friction_stiction",
        "declared_detectable": False,
        "invisible_because": "friction_stiction_ratio / crawling.* 的分母要 fe；"
                             "本样本无 pos_cmd/pos_fb，C1 派生规则 1 起不出 fe",
        "magnitude": {"A_m_s": a, "v_s_m_s": vs, "tau_c_s": tau_c,
                      "tau_s_over_tau_c": 1.5},
    }


NO_INJECTION = None


#: 事件流注入（纯事件，不动波形）。C6 §1 的 `source` / `level` 词表。
def _event_rows_for_inj19() -> list[dict]:
    """INJ-19：换型时脉冲当量被覆盖（r = 10）。r>1 ⟹ recipe_new = 10×recipe_old。"""
    return [
        {"t": 1.200000, "level": "info", "source": "process", "code": "step_started",
         "axis": None, "detail": {"step": "rewind_fast", "recipe_old": "WF125_R1",
                                  "recipe_new": "WF125_R10"}},
        {"t": 1.200500, "level": "warn", "source": "mes", "code": "scale_changed",
         "axis": None, "detail": {"r": 10, "recipe_old": "WF125_R1", "recipe_new": "WF125_R10",
                                  "counts_per_mm_old": 5.8349, "counts_per_mm_new": 58.349}},
    ]


def _event_rows_for_inj15() -> list[dict]:
    """INJ-15：上位机线程阻塞（source=host, code=thread_stall, level=warn）。"""
    return [
        {"t": 2.000000, "level": "info", "source": "motion", "code": "move_started",
         "axis": None, "detail": {"target": -0.5}},
        {"t": 2.041200, "level": "warn", "source": "host", "code": "thread_stall",
         "axis": None, "detail": {"stall_ms": 41.2}},
        {"t": 2.082400, "level": "info", "source": "motion", "code": "move_done",
         "axis": None, "detail": {"settled": False}},
    ]


# --------------------------------------------------------------------------- 案例表
# case_id 命名规范 = KB8 §1.2：<tier>-<origin>-<INJ 或 control>-<4 位序号>

CASES: list[dict] = [
    {
        "case_id": "T1a-DARUS-CTL-0001",
        "split": "dev",
        "inject": NO_INJECTION,
        "events": None,
        "injected_fault": None,
        # DaRUS 试验台受试对象健康（C5 §1：「故障归因（受试对象健康，非故障数据）」）。
        # 这是本仓唯一**非同源**的真值：不是我们注入的，是数据集本身的属性。
        "expected_verdict_class": "none_of_the_above",
        "gold_note": "受试对象健康、无任何注入（样本量减半投影：门控窗口前 2500 行）；"
                     "正确输出是拒绝下结论",
        "expected_not_evaluable_min": 2,
        "forbidden_conclusions": ["kHz_absent", "no_anomaly_claim", "field_effective",
                                  "thermal_drift", "sub_quantum_mm_claim"],
        "counterfactual_variants": [],
        "project_rows": 2500,
        # KB8 §1.5「该案例**具体**不可评估的原因必须出现在 not_evaluable 里」的可执行化：
        # 这里列的是**样本事实**推出的义务键名，runner 再去比对 C3 实际登记的 blocked_by。
        "expected_blocked_by": ["band_gate_fs_1k", "absent_events_jsonl", "absent_temp_channel"],
        # 本样本没有 cur_q / fe，而 registration._BLOCKED_BY 里**没有**这两个缺席键
        # （C3 规则 16 禁止自由造键 ⟹ 引擎无法登记「缺 cur_q」「缺 fe」）。
        # 这两条是登记层的能力缺口，不是本案例的判据义务，单独列以免混进命中率。
        "unimplementable_blocked_by": ["absent_cur_q_channel", "absent_fe_channel"],
    },
    {
        "case_id": "T1a-DARUS-INJ01-0001",
        "split": "hidden",
        "inject": inj_inj01_khz_resonance,
        "events": None,
        "injected_fault": {"kb5_inj": "INJ-01", "kb0_slug": "mechanical_resonance"},
        "expected_verdict_class": "refuse_insufficient_data",
        "gold_note": "注入了 kHz 谐振，但 fs=1 kHz ⟹ R-03/R-04 进 blocked_rules；"
                     "正确输出是拒答 + blocked_rules，不是「未发现谐振」，也不是「检出谐振」",
        "expected_not_evaluable_min": 1,
        "forbidden_conclusions": ["kHz_absent", "no_anomaly_claim", "field_effective",
                                  "thermal_drift", "sub_quantum_mm_claim"],
        "counterfactual_variants": [
            {"fs_hz": "1000 → 8000", "期望结论翻转": "mechanical_resonance",
             "出处": "KB8 §2.1 mechanical_resonance 行：kHz 档只在 fs≥5000 可观测"},
        ],
        "expected_blocked_by": ["band_gate_fs_1k", "absent_events_jsonl", "absent_temp_channel"],
        "unimplementable_blocked_by": [],
    },
    {
        "case_id": "T1a-DARUS-INJ04-0001",
        "split": "dev",
        "inject": inj_inj04_stiction,
        "events": None,
        "injected_fault": {"kb5_inj": "INJ-04", "kb0_slug": "mechanical_friction_stiction"},
        "expected_verdict_class": "refuse_insufficient_data",
        "gold_note": "注入了粘滑，但 fe 的两路原料（pos_cmd/pos_fb）皆无；"
                     "正确输出是拒答并登记不可评估原因",
        "expected_not_evaluable_min": 1,
        "forbidden_conclusions": ["no_anomaly_claim", "field_effective", "thermal_drift",
                                  "sub_quantum_mm_claim"],
        "counterfactual_variants": [
            {"present_channels": "补 pos_cmd + pos_fb（派生 fe）",
             "期望结论翻转": "mechanical_friction_stiction",
             "出处": "KB8 §2.1 mechanical_friction_stiction 行：通道需求 fe+vel_cmd"},
        ],
        "expected_blocked_by": ["absent_events_jsonl", "absent_temp_channel"],
        # 本案例的核心不可评估原因就是「缺 fe」，但 registration._BLOCKED_BY 无对应键
        # ⟹ C3 不可能登记它。这条能力缺口由「拒答正确率」承压，不由命中率承压。
        "unimplementable_blocked_by": ["absent_fe_channel"],
    },
    {
        "case_id": "T1a-DARUS-INJ11-0001",
        "split": "hidden",
        "inject": inj_inj11_torque_ripple,
        "events": None,
        "injected_fault": {"kb5_inj": "INJ-11", "kb0_slug": "electrical_torque_ripple"},
        "expected_verdict_class": "refuse_insufficient_data",
        "gold_note": "注入了 6k±1 型转矩纹动，但 R-11 读 spectral.cur_q 而本样本只有 torque；"
                     "正确输出是拒答 + 登记缺 cur_q 导致的不可评估",
        "expected_not_evaluable_min": 1,
        "forbidden_conclusions": ["no_anomaly_claim", "field_effective", "thermal_drift",
                                  "sub_quantum_mm_claim"],
        "counterfactual_variants": [
            {"present_channels": "补 cur_q 通道", "期望结论翻转": "electrical_torque_ripple",
             "出处": "KB8 §2.1 electrical_torque_ripple 行：通道需求 cur_q"},
        ],
        "expected_blocked_by": ["absent_events_jsonl", "absent_temp_channel"],
        # 同上：本案例的核心原因「缺 cur_q」在 registration._BLOCKED_BY 里**没有键**
        # （R-11 只产 blocked_rules 分支行，按 A-79 不落整叶 not_evaluable）。
        "unimplementable_blocked_by": ["absent_cur_q_channel"],
    },
    {
        "case_id": "T1a-DARUS-INJ19-0001",
        "split": "dev",
        "inject": NO_INJECTION,
        "events": _event_rows_for_inj19(),
        "injected_fault": {"kb5_inj": "INJ-19", "kb0_slug": "software_induced_pulse_eq_overwritten"},
        "expected_verdict_class": "co_occurrence_only",
        "gold_note": "只注入了事件流（脉冲当量被覆盖），波形未改；本样本 counts_per_mm=null，"
                     "换算链无载体，且事件时钟未经外部核对 ⟹ 只能共现、不得归因",
        "expected_not_evaluable_min": 1,
        "forbidden_conclusions": ["no_anomaly_claim", "field_effective", "thermal_drift",
                                  "sub_quantum_mm_claim"],
        "counterfactual_variants": [
            {"sync.verified": "false → true（trigger_edge, τ_u=1.0 ms）",
             "期望结论翻转": "software_induced_pulse_eq_overwritten",
             "出处": "KB5 §3.3 / C2 规则 8：G1..G5 全过才允许因果归因"},
        ],
        # events.jsonl 确实在包里 ⟹ 义务键是 sync_unverified（KB4 §1.5 分支 E2），
        # **不是** absent_events_jsonl。若引擎给出后者，拒答就是「理由错误」而非做对。
        "expected_blocked_by": ["sync_unverified", "band_gate_fs_1k", "absent_temp_channel"],
        "unimplementable_blocked_by": [],
    },
    {
        "case_id": "T1a-DARUS-INJ15-0001",
        "split": "dev",
        "inject": NO_INJECTION,
        "events": _event_rows_for_inj15(),
        "injected_fault": {"kb5_inj": "INJ-15", "kb0_slug": "software_induced_host_thread_jitter"},
        "expected_verdict_class": "co_occurrence_only",
        "gold_note": "只注入了上位机线程停顿事件流，波形未改；无 fe 无位置通道，"
                     "且事件时钟未对齐 ⟹ 只能共现、不得归因",
        "expected_not_evaluable_min": 1,
        "forbidden_conclusions": ["no_anomaly_claim", "field_effective", "thermal_drift",
                                  "sub_quantum_mm_claim"],
        "counterfactual_variants": [
            {"sync.verified": "false → true（trigger_edge, τ_u=1.0 ms）",
             "期望结论翻转": "software_induced_host_thread_jitter",
             "出处": "KB5 §3.3 / C2 规则 8"},
        ],
        "expected_blocked_by": ["sync_unverified", "band_gate_fs_1k", "absent_temp_channel"],
        "unimplementable_blocked_by": [],
    },
    {
        # A-61 孪生的 no_events 态：波形与 INJ19-0001 **逐字节相同**，只去掉 events.jsonl。
        "case_id": "T1a-DARUS-CTL-0002",
        "split": "hidden",
        "inject": NO_INJECTION,
        "events": None,
        "injected_fault": {"kb5_inj": "INJ-19", "kb0_slug": "software_induced_pulse_eq_overwritten"},
        "expected_verdict_class": "refuse_insufficient_data",
        "gold_note": "INJ19-0001 的无事件孪生（A-61）：波形逐字节相同，只少 events.jsonl；"
                     "无事件流 ⟹ 软件族必须整族登记 not_evaluable 且不得归因",
        "expected_not_evaluable_min": 1,
        "forbidden_conclusions": ["no_anomaly_claim", "field_effective", "thermal_drift",
                                  "sub_quantum_mm_claim"],
        "counterfactual_variants": [],
        "twin_of": "T1a-DARUS-INJ19-0001",
        "expected_blocked_by": ["absent_events_jsonl", "band_gate_fs_1k", "absent_temp_channel"],
        "unimplementable_blocked_by": [],
    },
]


# --------------------------------------------------------------------------- 构建

def _project_rows(table, lo: int, n: int) -> None:
    """把表裁到门控窗口的前 n 行（投影变体；A-62「只改元数据/数据」的样本量版）。

    裁完后 `bTrigger_Record` 全置 1，使 `c1.build_meta` 的门控恰好取到这 n 行。
    """
    hi = lo + n - 1
    for name in list(table.data):
        table.data[name] = table.data[name][lo:hi + 1]
    table.data["bTrigger_Record"] = [1.0] * n
    table.sample_index = [float(i) for i in range(n)]
    table.n_rows_raw = n


def _meta_variant(meta: dict, case: dict) -> dict:
    """按案例做**只改元数据**的投影（KB8 §2.2 的 A-62 `unknown_config` 一类做法）。
    本轮没有任何案例需要改元数据；留这个钩子是为了让「只改元数据、数据与哈希不变」
    这条纪律在代码里有明确落点，而不是靠注释承诺。"""
    return meta


def gate_window(table) -> tuple[int, int]:
    """触发门控窗口（行号，含端）。样本包只落这段，注入也只落这段。"""
    episodes = twincat.gate_episodes(table.data["bTrigger_Record"])
    if len(episodes) != 1:
        raise SystemExit("期望恰好 1 段触发门控窗口，实得 %d 段" % len(episodes))
    return episodes[0]


def materialize(case: dict, outdir: str) -> dict:
    """跑完整生产链路，返回 (meta, ingest, features)。样本包只落 meta/waveform/events。"""
    table = twincat.read_scope(SOURCE_CSV)
    t = _t_of(table)
    win = gate_window(table)
    if case.get("project_rows"):
        lo, n = win[0], int(case["project_rows"])
        _project_rows(table, lo, n)
        win = (0, n - 1)
        t = _t_of(table)
    truth = case["inject"](table, t, win) if case["inject"] else None

    meta, ingest = c1.build_meta(table, sample_id=case["case_id"])
    meta = _meta_variant(meta, case)
    meta.setdefault("source", {})
    # 案例身份锚在输入字节上（KB8 §1.4 / A-60）：source.tier 必须是本案例的层。
    meta["source"]["tier"] = case["source_tier"]
    pack = c1.write_pack(meta, ingest, outdir)
    ingest["sample_id"] = case["case_id"]
    ingest["sha256"] = pack["sha256"]

    ev_path = os.path.join(outdir, "events.jsonl")
    if case["events"]:
        with open(ev_path, "w", encoding="utf-8", newline="\n") as fh:
            for row in case["events"]:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    elif os.path.exists(ev_path):
        os.remove(ev_path)

    feats = features.compute(meta, ingest, outdir)
    return {"meta": meta, "ingest": ingest, "features": feats, "truth": truth, "pack": pack}


def freeze_digest(pack_dir: str) -> str:
    """KB8 §1.4：SHA256( bytes(meta.json) || 0x00 || bytes(waveform.tsv) || 0x00 || bytes(events.jsonl 或空) )。"""
    h = hashlib.sha256()
    for name in ("meta.json", "waveform.tsv", "events.jsonl"):
        path = os.path.join(pack_dir, name)
        blob = b""
        if os.path.exists(path):
            with open(path, "rb") as fh:
                blob = fh.read()
        h.update(blob)
        h.update(b"\x00")
    return h.hexdigest()


def features_digest(features: dict) -> str:
    """KB5 §5.4 `self_check.features_sha256` 的口径（C2 特征输出字节），附加字段、非案例身份。"""
    body = json.dumps(features, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def case_row(case: dict, meta: dict, feats: dict, truth: dict | None) -> dict:
    """按 KB8 §1.1 的字段表逐字产出案例目录行（字段名以 KB0 §4 / C1 / C2 为准）。"""
    ec = feats.get("event_context") or {}
    row = {
        "case_id": case["case_id"],
        "source_tier": case["source_tier"],
        "origin": copy.deepcopy(case["origin"]),
        "sha256": freeze_digest(os.path.join(SAMPLES_DIR, case["case_id"])),
        "features_sha256": features_digest(feats),
        "split": case["split"],
        "fs_hz": meta["sample_rate_hz"],
        "reliable_band_hz": feats["freq_limits"]["reliable_band_hz"],
        "present_channels": list(meta["present_channels"]),
        "sensor_config": meta.get("sensor_config"),
        "counts_per_mm": meta.get("counts_per_mm"),
        "events_present": bool(case["events"]),
        "sync_verified": (ec.get("sync") or {}).get("verified"),
        "segments_kinds": sorted({s["kind"] for s in meta.get("segments", [])}),
        "injected_fault": copy.deepcopy(case["injected_fault"]),
        "expected_verdict_class": case["expected_verdict_class"],
        "expected_not_evaluable_min": case["expected_not_evaluable_min"],
        "gold_params_ref": None,
        "forbidden_conclusions": list(case["forbidden_conclusions"]),
        "counterfactual_variants": copy.deepcopy(case["counterfactual_variants"]),
        "human_baseline_labels": {"status": "pending"},
        # —— 以下为旁挂说明位，不属 KB8 §1.1 的权威字段，只保证真值可复算 ——
        "gold_note": case["gold_note"],
        "expected_blocked_by": list(case["expected_blocked_by"]),
        "unimplementable_blocked_by": list(case["unimplementable_blocked_by"]),
    }
    if truth:
        row["injection_truth"] = truth
    if case.get("twin_of"):
        row["twin_of"] = case["twin_of"]
    return row


def assign_source_tier_and_origin() -> None:
    for c in CASES:
        c["source_tier"] = "T1-a"
        c["origin"] = copy.deepcopy(ORIGIN_DARUS3600)