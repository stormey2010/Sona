#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
touch .env
set_default() { grep -q "^$1=" .env 2>/dev/null || printf '%s=%s\n' "$1" "$2" >> .env; }
audio_gid="$(getent group audio | cut -d: -f3 || true)"
mic="$(arecord -l 2>/dev/null | sed -n 's/^card [0-9]*: \([^ ]*\).*device \([0-9]*\):.*/plughw:CARD=\1,DEV=\2/p' | head -1)"
speaker="$(aplay -l 2>/dev/null | sed -n 's/^card [0-9]*: \([^ ]*\).*device \([0-9]*\):.*/plughw:CARD=\1,DEV=\2/p' | head -1)"
set_default STT_UID "$(id -u)"
set_default STT_GID "$(id -g)"
set_default AUDIO_GID "${audio_gid:-29}"
set_default STT_AUDIO_DEVICE "${mic:-default}"
set_default ASSISTANT_NAME Sona
set_default TTS_AUDIO_DEVICE "${speaker:-default}"
set_default STT_BACKEND groq
set_default STT_LANGUAGE en
set_default STT_SILENCE_SECONDS 1.2
set_default STT_MAX_RECORD_SECONDS 45
set_default STT_SPEECH_THRESHOLD 300
set_default STT_NOISE_MULTIPLIER 2.5
set_default STT_RECORD_SECONDS 5
set_default WAKEWORD_MODE preset
set_default WAKEWORD_PRESET "hey jarvis"
set_default WAKEWORD_CUSTOM_MODEL wakewords/hey_gideon.tflite
set_default WAKEWORD_THRESHOLD 0.5
set_default WAKEWORD_COOLDOWN_SECONDS 3
set_default WAKE_START_SOUND assets/sounds/start-listening.mp3
set_default WAKE_END_SOUND assets/sounds/end-listening.wav
set_default GROQ_API_KEY ""
set_default GROQ_STT_MODEL whisper-large-v3-turbo
set_default GROQ_TTS_MODEL canopylabs/orpheus-v1-english
set_default GROQ_TTS_VOICE autumn
set_default CEREBRAS_API_KEY ""
set_default CEREBRAS_MODEL gpt-oss-120b
set_default CEREBRAS_SYSTEM_PROMPT ""
set_default TAVILY_API_KEY ""
set_default HOMEASSISTANT_URL ""
set_default HOMEASSISTANT_TOKEN ""
set_default HA_MCP_ENABLED false
set_default SONA_AUTOSTART true
mkdir -p recordings wakewords/uploads assets/sounds/uploads
