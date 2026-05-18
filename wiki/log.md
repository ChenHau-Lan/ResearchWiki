---
type: synthesis
status: draft
source_status: personal-note
topics: [log]
created: 2026-05-16
updated: 2026-05-16
sources: []
---

# Research Wiki Log

Append-only log. Entries should use this heading format:

`## [YYYY-MM-DD] workflow | short title`

## [2026-05-16] setup | Initialized research wiki v1

- Created canonical layers: `raw/`, `inbox/`, `wiki/`, `templates/`, `notion/`.
- Added topic-first wiki taxonomy.
- Added workflow rules in `AGENTS.md`.
- Added initial `references.bib` placeholder.

## [2026-05-17] ingest-paper | Imported Zotero library metadata

- Enabled Zotero local API and exported 247 BibTeX entries into `references.bib`.
- Created Zotero Library Inventory from 248 Zotero top-level items.
- Marked import as metadata-only: 4 items have URL-only/incomplete titles, and no paper-level claims were added without full-text verification.
- Updated topic indexes for aerosol, cloud microphysics, remote sensing, modeling, and synthesis.

## [2026-05-17] ingest-paper | Cleaned Zotero metadata and started first paper pages

- Replaced 5 incomplete Zotero-exported BibTeX entries with verified metadata: `levin_aerosol_2009`, `liu_significant_2022`, `chen_evaluation_2020`, `baars_unprecedented_2019`, and `wang_wildfire_2025`.
- Added metadata override file for repeatable Zotero inventory generation.
- Started 5 formal paper pages with conservative read status labels; no full-text claims were added.
- Left 2 non-paper items in metadata cleanup: an email confirmation webpage and a pre-arrival guide attachment.

## [2026-05-17] synthesis | Added Obsidian presentation layer

- Added `研究知識庫首頁.md` as a vault-level dashboard.
- Added `Zotero 文獻地圖.canvas` for visual navigation of the Zotero import and started paper pages.
- Added Zotero Reading Queue to track paper upgrade priority.

## [2026-05-17] synthesis | Simplified Obsidian wiki structure

- Renamed topic README files to explicit topic MOC filenames for clearer Obsidian graph nodes.
- Moved the dashboard and canvas into `wiki/` as `home.md` and `zotero_mind_map.canvas`.
- Simplified [[index|Research Wiki Index]] into a concise hub for topic pages, inventory, and reading queue.

## [2026-05-17] synthesis | Enforced three-layer Obsidian graph

- Added subtopic MOCs so Graph View follows topic hub → subtopic → paper.
- Removed direct paper links from high-level dashboard/index pages.
- Set Obsidian Graph View filter to hide maintenance pages by default.
- Rebuilt `zotero_mind_map.canvas` as a three-layer map.

## [2026-05-17] refactor | Simplified literature schema and wiki folders

- Removed `main_keywords` from generated literature schema; `topics` now carries broad subject categories.
- Renamed `sub_keywords` to `keywords` for detailed cross-linking.
- Renamed `sub_*` keyword pages to `keyword_*` and removed obsolete `main_*` keyword pages one explicit file at a time.
- Simplified `wiki/` to `.obsidian/`, `literature/`, and `code/`; removed obsolete empty topic folders and legacy MOC files one explicit path at a time.
- Removed obsolete `home.md` and `zotero_mind_map.canvas`; Graph View now relies on `literature/` plus keyword pages.

## [2026-05-17] ingest-paper | Promoted external search candidates

- Added `deshler_a_2008` from Crossref metadata: A review of global stratospheric aerosol: Measurements, importance, life cycle, and local stratospheric aerosol
- Added `liu_sensitivity_2007` from Crossref metadata: Sensitivity of Cloud-Resolving Simulations of Warm-Season Convection to Cloud Microphysics Parameterizations
- Added `kogan_a_2013` from Crossref metadata: A Cumulus Cloud Microphysics Parameterization for Cloud-Resolving Models
- Added `selimovic_in_2019` from Crossref metadata: In situ measurements of trace gases, PM, and aerosol optical properties during the 2017 NW US wildfire smoke event
- Added `min_evaluation_2015` from Crossref metadata: Evaluation of WRF Cloud Microphysics Schemes Using Radar Observations
- Added `ekman_impact_2011` from Crossref metadata: Impact of Two-Way Aerosol–Cloud Interaction and Changes in Aerosol Size Distribution on Simulated Aerosol-Induced Deep Convective Cloud Sensitivity
- Added `glotfelty_the_2019` from Crossref metadata: The Weather Research and Forecasting Model with Aerosol–Cloud Interactions (WRF-ACI): Development, Evaluation, and Initial Application
- Added `ovtchinnikov_nonlinear_2009` from Crossref metadata: Nonlinear Advection Algorithms Applied to Interrelated Tracers: Errors and Implications for Modeling Aerosol–Cloud Interactions

## [2026-05-17] ingest-paper | Promoted external search candidates

