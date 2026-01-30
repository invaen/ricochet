# Phase 5: Crawler & Payloads - Research

**Researched:** 2026-01-29
**Domain:** Web crawling, HTML parsing, link/form extraction, payload file loading
**Confidence:** HIGH (stdlib-only, well-documented APIs)

## Summary

Phase 5 adds two capabilities to Ricochet: (1) automatic discovery of injection points via web crawling, and (2) loading custom payloads from files. Both features leverage Python's stdlib exclusively, continuing the zero-dependency constraint.

For crawling, Python provides `html.parser.HTMLParser` for HTML parsing and `urllib.parse` for URL handling. The crawler will extract links (`<a href>`), forms (`<form action>` with `<input>`/`<select>`/`<textarea>`), and URL parameters. The existing `http_client.py` from Phase 4 handles all HTTP operations. URL normalization and same-domain filtering use `urllib.parse.urljoin()` and `urlparse()`.

For payload loading, a simple line-by-line file reader with filtering (skip comments, blank lines) provides maximum compatibility with existing wordlist formats (SecLists, Wfuzz, custom). The existing `{{CALLBACK}}` placeholder substitution from `injector.py` already handles correlation ID embedding.

**Primary recommendation:** Build a `LinkFormExtractor` subclass of `HTMLParser`, a `Crawler` class using BFS with depth limiting, and a `load_payloads()` function that reads line-delimited payload files.

## Standard Stack

The established libraries/tools for this domain (stdlib only per constraint):

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `html.parser.HTMLParser` | stdlib | HTML parsing for link/form extraction | Only stdlib HTML parser option |
| `urllib.parse` | stdlib | urljoin, urlparse, urldefrag | URL normalization and resolution |
| `collections.deque` | stdlib | BFS queue for crawling | O(1) append/popleft |
| `urllib.robotparser` | stdlib | robots.txt compliance (optional) | Ethical crawling support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.parse.parse_qsl` | stdlib | Extract form field values | Hidden field extraction |
| `re` | stdlib | Pattern matching | Filter file extensions, URLs |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTMLParser | regex extraction | Less robust, breaks on malformed HTML |
| BFS crawling | DFS | BFS respects depth limit more naturally |
| Line-delimited payloads | JSON/YAML | Simpler, compatible with existing wordlists |

**Installation:**
```bash
# No installation needed - all stdlib
python -c "from html.parser import HTMLParser; from collections import deque; import urllib.parse"
```

## Architecture Patterns

### Recommended Project Structure
```
ricochet/
├── injection/
│   ├── __init__.py         # Export Crawler, load_payloads
│   ├── parser.py           # (existing) ParsedRequest
│   ├── injector.py         # (existing) Injector class
│   ├── http_client.py      # (existing) send_request
│   ├── vectors.py          # (existing) InjectionVector, extract_vectors
│   ├── crawler.py          # NEW: Crawler class, link/form extraction
│   └── payloads.py         # NEW: load_payloads() function
└── cli.py                  # Add 'crawl' subcommand, --payloads flag
```

### Pattern 1: HTMLParser Subclass for Link/Form Extraction
**What:** Custom HTMLParser that collects links and forms during parsing
**When to use:** Processing crawled HTML responses
**Example:**
```python
# Source: Python html.parser documentation
from html.parser import HTMLParser
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class FormData:
    """Extracted HTML form with its inputs."""
    action: str                              # Form action URL
    method: str                              # GET or POST
    inputs: list[tuple[str, str, str]]       # (name, type, value)

@dataclass
class ExtractedData:
    """All extracted links and forms from a page."""
    links: list[str] = field(default_factory=list)
    forms: list[FormData] = field(default_factory=list)

class LinkFormExtractor(HTMLParser):
    """Extract links and forms from HTML content."""

    def __init__(self):
        super().__init__()
        self.result = ExtractedData()
        self._current_form: Optional[FormData] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)

        if tag == 'a':
            href = attrs_dict.get('href')
            if href:
                self.result.links.append(href)

        elif tag == 'form':
            action = attrs_dict.get('action', '')
            method = attrs_dict.get('method', 'GET').upper()
            self._current_form = FormData(action=action, method=method, inputs=[])

        elif tag in ('input', 'select', 'textarea') and self._current_form:
            name = attrs_dict.get('name', '')
            input_type = attrs_dict.get('type', 'text')
            value = attrs_dict.get('value', '')
            if name:  # Only track named inputs
                self._current_form.inputs.append((name, input_type, value))

    def handle_endtag(self, tag: str) -> None:
        if tag == 'form' and self._current_form:
            self.result.forms.append(self._current_form)
            self._current_form = None

    def extract(self, html: str) -> ExtractedData:
        """Parse HTML and return extracted data."""
        self.reset()
        self.result = ExtractedData()
        self._current_form = None
        self.feed(html)
        return self.result
