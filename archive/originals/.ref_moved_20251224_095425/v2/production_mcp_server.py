#!/usr/bin/env python3
"""
Singularity MCP Server - Production Ready
Provides comprehensive development tools via HTTP API
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import hashlib
import difflib
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, List

from aiohttp import web


def load_config():
    """Load configuration with defaults"""
    default = {
        "model": "qwen2.5-coder:14b-instruct-q4_K_M",
        "temperature": 0.2,
        "context_length": 8192,
        "allow_sudo": False,
        "auto_apply": False,
    }
    try:
        cfg_path = Path.home() / ".singularity" / "config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            return {**default, **cfg}
    except Exception:
        pass
    return default


class ToolStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"


@dataclass
class ToolResult:
    """Structured result for all tool operations"""
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self):
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class MCPServer:
    """Production MCP Server with all tools implemented"""

    def __init__(self):
        self.config = load_config()
        self.base_dir = Path.home() / ".singularity"
        self.cache_dir = self.base_dir / "cache"
        self.knowledge_dir = self.base_dir / "knowledge"
        self.plans_dir = self.base_dir / "plans"
        self.sessions_dir = self.base_dir / "sessions"
        self._init_directories()

    def _init_directories(self):
        """Initialize required directories"""
        for dir_path in [self.base_dir, self.cache_dir, self.knowledge_dir, 
                         self.plans_dir, self.sessions_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def http_handler(self, request):
        """Handle HTTP POST requests to /call"""
        start = time.time()

        try:
            payload = await request.json()
        except Exception:
            return web.json_response(
                {"error": "Invalid JSON payload"}, 
                status=400
            )

        tool_name = payload.get("name")
        arguments = payload.get("arguments", {})

        if not tool_name:
            return web.json_response(
                {"error": "Missing 'name' field"}, 
                status=400
            )

        # Get handler method
        handler = getattr(self, tool_name, None)
        if not handler:
            return web.json_response(
                {"error": f"Unknown tool: {tool_name}"}, 
                status=400
            )

        try:
            result = handler(arguments)
            if asyncio.iscoroutine(result):
                result = await result

            execution_time = (time.time() - start) * 1000

            if isinstance(result, ToolResult):
                response = result.to_dict()
                response["execution_time_ms"] = execution_time
                return web.json_response(response)
            else:
                # Legacy support for non-ToolResult returns
                return web.json_response({
                    "status": "SUCCESS",
                    "data": result,
                    "execution_time_ms": execution_time
                })

        except Exception as e:
            execution_time = (time.time() - start) * 1000
            return web.json_response({
                "status": "ERROR",
                "error": str(e),
                "execution_time_ms": execution_time
            }, status=500)

    async def health(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        })

    # ==================== FILE OPERATIONS ====================

    async def write_code(self, args: Dict) -> ToolResult:
        """Write code to a file with backup"""
        try:
            filepath = Path(args["filepath"]).expanduser()
            content = args["content"]
            mode = args.get("mode", "overwrite")

            # Create parent directories
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Backup existing file
            backup_path = None
            if filepath.exists():
                timestamp = int(datetime.now().timestamp())
                backup_path = filepath.with_suffix(f"{filepath.suffix}.backup.{timestamp}")
                filepath.rename(backup_path)

            # Write new content
            filepath.write_text(content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "filepath": str(filepath),
                    "size": len(content),
                    "lines": len(content.splitlines()),
                    "backup": str(backup_path) if backup_path else None
                },
                warnings=["Backup created"] if backup_path else []
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def read_code(self, args: Dict) -> ToolResult:
        """Read and analyze code file"""
        try:
            filepath = Path(args["filepath"]).expanduser()
            
            if not filepath.exists():
                return ToolResult(status=ToolStatus.ERROR, error="File not found")

            content = filepath.read_text()
            
            data = {
                "content": content,
                "size": len(content),
                "lines": len(content.splitlines()),
                "path": str(filepath)
            }

            # Optional pattern matching
            pattern = args.get("pattern")
            if pattern:
                matches = []
                for i, line in enumerate(content.splitlines(), 1):
                    if pattern in line:
                        matches.append({"line": i, "content": line.strip()})
                data["matches"] = matches

            return ToolResult(status=ToolStatus.SUCCESS, data=data)

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def search_files(self, args: Dict) -> ToolResult:
        """Search files for a pattern"""
        try:
            query = args["query"]
            path = Path(args.get("path", "."))
            limit = args.get("limit", 100)

            matches = []
            files_searched = 0

            for filepath in path.rglob("*"):
                if not filepath.is_file():
                    continue
                
                # Skip hidden files and common exclusions
                if any(part.startswith('.') for part in filepath.parts):
                    continue
                if any(x in str(filepath) for x in ['node_modules', '__pycache__', '.git']):
                    continue

                files_searched += 1
                
                try:
                    content = filepath.read_text()
                    for i, line in enumerate(content.splitlines(), 1):
                        if query.lower() in line.lower():
                            matches.append({
                                "file": str(filepath),
                                "line": i,
                                "content": line.strip()
                            })
                            
                            if len(matches) >= limit:
                                break
                except Exception:
                    continue

                if len(matches) >= limit:
                    break

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "matches": matches,
                    "files_searched": files_searched,
                    "query": query
                }
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ==================== EXECUTION ====================

    async def execute_code(self, args: Dict) -> ToolResult:
        """Execute shell command with timeout"""
        try:
            command = args["command"]
            cwd = args.get("cwd", str(Path.cwd()))
            timeout = args.get("timeout", 30)

            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )

                return ToolResult(
                    status=ToolStatus.SUCCESS if proc.returncode == 0 else ToolStatus.ERROR,
                    data={
                        "stdout": stdout.decode() if stdout else "",
                        "stderr": stderr.decode() if stderr else "",
                        "returncode": proc.returncode,
                        "command": command
                    }
                )

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Command timed out after {timeout}s"
                )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ==================== GIT OPERATIONS ====================

    async def git_operation(self, args: Dict) -> ToolResult:
        """Perform git operations"""
        try:
            operation = args["operation"]
            git_args = args.get("args", [])

            cmd = ["git", operation] + git_args

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            return ToolResult(
                status=ToolStatus.SUCCESS if result.returncode == 0 else ToolStatus.ERROR,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "operation": operation
                }
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ==================== ANALYSIS ====================

    async def analyze_codebase(self, args: Dict) -> ToolResult:
        """Analyze codebase structure and metrics"""
        try:
            path = Path(args.get("path", "."))
            analysis_type = args.get("analysis_type", "structure")

            files = []
            for p in path.rglob("*"):
                if p.is_file() and not any(part.startswith('.') for part in p.parts):
                    files.append(p)

            report = {"files_count": len(files)}

            if analysis_type in ("structure", "all"):
                report["structure"] = [
                    {
                        "path": str(p.relative_to(path)),
                        "size": p.stat().st_size,
                        "extension": p.suffix
                    }
                    for p in files[:100]
                ]

            if analysis_type in ("todos", "all"):
                todos = []
                for p in files:
                    try:
                        content = p.read_text()
                        for i, line in enumerate(content.splitlines(), 1):
                            if "TODO" in line or "FIXME" in line:
                                todos.append({
                                    "file": str(p.relative_to(path)),
                                    "line": i,
                                    "content": line.strip()
                                })
                    except Exception:
                        continue
                report["todos"] = todos[:100]

            return ToolResult(status=ToolStatus.SUCCESS, data=report)

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ==================== KNOWLEDGE BASE ====================

    async def save_knowledge(self, args: Dict) -> ToolResult:
        """Save knowledge to persistent storage"""
        try:
            topic = args["topic"]
            content = args["content"]
            tags = args.get("tags", [])

            knowledge_id = topic.replace(" ", "_").lower()
            filepath = self.knowledge_dir / f"{knowledge_id}.json"

            knowledge = {
                "topic": topic,
                "content": content,
                "tags": tags,
                "created": datetime.now().isoformat(),
                "updated": datetime.now().isoformat()
            }

            filepath.write_text(json.dumps(knowledge, indent=2))

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"knowledge_id": knowledge_id, "path": str(filepath)}
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    async def query_knowledge(self, args: Dict) -> ToolResult:
        """Query knowledge base"""
        try:
            query = args["query"].lower()
            limit = args.get("limit", 10)

            results = []
            for filepath in self.knowledge_dir.glob("*.json"):
                try:
                    knowledge = json.loads(filepath.read_text())
                    
                    # Simple relevance scoring
                    score = 0
                    if query in knowledge.get("topic", "").lower():
                        score += 10
                    if query in knowledge.get("content", "").lower():
                        score += 5

                    if score > 0:
                        results.append({
                            "topic": knowledge.get("topic"),
                            "score": score,
                            "excerpt": knowledge.get("content", "")[:200] + "...",
                            "tags": knowledge.get("tags", [])
                        })
                except Exception:
                    continue

            results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]

            return ToolResult(status=ToolStatus.SUCCESS, data={"results": results})

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ==================== PLANNING ====================

    async def create_plan(self, args: Dict) -> ToolResult:
        """Create a project plan"""
        try:
            goal = args["goal"]
            
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            plan = {
                "id": plan_id,
                "goal": goal,
                "created": datetime.now().isoformat(),
                "status": "active",
                "items": []
            }

            filepath = self.plans_dir / f"{plan_id}.json"
            filepath.write_text(json.dumps(plan, indent=2))

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"plan_id": plan_id, "path": str(filepath)}
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    # ==================== UTILITIES ====================

    async def fetch_url(self, args: Dict) -> ToolResult:
        """Fetch content from URL"""
        try:
            import urllib.request
            
            url = args["url"]
            timeout = args.get("timeout", 10)

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Singularity/1.0"}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")

            # Basic HTML stripping
            content = re.sub(r"<[^>]+>", "", content)
            content = " ".join(content.split())

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"content": content[:5000], "url": url}
            )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))


async def main():
    """Start the MCP server"""
    import argparse

    parser = argparse.ArgumentParser(description="Singularity MCP Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)  # 0 = random port
    args = parser.parse_args()

    server = MCPServer()
    app = web.Application()

    # Routes
    app.router.add_post("/call", server.http_handler)
    app.router.add_get("/health", server.health)

    runner = web.AppRunner(app)

    try:
        await runner.setup()
        site = web.TCPSite(runner, args.host, args.port)
        await site.start()

        # Get actual port and print it (for parent process to capture)
        for s in runner.sites:
            try:
                server_obj = s._server
                sockets = server_obj.sockets
                actual_port = sockets[0].getsockname()[1]
                
                # IMPORTANT: Print in a format parent process can parse
                print(f"MCP server listening on {args.host}:{actual_port}", flush=True)
                break
            except Exception:
                continue

        # Keep running
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("MCP server shutting down", flush=True)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("MCP server stopped", flush=True)