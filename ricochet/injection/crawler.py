"""
Web crawler for automatic injection point discovery.

Provides HTML parsing for link and form extraction, URL normalization,
and BFS-based crawling with configurable depth and rate limiting.
"""

import json
from collections import deque
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urldefrag, urlparse

from ricochet.injection.http_client import send_request
from ricochet.injection.rate_limiter import RateLimiter


@dataclass
class FormData:
    """
    Extracted form data from HTML.

    Attributes:
        action: Form action URL (relative or absolute)
        method: HTTP method (GET or POST)
        inputs: List of (name, type, value) tuples for form inputs
    """

    action: str
    method: str
    inputs: list[tuple[str, str, str]] = field(default_factory=list)


@dataclass
class ExtractedData:
    """
    Data extracted from a single HTML page.

    Attributes:
        links: List of href values from anchor tags
        forms: List of FormData objects
    """

    links: list[str] = field(default_factory=list)
    forms: list[FormData] = field(default_factory=list)


@dataclass
class CrawlResult:
    """
    Result from crawling a single page.

    Attributes:
        url: The URL that was crawled
        depth: Depth in the crawl tree (0 for seed URL)
        forms: Forms discovered on this page
        links: Links discovered on this page
        error: Error message if crawl failed, None otherwise
    """

    url: str
    depth: int
    forms: list[FormData] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class CrawlVector:
    """
    An injectable vector discovered during crawling.

    Attributes:
        url: Target URL for injection
        method: HTTP method (GET or POST)
        param_name: Name of the parameter to inject into
        param_type: Type of input (text, hidden, password, etc.)
        location: Where the parameter is located (form, query, body)
    """

    url: str
    method: str
    param_name: str
    param_type: str
    location: str  # 'form', 'query', 'body'


# File extensions to skip during crawling (binary/non-HTML content)
SKIP_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".bmp",
    ".tiff",
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".zip",
    ".tar",
    ".gz",
    ".rar",
    ".7z",
    ".exe",
    ".dmg",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".wav",
    ".ogg",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}


class LinkFormExtractor(HTMLParser):
    """
    HTML parser that extracts links and forms from HTML content.

    Usage:
        extractor = LinkFormExtractor()
        data = extractor.extract(html_content)
        print(data.links)  # ['/', '/about', '/contact']
        print(data.forms)  # [FormData(...), ...]
    """

    def __init__(self):
        """Initialize the extractor."""
        super().__init__()
        self._reset_state()

    def _reset_state(self):
        """Reset internal state for a new extraction."""
        self.result = ExtractedData()
        self._current_form: Optional[FormData] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Handle opening tags - extract links, forms, and inputs."""
        attrs_dict = {k: v for k, v in attrs if v is not None}

        if tag == "a":
            # Extract href from anchor tags
            href = attrs_dict.get("href")
            if href:
                self.result.links.append(href)

        elif tag == "form":
            # Start a new form
            action = attrs_dict.get("action", "")
            method = attrs_dict.get("method", "GET").upper()
            self._current_form = FormData(action=action, method=method)

        elif tag in ("input", "select", "textarea") and self._current_form is not None:
            # Collect form inputs
            name = attrs_dict.get("name", "")
            if name:  # Only collect inputs with names
                input_type = attrs_dict.get("type", "text")
                value = attrs_dict.get("value", "")
                self._current_form.inputs.append((name, input_type, value))

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags - close forms."""
        if tag == "form" and self._current_form is not None:
            self.result.forms.append(self._current_form)
            self._current_form = None

    def extract(self, html: str) -> ExtractedData:
        """
        Extract links and forms from HTML content.

        Args:
            html: HTML content to parse

        Returns:
            ExtractedData with discovered links and forms
        """
        self._reset_state()
        try:
            self.feed(html)
        except Exception:
            # Malformed HTML - return what we have
            pass

        # Handle unclosed form tag
        if self._current_form is not None:
            self.result.forms.append(self._current_form)
            self._current_form = None

        return self.result


