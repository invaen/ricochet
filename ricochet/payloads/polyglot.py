"""
Polyglot payload generator for universal vulnerability detection.

Generates payloads that work across multiple vulnerability contexts without
modification. Useful for initial detection phase when the exact vulnerability
type is unknown.

Key polyglots:
    - SSTI: Works on 51/51 template engines (Hackmanit research)
    - XSS: Works across HTML contexts (body, attribute, script)
    - SQLi: Time-based detection across multiple databases
"""

from pathlib import Path
from typing import Iterator

from ricochet.injection.payloads import load_payloads


class PolyglotPayloadGenerator:
    """Generator for universal polyglot detection payloads.

    Polyglots reduce testing effort by working in multiple contexts
    without modification. The trade-off is they're optimized for breadth
    over depth - use specific generators for thorough testing.

    Attributes:
        vuln_type: The vulnerability type identifier ("polyglot")

    Example:
        >>> gen = PolyglotPayloadGenerator()
        >>> for payload, context in gen.generate("http://callback.example.com"):
        ...     print(f"[{context}] {payload[:50]}...")
    """

    vuln_type = "polyglot"

    def generate(self, callback_url: str) -> Iterator[tuple[str, str]]:
        """Generate polyglot payloads with callback placeholder.

        Args:
            callback_url: Base callback URL (not used directly, placeholder
                         substitution happens in Injector)

        Yields:
            Tuples of (payload, context) where:
            - payload: Polyglot payload string with {{CALLBACK}} placeholder
            - context: Always "universal" for polyglots since they work
                      across multiple vulnerability contexts
        """
        builtin_dir = Path(__file__).parent / "builtin"
        filepath = builtin_dir / "polyglot-detection.txt"

        if filepath.exists():
            for payload in load_payloads(filepath):
                yield (payload, "universal")
