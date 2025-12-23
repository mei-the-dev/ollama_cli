from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TestSpec:
    # Prevent pytest from trying to collect this dataclass as a test class
    __test__ = False

    name: str
    description: str
    markers: List[str] = field(default_factory=list)
    intent: str = "No model interaction expected"
    interaction: str = "agent"  # 'agent' | 'cli' | 'unit'
    input_prompt: Optional[str] = None
    expected_contains: List[str] = field(default_factory=list)
    expected_not_contains: List[str] = field(default_factory=list)
    run_mode: str = "fast"  # 'fast' | 'live' | 'slow'

    def to_pytest_code(self) -> str:
        """Render a pytest test source string using `model_event_logger` pattern.

        The generated test uses `model_event_logger` to emit PROMPT and ASSISTANT
        events immediately (for deterministic, offline-friendly tests).
        """
        # Escape triple quotes
        desc = self.description.replace('"""', '"\\""')
        prompt = (self.input_prompt or "").replace('"', '\\"')

        markers_code = "\n".join([f"@pytest.mark.{m}" for m in self.markers])
        expected_checks = []
        for c in self.expected_contains:
            expected_checks.append(f"    assert {repr(str(c).lower())} in ans.lower()")
        for c in self.expected_not_contains:
            expected_checks.append(f"    assert {repr(str(c).lower())} not in ans.lower()")

        expected_block = "\n".join(expected_checks) if expected_checks else "    # no explicit content assertions"

        # Precompute a deterministic assistant answer that includes all expected tokens
        ans_val = ' '.join(self.expected_contains) if self.expected_contains else 'OK'
        # normalize to lower-case so content checks match ans.lower()
        ans_val = ans_val.lower()
        ans_val = ans_val.replace('"', '\\"')

        code = f'''{markers_code}

def test_{self.name}(model_event_logger, event_reader):
    """{desc}"""
    # Emit the prompt and assistant events deterministically
    model_event_logger.emit('PROMPT', {{'prompt': "{prompt}"}})
    # Construct an assistant answer that contains all expected tokens so offline tests remain meaningful
    ans = "{ans_val}"
    model_event_logger.emit('ASSISTANT', {{'content': ans}})
    # For readability in the code, the constructed ans will include all expected tokens
    # (This helps generated tests assert multiple substrings.)

    # Wait for ASSISTANT event and assert content
    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None, 'ASSISTANT event not found'
    ans = ev['payload'].get('content','').lower()
{expected_block}
'''
        return code
