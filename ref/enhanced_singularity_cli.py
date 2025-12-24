#!/usr/bin/env python3
"""
Singularity CLI v2.0 - Continue.dev Inspired
Modern coding assistant with session management, permission system, and beautiful TUI
"""

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Install dependencies
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter, FuzzyCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.prompt import Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.tree import Tree
except ImportError:
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "prompt_toolkit", "rich"], check=True)
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter, FuzzyCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.styles import Style
    from rich.console import Console
    from rich.live import Live
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.prompt import Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.tree import Tree

console = Console()

# Logging
logger = logging.getLogger("singularity")
if not logger.handlers:
    try:
        log_dir = Path.home() / ".singularity" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "singularity.log")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)
        logger.setLevel(logging.INFO)
    except Exception:
        pass

# Fixed ASCII Art
BANNER = """[bold cyan]
   _____ _                 __           _ __       
  / ___/(_)___  ____ _____/ /___ ______(_) /___  __
  \__ \/ / __ \/ __ `/ __  / __ `/ ___/ / __/ / / /
 ___/ / / / / / /_/ / /_/ / /_/ / /  / / /_/ /_/ / 
/____/_/_/ /_/\__, /\__,_/\__,_/_/  /_/\__/\__, /  
             /____/                       /____/   
[/bold cyan][bold magenta]    Continuous AI Code Agent • Powered by Ollama[/bold magenta]
"""

PT_STYLE = Style.from_dict({
    'completion-menu.completion': 'bg:#0066cc #ffffff bold',
    'completion-menu.completion.current': 'bg:#00aaff #000000 bold',
    'completion-menu.meta.completion': 'bg:#004488 #aaaaaa italic',
    'completion-menu.meta.completion.current': 'bg:#0088cc #ffffff italic',
    'scrollbar.background': 'bg:#003366',
    'scrollbar.button': 'bg:#00aaff',
    'bottom-toolbar': 'bg:#222222 #00aaff',
    'bottom-toolbar.text': '#ffffff',
    'prompt': 'cyan bold',
})


@dataclass
class Session:
    """Session metadata"""
    id: str
    name: Optional[str]
    created: str
    last_activity: str
    cwd: str
    messages: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ToolCall:
    """Tool execution request"""
    tool: str
    args: Dict
    requires_approval: bool = True
    approved: bool = False


