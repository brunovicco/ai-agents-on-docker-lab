"""Decoy MCP server for testing whether a static sandbox can reach servers it was not given.

Register it on the host without loading it into the sandbox. If an agent in that sandbox can
return the canary, the static tool catalog does not isolate unloaded servers.
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

CANARY = "solar-decoy-canary-3f9c"
server = FastMCP("solar-decoy")


@server.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
    )
)
def decoy_ping() -> str:
    """Return a fixed canary that proves this server was reached."""
    return CANARY


if __name__ == "__main__":
    server.run(transport="stdio")
