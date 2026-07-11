#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
die() { echo "Error: $*" >&2; exit 1; }
[[ -f .env ]] || die "Run ./sona-stt setup first to select a microphone."

set_value() {
  local key="$1" value="$2" temp
  temp="$(mktemp)"
  awk -F= -v key="$key" -v value="$value" '
    $1 == key { print key "=" value; found=1; next } { print }
    END { if (!found) print key "=" value }
  ' .env > "$temp"
  mv "$temp" .env
}

echo "Sona Wake-Word Setup"
echo ""
echo "1) Preset wake word"
echo "2) Custom model file (.tflite or .onnx)"
echo "0) Exit"
read -r -p "Choose a mode: " mode

case "$mode" in
  1)
    presets=("alexa" "hey jarvis" "hey mycroft" "hey rhasspy" "current weather" "timers")
    echo ""
    echo "Available preset models:"
    for index in "${!presets[@]}"; do printf '%d) %s\n' "$((index + 1))" "${presets[$index]}"; done
    read -r -p "Choose a wake word: " choice
    [[ "$choice" =~ ^[1-6]$ ]] || die "Please choose a listed preset."
    set_value WAKEWORD_MODE preset
    set_value WAKEWORD_PRESET "${presets[$((choice - 1))]}"
    set_value WAKEWORD_CUSTOM_MODEL ""
    echo "Selected preset: ${presets[$((choice - 1))]}"
    ;;
  2)
    mkdir -p wakewords
    echo "Copy your trained .tflite or .onnx model into: $ROOT_DIR/wakewords/"
    echo "Files currently there:"
    find wakewords -maxdepth 1 -type f \( -name '*.tflite' -o -name '*.onnx' \) -printf '  %f\n' || true
    read -r -p "Custom model filename: " filename
    [[ "$filename" != */* && "$filename" != *..* ]] || die "Enter only a filename from wakewords/."
    [[ "$filename" == *.tflite || "$filename" == *.onnx ]] || die "The model must end in .tflite or .onnx."
    [[ -f "wakewords/$filename" ]] || die "wakewords/$filename does not exist. Copy the model first."
    set_value WAKEWORD_MODE custom
    set_value WAKEWORD_CUSTOM_MODEL "wakewords/$filename"
    echo "Selected custom model: wakewords/$filename"
    ;;
  0) exit 0 ;;
  *) die "Please choose 0, 1, or 2." ;;
esac

threshold="$(awk -F= '$1 == "WAKEWORD_THRESHOLD" {value=$2} END {print value}' .env)"
set_value WAKEWORD_THRESHOLD "${threshold:-0.5}"
echo "Wake-word settings saved. Rebuild with: ./sona-stt update"
