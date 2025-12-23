#!/usr/bin/env python3
"""
Singularity CLI - Beautiful Code Agent Interface
Powered by Ollama Qwen2.5-Coder with MCP Tools
"""

import argparse
import asyncio
import getpass
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

try:
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
except ImportError:
    print("Installing required dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table

console = Console()

# Setup a simple file logger for non-interactive/plain logs
logger = logging.getLogger("singularity")
if not logger.handlers:
    try:
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "singularity.log")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
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
        self.model = "Qwen2.5-Coder-14B"
        self.conversation_history = []
        self.current_plan = None
        self.mcp_server_url = None

    async def start_mcp_server(self):
        pass

    async def stop_mcp_server(self):
        pass

    async def execute_with_animation(self, prompt, status, system=None):
        # Dummy implementation for CLI to work
        console.print(f"[bold green]Agent:[/bold green] {prompt}")

    def display_plan(self, plan):
        console.print(f"[cyan]Plan:[/cyan] {plan}")


class SingularityCLI:
    def __init__(self):
        self.agent = SingularityAgent()
        # Auto-apply writes if env SINGULARITY_AUTO_APPLY=1 or config auto_apply true
        self.auto_apply = bool(os.environ.get("SINGULARITY_AUTO_APPLY"))
        self.sudo_password = None
        self.modes = {
            "chat": "💬 Interactive chat mode",
            "code": "⚡ Code generation mode",
            "plan": "📋 Project planning mode",
            "batch": "📦 Batch file generation",
            "learn": "🎓 Learn and save knowledge",
            "analyze": "🔍 Codebase analysis",
        }

    def show_banner(self):
        """Display the banner with a stylized layout"""
        console.clear()
        # Create a two-column header with the banner and quick tips
        left = Panel(BANNER, border_style="magenta", padding=(1, 2))
        tips_text = (
            "[bold]Quick Tips[/bold]\n"
            "- Use [cyan]@file.py[/cyan] to inject a file into context\n"
            "- Use [cyan]@web:http://...[/cyan] to fetch docs\n"
            "- Use [cyan]/mode code[/cyan] to generate code\n\n"
            "Type [cyan]help[/cyan] to see commands"
        )
        tips = Panel(tips_text, border_style="green", padding=(1, 2),)
        console.print(Columns([left, tips]))
        # Subtle divider
        console.rule(
            "[dim]Ready — Ask me to generate code, suggest edits, or explore the repo[/dim]"
        )

    async def startup_config_prompt(self):
        """Interactive prompts at startup to transfer knowledge/context and optionally enable auto-apply and sudo."""
        # Skip prompts if not attached to a TTY (non-interactive environment)
        # Allow tests (pytest) to run prompts even when not a TTY by checking test env.
        if not sys.stdin.isatty() and not os.environ.get("PYTEST_CURRENT_TEST"):
            console.print(
                "[yellow]Non-interactive environment detected; skipping startup prompts.[/yellow]"
            )
            return

        # Transfer knowledge
        try:
            if Confirm.ask(
                "Transfer local knowledge to the model's system prompt (recommended)?"
            ):
                kb_dir = Path.home() / ".singularity" / "knowledge"
                if kb_dir.exists():
                    entries = []
                    for f in list(kb_dir.glob("*.json"))[:20]:
                        try:
                            j = json.loads(f.read_text())
                            entries.append(
                                f"{j.get('topic')}: { (j.get('content','')[:300] + '...') if len(j.get('content',''))>300 else j.get('content','') }"
                            )
                        except Exception:
                            continue
                    if entries:
                        sys_msg = "Knowledge Summary:\n" + "\n".join(entries[:10])
                        # Insert as a system message at the start of conversation history
                        self.agent.conversation_history.insert(
                            0, {"role": "system", "content": sys_msg}
                        )
                        console.print(
                            "[green]Knowledge summary loaded into the agent context.[/green]"
                        )
        except Exception:
            console.print(
                "[yellow]Skipping knowledge transfer (non-interactive environment).[/yellow]"
            )

        # Transfer context
        try:
            if Confirm.ask(
                "Transfer conversation context (context.json) to the model? "
            ):
                ctx_file = Path.home() / ".singularity" / "context" / "context.json"
                if ctx_file.exists():
                    try:
                        ctx = json.loads(ctx_file.read_text())
                        ctx_text = "\n".join([c.get("content", "") for c in ctx][-20:])
                        self.agent.conversation_history.insert(
                            0,
                            {
                                "role": "system",
                                "content": "Conversation context:\n" + ctx_text,
                            },
                        )
                        console.print("[green]Conversation context injected.[/green]")
                    except Exception:
                        console.print("[yellow]Failed to load context file.[/yellow]")
        except Exception:
            console.print(
                "[yellow]Skipping context transfer (non-interactive environment).[/yellow]"
            )

        # Auto-apply writes
        try:
            if Confirm.ask(
                "Enable auto-approval for file writes (auto-apply)? This will allow the CLI to apply agent-suggested file writes without prompting."
            ):
                cfg_path = Path.home() / ".singularity" / "config.json"
                try:
                    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
                except Exception:
                    cfg = {}
                cfg["auto_apply"] = True
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(cfg, indent=2))
                os.environ["SINGULARITY_AUTO_APPLY"] = "1"
                self.auto_apply = True
                console.print("[green]Auto-apply enabled.[/green]")
        except Exception:
            console.print("[yellow]Skipping auto-apply configuration.[/yellow]")

        # Sudo privileges
        try:
            if Confirm.ask(
                "Enable sudo privileges for MCP server tools? (This allows the server to run sudo commands.)"
            ):
                cfg_path = Path.home() / ".singularity" / "config.json"
                try:
                    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
                except Exception:
                    cfg = {}
                cfg["allow_sudo"] = True
                cfg_path.parent.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text(json.dumps(cfg, indent=2))
                # Optionally ask for password to store for this session only
                if Confirm.ask(
                    "Store sudo password for this session to allow non-interactive sudo?"
                ):
                    try:
                        pw = getpass.getpass(
                            "Enter sudo password (stored only in memory for this session): "
                        )
                        self.sudo_password = pw
                        console.print(
                            "[green]Sudo password stored for session.[/green]"
                        )
                    except Exception:
                        console.print(
                            "[yellow]Could not read password; sudo will use non-interactive mode and may fail if password required.[/yellow]"
                        )
                console.print(
                    "[green]Sudo enabled in config. You can disable it later at ~/.singularity/config.json[/green]"
                )
        except Exception:
            console.print("[yellow]Skipping sudo configuration.[/yellow]")

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
                            console.print(
                                f"[green]Switched to {current_mode} mode[/green]"
                            )
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
                        if len(sub) >= 1 and sub[0] == "show":
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
            (
                "/config show",
                "Show effective configuration (env + ~/.singularity/config.json)",
            ),
            ("/help", "Show this help"),
            ("/exit", "Exit Singularity"),
        ]
        for cmd, desc in commands:
            help_table.add_row(cmd, desc)
        console.print(help_table)

    def show_modes(self):
        """Display available modes"""
        modes_table = Table(
            title="Available Modes", show_header=True, header_style="bold cyan"
        )
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
            "analyze": f"Analyze the codebase focusing on: {prompt}. Provide insights and recommendations.",
        }

        # Build a tool-aware system prompt instructing the model to emit JSON tool calls when needed
        tool_prompt = (
            f"{self.agent.model} system: If you need to perform actions like writing files or running shell commands, "
            'output a single JSON object and nothing else with the structure: {"tool": "name", "args": {...}}. '
            'For file creation/modification use tool "write_code" with args {"filepath": "/path", "content": "...", "mode": "overwrite"}. '
            "Available tools: write_code, apply_edit, refactor_code, search_files, fetch_url, execute_code, git_operation."
        )
        full_prompt = mode_prompts.get(mode, prompt)
        await self.agent.execute_with_animation(
            full_prompt, f"Processing in {mode} mode", system=tool_prompt
        )

    def get_effective_config(self) -> Dict:
        """Return the effective configuration merging environment variables and ~/.singularity/config.json (with ~/.omarchy fallback)"""
        singularity_cfg = Path.home() / ".singularity" / "config.json"
        omarchy_cfg = Path.home() / ".omarchy" / "config.json"
        file_cfg = {}
        try:
            if singularity_cfg.exists():
                file_cfg = json.loads(singularity_cfg.read_text())
            elif omarchy_cfg.exists():
                file_cfg = json.loads(omarchy_cfg.read_text())
        except Exception:
            logger.exception("Failed to read config file")

        def env_bool(key, default=False):
            v = os.environ.get(key)
            if v is None:
                return file_cfg.get(key.lower(), default)
            return v.lower() in ("1", "true", "yes", "on")

        conf = {
            "allow_sudo": env_bool(
                "SINGULARITY_ALLOW_SUDO",
                file_cfg.get("allow_sudo", False)
                or env_bool("OMARCHY_ALLOW_SUDO", False),
            ),
            "auto_apply": env_bool(
                "SINGULARITY_AUTO_APPLY",
                file_cfg.get("auto_apply", False)
                or env_bool("OMARCHY_AUTO_APPLY", False),
            ),
            "skip_ollama": env_bool("SINGULARITY_SKIP_OLLAMA", False)
            or env_bool("OMARCHY_SKIP_OLLAMA", False),
            "model": os.environ.get(
                "SINGULARITY_MODEL",
                os.environ.get(
                    "OMARCHY_MODEL", file_cfg.get("model", self.agent.model)
                ),
            ),
            "mcp_server_url": getattr(self.agent, "mcp_server_url", None)
            or os.environ.get("SINGULARITY_MCP_SERVER_URL")
            or os.environ.get("OMARCHY_MCP_SERVER_URL"),
            "preferred_terminal": os.environ.get(
                "SINGULARITY_PREFERRED_TERMINAL",
                file_cfg.get("preferred_terminal")
                or os.environ.get("OMARCHY_PREFERRED_TERMINAL"),
            ),
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
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                try:
                    out_bytes, err_bytes = await asyncio.wait_for(
                        proc.communicate(), timeout=30
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    console.print("[red]Error: command timed out after 30s[/red]")
                    logger.warning("execute_command timeout: %s", cmd)
                    return
                out = out_bytes.decode(errors="replace") if out_bytes else ""
                err = err_bytes.decode(errors="replace") if err_bytes else ""
                if out:
                    console.print(Panel(out, title="Output", border_style="green"))
                if err:
                    console.print(Panel(err, title="Errors", border_style="red"))
                logger.info(
                    "execute_command finished: %s (rc=%s)", cmd, proc.returncode
                )
            except Exception as e:
                logger.exception("execute_command error")
                console.print(f"[red]Error executing command: {e!r}[/red]")

    async def start_dashboard(self):
        """Start the dashboard UI.

        - If `tmux` is available, spawn a new tmux window named `dashboard-<ts>` and run the dashboard there.
        - Otherwise, start the dashboard as a background Python process and write logs to ./logs/dashboard.log
        """
        import time

        dashboard_path = os.path.join(
            os.path.dirname(__file__), "ref", "singularity_dashboard.py"
        )

        # Ensure log dir exists
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        dashboard_log = os.path.join(log_dir, "dashboard.log")

        tmux_path = shutil.which("tmux")
        window_name = f"dashboard-{int(time.time())}"
        python_exec = sys.executable

        # Prepare MCP server URL to pass into the dashboard
        mcp_url = (
            getattr(self.agent, "mcp_server_url", None)
            or os.environ.get("SINGULARITY_MCP_SERVER_URL")
            or os.environ.get("OMARCHY_MCP_SERVER_URL")
            or "http://127.0.0.1:8000"
        )

        if tmux_path:
            # If we're already inside tmux, create a new window in the current session so the user sees it.
            if "TMUX" in os.environ:
                shell_cmd = f"OMARCHY_MCP_SERVER_URL='{mcp_url}' exec {python_exec} {dashboard_path}"
                cmd = [
                    tmux_path,
                    "new-window",
                    "-n",
                    window_name,
                    "bash",
                    "-lc",
                    shell_cmd,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                console.print(
                    f"[green]Dashboard launched in new tmux window '{window_name}' (pid: {proc.pid}).[/green]"
                )
            else:
                session_name = os.environ.get("SINGULARITY_SESSION", "singularity")
                shell_cmd = f"OMARCHY_MCP_SERVER_URL='{mcp_url}' exec {python_exec} {dashboard_path}"
                cmd = [
                    tmux_path,
                    "new-session",
                    "-d",
                    "-s",
                    session_name,
                    "-n",
                    window_name,
                    "bash",
                    "-lc",
                    shell_cmd,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                console.print(
                    f"[green]Dashboard launched in tmux session '{session_name}', window '{window_name}' (pid: {proc.pid}). Attach with: tmux attach -t {session_name}[/green]"
                )

                # If a graphical display is available, try to auto-open a terminal emulator attached to the tmux session
                try:
                    if "DISPLAY" in os.environ:
                        preferred = os.environ.get("SINGULARITY_PREFERRED_TERMINAL")
                        term_path = shutil.which(preferred) if preferred else None
                        if not term_path:
                            for term_candidate in (
                                "alacritty",
                                "kitty",
                                "gnome-terminal",
                                "x-terminal-emulator",
                                "xterm",
                            ):
                                term_path = shutil.which(term_candidate)
                                if term_path:
                                    break
                        if term_path:
                            # Attempt to launch terminal emulator and run tmux attach -t <session>
                            attach_cmd = [
                                term_path,
                                "-e",
                                "tmux",
                                "attach",
                                "-t",
                                session_name,
                            ]
                            try:
                                term_proc = await asyncio.create_subprocess_exec(
                                    *attach_cmd,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE,
                                )
                                console.print(
                                    f"[green]Launched terminal {term_path} to attach to tmux session {session_name} (pid: {term_proc.pid})[/green]"
                                )
                            except Exception:
                                # Non-fatal if terminal cannot be launched
                                pass
                except Exception:
                    pass

        else:
            # Start a background process logging to file
            cmd = [python_exec, dashboard_path]
            with open(dashboard_log, "ab") as fh:
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=fh, stderr=fh)
            console.print(
                f"[green]Dashboard started as background process (pid: {proc.pid}). Logs: {dashboard_log}[/green]"
            )


# Attach existing module-level helper functions to SingularityCLI so they behave as instance methods
for _name in (
    "startup_config_prompt",
    "interactive_mode",
    "process_prompt",
    "get_effective_config",
    "show_config_table",
    "print_config_json",
    "execute_command",
    "start_dashboard",
):
    if _name in globals():
        setattr(SingularityCLI, _name, globals()[_name])


async def main():
    """Main entry point"""
    # Ensure child Python processes use unbuffered stdout so their prints are readable by parent processes
    os.environ["PYTHONUNBUFFERED"] = "1"

    parser = argparse.ArgumentParser(
        description="Singularity - AI Code Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("prompt", nargs="*", help="Direct prompt (non-interactive)")
    parser.add_argument("-m", "--mode", default="chat", help="Mode to use")
    parser.add_argument(
        "--startup-check-only",
        action="store_true",
        help="Start MCP server and exit (used in tests)",
    )
    parser.add_argument(
        "--startup-wait",
        type=int,
        default=0,
        help="When used with --startup-check-only, wait this many seconds before exiting",
    )
    parser.add_argument(
        "--no-startup-config",
        action="store_true",
        help="Skip interactive startup configuration prompts (for CI)",
    )
    parser.add_argument("--version", action="version", version="Singularity 1.0.0")

    args = parser.parse_args()

    cli = SingularityCLI()

    # Support early CLI command: `omarchy config show` which should not trigger startup
    if (
        args.prompt
        and len(args.prompt) >= 2
        and args.prompt[0] == "config"
        and args.prompt[1] == "show"
    ):
        cli.print_config_json()
        return

    # Ensure MCP server is running for tools
    try:
        await cli.agent.start_mcp_server()
    except Exception:
        console.print(
            "[yellow]Warning: could not start MCP server automatically.[/yellow]"
        )

    # If this invocation only wants to check startup, report the MCP URL and exit (used in tests)
    if args.startup_check_only:
        # Wait up to startup_wait (or 5s default) for the agent to discover the MCP URL
        wait_for = (
            args.startup_wait if (args.startup_wait and args.startup_wait > 0) else 5
        )
        url = getattr(cli.agent, "mcp_server_url", None)
        start_t = time.time()
        while not url and (time.time() - start_t) < wait_for:
            await asyncio.sleep(0.05)
            url = getattr(cli.agent, "mcp_server_url", None)

        if url:
            # Use plain print to ensure the message goes to stdout (tests read stdout)
            print(f"Startup check: MCP server at {url}", flush=True)
        else:
            print(
                "Startup check: MCP server started but did not report URL", flush=True
            )

        if args.startup_wait and args.startup_wait > 0:
            console.print(
                f"[cyan]Waiting for {args.startup_wait}s before shutdown...[/cyan]"
            )
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
            console.print(
                f"[cyan]Waiting for {args.startup_wait}s before continuing...[/cyan]"
            )
            try:
                await asyncio.sleep(args.startup_wait)
            except Exception:
                pass

    # Check if Ollama is running (skip when environment variable SINGULARITY_SKIP_OLLAMA is set)
    if not os.environ.get("SINGULARITY_SKIP_OLLAMA"):
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:11434/api/tags"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode != 0:
                console.print(
                    "[red]Ollama is not running. Please start it with: ollama serve[/red]"
                )
                return
        except Exception as e:
            console.print(f"[red]Cannot connect to Ollama: {e}[/red]")
            logger.exception("Cannot connect to Ollama")
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
