# -*- coding: utf-8 -*-

import re
import unicodedata
import pdfplumber
import json
from pathlib import Path

import sys


import os

def dbg(msg):
    here = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(here, "parser_debug.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

sys.stdout.reconfigure(encoding='utf-8')



# ==========================================================
#  YARDIMCI FONKSİYONLAR
# ==========================================================
def to_turkish_upper(text):
    if not text:
        return text
    mapping = {
        "i": "İ", "ı": "I", "ğ": "Ğ",
        "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç",
    }
    return "".join(mapping.get(c, c.upper()) for c in text)


def normalize_text(t):
    if not t:
        return ""
    t = unicodedata.normalize("NFKC", t)
    t = t.replace("\u00A0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()

def parse_amount(s):
    # temizle
    s = (s or "").strip()
    if not s:
        return None
    # izin verilenler: digits, dot, comma, minus
    s = re.sub(r"[^\d\-,\.]", "", s)

    # negatif işareti tespit
    neg = False
    if s.startswith("-"):
        neg = True
        s = s[1:]

    # hem nokta hem virgül varsa: hangisi son geçiyorsa o ondalık sayılır
    if "." in s and "," in s:
        if s.rfind(".") > s.rfind(","):
            # nokta ondalık, virgül binlik -> sil virgüller
            s = s.replace(",", "")
        else:
            # virgül ondalık, nokta binlik -> sil noktalar, virgülü noktaya çevir
            s = s.replace(".", "")
            s = s.replace(",", ".")
    else:
        # sadece nokta veya sadece virgül varsa karar:
        if "," in s and "." not in s:
            # virgül tekse ondalık kabul et
            s = s.replace(",", ".")
        # eğer sadece nokta varsa:
        # kontrol et: sondan sonra 1-2 hane varsa ondalık (ör: 6672.8 veya 6.63)
        # aksi halde (ör: 6.631 veya 6631) nokta binlik olabilir -> sil
        elif "." in s and "," not in s:
            after = s.split(".")[-1]
            if len(after) == 3 and all(ch.isdigit() for ch in after):
                # büyük olasılıkla binlik ayraç, kaldır
                s = s.replace(".", "")
            # else nokta zaten ondalık, bırak olduğu gibi

    try:
        val = float(s)
        return -val if neg else val
    except:
        return None


# ==========================================================
#  PDF OKUYUCU
# ==========================================================
def extract_text(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            p = page.extract_text()
            if p:
                text += p + "\n"
    return normalize_text(text)


# ==========================================================
#  BANKA TESPİT
# ==========================================================
def normalize(s):
    s = s.lower()
    tr_map = {
        "ı":"i", "ğ":"g", "ü":"u", "ş":"s",
        "ö":"o", "ç":"c",
        "İ":"i", "Ğ":"g", "Ü":"u", "Ş":"s",
        "Ö":"o", "Ç":"c"
    }
    for k,v in tr_map.items():
        s = s.replace(k, v)
    return s

def banka_tespit(text):
    up = text.upper()

    # İŞ BANKASI — güvenli tespit
    if ("ISBANK.COM.TR" in up
        or "İŞCEP" in up
        or "ISCEP" in up
        or ("E-DEKONT" in up and "ZIRAAT" not in up)
        or re.search(r"REFERANS NUMARASI\s*:\s*\d{2}\.\d{2}\.\d{4}\/\d+", up)
    ):
        return "isbank"


    # DENİZBANK
    if "DENIZBANK" in up or "DENİZBANK" in up or "DENIZ BANK" in up:
        return "denizbank"

    # ENPARA / FİNANSBANK / QNB
    if "ENPARA" in up or "FINANSBANK" in up or "FİNANSBANK" in up or "QNB" in up:
        return "enpara"

    # GARANTİ
    if "GARANTI" in up or "GARANTİ" in up:
        return "garanti"

    # VAKIFBANK
    if "VAKIFBANK" in up or "T. VAKIFLAR BANKASI" in up:
        return "vakif"

    # YAPI KREDİ
    if "YAPI KREDI" in up or "YAPI KREDİ" in up or "YAPI VE KREDI" in up:
        return "yapikredi"

    # ZİRAAT BANKASI
    if "ZIRAAT" in up or "ZİRAAT" in up:
        return "ziraat"

    # HALKBANK — eklenmesi gereken satır
    if "HALKBANK" in up or "HALK BANK" in up or "WWW.HALKBANK" in up:
        return "halkbank"
    
    # ✔ ING BANK (yeni eklenen)
    if (
        "ING BANK" in up
        or "İNG BANK" in up
        or "INGBANK" in up
    ):
        return "ing"
    
    # KUVEYT TÜRK
    if "KUVEYTTURK" in up or "KUVEYT" in up:
        return "kuveytturk"
    
    # VAKIF KATILIM
    if "VAKIF KATILIM" in up or "VAKIF KATILIM BANKASI" in up or "VAKIFKATILIM" in up:
        return "vakifkatilim"
    
    # ⭐ AKBANK — (YENİ EKLEDİK)
    if (
        "AKBANK" in up
        or "AKBANK T.A.Ş" in up
        or "WWW.AKBANK.COM" in up
        or "AKBANK T.A.Ş." in up
        or "GENEL MÜDÜRLÜK: SABANCI CENTER" in up  # çoğu dekontta geçer
        or "VERGİ NO: 0150015264" in up            # Akbank'ın sabit vergi no'su
        or "TR04 0004" in up                      # Akbank IBAN prefix
    ):
        return "akbank"

    


    return "bilinmiyor"









# ==========================================================
#  ENPARA PARSER (stabil – tüm enpara varyantları için)
# ==========================================================
def parse_enpara(text):
    dbg("ENTERED ENPARA PARSER")

    raw = text  # sen 'text' gönderiyorsun, isim tutarlı olsun

    data = {
        "banka": "ENPARA",
        "is_fast": False,
        "is_havale": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": False,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:500]
    }

    up = raw.upper()

    # ---------------------------
    #  TÜRLER
    # ---------------------------
    if "FAST" in up:
        data["is_fast"] = True
    if "EFT" in up:
        data["is_havale"] = True
    if "GIDEN" in up or "GİDEN" in up:
        data["is_giden"] = True
    if "GELEN" in up:
        data["is_gelen"] = True
    if "MAAŞ" in up:
        data["is_maas"] = True

    # ---------------------------
    #  TARİH (boşluk OLMASA bile yakalar)
    # ---------------------------
    date = None

    # 1) "İşlem tarihi ve saati :04.11.2025 12:58"
    p1 = r"[İIıi]şlem\s+tarihi(?:\s+ve\s+saati)?\s*[:]\s*(\d{2}[./]\d{2}[./]\d{4})(?:\s+([0-2]\d:[0-5]\d))?"
    m = re.search(p1, raw, flags=re.IGNORECASE)
    if m:
        date = m.group(1)

    # 2) Başlıktan yakalanmazsa ikinci şans
    if not date:
        m = re.search(r"(\d{2}[./]\d{2}[./]\d{4})\s+([0-2]\d:[0-5]\d)", raw)
        if m:
            date = m.group(1)

    # 3) Son çare: sadece tarihi al
    if not date:
        m = re.search(r"(\d{2}[./]\d{2}[./]\d{4})", raw)
        if m:
            date = m.group(1)

    if date:
        data["islemtarihi"] = date




    # ---------------------------
    #  TUTAR (ENPARA FORMAT: 6,660.00)
    # ---------------------------
    m = re.search(r"TL\s*([\d\.,]+)", raw)
    if m:
        tutar = m.group(1)
        tutar = tutar.replace(",", "").replace(".", "")
        # önce son iki haneyi ayır
        if len(tutar) > 2:
            tutar = tutar[:-2] + "." + tutar[-2:]
        data["tutar"] = parse_amount(tutar)

    # ---------------------------
    #  GÖNDEREN
    # ---------------------------
    m = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw)
    if m:
        data["gonderen"] = m.group(1).split("AÇIKLAMA")[0].strip()

    # ---------------------------
    #  ALICI ÜNVANI
    # ---------------------------
    m = re.search(r"ALICI ÜNVANI\s*:\s*([^\n]+)", raw)
    if m:
        # önce IBAN ile ayrımı yap
        name = m.group(1).split("IBAN")[0].strip()
        # sondaki gereksiz "ALICI" kelimesini (nokta/virgül vb ile birlikte) temizle
        name = re.sub(r'[,\.\s]*\bALICI\b[,\.\s]*$', '', name, flags=re.IGNORECASE).strip()
        data["alici"] = name

    # ---------------------------
    #  ALICI IBAN
    # ---------------------------
    m = re.search(r"ALICI IBAN\s*:\s*(TR[0-9 ]+)", raw)
    if m:
        data["aliciiban"] = m.group(1).replace(" ", "")

    # ---------------------------
    #  GÖNDEREN IBAN (MÜŞTERİ UNVANI SATIRI)
    # ---------------------------
    m = re.search(r"MÜŞTERİ ÜNVANI.*?IBAN\s*:\s*(TR[0-9 ]+)", raw, re.S)
    if m:
        data["gondereniban"] = m.group(1).replace(" ", "")

    if data["is_gelen"]:
        # Şube adı satırını tek satır olarak al
        m = re.search(r"Şube adı\s*:([^\n\r]+)", raw, flags=re.I)
        if m:
            line = m.group(1).strip()

            # İçinden Sayın ... kısmını çek
            m2 = re.search(r"Sayın\s+(.+)", line, flags=re.I)
            if m2:
                data["alici"] = m2.group(1).strip()

        # Gelen işlemde ALICI IBAN yok
        data["aliciiban"] = ""

        # Gönderen IBAN tablo satırından çıkarılır
        m = re.search(r"Vadesiz TL\s+(TR[0-9 ]+)", raw)
        if m:
            data["gondereniban"] = m.group(1).replace(" ", "")
        else:
            # Bazı enpara varyantları 'Günlük hesap' yazıyor
            m = re.search(r"(Vadesiz|Günlük)\s+TL\s+(TR[0-9 ]+)", raw)
            if m:
                data["gondereniban"] = m.group(2).replace(" ", "")


    data["gonderen"] = to_turkish_upper(data["gonderen"])
    data["alici"] = to_turkish_upper(data["alici"])

    dbg("ENPARA PARSER DONE")
    return data







# ==========================================================
# GARANTI — KUSURSUZ UNIVERSAL PARSER (MAAŞ / FAST / HAVALE)
# ==========================================================
def parse_garanti(text):
    import re, unicodedata
    TU = unicodedata.normalize("NFKD", text).upper()
    dbg("TU=" + TU)

    result = {
        "banka": "garanti",
        "_debug": "garanti_universal",
    }

    if not text:
        return result

    # Normalizasyon (boşluklar korunur)
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\u00A0", " ")
    t = re.sub(r"[ \t]+", " ", t).strip()
    TU = t.upper()

    # -----------------------------
    # Yardımcı: isim satırı temizleyici
    # -----------------------------
    def clean_name_line(s):
        if not s:
            return s
        s = s.strip()
        s = re.sub(r"\s+", " ", s)

        s = re.sub(r"\*{2,}\s*/\s*\*{2,}", "", s)
        s = re.sub(r"\*{2,}", "", s)

        # müşteri numarası etiketlerini kaldır
        s = re.sub(r"\bMÜŞTERİ(?:\s*NUMARASI|\s*NO)?\s*[:\-]?\s*\d+\b", "", s, flags=re.I)
        s = re.sub(r"\bMUSTERI(?:\s*NUMARASI|\s*NO)?\s*[:\-]?\s*\d+\b", "", s, flags=re.I)

        # TC / VKN gibi etiketleri kaldır
        s = re.sub(r"\b(TC|TCKN|VKN|SIRA\s*NO|SIRA)\s*[:\-]?\s*[\d\w\-\/]+\b", "", s, flags=re.I)

        # Baştaki */-/rakam karışımı blokları tek seferde sil
        s = re.sub(r"^[\*\s\/\-\d]+", "", s)

        # İçteki hesap formatlarını kaldır
        s = re.sub(r"\b\d{2,6}\s*\/\s*\d{3,10}\b", "", s)

        # Yıldızlı hesap kalıntılarını temizle
        s = re.sub(r"\*{2,}.*?(?=[A-ZÇĞİÖŞÜ])", "", s)

        # Adres kelimeleri görünce kes
        s = re.split(
            r"\b(MAH|MAH\.|SOK|SOK\.|CAD|CAD\.|SK|SK\.|NO:|NO|KAPI|BULVAR|BLV|APT|DAIRE|DAİRE)\b",
            s,
            flags=re.I
        )[0].strip()

        # IBAN kelimesinden sonrası çöp olabilir
        s = re.sub(r"\bIBAN\b.*", "", s, flags=re.I).strip()

        # Makul uzunluk
        parts = s.split()
        if len(parts) > 8:
            s = " ".join(parts[:8])

        return s.strip()

    # Türkçe upper
    def toTU(x):
        return x.replace("i", "İ").upper() if x else x

    # -------------------------------------
    # ORTAK: Üst IBAN (bu her zaman ALICI IBAN’dır)
    # -------------------------------------
    top_iban = None
    m = re.search(r"IBAN\s*[:]?\s*(TR[0-9 ]{20,34})", t)
    if m:
        top_iban = m.group(1).replace(" ", "")

    # İşlem Tarihi
    m = re.search(r"(İŞLEM|ISLEM)\s*TAR(İ|I)H(İ|I)\s*[: ]+(\d{2}[./]\d{2}[./]\d{4})", t, re.I)
    if m:
        result["islemtarihi"] = m.group(4).replace("/", ".")

    # Tutar
    m = re.search(r"TUTAR\s*:?\s*[+\- ]*\s*([\d\.,]+)", t)
    if m:
        raw = m.group(1).replace(".", "").replace(",", ".")
        try:
            result["tutar"] = float(raw)
        except:
            pass

    # SAYIN altı
    sayin = None
    m = re.search(r"SAYIN\s+([^\n\r]+)", t, re.I)
    if m:
        sayin = clean_name_line(m.group(1))

    # -------------------------------------
    # Format tespiti
    # -------------------------------------
    IS_FAST = "FAST" in TU
    IS_HAVALE = "HAVALE" in TU
    IS_MAAS = (
        ("MAAŞ" in TU or "MAAS" in TU)
        and ("KURUM" in TU or "MAAS ÖDEMESİ" in TU or "MAAS ODEMESI" in TU)
    )

    # Güvenli, tek noktadan borçlu/alacaklı tespiti
    HAS_BORCLU = ("BORÇLU" in TU) or ("BORCLU" in TU)
    HAS_ALACAKLI = "ALACAKLI" in TU

    dbg(f"IS_FAST={IS_FAST} IS_HAVALE={IS_HAVALE} IS_MAAS={IS_MAAS} HAS_BORCLU={HAS_BORCLU} HAS_ALACAKLI={HAS_ALACAKLI}")
    if top_iban:
        dbg("TOP_IBAN=" + top_iban)

    # --- Varsayılan gönderici IBAN: top_iban (sadece BORÇLU değilse bırakılacak) ---
    if top_iban and not HAS_BORCLU:
        result["gondereniban"] = top_iban

    # ==========================================================
    # 1) FAST
    # ==========================================================
    if IS_FAST:
        if sayin:
            result["gonderen"] = toTU(sayin)

        # Alıcı
        m = re.search(r"ALACAKLI\s*:\s*([^\n\r]+)", t, re.I)
        if m:
            result["alici"] = toTU(clean_name_line(m.group(1)))

        # Alıcı IBAN
        m = re.search(r"ALACAKLI IBAN\s*:\s*(TR[0-9 ]+)", t)
        if m:
            result["aliciiban"] = m.group(1).replace(" ", "")
        else:
            result["aliciiban"] = top_iban  # fallback

        return result

    # ==========================================================
    # 2) MAAŞ
    # ==========================================================
    if IS_MAAS:
        if sayin:
            result["alici"] = toTU(sayin)

        m = re.search(r"KURUM\s*:\s*([^\n\r]+)", t, re.I)
        if m:
            result["gonderen"] = toTU(clean_name_line(m.group(1)))

        # ALICI IBAN
        m = re.search(r"ALICI\s*IBAN\s*:\s*(TR[0-9 ]+)", t)
        if m:
            result["aliciiban"] = m.group(1).replace(" ", "")
        else:
            result["aliciiban"] = top_iban

        result["gondereniban"] = "" 

        return result

    # ==========================================================
    # 3) HAVALE
    # ==========================================================
    if IS_HAVALE:

        dbg("ENTERED HAVALE BRANCH")

        # ---------------------
        # VARYANT 1: BORÇLU → gönderen
        # ---------------------
        if HAS_BORCLU:
            dbg("BORÇLU BLOĞUNA GİRDİ")

            # GÖNDEREN (borçlu hesap)
            m = re.search(r"BORÇLU HESAP\s*:\s*([^\n\r]+)", t, re.I)
            if not m:
                m = re.search(r"BORCLU HESAP\s*:\s*([^\n\r]+)", t, re.I)
            if m:
                result["gonderen"] = toTU(clean_name_line(m.group(1)))

            # GÖNDEREN IBAN hiçbir zaman doldurulmasın
            dbg("BORÇLU OLDUĞU İÇİN gondereniban = '' (BOŞ BIRAKILDI)")
            result["gondereniban"] = ""

            # ALICI = SAYIN
            if sayin:
                result["alici"] = toTU(sayin)

            # ALICI IBAN = üstteki IBAN
            result["aliciiban"] = top_iban

            return result

        # ---------------------
        # VARYANT 2: ALACAKLI → alıcı
        # ---------------------
        if HAS_ALACAKLI:
            m = re.search(r"ALACAKLI HESAP\s*:\s*([^\n\r]+)", t, re.I)
            if m:
                result["alici"] = toTU(clean_name_line(m.group(1)))

            m = re.search(r"ALACAKLI IBAN\s*:\s*(TR[0-9 ]+)", t)
            if m:
                result["aliciiban"] = m.group(1).replace(" ", "")
            else:
                result["aliciiban"] = top_iban

            if sayin:
                result["gonderen"] = toTU(sayin)

            # gönderen iban fallback (sadece varsa yıldızları temizleyip ata)
            m = re.search(r"BORÇLU IBAN\s*:\s*(TR[0-9 *]+)", t, re.I)
            if m:
                result["gondereniban"] = m.group(1).replace(" ", "").replace("*", "")
            return result

        # ---------------------
        # Genel fallback
        # ---------------------
        if sayin:
            result["alici"] = toTU(sayin)
        result["aliciiban"] = top_iban
        return result

    result["gonderen"] = to_turkish_upper(result.get("gonderen", ""))
    result["alici"] = to_turkish_upper(result.get("alici", ""))

    # FALLBACK
    result["_debug"] += " | fallback"
    return result







def parse_vakifbank(text):
    import re, unicodedata
    t = unicodedata.normalize("NFKC", text)
    TU = t.upper()

    data = {
        "banka": "vakifbank",
        "is_havale": False,
        "is_eft": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": False,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": t[:500]
    }

    # Tür tespiti
    if re.search(r"\bHAVALE\b", TU):
        data["is_havale"] = True
    if re.search(r"\bEFT\b", TU):
        data["is_eft"] = True
    if re.search(r"\bMAAŞ\b|\bMAAS\b|\bMAAŞ ÖDEMESİ\b", TU):
        data["is_maas"] = True
    if re.search(r"\bGELEN\b", TU):
        data["is_gelen"] = True
    if re.search(r"\bGİDEN\b|\bGIDEN\b", TU):
        data["is_giden"] = True

    # -----------------------
    # Tarih
    # -----------------------
    m = re.search(r"İŞLEM(?:\s+TARİHİ|\s+TARİHİ\s+)?\s*[:]*\s*([0-9]{2}[./][0-9]{2}[./][0-9]{4})", t, flags=re.I)
    if m:
        data["islemtarihi"] = m.group(1).replace("/", ".")

    # -----------------------
    # Tutar (ilk bulunan TL değeri, güvenli dönüşüm)
    # -----------------------
    m = re.search(r"İŞLEM\s*TUTARI\s*[:\-]?\s*([0-9\.,]+)\s*TL", t, flags=re.I)
    if not m:
        m = re.search(r"([0-9\.,]+)\s*TL", t, flags=re.I)
    if m:
        raw = m.group(1)
        # 6.631,40 -> 6631.40
        data["tutar"] = parse_amount(raw)

    # -----------------------
    # IBAN'ları topla (metindeki tüm TR... dizileri)
    # -----------------------
    ibans = re.findall(r"(TR[0-9 ]{10,34})", t, flags=re.I)
    ibans = [s.replace(" ", "") for s in ibans]

    # -----------------------
    # Öncelikli: ALICI bloklarından al (örnek: "ALICI HESAP NO", "ALICI AD SOYAD/UNVAN")
    # -----------------------
    alici_name = None
    m = re.search(r"ALICI(?:\s+HESAP\s*NO)?\s*(?:[:\-]|\s)\s*([^\n\r]+)", t, flags=re.I)
    if m:
        # satır bazlı al
        line = m.group(1).strip()
        # temizle (satır içindeki gereksiz parçalar)
        line = re.split(r"\s{2,}|\t", line)[0].strip()
        alici_name = line

    # Eğer ALICI satırında IBAN varsa al
    m = re.search(r"ALICI(?:\s+.*)?\s*IBAN\s*[:\-]?\s*(TR[0-9 ]{10,34})", t, flags=re.I)
    if m:
        data["aliciiban"] = m.group(1).replace(" ", "")

    # -----------------------
    # GÖNDEREN blokları
    # -----------------------
    gonderen_name = None
    m = re.search(r"GONDEREN(?:\s+AD|\s+AD\s+RE)?\s*(?:[:\-]|\s)\s*([^\n\r]+)", t, flags=re.I)
    if m:
        gonderen_name = m.group(1).strip()

    # Eğer "GONDEREN HESAP NO" altındaki satırlarda isim varsa al
    if not gonderen_name:
        m = re.search(r"GONDEREN HESAP NO\s*([^\n\r]+)", t, flags=re.I)
        if m:
            gonderen_name = m.group(1).strip()

    # GÖNDEREN IBAN varsa yakala (özel etiket veya yakın metin)
    m = re.search(r"GONDEREN(?:\s+.*)?\s*IBAN\s*[:\-]?\s*(TR[0-9 ]{10,34})", t, flags=re.I)
    if m:
        data["gondereniban"] = m.group(1).replace(" ", "")

    # -----------------------
    # Tablodan IBAN/isim eşleştirme: satır bazlı arama
    # Örnek satır formatları:
    #   TR06...    ALICI ...    (veya)  Vadesiz TL TR2800... GÖNDEREN AD ...
    # -----------------------
    # Satırları dolaşarak ilk TR'li satırların yanındaki isimleri al
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    for ln in lines:
        # eğer satırda hem IBAN hem isim benzeri varsa
        m = re.search(r"(TR[0-9 ]{10,34})\s+(.+)", ln, flags=re.I)
        if m:
            iban = m.group(1).replace(" ", "")
            rest = m.group(2).strip().rstrip(",")
            # eğer satır içinde "ALICI" geçiyorsa -> alıcıiban
            if re.search(r"\bALICI\b", ln, flags=re.I) or re.search(r"ALICI AD|ALICI HESAP", ln, flags=re.I):
                data["aliciiban"] = iban
                if not data["alici"]:
                    data["alici"] = rest
                continue
            # eğer satır içinde "GONDEREN" veya "GÖNDEREN" geçiyorsa -> göndereniban
            if re.search(r"\bGONDEREN\b|\bGÖNDEREN\b", ln, flags=re.I):
                data["gondereniban"] = iban
                if not data["gonderen"]:
                    data["gonderen"] = rest
                continue
            # Eğer daha önce aliciiban yok, ilk TR satırı büyük olasılıkla aliciiban
            if not data["aliciiban"]:
                data["aliciiban"] = iban
                # rest kısmı bazen alıcı adını içerir (ör: ALICI AD SOYAD/UNVAN ECE BİÇER)
                if not data["alici"]:
                    # strip sayfa/etiket kalıntılarını
                    candidate = re.split(r"\s{2,}|,|/|HESAP|ALICI|GONDEREN", rest, flags=re.I)[0].strip()
                    if candidate:
                        data["alici"] = candidate
                continue
            # Eğer aliciiban dolu ama göndereniban boş, ikinci TR değeri genelde göndereniban
            if data["aliciiban"] and not data["gondereniban"]:
                data["gondereniban"] = iban
                if not data["gonderen"]:
                    candidate = re.split(r"\s{2,}|,|/|HESAP|ALICI|GONDEREN", rest, flags=re.I)[0].strip()
                    if candidate:
                        data["gonderen"] = candidate
                continue

    # -----------------------
    # Eğer hâlâ IBAN eksik ise fallback: ibans listesine göre
    # -----------------------
    if not data["aliciiban"] and len(ibans) >= 1:
        data["aliciiban"] = ibans[0]
    if not data["gondereniban"] and len(ibans) >= 2:
        data["gondereniban"] = ibans[1]

    # -----------------------
    # İsim temizlemeleri (satır bazlı ek kontroller)
    # -----------------------
    # örnek: "ALICI AD SOYAD/UNVAN ŞEHRİ ECE BİÇER" -> after the token parts
    if not data["alici"]:
        m = re.search(r"ALICI(?:\s+AD\s+SOYAD\/UNVAN)?\s*[^\n\r]*\s*([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ\s]+[A-ZÇĞİÖŞÜ])", TU)
        if m:
            data["alici"] = m.group(1).strip()

    if not data["gonderen"]:
        # try to capture lines following "GONDEREN" or content nearby IBAN
        m = re.search(r"GONDEREN(?:\s+AD)?\s*[:\-]?\s*([^\n\r]+)", t, flags=re.I)
        if m:
            data["gonderen"] = m.group(1).strip()

    # Satır sonu/başlık kalıntılarını temizle
    for k in ("gonderen", "alici"):
        if isinstance(data[k], str):
            data[k] = re.sub(r"\s{2,}", " ", data[k]).strip()
            # temizle olası etiket soneklerini
            data[k] = re.sub(r"\b(TC KİMLİK|TC KİMLİK NUMARASI|TC KIMLIK|SICIL NUMARASI|SİCİL|SICIL)\b.*$", "", data[k], flags=re.I).strip()
            data[k] = re.sub(r"[,:;\/]+$", "", data[k]).strip()

    # -----------------------
    # Gelen işlemler için mantık: gelen ise alici muhtemelen dekontta senin adın (MÜŞTERİ)
    # Eğer "GELEN" mevcutsa ve müşteri etiketi varsa alıcıyı müşteri unvanından al
    # -----------------------
    if data["is_gelen"]:
        # Müşteri unvanı satırından alıcıyı al (ör: "MÜŞTERİ ÜNVANI: DOĞUŞ EFE BAHCEÇİ")
        m = re.search(r"MÜŞTERİ\s+ÜNVANI\s*[:\-]?\s*([^\n\r]+)", t, flags=re.I)
        if m:
            data["alici"] = m.group(1).strip()
        # Gelenlerde aliciiban genelde boş (banka sadece hesap numara gösteriyor) — eğer IBAN dekontta yok ise boş bırak
        # Ancak göndereniban tablo satırından aldıksa onu koru (aksi halde boş bırak)
        # Eğer gönderici IBAN hala boş, tablo satırındaki TR preceding isimden çekmeye çalış
        if not data["gondereniban"]:
            # örnek satır: "Vadesiz TL TR280015700000000158798217 CORE BİNA..."
            m = re.search(r"(Vadesiz|Günlük|VADESİZ|VADEZİZ)\s+TL\s+(TR[0-9 ]{10,34})", t, flags=re.I)
            if m:
                data["gondereniban"] = m.group(2).replace(" ", "")


    # --------------------------------------------------
    # VAKIFBANK ESKİ HAVALe FORMATINI ÖZEL YAKALAMA
    # Alıcı = "ALICI AD ... " satırı
    # Alıcı IBAN = Üstteki TR satırı + altındaki sayısal kuyruk
    # Gönderen = GONDEREN AD + GONDEREN HESAP NO bloklarından isim birleştirme
    # Maskeli IBAN varsa göndereniban boş
    # --------------------------------------------------

    # 1) Alıcı adı
    m = re.search(r"ALICI AD SOYAD/UNVAN\s+([A-ZÇĞİÖŞÜa-zçğıöşü\s]+)", t, flags=re.I)
    if m:
        data["alici"] = m.group(1).strip()

    # 2) Alıcı IBAN (iki satır birleşmiş)
    iban_top = None
    iban_bottom = None

    m_top = re.search(r"^(TR[0-9 ]{10,34})\s*$", t, flags=re.M)
    m_bottom = re.search(r"^\s*([0-9]{2,}\s*[0-9]{2,})\s*$", t, flags=re.M)

    if m_top and m_bottom:
        iban_top = m_top.group(1).replace(" ", "")
        iban_bottom = m_bottom.group(1).replace(" ", "")
        data["aliciiban"] = (iban_top + iban_bottom).strip()

    # --------------------------
    # GÖNDEREN (tek satır, sade)
    # --------------------------
    gonderen = ""
    lines = [ln.strip() for ln in t.splitlines()]

    for i, ln in enumerate(lines):
        # maskeli IBAN satırını bul
        if re.search(r"TR[0-9 ]*\*+", ln):
            if i > 0:
                prev = lines[i-1].strip()
                # Eğer önceki satır tamamen rakam / IBAN değilse gönderendir
                if re.search(r"[A-Za-zÇĞİÖŞÜçğışöüİ]", prev):
                    gonderen = prev
            break

    data["gonderen"] = gonderen
    data["gondereniban"] = ""  # maskeli olduğu için her zaman boş

    # 4) Gönderen IBAN: maskeli ise boş bırak
    if re.search(r"TR[0-9 ]+\*{2,}", t):
        data["gondereniban"] = ""



    # ------------------------------
    # VAKIFBANK FORMAT TÜR 2:
    # TRxx ... 7361 → alt satır → ADSOYAD/UNVAN → isim → bir alt satır → ek hesap numarası
    # ------------------------------
    # ----------------------------------------------------
    # VAKIFBANK FORMAT TÜR 2 (İNCİ HOLDİNG AŞ olan)
    # ----------------------------------------------------
    if data["gonderen"] == "" and data["gondereniban"] == "":
        lines = [l.strip() for l in t.splitlines()]

        for i, ln in enumerate(lines):
            # IBAN ilk satır (maskesiz)
            if re.match(r"^TR\d[\d ]+$", ln):
                iban_part1 = ln.replace(" ", "")
                name = ""
                iban_part2 = ""

                # Bir alt satır ADSOYAD/UNVAN içerir → isim buradadır
                if i+1 < len(lines) and "ADSOYAD" in lines[i+1].upper():
                    raw_name_line = lines[i+1]

                    # Etiketleri temizle → sadece ismi bırak
                    name = re.sub(
                        r"HESAP NUMARASI|ADSOYAD/UNVAN1|ADSOYAD|UNVAN1",
                        "",
                        raw_name_line,
                        flags=re.I,
                    ).strip()

                # İBAN ikinci parça (sadece rakam)
                if i+2 < len(lines):
                    if re.fullmatch(r"[0-9 ]+", lines[i+2]):
                        iban_part2 = lines[i+2].replace(" ", "")

                full_iban = iban_part1 + iban_part2

                data["gonderen"] = name
                data["gondereniban"] = full_iban
                data["alici"] = ""
                data["aliciiban"] = ""
                break



    # -----------------------
    # Son temiz: Türkçe büyük harf dönüşümü (kullanıcı dosyasında to_turkish_upper varsa onu kullan)
    # -----------------------
    try:
        # tercih: global fonksiyon to_turkish_upper
        data["gonderen"] = to_turkish_upper(data["gonderen"])
        data["alici"] = to_turkish_upper(data["alici"])
    except Exception:
        # fallback kaba upper
        data["gonderen"] = (data["gonderen"] or "").upper()
        data["alici"] = (data["alici"] or "").upper()

    return data







def parse_yapikredi(text):
    import re

    def to_turkish_upper(s):
        up = (
            s.replace("i", "İ")
             .replace("ı", "I")
             .upper()
        )
        return up


    raw = text
    up = raw.upper()

    print(repr(up[:200]))

    data = {
        "banka": "yapikredi",
        "is_havale": False,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": False,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:500],
    }

    # ----------------------------------------------------
    # 1) FORMAT TESPİTİ
    # ----------------------------------------------------
    is_format_maas = ("MAAŞ ALACAK DEKONTU" in up) or ("ÖDEME YAPAN İSİM" in up)
    
    is_format_fast = False
    if "FAST GÖNDERİMİ" in up or "GİDEN FAST" in up:
        is_format_fast = True
        data["is_fast"] = True
        data["is_giden"] = True

    


    # ----------------------------------------------------
    # 2) FORMAT 1 — MAAŞ ALACAK DEKONTU (GELEN İŞLEM)
    # ----------------------------------------------------
    if is_format_maas:

        # Gönderen (ÖDEME YAPAN)
        m = re.search(r"ÖDEME YAPAN İSİM\/ÜNVAN\s*:\s*([^\n]+)", raw)
        if m:
            data["gonderen"] = to_turkish_upper(m.group(1).strip())

        # Gönderen IBAN
        m = re.search(r"IBAN NO\s*:\s*(TR[0-9 ]+)", raw)
        if m:
            data["gondereniban"] = m.group(1).replace(" ", "")

        # Tutar
        m = re.search(r"TUTAR\s*:\s*([\d\.,]+)", raw)
        if m:
            data["tutar"] = parse_amount(m.group(1))

        # Tarih
        m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}\.\d{2}\.\d{4})", raw)
        if m:
            data["islemtarihi"] = m.group(1)

        # ALICI — AÇIKLAMA satırından çek ("/" sonrası gerçek isim)
        # ALICI — Çok satırlı AÇIKLAMA yapısı için
        alici_candidate = ""

        # 1) AÇIKLAMA satırının index'ini bul
        lines = raw.splitlines()
        for i, ln in enumerate(lines):
            if ln.strip().upper().startswith("AÇIKLAMA"):
                # 2) Bu satırı ve bir ALT satırı birleştir
                merged = ln
                if i + 1 < len(lines):
                    merged += " " + lines[i+1]

                # 3) "/" sonrası ismi al
                if "/" in merged:
                    part = merged.split("/")[-1].strip()

                    # 4) Ticari bilgilerden kes
                    part = re.split(r"TİCARİ|UNVAN|VD|VERGİ|BANKASI|A\.Ş", part, flags=re.I)[0].strip()

                    # 5) gerçekten isim mi?
                    if re.search(r"[A-Za-zÇĞİÖŞÜçğışöüİ]", part):
                        alici_candidate = part
                break

        if alici_candidate:
            data["alici"] = to_turkish_upper(alici_candidate)


        data["is_maas"] = True
        data["is_gelen"] = True
        return data

    # ----------------------------------------------------
    # 3) FORMAT 2 — FAST / EFT / GİDEN İŞLEM
    # ----------------------------------------------------
    if is_format_fast:
        # İşlem tarihi
        m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
        if m:
            data["islemtarihi"] = m.group(1)

        # Tutar
        m = re.search(r"TOPLAM TAHSİLAT TUTARI\s*:\s*-?([\d\.,]+)", raw, re.I)
        if m:
            data["tutar"] = parse_amount(m.group(1))

        # Gönderen IBAN (sadece IBAN'ın kendisini al)
        m = re.search(r"IBAN *: *(TR[0-9 ]{10,})", raw)
        if m:
            data["gondereniban"] = m.group(1).replace(" ", "")

        # Gönderen ad (ilk ':' işaretine kadar olan isim)
        m = re.search(r"GÖNDEREN ADI *: *([^\n]+)", raw, re.I)
        if m:
            name = m.group(1)
            name = name.split("ÖDEMENİN")[0]
            name = name.split("KAYNAĞI")[0]
            name = name.strip()
            data["gonderen"] = to_turkish_upper(name)

        # Alıcı IBAN
        m = re.search(r"ALICI HESAP *: *(TR[0-9 ]+)", raw, re.I)
        if m:
            data["aliciiban"] = m.group(1).replace(" ", "")

        # Alıcı ad
        m = re.search(r"ALICI ADI *: *([^\n]+)", raw, re.I)
        if m:
            data["alici"] = to_turkish_upper(m.group(1).strip())

        return data

    # ----------------------------------------------------
    # FORMAT TESPİT EDİLEMEDİ — boş bırak ama crash etme
    # ----------------------------------------------------
    return data






