"""CLI entry point and argument parser for Ricochet."""

import argparse
import sys
from pathlib import Path

from ricochet import __version__
from ricochet.core.store import InjectionStore, get_db_path


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
    listen_parser.set_defaults(func=cmd_listen)

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
    else:
        print("Error: specify --http to start HTTP callback server", file=sys.stderr)
        print("  Example: ricochet listen --http", file=sys.stderr)
        return 2


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
