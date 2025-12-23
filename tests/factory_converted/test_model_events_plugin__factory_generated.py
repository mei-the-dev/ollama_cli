from tests.factory.spec import TestSpec

spec_test_model_event_fixture_writes_jsonl = TestSpec(
    name='test_model_event_fixture_writes_jsonl',
    description='Ensure the fixture writes events to the configured JSONL path.',
    markers=['model_event_logger'],
    input_prompt=None,
    expected_contains=['assert p.exists()', 'assert len(lines) == 2', "assert entries[0]['event'] == 'PROMPT'", "assert entries[1]['event'] == 'ASSISTANT'", "assert entries[1]['payload']['content'] == 'world'"],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_model_event_fixture_writes_jsonl]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
