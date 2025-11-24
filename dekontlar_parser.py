import re
import sys
import io
import fitz  # PyMuPDF
import json
from pathlib import Path
import unicodedata
import os

# Konsol çıktısı UTF-8 destekli olsun (Windows için)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def to_turkish_upper(text):
    """Türkçe karakterleri koruyarak tamamen büyük harfe çevirir."""
    if not text:
        return text

    replace_map = {
        "i": "İ",
        "ı": "I",
        "ğ": "Ğ",
        "ü": "Ü",
        "ş": "Ş",
        "ö": "Ö",
        "ç": "Ç",
    }

    text = "".join(replace_map.get(c, c.upper()) for c in text)
    return text


# ==========================================================
# 0️⃣ METİN ÇIKARMA FONKSİYONU
# ==========================================================
def extract_text(filepath):
    """PyMuPDF (fitz) ile PDF'ten metin çıkarır."""
    text = ""
    with fitz.open(filepath) as doc:
        for page in doc:
            text += page.get_text("text")
    return text




# ==========================================================
# 1️⃣ DENİZBANK
# ==========================================================
def parse_denisbank(text):
    result = {"banka": "Denizbank"}

    # Görünmeyen karakterleri temizle, normalize et
    text_compact = re.sub(r"\s+", " ", text)

    # Gönderen adı
    m = re.search(r"Ad[ıi]\s*Soyad[ıi]\s+(.+?)\s+(?:VKN|VKN\s*/\s*TCKN)", text_compact, re.S | re.I)
    if m:
        result["gonderen"] = re.sub(r"\s+", " ", m.group(1).strip())

    # Gönderen IBAN
    m = re.search(r"IBAN\s+(TR[0-9 ]{20,})", text_compact, re.I)
    if m:
        result["gondereniban"] = m.group(1).replace(" ", "").strip()

    # Alıcı IBAN
    m = re.search(r"ALICI\s*IBAN\s+(TR[0-9 ]{20,})", text_compact, re.I)
    if m:
        result["aliciiban"] = m.group(1).replace(" ", "").strip()

    # 🟢 Alıcı adı (tam doğru biçim)
    m = re.search(
        r"ALICI\s*AD[İI]\s*SOYAD[İI]\s+([A-ZÇĞİÖŞÜa-zçğıöşü\s\.\-&]+?)(?=\s+(?:TUTAR|MASRAF|AÇIKLAMA|TL|$))",
        text_compact, re.I
    )
    if m:
        result["alici"] = re.sub(r"\s+", " ", m.group(1).strip())

    # Tutar
    m = re.search(r"TUTAR\s+([\d\.,]+)\s*TL", text_compact, re.I)
    if m:
        try:
            result["tutar"] = float(m.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            result["tutar"] = None

    # İşlem Tarihi
    m = re.search(r"İŞLEM\s*TARİH[İI]\s+(\d{2}\.\d{2}\.\d{4}\s*\d{2}:\d{2}:\d{2})", text_compact, re.I)
    if m:
        result["islemtarihi"] = m.group(1).strip()

    # Türkçe büyük harf düzeltmesi
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = to_turkish_upper(result["gonderen"])
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = to_turkish_upper(result["alici"])

    print(f"✅ parse_denisbank tamamlandı: {result}")
    return result





# ==========================================================
# 2️⃣ YAPI KREDİ
# ==========================================================
def parse_yapikredi(text):
    print("➡️ parse_yapikredi başladı")
    result = {"banka": "Yapı Kredi"}

    try:
        clean = re.sub(r"\s+", " ", text)

        # Gönderen adı
        m = re.search(r"GÖNDEREN\s*ADI\s*[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]{2,50}?)(?=\s*ÖDEMENIN|IBAN|ALICI|$)", clean, re.I)
        if m:
            result["gonderen"] = m.group(1).strip().title()

        # Gönderen IBAN
        m = re.search(r"IBAN[:\-]?\s*(TR[0-9 ]{20,})", clean, re.I)
        if m:
            result["gondereniban"] = m.group(1).replace(" ", "").strip()

        # Alıcı adı
        m = re.search(r"ALICI\s*ADI\s*[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s]{2,50}?)(?=\s*ALICI\s*TCKN|AÇIKLAMA|$)", clean, re.I)
        if m:
            result["alici"] = m.group(1).strip().title()

        # Alıcı IBAN
        m = re.search(r"ALICI\s*(?:HESAP|IBAN)\s*[:\-]?\s*(TR[0-9 ]{20,})", clean, re.I)
        if m:
            result["aliciiban"] = m.group(1).replace(" ", "").strip()

        # Tutar
        m = re.search(r"GIDEN\s*FAST\s*TUTARI\s*[:\-]?\s*-?([\d\.,]+)", clean, re.I)
        if m:
            result["tutar"] = float(m.group(1).replace(".", "").replace(",", "."))

        # Tarih
        m = re.search(r"IŞLEM\s*TARIHI\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})", clean, re.I)
        if m:
            result["islemtarihi"] = m.group(1)

    except Exception as e:
        print("❌ parse_yapikredi hata:", e)
    
    # ==========================================================
    #  Ad ve soyadları tamamen büyük harfe çevir
    # ==========================================================
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = result["gonderen"].upper()

    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = result["alici"].upper()

    # parse fonksiyonlarının sonunda:
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = to_turkish_upper(result["gonderen"])
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = to_turkish_upper(result["alici"])   

    print("✅ parse_yapikredi tamamlandı:", result) 
    return result












# ==========================================================
# 3️⃣ FİNANSBANK / ENPARA
# ==========================================================
def parse_finansbank(text):
    import re, unicodedata

    result = {"banka": "QNB Finansbank (Enpara)"}

    # Normalize
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("İ", "I").replace("ı", "i")

    # 🔹 Alıcı IBAN önce aranmalı (çünkü metinde bu daha sonra geliyor)
    m = re.search(r"ALICI\s*IBAN\s*:\s*(TR[0-9 ]{20,})", text, re.I)
    if m:
        result["aliciiban"] = m.group(1).replace(" ", "").strip()

    # 🔹 Gönderen IBAN — "ALICI" kelimesi içermeyen IBAN satırlarını yakala
    m = re.search(r"(?<!ALICI\s)IBAN\s*:\s*(TR[0-9 ]{20,})", text, re.I)
    if m:
        result["gondereniban"] = m.group(1).replace(" ", "").strip()

    # Gönderen adı
    m = re.search(
        r"MÜŞTER[Iİ]\s*ÜNVAN[Iİ]\s*:\s*([A-ZÇĞÖŞÜa-zçğıöşü\s\.\-]+?)(?=\s+IBAN|$)",
        text, re.I)
    if not m:
        m = re.search(
            r"GÖNDEREN\s*:\s*([A-ZÇĞÖŞÜa-zçğıöşü\s\.\-]+?)(?=\s+IBAN|$)",
            text, re.I)
    if m:
        result["gonderen"] = m.group(1).strip().upper()

    # Alıcı adı
    m = re.search(
        r"ALICI\s*ÜNVAN[Iİ]\s*:\s*([A-ZÇĞÖŞÜa-zçğıöşü\s\.\-]+?)(?=\s+ALICI\s*IBAN|$)",
        text, re.I)
    if m:
        result["alici"] = m.group(1).strip().upper()

    # Tutar (her türlü format)
    m = re.search(r"EFT\s*TUTAR[Iİ]\s*:\s*([\d\.,]+)", text, re.I)
    if m:
        raw_tutar = m.group(1)
        if re.search(r"\d+\.\d{3},\d+", raw_tutar):
            clean = raw_tutar.replace(".", "").replace(",", ".")
        elif re.search(r"\d+,\d{3}\.\d+", raw_tutar):
            clean = raw_tutar.replace(",", "")
        elif re.search(r"\d+,\d{3}", raw_tutar):
            clean = raw_tutar.replace(",", "")
        else:
            clean = raw_tutar
        try:
            result["tutar"] = float(clean)
        except:
            result["tutar"] = None

    # --- İşlem tarihi yakalama (güçlendirilmiş) ---
    # dene: "Işlem tarihi ve saati 02.10.2025 14:28:35" veya "İşlem Tarihi : 02.10.2025" vb.
    date_patterns = [
        r"işlem\s*tarihi\s*ve\s*saati\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})",   # "Işlem tarihi ve saati 02.10.2025"
        r"dokum[^\n]{0,50}dekont\s*tarihi\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})", # "Dekont Tarihi : 03.10.2025"
        r"dekont\s*tarihi\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})",
        r"işlem\s*tarih[ıi]\s*[:\-]?\s*(\d{2}\.\d{2}\.\d{4})",
        r"(\d{2}\.\d{2}\.\d{4})"  # fallback: ilk bulunan tarih
    ]

    found_date = None
    for p in date_patterns:
        m = re.search(p, text, re.I)
        if m:
            found_date = m.group(1)
            break

    if found_date:
        # istersen zamanı da almak istersin: (\d{2}\.\d{2}\.\d{4}\s*\d{2}:\d{2}:\d{2}) pattern'i ile
        result["islemtarihi"] = found_date
    else:
        # kesinlikle tarih yoksa None bırak veya boş string
        result["islemtarihi"] = None
    # --- tarih bloğu sonu ---

    # İşlem tarihi
    m = re.search(r"ISLEM\s*TAR[Iİ]H[Iİ]\s*(?:VE\s*SAATI)?\s*:?[\s\-]*(\d{2}\.\d{2}\.\d{4})", text, re.I)
    if m:
        result["islemtarihi"] = m.group(1).strip()

    # parse fonksiyonlarının sonunda:
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = to_turkish_upper(result["gonderen"])
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = to_turkish_upper(result["alici"])        

    print(f"✅ parse_finansbank tamamlandı: {result}")
    return result







# ==========================================================
# 4️⃣ İŞ BANKASI
# ==========================================================
def parse_isbank(text):
    result = {"banka": "İş Bankası"}

    # Normalize (İ/ı farkını ortadan kaldırmak ve görünmeyen karakterleri temizlemek)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("İ", "I").replace("ı", "i")

    # Gönderen
    m = re.search(r"e-?Dekont\s+([A-ZÇĞİÖŞÜa-zçğıöşü\s\.\-&]+?)\s+Müşteri\s*No", text)
    if m:
        result["gonderen"] = m.group(1).strip()

    # Gönderen IBAN
    m = re.search(r"IBAN\s*:?\s*(TR[0-9 ]{20,})", text)
    if m:
        result["gondereniban"] = m.group(1).replace(" ", "").strip()

    # Tutar (İşlem Tutarı) — TRY veya TL ile biten biçim de dahil
    m = re.search(r"[iıIİ]şlem\s*tutar[iıIİ]?\s*:?\s*([\d\.,]+)\s*(?:try|tl)?", text, re.I)
    if m:
        try:
            result["tutar"] = float(m.group(1).replace(".", "").replace(",", "."))
        except:
            result["tutar"] = None

    # Tarih (Dekont Tarihi)
    m = re.search(r"Dekont\s*Tarih[ıi]\s*:?\s*(\d{2}\.\d{2}\.\d{4})", text)
    if m:
        result["islemtarihi"] = m.group(1).strip()

    # Alıcı IBAN
    m = re.search(r"alici\s*iban\s*:?\s*(TR[0-9 ]{20,})", text, re.I)
    if m:
        result["aliciiban"] = m.group(1).replace(" ", "").strip()

    # Alıcı isim/unvan
    m = re.search(r"alici\s*(?:isim\s*[\\\/]?\s*unvan|isim|unvan)\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s\.\-&]+?)(?=\s+BSMV|$)", text, re.I)

    if m:
        result["alici"] = m.group(1).strip()

    # Adları tamamen büyük harfe çevir
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = result["gonderen"].upper()
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = result["alici"].upper()

    # parse fonksiyonlarının sonunda:
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = to_turkish_upper(result["gonderen"])
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = to_turkish_upper(result["alici"])        

    print(f"✅ parse_isbank tamamlandı: {result}")
    return result






# ==========================================================
# 5️⃣ GARANTİ BBVA
# ==========================================================
def parse_garanti(text):
    import re, unicodedata

    result = {"banka": "Garanti BBVA"}

    # Normalize
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("İ", "I").replace("ı", "i")

    # Gönderen adı (maaş kurumu)
    m = re.search(
        r"MAA[SŞ]\s*KURUM\s*:?\s*([A-ZÇĞÖŞÜa-zçğıöşü0-9\s\.\-&]+?)(?=\s+(?:YALNIZ|SIRA|TUTAR|TL|$))",
        text, re.I)
    if m:
        result["gonderen"] = m.group(1).strip().upper()

    # Gönderen IBAN
    m = re.search(r"IBAN\s*:\s*(TR[0-9 ]{20,})", text, re.I)
    if m:
        result["gondereniban"] = m.group(1).replace(" ", "").strip()

    # Alıcı (SAYIN … kısmı)
    m = re.search(r"SAYIN\s+([A-ZÇĞÖŞÜa-zçğıöşü\s\.\-]+)", text)
    if m:
        result["alici"] = m.group(1).strip().upper()

    # Alıcı IBAN tespiti
    m = re.search(r"ALICI\s*IBAN\s*:?\s*(TR[0-9 ]{20,})", text, re.I)
    if m:
        result["aliciiban"] = m.group(1).replace(" ", "").strip()
    else:
        result["aliciiban"] = ""


    # Tutar
    m = re.search(r"TUTAR\s*:?\s*[+\-]?\s*([\d\.,]+)\s*TL", text)
    if m:
        raw = m.group(1)
        raw = raw.replace(".", "").replace(",", ".")
        try:
            result["tutar"] = float(raw)
        except:
            result["tutar"] = None

    # Tarih (İşlem veya Düzenlenme tarihi)
    m = re.search(r"ISLEM\s*TARIHI\s*:?\s*(\d{2}[./]\d{2}[./]\d{4})", text, re.I)
    if not m:
        m = re.search(r"DÜZENLENME\s*TARIHI\s*:?\s*(\d{2}[./]\d{2}[./]\d{4})", text, re.I)
    if m:
        result["islemtarihi"] = m.group(1).replace("/", ".")

    # parse fonksiyonlarının sonunda:
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = to_turkish_upper(result["gonderen"])
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = to_turkish_upper(result["alici"])

    print(f"✅ parse_garanti tamamlandı: {result}")
    return result




# ==========================================================
# 6️⃣ GENEL PARSER (Bilinmeyen Banka)
# ==========================================================
def parse_general(text):
    print("🟪 parse_general çalıştı")
    result = {"banka": "Bilinmiyor"}

    m = re.search(r"(?:GÖNDEREN|MÜŞTER[İI]|SAYIN|ÜNVANI)[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s\.\-&]+)", text)
    if m:
        result["gonderen"] = m.group(1).strip()

    ibans = re.findall(r"\bTR[0-9 ]{16,}\b", text)
    if ibans:
        result["gondereniban"] = ibans[0].replace(" ", "")
        if len(ibans) > 1:
            result["aliciiban"] = ibans[1].replace(" ", "")

    m = re.search(r"(?:ALICI|ALAN|TRANSFER ED[İI]LEN)[:\-]?\s*([A-ZÇĞİÖŞÜa-zçğıöşü\s\.\-&]+)", text)
    if m:
        result["alici"] = m.group(1).strip()

    m = re.search(r"(?:TUTAR|İŞLEM TUTARI|FAST TUTARI)[:\-]?\s*([\d\.,]+)\s*TL", text)
    if m:
        try:
            result["tutar"] = float(m.group(1).replace(".", "").replace(",", "."))
        except:
            pass

    m = re.search(r"(\d{2}[./]\d{2}[./]\d{4}(?:\s*\d{2}:\d{2}:\d{2})?)", text)
    if m:
        result["islemtarihi"] = m.group(1).strip()

    m = re.search(r"(Denizbank|Ziraat|Vakıfbank|İş\s*Bankası|Garanti|Yapı\s*Kredi|Finansbank|Enpara|Akbank|ING)", text, re.I)
    if m:
        result["banka"] = m.group(1).strip()

    # parse fonksiyonlarının sonunda:
    if "gonderen" in result and isinstance(result["gonderen"], str):
        result["gonderen"] = to_turkish_upper(result["gonderen"])
    if "alici" in result and isinstance(result["alici"], str):
        result["alici"] = to_turkish_upper(result["alici"])   

    return result


# ==========================================================
# 7️⃣ ANA PARSER SEÇİCİ
# ==========================================================
def parse_dekont(filepath):
    text = extract_text(filepath)
    text_clean = re.sub(r"\s+", " ", text)

    # normalize text (remove invisible spaces and normalize Turkish chars)
    text_clean = unicodedata.normalize("NFKC", text_clean)
    text_clean = text_clean.replace("İ", "I").replace("ı", "i")

    # ⚡ Öncelikle Yapı Kredi kontrolü
    if re.search(r"yapi\s*(ve\s*)?kredi", text_clean, re.I):
        result = parse_yapikredi(text_clean)

    elif re.search(r"Deniz\s*bank", text_clean, re.I):
        result = parse_denisbank(text_clean)

    elif re.search(r"Enpara|Finansbank", text_clean, re.I):
        result = parse_finansbank(text_clean)

    elif re.search(r"İş\s*Bankas[ıi]|isbank\.com\.tr|İşCep", text_clean, re.I):
        result = parse_isbank(text_clean)

    elif re.search(r"Garanti|T\.?\s*Garanti\s*Bankas[ıi]", text_clean, re.I):
        result = parse_garanti(text_clean)

    elif re.search(r"Ziraat\s*Bankas[ıi]", text_clean, re.I):
        result = parse_general(text_clean)
        result["banka"] = "Ziraat Bankası"
    else:
        result = parse_general(text_clean)

    print(json.dumps(result, ensure_ascii=False))

    return result


# ==========================================================
# 8️⃣ KOMUT SATIRI GİRİŞİ
# ==========================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python dekontlar_parser.py <dosya_yolu>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print("Dosya bulunamadı:", file_path)
        sys.exit(1)

    parse_dekont(file_path)
