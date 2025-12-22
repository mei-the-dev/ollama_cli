
class BaseModule:
    """Base class for dashboard monitoring modules.

    Modules should implement `mount(app)` to attach widgets into the dashboard,
    and `start(app)` to schedule periodic work (e.g., via app.set_interval).
    """
    def __init__(self, name: str):
        self.name = name
        self.app = None

    def mount(self, app):
        """Attach widgets into the app. Should be synchronous and idempotent."""
        self.app = app

    async def start(self):
        """Start periodic tasks. Override if needed."""
        return

    async def stop(self):
        """Stop/cleanup tasks. Override if needed."""
        return
