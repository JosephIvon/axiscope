"""C1 §audit.assumptions 的锚定词表（#25 / C3 规则 19 的唯一实现）。

正向表逐形式给一个真实用过的锚；负向表钉住"散文不是锚"（KB0 §6 检查 22）。
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from axiscope import anchors  # noqa: E402


@pytest.mark.parametrize("anchor,kind", [
    ("meta.drive.current_limit_a", "meta 字段"),
    ("meta.audit.identity_check", "meta 字段"),
    ("channels.vel_fb", "通道"),
    ("extra_channels.dPosition_asco", "通道"),
    ("event_context.sync.uncertainty_ms", "C2 特征路径"),
    ("resonance.estimation.n_segments", "C2 特征路径"),
    ("step_response[0].settling_time_ms", "C2 特征路径"),
    ("R-11", "规则/判据"),
    ("R-11#switching_freq", "规则/判据"),
    ("electrical_feedforward_mismatch", "KB 叶名"),
    ("software_induced_host_thread_jitter", "KB 叶名"),
    ("KB4§2.1(c)", "文档锚"),
])
def test_six_anchor_forms(anchor, kind):
    assert anchors.anchor_kind(anchor) == kind


@pytest.mark.parametrize("anchor", [
    "限流值没给，按额定电流兜底",           # 散文
    "H2 的 severity 是自己推断的",          # 散文
    "src/axiscope/engine.py",              # 仓内路径
    "../meta.json",                        # 越界路径
    "channels.vel_fb 的符号",              # 带空格的半截锚
    "kb4 2.9",                             # 文档锚缺 §
    "",                                    # 空
    None,                                  # 缺键
])
def test_non_anchors_are_rejected(anchor):
    assert anchors.anchor_kind(anchor) is None


def test_assumption_row_needs_both_keys():
    assert anchors.assumption_row("channels.torque", "绝对刻度未定") == {
        "anchor": "channels.torque", "statement": "绝对刻度未定"}
    with pytest.raises(anchors.AnchorNotStable):
        anchors.assumption_row("刻度没定", "绝对刻度未定")
    with pytest.raises(anchors.AnchorNotStable):
        anchors.assumption_row("channels.torque", "   ")
