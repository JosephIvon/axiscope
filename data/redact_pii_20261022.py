#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""redact_pii_20261022.py —— KB2 §六 脱敏的一次性执行记录（2026-10-22，收尾清偿 C1）。

规则来源：docs/kb/KB2-waveform-formats.md §6.1（字段级规则）/ §6.3（发布门断言）。
  - 只清除：主机路径（C:\\Versuchsstand\\…）、ADS NetID（`141.58.` 网段上的完整路由标识；
    绝对墙钟时刻（ticks + 德语墙钟 + 侧车导出时刻）。
  - 绝不清除：署名（Reichenbach/Stuttgart）、DOI、许可（CC BY 4.0）、数据数值、
    通道符号名（L10）、Port（851）。
  - 行数保持：全部替换均为等行内替换，不增删行（引用网行号指针不失效）。
执行后验证：python data/probe_pii.py（标识值 token 应为 0）+ pytest 全量。
脱敏前 md5（与上游 DaRUS 记录的核验见各 .source.txt 侧车 verified_against 段）：
  Export10_244531.csv  8cba13dfae7d1a3cdf48d3e20851dadb
  DD_head.csv          995d0d916f872520025a1d57e685ab9f
"""
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def md5(p):
    return hashlib.md5(pathlib.Path(p).read_bytes()).hexdigest()

def swap(path, pairs, regexes=()):
    p = ROOT / path
    b = p.read_bytes()
    pre = hashlib.md5(b).hexdigest()
    total = 0
    for old, new in pairs:
        n = b.count(old)
        if n == 0:
            print(f"[MISS] {path}: 未找到 {old[:50]!r}")
            sys.exit(1)
        b = b.replace(old, new)
        total += n
    for pat, new in regexes:
        b, n = re.subn(pat, new, b)
        total += n
    p.write_bytes(b)
    print(f"[OK] {path}: {total} 处替换 | md5 {pre} -> {md5(p)}")

# ---- 1) Export10_244531.csv：L2 路径 / L3-L4 ticks+墙钟 / L11 NetID ×32
# 规则按**形态**写（正则族），不复述被替换的具体字节值——路径、墙钟、路由标识的
# 原文不在本仓留痕。原脚本另在起始时间行末尾追加了「≈ 18.65 s」的导出时长
# （由 18650 行 × 1 ms 推出，不是墙钟），此处以注释记明。
swap("data/raw/Export10_244531.csv", [], regexes=[
    (rb"C:\\Versuchsstand\\[^\s\xef\xbc\x8c\xef\xbc\x9b\xef\xbc\x89]+", b"[REDACTED_HOST_PATH]"),
    (rb"\b1\d{17}\t[A-Za-z]+, \d{1,2}\. \w+ \d{4}\t\d{2}:\d{2}:\d{2}\.\d+",
     b"[REDACTED_WALLCLOCK]\t[REDACTED_WALLCLOCK]\t[REDACTED_WALLCLOCK]"),
    (rb"141\.58\.\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", b"[REDACTED_ADS_NETID]"),
])

# ---- 2) DD_head.csv：L2 路径 / L3-L4 ticks+墙钟（本变体无 NetID 行）
swap("data/raw/DD_head.csv", [], regexes=[
    (rb"C:\\Versuchsstand\\[^\s\xef\xbc\x8c\xef\xbc\x9b\xef\xbc\x89]+", b"[REDACTED_HOST_PATH]"),
    (rb"\b1\d{17}\t[A-Za-z]+, \d{1,2}\. \w+ \d{4}\t\d{2}:\d{2}:\d{2}\.\d+",
     b"[REDACTED_WALLCLOCK]\t[REDACTED_WALLCLOCK]\t[REDACTED_WALLCLOCK]"),
])

# ---- 3) Export10 侧车：路径 / 导出时刻 / 标题纠偏（KB7 裁决 2026-10-22）
swap("data/raw/Export10_244531.csv.source.txt", [
    ("（数据集标题 \"Measurement data for the identification of dynamic running properties of synthetic fiber ropes\"）".encode("utf-8"),
     "（数据集标题 \"Measurement data for: Development of a Cable Actuator Test Rig for "
     "Identification of Dynamic Running Properties of Synthetic Fiber Ropes\"——2026-10-22 纠偏："
     "旧记为转述有误，以 darus3600.json API 留档 latestVersion typeName=title 逐字为准，与 KB7:10 一致）".encode("utf-8")),
], regexes=[
    (rb"C:\\Versuchsstand\\[^\s\xef\xbc\x8c\xef\xbc\x9b\xef\xbc\x89]+", b"[REDACTED_HOST_PATH]"),
    (r"导出时刻 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)? ~ \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?".encode("utf-8"),
     "[REDACTED_WALLCLOCK]（相对时长 ≈ 18.65 s）".encode("utf-8")),
])

# ---- 4) DD_head 侧车：路径命中 1 处（probe_pii 清单），正则兜底同款路径族
swap("data/raw/DD_head.csv.source.txt", [], regexes=[
    (rb"C:\\Versuchsstand\\[^\s\xef\xbc\x8c\xef\xbc\x9b\xef\xbc\x89]+", b"[REDACTED_HOST_PATH]"),
])

print("完成：4 文件全部等行数替换；请复跑 probe_pii.py 与 pytest 验证。")
