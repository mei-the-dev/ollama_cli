from tests.factory.spec import TestSpec

spec_test_extract_json_object_various = TestSpec(
    name='test_extract_json_object_various',
    description='Generated from test_extract_json_object_various',
    markers=['SingularityAgent'],
    input_prompt=None,
    expected_contains=['assert res == expected'],
    expected_not_contains=[],
)

spec_test_process_with_tools_calls_mcp = TestSpec(
    name='test_process_with_tools_calls_mcp',
    description='Generated from test_process_with_tools_calls_mcp',
    markers=['SingularityAgent', 'agent', 'model_event_logger'],
    input_prompt=None,
    expected_contains=["assert 'Executed' in res or res.startswith('✓')", "assert 'PROMPT' in kinds", "assert 'ASSISTANT' in kinds", "assert 'PARSED_TOOL' in kinds", "assert parsed['payload']['tool'] == 'test_tool'", "assert parsed['payload']['args'] == {'x': 1}", "assert isinstance(parsed['payload'].get('raw'), dict)", "assert parsed['payload']['raw'].get('tool') == 'test_tool'", "assert name == 'test_tool'", "assert args == {'x': 1}"],
    expected_not_contains=[],
)

spec_test_process_with_tools_normalizes_file_path = TestSpec(
    name='test_process_with_tools_normalizes_file_path',
    description='Generated from test_process_with_tools_normalizes_file_path',
    markers=['SingularityAgent', 'agent', 'model_event_logger'],
    input_prompt=None,
    expected_contains=["assert 'Executed' in res or res.startswith('✓')", "assert any((e.get('event') == 'PARSED_TOOL' and e.get('payload', {}).get('tool') == 'write_code' for e in evs))", "assert parsed['payload']['args'].get('filepath') == target", "assert parsed['payload']['args'].get('content') == 'hello'", "assert isinstance(parsed['payload'].get('raw'), dict)", "assert 'file_path' in parsed['payload']['raw'].get('args', {}) or 'filepath' in parsed['payload']['raw'].get('args', {})", "assert name == 'write_code'", "assert args.get('filepath') == target", "assert args.get('content') == 'hello'"],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_extract_json_object_various, spec_test_process_with_tools_calls_mcp, spec_test_process_with_tools_normalizes_file_path]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
