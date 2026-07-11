"""A deliberately idle service so Compose can keep the prepared image running."""
import time

print("Sona STT container is ready. Run ./sona-stt test or ./sona-stt interactive.", flush=True)
while True:
    time.sleep(3600)

