#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
command -v docker >/dev/null 2>&1 || { echo "Docker is required first: https://docs.docker.com/engine/install/" >&2; exit 1; }
if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
  echo "Using sudo for Docker in this session. Log out and back in later to activate Docker-group access."
else
  echo "Docker is installed but its daemon is unavailable. Run: sudo systemctl enable --now docker" >&2
  exit 1
fi
"${DOCKER[@]}" compose version >/dev/null
export SONA_HOST_DIR="$ROOT_DIR"
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"
export HOST_AUDIO_GID="$(getent group audio | cut -d: -f3 || echo 29)"
mkdir -p recordings wakewords/uploads assets/sounds/uploads
"${DOCKER[@]}" compose -f compose.install.yaml up -d --build
ip="$(hostname -I | awk '{print $1}')"
echo "Sona installer dashboard: http://${ip:-localhost}:5054"
echo "Open Setup & settings, complete the form, then choose Save & apply."
