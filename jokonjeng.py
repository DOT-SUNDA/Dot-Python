import requests
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

# ====== KONFIGURASI ======
BOT_TOKEN = '8455364218:AAFoy_mvhZi9HYeTM48hO9aXapE-cYmWuCs'
AUTHORIZED_USER_ID = 6501677690
PORT = 5000
IP_FILE = 'ip_list.txt'

# ====== STATE KONVERSASI ======
LINKS, BUKA, TUTUP, ADD_IP = range(4)
TARGET_TYPE = None  # Untuk menyimpan pilihan target (1=Rebuild, 2=Looping)

# ====== MANAJEMEN IP ======
def load_ips():
    """Memuat daftar IP dari file"""
    if not os.path.exists(IP_FILE):
        return []
    with open(IP_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def save_ips(ips):
    """Menyimpan daftar IP ke file"""
    with open(IP_FILE, 'w') as f:
        for ip in ips:
            f.write(ip + '\n')

# ====== HANDLER UTAMA ======
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan menu panel utama"""
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("⛔ Akses ditolak. Anda tidak diotorisasi.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Set Link & Jadwal", callback_data='setlink')],
        [InlineKeyboardButton("▶️ Start All", callback_data='startall')],
        [InlineKeyboardButton("⏹ Stop All", callback_data='stopall')],
        [InlineKeyboardButton("⚙️ Manage IP", callback_data='manageip')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🛠️ Panel Kontrol Bot - Pilih aksi:', reply_markup=reply_markup)

# ====== HANDLER TOMBOL ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani semua aksi dari tombol inline"""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != AUTHORIZED_USER_ID:
        await query.edit_message_text("⛔ Akses ditolak. Anda tidak diotorisasi.")
        return

    data = query.data

    if data == 'startall':
        await handle_start_all(query)
    elif data == 'stopall':
        await handle_stop_all(query)
    elif data == 'setlink':
        await query.edit_message_text("📩 Kirimkan daftar link (1 link per baris):")
        return LINKS
    elif data == 'manageip':
        await show_ip_management(query)
    elif data == 'addip':
        await query.edit_message_text("➕ Kirim IP yang ingin ditambahkan:")
        return ADD_IP
    elif data == 'clearip':
        save_ips([])
        await query.edit_message_text("✅ Semua IP telah dihapus.")
        await show_ip_management(query)
    elif data.startswith('remove_'):
        ip_to_remove = data[7:]
        ips = load_ips()
        if ip_to_remove in ips:
            ips.remove(ip_to_remove)
            save_ips(ips)
            await query.edit_message_text(f"✅ IP {ip_to_remove} berhasil dihapus.")
            await show_ip_management(query)
        else:
            await query.edit_message_text(f"⚠️ IP {ip_to_remove} tidak ditemukan.")
    elif data == 'back':
        await panel_from_query(query)

async def handle_target_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pemilihan target (Rebuild/Looping)"""
    query = update.callback_query
    await query.answer()

    global TARGET_TYPE
    
    if query.data == 'target_1':
        TARGET_TYPE = "1"
        await execute_start_all(query, "Rebuild")
    elif query.data == 'target_2':
        TARGET_TYPE = "2"
        await execute_start_all(query, "Looping")
    elif query.data == 'cancel_target':
        await query.edit_message_text("❌ Eksekusi script dibatalkan.")
        TARGET_TYPE = None

async def execute_start_all(query, target_name):
    """Eksekusi start all berdasarkan target yang dipilih"""
    RDP_LIST = load_ips()
    await query.edit_message_text(f"🔄 Memulai script ({target_name}) di semua RDP...")
    
    messages = []
    for ip in RDP_LIST:
        try:
            res = requests.post(
                f"http://{ip}:{PORT}/start-script",
                json={"target": TARGET_TYPE},
                timeout=5
            )
            messages.append(f"🔹 {ip} → {res.json().get('message', 'Success')}")
        except Exception as e:
            messages.append(f"🔴 {ip} → Error: {str(e)}")
    
    await query.edit_message_text("\n".join(messages))
    TARGET_TYPE = None

async def panel_from_query(query):
    """Menampilkan panel utama dari query"""
    keyboard = [
        [InlineKeyboardButton("✅ Set Link & Jadwal", callback_data='setlink')],
        [InlineKeyboardButton("▶️ Start All", callback_data='startall')],
        [InlineKeyboardButton("⏹ Stop All", callback_data='stopall')],
        [InlineKeyboardButton("⚙️ Manage IP", callback_data='manageip')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('🛠️ Panel Kontrol Bot - Pilih aksi:', reply_markup=reply_markup)

async def show_ip_management(query):
    """Menampilkan menu manajemen IP dengan daftar yang bisa diklik"""
    current_ips = load_ips()
    
    ip_buttons = []
    for ip in current_ips:
        ip_buttons.append([InlineKeyboardButton(f"❌ {ip}", callback_data=f'remove_{ip}')])
    
    action_buttons = [
        [InlineKeyboardButton("➕ Add IP", callback_data='addip')],
        [InlineKeyboardButton("🗑 Clear All IP", callback_data='clearip')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='back')]
    ]
    
    reply_markup = InlineKeyboardMarkup(ip_buttons + action_buttons)
    
    message = "📋 Daftar IP Saat Ini:\n" + "\n".join([f"• {ip}" for ip in current_ips]) if current_ips else "📭 Tidak ada IP terdaftar"
    await query.edit_message_text(message, reply_markup=reply_markup)

async def handle_start_all(query):
    """Menangani permintaan start all dengan pilihan target"""
    RDP_LIST = load_ips()
    if not RDP_LIST:
        await query.edit_message_text("⚠️ Belum ada IP yang terdaftar.")
        return

    keyboard = [
        [InlineKeyboardButton("🔄 Rebuild", callback_data='target_1')],
        [InlineKeyboardButton("🔁 Looping", callback_data='target_2')],
        [InlineKeyboardButton("❌ Batal", callback_data='cancel_target')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📡 Pilih jenis eksekusi script:", reply_markup=reply_markup)

async def handle_stop_all(query):
    """Menangani permintaan stop all"""
    RDP_LIST = load_ips()
    if not RDP_LIST:
        await query.edit_message_text("⚠️ Belum ada IP yang terdaftar.")
        return

    await query.edit_message_text("🛑 Menghentikan script di semua RDP...")
    messages = []
    for ip in RDP_LIST:
        try:
            res = requests.post(f"http://{ip}:{PORT}/stop-script", timeout=5)
            messages.append(f"🔹 {ip} → {res.json().get('message', 'Success')}")
        except Exception as e:
            messages.append(f"🔴 {ip} → Error: {str(e)}")
    await query.edit_message_text("\n".join(messages))

# ====== HANDLER SET LINK & JADWAL ======
async def setlink_receive_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima daftar link dari pengguna"""
    links = [line.strip() for line in update.message.text.splitlines() if line.strip()]
    if not links:
        await update.message.reply_text("⚠️ Tidak ada link yang valid. Silakan coba lagi.")
        return ConversationHandler.END
    
    context.user_data['links'] = links
    await update.message.reply_text("⏰ Kirim jam buka (format: HH:MM):")
    return BUKA

async def setlink_receive_buka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima jam buka dari pengguna"""
    buka = update.message.text.strip()
    if not validate_time_format(buka):
        await update.message.reply_text("⚠️ Format waktu tidak valid. Gunakan format HH:MM. Silakan coba lagi.")
        return BUKA
    
    context.user_data['buka'] = buka
    await update.message.reply_text("⏰ Kirim jam tutup (format: HH:MM):")
    return TUTUP

async def setlink_receive_tutup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima jam tutup dari pengguna dan memprosesnya"""
    tutup = update.message.text.strip()
    if not validate_time_format(tutup):
        await update.message.reply_text("⚠️ Format waktu tidak valid. Gunakan format HH:MM. Silakan coba lagi.")
        return TUTUP
    
    context.user_data['tutup'] = tutup
    links = context.user_data['links']
    
    try:
        buka_jam, buka_menit = map(int, context.user_data['buka'].split(":"))
        tutup_jam, tutup_menit = map(int, context.user_data['tutup'].split(":"))
    except ValueError:
        await update.message.reply_text("⚠️ Format waktu tidak valid. Silakan mulai kembali.")
        return ConversationHandler.END

    RDP_LIST = load_ips()
    if not RDP_LIST:
        await update.message.reply_text("⚠️ Belum ada IP yang ditambahkan. Tambahkan IP terlebih dahulu.")
        return ConversationHandler.END

    chunk_size = len(links) // len(RDP_LIST)
    chunks = [links[i:i + chunk_size] for i in range(0, len(links), chunk_size)]
    if len(chunks) > len(RDP_LIST):
        chunks[-2].extend(chunks[-1])
        chunks = chunks[:-1]

    messages = ["⚙️ Hasil pembaruan link dan jadwal:"]
    for idx, ip in enumerate(RDP_LIST):
        try:
            payload_link = {
                "link": "\n".join(chunks[idx]) if idx < len(chunks) else ""
            }
            res_link = requests.post(f"http://{ip}:{PORT}/update-link", json=payload_link, timeout=10)

            payload_jadwal = {
                "buka_jam": buka_jam,
                "buka_menit": buka_menit,
                "tutup_jam": tutup_jam,
                "tutup_menit": tutup_menit
            }
            res_jadwal = requests.post(f"http://{ip}:{PORT}/update-waktu", json=payload_jadwal, timeout=10)

            messages.append(f"🔹 {ip} → Link: {res_link.json().get('message', 'Success')} | Jadwal: {res_jadwal.json().get('message', 'Success')}")
        except Exception as e:
            messages.append(f"🔴 {ip} → Error: {str(e)}")

    await update.message.reply_text("\n".join(messages))
    return ConversationHandler.END

def validate_time_format(time_str):
    """Validasi format waktu HH:MM"""
    try:
        hours, minutes = map(int, time_str.split(":"))
        return 0 <= hours < 24 and 0 <= minutes < 60
    except ValueError:
        return False

# ====== HANDLER TAMBAH IP ======
async def add_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menambahkan IP baru ke daftar"""
    ip = update.message.text.strip()
    if not validate_ip(ip):
        await update.message.reply_text("⚠️ Format IP tidak valid. Silakan coba lagi.")
        return ADD_IP
    
    ips = load_ips()
    if ip in ips:
        await update.message.reply_text(f"ℹ️ IP {ip} sudah ada dalam daftar.")
    else:
        ips.append(ip)
        save_ips(ips)
        await update.message.reply_text(f"✅ IP {ip} berhasil ditambahkan.")
    return ConversationHandler.END

def validate_ip(ip):
    """Validasi dasar format IP (sederhana)"""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) < 256 for part in parts)
    except ValueError:
        return False

# ====== HANDLER PEMBATALAN ======
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan operasi saat ini"""
    await update.message.reply_text("❌ Operasi dibatalkan.")
    return ConversationHandler.END

# ====== INISIALISASI BOT ======
if __name__ == '__main__':
    print("🚀 Memulai bot...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handler perintah utama
    app.add_handler(CommandHandler("panel", panel))
    
    # Handler untuk tombol inline
    app.add_handler(CallbackQueryHandler(
        button_handler,
        pattern='setlink|addip|removeip|startall|stopall|manageip|clearip|back'
    ))
    app.add_handler(CallbackQueryHandler(
        handle_target_selection,
        pattern='target_1|target_2|cancel_target'
    ))
    
    # Handler untuk konversasi
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='setlink|addip')],
        states={
            LINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, setlink_receive_links)],
            BUKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, setlink_receive_buka)],
            TUTUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setlink_receive_tutup)],
            ADD_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ip)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(conv_handler)

    print("🤖 Bot siap menerima perintah...")
    app.run_polling()
