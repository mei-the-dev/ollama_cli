import pytest

import os
import pytest

if os.environ.get("ALLOW_REF_IMPORTS") != "1":
    pytest.skip("Tests importing ref are disabled by default. Set ALLOW_REF_IMPORTS=1 to enable.", allow_module_level=True)

from ref.singularity_dashboard import SingularityDashboard


@pytest.mark.asyncio
async def test_toggle_log_state():
    app = SingularityDashboard()
    app.register_modules()
    app.mount_modules()
    # initial state should be not collapsed
    assert not getattr(app, "log_collapsed", False)
    app.toggle_log()
    assert app.log_collapsed is True
    app.toggle_log()
    assert app.log_collapsed is False
