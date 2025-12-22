import os
import sys
import json
import subprocess
import time
from pathlib import Path
import pytest

from mcp_server import MCPServer, ToolStatus


@pytest.fixture
def mcp(tmp_path, monkeypatch):
    # Ensure MCPServer uses temporary home to avoid touching real ~/.omarchy
    monkeypatch.setenv('HOME', str(tmp_path))
    server = MCPServer()
    # Make sure directories are within tmp_path
    server.knowledge_base = tmp_path / 'knowledge'
    server.plans_dir = tmp_path / 'plans'
    server.context_dir = tmp_path / 'context'
    server.init_directories()
    return server


def test_write_and_read_code(mcp, tmp_path):
    target = tmp_path / 'hello.txt'
    import asyncio

    # Write file
    out = asyncio.run(mcp.write_code({'filepath': str(target), 'content': 'hello world', 'mode': 'overwrite'}))
    assert out.status == ToolStatus.SUCCESS

    # Read back
    r2 = asyncio.run(mcp.read_code({'filepath': str(target)}))
    assert r2.status == ToolStatus.SUCCESS
    assert 'hello world' in r2.data.get('content', '')


def test_apply_edit(mcp, tmp_path):
    f = tmp_path / 'edit.txt'
    f.write_text('foo bar baz')
    import asyncio
    # preview
    pre = asyncio.run(mcp.apply_edit({'filepath': str(f), 'search': 'bar', 'replace': 'BAR', 'preview': True, 'apply': False}))
    assert pre.status == ToolStatus.SUCCESS
    assert 'bar' in pre.data.get('preview', '')
    # apply
    ap = asyncio.run(mcp.apply_edit({'filepath': str(f), 'search': 'bar', 'replace': 'BAR', 'preview': False, 'apply': True}))
    assert ap.status == ToolStatus.SUCCESS
    assert 'BAR' in f.read_text()


def test_search_files(mcp, tmp_path):
    (tmp_path / 'a.txt').write_text('apple\nbanana')
    (tmp_path / 'b.txt').write_text('carrot\napple pie')
    import asyncio
    r = asyncio.run(mcp.search_files({'query': 'apple', 'path': str(tmp_path)}))
    assert r.status == ToolStatus.SUCCESS
    assert len(r.data['matches']) >= 2


def test_generate_and_run_tests(mcp, tmp_path):
    mod = tmp_path / 'mod.py'
    mod.write_text('def add(a,b):\n    return a+b\n')
    import asyncio
    gen = asyncio.run(mcp.generate_tests({'filepath': str(mod)}))
    assert gen.status == ToolStatus.SUCCESS
    testfile = mod.parent / 'tests' / f'test_{mod.stem}.py'
    assert testfile.exists()
    # Run pytest directly in the module parent so imports resolve
    import subprocess
    proc = subprocess.run([sys.executable, '-m', 'pytest', '-q'], cwd=str(tmp_path), capture_output=True, text=True)
    assert proc.returncode == 0, f"pytest failed: stdout={proc.stdout}\nstderr={proc.stderr}"


def test_refactor_code_rename(mcp, tmp_path):
    f = tmp_path / 'r.py'
    f.write_text('CONST = 1\nprint(CONST)')
    import asyncio
    pre = asyncio.run(mcp.refactor_code({'filepath': str(f), 'refactor_type': 'rename', 'old': 'CONST', 'new': 'NEW_CONST', 'preview': True, 'apply': False}))
    assert pre.status == ToolStatus.SUCCESS
    ap = asyncio.run(mcp.refactor_code({'filepath': str(f), 'refactor_type': 'rename', 'old': 'CONST', 'new': 'NEW_CONST', 'preview': False, 'apply': True}))
    assert ap.status == ToolStatus.SUCCESS
    assert 'NEW_CONST' in f.read_text()


def test_create_and_update_plan(mcp):
    import asyncio
    create = asyncio.run(mcp.create_plan({'goal': 'Test plan', 'auto_break_down': True}))
    assert create.status == ToolStatus.SUCCESS
    pid = create.data['plan_id']
    upd = asyncio.run(mcp.update_plan({'plan_id': pid, 'item_id': '1', 'status': 'complete'}))
    assert upd.status == ToolStatus.SUCCESS
    assert upd.data['progress'] >= 0


def test_save_and_query_knowledge(mcp):
    import asyncio
    sk = asyncio.run(mcp.save_knowledge({'topic': 'Test', 'content': 'This is a test', 'tags': ['test']}))
    assert sk.status == ToolStatus.SUCCESS
    q = asyncio.run(mcp.query_knowledge({'query': 'test', 'limit': 10}))
    assert q.status == ToolStatus.SUCCESS
    assert len(q.data['results']) >= 1


def test_manage_context(mcp):
    import asyncio
    a = asyncio.run(mcp.manage_context({'action': 'add', 'items': ['note1']}))
    assert a.status == ToolStatus.SUCCESS
    l = asyncio.run(mcp.manage_context({'action': 'list'}))
    assert l.status == ToolStatus.SUCCESS
    assert l.data['count'] >= 1
    r = asyncio.run(mcp.manage_context({'action': 'remove', 'items': 'note1'}))
    assert r.status == ToolStatus.SUCCESS


def test_execute_code_echo(mcp):
    import asyncio
    r = asyncio.run(mcp.execute_code({'command': 'echo hello', 'cwd': '.', 'capture_output': True}))
    assert r.status == ToolStatus.SUCCESS
    assert 'hello' in r.data.get('stdout', '')


def test_http_call_endpoint(tmp_path):
    # Start server as subprocess and call write_code/read_code via HTTP
    script = Path.home() / '.omarchy' / 'mcp_server.py'
    proc = subprocess.Popen([sys.executable, str(script), '--host', '127.0.0.1', '--port', '0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    host = None
    port = None
    start = time.time()
    try:
        while time.time() - start < 6:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.05)
                continue
            if 'MCP server listening on' in line:
                parts = line.strip().split()
                hostport = parts[-1]
                host, port_s = hostport.split(':')
                port = int(port_s)
                break
        assert port is not None
        url = f'http://{host}:{port}'
        payload = {"name": "write_code", "arguments": {"filepath": str(tmp_path / 'x.txt'), 'content': 'hi', 'mode': 'overwrite'}}
        import urllib.request
        req = urllib.request.Request(url + '/call', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=3) as r:
            resp = json.loads(r.read())
            assert resp.get('status') == 'SUCCESS'
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
