#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT_DIR/dashboard/bootstrap.sh"
SERVICE=/etc/systemd/system/sona-dashboard.service
sudo tee "$SERVICE" >/dev/null <<EOF
[Unit]
Description=Sona LAN Dashboard
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=$USER
SupplementaryGroups=docker
WorkingDirectory=$ROOT_DIR
ExecStart=/usr/bin/python3 $ROOT_DIR/dashboard/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sona-dashboard.service
sudo systemctl restart sona-dashboard.service
for _ in {1..20}; do
  if curl -fsS http://127.0.0.1:5054/api/overview >/dev/null 2>&1; then
    ip="$(hostname -I | awk '{print $1}')"
    echo "Dashboard ready: http://${ip:-localhost}:5054"
    exit 0
  fi
  sleep 0.25
done
echo "Dashboard failed to start. Recent service output:" >&2
sudo systemctl status sona-dashboard.service --no-pager >&2 || true
sudo journalctl -u sona-dashboard.service -n 30 --no-pager >&2 || true
exit 1
