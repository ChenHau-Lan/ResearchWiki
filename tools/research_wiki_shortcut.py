#!/usr/bin/env python3
"""Small command helper for Research Wiki.

The helper keeps paper-source intake in raw/paper_sources.md, preserves DOI
progress in raw/doi_dashboard.md, imports local evidence, starts Codex
handoffs, manages topics/subtopics, runs local maintenance, and rebuilds the
full_text index. It never deletes files.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()

DOI_LIST = ROOT / "raw" / "doi_list.md"
PAPER_SOURCES = ROOT / "raw" / "paper_sources.md"
DOI_DASHBOARD = ROOT / "raw" / "doi_dashboard.md"
FULL_TEXT_INDEX_JSON = ROOT / "raw" / "full_text_index.json"
FULL_TEXT_INDEX_MD = ROOT / "raw" / "full_text_index.md"
FULL_TEXT_DIR = ROOT / "raw" / "full_text"
DOI_PDF_DIR = ROOT / "raw" / "doi_pdf"
RAW_FILES_DIR = ROOT / "raw" / "files"
STAGING_TEXT_DIR = ROOT / "raw" / "staging" / "extracted_text"
WIKI_LIT = ROOT / "wiki" / "literature"
TOPICS = ROOT / "wiki" / "literature" / "topic_registry.md"
WIKI_SYNTHESIS = ROOT / "wiki" / "synthesis"
WIKI_MEETINGS = ROOT / "wiki" / "meetings"
WIKI_PROJECT_SYNTHESIS = ROOT / "wiki" / "project_synthesis"
WIKI_SEMINARS = ROOT / "wiki" / "seminars"
MAINTENANCE_DIR = ROOT / "maintenance"
OBSIDIAN_GRAPH_GUIDE = MAINTENANCE_DIR / "obsidian_graph_guide.md"
USER_GUIDE = ROOT / "USER_GUIDE.md"
CODEX_LAST_LOG = MAINTENANCE_DIR / "codex_last_run.log"
CODEX_APP_HANDOFF_PROMPT = MAINTENANCE_DIR / "codex_app_handoff_prompt.md"
CODEX_APP_LAST_LOG = MAINTENANCE_DIR / "codex_app_last_run.log"

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s<>)\]]+", re.IGNORECASE)
OLD_BOARD_HEADER = "| DOI | Status | Title | Full Text | Wiki Page | Next Action | Updated | Note |"
LEGACY_BOARD_HEADER = "| Paper | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
LEGACY_DETAIL_BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text | Next Action | Updated | Note |"
BOARD_HEADER = "| Last Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text |"
BOARD_SEPARATOR = "|---|---|---|---|---|---|---|"
NOTE_HEADER = "| DOI | Next Action | Updated | Note |"
NOTE_SEPARATOR = "|---|---|---|---|"
STATUSES = {
    "new",
    "metadata_ok",
    "full_text_needed",
    "full_text_done",
    "wiki_done",
    "abstract_only",
    "blocked",
}


def print_header() -> None:
    print("\nResearchWiki")
    print("=" * 12)
    print(f"Root: {ROOT}\n")


def pause() -> None:
    input("\nPress Enter to continue...")


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"{label}{suffix}: ").strip()
    except EOFError:
        return default
    return value or default


def open_path(path: Path) -> None:
    ensure_core_files()
    subprocess.run(["open", str(path)], cwd=ROOT)


def launch_codex() -> bool:
    if os.environ.get("RESEARCHWIKI_NO_OPEN") == "1":
        print("Codex launch skipped because RESEARCHWIKI_NO_OPEN=1.")
        return False
    proc = subprocess.run(["open", "-a", "Codex", str(ROOT)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode == 0:
        print("Codex launch requested for this project.")
        return True
    else:
        print("Could not launch Codex automatically. Open Codex manually and paste the prompt below.")
        if proc.stderr.strip():
            print(proc.stderr.strip())
        return False


def copy_to_clipboard(text: str) -> bool:
    if os.environ.get("RESEARCHWIKI_NO_OPEN") == "1":
        return False
    pbcopy = shutil.which("pbcopy")
    if not pbcopy:
        return False
    proc = subprocess.run([pbcopy], input=text, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.returncode == 0


def find_codex_binary() -> str | None:
    found = shutil.which("codex")
    if found:
        return found
    fallback = Path("/Applications/Codex.app/Contents/Resources/codex")
    if fallback.exists():
        return str(fallback)
    return None


def print_codex_process_status() -> None:
    proc = subprocess.run(["pgrep", "-if", "Codex"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if proc.returncode == 0 and proc.stdout.strip():
        print("Codex process appears to be running.")
    else:
        print("Codex process was not detected. If Codex is open under another process name, paste the prompt manually.")


def codex_env() -> dict[str, str]:
    env = os.environ.copy()
    path_parts = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]
    path_parts.extend(env.get("PATH", "").split(":"))
    seen: set[str] = set()
    env["PATH"] = ":".join(part for part in path_parts if part and not (part in seen or seen.add(part)))
    return env


def print_acquisition_result(rows: list[dict[str, str]], active_dois: set[str], failure_hint: str = "") -> None:
    print("\n== Acquisition Result ==")
    by_doi = {row["doi"]: row for row in rows}
    for doi in sorted(active_dois):
        row = by_doi.get(doi)
        if not row:
            print(f"- DOI: {doi}")
            print("  Result: failed - row missing from DOI dashboard after refresh")
            continue
        pdf = row.get("pdf") or "no_pdf"
        full_text = row.get("full_text") or "no_full_text"
        status = row.get("status") or "unknown"
        note = row.get("note") or row.get("next_action") or "no reason recorded"
        if row.get("full_text") and row.get("pdf"):
            result = "success - full text Markdown and PDF exist"
        elif row.get("full_text") and failure_hint:
            result = f"failed - full text exists, but PDF backfill failed: {failure_hint}"
        elif row.get("full_text"):
            result = "partial - full text Markdown exists, but PDF is missing"
        elif row.get("pdf"):
            result = "partial - PDF exists but full text Markdown is missing"
        elif failure_hint:
            result = f"failed - {failure_hint}"
        else:
            result = f"failed - {note}"
        print(f"- DOI: {doi}")
        print(f"  Paper: {row.get('paper') or 'unknown'} | Journal: {row.get('journal') or 'unknown'}")
        print(f"  Result: {result}")
        print(f"  Wiki Status: {status} | Access Legality: {row.get('access_legality') or 'unknown'}")
        print(f"  PDF: {pdf}")
        print(f"  Full Text: {full_text}")


def print_wiki_ingest_result(rows: list[dict[str, str]], active_dois: set[str], failure_hint: str = "") -> None:
    print("\n== Wiki Ingest Result ==")
    by_doi = {row["doi"]: row for row in rows}
    for doi in sorted(active_dois):
        row = by_doi.get(doi)
        if not row:
            print(f"- DOI: {doi}")
            print("  Result: failed - row missing from DOI dashboard after refresh")
            continue
        wiki_page = row.get("wiki_page") or "check wiki/literature"
        if row.get("status") == "wiki_done":
            result = "success - paper page updated"
        elif failure_hint:
            result = f"failed - {failure_hint}"
        else:
            result = f"needs check - status is {row.get('status') or 'unknown'}"
        print(f"- DOI: {doi}")
        print(f"  Paper: {row.get('paper') or 'unknown'} | Journal: {row.get('journal') or 'unknown'}")
        print(f"  Result: {result}")
        print(f"  Wiki Page: {wiki_page}")
        print(f"  Full Text: {row.get('full_text') or 'no_full_text'}")


def format_codex_status_line(text: str) -> str | None:
    index = text.find("RW_")
    if index == -1:
        return None
    payload = text[index:].strip()
    parts = [part.strip() for part in payload.split("|")]
    if any("<" in part and ">" in part for part in parts[1:]):
        return None
    tag = parts[0]
    if tag == "RW_STATUS" and len(parts) >= 3:
        return f"DOI: {parts[1]}\nTitle: {parts[2]}"
    if tag == "RW_ATTEMPT" and len(parts) >= 4:
        return f"Attempt: {parts[2]} ({parts[3]})"
    if tag == "RW_RESULT" and len(parts) >= 4:
        return f"Result: {parts[2]} - {parts[3]}"
    if tag == "RW_WIKI_PAGE" and len(parts) >= 3:
        return f"Wiki Page: {parts[2]}"
    if tag in {"RW_FILE", "RW_DASHBOARD"}:
        return None
    return payload


def start_codex_prompt(prompt_text: str, task_label: str, *, background: bool = True, reasoning_effort: str | None = None) -> None:
    if os.environ.get("RESEARCHWIKI_NO_OPEN") == "1":
        print("Codex launch skipped because RESEARCHWIKI_NO_OPEN=1.")
        print("\nPrompt that would be sent to Codex:\n")
        print(prompt_text)
        return

    codex = find_codex_binary()
    if codex:
        command = [
            codex,
            "--search",
            "exec",
            "--ephemeral",
            "--cd",
            str(ROOT),
            "--color",
            "never",
            "-c",
            "shell_environment_policy.inherit=all",
        ]
        if reasoning_effort:
            command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
        command.append(prompt_text)
        if background:
            MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
            header = (
                f"Research Wiki Codex handoff: {task_label}\n"
                f"Started: {datetime.now().isoformat(timespec='seconds')}\n\n"
                f"Reasoning effort: {reasoning_effort or 'default'}\n\n"
                "Prompt\n"
                "------\n"
                f"{prompt_text}\n\n"
                "Codex Output\n"
                "------------\n"
            )
            CODEX_LAST_LOG.write_text(header, encoding="utf-8")
            log_handle = CODEX_LAST_LOG.open("a", encoding="utf-8")
            proc = subprocess.Popen(
                command,
                cwd=ROOT,
                env=codex_env(),
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            log_handle.close()
            time.sleep(0.5)
            status = "running" if proc.poll() is None else f"exited with code {proc.returncode}"
            print(f"Started Codex background task for {task_label}.")
            print(f"PID: {proc.pid} ({status})")
            print(f"Log: {CODEX_LAST_LOG.relative_to(ROOT)}")
            print("The command menu is ready again; check the log or refresh the dashboard later.")
        else:
            print(f"Starting Codex for {task_label}.")
            print("Codex output will stay visible in this terminal until the session exits.")
            proc = subprocess.run(command, cwd=ROOT, env=codex_env())
            print(f"Codex session exited with code {proc.returncode}.")
            print_codex_process_status()
        return

    print("Codex CLI was not found. Opening Codex app instead.")
    launch_codex()
    print_codex_process_status()
    print("\nPaste this prompt in Codex:\n")
    print(prompt_text)


def run_codex_prompt_foreground(prompt_text: str, task_label: str, *, reasoning_effort: str | None = None) -> tuple[int, str]:
    if os.environ.get("RESEARCHWIKI_NO_OPEN") == "1":
        print("Codex launch skipped because RESEARCHWIKI_NO_OPEN=1.")
        print("\nPrompt that would be sent to Codex:\n")
        print(prompt_text)
        return 0, ""

    codex = find_codex_binary()
    if not codex:
        print("Codex CLI was not found. Opening Codex app instead.")
        launch_codex()
        print_codex_process_status()
        print("\nPaste this prompt in Codex:\n")
        print(prompt_text)
        return 1, "Codex CLI was not found; paste the prompt into the Codex app manually."

    MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        f"Research Wiki Codex handoff: {task_label}\n"
        f"Started: {datetime.now().isoformat(timespec='seconds')}\n\n"
        f"Reasoning effort: {reasoning_effort or 'default'}\n\n"
        "Prompt\n"
        "------\n"
        f"{prompt_text}\n\n"
        "Codex Output\n"
        "------------\n"
    )
    CODEX_LAST_LOG.write_text(header, encoding="utf-8")

    command = [
        codex,
        "--search",
        "exec",
        "--ephemeral",
        "--cd",
        str(ROOT),
        "--color",
        "never",
        "-c",
        "shell_environment_policy.inherit=all",
    ]
    if reasoning_effort:
        command.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])
    command.append(prompt_text)

    print(f"\nStarting Codex for {task_label}...")
    print(f"Reasoning effort: {reasoning_effort or 'default'}")
    print(f"Log: {CODEX_LAST_LOG.relative_to(ROOT)}")
    print("Acquisition status:")
    print("-" * 24)

    with CODEX_LAST_LOG.open("a", encoding="utf-8") as log_handle:
        shown_any = False
        failure_hint = ""
        proc = subprocess.Popen(
            command,
            cwd=ROOT,
            env=codex_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log_handle.write(line)
            log_handle.flush()
            text = line.rstrip()
            formatted = format_codex_status_line(text)
            if formatted:
                shown_any = True
                print(formatted)
            lowered = text.lower()
            if not failure_hint:
                if "readonly database" in lowered or "attempt to write a readonly database" in lowered:
                    failure_hint = "Codex CLI could not start because its state database is read-only in this environment."
                elif "failed to initialize in-process app-server client" in lowered:
                    failure_hint = "Codex CLI could not initialize the app-server client in this environment."
                elif "operation not permitted" in lowered and "codex" in lowered:
                    failure_hint = "Codex CLI hit an Operation not permitted startup error."
        return_code = proc.wait()

    print("-" * 24)
    if return_code != 0 and not shown_any and failure_hint:
        print(f"Result: failed - {failure_hint}")
    print(f"Codex finished with exit code {return_code}.")
    return return_code, failure_hint


def escape_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ").strip()


def split_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [part.strip().replace(r"\|", "|") for part in stripped.strip("|").split("|")]


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;")
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.lower()


def extract_dois(text: str) -> list[str]:
    seen: set[str] = set()
    dois: list[str] = []
    for match in DOI_RE.findall(text):
        doi = normalize_doi(match)
        if doi and doi not in seen:
            seen.add(doi)
            dois.append(doi)
    return dois


def normalize_source_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).rstrip()


def extract_urls(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_RE.findall(text):
        url = match.rstrip(".,;")
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def default_doi_list() -> str:
    return """# DOI List

