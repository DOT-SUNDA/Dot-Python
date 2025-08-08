from multiprocessing import Process, Barrier
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

SLEEP_SEBELUM_AKSI = 30
SLEEP_SESUDAH_AKSI = 30
SLEEP_JIKA_ERROR = 10

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
        
        driver.find_element(By.TAG_NAME, "body").click()
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("c").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        
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

    if window_position:
        driver.set_window_position(*window_position)

    total = len(links)
    index = 0
    count = 0

    while True:
        success = process_single_link(driver, links[index])
        if success:
            count += 1

        try:
            barrier.wait()
        except:
            break

        index = (index + 1) % total

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
            "window_position": (0, 0)
        },
    ]

    all_links = read_links_from_file("link.txt")
    if not all_links:
        exit(1)

    links_for_profiles = [[] for _ in user_profiles]
    for i, link in enumerate(all_links):
        links_for_profiles[i % len(user_profiles)].append(link)

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
        for p in processes:
            p.terminate()
