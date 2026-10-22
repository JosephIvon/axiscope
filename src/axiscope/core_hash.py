"""C3 规则 21：`audit.deterministic_core_hash` 的哈希核（本模块是该定义在代码里的唯一落点）。

契约在 `docs/contracts/C3-diagnosis.md` 规则 21，生产者（`engine.analyze`）与校验器
（`c3validate.validate`）共用本模块的 `core_hash()`。规则 21 明写「落码侧与校验器复算侧
必须按本条，不得各自发明」——两侧各写一份就等于留下一个「产品自洽、校验器自洽、两者
互相不一致」的合法角落，而那正是本字段要排除的形状。

规范化四步（规则 21 逐字）：(1) 按清单把产物裁成一棵树；(2) `json.dumps(...,
ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`；
(3) UTF-8 编码取 SHA-256；(4) 写成 `sha256:<64 位小写 hex>`。三条不可省细节也在这里：
数组顺序保留（`hypotheses[]` 的 rank 序正是被锁定的对象）、`null` 保留为 `null` 不省键
（"没实现"与"值为 null"必须哈希不同）、不做二次取整（吃的是产物里已 `display()` 的两位值，
因此本哈希区分不了 ±0.01 并列带内两位显示相同的两种序——那一侧由 KB4 §2.9 的并列带负责）。
"""
from __future__ import annotations

import hashlib
import json

HASH_PREFIX = "sha256:"
HASH_LENGTH = 64
# 规则 21 的合法值三形态：空串（生产者未计算）/ `sha256:<hex>`（已计算）/ `…`（示例占位符，待清零）
EMPTY_HASH = ""
PLACEHOLDER_HASH = "…"

# 规则 21 点名的字段清单。清单外的键一律不进核（"唯一清单"是排他的，不是"至少含"）。
VERDICT_KEYS = ("primary", "overall_confidence", "actionable")
HYPOTHESIS_KEYS = ("id", "fault_mode", "rank", "confidence", "severity",
                   "next_data_to_collect")
# `considered` 的元素本身就是 fault_mode slug；`not_evaluable` 行按契约点名只取 fault_mode
# 与原因键（仓内实际键名是 `why`，`rules_skipped` 那边才是 `reason`）。
# `blocked_by` 不在核内：它对结论的唯一作用是喂 §2.2 的缺席扣减，而 `verdict.overall_confidence`
# 已在核内 ⟹ 换 blocked_by 若改变不了结论就不该改指纹，改得了就已经被抓。
DIFF_ROW_KEYS = ("fault_mode", "why", "reason")
RULE_SKIPPED_KEYS = ("rule_id", "reason")


def core_tree(diagnosis: dict) -> dict:
    """按规则 21 的清单把产物裁成参与哈希的树。清单里的键即使缺席也补成 `null`
    （规则 21 细节 ii：`null` 不得省键，否则"字段没实现"与"字段值为 null"会哈希成同一个）。"""
    verdict = diagnosis.get("verdict") or {}
    hypotheses = diagnosis.get("hypotheses") or []
    differential = diagnosis.get("differential") or {}
    audit = diagnosis.get("audit") or {}
    return {
        "schema": diagnosis.get("schema"),
        "case_id": diagnosis.get("case_id"),
        "inputs": _plain(diagnosis.get("inputs")),
        "verdict": {k: _plain(verdict.get(k)) for k in VERDICT_KEYS},
        "hypotheses": [_hypothesis(h) for h in hypotheses if isinstance(h, dict)],
        "differential": {
            "considered": _plain(differential.get("considered")),
            "not_evaluable": [_diff_row(r) for r in _rows(differential.get("not_evaluable"))],
        },
        "validation": _plain(diagnosis.get("validation")),
        "safety": _plain(diagnosis.get("safety")),
        "freq_limits": _plain(diagnosis.get("freq_limits")),
        "audit": {
            "rules_fired": _plain(audit.get("rules_fired")),
            "rules_skipped": [{k: _plain(row.get(k)) for k in RULE_SKIPPED_KEYS}
                              for row in _rows(audit.get("rules_skipped"))],
            "assumptions": [{"anchor": _plain(a.get("anchor"))}
                            for a in _rows(audit.get("assumptions")) if isinstance(a, dict)],
        },
    }


def core_hash(diagnosis: dict) -> str:
    """规则 21 的四步规范化，返回 `sha256:<64 位小写 hex>`。"""
    blob = json.dumps(core_tree(diagnosis), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")
    return HASH_PREFIX + hashlib.sha256(blob).hexdigest()


def is_computed(value) -> bool:
    return (isinstance(value, str) and value.startswith(HASH_PREFIX)
            and len(value) == len(HASH_PREFIX) + HASH_LENGTH
            and all(c in "0123456789abcdef" for c in value[len(HASH_PREFIX):]))


def is_placeholder(value) -> bool:
    return value == PLACEHOLDER_HASH


def _hypothesis(h: dict) -> dict:
    out = {k: _plain(h.get(k)) for k in HYPOTHESIS_KEYS}
    # 证据行的 13 键 / 反证行的 8 键逐字进核：它们是 C 的原始输入，规则 15 逐条判它们。
    out["supporting_evidence"] = _plain(h.get("supporting_evidence"))
    out["contradicting_evidence"] = _plain(h.get("contradicting_evidence"))
    return out


def _diff_row(row) -> dict:
    if not isinstance(row, dict):
        return {"fault_mode": _plain(row)}
    return {k: _plain(row.get(k)) for k in DIFF_ROW_KEYS}


def _rows(x) -> list:
    return x if isinstance(x, list) else []


def _plain(value):
    """只留 `dict/list/str/int/float/bool/None`（规则 21 第 1 步）。"""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)