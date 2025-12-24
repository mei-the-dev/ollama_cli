import os
import asyncio

import singularity_cli


class DummySession:
    def __init__(self, responses):
        self._responses = responses
        self.prompt_calls = 0

    def prompt(self, *args, **kwargs):
        # synchronous prompt
        if self._responses:
            return self._responses.pop(0)
        return '/exit'


async def run_it():
    # Use small sequence: /mode code, /exit
    dummy = DummySession(['/mode code', '/exit'])
    monkey = lambda *a, **k: dummy


def test_prompt_toolkit_mode_enabled(monkeypatch):
    # Enable prompt_toolkit mode but patch PromptSession to use DummySession
    monkeypatch.setenv('SINGULARITY_USE_PROMPT_TOOLKIT', '1')
    class FakePromptSession:
        def __init__(self, *a, **k):
            self._d = DummySession(['/mode code', '/exit'])
        def prompt(self, *a, **k):
            return self._d.prompt()
    monkeypatch.setattr('singularity_cli.PromptSession', FakePromptSession)

    # Also ensure key bindings function exists
    cli = singularity_cli.SingularityCLI()
    assert hasattr(cli, 'setup_key_bindings')

    # Running interactive_mode should not raise (it will exit internally)
    import asyncio
    asyncio.run(cli._interactive_mode_prompt_toolkit())
    # cleanup
    monkeypatch.delenv('SINGULARITY_USE_PROMPT_TOOLKIT', raising=False)
