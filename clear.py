import time
from multiprocessing import Process
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def get_options(user_data_dir, profile_dir):
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--window-size=800,600")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return options

def clear_browser(user_data_dir, profile_dir):
    options = get_options(user_data_dir, profile_dir)
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("chrome://settings/clearBrowserData")
        time.sleep(3)

        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.TAB * 11 + Keys.ENTER)

        print(f"[{profile_dir}] Tombol 'Hapus data' berhasil ditekan.")
        time.sleep(5)
    except Exception as e:
        print(f"[{profile_dir}] Gagal menghapus data: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    profiles = [
        {
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile1",
            "profile_dir": "Default"
        },
        {
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile2",
            "profile_dir": "Default"
        }
    ]

    processes = []
    for profile in profiles:
        p = Process(target=clear_browser, args=(
            profile['user_data_dir'],
            profile['profile_dir']
        ))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    print("Pembersihan selesai untuk semua profil.")
