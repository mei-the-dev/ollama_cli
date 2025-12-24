from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class ToolCategory(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"


@dataclass
class Tool:
    name: str
    description: str
    category: ToolCategory = ToolCategory.SYSTEM
    default_permission: str = "ask"
    schema: Optional[Dict[str, Any]] = field(default_factory=dict)
    handler: Optional[Callable] = None


# Simple registry
_registry: Dict[str, Tool] = {}


def register_tool(name: str, description: str = "", category: ToolCategory = ToolCategory.SYSTEM, default_permission: str = "ask", schema: Optional[Dict] = None):
    def _decorator(func: Callable):
        t = Tool(name=name, description=description, category=category, default_permission=default_permission, schema=schema or {}, handler=func)
        _registry[name] = t
        return func

    return _decorator


def get_tool(name: str) -> Optional[Tool]:
    return _registry.get(name)


def list_tools():
    return list(_registry.values())


def clear_registry():
    _registry.clear()
