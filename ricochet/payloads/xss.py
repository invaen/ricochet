"""
XSS payload generator with browser-based callback embedding.

Generates XSS payloads that trigger HTTP callbacks when executed in browser
context. These payloads detect stored/reflected XSS by phoning home rather
than relying on visible indicators like alert().
"""

from pathlib import Path
from typing import Iterator

from ricochet.injection.payloads import load_payloads


class XSSPayloadGenerator:
    """Generator for XSS callback payloads.

    Loads XSS payloads from builtin file and yields them with context hints.
    Payloads contain {{CALLBACK}} placeholder which is substituted by the
    Injector class during injection.

    Attributes:
        vuln_type: The vulnerability type this generator targets ("xss")

    Example:
        >>> gen = XSSPayloadGenerator()
        >>> for payload, context in gen.generate("http://callback.example.com"):
        ...     print(f"Payload: {payload[:50]}...")
    """

    vuln_type = "xss"

    def generate(self, callback_url: str) -> Iterator[tuple[str, str]]:
        """Generate XSS payloads with callback placeholder.

        Args:
            callback_url: Base callback URL (not used directly, placeholder
                         substitution happens in Injector)

        Yields:
            Tuples of (payload, context) where:
            - payload: XSS payload string with {{CALLBACK}} placeholder
            - context: Context hint (e.g., "html") for payload formatting
        """
        builtin_path = Path(__file__).parent / "builtin" / "xss-callback.txt"
        for payload in load_payloads(builtin_path):
            yield (payload, "html")
