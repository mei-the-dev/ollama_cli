#!/usr/bin/env python3
"""
Singularity CLI - Next-Generation AI Code Agent
Better than GitHub Copilot CLI and Continue
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Check and install dependencies
try:
    import aiohttp
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.live import Live
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.tree import Tree
except ImportError:
    import subprocess
    print("📦 Installing dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-q",
        "aiohttp", "prompt_toolkit", "rich", "pygments"
    ], check=True)
    # Re-import after installation
    import aiohttp
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.document import Document
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.live import Live
    from rich.syntax import Syntax
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.layout import Layout
    from rich.tree import Tree

console = Console()

# Stunning gradient banner
BANNER = """[bold]
[#FF00FF]   ███████╗██╗███╗   ██╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ ██╗████████╗██╗   ██╗
[#FF33FF]   ██╔════╝██║████╗  ██║██╔════╝ ██║   ██║██║     ██╔══██╗██╔══██╗██║╚══██╔══╝╚██╗ ██╔╝
[#FF66FF]   ███████╗██║██╔██╗ ██║██║  ███╗██║   ██║██║     ███████║██████╔╝██║   ██║    ╚████╔╝ 
[#FF99FF]   ╚════██║██║██║╚██╗██║██║   ██║██║   ██║██║     ██╔══██║██╔══██╗██║   ██║     ╚██╔╝  
[#FFCCFF]   ███████║██║██║ ╚████║╚██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║██║   ██║      ██║   
[#FFFFFF]   ╚══════╝╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝      ╚═╝   
[/bold]
[dim]🚀 Better than GitHub Copilot CLI | Powered by Qwen2.5-Coder 14B[/dim]
"""

# Custom styling
STYLE = Style.from_dict({
    'prompt': '#00ffff bold',
    'mode': '#ff00ff bold',
    'completion-menu': 'bg:#1e1e1e #ffffff',
    'completion-menu.completion': 'bg:#1e1e1e #00ffff',
    'completion-menu.completion.current': 'bg:#00ffff #000000 bold',
})


class WorkspaceIndexer:
    """Fast workspace indexing with smart caching"""
    
    def __init__(self):
        self.files: List[Path] = []
        self.git_files: List[str] = []
        self.file_contents_cache: Dict[str, str] = {}
        self._index_workspace()
    
    def _index_workspace(self):
        """Index workspace files"""
        try:
            # Try git first (faster)
            import subprocess
            result = subprocess.run(
                ['git', 'ls-files'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                self.git_files = [f for f in result.stdout.splitlines() if f]
                self.files = [Path(f) for f in self.git_files[:500]]
                return
        except Exception:
            pass
        
        # Fallback to manual indexing
        cwd = Path.cwd()
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.md', '.txt', '.yaml', '.yml'}
        self.files = []
        
        for ext in extensions:
            try:
                self.files.extend(list(cwd.rglob(f"*{ext}"))[:200])
            except Exception:
                continue
    
    def get_file_content(self, filepath: str) -> Optional[str]:
        """Get file content with caching"""
        if filepath in self.file_contents_cache:
            return self.file_contents_cache[filepath]
        
        try:
            path = Path(filepath)
            if path.exists():
                content = path.read_text()
                self.file_contents_cache[filepath] = content
                return content
        except Exception:
            pass
        return None


class SmartCompleter(Completer):
    """Intelligent autocomplete like Copilot CLI"""
    
    def __init__(self, workspace: WorkspaceIndexer):
        self.workspace = workspace
        self.recent_commands = []
    
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor()
        
        # Command completions
        if text.startswith('/'):
            yield from self._command_completions(word)
        
        # File path completions (@file:)
        elif '@file:' in text or 'in ' in text or 'file ' in text:
            yield from self._file_completions(word)
        
        # Smart intent completions
        else:
            yield from self._intent_completions(text, word)
    
    def _command_completions(self, word: str):
        """Command completions"""
        commands = [
            ("/new", "🔄 Start new conversation"),
            ("/clear", "🧹 Clear screen"),
            ("/files", "📁 List indexed files"),
            ("/search", "🔍 Search code"),
            ("/explain", "💡 Explain code"),
            ("/fix", "🔧 Fix code"),
            ("/test", "🧪 Generate tests"),
            ("/docs", "📚 Generate docs"),
            ("/commit", "💾 Smart git commit"),
            ("/review", "👀 Code review"),
            ("/refactor", "♻️ Refactor code"),
            ("/help", "❓ Show help"),
            ("/exit", "👋 Exit"),
        ]
        
        for cmd, desc in commands:
            if word.lower() in cmd.lower():
                yield Completion(
                    cmd,
                    start_position=-len(word),
                    display=f"{cmd}",
                    display_meta=desc
                )
    
    def _file_completions(self, word: str):
        """File path completions"""
        for filepath in self.workspace.files:
            path_str = str(filepath)
            if word.lower() in path_str.lower():
                # Icon based on file type
                icon = {
                    '.py': '🐍', '.js': '📜', '.ts': '📘',
                    '.json': '📋', '.md': '📝', '.txt': '📄'
                }.get(filepath.suffix, '📄')
                
                yield Completion(
                    path_str,
                    start_position=-len(word),
                    display=f"{icon} {path_str}",
                    display_meta=f"{filepath.stat().st_size // 1024}KB" if filepath.exists() else ""
                )
    
    def _intent_completions(self, text: str, word: str):
        """Smart intent-based completions"""
        intents = [
            # Code generation
            ("create a", "✨ Generate new code"),
            ("write a", "✍️ Write code"),
            ("generate", "🎨 Generate code/files"),
            ("build a", "🏗️ Build application"),
            
            # Code modification
            ("fix", "🔧 Fix code"),
            ("refactor", "♻️ Refactor code"),
            ("optimize", "⚡ Optimize performance"),
            ("add", "➕ Add feature"),
            ("update", "🔄 Update code"),
            
            # Analysis
            ("explain", "💡 Explain code"),
            ("review", "👀 Review code"),
            ("analyze", "🔬 Analyze codebase"),
            ("find bugs", "🐛 Find bugs"),
            ("check", "✅ Check code"),
            
            # Testing
            ("test", "🧪 Generate/run tests"),
            ("debug", "🔍 Debug code"),
            
            # Documentation
            ("document", "📚 Generate docs"),
            ("what is", "❓ Get explanation"),
            ("how to", "💭 Get guidance"),
        ]
        
        for intent, desc in intents:
            if not word or word.lower() in intent.lower():
                yield Completion(
                    intent,
                    start_position=-len(word),
                    display=intent,
                    display_meta=desc
                )


class AIAgent:
    """AI agent with full Ollama and MCP integration"""
    
    def __init__(self):
        self.model = "qwen2.5-coder:14b-instruct-q4_K_M"
        self.conversation_history: List[Dict] = []
        self.mcp_server_url: Optional[str] = None
        self.mcp_process = None
    
    async def start_mcp_server(self):
        """Start MCP server"""
        mcp_paths = [
            Path.home() / ".singularity" / "mcp_server.py",
            Path(__file__).parent / "mcp_server.py",
        ]
        
        mcp_path = None
        for path in mcp_paths:
            if path.exists():
                mcp_path = path
                break
        
        if not mcp_path:
            console.print("[yellow]⚠️  MCP server not found[/yellow]")
            return False
        
        try:
            self.mcp_process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(mcp_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for server URL
            async with asyncio.timeout(5):
                async for line in self.mcp_process.stdout:
                    line_text = line.decode().strip()
                    if "listening on" in line_text.lower():
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', line_text)
                        if match:
                            host, port = match.groups()
                            self.mcp_server_url = f"http://{host}:{port}"
                            return True
        except Exception as e:
            console.print(f"[red]✗ MCP server error: {e}[/red]")
        
        return False
    
    async def stop_mcp_server(self):
        """Stop MCP server"""
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                await self.mcp_process.wait()
            except Exception:
                pass
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call MCP tool"""
        if not self.mcp_server_url:
            return {"status": "ERROR", "error": "MCP server not running"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mcp_server_url}/call",
                    json={"name": tool_name, "arguments": arguments},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def stream_response(self, prompt: str, system: Optional[str] = None):
        """Stream response from Ollama"""
        messages = self.conversation_history.copy()
        if system:
            messages.insert(0, {"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2, "num_ctx": 8192}
        }
        
        full_response = ""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:11434/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
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
        except Exception as e:
            yield f"Error: {e}"
            return
        
        # Update history
        if full_response:
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": full_response})
    
    async def process_with_tools(self, prompt: str) -> Tuple[str, Optional[Dict]]:
        """Process prompt and execute tools if needed"""
        system = """You are a helpful coding assistant with access to tools.
When you need to perform file operations, respond ONLY with a JSON object:
{"tool": "tool_name", "args": {...}}

Available tools:
- write_code: Create/modify files (args: filepath, content)
- read_code: Read file (args: filepath)
- search_files: Search workspace (args: query)
- execute_code: Run commands (args: command)

For conversation, respond naturally without JSON."""
        
        response = ""
        async for chunk in self.stream_response(prompt, system):
            response += chunk
        
        # Check for tool call
        if response.strip().startswith("{"):
            try:
                tool_call = json.loads(response.strip())
                if "tool" in tool_call:
                    result = await self.call_mcp_tool(
                        tool_call["tool"],
                        tool_call.get("args", {})
                    )
                    return response, result
            except:
                pass
        
        return response, None


class SingularityCLI:
    """Ultimate CLI experience"""
    
    def __init__(self):
        self.agent = AIAgent()
        self.workspace = WorkspaceIndexer()
        self.completer = SmartCompleter(self.workspace)
        self.current_mode = "💬 chat"
        
        # Setup prompt session
        history_file = Path.home() / ".singularity" / "history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.kb = KeyBindings()
        self._setup_keybindings()
        
        self.session = PromptSession(
            completer=self.completer,
            style=STYLE,
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=self.kb,
            mouse_support=True,
            complete_while_typing=True,
        )
    
    def _setup_keybindings(self):
        """Setup keyboard shortcuts"""
        
        @self.kb.add('c-space')
        def _(event):
            """Ctrl+Space: Force completion"""
            event.app.current_buffer.start_completion()
        
        @self.kb.add('c-l')
        def _(event):
            """Ctrl+L: Clear screen"""
            console.clear()
            self.show_banner()
    
    def show_banner(self):
        """Show stunning banner"""
        console.print(BANNER)
        
        # Status table
        status = Table.grid(padding=1)
        status.add_column(style="cyan", justify="right")
        status.add_column(style="white")
        
        status.add_row("Model:", f"[green]✓[/green] {self.agent.model.split(':')[0]}")
        status.add_row("Mode:", f"[magenta]{self.current_mode}[/magenta]")
        status.add_row("Files:", f"[yellow]{len(self.workspace.files)}[/yellow]")
        status.add_row("MCP:", "[green]✓[/green]" if self.agent.mcp_server_url else "[yellow]○[/yellow]")
        
        console.print(Panel(
            status,
            title="[bold cyan]Status[/bold cyan]",
            border_style="cyan",
            padding=(0, 2)
        ))
        
        # Quick tips
        console.print(
            "[dim]💡 Tab for autocomplete • Ctrl+Space to force • Ctrl+L to clear • /help for commands[/dim]\n"
        )
    
    async def interactive_mode(self):
        """Main interactive loop"""
        console.clear()
        self.show_banner()
        
        while True:
            try:
                # Beautiful prompt
                prompt_text = HTML(
                    f'<prompt>singularity</prompt> <mode>[{self.current_mode}]</mode> › '
                )
                
                user_input = await self.session.prompt_async(prompt_text)
                
                if not user_input.strip():
                    continue
                
                # Handle commands
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    await self.handle_prompt(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]💡 Press Ctrl+D or type /exit to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    async def handle_command(self, command: str):
        """Handle / commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        handlers = {
            '/exit': self.cmd_exit,
            '/help': self.cmd_help,
            '/new': self.cmd_new,
            '/clear': self.cmd_clear,
            '/files': self.cmd_files,
            '/search': lambda: self.cmd_search(args),
            '/explain': lambda: self.cmd_explain(args),
            '/fix': lambda: self.cmd_fix(args),
            '/test': lambda: self.cmd_test(args),
            '/docs': lambda: self.cmd_docs(args),
            '/commit': self.cmd_commit,
            '/review': lambda: self.cmd_review(args),
        }
        
        handler = handlers.get(cmd)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
            console.print("[yellow]Type /help for available commands[/yellow]")
    
    async def handle_prompt(self, prompt: str):
        """Handle natural language prompts"""
        # Parse context providers
        enhanced_prompt = self._enhance_prompt(prompt)
        
        # Stream response with live display
        with Live(console=console, refresh_per_second=10) as live:
            response = ""
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            frame = 0
            
            async for chunk in self.agent.stream_response(enhanced_prompt):
                response += chunk
                frame = (frame + 1) % len(frames)
                
                # Show streaming response
                live.update(Panel(
                    Markdown(response),
                    title=f"[cyan]{frames[frame]}[/cyan] Generating...",
                    border_style="cyan"
                ))
            
            # Check for tool execution
            tool_result = None
            if response.strip().startswith("{") and "tool" in response:
                live.update(Panel(
                    "[yellow]🔧 Executing tool...[/yellow]",
                    border_style="yellow"
                ))
                
                try:
                    tool_call = json.loads(response.strip())
                    tool_result = await self.agent.call_mcp_tool(
                        tool_call["tool"],
                        tool_call.get("args", {})
                    )
                except:
                    pass
            
            # Final display
            if tool_result and tool_result.get("status") == "SUCCESS":
                console.print(Panel(
                    f"[green]✓[/green] Tool executed\n{json.dumps(tool_result.get('data'), indent=2)}",
                    border_style="green"
                ))
            else:
                live.update(Panel(
                    Markdown(response),
                    title="[green]✓[/green] Complete",
                    border_style="green"
                ))
    
    def _enhance_prompt(self, prompt: str) -> str:
        """Enhance prompt with context providers"""
        enhanced = prompt
        
        # @file: provider
        file_matches = re.findall(r'@file:([^\s]+)', prompt)
        for filepath in file_matches:
            content = self.workspace.get_file_content(filepath)
            if content:
                enhanced += f"\n\n--- {filepath} ---\n{content[:2000]}\n"
        
        # @tree provider
        if '@tree' in prompt:
            tree = self._get_tree()
            enhanced += f"\n\n--- Directory Tree ---\n{tree}\n"
        
        return enhanced
    
    def _get_tree(self) -> str:
        """Get directory tree"""
        tree = Tree("📁 " + Path.cwd().name)
        for file in sorted(self.workspace.files[:30]):
            icon = "📄" if file.is_file() else "📁"
            tree.add(f"{icon} {file.name}")
        return str(tree)
    
    def cmd_exit(self):
        """Exit command"""
        console.print("[yellow]👋 Goodbye! Happy coding![/yellow]")
        raise EOFError
    
    def cmd_help(self):
        """Show help"""
        table = Table(title="Commands", show_header=True, border_style="cyan")
        table.add_column("Command", style="cyan", width=20)
        table.add_column("Description", style="white")
        
        commands = [
            ("/new", "Start new conversation"),
            ("/clear", "Clear screen"),
            ("/files", "List workspace files"),
            ("/search <q>", "Search code"),
            ("/explain <file>", "Explain code"),
            ("/fix <file>", "Fix code issues"),
            ("/test <file>", "Generate tests"),
            ("/docs <file>", "Generate docs"),
            ("/commit", "Smart commit message"),
            ("/review <file>", "Code review"),
            ("/help", "Show this help"),
            ("/exit", "Exit Singularity"),
        ]
        
        for cmd, desc in commands:
            table.add_row(cmd, desc)
        
        console.print(table)
        
        console.print("\n[bold cyan]Context Providers:[/bold cyan]")
        console.print("  [yellow]@file:path[/yellow] - Include file content")
        console.print("  [yellow]@tree[/yellow] - Show directory tree")
        
        console.print("\n[bold cyan]Keyboard Shortcuts:[/bold cyan]")
        console.print("  [yellow]Tab[/yellow] - Autocomplete")
        console.print("  [yellow]Ctrl+Space[/yellow] - Force completion")
        console.print("  [yellow]Ctrl+L[/yellow] - Clear screen")
    
    def cmd_new(self):
        """New conversation"""
        self.agent.conversation_history = []
        console.print("[green]✓[/green] New conversation started")
    
    def cmd_clear(self):
        """Clear screen"""
        console.clear()
        self.show_banner()
    
    def cmd_files(self):
        """List files"""
        table = Table(title="Workspace Files", show_header=True)
        table.add_column("File", style="cyan")
        table.add_column("Size", style="yellow", justify="right")
        
        for file in self.workspace.files[:20]:
            if file.exists():
                size = file.stat().st_size // 1024
                table.add_row(str(file), f"{size}KB")
        
        console.print(table)
    
    async def cmd_search(self, query: str):
        """Search code"""
        if not query:
            console.print("[red]Usage: /search <query>[/red]")
            return
        
        result = await self.agent.call_mcp_tool("search_files", {"query": query})
        
        if result.get("status") == "SUCCESS":
            matches = result.get("data", {}).get("matches", [])
            for match in matches[:10]:
                console.print(f"[cyan]{match['file']}:{match['line']}[/cyan] {match['content']}")
        else:
            console.print("[yellow]No matches found[/yellow]")
    
    async def cmd_explain(self, filepath: str):
        """Explain code"""
        if not filepath:
            console.print("[red]Usage: /explain <file>[/red]")
            return
        
        content = self.workspace.get_file_content(filepath)
        if content:
            await self.handle_prompt(f"Explain this code:\n\n{content[:3000]}")
        else:
            console.print(f"[red]File not found: {filepath}[/red]")
    
    async def cmd_fix(self, filepath: str):
        """Fix code"""
        if not filepath:
            console.print("[red]Usage: /fix <file>[/red]")
            return
        
        await self.handle_prompt(f"Find and fix issues in @file:{filepath}")
    
    async def cmd_test(self, filepath: str):
        """Generate tests"""
        if not filepath:
            console.print("[red]Usage: /test <file>[/red]")
            return
        
        await self.handle_prompt(f"Generate comprehensive tests for @file:{filepath}")
    
    async def cmd_docs(self, filepath: str):
        """Generate docs"""
        if not filepath:
            console.print("[red]Usage: /docs <file>[/red]")
            return
        
        await self.handle_prompt(f"Generate documentation for @file:{filepath}")
    
    async def cmd_commit(self):
        """Smart commit"""
        import subprocess
        try:
            result = subprocess.run(['git', 'diff', '--cached'], capture_output=True, text=True)
            diff = result.stdout
            if diff:
                await self.handle_prompt(f"Generate a concise git commit message for these changes:\n\n{diff[:2000]}")
            else:
                console.print("[yellow]No staged changes[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def cmd_review(self, filepath: str):
        """Code review"""
        if not filepath:
            console.print("[red]Usage: /review <file>[/red]")
            return
        
        await self.handle_prompt(f"Perform a detailed code review of @file:{filepath}")


async def main():
    """Main entry point"""
    # Check Ollama
    import subprocess
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
    with console.status("[cyan]🚀 Starting MCP server...[/cyan]"):
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