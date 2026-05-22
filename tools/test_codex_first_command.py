#!/usr/bin/env python3
"""Smoke tests for the canonical Codex-first command.

The tests copy the repository to a temporary directory and mutate only that
copy. They do not reset or edit the user's live raw/ files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def copy_repo_to_temp() -> Path:
    parent = Path(tempfile.mkdtemp(prefix="research_wiki_codex_first_"))
    work = parent / "repo"
    ignore = shutil.ignore_patterns(".git", "tmp", "__pycache__", "*.pyc")
    shutil.copytree(ROOT, work, ignore=ignore)
    return work


def run(
    work: Path,
    args: list[str],
    *,
    input_text: str = "",
    extra_env: dict[str, str] | None = None,
    timeout: int = 240,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["RESEARCHWIKI_NO_OPEN"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        args,
        cwd=work,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def reset_database(work: Path) -> None:
    proc = run(work, [sys.executable, "tools/init_research_wiki.py"], input_text="INIT TEST DATABASE\nn\nn\n")
    if proc.returncode != 0:
        raise AssertionError(f"initializer failed:\n{proc.stdout}")


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_text_pdf(path: Path, lines: list[str]) -> None:
    content_lines = ["BT", "/F1 10 Tf", "72 760 Td", "12 TL"]
    for line in lines:
        content_lines.append(f"({pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{index} 0 obj\n".encode("ascii"))
        data.extend(obj)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(bytes(data))


def add_fixture_pdf(work: Path, name: str = "downloaded_article.pdf") -> None:
    doi = "10.5194/acp-8-15-2008"
    lines = [
        "Atmos. Chem. Phys., 8, 15-24, 2008",
        f"https://doi.org/{doi}",
        "Aerosols' influence on the interplay between condensation, evaporation and rain in warm cumulus cloud",
        "O. Altaratz, I. Koren, T. Reisin, A. Kostinski, G. Feingold, Z. Levin, and Y. Yin",
        "Abstract. This synthetic test article is generated for Research Wiki workflow tests.",
        "1 Introduction",
        "The article discusses aerosol particles, cloud condensation nuclei, cloud microphysics, and command testing.",
        "2 Methods",
        "The methods section exists so direct full text quality-control tests have enough body text.",
        "3 Results",
        "The results section repeats controlled scientific vocabulary while avoiding publisher text.",
        "4 Conclusions",
        "The conclusion states that this is a synthetic fixture and not a real article.",
        "References",
        "Synthetic Reference 2026. Research Wiki fixture validation.",
    ]
    path = work / "raw" / "doi_pdf" / name
    write_text_pdf(path, lines * 8)


def add_copernicus_duplicate_pdf_fixtures(work: Path) -> None:
    doi = "10.5194/acp-8-15-2008"
    lines = [
        "Atmos. Chem. Phys., 8, 15-24, 2008",
        f"https://doi.org/{doi}",
        "Synthetic duplicate PDF fixture",
        "O. Altaratz, I. Koren, T. Reisin, A. Kostinski, G. Feingold, Z. Levin, and Y. Yin",
        "Abstract. This file checks duplicate publisher filenames.",
    ]
    for name in ["acp-8-15-2008.pdf", "acp-8-15-2008-3.pdf"]:
        write_text_pdf(work / "raw" / "doi_pdf" / name, lines * 8)


def add_duplicate_cleanup_fixtures(work: Path) -> None:
    doi = "10.5194/acp-8-15-2008"
    lines = [
        "Atmos. Chem. Phys., 8, 15-24, 2008",
        f"https://doi.org/{doi}",
        "Synthetic duplicate cleanup PDF fixture",
        "O. Altaratz, I. Koren, T. Reisin, A. Kostinski, G. Feingold, Z. Levin, and Y. Yin",
        "Abstract. This file checks manual duplicate cleanup.",
    ]
    for name in ["altaratz_2008_acp.pdf", "acp-8-15-2008.pdf", "acp-8-15-2008-3.pdf"]:
        write_text_pdf(work / "raw" / "doi_pdf" / name, lines * 8)


def add_source_doi(work: Path, doi: str) -> None:
    source_file = work / "raw" / "paper_sources.md"
    text = read(source_file)
    text = text.replace("```text\n```", f"```text\n{doi}\n```")
    text = text.replace("```text\n\n```", f"```text\n{doi}\n```")
    source_file.write_text(text, encoding="utf-8")


def run_command(work: Path, input_text: str, *, extra_env: dict[str, str] | None = None) -> str:
    proc = run(work, [sys.executable, "tools/research_wiki_codex_shortcut.py"], input_text=input_text, extra_env=extra_env)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout)
    return proc.stdout


def assert_contains(text: str, value: str) -> None:
    if value not in text:
        raise AssertionError(f"missing expected text: {value}\n{text[-4000:]}")


def assert_file(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"missing expected file: {path}")


def assert_no_generated_files(path: Path) -> None:
    generated = [item for item in path.iterdir() if item.name != ".gitkeep"]
    if generated:
        raise AssertionError(f"unexpected generated files in {path}: {[item.name for item in generated]}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def scenario_smoke_menu_exit(work: Path) -> None:
    out = run_command(work, "0\n")
    assert_contains(out, "ResearchWiki Codex-first")
    assert_contains(out, "Open/add paper sources")


def scenario_no_deleted_command_reference(work: Path) -> None:
    deleted_command = "ResearchWiki" + ".command"
    bad_references = [
        f"`{deleted_command}`",
        f"./{deleted_command}",
        f" {deleted_command}",
        f"{deleted_command} ",
    ]
    if (work / deleted_command).exists():
        raise AssertionError(f"{deleted_command} should not exist in the canonical Codex-first release")
    checked = [
        "README.md",
        "README.zh-TW.md",
        "USER_GUIDE.md",
        "USER_GUIDE.zh-TW.md",
        "SUPPORT.md",
        "SUPPORT.zh-TW.md",
        "INSTALL.md",
        "INSTALL.zh-TW.md",
        "AGENTS.md",
        "core/README.md",
        "core/test_contract.md",
        "tools/check_install.py",
    ]
    for rel in checked:
        text = read(work / rel)
        if any(pattern in text for pattern in bad_references):
            raise AssertionError(f"{rel} still references deleted {deleted_command}")


def scenario_windows_launchers_are_repo_relative(work: Path) -> None:
    codex_cmd = read(work / "ResearchWikiCodex.cmd")
    init_cmd = read(work / "InitializeResearchWiki.cmd")
    for text in [codex_cmd, init_cmd]:
        assert_contains(text, 'cd /d "%~dp0"')
        if "/" + "Users/" in text or "Desktop/wiki_research" in text:
            raise AssertionError(text)
    assert_contains(codex_cmd, "tools\\research_wiki_codex_shortcut.py")
    assert_contains(init_cmd, "tools\\init_research_wiki.py")


def scenario_topic_setup_blank_and_custom(work: Path) -> None:
    proc = run(work, [sys.executable, "tools/init_research_wiki.py"], input_text="1\n\n\n")
    if proc.returncode != 0:
        raise AssertionError(proc.stdout)
    registry = read(work / "wiki" / "literature" / "topic_registry.md")
    assert_contains(registry, "## Active Topics")
    if "aerosol" in registry or "wildfire" in registry:
        raise AssertionError(registry)

    proc = run(work, [sys.executable, "tools/init_research_wiki.py"], input_text="1\ncloud physics, wildfire smoke\nmicrophysics\n")
    if proc.returncode != 0:
        raise AssertionError(proc.stdout)
    registry = read(work / "wiki" / "literature" / "topic_registry.md")
    assert_contains(registry, "`cloud_physics`")
    assert_contains(registry, "`wildfire_smoke`")
    assert_contains(registry, "`microphysics`")


def scenario_option2_pdf_scan_no_staging(work: Path) -> None:
    reset_database(work)
    add_fixture_pdf(work)
    out = run_command(work, "2\n\n0\n")
    assert_contains(out, "No persistent staging full text was created")
    assert_contains(out, "Open skipped because RESEARCHWIKI_NO_OPEN=1")
    assert_contains(read(work / "raw" / "doi_dashboard.md"), "10.5194/acp-8-15-2008")
    assert_contains(read(work / "raw" / "doi_dashboard.md"), "| Last Name_Year | Journal | DOI | Wiki Status | PDF | Full Text |")
    assert_file(work / "raw" / "doi_pdf" / "altaratz_2008_acp.pdf")
    assert_no_generated_files(work / "raw" / "staging" / "extracted_text")
    assert_no_generated_files(work / "raw" / "full_text")


def scenario_option3_stub_success_no_staging(work: Path) -> None:
    reset_database(work)
    add_fixture_pdf(work)
    out = run_command(work, "3\n\n0\n", extra_env={"RESEARCHWIKI_TEST_CODEX_FIRST_QC_STUB": "1"})
    assert_contains(out, "Created QCed full_text")
    assert_file(work / "raw" / "full_text" / "altaratz_2008_acp.md")
    assert_contains(read(work / "raw" / "doi_dashboard.md"), "full_text_done")
    assert_no_generated_files(work / "raw" / "staging" / "extracted_text")


def scenario_option3_stub_failure_no_artifacts(work: Path) -> None:
    reset_database(work)
    add_fixture_pdf(work)
    out = run_command(work, "3\n\n0\n", extra_env={"RESEARCHWIKI_TEST_CODEX_FIRST_QC_FAIL": "1"})
    assert_contains(out, "Test-mode QC failure")
    assert_no_generated_files(work / "raw" / "staging" / "extracted_text")
    assert_no_generated_files(work / "raw" / "full_text")
    assert_contains(read(work / "raw" / "doi_dashboard.md"), "codex_first_qc_needs_authorized_source")


def scenario_option3_missing_pdf_opens_download_pages(work: Path) -> None:
    reset_database(work)
    add_source_doi(work, "10.5194/acp-8-15-2008")
    out = run_command(
        work,
        "3\n1\n\n\n0\n",
        extra_env={"RESEARCHWIKI_TEST_CODEX_FIRST_QC_FAIL": "1"},
    )
    assert_contains(out, "Download / Full-Text Pages")
    assert_contains(out, "Open skipped because RESEARCHWIKI_NO_OPEN=1")
    assert_contains(out, "No local PDF was found after the download check")
    assert_no_generated_files(work / "raw" / "staging" / "extracted_text")
    assert_no_generated_files(work / "raw" / "full_text")


def scenario_option2_duplicate_pdf_suffix_no_fake_doi(work: Path) -> None:
    reset_database(work)
    add_source_doi(work, "10.5194/acp-8-15-2008")
    add_copernicus_duplicate_pdf_fixtures(work)
    out = run_command(work, "2\n\n0\n\n0\n", extra_env={"RESEARCHWIKI_DISABLE_PDF_TEXT": "1"})
    assert_contains(out, "duplicate-looking PDF")
    dashboard = read(work / "raw" / "doi_dashboard.md")
    if "10.5194/acp-8-15-2008-3" in dashboard:
        raise AssertionError(dashboard)
    assert_contains(dashboard, "10.5194/acp-8-15-2008")
    assert_no_generated_files(work / "raw" / "staging" / "extracted_text")
    assert_no_generated_files(work / "raw" / "full_text")


def scenario_table_checker_reports_fragmented_table(work: Path) -> None:
    reset_database(work)
    target = work / "raw" / "full_text" / "table_fragment_fixture.md"
    target.write_text(
        """---
