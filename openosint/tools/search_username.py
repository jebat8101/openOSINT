# openosint/tools/search_username.py
"""
Username OSINT module.

Wraps the 'sherlock' binary to enumerate online services
where a target username is registered.
"""

import asyncio
import logging
import shutil

from openosint.tools.exceptions import (
    OSINTError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
)

logger = logging.getLogger(__name__)

_BINARY = "sherlock"
_DEFAULT_TIMEOUT = 180
_PER_SITE_TIMEOUT = "3"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _execute_sherlock(username: str, timeout: int) -> str:
    """
    Execute the sherlock binary asynchronously against *username*.

    Parameters
    ----------
    username:
        Target username or alias.
    timeout:
        Maximum wall-clock seconds before the process is killed.

    Returns
    -------
    str
        Raw stdout decoded as UTF-8 containing discovered profile URLs.

    Raises
    ------
    ToolNotFoundError
        Binary is absent from the system PATH.
    ToolExecutionError
        No output was produced (all sites failed or username not found).
    ToolTimeoutError
        Process did not terminate within *timeout* seconds.
    """
    if not shutil.which(_BINARY):
        raise ToolNotFoundError(
            f"'{_BINARY}' is not installed or not in PATH. "
            "Install it with: pip install sherlock-project"
        )

    # --print-found suppresses negative results, reducing LLM context noise.
    # --timeout limits per-site connection time independently of the global timeout.
    command: list[str] = [
        _BINARY,
        username,
        "--print-found",
        "--timeout",
        _PER_SITE_TIMEOUT,
    ]
    process: asyncio.subprocess.Process | None = None

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=float(timeout),
        )

        raw = stdout.decode("utf-8", errors="replace").strip()

        if not raw:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ToolExecutionError(
                f"sherlock produced no output for '{username}'. stderr: {detail}"
            )

        return raw

    except asyncio.TimeoutError:
        if process is not None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        raise ToolTimeoutError(
            f"sherlock scan of '{username}' timed out after {timeout}s."
        )


def _format_output(raw: str, username: str) -> str:
    """Return a structured string suitable for both CLI display and LLM consumption."""
    if not raw:
        return f"No accounts found for username '{username}'."
    return f"OSINT results for username '{username}':\n\n{raw}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_username_osint(
    username: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT,
) -> str:
    """
    Run a username OSINT scan and return a formatted result string.

    On tool-level failure the error is caught, logged, and returned
    as a descriptive string so that callers (MCP server, CLI) can
    relay the message without raising.

    Parameters
    ----------
    username:
        Target username or alias.
    timeout_seconds:
        Maximum execution time passed to the subprocess layer.

    Returns
    -------
    str
        Formatted result string or a descriptive error message.
    """
    logger.info("Starting username OSINT scan for: %s", username)

    try:
        raw = await _execute_sherlock(username, timeout_seconds)
        result = _format_output(raw, username)
        logger.info("Username scan complete for: %s", username)
        return result

    except OSINTError as exc:
        logger.warning("Username scan failed: %s", exc)
        return f"Scan error: {exc}"

    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected error during username scan.")
        return f"Internal error: {exc}"
