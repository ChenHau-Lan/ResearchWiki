"""Portable, policy-aware scientific artifact acquisition for RKF.

The default provider uses only open/public metadata and artifact routes.  It has
no institutional credentials, browser profile, CAPTCHA flow, or paywall-bypass
behavior.  Browser/subscription automation remains an explicitly configured
external adapter.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import sqlite3
import stat
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence

from .core import extract_doi, normalize_doi
from .lineage import ACTIVATION_ID_RE, PROJECT_ID_RE
from .providers import AcquisitionAttempt, FullTextProviderResult


DOI_EXACT_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
PDF_DOI_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9])10\.\d{4,9}/\S+",
    re.IGNORECASE,
)
ARXIV_RE = re.compile(r"^(?:arxiv:)?(?P<value>\d{4}\.\d{4,5}(?:v\d+)?)$", re.IGNORECASE)
ADS_RE = re.compile(r"^(?:ads:)?(?P<value>\d{4}[A-Za-z0-9.&]{14}[A-Za-z0-9.])$", re.IGNORECASE)
NTRS_RE = re.compile(r"^(?:ntrs:)?(?P<value>\d{8,})$", re.IGNORECASE)
PRIVATE_HOST_NAMES = {"localhost", "localhost.localdomain", "metadata.google.internal"}
RFC6052_WELL_KNOWN_PREFIX = ipaddress.ip_network("64:ff9b::/96")
RFC8215_LOCAL_USE_TRANSLATION_PREFIX = ipaddress.ip_network("64:ff9b:1::/48")
KNOWN_REPOSITORY_HOSTS = {
    "oceanrep.geomar.de",
}
IDENTIFIER_TYPES = {
    "doi",
    "url",
    "arxiv",
    "ads-bibcode",
    "eartharxiv",
    "osf-preprint",
    "ess-open-archive",
    "datacite-doi",
    "handle",
    "nasa-ntrs",
    "noaa-report",
    "wmo-report",
    "ipcc-report",
    "repository",
    "report",
}
ARTIFACT_RELATION_KEYS = {"relationship", "artifact_type", "host", "identifier"}
MAX_LANDING_PDF_DEPTH = 4
MAX_IDENTIFIERS_PER_REQUEST = 8
DEFAULT_MAX_CANDIDATE_REQUESTS = 32


@dataclass(frozen=True)
class ProviderRouteProfile:
    key: str
    publisher: str
    prefixes: tuple[str, ...]
    selection: str
    policy_note: str


ATMOSPHERIC_P0_PROFILES: tuple[ProviderRouteProfile, ...] = (
    ProviderRouteProfile("agu-wiley", "AGU/Wiley", ("10.1029", "10.1002"), "metadata-host-then-prefix-hint", "OA metadata first; Wiley TDM only with a user token."),
    ProviderRouteProfile("ams", "American Meteorological Society", ("10.1175",), "landing-citation-meta", "Official DOI landing and citation metadata; no access-control bypass."),
    ProviderRouteProfile("copernicus", "Copernicus/EGU", ("10.5194",), "verified-open-template", "Official OA article PDF template."),
    ProviderRouteProfile("elsevier", "Elsevier", ("10.1016",), "metadata-host-then-prefix-hint", "OA metadata first; Article Retrieval API only with a user API key."),
    ProviderRouteProfile("springer-nature", "Springer Nature", ("10.1007", "10.1186", "10.1038"), "official-oa-or-landing", "Official OA direct path where applicable, then DOI landing metadata."),
    ProviderRouteProfile("iop", "IOP", ("10.1088",), "landing-citation-meta", "Official DOI landing metadata; no access-control bypass."),
    ProviderRouteProfile("acs", "American Chemical Society", ("10.1021",), "landing-citation-meta", "Official DOI landing metadata; no access-control bypass."),
    ProviderRouteProfile("aaas", "AAAS", ("10.1126",), "landing-citation-meta", "Official DOI landing metadata; no access-control bypass."),
    ProviderRouteProfile("taylor-francis", "Taylor & Francis", ("10.1080",), "landing-citation-meta", "Official DOI landing metadata; no access-control bypass."),
)

ATMOSPHERIC_P1_PROFILES: tuple[ProviderRouteProfile, ...] = (
    ProviderRouteProfile("mdpi", "MDPI", ("10.3390",), "official-oa-landing", "Official OA landing metadata and article-level license evidence."),
    ProviderRouteProfile("frontiers", "Frontiers", ("10.3389",), "official-oa-or-landing", "Official OA PDF/HTML where exposed; no robots or access-control bypass."),
    ProviderRouteProfile("j-stage", "J-STAGE", ("10.2151",), "official-oa-landing", "Official J-STAGE landing metadata and article-level license evidence."),
)


def provider_profile_for_doi(doi: str) -> ProviderRouteProfile | None:
    normalized = normalize_doi(doi)
    prefix = normalized.partition("/")[0]
    return next(
        (
            profile
            for profile in (*ATMOSPHERIC_P0_PROFILES, *ATMOSPHERIC_P1_PROFILES)
            if prefix in profile.prefixes
        ),
        None,
    )


@dataclass(frozen=True)
class CanonicalIdentifier:
    identifier_type: str
    value: str

    def __post_init__(self) -> None:
        if self.identifier_type not in IDENTIFIER_TYPES:
            raise ValueError(f"unsupported identifier type: {self.identifier_type}")
        if not self.value.strip() or len(self.value) > 2048:
            raise ValueError("identifier value is empty or too long")


@dataclass(frozen=True)
class CanonicalIdentifierSet:
    identifiers: tuple[CanonicalIdentifier, ...]

    def __post_init__(self) -> None:
        if not self.identifiers:
            raise ValueError("at least one identifier is required")
        if len(self.identifiers) > MAX_IDENTIFIERS_PER_REQUEST:
            raise ValueError(
                f"at most {MAX_IDENTIFIERS_PER_REQUEST} identifiers are allowed per request"
            )
        doi_values = {
            normalize_doi(item.value)
            for item in self.identifiers
            if item.identifier_type in {"doi", "datacite-doi"}
        }
        if len(doi_values) > 1:
            raise ValueError("identifier conflict: multiple DOI values require review")

    @classmethod
    def resolve(cls, values: Sequence[str]) -> "CanonicalIdentifierSet":
        resolved: list[CanonicalIdentifier] = []
        seen: set[tuple[str, str]] = set()
        for raw in values:
            item = resolve_identifier(raw)
            key = (item.identifier_type, item.value)
            if key not in seen:
                seen.add(key)
                resolved.append(item)
        return cls(tuple(resolved))

    @property
    def primary(self) -> CanonicalIdentifier:
        return self.identifiers[0]

    def first(self, *identifier_types: str) -> CanonicalIdentifier | None:
        return next(
            (item for item in self.identifiers if item.identifier_type in identifier_types),
            None,
        )


def resolve_identifier(raw: str) -> CanonicalIdentifier:
    """Normalize one DOI, URL, preprint, ADS, Handle, or report identifier."""

    value = str(raw).strip().strip("\"'")
    if not value:
        raise ValueError("identifier is required")
    lowered = value.lower()
    prefixed_types = (
        (("eartharxiv:", "earth-arxiv:"), "eartharxiv"),
        (("osf:", "osf-preprint:"), "osf-preprint"),
        (("ess:", "essoar:", "ess-open-archive:"), "ess-open-archive"),
        (("noaa:", "noaa-report:"), "noaa-report"),
        (("wmo:", "wmo-report:"), "wmo-report"),
        (("ipcc:", "ipcc-report:"), "ipcc-report"),
    )
    for prefixes, identifier_type in prefixed_types:
        prefix = next((item for item in prefixes if lowered.startswith(item)), "")
        if not prefix:
            continue
        identifier_value = value[len(prefix) :].strip()
        if identifier_value.lower().startswith(("https://doi.org/", "http://doi.org/")):
            identifier_value = urllib.parse.unquote(
                urllib.parse.urlsplit(identifier_value).path.lstrip("/")
            )
        if not identifier_value or len(identifier_value) > 512:
            raise ValueError(f"invalid {identifier_type} identifier")
        if identifier_type == "ipcc-report":
            identifier_value = re.sub(r"[-_/\s]+", "-", identifier_value).lower().strip("-")
        return CanonicalIdentifier(identifier_type, identifier_value)
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() in {"http", "https"}:
        host = (parsed.hostname or "").lower()
        if host in {"doi.org", "dx.doi.org"}:
            doi = urllib.parse.unquote(parsed.path.lstrip("/"))
            normalized_doi = normalize_doi(doi)
            if DOI_EXACT_RE.fullmatch(normalized_doi):
                return CanonicalIdentifier("doi", normalized_doi)
        doi = urllib.parse.unquote(extract_doi(value))
        if host in {"arxiv.org", "export.arxiv.org"}:
            match = re.search(r"/(?:abs|pdf)/([^/?#]+)", parsed.path, re.IGNORECASE)
            if match:
                return CanonicalIdentifier("arxiv", match.group(1).removesuffix(".pdf"))
        if host == "ntrs.nasa.gov":
            match = re.search(r"/(?:citations|api/citations)/([^/?#]+)", parsed.path)
            if match:
                return CanonicalIdentifier("nasa-ntrs", match.group(1))
        if host in {"ui.adsabs.harvard.edu", "adsabs.harvard.edu"}:
            match = re.search(r"/(?:abs|link_gateway)/([^/?#]+)", parsed.path, re.IGNORECASE)
            if match and ADS_RE.fullmatch(urllib.parse.unquote(match.group(1))):
                return CanonicalIdentifier("ads-bibcode", urllib.parse.unquote(match.group(1)))
        if host == "eartharxiv.org":
            match = re.search(r"/repository/(?:view|object)/(\d+)", parsed.path, re.IGNORECASE)
            if match:
                return CanonicalIdentifier("eartharxiv", match.group(1))
        if host in {"osf.io", "api.osf.io"}:
            match = re.search(r"/(?:v2/)?preprints/(?:[^/]+/)?([^/?#]+)", parsed.path, re.IGNORECASE)
            if match:
                identifier_type = "eartharxiv" if "/eartharxiv/" in parsed.path.lower() else "osf-preprint"
                return CanonicalIdentifier(identifier_type, match.group(1))
        if host == "repository.library.noaa.gov":
            match = re.search(r"/view/noaa/(\d+)", parsed.path, re.IGNORECASE)
            if match:
                return CanonicalIdentifier("noaa-report", match.group(1))
        if host in {"hdl.handle.net", "handle.net"}:
            return CanonicalIdentifier("handle", parsed.path.strip("/"))
        if (
            host in KNOWN_REPOSITORY_HOSTS
            or host.startswith("digitalcommons.")
            or any(
                token in host
                for token in ("osf.io", "eartharxiv", "essoar", "zenodo.org")
            )
        ):
            return CanonicalIdentifier("repository", value)
        return CanonicalIdentifier("url", value)
    normalized = urllib.parse.unquote(normalize_doi(value))
    if DOI_EXACT_RE.fullmatch(normalized):
        return CanonicalIdentifier("doi", normalized)
    arxiv = ARXIV_RE.fullmatch(value)
    if arxiv:
        return CanonicalIdentifier("arxiv", arxiv.group("value"))
    ads = ADS_RE.fullmatch(value)
    if ads:
        return CanonicalIdentifier("ads-bibcode", ads.group("value"))
    ntrs = NTRS_RE.fullmatch(value)
    if value.lower().startswith("ntrs:") and ntrs:
        return CanonicalIdentifier("nasa-ntrs", ntrs.group("value"))
    if value.lower().startswith("report:"):
        return CanonicalIdentifier("report", value.split(":", 1)[1].strip())
    raise ValueError(f"unsupported or ambiguous identifier: {value}")


def extract_identifiers_from_text(text: str) -> list[str]:
    """Extract explicit URLs or typed identifiers without guessing a missing ID."""

    values: list[str] = []
    patterns = (
        r"https?://\S+",
        r"(?<![A-Za-z0-9-])(?:ads|eartharxiv|earth-arxiv|osf|osf-preprint|ess|essoar|ess-open-archive|noaa|noaa-report|wmo|wmo-report|ipcc|ipcc-report|report):[^\s,]+",
        r"(?<![A-Za-z0-9])10\.\d{4,9}/[^\s<>\"']+",
        r"(?<![A-Za-z0-9-])arxiv:\d{4}\.\d{4,5}(?:v\d+)?",
        r"(?<![A-Za-z0-9-])ntrs:\d{8,}",
    )
    matches = [match for pattern in patterns for match in re.finditer(pattern, text, re.IGNORECASE)]
    for match in sorted(matches, key=lambda item: item.start()):
        value = match.group(0).rstrip(".,")
        try:
            resolve_identifier(value)
        except ValueError:
            continue
        if value not in values:
            values.append(value)
    return values


@dataclass(frozen=True)
class AcquisitionRequest:
    identifiers: CanonicalIdentifierSet
    project_id: str
    activation_id: str
    source_id: str
    desired_artifacts: tuple[str, ...] = ("version-of-record-pdf", "accepted-manuscript", "preprint")
    policy_profile: str = "portable-oa"
    expected_title: str = ""

    def __post_init__(self) -> None:
        if not PROJECT_ID_RE.fullmatch(self.project_id) or not ACTIVATION_ID_RE.fullmatch(
            self.activation_id
        ):
            raise ValueError("acquisition request requires valid project/activation lineage")
        if not self.source_id.strip():
            raise ValueError("acquisition request requires source_id")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", self.policy_profile):
            raise ValueError("invalid acquisition policy profile")


@dataclass(frozen=True)
class AcquisitionPolicy:
    metadata_timeout_s: float = 12.0
    artifact_timeout_s: float = 35.0
    max_metadata_bytes: int = 5 * 1024 * 1024
    max_html_bytes: int = 4 * 1024 * 1024
    max_artifact_bytes: int = 64 * 1024 * 1024
    min_pdf_bytes: int = 1000
    max_candidates: int = 24
    max_candidate_requests: int = DEFAULT_MAX_CANDIDATE_REQUESTS
    courtesy_interval_s: float = 0.15
    skip_not_entitled: bool = False

    def __post_init__(self) -> None:
        if min(self.metadata_timeout_s, self.artifact_timeout_s) <= 0:
            raise ValueError("acquisition timeouts must be positive")
        if min(self.max_metadata_bytes, self.max_html_bytes, self.max_artifact_bytes) <= 0:
            raise ValueError("acquisition byte limits must be positive")
        if (
            self.min_pdf_bytes < 8
            or self.max_candidates < 2
            or self.max_candidate_requests < 1
            or self.courtesy_interval_s < 0
        ):
            raise ValueError("acquisition policy limits are invalid")


@dataclass
class _CandidateRequestBudget:
    """Shared bound for artifact/landing HTTP requests in one acquisition."""

    limit: int
    used: int = 0
    denied: bool = False

    def consume(self) -> bool:
        if self.used >= self.limit:
            self.denied = True
            return False
        self.used += 1
        return True


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    url: str
    headers: dict[str, str]
    body: bytes


def _normalized_http_headers(headers: Any) -> dict[str, str]:
    """Lowercase response headers while preserving repeated Link fields."""

    normalized = {
        str(key).lower(): str(value)
        for key, value in (headers.items() if headers is not None else [])
    }
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        link_values = [str(value) for value in (get_all("Link") or []) if value]
        if link_values:
            normalized["link"] = ", ".join(link_values)
    return normalized


class HTTPClient(Protocol):
    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout_s: float,
        max_bytes: int,
    ) -> HTTPResponse: ...


class HTTPTransportError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class ResponseTooLargeError(HTTPTransportError):
    pass


class _NonPublicIPAddressError(ValueError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class UrllibHTTPClient:
    """Bounded HTTP client with validated, secret-safe redirect handling.

    The default opener deliberately ignores environment proxy settings so that
    the socket peer checked below is the destination selected by urllib, not a
    proxy that could resolve the destination independently.  Custom openers are
    accepted for testing/integration, but must expose a standard-library style
    socket peer; otherwise requests fail closed before the response body is
    read.
    """

    REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
    PUBLIC_HEADERS = frozenset({"accept", "accept-encoding", "referer", "user-agent"})

    def __init__(self, *, opener: Any | None = None, max_redirects: int = 5) -> None:
        if max_redirects < 0 or max_redirects > 10:
            raise ValueError("max_redirects must be between 0 and 10")
        self.opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler(),
        )
        self.max_redirects = max_redirects

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int]:
        parsed = urllib.parse.urlsplit(url)
        scheme = parsed.scheme.lower()
        port = parsed.port or (443 if scheme == "https" else 80)
        return scheme, (parsed.hostname or "").lower().rstrip("."), port

    @classmethod
    def _origin_referer(cls, value: str) -> str:
        """Return a credential-free, path-free Referer origin or an empty value."""

        try:
            scheme, host, port = cls._origin(value)
        except ValueError:
            return ""
        if scheme not in {"http", "https"} or not host:
            return ""
        rendered_host = f"[{host}]" if ":" in host else host
        default_port = 443 if scheme == "https" else 80
        netloc = rendered_host if port == default_port else f"{rendered_host}:{port}"
        return f"{scheme}://{netloc}/"

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        timeout_s: float,
        max_bytes: int,
    ) -> HTTPResponse:
        current_url = _quote_http_url(url)
        request_headers: dict[str, str] = {}
        for name, value in headers.items():
            if name.lower() == "referer":
                safe_referer = self._origin_referer(str(value))
                if safe_referer:
                    request_headers[name] = safe_referer
            else:
                request_headers[name] = value
        secret_headers = {
            name.lower()
            for name in request_headers
            if name.lower() not in self.PUBLIC_HEADERS
        }
        if secret_headers and urllib.parse.urlsplit(current_url).scheme.lower() != "https":
            raise HTTPTransportError(
                "AUTHENTICATED_INSECURE_INITIAL_URL",
                retryable=False,
            )
        for redirect_count in range(self.max_redirects + 1):
            _validate_public_url(current_url, resolve_dns=True)
            request = urllib.request.Request(
                current_url,
                headers=request_headers,
                method="GET",
            )
            try:
                with self.opener.open(request, timeout=timeout_s) as response:
                    _validate_urllib_peer(response)
                    final_url = _quote_http_url(str(response.geturl()))
                    _validate_public_url(final_url, resolve_dns=True)
                    if (
                        urllib.parse.urlsplit(current_url).scheme.lower() == "https"
                        and urllib.parse.urlsplit(final_url).scheme.lower() != "https"
                    ):
                        raise HTTPTransportError(
                            "INSECURE_REDIRECT",
                            retryable=False,
                        )
                    if secret_headers and self._origin(final_url) != self._origin(current_url):
                        raise HTTPTransportError(
                            "AUTHENTICATED_CROSS_ORIGIN_RESPONSE",
                            retryable=False,
                        )
                    body = response.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        raise ResponseTooLargeError("response exceeded configured byte limit")
                    return HTTPResponse(
                        status=int(response.status),
                        url=final_url,
                        headers=_normalized_http_headers(response.headers),
                        body=body,
                    )
            except urllib.error.HTTPError as error:
                _validate_urllib_peer(error)
                response_headers = _normalized_http_headers(error.headers)
                location = response_headers.get("location", "")
                if int(error.code) in self.REDIRECT_STATUSES and location:
                    if redirect_count >= self.max_redirects:
                        raise HTTPTransportError("HTTP_REDIRECT_LIMIT", retryable=False) from error
                    next_url = _quote_http_url(
                        urllib.parse.urljoin(current_url, location)
                    )
                    _validate_public_url(next_url, resolve_dns=True)
                    if (
                        urllib.parse.urlsplit(current_url).scheme.lower() == "https"
                        and urllib.parse.urlsplit(next_url).scheme.lower() != "https"
                    ):
                        raise HTTPTransportError(
                            "INSECURE_REDIRECT",
                            retryable=False,
                        ) from error
                    if secret_headers and self._origin(next_url) != self._origin(current_url):
                        raise HTTPTransportError(
                            "AUTHENTICATED_CROSS_ORIGIN_REDIRECT",
                            retryable=False,
                        ) from error
                    if self._origin(next_url) != self._origin(current_url):
                        request_headers = {
                            name: value
                            for name, value in request_headers.items()
                            if name.lower() != "referer"
                        }
                    current_url = next_url
                    continue
                body = error.read(min(max_bytes, 256 * 1024))
                return HTTPResponse(
                    status=int(error.code),
                    url=str(error.geturl()),
                    headers=response_headers,
                    body=body,
                )
            except HTTPTransportError:
                raise
            except (TimeoutError, urllib.error.URLError, OSError) as error:
                raise HTTPTransportError(type(error).__name__) from error
        raise HTTPTransportError("HTTP_REDIRECT_LIMIT", retryable=False)


def _embedded_ipv4_addresses(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> tuple[ipaddress.IPv4Address, ...]:
    """Return IPv4 addresses carried by recognized IPv6 transition formats."""

    if not isinstance(address, ipaddress.IPv6Address):
        return ()
    embedded: list[ipaddress.IPv4Address] = []
    if address.ipv4_mapped is not None:
        embedded.append(address.ipv4_mapped)
    if address.sixtofour is not None:
        embedded.append(address.sixtofour)
    if address.teredo is not None:
        embedded.extend(address.teredo)
    if address in RFC6052_WELL_KNOWN_PREFIX:
        embedded.append(ipaddress.IPv4Address(int(address) & 0xFFFFFFFF))
    return tuple(dict.fromkeys(embedded))


def _validate_public_ip_address(
    value: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Parse one IP and reject non-global outer or embedded destinations."""

    address = ipaddress.ip_address(str(value).split("%", 1)[0])
    if (
        isinstance(address, ipaddress.IPv6Address)
        and address in RFC8215_LOCAL_USE_TRANSLATION_PREFIX
    ) or not address.is_global or any(
        not embedded.is_global for embedded in _embedded_ipv4_addresses(address)
    ):
        raise _NonPublicIPAddressError(str(address))
    return address


