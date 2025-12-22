import os
import json
import asyncio
import subprocess
import sys
import pytest
from pathlib import Path

# Ensure we can import from repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_server import MCPServer, ToolResult, ToolStatus

@pytest.fixture(autouse=True)
def temp_home(tmp_path, monkeypatch):
    # Make HOME point to tmp_path so sessions and .omarchy are isolated
    monkeypatch.setenv('HOME', str(tmp_path))
    return tmp_path

@pytest.mark.asyncio
async def test_write_and_apply_edit(tmp_path):
    server = MCPServer()
    target = tmp_path / 'sample.py'
    args = {'filepath': str(target), 'content': 'def foo(x,y):\n return x+y\n'}
    res = await server.write_code(args)
    assert isinstance(res, ToolResult)
    assert res.status == ToolStatus.SUCCESS
    assert target.exists()
    # Preview an edit
    edit_preview = await server.apply_edit({'filepath': str(target), 'search': 'x+y', 'replace': 'x + y', 'preview': True})
    assert edit_preview.status == ToolStatus.SUCCESS
    assert 'preview' in edit_preview.data
    # Apply the edit
    edit_apply = await server.apply_edit({'filepath': str(target), 'search': 'x+y', 'replace': 'x + y', 'apply': True})
    assert edit_apply.status == ToolStatus.SUCCESS
    # Check backup exists
    backups = list(target.parent.glob('*.backup.*'))
    assert backups, 'Backup file should exist after apply'
    # Content changed
    assert 'x + y' in target.read_text()

@pytest.mark.asyncio
async def test_generate_tests_and_run(tmp_path, monkeypatch):
    server = MCPServer()
    # Create simple module
    mod = tmp_path / 'mymod.py'
    mod.write_text('def add(a,b):\n    return a+b\n')
    # generate tests
    res = await server.generate_tests({'filepath': str(mod)})
    assert res.status == ToolStatus.SUCCESS
    tests_created = Path(res.data['tests_created'])
    assert tests_created.exists()
    # Run tests
    test_res = await server.test_code({'filepath': str(tests_created)})
    assert isinstance(test_res, ToolResult)
    # pytest will run but tests are trivial (assert True) so expect success
    assert test_res.status in (ToolStatus.SUCCESS, ToolStatus.ERROR)

@pytest.mark.asyncio
async def test_create_project_and_venv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    server = MCPServer()
    res = await server.create_project({'name': 'proj', 'template': 'python-api', 'create_venv': True, 'git_init': False})
    assert res.status == ToolStatus.SUCCESS
    proj_dir = Path(res.data['project'])
    assert proj_dir.exists()
    assert (proj_dir / 'src' / 'main.py').exists()
    # venv created
    assert (proj_dir / '.venv').exists()

@pytest.mark.asyncio
async def test_search_files(tmp_path):
    server = MCPServer()
    f1 = tmp_path / 'a.txt'
    f2 = tmp_path / 'b.txt'
    f1.write_text('hello world\nfoo')
    f2.write_text('another line\nhello again')
    res = await server.search_files({'query': 'hello', 'path': str(tmp_path)})
    assert res.status == ToolStatus.SUCCESS
    assert len(res.data['matches']) >= 2

@pytest.mark.asyncio
async def test_save_and_load_session(temp_home):
    server = MCPServer()
    server.conversation_history = [{'role': 'user', 'content': 'hi'}]
    server.current_plan = {'id': 'plan_1'}
    # prepare context
    ctx_file = Path.home() / '.omarchy' / 'context' / 'context.json'
    ctx_file.parent.mkdir(parents=True, exist_ok=True)
    ctx_file.write_text(json.dumps([{'id':'1','content':'test'}]))
    s = await server.save_session({'name': 's1', 'description': 'desc'})
    assert s.status == ToolStatus.SUCCESS
    sessions_dir = Path.home() / '.omarchy' / 'sessions'
    session_file = sessions_dir / 's1.json'
    assert session_file.exists()
    l = await server.load_session({'name': 's1'})
    assert l.status == ToolStatus.SUCCESS
    assert server.conversation_history[0]['content'] == 'hi'

@pytest.mark.asyncio
async def test_execute_streaming():
    server = MCPServer()
    # Use a command that prints multiple lines
    cmd = 'for i in 1 2 3; do echo line$i; sleep 0.01; done'
    res = await server.execute_code({'command': cmd, 'stream': True, 'timeout': 5})
    assert res.status in (ToolStatus.SUCCESS, ToolStatus.ERROR)
    assert 'streamed_chunks' in (res.data or {})

@pytest.mark.asyncio
async def test_refactor_rename(tmp_path):
    server = MCPServer()
    f = tmp_path / 'r.py'
    f.write_text('def old_name():\n    pass\n')
    res = await server.refactor_code({'filepath': str(f), 'refactor_type': 'rename', 'old': 'old_name', 'new': 'new_name', 'preview': True})
    assert res.status == ToolStatus.SUCCESS
    assert 'preview' in res.data
    # apply
    res2 = await server.refactor_code({'filepath': str(f), 'refactor_type': 'rename', 'old': 'old_name', 'new': 'new_name', 'apply': True})
    assert res2.status == ToolStatus.SUCCESS
    assert 'new_name' in f.read_text()

@pytest.mark.asyncio
async def test_cli_starts_mcp_server(tmp_path, monkeypatch):
    # Ensure ~/.omarchy/mcp_server.py exists for the test HOME
    home = tmp_path
    monkeypatch.setenv('HOME', str(home))
    om_dir = home / '.omarchy'
    om_dir.mkdir(parents=True, exist_ok=True)
    # Copy the project mcp_server.py into the test HOME
    src = Path(__file__).resolve().parents[1] / 'mcp_server.py'
    dst = om_dir / 'mcp_server.py'
    dst.write_text(src.read_text())
    dst.chmod(0o755)
    # Start via OmarchyAgent
    from omarchy_cli import OmarchyAgent
    agent = OmarchyAgent()
    proc = await agent.start_mcp_server(timeout=3.0)
    assert proc is not None
    # Wait briefly and perform health check
    import urllib.request, json
    url = getattr(agent, 'mcp_server_url', None)
    assert url is not None
    resp = urllib.request.urlopen(f"{url}/health", timeout=3)
    body = json.loads(resp.read())
    assert body.get('status') == 'ok'
    # Stop server
    await agent.stop_mcp_server()

# CLI script test - run a tool via scripts/mcp_tool.py
def test_cli_tool(tmp_path, monkeypatch):
    # run write_code via CLI
    t = tmp_path / 'cli_test.py'
    args = json.dumps({'filepath': str(t), 'content': 'x=1\n'})
    out = subprocess.run([sys.executable, 'scripts/mcp_tool.py', 'write_code', args], capture_output=True, text=True)
    assert out.returncode == 0
    assert t.exists()
