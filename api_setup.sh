#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f .env ]] || { echo "Run ./sona-stt setup first." >&2; exit 1; }
set_value(){ local k="$1" v="$2" t; t="$(mktemp)"; awk -F= -v k="$k" -v v="$v" '$1==k{print k"="v; f=1; next}{print} END{if(!f)print k"="v}' .env > "$t"; mv "$t" .env; }
secret(){ local name="$1" value; read -r -s -p "$name (leave blank to keep current): " value; echo; [[ -n "$value" ]] && set_value "$name" "$value"; }
echo "Sona API Setup"
echo "Groq: speech-to-text and text-to-speech"
secret GROQ_API_KEY
echo "Cerebras: LLM"
secret CEREBRAS_API_KEY
echo "Tavily: web search, extract, and crawl (use a newly rotated key)"
secret TAVILY_API_KEY
echo "Choose Groq voice: 1) autumn 2) diana 3) hannah 4) austin 5) daniel 6) troy"
read -r -p "Voice [1]: " voice; voices=(autumn diana hannah austin daniel troy); voice="${voice:-1}"; [[ "$voice" =~ ^[1-6]$ ]] || { echo "Invalid voice" >&2; exit 1; }; set_value GROQ_TTS_VOICE "${voices[$((voice-1))]}"
mapfile -t speakers < <(aplay -l 2>/dev/null | sed -nE 's/^card [0-9]+: ([^ ]+) \[([^]]+)\].*/\1|\2/p')
echo "Speakers:"; for i in "${!speakers[@]}"; do IFS='|' read -r id desc <<< "${speakers[$i]}"; printf '%d) %s\n' "$((i+1))" "$desc"; done; echo "0) Skip"; read -r -p "Select speaker: " choice
if [[ "$choice" =~ ^[1-9][0-9]*$ ]] && ((choice<=${#speakers[@]})); then IFS='|' read -r id _ <<< "${speakers[$((choice-1))]}"; set_value TTS_AUDIO_DEVICE "plughw:CARD=${id},DEV=0"; fi
set_value STT_BACKEND groq; set_value GROQ_STT_MODEL whisper-large-v3-turbo; set_value GROQ_TTS_MODEL canopylabs/orpheus-v1-english; set_value CEREBRAS_MODEL gpt-oss-120b
current_prompt="$(awk -F= '$1=="CEREBRAS_SYSTEM_PROMPT"{value=$2} END{print value}' .env)"
read -r -p "System prompt (leave blank to keep current): " prompt
if [[ -n "$prompt" ]]; then set_value CEREBRAS_SYSTEM_PROMPT "$prompt"; elif [[ -z "$current_prompt" ]]; then set_value CEREBRAS_SYSTEM_PROMPT "You are Sona, a concise helpful voice assistant."; fi
echo "Saved API settings to .env. Keys are local and ignored by Git."
