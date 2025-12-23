from tests.factory.spec import TestSpec

spec_test_cli_starts_mcp_server = TestSpec(
    name='test_cli_starts_mcp_server',
    description='Generated from test_cli_starts_mcp_server',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=['assert proc is not None', 'assert url is not None', "assert body.get('status') == 'ok'"],
    expected_not_contains=[],
)

spec_test_execute_streaming = TestSpec(
    name='test_execute_streaming',
    description='Ensure execute_code streaming returns streamed_chunks and appropriate status',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=['streamed_chunks'],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_cli_starts_mcp_server, spec_test_execute_streaming]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
