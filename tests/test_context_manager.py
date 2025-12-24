import os
from pathlib import Path
import tempfile

import context_manager


def test_add_file_and_build_context(tmp_path):
    cm = context_manager.ContextManager(max_tokens=200)

    f = tmp_path / "a.py"
    f.write_text("def foo():\n    return 1\n\n# end")
    assert cm.add_file(f) is True

    cm.add_snippet("note", "This is a short snippet about behavior.")
    prompt = cm.build_context_prompt()
    assert "###" in prompt
    assert "def foo" in prompt


def test_truncation_respects_token_budget(tmp_path):
    cm = context_manager.ContextManager(max_tokens=10)
    long_text = "\n".join(["line {}".format(i) for i in range(100)])
    cm.add_snippet("long", long_text)
    prompt = cm.build_context_prompt()
    # Should be truncated
    assert len(prompt.splitlines()) < 100
    # Must include header
    assert "### long" in prompt
