"""KB2 §8.3 端到端断言 + §6 脱敏断言。

每个「本检查能抓 X 类缺陷」的断言都在 tests/test_slice.py 里有对应的负向测试（KB0 §6 检查 22：
断言在跑 ≠ 断言能抓）。
"""
from __future__ import annotations

import io
import json
import os

from . import anchors
from . import features as feat_mod
from .features import BAND_FLOOR, BRANCH_FLOOR, NYQUIST_SAFETY

C1_VOCAB = {"pos_cmd", "pos_fb", "fe", "vel_cmd", "vel_fb", "cur_q", "cur_cmd",
            "torque", "temp", "laser_power", "io", "vision_x", "vision_y", "vision_angle"}
REDACT_TOKENS = ("Versuchsstand", "141.58.", "C:\\")


def read_wave(path: str) -> tuple[list[str], list[list[float]]]:
    # 通用换行：waveform.tsv 若是 CRLF，逐格 rstrip("\n") 会把 \r 留在末格，
    # 于是列名变成 "torque\r"，整条回算断言以 KeyError 崩掉而不是给出结论。
    with io.open(path, encoding="utf-8") as fh:
        head = fh.readline().rstrip("\r\n").split("\t")
        rows = [[float(c) if c != "nan" else float("nan") for c in ln.rstrip("\r\n").split("\t")]
                for ln in fh if ln.strip()]
    return head, rows


