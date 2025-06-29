import json
import subprocess
import time
import os
import psutil
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify

# File konfigurasi
TARGET_FILE = "gaskeun.py"
PID_FILE = "file_pid.txt"
WAKTU_FILE = "waktu.json"
LINK_FILE = "link.txt"

app = Flask(__name__)

# ========== ENDPOINT API ==========

@app.route("/get-jadwal", methods=["GET"])
def get_jadwal():
    if not os.path.exists(WAKTU_FILE):
        return jsonify({"error": "waktu.json tidak ditemukan"}), 404
    with open(WAKTU_FILE, "r") as f:
        return jsonify(json.load(f))

@app.route("/update-waktu", methods=["POST"])
def update_jadwal():
    try:
        data = request.get_json()
        for key in ["buka_jam", "buka_menit", "tutup_jam", "tutup_menit"]:
            if key not in data:
                return jsonify({"error": f"Parameter '{key}' hilang"}), 400

        if not (0 <= data["buka_jam"] < 24 and 0 <= data["tutup_jam"] < 24):
            return jsonify({"error": "Jam harus 0–23"}), 400
        if not (0 <= data["buka_menit"] < 60 and 0 <= data["tutup_menit"] < 60):
            return jsonify({"error": "Menit harus 0–59"}), 400

        with open(WAKTU_FILE, "w") as f:
            json.dump(data, f, indent=4)

        return jsonify({"success": True, "message": "Jadwal diperbarui"}), 200
    except:
        return jsonify({"error": "Gagal memperbarui jadwal"}), 500

@app.route("/update-link", methods=["POST"])
def update_link():
    try:
        data = request.get_json()
        if not data or "link" not in data or not isinstance(data["link"], str):
            return jsonify({"error": "Data 'link' harus berupa string"}), 400

        # Ambil data link, pecah per baris
        links = [line.strip() for line in data["link"].splitlines() if line.strip()]

        with open("link.txt", "w") as f:
            for link in links:
                f.write(link + "\n")

        return jsonify({
            "success": True,
            "message": f"{len(links)} link disimpan"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menyimpan link: {str(e)}"}), 500

@app.route("/start-script", methods=["POST"])
def start_script():
    try:
        if os.path.exists(PID_FILE):
            return jsonify({"message": "Script sudah berjalan"}), 200
        start_target_file()
        return jsonify({"success": True, "message": "Script dijalankan"}), 200
    except:
        return jsonify({"error": "Gagal menjalankan script"}), 500

@app.route("/stop-script", methods=["POST"])
def stop_script():
    try:
        kill_target_file()
        kill_browser_only()
        return jsonify({"success": True, "message": "Script & browser dihentikan"}), 200
    except:
        return jsonify({"error": "Gagal menghentikan script"}), 500

# ========== FUNGSI UTAMA ==========

def read_schedule():
    try:
        with open(WAKTU_FILE, "r") as file:
            return json.load(file)
    except:
        return {"buka_jam": 1, "buka_menit": 0, "tutup_jam": 2, "tutup_menit": 0}

def is_time_match(now, hour, minute):
    return now.hour == hour and now.minute == minute

def start_target_file():
    if os.path.exists(PID_FILE):
        return
    process = subprocess.Popen(["python", TARGET_FILE])
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

def kill_target_file():
    if not os.path.exists(PID_FILE):
        return
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

def kill_browser_only():
    try:
        subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

# ========== JADWAL OTOMATIS ==========

def scheduler_loop():
    last_buka = False
    last_tutup = False

    while True:
        now = datetime.now()
        jadwal = read_schedule()

        buka_jam = jadwal.get("buka_jam", 1)
        buka_menit = jadwal.get("buka_menit", 0)
        tutup_jam = jadwal.get("tutup_jam", 2)
        tutup_menit = jadwal.get("tutup_menit", 0)

        if is_time_match(now, buka_jam, buka_menit) and not last_buka:
            start_target_file()
            last_buka = True
            last_tutup = False

        if is_time_match(now, tutup_jam, tutup_menit) and not last_tutup:
            kill_target_file()
            kill_browser_only()
            last_tutup = True
            last_buka = False

        time.sleep(30)

# ========== HANDLE ENDPOINT SALAH TANPA OUTPUT ==========

@app.errorhandler(404)
@app.errorhandler(405)
def no_output(_):
    return "", 204  # Tidak kirim pesan, aman untuk public use

# ========== JALANKAN ==========

if __name__ == "__main__":
    Thread(target=scheduler_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
