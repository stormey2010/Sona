#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
die() { echo "Error: $*" >&2; exit 1; }
run_docker() {
  if docker info >/dev/null 2>&1; then docker "$@"
  elif sudo docker info >/dev/null 2>&1; then sudo docker "$@"
  else die "Docker daemon is unavailable. Run: sudo systemctl enable --now docker"
  fi
}

echo "Sona Speech-to-Text Test Installer"
echo ""
echo "[1/6] Checking system"
[[ "$(uname -m)" =~ ^(aarch64|arm64)$ ]] || die "This project requires 64-bit ARM Linux (Raspberry Pi OS 64-bit)."
if [[ ! -r /proc/device-tree/model ]] || ! tr -d '\0' < /proc/device-tree/model | grep -qi 'Raspberry Pi'; then
  die "This does not appear to be a Raspberry Pi."
fi
echo "Raspberry Pi ARM64 detected."

echo "[2/6] Checking Docker"
if ! command -v docker >/dev/null 2>&1; then
  command -v curl >/dev/null 2>&1 || { sudo apt-get update; sudo apt-get install -y curl; }
  curl -fsSL https://get.docker.com | sudo sh
fi
if ! docker compose version >/dev/null 2>&1 && ! sudo docker compose version >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker-compose-plugin
fi
echo "Docker is installed."
sudo systemctl enable --now docker >/dev/null 2>&1 || true

echo "[3/6] Installing audio tools"
sudo apt-get update
sudo apt-get install -y alsa-utils usbutils curl
sudo usermod -aG docker "$USER"
if ! docker info >/dev/null 2>&1; then
  echo "Docker group membership is not active in this SSH session yet; Sona will use sudo docker for now."
  echo "Log out and back in later to run Docker without sudo."
fi

echo "[4/6] Detecting microphones"
./setup.sh

echo "[5/6] Building speech-to-text container"
run_docker compose build

echo "[6/6] Starting container and checking audio access"
run_docker compose up -d
run_docker compose run --rm stt arecord -l || die "The container cannot list audio capture devices. Check /dev/snd and audio permissions."

echo ""
echo "Setup complete."
echo "Run one test:       ./sona-stt test"
echo "Run interactive:    ./sona-stt interactive"
echo "View logs:          ./sona-stt logs"
