# RKF Auto-Connect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable RKF auto-connect layer so connected projects automatically capture research searches, DOI/URL leads, web clips, and valuable research discussions into RKF without requiring the user to name RKF every time.

**Architecture:** Add a small repo-side helper in `tools/rkf_auto_connect.py` for config resolution, trigger classification, project markers, and safe RKF CLI command construction. Install a global personal skill named `rkf-auto-connect` that calls the helper and then routes captures through existing RKF commands such as `inbox capture` and `hot record`. Keep RKF schemas and evidence boundaries inside RKF; the connector is only a policy and routing layer.

**Tech Stack:** Python standard library, TOML via `tomllib`, existing RKF CLI, Markdown skill docs, unittest.

---

## File Structure

- Create `tools/rkf_auto_connect.py`: standalone helper used by the global skill from any project. It resolves `~/.codex/rkf_connector.toml`, classifies capture triggers, reads/writes `.rkf-connect.toml`, and prints safe RKF CLI commands.
- Create `tests/test_rkf_auto_connect.py`: focused tests for config resolution, trigger classification, blocked captures, command generation, and marker writing.
- Create `$HOME/.codex/skills/rkf-auto-connect/SKILL.md`: global personal skill instructions. This file is outside the repo and requires explicit approval before writing.
- Create or update `$HOME/.codex/rkf_connector.toml`: local global connector config. This file is outside the repo and requires explicit approval before writing.
- Create `docs/workflows/rkf-auto-connect.zh-TW.md`: user-facing workflow for connecting projects and understanding auto-capture.
- Modify `docs/FEATURES_AND_COMMANDS.zh-TW.md`: mention auto-connect helper and workflow.
- Modify `docs/PROJECT_MEMORY.md`: record the durable auto-connect decision.
- Modify `CHANGELOG.md`: note RKF auto-connect support.

Commits are not automatic in this repo. If the user explicitly asks for a commit during execution, make one focused commit after verification; otherwise stop with a diff summary.

### Task 1: Write Failing Tests For The Repo-Side Helper

**Files:**
- Create: `tests/test_rkf_auto_connect.py`

- [ ] **Step 1: Create the test file**

Use this complete file:

