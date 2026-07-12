"""Persistent Sona service used by Docker's restart policy."""
import os
import time

from .telemetry import emit

name = os.getenv("ASSISTANT_NAME", "Sona").strip() or "Sona"

def enabled(name: str) -> bool:
    return os.getenv(name, "false").lower() in {"1", "true", "yes", "on"}


if not enabled("SONA_AUTOSTART"):
    print(f"{name} is ready. Autostart is off; run ./sona-stt assistant or ./sona-stt wakeword.", flush=True)
    emit("service", f"{name} started with autostart off")
    while True:
        time.sleep(3600)
elif os.getenv("WAKEWORD_MODE", "preset").lower() == "off":
    print(f"{name} autostart is on, but the wake word is off. Run setup and select a wake word.", flush=True)
    emit("service", f"{name} autostart is on but wake word is off")
    while True:
        time.sleep(3600)
else:
    print(f"{name} autostart is on. Starting the wake-word listener.", flush=True)
    emit("service", "Wake-word listener started")
    from .wakeword import listen
    while True:
        try:
            listen()
            cooldown = max(0.0, float(os.getenv("WAKEWORD_COOLDOWN_SECONDS", "3")))
            print(f"Waiting {cooldown:g}s before listening again to prevent speaker feedback.", flush=True)
            time.sleep(cooldown)
        except Exception as exc:
            print(f"{name} error: {exc}. Retrying in 5 seconds.", flush=True)
            emit("error", str(exc))
            time.sleep(5)
