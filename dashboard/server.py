#!/usr/bin/env python3
"""Trusted-LAN control panel for Sona."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
ENV_PATH = ROOT / ".env"
RECORDINGS = ROOT / "recordings"
ACTIVITY = RECORDINGS / "activity.jsonl"
HISTORY = RECORDINGS / "conversation.json"
PORT = 5054

EDITABLE = {
    "ASSISTANT_NAME", "STT_AUDIO_DEVICE", "TTS_AUDIO_DEVICE", "STT_SILENCE_SECONDS", "STT_MAX_RECORD_SECONDS",
    "STT_SPEECH_THRESHOLD", "STT_NOISE_MULTIPLIER", "STT_LANGUAGE", "STT_RECORD_SECONDS",
    "STT_BACKEND", "GROQ_API_KEY", "GROQ_STT_MODEL", "GROQ_TTS_MODEL", "GROQ_TTS_VOICE",
    "CEREBRAS_API_KEY", "CEREBRAS_MODEL", "CEREBRAS_SYSTEM_PROMPT", "TAVILY_API_KEY", "WAKEWORD_MODE",
    "WAKEWORD_PRESET", "WAKEWORD_CUSTOM_MODEL", "WAKEWORD_THRESHOLD", "WAKE_START_SOUND",
    "WAKE_END_SOUND", "TOOL_CALL_SOUND", "WAKEWORD_COOLDOWN_SECONDS", "HOMEASSISTANT_URL", "HOMEASSISTANT_TOKEN", "HA_MCP_ENABLED", "SONA_AUTOSTART",
}
SECRET_KEYS = {"GROQ_API_KEY", "CEREBRAS_API_KEY", "TAVILY_API_KEY", "HOMEASSISTANT_TOKEN"}


def compose_args(*args: str) -> list[str]:
    config = env_values()
    base = ["docker", "compose"]
    if config.get("HA_MCP_ENABLED", "false").lower() == "true" and config.get("HOMEASSISTANT_URL") and config.get("HOMEASSISTANT_TOKEN"):
        base += ["--profile", "ha-mcp"]
    return [*base, *args]


def env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if raw and not raw.startswith("#") and "=" in raw:
                key, value = raw.split("=", 1)
                values[key] = value
    return values


def write_env(changes: dict[str, object]) -> None:
    values = env_values()
    for key, raw in changes.items():
        if key not in EDITABLE:
            continue
        value = str(raw).replace("\r", " ").replace("\n", " ").strip()
        if key in SECRET_KEYS and not value:
            continue
        values[key] = value
    lines = ["# Sona local settings. This file is ignored by Git."]
    lines.extend(f"{key}={value}" for key, value in values.items())
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def command(args: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out after {timeout} seconds"


def refresh_dashboard() -> None:
    if os.getenv("DASHBOARD_DOCKER_MODE", "false").lower() == "true":
        command(["docker", "compose", "-f", "compose.install.yaml", "up", "-d", "--build", "--force-recreate", "installer"])
    else:
        os._exit(0)


def recent_jsonl(path: Path, limit: int = 100) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return items


def history() -> list[dict]:
    try:
        value = json.loads(HISTORY.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def devices(tool: str) -> list[dict[str, str]]:
    code, output = command([tool, "-l"], timeout=10)
    if code:
        return []
    result = []
    import re
    for line in output.splitlines():
        match = re.match(r"card (\d+): ([^ ]+) \[([^]]+)\], device (\d+):", line)
        if match:
            result.append({"label": match.group(3), "value": f"plughw:CARD={match.group(2)},DEV={match.group(4)}"})
    return result


def overview() -> dict:
    config = env_values()
    code, ps = command(compose_args("ps", "--format", "json"), timeout=20)
    online = code == 0 and '"State":"running"' in ps.replace(" ", "")
    all_activities = recent_jsonl(ACTIVITY, 10000)
    activities = all_activities[-100:]
    tokens = {"prompt": 0, "completion": 0, "total": 0}
    for item in all_activities:
        usage = item.get("usage") or {}
        tokens["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
        tokens["completion"] += int(usage.get("completion_tokens", 0) or 0)
        tokens["total"] += int(usage.get("total_tokens", 0) or 0)
    safe = {key: value for key, value in config.items() if key in EDITABLE and key not in SECRET_KEYS}
    if safe.get("CEREBRAS_SYSTEM_PROMPT") == "You are Sona, a concise helpful voice assistant.":
        safe["CEREBRAS_SYSTEM_PROMPT"] = ""
    safe.update({f"{key}_SAVED": bool(config.get(key)) for key in SECRET_KEYS})
    try:
        uptime = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError):
        uptime = 0
    return {
        "online": online,
        "container": ps,
        "activity": activities[-50:][::-1],
        "history": history()[::-1],
        "tokens": tokens,
        "settings": safe,
        "microphones": devices("arecord"),
        "speakers": devices("aplay"),
        "wakewords": sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "wakewords").rglob("*.tflite")),
        "sounds": sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "assets" / "sounds").rglob("*") if p.suffix.lower() in {".wav", ".mp3"}),
        "host": {"name": socket.gethostname(), "uptime": uptime, "disk_free": shutil.disk_usage(ROOT).free},
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, format: str, *args) -> None:
        pass

    def json_response(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/overview":
            self.json_response(overview())
        elif path == "/api/logs":
            _, output = command(compose_args("logs", "--tail", "250", "--no-color"), timeout=30)
            self.json_response({"logs": output})
        else:
            super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/settings":
                write_env(self.body())
                code, output = command(compose_args("up", "-d", "--build", "--force-recreate"))
                self.json_response({"ok": code == 0, "output": output}, 200 if code == 0 else 500)
            elif path == "/api/upload":
                query = parse_qs(parsed.query)
                kind = query.get("kind", [""])[0]
                filename = Path(query.get("filename", [""])[0]).name
                suffix = Path(filename).suffix.lower()
                allowed = {"sound": {".wav", ".mp3"}, "wakeword": {".tflite", ".onnx"}}
                if kind not in allowed or suffix not in allowed[kind] or not filename:
                    self.json_response({"error": "Unsupported upload type."}, 400); return
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 20 * 1024 * 1024:
                    self.json_response({"error": "File must be between 1 byte and 20 MB."}, 400); return
                folder = ROOT / ("assets/sounds/uploads" if kind == "sound" else "wakewords/uploads")
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / filename
                target.write_bytes(self.rfile.read(length))
                self.json_response({"ok": True, "path": str(target.relative_to(ROOT)).replace("\\", "/")})
            elif path == "/api/action/restart":
                code, output = command(compose_args("restart"))
                self.json_response({"ok": code == 0, "output": output}, 200 if code == 0 else 500)
            elif path == "/api/action/start":
                code, output = command(compose_args("up", "-d"))
                self.json_response({"ok": code == 0, "output": output}, 200 if code == 0 else 500)
            elif path == "/api/action/stop":
                code, output = command(compose_args("stop"))
                self.json_response({"ok": code == 0, "output": output}, 200 if code == 0 else 500)
            elif path == "/api/action/speaker-test":
                requested = self.body().get("device", "")
                args = ["docker", "compose", "run", "--rm"]
                if requested:
                    args += ["-e", f"TTS_AUDIO_DEVICE={requested}"]
                args += ["stt", "python", "-m", "app.speaker_test"]
                code, output = command(args, timeout=60)
                self.json_response({"ok": code == 0, "output": output}, 200 if code == 0 else 500)
            elif path == "/api/action/update":
                outputs = []
                for args in (["git", "pull", "--ff-only"], compose_args("build", "--pull"), compose_args("up", "-d")):
                    code, output = command(list(args))
                    outputs.append(output)
                    if code:
                        self.json_response({"ok": False, "output": "\n".join(outputs)}, 500)
                        return
                self.json_response({"ok": True, "output": "\n".join(outputs)})
                threading.Timer(1.0, refresh_dashboard).start()
            elif path == "/api/action/clear-history":
                HISTORY.unlink(missing_ok=True)
                self.json_response({"ok": True})
            else:
                self.json_response({"error": "Not found"}, 404)
        except Exception as exc:
            self.json_response({"ok": False, "error": str(exc)}, 500)


if __name__ == "__main__":
    RECORDINGS.mkdir(exist_ok=True)
    print(f"Sona dashboard: http://0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
