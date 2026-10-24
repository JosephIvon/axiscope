"""探针：本地各导出方言在现有解析器上的实际行为。

口径：只报**实测**结果 —— 每份文件喂给 `axiscope.run()`，打印成功/异常类型/异常首行，
外加用 `twincat.read_scope` 单独看它停在读表头还是读数据那一层。

用法：PYTHONPATH=src PYTHONIOENCODING=utf-8 python data/probe_dialects.py
"""
from __future__ import annotations

import io
import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from axiscope import c1, engine, features, twincat  # noqa: E402

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


CANDIDATES = [
    ("TwinCAT Scope View (t_idx,value) 交替 / TAB / 元数据块",
     "data/raw/Export10_244531.csv"),
    ("半角逗号 / 首列空表头行号 / ISO-8601 时间列 t",
     "data/incoming/6114_lsmc.csv"),
    ("TAB 分隔 / t 为 ISO-8601",
     "data/incoming/current-hunt/3900_const_vel_110.tab"),
    ("TAB 分隔 / t 为 ISO-8601（6114 另一文件）",
     "data/incoming/6114_ObserverTestSet.tab"),
    ("分号分隔 + 欧洲小数逗号 + X (ms) 时间列",
     "data/incoming/2563_LDD_Transfer_function_Force_controlled.csv"),
    ("首列段名 / 半角逗号 / 科学计数法",
     "data/raw/参数分析仪波形_PMU_1t1r_CVSV导出样例.csv"),
]

OUT = "build/dialect_probe"


def probe_read(path: str) -> str:
    try:
        table = twincat.read_scope(path)
    except Exception as exc:  # noqa: BLE001 — 探针要看见任何失败
        return f"FAIL  {type(exc).__name__}: {str(exc).splitlines()[0][:120]}"
    return (f"OK    n_rows_raw={table.n_rows_raw} n_columns={table.n_columns} "
            f"header_rows={getattr(table, 'header_rows', 'n/a')}")


def probe_full(path: str) -> str:
    outdir = os.path.join(OUT, os.path.splitext(os.path.basename(path))[0])
    try:
        table = twincat.read_scope(path)
        sid = os.path.splitext(os.path.basename(path))[0]
        meta, ingest = c1.build_meta(table, sample_id=sid)
        # 与 __main__.run() 同序：write_pack 要回填 sha256，且 sample_id 必须在 compute 之前进 ingest
        pack = c1.write_pack(meta, ingest, outdir)
        ingest["sample_id"] = sid
        ingest["sha256"] = pack["sha256"]
        feats = features.compute(meta, ingest, outdir)
        diag = engine.analyze(feats, meta=meta, source_tier=meta["source"]["tier"],
                              case_id=sid)
        return (f"OK    fs={meta['sample_rate_hz']:g}Hz "
                f"n_samples={meta['quality']['n_samples']} "
                f"channels={len(meta['present_channels'])} "
                f"primary={diag['verdict']['primary']} "
                f"blocked={len(feats['freq_limits']['blocked_rules'])} "
                f"unavailable={len(feats['unavailable'])}")
    except Exception as exc:  # noqa: BLE001
        tb = traceback.extract_tb(sys.exc_info()[2])
        where = ""
        for frame in reversed(tb):
            if "axiscope" in frame.filename:
                where = f"{os.path.basename(frame.filename)}:{frame.lineno} {frame.name}"
                break
        return f"FAIL  {type(exc).__name__} @ {where}: {str(exc).splitlines()[0][:120]}"


def main() -> int:
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    os.chdir(root)
    os.makedirs(OUT, exist_ok=True)
    print(f"探针：本地导出方言 × 现有解析器（{len(CANDIDATES)} 份）")
    print("=" * 78)
    for label, path in CANDIDATES:
        exists = os.path.exists(path)
        print(f"\n[{label}]")
        print(f"  路径   {path}" + ("" if exists else "   ← 文件不存在"))
        if not exists:
            continue
        print(f"  大小   {os.path.getsize(path):,} B")
        with open(path, "rb") as fh:
            head = fh.readline()[:160]
        print(f"  首行   {head!r}")
        print(f"  read_scope  {probe_read(path)}")
        print(f"  端到端      {probe_full(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
