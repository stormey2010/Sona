#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
configure_docker_network() {
  # Raspberry Pi networks sometimes advertise IPv6 without providing a usable
  # route. Docker's Go resolver can choose that dead route for auth.docker.io.
  # Prefer IPv4 for dual-stack names without disabling IPv6 system-wide.
  local dropin="/etc/systemd/system/docker.service.d/sona-network.conf"
  local changed=0
  if ! grep -qxF 'precedence ::ffff:0:0/96  100' /etc/gai.conf 2>/dev/null; then
    echo 'precedence ::ffff:0:0/96  100' | sudo tee -a /etc/gai.conf >/dev/null
    changed=1
  fi
  if ! sudo test -f "$dropin" || ! sudo grep -qxF 'Environment="GODEBUG=netdns=cgo"' "$dropin"; then
    sudo mkdir -p "$(dirname "$dropin")"
    sudo tee "$dropin" >/dev/null <<'EOF'
[Service]
Environment="GODEBUG=netdns=cgo"
EOF
    changed=1
  fi
  if ((changed)); then
    echo "Docker Hub has an unreachable IPv6 route; configuring Docker to prefer IPv4..."
    sudo systemctl daemon-reload
    sudo systemctl restart docker
  fi
}
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
configure_docker_network
"${DOCKER[@]}" compose version >/dev/null
export SONA_HOST_DIR="$ROOT_DIR"
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"
export HOST_AUDIO_GID="$(getent group audio | cut -d: -f3 || echo 29)"
mkdir -p recordings wakewords/uploads assets/sounds/uploads
echo "Checking Docker Hub access..."
"${DOCKER[@]}" pull --quiet docker:29-cli >/dev/null || {
  echo "Docker Hub is still unreachable. Check the Pi's internet connection, then rerun ./docker-install.sh." >&2
  exit 1
}
"${DOCKER[@]}" compose -f compose.install.yaml up -d --build
ip="$(hostname -I | awk '{print $1}')"
echo "Sona installer dashboard: http://${ip:-localhost}:5054"
echo "Open Setup & settings, complete the form, then choose Save & apply."
