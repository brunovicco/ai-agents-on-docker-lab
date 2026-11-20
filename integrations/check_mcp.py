"""Exercise the forecast server over the real MCP stdio transport."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check() -> None:
    """Negotiate, discover the only tool and request the synthetic forecast."""
    params = StdioServerParameters(
        command=sys.executable, args=[str(Path(__file__).with_name("forecast_mcp.py"))]
    )
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        result = await session.list_tools()
        if [tool.name for tool in result.tools] != ["forecast_day"]:
            raise ValueError("Unexpected tool catalog")
        reply = await session.call_tool("forecast_day", {})
        block = reply.content[0]
        if reply.isError or block.type != "text" or json.loads(block.text)["slots"] != 2:
            raise ValueError("Invalid MCP response")
        print("MCP OK: initialize, tools/list, tools/call forecast_day")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(check(), timeout=20))
