import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters
import json
import os
from datetime import datetime

# Configuration
DEFAULT_API_PORT = 5000
TOKEN = "8455364218:AAFoy_mvhZi9HYeTM48hO9aXapE-cYmWuCs"  # Replace with your Telegram bot token
ADMIN_IDS = [6501677690]  # Replace with your admin ID(s)
IP_LIST_FILE = "ip_list.json"  # File to store IP addresses

# Initialize IP list
if not os.path.exists(IP_LIST_FILE):
    with open(IP_LIST_FILE, "w") as f:
        json.dump({"ips": []}, f)

# Helper functions
def is_admin(update: Update):
    return update.effective_user.id in ADMIN_IDS

def get_ip_list():
    with open(IP_LIST_FILE, "r") as f:
        return json.load(f).get("ips", [])

def save_ip_list(ip_list):
    with open(IP_LIST_FILE, "w") as f:
        json.dump({"ips": ip_list}, f)

def send_api_request(ip, endpoint, method="GET", data=None, port=DEFAULT_API_PORT):
    url = f"http://{ip}:{port}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json=data, timeout=5)
        
        return {
            "ip": ip,
            "response": response.json() if response.content else {"status": response.status_code}
        }
    except Exception as e:
        return {
            "ip": ip,
            "error": str(e)
        }

def send_mass_request(endpoint, method="GET", data=None, target_ips=None):
    if target_ips is None:
        target_ips = get_ip_list()
    
    results = []
    for ip in target_ips:
        results.append(send_api_request(ip, endpoint, method, data))
    return results

