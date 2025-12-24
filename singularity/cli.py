"""Compatibility shim for CLI.
Exports: SingularityCLI, main()
"""
from typing import Optional

# Import from the existing top-level module as a compatibility shim
from singularity_cli import SingularityCLI, main as legacy_main  # type: ignore


def get_cli(*args, **kwargs) -> SingularityCLI:
    return SingularityCLI(*args, **kwargs)


def main(argv: Optional[list] = None) -> None:
    """Entry point compatibility: delegate to legacy main()"""
    # legacy_main reads sys.argv internally; passing argv is optional
    legacy_main()


__all__ = ["get_cli", "main", "SingularityCLI"]
