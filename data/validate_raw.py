"""数据文件批量校验脚本（非产品代码，KB2 §五 / C1 红线的解析器端初筛）。

对 data/raw/ 下每个文件自动完成三件事：
  1. 时基    —— 单调性、dt 统计、抖动比、实测 fs 与声明 fs/挂钟时长三方交叉核对；
  2. 通道    —— 表头/单位解析、语义角色映射到 C1 规范名、能力缺口判定；
  3. 运动特征 —— 位置跨度、速度非零占比、运动段计数、加速度段、波峰因子（防纯正弦合成）、
                 跟随误差恒等式复算。

判据全部来自知识库，不新造：六条硬拒取自 KB2 §5.1（映射 C1 数据质量红线），
抖动比口径 std(dt)/median(dt) 同 C2 `quality.dt_jitter_ratio`。

不采信任何自述：`.source.txt` 里声明的采样率/行数/通道数一律与实测值对比，
输出 SUPPORTED / CONTRADICTED / UNVERIFIABLE。

`--selftest` 用七个人造退化样本逐条证伪六条红线（KB0 §6 检查 22 要求的负向测试）。

用法：
    python data/validate_raw.py                    # 扫 data/raw/
    python data/validate_raw.py a.csv b.csv        # 只扫指定文件
    python data/validate_raw.py --selftest         # 负向测试
    python data/validate_raw.py --out-txt f --out-json g
"""
import argparse, datetime, hashlib, io, json, math, os, re, statistics as st, sys, zipfile

# ---------------------------------------------------------------- 常量（出处见各行注释）

N_SAMPLES_MIN = 2000          # KB2 §5.1 硬拒 1（C1 红线）
DURATION_MIN_S = 0.5          # KB2 §5.1 硬拒 2
JITTER_MAX = 0.2              # KB2 §5.1 硬拒 3 == C2 quality.dt_jitter_ratio 上界
NAN_MAX = 0.05                # KB2 §5.1 硬拒 4
CRITICAL_ROLES = {"cur_q", "vel_fb", "fe"}   # KB2 §5.1 硬拒 6：三者全缺才拒

# 语义角色词典（C1 §通道映射的词表端；只映射，不猜未见于表头的语义）。
# 优先级不变：速度/电流/转矩必须排在位置之前——否则 `dVelocity_asco_enc` 的 `_enc`
# 会被位置词典抢先命中（本脚本对 Export10 的第一版实测就踩了这个）。
# ★ R-5（KB2 §4.12 / VERIFICATION §8.7）：量名判定改在**整词 token** 上做（分词与
# `name_tokens` 共用 `split_name_tokens`），不再用子串正则——实测子串命中造成
# `OilLevel_L → vel_fb`（le**vel**）、`FailureRate → vel_fb`（**rate**）、
# `Timestamp → cur_other`（timest**amp**）三处误报；按裁定不继续加正则补丁。
# 连带的两处如实登记：
#   · 裸 "rate" 从 vel 整词表剔除——只要它在表内，FailureRate 的整词 "rate" 仍会命中，
#     token 化也救不了；`Rate_asco / dRate_asco` 因此落 unmapped（命名族缺口，同 R-4
#     性质；vel_fb 角色仍由各 velocity 列给出，硬拒结论不受影响）。
#   · 单字母 "f" 只在**首 token** 计 force（对应旧 `^f_` 族名）；camel 拆词产物 "NoF"
#     的尾 token "f" 不得判成力（旧子串口径本就不命中，token 化若放宽反而会新增误报）。
QTY_TOKENS = [
    ("vel",     {"vel", "velocity", "speed", "rpm", "fdot", "spd", "v"}),
    ("torque",  {"torque", "tq", "mq", "moment", "tau"}),
    ("cur",     {"cur", "current", "iq", "q", "ma", "amp", "amps", "amper", "amperage"}),
    ("power",   {"power", "pwr", "watt", "watts", "laser"}),
    ("pos",     {"pos", "position", "encoder", "enc", "ist", "achse", "axis",
                 "mm", "pls", "dist", "path", "x"}),
    ("force",   {"force", "kistler", "newton", "loadcell"}),
]
# 「差值」是修饰而非物理量：pos 的差值 = 跟随误差 fe；force/vel 的差值只是 extra.<qty>.diff。
# 旧版把 f_diff（力差值）当成 fe，导致 DD_head 的恒等式检查拿错通道。
# `e_x` 族（DARUS-3759 数据集 README 逐字写明 "$e_x = x_d - x_l$ is the tracking error"）：
# 单字母下标的误差记号。早先词表没有它，把 2 kHz / 40 000 行的真 fe 数据集按「fe 全缺」误拒过。
# token 口径：首 token 为 e 且次 token 是单个字母（`e_3d` 的 "3d" 不是，维持原判不映 fe）。
DIFF_TOKENS = {"fe", "follow", "follower", "err", "error", "lag", "devi", "deviation",
               "abweich", "abweichung", "diff"}
# 元数据列（传感器编号、通道号、型号）不是波形，不参与任何判据
META_HINT = r"(?:_no\b|no$|_num\b|number|\bid\b|_idx\b|_sel\b|_type\b|_version\b|sensor)"
# 匈牙利命名 bXxx 必须对**原名**大小写敏感判定（小写化后 [A-Z] 永不命中，bMovingForward 曾被误成未映射）
IO_HINT = re.compile(r"(?:\bb[A-Z][A-Za-z0-9]*|bool|switch|trig\w*|trigger|limit|flag|(^|[._])di\d?($|[._])"
                     r"|(^|[._])do\d?($|[._])|enable|hall|home)")
META_HINT_RE = re.compile(META_HINT)
# 方向（指令/反馈）同样改整词判定（R-5 同一条裁定）。指令后缀与 `name_tokens`
# 的剥后缀逻辑同源共用：`x_Ltar` 拆出 "ltar"，量名走整词（不命中），方向走后缀 "tar"。
DIR_CMD_TOKENS = {"tar", "target", "set", "setpoint", "cmd", "command", "soll",
                  "profile", "plan", "cmdpos", "sp"}
DIR_FB_TOKENS = {"act", "actual", "meas", "measure", "measured", "measurement", "fb", "fbk",
                 "enc", "real", "feedback", "now", "ist"}
INSTR_SUFFIX_RE = re.compile(
    r"(tar|target|setpoint|set|cmd|command|sp|plan|actual|act|meas|fbk|fb|real|now|ist)$")
_SUFFIX_CMD = {"tar", "target", "setpoint", "set", "cmd", "command", "sp", "plan"}
TIME_NAME = r"(?:sampletime|^t$|^time|\btime\b|_ms$|_us$|_s$|zeit|timestamp|\bts\b|sample)"
# R-3（KB2 §4.12 / KB7 台账 15/16/17 行）：6114 两 CSV 的 t 列是 ISO-8601 文本时间戳，
# 此前 fnum 全判 NaN → 无时间列可解析 → 被「时基非严格单调」误拒。修法只补**解析**：
# 文本转 epoch 秒后，单调性/抖动等判据原样保留（不放松门槛）。裸时间按 UTC 理解
# （单调性只看差分，同文件内时区偏移相消）。
ISO_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:[.,](\d+))?"
    r"(?:\s*(?:Z|([+-])(\d{2}):?(\d{2})(?::?(\d{2}))?))?$")
# 分轴标签时剔除的结构词：留下 asco/test/load/lsv 这类"哪根轴/哪个测头"的家谱词
STOP_TOKENS = set("""measurement connector symbol name d b f x v iq id pos position vel velocity torque
current cur force power pwr diff err error tar target act actual ist meas fb fbk cmd command enc encoder
rate speed rms avg min max true false value val chan channel axis no num number type unit ms us sec s""".split())

UNIT_RE = re.compile(r"\[([a-zA-Zµ%°/]{1,10})\]|([%°])$")
NUM_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
# R-6（KB2 §4.12 / KB7 台账 20 行）：中欧/南美导出用**逗号做小数点**（`2563_LDD_*.csv`：
# `0,000000;19,999996;-20,172794`，分号分隔）。取值路径 `fnum` 早已会把逗号转成点，
# 但**布局判定** `is_num` 只认点十进制 ⟹ 整份可读文件被判 `layout=unparsed`、
# 台账里那句「时长 0.128 s」因此没有工具载体。只补判定，不补判据。
COMMA_DEC_RE = re.compile(r"^-?(?:\d+,\d*|,\d+)(?:[eE][+-]?\d+)?$")

LEAK_PATTERNS = [   # KB7 脱敏要求：发布前必须命中并处理
    # 盘符路径须排除 "https://" —— 前一版把 s://doi.org 误报成 windows_path
    ("windows_path", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]{1,2}(?:[^\s\"'<>|;,]{1,40}\\){1,6}[^\s\"'<>|,;]*")),
    ("ethercat_netid", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,2}\.\d{1,2}\b")),
    ("unc_path", re.compile(r"\\\\[A-Za-z0-9_.-]+\\[^\s\"']{2,60}")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    ("user_dir", re.compile(r"[\\/](?:Users|home)[\\/](?!\*)[A-Za-z0-9._-]{2,24}")),
    # 只盯真标识：现场项目名与 NetID 字样；传感器厂商名不算泄漏
    ("site_identifier", re.compile(r"(?i)(Versuchsstand|cable-actuator|cati-twincat|NetID|\bProjekte\b)")),
]
HTML_MARKERS = (b"<!doctype", b"<html", b"<head", b"<script", b"<meta ")


# ---------------------------------------------------------------- 基础工具

def sha256_bytes(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decode(raw):
    """编码判定：utf-8-sig 只在真有 BOM 时报，否则严格 utf-8 → cp1252 → latin-1 → utf-16。"""
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig"), "utf-8-sig(BOM)"
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "replace"), "utf-16(BOM)"
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", "replace"), "utf-8+replace"


def sniff_delimiter(line):
    for d, name in (("\t", "tab"), (";", "semicolon"), (",", "comma")):
        if line.count(d) >= 2:
            return d, name
    return " ", "space"


def is_num(tok, decimal_comma=False):
    s = tok.strip()
    return bool(NUM_RE.match(s) or (decimal_comma and COMMA_DEC_RE.match(s)))


def sniff_decimal_comma(rows_cells):
    """表体是否用逗号作小数点（R-6）。判据：窗口内**点十进制**单元格几乎不出现，
    而逗号十进制单元格占多数——两个条件同时成立才算，避免把
    `1,234`（千分位）或逗号分隔的正数表误判成小数逗号。"""
    dot = com = 0
    for r in rows_cells[:200]:
        for c in r:
            s = (c or "").strip()
            if NUM_RE.match(s):
                dot += 1
            elif COMMA_DEC_RE.match(s):
                com += 1
    return com >= 20 and com > 4 * dot


def fnum(tok):
    tok = tok.strip().replace(",", ".") if NUM_RE.match(tok.strip().replace(",", ".")) else tok.strip()
    if not NUM_RE.match(tok):
        return math.nan
    try:
        return float(tok)
    except ValueError:
        return math.nan


def iso_epoch(tok):
    """ISO-8601 文本时间戳 → epoch 秒；不匹配形态返回 NaN（R-3，判据本身不动，只补解析）。
    裸时间戳（无时区偏移）按 UTC 理解：单调性判定只看差分，同文件内偏移相消。"""
    m = ISO_TS_RE.match((tok or "").strip())
    if not m:
        return math.nan
    y, mo, d, hh, mi, ss, frac, sign, oh, om, osec = m.groups()
    micro = int((frac + "000000")[:6]) if frac else 0
    try:
        base = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss), micro,
                                 tzinfo=datetime.timezone.utc)
    except ValueError:
        return math.nan
    if sign:
        off = datetime.timedelta(hours=int(oh), minutes=int(om), seconds=int(osec or 0))
        base += off if sign == "-" else -off
    return base.timestamp()


def stats(v):
    v = [x for x in v if not math.isnan(x)]
    if not v:
        return None
    return {"n": len(v), "min": min(v), "max": max(v), "mean": st.fmean(v),
            "std": st.pstdev(v) if len(v) > 1 else 0.0, "first": v[0], "last": v[-1],
            "distinct": len(set(v)), "nan": 0}


# ---------------------------------------------------------------- 表头与布局解析

def _token_direction(toks):
    for t in toks:
        if t in DIR_CMD_TOKENS:
            return "cmd"
        m = INSTR_SUFFIX_RE.search(t)
        if m and m.group(1) in _SUFFIX_CMD:
            return "cmd"
    for t in toks:
        if t in DIR_FB_TOKENS:
            return "fb"
        m = INSTR_SUFFIX_RE.search(t)
        if m:
            return "fb"
    return None


