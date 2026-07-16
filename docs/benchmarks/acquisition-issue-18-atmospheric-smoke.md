# Issue #18 Atmospheric Paper Acquisition Smoke Test

Date: 2026-07-16

This test used the 79 citations supplied for issue #18. All network access used
public OA metadata, official publisher/repository routes, or the public
OpenAlex index. No institutional account, browser profile, cookie, fabricated
contact email, or paywall-bypass route was used. Downloaded PDFs and the raw
JSON report stayed in temporary private storage and are not part of the
repository.

## Result

- Initial citation-only run: 79 citations, 78 DOI identifiers, 40 artifacts
  obtained, 39 `manual-required`.
- One citation (Tewari et al. 2004) had no DOI/URL. The official UCAR/WRF PDF
  was located and retested through the URL-identifier route, raising the
  resolved result to **41 obtained and 38 remaining manual**.
- Successful routes: 26 Copernicus direct, 8 OpenAlex landing-page
  `citation_pdf_url`, 4 Crossref PDF links, 2 OpenAlex direct PDFs, and 1
  explicit official UCAR URL.
- Version provenance: 30 Version of Record, 10 preprints from the DOI corpus,
  plus one URL artifact whose version remains `unknown` pending human version
  classification.
- All 41 obtained artifacts passed PDF magic/EOF, checksum, text-layer, page,
  title/DOI identity, and locator-readiness checks. The 40-DOI corpus covered
  786 pages; the UCAR artifact added 6 pages. No invalid PDF, checksum mismatch,
  or identity mismatch was accepted.
- `Promotion: none`: these are readable artifacts, not Evidence and not
  human-verified Claims.

These version and identity counts preserve the then-current classifier and
verifier output as a historical baseline. The 79-citation corpus was not rerun
under the later stricter exact-DOI/title identity rules or conservative
Crossref/PMC/MDPI version rules, so its 30-VOR and 41-pass labels must not be
treated as current provenance revalidation.

OpenAlex added ten successful routes over the first implementation pass,
including public manuscript/preprint locations that anonymous Semantic Scholar
could not supply while rate-limited. The final run still did not enable
Unpaywall because no real contact email was provided.

## Remaining 38 not obtained in this environment

These are not declared globally unavailable. They require a configured OA
contact, publisher token, institutional resolver/adapter, ILL, or a
user-provided lawful artifact.

### AGU/Wiley — 16

Publisher/OpenAlex PDF routes returned `401/403`; anonymous OA indexes did not
produce another usable artifact. The `10.1002` and `10.1029` families now route
to optional Wiley TDM when a user token is supplied.

- `10.1029/91JD02472`
- `10.1029/2005JD006721`
- `10.1029/2002GL016633`
- `10.1029/2000JD000053`
- `10.1029/1999RG000078`
- `10.1029/2008JD009944`
- `10.1029/2001GL013252`
- `10.1029/2008JD011006`
- `10.1029/2009JD012353`
- `10.1029/1998JD200119`
- `10.1029/2018JD029878`
- `10.1029/2012JD018370`
- `10.1029/2024GL108444`
- `10.1029/2011JD016106`
- `10.1002/2013JD019860`
- `10.1002/2013JD021067`

Handling: configure a real `RKF_CONTACT_EMAIL` and rerun Unpaywall; if no OA
copy appears, use a personal Wiley TDM token or a serial machine-local
institutional adapter. Otherwise use resolver/ILL or provide a lawful PDF.

### American Meteorological Society — 12

Official AMS PDF/landing routes returned `403`. Five legacy DOIs containing
percent-encoded angle brackets were initially double-encoded; the resolver was
fixed and a focused rerun confirmed Crossref identity resolution, after which
the blocker was correctly reduced to publisher authorization.

- `10.1175/1520-0469(2002)059%3C0461:TAOTFT%3E2.0.CO;2`
- `10.1175/MWR3145.1`
- `10.1175/MWR3146.1`
- `10.1175/2009WAF2222241.1`
- `10.1175/1520-0442(1996)009%3C2058:AAPOTS%3E2.0.CO;2`
- `10.1175/2009WAF2222269.1`
- `10.1175/1520-0469(1989)046%3C1419:AGPFTS%3E2.0.CO;2`
- `10.1175/1520-0469(1978)035%3C2123:RPIEWC%3E2.0.CO;2`
- `10.1175/2008MWR2387.1`
- `10.1175/JAS-D-13-0305.1`
- `10.1175/1520-0469(1977)034%3C1149:TIOPOT%3E2.0.CO;2`
- `10.1175/2008MWR2415.1`

Handling: try Unpaywall with a real contact first, then a serial institutional
resolver/browser adapter or ILL. Keep the decoded canonical DOI internally and
correctly re-encode it only when building an HTTP URL.

### AAAS / Science — 4

- `10.1126/science.245.4923.1227`
- `10.1126/science.1092779`
- `10.1126/science.1180353`
- `10.1126/science.1089424`

Handling: repository landing pages exposed no usable PDF and the publisher
returned authorization failures. Retry Unpaywall; then use lawful
subscription/ILL or a user-provided manuscript.

### PNAS — 3

- `10.1073/pnas.1607171113`
- `10.1073/pnas.1316830110`
- `10.1073/pnas.0700618104`

Handling: PMCID/OpenAlex records were inspected, but the tested official PDF
routes were absent or authorization-gated. Do not treat a PMCID mapping as an
OA-PDF guarantee. Use Unpaywall, the official resolver, ILL, or a lawful local
copy. A different PNAS item in the corpus (`10.1073/pnas.2207329119`) did
succeed through a public route, so this is item-specific rather than a blanket
PNAS route failure.

### Elsevier — 3

- `10.1016/j.earscirev.2008.03.001`
- `10.1016/S0022-1694(00)00343-7`
- `10.1016/j.atmosenv.2005.04.027`

Handling: provide `ELSEVIER_TDM_KEY` through a secret provider, with an
optional personal institution token when authorized. The adapter intentionally
does not send `view=FULL`. If TDM is not authorized, use resolver/ILL. One other
Elsevier item in the corpus succeeded through a public preprint route.

## Improvement priorities from this test

1. Configure a real Unpaywall contact and retest the 38-item manual set.
2. Add a machine-local macOS Keychain/Linux Secret Service implementation for
   publisher tokens; keep environment secrets CI/test-only.
3. Complete an AMS authorized adapter and regression fixtures for the five
   legacy angle-bracket DOI forms.
4. Add provider-specific retry-after persistence across processes, not only
   the in-process 429 circuit breaker.
5. Add JATS/XML as an independently registrable artifact when an OA PDF is not
   available, while keeping the Read scope and version locator explicit.
6. Add a human review step for URL-only artifact version classification. The
   UCAR PDF passed identity/readability checks but its version is still
   `unknown`.
7. Build a maintained public atmospheric fixture corpus with one legal,
   deterministic route per P0 publisher; live publisher responses alone are
   too volatile for CI.
