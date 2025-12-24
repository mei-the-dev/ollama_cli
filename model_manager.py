import asyncio
import os
import shutil
import subprocess
from typing import Dict, Optional

try:
    import aiohttp
except Exception:
    aiohttp = None


def _get_env_int(name: str, default: int) -> int:
    try:
        v = os.environ.get(name)
        return int(v) if v is not None else default
    except Exception:
        return default


async def get_gpu_free_memory_mb() -> Optional[int]:
    """Return free GPU memory in MB for the first GPU (if nvidia-smi available).

    Returns None if nvidia-smi isn't available or fails.
    """
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,nounits,noheader"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if out.returncode == 0 and out.stdout:
            # pick the smallest free memory across GPUs
            values = [int(x.strip()) for x in out.stdout.splitlines() if x.strip()]
            if values:
                return min(values)
    except Exception:
        pass
    return None


class ModelClient:
    """Lightweight wrapper around Ollama HTTP streaming endpoints, reuses aiohttp session."""

    def __init__(self, model: str, ollama_url: Optional[str] = None):
        if aiohttp is None:
            raise RuntimeError("aiohttp is required for ModelClient")
        self.model = model
        self.ollama_base = ollama_url or os.environ.get("OLLAMA_URL") or "http://localhost:11434"
        self._session = aiohttp.ClientSession()

    async def stream(self, prompt: str, system: Optional[str] = None, timeout: float = 120.0):
        """Stream chunks from Ollama, yielding strings similarly to previous implementation."""
        payload = {
            "model": self.model,
            "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {"temperature": 0.2},
        }
        chat_url = self.ollama_base.rstrip("/") + "/api/chat"

        async with self._session.post(chat_url, json=payload, timeout=timeout) as resp:
            if resp.status != 200:
                text = await resp.text()
                yield f"Error: Ollama HTTP {resp.status}: {text}"
                return
            async for raw in resp.content:
                if not raw:
                    continue
                text = raw.decode(errors="replace")
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    # try parse json chunk content
                    try:
                        import json

                        chunk = json.loads(line)
                    except Exception:
                        continue
                    msg = None
                    if isinstance(chunk, dict):
                        if "message" in chunk and isinstance(chunk["message"], dict):
                            msg = chunk["message"].get("content", "")
                        elif "delta" in chunk and isinstance(chunk["delta"], dict):
                            msg = chunk["delta"].get("content", "")
                        elif chunk.get("content"):
                            msg = chunk.get("content")
                        elif chunk.get("response"):
                            msg = chunk.get("response")
                    if msg:
                        yield msg

    async def close(self):
        try:
            await self._session.close()
        except Exception:
            pass


class ModelManager:
    """Manages shared ModelClient instances and global concurrency/VRAM checks."""

    def __init__(self):
        self._clients: Dict[str, ModelClient] = {}
        max_calls = _get_env_int("SINGULARITY_MAX_MODEL_CALLS", 4)
        self._sem = asyncio.Semaphore(max_calls)
        self._gpu_min_free_mb = _get_env_int("SINGULARITY_GPU_MIN_FREE_MB", 200)
        self._wait_seconds = _get_env_int("SINGULARITY_MODEL_CALL_WAIT_SEC", 1)

    def _get_client(self, model: str) -> ModelClient:
        if model not in self._clients:
            self._clients[model] = ModelClient(model)
        return self._clients[model]

    async def _wait_for_memory(self):
        """Block until GPU free memory is above threshold (if available)."""
        try:
            free = await get_gpu_free_memory_mb()
            if free is None:
                return
            # wait until free >= threshold
            while free < self._gpu_min_free_mb:
                await asyncio.sleep(self._wait_seconds)
                free = await get_gpu_free_memory_mb()
        except Exception:
            pass

    async def stream(self, model: str, prompt: str, system: Optional[str] = None, timeout: float = 120.0):
        """Acquire capacity and stream results from the model."""
        await self._wait_for_memory()
        async with self._sem:
            client = self._get_client(model)
            async for chunk in client.stream(prompt, system=system, timeout=timeout):
                yield chunk

    async def close_all(self):
        for c in list(self._clients.values()):
            try:
                await c.close()
            except Exception:
                pass
        self._clients.clear()


# Module-level singleton
_default_manager: Optional[ModelManager] = None


def get_default_manager() -> ModelManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ModelManager()
    return _default_manager
