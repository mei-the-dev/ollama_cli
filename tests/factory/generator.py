from __future__ import annotations

from pathlib import Path
from typing import Sequence
from .spec import TestSpec


def write_test_from_spec(spec: TestSpec, out_dir: str | Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"test_factory_{spec.name}.py"
    src = "import pytest\n\n" + spec.to_pytest_code()
    filename.write_text(src, encoding="utf-8")
    return filename


def bulk_write(specs: Sequence[TestSpec], out_dir: str | Path) -> list[Path]:
    paths = []
    for s in specs:
        p = write_test_from_spec(s, out_dir)
        paths.append(p)
    return paths
