import asyncio
import json
from aiohttp import web
from pathlib import Path

import singularity_cli


async def _start_test_server(handler):
    app = web.Application()
    app.router.add_post('/call', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()

    # Extract actual port
    port = None
    for s in runner.sites:
        try:
            sock = s._server.sockets[0]
            port = sock.getsockname()[1]
            break
        except Exception:
            continue

    url = f'http://127.0.0.1:{port}'

    return runner, url


def test_call_mcp_tool_success():
    async def handler(request):
        payload = await request.json()
        assert payload['name'] == 'test_tool'
        return web.json_response({'status': 'SUCCESS', 'data': {'result': 'ok'}})

    async def inner():
        runner, url = await _start_test_server(handler)
        try:
            agent = singularity_cli.SingularityAgent()
            agent.mcp_server_url = url
            res = await agent.call_mcp_tool('test_tool', {'x': 1})
            assert res['status'] == 'SUCCESS'
            assert res['data']['result'] == 'ok'
        finally:
            await runner.cleanup()

    asyncio.run(inner())


def test_call_mcp_tool_retries_on_5xx_then_success():
    state = {'calls': 0}

    async def handler(request):
        state['calls'] += 1
        if state['calls'] == 1:
            return web.Response(status=500, text='server down')
        return web.json_response({'status': 'SUCCESS', 'data': {'recovered': True}})

    async def inner():
        runner, url = await _start_test_server(handler)
        try:
            agent = singularity_cli.SingularityAgent()
            agent.mcp_server_url = url
            res = await agent.call_mcp_tool('test_tool', {}, timeout=1.0, retries=2)
            assert res['status'] == 'SUCCESS'
            assert res['data']['recovered'] is True
            assert state['calls'] >= 2
        finally:
            await runner.cleanup()

    asyncio.run(inner())


def test_call_mcp_tool_timeout():
    async def handler(request):
        # Simulate slow handling that will trigger client timeout
        await asyncio.sleep(0.3)
        return web.json_response({'status': 'SUCCESS', 'data': {'late': True}})

    async def inner():
        runner, url = await _start_test_server(handler)
        try:
            agent = singularity_cli.SingularityAgent()
            agent.mcp_server_url = url
            res = await agent.call_mcp_tool('test_tool', {}, timeout=0.05, retries=1)
            assert res['status'] == 'ERROR'
            assert 'timeout' in res['error'].lower() or 'deadline' in res['error'].lower()
        finally:
            await runner.cleanup()

    asyncio.run(inner())
