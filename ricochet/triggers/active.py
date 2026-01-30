"""
Active trigger probing for second-order execution contexts.

Probes common admin, support, and analytics endpoints to trigger stored
XSS payloads that would otherwise require manual admin access.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from ricochet.injection.http_client import send_request
from ricochet.injection.rate_limiter import RateLimiter


# Common endpoints where second-order payloads may render
TRIGGER_ENDPOINTS = [
    # Admin/Management
    "/admin",
    "/admin/users",
    "/admin/logs",
    "/admin/reports",
    "/dashboard",
    "/manage",
    "/panel",
    "/console",
    # Support/Helpdesk
    "/support",
    "/tickets",
    "/helpdesk",
    "/support/tickets",
    "/feedback",
    # Reporting/Analytics
    "/analytics",
    "/reports",
    "/stats",
    "/logs",
    "/metrics",
    # Content Management
    "/moderation",
    "/content",
    "/posts",
    "/comments",
    "/reviews",
    # Export Functions
    "/export",
    "/download",
    "/pdf",
    "/report/generate",
    "/print",
]


@dataclass
class TriggerResult:
    """
    Result of probing a single endpoint.

    Attributes:
        endpoint: The endpoint path that was probed
        status: HTTP status code (None if request failed)
        error: Error message (None if request succeeded)
        response_size: Size of response body in bytes
    """

    endpoint: str
    status: Optional[int]
    error: Optional[str]
    response_size: int


class ActiveTrigger:
    """
    Active trigger prober for second-order execution contexts.

    Probes common admin/support/analytics endpoints to trigger stored
    payloads. Uses rate limiting to avoid overwhelming targets.

    Args:
        base_url: Target base URL (e.g., https://target.com)
        rate_limit: Requests per second (default: 2.0, slower than injection)
        timeout: Request timeout in seconds (default: 10.0)
        proxy_url: Optional HTTP proxy URL

    Example:
        >>> trigger = ActiveTrigger("https://target.com", rate_limit=1.0)
        >>> results = trigger.probe_all()
        >>> for r in results:
        ...     if r.status == 200:
        ...         print(f"[+] {r.endpoint} accessible")
    """

    def __init__(
        self,
        base_url: str,
        rate_limit: float = 2.0,
        timeout: float = 10.0,
        proxy_url: Optional[str] = None,
    ) -> None:
        # Normalize base URL (remove trailing slash)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._proxy_url = proxy_url
        self._rate_limiter = RateLimiter(rate=rate_limit, burst=1)

    @property
    def base_url(self) -> str:
        """Target base URL."""
        return self._base_url

    def probe_endpoint(self, endpoint: str) -> TriggerResult:
        """
        Probe a single endpoint.

        Args:
            endpoint: Endpoint path (e.g., /admin)

        Returns:
            TriggerResult with status/error and response size
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = f"{self._base_url}{endpoint}"

        try:
            response = send_request(
                url=url,
                method="GET",
                timeout=self._timeout,
                verify_ssl=False,
                proxy_url=self._proxy_url,
            )
            return TriggerResult(
                endpoint=endpoint,
                status=response.status,
                error=None,
                response_size=len(response.body),
            )

        except TimeoutError:
            return TriggerResult(
                endpoint=endpoint,
                status=None,
                error="timeout",
                response_size=0,
            )

        except ConnectionError as e:
            return TriggerResult(
                endpoint=endpoint,
                status=None,
                error=str(e),
                response_size=0,
            )

    def probe_all(
        self,
        endpoints: Optional[list[str]] = None,
        callback: Optional[Callable[[TriggerResult], None]] = None,
    ) -> list[TriggerResult]:
        """
        Probe multiple endpoints with rate limiting.

        Args:
            endpoints: List of endpoints to probe (default: TRIGGER_ENDPOINTS)
            callback: Optional function called with each result

        Returns:
            List of TriggerResult for all probed endpoints
        """
        if endpoints is None:
            endpoints = TRIGGER_ENDPOINTS

        results: list[TriggerResult] = []

        for endpoint in endpoints:
            # Rate limit between requests
            self._rate_limiter.acquire()

            result = self.probe_endpoint(endpoint)
            results.append(result)

            if callback is not None:
                callback(result)

        return results
