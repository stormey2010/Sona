# Sona: Raspberry Pi Docker speech-to-text test

Sona is a deliberately small, local test for one path only:

```text
USB microphone -> Raspberry Pi -> Docker container -> WAV recording -> faster-whisper -> text in your SSH terminal
```

It includes optional local wake-word detection, but does not include text-to-speech, Home Assistant, a web UI, cloud speech APIs, MQTT, an LLM, or authentication. Its job is to prove that the Pi can pass USB microphone audio safely into Docker and transcribe it locally.

Sona can use Groq for speech-to-text and text-to-speech, Cerebras for the assistant LLM, and Tavily for web search, extraction, and crawling.

## What you need

- Raspberry Pi 5 with **64-bit Raspberry Pi OS** and an internet connection.
- SSH access to the Pi. You can do the entire install from SSH; no desktop is required.
- A USB microphone (or USB microphone array) connected before setup.
- About 2 GB of free disk space for Docker, Python packages, and the first Whisper model download. `tiny.en` is the default and is the sensible first test on a Pi 5.

> Do not run this on 32-bit Raspberry Pi OS. The installer deliberately stops on non-ARM64 systems.

## First installation, from an empty Raspberry Pi

1. SSH into the Pi, then update its package list and install Git if it is not already installed:

   ```bash
   sudo apt-get update
   sudo apt-get install -y git
   ```

2. Plug in the USB microphone. You can confirm that the Pi sees USB hardware with:

   ```bash
   lsusb
   ```

3. Clone Sona and enter the new folder:

   ```bash
   git clone https://github.com/stormey2010/Sona.git sona-stt
   cd sona-stt
   ```

4. Make the scripts executable and run the installer:

   ```bash
   chmod +x install.sh setup.sh sona-stt
   ./install.sh
   ```

5. The installer checks that this is a 64-bit Raspberry Pi, installs Docker if necessary, installs ALSA/USB tools, adds your current SSH user to the `docker` group, and opens the microphone selector. Pick the number for your microphone.

   It then writes `.env`, configures Docker to prefer working IPv4 routes when contacting Docker Hub (without disabling IPv6), verifies that the Python base image can download, builds the ARM64 Docker image, starts the prepared container, and verifies that the container can see recording devices. On the first install Docker membership normally is not active until you log out and back in. That is okay: Sona automatically falls back to `sudo docker` during this session.

6. Record and transcribe your first sample:

   ```bash
   ./sona-stt test
   ```

   Speak normally while the five-second recording runs. The first transcription downloads the `tiny.en` Whisper model, so it can take longer than later runs. A successful result ends with:

   ```text
   You said:
   "your recognized speech appears here"
   ```

7. For repeated tests without retyping the command:

   ```bash
   ./sona-stt interactive
   ```

   Press Enter to record another five-second sample. Type `q` then Enter to exit.

## Everyday commands

All commands run from the cloned `sona-stt` folder.

| Command | What it does |
| --- | --- |
| `./sona-stt setup` | Re-detect microphones and rewrite `.env` with a new selection. Use after swapping microphones. |
| `./sona-stt test` | Record once, save a WAV in `recordings/`, check it is not silent, and transcribe it. |
| `./sona-stt interactive` | Repeat record/transcribe tests until you enter `q`. |
| `./sona-stt stt-setup` | Choose whether Whisper runs on the Pi or a Sona server. |
| `./sona-stt stt-status` | Show local mode or check the configured server health endpoint. |
| `./sona-stt wakeword-setup` | Choose a built-in OpenWakeWord phrase or a custom local model file. |
| `./sona-stt wakeword` | Listen continuously for the selected wake word, then record and transcribe one command. |
| `./sona-stt wakewords` | List supported preset models and custom files available in `wakewords/`. |
| `./sona-stt devices` | Show host recording devices, all ALSA names, USB devices, and container recording devices. |
| `./sona-stt logs` | Follow the prepared container log. Press Ctrl+C to stop following logs only. |
| `./sona-stt restart` | Restart the prepared Compose container. |
| `./sona-stt stop` | Stop the prepared Compose container. |
| `./sona-stt update` | Pull the newest Git commit, rebuild using newer base images where available, and start it. |

