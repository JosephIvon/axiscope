"""`audit.assumptions` 的元素形状（C1 §audit.assumptions；C3 规则 19 的机器侧）。

为什么单独一个叶子模块：C1 接入层与 C3 引擎层产**同一个形状**，而既有依赖方向是
`features.py → c1.py`，把形状定义放进 `registration.py`（它 import features）会让 c1
反向依赖登记层 ⟹ 成环。锚定词表本身不依赖任何人，所以它自己成为一个叶子。
"""
from __future__ import annotations
import re

#: 稳定锚的六种形式。散文不是锚：一条没有锚的 assumption 无法被报告引用，
#: 也回答不了"这条假定作废时哪条结论跟着塌"。
ANCHOR_FORMS = (
    ("meta 字段", re.compile(r"^meta(?:\.[A-Za-z0-9_]+)+$")),
    ("通道", re.compile(r"^(?:channels|extra_channels)\.[A-Za-z0-9_\[\]\-]+$")),
    ("C2 特征路径",
     re.compile(r"^[a-z][a-z0-9_]*(?:\[\w+\])?(?:\.[a-z][a-z0-9_]*(?:\[\w+\])?)+$")),
    ("规则/判据", re.compile(r"^R-\d{2}(?:#[A-Za-z0-9_]+)?$")),
    ("KB 叶名", re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}$")),
    ("文档锚", re.compile(r"^KB\d(?:§[^\s]+)?$")),
)


class AnchorNotStable(ValueError):
    """anchor 不落在受控形式内，或 statement 为空 ⟹ 这条登记不可被引用（C3 规则 19）。"""


def anchor_kind(anchor) -> str | None:
    for name, rx in ANCHOR_FORMS:
        if isinstance(anchor, str) and rx.match(anchor):
            return name
    return None


def assumption_row(anchor: str, statement: str) -> dict:
    kind = anchor_kind(anchor)
    if kind is None:
        raise AnchorNotStable(
            f"assumption 的 anchor {anchor!r} 不在 C1 §audit.assumptions 的六种稳定形式内")
    if not isinstance(statement, str) or not statement.strip():
        raise AnchorNotStable(f"{anchor} 的 assumption 缺少 statement 散文")
    return {"anchor": anchor, "statement": statement}
