"""Read-only synthetic forecast exposed through the official MCP SDK.

The server speaks stdio by default. With --transport streamable-http it serves HTTP for clients
that should connect to an already running container instead of starting one per session.
"""

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

server = FastMCP("solar-forecast")
FORECAST = Path(__file__).resolve().parents[1] / "lab/forecast/day.json"
READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


class HourForecast(BaseModel):
    """Forecast for one eligible one-hour charging block."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hour: int = Field(ge=0, le=23, description="Hour of day, 0 through 23")
    pv_wh: int = Field(ge=0, description="Forecast solar generation in watt-hours")
    home_wh: int = Field(ge=0, description="Forecast household consumption in watt-hours")


class DayForecast(BaseModel):
    """Charging requirement and eligible hours for one day."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    charge_wh: int = Field(gt=0, description="Energy each selected block delivers, in Wh")
    slots: int = Field(ge=1, description="Number of distinct hours to select")
    hours: list[HourForecast] = Field(max_length=24, description="Eligible hours")


@server.tool(annotations=READ_ONLY)
def forecast_day() -> DayForecast:
    """Read the synthetic forecast: charge per block, blocks to select, and eligible hours."""
    return DayForecast.model_validate_json(FORECAST.read_text())


def main() -> None:
    """Serve over stdio, or over streamable HTTP for loopback clients."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port")
    args = parser.parse_args()
    if args.transport == "streamable-http":
        server.settings.host = args.host
        server.settings.port = args.port
        # The container publishes the port on loopback only; reject other Host headers so a
        # page in a browser cannot reach the server through DNS rebinding.
        server.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*"],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*"],
        )
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
