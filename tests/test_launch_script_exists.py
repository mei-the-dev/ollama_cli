import os


def test_launch_script_exists():
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "scripts", "launch_with_dashboard.sh"
        )
    )
    assert os.path.exists(path), f"Launch script not found at {path}"


def test_launch_script_executable():
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "scripts", "launch_with_dashboard.sh"
        )
    )
    assert os.access(path, os.X_OK), "Launch script is not executable"
