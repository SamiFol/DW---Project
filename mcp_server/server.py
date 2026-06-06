"""MCP server (UC4).

Exposes the data warehouse as MCP tools so an LLM client (Claude Desktop, the
MCP Inspector, Cursor, ...) can answer questions grounded strictly in stored
data. Every tool calls the tested Repository / analytics layer (via
mcp_server.tools), so the assistant reports what the warehouse holds rather than
inventing finance facts.

Built on the official MCP Python SDK (`mcp`), high-level FastMCP server.

Run it:
    pip install mcp
    python -m mcp_server.server          # stdio transport (default)
    # or debug interactively in the MCP Inspector:
    mcp dev mcp_server/server.py
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_server import tools

mcp = FastMCP("acme-dwh")


@mcp.tool()
def list_assets(as_of: str | None = None) -> list[dict]:
    """List available financial assets (id, symbol, class, region). Optional
    `as_of` ISO date reconstructs the catalogue as it was at that time."""
    return tools.list_assets_impl(tools.repo(), as_of)


@mcp.tool()
def get_asset(asset_id: str, as_of: str | None = None) -> dict:
    """Full details of one asset by id, optionally as of a past `as_of` date."""
    return tools.get_asset_impl(tools.repo(), asset_id, as_of)


@mcp.tool()
def list_sources() -> list[dict]:
    """List the data providers (provenance) the warehouse ingested from."""
    return tools.list_sources_impl(tools.repo())


@mcp.tool()
def get_source(source_id: str) -> dict:
    """Full details of one data source/provider by id."""
    return tools.get_source_impl(tools.repo(), source_id)


@mcp.tool()
def get_time_series(asset_id: str, source_id: str,
                    start: str | None = None, end: str | None = None) -> dict:
    """Time-series points (OHLCV/indicators) for an asset from a given source,
    optionally bounded by `start`/`end` ISO dates."""
    return tools.get_time_series_impl(tools.repo(), asset_id, source_id, start, end)


@mcp.tool()
def summarize_trends(asset_id: str, source_id: str, end: str | None = None) -> dict:
    """Computed insights for an asset: aggregations, trend, volatility-based
    risk, and a naive next-day forecast. `end` caps the history analysed."""
    return tools.summarize_trends_impl(tools.repo(), asset_id, source_id, end)


@mcp.tool()
def compare_assets(asset_id_a: str, asset_id_b: str, source_id: str) -> dict:
    """Side-by-side computed insights for two assets from the same source."""
    return tools.compare_assets_impl(tools.repo(), asset_id_a, asset_id_b, source_id)


@mcp.tool()
def explain_change(asset_id: str, source_id: str) -> dict:
    """Grounded figures (start/last price, % change, risk) for explaining how an
    asset moved. The assistant must narrate using only these numbers."""
    return tools.explain_change_impl(tools.repo(), asset_id, source_id)


@mcp.prompt()
def grounded_analyst() -> str:
    """A priming prompt that keeps the assistant grounded in warehouse data."""
    return (
        "You are Acme Ltd's market-data analyst. Answer ONLY using the acme-dwh "
        "MCP tools. First call the relevant tool(s), then explain the numbers "
        "they return. Never state prices, trends, or risk levels that did not "
        "come from a tool call. If the data is missing, say so."
    )


if __name__ == "__main__":
    mcp.run()
