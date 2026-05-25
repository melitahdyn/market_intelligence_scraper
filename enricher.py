# =====================================================
# ENRICHER.PY
# =====================================================

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

EMAIL_PATTERN = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
PHONE_PATTERN = r"(?:\+62|62|0)[\s\-]?(?:\d[\s\-]?){7,13}\d"

IG_PATTERN = r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_\.]+)"
LI_PATTERN = r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9_\-\.]+)"

EMAIL_BLACKLIST = [
    "@gmail.com",
    "@yahoo.com",
    "@hotmail.com",
]

WEBSITE_CACHE = {}
HTML_CACHE = {}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# =====================================================
# HELPERS
# =====================================================

def clean_url(url):
    if not url or url == "N/A":
        return None

    url = url.strip().rstrip("/")

    if not url.startswith("http"):
        url = "https://" + url

    return url


def extract_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "").lower()
    except:
        return ""


def is_valid_email(email):

    email = email.lower()

    for bl in EMAIL_BLACKLIST:
        if bl in email:
            return False

    return True


def fetch_page(url, timeout=6):

    if url in HTML_CACHE:
        return HTML_CACHE[url]

    try:
        r = SESSION.get(
            url,
            timeout=timeout,
            allow_redirects=True
        )

        if r.status_code == 200:
            HTML_CACHE[url] = r.text
            return r.text

    except:
        return None

    return None


# =====================================================
# EXTRACT CONTACT
# =====================================================

def extract_contacts_from_html(html):

    if not html:
        return {
            "Email": "N/A",
            "Nomor": "N/A",
            "Linkedin/Instagram": "N/A"
        }

    soup = BeautifulSoup(html, "html.parser")

    html_text = soup.get_text(" ", strip=True)

    # EMAIL
    emails = []

    for email in re.findall(EMAIL_PATTERN, html_text):

        if is_valid_email(email):
            emails.append(email)

    email_result = emails[0] if emails else "N/A"

    # PHONE
    phones = re.findall(PHONE_PATTERN, html_text)

    phone_result = phones[0] if phones else "N/A"

    # SOCIAL MEDIA
    social = "N/A"

    all_links = [a.get("href", "") for a in soup.find_all("a", href=True)]

    for link in all_links:

        if "instagram.com" in link:
            social = link
            break

        if "linkedin.com" in link:
            social = link
            break

    return {
        "Email": email_result,
        "Nomor": phone_result,
        "Linkedin/Instagram": social
    }


# =====================================================
# ENRICH WEBSITE
# =====================================================

def enrich_from_website(website_url):

    website_url = clean_url(website_url)

    if not website_url:
        return {
            "Email": "N/A",
            "Nomor": "N/A",
            "Linkedin/Instagram": "N/A"
        }

    domain = extract_domain(website_url)

    if domain in WEBSITE_CACHE:
        return WEBSITE_CACHE[domain]

    result = {
        "Email": "N/A",
        "Nomor": "N/A",
        "Linkedin/Instagram": "N/A"
    }

    html_main = fetch_page(website_url)

    if html_main:

        temp = extract_contacts_from_html(html_main)

        for k, v in temp.items():
            if v != "N/A":
                result[k] = v

        soup = BeautifulSoup(html_main, "html.parser")

        candidate_links = []

        keywords = [
            "contact",
            "kontak",
            "about",
            "tentang"
        ]

        for a in soup.find_all("a", href=True):

            href = a["href"].lower()

            if any(k in href for k in keywords):

                full_url = urljoin(website_url, a["href"])

                if domain in extract_domain(full_url):
                    candidate_links.append(full_url)

        urls_to_scan = list(dict.fromkeys(candidate_links))[:3]

        for u in urls_to_scan:

            html_page = fetch_page(u)

            if html_page:

                temp = extract_contacts_from_html(html_page)

                for k, v in temp.items():

                    if result[k] == "N/A" and v != "N/A":
                        result[k] = v

    WEBSITE_CACHE[domain] = result

    return result


# =====================================================
# FAST FALLBACK
# =====================================================

def enrich_from_name(company_name, location=""):

    return {
        "Email": "N/A",
        "Nomor": "N/A",
        "Linkedin/Instagram": "N/A"
    }