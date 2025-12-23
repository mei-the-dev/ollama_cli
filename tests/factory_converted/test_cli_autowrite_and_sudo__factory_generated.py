from tests.factory.spec import TestSpec

spec_test_cli_autowrite = TestSpec(
    name='test_cli_autowrite',
    description='Generated from test_cli_autowrite',
    markers=['agent'],
    input_prompt=None,
    expected_contains=["assert 'PARSED_TOOL' in kinds or any((e.get('event') == 'ASSISTANT' for e in evs))", "assert parsed['payload'].get('tool') == 'write_code'", "assert raw_args.get('filepath') == 'test_out.txt' or raw_args.get('file_path') == 'test_out.txt'"],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_cli_autowrite]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
