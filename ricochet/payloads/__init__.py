"""
Payload generators for vulnerability detection.

Each generator yields (payload, context) tuples where:
- payload: String with {{CALLBACK}} placeholder for correlation
- context: Hint about where payload is effective (html, mssql, jinja2, universal, etc.)

Generators:
- XSSPayloadGenerator: Browser-executed XSS payloads
- SQLiPayloadGenerator: Database-specific OOB SQLi payloads
- SSTIPayloadGenerator: Template engine command execution payloads
- PolyglotPayloadGenerator: Universal detection payloads
"""

from .xss import XSSPayloadGenerator
from .sqli import SQLiPayloadGenerator
from .ssti import SSTIPayloadGenerator
from .polyglot import PolyglotPayloadGenerator

__all__ = [
    "XSSPayloadGenerator",
    "SQLiPayloadGenerator",
    "SSTIPayloadGenerator",
    "PolyglotPayloadGenerator",
]
