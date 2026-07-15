# Ask Scaling Baseline

> Status: Current for the unreleased RKF v1.2 target
> Last verified: 2026-07-15

This zero-network baseline runs an `evidence-only` query against receipt-backed
canonical Evidence. It checks that the deterministic query projection reduces
repeated corpus reads without changing Ask ranking, trust labels, answer
boundaries, graph context, or result identity.

Run the default synthetic baseline:

```bash
python3 tools/benchmark_rkf_ask.py --check
```

CI uses a smaller fixture:

```bash
python3 tools/benchmark_rkf_ask.py --check --documents 40 --canonical 12 --limit 5
```

The acceptance contract is deliberately structural and relative:

- full scan, cold index, and warm index return the same stable result;
- every returned card is locator-backed canonical Evidence and remains
  claim-ready under the strict `evidence-only` policy;
- a warm index reads fewer corpus contents than a full scan, with zero content
  reads expected when fingerprints match;
- canonical full validation is exercised and stays within the oversampled
  candidate window;
- deleting the derived index and rebuilding it leaves canonical bytes and the
  stable Ask result unchanged;
- elapsed milliseconds are reported by stage for diagnosis, not used as a
  portable pass/fail threshold.

The stage timing fields do not overlap: `index_ms` measures deterministic
manifest/load/store overhead and excludes `scan_ms`, while `scan_ms` measures
corpus content reads and snapshot serialization. Their sum remains diagnostic
and may be lower than `total_ms` because total time also includes orchestration
overhead.

On 2026-07-15, the 40-document/12-Evidence fixture contained 92 indexed source
files. The full scan read 92 snapshot contents; the warm indexed Ask read 0
snapshot contents, validated 12 canonical candidates, and returned only
locator-backed, claim-ready Evidence with complete result/trust parity. After
the index was deleted, a rebuild preserved both canonical bytes and the stable
Ask result. Observed wall-clock timings vary by machine and filesystem and are
therefore not a release requirement.

The fixture is temporary and synthetic. It does not read user research data,
use a semantic provider, persist a retrieval run, or require network access.