# Command handlers
def start(update: Update, context: CallbackContext):
    if not is_admin(update):
        update.message.reply_text("❌ Anda tidak memiliki akses ke bot ini.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔄 Status Script", callback_data='status')],
        [InlineKeyboardButton("▶️ Start Script", callback_data='start_script'),
         InlineKeyboardButton("⏹️ Stop Script", callback_data='stop_script')],
        [InlineKeyboardButton("⏰ Lihat Jadwal", callback_data='view_schedule'),
         InlineKeyboardButton("✏️ Edit Jadwal", callback_data='edit_schedule')],
        [InlineKeyboardButton("🔗 Update Link", callback_data='update_link')],
        [InlineKeyboardButton("📡 Kelola IP", callback_data='manage_ips')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('📊 Panel Kontrol Script:', reply_markup=reply_markup)

def manage_ips(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    ip_list = get_ip_list()
    ip_count = len(ip_list)
    
    keyboard = [
        [InlineKeyboardButton("➕ Tambah IP", callback_data='add_ip')],
        [InlineKeyboardButton("➖ Hapus IP", callback_data='remove_ip')],
        [InlineKeyboardButton("🔄 List IP", callback_data='list_ips')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text=f"📡 Manajemen IP Server\n\nTotal IP terdaftar: {ip_count}",
        reply_markup=reply_markup
    )

def add_ip(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    context.user_data['adding_ip'] = True
    query.edit_message_text(
        "➕ Masukkan IP address yang ingin ditambahkan:\n"
        "Contoh: 192.168.1.100\n\n"
        "Untuk menambahkan multiple IP, pisahkan dengan baris baru."
    )

def remove_ip(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    ip_list = get_ip_list()
    if not ip_list:
        query.edit_message_text("❌ Tidak ada IP yang terdaftar.")
        return
    
    keyboard = []
    for ip in ip_list:
        keyboard.append([InlineKeyboardButton(f"❌ {ip}", callback_data=f'remove_{ip}')])
    
    keyboard.append([InlineKeyboardButton("🗑️ Hapus Semua", callback_data='remove_all')])
    keyboard.append([InlineKeyboardButton("🔙 Kembali", callback_data='manage_ips')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="➖ Pilih IP yang ingin dihapus:",
        reply_markup=reply_markup
    )

def list_ips(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    ip_list = get_ip_list()
    if not ip_list:
        text = "❌ Tidak ada IP yang terdaftar."
    else:
        text = "📡 Daftar IP Server:\n\n" + "\n".join(f"• {ip}" for ip in ip_list)
    
    keyboard = [
        [InlineKeyboardButton("🔙 Kembali", callback_data='manage_ips')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)

def status(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    results = send_mass_request("get-active-file")
    
    status_messages = []
    for result in results:
        if 'error' in result:
            status_messages.append(f"❌ {result['ip']}: {result['error']}")
        else:
            active_file = result['response']
            status_text = "🟢 Berjalan" if "active_file" in active_file else "🔴 Berhenti"
            if "active_file" in active_file:
                status_text += f" ({active_file['active_file']})"
            status_messages.append(f"• {result['ip']}: {status_text}")
    
    keyboard = [
        [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="📊 Status Script:\n" + "\n".join(status_messages) if status_messages else "Tidak ada server yang merespon",
        reply_markup=reply_markup
    )

def start_script(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    ip_list = get_ip_list()
    if not ip_list:
        query.edit_message_text("❌ Tidak ada IP yang terdaftar.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🔄 Script 1 (awal.py)", callback_data='start_1')],
        [InlineKeyboardButton("🔄 Script 2 (gaskeun.py)", callback_data='start_2')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Pilih script yang akan dijalankan:",
        reply_markup=reply_markup
    )

def start_script_option(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    script_id = query.data.split('_')[1]
    results = send_mass_request("start-script", "POST", {"target": script_id})
    
    success_count = sum(1 for r in results if 'response' in r and 'success' in r['response'])
    total = len(results)
    
    query.edit_message_text(f"✅ Script {script_id} berhasil dijalankan di {success_count}/{total} server")

def stop_script(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    results = send_mass_request("stop-script", "POST")
    
    success_count = sum(1 for r in results if 'response' in r and 'success' in r['response'])
    total = len(results)
    
    query.edit_message_text(f"✅ Script berhasil dihentikan di {success_count}/{total} server")

def view_schedule(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    results = send_mass_request("get-jadwal")
    
    schedule_messages = []
    for result in results:
        if 'error' in result:
            schedule_messages.append(f"❌ {result['ip']}: {result['error']}")
        else:
            schedule = result['response']
            if "error" not in schedule:
                schedule_text = (
                    f"• {result['ip']}: Buka {schedule['buka_jam']:02d}:{schedule['buka_menit']:02d} - "
                    f"Tutup {schedule['tutup_jam']:02d}:{schedule['tutup_menit']:02d}"
                )
                schedule_messages.append(schedule_text)
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Jadwal", callback_data='edit_schedule')],
        [InlineKeyboardButton("🔙 Kembali", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        text="⏰ Jadwal Saat Ini:\n" + "\n".join(schedule_messages) if schedule_messages else "Tidak ada jadwal yang ditemukan",
        reply_markup=reply_markup
    )

def edit_schedule(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    context.user_data['editing_schedule'] = True
    query.edit_message_text(
        "✏️ Kirim jadwal baru dalam format:\n"
        "buka_jam buka_menit tutup_jam tutup_menit\n\n"
        "Contoh: 8 0 16 30\n"
        "(Artinya buka jam 08:00 dan tutup jam 16:30)\n\n"
        "Jadwal ini akan diterapkan ke semua server."
    )

def update_link(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    context.user_data['updating_link'] = True
    query.edit_message_text(
        "🔗 Kirim link baru (satu link per baris)\n"
        "Link ini akan diperbarui di semua server."
    )

def handle_message(update: Update, context: CallbackContext):
    if not is_admin(update):
        return
    
    if context.user_data.get('adding_ip'):
        new_ips = [ip.strip() for ip in update.message.text.splitlines() if ip.strip()]
        ip_list = get_ip_list()
        
        added = []
        already_exists = []
        
        for ip in new_ips:
            if ip not in ip_list:
                ip_list.append(ip)
                added.append(ip)
            else:
                already_exists.append(ip)
        
        save_ip_list(ip_list)
        
        message = []
        if added:
            message.append(f"✅ Berhasil menambahkan {len(added)} IP:")
            message.extend(f"• {ip}" for ip in added)
        if already_exists:
            message.append(f"\n⚠️ {len(already_exists)} IP sudah ada:")
            message.extend(f"• {ip}" for ip in already_exists)
        
        update.message.reply_text("\n".join(message))
        context.user_data.pop('adding_ip', None)
        start(update, context)
    
    elif context.user_data.get('editing_schedule'):
        try:
            parts = update.message.text.split()
            if len(parts) != 4:
                raise ValueError("Format tidak valid")
            
            buka_jam = int(parts[0])
            buka_menit = int(parts[1])
            tutup_jam = int(parts[2])
            tutup_menit = int(parts[3])
            
            # Validate time
            if not (0 <= buka_jam < 24 and 0 <= tutup_jam < 24):
                raise ValueError("Jam harus antara 0-23")
            if not (0 <= buka_menit < 60 and 0 <= tutup_menit < 60):
                raise ValueError("Menit harus antara 0-59")
            
            data = {
                "buka_jam": buka_jam,
                "buka_menit": buka_menit,
                "tutup_jam": tutup_jam,
                "tutup_menit": tutup_menit
            }
            
            results = send_mass_request("update-waktu", "POST", data)
            
            success_count = sum(1 for r in results if 'response' in r and 'success' in r['response'])
            total = len(results)
            
            update.message.reply_text(f"✅ Jadwal berhasil diperbarui di {success_count}/{total} server")
            
        except Exception as e:
            update.message.reply_text(f"❌ Format tidak valid: {str(e)}")
        
        context.user_data.pop('editing_schedule', None)
        start(update, context)
    
    elif context.user_data.get('updating_link'):
        results = send_mass_request("update-link", "POST", {"link": update.message.text})
        
        success_count = sum(1 for r in results if 'response' in r and 'success' in r['response'])
        total = len(results)
        
        update.message.reply_text(f"✅ Link berhasil diperbarui di {success_count}/{total} server")
        context.user_data.pop('updating_link', None)
        start(update, context)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    
    if data == 'main_menu':
        start(update, context)
    elif data == 'status':
        status(update, context)
    elif data == 'start_script':
        start_script(update, context)
    elif data.startswith('start_'):
        start_script_option(update, context)
    elif data == 'stop_script':
        stop_script(update, context)
    elif data == 'view_schedule':
        view_schedule(update, context)
    elif data == 'edit_schedule':
        edit_schedule(update, context)
    elif data == 'update_link':
        update_link(update, context)
    elif data == 'manage_ips':
        manage_ips(update, context)
    elif data == 'add_ip':
        add_ip(update, context)
    elif data == 'remove_ip':
        remove_ip(update, context)
    elif data == 'list_ips':
        list_ips(update, context)
    elif data.startswith('remove_'):
        ip_to_remove = data[7:]
        if ip_to_remove == 'all':
            save_ip_list([])
            query.edit_message_text("✅ Semua IP berhasil dihapus")
        else:
            ip_list = get_ip_list()
            if ip_to_remove in ip_list:
                ip_list.remove(ip_to_remove)
                save_ip_list(ip_list)
                query.edit_message_text(f"✅ IP {ip_to_remove} berhasil dihapus")
            else:
                query.edit_message_text(f"❌ IP {ip_to_remove} tidak ditemukan")
        manage_ips(update, context)

def error_handler(update: Update, context: CallbackContext):
    if update and update.message:
        update.message.reply_text(f"⚠️ Terjadi error: {context.error}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    
    # Callback button handlers
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlers
    dp.add_handler(MessageHandler(filters.text & ~filters.command, handle_message))
    
    # Error handler
    dp.add_error_handler(error_handler)
    
    # Start the bot
    updater.start_polling()
    print("Bot sedang berjalan...")
    updater.idle()

if __name__ == '__main__':
    main()
