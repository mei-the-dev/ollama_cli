"""Singularity packaged API shim

This package is a thin wrapper while we gradually refactor the codebase into a package layout.
It re-exports the primary public surface for backward-compatible imports.
"""

__all__ = ["__version__", "cli", "agent", "mcp", "tools", "permissions", "context", "ui"]

__version__ = "0.0.0-refactor"

# Lazy imports to avoid expensive startup
from . import cli  # noqa: E402,F401
from . import agent  # noqa: E402,F401
from . import mcp  # noqa: E402,F401
from . import tools  # noqa: E402,F401
from . import permissions  # noqa: E402,F401
from . import context  # noqa: E402,F401
from . import ui  # noqa: E402,F401
