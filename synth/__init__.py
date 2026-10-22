"""KB5 合成被控对象：参数集、模型、注入、样本包写出器。

规范：`docs/kb/KB5-simulation-plant.md`。本包只做「规范 → 代码」的落地，
不改写规范里的任何一个物理量出处；每个参数的 provenance 逐项落在 `truth.json`。

证据层级纪律（KB5 §0 / §6.2）：本包产出的样本 `source_tier = "T3"`，
只能表述为「判据按构造检出植入误差、且在对抗案例上正确拒答」，
**不得**表述为诊断准确。
"""
from __future__ import annotations

__all__ = ["SCHEMA_TRUTH", "WAVING_CAVEAT"]

SCHEMA_TRUTH = "axiscope.truth/1"
WAVING_CAVEAT = "仿真不含真实调度器与总线仲裁"