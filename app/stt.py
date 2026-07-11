"""Recording and local transcription helpers."""
from __future__ import annotations

import audioop
import os
import shutil
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path


class SonaError(RuntimeError):
    """An error that can be shown directly to a Sona user."""


def setting(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise SonaError(f"{name} is not set. Run ./sona-stt setup to choose a microphone.")
    return value


def recording_path() -> Path:
    directory = Path("/app/recordings")
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"recording-{datetime.now():%Y%m%d-%H%M%S}.wav"


def record(seconds: int | None = None) -> Path:
    device = setting("STT_AUDIO_DEVICE")
    seconds = seconds or int(setting("STT_RECORD_SECONDS", "5"))
    if not Path("/dev/snd").exists():
        raise SonaError("/dev/snd is unavailable in the container. Run ./sona-stt setup and check Docker audio permissions.")
    if not shutil.which("arecord"):
        raise SonaError("arecord is missing from the container image.")

    target = recording_path()
    print(f"Using microphone: {device}")
    print(f"Recording for {seconds} seconds...")
    command = ["arecord", "--device", device, "--format=S16_LE", "--channels=1", "--rate=16000", "--duration", str(seconds), str(target)]
    try:
        subprocess.run(command, check=True, text=True, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise SonaError("arecord could not be started.") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip()
        raise SonaError(
            "Recording failed. The selected ALSA device may be disconnected, unsupported, or inaccessible.\n"
            f"arecord said: {detail}\n"
            "Run ./sona-stt devices, then ./sona-stt setup if the device changed."
        ) from exc

    if not target.exists() or target.stat().st_size <= 44:
        raise SonaError("No audio was captured. Check the microphone and selected device.")
    validate_audio(target)
    print(f"Recording complete: {target}")
    return target


def validate_audio(path: Path) -> None:
    try:
        with wave.open(str(path), "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            level = audioop.rms(frames, wav.getsampwidth())
    except (wave.Error, EOFError) as exc:
        raise SonaError(f"The captured file is not a readable WAV recording: {exc}") from exc
    if not frames:
        raise SonaError("No audio was captured.")
    # A low threshold avoids rejecting quiet voices while still catching all-zero recordings.
    if level < 8:
        raise SonaError("Audio is silent. Check the microphone input level, mute switch, and ALSA device.")
    print(f"Audio level: valid (RMS {level})")


def transcribe(path: Path) -> str:
    model_name = setting("STT_MODEL", "tiny.en")
    language = setting("STT_LANGUAGE", "en")
    print(f"Loading Whisper model: {model_name}")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            download_root=os.getenv("STT_MODEL_DIR"),
        )
        print("Transcribing...")
        segments, _ = model.transcribe(str(path), language=language, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:  # faster-whisper does not expose one stable exception hierarchy
        raise SonaError(
            f"Transcription failed: {exc}\n"
            "If this is the first run, ensure the Pi has internet access so the model can download."
        ) from exc
    return text or "(No speech detected.)"


def run_once() -> None:
    try:
        path = record()
        text = transcribe(path)
        print('\nYou said:\n"' + text + '"')
    except SonaError as exc:
        print(f"\nSona error: {exc}", file=sys.stderr)
        raise SystemExit(1)

