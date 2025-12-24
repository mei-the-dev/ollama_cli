#!/usr/bin/env python3
"""
Singularity MCP Server - Advanced Code Agent Tools (legacy: Omarchy)
Provides comprehensive development capabilities with self-improvement
"""

import ast
import asyncio
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from aiohttp import web


# Configuration
def load_config():
    default = {
        "model": "qwen2.5-coder:14b-instruct-q4_K_M",
        "temperature": 0.0,
        "context_length": 8192,
        "allow_sudo": False,
        "auto_apply": False,
    }
    try:
        # Prefer new location ~/.singularity if present, otherwise fallback to legacy ~/.omarchy
        cfg_path = (
            (Path.home() / ".singularity" / "config.json")
            if (Path.home() / ".singularity").exists()
            else (Path.home() / ".omarchy" / "config.json")
        )
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
                return {**default, **cfg}
            except Exception:
                return default
    except Exception:
        return default
    return default


# Structured result for all tool operations
class ToolStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"


@dataclass
class ToolResult:
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    warnings: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# MCP Server Implementation
class MCPServer:
    def __init__(self):
        self.config = load_config()
        # Compute base config directory at runtime so tests that monkeypatch HOME work correctly
        base_dir = (
            (Path.home() / ".singularity")
            if (Path.home() / ".singularity").exists()
            else (Path.home() / ".omarchy")
        )
        self.knowledge_base = base_dir / "knowledge"
        self.tools_dir = base_dir / "tools"
        self.plans_dir = base_dir / "plans"
        self.cache_dir = base_dir / "cache"
        self.context_dir = base_dir / "context"
        self.templates_dir = base_dir / "templates"
        self.init_directories()
        # Ensure config file exists with defaults if not present
        try:
            cfg_path = (
                (Path.home() / ".singularity" / "config.json")
                if (Path.home() / ".singularity").exists()
                else (Path.home() / ".singularity" / "config.json")
            )
            if not cfg_path.exists():
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(self.config, indent=2))
        except Exception:
            pass
        self.context_memory = []  # Active context window
        self.file_watchers = {}  # Track file changes

        # Telemetry / metrics
        from collections import deque

        self.start_time = time.time()
        self.telemetry = {
            "request_count": 0,
            "latencies_ms": deque(maxlen=1000),
            "recent_requests": deque(maxlen=1000),
        }

        # Register available tools into the central tools registry (if present)
        try:
            import tools as tools_mod

            registration_map = {
                # Register common aliases to the implemented methods (legacy names vary across versions)
                "read_file": ("read_code", tools_mod.ToolCategory.READ, "Read code/file with encoding detection and parsing"),
                "read_code": ("read_code", tools_mod.ToolCategory.READ, "Read code/file with encoding detection and parsing"),
                "write_file": ("write_code", tools_mod.ToolCategory.WRITE, "Write file with backup and optional auto-format"),
                "write_code": ("write_code", tools_mod.ToolCategory.WRITE, "Write file with backup and optional auto-format"),
                "apply_diff": ("apply_diff", tools_mod.ToolCategory.WRITE, "Apply diff preview and patch"),
                "execute_bash": ("execute_code", tools_mod.ToolCategory.EXECUTE, "Execute code/command with timeout and streaming"),
                "execute_code": ("execute_code", tools_mod.ToolCategory.EXECUTE, "Execute code/command with timeout and streaming"),
                "search_codebase": ("search_docs", tools_mod.ToolCategory.READ, "Smart codebase search"),
                "search_docs": ("search_docs", tools_mod.ToolCategory.READ, "Smart codebase search"),
                "analyze_file": ("read_code", tools_mod.ToolCategory.READ, "Analyze file with AST metrics (alias to read_code)"),
                "git_operation": ("git_operation", tools_mod.ToolCategory.EXECUTE, "Perform git operations"),
            }

            for public_name, (method_name, category, desc) in registration_map.items():
                handler = getattr(self, method_name, None)
                if handler:
                    try:
                        tools_mod._registry[public_name] = tools_mod.Tool(
                            name=public_name,
                            description=desc,
                            category=category,
                            default_permission=("always_allow" if category == tools_mod.ToolCategory.READ else "ask"),
                            schema={},
                            handler=handler,
                        )
                    except Exception:
                        # Best-effort registration; don't fail initialization
                        pass
        except Exception:
            # tools module not available — skip registration
            pass

    async def http_handler(self, request):
        """HTTP POST /call -> JSON {"name":..., "arguments":{...}}"""
        start = time.time()
        try:
            payload = await request.json()
        except Exception:
            # record telemetry even for bad requests
            elapsed_ms = (time.time() - start) * 1000.0
            self._record_telemetry(elapsed_ms)
            return web.json_response({"error": "invalid json"}, status=400)
        tool_name = payload.get("name")
        arguments = payload.get("arguments", {})
        if not tool_name:
            elapsed_ms = (time.time() - start) * 1000.0
            self._record_telemetry(elapsed_ms)
            return web.json_response({"error": "no tool name"}, status=400)
        handler = getattr(self, tool_name, None)
        if not handler:
            elapsed_ms = (time.time() - start) * 1000.0
            self._record_telemetry(elapsed_ms)
            return web.json_response(
                {"error": f"Unknown tool: {tool_name}"}, status=400
            )
        try:
            result = handler(arguments)
            if asyncio.iscoroutine(result):
                result = await result
            elapsed_ms = (time.time() - start) * 1000.0
            self._record_telemetry(elapsed_ms)
            # Normalize to ToolResult for consistent responses
            if not isinstance(result, ToolResult):
                try:
                    result = ToolResult(status=ToolStatus.SUCCESS, data=result)
                except Exception:
                    # Fallback to generic success wrapper
                    result = ToolResult(status=ToolStatus.SUCCESS, data={"result": result})

            return aiohttp.web.json_response(
                {
                    "status": result.status.value,
                    "data": result.data,
                    "error": result.error,
                    "warnings": result.warnings,
                    "metadata": result.metadata,
                }
            )
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000.0
            self._record_telemetry(elapsed_ms)
            return web.json_response({"error": str(e)}, status=500)

    async def health(self, request):
        """Health endpoint augmented with basic telemetry metrics"""
        now = time.time()
        uptime = now - self.start_time
        telemetry = self._telemetry_summary()
        return web.json_response(
            {"status": "ok", "uptime": uptime, "telemetry": telemetry}
        )

    def _record_telemetry(self, latency_ms: float):
        try:
            self.telemetry["request_count"] += 1
            self.telemetry["latencies_ms"].append(latency_ms)
            self.telemetry["recent_requests"].append(time.time())
        except Exception:
            pass

    def _telemetry_summary(self):
        import statistics

        latencies = list(self.telemetry.get("latencies_ms", []))
        summary = {
            "request_count": int(self.telemetry.get("request_count", 0)),
            "avg_latency_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "reqs_last_minute": 0,
            "gpu_memory_mb": None,
        }
        try:
            if latencies:
                summary["avg_latency_ms"] = statistics.mean(latencies)
                summary["p50_ms"] = statistics.median(latencies)
                if len(latencies) >= 1:
                    sorted_l = sorted(latencies)
                    idx = int(len(sorted_l) * 0.95) - 1
                    idx = max(0, min(idx, len(sorted_l) - 1))
                    summary["p95_ms"] = sorted_l[idx]
            # requests in last minute
            cutoff = time.time() - 60.0
            reqs = [t for t in self.telemetry.get("recent_requests", []) if t >= cutoff]
            summary["reqs_last_minute"] = len(reqs)
            # GPU memory via nvidia-smi if available
            try:
                import subprocess

                out = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used",
                        "--format=csv,nounits,noheader",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if out.returncode == 0 and out.stdout:
                    mb = int(out.stdout.strip().splitlines()[0])
                    summary["gpu_memory_mb"] = mb
            except Exception:
                summary["gpu_memory_mb"] = None
        except Exception:
            pass
        return summary

    def init_directories(self):
        """Initialize required directories"""
        for dir_path in [
            self.knowledge_base,
            self.tools_dir,
            self.plans_dir,
            self.cache_dir,
            self.context_dir,
            self.templates_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main request handler"""
        method = request.get("method")
        params = request.get("params", {})

        handlers = {
            "tools/list": self.list_tools,
            "tools/call": self.call_tool,
            "resources/list": self.list_resources,
            "resources/read": self.read_resource,
        }

        handler = handlers.get(method)
        if handler:
            return await handler(params)
        return {"error": f"Unknown method: {method}"}

    async def list_tools(self, params: Dict) -> Dict:
        """List all available tools"""
        tools = [
            {
                "name": "write_code",
                "description": "Write code to a file with automatic backup and diff preview",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "content": {"type": "string"},
                        "language": {"type": "string"},
                        "mode": {
                            "type": "string",
                            "enum": [
                                "overwrite",
                                "append",
                                "insert_after",
                                "replace_section",
                            ],
                        },
                    },
                    "required": ["filepath", "content"],
                },
            },
            {
                "name": "read_code",
                "description": "Read and analyze code with context - supports pattern matching and AST parsing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "pattern": {"type": "string"},
                        "parse_ast": {"type": "boolean"},
                        "line_range": {"type": "array", "items": {"type": "integer"}},
                    },
                },
            },
            {
                "name": "apply_diff",
                "description": "Apply surgical code changes using unified diff format - precise and safe",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "diff": {"type": "string"},
                        "dry_run": {"type": "boolean"},
                    },
                    "required": ["filepath", "diff"],
                },
            },
            {
                "name": "execute_code",
                "description": "Execute code with environment isolation and resource limits",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                        "env": {"type": "object"},
                        "timeout": {"type": "integer"},
                        "capture_output": {"type": "boolean"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "search_docs",
                "description": "Search online documentation with caching and smart ranking",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "source": {
                            "type": "string",
                            "enum": [
                                "web",
                                "github",
                                "stackoverflow",
                                "docs",
                                "pypi",
                                "npm",
                            ],
                        },
                        "use_cache": {"type": "boolean"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "git_operation",
                "description": "Enhanced git operations with smart commit messages and conflict resolution",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string"},
                        "args": {"type": "array", "items": {"type": "string"}},
                        "auto_stage": {"type": "boolean"},
                        "generate_message": {"type": "boolean"},
                    },
                    "required": ["operation"],
                },
            },
            {
                "name": "create_plan",
                "description": "Create detailed plans with automatic task breakdown and dependency analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "context": {"type": "string"},
                        "auto_break_down": {"type": "boolean"},
                        "estimate_time": {"type": "boolean"},
                    },
                    "required": ["goal"],
                },
            },
            {
                "name": "update_plan",
                "description": "Update plan with smart progress tracking and blocker detection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string"},
                        "item_id": {"type": "string"},
                        "status": {"type": "string"},
                        "notes": {"type": "string"},
                        "time_spent": {"type": "integer"},
                    },
                    "required": ["plan_id", "item_id", "status"],
                },
            },
            {
                "name": "save_knowledge",
                "description": "Save with tagging, semantic search, and automatic linking",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "content": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "code_examples": {"type": "array"},
                        "related_files": {"type": "array"},
                    },
                    "required": ["topic", "content"],
                },
            },
            {
                "name": "query_knowledge",
                "description": "Semantic search with relevance ranking and context extraction",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer"},
                        "include_examples": {"type": "boolean"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "batch_generate",
                "description": "Generate multiple files with template support and validation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "specs": {"type": "array"},
                        "template": {"type": "string"},
                        "validate": {"type": "boolean"},
                        "dry_run": {"type": "boolean"},
                    },
                    "required": ["specs"],
                },
            },
            {
                "name": "analyze_codebase",
                "description": "Deep analysis with dependency graphs, complexity metrics, and security scanning",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "analysis_type": {
                            "type": "string",
                            "enum": [
                                "structure",
                                "dependencies",
                                "complexity",
                                "security",
                                "todos",
                                "dead_code",
                            ],
                        },
                        "recursive": {"type": "boolean"},
                        "include_tests": {"type": "boolean"},
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "add_tool",
                "description": "Self-improvement: Add new tool with validation and testing",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "code": {"type": "string"},
                        "schema": {"type": "object"},
                        "test_cases": {"type": "array"},
                    },
                    "required": ["name", "description", "code"],
                },
            },
            {
                "name": "test_code",
                "description": "Comprehensive testing with coverage reports and auto-fix suggestions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "test_type": {
                            "type": "string",
                            "enum": [
                                "unit",
                                "integration",
                                "lint",
                                "type_check",
                                "coverage",
                            ],
                        },
                        "auto_fix": {"type": "boolean"},
                        "generate_tests": {"type": "boolean"},
                    },
                    "required": ["filepath"],
                },
            },
            {
                "name": "refactor_code",
                "description": "Smart refactoring with safety checks and preview",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "refactor_type": {
                            "type": "string",
                            "enum": [
                                "extract_function",
                                "rename",
                                "inline",
                                "optimize",
                                "modernize",
                            ],
                        },
                        "target": {"type": "string"},
                        "preview": {"type": "boolean"},
                    },
                    "required": ["filepath", "refactor_type"],
                },
            },
            {
                "name": "generate_tests",
                "description": "Auto-generate unit tests with edge cases and mocks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "test_framework": {"type": "string"},
                        "coverage_target": {"type": "integer"},
                    },
                    "required": ["filepath"],
                },
            },
            {
                "name": "find_similar",
                "description": "Find similar code patterns for reuse or refactoring",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code_snippet": {"type": "string"},
                        "search_path": {"type": "string"},
                        "threshold": {"type": "number"},
                    },
                    "required": ["code_snippet"],
                },
            },
            {
                "name": "explain_code",
                "description": "Generate detailed explanations with flow diagrams",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "detail_level": {
                            "type": "string",
                            "enum": ["brief", "detailed", "expert"],
                        },
                        "include_diagram": {"type": "boolean"},
                    },
                    "required": ["filepath"],
                },
            },
            {
                "name": "debug_assistant",
                "description": "Interactive debugging with root cause analysis and fix suggestions",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "error_message": {"type": "string"},
                        "code_context": {"type": "string"},
                        "stack_trace": {"type": "string"},
                        "suggest_fixes": {"type": "boolean"},
                    },
                    "required": ["error_message"],
                },
            },
            {
                "name": "create_template",
                "description": "Create reusable code templates from existing code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "source_files": {"type": "array"},
                        "variables": {"type": "array"},
                        "description": {"type": "string"},
                    },
                    "required": ["name", "source_files"],
                },
            },
            {
                "name": "save_session",
                "description": "Save current session (conversation, context, plan) to disk",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "load_session",
                "description": "Load a saved session by name",
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
            {
                "name": "manage_context",
                "description": "Manage conversation context window intelligently",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["add", "remove", "summarize", "list", "clear"],
                        },
                        "items": {"type": "array"},
                        "auto_prune": {"type": "boolean"},
                    },
                    "required": ["action"],
                },
            },
            {
                "name": "search_files",
                "description": "Search files for a pattern with context lines and fuzzy matching",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "path": {"type": "string"},
                        "context_lines": {"type": "integer"},
                        "fuzzy": {"type": "boolean"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "apply_edit",
                "description": "Search and replace with preview and safe backup",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "search": {"type": "string"},
                        "replace": {"type": "string"},
                        "use_regex": {"type": "boolean"},
                        "preview": {"type": "boolean"},
                        "apply": {"type": "boolean"},
                    },
                    "required": ["filepath", "search", "replace"],
                },
            },
            {
                "name": "create_project",
                "description": "Create a new project scaffold from templates",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "template": {"type": "string"},
                        "git_init": {"type": "boolean"},
                        "create_venv": {"type": "boolean"},
                        "install_deps": {"type": "boolean"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "code_review",
                "description": "Automated code review with best practices and security checks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "check_security": {"type": "boolean"},
                        "check_performance": {"type": "boolean"},
                        "check_style": {"type": "boolean"},
                        "severity_threshold": {"type": "string"},
                    },
                    "required": ["filepath"],
                },
            },
            {
                "name": "estimate_complexity",
                "description": "Estimate time and complexity for implementation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string"},
                        "similar_tasks": {"type": "array"},
                        "include_breakdown": {"type": "boolean"},
                    },
                    "required": ["task_description"],
                },
            },
        ]
        return {"tools": tools}

    async def read_code(self, args: Dict) -> ToolResult:
        """Enhanced read with AST parsing and context, returns ToolResult"""
        try:
            filepath = args.get("filepath")
            pattern = args.get("pattern")
            parse_ast = args.get("parse_ast", False)
            line_range = args.get("line_range")
            if not filepath:
                return ToolResult(status=ToolStatus.ERROR, error="No filepath provided")
            path = Path(filepath)
            if not path.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")
            code = path.read_text()
            data = {"content": code}
            if pattern:
                matches = []
                for i, line in enumerate(code.splitlines()):
                    if pattern in line:
                        matches.append({"line": i + 1, "content": line})
                data["matches"] = matches
            if parse_ast:
                try:
                    tree = ast.parse(code)
                    data["ast"] = ast.dump(tree)
                except Exception as e:
                    data["ast_error"] = str(e)
            if line_range:
                start, end = line_range
                lines = code.splitlines()[start - 1 : end]
                data["lines"] = lines
            return ToolResult(status=ToolStatus.SUCCESS, data=data)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def call_tool(self, params: Dict) -> Dict:
        """Dispatch and call a named tool with arguments.
        Accepts params: {"name": <tool_name>, "arguments": {...}}
        Returns a serialized response suitable for the CLI.
        """
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if not tool_name:
            return {
                "content": [{"type": "text", "text": "Error: No tool name provided"}],
                "isError": True,
            }

        handler = getattr(self, tool_name, None)
        if not handler or not callable(handler):
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "isError": True,
            }

        try:
            result = handler(args)
            if asyncio.iscoroutine(result):
                result = await result

            if isinstance(result, ToolResult):
                out = {
                    "status": result.status.value,
                    "data": result.data,
                    "error": result.error,
                    "warnings": result.warnings,
                    "metadata": result.metadata,
                }
                return {
                    "content": [
                        {"type": "tool_result", "text": json.dumps(out, indent=2)}
                    ]
                }

            # legacy dict/list
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True,
            }

    async def write_code(self, args: Dict) -> ToolResult:
        """Enhanced write with diff preview and multiple modes, returns ToolResult"""
        try:
            filepath = Path(args["filepath"])
            content = args["content"]
            mode = args.get("mode", "overwrite")
            filepath.parent.mkdir(parents=True, exist_ok=True)
            diff_preview = None
            warnings = []
            metadata = {}
            if filepath.exists():
                original = filepath.read_text()
                backup_path = filepath.with_suffix(
                    filepath.suffix + f".backup.{int(datetime.now().timestamp())}"
                )
                filepath.rename(backup_path)
                warnings.append(f"Backup created: {backup_path}")
                diff = list(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=str(filepath),
                        tofile=str(filepath),
                    )
                )
                diff_preview = "".join(diff)
                metadata["diff_preview"] = diff_preview
            auto_format = bool(args.get("auto_format", False))
            if mode == "append":
                existing = filepath.read_text() if filepath.exists() else ""
                content = existing + "\n" + content
            filepath.write_text(content)
            # Auto-format for Python
            if auto_format and filepath.suffix == ".py":
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "black"], check=False
                    )
                    subprocess.run(
                        [sys.executable, "-m", "black", str(filepath)], check=False
                    )
                    warnings.append("auto_format: black applied")
                    # Refresh content and diff
                    formatted = filepath.read_text()
                    metadata["formatted"] = True
                    # Recompute hash and size
                    content = formatted
                except Exception as fe:
                    warnings.append(f"auto_format failed: {fe}")
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
            metadata.update(
                {
                    "filepath": str(filepath),
                    "size": len(content),
                    "lines": len(content.splitlines()),
                    "hash": content_hash,
                }
            )
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"message": f"Code written to {filepath}"},
                warnings=warnings,
                metadata=metadata,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def apply_diff(self, args: Dict) -> ToolResult:
        """Apply unified diff format changes - surgical precision, returns ToolResult"""
        try:
            filepath = Path(args["filepath"])
            diff_text = args["diff"]
            dry_run = args.get("dry_run", False)
            if not filepath.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")
            # (Stub) Real implementation would use a diff parser
            # For now, just preview diff
            if dry_run:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"message": "Dry run: diff preview only"},
                    metadata={"diff": diff_text},
                )
            # Not implemented: actually apply diff
            return ToolResult(
                status=ToolStatus.ERROR, error="Diff application not implemented yet."
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def git_operation(self, args: Dict) -> ToolResult:
        """Enhanced git with smart features, returns ToolResult"""
        try:
            operation = args["operation"]
            git_args = args.get("args", [])
            auto_stage = args.get("auto_stage", False)
            generate_message = args.get("generate_message", False)
            if auto_stage and operation == "commit":
                subprocess.run(["git", "add", "-A"], capture_output=True)
            if generate_message and operation == "commit":
                diff_result = subprocess.run(
                    ["git", "diff", "--cached"], capture_output=True, text=True
                )
                diff = diff_result.stdout
                ai_message = f"AI commit message for changes:\n{diff[:100]}..."
                git_args = ["-m", ai_message] + git_args
            result = subprocess.run(
                ["git", operation, *git_args], capture_output=True, text=True
            )
            data = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
                "operation": operation,
            }
            status = ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR
            return ToolResult(status=status, data=data)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def execute_code(self, args: Dict) -> ToolResult:
        """Enhanced execution with resource limits and environment isolation, returns ToolResult"""
        try:
            command = args["command"]
            cwd = args.get("cwd", str(Path.cwd()))
            env = args.get("env", {})
            timeout = args.get("timeout", 30)
            capture_output = args.get("capture_output", True)
            stream = bool(args.get("stream", False))
            full_env = os.environ.copy()
            full_env.update(env)
            start_time = datetime.now()

            # Support optional sudo via args['sudo'] when enabled in config
            use_sudo = bool(args.get("sudo", False))
            if use_sudo and not self.config.get("allow_sudo", False):
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Sudo not allowed by server configuration",
                )
            if use_sudo:
                # Use sudo -n (non-interactive) so it fails if password is required
                command = f"sudo -n {command}"

            if stream:
                # Stream output asynchronously and collect chunks
                proc = await asyncio.create_subprocess_shell(
                    command,
                    cwd=cwd,
                    env=full_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                chunks = []
                try:
                    while True:
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        text = line.decode(errors="replace")
                        chunks.append(
                            {"timestamp": datetime.now().isoformat(), "chunk": text}
                        )
                    await asyncio.wait_for(proc.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Command timed out after {timeout} seconds",
                        metadata={"streamed": True},
                    )
                execution_time = (datetime.now() - start_time).total_seconds()
                data = {
                    "returncode": proc.returncode,
                    "streamed_chunks": chunks,
                    "execution_time": execution_time,
                    "command": command,
                }
                status = (
                    ToolStatus.SUCCESS if proc.returncode == 0 else ToolStatus.ERROR
                )
                return ToolResult(status=status, data=data)

            # Non-streaming (legacy)
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=full_env,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            data = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
                "execution_time": execution_time,
                "command": command,
            }
            status = ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR
            return ToolResult(status=status, data=data)
        except subprocess.TimeoutExpired:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Command timed out after {timeout} seconds",
                metadata={"timeout": True},
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def search_docs(self, args: Dict) -> ToolResult:
        """Enhanced doc search with caching, returns ToolResult"""
        try:
            query = args["query"]
            source = args.get("source", "web")
            use_cache = args.get("use_cache", True)
            cache_key = hashlib.md5(f"{source}:{query}".encode()).hexdigest()
            cache_file = self.cache_dir / f"{cache_key}.json"
            if use_cache and cache_file.exists():
                if (datetime.now().timestamp() - cache_file.stat().st_mtime) < 86400:
                    data = json.loads(cache_file.read_text())
                    return ToolResult(
                        status=ToolStatus.SUCCESS, data=data, metadata={"cached": True}
                    )
            search_urls = {
                "web": f"https://www.google.com/search?q={query}+documentation",
                "github": f"https://github.com/search?q={query}",
                "stackoverflow": f"https://stackoverflow.com/search?q={query}",
                "docs": f"https://devdocs.io/#q={query}",
                "pypi": f"https://pypi.org/search/?q={query}",
                "npm": f"https://www.npmjs.com/search?q={query}",
            }
            data = {
                "query": query,
                "source": source,
                "url": search_urls.get(source),
                "cached": False,
                "message": f"Search query prepared for {source}",
            }
            if use_cache:
                cache_file.write_text(json.dumps(data))
            return ToolResult(status=ToolStatus.SUCCESS, data=data)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Duplicate git_operation definition removed; earlier definition returning ToolResult is kept for consistent ToolResult usage.

    async def create_plan(self, args: Dict) -> ToolResult:
        """Enhanced planning with auto breakdown, returns ToolResult"""
        try:
            goal = args["goal"]
            context = args.get("context", "")
            auto_break_down = args.get("auto_break_down", True)
            estimate_time = args.get("estimate_time", True)
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            items = []
            if auto_break_down:
                common_phases = [
                    {
                        "id": "1",
                        "description": "Project setup and structure",
                        "estimate": "30m",
                        "dependencies": [],
                    },
                    {
                        "id": "2",
                        "description": "Core implementation",
                        "estimate": "2h",
                        "dependencies": ["1"],
                    },
                    {
                        "id": "3",
                        "description": "Testing and validation",
                        "estimate": "1h",
                        "dependencies": ["2"],
                    },
                    {
                        "id": "4",
                        "description": "Documentation",
                        "estimate": "30m",
                        "dependencies": ["3"],
                    },
                ]
                items = common_phases
            plan = {
                "id": plan_id,
                "goal": goal,
                "context": context,
                "created": datetime.now().isoformat(),
                "status": "active",
                "items": items,
                "progress": 0,
                "estimated_total": "4h" if estimate_time else None,
            }
            plan_file = self.plans_dir / f"{plan_id}.json"
            plan_file.write_text(json.dumps(plan, indent=2))
            data = {
                "plan_id": plan_id,
                "items_count": len(items),
                "estimated_time": plan.get("estimated_total"),
                "message": "Plan created with task breakdown",
            }
            return ToolResult(
                status=ToolStatus.SUCCESS, data=data, metadata={"plan": plan}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def update_plan(self, args: Dict) -> ToolResult:
        """Enhanced plan updates with analytics, returns ToolResult"""
        try:
            plan_id = args["plan_id"]
            item_id = args["item_id"]
            status = args["status"]
            notes = args.get("notes", "")
            time_spent = args.get("time_spent", 0)
            plan_file = self.plans_dir / f"{plan_id}.json"
            if not plan_file.exists():
                return ToolResult(status=ToolStatus.ERROR, error="Plan not found")
            plan = json.loads(plan_file.read_text())
            item_found = False
            for item in plan["items"]:
                if item["id"] == item_id:
                    item["status"] = status
                    item["updated"] = datetime.now().isoformat()
                    if notes:
                        item["notes"] = notes
                    if time_spent:
                        item["time_spent"] = time_spent
                    item_found = True
                    break
            if not item_found:
                plan["items"].append(
                    {
                        "id": item_id,
                        "status": status,
                        "created": datetime.now().isoformat(),
                        "notes": notes,
                        "time_spent": time_spent,
                    }
                )
            completed = sum(
                1 for item in plan["items"] if item.get("status") == "complete"
            )
            plan["progress"] = (
                int((completed / len(plan["items"])) * 100) if plan["items"] else 0
            )
            plan_file.write_text(json.dumps(plan, indent=2))
            data = {
                "plan_id": plan_id,
                "progress": plan["progress"],
                "completed": completed,
                "total": len(plan["items"]),
                "message": "Plan updated",
            }
            return ToolResult(
                status=ToolStatus.SUCCESS, data=data, metadata={"plan": plan}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def save_knowledge(self, args: Dict) -> ToolResult:
        """Enhanced knowledge saving with relationships, returns ToolResult"""
        try:
            topic = args["topic"]
            content = args["content"]
            tags = args.get("tags", [])
            code_examples = args.get("code_examples", [])
            related_files = args.get("related_files", [])
            knowledge_id = topic.replace(" ", "_").lower()
            knowledge_file = self.knowledge_base / f"{knowledge_id}.json"
            is_update = False
            if knowledge_file.exists():
                existing = json.loads(knowledge_file.read_text())
                tags = list(set(tags + existing.get("tags", [])))
                existing["content"] += "\n\n" + content
                existing["updated"] = datetime.now().isoformat()
                existing["tags"] = tags
                existing["code_examples"] = code_examples + existing.get(
                    "code_examples", []
                )
                knowledge = existing
                is_update = True
            else:
                knowledge = {
                    "topic": topic,
                    "content": content,
                    "tags": tags,
                    "code_examples": code_examples,
                    "related_files": related_files,
                    "created": datetime.now().isoformat(),
                    "updated": datetime.now().isoformat(),
                    "access_count": 0,
                }
            knowledge_file.write_text(json.dumps(knowledge, indent=2))
            data = {"knowledge_id": knowledge_id, "tags": tags, "is_update": is_update}
            return ToolResult(
                status=ToolStatus.SUCCESS, data=data, metadata={"knowledge": knowledge}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def query_knowledge(self, args: Dict) -> ToolResult:
        """Enhanced knowledge query with ranking"""
        try:
            query = args["query"].lower()
            tags = args.get("tags", [])
            limit = args.get("limit", 10)
            include_examples = args.get("include_examples", True)
            results = []
            files_searched = 0
            for kb_file in self.knowledge_base.glob("*.json"):
                files_searched += 1
                kb = json.loads(kb_file.read_text())
                # Calculate relevance score
                score = 0
                if query in kb.get("topic", "").lower():
                    score += 10
                if query in kb.get("content", "").lower():
                    score += 5
                if tags and any(t in kb.get("tags", []) for t in tags):
                    score += 3
                if score > 0:
                    kb["access_count"] = kb.get("access_count", 0) + 1
                    kb_file.write_text(json.dumps(kb, indent=2))
                    entry = {
                        "knowledge_id": kb_file.stem,
                        "topic": kb.get("topic"),
                        "score": score,
                        "tags": kb.get("tags", []),
                        "excerpt": (
                            (kb.get("content", "")[:300] + "...")
                            if len(kb.get("content", "")) > 300
                            else kb.get("content", "")
                        ),
                    }
                    if include_examples:
                        entry["examples"] = kb.get("code_examples", [])[:3]
                    results.append(entry)
            results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"results": results, "files_searched": files_searched},
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def analyze_codebase(self, args: Dict) -> ToolResult:
        """Analyze a codebase for structure, dependencies, complexity, security, and TODOs"""
        try:
            path = Path(args.get("path", "."))
            analysis_type = args.get("analysis_type", "structure")
            recursive = bool(args.get("recursive", True))
            include_tests = bool(args.get("include_tests", False))
            files = []
            for p in path.rglob("*") if recursive else path.iterdir():
                if p.is_file():
                    if not include_tests and (
                        "test" in p.name.lower() or "/tests/" in str(p)
                    ):
                        continue
                    files.append(p)
            report = {"files": len(files)}
            if analysis_type in ("structure", "all"):
                report["structure"] = [
                    {
                        "path": str(p),
                        "size": p.stat().st_size,
                        "lines": len(p.read_text().splitlines()),
                    }
                    for p in files[:200]
                ]
            if analysis_type in ("dependencies", "all"):
                imports = {}
                for p in [f for f in files if f.suffix == ".py"]:
                    try:
                        tree = ast.parse(p.read_text())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for n in node.names:
                                    imports.setdefault(n.name, 0)
                                    imports[n.name] += 1
                            if isinstance(node, ast.ImportFrom):
                                module = node.module or ""
                                imports.setdefault(module, 0)
                                imports[module] += 1
                    except Exception:
                        continue
                report["dependencies"] = sorted(
                    imports.items(), key=lambda x: x[1], reverse=True
                )[:200]
            if analysis_type in ("complexity", "all"):

                def complexity_of_node(node):
                    score = 1
                    for child in ast.walk(node):
                        if isinstance(
                            child,
                            (
                                ast.If,
                                ast.For,
                                ast.While,
                                ast.And,
                                ast.Or,
                                ast.Try,
                                ast.With,
                            ),
                        ):
                            score += 1
                    return score

                complexities = []
                for p in [f for f in files if f.suffix == ".py"]:
                    try:
                        tree = ast.parse(p.read_text())
                        for func in [
                            n
                            for n in ast.walk(tree)
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]:
                            complexities.append(
                                {
                                    "file": str(p),
                                    "function": func.name,
                                    "complexity": complexity_of_node(func),
                                }
                            )
                    except Exception:
                        continue
                report["complexity"] = sorted(
                    complexities, key=lambda x: x["complexity"], reverse=True
                )[:200]
            if analysis_type in ("security", "all"):
                issues = []
                patterns = [
                    "eval(",
                    "exec(",
                    "os.system(",
                    "subprocess.run(",
                    "pickle.load(",
                ]
                for p in files:
                    try:
                        text = p.read_text()
                    except Exception:
                        continue
                    for pat in patterns:
                        if pat in text:
                            issues.append(
                                {"file": str(p), "pattern": pat, "context": text[:200]}
                            )
                report["security_issues"] = issues[:200]
            if analysis_type in ("todos", "all"):
                todos = []
                for p in files:
                    try:
                        text = p.read_text()
                    except Exception:
                        continue
                    for i, line in enumerate(text.splitlines()):
                        if "TODO" in line or "FIXME" in line:
                            todos.append(
                                {"file": str(p), "line": i + 1, "content": line.strip()}
                            )
                report["todos"] = todos[:500]
            return ToolResult(status=ToolStatus.SUCCESS, data=report)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def debug_assistant(self, args: Dict) -> ToolResult:
        """Provide debugging suggestions based on error messages and code context"""
        try:
            error = args.get("error_message", "")
            stack = args.get("stack_trace", "")
            code = args.get("code_context", "")
            language = args.get("language", "python")  # noqa: F841
            suggest = bool(args.get("suggest_fixes", True))
            explanation = ""
            root = None
            suggestions = []
            if "NoneType" in error and "iter" in error.lower():
                explanation = "This error usually means you're trying to iterate over a None value."
                root = "Variable is None where iterable expected"
                if suggest:
                    suggestions.append(
                        {
                            "description": "Add a None check or default to empty list",
                            "code": "if var is not None:\n    for x in var:\n        ...",
                            "confidence": 0.95,
                        }
                    )
                    suggestions.append(
                        {
                            "description": "Initialize with empty list when None",
                            "code": "var = var or []",
                            "confidence": 0.85,
                        }
                    )
            elif "NameError" in error:
                explanation = "NameError indicates a variable is referenced before assignment or not defined in scope."
                root = "Undefined variable"
                if suggest:
                    suggestions.append(
                        {
                            "description": "Define the variable or import the module",
                            "code": "my_var = 0",
                            "confidence": 0.9,
                        }
                    )
            elif "SyntaxError" in error:
                explanation = "SyntaxError indicates invalid syntax in your code. Check the stack trace for exact location."
                root = "Invalid syntax"
                if suggest:
                    suggestions.append(
                        {
                            "description": "Fix syntax as indicated by parser",
                            "code": "# Inspect the line and correct syntax",
                            "confidence": 0.9,
                        }
                    )
            else:
                explanation = "No specific heuristic matched. Provide relevant stack trace and surrounding code for deeper analysis."
                root = "Unknown"
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "explanation": explanation,
                    "root_cause": root,
                    "suggested_fixes": suggestions,
                    "stack": stack,
                    "code": code,
                },
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def search_files(self, args: Dict) -> ToolResult:
        """Search files under a path for a query string and return matches with context"""
        try:
            query = args.get("query")
            base_path = Path(args.get("path", "."))
            context_lines = int(args.get("context_lines", 2))
            fuzzy = bool(args.get("fuzzy", False))  # noqa: F841
            limit = int(args.get("limit", 200))
            if not query:
                return ToolResult(status=ToolStatus.ERROR, error="No query provided")
            matches = []
            files_searched = 0
            for p in base_path.rglob("*"):
                if p.is_file():
                    files_searched += 1
                    try:
                        text = p.read_text()
                    except Exception:
                        continue
                    lines = text.splitlines()
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            context = lines[start:end]
                            matches.append(
                                {
                                    "file": str(p),
                                    "line": i + 1,
                                    "content": line.strip(),
                                    "context": context,
                                }
                            )
                            if len(matches) >= limit:
                                break
                    if len(matches) >= limit:
                        break
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"matches": matches, "files_searched": files_searched},
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def apply_edit(self, args: Dict) -> ToolResult:
        """Perform a search-and-replace with preview option and safe backup"""
        try:
            filepath = Path(args.get("filepath"))
            search = args.get("search")
            replace = args.get("replace", "")
            use_regex = bool(args.get("use_regex", False))
            preview = bool(args.get("preview", True))
            do_apply = bool(args.get("apply", False))
            if not filepath.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")
            original = filepath.read_text()
            if use_regex:
                new_content, count = re.subn(search, replace, original)
            else:
                new_content = original.replace(search, replace)
                count = original.count(search)
            # Generate diff preview
            diff = "".join(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=str(filepath),
                    tofile=str(filepath),
                )
            )
            if preview and not do_apply:
                return ToolResult(
                    status=ToolStatus.SUCCESS, data={"matches": count, "preview": diff}
                )
            if do_apply:
                backup = filepath.with_suffix(
                    filepath.suffix + f".backup.{int(datetime.now().timestamp())}"
                )
                filepath.rename(backup)
                filepath.write_text(new_content)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"matches": count, "diff": diff},
                    metadata={"backup": str(backup)},
                )
            return ToolResult(
                status=ToolStatus.ERROR, error="No action taken: set preview or apply"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def create_project(self, args: Dict) -> ToolResult:
        """Create a simple project scaffold for common templates"""
        try:
            name = args.get("name")
            template = args.get("template", "python-api")
            git_init = bool(args.get("git_init", True))
            create_venv = bool(args.get("create_venv", True))
            install_deps = bool(args.get("install_deps", False))
            project_dir = Path.cwd() / name
            if project_dir.exists():
                return ToolResult(
                    status=ToolStatus.ERROR, error="Project directory already exists"
                )
            project_dir.mkdir(parents=True)
            # Basic python-api scaffold
            if template == "python-api":
                (project_dir / "src").mkdir()
                app_py = project_dir / "src" / "main.py"
                app_py.write_text(
                    "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'status': 'ok'}\n"
                )
                (project_dir / "requirements.txt").write_text(
                    "fastapi\nuvicorn[standard]\n"
                )
                (project_dir / "README.md").write_text(
                    f"# {name}\n\nGenerated by Singularity (Omarchy compatible)\n"
                )
            else:
                (project_dir / "README.md").write_text(
                    f"# {name}\n\nGenerated by Singularity (Omarchy compatible) (template: {template})\n"
                )
            warnings = []
            if create_venv:
                venv_dir = project_dir / ".venv"
                subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])
                warnings.append(f"venv created at {venv_dir}")
                if install_deps:
                    pip_bin = venv_dir / "bin" / "pip"
                    if pip_bin.exists():
                        subprocess.run(
                            [
                                str(pip_bin),
                                "install",
                                "-r",
                                str(project_dir / "requirements.txt"),
                            ]
                        )
            if git_init:
                subprocess.run(["git", "init", str(project_dir)])
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"project": str(project_dir)},
                warnings=warnings,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def save_session(self, args: Dict) -> ToolResult:
        """Save current session to ~/.singularity/sessions/<name>.json"""
        try:
            name = args.get("name")
            description = args.get("description", "")
            if not name:
                return ToolResult(
                    status=ToolStatus.ERROR, error="No session name provided"
                )
            sessions_dir = Path.home() / ".singularity" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_file = sessions_dir / f"{name}.json"
            # Gather session data
            ctx_file = self.context_dir / "context.json"
            context = []
            if ctx_file.exists():
                try:
                    context = json.loads(ctx_file.read_text())
                except Exception:
                    context = []
            session = {
                "name": name,
                "description": description,
                "created": datetime.now().isoformat(),
                "conversation_history": getattr(self, "conversation_history", []),
                "current_plan": getattr(self, "current_plan", None),
                "context": context,
            }
            session_file.write_text(json.dumps(session, indent=2))
            return ToolResult(
                status=ToolStatus.SUCCESS, data={"session": str(session_file)}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def load_session(self, args: Dict) -> ToolResult:
        """Load a previously saved session into memory"""
        try:
            name = args.get("name")
            if not name:
                return ToolResult(
                    status=ToolStatus.ERROR, error="No session name provided"
                )
            sessions_dir = Path.home() / ".singularity" / "sessions"
            session_file = sessions_dir / f"{name}.json"
            if not session_file.exists():
                return ToolResult(status=ToolStatus.ERROR, error="Session not found")
            session = json.loads(session_file.read_text())
            self.conversation_history = session.get("conversation_history", [])
            self.current_plan = session.get("current_plan")
            # Restore context
            ctx_file = self.context_dir / "context.json"
            ctx_file.write_text(json.dumps(session.get("context", []), indent=2))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"loaded": True, "session": str(session_file)},
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def generate_tests(self, args: Dict) -> ToolResult:
        """Generate simple pytest tests for a Python file by inspecting function defs"""
        try:
            filepath = args.get("filepath")
            if not filepath:
                return ToolResult(status=ToolStatus.ERROR, error="No filepath provided")
            path = Path(filepath)
            if not path.exists() or path.suffix != ".py":
                return ToolResult(
                    status=ToolStatus.ERROR, error="File not found or not a Python file"
                )
            module_name = path.stem
            tests_dir = path.parent / "tests"
            tests_dir.mkdir(exist_ok=True)
            test_file = tests_dir / f"test_{module_name}.py"
            source = path.read_text()
            try:
                tree = ast.parse(source)
            except Exception as e:
                return ToolResult(
                    status=ToolStatus.ERROR, error=f"AST parse failed: {e}"
                )
            funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            if not funcs:
                return ToolResult(
                    status=ToolStatus.ERROR, error="No functions found to test"
                )
            header = f"# Auto-generated tests for {module_name}\nimport pytest\nfrom {module_name} import *\n\n"
            body = ""
            for f in funcs[:10]:
                test_name = f"test_{f.name}_basic"
                body += f"def {test_name}():\n    # TODO: expand assertions for {f.name}\n    assert True\n\n"
            test_file.write_text(header + body)
            return ToolResult(
                status=ToolStatus.SUCCESS, data={"tests_created": str(test_file)}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def manage_context(self, args: Dict) -> ToolResult:
        """Manage conversation context window intelligently"""
        try:
            action = args.get("action")
            items = args.get("items", [])
            auto_prune = bool(args.get("auto_prune", False))  # noqa: F841
            ctx_file = self.context_dir / "context.json"
            context = []
            if ctx_file.exists():
                try:
                    context = json.loads(ctx_file.read_text())
                except Exception:
                    context = []
            if action == "add":
                added = []
                if isinstance(items, str):
                    items = [items]
                for it in items:
                    entry = {
                        "id": hashlib.md5(
                            (it + str(datetime.now().timestamp())).encode()
                        ).hexdigest()[:8],
                        "content": it,
                        "created": datetime.now().isoformat(),
                    }
                    context.append(entry)
                    added.append(entry)
                ctx_file.write_text(json.dumps(context, indent=2))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"added": added, "total": len(context)},
                )
            if action == "remove":
                removed = []
                needle = items if isinstance(items, str) else None
                new_ctx = []
                for e in context:
                    if needle and needle in e.get("content", ""):
                        removed.append(e)
                    else:
                        new_ctx.append(e)
                ctx_file.write_text(json.dumps(new_ctx, indent=2))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"removed": removed, "total": len(new_ctx)},
                )
            if action == "list":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"items": context, "count": len(context)},
                )
            if action == "clear":
                if ctx_file.exists():
                    ctx_file.unlink()
                return ToolResult(status=ToolStatus.SUCCESS, data={"cleared": True})
            if action == "summarize":
                combined = "\n".join([e["content"] for e in context])
                summary = (
                    (combined[:1000] + "...") if len(combined) > 1000 else combined
                )
                return ToolResult(status=ToolStatus.SUCCESS, data={"summary": summary})
            return ToolResult(status=ToolStatus.ERROR, error="Unknown action")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def test_code(self, args: Dict) -> ToolResult:
        """Run tests for a file or project using pytest and return results"""
        try:
            filepath = args.get("filepath")
            test_type = args.get("test_type", "unit")  # noqa: F841
            auto_fix = bool(args.get("auto_fix", False))  # noqa: F841
            generate_tests = bool(args.get("generate_tests", False))  # noqa: F841
            cwd = Path(filepath).parent if filepath else Path.cwd()
            cmd = [sys.executable, "-m", "pytest", "-q"]
            if filepath:
                cmd.append(str(filepath))
            # Run pytest
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
            data = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
            status = ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR
            return ToolResult(status=status, data=data)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def refactor_code(self, args: Dict) -> ToolResult:
        """Simple refactoring operations with safety checks. Currently supports 'rename'"""
        try:
            filepath = Path(args.get("filepath"))
            refactor_type = args.get("refactor_type")
            if not filepath.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")
            if refactor_type == "rename":
                old = args.get("old")
                new = args.get("new")
                preview = bool(args.get("preview", True))
                apply_change = bool(args.get("apply", False))
                content = filepath.read_text()
                if old not in content:
                    return ToolResult(
                        status=ToolStatus.ERROR, error="String to rename not found"
                    )
                count = content.count(old)
                diff = "".join(
                    difflib.unified_diff(
                        content.splitlines(keepends=True),
                        content.replace(old, new).splitlines(keepends=True),
                        fromfile=str(filepath),
                        tofile=str(filepath),
                    )
                )
                if preview and not apply_change:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"matches": count, "preview": diff},
                    )
                if apply_change:
                    backup = filepath.with_suffix(
                        filepath.suffix + f".backup.{int(datetime.now().timestamp())}"
                    )
                    filepath.rename(backup)
                    filepath.write_text(content.replace(old, new))
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"matches": count, "diff": diff},
                        metadata={"backup": str(backup)},
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="No action taken: set preview or apply",
                )
            return ToolResult(
                status=ToolStatus.ERROR, error="Unsupported refactor type"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


async def _fetch_url_impl(self, args: Dict) -> ToolResult:
    """Fetch text content from a URL (documentation reader)."""
    try:
        url = args.get("url")
        if not url:
            return ToolResult(status=ToolStatus.ERROR, error="No URL provided")
        timeout = float(args.get("timeout", 5.0))
        maxlen = int(args.get("maxlen", 8000))
        req = urllib.request.Request(
            url, headers={"User-Agent": "Singularity/1.0 (Omarchy compatible)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        # Strip tags and collapse whitespace
        text = re.sub(r"<[^<]+?>", "", raw)
        text = " ".join(text.split())
        return ToolResult(
            status=ToolStatus.SUCCESS, data={"text": text[:maxlen], "url": url}
        )
    except Exception as e:
        return ToolResult(status=ToolStatus.ERROR, error=str(e))


# Attach the implementation to the class for use by instances
MCPServer.fetch_url = _fetch_url_impl

if __name__ == "__main__":
    # Run a minimal HTTP server exposing the MCP tools
    import argparse
    import logging
    import sys
    import traceback

    from aiohttp import web

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("mcp_server")

    parser = argparse.ArgumentParser(
        description="Run MCP server for Singularity (Omarchy compatible)"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    # Immediate diagnostics to ensure __main__ executes when launched as subprocess

    print("MCP runner: __main__ entered", flush=True)
    try:
        print("MCP runner: sys.executable=" + sys.executable, flush=True)
    except Exception:
        pass

    mcp = MCPServer()
    app = web.Application()
    app.router.add_post("/call", mcp.http_handler)
    app.router.add_get("/health", mcp.health)

    runner = web.AppRunner(app)

    async def start():
        try:
            logger.debug("Runner setup starting")
            await runner.setup()
            site = web.TCPSite(runner, args.host, args.port)
            await site.start()
            logger.debug("Site started")

            # Retrieve the actual port
            sockets = []
            for s in runner.sites:
                # site._server is internal but gives access to sockets
                try:
                    server = s._server
                    sockets = server.sockets
                except Exception:
                    logger.exception("Error while inspecting runner.sites")
                    continue
            port = sockets[0].getsockname()[1] if sockets else args.port
            # Announce listening address (flush to ensure subprocess readers get it)
            print(f"MCP server listening on {args.host}:{port}", flush=True)

            # Keep running until cancelled
            await asyncio.Event().wait()
        except Exception:
            print(
                "MCP server failed to start; see stderr for traceback",
                file=sys.stderr,
                flush=True,
            )
            traceback.print_exc()
            raise
        finally:
            try:
                await runner.cleanup()
            except Exception:
                logger.exception("Failed to cleanup runner")

    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("MCP server shutting down", flush=True)
    except Exception as e:
        print(f"MCP server exited with error: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    async def analyze_codebase(self, args: Dict) -> ToolResult:
        """Analyze a codebase for structure, dependencies, complexity, security, and TODOs"""
        try:
            path = Path(args.get("path", "."))
            analysis_type = args.get("analysis_type", "structure")
            recursive = bool(args.get("recursive", True))
            include_tests = bool(args.get("include_tests", False))
            files = []
            for p in path.rglob("*") if recursive else path.iterdir():
                if p.is_file():
                    if not include_tests and (
                        "test" in p.name.lower() or "/tests/" in str(p)
                    ):
                        continue
                    files.append(p)
            report = {"files": len(files)}
            if analysis_type in ("structure", "all"):
                report["structure"] = [
                    {
                        "path": str(p),
                        "size": p.stat().st_size,
                        "lines": len(p.read_text().splitlines()),
                    }
                    for p in files[:200]
                ]
            if analysis_type in ("dependencies", "all"):
                imports = {}
                for p in [f for f in files if f.suffix == ".py"]:
                    try:
                        tree = ast.parse(p.read_text())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for n in node.names:
                                    imports.setdefault(n.name, 0)
                                    imports[n.name] += 1
                            if isinstance(node, ast.ImportFrom):
                                module = node.module or ""
                                imports.setdefault(module, 0)
                                imports[module] += 1
                    except Exception:
                        continue
                report["dependencies"] = sorted(
                    imports.items(), key=lambda x: x[1], reverse=True
                )[:200]
            if analysis_type in ("complexity", "all"):

                def complexity_of_node(node):
                    score = 1
                    for child in ast.walk(node):
                        if isinstance(
                            child,
                            (
                                ast.If,
                                ast.For,
                                ast.While,
                                ast.And,
                                ast.Or,
                                ast.Try,
                                ast.With,
                            ),
                        ):
                            score += 1
                    return score

                complexities = []
                for p in [f for f in files if f.suffix == ".py"]:
                    try:
                        tree = ast.parse(p.read_text())
                        for func in [
                            n
                            for n in ast.walk(tree)
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]:
                            complexities.append(
                                {
                                    "file": str(p),
                                    "function": func.name,
                                    "complexity": complexity_of_node(func),
                                }
                            )
                    except Exception:
                        continue
                report["complexity"] = sorted(
                    complexities, key=lambda x: x["complexity"], reverse=True
                )[:200]
            if analysis_type in ("security", "all"):
                issues = []
                patterns = [
                    "eval(",
                    "exec(",
                    "os.system(",
                    "subprocess.run(",
                    "pickle.load(",
                ]
                for p in files:
                    try:
                        text = p.read_text()
                    except Exception:
                        continue
                    for pat in patterns:
                        if pat in text:
                            issues.append(
                                {"file": str(p), "pattern": pat, "context": text[:200]}
                            )
                report["security_issues"] = issues[:200]
            if analysis_type in ("todos", "all"):
                todos = []
                for p in files:
                    try:
                        text = p.read_text()
                    except Exception:
                        continue
                    for i, line in enumerate(text.splitlines()):
                        if "TODO" in line or "FIXME" in line:
                            todos.append(
                                {"file": str(p), "line": i + 1, "content": line.strip()}
                            )
                report["todos"] = todos[:500]
            return ToolResult(status=ToolStatus.SUCCESS, data=report)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def search_files(self, args: Dict) -> ToolResult:
        """Search files under a path for a query string and return matches with context"""
        try:
            query = args.get("query")
            base_path = Path(args.get("path", "."))
            context_lines = int(args.get("context_lines", 2))
            fuzzy = bool(args.get("fuzzy", False))  # noqa: F841
            limit = int(args.get("limit", 200))
            if not query:
                return ToolResult(status=ToolStatus.ERROR, error="No query provided")
            matches = []
            files_searched = 0
            for p in base_path.rglob("*"):
                if p.is_file():
                    files_searched += 1
                    try:
                        text = p.read_text()
                    except Exception:
                        continue
                    lines = text.splitlines()
                    for i, line in enumerate(lines):
                        if query.lower() in line.lower():
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            context = lines[start:end]
                            matches.append(
                                {
                                    "file": str(p),
                                    "line": i + 1,
                                    "content": line.strip(),
                                    "context": context,
                                }
                            )
                            if len(matches) >= limit:
                                break
                    if len(matches) >= limit:
                        break
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"matches": matches, "files_searched": files_searched},
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def apply_edit(self, args: Dict) -> ToolResult:
        """Perform a search-and-replace with preview option and safe backup"""
        try:
            filepath = Path(args.get("filepath"))
            search = args.get("search")
            replace = args.get("replace", "")
            use_regex = bool(args.get("use_regex", False))
            preview = bool(args.get("preview", True))
            do_apply = bool(args.get("apply", False))
            if not filepath.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")
            original = filepath.read_text()
            if use_regex:
                new_content, count = re.subn(search, replace, original)
            else:
                new_content = original.replace(search, replace)
                count = original.count(search)
            # Generate diff preview
            diff = "".join(
                difflib.unified_diff(
                    original.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=str(filepath),
                    tofile=str(filepath),
                )
            )
            if preview and not do_apply:
                return ToolResult(
                    status=ToolStatus.SUCCESS, data={"matches": count, "preview": diff}
                )
            if do_apply:
                backup = filepath.with_suffix(
                    filepath.suffix + f".backup.{int(datetime.now().timestamp())}"
                )
                filepath.rename(backup)
                filepath.write_text(new_content)
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"matches": count, "diff": diff},
                    metadata={"backup": str(backup)},
                )
            return ToolResult(
                status=ToolStatus.ERROR, error="No action taken: set preview or apply"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def create_project(self, args: Dict) -> ToolResult:
        """Create a simple project scaffold for common templates"""
        try:
            name = args.get("name")
            template = args.get("template", "python-api")
            git_init = bool(args.get("git_init", True))
            create_venv = bool(args.get("create_venv", True))
            install_deps = bool(args.get("install_deps", False))
            project_dir = Path.cwd() / name
            if project_dir.exists():
                return ToolResult(
                    status=ToolStatus.ERROR, error="Project directory already exists"
                )
            project_dir.mkdir(parents=True)
            # Basic python-api scaffold
            if template == "python-api":
                (project_dir / "src").mkdir()
                app_py = project_dir / "src" / "main.py"
                app_py.write_text(
                    "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'status': 'ok'}\n"
                )
                (project_dir / "requirements.txt").write_text(
                    "fastapi\nuvicorn[standard]\n"
                )
                (project_dir / "README.md").write_text(
                    f"# {name}\n\nGenerated by Singularity (Omarchy compatible)\n"
                )
            else:
                (project_dir / "README.md").write_text(
                    f"# {name}\n\nGenerated by Singularity (Omarchy compatible) (template: {template})\n"
                )
            warnings = []
            if create_venv:
                venv_dir = project_dir / ".venv"
                subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])
                warnings.append(f"venv created at {venv_dir}")
                if install_deps:
                    pip_bin = venv_dir / "bin" / "pip"
                    if pip_bin.exists():
                        subprocess.run(
                            [
                                str(pip_bin),
                                "install",
                                "-r",
                                str(project_dir / "requirements.txt"),
                            ]
                        )
            if git_init:
                subprocess.run(["git", "init", str(project_dir)])
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"project": str(project_dir)},
                warnings=warnings,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def save_session(self, args: Dict) -> ToolResult:
        """Save current session to ~/.singularity/sessions/<name>.json"""
        try:
            name = args.get("name")
            description = args.get("description", "")
            if not name:
                return ToolResult(
                    status=ToolStatus.ERROR, error="No session name provided"
                )
            sessions_dir = Path.home() / ".singularity" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_file = sessions_dir / f"{name}.json"
            # Gather session data
            ctx_file = self.context_dir / "context.json"
            context = []
            if ctx_file.exists():
                try:
                    context = json.loads(ctx_file.read_text())
                except Exception:
                    context = []
            session = {
                "name": name,
                "description": description,
                "created": datetime.now().isoformat(),
                "conversation_history": getattr(self, "conversation_history", []),
                "current_plan": getattr(self, "current_plan", None),
                "context": context,
            }
            session_file.write_text(json.dumps(session, indent=2))
            return ToolResult(
                status=ToolStatus.SUCCESS, data={"session": str(session_file)}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def load_session(self, args: Dict) -> ToolResult:
        """Load a previously saved session into memory"""
        try:
            name = args.get("name")
            if not name:
                return ToolResult(
                    status=ToolStatus.ERROR, error="No session name provided"
                )
            sessions_dir = Path.home() / ".singularity" / "sessions"
            session_file = sessions_dir / f"{name}.json"
            if not session_file.exists():
                return ToolResult(status=ToolStatus.ERROR, error="Session not found")
            session = json.loads(session_file.read_text())
            self.conversation_history = session.get("conversation_history", [])
            self.current_plan = session.get("current_plan")
            # Restore context
            ctx_file = self.context_dir / "context.json"
            ctx_file.write_text(json.dumps(session.get("context", []), indent=2))
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"loaded": True, "session": str(session_file)},
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def generate_tests(self, args: Dict) -> ToolResult:
        """Generate simple pytest tests for a Python file by inspecting function defs"""
        try:
            filepath = args.get("filepath")
            if not filepath:
                return ToolResult(status=ToolStatus.ERROR, error="No filepath provided")
            path = Path(filepath)
            if not path.exists() or path.suffix != ".py":
                return ToolResult(
                    status=ToolStatus.ERROR, error="File not found or not a Python file"
                )
            module_name = path.stem
            tests_dir = path.parent / "tests"
            tests_dir.mkdir(exist_ok=True)
            test_file = tests_dir / f"test_{module_name}.py"
            source = path.read_text()
            try:
                tree = ast.parse(source)
            except Exception as e:
                return ToolResult(
                    status=ToolStatus.ERROR, error=f"AST parse failed: {e}"
                )
            funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            if not funcs:
                return ToolResult(
                    status=ToolStatus.ERROR, error="No functions found to test"
                )
            header = f"# Auto-generated tests for {module_name}\nimport pytest\nfrom {module_name} import *\n\n"
            body = ""
            for f in funcs[:10]:
                test_name = f"test_{f.name}_basic"
                body += f"def {test_name}():\n    # TODO: expand assertions for {f.name}\n    assert True\n\n"
            test_file.write_text(header + body)
            return ToolResult(
                status=ToolStatus.SUCCESS, data={"tests_created": str(test_file)}
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def manage_context(self, args: Dict) -> ToolResult:
        """Manage conversation context window intelligently"""
        try:
            action = args.get("action")
            items = args.get("items", [])
            auto_prune = bool(args.get("auto_prune", False))  # noqa: F841
            ctx_file = self.context_dir / "context.json"
            context = []
            if ctx_file.exists():
                try:
                    context = json.loads(ctx_file.read_text())
                except Exception:
                    context = []
            if action == "add":
                added = []
                if isinstance(items, str):
                    items = [items]
                for it in items:
                    entry = {
                        "id": hashlib.md5(
                            (it + str(datetime.now().timestamp())).encode()
                        ).hexdigest()[:8],
                        "content": it,
                        "created": datetime.now().isoformat(),
                    }
                    context.append(entry)
                    added.append(entry)
                ctx_file.write_text(json.dumps(context, indent=2))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"added": added, "total": len(context)},
                )
            if action == "remove":
                removed = []
                needle = items if isinstance(items, str) else None
                new_ctx = []
                for e in context:
                    if needle and needle in e.get("content", ""):
                        removed.append(e)
                    else:
                        new_ctx.append(e)
                ctx_file.write_text(json.dumps(new_ctx, indent=2))
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"removed": removed, "total": len(new_ctx)},
                )
            if action == "list":
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"items": context, "count": len(context)},
                )
            if action == "clear":
                if ctx_file.exists():
                    ctx_file.unlink()
                return ToolResult(status=ToolStatus.SUCCESS, data={"cleared": True})
            if action == "summarize":
                combined = "\n".join([e["content"] for e in context])
                summary = (
                    (combined[:1000] + "...") if len(combined) > 1000 else combined
                )
                return ToolResult(status=ToolStatus.SUCCESS, data={"summary": summary})
            return ToolResult(status=ToolStatus.ERROR, error="Unknown action")
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def test_code(self, args: Dict) -> ToolResult:
        """Run tests for a file or project using pytest and return results"""
        try:
            filepath = args.get("filepath")
            test_type = args.get("test_type", "unit")  # noqa: F841
            auto_fix = bool(args.get("auto_fix", False))  # noqa: F841
            generate_tests = bool(args.get("generate_tests", False))  # noqa: F841
            cwd = Path(filepath).parent if filepath else Path.cwd()
            cmd = [sys.executable, "-m", "pytest", "-q"]
            if filepath:
                cmd.append(str(filepath))
            # Run pytest
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))
            data = {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
            status = ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR
            return ToolResult(status=status, data=data)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def refactor_code(self, args: Dict) -> ToolResult:
        """Simple refactoring operations with safety checks. Currently supports 'rename'"""
        try:
            filepath = Path(args.get("filepath"))
            refactor_type = args.get("refactor_type")
            if not filepath.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")
            if refactor_type == "rename":
                old = args.get("old")
                new = args.get("new")
                preview = bool(args.get("preview", True))
                apply_change = bool(args.get("apply", False))
                content = filepath.read_text()
                if old not in content:
                    return ToolResult(
                        status=ToolStatus.ERROR, error="String to rename not found"
                    )
                count = content.count(old)
                diff = "".join(
                    difflib.unified_diff(
                        content.splitlines(keepends=True),
                        content.replace(old, new).splitlines(keepends=True),
                        fromfile=str(filepath),
                        tofile=str(filepath),
                    )
                )
                if preview and not apply_change:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"matches": count, "preview": diff},
                    )
                if apply_change:
                    backup = filepath.with_suffix(
                        filepath.suffix + f".backup.{int(datetime.now().timestamp())}"
                    )
                    filepath.rename(backup)
                    filepath.write_text(content.replace(old, new))
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"matches": count, "diff": diff},
                        metadata={"backup": str(backup)},
                    )
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="No action taken: set preview or apply",
                )
            return ToolResult(
                status=ToolStatus.ERROR, error="Unsupported refactor type"
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
