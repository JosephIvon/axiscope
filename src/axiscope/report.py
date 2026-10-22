"""最小 HTML 报告：把「这份数据能回答什么、不能回答什么」写成可读事实。

报告层不是判据层：它只印 C2 已登记的数值 + ingest 实测（后者显式标注为 necessary_context，
不得被引用为规则证据，KB3 §1 首段），以及 C3 引擎已经算好并登记过的字段（第八节）——
本节不重算 ρ、不重算 S(e)、不改变任何排序，措辞上限取自引擎的 <code>audit.tier_ledger</code>。
"""
from __future__ import annotations

import html
import io
import json
import os

CSS = """
:root{--bg:#fbfbfa;--fg:#1c1c1a;--mut:#6b6b66;--line:#e3e3de;--warn:#8a4b12;--no:#7a2e2e}
*{box-sizing:border-box}
body{margin:0;padding:32px 40px;background:var(--bg);color:var(--fg);
font:15px/1.65 -apple-system,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",sans-serif}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:28px 0 8px;
padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:14.5px;margin:20px 0 6px} h4{font-size:13px;margin:14px 0 4px;
color:var(--mut);font-weight:600}
.sub{color:var(--mut);font-size:13px;margin-bottom:20px}
table{border-collapse:collapse;width:100%;margin:8px 0 4px;font-size:13px}
th,td{border:1px solid var(--line);padding:5px 9px;text-align:left;vertical-align:top}
th{background:#f3f3f0;font-weight:600;white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code{font:12.5px/1.5 ui-monospace,Consolas,monospace;background:#f3f3f0;padding:1px 4px;border-radius:3px}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:12px;border:1px solid}
.t-ok{color:#1d5c2f;border-color:#b6d8c1;background:#eef7f1}
.t-no{color:var(--no);border-color:#e0bcbc;background:#fbeeed}
.t-warn{color:var(--warn);border-color:#e2c9a8;background:#fbf2e6}
.note{color:var(--mut);font-size:12.5px;margin:4px 0 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin:10px 0}
.card{border:1px solid var(--line);border-radius:6px;padding:10px 12px;background:#fff}
.card .k{color:var(--mut);font-size:12px} .card .v{font-size:19px;font-variant-numeric:tabular-nums}
ol,ul{margin:6px 0 6px 20px;padding:0} li{margin:3px 0}
footer{margin-top:34px;padding-top:12px;border-top:1px solid var(--line);
color:var(--mut);font-size:12px}
"""


def _e(x) -> str:
    return html.escape(str(x))


def _num(x, unit: str = "") -> str:
    if x is None:
        return '<span class="tag t-no">null</span>'
    if isinstance(x, bool):
        return "是" if x else "否"
    if isinstance(x, float):
        s = f"{x:.6g}"
    else:
        s = f"{x:,}" if isinstance(x, int) else str(x)
    return f"{s}{(' ' + unit) if unit else ''}"


def _rows(head: list[str], body: list[list[str]]) -> str:
    th = "".join(f"<th>{_e(h)}</th>" for h in head)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def _card(k: str, v: str) -> str:
    return f'<div class="card"><div class="k">{_e(k)}</div><div class="v">{v}</div></div>'


def _tier_of(audit: dict, claim_id: str) -> dict:
    for row in audit.get("tier_ledger") or []:
        if row.get("claim_id") == claim_id:
            return row
    return {}


def _safety_strip(safety: dict) -> str:
    def lit(key: str) -> str:
        return f'<code>{key}={_e(str(bool(safety.get(key))).lower())}</code>'

    return ('<h4>安全边界</h4>'
            '<div class="grid">'
            + _card("写入设备", lit("writes_to_device"))
            + _card("人工确认", lit("requires_human_approval"))
            + "</div>"
            + "<ul>" + "".join(f"<li>{_e(h)}</li>"
                               for h in safety.get("hard_blocks") or [])
            + f"<li>{_e(safety.get('disclaimer') or '')}</li></ul>")


