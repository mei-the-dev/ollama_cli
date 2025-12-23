#!/usr/bin/env python3
"""
Singularity CLI - Production Ready
Beautiful AI Code Agent with Full MCP Integration
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import aiohttp
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.live import Live
    from rich.syntax import Syntax
except ImportError:
    print("📦 Installing dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "aiohttp", "prompt_toolkit", "rich"
    ], check=True)
    import aiohttp
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.live import Live
    from rich.syntax import Syntax

console = Console()

BANNER = """[bold magenta]
   ███████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ ██╗████████╗██╗   ██╗
   ██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
   ███████╗██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║██████╔╝██║   ██║    ╚████╔╝ 
   ╚════██║██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║██╔══██╗██║   ██║     ╚██╔╝  
   ███████║██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║██║   ██║      ██║   
   ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   
[/bold magenta]
[dim]🚀 Production-Ready AI Code Agent | Powered by Qwen2.5-Coder[/dim]
"""

custom_style = Style.from_dict({
    'prompt': '#00ffff bold',
    'mode': '#ff00ff',
})


class SmartCompleter(Completer):
    """Intelligent autocomplete"""

    def __init__(self):
        self.workspace_files = self._index_workspace()

    def _index_workspace(self) -> List[str]:
        """Index workspace files"""
        try:
            cwd = Path.cwd()
            files = []
            for ext in ['.py', '.js', '.ts', '.json', '.md', '.txt']:
                files.extend([str(f.relative_to(cwd)) for f in cwd.rglob(f"*{ext}")])
            return files[:200]
        except Exception:
            return []

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor()

        # Command completions
        if text.startswith('/'):
            commands = [
                ("/mode", "Switch mode"),
                ("/new", "New conversation"),
                ("/exec", "Execute command"),
                ("/search", "Search workspace"),
                ("/help", "Show help"),
                ("/exit", "Exit"),
            ]
            for cmd, desc in commands:
                if word.lower() in cmd.lower():
                    yield Completion(cmd, start_position=-len(word), display_meta=desc)

        # File completions for @file:
        elif '@file:' in text:
            for filepath in self.workspace_files:
                if word.lower() in filepath.lower():
                    yield Completion(
                        filepath,
                        start_position=-len(word),
                        display_meta=f"📄 {filepath}"
                    )


class SingularityAgent:
    """AI Agent with Ollama and MCP integration"""

    def __init__(self):
        self.model = "qwen2.5-coder:14b-instruct-q4_K_M"
        self.conversation_history = []
        self.mcp_server_url = None
        self.mcp_process = None

    async def start_mcp_server(self):
        """Start MCP server and capture URL"""
        try:
            mcp_path = Path.home() / ".singularity" / "mcp_server.py"
            if not mcp_path.exists():
                # Try current directory
                mcp_path = Path(__file__).parent / "mcp_server.py"
            
            if not mcp_path.exists():
                console.print("[yellow]⚠️  MCP server not found at ~/.singularity/mcp_server.py[/yellow]")
                return False

            # Start server
            self.mcp_process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(mcp_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for server to announce URL (max 5 seconds)
            try:
                async with asyncio.timeout(5):
                    async for line in self.mcp_process.stdout:
                        line_text = line.decode().strip()
                        if "listening on" in line_text.lower():
                            # Parse: "MCP server listening on 127.0.0.1:12345"
                            match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', line_text)
                            if match:
                                host, port = match.groups()
                                self.mcp_server_url = f"http://{host}:{port}"
                                console.print(f"[green]✓[/green] MCP server started at {self.mcp_server_url}")
                                return True
            except asyncio.TimeoutError:
                console.print("[yellow]⚠️  MCP server started but URL not captured[/yellow]")
                return False

        except Exception as e:
            console.print(f"[red]✗ Failed to start MCP server: {e}[/red]")
            return False

    async def stop_mcp_server(self):
        """Stop MCP server"""
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                await self.mcp_process.wait()
                console.print("[yellow]MCP server stopped[/yellow]")
            except Exception:
                pass

    async def call_mcp_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call MCP tool via HTTP"""
        if not self.mcp_server_url:
            return {"error": "MCP server not running"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mcp_server_url}/call",
                    json={"name": tool_name, "arguments": arguments},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def generate_streaming(self, prompt: str, system: Optional[str] = None):
        """Generate streaming response from Ollama"""
        messages = self.conversation_history.copy()
        if system:
            messages.insert(0, {"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2}
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:11434/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    full_response = ""
                    
                    async for line in resp.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode())
                                if "message" in chunk:
                                    content = chunk["message"].get("content", "")
                                    if content:
                                        full_response += content
                                        yield content
                                
                                if chunk.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue

                    # Update history
                    self.conversation_history.append({"role": "user", "content": prompt})
                    self.conversation_history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            yield f"Error: {e}"

    async def process_with_tools(self, prompt: str) -> str:
        """Process prompt and detect tool usage"""
        # Build system prompt that instructs model to use tools
        system = """You are a helpful coding assistant with access to tools.
When you need to perform actions, respond with a JSON object containing:
{"tool": "tool_name", "args": {...}}

Available tools:
- write_code: Create/modify files (args: filepath, content)
- read_code: Read file contents (args: filepath)
- search_files: Search workspace (args: query, path)
- execute_code: Run shell commands (args: command)
- git_operation: Git commands (args: operation, args)

For normal conversation, respond naturally without JSON."""

        response = ""
        async for chunk in self.generate_streaming(prompt, system):
            response += chunk

        # Check if response contains tool call
        if response.strip().startswith("{") and "tool" in response:
            try:
                tool_call = json.loads(response.strip())
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})

                # Execute tool
                result = await self.call_mcp_tool(tool_name, tool_args)

                # Format result
                if result.get("status") == "SUCCESS":
                    data = result.get("data", {})
                    return f"✓ Executed {tool_name}\n{json.dumps(data, indent=2)}"
                else:
                    return f"✗ Tool error: {result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"✗ Failed to parse tool call: {e}"

        return response


