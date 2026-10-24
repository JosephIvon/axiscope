import json
import sys

try:
    # 控制台不是 UTF-8 时 print 会抛 UnicodeEncodeError——脚本崩在打印上，
    # 而不是给出判定。Windows 控制台默认 cp936/cp1252，GitHub runner 是 cp1252。
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 环境相关
    pass



def walk(blocks):
    out = {}
    for _bname, blk in blocks.items():
        for fld in blk.get("fields", []):
            out[fld["typeName"]] = fld.get("value")
    return out


for f, doi in [("data/raw/darus3600.json", "DARUS-3600"), ("data/raw/darus5171.json", "DARUS-5171")]:
    d = json.load(open(f, encoding="utf-8"))["data"]
    lv = d["latestVersion"]
    md = walk(lv.get("metadataBlocks", {}))
    print("=" * 66)
    print(doi, "| version", lv.get("versionNumber"), "| released", lv.get("releaseTime"))
    print("  LICENSE:", json.dumps(lv.get("license"))[:200])
    for key in ("title", "subtitle", "author", "keyword", "subject", "publicationDate"):
        if key in md:
            print(f"  {key.upper():9s}", json.dumps(md[key], ensure_ascii=False)[:400])
    desc = md.get("description")
    if desc:
        txt = " ".join(x.get("value", "") for x in desc) if isinstance(desc, list) else str(desc)
        print("  DESCRIPTION:", txt[:1500])
