#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f .env ]] || { echo "Run ./sona-stt setup first." >&2; exit 1; }
set_value(){ local k="$1" v="$2" t; t="$(mktemp)"; awk -v k="$k" -v v="$v" 'index($0,k"=")==1 {print k"="v; f=1; next}{print} END{if(!f)print k"="v}' .env > "$t"; mv "$t" .env; }
get(){ awk -v k="$1" 'index($0,k"=")==1 {sub(/^[^=]*=/,""); v=$0} END{print v}' .env; }
current_mode="$(get WAKEWORD_MODE)"; current_preset="$(get WAKEWORD_PRESET)"; current_preset="${current_preset:-hey jarvis}"
echo "Wake word: ${current_mode:-preset} / ${current_preset}"
echo "  Enter) keep saved wake word   1) choose preset   2) custom model   0) turn off"
read -r -p "Choose [Enter]: " mode
case "$mode" in
  "") ;;
  0) set_value WAKEWORD_MODE off; echo "  Wake word off." ;;
  1)
    presets=(alexa "hey jarvis" "hey mycroft" "hey rhasspy" weather timer)
    for i in "${!presets[@]}"; do printf '  %d) %s\n' "$((i+1))" "${presets[$i]}"; done
    read -r -p "Preset [2]: " choice; choice="${choice:-2}"; [[ "$choice" =~ ^[1-6]$ ]] || { echo "Invalid preset" >&2; exit 1; }
    set_value WAKEWORD_MODE preset; set_value WAKEWORD_PRESET "${presets[$((choice-1))]}"; set_value WAKEWORD_CUSTOM_MODEL "" ;;
  2)
    echo "Copy a .tflite or .onnx model into wakewords/ first."
    read -r -p "Model filename: " filename; [[ -f "wakewords/$filename" ]] || { echo "Model not found." >&2; exit 1; }
    set_value WAKEWORD_MODE custom; set_value WAKEWORD_CUSTOM_MODEL "wakewords/$filename" ;;
  *) echo "Invalid choice" >&2; exit 1 ;;
esac
[[ -n "$(get WAKEWORD_THRESHOLD)" ]] || set_value WAKEWORD_THRESHOLD 0.5
