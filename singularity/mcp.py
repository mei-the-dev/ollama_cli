"""MCP shim
Re-exports MCP server functionality from top-level `mcp_server.py` for gradual migration."""
from mcp_server import MCPServer  # type: ignore

__all__ = ["MCPServer"]
