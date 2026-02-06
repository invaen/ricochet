"""
SSTI payload generator with template engine selection.

Generates server-side template injection payloads that execute system commands
to trigger callbacks. These payloads detect SSTI by having the server run
curl/wget/nslookup to phone home when template code is executed.
"""

from pathlib import Path
from typing import Iterator, Optional

from ricochet.injection.payloads import load_payloads


class SSTIPayloadGenerator:
    """Generator for SSTI callback payloads.

    Loads SSTI payloads from engine-specific builtin files and yields them
    with engine metadata. Payloads contain {{CALLBACK}} placeholder which
    is substituted by the Injector class during injection.

    Supports targeting specific template engines or generating payloads for
    all supported engines.

    Attributes:
        vuln_type: The vulnerability type this generator targets ("ssti")
        ENGINES: List of supported template engines

    Example:
        >>> # All engines
        >>> gen = SSTIPayloadGenerator()
        >>> for payload, engine in gen.generate("http://callback.example.com"):
        ...     print(f"{engine}: {payload[:50]}...")

        >>> # Specific engine
        >>> gen = SSTIPayloadGenerator(engine="jinja2")
        >>> payloads = list(gen.generate("http://callback.example.com"))
        >>> assert all(p[1] == "jinja2" for p in payloads)
    """

    vuln_type = "ssti"
    ENGINES = ["jinja2", "freemarker", "twig", "erb", "velocity", "mako"]

    def __init__(self, engine: Optional[str] = None):
        """Initialize SSTI payload generator.

        Args:
            engine: Specific template engine to target (jinja2, freemarker, twig,
                   erb, velocity, mako). If None, generates payloads for all
                   supported engines.

        Raises:
            ValueError: If specified engine is not supported.
        """
        if engine is not None and engine not in self.ENGINES:
            raise ValueError(
                f"Unknown engine '{engine}'. Supported: {', '.join(self.ENGINES)}"
            )
        self.engine = engine

    def generate(self, callback_url: str) -> Iterator[tuple[str, str]]:
        """Generate SSTI payloads with callback placeholder.

        Args:
            callback_url: Base callback URL (not used directly, placeholder
                         substitution happens in Injector)

        Yields:
            Tuples of (payload, engine) where:
            - payload: SSTI payload string with {{CALLBACK}} placeholder
            - engine: Template engine name (jinja2, freemarker, twig)
        """
        builtin_dir = Path(__file__).parent / "builtin"

        engines = [self.engine] if self.engine else self.ENGINES

        for eng in engines:
            filepath = builtin_dir / f"ssti-{eng}.txt"
            if filepath.exists():
                for payload in load_payloads(filepath):
                    yield (payload, eng)