def normalize_url(base_url: str, href: str) -> Optional[str]:
    """
    Normalize a URL relative to a base URL.

    Args:
        base_url: The page URL where the link was found
        href: The href value to normalize

    Returns:
        Normalized absolute URL, or None if URL should be skipped
    """
    # Skip non-HTTP schemes
    href_lower = href.lower().strip()
    if href_lower.startswith(("javascript:", "mailto:", "tel:", "data:", "#")):
        return None

    # Join with base URL
    full_url = urljoin(base_url, href)

    # Remove fragment
    full_url, _ = urldefrag(full_url)

    # Validate scheme
    parsed = urlparse(full_url)
    if parsed.scheme not in ("http", "https"):
        return None

    # Ensure we have a host
    if not parsed.netloc:
        return None

    return full_url


def is_same_domain(base_url: str, target_url: str) -> bool:
    """
    Check if two URLs are on the same domain.

    Args:
        base_url: The base/seed URL
        target_url: The URL to check

    Returns:
        True if both URLs have the same netloc (domain:port)
    """
    base_parsed = urlparse(base_url)
    target_parsed = urlparse(target_url)
    return base_parsed.netloc.lower() == target_parsed.netloc.lower()


def is_crawlable_url(url: str) -> bool:
    """
    Check if a URL points to crawlable content (not binary files).

    Args:
        url: URL to check

    Returns:
        True if URL appears to be crawlable HTML content
    """
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Check for skip extensions
    for ext in SKIP_EXTENSIONS:
        if path.endswith(ext):
            return False

    return True


class Crawler:
    """
    Web crawler for discovering injection points.

    Performs BFS crawling from a seed URL, extracting links and forms
    while respecting depth, page limits, and rate limiting.

    Attributes:
        max_depth: Maximum crawl depth from seed URL
        max_pages: Maximum pages to crawl
        timeout: Request timeout in seconds
        rate_limit: Maximum requests per second
    """

    def __init__(
        self,
        max_depth: int = 2,
        max_pages: int = 100,
        timeout: float = 10.0,
        rate_limit: float = 10.0,
    ):
        """
        Initialize the crawler.

        Args:
            max_depth: Maximum depth to crawl (0 = seed only)
            max_pages: Maximum number of pages to crawl
            timeout: Request timeout in seconds
            rate_limit: Maximum requests per second
        """
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout
        self._rate_limiter = RateLimiter(rate=rate_limit, burst=1)
        self._extractor = LinkFormExtractor()

    def crawl(self, seed_url: str) -> list[CrawlResult]:
        """
        Crawl a website starting from the seed URL.

        Uses BFS to discover pages up to max_depth, respecting max_pages
        and rate limiting constraints.

        Args:
            seed_url: Starting URL for the crawl

        Returns:
            List of CrawlResult objects for each page visited
        """
        # Normalize seed URL
        parsed = urlparse(seed_url)
        if not parsed.scheme:
            seed_url = f"http://{seed_url}"

        results: list[CrawlResult] = []
        visited: set[str] = set()

        # BFS queue: (url, depth)
        queue: deque[tuple[str, int]] = deque()
        queue.append((seed_url, 0))
        visited.add(seed_url)

        while queue and len(results) < self.max_pages:
            url, depth = queue.popleft()

            # Process this page
            result = self._process_page(url, depth)
            results.append(result)

            # Don't follow links from pages with errors or at max depth
            if result.error or depth >= self.max_depth:
                continue

            # Queue new links
            for link in result.links:
                normalized = normalize_url(url, link)
                if normalized is None:
                    continue

                # Same-domain check
                if not is_same_domain(seed_url, normalized):
                    continue

                # Skip binary files
                if not is_crawlable_url(normalized):
                    continue

                # Skip already visited
                if normalized in visited:
                    continue

                # Add to queue
                visited.add(normalized)
                queue.append((normalized, depth + 1))

        return results

    def _process_page(self, url: str, depth: int) -> CrawlResult:
        """
        Fetch and process a single page.

        Args:
            url: URL to fetch
            depth: Current crawl depth

        Returns:
            CrawlResult with extracted data or error
        """
        # Rate limit
        self._rate_limiter.acquire()

        try:
            response = send_request(
                url=url,
                method="GET",
                timeout=self.timeout,
                verify_ssl=False,  # Security testing often targets self-signed certs
            )

            # Check for HTML content
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                return CrawlResult(
                    url=url,
                    depth=depth,
                    error=f"Non-HTML content: {content_type}",
                )

            # Parse HTML
            try:
                html = response.body.decode("utf-8", errors="replace")
            except Exception as e:
                return CrawlResult(
                    url=url,
                    depth=depth,
                    error=f"Failed to decode body: {e}",
                )

            extracted = self._extractor.extract(html)

            return CrawlResult(
                url=url,
                depth=depth,
                forms=extracted.forms,
                links=extracted.links,
            )

        except TimeoutError as e:
            return CrawlResult(url=url, depth=depth, error=str(e))

        except ConnectionError as e:
            return CrawlResult(url=url, depth=depth, error=str(e))

        except Exception as e:
            return CrawlResult(url=url, depth=depth, error=f"Unexpected error: {e}")