def guess_role_from_name(name):
    """表头名 → (quantity, direction, is_diff)；映射不上返回 (None, None, False)，不猜语义（KB2 §三）。

    名字与 `src/axiscope/mapping.py::channel_role` **必须不同**（A-54 单一名字律）：本函数是审计**之前**
    按列名猜量名/方向（返回值是三元组），引擎那一支是审计**之后**回答"该列登记为 canonical 还是 extra"
    （返回值是字符串）。两者过去同名，读代码的人会拿错那一份。
    量名/方向/差值一律在**整词 token** 上判定（R-5 裁定：走 token 化匹配、不再加正则补丁），
    meta/io 的既有口径不动。
    """
    low = name.lower()
    if META_HINT_RE.search(low) and not re.search(r"pos|velocity|force", low):
        return "meta", "na", False
    if IO_HINT.search(name):
        return "io", "na", False
    toks = split_name_tokens(name)
    qty = None
    for q, vocab in QTY_TOKENS:
        for i, t in enumerate(toks):
            if t in vocab:
                qty = q
                break
            if q == "force" and t == "f" and i == 0:
                qty = "force"
                break
        if qty:
            break
    if qty is None and any(toks[i] == "load" and toks[i + 1] == "cell"
                           for i in range(len(toks) - 1)):
        qty = "force"
    if qty is None:
        return None, None, False
    d = _token_direction(toks)
    if d is None:
        d = "fb" if qty in ("pos", "vel", "cur", "torque") else "na"
    is_diff = any(t in DIFF_TOKENS for t in toks) or (
        len(toks) >= 2 and toks[0] == "e" and len(toks[1]) == 1 and "a" <= toks[1] <= "z")
    return qty, d, is_diff


def canonical_role(qty, d, raw, is_diff):
    """C1 规范名。fe/pos/vel/cur 四类进红线判定，其余记 extra_channels（KB2 §二坑 1）。"""
    rl = raw.lower()
    if qty == "meta":
        return None
    if qty == "io":
        return "io"
    if qty == "pos" and is_diff:
        return "fe"
    if is_diff:
        return f"extra.{qty}.diff"
    if qty == "pos":
        return f"pos_{d}"
    if qty == "vel":
        return f"vel_{d}"
    if qty == "cur":
        return "cur_q" if re.search(r"iq|_q\b|q_axis|torque_current", rl) else "cur_other"
    if qty == "power":
        return "laser_power" if "laser" in rl else f"extra.power.{d}" if d != "na" else "extra.power"
    return f"extra.{qty}.{d}" if d != "na" else f"extra.{qty}"


def split_name_tokens(raw_name):
    """整词切分（R-5 的分词底座，`name_tokens` 与 `guess_role_from_name` 共用）：
    按非字母数字切，再拆驼峰，并剥掉匈牙利类型前缀（dPosition→d position）。"""
    toks = []
    for seg in re.split(r"[^A-Za-z0-9]+", raw_name):
        if not seg:
            continue
        if len(seg) > 2 and seg[0].islower() and seg[1].isupper():
            seg = seg[0] + " " + seg[1:]
        toks += [t.lower() for t in re.split(
            r"[^A-Za-z0-9]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", seg)) if t]
    return toks


def name_tokens(raw_name):
    """家谱词（轴名）用 token：切词后剔除结构词与数字，并剥指令后缀。
    不剥前缀会把 `dPosition_test` 的轴名识别成 'dposition'，跨轴分组因此失效。"""
    # 家谱词常与指令后缀粘连（x_Ltar → ltar），剥掉后缀 l 才能与 x_L 归到同一轴组
    out = []
    for t in split_name_tokens(raw_name):
        if t.isdigit() or t in STOP_TOKENS:
            continue
        stem = INSTR_SUFFIX_RE.sub("", t)
        if stem and stem not in STOP_TOKENS:
            out.append(stem)
    return out


def assign_tags(chans):
    """按"家谱词"分轴：test/asco/load/lsv/L/T 这类被多通道共享、且不是结构词的 token。
    恒等式与 cmd↔fb 配对只能在同轴内做，跨轴相减会得到看似成立实则无意义的结果。"""
    from collections import Counter
    tok = {id(c): set(name_tokens(c["raw_name"])) for c in chans}
    cnt = Counter()
    for ts in tok.values():
        cnt.update(ts)
    shared = [t for t, n in cnt.most_common() if n >= 2]
    for c in chans:
        ts = tok[id(c)]
        c["axis_tag"] = next((t for t in shared if t in ts), "?")
    return chans


def parse_table(path, max_bytes=64 << 20):
    """返回 (meta, layout, chans, time_col, n_rows, flags)。

    行式读入（默认最多 64MB，撞线在 flags.size_truncated_at_read 显式报告），
    列数众数定主形状，不符的行剔除并计入 flags.n_rows_shape_mismatch，
    数据行再受 ROW_CAP 上限约束（撞线计入 flags.row_cap_hit）。
    """
    raw = open(path, "rb").read(max_bytes)
    flags = {}
    flags["size_truncated_at_read"] = os.path.getsize(path) > max_bytes
    text, enc = decode(raw)
    head = raw[:4096].lower()
    flags["looks_like_html"] = any(m in head for m in HTML_MARKERS)
    flags["bom"] = raw[:3] == b"\xef\xbb\xbf" or raw[:2] in (b"\xff\xfe", b"\xfe\xff")
    crlf = text.count("\r\n")
    lf = text.count("\n")
    flags["line_ending"] = "CRLF" if crlf and crlf == lf else ("LF" if lf else "none")

    lines = [ln.rstrip("\r\n") for ln in io.StringIO(text, newline="\n").read().split("\n")]
    flags["n_nonempty_lines"] = sum(1 for l in lines if l.strip() != "")
    delim, delim_name = sniff_delimiter(lines[0] if lines else "")
    rows_cells = [ln.split(delim) for ln in lines]
    nc = max((len(r) for r in rows_cells[:400]), default=0)

    # 数据块起点：连续 20 行、数值占比 > 0.6、单元格数等于众数
    counts = [len(r) for r in rows_cells if r and r != [""]]
    mode_nc = max(set(counts), key=counts.count) if counts else 0
    dec_comma = sniff_decimal_comma(rows_cells)
    flags["decimal_comma"] = dec_comma

    def name_score(r):
        toks = [c for c in r if c not in ("", None)]
        if not toks:
            return -1
        nonnum = sum(1 for c in toks if not is_num(c, dec_comma))
        return (nonnum / len(toks)) * len(set(toks)) if nonnum else -1

    # 首行像表头时，数据块至少从第 2 行起——否则表头无处安放
    i0 = 1 if (rows_cells and name_score(rows_cells[0]) > 0) else 0

    def row_ok(r):
        return (len(r) == mode_nc
                and sum(1 for c in r if is_num(c, dec_comma)) >= 0.6 * mode_nc)

    data_start = None
    for i in range(i0, min(len(rows_cells), 200)):
        window = rows_cells[i:i + 20]
        if len(window) < 20:
            break
        if sum(1 for r in window if row_ok(r)) >= 18:
            data_start = i
            break
    if data_start is not None:
        # 20/18 的宽松窗口会把 "Port\t851\tPort\t851…" 这类**数值型表头行**放进来
        # （Export10 实测：每个通道首值都成了 851.0，min/max/std 与恒等式全被带偏）
        # ⟹ 定位到窗口后再向前跳过不合格的行
        while data_start < len(rows_cells) and not row_ok(rows_cells[data_start]):
            data_start += 1
    if data_start is None or data_start >= len(rows_cells):
        return {"encoding": enc, "delimiter": delim_name}, "unparsed", [], {"series": []}, flags["n_nonempty_lines"], flags

    # 名称行 / 单位行：data_start 之前 token 最像名字的两行
    pre = rows_cells[:data_start]
    cand = [(name_score(r), i) for i, r in enumerate(pre)]
    cand = [c for c in cand if c[0] > 0]
    if not cand:
        return {"encoding": enc, "delimiter": delim_name}, "unparsed", [], {"series": []}, flags["n_nonempty_lines"], flags
    _, name_i = max(cand)
    name_row = pre[name_i]

    layout = "plain_matrix"
    even_same = len(set(name_row[0::2])) == 1 and len(name_row) > 4
    if even_same:                       # TwinCAT Scope View：(x轴名, 通道名) 交替，见 KB2 §一
        layout = "twincat_interleaved"
        names = name_row[1::2]
        units_row = pre[name_i + 1] if name_i + 1 < len(pre) else []
        units = units_row[1::2] if len(units_row) > 1 else []
        axis_names = units_row[0::2] if units_row else []
        declared_period = units_row[1::2] if units_row else []
        meta = {"axis_name": axis_names[0] if axis_names else None,
                "declared_period_raw": declared_period[0] if declared_period else None}
    else:
        names = [c.strip() for c in name_row]
        units = []
        meta = {}
    meta["encoding"], meta["delimiter"] = enc, delim_name
    meta["header_rows"] = data_start
    meta["kv_meta"] = kv_meta(pre)

    # 数值列抽取
    # ROW_CAP：第一版硬写 [:200000]，把 200001 行的 ScienceDB 样本静悄悄削掉一行，
    # 于是自述 rows=200001 被我判成 CONTRADICTED。上限本身要保留（内存），但撞线必须显式报告。
    ROW_CAP = 4_000_000
    ncols = mode_nc
    body = rows_cells[data_start:]
    flags["n_blank_rows_skipped"] = sum(1 for r in body if not r or
                                        not any(c.strip() for c in r))
    shaped = [r for r in body if r and any(c.strip() for c in r)]
    fit = [r for r in shaped if len(r) == ncols]
    flags["n_rows_shape_mismatch"] = len(shaped) - len(fit)
    flags["row_cap"] = ROW_CAP
    flags["row_cap_hit"] = len(fit) > ROW_CAP
    cells = fit[:ROW_CAP]
    cols = [[fnum(r[j]) for r in cells] for j in range(ncols)]
    if layout == "twincat_interleaved":
        time_col = 0
        time_col_source = "format_family:twincat"
        val_cols = list(range(1, ncols, 2))
        meta["declared_axis_period_per_channel"] = [units_row[2 * k + 1] if units_row and 2 * k + 1 < len(units_row) else None
                                                    for k in range(len(names))]
    else:
        time_col = None
        time_col_source = None
        for j, nm in enumerate(names):
            if nm and re.search(TIME_NAME, nm.lower()):
                time_col, time_col_source = j, "column_name"
                break
        if time_col is None:
            # R-3：列名认不出时，先看内容——整列（抽样）都是 ISO-8601 文本的列就是时基列，
            # 优先于「数值严格递增列」启发（6114 若 t 列改名也不会再被行号索引列抢位）。
            iso_cols = [j for j in range(ncols)
                        if _col_looks_iso([r[j] for r in cells[:200] if j < len(r)])]
            if iso_cols:
                time_col, time_col_source = iso_cols[0], "iso8601_content"
        if time_col is None:
            mono = [j for j, c in enumerate(cols) if len(c) > 10 and all(
                    (not math.isnan(c[k])) and (k == 0 or c[k] > c[k - 1]) for k in range(1, min(len(c), 50)))]
            if mono:
                # 启发式：这一列只是"前 50 点递增"，身份未经列名/形态证实（可能是速度斜坡、
                # 计数累积）。留痕是为了 R-7——它整体不单调时只能说"没有可用的时基列"，
                # 不能报「时基非严格单调」，那是对一个未证实身份的列下的判定。
                time_col, time_col_source = mono[0], "monotonic_heuristic"
        val_cols = [j for j in range(ncols) if j != time_col]

    chans = []
    for n, ch_idx in enumerate(val_cols):
        j = 2 * (n + 1) - 1 if layout == "twincat_interleaved" else ch_idx
        # names 是整行表头（含时间列），val_cols 已把时间列剔除——plain_matrix 必须按列号
        # 取名，否则名实整体错位一列且末列被静悄悄丢掉（KB0 §6 检查 22 的负向测试覆盖此条）。
        raw_name = names[n] if layout == "twincat_interleaved" else (
            names[ch_idx] if ch_idx < len(names) else f"col{ch_idx}")
        unit = None
        if layout == "twincat_interleaved":
            unit = UNIT_RE.search(raw_name)
        elif n < len(units):
            unit = UNIT_RE.search(units[n]) or (UNIT_RE.search(raw_name) if raw_name else None)
        else:
            unit = UNIT_RE.search(raw_name) if raw_name else None
        qty, d, is_diff = guess_role_from_name(raw_name)
        chans.append({"raw_name": raw_name, "col": j,
                      "unit": (unit.group(1) or unit.group(2)) if unit else None,
                      "quantity": qty, "direction": d, "is_diff": is_diff,
                      "canonical": canonical_role(qty, d, raw_name, is_diff) if qty else None,
                      "series": cols[j]})
    assign_tags(chans)
    tc = {"col": time_col, "source": time_col_source,
          "name": (names[time_col] if time_col is not None and time_col < len(names) else None),
          "series": cols[time_col] if time_col is not None else []}
    # R-3：时间列数值口径失败（fnum 全 NaN）而原文是 ISO-8601 ⟹ 转 epoch 秒再入时基分析；
    # 严格单调门原样作用于转换后的序列（改的是解析，不是判据）。
    if time_col is not None and sum(1 for x in tc["series"] if not math.isnan(x)) < 3:
        parsed = [iso_epoch(r[time_col]) for r in cells if time_col < len(r)]
        if len(parsed) >= 3 and sum(1 for x in parsed if not math.isnan(x)) >= 0.6 * len(parsed):
            tc["series"] = parsed
            tc["iso8601"] = True
    return meta, layout, chans, tc, len(cells), flags


