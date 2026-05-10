# openosint/tools/search_email.py
"""
Email OSINT module.

Wraps the 'holehe' binary to enumerate online services
registered against a target email address.
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

_BINARY = "holehe"
_DEFAULT_TIMEOUT = 120


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _execute_holehe(email: str, timeout: int) -> str:
    """
    Execute the holehe binary asynchronously against *email*.

    Parameters
    ----------
    email:
        Target email address.
    timeout:
        Maximum wall-clock seconds before the process is killed.

    Returns
    -------
    str
        Raw stdout decoded as UTF-8.

    Raises
    ------
    ToolNotFoundError
        Binary is absent from the system PATH.
    ToolExecutionError
        Process exited with a non-zero return code.
    ToolTimeoutError
        Process did not terminate within *timeout* seconds.
    """
    if not shutil.which(_BINARY):
        raise ToolNotFoundError(
            f"'{_BINARY}' is not installed or not in PATH. "
            "Install it with: pip install holehe"
        )

    command: list[str] = [_BINARY, email, "--only-used"]
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

        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise ToolExecutionError(
                f"holehe exited with code {process.returncode}: {detail}"
            )

        return stdout.decode("utf-8", errors="replace").strip()

    except asyncio.TimeoutError:
        if process is not None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        raise ToolTimeoutError(
            f"holehe scan of '{email}' timed out after {timeout}s."
        )


def _format_output(raw: str, email: str) -> str:
    """Return a structured string suitable for both CLI display and LLM consumption."""
    if not raw:
        return f"No registered services found for {email}."
    return f"OSINT results for '{email}':\n\n{raw}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_email_osint(
    email: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT,
) -> str:
    """
    Run an email OSINT scan and return a formatted result string.

    On tool-level failure the error is caught, logged, and returned
    as a descriptive string so that callers (MCP server, CLI) can
    relay the message without raising.

    Parameters
    ----------
    email:
        Target email address.
    timeout_seconds:
        Maximum execution time passed to the subprocess layer.

    Returns
    -------
    str
        Formatted result string or a descriptive error message.
    """
    logger.info("Starting email OSINT scan for: %s", email)

    try:
        raw = await _execute_holehe(email, timeout_seconds)
        result = _format_output(raw, email)
        logger.info("Email scan complete for: %s", email)
        return result

    except OSINTError as exc:
        logger.warning("Email scan failed: %s", exc)
        return f"Scan error: {exc}"

    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected error during email scan.")
        return f"Internal error: {exc}"
