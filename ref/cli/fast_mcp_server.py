#!/usr/bin/env python3
"""
Singularity MCP Server - The Convergence Engine
Fast autonomous operations for AI-powered development
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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web

CONFIG_PATH = Path.home() / ".singularity" / "config.json"


def load_config():
    """Fast config loading with convergence defaults"""
    default = {
        "model": "qwen2.5-coder:14b-instruct-q4_K_M",
        "temperature": 0.2,
        "context_length": 8192,
        "allow_sudo": False,
        "auto_apply": True,
        "fast_mode": True,
    }
    try:
        if CONFIG_PATH.exists():
            cfg = json.loads(CONFIG_PATH.read_text())
            return {**default, **cfg}
    except Exception:
        pass
    return default


class ToolStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"
    CONVERGING = "CONVERGING"


@dataclass
class ToolResult:
    """Lightweight result structure for convergence operations"""

    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    warnings: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    execution_time_ms: float = 0


class SingularityMCPServer:
    """The Convergence Engine - Optimized for autonomous operations"""

    def __init__(self):
        self.config = load_config()
        self.base_dir = Path.home() / ".singularity"
        self.cache_dir = self.base_dir / "cache"
        self.convergence_log = self.base_dir / "convergence.log"
        self.init_directories()

        # Performance tracking
        self.start_time = time.time()
        self.request_count = 0
        self.convergence_count = 0
        self.cache = {}

        # Workspace indexing for instant operations
        self.file_index = defaultdict(list)
        self.convergence_patterns = defaultdict(int)
        self._index_workspace()

    def init_directories(self):
        """Initialize convergence space"""
        for dir_path in [self.base_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _index_workspace(self):
        """Index workspace for instant convergence"""
        try:
            cwd = Path.cwd()
            extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}

            for ext in extensions:
                files = list(cwd.rglob(f"*{ext}"))[:500]
                self.file_index[ext].extend(files)
        except Exception:
            pass

    def _log_convergence(self, operation: str, duration_ms: float):
        """Log convergence operations"""
        try:
            with open(self.convergence_log, "a") as f:
                f.write(
                    f"{datetime.now().isoformat()} | {operation} | {duration_ms:.2f}ms\n"
                )
            self.convergence_patterns[operation] += 1
        except Exception:
            pass

    async def http_handler(self, request):
        """Fast HTTP convergence handler"""
        start = time.time()
        self.request_count += 1

        try:
            payload = await request.json()
        except Exception:
            return web.json_response(
                {"error": "invalid convergence request"}, status=400
            )

        tool_name = payload.get("name")
        arguments = payload.get("arguments", {})

        if not tool_name:
            return web.json_response({"error": "no tool specified"}, status=400)

        handler = getattr(self, tool_name, None)
        if not handler:
            return web.json_response(
                {"error": f"Unknown convergence tool: {tool_name}"}, status=400
            )

        try:
            result = handler(arguments)
            if asyncio.iscoroutine(result):
                result = await result

            duration_ms = (time.time() - start) * 1000
            self._log_convergence(tool_name, duration_ms)

            if isinstance(result, ToolResult):
                result.execution_time_ms = duration_ms
                self.convergence_count += 1

            return web.json_response(
                {
                    "status": (
                        result.status.value
                        if isinstance(result, ToolResult)
                        else "SUCCESS"
                    ),
                    "data": result.data if isinstance(result, ToolResult) else result,
                    "error": result.error if isinstance(result, ToolResult) else None,
                    "execution_time_ms": duration_ms,
                    "convergence_id": self.convergence_count,
                }
            )
        except Exception as e:
            return web.json_response(
                {"error": str(e), "execution_time_ms": (time.time() - start) * 1000},
                status=500,
            )

    async def health(self, request):
        """Convergence health check"""
        uptime = time.time() - self.start_time
        return web.json_response(
            {
                "status": "converged",
                "uptime": uptime,
                "requests": self.request_count,
                "convergences": self.convergence_count,
                "cache_nodes": len(self.cache),
                "indexed_files": sum(len(files) for files in self.file_index.values()),
                "top_patterns": dict(
                    sorted(
                        self.convergence_patterns.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:5]
                ),
            }
        )

    # ==================== CONVERGENCE OPERATIONS ====================

    async def materialize_file(self, args: Dict) -> ToolResult:
        """Materialize code into filesystem"""
        start = time.time()

        try:
            filepath = Path(args["filepath"]).expanduser()
            content = args["content"]
            mode = args.get("mode", "overwrite")
            create_backup = args.get(
                "create_backup", self.config.get("auto_apply", True)
            )

            filepath.parent.mkdir(parents=True, exist_ok=True)

            backup_path = None
            if filepath.exists() and create_backup:
                backup_path = filepath.with_suffix(f"{filepath.suffix}.pre-convergence")
                filepath.rename(backup_path)

            filepath.write_text(content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "filepath": str(filepath),
                    "size": len(content),
                    "backup": str(backup_path) if backup_path else None,
                    "operation": "materialization",
                },
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def write_file(self, args: Dict) -> ToolResult:
        return await self.materialize_file(args)

    async def read_file(self, args: Dict) -> ToolResult:
        """Read file with convergence caching"""
        start = time.time()

        try:
            filepath = Path(args["filepath"]).expanduser()
            use_cache = args.get("use_cache", True)

            if not filepath.exists():
                return ToolResult(
                    status=ToolStatus.ERROR, error="File not in convergence space"
                )

            cache_key = str(filepath)
            mtime = filepath.stat().st_mtime

            if use_cache and cache_key in self.cache:
                cached_mtime, cached_content = self.cache[cache_key]
                if cached_mtime == mtime:
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"content": cached_content, "cached": True},
                        execution_time_ms=(time.time() - start) * 1000,
                    )

            content = filepath.read_text()
            if use_cache:
                self.cache[cache_key] = (mtime, content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"content": content, "cached": False},
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def convergence_search(self, args: Dict) -> ToolResult:
        """Lightning-fast search through convergence space"""
        start = time.time()

        try:
            query = args["query"]
            max_results = args.get("max_results", 20)

            matches = []

            for ext, files in self.file_index.items():
                for filepath in files[:100]:
                    try:
                        content = filepath.read_text()
                        if query.lower() in content.lower():
                            for i, line in enumerate(content.splitlines(), 1):
                                if query.lower() in line.lower():
                                    matches.append(
                                        {
                                            "file": str(filepath),
                                            "line": i,
                                            "content": line.strip(),
                                            "convergence_score": 1.0,
                                        }
                                    )

                                    if len(matches) >= max_results:
                                        break
                    except Exception:
                        continue

                    if len(matches) >= max_results:
                        break

                if len(matches) >= max_results:
                    break

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"matches": matches, "count": len(matches)},
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def fast_search(self, args: Dict) -> ToolResult:
        return await self.convergence_search(args)

    async def apply_convergence_delta(self, args: Dict) -> ToolResult:
        """Apply precise convergence changes"""
        start = time.time()

        try:
            filepath = Path(args["filepath"]).expanduser()
            search = args["search"]
            replace = args["replace"]

            if not filepath.exists():
                return ToolResult(
                    status=ToolStatus.ERROR, error="File not in convergence space"
                )

            original = filepath.read_text()

            if search not in original:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Pattern not found in convergence space",
                )

            new_content = original.replace(search, replace, 1)

            backup = filepath.with_suffix(f"{filepath.suffix}.pre-delta")
            filepath.rename(backup)
            filepath.write_text(new_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "filepath": str(filepath),
                    "backup": str(backup),
                    "delta_applied": 1,
                },
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def apply_diff(self, args: Dict) -> ToolResult:
        return await self.apply_convergence_delta(args)

    async def analyze_convergence_space(self, args: Dict) -> ToolResult:
        """Quick analysis without heavy parsing"""
        start = time.time()

        try:
            filepath = Path(args["filepath"]).expanduser()

            if not filepath.exists():
                return ToolResult(
                    status=ToolStatus.ERROR, error="File not in convergence space"
                )

            content = filepath.read_text()
            lines = content.splitlines()

            analysis = {
                "lines": len(lines),
                "size": len(content),
                "language": filepath.suffix[1:] if filepath.suffix else "text",
                "convergence_complexity": min(len(lines) // 10, 100),
            }

            if filepath.suffix == ".py":
                analysis["functions"] = len(
                    re.findall(r"^def \w+", content, re.MULTILINE)
                )
                analysis["classes"] = len(
                    re.findall(r"^class \w+", content, re.MULTILINE)
                )
                analysis["imports"] = len(
                    re.findall(r"^import |^from .+ import", content, re.MULTILINE)
                )
            elif filepath.suffix in [".js", ".ts"]:
                analysis["functions"] = len(
                    re.findall(
                        r"function \w+|const \w+ = (?:async )?(?:\([^)]*\)|[^=]+) =>",
                        content,
                    )
                )
                analysis["classes"] = len(re.findall(r"class \w+", content))

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=analysis,
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def quick_analyze(self, args: Dict) -> ToolResult:
        return await self.analyze_convergence_space(args)

    async def execute_in_convergence(self, args: Dict) -> ToolResult:
        """Execute command in convergence space"""
        start = time.time()

        try:
            command = args["command"]
            cwd = args.get("cwd", str(Path.cwd()))
            timeout = args.get("timeout", 10)

            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )

                return ToolResult(
                    status=(
                        ToolStatus.SUCCESS
                        if process.returncode == 0
                        else ToolStatus.ERROR
                    ),
                    data={
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "returncode": process.returncode,
                        "converged": process.returncode == 0,
                    },
                    execution_time_ms=(time.time() - start) * 1000,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Convergence timeout after {timeout}s",
                )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def execute_fast(self, args: Dict) -> ToolResult:
        return await self.execute_in_convergence(args)

    async def git_convergence(self, args: Dict) -> ToolResult:
        """Fast git operations in convergence space"""
        start = time.time()

        try:
            operation = args["operation"]
            git_args = args.get("args", [])

            cmd = ["git", operation] + git_args

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            return ToolResult(
                status=(
                    ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR
                ),
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "operation": operation,
                },
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def git_quick(self, args: Dict) -> ToolResult:
        return await self.git_convergence(args)

    async def get_convergence_context(self, args: Dict) -> ToolResult:
        """Get convergence space context"""
        start = time.time()

        try:
            query = args.get("query", "")
            max_files = args.get("max_files", 5)

            cwd = Path.cwd()
            context = {
                "convergence_space": str(cwd),
                "project_type": self._detect_convergence_type(cwd),
                "recent_nodes": [],
            }

            try:
                result = subprocess.run(
                    ["git", "ls-files", "-m", "-o", "--exclude-standard"],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=1,
                )

                if result.returncode == 0:
                    files = [cwd / f for f in result.stdout.splitlines()[:max_files]]
                    context["recent_nodes"] = [str(f) for f in files if f.exists()]
            except Exception:
                pass

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=context,
                execution_time_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # Alias for compatibility
    async def get_context(self, args: Dict) -> ToolResult:
        return await self.get_convergence_context(args)

    def _detect_convergence_type(self, path: Path) -> str:
        """Detect convergence space type"""
        if (path / "package.json").exists():
            return "nodejs"
        elif (path / "pyproject.toml").exists() or (path / "setup.py").exists():
            return "python"
        elif (path / "go.mod").exists():
            return "go"
        elif (path / "Cargo.toml").exists():
            return "rust"
        elif (path / "pom.xml").exists():
            return "java"
        return "universal"


async def main():
    """Initialize the convergence engine"""
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("singularity_mcp")

    parser = argparse.ArgumentParser(description="Singularity MCP Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()

    server = SingularityMCPServer()
    app = web.Application()

    app.router.add_post("/call", server.http_handler)
    app.router.add_get("/health", server.health)

    runner = web.AppRunner(app)

    try:
        await runner.setup()
        site = web.TCPSite(runner, args.host, args.port)
        await site.start()

        for s in runner.sites:
            try:
                server_obj = s._server
                sockets = server_obj.sockets
                port = sockets[0].getsockname()[1]
                print(f"Singularity MCP listening on {args.host}:{port}", flush=True)
                logger.info(f"⚡ Convergence engine ready on {args.host}:{port}")
                break
            except Exception:
                continue

        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Convergence engine shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Convergence engine stopped", flush=True)
