# openosint/mcp_server.py
"""
OpenOSINT MCP Server.

Exposes OSINT tool capabilities to MCP-compliant AI clients
(Claude Code, Claude Desktop, etc.) over standard I/O.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

from openosint.tools.search_email import run_email_osint
from openosint.tools.search_username import run_username_osint

logging.basicConfig(
    level=logging.INFO,
    format="[MCP] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Server("openosint")


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    Declare available OSINT tools to the connected AI agent.

    The *description* field is the primary signal the LLM uses to decide
    when and how to invoke each tool. Keep descriptions precise.
    """
    return [
        Tool(
            name="search_email",
            description=(
                "Enumerate online accounts and services associated with an email "
                "address. Use this to map a target's digital presence."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Target email address (e.g. target@example.com).",
                    }
                },
                "required": ["email"],
            },
        ),
        Tool(
            name="search_username",
            description=(
                "Enumerate social networks, forums, and web services where a "
                "specific username is registered. Use this to track an alias."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Target username or alias (e.g. johndoe99).",
                    }
                },
                "required": ["username"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool router
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """
    Route an incoming tool call from the AI agent to the appropriate handler.

    All exceptions are caught here and converted to MCP error responses so
    that the agent receives actionable feedback rather than a silent failure.
    """
    logger.info("Tool requested: %s | args: %s", name, arguments)

    try:
        if name == "search_email":
            return await _handle_search_email(arguments)
        if name == "search_username":
            return await _handle_search_username(arguments)

        raise ValueError(f"Unknown tool: '{name}'")

    except ValueError as exc:
        logger.error("Validation error for tool '%s': %s", name, exc)
        return _error_response(str(exc))

    except Exception as exc:
        logger.exception("Unhandled error executing tool '%s'.", name)
        return _error_response(f"Internal server error: {exc}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _handle_search_email(args: dict[str, Any]) -> CallToolResult:
    email: str | None = args.get("email")
    if not email:
        raise ValueError("Required parameter 'email' is missing.")
    result = await run_email_osint(email, timeout_seconds=120)
    return _ok_response(result)


async def _handle_search_username(args: dict[str, Any]) -> CallToolResult:
    username: str | None = args.get("username")
    if not username:
        raise ValueError("Required parameter 'username' is missing.")
    result = await run_username_osint(username, timeout_seconds=180)
    return _ok_response(result)


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _ok_response(text: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=False,
    )


def _error_response(text: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        isError=True,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _serve() -> None:
    logger.info("OpenOSINT MCP server starting (stdio transport).")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def main() -> None:
    """Synchronous entry point for the MCP server process."""
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