class SingularityCLI:
    """Production-ready CLI"""

    def __init__(self):
        self.agent = SingularityAgent()
        self.completer = SmartCompleter()
        self.current_mode = "chat"
        
        # Setup prompt session
        history_file = Path.home() / ".singularity" / "history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        self.session = PromptSession(
            completer=self.completer,
            style=custom_style,
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
        )

    def show_banner(self):
        """Display banner"""
        console.clear()
        console.print(BANNER)
        
        status = Table.grid(padding=1)
        status.add_column(style="cyan", justify="right")
        status.add_column(style="white")
        status.add_row("Model:", f"[green]✓[/green] {self.agent.model}")
        status.add_row("Mode:", f"[magenta]{self.current_mode}[/magenta]")
        status.add_row("MCP:", f"[green]✓[/green] Connected" if self.agent.mcp_server_url else "[yellow]Starting...[/yellow]")
        
        console.print(Panel(status, title="[bold cyan]Status[/bold cyan]", border_style="cyan"))
        console.print("[dim]Type /help for commands • Press Tab for autocomplete[/dim]\n")

    async def interactive_mode(self):
        """Main interactive loop"""
        self.show_banner()

        while True:
            try:
                prompt_text = HTML(f'<prompt>singularity</prompt> <mode>[{self.current_mode}]</mode> › ')
                user_input = await self.session.prompt_async(prompt_text)

                if not user_input.strip():
                    continue

                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    await self.handle_prompt(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]💡 Use /exit to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    async def handle_command(self, command: str):
        """Handle / commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if cmd == '/exit':
            console.print("[yellow]👋 Goodbye![/yellow]")
            raise EOFError
        elif cmd == '/help':
            self.show_help()
        elif cmd == '/mode':
            await self.cmd_mode(args)
        elif cmd == '/new':
            self.agent.conversation_history = []
            console.print("[green]✓[/green] New conversation started")
        elif cmd == '/exec':
            await self.cmd_exec(args)
        elif cmd == '/search':
            await self.cmd_search(args)
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")

    async def handle_prompt(self, prompt: str):
        """Handle natural language prompts"""
        # Parse context providers
        enhanced_prompt = await self.parse_context(prompt)

        # Stream response with live display
        with Live(console=console, refresh_per_second=10) as live:
            response = ""
            frame = 0
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

            async for chunk in self.agent.generate_streaming(enhanced_prompt):
                response += chunk
                frame = (frame + 1) % len(frames)

                live.update(Panel(
                    Markdown(response),
                    title=f"[cyan]{frames[frame]}[/cyan] Thinking...",
                    border_style="cyan"
                ))

            # Check for tool calls in final response
            if response.strip().startswith("{") and "tool" in response:
                live.update(Panel(
                    "[yellow]🔧 Executing tool...[/yellow]",
                    border_style="yellow"
                ))
                
                try:
                    tool_call = json.loads(response.strip())
                    result = await self.agent.call_mcp_tool(
                        tool_call["tool"],
                        tool_call.get("args", {})
                    )
                    
                    if result.get("status") == "SUCCESS":
                        console.print(Panel(
                            f"[green]✓[/green] Tool executed: {tool_call['tool']}\n{json.dumps(result.get('data'), indent=2)}",
                            border_style="green"
                        ))
                    else:
                        console.print(Panel(
                            f"[red]✗[/red] Tool failed: {result.get('error')}",
                            border_style="red"
                        ))
                except Exception as e:
                    console.print(f"[red]Tool execution error: {e}[/red]")
            else:
                live.update(Panel(
                    Markdown(response),
                    title="[green]✓[/green] Complete",
                    border_style="green"
                ))

    async def parse_context(self, prompt: str) -> str:
        """Parse @file: and other context providers"""
        enhanced = prompt

        # @file: provider
        file_matches = re.findall(r'@file:([^\s]+)', prompt)
        for filepath in file_matches:
            try:
                path = Path(filepath)
                if path.exists():
                    content = path.read_text()
                    enhanced += f"\n\n--- Content of {filepath} ---\n{content[:2000]}\n"
            except Exception:
                pass

        # @tree provider
        if '@tree' in prompt:
            try:
                tree_output = subprocess.run(
                    ['ls', '-R'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                enhanced += f"\n\n--- Directory Tree ---\n{tree_output.stdout[:1000]}\n"
            except Exception:
                pass

        return enhanced

    def show_help(self):
        """Show help"""
        table = Table(title="Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")

        commands = [
            ("/mode <n>", "Switch mode"),
            ("/new", "New conversation"),
            ("/exec <cmd>", "Execute shell command"),
            ("/search <q>", "Search workspace"),
            ("/help", "Show this help"),
            ("/exit", "Exit Singularity"),
        ]

        for cmd, desc in commands:
            table.add_row(cmd, desc)

        console.print(table)
        console.print("\n[cyan]Context Providers:[/cyan]")
        console.print("  @file:path - Include file content")
        console.print("  @tree - Show directory structure")

    async def cmd_mode(self, mode: str):
        """Switch mode"""
        if mode in ["chat", "code", "plan", "review", "debug"]:
            self.current_mode = mode
            console.print(f"[green]✓[/green] Switched to [magenta]{mode}[/magenta] mode")
        else:
            console.print("[yellow]Available modes: chat, code, plan, review, debug[/yellow]")

    async def cmd_exec(self, cmd: str):
        """Execute command"""
        if not cmd:
            console.print("[red]Usage: /exec <command>[/red]")
            return

        result = await self.agent.call_mcp_tool("execute_code", {"command": cmd})
        
        if result.get("status") == "SUCCESS":
            data = result.get("data", {})
            if data.get("stdout"):
                console.print(Panel(data["stdout"], title="Output", border_style="green"))
            if data.get("stderr"):
                console.print(Panel(data["stderr"], title="Errors", border_style="red"))
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")

    async def cmd_search(self, query: str):
        """Search workspace"""
        if not query:
            console.print("[red]Usage: /search <query>[/red]")
            return

        result = await self.agent.call_mcp_tool("search_files", {"query": query})
        
        if result.get("status") == "SUCCESS":
            matches = result.get("data", {}).get("matches", [])
            if matches:
                for match in matches[:10]:
                    console.print(f"[cyan]{match['file']}:{match['line']}[/cyan] {match['content']}")
            else:
                console.print("[yellow]No matches found[/yellow]")
        else:
            console.print(f"[red]Error: {result.get('error')}[/red]")


async def main():
    """Main entry point"""
    # Check Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=2
        )
        if result.returncode != 0:
            console.print("[red]❌ Ollama not running. Start with: ollama serve[/red]")
            return
    except Exception:
        console.print("[red]❌ Cannot connect to Ollama[/red]")
        return

    cli = SingularityCLI()

    # Start MCP server
    console.print("[cyan]🚀 Starting MCP server...[/cyan]")
    await cli.agent.start_mcp_server()

    try:
        await cli.interactive_mode()
    except EOFError:
        pass
    finally:
        await cli.agent.stop_mcp_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")