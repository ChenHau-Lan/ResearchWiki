# Issue #18 Identifier-only Adapter Smoke Test

Date: 2026-07-16

This focused smoke test exercised the dedicated ADS, OSF, EarthArXiv, ESS Open
Archive, NOAA, WMO, and IPCC resolution contracts. Network checks used only
public metadata and official provider/repository routes. Temporary PDFs and raw
reports stayed outside the repository. Artifact success remained
`Promotion: none`.

## Result

| Adapter input | Outcome in this environment | What was verified |
|---|---|---|
| `ads:2016PNAS..11311770A` | `manual-required` | The 19-character bibcode resolved to official ADS eprint, publisher, and abstract routes. The tested item exposed no anonymously downloadable artifact. |
| `osf:8sepv_v1` | `manual-required` | Public preprint metadata and the primary-file record resolved. The documented `links.download` route redirected to the generic WaterButler host, whose GET timed out during this run. |
| `eartharxiv:2777` | `obtained` | Current Janeway landing metadata exposed the official PDF; 65 pages, text layer, checksum, and locator readiness passed. Identity remained `unverified` because the numeric identifier alone supplied no title or DOI comparison token. |
| `essoar:10.1002/essoar.10512747.1` | `manual-required` | Crossref/OpenAlex identity resolution succeeded, but the official ESS Open Archive route returned `403` and the optional Wiley TDM token was not configured. |
| `noaa:55689` | `obtained` | The official NOAA IR landing and main-document route produced a 35-page readable report with checksum, text layer, and locator readiness. Identity remained `unverified` for the PID-only input. |
| `wmo:state-of-global-climate-2023` | `manual-required` | The official WMO publication page resolved, but the full-report link entered the WMO e-Library verification surface and no public PDF metadata route was available to the headless client. |
| `ipcc:ar6-wg1` and registered AR6 aliases | deterministic fixture only | Exact official IPCC full-report and landing URLs are registered and fixture-tested. The live full-volume download was intentionally skipped because complete volumes can exceed the default 64 MiB artifact limit. |

These results describe one bounded run, not global availability. A metadata
route resolving successfully does not mean that a downloadable artifact is
available, and a transient timeout or authorization response is not recorded
as permanent unavailability.

## Handling and improvement path

1. **ADS:** optionally supply `ADS_API_TOKEN` through `SecretProvider` to add
   title/DOI identity metadata, then reuse the DOI/OA route ladder. If ADS and
   publisher gateways remain closed, use a lawful local copy, resolver, or ILL.
2. **OSF:** retry the documented `links.download` route with provider backoff.
   Do not hard-code a regional WaterButler hostname because the public API did
   not expose a portable region field. Persistent failures become a
   user-provided-artifact handoff.
3. **EarthArXiv:** add identity metadata extraction from the Janeway landing or
   DataCite record so a numeric-ID acquisition can become title/DOI-verified,
   not only readable and locator-ready.
4. **ESS Open Archive:** require the full ESSOAr DOI. Configure a real
   Unpaywall contact and, when authorized, a Wiley TDM token; otherwise use the
   official resolver or ILL. Do not guess from a bare Authorea number.
5. **NOAA:** add an official report-number-to-NOAA-IR-PID catalogue before
   accepting free-form technical memorandum numbers. The exact PID route is
   already deterministic.
6. **WMO:** maintain a reviewed slug/record registry and allow a human browser
   handoff for the e-Library verification surface. Do not automate CAPTCHA or
   anti-bot bypass.
7. **IPCC:** register chapter and summary identifiers in addition to complete
   volumes. For a full volume, raise `max_artifact_bytes` only as an explicit
   per-run choice and retain checksum/QC validation.
