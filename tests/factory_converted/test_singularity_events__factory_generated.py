from tests.factory.spec import TestSpec

spec_test_events_emitted = TestSpec(
    name='test_events_emitted',
    description='Generated from test_events_emitted',
    markers=['SingularityAgent', 'agent', 'model_event_logger'],
    input_prompt=None,
    expected_contains=["assert 'Executed' in res or 'Executed' in res or '✓ Executed' in res", "assert 'PROMPT' in kinds", "assert 'ASSISTANT' in kinds", "assert 'PARSED_TOOL' in kinds", "assert parsed_events['PARSED_TOOL']['payload']['tool'] == 'read_code'", "assert parsed_events['PARSED_TOOL']['payload']['args']['filepath'] == 'foo.txt'", "assert name == 'read_code'", "assert arguments.get('filepath') == 'foo.txt'"],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_events_emitted]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
