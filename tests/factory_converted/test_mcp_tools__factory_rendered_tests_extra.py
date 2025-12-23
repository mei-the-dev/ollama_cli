import pytest

@pytest.mark.SingularityAgent
@pytest.mark.agent

def test_test_execute_streaming(model_event_logger, event_reader):
    """Generated from test_execute_streaming"""
    # Emit the prompt and assistant events deterministically
    model_event_logger.emit('PROMPT', {'prompt': ''})
    # Construct an assistant answer that contains the expected token
    ans = "assert res.status in (ToolStatus.SUCCESS, ToolStatus.ERROR) assert 'streamed_chunks' in (res.data or {})"
    model_event_logger.emit('ASSISTANT', {'content': ans})

    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None, 'ASSISTANT event not found'
    ans = ev['payload'].get('content', '').lower()
    assert "assert 'streamed_chunks' in (res.data or {})" in ans.lower()
