import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time

options = webdriver.ChromeOptions()
options.add_argument("user-data-dir=C:/Users/Administrator/AppData/Local/Google/Chrome/User Data")
options.add_argument("--profile-directory=Default")
options.add_argument("--window-position=0,200")
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

def process_links(driver):
    links = read_links_from_file('link.txt')
    for index, link in enumerate(links):
        if index == 0:
            driver.get(link)
        else:
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(link)

        wait = WebDriverWait(driver, 60)
        try:
            trust_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner of this shared workspace')]")))
            trust_button.click()

            open_workspace_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Open Workspace')]")))
            open_workspace_button.click()
            print(f"Berhasil memproses link: {link}")
        except Exception as e:
            print(f"Gagal memproses link: {link}. Error: {str(e)}")

        time.sleep(30)
        body = driver.find_element("tag name", "body")
        body.click()
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("c").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        time.sleep(30)

# === Jalankan hanya sekali, browser tetap terbuka ===
try:
    print("Menjalankan proses...")
    driver = webdriver.Chrome(options=options)
    process_links(driver)
    print("Selesai memproses semua link. Browser tetap terbuka.")
    
    # Tambahan agar Python tidak keluar (Chrome tidak tertutup)
    input("Tekan ENTER jika ingin menutup browser secara manual...")
except Exception as e:
    print(f"Terjadi error: {e}")
