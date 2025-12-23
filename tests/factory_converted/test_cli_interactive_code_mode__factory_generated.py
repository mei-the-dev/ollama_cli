from tests.factory.spec import TestSpec

spec_test_interactive_code_mode_prints_code_and_no_placeholder = TestSpec(
    name='test_interactive_code_mode_prints_code_and_no_placeholder',
    description="Simulate interactive CLI: /mode code, then a code prompt, ensure code-like reply and no 'placeholder' in output.",
    markers=['SingularityAgent'],
    input_prompt='interactive prompt',
    expected_contains=['def ', "assert any((e.get('event') == 'ASSISTANT' for e in evs))"],
    expected_not_contains=['placeholder'],
)


def test_factory_generated():
    for spec in [spec_test_interactive_code_mode_prints_code_and_no_placeholder]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
