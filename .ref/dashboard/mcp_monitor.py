import os

import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class MCPStatus(Static):
    def __init__(self, name: str = "MCP Server", id: str = "stat-mcp"):
        super().__init__()
        self.service_name = name
        self.id = id

    def on_mount(self):
        self.update(f"{self.service_name}: --")

    def set_status(self, is_up: bool):
        status = "ONLINE" if is_up else "OFFLINE"
        self.last_status = status
        self.update(f"{self.service_name}: {status}")


class MCPMonitor(BaseModule):
    def __init__(self, poll_interval: float = 2.0):
        super().__init__("mcp")
        self.poll_interval = poll_interval
        self.widget = MCPStatus()
        self._task = None

    def mount(self, app):
        super().mount(app)
        # If the textual screen isn't active (e.g., in unit tests), defer actual mounting
        try:
            # Ensure there is a kpi-grid container to put this widget into
            grid = app.query_one(".kpi-grid")
            grid.mount(self.widget)
            self._mounted = True
        except Exception:
            # Defer mounting until the UI is active
            self._mounted = False

    async def do_check(self):
        mcp_url = os.environ.get("OMARCHY_MCP_SERVER_URL", "http://127.0.0.1:8000")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{mcp_url.rstrip('/')}/call",
                    json={"method": "tools/list", "params": {}},
                    timeout=1,
                ) as r:
                    is_up = r.status == 200
                    self.widget.set_status(is_up)
                    # Update dashboard KPI placeholder if available
                    try:
                        port = ""
                        try:
                            from urllib.parse import urlparse

                            u = urlparse(mcp_url)
                            port = u.port or ""
                        except Exception:
                            port = ""
                        if self.app:
                            try:
                                self.app.set_kpi(
                                    "#kpi-mcp",
                                    f"MCP: {'ONLINE' if is_up else 'OFFLINE'}\nPort: {port}",
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        if is_up and self.app:
                            self.app.query_one("#sys-log").write("MCP Server: OK")
                    except Exception:
                        pass
        except Exception:
            self.widget.set_status(False)

    @work(exclusive=True)
    async def _check(self):
        # wrapper used by textual worker decorator; delegate to the pure async implementation
        await self.do_check()

    async def start(self):
        # schedule periodic check via app.set_interval
        if not self.app:
            return
        self._task = self.app.set_interval(self.poll_interval, self._check)

    async def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
