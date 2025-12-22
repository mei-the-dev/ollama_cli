import os
import sys
import subprocess
import time
import json
from pathlib import Path
import urllib.request


def test_cli_startup_and_batch_file_ops(tmp_path):
    # Look for either the new 'singularity' CLI wrapper or the legacy 'omarchy'
    # Prefer the local repo CLI for deterministic tests; fallback to installed wrappers if not present
    # Prefer local repo CLI (singularity or legacy omarchy) for deterministic tests
    local_script = Path('./singularity_cli.py')
    if not local_script.exists():
        local_script = Path('./omarchy_cli.py')

    if local_script.exists():
        script_cmd = [sys.executable, str(local_script)]
    else:
        # Look for either the new 'singularity' CLI wrapper or the legacy 'omarchy'
        script = Path(sys.executable).resolve().parent.parent / 'bin' / 'singularity'
        # Fallback if not installed in virtualenv bin
        if not script.exists():
            script = Path('/usr/local/bin/singularity')
        # Final fallback to legacy name for compatibility
        if not script.exists():
            script = Path(sys.executable).resolve().parent.parent / 'bin' / 'omarchy'
        if not script.exists():
            script = Path('/usr/local/bin/omarchy')
        assert script.exists(), f"CLI executable not found at {script}"
        script_cmd = [str(script)]

    env = os.environ.copy()
    # Set the new and legacy env var to be safe during transition
    env['SINGULARITY_SKIP_OLLAMA'] = '1'
    env['OMARCHY_SKIP_OLLAMA'] = '1'  # ensure backwards compatibility during rebrand

    proc = subprocess.Popen(script_cmd + ['--startup-check-only', '--startup-wait', '3'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

    host = None
    port = None
    url = None

    start = time.time()
    try:
        # Wait up to 6s for output
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
                    url = f'http://{host}:{port}'
                    break
            if 'Startup check: MCP server at' in line:
                # agent prints the discovered URL
                # e.g., Startup check: MCP server at http://127.0.0.1:44741
                part = line.strip().split()[-1]
                if part.startswith('http'):
                    url = part
                    break
        assert url, "CLI did not report MCP server URL"

        # Use the MCP server HTTP endpoint to write a file using write_code tool
        payload = {
            "name": "write_code",
            "arguments": {
                "filepath": str(tmp_path / 'batch_file.txt'),
                "content": "hello from batch",
                "mode": "overwrite"
            }
        }
        req = urllib.request.Request(url + '/call', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=3) as r:
            resp = json.loads(r.read())
            assert resp.get('status') == 'SUCCESS'

        # Read back the file via read_code
        payload = {
            "name": "read_code",
            "arguments": {
                "filepath": str(tmp_path / 'batch_file.txt')
            }
        }
        req = urllib.request.Request(url + '/call', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=3) as r:
            resp = json.loads(r.read())
            assert resp.get('status') == 'SUCCESS'
            data = resp.get('data')
            assert 'hello from batch' in data.get('content', '') or Path(tmp_path / 'batch_file.txt').read_text() == 'hello from batch'

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()