#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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
echo "Dashboard ready on port 5054."