```

### Pattern 2: URL Normalization and Same-Domain Filtering
**What:** Resolve relative URLs and filter to same domain
**When to use:** Processing extracted links before adding to crawl queue
**Example:**
```python
# Source: Python urllib.parse documentation
from urllib.parse import urljoin, urlparse, urldefrag

def normalize_url(base_url: str, href: str) -> Optional[str]:
    """Normalize a href relative to base_url.

    Returns absolute URL or None if should be skipped.
    """
    # Remove fragment (we don't care about anchors)
    href, _ = urldefrag(href)
    if not href:
        return None

    # Skip non-HTTP schemes
    if href.startswith(('javascript:', 'mailto:', 'tel:', 'data:')):
        return None

    # Resolve relative to absolute
    absolute = urljoin(base_url, href)

    # Validate scheme
    parsed = urlparse(absolute)
    if parsed.scheme not in ('http', 'https'):
        return None

    return absolute

def is_same_domain(base_url: str, target_url: str) -> bool:
    """Check if target_url is same domain as base_url."""
    base_parsed = urlparse(base_url)
    target_parsed = urlparse(target_url)
    return base_parsed.netloc == target_parsed.netloc

def is_crawlable_url(url: str) -> bool:
    """Check if URL points to crawlable content (not binary files)."""
    # Skip common non-HTML extensions
    skip_extensions = {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
        '.css', '.js', '.ico', '.woff', '.woff2', '.ttf', '.eot',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    }
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    return not any(path_lower.endswith(ext) for ext in skip_extensions)
```

### Pattern 3: BFS Crawler with Depth Limiting
**What:** Crawl pages breadth-first with configurable depth limit
**When to use:** Auto-discovering injection points across a site
**Example:**
```python
# Source: Standard BFS algorithm + web crawling best practices
from collections import deque
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class CrawlResult:
    """Result of crawling a single URL."""
    url: str
    depth: int
    vectors: list['InjectionVector']  # From extract_vectors
    forms: list[FormData]
    error: Optional[str] = None

class Crawler:
    """BFS web crawler with depth limiting and same-domain filtering."""

    def __init__(
        self,
        http_client: Callable[[str], 'HttpResponse'],
        max_depth: int = 2,
        max_pages: int = 100,
        same_domain_only: bool = True,
    ):
        self.http_client = http_client
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.same_domain_only = same_domain_only
        self.visited: set[str] = set()
        self.results: list[CrawlResult] = []

    def crawl(self, seed_url: str) -> list[CrawlResult]:
        """Crawl starting from seed_url, discovering injection points."""
        queue: deque[tuple[str, int]] = deque([(seed_url, 0)])
        self.visited = set()
        self.results = []

        while queue and len(self.visited) < self.max_pages:
            url, depth = queue.popleft()

            # Skip if already visited
            if url in self.visited:
                continue
            self.visited.add(url)

            # Fetch and parse page
            result = self._process_page(url, depth)
            self.results.append(result)

            # Don't follow links beyond max_depth
            if depth >= self.max_depth:
                continue

            if result.error:
                continue

            # Queue discovered links
            # (links extracted in _process_page)
            for link in self._get_links_from_result(result):
                normalized = normalize_url(url, link)
                if normalized and normalized not in self.visited:
                    if not self.same_domain_only or is_same_domain(seed_url, normalized):
                        if is_crawlable_url(normalized):
                            queue.append((normalized, depth + 1))

        return self.results

    def _process_page(self, url: str, depth: int) -> CrawlResult:
        """Fetch page and extract injection vectors."""
        try:
            response = self.http_client(url)

            # Extract links and forms from HTML
            extractor = LinkFormExtractor()
            html = response.body.decode('utf-8', errors='replace')
            extracted = extractor.extract(html)

            # Build vectors from URL params and forms
            vectors = self._extract_url_vectors(url)
            vectors.extend(self._extract_form_vectors(extracted.forms, url))

            # Store links for later queuing (pattern differs slightly)
            result = CrawlResult(
                url=url,
                depth=depth,
                vectors=vectors,
                forms=extracted.forms,
            )
            result._links = extracted.links  # Temporary storage
            return result

        except Exception as e:
            return CrawlResult(
                url=url,
                depth=depth,
                vectors=[],
                forms=[],
                error=str(e),
            )
```

### Pattern 4: Payload File Loading
**What:** Load payloads from line-delimited text files
**When to use:** User provides custom payload file with --payloads
**Example:**
```python
# Source: Standard practice for wordlist loading (SecLists, Wfuzz compatible)
from pathlib import Path
from typing import Iterator

