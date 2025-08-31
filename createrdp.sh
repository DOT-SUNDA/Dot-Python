#!/bin/bash

# Daftar IP VPS
VPS_LIST=(
165.232.171.115
178.128.110.103
104.248.155.32
143.198.221.132
178.128.113.44
159.65.10.241
159.223.82.122
68.183.239.57
139.59.249.1
104.248.147.216
)

# Password SSH
PASSWORD="Dotaja123@HHHH"

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
    send -- "bash reinstall.sh dd --img \"https://dotvps.biz.id/dotbot.gz\" --rdp-port 2003 --password \"jokoaja\"\r"
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
