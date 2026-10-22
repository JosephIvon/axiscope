"""TwinCAT 3 Scope View CSV 读取器（KB2 §4.1 族卡 + §4.10 样本卡实测形态）。

只做「读成结构化表」这一件事，语义映射在 mapping.py，契约装包在 c1.py。
"""
from __future__ import annotations

import io
import math
import os
from dataclasses import dataclass, field

REDACT_PATTERNS = (
    "Versuchsstand",
    "[REDACTED_ADS_NETID]",
    r"C:\\",
)


class ScopeFormatError(Exception):
    """结构定位失败：宁可拒读，不得按猜测解析（KB2 §三）。"""


@dataclass
class Column:
    name: str
    symbol: str | None
    unit: str | None
    col_index: int
    meta: dict = field(default_factory=dict)


@dataclass
class ScopeTable:
    path: str
    encoding: str
    newline: str
    bom: bool
    n_header_rows: int
    n_columns: int
    columns: list[Column]
    sample_time_ms: float | None
    n_rows_raw: int
    n_rows_shape_mismatch: int
    sample_index: list[float]
    data: dict[str, list[float]]
    file_meta: dict[str, str]
    redaction_hits: dict[str, int]
    # —— 下方四个槽位只被导出方言分派器（dialects.py）填，D1 保持缺省值 ——
    dialect: str = "twincat_scope_view"
    time_column: str | None = None
    time_col_source: str | None = None
    unit_source: str | None = None

    def column(self, name: str) -> Column:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(name)


def _split(text: str) -> list[str]:
    return text.split("\r\n") if "\r\n" in text[:4096] else text.split("\n")


def _to_float(cell: str) -> float:
    cell = cell.strip()
    if cell == "" or cell.lower() in ("nan", "na", "#nAN"):
        return float("nan")
    return float(cell)


def read_scope(path: str) -> ScopeTable:
    raw = io.open(path, "rb").read()
    bom = raw[:3] == b"\xef\xbb\xbf"
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text[:4096] else "\n"
    lines = _split(text)

    from . import dialects                      # 顶层 import 会与 dialects→twincat 成环
    if not dialects.is_scope_view(lines):
        return dialects.read_table(path, text=text, newline=newline, bom=bom)

    hits = {p: text.count(p) for p in REDACT_PATTERNS}
    hits = {k: v for k, v in hits.items() if v}

    names_at = None
    best = 0
    for i, line in enumerate(lines[:200]):
        cells = line.split("\t")
        if len(cells) > best and cells[0].strip() == "Name" and cells[1].strip() != "":
            names_at, best = i, len(cells)
    if names_at is None:
        raise ScopeFormatError(f"未找到 'Name' 表头行：{path}")

    names_row = lines[names_at].split("\t")
    if len(names_row) % 2 != 0:
        raise ScopeFormatError(f"表头列数为奇数（非键值交替）：{len(names_row)}")
    n_columns = len(names_row) // 2
    names = [names_row[2 * k + 1].strip() for k in range(n_columns)]
    if len(set(names)) != n_columns:
        raise ScopeFormatError("通道名重复，无法唯一定位列")

    columns = [Column(name=names[k], symbol=None, unit=None, col_index=2 * k + 1)
               for k in range(n_columns)]
    kv_rows: list[list[str]] = []
    r = names_at + 1
    while r < len(lines):
        cells = lines[r].split("\t")
        if len(cells) == 1 and cells[0].strip() == "":
            break
        if len(cells) != len(names_row):
            break
        try:
            float(cells[0])
            break  # 数值行即数据行：键值块到此为止
        except ValueError:
            pass
        kv_rows.append(cells)
        r += 1
    while r < len(lines) and lines[r].strip() == "":
        r += 1
    for cells in kv_rows:
        key = cells[0].strip()
        for k in range(n_columns):
            columns[k].meta[key] = cells[2 * k + 1].strip()
    for col in columns:
        col.unit = col.meta.get("SampleTime[ms]")
        sym = col.meta.get("SymbolName")
        col.symbol = sym or None

    sample_time = None
    for col in columns:
        if col.unit not in (None, ""):
            sample_time = float(col.unit)
            break

    data_start = r
    rows: list[list[str]] = []
    n_mismatch = 0
    for line in lines[data_start:]:
        if line == "":
            continue
        cells = line.split("\t")
        if len(cells) != len(names_row):
            n_mismatch += 1
            continue
        rows.append(cells)

    file_meta: dict[str, str] = {}
    for line in lines[:names_at]:
        cells = line.split("\t")
        if len(cells) >= 2 and cells[0].strip() and not cells[0].strip().startswith("Starttime") \
                and not cells[0].strip().startswith("Endtime"):
            file_meta.setdefault(cells[0].strip(), cells[1].strip())

    sample_index = [_to_float(row[0]) for row in rows]
    series: dict[str, list[float]] = {}
    for k, col in enumerate(columns):
        j = 2 * k + 1
        col.col_index = j
        try:
            series[col.name] = [_to_float(row[j]) for row in rows]
        except ValueError as exc:
            raise ScopeFormatError(f"通道 {col.name} 含非数值单元：{exc}") from exc

    return ScopeTable(
        path=path, encoding="utf-8", newline=newline, bom=bom,
        n_header_rows=data_start, n_columns=n_columns, columns=columns,
        sample_time_ms=sample_time, n_rows_raw=len(lines) - data_start - 1,
        n_rows_shape_mismatch=n_mismatch, sample_index=sample_index, data=series,
        file_meta=file_meta, redaction_hits=hits,
    )


def gate_episodes(flags: list[float]) -> list[tuple[int, int]]:
    """返回门控为真的极大连续区间 [start, end]（含端）。"""
    eps: list[tuple[int, int]] = []
    start = None
    for i, v in enumerate(flags):
        if v == v and v != 0:
            if start is None:
                start = i
        elif start is not None:
            eps.append((start, i - 1))
            start = None
    if start is not None:
        eps.append((start, len(flags) - 1))
    return eps


def timebase_stats(index: list[float], dt_ms: float) -> dict:
    dts = [(index[i + 1] - index[i]) * dt_ms / 1000.0 for i in range(len(index) - 1)]
    if not dts:
        return {"dt_median_s": None, "dt_jitter_ratio": None, "strictly_monotonic": False}
    srt = sorted(dts)
    med = srt[len(srt) // 2]
    mean = sum(dts) / len(dts)
    var = sum((d - mean) ** 2 for d in dts) / len(dts)
    jitter = math.sqrt(var) / mean if mean else float("nan")
    return {
        "dt_median_s": med,
        "dt_jitter_ratio": 0.0 if jitter != jitter else jitter,
        "strictly_monotonic": all(d > 0 for d in dts),
        "gap_max_s": max(dts),
    }


def basename(path: str) -> str:
    return os.path.basename(path)