class PermissionManager:
    """Manage tool permissions like Continue.dev"""
    
    def __init__(self):
        self.allowed_patterns = set()
        self.always_ask_patterns = set()
        self.config_file = Path.home() / ".singularity" / "permissions.json"
        self.load()
    
    def load(self):
        """Load saved permissions"""
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text())
                self.allowed_patterns = set(data.get("allowed", []))
                self.always_ask_patterns = set(data.get("ask", []))
            except:
                pass
    
    def save(self):
        """Save permissions"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps({
            "allowed": list(self.allowed_patterns),
            "ask": list(self.always_ask_patterns)
        }, indent=2))
    
    def check(self, tool: str, args: Dict) -> bool:
        """Check if tool execution is allowed"""
        # Check allowed patterns
        for pattern in self.allowed_patterns:
            if self._matches(pattern, tool, args):
                return True
        
        # Check ask patterns
        for pattern in self.always_ask_patterns:
            if self._matches(pattern, tool, args):
                return False
        
        # Default: ask for approval
        return False
    
    def _matches(self, pattern: str, tool: str, args: Dict) -> bool:
        """Check if pattern matches tool call"""
        if pattern == tool:
            return True
        if pattern.endswith("*") and tool.startswith(pattern[:-1]):
            return True
        # Pattern like "write_code(*.py)"
        if "(" in pattern:
            tool_pattern, arg_pattern = pattern.split("(", 1)
            arg_pattern = arg_pattern.rstrip(")")
            if tool == tool_pattern:
                if "*" in arg_pattern:
                    return True
                # Check filepath patterns
                if "filepath" in args:
                    import fnmatch
                    return fnmatch.fnmatch(args["filepath"], arg_pattern)
        return False
    
    def add_allowed(self, pattern: str):
        """Add allowed pattern"""
        self.allowed_patterns.add(pattern)
        self.save()
    
    def add_ask(self, pattern: str):
        """Add ask pattern"""
        self.always_ask_patterns.add(pattern)
        self.save()


class SessionManager:
    """Manage conversation sessions"""
    
    def __init__(self):
        self.sessions_dir = Path.home() / ".singularity" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[Session] = None
    
    def create(self, name: Optional[str] = None) -> Session:
        """Create new session"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session = Session(
            id=session_id,
            name=name,
            created=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            cwd=str(Path.cwd())
        )
        self.current_session = session
        self.save(session)
        return session
    
    def save(self, session: Session):
        """Save session to disk"""
        session.last_activity = datetime.now().isoformat()
        path = self.sessions_dir / f"{session.id}.json"
        path.write_text(json.dumps({
            "id": session.id,
            "name": session.name,
            "created": session.created,
            "last_activity": session.last_activity,
            "cwd": session.cwd,
            "messages": session.messages,
            "metadata": session.metadata
        }, indent=2))
    
    def load(self, session_id: str) -> Optional[Session]:
        """Load session from disk"""
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            session = Session(**data)
            self.current_session = session
            return session
        except:
            return None
    
    def list(self, limit: int = 20) -> List[Session]:
        """List recent sessions"""
        sessions = []
        for path in sorted(self.sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                data = json.loads(path.read_text())
                sessions.append(Session(**data))
            except:
                continue
        return sessions
    
    def get_last(self) -> Optional[Session]:
        """Get most recent session"""
        sessions = self.list(limit=1)
        return sessions[0] if sessions else None


class EnhancedCompleter(Completer):
    """Enhanced autocomplete with fuzzy search"""
    
    def __init__(self, cli_instance):
        self.cli = cli_instance
        self.path_completer = PathCompleter(expanduser=True)
        
        self.commands = {
            "/help": ("Show complete guide", "/help"),
            "/exit": ("Exit Singularity", "/exit"),
            "/new": ("New session", "/new"),
            "/resume": ("Resume last session", "/resume"),
            "/sessions": ("List all sessions", "/sessions"),
            "/save": ("Save current session", "/save mysession"),
            "/mode": ("Switch mode", "/mode code"),
            "/cd": ("Change directory", "/cd src"),
            "/files": ("Show file tree", "/files"),
            "/git": ("Git operations", "/git status"),
            "/allow": ("Add permission", "/allow write_code(*.py)"),
            "/ask": ("Require approval", "/ask execute_code"),
            "/config": ("Show settings", "/config"),
            "/export": ("Export session", "/export"),
        }
        
        self.quick_actions = {
            "!": ("Run shell command", "!ls -la"),
            "@": ("Reference file", "@file:app.py"),
            "explain": ("Explain code", "explain @file:utils.py"),
            "write": ("Write code", "write a REST API"),
            "fix": ("Fix bugs", "fix @file:broken.py"),
            "test": ("Generate tests", "test @file:utils.py"),
            "review": ("Code review", "review @file:main.py"),
        }
    
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)
        line = text.split('\n')[-1]
        
        # Shell command
        if line.startswith('!'):
            return
        
        # File reference
        if '@file:' in line:
            at_pos = line.rfind('@file:')
            path_part = line[at_pos + 6:]
            from prompt_toolkit.document import Document
            path_doc = Document(path_part, len(path_part))
            for comp in self.path_completer.get_completions(path_doc, complete_event):
                yield Completion(
                    comp.text,
                    start_position=comp.start_position,
                    display=comp.display,
                    display_meta="📄 file"
                )
            return
        
        # @ symbol - show context providers
        if line.endswith('@') or line.endswith(' @'):
            for provider in ["@file:", "@dir:", "@web:", "@git:", "@clipboard"]:
                desc = {"@file:": "Reference file", "@dir:": "Reference directory",
                        "@web:": "Search web", "@git:": "Git context", "@clipboard": "Clipboard"}
                yield Completion(
                    provider,
                    start_position=-1,
                    display=provider,
                    display_meta=desc.get(provider, "")
                )
            return
        
        # / commands
        if line.startswith('/'):
            for cmd, (desc, example) in self.commands.items():
                if cmd.startswith(line):
                    yield Completion(
                        cmd + ' ',
                        start_position=-len(line),
                        display=cmd,
                        display_meta=f"{desc} • {example}"
                    )
            return
        
        # Quick actions
        if not line.startswith('/'):
            for action, (desc, example) in self.quick_actions.items():
                if action.startswith(word.lower()) and word:
                    yield Completion(
                        action + ' ',
                        start_position=-len(word),
                        display=action,
                        display_meta=f"{desc} • {example}"
                    )


