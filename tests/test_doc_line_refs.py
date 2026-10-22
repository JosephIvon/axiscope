"""文档行号指针的落点核对（KB0 §6 检查 28 的姊妹项；任务 #44，裁决 A-120）。

纪律来自 KB0 §6 检查 22/27：**检查必须能抓缺陷（负向例），数字必须由脚本自己数**。
本文件只做两件事：把 `data/probe_doc_line_refs.py` 的判定接进套件，以及钉住它的检测力。
口径（引文归属、external-target 豁免边界）定义在探针自己的 docstring 里，不在这里复述一份。
"""
from __future__ import annotations

import importlib.util
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join(ROOT, "data", "probe_doc_line_refs.py")
sys.path.insert(0, os.path.join(ROOT, "src"))


def _load_probe():
    spec = importlib.util.spec_from_file_location("probe_doc_line_refs", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


probe = _load_probe()


def _scan(root, opts=None, targets=None):
    opts = opts if opts is not None else probe.Opts([])
    index = probe.build_index(root)
    out = []
    for rel in targets:
        recs, _, _ = probe.scan_doc(os.path.join(root, rel), root, index, opts)
        out.extend(recs)
    return out


def _repo_scan(opts=None):
    files = probe.default_targets(ROOT)
    index = probe.build_index(ROOT)
    out = []
    for f in files:
        recs, _, _ = probe.scan_doc(f, ROOT, index, opts or probe.Opts([]))
        out.extend(recs)
    return out


CASE_STATUS = ("stale", "partial-quote", "missing-file", "range-out-of-bounds")


def test_the_repo_has_no_broken_line_references():
    """缺省（严格）口径下全仓 0 病例。数字由断言现算，不抄探针打印行。"""
    bad = [r for r in _repo_scan() if r["status"] in CASE_STATUS]
    assert not bad, "行号指针病例：%s" % [
        "%s:%s %s %s" % (r["doc"], r["line"], r["ptr"], r["status"]) for r in bad]


def test_relaxed_attribution_also_finds_nothing():
    """放宽口径（认反引号引文 + 跨行找引文）是本仓排版的主口径，它也必须 0 病例——否则
    「严格口径干净」只是因为它没看。"""
    opts = probe.Opts(["--multiline", "--quote-backtick"])
    bad = [r for r in _repo_scan(opts) if r["status"] in CASE_STATUS]
    assert not bad, "放宽口径下的病例：%s" % [
        "%s:%s %s %s" % (r["doc"], r["line"], r["ptr"], r["status"]) for r in bad]


def test_external_targets_are_exactly_the_two_audited_project_paths():
    """`docs/AUDIT-*.md` 里指向**被审计项目**的路径不判病例，但必须逐条可见且数量锁死：
    多一条可能意味着我们真删了本仓文件，少一条意味着引用被改掉了。"""
    got = sorted("%s:%s %s" % (r["doc"], r["line"], r["ptr"])
                 for r in _repo_scan() if r["status"] == "external-target")
    assert got == ["docs/AUDIT-minimax-round3.md:19 tests/test_mcopilot.py:485",
                   "docs/AUDIT-minimax-round3.md:41 adapter_gen.py:73"]


def _write(tmp_path, rel, rows):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return rel


def test_it_catches_a_stale_pointer_in_a_synthetic_doc(tmp_path):
    """检查 22（负向例）：一份临时文档里放一条正确指针与一条漂移指针 ⟹ 只报漂移那条。"""
    root = str(tmp_path)
    _write(tmp_path, "kb/tgt.md", ["# 标题", "甲句 alpha-one 在这里"])
    rel = _write(tmp_path, "kb/doc.md", [
        "正确 `kb/tgt.md:2`：「甲句 alpha-one」。",
        "漂移 `kb/tgt.md:2`：「这句话仓内不存在 atoz」。",
    ])
    recs = _scan(root, targets=[rel.replace(os.sep, "/")])
    assert [r["status"] for r in recs] == ["hit", "stale"]
    assert "全文件未命中" in recs[1]["detail"]


def test_it_catches_an_out_of_bounds_range(tmp_path):
    """越界是独立的一类病，单列一例，免得「行号漂了但还在文件里」被当成同一件事。"""
    root = str(tmp_path)
    _write(tmp_path, "kb/tgt.md", ["# 标题", "甲句 alpha-one 在这里"])
    rel = _write(tmp_path, "kb/doc.md", ["越界 `kb/tgt.md:2-99`：「甲句 alpha-one」。"])
    recs = _scan(root, targets=[rel.replace(os.sep, "/")])
    assert [r["status"] for r in recs] == ["range-out-of-bounds"]
    assert "超出" in recs[0]["detail"]


def test_the_missing_file_class_survives_outside_audit_docs(tmp_path):
    """豁免边界：AUDIT 文档外的「文件不存在」仍判病例（豁免不是漂移洗白机）。"""
    root = str(tmp_path)
    _write(tmp_path, "kb/tgt.md", ["# 标题", "甲句 alpha-one 在这里"])
    plain = _write(tmp_path, "kb/plain.md", ["没了 `kb/gone.md:1`：「甲句 alpha-one」。"])
    audit = _write(tmp_path, "docs/AUDIT-x.md", ["外部 `kb/gone.md:1`：「甲句 alpha-one」。"])
    index = probe.build_index(root)
    p_plain, _, _ = probe.scan_doc(os.path.join(root, plain), root, index, probe.Opts([]))
    p_audit, _, _ = probe.scan_doc(os.path.join(root, audit), root, index, probe.Opts([]))
    assert p_plain[0]["status"] == "missing-file"
    assert p_audit[0]["status"] == "external-target"


def test_probe_selftest_is_green(capsys):
    """探针自己的负向例是它的检测力证明；它自己必须先绿，数字取自它的打印行。"""
    assert probe.selftest() == 0
    out = capsys.readouterr().out.strip().split("\n")[-1]
    m = out.replace(" ", "")
    assert m.startswith("通过"), out
    ran, ok = m.replace("通过", "").split("/执行")[0], m.replace("通过", "").split("/执行")[1]
    assert ok.split("/")[0] == ran and ran.isdigit() and int(ran) >= 25