```python
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tools import rkf_auto_connect as auto


class RKFAutoConnectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.researchwiki = self.root / "ResearchWiki"
        self.researchwiki.mkdir()
        (self.researchwiki / "rkf.workspace.toml").write_text(
            "[storage]\nwiki_root = \"${HOME}/ResearchWiki/wiki\"\n",
            encoding="utf-8",
        )
        self.config = self.root / "rkf_connector.toml"
        self.old_env = os.environ.copy()
        os.environ["RKF_CONNECTOR_CONFIG"] = str(self.config)
        self.config.write_text(
            "[researchwiki]\n"
            f"root = \"{self.researchwiki.as_posix()}\"\n\n"
            "[policy]\n"
            "mode = \"active-aggressive\"\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        self.tmp.cleanup()

    def test_load_config_resolves_researchwiki_root(self) -> None:
        config = auto.load_connector_config()

        self.assertEqual(config.researchwiki_root, self.researchwiki)
        self.assertEqual(config.mode, "active-aggressive")

    def test_classify_active_doi_source_material(self) -> None:
        decision = auto.classify_capture(
            text="Find papers related to DOI 10.1234/example and summarize the source.",
            source_url="",
            project_name="AnyProject",
        )

        self.assertEqual(decision.level, "active")
        self.assertIn("doi", decision.reasons)
        self.assertIn("inbox", decision.targets)
        self.assertIn("hot", decision.targets)

    def test_classify_aggressive_research_discussion_without_doi(self) -> None:
        decision = auto.classify_capture(
            text="This WRF microphysics calibration idea may change the experiment design and manuscript argument.",
            source_url="",
            project_name="QUACS",
        )

        self.assertEqual(decision.level, "aggressive")
        self.assertIn("research-discussion", decision.reasons)
        self.assertIn("inbox", decision.targets)

    def test_classify_ordinary_coding_debug_as_none(self) -> None:
        decision = auto.classify_capture(
            text="Fix this CSS padding issue in the dashboard button.",
            source_url="",
            project_name="WebApp",
        )

        self.assertEqual(decision.level, "none")
        self.assertEqual(decision.targets, [])

    def test_block_private_paths_and_long_transcripts(self) -> None:
        private_path = "/" + "Users/example/private.txt"
        private_decision = auto.classify_capture(
            text=f"Read {private_path} and save it.",
            source_url="",
            project_name="AnyProject",
        )
        long_decision = auto.classify_capture(
            text="chat transcript\n" * 900,
            source_url="",
            project_name="AnyProject",
        )

        self.assertEqual(private_decision.level, "blocked")
        self.assertIn("private-path", private_decision.reasons)
        self.assertEqual(long_decision.level, "blocked")
        self.assertIn("too-long", long_decision.reasons)

    def test_build_inbox_command_uses_existing_rkf_cli(self) -> None:
        config = auto.load_connector_config()
        command = auto.build_inbox_command(
            config=config,
            title="ChatGPT note on aerosol paper",
            origin="project:QUACS",
            clip="Short source-grounded summary mentioning DOI 10.1234/example.",
            reader_note="User idea goes here.",
            doi="10.1234/example",
            source_url="https://example.org/paper",
            no_inject=False,
        )

        self.assertEqual(command[:4], ["python3", str(self.researchwiki / "tools" / "rk.py"), "inbox", "capture"])
        self.assertIn("--doi", command)
        self.assertIn("10.1234/example", command)
        self.assertNotIn("/" + "Users/", " ".join(command))

    def test_build_hot_command_records_research_demand(self) -> None:
        config = auto.load_connector_config()
        command = auto.build_hot_command(
            config=config,
            query="recent aerosol-cloud parameterization papers",
            origin="project:ResearchProject",
            intent="paper-search",
        )

        self.assertEqual(command[:4], ["python3", str(self.researchwiki / "tools" / "rk.py"), "hot", "record"])
        self.assertIn("--intent", command)
        self.assertIn("paper-search", command)

    def test_write_project_marker_is_public_safe(self) -> None:
        project = self.root / "SomeProject"
        project.mkdir()

        marker = auto.write_project_marker(project, mode="active-aggressive")

        self.assertEqual(marker, project / ".rkf-connect.toml")
        text = marker.read_text(encoding="utf-8")
        self.assertIn("enabled = true", text)
        self.assertIn("mode = \"active-aggressive\"", text)
        self.assertNotIn(str(self.researchwiki), text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
python3 -m unittest tests.test_rkf_auto_connect
```

Expected: FAIL with an import error for `tools.rkf_auto_connect`.

### Task 2: Implement The Repo-Side Helper

**Files:**
- Create: `tools/rkf_auto_connect.py`
- Test: `tests/test_rkf_auto_connect.py`

- [ ] **Step 1: Create `tools/rkf_auto_connect.py`**

Use this complete file:

