#!/bin/bash

# UPDATE DAN INSTALL DEPENDENSI
apt update
apt install -y npm git screen

# CLONE STRATUM-ETHPROXY JIKA BELUM ADA
if [ ! -d "$HOME/stratum-ethproxy" ]; then
    git clone https://github.com/oneevil/stratum-ethproxy $HOME/stratum-ethproxy
fi

cd $HOME/stratum-ethproxy

# INSTALL NODE MODULES
npm install

# BUAT FILE .env
cat <<EOL > .env
REMOTE_HOST=eu.rplant.xyz
REMOTE_PORT=7022
REMOTE_PASSWORD=x
LOCAL_HOST=0.0.0.0
LOCAL_PORT=80
EOL

# MEMBUAT SYSTEMD SERVICE
SERVICE_FILE="/etc/systemd/system/gula.service"

sudo bash -c "cat <<EOL > $SERVICE_FILE
[Unit]
Description=Stratum GULA Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/stratum-ethproxy
EnvironmentFile=$HOME/stratum-ethproxy/.env
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL"

# RELOAD SYSTEMD DAN ENABLE SERVICE
sudo systemctl daemon-reload
sudo systemctl enable gula.service
sudo systemctl start gula.service

echo "Stratum GULA sudah dijalankan dan akan otomatis start saat reboot."
