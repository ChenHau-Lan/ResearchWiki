---
name: research-wiki-fulltext-acquisition
description: Use this project-local skill when acquiring authorized full text for paper-source Research Wiki intake, saving DOI PDFs, converting extraction staging into QCed readable Markdown, verifying completeness, and updating raw/full_text_index without writing wiki paper pages.
---

# Research Wiki Full-Text Acquisition

Use this skill for DOI or article URL intake when the goal is to obtain legal, complete, readable full-text Markdown for this repository.

Canonical command-independent rules live in `core/skills/research-wiki-fulltext-acquisition/SKILL.md`, `core/principles.md`, and `core/data_contract.md`. Treat those files as authoritative if this project-local wrapper drifts.

Default product workflow is source-first and semi-automatic: collect DOI/URL/PDF source pointers, open authorized DOI/publisher pages, let the user download PDFs into `raw/doi_pdf/`, run local evidence import and staging extraction, then run Codex reflow/QC before writing `raw/full_text/`. Use Codex source finding as a fallback for open publisher HTML/XML, authorized browser-session capture, or rows where metadata/source judgment is genuinely needed.

This skill stops at full-text acquisition. Wiki paper-page creation is a separate handoff handled by the Research Wiki academic writing workflow.

Recommended Codex reasoning effort: `high` only for exceptional source/full-text finding. The task requires source-route judgment, metadata verification, legal access checks, filename decisions, and completeness validation, but it should not spend effort on exhaustive route chasing or cross-paper synthesis.

## Core Rules

- Preserve the evidence chain.
- Do not bypass paywalls, CAPTCHA, robots, or credential barriers.
- Authorized browser-session capture is allowed only when the user can already access the content.
- If the user reports that the article page is readable in a normal browser and that the PDF button can be downloaded, treat this as authorized browser-session access. Do not stop at shell `curl`/`wget` failures.
- Prefer publisher XML/HTML or authorized DOM when it gives complete article text.
- When publisher shell requests return 403 but the browser page works, use browser-session PDF download before marking the DOI blocked.
- If readable full text already exists from HTML/XML/DOM but the DOI PDF is missing, treat the DOI as needing PDF backfill. Save the PDF evidence when the browser PDF button is legally available.
- Save DOI PDFs, when obtained, to `raw/doi_pdf/<paper_file_key>.pdf`.
- Output final readable Markdown to `raw/full_text/<paper_file_key>.md` only after Codex reflow/QC.
- For `ResearchWikiCodex.command` Codex-first flows, first try legal complete online text. If that fails, open the publisher/DOI page where the user can download the PDF, ask the user to save it into `raw/doi_pdf/`, confirm the file exists, then continue. Do not create new persistent staging full text in this Codex-first path.
- When legal web full text is complete, write QCed `raw/full_text/` from the web source and mark PDF backfill optional. Do not require PDF before wiki ingest solely for layout evidence.
- Prefer opening a small number of DOI/source pages for user download over a long Codex search session.
- If complete text and PDF are still unavailable but a reliable abstract is available, write an abstract-only `raw/full_text/<paper_file_key>.md` placeholder and mark the dashboard `abstract_only`.
- If a PDF is obtained, extract machine text to `raw/staging/extracted_text/` first, then convert it into QCed `raw/full_text/`. Do not leave the task at PDF-only unless extraction fails or the PDF is unreadable.
- If a legal complete source is not obvious after local evidence, publisher landing page, obvious open HTML/XML/PDF, and visible browser PDF controls, stop and update the dashboard with `authorized_browser_or_user_pdf_needed` instead of spending a long session searching.
- `paper_file_key` is `first_author_last_name_year_journal_abbrev`, all lowercase ASCII, with punctuation removed and spaces changed to underscores. Prefer standard journal abbreviations when known. If there is a collision, append a short DOI slug.
- Rebuild the index with `python3 tools/build_full_text_index.py`.
- Do not copy full paper text into `wiki/literature/`.
- Do not create or update `wiki/literature/` in this skill.

## Acquisition Priority

