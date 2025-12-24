from pathlib import Path
from typing import Dict, List, Optional


def estimate_tokens(text: str) -> int:
    """Estimate token count for text using a conservative heuristic.

    We prefer a fast, dependency-free heuristic: tokens ~= words * 1.3
    If `tiktoken` is available, prefer it.
    """
    try:
        import tiktoken  # type: ignore

        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(text))
    except Exception:
        words = len(text.split())
        return int(words * 1.3) + 1


class ContextManager:
    """Manage context snippets and files with token-awareness and prioritization."""

    def __init__(self, max_tokens: int = 2000, max_file_size: int = 1024 * 1024):
        self.max_tokens = max_tokens
        self.max_file_size = max_file_size
        self.files: Dict[str, str] = {}  # path -> content
        self.snippets: List[Dict] = []  # list of {'source': str, 'content': str, 'tokens': int}

    def add_file(self, path: Path) -> bool:
        try:
            if not path.exists() or not path.is_file():
                return False
            size = path.stat().st_size
            if size > self.max_file_size:
                return False
            txt = path.read_text(encoding="utf-8", errors="replace")
            self.files[str(path)] = txt
            return True
        except Exception:
            return False

    def add_snippet(self, source: str, content: str) -> None:
        tokens = estimate_tokens(content)
        self.snippets.append({"source": source, "content": content, "tokens": tokens})

    def _truncate_to_tokens(self, text: str, token_budget: int) -> str:
        # Conservative truncation by lines until token budget satisfied
        lines = text.splitlines()
        if not lines:
            return ""
        out = []
        tokens = 0
        for line in lines:
            t = estimate_tokens(line)
            if tokens + t > token_budget:
                break
            out.append(line)
            tokens += t
        return "\n".join(out)

    def build_context_prompt(self) -> str:
        """Build a context string that fits within max_tokens.

        Prioritize:
          1. explicit snippets (user-provided)
          2. small files, sorted by modification time (recent first)
        """
        parts: List[str] = []
        remaining = self.max_tokens

        # Add snippets first
        for s in sorted(self.snippets, key=lambda x: x.get("tokens", 0)):
            t = s.get("tokens", 0)
            if t <= remaining:
                parts.append(f"### {s['source']}\n```\n{s['content']}\n```")
                remaining -= t
            else:
                truncated = self._truncate_to_tokens(s["content"], remaining)
                if truncated:
                    parts.append(f"### {s['source']}\n```\n{truncated}\n```")
                    remaining = 0
                break

        if remaining <= 0:
            return "\n\n".join(parts)

        # Add files (prioritize smaller and more recent)
        file_items = list(self.files.items())
        # sort by mtime desc then by size ascending
        try:
            file_items.sort(key=lambda kv: (Path(kv[0]).stat().st_mtime * -1, len(kv[1])))
        except Exception:
            file_items = file_items

        for path, content in file_items:
            t = estimate_tokens(content)
            if t <= remaining:
                parts.append(f"### {path}\n```\n{content}\n```")
                remaining -= t
            else:
                truncated = self._truncate_to_tokens(content, remaining)
                if truncated:
                    parts.append(f"### {path}\n```\n{truncated}\n```")
                    remaining = 0
                break

        return "\n\n".join(parts)
