#!/usr/bin/env python3
"""
Singularity v3.0 - Continue.dev-inspired Coding Agent
Modern agent loop with granular permissions, streaming, and battle-tested patterns
"""

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from collections import deque

# Install dependencies if needed
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.tree import Tree
    from rich.text import Text
except ImportError:
    print("📦 Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "prompt_toolkit", "rich"], check=True)
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.tree import Tree
    from rich.text import Text

console = Console()
logger = logging.getLogger("singularity")

# Configure logging
log_dir = Path.home() / ".singularity" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / f"singularity_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

# Banner
BANNER = """[bold cyan]
╔═══════════════════════════════════════╗
║   🚀 SINGULARITY v3.0                ║
║   Continue.dev-inspired Agent        ║
║   Battle-tested • Modular • Fast    ║
╚═══════════════════════════════════════╝
[/bold cyan]"""


class PermissionLevel(Enum):
    """Permission levels for tools - Continue.dev style"""
    ALWAYS_ALLOW = "always_allow"  # Read-only operations
    ASK = "ask"  # Write operations that need approval
    NEVER = "never"  # Blocked operations


class ToolCategory(Enum):
    """Tool categories for permission management"""
    READ = "read"  # Read, List, Search, Diff
    WRITE = "write"  # Write, Edit, Create
    EXECUTE = "execute"  # Bash, Shell commands
    NETWORK = "network"  # Web requests, API calls
    SYSTEM = "system"  # System operations


@dataclass
class Tool:
    """Tool definition with metadata"""
    name: str
    description: str
    category: ToolCategory
    default_permission: PermissionLevel
    schema: Dict[str, Any]
    handler: Callable
    
    def __hash__(self):
        return hash(self.name)


@dataclass
class ToolCall:
    """Represents a tool execution request"""
    tool_name: str
    arguments: Dict[str, Any]
    context: Optional[str] = None
    requires_approval: bool = True
    approved: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class AgentStep:
    """Single step in agent execution loop"""
    step_number: int
    action: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    thoughts: str = ""
    output: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """Session state - Continue.dev inspired"""
    id: str
    messages: List[Dict] = field(default_factory=list)
    steps: List[AgentStep] = field(default_factory=list)
    context_files: List[Path] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


class PermissionManager:
    """Granular permission system - Continue.dev style
    
    Implements three-tier permission model:
    - always_allow: Read-only tools (automatic)
    - ask: Write operations (require confirmation)
    - never: Blocked operations (safety)
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (Path.home() / ".singularity" / "permissions.json")
        self.rules: Dict[str, PermissionLevel] = {}
        self.tool_permissions: Dict[str, PermissionLevel] = {}
        self.load()
    
    def load(self):
        """Load permission rules from config"""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.rules = {k: PermissionLevel(v) for k, v in data.get("rules", {}).items()}
                self.tool_permissions = {k: PermissionLevel(v) for k, v in data.get("tools", {}).items()}
            except Exception as e:
                logger.error(f"Failed to load permissions: {e}")
    
    def save(self):
        """Save permission rules to config"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "rules": {k: v.value for k, v in self.rules.items()},
            "tools": {k: v.value for k, v in self.tool_permissions.items()}
        }
        self.config_path.write_text(json.dumps(data, indent=2))
    
    def check_permission(self, tool: Tool, arguments: Dict) -> bool:
        """Check if tool execution is allowed
        
        Returns:
            True if auto-approved, False if requires user approval
        """
        # Check explicit tool permission
        if tool.name in self.tool_permissions:
            perm = self.tool_permissions[tool.name]
            if perm == PermissionLevel.ALWAYS_ALLOW:
                return True
            elif perm == PermissionLevel.NEVER:
                raise PermissionError(f"Tool {tool.name} is blocked")
            return False
        
        # Check category-based rules
        category_perm = self.rules.get(tool.category.value)
        if category_perm == PermissionLevel.ALWAYS_ALLOW:
            return True
        elif category_perm == PermissionLevel.NEVER:
            raise PermissionError(f"Category {tool.category.value} is blocked")
        
        # Default to tool's default permission
        return tool.default_permission == PermissionLevel.ALWAYS_ALLOW
    
    def set_permission(self, pattern: str, level: PermissionLevel):
        """Set permission for tool or category"""
        self.rules[pattern] = level
        self.save()
    
    def allow_tool(self, tool_name: str):
        """Always allow a specific tool"""
        self.tool_permissions[tool_name] = PermissionLevel.ALWAYS_ALLOW
        self.save()
    
    def block_tool(self, tool_name: str):
        """Block a specific tool"""
        self.tool_permissions[tool_name] = PermissionLevel.NEVER
        self.save()


