import os


def test_dashboard_file_exists():
    path = os.path.join(
        os.path.dirname(__file__), "..", "ref", "singularity_dashboard.py"
    )
    path = os.path.abspath(path)
    assert os.path.exists(path), f"Dashboard script not found at {path}"


def test_dashboard_executable_flag():
    path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "ref", "singularity_dashboard.py")
    )
    assert (
        os.access(path, os.X_OK) or os.stat(path).st_mode & 0o100
    ), "Dashboard script is not executable (not required but recommended)"
