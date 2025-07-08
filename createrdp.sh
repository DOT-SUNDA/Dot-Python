#!/bin/bash

# Daftar IP VPS
VPS_LIST=(
188.166.176.108
159.223.65.149
157.230.42.21
159.223.37.153
157.245.192.4
143.198.200.139
178.128.50.218
167.71.209.50
206.189.152.232
178.128.209.113
)

# Password SSH
PASSWORD="VPSNEW@2BULAN"

# Perintah yang akan dijalankan (URL SUDAH DIGANTI)
REMOTE_COMMAND='wget -O reinstall.sh https://raw.githubusercontent.com/bin456789/reinstall/refs/heads/main/reinstall.sh; bash reinstall.sh dd --img "http://103.126.226.217:8000/dotajav2.gz" --rdp-port 2003 --password "jokoaja"; reboot'

# Cek expect
if ! command -v expect &> /dev/null; then
    echo "🔧 Menginstal expect..."
    sudo apt update && sudo apt install -y expect
fi

# Fungsi jalankan satu VPS lalu tunggu hingga koneksi terputus (karena reboot)
run_on_vps() {
    local IP="$1"

    echo "🚀 Menyambung ke $IP dan menjalankan script..."

    expect <<EOF
log_user 1
spawn ssh -o StrictHostKeyChecking=no root@$IP
expect {
    "*yes/no" { send "yes\r"; exp_continue }
    "*assword:" { send "$PASSWORD\r" }
}
expect "#"
send "$REMOTE_COMMAND\r"
expect {
    "Connection to $IP closed" {
        puts "🔌 Koneksi ke $IP terputus (reboot dimulai)"
    }
    eof {
        puts "🔌 Koneksi ke $IP terputus (EOF diterima)"
    }
}
EOF
}

# Jalankan satu per satu
for IP in "${VPS_LIST[@]}"; do
    run_on_vps "$IP"
    echo "✅ Selesai untuk $IP"
    echo "----------------------------"
done

echo "🎉 SEMUA VPS SELESAI!"
