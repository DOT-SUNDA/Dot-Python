import json
import subprocess
import time
import os
import psutil
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify

# File konfigurasi
TARGET_FILES = {
    "1": "awal.py",
    "2": "gaskeun.py"
}
ACTIVE_FILE = "active_file.json"
PID_FILE = "file_pid.txt"
WAKTU_FILE = "waktu.json"
LINK_FILE = "link.txt"

app = Flask(__name__)

# ========== ENDPOINT API ==========

@app.route("/start-script", methods=["POST"])
def start_script():
    try:
        data = request.get_json()
        target_id = str(data.get("target", "1"))
        if target_id not in TARGET_FILES:
            return jsonify({"error": "Target tidak valid"}), 400

        if os.path.exists(PID_FILE):
            return jsonify({"message": "Script sudah berjalan"}), 200

        target_file = TARGET_FILES[target_id]
        start_target_file(target_file)
        save_active_file(target_file)

        return jsonify({"success": True, "message": f"Script {target_file} dijalankan"}), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menjalankan script: {e}"}), 500

@app.route("/stop-script", methods=["POST"])
def stop_script():
    try:
        kill_target_file()
        kill_browser_only()
        return jsonify({"success": True, "message": "Script & browser dihentikan"}), 200
    except:
        return jsonify({"error": "Gagal menghentikan script"}), 500
        
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

        links = [line.strip() for line in data["link"].splitlines() if line.strip()]

        with open(LINK_FILE, "w") as f:
            for link in links:
                f.write(link + "\n")

        return jsonify({
            "success": True,
            "message": f"{len(links)} link disimpan"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Gagal menyimpan link: {str(e)}"}), 500


# ========== FUNGSI UTAMA ==========

def save_active_file(file_name):
    with open(ACTIVE_FILE, "w") as f:
        json.dump({"file": file_name}, f)

def get_active_file():
    if os.path.exists(ACTIVE_FILE):
        try:
            with open(ACTIVE_FILE, "r") as f:
                return json.load(f).get("file")
        except:
            pass
    return None

def start_target_file(file_name):
    if os.path.exists(PID_FILE):
        return
    process = subprocess.Popen(["python", file_name])
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
        if os.path.exists(ACTIVE_FILE):
            os.remove(ACTIVE_FILE)

# ========== Jadwal ==========

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
            active_file = get_active_file()
            if active_file:
                start_target_file(active_file)
            last_buka = True
            last_tutup = False

        if is_time_match(now, tutup_jam, tutup_menit) and not last_tutup:
            kill_target_file()
            kill_browser_only()
            last_tutup = True
            last_buka = False

        time.sleep(30)

def is_time_match(now, hour, minute):
    return now.hour == hour and now.minute == minute

def read_schedule():
    try:
        with open(WAKTU_FILE, "r") as file:
            return json.load(file)
    except:
        return {"buka_jam": 1, "buka_menit": 0, "tutup_jam": 2, "tutup_menit": 0}

def kill_browser_only():
    try:
        subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

@app.errorhandler(404)
@app.errorhandler(405)
def no_output(_):
    return "", 204

# ========== JALANKAN ==========
if __name__ == "__main__":
    Thread(target=scheduler_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
