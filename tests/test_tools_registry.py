import pytest
import tools


def test_register_and_get_tool():
    tools.clear_registry()

    @tools.register_tool("echo", description="Echoes input", category=tools.ToolCategory.READ, default_permission="always_allow")
    def echo_handler(args):
        return {"echo": args}

    t = tools.get_tool("echo")
    assert t is not None
    assert t.name == "echo"
    assert t.description == "Echoes input"
    assert t.category == tools.ToolCategory.READ
    assert t.default_permission == "always_allow"
    assert callable(t.handler)

    # Handler should be callable and return expected result
    res = t.handler({"foo": "bar"})
    assert res == {"echo": {"foo": "bar"}}


def test_list_tools_returns_registered():
    tools.clear_registry()

    @tools.register_tool("a", description="a")
    def a_handler(args):
        return True

    @tools.register_tool("b", description="b")
    def b_handler(args):
        return True

    lst = tools.list_tools()
    names = {t.name for t in lst}
    assert names == {"a", "b"}
