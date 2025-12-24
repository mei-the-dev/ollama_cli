"""Agent shim
Re-exports the SingularityAgent class for package consumers."""
from singularity_cli import SingularityAgent  # type: ignore

__all__ = ["SingularityAgent"]
