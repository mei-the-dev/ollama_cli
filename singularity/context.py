"""Context shim
Re-export ContextManager from the top-level `context_manager.py` file.
"""
from context_manager import ContextManager  # type: ignore

__all__ = ["ContextManager"]