- Added `grabowski_cloud_2000` from Crossref metadata: Cloud Microphysics and the Tropical Climate: Cloud-Resolving Model Perspective
- Added `yu_on_2018` from Crossref metadata: On the Linkage among Strong Stratospheric Mass Circulation, Stratospheric Sudden Warming, and Cold Weather Events
- Added `geresdi_evaluation_2017` from Crossref metadata: Evaluation of Orographic Cloud Seeding Using a Bin Microphysics Scheme: Two-Dimensional Approach
- Added `jia_exploring_2019` from Crossref metadata: Exploring aerosol–cloud interaction using VOCALS-REx aircraft measurements
- Added `liang_future_2023` from Crossref metadata: Future changes in atmospheric rivers over East  Asia under stratospheric aerosol intervention
- Added `ward_a_2011` from Crossref metadata: A Method for Forecasting Cloud Condensation Nuclei Using Predictions of Aerosol Physical and Chemical Properties from WRF/Chem
- Added `aydell_mobile_2021` from Crossref metadata: Mobile Ka-Band Polarimetric Doppler Radar Observations of Wildfire Smoke Plumes
- Added `timmreck_a_2000` from Crossref metadata: A microphysical model for simulation of stratospheric aerosol in a climate model

## [2026-05-17] refactor | Full-text filter and scheme directions

- Marked literature pages with `full_text: true/false` based on PDF `file` fields in `references.bib`.
- Added `keyword_microphysics_scheme` and `keyword_aerosol_scheme` using only full-text-visible literature pages.
- Wrote no-fulltext deletion candidates to `raw/papers/no-fulltext-delete-candidates-2026-05-17.md`.
- Removed two non-paper pages one explicit file at a time: I-901 payment confirmation and pre-arrival guide attachment.
- Updated Obsidian Graph View search to hide `full_text: false` pages by default.

## [2026-05-18] refactor | Separated paper, code, and synthesis roles

- Updated `AGENTS.md` with explicit knowledge boundaries: paper pages are single-paper facts, code pages are implementation facts, and synthesis pages are research judgment.
- Added `reading_status`, `review_stage`, and `keywords` frontmatter rules.
- Added `templates/synthesis.md`.
- Added `wiki/synthesis/synthesis.md` and `wiki/concepts/concepts.md` as new top-level entry points.
- Updated `wiki/index.md`, `wiki/literature/literature.md`, and page templates to reflect the new architecture.

## [2026-05-18] taxonomy | Added paper topics registry

- Added `wiki/literature/paper_topics.md` as the controlled list for paper frontmatter `topics:`.
- Updated `AGENTS.md`, `wiki/index.md`, and `wiki/literature/literature.md` so paper topics are selected from the registry before new broad topics are introduced.

## [2026-05-18] taxonomy | Promoted candidate paper topics

- Promoted `radar_meteorology`, `field_campaigns`, and `climate_change` to active paper topics.
- Added simplification guidance so mechanism/method terms such as `pyrocb`, `retrieval_validation`, `drop_size_distribution`, and `microphysics_scheme` stay in `keywords:` rather than broad `topics:`.

## [2026-05-18] taxonomy | Revised active paper topic list

- Revised active paper topics to: `aerosol`, `microphysics`, `cloud_physics`, `remote_sensing`, `modeling`, `instrumentation`, `tropical_cyclone`, `precipitation`, `wildfire`, `radar_meteorology`, `field_campaign`, and `climate_change`.
- Moved `cloud_microphysics`, `wildfire_smoke`, `field_campaigns`, and `stratospheric_aerosol` guidance into simplification/candidate rules instead of keeping them as active topic names.
- Kept `radar_meteorology` as the active topic name; use `radar_metrology` as a keyword only when the source is specifically about radar measurement/calibration uncertainty.

## [2026-05-18] lint-wiki | Converted paper topics to revised registry

- Added `wiki/literature/topic_cleanup_report.md`.
- Converted 47 paper pages from old topic names to the revised active topic registry.
- Moved detailed terms such as `pyrocb`, `wildfire_smoke`, `stratospheric_aerosol`, `retrieval_validation`, and `aerosol_cloud_interaction` into `keywords:`.
- Moved `needs_triage` from `topics:` into `keywords:` where applicable.
- Synced paper page body `## Keywords` display lines with the revised frontmatter.
- Verified that no paper page still uses a non-registry topic after conversion.

## [2026-05-18] lint-wiki | Audited paper template compliance

- Added `wiki/literature/paper_template_audit.md`.
- Checked all `type: paper` pages against the current paper template.
- Added missing `reading_status`, `review_stage`, `keywords`, and required paper sections where absent.
- No paper claims were changed during the audit.

## [2026-05-18] ingest-paper | Added aerosol and microphysics scheme anchors

- Added `raw/literature_search/aerosol_microphysics_scheme_search_2026-05-18.md`.
- Added or linked BibTeX entries and paper pages for aerosol scheme, microphysics scheme, and aerosol-microphysics coupling anchors.
- Added `wiki/synthesis/aerosol_microphysics_scheme_synthesis.md`.
- Added `wiki/synthesis/aerosol_microphysics_questions_2026-05-18.md` to record the user's research questions and follow-up questions.
