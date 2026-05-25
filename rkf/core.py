"""Core runtime helpers for the Research Knowledge Framework.

RKF keeps research memory governed: candidates become source records, reviewed
reading artifacts can support paper pages, and durable knowledge stays in wiki
objects with evidence boundaries. Temporary PDF or OCR extraction may help an
agent read, but it is not a persisted knowledge layer.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
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
PAPER_READING_STATUSES = {"full-read", "first-pass-pdf-qc", "ocr-qc", "visual-qc"}
LOCAL_PATH_PATTERNS = [
    re.compile("/" + r"Users/(?!\[\^)[^/\s]+"),
    re.compile(r"C:\\Users\\", re.IGNORECASE),
]


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


def infer_evidence_tier(meta: dict[str, Any], body: str = "") -> str:
    explicit = str(meta.get("evidence_tier", "")).strip()
    if explicit:
        return explicit
    page_type = str(meta.get("type", ""))
    boundary = str(meta.get("evidence_boundary", "")).lower()
    reading = str(meta.get("reading_status", "")).lower()
    text = body.lower()
    if "review-blocker" in boundary:
        return "review-blocker"
    if page_type == "paper":
        if reading == "full-read" and meta.get("evidence_ids"):
            return "locator-backed"
        if reading in {"first-pass-pdf-qc", "ocr-qc", "visual-qc"} and meta.get("evidence_ids"):
            return "pdf-qc-stub"
        if "metadata" in text or "abstract" in text:
            return "metadata-only"
        return "candidate"
    if "metadata" in boundary or "abstract" in boundary:
        return "mixed"
    if "pdf-evidence" in boundary or meta.get("evidence_ids"):
        return "locator-backed"
    if "candidate" in boundary:
        return "candidate"
    return "review-blocker"


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
    state: Path
    sources: Path
    evidence_index: Path
    gates: Path
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
            state=state,
            sources=state / "sources",
            evidence_index=state / "evidence",
            gates=state / "gates",
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
    set_source_status(ws, record, "pdf_downloaded")
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
        raise SystemExit(f"invalid PDF QC status: {qc_status}")
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
    set_source_status(ws, record, "pdf_qc_done")
    append_log(ws, "verify-pdf", f"{record['source_id']} qc_status={qc_status}")
    return artifact


def qced_pdf_artifact(ws: Workspace, record: dict[str, Any]) -> dict[str, Any] | None:
    artifact = pdf_artifact(ws, record)
    if artifact and artifact.get("qc_status") in PDF_QC_DONE and artifact.get("status") == "pdf_qc_done":
        return artifact
    return None


def create_paper_note(ws: Workspace, record: dict[str, Any], *, slug: str = "") -> Path:
    artifact = qced_pdf_artifact(ws, record)
    if record.get("status") != "pdf_qc_done" or artifact is None:
        raise SystemExit("refusing paper distill: source has no QCed PDF evidence")
    title = record.get("title") or record["source_id"].replace("_", " ").title()
    page_slug = slugify(slug or record["source_id"])
    dest = ws.paths.knowledge / "papers" / f"{page_slug}.md"
    meta = {
        "type": "paper",
        "status": "draft",
        "source_id": record["source_id"],
        "source_status": "peer-reviewed",
        "reading_status": "full-read",
        "review_stage": "ai-extracted",
        "evidence_boundary": "pdf-evidence",
        "evidence_tier": "locator-backed" if artifact.get("locators") else "pdf-qc-stub",
        "evidence_ids": [artifact["evidence_id"]],
        "topics": record.get("topic_ids", []),
        "created": today(),
        "updated": today(),
    }
    locators = artifact.get("locators", [])
    locator_lines = "\n".join(f"- {item}" for item in locators) if locators else "- TBD while reading PDF"
    body = (
        f"# {title}\n\n"
        "## Source Identity\n\n"
        f"- Source ID: {record['source_id']}\n"
        f"- DOI: {record.get('normalized_doi', '')}\n"
        f"- PDF Evidence: {artifact['evidence_id']}\n"
        "- Evidence status: QCed PDF\n\n"
        "## PDF Locators\n\n"
        f"{locator_lines}\n\n"
        "## Reading Notes\n\n"
        "- Research question:\n"
        "- Method:\n"
        "- Key findings:\n"
        "- Limitations:\n\n"
        "## Claims To Promote\n\n"
        "- Claim:\n"
        "  - PDF locator:\n"
        "  - Caveat:\n\n"
        "## Graph Links\n\n"
        "- Topics:\n"
        "- Concepts:\n"
        "- Questions:\n"
    )
    write_text(dest, frontmatter(meta) + body)
    set_source_status(ws, record, "wiki_done")
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
            summary = first_summary_line(body)
            suffix = f" - {summary}" if summary else ""
            lines.append(
                f"- [{title}]({rel}): type={page_type}; status={status}; review={review_stage}; "
                f"evidence={boundary or 'unspecified'}; tier={tier}; topics={topics or 'none'}{suffix}"
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
            if reading_status != "full-read" and meta.get("status") not in {"draft", "review"}:
                errors.append(f"{rel}: non-full-read paper pages must stay draft or review")
            if meta.get("evidence_boundary") != "pdf-evidence":
                errors.append(f"{rel}: paper page must use pdf-evidence boundary")
            if not meta.get("evidence_ids"):
                errors.append(f"{rel}: paper page missing PDF evidence id")
    return errors


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
    return errors


def export_graph(ws: Workspace) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in sorted(ws.paths.sources.glob("*.json")) if ws.paths.sources.exists() else []:
        record = read_json(path)
        nodes.append({"id": record["source_id"], "type": "source", "status": record.get("status", "")})
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
            nodes.append({"id": node_id, "type": meta.get("type", "knowledge"), "status": meta.get("status", "")})
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
    allowed_modes = ["capture", "discover", "acquire", "verify-pdf", "distill", "query", "save", "synthesize", "lint", "graph"]
    path = ws.paths.prompts / "external_sandbox_context.md"
    write_text(
        path,
        "# Research Knowledge Framework Context Capsule\n\n"
        f"- Repo path: {ws.root}\n"
        f"- Private evidence root: {ws.paths.private_evidence}\n"
        "- Public-safe boundary: do not paste PDFs, full article text, local secrets, or private Drive paths into public wiki pages.\n"
        "- Evidence rule: metadata, search candidates, and ARS reports are not evidence; a QCed PDF artifact is required before paper distillation.\n"
        "- Durable path: PDF evidence -> PDF QC -> wiki page.\n"
        "- Target save layers: paper, question, concept, claim, synthesis, topic, meeting, seminar, review item.\n"
        "- Allowed modes: "
        + ", ".join(allowed_modes)
        + "\n\n"
        "## Save Proposal Format\n\n"
        "```yaml\n"
        "target_layer: paper | question | concept | claim | synthesis | topic | review\n"
        "title: short title\n"
        "evidence_boundary: PDF locator, existing wiki page, or review blocker\n"
        "confidence: low | medium | high | mixed\n"
        "recommended_mode: save | review | synthesize | distill\n"
        "reason_to_save: one sentence\n"
        "```\n",
    )
    return path