```python
"""Cross-project RKF auto-connect helper.

This helper is intentionally small: it resolves the local RKF checkout,
classifies whether a task should be captured, and builds existing RKF CLI
commands. It does not own RKF schemas or promote claims.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


DEFAULT_CONFIG = Path(os.environ.get("RKF_CONNECTOR_CONFIG", "~/.codex/rkf_connector.toml")).expanduser()
PRIVATE_PATH_RE = re.compile(r"/" + r"Users/[^/\s]+|C:" + r"\\Users\\", re.IGNORECASE)
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_RE = re.compile(r"\barxiv:\s*\d{4}\.\d{4,5}(?:v\d+)?|\barxiv\.org/abs/\d{4}\.\d{4,5}", re.IGNORECASE)
PUBMED_RE = re.compile(r"\bPMID:\s*\d+\b|\bpubmed\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)>\"]+")
LONG_CAPTURE_LIMIT = 12000

ACTIVE_TERMS = {
    "paper",
    "papers",
    "doi",
    "citation",
    "reference",
    "journal",
    "conference",
    "literature",
    "source",
    "web clip",
    "dataset",
    "arxiv",
    "pubmed",
}

AGGRESSIVE_TERMS = {
    "synthesis",
    "literature review",
    "method",
    "experiment design",
    "manuscript",
    "proposal",
    "hypothesis",
    "claim",
    "evidence",
    "diagnostic",
    "parameterization",
    "calibration",
    "interpretation",
    "研究",
    "文獻",
    "方法",
    "實驗",
    "論文",
    "投稿",
    "假說",
    "證據",
    "綜整",
}

CODING_ONLY_TERMS = {
    "css",
    "button",
    "padding",
    "typescript",
    "react component",
    "build error",
    "lint error",
}


@dataclass(frozen=True)
class ConnectorConfig:
    researchwiki_root: Path
    mode: str
    config_path: Path


@dataclass(frozen=True)
class CaptureDecision:
    level: str
    targets: list[str]
    reasons: list[str]
    summary: str


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"RKF connector config not found: {path}")
    if tomllib is not None:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    data: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = data.setdefault(line.strip("[]"), {})
            continue
        if current is not None and "=" in line:
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip().strip('"')
    return data


def _expand_path(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def load_connector_config(path: Path | None = None) -> ConnectorConfig:
    config_path = path or Path(os.environ.get("RKF_CONNECTOR_CONFIG", str(DEFAULT_CONFIG))).expanduser()
    data = _load_toml(config_path)
    researchwiki = data.get("researchwiki", {}) if isinstance(data, dict) else {}
    policy = data.get("policy", {}) if isinstance(data, dict) else {}
    root_value = researchwiki.get("root") if isinstance(researchwiki, dict) else None
    if not isinstance(root_value, str) or not root_value.strip():
        raise SystemExit("RKF connector config missing [researchwiki].root")
    root = _expand_path(root_value)
    if not (root / "tools" / "rk.py").exists():
        raise SystemExit(f"RKF CLI not found under configured root: {root}")
    mode = policy.get("mode", "active-aggressive") if isinstance(policy, dict) else "active-aggressive"
    return ConnectorConfig(researchwiki_root=root, mode=str(mode), config_path=config_path)


def _contains_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _summary(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:220]


def classify_capture(*, text: str, source_url: str = "", project_name: str = "") -> CaptureDecision:
    haystack = f"{text}\n{source_url}\n{project_name}".strip()
    reasons: list[str] = []
    targets: list[str] = []
    if PRIVATE_PATH_RE.search(haystack):
        return CaptureDecision(level="blocked", targets=[], reasons=["private-path"], summary=_summary(text))
    if len(haystack) > LONG_CAPTURE_LIMIT:
        return CaptureDecision(level="blocked", targets=[], reasons=["too-long"], summary=_summary(text))
    if not haystack:
        return CaptureDecision(level="none", targets=[], reasons=[], summary="")

    if DOI_RE.search(haystack):
        reasons.append("doi")
    if ARXIV_RE.search(haystack):
        reasons.append("arxiv")
    if PUBMED_RE.search(haystack):
        reasons.append("pubmed")
    if URL_RE.search(source_url) or URL_RE.search(text):
        reasons.append("url")
    if _contains_any(haystack, ACTIVE_TERMS):
        reasons.append("source-like")
    if _contains_any(haystack, AGGRESSIVE_TERMS):
        reasons.append("research-discussion")

    if "research-discussion" in reasons:
        targets.append("inbox")
        if any(reason in reasons for reason in ("doi", "arxiv", "pubmed", "source-like")):
            targets.append("hot")
        return CaptureDecision(level="aggressive", targets=sorted(set(targets)), reasons=sorted(set(reasons)), summary=_summary(text))

    if reasons:
        targets.append("inbox")
        if any(reason in reasons for reason in ("doi", "arxiv", "pubmed", "source-like")):
            targets.append("hot")
        return CaptureDecision(level="active", targets=sorted(set(targets)), reasons=sorted(set(reasons)), summary=_summary(text))

    if _contains_any(haystack, CODING_ONLY_TERMS):
        return CaptureDecision(level="none", targets=[], reasons=["ordinary-coding"], summary=_summary(text))
    return CaptureDecision(level="none", targets=[], reasons=[], summary=_summary(text))


def _rk_command(config: ConnectorConfig, *args: str) -> list[str]:
    return ["python3", str(config.researchwiki_root / "tools" / "rk.py"), *args]


def build_inbox_command(
    *,
    config: ConnectorConfig,
    title: str,
    origin: str,
    clip: str,
    reader_note: str = "",
    agent_note: str = "",
    doi: str = "",
    source_url: str = "",
    topic_id: str = "",
    no_inject: bool = False,
) -> list[str]:
    command = _rk_command(config, "inbox", "capture", title, "--origin", origin, "--clip", clip)
    if reader_note:
        command.extend(["--reader-note", reader_note])
    if agent_note:
        command.extend(["--agent-note", agent_note])
    if doi:
        command.extend(["--doi", doi])
    if source_url:
        command.extend(["--source-url", source_url])
    if topic_id:
        command.extend(["--topic-id", topic_id])
    if no_inject:
        command.append("--no-inject")
    return command


def build_hot_command(*, config: ConnectorConfig, query: str, origin: str, intent: str = "research-discussion") -> list[str]:
    return _rk_command(config, "hot", "record", query, "--origin", origin, "--intent", intent)


def write_project_marker(project_root: Path, *, mode: str = "active-aggressive") -> Path:
    project_root.mkdir(parents=True, exist_ok=True)
    marker = project_root / ".rkf-connect.toml"
    marker.write_text(
        "[rkf_auto_connect]\n"
        "enabled = true\n"
        f"mode = \"{mode}\"\n"
        "config = \"global\"\n",
        encoding="utf-8",
    )
    return marker


def read_project_marker(project_root: Path) -> dict[str, Any]:
    marker = project_root / ".rkf-connect.toml"
    if not marker.exists():
        return {"enabled": False, "mode": ""}
    data = _load_toml(marker)
    section = data.get("rkf_auto_connect", {}) if isinstance(data, dict) else {}
    return section if isinstance(section, dict) else {"enabled": False, "mode": ""}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rkf-auto-connect", description="Classify and route cross-project RKF captures")
    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--config")

    classify = sub.add_parser("classify")
    classify.add_argument("text")
    classify.add_argument("--source-url", default="")
    classify.add_argument("--project-name", default="")

    marker = sub.add_parser("mark-project")
    marker.add_argument("project_root")
    marker.add_argument("--mode", default="active-aggressive")

    inbox = sub.add_parser("inbox-command")
    inbox.add_argument("title")
    inbox.add_argument("--origin", required=True)
    inbox.add_argument("--clip", required=True)
    inbox.add_argument("--reader-note", default="")
    inbox.add_argument("--agent-note", default="")
    inbox.add_argument("--doi", default="")
    inbox.add_argument("--source-url", default="")
    inbox.add_argument("--topic-id", default="")
    inbox.add_argument("--no-inject", action="store_true")

    hot = sub.add_parser("hot-command")
    hot.add_argument("query")
    hot.add_argument("--origin", required=True)
    hot.add_argument("--intent", default="research-discussion")

    args = parser.parse_args(argv)
    if args.command == "resolve":
        config = load_connector_config(Path(args.config).expanduser() if args.config else None)
        print(json.dumps({"researchwiki_root": str(config.researchwiki_root), "mode": config.mode}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "classify":
        decision = classify_capture(text=args.text, source_url=args.source_url, project_name=args.project_name)
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
        return 0
    if args.command == "mark-project":
        path = write_project_marker(Path(args.project_root).expanduser().resolve(), mode=args.mode)
        print(path)
        return 0

    config = load_connector_config()
    if args.command == "inbox-command":
        print(json.dumps(build_inbox_command(config=config, title=args.title, origin=args.origin, clip=args.clip, reader_note=args.reader_note, agent_note=args.agent_note, doi=args.doi, source_url=args.source_url, topic_id=args.topic_id, no_inject=args.no_inject), ensure_ascii=False))
        return 0
    if args.command == "hot-command":
        print(json.dumps(build_hot_command(config=config, query=args.query, origin=args.origin, intent=args.intent), ensure_ascii=False))
        return 0
    raise SystemExit(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 2: Run the focused tests and verify they pass**

Run:

```bash
python3 -m unittest tests.test_rkf_auto_connect
```

Expected: PASS.

- [ ] **Step 3: Run the existing RKF CLI tests**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: PASS.

### Task 3: Install The Global Personal Skill And Config

**Files:**
- Create: `$HOME/.codex/skills/rkf-auto-connect/SKILL.md`
- Create: `$HOME/.codex/rkf_connector.toml`
- Test: `tools/rkf_auto_connect.py`

This task writes outside the repository. Request approval before making these filesystem changes.

- [ ] **Step 1: Create the global connector config**

Create `$HOME/.codex/rkf_connector.toml` with this exact content:

```toml
[researchwiki]
root = "${HOME}/Desktop/ResearchWiki"

