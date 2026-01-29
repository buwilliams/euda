"""Shared HTTP client for Euno skills."""

import base64
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Any
from xml.etree import ElementTree as ET


@dataclass
class HTTPResponse:
    """HTTP response with helper methods."""

    status: int
    body: bytes
    headers: dict[str, str]

    @property
    def ok(self) -> bool:
        """True if status is 2xx."""
        return 200 <= self.status < 300

    def text(self, encoding: str = "utf-8") -> str:
        """Decode body as text."""
        return self.body.decode(encoding, errors="replace")

    def json(self) -> Any:
        """Parse body as JSON."""
        return json.loads(self.body.decode("utf-8"))

    def xml(self) -> ET.Element:
        """Parse body as XML."""
        return ET.fromstring(self.body)


class HTTPClient:
    """HTTP client with consistent error handling.

    Provides a unified interface for making HTTP requests across skills,
    with configurable timeouts, user agent, and authentication.

    Example:
        client = HTTPClient(timeout=10, user_agent="Euno/1.0 (MySkill)")
        response = client.get("https://example.com/api/data")
        if response.ok:
            data = response.json()
    """

    DEFAULT_USER_AGENT = "Euno/1.0"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        base_url: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        """Initialize HTTP client.

        Args:
            base_url: Base URL prepended to all request paths
            timeout: Default request timeout in seconds
            user_agent: User-Agent header value
        """
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.timeout = timeout
        self.user_agent = user_agent
        self._auth_header: Optional[str] = None

    def set_basic_auth(self, username: str, password: str) -> None:
        """Set Basic authentication credentials."""
        credentials = f"{username}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"

    def set_bearer_token(self, token: str) -> None:
        """Set Bearer token authentication."""
        self._auth_header = f"Bearer {token}"

    def request(
        self,
        method: str,
        url: str,
        data: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> HTTPResponse:
        """Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: URL path (joined with base_url) or full URL
            data: Request body bytes
            headers: Additional headers
            timeout: Request timeout (uses default if not specified)

        Returns:
            HTTPResponse with status, body, and headers

        Raises:
            ConnectionError: Network failure or connection refused
        """
        # Build full URL
        if url.startswith(("http://", "https://")):
            full_url = url
        else:
            full_url = f"{self.base_url}{url}"

        # Build headers
        req_headers = {"User-Agent": self.user_agent}
        if self._auth_header:
            req_headers["Authorization"] = self._auth_header
        if headers:
            req_headers.update(headers)

        # Create request
        req = urllib.request.Request(
            full_url, data=data, headers=req_headers, method=method
        )

        # Execute request
        try:
            with urllib.request.urlopen(
                req, timeout=timeout or self.timeout
            ) as response:
                return HTTPResponse(
                    status=response.status,
                    body=response.read(),
                    headers=dict(response.headers),
                )
        except urllib.error.HTTPError as e:
            return HTTPResponse(
                status=e.code,
                body=e.read(),
                headers=dict(e.headers),
            )
        except urllib.error.URLError as e:
            raise ConnectionError(f"Could not connect: {e.reason}") from e
        except TimeoutError as e:
            raise ConnectionError(f"Request timed out after {timeout or self.timeout}s") from e

    def get(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> HTTPResponse:
        """Make a GET request."""
        return self.request("GET", url, headers=headers, timeout=timeout)

    def post(
        self,
        url: str,
        data: Optional[bytes] = None,
        json_data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> HTTPResponse:
        """Make a POST request.

        Args:
            url: URL path or full URL
            data: Raw bytes body
            json_data: Data to serialize as JSON (sets Content-Type)
            headers: Additional headers
            timeout: Request timeout
        """
        req_headers = headers.copy() if headers else {}
        if json_data is not None:
            data = json.dumps(json_data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        return self.request("POST", url, data=data, headers=req_headers, timeout=timeout)

    def put(
        self,
        url: str,
        data: Optional[bytes] = None,
        json_data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> HTTPResponse:
        """Make a PUT request."""
        req_headers = headers.copy() if headers else {}
        if json_data is not None:
            data = json.dumps(json_data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        return self.request("PUT", url, data=data, headers=req_headers, timeout=timeout)

    def delete(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> HTTPResponse:
        """Make a DELETE request."""
        return self.request("DELETE", url, headers=headers, timeout=timeout)

    @classmethod
    def fetch(
        cls,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> HTTPResponse:
        """One-off fetch without creating a client instance.

        Args:
            url: Full URL to fetch
            headers: Additional headers
            timeout: Request timeout
            user_agent: User-Agent header

        Returns:
            HTTPResponse

        Raises:
            ConnectionError: Network failure
        """
        client = cls(timeout=timeout, user_agent=user_agent)
        return client.get(url, headers=headers)
