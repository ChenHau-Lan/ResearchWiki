# Issue #18 atmospheric-journal live smoke (2026-07-16)

This is the bounded live result for the 14-case atmospheric-journal corpus in
[`acquisition-issue-18-atmospheric-journal-corpus.json`](acquisition-issue-18-atmospheric-journal-corpus.json).
The sole observational input for this record was the designated final
`rkf-acquisition-smoke-report-v1` run; this document does not merge observations
from exploratory or earlier runs.

## Result boundary

- Inputs: 14 DOI-centred cases (11 P0 cases spanning the mandated publisher
  profiles and 3 P1 atmospheric-journal cases).
- Acquisition status: **14/14 `obtained`**.
- Downloaded artifacts: **14/14**.
- Artifact QC and identity gate: **14/14 `research_ready_verified=true`**;
  every artifact was `readable` and every identity check was `verified`.
- Promotion: **`none`**.
- External QC tools were enabled; no contact email was configured.
- This result means acquisition plus artifact QC succeeded for this bounded
  corpus at the stated test time. It does **not** mean that 14/14 records have
  complete version/license provenance, and it does not promote any Paper,
  Evidence, Claim, or Synthesis trust state.

## Routes observed

| Final route | Count |
|---|---:|
| `openalex-landing.citation-meta` | 3 |
| `crossref-link` | 2 |
| `ncbi-pmc-cloud` | 2 |
| `openalex-pdf` | 2 |
| `copernicus-direct` | 1 |
| `direct-identifier` | 1 |
| `mdpi-official-pdf` | 1 |
| `noaa-ir-landing.citation-meta` | 1 |
| `springer-official-oa` | 1 |
| **Total** | **14** |

## Per-journal outcome

An em dash in the License column means the final report recorded an empty
license value; it must not be read as evidence that no license exists.

| Tier | Publisher / journal | DOI | Status and route | Artifact version | License recorded | Pages | QC / identity |
|---|---|---|---|---|---|---:|---|
| P0 | AGU / Wiley — *AGU Advances* | `10.1029/2020AV000350` | `obtained` via `openalex-landing.citation-meta` | `preprint` | `cc-by-nc` | 8 | `readable` / `verified` |
| P0 | Wiley / RMetS — *Quarterly Journal of the Royal Meteorological Society* | `10.1002/qj.4944` | `obtained` via `noaa-ir-landing.citation-meta` | `unknown` | — | 28 | `readable` / `verified` |
| P0 | AMS — *Weather and Forecasting* | `10.1175/2009WAF2222252.1` | `obtained` via `openalex-landing.citation-meta` | `preprint` | — | 15 | `readable` / `verified` |
| P0 | Copernicus — *Atmospheric Measurement Techniques* | `10.5194/amt-17-5619-2024` | `obtained` via `copernicus-direct` | `version-of-record` | — | 18 | `readable` / `verified` |
| P0 | Elsevier — *Atmospheric Environment* | `10.1016/j.atmosenv.2022.119234` | `obtained` via `ncbi-pmc-cloud` | `unknown` | `CC BY` | 9 | `readable` / `verified` |
| P0 | Springer Nature — *Climate Dynamics* | `10.1007/s00382-024-07441-6` | `obtained` via `springer-official-oa` | `version-of-record` | — | 13 | `readable` / `verified` |
| P0 | Springer Nature — *Communications Earth & Environment* | `10.1038/s43247-022-00563-x` | `obtained` via `crossref-link` | `version-of-record` | `https://creativecommons.org/licenses/by/4.0` | 11 | `readable` / `verified` |
| P0 | IOP — *Environmental Research Letters* | `10.1088/1748-9326/adc0b1` | `obtained` via `crossref-link` | `accepted-manuscript` | — | 9 | `readable` / `verified` |
| P0 | ACS — *ACS ES&T Air* | `10.1021/acsestair.5c00180` | `obtained` via `ncbi-pmc-cloud` | `unknown` | `CC BY-NC-ND` | 15 | `readable` / `verified` |
| P0 | AAAS — *Science* | `10.1126/science.1125261` | `obtained` via `openalex-landing.citation-meta` | `preprint` | — | 10 | `readable` / `verified` |
| P0 | Taylor & Francis — *Atmospheric and Oceanic Science Letters* | `10.1080/16742834.2017.1321951` | `obtained` via `direct-identifier` | `unknown` | — | 5 | `readable` / `verified` |
| P1 | MDPI — *Atmosphere* | `10.3390/atmos15091123` | `obtained` via `mdpi-official-pdf` | `unknown` | — | 26 | `readable` / `verified` |
| P1 | Frontiers — *Frontiers in Earth Science — Atmospheric Science* | `10.3389/feart.2022.931916` | `obtained` via `openalex-pdf` | `version-of-record` | `cc-by` | 14 | `readable` / `verified` |
| P1 | Meteorological Society of Japan / J-STAGE — *Journal of the Meteorological Society of Japan* | `10.2151/jmsj.2024-020` | `obtained` via `openalex-pdf` | `version-of-record` | `cc-by` | 42 | `readable` / `verified` |