[policy]
mode = "active-aggressive"
```

- [ ] **Step 2: Create the global skill directory**

Create `$HOME/.codex/skills/rkf-auto-connect/`.

- [ ] **Step 3: Create the global skill entrypoint**

Create `$HOME/.codex/skills/rkf-auto-connect/SKILL.md` with this exact content:

```markdown
---
name: rkf-auto-connect
description: Auto-connect active Codex projects to the user's RKF database. Use when the user asks to connect RKF, or when research-related searches, DOI/URL leads, web clips, literature synthesis, method discussion, experiment design, manuscript reasoning, or reusable research ideas should be automatically captured.
---

# RKF Auto-Connect

Use this skill when:

- The user says `連結我的 RKF 資料庫`, `connect my RKF database`, or similar.
- A connected project contains research-relevant search, DOI, URL, web clip, paper lead, literature synthesis, method discussion, experiment design, manuscript reasoning, claim comparison, or reusable research idea.
- A valuable research discussion should be preserved without promoting it to stable evidence.

Do not use this skill for ordinary coding/debugging work with no research value.

## Setup

Resolve configuration from `$HOME/.codex/rkf_connector.toml`.

Expected config:

```toml
[researchwiki]
root = "${HOME}/Desktop/ResearchWiki"

[policy]
mode = "active-aggressive"
```

