#!/usr/bin/env python3
"""Reset-first intake-matrix tests for ResearchWiki.command.

Each scenario resets the local test database, lays down one intake entry
condition, runs the relevant command branch, and records what happened. The
matrix is designed to debug source/DOI/PDF intake before exercising the full
workflow.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(tempfile.gettempdir()) / "research_wiki_test_fixtures" / "doi_pdf"
REPORT = ROOT / "maintenance" / f"workflow_test_report_{datetime.now().date().isoformat()}.md"


def run(
    args: list[str],
    *,
    input_text: str = "",
    timeout: int = 180,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["RESEARCHWIKI_NO_OPEN"] = "1"
    env["RESEARCHWIKI_TEST_QC_STUB"] = "1"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def sanitize_report_text(text: str) -> str:
    return text.replace(str(ROOT), "<repo>")


def compact_report_text(text: str, *, head: int = 1400, tail: int = 3000) -> str:
    clean = sanitize_report_text(text)
    if len(clean) <= head + tail + 80:
        return clean
    return clean[:head].rstrip() + "\n\n... [output truncated] ...\n\n" + clean[-tail:].lstrip()


def reset_database() -> str:
    proc = run(["python3", "tools/init_research_wiki.py"], input_text="INIT TEST DATABASE\nn\n")
    if proc.returncode != 0:
        raise AssertionError(f"initializer failed:\n{proc.stdout}")
    return proc.stdout


def run_post_scenario_checks() -> str:
    checks = [
        ["python3", "tools/wiki_lint.py"],
        ["python3", "tools/wiki_doctor.py"],
        ["python3", "tools/check_install.py", "--strict"],
    ]
    outputs: list[str] = []
    for command in checks:
        proc = run(command, timeout=180)
        label = " ".join(command)
        outputs.append(f"$ {label}\n{proc.stdout.strip()}")
        if proc.returncode != 0:
            raise AssertionError(f"{label} failed:\n{proc.stdout}")
    index = read_index()
    if "summary" not in index or "entries" not in index:
        raise AssertionError("raw/full_text_index.json is missing summary or entries")
    outputs.append(
        "$ inspect raw/full_text_index.*\n"
        f"primary_entries={index['summary'].get('primary_entries')}; "
        f"wiki_ingest_needed={index['summary'].get('wiki_ingest_needed')}; "
        f"fulltext_qc_needed={index['summary'].get('fulltext_qc_needed')}"
    )
    rows = main_board_rows()
    outputs.append("$ inspect raw/doi_dashboard.md\n" + "\n".join(rows or ["<no DOI rows>"]))
    return "\n\n".join(outputs)


def run_command(input_text: str, *, extra_env: dict[str, str] | None = None, timeout: int = 240) -> str:
    proc = run(["python3", "tools/research_wiki_shortcut.py"], input_text=input_text, extra_env=extra_env, timeout=timeout)
    if proc.returncode != 0:
        raise AssertionError(f"ResearchWiki.command failed:\n{proc.stdout}")
    return proc.stdout


def paper_intake_add_source(value: str) -> str:
    return run_command(f"1\n1\n{value}\n\n0\n\n0\n")


def paper_intake_open_sources() -> str:
    return run_command("1\n2\n\n\n0\n\n0\n")


def paper_intake_local_import(*, extra_env: dict[str, str] | None = None) -> str:
    return run_command("1\n3\n\n0\n\n0\n", extra_env=extra_env)


def paper_intake_codex_qc(*, extra_env: dict[str, str] | None = None) -> str:
    return run_command("1\n4\n\n0\n\n0\n", extra_env=extra_env)


def paper_intake_source_fallback() -> str:
    return run_command("1\n5\n\n0\n\n0\n")


def option7_dry_run() -> str:
    proc = run(["python3", "tools/research_wiki_shortcut.py"], input_text="2\n0\n", timeout=240)
    if proc.returncode != 0:
        raise AssertionError(f"wiki ingest dry run failed:\n{proc.stdout[:4000]}")
    return proc.stdout


def read_index() -> dict:
    return json.loads((ROOT / "raw" / "full_text_index.json").read_text(encoding="utf-8"))


def read_dashboard() -> str:
    return (ROOT / "raw" / "doi_dashboard.md").read_text(encoding="utf-8")


def read_paper_sources() -> str:
    return (ROOT / "raw" / "paper_sources.md").read_text(encoding="utf-8")


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_text_pdf(path: Path, lines: list[str]) -> None:
    """Write a tiny one-page text PDF that pdftotext can read."""
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


def fixture_lines(doi: str, journal_line: str, title: str, authors: str) -> list[str]:
    body = [
        journal_line,
        f"https://doi.org/{doi}",
        title,
        authors,
        "Abstract. This synthetic test article is generated for Research Wiki workflow tests.",
        "It contains enough text for local extraction, DOI matching, title detection, and author key inference.",
        "1 Introduction",
        "The article discusses wildfire smoke, aerosol particles, cloud condensation nuclei, cloud microphysics, and research database testing.",
        "2 Methods",
        "The methods section exists so the machine extraction has a realistic body section for downstream quality-control prompts.",
        "3 Results",
        "The results section repeats controlled scientific vocabulary while avoiding real publisher text or copyrighted article content.",
        "4 Conclusions",
        "The conclusion states that this is a synthetic fixture and not a real article.",
        "References",
        "Synthetic Reference 2026. Research Wiki fixture validation.",
    ]
    return body + body + body


def ensure_fixtures() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "acp-8-15-2008.pdf": fixture_lines(
            "10.5194/acp-8-15-2008",
            "Atmos. Chem. Phys., 8, 15-24, 2008",
            "Aerosols' influence on the interplay between condensation, evaporation and rain in warm cumulus cloud",
            "O. Altaratz, I. Koren, T. Reisin, A. Kostinski, G. Feingold, Z. Levin, and Y. Yin",
        ),
        "acp-12-7285-2012.pdf": fixture_lines(
            "10.5194/acp-12-7285-2012",
            "Atmos. Chem. Phys., 12, 7285-7293, 2012",
            "Cloud condensation nuclei activity of fresh primary and aged biomass burning aerosol",
            "G. J. Engelhart, C. J. Hennigan, M. A. Miracolo, A. L. Robinson, and S. N. Pandis",
        ),
        "acp-21-9779-2021.pdf": fixture_lines(
            "10.5194/acp-21-9779-2021",
            "Atmos. Chem. Phys., 21, 9779-9807, 2021",
            "Tropospheric and stratospheric wildfire smoke profiling with lidar: mass, surface area, CCN, and INP retrieval",
            "Albert Ansmann, Kevin Ohneiser, Rodanthi-Elisavet Mamouri, Daniel A. Knopf, and Boris Barja",
        ),
        "conrick_2021_waf.pdf": fixture_lines(
            "10.1175/WAF-D-21-0044.1",
            "Weather and Forecasting, 36, 1519-1536, 2021",
            "The Influence of Wildfire Smoke on Cloud Microphysics during the September 2020 Pacific Northwest Wildfires",
            "ROBERT CONRICK, CLIFFORD F. MASS, JOSEPH P. BOOMGARD-ZAGRODNIK, AND DAVID OVENS",
        ),
    }
    for name, lines in fixtures.items():
        write_text_pdf(FIXTURES / name, lines)


def copy_fixture(name: str, target_name: str | None = None) -> None:
    ensure_fixtures()
    src = FIXTURES / name
    if not src.exists():
        raise AssertionError(f"missing fixture: {src}")
    target = ROOT / "raw" / "doi_pdf" / (target_name or name)
    shutil.copy2(src, target)


def add_dois(*dois: str) -> None:
    source_file = ROOT / "raw" / "paper_sources.md"
    text = source_file.read_text(encoding="utf-8")
    block = "\n".join(dois)
    text = re.sub(r"```text\n.*?\n```", f"```text\n{block}\n```", text, flags=re.DOTALL)
    source_file.write_text(text, encoding="utf-8")


def add_to_legacy_doi_list(*dois: str) -> None:
    doi_list = ROOT / "raw" / "doi_list.md"
    text = doi_list.read_text(encoding="utf-8")
    block = "\n".join(dois)
    text = re.sub(r"```text\n.*?\n```", f"```text\n{block}\n```", text, flags=re.DOTALL)
    doi_list.write_text(text, encoding="utf-8")


def write_qced_full_text(path: str, doi: str, title: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"""---
title: "{title}"
doi: {doi}
language: en
source_pdf: ""
extraction_status: codex_qc_done
readability_status: readable
qc_status: codex_qc_done
---

