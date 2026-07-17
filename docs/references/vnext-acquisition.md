# vNext Scientific Artifact Acquisition

This is the implementation reference for the current **portable-core slice**
of GitHub issue #18. It extends the v1 `FullTextProvider` boundary without
adding a sixth user workflow: acquisition remains an internal operation of
**Add**, and `Promotion: none` always applies. It is not the completed issue
inventory or a complete set of institutional adapters.

## Implemented contracts

- `CanonicalIdentifierSet` accepts DOI, URL, arXiv, ADS bibcode, DataCite DOI,
  Handle, NASA NTRS, EarthArXiv/OSF/ESS Open Archive, NOAA/WMO/IPCC,
  repository, and report identifiers. Conflicting DOI values fail closed.
- `IdentifierAdapterRegistry` gives each identifier type one explicit owner and
  fails closed on duplicate registrations. Dedicated adapters cover ADS direct
  access plus optional API identity, OSF's public preprint/primary-file API,
  current EarthArXiv Janeway records and legacy OSF records, ESSOAr DOIs, NOAA
  IR PIDs, WMO publication/library records, and an exact IPCC report registry.
- `PortableScientificAcquisitionProvider` uses bounded, contact-identifying
  HTTP requests and a route ladder covering Crossref/DataCite identity,
  Unpaywall all-locations when a real contact email is configured, Semantic
  Scholar, OpenAlex, current NCBI ID conversion and PMC Open Data Cloud,
  generic repository/citation metadata, verified publisher routes, and
  optional Elsevier/Wiley TDM tokens supplied through a `SecretProvider`.
- Repository landing discovery accepts bounded citation metadata, explicit PDF
  anchors, and HTTP Signposting `rel=item; type=application/pdf`. For standard
  DSpace `/bitstreams/<uuid>/download` links, the same-origin public REST
  `/server/api/core/bitstreams/<uuid>/content` endpoint is tried first, then
  the advertised URL remains a fallback. Both still pass normal network,
  artifact-size, PDF, and identity gates.
- The public atmospheric corpus has 11 P0 representative cases: AGU/Wiley
  (`10.1029`), Wiley/RMetS (`10.1002`), AMS, Copernicus, Elsevier, Springer
  (`10.1007`), Nature (`10.1038`), IOP, ACS, AAAS, and Taylor & Francis. Its
  three P1 cases are MDPI, Frontiers, and J-STAGE. Prefix is only a final
  routing hint; exact adapters, metadata, landing host, and OA/repository
  locations are evaluated first.
- `ExternalPaperFetchProvider` maps upstream `paper_fetch.py --json` exit 4/5
  to `retryable`, validates the returned file again, and keeps institutional
  login/browser behavior outside RKF core.
- `SQLiteHoldingsEntitlementProvider` keeps `unknown`, `covered`, and
  `not-covered` distinct, including multiple and open-ended coverage ranges.
- Acquisition statuses are `obtained`, `manual-required`, `retryable`,
  `not-entitled`, `unavailable`, `blocked`, `identity-mismatch`,
  `invalid-artifact`, and `provider-error`. A metadata route can be `resolved`
  or `no-result` without claiming that an artifact was obtained.
- Every result carries an idempotent `acquisition_run_id`, public-safe route
  attempts, provider/version, retry class, artifact checksum, version, license,
  host-only source provenance, and project/activation lineage. Review loads
  the private, path-redacted acquisition timeline.
- Checksum-addressed PDFs are stored only under an explicit owner-only private
  boundary. Connector acquisition uses ignored private state; the smoke helper
  requires a non-symlinked output boundary outside the repository and refuses
  overwrite. Registration deduplicates identical bytes and never publishes
  article text.
- Default HTTP transport rejects private/reserved DNS answers and connected
  peers, including private IPv4 embedded in IPv4-mapped, 6to4, Teredo, and
  NAT64 forms. It rejects HTTPS downgrade, strips cross-origin `Referer`, keeps
  secret-bearing requests HTTPS/same-origin, and caps candidate/landing HTTP
  requests at 32 per acquisition.
- HTTP body reads now use a monotonic wall-clock deadline in addition to socket
  inactivity and byte limits. External full-text adapters cap stdout and
  stderr while the child is running; overflow kills the child and produces a
  typed result rather than buffering arbitrary diagnostics.
- `SQLiteRetryAfterStore` persists only route labels and expiry timestamps in
  owner-only state so independent processes honor provider 429 backoff. Review
  builds a route-health scorecard from path-redacted acquisition attempts.
- Allowlisted macOS Keychain, Linux Secret Service, and optional Windows
  Credential Manager/`pywin32` backends keep publisher tokens outside ordinary
  config and lineage. The environment backend remains intended for CI/tests.
- Landing, Crossref, and DataCite relationships create independent
  `rkf-related-artifact-v1` pointer records for datasets, software,
  supplements, HTML/XML, versions, corrections, and retractions. These records
  contain only host and identifier fingerprints, remain `pointer-only`, expose
  human provenance gaps in Review, and never promote Evidence or Claims.
