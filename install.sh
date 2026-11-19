#!/bin/bash
# Установка / обновление бота на Ubuntu (запускать от root):
#   bash install.sh
set -e
cd "$(dirname "$(readlink -f "$0")")"
DIR="$(pwd)"

apt-get update -qq
apt-get install -y -qq python3-venv git > /dev/null

[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo "!!! Заполни $DIR/.env (nano .env) и запусти: systemctl restart redflag"
fi

cat > /etc/systemd/system/redflag.service <<EOF
[Unit]
Description=REDFLAG Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
User=root
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable redflag > /dev/null 2>&1
systemctl restart redflag
sleep 2
systemctl --no-pager status redflag | head -n 5
echo "Логи: journalctl -u redflag -f"