def results_to_vectors(results: list[CrawlResult]) -> list[CrawlVector]:
    """
    Convert crawl results to injectable vectors.

    Extracts form inputs and query parameters as injection targets.

    Args:
        results: List of CrawlResult from crawling

    Returns:
        List of CrawlVector objects representing injection points
    """
    vectors: list[CrawlVector] = []

    for result in results:
        if result.error:
            continue

        # Extract vectors from forms
        for form in result.forms:
            # Resolve form action URL
            action_url = normalize_url(result.url, form.action) or result.url

            for name, input_type, _ in form.inputs:
                # Skip submit buttons
                if input_type.lower() in ("submit", "button", "image", "reset"):
                    continue

                # Determine location based on method
                location = "body" if form.method == "POST" else "query"

                vectors.append(
                    CrawlVector(
                        url=action_url,
                        method=form.method,
                        param_name=name,
                        param_type=input_type,
                        location=location,
                    )
                )

        # Extract query parameters from URL
        parsed = urlparse(result.url)
        if parsed.query:
            # Parse query string manually to preserve order and duplicates
            for param in parsed.query.split("&"):
                if "=" in param:
                    name, _ = param.split("=", 1)
                    if name:
                        vectors.append(
                            CrawlVector(
                                url=result.url,
                                method="GET",
                                param_name=name,
                                param_type="query",
                                location="query",
                            )
                        )

    # Deduplicate vectors (same url, method, param_name, location)
    seen: set[tuple[str, str, str, str]] = set()
    unique_vectors: list[CrawlVector] = []

    for v in vectors:
        key = (v.url, v.method, v.param_name, v.location)
        if key not in seen:
            seen.add(key)
            unique_vectors.append(v)

    return unique_vectors


def export_vectors(vectors: list[CrawlVector], filepath: Path) -> None:
    """
    Export crawl vectors to a JSON file.

    Args:
        vectors: List of CrawlVector objects to export
        filepath: Path to write JSON file
    """
    data = [
        {
            "url": v.url,
            "method": v.method,
            "param_name": v.param_name,
            "param_type": v.param_type,
            "location": v.location,
        }
        for v in vectors
    ]

    filepath.write_text(json.dumps(data, indent=2))


def load_crawl_vectors(filepath: Path) -> list[CrawlVector]:
    """
    Load crawl vectors from a JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        List of CrawlVector objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is malformed or missing required fields
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Vector file not found: {filepath}")

    try:
        data = json.loads(filepath.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {filepath}")

    vectors: list[CrawlVector] = []

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not an object")

        required = {"url", "method", "param_name", "param_type", "location"}
        missing = required - set(item.keys())
        if missing:
            raise ValueError(f"Item {i} missing required fields: {missing}")

        vectors.append(
            CrawlVector(
                url=item["url"],
                method=item["method"],
                param_name=item["param_name"],
                param_type=item["param_type"],
                location=item["location"],
            )
        )

    return vectors
