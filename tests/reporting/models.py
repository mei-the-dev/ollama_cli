from typing import Any, Dict, Optional

# pydantic is nice to have for validation, but we make it optional so the test
# suite can run in minimal environments (CI can add pydantic to the environment
# to enable stricter validation).
try:
    from pydantic import BaseModel

    class ModelEvent(BaseModel):
        ts: str
        test: str
        event: str
        payload: Dict[str, Any]

    class Card(BaseModel):
        test: str
        prompt: str
        answer: str
        parsed_tool: Optional[Dict[str, Any]] = None

except Exception:
    # Fallback lightweight validators
    class ModelEvent:
        def __init__(self, ts: str, test: str, event: str, payload: Dict[str, Any]):
            if not isinstance(ts, str):
                raise TypeError("ts must be str")
            if not isinstance(test, str):
                raise TypeError("test must be str")
            if not isinstance(event, str):
                raise TypeError("event must be str")
            if not isinstance(payload, dict):
                raise TypeError("payload must be dict")

    class Card:
        def __init__(self, test: str, prompt: str, answer: str, parsed_tool: Optional[Dict[str, Any]] = None):
            if not isinstance(test, str):
                raise TypeError("test must be str")
            if not isinstance(prompt, str):
                raise TypeError("prompt must be str")
            if not isinstance(answer, str):
                raise TypeError("answer must be str")
            if parsed_tool is not None and not isinstance(parsed_tool, dict):
                raise TypeError("parsed_tool must be dict or None")
