"""GatewayPort over MCP. The pipeline and the Strands tool gate decide; this only carries an approved call.

The target is an MCPServer in-process, or the URL of a Streamable HTTP server, which is the shape of an
AgentCore Gateway MCP target.
"""

import asyncio
from typing import Any

from mcp.client import Client
from mcp.server.mcpserver import MCPServer

from fs_prod_agent.mcp_servers.catalog import manifest_for


class ToolCallFailed(RuntimeError):
    """The MCP server returned an error result for a call."""


class McpGateway:
    def __init__(self, target: MCPServer | str) -> None:
        self.target = target
        self.calls: list[str] = []

    def call(self, tool_name: str, arguments: dict[str, str]) -> str:
        manifest_for(tool_name)
        text = asyncio.run(self._call(tool_name, arguments))
        self.calls.append(tool_name)
        return text

    async def _call(self, tool_name: str, arguments: dict[str, str]) -> str:
        async with Client(self.target) as client:
            result = await client.call_tool(tool_name, dict(arguments))
        text = "\n".join(_text(block) for block in result.content)
        if result.is_error:
            raise ToolCallFailed(f"{tool_name}: {text}")
        return text


def _text(block: Any) -> str:
    return str(getattr(block, "text", ""))
