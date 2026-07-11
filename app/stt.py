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
        if "Permission denied" in detail and "/app/recordings" in detail:
            raise SonaError(
                "The recordings directory is not writable by the container.\n"
                "Run ./sona-stt setup to repair it, then run ./sona-stt update to rebuild the image."
            ) from exc
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


def record_until_silence() -> Path:
    """Record after a wake word until speech is followed by configured silence."""
    device = setting("STT_AUDIO_DEVICE")
    silence_seconds = float(setting("STT_SILENCE_SECONDS", "1.2"))
    max_seconds = float(setting("STT_MAX_RECORD_SECONDS", "30"))
    threshold = int(setting("STT_SPEECH_THRESHOLD", "120"))
    rate, chunk_ms = 16000, 100
    chunk_bytes = rate * 2 * chunk_ms // 1000
    silence_chunks_needed = max(1, round(silence_seconds * 1000 / chunk_ms))
    max_chunks = max(1, round(max_seconds * 1000 / chunk_ms))
    command = [
        "arecord", "--device", device, "--format=S16_LE", "--channels=1",
        "--rate=16000", "-t", "raw", "--quiet",
    ]
    print(f"Using microphone: {device}")
    print(f"Speak now. Recording stops after {silence_seconds:g}s of silence...")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frames: list[bytes] = []
    speech_started = False
    silent_chunks = 0
    try:
        assert process.stdout is not None
        for _ in range(max_chunks):
            raw = process.stdout.read(chunk_bytes)
            if len(raw) != chunk_bytes:
                detail = process.stderr.read().decode(errors="replace").strip() if process.stderr else ""
                raise SonaError(f"Microphone stream stopped unexpectedly: {detail}")
            frames.append(raw)
            level = audioop.rms(raw, 2)
            if level >= threshold:
                if not speech_started:
                    print("Speech detected.")
                speech_started = True
                silent_chunks = 0
            elif speech_started:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_needed:
                    break
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

    if not speech_started:
        raise SonaError(
            "No speech was detected before the recording limit. Speak closer to the microphone, "
            "or lower STT_SPEECH_THRESHOLD in .env."
        )
    target = recording_path()
    with wave.open(str(target), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"".join(frames))
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


def transcribe_local(path: Path) -> str:
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


def transcribe_remote(path: Path) -> str:
    url = setting("STT_REMOTE_URL").rstrip("/") + "/transcribe"
    language = setting("STT_LANGUAGE", "en")
    timeout = int(setting("STT_REMOTE_TIMEOUT", "180"))
    print(f"Sending recording to STT server: {url}")
    try:
        import requests

        with path.open("rb") as audio:
            response = requests.post(
                url,
                files={"audio": (path.name, audio, "audio/wav")},
                data={"language": language},
                timeout=timeout,
            )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("text")
        if not isinstance(text, str):
            raise SonaError("The STT server returned no transcription text.")
        return text or "(No speech detected.)"
    except SonaError:
        raise
    except requests.HTTPError as exc:
        detail = ""
        if exc.response is not None:
            try:
                detail = str(exc.response.json().get("detail", ""))
            except ValueError:
                detail = exc.response.text.strip()
        raise SonaError(
            f"The STT server rejected the recording ({exc}). {detail}\n"
            "Run ./sona-stt stt-status and ./sona-server logs on the server."
        ) from exc
    except requests.RequestException as exc:
        raise SonaError(
            f"The STT server could not be reached or rejected the recording: {exc}\n"
            "Run ./sona-stt stt-status, confirm the server is running, and check STT_REMOTE_URL."
        ) from exc
    except ValueError as exc:
        raise SonaError(f"The STT server returned invalid JSON: {exc}") from exc


def transcribe(path: Path) -> str:
    backend = setting("STT_BACKEND", "local").lower()
    if backend == "local":
        return transcribe_local(path)
    if backend == "groq":
        from .cloud import groq_transcribe
        return groq_transcribe(path)
    raise SonaError("STT_BACKEND must be local or groq. Run ./sona-stt api-setup.")


def run_once() -> None:
    try:
        path = record()
        text = transcribe(path)
        print('\nYou said:\n"' + text + '"')
    except SonaError as exc:
        print(f"\nSona error: {exc}", file=sys.stderr)
        raise SystemExit(1)