The direct Docker commands are also useful:

```bash
docker compose run --rm stt python -m app.record_test
docker compose run --rm -it stt python -m app.interactive
docker compose run --rm stt arecord -l
docker compose run --rm stt arecord -L
docker compose logs -f
```

If `docker` says permission is denied immediately after installing, substitute `sudo docker` or log out of SSH and log in again. The helper commands detect this and use `sudo docker` automatically.

`update` intentionally opens the microphone selector again. This refreshes the audio group and numeric user IDs used by the non-root container, preventing a changed USB device or filesystem permission from breaking recordings after an update.

## API assistant setup

First install and every `./sona-stt update` run one ten-step wizard: microphone, end-of-speech silence time, speaker plus optional test tone, Groq key, Cerebras key, Tavily key, TTS voice, system prompt, wake word, and start-on-reboot. Each setting gets its own clean terminal screen. Press Enter to keep only the current value and continue to the next screen. API keys are visible while being typed, but saved keys are never displayed afterward and `.env` remains excluded from Git.

On the Pi, select remote mode:

```bash
cd ~/sona-stt
./sona-stt update
./sona-stt assistant
```

The setup identifies each service before requesting its key: Groq for STT/TTS, Cerebras for the LLM, and Tavily for web tools. Keys are saved only in ignored `.env`. Rotate any key that was pasted into a chat before entering it. Setup also offers Groq voices (`autumn`, `diana`, `hannah`, `austin`, `daniel`, `troy`) and detected ALSA speakers. `assistant` records, uses Groq STT, lets Cerebras answer with Tavily web tools when needed, then plays Groq TTS. Set `STT_BACKEND=local` in `.env` if you want tests to retain local Whisper.

The system prompt is asked during guided setup. To edit it later, run `./sona-stt prompt`; leave API-key prompts blank to retain their existing values, then enter the replacement system prompt. Sona stores the most recent eight user messages and eight assistant responses in `recordings/conversation.json`, which is sent with later requests as short-term conversation history. Delete that file to clear the conversation.

After wake-word detection, Sona records until you finish speaking instead of using a fixed five-second window. `STT_SILENCE_SECONDS` controls how long the microphone must remain quiet before recording stops (default `1.2`, configurable from `0.2` to `10` during setup). While waiting for the wake word, Sona measures the room's audio floor and automatically raises the speech threshold above steady fan, HVAC, and electrical noise. Setup offers sensitive, normal, and strong noise rejection. `STT_MAX_RECORD_SECONDS` provides a 30-second safety limit.

Use `./sona-stt speaker-test` to play a short tone through the selected speaker. This tests output separately from the microphone and AI services.

## LAN dashboard

Sona installs a responsive control dashboard on port `5054`. Open `http://PI-IP:5054` from a phone, tablet, or computer on the same trusted network. Run `./sona-stt dashboard` to print the exact URL.

The dashboard shows live online state, recent wake-word and assistant activity, timestamped conversation messages, Cerebras prompt/completion/total token usage, host uptime, Docker logs, and current device configuration. Setup & Settings can change microphones, speakers, silence/noise controls, models, voice, system prompt, wake word, autostart, and API keys. Blank API-key fields preserve the saved values. Restart and Update controls manage the Docker service directly from the Pi host.

The dashboard intentionally listens on the trusted LAN and has no login yet. Do not port-forward port `5054` or expose it to the public internet, because it can change settings and restart/update Sona.

### Choose terminal or web setup

`./install.sh` and `./sona-stt update` start and verify the dashboard before setup. Press `1` for terminal setup or `2` for web setup; the command prints the Pi's exact URL, such as `http://192.168.1.50:5054`. If port 5054 cannot start, the script prints the systemd status and journal instead of claiming it worked.

The web setup can build the container on a fresh installation. Choose the microphone, speaker, wake word, listening sounds, and API settings, then press **Save & apply**.

You can also rename the assistant in **Setup & settings**. The chosen name is used by the dashboard, terminal responses, service messages, and built-in system prompt. Renaming the assistant does not retrain the wake-word model; upload or select a matching wake-word model separately.