def _col_looks_iso(col_cells):
    vals = [c.strip() for c in col_cells if c and c.strip()]
    if len(vals) < 3:
        return False
    return sum(1 for v in vals if ISO_TS_RE.match(v)) >= 0.9 * len(vals)


def kv_meta(pre_rows):
    """表头前的 key<TAB>value 元数据（TwinCAT 有 6 行；含挂钟起止）。"""
    out = {}
    for r in pre_rows:
        if len(r) >= 2 and r[0] and not is_num(r[0]) and len(r[0]) < 40:
            out[r[0].strip()] = "\t".join(x for x in r[1:] if x != "")[:160]
    return out


# ---------------------------------------------------------------- 时基

def analyze_time(tc, n_rows, kv, layout, claim_fs=None):
    t = [x for x in (tc.get("series") or []) if not math.isnan(x)]
    if len(t) < 3:
        return {"status": "no_time_column", "time_col_source": tc.get("source")}, []
    dts = [t[i + 1] - t[i] for i in range(len(t) - 1)]
    med = st.median(dts)
    res = {"col": tc["col"], "name": tc["name"], "time_col_source": tc.get("source"),
           "unit_inferred": None,
           "n": len(t), "t0": t[0], "t1": t[-1],
           "strictly_monotonic": all(d > 0 for d in dts),
           "monotonic": all(d >= 0 for d in dts),
           "any_duplicate": any(d == 0 for d in dts),
           "dt_median": med, "dt_mean": st.fmean(dts),
           "dt_min": min(dts), "dt_max": max(dts),
           "dt_std": st.pstdev(dts), "n_distinct_dt": len(set(dts)),
           "dt_jitter_ratio": (st.pstdev(dts) / abs(med)) if med else math.inf,
           "duration_units": t[-1] - t[0]}
    # 时间列单位：列名 > 格式家族（TwinCAT）> 来源存证佐证 > 否则 ambiguous。**不做默认值冒充**
    # （KB2 §三 / §5.2）。第一版硬写「未知即按 ms」，500 Hz 的 `tout`(s) 被读成 500 kHz、
    # 400 s 的样本被误判成「有效时长<0.5s」而硬拒——单位未定时不许开硬拒红线。
    nm = (tc["name"] or "").lower()
    UNIT = {"us": 1e-6, "ms": 1e-3, "s": 1e0}
    if tc.get("iso8601"):
        # R-3：ISO-8601 已解析为 epoch 秒，单位由格式本身定死（秒），不再有 us/ms/s 假设，
        # 也不需要 sidecar 佐证解除歧义；单调性/抖动判据照常作用于差分。
        res["time_format"] = "iso8601_text"
        res["unit_inferred"] = "s"
        res["unit_source"], res["unit_ambiguous"] = "iso8601_text:epoch_seconds", False
        res["duration_s"] = res["duration_units"]
        res["fs_hz"] = (1.0 / med) if med else None
    else:
        res["duration_hypotheses_s"] = {k: res["duration_units"] * v for k, v in UNIT.items()}
        res["fs_hypotheses_hz"] = ({k: 1.0 / (med * v) for k, v in UNIT.items()} if med else {})
        named = ("ms" if "ms" in nm else
                 ("us" if "us" in nm and "ms" not in nm else
                  ("s" if re.search(r"(?:^|[^a-z])s\b|second|\bsec\b", nm) else None)))
        unit, res["unit_source"], res["unit_ambiguous"] = None, None, True
        if named:
            unit = UNIT[named]
            res["unit_source"], res["unit_ambiguous"] = f"column_name:{named}", False
        elif layout == "twincat_interleaved":
            unit = UNIT["ms"]                       # KB2 §一：Scope View col0 SampleTime 固定 ms
            res["unit_source"], res["unit_ambiguous"] = "format_family:twincat(SampleTime=ms)", False
        elif claim_fs:
            # sidecar（数据集页面/发布者文档）声称的采样率若只吻合一种单位假设，可作外部佐证
            # 解除单位歧义——这是 ③b 外部出处，不是本地自洽（A-89），故单列来源标签。
            hits = [k for k, v in res["fs_hypotheses_hz"].items()
                    if abs(v - claim_fs) <= 0.05 * max(claim_fs, 1e-9)]
            if len(hits) == 1:
                unit = UNIT[hits[0]]
                res["unit_source"], res["unit_ambiguous"] = f"sidecar_attested:{hits[0]}", False
            elif len(hits) > 1:
                res["unit_conflict"] = f"声称 {claim_fs:g}Hz 同时吻合 {hits} 假设，仍判未定"
        res["unit_inferred"] = None if unit is None else (named or res.get("unit_source"))
        res["duration_s"] = None if unit is None else res["duration_units"] * unit
        res["fs_hz"] = (None if unit is None or not med else 1.0 / (med * unit))

        # 声明时基：表头里的周期常数（TwinCAT 单位行 '1' 表示 1 ms/点；单位同时间列）
        decl = kv.get("declared_period_raw")
        if unit is not None and decl is not None and is_num(str(decl)):
            res["declared_period_units"] = fnum(str(decl))
            res["declared_fs_hz"] = 1.0 / (res["declared_period_units"] * unit) if res["declared_period_units"] else None
            res["declared_vs_measured_ratio"] = res["declared_fs_hz"] / res["fs_hz"] if res["fs_hz"] else None

    # 挂钟交叉核对：.NET ticks(100ns) 或 HH:MM:SS.mmm
    wc = wallclock_duration_s(kv)
    if wc is not None and res.get("duration_s") is not None:
        res["wallclock_duration_s"] = wc
        res["wallclock_vs_measured_ratio"] = wc / res["duration_s"] if res["duration_s"] else None
        res["fs_from_wallclock"] = (n_rows - 1) / wc if wc > 0 else None
    return res, []


def wallclock_duration_s(kv):
    start = end = None
    for k, v in kv.items():
        kl = k.lower()
        if "start" in kl:
            start = v
        elif "end" in kl:
            end = v
    for pair in ((start, end),):
        if not pair[0] or not pair[1]:
            continue
        ticks = [None, None]
        for i, val in enumerate(pair):
            m = re.search(r"\b(1\d{16,17})\b", val)
            if m:
                ticks[i] = int(m.group(1))
        if ticks[0] and ticks[1] and ticks[1] > ticks[0]:
            return (ticks[1] - ticks[0]) / 1e7
        hm = [re.search(r"(\d{1,2}):(\d{2}):(\d{2})\.?(\d{1,3})?", val) for val in pair]
        if all(hm):
            sec = lambda m: int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int((m.group(4) or "0").ljust(3, "0")) / 1000
            d = sec(hm[1]) - sec(hm[0])
            return d if d > 0 else None
    return None


# ---------------------------------------------------------------- 运动特征

def analyze_channel(series, fs, t):
    v = [x for x in series if not math.isnan(x)]
    if not v:
        return {"status": "all_nan"}
    s = stats(series)
    nan_ratio = (len(series) - len(v)) / max(len(series), 1)
    mean = s["mean"]
    centred = [x - mean for x in v]
    rms = math.sqrt(st.fmean([x * x for x in centred])) if centred else 0.0
    peak = max(map(abs, centred), default=0.0)
    crest = peak / rms if rms > 0 else 0.0
    out = dict(s, rms=rms, crest_factor=crest, nan_ratio=nan_ratio,
               span=s["max"] - s["min"], std_over_range=(s["max"] - s["min"]) and s["std"])
    # 枚举/编号列（如 dForceSensorNo）值是整数且值域极小，不是波形量 —— 名字像 force 也不算力曲线
    out["is_enumerated"] = out["distinct"] <= 8 and all(abs(x - round(x)) < 1e-12 for x in v)
    if len(v) < 3:
        return out
    d1 = [v[i + 1] - v[i] for i in range(len(v) - 1)]
    d2 = [d1[i + 1] - d1[i] for i in range(len(d1) - 1)]
    aq = sorted(map(abs, d1))
    q = lambda p: aq[min(len(aq) - 1, int(p * len(aq)))]
    noise, dyn = q(0.10), q(0.90)
    # 动态性双门控：步进信噪（否则纯噪声通道也算"在动"）+ 相对跨度（否则准静态漂移也算 move 段）
    snr_ok = dyn > 5 * (noise + 1e-15)
    rel_span_ok = out["span"] > 1e-4 * (abs(s["max"]) + abs(s["min"]) + 1e-15)
    is_dynamic = snr_ok and rel_span_ok
    thr = max(3 * noise, 0.05 * dyn, 1e-15)
    moving = [abs(d) > thr for d in d1] if is_dynamic else [False] * len(d1)
    out["is_dynamic"] = is_dynamic
    out["dyn_snr"] = (dyn / noise) if noise else (math.inf if dyn else 0.0)
    out["nonzero_motion_fraction"] = sum(1 for m in moving if m) / max(len(moving), 1)
    segs, run = [], 0
    for m in moving:
        if m:
            run += 1
        elif run:
            segs.append(run)
            run = 0
    if run:
        segs.append(run)
    out["n_move_segments"] = len([x for x in segs if x >= 3])
    out["move_time_s"] = sum(x for x in segs if x >= 3) / fs if fs else None
    out["max_segment_len"] = max(segs) if segs else 0
    signs = [1 if x > thr else (-1 if x < -thr else 0) for x in d1]
    out["n_direction_changes"] = sum(1 for i in range(1, len(signs))
                                     if signs[i] and signs[i - 1] and signs[i] != signs[i - 1])
    out["d2_rms"] = math.sqrt(st.fmean([x * x for x in d2])) if d2 else 0.0
    # 退化形态：恒值 / 纯斜坡（合成）/ 纯正弦（合成）
    out["is_constant"] = s["std"] == 0
    if out["n_move_segments"] <= 1 and len(d2) > 10:
        out["near_linear_ramp"] = st.pstdev(d2) < 1e-9 * max(1.0, abs(s["mean"]))
    else:
        out["near_linear_ramp"] = False
    out["sine_like"] = 1.30 < crest < 1.55 and out["n_direction_changes"] > 0.6 * max(len(v) / 20, 1)
    return out


def _identity_triple(cmd, fb, fe, cmd_nm, fb_nm, fe_nm, assumed, alternatives=None):
    n = min(len(cmd), len(fb), len(fe))
    res = [fe[i] - (cmd[i] - fb[i]) for i in range(n)
           if not (math.isnan(fe[i]) or math.isnan(cmd[i]) or math.isnan(fb[i]))]
    if len(res) < 10:
        return None
    fev = [x for x in fe[:n] if not math.isnan(x)]
    s_fe = st.pstdev(fev) or 1e-15
    fe_span = (max(fev) - min(fev)) or 1e-15
    alt = [fe[i] - (fb[i] - cmd[i]) for i in range(n)]
    return {"n": len(res), "mean": st.fmean(res), "std": st.pstdev(res),
            "max_abs": max(map(abs, res)),
            "residual_vs_fe_std_pct": 100.0 * st.pstdev(res) / s_fe,
            "identity_holds": (st.pstdev(res) < 0.01 * s_fe
                               and abs(st.fmean(res)) < 0.01 * fe_span),
            "fe_sign": "fe=cmd-fb" if abs(st.fmean(res)) <= abs(st.fmean(alt)) else "fe=fb-cmd",
            "channels": {"pos_cmd": cmd_nm, "pos_fb": fb_nm, "fe": fe_nm},
            "fe_group_assumed": assumed,
            "candidate_groups": alternatives or {},
            "note": "residual_vs_fe_std_pct<1 ⟹ 恒等式成立（同单位）；否则单位/符号/采样错位，人工判读（KB2 §三）"}


