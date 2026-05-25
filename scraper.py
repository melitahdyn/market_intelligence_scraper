import time
import re
import random
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
]

PHONE_REGEX = r"(\+62|0)\d[\d\s\-]{7,}"


# ======================================================
# SETUP DRIVER
# ======================================================
def setup_driver():
    options = Options()

    # STREAMLIT CLOUD FIX
    options.binary_location = "/usr/bin/chromium"

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_experimental_option(
        "excludeSwitches", ["enable-automation"]
    )
    options.add_experimental_option(
        "useAutomationExtension", False
    )

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(
        service=service,
        options=options
    )

    driver.set_page_load_timeout(60)

    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    """)

    return driver
# ======================================================
# CLOSE COOKIE
# ======================================================
def close_cookie_popup(driver):
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")

        for btn in buttons:
            txt = btn.text.lower()

            if any(
                x in txt for x in
                ["accept", "setuju", "terima"]
            ):
                btn.click()
                time.sleep(1)
                break
    except:
        pass


# ======================================================
# EXTRACT DETAIL
# ======================================================
def extract_place_detail(driver):

    row = {
        "Nama Perusahaan": "N/A",
        "Alamat": "N/A",
        "Telepon": "N/A",
        "Website": "N/A",
        "Email": "N/A",
        "Linkedin/Instagram": "N/A",
        "Link Maps": driver.current_url
    }

    # ==========================
    # NAMA TEMPAT
    # ==========================
    try:
        h1 = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "h1")
            )
        )

        nama = h1.text.strip()

        if not nama:
            return None

        row["Nama Perusahaan"] = nama

    except:
        return None

    # ==========================
    # WEBSITE
    # ==========================
    try:
        web_btn = driver.find_element(
            By.CSS_SELECTOR,
            'a[data-item-id="authority"]'
        )

        href = web_btn.get_attribute("href")

        if href:
            row["Website"] = href

    except:
        pass

    # ==========================
    # ALAMAT
    # ==========================
    try:
        addr = driver.find_element(
            By.CSS_SELECTOR,
            '[data-item-id="address"]'
        )

        txt = (
            addr.get_attribute("aria-label")
            or addr.text
        )

        txt = re.sub(
            r"^(Alamat|Address)\s*:\s*",
            "",
            txt,
            flags=re.IGNORECASE
        )

        row["Alamat"] = txt.strip()

    except:
        pass

    # ==========================
    # TELEPON
    # ==========================
    try:
        phone = driver.find_element(
            By.CSS_SELECTOR,
            '[data-item-id*="phone"]'
        )

        txt = (
            phone.get_attribute("aria-label")
            or phone.text
        )

        txt = re.sub(
            r"^(Telepon|Phone)\s*:\s*",
            "",
            txt,
            flags=re.IGNORECASE
        )

        row["Telepon"] = txt.strip()

    except:
        pass

    return row


# ======================================================
# SCROLL LIST
# ======================================================
def scroll_results(driver, wait):

    try:
        feed = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    '//div[@role="feed"]'
                )
            )
        )

        last_count = 0

        for _ in range(10):

            driver.execute_script("""
                arguments[0].scrollTop =
                arguments[0].scrollHeight
            """, feed)

            time.sleep(2)

            cards = driver.find_elements(
                By.XPATH,
                '//a[contains(@href,"/maps/place/")]'
            )

            if len(cards) == last_count:
                break

            last_count = len(cards)

        return True

    except:
        return False


# ======================================================
# MAIN SCRAPER
# ======================================================
def scrape_google_maps(
    query,
    max_results=30,
    max_scroll=8
):

    driver = None
    data = []

    try:
        print(f"🔎 Query: {query}")

        driver = setup_driver()
        wait = WebDriverWait(driver, 30)

        encoded_query = urllib.parse.quote(query)

        url = (
            f"https://www.google.com/maps/search/"
            f"{encoded_query}"
        )

        driver.get(url)

        time.sleep(6)
        print("TITLE:", driver.title)
        print("URL:", driver.current_url)
        driver.save_screenshot("/tmp/maps_debug.png")
        print(driver.page_source[:1000])
        
        close_cookie_popup(driver)

        # ==================================
        # Kalau langsung detail page
        # ==================================
        if "/maps/place/" in driver.current_url:

            detail = extract_place_detail(driver)

            if detail:
                data.append(detail)

            return data

        # ==================================
        # WAIT FEED
        # ==================================
        try:
            wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        '//div[@role="feed"]'
                    )
                )
            )
        except:
            print("⚠️ Feed tidak muncul")
            return data

        # ==================================
        # SCROLL
        # ==================================
        scroll_results(driver, wait)

        # ==================================
        # AMBIL LIST ITEM
        # ==================================
        items = driver.find_elements(
            By.XPATH,
            '//a[contains(@href,"/maps/place/")]'
        )

        print(f"📋 Item ditemukan: {len(items)}")

        if not items:
            print("⚠️ Tidak ada item")
            return data

        place_urls = []

        for item in items:
            try:
                href = item.get_attribute("href")

                if (
                    href
                    and "/maps/place/" in href
                    and href not in place_urls
                ):
                    place_urls.append(href)

            except:
                pass

        place_urls = place_urls[:max_results]

        print(
            f"🔗 URL unik: "
            f"{len(place_urls)}"
        )

        # ==================================
        # VISIT DETAIL
        # ==================================
        for i, place_url in enumerate(place_urls):

            try:
                driver.get(place_url)

                time.sleep(2)

                detail = extract_place_detail(driver)

                if detail:
                    data.append(detail)

                    print(
                        f"✅ [{i+1}] "
                        f"{detail['Nama Perusahaan']}"
                    )

            except Exception as e:
                print(f"⚠️ Error detail: {e}")

        return data

    except Exception as e:
        print(f"❌ Error scraping: {e}")
        return data

    finally:
        if driver:
            driver.quit()
