#!/usr/bin/env python3
"""Run a bounded, private smoke corpus through the portable acquisition core."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import urllib.parse
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Sequence


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from rkf.acquisition import (  # noqa: E402
    AcquisitionPolicy,
    AcquisitionRequest,
    CanonicalIdentifierSet,
    ExternalPDFTextExtractor,
    PDFArtifactValidator,
    PortableScientificAcquisitionProvider,
    extract_identifiers_from_text,
)


REPORT_SCHEMA = "rkf-acquisition-smoke-report-v1"
ATMOSPHERIC_CORPUS_ID = "acquisition-issue-18-atmospheric-journal-live-smoke"
JSON_REPORT_NAME = "paper-fetch-results.json"
MARKDOWN_REPORT_NAME = "paper-fetch-results.md"
ARTIFACT_DIRECTORY_NAME = "artifacts"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "references",
        type=Path,
        help="one citation per line, or an earlier private smoke-report JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new private/temporary report directory outside the repository",
    )
    parser.add_argument("--contact-email", default=os.environ.get("RKF_CONTACT_EMAIL", ""))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--indices", default="", help="comma-separated 1-based citation indices")
    parser.add_argument("--external-qc-tools", action="store_true")
    parser.add_argument("--artifact-timeout", type=float, default=35.0)
    parser.add_argument("--metadata-timeout", type=float, default=12.0)
    return parser.parse_args(argv)


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _path_is_within(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _reject_symlink_components(path: Path) -> None:
    absolute = _absolute_path(path)
    allowed_system_aliases: set[Path] = set()
    if sys.platform == "darwin":
        for alias, canonical in (
            (Path("/var"), Path("/private/var")),
            (Path("/tmp"), Path("/private/tmp")),
        ):
            if alias.is_symlink() and alias.resolve() == canonical:
                allowed_system_aliases.add(alias)
    for component in (*reversed(absolute.parents), absolute):
        if component.is_symlink() and component not in allowed_system_aliases:
            raise ValueError(f"output path cannot contain symlinks: {component}")


def prepare_output_directory(path: Path) -> Path:
    """Create one private output root without following links or reusing targets."""

    output_dir = _absolute_path(path)
    _reject_symlink_components(output_dir)
    resolved_output = output_dir.resolve(strict=False)
    if _path_is_within(REPO.resolve(), resolved_output):
        raise ValueError("--output-dir must be outside the repository")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError("--output-dir must be a directory")
    for target in (
        output_dir / JSON_REPORT_NAME,
        output_dir / MARKDOWN_REPORT_NAME,
        output_dir / ARTIFACT_DIRECTORY_NAME,
    ):
        if target.is_symlink() or target.exists():
            raise FileExistsError(f"refusing to overwrite existing smoke target: {target.name}")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    _reject_symlink_components(output_dir)
    if not output_dir.is_dir():
        raise ValueError("--output-dir is invalid")
    os.chmod(output_dir, 0o700)
    return output_dir


def write_private_text(path: Path, text: str) -> None:
    """Create one owner-only report atomically with no overwrite or symlink follow."""

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            descriptor = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)
        raise


def load_indexed_citations(path: Path) -> tuple[list[tuple[int, str]], str]:
    """Load line citations, the public atmospheric corpus, or a prior smoke run."""

    input_path = _absolute_path(path)
    if not input_path.is_file():
        raise ValueError("references input must be a readable file")
    text = input_path.read_text(encoding="utf-8")
    if input_path.suffix.lower() != ".json":
        citations = [line.strip() for line in text.splitlines() if line.strip()]
        if not citations:
            raise ValueError("references input contains no citations")
        return list(enumerate(citations, 1)), "citation-lines"

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("smoke JSON input is invalid") from error
    if not isinstance(payload, dict):
        raise ValueError("JSON acquisition input must be an object")
    if payload.get("corpus_id") == ATMOSPHERIC_CORPUS_ID:
        raw_cases = payload.get("cases")
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ValueError("atmospheric journal corpus has no cases")
        indexed_cases: list[tuple[int, str]] = []
        seen_dois: set[str] = set()
        for index, raw_case in enumerate(raw_cases, 1):
            if not isinstance(raw_case, dict):
                raise ValueError("atmospheric journal corpus cases must be objects")
            doi = raw_case.get("doi")
            if not isinstance(doi, str) or not doi.strip():
                raise ValueError("atmospheric journal corpus case DOI is required")
            normalized = CanonicalIdentifierSet.resolve([doi.strip()]).primary
            if normalized.identifier_type != "doi":
                raise ValueError("atmospheric journal corpus cases must use DOI identifiers")
            if normalized.value in seen_dois:
                raise ValueError("atmospheric journal corpus DOI values must be unique")
            seen_dois.add(normalized.value)
            alternate_identifiers = raw_case.get("alternate_identifiers", [])
            if not isinstance(alternate_identifiers, list) or not all(
                isinstance(item, str) and item.strip()
                for item in alternate_identifiers
            ):
                raise ValueError(
                    "atmospheric journal corpus alternate_identifiers must be strings"
                )
            serialized_alternates: list[str] = []
            for raw_identifier in alternate_identifiers:
                identifier = raw_identifier.strip()
                if re.search(r"\s", identifier):
                    parsed_identifier = urllib.parse.urlsplit(identifier)
                    if parsed_identifier.scheme.lower() not in {"http", "https"}:
                        raise ValueError(
                            "atmospheric journal corpus typed identifiers cannot contain whitespace"
                        )
                    identifier = urllib.parse.urlunsplit(
                        (
                            parsed_identifier.scheme,
                            parsed_identifier.netloc,
                            urllib.parse.quote(
                                parsed_identifier.path,
                                safe="/%:@!$&'()*+,;=-._~",
                            ),
                            urllib.parse.quote(
                                parsed_identifier.query,
                                safe="=&;%:@/?+,-._~",
                            ),
                            urllib.parse.quote(
                                parsed_identifier.fragment,
                                safe="=&;%:@/?+,-._~",
                            ),
                        )
                    )
                serialized_alternates.append(identifier)
            expected_identifiers = CanonicalIdentifierSet.resolve(
                [normalized.value, *serialized_alternates]
            )
            citation = " ".join(
                [normalized.value, *serialized_alternates]
            )
            extracted_identifiers = CanonicalIdentifierSet.resolve(
                extract_identifiers_from_text(citation)
            )
            if extracted_identifiers.identifiers != expected_identifiers.identifiers:
                raise ValueError(
                    "atmospheric journal corpus identifiers are not losslessly extractable"
                )
            indexed_cases.append((index, citation))
        return indexed_cases, "atmospheric-journal-corpus"
    if payload.get("schema") != REPORT_SCHEMA:
        raise ValueError(
            f"JSON acquisition input must be corpus {ATMOSPHERIC_CORPUS_ID} "
            f"or schema {REPORT_SCHEMA}"
        )
    raw_results = payload.get("results")
    if not isinstance(raw_results, list) or not raw_results:
        raise ValueError("smoke JSON input has no results to rerun")
    indexed: list[tuple[int, str]] = []
    seen: set[int] = set()
    for raw in raw_results:
        if not isinstance(raw, dict):
            raise ValueError("smoke JSON results must be objects")
        index = raw.get("index")
        citation = raw.get("citation")
        if isinstance(index, bool) or not isinstance(index, int) or index < 1:
            raise ValueError("smoke JSON result index must be a positive integer")
        if index in seen:
            raise ValueError("smoke JSON result indexes must be unique")
        if not isinstance(citation, str) or not citation.strip():
            raise ValueError("smoke JSON result citation is required for rerun")
        seen.add(index)
        indexed.append((index, citation.strip()))
    indexed.sort(key=lambda item: item[0])
    return indexed, "smoke-report-json"


def parse_indices(value: str) -> set[int]:
    if not value:
        return set()
    tokens = value.split(",")
    if any(not re.fullmatch(r"[1-9][0-9]*", token.strip()) for token in tokens):
        raise ValueError("--indices must be comma-separated positive integers")
    return {int(token.strip()) for token in tokens}


def select_indexed_citations(
    indexed_citations: Sequence[tuple[int, str]],
    *,
    indices: str,
    limit: int,
) -> list[tuple[int, str]]:
    if limit < 0:
        raise ValueError("--limit cannot be negative")
    selected_indices = parse_indices(indices)
    available = {index for index, _ in indexed_citations}
    missing = selected_indices - available
    if missing:
        missing_text = ", ".join(str(item) for item in sorted(missing))
        raise ValueError(f"--indices not present in input: {missing_text}")
    selected = [
        item for item in indexed_citations if not selected_indices or item[0] in selected_indices
    ]
    if limit:
        selected = selected[:limit]
    if not selected:
        raise ValueError("selection contains no citations")
    return selected


def validate_runtime_arguments(args: argparse.Namespace) -> None:
    if not 1 <= args.workers <= 4:
        raise ValueError("--workers must be between 1 and 4")
    if args.limit < 0:
        raise ValueError("--limit cannot be negative")
    for name in ("artifact_timeout", "metadata_timeout"):
        value = float(getattr(args, name))
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"--{name.replace('_', '-')} must be a positive finite number")


def expected_title_from_citation(citation: str, identifiers: Sequence[str]) -> str:
    title_context = citation
    for identifier in identifiers:
        title_context = title_context.replace(identifier, " ")
    title_context = re.sub(r"\s+", " ", title_context).strip(" .,:;()[]")
    return title_context if len(title_context.split()) >= 4 else ""


def is_downloaded(result: dict[str, Any]) -> bool:
    return bool(
        result.get("status") == "obtained"
        and result.get("pdf_magic_validated") is True
        and re.fullmatch(r"[a-f0-9]{64}", str(result.get("artifact_sha256", "")))
        and result.get("private_artifact_available") is True
    )


def is_research_ready_verified(result: dict[str, Any]) -> bool:
    return bool(
        is_downloaded(result)
        and result.get("quality_state") == "readable"
        and result.get("identity_state") == "verified"
        and result.get("text_layer_state") == "available"
        and result.get("locator_readiness") == "ready"
        and isinstance(result.get("page_count"), int)
        and result.get("page_count", 0) > 0
    )


def classify_result(result: dict[str, Any]) -> dict[str, Any]:
    result["downloaded"] = is_downloaded(result)
    result["research_ready_verified"] = is_research_ready_verified(result)
    return result


def build_summary(
    results: Sequence[dict[str, Any]],
    *,
    input_kind: str,
    input_source_count: int,
    contact_email_configured: bool,
    external_qc_tools: bool,
) -> dict[str, Any]:
    normalized_results = [classify_result(dict(item)) for item in results]
    status_counts = Counter(
        str(item.get("status") or "unknown") for item in normalized_results
    )
    route_counts = Counter(
        str(item["route"]) for item in normalized_results if item.get("route")
    )
    provider_status: dict[str, Counter[str]] = defaultdict(Counter)
    for item in normalized_results:
        provider = str(item.get("provider") or "not-run")
        provider_status[provider][str(item.get("status") or "unknown")] += 1
    return {
        "schema": REPORT_SCHEMA,
        "input_kind": input_kind,
        "input_source_count": input_source_count,
        "source_count": len(normalized_results),
        "identifier_count": sum(
            bool(item.get("identifier")) for item in normalized_results
        ),
        "downloaded_count": sum(
            bool(item.get("downloaded")) for item in normalized_results
        ),
        "research_ready_verified_count": sum(
            bool(item.get("research_ready_verified"))
            for item in normalized_results
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "route_counts": dict(sorted(route_counts.items())),
        "provider_status_counts": {
            provider: dict(sorted(counts.items()))
            for provider, counts in sorted(provider_status.items())
        },
        "contact_email_configured": contact_email_configured,
        "external_qc_tools": external_qc_tools,
        "promotion": "none",
        "results": normalized_results,
    }


def recommendation(result: dict[str, Any]) -> str:
    blockers = set(result.get("blocker_codes", []))
    status = result.get("status")
    if "UNPAYWALL_EMAIL_NOT_CONFIGURED" in blockers:
        return (
            "設定 RKF_CONTACT_EMAIL 後重跑 Unpaywall；"
            "現有其他 OA routes 仍已測試。"
        )
    if status == "retryable":
        return (
            "依 provider retry class 做有限度 serial retry；"
            "若持續 429，延長 backoff。"
        )
    if status == "manual-required":
        return (
            "使用圖書館 resolver、ILL，或由使用者提供合法 PDF；"
            "不要把此狀態記為 unavailable。"
        )
    if status == "not-entitled":
        return (
            "確認 holdings coverage，改走 ILL/OA manuscript；"
            "不要重試 institution route。"
        )
    if status == "identity-mismatch":
        return (
            "人工核對首頁 DOI/title；拒絕註冊目前 artifact，"
            "並修正 route/landing metadata。"
        )
    if status == "invalid-artifact":
        return (
            "檢查是否抓到 viewer/HTML/supplement、檔案截斷或需要 OCR；"
            "修正 route 後重試。"
        )
    if status == "provider-error":
        return (
            "保存 provider/status evidence，更新 adapter fixture 或等待 provider 修復。"
        )
    if status == "unavailable":
        return (
            "新增合法 publisher/repository adapter，"
            "或改用 resolver/ILL/user-provided artifact。"
        )
    if status == "blocked":
        return "檢查 URL safety/policy 或本機 adapter 設定；不可繞過 access control。"
    return "人工檢查。"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_runtime_arguments(args)
        all_indexed_citations, input_kind = load_indexed_citations(args.references)
        indexed_citations = select_indexed_citations(
            all_indexed_citations,
            indices=args.indices,
            limit=args.limit,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise SystemExit(str(error)) from error
    extractor = ExternalPDFTextExtractor() if args.external_qc_tools else None
    validator = PDFArtifactValidator(
        text_extractor=extractor if extractor and extractor.available else None
    )
    try:
        policy = AcquisitionPolicy(
            artifact_timeout_s=args.artifact_timeout,
            metadata_timeout_s=args.metadata_timeout,
        )
        provider = PortableScientificAcquisitionProvider(
            contact_email=args.contact_email,
            storage_root=_absolute_path(args.output_dir)
            / ARTIFACT_DIRECTORY_NAME,
            policy=policy,
            validator=validator,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    try:
        output_dir = prepare_output_directory(args.output_dir)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    corpus_fingerprint = hashlib.sha256(
        "\n".join(f"{index}\t{citation}" for index, citation in indexed_citations).encode(
            "utf-8"
        )
    ).hexdigest()
    project_id = "prj_" + corpus_fingerprint[:24]
    activation_id = "act_" + uuid.uuid4().hex[:24]

    def run(index: int, citation: str) -> dict[str, Any]:
        identifiers = extract_identifiers_from_text(citation)
        if not identifiers:
            return classify_result(
                {
                    "index": index,
                    "citation": citation,
                    "identifier": "",
                    "status": "manual-required",
                    "blocker_codes": ["IDENTIFIER_MISSING"],
                    "recommendation": (
                        "補 DOI、官方 URL、repository ID 或 report identifier，"
                        "再執行 acquisition。"
                    ),
                }
            )
        identifier = identifiers[0]
        canonical_identifiers = CanonicalIdentifierSet.resolve(identifiers)
        expected_title = expected_title_from_citation(citation, identifiers)
        source_id = "src_" + hashlib.sha256(identifier.encode()).hexdigest()[:20]
        try:
            result = provider.acquire(
                AcquisitionRequest(
                    identifiers=canonical_identifiers,
                    source_id=source_id,
                    expected_title=expected_title,
                    project_id=project_id,
                    activation_id=activation_id,
                )
            ).public_payload()
        except Exception as error:  # smoke report must keep the rest of the corpus running
            result = {
                "status": "provider-error",
                "provider": provider.name,
                "provider_version": provider.version,
                "blocker_codes": ["UNHANDLED_PROVIDER_EXCEPTION"],
                "diagnostic": type(error).__name__,
            }
        result.update({"index": index, "citation": citation, "identifier": identifier})
        if result.get("status") != "obtained":
            result["recommendation"] = recommendation(result)
        return classify_result(result)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run, index, citation): index
            for index, citation in indexed_citations
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                json.dumps(
                    {
                        "index": result["index"],
                        "status": result["status"],
                        "identifier": result["identifier"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    results.sort(key=lambda item: item["index"])
    summary = build_summary(
        results,
        input_kind=input_kind,
        input_source_count=len(all_indexed_citations),
        contact_email_configured=bool(args.contact_email),
        external_qc_tools=bool(extractor and extractor.available),
    )
    json_path = output_dir / JSON_REPORT_NAME
    lines = [
        "# RKF Paper Acquisition Smoke Report",
        "",
        f"- Citations: {len(indexed_citations)}",
        f"- Identifiers: {summary['identifier_count']}",
        f"- Downloaded: {summary['downloaded_count']}",
        f"- Research-ready verified: {summary['research_ready_verified_count']}",
        "- Status counts: "
        f"`{json.dumps(summary['status_counts'], ensure_ascii=False, sort_keys=True)}`",
        "- Selected route counts: "
        f"`{json.dumps(summary['route_counts'], ensure_ascii=False, sort_keys=True)}`",
        "- Provider/status counts: "
        f"`{json.dumps(summary['provider_status_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- Unpaywall contact configured: `{summary['contact_email_configured']}`",
        f"- External PDF QC tools: `{summary['external_qc_tools']}`",
        "- Promotion: `none`",
        "",
        "## Downloaded but not research-ready verified",
        "",
    ]
    for item in results:
        if not item["downloaded"] or item["research_ready_verified"]:
            continue
        lines.extend(
            [
                f"### {item['index']}. {item['identifier']}",
                "",
                f"- Quality: `{item.get('quality_state', 'unknown')}`",
                f"- Identity: `{item.get('identity_state', 'unverified')}`",
                f"- Locator readiness: `{item.get('locator_readiness', 'unknown')}`",
                f"- Citation: {item['citation']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Not downloaded",
            "",
        ]
    )
    for item in results:
        if item["downloaded"]:
            continue
        lines.extend(
            [
                f"### {item['index']}. {item['identifier'] or 'identifier missing'}",
                "",
                f"- Status: `{item['status']}`",
                f"- Blockers: `{', '.join(item.get('blocker_codes', [])) or 'none'}`",
                f"- Action: {item.get('recommendation', recommendation(item))}",
                f"- Citation: {item['citation']}",
                "",
            ]
        )
    markdown_path = output_dir / MARKDOWN_REPORT_NAME
    try:
        write_private_text(
            json_path,
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        )
        write_private_text(markdown_path, "\n".join(lines))
    except OSError as error:
        raise SystemExit(f"failed to write private smoke report: {type(error).__name__}") from error
    print(
        json.dumps(
            {
                "report": json_path.name,
                "markdown": markdown_path.name,
                "downloaded_count": summary["downloaded_count"],
                "research_ready_verified_count": summary[
                    "research_ready_verified_count"
                ],
                "status_counts": summary["status_counts"],
                "route_counts": summary["route_counts"],
                "provider_status_counts": summary["provider_status_counts"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
