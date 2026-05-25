import pandas as pd
import time
from scraper import scrape_google_maps

def classify_keyword(keyword):
    keyword = keyword.lower()

    instansi = ["bps", "badan", "dinas", "kantor", "kementerian", "pemerintah"]
    bisnis = ["cafe", "klinik", "toko", "restoran", "salon", "apotek"]

    if any(k in keyword for k in instansi):
        return "instansi"
    elif any(k in keyword for k in bisnis):
        return "bisnis"
    else:
        return "umum"


def generate_queries(keyword, area_name, parent_area, tipe):
    
    if tipe == "instansi":
        return [
            f"{keyword} {parent_area}",
            f"{keyword} di {parent_area}",
            f"{keyword} {parent_area} Indonesia"
        ]

    elif tipe == "bisnis":
        return [
            f"{keyword} di Kecamatan {area_name}, {parent_area}",
            f"{keyword} {area_name} {parent_area}"
        ]

    else:
        return [
            f"{keyword} {parent_area}",
            f"{keyword} di {parent_area}",
            f"{keyword} {area_name} {parent_area}"
        ]


def smart_scrape(area_name, keyword, parent_area):
    
    tipe = classify_keyword(keyword)
    queries = generate_queries(keyword, area_name, parent_area, tipe)

    all_data = []

    for q in queries:
        print(f"🔎 Smart Query: {q}")

        result = scrape_google_maps(q)

        if result:
            df = pd.DataFrame(result)

            if not df.empty:
                df['Query Source'] = q
                all_data.append(df)
                break

        time.sleep(2)

    # fallback global
    if not all_data:
        print("⚠️ Fallback global aktif")
        result = scrape_google_maps(f"{keyword} {parent_area}")

        if result:
            return pd.DataFrame(result)

    if all_data:
        return pd.concat(all_data, ignore_index=True)

    return pd.DataFrame()