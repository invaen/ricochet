"""Bug bounty report templates for different vulnerability types."""

XSS_TEMPLATE = '''## Summary
{vuln_type} vulnerability in `{parameter}` parameter at `{target_url}`

## Severity
{severity_upper} - {severity_reasoning}

## Description
A {vuln_subtype} XSS vulnerability exists in the `{parameter}` parameter of the `{endpoint}` endpoint. When a malicious payload is submitted, it is {storage_behavior} and later executed in the context of {execution_context}.

## Steps to Reproduce
1. Navigate to: `{injection_url}`
2. Enter the following payload in the `{parameter}` field:
   ```
   {payload}
   ```
3. Submit the form/request
4. {trigger_step}
5. Observe callback received at: `{callback_url}`

## Proof of Concept
- **Correlation ID:** `{correlation_id}`
- **Injection Point:** `{target_url}` (parameter: `{parameter}`)
- **Payload Used:** `{payload}`
- **Callback Received:** {callback_timestamp}
- **Delay:** {delay_seconds:.1f} seconds

{metadata_section}

## Impact
An attacker can:
- Execute arbitrary JavaScript in victims' browsers
- Steal session cookies and hijack user accounts (if not HttpOnly)
- Perform actions on behalf of authenticated users
- Access sensitive data displayed on the page
{custom_impact}

## Remediation
- Implement proper output encoding (HTML entity encoding for HTML context)
- Use Content-Security-Policy headers to restrict inline script execution
- Set HttpOnly flag on sensitive cookies
- Implement input validation on the server side

## References
- OWASP XSS Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- CWE-79: Improper Neutralization of Input During Web Page Generation
'''

SQLI_TEMPLATE = '''## Summary
Out-of-band SQL Injection vulnerability in `{parameter}` parameter at `{target_url}`

## Severity
{severity_upper} - {severity_reasoning}

## Description
An out-of-band SQL Injection vulnerability exists in the `{parameter}` parameter of the `{endpoint}` endpoint. The application is vulnerable to SQL injection, allowing an attacker to exfiltrate data or execute arbitrary SQL commands through out-of-band channels.

## Steps to Reproduce
1. Navigate to: `{injection_url}`
2. Enter the following payload in the `{parameter}` field:
   ```
   {payload}
   ```
3. Submit the form/request
4. {trigger_step}
5. Observe DNS/HTTP callback received at: `{callback_url}`

## Proof of Concept
- **Correlation ID:** `{correlation_id}`
- **Injection Point:** `{target_url}` (parameter: `{parameter}`)
- **Payload Used:** `{payload}`
- **Callback Received:** {callback_timestamp}
- **Delay:** {delay_seconds:.1f} seconds

{metadata_section}

## Impact
An attacker can:
- Extract sensitive data from the database
- Access or modify database contents
- Execute arbitrary SQL commands
- Potentially compromise the entire database server
- Escalate to remote code execution depending on database configuration
{custom_impact}

## Remediation
- Use parameterized queries (prepared statements) for all database operations
- Implement input validation and sanitization
- Apply principle of least privilege for database accounts
- Disable dangerous database features (e.g., xp_cmdshell, LOAD_FILE)
- Use Web Application Firewall (WAF) to detect and block SQL injection attempts

## References
- OWASP SQL Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- CWE-89: Improper Neutralization of Special Elements used in an SQL Command
'''

SSTI_TEMPLATE = '''## Summary
Server-Side Template Injection (SSTI) vulnerability in `{parameter}` parameter at `{target_url}`

## Severity
{severity_upper} - {severity_reasoning}

## Description
A Server-Side Template Injection vulnerability exists in the `{parameter}` parameter of the `{endpoint}` endpoint. User-controlled input is passed unsafely to a template engine, allowing an attacker to inject template directives and execute arbitrary code on the server.

## Steps to Reproduce
1. Navigate to: `{injection_url}`
2. Enter the following payload in the `{parameter}` field:
   ```
   {payload}
   ```
3. Submit the form/request
4. {trigger_step}
5. Observe callback received at: `{callback_url}`

## Proof of Concept
- **Correlation ID:** `{correlation_id}`
- **Injection Point:** `{target_url}` (parameter: `{parameter}`)
- **Payload Used:** `{payload}`
- **Callback Received:** {callback_timestamp}
- **Delay:** {delay_seconds:.1f} seconds

{metadata_section}

## Impact
An attacker can:
- Execute arbitrary code on the server (Remote Code Execution)
- Read sensitive files from the server filesystem
- Access environment variables and configuration data
- Completely compromise the application server
- Pivot to internal network resources
{custom_impact}

## Remediation
- Never pass user input directly to template engines
- Use sandboxed template environments with restricted functionality
- Implement strict input validation and whitelist allowed characters
- Use logic-less template engines when possible (e.g., Mustache)
- Apply Content Security Policy (CSP) as defense-in-depth

## References
- PortSwigger SSTI: https://portswigger.net/web-security/server-side-template-injection
- HackTricks SSTI: https://book.hacktricks.xyz/pentesting-web/ssti-server-side-template-injection
- CWE-94: Improper Control of Generation of Code
'''

GENERIC_TEMPLATE = '''## Summary
{vuln_type} vulnerability in `{parameter}` parameter at `{target_url}`

## Severity
{severity_upper} - {severity_reasoning}

## Description
A callback was successfully triggered from the `{parameter}` parameter at `{target_url}`. This indicates the application may be vulnerable to second-order execution or out-of-band data exfiltration.

## Steps to Reproduce
1. Navigate to: `{injection_url}`
2. Enter the following payload in the `{parameter}` field:
   ```
   {payload}
   ```
3. Submit the form/request
4. {trigger_step}
5. Observe callback received at: `{callback_url}`

## Proof of Concept
- **Correlation ID:** `{correlation_id}`
- **Injection Point:** `{target_url}` (parameter: `{parameter}`)
- **Payload Used:** `{payload}`
- **Callback Received:** {callback_timestamp}
- **Delay:** {delay_seconds:.1f} seconds

{metadata_section}

## Impact
The impact depends on the specific vulnerability type and execution context. Potential impacts include:
- Unauthorized data access or exfiltration
- Code execution in user or administrative contexts
- Server-side code execution
{custom_impact}

## Remediation
- Perform thorough input validation and output encoding
- Implement proper content security policies
- Use parameterized queries for database operations
- Sanitize user input before rendering in templates or web pages
- Apply principle of least privilege

## References
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CWE Common Weakness Enumeration: https://cwe.mitre.org/
'''
