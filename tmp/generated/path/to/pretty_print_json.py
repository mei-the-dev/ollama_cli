#!/usr/bin/env python3
import json
from typing import Any

def pretty_print_json(data: Any) -> None:
    """
    Pretty-prints JSON data to the terminal with colorization if 'rich' is available.
    Falls back to standard print if 'rich' is not installed.
    
    Args:
        data (Any): The JSON data to be printed. This can be a dictionary, list, or any serializable object.
    """
    try:
        from rich import print as rprint
        from rich.json import JSON
        # Use 'rich' to pretty-print the JSON with colorization
        rprint(JSON(json.dumps(data, indent=4)))
    except ImportError:
        # Fallback to standard print if 'rich' is not available
        print(json.dumps(data, indent=4))
