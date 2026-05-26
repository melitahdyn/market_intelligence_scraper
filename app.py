import streamlit as st
import pandas as pd
import time
import io
import gspread
import concurrent.futures
import enricher
from concurrent.futures import ThreadPoolExecutor
from oauth2client.service_account import ServiceAccountCredentials

from wilayah import get_provinces, get_regencies, get_districts
from scraper import scrape_google_maps
from smart_logic import smart_scrape
from segmentasi import classify_segmentasi


# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Canvassing Intelligence — Swabina",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS CLEAN FINAL FIXED
# ============================================================

st.markdown("""
<style>

/* =========================================================
BACKGROUND
========================================================= */
.stApp {
    background-color: #F5F7FB;
    color: #111827;
}

/* =========================================================
HIDE STREAMLIT
========================================================= */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* =========================================================
MAIN CONTAINER
========================================================= */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 1400px;
}

/* =========================================================
SIDEBAR
========================================================= */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A, #1E293B);
    padding-top: 1rem;
}

/* =========================================================
SIDEBAR CONTENT SPACING
========================================================= */
[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* =========================================================
HEADINGS
========================================================= */
h1, h2, h3, h4 {
    color: #0F172A !important;
    font-weight: 700 !important;
}

/* =========================================================
MAIN CONTENT TEXT
========================================================= */
.main p,
.main label,
.main span,
.main div {
    color: #111827 !important;
}

/* =========================================================
SIDEBAR TEXT ONLY
========================================================= */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
    color: #E5E7EB !important;
    font-size: 15px !important;
}

/* =========================================================
CUSTOM CARD
========================================================= */
.custom-card {
    background: white;
    padding: 1.2rem;
    border-radius: 18px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    margin-bottom: 1rem;
}

/* =========================================================
INPUT FULL WIDTH
========================================================= */
.stTextInput,
.stSelectbox,
.stSlider,
.stNumberInput {
    width: 100% !important;
}

/* =========================================================
INPUT STYLE
========================================================= */
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stNumberInput input {
    background: #FFFFFF !important;
    color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 14px !important;
    min-height: 52px !important;
    font-size: 16px !important;
}

/* =========================================================
BUTTON
========================================================= */
.stButton button {
    background: linear-gradient(135deg, #10B981, #06B6D4) !important;
    color: white !important;
    border: none !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    padding: 0.8rem 1.5rem !important;
    transition: 0.2s ease;
}

.stButton button:hover {
    transform: translateY(-1px);
    opacity: 0.96;
}

/* =========================================================
UPLOAD BOX
========================================================= */
[data-testid="stFileUploader"] {
    background: white;
    border: 2px dashed #CBD5E1;
    border-radius: 16px;
    padding: 1rem;
}

/* =========================================================
TABS
========================================================= */
button[data-baseweb="tab"] {
    background: #E5E7EB !important;
    color: #374151 !important;
    border-radius: 12px 12px 0 0 !important;
    padding: 10px 18px !important;
    font-weight: 600 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #10B981, #06B6D4) !important;
    color: white !important;
}

/* =========================================================
DATAFRAME
========================================================= */
.stDataFrame {
    border-radius: 14px;
    overflow: hidden;
}

/* =========================================================
PROGRESS BAR
========================================================= */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg,#10B981,#06B6D4);
}

/* =========================================================
SLIDER FIX
========================================================= */
.stSlider {
    padding-top: 10px !important;
    padding-bottom: 10px !important;
}

/* =========================================================
RADIO BUTTON SPACING
========================================================= */
div[role="radiogroup"] > label {
    margin-bottom: 12px !important;
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    font-size: 16px !important;
}

/* =========================================================
SIDEBAR CARD
========================================================= */
.sidebar-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    padding: 18px;
    border-radius: 18px;
    margin-bottom: 18px;
}

/* =========================================================
TITLE
========================================================= */
h1 {
    font-size: 3rem !important;
    margin-bottom: 0.2rem !important;
}

/* =========================================================
SUBTITLE
========================================================= */
.subtitle {
    color: #6B7280 !important;
    font-size: 1rem !important;
    margin-top: -8px !important;
    margin-bottom: 1.5rem !important;
}

/* =========================================================
CARD STYLE MAIN AREA
========================================================= */
.main-card {
    background: white;
    padding: 1.5rem;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.04);
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPER: Ekstrak Wilayah (Kota/Kab) dari string Alamat
# ============================================================
def extract_wilayah_from_alamat(alamat: str) -> str:
    """
    Parsing alamat Google Maps → ambil bagian Kota/Kabupaten.

    Contoh input:
      "Jl. Embong Malang No.1, Kedungdoro, Kec. Tegalsari, Kota Surabaya, Jawa Timur 60261"
      "Jalan Ahmad Yani 123, Sidoarjo, Jawa Timur 61214"
      "Jl. Raya Darmo No.90, Kab. Gresik, Jawa Timur"

    Output: "Kota Surabaya" / "Kabupaten Sidoarjo" / "Gresik" / "N/A"
    """
    import re

    if not alamat or alamat == "N/A":
        return "N/A"

    # ── Pola eksplisit: "Kota X" atau "Kabupaten X" atau "Kab. X" ──
    patterns = [
        r"(Kota\s+[A-Za-z\s]+?)(?:,|\d|$)",
        r"(Kabupaten\s+[A-Za-z\s]+?)(?:,|\d|$)",
        r"Kab\.\s*([A-Za-z\s]+?)(?:,|\d|$)",
        r"Kab\s+([A-Za-z\s]+?)(?:,|\d|$)",
    ]
    for pat in patterns:
        m = re.search(pat, alamat, re.IGNORECASE)
        if m:
            hasil = m.group(1).strip().title()
            if hasil:
                return hasil

    # ── Fallback: pecah by koma, cari bagian yang bukan jalan/kecamatan/kelurahan ──
    SKIP_KEYWORDS = [
        "jl.", "jalan", "gg.", "gang", "rt", "rw", "no.", "blok",
        "kec.", "kecamatan", "kel.", "kelurahan", "desa", "dusun",
        "indonesia", "provinsi"
    ]
    PROVINSI = [
        "aceh", "sumatera", "riau", "jambi", "bengkulu", "lampung",
        "bangka", "kepulauan", "dki", "jakarta", "jawa", "banten",
        "bali", "nusa", "kalimantan", "sulawesi", "gorontalo",
        "maluku", "papua"
    ]

    parts = [p.strip() for p in alamat.split(",")]
    for part in reversed(parts):  # dari belakang: kota biasanya di akhir
        part_lower = part.lower()
        if any(kw in part_lower for kw in SKIP_KEYWORDS):
            continue
        if any(prov in part_lower for prov in PROVINSI):
            continue
        clean = re.sub(r"\d", "", part).strip()
        if not clean:
            continue
        # buang kode pos di akhir
        clean = re.sub(r"\s*\d{5}\s*$", "", part).strip()
        if clean:
            return clean.title()

    return "N/A"


# ============================================================
# HELPER: Normalize dataframe
# ============================================================
def normalize_dataframe(df, keyword=""):
    if df.empty:
        return df

    df = df.copy()
    df_final = pd.DataFrame()
    df_final["Nama Perusahaan"] = df.get("Nama Perusahaan", "N/A")

    df_final["Segmentasi"] = df.apply(
        lambda x: classify_segmentasi(x.get("Nama Perusahaan", ""), keyword),
        axis=1
    )

    df_final["Wilayah (KOTA/KAB)"] = df.get("Lokasi/Wilayah", "N/A")
    df_final["Alamat"] = df.get("Alamat", "N/A")
    df_final["Link Google Maps"] = df.get("Link Maps", "N/A")
    df_final["Nomor"] = df.get("Telepon", "N/A")
    df_final["Email"] = df.get("Email", "N/A")
    df_final["Linkedin/Instagram"] = df.get("Linkedin/Instagram", "N/A")
    df_final["Web link"] = df.get("Website", "N/A")

    df_final = df_final.drop_duplicates(subset=["Nama Perusahaan", "Alamat"])
    return df_final


def enrich_contacts(df, progress_callback=None):
    """Enrichment dengan progress tracking."""
    if df.empty:
        return df

    df = df.copy()
    TARGET_SEGMENTS = [
        "Manufaktur", "Logistik & Ekspedisi", "Bank/Keuangan",
        "Rumah Sakit (Kesehatan)", "Instansi Pemerintah",
        "Telekomunikasi", "Energi & Utilitas"
    ]

    total = len(df)
    for i, (idx, row) in enumerate(df.iterrows()):
        if progress_callback:
            progress_callback(i, total, row.get("Nama Perusahaan", ""))

        if row["Segmentasi"] not in TARGET_SEGMENTS:
            continue

        web = row.get("Web link", "N/A")
        if web and web != "N/A":
            info = enricher.enrich_from_website(web)
            if df.at[idx, "Email"] == "N/A":
                df.at[idx, "Email"] = info["Email"]
            if df.at[idx, "Nomor"] == "N/A":
                df.at[idx, "Nomor"] = info["Nomor"]
            if df.at[idx, "Linkedin/Instagram"] == "N/A":
                df.at[idx, "Linkedin/Instagram"] = info["Linkedin/Instagram"]

    return df


# ============================================================
# HELPER: Upload to Google Sheets
# ============================================================
def upload_to_sheets(df):
    try:
        import json
        from google.oauth2.service_account import Credentials
        import gspread

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        # ← Baca dari st.secrets, bukan dari file
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key("1LjeNfv0Must7Tqs0GLTs4nW40UxiKOQwtjNGYCij_tU")
        sheet = spreadsheet.sheet1

        expected_cols = [
            "Nama Perusahaan", "Segmentasi", "Wilayah (KOTA/KAB)", "Alamat",
            "Link Google Maps", "Nomor", "Email", "Linkedin/Instagram", "Web link"
        ]

        df = df.copy()
        df = df[expected_cols]
        df = df.fillna("N/A").astype(str)

        existing_values = sheet.get_all_values()

        if not existing_values:
            sheet.append_row(expected_cols)
            existing_values = [expected_cols]
        elif existing_values[0] != expected_cols:
            sheet.delete_rows(1)
            sheet.insert_row(expected_cols, 1)
            existing_values = sheet.get_all_values()

        existing_keys = set()
        for row in existing_values[1:]:
            nama = row[0].strip().lower() if len(row) > 0 else ""
            alamat = row[3].strip().lower() if len(row) > 3 else ""
            existing_keys.add(f"{nama}|{alamat}")

        rows_to_append = []
        new_count = 0
        for _, r in df.iterrows():
            key = f"{str(r['Nama Perusahaan']).strip().lower()}|{str(r['Alamat']).strip().lower()}"
            if key not in existing_keys:
                rows_to_append.append(r.tolist())
                existing_keys.add(key)
                new_count += 1

        if not rows_to_append:
            st.info("⚠️ Tidak ada data baru (semua duplicate).")
            return True

        sheet.append_rows(rows_to_append)
        st.success(f"✅ Upload sukses! {new_count} data baru ditambahkan ke Spreadsheet.")
        return True

    except Exception as e:
        st.error(f"❌ Upload Error: {e}")
        return False


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="padding: 16px 0 8px; border-bottom: 1px solid rgba(255,255,255,0.07); margin-bottom: 16px;">
        <span style="font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:700; color:#00E5A0 !important;">🎯 CANVASSING INTEL</span>
        <div style="font-size:0.7rem; color:#8B90A0 !important; margin-top:2px;">by Swabina | Market Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    mode = st.radio("Mode Scraping:", [
        "🔍 Per Wilayah (Massal)",
        "📍 Satu Provinsi Full",
        "🎯 Cari Spesifik + Nearby",
        "🇮🇩 Nasional (Publik Sektor)",
        "📂 Import Excel & Enrich"
    ], index=3)

    st.markdown("---")

    # Init defaults
    target_list_loop = []
    selected_area_name = ""
    selected_prov_name = ""
    selected_reg_name = ""
    selected_kec_specific = ""
    input_keyword = ""
    mode_wilayah = "kecamatan"
    enable_nearby = False
    excel_df = None

    @st.cache_data
    def load_provinces():
        return get_provinces()

    prov_data = load_provinces()
    prov_map = {item['name']: item['id'] for item in prov_data}

    # ===================== MODE: NASIONAL =====================
    if mode == "🇮🇩 Nasional (Publik Sektor)":
        st.markdown("**📍 Konfigurasi Nasional**")
        st.info("🤖 Scraping otomatis di **38 Provinsi**")
        input_keyword = st.text_input("Nama Instansi / Dinas", value="BNPB")
        target_list_loop = [p['name'] for p in prov_data]
        selected_area_name = "Seluruh_Indonesia"

    # ===================== MODE: SATU PROVINSI =====================
    elif mode == "📍 Satu Provinsi Full":
        st.markdown("**📍 Konfigurasi Provinsi**")
        selected_prov_name = st.selectbox("Pilih Provinsi", list(prov_map.keys()))

        @st.cache_data
        def load_regencies(id_prov):
            return get_regencies(id_prov)

        if selected_prov_name:
            reg_data = load_regencies(prov_map[selected_prov_name])
            target_list_loop = [item['name'] for item in reg_data]

        selected_area_name = selected_prov_name
        input_keyword = st.text_input("Kategori Bisnis", value="Distributor Pupuk")

    # ===================== MODE: PER WILAYAH =====================
    elif mode == "🔍 Per Wilayah (Massal)":
        st.markdown("**📍 Lokasi Spesifik**")
        selected_prov_name = st.selectbox("Pilih Provinsi", list(prov_map.keys()))

        reg_map = {}
        if selected_prov_name:
            reg_data = get_regencies(prov_map[selected_prov_name])
            reg_map = {item['name']: item['id'] for item in reg_data}

        selected_reg_name = st.selectbox("Pilih Kota/Kabupaten", list(reg_map.keys()))

        dist_names = []
        if selected_reg_name:
            dist_data = get_districts(reg_map[selected_reg_name])
            dist_names = [item['name'] for item in dist_data]

        tipe_pencarian = st.radio(
            "Mode Wilayah:",
            ["🏙️ Kota/Kab", "🏘️ Per Kecamatan"],
            index=0
        )

        mode_wilayah = "kota" if tipe_pencarian == "🏙️ Kota/Kab" else "kecamatan"
        input_keyword = st.text_input("Kategori Bisnis / Instansi", value="Rumah Sakit")

        if tipe_pencarian == "🏙️ Kota/Kab":
            target_list_loop = [selected_reg_name] if selected_reg_name else []
            selected_area_name = selected_reg_name
        else:
            opsi = ["--- SEMUA KECAMATAN ---"] + dist_names
            pilihan_kec = st.selectbox("Target Kecamatan", opsi)
            if pilihan_kec == "--- SEMUA KECAMATAN ---":
                target_list_loop = dist_names
            else:
                target_list_loop = [pilihan_kec]
            selected_area_name = selected_reg_name

    # ===================== MODE: SPESIFIK =====================
    elif mode == "🎯 Cari Spesifik + Nearby":
        st.markdown("**📍 Lokasi Target**")
        selected_prov_name = st.selectbox("Pilih Provinsi", list(prov_map.keys()))

        reg_map = {}
        if selected_prov_name:
            reg_data = get_regencies(prov_map[selected_prov_name])
            reg_map = {item['name']: item['id'] for item in reg_data}

        selected_reg_name = st.selectbox("Pilih Kota/Kabupaten", list(reg_map.keys()))

        dist_names = []
        if selected_reg_name:
            dist_data = get_districts(reg_map[selected_reg_name])
            dist_names = [item['name'] for item in dist_data]

        selected_kec_specific = st.selectbox("Target Kecamatan", dist_names)
        selected_area_name = f"{selected_kec_specific}_{selected_reg_name}"
        input_keyword = st.text_input("Nama Perusahaan / Kategori", value="Indomaret")

        st.markdown("---")
        enable_nearby = st.checkbox("📡 Aktifkan Nearby", value=True)

    # ===================== MODE: IMPORT EXCEL =====================
    elif mode == "📂 Import Excel & Enrich":
        st.markdown("**📂 Import Data Perusahaan**")
        st.caption("Upload Excel dengan kolom: Nama Perusahaan, Website (opsional), Wilayah (opsional)")

        uploaded_file = st.file_uploader(
            "Upload file Excel (.xlsx / .csv)",
            type=["xlsx", "csv"],
            key="excel_uploader"
        )

        if uploaded_file:
            try:
                if uploaded_file.name.endswith(".csv"):
                    excel_df = pd.read_csv(uploaded_file)
                else:
                    excel_df = pd.read_excel(uploaded_file)

                st.success(f"✅ Loaded: {len(excel_df)} baris, {len(excel_df.columns)} kolom")
                st.caption(f"Kolom: {', '.join(excel_df.columns.tolist())}")
            except Exception as e:
                st.error(f"❌ Error membaca file: {e}")
                excel_df = None

    st.markdown("---")
    max_workers = st.slider("🤖 Jumlah Robot (Threads)", 1, 4, 2)
    st.markdown("---")
    st.caption("© 2025 duo gen-Z ITS · All Rights Reserved")


# ============================================================
# MAIN HEADER
# ============================================================
st.markdown("""
<div style="border-bottom: 1px solid rgba(255,255,255,0.07); padding-bottom: 20px; margin-bottom: 24px;">
    <div style="display:flex; align-items:center; gap:14px;">
        <div style="width:48px; height:48px; background:rgba(0,229,160,0.12); border:1px solid rgba(0,229,160,0.3); 
                    border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:1.5rem;">
            🎯
        </div>
        <div>
            <h1 style="font-family:'Syne',sans-serif !important; font-size:1.8rem !important; 
                       font-weight:800 !important; margin:0; color:#F0F2F5 !important; letter-spacing:-0.3px;">
                Market Intelligence Scraper
            </h1>
            <p style="font-size:0.82rem; color:#8B90A0 !important; margin:2px 0 0;">
                Database calon mitra otomatis — scraping, enrichment & sinkronisasi Google Sheets
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================
tab_scrape, tab_excel = st.tabs(["🔍 Scraping Maps", "📂 Import & Enrich Excel"])


# ============================================================
# TAB 1: SCRAPING MAPS
# ============================================================
with tab_scrape:

    if mode == "📂 Import Excel & Enrich":
        st.info("💡 Pilih tab **Import & Enrich Excel** atau ganti mode di sidebar ke mode scraping.")

    else:
        # Summary config
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">MODE</div>
                <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:600; 
                            color:#00E5A0 !important; margin-top:4px;">{mode.split(' ', 1)[1] if ' ' in mode else mode}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_cfg2:
            area_display = selected_area_name or selected_reg_name or "—"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">AREA TARGET</div>
                <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:600; 
                            color:#5B8DEF !important; margin-top:4px;">{area_display[:30]}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_cfg3:
            kw_display = input_keyword or "—"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-label">KEYWORD</div>
                <div style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:600; 
                            color:#FF9F40 !important; margin-top:4px;">{kw_display[:25]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # PROGRESS SECTION (always visible, updates saat scraping)
        progress_section = st.container()
        with progress_section:
            st.markdown('<div class="progress-card">', unsafe_allow_html=True)

            col_prog1, col_prog2 = st.columns([3, 1])
            with col_prog1:
                prog_title = st.empty()
                prog_title.markdown("**⏳ Siap untuk scraping...**")
                progress_bar = st.progress(0)
                prog_detail = st.empty()
                prog_detail.markdown(
                    "<span style='font-size:0.82rem; color:#8B90A0;'>Tekan tombol untuk memulai</span>",
                    unsafe_allow_html=True
                )
            with col_prog2:
                prog_count = st.empty()
                prog_count.markdown("""
                <div style="text-align:center; padding:10px;">
                    <div class="stat-number" style="font-size:1.8rem;">0</div>
                    <div class="stat-label">Data Terkumpul</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # LOG CONTAINER
        log_expander = st.expander("📋 Live Log Scraping", expanded=False)
        log_placeholder = log_expander.empty()
        log_lines = []

        def update_log(msg):
            log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
            if len(log_lines) > 50:
                log_lines.pop(0)
            log_text = "\n".join(log_lines[-25:])
            log_placeholder.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

        # START BUTTON
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            start_btn = st.button("🚀  MULAI SCRAPING", width='stretch', type="primary")

        st.markdown("<br>", unsafe_allow_html=True)

        # RESULT PLACEHOLDER
        result_placeholder = st.empty()

        # ============================================================
        # HELPER FUNCTION — di luar if block agar tidak ada masalah scope
        # ============================================================
        def clean_area(area):
            return (
                area.replace("KABUPATEN", "")
                    .replace("KOTA", "")
                    .replace("Kab.", "")
                    .strip()
    )
        
        def expand_keyword(keyword):
            k = keyword.lower()

            mapping = {
                "rumah sakit": ["rumah sakit", "rs", "rsud", "klinik"],
                "badan pusat statistik": ["bps", "badan pusat statistik"],
                "bank": ["bank", "bca", "bri", "mandiri", "bni"],
                "logistik": ["logistik", "ekspedisi", "gudang"],
            }

            for key, variants in mapping.items():
                if key in k:
                    return variants

            return [keyword]

        def process_single_area(area_name, keyword, mode_type, parent_area, mode_wil="kecamatan"):
            try:
                if mode_wil == "kota":
                    area_clean = clean_area(area_name)
                    keywords = expand_keyword(keyword)
 
                    queries = []
                    for kw in keywords:
                        queries.extend([
                            f"{kw} {area_clean}",
                            f"{kw} di {area_clean}",
                            f"{kw} {area_clean} Jawa Timur",
                            f"{kw} near {area_clean}",
                        ])
 
                    all_data = []
                    for q in queries:
                        hasil = scrape_google_maps(q)
                        if hasil:
                            all_data.extend(hasil)
 
                    # Fallback jika semua query kosong
                    if not all_data:
                        print("⚠️ Fallback query aktif")
                        fallback_query = f"{keyword} {area_clean} Indonesia"
                        hasil = scrape_google_maps(fallback_query)  # FIX: pakai fallback_query
                        if hasil:
                            all_data.extend(hasil)
 
                    # FIX UTAMA: return df jika ada data
                    if all_data:
                        df = pd.DataFrame(all_data).drop_duplicates(
                            subset=["Nama Perusahaan", "Alamat"]
                        )
                        df["Lokasi/Wilayah"] = area_name
                        df["Status"] = mode_type
                        return df  # ← RETURN DATA, bukan pd.DataFrame() kosong!
 
                    return pd.DataFrame()  # hanya kalau benar-benar kosong
 
                else:
                    # mode kecamatan — pakai smart_scrape
                    df = smart_scrape(area_name, keyword, parent_area)
                    if not df.empty:
                        df["Lokasi/Wilayah"] = parent_area
                        df["Status"] = mode_type
                        return df
                    return pd.DataFrame()
 
            except Exception as e:
                print(f"Error process_single_area ({area_name}): {e}")
                return pd.DataFrame()

        # ============================================================
        # EKSEKUSI SCRAPING
        # ============================================================
        if start_btn:
            all_results = []
            all_results_df = pd.DataFrame()

            total_targets = len(target_list_loop) if target_list_loop else 1
            completed = 0

            # Mode massal (nasional, provinsi, per wilayah)
            if mode in ["🇮🇩 Nasional (Publik Sektor)", "📍 Satu Provinsi Full", "🔍 Per Wilayah (Massal)"]:

                prog_title.markdown("**🤖 Robot sedang berjalan...**")
                update_log(f"🚀 Memulai scraping: {input_keyword} | {total_targets} area target")

                lock = __import__('threading').Lock()
                completed_count = [0]

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            process_single_area, area, input_keyword, mode,
                            selected_area_name, mode_wilayah
                        ): area
                        for area in target_list_loop
                    }

                    for future in concurrent.futures.as_completed(futures):
                        area = futures[future]
                        try:
                            df_result = future.result()
                            with lock:
                                completed_count[0] += 1
                                pct = int(completed_count[0] / total_targets * 100)
                                progress_bar.progress(pct)

                                if not df_result.empty:
                                    all_results.append(df_result)

                                total_so_far = sum(len(r) for r in all_results)

                                prog_detail.markdown(
                                    f"<span style='font-size:0.82rem; color:#8B90A0;'>✓ {area} selesai — {completed_count[0]}/{total_targets} area</span>",
                                    unsafe_allow_html=True
                                )
                                prog_count.markdown(f"""
                                <div style="text-align:center; padding:10px;">
                                    <div class="stat-number" style="font-size:1.8rem;">{total_so_far}</div>
                                    <div class="stat-label">Data Terkumpul</div>
                                </div>
                                """, unsafe_allow_html=True)
                                update_log(f"✅ {area}: {len(df_result)} data | Total: {total_so_far}")

                        except Exception as e:
                            update_log(f"⚠️ Error di {area}: {e}")

            # Mode spesifik (single query)
            else:
                prog_title.markdown("**🎯 Mencari target spesifik...**")
                update_log(f"🎯 Query: {input_keyword} di {selected_reg_name}")
                progress_bar.progress(20)

                query = f"{input_keyword} {selected_reg_name}"
                try:
                    hasil_main = scrape_google_maps(query)
                    if hasil_main:
                        df_main = pd.DataFrame(hasil_main)
                        df_main["Lokasi/Wilayah"] = selected_reg_name
                        df_main["Status"] = "TARGET UTAMA"
                        all_results_df = df_main
                        update_log(f"✅ Ditemukan {len(df_main)} hasil")
                    progress_bar.progress(100)
                except Exception as e:
                    st.error(f"Error: {e}")
                    update_log(f"❌ Error: {e}")

            # Gabungkan semua hasil
            if all_results:
                all_results_df = pd.concat(all_results, ignore_index=True)
                all_results_df = all_results_df.drop_duplicates(subset=["Nama Perusahaan", "Alamat"])

            progress_bar.progress(100)
            prog_title.markdown("**✅ Scraping selesai!**")

            # =====================================
            # POST-PROCESSING
            # =====================================
            if not all_results_df.empty:
                all_results_df = all_results_df.drop_duplicates(subset=["Nama Perusahaan", "Alamat"])
                df_upload = normalize_dataframe(all_results_df, input_keyword)

                # Enrichment dengan progress
                enrich_prog = st.progress(0)
                enrich_status = st.empty()

                def enrich_progress_cb(i, total, name):
                    pct = int(i / total * 100) if total > 0 else 0
                    enrich_prog.progress(pct)
                    enrich_status.markdown(
                        f"<span style='font-size:0.82rem; color:#8B90A0;'>🔎 Enriching: {name[:40]}...</span>",
                        unsafe_allow_html=True
                    )

                with st.spinner("🔎 Mencari email, nomor & sosial media dari website..."):
                    df_upload = enrich_contacts(df_upload, progress_callback=enrich_progress_cb)

                enrich_prog.progress(100)
                enrich_status.markdown(
                    "<span style='font-size:0.82rem; color:#00E5A0;'>✅ Enrichment selesai!</span>",
                    unsafe_allow_html=True
                )

                # Upload ke Sheets
                with st.spinner("☁️ Menyinkronkan ke Google Sheets..."):
                    upload_to_sheets(df_upload)
                    update_log("☁️ Upload ke Google Sheets selesai")

                # Final stats
                total_data = len(df_upload)
                has_email = (df_upload["Email"] != "N/A").sum()
                has_nomor = (df_upload["Nomor"] != "N/A").sum()
                has_sosmed = (df_upload["Linkedin/Instagram"] != "N/A").sum()

                prog_count.markdown(f"""
                <div style="text-align:center; padding:10px;">
                    <div class="stat-number" style="font-size:1.8rem;">{total_data}</div>
                    <div class="stat-label">Total Final</div>
                </div>
                """, unsafe_allow_html=True)

                # Stats row
                st.markdown("<br>", unsafe_allow_html=True)
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    st.markdown(f'<div class="stat-card"><div class="stat-number">{total_data}</div><div class="stat-label">Total Data</div></div>', unsafe_allow_html=True)
                with sc2:
                    st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#5B8DEF !important;">{has_email}</div><div class="stat-label">Punya Email</div></div>', unsafe_allow_html=True)
                with sc3:
                    st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#FF9F40 !important;">{has_nomor}</div><div class="stat-label">Punya Nomor</div></div>', unsafe_allow_html=True)
                with sc4:
                    st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#FF6B6B !important;">{has_sosmed}</div><div class="stat-label">Punya Sosmed</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Download button
                col_dl1, col_dl2 = st.columns([3, 1])
                with col_dl2:
                    csv_data = df_upload.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Download CSV",
                        data=csv_data,
                        file_name=f"scraping_{input_keyword.replace(' ','_')}_{time.strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        width='stretch'
                    )

                # Dataframe
                st.dataframe(df_upload, width='stretch', height=450)

            else:
                st.warning("⚠️ Tidak ada data ditemukan. Coba ubah keyword atau perluas area pencarian.")
                update_log("⚠️ Tidak ada data ditemukan")


# ============================================================
# TAB 2: IMPORT EXCEL & ENRICH
# ============================================================
with tab_excel:
    st.markdown("### 📂 Import Daftar Perusahaan dari Excel")
    st.markdown(
        "<span style='color:#8B90A0; font-size:0.85rem;'>Upload file Excel/CSV berisi daftar perusahaan, "
        "robot akan mencari email, nomor telepon, dan sosial media secara otomatis.</span>",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Format guide
    with st.expander("📋 Format Excel yang Diperlukan"):
        st.markdown("""
        **Kolom wajib:**
        - `Nama Perusahaan` — nama perusahaan/instansi

        **Kolom opsional (bantu akurasi enrichment):**
        - `Website` — URL website perusahaan (jika ada)
        - `Wilayah` — nama kota/kabupaten
        - `Alamat` — alamat lengkap

        **Contoh:**

        | Nama Perusahaan | Website | Wilayah |
        |---|---|---|
        | RSUD Dr. Soetomo | https://rsudsoetomo.id | Surabaya |
        | Pabrik Semen Gresik | https://semengresik.com | Gresik |
        | PT Bank BRI Tbk | https://bri.co.id | Jakarta |
        """)

    # Uploader
    uploaded_excel = st.file_uploader(
        "📎 Upload File Excel atau CSV",
        type=["xlsx", "xls", "csv"],
        key="main_excel_uploader"
    )

    if uploaded_excel:
        try:
            if uploaded_excel.name.endswith(".csv"):
                df_input = pd.read_csv(uploaded_excel)
            else:
                df_input = pd.read_excel(uploaded_excel)
        except Exception as e:
            st.error(f"❌ Gagal membaca file: {e}")
            df_input = None

        if df_input is not None:
            st.success(f"✅ File berhasil dibaca: **{len(df_input)} baris** | **{len(df_input.columns)} kolom**")

            # Preview
            st.markdown("**Preview Data:**")
            st.dataframe(df_input.head(5), width='stretch')

            # Column mapping
            st.markdown("---")
            st.markdown("**⚙️ Mapping Kolom**")
            col_map1, col_map2, col_map3 = st.columns(3)

            all_cols = ["(tidak ada)"] + df_input.columns.tolist()

            with col_map1:
                col_nama = st.selectbox(
                    "Kolom Nama Perusahaan",
                    all_cols,
                    index=1 if len(df_input.columns) > 0 else 0
                )
            with col_map2:
                # Cari kolom website secara otomatis
                website_idx = 0
                for i, c in enumerate(all_cols):
                    if "web" in c.lower() or "site" in c.lower() or "url" in c.lower():
                        website_idx = i
                        break
                col_website = st.selectbox("Kolom Website (opsional)", all_cols, index=website_idx)
            with col_map3:
                wilayah_idx = 0
                for i, c in enumerate(all_cols):
                    if "wilayah" in c.lower() or "kota" in c.lower() or "lokasi" in c.lower():
                        wilayah_idx = i
                        break
                col_wilayah = st.selectbox("Kolom Wilayah (opsional)", all_cols, index=wilayah_idx)

            st.markdown("<br>", unsafe_allow_html=True)

            # Progress section
            excel_prog_card = st.container()
            with excel_prog_card:
                st.markdown('<div class="progress-card">', unsafe_allow_html=True)
                ecol1, ecol2 = st.columns([3, 1])
                with ecol1:
                    excel_prog_title = st.empty()
                    excel_prog_title.markdown("**⏳ Siap untuk enrichment...**")
                    excel_prog_bar = st.progress(0)
                    excel_prog_detail = st.empty()
                with ecol2:
                    excel_count = st.empty()
                    excel_count.markdown("""
                    <div style="text-align:center; padding:10px;">
                        <div class="stat-number" style="font-size:1.5rem;">0/0</div>
                        <div class="stat-label">Progress</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            col_ebtn1, col_ebtn2, col_ebtn3 = st.columns([1, 2, 1])
            with col_ebtn2:
                start_excel_btn = st.button(
                    "🔍  MULAI ENRICHMENT",
                    width='stretch',
                    type="primary",
                    key="excel_start"
                )

            excel_result_placeholder = st.empty()

            if start_excel_btn:
                if col_nama == "(tidak ada)":
                    st.error("❌ Pilih kolom 'Nama Perusahaan' terlebih dulu!")
                else:
                    excel_prog_title.markdown("**🔍 Scraping + Enrichment berjalan...**")

                    # ── Ambil daftar nama perusahaan dari Excel ──────────────
                    nama_list = df_input[col_nama].dropna().astype(str).tolist()
                    nama_list = [n.strip() for n in nama_list if n.strip() and n.strip() != "N/A"]

                    wilayah_list = []
                    if col_wilayah != "(tidak ada)":
                        wilayah_list = df_input[col_wilayah].fillna("").astype(str).tolist()
                    else:
                        wilayah_list = [""] * len(nama_list)

                    total_excel = len(nama_list)
                    enriched_count = 0
                    rows_result = []

                    for i, nama in enumerate(nama_list):
                        wilayah = wilayah_list[i] if i < len(wilayah_list) else ""

                        # ── Update progress UI ───────────────────────────────
                        pct = int((i + 1) / total_excel * 100) if total_excel > 0 else 0
                        excel_prog_bar.progress(pct)
                        excel_prog_detail.markdown(
                            f"<span style='font-size:0.82rem; color:#8B90A0;'>"
                            f"🔎 [{i+1}/{total_excel}] Scraping: {nama[:50]}...</span>",
                            unsafe_allow_html=True
                        )
                        excel_count.markdown(f"""
                        <div style="text-align:center; padding:10px;">
                            <div class="stat-number" style="font-size:1.5rem;">{i+1}/{total_excel}</div>
                            <div class="stat-label">Progress</div>
                        </div>
                        """, unsafe_allow_html=True)

                        # ── LANGKAH 1: Scrape Google Maps pakai nama perusahaan ──
                        # Susun query: nama saja, lalu nama + wilayah jika ada
                        queries_to_try = [nama]
                        if wilayah and wilayah.strip():
                            queries_to_try.append(f"{nama} {wilayah.strip()}")

                        maps_result = None
                        for q in queries_to_try:
                            hasil = scrape_google_maps(q, max_results=3, max_scroll=2)
                            if hasil:
                                # Ambil hasil paling relevan: nama paling mirip
                                nama_lower = nama.lower()
                                best = None
                                for h in hasil:
                                    h_nama = str(h.get("Nama Perusahaan", "")).lower()
                                    # Cek kecocokan nama (setidaknya 1 kata kunci cocok)
                                    kata = [k for k in nama_lower.split() if len(k) > 3]
                                    if any(k in h_nama for k in kata):
                                        best = h
                                        break
                                # Kalau tidak ada yang cocok, ambil hasil pertama saja
                                maps_result = best if best else hasil[0]
                                break

                        # ── Bangun row hasil ─────────────────────────────────
                        row_data = {
                            "Nama Perusahaan": nama,
                            "Segmentasi": classify_segmentasi(nama, ""),
                            "Wilayah (KOTA/KAB)": wilayah if wilayah else "N/A",
                            "Alamat": "N/A",
                            "Link Google Maps": "N/A",
                            "Nomor": "N/A",
                            "Email": "N/A",
                            "Linkedin/Instagram": "N/A",
                            "Web link": "N/A",
                        }

                        if maps_result:
                            alamat_scraped = maps_result.get("Alamat", "N/A") or "N/A"
                            row_data["Alamat"]             = alamat_scraped
                            row_data["Nomor"]              = maps_result.get("Telepon", "N/A") or "N/A"
                            row_data["Web link"]           = maps_result.get("Website", "N/A") or "N/A"
                            row_data["Link Google Maps"]   = maps_result.get("Link Maps", "N/A") or "N/A"
                            row_data["Email"]              = maps_result.get("Email", "N/A") or "N/A"
                            row_data["Linkedin/Instagram"] = maps_result.get("Linkedin/Instagram", "N/A") or "N/A"

                            # ── Ekstrak Wilayah dari Alamat yang discrape ────
                            # Prioritas: dari Excel jika ada, fallback parse dari alamat
                            if not wilayah or wilayah.strip() == "":
                                row_data["Wilayah (KOTA/KAB)"] = extract_wilayah_from_alamat(alamat_scraped)
                            else:
                                # Tetap pakai wilayah dari Excel, tapi jika masih N/A coba parse alamat
                                row_data["Wilayah (KOTA/KAB)"] = wilayah.strip() or extract_wilayah_from_alamat(alamat_scraped)

                            # ── LANGKAH 2: Enrich dari website jika ada ──────
                            web = row_data["Web link"]
                            if web and web != "N/A" and str(web).startswith("http"):
                                info = enricher.enrich_from_website(str(web))
                                if row_data["Email"] == "N/A":
                                    row_data["Email"] = info.get("Email", "N/A")
                                if row_data["Nomor"] == "N/A":
                                    row_data["Nomor"] = info.get("Nomor", "N/A")
                                if row_data["Linkedin/Instagram"] == "N/A":
                                    row_data["Linkedin/Instagram"] = info.get("Linkedin/Instagram", "N/A")

                            # Hitung yang berhasil dapat minimal 1 data kontak
                            if any(row_data[k] != "N/A" for k in ["Nomor", "Email", "Web link", "Alamat"]):
                                enriched_count += 1

                        rows_result.append(row_data)

                    df_work = pd.DataFrame(rows_result)

                    excel_prog_bar.progress(100)
                    excel_prog_title.markdown("**✅ Enrichment selesai!**")
                    excel_prog_detail.markdown(
                        f"<span style='font-size:0.82rem; color:#00E5A0;'>✅ {enriched_count} dari {total_excel} berhasil di-enrich</span>",
                        unsafe_allow_html=True
                    )

                    # Stats
                    st.markdown("<br>", unsafe_allow_html=True)
                    es1, es2, es3, es4 = st.columns(4)
                    with es1:
                        st.markdown(f'<div class="stat-card"><div class="stat-number">{total_excel}</div><div class="stat-label">Total Diproses</div></div>', unsafe_allow_html=True)
                    with es2:
                        has_e = (df_work["Email"] != "N/A").sum()
                        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#5B8DEF !important;">{has_e}</div><div class="stat-label">Punya Email</div></div>', unsafe_allow_html=True)
                    with es3:
                        has_n = (df_work["Nomor"] != "N/A").sum()
                        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#FF9F40 !important;">{has_n}</div><div class="stat-label">Punya Nomor</div></div>', unsafe_allow_html=True)
                    with es4:
                        has_s = (df_work["Linkedin/Instagram"] != "N/A").sum()
                        st.markdown(f'<div class="stat-card"><div class="stat-number" style="color:#FF6B6B !important;">{has_s}</div><div class="stat-label">Punya Sosmed</div></div>', unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Download
                    col_ed1, col_ed2 = st.columns([3, 1])
                    with col_ed2:
                        csv_excel = df_work.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Download Hasil",
                            data=csv_excel,
                            file_name=f"enriched_{time.strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            width='stretch'
                        )

                    # Upload to sheets
                    with st.spinner("☁️ Upload ke Google Sheets..."):
                        upload_cols = ["Nama Perusahaan", "Segmentasi", "Wilayah (KOTA/KAB)",
                                       "Email", "Nomor", "Linkedin/Instagram", "Web link"]
                        df_sheets = df_work.copy()
                        for c in upload_cols:
                            if c not in df_sheets.columns:
                                df_sheets[c] = "N/A"
                        df_sheets["Alamat"] = "N/A"
                        df_sheets["Link Google Maps"] = "N/A"
                        upload_to_sheets(df_sheets)

                    st.dataframe(df_work, width='stretch', height=450)

    else:
        st.markdown("""
        <div style="background:rgba(91,141,239,0.06); border:1px dashed rgba(91,141,239,0.3); 
                    border-radius:12px; padding:40px; text-align:center; margin-top:24px;">
            <div style="font-size:2rem; margin-bottom:12px;">📂</div>
            <div style="font-family:'Syne',sans-serif; font-size:1.1rem; color:#F0F2F5 !important;">Upload file Excel atau CSV</div>
            <div style="font-size:0.82rem; color:#8B90A0 !important; margin-top:6px;">
                Format: .xlsx, .xls, atau .csv · Max 10MB
            </div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div class="footer-bar">
    © 2025 <strong style="color:#00E5A0 !important;">duo gen-Z ITS</strong> &nbsp;·&nbsp; 
    Market Intelligence & Canvassing Tool &nbsp;·&nbsp; All Rights Reserved
</div>
""", unsafe_allow_html=True)
