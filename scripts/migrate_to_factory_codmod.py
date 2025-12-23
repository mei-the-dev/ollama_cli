"""
Codemod to convert existing pytest tests that interact with SingularityAgent/model fixtures
into TestFactory-style TestSpec-based tests that emit structured events using ModelEventLogger.

This is a lightweight AST-based transformer that:
- Locates test functions that reference known fixtures (e.g., model_event_logger, SingularityAgent, event_reader)
- Creates a `TestSpec` instance with metadata: name, description from docstring (or placeholder), markers, steps
- Writes a new file under `tests/factory_converted/` with a generated pytest test using TestSpec

Usage:
    python scripts/migrate_to_factory_codmod.py --files path/to/test_file.py [--out tests/factory_converted]

This codemod is intentionally conservative: it will not modify the original file by default; instead
it will produce generated TestFactory tests into the output directory for review.
"""
import ast
import argparse
import os
import textwrap
from pathlib import Path

FIXTURE_KEYWORDS = {"SingularityAgent", "model_event_logger", "event_reader", "agent"}

TEMPLATE = '''from tests.factory.spec import TestSpec

{testspecs}


def test_factory_generated():
    for spec in [{names}]:
        code = spec.to_pytest_code()
        # Write or execute generated code - tests are already written/generated for CI
        assert isinstance(code, str)
'''

SPECFMT = '''spec_{pyname} = TestSpec(
    name={name!r},
    description={desc!r},
    markers={markers!r},
    input_prompt={input_prompt!r},
    expected_contains={expected_contains!r},
    expected_not_contains={expected_not_contains!r},
)'''



def find_test_functions(source_ast):
    """Return (func_def_node, name, docstring, identifiers)

    identifiers include: function arg names + any Name/Attribute identifiers used in the function body.
    This allows detection of fixtures that are referenced implicitly (not just as args).
    """
    tests = []

    for node in ast.walk(source_ast):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            # collect arg names
            arg_names = [a.arg for a in node.args.args]

            # collect Name and Attribute identifiers in body
            ids = set(arg_names)
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    ids.add(child.id)
                elif isinstance(child, ast.Attribute):
                    # attr may be 'execute_with_animation' or object.attr; include both
                    if isinstance(child.attr, str):
                        ids.add(child.attr)
                    if isinstance(child.value, ast.Name):
                        ids.add(child.value.id)

            doc = ast.get_docstring(node)
            tests.append((node, node.name, doc, sorted(ids)))
    return tests


def references_fixtures(identifiers):
    """Return True if any of the known fixture keywords are in identifiers."""
    return any(i in FIXTURE_KEYWORDS for i in identifiers)


def render_steps_from_func(node: ast.FunctionDef):
    # Very naive: extract simple calls and assert statements as steps
    steps = []
    for child in ast.walk(node):
        if isinstance(child, ast.Expr) and isinstance(child.value, ast.Call):
            func = child.value.func
            if isinstance(func, ast.Attribute):
                steps.append(ast.unparse(child).strip())
            elif isinstance(func, ast.Name):
                steps.append(ast.unparse(child).strip())
        elif isinstance(child, ast.Assert):
            steps.append("assert " + ast.unparse(child.test).strip())
    return steps or ["# no steps extracted"]


