"""Short non-fatal listening cue playback."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .telemetry import emit


def play_cue(setting_name: str) -> None:
    value = os.getenv(setting_name, "").strip()
    if not value or value.lower() == "off":
        return
    path = Path(value)
    if not path.is_absolute():
        path = Path("/app") / path
    if not path.is_file():
        emit("warning", f"Listening sound not found: {value}")
        return
    device = os.getenv("TTS_AUDIO_DEVICE") or "default"
    command = (["aplay", "--device", device, "--quiet", str(path)] if path.suffix.lower() == ".wav"
               else ["mpg123", "-q", "-a", device, str(path)])
    try:
        subprocess.run(command, check=True, timeout=15)
    except Exception as exc:
        emit("warning", f"Could not play {path.name}: {exc}")