class ContextManager:
    """Smart context window management - Continue.dev style"""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.files: Dict[str, str] = {}
        self.snippets: List[Dict] = []
        self.auto_context: List[str] = []
    
    def add_file(self, path: Path) -> bool:
        """Add file to context"""
        try:
            if path.exists() and path.is_file():
                content = path.read_text()[:5000]  # Limit per file
                self.files[str(path)] = content
                return True
        except Exception as e:
            logger.error(f"Failed to add file {path}: {e}")
        return False
    
    def add_snippet(self, code: str, language: str = "python", description: str = ""):
        """Add code snippet to context"""
        self.snippets.append({
            "code": code,
            "language": language,
            "description": description
        })
    
    def build_context_prompt(self) -> str:
        """Build context section for prompt"""
        parts = []
        
        if self.files:
            parts.append("## Referenced Files")
            for path, content in list(self.files.items())[:5]:  # Limit files
                parts.append(f"### {path}\n```\n{content[:2000]}\n```")
        
        if self.snippets:
            parts.append("## Code Snippets")
            for snip in self.snippets[-3:]:  # Last 3 snippets
                parts.append(f"{snip['description']}\n```{snip['language']}\n{snip['code']}\n```")
        
        return "\n\n".join(parts)
    
    def clear(self):
        """Clear all context"""
        self.files.clear()
        self.snippets.clear()


class AgentLoop:
    """Battle-tested agent execution loop - Continue.dev architecture
    
    Implements:
    - Multi-step reasoning
    - Tool calling with approval
    - Error recovery
    - Streaming output
    """
    
    def __init__(self, llm_client, permission_manager: PermissionManager, max_steps: int = 10):
        self.llm = llm_client
        self.permissions = permission_manager
        self.max_steps = max_steps
        self.current_session: Optional[Session] = None
        self.tools: Dict[str, Tool] = {}
        self.metrics = {
            "total_steps": 0,
            "tool_calls": 0,
            "approvals_requested": 0,
            "errors": 0
        }
    
    def register_tool(self, tool: Tool):
        """Register a tool for agent use"""
        self.tools[tool.name] = tool
    
    async def execute(self, prompt: str, context: Optional[ContextManager] = None) -> str:
        """Execute agent loop with multi-step reasoning"""
        session = Session(id=f"session_{int(time.time())}")
        self.current_session = session
        
        # Add initial user message
        session.messages.append({"role": "user", "content": prompt})
        
        # Build system prompt with tool descriptions
        system_prompt = self._build_system_prompt()
        if context:
            system_prompt += f"\n\n{context.build_context_prompt()}"
        
        step_number = 0
        while step_number < self.max_steps:
            step_number += 1
            step = AgentStep(step_number=step_number, action="thinking")
            
            # Stream LLM response
            full_response = ""
            with Live(console=console, refresh_per_second=10) as live:
                async for chunk in self.llm.stream(session.messages, system_prompt):
                    full_response += chunk
                    live.update(Panel(Markdown(full_response), title=f"🤖 Step {step_number}", border_style="cyan"))
            
            step.output = full_response
            session.messages.append({"role": "assistant", "content": full_response})
            
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(full_response)
            
            if not tool_calls:
                # No more tools to call - agent is done
                session.steps.append(step)
                break
            
            # Execute tool calls
            for tool_call in tool_calls:
                step.tool_calls.append(tool_call)
                await self._execute_tool_call(tool_call)
            
            session.steps.append(step)
            
            # Add tool results to conversation
            results_msg = self._format_tool_results(tool_calls)
            session.messages.append({"role": "system", "content": results_msg})
            
            # Check if agent wants to continue
            if "TASK_COMPLETE" in full_response or "I'm done" in full_response:
                break
        
        return session.steps[-1].output if session.steps else ""
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with tool descriptions"""
        tools_desc = []
        for tool in self.tools.values():
            tools_desc.append(f"- {tool.name}: {tool.description}")
        
        return f"""You are Singularity, an expert coding agent. You can use tools to accomplish tasks.

Available tools:
{chr(10).join(tools_desc)}

To use a tool, output JSON in this format:
{{"tool": "tool_name", "arguments": {{"arg1": "value1"}}}}

