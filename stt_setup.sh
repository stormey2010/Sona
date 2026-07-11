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

echo "Sona Speech-to-Text Backend"
echo ""
echo "1) Local Raspberry Pi (default)"
echo "2) Remote Sona STT server"
echo "0) Exit"
read -r -p "Choose where transcription runs: " choice
case "$choice" in
  1)
    set_value STT_BACKEND local
    set_value STT_REMOTE_URL ""
    echo "Selected local Raspberry Pi transcription."
    ;;
  2)
    read -r -p "Server URL (example: http://192.168.1.50:8080): " url
    url="${url%/}"
    [[ "$url" =~ ^https?://[^[:space:]]+$ ]] || die "Enter a full http:// or https:// URL."
    set_value STT_BACKEND remote
    set_value STT_REMOTE_URL "$url"
    set_value STT_REMOTE_TIMEOUT 180
    echo "Selected remote server: $url"
    ;;
  0) exit 0 ;;
  *) die "Please choose 0, 1, or 2." ;;
esac
echo "Saved. Run ./sona-stt test to use this backend."
