import requests
import os
import re
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
SET_LINK, SET_BUKA, SET_TUTUP, ADD_IP = range(4)

# ====== INISIALISASI ======
def load_ips():
    if not os.path.exists(IP_FILE):
        return []
    with open(IP_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def save_ips(ips):
    with open(IP_FILE, 'w') as f:
        for ip in ips:
            f.write(ip + '\n')

# ====== HANDLER UTAMA ======
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ Set Link & Jadwal", callback_data='set_link')],
        [InlineKeyboardButton("⚙️ Manage IP", callback_data='manage_ip')],
        [InlineKeyboardButton("▶️ Start All", callback_data='start_all')],
        [InlineKeyboardButton("⏹ Stop All", callback_data='stop_all')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🛠️ Panel Kontrol:', reply_markup=reply_markup)

# ====== HANDLER CONVERSATION ======
async def receive_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima daftar link"""
    if not update.message or not update.message.text:
        await update.message.reply_text("⚠️ Input tidak valid")
        return ConversationHandler.END
        
    context.user_data['links'] = update.message.text.split('\n')
    await update.message.reply_text("🕒 Masukkan jam BUKA (HH:MM):")
    return SET_BUKA

async def receive_buka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima jam buka"""
    if not update.message or not update.message.text:
        await update.message.reply_text("⚠️ Input tidak valid")
        return ConversationHandler.END
        
    if not re.match(r'^\d{2}:\d{2}$', update.message.text):
        await update.message.reply_text("⚠️ Format jam salah. Gunakan HH:MM")
        return SET_BUKA
        
    context.user_data['buka'] = update.message.text
    await update.message.reply_text("🕒 Masukkan jam TUTUP (HH:MM):")
    return SET_TUTUP

async def receive_tutup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima jam tutup dan memproses"""
    if not update.message or not update.message.text:
        await update.message.reply_text("⚠️ Input tidak valid")
        return ConversationHandler.END
        
    if not re.match(r'^\d{2}:\d{2}$', update.message.text):
        await update.message.reply_text("⚠️ Format jam salah. Gunakan HH:MM")
        return SET_TUTUP
        
    context.user_data['tutup'] = update.message.text
    
    # Proses data
    await process_schedule(update, context)
    return ConversationHandler.END

async def receive_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima IP baru"""
    if not update.message or not update.message.text:
        await update.message.reply_text("⚠️ Input tidak valid")
        return ConversationHandler.END
        
    ip = update.message.text.strip()
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        await update.message.reply_text("⚠️ Format IP salah. Contoh: 192.168.1.1")
        return ADD_IP
        
    ips = load_ips()
    if ip in ips:
        await update.message.reply_text(f"ℹ️ IP {ip} sudah ada")
    else:
        ips.append(ip)
        save_ips(ips)
        await update.message.reply_text(f"✅ IP {ip} ditambahkan")
    
    await show_ip_menu(update.message)
    return ConversationHandler.END

# ====== FUNGSI PENDUKUNG ======
async def process_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memproses jadwal yang diinput"""
    try:
        links = context.user_data.get('links', [])
        buka = context.user_data.get('buka', '').split(':')
        tutup = context.user_data.get('tutup', '').split(':')
        
        # Validasi waktu
        if len(buka) != 2 or len(tutup) != 2:
            raise ValueError("Format waktu tidak valid")
            
        buka_jam, buka_menit = map(int, buka)
        tutup_jam, tutup_menit = map(int, tutup)
        
        # Kirim ke semua RDP
        results = []
        for ip in load_ips():
            try:
                # Update link
                res_link = requests.post(
                    f"http://{ip}:{PORT}/update-link",
                    json={"link": "\n".join(links)},
                    timeout=10
                )
                
                # Update jadwal
                res_jadwal = requests.post(
                    f"http://{ip}:{PORT}/update-waktu",
                    json={
                        "buka_jam": buka_jam,
                        "buka_menit": buka_menit,
                        "tutup_jam": tutup_jam,
                        "tutup_menit": tutup_menit
                    },
                    timeout=10
                )
                
                results.append(f"{ip}: Link={res_link.status_code}, Jadwal={res_jadwal.status_code}")
            except Exception as e:
                results.append(f"{ip}: Error - {str(e)}")
                
        await update.message.reply_text("📋 Hasil:\n" + "\n".join(results))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def show_ip_menu(message):
    """Menampilkan menu IP"""
    ips = load_ips()
    keyboard = [
        [InlineKeyboardButton(f"❌ {ip}", callback_data=f'remove_{ip}')] for ip in ips
    ] + [
        [InlineKeyboardButton("➕ Add IP", callback_data='add_ip')],
        [InlineKeyboardButton("🗑 Clear All", callback_data='clear_ip')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(
        "📋 Daftar IP:\n" + "\n".join(f"• {ip}" for ip in ips) if ips else "📭 Tidak ada IP",
        reply_markup=reply_markup
    )

# ====== HANDLER TOMBOL ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'set_link':
        await query.edit_message_text("📩 Kirim link (1 per baris):")
        return SET_LINK
        
    elif query.data == 'add_ip':
        await query.edit_message_text("➕ Kirim IP (contoh: 192.168.1.1):")
        return ADD_IP
        
    elif query.data.startswith('remove_'):
        ip = query.data[7:]
        ips = load_ips()
        if ip in ips:
            ips.remove(ip)
            save_ips(ips)
            await query.edit_message_text(f"✅ IP {ip} dihapus")
        else:
            await query.edit_message_text(f"⚠️ IP {ip} tidak ditemukan")
        await show_ip_menu(query)
        
    elif query.data == 'clear_ip':
        save_ips([])
        await query.edit_message_text("✅ Semua IP dihapus")
        await show_ip_menu(query)
        
    elif query.data == 'back':
        await panel_from_query(query)
        
    elif query.data == 'start_all':
        await start_all_rdp(query)
        
    elif query.data == 'stop_all':
        await stop_all_rdp(query)

async def panel_from_query(query):
    keyboard = [
        [InlineKeyboardButton("✅ Set Link & Jadwal", callback_data='set_link')],
        [InlineKeyboardButton("⚙️ Manage IP", callback_data='manage_ip')],
        [InlineKeyboardButton("▶️ Start All", callback_data='start_all')],
        [InlineKeyboardButton("⏹ Stop All", callback_data='stop_all')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('🛠️ Panel Kontrol:', reply_markup=reply_markup)

# ====== FUNGSI RDP ======
async def start_all_rdp(query):
    """Menjalankan script di semua RDP"""
    results = []
    for ip in load_ips():
        try:
            res = requests.post(
                f"http://{ip}:{PORT}/start-script",
                json={"target": "1"},
                timeout=5
            )
            results.append(f"{ip}: {res.status_code}")
        except Exception as e:
            results.append(f"{ip}: Error - {str(e)}")
    await query.edit_message_text("🚀 Start All:\n" + "\n".join(results))

async def stop_all_rdp(query):
    """Menghentikan script di semua RDP"""
    results = []
    for ip in load_ips():
        try:
            res = requests.post(f"http://{ip}:{PORT}/stop-script", timeout=5)
            results.append(f"{ip}: {res.status_code}")
        except Exception as e:
            results.append(f"{ip}: Error - {str(e)}")
    await query.edit_message_text("🛑 Stop All:\n" + "\n".join(results))

# ====== MAIN ======
if __name__ == '__main__':
    print("🚀 Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handler utama
    app.add_handler(CommandHandler("panel", panel))
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler, pattern='^set_link$|^add_ip$')
        ],
        states={
            SET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_links)],
            SET_BUKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_buka)],
            SET_TUTUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tutup)],
            ADD_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ip)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    
    # Handler untuk tombol lainnya
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^manage_ip$|^remove_.*$|^clear_ip$|^back$|^start_all$|^stop_all$'))

    print("🤖 Bot ready!")
    app.run_polling()