doi: 10.1234/example.table
title: "Synthetic table fixture"
extraction_status: codex_qc_done
readability_status: readable-with-warnings
qc_status: codex_qc_done
equation_quality: not_applicable
---

# Synthetic table fixture

```text
Table
1.
Species
Savanna
forest
Boreal
forest
CO2
1600
1500
CO
80
100
CH4
4
6
Continued
Species
Temperate
forest
CO2
1550
```
""",
        encoding="utf-8",
    )
    proc = run(work, [sys.executable, "tools/check_full_text_tables.py", "raw/full_text/table_fragment_fixture.md"])
    if proc.returncode != 0:
        raise AssertionError(proc.stdout)
    assert_contains(proc.stdout, "fragmented table block")
    assert_contains(proc.stdout, "table_quality")


def scenario_option2_bulk_delete_duplicate_pdfs(work: Path) -> None:
    reset_database(work)
    add_duplicate_cleanup_fixtures(work)
    out = run_command(work, "2\nDELETE ALL DUPLICATE PDFS\n\n0\n")
    assert_contains(out, "Duplicate PDF Review")
    assert_contains(out, "Deleted raw/doi_pdf/acp-8-15-2008.pdf")
    assert_contains(out, "Deleted raw/doi_pdf/acp-8-15-2008-3.pdf")
    assert_contains(out, "Deleted files: 2")
    assert_file(work / "raw" / "doi_pdf" / "altaratz_2008_acp.pdf")
    if (work / "raw" / "doi_pdf" / "acp-8-15-2008.pdf").exists():
        raise AssertionError("duplicate PDF was not deleted")
    if (work / "raw" / "doi_pdf" / "acp-8-15-2008-3.pdf").exists():
        raise AssertionError("duplicate PDF was not deleted")


def scenario_option5_creates_synthesis_prompt(work: Path) -> None:
    reset_database(work)
    out = run_command(work, "5\nSmoke microphysics question\n\n0\n")
    assert_contains(out, "Synthesis Conversation Handoff")
    assert_file(work / "wiki" / "synthesis" / "smoke_microphysics_question.md")
    prompt = read(work / "maintenance" / "codex_first_synthesis_prompt.md")
    assert_contains(prompt, "Draft synthesis page:")
    assert_contains(prompt, "Ask me questions first")


def scenario_option6_feedback_prompt(work: Path) -> None:
    reset_database(work)
    out = run_command(work, "6\n[feedback] dry run\n\n0\n")
    assert_contains(out, "Feedback Issue Handoff")
    prompt = read(work / "maintenance" / "codex_first_feedback_issue_prompt.md")
    assert_contains(prompt, "I will provide the full description before sending")
    assert_contains(prompt, "Do not submit the issue until I explicitly confirm")


def scenario_option7_external_sandbox_prompt(work: Path) -> None:
    reset_database(work)
    out = run_command(work, "7\nSmoke coupling across models\nsynthesis\n\n0\n")
    assert_contains(out, "External Sandbox Handoff")
    assert_file(work / "wiki" / "synthesis" / "smoke_coupling_across_models.md")
    prompt = read(work / "maintenance" / "external_sandbox_sync_prompt.md")
    assert_contains(prompt, "same computer")
    assert_contains(prompt, "Use the exact path above as the working directory")
    assert_contains(prompt, "Do not create a separate clone or branch")
    assert_contains(prompt, "Make edits directly in the exact database path")
    assert_contains(prompt, "I may paste current results")


def main() -> int:
    work = copy_repo_to_temp()
    scenarios = [
        scenario_smoke_menu_exit,
        scenario_no_deleted_command_reference,
        scenario_windows_launchers_are_repo_relative,
        scenario_topic_setup_blank_and_custom,
        scenario_option2_pdf_scan_no_staging,
        scenario_option3_stub_success_no_staging,
        scenario_option3_stub_failure_no_artifacts,
        scenario_option3_missing_pdf_opens_download_pages,
        scenario_option2_duplicate_pdf_suffix_no_fake_doi,
        scenario_table_checker_reports_fragmented_table,
        scenario_option2_bulk_delete_duplicate_pdfs,
        scenario_option5_creates_synthesis_prompt,
        scenario_option6_feedback_prompt,
        scenario_option7_external_sandbox_prompt,
    ]
    for scenario in scenarios:
        scenario(work)
        print(f"PASS {scenario.__name__}")
    print(f"Temp test repo left at: {work}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
