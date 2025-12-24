#!/usr/bin/env python3
"""
Singularity MCP Server v3.0 - Continue.dev-inspired
Enhanced tools with proper error handling, telemetry, and streaming
"""

import ast
import asyncio
import difflib
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mcp_server")


class ToolStatus(Enum):
    """Tool execution status"""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PARTIAL = "PARTIAL"
    TIMEOUT = "TIMEOUT"


@dataclass
class ToolResult:
    """Standardized tool result"""
    status: ToolStatus
    data: Any = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    execution_time: float = 0.0


class MCPServer:
    """Enhanced MCP server with telemetry and streaming"""
    
    def __init__(self):
        self.config = self._load_config()
        self.base_dir = Path.home() / ".singularity"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Telemetry
        self.start_time = time.time()
        self.metrics = {
            "requests": deque(maxlen=1000),
            "latencies": deque(maxlen=1000),
            "errors": deque(maxlen=1000),
            "tool_usage": {}
        }
    
    def _load_config(self) -> Dict:
        """Load configuration"""
        config_path = Path.home() / ".singularity" / "config.json"
        default = {
            "allow_sudo": False,
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "timeout": 30
        }
        
        if config_path.exists():
            try:
                user_config = json.loads(config_path.read_text())
                return {**default, **user_config}
            except:
                pass
        
        return default
    
    async def handle_tool_call(self, request):
        """Handle incoming tool call"""
        start_time = time.time()
        
        try:
            payload = await request.json()
        except:
            return web.json_response(
                {"error": "Invalid JSON"},
                status=400
            )
        
        tool_name = payload.get("name")
        arguments = payload.get("arguments", {})
        
        if not tool_name:
            return web.json_response(
                {"error": "Missing tool name"},
                status=400
            )
        
        # Record metrics
        self.metrics["requests"].append(time.time())
        self.metrics["tool_usage"][tool_name] = \
            self.metrics["tool_usage"].get(tool_name, 0) + 1
        
        # Get handler
        handler = getattr(self, f"tool_{tool_name}", None)
        if not handler:
            return web.json_response(
                {"error": f"Unknown tool: {tool_name}"},
                status=404
            )
        
        # Execute tool
        try:
            result = await handler(arguments)
            execution_time = time.time() - start_time
            
            if isinstance(result, ToolResult):
                result.execution_time = execution_time
                response_data = {
                    "status": result.status.value,
                    "data": result.data,
                    "error": result.error,
                    "warnings": result.warnings,
                    "metadata": {**result.metadata, "execution_time": execution_time}
                }
            else:
                response_data = {
                    "status": "SUCCESS",
                    "data": result,
                    "execution_time": execution_time
                }
            
            self.metrics["latencies"].append(execution_time)
            return web.json_response(response_data)
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.metrics["errors"].append({
                "tool": tool_name,
                "error": str(e),
                "time": time.time()
            })
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            
            return web.json_response(
                {
                    "status": "ERROR",
                    "error": str(e),
                    "execution_time": execution_time
                },
                status=500
            )
    
    async def health(self, request):
        """Health check with metrics"""
        uptime = time.time() - self.start_time
        
        # Calculate metrics
        total_requests = len(self.metrics["requests"])
        recent_requests = sum(1 for t in self.metrics["requests"] 
                            if time.time() - t < 60)
        
        latencies = list(self.metrics["latencies"])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return web.json_response({
            "status": "healthy",
            "uptime": uptime,
            "metrics": {
                "total_requests": total_requests,
                "requests_per_minute": recent_requests,
                "avg_latency_ms": avg_latency * 1000,
                "error_count": len(self.metrics["errors"]),
                "tool_usage": dict(self.metrics["tool_usage"])
            }
        })
    
    # Tool implementations
    
    async def tool_read_file(self, args: Dict) -> ToolResult:
        """Read file with size limits and encoding detection"""
        filepath = Path(args.get("filepath", ""))
        
        if not filepath.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                error="File not found"
            )
        
        try:
            size = filepath.stat().st_size
            if size > self.config["max_file_size"]:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"File too large: {size} bytes"
                )
            
            # Try UTF-8, fall back to latin-1
            try:
                content = filepath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = filepath.read_text(encoding="latin-1")
            
            # Parse AST for Python files
            ast_info = None
            if filepath.suffix == ".py":
                try:
                    tree = ast.parse(content)
                    functions = [n.name for n in ast.walk(tree) 
                               if isinstance(n, ast.FunctionDef)]
                    classes = [n.name for n in ast.walk(tree) 
                             if isinstance(n, ast.ClassDef)]
                    ast_info = {
                        "functions": functions[:20],
                        "classes": classes[:20]
                    }
                except:
                    pass
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "content": content,
                    "lines": len(content.splitlines()),
                    "size": size,
                    "encoding": "utf-8"
                },
                metadata={
                    "filepath": str(filepath),
                    "ast": ast_info
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def tool_write_file(self, args: Dict) -> ToolResult:
        """Write file with backup and formatting"""
        filepath = Path(args.get("filepath", ""))
        content = args.get("content", "")
        auto_format = args.get("auto_format", False)
        create_backup = args.get("create_backup", True)
        
        warnings = []
        
        try:
            # Create backup
            if filepath.exists() and create_backup:
                backup_path = filepath.with_suffix(
                    filepath.suffix + f".backup.{int(time.time())}"
                )
                filepath.rename(backup_path)
                warnings.append(f"Backup created: {backup_path}")
            
            # Write file
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)
            
            # Auto-format Python
            if auto_format and filepath.suffix == ".py":
                try:
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable, "-m", "black", str(filepath),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await asyncio.wait_for(proc.wait(), timeout=10)
                    warnings.append("Auto-formatted with black")
                    content = filepath.read_text()  # Read formatted content
                except:
                    warnings.append("Auto-format skipped (black not available)")
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "filepath": str(filepath),
                    "size": len(content),
                    "lines": len(content.splitlines())
                },
                warnings=warnings,
                metadata={
                    "hash": hashlib.sha256(content.encode()).hexdigest()[:8]
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def tool_apply_diff(self, args: Dict) -> ToolResult:
        """Apply unified diff with preview"""
        filepath = Path(args.get("filepath", ""))
        diff_text = args.get("diff", "")
        dry_run = args.get("dry_run", True)
        
        if not filepath.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                error="File not found"
            )
        
        try:
            original = filepath.read_text()
            
            # Parse diff and apply changes
            # This is a simplified implementation
            # Production would use difflib properly
            
            if dry_run:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"preview": diff_text},
                    warnings=["Dry run - no changes applied"]
                )
            
            # Apply diff (simplified)
            # In production, use proper diff parsing
            
            return ToolResult(
                status=ToolStatus.PARTIAL,
                error="Diff application not fully implemented",
                warnings=["Use write_file for now"]
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def tool_execute_bash(self, args: Dict) -> ToolResult:
        """Execute bash with timeout and streaming"""
        command = args.get("command", "")
        timeout = args.get("timeout", self.config["timeout"])
        stream = args.get("stream", False)
        env = args.get("env", {})
        
        if not command:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No command provided"
            )
        
        try:
            full_env = os.environ.copy()
            full_env.update(env)
            
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env
            )
            
            if stream:
                chunks = []
                try:
                    while True:
                        line = await asyncio.wait_for(
                            proc.stdout.readline(),
                            timeout=1.0
                        )
                        if not line:
                            break
                        chunks.append(line.decode(errors="replace"))
                    
                    await asyncio.wait_for(proc.wait(), timeout=timeout)
                    
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "chunks": chunks,
                            "returncode": proc.returncode
                        }
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return ToolResult(
                        status=ToolStatus.TIMEOUT,
                        error=f"Command timed out after {timeout}s",
                        data={"chunks": chunks}
                    )
            else:
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout
                    )
                    
                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={
                            "stdout": stdout.decode(errors="replace"),
                            "stderr": stderr.decode(errors="replace"),
                            "returncode": proc.returncode,
                            "success": proc.returncode == 0
                        }
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    return ToolResult(
                        status=ToolStatus.TIMEOUT,
                        error=f"Command timed out after {timeout}s"
                    )
                    
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def tool_search_codebase(self, args: Dict) -> ToolResult:
        """Smart codebase search with context"""
        query = args.get("query", "")
        path = Path(args.get("path", "."))
        include_context = args.get("include_context", True)
        context_lines = args.get("context_lines", 2)
        limit = args.get("limit", 100)
        
        if not query:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No query provided"
            )
        
        try:
            matches = []
            files_searched = 0
            
            for file in path.rglob("*"):
                if file.is_file() and len(matches) < limit:
                    # Skip binary and large files
                    if file.stat().st_size > 1024 * 1024:  # 1MB
                        continue
                    
                    try:
                        content = file.read_text()
                        files_searched += 1
                        lines = content.splitlines()
                        
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                match = {
                                    "file": str(file.relative_to(path)),
                                    "line": i + 1,
                                    "content": line.strip()
                                }
                                
                                if include_context:
                                    start = max(0, i - context_lines)
                                    end = min(len(lines), i + context_lines + 1)
                                    match["context"] = lines[start:end]
                                
                                matches.append(match)
                                
                                if len(matches) >= limit:
                                    break
                    except:
                        continue
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "matches": matches,
                    "total": len(matches)
                },
                metadata={
                    "files_searched": files_searched,
                    "truncated": len(matches) >= limit
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def tool_analyze_file(self, args: Dict) -> ToolResult:
        """Deep file analysis with metrics"""
        filepath = Path(args.get("filepath", ""))
        
        if not filepath.exists():
            return ToolResult(
                status=ToolStatus.ERROR,
                error="File not found"
            )
        
        try:
            content = filepath.read_text()
            lines = content.splitlines()
            
            analysis = {
                "filepath": str(filepath),
                "size": len(content),
                "lines": len(lines),
                "blank_lines": sum(1 for line in lines if not line.strip()),
                "imports": [],
                "functions": [],
                "classes": [],
                "complexity": 0
            }
            
            # Python-specific analysis
            if filepath.suffix == ".py":
                try:
                    tree = ast.parse(content)
                    
                    # Extract imports
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            analysis["imports"].extend([n.name for n in node.names])
                        elif isinstance(node, ast.ImportFrom):
                            module = node.module or ""
                            analysis["imports"].append(module)
                    
                    # Extract functions and classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            analysis["functions"].append({
                                "name": node.name,
                                "lineno": node.lineno,
                                "args": len(node.args.args)
                            })
                        elif isinstance(node, ast.ClassDef):
                            analysis["classes"].append({
                                "name": node.name,
                                "lineno": node.lineno,
                                "methods": sum(1 for n in node.body 
                                             if isinstance(n, ast.FunctionDef))
                            })
                    
                    # Calculate complexity (simplified)
                    complexity = 0
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.If, ast.For, ast.While, 
                                           ast.Try, ast.ExceptHandler)):
                            complexity += 1
                    analysis["complexity"] = complexity
                    
                except:
                    pass
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=analysis
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )
    
    async def tool_git_operation(self, args: Dict) -> ToolResult:
        """Git operations with smart defaults"""
        operation = args.get("operation", "")
        git_args = args.get("args", [])
        auto_add = args.get("auto_add", False)
        
        if not operation:
            return ToolResult(
                status=ToolStatus.ERROR,
                error="No operation specified"
            )
        
        try:
            # Auto-add before commit
            if operation == "commit" and auto_add:
                proc = await asyncio.create_subprocess_exec(
                    "git", "add", "-A",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.wait()
            
            # Execute git command
            cmd = ["git", operation] + git_args
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            return ToolResult(
                status=ToolStatus.SUCCESS if proc.returncode == 0 else ToolStatus.ERROR,
                data={
                    "stdout": stdout.decode(errors="replace"),
                    "stderr": stderr.decode(errors="replace"),
                    "returncode": proc.returncode
                },
                metadata={
                    "operation": operation,
                    "args": git_args
                }
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e)
            )


async def main():
    """Start MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server v3.0")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    
    server = MCPServer()
    app = web.Application()
    
    # Routes
    app.router.add_post("/call", server.handle_tool_call)
    app.router.add_get("/health", server.health)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, args.host, args.port)
    await site.start()
    
    # Get actual port
    port = list(runner.sites)[0]._server.sockets[0].getsockname()[1]
    
    print(f"MCP server listening on {args.host}:{port}", flush=True)
    logger.info(f"Server started on {args.host}:{port}")
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete", flush=True)
