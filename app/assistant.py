from .cloud import ask, groq_transcribe, speak
from .stt import SonaError, record


def main() -> None:
    try:
        audio = record()
        heard = groq_transcribe(audio)
        print(f'\nYou said:\n"{heard}"')
        reply = ask(heard)
        print(f'\nSona:\n"{reply}"')
        speak(reply)
    except SonaError as exc:
        print(f"\nSona error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