1. Existing verified Markdown in `raw/full_text/`.
2. Legal complete online text: publisher HTML/XML, open-access full text, authorized browser DOM, or user-provided source text.
3. Existing local PDF in `raw/doi_pdf/`, then local extraction/reflow in memory for the canonical Codex-first command, or staging for legacy workflows.
4. Missing PDF backfill for entries that already have full text but no `raw/doi_pdf/<paper_file_key>.pdf`.
5. User-provided full text or local saved publisher HTML/XML.
6. Authorized browser-session PDF download from the visible article page.
7. Authorized Chrome DOM capture when complete text is visible but PDF download is not available.
8. Publisher PDF through normal public or authorized access.
9. Open-access repository PDF or author manuscript.
10. Ask for user-provided PDF through the command's authorized PDF page workflow, then continue after confirming the file exists.
11. If a reliable abstract is available, create an abstract-only `raw/full_text/` placeholder and set dashboard status `abstract_only`.
12. Mark `blocked` or `full_text_needed`.

## Filename Rules

- Always verify first author, publication year, and journal before final naming.
- Use last name only for the first author: `conrick`, `smith`, `chen`.
- Use the publication year from the article metadata.
- Use a compact journal abbreviation when obvious or officially known:
  - `Weather and Forecasting` -> `waf`
  - `Bulletin of the American Meteorological Society` -> `bams`
  - `Atmospheric Chemistry and Physics` -> `acp`
  - `Frontiers in Earth Science` -> `front_earth_sci`
  - `Remote Sensing` -> `remote_sens`
  - `PLOS ONE` -> `plos_one`
- Example: `10.1175/WAF-D-21-0044.1` should become `conrick_2021_waf.pdf` and `conrick_2021_waf.md` after metadata is verified.
- If journal abbreviation is unclear, use a short journal slug and record the unresolved abbreviation in the dashboard note.

## PDF / Article Discovery Playbook

Use this order. Stop when a legal complete source is obtained, or when the next step should be user PDF download.

1. Resolve DOI landing page with normal browser behavior.
2. Check Crossref metadata for publisher, journal, year, license, and resource links.
3. Check Unpaywall or open-access indicators when available.
4. Inspect the publisher article page for `PDF`, `Download PDF`, `Full Text`, `XML`, `ePDF`, `View Article`, citation metadata, and canonical links.
5. Try stable publisher patterns only when they are normal public URLs for that publisher. Do not brute-force private endpoints.
6. Search exact DOI in quotes plus `PDF`, exact title in quotes plus `PDF`, and first-author/title only when a quick open-access route is plausible.
7. Prefer publisher HTML/XML for Markdown extraction when it is complete; save PDF as evidence when available.
8. If a shell route returns 403, bot block, or CloudFront denial but the user/browser can view the article, switch to the browser-session download protocol below.
9. If the browser route hits CAPTCHA, login wall, missing authorization, or an inaccessible PDF button, do not bypass it. Ask the user to provide the PDF or retry after opening the article in an authorized browser session.
10. Record every successful source or blocker in `raw/doi_dashboard.md` Note.

## Recommended Semi-Automatic Flow

Use this for normal batches:

1. Run command `Paper intake: sources -> QCed full_text`.
2. Download legal PDFs from publisher, author, open-access, institutional, or user-provided sources.
3. Save the PDFs directly in `raw/doi_pdf/`.
4. Rerun `Paper intake: sources -> QCed full_text` after saving PDFs.
5. Run `Ingest QCed full_text to wiki`.

Codex source/full-text finding inside Paper intake is for exceptions: open publisher HTML/XML extraction, authorized browser-session capture, or a small number of rows where metadata and access judgment matter. It should not become a long-running route chase for a DOI queue.

## Browser-Session PDF Download Protocol

Use this when a normal browser can view the full article or click the publisher PDF button, especially when shell requests return 403.

1. Emit `RW_ATTEMPT|<doi>|browser-session PDF download|<doi_or_article_url>`.
2. Open the DOI landing page or canonical publisher article page in the user's browser session when browser automation is available.
3. Look for visible controls named `PDF`, `Download PDF`, `Article PDF`, `ePDF`, `Full Text PDF`, or equivalent accessible labels.
4. Prefer clicking the visible publisher control over guessing hidden endpoints. Many publishers use session cookies, signed URLs, redirects, or download tokens that are only available from the browser page.
5. If automation supports setting the download folder, set it to `raw/doi_pdf/` before clicking. Otherwise download to the browser default downloads folder, then import exactly the newly downloaded PDF and rename it to `raw/doi_pdf/<paper_file_key>.pdf`.
6. Only import a browser-downloaded file when it is a single, clearly new PDF that matches the current DOI/title. Do not bulk move files from Downloads.
7. Verify the saved file:
   - file extension is `.pdf`;
   - file begins with a PDF signature or can be opened by PDF tools;
   - first pages or extracted text match the DOI/title;
   - file is not a login page, HTML error page, CAPTCHA page, or publisher cover-only stub.