def load_payloads(filepath: Path) -> list[str]:
    """Load payloads from a text file.

    File format:
    - One payload per line
    - Lines starting with # are comments (skipped)
    - Blank lines are skipped
    - Whitespace is preserved within payloads

    Args:
        filepath: Path to payload file

    Returns:
        List of payload strings

    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file isn't valid UTF-8
    """
    payloads = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip only the trailing newline, preserve other whitespace
            line = line.rstrip('\n\r')

            # Skip comments and blank lines
            if not line or line.startswith('#'):
                continue

            payloads.append(line)

    return payloads

def load_payloads_streaming(filepath: Path) -> Iterator[str]:
    """Generator version for large payload files.

    Use when payload file is too large to load into memory.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n\r')
            if not line or line.startswith('#'):
                continue
            yield line
```

### Anti-Patterns to Avoid
- **Parsing HTML with regex:** Use HTMLParser; regex breaks on malformed HTML
- **Not normalizing URLs:** Leads to duplicate crawling of same page
- **DFS without depth limit:** Can get stuck in infinite link loops
- **Loading entire payload file for each injection:** Load once, iterate many times
- **Not handling encoding errors:** HTML may not be valid UTF-8

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative URL resolution | String concatenation | `urllib.parse.urljoin()` | Handles edge cases (protocol-relative, query params) |
| URL normalization | Manual parsing | `urlparse()` + `urlunparse()` | Consistent handling of all URL components |
| HTML tag extraction | Regex like `<a href="([^"]+)">` | `HTMLParser` subclass | Handles quotes, entities, malformed HTML |
| Fragment removal | `url.split('#')[0]` | `urldefrag()` | Returns both parts, handles edge cases |
| Queue data structure | List with pop(0) | `collections.deque` | O(1) vs O(n) for popleft |

**Key insight:** URL handling has many subtle edge cases. `urljoin()` is RFC-compliant and handles protocol-relative URLs (`//example.com`), query string preservation, and parent directory traversal (`../`). Hand-rolling this logic will have bugs.

## Common Pitfalls

### Pitfall 1: Infinite Crawl Loops
**What goes wrong:** Crawler visits same URLs forever due to normalization issues
**Why it happens:** URLs with different fragments/query orders treated as different
**How to avoid:** Normalize URLs before adding to visited set; use `urldefrag()` to remove fragments
**Warning signs:** Visited count grows without bound, same content fetched repeatedly

### Pitfall 2: Crawling Binary Files
**What goes wrong:** Crawler tries to parse PDFs/images as HTML
**Why it happens:** Following all links without checking Content-Type or extension
**How to avoid:** Check URL extension before queuing; check Content-Type header after fetching
**Warning signs:** UnicodeDecodeError, HTMLParser errors, slow crawling

### Pitfall 3: Following External Links
**What goes wrong:** Crawler escapes target domain and crawls the entire internet
**Why it happens:** Not checking domain before following links
**How to avoid:** Compare `urlparse(url).netloc` to seed domain
**Warning signs:** Crawling unexpected domains, callbacks from random IPs

### Pitfall 4: Form Action Resolution
**What goes wrong:** Form action URLs not resolved relative to page URL
**Why it happens:** Using action value directly without urljoin
**How to avoid:** Always use `urljoin(page_url, form.action)` for form actions
**Warning signs:** 404s when submitting forms, wrong endpoints

### Pitfall 5: Hidden Input Fields Ignored
**What goes wrong:** CSRF tokens and other hidden fields not captured
**Why it happens:** Only extracting visible input fields
**How to avoid:** Extract all `<input>` regardless of type attribute
**Warning signs:** Form submissions fail, CSRF protection triggers

### Pitfall 6: Payload File Encoding Issues
**What goes wrong:** Non-ASCII payloads corrupted or cause errors
**Why it happens:** Reading file without explicit encoding
**How to avoid:** Always specify `encoding='utf-8'` when opening files
**Warning signs:** UnicodeDecodeError, garbled payload output

### Pitfall 7: Memory Exhaustion with Large Payload Files
**What goes wrong:** Loading millions of payloads into memory crashes
**Why it happens:** Reading entire file into list
**How to avoid:** Use streaming/generator approach for large files; document size limits
**Warning signs:** MemoryError, slow startup

## Code Examples

Verified patterns from official sources:

### Complete Link Extraction Example
```python
# Source: Python html.parser documentation
from html.parser import HTMLParser

class SimpleLinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and value:
                    self.links.append(value)

# Usage
parser = SimpleLinkExtractor()
parser.feed('<html><body><a href="/page1">Link</a></body></html>')
print(parser.links)  # ['/page1']
```

### URL Resolution Examples
```python
# Source: Python urllib.parse documentation
from urllib.parse import urljoin

base = 'http://www.example.com/dir/page.html'

# Relative path
urljoin(base, 'other.html')
# -> 'http://www.example.com/dir/other.html'

# Absolute path
urljoin(base, '/root.html')
# -> 'http://www.example.com/root.html'

# Protocol-relative
urljoin(base, '//other.com/page')
# -> 'http://other.com/page'  (inherits scheme)

# Parent directory
urljoin(base, '../sibling/page.html')
# -> 'http://www.example.com/sibling/page.html'

# Full URL (replaces base entirely)
urljoin(base, 'https://different.com/')
# -> 'https://different.com/'
```

### Converting Form to InjectionVectors
```python
# Source: Standard security testing practice
from urllib.parse import urljoin

def form_to_vectors(
    form: FormData,
    page_url: str
) -> tuple[str, list[InjectionVector]]:
    """Convert extracted form to injection vectors.

    Returns:
        Tuple of (resolved action URL, list of vectors)
    """
    # Resolve form action relative to page URL
    action_url = urljoin(page_url, form.action) if form.action else page_url

    vectors = []
    for name, input_type, value in form.inputs:
        # Skip submit buttons and file uploads
        if input_type in ('submit', 'button', 'image', 'file', 'reset'):
            continue

        # Determine location based on form method
        location = 'body' if form.method == 'POST' else 'query'

        vectors.append(InjectionVector(
            location=location,
            name=name,
            original_value=value,
        ))

    return action_url, vectors
```

### Robots.txt Compliance (Optional)
```python
# Source: Python urllib.robotparser documentation
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

def can_crawl(url: str, user_agent: str = 'Ricochet') -> bool:
    """Check if URL is allowed by robots.txt.

    Note: For security testing, this is typically disabled.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.read()
    except Exception:
        # If we can't read robots.txt, assume allowed
        return True

    return parser.can_fetch(user_agent, url)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| BeautifulSoup/lxml | HTMLParser (stdlib-only) | N/A (constraint) | Fewer features but zero dependencies |