Think step-by-step. After using tools, summarize what you did and what's next.
When done, say "TASK_COMPLETE" in your response.
"""
    
    def _parse_tool_calls(self, response: str) -> List[ToolCall]:
        """Parse tool calls from LLM response"""
        tool_calls = []
        
        # Find JSON objects in response
        for match in re.finditer(r'\{[^}]*"tool"[^}]*\}', response):
            try:
                obj = json.loads(match.group())
                if "tool" in obj and "arguments" in obj:
                    tool_name = obj["tool"]
                    if tool_name in self.tools:
                        tool_call = ToolCall(
                            tool_name=tool_name,
                            arguments=obj["arguments"]
                        )
                        tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def _execute_tool_call(self, tool_call: ToolCall):
        """Execute a tool call with permission checking"""
        tool = self.tools.get(tool_call.tool_name)
        if not tool:
            tool_call.error = f"Unknown tool: {tool_call.tool_name}"
            return
        
        # Check permissions
        try:
            auto_approved = self.permissions.check_permission(tool, tool_call.arguments)
            tool_call.requires_approval = not auto_approved
            
            if tool_call.requires_approval:
                # Ask user for approval
                self.metrics["approvals_requested"] += 1
                approved = await self._request_approval(tool_call)
                if not approved:
                    tool_call.error = "User denied approval"
                    return
            
            # Execute tool
            start_time = time.time()
            tool_call.result = await tool.handler(tool_call.arguments)
            tool_call.execution_time = time.time() - start_time
            self.metrics["tool_calls"] += 1
            
        except PermissionError as e:
            tool_call.error = str(e)
        except Exception as e:
            tool_call.error = f"Execution failed: {e}"
            self.metrics["errors"] += 1
            logger.error(f"Tool execution error: {e}", exc_info=True)
    
    async def _request_approval(self, tool_call: ToolCall) -> bool:
        """Request user approval for tool execution"""
        console.print(Panel(
            f"[yellow]Tool:[/yellow] {tool_call.tool_name}\n"
            f"[yellow]Arguments:[/yellow] {json.dumps(tool_call.arguments, indent=2)}\n\n"
            "[dim]Approve this action?[/dim]",
            title="⚠️  Approval Required",
            border_style="yellow"
        ))
        return Confirm.ask("Allow?", default=False)
    
    def _format_tool_results(self, tool_calls: List[ToolCall]) -> str:
        """Format tool results for conversation"""
        results = []
        for tc in tool_calls:
            if tc.error:
                results.append(f"❌ {tc.tool_name} failed: {tc.error}")
            else:
                result_str = json.dumps(tc.result, indent=2) if tc.result else "Success"
                results.append(f"✅ {tc.tool_name}: {result_str}")
        return "\n".join(results)


class OllamaClient:
    """Ollama LLM client with streaming"""
    
    def __init__(self, model: str = "qwen2.5-coder:14b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    async def stream(self, messages: List[Dict], system_prompt: str = ""):
        """Stream completion from Ollama"""
        try:
            import aiohttp
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"], check=True)
            import aiohttp
        
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        payload = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
            "options": {"temperature": 0.2}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    async for line in resp.content:
                        if line:
                            try:
                                chunk = json.loads(line)
                                if "message" in chunk and "content" in chunk["message"]:
                                    yield chunk["message"]["content"]
                            except:
                                continue
        except Exception as e:
            yield f"Error: {e}"


# Tool implementations
async def tool_read_file(args: Dict) -> Dict:
    """Read file contents"""
    filepath = Path(args["filepath"])
    if not filepath.exists():
        return {"error": "File not found"}
    try:
        content = filepath.read_text()
        return {
            "filepath": str(filepath),
            "content": content,
            "lines": len(content.splitlines()),
            "size": len(content)
        }
    except Exception as e:
        return {"error": str(e)}


async def tool_write_file(args: Dict) -> Dict:
    """Write content to file"""
    filepath = Path(args["filepath"])
    content = args["content"]
    
    # Backup if exists
    if filepath.exists():
        backup = filepath.with_suffix(filepath.suffix + ".backup")
        filepath.rename(backup)
    
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        return {
            "filepath": str(filepath),
            "size": len(content),
            "lines": len(content.splitlines())
        }
    except Exception as e:
        return {"error": str(e)}


async def tool_execute_bash(args: Dict) -> Dict:
    """Execute bash command"""
    command = args["command"]
    timeout = args.get("timeout", 30)
    
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "command": command,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "returncode": proc.returncode,
                "success": proc.returncode == 0
            }
        except asyncio.TimeoutError:
            proc.kill()
            return {"error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


async def tool_search_files(args: Dict) -> Dict:
    """Search for pattern in files"""
    query = args["query"]
    path = Path(args.get("path", "."))
    limit = args.get("limit", 50)
    
    matches = []
    for file in path.rglob("*"):
        if file.is_file() and len(matches) < limit:
            try:
                content = file.read_text()
                for i, line in enumerate(content.splitlines(), 1):
                    if query.lower() in line.lower():
                        matches.append({
                            "file": str(file),
                            "line": i,
                            "content": line.strip()
                        })
                        if len(matches) >= limit:
                            break
            except:
                continue
    
    return {"query": query, "matches": matches, "total": len(matches)}


class SingularityCLI:
    """Main CLI application"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.llm = OllamaClient()
        self.permissions = PermissionManager()
        self.context = ContextManager()
        self.agent = AgentLoop(self.llm, self.permissions)
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all available tools"""
        tools = [
            Tool(
                name="read_file",
                description="Read contents of a file",
                category=ToolCategory.READ,
                default_permission=PermissionLevel.ALWAYS_ALLOW,
                schema={"filepath": "string"},
                handler=tool_read_file
            ),
            Tool(
                name="write_file",
                description="Write content to a file",
                category=ToolCategory.WRITE,
                default_permission=PermissionLevel.ASK,
                schema={"filepath": "string", "content": "string"},
                handler=tool_write_file
            ),
            Tool(
                name="execute_bash",
                description="Execute a bash command",
                category=ToolCategory.EXECUTE,
                default_permission=PermissionLevel.ASK,
                schema={"command": "string", "timeout": "int"},
                handler=tool_execute_bash
            ),
            Tool(
                name="search_files",
                description="Search for pattern in files",
                category=ToolCategory.READ,
                default_permission=PermissionLevel.ALWAYS_ALLOW,
                schema={"query": "string", "path": "string", "limit": "int"},
                handler=tool_search_files
            )
        ]
        
        for tool in tools:
            self.agent.register_tool(tool)
    
    async def run_interactive(self):
        """Interactive TUI mode"""
        console.print(BANNER)
        console.print("\n[dim]Type /help for commands, @file to add context, Ctrl+D to exit[/dim]\n")
        
        history_file = Path.home() / ".singularity" / "history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        session = PromptSession(history=FileHistory(str(history_file)))
        
        while True:
            try:
                user_input = await asyncio.to_thread(
                    session.prompt,
                    "singularity › "
                )
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue
                
                # Handle context providers
                if user_input.startswith("@"):
                    self._handle_context_provider(user_input)
                    continue
                
                # Execute agent loop
                response = await self.agent.execute(user_input, self.context)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit or Ctrl+D to quit[/yellow]")
            except EOFError:
                console.print("\n[yellow]👋 Goodbye![/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Interactive error: {e}", exc_info=True)
    
    async def run_headless(self, prompt: str):
        """Headless mode - single prompt execution"""
        response = await self.agent.execute(prompt, self.context)
        console.print(response)
    
    async def _handle_command(self, command: str):
        """Handle slash commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/help":
            self._show_help()
        elif cmd == "/exit":
            sys.exit(0)
        elif cmd == "/clear":
            self.context.clear()
            console.print("[green]Context cleared[/green]")
        elif cmd == "/allow":
            if args:
                self.permissions.allow_tool(args)
                console.print(f"[green]Tool '{args}' always allowed[/green]")
        elif cmd == "/ask":
            if args:
                self.permissions.set_permission(args, PermissionLevel.ASK)
                console.print(f"[yellow]Tool '{args}' requires approval[/yellow]")
        elif cmd == "/block":
            if args:
                self.permissions.block_tool(args)
                console.print(f"[red]Tool '{args}' blocked[/red]")
        elif cmd == "/metrics":
            self._show_metrics()
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
    
    def _handle_context_provider(self, input_str: str):
        """Handle @ context providers"""
        if input_str.startswith("@file:"):
            filepath = Path(input_str[6:].strip())
            if self.context.add_file(filepath):
                console.print(f"[green]Added {filepath} to context[/green]")
            else:
                console.print(f"[red]Failed to add {filepath}[/red]")
    
    def _show_help(self):
        """Show help message"""
        table = Table(title="Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        
        commands = [
            ("/help", "Show this help"),
            ("/exit", "Exit Singularity"),
            ("/clear", "Clear context"),
            ("/allow <tool>", "Always allow tool"),
            ("/ask <tool>", "Require approval for tool"),
            ("/block <tool>", "Block tool"),
            ("/metrics", "Show execution metrics"),
            ("@file:<path>", "Add file to context")
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        console.print(table)
    
    def _show_metrics(self):
        """Show agent execution metrics"""
        table = Table(title="Agent Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in self.agent.metrics.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print(table)


async def main():
    parser = argparse.ArgumentParser(description="Singularity v3.0 - Continue.dev-inspired Agent")
    parser.add_argument("-p", "--prompt", help="Headless mode: single prompt")
    parser.add_argument("--allow", action="append", help="Auto-allow tool")
    parser.add_argument("--model", default="qwen2.5-coder:14b", help="LLM model")
    args = parser.parse_args()
    
    cli = SingularityCLI(headless=bool(args.prompt))
    cli.llm.model = args.model
    
    # Apply auto-allow rules
    if args.allow:
        for tool in args.allow:
            cli.permissions.allow_tool(tool)
    
    if args.prompt:
        await cli.run_headless(args.prompt)
    else:
        await cli.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
