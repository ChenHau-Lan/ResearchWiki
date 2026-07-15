const DATA_URL = "./data/rkf-public-snapshot.json";
const $ = (id) => document.getElementById(id);
const setText = (id, value) => { const node = $(id); if (node) node.textContent = String(value); };

function render(snapshot) {
  if (snapshot.schema === "rkf-public-dashboard-v1") {
    setText("publication-status", "Private compatibility preview");
    setText("quality-message", "Legacy aggregate preview; v1 public site uses only the synthetic guided demo.");
    return;
  }
  setText("publication-status", snapshot.status === "published" ? "Public-safe demo" : "Preview");
  setText("locator-coverage", `${snapshot.metrics.locator_coverage_pct}%`);
  setText("verified-evidence", snapshot.metrics.human_verified_evidence);
  setText("claim-counts", `${snapshot.metrics.verified_claims} / ${snapshot.metrics.disputed_claims}`);
  setText("gap-count", snapshot.metrics.unresolved_gaps);
  setText("quality-message", snapshot.quality.message);
  setText("footer-snapshot", `${snapshot.status} · ${snapshot.generated_at} · synthetic/public-safe`);
}

function showError() {
  setText("publication-status", "Demo unavailable");
  setText("quality-message", "Public demo metadata unavailable; no research claim is shown.");
  setText("footer-snapshot", "Demo unavailable · publication gate not satisfied");
}

const embeddedReviewSnapshot = globalThis.__RKF_PRIVATE_REVIEW_SNAPSHOT__;
const snapshotRequest = embeddedReviewSnapshot
  ? Promise.resolve(embeddedReviewSnapshot)
  : fetch(DATA_URL, { cache: "no-store" }).then((response) => {
  if (!response.ok) throw new Error("snapshot unavailable");
  return response.json();
});
snapshotRequest.then(render).catch(showError);
