const DATA_URL = "./data/rkf-public-snapshot.json";

const $ = (id) => document.getElementById(id);

function setText(id, value) {
  const element = $(id);
  if (element) element.textContent = String(value);
}

function formatDate(value) {
  if (!value) return "尚無 hot signal";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("zh-Hant", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(date);
}

function sumCounts(counts, keys) {
  return keys.reduce((total, key) => total + Number(counts?.[key] || 0), 0);
}

function renderHotspots(items) {
  const root = $("hotspot-list");
  root.replaceChildren();
  if (!Array.isArray(items) || items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "目前視窗內沒有可公開的 topic-level demand aggregate。";
    root.append(empty);
    return;
  }
  const maximum = Math.max(...items.map((item) => Number(item.demand_count) || 0), 1);
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "hotspot-item";

    const label = document.createElement("div");
    label.className = "hotspot-name";
    const name = document.createElement("strong");
    name.textContent = item.name;
    const id = document.createElement("small");
    id.textContent = item.topic_id;
    label.append(name, id);

    const track = document.createElement("div");
    track.className = "track";
    const progress = document.createElement("span");
    progress.style.setProperty("--progress", `${Math.max(5, (Number(item.demand_count) / maximum) * 100)}%`);
    track.append(progress);

    const count = document.createElement("b");
    count.textContent = Number(item.demand_count) || 0;
    row.append(label, track, count);
    root.append(row);
  });
}

function renderRegisteredAreas(items) {
  const root = $("registered-area-list");
  root.replaceChildren();
  if (!Array.isArray(items) || items.length === 0) {
    const empty = document.createElement("p");
    empty.className = "registered-area-empty";
    empty.textContent = "尚未註冊可公開的研究領域。";
    root.append(empty);
    return;
  }
  items.forEach((item) => {
    const area = document.createElement("div");
    area.className = "registered-area-item";
    const name = document.createElement("strong");
    name.textContent = item.name;
    const id = document.createElement("small");
    id.textContent = item.topic_id;
    area.append(name, id);
    root.append(area);
  });
}

function renderBars(rootId, counts, labels) {
  const root = $(rootId);
  root.replaceChildren();
  const entries = labels
    .map(([key, label]) => [label, Number(counts?.[key] || 0)])
    .filter(([, count]) => count > 0);
  if (!entries.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "尚無可呈現的聚合資料。";
    root.append(empty);
    return;
  }
  const maximum = Math.max(...entries.map(([, count]) => count), 1);
  entries.forEach(([label, count]) => {
    const row = document.createElement("div");
    row.className = "bar-row";
    const text = document.createElement("span");
    text.textContent = label;
    const track = document.createElement("div");
    track.className = "track";
    const progress = document.createElement("span");
    progress.style.setProperty("--progress", `${Math.max(4, (count / maximum) * 100)}%`);
    track.append(progress);
    const value = document.createElement("b");
    value.textContent = count;
    row.append(text, track, value);
    root.append(row);
  });
}

function renderGates(gates) {
  const labels = {
    require_pdf_checkpoint: "PDF checkpoint",
    require_pdf_qc: "PDF quality control",
    require_claim_support: "Claim support",
    require_synthesis_review: "Synthesis review",
  };
  const root = $("gate-list");
  root.replaceChildren();
  Object.entries(labels).forEach(([key, label]) => {
    const item = document.createElement("div");
    item.className = "gate-item";
    const state = document.createElement("span");
    state.className = `gate-state ${gates?.[key] ? "on" : "off"}`;
    state.setAttribute("aria-label", gates?.[key] ? "enabled" : "disabled");
    const text = document.createElement("span");
    text.textContent = label;
    item.append(state, text);
    root.append(item);
  });
}

function settingState(value) {
  return value ? "configured" : "not configured";
}

