"""DARUS-3600（DaRUS 3600，绳索/缆索执行器试验台）列 → C1 通道映射。

映射表逐条标注授权来源：族卡 KB2 §4.1 给「这类导出长什么样」，
样本卡 KB2 §4.10 给「我们手上这一份能撑什么」——冲突时以样本卡实测为准（KB2 §4.10 首段）。
拒映的列也必须逐条登记理由，KB2 §3.6 要求 N_mapped + N_extra == N_header。
"""
from __future__ import annotations

from dataclasses import dataclass, field

SI = "m/s"


@dataclass(frozen=True)
class Mapped:
    canonical: str
    raw_column: str
    unit: str
    sign: int = 1
    offset: float = 0.0
    inferred: bool = False
    confidence: float = 0.5
    basis: str = ""
    note: str = ""
    unit_unresolved: bool = False


@dataclass(frozen=True)
class Extra:
    name: str
    raw_column: str
    unit: str
    basis: str
    note: str = ""
    unit_unresolved: bool = False


MAPPED: tuple[Mapped, ...] = (
    Mapped(
        canonical="vel_cmd",
        raw_column="dVelocity_test_tar",
        unit=SI,
        confidence=0.6,
        basis="KB2 §4.1 映射表（`_tar` → vel_cmd）+ §4.10 实测 17,442/18,651 行有差、峰值 0.1270 m/s",
        note="`_tar` 后缀本身不构成指令轨证据；本映射的授权是实测两列确有差，"
             "且 §4.10 判「速度目标 ≠ 速度实际」⟹ vel_err 类判据可用",
    ),
    Mapped(
        canonical="vel_fb",
        raw_column="dVelocity_test",
        unit=SI,
        confidence=0.6,
        basis="KB2 §4.1 映射表（直映，本身带符号，不乘 dir）+ §4.10「本样本可撑 vel_err 类判据」",
        note="bMovingForward 全程恒 0 ⟹ 作者脚本的 dir=-1 规则无法用作符号来源（KB3 纪律 9），"
             "按 §4.1 不乘 dir、sign=+1 直映",
    ),
    Mapped(
        canonical="torque",
        raw_column="dTorque_test",
        unit="N_m",
        confidence=0.5,
        basis="KB2 §七-3（C1 torque.unit ∈ {percent_of_rated, N_m} 已于 A-4 落契约）",
        note="绝对刻度未定：作者脚本 catanalyze.m 第 100-102 行另有 ×10 修正（KB2 §七-3 转述），"
             "本地无该脚本可核 ⟹ 按 ×1 原样入包",
        unit_unresolved=True,
    ),
)


def _extras() -> dict[str, Extra]:
    pos = "位置/绳长残差（m），非 counts（KB2 §3.5 units_are=si_native）"
    vel = "速度（m/s）"
    force = "力（N）"
    power = "功率（W）"
    tor = "转矩（N·m，绝对刻度未定，见 torque 通道 note）"
    notes: dict[str, tuple[str, str, bool]] = {
        "dPosition_test": (pos, "三套位置测量之一；§4.10 判三源互不一致 ⟹ 不择一当 pos_fb", False),
        "dPosition_test_tar": (pos, "§4.1 族卡可映 pos_cmd，但 §4.10 实测它与 dPosition_test 逐行全等"
                                    "（0/18,651 行有差）⟹ 样本卡优先，拒映 pos_cmd，否则会凭空造出 fe ≡ 0 的指令轨", False),
        "dPosition_load": (pos, "与 dPosition_load_tar 逐行全等（0/18,651）⟹ 同样不是独立反馈", False),
        "dPosition_load_tar": (pos, "与 dPosition_load 逐行全等 ⟹ 拒映 pos_cmd", False),
        "dPosition_asco": (pos, "光学 ASCO 测量；与 dPosition_asco_enc 峰值差 180.15 ⟹ 交叉验证输入", False),
        "dPosition_asco_enc": (pos, "光学 ASCO 编码器测量；与 dPosition_asco 峰值差 180.15", False),
        "dPosition_lsv_enc": (pos, "电感 LSV 测量；三源之一", False),
        "dPosition_diff": (pos, "C1 派生规则 2 点名的「假朋友」：全 18,651 行实测 ≡ −(dPosition_test + "
                                 "dPosition_load)（行级最大残差 3.55e-15，corr 1.000000）⟹ 它是 PLC 现场"
                                 "计算列而非独立测量；本样本 fe 又恒零，规则 2 的 corr 自检分母退化，"
                                 "拒当 fe 的依据是恒等式本身而非相关性。按原名入 extra（绳长守恒残差，"
                                 "全程 0.1275…0.1354 m，即两绳总长仅守到 7.88 mm）", False),
        "dVelocity_load": (vel, "与 dVelocity_test 符号相反（缆索两端反向）；全程恒 +2 m/s 而 dVelocity_test 为 −2 m/s", False),
        "dVelocity_load_tar": (vel, "load 侧目标；与 dVelocity_test_tar 几乎无关（corr −0.009）", False),
        "dVelocity_asco": (vel, "ASCO 侧速度测量", False),
        "dVelocity_asco_enc": (vel, "ASCO 编码器速度测量", False),
        "dVelocity_lsv_enc": (vel, "LSV 编码器速度测量", False),
        "dVelocity_diff": (vel, "与 dPosition_diff 同族：全 18,651 行实测 ≡ −(dVelocity_test + "
                                "dVelocity_load)（行级最大残差 4.44e-16）⟹ PLC 计算列，非独立测量", False),
        "dRate_asco": (vel, "速率（ASCO 侧，单位存疑）", False),
        "dForce_load": (force, "负载侧力；与 dForce_tar 全行有差（峰值 97.5）⟹ 力控工况", False),
        "dForce_test": (force, "试验侧力", False),
        "dForce_tar": (force, "力目标；本样本恒值 125 ⟹ 恒值列", False),
        "dForce_diff": (force, "力差残差通道", False),
        "dForce_colinear": (force, "同向力分量", False),
        "dForce_orthogonal": (force, "正交力分量", False),
        "dForceSensorNo": (force, "恒值 8 ⟹ 力传感器编号，非物理量", False),
        "dTorque_load": (tor, "§4.1 把 dTorque_* 两列同映 torque，C1 只有一个 torque ⟹ 取 test 侧，"
                               "load 侧保留在 extra", True),
        "dPower_load": (power, "负载侧功率", False),
        "dPower_test": (power, "试验侧功率", False),
        "bMovingForward": ("0/1", "厂商布尔列 ⟹ 解析器内部输入，不入 waveform.tsv（C1 通道词表注 / KB2 §七-4）", False),
        "bTrigger_Record": ("0/1", "触发门控内部输入（KB3 纪律 8）⟹ 不入 waveform.tsv", False),
        "bTrigger_Export": ("0/1", "导出门控内部输入；本样本仅 2.7% 为真 ⟹ 门控用 bTrigger_Record", False),
        "bTrigger_Scope": ("0/1", "示波器使能；本样本恒 1 ⟹ 无截断", False),
    }
    return {raw: Extra(name=raw, raw_column=raw, unit=unit, basis="KB2 §3.6 不丢弃不猜语义",
                       note=note, unit_unresolved=unres)
            for raw, (unit, note, unres) in notes.items()}


