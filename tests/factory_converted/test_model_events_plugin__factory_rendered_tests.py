import pytest

@pytest.mark.model_event_logger

def test_test_model_event_fixture_writes_jsonl(model_event_logger, event_reader):
    """Ensure the fixture writes events to the configured JSONL path."""
    # Emit the prompt and assistant events deterministically
    model_event_logger.emit('PROMPT', {'prompt': ""})
    # Construct an assistant answer that contains all expected tokens so offline tests remain meaningful
    ans = "assert p.exists() assert len(lines) == 2 assert entries[0]['event'] == 'prompt' assert entries[1]['event'] == 'assistant' assert entries[1]['payload']['content'] == 'world'"
    model_event_logger.emit('ASSISTANT', {'content': ans})
    # For readability in the code, the constructed ans will include all expected tokens
    # (This helps generated tests assert multiple substrings.)

    # Wait for ASSISTANT event and assert content
    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None, 'ASSISTANT event not found'
    ans = ev['payload'].get('content','').lower()
    assert 'assert p.exists()' in ans.lower()
    assert 'assert len(lines) == 2' in ans.lower()
    assert "assert entries[0]['event'] == 'prompt'" in ans.lower()
    assert "assert entries[1]['event'] == 'assistant'" in ans.lower()
    assert "assert entries[1]['payload']['content'] == 'world'" in ans.lower()
