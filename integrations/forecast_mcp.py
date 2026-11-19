"""Read-only synthetic forecast exposed through the official MCP SDK."""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

server = FastMCP("solar-forecast")
FORECAST = Path(__file__).resolve().parents[1] / "lab/forecast/day.json"


@server.tool()
def forecast_day() -> str:
    """Read the synthetic forecast and the vehicle's charging requirement."""
    return json.dumps(json.loads(FORECAST.read_text()))


if __name__ == "__main__":
    server.run(transport="stdio")
