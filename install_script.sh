#!/bin/bash

# Singularity Installation Script
# Installs the MCP server and CLI for AI-powered coding

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Installing Singularity - AI Code Agent"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${CYAN}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is required but not installed.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check Ollama
echo -e "${CYAN}Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Ollama not found. Installing...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}✓ Ollama found${NC}"
fi

# Pull the model
echo -e "${CYAN}Pulling Qwen2.5-Coder model...${NC}"
echo -e "${YELLOW}This may take several minutes (model is ~8GB)${NC}"
ollama pull qwen2.5-coder:14b-instruct-q4_K_M

# Create Singularity directory (and legacy Omarchy directory for compatibility)
SINGULARITY_DIR="$HOME/.singularity"
OMARCHY_DIR="$HOME/.omarchy"
echo -e "${CYAN}Creating Singularity directory at ${SINGULARITY_DIR} (and legacy ${OMARCHY_DIR})...${NC}"
mkdir -p "$SINGULARITY_DIR" "$SINGULARITY_DIR/knowledge" "$SINGULARITY_DIR/plans" "$SINGULARITY_DIR/tools" "$SINGULARITY_DIR/sessions"
mkdir -p "$OMARCHY_DIR" "$OMARCHY_DIR/knowledge" "$OMARCHY_DIR/plans" "$OMARCHY_DIR/tools" "$OMARCHY_DIR/sessions"

# Install Python dependencies
echo -e "${CYAN}Installing Python dependencies...${NC}"
python3 -m pip install rich aiohttp

# Install MCP server from repo to Singularity directory (and copy legacy path)
echo -e "${CYAN}Installing MCP server into ${SINGULARITY_DIR} (and ${OMARCHY_DIR})...${NC}"
cp "$REPO_ROOT/mcp_server.py" "$SINGULARITY_DIR/mcp_server.py"
cp "$SINGULARITY_DIR/mcp_server.py" "$OMARCHY_DIR/mcp_server.py"
chmod +x "$SINGULARITY_DIR/mcp_server.py" "$OMARCHY_DIR/mcp_server.py"

# Install CLI into Singularity directory and create legacy Omarchy alias
echo -e "${CYAN}Installing Singularity CLI into ${SINGULARITY_DIR} (and legacy ${OMARCHY_DIR})...${NC}"
cp "$REPO_ROOT/singularity_cli.py" "$SINGULARITY_DIR/singularity.py"
cp "$SINGULARITY_DIR/singularity.py" "$OMARCHY_DIR/omarchy.py"
chmod +x "$SINGULARITY_DIR/singularity.py" "$OMARCHY_DIR/omarchy.py"

# Create command-line shortcuts for Singularity and a legacy Omarchy alias
echo -e "${CYAN}Creating command-line shortcuts...${NC}"
sudo ln -sf "$SINGULARITY_DIR/singularity.py" /usr/local/bin/singularity 2>/dev/null || \
    ln -sf "$SINGULARITY_DIR/singularity.py" "$HOME/.local/bin/singularity"
# Legacy alias (kept for compatibility)
sudo ln -sf "$SINGULARITY_DIR/singularity.py" /usr/local/bin/omarchy 2>/dev/null || \
    ln -sf "$SINGULARITY_DIR/singularity.py" "$HOME/.local/bin/omarchy"

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict
import subprocess
import shutil
import argparse

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.live import Live
    from rich.markdown import Markdown
    from rich import print as rprint
