import ast
import json
import pytest

@pytest.mark.fast
def test_generated_function_has_docstring(model_event_logger, event_reader):
    """Generated code should include a function with a docstring."""
    model_event_logger.emit('PROMPT', {'prompt': 'Write a Python function `add(a, b)` that returns the sum and includes a short docstring.'})
    ans = "def add(a, b):\n    \"\"\"Return the sum of a and b.\"\"\"\n    return a + b\n"
    model_event_logger.emit('ASSISTANT', {'content': ans})

    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None, 'Expected ASSISTANT event'
    content = ev['payload'].get('content', '')

    # Parse AST and ensure function has a docstring
    tree = ast.parse(content)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs, 'No function definition found in generated code'
    doc = ast.get_docstring(funcs[0])
    assert doc and len(doc.strip()) > 0, 'Generated function missing docstring'


@pytest.mark.fast
def test_generated_code_parses_without_syntax_error(model_event_logger, event_reader):
    """Generated code must be syntactically valid Python."""
    model_event_logger.emit('PROMPT', {'prompt': 'Generate a small Python helper that multiplies two numbers.'})
    ans = "def mul(a, b):\n    return a * b\n"
    model_event_logger.emit('ASSISTANT', {'content': ans})

    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None
    content = ev['payload'].get('content', '')

    # Ensure ast.parse succeeds
    try:
        ast.parse(content)
    except SyntaxError as e:
        pytest.fail(f'Generated code had syntax error: {e}')


@pytest.mark.fast
def test_generated_code_includes_tests(model_event_logger, event_reader):
    """Generated code should include an example unit test or a usage example."""
    model_event_logger.emit('PROMPT', {'prompt': 'Provide a function `inc(x)` and include a simple pytest-style test function asserting behavior.'})
    ans = (
        "def inc(x):\n    return x + 1\n\n"
        "def test_inc():\n    assert inc(1) == 2\n"
    )
    model_event_logger.emit('ASSISTANT', {'content': ans})

    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None
    content = ev['payload'].get('content', '')

    assert 'def test_' in content or 'assert ' in content, 'Generated content does not include a test or assertion'


@pytest.mark.fast
def test_no_placeholders_in_generated_code(model_event_logger, event_reader):
    """Ensure generated code doesn't contain template placeholders like {{...}} or <...>."""
    model_event_logger.emit('PROMPT', {'prompt': 'Generate a function `greet(name)` that returns a greeting string.'})
    ans = "def greet(name):\n    return f'Hello, {name}'\n"
    model_event_logger.emit('ASSISTANT', {'content': ans})

    ev = event_reader.wait_for('ASSISTANT', timeout=0.5)
    assert ev is not None
    content = ev['payload'].get('content', '')

    assert '{{' not in content and '}}' not in content, 'Found moustache-style placeholder in generated content'
    assert '<' not in content or '>' not in content or ('<' in content and '>' in content and content.count('<') == content.count('>')), 'Found raw angle-bracket placeholders'


@pytest.mark.fast
def test_parsed_tool_call_for_write_code(model_event_logger, event_reader):
    """When code is to be written to disk, parser should emit PARSED_TOOL write_code."""
    model_event_logger.emit('PROMPT', {'prompt': 'Save the file /tmp/example.py with content: print("hello") and emit the tool call.'})
    # Simulate model's assistant content and the parsed tool call emitted by the agent
    model_event_logger.emit('ASSISTANT', {'content': '{"tool": "write_file", "args": {"file_path": "/tmp/example.py", "content": "print(\"hello\")"}}'})
    model_event_logger.emit('PARSED_TOOL', {'tool': 'write_code', 'args': {'filepath': '/tmp/example.py', 'content': 'print("hello")'}})

    ev = event_reader.wait_for('PARSED_TOOL', timeout=0.5)
    assert ev is not None, 'PARSED_TOOL event not found'
    payload = ev['payload']
    assert payload.get('tool') == 'write_code' or payload.get('tool') == 'write_file', 'Parsed tool is not write_code/write_file'
    args = payload.get('args') or {}
    assert args.get('filepath') or args.get('file_path'), 'Parsed tool call missing filepath'
