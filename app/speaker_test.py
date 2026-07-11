"""Play a short ALSA test tone through Sona's configured speaker."""
import os
import subprocess

from .stt import SonaError


def main() -> None:
    device = os.getenv("TTS_AUDIO_DEVICE") or "default"
    print(f"Testing speaker: {device}")
    try:
        subprocess.run(["speaker-test", "--device", device, "--channels=2", "--test", "sine", "--nloops", "1"], check=True)
        print("Speaker test finished.")
    except FileNotFoundError as exc:
        raise SonaError("speaker-test is missing from the container.") from exc
    except subprocess.CalledProcessError as exc:
        raise SonaError(f"Speaker test failed for {device}: {exc}") from exc


if __name__ == "__main__":
    try:
        main()
    except SonaError as exc:
        print(f"Sona error: {exc}")
        raise SystemExit(1)
