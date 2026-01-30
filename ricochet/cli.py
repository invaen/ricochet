"""CLI entry point and argument parser for Ricochet."""

import argparse
import secrets
import sys
import time
from pathlib import Path
from typing import Optional

from ricochet import __version__
from ricochet.core.store import InjectionRecord, InjectionStore, get_db_path


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser with subcommand structure.
    """
    parser = argparse.ArgumentParser(
        prog='ricochet',
        description='Second-order vulnerability detection tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (-v for info, -vv for debug)'
    )
    parser.add_argument(
        '--db',
        type=Path,
        default=None,
        help='Database path (default: ~/.ricochet/ricochet.db)'
    )

    # Set up subparsers for future commands
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        metavar='<command>'
    )

    # Listen command - callback server
    listen_parser = subparsers.add_parser(
        'listen',
        help='Start callback server to receive OOB interactions'
    )
    listen_parser.add_argument(
        '--http',
        action='store_true',
        help='Start HTTP callback server'
    )
    listen_parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    listen_parser.add_argument(
        '-p', '--port',
        type=int,
        default=8080,
        help='Port to listen on (default: 8080)'
    )
    listen_parser.add_argument(
        '--dns',
        action='store_true',
        help='Start DNS callback server'
    )
    listen_parser.add_argument(
        '--dns-port',
        type=int,
        default=5353,
        help='DNS port (default: 5353)'
    )
    listen_parser.set_defaults(func=cmd_listen)

    # Interactsh command - external callback infrastructure
    interactsh_parser = subparsers.add_parser(
        'interactsh',
        help='Generate Interactsh callback URLs and poll for interactions'
    )
    interactsh_parser.add_argument(
        'action',
        choices=['url', 'poll'],
        help='Action: url (generate callback URLs), poll (check for interactions)'
    )
    interactsh_parser.add_argument(
        '--server',
        default='oast.pro',
        help='Interactsh server hostname (default: oast.pro)'
    )
    interactsh_parser.add_argument(
        '--correlation-id',
        help='Specific correlation ID (generates new if not provided)'
    )
    interactsh_parser.add_argument(
        '--secret',
        help='Secret for authenticated polling'
    )
    interactsh_parser.set_defaults(func=cmd_interactsh)

    # Inject command - payload injection
    inject_parser = subparsers.add_parser(
        'inject',
        help='Inject payloads into target'
    )

    # Target specification (mutually exclusive group)
    target_group = inject_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        '-u', '--url',
        help='Target URL'
    )
    target_group.add_argument(
        '-r', '--request',
        type=Path,
        help='Burp-format request file'
    )
    target_group.add_argument(
        '--from-crawl',
        type=Path,
        metavar='FILE',
        help='Use vectors from crawl export JSON file'
    )

    # Parameter specification (optional with -u, ignored with -r)
    inject_parser.add_argument(
        '-p', '--param',
        help='Specific parameter to inject (with -u)'
    )

    # Payload
    inject_parser.add_argument(
        '--payload',
        default='{{CALLBACK}}',
        help='Payload template with {{CALLBACK}} placeholder (default: {{CALLBACK}})'
    )
    inject_parser.add_argument(
        '--payloads',
        type=Path,
        help='File containing payloads (one per line, # for comments)'
    )

    # Callback configuration
    inject_parser.add_argument(
        '--callback-url',
        default='http://localhost:8080',
        help='Callback URL base (default: http://localhost:8080)'
    )

    # Rate limiting
    inject_parser.add_argument(
        '--rate',
        type=float,
        default=10.0,
        help='Requests per second (default: 10)'
    )

    # Timeout
    inject_parser.add_argument(
        '--timeout',
        type=float,
        default=10.0,
        help='Request timeout in seconds (default: 10)'
    )

    # HTTPS
    inject_parser.add_argument(
        '--https',
        action='store_true',
        help='Use HTTPS for URL construction'
    )

    # Dry-run
    inject_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be injected without sending requests'
    )

    # Proxy
    inject_parser.add_argument(
        '--proxy',
        metavar='URL',
        help='HTTP proxy URL (e.g., http://127.0.0.1:8080)'
    )

    inject_parser.set_defaults(func=cmd_inject)

    # Crawl command - web crawler for injection point discovery
    crawl_parser = subparsers.add_parser(
        'crawl',
        help='Crawl website to discover injection points'
    )
    crawl_parser.add_argument(
        '-u', '--url',
        required=True,
        help='Seed URL to start crawling from'
    )
    crawl_parser.add_argument(
        '--depth',
        type=int,
        default=2,
        help='Maximum crawl depth (default: 2)'
    )
    crawl_parser.add_argument(
        '--max-pages',
        type=int,
        default=100,
        help='Maximum pages to crawl (default: 100)'
    )
    crawl_parser.add_argument(
        '--timeout',
        type=float,
        default=10.0,
        help='Request timeout in seconds (default: 10)'
    )
    crawl_parser.add_argument(
        '--rate',
        type=float,
        default=10.0,
        help='Requests per second (default: 10)'
    )
    crawl_parser.add_argument(
        '--export',
        type=Path,
        metavar='FILE',
        help='Export discovered vectors to JSON file'
    )
    crawl_parser.set_defaults(func=cmd_crawl)

    # Findings command - show correlated findings
    findings_parser = subparsers.add_parser(
        'findings',
        help='Show correlated findings (injections that received callbacks)'
    )
    findings_parser.add_argument(
        '-o', '--output',
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)'
    )
    findings_parser.add_argument(
        '--since',
        metavar='HOURS',
        type=float,
        help='Only show findings from last N hours'
    )
    findings_parser.add_argument(
        '--min-severity',
        choices=['info', 'low', 'medium', 'high'],
        default='info',
        help='Minimum severity to show (default: info)'
    )
    findings_parser.set_defaults(func=cmd_findings)

    return parser


def cmd_listen(args, store) -> int:
    """Handle listen subcommand - start callback server.

    Args:
        args: Parsed command line arguments.
        store: InjectionStore instance.

    Returns:
        Exit code (0 for success, 2 for argument errors).
    """
    if args.http:
        from ricochet.server.http import run_callback_server
        return run_callback_server(args.host, args.port, store)
    elif args.dns:
        from ricochet.server.dns import run_dns_server
        return run_dns_server(args.host, args.dns_port, store)
    else:
        print("Error: specify --http or --dns to start callback server", file=sys.stderr)
        print("  Example: ricochet listen --http", file=sys.stderr)
        print("  Example: ricochet listen --dns", file=sys.stderr)
        return 2


def cmd_interactsh(args, store) -> int:
    """Handle interactsh subcommand - generate URLs and poll for interactions.

    Args:
        args: Parsed command line arguments.
        store: InjectionStore instance.

    Returns:
        Exit code (0 for success, 2 for argument errors).
    """
    from ricochet.external.interactsh import InteractshClient

    correlation_id = args.correlation_id
    if correlation_id is None:
        correlation_id = secrets.token_hex(8)  # 16-char hex

    client = InteractshClient(
        server=args.server,
        correlation_id=correlation_id,
        secret=args.secret
    )

    if args.action == 'url':
        # Generate and display callback URLs
        http_url = client.generate_url('http')
        dns_subdomain = client.generate_url('dns')

        print(f"Correlation ID: {correlation_id}")
        print(f"HTTP callback: {http_url}")
        print(f"DNS callback: {dns_subdomain}")
        print()
        print("Note: Use these URLs in your payloads. Monitor for callbacks with:")
        print(f"  ricochet interactsh poll --correlation-id {correlation_id}")
        print()
        print("For public servers, use external tooling (interactsh-client) for polling.")

        # Create placeholder injection record for tracking
        if store.get_injection(correlation_id) is None:
            record = InjectionRecord(
                id=correlation_id,
                target_url=f"interactsh://{args.server}",
                parameter="external",
                payload=f"http://{client.subdomain}/callback",
                timestamp=time.time(),
                context="Interactsh external callback"
            )
            store.record_injection(record)

        return 0

    elif args.action == 'poll':
        if args.correlation_id is None:
            print("Error: --correlation-id required for poll action", file=sys.stderr)
            return 2

        print(f"Polling {args.server} for interactions...")
        print("Note: This only works with self-hosted servers (encryption disabled).")
        print("Public servers require the official interactsh-client for polling.")
        print()

        interactions = client.poll(store)

        if not interactions:
            print("No interactions found (or server requires encryption).")
        else:
            print(f"Found {len(interactions)} interaction(s):")
            for i, interaction in enumerate(interactions, 1):
                print(f"\n{i}. [{interaction.protocol.upper()}] from {interaction.remote_address}")
                print(f"   Timestamp: {interaction.timestamp}")
                if interaction.raw_request:
                    preview = interaction.raw_request[:100]
                    if len(interaction.raw_request) > 100:
                        preview += "..."
                    print(f"   Request: {preview}")

        return 0

    return 0


def cmd_crawl(args, store) -> int:
    """Handle crawl subcommand - crawl website to discover injection points.

    Args:
        args: Parsed command line arguments.
        store: InjectionStore instance (not used directly but passed for consistency).

    Returns:
        Exit code (0 for success, 1 for errors, 2 for argument errors).
    """
    from ricochet.injection.crawler import (
        Crawler,
        export_vectors,
        results_to_vectors,
    )

    print(f"Crawling {args.url}")
    print(f"  Max depth: {args.depth}")
    print(f"  Max pages: {args.max_pages}")
    print(f"  Rate: {args.rate} req/s")
    print()

    crawler = Crawler(
        max_depth=args.depth,
        max_pages=args.max_pages,
        timeout=args.timeout,
        rate_limit=args.rate,
    )

    results = crawler.crawl(args.url)

    # Display crawl results
    pages_crawled = 0
    pages_errored = 0
    total_forms = 0
    total_links = 0

    for result in results:
        if result.error:
            pages_errored += 1
            print(f"[-] {result.url}")
            print(f"    Error: {result.error}")
        else:
            pages_crawled += 1
            total_forms += len(result.forms)
            total_links += len(result.links)
            print(f"[+] {result.url}")
            print(f"    Forms: {len(result.forms)}, Links: {len(result.links)}")
        print()

    # Convert to vectors
    vectors = results_to_vectors(results)

    # Summary
    print("=== Crawl Summary ===")
    print(f"Pages crawled: {pages_crawled}")
    print(f"Pages errored: {pages_errored}")
    print(f"Forms found: {total_forms}")
    print(f"Links found: {total_links}")
    print(f"Injection vectors: {len(vectors)}")

    if vectors:
        print()
        print("=== Discovered Vectors ===")
        for v in vectors:
            print(f"  [{v.method}] {v.url}")
            print(f"       param: {v.param_name} ({v.param_type}) [{v.location}]")

    # Export if requested
    if args.export:
        export_vectors(vectors, args.export)
        print()
        print(f"Exported {len(vectors)} vector(s) to {args.export}")
        print()
        print("Use with inject command:")
        print(f"  ricochet inject --from-crawl {args.export} --callback-url <url>")

    return 0


def cmd_findings(args, store) -> int:
    """Handle findings subcommand - show correlated findings.

    Args:
        args: Parsed command line arguments.
        store: InjectionStore instance.

    Returns:
        Exit code (0 for success).
    """
    from ricochet.output import output_json, output_text

    # Calculate since timestamp if provided
    since = None
    if args.since:
        since = time.time() - (args.since * 3600)  # hours to seconds

    # Get findings from store
    findings = store.get_findings(
        since=since,
        min_severity=args.min_severity
    )

    # Output in requested format
    # Use args.verbose from global -v flag
    verbose = getattr(args, 'verbose', 0) > 0

    if args.output == 'json':
        output_json(findings, verbose=verbose)
    else:
        output_text(findings, verbose=verbose)

    return 0


def _cmd_inject_from_crawl(args, store) -> int:
    """Handle inject --from-crawl mode.

    Injects payloads into vectors discovered during crawling.
    Each crawl vector specifies its own URL, method, and parameter.

    Args:
        args: Parsed command line arguments with from_crawl set.
        store: InjectionStore instance.

    Returns:
        Exit code (0 for success, 1 for errors, 2 for argument errors).
    """
    from ricochet.injection.crawler import CrawlVector, load_crawl_vectors
    from ricochet.injection.http_client import send_request, prepare_headers_for_body
    from ricochet.injection.injector import substitute_callback
    from ricochet.injection.rate_limiter import RateLimiter
    from ricochet.core.store import InjectionRecord
    from urllib.parse import urlparse, urlencode, parse_qs

    # Load crawl vectors
    if not args.from_crawl.exists():
        print(f"Error: Crawl vector file not found: {args.from_crawl}", file=sys.stderr)
        return 2

    try:
        crawl_vectors = load_crawl_vectors(args.from_crawl)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if not crawl_vectors:
        print("Warning: No vectors found in crawl file", file=sys.stderr)
        return 0

    print(f"Loaded {len(crawl_vectors)} vector(s) from {args.from_crawl}")
    print()

    # Load payloads
    if hasattr(args, 'payloads') and args.payloads:
        if not args.payloads.exists():
            print(f"Error: Payloads file not found: {args.payloads}", file=sys.stderr)
            return 2

        try:
            from ricochet.injection.payloads import load_payloads
            payloads = load_payloads(args.payloads)
        except UnicodeDecodeError as e:
            print(f"Error: Failed to read payloads file: {e}", file=sys.stderr)
            return 2

        if not payloads:
            print("Warning: No payloads found in file", file=sys.stderr)
            return 0

        print(f"Loaded {len(payloads)} payload(s)")
        print()
    else:
        payloads = [args.payload]

    if args.dry_run:
        print("=== DRY RUN MODE ===")
        print()

    # When using proxy, inform user
    if args.proxy:
        print(f"[*] Using proxy: {args.proxy}")
        print("[*] SSL verification disabled for proxy compatibility")
        print()

    # Create rate limiter
    rate_limiter = RateLimiter(rate=args.rate, burst=1)

    # Track results
    successful = 0
    failed = 0

    for cv in crawl_vectors:
        for payload in payloads:
            # Generate callback URL with correlation ID
            callback_with_id, correlation_id = substitute_callback(
                payload, args.callback_url
            )

            # Build the request based on vector location
            parsed = urlparse(cv.url)
            use_https = parsed.scheme == "https"

            if cv.location == "query":
                # Inject into query string
                query_params = parse_qs(parsed.query, keep_blank_values=True)
                # Set the parameter (replace if exists)
                query_params[cv.param_name] = [callback_with_id]
                new_query = urlencode(query_params, doseq=True)
                target_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
                method = cv.method
                body = None
            elif cv.location == "body":
                # Inject into POST body
                target_url = cv.url
                method = cv.method
                body = urlencode({cv.param_name: callback_with_id}).encode()
            else:
                # Default: treat as query
                target_url = f"{cv.url}?{cv.param_name}={callback_with_id}"
                method = cv.method
                body = None

            # Build headers
            headers = {
                "Host": parsed.netloc,
                "User-Agent": "Ricochet/1.0",
            }
            if body:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                headers = prepare_headers_for_body(headers, body)

            # Record injection
            record = InjectionRecord(
                id=correlation_id,
                target_url=target_url,
                parameter=cv.param_name,
                payload=callback_with_id,
                timestamp=time.time(),
                context=f"crawl:{cv.location}:{cv.method}",
            )
            store.record_injection(record)

            if args.dry_run:
                print(f"[*] {cv.location}:{cv.param_name}")
                print(f"    Correlation ID: {correlation_id}")
                print(f"    URL: {target_url}")
                print(f"    Method: {method}")
                print(f"    Status: DRY-RUN")
                print()
                successful += 1
                continue

            # Rate limit
            rate_limiter.acquire()

            # Send request
            try:
                response = send_request(
                    url=target_url,
                    method=method,
                    headers=headers,
                    body=body,
                    timeout=args.timeout,
                    verify_ssl=False,
                    proxy_url=args.proxy,
                )
                print(f"[+] {cv.location}:{cv.param_name}")
                print(f"    Correlation ID: {correlation_id}")
                print(f"    URL: {target_url}")
                print(f"    Status: HTTP {response.status}")
                print()
                successful += 1

            except (TimeoutError, ConnectionError) as e:
                print(f"[-] {cv.location}:{cv.param_name}")
                print(f"    Correlation ID: {correlation_id}")
                print(f"    URL: {target_url}")
                print(f"    Error: {e}")
                print()
                failed += 1

    # Summary
    print("=== Summary ===")
    print(f"Total: {successful + failed} injection(s)")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if args.dry_run:
        print()
        print("Note: No requests were sent (dry-run mode)")

    return 0 if failed == 0 else 1


def cmd_inject(args, store) -> int:
    """Handle inject subcommand - inject payloads into targets.

    Args:
        args: Parsed command line arguments.
        store: InjectionStore instance.

    Returns:
        Exit code (0 for success, 1 for errors, 2 for argument errors).
    """
    from ricochet.injection.injector import Injector
    from ricochet.injection.parser import (
        ParsedRequest,
        parse_request_file,
        parse_request_string,
    )
    from ricochet.injection.rate_limiter import RateLimiter
    from ricochet.injection.vectors import InjectionVector, extract_vectors
    from urllib.parse import urlparse

    # Handle --from-crawl mode (different injection approach)
    if hasattr(args, 'from_crawl') and args.from_crawl:
        return _cmd_inject_from_crawl(args, store)

    # Build or parse request
    if args.url:
        # Build simple GET request from URL
        parsed_url = urlparse(args.url)
        if not parsed_url.scheme:
            # No scheme, assume http or use --https
            scheme = "https" if args.https else "http"
            args.url = f"{scheme}://{args.url}"
            parsed_url = urlparse(args.url)

        if not parsed_url.netloc:
            print(f"Error: Invalid URL: {args.url}", file=sys.stderr)
            return 2

        # Build path with query
        path = parsed_url.path or "/"
        if parsed_url.query:
            path = f"{path}?{parsed_url.query}"

        request = ParsedRequest(
            method="GET",
            path=path,
            http_version="HTTP/1.1",
            headers={"Host": parsed_url.netloc, "User-Agent": "Ricochet/1.0"},
            body=None,
            host=parsed_url.netloc,
        )
        use_https = parsed_url.scheme == "https"

    elif args.request:
        # Read and parse Burp-format request file
        if not args.request.exists():
            print(f"Error: Request file not found: {args.request}", file=sys.stderr)
            return 2

        try:
            # Read in binary mode to preserve CRLF
            content = args.request.read_bytes()
            request = parse_request_file(content)
            use_https = args.https
        except ValueError as e:
            print(f"Error: Failed to parse request file: {e}", file=sys.stderr)
            return 2
    else:
        print("Error: Specify -u URL, -r request.txt, or --from-crawl vectors.json", file=sys.stderr)
        return 2

    # Create rate limiter and injector
    rate_limiter = RateLimiter(rate=args.rate, burst=1)

    # When using proxy, inform user
    if args.proxy:
        print(f"[*] Using proxy: {args.proxy}")
        print("[*] SSL verification disabled for proxy compatibility")
        print()

    injector = Injector(
        store=store,
        rate_limiter=rate_limiter,
        timeout=args.timeout,
        callback_url=args.callback_url,
        proxy_url=args.proxy,
    )

    # Get vectors
    vectors = extract_vectors(request)

    if not vectors:
        print("Warning: No injectable vectors found in request", file=sys.stderr)
        return 0

    # Load payloads from file or use single payload
    if args.payloads:
        if not args.payloads.exists():
            print(f"Error: Payloads file not found: {args.payloads}", file=sys.stderr)
            return 2

        try:
            from ricochet.injection.payloads import load_payloads
            payloads = load_payloads(args.payloads)
        except UnicodeDecodeError as e:
            print(f"Error: Failed to read payloads file (invalid UTF-8): {e}", file=sys.stderr)
            return 2

        if not payloads:
            print("Warning: No payloads found in file (empty or all comments)", file=sys.stderr)
            return 0

        print(f"Loaded {len(payloads)} payload(s) from {args.payloads}")
        print()
    else:
        payloads = [args.payload]

    if args.dry_run:
        print("=== DRY RUN MODE ===")
        print()

    # Inject all payloads
    all_results = []

    if args.param:
        # Find matching vector once
        matching_vector = None
        for v in vectors:
            if v.name == args.param:
                matching_vector = v
                break

        if matching_vector is None:
            print(f"Error: Parameter '{args.param}' not found in request", file=sys.stderr)
            print(f"Available parameters:", file=sys.stderr)
            for v in vectors:
                print(f"  - {v.location}:{v.name}", file=sys.stderr)
            return 2

        # Inject each payload into the specific parameter
        for payload in payloads:
            result = injector.inject_vector(
                request=request,
                vector=matching_vector,
                payload=payload,
                use_https=use_https,
                dry_run=args.dry_run,
            )
            all_results.append(result)
    else:
        # Inject each payload into all vectors
        for payload in payloads:
            results = injector.inject_all_vectors(
                request=request,
                payload=payload,
                use_https=use_https,
                dry_run=args.dry_run,
            )
            all_results.extend(results)

    results = all_results

    # Display results
    successful = 0
    failed = 0

    for result in results:
        status_icon = "[+]" if result.success else "[-]"
        status_info = f"HTTP {result.status}" if result.success and result.status else result.error

        print(f"{status_icon} {result.vector.location}:{result.vector.name}")
        print(f"    Correlation ID: {result.correlation_id}")
        print(f"    URL: {result.url}")
        print(f"    Status: {status_info}")
        print()

        if result.success:
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"=== Summary ===")
    print(f"Total: {len(results)} injection(s)")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if args.dry_run:
        print()
        print("Note: No requests were sent (dry-run mode)")

    return 0 if failed == 0 else 1


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code: 0 for success, 1 for runtime errors, 2 for argument errors.
    """
    try:
        parser = create_parser()
        args = parser.parse_args()

        # Initialize database (creates on first run)
        db_path = args.db if args.db is not None else get_db_path()
        store = InjectionStore(db_path)

        # If no command given, print help and exit successfully
        if args.command is None:
            parser.print_help()
            return 0

        # Dispatch to subcommand handler if one is set
        if hasattr(args, 'func'):
            return args.func(args, store)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130  # 128 + SIGINT(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
