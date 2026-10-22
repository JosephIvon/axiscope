"""厂商导出方言分派器：把非 Scope View 的布局归一到 `twincat.ScopeTable`。

只回答三件事：**有哪些列、每列多少行、时间轴从哪来**。列的物理语义是 mapping.py 的活
（KB2 §三「不猜语义」/ KB0 §1「无来源不填值」），本模块一概不判。

时间轴是唯一带硬门槛的东西，口径照 KB2 §4.12 的 R-3 / R-6 / R-7：

- ISO-8601 文本时间列 → epoch 秒（单位由格式本身定死，不做 us/ms/s 假设）；
- 列名里带单位（`X (ms)`）→ 按列名换算，出处记 `column_name:<unit>`；
- 列名既不带单位、内容也不是 ISO 文本 → 唯一合法出路是**外部佐证**
  （同目录 `<file>.source.txt` 的 `sampling_rate` 声称，且三种单位假设里**有且仅有一种**
  复现该声称），出处记 `sidecar_attested:<unit>`；
- 以上都不成立 → **拒读**。不拿「第一个递增的数值列」顶替时间列（那是 R-7 点名的
  「身份未证实」启发式），也不假定等间隔——没有时间基就没有 fs，特征与频谱判据全部失效。
"""
from __future__ import annotations

import datetime
import io
import os
import re

from .twincat import REDACT_PATTERNS, Column, ScopeFormatError, ScopeTable, _to_float

DIALECT_CSV_ISO = "csv_iso8601_rowindex"
DIALECT_TSV_ISO = "tsv_iso8601"
DIALECT_SEMICOLON_EURO = "semicolon_european_decimal"
DIALECT_CSV_SEGMENT = "csv_segment_index"

DELIM_NAMES = {"\t": "tab", ";": "semicolon", ",": "comma"}

#: 列名即 ISO-8601 时间列（KB2 §4.12 R-3 修的正是这一族：`t` 列是 ISO 文本）。
ISO_TIME_NAMES = frozenset({"t", "time", "timestamp", "zeit", "ts"})

#: 列名里带单位的数值时间列：`X (ms)`、`t (s)`（2563 导出实测写法）。
UNIT_TIME_RE = re.compile(r"\(\s*(ns|us|µs|μs|ms|s|sec|secs|second|seconds)\s*\)\s*$", re.I)
#: 别名折到四个规范单位上：折之前的别名表会让「有且仅有一种假设复现侧车声称」这条判据
#: 一次命中五个键（sec/secs/second/seconds 同值），把唯一性判据废掉。
UNIT_ALIAS = {"ns": "ns", "us": "us", "µs": "us", "μs": "us", "ms": "ms",
              "s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s"}
UNIT_TO_MS = {"ns": 1e-6, "us": 1e-3, "ms": 1.0, "s": 1e3}

ISO_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:[.,](\d+))?"
    r"(?:\s*(?:Z|([+-])(\d{2}):?(\d{2})(?::?(\d{2}))?))?$")

#: 名字里带 time 但不带单位的数值时间列（`TimeOutput`）——单位只能来自外部佐证。
#: 词表与 `data/validate_raw.py::TIME_NAME` 同源同文，避免两处各认一份（A-54 单一名字律）。
NUMERIC_TIME_NAME_RE = re.compile(
    r"(?:sampletime|^time|\btime\b|_ms$|_us$|_s$|zeit|timestamp|\bts\b|sample)", re.I)

NUM_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
COMMA_DEC_RE = re.compile(r"^-?(?:\d+,\d*|,\d+)(?:[eE][+-]?\d+)?$")

#: D4（无时间列的 TSV 测量表）表头形态：整行都是裸标识符列名。
BARE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_SIDECAR_FS_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\s*[Hh][Zz]")
_SIDECAR_KEYS = ("publisher", "license", "dataset_doi", "original_filename", "url")


def is_scope_view(lines: list[str]) -> bool:
    """Scope View 判据：前 200 行里存在 `Name<TAB>非空` 的表头行（D1 的原有判据）。"""
    for line in lines[:200]:
        cells = line.split("\t")
        if len(cells) > 1 and cells[0].strip() == "Name" and cells[1].strip() != "":
            return True
    return False


