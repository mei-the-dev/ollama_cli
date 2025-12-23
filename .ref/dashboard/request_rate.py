import os
from collections import deque

import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class RequestRateWidget(Static):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.history = deque(maxlen=60)

    def on_mount(self):
        # ensure history exists even if __init__ was not called in some test harnesses
        if not hasattr(self, "history"):
            self.history = deque(maxlen=60)
        self.update("Req/s: --")

    def set_rate(self, rate: float):
        if not hasattr(self, "history"):
            self.history = deque(maxlen=60)
        self.history.append(rate)
        # render a simple sparkline-like row (normalize rate to an index 0-70+)
        bars = "".join(
            "▁▂▃▄▅▆▇"[min(6, max(0, int(r / 10)))] if r is not None else " "
            for r in self.history
        )
        self.update(f"Req/s: {rate:.1f} [{bars}]")


class RequestRate(BaseModule):
    def __init__(self, poll_interval: float = 1.0):
        super().__init__("req-rate")
        self.poll_interval = poll_interval
        self.widget = RequestRateWidget()
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
        # Query /health and compute reqs_last_minute as rate
        try:
            mcp = os.environ.get("OMARCHY_MCP_SERVER_URL", "http://127.0.0.1:8000")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{mcp.rstrip('/')}/health", timeout=1) as r:
                    if r.status == 200:
                        data = await r.json()
                        rate = (
                            data.get("telemetry", {}).get("reqs_last_minute", 0) / 60.0
                        )
                        self.widget.set_rate(rate)
                        if self.app:
                            try:
                                self.app.set_kpi("#kpi-reqs", f"Req/s: {rate:.1f}")
                            except Exception:
                                pass
        except Exception:
            self.widget.set_rate(0.0)
            if self.app:
                try:
                    self.app.set_kpi("#kpi-reqs", "Req/s: 0.0")
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
