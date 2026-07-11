"""Small append-only activity feed shared with the LAN dashboard."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ACTIVITY_PATH = Path("/app/recordings/activity.jsonl")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def emit(kind: str, message: str, **details: Any) -> None:
    ACTIVITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    item = {"timestamp": now(), "kind": kind, "message": message, **details}
    with ACTIVITY_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")

