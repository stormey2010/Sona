import json
import os
from pathlib import Path

from .cloud import ask, groq_transcribe, speak
from .stt import SonaError, record
from .telemetry import emit, now


HISTORY_PATH = Path("/app/recordings/conversation.json")


def history() -> list[dict[str, str]]:
    try:
        items = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        users = [item for item in items if item.get("role") == "user"][-8:]
        assistants = [item for item in items if item.get("role") == "assistant"][-8:]
        allowed = users + assistants
        return [item for item in items if item in allowed][-16:]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(items: list[dict[str, str]]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    users = [item for item in items if item["role"] == "user"][-8:]
    assistants = [item for item in items if item["role"] == "assistant"][-8:]
    keep = [item for item in items if item in users + assistants][-16:]
    HISTORY_PATH.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")


def respond(audio=None) -> None:
    name = os.getenv("ASSISTANT_NAME", "Sona").strip() or "Sona"
    audio = audio or record()
    heard = groq_transcribe(audio)
    print(f'\nYou said:\n"{heard}"')
    prior = history()
    emit("user_message", heard)
    user_message = {"role": "user", "content": heard, "timestamp": now()}
    save_history([*prior, user_message])
    reply, usage = ask(heard, prior)
    assistant_message = {"role": "assistant", "content": reply, "timestamp": now()}
    save_history([*prior, user_message, assistant_message])
    emit("assistant_message", reply, usage=usage)
    print(f'\n{name}:\n"{reply}"')
    speak(reply)
    emit("tts", "Spoken response completed", voice=os.getenv("GROQ_TTS_VOICE", "autumn"))


def main() -> None:
    try:
        respond()
    except SonaError as exc:
        name = os.getenv("ASSISTANT_NAME", "Sona").strip() or "Sona"
        print(f"\n{name} error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
