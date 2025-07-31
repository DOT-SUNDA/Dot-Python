from multiprocessing import Process, Queue
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import os
import sys
import requests
import random
import logging
from datetime import datetime

# Configuration
CONFIG = {
    'SLEEP_AFTER_ACTION': (1, 3),  # Random range in seconds
    'SLEEP_IF_ERROR': (5, 10),
    'TELEGRAM_DELAY': (10, 30),  # Random delay range in seconds
    'MAX_TELEGRAM_REQUESTS': 5,  # Max requests per minute
    'CHROME_TIMEOUT': 20,
    'MAX_RETRIES': 2,
    'TELEGRAM_TOKEN': '8455364218:AAFoy_mvhZi9HYeTM48hO9aXapE-cYmWuCs',
    'TELEGRAM_CHAT_ID': '6501677690'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('link_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramRateLimiter:
    def __init__(self):
        self.last_request_time = 0
        self.request_count = 0
        self.reset_time = time.time() + 60  # Reset counter every minute
    
    def check_limit(self):
        current_time = time.time()
        if current_time > self.reset_time:
            self.request_count = 0
            self.reset_time = current_time + 60
        
        if self.request_count >= CONFIG['MAX_TELEGRAM_REQUESTS']:
            sleep_time = self.reset_time - current_time
            if sleep_time > 0:
                logger.warning(f"Telegram rate limit reached. Sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
            self.request_count = 0
            self.reset_time = time.time() + 60
        
        # Add random delay
        delay = random.uniform(*CONFIG['TELEGRAM_DELAY'])
        time.sleep(delay)
        self.request_count += 1

telegram_limiter = TelegramRateLimiter()

def silent_excepthook(exctype, value, traceback):
    logger.error(f"Unhandled exception: {exctype.__name__}: {value}", exc_info=traceback)

sys.excepthook = silent_excepthook

def get_options(user_data_dir, profile_dir):
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=500,500")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_settings.popups": 0
    })
    return options

def read_links_from_file(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Error reading links file: {e}")
        return []

def process_single_link(driver, link, retry_count=0):
    try:
        logger.info(f"Processing link: {link}")  # Log the complete link being processed
        driver.get(link)
        wait = WebDriverWait(driver, CONFIG['CHROME_TIMEOUT'])
        
        try:
            trust_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'I trust the owner')]")))
            trust_button.click()
            time.sleep(random.uniform(*CONFIG['SLEEP_AFTER_ACTION']))
            return True
        except TimeoutException:
            logger.debug(f"Timeout waiting for trust button on {link}")
            return False
        except Exception as e:
            logger.warning(f"Error processing {link}: {str(e)}")
            if retry_count < CONFIG['MAX_RETRIES']:
                time.sleep(random.uniform(*CONFIG['SLEEP_IF_ERROR']))
                return process_single_link(driver, link, retry_count + 1)
            return False
            
    except WebDriverException as e:
        logger.error(f"WebDriver error on {link}: {str(e)}")
        time.sleep(random.uniform(*CONFIG['SLEEP_IF_ERROR']))
        if retry_count < CONFIG['MAX_RETRIES']:
            return process_single_link(driver, link, retry_count + 1)
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing {link}: {str(e)}")
        return False

def send_to_telegram(file_path, caption):
    telegram_limiter.check_limit()
    
    url = f'https://api.telegram.org/bot{CONFIG["TELEGRAM_TOKEN"]}/sendDocument'
    
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': CONFIG["TELEGRAM_CHAT_ID"], 'caption': caption}
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
            return True
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")
        return False

def worker(profile_name, user_data_dir, profile_dir, window_position, links, result_queue):
    logger.info(f"Worker {profile_name} started with {len(links)} links")
    success_links = []
    driver = None
    
    try:
        options = get_options(user_data_dir, profile_dir)
        driver = webdriver.Chrome(options=options)
        
        if window_position:
            driver.set_window_position(*window_position)

        for i, link in enumerate(links, 1):                
            logger.info(f"{profile_name} processing link {i}/{len(links)}: {link}")
            if process_single_link(driver, link):
                success_links.append(link)
            else:
                logger.warning(f"Failed to process link: {link}")
                
        result_queue.put((profile_name, success_links))
        
    except Exception as e:
        logger.error(f"Worker {profile_name} crashed: {str(e)}")
        result_queue.put((profile_name, []))
    finally:
        if driver:
            driver.quit()
        logger.info(f"Worker {profile_name} finished")

def distribute_links(links, num_workers):
    """Distribute links evenly with round-robin distribution"""
    distributed = [[] for _ in range(num_workers)]
    for i, link in enumerate(links):
        distributed[i % num_workers].append(link)
    return distributed

if __name__ == "__main__":
    # User profiles configuration
    user_profiles = [
        {
            "name": "Profile1",
            "user_data_dir": r"C:\Users\Administrator\Desktop\Profile1",
            "profile_dir": "Default",
            "window_position": (0, 0)
        },
        # Add more profiles as needed
    ]

    all_links = read_links_from_file("link.txt")
    if not all_links:
        logger.error("No links found in link.txt")
        sys.exit(1)

    # Distribute links across profiles
    links_for_profiles = distribute_links(all_links, len(user_profiles))
    
    # Create a queue for results
    result_queue = Queue()
    
    processes = []
    for i, profile in enumerate(user_profiles):
        p = Process(
            target=worker,
            args=(
                profile['name'],
                profile['user_data_dir'],
                profile['profile_dir'],
                profile['window_position'],
                links_for_profiles[i],
                result_queue
            )
        )
        p.start()
        processes.append(p)
        time.sleep(5)  # Stagger process starts

    # Collect results
    all_success = []
    for _ in range(len(processes)):
        profile_name, success = result_queue.get()
        all_success.extend(success)
        logger.info(f"Received results from {profile_name}: {len(success)} successful links")

    # Wait for all processes to finish
    for p in processes:
        p.join()
        p.close()

    # Save and report results
    if all_success:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        success_filename = f"sukses_{timestamp}.txt"
        
        with open(success_filename, 'w') as f:
            f.write("\n".join(all_success) + "\n")
        
        # Also append to main success file
        with open("sukses.txt", 'a') as f:
            f.write("\n".join(all_success) + "\n")
        
        # Send to Telegram
        if send_to_telegram(
            success_filename,
            f"✅ Total Success: {len(all_success)}/{len(all_links)}\n"
            f"⏱️ Completed at: {timestamp.replace('_', ' ')}"
        ):
            # Delete sukses.txt after successful Telegram send
            try:
                os.remove("sukses.txt")
                logger.info("sukses.txt deleted after successful Telegram send")
            except Exception as e:
                logger.error(f"Error deleting sukses.txt: {e}")
        
        logger.info(f"Process completed. Success rate: {len(all_success)}/{len(all_links)}")
    else:
        logger.warning("No successful links processed")
