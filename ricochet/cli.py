"""CLI entry point and argument parser for Ricochet."""

import argparse
import secrets
import sys
import time
from pathlib import Path

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
