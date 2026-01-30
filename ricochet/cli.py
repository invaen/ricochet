"""CLI entry point and argument parser for Ricochet."""

import argparse
import sys
from pathlib import Path

from ricochet import __version__


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
    parser.add_subparsers(
        title='commands',
        dest='command',
        metavar='<command>'
    )

    return parser


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code: 0 for success, 1 for runtime errors, 2 for argument errors.
    """
    try:
        parser = create_parser()
        args = parser.parse_args()

        # If no command given, print help and exit successfully
        if args.command is None:
            parser.print_help()
            return 0

        # Dispatch to subcommand handler if one is set
        if hasattr(args, 'func'):
            return args.func(args)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130  # 128 + SIGINT(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
