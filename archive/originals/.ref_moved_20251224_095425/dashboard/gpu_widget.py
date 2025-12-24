import os

import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class GPUWidget(Static):
    def on_mount(self):
        self.update("GPU Mem: --")
        self.last = None

    def set_gpu(self, mb):
        self.last = mb
        txt = f"GPU Mem: {mb} MB" if mb is not None else "GPU Mem: N/A"
        self.update(txt)


class GPUMetrics(BaseModule):
    def __init__(self, poll_interval: float = 5.0):
        super().__init__("gpu")
        self.poll_interval = poll_interval
        self.widget = GPUWidget()

    def mount(self, app):
        super().mount(app)
        try:
            grid = app.query_one(".kpi-grid")
            grid.mount(self.widget)
            self._mounted = True
        except Exception:
            self._mounted = False

    async def do_check(self):
        # Read from MCP /health telemetry
        try:
            mcp = os.environ.get("OMARCHY_MCP_SERVER_URL", "http://127.0.0.1:8000")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{mcp.rstrip('/')}/health", timeout=1) as r:
                    if r.status == 200:
                        data = await r.json()
                        gpu = data.get("telemetry", {}).get("gpu_memory_mb")
                        self.widget.set_gpu(gpu)
                        return
        except Exception:
            pass
        self.widget.set_gpu(None)

    @work(exclusive=True)
    async def _check(self):
        await self.do_check()

    async def start(self):
        if not self.app:
            return
        self.app.set_interval(self.poll_interval, self._check)

    async def stop(self):
        return
