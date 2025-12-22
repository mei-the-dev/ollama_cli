#!/usr/bin/env python3
"""
Omarchy Command Center
A unified dashboard for monitoring Ollama and the Omarchy MCP Server.

Save this file in the repo (e.g. `ref/omarchy_dashboard.py`) or copy to `~/.omarchy/omarchy_dashboard.py`.
"""
import asyncio
import json
import time
import os
from datetime import datetime
from collections import deque

import aiohttp
import psutil

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Label,
    Log,
    Input,
    Tree,
)
from textual.reactive import reactive
from textual.worker import Worker
from textual import work

# --- VISUAL STYLING ---
CSS = """
Screen {
    background: #0f172a;
    color: #e2e8f0;
}

.kpi-grid {
    layout: grid;
    grid-size: 4 1;
    grid-gutter: 1;
    height: auto;
    margin-bottom: 1;
}

.main-content {
    height: 1fr;
    border: solid #334155;
    background: #1e293b;
}

.card {
    background: #1e293b;
    border: solid #334155;
    height: 10;
    padding: 1;
}

.status-ok { color: #4ade80; }
.status-err { color: #f87171; }
.status-wait { color: #facc15; }

.section-title {
    background: #334155;
    color: #f8fafc;
    padding: 0 1;
    text-style: bold;
}

#chat-log {
    height: 1fr;
    background: #0f172a;
    border: none;
    padding: 1;
}

.main-row {
    height: 1fr;
}
.left-col {
    width: 65%;
}
.right-col {
    width: 35%;
    border-left: solid #334155;
    padding: 1;
}
"""


