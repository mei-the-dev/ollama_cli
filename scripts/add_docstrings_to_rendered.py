"""Add missing docstrings to generated rendered pytest files in tests/factory_converted.

This script inserts a simple docstring into any test function that lacks one, using the function
name to generate a short description.

Usage:
    python scripts/add_docstrings_to_rendered.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDERED_GLOB = ROOT / "tests" / "factory_converted" / "*__factory_rendered_tests.py"

for p in Path(RENDERED_GLOB.parent).glob(RENDERED_GLOB.name):
    src = p.read_text()
    lines = src.splitlines()
    out_lines = []
    i = 0
    modified = False
    while i < len(lines):
        line = lines[i]
        out_lines.append(line)
        if line.strip().startswith("def test_"):
            # Peek next non-empty line
            j = i + 1
            # Skip decorators (should not be here since decorator lines are above def)
            if j < len(lines) and lines[j].strip().startswith('"""'):
                # already has docstring
                pass
            else:
                # Insert simple docstring
                fn_name = line.split()[1].split('(')[0]
                doc = f'    """Generated test for {fn_name}."""'
                out_lines.append(doc)
                modified = True
        i += 1
    if modified:
        p.write_text('\n'.join(out_lines) + '\n')
        print(f"Updated docstrings in: {p}")
    else:
        print(f"No changes needed: {p}")
