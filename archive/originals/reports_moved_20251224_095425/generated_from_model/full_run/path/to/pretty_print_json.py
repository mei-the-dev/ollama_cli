# Import necessary libraries
import json
from typing import Any


def pretty_print_json(data: Any) -> None:
    """
    Pretty-prints JSON data to the terminal, using 'rich' if available,
    otherwise falling back to standard print.

    Args:
        data (Any): The JSON data to be printed. This can be a dictionary,
                    list, or any other serializable object.
    """
    try:
        # Attempt to import 'rich' and use it for colorized output
        from rich.console import Console

        console = Console()
        console.print(json.dumps(data, indent=4))
    except ImportError:
        # Fallback to standard print if 'rich' is not available
        print(json.dumps(data, indent=4))
