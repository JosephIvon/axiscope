"""Markdown 表形检查（检查 27 的产物 + 检查 28 的载体，A-117）。

核四种"渲染即碎"的病例，全部只读、不改文件：
  1. **裸竖线**：单元格里的 `|x|`、`[a|b|c]` 把一行切成多于表头的列（GFM 要求写成 `\\|`）。
  2. **跨行拆行**：一条逻辑行被物理换行拆开——表格在第一个不含 `|` 的行就结束，后续内容脱表
     （KB0 §7 自己写过「Markdown 表行必须单行，跨行会碎表」，此前无机器载体）。
  3. **列数本身不符**：既不是裸竖线也不是拆行，就是真的多写/少写一格。
  4. **空行截断 / 无表头片段**：连续 `|` 行块的首行后面没有 `|---|` 分隔行。GFM 要求表整体连续，
     被空行切成两段后**后一段不再是表**（竖线原样印成散文）——KB0 §6 的表就碎在这一条上，
     而初版扫描只认"表头 + 分隔行"开头的块，对它**零检测力**，所以这一条是补出来的。

用法：`python data/probe_md_tables.py [文件或目录 ...]`（缺省扫 `docs/` 与 `README.md`）。
末尾的汇总行由脚本自数打印，文档只可引用打印值。退出码 0 = 无病例，1 = 有病例。
"""
import io
import re
import sys
from pathlib import Path

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass


SEP_RE = re.compile(r"^\|[\s:|-]+\|?\s*$")
STOP = ("|", ">", "#")


def npipes(line):
    return len(re.findall(r"(?<!\\)\|", line))


def files_of(args):
    out = []
    for a in args:
        p = Path(a)
        out.extend(sorted(p.rglob("*.md")) if p.is_dir() else [p])
    return out


def blocks_of(path):
    """产出 {file, kind, head_line, want, rows=[(行号, [物理行, ...]), ...]}。

    kind ∈ {"table", "orphan"}。orphan 块若与上一个 table 块之间只有空行（即"被空行截断的片段"），
    继承该表的 `want` 以便同时核列数；否则 `want = None`（只报碎表这一条）。
    """
    lines = io.open(path, encoding="utf-8").read().split("\n")
    i = 0
    prev = None
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            if lines[i].strip() and not lines[i].lstrip().startswith(STOP):
                prev = None
            i += 1
            continue
        sep = i + 1 < len(lines) and SEP_RE.match(lines[i + 1].strip())
        want = npipes(lines[i]) if sep else (prev[1] if prev else None)
        rows = []
        j = i + 2 if sep else i
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            grp = [lines[j].rstrip()]
            k = j + 1
            while k < len(lines) and lines[k].strip() and not lines[k].lstrip().startswith(STOP):
                grp.append(lines[k].strip())
                k += 1
            rows.append((j + 1, grp))
            j = k
        yield {"file": str(path), "kind": "table" if sep else "orphan",
               "head_line": i + 1 if sep else None, "want": want, "rows": rows}
        if sep:
            prev = (i + 1, want, j)
        i = j


def main(argv):
    args = argv or ["docs", "README.md"]
    n_rows = n_split = n_cols = n_orphan = 0
    for f in files_of(args):
        for blk in blocks_of(f):
            want = blk["want"]
            if blk["kind"] == "orphan":
                n_orphan += 1
                ln, grp = blk["rows"][0] if blk["rows"] else (0, [""])
                print("%s:%s 碎表片段（无表头或被空行截断，%d 行）| %s"
                      % (f, ln, len(blk["rows"]), grp[0][:56]))
            for ln, grp in blk["rows"]:
                n_rows += 1
                if want is None:
                    continue
                joined = " ".join(grp)
                got = npipes(joined)
                split = len(grp) > 1
                n_split += split
                n_cols += got != want
                if split or got != want:
                    print("%s:%s%s split=%d pipes=%d header(%s)=%s | %s"
                          % (f, ln, "(片段内)" if blk["kind"] == "orphan" else "",
                             len(grp), got, blk["head_line"], want, joined[:56]))
    print("scanned rows=%d | 跨行拆行=%d | 列数不符=%d | 碎表片段=%d | 合计病例=%d"
          % (n_rows, n_split, n_cols, n_orphan, n_split + n_cols + n_orphan))
    return 1 if (n_split or n_cols or n_orphan) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
