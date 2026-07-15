"""Candidate-only paper discovery for RKF.

Discovery is deliberately separated from source capture and evidence
promotion.  A preview performs network reads only, normalizes provider output
to a strict public-metadata allowlist, and produces an exact payload hash.  A
recorded run preserves that approved payload under ``state/search_runs``;
later acceptance is tracked in a separate state file so the recorded run
remains immutable.
"""

from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .core import Workspace, extract_doi, normalize_doi, read_json, slugify


DISCOVERY_PREVIEW_SCHEMA = "rkf-discovery-preview-v1"
DISCOVERY_RUN_SCHEMA = "rkf-discovery-run-v2"
DISCOVERY_CANDIDATE_SCHEMA = "rkf-discovery-candidate-v1"
DISCOVERY_ACCEPTANCE_SCHEMA = "rkf-discovery-acceptance-v1"
LEGACY_DISCOVERY_RUN_SCHEMA = "rkf-discovery-run-v1"

DEFAULT_MAX_RESULTS = 20
MAX_RESULTS_LIMIT = 100
MAX_QUERY_CHARS = 500
MAX_TITLE_CHARS = 500
MAX_AUTHORS = 20
MAX_AUTHOR_CHARS = 160
MAX_VENUE_CHARS = 300
MAX_PROVIDER_ID_CHARS = 300

ProviderClient = Callable[[str, int], Iterable[Mapping[str, Any]]]
HTTPGet = Callable[[str, Mapping[str, str]], bytes]