- A six-column holdings export can be previewed and atomically imported with
  `python3 tools/import_rkf_holdings.py holdings.csv --database holdings.sqlite3`;
  add `--apply` only after review. Missing rows remain `unknown`.
- A supplied machine-local `BrowserSessionProvider` is called serially only
  under the explicit `institutional-external` policy. The external
  `paper_fetch.py` adapter implements this boundary and preserves profile-busy,
  watchdog, SSO/manual, and Ovid seat outcomes as typed handoffs.

### Current NCBI PMC Cloud route

For a DOI that the current NCBI ID converter maps to a PMCID, the portable
provider requests `versions=yes`, selects the entry marked `current` (or the
highest listed version when no current flag is present), and then requests
`https://pmc-oa-opendata.s3.amazonaws.com/metadata/<versioned-PMCID>.json`. It
accepts the PDF only when the returned DOI matches, `is_pmc_openaccess` is
true, and the record is explicitly not retracted. A
`s3://pmc-oa-opendata/...` `pdf_url` is then converted only to the corresponding anonymous
`https://pmc-oa-opendata.s3.amazonaws.com/...` object URL. The HTML/CAPTCHA
surface is not scraped or bypassed. `is_manuscript=true` supports an accepted-
manuscript classification; `false` is not by itself proof of a version of
record, so those files remain `artifact_version=unknown`. License code and the
selected versioned PMCID remain in provenance; a machine-recorded license code
still requires human interpretation before a reuse-permission claim.

## Identifier-only adapters

These inputs do not require the caller to find a PDF URL first:

| Source | Accepted example | Resolution boundary |
|---|---|---|
| NASA ADS | `ads:2016PNAS..11311770A` | Official ADS eprint/publisher gateways; an optional `ADS_API_TOKEN` supplied through `SecretProvider` adds DOI/title identity resolution. |
| OSF Preprints | `osf:8sepv` or `osf:8sepv_v1` | Public JSON API → primary-file API → official download. The unversioned form follows OSF's latest version; `_vN` pins a version. Withdrawn records stop at a manual landing. |
| EarthArXiv | `eartharxiv:2777`, `eartharxiv:2p9wg`, or an EarthArXiv DOI | Numeric IDs use the current Janeway landing; legacy alphanumeric IDs use the OSF API; DOI forms use the normal DOI ladder. |
| ESS Open Archive | `essoar:10.1002/essoar.10512747.1` | Exact ESSOAr DOI through Crossref/DataCite/OA and official DOI landing. A bare Authorea article number is not globally unique enough and returns `manual-required`. |
| NOAA IR | `noaa:55689` or a NOAA DOI | Exact NOAA IR PID uses the official landing and main-document template. A free-form technical-memorandum series number must first be converted to a NOAA IR PID or DOI. |
| WMO | `wmo:state-of-global-climate-2023` or a numeric e-Library record ID | Registered publication-series slug or exact e-Library record; other terms go to official WMO search and normally require review. |
| IPCC | `ipcc:ar6-wg1`, `ipcc:ar6-wg2`, `ipcc:ar6-wg3`, `ipcc:ar6-syr`, or an IPCC DOI | Exact official full-report/landing registry. Unknown aliases stop at official search with `manual-required`. |

Report downloads remain subject to the bounded artifact policy. Some complete
IPCC volumes exceed the default 64 MiB limit; raising that limit is an explicit
per-run choice, not an automatic bulk-download exception.

## PDF and artifact QC

The portable validator checks PDF magic bytes, minimum size, EOF/truncation,
encryption hints, page count, text-layer availability, exact complete-token
DOI or distinctive-title identity, and
locator readiness. Optional local `pdfinfo`/`pdftotext` improve QC without
becoming required runtime dependencies. QC returns `readable`, `partial`,
`ocr-required`, `corrupt`, or `identity-mismatch`; it does not create Evidence
or verify a Claim.

Artifact records distinguish Version of Record, accepted manuscript, preprint,
and unknown version. Dataset, code, and supplement links discovered in landing
metadata are recorded as provenance pointers only; large datasets are not
downloaded. A locator from one version must not be silently reused for another.

## Connector opt-in

Portable network acquisition is explicit and off by default:

```bash
export RKF_ENABLE_PORTABLE_ACQUISITION=1
# Replace the placeholder before running; Unpaywall requires a real contact.
export RKF_CONTACT_EMAIL="<your real email address>"
```

The connector then stores acquired files under ignored `.rkf_private`. The
contact email enables Unpaywall and identifies responsible individual use; do
not use a fabricated address. Publisher tokens and institutional credentials
belong in an OS secret store or a machine-local external adapter, not the
repository or ordinary shell environment.

The private smoke-corpus helper is:

```bash
python3 tools/test_paper_acquisition.py references.txt \
  --output-dir /private/or/temporary/output \
  --external-qc-tools \
  --workers 2
```

