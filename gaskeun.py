from multiprocessing import Process, Barrier
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import os
import time

# Konfigurasi
SLEEP_SEBELUM_AKSI = 30
SLEEP_SESUDAH_AKSI = 30
SLEEP_JIKA_ERROR = 10

def log_sukses(profile_name, current, total):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {profile_name} berhasil proses link {current}/{total}", flush=True)

def log_error(profile_name, link, error):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {profile_name} error pada link {link}: {str(error)}", flush=True)

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

def split_links_equally(links, num_profiles):
    """Membagi link secara merata dengan menjaga urutan"""
    chunk_size = len(links) // num_profiles
    remainder = len(links) % num_profiles
    result = []
    index = 0
    for i in range(num_profiles):
        end = index + chunk_size + (1 if i < remainder else 0)
        result.append(links[index:end])
        index = end
    return result

def process_single_link(driver, link, profile_name):
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 10)
        
        try:
            trust = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust.click()
            time.sleep(2)
        except Exception as e:
            pass
        
        try:
            open_ws = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
            open_ws.click()
            time.sleep(2)
        except Exception as e:
            pass
        
        time.sleep(SLEEP_SEBELUM_AKSI)
        
        driver.find_element(By.TAG_NAME, "body").click()
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("c").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        
        time.sleep(SLEEP_SESUDAH_AKSI)
        return True
    except Exception as e:
        log_error(profile_name, link, e)
        time.sleep(SLEEP_JIKA_ERROR)
        return False

def worker(profile_name, user_data_dir, profile_dir, window_position, links, barrier: Barrier):
    if not links:
        print(f"{profile_name} tidak mendapatkan link untuk diproses")
        return

    try:
        options = get_options(user_data_dir, profile_dir)
        driver = webdriver.Chrome(options=options)
        
        if window_position:
            driver.set_window_position(*window_position)
            driver.set_window_size(500, 500)

        total = len(links)
        count = 0

        while True:
            for i, link in enumerate(links):
                success = process_single_link(driver, link, profile_name)
                if success:
                    count += 1
                    log_sukses(profile_name, count, total)

                try:
                    barrier.wait()  # Tunggu semua proses sebelum lanjut
                except:
                    break

    except Exception as e:
        print(f"Error pada worker {profile_name}: {str(e)}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    # Konfigurasi profil
    user_profiles = [
        {
            "name": "Profile1",
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile1",
            "profile_dir": "Default",
            "window_position": (0, 0)  # Posisi jendela pertama
        },
        {
            "name": "Profile2",
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile2",
            "profile_dir": "Default",
            "window_position": (500, 0)  # Posisi jendela kedua
        },
    ]

    # Baca link dari file
    all_links = read_links_from_file("link.txt")
    if not all_links:
        print("link.txt kosong, keluar.")
        exit(1)

    # Bagi link secara merata
    links_for_profiles = split_links_equally(all_links, len(user_profiles))

    # Tampilkan pembagian link
    for i, profile in enumerate(user_profiles):
        print(f"{profile['name']} mendapatkan {len(links_for_profiles[i])} link")

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
        print("\nMenghentikan semua proses...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("Semua proses dihentikan")
