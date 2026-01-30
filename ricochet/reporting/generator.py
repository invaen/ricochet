"""Report generator for bug bounty submissions."""

from datetime import datetime
from urllib.parse import urlparse

from ricochet.output.finding import Finding
from ricochet.reporting.templates import (
    GENERIC_TEMPLATE,
    SQLI_TEMPLATE,
    SSTI_TEMPLATE,
    XSS_TEMPLATE,
)


class ReportGenerator:
    """Generate bug bounty reports from findings."""

    def __init__(self, finding: Finding):
        """Initialize report generator with a finding.

        Args:
            finding: Finding object containing correlated injection and callback data.
        """
        self.finding = finding

    def _select_template(self) -> str:
        """Select appropriate template based on vulnerability context.

        Returns:
            Template string for the vulnerability type.
        """
        if self.finding.context is None:
            return GENERIC_TEMPLATE

        ctx_lower = self.finding.context.lower()
        if 'xss' in ctx_lower:
            return XSS_TEMPLATE
        elif 'sqli' in ctx_lower or 'sql' in ctx_lower:
            return SQLI_TEMPLATE
        elif 'ssti' in ctx_lower:
            return SSTI_TEMPLATE
        else:
            return GENERIC_TEMPLATE

    def _build_metadata_section(self) -> str:
        """Build metadata section from captured callback data.

        Returns:
            Formatted metadata section string, or empty if no metadata.
        """
        metadata = self.finding.metadata
        if not metadata:
            return "\n**Note:** No metadata was captured. Consider using exfiltration payloads for richer evidence (URL, cookies, DOM)."

        lines = ["\n## Captured Metadata"]

        # URL where XSS executed
        if 'url' in metadata:
            lines.append(f"- **Execution URL:** `{metadata['url']}`")

        # Cookies
        if 'cookies' in metadata:
            cookies = metadata['cookies']
            if cookies:
                lines.append(f"- **Cookies:** `{cookies[:200]}`")
                if not cookies:
                    lines.append("  - No cookies captured (may indicate HttpOnly flag is set)")
            else:
                lines.append("- **Cookies:** None (HttpOnly flag likely set)")

        # User-Agent
        if 'ua' in metadata:
            lines.append(f"- **User-Agent:** `{metadata['ua']}`")

        # DOM snippet
        if 'dom' in metadata:
            dom = metadata['dom']
            # Truncate for readability
            if len(dom) > 500:
                dom = dom[:500] + "..."
            lines.append(f"- **DOM Snippet:**")
            lines.append(f"  ```html")
            lines.append(f"  {dom}")
            lines.append(f"  ```")

        return "\n".join(lines)

    def _derive_severity_reasoning(self) -> str:
        """Derive severity reasoning based on context and metadata.

        Returns:
            Human-readable severity reasoning string.
        """
        ctx = self.finding.context or ''
        delay = self.finding.delay_seconds
        metadata = self.finding.metadata

        reasons = []

        # Stored vs reflected
        if delay > 60:
            reasons.append("stored vulnerability (delay > 1 minute)")
        else:
            reasons.append("reflected or short-delay execution")

        # Admin context
        if metadata and 'url' in metadata:
            url = metadata['url'].lower()
            if '/admin' in url or '/dashboard' in url or '/panel' in url:
                reasons.append("execution in admin context")
        elif delay > 3600:
            reasons.append("long delay suggests admin/moderation queue")

        # Cookie capture
        if metadata and 'cookies' in metadata and metadata['cookies']:
            reasons.append("successfully captured session cookies")

        # Base severity from context
        if 'ssti' in ctx.lower():
            return "Critical RCE vulnerability; " + ", ".join(reasons)
        elif 'sqli' in ctx.lower() or 'sql' in ctx.lower():
            return "High severity database access; " + ", ".join(reasons)
        elif 'xss' in ctx.lower():
            if reasons:
                return "XSS confirmed; " + ", ".join(reasons)
            return "XSS confirmed with callback"
        else:
            return "Callback confirmed; " + ", ".join(reasons) if reasons else "Callback confirmed"

    def _infer_execution_context(self) -> str:
        """Infer where the payload executed based on metadata and timing.

        Returns:
            Human-readable execution context string.
        """
        metadata = self.finding.metadata
        delay = self.finding.delay_seconds

        # Check metadata URL first
        if metadata and 'url' in metadata:
            url = metadata['url'].lower()
            if '/admin' in url:
                return "admin panel"
            elif '/dashboard' in url or '/panel' in url:
                return "administrative dashboard"
            elif '/moderate' in url or '/review' in url:
                return "moderation queue"
            else:
                # Extract rough context from path
                return f"application context ({metadata['url']})"

        # Infer from delay
        if delay > 3600:  # > 1 hour
            return "likely admin/moderation queue (long delay)"
        elif delay > 300:  # > 5 minutes
            return "background processing or review queue"
        else:
            return "unknown context (possibly user-triggered or background job)"

    def generate(self) -> str:
        """Generate complete bug bounty report.

        Returns:
            Markdown-formatted report string ready for submission.
        """
        template = self._select_template()

        # Extract URL components
        parsed = urlparse(self.finding.target_url)
        endpoint = parsed.path or '/'

        # Determine vulnerability type and subtype
        ctx = self.finding.context or 'unknown'
        if 'xss' in ctx.lower():
            vuln_type = "Cross-Site Scripting (XSS)"
            if 'html' in ctx.lower():
                vuln_subtype = "HTML context"
            elif 'attr' in ctx.lower():
                vuln_subtype = "attribute context"
            elif 'js' in ctx.lower():
                vuln_subtype = "JavaScript context"
            else:
                vuln_subtype = "stored"
        elif 'sqli' in ctx.lower() or 'sql' in ctx.lower():
            vuln_type = "SQL Injection"
            vuln_subtype = "out-of-band"
        elif 'ssti' in ctx.lower():
            vuln_type = "Server-Side Template Injection (SSTI)"
            vuln_subtype = "template engine"
        else:
            vuln_type = "Second-Order Vulnerability"
            vuln_subtype = "unknown type"

        # Storage behavior for XSS
        if self.finding.delay_seconds > 60:
            storage_behavior = "stored in the database"
        else:
            storage_behavior = "reflected or processed asynchronously"

        # Trigger step description
        if self.finding.delay_seconds > 3600:
            trigger_step = "Wait for admin/moderator to review (delay observed: {:.0f} seconds / {:.1f} hours)".format(
                self.finding.delay_seconds, self.finding.delay_seconds / 3600
            )
        elif self.finding.delay_seconds > 60:
            trigger_step = "Wait for background processing (delay observed: {:.0f} seconds)".format(
                self.finding.delay_seconds
            )
        else:
            trigger_step = "Payload executes immediately or shortly after submission"

        # Format callback timestamp
        callback_timestamp = datetime.fromtimestamp(self.finding.received_at).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Custom impact based on captured metadata
        custom_impact = []
        if self.finding.metadata:
            if self.finding.metadata.get('cookies'):
                custom_impact.append("- Session cookies were successfully captured")
            if '/admin' in str(self.finding.metadata.get('url', '')):
                custom_impact.append("- Payload executed in administrative context")

        custom_impact_str = "\n" + "\n".join(custom_impact) if custom_impact else ""

        # Fill template
        report = template.format(
            vuln_type=vuln_type,
            parameter=self.finding.parameter,
            target_url=self.finding.target_url,
            severity_upper=self.finding.severity.upper(),
            severity_reasoning=self._derive_severity_reasoning(),
            vuln_subtype=vuln_subtype,
            endpoint=endpoint,
            storage_behavior=storage_behavior,
            execution_context=self._infer_execution_context(),
            injection_url=self.finding.target_url,
            payload=self.finding.payload,
            trigger_step=trigger_step,
            callback_url=self.finding.request_path,
            correlation_id=self.finding.correlation_id,
            callback_timestamp=callback_timestamp,
            delay_seconds=self.finding.delay_seconds,
            metadata_section=self._build_metadata_section(),
            custom_impact=custom_impact_str,
        )

        return report


def generate_report(finding: Finding) -> str:
    """Generate bug bounty report from a finding.

    Convenience function wrapping ReportGenerator.

    Args:
        finding: Finding object containing correlated injection and callback data.

    Returns:
        Markdown-formatted report string ready for submission.
    """
    generator = ReportGenerator(finding)
    return generator.generate()