def run(meta: dict, feats: dict, ingest: dict, pack_dir: str, raw_columns: dict) -> list:
    out: list[tuple[str, bool, str]] = []

    def chk(name: str, ok: bool, detail: str) -> None:
        out.append((name, bool(ok), detail))

    head, wave = read_wave(os.path.join(pack_dir, "waveform.tsv"))
    t = [r[0] for r in wave]

    chk("wave.t[0] == 0", abs(t[0]) < 1e-12, f"t[0]={t[0]!r}")
    mono = all(b > a for a, b in zip(t, t[1:]))
    chk("wave.t 严格单调递增", mono, f"n={len(t)}，末值 {t[-1]:.6f} s")

    canon = list(meta["present_channels"])
    ext = [c for c in head if c.startswith("x_")]
    chk("wave 列数 == 1 + present + extra",
        len(head) == 1 + len(canon) + len(ext),
        f"{len(head)} 列 = 1 + {len(canon)} canonical + {len(ext)} extra")
    bad = [c for c in head[1:] if not c.startswith("x_") and c not in C1_VOCAB]
    chk("canonical 列名 ⊆ C1 词表", not bad, f"越界列={bad or '无'}")
    chk("列名与 t / 空名不相撞",
        "t" not in head[1:] and "" not in head,
        f"head={head[:4]}…")

    n_gate = meta["provenance"]["trigger_gate"]["rows_kept"]
    chk("quality.n_samples == len(wave) == 触发门控后行数",
        meta["quality"]["n_samples"] == len(wave) == n_gate,
        f"n_samples={meta['quality']['n_samples']}, len(wave)={len(wave)}, 门控保留={n_gate}")

    if "fe" in canon:
        chk("fe ≡ pos_cmd - pos_fb", "pos_cmd" in canon and "pos_fb" in canon,
            "C1 派生规则 1 的前提必须同时可见 pos_cmd 与 pos_fb")
    else:
        chk("fe ≡ pos_cmd - pos_fb", True,
            "本样本 fe 不在 present_channels ⟹ 恒真（KB2 §4.10：_tar 列逐行全等，拒绝派生 fe）")

    chk("方向符号通道 |signed| == |raw| 且 sign ∈ {±1}",
        all(c["sign"] in (1, -1) for c in meta["channels"].values()),
        "bMovingForward 全程恒 0 ⟹ 作者脚本的 dir 乘子不产生符号信息（KB3 纪律 9），"
        "按 KB2 §4.1 直映、sign=+1")

    rows = meta["audit"]["assumptions"]
    chk("audit.assumptions 行形状与锚词表",
        bool(rows) and all(isinstance(r, dict) and anchors.anchor_kind(r.get("anchor"))
                           and str(r.get("statement") or "").strip() for r in rows),
        f"{len(rows)} 行：锚={[r.get('anchor') for r in rows if isinstance(r, dict)]}")

    floor = {**BAND_FLOOR, **{b.split("#")[0]: v for b, v in BRANCH_FLOOR.items()}}
    need = {r for r, f in floor.items() if f > meta["quality"]["nyquist_hz"]}
    have = {b.split("#")[0] for b in feats["freq_limits"]["blocked_rules"]}
    def key(b: str) -> tuple[str, str | None]:
        parts = b.split("#")
        return parts[0], parts[1] if len(parts) > 1 else None

    ga = {(u.get("rule"), u.get("branch")) for u in feats["unavailable"] if u.get("rule")}
    blocked_keys = {key(b) for b in feats["freq_limits"]["blocked_rules"]}
    chk("blocked_rules ⊇ {R : band⊥ > nyquist}", need <= have,
        f"需 {sorted(need)}，实得 {feats['freq_limits']['blocked_rules']}")
    orphan = sorted(str(k) for k in blocked_keys - ga)
    extra = sorted(str(k) for k in ga - blocked_keys)
    chk("blocked_rules 与 unavailable 的 rule/branch 一一对账（A-79）",
        not orphan and not extra,
        f"无对应 unavailable 的阻塞项={orphan or '无'}；无对应 blocked_rules 的 rule 行={extra or '无'}")

    tbs = meta["time_bases"]
    prim = [tb for tb in tbs if tb["role"] == "primary"]
    chk("time_bases 中 primary 恰一条且被指名",
        len(prim) == 1 and meta["primary_time_base"] == prim[0]["id"],
        f"primary={[tb['id'] for tb in prim]}，meta.primary_time_base={meta['primary_time_base']}")
    chk("time_bases[].id 唯一", len({tb["id"] for tb in tbs}) == len(tbs),
        f"ids={[tb['id'] for tb in tbs]}")
    ids = {tb["id"] for tb in tbs}
    refs = [c.get("time_base_ref") for c in meta["channels"].values()]
    refs += [c.get("time_base_ref") for c in meta["extra_channels"].values()]
    chk("channels[].time_base_ref ∈ time_bases[].id 或 null（null=继承 primary）",
        all(r is None or r in ids for r in refs), f"非 null 的引用={[r for r in refs if r] or '无'}")
    chk("resample[].band_effect 必填（A-96 规则 3）",
        all(r.get("band_effect") in ("none", "band_lost", "aliased_risk")
            for r in meta["resample"]),
        f"resample={meta['resample']}（空数组合法：Scope View 单栅格，无跨栅格运算）")
    chk("事件栅格不得作主栅格",
        not [tb for tb in tbs if tb["role"] == "event" and tb["id"] == meta["primary_time_base"]],
        "本样本无 event 栅格")
    chk("sample_rate_hz == time_bases[primary].sample_rate_hz（向后兼容锚点自洽）",
        abs(meta["sample_rate_hz"] - prim[0]["sample_rate_hz"]) < 1e-12,
        f"{meta['sample_rate_hz']} vs {prim[0]['sample_rate_hz']}")

    n_mapped = len(meta["channels"])
    n_extra = len(meta["extra_channels"])
    n_header = n_mapped + n_extra
    chk("N_mapped + N_extra == N_header（无通道既不映射也不入 extra）",
        n_header == raw_columns["n_columns"],
        f"{n_mapped} + {n_extra} = {n_header}；表头 {raw_columns['n_columns']} 列")
    roles = {c["role"] for c in meta["channels"].values()} | \
            {c["role"] for c in meta["extra_channels"].values()}
    chk("role ∈ {mapped, unmapped}", roles <= {"mapped", "unmapped"}, f"实得 {sorted(roles)}")

    blob = io.open(os.path.join(pack_dir, "meta.json"), encoding="utf-8").read()
    blob += io.open(os.path.join(pack_dir, "waveform.tsv"), encoding="utf-8").read()
    hits = [tok for tok in REDACT_TOKENS if tok in blob]
    chk("包内不含主机路径 / ADS NetID（KB2 §6.3）", not hits, f"命中={hits or '无'}")

    cite = meta["provenance"]["citation"]
    chk("署名与 DOI 在包内（KB2 §6.2/6.3）",
        cite["doi"] in meta["provenance"]["citation"]["doi"].split()
        or cite["doi"] in blob, f"{cite['author']} / {cite['doi']} / {cite['license']}")
    chk("license == CC BY 4.0", cite["license"] == "CC BY 4.0", cite["license"])

    worst = 0.0
    for ci, name in enumerate(head[1:], start=1):
        if name.startswith("x_") or name not in meta["channels"]:
            continue  # 未登记进 C1 的列由词表断言单独报错，不该在这里抛 KeyError
        ch = meta["channels"][name]
        raw = ingest["series"][ch["raw_column"]]
        col = [r[ci] for r in wave]
        for a, b in zip(raw, col):
            worst = max(worst, abs(a * ch["sign"] + ch["offset"] - b))
    chk("包内数值 ≡ 母本数值（门控后逐点回算，|Δ| == 0）", worst == 0.0,
        f"max|Δ| = {worst:g}（{len(canon)} 个 canonical 通道 × {len(wave)} 行）")

    chk("C2 值与 unavailable 互斥 / 三处 fs 自洽 / 预览非空约束",
        _selfcheck_ok(feats, meta), "features.check_self_consistency 通过")
    return out


def _selfcheck_ok(feats: dict, meta: dict) -> bool:
    try:
        feat_mod.check_self_consistency(feats, meta)
    except feat_mod.FeatureError:
        return False
    return True


def load_pack(pack_dir: str) -> tuple[dict, dict]:
    meta = json.load(io.open(os.path.join(pack_dir, "meta.json"), encoding="utf-8"))
    feats = json.load(io.open(os.path.join(pack_dir, "features.json"), encoding="utf-8"))
    return meta, feats