def fe_identity(chans):
    """跟随误差恒等式复算（KB2 §二坑 5 / C1 规则 2）：fe ?= pos_cmd − pos_fb，**同轴内**做。

    跨轴取通道会得到"看起来成立、实际无意义"的结果——第一版就用了文件里第一个
    pos_cmd/pos_fb/fe，在 Export10 上把 asco 与 test 两组轴混减，残差 mean=−0.9 std=6.2。
    """
    out = {}
    tags = {}
    for c in chans:
        if c["canonical"]:
            tags.setdefault(c.get("axis_tag") or "?", []).append(c)

    def pick(role, cs):
        return next((c for c in cs if c["canonical"] == role), None)

    for tag, cs in sorted(tags.items()):
        if tag == "?":      # 无家谱词的"组"不构成同轴证据，只作为孤儿 fe 的候选来源
            continue
        cmd, fb, fe = pick("pos_cmd", cs), pick("pos_fb", cs), pick("fe", cs)
        if not (cmd and fb and fe):
            continue
        got = _identity_triple(cmd["series"], fb["series"], fe["series"],
                               cmd["raw_name"], fb["raw_name"], fe["raw_name"], False)
        if got:
            out[tag] = got

    # 孤儿 fe（通道名里没有家谱词，如 dPosition_diff）：对**每个**候选轴组都算一遍残差，
    # 取最小者并把全部备选一并列出——残差最小本身就是"这根 fe 属于哪根轴"的证据（A-88 式举证）。
    orphan_fe = [c for c in chans if c["canonical"] == "fe" and c.get("axis_tag") == "?"
                 and not any(o["channels"]["fe"] == c["raw_name"] for o in out.values())]
    for o in orphan_fe:
        cands = {}
        for tag, cs in tags.items():
            cmd, fb = pick("pos_cmd", cs), pick("pos_fb", cs)
            if cmd and fb and not pick("fe", cs):
                got = _identity_triple(cmd["series"], fb["series"], o["series"],
                                       cmd["raw_name"], fb["raw_name"], o["raw_name"], True)
                if got:
                    cands[tag] = got
        if not cands:
            continue
        best = min(cands, key=lambda t: cands[t]["residual_vs_fe_std_pct"])
        rest = sorted((v["residual_vs_fe_std_pct"] for t, v in cands.items() if t != best))
        uniq = bool(rest) and cands[best]["residual_vs_fe_std_pct"] < 0.2 * rest[0]
        cands[best]["candidate_groups"] = {t: round(v["residual_vs_fe_std_pct"], 4)
                                           for t, v in cands.items()}
        cands[best]["fe_group_unique"] = uniq
        out[best] = cands[best]
    if not out:
        return {"status": "not_computable",
                "needs": "同一 axis_tag 下同时存在 pos_cmd / pos_fb / fe",
                "available_roles": sorted({str(c["canonical"]) for c in chans if c["canonical"]})}
    return {"status": "ok", "per_axis": out}


# ---------------------------------------------------------------- 红线判定

def redlines(tb, chans, n_rows):
    fired = []
    meas = {}
    meas["n_filtered"] = n_rows
    if n_rows < N_SAMPLES_MIN:
        fired.append(f"n_samples<{N_SAMPLES_MIN} (实测 {n_rows})")
    dur = tb.get("duration_s")
    meas["duration_s"] = dur
    if dur is not None and dur < DURATION_MIN_S:
        fired.append(f"有效时长<{DURATION_MIN_S}s (实测 {dur:.4f}s)")
    if tb.get("status") == "no_time_column":
        # R-7：无时间列 ≠ 非单调。此前 `strictly_monotonic` 缺省 False ⟹ 拒因写成
        # 「时基非严格单调」，把一个"无从判定"报成了"判定不合格"（C1 §time_bases 第 ⑤ 条
        # 对 event 栅格明令禁止这种写法，检查 22：拒因必须指向实测到的缺陷）。
        fired.append("无时间列可解析（时基不可得，不作单调性结论）")
    elif not tb.get("strictly_monotonic", False):
        if tb.get("time_col_source") == "monotonic_heuristic":
            # 身份未证实的列（只按"前 50 点递增"抢来的）整体不单调 ⟹ 结论仍是"没有可用时基列"，
            # 而不是"这一列不单调"——后者会对一个数值通道下时基判决。
            fired.append("无时间列可解析（列名/ISO 形态均不识别，递增启发列不成立）")
        else:
            fired.append("时基非严格单调（无法定义 t_i，拒）")
    jr = tb.get("dt_jitter_ratio")
    meas["dt_jitter_ratio"] = jr
    if (jr is not None and jr > JITTER_MAX
            and not (tb.get("time_col_source") == "monotonic_heuristic"
                     and not tb.get("strictly_monotonic", False))):
        fired.append(f"dt_jitter_ratio>{JITTER_MAX} (实测 {jr:.3f})")
    present = {c["canonical"] for c in chans if c["canonical"]}
    per_ch = [c.get("feat", {}).get("nan_ratio") for c in chans]
    nan_g = max([x for x in per_ch if x is not None], default=0.0)
    meas["nan_ratio_worst_channel"] = nan_g
    if nan_g > NAN_MAX:
        fired.append(f"nan_ratio>{NAN_MAX} (最差通道 {nan_g:.3f})")
    dyn = max([c.get("feat", {}).get("n_move_segments", 0) for c in chans], default=0)
    meas["n_move_segments_max"] = dyn
    if dyn == 0:
        fired.append("无动态分段（无 move/settling/probing 段）")
    missing = CRITICAL_ROLES - present
    meas["present_canonical"] = sorted(present)
    meas["missing_critical"] = sorted(missing)
    if missing == set(CRITICAL_ROLES):
        # 三类角色全缺有两种成因：数据里真的没有，或本解析器认不出这套命名（机器人学
        # q/theta/qd 一类）。后者不能写成「数据缺失」——那是我们没证明的断言（A-88）。
        unmapped = [c["raw_name"] for c in chans if not c["canonical"]]
        fired.append("cur_q/vel_fb/fe 全缺" if len(unmapped) * 2 < len(chans) else
                     f"cur_q/vel_fb/fe 未识别（{len(unmapped)}/{len(chans)} 列未映射，"
                     f"疑为命名族缺口而非数据缺失，须按数据集文档人工复判）")
    return fired, meas


def soft_degradations(chans):
    out = []
    present = {c["canonical"] for c in chans if c["canonical"]}
    if "fe" in present and "pos_fb" in present and "pos_cmd" not in present:
        out.append("缺 pos_cmd → C1 规则 2 派生，运动学特征不降级")
    if "fe" in present and "pos_fb" not in present and "pos_cmd" not in present:
        out.append("只有 fe → C1 规则 3：超调/稳定时间 unavailable，纹波/稳态判据仍可跑")
    if "vel_fb" in present and "cur_q" not in present and "cur_other" not in present:
        out.append("cur_q 缺 → 共振主通道弱，freq 类判据降级并提示需电流通道（KB2 §5.2）")
    if any(str(c["canonical"]).startswith("extra.") for c in chans):
        out.append("存在 C1 无对应通道 → 入 extra_channels（KB2 §二坑 6）")
    return out


# ---------------------------------------------------------------- 自述核证

SIDECAR_TEXT_KEYS = ("url", "publisher", "license", "dataset_doi", "original_filename",
                     "format_family", "device_or_software", "variable_semantics")
# 2026-10-20 依据实测教训增补的四项（见 PROVENANCE-TEMPLATE.md）
TEMPLATE_V2_KEYS = ("derived_from", "upstream_id", "verified_against", "verified_by")
UNREGISTERED_RE = re.compile(r"(来源未登记|未登记|未证实|未知|无法实测|N/?A$|^NONE$)", re.I)


def read_sidecar_fields(path):
    """按 PROVENANCE-TEMPLATE 的 `key: value` 结构读 sidecar。

    第一版用散文正则扫 fs/rows/channels，结果把 `channels: 11（tout, q1, …）` 读成 1、
    把 `1t1r` 里的 1 当成通道数——模板既然是结构化的，就不该再用正则猜（KB0 §6 检查 22 的
    反向教训：核对逻辑自己也要有负向测试）。
    """
    if not os.path.exists(path):
        return None
    text, enc = decode(open(path, "rb").read())
    out = {}
    for ln in text.split("\n"):
        m = re.match(r"\s*([A-Za-z][A-Za-z0-9 _-]{0,28}?)\s*:\s*(\S.*)$", ln)
        if m:
            out.setdefault(m.group(1).strip().lower().replace(" ", "_").replace("-", "_"),
                           m.group(2).strip())
    return {"fields": out, "text": text, "encoding": enc}


def _leading_num(s):
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)", s or "")
    return float(m.group(1).replace(",", "")) if m else None


def claimed_fs_hz(s):
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(GHz|MHz|kHz|Hz)", s or "", re.I)
    if not m:
        return None
    mult = {"ghz": 1e9, "mhz": 1e6, "khz": 1e3, "hz": 1.0}[m.group(2).lower()]
    return float(m.group(1).replace(",", "")) * mult


def _cmp(label, claimed, cands, tol=0.05, context=None):
    """cands: [(实测值, 口径说明)]；命中任一口径即 SUPPORTED（口径差异要写明）。

    context：实测口径不可用时给出的旁证（如未解析文件的物理行数），只写进 note，
    不参与判定——布局都解析不了的文件既不能证伪也不能算核实（A-89 ③b）。
    """
    if claimed is None:
        return {"claim": label, "status": "UNVERIFIABLE", "check": "无自述数字",
                "note": "sidecar 该项未给出可比数字（不占应核对 n）"}
    for mv, how in cands:
        if mv is None:
            continue
        if abs(mv - claimed) <= tol * max(abs(claimed), 1e-9):
            return {"claim": label, "claimed": claimed, "measured": mv, "status": "SUPPORTED",
                    "note": f"实测一致（口径：{how}）"}
    known = [(m, h) for m, h in cands if m is not None]
    if not known:                       # 实测口径全不可用（如 layout=unparsed）⟹ 无从证伪
        return {"claim": label, "claimed": claimed, "measured": None, "status": "UNVERIFIABLE",
                "note": "实测值不可用（布局未解析），既不支持也不证伪" +
                        (f"；旁证：{context}" if context else "")}
    mv, how = known[0]
    return {"claim": label, "claimed": claimed, "measured": mv, "status": "CONTRADICTED",
            "note": f"实测 {mv:.6g} ≠ 声称 {claimed:.6g}（口径：{how}）"}