def _validate_urllib_peer(response: Any) -> str:
    """Validate the socket peer exposed by urllib before reading a body.

    CPython's urllib response wrappers vary slightly across HTTP, HTTPS, and
    HTTPError paths.  Walk only the known wrapper/socket attributes used by the
    standard library.  An uninspectable response is rejected rather than
    falling back to the earlier DNS answer, which would reintroduce a DNS
    rebinding time-of-check/time-of-use gap.
    """

    pending: list[tuple[Any, int]] = [(response, 0)]
    seen: set[int] = set()
    while pending:
        candidate, depth = pending.pop(0)
        if candidate is None or id(candidate) in seen:
            continue
        seen.add(id(candidate))
        getpeername = getattr(candidate, "getpeername", None)
        if callable(getpeername):
            try:
                peer = getpeername()
            except OSError:
                peer = None
            if peer:
                value = peer[0] if isinstance(peer, tuple) else peer
                try:
                    address = _validate_public_ip_address(str(value))
                except _NonPublicIPAddressError as error:
                    raise HTTPTransportError(
                        "NON_PUBLIC_PEER_ADDRESS",
                        retryable=False,
                    ) from error
                except ValueError as error:
                    raise HTTPTransportError(
                        "PEER_ADDRESS_INVALID",
                        retryable=False,
                    ) from error
                return str(address)
        if depth >= 4:
            continue
        for attribute in ("fp", "raw", "_sock", "sock", "_connection"):
            nested = getattr(candidate, attribute, None)
            if nested is not None:
                pending.append((nested, depth + 1))
    raise HTTPTransportError("PEER_ADDRESS_UNAVAILABLE", retryable=False)


def _quote_http_url(url: str) -> str:
    """Percent-encode raw spaces/non-ASCII without altering existing escapes."""

    parsed = urllib.parse.urlsplit(str(url).strip())
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            urllib.parse.quote(
                parsed.path,
                safe="/%:@!$&'()*+,;=-._~",
            ),
            urllib.parse.quote(
                parsed.query,
                safe="=&;%:@/?+,-._~",
            ),
            urllib.parse.quote(parsed.fragment, safe="=&;%:@/?+,-._~"),
        )
    )