Do not write private Drive paths into project docs. The ResearchWiki checkout resolves live storage through its own `rkf.workspace.toml`.

## Connection Workflow

When the user asks to connect RKF in a project:

1. Resolve the ResearchWiki checkout from `$HOME/.codex/rkf_connector.toml`.
2. Verify that `tools/rk.py` and `rkf.workspace.toml` exist under that checkout.
3. Offer session-scope connection immediately.
4. If the user wants project-scope connection, create `.rkf-connect.toml` in the project root:

```toml
[rkf_auto_connect]
enabled = true
mode = "active-aggressive"
config = "global"
```

5. Report that research-related searches, DOI/URL leads, web clips, and valuable research discussion will be captured to RKF inbox/hot.md.

## Trigger Policy

Active triggers:

- DOI, arXiv ID, PubMed ID, ISBN, dataset DOI, formal citation.
- Paper title, author-year reference, journal/conference name, literature search query.
- Important source URL used as evidence.
- Web clip or source-backed excerpt.
- Repeated research question suitable for `hot.md`.

Aggressive research triggers:

- Literature synthesis or comparison.
- Method design, model planning, or experiment design.
- Manuscript/proposal argument structure.
- Research claim evaluation.
- Interpretation of figures, datasets, diagnostics, or equations.
- Reusable idea, hypothesis, caveat, or open question.

Do not auto-capture:

- Ordinary coding/debugging with no research value.
- Secrets, keys, tokens, credentials, private paths, or sensitive personal data.
- Full article text, whole ChatGPT transcripts, browser captures, or PDFs.
- Copyrighted text beyond short excerpts.
- Anything prohibited by active project instructions.

## Commands

Use the helper to classify uncertain material:

```bash
python3 "${HOME}/Desktop/ResearchWiki/tools/rkf_auto_connect.py" classify "text to classify" --project-name "ProjectName"
```

Use existing RKF CLI for writes:

