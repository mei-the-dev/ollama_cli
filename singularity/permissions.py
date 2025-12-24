"""Permissions shim
Re-export PermissionManager and PermissionLevel from singularity_cli for gradual migration."""
from singularity_cli import PermissionManager, PermissionLevel  # type: ignore

__all__ = ["PermissionManager", "PermissionLevel"]
