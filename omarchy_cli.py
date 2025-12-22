#!/usr/bin/env python3
"""Compatibility shim for the rebrand to Singularity.

This module keeps the legacy module name `omarchy_cli` available for imports and
for users who still call the old script name. It re-exports the new API from
`singularity_cli.py` and prints a deprecation notice when executed directly.
"""

import warnings
import asyncio

# Import the canonical implementations from the rebranded module
try:
    from singularity_cli import SingularityAgent, SingularityCLI, main  # type: ignore
except Exception:
    raise

# Provide backward-compatible names
OmarchyAgent = SingularityAgent  # type: ignore[name-defined]
OmarchyCLI = SingularityCLI  # type: ignore[name-defined]

if __name__ == "__main__":
    warnings.warn("The 'omarchy' command and API are deprecated; please use 'singularity' instead.", DeprecationWarning)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        try:
            from rich.console import Console

            Console().print("\n[yellow]Goodbye![/yellow]")
        except Exception:
            pass
