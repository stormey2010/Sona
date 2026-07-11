"""Persistent Sona service used by Docker's restart policy."""
import os
import time

def enabled(name: str) -> bool:
    return os.getenv(name, "false").lower() in {"1", "true", "yes", "on"}


if not enabled("SONA_AUTOSTART"):
    print("Sona is ready. Autostart is off; run ./sona-stt assistant or ./sona-stt wakeword.", flush=True)
    while True:
        time.sleep(3600)
elif os.getenv("WAKEWORD_MODE", "preset").lower() == "off":
    print("Sona autostart is on, but the wake word is off. Run setup and select a wake word.", flush=True)
    while True:
        time.sleep(3600)
else:
    print("Sona autostart is on. Starting the wake-word listener.", flush=True)
    from .wakeword import listen
    while True:
        try:
            listen()
        except Exception as exc:
            print(f"Sona error: {exc}. Retrying in 5 seconds.", flush=True)
            time.sleep(5)