def parse_ziraat(text):
    raw = text
    up = raw.upper()

    data = {
        "banka": "ziraat",
        "is_havale": False,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": False,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:500]
    }

    #--------------------------
    # TÜR TESPİTİ
    #--------------------------
    is_fast = "HESAPTAN FAST" in up or "FAST" in up
    is_havale = "HESAPTAN HESABA HAVALE" in up or "HAVALE TUTARI" in up

    if is_fast:
        data["is_fast"] = True
        data["is_giden"] = True

    if is_havale:
        data["is_havale"] = True
        data["is_giden"] = True

    #--------------------------
    # TARİH
    #--------------------------
    m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}[./]\d{2}[./]\d{4})", raw, re.I)
    if m:
        data["islemtarihi"] = m.group(1)

    #--------------------------
    # TUTAR
    #--------------------------
    if is_havale:
        m = re.search(r"Havale Tutarı\s*:\s*([\d\.,]+)", raw, re.I)
    else:
        m = re.search(r"İşlem Tutarı\s*:\s*([\d\.,]+)", raw, re.I)

    if m:
        data["tutar"] = parse_amount(m.group(1))

    #--------------------------
    # GÖNDEREN (HAVALE) — IBAN sağındaki satırdan alınır
    #--------------------------
    if is_havale:
        data["gondereniban"] = ""  # havale için boş kalacak

        lines = [ln.rstrip() for ln in raw.splitlines()]

        # Göndereni bulacağımız tek satır:
        # "ŞUBE KODU/ADI : ... YKS YANGIN ..."
        sender = ""
        for ln in lines:
            up_ln = ln.upper()
            if "ŞUBE KODU/ADI" in up_ln:
                # sağ tarafı al
                right = ln.split(":", 1)[1].strip() if ":" in ln else ln.strip()
                # sondaki isim: şube açıklamalarını at → firmayı al
                # 1204/KAHRAMANLAR/İZMİR ŞUBESİ  YKS YANGIN YKS YANGIN KORUMA SİSTEMLERİ
                # mantık: "ŞUBESİ" kelimesinden SONRASINI al
                if "ŞUBESİ" in right.upper():
                    sender = right.upper().split("ŞUBESİ", 1)[1].strip()
                else:
                    # fallback: tüm kelimeler içinde en uzun isim bloğunu seç
                    parts = right.split()
                    sender = " ".join(parts[-4:])  # nadiren gerekir
                break
        
        data["gonderen"] = to_turkish_upper(sender)

        # 3) HAVALEDE gönderen IBAN boş kalacak
        data["gondereniban"] = ""

    
    # FAST GÖNDEREN IBAN (sadece ilk 26 hane)
    # --------------------------
    if is_fast:
        m = re.search(r"IBAN\s*:\s*(TR[0-9 ]{24,34})", raw, re.I)
        if m:
            iban_raw = m.group(1)
            # Sadece IBAN kısmını al (26 karakter)
            iban_clean = iban_raw.replace(" ", "")
            data["gondereniban"] = iban_clean[:28]  # TR + 2 digit + 22 digit = 26-28 arası




    #--------------------------
    # GÖNDEREN AD (FAST)
    #--------------------------
    if is_fast:
        m = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw, re.I)
        if m:
            data["gonderen"] = to_turkish_upper(m.group(1).strip())

    #--------------------------
    # ALICI AD
    #--------------------------
    if is_havale:
        m = re.search(r"Alacaklı Adı Soyadı\s*:\s*([^\n]+)", raw, re.I)
        if m:
            data["alici"] = to_turkish_upper(m.group(1).strip())

    if is_fast:
        m = re.search(r"Alıcı\s*:\s*([^\n]+)", raw, re.I)
        if m:
            data["alici"] = to_turkish_upper(m.group(1).strip())

    #--------------------------
    # ALICI IBAN
    #--------------------------
    if is_havale:
        m = re.search(r"Alacaklı IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
        if m:
            data["aliciiban"] = m.group(1).replace(" ", "")

    if is_fast:
        m = re.search(r"Alıcı Hesap\s*:\s*(TR[0-9 ]+)", raw, re.I)
        if m:
            data["aliciiban"] = m.group(1).replace(" ", "")

    return data





def parse_akbank(text):
    import re
    raw = text
    up = raw.upper()

    data = {
        "banka": "akbank",
        "is_havale": False,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": True,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:800]
    }

    # maaş tespiti
    if "MAAŞ ÖDEMESİ" in up or "MAAS ODEMESI" in up:
        data["is_maas"] = True

    # tarih
    m = re.search(r"İşlem Tarihi/Saati\s*:\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
    if m:
        data["islemtarihi"] = m.group(1)

    # tutar
    m = re.search(r"TOPLAM\s*([\d\.,]+)\s*TL", raw, re.I)
    if m:
        data["tutar"] = parse_amount(m.group(1))

    # --- İSİM ALGORİTMASI ---
    lines = raw.split("\n")

    for i, ln in enumerate(lines):
        if "Adı Soyadı/Unvan" in ln or "Adi Soyadi/Unvan" in ln:
            # Bir satırda iki tane geçebilir → ayır
            parts = re.split(r"Adı Soyadı/Unvan\s*:", ln, flags=re.I)
            parts = [p.strip() for p in parts if p.strip()]

            if len(parts) == 1:
                # sadece gönderen var
                data["gonderen"] = to_turkish_upper(parts[0])

                # alt satır “ÜRÜNLERİ LTD.Ş” ise ekle
                if i+1 < len(lines):
                    nxt = lines[i+1].strip()
                    if nxt and not nxt.startswith(("Adres", "TR", "ÜRN", "Hesap", "Borçlu", "Alacaklı", "Müşteri")):
                        data["gonderen"] = to_turkish_upper(parts[0] + " " + nxt)

            elif len(parts) == 2:
                # 1. gönderen, 2. alıcı
                sender = parts[0]
                receiver = parts[1]

                # sender alt satırı
                if i+1 < len(lines):
                    nxt = lines[i+1].strip()
                    if nxt and not nxt.startswith(("Adres", "TR", "ÜRN", "Hesap", "Borçlu", "Alacaklı", "Müşteri")):
                        sender = sender + " " + nxt

                data["gonderen"] = to_turkish_upper(sender)
                data["alici"] = to_turkish_upper(receiver)

    # --- IBAN yakalama ---
    raw2 = raw.replace("\n", " ")
    ibans = re.findall(r"(TR[0-9][0-9\s]{20,34})", raw2, flags=re.I)
    ibans = [re.sub(r"\s+", "", x) for x in ibans]

    if len(ibans) >= 1:
        data["gondereniban"] = ibans[0]
    if len(ibans) >= 2:
        data["aliciiban"] = ibans[1]

    return data







def parse_denizbank(text):
    import re

    raw = text
    up = raw.upper()

    data = {
        "banka": "denizbank",
        "is_havale": False,
        "is_eft": False,
        "is_fast": True,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": True,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:800]
    }

    # ------------------------------------
    # DENİZBANK GÖNDEREN
    # ------------------------------------
    sender = ""
    lines = raw.split("\n")

    STOP_WORDS = [
        "İŞLEM", "TÜRÜ", "GIDEN", "GİDEN", "TARİH", "TARIHI",
        "FAST", "MASRAF", "IBAN", "VKN", "TUTAR", "VALÖR",
        "VALOR", "AÇIKLAMA", "TCKN"
    ]

    for i, line in enumerate(lines):
        if "Adı Soyadı" in line or "ADI SOYADI" in line.upper():

            right = line.split("Adı Soyadı")[-1].strip()
            if not right:
                right = line.split("ADI SOYADI")[-1].strip()

            parts = []

            # ilk satırdan temiz isim çıkar
            cleaned = []
            for token in right.split():
                if token.upper() not in STOP_WORDS:
                    cleaned.append(token)
            if cleaned:
                parts.append(" ".join(cleaned))

            # alt satırlara in (maks 3 satır)
            for j in range(i+1, min(i+4, len(lines))):
                ln = lines[j].strip().split()

                good_tokens = []
                for t in ln:
                    T = t.upper()
                    if T not in STOP_WORDS and re.match(r"^[A-ZÇĞİÖŞÜ]+$", T):
                        good_tokens.append(t)

                if good_tokens:
                    parts.append(" ".join(good_tokens))
                else:
                    break

            sender = " ".join(parts)
            break

    data["gonderen"] = to_turkish_upper(sender.strip())

    # ---------------------------------------------------------
    # GÖNDEREN IBAN (ilk IBAN)
    # ---------------------------------------------------------
    ibans = re.findall(r"(TR[0-9][0-9\s]{20,40})", raw, re.I)
    ibans = [re.sub(r"\s+", "", x) for x in ibans]

    if len(ibans) >= 1:
        data["gondereniban"] = ibans[0]
    if len(ibans) >= 2:
        data["aliciiban"] = ibans[1]

    # ---------------------------------------------------------
    # ALICI ADI
    # ---------------------------------------------------------
    m = re.search(r"Alıcı Adı Soyadı\s+(.+?)\n", raw, re.I)
    if m:
        data["alici"] = m.group(1).strip().upper()

    # ---------------------------------------------------------
    # TUTAR
    # ---------------------------------------------------------
    m = re.search(r"Tutar\s+([\d\.,]+)\s*TL", raw, re.I)
    if m:
        data["tutar"] = parse_amount(m.group(1))

    # ---------------------------------------------------------
    # TARİH
    # ---------------------------------------------------------
    m = re.search(r"İşlem Tarihi\s+(\d{2}\.\d{2}\.\d{4})", raw, re.I)
    if m:
        data["islemtarihi"] = m.group(1)

    # ---------------------------------------------------------
    # Maaş Ödemesi Tespiti
    # ---------------------------------------------------------
    if "STAJ" in up or "MAAŞ" in up or "MAAS" in up:
        data["is_maas"] = True

    return data





def parse_halkbank(text):
    raw = text
    up = raw.upper()

    data = {
        "banka": "halkbank",
        "is_havale": False,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": False,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:500],
    }

    # --------------------------
    # TÜRLER
    # --------------------------
    if "FAST" in up:
        data["is_fast"] = True
        data["is_giden"] = True

    if "PARA TRANSFERİ" in up or "HAVALE" in up:
        data["is_havale"] = True
        data["is_giden"] = True

    # --------------------------
    # TARİH
    # --------------------------
    m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}/\d{2}/\d{4})", raw)
    if m:
        data["islemtarihi"] = m.group(1).replace("/", ".")

    # --------------------------
    # TUTAR
    # --------------------------
    m = re.search(r"İŞLEM TUTARI\s*\(TL\)\s*:\s*([\d\.,]+)", raw, re.I)
    if m:
        data["tutar"] = parse_amount(m.group(1))

    # --------------------------
    # GÖNDEREN
    # --------------------------
    m = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw)
    if m:
        data["gonderen"] = to_turkish_upper(m.group(1).strip())

    # --------------------------
    # GÖNDEREN IBAN
    # --------------------------
    m = re.search(r"GÖNDEREN IBAN\s*:\s*(TR[0-9 ]+)", raw)
    if m:
        data["gondereniban"] = m.group(1).replace(" ", "")

    # --------------------------
    # ALICI
    # --------------------------
    m = re.search(r"ALICI\s*:\s*([^\n]+)", raw)
    if m:
        data["alici"] = to_turkish_upper(m.group(1).strip())

    # --------------------------
    # ALICI IBAN
    # --------------------------
    m = re.search(r"ALICI IBAN\s*:\s*(TR[0-9 ]+)", raw)
    if m:
        data["aliciiban"] = m.group(1).replace(" ", "")

    return data