def _evidence_table(rows: list[dict]) -> str:
    return _rows(["判据", "值", "算子", "阈值", "n", "n_ref", "conf", "S(e)"],
                 [[f"<code>{_e(e.get('rule_id'))}#{_e(e.get('condition_index'))}</code>"
                   f"<div class=\"note\"><code>{_e(e.get('feature'))}</code></div>",
                   _num(e.get("value")), _e(e.get("operator")), _num(e.get("threshold")),
                   _num(e.get("n")), _num(e.get("n_ref")), _num(e.get("conf")),
                   _num(e.get("strength"))] for e in rows])


def diagnosis_section(diag: dict) -> list[str]:
    """第八节：C3 归因输出。只印引擎已登记字段，措辞不得高于 <code>tier_ledger</code> 的上限。"""
    parts: list[str] = []
    A = parts.append
    verdict = diag.get("verdict") or {}
    hyps = diag.get("hypotheses") or []
    diff = diag.get("differential") or {}
    audit = diag.get("audit") or {}
    safety = diag.get("safety") or {}
    by_id = {h.get("id"): h for h in hyps}
    primary = by_id.get(verdict.get("primary"))

    A("<h2>八、C3 归因：假设排序与置信度</h2>")
    A(f'<p class="note">契约 <code>{_e(diag.get("schema"))}</code> · 引擎 v{_e(diag.get("engine_version"))}'
      f' · 用例 <code>{_e(diag.get("case_id"))}</code> · '
      f"命中规则 {_e('、'.join(audit.get('rules_fired') or []) or '（无）')}</p>")

    vt = _tier_of(audit, "verdict.summary")
    A('<div class="grid">')
    A(_card("主假设", f"<code>{_e(verdict.get('primary') or '（无）')}</code>"
                      + (f"<br><span class=\"note\">{_e(primary.get('display_name'))}</span>" if primary else "")))
    A(_card("overall_confidence", _num(verdict.get("overall_confidence"))))
    A(_card("严重度", f"S{primary['severity']}" if primary else "—"))
    A(_card("本条结论的措辞上限", _e(vt.get("wording_ceiling") or "—")))
    A("</div>")

    if hyps:
        A(f"<p>{_e(verdict.get('summary') or '')}</p>")
        A(f'<p class="note">{_e(verdict.get("confidence_note") or "")}</p>')
    else:
        A("<p><strong>本轮零条假设可评分。</strong>这不是「没有问题」，而是「不可判定」——"
          "每条规则的支持证据都需要 KB4 §2.1 的原始输入（样本量、频带、事件上下文），"
          "本样本能同时凑齐 ≥2 条的叶为零。缺席原因逐条见下表与第六节。</p>")

    A(_rows(["排名", "假设", "fault_mode", "严重度", "C", "支持证据", "反证扣分", "证据等级"],
            [[_num(h.get("rank")), f"<code>{_e(h.get('id'))}</code> {_e(h.get('display_name') or '')}",
              f"<code>{_e(h.get('fault_mode'))}</code>", f"S{_e(h.get('severity'))}",
              _num(h.get("confidence")),
              f"{len(h.get('supporting_evidence') or [])} 条",
              f"{len(h.get('contradicting_evidence') or [])} 条 / "
              f"Σv={round(sum(r.get('penalty') or 0 for r in h.get('contradicting_evidence') or []), 2)}",
              _e(_tier_of(audit, h.get("id")).get("source_tier") or "—")]
             for h in hyps]
            or [["—", "（无可评分假设）", "—", "—", "—", "0 条", "0 条", "—"]]))
    A('<p class="note">排名口径为 KB4 §2.9 字典序 (severity, C, …)，S0 最紧急 ⟹ 严重度编号越小排越前。'
      "「反证扣分」为 KB4 §2.4 的 v_j 之和（封顶 0.5），"
      "<em>门禁条件不计入 A_sup</em>（§2.7 反自证条款）。</p>")

    for h in hyps:
        tier = _tier_of(audit, h.get("id"))
        A(f"<h3>{_e(h.get('rank'))}. {_e(h.get('display_name') or h.get('fault_mode'))} "
          f"（<code>{_e(h.get('id'))}</code> · C={_num(h.get('confidence'))} · "
          f"S{_e(h.get('severity'))} · {_e(tier.get('source_tier') or '—')}）</h3>")
        A("<h4>支持证据（KB4 §2.1 逐格原始输入）</h4>")
        A(_evidence_table(h.get("supporting_evidence") or []))
        A('<p class="note">S(e) = g(ρ)·conf·n_factor·band_factor 由上表左列独立复算得出，'
          "报告层不重算、只印引擎写下的值；校验器 <code>C3-R15-*</code> 会拿这些原始字段反向核对 S(e)。</p>")
        refuters = h.get("contradicting_evidence") or []
        A("<h4>反证</h4>")
        A(_rows(["规则", "判据", "值", "阈值", "ρ′", "v_j"],
                [[f"<code>{_e(r.get('rule_id'))}</code>", f"<code>{_e(r.get('feature'))}</code>",
                  _num(r.get("value")), _num(r.get("threshold")), _num(r.get("rho_prime")),
                  _num(r.get("penalty"))] for r in refuters]
                or [["(无)", "—", "—", "—", "—", "0.00"]]))
        rec = h.get("recommendation") or {}
        eff = rec.get("expected_effect") or {}
        A("<h4>建议与依据</h4>")
        A(_rows(["项", "内容"], [
            ["动作", f"<code>{_e(rec.get('action_id'))}</code> {_e(rec.get('action') or '')}"],
            ["预期效果口径", f"<code>{_e(eff.get('basis'))}</code> — {_e(eff.get('direction') or '')}"],
            ["须人工确认", _num(rec.get("requires_human_approval"))],
            ["可逆", _num(rec.get("reversible"))],
        ]))
        A('<p class="note">C4 仿真未实现 ⟹ <code>expected_effect.basis</code> 只能是 '
          "<code>rule_heuristic</code>，本节不给改进百分比、不给参数值（A-64）。</p>")
        ndc = h.get("next_data_to_collect") or []
        if ndc:
            A("<h4>补什么数据</h4>")
            A(_rows(["要补的观测", "为什么", "解锁什么"],
                    [[_e(r.get("ask")), _e(r.get("why")), _e(r.get("unlocks"))] for r in ndc]))

    A("<h3>差分诊断：考虑过什么、什么算不了</h3>")
    considered = diff.get("considered") or []
    A(f"<p>考虑过的叶：{_e('、'.join(considered) or '（无）')}。</p>")
    ne = diff.get("not_evaluable") or []
    A(_rows(["故障模式 / 族", "blocked_by", "为什么不可评估"],
            [[f"<code>{_e(r.get('fault_mode') or r.get('family'))}</code>",
              f"<code>{_e(r.get('blocked_by'))}</code>", _e(r.get("why"))] for r in ne]
            or [["(无)", "—", "—"]]))
    A('<p class="note"><code>blocked_by</code> 只能取 KB0/C3 规则 16 的稳定键名；'
      "把「不可观测」写成「没有」是 C2 规则 7 / R-25 明令禁止的越界表述。</p>")

    ua = diag.get("unavailable") or []
    if ua:
        A("<h4>诊断侧登记的不可算特征</h4>")
        A(_rows(["特征路径", "原因"],
                [[f"<code>{_e(r.get('feature'))}</code>", _e(r.get("reason"))] for r in ua]))

    A("<h3>审计留痕</h3>")
    A(_rows(["类别", "内容"], [
        ["跳过的规则", "<br>".join(f"<code>{_e(s.get('rule_id'))}</code> — {_e(s.get('reason'))}"
                                   for s in audit.get("rules_skipped") or []) or "（无）"],
        ["显式假设", "<br>".join(f"<code>{_e(a.get('anchor'))}</code> — {_e(a.get('statement'))}"
                                for a in audit.get("assumptions") or []) or "（无）"],
        ["仲裁记录", "<br>".join(_e(n) for n in audit.get("arbitration_notes") or []) or "（无）"],
        ["外部引用计数", f"verified={_num(audit.get('external_counts', {}).get('verified'))} / "
                       f"total={_num(audit.get('external_counts', {}).get('total'))}"
                       "<div class=\"note\">verified_by ≠ self 不计入 k（KB4 §2.8）</div>"],
    ]))

    checks = diag.get("contract_checks") or []
    if checks:
        bad = [c for c in checks if not c.get("passed")]
        A("<h4>C3 契约校验（非契约字段，随报告附于 <code>diagnosis.json</code>）</h4>")
        A(f'<p><span class="tag {"t-ok" if not bad else "t-no"}">'
          f"{len(checks) - len(bad)}/{len(checks)} 通过</span>"
          f"{'；逐条结果见 <code>diagnosis.json</code> 的 <code>contract_checks</code>。' if not bad else ''}</p>")
        if bad:
            A(_rows(["检查项", "内容"],
                    [[f"<code>{_e(c.get('check_id'))}</code>", _e(c.get("detail"))] for c in bad]))

    A(_safety_strip(safety))
    return parts


