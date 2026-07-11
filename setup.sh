#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

bold=$'\033[1m'; dim=$'\033[2m'; green=$'\033[32m'; cyan=$'\033[36m'; reset=$'\033[0m'
[[ -t 1 ]] || bold= dim= green= cyan= reset=
screen(){ [[ -t 1 ]] && printf '\033[2J\033[H' || true; }
die(){ echo "Error: $*" >&2; exit 1; }
old_env="$(mktemp)"; [[ -f .env ]] && cp .env "$old_env"; trap 'rm -f "$old_env"' EXIT
value(){ awk -v key="$1" 'index($0,key"=")==1 {sub(/^[^=]*=/,""); v=$0} END{print v}' "$old_env"; }
command -v arecord >/dev/null 2>&1 || die "Audio tools are missing. Run ./install.sh first."

old_mic="$(value STT_AUDIO_DEVICE)"; old_voice="$(value GROQ_TTS_VOICE)"; old_voice="${old_voice:-autumn}"
screen
echo "${bold}${cyan}Sona setup${reset}"
echo "${dim}Press Enter to keep this setting and continue.${reset}"
echo ""
echo "${bold}1 / 9  Microphone${reset}"
mapfile -t cards < <(arecord -l 2>/dev/null | sed -nE 's/^card ([0-9]+): ([^ ]+) \[([^]]+)\].*/\1|\2|\3/p')
((${#cards[@]})) || die "No microphone found. Connect one, then rerun ./sona-stt setup."
default=1
for i in "${!cards[@]}"; do
  IFS='|' read -r card id name <<< "${cards[$i]}"; device="plughw:CARD=${id},DEV=0"
  [[ "$device" == "$old_mic" ]] && default=$((i+1))
  printf '  %d) %s%s%s\n' "$((i+1))" "$name" "$([[ "$device" == "$old_mic" ]] && echo '  (saved)')" ""
done
read -r -p "Choose microphone [$default]: " choice || choice=""; choice="${choice:-$default}"
[[ "$choice" =~ ^[0-9]+$ ]] && ((choice>=1 && choice<=${#cards[@]})) || die "Choose one of the listed numbers."
IFS='|' read -r _ mic_id mic_name <<< "${cards[$((choice-1))]}"
mic="plughw:CARD=${mic_id},DEV=0"

audio_gid="$(getent group audio | awk -F: '{print $3}')"; [[ -n "$audio_gid" ]] || die "Could not read the host audio group."
mkdir -p recordings
[[ -w recordings ]] || sudo chown -R "$(id -u):$(id -g)" recordings

cat > .env <<EOF
# Sona local settings. This file is ignored by Git.
STT_AUDIO_DEVICE=${mic}
STT_MODEL=$(value STT_MODEL)
STT_LANGUAGE=$(value STT_LANGUAGE)
STT_RECORD_SECONDS=$(value STT_RECORD_SECONDS)
AUDIO_GID=${audio_gid}
STT_UID=$(id -u)
STT_GID=$(id -g)
STT_BACKEND=$(value STT_BACKEND)
GROQ_API_KEY=$(value GROQ_API_KEY)
GROQ_STT_MODEL=$(value GROQ_STT_MODEL)
GROQ_TTS_MODEL=$(value GROQ_TTS_MODEL)
GROQ_TTS_VOICE=${old_voice}
TTS_AUDIO_DEVICE=$(value TTS_AUDIO_DEVICE)
CEREBRAS_API_KEY=$(value CEREBRAS_API_KEY)
CEREBRAS_MODEL=$(value CEREBRAS_MODEL)
CEREBRAS_SYSTEM_PROMPT=$(value CEREBRAS_SYSTEM_PROMPT)
TAVILY_API_KEY=$(value TAVILY_API_KEY)
SONA_AUTOSTART=$(value SONA_AUTOSTART)
WAKEWORD_MODE=$(value WAKEWORD_MODE)
WAKEWORD_PRESET=$(value WAKEWORD_PRESET)
WAKEWORD_CUSTOM_MODEL=$(value WAKEWORD_CUSTOM_MODEL)
WAKEWORD_THRESHOLD=$(value WAKEWORD_THRESHOLD)
EOF
sed -i 's/^STT_MODEL=$/STT_MODEL=tiny.en/; s/^STT_LANGUAGE=$/STT_LANGUAGE=en/; s/^STT_RECORD_SECONDS=$/STT_RECORD_SECONDS=5/; s/^STT_BACKEND=$/STT_BACKEND=groq/; s/^GROQ_STT_MODEL=$/GROQ_STT_MODEL=whisper-large-v3-turbo/; s/^GROQ_TTS_MODEL=$/GROQ_TTS_MODEL=canopylabs\/orpheus-v1-english/; s/^CEREBRAS_MODEL=$/CEREBRAS_MODEL=gpt-oss-120b/; s/^SONA_AUTOSTART=$/SONA_AUTOSTART=false/; s/^WAKEWORD_MODE=$/WAKEWORD_MODE=preset/; s/^WAKEWORD_PRESET=$/WAKEWORD_PRESET=hey jarvis/; s/^WAKEWORD_THRESHOLD=$/WAKEWORD_THRESHOLD=0.5/' .env

echo "  ${green}✓${reset} ${mic_name}"
./api_setup.sh
./wakeword_setup.sh
screen
echo "${bold}${cyan}Sona setup${reset}"
echo "${bold}9 / 9  Start automatically${reset}"
current_start="$(awk -v k='SONA_AUTOSTART' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"; current_start="${current_start:-false}"
if [[ "$current_start" == true ]]; then start_default=Y; else start_default=N; fi
read -r -p "Start Sona after every reboot? [$start_default]: " start_choice || start_choice=""
if [[ -z "$start_choice" ]]; then :; elif [[ "$start_choice" =~ ^[Yy]$ ]]; then sed -i 's/^SONA_AUTOSTART=.*/SONA_AUTOSTART=true/' .env; elif [[ "$start_choice" =~ ^[Nn]$ ]]; then sed -i 's/^SONA_AUTOSTART=.*/SONA_AUTOSTART=false/' .env; else die "Enter y, n, or press Enter to keep the saved setting."; fi
screen
summary_speaker="$(awk -v k='TTS_AUDIO_DEVICE' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"; summary_speaker="${summary_speaker:-system default}"
summary_mode="$(awk -v k='WAKEWORD_MODE' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"
if [[ "$summary_mode" == custom ]]; then summary_wake="$(awk -v k='WAKEWORD_CUSTOM_MODEL' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"; elif [[ "$summary_mode" == off ]]; then summary_wake="off"; else summary_wake="$(awk -v k='WAKEWORD_PRESET' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"; fi
echo "${green}${bold}✓ Sona setup complete${reset}"
echo ""
echo "  Microphone: ${mic_name}"
echo "  Speaker:    ${summary_speaker}"
echo "  Voice:      $(awk -v k='GROQ_TTS_VOICE' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"
echo "  Wake word:  ${summary_wake}"
echo "  Autostart:  $(awk -v k='SONA_AUTOSTART' 'index($0,k"=")==1{sub(/^[^=]*=/,""); print}' .env)"
echo ""
echo "Run: ${bold}./sona-stt assistant${reset}"