The output directory must be non-symlinked and outside the repository; its
report and artifact targets must not already exist and are never overwritten.
The helper accepts citation lines, the public atmospheric-journal corpus JSON,
or an earlier private `paper-fetch-results.json`, so a previous run can be
selected again with `--indices` and written to a different output directory.
It allows at most four workers, uses provider-level rate-limit backoff and a
shared 32-request candidate/landing budget per acquisition, and writes no PDF
or article text into the repository. Reference lines may contain
explicit HTTP(S) URLs or the typed identifiers shown above.

The report counts an item as downloaded only when a checksum-addressed PDF with
validated magic bytes is present in the private store. The stricter
`research_ready_verified_count` also requires readable text, verified identity,
pages, and locator readiness. It separately records provider status and
selected-route counts. Every report retains `Promotion: none`.

## Legal and safety boundary

- No Sci-Hub, DRM bypass, SSO/CAPTCHA bypass, credential sharing, or automatic
  bulk institutional download.
- SSO/CAPTCHA and other access-control surfaces are detected and stopped as a
  typed manual handoff. Publisher/browser routes remain serial, optional, and
  externally configured.
- `401`/`403`, missing holdings, retryable failures, and unavailable artifacts
  remain distinct.
- Missing authorization returns a resolver/ILL/user-provided-artifact handoff.
- Artifact success and QC never raise Evidence verification or Claim status.
- Route metadata, license strings, and access expectations are recorded for
  review; legal eligibility, reuse terms, and publisher-policy interpretation
  still require a human check.

## Bounded atmospheric-journal observation

The public corpus lists the 11 P0 and 3 P1 cases separately in
[`../benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json`](../benchmarks/acquisition-issue-18-atmospheric-journal-corpus.json).
In one live run on 2026-07-16, all 14 results were `obtained` and all 14 met the
helper's research-ready PDF checks. Nine selected route labels were observed:
Copernicus direct, Crossref link, direct identifier, MDPI official PDF, current
NCBI PMC Cloud, NOAA IR citation metadata, OpenAlex citation metadata,
OpenAlex PDF, and Springer official OA. Every result retained
`Promotion: none`, and raw reports/PDFs stayed in a repository-external private
temporary boundary.

This is bounded observational evidence for those exact representatives at
that time. It does not establish global availability, guarantee future
publisher behavior, or complete native institutional adapters. The public-safe
case-by-case result is in
[`../benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md`](../benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md).

## Definition-of-Done items still open

The issue #18 inventory is intentionally larger than this portable-core slice.
Do not close the issue yet. The following remain explicit gaps:

- Complete free-form report-number catalogues for non-DOI ESSOAr items and
  arbitrary NOAA/WMO/IPCC series names. Exact ADS/OSF/EarthArXiv/ESSOAr DOI,
  NOAA PID, WMO record/registered slug, and registered IPCC IDs now resolve;
  ambiguous aliases deliberately return a manual official-search handoff.
- Actual download and format-specific validation of publisher HTML, JATS/XML,
  supplements, figures, and tables. These are now independently registered as
  public-safe pointer records, and Crossref/DataCite version/correction/
  retraction relationships are linked, but pointer registration is not proof
  of artifact identity or a completed download.
- Full data/code availability statement extraction, model/instrument/campaign/
  satellite/reanalysis version extraction, and Review gaps based on those
  domain fields.
- Institution-specific endpoint configuration, holdings exports, and Ovid seat
  release/cooldown behavior remain machine-local inputs to the now-complete
  serial external adapter boundary. RKF cannot ship or infer them, and it will
  not copy one institution's setup into the public repository.
- Per-provider terms/policy review dates and legal eligibility conclusions
  require human review. Route-health, cross-process retry state, and
  deterministic P0 route/identity fixtures are implemented, but operational
  success is not a terms-of-use conclusion.
- Human version classification for URL-only artifacts and a complete
  supersedes decision for the five version-unknown live artifacts. Structured
  `is-version-of`/`corrects`/`retracts` edges are now registered when Crossref
  or DataCite supplies them; unverified relationships stay pending.

The curated live atmospheric-journal result and provenance gaps are in
[`../benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md`](../benchmarks/acquisition-issue-18-atmospheric-journal-live-smoke.md).
Reusable journal-family route ladders, including the boundary between reusable
publisher logic and article-specific repository identifiers, are maintained in
[`../operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md`](../operations/atmospheric-journal-acquisition-route-playbook.zh-TW.md).
The user-requested public-safe conversation and implementation closeout is in
[`../operations/2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md`](../operations/2026-07-16-issue-18-atmospheric-journal-closeout.zh-TW.md).
The separate 79-citation result remains a historical baseline in
[`../benchmarks/acquisition-issue-18-atmospheric-smoke.md`](../benchmarks/acquisition-issue-18-atmospheric-smoke.md).
The focused ADS/OSF/EarthArXiv/ESSOAr/NOAA/WMO/IPCC result is in
[`../benchmarks/acquisition-issue-18-identifier-adapter-smoke.md`](../benchmarks/acquisition-issue-18-identifier-adapter-smoke.md).