def render(meta: dict, feats: dict, ingest: dict, checks: list[tuple[str, bool, str]],
           diag: dict | None = None) -> str:
    q = meta["quality"]
    tb = meta["time_bases"][0]
    fl = feats["freq_limits"]
    cite = meta["provenance"]["citation"]
    gate = meta["provenance"]["trigger_gate"]
    sb = feats["spectral"].get("vel_fb", {})
    parts: list[str] = []
    A = parts.append

    A(f"<h1>样本诊断报告 · {_e(meta['source']['original_filename'])}</h1>")
    A(f"<div class=\"sub\">C1 样本包 <code>{_e(feats['ref']['sample_id'])}</code> · "
      f"证据等级 {_e(meta['source']['tier'])} · sha256 <code>{_e(feats['ref']['sha256'][:16])}…</code> · "
      f"本报告只做离线分析与建议，<code>writes_to_device=false</code>、"
      f"<code>requires_human_approval=true</code></div>")

    A("<h2>一、这份数据是什么</h2>")
    A('<div class="grid">')
    A(_card("厂商 / 型号", f"{_e(meta['source']['vendor'])}<br><span class=\"note\">"
                          f"{_e(meta['source']['drive_model'])}</span>"))
    A(_card("采样率", _num(meta["sample_rate_hz"], "Hz")))
    A(_card("有效时长", _num(q["n_samples"] / meta["sample_rate_hz"], "s")))
    A(_card("时基抖动比", _num(q["dt_jitter_ratio"])))
    A(_card("奈奎斯特 / 可靠带", f"{_num(fl['nyquist_hz'], 'Hz')} / "
                                f"{_num(fl['reliable_band_hz'], 'Hz')}"))
    A(_card("NaN 占比", _num(q["nan_ratio"])))
    A("</div>")
    A(_rows(["项", "值", "说明"], [
        ["单位基准", f"<code>{_e(meta['units_are'])}</code>",
         "源数据即 SI（m / m·s⁻¹ / N·m），无编码器 counts 刻度 ⟹ 全部 <code>*_counts</code> 路径无来源，"
         "本报告不折算、不臆造 µm 级数字（C1 单位规则 / KB3 纪律 4）"],
        ["触发门控", f"<code>{_e(gate['channel'])}</code> 保留 {gate['rows_kept']:,} / "
                     f"{meta['provenance']['n_rows_raw']:,} 行",
         f"门控区间行号 {gate['rows_used'][0]}–{gate['rows_used'][1]}，共 {gate['n_episodes']} 段；"
         "未过滤会把 3.7 倍于有效的行算进 RMS 与频谱（KB3 纪律 8）"],
        ["表头行数", _num(meta["provenance"]["header_rows"]), "数据自其下一行起"],
        ["行形状不符丢弃", _num(meta["provenance"]["n_rows_shape_mismatch"]), "KB2 §二坑 4"],
        ["署名", f"{_e(cite['author'])}", f"DOI <code>{_e(cite['doi'])}</code> · "
                                          f"许可 {_e(cite['license'])}（{_e(cite['note'])}）"],
    ]))

    A("<h2>二、频带门禁：哪些判据在采样率面前不存在</h2>")
    A(f"<p>{_e(fl['reason'])}</p>")
    gate_reason = {(r.get("rule"), r.get("branch")): r["reason"] for r in feats["unavailable"]
                   if r.get("rule")}
    A(_rows(["被阻塞的规则 / 支路", "原因"],
            [[f"<code>{_e(b)}</code>",
              _e(gate_reason.get(tuple(b.split("#")) if "#" in b else (b, None),
                                 "见 features.unavailable"))]
             for b in fl["blocked_rules"]]))
    A('<p class="note">被阻塞的判据只能写「不可观测」。'
      '把「看不见」写成「没有」（如"未检出机械谐振"）是本项目明令禁止的越界表述（C2 规则 7 / R-25）。</p>')

    A("<h2>三、通道能力矩阵</h2>")
    rows = []
    for name, c in meta["channels"].items():
        rows.append([f"<span class=\"tag t-ok\">mapped</span> <code>{_e(name)}</code>",
                     f"<code>{_e(c['raw_column'])}</code>", _e(c["unit"]), _num(c["confidence"]),
                     f"{_e(c['basis'])}<div class=\"note\">{_e(c['note'])}</div>"])
    for name, c in meta["extra_channels"].items():
        rows.append([f"<span class=\"tag t-warn\">unmapped</span> <code>{_e(name)}</code>",
                     f"<code>{_e(c['raw_column'])}</code>", _e(c["native_unit"]), "—",
                     _e(c["note"])])
    A(_rows(["角色 / canonical", "原始列", "单位", "confidence", "依据与理由"], rows))
    A(f"<p class=\"note\">映射 {len(meta['channels'])} 列 + 未映射 {len(meta['extra_channels'])} 列 = "
      f"{len(meta['channels']) + len(meta['extra_channels'])} 列 = 表头列数（KB2 §3.6："
      "既不丢弃也不猜语义）。厂商布尔列（<code>bMovingForward</code> / <code>bTrigger_*</code>）"
      "是解析器内部输入，不进 <code>waveform.tsv</code>（C1 通道词表注 / A-7）。</p>")

    A("<h2>四、实测发现（ingest 层，非 C2 特征）</h2>")
    A('<p class="note">以下数字在接入时实测得到，按 KB3 §1 首段只能作 '
      "<code>necessary_context</code> 出现在叙述里，<strong>不得</strong>被规则引擎引作 "
      "<code>supporting_evidence[].feature</code>——同一批数值现已按 C2 规则 16 进 "
      "<code>sensor_disagreement.pairs[]</code>（携带单位与原点常偏），规则层从此可见"
      "（A-98 ④：只留叙述等于让规则引擎看不见「哪个传感器在说话」）。</p>")
    A("<h3>4.1 多套位置测量的分歧（幅值已扣原点常偏）</h3>")
    A(_rows(["通道 A", "通道 B", "原理 A × 原理 B", "有差异行数", "原点常偏 (m)",
             "分歧 RMS (m)", "分歧峰值 (m)", "corr(原始值)", "方向"],
            [[f"<code>{_e(p['a'])}</code>", f"<code>{_e(p['b'])}</code>",
              _e("%s × %s" % (p["a_principle"] or "未登记", p["b_principle"] or "未登记")),
              f"{p['n_rows_differ']:,}", _num(p["datum_offset"], "m"),
              _num(p["rms"], "m"), _num(p["max_abs"], "m"),
              _num(p["corr"]), _e(p["direction"])] for p in ingest["pairs"]]))
    worst = max(ingest["pairs"], key=lambda p: abs(p["datum_offset"]))
    A('<p class="note">分歧本身是证据，不得择一当真理（C1 <code>cross_validation.note</code> / A-6）。'
      "RMS/峰值定义在 <code>resid = (a−b) − mean(a−b)</code> 上，表中「原点常偏」列即 "
      f"<code>mean(a−b)</code>：本样本原点常偏最大的一对是 <code>{_e(worst['a'])}</code> ↔ "
      f"<code>{_e(worst['b'])}</code>，常偏 {_num(worst['datum_offset'])} m 而残差 RMS 只有 "
      f"{_num(worst['rms'])} m，相差约 {abs(worst['datum_offset']) / worst['rms']:.3g} 倍——"
      "不减掉常数项就会把安装原点读成分歧（C2 规则 16 / A-106）。"
      "<code>corr</code> 在原始值上算（平移不改变相关系数）。原理一栏任一为「未登记」的对"
      "不计入 <code>second_feedback_available</code>（A-98 ②）。</p>")
    if ingest.get("sign_check"):
        A(f"<h3>4.2 速度通道符号一致性</h3><p>{_e(ingest['sign_check'])}</p>")
    if ingest.get("masquerade"):
        A("<h3>4.3 指令列与其同名反馈列的逐行比对（A-98 ③ 的冒充支）</h3>")
        A(_rows(["指令列", "同名反馈列", "比对行数", "有差异行数", "结论"],
                [[f"<code>{_e(m['cmd'])}</code>", f"<code>{_e(m['fb'])}</code>",
                  f"{m['n_rows']:,}", f"{m['n_rows_differ']:,}",
                  "逐行全等 ⟹ 二者非独立测量" if m["n_rows_differ"] == 0
                  else "有差异，未触发冒充支"] for m in ingest["masquerade"]]))
        A('<p class="note"><code>feedback_integrity.masquerade_suspected</code> 由本表驱动，'
          "不是 KB2 §4.10 样本卡注释的转述。全等孪生列都不在 4.1 的互证对里，"
          "列间恒等式的接入层核对见 4.4（A-105 已落）。</p>")
    identity = ingest.get("identity") or {}
    if identity.get("performed"):
        A("<h3>4.4 列间恒等式核对：哪些列不是第二次测量（A-105 ①③）</h3>")
        A(_rows(["判为派生的列（方向来自文档声明，不是数据）", "恒等式（行级最大残差 / 容差）", "声明来源"],
                [[f"<code>{_e(d['column'])}</code>",
                  "≡ %s，常数项 γ = %.3g；行级最大残差 %.3g、容差 %.3g（均为该列原生单位）" % (
                      " ".join("%+.4g·%s" % (c, _e(b))
                               for c, b in zip(d["coefficients"], d["basis"])),
                      d["gamma"], d["max_abs_residual"], d["tolerance"]),
                  _e(d["declared_by"])] for d in identity["derived"]]))
        A(_rows(["逐行全等的两列", "保留 / 丢弃", "比对行数"],
                [[f"<code>{_e(a)}</code> ↔ <code>{_e(b)}</code>",
                  "保留 <code>%s</code>，丢弃 <code>%s</code>" % (
                      _e(b if a in identity["duplicate_dropped"] else a),
                      _e(a if a in identity["duplicate_dropped"] else b)),
                  f"{identity['n_rows_checked']:,}"]
                 for a, b in identity["duplicates"]]))
        for rel in [f for f in ingest["findings"]
                    if f["kind"] == "linear_dependency_unattributed"]:
            A(f"<p class='note'>未归因的线性约束：{'、'.join('<code>%s</code>' % _e(c) for c in rel['columns'])}"
              f" 之间确有定系数关系（最小行级残差 {_num(rel['min_max_abs_residual'])}，"
              f"单位为这些列各自的原生刻度），但"
              f"{_e(rel['reason'])}——同一条恒等式有三个书写方向，数据本身分不出谁是算出来的，"
              "指认方向需要文档声明（<code>mapping.DECLARED_COMPUTED</code>）。"
              "它仍按一条独立约束扣自由度，不给任何一列贴派生标签（A-105 ①）。</p>")
        n_pos_derived = sum(1 for d in identity["derived"] if d["column"].startswith("dPosition"))
        n_pos_twin = sum(1 for c in identity["duplicate_dropped"] if c.startswith("dPosition"))
        A(f"<p class='note'>常数列 {len(identity['constants'])} 条（"
          f"{_e('、'.join(identity['constants']))}）既不是测量也不是派生列，同样不计入独立性。"
          f"位置列 {len(identity['position_columns_seen'])} 条，扣派生 {n_pos_derived} 条、"
          f"扣全等孪生的丢弃侧 {n_pos_twin} 条、扣未归因线性约束 "
          f"{identity['n_unattributed_among_position']} 条 ⟹ 独立位置测量 "
          f"{identity['n_independent_position']} 条"
          f"（{_e('、'.join(identity['independent_position_columns']))}）。计数落在 "
          f"<code>meta.audit.identity_check.n_independent_position</code> = "
          f"{identity['n_independent_position']}，C2 的 <code>feedback_integrity.identity_check</code> "
          "是它的镜像；<code>second_feedback_available</code> 与 4.1 的分歧对都在这个集合之后才数"
          "（A-105 ②③⑤）。核对没跑成时该字段为 null，相关判据按 "
          "<code>blocked_by = derived_column_unchecked</code> 不可评估。</p>")

    A("<h2>五、算出来的 C2 特征</h2>")
    rows = [["<code>spectral.vel_fb.dominant_freq_hz</code>", _num(sb.get("dominant_freq_hz"), "Hz"),
             f"在 [{max(2 * feats['resonance']['resolution_hz'], 1.0):.3g}, "
             f"{fl['reliable_band_hz']:.6g}] Hz 内取 PSD 极大（Welch / hann / "
             f"nperseg={feats['resonance']['estimation']['nperseg']}，"
             f"Δf={feats['resonance']['resolution_hz']:.6g} Hz）"]]
    rows.append(["<code>spectral.vel_fb.dominant_psd_ratio</code>",
                 _num(sb.get("dominant_psd_ratio")), "主峰带内能量 / 带内总能量，∈[0,1]"])
    rows.append(["<code>spectral.vel_fb.tonality_index</code>",
                 _num(sb.get("tonality_index")), "1 − 谱平坦度；≈1 纯音、≈0 白噪声"])
    for p in feats["sensor_disagreement"]["pairs"]:
        rows.append([f"<code>sensor_disagreement.pairs[{_e(p['a'])}|{_e(p['b'])}]"
                     f".rms_counts / .max_counts</code>",
                     "%s / %s %s" % (_num(p["rms_counts"]), _num(p["max_counts"]),
                                     _e(p["unit"])),
                     "在 resid = (a−b) − mean(a−b) 上算，常偏另记 <code>datum_offset</code> = "
                     f"{_num(p['datum_offset'])} {_e(p['unit'])}（C2 规则 16 / A-106）；"
                     "后缀 counts 是历史名，单位随行（A-97 ③）"])
    rows.append(["<code>feedback_integrity.second_feedback_available</code>",
                 _num(feats["feedback_integrity"]["second_feedback_available"]),
                 "由「至少一对分属不同物理原理」推出（A-98 ②），不再由 C1 "
                 "<code>cross_validation.pairs</code> 非空直接推——同原理的两列分歧不算第二次独立测量"])
    rows.append(["<code>feedback_integrity.masquerade_suspected</code>",
                 _num(feats["feedback_integrity"]["masquerade_suspected"]),
                 "接入层逐行实测指令候选与反馈候选的行数差（A-98 ③）：本样本 "
                 "<code>dPosition_test_tar</code> 与 <code>dPosition_test</code> 全等 ⟹ "
                 "「指令轨与候选反馈逐行全等，二者非独立测量」"])
    A(_rows(["特征路径", "值", "口径"], rows))
    seg_rows = [[f"<code>{_e(s['kind'])}</code> #{s['id']}",
                 _num(s["t0"], "s"), _num(s["t1"], "s"), _e(s.get("note") or "")]
                for s in meta["segments"]]
    A(_rows(["分段 kind", "t0", "t1", "判据"], seg_rows or [["(无)", "", "", ""]]))

    A("<h2>六、算不了什么（结构化事实，不是遗漏）</h2>")
    A(f"<p>共 {len(feats['unavailable'])} 条。每条都指向具体缺口，"
      "而不是「没检出」——两者在证据强度上完全不同（C2 规则 2）。</p>")
    ua = sorted(feats["unavailable"], key=lambda r: (r.get("rule") or "~", r["feature"]))
    A(_rows(["规则/支路", "特征路径", "原因"],
            [[(f"<code>{_e(r['rule'])}</code>" + (f"<br><code>{_e(r['branch'])}</code>" if r.get("branch") else ""))
              if r.get("rule") else '<span class="tag t-no">通道/单位缺失</span>',
              f"<code>{_e(r['feature'])}</code>", _e(r["reason"])] for r in ua]))

    A("<h2>七、端到端断言自检</h2>")
    A(_rows(["断言", "结果", "内容"],
            [[_e(name), f'<span class="tag {"t-ok" if ok else "t-no"}">{"PASS" if ok else "FAIL"}</span>',
              _e(detail)] for name, ok, detail in checks]))

    if diag is not None:
        for fragment in diagnosis_section(diag):
            A(fragment)
        limit_head = "九"
    else:
        limit_head = "八"

    A(f"<h2>{limit_head}、必须随报告一起读的限定</h2>")
    A("<ul>")
    A("<li><strong>线缆试验台 ≠ 半导体产线。</strong>本样本来自 DaRUS 公开试验数据集，"
      "本仓无该设备现场/产线验证，叙述措辞不得高于 <code>T1-a 实测</code>。</li>")
    if diag is None:
        A("<li><strong>本次不做故障归因。</strong>规则引擎（C3）未接入；本报告只给「能算什么」与"
          "「不能算什么」，任何诊断结论都还没有产生。</li>")
    else:
        A("<li><strong>归因是离线建议，不是下发。</strong>第八节的假设与置信度由 C3 规则引擎产出，"
          "<code>safety.writes_to_device = false</code>、<code>requires_human_approval = true</code>；"
          "改进量没有仿真验证记录，因此只给方向、不给百分比。</li>")
    A("<li><strong>触发门控改变样本构成。</strong>门控后仅 5.000 s 单一恒速段，"
      "样本不代表整段试验（未过滤会多算 3.7 倍于有效的数据）。</li>")
    A(f"<li><strong>redaction 自检：</strong>包内不含主机路径与 ADS NetID（KB2 §6.3）；"
      f"母本 `data/raw/` 仍是未脱敏工作副本，发布前须按 §6.1 同步脱敏。</li>")
    A("</ul>")
    A(f"<footer>由 axiscope Python 引擎生成 · 契约 C1/C2"
      f"{'/C3' if diag is not None else ''} · 规则库 KB3 R-01…R-30 · "
      f"数据 {cite['license']} · 署名与 DOI 见上表（脱敏不清署名）</footer>")

    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<title>axiscope 样本诊断报告</title>"
            f"<style>{CSS}</style></head><body>" + "\n".join(parts) + "</body></html>")


def write_report(path: str, html_text: str) -> None:
    io.open(path, "w", encoding="utf-8", newline="\n").write(html_text)


def write_features(path: str, feats: dict) -> None:
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(feats, ensure_ascii=False, indent=2) + "\n")