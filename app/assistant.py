import json
from pathlib import Path

from .cloud import ask, groq_transcribe, speak
from .stt import SonaError, record


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
    audio = audio or record()
    heard = groq_transcribe(audio)
    print(f'\nYou said:\n"{heard}"')
    prior = history()
    reply = ask(heard, prior)
    save_history([*prior, {"role": "user", "content": heard}, {"role": "assistant", "content": reply}])
    print(f'\nSona:\n"{reply}"')
    speak(reply)


def main() -> None:
    try:
        respond()
    except SonaError as exc:
        print(f"\nSona error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
