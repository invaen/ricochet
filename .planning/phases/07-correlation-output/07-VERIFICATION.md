---
phase: 07-correlation-output
verified: 2026-01-30T07:15:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 7: Correlation & Output Verification Report

**Phase Goal:** Tool correlates callbacks with injections and outputs findings in multiple formats
**Verified:** 2026-01-30T07:15:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | When callback fires, tool identifies the exact injection point that triggered it | VERIFIED | `InjectionStore.get_findings()` uses INNER JOIN on `correlation_id` to link callbacks to injections (store.py:302-319) |
| 2 | User can get findings in JSON format with `-o json` | VERIFIED | CLI `findings -o json` calls `output_json()` which outputs JSONL format (cli.py:502-503, formatters.py:11-59) |
| 3 | User can get human-readable output with `-o text` | VERIFIED | CLI `findings -o text` calls `output_text()` with severity icons (cli.py:504-505, formatters.py:62-107) |
| 4 | User can enable verbose/debug mode to see payloads and responses | VERIFIED | Global `-v` flag controls logging level (cli.py:15-35), verbose param enables full payload/callback details in formatters (formatters.py:45-57, 98-105) |
| 5 | User can route traffic through HTTP proxy with `--proxy` | VERIFIED | CLI `inject --proxy URL` wires to `Injector(proxy_url=args.proxy)` which passes to `send_request(proxy_url=...)` using `ProxyHandler` (cli.py:214-218, 775, injector.py:87, 169, http_client.py:98-106) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ricochet/output/finding.py` | Finding dataclass with severity property | VERIFIED | 46 lines, `@dataclass Finding` with `@property severity` deriving from context (lines 7-45) |
| `ricochet/output/__init__.py` | Exports Finding, output_json, output_text | VERIFIED | 6 lines, exports all three via `__all__` |
| `ricochet/output/formatters.py` | output_json() and output_text() functions | VERIFIED | 107 lines, both functions implemented with verbose support |
| `ricochet/core/store.py` | get_findings() correlation query | VERIFIED | 353 lines, `get_findings()` at lines 285-352 with INNER JOIN correlation |
| `ricochet/cli.py` | findings subcommand with -o, --since, --min-severity; inject --proxy | VERIFIED | 918 lines, findings parser (264-287), cmd_findings (475-507), --proxy (214-218) |
| `ricochet/injection/http_client.py` | ProxyHandler support in send_request | VERIFIED | 180 lines, proxy_url param (60), ProxyHandler (97-106) |
| `ricochet/injection/injector.py` | Injector accepts proxy_url | VERIFIED | 395 lines, proxy_url in __init__ (87), passed to send_request (169) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ricochet/core/store.py` | `ricochet/output/finding.py` | `from ricochet.output.finding import Finding` | WIRED | Line 10, returns `list[Finding]` from get_findings() |
| `ricochet/cli.py` | `ricochet/output/formatters.py` | `output_json(findings, ...)` / `output_text(findings, ...)` | WIRED | Lines 485, 502-505, calls formatters with findings from store |
| `ricochet/output/formatters.py` | `ricochet/output/finding.py` | `list[Finding]` parameter type | WIRED | Lines 8, 12, 63, imports and accepts Finding objects |
| `ricochet/cli.py` | `ricochet/injection/injector.py` | `proxy_url=args.proxy` | WIRED | Line 775, passes proxy URL to Injector |
| `ricochet/injection/injector.py` | `ricochet/injection/http_client.py` | `proxy_url=self.proxy_url` | WIRED | Line 169, passes proxy to send_request() |
| `ricochet/cli.py` | `ricochet/injection/http_client.py` | `proxy_url=args.proxy` (from-crawl mode) | WIRED | Line 660, direct call with proxy |

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| OUT-01: Match callbacks to injections | SATISFIED | get_findings() INNER JOIN |
| OUT-02: JSON output format | SATISFIED | output_json() JSONL |
| OUT-03: Text output format | SATISFIED | output_text() with icons |
| OUT-04: Verbose/debug mode | SATISFIED | -v flag + verbose param |
| OUT-05: HTTP proxy support | SATISFIED | --proxy flag wired through |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | - | - | - | - |

All "placeholder" matches in CLI and injector are documentation/help text, not stub implementations.

### Human Verification Required

#### 1. End-to-End Correlation Test

**Test:** Inject a payload, simulate callback, verify finding correlates correctly
**Expected:** Finding shows correct injection target, parameter, and callback details
**Why human:** Requires running callback server and simulating full flow

#### 2. Proxy Traffic Inspection

**Test:** Run `ricochet inject -u http://target --proxy http://127.0.0.1:8080` with Burp/ZAP running
**Expected:** All injection traffic appears in proxy history
**Why human:** Requires external proxy tool setup

#### 3. Visual Output Verification

**Test:** Run `ricochet findings -o text` with actual findings
**Expected:** Output is human-readable with severity icons ([!], [+], etc.)
**Why human:** Visual inspection of formatting quality

### Verification Details

**Automated Tests Executed:**

```
1. Finding severity derivation:
   - context='ssti:jinja2' -> severity=high   PASS
   - context='sqli:mssql' -> severity=high    PASS
   - context='xss:html' -> severity=medium    PASS
   - context='other' -> severity=info         PASS
   - context=None -> severity=info            PASS

2. Module imports:
   - from ricochet.output import Finding, output_json, output_text   OK
   - from ricochet.core.store import InjectionStore; s.get_findings()  OK

3. CLI commands:
   - ricochet findings --help                 Shows -o, --since, --min-severity
   - ricochet inject --help | grep proxy      Shows --proxy URL
   - ricochet findings -o text                "No findings." (empty DB)
   - ricochet findings -o json                (empty output, no findings)

4. Parameter introspection:
   - proxy_url in send_request signature      True
   - proxy_url in Injector.__init__ signature True
```

---

*Verified: 2026-01-30T07:15:00Z*
*Verifier: Claude (gsd-verifier)*