def sniff_delimiter(line: str) -> str | None:
    """TAB 优先、其次分号、最后半角逗号；`;` 优先于 `,` 是欧洲小数逗号布局的前提。"""
    for d in ("\t", ";", ","):
        if line.count(d) >= 2:
            return d
    return None


def sniff_decimal_comma(rows: list[list[str]]) -> bool:
    """表体是否用逗号作小数点（KB2 R-6）。点十进制几乎不出现**且**逗号十进制占多数，
    两个条件同时成立才算——防把千分位 `1,234` 误判成小数逗号。"""
    dot = com = 0
    for r in rows[:200]:
        for c in r:
            s = (c or "").strip()
            if NUM_RE.match(s):
                dot += 1
            elif COMMA_DEC_RE.match(s):
                com += 1
    return com >= 20 and com > 4 * dot


def iso_epoch_s(tok: str) -> float:
    """ISO-8601 文本时间戳 → epoch 秒；形态不合返回 NaN。裸时间戳按 UTC 理解
    （单调性与 dt 统计只看差分，同文件内的时区偏移相消）。"""
    m = ISO_TS_RE.match((tok or "").strip())
    if not m:
        return float("nan")
    y, mo, d, hh, mi, ss, frac, sign, oh, om, osec = m.groups()
    micro = int((frac + "000000")[:6]) if frac else 0
    try:
        base = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss), micro,
                                 tzinfo=datetime.timezone.utc)
    except ValueError:
        return float("nan")
    if sign:
        off = datetime.timedelta(hours=int(oh), minutes=int(om), seconds=int(osec or 0))
        base += off if sign == "-" else -off
    return base.timestamp()


def sidecar_fields(path: str) -> dict[str, str]:
    """`<file>.source.txt` 侧车的键值（数据集出处与发布者声明都登记在这里）。"""
    side = path + ".source.txt"
    if not os.path.exists(side):
        return {}
    try:
        text = io.open(side, encoding="utf-8").read()
    except OSError:
        return {}
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip().lower()
        if k in _SIDECAR_KEYS or k == "sampling_rate":
            out[k] = v.strip()
    return out


def sidecar_sampling_rate_hz(path: str) -> float | None:
    claim = sidecar_fields(path).get("sampling_rate", "")
    m = _SIDECAR_FS_RE.search(claim)
    return float(m.group(1)) if m else None