### Listening sounds and uploads

Sona plays the included start sound after hearing the wake word and the included end sound when end-of-speech detection stops recording. In **Setup & settings**, select either sound or turn it off. You can upload `.wav`/`.mp3` cue sounds and `.tflite`/`.onnx` OpenWakeWord models from the phone or computer viewing the dashboard. User uploads stay on the Pi and are ignored by Git.

After speaking a complete TTS response, Sona waits three seconds before reopening the wake-word microphone. Adjust **After-speaking cooldown** in the dashboard if the speaker still retriggers the wake word. Increase the wake threshold slightly as a second defense against false triggers; decrease it only when the real wake phrase is being missed.

The built-in system prompt is optimized for spoken answers: quick, direct, plain sentences without numbered lists, parentheses, markdown, or unnecessary detail. It explains the web search, page extraction, crawling, and Home Assistant tools and tells the assistant to verify tool results. Leave the system-prompt box blank to use this built-in prompt, or enter your own replacement.

The included `tool-call-notification.wav` plays immediately before the assistant performs a web search, extracts or crawls a page, checks Home Assistant, or controls a Home Assistant device. Select a different sound or turn it off with **Tool-call sound** in the dashboard. Tool calls also appear in the activity feed.

The **Wake threshold** field is editable in web settings from `0.05` through `1.0`. Higher values reduce accidental wake-ups; lower values make the real phrase easier to trigger but increase false detections. Start around `0.5`, then adjust in steps of `0.05`.

## Fully Docker-based installation

This alternative keeps both setup and the voice assistant in Docker. The first container is the `sona-install:local` image: it serves the setup dashboard on port `5054`, detects `/dev/snd`, writes the project `.env`, and controls the host Docker engine through its socket. After **Save & apply**, it builds and starts the normal `sona-stt:local` voice image.

### Step 1: check whether Docker is already installed

Run:

```bash
docker --version
docker compose version
```

If both commands print versions, skip to Step 3. If either says `command not found`, install Docker below.

### Step 2: install Docker on Raspberry Pi OS 64-bit

These commands use Docker's official Debian repository, which supports ARM64 and current 64-bit Raspberry Pi OS releases including Trixie. Run them one block at a time:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add Docker's package repository:

```bash
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
```

Install Docker Engine, Buildx, and the Docker Compose plugin:

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

If APT reports conflicts with an older distribution-provided Docker installation, remove only those conflicting packages and repeat the install command:

```bash
sudo apt remove docker.io docker-compose docker-doc podman-docker containerd runc
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

This package removal does not automatically delete existing Docker images or volumes, but review the APT confirmation before accepting it.

Verify the installation:

```bash
sudo docker run --rm hello-world
sudo docker compose version
```

Docker-group access normally becomes active after logging out and back in. Sona's installer automatically uses `sudo docker` during the current session if necessary, so you can continue immediately.

### Step 3: download and start Sona's Docker installer

```bash
git clone https://github.com/stormey2010/Sona.git sona-stt
cd sona-stt
chmod +x docker-install.sh
./docker-install.sh
```

If the repository was already downloaded, update it instead:

```bash
cd ~/sona-stt
git pull --ff-only
./docker-install.sh
```

The last line prints the exact dashboard address, such as `http://192.168.1.50:5054`. Open it from another device on the same network, complete **Setup & settings**, and press **Save & apply**. No host Python installation or systemd dashboard service is used by this method.

Check the installer at any time with:

```bash
sudo docker ps --filter name=sona-install
sudo docker logs --tail 100 sona-install
```

The dashboard's **Update** button pulls the repository, rebuilds and restarts `sona-stt:local`, then rebuilds and replaces `sona-install:local` so both Docker images receive updates. The page may disconnect briefly while its own dashboard container is replaced; refresh it after about ten seconds.

The Docker installer mounts `/var/run/docker.sock`, which gives the dashboard full control of Docker on that Pi. Keep port `5054` restricted to a trusted LAN and never expose it to the public internet.

### Home Assistant and HA-MCP