```bash
python3 "${HOME}/Desktop/ResearchWiki/tools/rk.py" inbox capture "Title" --origin "project:ProjectName" --clip "Short public-safe excerpt or summary." --reader-note "User idea or project relation."
python3 "${HOME}/Desktop/ResearchWiki/tools/rk.py" hot record "research question" --origin "project:ProjectName" --intent paper-search
```

For DOI material, include `--doi`. RKF will use guarded source/paper backlink injection and will not promote stable claims.

## Reporting

After auto-capture, report concisely:

- what was captured;
- where it went: inbox, hot.md, SourceRecord, or paper backlink;
- what was not promoted;
- any blocker.
```

- [ ] **Step 4: Verify config resolution**

Run:

```bash
python3 tools/rkf_auto_connect.py resolve
```

Expected: JSON with `researchwiki_root` ending in `Desktop/ResearchWiki` and `mode` equal to `active-aggressive`.

- [ ] **Step 5: Verify classification from the installed skill contract**

Run:

```bash
python3 tools/rkf_auto_connect.py classify "Find recent DOI 10.1234/example papers for aerosol-cloud parameterization" --project-name ResearchWiki
```

Expected: JSON with `"level": "aggressive"` or `"level": "active"` and targets containing `inbox` and `hot`.

### Task 4: Add User-Facing Workflow Documentation

**Files:**
- Create: `docs/workflows/rkf-auto-connect.zh-TW.md`
- Modify: `docs/FEATURES_AND_COMMANDS.zh-TW.md`
- Modify: `docs/PROJECT_MEMORY.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Create the workflow doc**

Create `docs/workflows/rkf-auto-connect.zh-TW.md` with this exact content:

