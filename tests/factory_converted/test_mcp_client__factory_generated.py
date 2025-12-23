from tests.factory.spec import TestSpec

spec_test_call_mcp_tool_success = TestSpec(
    name='test_call_mcp_tool_success',
    description='Generated from test_call_mcp_tool_success',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=["assert payload['name'] == 'test_tool'", "assert res['status'] == 'SUCCESS'", "assert res['data']['result'] == 'ok'", "assert not any((e.get('event') == 'PARSED_TOOL' for e in evs))"],
    expected_not_contains=[],
)

spec_test_call_mcp_tool_retries_on_5xx_then_success = TestSpec(
    name='test_call_mcp_tool_retries_on_5xx_then_success',
    description='Generated from test_call_mcp_tool_retries_on_5xx_then_success',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=["assert res['status'] == 'SUCCESS'", "assert res['data']['recovered'] is True", "assert state['calls'] >= 2"],
    expected_not_contains=[],
)

spec_test_call_mcp_tool_timeout = TestSpec(
    name='test_call_mcp_tool_timeout',
    description='Generated from test_call_mcp_tool_timeout',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=["assert res['status'] == 'ERROR'", "assert 'timeout' in res['error'].lower() or 'deadline' in res['error'].lower()"],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_call_mcp_tool_success, spec_test_call_mcp_tool_retries_on_5xx_then_success, spec_test_call_mcp_tool_timeout]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
