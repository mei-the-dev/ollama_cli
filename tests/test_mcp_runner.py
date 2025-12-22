import sys
import subprocess
import time
import urllib.request
from pathlib import Path


def test_mcp_server_starts_and_reports_port():
    script = Path.home() / '.omarchy' / 'mcp_server.py'
    assert script.exists(), "mcp_server script should exist"

    proc = subprocess.Popen([sys.executable, str(script), '--host', '127.0.0.1', '--port', '0'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    host = None
    port = None

    start = time.time()
    try:
        # Wait up to 6 seconds for the listening announcement
        while time.time() - start < 6:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.05)
                continue
            if 'MCP server listening on' in line:
                parts = line.strip().split()
                hostport = parts[-1]
                if ':' in hostport:
                    host, port_s = hostport.split(':')
                    port = int(port_s)
                    break
        assert host is not None and port is not None, "Did not get listening announcement from mcp_server"

        # Check health endpoint
        url = f'http://{host}:{port}/health'
        with urllib.request.urlopen(url, timeout=3) as r:
            body = r.read().decode()
            assert '"status": "ok"' in body
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()