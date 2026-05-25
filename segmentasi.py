import re

SEGMENT_RULES = [

    # =====================================================
    # ENERGI & UTILITAS
    # =====================================================
    ("Energi & Utilitas", [
        r"\bpln\b",
        r"perusahaan\s*listrik\s*negara",
        r"\bpertamina\b",
        r"\boil\b",
        r"\bgas\b",
        r"\bmigas\b",
        r"\benergi\b",
        r"\bpower\b",
        r"\bpembangkit\b",
        r"\bup3\b",
        r"\bulp\b",
        r"\bspbu\b",
        r"\bdep[o0]\b",
        r"\bdepo\b"
    ]),

    # =====================================================
    # TELEKOMUNIKASI
    # =====================================================
    ("Telekomunikasi", [
        r"\btelkom\b",
        r"\btelkomsel\b",
        r"\bindosat\b",
        r"\bxl\b",
        r"\baxis\b",
        r"\bsmartfren\b",
        r"\btri\b",
        r"\b3\b",
        r"\bprovider\b",
        r"\btelekomunikasi\b",
        r"\btelecommunication\b"
    ]),

    # =====================================================
    # KEPOLISIAN
    # =====================================================
    ("Kantor Polisi", [
        r"\bpolres\b",
        r"\bpolsek\b",
        r"\bpolda\b",
        r"\bkepolisian\b",
        r"\bpolisi\b"
    ]),

    # =====================================================
    # TNI / MILITER
    # =====================================================
    ("Instansi Pemerintah", [
        r"\bkodim\b",
        r"\bkoramil\b",
        r"\btni\b",
        r"\btentara\b",
        r"\bkomando\b",
        r"\bal\b",
        r"\bau\b",
        r"\bad\b"
    ]),

    # =====================================================
    # INSTANSI PEMERINTAH (KANTOR/DINAS)
    # =====================================================
    ("Instansi Pemerintah", [
        r"\bdprd\b",
        r"\bdpr\b",
        r"\bmpr\b",

        r"\bbps\b",
        r"\bbnpb\b",
        r"\bbpbd\b",
        r"\bbnpt\b",
        r"\bbpk\b",
        r"\bkejaksaan\b",
        r"\bpengadilan\b",
        r"\bkementerian\b",
        r"\bdinas\b",
        r"\bpemerintah\b",
        r"\bpemkot\b",
        r"\bpemkab\b",
        r"\bpemprov\b",
        r"\bsekretariat\s*daerah\b",
        r"\bbalai\b",
        r"\bdisdukcapil\b",
        r"\bdukcapil\b",
        r"\bbappeda\b",
        r"\bdisnaker\b",
        r"\bdishub\b",
        r"\bdlh\b",
        r"\bkominfo\b",
        r"\bkpu\b",
        r"\bbawaslu\b",
        r"\bkelurahan\b",
        r"\bkecamatan\b",
        r"\bdesa\b"
    ]),

    # =====================================================
    # RUMAH SAKIT / KESEHATAN
    # =====================================================
    ("Rumah Sakit (Kesehatan)", [
        r"\brsud\b",
        r"\brsup\b",
        r"\brsia\b",
        r"\brsu\b",
        r"\brs\b",
        r"rumah\s*sakit",
        r"\bklinik\b",
        r"\bpuskesmas\b",
        r"\bapotek\b",
        r"\blaboratorium\b",
        r"\blab\b",
        r"\bdokter\b",
        r"\bfarmasi\b"
    ]),

    # =====================================================
    # UNIVERSITAS / PENDIDIKAN
    # =====================================================
    ("Universitas / Lembaga Pendidikan", [
        r"\buniversitas\b",
        r"\binstitut\b",
        r"\bpoliteknik\b",
        r"\bakademi\b",
        r"\bsekolah\b",
        r"\bsmk\b",
        r"\bsma\b",
        r"\bsmp\b",
        r"\bsd\b",
        r"\bmadrasah\b",
        r"\bpesantren\b",
        r"\bpondok\b",
        r"\bstie\b",
        r"\bstmik\b"
    ]),

    # =====================================================
    # TEMPAT IBADAH
    # =====================================================
    ("Tempat Ibadah", [
        r"\bmasjid\b",
        r"\bmusholla\b",
        r"\bmushola\b",
        r"\bgereja\b",
        r"\bvihara\b",
        r"\bpura\b",
        r"\bklenteng\b",
        r"\bkatedral\b",
        r"\bkapel\b"
    ]),

    # =====================================================
    # BANK / KEUANGAN
    # =====================================================
    ("Bank/Keuangan", [
        r"\bbank\b",
        r"\bbri\b",
        r"\bbni\b",
        r"\bbtn\b",
        r"\bmandiri\b",
        r"\bbca\b",
        r"\bcimb\b",
        r"\bpermata\b",
        r"\bpanin\b",
        r"\bdanamon\b",
        r"\bmaybank\b",
        r"\bocbc\b",
        r"\bhsbc\b",

        r"\bpegadaian\b",
        r"\basuransi\b",
        r"\bfinance\b",
        r"\bmulti\s*finance\b",
        r"\bleasing\b",
        r"\bkoperasi\b",
        r"\bsimpan\s*pinjam\b",
        r"\bsekuritas\b",
        r"\binvestasi\b",
        r"\bpembiayaan\b",
        r"\bfintech\b"
    ]),

    # =====================================================
    # LOGISTIK & EKSPEDISI
    # =====================================================
    ("Logistik & Ekspedisi", [
        r"\blogistik\b",
        r"\bekspedisi\b",
        r"\bcargo\b",
        r"\bkurir\b",
        r"\bdelivery\b",
        r"\bshipping\b",
        r"\bfreight\b",
        r"\bforwarder\b",
        r"\btrucking\b",
        r"\btransport\b",
        r"\btransportasi\b",
        r"\bgudang\b",
        r"\bwarehouse\b",
        r"\bdistribution\b",
        r"\bdistribusi\b",

        r"\bjne\b",
        r"\bjnt\b",
        r"\bsicepat\b",
        r"\banteraja\b",
        r"\bpos\s*indonesia\b",
        r"\btiki\b",
        r"\bdhl\b",
        r"\bfedex\b",
        r"\bninja\s*(express|xpress)\b",
        r"\bshopee\s*express\b",
        r"\bspx\b",
        r"\blalamove\b",
        r"\bgrab\s*express\b",
        r"\bgosend\b"
    ]),

    # =====================================================
    # MANUFAKTUR
    # =====================================================
    ("Manufaktur", [
        r"\bpabrik\b",
        r"\bmanufaktur\b",
        r"\bmanufacturing\b",
        r"\bindustri\b",
        r"\bproduksi\b",
        r"\bplant\b",
        r"\bfactory\b",

        # manufaktur BUMN / besar
        r"\bpetrokimia\b",
        r"\bpupuk\b",
        r"\bsemen\b",
        r"\bsteel\b",
        r"\bbaja\b"
    ]),

    # =====================================================
    # RETAIL
    # =====================================================
    ("Retail", [
        r"\bindomaret\b",
        r"\balfamart\b",
        r"\bminimarket\b",
        r"\bhypermart\b",
        r"\bsupermarket\b",
        r"\bdepartment\s*store\b",
        r"\bmart\b"
    ]),

    # =====================================================
    # MALL
    # =====================================================
    ("Mall", [
        r"\bmall\b",
        r"\bplaza\b",
        r"\bshopping\s*center\b",
        r"\bsupermall\b",
        r"\btrade\s*center\b"
    ]),

    # =====================================================
    # PERHOTELAN
    # =====================================================
    ("Perhotelan", [
        r"\bhotel\b",
        r"\bresort\b",
        r"\bguest\s*house\b",
        r"\bpenginapan\b",
        r"\bhostel\b",
        r"\bvilla\b"
    ]),

    # =====================================================
    # PARIWISATA
    # =====================================================
    ("Pariwisata", [
        r"\bwisata\b",
        r"\btour\b",
        r"\btravel\b",
        r"\bpantai\b",
        r"\btaman\b",
        r"\bmuseum\b",
        r"\bkebun\s*binatang\b",
        r"\bzoo\b",
        r"\bwaterpark\b",
        r"\btheme\s*park\b"
    ]),

    # =====================================================
    # PERDAGANGAN UMUM
    # =====================================================
    ("Perdagangan (Umum)", [
        r"\bdistributor\b",
        r"\bsupplier\b",
        r"\bagen\b",
        r"\bgrosir\b",
        r"\bperdagangan\b",
        r"\btrading\b",
        r"\btoko\b"
    ]),

    # =====================================================
    # DEFAULT PERUSAHAAN FORMAL (PT/CV/UD)
    # =====================================================
    ("Perdagangan (Umum)", [
        r"^\s*pt[\.\s]",
        r"^\s*cv[\.\s]",
        r"^\s*ud[\.\s]",
        r"^\s*pd[\.\s]",
        r"\bpt\b",
        r"\bcv\b",
        r"\bud\b",
        r"\bpd\b"
    ]),
]


def classify_segmentasi(nama_perusahaan, keyword=""):
    text = f"{nama_perusahaan} {keyword}".lower().strip()
    text = re.sub(r"\s+", " ", text)

    for segment, patterns in SEGMENT_RULES:
        for pat in patterns:
            if re.search(pat, text):
                return segment

    return "Perdagangan (Umum)"