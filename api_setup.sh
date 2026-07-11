#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f .env ]] || { echo "Run ./sona-stt setup first." >&2; exit 1; }
bold=$'\033[1m'; dim=$'\033[2m'; green=$'\033[32m'; reset=$'\033[0m'; [[ -t 1 ]] || bold= dim= green= reset=
screen(){ [[ -t 1 ]] && printf '\033[2J\033[H' || true; }
set_value(){ local k="$1" v="$2" t; t="$(mktemp)"; awk -F= -v k="$k" -v v="$v" '$1==k{print k"="v; f=1; next}{print} END{if(!f)print k"="v}' .env > "$t"; mv "$t" .env; }
get(){ awk -v k="$1" 'index($0,k"=")==1 {sub(/^[^=]*=/,""); v=$0} END{print v}' .env; }
secret(){ local label="$1" name="$2" v saved="missing"; [[ -n "$(get "$name")" ]] && saved="saved"; screen; echo "${bold}${label}${reset}  ${dim}(${saved})${reset}"; echo "${dim}Press Enter to keep this key and continue. Your typing will be visible.${reset}"; read -r -p "New key: " v || v=""; if [[ -n "$v" ]]; then set_value "$name" "$v"; fi; return 0; }

screen
echo "${bold}2 / 9  Speaker${reset}"
mapfile -t speakers < <(aplay -l 2>/dev/null | sed -nE 's/^card [0-9]+: ([^ ]+) \[([^]]+)\].*/\1|\2/p')
current="$(get TTS_AUDIO_DEVICE)"; default=0
for i in "${!speakers[@]}"; do IFS='|' read -r id name <<< "${speakers[$i]}"; device="plughw:CARD=${id},DEV=0"; [[ "$device" == "$current" ]] && default=$((i+1)); printf '  %d) %s%s\n' "$((i+1))" "$name" "$([[ "$device" == "$current" ]] && echo '  (saved)')"; done
echo "  0) system default"
read -r -p "Choose speaker [$default]: " choice || choice=""; choice="${choice:-$default}"
if [[ "$choice" == 0 ]]; then device="default"; set_value TTS_AUDIO_DEVICE ""; elif [[ "$choice" =~ ^[1-9][0-9]*$ ]] && ((choice<=${#speakers[@]})); then IFS='|' read -r id speaker_name <<< "${speakers[$((choice-1))]}"; device="plughw:CARD=${id},DEV=0"; set_value TTS_AUDIO_DEVICE "$device"; else echo "Invalid speaker" >&2; exit 1; fi
read -r -p "Play a test tone now? [y/N]: " test_tone || test_tone=""; test_tone="${test_tone:-n}"
if [[ "$test_tone" =~ ^[Yy]$ ]]; then speaker-test --device "$device" --channels=2 --test=sine --nloops=1 >/dev/null 2>&1 && echo "  ${green}✓ Speaker works${reset}" || echo "  Speaker test failed. Try another output next setup."; fi

secret "3 / 9  Groq — speech recognition and voice" GROQ_API_KEY
secret "4 / 9  Cerebras — assistant intelligence" CEREBRAS_API_KEY
secret "5 / 9  Tavily — web search tools" TAVILY_API_KEY

screen; echo "${bold}6 / 9  Assistant voice${reset}"; echo "${dim}Press Enter to keep the saved voice.${reset}"
voices=(autumn diana hannah austin daniel troy); current="$(get GROQ_TTS_VOICE)"; current="${current:-autumn}"; default=1
for i in "${!voices[@]}"; do [[ "${voices[$i]}" == "$current" ]] && default=$((i+1)); done
echo "  1) autumn  2) diana  3) hannah  4) austin  5) daniel  6) troy"
read -r -p "Choose voice [$default]: " choice || choice=""; choice="${choice:-$default}"; [[ "$choice" =~ ^[1-6]$ ]] || { echo "Invalid voice" >&2; exit 1; }; set_value GROQ_TTS_VOICE "${voices[$((choice-1))]}"

screen; echo "${bold}7 / 9  System prompt${reset}"; echo "${dim}Press Enter to keep the current prompt.${reset}"
read -r -p "> " prompt || prompt=""; [[ -n "$prompt" ]] && set_value CEREBRAS_SYSTEM_PROMPT "$prompt"
[[ -n "$(get CEREBRAS_SYSTEM_PROMPT)" ]] || set_value CEREBRAS_SYSTEM_PROMPT "You are Sona, a concise helpful voice assistant."
set_value STT_BACKEND groq; set_value GROQ_STT_MODEL whisper-large-v3-turbo; set_value GROQ_TTS_MODEL canopylabs/orpheus-v1-english; set_value CEREBRAS_MODEL gpt-oss-120b
