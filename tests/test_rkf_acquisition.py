from __future__ import annotations

import hashlib
import json
import io
import tempfile
import unittest
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rkf.acquisition import (
    AcquisitionPolicy,
    AcquisitionRequest,
    CanonicalIdentifierSet,
    ExternalPaperFetchProvider,
    HTTPTransportError,
    HTTPResponse,
    IdentifierAdapterRegistry,
    LinuxSecretServiceProvider,
    MacOSKeychainSecretProvider,
    PDFArtifactValidator,
    PortableScientificAcquisitionProvider,
    PrivateArtifactStore,
    SQLiteRetryAfterStore,
    UrllibHTTPClient,
    WindowsCredentialManagerSecretProvider,
    _read_bounded_http_body,
    _validate_public_url,
    coverage_includes_year,
    default_identifier_adapters,
    extract_identifiers_from_text,
    ingest_holdings_csv,
    provider_profile_for_doi,
    resolve_identifier,
)
from rkf.providers import (
    AcquisitionAttempt,
    FullTextProviderResult,
    ensure_acquisition_run_id,
    load_acquisition_runs,
    register_acquisition_run,
)
from rkf.processes import BoundedProcessResult
from rkf.core import Workspace


PROJECT_ID = "prj_1234567890abcdef12345678"
ACTIVATION_ID = "act_1234567890abcdef12345678"


def pdf_fixture() -> bytes:
    return (
        b"%PDF-1.4\n1 0 obj<</Type /Page>>endobj\n"
        + b"x" * 1400
        + b"\nstartxref\n1\n%%EOF\n"
    )


class TextExtractor:
    def inspect(self, _: bytes):
        return (
            "Impact of anthropogenic climate change on wildfire across western US forests "
            "doi 10.1073/pnas.1607171113",
            6,
            False,
        )


class FakeHTTP:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.request_headers = []

    def get(self, url, *, headers, timeout_s, max_bytes):
        self.calls.append(url)
        self.request_headers.append(dict(headers))
        response = self.responses.get(url)
        if response is None:
            return HTTPResponse(status=404, url=url, headers={"content-type": "application/json"}, body=b"{}")
        if isinstance(response, Exception):
            raise response
        return response


def response(url: str, body: bytes, *, status: int = 200, content_type: str = "application/json"):
    return HTTPResponse(status=status, url=url, headers={"content-type": content_type}, body=body)


class PeerBody(io.BytesIO):
    def __init__(self, value: bytes = b"", *, peer_ip: str = "93.184.216.34") -> None:
        super().__init__(value)
        self.peer_ip = peer_ip

    def getpeername(self):
        return self.peer_ip, 443


