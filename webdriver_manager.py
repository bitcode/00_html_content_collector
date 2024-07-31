import ProxyManager
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import logging
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def setup_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no GUI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    proxy = ProxyManager().get_proxy()
    chrome_options.add_argument(f'--proxy-server={proxy["https"]}')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scroll_page(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(2)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

        # Optional: implement a maximum scroll limit
        if last_height > 50000:  # Example: stop after 50000 pixels
            logging.info("Reached maximum scroll limit")
            break

def expand_content(driver):
    # List of common class names or IDs for expandable content
    expandable_selectors = [
        ".show-more", ".read-more", ".expand", "[id*='expand']", "[class*='expand']",
        "[aria-expanded='false']", ".collapsed", ".toggle", ".accordion-header"
    ]

    load_more_selectors = [
        ".load-more", ".show-more", "#loadMoreButton",
        "[data-action='load-more']", "[aria-label='Load more']"
    ]

    for selector in load_more_selectors:
        while True:
            try:
                load_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(2)  # Wait for content to load
            except TimeoutException:
                # No more "Load More" buttons found
                break
            except ElementClickInterceptedException:
                # Button might be obscured, try to scroll to it
                driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
                time.sleep(1)
                continue
            except Exception as e:
                logging.error(f"Error expanding 'Load More' content: {str(e)}")
                break

    for selector in expandable_selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            try:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(1)  # Wait for content to expand
            except ElementClickInterceptedException:
                logging.warning(f"Could not click element: {selector}")
            except Exception as e:
                logging.error(f"Error expanding content: {str(e)}")
