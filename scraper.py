import time
import re
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

PHONE_REGEX = r"(\+62|0)\s?\d[\d\s\-]{7,}"


def setup_driver():
    options = Options()

    DEBUG = False
    if not DEBUG:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-geolocation")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def close_cookie_popup(driver):
    try:
        buttons = driver.find_elements(By.XPATH, "//button")
        for btn in buttons:
            txt = btn.text.lower()
            if "accept" in txt or "setuju" in txt or "terima" in txt:
                btn.click()
                time.sleep(1)
                break
    except:
        pass


# =====================================================
# SELECTOR HELPERS — STABLE & FALLBACK-AWARE
# =====================================================

def find_element_safe(driver, selectors):
    """
    Coba beberapa selector secara berurutan, return element pertama yang ditemukan.
    selectors = list of (By, value) tuple
    """
    for by, val in selectors:
        try:
            el = driver.find_element(by, val)
            if el and el.text.strip():
                return el
        except:
            continue
    return None


def find_elements_safe(driver, selectors):
    """
    Coba beberapa selector, return list pertama yang tidak kosong.
    """
    for by, val in selectors:
        try:
            els = driver.find_elements(by, val)
            if els:
                return els
        except:
            continue
    return []


# =====================================================
# EXTRACT PLACE DETAIL
# =====================================================

def extract_place_detail(driver):
    """
    Ambil detail dari panel kanan Google Maps.
    Menggunakan selector stabil berbasis href, aria, dan XPath semantik.
    """
    row = {
        "Nama Perusahaan": "N/A",
        "Alamat": "N/A",
        "Telepon": "N/A",
        "Website": "N/A",
        "Email": "N/A",
        "Linkedin/Instagram": "N/A",
        "Link Maps": driver.current_url
    }

    # ── NAMA TEMPAT ──────────────────────────────────────
    # Google Maps selalu render nama di <h1>, apapun class-nya
    name_el = find_element_safe(driver, [
        (By.CSS_SELECTOR, "h1"),
        (By.XPATH, "//h1"),
        # Fallback: aria-label pada panel detail
        (By.XPATH, '//div[@role="main"]//h1'),
    ])

    if not name_el:
        # Kalau h1 tidak ada sama sekali, page belum load atau bukan detail page
        print("  ⚠️  h1 tidak ditemukan, skip entry ini")
        return None

    nama = name_el.text.strip()
    if not nama:
        return None

    row["Nama Perusahaan"] = nama

    # ── WEBSITE ──────────────────────────────────────────
    # Google Maps render link website dengan data-item-id="authority"
    # Selector ini jauh lebih stabil dari class name
    website_els = find_elements_safe(driver, [
        (By.CSS_SELECTOR, 'a[data-item-id="authority"]'),
        (By.XPATH, '//a[@data-item-id="authority"]'),
        # Fallback: cari link yang mengandung teks "website" atau href non-maps
        (By.XPATH, '//a[contains(@aria-label,"website") or contains(@aria-label,"Website") or contains(@aria-label,"situs")]'),
    ])

    if website_els:
        href = website_els[0].get_attribute("href")
        if href and "google.com/maps" not in href:
            row["Website"] = href

    # ── ALAMAT & TELEPON ─────────────────────────────────
    # Google Maps menyimpan alamat LENGKAP (termasuk Kota/Kab) di aria-label,
    # bukan di teks visible yang sering terpotong.

    # Cara 1: data-item-id="address" → baca aria-label untuk alamat lengkap
    try:
        addr_el = driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"]')
        # aria-label berisi: "Alamat: Jl. xxx, Kec. yyy, Kota Surabaya, Jawa Timur 60261"
        aria = addr_el.get_attribute("aria-label") or ""
        # Buang prefix "Alamat:" / "Address:"
        full_addr = re.sub(r"^(Alamat|Address)\s*:\s*", "", aria, flags=re.IGNORECASE).strip()
        # Kalau aria-label kosong, fallback ke teks visible
        row["Alamat"] = full_addr or addr_el.text.strip() or "N/A"
    except:
        pass

    # Cara 1b: telepon via data-item-id
    try:
        phone_el = driver.find_element(By.CSS_SELECTOR, '[data-item-id^="phone:tel"]')
        aria_phone = phone_el.get_attribute("aria-label") or ""
        full_phone = re.sub(r"^(Telepon|Phone|Tel)\s*:\s*", "", aria_phone, flags=re.IGNORECASE).strip()
        row["Telepon"] = full_phone or phone_el.text.strip() or "N/A"
    except:
        pass

    # Cara 2: XPath aria-label fallback
    if row["Alamat"] == "N/A":
        try:
            addr_el = driver.find_element(By.XPATH,
                '//button[@data-item-id="address"] | '
                '//button[contains(@aria-label,"Alamat")] | '
                '//button[contains(@aria-label,"Address")]'
            )
            aria = addr_el.get_attribute("aria-label") or ""
            full_addr = re.sub(r"^(Alamat|Address)\s*:\s*", "", aria, flags=re.IGNORECASE).strip()
            row["Alamat"] = full_addr or addr_el.text.strip() or "N/A"
        except:
            pass

    if row["Telepon"] == "N/A":
        try:
            phone_el = driver.find_element(By.XPATH,
                '//button[contains(@data-item-id,"phone")] | '
                '//button[contains(@aria-label,"Telepon")] | '
                '//button[contains(@aria-label,"Phone")]'
            )
            aria_phone = phone_el.get_attribute("aria-label") or ""
            full_phone = re.sub(r"^(Telepon|Phone|Tel)\s*:\s*", "", aria_phone, flags=re.IGNORECASE).strip()
            row["Telepon"] = full_phone or phone_el.text.strip() or "N/A"
        except:
            pass

    # Cara 3: Text scan — backup terakhir
    # Perluas keyword agar tangkap alamat tanpa prefix "Jl."
    ADDR_KEYWORDS = [
        "Jl.", "Jalan", "Jl ", "Gang", "Gg.", "RT", "RW", "No.",
        "Kec.", "Kecamatan", "Kel.", "Kelurahan",
        "Kab.", "Kabupaten", "Kota ",
        "Blok", "Komplek", "Komp.", "Perumahan", "Ruko",
        "Surabaya", "Jakarta", "Bandung", "Medan", "Semarang",
        "Makassar", "Palembang", "Depok", "Tangerang", "Bekasi",
    ]

    if row["Alamat"] == "N/A" or row["Telepon"] == "N/A":
        try:
            panel = driver.find_element(By.XPATH, '//div[@role="main"]')
            all_els = panel.find_elements(By.XPATH, './/div[string-length(text()) > 8]')

            for el in all_els:
                txt = el.text.strip()
                if not txt or len(txt) > 300:
                    continue

                if row["Alamat"] == "N/A" and any(kw in txt for kw in ADDR_KEYWORDS):
                    row["Alamat"] = txt

                if row["Telepon"] == "N/A" and re.search(PHONE_REGEX, txt):
                    match = re.search(PHONE_REGEX, txt)
                    row["Telepon"] = match.group(0).strip() if match else txt

        except:
            pass

    return row