8. After saving the PDF, immediately run the PDF-to-Markdown gate.
9. If readable full text already exists, update its frontmatter `source_pdf: raw/doi_pdf/<paper_file_key>.pdf` after verifying the PDF. Preserve the existing `source_type` and `source_path` if they describe the HTML/XML/DOM source.
10. If the browser opens an in-browser PDF viewer rather than downloading, use the viewer's download button or capture the final PDF URL only when it is authorized in the same browser session.
11. If browser automation is unavailable, open the article page for the user and ask them to click the PDF button; the user should place the downloaded PDF directly in `raw/doi_pdf/`. The local command maintenance step will detect extra PDFs in that folder, rename matched files to `raw/doi_pdf/<paper_file_key>.pdf`, and update the dashboard/index.

Suggested progress lines:

```text
RW_ATTEMPT|<doi>|browser-session article page|<url>
RW_ATTEMPT|<doi>|browser-session PDF button|<button_text_or_href>
RW_RESULT|<doi>|success|downloaded authorized PDF from browser session
RW_RESULT|<doi>|failed|browser session could not access PDF: <reason>
```

These are examples only. Do not emit angle-bracket placeholder lines as real command output.

Common public patterns to try after metadata verification:

- AMS / AMETSOC: DOI landing page, `journals.ametsoc.org/view/journals/<journal>/<volume>/<issue>/<DOI>.xml`, `journals.ametsoc.org/downloadpdf/journals/<journal>/<volume>/<issue>/<DOI>.pdf`, or authorized browser download.
- Copernicus: article pages commonly expose `/articles/<volume>/<page>/<year>/` and PDFs like `<journal>-<volume>-<page>-<year>.pdf`.
- Frontiers: article pages commonly expose `/journals/<journal>/articles/<DOI suffix>/full` and a visible PDF download.
- MDPI: article pages commonly expose HTML and PDF buttons; PDF routes often derive from ISSN/volume/issue/article number metadata.
- PLOS: article pages commonly expose printable/PDF file routes with `id=<DOI>&type=printable`.

## AMS / AMETSOC Notes

- Do not bypass CloudFront, CAPTCHA, robots, paywalls, or credential barriers.
- AMS states that WAF and other AMS technical journal articles are free to read through AMS Journals Online 12 months after publication.
- If a direct programmatic fetch returns CloudFront 403 but the article is visible in the browser, use the browser-session PDF download protocol. This is the preferred AMS fallback before asking the user to provide the PDF.
- For AMS, prefer the visible `PDF` / `Download PDF` control on the article page over brute-forcing CloudFront or private asset URLs.
- For AMS DOI patterns, try the DOI landing page first. When metadata reveals journal/volume/issue, candidate URLs often use:
  - `https://journals.ametsoc.org/view/journals/<journal>/<volume>/<issue>/<DOI>.xml`
  - `https://journals.ametsoc.org/downloadpdf/journals/<journal>/<volume>/<issue>/<DOI>.pdf`
  - `https://journals.ametsoc.org/doi/pdf/<DOI>`
- For `10.1175/WAF-D-21-0044.1`, the likely AMS paths are:
  - `https://journals.ametsoc.org/view/journals/wefo/36/4/WAF-D-21-0044.1.xml`
  - `https://journals.ametsoc.org/downloadpdf/journals/wefo/36/4/WAF-D-21-0044.1.pdf`

## Completeness Gate

Before marking full text as usable, verify:

- Title and DOI match.
- Abstract is present.
- Body sections are present.
- Conclusion/summary is present when the article has one.
- Figure/table captions are not obviously missing.
- References are present.
- Appendices and supplementary-material notes are present when the article has them.
- Text is readable top-to-bottom.
- Equations and tables are flagged if extraction quality is uncertain.

## Reflow / Noise Cleanup Gate

Before writing `raw/full_text/` or allowing wiki ingest:

- Repair sentence and paragraph breaks introduced by PDF extraction.
- Dehyphenate words split across line endings when context is clear.
- Remove repeated page headers/footers, journal/date/author page furniture, page numbers, and orphaned equation fragments.
- Treat disconnected fragments such as isolated article date, author name, and equation-symbol blocks as extraction noise unless they are needed to preserve a meaningful equation.
- Ensure each article section has a clear Markdown heading and appears in order.
- Ensure figure captions and table captions are labeled and not merged into unrelated paragraphs.
- Preserve each table caption as its own `### Table N. <caption>` section.
- Use Markdown tables only when row/column structure is clear. For wide,
  numeric, multi-page, or continued tables, keep the content in a fenced `text`
  block under the table heading with `Table status`, source pages when known,
  and a note that numeric reuse requires PDF/supplement checking.
- Keep `Table N. Continued` under the same table section. Never let table rows,
  one-word column fragments, or continuation markers spill into prose.
- Set `table_quality: good`, `partial`, `poor`, or `not_applicable` in final
  full_text frontmatter. If a central table cannot be recovered from HTML/XML,
  PDF, or supplement, mark `table_quality: poor` and keep the dashboard at
  `full_text_needed` when that prevents trustworthy reading.
- If the article is still noisy after cleanup, keep dashboard status `full_text_needed` and record a blocker rather than marking it full-read.

## PDF-to-Staging-to-Full-Text Gate

When only PDF is available:

1. Save the PDF first under `raw/doi_pdf/<paper_file_key>.pdf`.
2. Try text extraction with available local tools such as `pdftotext`, PyMuPDF, or another project-approved extractor.
3. Write machine-extracted Markdown to `raw/staging/extracted_text/<paper_file_key>.md`.
4. Preserve page/section order as much as possible.
5. Mark `extraction_status: machine_extracted_needs_codex_qc`, `readability_status: needs_codex_qc`, `qc_status: pending_codex_qc`, and `equation_quality: not_checked`.
6. Run Codex reflow/QC and write final readable Markdown to `raw/full_text/<paper_file_key>.md` only if QC succeeds.
7. If extraction or QC fails, leave the PDF/staging path in the dashboard Note and set `Next Action` to `codex_convert_to_full_text`.

For the canonical Codex-first command, do not write new staging files. Use in-memory extraction or legal online text, then write only QCed `raw/full_text/`, abstract-only placeholder, or a dashboard blocker.

## Metadata

Readable full-text Markdown should include frontmatter with:

- `doi`
- `title`
- `authors`
- `journal` or venue
- `year`
- `source_type`
- `source_path` or `source_pdf`
- `status` or `extraction_status`
- `readability_status`
- `equation_quality`
- `table_quality`
- `language`
- `created`
- `updated`

## Duplicate DOI / PDF Guard

Before spending Codex time, check whether the canonical DOI already has
`raw/doi_pdf/`, `raw/full_text/`, or an index/dashboard row. Reuse existing
evidence instead of creating another paper entry.

- Normalize DOI URLs and DOI strings before comparison.
- Treat Copernicus filename-copy suffixes such as
  `10.5194/acp-5-799-2005-2` or `10.5194/acp-5-799-2005-3` as duplicates of
  `10.5194/acp-5-799-2005`, not as new papers.
- If duplicate PDF files are found, do not delete them automatically. Report
  the duplicate paths and continue with the canonical PDF/full_text only.

## Acquisition Handoff

After QCed full text exists:

1. Run `python3 tools/build_full_text_index.py`.
2. Update `raw/doi_dashboard.md`.
3. If only staging text exists, keep DOI dashboard `Status` as `full_text_needed` and `Next Action` as `codex_convert_to_full_text`.
4. After Codex reflow/QC succeeds, set DOI dashboard `Status` to `full_text_done` and `Next Action` to `ingest_full_text_to_wiki`, or continue to wiki ingest.
5. If only `raw/doi_pdf/<paper_file_key>.pdf` exists, keep `Status` as `full_text_needed`, set `Next Action` to `codex_convert_to_full_text`, and record the PDF path in `Note`.
6. Do not mark `wiki_done`; that belongs to the separate wiki ingest step.

## Repository Paths

- Paper-source input: `raw/paper_sources.md`
- Legacy DOI input: `raw/doi_list.md`
- DOI progress: `raw/doi_dashboard.md`
- DOI PDFs: `raw/doi_pdf/`
- Extraction staging: `raw/staging/extracted_text/`
- Raw user files: `raw/files/`
- Readable full text: `raw/full_text/`
- Full-text index: `raw/full_text_index.md`, `raw/full_text_index.json`
- Paper pages: `wiki/literature/`
- Repair tools: `tools/wiki_doctor.py`, `tools/generate_repair_plan.py`
