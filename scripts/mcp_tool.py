#!/usr/bin/env python3
import sys
import json
import asyncio
from pathlib import Path
# Ensure project root is on sys.path so imports work when run from tests or other dirs
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from mcp_server import MCPServer, ToolResult  # noqa: E402

async def main():
    if len(sys.argv) < 3:
        print("Usage: mcp_tool.py <tool_name> '<json args>'")
        sys.exit(2)
    tool = sys.argv[1]
    try:
        args = json.loads(sys.argv[2])
    except Exception:
        print("Invalid JSON args")
        sys.exit(2)
    server = MCPServer()
    handler = getattr(server, tool, None)
    if not handler:
        print(f"Unknown tool: {tool}")
        sys.exit(2)
    result = handler(args)
    if asyncio.iscoroutine(result):
        result = await result
    if isinstance(result, ToolResult):
        out = {
            "status": result.status.value,
            "data": result.data,
            "error": result.error,
            "warnings": result.warnings,
            "metadata": result.metadata,
        }
        print(json.dumps(out, indent=2))
    else:
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
