# openosint/cli.py
"""
OpenOSINT command-line interface.

Provides direct, human-in-the-loop execution of OSINT modules
without requiring an AI agent or MCP client.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from openosint.tools.search_email import run_email_osint
from openosint.tools.search_username import run_username_osint

_DIVIDER = "=" * 60


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _configure_logging(verbose: bool) -> None:
    """Configure root logger verbosity."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="[%(levelname)s] %(name)s: %(message)s")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="openosint",
        description="OpenOSINT — CLI interface for direct OSINT tool execution.",
        epilog="Example: openosint email target@example.com --timeout 60",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="command",
    )

    # email subcommand
    email_cmd = subparsers.add_parser(
        "email",
        help="Enumerate services registered against an email address.",
    )
    email_cmd.add_argument("target", type=str, metavar="ADDRESS")
    email_cmd.add_argument(
        "-t", "--timeout",
        type=int,
        default=120,
        metavar="SECONDS",
        help="Maximum execution time (default: 120).",
    )

    # username subcommand
    username_cmd = subparsers.add_parser(
        "username",
        help="Enumerate platforms where a username is registered.",
    )
    username_cmd.add_argument("target", type=str, metavar="USERNAME")
    username_cmd.add_argument(
        "-t", "--timeout",
        type=int,
        default=180,
        metavar="SECONDS",
        help="Maximum execution time (default: 180).",
    )

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _print_result(result: str) -> None:
    print(_DIVIDER)
    print(" SCAN RESULTS ".center(60, "="))
    print(_DIVIDER)
    print(result)
    print(_DIVIDER)


async def _handle_email(target: str, timeout: int) -> None:
    print(f"[*] Email scan: {target}")
    print(f"[*] Timeout: {timeout}s\n")
    result = await run_email_osint(email=target, timeout_seconds=timeout)
    _print_result(result)


async def _handle_username(target: str, timeout: int) -> None:
    print(f"[*] Username scan: {target}")
    print(f"[*] Timeout: {timeout}s\n")
    result = await run_username_osint(username=target, timeout_seconds=timeout)
    _print_result(result)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

async def _async_main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    if args.command == "email":
        await _handle_email(args.target, args.timeout)
    elif args.command == "username":
        await _handle_username(args.target, args.timeout)
    else:
        parser.print_help()
        sys.exit(1)


def main() -> None:
    """Synchronous entry point registered in pyproject.toml."""
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"[!] Fatal: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
