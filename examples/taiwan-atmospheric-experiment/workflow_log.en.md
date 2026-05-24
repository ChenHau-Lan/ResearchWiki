# Workflow Log: Organizing Atmospheric Experiments In Taiwan

## 1. Starting Request

User request:

> I want to organize atmospheric experiments in Taiwan, such as TAMEX, SoWMEX,
> and TAHOPE.

Skill routing:

- `academic-research-skills` / `deep-research:lit-review`: find SCI papers and
  plausible DOI/PDF routes.
- `academic-research-skills` / `deep-research:fact-check`: verify source
  identity and keep ARS output as proposal context.
- `rkf-evidence-vault`: capture sources, stage legal PDF routes, and run PDF QC.
- `rkf-knowledge-synthesis`: turn QCed PDFs into paper, concept, overview, and
  synthesis pages.
- `rkf-wiki-core`: answer a decision-oriented question from existing pages.
- `rkf-lint`: check that no PDFs, article text, or private paths enter Git.

## 2. Topic Design

Topic ID: `taiwan-atmospheric-field-campaigns`

The scope includes TAMEX, SoWMEX/TiMREX, TAHOPE/PRECIP, Cape Fuguei, Lulin,
complex-terrain rainfall, radar microphysics, data assimilation, and
aerosol-cloud observations in Taiwan.

## 3. Literature Search

The SCI candidate list is saved in `literature_candidates.md`. This example
ingests representative PDFs after checkpoint/QC:

- Chen and Liang 1992 TAMEX midlevel vortex
- You et al. 2020 SoWMEX IOP8 dual-polarimetric radar model validation
- Miao et al. 2025 TAHOPE/PRECIP IOP2 convective cell merger
- Cheung et al. 2020 Cape Fuguei CCN hygroscopicity
- Chang et al. 2021 CCN and diurnal precipitation over Taiwan topography
- Lin et al. 2026 Lulin aerosol-cloud mixing ratio

Kuo and Chen 1990, Chang et al. 2015, and Yang et al. 2024 remain candidate
items until legal PDF acquisition and QC are completed.

## 4. PDF QC

Each paper has a `state/gates/pdf_acquisition/*.md` record for:

- source identity
- legal route
- readability
- PDF locators
- no durable article-text layer

## 5. Wiki Ingest

Each QCed PDF becomes one `knowledge/papers/*.md` page. The page summarizes
evidence and records locators; it does not store PDFs or full article text.

## 6. Wiki Query

Question:

> What should Taiwan do in a future meteorological observation experiment?

Answer:

`knowledge/synthesis/future-taiwan-meteorological-observation-experiment.md`

Core conclusion: future Taiwan campaigns should treat TAMEX, SoWMEX/TiMREX,
and TAHOPE/PRECIP as a design ladder from terrain-rainfall diagnosis to
radar microphysics, data assimilation, prediction products, and data
governance.

## 7. Next Steps

- Add Kuo and Chen 1990 TAMEX overview after PDF QC.
- Add Chang, Lee, and Liou 2015 SoWMEX/TiMREX microphysics after PDF QC.
- Add Yang et al. 2024 TAHOPE/PRECIP IOP3 data-assimilation paper after PDF QC.
- Add radar/disdrometer/profiler/aircraft deployment papers.
- Add more Taiwan in-situ cloud-event papers.
- Promote draft synthesis claims into locator-backed claim pages.