Paste DOI values in the block below, one DOI per line.

This legacy file is still supported for DOI-only intake. New mixed DOI / URL
source pointers should go in `raw/paper_sources.md`.

## Add DOI Here

```text

```
"""


def default_paper_sources() -> str:
    return """# Paper Sources

Paste paper source pointers in the block below, one per line.

Accepted source pointers include DOI values, DOI URLs, article/publisher URLs,
PDF URLs, or short source notes that help locate a legal full text. Processing
progress is tracked in `raw/doi_dashboard.md` after a DOI or reliable metadata
is resolved.

## Add Sources Here

```text

```
"""


def default_doi_dashboard() -> str:
    initial_board = render_board(
        [
            {
                "paper": "conrick_2021",
                "journal": "waf",
                "doi": "10.1175/waf-d-21-0044.1",
                "status": "new",
                "access_legality": "unknown",
                "pdf": "",
                "full_text": "",
                "next_action": "acquire_full_text",
                "updated": TODAY,
                "note": "Test DOI for first acquisition check.",
            }
        ]
    )
    return f"""# DOI Dashboard

This board tracks where each resolved DOI is in the paper-source ingest process.

## DOI Status Board

{initial_board}

## Status Legend

- `new`: newly added, not processed yet.
- `metadata_ok`: title/authors/year/venue/DOI checked.
- `full_text_needed`: metadata exists, readable full text is missing.
- `full_text_done`: QCed `raw/full_text/<paper_file_key>.md` exists.
- `wiki_done`: `wiki/literature/<slug>.md` exists.
- `abstract_only`: only abstract was available; the paper page must say so.
- `blocked`: DOI/source/access problem needs human decision.
"""


def ensure_core_files() -> None:
    FULL_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    DOI_PDF_DIR.mkdir(parents=True, exist_ok=True)
    RAW_FILES_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_LIT.mkdir(parents=True, exist_ok=True)
    WIKI_SYNTHESIS.mkdir(parents=True, exist_ok=True)
    WIKI_MEETINGS.mkdir(parents=True, exist_ok=True)
    WIKI_PROJECT_SYNTHESIS.mkdir(parents=True, exist_ok=True)
    WIKI_SEMINARS.mkdir(parents=True, exist_ok=True)
    MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    (STAGING_TEXT_DIR / ".gitkeep").touch()
    if not DOI_LIST.exists():
        DOI_LIST.write_text(default_doi_list(), encoding="utf-8")
    if not PAPER_SOURCES.exists():
        PAPER_SOURCES.write_text(default_paper_sources(), encoding="utf-8")
    if not DOI_DASHBOARD.exists():
        DOI_DASHBOARD.write_text(default_doi_dashboard(), encoding="utf-8")

    # One-time migration support from the older combined doi_list.md.
    text = DOI_LIST.read_text(encoding="utf-8")
    if BOARD_HEADER in text or LEGACY_BOARD_HEADER in text or LEGACY_DETAIL_BOARD_HEADER in text or OLD_BOARD_HEADER in text:
        dashboard_text = DOI_DASHBOARD.read_text(encoding="utf-8")
        old_rows = parse_board(text)
        current_rows = parse_board(dashboard_text)
        rows_by_doi = {row["doi"]: row for row in current_rows}
        for row in old_rows:
            rows_by_doi.setdefault(row["doi"], row)
        DOI_DASHBOARD.write_text(replace_board(dashboard_text, list(rows_by_doi.values())), encoding="utf-8")
        _, _, quick_block = quick_add_block(text)
        DOI_LIST.write_text(replace_quick_add(default_doi_list(), extract_dois(quick_block)), encoding="utf-8")

    source_text = PAPER_SOURCES.read_text(encoding="utf-8")
    if "## Add Sources Here" not in source_text:
        PAPER_SOURCES.write_text(default_paper_sources().rstrip() + "\n\n" + source_text.strip() + "\n", encoding="utf-8")


def quick_add_block(text: str) -> tuple[int, int, str]:
    heading = re.search(r"(?m)^## (Add DOI Here|Quick Add)[ \t]*$", text)
    if not heading:
        return -1, -1, ""
    next_heading = re.search(r"(?m)^## .+$", text[heading.end() :])
    end = heading.end() + next_heading.start() if next_heading else len(text)
    block = text[heading.end() : end]
    return heading.end(), end, block


def replace_quick_add(text: str, new_dois: list[str]) -> str:
    start, end, _ = quick_add_block(text)
    block = (
        "\n\n```text\n"
        + "\n".join(new_dois)
        + ("\n" if new_dois else "")
        + "```\n"
    )
    if start == -1:
        return text.rstrip() + "\n\n## Add DOI Here" + block
    return text[:start] + block + text[end:]


def source_add_block(text: str) -> tuple[int, int, str]:
    heading = re.search(r"(?m)^## (Add Sources Here|Quick Add Sources)[ \t]*$", text)
    if not heading:
        return -1, -1, ""
    next_heading = re.search(r"(?m)^## .+$", text[heading.end() :])
    end = heading.end() + next_heading.start() if next_heading else len(text)
    block = text[heading.end() : end]
    return heading.end(), end, block


def parse_source_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_source_line(raw_line)
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        lines.append(line)
    return lines


def replace_source_add(text: str, sources: list[str]) -> str:
    start, end, _ = source_add_block(text)
    unique: list[str] = []
    seen: set[str] = set()
    for source in sources:
        normalized = normalize_source_line(source)
        key = normalized.lower()
        if normalized and key not in seen:
            unique.append(normalized)
            seen.add(key)
    block = (
        "\n\n```text\n"
        + "\n".join(unique)
        + ("\n" if unique else "")
        + "```\n"
    )
    if start == -1:
        return text.rstrip() + "\n\n## Add Sources Here" + block
    return text[:start] + block + text[end:]


def unresolved_source_lines() -> list[str]:
    ensure_core_files()
    source_text = PAPER_SOURCES.read_text(encoding="utf-8")
    _, _, source_block = source_add_block(source_text)
    return [line for line in parse_source_lines(source_block) if not extract_dois(line)]


def parse_board(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows_by_doi: dict[str, dict[str, str]] = {}
    in_board = ""
    for line in text.splitlines():
        if line.strip() in {BOARD_HEADER, LEGACY_BOARD_HEADER, LEGACY_DETAIL_BOARD_HEADER}:
            in_board = "new"
            continue
        if line.strip() == OLD_BOARD_HEADER:
            in_board = "old"
            continue
        if line.strip() == NOTE_HEADER:
            in_board = "notes"
            continue
        if not in_board:
            continue
        if line.strip().startswith("|---"):
            continue
        if line.strip() == "## DOI Notes":
            continue
        if line.startswith("## "):
            break
        parts = split_row(line)
        if not parts:
            continue
        if in_board == "new" and len(parts) in {7, 10}:
            doi = normalize_doi(parts[2])
            if not doi:
                continue
            status = parts[3] if parts[3] in STATUSES else "new"
            row = {
                "paper": parts[0],
                "journal": parts[1],
                "doi": doi,
                "status": status,
                "access_legality": parts[4],
                "pdf": parts[5],
                "full_text": parts[6],
                "wiki_page": "",
                "title": "",
                "next_action": parts[7] if len(parts) == 10 else "",
                "updated": parts[8] if len(parts) == 10 else "",
                "note": parts[9] if len(parts) == 10 else "",
            }
            rows.append(row)
            rows_by_doi[doi] = row
        elif in_board == "old" and len(parts) == 8:
            doi = normalize_doi(parts[0])
            if not doi:
                continue
            status = parts[1] if parts[1] in STATUSES else "new"
            row = {
                "paper": "",
                "journal": "",
                "doi": doi,
                "status": status,
                "access_legality": "",
                "pdf": "",
                "title": parts[2],
                "full_text": parts[3],
                "wiki_page": parts[4],
                "next_action": parts[5],
                "updated": parts[6],
                "note": parts[7],
            }
            rows.append(row)
            rows_by_doi[doi] = row
        elif in_board == "notes" and len(parts) == 4:
            doi = normalize_doi(parts[0])
            row = rows_by_doi.get(doi)
            if row:
                row["next_action"] = parts[1]
                row["updated"] = parts[2]
                row["note"] = parts[3]
    return rows


def render_board(rows: list[dict[str, str]]) -> str:
    lines = [BOARD_HEADER, BOARD_SEPARATOR]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                escape_cell(row.get(key, ""))
                for key in ["paper", "journal", "doi", "status", "access_legality", "pdf", "full_text"]
            )
            + " |"
        )
    lines.extend(["", "## DOI Notes", "", NOTE_HEADER, NOTE_SEPARATOR])
    for row in rows:
        lines.append(
            "| "
            + " | ".join(escape_cell(row.get(key, "")) for key in ["doi", "next_action", "updated", "note"])
            + " |"
        )
    return "\n".join(lines)


def replace_board(text: str, rows: list[dict[str, str]]) -> str:
    heading = re.search(r"(?m)^## DOI Status Board[ \t]*$", text)
    board = "\n\n" + render_board(rows) + "\n\n"
    if not heading:
        return text.rstrip() + "\n\n## DOI Status Board" + board
    next_heading = re.search(r"(?m)^## Status Legend[ \t]*$", text[heading.end() :])
    end = heading.end() + next_heading.start() if next_heading else len(text)
    return text[: heading.end()] + board + text[end:]


def local_path_exists(value: str) -> bool:
    if not value or re.match(r"^[a-z]+://", value, flags=re.IGNORECASE):
        return False
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / value
    return path.exists()


def parse_simple_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    result: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        if ":" not in raw_line or raw_line.startswith(" "):
            continue
        key, value = raw_line.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def full_text_is_qced(value: str) -> bool:
    if not value or not local_path_exists(value):
        return False
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / value
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_simple_frontmatter(text)
    status_blob = " ".join(
        [
            fm.get("extraction_status", ""),
            fm.get("readability_status", ""),
            fm.get("qc_status", ""),
        ]
    ).lower()
    if "machine_extracted_needs_codex_qc" in status_blob or "needs_codex_qc" in status_blob or "pending_codex_qc" in status_blob:
        return False
    return fm.get("extraction_status") == "codex_qc_done" or fm.get("qc_status") == "codex_qc_done"


def paper_page_needs_cleanup(value: str) -> bool:
    if not value or not local_path_exists(value):
        return False
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / value
    text = path.read_text(encoding="utf-8", errors="replace")
    redundant_markers = [
        "## Zotero / Citation Gate",
        "## Synthesis Update Needed",
        "## Full Text Evidence",
        "Temporary ID / DOI Slug",
        "User Question Trigger",
        "Reread Trigger",
        "Optional Translation MD:",
    ]
    return any(marker in text for marker in redundant_markers)


def repo_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def expected_pdf_path(row: dict[str, str]) -> Path | None:
    paper = row.get("paper", "").strip()
    journal = row.get("journal", "").strip()
    if not paper or not journal:
        return None
    return DOI_PDF_DIR / f"{paper}_{journal}.pdf"


def doi_suffix(doi: str) -> str:
    normalized = normalize_doi(doi)
    return normalized.split("/", 1)[1] if "/" in normalized else normalized


def slugify_key(value: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.lower())).strip("_")


def doi_suffix_variants(doi: str) -> set[str]:
    suffix = doi_suffix(doi)
    if not suffix:
        return set()
    variants = {
        suffix,
        suffix.replace("/", "-"),
        suffix.replace("/", "_"),
        suffix.replace("-", "_"),
        slugify_key(suffix),
    }
    return {variant.lower() for variant in variants if variant}


def filename_matches_doi(path: Path, row: dict[str, str]) -> bool:
    lowered_name = path.stem.lower()
    return any(variant and variant in lowered_name for variant in doi_suffix_variants(row.get("doi", "")))


def pdf_signature_ok(path: Path) -> bool:
    try:
        return path.read_bytes()[:5] == b"%PDF-"
    except OSError:
        return False


def pdf_text_preview(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return ""
    proc = subprocess.run(
        [pdftotext, "-f", "1", "-l", "3", str(path), "-"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return proc.stdout if proc.returncode == 0 else ""


def extract_pdf_doi(path: Path, preview: str = "") -> str:
    text = preview or pdf_text_preview(path)
    dois = extract_dois(text)
    if dois:
        return dois[0]

    # Some publisher PDF filenames contain only the DOI suffix.
    stem = path.stem.lower()
    if stem.startswith("wefo-waf-d-"):
        return normalize_doi("10.1175/" + stem.split("wefo-", 1)[1])
    if stem.startswith("acp-"):
        return normalize_doi("10.5194/" + stem)
    if stem.startswith("s41612-"):
        return normalize_doi("10.1038/" + stem)
    return ""


def pdf_text_extract(path: Path) -> tuple[str, str]:
    """Extract full text from a PDF using local tools only."""
    try:
        import fitz  # type: ignore[import-not-found]

        parts: list[str] = []
        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc, start=1):
                page_text = page.get_text("text").strip()
                if page_text:
                    parts.append(f"\n\n[Page {page_index}]\n\n{page_text}")
        text = "\n".join(parts).strip()
        if text:
            return text, "pymupdf"
    except Exception:
        pass

    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        proc = subprocess.run(
            [pdftotext, "-layout", str(path), "-"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip(), "pdftotext"

    return "", "unavailable"


def yaml_string(value: str) -> str:
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    return '"' + compact.replace("\\", "\\\\").replace('"', '\\"') + '"'


def infer_year(row: dict[str, str]) -> str:
    for value in [row.get("paper", ""), row.get("title", ""), row.get("note", "")]:
        match = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", value)
        if match:
            return match.group(1)
    return ""


def readable_title(row: dict[str, str], fallback: str) -> str:
    title = row.get("title", "").strip()
    if title:
        return title
    paper = row.get("paper", "").strip()
    return paper.replace("_", " ").title() if paper else fallback


def clean_pdf_lines(text: str, *, limit: int = 90) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines()[:limit]:
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return lines


def is_author_line(line: str) -> bool:
    if len(line) > 220:
        return False
    if re.search(r"\bet\s+al\.?$", line, re.IGNORECASE):
        return False
    if re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b", line):
        return False
    if re.search(
        r"\b(Abstract|Introduction|Received|Published|Atmospheric|Chemistry|Physics|ARTICLE|OPEN|European|Geosciences|Union|Author|License)\b",
        line,
    ):
        return False
    initial_author = r"^[A-Z]\.\s*(?:[A-Z]\.\s*){0,3}[A-Z][A-Za-z'`-]+\d*"
    full_author = r"^[A-Z][a-z]+(?:\s+[A-Z]\.){0,3}\s+[A-Z][A-Za-z'`-]+\d*"
    uppercase_author = r"^[A-Z][A-Z'`-]+\s+[A-Z][A-Z'`-]+[,a-z0-9 ]"
    if re.match(initial_author, line):
        return True
    if re.match(uppercase_author, line):
        return True
    return bool((("," in line) or re.search(r"\d", line)) and re.match(full_author, line))


def first_author_last_name(text: str) -> str:
    for line in clean_pdf_lines(text):
        if not is_author_line(line):
            continue
        first_author = re.split(r",|\band\b", line, maxsplit=1)[0]
        first_author = re.sub(r"\d+", "", first_author)
        first_author = first_author.replace("III", "").strip(" ,;")
        tokens = re.findall(r"[A-Za-z'`-]+", first_author)
        if tokens:
            return slugify_key(tokens[-1])
    return ""


def is_pdf_title_furniture(line: str) -> bool:
    if re.fullmatch(r"\d+", line):
        return True
    if re.search(r"\bet\s+al\.?$", line, re.IGNORECASE):
        return True
    if re.match(r"^(VOLUME|VOL\.|NO\.|NUMBER)\s+\d+", line, re.IGNORECASE):
        return True
    if re.match(
        r"^(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+(19|20)\d{2}$",
        line,
        re.IGNORECASE,
    ):
        return True
    if "downloaded" in line.lower() and "unauthenticated" in line.lower():
        return True
    return False


def pdf_title_hint(text: str) -> str:
    lines = clean_pdf_lines(text)
    author_index = next((index for index, line in enumerate(lines) if is_author_line(line)), -1)
    if author_index <= 0:
        return ""
    stop_re = re.compile(
        r"^(Atmos\. Chem\. Phys\.|Atmospheric Chemistry and Physics|Atmospheric$|Chemistry$|and Physics$|www\.|https?://|doi:|©|ARTICLE|OPEN|European Geosciences Union|Published by|SRef-ID|.*Creative Commons.*License)",
        re.IGNORECASE,
    )
    title_lines: list[str] = []
    for line in reversed(lines[max(0, author_index - 8) : author_index]):
        if stop_re.search(line):
            break
        if is_pdf_title_furniture(line):
            continue
        title_lines.append(line)
    title = " ".join(reversed(title_lines)).strip(" -")
    return title if len(title) >= 12 else ""


def infer_pdf_year(row: dict[str, str], text: str) -> str:
    existing = infer_year(row)
    if existing:
        return existing
    suffix = doi_suffix(row.get("doi", ""))
    match = re.search(r"(19|20)\d{2}", suffix)
    if match:
        return match.group(0)
    short_match = re.search(r"-(\d{2})-", suffix)
    if short_match:
        value = int(short_match.group(1))
        if value <= 40:
            return f"20{value:02d}"
        return f"19{value:02d}"
    nature_match = re.search(r"-(\d{3})-", suffix)
    if nature_match and nature_match.group(1).startswith("0"):
        return f"2{nature_match.group(1)}"
    journal_year = re.search(r"\((20\d{2}|19\d{2})\)", text[:2000])
    if journal_year:
        return journal_year.group(1)
    text_match = re.search(r"\b(19|20)\d{2}\b", text[:3000])
    return text_match.group(0) if text_match else ""


def infer_pdf_journal(row: dict[str, str], text: str) -> str:
    journal = row.get("journal", "").strip()
    if journal:
        return journal
    doi = normalize_doi(row.get("doi", ""))
    suffix = doi_suffix(doi)
    lowered = text[:3000].lower()
    if doi.startswith("10.5194/acp-") or "atmos. chem. phys." in lowered or "atmospheric chemistry and physics" in lowered:
        return "acp"
    if doi.startswith("10.1175/waf-d") or "weather and forecasting" in lowered:
        return "waf"
    if doi.startswith("10.1038/s41612") or "npj climate and atmospheric science" in lowered:
        return "npj_clim_atmos_sci"
    first_token = suffix.split("-", 1)[0]
    return slugify_key(first_token) if first_token else "unknown_journal"


def infer_pdf_key(row: dict[str, str], path: Path, text: str) -> tuple[str, str, str, str]:
    journal = infer_pdf_journal(row, text)
    year = infer_pdf_year(row, text)
    author = ""
    paper = row.get("paper", "").strip()
    if paper and re.search(r"_(19|20)\d{2}$", paper):
        author = paper.rsplit("_", 1)[0]
    if not author:
        author = first_author_last_name(text)
    title = row.get("title", "").strip() or pdf_title_hint(text)
    if author and year and journal:
        return f"{author}_{year}", journal, title, f"{author}_{year}_{journal}"
    fallback = slugify_key(doi_suffix(row.get("doi", "")) or path.stem)
    paper_fallback = f"{author}_{year}" if author and year else fallback
    return paper_fallback, journal, title, fallback


def render_staging_text_md(row: dict[str, str], pdf_path: Path, text: str, extractor: str) -> str:
    title = readable_title(row, pdf_path.stem.replace("_", " ").title())
    journal = row.get("journal", "")
    year = infer_year(row)
    source_pdf = repo_relative(pdf_path)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", text).strip()
    return "\n".join(
        [
            "---",
            f"doi: {yaml_string(row.get('doi', ''))}",
            f"title: {yaml_string(title)}",
            "authors: []",
            f"journal: {yaml_string(journal)}",
            f"journal_abbrev: {yaml_string(journal)}",
            f"year: {yaml_string(year)}",
            "source_type: authorized_pdf_text_extraction",
            f"source_pdf: {source_pdf}",
            "extraction_status: machine_extracted_needs_codex_qc",
            "readability_status: needs_codex_qc",
            "equation_quality: not_checked",
            "qc_status: pending_codex_qc",
            "language: en",
            f"created: {TODAY}",
            f"updated: {TODAY}",
            "---",
            "",
            f"# {title}",
            "",
            "## Source Metadata",
            "",
            f"- DOI: {row.get('doi', '')}",
            f"- Journal / venue: {journal or 'unknown'}",
            f"- Year: {year or 'unknown'}",
            f"- Source PDF: {source_pdf}",
            f"- Extraction tool: {extractor}",
            "",
            "## Extraction Notes",
            "",
            "- This Markdown was generated mechanically from an authorized local PDF.",
            "- It is staging text only. It must be reflowed and QCed before it can be copied to raw/full_text/.",
            "- Codex should reflow paragraphs, remove repeated page furniture, verify metadata, and set readability/equation/table QC fields before producing final full_text.",
            "",
            "## Extracted Full Text",
            "",
            cleaned,
            "",
        ]
    )


def render_qced_full_text_from_staging(staging_path: Path, text: str) -> str:
    """Deterministic test-mode stand-in for Codex reflow/QC."""
    text = text.replace("extraction_status: machine_extracted_needs_codex_qc", "extraction_status: codex_qc_done")
    text = text.replace("readability_status: needs_codex_qc", "readability_status: readable")
    text = text.replace("qc_status: pending_codex_qc", "qc_status: codex_qc_done")
    text = text.replace("equation_quality: not_checked", "equation_quality: not_applicable")
    text = re.sub(r"updated: .+", f"updated: {TODAY}", text, count=1)
    text = text.replace(
        "- It is staging text only. It must be reflowed and QCed before it can be copied to raw/full_text/.",
        "- This Markdown has been reflowed and QCed by the deterministic Research Wiki test stub.",
    )
    text = text.replace(
        "- Codex should reflow paragraphs, remove repeated page furniture, verify metadata, and set readability/equation/table QC fields before producing final full_text.",
        f"- Test-mode QC source: {repo_relative(staging_path)}.",
    )
    return text


def score_pdf_for_row(path: Path, row: dict[str, str], text: str) -> int:
    score = 0
    lowered_text = text.lower()
    lowered_name = path.name.lower()
    doi = row.get("doi", "")
    title = row.get("title", "")
    if doi:
        doi_variants = {doi.lower(), doi.lower().replace("/", "_"), doi.lower().replace("/", "-")}
        doi_variants.update(doi_suffix_variants(doi))
        for variant in doi_variants:
            if variant and (variant in lowered_text or variant in lowered_name):
                score += 8
                break
    if title and title.lower() in lowered_text:
        score += 6
    elif title:
        words = [word for word in re.findall(r"[a-z0-9]{5,}", title.lower()) if word not in {"during", "influence"}]
        hits = sum(1 for word in words[:8] if word in lowered_text)
        score += min(hits, 5)
    expected = expected_pdf_path(row)
    if expected and path.name.lower() == expected.name.lower():
        score += 10
    if row.get("paper") and row["paper"].lower() in lowered_name:
        score += 3
    if row.get("journal") and row["journal"].lower() in lowered_name:
        score += 2
    return score


def update_frontmatter_field(path: Path, updates: dict[str, str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end == -1:
        return False
    body_start = end + len("\n---")
    frontmatter = text[4:end].splitlines()
    body = text[body_start:]
    replaced: set[str] = set()
    new_lines: list[str] = []
    for line in frontmatter:
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key in updates:
            new_lines.append(f"{key}: {updates[key]}")
            replaced.add(key)
        else:
            new_lines.append(line)
        if key == "source_path" and "source_pdf" in updates and "source_pdf" not in replaced:
            new_lines.append(f"source_pdf: {updates['source_pdf']}")
            replaced.add("source_pdf")
    for key, value in updates.items():
        if key not in replaced:
            new_lines.append(f"{key}: {value}")
    new_text = "---\n" + "\n".join(new_lines).rstrip() + "\n---" + body
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def import_new_doi_pdfs(rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    ensure_core_files()
    messages: list[str] = []
    warnings: list[str] = []
    pdfs = sorted(
        path
        for path in DOI_PDF_DIR.glob("*.pdf")
        if path.is_file() and not path.name.startswith(".")
    )
    expected_paths = {
        expected.resolve()
        for row in rows
        for expected in [expected_pdf_path(row)]
        if expected is not None
    }
    current_paths = {
        (ROOT / row["pdf"]).resolve()
        for row in rows
        if row.get("pdf") and local_path_exists(row["pdf"])
    }
    extra_pdfs = [path for path in pdfs if path.resolve() not in expected_paths and path.resolve() not in current_paths]
    rows_missing_pdf = [row for row in rows if row.get("doi") and not row.get("pdf")]
    rows_by_doi = {normalize_doi(row["doi"]): row for row in rows if row.get("doi")}

    if not extra_pdfs:
        messages.append("No extra PDF files found in raw/doi_pdf/.")
        return messages, warnings

    used_rows: set[str] = set()
    for path in extra_pdfs:
        if not pdf_signature_ok(path):
            warnings.append(f"Skipped {repo_relative(path)} because it does not look like a PDF file.")
            continue
        preview = pdf_text_preview(path)
        pdf_doi = extract_pdf_doi(path, preview)
        if pdf_doi and pdf_doi not in rows_by_doi:
            new_row = {
                "paper": "",
                "journal": "",
                "doi": pdf_doi,
                "status": "new",
                "access_legality": "verified_source",
                "pdf": "",
                "title": "",
                "full_text": "",
                "wiki_page": "",
                "next_action": "import_evidence_and_create_qced_full_text",
                "updated": TODAY,
                "note": f"auto-created from orphan PDF {repo_relative(path)}",
            }
            rows.append(new_row)
            rows_by_doi[pdf_doi] = new_row
            rows_missing_pdf.append(new_row)
            messages.append(f"Added dashboard row for DOI {pdf_doi} from orphan PDF {repo_relative(path)}.")

        if pdf_doi and pdf_doi in rows_by_doi and rows_by_doi[pdf_doi].get("pdf"):
            warnings.append(
                f"Skipped duplicate-looking PDF {repo_relative(path)} because DOI {pdf_doi} already has {rows_by_doi[pdf_doi]['pdf']}."
            )
            continue

        direct_matches = []
        if pdf_doi and pdf_doi in rows_by_doi and not rows_by_doi[pdf_doi].get("pdf"):
            direct_matches.append(rows_by_doi[pdf_doi])
        direct_matches.extend(row for row in rows_missing_pdf if filename_matches_doi(path, row) and row not in direct_matches)
        if direct_matches:
            direct_row = direct_matches[0]
            if direct_row["doi"] in used_rows:
                warnings.append(f"Skipped duplicate-looking PDF {repo_relative(path)} for already imported DOI {direct_row['doi']}.")
                continue
            best_score, best_row = 100, direct_row
        else:
            scored = sorted(
                ((score_pdf_for_row(path, row, preview), row) for row in rows_missing_pdf if row["doi"] not in used_rows),
                key=lambda item: item[0],
                reverse=True,
            )
            if not scored:
                warnings.append(
                    f"Skipped {repo_relative(path)} because no DOI could be extracted and no dashboard row matched it. Add a DOI or source note to raw/paper_sources.md, or move non-DOI source files to raw/files/."
                )
                continue
            best_score, best_row = scored[0]

        if best_score < 5:
            if len(extra_pdfs) == 1 and len(rows_missing_pdf) == 1:
                best_row = rows_missing_pdf[0]
                warnings.append(
                    f"Low-confidence single-file match: {repo_relative(path)} -> {best_row['doi']}."
                )
            else:
                warnings.append(
                    f"Skipped {repo_relative(path)} because it did not clearly match a DOI row."
                )
                continue
        paper, journal, title, paper_file_key = infer_pdf_key(best_row, path, preview)
        if paper and not best_row.get("paper"):
            best_row["paper"] = paper
        if journal and not best_row.get("journal"):
            best_row["journal"] = journal
        if title and not best_row.get("title"):
            best_row["title"] = title
        target = DOI_PDF_DIR / f"{paper_file_key}.pdf"
        if target.exists():
            best_row["pdf"] = repo_relative(target)
            used_rows.add(best_row["doi"])
            if target.resolve() == path.resolve():
                messages.append(f"Linked existing canonical PDF {repo_relative(target)} for {best_row['doi']}.")
            else:
                warnings.append(f"Skipped duplicate-looking PDF {repo_relative(path)} because {repo_relative(target)} already exists.")
            continue
        path.rename(target)
        used_rows.add(best_row["doi"])
        source_pdf = repo_relative(target)
        if best_row.get("full_text") and local_path_exists(best_row["full_text"]):
            full_text_path = ROOT / best_row["full_text"]
            update_frontmatter_field(full_text_path, {"source_pdf": source_pdf, "updated": TODAY})
        best_row["pdf"] = source_pdf
        best_row["access_legality"] = best_row.get("access_legality") or "verified_source"
        best_row["next_action"] = "review_or_ask_question" if best_row.get("full_text") else "codex_convert_to_full_text"
        best_row["note"] = f"imported local PDF {source_pdf}"
        messages.append(f"Imported {repo_relative(path)} -> {source_pdf} for {best_row['doi']}.")
    return messages, warnings


def print_pdf_import_report(messages: list[str], warnings: list[str]) -> None:
    print("\n== DOI PDF Import ==")
    for message in messages:
        print(f"- {message}")
    for warning in warnings:
        print(f"- Warning: {warning}")


def extract_staging_text_from_doi_pdfs(rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    messages: list[str] = []
    warnings: list[str] = []
    for row in rows:
        pdf_ref = row.get("pdf", "")
        if not pdf_ref or not local_path_exists(pdf_ref):
            continue
        if row.get("full_text") and local_path_exists(row["full_text"]):
            continue
        pdf_path = ROOT / pdf_ref if not Path(pdf_ref).is_absolute() else Path(pdf_ref)
        target = STAGING_TEXT_DIR / f"{pdf_path.stem}.md"
        if target.exists():
            if row.get("status") != "wiki_done":
                row["status"] = "full_text_needed"
            row["next_action"] = "codex_convert_to_full_text"
            row["updated"] = TODAY
            row["note"] = row.get("note") or f"staging extraction found at {repo_relative(target)}; Codex conversion/QC needed"
            messages.append(f"Linked existing staging text {repo_relative(target)} for {row['doi']}.")
            continue

        text, extractor = pdf_text_extract(pdf_path)
        if not text:
            warnings.append(f"Could not extract text from {repo_relative(pdf_path)} because no PDF text extractor was available or extraction returned empty text.")
            row["next_action"] = "codex_convert_to_full_text"
            row["note"] = f"PDF found at {repo_relative(pdf_path)}, but local text extraction failed."
            row["updated"] = TODAY
            continue
        if len(text.strip()) < 1000:
            warnings.append(f"Skipped staging write for {repo_relative(pdf_path)} because extracted text was very short; inspect the PDF manually.")
            row["next_action"] = "inspect_pdf_or_convert_manually"
            row["note"] = f"PDF found at {repo_relative(pdf_path)}, but extracted text was too short for reliable full_text conversion."
            row["updated"] = TODAY
            continue

        target.write_text(render_staging_text_md(row, pdf_path, text, extractor), encoding="utf-8")
        staging_ref = repo_relative(target)
        if row.get("status") != "wiki_done":
            row["status"] = "full_text_needed"
        row["next_action"] = "codex_convert_to_full_text"
        row["updated"] = TODAY
        row["note"] = f"machine-extracted local PDF to staging {staging_ref}; Codex conversion/QC needed before full_text is created"
        row["access_legality"] = row.get("access_legality") or "verified_source"
        messages.append(f"Extracted {repo_relative(pdf_path)} -> {staging_ref} for {row['doi']} (not indexed until Codex QC creates raw/full_text).")
    if not messages and not warnings:
        messages.append("No DOI PDFs needed staging extraction.")
    return messages, warnings


def print_pdf_extraction_report(messages: list[str], warnings: list[str]) -> None:
    print("\n== PDF to Staging Text ==")
    for message in messages:
        print(f"- {message}")
    for warning in warnings:
        print(f"- Warning: {warning}")


def staging_path_for_row(row: dict[str, str]) -> Path | None:
    pdf_ref = row.get("pdf", "")
    if not pdf_ref or not local_path_exists(pdf_ref):
        return None
    pdf_path = ROOT / pdf_ref if not Path(pdf_ref).is_absolute() else Path(pdf_ref)
    candidate = STAGING_TEXT_DIR / f"{pdf_path.stem}.md"
    return candidate if candidate.exists() else None


def rows_needing_full_text_conversion(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    active: list[dict[str, str]] = []
    for row in rows:
        if row.get("full_text") and local_path_exists(row["full_text"]):
            continue
        staging = staging_path_for_row(row)
        if staging:
            active.append(row)
    return active


def test_stub_create_qced_full_text(rows: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    messages: list[str] = []
    warnings: list[str] = []
    for row in rows_needing_full_text_conversion(rows):
        staging = staging_path_for_row(row)
        if not staging:
            continue
        target = FULL_TEXT_DIR / f"{staging.stem}.md"
        if target.exists():
            row["full_text"] = repo_relative(target)
            row["status"] = "full_text_done" if row.get("status") != "wiki_done" else row["status"]
            row["next_action"] = "ingest_full_text_to_wiki"
            row["updated"] = TODAY
            row["note"] = f"existing QCed full_text found at {repo_relative(target)}"
            messages.append(f"Linked existing QCed full_text {repo_relative(target)} for {row['doi']}.")
            continue
        staging_text = staging.read_text(encoding="utf-8", errors="replace")
        target.write_text(render_qced_full_text_from_staging(staging, staging_text), encoding="utf-8")
        row["full_text"] = repo_relative(target)
        if row.get("status") != "wiki_done":
            row["status"] = "full_text_done"
        row["next_action"] = "ingest_full_text_to_wiki"
        row["updated"] = TODAY
        row["note"] = f"created QCed full_text from staging {repo_relative(staging)} using deterministic test stub"
        row["access_legality"] = row.get("access_legality") or "verified_source"
        messages.append(f"Created QCed full_text {repo_relative(target)} for {row['doi']}.")
    if not messages and not warnings:
        messages.append("No staging text needed full_text conversion.")
    return messages, warnings


def build_full_text_conversion_prompt(rows: list[dict[str, str]]) -> str:
    items: list[str] = []
    for row in rows:
        staging = staging_path_for_row(row)
        if not staging:
            continue
        target = FULL_TEXT_DIR / f"{staging.stem}.md"
        items.append(
            "\n".join(
                [
                    f"- DOI: {row['doi']}",
                    f"  Title: {row.get('title') or 'unknown'}",
                    f"  Paper: {row.get('paper') or 'unknown'}",
                    f"  Journal: {row.get('journal') or 'unknown'}",
                    f"  PDF: {row.get('pdf') or 'missing'}",
                    f"  Staging text: {repo_relative(staging)}",
                    f"  Target full_text: {repo_relative(target)}",
                ]
            )
        )
    target_lines = "\n".join(items)
    return f"""You are working inside this Research Wiki project.