def check_claims(sc, measured, path=None):
    """sidecar 自述逐条 vs 实测 —— 不采信自述（A-88/A-89：第三方转述对本仓库不算核对）。"""
    if sc is None:
        return [{"claim": "source sidecar", "status": "ABSENT",
                 "note": "无 .source.txt ⟹ external_reference 与 verified_against 无从登记，该样本不可进 KB2 接入卡"}]
    f = sc["fields"]
    results = []
    for key in SIDECAR_TEXT_KEYS:
        v = f.get(key)
        if v is None:
            results.append({"claim": key, "status": "MISSING", "check": "登记核对",
                            "note": "模板该项缺失"})
        elif UNREGISTERED_RE.search(v):
            results.append({"claim": key, "status": "NOT_REGISTERED", "text": v[:120],
                            "check": "登记核对",
                            "note": "已如实标注「来源未登记」，不得据此声称厂商代表性"})
        else:
            results.append({"claim": key, "status": "REGISTERED", "text": v[:160],
                            "check": "登记核对",
                            "note": ("已登记 url，但 source_tier（public-doc / official-artifact）"
                                     "须按域名与许可人工判读，脚本不代判" if key == "url" else
                                     "字段已填写；内容真伪不在本脚本核对范围")})
    ctx = measured.get("unparsable_context")
    miss_v2 = [k for k in TEMPLATE_V2_KEYS if not f.get(k)]
    results.append({"claim": "template_v2", "check": "登记核对",
                    "status": "OK" if not miss_v2 else "MISSING",
                    "note": ("新模板四项齐备" if not miss_v2 else
                             f"缺 {'/'.join(miss_v2)}——旧 sidecar 未登记「是否派生 / 上游文件号 / "
                             "我方核对对象 / 核对主体」，来源等级无法升格"),
                    "missing": miss_v2})
    results.append(_cmp("rows", _leading_num(f.get("rows", "")),
                        [(measured.get("rows"), "可解析数据行")], context=ctx))
    results.append(_cmp("channels", _leading_num(f.get("channels", "")),
                        [(measured.get("channels"), "不含时间列"),
                         (measured.get("channels_total_columns"), "含时间列的全部列")], context=ctx))
    cfs = claimed_fs_hz(f.get("sampling_rate", ""))
    if cfs is not None and measured.get("fs_hz") is None and measured.get("fs_hypotheses"):
        hits = [(u, hz) for u, hz in measured["fs_hypotheses"].items()
                if abs(hz - cfs) <= 0.05 * max(cfs, 1e-9)]
        results.append({"claim": "fs_hz", "claimed": cfs, "measured": None,
                        "status": "SUPPORTED_BY_HYPOTHESIS" if len(hits) == 1 else ("CONTRADICTED" if not hits else "AMBIGUOUS"),
                        "note": (f"单位未独立核实；声称值只与 {hits[0][0]} 假设吻合 ⟹ 可作为时基单位的外部佐证"
                                 if len(hits) == 1 else "与任何单位假设都不吻合")})
    else:
        r = _cmp("fs_hz", cfs, [(measured.get("fs_hz"), "时间列差分")], context=ctx)
        us = (measured.get("unit_source") or "")
        if r.get("status") == "SUPPORTED" and us.startswith("sidecar_attested"):
            # 时基单位本身就是靠这句自述解除的，再拿 fs 去「核实」这句自述是循环论证
            r["status"] = "SUPPORTED_NON_INDEPENDENT"
            r["counts_as_verification"] = False
            r["note"] += f"；但单位来源={us}（同源互证，A-88 无独立证明力，不计入已核对 k）"
        else:
            r["counts_as_verification"] = r.get("status") == "SUPPORTED"
        results.append(r)
    # 自述哈希只从「写来自述」的字段取；verified_against/verified_by 里的哈希是**我方核对记录**，
    # 把它当自述会让"我方算出来的值"冒充"抓取方的声明"，核对就空转了（2026-10-20 补 v2 字段时踩到）。
    claim_txt = " ".join([(f.get(k) or "") for k in ("md5", "hash", "notes", "checksum")]) or \
        (sc["text"] if not any(f.get(k) for k in ("derived_from", "upstream_id",
                                                  "verified_against", "verified_by")) else "")
    rec_txt = " ".join([(f.get(k) or "") for k in ("verified_against", "verified_by")])
    hexes = {h.lower() for h in re.findall(r"\b([0-9a-f]{32})\b", claim_txt, re.I)}
    rec_hexes = {h.lower() for h in re.findall(r"\b([0-9a-f]{32})\b", rec_txt, re.I)}
    actual = ""
    if path and os.path.exists(path):
        actual = hashlib.md5(open(path, "rb").read()).hexdigest()
    if hexes:
        hit = bool(actual) and actual in hexes
        # 派生/转码产物：写 sidecar 的和生成文件的是同一只手，哈希相符只证明没转坏，
        # 不证明来自它声称的外部源（A-88 同源无证明力 + A-89 核对主体不可转借）。
        # 只看这两个会写「转换而来 / NONE」的字段——早先扫全文把「电导、电阻类派生量」
        # 这种讲物理量的话当成了「文件是派生物」，误判了一整条哈希存证。
        dv = (f.get("derived_from") or "").strip()
        der_txt = " ".join(filter(None, [f.get("original_filename") or "",
                                         f.get("format_family") or "",
                                         # 「NONE（未转换/未截断）」是**明确声明未派生**，不进关键词扫描；
                                         # 「未登记」不是——来源不明时仍按可疑派生处理。
                                         "" if re.match(r"^(NONE|无|n/?a)", dv, re.I) else dv]))
        # 「截取/截断」也是派生：DD_head.csv = 母本前 400,001 B（2026-10-20 现场核出），
        # 切片自己的哈希只证明切片没坏，不证明它来自哪个母本。
        # 但先要排除否定语境——「未截断」里就含「截断」，2026-10-20 曾据此把
        # 4152（derived_from 明写 NONE（未转换/未截断…））误判成派生产物。
        der_scan = re.sub(r"[未无非不][^，,；;。\s]{0,4}", " ", der_txt)
        derived = bool(re.search(r"转换而来|转换自|转码|派生|derived|重采样|re-?export"
                                 r"|截取|截断|truncat", der_scan, re.I)) \
            or (f.get("original_filename") is not None
                and bool(UNREGISTERED_RE.search(f["original_filename"])))
        r = {"claim": "hash", "status": "MATCHES_FILE" if hit else "UNMATCHED",
             "claimed": sorted(hexes)[:2], "measured": actual or None,
             "counts_as_verification": hit and not derived,
             "note": ("自述哈希与实体一致" if hit else
                      "与实体 md5 不符——可能声明的是母包/原始文件哈希，须人工判读，不作 SUPPORTED")
                     + ("；⚠️ 本文件为本地派生/转码产物，自述方与生成方同源，"
                        "哈希相符只说明未转坏，不构成外部来源证据，不计入已核对 k" if derived else "")}
        results.append(r)
    for r in results:
        r.setdefault("check", "实测核对")   # rows/channels/fs/hash 一律 vs 实体文件实测（A-88 已核对 k 的口径）
        r.setdefault("verified_by", "本脚本本次运行")
        r.setdefault("counts_as_verification",
                     r["status"] in ("SUPPORTED", "MATCHES_FILE"))
    return results


def claims_ledger(claims):
    """A-88 口径：已核对 k / 应核对 n，只统计与实体文件比过的数值/哈希类自述。

    登记类字段（url/publisher/license/…）只证明 sidecar 里写了这句话，不构成核对。
    """
    num = [c for c in claims if c.get("check") == "实测核对"]
    k = sum(1 for c in num if c.get("counts_as_verification"))
    return {"verified": k, "total": len(num),
            "excluded_same_source": sum(1 for c in num if c.get("status") in
                                        ("SUPPORTED", "MATCHES_FILE", "SUPPORTED_NON_INDEPENDENT")
                                        and not c.get("counts_as_verification")),
            "contradicted": sum(1 for c in num if c.get("status") == "CONTRADICTED"),
            "unverifiable": sum(1 for c in num if c.get("status") in
                                ("UNVERIFIABLE", "UNMATCHED")),
            "not_registered": sum(1 for c in claims if c.get("status") == "NOT_REGISTERED"),
            "missing_fields": [c["claim"] for c in claims
                               if c.get("status") == "MISSING" and c["claim"] != "template_v2"],
            "sidecar_absent": any(c.get("status") == "ABSENT" for c in claims)}


# ---------------------------------------------------------------- 逐文件校验

def validate(path):
    size = os.path.getsize(path)
    rep = {"file": os.path.basename(path), "path": path.replace(os.sep, "/"), "bytes": size,
           "sha256": sha256_bytes(path), "kind": None, "verdict": None, "redlines_fired": [],
           "notes": []}
    ext = os.path.splitext(path)[1].lower()

    if ext in (".zip", ".7z", ".gz", ".rar"):
        rep["kind"] = "archive"
        try:
            with zipfile.ZipFile(path) as z:
                rep["archive_listing"] = [(i.filename, i.file_size) for i in z.infolist()][:200]
                rep["notes"].append("只列目录，不解压、不执行任何内容")
        except Exception as e:
            rep["notes"].append(f"压缩包不可读: {e}")
        rep["verdict"] = "needs_unpack_to_assess"
        return rep

    # `.tab` 是制表符分隔的常见变体（DaRUS/ISW 进给轴数据集即用此后缀，2026-10-20 实见），
    # 早先没列入可解析后缀，把 2.8 MB 的真 fe 候选整个当非波形存证跳过了。
    if ext not in (".csv", ".tsv", ".tab", ".dat", ".txt", ".asc", ".log"):
        rep["kind"] = "ancillary"          # 手册摘录/XML/MATLAB 脚本等：不判波形，仅存证 + 泄漏扫描
        rep["verdict"] = "not_a_waveform"
        raw = open(path, "rb").read()
        text, enc = decode(raw)
        rep["encoding"] = enc
        rep["leaks"] = scan_leaks(text)
        return rep

    rep["kind"] = "waveform_candidate"
    meta, layout, chans, tc, n_rows, flags = parse_table(path)
    sc = read_sidecar_fields(path + ".source.txt")
    claim_fs = claimed_fs_hz(sc["fields"].get("sampling_rate", "")) if sc else None
    rep["format"] = {"layout": layout, "encoding": meta.get("encoding"),
                     "delimiter": meta.get("delimiter"), "header_rows": meta.get("header_rows"),
                     "line_ending": flags.get("line_ending"), "bom": flags.get("bom"),
                     "decimal_comma": flags.get("decimal_comma"),
                     "looks_like_html": flags.get("looks_like_html"),
                     "size_truncated_at_read": flags.get("size_truncated_at_read")}
    rep["n_file_lines"] = flags.get("n_nonempty_lines")
    rep["n_rows_shape_mismatch"] = flags.get("n_rows_shape_mismatch")
    rep["n_blank_rows_skipped"] = flags.get("n_blank_rows_skipped")
    rep["n_total_columns"] = (len(chans) + (1 if tc.get("col") is not None else 0))
    if flags.get("row_cap_hit"):
        rep["notes"].append(f"数据行数超过 ROW_CAP={flags.get('row_cap')}，已截断计数（显式报告，不静默）")
    rep["n_data_rows"] = n_rows
    rep["bytes_per_row"] = round(size / n_rows, 1) if n_rows else None
    rep["header_meta"] = {k: v for k, v in meta.get("kv_meta", {}).items()}
    if flags.get("looks_like_html"):
        rep["redlines_fired"] = ["文件是 HTML 页面而非波形导出（下载得到的是网页正文）"]
        rep["verdict"] = "reject_html_not_data"
        return rep
    if layout == "unparsed":
        rep["redlines_fired"] = ["未找到可解析的数据块（表头/列数无法定位）"]
        rep["verdict"] = "reject_unparsable"
        rep["leaks"] = scan_leaks(io.open(path, "r", encoding="utf-8", errors="replace").read())
        # 解析不了也要把自述核对做完：厂商表头族的 rows/channels/sampling_rate
        # 恰恰是这一族能否升格 public-doc 的关键证据，不能因为 layout=unparsed 就跳过。
        rep["sidecar_claims"] = check_claims(sc, {"unparsable_context":
                                                  f"物理非空行 {n_rows}（含表头，不等于数据行数）"}, path)
        rep["claims_ledger"] = claims_ledger(rep["sidecar_claims"])
        return rep

    tb, _ = analyze_time(tc, n_rows, {**meta.get("kv_meta", {}),
                                      **({"declared_period_raw": meta.get("declared_period_raw")}
                                         if meta.get("declared_period_raw") else {})}, layout, claim_fs)
    fs = tb.get("fs_hz")
    for c in chans:
        c["feat"] = analyze_channel(c["series"], fs, tc.get("series"))
    rep["timebase"] = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in tb.items()}
    rep["channels"] = [{"raw_name": c["raw_name"], "col": c["col"], "unit": c["unit"],
                        "quantity": c["quantity"], "direction": c["direction"],
                        "is_diff": c["is_diff"], "axis_tag": c.get("axis_tag"),
                        "canonical": c["canonical"],
                        "stats": {k: (round(v, 6) if isinstance(v, float) else v)
                                  for k, v in c["feat"].items() if k in
                                  ("min", "max", "mean", "std", "span", "distinct", "rms",
                                   "crest_factor", "nan_ratio", "n_move_segments",
                                   "nonzero_motion_fraction", "n_direction_changes",
                                   "move_time_s", "is_constant", "sine_like", "near_linear_ramp",
                                   "max_segment_len", "is_dynamic", "dyn_snr", "is_enumerated",
                                   "status")}}
                       for c in chans]
    rep["fe_identity"] = fe_identity(chans)

    fired, meas = redlines(tb, chans, n_rows)
    rep["measured"] = {k: (round(v, 6) if isinstance(v, float) else v) for k, v in meas.items()}
    rep["redlines_fired"] = fired
    rep["soft_degradations"] = soft_degradations(chans)
    if size and n_rows:
        bpc = size / n_rows / max(len(chans) + 1, 1)
        rep["bytes_per_cell"] = round(bpc, 1)
        if bpc > 40:
            rep["notes"].append(f"每单元格约 {bpc:.0f} 字节——列数/行数与体积不匹配（自述行数的典型破绽）")
        elif bpc < 1.5:
            rep["notes"].append(f"每单元格约 {bpc:.2f} 字节——不可能容纳这些通道，疑似截断或空填充")
    wc_r = tb.get("wallclock_vs_measured_ratio") if tb else None
    if wc_r is not None and abs(wc_r - 1.0) > 0.05:
        rep["notes"].append(
            f"表头挂钟时长与时间列跨度不符（比值 {wc_r:.3f}）——"
            f"{'文件被截断（只含前一部分采样）' if wc_r > 1 else '时间列单位推断有误或存在丢帧'}")
    rep["verdict"] = "reject" if fired else "accept"
    rep["leaks"] = scan_leaks("\n".join(str(x) for x in rep["header_meta"].values()))
    rep["sidecar_claims"] = check_claims(sc, {
        "rows": None if flags.get("size_truncated_at_read") else n_rows,
        "channels": len(chans),
        "channels_total_columns": rep["n_total_columns"],
        "fs_hz": tb.get("fs_hz"), "fs_hypotheses": tb.get("fs_hypotheses_hz"),
        "unit_source": tb.get("unit_source"),
        "unparsable_context": ("读取仅前 64MB，行数被截断，不可作实测口径"
                               if flags.get("size_truncated_at_read") else None)}, path)
    rep["claims_ledger"] = claims_ledger(rep["sidecar_claims"])
    return rep


