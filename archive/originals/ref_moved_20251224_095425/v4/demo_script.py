#!/usr/bin/env python3
"""
Demo script for Revolutionary MCP Server
=========================================

This script demonstrates all the revolutionary features:
1. Code validation
2. AI improvements
3. Test generation
4. Security scanning
5. Self-learning patterns
6. Context search

Usage:
    python demo_mcp.py
"""

import json
import requests
import time
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

MCP_URL = "http://localhost:8765"


def print_header(text):
    """Print a fancy header"""
    console.print()
    console.rule(f"[bold cyan]{text}[/bold cyan]")
    console.print()


def call_tool(tool_name, args):
    """Call MCP tool and return result"""
    try:
        response = requests.post(
            f"{MCP_URL}/tool",
            json={"tool": tool_name, "args": args},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        console.print(f"[red]Error calling {tool_name}: {e}[/red]")
        return None


def demo_validation():
    """Demo 1: Code Validation"""
    print_header("🔍 Demo 1: Code Validation")
    
    # Bad code with security issues
    bad_code = '''
def login(username, password):
    query = "SELECT * FROM users WHERE username='" + username + "' AND password='" + password + "'"
    result = db.execute(query)
    return result
'''
    
    console.print("[yellow]Testing bad code with SQL injection:[/yellow]")
    console.print(Syntax(bad_code, "python", theme="monokai"))
    
    result = call_tool("validate_code", {
        "code": bad_code,
        "language": "python",
        "check_security": True
    })
    
    if result and result['status'] == 'SUCCESS':
        data = result['data']
        
        # Create results table
        table = Table(title="Validation Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Score", f"{data.get('score', 0)}/10")
        table.add_row("Verdict", data.get('verdict', 'UNKNOWN'))
        
        console.print(table)
        
        if data.get('security'):
            console.print("\n[bold red]🛡️ Security Issues:[/bold red]")
            for issue in data['security']:
                console.print(f"  • {issue}")
        
        if data.get('improvements'):
            console.print("\n[bold green]✨ Improvements:[/bold green]")
            for imp in data['improvements']:
                console.print(f"  • {imp}")
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def demo_improvement():
    """Demo 2: Code Improvement"""
    print_header("✨ Demo 2: AI-Powered Code Improvement")
    
    # Suboptimal code
    original_code = '''
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total
'''
    
    console.print("[yellow]Original code:[/yellow]")
    console.print(Syntax(original_code, "python", theme="monokai"))
    
    result = call_tool("improve_code", {
        "code": original_code,
        "language": "python",
        "focus": "readability"
    })
    
    if result and result['status'] == 'SUCCESS':
        data = result['data']
        
        console.print("\n[bold green]Improved code:[/bold green]")
        improved = data.get('improved_code', '')
        if improved:
            console.print(Syntax(improved, "python", theme="monokai"))
        
        if data.get('changes'):
            console.print("\n[bold cyan]Changes made:[/bold cyan]")
            for change in data['changes']:
                console.print(f"  • {change}")
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def demo_test_generation():
    """Demo 3: Test Generation"""
    print_header("🧪 Demo 3: Automatic Test Generation")
    
    code = '''
def divide_numbers(a, b):
    """Divide two numbers safely."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
    
    console.print("[yellow]Code to test:[/yellow]")
    console.print(Syntax(code, "python", theme="monokai"))
    
    result = call_tool("generate_tests", {
        "code": code,
        "language": "python",
        "framework": "pytest",
        "coverage_target": 90
    })
    
    if result and result['status'] == 'SUCCESS':
        data = result['data']
        test_code = data.get('test_code', '')
        
        console.print("\n[bold green]Generated tests:[/bold green]")
        if test_code:
            console.print(Syntax(test_code, "python", theme="monokai"))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def demo_security_scan():
    """Demo 4: Security Scanning"""
    print_header("🛡️ Demo 4: Security Vulnerability Scanning")
    
    dangerous_code = '''
import pickle
import os

def load_config(filename):
    with open(filename, 'rb') as f:
        config = pickle.load(f)
    return config

def run_command(user_input):
    os.system(f"echo {user_input}")
'''
    
    console.print("[yellow]Code with vulnerabilities:[/yellow]")
    console.print(Syntax(dangerous_code, "python", theme="monokai"))
    
    result = call_tool("security_scan", {
        "code": dangerous_code,
        "language": "python"
    })
    
    if result and result['status'] == 'SUCCESS':
        data = result['data']
        
        console.print("\n[bold red]🚨 Security Analysis:[/bold red]")
        console.print(Panel(
            json.dumps(data, indent=2),
            title="Vulnerabilities Found",
            border_style="red"
        ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def demo_learning():
    """Demo 5: Self-Learning Pattern"""
    print_header("🧠 Demo 5: Self-Learning from Corrections")
    
    before = "def getData(x):\n    return x"
    after = "def get_data(x):\n    return x"
    
    console.print("[yellow]Before (Copilot suggestion):[/yellow]")
    console.print(Syntax(before, "python", theme="monokai"))
    
    console.print("\n[green]After (Your correction):[/green]")
    console.print(Syntax(after, "python", theme="monokai"))
    
    result = call_tool("learn_pattern", {
        "code_before": before,
        "code_after": after,
        "category": "naming",
        "description": "Prefer snake_case over camelCase for functions"
    })
    
    if result and result['status'] == 'SUCCESS':
        data = result['data']
        
        console.print(f"\n[bold green]✓ Pattern learned![/bold green]")
        console.print(f"  Pattern ID: {data.get('pattern_id')}")
        console.print(f"  Total patterns: {data.get('total_patterns')}")
        console.print("\n[dim]Next time similar code appears, the system will suggest this correction automatically![/dim]")
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def demo_stats():
    """Demo 6: Server Statistics"""
    print_header("📊 Demo 6: Server Statistics & Performance")
    
    result = call_tool("get_stats", {})
    
    if result and result['status'] == 'SUCCESS':
        data = result['data']
        
        table = Table(title="MCP Server Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow", justify="right")
        
        table.add_row("Total Requests", str(data.get('requests', 0)))
        table.add_row("Code Validations", str(data.get('validations', 0)))
        table.add_row("Improvements Suggested", str(data.get('improvements_suggested', 0)))
        table.add_row("Patterns Learned", str(data.get('patterns_learned', 0)))
        table.add_row("Total Patterns", str(data.get('patterns_count', 0)))
        table.add_row(
            "Avg Response Time",
            f"{data.get('avg_response_time', 0):.2f}s"
        )
        
        console.print(table)


def main():
    """Run all demos"""
    console.clear()
    
    # Check if server is running
    try:
        response = requests.get(f"{MCP_URL}/health", timeout=5)
        response.raise_for_status()
        health = response.json()
        
        console.print(Panel(
            f"[bold green]✓ MCP Server is running[/bold green]\n"
            f"Model: {health.get('model', 'unknown')}\n"
            f"Status: {health.get('status', 'unknown')}",
            title="Connection Status",
            border_style="green"
        ))
    except Exception as e:
        console.print(Panel(
            f"[bold red]✗ Cannot connect to MCP server[/bold red]\n\n"
            f"Error: {e}\n\n"
            f"Please start the server with:\n"
            f"  python copilot_mcp_server.py --port 8765",
            title="Connection Failed",
            border_style="red"
        ))
        return
    
    # Show banner
    console.print()
    console.print("[bold magenta]═" * 60 + "[/bold magenta]")
    console.print("[bold magenta]    🚀 Revolutionary MCP Server Demo[/bold magenta]")
    console.print("[bold magenta]    Copilot + Qwen = AI Revolution[/bold magenta]")
    console.print("[bold magenta]═" * 60 + "[/bold magenta]")
    console.print()
    
    console.input("[dim]Press Enter to start the demos...[/dim]")
    
    # Run demos
    demos = [
        demo_validation,
        demo_improvement,
        demo_test_generation,
        demo_security_scan,
        demo_learning,
        demo_stats
    ]
    
    for demo in demos:
        try:
            demo()
        except KeyboardInterrupt:
            console.print("\n[yellow]Demo interrupted by user[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Demo error: {e}[/red]")
            console.input("\n[dim]Press Enter to continue...[/dim]")
    
    # Final message
    console.print()
    console.print(Panel(
        "[bold green]✓ All demos completed![/bold green]\n\n"
        "You've seen:\n"
        "• Code validation with AI\n"
        "• Intelligent code improvements\n"
        "• Automatic test generation\n"
        "• Security vulnerability scanning\n"
        "• Self-learning patterns\n"
        "• Performance statistics\n\n"
        "[bold cyan]Ready to revolutionize your development workflow![/bold cyan]",
        title="Demo Complete",
        border_style="green"
    ))


if __name__ == "__main__":
    # Install rich if not available
    try:
        from rich.console import Console
    except ImportError:
        print("Installing rich for better output...")
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)
        from rich.console import Console
    
    main()