```markdown
# RKF Auto-Connect Workflow

這份文件說明如何在任何 Codex 專案連結 RKF 資料庫，讓研究相關搜尋、DOI/URL lead、網頁 clip、ChatGPT 片段與有價值研究討論自動回饋到 RKF。

## 啟用方式

在專案中對 agent 說：

```text
連結我的 RKF 資料庫
```

Agent 會使用全域 `rkf-auto-connect` skill，從 `$HOME/.codex/rkf_connector.toml` 找到 ResearchWiki checkout，再由 ResearchWiki 的 `rkf.workspace.toml` 解析 live `wiki_root`。

## 自動記錄政策

RKF auto-connect 使用 Active/Aggressive hybrid policy。

Active trigger 會自動記錄：

- DOI、arXiv、PubMed、ISBN、dataset DOI；
- paper title、citation、journal/conference、literature search；
- 被用作 evidence 的重要 URL；
- 網頁短摘錄或 source-backed summary；
- 反覆出現、適合進 `hot.md` 的研究問題。

Aggressive research trigger 也會自動記錄：

- 文獻 synthesis 或比較；
- method、model、experiment design；
- manuscript/proposal argument；
- claim evaluation；
- figures、datasets、diagnostics、equations 的研究解讀；
- 可回用 idea、hypothesis、caveat、open question。

## 寫入位置

- 搜尋需求與反覆研究問題：`hot.md`
- ChatGPT/web/project clip：`knowledge/inbox/`
- DOI/URL source identity：`state/sources/*.json`
- DOI 相關 paper：guarded paper backlink
- 清楚 target source 的閱讀問題或修正：`state/reading/*.json`

## 不會自動做的事

- 不自動升級 stable claim。
- 不保存整篇 article text。
- 不保存整段私人 ChatGPT transcript。
- 不保存 PDF、browser capture、private path、secret 或個資。
- 不覆寫 project `AGENTS.md` 或既有 project memory。

## 專案範圍標記

如果要讓某專案長期記得 RKF auto-connect，可以在專案根目錄建立 `.rkf-connect.toml`：

```toml
[rkf_auto_connect]
enabled = true
mode = "active-aggressive"
config = "global"
```

這個檔案不得存 private Drive path；真正的 RKF 路徑由全域 config 與 `rkf.workspace.toml` 解析。

## 取消或暫停

在目前 session 可直接說：

```text
這個 thread 暫停 RKF auto-capture
```

專案層級則移除或停用 `.rkf-connect.toml`：

```toml
[rkf_auto_connect]
enabled = false
mode = "active-aggressive"
config = "global"
```

## 回報格式

Agent 自動記錄後應簡短回報：

```text
已自動記錄到 RKF: inbox + hot-query；沒有 promote stable claim。
```

如果因 private path、全文過長或 project rule 被擋，agent 應改成 pending capture proposal。
```

- [ ] **Step 2: Update command inventory**

In `docs/FEATURES_AND_COMMANDS.zh-TW.md`, add a row under core features:

```markdown
| Auto-connect helper | 跨專案偵測研究相關搜尋、DOI/URL、web clip 與有價值研究討論，並自動回饋到 RKF inbox/hot.md | global `rkf-auto-connect` skill、`tools/rkf_auto_connect.py` |
```

Add a short command example near the inbox/hot examples:

```markdown
Classify whether a cross-project discussion should be captured:

```bash
python3 tools/rkf_auto_connect.py classify "Find DOI 10.1234/example papers for aerosol-cloud parameterization" --project-name ResearchProject
```
```

- [ ] **Step 3: Update project memory**

In `docs/PROJECT_MEMORY.md`, add under Durable Decisions:

```markdown
- RKF auto-connect should be implemented as a global personal skill plus a small
  repo-side helper. Connected projects use Active/Aggressive hybrid capture:
  source-like material is captured actively, valuable research discussion is
  captured aggressively, and claim promotion remains conservative.
```

Add under Known Operational Traps:

```markdown
- Trap: making every project duplicate RKF routing rules. Fix: use the global
  `rkf-auto-connect` skill and keep project markers small and public-safe.
```

- [ ] **Step 4: Update changelog**

In `CHANGELOG.md`, add under Unreleased:

```markdown
- Add RKF auto-connect design and helper plan for cross-project Active/Aggressive
  capture into RKF inbox and hot-query layers.
```

### Task 5: Verification And Handoff

**Files:**
- Verify: `tools/rkf_auto_connect.py`
- Verify: `tests/test_rkf_auto_connect.py`
- Verify: docs changed in Task 4

- [ ] **Step 1: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_rkf_auto_connect
```

Expected: PASS.

- [ ] **Step 2: Run full tests**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: PASS.

- [ ] **Step 3: Compile Python files**

Run:

```bash
python3 -m py_compile tools/rk.py tools/rkf_auto_connect.py rkf/*.py tools/public_safety_scan.py
```

Expected: no output and exit code 0.

- [ ] **Step 4: Run RKF lint and public safety checks**

Run:

```bash
python3 tools/rk.py lint
python3 tools/rk.py topic lint
python3 tools/public_safety_scan.py
```

Expected:

```text
rkf all passed
topic lint passed
public_safety_scan passed
```

- [ ] **Step 5: Verify helper behavior manually**

Run:

```bash
python3 tools/rkf_auto_connect.py classify "This method could support WRF microphysics calibration design" --project-name QUACS
```

Expected: JSON with `level` set to `aggressive` and `targets` containing `inbox`.

- [ ] **Step 6: Review dirty worktree boundaries**

Run:

```bash
git status --short
git diff --stat
```

Expected: changes are limited to the auto-connect helper, tests, workflow docs, global skill/config if approved, and the previously existing RKF dirty files. Do not revert unrelated existing changes.

- [ ] **Step 7: Final handoff**

Report:

- which files were created or modified;
- whether the global skill/config was installed or skipped due to approval;
- test results;
- how to use the feature in another project;
- that no stable claims are auto-promoted.

Do not commit unless the user explicitly requests a commit.

## Plan Self-Review

- Spec coverage: covers global skill, config, project marker, Active/Aggressive triggers, negative triggers, RKF write targets, error handling, docs, and verification.
- Placeholder scan: no incomplete markers or vague implementation steps remain.
- Type consistency: the same names are used throughout: `ConnectorConfig`, `CaptureDecision`, `classify_capture`, `build_inbox_command`, `build_hot_command`, `.rkf-connect.toml`, and `rkf-auto-connect`.
- Scope check: one implementation plan is sufficient because the first version uses a helper plus skill docs, not a daemon or browser extension.