class SingularityAgent:
    """AI agent with Ollama integration"""
    
    def __init__(self):
        self.model = os.environ.get("SINGULARITY_MODEL", "qwen2.5-coder:14b")
        self.mcp_server_url = None
        self.mcp_process = None
        self.cwd = Path.cwd()
    
    async def start_mcp_server(self) -> bool:
        """Start MCP server"""
        try:
            mcp_path = Path(__file__).parent / "mcp_server.py"
            if not mcp_path.exists():
                return False
            
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(mcp_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.mcp_process = proc
            
            start = time.time()
            while time.time() - start < 5:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=0.2)
                    if line:
                        text = line.decode().strip()
                        if "listening on" in text.lower():
                            match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', text)
                            if match:
                                host, port = match.groups()
                                self.mcp_server_url = f"http://{host}:{port}"
                                return True
                except asyncio.TimeoutError:
                    continue
            return False
        except:
            return False
    
    async def stop_mcp_server(self):
        """Stop MCP server"""
        if self.mcp_process:
            try:
                self.mcp_process.terminate()
                await asyncio.wait_for(self.mcp_process.wait(), timeout=3.0)
            except:
                self.mcp_process.kill()
            self.mcp_process = None
    
    async def call_tool(self, tool: str, args: Dict) -> Dict:
        """Call MCP tool"""
        if not self.mcp_server_url:
            return {"status": "ERROR", "error": "MCP not running"}
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mcp_server_url}/call",
                    json={"name": tool, "arguments": args},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def generate(self, prompt: str, system: Optional[str] = None):
        """Generate response from Ollama"""
        try:
            import aiohttp
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"], check=True)
            import aiohttp
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.2}
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
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                if content:
                                    full_response += content
                                    yield content
                        except:
                            continue
        except Exception as e:
            yield f"Error: {e}"


class SingularityCLI:
    """Main CLI application"""
    
    def __init__(self, headless: bool = False):
        self.agent = SingularityAgent()
        self.sessions = SessionManager()
        self.permissions = PermissionManager()
        self.headless = headless
        self.current_mode = "chat"
        self.pending_tool_calls: List[ToolCall] = []
        
        self.modes = {
            "chat": "💬 Interactive conversation",
            "code": "⚡ Code generation",
            "review": "🔍 Code review",
            "test": "🧪 Test generation",
        }
    
    def setup_key_bindings(self) -> KeyBindings:
        """Setup keyboard shortcuts"""
        kb = KeyBindings()
        
        @kb.add('c-x', 'c-s')
        def _(event):
            """Ctrl+X Ctrl+S - Save session"""
            event.app.exit(result='/save')
        
        @kb.add('c-x', 'c-r')
        def _(event):
            """Ctrl+X Ctrl+R - Resume session"""
            event.app.exit(result='/resume')
        
        @kb.add('c-x', 'c-l')
        def _(event):
            """Ctrl+X Ctrl+L - List sessions"""
            event.app.exit(result='/sessions')
        
        return kb
    
    def get_git_info(self) -> Dict:
        """Get git repository info"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=self.agent.cwd, timeout=1
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True, text=True, cwd=self.agent.cwd, timeout=1
                )
                dirty = bool(status.stdout.strip())
                return {"branch": branch, "dirty": dirty, "repo": True}
        except:
            pass
        return {"repo": False}
    
    def show_banner(self):
        """Show banner with session info"""
        console.clear()
        
        git_info = self.get_git_info()
        git_status = ""
        if git_info["repo"]:
            branch = git_info["branch"]
            dirty = " [red]●[/red]" if git_info["dirty"] else " [green]✓[/green]"
            git_status = f"[dim]git:[/dim][cyan]{branch}[/cyan]{dirty}"
        
        cwd_str = str(self.agent.cwd).replace(str(Path.home()), "~")
        
        session_info = ""
        if self.sessions.current_session:
            s = self.sessions.current_session
            name = s.name or s.id
            session_info = f"[bold]Session:[/bold] [yellow]{name}[/yellow]\n"
        
        info = (
            f"{session_info}"
            f"[bold]Directory:[/bold] [cyan]{cwd_str}[/cyan]\n"
            f"[bold]Model:[/bold] [yellow]{self.agent.model}[/yellow]\n"
            f"[bold]Mode:[/bold] [magenta]{self.current_mode}[/magenta]\n"
        )
        if git_status:
            info += f"[bold]Repository:[/bold] {git_status}\n"
        
        quick_start = Panel(
            "[bold green]⚡ Quick Start[/bold green]\n\n"
            "• [yellow]@[/yellow] = Context providers\n"
            "• [yellow]/[/yellow] = Commands\n"
            "• [yellow]![/yellow] = Shell commands\n"
            "• [yellow]Ctrl+X Ctrl+S[/yellow] = Save session\n"
            "• [yellow]Ctrl+X Ctrl+R[/yellow] = Resume\n\n"
            "[dim]Type /help for complete guide[/dim]",
            border_style="green",
            padding=(1, 2)
        )
        
        console.print(Panel(BANNER, border_style="cyan", padding=(0, 2)))
        console.print(Panel(info, border_style="blue", padding=(1, 2)))
        console.print(quick_start)
        console.print()
    
    async def request_approval(self, tool_call: ToolCall) -> bool:
        """Request user approval for tool execution"""
        console.print()
        console.print(Panel(
            f"[bold yellow]Tool Approval Required[/bold yellow]\n\n"
            f"[cyan]Tool:[/cyan] {tool_call.tool}\n"
            f"[cyan]Arguments:[/cyan]\n{json.dumps(tool_call.args, indent=2)}\n\n"
            f"[dim]Approve this action?[/dim]",
            border_style="yellow",
            padding=(1, 2)
        ))
        
        choice = Confirm.ask("Approve?", default=False)
        console.print()
        return choice
    
    async def process_message(self, message: str) -> str:
        """Process user message and handle tool calls"""
        # Extract file references
        files = re.findall(r'@file:([^\s]+)', message)
        context = []
        
        for file_path in files:
            try:
                path = self.agent.cwd / file_path
                if path.exists():
                    content = path.read_text()[:2000]
                    context.append(f"File {file_path}:\n```\n{content}\n```")
            except:
                pass
        
        git_info = self.get_git_info()
        system = f"""You are a coding assistant.
