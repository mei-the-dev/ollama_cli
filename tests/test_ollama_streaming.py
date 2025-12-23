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


def test_generate_streaming_basic(tmp_path, model_event_logger):
    # Ensure events for this streaming test are written to a temp file
    events_path = tmp_path / "events.jsonl"
    import os
    os.environ["TEST_MODEL_EVENTS_PATH"] = str(events_path)

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

            # Use the agent's higher-level API so PROMPT/ASSISTANT events are emitted
            res = await agent.process_with_tools('hi')
            # process_with_tools returns None for non-tool responses; just ensure conversation history is updated
            assert agent.conversation_history and agent.conversation_history[-1]['content'] == 'Hello world'

            # Validate events were emitted
            lines = list(events_path.read_text(encoding='utf-8').splitlines())
            evs = [json.loads(l) for l in lines]
            kinds = [e.get('event') for e in evs]
            assert 'PROMPT' in kinds
            assert 'ASSISTANT' in kinds
            # Since this streaming response contains no tool call, assert PARSED_TOOL is not emitted
            assert not any(e.get('event') == 'PARSED_TOOL' for e in evs)
        finally:
            await runner.cleanup()

    asyncio.run(inner())