# =====================================================
# SCROLL PANEL KIRI (DAFTAR HASIL)
# =====================================================

def scroll_results(driver, wait, max_scroll=8):
    """
    Scroll panel hasil pencarian (list kiri).
    Menggunakan div[role='feed'] yang merupakan selector ARIA stabil.
    """
    try:
        scrollable_div = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )

        last_height = 0
        for _ in range(max_scroll):
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
            )
            time.sleep(1.5)

            new_height = driver.execute_script(
                "return arguments[0].scrollHeight", scrollable_div
            )
            if new_height == last_height:
                print(f"  📜 Scroll selesai (tidak ada konten baru)")
                break

            last_height = new_height

        return True

    except Exception as e:
        print(f"  ⚠️  Scroll gagal: {e}")
        return False


# =====================================================
# MAIN SCRAPER
# =====================================================

def scrape_google_maps(query, max_results=30, max_scroll=8):
    driver = None
    data = []

    try:
        driver = setup_driver()
        wait = WebDriverWait(driver, 30)

        print(f"🔎 Query: {query}")

        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        driver.get(url)
        time.sleep(3)  # Beri waktu lebih untuk load awal

        close_cookie_popup(driver)

        # ==========================
        # DETEKSI: LIST vs DETAIL PAGE
        # ==========================
        # Jika langsung masuk satu tempat (bukan list), URL mengandung /place/
        if "/maps/place/" in driver.current_url:
            print("  📍 Langsung masuk halaman detail (bukan list)")
            detail = extract_place_detail(driver)
            if detail:
                data.append(detail)
                print(f"  ✅ Ekstrak: {detail['Nama Perusahaan']}")
            return data

        # ==========================
        # SCROLL PANEL LIST
        # ==========================
        scroll_ok = scroll_results(driver, wait, max_scroll=max_scroll)
        time.sleep(1)

        # ==========================
        # AMBIL LIST ITEM — SELECTOR STABIL
        # Gunakan href yang selalu mengandung /maps/place/ untuk setiap item
        # Ini jauh lebih stabil daripada class name yang berubah
        # ==========================
        items = find_elements_safe(driver, [
            # Selector utama: link ke halaman place (PALING STABIL)
            (By.XPATH, '//div[@role="feed"]//a[contains(@href, "/maps/place/")]'),
            # Fallback 1: article role
            (By.XPATH, '//div[@role="feed"]//*[@role="article"]'),
            # Fallback 2: semua anchor di dalam feed
            (By.CSS_SELECTOR, 'div[role="feed"] a[href*="/maps/place/"]'),
        ])

        print(f"  📋 Ditemukan {len(items)} item di list")

        # ==========================
        # FALLBACK: tidak ada list sama sekali
        # ==========================
        if len(items) == 0:
            print("  ⚠️  List kosong, mencoba ekstrak dari halaman saat ini")
            detail = extract_place_detail(driver)
            if detail:
                data.append(detail)
            return data

        # ==========================
        # KUMPULKAN URL SEMUA PLACE DULU
        # Hindari stale element reference akibat DOM re-render saat click
        # ==========================
        place_urls = []
        for item in items[:max_results]:
            try:
                href = item.get_attribute("href")
                if href and "/maps/place/" in href and href not in place_urls:
                    place_urls.append(href)
            except:
                continue

        print(f"  🔗 {len(place_urls)} URL unik siap di-visit")

        # ==========================
        # VISIT SETIAP URL
        # Lebih reliable daripada click karena menghindari stale element
        # ==========================
        for idx, place_url in enumerate(place_urls):
            try:
                driver.get(place_url)
                time.sleep(2)

                detail = extract_place_detail(driver)
                if detail:
                    data.append(detail)
                    print(f"  ✅ [{idx+1}/{len(place_urls)}] {detail['Nama Perusahaan']}")
                else:
                    print(f"  ⚠️  [{idx+1}/{len(place_urls)}] Gagal ekstrak detail")

            except Exception as e:
                print(f"  ⚠️  Error item {idx+1}: {e}")
                continue

        return data

    except Exception as e:
        print(f"⚠️ Error scraping '{query}': {e}")
        return data

    finally:
        if driver:
            driver.quit()
            print(f"✅ Driver untuk '{query}' telah ditutup dengan aman.")