In Home Assistant, open your profile and create a **Long-Lived Access Token**. In Sona's web settings, enter the Home Assistant URL (for example `http://192.168.1.20:8123`), paste the token, and set **Home Assistant tools** to on. Saving starts the official HA-MCP container and gives Sona focused tools for entity search, state lookup, and service calls. The saved token stays in the ignored `.env` file and is not returned to the browser.

Configure only this HA-MCP method for Sona. The upstream project warns that configuring two HA-MCP servers for one client can cause connection hangs.

Run one assistant conversation manually with `./sona-stt assistant`. Run the wake-word listener in the current SSH session with `./sona-stt wakeword`. If start-on-reboot is enabled in setup, Docker starts Sona's wake-word assistant automatically whenever the Pi and Docker restart; check it with `./sona-stt logs` and disable it by running setup again and choosing `n` at the final step. Because the background listener owns the microphone, stop it before a manual test with `./sona-stt stop`, run `./sona-stt assistant`, then restore autostart with `./sona-stt start`.

Keep the server on your trusted LAN. The simple server intentionally has no authentication and should not be exposed to the public internet or port-forwarded.

## How microphone selection works

`./setup.sh` reads `arecord -l` and offers detected capture cards as numbered choices. It stores a name such as:

```env
STT_AUDIO_DEVICE=plughw:CARD=Array,DEV=0
```

in a local `.env` file, along with the host `audio` group ID. The Compose file passes `/dev/snd` into the container and adds that audio group; it does **not** use privileged Docker mode.

Setup also records your numeric Linux user and group IDs. The container uses those IDs, which lets its non-root process save WAV files to the local `recordings/` directory without weakening the directory permissions.

Sona prefers the ALSA card identifier (`CARD=Array`) over a numeric card number (`hw:3,0`). USB audio card numbers can change after a reboot or when devices are unplugged; the card identifier is usually stable. If the card identifier itself changes or the microphone disappears, run:

```bash
./sona-stt devices
./sona-stt setup
```

`arecord -L` lists all ALSA device names. A selected device is recorded as mono, 16-bit PCM, 16 kHz WAV—the expected format for this simple Whisper test.

## Change the Whisper model or recording length

After `./sona-stt setup` creates `.env`, edit it with a terminal editor such as `nano .env`:

```bash
nano .env
```

Useful settings are:

```env
STT_MODEL=tiny.en
STT_LANGUAGE=en
STT_RECORD_SECONDS=5
```

For better English accuracy at a higher CPU/RAM cost, set `STT_MODEL=base.en` or `small.en`. Use `tiny`/`base`/`small` (without `.en`) with an appropriate `STT_LANGUAGE` for multilingual speech. Run `./sona-stt test` afterward; the selected model downloads once into Docker's persistent `whisper-models` volume and is reused on later runs.

## Wake-word detection

Sona uses OpenWakeWord locally in the same microphone-enabled container. It listens to 16 kHz microphone audio in short frames. Once the selected phrase reaches the configured confidence threshold, it stops listening, records the next five seconds, and transcribes that command.

The container intentionally pins NumPy below version 2 because OpenWakeWord's ARM TFLite runtime is currently built against the NumPy 1.x ABI.

After updating and rebuilding Sona, choose a built-in model:

```bash
./sona-stt wakeword-setup
./sona-stt update
./sona-stt wakeword
```

The built-in English models are `alexa`, `hey jarvis`, `hey mycroft`, `hey rhasspy`, `weather`, and `timer`. They are downloaded automatically into Sona's persistent Docker volume on first use. `weather` recognizes current-weather requests and `timer` recognizes timer requests. The default threshold is `0.5`; raise `WAKEWORD_THRESHOLD` in `.env` to reduce false triggers, or lower it if the phrase is missed.

### Use your own wake word

OpenWakeWord needs a trained model for a new phrase; typing a phrase alone cannot create one. Train or obtain a compatible `.tflite` or `.onnx` OpenWakeWord model, then copy it to `wakewords/` on the Pi. For example:

```bash
cp /path/to/my-wake-word.tflite ~/sona-stt/wakewords/
cd ~/sona-stt
./sona-stt wakeword-setup
./sona-stt update
./sona-stt wakeword
```

