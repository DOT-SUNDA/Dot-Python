from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import os
import time
import sys

# Konfigurasi Waktu
SLEEP_SEBELUM_AKSI = 60
SLEEP_SESUDAH_AKSI = 30
SLEEP_JIKA_ERROR = 10
LOG_CLEAR_INTERVAL = 3600  # 1 jam dalam detik

# Variabel global untuk waktu terakhir clear log
last_log_clear_time = datetime.now()

def clear_screen():
    """Membersihkan layar console"""
    os.system('cls' if os.name == 'nt' else 'clear')

def log_sukses(profile_name, current, total):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {profile_name} berhasil proses link {current}/{total}", flush=True)

def log_error(profile_name, link, error):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {profile_name} error pada link {link}: {str(error)}", flush=True)

def log_element_not_found(profile_name, element_name):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {profile_name} elemen '{element_name}' tidak ditemukan, melanjutkan...", flush=True)

def check_and_clear_logs():
    global last_log_clear_time
    now = datetime.now()
    if (now - last_log_clear_time).total_seconds() >= LOG_CLEAR_INTERVAL:
        clear_screen()
        print(f"[{now.strftime('%H:%M:%S')}] Log telah dibersihkan")
        last_log_clear_time = now

def get_options(user_data_dir, profile_dir):
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-features=InfiniteSessionRestore")
    options.add_argument("--window-size=500,500")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    })
    return options

def read_links_from_file(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def process_single_link(driver, link, profile_name):
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 10)
        
        try:
            trust = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust.click()
        except Exception as e:
            log_element_not_found(profile_name, "I trust the owner")
            return False
        
        try:
            open_ws = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
            open_ws.click()
        except Exception as e:
            log_element_not_found(profile_name, "Open Workspace")
            return False
        
        time.sleep(SLEEP_SEBELUM_AKSI)
        
        try:
            driver.find_element(By.TAG_NAME, "body").click()
            actions = ActionChains(driver)
            actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("c").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        except Exception as e:
            log_error(profile_name, link, e)
            return False
        
        time.sleep(SLEEP_SESUDAH_AKSI)
        return True
        
    except Exception as e:
        log_error(profile_name, link, e)
        time.sleep(SLEEP_JIKA_ERROR)
        return False

def worker(profile_name, user_data_dir, profile_dir, window_position, links):
    if not links:
        print(f"{profile_name} tidak memiliki link untuk diproses")
        return

    options = get_options(user_data_dir, profile_dir)
    driver = webdriver.Chrome(options=options)
    
    if window_position:
        driver.set_window_position(*window_position)

    while True:
        total = len(links)
        count = 0

        for index, link in enumerate(links):
            check_and_clear_logs()  # Cek apakah perlu clear log
            success = process_single_link(driver, link, profile_name)
            if success:
                count += 1
                log_sukses(profile_name, count, total)

if __name__ == "__main__":
    user_profiles = [
        {
            "name": "Profile1",
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile1",
            "profile_dir": "Default",
            "window_position": (0, 0)
        },
        {
            "name": "Profile2",
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile2",
            "profile_dir": "Default",
            "window_position": (0, 150)
        },
    ]

    all_links = read_links_from_file("link.txt")
    if not all_links:
        print("link.txt kosong, keluar.")
        exit(1)

    links_for_profiles = [[] for _ in user_profiles]
    for i, link in enumerate(all_links):
        links_for_profiles[i % len(user_profiles)].append(link)

    processes = []
    for i, profile in enumerate(user_profiles):
        p = Process(target=worker, args=(
            profile['name'],
            profile['user_data_dir'],
            profile['profile_dir'],
            profile['window_position'],
            links_for_profiles[i]
        ))
        p.start()
        processes.append(p)
        print(f"Memulai proses untuk {profile['name']} dengan {len(links_for_profiles[i])} link")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nMenghentikan semua proses...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("Semua proses dihentikan.")
