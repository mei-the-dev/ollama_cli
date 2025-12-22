"""Ensure no active 'omarchy' tokens remain in code files outside allowed locations.

This test is intended as a safety guard during the rebrand: it fails if any
`.py` files contain the substring "omarchy" except for a short allowlist.

Allowed locations:
- `ref/legacy/` (historical archives)
- `tests/` (tests may assert legacy behavior)
- top-level `omarchy_cli.py` (compatibility shim)
- `.venv/`, `.mypy_cache/`, `logs/`
"""

from pathlib import Path


def test_no_active_omarchy_tokens_in_code_files():
    root = Path(__file__).resolve().parent.parent

    allow_prefixes = {
        (root / "ref" / "legacy").as_posix(),
        (root / "tests").as_posix(),
        (root / ".venv").as_posix(),
        (root / ".mypy_cache").as_posix(),
        (root / "logs").as_posix(),
    }

    allow_files = {(root / "omarchy_cli.py").as_posix()}

    def is_allowed(path: Path) -> bool:
        p = path.as_posix()
        if p in allow_files:
            return True
        for ap in allow_prefixes:
            if p.startswith(ap):
                return True
        return False

    offenders = []
    for path in root.rglob("*.py"):
        if is_allowed(path):
            continue
        try:
            text = path.read_text(errors="ignore").lower()
        except Exception:
            # skip binary / unreadable files
            continue
        if "omarchy" in text:
            # capture the first offending line for context (but allow known-compat occurrences)
            for n, line in enumerate(text.splitlines(), start=1):
                line_low = line.lower()
                if "omarchy" in line_low:
                    # Allowed when referencing compatibility markers or env vars or paths
                    if (
                        ".omarchy" in line_low
                        or "omarchy_mcp_server_url" in line_low
                        or "omarchy_" in line_low
                        or "legacy" in line_low
                        or "deprecated" in line_low
                    ):
                        continue
                    offenders.append(f"{path.relative_to(root)}:{n}: {line.strip()}")
                    break

    assert not offenders, (
        "Found active 'omarchy' tokens in code files outside allowed locations:\n"
        + "\n".join(offenders)
    )
