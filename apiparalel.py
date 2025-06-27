import json
import subprocess
import time
import os
import psutil
from datetime import datetime
from threading import Thread
from flask import Flask, request, jsonify

# Konfigurasi file
TARGET_FILE = "gaskeun.py"
PID_FILE = "file_pid.txt"
WAKTU_FILE = "waktu.json"

# Flask app
app = Flask(__name__)

# =======================
# BAGIAN: API
# =======================

@app.route("/get-jadwal", methods=["GET"])
def get_jadwal():
    if not os.path.exists(WAKTU_FILE):
        return jsonify({"error": "waktu.json tidak ditemukan"}), 404
    with open(WAKTU_FILE, "r") as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/update-waktu", methods=["POST"])
def update_jadwal():
    try:
        data = request.get_json()
        required_fields = ["buka_jam", "buka_menit", "tutup_jam", "tutup_menit"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Parameter tidak lengkap"}), 400

        if not (0 <= data["buka_jam"] < 24 and 0 <= data["tutup_jam"] < 24):
            return jsonify({"error": "Jam harus antara 0-23"}), 400
        if not (0 <= data["buka_menit"] < 60 and 0 <= data["tutup_menit"] < 60):
            return jsonify({"error": "Menit harus antara 0-59"}), 400

        try:
            with open(WAKTU_FILE, "r") as f:
                current_data = json.load(f)
            data["nonstop"] = current_data.get("nonstop", False)
        except:
            data["nonstop"] = False

        with open(WAKTU_FILE, "w") as f:
            json.dump(data, f, indent=4)

        return jsonify({"success": True, "message": "Jadwal berhasil diperbarui"}), 200

    except Exception as e:
        return jsonify({"error": f"Gagal memperbarui jadwal: {str(e)}"}), 500

@app.route("/set-nonstop", methods=["POST"])
def set_nonstop():
    try:
        data = request.get_json()
        if "nonstop" not in data or not isinstance(data["nonstop"], bool):
            return jsonify({"error": "Parameter 'nonstop' harus True atau False"}), 400

        config = read_schedule()
        config["nonstop"] = data["nonstop"]
        with open(WAKTU_FILE, "w") as f:
            json.dump(config, f, indent=4)

        return jsonify({"success": True, "message": f"Mode nonstop di-set ke {data['nonstop']}"}), 200

    except Exception as e:
        return jsonify({"error": f"Gagal mengatur mode nonstop: {str(e)}"}), 500

# =======================
# BAGIAN: SCHEDULER
# =======================

def read_schedule():
    try:
        with open(WAKTU_FILE, "r") as file:
            return json.load(file)
    except:
        return {
            "buka_jam": 1,
            "buka_menit": 0,
            "tutup_jam": 2,
            "tutup_menit": 0,
            "nonstop": False
        }

def is_time_match(now, hour, minute):
    return now.hour == hour and now.minute == minute

def start_target_file():
    if os.path.exists(PID_FILE):
        return  # Sudah jalan
    try:
        process = subprocess.Popen(["python", TARGET_FILE])
        with open(PID_FILE, "w") as f:
            f.write(str(process.pid))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {TARGET_FILE} dijalankan")
    except:
        print(f"[!] Gagal menjalankan {TARGET_FILE}")

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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {TARGET_FILE} dihentikan")
    except:
        print(f"[!] Gagal menghentikan {TARGET_FILE}")
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

def kill_browser_only():
    try:
        subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chrome dihentikan")
    except:
        pass

def scheduler_loop():
    last_buka_flag = False
    last_tutup_flag = False

    while True:
        now = datetime.now()
        jadwal = read_schedule()
        nonstop = jadwal.get("nonstop", False)

        if nonstop:
            if not last_buka_flag:
                start_target_file()
                last_buka_flag = True
                print(f"[{now.strftime('%H:%M:%S')}] Mode nonstop aktif, file dijalankan.")
        else:
            buka_jam = jadwal.get("buka_jam", 1)
            buka_menit = jadwal.get("buka_menit", 0)
            tutup_jam = jadwal.get("tutup_jam", 2)
            tutup_menit = jadwal.get("tutup_menit", 0)

            if is_time_match(now, buka_jam, buka_menit) and not last_buka_flag:
                start_target_file()
                last_buka_flag = True
                last_tutup_flag = False  # Reset flag tutup
                print(f"[{now.strftime('%H:%M:%S')}] Jadwal buka, file dijalankan.")

            if is_time_match(now, tutup_jam, tutup_menit) and not last_tutup_flag:
                kill_target_file()
                kill_browser_only()
                last_tutup_flag = True
                last_buka_flag = False  # Reset flag buka
                print(f"[{now.strftime('%H:%M:%S')}] Jadwal tutup, file dihentikan.")

        time.sleep(30)

# =======================
# JALANKAN
# =======================

if __name__ == "__main__":
    Thread(target=scheduler_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
