"""C6 事件流读取器的负向用例（KB0 §6 检查 22：能自曝某类缺陷的检查器必须附
「故意注入该缺陷、断言真的触发」的用例，否则它只是约定不是门禁）。

事件流来自现场进程日志，词表越界若照单全收，按 source 分组的计数会静默归零而不报错——
所以这些用例守的是「拼错必须拒收」这条，不是「解析成功」那条。
"""
from __future__ import annotations

import json
import os

import pytest

from axiscope import features as F


def _write(tmp_path, rows, sync=None):
    with open(os.path.join(tmp_path, "events.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {"segments": [{"kind": "path", "t0": 0.0, "t1": 10.0}]}
    if sync is not None:
        meta["sync"] = sync
    return meta


def test_missing_events_returns_none(tmp_path):
    assert F._read_events(str(tmp_path)) is None


def test_unknown_source_is_rejected(tmp_path):
    _write(tmp_path, [{"t": 0.1, "source": "gcode", "level": "info", "code": "x"}])
    with pytest.raises(F.FeatureError, match="source"):
        F._read_events(str(tmp_path))


def test_unknown_level_is_rejected(tmp_path):
    _write(tmp_path, [{"t": 0.1, "source": "host", "level": "critical", "code": "x"}])
    with pytest.raises(F.FeatureError, match="level"):
        F._read_events(str(tmp_path))


def test_missing_timestamp_is_rejected(tmp_path):
    _write(tmp_path, [{"source": "host", "level": "info", "code": "x"}])
    with pytest.raises(F.FeatureError, match="t"):
        F._read_events(str(tmp_path))


def test_malformed_json_line_is_rejected(tmp_path):
    with open(os.path.join(tmp_path, "events.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("{not json}\n")
    with pytest.raises(F.FeatureError, match="JSON"):
        F._read_events(str(tmp_path))


def test_unknown_sync_method_is_rejected():
    with pytest.raises(F.FeatureError, match="sync.method"):
        F._read_sync({"sync": {"method": "carrier_pigeon"}})


def test_absent_sync_yields_nulls_not_placeholders():
    """A-103 ③：缺失时不得填 `unknown`/`false`/`5.0` —— 填了会悄悄参与 G3/G5 门禁。"""
    assert F._read_sync({}) == {"method": None, "verified": None, "uncertainty_ms": None}


def test_counts_are_derived_from_the_event_stream(tmp_path):
    rows = [
        {"t": 0.1, "source": "interp", "level": "warn", "code": "buffer_underrun"},
        {"t": 0.2, "source": "interp", "level": "warn", "code": "buffer_underrun"},
        {"t": 0.3, "source": "network", "level": "debug", "code": "wkc_error",
         "detail": {"hold_ms": 2.5}},
        {"t": 0.4, "source": "drive", "level": "alarm", "code": "A.8101"},
        {"t": 0.5, "source": "vision", "level": "info", "code": "result",
         "detail": {"latency_ms": 30.0}},
        {"t": 0.6, "source": "vision", "level": "info", "code": "result",
         "detail": {"latency_ms": 31.2}},
    ]
    meta = _write(tmp_path, rows)
    ev = F._read_events(str(tmp_path))
    ctx = F._event_context(ev, F._read_sync(meta), meta, lambda p, r: None)
    assert ctx["available"] is True
    assert ctx["n_events"] == 6
    assert ctx["n_alarm"] == 1
    assert ctx["interp_underrun_count"] == 2
    assert ctx["interp_underrun_during_path"] == 2  # 两条都落在 path 段 [0, 10] 内
    assert ctx["network_cycle_miss_count"] == 1
    assert ctx["bus_cycle_hold_max_ms"] == 2.5
    assert ctx["vision_result_latency_p95_ms"] == 31.2


def test_causal_claims_stay_false_when_alignment_residual_is_null(tmp_path):
    """C6 §3 规则 2：对齐残差必须 ≤ uncertainty_ms 才允许因果声明。

    残差算不出来（null）时该不等式无从判定，故即便 sync 自报 verified=true 也不放行——
    「未核」不得读成「已核且合格」。
    """
    meta = _write(tmp_path, [{"t": 0.1, "source": "host", "level": "warn", "code": "gc_pause"}],
                  sync={"method": "trigger_edge", "verified": True, "uncertainty_ms": 0.5})
    ev = F._read_events(str(tmp_path))
    ctx = F._event_context(ev, F._read_sync(meta), meta, lambda p, r: None)
    assert ctx["sync"]["verified"] is True
    assert ctx["alignment_residual_ms"] is None
    assert ctx["causal_claims_permitted"] is False


def test_undefined_fe_spike_vocabulary_is_registered_not_invented(tmp_path):
    """`fe_spike_*` 没有权威口径时必须登记 null 并写明理由，不得臆造一个阈值。"""
    meta = _write(tmp_path, [{"t": 0.1, "source": "host", "level": "warn", "code": "gc_pause"}])
    rows = []
    F._event_context(F._read_events(str(tmp_path)), F._read_sync(meta), meta,
                     lambda p, r: rows.append((p, r)))
    registered = {p for p, _ in rows}
    assert "event_context.fe_spike_count" in registered
    assert "event_context.alignment_residual_ms" in registered
    reasons = dict(rows)
    assert "不臆造" in reasons["event_context.fe_spike_count"]