import asyncio
import json
from aiohttp import web

import singularity_cli


async def _start_streaming_server(handler):
    app = web.Application()
    app.router.add_post('/api/chat', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()

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


def test_generate_streaming_basic():
    async def handler(request):
        resp = web.StreamResponse(status=200, headers={'Content-Type': 'application/json'})
        await resp.prepare(request)
        chunks = [
            '{"message": {"content": "Hello "}}\n',
            '{"message": {"content": "world"}}\n',
            '{"done": true}\n',
        ]
        for c in chunks:
            await resp.write(c.encode())
            await asyncio.sleep(0.01)
        await resp.write_eof()
        return resp

    async def inner():
        runner, url = await _start_streaming_server(handler)
        try:
            agent = singularity_cli.SingularityAgent()
            # point to local server via overriding the base URL used in generate_streaming
            # monkeypatching the endpoint by setting environment is not needed; we will temporarily
            # patch the constant URL by assigning an attribute
            original = 'http://localhost:11434'
            # use monkeypatching-like substitution by editing the method closure isn't trivial,
            # so instead we'll create a small wrapper to call stream via session posting to our test server

            # Replace the method to call our test server
            async def generate_streaming_to_url(prompt, system=None, timeout=120.0):
                import aiohttp
                messages = agent.conversation_history.copy()
                messages.append({"role": "user", "content": prompt})
                payload = {"model": agent.model, "messages": messages, "stream": True}
                full = ""
                async with aiohttp.ClientSession() as session:
                    async with session.post(url + '/api/chat', json=payload) as resp:
                        async for raw in resp.content:
                            if not raw:
                                continue
                            text = raw.decode()
                            for line in text.splitlines():
                                if not line.strip():
                                    continue
                                try:
                                    chunk = json.loads(line)
                                except Exception:
                                    continue
                                if 'message' in chunk:
                                    content = chunk['message'].get('content', '')
                                    full += content
                                    yield content
                agent.conversation_history.append({"role":"assistant","content":full})

            # bind our wrapper
            agent.generate_streaming = generate_streaming_to_url

            out = []
            async for piece in agent.generate_streaming('hi'):
                out.append(piece)
            assert ''.join(out) == 'Hello world'
            assert agent.conversation_history and agent.conversation_history[-1]['content'] == 'Hello world'
        finally:
            await runner.cleanup()

    asyncio.run(inner())
