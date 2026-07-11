#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f .env ]] || { echo "Run ./sona-stt setup first." >&2; exit 1; }
set_value(){ local k="$1" v="$2" t; t="$(mktemp)"; awk -F= -v k="$k" -v v="$v" '$1==k{print k"="v; f=1; next}{print} END{if(!f)print k"="v}' .env > "$t"; mv "$t" .env; }
get(){ awk -F= -v k="$1" '$1==k{v=$2} END{print v}' .env; }
secret(){ local name="$1" v; read -r -s -p "  ${name} (Enter keeps saved): " v; echo; [[ -n "$v" ]] && set_value "$name" "$v"; }

echo ""
echo "${bold:-}Voice & AI${reset:-}"
echo "${dim:-}Keys are hidden and saved only in .env.${reset:-}"
secret GROQ_API_KEY; secret CEREBRAS_API_KEY; secret TAVILY_API_KEY
voices=(autumn diana hannah austin daniel troy); current="$(get GROQ_TTS_VOICE)"; current="${current:-autumn}"; default=1
for i in "${!voices[@]}"; do [[ "${voices[$i]}" == "$current" ]] && default=$((i+1)); done
echo ""
printf 'Voice: 1) autumn  2) diana  3) hannah  4) austin  5) daniel  6) troy\n'
read -r -p "Choose voice [$default]: " choice; choice="${choice:-$default}"; [[ "$choice" =~ ^[1-6]$ ]] || { echo "Invalid voice" >&2; exit 1; }; set_value GROQ_TTS_VOICE "${voices[$((choice-1))]}"
mapfile -t speakers < <(aplay -l 2>/dev/null | sed -nE 's/^card [0-9]+: ([^ ]+) \[([^]]+)\].*/\1|\2/p')
echo ""; echo "Speaker (optional):"; for i in "${!speakers[@]}"; do IFS='|' read -r id name <<< "${speakers[$i]}"; printf '  %d) %s\n' "$((i+1))" "$name"; done; echo "  0) system default"
read -r -p "Choose speaker [0]: " choice; choice="${choice:-0}"
if [[ "$choice" == 0 ]]; then set_value TTS_AUDIO_DEVICE ""; elif [[ "$choice" =~ ^[1-9][0-9]*$ ]] && ((choice<=${#speakers[@]})); then IFS='|' read -r id _ <<< "${speakers[$((choice-1))]}"; set_value TTS_AUDIO_DEVICE "plughw:CARD=${id},DEV=0"; else echo "Invalid speaker" >&2; exit 1; fi
current="$(get CEREBRAS_SYSTEM_PROMPT)"; echo ""; echo "System prompt (one line; Enter keeps saved):"; read -r -p "> " prompt
[[ -n "$prompt" ]] && set_value CEREBRAS_SYSTEM_PROMPT "$prompt"
[[ -n "$(get CEREBRAS_SYSTEM_PROMPT)" ]] || set_value CEREBRAS_SYSTEM_PROMPT "You are Sona, a concise helpful voice assistant."
set_value STT_BACKEND groq; set_value GROQ_STT_MODEL whisper-large-v3-turbo; set_value GROQ_TTS_MODEL canopylabs/orpheus-v1-english; set_value CEREBRAS_MODEL gpt-oss-120b
echo "  Setup saved."
