"""Read-only synthetic forecast exposed through the official MCP SDK."""

from pathlib import Path

from mcp.server.fastmcp import FastMCP
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


if __name__ == "__main__":
    server.run(transport="stdio")
