# Import necessary libraries
import json
from typing import Any


def pretty_print_json(data: Any) -> None:
    """
    Pretty-prints JSON data to the terminal with colorization if 'rich' is available.
    Fallbacks to standard print if 'rich' is not installed.

    Args:
        data (Any): The JSON data to be printed. Can be a dictionary, list, or any serializable object.
    """
    try:
        # Attempt to import rich and use its pretty-printing capabilities
        from rich.console import Console

        console = Console()
        console.print(json.dumps(data, indent=4))
    except ImportError:
        # Fallback to standard print if 'rich' is not available
        print(json.dumps(data, indent=4))
