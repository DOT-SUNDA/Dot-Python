import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# Setup Chrome driver options
options = webdriver.ChromeOptions()
options.add_argument("user-data-dir=C:/Users/Administrator/AppData/Local/Google/Chrome/User Data")
options.add_argument("--profile-directory=kontol2")
options.add_argument("--window-position=0,300")
options.add_argument("--window-size=500,500")
options.add_argument("--disable-extensions")
options.add_argument("--disable-gpu")
options.add_argument("--force-dark-mode")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_experimental_option('excludeSwitches', ['enable-logging'])

def read_links_from_file(file_path):
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
            pass  # Tombol ini tidak selalu ada

        open_workspace_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
        open_workspace_button.click()

        time.sleep(30)

        body = driver.find_element("tag name", "body")
        body.click()
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("c").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()

        time.sleep(30)
    except:
        time.sleep(10)

def main_loop():
    driver = webdriver.Chrome(options=options)
    links = read_links_from_file("link2.txt")
    
    if not links:
        return

    index = 0
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear terminal
        print(f"Memproses link {index + 1} dari {len(links)}...")
        process_single_link(driver, links[index])

        index += 1
        if index >= len(links):
            index = 0  # Ulang dari awal

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        pass
