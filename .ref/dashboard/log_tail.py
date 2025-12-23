import os

from textual.widgets import Log

from .monitor_base import BaseModule


class LogTail(BaseModule):
    def __init__(self, path=None, lines=20, poll_interval: float = 1.0):
        super().__init__("log-tail")
        self.path = path or os.path.join(
            os.path.dirname(__file__), "..", "logs", "mcp_server.log"
        )
        self.lines = lines
        self.poll_interval = poll_interval
        self.widget = Log(highlight=False)
        self._task = None

    def mount(self, app):
        super().mount(app)
        try:
            # place log widget in main content area
            container = app.query_one(".main-content")
            container.mount(self.widget)
            self._mounted = True
        except Exception:
            self._mounted = False

    async def do_check(self):
        try:
            if not os.path.exists(self.path):
                return
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read().splitlines()[-self.lines :]
            self.widget.clear()
            for line in data:
                self.widget.write(line)
        except Exception:
            pass

    async def start(self):
        if not self.app:
            return
        self.app.set_interval(
            self.poll_interval, lambda: self.app.call_later(self.do_check)
        )

    async def stop(self):
        return
