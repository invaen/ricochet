"""Output module for ricochet findings."""

from ricochet.output.finding import Finding
from ricochet.output.formatters import output_json, output_text

__all__ = ['Finding', 'output_json', 'output_text']
