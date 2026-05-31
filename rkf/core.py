"""Core runtime helpers for the Research Knowledge Framework.

RKF keeps research memory active and governed: source records can become early
paper drafts, reading maturity records show how well the user and agents
understand a source, and evidence boundaries still control stable claims,
trusted synthesis, citation, and publication.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from hashlib import sha1
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
TOPIC_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SOURCE_STATUSES = {
    "new",
    "metadata_ok",
    "candidate_found",
    "paper_draft",
    "needs_user_pdf",
    "fulltext_available",
    "reading_in_progress",
    "reading_mature",
    "pdf_checkpoint_required",
    "pdf_downloaded",
    "pdf_qc_needed",
    "pdf_qc_done",
    "wiki_done",
    "abstract_only",
    "blocked",
}

KNOWLEDGE_TYPES = {
    "paper",
    "question",
    "concept",
    "claim",
    "topic",
    "synthesis",
    "overview",
    "project-synthesis",
    "meeting",
    "seminar",
}

PDF_QC_DONE = {"codex_qc_done", "human_qc_done"}
PAPER_READING_STATUSES = {
    "metadata-only",
    "abstract-read",
    "skimmed",
    "partial-fulltext",
    "fulltext-available",
    "first-pass-pdf-qc",
    "ocr-qc",
    "visual-qc",
    "fulltext-read",
    "full-read",
    "human-reviewed",
    "synthesis-ready",
    "reproduced",
    "mixed",
    "blocked",
}
FULLTEXT_STATUSES = {
    "unknown",
    "needs-user-pdf",
    "user-pdf-provided",
    "publisher-html",
    "publisher-pdf",
    "open-access-pdf",
    "partial-only",
    "fulltext-read",
    "unavailable",
    "blocked",
    "not-applicable",
}
HUMAN_FEEDBACK_LEVELS = {"none", "skimmed", "discussed", "annotated", "trusted"}
UNDERSTANDING_CONFIDENCES = {"low", "medium", "high", "mixed"}
CLAIM_READINESS = {"not-ready", "locator-needed", "claim-ready", "synthesis-ready"}
SYNTHESIS_MATURITY = {"draft", "single-source", "multi-source", "human-reviewed", "publication-ready"}
SOURCE_COVERAGE = {"unknown", "partial", "representative", "systematic"}
LOCAL_PATH_PATTERNS = [
    re.compile("/" + r"Users/(?!\[\^)[^/\s]+"),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
]
HOT_RECORDS_START = "<!-- RKF-HOT-RECORDS:START -->"
HOT_RECORDS_END = "<!-- RKF-HOT-RECORDS:END -->"
HOT_GENERATED_START = "<!-- RKF-HOT-GENERATED:START -->"
HOT_GENERATED_END = "<!-- RKF-HOT-GENERATED:END -->"
HOT_EVENT_SCHEMA = "rkf-hot-query-event-v1"
HOT_QUERY_MAX_CHARS = 500
HOT_NOTES_MAX_CHARS = 1000
HOT_DEFAULT_WINDOW_DAYS = 30
HOT_RECORD_RE = re.compile(
    r"^-\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\|\s*origin=(?P<origin>[^|]+)\|\s*topic=(?P<topic>[^|]+)\|\s*intent=(?P<intent>[^|]+)\|\s*query=\"(?P<query>[^\"]*)\"(?:\s*\|\s*leads=\"(?P<leads>[^\"]*)\")?(?:\s*\|\s*notes=\"(?P<notes>[^\"]*)\")?\s*$"
)


def today() -> str:
    return date.today().isoformat()


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str, max_len: int = 80) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return (value[:max_len].strip("_") or "item")


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;")
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi:\s*", "", value, flags=re.IGNORECASE)
    return value.lower()


def extract_doi(value: str) -> str:
    match = DOI_RE.search(value)
    return normalize_doi(match.group(0)) if match else ""


def source_id_from_value(kind: str, value: str) -> str:
    doi = extract_doi(value)
    if doi:
        return "doi_" + slugify(doi.replace("/", "_"))
    return f"{kind}_{slugify(value, 64)}"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 4 :].lstrip("\n")
    meta: dict[str, Any] = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if ":" not in line or line.startswith(" "):
            index += 1
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value == "":
            items: list[str] = []
            lookahead = index + 1
            while lookahead < len(lines) and lines[lookahead].startswith("  - "):
                items.append(lines[lookahead][4:].strip())
                lookahead += 1
            meta[key.strip()] = items
            index = lookahead
            continue
        if value == "[]":
            parsed: Any = []
        elif value in {"true", "false"}:
            parsed = value == "true"
        else:
            parsed = value.strip('"')
        meta[key.strip()] = parsed
        index += 1
    return meta, body


def frontmatter(meta: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def first_heading(body: str, fallback: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback
    return fallback


def first_summary_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        if stripped.startswith("!") or stripped.startswith("|"):
            continue
        return stripped[:180]
    return ""


def knowledge_page_records(ws: "Workspace") -> list[tuple[Path, dict[str, Any], str]]:
    records: list[tuple[Path, dict[str, Any], str]] = []
    if not ws.paths.knowledge.exists():
        return records
    for path in sorted(ws.paths.knowledge.rglob("*.md")):
        meta, body = parse_frontmatter(read_text(path))
        if meta:
            records.append((path, meta, body))
    return records


def infer_evidence_tier(meta: dict[str, Any], body: str = "") -> str:
    explicit = str(meta.get("evidence_tier", "")).strip()
    if explicit:
        return explicit
    page_type = str(meta.get("type", ""))
    boundary = str(meta.get("evidence_boundary", "")).lower()
    reading = str(meta.get("reading_status", "")).lower()
    claim_readiness = str(meta.get("claim_readiness", "")).lower()
    human_feedback = str(meta.get("human_feedback_level", "")).lower()
    text = body.lower()
    if "review-blocker" in boundary:
        return "review-blocker"
    if page_type == "paper":
        if claim_readiness in {"claim-ready", "synthesis-ready"}:
            return "claim-ready"
        if human_feedback in {"annotated", "trusted"} and reading in {"fulltext-read", "full-read", "human-reviewed"}:
            return "human-matured"
        if reading in {"fulltext-read", "full-read", "human-reviewed"} and meta.get("evidence_ids"):
            return "locator-backed"
        if reading in {"first-pass-pdf-qc", "ocr-qc", "visual-qc"} and meta.get("evidence_ids"):
            return "pdf-qc-stub"
        if reading in {"metadata-only", "abstract-read"} or "metadata" in text or "abstract" in text:
            return "metadata-only"
        return "reading-draft"
    if "metadata" in boundary or "abstract" in boundary:
        return "mixed"
    if "pdf-evidence" in boundary or meta.get("evidence_ids"):
        return "locator-backed"
    if "candidate" in boundary:
        return "candidate"
    return "review-blocker"


def set_frontmatter(path: Path, meta: dict[str, Any], body: str) -> None:
    write_text(path, frontmatter(meta) + body)


def relative_workspace_path(ws: "Workspace", path: Path) -> str:
    for base in (ws.paths.wiki_root, ws.root):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return str(path)


def append_log(ws: "Workspace", action: str, message: str) -> None:
    ws.paths.log.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"- {timestamp} `{action}` {message.rstrip()}\n"
    if not ws.paths.log.exists():
        ws.paths.log.write_text("# Wiki Log\n\n", encoding="utf-8")
    with ws.paths.log.open("a", encoding="utf-8") as handle:
        handle.write(line)


def load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if tomllib is None:
        data: dict[str, Any] = {}
        section: dict[str, Any] | None = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = data.setdefault(line.strip("[]"), {})
                continue
            if "=" in line and section is not None:
                key, value = line.split("=", 1)
                section[key.strip()] = value.strip().strip('"')
        return data
    with path.open("rb") as handle:
        return tomllib.load(handle)


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    wiki_root: Path
    index: Path
    log: Path
    hot_md: Path
    state: Path
    sources: Path
    evidence_index: Path
    gates: Path
    reading: Path
    search_runs: Path
    knowledge: Path
    governance: Path
    graph: Path
    prompts: Path
    private_evidence: Path


class Workspace:
    """Path and persistence boundary for an RKF workspace."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(os.environ.get("RKF_ROOT", root or Path(__file__).resolve().parents[1])).resolve()
        self.config = self._load_config()
        self.paths = self._paths()

    def _load_config(self) -> dict[str, Any]:
        for name in ("rkf.workspace.toml", "workspace.toml"):
            config = load_toml(self.root / name)
            if config:
                return config
        return {}

    def _config_path(self, section: str, key: str, fallback: Path) -> Path:
        configured = self._configured_path(section, key)
        return configured or fallback

    def _configured_path(self, section: str, key: str) -> Path | None:
        section_value = self.config.get(section, {}) if isinstance(self.config, dict) else {}
        value = section_value.get(key) if isinstance(section_value, dict) else None
        if isinstance(value, str) and value.strip():
            return Path(os.path.expandvars(os.path.expanduser(value))).resolve()
        return None

    def _paths(self) -> WorkspacePaths:
        wiki_root = self._configured_path("storage", "wiki_root") or self.root
        state = wiki_root / "state"
        private_evidence = self._config_path("storage", "private_evidence_root", self.root / ".rkf_private" / "evidence")
        return WorkspacePaths(
            root=self.root,
            wiki_root=wiki_root,
            index=wiki_root / "index.md",
            log=wiki_root / "log.md",
            hot_md=wiki_root / "hot.md",
            state=state,
            sources=state / "sources",
            evidence_index=state / "evidence",
            gates=state / "gates",
            reading=state / "reading",
            search_runs=state / "search_runs",
            knowledge=wiki_root / "knowledge",
            governance=wiki_root / "governance",
            graph=wiki_root / "graph",
            prompts=self.root / "prompts",
            private_evidence=private_evidence,
        )

    def ensure_base(self) -> None:
        for path in (
            self.paths.sources,
            self.paths.evidence_index,
            self.paths.gates,
            self.paths.reading,
            self.paths.search_runs,
            self.paths.knowledge,
            self.paths.governance,
            self.paths.graph,
            self.paths.prompts,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def source_path(self, source_id: str) -> Path:
        return self.paths.sources / f"{source_id}.json"

    def evidence_path(self, evidence_id: str) -> Path:
        return self.paths.evidence_index / f"{evidence_id}.json"

    def reading_ledger_path(self, source_id: str) -> Path:
        return self.paths.reading / f"{source_id}.json"

    def load_source(self, source_id: str) -> dict[str, Any]:
        path = self.source_path(source_id)
        if not path.exists():
            raise SystemExit(f"source record not found: {source_id}")
        return read_json(path)

    def save_source(self, record: dict[str, Any]) -> None:
        record["updated"] = today()
        write_json(self.source_path(record["source_id"]), record)

    def save_evidence(self, artifact: dict[str, Any]) -> None:
        artifact["updated"] = today()
        write_json(self.evidence_path(artifact["evidence_id"]), artifact)

    def topic_registry_path(self) -> Path:
        return self.paths.governance / "topic_registry.json"

    def load_topics(self) -> list[dict[str, Any]]:
        path = self.topic_registry_path()
        if not path.exists():
            return []
        topics = read_json(path).get("topics", [])
        return topics if isinstance(topics, list) else []

    def save_topics(self, topics: list[dict[str, Any]]) -> None:
        write_json(
            self.topic_registry_path(),
            {
                "schema": "rkf-topic-registry-v1",
                "updated": today(),
                "topics": sorted(topics, key=lambda item: item["topic_id"]),
            },
        )


def create_source(ws: Workspace, *, kind: str, value: str, title: str = "", topic_id: str = "", note: str = "") -> dict[str, Any]:
    ws.ensure_base()
    source_id = source_id_from_value(kind, value)
    if ws.source_path(source_id).exists():
        record = read_json(ws.source_path(source_id))
    else:
        record = {
            "schema": "rkf-source-record-v1",
            "source_id": source_id,
            "kind": kind,
            "value": value,
            "normalized_doi": extract_doi(value),
            "title": title,
            "status": "new",
            "reading_state": "metadata-only",
            "fulltext_status": "needs-user-pdf",
            "topic_ids": [],
            "gates": [],
            "evidence_ids": [],
            "notes": [],
            "created": today(),
            "updated": today(),
        }
    if title:
        record["title"] = title
    if topic_id and topic_id not in record["topic_ids"]:
        record["topic_ids"].append(topic_id)
    if note:
        record["notes"].append({"date": today(), "note": note})
    ws.save_source(record)
    append_log(ws, "capture", f"{record['source_id']} kind={kind} status={record['status']}")
    return record


def set_source_status(ws: Workspace, record: dict[str, Any], status: str) -> dict[str, Any]:
    if status not in SOURCE_STATUSES:
        raise SystemExit(f"invalid source status: {status}")
    record["status"] = status
    ws.save_source(record)
    return record


def default_reading_ledger_ref(source_id: str) -> str:
    return f"state/reading/{source_id}.json"


def load_reading_ledger(ws: Workspace, source_id: str) -> dict[str, Any]:
    path = ws.reading_ledger_path(source_id)
    if not path.exists():
        return {
            "schema": "rkf-reading-ledger-v1",
            "source_id": source_id,
            "knowledge_path": "",
            "events": [],
            "created": today(),
            "updated": today(),
        }
    return read_json(path)


def append_reading_event(
    ws: Workspace,
    *,
    source_id: str,
    event_type: str,
    summary: str,
    actor: str = "codex",
    knowledge_path: str = "",
    public_safe: bool = True,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assert_public_safe_hot_value(summary, field="reading_event", max_chars=HOT_NOTES_MAX_CHARS)
    ledger = load_reading_ledger(ws, source_id)
    if knowledge_path:
        ledger["knowledge_path"] = knowledge_path
    ledger.setdefault("events", []).append(
        {
            "created": datetime.now().isoformat(timespec="seconds"),
            "type": event_type,
            "actor": actor,
            "summary": summary.strip(),
            "public_safe": public_safe,
            "details": details or {},
        }
    )
    ledger["updated"] = today()
    write_json(ws.reading_ledger_path(source_id), ledger)
    append_log(ws, "reading-event", f"{source_id} {event_type} {summary[:80]}")
    return ledger


def find_paper_page_for_source(ws: Workspace, source_id: str) -> Path | None:
    for path, meta, _ in knowledge_page_records(ws):
        if meta.get("type") == "paper" and meta.get("source_id") == source_id:
            return path
    return None


def maturity_defaults_for_paper(record: dict[str, Any], artifact: dict[str, Any] | None) -> dict[str, str]:
    if artifact and artifact.get("status") == "pdf_qc_done":
        reading_state = "fulltext-read"
        fulltext_status = "fulltext-read"
        claim_readiness = "claim-ready" if artifact.get("locators") else "locator-needed"
        understanding_confidence = "medium"
    elif artifact:
        reading_state = "partial-fulltext"
        fulltext_status = "user-pdf-provided"
        claim_readiness = "locator-needed"
        understanding_confidence = "low"
    else:
        status = str(record.get("status", ""))
        reading_state = "abstract-read" if status == "abstract_only" else "metadata-only"
        fulltext_status = "needs-user-pdf"
        claim_readiness = "not-ready"
        understanding_confidence = "low"
    return {
        "reading_state": reading_state,
        "fulltext_status": fulltext_status,
        "human_feedback_level": "none",
        "understanding_confidence": understanding_confidence,
        "claim_readiness": claim_readiness,
        "last_reading_interaction": today(),
        "reading_ledger": default_reading_ledger_ref(str(record["source_id"])),
    }


def update_paper_maturity(
    ws: Workspace,
    source_id: str,
    *,
    reading_state: str = "",
    fulltext_status: str = "",
    human_feedback_level: str = "",
    understanding_confidence: str = "",
    claim_readiness: str = "",
    note: str = "",
    actor: str = "codex",
) -> Path:
    path = find_paper_page_for_source(ws, source_id)
    if path is None:
        raise SystemExit(f"paper page not found for source: {source_id}")
    meta, body = parse_frontmatter(read_text(path))
    if reading_state:
        meta["reading_state"] = reading_state
        meta["reading_status"] = reading_state
    if fulltext_status:
        meta["fulltext_status"] = fulltext_status
    if human_feedback_level:
        meta["human_feedback_level"] = human_feedback_level
    if understanding_confidence:
        meta["understanding_confidence"] = understanding_confidence
    if claim_readiness:
        meta["claim_readiness"] = claim_readiness
    meta["last_reading_interaction"] = today()
    meta["updated"] = today()
    set_frontmatter(path, meta, body)
    if note:
        append_reading_event(
            ws,
            source_id=source_id,
            event_type="human-feedback" if actor == "human" else "reading-update",
            actor=actor,
            summary=note,
            knowledge_path=relative_workspace_path(ws, path),
            details={
                "reading_state": meta.get("reading_state", ""),
                "fulltext_status": meta.get("fulltext_status", ""),
                "human_feedback_level": meta.get("human_feedback_level", ""),
                "understanding_confidence": meta.get("understanding_confidence", ""),
                "claim_readiness": meta.get("claim_readiness", ""),
            },
        )
    return path


def write_acquisition_checkpoint(ws: Workspace, record: dict[str, Any], *, route: str, screenshot: str = "") -> Path:
    gate_id = f"pdf_acquisition_{record['source_id']}"
    path = ws.paths.gates / "pdf_acquisition" / f"{record['source_id']}.md"
    write_text(
        path,
        "# PDF Acquisition Gate\n\n"
        f"- Gate ID: {gate_id}\n"
        f"- Source ID: {record['source_id']}\n"
        f"- Candidate route: {route}\n"
        f"- Screenshot: {screenshot}\n"
        "- Decision: pending\n\n"
        "## Human Checkpoints\n\n"
        "- Confirm the route is legal and authorized for your access.\n"
        "- Confirm the PDF or publisher artifact matches the intended source identity.\n"
        "- Confirm this is usable article evidence, not only metadata or an abstract page.\n"
        "- Run acquisition again with explicit approval only after these checks.\n",
    )
    record.setdefault("gates", []).append(
        {
            "gate_id": gate_id,
            "type": "pdf_acquisition",
            "status": "pending",
            "path": relative_workspace_path(ws, path),
        }
    )
    set_source_status(ws, record, "pdf_checkpoint_required")
    append_log(ws, "acquire-checkpoint", f"{record['source_id']} route={route}")
    return path


def approved_pdf_acquisition(ws: Workspace, record: dict[str, Any], pdf_path: Path) -> dict[str, Any]:
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    pdf_root = ws.paths.private_evidence / "doi_pdf"
    pdf_root.mkdir(parents=True, exist_ok=True)
    dest = pdf_root / f"{record['source_id']}.pdf"
    shutil.copy2(pdf_path, dest)
    evidence_id = f"pdf_{record['source_id']}"
    artifact = {
        "schema": "rkf-evidence-artifact-v1",
        "evidence_id": evidence_id,
        "source_id": record["source_id"],
        "artifact_type": "pdf",
        "status": "pdf_downloaded",
        "qc_status": "pending",
        "storage_path": f"private_evidence/doi_pdf/{record['source_id']}.pdf",
        "public_safe_pointer": f"private_evidence/doi_pdf/{record['source_id']}.pdf",
        "locators": [],
        "created": today(),
        "updated": today(),
    }
    ws.save_evidence(artifact)
    if evidence_id not in record.setdefault("evidence_ids", []):
        record["evidence_ids"].append(evidence_id)
    record["fulltext_status"] = "user-pdf-provided"
    record["reading_state"] = "partial-fulltext"
    set_source_status(ws, record, "pdf_downloaded")
    paper_path = find_paper_page_for_source(ws, str(record["source_id"]))
    if paper_path is not None:
        update_paper_maturity(
            ws,
            str(record["source_id"]),
            reading_state="partial-fulltext",
            fulltext_status="user-pdf-provided",
            claim_readiness="locator-needed",
            note="User-provided PDF stored; reading maturity updated through the normal full-text path.",
        )
    append_log(ws, "acquire", f"{record['source_id']} stored {evidence_id}")
    return artifact


def pdf_artifact(ws: Workspace, record: dict[str, Any]) -> dict[str, Any] | None:
    for evidence_id in record.get("evidence_ids", []):
        path = ws.evidence_path(evidence_id)
        if not path.exists():
            continue
        artifact = read_json(path)
        if artifact.get("artifact_type") == "pdf":
            return artifact
    return None


def verify_pdf(ws: Workspace, record: dict[str, Any], *, locator: str = "", note: str = "", qc_status: str = "codex_qc_done") -> dict[str, Any]:
    if qc_status not in PDF_QC_DONE:
        raise SystemExit(f"invalid PDF review status: {qc_status}")
    artifact = pdf_artifact(ws, record)
    if artifact is None:
        raise SystemExit("refusing PDF verification: no approved PDF evidence")
    artifact["status"] = "pdf_qc_done"
    artifact["qc_status"] = qc_status
    artifact.setdefault("locators", [])
    if locator:
        artifact["locators"].append(locator)
    if note:
        artifact.setdefault("qc_notes", []).append({"date": today(), "note": note})
    ws.save_evidence(artifact)
    record["fulltext_status"] = "fulltext-read"
    record["reading_state"] = "fulltext-read"
    set_source_status(ws, record, "pdf_qc_done")
    paper_path = find_paper_page_for_source(ws, str(record["source_id"]))
    if paper_path is not None:
        update_paper_maturity(
            ws,
            str(record["source_id"]),
            reading_state="fulltext-read",
            fulltext_status="fulltext-read",
            claim_readiness="claim-ready" if locator else "locator-needed",
            understanding_confidence="medium",
            note=note or locator or "Full text identity and readability were checked.",
        )
    append_log(ws, "verify-pdf", f"{record['source_id']} qc_status={qc_status}")
    return artifact


def qced_pdf_artifact(ws: Workspace, record: dict[str, Any]) -> dict[str, Any] | None:
    artifact = pdf_artifact(ws, record)
    if artifact and artifact.get("qc_status") in PDF_QC_DONE and artifact.get("status") == "pdf_qc_done":
        return artifact
    return None


def create_paper_note(ws: Workspace, record: dict[str, Any], *, slug: str = "") -> Path:
    artifact = qced_pdf_artifact(ws, record)
    if artifact is None:
        artifact = pdf_artifact(ws, record)
    title = record.get("title") or record["source_id"].replace("_", " ").title()
    page_slug = slugify(slug or record["source_id"])
    dest = ws.paths.knowledge / "papers" / f"{page_slug}.md"
    maturity = maturity_defaults_for_paper(record, artifact)
    evidence_ids = [artifact["evidence_id"]] if artifact else []
    boundary = "pdf-evidence" if artifact and artifact.get("status") == "pdf_qc_done" else "review-blocker"
    evidence_tier = infer_evidence_tier(
        {
            "type": "paper",
            "reading_status": maturity["reading_state"],
            "claim_readiness": maturity["claim_readiness"],
            "human_feedback_level": maturity["human_feedback_level"],
            "evidence_ids": evidence_ids,
            "evidence_boundary": boundary,
        }
    )
    meta = {
        "type": "paper",
        "status": "draft",
        "source_id": record["source_id"],
        "source_status": "peer-reviewed",
        "reading_status": maturity["reading_state"],
        "reading_state": maturity["reading_state"],
        "fulltext_status": maturity["fulltext_status"],
        "human_feedback_level": maturity["human_feedback_level"],
        "understanding_confidence": maturity["understanding_confidence"],
        "claim_readiness": maturity["claim_readiness"],
        "last_reading_interaction": maturity["last_reading_interaction"],
        "reading_ledger": maturity["reading_ledger"],
        "review_stage": "ai-extracted",
        "evidence_boundary": boundary,
        "evidence_tier": evidence_tier,
        "evidence_ids": evidence_ids,
        "topics": record.get("topic_ids", []),
        "created": today(),
        "updated": today(),
    }
    locators = artifact.get("locators", []) if artifact else []
    locator_lines = "\n".join(f"- {item}" for item in locators) if locators else "- TBD while reading PDF"
    evidence_line = f"- PDF Evidence: {artifact['evidence_id']}" if artifact else "- PDF Evidence: not provided yet"
    evidence_status = "Checked PDF" if artifact and artifact.get("status") == "pdf_qc_done" else "Reading draft; evidence boundary not promoted"
    body = (
        f"# {title}\n\n"
        "## Source Identity\n\n"
        f"- Source ID: {record['source_id']}\n"
        f"- DOI: {record.get('normalized_doi', '')}\n"
        f"{evidence_line}\n"
        f"- Evidence status: {evidence_status}\n\n"
        "## Reading Maturity\n\n"
        f"- Reading state: {maturity['reading_state']}\n"
        f"- Full text status: {maturity['fulltext_status']}\n"
        f"- Human feedback level: {maturity['human_feedback_level']}\n"
        f"- Understanding confidence: {maturity['understanding_confidence']}\n"
        f"- Claim readiness: {maturity['claim_readiness']}\n"
        f"- Reading ledger: {maturity['reading_ledger']}\n\n"
        "## Locators\n\n"
        f"{locator_lines}\n\n"
        "## Reading Notes\n\n"
        "- Research question:\n"
        "- Method:\n"
        "- Key findings:\n"
        "- Limitations:\n\n"
        "## Questions And Feedback\n\n"
        "- User questions:\n"
        "- Human feedback:\n"
        "- Open blockers:\n\n"
        "## Claims To Promote\n\n"
        "- Claim:\n"
        "  - Locator or blocker:\n"
        "  - Caveat:\n\n"
        "## Graph Links\n\n"
        "- Topics:\n"
        "- Concepts:\n"
        "- Questions:\n"
    )
    write_text(dest, frontmatter(meta) + body)
    set_source_status(ws, record, "wiki_done" if artifact and artifact.get("status") == "pdf_qc_done" else "paper_draft")
    append_reading_event(
        ws,
        source_id=str(record["source_id"]),
        event_type="paper-draft-created",
        summary=f"Paper draft created with reading_state={maturity['reading_state']} and fulltext_status={maturity['fulltext_status']}.",
        knowledge_path=relative_workspace_path(ws, dest),
    )
    append_log(ws, "distill-paper", f"{record['source_id']} -> {relative_workspace_path(ws, dest)}")
    return dest


def add_topic(
    ws: Workspace,
    *,
    topic_id: str,
    name: str,
    scope: str,
    aliases: list[str],
    include: list[str],
    exclude: list[str],
    search: list[str],
    cadence: str,
) -> dict[str, Any]:
    if not TOPIC_ID_RE.match(topic_id):
        raise SystemExit(f"invalid topic id: {topic_id}")
    topics = [topic for topic in ws.load_topics() if topic.get("topic_id") != topic_id]
    topic = {
        "topic_id": topic_id,
        "name": name,
        "aliases": aliases,
        "scope": scope,
        "include": include,
        "exclude": exclude,
        "default_search_strings": search,
        "canonical_pages": [],
        "review_cadence": cadence,
        "updated": today(),
    }
    topics.append(topic)
    ws.save_topics(topics)
    topic_page = ws.paths.knowledge / "topics" / f"{topic_id}.md"
    write_text(
        topic_page,
        frontmatter(
            {
                "type": "topic",
                "status": "draft",
                "topic_id": topic_id,
                "review_stage": "human-checked",
                "topics": [topic_id],
                "created": today(),
                "updated": today(),
                "sources": [],
            }
        )
        + f"# {name}\n\n## Scope\n\n{scope or 'TBD'}\n\n## Search Defaults\n\n"
        + "\n".join(f"- {item}" for item in search)
        + "\n\n## Include\n\n"
        + "\n".join(f"- {item}" for item in include)
        + "\n\n## Exclude\n\n"
        + "\n".join(f"- {item}" for item in exclude)
        + "\n",
    )
    append_log(ws, "topic-add", f"{topic_id} {name}")
    return topic


def normalize_hot_query(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = value.strip("\"'")
    return value


def assert_public_safe_hot_value(value: str, *, field: str, max_chars: int) -> None:
    if len(value) > max_chars:
        raise SystemExit(f"hot query {field} is too long; refusing possible pasted transcript or article text")
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(value):
            raise SystemExit(f"hot query {field} contains a local/private path")


def hot_event_id(*, created: str, origin: str, intent: str, normalized_query: str, topic_ids: list[str]) -> str:
    payload = json.dumps(
        {
            "created": created,
            "origin": origin,
            "intent": intent,
            "normalized_query": normalized_query,
            "topic_ids": sorted(topic_ids),
        },
        sort_keys=True,
    )
    return "hot_" + sha1(payload.encode("utf-8")).hexdigest()[:16]


def _topic_match_text(topic: dict[str, Any]) -> str:
    chunks: list[str] = [
        str(topic.get("topic_id", "")).replace("-", " "),
        str(topic.get("name", "")),
        str(topic.get("scope", "")),
    ]
    for key in ("aliases", "include", "default_search_strings"):
        chunks.extend(str(item) for item in topic.get(key, []))
    text = " ".join(chunks).lower().replace('"', " ")
    return re.sub(r"[^a-z0-9]+", " ", text)


def infer_hot_topics(ws: Workspace, query: str, explicit_topic_id: str = "") -> tuple[list[str], str]:
    explicit_topic_id = explicit_topic_id.strip()
    if explicit_topic_id and explicit_topic_id.lower() not in {"none", "unknown"}:
        return [explicit_topic_id], "explicit"
    normalized = normalize_hot_query(query)
    query_words = {word for word in re.findall(r"[a-z0-9]+", normalized) if len(word) >= 3}
    scored: list[tuple[int, str]] = []
    for topic in ws.load_topics():
        topic_id = str(topic.get("topic_id", ""))
        if not topic_id:
            continue
        score = 0
        candidates = [topic_id.replace("-", " "), str(topic.get("name", ""))]
        candidates.extend(str(item) for item in topic.get("aliases", []))
        for phrase in candidates:
            phrase_key = normalize_hot_query(phrase.replace("-", " "))
            if phrase_key and phrase_key in normalized:
                score += 4
        topic_words = set(_topic_match_text(topic).split())
        overlap = query_words & topic_words
        score += min(len(overlap), 4)
        if score >= 2:
            scored.append((score, topic_id))
    if not scored:
        return [], "unknown"
    scored.sort(key=lambda item: (-item[0], item[1]))
    best_score = scored[0][0]
    return [topic_id for score, topic_id in scored if score == best_score], "matched"


def record_hot_query(
    ws: Workspace,
    *,
    query: str,
    topic_id: str = "",
    origin: str = "local",
    intent: str = "query",
    paper_leads: list[str] | None = None,
    notes: str = "",
    created: str = "",
) -> dict[str, Any]:
    ws.ensure_base()
    assert_public_safe_hot_value(query, field="query", max_chars=HOT_QUERY_MAX_CHARS)
    assert_public_safe_hot_value(notes, field="notes", max_chars=HOT_NOTES_MAX_CHARS)
    paper_leads = paper_leads or []
    for lead in paper_leads:
        assert_public_safe_hot_value(lead, field="paper_leads", max_chars=HOT_QUERY_MAX_CHARS)
    normalized_query = normalize_hot_query(query)
    if not normalized_query:
        raise SystemExit("hot query cannot be empty")
    created = created or datetime.now().isoformat(timespec="seconds")
    topic_ids, topic_fit = infer_hot_topics(ws, query, topic_id)
    event = {
        "schema": HOT_EVENT_SCHEMA,
        "event_id": hot_event_id(
            created=created,
            origin=origin,
            intent=intent,
            normalized_query=normalized_query,
            topic_ids=topic_ids,
        ),
        "created": created,
        "origin": origin,
        "intent": intent,
        "query": query.strip(),
        "normalized_query": normalized_query,
        "topic_ids": topic_ids,
        "topic_fit": topic_fit,
        "paper_leads": paper_leads,
        "notes": notes.strip(),
    }
    append_hot_record(ws, event)
    append_log(ws, "hot-record", f"{intent} topics={','.join(topic_ids) or 'unknown'} query={normalized_query[:80]}")
    return event


def _hot_escape(value: str) -> str:
    return value.replace('"', "'").replace("\n", " ").strip()


def _hot_record_line(event: dict[str, Any]) -> str:
    created = str(event.get("created", today()))[:10]
    origin = _hot_escape(str(event.get("origin", "local")))
    intent = _hot_escape(str(event.get("intent", "query")))
    topic_ids = [str(item) for item in event.get("topic_ids", []) if str(item).strip()]
    topic = ",".join(topic_ids) if topic_ids else "unknown"
    query = _hot_escape(str(event.get("query", "")))
    line = f'- {created} | origin={origin} | topic={topic} | intent={intent} | query="{query}"'
    leads = [_hot_escape(str(item)) for item in event.get("paper_leads", []) if str(item).strip()]
    notes = _hot_escape(str(event.get("notes", "")))
    if leads:
        line += f' | leads="{"; ".join(leads)}"'
    if notes:
        line += f' | notes="{notes}"'
    return line


def _extract_block(text: str, start_marker: str, end_marker: str) -> str:
    if start_marker not in text or end_marker not in text:
        return ""
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return text[start:end].strip("\n")


def _parse_hot_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("<!--"):
        return None
    match = HOT_RECORD_RE.match(stripped)
    if not match:
        return None
    topic_raw = match.group("topic").strip()
    topic_ids = [] if topic_raw.lower() in {"", "none", "unknown"} else [item.strip() for item in topic_raw.split(",") if item.strip()]
    query = match.group("query").strip()
    normalized_query = normalize_hot_query(query)
    leads = [item.strip() for item in (match.group("leads") or "").split(";") if item.strip()]
    notes = (match.group("notes") or "").strip()
    created = match.group("date")
    return {
        "schema": HOT_EVENT_SCHEMA,
        "event_id": hot_event_id(
            created=created,
            origin=match.group("origin").strip(),
            intent=match.group("intent").strip(),
            normalized_query=normalized_query,
            topic_ids=topic_ids,
        ),
        "created": created,
        "origin": match.group("origin").strip(),
        "intent": match.group("intent").strip(),
        "query": query,
        "normalized_query": normalized_query,
        "topic_ids": topic_ids,
        "topic_fit": "explicit" if topic_ids else "unknown",
        "paper_leads": leads,
        "notes": notes,
    }


def _hot_records_text(ws: Workspace) -> str:
    if not ws.paths.hot_md.exists():
        return ""
    return _extract_block(read_text(ws.paths.hot_md), HOT_RECORDS_START, HOT_RECORDS_END)


def load_hot_events(ws: Workspace) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in _hot_records_text(ws).splitlines():
        event = _parse_hot_line(line)
        if event is not None:
            events.append(event)
    return events


def append_hot_record(ws: Workspace, event: dict[str, Any]) -> None:
    if not ws.paths.hot_md.exists():
        write_text(ws.paths.hot_md, render_hot_markdown(ws))
    text = read_text(ws.paths.hot_md)
    record_line = _hot_record_line(event)
    if HOT_RECORDS_START not in text or HOT_RECORDS_END not in text:
        text = render_hot_markdown(ws)
    start = text.index(HOT_RECORDS_START) + len(HOT_RECORDS_START)
    end = text.index(HOT_RECORDS_END, start)
    existing = text[start:end].strip("\n")
    replacement = "\n" + (existing + "\n" if existing else "") + record_line + "\n"
    write_text(ws.paths.hot_md, text[:start] + replacement + text[end:])


def _event_date(event: dict[str, Any]) -> date | None:
    created = str(event.get("created", ""))
    try:
        return datetime.fromisoformat(created).date()
    except ValueError:
        try:
            return date.fromisoformat(created[:10])
        except ValueError:
            return None


def recent_hot_events(ws: Workspace, *, days: int = HOT_DEFAULT_WINDOW_DAYS) -> list[dict[str, Any]]:
    cutoff = date.today() - timedelta(days=days - 1)
    recent: list[dict[str, Any]] = []
    for event in load_hot_events(ws):
        event_day = _event_date(event)
        if event_day is None or event_day >= cutoff:
            recent.append(event)
    return recent


def _format_counter(counter: Counter[str], *, empty: str) -> list[str]:
    if not counter:
        return [f"- {empty}"]
    return [f"- {name}: {count}" for name, count in counter.most_common()]


def render_hot_markdown(ws: Workspace, *, days: int = HOT_DEFAULT_WINDOW_DAYS) -> str:
    events = recent_hot_events(ws, days=days)
    records = _hot_records_text(ws)
    topic_names = {str(topic.get("topic_id", "")): str(topic.get("name", "")) for topic in ws.load_topics()}
    topic_counts: Counter[str] = Counter()
    question_counts: dict[str, Counter[str]] = defaultdict(Counter)
    paper_leads: Counter[str] = Counter()
    unknown: Counter[str] = Counter()
    for event in events:
        query = str(event.get("normalized_query") or event.get("query", "")).strip()
        if not query:
            continue
        topic_ids = [str(item) for item in event.get("topic_ids", []) if str(item).strip()]
        if not topic_ids:
            unknown[query] += 1
            continue
        for topic_id in topic_ids:
            topic_counts[topic_id] += 1
            question_counts[topic_id][query] += 1
        for lead in event.get("paper_leads", []):
            if str(lead).strip():
                paper_leads[str(lead).strip()] += 1
    lines = [
        "# Hot Research Questions",
        "",
        f"Generated: {today()}",
        f"Window: last {days} days",
        "",
        "This dashboard records public-safe research demand signals. It is not evidence, not a knowledge page, and not a stable claim source.",
        "",
        HOT_GENERATED_START,
        "",
        "## Top Topics",
        "",
    ]
    if topic_counts:
        for topic_id, count in topic_counts.most_common():
            label = topic_names.get(topic_id, topic_id)
            lines.append(f"- {topic_id} ({label}): {count}")
    else:
        lines.append("- No topic-linked hot queries in this window.")
    lines.extend(["", "## Frequent Questions By Topic", ""])
    if question_counts:
        for topic_id in sorted(question_counts):
            label = topic_names.get(topic_id, topic_id)
            lines.append(f"### {topic_id} - {label}")
            lines.extend(_format_counter(question_counts[topic_id], empty="No questions recorded."))
            lines.append("")
    else:
        lines.append("- No frequent questions recorded.")
        lines.append("")
    lines.extend(["## Paper/Search Leads", ""])
    lines.extend(_format_counter(paper_leads, empty="No paper/search leads recorded."))
    lines.extend(["", "## Unknown-Topic Triage", ""])
    lines.extend(_format_counter(unknown, empty="No unknown-topic queries in this window."))
    lines.extend(["", HOT_GENERATED_END, "", "## Query Records", ""])
    lines.append("Records below are the retrieval source for this file. Keep them short and public-safe.")
    lines.append('Format: `- YYYY-MM-DD | origin=local | topic=topic-id | intent=query | query="short question"`')
    lines.append("")
    lines.append(HOT_RECORDS_START)
    if records:
        lines.append(records.rstrip())
    lines.append(HOT_RECORDS_END)
    lines.append("")
    return "\n".join(lines)


def refresh_hot_markdown(ws: Workspace, *, days: int = HOT_DEFAULT_WINDOW_DAYS) -> Path:
    ws.ensure_base()
    write_text(ws.paths.hot_md, render_hot_markdown(ws, days=days))
    append_log(ws, "hot-refresh", f"generated {relative_workspace_path(ws, ws.paths.hot_md)}")
    return ws.paths.hot_md


def generate_wiki_index(ws: Workspace) -> Path:
    ws.ensure_base()
    lines = [
        "# Wiki Index",
        "",
        f"Generated: {today()}",
        "",
        "This index is the compact entrypoint for LLM retrieval. It lists public-safe knowledge objects, review state, topics, and evidence tier.",
        "",
        "## Knowledge Pages",
        "",
    ]
    page_count = 0
    if ws.paths.knowledge.exists():
        for path in sorted(ws.paths.knowledge.rglob("*.md")):
            meta, body = parse_frontmatter(read_text(path))
            title = first_heading(body, path.stem.replace("_", " ").replace("-", " ").title())
            rel = relative_workspace_path(ws, path)
            topics = ", ".join(str(item) for item in meta.get("topics", [])) if meta else ""
            page_type = meta.get("type", "unknown") if meta else "unknown"
            status = meta.get("status", "unknown") if meta else "unknown"
            review_stage = meta.get("review_stage", "unknown") if meta else "unknown"
            boundary = meta.get("evidence_boundary", "") if meta else ""
            tier = infer_evidence_tier(meta, body) if meta else "review-blocker"
            maturity_bits: list[str] = []
            if page_type == "paper":
                maturity_bits.append(f"reading={meta.get('reading_state', meta.get('reading_status', 'unknown'))}")
                maturity_bits.append(f"fulltext={meta.get('fulltext_status', 'unknown')}")
                maturity_bits.append(f"human={meta.get('human_feedback_level', 'unknown')}")
                maturity_bits.append(f"claim={meta.get('claim_readiness', 'unknown')}")
            if page_type == "synthesis":
                maturity_bits.append(f"maturity={meta.get('synthesis_maturity', 'unknown')}")
                maturity_bits.append(f"coverage={meta.get('source_coverage', 'unknown')}")
                maturity_bits.append(f"claim={meta.get('claim_readiness', 'unknown')}")
            maturity = f"; {'; '.join(maturity_bits)}" if maturity_bits else ""
            summary = first_summary_line(body)
            suffix = f" - {summary}" if summary else ""
            lines.append(
                f"- [{title}]({rel}): type={page_type}; status={status}; review={review_stage}; "
                f"evidence={boundary or 'unspecified'}; tier={tier}; topics={topics or 'none'}{maturity}{suffix}"
            )
            page_count += 1
    if page_count == 0:
        lines.append("- No knowledge pages found.")
    lines.extend(["", "## Topic Registry", ""])
    topics = ws.load_topics()
    if topics:
        for topic in topics:
            aliases = ", ".join(topic.get("aliases", []))
            lines.append(
                f"- {topic.get('topic_id', '')}: {topic.get('name', '')}; "
                f"cadence={topic.get('review_cadence', '')}; aliases={aliases or 'none'}"
            )
    else:
        lines.append("- No governed topics found.")
    write_text(ws.paths.index, "\n".join(lines).rstrip() + "\n")
    append_log(ws, "index", f"generated {relative_workspace_path(ws, ws.paths.index)} with {page_count} knowledge pages")
    return ws.paths.index


def _source_records(ws: Workspace) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not ws.paths.sources.exists():
        return records
    for path in sorted(ws.paths.sources.glob("*.json")):
        record = read_json(path)
        source_id = str(record.get("source_id", ""))
        if source_id:
            records[source_id] = record
    return records


def _evidence_records(ws: Workspace) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not ws.paths.evidence_index.exists():
        return records
    for path in sorted(ws.paths.evidence_index.glob("*.json")):
        record = read_json(path)
        evidence_id = str(record.get("evidence_id", ""))
        if evidence_id:
            records[evidence_id] = record
    return records


def lint_topics(ws: Workspace) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_aliases: dict[str, str] = {}
    for topic in ws.load_topics():
        topic_id = str(topic.get("topic_id", ""))
        if not TOPIC_ID_RE.match(topic_id):
            errors.append(f"invalid topic_id: {topic_id}")
        if topic_id in seen_ids:
            errors.append(f"duplicate topic_id: {topic_id}")
        seen_ids.add(topic_id)
        if not topic.get("scope"):
            errors.append(f"{topic_id}: missing scope")
        if not topic.get("default_search_strings"):
            errors.append(f"{topic_id}: missing default_search_strings")
        for alias in topic.get("aliases", []):
            key = str(alias).strip().lower()
            if key and key in seen_aliases and seen_aliases[key] != topic_id:
                errors.append(f"alias {alias!r} used by {seen_aliases[key]} and {topic_id}")
            if key:
                seen_aliases[key] = topic_id
    return errors


def lint_graph_links(ws: Workspace) -> list[str]:
    errors: list[str] = []
    sources = _source_records(ws)
    evidence = _evidence_records(ws)
    topics = {str(topic.get("topic_id", "")) for topic in ws.load_topics() if str(topic.get("topic_id", "")).strip()}
    check_topics = bool(topics)

    for source_id, record in sources.items():
        for evidence_id in record.get("evidence_ids", []):
            if str(evidence_id) not in evidence:
                errors.append(f"{source_id}: missing evidence artifact {evidence_id}")
        if check_topics:
            for topic_id in record.get("topic_ids", []):
                if str(topic_id) not in topics:
                    errors.append(f"{source_id}: unknown topic {topic_id}")

    for evidence_id, artifact in evidence.items():
        source_id = str(artifact.get("source_id", ""))
        if source_id and source_id not in sources:
            errors.append(f"{evidence_id}: missing source record {source_id}")

    for path, meta, _ in knowledge_page_records(ws):
        rel = relative_workspace_path(ws, path)
        source_id = str(meta.get("source_id", ""))
        if source_id and source_id not in sources:
            errors.append(f"{rel}: missing source record {source_id}")
        for evidence_id in meta.get("evidence_ids", []):
            if str(evidence_id) not in evidence:
                errors.append(f"{rel}: missing evidence artifact {evidence_id}")
        if check_topics:
            for topic_id in meta.get("topics", []):
                if str(topic_id) not in topics:
                    errors.append(f"{rel}: unknown topic {topic_id}")
    return errors


def lint_ars_handoff(ws: Workspace) -> list[str]:
    errors: list[str] = []
    proposal_boundaries = {"ars-proposal", "review-blocker"}
    for path, meta, body in knowledge_page_records(ws):
        rel = relative_workspace_path(ws, path)
        page_type = str(meta.get("type", ""))
        boundary = str(meta.get("evidence_boundary", ""))
        status = str(meta.get("status", ""))
        evidence_tier = str(meta.get("evidence_tier", ""))
        has_ars_marker = "source_from_ars" in meta or "source_from_ars:" in body

        if page_type == "paper" and boundary == "ars-proposal":
            errors.append(f"{rel}: paper pages cannot use ARS output as evidence")
        if has_ars_marker and boundary not in proposal_boundaries:
            errors.append(f"{rel}: ARS-derived material must use ars-proposal or review-blocker boundary")
        if boundary == "ars-proposal" and status == "reviewed":
            errors.append(f"{rel}: ARS proposal cannot be reviewed without evidence promotion")
        if boundary == "ars-proposal" and evidence_tier and evidence_tier != "review-blocker":
            errors.append(f"{rel}: ARS proposal must not claim evidence tier {evidence_tier}")
    return errors


def lint_knowledge_pages(ws: Workspace) -> list[str]:
    errors: list[str] = []
    if not ws.paths.knowledge.exists():
        return errors
    for path in ws.paths.knowledge.rglob("*.md"):
        text = read_text(path)
        meta, _ = parse_frontmatter(text)
        rel = relative_workspace_path(ws, path)
        if not meta:
            errors.append(f"{rel}: missing YAML frontmatter")
            continue
        page_type = str(meta.get("type", ""))
        if page_type not in KNOWLEDGE_TYPES:
            errors.append(f"{rel}: invalid type {page_type!r}")
        for key in ("status", "review_stage", "topics", "created", "updated"):
            if key not in meta:
                errors.append(f"{rel}: missing {key}")
        if page_type == "paper":
            reading_status = str(meta.get("reading_status", ""))
            if reading_status not in PAPER_READING_STATUSES:
                errors.append(f"{rel}: invalid paper reading_status {reading_status!r}")
            if reading_status not in {"full-read", "fulltext-read", "human-reviewed"} and meta.get("status") not in {"draft", "review", "needs-verification"}:
                errors.append(f"{rel}: non-full-read paper pages must stay draft or review")
            maturity_keys = {
                "reading_state",
                "fulltext_status",
                "human_feedback_level",
                "understanding_confidence",
                "claim_readiness",
                "reading_ledger",
            }
            legacy_paper = not any(meta.get(key) for key in maturity_keys)
            for key, allowed in (
                ("reading_state", PAPER_READING_STATUSES),
                ("fulltext_status", FULLTEXT_STATUSES),
                ("human_feedback_level", HUMAN_FEEDBACK_LEVELS),
                ("understanding_confidence", UNDERSTANDING_CONFIDENCES),
                ("claim_readiness", CLAIM_READINESS),
            ):
                value = str(meta.get(key, ""))
                if value and value not in allowed:
                    errors.append(f"{rel}: invalid {key} {value!r}")
                if not value and not legacy_paper:
                    errors.append(f"{rel}: missing {key}")
            if not meta.get("reading_ledger") and not legacy_paper:
                errors.append(f"{rel}: paper page missing reading_ledger")
            claim_readiness = str(meta.get("claim_readiness", ""))
            if claim_readiness in {"claim-ready", "synthesis-ready"}:
                has_support = bool(meta.get("evidence_ids")) or str(meta.get("human_feedback_level", "")) in {"annotated", "trusted"}
                if not has_support:
                    errors.append(f"{rel}: claim-ready paper needs evidence id or strong human feedback")
        if page_type == "synthesis":
            for key, allowed in (
                ("synthesis_maturity", SYNTHESIS_MATURITY),
                ("source_coverage", SOURCE_COVERAGE),
                ("human_feedback_level", HUMAN_FEEDBACK_LEVELS),
                ("claim_readiness", CLAIM_READINESS),
            ):
                value = str(meta.get(key, ""))
                if value and value not in allowed:
                    errors.append(f"{rel}: invalid {key} {value!r}")
    return errors


def _resolve_knowledge_path(ws: Workspace, target: str) -> Path | None:
    raw = Path(target).expanduser()
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend(
            [
                ws.paths.wiki_root / raw,
                ws.root / raw,
                ws.paths.knowledge / raw,
            ]
        )
        if raw.suffix != ".md":
            candidates.extend(
                [
                    ws.paths.wiki_root / f"{target}.md",
                    ws.root / f"{target}.md",
                    ws.paths.knowledge / f"{target}.md",
                ]
            )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def _target_words(title: str, body: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9][a-z0-9-]{3,}", f"{title} {first_summary_line(body)}".lower()))
    return {word.strip("-") for word in words if len(word.strip("-")) >= 4}


def propose_propagation(ws: Workspace, target: str, *, write: bool = False) -> dict[str, Any]:
    ws.ensure_base()
    sources = _source_records(ws)
    evidence = _evidence_records(ws)
    target_id = target
    target_kind = "unknown"
    target_title = target
    target_topics: set[str] = set()
    target_evidence: set[str] = set()
    target_source = ""
    target_terms: set[str] = set()
    target_boundary = ""
    target_tier = ""
    target_path: Path | None = None

    if target in sources:
        record = sources[target]
        target_kind = "source"
        target_id = target
        target_title = str(record.get("title") or record.get("value") or target)
        target_topics = {str(item) for item in record.get("topic_ids", []) if str(item).strip()}
        target_evidence = {str(item) for item in record.get("evidence_ids", []) if str(item).strip()}
        target_source = target
    else:
        target_path = _resolve_knowledge_path(ws, target)
        if target_path is None:
            raise SystemExit(f"propagation target not found: {target}")
        meta, body = parse_frontmatter(read_text(target_path))
        if not meta:
            raise SystemExit(f"propagation target has no frontmatter: {target}")
        target_kind = str(meta.get("type", "knowledge"))
        target_id = relative_workspace_path(ws, target_path)
        target_title = first_heading(body, target_path.stem.replace("_", " ").replace("-", " ").title())
        target_topics = {str(item) for item in meta.get("topics", []) if str(item).strip()}
        target_evidence = {str(item) for item in meta.get("evidence_ids", []) if str(item).strip()}
        target_source = str(meta.get("source_id", ""))
        target_terms = _target_words(target_title, body)
        target_boundary = str(meta.get("evidence_boundary", ""))
        target_tier = infer_evidence_tier(meta, body)

    impacts: list[dict[str, Any]] = []
    for path, meta, body in knowledge_page_records(ws):
        if target_path is not None and path.resolve() == target_path:
            continue
        reasons: list[str] = []
        page_topics = {str(item) for item in meta.get("topics", []) if str(item).strip()}
        shared_topics = sorted(target_topics & page_topics)
        if shared_topics:
            reasons.append("shared topics: " + ", ".join(shared_topics))
        page_evidence = {str(item) for item in meta.get("evidence_ids", []) if str(item).strip()}
        shared_evidence = sorted(target_evidence & page_evidence)
        if shared_evidence:
            reasons.append("shared evidence: " + ", ".join(shared_evidence))
        page_source = str(meta.get("source_id", ""))
        if target_source and page_source == target_source:
            reasons.append(f"same source: {target_source}")
        page_terms = _target_words(first_heading(body, path.stem), body)
        shared_terms = sorted(target_terms & page_terms)
        if len(shared_terms) >= 2:
            reasons.append("term overlap: " + ", ".join(shared_terms[:5]))
        if reasons:
            impacts.append(
                {
                    "path": relative_workspace_path(ws, path),
                    "type": meta.get("type", "knowledge"),
                    "reasons": reasons,
                    "recommendation": "review-before-update",
                }
            )

    blockers: list[str] = []
    if target_kind != "source" and target_boundary in {"ars-proposal", "review-blocker"}:
        blockers.append(f"target boundary is {target_boundary}; do not promote without evidence review")
    if target_kind != "source" and target_tier == "review-blocker":
        blockers.append("target evidence tier is review-blocker")
    if target_kind == "source" and target_source in sources and not sources[target_source].get("evidence_ids"):
        blockers.append("source has no evidence artifacts yet")

    proposal = {
        "schema": "rkf-propagation-proposal-v1",
        "created": today(),
        "target": target_id,
        "target_type": target_kind,
        "affected_pages": impacts,
        "blockers": blockers,
        "rule": "proposal-only; do not rewrite knowledge pages automatically",
    }
    if write:
        proposal_path = ws.paths.gates / "propagation" / f"{slugify(target_id, 48)}_{now_stamp()}.md"
        lines = [
            "# Propagation Review Proposal",
            "",
            f"- Target: {target_id}",
            f"- Target type: {target_kind}",
            f"- Created: {today()}",
            "- Rule: proposal-only; do not rewrite knowledge pages automatically",
            "",
            "## Affected Pages",
            "",
        ]
        if impacts:
            for item in impacts:
                lines.append(f"- {item['path']} ({item['type']}): {'; '.join(item['reasons'])}")
        else:
            lines.append("- No affected pages found.")
        lines.extend(["", "## Review Blockers", ""])
        if blockers:
            lines.extend(f"- {item}" for item in blockers)
        else:
            lines.append("- No deterministic blockers found.")
        write_text(proposal_path, "\n".join(lines) + "\n")
        proposal["proposal_path"] = relative_workspace_path(ws, proposal_path)
        append_log(ws, "propagate", f"{target_id} affected={len(impacts)} proposal={proposal['proposal_path']}")
    return proposal


def _paper_page_index(ws: Workspace) -> dict[str, tuple[Path, dict[str, Any], str]]:
    index: dict[str, tuple[Path, dict[str, Any], str]] = {}
    for path, meta, body in knowledge_page_records(ws):
        if meta.get("type") == "paper" and meta.get("source_id"):
            index[str(meta["source_id"])] = (path, meta, body)
    return index


def paper_queue(ws: Workspace) -> list[dict[str, Any]]:
    sources = _source_records(ws)
    papers = _paper_page_index(ws)
    hot_events = load_hot_events(ws) if ws.paths.hot_md.exists() else []
    hot_leads = Counter()
    for event in hot_events:
        for lead in event.get("paper_leads", []):
            lead_text = str(lead)
            hot_leads[lead_text] += 1
            doi = extract_doi(lead_text)
            if doi:
                hot_leads[source_id_from_value("doi", doi)] += 1

    items: list[dict[str, Any]] = []
    for source_id, record in sources.items():
        path_meta_body = papers.get(source_id)
        title = str(record.get("title") or record.get("value") or source_id)
        if path_meta_body is None:
            reasons = ["no paper draft"]
            if str(record.get("fulltext_status", "")) in {"needs-user-pdf", ""}:
                reasons.append("full text status unknown or needs user PDF")
            priority = 10 + hot_leads[source_id]
            items.append(
                {
                    "source_id": source_id,
                    "title": title,
                    "priority": priority,
                    "action": "create-paper-draft",
                    "reasons": reasons,
                    "path": "",
                }
            )
            continue
        path, meta, _ = path_meta_body
        reasons: list[str] = []
        action = "review-reading"
        fulltext_status = str(meta.get("fulltext_status", ""))
        reading_state = str(meta.get("reading_state", meta.get("reading_status", "")))
        human_feedback = str(meta.get("human_feedback_level", "none"))
        claim_readiness = str(meta.get("claim_readiness", ""))
        priority = hot_leads[source_id]
        if fulltext_status == "needs-user-pdf":
            reasons.append("needs user PDF for full text")
            action = "request-user-pdf"
            priority += 90
        if reading_state in {"metadata-only", "abstract-read"}:
            reasons.append(f"reading state is {reading_state}")
            priority += 50
        if human_feedback == "none":
            reasons.append("no human feedback yet")
            priority += 30
        if claim_readiness == "locator-needed":
            reasons.append("locator needed before stable claims")
            priority += 20
        if hot_leads[source_id]:
            reasons.append(f"repeated paper/search demand: {hot_leads[source_id]}")
            priority += 10 * hot_leads[source_id]
        if not reasons and claim_readiness in {"claim-ready", "synthesis-ready"}:
            reasons.append("ready for synthesis review")
            action = "synthesis-review"
            priority += 10
        if reasons:
            items.append(
                {
                    "source_id": source_id,
                    "title": title,
                    "priority": priority,
                    "action": action,
                    "reasons": reasons,
                    "path": relative_workspace_path(ws, path),
                }
            )
    items.sort(key=lambda item: (-int(item["priority"]), str(item["source_id"])))
    return items


def render_paper_nudge(ws: Workspace, *, limit: int = 10) -> str:
    items = paper_queue(ws)[:limit]
    lines = [
        "# RKF Paper Reading Nudge",
        "",
        f"Generated: {today()}",
        "",
        "This is an active reading queue. It prioritizes understanding maturity and user feedback; it does not promote claims by itself.",
        "",
    ]
    if not items:
        lines.append("- No active paper nudges.")
        return "\n".join(lines) + "\n"
    for item in items:
        path = f" path={item['path']}" if item.get("path") else ""
        lines.append(f"- {item['source_id']} action={item['action']} priority={item['priority']}{path}")
        lines.append(f"  reasons: {'; '.join(item['reasons'])}")
    return "\n".join(lines) + "\n"


def render_workspace_status(ws: Workspace, *, log_tail: int = 5) -> str:
    sources = _source_records(ws)
    evidence = _evidence_records(ws)
    knowledge = knowledge_page_records(ws)
    source_counts = Counter(str(record.get("status", "unknown")) for record in sources.values())
    evidence_counts = Counter(str(record.get("status", "unknown")) for record in evidence.values())
    knowledge_counts = Counter(str(meta.get("type", "unknown")) for _, meta, _ in knowledge)
    paper_reading_counts = Counter(
        str(meta.get("reading_state", meta.get("reading_status", "unknown")))
        for _, meta, _ in knowledge
        if meta.get("type") == "paper"
    )
    paper_queue_count = len(paper_queue(ws))
    gate_count = len(list(ws.paths.gates.rglob("*.md"))) if ws.paths.gates.exists() else 0
    hot_events = recent_hot_events(ws) if ws.paths.hot_md.exists() else []

    lines = [
        "# RKF Workspace Status",
        "",
        f"- Wiki root: {relative_workspace_path(ws, ws.paths.wiki_root)}",
        f"- Knowledge pages: {len(knowledge)}",
        f"- Sources: {len(sources)}",
        f"- Evidence artifacts: {len(evidence)}",
        f"- Pending/review gate files: {gate_count}",
        f"- Topics: {len(ws.load_topics())}",
        f"- Hot-query events in window: {len(hot_events)}",
        f"- Active paper nudges: {paper_queue_count}",
        "",
        "## Source Status",
        "",
    ]
    lines.extend(_format_counter(source_counts, empty="No source records."))
    lines.extend(["", "## Evidence Status", ""])
    lines.extend(_format_counter(evidence_counts, empty="No evidence artifacts."))
    lines.extend(["", "## Knowledge Types", ""])
    lines.extend(_format_counter(knowledge_counts, empty="No knowledge pages."))
    lines.extend(["", "## Paper Reading State", ""])
    lines.extend(_format_counter(paper_reading_counts, empty="No paper reading states."))
    lines.extend(["", "## Recent Log", ""])
    if ws.paths.log.exists():
        log_lines = [line for line in read_text(ws.paths.log).splitlines() if line.startswith("- ")]
        lines.extend(log_lines[-log_tail:] or ["- No log entries."])
    else:
        lines.append("- No wiki log found.")
    return "\n".join(lines) + "\n"


def lint_public_safety(ws: Workspace) -> list[str]:
    errors: list[str] = []
    scan_roots = [ws.paths.knowledge, ws.paths.governance, ws.paths.graph]
    for root in scan_roots:
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            rel = relative_workspace_path(ws, path)
            if path.suffix.lower() == ".pdf":
                errors.append(f"{rel}: PDF file is in public wiki layer")
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pattern in LOCAL_PATH_PATTERNS:
                for match in pattern.findall(text):
                    errors.append(f"{rel}: local/private path pattern: {match}")
            if rel.startswith("knowledge/papers/") and len(text) > 120000:
                errors.append(f"{rel}: unusually large paper page may contain copied article text")
    if ws.paths.hot_md.exists():
        rel = relative_workspace_path(ws, ws.paths.hot_md)
        text = ws.paths.hot_md.read_text(encoding="utf-8", errors="replace")
        for pattern in LOCAL_PATH_PATTERNS:
            for match in pattern.findall(text):
                errors.append(f"{rel}: local/private path pattern: {match}")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if len(line) > HOT_NOTES_MAX_CHARS:
                errors.append(f"{rel}:{line_number}: unusually long hot-query line may contain pasted transcript or article text")
    return errors


def export_graph(ws: Workspace) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []:
        record = read_json(path)
        node = {"id": record["source_id"], "type": "source", "status": record.get("status", "")}
        for key in ("reading_state", "fulltext_status"):
            if record.get(key):
                node[key] = record[key]
        nodes.append(node)
        for evidence_id in record.get("evidence_ids", []):
            edges.append({"from": record["source_id"], "to": evidence_id, "type": "has-evidence"})
        for topic_id in record.get("topic_ids", []):
            edges.append({"from": record["source_id"], "to": topic_id, "type": "tagged-with"})
    if ws.paths.knowledge.exists():
        for path in sorted(ws.paths.knowledge.rglob("*.md")):
            meta, _ = parse_frontmatter(read_text(path))
            if not meta:
                continue
            node_id = path.relative_to(ws.paths.knowledge).with_suffix("").as_posix()
            node = {"id": node_id, "type": meta.get("type", "knowledge"), "status": meta.get("status", "")}
            for key in (
                "reading_state",
                "fulltext_status",
                "human_feedback_level",
                "claim_readiness",
                "synthesis_maturity",
                "source_coverage",
            ):
                if meta.get(key):
                    node[key] = meta[key]
            nodes.append(node)
            for evidence_id in meta.get("evidence_ids", []):
                edges.append({"from": node_id, "to": evidence_id, "type": "supported-by"})
            if meta.get("source_id"):
                edges.append({"from": node_id, "to": meta["source_id"], "type": "derived-from"})
            for topic_id in meta.get("topics", []):
                edges.append({"from": node_id, "to": topic_id, "type": "tagged-with"})
    graph = {"schema": "rkf-graph-v1", "generated": today(), "nodes": nodes, "edges": edges}
    write_json(ws.paths.graph / "research_graph.json", graph)
    return graph


def external_sandbox_capsule(ws: Workspace) -> Path:
    allowed_modes = [
        "capture",
        "discover",
        "acquire",
        "verify-pdf",
        "distill",
        "query",
        "save",
        "synthesize",
        "hot record",
        "hot refresh",
        "paper status",
        "paper feedback",
        "paper queue",
        "paper next",
        "paper nudge",
        "status",
        "propagate",
        "lint",
        "graph",
    ]
    path = ws.paths.prompts / "external_sandbox_context.md"
    write_text(
        path,
        "# Research Knowledge Framework Context Capsule\n\n"
        f"- Repo path: {ws.root}\n"
        f"- Private evidence root: {ws.paths.private_evidence}\n"
        "- Public-safe boundary: do not paste PDFs, full article text, local secrets, or private Drive paths into public wiki pages.\n"
        "- Reading rule: metadata, search candidates, and ARS reports may start paper drafts, but they are not stable claim evidence by themselves.\n"
        "- Durable path: capture source -> create/read paper draft -> update full-text status -> request user PDF only when unavailable -> record feedback/locators -> promote claims only at the boundary.\n"
        "- Claim boundary: stable claims and trusted synthesis need a locator, human feedback, existing governed source, or explicit blocker.\n"
        "- Reading ledger rule: public-safe reading events live under state/reading/ and are operational memory, not claim evidence by themselves.\n"
        "- Hot-query rule: public-safe research questions may be recorded in hot.md with `python3 tools/rk.py hot record`; do not create separate hot-query files.\n"
        "- Target save layers: paper, question, concept, claim, synthesis, topic, meeting, seminar, review item.\n"
        "- Allowed modes: "
        + ", ".join(allowed_modes)
        + "\n\n"
        "## Save Proposal Format\n\n"
        "```yaml\n"
        "target_layer: paper | question | concept | claim | synthesis | topic | review\n"
        "title: short title\n"
        "reading_state: metadata-only | abstract-read | partial-fulltext | fulltext-read | human-reviewed | blocked\n"
        "fulltext_status: unknown | needs-user-pdf | user-pdf-provided | publisher-html | publisher-pdf | open-access-pdf | partial-only | fulltext-read | unavailable | blocked\n"
        "human_feedback_level: none | skimmed | discussed | annotated | trusted\n"
        "evidence_boundary: metadata-only, locator, existing wiki page, human-reviewed, or review blocker\n"
        "confidence: low | medium | high | mixed\n"
        "recommended_mode: save | review | synthesize | distill | paper-feedback\n"
        "reason_to_save: one sentence\n"
        "```\n",
    )
    return path
