import os
import time
from datetime import datetime
from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# ==========================
# KONFIGURASI TIME SLEEP
# ==========================
SLEEP_SEBELUM_AKSI = 30
SLEEP_SESUDAH_AKSI = 30
SLEEP_JIKA_ERROR = 10

def get_options(user_data_dir, profile_dir, position):
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--window-size=500,500")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return options

def read_links_from_file(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as file:
        links = file.readlines()
    return [link.strip() for link in links if link.strip()]

def process_single_link(driver, link):
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 30)

        try:
            trust_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner of this shared workspace')]")))
            trust_button.click()
        except:
            pass

        try:
            open_workspace_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
            open_workspace_button.click()
        except:
            pass

        time.sleep(SLEEP_SEBELUM_AKSI)

        body = driver.find_element(By.TAG_NAME, "body")
        body.click()

        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("c").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()

        time.sleep(SLEEP_SESUDAH_AKSI)

    except:
        time.sleep(SLEEP_JIKA_ERROR)

def worker(user_data_dir, profile_dir, window_position, links_subset):
    if not links_subset:
        return

    options = get_options(user_data_dir, profile_dir, window_position)
    driver = webdriver.Chrome(options=options)

    index = 0
    while True:
        process_single_link(driver, links_subset[index])
        index = (index + 1) % len(links_subset)

if __name__ == "__main__":
    user_profiles = [
        {
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile1",
            "profile_dir": "Default",
            "window_position": (0, 100)
        },
        {
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile2",
            "profile_dir": "Default",
            "window_position": (0, 300)
        },
    ]

    all_links = read_links_from_file("link.txt")
    if not all_links:
        exit(1)

    links_for_profiles = [[] for _ in user_profiles]
    for i, link in enumerate(all_links):
        links_for_profiles[i % len(user_profiles)].append(link)

    processes = []
    for i, profile in enumerate(user_profiles):
        p = Process(target=worker, args=(
            profile['user_data_dir'],
            profile['profile_dir'],
            profile['window_position'],
            links_for_profiles[i]
        ))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