| Scrapy framework | Custom BFS crawler | N/A (constraint) | More control, simpler |
| Recursive DFS | BFS with deque | Best practice | Better depth control, avoids stack overflow |
| Load all payloads at once | Streaming iterator option | Memory efficiency | Handles large wordlists |

**Current security scanning best practices (2025):**
- Wapiti 3.2.8 crawls for forms and inputs, fuzzes discovered injection points
- Tools like ffuf use simple line-delimited wordlists for compatibility with SecLists
- Modern scanners use BFS with depth limits to avoid infinite crawling

## Open Questions

Things that couldn't be fully resolved:

1. **JavaScript-Rendered Content**
   - What we know: HTMLParser only sees static HTML, not JS-rendered content
   - What's unclear: How much content is missed on modern SPAs
   - Recommendation: Document limitation; suggest Burp/browser-based crawling for JS-heavy sites

2. **Multipart Form Handling**
   - What we know: Current form extraction doesn't handle file upload forms properly
   - What's unclear: Whether file upload forms are important injection vectors
   - Recommendation: Skip file inputs, document limitation

3. **Cookie-Based Crawling**
   - What we know: Some pages require authentication cookies to access
   - What's unclear: Best way to provide cookies for crawling
   - Recommendation: Add --cookie flag to crawl command, pass to http_client

4. **Crawl-Delay Compliance**
   - What we know: robots.txt may specify Crawl-delay directive
   - What's unclear: Whether to honor it for security testing
   - Recommendation: Use existing rate limiter, ignore robots.txt crawl-delay for pentest

## Sources

### Primary (HIGH confidence)
- [Python html.parser documentation](https://docs.python.org/3/library/html.parser.html) - HTMLParser class, handler methods, subclassing
- [Python urllib.parse documentation](https://docs.python.org/3/library/urllib.parse.html) - urljoin, urlparse, urldefrag, URL handling

### Secondary (MEDIUM confidence)
- [Scrape.do Python Crawler Guide (2025)](https://scrape.do/blog/web-crawler-python/) - BFS patterns, depth limiting, visited tracking
- [Wapiti Scanner](https://wapiti-scanner.github.io/) - Security scanner crawling approach (3.2.8, Oct 2025)
- [Python urllib.robotparser documentation](https://docs.python.org/3/library/urllib.robotparser.html) - robots.txt parsing

### Tertiary (LOW confidence)
- [ZenRows Crawler Tutorial](https://www.zenrows.com/blog/web-crawler-python) - General crawler patterns
- [FreeCodeCamp Security Scanner](https://www.freecodecamp.org/news/build-a-web-application-security-scanner-with-python/) - Form extraction for vulnerability scanning

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib well-documented, all APIs verified
- Architecture: HIGH - BFS crawling is standard, patterns from official docs
- Pitfalls: MEDIUM - Some based on security testing experience rather than docs
- Payload loading: HIGH - Simple file I/O, compatible with established tools

**Research date:** 2026-01-29
**Valid until:** 2026-03-29 (60 days - stdlib is stable)
