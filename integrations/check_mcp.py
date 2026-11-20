"""Exercise the forecast and decoy servers over the real MCP stdio transport."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

HERE = Path(__file__).resolve().parent
# Run the image as sbx would launch it: no network, read-only root, no capabilities.
DOCKER_RUN = [
    "run",
    "-i",
    "--rm",
    "--network",
    "none",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
]


def server_params(script: str, image: str | None) -> StdioServerParameters:
    """Launch a server script locally or inside the packaged image."""
    if image is None:
        return StdioServerParameters(command=sys.executable, args=[str(HERE / script)])
    args = [*DOCKER_RUN, "--entrypoint", "python", image, f"integrations/{script}"]
    return StdioServerParameters(command="docker", args=args)


async def check_forecast(image: str | None) -> None:
    """Check the catalog, annotations, schema, and structured result of forecast_day."""
    params = server_params("forecast_mcp.py", image)
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        if [tool.name for tool in tools] != ["forecast_day"]:
            raise ValueError("Unexpected tool catalog")
        hints = tools[0].annotations
        if hints is None or not hints.readOnlyHint or hints.openWorldHint:
            raise ValueError("forecast_day must be annotated read-only and closed-world")
        if tools[0].outputSchema is None:
            raise ValueError("forecast_day must publish an output schema")
        reply = await session.call_tool("forecast_day", {})
        data = reply.structuredContent
        if reply.isError or data is None or data["slots"] != 2 or len(data["hours"]) != 4:
            raise ValueError("Invalid structured MCP response")
        block = reply.content[0]
        if block.type != "text" or json.loads(block.text) != data:
            raise ValueError("Text content must mirror the structured result")
    print("MCP OK: forecast_day is read-only, typed, and returns the synthetic forecast")


async def check_http(url: str) -> None:
    """Check forecast_day on a running server over streamable HTTP."""
    async with (
        streamablehttp_client(url) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        if [tool.name for tool in (await session.list_tools()).tools] != ["forecast_day"]:
            raise ValueError("Unexpected tool catalog over HTTP")
        reply = await session.call_tool("forecast_day", {})
        if reply.isError or reply.structuredContent is None:
            raise ValueError("Invalid MCP response over HTTP")
        if reply.structuredContent["slots"] != 2:
            raise ValueError("Unexpected forecast over HTTP")
    print("MCP OK: forecast_day over streamable HTTP")


async def check_decoy(image: str | None) -> None:
    """Check that the decoy returns its canary."""
    params = server_params("decoy_mcp.py", image)
    async with stdio_client(params) as streams, ClientSession(*streams) as session:
        await session.initialize()
        reply = await session.call_tool("decoy_ping", {})
        block = reply.content[0]
        if reply.isError or block.type != "text" or not block.text.startswith("solar-decoy"):
            raise ValueError("Invalid decoy response")
    print("MCP OK: decoy_ping returns the canary")


def main() -> None:
    """Parse arguments and run the checks with a timeout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Run the servers from this image with Docker")
    parser.add_argument("--url", help="Check only a running forecast server at this HTTP URL")
    args = parser.parse_args()

    async def run() -> None:
        if args.url:
            await check_http(args.url)
            return
        await check_forecast(args.image)
        await check_decoy(args.image)

    asyncio.run(asyncio.wait_for(run(), timeout=60))


if __name__ == "__main__":
    main()