def _median(xs: list[float]) -> float:
    srt = sorted(xs)
    return srt[len(srt) // 2]


def _looks_iso(cells: list[str]) -> bool:
    vals = [c.strip() for c in cells if c and c.strip()]
    if len(vals) < 3:
        return False
    return sum(1 for v in vals if ISO_TS_RE.match(v)) >= 0.9 * len(vals)


def _resolve_time_column(names: list[str], rows: list[list[str]]) -> tuple[int | None, str, str]:
    """（列号, time_col_source, 形态）。形态 ∈ {"iso8601", "numeric"}；列号 None = 无时间列。"""
    for j, nm in enumerate(names):
        if nm.lower() in ISO_TIME_NAMES:
            return j, "column_name", "iso8601"
    for j, nm in enumerate(names):
        if UNIT_TIME_RE.search(nm):
            return j, "column_name", "numeric"
    for j, nm in enumerate(names):
        if NUMERIC_TIME_NAME_RE.search(nm):
            return j, "column_name", "numeric"
    for j in range(len(names)):
        if _looks_iso([r[j] for r in rows[:200] if j < len(r)]):
            return j, "iso8601_content", "iso8601"
    return None, "none", "none"


def _time_values(name: str, kind: str, rows: list[list[str]], j: int, path: str) -> list[float]:
    if kind == "iso8601":
        vals = []
        for i, r in enumerate(rows):
            v = iso_epoch_s(r[j])
            if v != v:
                raise ScopeFormatError(
                    f"时间列 {name} 第 {i} 行不是 ISO-8601 时间戳：{r[j]!r}（{path}）；"
                    "时间基不可得，按 C1 拒读，不退回等间隔假设")
            vals.append(v)
        return vals
    vals = []
    for i, r in enumerate(rows):
        try:
            vals.append(_to_float(r[j]))
        except ValueError as exc:
            raise ScopeFormatError(
                f"时间列 {name} 第 {i} 行不是数值：{r[j]!r}（{exc}，{path}）") from exc
    if any(v != v for v in vals):
        raise ScopeFormatError(f"时间列 {name} 含空/非数值单元 ⟹ 时基有缺口，按 C1 拒读：{path}")
    return vals


def _unit_to_ms(name: str, dt_median_raw: float, path: str) -> tuple[float, str]:
    """时间列单位 → 毫秒/单位 与出处标签。列名不带单位时只认侧车外部佐证，不做默认值。"""
    m = UNIT_TIME_RE.search(name)
    if m:
        unit = UNIT_ALIAS[m.group(1).lower()]
        return UNIT_TO_MS[unit], "column_name:" + unit
    claim = sidecar_sampling_rate_hz(path)
    if claim:
        hits = [u for u in UNIT_TO_MS
                if abs(1000.0 / (dt_median_raw * UNIT_TO_MS[u]) - claim) <= 0.05 * max(claim, 1e-9)]
        if len(hits) == 1:
            return UNIT_TO_MS[hits[0]], "sidecar_attested:" + hits[0]
    raise ScopeFormatError(
        f"时间列 {name} 的单位无来源：列名未带单位，侧车 <file>.source.txt 的 sampling_rate "
        f"声称也无法在 us/ms/s 三种假设里唯一复现（{path}）；KB2 §5.2：单位未定不得据此开样本")


def _no_timebase(path: str, names: list[str]) -> ScopeFormatError:
    return ScopeFormatError(
        f"该导出无时间列，无法确定采样率，按 C1 拒收：{path}"
        f"（表头 {len(names)} 列均为裸通道名 {names[:5]}，既无时间语义列名、"
        "内容也不是 ISO-8601 文本；KB2 §4.12 R-7：不得拿「第一个递增的数值列」顶替时间列，"
        "更不得假定等间隔——没有时间基就没有 fs，特征与频谱判据全部失效）")


def _unrecognized(path: str, delim: str | None, names: list[str]) -> ScopeFormatError:
    return ScopeFormatError(
        f"未识别为任何已知导出方言：未找到 TwinCAT Scope View 的 'Name' 表头行，"
        f"分隔符 {DELIM_NAMES.get(delim, delim)!r} 的首行也不像测量列清单（{names[:4]}）：{path}")


def read_table(path: str, *, text: str, newline: str, bom: bool) -> ScopeTable:
    """非 D1 方言的统一入口：产出与 `read_scope()` 同型的 `ScopeTable`。"""
    lines = text.split("\r\n") if newline == "\r\n" else text.split("\n")
    while lines and lines[-1].strip() == "":
        lines.pop()
    head_at = next((i for i, l in enumerate(lines) if l.strip() != ""), None)
    if head_at is None:
        raise ScopeFormatError(f"文件无内容：{path}")
    head = lines[head_at]
    delim = sniff_delimiter(head)
    if delim is None:
        raise _unrecognized(path, delim, [head.strip()])
    names = [c.strip() for c in head.split(delim)]
    if len(set(names)) != len(names):
        raise ScopeFormatError(f"表头列名重复，无法唯一定位列：{path}")

    raw_rows: list[list[str]] = []
    n_mismatch = 0
    for line in lines[head_at + 1:]:
        if line.strip() == "":
            continue
        cells = [c.strip() for c in line.split(delim)]
        if len(cells) != len(names):
            n_mismatch += 1
            continue
        raw_rows.append(cells)
    if not raw_rows:
        raise ScopeFormatError(f"表头之后无数据行：{path}")

    euro = sniff_decimal_comma(raw_rows)
    if euro:
        # 先按 `;` 切分、再把每个字段里的 `,` 换成 `.`；顺序反了会把数字切碎
        raw_rows = [[c.replace(",", ".") for c in r] for r in raw_rows]

    t_at, t_source, t_kind = _resolve_time_column(names, raw_rows)
    if t_at is None:
        if delim == "\t" and len(names) >= 2 \
                and all(BARE_NAME_RE.match(n) for n in names) and raw_rows:
            raise _no_timebase(path, names)
        raise _unrecognized(path, delim, names)

    t_raw = _time_values(names[t_at], t_kind, raw_rows, t_at, path)
    dts = [b - a for a, b in zip(t_raw, t_raw[1:])]
    if not dts:
        raise ScopeFormatError(f"时间列 {names[t_at]} 只有 1 行 ⟹ 无 dt、无采样率，按 C1 拒收：{path}")
    for i, d in enumerate(dts):
        if not d > 0:
            raise ScopeFormatError(
                f"时基非严格单调：时间列 {names[t_at]} 第 {i+1} 行相对前一行 Δ={d:g} "
                f"（{path}）；身份已证实的时间列才判单调（KB2 §4.12 R-7）")
    dt_median_raw = _median(dts)
    ms_per_unit, unit_source = (1000.0, "iso8601_text:epoch_seconds") if t_kind == "iso8601" \
        else _unit_to_ms(names[t_at], dt_median_raw, path)

    # `sample_index` 装的是**相对首行的毫秒数**而不是行序号：这几条方言的时间轴来自导出自带的
    # 时间列，逐行差分才带抖动/丢行信息，用行序号会把它们抹平成等间隔。`sample_time_ms` 取 1.0
    # 只作「毫秒 → 秒」的换算载体（下游 `timebase_stats(index, dt_ms)` 仍按 `(Δidx)·dt_ms/1000`
    # 取秒），**不是**厂商声明的采样周期——声明周期只有 Scope View 的 `SampleTime[ms]` 才是。
    sample_index = [(v - t_raw[0]) * ms_per_unit for v in t_raw]

    idx_at = 0 if names[0] == "" else None
    id_at = next((j for j, n in enumerate(names)
                  if j != t_at and n.lower() == "id"), None)
    skip = {j for j in (t_at, idx_at, id_at) if j is not None}

    columns: list[Column] = []
    series: dict[str, list[float]] = {}
    for j, nm in enumerate(names):
        if j in skip:
            continue
        try:
            series[nm] = [_to_float(r[j]) for r in raw_rows]
        except ValueError as exc:
            raise ScopeFormatError(f"通道 {nm} 含非数值单元：{exc}（{path}）") from exc
        columns.append(Column(name=nm, symbol=None, unit=None, col_index=j))
    if not columns:
        raise ScopeFormatError(f"除时间列与结构列外没有任何测量通道：{path}")

    if delim == "\t":
        dialect = DIALECT_TSV_ISO
    elif delim == ";":
        dialect = DIALECT_SEMICOLON_EURO
    elif idx_at == 0 and t_at == 1:
        dialect = DIALECT_CSV_ISO
    else:
        dialect = DIALECT_CSV_SEGMENT

    hits = {p: text.count(p) for p in REDACT_PATTERNS}
    file_meta = {
        "axiscope.dialect": dialect,
        "delimiter": DELIM_NAMES[delim],
        "decimal_comma": "true" if euro else "false",
        "time_column": names[t_at],
        "time_col_source": t_source,
        "time_unit_source": unit_source,
        "row_index_column": names[idx_at] if idx_at is not None else "",
        "id_column": names[id_at] if id_at is not None else "",
        "header_columns_total": str(len(names)),
        "encoding": "utf-8-sig" if bom else "utf-8",
    }
    side = sidecar_fields(path)
    for key in _SIDECAR_KEYS:
        if key in side:
            file_meta["sidecar." + key] = side[key][:160]

    return ScopeTable(
        path=path, encoding=file_meta["encoding"], newline=newline, bom=bom,
        n_header_rows=head_at + 1, n_columns=len(columns), columns=columns,
        sample_time_ms=1.0, n_rows_raw=len(raw_rows), n_rows_shape_mismatch=n_mismatch,
        sample_index=sample_index, data=series, file_meta=file_meta,
        redaction_hits={k: v for k, v in hits.items() if v},
        dialect=dialect, time_column=names[t_at], time_col_source=t_source,
        unit_source=unit_source,
    )