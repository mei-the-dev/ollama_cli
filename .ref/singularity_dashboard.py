#!/usr/bin/env python3
"""
Singularity Command Center (legacy: Omarchy)
A unified dashboard for monitoring Ollama and the Singularity MCP Server (Omarchy-compatible).

Save this file in the repo (e.g. `ref/singularity_dashboard.py`) or copy to `~/.singularity/singularity_dashboard.py`.
"""
import json
import os
from collections import deque
from datetime import datetime
from pathlib import Path

import aiohttp
import psutil
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (Button, Footer, Header, Input, Label, Log, Static,
                             Tree)

# --- VISUAL STYLING ---
CSS = """
Screen {
    background: #071226;
    color: #e6eef6;
}

.kpi-grid {
    layout: grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    grid-auto-rows: auto;
    gap: 1 1;
    padding: 1 1;
}

.card {
    border: solid #334155;
    padding: 1 1;
    background: #0b1220;
    height: auto;
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

.main-content {
    padding: 1 1;
    border-top: solid #1f2937;
}

#sys-log {
    height: 12;
    background: #0f172a;
}

#chat-log {
    height: 6;
    background: #08101a;
    border: none;
    padding: 1;
}

.main-row {
    height: 14;
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
        last = "".join("▇" if v > 25 else "▂" if v > 5 else " " for v in self.values)
        self.query_one("#spark").update(last)
        self.query_one("#val-lbl").update(f"{usage:.1f}%")


class SingularityDashboard(App):
    CSS = CSS
    TITLE = "SINGULARITY COMMAND CENTER"
    SUB_TITLE = "v2.0 | Model & Tool Monitor"

    ollama_online = reactive(False)
    mcp_online = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # KPI grid — modules will mount their widgets here
        with Grid(classes="kpi-grid"):
            # Reserve explicit card slots for visible KPIs so layout is stable
            yield Static("Ollama: --\nPort: 11434", id="kpi-ollama", classes="card")
            yield Static("MCP: --\nPort: --", id="kpi-mcp", classes="card")
            yield Static("Req/s: --", id="kpi-reqs", classes="card")
            yield Static("Latency: --", id="kpi-lat", classes="card")

        with Container(classes="main-content"):
            # Header with toggle
            with Horizontal():
                yield Label("  Server Log Tail (MCP)", classes="section-title")
                yield Button("Toggle Log", id="btn-toggle-log")
            yield Container(id="log-panel")
            # Place the Log inside the log-panel container so it can be shown/hidden
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

    def register_modules(self):
        """Create module instances and store them in self.modules (no mounting yet).
        Honor enabled_modules setting from ~/.singularity/config.json or SINGULARITY_PREFERRED_MODULES env var.
        """
        from ref.dashboard.gpu_widget import GPUMetrics
        from ref.dashboard.latency_graph import LatencyGraph
        from ref.dashboard.llm_monitor import LLMMonitor
        from ref.dashboard.llm_telemetry import LLMTelemetry
        from ref.dashboard.log_tail import LogTail
        from ref.dashboard.mcp_metrics import MCPMetrics
        from ref.dashboard.mcp_monitor import MCPMonitor
        from ref.dashboard.request_rate import RequestRate

        candidates = [
            ("mcp", MCPMonitor()),
            ("llm", LLMMonitor()),
            ("mcp_metrics", MCPMetrics()),
            ("llm_telemetry", LLMTelemetry()),
            ("req_rate", RequestRate()),
            ("latency", LatencyGraph()),
            ("gpu", GPUMetrics()),
            ("log_tail", LogTail()),
        ]

        enabled = self._read_enabled_modules()
        # initialize registries
        self._widget_registry = []
        self._disabled_modules = []
        self._kpi_map = {}

        self.modules = []
        for name, inst in candidates:
            inst._module_name = name
            inst._enabled = (enabled is None) or (name in enabled)
            self.modules.append(inst)

    def _config_path(self):
        # Prefer new dot folder; fallback logic can be added if needed
        return Path.home() / ".singularity" / "config.json"

    def _read_enabled_modules(self):
        # Check env var first
        env = os.environ.get("SINGULARITY_PREFERRED_MODULES")
        if env:
            return [m.strip() for m in env.split(",") if m.strip()]
        cfgp = self._config_path()
        if not cfgp.exists():
            return None
        try:
            j = json.loads(cfgp.read_text())
            return j.get("enabled_modules")
        except Exception:
            return None

    def _write_enabled_modules(self, modules_list):
        cfgp = self._config_path()
        cfgp.parent.mkdir(parents=True, exist_ok=True)
        try:
            cfg = json.loads(cfgp.read_text()) if cfgp.exists() else {}
        except Exception:
            cfg = {}
        cfg["enabled_modules"] = modules_list
        cfgp.write_text(json.dumps(cfg, indent=2))

    def mount_modules(self):
        """Attempt to mount modules' widgets into the UI; always add widget references to _widget_registry so tests can inspect them.
        Also create fallback KPI placeholders in `_kpi_map` so modules can update KPIs even when the Textual DOM is not active (headless tests).
        Only mount modules which are enabled per config; disabled modules will be skipped and recorded.
        """
        self._widget_registry = []
        self._kpi_map = {}
        self._disabled_modules = []
        # try to locate existing KPI static slots - if not present, create placeholders
        for kid in ("#kpi-ollama", "#kpi-mcp", "#kpi-reqs", "#kpi-lat"):
            try:
                self.query_one(kid)
                self._kpi_map[kid] = None  # presence confirmed
            except Exception:
                self._kpi_map[kid] = ""  # placeholder text

        for m in self.modules:
            if getattr(m, "_enabled", True) is False:
                if m._module_name not in self._disabled_modules:
                    self._disabled_modules.append(m._module_name)
                continue
            try:
                m.mount(self)
                m._mounted = True
            except Exception:
                m._mounted = False
            # record widget reference for tests even if mount deferred
            if hasattr(m, "widget"):
                if m.widget not in self._widget_registry:
                    self._widget_registry.append(m.widget)

    def set_kpi(self, kpi_id: str, text: str):
        """Set KPI text by id (e.g., '#kpi-mcp'). Always update the internal placeholder map so tests can read it."""
        try:
            # Try update the real widget if available
            self.query_one(kpi_id).update(text)
        except Exception:
            # Store placeholder text for tests / headless
            self._kpi_map.setdefault(kpi_id, text)
            self._kpi_map[kpi_id] = text

    def enable_module(self, name: str):
        """Enable and persist a module by name. If the module is currently disabled, mount and start it."""
        # update config file
        enabled = set(self._read_enabled_modules() or [])
        enabled.add(name)
        self._write_enabled_modules(list(enabled))
        # find module and enable
        for m in self.modules:
            if getattr(m, "_module_name", None) == name:
                m._enabled = True
                try:
                    m.mount(self)
                    m._mounted = True
                except Exception:
                    m._mounted = False
                try:
                    self.call_later(lambda m=m: self.start_module(m))
                except Exception:
                    pass
                if hasattr(m, "widget"):
                    self._widget_registry.append(m.widget)

    def disable_module(self, name: str):
        """Disable and persist a module by name. If the module is running, stop/unmount it."""
        enabled = set(self._read_enabled_modules() or [])
        if name in enabled:
            enabled.remove(name)
        self._write_enabled_modules(list(enabled))
        for m in self.modules:
            if getattr(m, "_module_name", None) == name:
                m._enabled = False
                if name not in self._disabled_modules:
                    self._disabled_modules.append(name)
                try:
                    if getattr(m, "stop", None):
                        self.call_later(lambda m=m: self.run_module_stop(m))
                except Exception:
                    pass
                # remove widget from registry
                if (
                    hasattr(m, "widget")
                    and hasattr(self, "_widget_registry")
                    and m.widget in self._widget_registry
                ):
                    try:
                        self._widget_registry.remove(m.widget)
                    except Exception:
                        pass

    async def run_module_stop(self, m):
        try:
            await m.stop()
        except Exception:
            pass

    def toggle_module(self, name: str):
        if name in (self._read_enabled_modules() or []):
            self.disable_module(name)
        else:
            self.enable_module(name)

    def get_kpi_text(self, kpi_id: str):
        try:
            if kpi_id in self._kpi_map:
                return self._kpi_map[kpi_id]
        except Exception:
            pass
        return None

    log_collapsed = reactive(False)

    def on_mount(self):
        # Initialize modules
        self.register_modules()
        # Mount into UI (if available) and also populate KPI slots
        try:
            self.mount_modules()
            # Populate quick KPI labels for immediate feedback
            try:
                self.query_one("#kpi-ollama").update("Ollama: --\nPort: 11434")
                self.query_one("#kpi-mcp").update("MCP: --\nPort: --")
            except Exception:
                pass
        except Exception:
            # Ensure modules are still registered even if mount fails
            pass

        # Start their periodic tasks (start will be safe if UI isn't yet active)
        for m in self.modules:
            self.call_later(lambda m=m: self.start_module(m))

        # Keep existing logging and tool check schedule
        self.set_interval(1.0, self.monitor_resources)
        self.set_interval(1.0, self.refresh_kpis)
        self.log_msg("Dashboard initialized with modules.")
        self.call_later(self.check_tools)

    def toggle_log(self):
        """Toggle the visibility of the server log panel."""
        self.log_collapsed = not getattr(self, "log_collapsed", False)
        try:
            # If running Textual, toggle the log's container visibility
            panel = self.query_one("#log-panel")
            log = self.query_one("#sys-log")
            if self.log_collapsed:
                log.display = False
                try:
                    panel.styles.height = 1
                except Exception:
                    pass
            else:
                log.display = True
                try:
                    panel.styles.height = None
                except Exception:
                    pass
        except Exception:
            # Headless: just update flag and fall back placeholder
            pass

    def action_toggle_log(self):
        # Expose an action that UI buttons can call
        self.toggle_log()

    def refresh_kpis(self):
        # Update KPI slots by reading module widgets where available
        try:
            # Update Ollama/MCP and telemetry KPIs
            for w in getattr(self, "_widget_registry", []):
                # match by class name or id heuristics
                # For now, rely on module widgets updating log and status; leave placeholders
                pass
        except Exception:
            pass

    def start_module(self, module):
        # Start is async; schedule it
        try:
            self.call_later(lambda: self.run_module_start(module))
        except Exception:
            pass

    async def run_module_start(self, module):
        try:
            await module.start()
        except Exception:
            pass

    def log_msg(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            self.query_one("#sys-log").write(f"[{timestamp}] {msg}")
        except Exception:
            # If the UI screen isn't active (tests), fall back to printing
            print(f"[{timestamp}] {msg}")

    @work(exclusive=True)
    async def monitor_services(self):
        # Check Ollama
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:11434/api/tags", timeout=1
                ) as r:
                    is_up = r.status == 200
                    self.query_one("#stat-ollama").status = (
                        "ONLINE" if is_up else "OFFLINE"
                    )
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
                async with session.post(
                    "http://localhost:8080/mcp", json=payload, timeout=1
                ) as r:
                    is_up = r.status == 200
                    self.query_one("#stat-mcp").status = (
                        "ONLINE" if is_up else "OFFLINE"
                    )
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

        for p in psutil.process_iter(["name", "cpu_percent", "pid"]):
            try:
                name = (p.info.get("name") or "").lower()
                if "ollama" in name:
                    ollama_cpu += p.info.get("cpu_percent") or 0.0
                elif "python" in name and p.info.get("pid") != os.getpid():
                    python_cpu += p.info.get("cpu_percent") or 0.0
            except Exception:
                pass

        graphs = self.query(ResourceGraph)
        if len(graphs) >= 2:
            graphs[0].update_data(ollama_cpu)
            graphs[1].update_data(python_cpu)

    async def on_button_pressed(self, event):
        btn = getattr(event, "button", None)
        if not btn:
            return
        if btn.id == "btn-refresh-tools":
            await self.check_tools()
        elif btn.id == "btn-toggle-log":
            self.toggle_log()

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
                        node.add(
                            f"[italic]{t.get('description', 'No description')}[/italic]"
                        )

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

        count = 0

        try:
            model = os.environ.get("OMARCHY_MODEL", "qwen2.5-coder:14b-instruct-q4_K_M")

            async with aiohttp.ClientSession() as session:
                payload = {"model": model, "prompt": prompt, "stream": True}
                async with session.post(
                    "http://localhost:11434/api/generate", json=payload, timeout=30
                ) as r:
                    async for line in r.content:
                        if not line:
                            continue
                        # try to decode and parse JSON lines, best-effort
                        try:
                            raw = line.decode("utf-8").strip()
                            if not raw:
                                continue
                            data = json.loads(raw)
                        except Exception:
                            piece = line.decode("utf-8", errors="ignore")
                            log.write(piece)
                            continue

                        if "response" in data:
                            chunk = data["response"]
                            log.write(chunk)
                            count += 1

                        if data.get("done"):
                            total_s = data.get("total_duration", 0) / 1e9
                            eval_s = data.get("eval_duration", 0) / 1e9
                            self.log_msg(
                                f"Inference complete: {count} tokens in {total_s:.2f}s (eval {eval_s:.2f}s)"
                            )
                            log.write("\n")
                            break

        except Exception as e:
            log.write(f"\n[red]Error: {e}[/red]")


def main():
    app = SingularityDashboard()
    app.run()


if __name__ == "__main__":
    main()
