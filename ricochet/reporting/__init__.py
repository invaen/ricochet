"""Bug bounty report generation module."""

from ricochet.reporting.generator import ReportGenerator, generate_report
from ricochet.reporting.templates import (
    GENERIC_TEMPLATE,
    SQLI_TEMPLATE,
    SSTI_TEMPLATE,
    XSS_TEMPLATE,
)

__all__ = [
    'ReportGenerator',
    'generate_report',
    'XSS_TEMPLATE',
    'SQLI_TEMPLATE',
    'SSTI_TEMPLATE',
    'GENERIC_TEMPLATE',
]