def generate_tests_from_file(path: Path, outdir: Path):
    src = path.read_text()
    tree = ast.parse(src)
    found = find_test_functions(tree)
    specs = []
    varnames = []
    for node, name, doc, fixtures in found:
        if references_fixtures(fixtures):
            desc = doc or "Generated from {name}".format(name=name)
            steps = render_steps_from_func(node)
            pyname = name
            # Ensure pyname is a valid Python identifier (test functions usually are)
            # Convert extracted steps into TestSpec fields where possible
            # Try to heuristically populate input_prompt and expected_contains/not_contains
            input_prompt = None
            expected_contains = []
            expected_not_contains = []
            for s in steps:
                if "setenv('TEST_MODEL_EVENTS_PATH'" in s or "setenv(\"TEST_MODEL_EVENTS_PATH\"" in s:
                    # not a content expectation
                    continue
                if s.strip().startswith("assert"):
                    # parse simple "assert 'foo' in out" style
                    if " in out" in s and "'" in s:
                        tok = s.split("'", 2)[1]
                        if "not" in s:
                            expected_not_contains.append(tok)
                        else:
                            expected_contains.append(tok)
                    elif "ASSISTANT" in s and "get('content')" in s:
                        expected_contains.append('ASSISTANT')
                    else:
                        expected_contains.append(s)
                elif "Prompt.ask" in s or "Prompt, 'ask'" in s or "Prompt.ask" in s:
                    input_prompt = "interactive prompt"
                elif "generate an animated" in s:
                    input_prompt = "generate an animated ux loading component"

            spec = SPECFMT.format(
                pyname=pyname,
                name=name,
                desc=desc,
                markers=[f for f in fixtures if f in FIXTURE_KEYWORDS],
                input_prompt=input_prompt,
                expected_contains=expected_contains,
                expected_not_contains=expected_not_contains,
            )
            specs.append(spec)
            varnames.append(f"spec_{pyname}")
    if not specs:
        return None
    testspecs = "\n\n".join(specs)
    names = ", ".join(varnames)
    content = TEMPLATE.format(testspecs=testspecs, names=names)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / (path.stem + "__factory_generated.py")
    outpath.write_text(content)

    # Additionally, generate an executable pytest file that contains the rendered test code
    # by instantiating TestSpec and calling to_pytest_code(). This means running the generated test
    # will actually emit model events (useful for enforcement).
    try:
        import sys
        sys.path.insert(0, str(Path('.').resolve()))
        from tests.factory.spec import TestSpec as _TS
        # For each spec block, instantiate and render
        pytest_blocks = []
        for s in specs:
            # evaluate the var assignment 'spec_<name> = TestSpec(...)' safely to extract args
            # naive parse: extract name and kwargs between parentheses
            left, right = s.split('=', 1)
            varname = left.strip()
            # execute right side in a safe namespace
            ns = {}
            right_d = textwrap.dedent(right)
            right_d = right_d.lstrip()
            try:
                # Execute RHS as an expression and assign to 'spec_obj' so we can retrieve it
                exec("spec_obj = " + right_d, {"TestSpec": _TS}, ns)
            except Exception as e:
                print("DEBUG: failed to exec spec rhs; repr(right_d[:300]):", repr(right_d[:300]))
                raise
            spec_obj = None
            # debug: show ns keys/types
            # print('DEBUG ns:', {k:type(v) for k,v in ns.items()})
            for v in ns.values():
                if isinstance(v, _TS):
                    spec_obj = v
                    break
            if spec_obj is None and 'TestSpec' in ns and isinstance(ns['TestSpec'], _TS):
                spec_obj = ns['TestSpec']
            if spec_obj is None:
                # fallback: pick first value that looks like a dataclass-like with name attribute
                for v in ns.values():
                    if hasattr(v, 'name'):
                        spec_obj = v
                        break
            if spec_obj is None:
                print('DEBUG: spec_obj not found in ns; ns keys:', list(ns.keys()))
            if hasattr(spec_obj, 'to_pytest_code'):
                pytest_blocks.append(spec_obj.to_pytest_code())
        if pytest_blocks:
            print(f"rendered {len(pytest_blocks)} pytest blocks for {path}")
            gpath = outdir / (path.stem + "__factory_rendered_tests.py")
            content = '\n\n'.join(pytest_blocks)
            if '@pytest' in content:
                content = 'import pytest\n\n' + content
            gpath.write_text(content)
        else:
            print(f"no pytest blocks rendered for {path}")
    except Exception as e:
        print("warning: could not render pytest files:", e)

    return outpath


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--files", nargs='+', required=True)
    p.add_argument("--out", default="tests/factory_converted")
    args = p.parse_args()
    outdir = Path(args.out)
    generated = []
    for f in args.files:
        path = Path(f)
        if not path.exists():
            print("file not found:", f)
            continue
        outpath = generate_tests_from_file(path, outdir)
        if outpath:
            print("generated:", outpath)
            generated.append(str(outpath))
        else:
            print("no convertible tests found in:", f)
    if not generated:
        print("No tests generated.")

if __name__ == '__main__':
    main()
