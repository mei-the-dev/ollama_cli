import os

import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class LatencyWidget(Static):
    def on_mount(self):
        self.update("Latency: p50=? p95=?")
        self.last = {}

    def set_latency(self, p50, p95, avg=None):
        self.last = {"p50": p50, "p95": p95, "avg": avg}
        self.update(
            f"Latency: p50={p50:.1f}ms p95={p95:.1f}ms avg={avg:.1f}ms"
            if avg is not None
            else f"Latency: p50={p50}ms p95={p95}ms"
        )


class LatencyGraph(BaseModule):
    def __init__(self, poll_interval: float = 2.0):
        super().__init__("latency")
        self.poll_interval = poll_interval
        self.widget = LatencyWidget()

    def mount(self, app):
        super().mount(app)
        try:
            grid = app.query_one(".kpi-grid")
            grid.mount(self.widget)
            self._mounted = True
        except Exception:
            self._mounted = False

    async def do_check(self):
        try:
            mcp = os.environ.get("OMARCHY_MCP_SERVER_URL", "http://127.0.0.1:8000")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{mcp.rstrip('/')}/health", timeout=1) as r:
                    if r.status == 200:
                        data = await r.json()
                        tele = data.get("telemetry", {})
                        p50 = tele.get("p50_ms") or 0.0
                        p95 = tele.get("p95_ms") or 0.0
                        avg = tele.get("avg_latency_ms") or 0.0
                        self.widget.set_latency(p50, p95, avg)
                        if self.app:
                            try:
                                self.app.set_kpi(
                                    "#kpi-lat",
                                    f"Latency: p50={p50:.1f}ms p95={p95:.1f}ms",
                                )
                            except Exception:
                                pass
        except Exception:
            self.widget.set_latency(0.0, 0.0, 0.0)
            if self.app:
                try:
                    self.app.set_kpi("#kpi-lat", "Latency: --")
                except Exception:
                    pass

    @work(exclusive=True)
    async def _check(self):
        await self.do_check()

    async def start(self):
        if not self.app:
            return
        self.app.set_interval(self.poll_interval, self._check)

    async def stop(self):
        return