First read and follow the command-independent core contract:
- core/principles.md
- core/data_contract.md
- core/agent_contract.md
- core/skills/research-wiki-fulltext-acquisition/SKILL.md

Goal:
Convert staging machine extraction into QCed readable full text. Do not create or update wiki/literature pages in this task.

Target staging files:
{target_lines}

Rules:
0. Core contract is authoritative. If these command instructions conflict with core/*, follow core/* and report the mismatch.
1. Read each staging text and source PDF listed above.
2. Reflow broken line wraps and hyphenation where clear.
3. Remove repeated page headers/footers, page numbers, duplicated publisher furniture, and extraction boilerplate when safe.
4. Preserve the complete article body, section order, figure/table captions, references, appendices, and important limitations. Do not summarize or omit body sections.
5. Verify DOI/title/metadata against the staging text and PDF. If staging text and PDF disagree, do not write final full_text for that DOI; update the dashboard note with the blocker.
6. Write final readable Markdown only to raw/full_text/<paper_file_key>.md. Do not put pending machine extraction in raw/full_text/.
7. Final full_text frontmatter must use:
   - extraction_status: codex_qc_done
   - readability_status: readable, readable-with-warnings, or poor
   - qc_status: codex_qc_done
   - equation_quality: good, partial, poor, or not_applicable
8. If conversion succeeds, update raw/doi_dashboard.md for that DOI: Status = full_text_done, Full Text = raw/full_text/<paper_file_key>.md, Next Action = ingest_full_text_to_wiki.
9. If conversion fails, keep Status = full_text_needed, keep Full Text empty, set Next Action = codex_convert_to_full_text, and record a concise blocker.
10. Run python3 tools/build_full_text_index.py after writing final full_text.

Console output protocol:
- Emit concise progress lines only with these exact prefixes:
  - RW_STATUS|<doi>|<paper title>
  - RW_ATTEMPT|<doi>|convert_staging_to_qced_full_text|<staging_path>
  - RW_RESULT|<doi>|success|<reason>
  - RW_RESULT|<doi>|failed|<reason>
  - RW_FILE|<doi>|<pdf_path_or_none>|<full_text_path_or_none>
  - RW_DASHBOARD|<doi>|<wiki_status>|<access_legality>|<next_action>
- Do not emit the example protocol lines themselves. Never emit angle-bracket placeholders as real progress.
"""


def create_qced_full_text(rows: list[dict[str, str]]) -> tuple[list[str], list[str], bool]:
    active = rows_needing_full_text_conversion(rows)
    if not active:
        return ["No staging text needed full_text conversion."], [], False
    if os.environ.get("RESEARCHWIKI_TEST_QC_FAIL") == "1":
        for row in active:
            staging = staging_path_for_row(row)
            row["status"] = "full_text_needed"
            row["full_text"] = ""
            row["next_action"] = "codex_convert_to_full_text"
            row["updated"] = TODAY
            row["note"] = f"test-mode QC failure for staging {repo_relative(staging) if staging else 'missing'}"
        return [], ["Test-mode QC failure; no raw/full_text files were created."], True
    if os.environ.get("RESEARCHWIKI_TEST_QC_STUB") == "1":
        messages, warnings = test_stub_create_qced_full_text(rows)
        return messages, warnings, True
    prompt_text = build_full_text_conversion_prompt(active)
    return_code, failure_hint = run_codex_prompt_foreground(
        prompt_text,
        "full_text conversion and QC",
        reasoning_effort="high",
    )
    if return_code != 0:
        warning = failure_hint or "Codex full_text conversion did not complete."
        for row in active:
            row["status"] = "full_text_needed"
            row["next_action"] = "codex_convert_to_full_text"
            row["updated"] = TODAY
            row["note"] = warning
        return [], [warning], False
    return ["Codex full_text conversion completed or prompt was emitted; refresh the dashboard/index for final status."], [], False


def print_full_text_conversion_report(messages: list[str], warnings: list[str]) -> None:
    print("\n== Staging to QCed Full Text ==")
    for message in messages:
        print(f"- {message}")
    for warning in warnings:
        print(f"- Warning: {warning}")


def write_dashboard_rows(rows: list[dict[str, str]]) -> None:
    dashboard_text = DOI_DASHBOARD.read_text(encoding="utf-8")
    DOI_DASHBOARD.write_text(replace_board(dashboard_text, rows), encoding="utf-8")


def build_full_text_index_quiet() -> str:
    proc = subprocess.run(
        ["python3", "tools/build_full_text_index.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.stdout if proc.returncode == 0 else proc.stdout


def load_full_text_index() -> dict[str, dict[str, str]]:
    if not FULL_TEXT_INDEX_JSON.exists():
        return {}
    try:
        data = json.loads(FULL_TEXT_INDEX_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    result: dict[str, dict[str, str]] = {}
    for entry in data.get("entries", []):
        doi = normalize_doi(str(entry.get("doi", "")))
        if doi:
            checked = dict(entry)
            for key in ("readable_md", "wiki_page", "zh_full_md"):
                if checked.get(key) and not local_path_exists(str(checked[key])):
                    checked[key] = ""
            result[doi] = checked
    return result


def extract_bullet(label: str, text: str) -> str:
    match = re.search(rf"^-\s*{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def scan_wiki_by_doi() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for path in sorted(WIKI_LIT.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        doi = normalize_doi(extract_bullet("DOI", text))
        if not doi:
            continue
        reading_status = extract_bullet("Reading Status", text)
        title = extract_bullet("Title", text) or path.stem
        result[doi] = {
            "wiki_page": path.relative_to(ROOT).as_posix(),
            "title": title,
            "reading_status": reading_status,
        }
    return result


def journal_abbrev(text: str) -> str:
    lowered = text.lower()
    mappings = {
        "weather and forecasting": "waf",
        "bulletin of the american meteorological society": "bams",
        "atmospheric chemistry and physics": "acp",
        "frontiers in earth science": "front_earth_sci",
        "remote sensing": "remote_sens",
        "plos one": "plos_one",
    }
    for name, abbrev in mappings.items():
        if name in lowered:
            return abbrev
    return ""


def infer_paper_and_journal(
    row: dict[str, str],
    title: str,
    index_entry: dict[str, str],
    wiki_entry: dict[str, str],
) -> tuple[str, str]:
    paper = row.get("paper", "").strip()
    journal = row.get("journal", "").strip()
    note = row.get("note", "")

    expected = re.search(r"Expected key:\s*([a-z0-9_]+)", note, flags=re.IGNORECASE)
    if expected:
        tokens = expected.group(1).lower().split("_")
        if len(tokens) >= 3 and re.fullmatch(r"(19|20)\d{2}", tokens[1]):
            paper = paper or f"{tokens[0]}_{tokens[1]}"
            journal = journal or "_".join(tokens[2:])

    if not paper:
        source = " ".join([wiki_entry.get("wiki_page", ""), title, note])
        year_match = re.search(r"\b(19|20)\d{2}\b", source)
        stem = Path(wiki_entry.get("wiki_page", "")).stem
        last_name = stem.split("_", 1)[0] if stem else ""
        if last_name and year_match:
            paper = f"{last_name.lower()}_{year_match.group(0)}"

    if not journal:
        journal = (
            str(index_entry.get("journal_abbrev") or "")
            or journal_abbrev(str(index_entry.get("journal") or ""))
            or journal_abbrev(note)
            or journal_abbrev(title)
        )

    return paper, journal


def find_named_artifact(folder: Path, paper: str, journal: str, suffix: str) -> str:
    candidates: list[Path] = []
    if paper and journal:
        candidates.append(folder / f"{paper}_{journal}{suffix}")
    if paper:
        candidates.extend(sorted(folder.glob(f"{paper}_*{suffix}")))
    for path in candidates:
        if path.is_file() and not path.name.startswith("."):
            return path.relative_to(ROOT).as_posix()
    return ""


def infer_access_legality(row: dict[str, str], status: str, note: str, pdf: str, full_text: str) -> str:
    existing = row.get("access_legality", "").strip()
    if existing and existing != "unknown":
        return existing
    lowered = " ".join([note, row.get("next_action", "")]).lower()
    if full_text or pdf:
        return "verified_source"
    if "403" in lowered or "blocked" in lowered or "authorized" in lowered:
        return "authorized_needed"
    if status == "blocked":
        return "blocked"
    return existing or "unknown"


def refreshed_row(row: dict[str, str], index: dict[str, dict[str, str]], wiki: dict[str, dict[str, str]]) -> dict[str, str]:
    doi = normalize_doi(row["doi"])
    index_entry = index.get(doi, {})
    wiki_entry = wiki.get(doi, {})
    title = index_entry.get("title") or wiki_entry.get("title") or row.get("title", "")
    row_full_text = row.get("full_text", "") if full_text_is_qced(row.get("full_text", "")) else ""
    full_text = index_entry.get("readable_md") or row_full_text
    pdf = row.get("pdf", "") if local_path_exists(row.get("pdf", "")) else ""
    if not pdf and local_path_exists(str(index_entry.get("source_pdf") or "")):
        pdf = str(index_entry.get("source_pdf") or "")
    wiki_page = index_entry.get("wiki_page") or wiki_entry.get("wiki_page") or (
        row.get("wiki_page", "") if local_path_exists(row.get("wiki_page", "")) else ""
    )
    reading_status = (wiki_entry.get("reading_status") or "").lower()
    fulltext_status = str(index_entry.get("fulltext_status") or "").lower()
    readability_status = str(index_entry.get("readability_status") or "").lower()
    full_text_needs_qc = (
        "needs_codex_qc" in fulltext_status
        or "needs_codex_qc" in readability_status
        or "pending_codex_qc" in fulltext_status
        or "pending_codex_qc" in readability_status
        or "needs-human-review" in readability_status
        or index_entry.get("dispatch_status") == "fulltext_qc_needed"
    )
    paper, journal = infer_paper_and_journal(row, title, index_entry, {**wiki_entry, "wiki_page": wiki_page})
    if not pdf:
        pdf = find_named_artifact(DOI_PDF_DIR, paper, journal, ".pdf")
    if not full_text:
        candidate_full_text = find_named_artifact(FULL_TEXT_DIR, paper, journal, ".md")
        full_text = candidate_full_text if full_text_is_qced(candidate_full_text) else ""

    if full_text and full_text_needs_qc:
        status = "full_text_needed"
        next_action = "codex_convert_to_full_text"
        note = "pending full_text found outside contract; Codex conversion/QC needed before indexing"
    elif full_text and wiki_page and ("full-read" in reading_status or "reproduced" in reading_status):
        status = "wiki_done"
        if pdf:
            next_action = "review_or_ask_question"
            note = "full text, PDF, and full-read paper page found"
        else:
            next_action = "backfill_pdf_optional"
            note = "wiki_done from full text; local PDF missing"
    elif full_text and wiki_page:
        status = "full_text_done"
        next_action = "ingest_full_text_to_wiki"
        note = "full text found; paper page needs full-read ingest"
    elif full_text:
        status = "full_text_done"
        next_action = "ingest_full_text_to_wiki"
        note = "full text found"
    elif pdf:
        status = "full_text_needed"
        next_action = "codex_convert_to_full_text"
        staging = staging_path_for_row({**row, "pdf": pdf})
        if staging:
            note = f"staging extraction found at {repo_relative(staging)}; QCed full_text Markdown missing"
        else:
            note = "PDF found; readable full text Markdown missing"
    elif wiki_page and "abstract-only" in reading_status:
        status = "abstract_only"
        next_action = row.get("next_action") or "acquire_full_text"
        note = row.get("note") or "abstract-only paper page found"
    elif wiki_page:
        status = "metadata_ok"
        next_action = "check_or_get_full_text"
        note = "paper page found, full text not indexed"
    else:
        existing_status = row.get("status") if row.get("status") in STATUSES else "new"
        stale_completed = row.get("status") in {"full_text_done", "wiki_done"}
        if existing_status in {"metadata_ok", "full_text_needed"}:
            status = existing_status
            next_action = row.get("next_action") or ("get_full_text" if existing_status == "full_text_needed" else "check_or_get_full_text")
            note = row.get("note") or "waiting for full text"
        elif stale_completed or title:
            status = "full_text_needed"
            next_action = "get_full_text"
            note = "full text path missing; refresh downgraded status"
        else:
            status = "new"
            next_action = "acquire_full_text"
            note = row.get("note") or "waiting for full-text acquisition"

    if row.get("status") == "blocked" and not (pdf or full_text):
        status = "blocked"
        next_action = row.get("next_action") or "fix_source_or_access"
        note = row.get("note") or note

    access_legality = infer_access_legality(row, status, note, pdf, full_text)

    return {
        "paper": paper,
        "journal": journal,
        "doi": doi,
        "status": status,
        "access_legality": access_legality,
        "pdf": pdf,
        "title": title,
        "full_text": full_text,
        "wiki_page": wiki_page,
        "next_action": next_action,
        "updated": TODAY,
        "note": note,
    }


def sync_doi_board() -> list[dict[str, str]]:
    ensure_core_files()
    doi_text = DOI_LIST.read_text(encoding="utf-8")
    source_text = PAPER_SOURCES.read_text(encoding="utf-8")
    dashboard_text = DOI_DASHBOARD.read_text(encoding="utf-8")
    _, _, quick_block = quick_add_block(doi_text)
    quick_dois = extract_dois(quick_block)
    _, _, source_block = source_add_block(source_text)
    source_lines = parse_source_lines(source_block)
    source_dois = extract_dois("\n".join(source_lines))
    unresolved_sources = [line for line in source_lines if not extract_dois(line)]
    existing_rows = parse_board(dashboard_text)

    rows_by_doi: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for row in existing_rows:
        doi = normalize_doi(row["doi"])
        if doi and doi not in rows_by_doi:
            rows_by_doi[doi] = row
            order.append(doi)
    for doi in quick_dois + source_dois:
        if doi not in rows_by_doi:
            rows_by_doi[doi] = {
                "paper": "",
                "journal": "",
                "doi": doi,
                "status": "new",
                "access_legality": "unknown",
                "pdf": "",
                "title": "",
                "full_text": "",
                "wiki_page": "",
                "next_action": "acquire_full_text",
                "updated": TODAY,
                "note": "from paper_sources" if doi in source_dois else "from doi_list",
            }
            order.append(doi)

    index = load_full_text_index()
    wiki = scan_wiki_by_doi()
    rows = [refreshed_row(rows_by_doi[doi], index, wiki) for doi in order]

    DOI_LIST.write_text(replace_quick_add(doi_text, []), encoding="utf-8")
    PAPER_SOURCES.write_text(replace_source_add(source_text, unresolved_sources), encoding="utf-8")
    DOI_DASHBOARD.write_text(replace_board(dashboard_text, rows), encoding="utf-8")
    return rows


def add_or_open_paper_sources() -> None:
    ensure_core_files()
    value = prompt("Paste DOI / DOI URL / article URL / PDF URL, or press Enter to open raw/paper_sources.md")
    if not value:
        open_path(PAPER_SOURCES)
        return
    incoming_lines = [normalize_source_line(line) for line in value.splitlines() if normalize_source_line(line)]
    if not incoming_lines:
        print("No source pointers found.")
        return

    source_text = PAPER_SOURCES.read_text(encoding="utf-8")
    existing_sources = {line.lower() for line in parse_source_lines(source_text)}
    existing_dois = set(extract_dois(source_text + "\n" + DOI_LIST.read_text(encoding="utf-8") + "\n" + DOI_DASHBOARD.read_text(encoding="utf-8")))
    new_sources: list[str] = []
    for source in incoming_lines:
        source_dois = extract_dois(source)
        if source_dois and all(doi in existing_dois for doi in source_dois):
            continue
        if source.lower() in existing_sources:
            continue
        new_sources.append(source)
    if not new_sources:
        print("All source pointers already exist in raw/paper_sources.md or raw/doi_dashboard.md.")
        return

    _, _, source_block = source_add_block(source_text)
    current_sources = parse_source_lines(source_block)
    PAPER_SOURCES.write_text(replace_source_add(source_text, current_sources + new_sources), encoding="utf-8")
    print(f"Added {len(new_sources)} source pointer(s) to raw/paper_sources.md.")
    print("Progress will appear in raw/doi_dashboard.md after source resolution or DOI sync.")


def active_acquisition_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if (
            row["status"] in {"new", "metadata_ok", "abstract_only", "blocked"}
            or (row["status"] == "full_text_needed" and not row.get("full_text"))
        )
        or (row.get("full_text") and not row.get("pdf"))
    ]


def build_full_text_acquisition_prompt(active: list[dict[str, str]], *, app_handoff: bool = False) -> str:
    doi_lines = "\n".join(
        f"- DOI: {row['doi']}\n  Title: {row.get('title') or 'unknown'}\n  Paper: {row.get('paper') or 'unknown'}\n  Journal: {row.get('journal') or 'unknown'}\n  Current wiki status: {row['status']}\n  Next action: {row['next_action']}"
        for row in active
    )
    app_log_rule = ""
    if app_handoff:
        app_log_rule = f"""

Codex app handoff logging:
- This task was launched from ResearchWiki.command app handoff mode.
- Append concise execution notes to {display_path(CODEX_APP_LAST_LOG)} as you work.
- Log at least: started time, target DOI, title, each acquisition route attempted, success/failure reason, PDF path, full_text path, dashboard status, and unresolved blockers.
- Do not paste full article text into the log.
- If you cannot write the log file, say so in your final response.
"""
    return f"""You are working inside this Research Wiki project.

First read and follow the command-independent core contract:
- core/principles.md
- core/data_contract.md
- core/agent_contract.md
- core/skills/research-wiki-fulltext-acquisition/SKILL.md

Then use AGENTS.md and USER_GUIDE.md for repository-specific implementation details. ResearchWiki.command is only a UI implementation of the core contract.

Target DOI rows:
{doi_lines}
{app_log_rule}

Goal:
Source/full-text finding for rows that need authorized evidence. Acquire or identify missing authorized evidence only: PDF, publisher HTML/XML, readable full text, or a clear legal source route. Do not create or update wiki/literature paper pages in this task. Wiki-page ingest is a separate command option.

Rules:
0. Core contract is authoritative. If these command instructions conflict with core/*, follow core/* and report the mismatch.
1. Check raw/doi_dashboard.md, raw/doi_pdf/, raw/full_text/, raw/full_text_index.*, and raw/files/ first to avoid duplicates.
2. Verify DOI metadata: title, authors, venue/year, DOI, and canonical URL. Do not fabricate metadata.
3. Use paper-based filenames, not DOI-based filenames. Build `paper_file_key` as `<first_author_last_name>_<year>_<journal_abbrev>`, all lowercase ASCII, punctuation removed, spaces changed to underscores. Prefer standard journal abbreviations when known, for example `waf`, `bams`, `acp`, `front_earth_sci`, `remote_sens`, `plos_one`.
4. If metadata is incomplete, temporarily use `<first_author_last_name>_<year>_<short_journal_slug>` and revise it after verification. If two papers collide, append a short DOI slug such as `_waf_d_21_0044_1`.
5. If Full Text already exists but PDF is missing, treat this as PDF backfill. Do not redo the full text unless it is incomplete or mismatched.
6. If a PDF is obtained, save it as raw/doi_pdf/<paper_file_key>.pdf.
7. Do not write pending machine extraction to raw/full_text/. If you capture machine text, put it in raw/staging/extracted_text/ or leave instructions for option 6.
8. Only write raw/full_text/<paper_file_key>.md if the text has already been reflowed, QCed, and frontmatter says extraction_status: codex_qc_done and qc_status: codex_qc_done.
9. This command is not the default high-volume DOI path. For routine rows, prefer the semi-automatic flow: option 5 opens authorized source pages, the user saves PDFs into raw/doi_pdf/, option 6 imports evidence and creates QCed raw/full_text, and option 7 ingests wiki pages.
10. Spend reasoning on legal source selection, metadata verification, filename correctness, and completeness checks. Do not spend time on exhaustive publisher-route chasing, broad web searches, or research synthesis.
11. For each DOI, try existing local evidence, obvious open publisher HTML/XML/PDF, and visible authorized browser PDF controls. If those do not work promptly, update the dashboard to `full_text_needed`, set Next Action to `authorized_browser_or_user_pdf_needed`, and move on.
12. If the user/browser can view the article page and click the PDF button, treat that as authorized browser-session access. Do not mark blocked only because shell curl/wget/programmatic fetch returns 403.
13. For the current WAF test DOI, try normal DOI landing first, then candidate AMS paths such as:
   - https://journals.ametsoc.org/view/journals/wefo/36/4/WAF-D-21-0044.1.xml
   - https://journals.ametsoc.org/downloadpdf/journals/wefo/36/4/WAF-D-21-0044.1.pdf
   - https://journals.ametsoc.org/doi/pdf/10.1175/WAF-D-21-0044.1
   If direct fetch returns CloudFront 403, switch to browser-session PDF download: open the DOI/article page in an authorized browser session, click the visible PDF/Download PDF control, save or import the resulting PDF to raw/doi_pdf/<paper_file_key>.pdf, then verify title/DOI.
14. For AMS / AMETSOC papers, do not bypass CloudFront, CAPTCHA, robots, or access controls. AMS says WAF and other technical journals are free to read after 12 months, so prefer normal AMS Journals Online article/PDF pages and visible browser PDF controls.
15. If browser automation is available, use it to download the visible publisher PDF automatically. If automation cannot access the browser session, open the page for the user and ask for manual click/download only as the fallback.
16. If a PDF is obtained, save/import it and let option 6 perform staging extraction plus Codex reflow/QC into final raw/full_text. Do not stop at PDF-only unless source access or extraction is blocked.
17. Run python3 tools/build_full_text_index.py after adding or changing full text/PDF metadata.
18. Update raw/doi_dashboard.md only for acquisition state:
    - full text Markdown exists: Status = full_text_done, Full Text = raw/full_text/<paper_file_key>.md, Next Action = ingest_full_text_to_wiki.
    - PDF exists but QCed Markdown is not complete: keep Status = full_text_needed, Full Text empty, Next Action = codex_convert_to_full_text, Note includes raw/doi_pdf/<paper_file_key>.pdf.
    - full text and wiki page already exist, and this task only backfilled PDF: keep Status = wiki_done, set PDF = raw/doi_pdf/<paper_file_key>.pdf, update the full-text Markdown frontmatter `source_pdf` to that path, and set Next Action = review_or_ask_question.
    - access is still blocked: Status = blocked or full_text_needed with a clear Note.
19. Do not newly mark wiki_done in this task. Do not write synthesis.
20. In your final response, explicitly list:
    - PDF path created, or why no PDF was created.
    - full_text Markdown path created, or why no Markdown was created.
    - dashboard status and next action.

Console output protocol:
- Emit concise progress lines only with these exact prefixes so ResearchWiki.command can show the important parts:
  - RW_STATUS|<doi>|<paper title>
  - RW_ATTEMPT|<doi>|<method>|<url_or_source>
  - RW_RESULT|<doi>|success|<reason>
  - RW_RESULT|<doi>|failed|<reason>
  - RW_FILE|<doi>|<pdf_path_or_none>|<full_text_path_or_none>
  - RW_DASHBOARD|<doi>|<wiki_status>|<access_legality>|<next_action>
- The command displays only DOI/title, attempts, and success/failure reason. File and dashboard lines are kept in the full log.
- Do not emit the example protocol lines themselves. Never emit angle-bracket placeholders such as `<doi>` or `<reason>` as real progress.
- Keep normal prose short.
"""


def show_active_acquisition_rows(active: list[dict[str, str]]) -> None:
    print("\n== Full-Text Acquisition ==")
    for row in active:
        print(f"DOI: {row['doi']}")
        print(f"Title: {row.get('title') or 'unknown'}")
        print("")


def write_codex_app_handoff_prompt(prompt_text: str) -> None:
    MAINTENANCE_DIR.mkdir(parents=True, exist_ok=True)
    CODEX_APP_LAST_LOG.write_text(
        "Research Wiki Codex app handoff\n"
        f"Generated: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Prompt file: {display_path(CODEX_APP_HANDOFF_PROMPT)}\n"
        "Status: awaiting Codex app execution\n\n"
        "The Codex app run should append concise acquisition notes below.\n\n",
        encoding="utf-8",
    )
    CODEX_APP_HANDOFF_PROMPT.write_text(
        "---\n"
        "type: maintenance\n"
        "status: draft\n"
        "source_status: personal-note\n"
        "topics: []\n"
        "subtopics: []\n"
        f"created: {TODAY}\n"
        f"updated: {TODAY}\n"
        "sources: []\n"
        "---\n\n"
        "# Codex App DOI Acquisition Prompt\n\n"
        "Paste the prompt below into a Codex app conversation opened in this repository.\n\n"
        "```text\n"
        f"{prompt_text.rstrip()}\n"
        "```\n\n"
        "## Graph Links\n\n"
        "- Topics:\n"
        "- Subtopics:\n"
        "- Related literature:\n"
        "- Related synthesis:\n"
        "- Related seminars:\n"
        "- Related projects:\n",
        encoding="utf-8",
    )


def prepare_codex_app_acquisition_prompt() -> None:
    rows = sync_doi_board()
    active = active_acquisition_rows(rows)
    if not active:
        print("\nNo DOI rows currently need full-text/PDF acquisition. Check raw/doi_dashboard.md.")
        return

    show_active_acquisition_rows(active)
    prompt_text = build_full_text_acquisition_prompt(active, app_handoff=True)
    write_codex_app_handoff_prompt(prompt_text)
    copied = copy_to_clipboard(prompt_text)
    launched = launch_codex()

    print("\n== Codex App Handoff ==")
    print(f"Prompt file: {CODEX_APP_HANDOFF_PROMPT.relative_to(ROOT)}")
    print(f"Run log: {CODEX_APP_LAST_LOG.relative_to(ROOT)}")
    if launched:
        print("Codex app has been asked to open this project.")
    else:
        print("Open Codex manually with this project if the app did not appear.")
    if copied:
        print("Prompt copied to clipboard. Paste it into the new Codex conversation and run it.")
    else:
        print("Clipboard copy was unavailable. Open the prompt file above and paste it into Codex.")
    print("After Codex finishes, run option 6 to import PDFs/rebuild the dashboard, then option 7 to create or refresh the wiki page.")


def launch_full_text_acquisition_prompt() -> None:
    rows = sync_doi_board()
    active = active_acquisition_rows(rows)
    if not active:
        print("\nNo DOI rows currently need full-text/PDF acquisition. Check raw/doi_dashboard.md.")
        return

    show_active_acquisition_rows(active)
    prompt_text = build_full_text_acquisition_prompt(active)
    return_code, failure_hint = run_codex_prompt_foreground(prompt_text, "DOI full-text acquisition", reasoning_effort="high")
    rows = sync_doi_board()
    messages, warnings = import_new_doi_pdfs(rows)
    extraction_messages, extraction_warnings = extract_staging_text_from_doi_pdfs(rows)
    write_dashboard_rows(rows)
    print_pdf_import_report(messages, warnings)
    print_pdf_extraction_report(extraction_messages, extraction_warnings)
    conversion_messages, conversion_warnings, rows_mutated = create_qced_full_text(rows)
    if rows_mutated:
        write_dashboard_rows(rows)
    print_full_text_conversion_report(conversion_messages, conversion_warnings)
    build_full_text_index_quiet()
    rows = sync_doi_board()
    print_acquisition_result(rows, {row["doi"] for row in active}, failure_hint if return_code else "")


def launch_wiki_ingest_prompt() -> None:
    rows = sync_doi_board()
    active = [
        row
        for row in rows
        if row.get("full_text")
        and full_text_is_qced(row.get("full_text", ""))
        and (
            row["status"] == "full_text_done"
            or row.get("next_action") == "ingest_full_text_to_wiki"
            or paper_page_needs_cleanup(row.get("wiki_page", ""))
        )
    ]
    if not active:
        print("\nNo DOI rows currently have QCed full_text waiting for wiki ingest or cleanup.")
        return

    doi_lines = "\n".join(
        f"- {row['doi']} (full_text: {row['full_text']}; pdf: {row.get('pdf') or 'missing'}; next_action: {row.get('next_action') or 'unknown'}; wiki_page: {row['wiki_page'] or 'missing'}; cleanup_needed: {paper_page_needs_cleanup(row.get('wiki_page', ''))})"
        for row in active
    )
    prompt_text = f"""You are working inside this Research Wiki project.

First read and follow the command-independent core contract:
- core/principles.md
- core/data_contract.md
- core/agent_contract.md
- core/skills/research-wiki-academic-writer/SKILL.md

Then use AGENTS.md, USER_GUIDE.md, and templates/paper.md for repository-specific implementation details. ResearchWiki.command is only a UI implementation of the core contract.

Target DOI rows ready for full-text QC and/or wiki ingest:
{doi_lines}

Goal:
Create, update, or clean wiki/literature paper pages from already QCed raw/full_text Markdown. Do not acquire new PDFs, new sources, or perform full_text reflow/QC in this task.

Rules:
0. Core contract is authoritative. If these command instructions conflict with core/*, follow core/* and report the mismatch.
1. Read raw/full_text_index.json and the Full Text paths listed above.
2. Verify the full_text DOI/title against the dashboard row and source PDF before writing. If the PDF and full_text disagree, stop for that DOI and record the blocker.
3. If any full_text frontmatter still says `machine_extracted_needs_codex_qc`, `needs_codex_qc`, `pending_codex_qc`, or `needs-human-review`, do not ingest it; update the dashboard with Next Action = codex_convert_to_full_text.
4. Use templates/paper.md. If an existing page contains old verbose sections, replace them with the concise structure.
5. Set paper-page `reading_status: full-read` only if the body text, methods, results, limitations, and conclusion/summary were actually read from QCed raw/full_text.
6. Keep full paper text out of wiki/literature. The wiki page should be a reading note, not a copy.
7. The generated wiki page should contain only this paper's content plus necessary source pointers. Do not copy template field guides, placeholder text, empty fields, long operational explanations, generic Zotero boilerplate, user-trigger boilerplate, or unnecessary synthesis sections.
8. Keep metadata concise: title, authors, venue/year, DOI, reading status, full_text path, and PDF path if available.
9. Preserve abstract-only warnings only if full text is still incomplete; otherwise replace them with full-read evidence notes.
10. Put cross-paper interpretation in wiki/synthesis only if explicitly necessary and evidence-labeled. For this command, prefer not to update synthesis.
11. Update raw/doi_dashboard.md:
    - if wiki page was created from QCed full_text: Status = wiki_done, Wiki Page = path, Next Action = review_or_ask_question.
    - if wiki ingest did not happen but QCed full_text remains usable: Status = full_text_done, Next Action = ingest_full_text_to_wiki.
    - if full_text is not actually QCed: Status = full_text_needed, Full Text empty, Next Action = codex_convert_to_full_text, Note = blocker.
12. Run python3 tools/build_full_text_index.py after changing paper pages.

Console output protocol:
- Emit concise progress lines only with these exact prefixes so ResearchWiki.command can show the important parts:
  - RW_STATUS|<doi>|<paper title>
  - RW_ATTEMPT|<doi>|full_text QC|<full_text_path>
  - RW_ATTEMPT|<doi>|wiki ingest from full_text|<full_text_path>
  - RW_RESULT|<doi>|success|<one_sentence_result>
  - RW_RESULT|<doi>|failed|<reason>
  - RW_WIKI_PAGE|<doi>|<wiki_page_path>
- Do not emit the example protocol lines themselves. Never emit angle-bracket placeholders such as `<doi>` or `<reason>` as real progress.
- Keep normal prose short; full details go to maintenance/codex_last_run.log.
"""
    return_code, failure_hint = run_codex_prompt_foreground(prompt_text, "wiki-page ingest", reasoning_effort="medium")
    subprocess.run(
        ["python3", "tools/build_full_text_index.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    rows = sync_doi_board()
    print_wiki_ingest_result(rows, {row["doi"] for row in active}, failure_hint if return_code else "")


def manage_topics() -> None:
    ensure_core_files()
    if not TOPICS.exists():
        print("Topic registry missing: wiki/literature/topic_registry.md")
        return
    action = prompt("Type a candidate subtopic to append, or press Enter to open registry")
    if not action:
        open_path(TOPICS)
        return
    topic = re.sub(r"[^a-z0-9_]+", "_", action.lower()).strip("_")
    if not topic:
        print("Topic was empty after normalization.")
        return
    text = TOPICS.read_text(encoding="utf-8")
    if f"`{topic}`" in text:
        print(f"`{topic}` already exists in the topic registry.")
        return
    marker = "| Candidate | Reason to Consider | Promote When |\n|---|---|---|"
    row = f"\n| `{topic}` | Added from ResearchWiki.command. | It becomes a durable research direction across multiple papers. |"
    if marker in text:
        text = text.replace(marker, marker + row, 1)
    else:
        text = text.rstrip() + "\n\n## Candidate Subtopics\n\n" + marker + row + "\n"
    TOPICS.write_text(text, encoding="utf-8")
    print(f"Added `{topic}` to Candidate Subtopics.")


def project_prompt() -> None:
    idea = prompt("Project / idea / research question")
    if not idea:
        idea = "Start by discussing with me to clarify the new research question."
    prompt_text = f"""You are working inside this Research Wiki project.

Project / idea:
{idea}

First read core/principles.md, core/data_contract.md, core/agent_contract.md, AGENTS.md, USER_GUIDE.md, wiki/index.md, and wiki/literature/topic_registry.md.

Start by discussing with me to clarify the research question. Do not ask me to choose a topic first.

After the conversation is clear enough, infer suitable topics, subtopics, and keywords. Check wiki/synthesis, wiki/literature, wiki/seminars, wiki/project_synthesis, raw/full_text_index.md, and raw/doi_dashboard.md for related material.

List DOI values or source pointers that should be added, and add ingest candidates to raw/paper_sources.md when appropriate. Do not create code or inbox pages. Use only the paper, synthesis, meeting, project_synthesis, seminar, paper source queue, DOI dashboard, and maintenance workflows.
"""
    start_codex_prompt(prompt_text, "a project conversation")


def prepare_support_issue() -> None:
    ensure_core_files()
    print("\nPreparing redacted support report and prefilled GitHub issue URL...")
    args = ["python3", "tools/support_report.py", "--issue-url"]
    if os.environ.get("RESEARCHWIKI_NO_OPEN") != "1":
        args.append("--open")
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = proc.stdout.strip()
    if output:
        print(output)
    if proc.returncode != 0:
        print("\nSupport issue preparation failed. You can still run:")
        print("python3 tools/support_report.py --issue-url")


def print_dashboard_summary(rows: list[dict[str, str]]) -> None:
    counts = {status: 0 for status in STATUSES}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("\n== DOI Dashboard ==")
    print(f"Rows refreshed: {len(rows)}")
    for status in ["new", "metadata_ok", "full_text_needed", "full_text_done", "wiki_done", "abstract_only", "blocked"]:
        print(f"- {status}: {counts.get(status, 0)}")
    print("\nLast Name_Year | Journal | DOI | Wiki Status | Access Legality | PDF | Full Text")
    for row in rows:
        pdf_status = row.get("pdf") or "no_pdf"
        full_text_status = row.get("full_text") or "no_full_text"
        print(
            f"- {row.get('paper') or 'unknown'} | {row.get('journal') or 'unknown'} | {row['doi']} | "
            f"{row['status']} | {row.get('access_legality') or 'unknown'} | "
            f"pdf: {pdf_status} | full_text: {full_text_status}"
        )
    print(f"Output: {DOI_DASHBOARD.relative_to(ROOT)}")


def open_authorized_source_pages() -> None:
    ensure_core_files()
    rows = sync_doi_board()
    missing = [row for row in rows if row.get("doi") and not row.get("pdf")]
    unresolved_sources = unresolved_source_lines()
    if not missing and not unresolved_sources:
        print("\nNo DOI rows are missing PDFs, and no unresolved source pointers are queued.")
        return

    print("\n== Authorized Source Pages ==")
    print("This helper opens DOI/article/source pages only. Use publisher, author, open-access, institutional, or user-provided full text/PDFs.")
    print("Unauthorized shadow-library downloads are not automated by this project.")
    print("")
    source_urls = [url for line in unresolved_sources for url in extract_urls(line)]
    for index, source in enumerate(unresolved_sources, start=1):
        print(f"Source {index}: {source}")
    if missing:
        print("")
        for index, row in enumerate(missing, start=1):
            expected = expected_pdf_path(row)
            print(f"DOI {index}: {row['doi']}")
            print(f"   Title: {row.get('title') or 'unknown'}")
            print(f"   Expected PDF: {repo_relative(expected) if expected else 'unknown'}")

    max_to_open_text = prompt("Max source/DOI pages to open now", "5")
    try:
        max_to_open = max(0, int(max_to_open_text))
    except ValueError:
        max_to_open = 5

    if os.environ.get("RESEARCHWIKI_NO_OPEN") == "1":
        print("\nOpen skipped because RESEARCHWIKI_NO_OPEN=1.")
        max_to_open = 0

    if max_to_open:
        opened = 0
        for url in source_urls[:max_to_open]:
            subprocess.run(["open", url], cwd=ROOT)
            opened += 1
        remaining = max_to_open - opened
        for row in missing[:remaining]:
            doi_url = f"https://doi.org/{quote(row['doi'], safe='/')}"
            subprocess.run(["open", doi_url], cwd=ROOT)
            opened += 1
        subprocess.run(["open", str(DOI_PDF_DIR)], cwd=ROOT)
        print(f"\nOpened {opened} source/DOI page(s) and raw/doi_pdf/.")

    print("\nAfter downloading authorized PDFs or confirming full text, place evidence in raw/doi_pdf/ or source notes, then run option 6.")


def rebuild_full_text_index() -> None:
    ensure_core_files()
    print("\nChecking raw/doi_pdf for newly added PDF files...")
    rows = sync_doi_board()
    messages, warnings = import_new_doi_pdfs(rows)
    extraction_messages, extraction_warnings = extract_staging_text_from_doi_pdfs(rows)
    write_dashboard_rows(rows)
    print_pdf_import_report(messages, warnings)
    print_pdf_extraction_report(extraction_messages, extraction_warnings)
    conversion_messages, conversion_warnings, rows_mutated = create_qced_full_text(rows)
    if rows_mutated:
        write_dashboard_rows(rows)
    print_full_text_conversion_report(conversion_messages, conversion_warnings)

    print("\nRebuilding local full_text index...")
    proc = subprocess.run(
        ["python3", "tools/build_full_text_index.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        print("\nIndex rebuild failed.")
        if proc.stdout.strip():
            print(proc.stdout.strip())
        return
    rows = sync_doi_board()
    print_dashboard_summary(rows)
    print("\n== full_text Index ==")
    if proc.stdout.strip():
        print(proc.stdout.strip())
    else:
        print("No full_text index output.")
    print("Outputs: raw/full_text_index.md, raw/full_text_index.json")


def run_health_check() -> None:
    ensure_core_files()
    proc = subprocess.run(
        ["python3", "tools/wiki_doctor.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(proc.stdout.strip())
    if ".DS_Store present" in proc.stdout:
        print("")
        print("Cleanup note: .DS_Store warnings are release hygiene only.")
        print("Remove exact files one at a time after human review; do not use recursive or wildcard cleanup.")


def generate_repair_plan() -> None:
    ensure_core_files()
    proc = subprocess.run(
        ["python3", "tools/generate_repair_plan.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(proc.stdout.strip())
    print("Repair plans are advisory and never delete files.")


def open_graph_guide() -> None:
    ensure_core_files()
    if not OBSIDIAN_GRAPH_GUIDE.exists():
        print("Missing maintenance/obsidian_graph_guide.md")
        return
    open_path(OBSIDIAN_GRAPH_GUIDE)


def menu() -> None:
    actions = {
        "1": ("Add/open paper sources", add_or_open_paper_sources),
        "2": ("Open/manage DOI dashboard", lambda: open_path(DOI_DASHBOARD)),
        "3": ("Codex-assisted source/full-text finding", launch_full_text_acquisition_prompt),
        "4": ("Prepare Codex app source/full-text finding prompt", prepare_codex_app_acquisition_prompt),
        "5": ("Open authorized source pages", open_authorized_source_pages),
        "6": ("Import evidence + create QCed full_text", rebuild_full_text_index),
        "7": ("Ingest QCed full_text to wiki", launch_wiki_ingest_prompt),
        "8": ("Launch Codex project conversation", project_prompt),
        "9": ("Manage topic/subtopic registry", manage_topics),
        "10": ("Open Obsidian graph guide", open_graph_guide),
        "11": ("Run database health check (diagnose only)", run_health_check),
        "12": ("Generate repair plan (no deletes)", generate_repair_plan),
        "13": ("Prepare GitHub support issue (redacted)", prepare_support_issue),
        "0": ("Exit", None),
    }
    while True:
        print_header()
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        choice = prompt("Choose", "0" if not sys.stdin.isatty() else "")
        if choice == "0":
            print("Bye.")
            return
        action = actions.get(choice)
        if not action:
            print("Unknown choice.")
            pause()
            continue
        try:
            action[1]()
        except KeyboardInterrupt:
            print("\nCancelled.")
        except Exception as exc:
            print(f"\nError: {exc}")
        if choice in {"3", "7"}:
            continue
        pause()


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(130)