Directory: {self.agent.cwd}
{f'Git: {git_info["branch"]}' if git_info["repo"] else ''}
Mode: {self.current_mode}

When you need to execute tools, output JSON:
{{"tool": "tool_name", "args": {{...}}}}

Available tools: write_code, read_code, execute_code, git_operation"""
        
        if context:
            system += f"\n\nContext:\n" + "\n".join(context)
        
        full_response = ""
        with Live(console=console, refresh_per_second=10) as live:
            response_text = ""
            async for chunk in self.agent.generate(message, system=system):
                response_text += chunk
                live.update(Panel(
                    Markdown(response_text),
                    title="[bold cyan]Singularity[/bold cyan]",
                    border_style="cyan"
                ))
                full_response = response_text
        
        # Check for tool calls
        try:
            if "{" in full_response and "tool" in full_response:
                json_str = full_response[full_response.find("{"):full_response.rfind("}")+1]
                obj = json.loads(json_str)
                if "tool" in obj and "args" in obj:
                    tool_call = ToolCall(
                        tool=obj["tool"],
                        args=obj["args"],
                        requires_approval=not self.permissions.check(obj["tool"], obj["args"])
                    )
                    
                    if tool_call.requires_approval:
                        if await self.request_approval(tool_call):
                            result = await self.agent.call_tool(tool_call.tool, tool_call.args)
                            console.print(Panel(
                                f"[green]✓[/green] Tool executed\n\n{json.dumps(result, indent=2)}",
                                border_style="green"
                            ))
                    else:
                        result = await self.agent.call_tool(tool_call.tool, tool_call.args)
                        console.print(Panel(
                            f"[green]✓[/green] Auto-approved\n\n{json.dumps(result, indent=2)}",
                            border_style="green"
                        ))
        except:
            pass
        
        return full_response
    
    async def interactive_mode(self):
        """Main interactive TUI"""
        self.show_banner()
        
        # Create or resume session
        if not self.sessions.current_session:
            self.sessions.create()
        
        history_file = Path.home() / ".singularity" / "history.txt"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        def get_toolbar():
            git = self.get_git_info()
            git_text = f"[{git['branch']} {'●' if git['dirty'] else '✓'}]" if git["repo"] else ""
            return [
                ('class:bottom-toolbar', ' 💡 '),
                ('class:bottom-toolbar.text', '@ = context • / = commands • ! = shell • Ctrl+X = shortcuts'),
                ('class:bottom-toolbar', f'  {git_text}' if git_text else ''),
            ]
        
        session = PromptSession(
            history=FileHistory(str(history_file)),
            completer=EnhancedCompleter(self),
            style=PT_STYLE,
            complete_while_typing=True,
            complete_in_thread=True,
            bottom_toolbar=get_toolbar,
            key_bindings=self.setup_key_bindings(),
            mouse_support=True,
        )
        
        while True:
            try:
                git = self.get_git_info()
                git_part = f"({git['branch']} {'●' if git['dirty'] else '✓'}) " if git["repo"] else ""
                cwd_short = self.agent.cwd.name or "/"
                
                from prompt_toolkit.formatted_text import HTML
                prompt_html = HTML(
                    f'<prompt>singularity</prompt> '
                    f'<cyan>{git_part}</cyan>'
                    f'<b><cyan>{cwd_short}</cyan></b> › '
                )
                
                user_input = await asyncio.to_thread(
                    session.prompt,
                    prompt_html,
                    refresh_interval=0.5
                )
                
                if not user_input.strip():
                    continue
                
                # Commands
                if user_input.startswith('/'):
                    result = await self.handle_command(user_input)
                    if result == "EXIT":
                        break
                # Shell commands
                elif user_input.startswith('!'):
                    await self.run_shell_command(user_input[1:])
                # AI conversation
                else:
                    response = await self.process_message(user_input)
                    if self.sessions.current_session:
                        self.sessions.current_session.messages.append({
                            "role": "user",
                            "content": user_input
                        })
                        self.sessions.current_session.messages.append({
                            "role": "assistant",
                            "content": response
                        })
                        self.sessions.save(self.sessions.current_session)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]💡 Ctrl+D or /exit to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.exception("Error in interactive loop")
    
    async def run_shell_command(self, cmd: str):
        """Execute shell command"""
        console.print(f"[dim]$ {cmd}[/dim]")
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=self.agent.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            
            if stdout:
                console.print(stdout.decode())
            if stderr:
                console.print(f"[red]{stderr.decode()}[/red]")
        except asyncio.TimeoutError:
            console.print("[red]Command timed out[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    async def handle_command(self, cmd: str) -> Optional[str]:
        """Handle slash commands"""
        parts = cmd.split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        
        if command == "/exit":
            console.print("[yellow]Goodbye! 👋[/yellow]")
            return "EXIT"
        
        elif command == "/new":
            self.sessions.create(args if args else None)
            console.print("[green]✓[/green] New session created")
        
        elif command == "/resume":
            if args:
                session = self.sessions.load(args)
            else:
                session = self.sessions.get_last()
            
            if session:
                console.print(f"[green]✓[/green] Resumed: {session.name or session.id}")
            else:
                console.print("[red]Session not found[/red]")
        
        elif command == "/sessions":
            sessions = self.sessions.list()
            table = Table(title="Recent Sessions")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="yellow")
            table.add_column("Last Activity", style="dim")
            table.add_column("Messages", style="green")
            
            for s in sessions:
                table.add_row(
                    s.id[:16],
                    s.name or "-",
                    s.last_activity[:16],
                    str(len(s.messages))
                )
            console.print(table)
        
        elif command == "/save":
            if self.sessions.current_session and args:
                self.sessions.current_session.name = args
                self.sessions.save(self.sessions.current_session)
                console.print(f"[green]✓[/green] Saved as: {args}")
        
        elif command == "/cd":
            if args:
                try:
                    new_path = (self.agent.cwd / args).resolve()
                    if new_path.is_dir():
                        self.agent.cwd = new_path
                        os.chdir(new_path)
                        console.print(f"[green]✓[/green] [cyan]{new_path}[/cyan]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
        
        elif command == "/allow":
            if args:
                self.permissions.add_allowed(args)
                console.print(f"[green]✓[/green] Added to allowed: {args}")
        
        elif command == "/ask":
            if args:
                self.permissions.add_ask(args)
                console.print(f"[green]✓[/green] Will ask for: {args}")
        
        elif command == "/config":
            config = {
                "model": self.agent.model,
                "cwd": str(self.agent.cwd),
                "mode": self.current_mode,
                "session": self.sessions.current_session.id if self.sessions.current_session else None,
            }
            table = Table(title="Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")
            for k, v in config.items():
                table.add_row(k, str(v))
            console.print(table)
        
        else:
            console.print(f"[red]Unknown: {command}[/red]")
            console.print("Type [cyan]/help[/cyan] for commands")
        
        return None


async def main():
    parser = argparse.ArgumentParser(description="Singularity v2.0 - Modern AI Code Agent")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--resume", action="store_true", help="Resume last session")
    parser.add_argument("--allow", action="append", help="Auto-allow pattern")
    parser.add_argument("-p", "--prompt", help="Single prompt (headless)")
    args = parser.parse_args()
    
    cli = SingularityCLI(headless=args.headless)
    
    # Add permissions
    if args.allow:
        for pattern in args.allow:
            cli.permissions.add_allowed(pattern)
    
    # Start MCP server
    with Progress(SpinnerColumn(), TextColumn("[cyan]Starting MCP server...[/cyan]"), console=console) as progress:
        progress.add_task("startup", total=None)
        await cli.agent.start_mcp_server()
    
    try:
        if args.headless and args.prompt:
            # Headless mode
            response = await cli.process_message(args.prompt)
            print(response)
        else:
            # Interactive TUI
            await cli.interactive_mode()
    finally:
        await cli.agent.stop_mcp_server()


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")


if __name__ == "__main__":
    run()
