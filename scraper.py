import time
import re
import urllib.parse
import base64

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=id-ID")  # ← paksa bahasa Indonesia
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    # ← Kurangi dari 60 ke 20 agar tidak hang terlalu lama
    driver.set_page_load_timeout(20)

    driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined })
    """)
    return driver


# ======================================================
# DETEKSI CONSENT / CAPTCHA PAGE  ← BARU
# ======================================================
def is_blocked(driver):
    """Cek apakah Google redirect ke halaman consent/CAPTCHA."""
    url = driver.current_url
    title = driver.title.lower()
    blocked_signals = [
        "consent.google",
        "accounts.google",
        "sorry/index",
    ]
    if any(s in url for s in blocked_signals):
        return True
    if "sebelum melanjutkan" in title or "before you continue" in title:
        return True
    return False


# ======================================================
# SCREENSHOT DEBUG  ← BARU
# Simpan screenshot jika ada masalah, untuk debug
# ======================================================
def save_debug_screenshot(driver, name="debug"):
    try:
        screenshot = driver.get_screenshot_as_base64()
        with open(f"/tmp/{name}.png", "wb") as f:
            f.write(base64.b64decode(screenshot))
        print(f"📸 Screenshot disimpan: /tmp/{name}.png")
    except Exception as e:
        print(f"⚠️ Gagal screenshot: {e}")


# ======================================================
# CLOSE COOKIE
# ======================================================
def close_cookie_popup(driver):
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            txt = btn.text.lower()
            if any(x in txt for x in ["accept", "setuju", "terima", "agree"]):
                btn.click()
                time.sleep(1)
                break
    except:
        pass


# ======================================================
# EXTRACT DETAIL  ← DIPERKUAT DENGAN FALLBACK SELECTOR
# ======================================================
def extract_place_detail(driver):
    row = {
        "Nama Perusahaan": "N/A",
        "Alamat": "N/A",
        "Telepon": "N/A",
        "Website": "N/A",
        "Email": "N/A",
        "Linkedin/Instagram": "N/A",
        "Link Maps": driver.current_url,
    }

    # ==========================
    # NAMA TEMPAT — multi-selector fallback
    # ==========================
    nama = None
    nama_selectors = [
        (By.TAG_NAME, "h1"),
        (By.CSS_SELECTOR, '[data-attrid="title"]'),
        (By.CSS_SELECTOR, ".fontHeadlineLarge"),
        (By.CSS_SELECTOR, ".DUwDvf"),          # selector lama
        (By.CSS_SELECTOR, ".qBF1Pd"),          # selector alternatif
    ]
    for by, sel in nama_selectors:
        try:
            el = WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((by, sel))
            )
            nama = el.text.strip()
            if nama:
                break
        except:
            continue

    if not nama:
        print("⚠️ Nama tidak ditemukan, skip halaman ini")
        save_debug_screenshot(driver, "no_name_found")
        return None

    row["Nama Perusahaan"] = nama

    # ==========================
    # WEBSITE
    # ==========================
    website_selectors = [
        'a[data-item-id="authority"]',
        'a[href*="http"][data-tooltip="Buka website"]',
        'a[aria-label*="website"]',
        'a[aria-label*="Website"]',
    ]
    for sel in website_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            href = el.get_attribute("href")
            if href and not "google.com" in href:
                row["Website"] = href
                break
        except:
            continue

    # ==========================
    # ALAMAT
    # ==========================
    alamat_selectors = [
        '[data-item-id="address"]',
        'button[data-item-id="address"]',
        '[aria-label*="Alamat"]',
        '[aria-label*="Address"]',
    ]
    for sel in alamat_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            txt = el.get_attribute("aria-label") or el.text
            txt = re.sub(r"^(Alamat|Address)\s*:\s*", "", txt, flags=re.IGNORECASE)
            row["Alamat"] = txt.strip()
            break
        except:
            continue

    # ==========================
    # TELEPON
    # ==========================
    phone_selectors = [
        '[data-item-id*="phone"]',
        'button[data-tooltip*="Salin nomor"]',
        '[aria-label*="Telepon"]',
        '[aria-label*="Phone"]',
    ]
    for sel in phone_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            txt = el.get_attribute("aria-label") or el.text
            txt = re.sub(r"^(Telepon|Phone)\s*:\s*", "", txt, flags=re.IGNORECASE)
            row["Telepon"] = txt.strip()
            break
        except:
            continue

    return row


# ======================================================
# SCROLL LIST
# ======================================================
def scroll_results(driver, wait, max_scroll=10):
    try:
        feed = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )
        last_count = 0
        for _ in range(max_scroll):
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", feed
            )
            time.sleep(2)
            cards = driver.find_elements(
                By.XPATH, '//a[contains(@href,"/maps/place/")]'
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
def scrape_google_maps(query, max_results=30):
    driver = None
    data = []

    try:
        print(f"🔎 Query: {query}")
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)  # ← Turun dari 30 ke 20

        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/maps/search/{encoded_query}"

        try:
            driver.get(url)
        except Exception as e:
            # page_load_timeout kadang raise tapi halaman sudah cukup termuat
            print(f"⚠️ Load timeout (lanjut): {e}")

        time.sleep(4)  # ← Turun dari 6 ke 4

        print(f"TITLE: {driver.title}")
        print(f"URL: {driver.current_url}")

        # ← CEK BLOKIR DULUAN
        if is_blocked(driver):
            print("❌ Google memblokir / redirect consent. IP Cloud terdeteksi sebagai bot.")
            save_debug_screenshot(driver, "blocked")
            return data

        close_cookie_popup(driver)

        # Langsung ke detail page
        if "/maps/place/" in driver.current_url:
            detail = extract_place_detail(driver)
            if detail:
                data.append(detail)
            return data

        # Tunggu feed
        try:
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
            )
        except:
            print("⚠️ Feed tidak muncul")
            save_debug_screenshot(driver, "no_feed")
            # Coba cek apakah langsung single result
            if "/maps/place/" in driver.current_url:
                detail = extract_place_detail(driver)
                if detail:
                    data.append(detail)
            return data

        scroll_results(driver, wait)

        items = driver.find_elements(
            By.XPATH, '//a[contains(@href,"/maps/place/")]'
        )
        print(f"📋 Item ditemukan: {len(items)}")

        place_urls = []
        for item in items:
            try:
                href = item.get_attribute("href")
                if href and "/maps/place/" in href and href not in place_urls:
                    place_urls.append(href)
            except:
                pass

        place_urls = place_urls[:max_results]
        print(f"🔗 URL unik: {len(place_urls)}")

        for i, place_url in enumerate(place_urls):
            try:
                try:
                    driver.get(place_url)
                except:
                    pass  # Timeout tapi lanjut

                time.sleep(2)

                detail = extract_place_detail(driver)
                if detail:
                    data.append(detail)
                    print(f"✅ [{i+1}] {detail['Nama Perusahaan']}")
                else:
                    print(f"⚠️ [{i+1}] Detail kosong untuk: {place_url}")

            except Exception as e:
                print(f"⚠️ Error detail [{i+1}]: {e}")

        return data

    except Exception as e:
        print(f"❌ Error scraping: {e}")
        if driver:
            save_debug_screenshot(driver, "fatal_error")
        return data

    finally:
        if driver:
            driver.quit()
