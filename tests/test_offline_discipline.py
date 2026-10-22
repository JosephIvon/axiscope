"""c3validate / engine 两处模块 docstring 的离线纪律（「不调 LLM、不联网」与
「confidence 一律由 §2.2 重算，LLM 只能改措辞」）的可执行门禁。

扫描确定性内核（`src/axiscope` 与 `synth`）全部模块：网络栈 / LLM SDK / 训练框架
三类禁运 import，加动态执行逃逸构造（`__import__` / `importlib.import_module` /
裸 `eval` / `exec` / `compile` / `os.system` / `os.popen`；点号前缀的 `re.compile`
不算）。规则 17/18 读仓内产物的既定例外不受影响——本门禁只拦网络与模型调用，
不拦文件读取。

门禁自身三条纪律（KB0 §6 检查 22 的形状）：
1. 扫描集用 glob 现点现算，新增模块自动入闸；扫到文件数不足下限即红，防空转绿灯。
2. 负向注入证明检测力；注入锚点（各模块共有的 `from __future__` 行）缺失时响亮
   失败，且「harness 遇哑锚必须失败」本身也有一条用例来钉。
3. 合法构造（`import json`、`re.compile`）零命中对照，防门禁退化成「见 import 就红」。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("src/axiscope", "synth")
MIN_FILES = 10

FORBIDDEN = {
    "offline-net": (
        "socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp",
        "websockets", "websocket", "grpc", "smtplib", "ftplib", "telnetlib",
        "xmlrpc",
    ),
    "offline-llm": (
        "openai", "anthropic", "cohere", "litellm", "langchain", "langgraph",
        "llama_index", "tiktoken", "mistralai", "groq", "ollama", "dashscope",
        "zhipuai", "qianfan", "google.generativeai", "transformers",
    ),
    "ml-core": (
        "torch", "torchvision", "torchaudio", "sklearn", "tensorflow",
        "keras", "xgboost", "lightgbm", "catboost", "jax", "paddle",
        "paddleocr",
    ),
}

IMPORT_LINE = re.compile(r"^\s*import\s+(.+?)\s*(?:#.*)?$")
FROM_LINE = re.compile(r"^\s*from\s+([\w.]+)\s+import\b")
DYNAMIC = (
    (re.compile(r"(?<![\w.])__import__\s*\("), "dyn-import"),
    (re.compile(r"(?<![\w.])importlib\.import_module\s*\("), "dyn-import"),
    (re.compile(r"(?<![\w.])eval\s*\("), "dyn-exec"),
    (re.compile(r"(?<![\w.])exec\s*\("), "dyn-exec"),
    (re.compile(r"(?<![\w.])compile\s*\("), "dyn-exec"),
    (re.compile(r"\bos\.system\s*\("), "shell-escape"),
    (re.compile(r"\bos\.popen\s*\("), "shell-escape"),
)

ANCHOR = r"^from __future__ import annotations$"


def forbidden_rule(module: str) -> str | None:
    for rule, mods in FORBIDDEN.items():
        for mod in mods:
            if module == mod or module.startswith(mod + "."):
                return rule
    return None


def imported_roots(line: str) -> list[str]:
    m = IMPORT_LINE.match(line)
    if m is None:
        return []
    roots = []
    for token in m.group(1).split(","):
        head = token.strip().split(" as ")[0].split()
        if head:
            roots.append(head[0])
    return roots


def scan_text(text: str, origin: str) -> list[tuple[str, int, str, str]]:
    hits: list[tuple[str, int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for root in imported_roots(line):
            rule = forbidden_rule(root)
            if rule:
                hits.append((origin, lineno, rule, line.strip()))
        for pat, rule in DYNAMIC:
            if pat.search(line):
                hits.append((origin, lineno, rule, line.strip()))
    return hits


def discover() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        files.extend((ROOT / d).glob("*.py"))
    files = sorted(files)
    if len(files) < MIN_FILES:
        pytest.fail(
            f"扫描集只剩 {len(files)} 个文件（下限 {MIN_FILES}）——"
            "发现逻辑可能坏了，门禁不许空转放行"
        )
    return files


def core_findings() -> list[tuple[str, int, str, str]]:
    hits: list[tuple[str, int, str, str]] = []
    for f in discover():
        hits += scan_text(f.read_text(encoding="utf-8"),
                          f.relative_to(ROOT).as_posix())
    return hits


def inject(text: str, snippet: str) -> tuple[str, int]:
    m = re.search(ANCHOR, text, re.M)
    if m is None:
        pytest.fail("注入锚点（from __future__ 行）没找到——"
                    "缺陷没注进去，负向用例拒绝空转通过")
    lineno = text[: m.start()].count("\n") + 1
    return text[: m.start()] + snippet + text[m.start():], lineno


def engine_text() -> str:
    return (ROOT / "src/axiscope/engine.py").read_text(encoding="utf-8")


def test_deterministic_core_has_no_forbidden_constructs():
    hits = core_findings()
    assert hits == [], "确定性内核出现禁运构造：" + "; ".join(
        f"{o} 第{n}行 [{r}] {t}" for o, n, r, t in hits)


def test_discovery_covers_both_packages():
    rel = {f.relative_to(ROOT).as_posix() for f in discover()}
    assert any(r.startswith("src/axiscope/") for r in rel), rel
    assert any(r.startswith("synth/") for r in rel), rel


@pytest.mark.parametrize("snippet,rule", [
    ("import socket  # 门禁负向注入：网络栈\n", "offline-net"),
    ("import openai  # 门禁负向注入：LLM SDK\n", "offline-llm"),
    ("import torch  # 门禁负向注入：训练框架\n", "ml-core"),
])
def test_injected_forbidden_import_is_caught_at_the_injected_line(snippet, rule):
    poisoned, lineno = inject(engine_text(), snippet)
    assert snippet.strip() in poisoned
    hits = scan_text(poisoned, "poisoned")
    assert [(h[1], h[2]) for h in hits if h[2] == rule] == [(lineno, rule)]


def test_injected_dynamic_escapes_are_caught():
    clean = scan_text(engine_text(), "engine")
    assert [h for h in clean if h[2].startswith(("dyn", "shell"))] == [], clean
    poisoned, lineno = inject(
        engine_text(),
        'm = __import__("socket")\nv = eval("1 + 1")\n',
    )
    hits = scan_text(poisoned, "poisoned")
    assert {"dyn-import", "dyn-exec"} <= {h[2] for h in hits}
    assert {h[1] for h in hits if h[2].startswith("dyn")} == {lineno, lineno + 1}


def test_legitimate_constructs_must_not_be_flagged():
    poisoned, _ = inject(
        engine_text(),
        "import json  # 对照：合法 import\n"
        "pat = re.compile('x')  # 对照：点号前缀的 compile 不是逃逸\n",
    )
    assert scan_text(poisoned, "poisoned") == []


def test_injection_harness_itself_fails_on_missing_anchor():
    with pytest.raises(pytest.fail.Exception, match="注入锚点"):
        inject("this text has no anchor line\n", "import socket\n")


def _run_cli(tmp_path: Path, inp: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
           "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "axiscope", "--in", str(inp),
         "--out", str(tmp_path / "out")],
        capture_output=True, env=env, cwd=str(ROOT), timeout=180,
    )


def test_cli_dialect_rejection_exits_2_not_crash(tmp_path):
    r = _run_cli(tmp_path, ROOT / "data/incoming/6114_ObserverTestSet.tab")
    err = r.stderr.decode("utf-8", "replace")
    assert r.returncode == 2, err[-400:]
    assert "拒收" in err
    assert "Traceback" not in err


def test_cli_clean_run_still_exits_zero(tmp_path):
    r = _run_cli(tmp_path, ROOT / "data/raw/Export10_244531.csv")
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[-400:]