All 14 rows also recorded `research_ready_verified=true` in the final report.
The AMS repository location had migrated from legacy Digital Commons URLs to
Iowa State's DSpace service; the final run followed the landing's HTTP
Signposting PDF item to the same-origin public DSpace REST bitstream, then
applied the normal PDF and DOI identity checks.

## Provenance review gaps

The 14/14 acquisition and QC result is intentionally separate from provenance
completeness:

- Eight rows have no machine-recorded license in the final report: Wiley/RMetS,
  AMS, Copernicus, Springer *Climate Dynamics*, IOP, AAAS, Taylor & Francis,
  and MDPI.
  Their licenses therefore remain a provenance-review item even where the
  corpus expectation or landing-page policy note indicates lawful access.
- Five rows have `artifact_version=unknown`: Wiley/RMetS, Elsevier, ACS,
  Taylor & Francis, and MDPI. The NCBI Open Data `is_manuscript=false` flag is
  not treated as proof of a version of record, and the bounded MDPI revision
  URL is a discovery heuristic rather than version evidence.
- The IOP Crossref link is recorded as `accepted-manuscript` because its
  `content-version` says `am`; the report does not copy a VOR-scoped license
  onto that file. `research_ready_verified=true` confirms artifact usability
  and identity, not version or license completeness.

## Lawful-access and safety boundary

- Only publisher, authoritative metadata, or authorized repository routes are
  in scope. Authentication controls, paywalls, robots restrictions, CAPTCHAs,
  and anti-bot controls are not bypassed.
- A blocked route must remain retryable or manual-required; it is not evidence
  that an article is unavailable and is not permission to use an untrusted
  mirror.
- Publisher and repository availability can change. This is a dated live smoke,
  not a guarantee that every route will remain reachable on a later run.
- PDF artifacts, hashes, temporary paths, raw article text, credentials, and
  private machine details are intentionally excluded from this public record.
- Artifact identity/readability QC is not locator-backed Evidence review.
  Human-reviewed Evidence is still required before supported, disputed, or
  verified Claim promotion. The run explicitly reports `promotion: none`.

## Reproduction

Run from the repository root and select a **new directory outside the
repository** for artifacts and the private raw report:

```bash
python3 tools/test_paper_acquisition.py \
  docs/benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json \
  --output-dir /path/outside/repository/rkf-atmospheric-journal-smoke \
  --external-qc-tools \
  --workers 2 \
  --artifact-timeout 35 \
  --metadata-timeout 12
```

Do not reuse an existing output directory. A rerun is a new time-bounded
observation and should not silently overwrite the `2026-07-16` outcomes in the
corpus.

For same-journal retry order and the boundary on article-specific alternate
identifiers, use the
[journal acquisition route playbook](../operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md).

## Historical comparison boundary

The earlier [79-citation atmospheric smoke](acquisition-issue-18-atmospheric-smoke.md)
is retained unchanged as a historical baseline. Its corpus, date, routes, and
success denominator differ from this curated 14-case journal-family smoke, so
the two percentages should not be compared as if they were repeated measures
of one unchanged benchmark.
