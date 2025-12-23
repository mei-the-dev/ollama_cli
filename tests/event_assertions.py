import json
from pathlib import Path
from typing import List, Dict, Optional


def read_events(path: str) -> List[Dict]:
    p = Path(path)
    try:
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return []


def find_event(events: List[Dict], kind: str) -> Optional[Dict]:
    for e in events:
        if e.get("event") == kind:
            return e
    return None


def collect_by_test(events: List[Dict]) -> Dict[str, List[Dict]]:
    out = {}
    for e in events:
        t = e.get("test") or "unknown"
        out.setdefault(t, []).append(e)
    return out
