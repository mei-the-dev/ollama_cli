import aiohttp
from textual import work
from textual.widgets import Static

from .monitor_base import BaseModule


class LLMTelemetryWidget(Static):
    def on_mount(self):
        self.update("LLM: --")
        self.last_info = {}

    def set_info(self, info: dict):
        self.last_info = info
        name = info.get("model", "unknown")
        loaded = info.get("loaded_models", "?")
        latency = info.get("last_latency_ms", "?")
        self.update(f"Model: {name} | Loaded: {loaded} | Latency: {latency}ms")


class LLMTelemetry(BaseModule):
    def __init__(self, poll_interval: float = 2.0):
        super().__init__("llm-telemetry")
        self.poll_interval = poll_interval
        self.widget = LLMTelemetryWidget()
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
        # Attempt to call Ollama's tags or status endpoint to fetch basic info
        info = {"model": "unknown", "loaded_models": 0, "last_latency_ms": None}
        try:
            async with aiohttp.ClientSession() as session:
                # Try tags endpoint first
                async with session.get(
                    "http://localhost:11434/api/tags", timeout=1
                ) as r:
                    if r.status == 200:
                        info["model"] = "ollama"
                        info["loaded_models"] = 1
        except Exception:
            # Not available
            pass
        try:
            self.widget.set_info(info)
            if self.app:
                try:
                    self.app.query_one("#sys-log").write("LLM telemetry updated")
                except Exception:
                    pass
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
