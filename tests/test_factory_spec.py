from tests.factory.spec import TestSpec
from textwrap import dedent


def test_to_pytest_code_contains_expected_snippet():
    s = TestSpec(
        name="sample",
        description="A sample test",
        markers=['fast'],
        input_prompt="generate hello",
        expected_contains=["hello"],
    )
    code = s.to_pytest_code()
    assert "model_event_logger.emit('PROMPT'" in code
    assert "model_event_logger.emit('ASSISTANT'" in code
    assert "assert 'hello' in ans.lower()" in code
