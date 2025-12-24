# This script provides a sandbox environment to safely execute untrusted Python code.

import ast
import sys
from io import StringIO


class RestrictedNodeVisitor(ast.NodeVisitor):
    # Define a set of allowed nodes
    ALLOWED_NODES = {"Module", "Expr", "Call", "Name", "Constant", "Load"}

    def visit(self, node):
        if type(node).__name__ not in self.ALLOWED_NODES:
            raise ValueError(f"Node {type(node).__name__} is not allowed")
        super().visit(node)


def safe_execute(code):
    # Parse the code into an AST
    tree = ast.parse(code)

    # Check for restricted nodes
    RestrictedNodeVisitor().visit(tree)

    # Define a restricted set of globals and locals
    restricted_globals = {
        "__builtins__": None,
        "print": print,
        "len": len,
        "range": range,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
    }
    restricted_locals = {}

    # Redirect stdout to capture print statements
    old_stdout = sys.stdout
    new_stdout = StringIO()
    sys.stdout = new_stdout
    try:
        # Execute the code in a restricted environment
        exec(compile(tree, filename="<ast>", mode="exec"), restricted_globals, restricted_locals)
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    # Return captured output and any results from the execution
    return new_stdout.getvalue(), restricted_locals


def main():
    code = "print('Hello, world!')"
    try:
        output, results = safe_execute(code)
        print(f"Output: {output}")
        print(f"Results: {results}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
