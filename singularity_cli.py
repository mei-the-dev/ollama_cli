#!/usr/bin/env python3
"""
Singularity CLI - Beautiful Code Agent Interface
Powered by Ollama Qwen2.5-Coder with MCP Tools
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import shutil
import argparse
from datetime import datetime
import logging
import getpass
import aiohttp

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.live import Live
    from rich.markdown import Markdown
except ImportError:
    print("Installing required dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.live import Live
    from rich.markdown import Markdown

console = Console()

# Setup a simple file logger for non-interactive/plain logs
logger = logging.getLogger('singularity')
if not logger.handlers:
    try:
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / 'singularity.log')
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
    except Exception:
        pass


# ASCII Art Banner
BANNER = """
[bold magenta]
    ╔═╗┬ ┬┌─┐┌─┐┌─┐┬ ┬  ╔═╗┬ ┬┌─┐┬  ┬
    ╚═╗└┬┘├┤ ├─┘├┤ │││  ║  ├─┤├┤ └┐┌┘
    ╚═╝ ┴ └─┘┴  └  └┴┘  ╚═╝┴ ┴└─┘ └┘
[/bold magenta]
[bold cyan]Singularity — Artistic Code Agent[/bold cyan]
[dim]🔮 Powered by Qwen2.5-Coder 14B via Ollama | Use @web, @file, @diff, @tree for Context Providers[/dim]
"""

THINKING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
CODE_FRAMES = ["◐", "◓", "◑", "◒"]
COMPLETE_SYMBOL = "✓"
ERROR_SYMBOL = "✗"


class SingularityAgent:
    def __init__(self):
        self.model = "qwen2.5-coder:14b-instruct-q4_K_M"
        self.mcp_server_path = Path.home() / ".singularity" / "mcp_server.py"
        self.conversation_history = []
        self.current_plan = None
        
    async def start_mcp_server(self, timeout: float = 5.0):
        """Start the MCP server process and wait for it to announce a listening port."""
        if not self.mcp_server_path.exists():
            # Fallback: if there's a copy of mcp_server.py in the repository, use it (useful for tests/local dev)
            repo_path = Path(__file__).resolve().parents[0] / 'mcp_server.py'
            if repo_path.exists():
                self.mcp_server_path = repo_path
            else:
                console.print("[yellow]MCP server not found. Please install it first (or copy mcp_server.py to ~/.singularity/).[/yellow]")
                return None

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(self.mcp_server_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Read stdout lines until we get the listening announcement or timeout
            port = None
            start = asyncio.get_event_loop().time()
            while True:
                if process.stdout.at_eof():
                    break
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout)
                except asyncio.TimeoutError:
                    break
                if not line:
                    break
                text = line.decode(errors="replace").strip()
                if text:
                    console.print(f"[dim]{text}[/dim]")
                if "MCP server listening on" in text:
                    # parse host:port
                    parts = text.split()
                    hostport = parts[-1]
                    if ':' in hostport:
                        host, port_s = hostport.split(':')
                        try:
                            port = int(port_s)
                            self.mcp_server_url = f"http://{host}:{port}"
                        except ValueError:
                            pass
                    break
                if (asyncio.get_event_loop().time() - start) > timeout:
                    break

            self.mcp_process = process
            if port:
                console.print(f"[green]MCP server running at {self.mcp_server_url}[/green]")
                logger.info('MCP server running at %s', self.mcp_server_url)
            else:
                console.print("[yellow]MCP server started but did not report port within timeout[/yellow]")
                logger.warning('MCP server started but did not report port within timeout')
            return process
        except Exception as e:
            console.print(f"[red]Failed to start MCP server: {e}[/red]")
            return None

    async def stop_mcp_server(self):
        """Stop the running MCP server process if any."""
        proc = getattr(self, 'mcp_process', None)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=3)
                console.print("[green]MCP server stopped[/green]")
            except Exception:
                proc.kill()
                console.print("[red]MCP server killed[/red]")
            finally:
                self.mcp_process = None
                self.mcp_server_url = None

    async def call_ollama(self, prompt: str, system: Optional[str] = None, tools: Optional[List[Dict]] = None):
        """Call Ollama with streaming support"""
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        if system:
            payload["system"] = system
        
        if tools:
            payload["tools"] = tools
        
        try:
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-X", "POST",
                "http://localhost:11434/api/chat",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            full_response = ""
            tool_calls = []
            
            async for line in process.stdout:
                if line:
                    try:
                        chunk = json.loads(line.decode())
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            if content:
                                full_response += content
                                yield {"type": "content", "data": content}
                            
                            # Check for tool calls
                            if "tool_calls" in chunk["message"]:
                                tool_calls.extend(chunk["message"]["tool_calls"])
                        
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
            
            if tool_calls:
                yield {"type": "tool_calls", "data": tool_calls}
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            yield {"type": "error", "data": str(e)}

    async def execute_with_animation(self, prompt: str, task_description: str, system: Optional[str] = None):
        # When executing with animation, ensure model gets current knowledge/context from disk if configured
        # (This doesn't send files, but appends a short summary of known topics into the system prompt when available.)
        knowledge_summary = ''
        try:
            kb_dir = Path.home() / '.omarchy' / 'knowledge'
            if kb_dir.exists():
                entries = []
                for f in list(kb_dir.glob('*.json'))[:10]:
                    try:
                        j = json.loads(f.read_text())
                        entries.append(f"{j.get('topic')} - { (j.get('content','')[:200] + '...') if len(j.get('content'))>200 else j.get('content','')} ")
                    except Exception:
                        continue
                if entries:
                    knowledge_summary = '\n'.join(entries[:5])
                    if system:
                        system = (system + '\n\nKnowledge Summary:\n' + knowledge_summary)
                    else:
                        system = 'Knowledge Summary:\n' + knowledge_summary
        except Exception:
            pass
        """Execute a prompt with beautiful animation"""
        console.print(f"\n[bold cyan]→[/bold cyan] {task_description}")
        
        full_response = ""
        
        with Live(console=console, refresh_per_second=10) as live:
            frame_idx = 0
            
            async for chunk in self.call_ollama(prompt, system=system):
                if chunk["type"] == "content":
                    full_response += chunk["data"]
                    
                    # Animated thinking indicator
                    frame = THINKING_FRAMES[frame_idx % len(THINKING_FRAMES)]
                    live.update(
                        Panel(
                            f"[cyan]{frame}[/cyan] {full_response}",
                            title="[bold]Agent Response[/bold]",
                            border_style="cyan"
                        )
                    )
                    frame_idx += 1
                
                elif chunk["type"] == "tool_calls":
                    live.update(
                        Panel(
                            f"[green]{COMPLETE_SYMBOL}[/green] Response complete\n[yellow]Executing tools...[/yellow]",
                            title="[bold]Agent Response[/bold]",
                            border_style="green"
                        )
                    )
                    # Handle tool execution
                    await self.handle_tool_calls(chunk["data"])
                
                elif chunk["type"] == "error":
                    live.update(
                        Panel(
                            f"[red]{ERROR_SYMBOL}[/red] Error: {chunk['data']}",
                            title="[bold]Error[/bold]",
                            border_style="red"
                        )
                    )
                    return
        
        # Final display
        console.print(Panel(
            Markdown(full_response),
            title=f"[bold green]{COMPLETE_SYMBOL}[/bold green] Complete",
            border_style="green"
        ))
        
        return full_response



    async def handle_tool_calls(self, tool_calls: List[Dict]):
        """Handle MCP tool calls (tool_calls is a list of dicts or single dict)"""
        if isinstance(tool_calls, dict):
            tool_calls = [tool_calls]

        for tool_call in tool_calls:
            # support both streaming tool format and simple JSON {"tool":..., "args":...}
            tool_name = None
            tool_args = {}
            if 'function' in tool_call:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = tool_call.get("function", {}).get("arguments", {})
            else:
                tool_name = tool_call.get('tool') or tool_call.get('name')
                tool_args = tool_call.get('args') or tool_call.get('arguments') or {}

            console.print(f"  [yellow]→[/yellow] Executing: [bold]{tool_name}[/bold]")

            # If write_code, optionally confirm with user unless auto_apply is enabled or non-interactive
            auto_apply = bool(os.environ.get('SINGULARITY_AUTO_APPLY')) or getattr(self, 'auto_apply', False)
            interactive = sys.stdin.isatty()
            if tool_name == 'write_code' and not auto_apply:
                if interactive:
                    try:
                        confirm = Confirm.ask(f"Apply write to {tool_args.get('filepath')}? (y/n)")
                    except Exception:
                        confirm = False
                else:
                    confirm = False
                if not confirm:
                    console.print(f"[yellow]Skipped writing {tool_args.get('filepath')}[/yellow]")
                    continue

            # If execute_code and sudo requested, attach sudo_password if available
            if tool_name == 'execute_code' and tool_args.get('sudo'):
                sudo_pw = getattr(self, 'sudo_password', None)
                if sudo_pw:
                    tool_args['sudo_password'] = sudo_pw

            # Execute tool via MCP server HTTP API
            try:
                if not hasattr(self, 'mcp_server_url') or not self.mcp_server_url:
                    console.print(f"[red]MCP server URL not known; cannot execute tool {tool_name}[/red]")
                    continue
                async with aiohttp.ClientSession() as session:
                    payload = {"name": tool_name, "arguments": tool_args}
                    async with session.post(self.mcp_server_url + '/call', json=payload) as resp:
                        res = await resp.json()
                        console.print(f"  [green]{COMPLETE_SYMBOL}[/green] {tool_name} completed: {res.get('status', res)}")
            except Exception as e:
                console.print(f"  [red]Tool {tool_name} failed: {e!r}[/red]")

    
    def display_plan(self, plan: Dict):
        """Display current plan with progress"""
        table = Table(title="📋 Current Plan", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Task", style="white")
        table.add_column("Status", width=12)
        
        for idx, item in enumerate(plan.get("items", []), 1):
            status = item.get("status", "pending")
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "complete": "✓",
                "blocked": "🚫"
            }.get(status, "❓")
            
            status_color = {
                "pending": "yellow",
                "in_progress": "cyan",
                "complete": "green",
                "blocked": "red"
            }.get(status, "white")
            
            table.add_row(
                str(idx),
                item.get("description", "Task"),
                f"[{status_color}]{status_icon} {status}[/{status_color}]"
            )

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import shutil
import argparse
from datetime import datetime
import logging
import getpass
import aiohttp

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.live import Live
    from rich.markdown import Markdown
except ImportError:
    print("Installing required dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.live import Live
    from rich.markdown import Markdown

console = Console()

# Setup a simple file logger for non-interactive/plain logs
logger = logging.getLogger('singularity')
if not logger.handlers:
    try:
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / 'singularity.log')
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
    except Exception:
        pass


# ASCII Art Banner
BANNER = """
[bold magenta]
    ╔═╗┬ ┬┌─┐┌─┐┌─┐┬ ┬  ╔═╗┬ ┬┌─┐┬  ┬
    ╚═╗└┬┘├┤ ├─┘├┤ │││  ║  ├─┤├┤ └┐┌┘
    ╚═╝ ┴ └─┘┴  └  └┴┘  ╚═╝┴ ┴└─┘ └┘
