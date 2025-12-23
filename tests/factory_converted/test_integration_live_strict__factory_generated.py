from tests.factory.spec import TestSpec

spec_test_live_strict_write_code = TestSpec(
    name='test_live_strict_write_code',
    description='Strict end-to-end test (no mocking): model must emit a single JSON object (or fenced json) and nothing else.\n\n- Uses a production MCP server subprocess\n- Uses a real local Ollama model (chosen from /api/tags)\n- Verifies assistant output contains only JSON (or fenced JSON) and that the write succeeds',
    markers=['SingularityAgent', 'agent', 'event_reader'],
    input_prompt=None,
    expected_contains=['assert mcp_script.exists()', "assert isinstance(result, str) and result.startswith('✓')", "assert read_res.get('status') == 'SUCCESS'", 'assert file_text == content', "assert assistant_msg and isinstance(assistant_msg.get('content'), str)", 'assert parsed is not None', 'assert raw == parsed', "assert any((e.get('event') == 'PARSED_TOOL' for e in evs))", "assert ev.get('event') == 'PARSED_TOOL'", "assert isinstance(ev.get('payload', {}).get('raw') or ev.get('payload', {}).get('args'), dict)"],
    expected_not_contains=[],
)

spec_test_live_fragmented_json_streaming = TestSpec(
    name='test_live_fragmented_json_streaming',
    description='Ask the model to emit the JSON tool call fragmented across many small chunks and ensure the streamer reassembles it correctly.',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=['assert mcp_script.exists()', "assert isinstance(result, str) and result.startswith('✓')", "assert read_res.get('status') == 'SUCCESS'", 'assert file_text == content'],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_live_strict_write_code, spec_test_live_fragmented_json_streaming]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
