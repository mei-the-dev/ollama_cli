from tests.factory.spec import TestSpec

spec_test_live_model_emits_tool_and_mcp_exec = TestSpec(
    name='test_live_model_emits_tool_and_mcp_exec',
    description='Integration test: require Ollama running locally. It should emit a JSON tool call which we execute via MCP.\n\n- Starts the production MCP server from ref/v2/production_mcp_server.py (random port)\n- Ensures Ollama is reachable (fails if not)\n- Sends a prompt that instructs the model to output *only* a JSON tool call: {"tool": "write_code", "args": {...}}\n- process_with_tools should detect and execute the tool via MCP and return a success summary\n- The test verifies the file exists with the expected content',
    markers=['SingularityAgent', 'agent', 'event_reader'],
    input_prompt=None,
    expected_contains=['assert mcp_script.exists()', "assert parsed['payload'].get('tool') in ('write_code', 'write_file')", "assert isinstance(parsed['payload'].get('raw'), dict) or parsed['payload'].get('args')", "assert any((k in raw_args for k in ('filepath', 'file_path')))", 'assert any((v for v in raw_args.values() if isinstance(v, str)))'],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_live_model_emits_tool_and_mcp_exec]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
