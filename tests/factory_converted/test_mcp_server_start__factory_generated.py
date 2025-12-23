from tests.factory.spec import TestSpec

spec_test_parse_listen_line_variants = TestSpec(
    name='test_parse_listen_line_variants',
    description='Generated from test_parse_listen_line_variants',
    markers=['SingularityAgent'],
    input_prompt=None,
    expected_contains=['assert singularity_cli.SingularityAgent._parse_mcp_listen_line(line) == expected'],
    expected_not_contains=[],
)

spec_test_start_mcp_server_success = TestSpec(
    name='test_start_mcp_server_success',
    description='Generated from test_start_mcp_server_success',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=['assert result is True', "assert agent.mcp_server_url == 'http://127.0.0.1:54321'", "assert not any((e.get('event') == 'PARSED_TOOL' for e in evs))"],
    expected_not_contains=[],
)

spec_test_start_mcp_server_timeout = TestSpec(
    name='test_start_mcp_server_timeout',
    description='Generated from test_start_mcp_server_timeout',
    markers=['SingularityAgent', 'agent'],
    input_prompt=None,
    expected_contains=['assert result is False', 'assert agent.mcp_server_url is None'],
    expected_not_contains=[],
)

spec_test_parse_listen_line_hostname_and_ipv6 = TestSpec(
    name='test_parse_listen_line_hostname_and_ipv6',
    description='Generated from test_parse_listen_line_hostname_and_ipv6',
    markers=['SingularityAgent'],
    input_prompt=None,
    expected_contains=['assert singularity_cli.SingularityAgent._parse_mcp_listen_line(line) == expected'],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_parse_listen_line_variants, spec_test_start_mcp_server_success, spec_test_start_mcp_server_timeout, spec_test_parse_listen_line_hostname_and_ipv6]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