Select **Custom model file**, enter `my-wake-word.tflite`, then let the update rebuild the image. Custom model files remain local and are excluded from Git. OpenWakeWord documents a training notebook for creating custom models; expect to train the model outside the Pi, then copy the finished file here. [OpenWakeWord documentation](https://github.com/dscripka/openWakeWord#training-new-models)

## Troubleshooting

### No microphone in setup

Reconnect it, then inspect USB and ALSA discovery:

```bash
lsusb
arecord -l
arecord -L
```

If it appears in `lsusb` but not in `arecord -l`, the device may not expose an ALSA capture interface or may need a different USB cable/port.

### Selected device no longer exists

This happens after a microphone swap or a changed ALSA card name. Re-run `./sona-stt setup`, select the listed microphone, then run `./sona-stt test` again.

### Permission denied / container has no audio device

First check the host device and group:

```bash
ls -l /dev/snd
getent group audio
```

Then check what Docker sees:

```bash
./sona-stt devices
docker compose run --rm stt arecord -l
```

Run `./sona-stt setup` after changing host audio configuration so `.env` gets the current `AUDIO_GID`. Docker must be running, and the installer must have successfully created `.env` before Compose can pass the audio group into the container.

### Recording is silent

Use `./sona-stt devices` to verify the selected device, run setup again if needed, and check physical mute buttons or microphone gain. Sona rejects all-zero/nearly-silent WAV files before sending them to Whisper, and keeps recordings under `recordings/` so you can inspect them.

### The first model download fails

The first `test` needs internet access to fetch the Whisper model. Verify DNS/network access, then retry. Docker stores models in its named volume, so later tests do not redownload the same model.

### Docker Hub shows an unreachable IPv6 address

Current Sona installs configure Docker's resolver to prefer IPv4 for Docker Hub while leaving normal IPv6 networking enabled. If a previous install stopped at a Docker Hub `network is unreachable` error, update the project with the recovery steps below and rerun the installer. Do not disable IPv6 with `sysctl`; doing so can disconnect an SSH session that uses IPv6.

## Repair or update an existing installation

If you installed an older Sona version, or a build/recording/model download failed, run these commands one line at a time:

```bash
cd ~/sona-stt
git pull --ff-only
./setup.sh
sudo docker compose down -v
./install.sh
./sona-stt test
```

Choose your microphone when `setup.sh` prompts; it upgrades the local `.env` with the current user and audio settings before Compose runs. `down -v` removes only Sona's stopped containers and its downloaded Whisper-model volume. Use it for this first repair so the replacement non-root container gets a clean writable model cache. It does not remove your project files or `recordings/` WAV files.

### Docker daemon unavailable

Start Docker and retry:

```bash
sudo systemctl enable --now docker
sudo docker info
```

## Complete uninstall

From the project folder, stop containers and remove the project image/volumes:

```bash
./sona-stt stop
sudo systemctl disable --now sona-dashboard
sudo rm -f /etc/systemd/system/sona-dashboard.service
sudo docker compose down --rmi local --volumes --remove-orphans
cd ..
rm -rf sona-stt
```

Removing volumes also removes downloaded Whisper models. The installer adds your SSH user to the Docker group; if you want to undo that separately, run `sudo gpasswd -d "$USER" docker` and log in again.

## Project tree

```text
sona-stt/
├── app/
│   ├── __init__.py
│   ├── assistant.py
│   ├── cloud.py
│   ├── interactive.py
│   ├── record_test.py
│   ├── service.py
│   ├── speaker_test.py
│   ├── stt.py
│   ├── telemetry.py
│   └── wakeword.py
├── dashboard/
│   ├── static/
│   │   ├── app.js
│   │   ├── index.html
│   │   └── style.css
│   ├── install.sh
│   └── server.py
├── .gitignore
├── compose.yaml
├── Dockerfile
├── install.sh
├── requirements.txt
├── setup.sh
├── sona-stt
├── wakeword_setup.sh
├── wakewords/
└── README.md
```

`.env`, recordings, downloaded models, and Python caches are intentionally excluded from Git.