def _validate_public_url(url: str, *, resolve_dns: bool = False) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() not in {"https", "http"} or not parsed.hostname:
        raise ValueError("artifact route must be an HTTP(S) URL")
    host = parsed.hostname.lower().rstrip(".")
    if parsed.username or parsed.password or host in PRIVATE_HOST_NAMES or host.endswith((".local", ".internal")):
        raise ValueError("artifact route points to a private or credential-bearing host")
    try:
        address = _validate_public_ip_address(host.strip("[]"))
    except _NonPublicIPAddressError as error:
        raise ValueError("artifact route points to a non-public IP address") from error
    except ValueError:
        address = None
    if resolve_dns and address is None:
        try:
            resolved = {
                item[4][0]
                for item in socket.getaddrinfo(
                    host,
                    parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        except socket.gaierror as error:
            raise HTTPTransportError("PUBLIC_HOST_RESOLUTION_FAILED") from error
        if not resolved:
            raise HTTPTransportError("PUBLIC_HOST_RESOLUTION_EMPTY")
        for value in resolved:
            try:
                _validate_public_ip_address(value)
            except _NonPublicIPAddressError as error:
                raise ValueError(
                    "artifact route resolved to a non-public IP address"
                ) from error
            except ValueError as error:
                raise HTTPTransportError("PUBLIC_HOST_RESOLUTION_INVALID") from error
    return host


def _json_payload(response: HTTPResponse) -> dict[str, Any]:
    try:
        payload = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("metadata provider returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("metadata provider returned a non-object JSON payload")
    return payload


def _pdf_urls_from_link_header(value: str) -> tuple[str, ...]:
    """Extract bounded Signposting/RFC 8288 PDF item targets.

    Repository migrations often leave old landing URLs pointing at a new
    DSpace entity whose stable file relation is an HTTP ``Link`` header.
    Accept only explicit ``rel=item`` plus ``type=application/pdf`` entries;
    the normal URL, transport, size, and PDF identity gates still apply.
    """

    header = str(value or "")[:65536]
    targets: list[str] = []
    links = list(re.finditer(r"<([^<>]+)>", header))[:16]
    for index, link in enumerate(links):
        tail_end = links[index + 1].start() if index + 1 < len(links) else len(header)
        parameters = header[link.end() : tail_end]
        rel_match = re.search(
            r";\s*rel\s*=\s*(?:\"([^\"]*)\"|([^;,\s]+))",
            parameters,
            re.IGNORECASE,
        )
        type_match = re.search(
            r";\s*type\s*=\s*(?:\"([^\"]*)\"|([^;,\s]+))",
            parameters,
            re.IGNORECASE,
        )
        rel_value = (rel_match.group(1) or rel_match.group(2) or "") if rel_match else ""
        type_value = (type_match.group(1) or type_match.group(2) or "") if type_match else ""
        if (
            "item" in {token.lower() for token in rel_value.split()}
            and type_value.partition(";")[0].strip().lower() == "application/pdf"
        ):
            target = link.group(1).strip()
            dspace_content = _dspace_bitstream_content_url(target)
            for candidate in (dspace_content, target):
                if candidate and candidate not in targets:
                    targets.append(candidate)
    return tuple(targets)


def _dspace_bitstream_content_url(value: str) -> str:
    """Map a public DSpace front-end bitstream link to its same-origin REST file."""

    parsed = urllib.parse.urlsplit(value)
    match = re.fullmatch(
        r"/bitstreams/([0-9a-fA-F-]{36})/download/?",
        parsed.path,
    )
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or not match:
        return ""
    try:
        bitstream_id = str(uuid.UUID(match.group(1)))
    except ValueError:
        return ""
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            f"/server/api/core/bitstreams/{bitstream_id}/content",
            "",
            "",
        )
    )


def _pdf_text_contains_exact_doi(text: str, expected_doi: str) -> bool:
    """Match one complete DOI token, allowing only terminal citation punctuation.

    A prefix check is unsafe because punctuation such as ``.`` and ``)`` is
    valid inside a DOI.  Extract the whole DOI-shaped token first, then compare
    normalized values exactly.  An unmatched terminal closing parenthesis is
    treated as citation punctuation; a balanced parenthesis remains part of
    the DOI.
    """

    expected = normalize_doi(urllib.parse.unquote(expected_doi))
    if not expected:
        return False
    for match in PDF_DOI_TOKEN_RE.finditer(text):
        candidate = normalize_doi(urllib.parse.unquote(match.group(0)))
        if candidate == expected:
            return True
        # The token starts at the DOI, so an unmatched closing wrapper at its
        # end belongs to the surrounding citation. Balanced delimiters remain
        # part of the DOI (including legacy AMS angle-bracket suffixes).
        closing_pairs = {")": "(", "]": "[", "}": "{", ">": "<"}
        while candidate:
            closing = candidate[-1]
            opening = closing_pairs.get(closing)
            if opening and candidate.count(closing) > candidate.count(opening):
                candidate = normalize_doi(candidate[:-1])
            elif closing in {'"', "'"}:
                candidate = normalize_doi(candidate[:-1])
            else:
                break
            if candidate == expected:
                return True
    return False


def _pmc_cloud_https_url(value: str) -> str:
    """Map a current PMC Open Data S3 object URI to its anonymous HTTPS URL."""

    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() != "s3" or parsed.netloc != "pmc-oa-opendata":
        return ""
    path_parts = tuple(part for part in parsed.path.split("/") if part)
    if not path_parts or any(part in {".", ".."} for part in path_parts):
        return ""
    return urllib.parse.urlunsplit(
        (
            "https",
            "pmc-oa-opendata.s3.amazonaws.com",
            "/" + urllib.parse.quote("/".join(path_parts), safe="/-._~"),
            parsed.query,
            "",
        )
    )


def _crossref_artifact_provenance(content_version: object) -> tuple[str, str]:
    """Return a conservative RKF type/version for a Crossref full-text link."""

    normalized = str(content_version or "").strip().lower().replace("_", "-")
    if normalized in {"vor", "version-of-record", "publishedversion"}:
        return "version-of-record-pdf", "version-of-record"
    if normalized in {"am", "accepted-manuscript", "acceptedversion"}:
        return "accepted-manuscript", "accepted-manuscript"
    return "pdf", "unknown"


def _crossref_license_start_timestamp(license_item: dict[str, Any]) -> float | None:
    """Parse Crossref's license start value without treating an unknown date as active."""

    start = license_item.get("start")
    if not isinstance(start, dict):
        return None
    timestamp = start.get("timestamp")
    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
        # Crossref REST timestamps are milliseconds since the Unix epoch.
        return float(timestamp) / 1000.0
    date_time = start.get("date-time")
    if isinstance(date_time, str) and date_time.strip():
        try:
            parsed = datetime.fromisoformat(date_time.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    date_parts = start.get("date-parts")
    if (
        isinstance(date_parts, list)
        and date_parts
        and isinstance(date_parts[0], list)
        and date_parts[0]
    ):
        parts = date_parts[0]
        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return datetime(year, month, day, tzinfo=timezone.utc).timestamp()
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def _crossref_license_for_version(
    licenses: object,
    artifact_version: str,
    *,
    now: float | None = None,
) -> str:
    """Select the latest active license explicitly scoped to one artifact version."""

    if artifact_version not in {
        "version-of-record",
        "accepted-manuscript",
    }:
        return ""
    wanted = {
        "version-of-record": "vor",
        "accepted-manuscript": "am",
    }[artifact_version]
    current_time = time.time() if now is None else now
    matches: list[tuple[float, str]] = []
    for item in licenses if isinstance(licenses, list) else []:
        if not isinstance(item, dict):
            continue
        targets = [
            str(item.get(key) or "").strip().lower().replace("_", "-")
            for key in ("content-version", "applies-to")
            if item.get(key)
        ]
        normalized_targets = {
            {
                "version-of-record": "vor",
                "publishedversion": "vor",
                "accepted-manuscript": "am",
                "acceptedversion": "am",
            }.get(target, target)
            for target in targets
        }
        # Unscoped, conflicting, TDM-only, and otherwise unknown licenses are
        # not evidence that this particular downloadable artifact is licensed.
        if normalized_targets != {wanted}:
            continue
        start_timestamp = _crossref_license_start_timestamp(item)
        url = str(item.get("URL") or item.get("url") or "").strip()
        if not url or start_timestamp is None or start_timestamp > current_time:
            continue
        matches.append((start_timestamp, url))
    if not matches:
        return ""
    latest_start = max(start for start, _url in matches)
    latest_urls = {url for start, url in matches if start == latest_start}
    return next(iter(latest_urls)) if len(latest_urls) == 1 else ""


def _current_pmc_version(record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Select the documented current PMC version, or the latest listed version."""

    base_pmcid = str(record.get("pmcid") or "").strip().upper().partition(".")[0]
    if not re.fullmatch(r"PMC\d+", base_pmcid):
        return "", {}
    versions = record.get("versions")
    version_items = [item for item in versions if isinstance(item, dict)] if isinstance(versions, list) else []
    parsed: list[tuple[int, dict[str, Any], str]] = []
    for item in version_items:
        pmcid = str(item.get("pmcid") or "").strip().upper()
        match = re.fullmatch(r"PMC\d+\.(\d+)", pmcid)
        if match and pmcid.rpartition(".")[0] == base_pmcid:
            parsed.append((int(match.group(1)), item, pmcid))
    if not parsed:
        return "", {}
    current = [
        entry
        for entry in parsed
        if entry[1].get("current") is True
        or str(entry[1].get("current") or "").strip().lower() == "true"
    ]
    _version_number, selected, pmcid = max(
        current or parsed,
        key=lambda entry: entry[0],
    )
    return pmcid, selected


class _CitationMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.pdf_links: list[str] = []
        self.repository_pdf_links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        if tag.lower() == "record" and values.get("license"):
            self.meta.setdefault("repository_license", []).append(
                values["license"].strip()
            )
        if tag.lower() == "meta":
            name = (values.get("name") or values.get("property") or "").lower()
            content = values.get("content", "").strip()
            if name and content:
                self.meta.setdefault(name, []).append(content)
        if tag.lower() == "link" and (
            "pdf" in values.get("type", "").lower()
            or values.get("format", "").lower() == "pdf"
        ):
            if values.get("href"):
                self.pdf_links.append(values["href"])
        if tag.lower() == "a" and values.get("href"):
            href = values["href"].strip()
            href_path = urllib.parse.urlsplit(href).path.lower()
            if href_path.endswith(".pdf") or "pdf" in values.get("type", "").lower():
                self.repository_pdf_links.append(href)


def _dedupe_related(items: Iterable[dict[str, str]]) -> tuple[dict[str, str], ...]:
    unique: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
    for item in items:
        if set(item) <= ARTIFACT_RELATION_KEYS:
            key = tuple(sorted((str(name), str(value)) for name, value in item.items()))
            unique.setdefault(key, dict(item))
    return tuple(unique.values())


@dataclass(frozen=True)
class AcquisitionCandidate:
    route: str
    url: str
    kind: str = "pdf"
    artifact_type: str = "pdf"
    artifact_version: str = "unknown"
    license: str = ""
    referer: str = ""
    secret_name: str = ""
    secret_header: str = ""
    optional_secret_name: str = ""
    optional_secret_header: str = ""
    allow_repository_links: bool = False


class IdentifierAdapter(Protocol):
    """Resolve one canonical identifier type into official artifact candidates."""

    identifier_types: frozenset[str]

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]: ...


class IdentifierAdapterRegistry:
    """Capability registry; duplicate ownership of an identifier fails closed."""

    def __init__(self, adapters: Sequence[IdentifierAdapter]) -> None:
        self._by_type: dict[str, IdentifierAdapter] = {}
        for adapter in adapters:
            for identifier_type in adapter.identifier_types:
                if identifier_type not in IDENTIFIER_TYPES:
                    raise ValueError(f"adapter registered unsupported identifier type: {identifier_type}")
                if identifier_type in self._by_type:
                    raise ValueError(f"multiple adapters registered for {identifier_type}")
                self._by_type[identifier_type] = adapter

    def for_type(self, identifier_type: str) -> IdentifierAdapter | None:
        return self._by_type.get(identifier_type)

    @property
    def identifier_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_type))


class ADSBibcodeIdentifierAdapter:
    identifier_types = frozenset({"ads-bibcode"})

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        bibcode = identifier.value
        encoded = urllib.parse.quote(bibcode, safe=".&")
        candidates = [
            AcquisitionCandidate(
                "ads-eprint-gateway",
                f"https://ui.adsabs.harvard.edu/link_gateway/{encoded}/EPRINT_PDF",
                "pdf",
                "preprint",
                "preprint",
            )
        ]
        metadata: dict[str, Any] = {"title": "", "doi": "", "registry": "ads"}
        token = provider.secret_provider.get("ADS_API_TOKEN") if provider.secret_provider else None
        if token:
            query = urllib.parse.urlencode(
                {
                    "q": f'bibcode:"{bibcode}"',
                    "fl": "bibcode,title,doi,identifier,property,esources",
                    "rows": "1",
                }
            )
            payload = provider._metadata_get(
                f"https://api.adsabs.harvard.edu/v1/search/query?{query}",
                route="ads-api-identity",
                attempts=attempts,
                extra_headers={"Authorization": f"Bearer {token}"},
            )
            response = payload.get("response") if isinstance(payload.get("response"), dict) else {}
            docs = response.get("docs") if isinstance(response.get("docs"), list) else []
            doc = docs[0] if docs and isinstance(docs[0], dict) else {}
            titles = doc.get("title") if isinstance(doc.get("title"), list) else []
            metadata["title"] = str(titles[0]) if titles else str(doc.get("title") or "")
            doi_values = doc.get("doi") if isinstance(doc.get("doi"), list) else [doc.get("doi")]
            resolved_doi = next(
                (
                    normalize_doi(str(item))
                    for item in doi_values
                    if item and DOI_EXACT_RE.fullmatch(normalize_doi(str(item)))
                ),
                "",
            )
            if resolved_doi:
                doi_candidates, doi_metadata = provider._discover_doi(
                    resolved_doi,
                    attempts=attempts,
                )
                metadata = {**doi_metadata, **{key: value for key, value in metadata.items() if value}}
                candidates.extend(doi_candidates)
        candidates.extend(
            (
                AcquisitionCandidate(
                    "ads-publisher-gateway",
                    f"https://ui.adsabs.harvard.edu/link_gateway/{encoded}/PUB_PDF",
                    "pdf",
                    "version-of-record-pdf",
                    "version-of-record",
                ),
                AcquisitionCandidate(
                    "ads-abstract-landing",
                    f"https://ui.adsabs.harvard.edu/abs/{encoded}/abstract",
                    "landing",
                ),
            )
        )
        return candidates, metadata


class OSFPreprintIdentifierAdapter:
    identifier_types = frozenset({"osf-preprint"})

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        record_id = identifier.value
        encoded = urllib.parse.quote(record_id, safe="_-.")
        payload = provider._metadata_get(
            f"https://api.osf.io/v2/preprints/{encoded}/",
            route="osf-preprint-identity",
            attempts=attempts,
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        attributes = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
        links = data.get("links") if isinstance(data.get("links"), dict) else {}
        relationships = data.get("relationships") if isinstance(data.get("relationships"), dict) else {}
        doi_url = str(links.get("preprint_doi") or attributes.get("doi") or "")
        doi = normalize_doi(doi_url) if DOI_EXACT_RE.fullmatch(normalize_doi(doi_url)) else ""
        metadata: dict[str, Any] = {
            "title": str(attributes.get("title") or ""),
            "doi": doi,
            "registry": "osf-preprints",
            "license": "",
        }
        candidates: list[AcquisitionCandidate] = []
        html = str(links.get("html") or f"https://osf.io/preprints/{encoded}/")
        if attributes.get("date_withdrawn"):
            provider._attempt(
                attempts,
                route="osf-preprint-identity",
                status="manual-required",
                started=time.monotonic(),
                reason="PREPRINT_WITHDRAWN",
                host="api.osf.io",
            )
            return [AcquisitionCandidate("osf-preprint-landing", html, "landing", "preprint", "preprint")], metadata
        primary = relationships.get("primary_file") if isinstance(relationships.get("primary_file"), dict) else {}
        primary_links = primary.get("links") if isinstance(primary.get("links"), dict) else {}
        related = primary_links.get("related") if isinstance(primary_links.get("related"), dict) else {}
        file_api = str(related.get("href") or "")
        if file_api:
            file_payload = provider._metadata_get(
                file_api,
                route="osf-primary-file",
                attempts=attempts,
            )
            file_data = file_payload.get("data") if isinstance(file_payload.get("data"), dict) else {}
            file_attributes = file_data.get("attributes") if isinstance(file_data.get("attributes"), dict) else {}
            file_links = file_data.get("links") if isinstance(file_data.get("links"), dict) else {}
            download = str(file_links.get("download") or "")
            filename = str(file_attributes.get("name") or "")
            if download and (filename.lower().endswith(".pdf") or not filename):
                candidates.append(
                    AcquisitionCandidate(
                        "osf-primary-file",
                        download,
                        "pdf",
                        "preprint",
                        "preprint",
                    )
                )
        candidates.append(
            AcquisitionCandidate(
                "osf-preprint-landing",
                html,
                "landing",
                "preprint",
                "preprint",
            )
        )
        return candidates, metadata


class EarthArXivIdentifierAdapter:
    identifier_types = frozenset({"eartharxiv"})

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        value = identifier.value
        doi = normalize_doi(value)
        if DOI_EXACT_RE.fullmatch(doi):
            candidates, metadata = provider._discover_doi(doi, attempts=attempts)
            metadata["registry"] = "eartharxiv-datacite"
            return candidates, metadata
        if value.isdigit():
            return [
                AcquisitionCandidate(
                    "eartharxiv-janeway-landing",
                    f"https://eartharxiv.org/repository/view/{value}/",
                    "landing",
                    "preprint",
                    "preprint",
                )
            ], {"title": "", "doi": "", "registry": "eartharxiv-janeway"}
        candidates, metadata = OSFPreprintIdentifierAdapter().discover(
            provider,
            CanonicalIdentifier("osf-preprint", value),
            attempts=attempts,
        )
        metadata["registry"] = "eartharxiv-osf"
        return candidates, metadata


class ESSOpenArchiveIdentifierAdapter:
    identifier_types = frozenset({"ess-open-archive"})

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        doi = normalize_doi(identifier.value)
        if DOI_EXACT_RE.fullmatch(doi) and "/essoar." in doi.lower():
            candidates, metadata = provider._discover_doi(doi, attempts=attempts)
            metadata["registry"] = "ess-open-archive"
            return candidates, metadata
        provider._attempt(
            attempts,
            route="ess-open-archive-identity",
            status="manual-required",
            started=time.monotonic(),
            reason="ESSOAR_DOI_REQUIRED",
            host="essopenarchive.org",
        )
        return [], {"title": "", "doi": "", "registry": "ess-open-archive"}


class NOAAReportIdentifierAdapter:
    identifier_types = frozenset({"noaa-report"})

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        value = identifier.value
        doi = normalize_doi(value)
        if DOI_EXACT_RE.fullmatch(doi):
            candidates, metadata = provider._discover_doi(doi, attempts=attempts)
            metadata["registry"] = "noaa-doi"
            return candidates, metadata
        match = re.fullmatch(r"(?:noaa:)?(\d+)", value, re.IGNORECASE)
        if not match:
            provider._attempt(
                attempts,
                route="noaa-ir-identity",
                status="manual-required",
                started=time.monotonic(),
                reason="NOAA_IR_PID_OR_DOI_REQUIRED",
                host="repository.library.noaa.gov",
            )
            return [], {"title": "", "doi": "", "registry": "noaa-ir"}
        pid = match.group(1)
        base = f"https://repository.library.noaa.gov/view/noaa/{pid}"
        return [
            AcquisitionCandidate("noaa-ir-landing", base, "landing", "pdf", "unknown"),
            AcquisitionCandidate(
                "noaa-ir-main-pdf",
                f"{base}/noaa_{pid}_DS1.pdf",
                "pdf",
                "pdf",
                "unknown",
            ),
        ], {"title": "", "doi": "", "registry": "noaa-ir"}


class WMOReportIdentifierAdapter:
    identifier_types = frozenset({"wmo-report"})

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        value = identifier.value.strip()
        doi = normalize_doi(value)
        if DOI_EXACT_RE.fullmatch(doi):
            candidates, metadata = provider._discover_doi(doi, attempts=attempts)
            metadata["registry"] = "wmo-doi"
            return candidates, metadata
        normalized = re.sub(r"[_\s]+", "-", value.lower()).strip("-")
        if re.fullmatch(r"state-of-global-climate-\d{4}", normalized):
            url = (
                "https://public.wmo.int/publication-series/state-of-global-climate/"
                + normalized
            )
            route = "wmo-publication-series"
        elif normalized.isdigit():
            url = f"https://library.wmo.int/records/item/{normalized}"
            route = "wmo-library-record"
        else:
            url = "https://wmo.int/search?" + urllib.parse.urlencode(
                {"search_api_fulltext": value}
            )
            route = "wmo-official-search"
        return [AcquisitionCandidate(route, url, "landing", "report", "version-of-record")], {
            "title": "",
            "doi": "",
            "registry": "wmo",
        }


class IPCCReportIdentifierAdapter:
    identifier_types = frozenset({"ipcc-report"})
    REPORTS = {
        "ar6-wg1": (
            "Climate Change 2021: The Physical Science Basis",
            "https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_FullReport.pdf",
            "https://www.ipcc.ch/report/ar6/wg1/",
        ),
        "ar6-wg2": (
            "Climate Change 2022: Impacts, Adaptation and Vulnerability",
            "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_FullReport.pdf",
            "https://www.ipcc.ch/report/ar6/wg2/",
        ),
        "ar6-wg3": (
            "Climate Change 2022: Mitigation of Climate Change",
            "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_Full_Report.pdf",
            "https://www.ipcc.ch/report/ar6/wg3/",
        ),
        "ar6-syr": (
            "Climate Change 2023: Synthesis Report",
            "https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_FullVolume.pdf",
            "https://www.ipcc.ch/report/ar6/syr/",
        ),
    }
    ALIASES = {"ar6-wgi": "ar6-wg1", "ar6-wgii": "ar6-wg2", "ar6-wgiii": "ar6-wg3"}

    def discover(
        self,
        provider: "PortableScientificAcquisitionProvider",
        identifier: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        doi = normalize_doi(identifier.value)
        if DOI_EXACT_RE.fullmatch(doi):
            candidates, metadata = provider._discover_doi(doi, attempts=attempts)
            metadata["registry"] = "ipcc-doi"
            return candidates, metadata
        key = self.ALIASES.get(identifier.value.lower(), identifier.value.lower())
        report = self.REPORTS.get(key)
        if report is None:
            provider._attempt(
                attempts,
                route="ipcc-report-registry",
                status="manual-required",
                started=time.monotonic(),
                reason="IPCC_REPORT_ID_NOT_REGISTERED",
                host="www.ipcc.ch",
            )
            return [
                AcquisitionCandidate(
                    "ipcc-official-search",
                    "https://www.ipcc.ch/?" + urllib.parse.urlencode({"s": identifier.value}),
                    "landing",
                    "report",
                    "unknown",
                )
            ], {"title": "", "doi": "", "registry": "ipcc"}
        title, pdf_url, landing_url = report
        return [
            AcquisitionCandidate(
                "ipcc-full-report",
                pdf_url,
                "pdf",
                "report",
                "version-of-record",
            ),
            AcquisitionCandidate(
                "ipcc-report-landing",
                landing_url,
                "landing",
                "report",
                "version-of-record",
            ),
        ], {"title": title, "doi": "", "registry": "ipcc"}


def default_identifier_adapters() -> tuple[IdentifierAdapter, ...]:
    return (
        ADSBibcodeIdentifierAdapter(),
        OSFPreprintIdentifierAdapter(),
        EarthArXivIdentifierAdapter(),
        ESSOpenArchiveIdentifierAdapter(),
        NOAAReportIdentifierAdapter(),
        WMOReportIdentifierAdapter(),
        IPCCReportIdentifierAdapter(),
    )


@dataclass(frozen=True)
class ArtifactQualityResult:
    quality_state: str
    identity_state: str
    page_count: int
    text_layer_state: str
    locator_readiness: str
    mime_type: str = "application/pdf"
    blocker_codes: tuple[str, ...] = ()


class PDFTextExtractor(Protocol):
    def inspect(self, content: bytes) -> tuple[str, int, bool]: ...


class ExternalPDFTextExtractor:
    """Optional local QC using pdfinfo/pdftotext; never required by RKF core."""

    def __init__(self, *, pdfinfo: str = "pdfinfo", pdftotext: str = "pdftotext") -> None:
        self.pdfinfo = shutil.which(pdfinfo) or ""
        self.pdftotext = shutil.which(pdftotext) or ""

    @property
    def available(self) -> bool:
        return bool(self.pdfinfo and self.pdftotext)

    def inspect(self, content: bytes) -> tuple[str, int, bool]:
        if not self.available:
            return "", 0, False
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "artifact.pdf"
            pdf.write_bytes(content)
            info = subprocess.run(
                [self.pdfinfo, str(pdf)],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            page_match = re.search(r"^Pages:\s+(\d+)", info.stdout, re.MULTILINE)
            encrypted = bool(re.search(r"^Encrypted:\s+yes", info.stdout, re.MULTILINE | re.I))
            text = subprocess.run(
                [self.pdftotext, "-f", "1", "-l", "3", str(pdf), "-"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return text.stdout if text.returncode == 0 else "", int(page_match.group(1)) if page_match else 0, encrypted


class PDFArtifactValidator:
    def __init__(self, *, min_bytes: int = 1000, text_extractor: PDFTextExtractor | None = None) -> None:
        self.min_bytes = min_bytes
        self.text_extractor = text_extractor

    def validate(self, content: bytes, *, expected_doi: str = "", expected_title: str = "") -> ArtifactQualityResult:
        blockers: list[str] = []
        if len(content) < self.min_bytes or not content.startswith(b"%PDF-"):
            return ArtifactQualityResult(
                "corrupt", "unverified", 0, "unknown", "not-ready", blocker_codes=("PDF_MAGIC_OR_SIZE_INVALID",)
            )
        if b"%%EOF" not in content[-8192:]:
            return ArtifactQualityResult(
                "corrupt", "unverified", 0, "unknown", "not-ready", blocker_codes=("PDF_EOF_MISSING",)
            )
        page_count = len(re.findall(rb"/Type\s*/Page(?!s)\b", content))
        encrypted = b"/Encrypt" in content
        extracted_text = ""
        if self.text_extractor is not None:
            try:
                extracted_text, external_pages, external_encrypted = self.text_extractor.inspect(content)
                page_count = external_pages or page_count
                encrypted = encrypted or external_encrypted
            except (OSError, RuntimeError, subprocess.SubprocessError):
                blockers.append("PDF_EXTERNAL_QC_FAILED")
        if encrypted:
            blockers.append("PDF_ENCRYPTED")
        normalized_text = re.sub(r"\s+", " ", extracted_text).lower()
        text_layer_state = "available" if len(normalized_text) >= 80 else "missing" if self.text_extractor is not None else "unknown"
        identity_state = "unverified"
        doi_present = bool(
            normalized_text
            and expected_doi
            and _pdf_text_contains_exact_doi(normalized_text, expected_doi)
        )
        if doi_present:
            identity_state = "verified"
        elif normalized_text and expected_title:
            stopwords = {
                "about",
                "across",
                "after",
                "against",
                "among",
                "analysis",
                "and",
                "article",
                "based",
                "between",
                "case",
                "during",
                "effect",
                "effects",
                "for",
                "from",
                "impact",
                "into",
                "over",
                "study",
                "that",
                "the",
                "their",
                "this",
                "through",
                "under",
                "using",
                "with",
            }
            title_words = re.findall(r"[a-z0-9]+", expected_title.lower())
            normalized_title = " ".join(title_words)
            normalized_text_words = re.findall(r"[a-z0-9]+", normalized_text)
            text_words = set(normalized_text_words)
            title_tokens = tuple(
                dict.fromkeys(
                    token
                    for token in title_words
                    if len(token) >= 4 and token not in stopwords
                )
            )
            overlap = sum(token in text_words for token in title_tokens)
            coverage = overlap / len(title_tokens) if title_tokens else 0.0
            exact_title = bool(
                normalized_title
                and normalized_title in " ".join(normalized_text_words)
            )
            enough_tokens = (
                (len(title_tokens) >= 5 and overlap >= 4 and coverage >= 0.65)
                or (3 <= len(title_tokens) <= 4 and overlap >= 3 and coverage >= 0.75)
            )
            if exact_title or enough_tokens:
                identity_state = "verified"
            elif len(normalized_text) >= 1000 and (
                overlap == 0
                or (len(title_tokens) >= 5 and coverage < 0.35)
            ):
                identity_state = "mismatch"
                blockers.append("PDF_IDENTITY_MISMATCH")
        if identity_state == "mismatch":
            return ArtifactQualityResult(
                "identity-mismatch",
                identity_state,
                page_count,
                text_layer_state,
                "not-ready",
                blocker_codes=tuple(blockers),
            )
        if encrypted:
            quality = "partial"
        elif text_layer_state == "missing":
            quality = "ocr-required"
        elif text_layer_state == "available":
            quality = "readable"
        else:
            quality = "partial"
            blockers.append("TEXT_LAYER_UNDETERMINED")
        locator = "ready" if page_count > 0 and text_layer_state == "available" else "partial" if page_count > 0 else "unknown"
        return ArtifactQualityResult(
            quality,
            identity_state,
            page_count,
            text_layer_state,
            locator,
            blocker_codes=tuple(dict.fromkeys(blockers)),
        )


class PrivateArtifactStore:
    """Private artifact storage anchored below an explicit trusted boundary."""

    def __init__(self, root: Path, *, boundary_root: Path | None = None) -> None:
        self.root = Path(os.path.abspath(os.fspath(root)))
        if boundary_root is None:
            boundary = self.root.parent
            while not os.path.lexists(boundary):
                parent = boundary.parent
                if parent == boundary:
                    break
                boundary = parent
        else:
            boundary = Path(os.path.abspath(os.fspath(boundary_root)))
        try:
            self.root.relative_to(boundary)
        except ValueError as exc:
            raise ValueError("private acquisition store must stay inside its boundary") from exc
        self.boundary_root = boundary

    @staticmethod
    def _directory_open_flags() -> int:
        return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)

    @staticmethod
    def _file_open_flags() -> int:
        return os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)

    def _open_root_fd(self) -> int:
        """Open/create the store one component at a time without following links."""

        try:
            boundary_stat = os.lstat(self.boundary_root)
        except OSError as exc:
            raise ValueError("private acquisition storage boundary is unavailable") from exc
        if stat.S_ISLNK(boundary_stat.st_mode) or not stat.S_ISDIR(boundary_stat.st_mode):
            raise ValueError("private acquisition storage boundary is invalid")
        try:
            descriptor = os.open(self.boundary_root, self._directory_open_flags())
        except OSError as exc:
            raise ValueError("private acquisition storage boundary is unsafe") from exc
        try:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise ValueError("private acquisition storage boundary is invalid")
            relative = self.root.relative_to(self.boundary_root)
            for part in relative.parts:
                created = False
                try:
                    child = os.open(part, self._directory_open_flags(), dir_fd=descriptor)
                except FileNotFoundError:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=descriptor)
                        created = True
                    except FileExistsError:
                        pass
                    try:
                        child = os.open(part, self._directory_open_flags(), dir_fd=descriptor)
                    except OSError as exc:
                        raise ValueError("private acquisition store has an unsafe path component") from exc
                except OSError as exc:
                    raise ValueError("private acquisition store has an unsafe path component") from exc
                if not stat.S_ISDIR(os.fstat(child).st_mode):
                    os.close(child)
                    raise ValueError("private acquisition store has a non-directory path component")
                if created:
                    os.fchmod(child, 0o700)
                os.close(descriptor)
                descriptor = child
            os.fchmod(descriptor, 0o700)
            return descriptor
        except Exception:
            os.close(descriptor)
            raise

    def prepare_root(self) -> Path:
        descriptor = self._open_root_fd()
        os.close(descriptor)
        return self.root

    def unlink_entry(self, name: str) -> None:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("private artifact entry name is invalid")
        descriptor = self._open_root_fd()
        try:
            try:
                os.unlink(name, dir_fd=descriptor)
            except FileNotFoundError:
                pass
        finally:
            os.close(descriptor)

    def store_pdf(self, content: bytes, sha256: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError("private artifact checksum is invalid")
        if hashlib.sha256(content).hexdigest() != sha256:
            raise ValueError("private artifact checksum does not match content")
        target_name = f"{sha256}.pdf"
        target = self.root / target_name
        root_descriptor = self._open_root_fd()
        try:
            def reuse_existing() -> bool:
                try:
                    existing_descriptor = os.open(
                        target_name,
                        self._file_open_flags(),
                        dir_fd=root_descriptor,
                    )
                except FileNotFoundError:
                    return False
                except OSError as exc:
                    raise ValueError("private artifact target is unsafe") from exc
                try:
                    if not stat.S_ISREG(os.fstat(existing_descriptor).st_mode):
                        raise ValueError("private artifact target is not a regular file")
                    existing_digest = hashlib.sha256()
                    while chunk := os.read(existing_descriptor, 1024 * 1024):
                        existing_digest.update(chunk)
                    if existing_digest.hexdigest() != sha256:
                        raise ValueError("private artifact checksum collision")
                    os.fchmod(existing_descriptor, 0o600)
                    return True
                finally:
                    os.close(existing_descriptor)

            if reuse_existing():
                return target

            temporary_name = f".artifact-{uuid.uuid4().hex}.tmp"
            temporary_descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=root_descriptor,
            )
            try:
                try:
                    os.fchmod(temporary_descriptor, 0o600)
                    view = memoryview(content)
                    while view:
                        written = os.write(temporary_descriptor, view)
                        if written <= 0:
                            raise OSError("private artifact write made no progress")
                        view = view[written:]
                    os.fsync(temporary_descriptor)
                finally:
                    os.close(temporary_descriptor)
                try:
                    # Publish without replacement. A concurrent identical
                    # writer loses with EEXIST, verifies the winner, and
                    # safely reuses the checksum-addressed artifact.
                    os.link(
                        temporary_name,
                        target_name,
                        src_dir_fd=root_descriptor,
                        dst_dir_fd=root_descriptor,
                        follow_symlinks=False,
                    )
                    os.fsync(root_descriptor)
                except FileExistsError:
                    if not reuse_existing():
                        raise ValueError(
                            "private artifact target changed during storage"
                        )
                except OSError as exc:
                    raise ValueError("private artifact publish failed safely") from exc
            finally:
                try:
                    os.unlink(temporary_name, dir_fd=root_descriptor)
                except FileNotFoundError:
                    pass
            return target
        finally:
            os.close(root_descriptor)


@dataclass(frozen=True)
class EntitlementResult:
    state: str = "unknown"
    subscribed: bool | None = None
    covered: bool | None = None
    platform: str = ""

    def __post_init__(self) -> None:
        if self.state not in {"unknown", "covered", "not-covered"}:
            raise ValueError("invalid entitlement state")


class EntitlementProvider(Protocol):
    def check(self, *, identifier: CanonicalIdentifier, metadata: dict[str, Any]) -> EntitlementResult: ...


def _normalize_issn(value: str) -> str:
    compact = re.sub(r"[^0-9Xx]", "", value or "").upper()
    return f"{compact[:4]}-{compact[4:]}" if len(compact) == 8 else ""


def _normalize_journal_title(value: str) -> str:
    normalized = (value or "").lower().replace("&", " and ")
    return re.sub(r"^the", "", re.sub(r"[^a-z0-9]", "", normalized))


def coverage_includes_year(coverage: str, year: int | None) -> bool | None:
    if not coverage or not year:
        return None
    segments: list[tuple[int, int]] = []
    for chunk in re.split(r"(?=\bfrom\s+\d{4})", coverage, flags=re.I):
        start = re.search(r"from\s+(\d{4})", chunk, re.I)
        if not start:
            continue
        end = re.search(r"until\s+(\d{4})", chunk, re.I)
        segments.append((int(start.group(1)), int(end.group(1)) if end else 9999))
    if not segments:
        return None
    return any(start <= year <= end for start, end in segments)


class SQLiteHoldingsEntitlementProvider:
    """Read-only A-Z holdings lookup; a missing row remains unknown."""

    def __init__(self, database: Path) -> None:
        self.database = Path(database)

    def check(self, *, identifier: CanonicalIdentifier, metadata: dict[str, Any]) -> EntitlementResult:
        if not self.database.is_file() or self.database.is_symlink():
            return EntitlementResult()
        issns = [_normalize_issn(str(item)) for item in metadata.get("issns", [])]
        issns = [item for item in issns if item]
        journal = _normalize_journal_title(str(metadata.get("journal", "")))
        year_value = metadata.get("year")
        year = int(year_value) if isinstance(year_value, int) or str(year_value).isdigit() else None
        connection = sqlite3.connect(f"file:{self.database.resolve()}?mode=ro", uri=True, timeout=5)
        try:
            rows: list[tuple[Any, ...]] = []
            for issn in issns:
                rows = connection.execute(
                    "select title, platform, is_free, coverage from journals where issn_print=? or issn_e=?",
                    (issn, issn),
                ).fetchall()
                if rows:
                    break
            if not rows and journal:
                candidates = connection.execute(
                    "select title, platform, is_free, coverage from journals"
                ).fetchall()
                rows = [row for row in candidates if _normalize_journal_title(str(row[0])) == journal]
        except sqlite3.Error:
            return EntitlementResult()
        finally:
            connection.close()
        if not rows:
            return EntitlementResult()
        _title, platform, is_free, coverage = rows[0]
        covered = coverage_includes_year(str(coverage or ""), year)
        subscribed = not bool(is_free)
        if bool(is_free) or covered is True:
            state = "covered"
        elif subscribed and covered is False:
            state = "not-covered"
        else:
            state = "unknown"
        return EntitlementResult(
            state=state,
            subscribed=subscribed,
            covered=covered,
            platform=str(platform or ""),
        )


class SecretProvider(Protocol):
    def get(self, name: str) -> str | None: ...


class EnvironmentSecretProvider:
    """Opt-in environment backend for CI/tests; not a desktop secret store."""

    def __init__(self, *, allowed_names: Sequence[str]) -> None:
        self.allowed_names = frozenset(allowed_names)

    def get(self, name: str) -> str | None:
        if name not in self.allowed_names:
            return None
        return os.environ.get(name) or None


class BrowserSessionProvider(Protocol):
    def acquire(self, request: AcquisitionRequest) -> FullTextProviderResult: ...


class PortableScientificAcquisitionProvider:
    """Open/public route ladder with bounded downloads and artifact QC."""

    name = "rkf-portable-oa"
    version = "3"

    def __init__(
        self,
        *,
        contact_email: str = "",
        storage_root: Path | None = None,
        storage_boundary: Path | None = None,
        http_client: HTTPClient | None = None,
        policy: AcquisitionPolicy | None = None,
        validator: PDFArtifactValidator | None = None,
        entitlement_provider: EntitlementProvider | None = None,
        secret_provider: SecretProvider | None = None,
        identifier_adapters: Sequence[IdentifierAdapter] | None = None,
    ) -> None:
        self.contact_email = contact_email.strip()
        if self.contact_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.contact_email):
            raise ValueError("contact_email must be a valid email address")
        self.http = http_client or UrllibHTTPClient()
        self.policy = policy or AcquisitionPolicy()
        self.validator = validator or PDFArtifactValidator(min_bytes=self.policy.min_pdf_bytes)
        self.store = (
            PrivateArtifactStore(storage_root, boundary_root=storage_boundary)
            if storage_root is not None
            else None
        )
        self.entitlement_provider = entitlement_provider
        self.secret_provider = secret_provider
        self.identifier_adapters = IdentifierAdapterRegistry(
            identifier_adapters if identifier_adapters is not None else default_identifier_adapters()
        )
        self._rate_lock = threading.Lock()
        self._last_request = 0.0
        self._backoff_lock = threading.Lock()
        self._backoff_until: dict[str, float] = {}

    @property
    def user_agent(self) -> str:
        contact = f"mailto:{self.contact_email}" if self.contact_email else "https://github.com/ChenHau-Lan/ResearchWiki"
        return f"RKF-scientific-acquisition/{self.version} (+{contact})"

    def _wait_for_rate_slot(self) -> None:
        with self._rate_lock:
            remaining = self.policy.courtesy_interval_s - (time.monotonic() - self._last_request)
            if remaining > 0:
                time.sleep(remaining)
            self._last_request = time.monotonic()

    def _get(
        self,
        url: str,
        *,
        accept: str,
        timeout_s: float,
        max_bytes: int,
        extra_headers: dict[str, str] | None = None,
    ) -> HTTPResponse:
        _validate_public_url(url)
        self._wait_for_rate_slot()
        response = self.http.get(
            url,
            headers={"User-Agent": self.user_agent, "Accept": accept, **(extra_headers or {})},
            timeout_s=timeout_s,
            max_bytes=max_bytes,
        )
        _validate_public_url(response.url)
        return response

    @staticmethod
    def _attempt(
        attempts: list[AcquisitionAttempt],
        *,
        route: str,
        status: str,
        started: float,
        reason: str = "",
        host: str = "",
        http_status: int = 0,
    ) -> None:
        attempts.append(
            AcquisitionAttempt(
                route=route,
                status=status,
                reason_code=reason,
                host=host,
                http_status=http_status,
                elapsed_ms=max(0, int((time.monotonic() - started) * 1000)),
            )
        )

    def _metadata_get(
        self,
        url: str,
        *,
        route: str,
        attempts: list[AcquisitionAttempt],
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        host = urllib.parse.urlsplit(url).hostname or ""
        with self._backoff_lock:
            backoff_until = self._backoff_until.get(route, 0.0)
        if time.monotonic() < backoff_until:
            self._attempt(
                attempts,
                route=route,
                status="retryable",
                started=started,
                reason="PROVIDER_BACKOFF_ACTIVE",
                host=host,
            )
            return {}
        try:
            response = self._get(
                url,
                accept="application/json",
                timeout_s=self.policy.metadata_timeout_s,
                max_bytes=self.policy.max_metadata_bytes,
                extra_headers=extra_headers,
            )
        except ResponseTooLargeError:
            self._attempt(attempts, route=route, status="provider-error", started=started, reason="METADATA_TOO_LARGE", host=host)
            return {}
        except HTTPTransportError as error:
            self._attempt(
                attempts,
                route=route,
                status="retryable" if error.retryable else "blocked",
                started=started,
                reason="METADATA_TRANSPORT_ERROR" if error.retryable else "UNSAFE_METADATA_REDIRECT",
                host=host,
            )
            return {}
        except ValueError:
            self._attempt(attempts, route=route, status="blocked", started=started, reason="UNSAFE_METADATA_URL", host=host)
            return {}
        if response.status == 200:
            try:
                payload = _json_payload(response)
            except ValueError:
                self._attempt(attempts, route=route, status="provider-error", started=started, reason="METADATA_JSON_INVALID", host=host, http_status=200)
                return {}
            self._attempt(attempts, route=route, status="resolved", started=started, host=host, http_status=200)
            return payload
        status = "retryable" if response.status == 429 or response.status >= 500 else "unavailable"
        reason = "RATE_LIMITED" if response.status == 429 else "METADATA_HTTP_ERROR"
        if response.status == 429:
            retry_after = response.headers.get("retry-after", "")
            delay = float(retry_after) if retry_after.isdigit() else 60.0
            with self._backoff_lock:
                self._backoff_until[route] = max(
                    self._backoff_until.get(route, 0.0),
                    time.monotonic() + min(max(delay, 5.0), 600.0),
                )
        self._attempt(attempts, route=route, status=status, started=started, reason=reason, host=host, http_status=response.status)
        return {}

    @staticmethod
    def _add_candidate(candidates: list[AcquisitionCandidate], candidate: AcquisitionCandidate) -> None:
        if candidate.url and candidate.url not in {item.url for item in candidates}:
            candidates.append(candidate)

    def _cap_doi_candidates(
        self,
        candidates: Sequence[AcquisitionCandidate],
        *,
        protected_routes: set[str],
    ) -> list[AcquisitionCandidate]:
        """Bound opportunistic routes without dropping publisher or DOI fallbacks."""

        protected = [item for item in candidates if item.route in protected_routes]
        opportunistic = [item for item in candidates if item.route not in protected_routes]
        if len(protected) > self.policy.max_candidates:
            protected = sorted(
                protected,
                key=lambda item: (
                    0 if item.route.endswith("-landing-meta") else 1,
                    0 if item.secret_name else 1,
                ),
            )[: self.policy.max_candidates]
        available = self.policy.max_candidates - len(protected)
        selected_urls = {
            item.url
            for item in (*opportunistic[:available], *protected)
        }
        return [item for item in candidates if item.url in selected_urls]

    def _discover_doi(
        self,
        doi: str,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        candidates: list[AcquisitionCandidate] = []
        metadata: dict[str, Any] = {
            "doi": doi,
            "title": "",
            "license": "",
            "registry": "unknown",
            "issns": [],
            "journal": "",
            "year": None,
        }
        crossref_licenses: object = []
        copernicus = re.fullmatch(r"10\.5194/([a-z0-9-]+)-(\d+)-(\d+)-(\d{4})", doi, re.I)
        if copernicus:
            journal, volume, first_page, year = copernicus.groups()
            self._add_candidate(
                candidates,
                AcquisitionCandidate(
                    route="copernicus-direct",
                    url=f"https://{journal}.copernicus.org/articles/{volume}/{first_page}/{year}/{journal}-{volume}-{first_page}-{year}.pdf",
                    artifact_type="version-of-record-pdf",
                    artifact_version="version-of-record",
                ),
            )
        if doi.startswith(("10.1007/", "10.1186/")):
            self._add_candidate(
                candidates,
                AcquisitionCandidate(
                    route="springer-official-oa",
                    url=f"https://link.springer.com/content/pdf/{urllib.parse.quote(doi, safe='/')}.pdf",
                    artifact_type="version-of-record-pdf",
                    artifact_version="version-of-record",
                ),
            )
        encoded = urllib.parse.quote(doi, safe="")
        crossref = self._metadata_get(
            f"https://api.crossref.org/works/{encoded}",
            route="crossref-identity",
            attempts=attempts,
        )
        message = crossref.get("message") if isinstance(crossref.get("message"), dict) else {}
        if message:
            metadata["registry"] = "crossref"
            titles = message.get("title") or []
            metadata["title"] = str(titles[0]) if titles else ""
            metadata["issns"] = [str(item) for item in message.get("ISSN") or []]
            containers = message.get("container-title") or []
            metadata["journal"] = str(containers[0]) if containers else ""
            for date_key in ("published", "issued", "published-online", "published-print"):
                date_parts = ((message.get(date_key) or {}).get("date-parts") or [[None]])[0]
                if date_parts and date_parts[0]:
                    metadata["year"] = int(date_parts[0])
                    break
            licenses = message.get("license") or []
            crossref_licenses = licenses
            metadata["license"] = _crossref_license_for_version(
                licenses,
                "version-of-record",
            )
            for link in message.get("link") or []:
                if not isinstance(link, dict) or not link.get("URL"):
                    continue
                content_type = str(link.get("content-type", "")).lower()
                if "pdf" in content_type:
                    artifact_type, artifact_version = _crossref_artifact_provenance(
                        link.get("content-version")
                    )
                    self._add_candidate(
                        candidates,
                        AcquisitionCandidate(
                            route="crossref-link",
                            url=str(link["URL"]),
                            artifact_type=artifact_type,
                            artifact_version=artifact_version,
                            license=_crossref_license_for_version(
                                licenses,
                                artifact_version,
                            ),
                        ),
                    )
        else:
            datacite = self._metadata_get(
                f"https://api.datacite.org/dois/{encoded}",
                route="datacite-identity",
                attempts=attempts,
            )
            attributes = ((datacite.get("data") or {}).get("attributes") or {}) if isinstance(datacite.get("data"), dict) else {}
            if isinstance(attributes, dict) and attributes:
                metadata["registry"] = "datacite"
                titles = attributes.get("titles") or []
                if titles and isinstance(titles[0], dict):
                    metadata["title"] = str(titles[0].get("title", ""))
                content_url = attributes.get("contentUrl")
                for url in content_url if isinstance(content_url, list) else []:
                    self._add_candidate(candidates, AcquisitionCandidate("datacite-content", str(url)))
        if self.contact_email:
            unpaywall = self._metadata_get(
                f"https://api.unpaywall.org/v2/{encoded}?email={urllib.parse.quote(self.contact_email)}",
                route="unpaywall-all-locations",
                attempts=attempts,
            )
            locations: list[Any] = []
            if isinstance(unpaywall.get("best_oa_location"), dict):
                locations.append(unpaywall["best_oa_location"])
            locations.extend(item for item in unpaywall.get("oa_locations", []) if isinstance(item, dict))
            for location in locations:
                version = str(location.get("version", "")).lower()
                artifact_version = {
                    "publishedversion": "version-of-record",
                    "acceptedversion": "accepted-manuscript",
                    "submittedversion": "preprint",
                }.get(version, "unknown")
                artifact_type = {
                    "version-of-record": "version-of-record-pdf",
                    "accepted-manuscript": "accepted-manuscript",
                    "preprint": "preprint",
                }.get(artifact_version, "pdf")
                license_value = str(
                    location.get("license")
                    or _crossref_license_for_version(
                        crossref_licenses,
                        artifact_version,
                    )
                    or ""
                )
                if location.get("url_for_pdf"):
                    self._add_candidate(candidates, AcquisitionCandidate("unpaywall-pdf", str(location["url_for_pdf"]), "pdf", artifact_type, artifact_version, license_value))
                if location.get("url"):
                    self._add_candidate(candidates, AcquisitionCandidate("unpaywall-landing", str(location["url"]), "landing", artifact_type, artifact_version, license_value))
        else:
            self._attempt(
                attempts,
                route="unpaywall-all-locations",
                status="manual-required",
                started=time.monotonic(),
                reason="UNPAYWALL_EMAIL_NOT_CONFIGURED",
                host="api.unpaywall.org",
            )
        semantic = self._metadata_get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{encoded}?fields=openAccessPdf",
            route="semantic-scholar-oa",
            attempts=attempts,
        )
        oa_pdf = semantic.get("openAccessPdf") if isinstance(semantic.get("openAccessPdf"), dict) else {}
        if oa_pdf.get("url"):
            host = urllib.parse.urlsplit(str(oa_pdf["url"])).hostname or ""
            version = "preprint" if "arxiv" in host else "unknown"
            self._add_candidate(candidates, AcquisitionCandidate("semantic-scholar-oa", str(oa_pdf["url"]), "pdf", "preprint" if version == "preprint" else "pdf", version))
        openalex_identifier = urllib.parse.quote(f"https://doi.org/{doi}", safe="")
        openalex = self._metadata_get(
            f"https://api.openalex.org/works/{openalex_identifier}?select=id,doi,open_access,best_oa_location,locations",
            route="openalex-oa",
            attempts=attempts,
        )
        locations: list[dict[str, Any]] = []
        if isinstance(openalex.get("best_oa_location"), dict):
            locations.append(openalex["best_oa_location"])
        locations.extend(
            item for item in openalex.get("locations", []) if isinstance(item, dict)
        )
        for location in locations:
            version = {
                "publishedversion": "version-of-record",
                "acceptedversion": "accepted-manuscript",
                "submittedversion": "preprint",
            }.get(str(location.get("version", "")).lower(), "unknown")
            artifact_type = {
                "version-of-record": "version-of-record-pdf",
                "accepted-manuscript": "accepted-manuscript",
                "preprint": "preprint",
            }.get(version, "pdf")
            license_value = str(location.get("license") or "")
            source = location.get("source") if isinstance(location.get("source"), dict) else {}
            repository = source.get("type") == "repository"
            if location.get("pdf_url"):
                self._add_candidate(
                    candidates,
                    AcquisitionCandidate(
                        "openalex-pdf",
                        str(location["pdf_url"]),
                        "pdf",
                        artifact_type,
                        version,
                        license_value,
                        allow_repository_links=repository,
                    ),
                )
            if location.get("landing_page_url") and (location.get("is_oa") is True or repository or license_value):
                self._add_candidate(
                    candidates,
                    AcquisitionCandidate(
                        "openalex-landing",
                        str(location["landing_page_url"]),
                        "landing",
                        artifact_type,
                        version,
                        license_value,
                        allow_repository_links=repository,
                    ),
                )
        idconv_query = f"ids={encoded}&format=json&versions=yes&tool=rkf"
        if self.contact_email:
            idconv_query += "&email=" + urllib.parse.quote(self.contact_email)
        idconv = self._metadata_get(
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/?" + idconv_query,
            route="ncbi-idconv",
            attempts=attempts,
        )
        for record in idconv.get("records", []) if isinstance(idconv.get("records"), list) else []:
            if isinstance(record, dict) and record.get("pmcid"):
                pmcid = str(record["pmcid"]).upper()
                versioned_pmcid, selected_version = _current_pmc_version(record)
                selected_live = selected_version.get("live")
                selected_is_live = not (
                    selected_live is False
                    or str(selected_live or "").strip().lower() == "false"
                )
                if versioned_pmcid and selected_is_live:
                    cloud_metadata_url = (
                        "https://pmc-oa-opendata.s3.amazonaws.com/metadata/"
                        f"{urllib.parse.quote(versioned_pmcid, safe='')}.json"
                    )
                    cloud = self._metadata_get(
                        cloud_metadata_url,
                        route="ncbi-pmc-cloud-metadata",
                        attempts=attempts,
                    )
                    cloud_doi = normalize_doi(str(cloud.get("doi") or ""))
                    cloud_pdf = _pmc_cloud_https_url(str(cloud.get("pdf_url") or ""))
                    if (
                        cloud_pdf
                        and cloud_doi == doi
                        and cloud.get("is_pmc_openaccess") is True
                        and cloud.get("is_retracted") is False
                    ):
                        manuscript = cloud.get("is_manuscript") is True
                        cloud_candidate = AcquisitionCandidate(
                            "ncbi-pmc-cloud",
                            cloud_pdf,
                            "pdf",
                            "accepted-manuscript" if manuscript else "pdf",
                            "accepted-manuscript" if manuscript else "unknown",
                            str(cloud.get("license_code") or ""),
                        )
                        if cloud_candidate.url not in {item.url for item in candidates}:
                            candidates.insert(0, cloud_candidate)
                self._add_candidate(
                    candidates,
                    AcquisitionCandidate(
                        "europe-pmc",
                        f"https://europepmc.org/articles/{pmcid}?pdf=render",
                        "pdf",
                        "pdf",
                        "unknown",
                    ),
                )
        quoted_doi = urllib.parse.quote(doi, safe="/():;")
        official_pdf: tuple[str, str] | None = None
        if doi.startswith("10.1029/"):
            official_pdf = (
                "agu-wiley-official-pdf",
                f"https://agupubs.onlinelibrary.wiley.com/doi/pdfdirect/{quoted_doi}?download=true",
            )
        elif doi.startswith(("10.1002/", "10.1111/")):
            official_pdf = (
                "wiley-official-pdf",
                f"https://onlinelibrary.wiley.com/doi/pdfdirect/{quoted_doi}?download=true",
            )
        elif doi.startswith("10.1038/"):
            suffix = urllib.parse.quote(doi.split("/", 1)[1], safe="-._")
            official_pdf = (
                "nature-official-pdf",
                f"https://www.nature.com/articles/{suffix}.pdf",
            )
        elif doi.startswith("10.1088/"):
            official_pdf = (
                "iop-official-pdf",
                f"https://iopscience.iop.org/article/{quoted_doi}/pdf",
            )
        elif doi.startswith("10.1021/"):
            official_pdf = (
                "acs-official-pdf",
                f"https://pubs.acs.org/doi/pdf/{quoted_doi}",
            )
        elif doi.startswith("10.1126/"):
            official_pdf = (
                "aaas-official-pdf",
                f"https://www.science.org/doi/pdf/{quoted_doi}",
            )
        elif doi.startswith("10.1080/"):
            official_pdf = (
                "taylor-francis-official-pdf",
                f"https://www.tandfonline.com/doi/pdf/{quoted_doi}?download=true",
            )
        elif doi.startswith("10.3389/feart."):
            official_pdf = (
                "frontiers-official-pdf",
                "https://www.frontiersin.org/journals/earth-science/articles/"
                f"{quoted_doi}/pdf",
            )
        elif doi.startswith("10.3390/"):
            mdpi_match = re.fullmatch(
                r"10\.3390/(?P<code>[a-z]+)(?P<volume>\d{2})(?P<issue>\d{2})(?P<article>\d+)",
                doi,
                re.IGNORECASE,
            )
            journal_names = {"atmos": "atmosphere"}
            if mdpi_match and mdpi_match.group("code").lower() in journal_names:
                journal = journal_names[mdpi_match.group("code").lower()]
                stem = (
                    f"{journal}-{int(mdpi_match.group('volume'))}-"
                    f"{int(mdpi_match.group('article')):05d}"
                )
                for suffix in ("-v3", "-v2", "-v1", ""):
                    self._add_candidate(
                        candidates,
                        AcquisitionCandidate(
                            route="mdpi-official-pdf",
                            url=(
                                f"https://mdpi-res.com/d_attachment/{journal}/{stem}/"
                                f"article_deploy/{stem}{suffix}.pdf"
                            ),
                            # The suffix is a bounded discovery heuristic, not
                            # proof that this is the article's current revision.
                            artifact_type="pdf",
                            artifact_version="unknown",
                            license="",
                        ),
                    )
        if official_pdf is not None:
            route, url = official_pdf
            self._add_candidate(
                candidates,
                AcquisitionCandidate(
                    route=route,
                    url=url,
                    artifact_type="version-of-record-pdf",
                    artifact_version="version-of-record",
                    license=str(metadata.get("license") or ""),
                ),
            )
        if doi.startswith("10.1016/"):
            self._add_candidate(
                candidates,
                AcquisitionCandidate(
                    route="elsevier-tdm",
                    url=f"https://api.elsevier.com/content/article/doi/{urllib.parse.quote(doi, safe='/')}",
                    artifact_type="version-of-record-pdf",
                    artifact_version="version-of-record",
                    secret_name="ELSEVIER_TDM_KEY",
                    secret_header="X-ELS-APIKey",
                    optional_secret_name="ELSEVIER_INSTTOKEN",
                    optional_secret_header="X-ELS-Insttoken",
                ),
            )
        if doi.startswith(("10.1002/", "10.1029/", "10.1111/")):
            self._add_candidate(
                candidates,
                AcquisitionCandidate(
                    route="wiley-tdm",
                    url=f"https://api.wiley.com/onlinelibrary/tdm/v1/articles/{encoded}",
                    artifact_type="version-of-record-pdf",
                    artifact_version="version-of-record",
                    secret_name="WILEY_TDM_TOKEN",
                    secret_header="Wiley-TDM-Client-Token",
                ),
            )
        profile = provider_profile_for_doi(doi)
        landing_route = f"{profile.key}-landing-meta" if profile else "doi-landing-meta"
        self._add_candidate(
            candidates,
            AcquisitionCandidate(
                route=landing_route,
                url=f"https://doi.org/{urllib.parse.quote(doi, safe='/():;')}",
                kind="landing",
                # A DOI landing may expose a publisher or repository PDF, but
                # the landing relation alone is not artifact-level version or
                # license evidence for that exact file.
                artifact_type="pdf",
                artifact_version="unknown",
                license="",
            ),
        )
        protected_routes = {
            landing_route,
            *(
                item.route
                for item in candidates
                if item.secret_name
                or item.route.endswith("-official-pdf")
                or item.route == "ncbi-pmc-cloud"
            ),
        }
        return self._cap_doi_candidates(
            candidates,
            protected_routes=protected_routes,
        ), metadata

    def _discover(
        self,
        identifiers: CanonicalIdentifierSet,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        primary = identifiers.primary
        doi = identifiers.first("doi", "datacite-doi")
        if doi:
            doi_candidates, metadata = self._discover_doi(
                normalize_doi(doi.value),
                attempts=attempts,
            )
            explicit_candidates: list[AcquisitionCandidate] = []
            for alternate in identifiers.identifiers:
                if alternate.identifier_type in {"doi", "datacite-doi"}:
                    continue
                alternate_candidates, _alternate_metadata = self._discover_single(
                    alternate,
                    attempts=attempts,
                )
                for candidate in alternate_candidates:
                    self._add_candidate(explicit_candidates, candidate)
            combined: list[AcquisitionCandidate] = []
            for candidate in (*explicit_candidates, *doi_candidates):
                self._add_candidate(combined, candidate)
            protected_routes = {
                candidate.route
                for candidate in doi_candidates
                if candidate.secret_name
                or candidate.route.endswith("-landing-meta")
                or candidate.route.endswith("-official-pdf")
                or candidate.route == "ncbi-pmc-cloud"
            }
            return self._cap_doi_candidates(
                combined,
                protected_routes=protected_routes,
            ), metadata
        return self._discover_single(primary, attempts=attempts)

    def _discover_single(
        self,
        primary: CanonicalIdentifier,
        *,
        attempts: list[AcquisitionAttempt],
    ) -> tuple[list[AcquisitionCandidate], dict[str, Any]]:
        if primary.identifier_type == "arxiv":
            return [AcquisitionCandidate("arxiv-direct", f"https://arxiv.org/pdf/{primary.value}.pdf", "pdf", "preprint", "preprint")], {"title": "", "doi": "", "registry": "arxiv"}
        if primary.identifier_type == "nasa-ntrs":
            return [AcquisitionCandidate("nasa-ntrs-landing", f"https://ntrs.nasa.gov/citations/{primary.value}", "landing", "report", "unknown")], {"title": "", "doi": "", "registry": "nasa-ntrs"}
        if primary.identifier_type in {"url", "repository", "handle"}:
            kind = "pdf" if urllib.parse.urlsplit(primary.value).path.lower().endswith(".pdf") else "landing"
            return [
                AcquisitionCandidate(
                    "direct-identifier",
                    primary.value,
                    kind,
                    allow_repository_links=primary.identifier_type in {"repository", "handle"},
                )
            ], {"title": "", "doi": "", "registry": primary.identifier_type}
        adapter = self.identifier_adapters.for_type(primary.identifier_type)
        if adapter is not None:
            candidates, metadata = adapter.discover(self, primary, attempts=attempts)
            return candidates[: self.policy.max_candidates], metadata
        self._attempt(attempts, route="identifier-resolver", status="manual-required", started=time.monotonic(), reason="IDENTIFIER_ADAPTER_NOT_CONFIGURED")
        return [], {"title": "", "doi": "", "registry": primary.identifier_type}

    @staticmethod
    def _related_from_parser(parser: _CitationMetaParser, base_url: str) -> tuple[dict[str, str], ...]:
        related: list[dict[str, str]] = []
        mapping = {
            "citation_dataset": "dataset-link",
            "citation_data_url": "dataset-link",
            "citation_code_url": "software-link",
            "citation_supplementary_material": "supplement",
        }
        for meta_name, artifact_type in mapping.items():
            for value in parser.meta.get(meta_name, []):
                url = urllib.parse.urljoin(base_url, value)
                try:
                    host = _validate_public_url(url)
                except ValueError:
                    continue
                related.append(
                    {
                        "relationship": "supplements" if artifact_type == "supplement" else "related",
                        "artifact_type": artifact_type,
                        "host": host,
                        "identifier": "url-sha256:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
                    }
                )
        return tuple(related)

    def _fetch_candidate(
        self,
        candidate: AcquisitionCandidate,
        *,
        expected_doi: str,
        expected_title: str,
        attempts: list[AcquisitionAttempt],
        _request_budget: _CandidateRequestBudget | None = None,
        _visited_urls: set[str] | None = None,
        _depth: int = 0,
    ) -> tuple[bytes | None, AcquisitionCandidate, ArtifactQualityResult | None, tuple[dict[str, str], ...]]:
        started = time.monotonic()
        host = urllib.parse.urlsplit(candidate.url).hostname or ""
        request_budget = _request_budget or _CandidateRequestBudget(
            self.policy.max_candidate_requests
        )
        visited_urls = _visited_urls if _visited_urls is not None else set()
        candidate_url_key = urllib.parse.urldefrag(candidate.url).url
        if _depth > MAX_LANDING_PDF_DEPTH:
            self._attempt(
                attempts,
                route=candidate.route,
                status="provider-error",
                started=started,
                reason="LANDING_PDF_DEPTH_EXCEEDED",
                host=host,
            )
            return None, candidate, None, ()
        if candidate_url_key in visited_urls:
            self._attempt(
                attempts,
                route=candidate.route,
                status="provider-error",
                started=started,
                reason="LANDING_PDF_LOOP",
                host=host,
            )
            return None, candidate, None, ()
        visited_urls.add(candidate_url_key)
        extra_headers: dict[str, str] = {}
        if candidate.referer:
            extra_headers["Referer"] = candidate.referer
        if candidate.secret_name:
            secret = self.secret_provider.get(candidate.secret_name) if self.secret_provider else None
            if not secret:
                self._attempt(
                    attempts,
                    route=candidate.route,
                    status="manual-required",
                    started=started,
                    reason="PUBLISHER_TOKEN_NOT_CONFIGURED",
                    host=host,
                )
                return None, candidate, None, ()
            extra_headers[candidate.secret_header] = secret
        if candidate.optional_secret_name and self.secret_provider is not None:
            optional_secret = self.secret_provider.get(candidate.optional_secret_name)
            if optional_secret:
                extra_headers[candidate.optional_secret_header] = optional_secret
        if not request_budget.consume():
            self._attempt(
                attempts,
                route=candidate.route,
                status="provider-error",
                started=started,
                reason="ACQUISITION_REQUEST_BUDGET_EXHAUSTED",
                host=host,
            )
            return None, candidate, None, ()
        max_bytes = self.policy.max_artifact_bytes if candidate.kind == "pdf" else self.policy.max_html_bytes
        accept = "application/pdf,*/*;q=0.8" if candidate.kind == "pdf" else "text/html,application/pdf;q=0.9,*/*;q=0.5"
        try:
            response = self._get(
                candidate.url,
                accept=accept,
                timeout_s=self.policy.artifact_timeout_s,
                max_bytes=max_bytes,
                extra_headers=extra_headers,
            )
        except ResponseTooLargeError:
            self._attempt(attempts, route=candidate.route, status="invalid-artifact", started=started, reason="ARTIFACT_TOO_LARGE", host=host)
            return None, candidate, None, ()
        except ValueError:
            self._attempt(attempts, route=candidate.route, status="blocked", started=started, reason="UNSAFE_ARTIFACT_URL", host=host)
            return None, candidate, None, ()
        except HTTPTransportError as error:
            self._attempt(
                attempts,
                route=candidate.route,
                status="retryable" if error.retryable else "blocked",
                started=started,
                reason="ARTIFACT_TRANSPORT_ERROR" if error.retryable else "UNSAFE_ARTIFACT_REDIRECT",
                host=host,
            )
            return None, candidate, None, ()
        final_host = urllib.parse.urlsplit(response.url).hostname or host
        visited_urls.add(urllib.parse.urldefrag(response.url).url)
        if response.status == 429 or response.status >= 500:
            self._attempt(attempts, route=candidate.route, status="retryable", started=started, reason="RATE_LIMITED" if response.status == 429 else "ARTIFACT_SERVER_ERROR", host=final_host, http_status=response.status)
            return None, candidate, None, ()
        if response.status in {401, 403}:
            self._attempt(attempts, route=candidate.route, status="manual-required", started=started, reason="AUTHENTICATION_REQUIRED", host=final_host, http_status=response.status)
            return None, candidate, None, ()
        if response.status != 200:
            self._attempt(attempts, route=candidate.route, status="unavailable", started=started, reason="ARTIFACT_HTTP_ERROR", host=final_host, http_status=response.status)
            return None, candidate, None, ()
        if response.body.startswith(b"%PDF-"):
            quality = self.validator.validate(response.body, expected_doi=expected_doi, expected_title=expected_title)
            if quality.quality_state == "corrupt":
                status = "invalid-artifact"
            elif quality.quality_state == "identity-mismatch":
                status = "identity-mismatch"
            else:
                status = "obtained"
            self._attempt(attempts, route=candidate.route, status=status, started=started, reason=quality.blocker_codes[0] if quality.blocker_codes and status != "obtained" else "", host=final_host, http_status=200)
            return (
                response.body if status == "obtained" else None,
                AcquisitionCandidate(
                    candidate.route,
                    response.url,
                    "pdf",
                    candidate.artifact_type,
                    candidate.artifact_version,
                    candidate.license,
                    candidate.referer,
                    candidate.secret_name,
                    candidate.secret_header,
                    candidate.optional_secret_name,
                    candidate.optional_secret_header,
                ),
                quality,
                (),
            )
        content_type = response.headers.get("content-type", "").lower()
        markup_start = response.body[:4096].lstrip().lower()
        if (
            "html" not in content_type
            and "xml" not in content_type
            and not markup_start.startswith((b"<html", b"<?xml", b"<oa", b"<record"))
        ):
            self._attempt(attempts, route=candidate.route, status="invalid-artifact", started=started, reason="NON_PDF_RESPONSE", host=final_host, http_status=200)
            return None, candidate, None, ()
        parser = _CitationMetaParser()
        try:
            parser.feed(response.body.decode("utf-8", errors="replace"))
        except (TypeError, ValueError):
            self._attempt(attempts, route=candidate.route, status="provider-error", started=started, reason="LANDING_HTML_INVALID", host=final_host, http_status=200)
            return None, candidate, None, ()
        pdf_urls = [
            *_pdf_urls_from_link_header(response.headers.get("link", "")),
            *parser.meta.get("citation_pdf_url", []),
            *parser.pdf_links,
        ]
        if candidate.allow_repository_links:
            pdf_urls.extend(parser.meta.get("bepress_citation_pdf_url", []))
            for meta_name in (
                "eprints.document_url",
                "eprints.fulltext_url",
                "dc.identifier",
                "dcterms.identifier",
            ):
                pdf_urls.extend(
                    value
                    for value in parser.meta.get(meta_name, [])
                    if urllib.parse.urlsplit(value).path.lower().endswith(".pdf")
                )
            pdf_urls.extend(parser.repository_pdf_links)
        pdf_urls = list(dict.fromkeys(value for value in pdf_urls if value))
        related = self._related_from_parser(parser, response.url)
        if not pdf_urls:
            self._attempt(attempts, route=candidate.route, status="manual-required", started=started, reason="LANDING_NO_PDF_LINK", host=final_host, http_status=200)
            return None, candidate, None, related
        self._attempt(attempts, route=candidate.route, status="resolved", started=started, reason="LANDING_PDF_DISCOVERED", host=final_host, http_status=200)
        for url in pdf_urls[:4]:
            nested_route = (
                candidate.route
                if candidate.route.endswith(".citation-meta")
                else f"{candidate.route}.citation-meta"
            )
            nested = AcquisitionCandidate(
                route=nested_route,
                url=urllib.parse.urljoin(response.url, url),
                kind="pdf",
                artifact_type=candidate.artifact_type,
                artifact_version=candidate.artifact_version,
                license=(
                    candidate.license
                    or (
                        next(iter(parser.meta.get("repository_license", [])), "")
                        if candidate.allow_repository_links
                        else ""
                    )
                ),
                referer=response.url,
            )
            body, selected, quality, nested_related = self._fetch_candidate(
                nested,
                expected_doi=expected_doi,
                expected_title=expected_title,
                attempts=attempts,
                _request_budget=request_budget,
                _visited_urls=visited_urls,
                _depth=_depth + 1,
            )
            if body:
                return body, selected, quality, tuple((*related, *nested_related))
            if request_budget.denied:
                break
        return None, candidate, None, related

    def acquire(self, request: AcquisitionRequest) -> FullTextProviderResult:
        run_started = time.monotonic()
        attempts: list[AcquisitionAttempt] = []

        def run_id_for(status: str, *, route: str = "", digest: str = "") -> str:
            seed = {
                "project_id": request.project_id,
                "activation_id": request.activation_id,
                "source_id": request.source_id,
                "identifiers": [
                    (item.identifier_type, item.value)
                    for item in request.identifiers.identifiers
                ],
                "policy_profile": request.policy_profile,
                "status": status,
                "route": route,
                "artifact_sha256": digest,
                "attempts": [
                    (item.route, item.status, item.reason_code, item.host, item.http_status)
                    for item in attempts
                ],
            }
            fingerprint = hashlib.sha256(
                json.dumps(seed, ensure_ascii=True, sort_keys=True).encode("utf-8")
            ).hexdigest()[:24]
            return f"acq_{fingerprint}"

        candidates, metadata = self._discover(request.identifiers, attempts=attempts)
        if request.expected_title and not metadata.get("title"):
            metadata["title"] = request.expected_title[:1000]
        primary = request.identifiers.primary
        entitlement = EntitlementResult()
        if self.entitlement_provider is not None:
            entitlement = self.entitlement_provider.check(identifier=primary, metadata=metadata)
            if entitlement.state == "not-covered" and self.policy.skip_not_entitled:
                return FullTextProviderResult(
                    status="not-entitled",
                    provider=self.name,
                    provider_version=self.version,
                    tried_routes=tuple(dict.fromkeys(item.route for item in attempts)),
                    elapsed_ms=int((time.monotonic() - run_started) * 1000),
                    entitlement_state="not-covered",
                    blocker_codes=("ENTITLEMENT_NOT_COVERED",),
                    acquisition_run_id=run_id_for("not-entitled"),
                    identifier_types=tuple(item.identifier_type for item in request.identifiers.identifiers),
                    attempts=tuple(attempts),
                )
        expected_doi = normalize_doi(str(metadata.get("doi", ""))) if metadata.get("doi") else ""
        expected_title = str(metadata.get("title", ""))
        related: tuple[dict[str, str], ...] = ()
        request_budget = _CandidateRequestBudget(self.policy.max_candidate_requests)
        for candidate in candidates:
            body, selected, quality, found_related = self._fetch_candidate(
                candidate,
                expected_doi=expected_doi,
                expected_title=expected_title,
                attempts=attempts,
                _request_budget=request_budget,
            )
            related = _dedupe_related((*related, *found_related))
            if not body or quality is None:
                if request_budget.denied:
                    break
                continue
            digest = hashlib.sha256(body).hexdigest()
            private_handle = ""
            if self.store is not None:
                private_handle = str(self.store.store_pdf(body, digest))
            source_host = urllib.parse.urlsplit(selected.url).hostname or ""
            blockers = tuple(dict.fromkeys(quality.blocker_codes))
            return FullTextProviderResult(
                status="obtained",
                provider=self.name,
                provider_version=self.version,
                route=selected.route,
                tried_routes=tuple(dict.fromkeys(item.route for item in attempts)),
                artifact_sha256=digest,
                private_artifact_handle=private_handle,
                elapsed_ms=int((time.monotonic() - run_started) * 1000),
                entitlement_state=entitlement.state,
                pdf_magic_validated=True,
                blocker_codes=blockers,
                acquisition_run_id=run_id_for("obtained", route=selected.route, digest=digest),
                identifier_types=tuple(item.identifier_type for item in request.identifiers.identifiers),
                attempts=tuple(attempts),
                artifact_type=selected.artifact_type,
                artifact_version=selected.artifact_version,
                artifact_license=selected.license,
                source_host=source_host,
                byte_count=len(body),
                mime_type=quality.mime_type,
                quality_state=quality.quality_state,
                identity_state=quality.identity_state,
                page_count=quality.page_count,
                text_layer_state=quality.text_layer_state,
                locator_readiness=quality.locator_readiness,
                related_artifacts=_dedupe_related(related),
            )
        statuses = {attempt.status for attempt in attempts}
        if "manual-required" in statuses:
            status = "manual-required"
        elif "identity-mismatch" in statuses:
            status = "identity-mismatch"
        elif "invalid-artifact" in statuses:
            status = "invalid-artifact"
        elif "retryable" in statuses:
            status = "retryable"
        elif "provider-error" in statuses:
            status = "provider-error"
        elif "blocked" in statuses:
            status = "blocked"
        else:
            status = "unavailable"
        blockers = tuple(
            dict.fromkeys(
                attempt.reason_code
                for attempt in attempts
                if attempt.reason_code
                and attempt.status not in {"obtained", "resolved", "no-result"}
            )
        )
        return FullTextProviderResult(
            status=status,
            provider=self.name,
            provider_version=self.version,
            tried_routes=tuple(dict.fromkeys(item.route for item in attempts)),
            elapsed_ms=int((time.monotonic() - run_started) * 1000),
            entitlement_state=entitlement.state,
            blocker_codes=blockers or (("NO_AUTHORIZED_ARTIFACT_ROUTE",) if status == "unavailable" else ()),
            acquisition_run_id=run_id_for(status),
            identifier_types=tuple(item.identifier_type for item in request.identifiers.identifiers),
            attempts=tuple(attempts),
            related_artifacts=related,
        )

    def obtain(
        self,
        *,
        source_id: str,
        identifier: str,
        project_id: str,
        activation_id: str,
    ) -> FullTextProviderResult:
        identifiers = CanonicalIdentifierSet.resolve([identifier])
        return self.acquire(
            AcquisitionRequest(
                identifiers=identifiers,
                source_id=source_id,
                project_id=project_id,
                activation_id=activation_id,
            )
        )


class ExternalPaperFetchProvider:
    """Adapter for pinned/local ``paper_fetch.py --json`` institutional flows."""

    _PUBLIC_ROUTE_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
    # The pinned upstream adapter emits only these route function names. Do
    # not echo arbitrary label-shaped strings: a token can itself satisfy the
    # route-label regex.
    _PUBLIC_ROUTE_ALLOWLIST = frozenset(
        {"elsevier", "wiley", "springer", "unpaywall"}
    )
    _MAX_PUBLIC_TRIED_ROUTES = 8

    def __init__(
        self,
        command: Sequence[str],
        *,
        storage_root: Path,
        storage_boundary: Path | None = None,
        provider_version: str = "1.0.0",
        timeout_seconds: int = 300,
        max_artifact_bytes: int = 64 * 1024 * 1024,
        validator: PDFArtifactValidator | None = None,
    ) -> None:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("external paper-fetch command is required")
        if timeout_seconds <= 0:
            raise ValueError("external paper-fetch timeout must be positive")
        if max_artifact_bytes <= 0:
            raise ValueError("external paper-fetch artifact limit must be positive")
        self.command = tuple(command)
        self.store = PrivateArtifactStore(storage_root, boundary_root=storage_boundary)
        self.provider_version = provider_version
        self.timeout_seconds = timeout_seconds
        self.max_artifact_bytes = max_artifact_bytes
        self.validator = validator or PDFArtifactValidator()

    @classmethod
    def _public_tried_routes(cls, value: Any) -> tuple[str, ...]:
        """Return only non-sensitive route labels supplied by the adapter."""

        if not isinstance(value, (list, tuple)):
            return ()
        labels: list[str] = []
        for item in value:
            if len(labels) >= cls._MAX_PUBLIC_TRIED_ROUTES:
                break
            if not isinstance(item, str) or len(item) > 96:
                continue
            label = item.lower()
            if (
                not cls._PUBLIC_ROUTE_LABEL_RE.fullmatch(label)
                or label not in cls._PUBLIC_ROUTE_ALLOWLIST
                or label in labels
            ):
                continue
            labels.append(label)
        return tuple(labels)

    def _read_output(self, name: str) -> tuple[bytes | None, str]:
        try:
            root_descriptor = self.store._open_root_fd()
        except (OSError, ValueError):
            return None, "PROVIDER_FILE_UNSAFE"
        try:
            try:
                output_descriptor = os.open(
                    name,
                    PrivateArtifactStore._file_open_flags(),
                    dir_fd=root_descriptor,
                )
            except FileNotFoundError:
                return None, "PROVIDER_FILE_MISSING"
            except OSError:
                return None, "PROVIDER_FILE_UNSAFE"
            try:
                output_stat = os.fstat(output_descriptor)
                if not stat.S_ISREG(output_stat.st_mode):
                    return None, "PROVIDER_FILE_UNSAFE"
                if output_stat.st_size > self.max_artifact_bytes:
                    return None, "PROVIDER_FILE_TOO_LARGE"
                content = bytearray()
                while True:
                    chunk = os.read(
                        output_descriptor,
                        min(1024 * 1024, self.max_artifact_bytes + 1 - len(content)),
                    )
                    if not chunk:
                        break
                    content.extend(chunk)
                    if len(content) > self.max_artifact_bytes:
                        return None, "PROVIDER_FILE_TOO_LARGE"
                return bytes(content), ""
            except OSError:
                return None, "PROVIDER_FILE_UNSAFE"
            finally:
                os.close(output_descriptor)
        finally:
            os.close(root_descriptor)

    def _cleanup_output(self, name: str) -> bool:
        try:
            self.store.unlink_entry(name)
        except (OSError, ValueError):
            return False
        return True

    def obtain(
        self,
        *,
        source_id: str,
        identifier: str,
        project_id: str,
        activation_id: str,
    ) -> FullTextProviderResult:
        if not PROJECT_ID_RE.fullmatch(project_id) or not ACTIVATION_ID_RE.fullmatch(activation_id):
            raise ValueError("external paper-fetch requires valid lineage")
        temp_token = uuid.uuid4().hex[:24]
        started = time.monotonic()

        def stable_run_id(status: str, *, route: str = "", digest: str = "", blocker: str = "") -> str:
            seed = {
                "project_id": project_id,
                "activation_id": activation_id,
                "source_id": source_id,
                "identifier": identifier,
                "provider": "external-paper-fetch",
                "provider_version": self.provider_version,
                "status": status,
                "route": route,
                "digest": digest,
                "blocker": blocker,
            }
            return "acq_" + hashlib.sha256(
                json.dumps(seed, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()[:24]

        def without_artifact(
            status: str,
            blocker: str,
            *,
            route: str = "external-paper-fetch",
            tried: tuple[str, ...] = (),
        ) -> FullTextProviderResult:
            return FullTextProviderResult(
                status=status,
                provider="external-paper-fetch",
                provider_version=self.provider_version,
                route=route,
                tried_routes=tried,
                elapsed_ms=int((time.monotonic() - started) * 1000),
                blocker_codes=(blocker,),
                acquisition_run_id=stable_run_id(status, route=route, blocker=blocker),
                identifier_types=(resolve_identifier(identifier).identifier_type,),
                attempts=(AcquisitionAttempt(route, status, blocker),),
            )

        temp_root = self.store.prepare_root()
        output = temp_root / f".{temp_token}.download"
        command = [*self.command, "--json", identifier, str(output)]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            if not self._cleanup_output(output.name):
                return without_artifact("provider-error", "PROVIDER_OUTPUT_CLEANUP_FAILED")
            return without_artifact("retryable", "WATCHDOG_OR_COMMAND_TIMEOUT")
        except OSError:
            if not self._cleanup_output(output.name):
                return without_artifact("provider-error", "PROVIDER_OUTPUT_CLEANUP_FAILED")
            return without_artifact("provider-error", "PROVIDER_EXECUTION_ERROR")
        try:
            payload = json.loads(completed.stdout)
            if not isinstance(payload, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            if not self._cleanup_output(output.name):
                return without_artifact("provider-error", "PROVIDER_OUTPUT_CLEANUP_FAILED")
            return without_artifact("provider-error", "PROVIDER_OUTPUT_INVALID")
        tried = self._public_tried_routes(payload.get("tried", []))
        public_route = self._public_tried_routes([payload.get("route")])
        route = public_route[0] if public_route else "external-paper-fetch"
        if completed.returncode in {4, 5}:
            status = "retryable"
            blocker = "PROFILE_BUSY" if completed.returncode == 4 else "WATCHDOG_ABORT"
        elif completed.returncode == 1:
            status = "blocked"
            blocker = "PROVIDER_USAGE_ERROR"
        elif completed.returncode != 0 or payload.get("ok") is not True:
            status = "manual-required" if payload.get("resolver_url") else "unavailable"
            blocker = "MANUAL_RESOLVER_REQUIRED" if status == "manual-required" else "AUTOMATIC_ROUTES_EXHAUSTED"
        else:
            status = "obtained"
            blocker = ""
        if status != "obtained":
            if not self._cleanup_output(output.name):
                return without_artifact(
                    "provider-error",
                    "PROVIDER_OUTPUT_CLEANUP_FAILED",
                    route=route,
                    tried=tried,
                )
            return without_artifact(status, blocker, route=route, tried=tried)

        content, file_blocker = self._read_output(output.name)
        if not self._cleanup_output(output.name):
            return without_artifact(
                "provider-error",
                "PROVIDER_OUTPUT_CLEANUP_FAILED",
                route=route,
                tried=tried,
            )
        if content is None:
            return without_artifact(
                "invalid-artifact",
                file_blocker or "PROVIDER_FILE_UNSAFE",
                route=route,
                tried=tried,
            )
        quality = self.validator.validate(content, expected_doi=normalize_doi(identifier))
        if quality.quality_state in {"corrupt", "identity-mismatch"}:
            rejected = "identity-mismatch" if quality.quality_state == "identity-mismatch" else "invalid-artifact"
            return FullTextProviderResult(
                status=rejected,
                provider="external-paper-fetch",
                provider_version=self.provider_version,
                route=route,
                tried_routes=tried,
                elapsed_ms=int((time.monotonic() - started) * 1000),
                blocker_codes=quality.blocker_codes,
                acquisition_run_id=stable_run_id(
                    rejected,
                    route=route,
                    blocker=quality.blocker_codes[0] if quality.blocker_codes else "ARTIFACT_REJECTED",
                ),
                attempts=(AcquisitionAttempt(route, rejected, quality.blocker_codes[0] if quality.blocker_codes else "ARTIFACT_REJECTED"),),
            )
        digest = hashlib.sha256(content).hexdigest()
        target = self.store.store_pdf(content, digest)
        return FullTextProviderResult(
            status="obtained",
            provider="external-paper-fetch",
            provider_version=self.provider_version,
            route=route,
            tried_routes=tried,
            artifact_sha256=digest,
            private_artifact_handle=str(target),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            pdf_magic_validated=True,
            blocker_codes=quality.blocker_codes,
            acquisition_run_id=stable_run_id("obtained", route=route, digest=digest),
            identifier_types=(resolve_identifier(identifier).identifier_type,),
            attempts=(AcquisitionAttempt(route, "obtained"),),
            byte_count=len(content),
            mime_type="application/pdf",
            quality_state=quality.quality_state,
            identity_state=quality.identity_state,
            page_count=quality.page_count,
            text_layer_state=quality.text_layer_state,
            locator_readiness=quality.locator_readiness,
        )
