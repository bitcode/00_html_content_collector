# ./00_html_content_collector/webdriver_manager.py
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from custom_exceptions import NetworkError, ParsingError
from logger import setup_logging, log_error, log_info
from proxy_manager import ProxyManager

# Initialize loggers
loggers = setup_logging(output_dir='logs', doc_name='webdriver_manager', version='v1')

def setup_webdriver():
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        proxy = ProxyManager().get_proxy()
        chrome_options.add_argument(f'--proxy-server={proxy["https"]}')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        log_info(loggers, "WebDriver setup successful")
        return driver
    except Exception as e:
        log_error(loggers, NetworkError(f"Failed to setup WebDriver: {str(e)}"))
        raise

def scroll_page(driver):
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            if last_height > 50000:  # Example: stop after 50000 pixels
                log_info(loggers, "Reached maximum scroll limit")
                break
        log_info(loggers, "Page scrolling completed")
    except Exception as e:
        log_error(loggers, ParsingError(f"Error while scrolling page: {str(e)}"))
        raise

def expand_content(driver):
    expandable_selectors = [
        ".show-more", ".read-more", ".expand", "[id*='expand']", "[class*='expand']",
        "[aria-expanded='false']", ".collapsed", ".toggle", ".accordion-header"
    ]
    load_more_selectors = [
        ".load-more", ".show-more", "#loadMoreButton",
        "[data-action='load-more']", "[aria-label='Load more']"
    ]

    try:
        for selector in load_more_selectors:
            while True:
                try:
                    load_more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    driver.execute_script("arguments[0].click();", load_more_button)
                    time.sleep(2)
                except TimeoutException:
                    break
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
                    time.sleep(1)
                    continue
                except Exception as e:
                    log_error(loggers, ParsingError(f"Error expanding 'Load More' content: {str(e)}"))
                    break

        for selector in expandable_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    if element.is_displayed() and element.is_enabled():
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(1)
                except ElementClickInterceptedException:
                    log_error(loggers, ParsingError(f"Could not click element: {selector}"))
                except Exception as e:
                    log_error(loggers, ParsingError(f"Error expanding content: {str(e)}"))

        log_info(loggers, "Content expansion completed")
    except Exception as e:
        log_error(loggers, ParsingError(f"Error in expand_content: {str(e)}"))
        raise
