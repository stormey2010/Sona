"""Continuous local OpenWakeWord detection followed by Sona transcription."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from .stt import SonaError, record, setting, transcribe

FRAME_SAMPLES = 1280  # 80 ms at 16 kHz, as recommended by openWakeWord.


def wakeword_config() -> tuple[Path | str, str, str | None]:
    mode = setting("WAKEWORD_MODE", "preset").lower()
    if mode == "preset":
        preset = setting("WAKEWORD_PRESET", "hey jarvis")
        return preset, "tflite", preset
    if mode == "custom":
        model = Path(setting("WAKEWORD_CUSTOM_MODEL"))
        if not model.is_absolute():
            model = Path("/app") / model
        if not model.is_file():
            raise SonaError(
                f"Custom wake-word model was not found: {model}\n"
                "Put a .tflite or .onnx model in wakewords/ and run ./sona-stt wakeword-setup."
            )
        if model.suffix.lower() not in {".tflite", ".onnx"}:
            raise SonaError("A custom wake-word model must end in .tflite or .onnx.")
        return model, "onnx" if model.suffix.lower() == ".onnx" else "tflite", None
    raise SonaError("WAKEWORD_MODE must be preset or custom. Run ./sona-stt wakeword-setup.")


def load_detector() -> tuple[object, str]:
    """Download shared/preset models into a writable persistent volume, then load one."""
    selection, framework, preset = wakeword_config()
    cache = Path(setting("WAKEWORD_MODEL_DIR", "/home/app/.cache/openwakeword"))
    cache.mkdir(parents=True, exist_ok=True)
    try:
        from openwakeword.model import Model
        from openwakeword.utils import download_models

        # download_models also obtains the shared embedding/melspectrogram models.
        # A custom model still needs those shared feature models; Alexa is the small
        # preset used solely to make the utility fetch them.
        download_models(
            model_names=[preset.replace(" ", "_") if preset else "alexa"],
            target_directory=str(cache),
        )
        if preset:
            prefix = preset.replace(" ", "_")
            candidates = sorted(cache.glob(f"{prefix}_v*.{framework}"))
            if not candidates:
                raise SonaError(f"OpenWakeWord did not download the {preset!r} model.")
            model_path = candidates[-1]
            display_name = preset
        else:
            model_path = Path(selection)
            display_name = model_path.stem
        suffix = ".onnx" if framework == "onnx" else ".tflite"
        detector = Model(
            wakeword_models=[str(model_path)],
            inference_framework=framework,
            melspec_model_path=str(cache / f"melspectrogram{suffix}"),
            embedding_model_path=str(cache / f"embedding_model{suffix}"),
        )
        return detector, display_name
    except SonaError:
        raise
    except Exception as exc:
        raise SonaError(
            f"Could not download or load the wake-word model: {exc}\n"
            "Check internet access, then run ./sona-stt wakeword again."
        ) from exc


def listen() -> None:
    if not Path("/dev/snd").exists():
        raise SonaError("/dev/snd is unavailable in the container. Run ./sona-stt setup.")
    if not shutil.which("arecord"):
        raise SonaError("arecord is missing from the container image.")

    threshold = float(setting("WAKEWORD_THRESHOLD", "0.5"))
    device = setting("STT_AUDIO_DEVICE")
    detector, name = load_detector()
    command = [
        "arecord", "--device", device, "--format=S16_LE", "--channels=1", "--rate=16000",
        "-t", "raw", "--quiet",
    ]
    print("Sona Wake Word")
    print(f"Listening for: {name} (threshold {threshold:g})")
    print("Say the wake word, then speak your command after it. Press Ctrl+C to stop.\n")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert process.stdout is not None
        while True:
            raw = process.stdout.read(FRAME_SAMPLES * 2)
            if len(raw) != FRAME_SAMPLES * 2:
                error = process.stderr.read().decode(errors="replace").strip() if process.stderr else ""
                raise SonaError(f"Microphone stream stopped unexpectedly. {error}")
            scores = detector.predict(np.frombuffer(raw, dtype=np.int16))
            detected = [(label, score) for label, score in scores.items() if float(score) >= threshold]
            if not detected:
                continue
            label, score = max(detected, key=lambda item: float(item[1]))
            print(f"Wake word detected: {label} ({float(score):.2f})")
            process.terminate()
            process.wait(timeout=3)
            path = record()
            text = transcribe(path)
            print('\nYou said:\n"' + text + '"\n')
            return
    except KeyboardInterrupt:
        print("\nWake-word listener stopped.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> None:
    try:
        listen()
    except SonaError as exc:
        print(f"\nSona error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