# {title}

This synthetic QCed full text represents a readable Markdown article that is
already suitable for wiki ingest. It contains methods, results, discussion, and
limitations in compact fixture prose without using real publisher text.
""",
        encoding="utf-8",
    )


def assert_contains(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing expected text: {needle}")


def assert_not_contains(text: str, needle: str) -> None:
    if needle in text:
        raise AssertionError(f"unexpected text present: {needle}")


def assert_file(path: str) -> None:
    if not (ROOT / path).exists():
        raise AssertionError(f"missing expected file: {path}")


def assert_no_file(path: str) -> None:
    if (ROOT / path).exists():
        raise AssertionError(f"unexpected file exists: {path}")


def assert_no_generated_files(directory: str) -> None:
    root = ROOT / directory
    generated = [path for path in root.iterdir() if path.name != ".gitkeep"]
    if generated:
        raise AssertionError(f"unexpected generated files in {directory}: {[path.name for path in generated]}")


def main_board_rows() -> list[str]:
    dashboard = read_dashboard()
    match = re.search(r"## DOI Status Board\n\n(.*?)\n\n## DOI Notes", dashboard, flags=re.DOTALL)
    if not match:
        return []
    return [
        line
        for line in match.group(1).splitlines()
        if line.startswith("| ") and "|---" not in line and "Last Name_Year" not in line
    ]


def assert_one_dashboard_row_for(doi: str) -> None:
    rows = [line for line in main_board_rows() if doi.lower() in line.lower()]
    if len(rows) != 1:
        raise AssertionError(f"expected exactly one main dashboard row for {doi}, found {len(rows)}: {rows}")


def assert_no_codex_launch(output: str) -> None:
    assert_not_contains(output, "Codex launch skipped")
    assert_not_contains(output, "Starting Codex")
    assert_not_contains(output, "Prompt that would be sent to Codex")


def make_no_doi_pdf() -> None:
    target = ROOT / "raw" / "doi_pdf" / "manual_upload_no_doi.pdf"
    write_text_pdf(
        target,
        [
            "Local meeting handout with no DOI metadata.",
            "This synthetic file should not be silently ingested as DOI evidence.",
            "It has enough text to be a valid PDF but no DOI-like string.",
        ],
    )


def scenario_only_doi_in_legacy_list_creates_row_only() -> tuple[str, str]:
    reset_database()
    add_to_legacy_doi_list("10.5194/acp-8-15-2008")
    out = paper_intake_local_import()
    dash = read_dashboard()
    idx = read_index()
    assert_contains(dash, "10.5194/acp-8-15-2008")
    assert_contains(dash, "authorized_source_or_pdf_needed")
    assert_one_dashboard_row_for("10.5194/acp-8-15-2008")
    assert idx["summary"]["primary_entries"] == 0
    assert_no_file("raw/doi_pdf/altaratz_2008_acp.pdf")
    assert_no_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert_no_file("raw/full_text/altaratz_2008_acp.md")
    assert_no_codex_launch(out)
    return "only DOI in legacy list creates dashboard row and no evidence artifacts", out


def scenario_command_add_source_doi_then_local_import() -> tuple[str, str]:
    reset_database()
    add_out = paper_intake_add_source("10.1002/2013jd019860")
    assert_contains(add_out, "Added 1 source pointer")
    assert_contains(read_paper_sources(), "10.1002/2013jd019860")
    assert_no_codex_launch(add_out)

    import_out = paper_intake_local_import()
    dash = read_dashboard()
    assert_contains(dash, "10.1002/2013jd019860")
    assert_contains(dash, "authorized_source_or_pdf_needed")
    assert_one_dashboard_row_for("10.1002/2013jd019860")
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_generated_files("raw/doi_pdf")
    assert_no_generated_files("raw/staging/extracted_text")
    assert_no_generated_files("raw/full_text")
    assert_no_codex_launch(import_out)
    return "command Add/open paper sources accepts DOI and local import creates row only", add_out + "\n\n--- local import ---\n\n" + import_out


def scenario_doi_and_url_sources_dedupe_without_codex() -> tuple[str, str]:
    reset_database()
    article_url = "https://acp.copernicus.org/articles/21/9779/2021/"
    pdf_url = "https://acp.copernicus.org/articles/21/9779/2021/acp-21-9779-2021.pdf"
    add_dois(
        "10.5194/acp-21-9779-2021",
        "https://doi.org/10.5194/acp-21-9779-2021",
        article_url,
        pdf_url,
    )
    out = paper_intake_local_import()
    dash = read_dashboard()
    assert_contains(dash, "10.5194/acp-21-9779-2021")
    assert_one_dashboard_row_for("10.5194/acp-21-9779-2021")
    assert_contains(read_paper_sources(), article_url)
    assert_contains(read_paper_sources(), pdf_url)
    assert "https://doi.org/10.5194/acp-21-9779-2021" not in read_paper_sources()
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_codex_launch(out)
    return "DOI plus DOI URL/article URL/PDF URL dedupe without Codex", out


def scenario_duplicate_doi_across_queues_creates_one_row() -> tuple[str, str]:
    reset_database()
    doi = "10.5194/acp-21-9779-2021"
    add_to_legacy_doi_list(doi)
    add_dois(doi, f"https://doi.org/{doi}")
    out = paper_intake_local_import()
    dash = read_dashboard()
    assert_contains(dash, doi)
    assert_one_dashboard_row_for(doi)
    assert_contains(dash, "authorized_source_or_pdf_needed")
    assert "https://doi.org/10.5194/acp-21-9779-2021" not in read_paper_sources()
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_generated_files("raw/doi_pdf")
    assert_no_generated_files("raw/staging/extracted_text")
    assert_no_generated_files("raw/full_text")
    assert_no_codex_launch(out)
    return "duplicate DOI across legacy list and source queue creates one dashboard row", out


def scenario_open_authorized_sources_is_local_no_token() -> tuple[str, str]:
    reset_database()
    add_dois(
        "10.5194/acp-21-9779-2021",
        "https://acp.copernicus.org/articles/21/9779/2021/",
    )
    out = paper_intake_open_sources()
    dash = read_dashboard()
    assert_contains(out, "Authorized Source Pages")
    assert_contains(out, "Open skipped because RESEARCHWIKI_NO_OPEN=1.")
    assert_contains(dash, "10.5194/acp-21-9779-2021")
    assert_contains(dash, "authorized_source_or_pdf_needed")
    assert_no_generated_files("raw/doi_pdf")
    assert_no_generated_files("raw/staging/extracted_text")
    assert_no_generated_files("raw/full_text")
    assert_no_codex_launch(out)
    return "open authorized source pages is local/no-token and never falls through to Codex", out


def scenario_pdf_only_imports_to_staging_not_full_text() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf", "downloaded_article.pdf")
    out = paper_intake_local_import()
    dash = read_dashboard()
    idx = read_index()
    assert_contains(dash, "10.5194/acp-8-15-2008")
    assert_contains(dash, "full_text_needed")
    assert_contains(dash, "codex_convert_to_full_text")
    assert_file("raw/doi_pdf/altaratz_2008_acp.pdf")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert_no_file("raw/full_text/altaratz_2008_acp.md")
    assert idx["summary"]["primary_entries"] == 0
    assert_no_codex_launch(out)
    return "orphan PDF creates DOI row, canonical PDF, and staging only", out


def scenario_uppercase_pdf_extension_imports_to_canonical_lowercase() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf", "Downloaded_Article.PDF")
    out = paper_intake_local_import()
    dash = read_dashboard()
    assert_contains(dash, "10.5194/acp-8-15-2008")
    assert_contains(dash, "codex_convert_to_full_text")
    assert_file("raw/doi_pdf/altaratz_2008_acp.pdf")
    assert_no_file("raw/doi_pdf/Downloaded_Article.PDF")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert_no_file("raw/full_text/altaratz_2008_acp.md")
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_codex_launch(out)
    return "uppercase .PDF upload imports and renames to canonical lowercase .pdf", out


def scenario_pdf_import_without_text_extractor_keeps_pdf_only() -> tuple[str, str]:
    reset_database()
    add_dois("10.5194/acp-21-9779-2021")
    copy_fixture("acp-21-9779-2021.pdf", "acp-21-9779-2021.pdf")
    out = paper_intake_local_import(extra_env={"RESEARCHWIKI_DISABLE_PDF_TEXT": "1"})
    dash = read_dashboard()
    assert_contains(out, "Could not extract text")
    assert_contains(dash, "10.5194/acp-21-9779-2021")
    assert_contains(dash, "full_text_needed")
    assert_contains(dash, "codex_convert_to_full_text")
    assert_file("raw/doi_pdf/acp_21_9779_2021.pdf")
    assert_no_generated_files("raw/staging/extracted_text")
    assert_no_generated_files("raw/full_text")
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_codex_launch(out)
    return "PDF import without a local text extractor keeps PDF evidence only and does not create staging", out


def scenario_doi_list_plus_pdf_pairs_then_qc_stub() -> tuple[str, str]:
    reset_database()
    add_dois("10.5194/acp-21-9779-2021")
    copy_fixture("acp-21-9779-2021.pdf", "manual-download.pdf")
    local_out = paper_intake_local_import()
    dash = read_dashboard()
    assert_contains(dash, "codex_convert_to_full_text")
    assert_file("raw/doi_pdf/ansmann_2021_acp.pdf")
    assert_file("raw/staging/extracted_text/ansmann_2021_acp.md")
    assert_no_file("raw/full_text/ansmann_2021_acp.md")
    assert_no_codex_launch(local_out)

    qc_out = paper_intake_codex_qc()
    dash = read_dashboard()
    idx = read_index()
    assert_contains(dash, "full_text_done")
    assert_contains(dash, "ingest_full_text_to_wiki")
    assert_file("raw/full_text/ansmann_2021_acp.md")
    assert idx["summary"]["primary_entries"] == 1
    assert idx["summary"]["wiki_ingest_needed"] == 1
    return "DOI row plus PDF pairs locally; QC stub creates final full_text", local_out + "\n\n--- QC stub ---\n\n" + qc_out


def scenario_pdf_backfill_updates_existing_full_text_without_staging() -> tuple[str, str]:
    reset_database()
    doi = "10.5194/acp-21-9779-2021"
    add_dois(doi)
    write_qced_full_text(
        "raw/full_text/ansmann_2021_acp.md",
        doi,
        "Tropospheric and stratospheric wildfire smoke profiling with lidar",
    )
    index_out = run(["python3", "tools/build_full_text_index.py"]).stdout
    copy_fixture("acp-21-9779-2021.pdf", "manual-backfill.pdf")
    out = paper_intake_local_import()
    dash = read_dashboard()
    full_text = (ROOT / "raw" / "full_text" / "ansmann_2021_acp.md").read_text(encoding="utf-8")
    idx = read_index()
    assert_contains(dash, doi)
    assert_contains(dash, "full_text_done")
    assert_contains(dash, "ingest_full_text_to_wiki")
    assert_contains(dash, "raw/doi_pdf/ansmann_2021_acp.pdf")
    assert_contains(full_text, "source_pdf: raw/doi_pdf/ansmann_2021_acp.pdf")
    assert_file("raw/doi_pdf/ansmann_2021_acp.pdf")
    assert_no_generated_files("raw/staging/extracted_text")
    assert idx["summary"]["primary_entries"] == 1
    assert_no_codex_launch(out)
    return "PDF backfill updates an existing QCed full_text without staging or Codex", index_out + "\n\n--- PDF backfill ---\n\n" + out


def scenario_duplicate_pdf() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-21-9779-2021.pdf")
    copy_fixture("acp-21-9779-2021.pdf", "copy-acp-21-9779-2021.pdf")
    out = paper_intake_local_import()
    idx = read_index()
    assert idx["summary"]["primary_entries"] == 0
    assert_contains(out, "duplicate-looking PDF")
    assert_file("raw/staging/extracted_text/ansmann_2021_acp.md")
    assert_no_file("raw/full_text/ansmann_2021_acp.md")
    assert_no_codex_launch(out)
    return "duplicate PDF warns while local staging evidence stays canonical", out


def scenario_non_pdf_rejected() -> tuple[str, str]:
    reset_database()
    (ROOT / "raw" / "doi_pdf" / "not_a_pdf.pdf").write_text("<html>not a pdf</html>", encoding="utf-8")
    out = paper_intake_local_import()
    assert_contains(out, "does not look like a PDF")
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_codex_launch(out)
    return "HTML/error file in doi_pdf is rejected", out


def scenario_valid_pdf_no_doi() -> tuple[str, str]:
    reset_database()
    make_no_doi_pdf()
    out = paper_intake_local_import()
    assert_contains(out, "no DOI could be extracted")
    assert read_index()["summary"]["primary_entries"] == 0
    assert_no_codex_launch(out)
    return "valid PDF without DOI is not silently ingested", out


def scenario_pdf_doi_mismatch_creates_separate_row() -> tuple[str, str]:
    reset_database()
    add_dois("10.5194/acp-21-9779-2021")
    copy_fixture("acp-8-15-2008.pdf", "wrong-paper.pdf")
    out = paper_intake_local_import()
    dash = read_dashboard()
    assert_one_dashboard_row_for("10.5194/acp-21-9779-2021")
    assert_one_dashboard_row_for("10.5194/acp-8-15-2008")
    rows = main_board_rows()
    acp21 = next(row for row in rows if "10.5194/acp-21-9779-2021" in row)
    acp8 = next(row for row in rows if "10.5194/acp-8-15-2008" in row)
    if "raw/doi_pdf/" in acp21:
        raise AssertionError("mismatched PDF should not be attached to queued DOI")
    assert_contains(acp8, "raw/doi_pdf/altaratz_2008_acp.pdf")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert_no_codex_launch(out)
    return "PDF DOI mismatch creates a separate DOI row instead of forcing a bad match", out


def scenario_qc_failure_keeps_staging_out_of_index() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf")
    local_out = paper_intake_local_import()
    out = paper_intake_codex_qc(extra_env={"RESEARCHWIKI_TEST_QC_FAIL": "1"})
    dash = read_dashboard()
    idx = read_index()
    assert_contains(out, "Test-mode QC failure")
    assert_contains(dash, "full_text_needed")
    assert_contains(dash, "codex_convert_to_full_text")
    if (ROOT / "raw" / "full_text" / "altaratz_2008_acp.md").exists():
        raise AssertionError("QC failure should not create raw/full_text/altaratz_2008_acp.md")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert idx["summary"]["primary_entries"] == 0
    assert_no_codex_launch(local_out)
    return "QC failure keeps staging out of raw/full_text and full_text index", local_out + "\n\n--- QC failure ---\n\n" + out


def scenario_pending_full_text_is_rejected_then_cleaned() -> tuple[str, str]:
    reset_database()
    add_dois("10.5194/acp-21-9779-2021")
    local_out = paper_intake_local_import()
    pending_path = ROOT / "raw" / "full_text" / "ansmann_2021_acp.md"
    pending_path.write_text(
        """---