class RKFAcquisitionTests(unittest.TestCase):
    def test_p0_route_fixtures_cover_selection_identity_and_safety_boundary(self) -> None:
        fixture_path = (
            Path(__file__).parent
            / "fixtures"
            / "acquisition"
            / "p0-route-fixtures.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        self.assertEqual(len(fixture["cases"]), 11)
        self.assertIn("never bypass", fixture["access_control_boundary"])
        for case in fixture["cases"]:
            with self.subTest(publisher=case["publisher"]):
                candidates, _metadata = provider._discover_doi(
                    case["doi"],
                    attempts=[],
                )
                self.assertIn(
                    case["expected_route"],
                    {candidate.route for candidate in candidates},
                )

                class IdentityExtractor:
                    def inspect(self, _content):
                        return f"fixture title doi {case['doi']}", 2, False

                quality = PDFArtifactValidator(
                    min_bytes=8,
                    text_extractor=IdentityExtractor(),
                ).validate(pdf_fixture(), expected_doi=case["doi"])
                self.assertEqual(quality.identity_state, "verified")

    def test_http_body_enforces_monotonic_wall_clock_deadline(self) -> None:
        class StreamingBody:
            def __init__(self) -> None:
                self.calls = 0

            def read1(self, _size):
                self.calls += 1
                return b"chunk" if self.calls == 1 else b""

        clock = iter((0.0, 0.6))
        with patch("rkf.acquisition.time.monotonic", side_effect=lambda: next(clock)):
            with self.assertRaisesRegex(
                HTTPTransportError,
                "HTTP_WALL_CLOCK_DEADLINE",
            ):
                _read_bounded_http_body(
                    StreamingBody(),
                    max_bytes=1024,
                    deadline=0.5,
                )

    def test_native_secret_backends_are_allowlisted_and_non_logging(self) -> None:
        secret_result = BoundedProcessResult(0, stdout="secret-value\n", stderr="")
        with patch("rkf.acquisition.sys.platform", "darwin"), patch(
            "rkf.acquisition.run_bounded_process",
            return_value=secret_result,
        ) as runner:
            keychain = MacOSKeychainSecretProvider(
                allowed_names=("WILEY_TDM_TOKEN",)
            )
            self.assertEqual(keychain.get("WILEY_TDM_TOKEN"), "secret-value")
            self.assertIsNone(keychain.get("ELSEVIER_API_KEY"))
            self.assertNotIn("secret-value", " ".join(runner.call_args.args[0]))

        with patch("rkf.acquisition.sys.platform", "linux"), patch(
            "rkf.acquisition.run_bounded_process",
            return_value=secret_result,
        ):
            secret_service = LinuxSecretServiceProvider(
                allowed_names=("ELSEVIER_API_KEY",)
            )
            self.assertEqual(secret_service.get("ELSEVIER_API_KEY"), "secret-value")

        credential_manager = WindowsCredentialManagerSecretProvider(
            allowed_names=("ADS_API_TOKEN",),
            credential_reader=lambda _target: {
                "CredentialBlob": "windows-secret".encode("utf-16-le")
            },
        )
        self.assertEqual(credential_manager.get("ADS_API_TOKEN"), "windows-secret")

    def test_retry_after_state_is_cross_process_private_and_route_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "private" / "retry-after.sqlite3"
            first = SQLiteRetryAfterStore(path, boundary_root=root)
            second = SQLiteRetryAfterStore(path, boundary_root=root)

            first.record("unpaywall-all-locations", 30)

            self.assertGreater(second.remaining("unpaywall-all-locations"), 0)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("10.1000", path.read_bytes().decode("latin-1"))

    def test_institutional_external_policy_invokes_serial_browser_boundary(self) -> None:
        class BrowserAdapter:
            calls = 0

            def acquire(self, _request):
                self.calls += 1
                return FullTextProviderResult(
                    status="manual-required",
                    provider="machine-local-browser",
                    provider_version="1",
                    route="external-paper-fetch",
                    blocker_codes=("SSO_MANUAL_REQUIRED",),
                    attempts=(
                        AcquisitionAttempt(
                            "external-paper-fetch",
                            "manual-required",
                            "SSO_MANUAL_REQUIRED",
                        ),
                    ),
                )

        browser = BrowserAdapter()
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            browser_session_provider=browser,
        )
        request = AcquisitionRequest(
            identifiers=CanonicalIdentifierSet.resolve(
                ["https://publisher.example/article"]
            ),
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
            source_id="fixture",
            policy_profile="institutional-external",
        )

        result = provider.acquire(request)

        self.assertEqual(browser.calls, 1)
        self.assertEqual(result.status, "manual-required")
        self.assertIn("SSO_MANUAL_REQUIRED", result.blocker_codes)
        self.assertIn("external-paper-fetch", result.tried_routes)

    def test_holdings_csv_preview_apply_and_read_only_entitlement(self) -> None:
        from rkf.acquisition import SQLiteHoldingsEntitlementProvider

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            csv_path = root / "holdings.csv"
            database = root / "holdings.sqlite3"
            csv_path.write_text(
                "title,platform,issn_print,issn_e,is_free,coverage\n"
                "Journal of Fixtures,Fixture Platform,1234-5678,,0,from 2020 until 2025\n",
                encoding="utf-8",
            )

            preview = ingest_holdings_csv(csv_path, database)
            self.assertFalse(database.exists())
            applied = ingest_holdings_csv(csv_path, database, apply=True)
            entitlement = SQLiteHoldingsEntitlementProvider(database).check(
                identifier=resolve_identifier("10.1000/fixture"),
                metadata={
                    "issns": ["1234-5678"],
                    "journal": "Journal of Fixtures",
                    "year": 2024,
                },
            )

            self.assertFalse(preview["apply"])
            self.assertTrue(applied["apply"])
            self.assertEqual(database.stat().st_mode & 0o777, 0o600)
            self.assertEqual(entitlement.state, "covered")

    def test_atmospheric_p0_prefixes_have_explicit_policy_profiles(self) -> None:
        for doi in (
            "10.1029/example",
            "10.1175/example",
            "10.5194/example",
            "10.1016/example",
            "10.1002/example",
            "10.1007/example",
            "10.1038/example",
            "10.1088/example",
            "10.1021/example",
            "10.1126/example",
            "10.1080/example",
        ):
            with self.subTest(doi=doi):
                profile = provider_profile_for_doi(doi)
                self.assertIsNotNone(profile)
                self.assertIn("no access-control bypass", profile.policy_note.lower()) if profile.key in {"ams", "iop", "acs", "aaas", "taylor-francis"} else None

        self.assertIsNone(provider_profile_for_doi("10.10020/not-a-10.1002-paper"))

    def test_text_extractor_finds_bare_doi_arxiv_and_ntrs_identifiers(self) -> None:
        self.assertEqual(
            extract_identifiers_from_text(
                "Compare 10.5194/amt-17-5619-2024, arXiv:2401.01234 and NTRS:20230001234."
            ),
            [
                "10.5194/amt-17-5619-2024",
                "arXiv:2401.01234",
                "NTRS:20230001234",
            ],
        )

    def test_public_url_validation_rejects_private_dns_answers(self) -> None:
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("127.0.0.1", 443))],
        ):
            with self.assertRaisesRegex(ValueError, "non-public IP"):
                _validate_public_url("https://public-name.example/article", resolve_dns=True)

    def test_public_url_validation_rejects_non_public_embedded_ipv4(self) -> None:
        transition_addresses = (
            "::ffff:127.0.0.1",
            "2002:7f00:1::",
            "2001:0000:0808:0808:0000:0000:80ff:fffe",
            "64:ff9b::7f00:1",
            "64:ff9b:1::7f00:1",
        )
        for address in transition_addresses:
            with self.subTest(address=address), patch(
                "rkf.acquisition.socket.getaddrinfo",
                return_value=[(10, 1, 6, "", (address, 443, 0, 0))],
            ):
                with self.assertRaisesRegex(ValueError, "non-public IP"):
                    _validate_public_url(
                        "https://public-name.example/article",
                        resolve_dns=True,
                    )

    def test_authenticated_redirect_cannot_cross_origins(self) -> None:
        class RedirectOpener:
            calls = 0

            def open(self, request, timeout):
                type(self).calls += 1
                raise urllib.error.HTTPError(
                    request.full_url,
                    302,
                    "Found",
                    {"Location": "https://other.example/article.pdf"},
                    PeerBody(),
                )

        opener = RedirectOpener()
        client = UrllibHTTPClient(opener=opener)
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            with self.assertRaisesRegex(
                HTTPTransportError,
                "AUTHENTICATED_CROSS_ORIGIN_REDIRECT",
            ):
                client.get(
                    "https://publisher.example/article",
                    headers={"Authorization": "Bearer secret"},
                    timeout_s=1,
                    max_bytes=1024,
                )
        self.assertEqual(opener.calls, 1)

    def test_connected_private_peer_is_rejected_before_body_read(self) -> None:
        class PeerSocket:
            def getpeername(self):
                return "127.0.0.1", 443

        class SocketIO:
            _sock = PeerSocket()

        class BufferedBody:
            raw = SocketIO()

        class HTTPBody:
            fp = BufferedBody()

        class ReboundResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}
            read_called = False
            fp = HTTPBody()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return "https://public-name.example/article.pdf"

            def read(self, _size):
                type(self).read_called = True
                return b"should not be read"

        class RebindingOpener:
            def open(self, _request, timeout):
                return ReboundResponse()

        client = UrllibHTTPClient(opener=RebindingOpener())
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            with self.assertRaisesRegex(
                HTTPTransportError,
                "NON_PUBLIC_PEER_ADDRESS",
            ):
                client.get(
                    "https://public-name.example/article.pdf",
                    headers={"Accept": "application/pdf"},
                    timeout_s=1,
                    max_bytes=1024,
                )
        self.assertFalse(ReboundResponse.read_called)

    def test_connected_transition_peer_with_private_ipv4_is_rejected(self) -> None:
        class TransitionResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}
            read_called = False
            peer_ip = ""

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getpeername(self):
                return self.peer_ip, 443

            def geturl(self):
                return "https://public-name.example/article.pdf"

            def read(self, _size):
                type(self).read_called = True
                return b"should not be read"

        class TransitionOpener:
            def open(self, _request, timeout):
                return TransitionResponse()

        client = UrllibHTTPClient(opener=TransitionOpener())
        for address in (
            "2002:7f00:1::",
            "64:ff9b::7f00:1",
            "64:ff9b:1::7f00:1",
        ):
            with self.subTest(address=address), patch(
                "rkf.acquisition.socket.getaddrinfo",
                return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
            ):
                TransitionResponse.peer_ip = address
                TransitionResponse.read_called = False
                with self.assertRaisesRegex(
                    HTTPTransportError,
                    "NON_PUBLIC_PEER_ADDRESS",
                ):
                    client.get(
                        "https://public-name.example/article.pdf",
                        headers={"Accept": "application/pdf"},
                        timeout_s=1,
                        max_bytes=1024,
                    )
                self.assertFalse(TransitionResponse.read_called)

    def test_http_client_preserves_duplicate_link_header_fields(self) -> None:
        class DuplicateLinkHeaders:
            values = (
                '<https://repository.example/item>; rel="cite-as"',
                '<https://repository.example/file>; '
                'rel="item"; type="application/pdf"',
            )

            def items(self):
                return [
                    ("Content-Type", "text/html"),
                    *(('Link', value) for value in self.values),
                ]

            def get_all(self, name):
                return list(self.values) if name.lower() == "link" else None

        class LinkResponse:
            status = 200
            headers = DuplicateLinkHeaders()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getpeername(self):
                return "93.184.216.34", 443

            def geturl(self):
                return "https://repository.example/item"

            def read(self, _size):
                return b"<html></html>"

        class LinkOpener:
            def open(self, _request, timeout):
                return LinkResponse()

        client = UrllibHTTPClient(opener=LinkOpener())
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            result = client.get(
                "https://repository.example/item",
                headers={"Accept": "text/html"},
                timeout_s=1,
                max_bytes=1024,
            )

        self.assertIn('rel="cite-as"', result.headers["link"])
        self.assertIn('rel="item"', result.headers["link"])

    def test_uninspectable_peer_fails_closed_before_body_read(self) -> None:
        class UninspectableResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}
            read_called = False

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return "https://public-name.example/article.pdf"

            def read(self, _size):
                type(self).read_called = True
                return b"should not be read"

        class UninspectableOpener:
            def open(self, _request, timeout):
                return UninspectableResponse()

        client = UrllibHTTPClient(opener=UninspectableOpener())
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            with self.assertRaisesRegex(
                HTTPTransportError,
                "PEER_ADDRESS_UNAVAILABLE",
            ):
                client.get(
                    "https://public-name.example/article.pdf",
                    headers={"Accept": "application/pdf"},
                    timeout_s=1,
                    max_bytes=1024,
                )
        self.assertFalse(UninspectableResponse.read_called)

    def test_cross_origin_redirect_strips_referer(self) -> None:
        class RedirectResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}

            def __init__(self, url: str) -> None:
                self.url = url

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getpeername(self):
                return "93.184.216.34", 443

            def geturl(self):
                return self.url

            def read(self, _size):
                return b"ok"

        class RedirectOpener:
            def __init__(self) -> None:
                self.requests = []

            def open(self, request, timeout):
                self.requests.append(request)
                if len(self.requests) == 1:
                    raise urllib.error.HTTPError(
                        request.full_url,
                        302,
                        "Found",
                        {"Location": "https://cdn.example/article.pdf"},
                        PeerBody(),
                    )
                return RedirectResponse(request.full_url)

        opener = RedirectOpener()
        client = UrllibHTTPClient(opener=opener)
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            client.get(
                "https://publisher.example/article",
                headers={"Referer": "https://publisher.example/access?token=secret"},
                timeout_s=1,
                max_bytes=1024,
            )

        self.assertEqual(
            opener.requests[0].get_header("Referer"),
            "https://publisher.example/",
        )
        self.assertIsNone(opener.requests[1].get_header("Referer"))

    def test_same_origin_redirect_preserves_referer(self) -> None:
        class RedirectResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}

            def __init__(self, url: str) -> None:
                self.url = url

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def getpeername(self):
                return "93.184.216.34", 443

            def geturl(self):
                return self.url

            def read(self, _size):
                return b"ok"

        class RedirectOpener:
            def __init__(self) -> None:
                self.requests = []

            def open(self, request, timeout):
                self.requests.append(request)
                if len(self.requests) == 1:
                    raise urllib.error.HTTPError(
                        request.full_url,
                        302,
                        "Found",
                        {"Location": "/article.pdf"},
                        PeerBody(),
                    )
                return RedirectResponse(request.full_url)

        opener = RedirectOpener()
        client = UrllibHTTPClient(opener=opener)
        request_url = "https://publisher.example/article"
        referer = "https://publisher.example/access?token=secret#fragment"
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            client.get(
                request_url,
                headers={"Referer": referer},
                timeout_s=1,
                max_bytes=1024,
            )

        self.assertEqual(
            opener.requests[0].get_header("Referer"),
            "https://publisher.example/",
        )
        self.assertEqual(
            opener.requests[1].get_header("Referer"),
            "https://publisher.example/",
        )

    def test_https_redirect_to_http_is_rejected_without_secrets(self) -> None:
        class RedirectOpener:
            calls = 0

            def open(self, request, timeout):
                type(self).calls += 1
                raise urllib.error.HTTPError(
                    request.full_url,
                    302,
                    "Found",
                    {"Location": "http://publisher.example/article.pdf"},
                    PeerBody(),
                )

        opener = RedirectOpener()
        client = UrllibHTTPClient(opener=opener)
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            with self.assertRaisesRegex(HTTPTransportError, "INSECURE_REDIRECT"):
                client.get(
                    "https://publisher.example/article",
                    headers={"Accept": "application/pdf"},
                    timeout_s=1,
                    max_bytes=1024,
                )
        self.assertEqual(opener.calls, 1)

    def test_secret_headers_require_https_initial_url(self) -> None:
        class UnexpectedOpener:
            calls = 0

            def open(self, request, timeout):
                type(self).calls += 1
                raise AssertionError("insecure authenticated request must not be opened")

        opener = UnexpectedOpener()
        client = UrllibHTTPClient(opener=opener)
        with self.assertRaisesRegex(
            HTTPTransportError,
            "AUTHENTICATED_INSECURE_INITIAL_URL",
        ):
            client.get(
                "http://publisher.example/article",
                headers={"Authorization": "Bearer secret"},
                timeout_s=1,
                max_bytes=1024,
            )
        self.assertEqual(opener.calls, 0)

    def test_public_redirect_percent_encodes_raw_spaces(self) -> None:
        class RedirectResponse:
            status = 200
            headers = {"Content-Type": "application/pdf"}

            def __init__(self, url: str) -> None:
                self.url = url

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def geturl(self):
                return self.url

            def getpeername(self):
                return "93.184.216.34", 443

            def read(self, _size):
                return b"ok"

        class RedirectOpener:
            def __init__(self) -> None:
                self.calls = []

            def open(self, request, timeout):
                self.calls.append(request.full_url)
                if len(self.calls) == 1:
                    raise urllib.error.HTTPError(
                        request.full_url,
                        302,
                        "Found",
                        {"Location": "/files/accepted manuscript.pdf"},
                        PeerBody(),
                    )
                return RedirectResponse(request.full_url)

        opener = RedirectOpener()
        client = UrllibHTTPClient(opener=opener)
        with patch(
            "rkf.acquisition.socket.getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        ):
            result = client.get(
                "https://repository.example/item/42",
                headers={"Accept": "application/pdf"},
                timeout_s=1,
                max_bytes=1024,
            )

        self.assertEqual(
            opener.calls,
            [
                "https://repository.example/item/42",
                "https://repository.example/files/accepted%20manuscript.pdf",
            ],
        )
        self.assertEqual(result.url, opener.calls[-1])

    def test_holdings_coverage_parses_multiple_and_open_ended_segments(self) -> None:
        coverage = "Available from 1997 until 2001. Available from 2019"
        self.assertFalse(coverage_includes_year(coverage, 2010))
        self.assertTrue(coverage_includes_year(coverage, 2024))

    def test_identifier_resolver_is_multi_type_and_fails_closed_on_conflict(self) -> None:
        self.assertEqual(resolve_identifier("https://doi.org/10.1073/pnas.1607171113").identifier_type, "doi")
        self.assertIn(
            "<0461:taotft>",
            resolve_identifier(
                "https://doi.org/10.1175/1520-0469(2002)059%3C0461:TAOTFT%3E2.0.CO;2"
            ).value,
        )
        self.assertEqual(resolve_identifier("arXiv:2401.01234").identifier_type, "arxiv")
        self.assertEqual(resolve_identifier("ADS:2016PNAS..11311770A").identifier_type, "ads-bibcode")
        self.assertEqual(resolve_identifier("EarthArXiv:2777").identifier_type, "eartharxiv")
        self.assertEqual(resolve_identifier("OSF:8sepv_v1").identifier_type, "osf-preprint")
        self.assertEqual(
            resolve_identifier("ESSOAR:10.1002/essoar.10512747.1").identifier_type,
            "ess-open-archive",
        )
        self.assertEqual(resolve_identifier("NOAA:55689").identifier_type, "noaa-report")
        self.assertEqual(resolve_identifier("WMO:state-of-global-climate-2023").identifier_type, "wmo-report")
        self.assertEqual(resolve_identifier("IPCC:AR6_WGI").value, "ar6-wgi")
        self.assertEqual(resolve_identifier("https://ntrs.nasa.gov/citations/20230001234").identifier_type, "nasa-ntrs")
        with self.assertRaisesRegex(ValueError, "multiple DOI"):
            CanonicalIdentifierSet.resolve(["10.1000/one", "10.1000/two"])
        with self.assertRaisesRegex(ValueError, "at most 8 identifiers"):
            CanonicalIdentifierSet.resolve(
                [
                    "10.1000/example",
                    *(f"https://example.org/{index}.pdf" for index in range(8)),
                ]
            )
        self.assertEqual(
            extract_identifiers_from_text("Official PDF https://example.org/report.pdf."),
            ["https://example.org/report.pdf"],
        )
        self.assertEqual(
            extract_identifiers_from_text(
                "Resolve ADS:2016PNAS..11311770A and NOAA:55689."
            ),
            ["ADS:2016PNAS..11311770A", "NOAA:55689"],
        )

    def test_title_identity_requires_distinctive_coverage_not_two_common_tokens(self) -> None:
        class WrongTextExtractor:
            def inspect(self, _content):
                return (
                    ("unrelated climate change discussion " * 80).strip(),
                    3,
                    False,
                )

        result = PDFArtifactValidator(
            text_extractor=WrongTextExtractor()
        ).validate(
            pdf_fixture(),
            expected_title=(
                "Interdisciplinary studies of solar activity and climate change"
            ),
        )

        self.assertEqual(result.identity_state, "mismatch")
        self.assertEqual(result.quality_state, "identity-mismatch")

    def test_title_identity_accepts_high_distinctive_token_coverage(self) -> None:
        class MatchingTextExtractor:
            def inspect(self, _content):
                return (
                    "Interdisciplinary studies of solar activity and climate change "
                    + ("full article body " * 20),
                    5,
                    False,
                )

        result = PDFArtifactValidator(
            text_extractor=MatchingTextExtractor()
        ).validate(
            pdf_fixture(),
            expected_title=(
                "Interdisciplinary studies of solar activity and climate change"
            ),
        )

        self.assertEqual(result.identity_state, "verified")

    def test_doi_identity_does_not_accept_a_longer_doi_prefix_match(self) -> None:
        for longer_doi in (
            "10.1000/example-suffix",
            "10.1000/example.supplement",
            "10.1000/example)suffix",
            "10.1000/example;suffix",
            "10.1000/example%2Fsupplement",
            "10.1000/example<supplement>",
            "110.1000/example",
        ):
            with self.subTest(longer_doi=longer_doi):
                class LongerDOITextExtractor:
                    def inspect(self, _content):
                        return (
                            (f"unrelated article doi {longer_doi} " * 40).strip(),
                            4,
                            False,
                        )

                result = PDFArtifactValidator(
                    text_extractor=LongerDOITextExtractor()
                ).validate(
                    pdf_fixture(),
                    expected_doi="10.1000/example",
                )

                self.assertEqual(result.identity_state, "unverified")

    def test_doi_identity_accepts_terminal_citation_punctuation(self) -> None:
        class CitationPunctuationTextExtractor:
            def inspect(self, _content):
                return (
                    ("article identifier (10.1000/example). " * 40).strip(),
                    4,
                    False,
                )

        result = PDFArtifactValidator(
            text_extractor=CitationPunctuationTextExtractor()
        ).validate(
            pdf_fixture(),
            expected_doi="10.1000/example",
        )

        self.assertEqual(result.identity_state, "verified")

    def test_doi_identity_accepts_exact_legacy_ams_angle_bracket_doi(self) -> None:
        legacy_doi = (
            "10.1175/1520-0450(1999)038"
            "<1324:aiotco>2.0.co;2"
        )

        class LegacyAMSTextExtractor:
            def inspect(self, _content):
                return (
                    (f"article doi {legacy_doi} " * 20).strip(),
                    12,
                    False,
                )

        result = PDFArtifactValidator(
            text_extractor=LegacyAMSTextExtractor()
        ).validate(
            pdf_fixture(),
            expected_doi=legacy_doi,
        )

        self.assertEqual(result.identity_state, "verified")

    def test_identifier_adapter_registry_covers_requested_scientific_sources(self) -> None:
        registry = IdentifierAdapterRegistry(default_identifier_adapters())
        self.assertEqual(
            set(registry.identifier_types),
            {
                "ads-bibcode",
                "eartharxiv",
                "osf-preprint",
                "ess-open-archive",
                "noaa-report",
                "wmo-report",
                "ipcc-report",
            },
        )
        with self.assertRaisesRegex(ValueError, "multiple adapters"):
            IdentifierAdapterRegistry((*default_identifier_adapters(), default_identifier_adapters()[0]))

    def test_ads_bibcode_uses_official_link_gateway_without_guessing_a_doi(self) -> None:
        bibcode = "2016PNAS..11311770A"
        pdf = f"https://ui.adsabs.harvard.edu/link_gateway/{bibcode}/EPRINT_PDF"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({pdf: response(pdf, pdf_fixture(), content_type="application/pdf")}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="ads-fixture",
            identifier=f"ads:{bibcode}",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "ads-eprint-gateway")
        self.assertEqual(result.artifact_version, "preprint")
        self.assertEqual(result.identifier_types, ("ads-bibcode",))

    def test_osf_preprint_resolves_primary_file_through_public_json_api(self) -> None:
        record = "8sepv_v1"
        record_api = f"https://api.osf.io/v2/preprints/{record}/"
        file_api = "https://api.osf.io/v2/files/file-guid/"
        download = "https://osf.io/download/file-guid/"
        fake = FakeHTTP(
            {
                record_api: response(
                    record_api,
                    json.dumps(
                        {
                            "data": {
                                "attributes": {"title": "Public OSF preprint", "date_withdrawn": None},
                                "relationships": {
                                    "primary_file": {"links": {"related": {"href": file_api}}}
                                },
                                "links": {
                                    "html": f"https://osf.io/preprints/psyarxiv/{record}/",
                                    "preprint_doi": "https://doi.org/10.31234/osf.io/8sepv",
                                },
                            }
                        }
                    ).encode(),
                ),
                file_api: response(
                    file_api,
                    json.dumps(
                        {
                            "data": {
                                "attributes": {"name": "preprint.pdf"},
                                "links": {
                                    "download": download,
                                    "move": "https://files.osf.io/v1/resources/8sepv_v1/providers/osfstorage/file-guid",
                                },
                            }
                        }
                    ).encode(),
                ),
                download: response(download, pdf_fixture(), content_type="application/pdf"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="osf-fixture",
            identifier=f"osf:{record}",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "osf-primary-file")
        self.assertEqual(result.artifact_version, "preprint")
        self.assertEqual(fake.calls[:2], [record_api, file_api])

    def test_withdrawn_osf_preprint_is_a_manual_handoff(self) -> None:
        record_api = "https://api.osf.io/v2/preprints/withdrawn/"
        landing = "https://osf.io/preprints/eartharxiv/withdrawn/"
        fake = FakeHTTP(
            {
                record_api: response(
                    record_api,
                    json.dumps(
                        {
                            "data": {
                                "attributes": {
                                    "title": "Moved preprint",
                                    "date_withdrawn": "2021-02-08T00:00:00Z",
                                },
                                "links": {"html": landing},
                            }
                        }
                    ).encode(),
                ),
                landing: response(landing, b"<html></html>", content_type="text/html"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        result = provider.obtain(
            source_id="withdrawn-osf",
            identifier="osf:withdrawn",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "manual-required")
        self.assertIn("PREPRINT_WITHDRAWN", result.blocker_codes)

    def test_eartharxiv_numeric_record_uses_current_janeway_landing(self) -> None:
        landing = "https://eartharxiv.org/repository/view/2777/"
        pdf = "https://eartharxiv.org/repository/object/2777/download/5705/"
        html = f'<meta name="citation_pdf_url" content="{pdf}">'.encode()
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP(
                {
                    landing: response(landing, html, content_type="text/html"),
                    pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
                }
            ),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="eartharxiv-fixture",
            identifier="eartharxiv:2777",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "eartharxiv-janeway-landing.citation-meta")
        self.assertEqual(result.artifact_version, "preprint")

    def test_ess_open_archive_requires_its_doi_for_exact_resolution(self) -> None:
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )
        attempts = []
        candidates, metadata = provider._discover(
            CanonicalIdentifierSet.resolve(["essoar:10.1002/essoar.10512747.1"]),
            attempts=attempts,
        )

        self.assertEqual(metadata["registry"], "ess-open-archive")
        self.assertTrue(any(candidate.route.endswith("landing-meta") for candidate in candidates))

        result = provider.obtain(
            source_id="essoar-without-doi",
            identifier="essoar:10512747",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )
        self.assertEqual(result.status, "manual-required")
        self.assertIn("ESSOAR_DOI_REQUIRED", result.blocker_codes)

    def test_noaa_ir_pid_uses_official_landing_and_main_document_template(self) -> None:
        landing = "https://repository.library.noaa.gov/view/noaa/55689"
        pdf = f"{landing}/noaa_55689_DS1.pdf"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP(
                {
                    landing: response(landing, b"<html></html>", content_type="text/html"),
                    pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
                }
            ),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="noaa-fixture",
            identifier="noaa:55689",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "noaa-ir-main-pdf")
        self.assertEqual(result.artifact_type, "pdf")
        self.assertEqual(result.artifact_version, "unknown")

    def test_wmo_slug_uses_official_publication_series_landing(self) -> None:
        landing = (
            "https://public.wmo.int/publication-series/state-of-global-climate/"
            "state-of-global-climate-2023"
        )
        pdf = "https://public.wmo.int/files/state-of-global-climate-2023.pdf"
        html = f'<meta name="citation_pdf_url" content="{pdf}">'.encode()
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP(
                {
                    landing: response(landing, html, content_type="text/html"),
                    pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
                }
            ),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="wmo-fixture",
            identifier="wmo:state-of-global-climate-2023",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "wmo-publication-series.citation-meta")

    def test_ipcc_registered_report_id_uses_exact_official_pdf(self) -> None:
        pdf = "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_Full_Report.pdf"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({pdf: response(pdf, pdf_fixture(), content_type="application/pdf")}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="ipcc-fixture",
            identifier="ipcc:ar6-wgiii",
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "ipcc-full-report")
        self.assertEqual(result.artifact_type, "report")

    def test_all_unpaywall_locations_continue_after_auth_failure(self) -> None:
        doi = "10.1073/pnas.1607171113"
        encoded = urllib.parse.quote(doi, safe="")
        crossref_url = f"https://api.crossref.org/works/{encoded}"
        unpaywall_url = f"https://api.unpaywall.org/v2/{encoded}?email=test%40example.org"
        semantic_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{encoded}?fields=openAccessPdf"
        idconv_url = (
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
            f"?ids={encoded}&format=json&versions=yes&tool=rkf&email=test%40example.org"
        )
        blocked_pdf = "https://publisher.example/blocked.pdf"
        good_pdf = "https://repository.example/article.pdf"
        fake = FakeHTTP(
            {
                crossref_url: response(
                    crossref_url,
                    json.dumps({"message": {"title": ["Impact of anthropogenic climate change on wildfire across western US forests"]}}).encode(),
                ),
                unpaywall_url: response(
                    unpaywall_url,
                    json.dumps(
                        {
                            "best_oa_location": {"url_for_pdf": blocked_pdf, "version": "publishedVersion"},
                            "oa_locations": [
                                {"url_for_pdf": good_pdf, "version": "acceptedVersion", "license": "cc-by"}
                            ],
                        }
                    ).encode(),
                ),
                semantic_url: response(semantic_url, b"{}"),
                idconv_url: response(idconv_url, b'{"records":[]}'),
                blocked_pdf: response(blocked_pdf, b"forbidden", status=403, content_type="text/html"),
                good_pdf: response(good_pdf, pdf_fixture(), content_type="application/pdf"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            contact_email="test@example.org",
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="fixture",
            identifier=doi,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "unpaywall-pdf")
        self.assertEqual(result.artifact_version, "accepted-manuscript")
        self.assertEqual(result.quality_state, "readable")
        self.assertEqual(result.identity_state, "verified")
        self.assertIn("manual-required", {attempt.status for attempt in result.attempts})

    def test_landing_meta_extracts_pdf_and_related_research_artifacts(self) -> None:
        landing = "https://repository.example/item/42"
        pdf = "https://repository.example/files/main.pdf"
        html = (
            '<html><head><meta name="citation_pdf_url" content="/files/main.pdf">'
            '<meta name="citation_data_url" content="https://data.example/dataset/7"></head></html>'
        ).encode()
        fake = FakeHTTP(
            {
                landing: response(landing, html, content_type="text/html"),
                pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="repository-fixture",
            identifier=landing,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "direct-identifier.citation-meta")
        self.assertEqual(result.related_artifacts[0]["artifact_type"], "dataset-link")
        self.assertNotIn("https://data.example/dataset/7", json.dumps(result.public_payload()))
        self.assertEqual(fake.request_headers[1]["Referer"], landing)
        landing_attempt = next(
            attempt for attempt in result.attempts if attempt.route == "direct-identifier"
        )
        self.assertEqual(landing_attempt.status, "resolved")

    def test_repository_landing_can_use_an_explicit_pdf_anchor(self) -> None:
        landing = "https://zenodo.org/records/42"
        pdf = "https://zenodo.org/records/42/files/main.pdf"
        html = b'<html><body><a href="/records/42/files/main.pdf">PDF</a></body></html>'
        fake = FakeHTTP(
            {
                landing: response(landing, html, content_type="text/html"),
                pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="repository-anchor-fixture",
            identifier=landing,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "direct-identifier.citation-meta")
        self.assertEqual(fake.calls, [landing, pdf])
        self.assertEqual(fake.request_headers[1]["Referer"], landing)

    def test_repository_landing_accepts_bepress_pdf_metadata_without_pdf_suffix(self) -> None:
        landing = "https://digitalcommons.unl.edu/droughtfacpub/47/"
        pdf = (
            "https://digitalcommons.unl.edu/cgi/viewcontent.cgi?"
            "article=1046&context=droughtfacpub"
        )
        html = (
            '<meta name="bepress_citation_pdf_url" '
            f'content="{pdf}">'
        ).encode()
        fake = FakeHTTP(
            {
                landing: response(landing, html, content_type="text/html"),
                pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="bepress-fixture",
            identifier=landing,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "direct-identifier.citation-meta")
        self.assertEqual(fake.calls, [landing, pdf])

    def test_repository_signposting_link_header_resolves_pdf_item(self) -> None:
        landing = "https://dr.lib.iastate.edu/entities/publication/example"
        bitstream_id = "04175d56-e6dc-43de-af5a-38a5a19098cc"
        front_end_pdf = (
            f"https://dr.lib.iastate.edu/bitstreams/{bitstream_id}/download"
        )
        pdf = (
            "https://dr.lib.iastate.edu/server/api/core/bitstreams/"
            f"{bitstream_id}/content"
        )
        link_header = (
            '<https://dr.lib.iastate.edu/handle/20.500.1/example>; rel="cite-as", '
            f'<{front_end_pdf}>; rel="item"; type="application/pdf", '
            '<https://dr.lib.iastate.edu/signposting/example>; '
            'rel="describedby"; type="application/vnd.datacite.datacite+xml"'
        )
        fake = FakeHTTP(
            {
                landing: HTTPResponse(
                    status=200,
                    url=landing,
                    headers={"content-type": "text/html", "link": link_header},
                    body=b"<html><title>Repository item</title></html>",
                ),
                pdf: response(pdf, pdf_fixture(), content_type="application/pdf"),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=TextExtractor()),
        )

        result = provider.obtain(
            source_id="signposting-fixture",
            identifier=landing,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "direct-identifier.citation-meta")
        self.assertEqual(fake.calls, [landing, pdf])

    def test_doi_can_prioritize_an_explicit_authorized_repository_identifier(self) -> None:
        identifiers = CanonicalIdentifierSet.resolve(
            ["10.1002/qj.4944", "NOAA:71054"]
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        candidates, metadata = provider._discover(identifiers, attempts=[])

        self.assertEqual(metadata["doi"], "10.1002/qj.4944")
        self.assertEqual(candidates[0].route, "noaa-ir-landing")
        self.assertEqual(candidates[1].route, "noaa-ir-main-pdf")
        self.assertIn("agu-wiley-landing-meta", {item.route for item in candidates})

    def test_crossref_links_preserve_version_and_match_active_scoped_license(self) -> None:
        doi = "10.1000/crossref-versions"
        encoded = urllib.parse.quote(doi, safe="")
        crossref_url = f"https://api.crossref.org/works/{encoded}"
        accepted_pdf = "https://publisher.example/accepted.pdf"
        unknown_pdf = "https://publisher.example/unknown.pdf"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP(
                {
                    crossref_url: response(
                        crossref_url,
                        json.dumps(
                            {
                                "message": {
                                    "title": ["Crossref provenance fixture"],
                                    "license": [
                                        {
                                            "URL": "https://license.example/tdm",
                                            "applies-to": "tdm",
                                            "start": {"date-time": "2020-01-01T00:00:00Z"},
                                        },
                                        {
                                            "URL": "https://license.example/vor",
                                            "content-version": "vor",
                                            "start": {"date-time": "2020-01-01T00:00:00Z"},
                                        },
                                        {
                                            "URL": "https://license.example/am-old",
                                            "applies-to": "am",
                                            "start": {"date-time": "2020-01-01T00:00:00Z"},
                                        },
                                        {
                                            "URL": "https://license.example/am-current",
                                            "content-version": "am",
                                            "start": {"date-time": "2021-01-01T00:00:00Z"},
                                        },
                                        {
                                            "URL": "https://license.example/am-future",
                                            "content-version": "am",
                                            "start": {"date-time": "2099-01-01T00:00:00Z"},
                                        },
                                    ],
                                    "link": [
                                        {
                                            "URL": accepted_pdf,
                                            "content-type": "application/pdf",
                                            "content-version": "am",
                                        },
                                        {
                                            "URL": unknown_pdf,
                                            "content-type": "application/pdf",
                                            "content-version": "unspecified",
                                        },
                                    ],
                                }
                            }
                        ).encode(),
                    )
                }
            ),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        candidates, metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi]),
            attempts=[],
        )
        by_url = {candidate.url: candidate for candidate in candidates}

        self.assertEqual(by_url[accepted_pdf].artifact_type, "accepted-manuscript")
        self.assertEqual(by_url[accepted_pdf].artifact_version, "accepted-manuscript")
        self.assertEqual(by_url[accepted_pdf].license, "https://license.example/am-current")
        self.assertEqual(by_url[unknown_pdf].artifact_type, "pdf")
        self.assertEqual(by_url[unknown_pdf].artifact_version, "unknown")
        self.assertEqual(by_url[unknown_pdf].license, "")
        self.assertEqual(metadata["license"], "https://license.example/vor")

    def test_crossref_license_requires_matching_version_and_known_active_start(self) -> None:
        doi = "10.1000/crossref-license-scope"
        encoded = urllib.parse.quote(doi, safe="")
        crossref_url = f"https://api.crossref.org/works/{encoded}"
        published_pdf = "https://publisher.example/published.pdf"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP(
                {
                    crossref_url: response(
                        crossref_url,
                        json.dumps(
                            {
                                "message": {
                                    "license": [
                                        {
                                            "URL": "https://license.example/unscoped",
                                            "start": {"date-time": "2020-01-01T00:00:00Z"},
                                        },
                                        {
                                            "URL": "https://license.example/conflicting",
                                            "content-version": "vor",
                                            "applies-to": "am",
                                            "start": {"date-time": "2020-01-01T00:00:00Z"},
                                        },
                                        {
                                            "URL": "https://license.example/no-start",
                                            "content-version": "vor",
                                        },
                                    ],
                                    "link": [
                                        {
                                            "URL": published_pdf,
                                            "content-type": "application/pdf",
                                            "content-version": "vor",
                                        }
                                    ],
                                }
                            }
                        ).encode(),
                    )
                }
            ),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        candidates, metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi]),
            attempts=[],
        )
        candidate = next(item for item in candidates if item.url == published_pdf)

        self.assertEqual(candidate.artifact_version, "version-of-record")
        self.assertEqual(candidate.license, "")
        self.assertEqual(metadata["license"], "")

    def test_ncbi_pmc_cloud_uses_current_s3_metadata_and_https_pdf(self) -> None:
        doi = "10.1021/acsestair.5c00180"
        encoded = urllib.parse.quote(doi, safe="")
        idconv = (
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
            f"?ids={encoded}&format=json&versions=yes&tool=rkf"
        )
        cloud_metadata = (
            "https://pmc-oa-opendata.s3.amazonaws.com/metadata/"
            "PMC12439333.2.json"
        )
        https_pdf = (
            "https://pmc-oa-opendata.s3.amazonaws.com/PMC12439333.2/"
            "PMC12439333.2.pdf?md5=58b09bd1786f820ab0f47e2dd8b98c4c"
        )
        cloud_payload = json.dumps(
            {
                "pmcid": "PMC12439333",
                "version": 2,
                "doi": doi,
                "is_pmc_openaccess": True,
                "is_manuscript": False,
                "is_retracted": False,
                "license_code": "CC BY-NC-ND",
                "pdf_url": (
                    "s3://pmc-oa-opendata/PMC12439333.2/PMC12439333.2.pdf"
                    "?md5=58b09bd1786f820ab0f47e2dd8b98c4c"
                ),
            }
        ).encode()

        class DOITextExtractor:
            def inspect(self, _content):
                return f"Atmospheric research article doi {doi}", 4, False

        fake = FakeHTTP(
            {
                idconv: response(
                    idconv,
                    json.dumps(
                        {
                            "records": [
                                {
                                    "pmcid": "PMC12439333",
                                    "versions": [
                                        {"pmcid": "PMC12439333.1", "current": False},
                                        {"pmcid": "PMC12439333.2", "current": True},
                                    ],
                                }
                            ]
                        }
                    ).encode(),
                ),
                cloud_metadata: response(cloud_metadata, cloud_payload),
                https_pdf: response(
                    https_pdf,
                    pdf_fixture(),
                    content_type="application/pdf",
                ),
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
            validator=PDFArtifactValidator(text_extractor=DOITextExtractor()),
        )

        candidates, _metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi]),
            attempts=[],
        )
        cloud_candidate = next(
            candidate for candidate in candidates if candidate.route == "ncbi-pmc-cloud"
        )
        europe_candidate = next(
            candidate for candidate in candidates if candidate.route == "europe-pmc"
        )

        self.assertEqual(cloud_candidate.artifact_type, "pdf")
        self.assertEqual(cloud_candidate.artifact_version, "unknown")
        self.assertEqual(europe_candidate.artifact_type, "pdf")
        self.assertEqual(europe_candidate.artifact_version, "unknown")

        result = provider.obtain(
            source_id="pmc-fixture",
            identifier=doi,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "obtained")
        self.assertEqual(result.route, "ncbi-pmc-cloud")
        self.assertEqual(result.artifact_license, "CC BY-NC-ND")
        self.assertEqual(result.artifact_type, "pdf")
        self.assertEqual(result.artifact_version, "unknown")
        self.assertIn(https_pdf, fake.calls)

    def test_ncbi_pmc_cloud_keeps_doi_oa_and_retraction_gates(self) -> None:
        doi = "10.1016/j.example.2026.1"
        encoded = urllib.parse.quote(doi, safe="")
        idconv = (
            "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
            f"?ids={encoded}&format=json&versions=yes&tool=rkf"
        )
        cloud_metadata = (
            "https://pmc-oa-opendata.s3.amazonaws.com/metadata/PMC7654321.2.json"
        )
        idconv_payload = json.dumps(
            {
                "records": [
                    {
                        "pmcid": "PMC7654321",
                        "versions": [
                            {"pmcid": "PMC7654321.2", "current": True}
                        ],
                    }
                ]
            }
        ).encode()
        base_cloud = {
            "doi": doi,
            "is_pmc_openaccess": True,
            "is_manuscript": False,
            "is_retracted": False,
            "pdf_url": "s3://pmc-oa-opendata/PMC7654321.2/article.pdf",
        }

        for field, invalid_value in (
            ("doi", "10.1016/j.other.2026.1"),
            ("is_pmc_openaccess", False),
            ("is_retracted", True),
        ):
            with self.subTest(field=field):
                cloud_payload = {**base_cloud, field: invalid_value}
                provider = PortableScientificAcquisitionProvider(
                    http_client=FakeHTTP(
                        {
                            idconv: response(idconv, idconv_payload),
                            cloud_metadata: response(
                                cloud_metadata,
                                json.dumps(cloud_payload).encode(),
                            ),
                        }
                    ),
                    policy=AcquisitionPolicy(courtesy_interval_s=0),
                )

                candidates, _metadata = provider._discover(
                    CanonicalIdentifierSet.resolve([doi]),
                    attempts=[],
                )

                self.assertNotIn(
                    "ncbi-pmc-cloud",
                    {candidate.route for candidate in candidates},
                )

    def test_mdpi_atmosphere_profile_has_bounded_official_cdn_candidates(self) -> None:
        doi = "10.3390/atmos15091123"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP({}),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        candidates, _metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi]),
            attempts=[],
        )
        urls = [
            item.url for item in candidates if item.route == "mdpi-official-pdf"
        ]
        mdpi_candidates = [
            item for item in candidates if item.route == "mdpi-official-pdf"
        ]

        self.assertEqual(len(urls), 4)
        self.assertIn(
            "https://mdpi-res.com/d_attachment/atmosphere/"
            "atmosphere-15-01123/article_deploy/atmosphere-15-01123-v2.pdf",
            urls,
        )
        self.assertEqual(
            {(item.artifact_type, item.artifact_version, item.license) for item in mdpi_candidates},
            {("pdf", "unknown", "")},
        )

    def test_landing_pdf_self_reference_stops_without_refetching(self) -> None:
        landing = "https://repository.example/item/loop"
        html = f'<meta name="citation_pdf_url" content="{landing}">'.encode()
        fake = FakeHTTP({landing: response(landing, html, content_type="text/html")})
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        result = provider.obtain(
            source_id="loop-fixture",
            identifier=landing,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "provider-error")
        self.assertEqual(fake.calls, [landing])
        self.assertIn("LANDING_PDF_LOOP", result.blocker_codes)

    def test_landing_pdf_chain_has_a_bounded_depth(self) -> None:
        urls = [f"https://repository.example/item/depth-{index}" for index in range(6)]
        fake = FakeHTTP(
            {
                url: response(
                    url,
                    f'<meta name="citation_pdf_url" content="{urls[index + 1]}">'.encode(),
                    content_type="text/html",
                )
                for index, url in enumerate(urls[:-1])
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        result = provider.obtain(
            source_id="depth-fixture",
            identifier=urls[0],
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "provider-error")
        self.assertEqual(fake.calls, urls[:5])
        self.assertIn("LANDING_PDF_DEPTH_EXCEEDED", result.blocker_codes)

    def test_landing_candidate_fanout_has_a_shared_request_budget(self) -> None:
        root = "https://repository.example/item/root"
        children = [f"https://repository.example/item/child-{index}" for index in range(4)]
        grandchildren = [
            f"https://repository.example/item/child-{child}-leaf-{leaf}"
            for child in range(4)
            for leaf in range(4)
        ]

        def landing(urls: list[str]) -> bytes:
            return "".join(
                f'<meta name="citation_pdf_url" content="{url}">' for url in urls
            ).encode()

        fake = FakeHTTP(
            {
                root: response(root, landing(children), content_type="text/html"),
                **{
                    child: response(
                        child,
                        landing(grandchildren[index * 4 : (index + 1) * 4]),
                        content_type="text/html",
                    )
                    for index, child in enumerate(children)
                },
                **{
                    leaf: response(leaf, b"<html></html>", content_type="text/html")
                    for leaf in grandchildren
                },
            }
        )
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(
                courtesy_interval_s=0,
                max_candidate_requests=3,
            ),
        )

        result = provider.obtain(
            source_id="fanout-fixture",
            identifier=root,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertLessEqual(len(fake.calls), 3)
        self.assertIn("ACQUISITION_REQUEST_BUDGET_EXHAUSTED", result.blocker_codes)

    def test_candidate_request_budget_is_shared_across_top_level_routes(self) -> None:
        doi = "10.1000/request-budget"
        repository_urls = [
            "https://repository-one.example/article.pdf",
            "https://repository-two.example/article.pdf",
        ]
        fake = FakeHTTP({})
        provider = PortableScientificAcquisitionProvider(
            http_client=fake,
            policy=AcquisitionPolicy(
                courtesy_interval_s=0,
                max_candidate_requests=1,
            ),
        )

        result = provider.acquire(
            AcquisitionRequest(
                identifiers=CanonicalIdentifierSet.resolve([doi, *repository_urls]),
                source_id="top-level-budget-fixture",
                project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )
        )

        artifact_calls = [url for url in fake.calls if url in repository_urls]
        self.assertEqual(artifact_calls, repository_urls[:1])
        self.assertIn("ACQUISITION_REQUEST_BUDGET_EXHAUSTED", result.blocker_codes)

    def test_doi_candidate_cap_preserves_tdm_and_landing_routes(self) -> None:
        doi = "10.1016/j.example.2026.1"
        encoded = urllib.parse.quote(doi, safe="")
        unpaywall_url = (
            f"https://api.unpaywall.org/v2/{encoded}?email=test%40example.org"
        )
        fake = FakeHTTP(
            {
                unpaywall_url: response(
                    unpaywall_url,
                    json.dumps(
                        {
                            "oa_locations": [
                                {
                                    "url_for_pdf": f"https://repository-{index}.example/article.pdf",
                                    "version": "acceptedVersion",
                                }
                                for index in range(30)
                            ]
                        }
                    ).encode(),
                )
            }
        )
        provider = PortableScientificAcquisitionProvider(
            contact_email="test@example.org",
            http_client=fake,
            policy=AcquisitionPolicy(max_candidates=4, courtesy_interval_s=0),
        )

        candidates, _metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi]),
            attempts=[],
        )
        routes = [candidate.route for candidate in candidates]

        self.assertEqual(len(candidates), 4)
        self.assertIn("elsevier-tdm", routes)
        self.assertIn("elsevier-landing-meta", routes)

    def test_doi_candidate_cap_preserves_explicit_repository_and_tdm_routes(self) -> None:
        doi = "10.1016/j.example.2026.1"
        encoded = urllib.parse.quote(doi, safe="")
        unpaywall_url = (
            f"https://api.unpaywall.org/v2/{encoded}?email=test%40example.org"
        )
        repository_url = "https://repository.example/accepted.pdf"
        provider = PortableScientificAcquisitionProvider(
            contact_email="test@example.org",
            http_client=FakeHTTP(
                {
                    unpaywall_url: response(
                        unpaywall_url,
                        json.dumps(
                            {
                                "oa_locations": [
                                    {
                                        "url_for_pdf": (
                                            f"https://repository-{index}.example/article.pdf"
                                        ),
                                        "version": "acceptedVersion",
                                    }
                                    for index in range(30)
                                ]
                            }
                        ).encode(),
                    )
                }
            ),
            policy=AcquisitionPolicy(max_candidates=4, courtesy_interval_s=0),
        )

        candidates, _metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi, repository_url]),
            attempts=[],
        )
        routes = [candidate.route for candidate in candidates]

        self.assertEqual(len(candidates), 4)
        self.assertIn(repository_url, {candidate.url for candidate in candidates})
        self.assertIn("elsevier-tdm", routes)
        self.assertIn("elsevier-landing-meta", routes)

    def test_generic_doi_landing_does_not_infer_vor_or_license(self) -> None:
        doi = "10.1016/j.example.2026.1"
        encoded = urllib.parse.quote(doi, safe="")
        crossref_url = f"https://api.crossref.org/works/{encoded}"
        provider = PortableScientificAcquisitionProvider(
            http_client=FakeHTTP(
                {
                    crossref_url: response(
                        crossref_url,
                        json.dumps(
                            {
                                "message": {
                                    "title": ["Conservative landing provenance"],
                                    "license": [
                                        {
                                            "URL": "https://creativecommons.org/licenses/by/4.0/",
                                            "content-version": "vor",
                                            "start": {"timestamp": 0},
                                        }
                                    ],
                                }
                            }
                        ).encode(),
                    )
                }
            ),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        candidates, _metadata = provider._discover(
            CanonicalIdentifierSet.resolve([doi]),
            attempts=[],
        )
        landing = next(
            candidate
            for candidate in candidates
            if candidate.route == "elsevier-landing-meta"
        )

        self.assertEqual(landing.artifact_type, "pdf")
        self.assertEqual(landing.artifact_version, "unknown")
        self.assertEqual(landing.license, "")

    def test_retryable_is_not_collapsed_into_unavailable(self) -> None:
        doi = "10.1000/retry"
        encoded = urllib.parse.quote(doi, safe="")
        urls = {
            f"https://api.crossref.org/works/{encoded}": response("https://api.crossref.org", b"", status=503),
            f"https://api.datacite.org/dois/{encoded}": response("https://api.datacite.org", b"", status=503),
            f"https://api.unpaywall.org/v2/{encoded}?email=test%40example.org": response("https://api.unpaywall.org", b"", status=503),
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{encoded}?fields=openAccessPdf": response("https://api.semanticscholar.org", b"", status=429),
            (
                "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
                f"?ids={encoded}&format=json&versions=yes&tool=rkf&email=test%40example.org"
            ): response("https://pmc.ncbi.nlm.nih.gov", b"", status=503),
            f"https://doi.org/{urllib.parse.quote(doi, safe='/():;%<>=')}": response("https://doi.org", b"", status=503),
        }
        provider = PortableScientificAcquisitionProvider(
            contact_email="test@example.org",
            http_client=FakeHTTP(urls),
            policy=AcquisitionPolicy(courtesy_interval_s=0),
        )

        result = provider.obtain(
            source_id="retry",
            identifier=doi,
            project_id=PROJECT_ID,
            activation_id=ACTIVATION_ID,
        )

        self.assertEqual(result.status, "retryable")
        self.assertNotEqual(result.status, "unavailable")

    def test_external_paper_fetch_exit_four_is_serial_retry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            storage_root = Path(directory) / "artifacts"
            provider = ExternalPaperFetchProvider(
                ["python", "paper_fetch.py"],
                storage_root=storage_root,
                storage_boundary=Path(directory),
            )
            completed = BoundedProcessResult(4, stdout="{}", stderr="busy")

            def leave_partial_output(command, **_kwargs):
                Path(command[-1]).write_bytes(b"partial")
                return completed

            with patch("rkf.acquisition.run_bounded_process", side_effect=leave_partial_output):
                result = provider.obtain(
                    source_id="fixture",
                    identifier="10.1000/fixture",
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

            self.assertEqual(result.status, "retryable")
            self.assertIn("PROFILE_BUSY", result.blocker_codes)
            self.assertEqual(list(storage_root.glob(".*.download")), [])

    def test_external_paper_fetch_exposes_only_strict_tried_route_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            storage_root = boundary / "artifacts"
            provider = ExternalPaperFetchProvider(
                ["python", "paper_fetch.py"],
                storage_root=storage_root,
                storage_boundary=boundary,
            )

            def report_sensitive_attempts(command, **_kwargs):
                Path(command[-1]).write_bytes(b"partial")
                return BoundedProcessResult(
                    2,
                    stdout=json.dumps(
                        {
                            "ok": False,
                            "route": "https://resolver.example/paper?token=secret",
                            "tried": [
                                "Wiley",
                                "Unpaywall",
                                "wiley",
                                "secret-token-abc123",
                                "https://resolver.example/paper?token=secret",
                                "trusted-route\nsecret-token",
                                "../private/token",
                                "route?api_key=secret",
                                "a" * 97,
                                "",
                            ],
                        }
                    ),
                    stderr="",
                )

            with patch("rkf.acquisition.run_bounded_process", side_effect=report_sensitive_attempts):
                result = provider.obtain(
                    source_id="fixture",
                    identifier="10.1000/fixture",
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

            self.assertEqual(
                result.tried_routes,
                ("wiley", "unpaywall"),
            )
            exposed = " ".join(result.tried_routes)
            self.assertNotIn("token", exposed)
            self.assertNotIn("secret", exposed)
            self.assertNotIn("\n", exposed)
            self.assertEqual(result.route, "external-paper-fetch")
            self.assertEqual(list(storage_root.glob(".*.download")), [])

    def test_private_artifact_store_rejects_an_ancestor_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            outside = boundary / "outside"
            outside.mkdir()
            linked_parent = boundary / "private"
            linked_parent.symlink_to(outside, target_is_directory=True)
            store = PrivateArtifactStore(
                linked_parent / "artifacts",
                boundary_root=boundary,
            )
            content = pdf_fixture()
            digest = hashlib.sha256(content).hexdigest()

            with self.assertRaisesRegex(ValueError, "unsafe path component"):
                store.store_pdf(content, digest)

            self.assertFalse((outside / "artifacts").exists())

    def test_private_artifact_store_writes_below_boundary_with_private_modes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            storage_root = boundary / "private" / "artifacts"
            store = PrivateArtifactStore(storage_root, boundary_root=boundary)
            content = pdf_fixture()
            digest = hashlib.sha256(content).hexdigest()

            target = store.store_pdf(content, digest)
            reused = store.store_pdf(content, digest)

            self.assertEqual(target, reused)
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(storage_root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_private_artifact_store_reuses_concurrent_identical_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            storage_root = boundary / "private" / "artifacts"
            store = PrivateArtifactStore(storage_root, boundary_root=boundary)
            content = pdf_fixture()
            digest = hashlib.sha256(content).hexdigest()

            with ThreadPoolExecutor(max_workers=8) as executor:
                targets = list(
                    executor.map(
                        lambda _index: store.store_pdf(content, digest),
                        range(32),
                    )
                )

            self.assertEqual(set(targets), {storage_root / f"{digest}.pdf"})
            self.assertEqual(targets[0].read_bytes(), content)
            self.assertEqual(list(storage_root.glob(".artifact-*.tmp")), [])

    def test_external_paper_fetch_rejects_and_unlinks_symlink_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            storage_root = boundary / "artifacts"
            symlink_target = boundary / "outside.pdf"
            symlink_target.write_bytes(pdf_fixture())
            provider = ExternalPaperFetchProvider(
                ["python", "paper_fetch.py"],
                storage_root=storage_root,
                storage_boundary=boundary,
            )

            def leave_symlink_output(command, **_kwargs):
                Path(command[-1]).symlink_to(symlink_target)
                return BoundedProcessResult(
                    0,
                    stdout=json.dumps({"ok": True, "route": "fixture"}),
                    stderr="",
                )

            with patch("rkf.acquisition.run_bounded_process", side_effect=leave_symlink_output):
                result = provider.obtain(
                    source_id="fixture",
                    identifier="10.1000/fixture",
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

            self.assertEqual(result.status, "invalid-artifact")
            self.assertIn("PROVIDER_FILE_UNSAFE", result.blocker_codes)
            self.assertEqual(symlink_target.read_bytes(), pdf_fixture())
            self.assertEqual(list(storage_root.glob(".*.download")), [])

    def test_external_paper_fetch_rejects_oversized_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            storage_root = boundary / "artifacts"
            provider = ExternalPaperFetchProvider(
                ["python", "paper_fetch.py"],
                storage_root=storage_root,
                storage_boundary=boundary,
                max_artifact_bytes=32,
            )

            def leave_oversized_output(command, **_kwargs):
                Path(command[-1]).write_bytes(b"x" * 33)
                return BoundedProcessResult(
                    0,
                    stdout=json.dumps({"ok": True, "route": "fixture"}),
                    stderr="",
                )

            with patch("rkf.acquisition.run_bounded_process", side_effect=leave_oversized_output):
                result = provider.obtain(
                    source_id="fixture",
                    identifier="10.1000/fixture",
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

            self.assertEqual(result.status, "invalid-artifact")
            self.assertIn("PROVIDER_FILE_TOO_LARGE", result.blocker_codes)
            self.assertEqual(list(storage_root.glob(".*.download")), [])

    def test_external_paper_fetch_timeout_cleans_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            boundary = Path(directory)
            storage_root = boundary / "artifacts"
            provider = ExternalPaperFetchProvider(
                ["python", "paper_fetch.py"],
                storage_root=storage_root,
                storage_boundary=boundary,
                timeout_seconds=1,
            )

            def time_out_with_partial_output(command, **_kwargs):
                Path(command[-1]).write_bytes(b"partial")
                return BoundedProcessResult(
                    -9,
                    stdout="",
                    stderr="",
                    timed_out=True,
                )

            with patch("rkf.acquisition.run_bounded_process", side_effect=time_out_with_partial_output):
                result = provider.obtain(
                    source_id="fixture",
                    identifier="10.1000/fixture",
                    project_id=PROJECT_ID,
                    activation_id=ACTIVATION_ID,
                )

            self.assertEqual(result.status, "retryable")
            self.assertIn("WATCHDOG_OR_COMMAND_TIMEOUT", result.blocker_codes)
            self.assertEqual(list(storage_root.glob(".*.download")), [])

    def test_acquisition_run_is_private_redacted_and_review_loadable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            result = PortableScientificAcquisitionProvider(
                http_client=FakeHTTP({}),
                policy=AcquisitionPolicy(courtesy_interval_s=0),
            )
            # Use a typed fixture result so this test stays zero-network.
            fixture = FullTextProviderResult(
                status="manual-required",
                provider=result.name,
                provider_version=result.version,
                acquisition_run_id="acq_1234567890abcdef12345678",
                identifier_types=("doi",),
                blocker_codes=("MANUAL_RESOLVER_REQUIRED",),
            )
            run = register_acquisition_run(
                workspace,
                result=fixture,
                identifier="10.1073/pnas.1607171113",
                source_id="pnas-fixture",
                paper_id="papers/pnas-fixture",
                origin_project_id=PROJECT_ID,
                activation_id=ACTIVATION_ID,
            )
            loaded = load_acquisition_runs(workspace, status="manual-required")

            self.assertEqual(loaded, [run])
            self.assertNotIn("10.1073/pnas.1607171113", json.dumps(run))
            self.assertTrue(run["paths_redacted"])
            self.assertEqual(
                (workspace.root / ".rkf_private" / "acquisition" / "runs" / f"{run['acquisition_run_id']}.json").stat().st_mode & 0o777,
                0o600,
            )

    def test_action_scoped_run_id_includes_paper_identity(self) -> None:
        provider_result = FullTextProviderResult(
            status="manual-required",
            provider="fixture",
            provider_version="1",
            acquisition_run_id="acq_1234567890abcdef12345678",
            blocker_codes=("MANUAL_RESOLVER_REQUIRED",),
        )
        base_identity = {
            "origin_project_id": PROJECT_ID,
            "activation_id": ACTIVATION_ID,
            "source_id": "shared-source",
            "identifier": "10.1000/shared",
        }

        first = ensure_acquisition_run_id(
            provider_result,
            identity={**base_identity, "paper_id": "papers/first"},
        )
        second = ensure_acquisition_run_id(
            provider_result,
            identity={**base_identity, "paper_id": "papers/second"},
        )

        self.assertNotEqual(first.acquisition_run_id, second.acquisition_run_id)
        self.assertEqual(
            first.acquisition_run_id,
            ensure_acquisition_run_id(
                provider_result,
                identity={**base_identity, "paper_id": "papers/first"},
            ).acquisition_run_id,
        )

    def test_acquisition_run_collision_ignores_volatile_elapsed_timings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            fixture = FullTextProviderResult(
                status="retryable",
                provider="fixture",
                provider_version="1",
                acquisition_run_id="acq_1234567890abcdef12345678",
                blocker_codes=("RATE_LIMITED",),
                elapsed_ms=10,
                attempts=(
                    AcquisitionAttempt(
                        "fixture-route",
                        "retryable",
                        "RATE_LIMITED",
                        elapsed_ms=3,
                    ),
                ),
            )
            registration = {
                "identifier": "10.1000/retry",
                "source_id": "retry-fixture",
                "paper_id": "papers/retry-fixture",
                "origin_project_id": PROJECT_ID,
                "activation_id": ACTIVATION_ID,
            }

            first = register_acquisition_run(
                workspace,
                result=fixture,
                **registration,
            )
            second = register_acquisition_run(
                workspace,
                result=replace(
                    fixture,
                    elapsed_ms=99,
                    attempts=(
                        AcquisitionAttempt(
                            "fixture-route",
                            "retryable",
                            "RATE_LIMITED",
                            elapsed_ms=42,
                        ),
                    ),
                ),
                **registration,
            )

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