function render(snapshot) {
  const publication = snapshot.publication || {};
  const status = publication.status || "pending-review";
  const statusElement = $("publication-status");
  statusElement.textContent = status === "synthetic-preview" ? "Synthetic preview" : status.replace("-", " ");
  statusElement.className = `status-pill ${status === "synthetic-preview" ? "synthetic" : ""}`;

  setText("freshness-label", `Snapshot ${formatDate(snapshot.generated_at)}`);
  setText("snapshot-label", `hash ${String(snapshot.snapshot_hash || "").slice(0, 12)}`);
  setText("window-label", `${snapshot.window_days} DAYS`);
  setText("demand-total", snapshot.demand.event_count);
  setText("linked-demand", snapshot.demand.topic_linked_event_count);
  setText("untriaged-demand", snapshot.demand.untriaged_event_count);
  setText("knowledge-count", snapshot.knowledge.page_count);
  setText("topic-count", `${snapshot.knowledge.registered_topic_count} registered topics`);
  setText("paper-count", snapshot.paper_pipeline.paper_page_count);
  setText("source-count", `${snapshot.paper_pipeline.source_count} governed sources`);
  setText("queue-count", snapshot.paper_pipeline.queue_count);
  setText("graph-count", snapshot.graph.node_count);
  setText("edge-count", `${snapshot.graph.edge_count} governed relationships`);

  renderHotspots(snapshot.research_hotspots);
  renderRegisteredAreas(snapshot.registered_research_areas);

  setText("candidate-count", snapshot.discovery.candidate_count);
  setText("run-count", snapshot.discovery.run_count);
  setText("accepted-count", snapshot.discovery.decision_counts.accepted);
  setText("duplicate-count", snapshot.discovery.decision_counts.duplicate);
  setText("ambiguous-count", snapshot.discovery.decision_counts.ambiguous);
  setText("other-decision-count", snapshot.discovery.decision_counts.other);

  setText("pipeline-discover", snapshot.discovery.candidate_count);
  setText("pipeline-register", snapshot.paper_pipeline.source_count);
  setText("pipeline-read", snapshot.paper_pipeline.paper_page_count);
  setText(
    "pipeline-support",
    sumCounts(snapshot.paper_pipeline.claim_readiness_counts, ["claim-ready", "synthesis-ready"]),
  );

  renderBars("reading-bars", snapshot.paper_pipeline.reading_state_counts, [
    ["metadata-only", "Metadata only"],
    ["abstract-read", "Abstract read"],
    ["skimmed", "Skimmed"],
    ["partial-fulltext", "Partial full text"],
    ["fulltext-available", "Full text available"],
    ["first-pass-pdf-qc", "First-pass PDF QC"],
    ["ocr-qc", "OCR quality control"],
    ["visual-qc", "Visual quality control"],
    ["fulltext-read", "Full text read"],
    ["full-read", "Full read"],
    ["human-reviewed", "Human reviewed"],
    ["synthesis-ready", "Synthesis ready"],
    ["reproduced", "Reproduced"],
    ["mixed", "Mixed maturity"],
    ["blocked", "Blocked"],
    ["other", "Other"],
  ]);
  renderBars("claim-bars", snapshot.paper_pipeline.claim_readiness_counts, [
    ["not-ready", "Not ready"],
    ["locator-needed", "Locator needed"],
    ["claim-ready", "Claim ready"],
    ["synthesis-ready", "Synthesis ready"],
    ["other", "Other"],
  ]);

  setText("schema-value", snapshot.framework.knowledge_schema);
  setText("cadence-value", snapshot.framework.review_cadence);
  setText("writer-value", snapshot.health.writer_role);
  const lintTotal = Object.values(snapshot.health.lint_counts).reduce((sum, value) => sum + Number(value || 0), 0);
  setText("lint-value", lintTotal);
  setText("doctor-blocker-value", snapshot.health.doctor_blocker_count);
  setText("doctor-warning-value", snapshot.health.doctor_warning_count);
  setText("wiki-storage-value", settingState(snapshot.framework.storage_handles.wiki_root_configured));
  setText("raw-storage-value", settingState(snapshot.framework.storage_handles.raw_root_configured));
  setText(
    "private-storage-value",
    settingState(snapshot.framework.storage_handles.private_evidence_configured),
  );
  const health = $("connection-health");
  health.textContent = snapshot.health.connection_status;
  health.className = `health-badge ${snapshot.health.connection_status}`;
  renderGates(snapshot.framework.gates);

  setText(
    "footer-snapshot",
    `${status} · ${String(snapshot.snapshot_hash).slice(0, 12)} · ${formatDate(snapshot.generated_at)}`,
  );
}

function showError() {
  const status = $("publication-status");
  status.textContent = "Snapshot unavailable";
  status.className = "status-pill error";
  setText("freshness-label", "無法載入公開快照");
  setText("snapshot-label", "No public data loaded");
  setText("footer-snapshot", "Snapshot unavailable · publication gate not satisfied");
  const root = $("hotspot-list");
  root.replaceChildren();
  const message = document.createElement("p");
  message.className = "empty-state";
  message.textContent = "Dashboard data 目前不可用。請確認公開 snapshot 已通過 exact-hash publication gate。";
  root.append(message);
  const areas = $("registered-area-list");
  areas.replaceChildren();
  const areaMessage = document.createElement("p");
  areaMessage.className = "registered-area-empty";
  areaMessage.textContent = "無法載入 registered research areas。";
  areas.append(areaMessage);
}

const embeddedReviewSnapshot = globalThis.__RKF_PRIVATE_REVIEW_SNAPSHOT__;
const snapshotRequest = embeddedReviewSnapshot
  ? Promise.resolve(embeddedReviewSnapshot)
  : fetch(DATA_URL, { cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error("snapshot unavailable");
      return response.json();
    });

snapshotRequest
  .then(render)
  .catch(showError);
