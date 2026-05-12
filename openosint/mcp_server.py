# openosint/mcp_server.py
"""
OpenOSINT MCP Server — v2.3.0

Exposes all 9 OSINT tool capabilities to MCP-compliant AI clients
over standard I/O.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from openosint.json_output import to_json
from openosint.tools.search_email import run_email_osint
from openosint.tools.search_username import run_username_osint
from openosint.tools.search_breach import run_breach_osint
from openosint.tools.search_whois import run_whois_osint
from openosint.tools.search_ip import run_ip_osint
from openosint.tools.search_domain import run_domain_osint
from openosint.tools.generate_dorks import run_dork_osint
from openosint.tools.search_paste import run_paste_osint
from openosint.tools.search_phone import run_phone_osint

logging.basicConfig(level=logging.INFO, format="[MCP] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
app = Server("openosint")

# Optional json_output field appended to every tool's inputSchema.
_JSON_PROP = {"json_output": {"type": "boolean", "description": "Return result as structured JSON."}}


def _with_json(schema: dict) -> dict:
    """Return a copy of *schema* with the optional json_output property added."""
    props = dict(schema.get("properties", {}))
    props.update(_JSON_PROP)
    return {**schema, "properties": props}


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="search_email", description="Enumerate accounts linked to an email using holehe.", inputSchema=_with_json({"type":"object","properties":{"email":{"type":"string"}},"required":["email"]})),
        Tool(name="search_username", description="Enumerate platforms where a username is registered using sherlock.", inputSchema=_with_json({"type":"object","properties":{"username":{"type":"string"}},"required":["username"]})),
        Tool(name="search_breach", description="Check if an email appears in data breaches via HaveIBeenPwned. Requires HIBP_API_KEY env var.", inputSchema=_with_json({"type":"object","properties":{"email":{"type":"string"}},"required":["email"]})),
        Tool(name="search_whois", description="Retrieve WHOIS registration data for a domain.", inputSchema=_with_json({"type":"object","properties":{"domain":{"type":"string"}},"required":["domain"]})),
        Tool(name="search_ip", description="Retrieve geolocation and ASN data for an IP address via ipinfo.io.", inputSchema=_with_json({"type":"object","properties":{"ip":{"type":"string"}},"required":["ip"]})),
        Tool(name="search_domain", description="Enumerate subdomains of a target domain using sublist3r.", inputSchema=_with_json({"type":"object","properties":{"domain":{"type":"string"}},"required":["domain"]})),
        Tool(name="generate_dorks", description="Generate targeted Google dork URLs for any target (name, email, username, domain).", inputSchema=_with_json({"type":"object","properties":{"target":{"type":"string"}},"required":["target"]})),
        Tool(name="search_paste", description="Search Pastebin dumps for an email or username via psbdmp.ws.", inputSchema=_with_json({"type":"object","properties":{"query":{"type":"string"}},"required":["query"]})),
        Tool(name="search_phone", description="Gather carrier and geolocation data for a phone number using phoneinfoga. Use E.164 format.", inputSchema=_with_json({"type":"object","properties":{"phone":{"type":"string"}},"required":["phone"]})),
    ]


# Map tool name → (coroutine factory, target key for JSON export)
_HANDLERS: dict[str, tuple] = {
    "search_email":    (lambda a: run_email_osint(a["email"], timeout_seconds=120),    lambda a: a["email"]),
    "search_username": (lambda a: run_username_osint(a["username"], timeout_seconds=180), lambda a: a["username"]),
    "search_breach":   (lambda a: run_breach_osint(a["email"]),                        lambda a: a["email"]),
    "search_whois":    (lambda a: run_whois_osint(a["domain"]),                        lambda a: a["domain"]),
    "search_ip":       (lambda a: run_ip_osint(a["ip"]),                               lambda a: a["ip"]),
    "search_domain":   (lambda a: run_domain_osint(a["domain"]),                       lambda a: a["domain"]),
    "generate_dorks":  (lambda a: run_dork_osint(a["target"]),                         lambda a: a["target"]),
    "search_paste":    (lambda a: run_paste_osint(a["query"]),                         lambda a: a["query"]),
    "search_phone":    (lambda a: run_phone_osint(a["phone"]),                         lambda a: a["phone"]),
}


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    logger.info("Tool: %s | args: %s", name, arguments)
    use_json = bool(arguments.get("json_output", False))
    try:
        if name not in _HANDLERS:
            raise ValueError(f"Unknown tool: '{name}'")
        handler, target_fn = _HANDLERS[name]
        result = await handler(arguments)
        if use_json:
            target = target_fn(arguments)
            text = to_json(name, target, result)
        else:
            text = result
        return CallToolResult(content=[TextContent(type="text", text=text)], isError=False)
    except (KeyError, ValueError) as exc:
        logger.error("Validation error: %s", exc)
        return CallToolResult(content=[TextContent(type="text", text=str(exc))], isError=True)
    except Exception as exc:
        logger.exception("Unhandled error in tool '%s'.", name)
        return CallToolResult(content=[TextContent(type="text", text=f"Internal error: {exc}")], isError=True)


async def _serve() -> None:
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())

def main() -> None:
    asyncio.run(_serve())

if __name__ == "__main__":
    main()
