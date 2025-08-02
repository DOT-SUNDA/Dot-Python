import requests
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, ConversationHandler, filters

BOT_TOKEN = '8455364218:AAFoy_mvhZi9HYeTM48hO9aXapE-cYmWuCs'
AUTHORIZED_USER_ID = 6501677690  # Ganti dengan User ID kamu

LINKS, BUKA, TUTUP, ADD_IP, REMOVE_IP = range(5)
PORT = 5000
IP_FILE = 'ip_list.txt'

# ====== IP MANAGEMENT ======
def load_ips():
    if not os.path.exists(IP_FILE):
        return []
    with open(IP_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def save_ips(ips):
    with open(IP_FILE, 'w') as f:
        for ip in ips:
            f.write(ip + '\n')

# ====== PANEL BUTTON ======
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    keyboard = [
        [InlineKeyboardButton("✅ Set Link & Jadwal", callback_data='setlink')],
        [InlineKeyboardButton("▶️ Start All", callback_data='startall')],
        [InlineKeyboardButton("⏹ Stop All", callback_data='stopall')],
        [InlineKeyboardButton("⚙️ Manage IP", callback_data='manageip')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Pilih aksi:', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    data = query.data

    if data == 'startall':
        RDP_LIST = load_ips()
        await query.edit_message_text("Memulai script di semua RDP...")
        messages = []
        for ip in RDP_LIST:
            try:
                res = requests.post(f"http://{ip}:{PORT}/start-script", json={"target": "1"}, timeout=5)
                messages.append(f"{ip} -> {res.json()}")
            except Exception as e:
                messages.append(f"{ip} -> Error: {e}")
        await query.edit_message_text("\n".join(messages))

    elif data == 'stopall':
        RDP_LIST = load_ips()
        await query.edit_message_text("Menghentikan script di semua RDP...")
        messages = []
        for ip in RDP_LIST:
            try:
                res = requests.post(f"http://{ip}:{PORT}/stop-script", timeout=5)
                messages.append(f"{ip} -> {res.json()}")
            except Exception as e:
                messages.append(f"{ip} -> Error: {e}")
        await query.edit_message_text("\n".join(messages))

    elif data == 'setlink':
        await query.edit_message_text("Kirimkan daftar link (1 link per baris):")
        return LINKS

    elif data == 'manageip':
        keyboard = [
            [InlineKeyboardButton("➕ Add IP", callback_data='addip')],
            [InlineKeyboardButton("➖ Remove IP", callback_data='removeip')],
            [InlineKeyboardButton("🗑 Clear All IP", callback_data='clearip')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Manage IP:', reply_markup=reply_markup)

    elif data == 'addip':
        await query.edit_message_text("Kirim IP yang ingin ditambahkan:")
        return ADD_IP

    elif data == 'removeip':
        await query.edit_message_text("Kirim IP yang ingin dihapus:")
        return REMOVE_IP

    elif data == 'clearip':
        save_ips([])
        await query.edit_message_text("Semua IP telah dihapus.")

# ====== SET LINK & JADWAL CHAT FLOW ======
async def setlink_receive_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['links'] = [line.strip() for line in update.message.text.splitlines() if line.strip()]
    await update.message.reply_text("Kirim jam buka (format: HH:MM):")
    return BUKA

async def setlink_receive_buka(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['buka'] = update.message.text.strip()
    await update.message.reply_text("Kirim jam tutup (format: HH:MM):")
    return TUTUP

async def setlink_receive_tutup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tutup'] = update.message.text.strip()

    links = context.user_data['links']
    buka_jam, buka_menit = map(int, context.user_data['buka'].split(":"))
    tutup_jam, tutup_menit = map(int, context.user_data['tutup'].split(":"))

    RDP_LIST = load_ips()
    if not RDP_LIST:
        await update.message.reply_text("Belum ada IP yang ditambahkan.")
        return ConversationHandler.END

    chunk_size = len(links) // len(RDP_LIST)
    chunks = [links[i:i + chunk_size] for i in range(0, len(links), chunk_size)]
    if len(chunks) > len(RDP_LIST):
        chunks[-2].extend(chunks[-1])
        chunks = chunks[:-1]

    messages = []
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

            messages.append(f"{ip} -> Link: {res_link.json()} | Jadwal: {res_jadwal.json()}")
        except Exception as e:
            messages.append(f"{ip} -> Error: {e}")

    await update.message.reply_text("\n".join(messages))
    return ConversationHandler.END

# ====== ADD / REMOVE IP ======
async def add_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = update.message.text.strip()
    ips = load_ips()
    if ip not in ips:
        ips.append(ip)
        save_ips(ips)
        await update.message.reply_text(f"IP {ip} ditambahkan.")
    else:
        await update.message.reply_text(f"IP {ip} sudah ada.")
    return ConversationHandler.END

async def remove_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = update.message.text.strip()
    ips = load_ips()
    if ip in ips:
        ips.remove(ip)
        save_ips(ips)
        await update.message.reply_text(f"IP {ip} dihapus.")
    else:
        await update.message.reply_text(f"IP {ip} tidak ditemukan.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END

# ====== MAIN ======
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(button_handler))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='setlink|addip|removeip')],
        states={
            LINKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, setlink_receive_links)],
            BUKA: [MessageHandler(filters.TEXT & ~filters.COMMAND, setlink_receive_buka)],
            TUTUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, setlink_receive_tutup)],
            ADD_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ip)],
            REMOVE_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_ip)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(conv_handler)

    print("Bot is running...")
    app.run_polling()
