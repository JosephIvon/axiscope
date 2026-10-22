"""探针：对候选 DOI 现场核 DaRUS API，打印权威元数据（供来源登记引用，不改任何文件）。

口径：只打**本会话实测**到的字段。上游没有的键一律打 None，不从标题猜、不从记忆补。

用法：PYTHONIOENCODING=utf-8 python data/probe_darus_provenance.py
"""
from __future__ import annotations

import json
import os
import urllib.request

CANDIDATES = [
    "10.18419/darus-2563", "10.18419/darus-3003", "10.18419/darus-3109",
    "10.18419/darus-3152", "10.18419/darus-3252", "10.18419/darus-3292",
    "10.18419/darus-3600", "10.18419/darus-3759", "10.18419/darus-3900",
    "10.18419/darus-4075", "10.18419/darus-4152", "10.18419/darus-4224",
    "10.18419/darus-5160", "10.18419/darus-5171", "10.18419/darus-6114",
    "10.18419/darus-6333",
]
BASE = "https://darus.uni-stuttgart.de/api/datasets/:persistentId/?persistentId=doi:"
OUT = "build/darus_provenance.json"


def fetch(doi: str) -> dict:
    req = urllib.request.Request(BASE + doi, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return {"http_status": resp.status, "body": json.loads(resp.read().decode("utf-8"))}


def main() -> int:
    out: dict[str, dict] = {}
    for doi in CANDIDATES:
        try:
            got = fetch(doi)
        except Exception as exc:  # 网络/解析失败都如实记，不猜
            out[doi] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"{doi}  ERROR {type(exc).__name__}: {exc}")
            continue
        body = got["body"]
        if body.get("status") != "OK":
            out[doi] = {"http_status": got["http_status"], "status": body.get("status")}
            print(f"{doi}  status={body.get('status')}")
            continue
        ver = body["data"]["latestVersion"]
        fields = ver["metadataBlocks"]["citation"].get("fields", [])

        def fv(name: str):
            for f in fields:
                if f.get("typeName") == name:
                    return f.get("value")
            return None

        titles = fv("title")
        titles = [titles] if isinstance(titles, str) else (titles or [])
        authors = fv("author")
        authors = ([a["authorName"]["value"] for a in authors]
                   if isinstance(authors, list) and authors and isinstance(authors[0], dict)
                   else (authors or []))
        lic = ver.get("license") or {}
        out[doi] = {
            "http_status": got["http_status"],
            "status": body.get("status"),
            "persistent_id": ver.get("datasetPersistentId"),
            "titles": titles,
            "authors": authors,
            "license_name": lic.get("name"),
            "license_uri": lic.get("uri"),
            "publication_date": ver.get("publicationDate"),
            "version_number": ver.get("versionNumber"),
            "version_state": ver.get("versionState"),
            "n_files": len(ver.get("files", [])),
            "root_id": ver.get("id"),
            "dataset_id": ver.get("datasetId"),
        }
        rec = out[doi]
        print(f"{doi}  {rec['persistent_id']}  files={rec['n_files']}  "
              f"lic={rec['license_name']}  v{rec['version_number']}")
        print(f"    title={titles}")
        print(f"    authors={authors}")
    os.makedirs("build", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())