EXTRAS: dict[str, Extra] = _extras()

CROSS_VALIDATION_PAIRS: tuple[tuple[str, str], ...] = (
    ("dPosition_test", "dPosition_asco_enc"),
    ("dPosition_test", "dPosition_lsv_enc"),
    ("dPosition_asco", "dPosition_asco_enc"),
)

#: 每列的物理测量原理（A-98 ②：`second_feedback_available` 的判据是「两条通道分属不同物理
#: 原理」，而不是「有两列」——同原理的两列分歧只能说明这套传感器内部不稳，不能当第二次独立
#: 测量）。来源：KB7 §硬件真值（`x_T` 电机轴编码器 / `x_asco_enc`、`x_asco_serial` 光学 /
#: `x_lsv_enc` 电感 LSV-2100-30）与 KB2 §3.5 通道卡行注。
#: 未登记的列一律 `None` ⟹ 该对**不参与**互证计数（unknown 与已知原理判"不同"是无据推断）。
PRINCIPLE: dict[str, str | None] = {
    "dPosition_test": "motor_encoder",
    "dPosition_asco": "optical_asco",
    "dPosition_asco_enc": "optical_asco",
    "dPosition_lsv_enc": "inductive_lsv",
}


def principle(raw_column: str) -> str | None:
    return PRINCIPLE.get(raw_column)


def channel_role(raw_column: str) -> str:
    """C1 登记位置：canonical 通道还是 extra（A-98 ① 的 `a_role`/`b_role` 值域）。"""
    return "canonical" if any(m.raw_column == raw_column for m in MAPPED) else "extra"


#: 指令轨候选 ↔ 反馈候选 的名字孪生（KB2 §4.1 族卡：`_tar` 后缀＝目标值）。A-98 ③ 要求
#: 「指令轨与候选反馈逐行全等」这条冒充判据在**接入层实测**，不能只留在拒映注释里——
#: 注释说的是本样本，实测才在任何一份同族导出上都成立或证伪。
CMD_FB_TWINS: tuple[tuple[str, str], ...] = (
    ("dPosition_test_tar", "dPosition_test"),
    ("dPosition_load_tar", "dPosition_load"),
    ("dVelocity_test_tar", "dVelocity_test"),
    ("dVelocity_load_tar", "dVelocity_load"),
)

#: 文档**已声明**为计算列的列 ↔ 其声明原料（KB2 §4.10 通道卡行注，A-104 ①）。
#: A-105 ① 要求接入层实测恒等式，但"实测到一条三列线性关系"本身不足以指认哪一列是算出来的：
#: `test + load + diff ≡ 0` 有三个书写方向，把真测量判成派生列就是替数据编故事。
#: 故归因只接受**唯一命中本表**的关系；其余关系登记为 `linear_dependency_unattributed`，
#: 只按自由度数扣减独立测量计数（约束是实测的，因果方向不是）。
DECLARED_COMPUTED: dict[str, tuple[str, ...]] = {
    "dPosition_diff": ("dPosition_test", "dPosition_load"),
    "dVelocity_diff": ("dVelocity_test", "dVelocity_load"),
}


def check_coverage(header_columns: list[str]) -> None:
    mapped = {m.raw_column for m in MAPPED}
    missing = [c for c in header_columns if c not in mapped and c not in EXTRAS]
    if missing:
        raise AssertionError(f"表头列未映射也未入 extra（KB2 §3.6）：{missing}")
    overlap = [c for c in header_columns if c in mapped and c in EXTRAS]
    if overlap:
        raise AssertionError(f"列同时被映为 canonical 与 extra：{overlap}")