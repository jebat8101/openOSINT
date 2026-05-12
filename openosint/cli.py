# openosint/cli.py
"""
OpenOSINT command-line interface.

Default behaviour  : launches the interactive REPL (Claude Code style).
Subcommands        : direct tool execution without AI (email, username).

Usage:
    openosint                          # interactive REPL
    openosint email target@example.com # direct, no AI
    openosint username johndoe99       # direct, no AI
    openosint --parallel email target@example.com  # parallel tools
    openosint --json email target@example.com      # JSON output
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from openosint.json_output import format_tool_result, to_json
from openosint.tools.search_email import run_email_osint
from openosint.tools.search_username import run_username_osint
from openosint.tools.search_breach import run_breach_osint
from openosint.tools.search_paste import run_paste_osint

_DIVIDER = "=" * 60


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="[%(levelname)s] %(name)s: %(message)s")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openosint",
        description=(
            "OpenOSINT — AI-powered OSINT framework.\n"
            "Run without arguments to start the interactive REPL."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  openosint                                  # interactive AI session\n"
            "  openosint email target@example.com         # direct email scan\n"
            "  openosint username johndoe99               # direct username scan\n"
            "  openosint --parallel email target@example.com  # parallel tools\n"
            "  openosint --json email target@example.com  # JSON output\n"
        ),
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        metavar="KEY",
        help="Anthropic API key (overrides ANTHROPIC_API_KEY env var).",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help=(
            "Run independent complementary tools concurrently using asyncio.gather(). "
            "For 'email': runs search_email + search_breach in parallel. "
            "For 'username': runs search_username + search_paste in parallel."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as structured JSON instead of formatted text.",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    # shell subcommand (explicit alias for REPL)
    subparsers.add_parser(
        "shell",
        help="Start the interactive REPL (default when no command given).",
    )

    # email subcommand
    email_cmd = subparsers.add_parser(
        "email",
        help="Direct email scan via holehe (no AI).",
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
        help="Direct username scan via sherlock (no AI).",
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
# Output helpers
# ---------------------------------------------------------------------------

def _print_result(result: str) -> None:
    print(_DIVIDER)
    print(" SCAN RESULTS ".center(60, "="))
    print(_DIVIDER)
    print(result)
    print(_DIVIDER)


def _print_result_labeled(label: str, result: str) -> None:
    print(_DIVIDER)
    print(f" {label} ".center(60, "="))
    print(_DIVIDER)
    print(result)
    print(_DIVIDER)


def _emit_json(data: dict | list) -> None:
    print(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Direct command handlers (no AI)
# ---------------------------------------------------------------------------

async def _handle_email(
    target: str,
    timeout: int,
    parallel: bool = False,
    json_output: bool = False,
) -> None:
    if parallel:
        print(f"[*] Email scan (parallel): {target}", file=sys.stderr)
        email_result, breach_result = await asyncio.gather(
            run_email_osint(email=target, timeout_seconds=timeout),
            run_breach_osint(email=target),
        )
        if json_output:
            _emit_json([
                format_tool_result("search_email", target, email_result),
                format_tool_result("search_breach", target, breach_result),
            ])
        else:
            _print_result_labeled("search_email", email_result)
            _print_result_labeled("search_breach", breach_result)
    else:
        print(f"[*] Email scan: {target}", file=sys.stderr)
        print(f"[*] Timeout: {timeout}s\n", file=sys.stderr)
        result = await run_email_osint(email=target, timeout_seconds=timeout)
        if json_output:
            _emit_json(format_tool_result("search_email", target, result))
        else:
            _print_result(result)


async def _handle_username(
    target: str,
    timeout: int,
    parallel: bool = False,
    json_output: bool = False,
) -> None:
    if parallel:
        print(f"[*] Username scan (parallel): {target}", file=sys.stderr)
        username_result, paste_result = await asyncio.gather(
            run_username_osint(username=target, timeout_seconds=timeout),
            run_paste_osint(query=target),
        )
        if json_output:
            _emit_json([
                format_tool_result("search_username", target, username_result),
                format_tool_result("search_paste", target, paste_result),
            ])
        else:
            _print_result_labeled("search_username", username_result)
            _print_result_labeled("search_paste", paste_result)
    else:
        print(f"[*] Username scan: {target}", file=sys.stderr)
        print(f"[*] Timeout: {timeout}s\n", file=sys.stderr)
        result = await run_username_osint(username=target, timeout_seconds=timeout)
        if json_output:
            _emit_json(format_tool_result("search_username", target, result))
        else:
            _print_result(result)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

async def _async_main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    # No subcommand or explicit 'shell' → launch REPL
    if args.command in (None, "shell"):
        from openosint.repl import run_repl
        run_repl(api_key=getattr(args, "api_key", None))
        return

    parallel = getattr(args, "parallel", False)
    json_output = getattr(args, "json_output", False)

    if args.command == "email":
        await _handle_email(args.target, args.timeout, parallel=parallel, json_output=json_output)
    elif args.command == "username":
        await _handle_username(args.target, args.timeout, parallel=parallel, json_output=json_output)
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