title: Synthetic pending full text fixture
doi: 10.5194/acp-21-9779-2021
extraction_status: machine_extracted_needs_codex_qc
readability_status: needs_codex_qc
qc_status: pending_codex_qc
---

This file intentionally imitates a bad machine extraction in raw/full_text.
It must be rejected by lint and skipped by the full_text index.
""",
        encoding="utf-8",
    )
    build_out = run(["python3", "tools/build_full_text_index.py"]).stdout
    idx = read_index()
    assert idx["summary"]["primary_entries"] == 0
    assert idx["summary"]["fulltext_qc_needed"] == 0
    ingest_out = option7_dry_run()
    assert_contains(ingest_out, "No DOI rows currently have QCed full_text waiting for wiki ingest or cleanup.")
    lint_proc = run(["python3", "tools/wiki_lint.py"])
    if lint_proc.returncode == 0:
        raise AssertionError("wiki_lint should reject pending QC text in raw/full_text")
    assert_contains(lint_proc.stdout, "raw/full_text may only contain QCed readable full text")
    cleanup_out = reset_database()
    return (
        "pending machine-extracted full_text is rejected by lint, skipped by index, and ignored by wiki ingest",
        local_out
        + "\n\n--- pending full_text index ---\n\n"
        + build_out
        + "\n\n--- wiki ingest before cleanup ---\n\n"
        + ingest_out
        + "\n\n--- lint rejection ---\n\n"
        + lint_proc.stdout
        + "\n\n--- cleanup reset ---\n\n"
        + cleanup_out,
    )


def scenario_initializer_cleans_legacy() -> tuple[str, str]:
    reset_database()
    (ROOT / "raw" / "legacy_raw").mkdir(parents=True, exist_ok=True)
    (ROOT / "raw" / "legacy_raw" / "old.txt").write_text("legacy", encoding="utf-8")
    (ROOT / "wiki" / "code").mkdir(parents=True, exist_ok=True)
    (ROOT / "wiki" / "code" / "old.md").write_text("[[missing_page]]", encoding="utf-8")
    out = reset_database()
    if (ROOT / "raw" / "legacy_raw").exists() or (ROOT / "wiki" / "code").exists():
        raise AssertionError("initializer did not remove legacy raw/wiki artifacts")
    literature = (ROOT / "wiki" / "literature" / "literature.md").read_text(encoding="utf-8")
    assert_contains(literature, "No paper pages have been generated yet.")
    return "initializer removes legacy raw/wiki artifacts and resets indexes", out


def scenario_canonical_pdf_without_row() -> tuple[str, str]:
    reset_database()
    copy_fixture("conrick_2021_waf.pdf")
    out = paper_intake_local_import()
    dash = read_dashboard()
    assert_contains(dash, "10.1175/waf-d-21-0044.1")
    assert_contains(dash, "raw/doi_pdf/conrick_2021_waf.pdf")
    assert_file("raw/staging/extracted_text/conrick_2021_waf.md")
    assert_no_file("raw/full_text/conrick_2021_waf.md")
    assert_no_codex_launch(out)
    return "canonical-named orphan PDF still creates DOI row and staging only", out


def scenario_second_run_idempotent() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf")
    paper_intake_local_import()
    out = paper_intake_local_import()
    idx = read_index()
    assert idx["summary"]["primary_entries"] == 0
    assert_contains(read_dashboard(), "codex_convert_to_full_text")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert_no_file("raw/full_text/altaratz_2008_acp.md")
    assert_no_codex_launch(out)
    return "running local import twice is idempotent before Codex QC", out


def scenario_option7_dry_run() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-12-7285-2012.pdf")
    paper_intake_local_import()
    no_qc_out = option7_dry_run()
    assert_contains(no_qc_out, "No DOI rows currently have QCed full_text waiting for wiki ingest or cleanup.")
    paper_intake_codex_qc()
    out = option7_dry_run()
    assert_contains(out, "Codex launch skipped because RESEARCHWIKI_NO_OPEN=1.")
    assert_contains(out, "Create, update, or clean wiki/literature paper pages from already QCed raw/full_text Markdown")
    assert_contains(out, "Do not acquire new PDFs, new sources, or perform full_text reflow/QC")
    return "wiki ingest ignores staging and selects only QCed full_text rows", no_qc_out + "\n\n--- after QC ---\n\n" + out


def scenario_article_url_stays_in_source_queue() -> tuple[str, str]:
    reset_database()
    paper_sources = ROOT / "raw" / "paper_sources.md"
    paper_sources.write_text(
        paper_sources.read_text(encoding="utf-8").replace(
            "```text\n\n```",
            "```text\nhttps://example.org/articles/no-doi-yet\n```",
        ),
        encoding="utf-8",
    )
    option5_out = paper_intake_open_sources()
    assert_contains(option5_out, "https://example.org/articles/no-doi-yet")
    assert_contains(read_paper_sources(), "https://example.org/articles/no-doi-yet")
    return "article URL without DOI remains in source queue and intake lists it", option5_out


def scenario_explicit_source_fallback_is_llm_only_exception() -> tuple[str, str]:
    reset_database()
    paper_sources = ROOT / "raw" / "paper_sources.md"
    paper_sources.write_text(
        paper_sources.read_text(encoding="utf-8").replace(
            "```text\n\n```",
            "```text\nhttps://example.org/articles/no-doi-yet\n```",
        ),
        encoding="utf-8",
    )
    local_out = paper_intake_open_sources()
    assert_no_codex_launch(local_out)
    fallback_out = paper_intake_source_fallback()
    assert_contains(fallback_out, "Codex Source-Resolution Fallback")
    assert_contains(fallback_out, "Prompt that would be sent to Codex")
    return "source-resolution fallback is explicit LLM path, not local intake", local_out + "\n\n--- fallback ---\n\n" + fallback_out


SCENARIOS = [
    scenario_only_doi_in_legacy_list_creates_row_only,
    scenario_command_add_source_doi_then_local_import,
    scenario_doi_and_url_sources_dedupe_without_codex,
    scenario_duplicate_doi_across_queues_creates_one_row,
    scenario_open_authorized_sources_is_local_no_token,
    scenario_pdf_only_imports_to_staging_not_full_text,
    scenario_uppercase_pdf_extension_imports_to_canonical_lowercase,
    scenario_pdf_import_without_text_extractor_keeps_pdf_only,
    scenario_doi_list_plus_pdf_pairs_then_qc_stub,
    scenario_pdf_backfill_updates_existing_full_text_without_staging,
    scenario_duplicate_pdf,
    scenario_non_pdf_rejected,
    scenario_valid_pdf_no_doi,
    scenario_pdf_doi_mismatch_creates_separate_row,
    scenario_qc_failure_keeps_staging_out_of_index,
    scenario_pending_full_text_is_rejected_then_cleaned,
    scenario_initializer_cleans_legacy,
    scenario_canonical_pdf_without_row,
    scenario_second_run_idempotent,
    scenario_option7_dry_run,
    scenario_article_url_stays_in_source_queue,
    scenario_explicit_source_fallback_is_llm_only_exception,
]


def build_final_sample_state() -> str:
    reset_database()
    for name in [
        "acp-8-15-2008.pdf",
        "acp-12-7285-2012.pdf",
        "acp-21-9779-2021.pdf",
        "conrick_2021_waf.pdf",
    ]:
        copy_fixture(name)
    local_out = paper_intake_local_import()
    qc_out = paper_intake_codex_qc()
    return local_out + "\n\n--- QC stub ---\n\n" + qc_out


def finish_state() -> tuple[str, str]:
    if os.environ.get("RESEARCHWIKI_LEAVE_SAMPLE_STATE") == "1":
        return "sample", build_final_sample_state()
    return "clean", reset_database()


def main() -> int:
    started = datetime.now()
    results: list[dict[str, str]] = []
    for index, scenario in enumerate(SCENARIOS, start=1):
        name = scenario.__name__
        try:
            description, output = scenario()
            validation = run_post_scenario_checks()
            results.append({"index": str(index), "name": name, "description": description, "status": "PASS", "output": output + "\n\n--- post-scenario checks ---\n\n" + validation})
            print(f"PASS {index}: {description}")
        except Exception as exc:
            results.append({"index": str(index), "name": name, "description": name, "status": "FAIL", "output": str(exc)})
            print(f"FAIL {index}: {name}: {exc}")

    final_state, final_output = finish_state()
    finished = datetime.now()

    lines = [
        "---",
        "type: maintenance",
        "status: draft",
        "source_status: personal-note",
        "reading_status: mixed",
        "review_stage: ai-extracted",
        "topics: []",
        "subtopics: []",
        "keywords: [workflow_test, doi_ingest]",
        f"created: {started.date().isoformat()}",
        f"updated: {finished.date().isoformat()}",
        "sources: []",
        "---",
        "",
        f"# Research Wiki Workflow Test Report {finished.date().isoformat()}",
        "",
        f"- Started: {started.isoformat(timespec='seconds')}",
        f"- Finished: {finished.isoformat(timespec='seconds')}",
        f"- Scenarios: {len(results)}",
        f"- Passed: {sum(1 for item in results if item['status'] == 'PASS')}",
        f"- Failed: {sum(1 for item in results if item['status'] == 'FAIL')}",
        "",
        "## Results",
        "",
    ]
    for item in results:
        lines.extend(
            [
                f"### {item['index']}. {item['description']}",
                "",
                f"- Status: {item['status']}",
                f"- Function: `{item['name']}`",
                "",
                "```text",
                compact_report_text(item["output"]),
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Final State",
            "",
            (
                "The test runner left a four-paper sample state for manual inspection."
                if final_state == "sample"
                else "The test runner reset the database to a clean template state after all scenarios."
            ),
            "",
            "```text",
            compact_report_text(final_output),
            "```",
            "",
            "## Graph Links",
            "",
            "- Topics:",
            "- Subtopics:",
            "- Related literature:",
            "- Related synthesis:",
            "- Related seminars:",
            "- Related projects: [[project_synthesis/project_synthesis]]",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 1 if any(item["status"] == "FAIL" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