[/bold magenta]
[bold cyan]Singularity — Artistic Code Agent[/bold cyan]
[dim]🔮 Powered by Qwen2.5-Coder 14B via Ollama | Use @web, @file, @diff, @tree for Context Providers[/dim]
"""

THINKING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
CODE_FRAMES = ["◐", "◓", "◑", "◒"]
COMPLETE_SYMBOL = "✓"
ERROR_SYMBOL = "✗"


class SingularityAgent:
    def __init__(self):
        self.model = "qwen2.5-coder:14b-instruct-q4_K_M"
        self.mcp_server_path = Path.home() / ".singularity" / "mcp_server.py"
        self.conversation_history = []
        self.current_plan = None
        
    async def start_mcp_server(self, timeout: float = 5.0):
        """Start the MCP server process and wait for it to announce a listening port."""
        if not self.mcp_server_path.exists():
            # Fallback: if there's a copy of mcp_server.py in the repository, use it (useful for tests/local dev)
            repo_path = Path(__file__).resolve().parents[0] / 'mcp_server.py'
            if repo_path.exists():
                self.mcp_server_path = repo_path
            else:
                console.print("[yellow]MCP server not found. Please install it first (or copy mcp_server.py to ~/.singularity/).[/yellow]")
                return None

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(self.mcp_server_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Read stdout lines until we get the listening announcement or timeout
            port = None
            start = asyncio.get_event_loop().time()
            while True:
                if process.stdout.at_eof():
                    break
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout)
                except asyncio.TimeoutError:
                    break
                if not line:
                    break
                text = line.decode(errors="replace").strip()
                if text:
                    console.print(f"[dim]{text}[/dim]")
                if "MCP server listening on" in text:
                    # parse host:port
                    parts = text.split()
                    hostport = parts[-1]
                    if ':' in hostport:
                        host, port_s = hostport.split(':')
                        try:
                            port = int(port_s)
                            self.mcp_server_url = f"http://{host}:{port}"
                        except ValueError:
                            pass
                    break
                if (asyncio.get_event_loop().time() - start) > timeout:
                    break

            self.mcp_process = process
            if port:
                console.print(f"[green]MCP server running at {self.mcp_server_url}[/green]")
                logger.info('MCP server running at %s', self.mcp_server_url)
            else:
                console.print("[yellow]MCP server started but did not report port within timeout[/yellow]")
                logger.warning('MCP server started but did not report port within timeout')
            return process
        except Exception as e:
            console.print(f"[red]Failed to start MCP server: {e}[/red]")
            return None

    async def stop_mcp_server(self):
        """Stop the running MCP server process if any."""
        proc = getattr(self, 'mcp_process', None)
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=3)
                console.print("[green]MCP server stopped[/green]")
            except Exception:
                proc.kill()
                console.print("[red]MCP server killed[/red]")
            finally:
                self.mcp_process = None
                self.mcp_server_url = None
    
    async def call_ollama(self, prompt: str, system: Optional[str] = None, tools: Optional[List[Dict]] = None):
        """Call Ollama with streaming support"""
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }
        
        if system:
            payload["system"] = system
        
        if tools:
            payload["tools"] = tools
        
        try:
            process = await asyncio.create_subprocess_exec(
                "curl",
                "-X", "POST",
                "http://localhost:11434/api/chat",
                "-H", "Content-Type: application/json",
                "-d", json.dumps(payload),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            full_response = ""
            tool_calls = []
            
            async for line in process.stdout:
                if line:
                    try:
                        chunk = json.loads(line.decode())
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            if content:
                                full_response += content
                                yield {"type": "content", "data": content}
                            
                            # Check for tool calls
                            if "tool_calls" in chunk["message"]:
                                tool_calls.extend(chunk["message"]["tool_calls"])
                        
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
            
            if tool_calls:
                yield {"type": "tool_calls", "data": tool_calls}
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            yield {"type": "error", "data": str(e)}
    
    async def execute_with_animation(self, prompt: str, task_description: str, system: Optional[str] = None):
        # When executing with animation, ensure model gets current knowledge/context from disk if configured
        # (This doesn't send files, but appends a short summary of known topics into the system prompt when available.)
        knowledge_summary = ''
        try:
            kb_dir = Path.home() / '.omarchy' / 'knowledge'
            if kb_dir.exists():
                entries = []
                for f in list(kb_dir.glob('*.json'))[:10]:
                    try:
                        j = json.loads(f.read_text())
                        entries.append(f"{j.get('topic')} - { (j.get('content','')[:200] + '...') if len(j.get('content',''))>200 else j.get('content','')} ")
                    except Exception:
                        continue
                if entries:
                    knowledge_summary = '\n'.join(entries[:5])
                    if system:
                        system = (system + '\n\nKnowledge Summary:\n' + knowledge_summary)
                    else:
                        system = 'Knowledge Summary:\n' + knowledge_summary
        except Exception:
            pass
        """Execute a prompt with beautiful animation"""
        console.print(f"\n[bold cyan]→[/bold cyan] {task_description}")
        
        full_response = ""
        
        with Live(console=console, refresh_per_second=10) as live:
            frame_idx = 0
            
            async for chunk in self.call_ollama(prompt, system=system):
                if chunk["type"] == "content":
                    full_response += chunk["data"]
                    
                    # Animated thinking indicator
                    frame = THINKING_FRAMES[frame_idx % len(THINKING_FRAMES)]
                    live.update(
                        Panel(
                            f"[cyan]{frame}[/cyan] {full_response}",
                            title="[bold]Agent Response[/bold]",
                            border_style="cyan"
                        )
                    )
                    frame_idx += 1
                
                elif chunk["type"] == "tool_calls":
                    live.update(
                        Panel(
                            f"[green]{COMPLETE_SYMBOL}[/green] Response complete\n[yellow]Executing tools...[/yellow]",
                            title="[bold]Agent Response[/bold]",
                            border_style="green"
                        )
                    )
                    # Handle tool execution
                    await self.handle_tool_calls(chunk["data"])
                
                elif chunk["type"] == "error":
                    live.update(
                        Panel(
                            f"[red]{ERROR_SYMBOL}[/red] Error: {chunk['data']}",
                            title="[bold]Error[/bold]",
                            border_style="red"
                        )
                    )
                    return
        
        # Final display
        console.print(Panel(
            Markdown(full_response),
            title=f"[bold green]{COMPLETE_SYMBOL}[/bold green] Complete",
            border_style="green"
        ))
        
        return full_response



    async def handle_tool_calls(self, tool_calls: List[Dict]):
        """Handle MCP tool calls (tool_calls is a list of dicts or single dict)"""
        if isinstance(tool_calls, dict):
            tool_calls = [tool_calls]

        for tool_call in tool_calls:
            # support both streaming tool format and simple JSON {"tool":..., "args":...}
            tool_name = None
            tool_args = {}
            if 'function' in tool_call:
                tool_name = tool_call.get("function", {}).get("name")
                tool_args = tool_call.get("function", {}).get("arguments", {})
            else:
                tool_name = tool_call.get('tool') or tool_call.get('name')
                tool_args = tool_call.get('args') or tool_call.get('arguments') or {}

            console.print(f"  [yellow]→[/yellow] Executing: [bold]{tool_name}[/bold]")

            # If write_code, optionally confirm with user unless auto_apply is enabled or non-interactive
            auto_apply = bool(os.environ.get('SINGULARITY_AUTO_APPLY')) or getattr(self, 'auto_apply', False)
            interactive = sys.stdin.isatty()
            if tool_name == 'write_code' and not auto_apply:
                if interactive:
                    try:
                        confirm = Confirm.ask(f"Apply write to {tool_args.get('filepath')}? (y/n)")
                    except Exception:
                        confirm = False
                else:
                    confirm = False
                if not confirm:
                    console.print(f"[yellow]Skipped writing {tool_args.get('filepath')}[/yellow]")
                    continue

            # If execute_code and sudo requested, attach sudo_password if available
            if tool_name == 'execute_code' and tool_args.get('sudo'):
                sudo_pw = getattr(self, 'sudo_password', None)
                if sudo_pw:
                    tool_args['sudo_password'] = sudo_pw

            # Execute tool via MCP server HTTP API
            try:
                if not hasattr(self, 'mcp_server_url') or not self.mcp_server_url:
                    console.print(f"[red]MCP server URL not known; cannot execute tool {tool_name}[/red]")
                    continue
                async with aiohttp.ClientSession() as session:
                    payload = {"name": tool_name, "arguments": tool_args}
                    async with session.post(self.mcp_server_url + '/call', json=payload) as resp:
                        res = await resp.json()
                        console.print(f"  [green]{COMPLETE_SYMBOL}[/green] {tool_name} completed: {res.get('status', res)}")
            except Exception as e:
                console.print(f"  [red]Tool {tool_name} failed: {e!r}[/red]")

    
    def display_plan(self, plan: Dict):
        """Display current plan with progress"""
        table = Table(title="📋 Current Plan", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Task", style="white")
        table.add_column("Status", width=12)
        
        for idx, item in enumerate(plan.get("items", []), 1):
            status = item.get("status", "pending")
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "complete": "✓",
                "blocked": "🚫"
            }.get(status, "❓")
            
            status_color = {
                "pending": "yellow",
                "in_progress": "cyan",
                "complete": "green",
                "blocked": "red"
            }.get(status, "white")
            
            table.add_row(
                str(idx),
                item.get("description", "Task"),
                f"[{status_color}]{status_icon} {status}[/{status_color}]"
            )
        
        console.print(table)


class SingularityCLI:
    def __init__(self):
        self.agent = SingularityAgent()
        # Auto-apply writes if env SINGULARITY_AUTO_APPLY=1 or config auto_apply true
        self.auto_apply = bool(os.environ.get('SINGULARITY_AUTO_APPLY'))
        self.sudo_password = None
        self.modes = {
            "chat": "💬 Interactive chat mode",
            "code": "⚡ Code generation mode",
            "plan": "📋 Project planning mode",
            "batch": "📦 Batch file generation",
            "learn": "🎓 Learn and save knowledge",
            "analyze": "🔍 Codebase analysis"
        }
    
    def show_banner(self):
        """Display the banner with a stylized layout"""
        console.clear()
        # Create a two-column header with the banner and quick tips
        left = Panel(BANNER, border_style="magenta", padding=(1,2))
        tips = Panel(
            "[bold]Quick Tips[/bold]\n- Use [cyan]@file.py[/cyan] to inject a file into context\n- Use [cyan]@web:http://...[/cyan] to fetch docs\n- Use [cyan]/mode code[/cyan] to generate code\n\nType [cyan]help[/cyan] to see commands",
            border_style="green", padding=(1,2)
        )
        console.print(Columns([left, tips]))
        # Subtle divider
        console.rule('[dim]Ready — Ask me to generate code, suggest edits, or explore the repo[/dim]')

    async def startup_config_prompt(self):
        """Interactive prompts at startup to transfer knowledge/context and optionally enable auto-apply and sudo."""
        # Skip prompts if not attached to a TTY (non-interactive environment)
        # Allow tests (pytest) to run prompts even when not a TTY by checking test env.
        if not sys.stdin.isatty() and not os.environ.get('PYTEST_CURRENT_TEST'):
            console.print("[yellow]Non-interactive environment detected; skipping startup prompts.[/yellow]")
            return

        # Transfer knowledge
        try:
            if Confirm.ask("Transfer local knowledge to the model's system prompt (recommended)?"):
                kb_dir = Path.home() / '.singularity' / 'knowledge'
                if kb_dir.exists():
                    entries = []
                    for f in list(kb_dir.glob('*.json'))[:20]:
                        try:
                            j = json.loads(f.read_text())
                            entries.append(f"{j.get('topic')}: { (j.get('content','')[:300] + '...') if len(j.get('content',''))>300 else j.get('content','') }")
                        except Exception:
                            continue
                    if entries:
                        sys_msg = "Knowledge Summary:\n" + "\n".join(entries[:10])
                        # Insert as a system message at the start of conversation history
                        self.agent.conversation_history.insert(0, {"role": "system", "content": sys_msg})
                        console.print("[green]Knowledge summary loaded into the agent context.[/green]")
        except Exception:
            console.print("[yellow]Skipping knowledge transfer (non-interactive environment).[/yellow]")

        # Transfer context
        try:
            if Confirm.ask("Transfer conversation context (context.json) to the model? "):
                ctx_file = Path.home() / '.singularity' / 'context' / 'context.json'
                if ctx_file.exists():
                    try:
                        ctx = json.loads(ctx_file.read_text())
                        ctx_text = '\n'.join([c.get('content','') for c in ctx][-20:])
                        self.agent.conversation_history.insert(0, {"role": "system", "content": "Conversation context:\n" + ctx_text})
                        console.print("[green]Conversation context injected.[/green]")
                    except Exception:
                        console.print("[yellow]Failed to load context file.[/yellow]")
        except Exception:
            console.print("[yellow]Skipping context transfer (non-interactive environment).[/yellow]")

        # Auto-apply writes
        try:
            if Confirm.ask("Enable auto-approval for file writes (auto-apply)? This will allow the CLI to apply agent-suggested file writes without prompting."):
                cfg_path = Path.home() / '.singularity' / 'config.json'
                try:
                    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
                except Exception:
                    cfg = {}
                cfg['auto_apply'] = True
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(cfg, indent=2))
                os.environ['SINGULARITY_AUTO_APPLY'] = '1'
                self.auto_apply = True
                console.print('[green]Auto-apply enabled.[/green]')
        except Exception:
            console.print('[yellow]Skipping auto-apply configuration.[/yellow]')

        # Sudo privileges
        try:
            if Confirm.ask("Enable sudo privileges for MCP server tools? (This allows the server to run sudo commands.)"):
                cfg_path = Path.home() / '.singularity' / 'config.json'
                try:
                    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
                except Exception:
                    cfg = {}
                cfg['allow_sudo'] = True
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(cfg, indent=2))
                # Optionally ask for password to store for this session only
                if Confirm.ask('Store sudo password for this session to allow non-interactive sudo?'):
                    try:
                        pw = getpass.getpass('Enter sudo password (stored only in memory for this session): ')
                        self.sudo_password = pw
                        console.print('[green]Sudo password stored for session.[/green]')
                    except Exception:
                        console.print('[yellow]Could not read password; sudo will use non-interactive mode and may fail if password required.[/yellow]')
                console.print('[green]Sudo enabled in config. You can disable it later at ~/.singularity/config.json[/green]')
        except Exception:
            console.print('[yellow]Skipping sudo configuration.[/yellow]')

    async def interactive_mode(self):
        """Main interactive loop"""
        self.show_banner()
        
        current_mode = "chat"
        
        while True:
            try:
                # Beautiful prompt
                prompt = Prompt.ask(
                    f"\n[bold cyan]singularity[/bold cyan] [[{current_mode}]]"
                )
                
                if not prompt:
                    continue
                
                # Handle commands
                if prompt.startswith("/"):
                    parts = prompt.split(maxsplit=1)
                    cmd = parts[0]
                    args = parts[1] if len(parts) > 1 else ""
                    
                    if cmd == "/exit":
                        console.print("[yellow]Goodbye! Happy coding! 👋[/yellow]")
                        break
                    elif cmd == "/help":
                        self.show_help()
                    elif cmd == "/mode":
                        if args in self.modes:
                            current_mode = args
                            console.print(f"[green]Switched to {current_mode} mode[/green]")
                        else:
                            self.show_modes()
                    elif cmd == "/new":
                        self.agent.conversation_history = []
                        console.print("[green]New conversation started[/green]")
                    elif cmd == "/plan":
                        if self.agent.current_plan:
                            self.agent.display_plan(self.agent.current_plan)
                        else:
                            console.print("[yellow]No active plan[/yellow]")
                    elif cmd == "/exec":
                        await self.execute_command(args)
                    elif cmd == "/dashboard":
                        # Launch dashboard in a separate process or tmux window
                        try:
                            await self.start_dashboard()
                        except Exception as e:
                            console.print(f"[red]Failed to start dashboard: {e}[/red]")
                    elif cmd == "/config":
                        sub = args.strip().split() if args else []
                        if len(sub) >= 1 and sub[0] == 'show':
                            self.show_config_table()
                        else:
                            console.print("[yellow]Usage: /config show[/yellow]")
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]")
                    
                    continue
                
                # Process based on mode
                await self.process_prompt(prompt, current_mode)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    def show_help(self):
        """Display help with available commands"""
        help_table = Table(title="Help", show_header=False)
        commands = [
            ("/mode <name>", "Switch modes"),
            ("/new", "Start a new conversation"),
            ("/plan", "View current plan"),
            ("/exec <cmd>", "Execute a shell command"),
            ("/dashboard", "Launch the dashboard"),
            ("/config show", "Show effective configuration (env + ~/.singularity/config.json)"),
            ("/help", "Show this help"),
            ("/exit", "Exit Singularity")
        ]
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        console.print(help_table)

    def show_modes(self):
        """Display available modes"""
        modes_table = Table(title="Available Modes", show_header=True, header_style="bold cyan")
        modes_table.add_column("Mode", style="cyan", width=15)
        modes_table.add_column("Description", style="white")
        for mode, desc in self.modes.items():
            modes_table.add_row(mode, desc)
        console.print(modes_table)

    async def process_prompt(self, prompt: str, mode: str):
        """Process prompt based on current mode"""
        mode_prompts = {
            "chat": f"User query: {prompt}",
            "code": f"Generate code for: {prompt}. Provide complete, production-ready code with comments.",
            "plan": f"Create a detailed implementation plan for: {prompt}. Break it into actionable steps.",
            "batch": f"Generate multiple files for: {prompt}. Create all necessary files and structure.",
            "learn": f"Research and learn about: {prompt}. Save findings to knowledge base.",
            "analyze": f"Analyze the codebase focusing on: {prompt}. Provide insights and recommendations."
        }

        # Build a tool-aware system prompt instructing the model to emit JSON tool calls when needed
        tool_prompt = (
            f"{self.agent.model} system: If you need to perform actions like writing files or running shell commands, "
            "output a single JSON object and nothing else with the structure: {\"tool\": \"name\", \"args\": {...}}. "
            "For file creation/modification use tool \"write_code\" with args {\"filepath\": \"/path\", \"content\": \"...\", \"mode\": \"overwrite\"}. "
            "Available tools: write_code, apply_edit, refactor_code, search_files, fetch_url, execute_code, git_operation."
        )
        full_prompt = mode_prompts.get(mode, prompt)
        await self.agent.execute_with_animation(full_prompt, f"Processing in {mode} mode", system=tool_prompt)

    def get_effective_config(self) -> Dict:
        """Return the effective configuration merging environment variables and ~/.singularity/config.json (with ~/.omarchy fallback)"""
        singularity_cfg = Path.home() / '.singularity' / 'config.json'
        omarchy_cfg = Path.home() / '.omarchy' / 'config.json'
        file_cfg = {}
        try:
            if singularity_cfg.exists():
                file_cfg = json.loads(singularity_cfg.read_text())
            elif omarchy_cfg.exists():
                file_cfg = json.loads(omarchy_cfg.read_text())
        except Exception:
            logger.exception('Failed to read config file')

        def env_bool(key, default=False):
            v = os.environ.get(key)
            if v is None:
                return file_cfg.get(key.lower(), default)
            return v.lower() in ('1', 'true', 'yes', 'on')

        conf = {
            'allow_sudo': env_bool('SINGULARITY_ALLOW_SUDO', file_cfg.get('allow_sudo', False) or env_bool('OMARCHY_ALLOW_SUDO', False)),
            'auto_apply': env_bool('SINGULARITY_AUTO_APPLY', file_cfg.get('auto_apply', False) or env_bool('OMARCHY_AUTO_APPLY', False)),
            'skip_ollama': env_bool('SINGULARITY_SKIP_OLLAMA', False) or env_bool('OMARCHY_SKIP_OLLAMA', False),
            'model': os.environ.get('SINGULARITY_MODEL', os.environ.get('OMARCHY_MODEL', file_cfg.get('model', self.agent.model))),
            'mcp_server_url': getattr(self.agent, 'mcp_server_url', None) or os.environ.get('SINGULARITY_MCP_SERVER_URL') or os.environ.get('OMARCHY_MCP_SERVER_URL'),
            'preferred_terminal': os.environ.get('SINGULARITY_PREFERRED_TERMINAL', file_cfg.get('preferred_terminal') or os.environ.get('OMARCHY_PREFERRED_TERMINAL'))
        }
        return conf

    def show_config_table(self):
        """Print config in a human-friendly table"""
        conf = self.get_effective_config()
        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        for k, v in conf.items():
            table.add_row(k, str(v))
        console.print(table)

    def print_config_json(self):
        conf = self.get_effective_config()
        print(json.dumps(conf, indent=2))

    async def execute_command(self, cmd: str):
        """Execute shell command asynchronously with animation and logging"""
        with console.status(f"[cyan]Executing: {cmd}[/cyan]", spinner="dots"):
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                try:
                    out_bytes, err_bytes = await asyncio.wait_for(proc.communicate(), timeout=30)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    console.print("[red]Error: command timed out after 30s[/red]")
                    logger.warning('execute_command timeout: %s', cmd)
                    return
                out = out_bytes.decode(errors='replace') if out_bytes else ''
                err = err_bytes.decode(errors='replace') if err_bytes else ''
                if out:
                    console.print(Panel(out, title="Output", border_style="green"))
                if err:
                    console.print(Panel(err, title="Errors", border_style="red"))
                logger.info('execute_command finished: %s (rc=%s)', cmd, proc.returncode)
            except Exception as e:
                logger.exception('execute_command error')
                console.print(f"[red]Error executing command: {e!r}[/red]")

    async def start_dashboard(self):
        """Start the dashboard UI.

        - If `tmux` is available, spawn a new tmux window named `dashboard-<ts>` and run the dashboard there.
        - Otherwise, start the dashboard as a background Python process and write logs to ./logs/dashboard.log
        """
        import time
        dashboard_path = os.path.join(os.path.dirname(__file__), 'ref', 'singularity_dashboard.py')

        # Ensure log dir exists
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        dashboard_log = os.path.join(log_dir, 'dashboard.log')

        tmux_path = shutil.which('tmux')
        window_name = f"dashboard-{int(time.time())}"
        python_exec = sys.executable

        # Prepare MCP server URL to pass into the dashboard
        mcp_url = getattr(self.agent, 'mcp_server_url', None) or os.environ.get('SINGULARITY_MCP_SERVER_URL') or os.environ.get('OMARCHY_MCP_SERVER_URL') or 'http://127.0.0.1:8000'

        if tmux_path:
            # If we're already inside tmux, create a new window in the current session so the user sees it.
            if 'TMUX' in os.environ:
                shell_cmd = f"OMARCHY_MCP_SERVER_URL='{mcp_url}' exec {python_exec} {dashboard_path}"
                cmd = [tmux_path, 'new-window', '-n', window_name, 'bash', '-lc', shell_cmd]
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                console.print(f"[green]Dashboard launched in new tmux window '{window_name}' (pid: {proc.pid}).[/green]")
            else:
                session_name = os.environ.get('SINGULARITY_SESSION', 'singularity')
                shell_cmd = f"OMARCHY_MCP_SERVER_URL='{mcp_url}' exec {python_exec} {dashboard_path}"
                cmd = [tmux_path, 'new-session', '-d', '-s', session_name, '-n', window_name, 'bash', '-lc', shell_cmd]
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                console.print(f"[green]Dashboard launched in tmux session '{session_name}', window '{window_name}' (pid: {proc.pid}). Attach with: tmux attach -t {session_name}[/green]")

        else:
            # Start a background process logging to file
            cmd = [python_exec, dashboard_path]
            with open(dashboard_log, 'ab') as fh:
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=fh, stderr=fh)
            console.print(f"[green]Dashboard started as background process (pid: {proc.pid}). Logs: {dashboard_log}[/green]")

# Attach existing module-level helper functions to SingularityCLI so they behave as instance methods
for _name in ('startup_config_prompt', 'interactive_mode', 'process_prompt', 'get_effective_config', 'show_config_table', 'print_config_json', 'execute_command', 'start_dashboard'):
    if _name in globals():
        setattr(SingularityCLI, _name, globals()[_name])

async def main():
    """Main entry point"""
    # Ensure child Python processes use unbuffered stdout so their prints are readable by parent processes
    os.environ['PYTHONUNBUFFERED'] = '1'

    parser = argparse.ArgumentParser(
        description="Singularity - AI Code Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("prompt", nargs="*", help="Direct prompt (non-interactive)")
    parser.add_argument("-m", "--mode", default="chat", help="Mode to use")
    parser.add_argument("--startup-check-only", action="store_true", help="Start MCP server and exit (used in tests)")
    parser.add_argument("--startup-wait", type=int, default=0, help="When used with --startup-check-only, wait this many seconds before exiting")
    parser.add_argument("--no-startup-config", action="store_true", help="Skip interactive startup configuration prompts (for CI)")
    parser.add_argument("--version", action="version", version="Singularity 1.0.0")

    args = parser.parse_args()

    cli = SingularityCLI()

    # Support early CLI command: `omarchy config show` which should not trigger startup
    if args.prompt and len(args.prompt) >= 2 and args.prompt[0] == 'config' and args.prompt[1] == 'show':
        cli.print_config_json()
        return

    # Ensure MCP server is running for tools
    try:
        await cli.agent.start_mcp_server()
    except Exception:
        console.print("[yellow]Warning: could not start MCP server automatically.[/yellow]")

    # If this invocation only wants to check startup, report the MCP URL and exit (used in tests)
    if args.startup_check_only:
        # Wait up to startup_wait (or 5s default) for the agent to discover the MCP URL
        wait_for = args.startup_wait if (args.startup_wait and args.startup_wait > 0) else 5
        url = getattr(cli.agent, 'mcp_server_url', None)
        start_t = time.time()
        while not url and (time.time() - start_t) < wait_for:
            await asyncio.sleep(0.05)
            url = getattr(cli.agent, 'mcp_server_url', None)

        if url:
            # Use plain print to ensure the message goes to stdout (tests read stdout)
            print(f"Startup check: MCP server at {url}", flush=True)
        else:
            print("Startup check: MCP server started but did not report URL", flush=True)

        if args.startup_wait and args.startup_wait > 0:
            console.print(f"[cyan]Waiting for {args.startup_wait}s before shutdown...[/cyan]")
            try:
                await asyncio.sleep(args.startup_wait)
            except Exception:
                pass
        try:
            await cli.agent.stop_mcp_server()
        except Exception:
            pass
        return

    # Interactive startup configuration (knowledge transfer, auto-apply, sudo)
    if not args.no_startup_config:
        try:
            await cli.startup_config_prompt()
        except Exception as e:
            console.print(f"[yellow]Startup config prompts skipped: {e}[/yellow]")
        # If user asked to wait briefly after configuration, honor that, but continue to the interactive CLI
        if args.startup_wait and args.startup_wait > 0:
            console.print(f"[cyan]Waiting for {args.startup_wait}s before continuing...[/cyan]")
            try:
                await asyncio.sleep(args.startup_wait)
            except Exception:
                pass

    # Check if Ollama is running (skip when environment variable SINGULARITY_SKIP_OLLAMA is set)
    if not os.environ.get('SINGULARITY_SKIP_OLLAMA'):
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                console.print("[red]Ollama is not running. Please start it with: ollama serve[/red]")
                return
        except Exception as e:
            console.print(f"[red]Cannot connect to Ollama: {e}[/red]")
            logger.exception('Cannot connect to Ollama')
            return

    # Direct prompt mode
    if args.prompt:
        prompt = " ".join(args.prompt)
        await cli.process_prompt(prompt, args.mode)
    else:
        # Interactive mode
        try:
            await cli.interactive_mode()
        finally:
            # Ensure we stop MCP server when exiting interactive mode
            try:
                await cli.agent.stop_mcp_server()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
