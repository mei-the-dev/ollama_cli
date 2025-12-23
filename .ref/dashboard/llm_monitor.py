import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class LLMStatus(Static):
    def __init__(self, name: str = "Ollama API", id: str = "stat-ollama"):
        super().__init__()
        self.service_name = name
        self.id = id

    def on_mount(self):
        self.update(f"{self.service_name}: --")

    def set_status(self, is_up: bool):
        status = "ONLINE" if is_up else "OFFLINE"
        self.last_status = status
        self.update(f"{self.service_name}: {status}")


class LLMMonitor(BaseModule):
    def __init__(self, poll_interval: float = 2.0):
        super().__init__("llm")
        self.poll_interval = poll_interval
        self.widget = LLMStatus()

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
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:11434/api/tags", timeout=1
                ) as r:
                    is_up = r.status == 200
                    self.widget.set_status(is_up)
                    try:
                        if self.app:
                            self.app.set_kpi(
                                "#kpi-ollama",
                                f"Ollama: {'ONLINE' if is_up else 'OFFLINE'}\nPort: 11434",
                            )
                    except Exception:
                        pass
                    try:
                        if is_up and self.app:
                            self.app.query_one("#sys-log").write("Ollama: OK")
                    except Exception:
                        pass
        except Exception:
            self.widget.set_status(False)

    @work(exclusive=True)
    async def _check(self):
        await self.do_check()

    async def start(self):
        if not self.app:
            return
        self.app.set_interval(self.poll_interval, self._check)

    async def stop(self):
        return