class ServiceStatus(Static):
    """Component to show UP/DOWN status of a service."""
    status = reactive("CHECKING")

    def __init__(self, service_name, port, **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name
        self.port = port

    def compose(self) -> ComposeResult:
        yield Label(f"{self.service_name}", classes="section-title")
        yield Label(f"Port: {self.port}")
        yield Label("UNKNOWN", id="status-lbl")

    def watch_status(self, val):
        lbl = self.query_one("#status-lbl")
        if val == "ONLINE":
            lbl.update("● ONLINE")
            lbl.classes = "status-ok"
        else:
            lbl.update("○ OFFLINE")
            lbl.classes = "status-err"


class ResourceGraph(Static):
    """Simple lightweight resource widget — sparkline fallback-free variant."""

    def __init__(self, title, process_name, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.process_name = process_name
        self.values = deque(maxlen=40)

    def compose(self) -> ComposeResult:
        yield Label(self.title)
        yield Label("--", id="spark")
        yield Label("0.0%", id="val-lbl")

    def update_data(self, usage):
        self.values.append(usage)
        # simple ascii graph using block characters
        last = ''.join('▇' if v > 25 else '▂' if v > 5 else ' ' for v in self.values)
        self.query_one("#spark").update(last)
        self.query_one("#val-lbl").update(f"{usage:.1f}%")


class OmarchyDashboard(App):
    CSS = CSS
    TITLE = "OMARCHY COMMAND CENTER"
    SUB_TITLE = "v2.0 | Model & Tool Monitor"

    ollama_online = reactive(False)
    mcp_online = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Grid(classes="kpi-grid"):
            yield ServiceStatus("Ollama API", 11434, id="stat-ollama", classes="card")
            yield ServiceStatus("MCP Server", 8080, id="stat-mcp", classes="card")
            yield ResourceGraph("Ollama CPU", "ollama", classes="card")
            yield ResourceGraph("MCP (Python) CPU", "python", classes="card")

        with Container(classes="main-content"):
            yield Label("  Server Log Tail (MCP)", classes="section-title")
            yield Log(id="sys-log")

        with Horizontal(classes="main-row"):
            with Vertical(classes="left-col"):
                yield Log(id="chat-log")
                yield Input(placeholder="Send prompt to Ollama...", id="chat-input")

            with Vertical(classes="right-col"):
                yield Label("Live Tools", classes="section-title")
                yield Button("Refresh Tools", id="btn-refresh-tools")
                yield Container(id="tool-container", classes="main-content")

        yield Footer()

    def on_mount(self):
        self.set_interval(2.0, self.monitor_services)
        self.set_interval(1.0, self.monitor_resources)
        self.log_msg("Dashboard initialized.")
        # schedule initial tool check
        self.call_later(self.check_tools)

    def log_msg(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#sys-log").write(f"[{timestamp}] {msg}")

    @work(exclusive=True)
    async def monitor_services(self):
        # Check Ollama
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags", timeout=1) as r:
                    is_up = r.status == 200
                    self.query_one("#stat-ollama").status = "ONLINE" if is_up else "OFFLINE"
                    if is_up and not self.ollama_online:
                        self.log_msg("Ollama connected.")
                    self.ollama_online = is_up
        except Exception:
            self.query_one("#stat-ollama").status = "OFFLINE"
            self.ollama_online = False

        # Check MCP by calling /mcp tools/list
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"method": "tools/list", "params": {}}
                async with session.post("http://localhost:8080/mcp", json=payload, timeout=1) as r:
                    is_up = r.status == 200
                    self.query_one("#stat-mcp").status = "ONLINE" if is_up else "OFFLINE"
                    if is_up and not self.mcp_online:
                        self.log_msg("MCP Server connected.")
                        await self.check_tools()  # auto-refresh
                    self.mcp_online = is_up
        except Exception:
            self.query_one("#stat-mcp").status = "OFFLINE"
            self.mcp_online = False

    def monitor_resources(self):
        ollama_cpu = 0.0
        python_cpu = 0.0

        for p in psutil.process_iter(['name', 'cpu_percent', 'pid']):
            try:
                name = (p.info.get('name') or '').lower()
                if 'ollama' in name:
                    ollama_cpu += (p.info.get('cpu_percent') or 0.0)
                elif 'python' in name and p.info.get('pid') != os.getpid():
                    python_cpu += (p.info.get('cpu_percent') or 0.0)
            except Exception:
                pass

        graphs = self.query(ResourceGraph)
        if len(graphs) >= 2:
            graphs[0].update_data(ollama_cpu)
            graphs[1].update_data(python_cpu)

    async def on_button_pressed(self, event):
        if event.button.id == "btn-refresh-tools":
            await self.check_tools()

    @work
    async def check_tools(self):
        if not self.mcp_online:
            return

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"method": "tools/list", "params": {}}
                async with session.post("http://localhost:8080/mcp", json=payload) as r:
                    data = await r.json()
                    tools = data.get("tools", [])

                    cont = self.query_one("#tool-container")
                    await cont.remove_children()

                    tree = Tree("Available Tools")
                    tree.root.expand()

                    for t in tools:
                        node = tree.root.add(f"[bold cyan]{t.get('name')}[/bold cyan]")
                        node.add(f"[italic]{t.get('description', 'No description')}[/italic]")

                        props = t.get("inputSchema", {}).get("properties", {})
                        if props:
                            args_node = node.add("Arguments")
                            for k, v in props.items():
                                args_node.add(f"[yellow]{k}[/yellow]: {v.get('type')}")

                    await cont.mount(tree)
                    self.log_msg(f"Refreshed tool list: {len(tools)} tools found.")
        except Exception as e:
            self.log_msg(f"Failed to fetch tools: {e}")

    async def on_input_submitted(self, event):
        val = event.value
        if not val:
            return
        event.input.value = ""

        log = self.query_one("#chat-log")
        log.write(f"\n[bold green]You >[/bold green] {val}")
        await self.run_inference(val)

    @work(exclusive=True)
    async def run_inference(self, prompt):
        log = self.query_one("#chat-log")
        log.write("[bold purple]AI >[/bold purple] ")

        start_time = time.time()
        count = 0

        try:
            model = os.environ.get("OMARCHY_MODEL", "qwen2.5-coder:14b-instruct-q4_K_M")

            async with aiohttp.ClientSession() as session:
                payload = {"model": model, "prompt": prompt, "stream": True}
                async with session.post("http://localhost:11434/api/generate", json=payload, timeout=30) as r:
                    async for line in r.content:
                        if not line:
                            continue
                        # try to decode and parse JSON lines, best-effort
                        try:
                            raw = line.decode('utf-8').strip()
                            if not raw:
                                continue
                            data = json.loads(raw)
                        except Exception:
                            piece = line.decode('utf-8', errors='ignore')
                            log.write(piece)
                            continue

                        if "response" in data:
                            chunk = data["response"]
                            log.write(chunk)
                            count += 1

                        if data.get("done"):
                            total_s = data.get("total_duration", 0) / 1e9
                            eval_s = data.get("eval_duration", 0) / 1e9
                            self.log_msg(f"Inference complete: {count} tokens in {total_s:.2f}s (eval {eval_s:.2f}s)")
                            log.write("\n")
                            break

        except Exception as e:
            log.write(f"\n[red]Error: {e}[/red]")


def main():
    app = OmarchyDashboard()
    app.run()


if __name__ == "__main__":
    main()
