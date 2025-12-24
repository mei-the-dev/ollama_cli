# This script provides a sandbox environment to safely execute untrusted Python code.

import ast
import sys
from typing import Any, Dict, Optional


class SafeEval(ast.NodeVisitor):
    """
    A class that uses the Abstract Syntax Tree (AST) module to traverse and evaluate Python code in a safe manner.
    It restricts access to certain built-in functions and modules to prevent malicious or unintended behavior.
    """

    def __init__(self, restricted_globals: Optional[Dict[str, Any]] = None):
        self.restricted_globals = {
            "__builtins__": {
                "None": None,
                "True": True,
                "False": False,
                "abs": abs,
                "all": all,
                "any": any,
                "ascii": ascii,
                "bin": bin,
                "bool": bool,
                "bytearray": bytearray,
                "bytes": bytes,
                "callable": callable,
                "chr": chr,
                "classmethod": classmethod,
                "compile": compile,
                "complex": complex,
                "delattr": delattr,
                "dict": dict,
                "dir": dir,
                "divmod": divmod,
                "enumerate": enumerate,
                "filter": filter,
                "float": float,
                "format": format,
                "frozenset": frozenset,
                "getattr": getattr,
                "globals": globals,
                "hasattr": hasattr,
                "hash": hash,
                "hex": hex,
                "id": id,
                "int": int,
                "isinstance": isinstance,
                "issubclass": issubclass,
                "iter": iter,
                "len": len,
                "list": list,
                "map": map,
                "max": max,
                "memoryview": memoryview,
                "min": min,
                "next": next,
                "object": object,
                "oct": oct,
                "open": open,
                "ord": ord,
                "pow": pow,
                "print": print,
                "property": property,
                "range": range,
                "repr": repr,
                "reversed": reversed,
                "round": round,
                "set": set,
                "setattr": setattr,
                "slice": slice,
                "sorted": sorted,
                "staticmethod": staticmethod,
                "str": str,
                "sum": sum,
                "super": super,
                "tuple": tuple,
                "type": type,
                "vars": vars,
                "zip": zip,
            },
        }

        if restricted_globals:
            self.restricted_globals.update(restricted_globals)

    def visit_Call(self, node):
        # Restrict calls to potentially dangerous functions
        func_name = ast.unparse(node.func)
        if func_name in ["__import__", "eval", "exec", "compile"]:
            raise ValueError(f"Function call {func_name} is not allowed.")
        self.generic_visit(node)

    def visit_Import(self, node):
        # Restrict import statements
        for alias in node.names:
            if alias.name.startswith("os") or alias.name.startswith("sys") or alias.name.startswith("subprocess"):
                raise ValueError(f"Import of {alias.name} is not allowed.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        # Restrict import from statements
        if node.module and (
            node.module.startswith("os") or node.module.startswith("sys") or node.module.startswith("subprocess")
        ):
            raise ValueError(f"Import from {node.module} is not allowed.")
        self.generic_visit(node)

    def evaluate(self, code: str) -> Any:
        # Parse the code into an AST and visit each node
        tree = ast.parse(code)
        self.visit(tree)
        # Execute the safe code in a restricted environment
        return eval(compile(tree, filename="<ast>", mode="exec"), self.restricted_globals)


def sandbox_execute_code(code: str) -> Any:
    """
    Executes untrusted Python code in a sandboxed environment.
    Args:
        code (str): The Python code to execute.

    Returns:
        Any: The result of the executed code.

    Raises:
        ValueError: If the code contains restricted operations.
    """
    safe_eval = SafeEval()
    return safe_eval.evaluate(code)


if __name__ == "__main__":
    # Example usage
    try:
        result = sandbox_execute_code('print("Hello, World!")')
        print(f"Execution successful: {result}")
    except ValueError as e:
        print(f"Execution failed: {e}")
