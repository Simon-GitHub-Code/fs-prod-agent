"""The desk's tools as an MCP server. Names, descriptions and effects come from the catalog manifests.

The server answers from the fixture book. It never decides: the pipeline's tool gate and policy run
before any call reaches it, as they would in front of an AgentCore Gateway MCP target.
"""

from collections.abc import Callable

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

from fs_prod_agent.adapters.local.books import holdings_text, manager_report, policy_text
from fs_prod_agent.mcp_servers.catalog import MANIFESTS

SERVER_NAME = "oversight-desk"
SERVE_HOST = "127.0.0.1"
SERVE_PORT = 8767


def get_manager_report(query: str = "") -> str:
    return manager_report(query)


def search_policy(query: str = "") -> str:
    del query
    return policy_text()


def get_holdings(query: str = "") -> str:
    del query
    return holdings_text()


def draft_briefing(topic: str = "") -> str:
    return f"Draft briefing saved for the analyst: {topic or 'untitled'}. It has not been sent."


def submit_committee_paper(title: str = "") -> str:
    return f"Paper queued for the investment committee: {title or 'untitled'}. A person must release it."


_HANDLERS: dict[str, Callable[..., str]] = {
    "get_manager_report": get_manager_report,
    "search_policy": search_policy,
    "get_holdings": get_holdings,
    "draft_briefing": draft_briefing,
    "submit_committee_paper": submit_committee_paper,
}


def build_server() -> MCPServer:
    """One tool per manifest. A manifest without a handler fails here, at build, not at call time."""
    server = MCPServer(SERVER_NAME, instructions="Investment oversight tools. The desk drafts and checks.")
    for manifest in MANIFESTS:
        server.tool(
            name=manifest.name,
            description=manifest.description,
            annotations=_annotations(manifest.effect),
        )(_HANDLERS[manifest.name])
    return server


def serve(host: str = SERVE_HOST, port: int = SERVE_PORT) -> None:
    build_server().run(transport="streamable-http", host=host, port=port)


def _annotations(effect: str) -> ToolAnnotations:
    return ToolAnnotations(read_only_hint=effect == "read", destructive_hint=False, idempotent_hint=effect == "read")
