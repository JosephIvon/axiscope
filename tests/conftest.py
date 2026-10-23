"""原始数据按 A-131 口径不入库（可按 DOI 重下 / 由生成器再生）；干净克隆里缺件时，
依赖它的测试必须**响亮地跳过**并写明「当前不可自动复核」——
既不许红着装作已核过，也不许静默跳过（KB0 §6 检查 22 的形状：跳过也要有口径）。

声明方式：各测试文件顶部写 `REQUIRES_DATA = ("data/raw/xxx.csv", ...)`，
由本文件统一执行。**显式声明，不靠猜路径**——猜出来的口径迟早会漂。
"""
from __future__ import annotations

import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# CLI 用例需要的原始数据（与 test_offline_discipline.py 的两条用例对应）
CLI_DATA = (
    "data/raw/Export10_244531.csv",
    "data/incoming/6114_ObserverTestSet.tab",
)


def _missing(rel_paths):
    return [rel for rel in rel_paths
            if not os.path.isfile(os.path.join(ROOT, rel.replace("/", os.sep)))]


def pytest_collection_modifyitems(config, items):
    """缺原始数据的测试逐条跳过，并把缺件清单写进 skip 原因（loud skip）。"""
    for item in items:
        need = getattr(item.module, "REQUIRES_DATA", ())
        if not need:
            continue
        missing = _missing(need)
        if missing:
            item.add_marker(pytest.mark.skip(
                reason="原始数据按 A-131 口径不入库，缺 %s："
                       "在档结论与指纹自洽，但**当前不可自动复核**" % "、".join(missing)))


@pytest.fixture
def require_cli_data():
    missing = _missing(CLI_DATA)
    if missing:
        pytest.skip("原始数据按 A-131 口径不入库，缺 %s："
                    "**当前不可自动复核**" % "、".join(missing))
