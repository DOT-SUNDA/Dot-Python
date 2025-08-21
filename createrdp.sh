#!/bin/bash

# Daftar IP VPS
VPS_LIST=(
143.198.82.128
165.232.172.105
206.189.93.252
157.230.243.219
139.59.231.217
143.198.211.75
178.128.56.94
167.71.215.44
152.42.207.119
)

# Password SSH
PASSWORD="VPS@2BULAN"

# Cek apakah expect tersedia
if ! command -v expect &> /dev/null; then
    echo "🔧 Menginstal expect..."
    sudo apt update && sudo apt install -y expect
fi

# Fungsi untuk jalankan perintah di satu VPS
run_on_vps() {
    local IP="$1"
    echo "🚀 Menyambung ke $IP dan menjalankan auto reinstall..."

    expect <<EOF
log_user 1
set timeout 120
spawn ssh -o StrictHostKeyChecking=no root@$IP
expect {
    "*yes/no" { send "yes\r"; exp_continue }
    "*assword:" { send "$PASSWORD\r" }
}
expect "#" {
    send -- "wget -O reinstall.sh https://raw.githubusercontent.com/bin456789/reinstall/refs/heads/main/reinstall.sh\r"
    expect "#"
    send -- "bash reinstall.sh dd --img \"http://209.97.171.222/dotbot.gz\" --rdp-port 2003 --password \"jokoaja\"\r"
    expect "#"
    send -- "reboot\r"
}
# Menunggu koneksi terputus karena reboot
expect {
    "Connection to $IP closed" {
        puts "🔌 Koneksi ke $IP terputus (reboot)"
    }
    eof {
        puts "🔌 EOF diterima (reboot)"
    }
}
EOF
}

# Loop ke semua VPS
for IP in "${VPS_LIST[@]}"; do
    run_on_vps "$IP"
    echo "✅ Selesai untuk $IP"
    echo "----------------------------"
done

echo "🎉 SEMUA VPS SELESAI!"
