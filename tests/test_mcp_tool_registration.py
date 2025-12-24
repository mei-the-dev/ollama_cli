import pytest

import mcp_server
import tools


def test_mcp_server_registers_tools():
    # Ensure registry clean
    tools.clear_registry()

    server = mcp_server.MCPServer()

    # Expected tools were registered
    for name in ["read_file", "write_file", "apply_diff", "execute_bash", "search_codebase", "analyze_file", "git_operation"]:
        t = tools.get_tool(name)
        assert t is not None, f"Tool {name} not registered"
        assert callable(t.handler), f"Handler for {name} must be callable"
        # Read tools default to always_allow
        if name in ("read_file", "search_codebase", "analyze_file"):
            assert t.default_permission == "always_allow"
        else:
            assert t.default_permission == "ask"