def parse_ing(text):
    raw = text
    up = raw.upper()

    data = {
        "banka": "ing",
        "is_havale": False,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": True,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:500]
    }

    # MAAŞ
    if "MAAŞ" in up or "MAAS" in up:
        data["is_maas"] = True

    # TARİH
    m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}[./]\d{2}[./]\d{4})", raw, re.I)
    if m:
        data["islemtarihi"] = m.group(1)

    # TUTAR
    m = re.search(r"İŞLEM TUTARI\s*:\s*([\d\.,]+)", raw, re.I)
    if m:
        data["tutar"] = parse_amount(m.group(1))

    # ALICI (SAYIN …)
    m = re.search(r"SAYIN\s+([A-ZÇĞİÖŞÜa-zçğıöşü ]+)", raw, re.I)
    if m:
        data["alici"] = to_turkish_upper(m.group(1).strip())

    # ALICI IBAN
    m = re.search(r"IBAN:\s*(TR[0-9 ]+)", raw, re.I)
    if m:
        data["aliciiban"] = m.group(1).replace(" ", "")

    # Gönderen yok → boş kalsın
    data["gonderen"] = ""
    data["gondereniban"] = ""

    return data






def parse_isbank(text):
    raw = text
    up = raw.upper()

    data = {
        "banka": "isbankasi",
        "is_havale": False,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": True,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": "",
        "islemtarihi": "",
        "_debug_raw": raw[:500]
    }

    # FAST TESPİTİ
    if "FAST" in up:
        data["is_fast"] = True

    # TARİH
    m = re.search(r"İşlem Zam\./Valör\s*:\s*(\d{2}[./]\d{2}[./]\d{4})", raw, re.I)
    if m:
        data["islemtarihi"] = m.group(1)

    # -------------------------------
    # GÖNDEREN AL
    # -------------------------------

    # 1) Tek satırda olan versiyon
    m = re.search(
        r"\n([A-ZÇĞİÖŞÜ0-9 .\-]+?)\s+İŞLEM YERİ",
        text,
        re.IGNORECASE
    )
    if m:
        data["gonderen"] = m.group(1).strip()
    else:
        # 2) İki satıra düşmüş versiyon
        m2 = re.search(
            r"\n([A-ZÇĞİÖŞÜ0-9 .\-]+)\nİŞLEM YERİ",
            text,
            re.IGNORECASE
        )
        data["gonderen"] = m2.group(1).strip() if m2 else ""



    # GÖNDEREN IBAN
    m = re.search(r"IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
    if m:
        data["gondereniban"] = m.group(1).replace(" ", "")

    # ALICI
    m = re.search(r"Alıcı\s+Isim\\?Unvan\s*:\s*([^\n]+)", raw, re.I)
    if m:
        data["alici"] = to_turkish_upper(m.group(1).strip())

    # ALICI IBAN
    m = re.search(r"Alıcı IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
    if m:
        data["aliciiban"] = m.group(1).replace(" ", "")

    # TUTAR
    m = re.search(r"İşlem Tutarı\s*:\s*([\d\.,]+)", raw, re.I)
    if m:
        data["tutar"] = parse_amount(m.group(1))

    return data






def parse_kuveytturk(text):
    data = {
        "banka": "kuveytturk",
        "is_havale": False,
        "is_eft": False,
        "is_fast": True,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": True,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": 0,
        "islemtarihi": ""
    }

    # --- Gönderen ---
    # Metin tamamen birleşik olduğu için tüm şirket adı tek blok:
    m = re.search(r"GönderenK[iı]şi\n?([A-ZÇĞİÖŞÜ0-9]+.+?)\nAlici", text, re.IGNORECASE)
    if m:
        data["gonderen"] = m.group(1).replace("\n", "").strip()
    else:
        # Alternatif
        m2 = re.search(r"GönderenK[iı]şi\s*([\s\S]+?)\nAlici", text, re.IGNORECASE)
        if m2:
            name = m2.group(1).strip()
            name = name.replace("\n", "")
            name = re.sub(r"[^A-ZÇĞİÖŞÜ0-9 ]", " ", name)
            data["gonderen"] = name

    # --- Alıcı ---
    m = re.search(r"Alici\s*([\s\S]+?)\nGönderilenIBAN", text, re.IGNORECASE)
    if m:
        data["alici"] = m.group(1).strip()
    data["alici"] = to_turkish_upper(data["alici"])

    # --- Alıcı IBAN ---
    m = re.search(r"GönderilenIBAN\s*(TR[0-9 ]+)", text, re.IGNORECASE)
    if m:
        data["aliciiban"] = m.group(1).replace(" ", "").strip()

    # --- Tutar ---
    m = re.search(r"Tutar\s*([\d\.,]+)", text, re.IGNORECASE)
    if m:
        data["tutar"] = float(m.group(1).replace(".", "").replace(",", "."))

    # --- İşlem Tarihi ---
    m = re.search(r"İşlemTarihi\s*([0-9\.]+)", text, re.IGNORECASE)
    if m:
        t = m.group(1).strip()
        # Formatı düzelt
        if "." not in t and len(t) == 10:
            t = f"{t[0:2]}.{t[2:4]}.{t[4:]}"
        data["islemtarihi"] = t

    return data






def parse_vakifkatilim(text):
    raw = text  # <-- EKLENDİ

    data = {
        "banka": "vakifkatilim",
        "is_havale": True,
        "is_eft": False,
        "is_fast": False,
        "is_maas": False,
        "is_gelen": False,
        "is_giden": True,
        "gonderen": "",
        "gondereniban": "",
        "alici": "",
        "aliciiban": "",
        "tutar": 0,
        "islemtarihi": ""
    }

    # -------------------------
    # Temizleyici
    # -------------------------
    def clean_name(s):
        if not s:
            return s
        s = s.strip()

        # sondaki garip karakterleri sil
        s = re.sub(r"[^\wÇÖŞİĞÜçöşığü\s\.]+$", "", s)

        # tek harflik kırpıntıyı sil (örn: 'G')
        s = re.sub(r"\b[A-ZÇÖŞİĞÜ]{1}$", "", s).strip()

        return s

    # -------------------------
    # GÖNDEREN
    # -------------------------
    m = re.search(r"Gönderen Kişi\s*:\s*([^\n]+)", raw, re.I)
    if m:
        data["gonderen"] = clean_name(to_turkish_upper(m.group(1).strip()))

    # -------------------------
    # ALICI
    # -------------------------
    m = re.search(r"Gönderilen Kişi\s*:\s*([^\n]+)", raw, re.I)
    if m:
        data["alici"] = clean_name(to_turkish_upper(m.group(1).strip()))

    # -------------------------
    # IBANLAR (bu dekontta yok)
    # -------------------------
    data["gondereniban"] = ""
    data["aliciiban"] = ""

    # -------------------------
    # TUTAR
    # -------------------------
    m = re.search(r"Tutar\s*([\d\.,]+)\s*TL", raw)
    if m:
        data["tutar"] = float(m.group(1).replace(".", "").replace(",", "."))

    # -------------------------
    # TARİH
    # -------------------------
    m = re.search(r"İşlem\s*Tarihi\s*:?\s*([0-9\/\.:\s]+)", raw)
    if not m:
        m = re.search(r"İşlem\s*:\s*([0-9\/\.]+)", raw)

    if m:
        tarih_raw = m.group(1).strip()
        tarih_raw = tarih_raw.split()[0]  # saat varsa kopart
        tarih_raw = tarih_raw.replace("/", ".")
        data["islemtarihi"] = tarih_raw

    return data













# ==========================================================
#  ANA PARSER YÖNLENDİRİCİ
# ==========================================================
def parse_dekont(filepath):
    text = extract_text(filepath)
    banka = banka_tespit(text)

    parsers = {
        "garanti": parse_garanti,
        "enpara": parse_enpara,
        "vakif": parse_vakifbank,
        "yapikredi": parse_yapikredi,
        "ziraat": parse_ziraat,
        "akbank": parse_akbank,
        "denizbank": parse_denizbank,
        "halkbank": parse_halkbank,
        "ing":parse_ing,
        "isbank": parse_isbank,
        "kuveytturk": parse_kuveytturk,
        "vakifkatilim": parse_vakifkatilim,

    }

    parser = parsers.get(banka)
    if parser:
        result = parser(text)
    else:
        result = {"banka": "bilinmiyor", "_debug": "no_match", "raw": text[:200]}

    # TEST ETİKETİ (HER ZAMAN JSON DOLU OLSUN)
    result["_test"] = "OK"
    result["_pdf_length"] = len(text)

    return result


# ==========================================================
#  MAIN (SADECE BURADA PRINT VAR → PHP UYUMLU)
# ==========================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Kullanım: python parser.py <pdf_yolu>")
        sys.exit(1)

    fp = Path(sys.argv[1])
    if not fp.exists():
        print(json.dumps({"hata": "Dosya bulunamadı"}, ensure_ascii=False))
        sys.exit(1)

    res = parse_dekont(fp)
    print(json.dumps(res, ensure_ascii=False))