_PREVIEW_KEYS = {
    "schema",
    "generated_at",
    "query",
    "topic_id",
    "requested_providers",
    "status",
    "provider_status",
    "candidate_count",
    "candidates",
    "evidence_boundary",
    "promotion",
    "persistence",
    "preview_hash",
}
_CANDIDATE_KEYS = {
    "schema",
    "candidate_id",
    "title",
    "authors",
    "year",
    "venue",
    "doi",
    "url",
    "provider",
    "provider_id",
    "providers",
    "provider_ids",
    "topic_id",
    "relevance_score",
    "ranking_explanation",
    "dedupe_status",
    "evidence_boundary",
    "claim_readiness",
    "promotion",
}
_PROVIDER_STATUS_KEYS = {"provider", "status", "count", "error_code"}
_RUN_KEYS = {
    "schema",
    "run_id",
    "recorded_at",
    "generated_at",
    "query",
    "topic_id",
    "preview_hash",
    "status",
    "requested_providers",
    "provider_status",
    "candidate_count",
    "candidates",
    "evidence_boundary",
    "promotion",
}
_RUN_ID_RE = re.compile(r"^run_[a-z0-9][a-z0-9_-]{0,159}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TOPIC_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PRIVATE_QUERY_RE = re.compile(
    r"(?:/(?:Users|home|private|Volumes)/|C:\\Users\\|file://|"
    r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|private[_-]?key|secret)\s*[:=])",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+(?:\.[A-Z]{2,})?\b",
    re.IGNORECASE,
)
_LOCAL_ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s=:(])(?:~[/\\]|/(?!/)[^\s\"']+|[A-Z]:[/\\][^\s\"']+|\\\\[^\s\"']+)",
    re.IGNORECASE,
)
_COMMON_TOKEN_RE = re.compile(
    r"\b(?:sk-(?:proj-)?|ghp_|github_pat_|xox[baprs]-)[A-Z0-9_-]{12,}\b|"
    r"\bAKIA[A-Z0-9]{16}\b|\bBearer\s+[A-Z0-9._~-]{12,}",
    re.IGNORECASE,
)
_HIGH_ENTROPY_RE = re.compile(
    r"\b(?=[A-Za-z0-9_-]{32,}\b)(?=[A-Za-z0-9_-]*[a-z])"
    r"(?=[A-Za-z0-9_-]*[A-Z])(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]+\b"
)
_NONPUBLIC_HOST_SUFFIXES = (
    ".example",
    ".home",
    ".internal",
    ".invalid",
    ".lan",
    ".local",
    ".localhost",
    ".test",
)
_NUMERIC_HOST_LABEL_RE = re.compile(r"^(?:0x[0-9a-f]+|[0-9]+)$", re.IGNORECASE)
_ACCEPTANCE_KEYS = {"schema", "run_id", "preview_hash", "updated_at", "accepted"}
_ACCEPTED_ITEM_KEYS = {"candidate_id", "accepted_at", "actor"}
LEGACY_DISCOVERY_RUN_KEYS = (
    {"schema", "query", "topic_id", "live", "candidates", "gate", "created"},
    {"schema", "query", "topic_ids", "live", "candidates", "gate", "created"},
)
LEGACY_DISCOVERY_CANDIDATE_KEYS = {
    frozenset({"source_id", "title", "year", "doi", "evidence_role", "status"}),
    frozenset({"source_id", "title", "year", "doi", "evidence_role", "status", "journal"}),
}
LEGACY_DISCOVERY_GATES = {
    "candidates_are_not_evidence",
    "candidates_and_metadata_are_not_stable_claim_evidence",
}


def _contains_private_metadata(value: str) -> bool:
    """Detect personal/path/token material without banning research terms.

    In particular, a bare word such as ``secret`` or ``password`` remains a
    valid scholarly query.  Only assignment-shaped sensitive values, personal
    addresses, local paths, or token-shaped strings are rejected.
    """

    return bool(
        _PRIVATE_QUERY_RE.search(value)
        or _EMAIL_RE.search(value)
        or _LOCAL_ABSOLUTE_PATH_RE.search(value)
        or _COMMON_TOKEN_RE.search(value)
        or _HIGH_ENTROPY_RE.search(value)
    )


class DiscoveryError(ValueError):
    """Raised when a discovery preview or recorded run is invalid."""


def validate_legacy_discovery_run(payload: Mapping[str, Any]) -> int:
    """Validate a deprecated v1 run and return its isolated candidate count."""

    if (
        payload.get("schema") != LEGACY_DISCOVERY_RUN_SCHEMA
        or set(payload) not in LEGACY_DISCOVERY_RUN_KEYS
        or not isinstance(payload.get("query"), str)
        or len(payload["query"]) > MAX_QUERY_CHARS
        or not isinstance(payload.get("live"), bool)
        or payload.get("gate") not in LEGACY_DISCOVERY_GATES
        or not isinstance(payload.get("created"), str)
    ):
        raise DiscoveryError("legacy discovery state is invalid")
    topic_value = payload.get("topic_ids", payload.get("topic_id", ""))
    if not (
        isinstance(topic_value, str)
        or (isinstance(topic_value, list) and all(isinstance(value, str) for value in topic_value))
    ):
        raise DiscoveryError("legacy discovery state is invalid")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 1000:
        raise DiscoveryError("legacy discovery state is invalid")
    for candidate in candidates:
        if (
            not isinstance(candidate, dict)
            or frozenset(candidate) not in LEGACY_DISCOVERY_CANDIDATE_KEYS
            or candidate.get("status") != "metadata_ok"
            or any(
                not isinstance(candidate.get(key), str)
                for key in ("source_id", "title", "doi", "evidence_role")
            )
            or not isinstance(candidate.get("year"), (str, int))
            or isinstance(candidate.get("year"), bool)
            or ("journal" in candidate and not isinstance(candidate.get("journal"), str))
        ):
            raise DiscoveryError("legacy discovery state is invalid")
    return len(candidates)


def audit_legacy_discovery(ws: Workspace) -> dict[str, Any]:
    """Classify legacy candidates as isolated, without persisting identities."""

    records: list[dict[str, Any]] = []
    validation_errors = 0
    root = ws.paths.search_runs
    paths = sorted(root.glob("*/candidates.json")) if root.exists() else []
    for path in paths:
        if path.parent.name.startswith("run_"):
            continue
        raw = path.read_bytes()
        fingerprint = sha256(raw).hexdigest()
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise DiscoveryError("legacy discovery state is invalid")
            candidate_count = validate_legacy_discovery_run(payload)
            status = "isolated-candidate-only"
        except (DiscoveryError, UnicodeDecodeError, json.JSONDecodeError):
            candidate_count = 0
            status = "validation-error"
            validation_errors += 1
        records.append(
            {
                "input_fingerprint": fingerprint,
                "candidate_count": candidate_count,
                "classification": "legacy-unclassified",
                "disposition": status,
                "promotion": "none",
            }
        )
    isolated_count = sum(
        int(record["candidate_count"])
        for record in records
        if record["disposition"] == "isolated-candidate-only"
    )
    return {
        "schema": "rkf-legacy-discovery-isolation-report-v1",
        "legacy_run_count": len(records),
        "before_legacy_candidate_count": isolated_count,
        "canonicalized_candidate_count": 0,
        "isolated_candidate_count": isolated_count,
        "unresolved_count": 0,
        "validation_error_count": validation_errors,
        "after_active_legacy_candidate_count": 0,
        "rollback_notes": "Read-only classification; no live candidate record was changed.",
        "records": records,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def discovery_preview_hash(preview: Mapping[str, Any]) -> str:
    """Return the exact hash for a preview, excluding its hash field itself."""

    payload = dict(preview)
    payload.pop("preview_hash", None)
    return sha256(_canonical_json(payload)).hexdigest()


def _default_http_get(url: str, headers: Mapping[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=dict(headers))
    with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310
        return response.read()


def _json_get(url: str, headers: Mapping[str, str], http_get: HTTPGet | None) -> Mapping[str, Any]:
    getter = http_get or _default_http_get
    payload = json.loads(getter(url, headers).decode("utf-8"))
    if not isinstance(payload, dict):
        raise DiscoveryError("provider response is not a JSON object")
    return payload


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
        return ""
    return value.strip() if isinstance(value, str) else ""


def _safe_text(value: Any, max_chars: int) -> str:
    text = " ".join(_first_text(value).split())
    if _contains_private_metadata(text):
        return ""
    return text[:max_chars]


def _safe_year(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        year = int(value)
    elif isinstance(value, str):
        match = re.search(r"(?:19|20)\d{2}", value)
        if not match:
            return None
        year = int(match.group(0))
    else:
        return None
    return year if 1800 <= year <= 2200 else None


def _safe_score(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        score = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if score != score or score in {float("inf"), float("-inf")}:
        return 0.0
    return round(max(0.0, score), 6)


def _safe_url(value: Any) -> str:
    raw = _first_text(value)
    if not raw or any(character.isspace() for character in raw) or _contains_private_metadata(raw):
        return ""
    try:
        parsed = urllib.parse.urlsplit(raw)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""
    host = hostname.casefold().rstrip(".")
    if not host or host == "localhost" or host.endswith(_NONPUBLIC_HOST_SUFFIXES):
        return ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            return ""
        # Browsers accept legacy IPv4 spellings such as ``127.1`` and
        # ``0x7f.0.0.1`` even though ``ipaddress`` rejects them.  Treat an
        # all-numeric/hex-label hostname as an obscured IP so a public RKF
        # landing link cannot point back to a reader's local network.
        if all(_NUMERIC_HOST_LABEL_RE.fullmatch(label) for label in host.split(".")):
            return ""
        try:
            host.encode("idna")
        except UnicodeError:
            return ""
    else:
        if not address.is_global:
            return ""
    if any(character in parsed.netloc for character in ("\r", "\n", "\t")):
        return ""
    lowered_path = parsed.path.lower()
    path_segments = {segment for segment in lowered_path.split("/") if segment}
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    looks_like_pdf = (
        lowered_path.endswith(".pdf")
        or "pdf" in path_segments
        or any(
            key.lower() in {"format", "type"} and value.lower() == "pdf"
            for key, value in query
        )
    )
    if looks_like_pdf:
        return ""
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", "")
    )


def _safe_doi(value: Any) -> str:
    raw = _first_text(value)
    if not raw:
        return ""
    doi = extract_doi(raw)
    return normalize_doi(doi) if doi else ""


def _author_names(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_authors: Iterable[Any] = re.split(r"\s*(?:;|\band\b)\s*", value)
    elif isinstance(value, list):
        raw_authors = value
    else:
        raw_authors = []
    names: list[str] = []
    for item in raw_authors:
        if isinstance(item, Mapping):
            name = _first_text(item.get("display_name") or item.get("name"))
            if not name:
                given = _first_text(item.get("given"))
                family = _first_text(item.get("family"))
                name = " ".join(part for part in (given, family) if part)
        else:
            name = _first_text(item)
        name = _safe_text(name, MAX_AUTHOR_CHARS)
        if name and name not in names:
            names.append(name)
        if len(names) >= MAX_AUTHORS:
            break
    return names


def _published_year(record: Mapping[str, Any]) -> int | None:
    for key in ("year", "publication_year", "published_year", "published", "date"):
        year = _safe_year(record.get(key))
        if year is not None:
            return year
    return None


def fetch_crossref(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    *,
    http_get: HTTPGet | None = None,
) -> list[dict[str, Any]]:
    """Fetch allowlisted bibliographic metadata from Crossref REST."""

    params = urllib.parse.urlencode(
        {
            "query.bibliographic": query,
            "rows": max_results,
            "select": "DOI,title,author,published,container-title,URL,score",
        }
    )
    url = f"https://api.crossref.org/works?{params}"
    payload = _json_get(
        url,
        {
            "Accept": "application/json",
            "User-Agent": "ResearchKnowledgeFramework/1.1 (+https://github.com/ChenHau-Lan/ResearchWiki)",
        },
        http_get,
    )
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, Mapping) else []
    results: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, Mapping):
            continue
        date_parts = item.get("published", {})
        year: int | None = None
        if isinstance(date_parts, Mapping):
            parts = date_parts.get("date-parts", [])
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                year = _safe_year(parts[0][0])
        doi = _safe_doi(item.get("DOI"))
        results.append(
            {
                "title": _first_text(item.get("title")),
                "authors": item.get("author", []),
                "year": year,
                "venue": _first_text(item.get("container-title")),
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else _safe_url(item.get("URL")),
                "provider_id": doi,
                "score": item.get("score", 0),
            }
        )
    return results


def fetch_arxiv(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    *,
    http_get: HTTPGet | None = None,
) -> list[dict[str, Any]]:
    """Fetch allowlisted bibliographic metadata from the arXiv Atom API."""

    params = urllib.parse.urlencode(
        {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
    )
    url = f"https://export.arxiv.org/api/query?{params}"
    getter = http_get or _default_http_get
    raw = getter(
        url,
        {
            "Accept": "application/atom+xml",
            "User-Agent": "ResearchKnowledgeFramework/1.1 (+https://github.com/ChenHau-Lan/ResearchWiki)",
        },
    )
    root = ET.fromstring(raw)
    atom = "{http://www.w3.org/2005/Atom}"
    arxiv = "{http://arxiv.org/schemas/atom}"
    results: list[dict[str, Any]] = []
    for entry in root.findall(f"{atom}entry"):
        title = _safe_text(entry.findtext(f"{atom}title", default=""), MAX_TITLE_CHARS)
        authors = [
            _safe_text(author.findtext(f"{atom}name", default=""), MAX_AUTHOR_CHARS)
            for author in entry.findall(f"{atom}author")
        ]
        entry_id = _safe_url(entry.findtext(f"{atom}id", default=""))
        provider_id = entry_id.rstrip("/").rsplit("/", 1)[-1] if entry_id else ""
        doi = _safe_doi(entry.findtext(f"{arxiv}doi", default=""))
        results.append(
            {
                "title": title,
                "authors": [author for author in authors if author],
                "year": _safe_year(entry.findtext(f"{atom}published", default="")),
                "venue": _safe_text(
                    entry.findtext(f"{arxiv}journal_ref", default="") or "arXiv",
                    MAX_VENUE_CHARS,
                ),
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else entry_id,
                "provider_id": provider_id,
                "score": 0,
            }
        )
    return results


def fetch_openalex(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    *,
    api_key: str,
    http_get: HTTPGet | None = None,
) -> list[dict[str, Any]]:
    """Fetch allowlisted metadata from OpenAlex when an API key is supplied."""

    if not api_key.strip():
        raise DiscoveryError("OPENALEX_API_KEY_REQUIRED")
    params = urllib.parse.urlencode(
        {"search": query, "per_page": max_results, "api_key": api_key.strip()}
    )
    payload = _json_get(
        f"https://api.openalex.org/works?{params}",
        {
            "Accept": "application/json",
            "User-Agent": "ResearchKnowledgeFramework/1.1 (+https://github.com/ChenHau-Lan/ResearchWiki)",
        },
        http_get,
    )
    results: list[dict[str, Any]] = []
    items = payload.get("results", [])
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, Mapping):
            continue
        authors: list[str] = []
        for authorship in item.get("authorships", []) if isinstance(item.get("authorships"), list) else []:
            if not isinstance(authorship, Mapping):
                continue
            author = authorship.get("author", {})
            if isinstance(author, Mapping):
                authors.append(_first_text(author.get("display_name")))
        primary = item.get("primary_location", {})
        source = primary.get("source", {}) if isinstance(primary, Mapping) else {}
        venue = _first_text(source.get("display_name")) if isinstance(source, Mapping) else ""
        landing_url = primary.get("landing_page_url", "") if isinstance(primary, Mapping) else ""
        doi = _safe_doi(item.get("doi"))
        results.append(
            {
                "title": _first_text(item.get("display_name") or item.get("title")),
                "authors": authors,
                "year": item.get("publication_year"),
                "venue": venue,
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else _safe_url(landing_url),
                "provider_id": _first_text(item.get("id")),
                "score": item.get("relevance_score", 0),
            }
        )
    return results


def adapt_paper_radar(
    payload: Sequence[Mapping[str, Any]] | Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Convert paper-radar exports to the same strict metadata input shape.

    Only bibliographic fields are read.  Abstracts, PDF routes, private state,
    deep-reading content, and arbitrary upstream fields are ignored.
    """

    if isinstance(payload, Mapping):
        records: Sequence[Mapping[str, Any]] = []
        for key in ("papers", "candidates", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                records = value
                break
    else:
        records = payload

    adapted: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        doi = _safe_doi(record.get("doi") or record.get("DOI"))
        public_url = record.get("url") or record.get("link") or record.get("public_url")
        adapted.append(
            {
                "title": record.get("title") or record.get("name"),
                "authors": record.get("authors") or record.get("author") or [],
                "year": (
                    record.get("year")
                    or record.get("publication_year")
                    or record.get("published_year")
                    or record.get("published")
                ),
                "venue": record.get("venue") or record.get("journal") or record.get("source"),
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else _safe_url(public_url),
                "provider_id": record.get("id") or record.get("pmid") or doi,
                "score": record.get("score") or record.get("interest_score") or 0,
            }
        )
    return adapted


def _normalize_provider_record(
    provider: str,
    record: Mapping[str, Any],
    *,
    topic_id: str,
) -> dict[str, Any] | None:
    title = _safe_text(record.get("title") or record.get("display_name"), MAX_TITLE_CHARS)
    if not title:
        return None
    doi = _safe_doi(record.get("doi") or record.get("DOI"))
    url = f"https://doi.org/{doi}" if doi else _safe_url(
        record.get("url") or record.get("URL") or record.get("link")
    )
    authors = _author_names(record.get("authors") or record.get("author") or [])
    provider_id = _safe_text(
        record.get("provider_id") or record.get("id") or doi,
        MAX_PROVIDER_ID_CHARS,
    )
    relevance_score = _safe_score(
        record.get("score") if record.get("score") is not None else record.get("relevance_score")
    )
    return {
        "schema": DISCOVERY_CANDIDATE_SCHEMA,
        "candidate_id": "",
        "title": title,
        "authors": authors,
        "year": _published_year(record),
        "venue": _safe_text(
            record.get("venue") or record.get("journal") or record.get("source"),
            MAX_VENUE_CHARS,
        ),
        "doi": doi,
        "url": url,
        "provider": provider,
        "provider_id": provider_id,
        "providers": [provider],
        "provider_ids": [f"{provider}:{provider_id}"] if provider_id else [],
        "topic_id": topic_id,
        "relevance_score": relevance_score,
        "ranking_explanation": (
            "Provider-ranked bibliographic match; candidate only."
            if relevance_score > 0
            else "Bibliographic match for the requested query; candidate only."
        ),
        "dedupe_status": "new",
        "evidence_boundary": "candidate-only",
        "claim_readiness": "not-ready",
        "promotion": "none",
    }


def _normalized_identity_text(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _bibliographic_key(candidate: Mapping[str, Any]) -> str:
    title = _normalized_identity_text(str(candidate.get("title", "")))
    year = str(candidate.get("year") or "")
    authors = candidate.get("authors", [])
    first_author = _normalized_identity_text(str(authors[0])) if isinstance(authors, list) and authors else ""
    if title and (year or first_author):
        return f"bib:{title}:{year}:{first_author}"
    provider_id = str(candidate.get("provider_id", ""))
    if provider_id:
        return f"provider:{candidate.get('provider', '')}:{provider_id}"
    return f"title:{title}"


def _identity_key(candidate: Mapping[str, Any]) -> str:
    doi = str(candidate.get("doi", ""))
    return f"doi:{doi}" if doi else _bibliographic_key(candidate)


def _merge_candidates(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for key in ("title", "venue", "doi", "url"):
        left_value = str(merged.get(key, ""))
        right_value = str(right.get(key, ""))
        if not left_value or (key == "title" and len(right_value) > len(left_value)):
            merged[key] = right_value
    if merged.get("year") is None and right.get("year") is not None:
        merged["year"] = right.get("year")
    merged["authors"] = list(dict.fromkeys([*merged.get("authors", []), *right.get("authors", [])]))[:MAX_AUTHORS]
    merged["providers"] = sorted(set([*merged.get("providers", []), *right.get("providers", [])]))
    merged["provider_ids"] = sorted(set([*merged.get("provider_ids", []), *right.get("provider_ids", [])]))
    merged["provider"] = merged["providers"][0]
    primary_prefix = f"{merged['provider']}:"
    primary_ids = [value for value in merged["provider_ids"] if value.startswith(primary_prefix)]
    merged["provider_id"] = primary_ids[0][len(primary_prefix) :] if primary_ids else ""
    merged["relevance_score"] = max(
        _safe_score(merged.get("relevance_score")),
        _safe_score(right.get("relevance_score")),
    )
    if merged["relevance_score"] > 0:
        merged["ranking_explanation"] = "Provider-ranked bibliographic match; candidate only."
    return merged


def _deduplicate_candidates(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    doi_index: dict[str, int] = {}
    bib_index: dict[str, int] = {}
    for source in candidates:
        candidate = dict(source)
        doi_key = f"doi:{candidate['doi']}" if candidate.get("doi") else ""
        bib_key = _bibliographic_key(candidate)
        index = doi_index.get(doi_key) if doi_key else None
        if index is None:
            bibliographic_match = bib_index.get(bib_key)
            if bibliographic_match is not None:
                existing_doi = str(merged[bibliographic_match].get("doi", ""))
                incoming_doi = str(candidate.get("doi", ""))
                if existing_doi and incoming_doi and existing_doi != incoming_doi:
                    merged[bibliographic_match]["dedupe_status"] = "ambiguous"
                    candidate["dedupe_status"] = "ambiguous"
                else:
                    index = bibliographic_match
        if index is None:
            index = len(merged)
            merged.append(candidate)
        else:
            merged[index] = _merge_candidates(merged[index], candidate)
        current = merged[index]
        if current.get("doi"):
            doi_index[f"doi:{current['doi']}"] = index
        bib_index.setdefault(_bibliographic_key(current), index)

    output: list[dict[str, Any]] = []
    for candidate in merged:
        identity = _identity_key(candidate)
        candidate["candidate_id"] = "cand_" + sha256(identity.encode("utf-8")).hexdigest()[:20]
        output.append(candidate)
    return output


def _existing_identity_sets(ws: Workspace) -> tuple[set[str], set[str], set[str]]:
    dois: set[str] = set()
    urls: set[str] = set()
    titles: set[str] = set()
    if not ws.paths.sources.exists():
        return dois, urls, titles
    for path in sorted(ws.paths.sources.glob("*.json")):
        try:
            record = read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        doi = _safe_doi(record.get("normalized_doi") or record.get("value"))
        url = _safe_url(record.get("value")) if record.get("kind") == "url" else ""
        title = _normalized_identity_text(str(record.get("title", "")))
        if doi:
            dois.add(doi)
        if url:
            urls.add(url)
        if title:
            titles.add(title)
    return dois, urls, titles


def _mark_existing(ws: Workspace, candidates: Sequence[dict[str, Any]]) -> None:
    dois, urls, titles = _existing_identity_sets(ws)
    for candidate in candidates:
        if candidate.get("doi") in dois or (candidate.get("url") and candidate.get("url") in urls):
            candidate["dedupe_status"] = "existing"
        elif _normalized_identity_text(str(candidate.get("title", ""))) in titles:
            candidate["dedupe_status"] = "ambiguous"


def _provider_status(provider: str, status: str, count: int, error_code: str = "") -> dict[str, Any]:
    return {
        "provider": provider,
        "status": status,
        "count": count,
        "error_code": error_code,
    }


def _default_provider_clients(
    *,
    openalex_api_key: str,
    http_get: HTTPGet | None,
) -> dict[str, ProviderClient]:
    clients: dict[str, ProviderClient] = {
        "crossref": lambda query, limit: fetch_crossref(query, limit, http_get=http_get),
        "arxiv": lambda query, limit: fetch_arxiv(query, limit, http_get=http_get),
    }
    if openalex_api_key:
        clients["openalex"] = lambda query, limit: fetch_openalex(
            query,
            limit,
            api_key=openalex_api_key,
            http_get=http_get,
        )
    return clients


def preview_discovery(
    ws: Workspace,
    *,
    query: str,
    topic_id: str = "",
    max_results: int = DEFAULT_MAX_RESULTS,
    provider_names: Sequence[str] | None = None,
    provider_clients: Mapping[str, ProviderClient] | None = None,
    paper_radar_records: Sequence[Mapping[str, Any]] | Mapping[str, Any] | None = None,
    openalex_api_key: str | None = None,
    http_get: HTTPGet | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a non-mutating, candidate-only discovery preview.

    ``provider_clients`` is the dependency-injection boundary used by tests and
    local adapters.  Provider exceptions are converted to path- and
    secret-free status codes; exception messages are never persisted.
    """

    if not isinstance(query, str):
        raise DiscoveryError("discovery query must be text")
    if not isinstance(topic_id, str):
        raise DiscoveryError("topic_id must be text")
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise DiscoveryError("max_results must be an integer")
    if provider_names is not None and (
        isinstance(provider_names, (str, bytes))
        or any(not isinstance(name, str) for name in provider_names)
    ):
        raise DiscoveryError("provider names must be a list of names")
    if paper_radar_records is not None and not isinstance(paper_radar_records, (Mapping, list, tuple)):
        raise DiscoveryError("paper-radar input must be a metadata record or list of records")

    normalized_query = " ".join(query.split())
    if not normalized_query:
        raise DiscoveryError("discovery query is required")
    if len(normalized_query) > MAX_QUERY_CHARS:
        raise DiscoveryError(f"discovery query exceeds {MAX_QUERY_CHARS} characters")
    if _contains_private_metadata(normalized_query):
        raise DiscoveryError("discovery query contains private or sensitive material")
    if max_results < 1 or max_results > MAX_RESULTS_LIMIT:
        raise DiscoveryError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

    api_key = openalex_api_key if openalex_api_key is not None else os.environ.get("OPENALEX_API_KEY", "")
    clients = (
        {str(name).strip().lower(): client for name, client in provider_clients.items()}
        if provider_clients is not None
        else _default_provider_clients(openalex_api_key=api_key, http_get=http_get)
    )
    if paper_radar_records is not None:
        clients["paper-radar"] = lambda _query, _limit: adapt_paper_radar(paper_radar_records)

    if provider_names is None:
        selected = list(clients)
    else:
        selected = list(dict.fromkeys(str(name).strip().lower() for name in provider_names if str(name).strip()))
    if not selected:
        raise DiscoveryError("at least one discovery provider is required")
    if any(not _PROVIDER_RE.fullmatch(provider) for provider in selected):
        raise DiscoveryError("provider names must use lowercase letters, digits, and hyphens")
    normalized_topic_id = topic_id.strip()
    if normalized_topic_id and (
        len(normalized_topic_id) > 160 or not _TOPIC_ID_RE.fullmatch(normalized_topic_id)
    ):
        raise DiscoveryError("topic_id must be a lowercase RKF topic identifier")

    collected: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    successful = 0
    for provider in selected:
        client = clients.get(provider)
        if client is None:
            error_code = (
                "OPENALEX_API_KEY_REQUIRED"
                if provider == "openalex" and not api_key
                else "PROVIDER_NOT_CONFIGURED"
            )
            statuses.append(_provider_status(provider, "skipped", 0, error_code))
            continue
        try:
            raw_records = list(client(normalized_query, max_results))
            accepted = 0
            for record in raw_records:
                if not isinstance(record, Mapping):
                    continue
                normalized = _normalize_provider_record(provider, record, topic_id=normalized_topic_id)
                if normalized is not None:
                    collected.append(normalized)
                    accepted += 1
            statuses.append(_provider_status(provider, "ok", accepted))
            successful += 1
        except Exception:  # Provider failures must be isolated and redacted.
            statuses.append(_provider_status(provider, "error", 0, "PROVIDER_UNAVAILABLE"))

    candidates = _deduplicate_candidates(collected)
    _mark_existing(ws, candidates)
    candidates.sort(
        key=lambda item: (
            -_safe_score(item.get("relevance_score")),
            -(item.get("year") or 0),
            str(item.get("title", "")).casefold(),
            str(item.get("candidate_id", "")),
        )
    )
    candidates = candidates[:max_results]

    if successful == len(selected):
        status = "ok"
    elif successful:
        status = "partial"
    else:
        status = "failed"
    preview: dict[str, Any] = {
        "schema": DISCOVERY_PREVIEW_SCHEMA,
        "generated_at": generated_at or _utc_now(),
        "query": normalized_query,
        "topic_id": normalized_topic_id,
        "requested_providers": selected,
        "status": status,
        "provider_status": statuses,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "evidence_boundary": "candidate-only",
        "promotion": "none",
        "persistence": "none",
    }
    preview["preview_hash"] = discovery_preview_hash(preview)
    _validate_preview(preview)
    return preview


def _validate_preview(preview: Mapping[str, Any]) -> None:
    if set(preview) != _PREVIEW_KEYS:
        raise DiscoveryError("preview contains fields outside the persistence allowlist")
    if preview.get("schema") != DISCOVERY_PREVIEW_SCHEMA:
        raise DiscoveryError("unsupported discovery preview schema")
    if preview.get("evidence_boundary") != "candidate-only" or preview.get("promotion") != "none":
        raise DiscoveryError("discovery preview cannot promote candidates")
    if preview.get("persistence") != "none":
        raise DiscoveryError("preview must remain non-persistent")
    if preview.get("status") not in {"ok", "partial", "failed"}:
        raise DiscoveryError("invalid discovery preview status")
    _validate_timestamp(preview.get("generated_at"), "generated_at")
    query = preview.get("query")
    if (
        not isinstance(query, str)
        or not query
        or query != " ".join(query.split())
        or len(query) > MAX_QUERY_CHARS
        or _contains_private_metadata(query)
    ):
        raise DiscoveryError("invalid discovery preview query")
    topic_id = preview.get("topic_id")
    if (
        not isinstance(topic_id, str)
        or len(topic_id) > 160
        or (topic_id and not _TOPIC_ID_RE.fullmatch(topic_id))
    ):
        raise DiscoveryError("invalid discovery preview topic_id")
    requested_providers = preview.get("requested_providers")
    if (
        not isinstance(requested_providers, list)
        or not requested_providers
        or len(requested_providers) != len(set(requested_providers))
        or any(
            not isinstance(provider, str) or not _PROVIDER_RE.fullmatch(provider)
            for provider in requested_providers
        )
    ):
        raise DiscoveryError("invalid requested discovery providers")
    candidates = preview.get("candidates")
    candidate_count = preview.get("candidate_count")
    if (
        not isinstance(candidates, list)
        or isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count != len(candidates)
        or len(candidates) > MAX_RESULTS_LIMIT
    ):
        raise DiscoveryError("preview candidate count mismatch")
    candidate_ids: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or set(candidate) != _CANDIDATE_KEYS:
            raise DiscoveryError("candidate contains fields outside the persistence allowlist")
        if candidate.get("schema") != DISCOVERY_CANDIDATE_SCHEMA:
            raise DiscoveryError("unsupported discovery candidate schema")
        if candidate.get("evidence_boundary") != "candidate-only" or candidate.get("promotion") != "none":
            raise DiscoveryError("discovery candidate cannot be promoted during discovery")
        if candidate.get("claim_readiness") != "not-ready":
            raise DiscoveryError("discovery candidate cannot be claim-ready")
        if candidate.get("dedupe_status") not in {"new", "existing", "ambiguous"}:
            raise DiscoveryError("invalid discovery candidate dedupe status")
        title = candidate.get("title")
        if (
            not isinstance(title, str)
            or not title
            or _safe_text(title, MAX_TITLE_CHARS) != title
        ):
            raise DiscoveryError("discovery candidate title is required")
        authors = candidate.get("authors")
        if (
            not isinstance(authors, list)
            or len(authors) > MAX_AUTHORS
            or any(
                not isinstance(author, str)
                or not author
                or _safe_text(author, MAX_AUTHOR_CHARS) != author
                for author in authors
            )
            or len(authors) != len(set(authors))
        ):
            raise DiscoveryError("invalid discovery candidate authors")
        year = candidate.get("year")
        if year is not None and (
            isinstance(year, bool)
            or not isinstance(year, int)
            or not 1800 <= year <= 2200
        ):
            raise DiscoveryError("invalid discovery candidate year")
        venue = candidate.get("venue")
        provider_id = candidate.get("provider_id")
        if (
            not isinstance(venue, str)
            or _safe_text(venue, MAX_VENUE_CHARS) != venue
            or not isinstance(provider_id, str)
            or _safe_text(provider_id, MAX_PROVIDER_ID_CHARS) != provider_id
        ):
            raise DiscoveryError("discovery candidate contains private or sensitive metadata")
        doi = candidate.get("doi")
        if (
            not isinstance(doi, str)
            or len(doi) > 300
            or (doi and _safe_doi(doi) != doi)
        ):
            raise DiscoveryError("invalid discovery candidate DOI")
        url = candidate.get("url")
        if not isinstance(url, str) or (url and _safe_url(url) != url):
            raise DiscoveryError("invalid or non-public discovery candidate URL")
        provider = candidate.get("provider")
        providers = candidate.get("providers")
        if (
            not isinstance(provider, str)
            or not _PROVIDER_RE.fullmatch(provider)
            or not isinstance(providers, list)
            or not providers
            or any(
                not isinstance(name, str) or not _PROVIDER_RE.fullmatch(name)
                for name in providers
            )
            or len(providers) != len(set(providers))
            or provider != providers[0]
            or provider not in providers
            or any(name not in requested_providers for name in providers)
        ):
            raise DiscoveryError("candidate primary provider is inconsistent")
        provider_ids = candidate.get("provider_ids")
        if (
            not isinstance(provider_ids, list)
            or any(
                not isinstance(value, str)
                or not value
                or len(value) > 340
                or _safe_text(value, 340) != value
                for value in provider_ids
            )
            or len(provider_ids) != len(set(provider_ids))
            or (provider_id and f"{provider}:{provider_id}" not in provider_ids)
        ):
            raise DiscoveryError("invalid candidate provider identity")
        if candidate.get("topic_id") != topic_id:
            raise DiscoveryError("candidate topic_id does not match preview")
        score = candidate.get("relevance_score")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or score < 0
        ):
            raise DiscoveryError("invalid candidate relevance score")
        if candidate.get("ranking_explanation") not in {
            "Provider-ranked bibliographic match; candidate only.",
            "Bibliographic match for the requested query; candidate only.",
        }:
            raise DiscoveryError("invalid candidate ranking explanation")
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not re.fullmatch(r"cand_[0-9a-f]{20}", candidate_id):
            raise DiscoveryError("invalid discovery candidate ID")
        expected_candidate_id = "cand_" + sha256(
            _identity_key(candidate).encode("utf-8")
        ).hexdigest()[:20]
        if candidate_id != expected_candidate_id:
            raise DiscoveryError("discovery candidate identity hash mismatch")
        if candidate_id in candidate_ids:
            raise DiscoveryError("duplicate discovery candidate ID")
        candidate_ids.add(candidate_id)
    provider_status = preview.get("provider_status")
    if (
        not isinstance(provider_status, list)
        or len(provider_status) != len(requested_providers)
    ):
        raise DiscoveryError("provider_status must be a list")
    provider_status_names: set[str] = set()
    for item in provider_status:
        if not isinstance(item, Mapping) or set(item) != _PROVIDER_STATUS_KEYS:
            raise DiscoveryError("provider status contains fields outside the persistence allowlist")
        status_provider = item.get("provider")
        if status_provider not in requested_providers or status_provider in provider_status_names:
            raise DiscoveryError("provider status does not match requested providers")
        provider_status_names.add(str(status_provider))
        item_status = item.get("status")
        error_code = item.get("error_code")
        count = item.get("count")
        if item_status not in {"ok", "error", "skipped"}:
            raise DiscoveryError("invalid provider status")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise DiscoveryError("invalid provider result count")
        if error_code not in {
            "",
            "PROVIDER_UNAVAILABLE",
            "PROVIDER_NOT_CONFIGURED",
            "OPENALEX_API_KEY_REQUIRED",
        }:
            raise DiscoveryError("invalid provider error code")
        if (item_status == "ok") != (error_code == ""):
            raise DiscoveryError("provider status and error code are inconsistent")
    successful = sum(item.get("status") == "ok" for item in provider_status)
    expected_status = (
        "ok"
        if successful == len(requested_providers)
        else "partial"
        if successful
        else "failed"
    )
    if preview.get("status") != expected_status:
        raise DiscoveryError("preview status is inconsistent with provider status")
    stored_hash = preview.get("preview_hash")
    if not isinstance(stored_hash, str) or not _HASH_RE.fullmatch(stored_hash):
        raise DiscoveryError("invalid discovery preview hash")
    if discovery_preview_hash(preview) != stored_hash:
        raise DiscoveryError("discovery preview hash mismatch")


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise DiscoveryError(f"{field} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DiscoveryError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise DiscoveryError(f"{field} must include a timezone")


def _validate_acceptance_state(
    state: Mapping[str, Any],
    *,
    run: Mapping[str, Any],
) -> None:
    if set(state) != _ACCEPTANCE_KEYS:
        raise DiscoveryError("acceptance state contains fields outside the persistence allowlist")
    if (
        state.get("schema") != DISCOVERY_ACCEPTANCE_SCHEMA
        or state.get("run_id") != run.get("run_id")
        or state.get("preview_hash") != run.get("preview_hash")
    ):
        raise DiscoveryError("invalid discovery acceptance state")
    _validate_timestamp(state.get("updated_at"), "updated_at")
    accepted = state.get("accepted")
    if not isinstance(accepted, list):
        raise DiscoveryError("accepted candidates must be a list")
    available_ids = {
        str(candidate.get("candidate_id"))
        for candidate in run.get("candidates", [])
        if isinstance(candidate, Mapping)
    }
    seen: set[str] = set()
    for item in accepted:
        if not isinstance(item, Mapping) or set(item) != _ACCEPTED_ITEM_KEYS:
            raise DiscoveryError("accepted candidate contains unallowlisted fields")
        candidate_id = item.get("candidate_id")
        if (
            not isinstance(candidate_id, str)
            or not re.fullmatch(r"cand_[0-9a-f]{20}", candidate_id)
            or candidate_id not in available_ids
            or candidate_id in seen
        ):
            raise DiscoveryError("accepted candidate does not belong to the discovery run")
        seen.add(candidate_id)
        if item.get("actor") not in {"human", "codex", "automation"}:
            raise DiscoveryError("invalid discovery acceptance actor")
        _validate_timestamp(item.get("accepted_at"), "accepted_at")


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _recorded_run_payload(preview: Mapping[str, Any], *, run_id: str, recorded_at: str) -> dict[str, Any]:
    return {
        "schema": DISCOVERY_RUN_SCHEMA,
        "run_id": run_id,
        "recorded_at": recorded_at,
        "generated_at": preview["generated_at"],
        "query": preview["query"],
        "topic_id": preview["topic_id"],
        "preview_hash": preview["preview_hash"],
        "status": preview["status"],
        "requested_providers": preview["requested_providers"],
        "provider_status": preview["provider_status"],
        "candidate_count": preview["candidate_count"],
        "candidates": preview["candidates"],
        "evidence_boundary": "candidate-only",
        "promotion": "none",
    }


def record_discovery_run(
    ws: Workspace,
    *,
    preview: Mapping[str, Any],
    expected_hash: str,
    recorded_at: str | None = None,
) -> dict[str, Any]:
    """Persist one exact, approved discovery preview without overwriting runs."""

    _validate_preview(preview)
    if not isinstance(expected_hash, str) or not _HASH_RE.fullmatch(expected_hash):
        raise DiscoveryError("expected discovery hash must be 64 lowercase hexadecimal characters")
    actual_hash = discovery_preview_hash(preview)
    if expected_hash != actual_hash or preview.get("preview_hash") != actual_hash:
        raise DiscoveryError("approved discovery preview hash mismatch")

    stamp = recorded_at or _utc_now()
    _validate_timestamp(stamp, "recorded_at")
    compact_stamp = re.sub(r"[^0-9TZ]", "", stamp).lower() or "unknown"
    base_id = f"run_{compact_stamp}_{slugify(str(preview['query']), 48)}_{actual_hash[:8]}"
    base_id = base_id[:160].rstrip("_")
    ws.paths.search_runs.mkdir(parents=True, exist_ok=True)
    suffix = 1
    while True:
        run_id = base_id if suffix == 1 else f"{base_id}_{suffix}"
        run_dir = ws.paths.search_runs / run_id
        try:
            run_dir.mkdir(exist_ok=False)
            break
        except FileExistsError:
            suffix += 1

    payload = _recorded_run_payload(preview, run_id=run_id, recorded_at=stamp)
    _atomic_write_json(run_dir / "candidates.json", payload)
    return {
        **payload,
        "run_path": f"state/search_runs/{run_id}/candidates.json",
    }


def _validated_run_id(run_id: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise DiscoveryError("invalid discovery run ID")
    return run_id


def load_discovery_run(ws: Workspace, run_id: str) -> dict[str, Any]:
    """Load one recorded candidate run by opaque run ID."""

    run_path = ws.paths.search_runs / _validated_run_id(run_id) / "candidates.json"
    if not run_path.exists():
        raise DiscoveryError(f"discovery run not found: {run_id}")
    payload = read_json(run_path)
    if (
        set(payload) != _RUN_KEYS
        or payload.get("schema") != DISCOVERY_RUN_SCHEMA
        or payload.get("run_id") != run_id
    ):
        raise DiscoveryError("invalid discovery run record")
    _validate_timestamp(payload.get("recorded_at"), "recorded_at")
    reconstructed = {
        "schema": DISCOVERY_PREVIEW_SCHEMA,
        "generated_at": payload["generated_at"],
        "query": payload["query"],
        "topic_id": payload["topic_id"],
        "requested_providers": payload["requested_providers"],
        "status": payload["status"],
        "provider_status": payload["provider_status"],
        "candidate_count": payload["candidate_count"],
        "candidates": payload["candidates"],
        "evidence_boundary": payload["evidence_boundary"],
        "promotion": payload["promotion"],
        "persistence": "none",
        "preview_hash": payload["preview_hash"],
    }
    _validate_preview(reconstructed)
    return payload


def select_run_candidates(
    run: Mapping[str, Any],
    candidate_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Return selected candidates in request order, rejecting unknown IDs."""

    requested = list(dict.fromkeys(candidate_ids))
    available = {
        str(candidate.get("candidate_id")): dict(candidate)
        for candidate in run.get("candidates", [])
        if isinstance(candidate, Mapping)
    }
    missing = [candidate_id for candidate_id in requested if candidate_id not in available]
    if missing:
        raise DiscoveryError("unknown candidate ID(s): " + ", ".join(missing))
    return [available[candidate_id] for candidate_id in requested]


def load_acceptance_state(ws: Workspace, run_id: str) -> dict[str, Any]:
    """Load acceptance state without modifying the immutable run record."""

    run = load_discovery_run(ws, run_id)
    path = ws.paths.search_runs / run_id / "acceptance.json"
    if not path.exists():
        return {
            "schema": DISCOVERY_ACCEPTANCE_SCHEMA,
            "run_id": run_id,
            "preview_hash": run["preview_hash"],
            "updated_at": "",
            "accepted": [],
        }
    try:
        state = read_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise DiscoveryError("invalid discovery acceptance state") from exc
    if not isinstance(state, Mapping):
        raise DiscoveryError("invalid discovery acceptance state")
    _validate_acceptance_state(state, run=run)
    return state


def mark_candidates_accepted(
    ws: Workspace,
    *,
    run_id: str,
    candidate_ids: Sequence[str],
    actor: str = "human",
    accepted_at: str | None = None,
) -> dict[str, Any]:
    """Idempotently mark selected run candidates as accepted.

    This helper records only candidate IDs, time, and an allowlisted actor.  It
    intentionally does not perform capture or claim promotion.
    """

    if actor not in {"human", "codex", "automation"}:
        raise DiscoveryError("acceptance actor must be human, codex, or automation")
    run = load_discovery_run(ws, run_id)
    selected = select_run_candidates(run, candidate_ids)
    if not selected:
        raise DiscoveryError("at least one candidate ID is required")
    state = load_acceptance_state(ws, run_id)
    accepted = {
        str(item["candidate_id"]): dict(item)
        for item in state.get("accepted", [])
        if isinstance(item, Mapping) and item.get("candidate_id")
    }
    stamp = accepted_at or _utc_now()
    _validate_timestamp(stamp, "accepted_at")
    added = 0
    for candidate in selected:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id not in accepted:
            accepted[candidate_id] = {
                "candidate_id": candidate_id,
                "accepted_at": stamp,
                "actor": actor,
            }
            added += 1
    if not added:
        return {
            **state,
            "added_count": 0,
            "accepted_count": len(accepted),
        }
    updated = {
        "schema": DISCOVERY_ACCEPTANCE_SCHEMA,
        "run_id": run_id,
        "preview_hash": run["preview_hash"],
        "updated_at": stamp,
        "accepted": sorted(accepted.values(), key=lambda item: item["candidate_id"]),
    }
    _atomic_write_json(ws.paths.search_runs / run_id / "acceptance.json", updated)
    return {
        **updated,
        "added_count": added,
        "accepted_count": len(updated["accepted"]),
    }


def discovery_status(ws: Workspace) -> dict[str, Any]:
    """Return aggregate, identity-free discovery run health."""

    run_count = 0
    candidate_count = 0
    accepted_count = 0
    malformed_run_count = 0
    latest_recorded_at = ""
    statuses: Counter[str] = Counter()
    providers: Counter[str] = Counter()
    if ws.paths.search_runs.exists():
        for path in sorted(ws.paths.search_runs.glob("run_*/candidates.json")):
            try:
                run = load_discovery_run(ws, path.parent.name)
                run_count += 1
                candidate_count += run["candidate_count"]
                statuses[str(run.get("status", "unknown"))] += 1
                latest_recorded_at = max(latest_recorded_at, str(run.get("recorded_at", "")))
                providers.update(str(name) for name in run.get("requested_providers", []))
                acceptance_path = path.parent / "acceptance.json"
                if acceptance_path.exists():
                    acceptance = load_acceptance_state(ws, str(run["run_id"]))
                    accepted_count += len(acceptance["accepted"])
            except (DiscoveryError, OSError, ValueError, TypeError, json.JSONDecodeError):
                malformed_run_count += 1
    return {
        "schema": "rkf-discovery-status-v1",
        "run_count": run_count,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "malformed_run_count": malformed_run_count,
        "latest_recorded_at": latest_recorded_at,
        "run_status_counts": dict(sorted(statuses.items())),
        "provider_run_counts": dict(sorted(providers.items())),
        "evidence_boundary": "candidate-only",
        "promotion": "none",
    }


__all__ = [
    "DISCOVERY_ACCEPTANCE_SCHEMA",
    "DISCOVERY_CANDIDATE_SCHEMA",
    "DISCOVERY_PREVIEW_SCHEMA",
    "DISCOVERY_RUN_SCHEMA",
    "DiscoveryError",
    "adapt_paper_radar",
    "discovery_preview_hash",
    "discovery_status",
    "fetch_arxiv",
    "fetch_crossref",
    "fetch_openalex",
    "load_acceptance_state",
    "load_discovery_run",
    "mark_candidates_accepted",
    "preview_discovery",
    "record_discovery_run",
    "select_run_candidates",
]
