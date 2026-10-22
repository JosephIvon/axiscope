"""文档行号指针核对器（任务 #44，由 KB0 §7 台账 A-117 ⑦ 立的账）。

核什么
------
仓内文档大量使用 `docs/kb/KB0-conventions.md:NNN`、`docs/AUDIT-glm-code-factory.md:110-129`
这类**裸行号指针**。行号会随增删行**静默漂移**，散文里看不出来。本脚本把每条指针拆成三问：

  1. 被指文件找得到吗？              找不到 ⟹ `missing-file`（病例）
                                      **引用方是 `docs/AUDIT-*.md` 时**改判 `external-target`
                                      （那是被审计项目的路径，不在本仓可核范围，见 `is_audit_doc`）
  2. 行号范围越界吗？（M 超过文件行数）越界 ⟹ `range-out-of-bounds`（病例）
  3. 指针所带的引文真的落在 N..M 里吗？不在 ⟹ `stale`（病例）；
     多段拼接引文只命中一部分 ⟹ `partial-quote`（病例）；
     指针后面根本没有引文 ⟹ `no-quote`（**不判**，不算病例）

口径（A-117 ⑦ 明确要求的先决条件：**先定引文归属，否则工具自己就是假病例的制造机**）
------------------------------------------------------------------------------
* **引文归属**：一条 `path:NNN` 指针只对**它后面紧邻的那一段引文**负责。实现上先把整行按
  `path:range` 切分，切出的片段归该片段起点之前的那条指针；片段里再以「紧邻」为闸——指针与
  引文之间只允许分隔符（反引号、空白、`：` `、` `，` `。` `；` `（）` `+` `／` `|` `*` `-`）。
  反例（本脚本必须**不**报病例）：同一行有两条引用、引文属于第二条 ⟹ 第一条记 `no-quote`。
  这条负向例就是 README 雏形脚本制造 2 处假阳性的地方，见 `--selftest` 用例 (c)。
* **引文定界**：`「」` `『』` `“”` `""` 四种成对括号；`「」` 支持嵌套（取到配平的收尾）。
  指针后可紧跟**多段**引文（`「A」／「B」`、`「A」+「B」`），它们同属这一段、每段都必须命中。
* **归一化比对**：去掉 `*`、反引号、空白、`「」『』` 后再判子串包含（原文常带粗体、引文常不带；
  去掉嵌套方括号以免「禁止写「手册…」」这类嵌套被判成不命中）。
* **省略号拼接**：引文含 `…` 时按 `…` 切成若干段，每段都必须命中，缺一段 ⟹ `partial-quote`。
* **无实质内容的引文不判**：引文里没有任何字母数字/CJK（如 `""`、`「…」`）⟹ `no-quote`。
* **范围语义**：`N-M` 是闭区间（落点在第 N 到第 M 行之间），单行就是 `N`。

已知局限（不要把它当成"绿了就是没问题"）
----------------------------------------
* 引文被改写而行号正确 ⟹ 本脚本判 `stale` 但报不出"行号错"，只报"该范围内找不到该引文"；
  真实成因（措辞被改写 vs 行号漂移）靠"引文是否在文件其他行命中"区分，已在打印里给出实际行号。
* 只认 `path.ext:NNN` 形态。**不带路径的续写形态**（`...md:526` 与 `:560`、`KB7:10`）不判，
  只在汇总前单独报一条计数（口径待裁定，默认保守不判 ⟹ 宁可少计，不可虚计）。
* 围栏代码块（三个反引号 / `~~~` 包起来的）里的 `file:NNN` **跳过**：代码块是示例内容、
  不是对文档的断言，扫它会把示例行号判成病例。跳过的条数在汇总前打印。
* `--multiline` 是**待裁定的扩展口径**（默认关）：指针行尾只有标点时，把下一行的引文当作它的
  引文。README 的「逐字抄自本仓库」一节正是这种排版，默认口径下这些指针全部记 `no-quote`。

怎么跑
------
    PYTHONIOENCODING=utf-8 python data/probe_doc_line_refs.py                    # 主扫描（缺省=严格口径）
    PYTHONIOENCODING=utf-8 python data/probe_doc_line_refs.py --selftest          # 负向测试（条数见末尾打印行）
    PYTHONIOENCODING=utf-8 python data/probe_doc_line_refs.py --quote-backtick --multiline   # 推荐的高产口径
    PYTHONIOENCODING=utf-8 python data/probe_doc_line_refs.py --own-segment       # 最宽（台账散文会造噪音，见下）
    PYTHONIOENCODING=utf-8 python data/probe_doc_line_refs.py docs/kb README.md   # 自定义扫描目标

口径开关（都不影响缺省值；缺省就是 A-117 ⑦ 指定的那一条）：
* `--quote-backtick`：反引号串也算引文。本仓的「逐字抄自本仓库」正是用反引号包原文，
  不开它就扫不到；开了以后仍有一道 `code_not_quote` 筛（路径 / 标识符 / 裸行号不算引文）。
* `--multiline`：指针行尾只剩标点时，往**紧邻的下一条非空行**找引文；该续行若是新条目
  （表行 `|`、列表项、标题、引用块）就停——越过表行会把下一行的引文错配给上一条指针。
* `--own-segment`：放宽到「本段内第一个引文串」，散文隔开也认。实测它对 KB0/KB4 台账的
  **代码转述**（「恒写空串」「没有生产者」）成批改红，那些不是逐字引文 ⟹ 不建议当门禁，
  只作为"还有哪些指针带得起引文"的排查工具。

主扫描缺省扫 `docs/**.md` + `README.md` + `data/*.md`。逐条打印
`文件:行号 指针 状态 [引文片段]`（`hit` 不打印，只进汇总），末尾汇总行由**脚本自数**打印，
文档只可引用打印值：

    扫描指针 N 条 | 命中 N | stale N | partial-quote N | no-quote N | missing-file N | range-out-of-bounds N | external-target N | 病例 N

退出码 0 = 无病例（`no-quote` 不算病例），1 = 有病例。只读，不改任何文件。
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

EXT = r"(?:md|py|json|txt|tsv|csv|tab|out|ya?ml|toml|sh|ipynb|log|ini|cfg|xml|html)"
# 只认「带扩展名的路径 + 冒号 + 行号（可带 -M 闭区间）」；不带路径的续写形态不判（见 docstring）
PTR_RE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9_][A-Za-z0-9_.+/@-]*\." + EXT + r"):(\d{1,6})(?:-(\d{1,6}))?")
# 不带路径的别名形态（`:560`、`KB7:10`）只计数不判定
BARE_RE = re.compile(r"(?:(?<=`)|(?<=\s)):?KB\d+:\d|(?<![\w./-]):\d{1,6}(?:-\d{1,6})?(?![\w-])")
FENCE = re.compile(r"^\s*(?:`{3,}|~{3,})")
# 新条目的开头（表行 / 列表项 / 标题 / 引用块 / 有序列表）：跨行找引文时不得越过
BLOCK_START = re.compile(r"^\s*(?:\||[-*+] |\d+\. |> |#)")
CJK_OR_ALNUM = re.compile(r"[0-9A-Za-z\u4e00-\u9fff]")

LBK, RBK = "\u300c", "\u300d"          # 「」
L2BK, R2BK = "\u300e", "\u300f"        # 『』
LDC, RDC = "\u201c", "\u201d"          # “”
BT = chr(96)                           # 反引号
PAIRS = {LBK: RBK, L2BK: R2BK, LDC: RDC, '"': '"'}
NESTED = {LBK, L2BK}
# 指针与引文之间允许的分隔符（**不含反引号**：反引号有两种身份，见 collect 的注释）
SEPS = " \t\u3000:：、,，。.；;/／+（）()[]*-—|~"
NORM_STRIP = re.compile(r"[\s" + BT + r"*「」『』\u200b\u00a0]")
ELLIPSIS = re.compile(r"…+|\.\.\.")
# 段内「另一个引用 token」：无扩展名的行号续写/别名（`README:283`、`:560`、`KB7:10`）、
# 不带行号的文件提及（`docs/kb/KB0-conventions.md`）、章节锚（`§7.3`）——见到即停，
# 因为引文的主人那是**它**而不是本指针（README:92 就是这种形状，own-segment 不许误判）。
BARE_CUT_RE = re.compile(
    r"(?:[A-Za-z][\w.+-]*|KB\d+|§\s?\d)?[:：]\d{1,6}(?:-\d{1,6})?(?![\w-])"
    r"|[§＃]\s?\d"
    r"|[A-Za-z0-9_][\w.+-]*\.[A-Za-z]{1,6}(?![\w])")


class Opts:
    """判定口径开关。缺省 = A-117 ⑦ 指定的严格口径（同一套 selftest 用例锁着）。"""
    own_segment = False   # 引文可以是段内第一个引文串（不要求紧邻）
    backtick = False      # 反引号串也算引文
    multiline = False     # 指针行尾只有标点时，往下找一行引文

    def __init__(self, argv):
        self.own_segment = "--own-segment" in argv
        self.backtick = "--quote-backtick" in argv
        self.multiline = "--multiline" in argv

    def __str__(self):
        on = [n for n, v in (("紧邻", not self.own_segment and not self.multiline and not self.backtick),
                             ("own-segment", self.own_segment),
                             ("quote-backtick", self.backtick),
                             ("multiline", self.multiline)) if v]
        return "+".join(on)


def norm(s):
    return NORM_STRIP.sub("", s)


def first_quote(s):
    """s[0] 是开引号 ⟹ 返回 (内容,  consumed 长度)；配不上对则 (None, 0)。"""
    op = s[0]
    cl = PAIRS[op]
    if op in NESTED:
        depth = 0
        for i, c in enumerate(s):
            if c == op:
                depth += 1
            elif c == cl:
                depth -= 1
                if depth == 0:
                    return s[1:i], i + 1
        return None, 0
    j = s.find(cl, 1)
    return (s[1:j], j + 1) if j > 0 else (None, 0)


def backtick_span(s):
    """s[0] 是反引号 ⟹ 取同一行内的成对内容；跨行不成对则不取（宁可少计，不可虚计）。

    反引号在本仓首先是「代码/标识符」排版，只在 `--quote-backtick` 下才可能当引文，
    且必须过 `code_not_quote` 这道筛：路径、标识符、裸行号续写都不是"逐字引用的原文"，
    把它们当引文就会造出假病例（实测 `:561`、`docs/kb/KB0-conventions.md`、`analyze` 三形）。
    """
    j = s.find(BT, 1)
    if j < 0:
        return None, 0
    content = s[1:j]
    if content.strip("\n ") == "" or CODE_NOT_QUOTE_RE.match(content.strip()):
        return None, 0
    return content, j + 1


# 看起来是标识符 / 文件路径 / 裸行号，而不是被逐字引用的原文
CODE_NOT_QUOTE_RE = re.compile(
    r"^[:：]\d{1,6}(?:-\d{1,6})?$"
    r"|^[^\s]*\." + EXT + r"$"
    r"|^[A-Za-z_][A-Za-z0-9_.()\[\]-]*$")


def collect(s, opts, skip_lead_backtick=False):
    """从 s 起连续取引文串（`「A」／「B」+「C」` 同属本指针）；遇到散文即停。

    反引号有两种身份：指针的收尾/排版（跳过）与引文定界（`--quote-backtick` 才认）。
    `skip_lead_backtick` 表示 s 的第一个反引号是**指针自己**的收尾，一定跳过。
    """
    out = []
    if skip_lead_backtick and s.startswith(BT):
        s = s[1:]
    while True:
        s = s.lstrip(SEPS)
        if not s:
            break
        if s[0] in PAIRS:
            q, adv = first_quote(s)
        elif s[0] == BT and opts.backtick:
            q, adv = backtick_span(s)
        elif s[0] == BT:
            s = s[1:]
            continue
        else:
            break
        if q is None:
            break
        out.append(q)
        s = s[adv:]
    return out


def quotes_of(tail, opts, skip_lead_backtick=False):
    """取本指针的引文串。

    缺省口径（A-117 ⑦ 指定的「紧邻」）：指针与引号之间只允许分隔符 ⟹ 散文隔开就不判。
    `--own-segment`：放宽到「本段（到下一条指针为止）内的第一个引文串」，但遇到段内更早的
      **另一个引用 token**（无扩展名形态 `README:283` / `:560` / `KB7:10`）即停——那条引用才是
      引文的主人，本指针记 `no-quote`。这一条正是 README 雏形脚本 2 处假阳性的成因。
    `--quote-backtick`：把反引号串也算引文（README 的「逐字抄自本仓库」用反引号包原文）。
    """
    q = collect(tail, opts, skip_lead_backtick)
    if q or not opts.own_segment:
        return q
    m = BARE_CUT_RE.search(tail)
    cut = m.start() if m else len(tail)
    for i, c in enumerate(tail[:cut]):
        if c in PAIRS or (opts.backtick and c == BT):
            got = collect(tail[i:], opts)
            if got:
                return got
    return []


class Target:
    """被指文件：按 root 相对路径 → 文档同目录 → 全仓 basename 唯一匹配 三级解析。"""

    def __init__(self, path_text, doc_path, root, index):
        self.text = path_text
        self.cands = []
        p = os.path.join(root, path_text.replace("/", os.sep))
        if os.path.isfile(p):
            self.cands = [p]
        else:
            p2 = os.path.normpath(os.path.join(os.path.dirname(doc_path), path_text))
            if os.path.isfile(p2):
                self.cands = [p2]
            else:
                base = os.path.basename(path_text)
                hit = index.get(base, [])
                if len(hit) == 1:
                    self.cands = hit
                elif len(hit) > 1:
                    self.cands = sorted(hit, key=len)      # 取路径最短者，并记歧义
                    self.ambiguous = len(hit)
                else:
                    self.ambiguous = 0
        self.ambiguous = getattr(self, "ambiguous", 0)
        self.lines = None
        if self.cands:
            try:
                ls = io.open(self.cands[0], encoding="utf-8", errors="replace").read().split("\n")
                # 文件末尾的换行不算一行，否则「指针指向最后一行」会被当成越界/不越界的边界抖动
                self.lines = ls[:-1] if ls and ls[-1] == "" else ls
            except OSError:
                self.lines = None

    @property
    def resolved(self):
        return self.lines is not None


def build_index(root):
    idx = {}
    skip = {".git", "node_modules", "__pycache__", ".venv", "build"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for fn in filenames:
            idx.setdefault(fn, []).append(os.path.join(dirpath, fn))
    return {k: v for k, v in idx.items()}


def check_ptr(tgt, n, m, quotes, whole):
    """返回 (status, detail)。quotes 是原始引文串列表。"""
    parts = []
    for q in quotes:
        for seg in ELLIPSIS.split(norm(q)):
            if seg and CJK_OR_ALNUM.search(seg):
                parts.append(seg)
    if not parts:
        return "no-quote", ""
    if not tgt.resolved:
        return "missing-file", ""
    lines = tgt.lines
    last = len(lines)
    if n < 1 or n > last:
        return "range-out-of-bounds", "N=%d 超出 1..%d" % (n, last)
    hi = m or n
    if hi < n:
        return "range-out-of-bounds", "M=%d < N=%d" % (hi, n)
    if hi > last:
        return "range-out-of-bounds", "M=%d 超出 1..%d" % (hi, last)
    inrange = norm("".join(lines[n - 1:hi]))
    hits = [p in inrange for p in parts]
    if all(hits):
        return "hit", ""
    missing = [p for p, h in zip(parts, hits) if not h]
    where = []
    for p in missing:
        ln = [i + 1 for i, l in enumerate(lines) if p in norm(l)]
        joined = p in whole
        where.append("%s→%s" % (p[:24], ",".join(map(str, ln[:4])) if ln else
                                ("跨行" if joined else "全文件未命中")))
    if any(hits):
        return "partial-quote", "未命中：" + "；".join(where)
    return "stale", "未命中：" + "；".join(where)


def is_audit_doc(rel):
    """引用方是不是 `docs/AUDIT-*.md`（第三方项目审计纪要）——那里引的是**被审计方**的路径。

    口径边界（A-120 裁）：这一类不判病例，但**必须打印且单列一桶**，并且 `tests/test_doc_line_refs.py`
    逐条比对已知清单。只在 `docs/` 的 KB 与 README 里出现「文件不存在」才是本仓漂移，仍判病例——
    否则这条豁免就成了一台把真漂移洗成干净的机器。
    """
    return rel.startswith("docs/AUDIT-")


def scan_doc(path, root, index, opts):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    lines = text.split("\n")
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    cache = {}
    in_fence = False
    recs = []
    skipped_code = 0
    skipped_bare = 0
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            skipped_code += len(PTR_RE.findall(line))
            continue
        ms = list(PTR_RE.finditer(line))
        skipped_bare += len(BARE_RE.findall(line))
        for j, mt in enumerate(ms):
            nxt = ms[j + 1].start() if j + 1 < len(ms) else len(line)
            tail = line[mt.end():nxt]
            quotes = quotes_of(tail, opts, skip_lead_backtick=True)
            if opts.multiline and not quotes and not tail.strip(SEPS + BT + "）)"):
                # 行尾只剩标点 ⟹ 引文可能被排到下一行（README「逐字抄自本仓库」一节就是这种）。
                # 只认**紧邻的下一条非空行**，且它不得是新条目（表行 / 列表项 / 标题 / 引用块）——
                # 跨过去就会把下一行的引文错配给上一条指针（实测 README:91 的表行就踩过）。
                nxt_line = lines[i] if i < len(lines) else ""
                if nxt_line.strip() and not BLOCK_START.match(nxt_line):
                    quotes = quotes_of(nxt_line, opts)
            ptext, n, m = mt.group(1), int(mt.group(2)), int(mt.group(3)) if mt.group(3) else 0
            if ptext not in cache:
                cache[ptext] = Target(ptext, path, root, index)
            tgt = cache[ptext]
            whole = norm("".join(tgt.lines)) if tgt.resolved else ""
            if not quotes:
                if tgt.resolved:
                    status, detail = "no-quote", ""
                elif is_audit_doc(rel):
                    # AUDIT-* 记的是**被审计的外部仓库**里的路径（`tests/test_mcopilot.py`、
                    # `adapter_gen.py` 都不在本仓）。它们不是本仓漂移，但也不许悄悄消失：
                    # 单独一个桶打印出来，测试按「桶内条目必须与已知清单逐条相等」盯着
                    # （多一条 = 可能我们真删了本仓文件；少一条 = 引用被改掉了）。
                    status, detail = "external-target", "指向被审计项目的文件，不在本仓可核范围"
                else:
                    status, detail = "missing-file", ""
            else:
                status, detail = check_ptr(tgt, n, m, quotes, whole)
            if status == "missing-file" and is_audit_doc(rel):
                # 两条判定路径（带引文 / 不带引文）都会落到 missing-file，豁免放在这里统一改判，
                # 否则「引文写得越全越像病例」这种反直觉的差别会留在实现里。
                status, detail = "external-target", "指向被审计项目的文件，不在本仓可核范围"
            recs.append({"doc": rel, "line": i, "ptr": mt.group(0), "status": status,
                         "quote": "／".join(quotes)[:60], "detail": detail,
                         "target": tgt.cands[0] if tgt.cands else ptext,
                         "range": "%d-%d" % (n, m or n),
                         "ambiguous": tgt.ambiguous})
    return recs, skipped_code, skipped_bare


def files_of(args, root):
    """命令行给的路径：目录 ⟹ 递归其下 *.md；文件 ⟹ 原样。相对路径按仓库根解析。"""
    from pathlib import Path
    out = []
    for a in args:
        p = Path(a if os.path.isabs(a) else os.path.join(root, a))
        if p.is_dir():
            out += [str(x) for x in sorted(p.rglob("*.md"))]
        elif p.is_file():
            out.append(str(p))
        else:
            sys.stderr.write("扫描目标不存在：%s\n" % a)
    return out


def default_targets(root):
    """主扫描缺省范围：docs/**.md + data/*.md + README.md（data 只取顶层 md，不递归存证目录）。"""
    out = []
    d = os.path.join(root, "docs")
    if os.path.isdir(d):
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames.sort()
            out += [os.path.join(dirpath, f) for f in sorted(filenames) if f.endswith(".md")]
    da = os.path.join(root, "data")
    if os.path.isdir(da):
        out += [os.path.join(da, f) for f in sorted(os.listdir(da)) if f.endswith(".md")]
    r = os.path.join(root, "README.md")
    if os.path.isfile(r):
        out.append(r)
    return [p for p in out if os.path.isfile(p)]


def main(argv):
    if "--selftest" in argv:
        return selftest()
    opts = Opts(argv)
    args = [a for a in argv if not a.startswith("--")]
    root = ROOT
    files = files_of(args, root) if args else default_targets(root)
    index = build_index(root)
    counts = {}
    total = skipped_code = skipped_bare = 0
    ambig = []
    for f in files:
        recs, sc, sb = scan_doc(f, root, index, opts)
        skipped_code += sc
        skipped_bare += sb
        for r in recs:
            total += 1
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            if r["ambiguous"]:
                ambig.append(r)
            if r["status"] != "hit":
                print("%s:%s %s %s [%s]%s%s" % (
                    r["doc"], r["line"], r["ptr"], r["status"], r["quote"],
                    " " + r["detail"] if r["detail"] else "",
                    " 路径歧义 %d 候选" % r["ambiguous"] if r["ambiguous"] else ""))
    cases = sum(counts.get(k, 0) for k in ("stale", "partial-quote", "missing-file", "range-out-of-bounds"))
    print("备注：口径=%s；跳过围栏代码块内指针 %d 条（示例内容，非断言）；"
          "不带路径的续写形态 %d 处（`:560` / `KB7:10` 一类，未判定）；路径歧义 %d 条" % (
              opts, skipped_code, skipped_bare, len(ambig)))
    print("扫描指针 %d 条 | 命中 %d | stale %d | partial-quote %d | no-quote %d | "
          "missing-file %d | range-out-of-bounds %d | external-target %d | 病例 %d" % (
              total, counts.get("hit", 0), counts.get("stale", 0),
              counts.get("partial-quote", 0), counts.get("no-quote", 0),
              counts.get("missing-file", 0), counts.get("range-out-of-bounds", 0),
              counts.get("external-target", 0), cases))
    return 1 if cases else 0


# ---------------------------------------------------------------- selftest
def selftest(tmp=None):
    """合成用例逐条证伪判定口径（KB0 §6 检查 22 的自我适用）；汇总计数由本函数自己数。"""
    tmp = tmp or os.path.join(ROOT, ".tmp_probe_doc_line_refs")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "kb"), exist_ok=True)

    def w(name, rows):
        io.open(os.path.join(tmp, name), "w", encoding="utf-8", newline="\n").write(
            "\n".join(rows) + "\n")

    # 被指文件：第 3 行原文不带粗体（引文带粗体时靠归一化命中），第 5 行是嵌套「」的原文
    w(os.path.join("kb", "tgt.md"), [
        "# 标题",
        "这是甲句 alpha-one",
        "乙句 beta-two 出现在这里",
        "丙句 gamma-three",
        "丁句引用嵌套：禁止写「手册确认的错误」或「我们的发现」",
    ])
    w(os.path.join("kb", "doc.md"), [
        "(a) 正确指针带命中引文 `kb/tgt.md:2`：「这是甲句 alpha-one」。",
        "(b) 指针漂移，引文实际在第 4 行 `kb/tgt.md:2`：「丙句 gamma-three」。",
        "(c) 同一行两条引用、引文属于第二条 `kb/tgt.md:2` 登记于此，另见 `kb/tgt.md:4`：「丙句 gamma-three」。",
        "(d) 粗体差异（引文有 ** 而原文没有）`kb/tgt.md:3`：「**乙句 beta-two** 出现在这里」。",
        "(e) 省略号多段拼接、第二段缺 `kb/tgt.md:2`：「这是甲句…这句话原文里没有」。",
        "(f) 指针后没有引文 `kb/tgt.md:2` 登记于此。",
        "(g) 文件不存在 `kb/none.md:3`：「这是甲句 alpha-one」。",
        "(h) 范围越界 `kb/tgt.md:2-99`：「这是甲句 alpha-one」。",
        "(i) 多段引文全部命中 `kb/tgt.md:2`：「这是甲句 alpha-one」／「这是甲句 alpha-one」。",
        "(j) 引文里没有任何实质内容 `kb/tgt.md:2`：「…」",
        "(k) 嵌套方括号引文 `kb/tgt.md:5`：「丁句引用嵌套：禁止写「手册确认的错误」或「我们的发现」」。",
        "(l) 引文与指针根本对不上（全文件都没有）`kb/tgt.md:2`：「这句话仓内不存在 atoz」。",
        "(m) 围栏代码块里的指针不判：",
        "```",
        "示例 `kb/tgt.md:2`：「这句话仓内不存在 atoz」。",
        "```",
    ])
    recs, skipped_code, _ = scan_doc(os.path.join(tmp, "kb", "doc.md"), tmp,
                                     build_index(tmp), Opts([]))
    by_line = {}
    for r in recs:
        by_line.setdefault(r["line"], []).append(r)

    # (用例名, doc.md 行号, 该行第几条指针, 期望状态, 期望 detail 含有的串或 None)
    cases = [
        ("a", 1, 0, "hit", None),
        ("b", 2, 0, "stale", "→4"),
        ("c-第一条不得背锅（抓 README 雏形的假阳性）", 3, 0, "no-quote", None),
        ("c-第二条正常判定", 3, 1, "hit", None),
        ("d", 4, 0, "hit", None),
        ("e", 5, 0, "partial-quote", "这句话原文里没有"),
        ("f", 6, 0, "no-quote", None),
        ("g", 7, 0, "missing-file", None),
        ("h", 8, 0, "range-out-of-bounds", "超出"),
        ("i", 9, 0, "hit", None),
        ("j", 10, 0, "no-quote", None),
        ("k", 11, 0, "hit", None),
        ("l", 12, 0, "stale", "全文件未命中"),
    ]
    print("负向测试（A-117 ⑦：引文归属口径必须先定，否则工具自己就是假病例的制造机）")
    executed = fails = 0
    for name, ln, pos, want, want_detail in cases:
        executed += 1
        at = by_line.get(ln, [])
        r = at[pos] if len(at) > pos else None
        ok = r is not None and r["status"] == want and (
            want_detail is None or want_detail in r["detail"])
        fails += 0 if ok else 1
        print("  %s (%s) kb/doc.md:%s 第 %d 条指针 期望=%s 实得=%s%s" % (
            "PASS" if ok else "FAIL", name, ln, pos + 1, want,
            r["status"] if r else "（无记录）",
            " | " + r["detail"] if ok and r["detail"] else ""))
        if not ok:
            print("        该行实得=%r" % ([(x["ptr"], x["status"], x["detail"]) for x in at],))

    # 病例/非病例的分界：no-quote 不算病例，其余缺省形态都算
    n_cases = sum(1 for r in recs if r["status"] not in ("hit", "no-quote"))
    executed += 1
    ok = n_cases == 5
    fails += 0 if ok else 1
    print("  %s (n) 病例口径：stale/partial-quote/missing-file/range-out-of-bounds 共 %d 条，"
          "no-quote %d 条不计病例（期望病例 5）" % (
              "PASS" if ok else "FAIL", n_cases,
              sum(1 for r in recs if r["status"] == "no-quote")))

    # 围栏代码块必须被跳过：不跳过就会把示例里的假引文判成病例
    executed += 1
    ok = skipped_code == 1 and 13 not in by_line
    fails += 0 if ok else 1
    print("  %s (o) 围栏代码块内的指针被跳过（跳过 %d 条、未进入判定）" % ("PASS" if ok else "FAIL", skipped_code))

    # 条数自洽：判定条数 + 围栏跳过 = 行内指针总数（12 行里 11 行各 1 条 + c 行 2 条 = 13，加围栏 1 = 14）
    executed += 1
    ok = len(recs) == 13 and len(recs) + skipped_code == 14
    fails += 0 if ok else 1
    print("  %s (p) 计数自洽：判定 %d 条 + 围栏跳过 %d 条 = 指针 %d 条" % (
        "PASS" if ok else "FAIL", len(recs), skipped_code, len(recs) + skipped_code))

    # 放宽口径的样本：own-segment / quote-backtick / multiline 各自开火与不开火的边界
    w(os.path.join("kb", "doc2.md"), [
        "(q) 散文隔开的引文归本指针 `kb/tgt.md:2` 登记于此，原文写作「这是甲句 alpha-one」。",
        "(r) 引文前有更早的无扩展名引用 token `kb/tgt.md:2` 属实（其写法见 README:4「丙句 gamma-three」）。",
        "(s) 反引号包起来的逐字原文 `kb/tgt.md:2`：`这是甲句 alpha-one`",
        "(t) 指针行尾只有标点、引文在下一行 `kb/tgt.md:2`：",
        "`这是甲句 alpha-one`",
    ])
    index = build_index(tmp)

    def probe(fname, flags, ln, pos):
        rs, _, _ = scan_doc(os.path.join(tmp, "kb", fname), tmp, index, Opts(flags))
        bl = {}
        for r in rs:
            bl.setdefault(r["line"], []).append(r)
        at = bl.get(ln, [])
        return at[pos]["status"] if len(at) > pos else "（无记录）"

    # (用例名, 文件, 口径开关, 行号, 第几条, 期望状态)
    flag_cases = [
        ("q-缺省严格口径不判（散文隔开）", "doc2.md", [], 1, 0, "no-quote"),
        ("q-own-segment 认散文后的第一条引文", "doc2.md", ["--own-segment"], 1, 0, "hit"),
        ("r-own-segment 也不许越过更早的另一条引用 token", "doc2.md", ["--own-segment"], 2, 0, "no-quote"),
        ("s-缺省不把反引号串当引文", "doc2.md", [], 3, 0, "no-quote"),
        ("s-quote-backtick 才认反引号逐字串", "doc2.md", ["--quote-backtick"], 3, 0, "hit"),
        ("t-缺省不跨行 ⟹ 下一行的原文归不到本指针", "doc2.md", [], 4, 0, "no-quote"),
        ("t-multiline+backtick 认下一行的逐字串", "doc2.md", ["--multiline", "--quote-backtick"], 4, 0, "hit"),
    ]
    print("放宽口径的边界（每条都同时验「开火」与「不开火」，防止工具自己造假病例）")
    for name, fn, flags, ln, pos, want in flag_cases:
        executed += 1
        got = probe(fn, flags, ln, pos)
        ok = got == want
        fails += 0 if ok else 1
        print("  %s (%s) %s:%s 口径=%s 期望=%s 实得=%s" % (
            "PASS" if ok else "FAIL", name, fn, ln, "+".join(flags) or "缺省", want, got))

    # `external-target` 的两侧（A-120）：AUDIT 文档里指向被审计项目的路径不判病例，
    # 同一形态写在 KB / README 里**仍**判 missing-file——否则这条豁免就是漂移洗白机。
    os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
    w(os.path.join("docs", "AUDIT-x.md"), [
        "(u) 引用被审计仓库的文件 `adapter_gen.py:73`：原文在那边。",
    ])
    w(os.path.join("docs", "kb-notaudit.md"), [
        "(v) 同一个不存在的路径 `adapter_gen.py:73` 出现在本仓文档里。",
    ])

    def probe_doc(rel):
        rs, _, _ = scan_doc(os.path.join(tmp, rel), tmp, build_index(tmp), Opts([]))
        return rs[0]["status"] if rs else "（无记录）"

    ext_cases = [
        ("u-AUDIT 文档引外部仓库的路径 ⟹ external-target（可见，不判病例）",
         probe_doc(os.path.join("docs", "AUDIT-x.md")), "external-target"),
        ("v-同一形态出现在本仓文档里 ⟹ 仍判 missing-file（漂移洗白机不许存在）",
         probe_doc(os.path.join("docs", "kb-notaudit.md")), "missing-file"),
    ]
    print("external-target 的豁免边界（豁免必须只对 AUDIT 文档成立）")
    for name, got, want in ext_cases:
        executed += 1
        ok = got == want
        fails += 0 if ok else 1
        print("  %s (%s) 期望=%s 实得=%s" % ("PASS" if ok else "FAIL", name, want, got))

    print("通过 %d / 执行 %d / 失败 %d" % (executed - fails, executed, fails))
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