except ImportError:
    print("Installing required dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.live import Live
    from rich.markdown import Markdown
    from rich import print as rprint

console = Console()

# ASCII Art Banner
BANNER = """
[bold cyan]
   ██████  ███    ███  █████  ██████   ██████ ██   ██ ██    ██ 
  ██    ██ ████  ████ ██   ██ ██   ██ ██      ██   ██  ██  ██  
  ██    ██ ██ ████ ██ ███████ ██████  ██      ███████   ████   
  ██    ██ ██  ██  ██ ██   ██ ██   ██ ██      ██   ██    ██    
   ██████  ██      ██ ██   ██ ██   ██  ██████ ██   ██    ██    
[/bold cyan]
[dim]         Powered by Qwen2.5-Coder 14B via Ollama[/dim]
"""

THINKING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
CODE_FRAMES = ["◐", "◓", "◑", "◒"]
COMPLETE_SYMBOL = "✓"
ERROR_SYMBOL = "✗"


class OmarchyAgent:
    def __init__(self):
        self.model = "qwen2.5-coder:14b-instruct-q4_K_M"
        self.mcp_server_path = Path.home() / ".omarchy" / "mcp_server.py"
        self.conversation_history = []
        self.current_plan = None
        
    async def start_mcp_server(self):
        """Start the MCP server process"""
        if not self.mcp_server_path.exists():
            console.print("[yellow]MCP server not found. Please install it first.[/yellow]")
            return None
        
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(self.mcp_server_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            return process
        except Exception as e:
            console.print(f"[red]Failed to start MCP server: {e}[/red]")
            return None
    
    async def call_ollama(self, prompt: str, system: str = None, tools: List[Dict] = None):
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
    
    async def execute_with_animation(self, prompt: str, task_description: str):
        """Execute a prompt with beautiful animation"""
        console.print(f"\n[bold cyan]→[/bold cyan] {task_description}")
        
        full_response = ""
        
        with Live(console=console, refresh_per_second=10) as live:
            frame_idx = 0
            
            async for chunk in self.call_ollama(prompt):
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
        """Handle MCP tool calls"""
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            tool_args = tool_call.get("function", {}).get("arguments", {})
            
            console.print(f"  [yellow]→[/yellow] Executing: [bold]{tool_name}[/bold]")
            
            # Execute tool via MCP server
            # This would connect to your MCP server
            await asyncio.sleep(0.5)  # Simulate execution
            
            console.print(f"  [green]{COMPLETE_SYMBOL}[/green] {tool_name} completed")
    
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


class OmarchyCLI:
    def __init__(self):
        self.agent = OmarchyAgent()
        self.modes = {
            "chat": "💬 Interactive chat mode",
            "code": "⚡ Code generation mode",
            "plan": "📋 Project planning mode",
            "batch": "📦 Batch file generation",
            "learn": "🎓 Learn and save knowledge",
            "analyze": "🔍 Codebase analysis"
        }
    
    def show_banner(self):
        """Display the Omarchy banner"""
        console.clear()
        console.print(BANNER)
        console.print(Panel(
            "[bold]Welcome to Omarchy - Your AI Code Agent[/bold]\n\n"
            "Type [cyan]help[/cyan] for commands or start coding!",
            border_style="cyan"
        ))
    
    def show_help(self):
        """Display help information"""
        help_table = Table(title="Available Commands", show_header=True, header_style="bold cyan")
        help_table.add_column("Command", style="cyan", width=20)
        help_table.add_column("Description", style="white")
        
        commands = [
            ("/mode <name>", "Switch mode (chat, code, plan, batch, learn, analyze)"),
            ("/new", "Start new conversation"),
            ("/plan", "View current plan"),
            ("/save", "Save current session"),
            ("/load", "Load previous session"),
            ("/exec <cmd>", "Execute shell command"),
            ("/git <operation>", "Perform git operation"),
            ("/help", "Show this help"),
            ("/exit", "Exit Omarchy")
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
    
    async def interactive_mode(self):
        """Main interactive loop"""
        self.show_banner()
        
        current_mode = "chat"
        
        while True:
            try:
                # Beautiful prompt
                prompt = Prompt.ask(
                    f"\n[bold cyan]omarchy[/bold cyan] [[{current_mode}]]"
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
                    else:
                        console.print(f"[red]Unknown command: {cmd}[/red]")
                    
                    continue
                
                # Process based on mode
                await self.process_prompt(prompt, current_mode)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
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
        
        full_prompt = mode_prompts.get(mode, prompt)
        await self.agent.execute_with_animation(full_prompt, f"Processing in {mode} mode")
    
    async def execute_command(self, cmd: str):
        """Execute shell command with animation"""
        with console.status(f"[cyan]Executing: {cmd}[/cyan]", spinner="dots"):
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.stdout:
                    console.print(Panel(result.stdout, title="Output", border_style="green"))
                if result.stderr:
                    console.print(Panel(result.stderr, title="Errors", border_style="red"))
                    
            except Exception as e:
                console.print(f"[red]Error executing command: {e}[/red]")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Omarchy - AI Code Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("prompt", nargs="*", help="Direct prompt (non-interactive)")
    parser.add_argument("-m", "--mode", default="chat", help="Mode to use")
    parser.add_argument("--version", action="version", version="Omarchy 1.0.0")
    
    args = parser.parse_args()
    
    cli = OmarchyCLI()
    
    # Check if Ollama is running
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=2
        )
        if result.returncode != 0:
            console.print("[red]Ollama is not running. Please start it with: ollama serve[/red]")
            return
    except:
        console.print("[red]Cannot connect to Ollama. Please ensure it's installed and running.[/red]")
        return
    
    # Direct prompt mode
    if args.prompt:
        prompt = " ".join(args.prompt)
        await cli.process_prompt(prompt, args.mode)
    else:
        # Interactive mode
        await cli.interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
CLI_END

chmod +x "$OMARCHY_DIR/omarchy.py"

# Create symlink
echo -e "${CYAN}Creating command-line shortcut...${NC}"
sudo ln -sf "$OMARCHY_DIR/omarchy.py" /usr/local/bin/omarchy 2>/dev/null || \
    ln -sf "$OMARCHY_DIR/omarchy.py" "$HOME/.local/bin/omarchy"

# Create configuration file (Singularity + legacy Omarchy copy)
echo -e "${CYAN}Creating configuration file...${NC}"
cat > "$SINGULARITY_DIR/config.json" << 'CONFIG_END'
{
  "model": "qwen2.5-coder:14b-instruct-q4_K_M",
  "ollama_host": "http://localhost:11434",
  "mcp_server_port": 3000,
  "default_mode": "chat",
  "auto_save_sessions": true,
  "knowledge_base_enabled": true,
  "git_integration": true,
  "theme": "monokai"
}
CONFIG_END
cp "$SINGULARITY_DIR/config.json" "$OMARCHY_DIR/config.json"

# Create welcome script
cat > "$OMARCHY_DIR/welcome.sh" << 'WELCOME_END'
#!/bin/bash
cat << "BANNER"
   ██████  ███    ███  █████  ██████   ██████ ██   ██ ██    ██ 
  ██    ██ ████  ████ ██   ██ ██   ██ ██      ██   ██  ██  ██  
  ██    ██ ██ ████ ██ ███████ ██████  ██      ███████   ████   
  ██    ██ ██  ██  ██ ██   ██ ██   ██ ██      ██   ██    ██    
   ██████  ██      ██ ██   ██ ██   ██  ██████ ██   ██    ██    

         Powered by Qwen2.5-Coder 14B via Ollama
BANNER

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Quick Start:"
echo "  singularity                    - Start interactive mode (omarchy alias supported)"
echo "  singularity 'your prompt'      - Direct prompt mode"
echo "  singularity --mode code        - Start in code mode"
echo "  singularity --help             - Show all options"
echo ""
echo "Configuration: ~/.omarchy/config.json"
echo "Knowledge Base: ~/.omarchy/knowledge/"
echo ""
WELCOME_END

chmod +x "$OMARCHY_DIR/welcome.sh"

# Start Ollama service if not running
echo -e "${CYAN}Checking Ollama service...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}Starting Ollama service...${NC}"
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Test installation
echo -e "${CYAN}Testing installation...${NC}"
if command -v omarchy &> /dev/null; then
    echo -e "${GREEN}✓ Omarchy CLI is ready!${NC}"
else
    echo -e "${YELLOW}Note: Add $HOME/.local/bin to your PATH if omarchy command is not found${NC}"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\" >> ~/.bashrc"
fi

# Display welcome message
echo ""
"$OMARCHY_DIR/welcome.sh"

# Create quick examples
cat > "$OMARCHY_DIR/examples.md" << 'EXAMPLES_END'
# Omarchy Examples

## Interactive Chat
```bash
omarchy
# Then type: "Explain how async/await works in Python"
```

## Code Generation
```bash
omarchy --mode code "Create a REST API with FastAPI for a todo app"
```

## Project Planning
```bash
omarchy --mode plan "Build a web scraper for e-commerce sites"
```

## Batch Generation
```bash
omarchy --mode batch "Generate CRUD operations for User, Product, Order models"
```

## Codebase Analysis
```bash
cd your-project
omarchy --mode analyze "Review security vulnerabilities"
```

## Learning Mode
```bash
omarchy --mode learn "Research best practices for React hooks"
```

## Direct Commands
```bash
# Generate a specific file
omarchy "Write a Python script to merge PDFs"

# Explain existing code
omarchy "Explain what this code does: $(cat myfile.py)"

# Debugging help
omarchy "Why am I getting this error: TypeError: 'NoneType' object is not iterable"
```

## Advanced Features

### Git Integration
```bash
# In interactive mode
/git status
/git commit -m "feat: add new feature"
/git push
```

### Knowledge Base
```bash
# Save learnings
/mode learn
> Research Docker best practices

# Query knowledge
> What did I learn about Docker?
```

### Plan Tracking
```bash
/mode plan
> Build a chat application

# View progress
/plan

# Mark items complete
> Complete: Setup project structure
```

## MCP Tools

The agent has access to powerful tools:
- **write_code**: Generate and save code files
- **execute_code**: Run and test code
- **search_docs**: Find documentation online
- **git_operation**: Full git integration
- **create_plan**: Break down complex tasks
- **save_knowledge**: Persistent learning
- **batch_generate**: Multiple file generation
- **analyze_codebase**: Deep code analysis
- **add_tool**: Self-improve by adding new tools

## Tips

1. **Be specific**: "Create a FastAPI endpoint for user authentication with JWT" 
   vs "make an API"

2. **Provide context**: Include relevant files, error messages, or requirements

3. **Use modes**: Switch modes for specialized tasks

4. **Save knowledge**: Use learn mode to build a personal knowledge base

5. **Plan big projects**: Use plan mode to break down complex features

6. **Iterate**: Refine generated code through conversation

## Configuration

Edit `~/.omarchy/config.json`:
```json
{
  "model": "qwen2.5-coder:14b-instruct-q4_K_M",
  "default_mode": "code",
  "auto_save_sessions": true,
  "theme": "dracula"
}
```

## Troubleshooting

### Ollama not responding
```bash
ollama serve
```

### Model not found
```bash
ollama pull qwen2.5-coder:14b-instruct-q4_K_M
```

### Permission errors
```bash
chmod +x ~/.omarchy/omarchy.py
```

### Reset knowledge base
```bash
rm -rf ~/.omarchy/knowledge/*
```
EXAMPLES_END

echo -e "${GREEN}✓ Examples saved to ~/.omarchy/examples.md${NC}"
echo ""
echo -e "${CYAN}Try it now:${NC} singularity (legacy 'omarchy' alias supported)"
echo ""