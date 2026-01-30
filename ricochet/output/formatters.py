"""Output formatters for findings (JSON, text)."""

import json
import sys
from datetime import datetime, timezone
from typing import TextIO

from ricochet.output.finding import Finding


def output_json(
    findings: list[Finding],
    file: TextIO = sys.stdout,
    verbose: bool = False
) -> None:
    """Output findings in JSONL format (one JSON object per line).

    Args:
        findings: List of Finding objects to output
        file: Output stream (default: stdout)
        verbose: Include full payload and callback body
    """
    for finding in findings:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "ricochet",
            "finding": {
                "correlation_id": finding.correlation_id,
                "severity": finding.severity,
                "injection": {
                    "target_url": finding.target_url,
                    "parameter": finding.parameter,
                    "injected_at": finding.injected_at,
                    "context": finding.context,
                },
                "callback": {
                    "source_ip": finding.source_ip,
                    "request_path": finding.request_path,
                    "received_at": finding.received_at,
                    "delay_seconds": round(finding.delay_seconds, 2),
                },
            }
        }

        if verbose:
            record["finding"]["injection"]["payload"] = finding.payload
            record["finding"]["callback"]["headers"] = finding.callback_headers
            if finding.callback_body:
                # Attempt to decode, fall back to base64
                try:
                    record["finding"]["callback"]["body"] = finding.callback_body.decode('utf-8')
                except (UnicodeDecodeError, AttributeError):
                    import base64
                    record["finding"]["callback"]["body_base64"] = base64.b64encode(
                        finding.callback_body if isinstance(finding.callback_body, bytes)
                        else finding.callback_body.encode()
                    ).decode('ascii')

        print(json.dumps(record), file=file)


def output_text(
    findings: list[Finding],
    file: TextIO = sys.stdout,
    verbose: bool = False
) -> None:
    """Output findings in human-readable text format.

    Args:
        findings: List of Finding objects to output
        file: Output stream (default: stdout)
        verbose: Include full payload and callback details
    """
    if not findings:
        print("No findings.", file=file)
        return

    print(f"=== Ricochet Findings ({len(findings)}) ===", file=file)
    print(file=file)

    severity_icons = {
        'high': '[!]',
        'medium': '[+]',
        'low': '[*]',
        'info': '[-]',
    }

    for i, f in enumerate(findings, 1):
        icon = severity_icons.get(f.severity, '[-]')

        print(f"{icon} Finding #{i}", file=file)
        print(f"    Correlation ID: {f.correlation_id}", file=file)
        print(f"    Target: {f.target_url}", file=file)
        print(f"    Parameter: {f.parameter}", file=file)
        print(f"    Severity: {f.severity.upper()}", file=file)
        print(f"    Delay: {f.delay_seconds:.2f}s", file=file)

        if verbose:
            print(file=file)
            print(f"    Payload: {f.payload}", file=file)
            print(f"    Context: {f.context}", file=file)
            print(f"    Callback from: {f.source_ip}", file=file)
            print(f"    Callback path: {f.request_path}", file=file)
            if f.callback_headers:
                print(f"    Callback headers: {f.callback_headers}", file=file)

        print(file=file)