def scan_leaks(text):
    out = []
    for name, pat in LEAK_PATTERNS:
        hits = pat.findall(text)
        if hits:
            first = hits[0]
            if isinstance(first, tuple):
                first = first[0]
            out.append({"pattern": name, "count": len(hits), "sample": str(first)[:100],
                        "action_required": "发布前脱敏"})
    return out


# ---------------------------------------------------------------- 负向测试（检查 22）

def synth_good(path, n=3000, fs=1000.0):
    """梯形轮廓的人造正常样本：三段往复运动 + 稳态噪声，供负向测试当基准。"""
    names = ["SampleTime[ms]", "pos_cmd[mm]", "pos_fb[mm]", "fe[mm]",
             "vel_fb[mm/s]", "cur_q[A]", "bEnable"]
    cmd, fb = [], []
    for i in range(n):
        x = i / n
        c = (x * 300) if x < 1 / 3 else (100 if x < 0.5 else 100 - (x - 0.5) * 200)
        cmd.append(c)
        fb.append(c + 0.02 * math.sin(2 * math.pi * 50 * i / fs) + 0.001 * ((-1) ** i))
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(names) + "\n")
        for i in range(n):
            vel = (fb[i] - fb[i - 1]) * fs if i else 0.0
            f.write("\t".join(f"{v:.6g}" for v in
                              [i / fs * 1000, cmd[i], fb[i], cmd[i] - fb[i], vel,
                               2.5 + 0.2 * math.sin(2 * math.pi * 3 * i / fs),
                               1 if 0.05 < x_frac(i, n) < 0.95 else 0]) + "\n")


def x_frac(i, n):
    return i / n


