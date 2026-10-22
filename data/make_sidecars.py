"""生成缺失的 `.source.txt` 侧车。

纪律（KB0 §6 / A-67）：**不编造 DOI、标题、文件名、采样率或任何数值**。
- DOI/标题/作者/许可：来自 `build/darus_provenance.json`（本会话 2026-10-21 现场
  GET DaRUS API 的实测落盘），本脚本只搬运，不自己写。
- md5/大小/行数/列数/表头：一律现算现打，不接受人工填入。
- 核不出来的，字段写「未核」并写清已试过什么，不猜。

用法：PYTHONIOENCODING=utf-8 python data/make_sidecars.py [--dry]
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROV = os.path.join(ROOT, "build", "darus_provenance.json")
RETRIEVED = "2026-10-21"

TEXTLIKE = {".csv", ".tab", ".txt", ".md", ".json", ".xml", ".head", ".tsv"}

# 相对路径 → (DOI 或 None, 该文件在本项目里的角色)
# 归组依据：文件名数字前缀与已现场核过的 DOI 一一对应；README 类文件按**内容**归组
# （3152_Readme.md 的正文自称 darus-3109，故归 3109，不按文件名归 3152）。
MANIFEST: dict[str, tuple[str | None, str]] = {
    "data/incoming/2563_LDD_Transfer_function_Force_controlled.csv":
        ("10.18419/darus-2563", "波形导出（分号 + 欧洲小数逗号方言，见 data/probe_dialects.py D5）"),
    "data/incoming/2563_Readme.md":
        ("10.18419/darus-2563", "上游 README（未解析）"),
    "data/incoming/3003_Readme.md":
        ("10.18419/darus-3003", "上游 README（未解析）"),
    "data/incoming/3152_Readme.md":
        ("10.18419/darus-3109", "上游 README。⚠️ 文件名前缀是 3152，正文自称 darus-3109 "
                               "「PI velocity controllers comparison」；已按内容归 3109。"
                               "DARUS-3152 是另一数据集（Validation data for comparison of "
                               "SMC-PI controllers vs. P-PI controller），本文件不属于它"),
    "data/incoming/3252_parameters_dist.txt":
        ("10.18419/darus-3252", "上游参数文件（未解析）"),
    "data/incoming/current-hunt/3292_PRBS.mat":
        ("10.18419/darus-3292", "PRBS 激励实验 .mat（本项目无 .mat 读取器，未解析）"),
    "data/incoming/current-hunt/3292_vel_sweep_s_0_dir_pos.mat":
        ("10.18419/darus-3292", "速度扫描 .mat（未解析）"),
    "data/incoming/current-hunt/3292_params.txt":
        ("10.18419/darus-3292", "上游参数文件（未解析）"),
    "data/incoming/current-hunt/3292_Readme.md":
        ("10.18419/darus-3292", "上游 README（未解析）"),
    "data/incoming/current-hunt/3759_Fig4_Path_errors.head":
        ("10.18419/darus-3759", "同名 .tab 的表头片段（未解析）"),
    "data/incoming/current-hunt/3900_baseline_control.head":
        ("10.18419/darus-3900", "baseline 对照数据的表头片段（未解析）"),
    "data/incoming/current-hunt/3900_const_vel_110.head":
        ("10.18419/darus-3900", "同名 .tab 的表头片段（未解析）"),
    "data/incoming/current-hunt/3900_const_vel_110.tab":
        ("10.18419/darus-3900", "波形导出（TAB + ISO-8601 方言，见 data/probe_dialects.py D3）"),
    "data/incoming/current-hunt/4075_experiment_apc.csv":
        ("10.18419/darus-4075", "自适应预载控制实验数据（未解析）"),
    "data/incoming/current-hunt/4075_experiment_std.csv":
        ("10.18419/darus-4075", "标准预载对照数据（未解析）"),
    "data/incoming/current-hunt/4152_Bridge_0_descriptor.txt":
        ("10.18419/darus-4152", "Bridge_0 实验的列描述行（未解析）"),
    "data/incoming/current-hunt/4152_Sine_0_descriptor.txt":
        ("10.18419/darus-4152", "Sine_0 实验的列描述行（未解析）"),
    "data/incoming/current-hunt/4152_README.md":
        ("10.18419/darus-4152", "上游 README（未解析）"),
    "data/incoming/current-hunt/5160_Fig6_Path_errors.head":
        ("10.18419/darus-5160", "同名 .tab 的表头片段（未解析）"),
    "data/incoming/current-hunt/5160_Fig6_Path_errors.tab":
        ("10.18419/darus-5160", "路径误差波形（未解析）"),
    "data/incoming/current-hunt/6333_figure3_data.head":
        ("10.18419/darus-6333", "同名 .tab 的表头片段（未解析）"),
    "data/incoming/current-hunt/6333_figure3_data.tab":
        ("10.18419/darus-6333", "图 3 数据（未解析）"),
    "data/incoming/393964_Export34_LdaFric_RW.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 393964，按编号归 5171）"),
    "data/incoming/394008_Export10_CDD_RW.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 394008，是 data/raw/DD_head.csv 的母本）"),
    "data/incoming/394085_CableActuatorTestRig.xml":
        ("10.18419/darus-5171", "试验台驱动配置 XML（dataFile 394085）"),
    "data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_RW_Export_3_id394119.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 394119）"),
    "data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_RW_Export_5_id394141.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 394141）"),
    "data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_UW_Export_5_id393961.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 393961）"),
    "data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_UW_Export_6_id394169.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 394169）"),
    "data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_UW_Export_7_id393966.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 393966）"),
    "data/incoming/darus5171/CDD_2024-07-23_LdaFricIdent_UW_Export_9_id394009.csv":
        ("10.18419/darus-5171", "TwinCAT 导出（dataFile 394009）"),
    "data/incoming/daRUS5171_listing_2026-10-20.json":
        ("10.18419/darus-5171", "本项目 2026-10-20 现场 GET 的 DaRUS 文件清单快照（非上游文件）"),
    "data/incoming/KUKA_readme.md":
        (None, "Zenodo 21456277 的 README；KB7 已登记该 DOI，本仓未再现场复核"),
    "data/incoming/KUKA_payload_dataset.zip":
        (None, "Zenodo 21456277 母包；KB7 已登记，本仓未再现场复核"),
    "data/incoming/wiredrawing_README.md":
        (None, "Zenodo 21526135；KB7 已登记且已判 dt_jitter_ratio=192.9 硬拒不接入"),
    "data/incoming/wiredrawing_dataset.xlsx":
        (None, "Zenodo 21526135；KB7 已登记且已判硬拒不接入"),
    "data/incoming/current-hunt/zen3929384_documentation.pdf":
        (None, "来源未登记。文件名暗示 Zenodo 3929384，但 PDF 内嵌 Title 逐字为 "
               "「Microsoft PowerPoint - Umrechnung.pptx」、Producer 为 "
               "「Microsoft: Print To PDF」，是德语换算讲义，与伺服波形无关；"
               "本仓未核到 3929384 对应记录，不据文件名断言 DOI"),
    "data/incoming/17622448_README.txt":
        (None, "来源未登记。内容逐字是上游 404 响应 "
               "{\"status\": 404, \"message\": \"Record '17622448' has no file 'README.md'.\"}，"
               "是本项目早前取 README 失败的留存，不是数据集内容"),
    "data/incoming/17622448_metadata.txt":
        (None, "来源未登记。元数据逐字题名「Industrial Machine Condition Monitoring Dataset」，"
               "作者 Roni Prasetyo / Elora Manuella Amei / Salmaa Rihhadatul ’Aisy / "
               "Aldian Nurcahyo（Supervisor）；本仓未核到 record 17622448 的正式 DOI，不据编号猜"),
    "data/incoming/17622448_dataset.csv":
        (None, "来源未登记。表结构与 17622448_metadata.txt 所述的预测性维护表一致"
               "（Timestamp/MachineCode/OT/DT/NoF/…），但非伺服波形"),
    "data/incoming/17622448_head.csv":
        (None, "来源未登记。上一份的前若干行"),
    "data/incoming/generator_data0001.csv":
        (None, "来源未登记。无表头 9 列小数值，表名含 generator，疑为仿真器中间产物；"
               "本仓无任何 README/清单指向它，来源不可考"),
}


def _delim(line: str) -> str:
    """按出现最多的分隔符判定方言：TAB 文件按逗号切只会得到 1 格。"""
    return max(("\t", ",", ";"), key=line.count)


def probe(path: str) -> dict:
    full = os.path.join(ROOT, path)
    raw = open(full, "rb").read()
    out = {"md5": hashlib.md5(raw).hexdigest(), "size": len(raw)}
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXTLIKE:
        try:
            text = raw.decode("utf-8-sig")
            lines = text.splitlines()
            out["n_lines"] = len(lines)
            if lines:
                out["header"] = lines[0][:400]
                sep = _delim(lines[0])
                out["sep"] = {"\t": "TAB", ",": "半角逗号", ";": "分号"}[sep]
                out["n_header_cols"] = len(lines[0].split(sep))
            out["bom"] = raw[:3] == b"\xef\xbb\xbf"
        except UnicodeDecodeError:
            out["n_lines"] = None
    return out


def build(path: str, doi: str | None, role: str, prov: dict) -> str:
    p = probe(path)
    if doi and doi in prov and "error" not in prov[doi]:
        rec = prov[doi]
        doi_line = f"{rec['persistent_id']}（{rec['titles'][0] if rec['titles'] else '标题未取到'}）"
        pub = "; ".join(rec["authors"]) or "未取到"
        lic = f"{rec['license_name']}"
        up = f"DaRUS datasetVersionId {rec['root_id']}（datasetId {rec['dataset_id']}），v{rec['version_number']}，上游共 {rec['n_files']} 个文件"
        ver = (f"{RETRIEVED} 现场 GET https://darus.uni-stuttgart.de/api/datasets/"
               f":persistentId/?persistentId=doi:{doi} → HTTP {rec['http_status']}，"
               f"status={rec['status']}，files={rec['n_files']}（落盘 build/darus_provenance.json）")
    else:
        doi_line = "未核（本仓未核到该文件的正式标识，不据文件名或编号推断）"
        pub = "未核"
        lic = "未核"
        up = "未核"
        ver = (f"{RETRIEVED} 本会话未能核到该文件的正式标识；"
               f"按 KB0/A-67 不编造 DOI，已在 notes 写明已试过什么")

    lines = [
        ("url", f"https://doi.org/{doi}" if doi else "未核"),
        ("retrieved_at", RETRIEVED),
        ("retrieved_by", "AI 智能体（本次仅做来源登记，未重新下载实体；实体来自更早的获取批次）"),
        ("publisher", pub),
        ("license", lic),
        ("dataset_doi", doi_line),
        ("original_filename", os.path.basename(path) + "（本地同名，未改名）"),
        ("format_family", os.path.splitext(path)[1].lstrip(".") or "无扩展名"),
        ("device_or_software", role),
        ("sampling_rate", "未测（本项目未接入该文件，不报采样率）"),
        ("rows", f"{p['n_lines']} 行（实测含表头；md5 {p['md5']}，{p['size']} B）"
                 if p.get("n_lines") is not None else
                 f"未按行计（二进制/非文本；md5 {p['md5']}，{p['size']} B）"),
        ("channels", f"表头 {p['n_header_cols']} 格（分隔符={p.get('sep')}，BOM={p.get('bom')}）"
                     if p.get("n_header_cols") else "未测"),
        ("variable_semantics", (p.get("header") or "未取到")
                                + ("  ⟨节选前 400 字符⟩" if p.get("header") else "")),
        ("notes", role),
        ("derived_from", "NONE（未做任何格式转换）"),
        ("upstream_id", up),
        ("verified_against", ver),
        ("verified_by", f"self（主智能体 {RETRIEVED} 亲自执行 data/probe_darus_provenance.py "
                        f"与 data/make_sidecars.py）"),
    ]
    w = max(len(k) for k, _ in lines)
    return "".join(f"{k.ljust(w)}: {v}\n" for k, v in lines)


def main() -> int:
    dry = "--dry" in sys.argv
    prov = {}
    if os.path.isfile(PROV):
        prov = json.load(io.open(PROV, encoding="utf-8"))
    written = skipped = 0
    for path, (doi, role) in sorted(MANIFEST.items()):
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            print(f"[miss] {path}")
            skipped += 1
            continue
        side = full + ".source.txt"
        if os.path.isfile(side):
            print(f"[skip] {path} 已有侧车")
            skipped += 1
            continue
        text = build(path, doi, role, prov)
        if dry:
            print(f"[dry ] {path}\n{text}")
        else:
            with io.open(side, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            written += 1
    print(f"[make_sidecars] 写入 {written} / 跳过 {skipped} / 清单 {len(MANIFEST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())