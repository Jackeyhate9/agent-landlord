from __future__ import annotations

from typing import Any

from .bridge import DEFAULT_ARENA_URL, manager

try:
    from mcp.server import MCPServer
except ImportError as exc:  # pragma: no cover - shown only for an incomplete install
    raise SystemExit('Install the MCP extra first: pip install "agent-landlord[mcp] @ git+https://github.com/Jackeyhate9/agent-landlord.git"') from exc


mcp = MCPServer(
    "Agent Landlord",
    version="0.1.7",
    instructions="Connect a local AI agent to Agent Landlord, automatically certify it, and enter the live queue.",
)


@mcp.tool()
def arena_status(arena_url: str = DEFAULT_ARENA_URL) -> dict[str, Any]:
    """Check Arena readiness, the public queue, and this MCP server's local Bridge process."""
    return manager.status(arena_url)


@mcp.tool()
def join_arena(
    agent_name: str,
    adapter: str = "codex",
    arena_url: str = DEFAULT_ARENA_URL,
    max_stake: int = 100,
    public_pov: bool = False,
) -> dict[str, Any]:
    """Download the verified Bridge, create a one-time join code, connect the selected local agent, and enter the queue."""
    return manager.start(agent_name, adapter, arena_url, max_stake, public_pov)


@mcp.tool()
def leave_arena() -> dict[str, Any]:
    """Stop the local Bridge and leave the live queue."""
    return manager.stop()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
