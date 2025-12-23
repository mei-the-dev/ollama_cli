import os

import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class MCPMetricsWidget(Static):
    def on_mount(self):
        self.update("MCP: --")
        self.last_metrics = {}

    def set_metrics(self, metrics: dict):
        self.last_metrics = metrics
        status = metrics.get("status", "unknown")
        uptime = metrics.get("uptime", "N/A")
        self.update(f"Status: {status} | Uptime: {uptime}")


class MCPMetrics(BaseModule):
    def __init__(self, poll_interval: float = 2.0):
        super().__init__("mcp-metrics")
        self.poll_interval = poll_interval
        self.widget = MCPMetricsWidget()
        self._task = None

    def mount(self, app):
        super().mount(app)
        try:
            grid = app.query_one(".kpi-grid")
            grid.mount(self.widget)
            self._mounted = True
        except Exception:
            self._mounted = False

    async def do_check(self):
        mcp_url = os.environ.get("OMARCHY_MCP_SERVER_URL", "http://127.0.0.1:8000")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{mcp_url.rstrip('/')}/health", timeout=1) as r:
                    if r.status == 200:
                        data = await r.json()
                        metrics = {
                            "status": data.get("status", "ok"),
                            "uptime": data.get("uptime"),
                        }
                        self.widget.set_metrics(metrics)
                        try:
                            if self.app:
                                self.app.query_one("#sys-log").write(
                                    "MCP metrics updated"
                                )
                        except Exception:
                            pass
                        return
        except Exception:
            pass
        self.widget.set_metrics({"status": "OFFLINE", "uptime": "N/A"})

    @work(exclusive=True)
    async def _check(self):
        await self.do_check()

    async def start(self):
        if not self.app:
            return
        self.app.set_interval(self.poll_interval, self._check)
