# openosint/tools/search_domain.py
"""
Domain enumeration module.

Uses crt.sh (certificate transparency) and sublist3r with stable search
engines. DNSdumpster and VirusTotal are excluded — they often break (CSRF /
rate limits) and crash sublist3r worker processes.

Returns a formatted string; never raises on failure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Iterable

import requests

from openosint.tools.exceptions import OSINTError, ToolExecutionError
from openosint.utils import SubprocessResult, run_subprocess

logger = logging.getLogger(__name__)

_BINARY = "sublist3r"
_DEFAULT_TIMEOUT = 120
_INSTALL_HINT = "Install it with: pip install sublist3r"
_CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"
# Exclude engines that frequently break (DNSdumpster CSRF, VirusTotal blocks).
_STABLE_ENGINES = "baidu,yahoo,google,bing,ask,netcraft,threatcrowd,ssl,passivedns"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_SUBDOMAIN_RE = re.compile(
    r"^(?:\*\.)?([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*)$",
    re.IGNORECASE,
)


def _normalize_domain(domain: str) -> str:
    """Strip scheme/path and return a bare hostname."""
    domain = domain.strip().lower()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix) :]
    return domain.split("/")[0].split(":")[0]


def _is_subdomain_of(candidate: str, domain: str) -> bool:
    candidate = candidate.lower().removeprefix("*.")
    return candidate == domain or candidate.endswith(f".{domain}")


def _parse_subdomains(text: str, domain: str) -> set[str]:
    """Extract unique hostnames for domain from sublist3r or crt.sh text output."""
    found: set[str] = set()
    for raw_line in text.splitlines():
        line = _ANSI_RE.sub("", raw_line).strip()
        if not line or line.startswith("["):
            continue
        # Sublist3r status lines and banners
        if any(
            token in line.lower()
            for token in ("enumerating", "searching", "total unique", "error:", "coded by")
        ):
            continue
        host = line.removeprefix("[+] ").strip().lower()
        if _is_subdomain_of(host, domain) and _SUBDOMAIN_RE.match(host):
            found.add(host)
    return found


def _fetch_crtsh_subdomains(domain: str, timeout_seconds: int) -> set[str]:
    """Query crt.sh certificate transparency logs for subdomains."""
    url = _CRTSH_URL.format(domain=domain)
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise OSINTError(f"crt.sh request failed: {exc}") from exc

    if response.status_code != 200:
        raise ToolExecutionError(
            f"crt.sh returned HTTP {response.status_code} for '{domain}'."
        )

    try:
        entries: list[dict] = response.json()
    except json.JSONDecodeError as exc:
        raise ToolExecutionError(f"crt.sh returned invalid JSON for '{domain}'.") from exc

    found: set[str] = set()
    for entry in entries:
        names = entry.get("name_value", "")
        for name in names.splitlines():
            host = name.strip().lower().removeprefix("*.")
            if _is_subdomain_of(host, domain):
                found.add(host)
    return found


async def _run_sublist3r(domain: str, timeout_seconds: int) -> SubprocessResult:
    """Execute sublist3r with engines that do not crash on DNSdumpster/VirusTotal."""
    return await run_subprocess(
        binary=_BINARY,
        args=["-d", domain, "-n", "-e", _STABLE_ENGINES],
        timeout_seconds=timeout_seconds,
        install_hint=_INSTALL_HINT,
    )


def _format_domain_results(subdomains: Iterable[str], domain: str, sources: list[str]) -> str:
    """Return a structured string suitable for CLI display and LLM consumption."""
    unique = sorted(set(subdomains), key=lambda h: (h.count("."), h))
    if not unique:
        return f"No subdomains found for '{domain}'."
    source_note = f" (sources: {', '.join(sources)})" if sources else ""
    body = "\n".join(f"[+] {host}" for host in unique)
    return f"Subdomains found for '{domain}'{source_note}:\n\n{body}"


async def run_domain_osint(
    domain: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT,
) -> str:
    """
    Enumerate subdomains of domain via crt.sh and sublist3r.

    Returns a descriptive error string on failure rather than raising.

    Parameters
    ----------
    domain:
        Target domain (e.g. example.com).
    timeout_seconds:
        Maximum execution time for external lookups.

    Returns
    -------
    str
        Formatted result string or a descriptive error message.
    """
    domain = _normalize_domain(domain)
    logger.info("Starting domain enumeration for: %s", domain)

    subdomains: set[str] = set()
    sources: list[str] = []
    errors: list[str] = []

    # crt.sh — reliable, no scraping / CSRF issues
    crt_timeout = min(timeout_seconds, 60)
    try:
        crt_subs = await asyncio.to_thread(
            _fetch_crtsh_subdomains, domain, crt_timeout
        )
        if crt_subs:
            subdomains |= crt_subs
            sources.append("crt.sh")
        logger.info("crt.sh returned %d hosts for %s", len(crt_subs), domain)
    except OSINTError as exc:
        logger.warning("crt.sh lookup failed: %s", exc)
        errors.append(str(exc))

    # sublist3r — skip dnsdumpster & virustotal (broken/blocked)
    try:
        result = await _run_sublist3r(domain, timeout_seconds)
        combined = f"{result.stdout}\n{result.stderr}"
        parsed = _parse_subdomains(combined, domain)
        if parsed:
            subdomains |= parsed
            sources.append("sublist3r")
        elif result.return_code != 0:
            errors.append(
                f"sublist3r exited with code {result.return_code} and no parseable hosts."
            )
        logger.info(
            "sublist3r returned %d hosts (exit %d) for %s",
            len(parsed),
            result.return_code,
            domain,
        )
    except OSINTError as exc:
        logger.warning("sublist3r failed: %s", exc)
        errors.append(str(exc))
    except Exception as exc:
        logger.exception("Unexpected error during sublist3r scan.")
        errors.append(f"sublist3r error: {exc}")

    if subdomains:
        logger.info("Domain enumeration complete for: %s (%d hosts)", domain, len(subdomains))
        return _format_domain_results(subdomains, domain, sources)

    if errors:
        return f"Scan error: no subdomains found for '{domain}'. " + "; ".join(errors)
    return f"No subdomains found for '{domain}'."
