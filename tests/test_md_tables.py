"""A-117：Markdown 表行的"形"——裸竖线、跨行拆行、列数不符（KB0 §6 检查 23 的载体）。

纪律「Markdown 表行必须单行，跨行会碎表」此前只活在 A-107 的行注里，没有任何工具核过；
而 A-114 的落点自己就制造了两例碎表（单元格里的 `max|fe|` 把一行切成 9 格），
正是检查 22 反对的形状——**散文写了口径、检测力为零**。

本例把口径交给 `data/probe_md_tables.py`：正向核全仓文档，负向按三种已知病例各造一份合成表，
证明它抓得住（抓不住的检查等于没有检查）。

    PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m pytest tests/test_md_tables.py -q
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "probe_md_tables", os.path.join(ROOT, "data", "probe_md_tables.py"))
pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pm)

TARGETS = [os.path.join(ROOT, "docs"), os.path.join(ROOT, "README.md")]


def _cases():
    out = []
    for f in pm.files_of(TARGETS):
        for blk in pm.blocks_of(f):
            want = blk["want"]
            if blk["kind"] == "orphan":
                out.append("%s:%s 碎表片段（%d 行）"
                           % (f.name, blk["rows"][0][0] if blk["rows"] else 0, len(blk["rows"])))
            for ln, grp in blk["rows"]:
                joined = " ".join(grp)
                if want is not None and (len(grp) > 1 or pm.npipes(joined) != want):
                    out.append("%s:%s split=%d pipes=%d want=%d"
                               % (f.name, ln, len(grp), pm.npipes(joined), want))
    return out


def test_every_markdown_table_row_in_the_repo_is_well_formed():
    bad = _cases()
    assert not bad, "碎表 / 裸竖线 / 列数不符的表行：\n" + "\n".join(bad)


BAD_TABLE = "\n".join([
    "| a | b |",
    "|---|---|",
    "| `x \\| y` 已转义 | 不该报 |",
    "| `max|x|` 裸竖线 | 该报 |",
    "| 多写一格 | 两 | 三 |",
    "| 拆成两行的行 | 第二格",
    "续写的内容脱表 |",
    "",
])


def test_the_probe_actually_catches_each_defect(tmp_path, capsys):
    p = tmp_path / "bad.md"
    p.write_text(BAD_TABLE, encoding="utf-8")
    rc = pm.main([str(p)])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "跨行拆行=1" in out and "列数不符=2" in out, out
    assert "已转义" not in out, "转义过的竖线被误报：" + out


BLANK_SPLIT = "\n".join([
    "| a | b |",
    "|---|---|",
    "| 表里的行 | ok |",
    "",
    "| 空行之后 | 这一段不再是表 |",
    "",
])


def test_a_table_split_by_a_blank_line_is_a_defect_too(tmp_path, capsys):
    """A-117 的第二批病例：KB0 §6 与 KB3 §2.1 的表都被空行截断过。

    初版扫描只认"表头 + `|---|`"开头的块，对这种片段**零检测力**——检查 22 的口径下，
    一个抓不住某类缺陷的检查在那一类上等于没有检查，所以本例把这个盲区钉成回归例。
    """
    p = tmp_path / "split.md"
    p.write_text(BLANK_SPLIT, encoding="utf-8")
    rc = pm.main([str(p)])
    out = capsys.readouterr().out
    assert rc == 1, out
    assert "碎表片段=1" in out, out
