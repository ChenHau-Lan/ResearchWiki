#!/usr/bin/env python3
"""Reset-first workflow tests for ResearchWiki.command.

This test runner is intentionally integration-heavy: each scenario resets the
local test database, lays down a small fixture state, runs the command helper,
and records what happened. It uses only scoped project reset behavior.
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


def option1_paper_intake(input_text: str = "1\n\n\n\n0\n", *, extra_env: dict[str, str] | None = None) -> str:
    proc = run(["python3", "tools/research_wiki_shortcut.py"], input_text=input_text, extra_env=extra_env)
    if proc.returncode != 0:
        raise AssertionError(f"paper intake failed:\n{proc.stdout}")
    return proc.stdout


def option6() -> str:
    return option1_paper_intake()


def option6_qc_fail() -> str:
    return option1_paper_intake(extra_env={"RESEARCHWIKI_TEST_QC_FAIL": "1"})


def option5_dry_run() -> str:
    proc = run(["python3", "tools/research_wiki_shortcut.py"], input_text="1\n\n1\n\n0\n")
    if proc.returncode != 0:
        raise AssertionError(f"paper intake source-page dry run failed:\n{proc.stdout}")
    return proc.stdout


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
    doi_list = ROOT / "raw" / "paper_sources.md"
    text = doi_list.read_text(encoding="utf-8")
    block = "\n".join(dois)
    text = re.sub(r"```text\n.*?\n```", f"```text\n{block}\n```", text, flags=re.DOTALL)
    doi_list.write_text(text, encoding="utf-8")


def assert_contains(text: str, needle: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing expected text: {needle}")


def assert_file(path: str) -> None:
    if not (ROOT / path).exists():
        raise AssertionError(f"missing expected file: {path}")


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


def scenario_orphan_acp8() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf")
    out = option6()
    dash = read_dashboard()
    idx = read_index()
    assert_contains(dash, "10.5194/acp-8-15-2008")
    assert_contains(dash, "ingest_full_text_to_wiki")
    assert idx["summary"]["fulltext_qc_needed"] == 0
    assert idx["summary"]["wiki_ingest_needed"] == 1
    assert_file("raw/full_text/altaratz_2008_acp.md")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    return "orphan ACP PDF creates DOI row and QCed full_text", out


def scenario_doi_list_plus_pdf() -> tuple[str, str]:
    reset_database()
    add_dois("https://doi.org/10.5194/acp-21-9779-2021")
    option5_out = option5_dry_run()
    assert_contains(option5_out, "Authorized Source Pages")
    assert_contains(option5_out, "10.5194/acp-21-9779-2021")
    assert_contains(option5_out, "Expected PDF: unknown")
    assert_contains(option5_out, "Open skipped because RESEARCHWIKI_NO_OPEN=1.")
    copy_fixture("acp-21-9779-2021.pdf")
    out = option6()
    dash = read_dashboard()
    assert_contains(dash, "10.5194/acp-21-9779-2021")
    assert_contains(dash, "ingest_full_text_to_wiki")
    assert_file("raw/full_text/ansmann_2021_acp.md")
    assert "10.5194/acp-21-9779-2021" not in read_paper_sources()
    return "paper intake opens sources then DOI PDF synchronizes to canonical paths", option5_out + "\n\n--- intake with PDF ---\n\n" + out


def scenario_multi_batch() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf")
    copy_fixture("acp-12-7285-2012.pdf")
    copy_fixture("conrick_2021_waf.pdf", "wefo-WAF-D-21-0044.1.pdf")
    out = option6()
    idx = read_index()
    assert idx["summary"]["primary_entries"] == 3
    assert idx["summary"]["fulltext_qc_needed"] == 0
    assert idx["summary"]["wiki_ingest_needed"] == 3
    dash = read_dashboard()
    assert_contains(dash, "10.1175/waf-d-21-0044.1")
    assert_file("raw/full_text/conrick_2021_waf.md")
    return "multiple orphan PDFs batch-import together", out


def scenario_duplicate_pdf() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-21-9779-2021.pdf")
    copy_fixture("acp-21-9779-2021.pdf", "copy-acp-21-9779-2021.pdf")
    out = option6()
    idx = read_index()
    assert idx["summary"]["primary_entries"] == 1
    assert_contains(out, "duplicate-looking PDF")
    return "duplicate PDF is warned but canonical evidence stays intact", out


def scenario_non_pdf_rejected() -> tuple[str, str]:
    reset_database()
    (ROOT / "raw" / "doi_pdf" / "not_a_pdf.pdf").write_text("<html>not a pdf</html>", encoding="utf-8")
    out = option6()
    assert_contains(out, "does not look like a PDF")
    assert read_index()["summary"]["primary_entries"] == 0
    return "HTML/error file in doi_pdf is rejected", out


def scenario_valid_pdf_no_doi() -> tuple[str, str]:
    reset_database()
    make_no_doi_pdf()
    out = option6()
    assert_contains(out, "no DOI could be extracted")
    assert read_index()["summary"]["primary_entries"] == 0
    return "valid PDF without DOI is not silently ingested", out


def scenario_qc_failure_keeps_staging_out_of_index() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf")
    out = option6_qc_fail()
    dash = read_dashboard()
    idx = read_index()
    assert_contains(out, "Test-mode QC failure")
    assert_contains(dash, "full_text_needed")
    assert_contains(dash, "codex_convert_to_full_text")
    if (ROOT / "raw" / "full_text" / "altaratz_2008_acp.md").exists():
        raise AssertionError("QC failure should not create raw/full_text/altaratz_2008_acp.md")
    assert_file("raw/staging/extracted_text/altaratz_2008_acp.md")
    assert idx["summary"]["primary_entries"] == 0
    return "QC failure keeps staging out of raw/full_text and full_text index", out


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
    out = option6()
    dash = read_dashboard()
    assert_contains(dash, "10.1175/waf-d-21-0044.1")
    assert_contains(dash, "raw/doi_pdf/conrick_2021_waf.pdf")
    assert_file("raw/full_text/conrick_2021_waf.md")
    return "canonical-named orphan PDF still creates DOI row", out


def scenario_second_run_idempotent() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-8-15-2008.pdf")
    option6()
    out = option6()
    idx = read_index()
    assert idx["summary"]["primary_entries"] == 1
    assert idx["summary"]["fulltext_qc_needed"] == 0
    assert_contains(read_dashboard(), "ingest_full_text_to_wiki")
    return "running paper intake twice is idempotent for QCed full_text rows", out


def scenario_option7_dry_run() -> tuple[str, str]:
    reset_database()
    copy_fixture("acp-12-7285-2012.pdf")
    option6()
    out = option7_dry_run()
    assert_contains(out, "Codex launch skipped because RESEARCHWIKI_NO_OPEN=1.")
    assert_contains(out, "Create, update, or clean wiki/literature paper pages from already QCed raw/full_text Markdown")
    assert_contains(out, "Do not acquire new PDFs, new sources, or perform full_text reflow/QC")
    return "wiki ingest selects QCed full_text rows and emits wiki-only prompt", out


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
    option5_out = option5_dry_run()
    assert_contains(option5_out, "https://example.org/articles/no-doi-yet")
    assert_contains(read_paper_sources(), "https://example.org/articles/no-doi-yet")
    return "article URL without DOI remains in source queue and intake lists it", option5_out


SCENARIOS = [
    scenario_orphan_acp8,
    scenario_doi_list_plus_pdf,
    scenario_multi_batch,
    scenario_duplicate_pdf,
    scenario_non_pdf_rejected,
    scenario_valid_pdf_no_doi,
    scenario_qc_failure_keeps_staging_out_of_index,
    scenario_initializer_cleans_legacy,
    scenario_canonical_pdf_without_row,
    scenario_second_run_idempotent,
    scenario_option7_dry_run,
    scenario_article_url_stays_in_source_queue,
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
    return option6()


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
            results.append({"index": str(index), "name": name, "description": description, "status": "PASS", "output": output})
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
