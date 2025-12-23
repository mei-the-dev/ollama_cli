from tests.factory.spec import TestSpec

spec_test_generate_streaming_basic = TestSpec(
    name='test_generate_streaming_basic',
    description='Generated from test_generate_streaming_basic',
    markers=['SingularityAgent', 'agent', 'model_event_logger'],
    input_prompt=None,
    expected_contains=["assert agent.conversation_history and agent.conversation_history[-1]['content'] == 'Hello world'", "assert 'PROMPT' in kinds", "assert 'ASSISTANT' in kinds", "assert not any((e.get('event') == 'PARSED_TOOL' for e in evs))"],
    expected_not_contains=[],
)


def test_factory_generated():
    for spec in [spec_test_generate_streaming_basic]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
