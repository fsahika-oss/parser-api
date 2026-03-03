# -*- coding: utf-8 -*-
import re
import unicodedata
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class VakifBankParser(BaseParser):
    def __init__(self, text):
        # Eski kodundaki NFKC normalizasyonunu koruyoruz
        normalized_text = unicodedata.normalize("NFKC", text)
        super().__init__(normalized_text, "vakifbank")

    def parse(self):
        t = self.text
        TU = self.up
        
        # 1. Tür Tespiti (Eski kodundaki \b sınırları ile)
        if re.search(r"\bHAVALE\b", TU): self.data["is_havale"] = True
        if re.search(r"\bEFT\b", TU): self.data["is_eft"] = True
        if re.search(r"\bMAAŞ\b|\bMAAS\b|\bMAAŞ ÖDEMESİ\b", TU): self.data["is_maas"] = True
        if re.search(r"\bGELEN\b", TU): self.data["is_gelen"] = True
        if re.search(r"\bGİDEN\b|\bGIDEN\b", TU): self.data["is_giden"] = True

        # 2. Tarih ve Tutar
        m_date = re.search(r"İŞLEM(?:\s+TARİHİ|\s+TARİHİ\s+)?\s*[:]*\s*([0-9]{2}[./][0-9]{2}[./][0-9]{4})", t, flags=re.I)
        if m_date: self.data["islemtarihi"] = m_date.group(1).replace("/", ".")

        m_tutar = re.search(r"İŞLEM\s*TUTARI\s*[:\-]?\s*([0-9\.,]+)\s*TL", t, flags=re.I)
        if not m_tutar: m_tutar = re.search(r"([0-9\.,]+)\s*TL", t, flags=re.I)
        if m_tutar: self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. İsim ve IBAN (Vakıfbank Tür 1: Havale/Ece Biçer)
        # Alıcı Adı
        m_alici = re.search(r"ALICI AD SOYAD/UNVAN\s+([A-ZÇĞİÖŞÜa-zçğıöşü\s]+)", t, flags=re.I)
        if m_alici: self.data["alici"] = m_alici.group(1).strip()

        # İki satıra bölünmüş Alıcı IBAN birleştirme (Eski koddaki M hatları)
        m_top = re.search(r"^(TR[0-9 ]{10,34})\s*$", t, flags=re.M)
        m_bottom = re.search(r"^\s*([0-9]{2,}\s*[0-9]{2,})\s*$", t, flags=re.M)
        if m_top and m_bottom:
            self.data["aliciiban"] = (m_top.group(1).replace(" ", "") + m_bottom.group(1).replace(" ", "")).strip()

        # Maskeli Gönderen Tespiti (Satır bazlı önceki satırı alma)
        lines = [ln.strip() for ln in t.splitlines()]
        for i, ln in enumerate(lines):
            if re.search(r"TR[0-9 ]*\*+", ln):
                if i > 0:
                    prev = lines[i-1].strip()
                    if re.search(r"[A-Za-zÇĞİÖŞÜçğışöüİ]", prev):
                        self.data["gonderen"] = prev
                break

        # ----------------------------------------------------
        # VAKIFBANK FORMAT TÜR 2 (İNCİ HOLDİNG AŞ olan)
        # Bu formatta TR ile başlayan ilk büyük blok GÖNDEREN'dir.
        # ----------------------------------------------------
        if self.data["gonderen"] == "":
            lines = [l.strip() for l in t.splitlines() if l.strip()]

            for i, ln in enumerate(lines):
                # Maskesiz, temiz IBAN satırını bul (Genelde Gönderen IBAN'dır)
                if re.match(r"^TR\d[\d ]+$", ln):
                    iban_part1 = ln.replace(" ", "")
                    
                    # Eğer bir alt satırda ADSOYAD/UNVAN1 etiketi varsa bu GÖNDEREN'dir
                    if i+1 < len(lines) and "ADSOYAD/UNVAN1" in to_turkish_upper(lines[i+1]):
                        # İsmi etiketlerden temizle
                        name = re.sub(r"HESAP NUMARASI|ADSOYAD/UNVAN1|ADSOYAD|UNVAN1", "", lines[i+1], flags=re.I).strip()
                        
                        self.data["gonderen"] = name
                        
                        # IBAN'ın devamı bir alt satırda olabilir (9526 23 gibi)
                        if i+2 < len(lines) and re.fullmatch(r"[0-9 ]+", lines[i+2]):
                            self.data["gondereniban"] = iban_part1 + lines[i+2].replace(" ", "")
                        else:
                            self.data["gondereniban"] = iban_part1
                        
                        # BU FORMATTA ALICI BİLGİSİ BU BLOKTA YOKTUR, BOŞ BIRAKILMALI
                        self.data["alici"] = ""
                        self.data["aliciiban"] = ""
                        break

        # 5. Gelen İşlem Mantığı
        if self.data["is_gelen"]:
            m_mus = re.search(r"MÜŞTERİ\s+ÜNVANI\s*[:\-]?\s*([^\n\r]+)", t, flags=re.I)
            if m_mus: self.data["alici"] = m_mus.group(1).strip()

        # 6. Son Temizlik ve Finalize
        self.data["gonderen"] = to_turkish_upper(self.data.get("gonderen", ""))
        self.data["alici"] = to_turkish_upper(self.data.get("alici", ""))
        
        return self.finalize()