def selftest(tmp=".tmp_selftest"):
    os.makedirs(tmp, exist_ok=True)
    cases = []
    p = lambda n: os.path.join(tmp, n)

    synth_good(p("good.tsv"))
    cases.append(("good.tsv", "accept", []))
    synth_good(p("short.tsv"), n=500)
    cases.append(("short.tsv", "reject", ["n_samples"]))
    synth_good(p("static.tsv"), n=3000)
    with io.open(p("static.tsv"), "w", encoding="utf-8", newline="\n") as f:  # 恒值通道
        f.write("SampleTime[ms]\tpos_cmd[mm]\tpos_fb[mm]\tfe[mm]\tvel_fb\tcur_q\n")
        for i in range(3000):
            f.write(f"{i}\t10\t10\t0\t0\t1\n")
    cases.append(("static.tsv", "reject", ["无动态分段"]))
    synth_good(p("jitter.tsv"))
    lines = io.open(p("jitter.tsv"), encoding="utf-8").read().split("\n")
    fixed = []
    for i, ln in enumerate(lines):
        if i and ln.strip():
            c = ln.split("\t")
            try:
                c[0] = f"{float(c[0]) * (1 + (0.9 if i % 2 else -0.9)):.4f}"
            except ValueError:
                pass
            fixed.append("\t".join(c))
        else:
            fixed.append(ln)
    io.open(p("jitter.tsv"), "w", encoding="utf-8", newline="\n").write("\n".join(fixed))
    cases.append(("jitter.tsv", "reject", ["dt_jitter_ratio"]))
    synth_good(p("nan.tsv"))
    l = io.open(p("nan.tsv"), encoding="utf-8").read().split("\n")
    out = []
    for i, ln in enumerate(l):
        if i and ln.strip():
            c = ln.split("\t")
            if i % 2:
                c[2] = "NaN"
            out.append("\t".join(c))
        else:
            out.append(ln)
    io.open(p("nan.tsv"), "w", encoding="utf-8", newline="\n").write("\n".join(out))
    cases.append(("nan.tsv", "reject", ["nan_ratio"]))
    io.open(p("nomo.tsv"), "w", encoding="utf-8", newline="\n").write(
        "SampleTime[ms]\tbEnable\tbLimit\n" + "".join(f"{i}\t1\t0\n" for i in range(3000)))
    cases.append(("nomo.tsv", "reject", ["cur_q/vel_fb/fe 全缺"]))
    io.open(p("page.csv"), "w", encoding="utf-8").write("<!DOCTYPE html>\n<html><head><title>下载</title></head></html>")
    cases.append(("page.csv", "reject_html_not_data", ["HTML"]))
    # 数值型表头行陷阱：TwinCAT 的 SymbolName/NetID/Port 三行里 Port 全是数字，
    # 曾被当作第一条数据（每个通道首值都成 851.0，min/max/std/恒等式全被带偏）——本用例锁死该回归
    with io.open(p("hdr.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("Name\tpos_cmd[mm]\tName\tpos_fb[mm]\tName\tfe[mm]\tName\tvel_fb[mm/s]\tName\tcur_q[A]\tName\tbEnable\n")
        f.write("SampleTime[ms]\t1\tSampleTime[ms]\t1\tSampleTime[ms]\t1\tSampleTime[ms]\t1\tSampleTime[ms]\t1\tSampleTime[ms]\t1\n")
        f.write("Port\t851\tPort\t851\tPort\t851\tPort\t851\tPort\t851\tPort\t851\n")
        f.write("\n")
        for i in range(3000):
            x = 300.0 * i / 1000 if i < 1000 else (300.0 if i < 2000 else 600.0 - 300.0 * i / 1000)
            fb = x + 0.02 * math.sin(2 * math.pi * 50 * i / 1000)
            f.write("\t".join(f"{v:.6g}" for v in [i, x, fb, x - fb, 0.3, 2.5, 1]) + "\n")
    cases.append(("hdr.tsv", "accept", []))
    io.open(p("short_dur.tsv"), "w", encoding="utf-8", newline="\n").write(
        "SampleTime[ms]\tpos_cmd\tpos_fb\tfe\tvel_fb\tcur_q\n" +
        "".join(f"{i * 0.05:.3f}\t{math.sin(i)}\t{math.sin(i)}\t0\t{math.cos(i)}\t1\n" for i in range(5000)))
    cases.append(("short_dur.tsv", "reject", ["有效时长"]))
    # 时间列单位无来源（列名不带单位、又不是 TwinCAT 交错布局）：第一版硬按 ms 假设，
    # 把 500 Hz / 6 s 的秒制文件读成 0.006 s 而误开「有效时长<0.5s」硬拒。
    # 现在只列 us/ms/s 三种假设、不开时长红线（KB2 §5.2 不用默认值冒充）。
    with io.open(p("unit_amb.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("tout\tpos_cmd\tpos_fb\tfe\tvel_fb\tcur_q\n")
        for i in range(3000):
            t = i * 0.002
            x = 3.0 * math.sin(2 * math.pi * 0.5 * t)
            fb = x - 0.01 * math.sin(2 * math.pi * 5 * t)
            f.write("\t".join(f"{v:.6g}" for v in [t, x, fb, x - fb, 0.4, 1.2]) + "\n")
    cases.append(("unit_amb.tsv", "accept", []))
    # 命名族缺口 ≠ 数据缺失：整套列名都不认识时，红线只能记「未识别」，不能宣称数据里没有
    # cur_q/vel_fb/fe（我们没有数据集文档作证据，A-88 同源无证明力）。
    io.open(p("unnamed.tsv"), "w", encoding="utf-8", newline="\n").write(
        "tout\ta1\ta2\ta3\ta4\ta5\n" +
        "".join("\t".join(f"{v:.6g}" for v in [i * 0.002, 3 * math.sin(0.01 * i),
                                               2 * math.sin(0.01 * i + 0.3), 0.01 * math.cos(0.05 * i),
                                               0.4, 1.2]) + "\n" for i in range(3000)))
    cases.append(("unnamed.tsv", "reject", ["未识别"]))

    # R-3（KB2 §4.12 / KB7 台账 15/16 行）：ISO-8601 文本时间列——6114 两 CSV 的 t 列形态，
    # 时基解析出来即正常；严格单调门原样作用于转换后的序列。
    def _iso(ms):
        s = datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return f"{s}.{int(ms % 1000):03d}000+00:00"
    for fn_dst, back_at in (("iso_good.tsv", None), ("iso_back.tsv", 10)):
        lines = io.open(p("good.tsv"), encoding="utf-8").read().split("\n")
        out = []
        for i, ln in enumerate(lines):
            if not ln.strip():
                out.append(ln)
                continue
            c = ln.split("\t")
            if i == 0:
                c[0] = "t"
            else:
                ms = float(c[0])
                if back_at and i == back_at:
                    ms -= 60000.0                  # 第 10 行整体拨回 1 分钟前（非单调注入）
                c[0] = _iso(ms)
            out.append("\t".join(c))
        io.open(p(fn_dst), "w", encoding="utf-8", newline="\n").write("\n".join(out))
    cases.append(("iso_good.tsv", "accept", []))
    cases.append(("iso_back.tsv", "reject", ["时基非严格单调"]))

    # R-6（KB7 台账 20 行 `2563_LDD_*.csv` 形态）：分号分隔 + 逗号小数。取值路径一直认逗号小数，
    # 缺的只是布局判定（`is_num`）——此前整份判 unparsable，「时长 0.128 s」没有工具载体。
    # 每格一律 6 位小数（与 2563 实体文件同形态：`0,000000;19,999996;-20,172794`）
    good_lines = io.open(p("good.tsv"), encoding="utf-8").read().split("\n")
    with io.open(p("comma_dec.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        for ln in good_lines:
            if not ln.strip():
                continue
            fh.write(";".join(f"{fnum(c):.6f}".replace(".", ",") if is_num(c.strip()) else c
                              for c in ln.split("\t")) + "\n")
    cases.append(("comma_dec.tsv", "accept", []))
    # R-7（KB7 台账 17 行 `6114_ObserverTestSet.tab` 形态）：没有一列像时间。
    # 此前 `strictly_monotonic` 缺省 False ⟹ 拒因写成「时基非严格单调」，把"无从判定"
    # 报成"判定不合格"（C1 §time_bases ⑤ 对 event 栅格明令禁止这种写法）。
    with io.open(p("timeguess.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("v_des\ta_des\tj_des\tx_des\tx_act\n")
        for k in range(3000):
            fh.write("\t".join(f"{v:.6g}" for v in [
                math.sin(0.01 * k), math.cos(0.01 * k), math.sin(0.03 * k),
                0.1 * math.sin(0.005 * k), 0.1 * math.sin(0.005 * k + 0.01)]) + "\n")
    # 连带的第二种形态：一列都不递增（`ObserverTestSet.tab` 是这种）⟹ 走 no_time_column 分支
    with io.open(p("notimebase.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("v_des\ta_des\tj_des\tx_des\tx_act\n")
        for k in range(3000):
            fh.write("\t".join(f"{v:.6g}" for v in [
                math.sin(0.5 * k), math.cos(0.5 * k), math.sin(0.7 * k),
                0.1 * math.sin(0.4 * k), 0.1 * math.sin(0.4 * k + 0.01)]) + "\n")

    print("负向测试（KB0 §6 检查 22）：每条红线须真的开火，否则该检查没有检测力")
    fails = 0
    for fn, want_v, want_any in cases:
        rep = validate(p(fn))
        ok_v = rep["verdict"] == want_v
        joined = " | ".join(rep["redlines_fired"])
        ok_r = all(k in joined for k in want_any)
        ok = ok_v and ok_r
        fails += 0 if ok else 1
        print(f"  {'PASS' if ok else 'FAIL'}  {fn:14s} verdict={rep['verdict']:20s} "
              f"红线={rep['redlines_fired'] if rep['redlines_fired'] else '（未开火）'}")
        if not ok:
            print(f"        期望 verdict={want_v} 期望命中={want_any}")
    print("\n回归断言（本脚本自己踩过的坑，逐条锁死，不只验 verdict）")
    reg = validate(p("hdr.tsv"))
    polluted = [c["raw_name"] for c in reg.get("channels", [])
                if c["stats"].get("min") == 851.0 or c["stats"].get("max") == 851.0]
    bool_ch = [c for c in reg.get("channels", []) if c["canonical"] == "io"]
    bool_ok = all((c["stats"].get("max") or 0) <= 1 for c in bool_ch)
    ok = not polluted and bool_ok and reg["verdict"] == "accept"
    fails += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  数值型表头行(Port=851)未混入数据"
          f"（污染通道={polluted}，布尔通道 max={[c['stats'].get('max') for c in bool_ch]}）")

    reg2 = validate(p("unit_amb.tsv"))
    tb2 = reg2.get("timebase") or {}
    hyp = tb2.get("duration_hypotheses_s") or {}
    ok2 = (tb2.get("duration_s") is None and tb2.get("unit_ambiguous")
           and not any("有效时长" in x for x in reg2["redlines_fired"])
           and abs(hyp.get("ms", 1) - 0.005998) < 1e-3 and abs(hyp.get("s", 0) - 5.998) < 1e-3)
    fails += 0 if ok2 else 1
    print(f"  {'PASS' if ok2 else 'FAIL'}  时间列单位无来源时不开时长红线"
          f"（duration_s={tb2.get('duration_s')}，假设 ms={hyp.get('ms')}s / s={hyp.get('s')}s，"
          f"红线={reg2['redlines_fired']}）")

    # R-7 回归断言：无时间列只报"时基不可得"，不得冒充单调性结论（拒因须指向实测到的缺陷）。
    # 两种形态分开锁：启发式抢列（身份未证实）与真的没有一列可用。
    reg3 = validate(p("timeguess.tsv"))
    tb3 = reg3.get("timebase") or {}
    fired3 = " | ".join(reg3["redlines_fired"])
    ok3 = (tb3.get("time_col_source") == "monotonic_heuristic"
           and "无时间列可解析" in fired3 and "非严格单调" not in fired3
           and "dt_jitter_ratio" not in fired3)
    fails += 0 if ok3 else 1
    print(f"  {'PASS' if ok3 else 'FAIL'}  递增启发抢列不冒充「时基非严格单调」"
          f"（source={tb3.get('time_col_source')}，红线={reg3['redlines_fired']}）")

    reg4 = validate(p("notimebase.tsv"))
    tb4 = reg4.get("timebase") or {}
    fired4 = " | ".join(reg4["redlines_fired"])
    ok4 = (tb4.get("status") == "no_time_column" and "时基不可得" in fired4
           and "非严格单调" not in fired4 and "无时间列" in unitize(tb4))
    fails += 0 if ok4 else 1
    print(f"  {'PASS' if ok4 else 'FAIL'}  无时基列判「时基不可得」而非单调性不合格"
          f"（status={tb4.get('status')}，红线={reg4['redlines_fired']}）")

    # 名实对齐：plain_matrix 的表头含时间列，通道名必须按列号取。
    # 反例样本把时间列放在首位（最常见形态），错位一列时末列还会被静悄悄丢掉。
    with io.open(p("align.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("t\tpos_cmd\tpos_fb\tfe_pos\n")
        for k in range(3000):
            fh.write("%.6f\t%.6f\t%.6f\t%.6f\n" % (k * 0.001, k * 0.001, k * 0.001 + 0.5, 0.5))
    reg4 = validate(p("align.tsv"))
    got4 = [(c["raw_name"], c["col"], c["stats"]["max"]) for c in reg4.get("channels", [])]
    want4 = [("pos_cmd", 1, 2.999), ("pos_fb", 2, 3.499), ("fe_pos", 3, 0.5)]
    ok4 = len(got4) == len(want4) and all(
        n == w and c == wc and abs(m - wm) < 5e-4 for (n, c, m), (w, wc, wm) in zip(got4, want4))
    fails += 0 if ok4 else 1
    print(f"  {'PASS' if ok4 else 'FAIL'}  通道名按列号对齐、时间列在首位时不错位不丢列"
          f"（实得={got4}，期望={want4}）")

    # R-5（KB2 §4.12 / VERIFICATION §8.7）的三处实测误报必须不再命中；
    # 同批锁死 token 化不得弄丢的既有正确判定（x_Ltar 的方向来自粘连指令后缀）。
    r5_bad = {n: guess_role_from_name(n) for n in ("OilLevel_L", "FailureRate", "Timestamp")
              if guess_role_from_name(n) != (None, None, False)}
    r5_keep = {n: guess_role_from_name(n) for n, want in (
        ("x_Ltar", ("pos", "cmd", False)), ("v_L", ("vel", "fb", False)),
        ("f_diff", ("force", "na", True)), ("e_x", ("pos", "fb", True)),
        ("dVelocity_test_tar", ("vel", "cmd", False))) if guess_role_from_name(n) != want}
    ok5 = not r5_bad and not r5_keep
    fails += 0 if ok5 else 1
    print(f"  {'PASS' if ok5 else 'FAIL'}  R-5 token 判定：三处子串误报已消除、既有判定未弄丢"
          f"（仍误报={r5_bad}，被弄丢={r5_keep}）")

    # R-3 解析层断言：ISO 时基单位由格式定死为秒（不靠 us/ms/s 假设、不靠 sidecar 解除歧义）
    tb5 = (validate(p("iso_good.tsv")).get("timebase") or {})
    ok6 = (tb5.get("unit_source") == "iso8601_text:epoch_seconds"
           and tb5.get("strictly_monotonic") and abs((tb5.get("fs_hz") or 0) - 1000.0) < 1.0)
    fails += 0 if ok6 else 1
    print(f"  {'PASS' if ok6 else 'FAIL'}  R-3 ISO 时基单位=epoch秒"
          f"（unit_source={tb5.get('unit_source')} fs={tb5.get('fs_hz')} "
          f"单调={tb5.get('strictly_monotonic')}）")

    print("\n自述核对器断言（KB0 §6 检查 22：核对逻辑自己也要有负向测试）")
    reg3 = 0

    def claim_case(name, data_fn, sidecar, expects, note):
        nonlocal reg3
        sc_path = p(data_fn + ".source.txt")
        io.open(sc_path, "w", encoding="utf-8", newline="\n").write(sidecar)
        rep = validate(p(data_fn))
        got = {c["claim"]: c["status"] for c in rep.get("sidecar_claims", [])}
        bad = {k: (v, got.get(k)) for k, v in expects.items() if got.get(k) != v}
        reg3 += 0 if not bad else 1
        print(f"  {'PASS' if not bad else 'FAIL'}  {name} — {note}"
              + (f" 不符项={bad} 实得={got}" if bad else ""))
        os.remove(sc_path)

    good_md5 = hashlib.md5(open(p("good.tsv"), "rb").read()).hexdigest()
    claim_case("true", "good.tsv",
               "url: https://localhost/synthetic\ntitle: 合成基准\n"
               "rows: 3000（数据行，不含表头）\nchannels: 6（不含时间列）\n"
               "sampling_rate: 1000 Hz\nlicense: 来源未登记\n"
               f"md5: {good_md5}\n",
               {"rows": "SUPPORTED", "channels": "SUPPORTED", "fs_hz": "SUPPORTED",
                "license": "NOT_REGISTERED", "publisher": "MISSING", "hash": "MATCHES_FILE",
                "url": "REGISTERED"},
               "如实自述须全判 SUPPORTED/REGISTERED，缺项判 MISSING，「来源未登记」不得当作已登记")
    claim_case("false", "good.tsv",
               "url: https://localhost/synthetic\nrows: 500\nchannels: 11\n"
               "sampling_rate: 100 Hz\nmd5: 00000000000000000000000000000000\n",
               {"rows": "CONTRADICTED", "channels": "CONTRADICTED", "fs_hz": "CONTRADICTED",
                "hash": "UNMATCHED"},
               "错报的 rows/channels/fs/哈希必须被实体文件证伪（否则核对器没有检测力）")
    claim_case("attest", "unit_amb.tsv",
               "url: https://localhost/synthetic\nsampling_rate: 500 Hz\n",
               {"fs_hz": "SUPPORTED_NON_INDEPENDENT"},
               "单位靠这句自述解除 ⟹ fs 再吻合也只算同源互证，不判独立 SUPPORTED（A-88）")
    amb_sc = p("unit_amb.tsv.source.txt")
    io.open(amb_sc, "w", encoding="utf-8", newline="\n").write(
        "url: https://localhost/synthetic\nsampling_rate: 500 Hz\n")
    amb = validate(p("unit_amb.tsv"))
    os.remove(amb_sc)
    tb_amb = amb["timebase"]
    ok = tb_amb.get("unit_source") == "sidecar_attested:s" and abs(
        (tb_amb.get("fs_hz") or 0) - 500) < 1e-6 and amb["verdict"] == "accept"
    reg3 += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  attest 后时基单位来源={tb_amb.get('unit_source')} "
          f"fs={tb_amb.get('fs_hz')} verdict={amb['verdict']}")

    # 列数不符的行剔除后必须计入 n_rows_shape_mismatch，并在 rows 实测口径里说清
    with io.open(p("ragged.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("SampleTime[ms]\tpos_cmd[mm]\tpos_fb[mm]\tfe[mm]\tvel_fb\tcur_q\n")
        for i in range(3000):
            x = 300.0 * i / 3000
            f.write("\t".join(f"{v:.6g}" for v in [i, x, x - 0.01, 0.01, 0.3, 2.5]) + "\n")
        for _ in range(5):
            f.write("EOF\ttrailer\n")
    io.open(p("ragged.tsv.source.txt"), "w", encoding="utf-8", newline="\n").write(
        "url: https://localhost/synthetic\nrows: 3000\n")
    rr = validate(p("ragged.tsv"))
    st = {c["claim"]: c["status"] for c in rr["sidecar_claims"]}
    ok = rr.get("n_rows_shape_mismatch") == 5 and rr.get("n_data_rows") == 3000 \
        and st.get("rows") == "SUPPORTED" and rr.get("n_blank_rows_skipped") == 1
    reg3 += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  尾行/异形行列剔除可计数"
          f"（shape_mismatch={rr.get('n_rows_shape_mismatch')}，空行={rr.get('n_blank_rows_skipped')}，"
          f"数据行={rr.get('n_data_rows')}，rows 核对={st.get('rows')}）")
    os.remove(p("ragged.tsv.source.txt"))

    no_sc = validate(p("good.tsv"))
    led = no_sc.get("claims_ledger") or {}
    ok = led.get("sidecar_absent") and no_sc["sidecar_claims"][0]["status"] == "ABSENT"
    reg3 += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  无 sidecar 时账本记 ABSENT 而非默认通过"
          f"（ledger={led}）")

    # 派生/转码产物：文件与 sidecar 同一只手写出，哈希相符也不构成外部来源证据（A-88 同源）
    d_md5 = hashlib.md5(open(p("good.tsv"), "rb").read()).hexdigest()
    sc_d = p("good.tsv.source.txt")
    io.open(sc_d, "w", encoding="utf-8", newline="\n").write(
        "url: https://china.scidb.cn/download?fileId=xxx\noriginal_filename: NONE"
        "（由 Controller1Periodic.mat 转换而来，非原始导出）\n"
        f"rows: 3000\nmd5: {d_md5}\n")
    rd = validate(p("good.tsv"))
    # 反例：正文里出现「电导、电阻类派生量」这类讲物理量的话，不能被当成「文件是派生物」
    io.open(sc_d, "w", encoding="utf-8", newline="\n").write(
        "url: https://cdn.jsdelivr.net/gh/x/y@example.csv\noriginal_filename: example.csv\n"
        "variable_semantics: G / R = 电导、电阻类派生量\n"
        f"md5: {d_md5}\n")
    rp = validate(p("good.tsv"))
    os.remove(sc_d)
    hp = [c for c in rp["sidecar_claims"] if c["claim"] == "hash"][0]
    h = [c for c in rd["sidecar_claims"] if c["claim"] == "hash"][0]
    led_d = rd["claims_ledger"]
    ok = h["status"] == "MATCHES_FILE" and h["counts_as_verification"] is False \
        and led_d["verified"] == 1 and led_d["excluded_same_source"] == 1 \
        and hp["counts_as_verification"] is True
    reg3 += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  同源派生文件的哈希相符不计入 k，"
          f"正文提「派生量」的原始下载文件仍计入"
          f"（派生={h['counts_as_verification']} 反例={hp['counts_as_verification']} ledger="
          f"verified={led_d['verified']}/total={led_d['total']} 同源剔除={led_d['excluded_same_source']}）")

    # 截断派生 vs 否定语境：DD_head.csv 的真实教训（2026-10-20）。
    # ① derived_from 明写「前 N 字节截断」⟹ 切片哈希相符也不算外部来源证据；
    # ② derived_from 写「NONE（未转换/未截断…）」⟹ 是否定语境，不得误判为派生。
    io.open(sc_d, "w", encoding="utf-8", newline="\n").write(
        "url: https://darus.uni-stuttgart.de/api/access/datafile/394008\n"
        "original_filename: Export 10.csv\n"
        "derived_from: 母本 dataFile 394008 的前 400,001 字节截断（head -c 400001）\n"
        f"md5: {d_md5}\n")
    rt = validate(p("good.tsv"))
    io.open(sc_d, "w", encoding="utf-8", newline="\n").write(
        "url: https://darus.uni-stuttgart.de/api/access/datafile/290225\n"
        "original_filename: Sine_0_output_00.txt\n"
        f"derived_from: NONE（未转换/未截断，服务器对象逐字节落地）\nmd5: {d_md5}\n")
    rn = validate(p("good.tsv"))
    os.remove(sc_d)
    ht = [c for c in rt["sidecar_claims"] if c["claim"] == "hash"][0]
    hn = [c for c in rn["sidecar_claims"] if c["claim"] == "hash"][0]
    ok = ht["counts_as_verification"] is False and hn["counts_as_verification"] is True
    reg3 += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  「截断」派生的哈希不计入 k，"
          f"而明写「NONE（未转换/未截断）」的原始下载必须计入（否定语境不是派生）"
          f"（截断={ht['counts_as_verification']} 未截断={hn['counts_as_verification']}）")

    total = len(cases) + 7 + 8
    print(f"负向测试：{total - fails - reg3} 通过 / {total} 执行 / {fails + reg3} 失败")
    return fails + reg3


# ---------------------------------------------------------------- 汇总输出

def unitize(tb):
    if not tb:
        return "时基不可用"
    if tb.get("status") == "no_time_column":
        return "无时间列（fs/时长/抖动/单调一律不作结论，R-7）"
    head_prefix = ("递增启发列（身份未证实）："
                   if tb.get("time_col_source") == "monotonic_heuristic" else "")
    fs = tb.get("fs_hz")
    head = (head_prefix + (f"fs实测={fs:.1f}Hz" if fs else "fs实测=单位未定")) + \
           (f" fs声明={tb['declared_fs_hz']:.1f}Hz" if tb.get("declared_fs_hz") else "") + \
           (f" fs挂钟={tb['fs_from_wallclock']:.1f}Hz" if tb.get("fs_from_wallclock") else "") + \
           (f" 抖动={tb.get('dt_jitter_ratio', float('nan')):.3f}" if tb.get("dt_jitter_ratio") is not None else "") + \
           (f" 时长={tb.get('duration_s', float('nan')):.3f}s" if tb.get("duration_s") is not None else "") + \
           (f" 单调={'Y' if tb.get('strictly_monotonic') else 'N'}")
    if tb.get("duration_s") is None and tb.get("duration_hypotheses_s"):
        h = tb["duration_hypotheses_s"]
        med = tb.get("dt_median") or 0.0
        fs_part = ("，fs 相应为 " + " / ".join(f"{1.0/(med*u):.4g}Hz" for u in (1e-6, 1e-3, 1e0))
                   if med else "")
        head += (f"\n        时间列单位未定（不猜，红线不开）：dt中位={med:g} → "
                 f"us 假设时长={h['us']:.6g}s / ms 假设={h['ms']:.6g}s / s 假设={h['s']:.6g}s"
                 f"{fs_part}")
    elif tb.get("unit_source"):
        head += f" 单位来源={tb['unit_source']}"
    return head


def render_txt(reports):
    L = []
    L.append("数据文件批量校验报告（初筛：时基 / 通道 / 运动特征）")
    L.append("判据出处：KB2 §5.1 六条硬拒 + C1 数据质量红线；抖动口径同 C2 quality.dt_jitter_ratio")
    L.append("自述一律不采信：.source.txt 声明值逐条 vs 实测（A-88/A-89）")
    L.append("=" * 108)
    for r in reports:
        L.append(f"\n◆ {r['file']}   [{r['kind']}]   verdict={r['verdict']}")
        L.append(f"  大小={r['bytes']:,} B  sha256={r['sha256'][:16]}…")
        if r["kind"] == "ancillary":
            L.append(f"  非波形存证文件（编码 {r.get('encoding')}）；泄漏扫描 {len(r.get('leaks', []))} 类命中")
            for lk in r.get("leaks", []):
                L.append(f"    泄漏[{lk['pattern']}] ×{lk['count']} 样例={lk['sample']}")
            continue
        if r["kind"] == "archive":
            L.append(f"  压缩包：仅列目录 {len(r.get('archive_listing', []))} 条，未解压未执行")
            continue
        f = r.get("format", {})
        L.append(f"  格式：layout={f.get('layout')} 分隔={f.get('delimiter')} 编码={f.get('encoding')} "
                 f"表头行={f.get('header_rows')} 换行={f.get('line_ending')} "
                 f"BOM={f.get('bom')} 小数逗号={f.get('decimal_comma')}")
        unp = f.get("layout") == "unparsed"
        L.append(f"  行数：{'物理非空行（布局未解析，无法区分数据行）' if unp else '数据'} "
                 f"{r.get('n_data_rows')} 行，每行 {r.get('bytes_per_row')} B，"
                 f"每单元格 {r.get('bytes_per_cell')} B")
        if r.get("n_rows_shape_mismatch"):
            L.append(f"        物理非空行 {r.get('n_file_lines')} 行，其中列数与主形状不符而剔除 "
                     f"{r['n_rows_shape_mismatch']} 行")
        tb = r.get("timebase")
        L.append("  时基：" + unitize(tb))
        if tb and tb.get("wallclock_duration_s"):
            L.append(f"        挂钟 {tb['wallclock_duration_s']:.3f}s vs 时间列 {tb['duration_s']:.3f}s "
                     f"比值={tb['wallclock_vs_measured_ratio']:.4f}")
        chs = r.get("channels", [])
        L.append(f"  通道：{len(chs)} 列，C1 规范名 → " +
                 ", ".join(f"{c['raw_name']}→{c['canonical'] or '未映射'}"
                           f"[{c.get('axis_tag')}]({(c['stats'].get('span') or 0):.3g})"
                           for c in chs[:10]) +
                 (" …" if len(chs) > 10 else ""))
        unmapped = [c["raw_name"] for c in chs if not c["canonical"]]
        if unmapped:
            L.append(f"        未映射（不猜语义，KB2 §三）：{unmapped[:8]}")
        cons = [c["raw_name"] for c in chs if c["stats"].get("is_constant")]
        if cons:
            L.append(f"        恒值通道：{cons[:8]}")
        enum = [c["raw_name"] for c in chs if c["stats"].get("is_enumerated")
                and not c["stats"].get("is_constant")]
        if enum:
            L.append(f"        整数且值域≤8（疑为编号/枚举列，非波形量）：{enum[:8]}")
        sines = [c["raw_name"] for c in chs if c["stats"].get("sine_like")]
        if sines:
            L.append(f"        纯正弦形态（波峰因子≈1.414，合成嫌疑）：{sines[:6]}")
        ms = max((c["stats"].get("n_move_segments", 0) for c in chs), default=0)
        nz = max((c["stats"].get("nonzero_motion_fraction", 0) or 0 for c in chs), default=0)
        L.append(f"  运动：最多运动段={ms} 段，非零运动占比峰值={nz:.3f}，"
                 f"跟随误差恒等式={r.get('fe_identity', {}).get('status')}")
        fe = r.get("fe_identity", {})
        for tag, one in sorted((fe.get("per_axis") or {}).items()):
            L.append(f"        [{tag}] fe-(cmd-fb): mean={one['mean']:+.6g} std={one['std']:.6g} "
                     f"max|.|={one['max_abs']:.6g} 残差/fe幅度={one['residual_vs_fe_std_pct']:.3g}% "
                     f"⟹ {'恒等式成立' if one['identity_holds'] else '不成立（单位/符号/错位待人工判读）'} "
                     f"符号判定={one['fe_sign']}")
            L.append(f"        [{tag}] 用通道: {one['channels']}")
            if one.get("fe_group_assumed"):
                L.append(f"        [{tag}] 注意：fe 通道名内无家谱词，按『残差最小的候选轴组』归组"
                         f"（唯一性={'是' if one.get('fe_group_unique') else '否'}），"
                         f"各候选残差%={one.get('candidate_groups')}")
        L.append(f"  红线：{'命中 ' + ' | '.join(r['redlines_fired']) if r['redlines_fired'] else '六条全过'}")
        if r.get("soft_degradations"):
            L.append("  软降级：" + "; ".join(r["soft_degradations"]))
        for lk in r.get("leaks", []):
            L.append(f"    泄漏[{lk['pattern']}] ×{lk['count']} 样例={lk['sample']} → 发布前脱敏")
        cl = r.get("claims_ledger")
        if cl:
            L.append(f"    自述核对账：数值/哈希类 {cl['verified']}/{cl['total']} 条与实体文件核过"
                     f"（证伪 {cl['contradicted']}、无从核对 {cl['unverifiable']}）"
                     + (f"，其中 {cl['excluded_same_source']} 条因同源/单位自证不计入 k"
                        if cl.get("excluded_same_source") else "")
                     + (f"；「来源未登记」{cl['not_registered']} 项" if cl["not_registered"] else "")
                     + (f"；模板缺项 {cl['missing_fields']}" if cl["missing_fields"] else ""))
        for c in r.get("sidecar_claims", []):
            head = f"    自述核对[{c['claim']}] {c['status']}"
            if c.get("measured") is not None:
                L.append(head + f" 声称={c.get('claimed')} 实测={c.get('measured')} — {c.get('note')}")
            elif c.get("text"):
                L.append(head + f" 「{c['text']}」 — {c.get('note', '')}")
            else:
                L.append(head + (f" — {c.get('note')}" if c.get("note") else ""))
        for n in r.get("notes", []):
            L.append(f"    备注：{n}")
    L.append("\n" + "=" * 108)
    L.append("汇总（执行 N / 跳过 M 分列，A-87 口径）")
    for r in reports:
        L.append(f"  {r['file']:44s} {r['kind']:18s} {r['verdict']:22s} "
                 f"{'红线 ' + str(len(r['redlines_fired'])) if r['redlines_fired'] else ''}")
    acc = sum(1 for r in reports if r["verdict"] == "accept")
    rej = sum(1 for r in reports if str(r["verdict"]).startswith("reject"))
    skip = sum(1 for r in reports if r["kind"] in ("ancillary", "archive"))
    L.append(f"  执行 {len(reports) - skip} / 跳过 {skip}（非波形存证不判红线） ⟹ accept {acc} / reject {rej}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--out-txt", default="data/validate_out.txt")
    ap.add_argument("--out-json", default="data/validate_report.json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    try:                                   # Git Bash 控制台默认 cp936，中文报告需强制 utf-8
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if a.selftest:
        sys.exit(1 if selftest() else 0)

    if a.paths:
        paths = list(a.paths)
    elif os.path.isdir("data/raw"):
        paths = [os.path.join("data", "raw", f) for f in sorted(os.listdir("data/raw"))]
    else:
        paths = []
    paths = [p for p in paths if os.path.isfile(p) and not p.endswith(".source.txt")]
    if not paths:
        print("没有可校验的文件（data/raw/ 为空或不存在）")
        return
    reports = []
    for p in paths:
        try:
            reports.append(validate(p))
        except Exception as e:                      # 单文件失败不影响其它文件
            reports.append({"file": os.path.basename(p), "path": p, "bytes": os.path.getsize(p),
                            "sha256": None, "kind": "error", "verdict": "reject_error",
                            "redlines_fired": [f"解析异常 {type(e).__name__}: {e}"]})
    txt = render_txt(reports)
    io.open(a.out_txt, "w", encoding="utf-8").write(txt + "\n")
    slim = json.loads(json.dumps(reports, default=str))
    for r in slim:
        for c in r.get("channels", []):
            c.pop("series", None)
    json.dump(slim, io.open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if not a.quiet:
        print(txt)
    print(f"\n[写出] {a.out_txt}\n[写出] {a.out_json}")


if __name__ == "__main__":
    main()
