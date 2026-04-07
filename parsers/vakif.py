# -*- coding: utf-8 -*-
import re
import unicodedata
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class VakifBankParser(BaseParser):
    def __init__(self, text):
        normalized_text = unicodedata.normalize("NFKC", text)
        super().__init__(normalized_text, "vakifbank")

    def parse(self):
        t = self.text
        TU = self.up
        
        # 1. Tür Tespiti
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

        # 3. Alıcı (eski yöntem)
        m_alici = re.search(r"ALICI AD SOYAD/UNVAN\s+([A-ZÇĞİÖŞÜa-zçğıöşü\s]+)", t, flags=re.I)
        if m_alici: self.data["alici"] = m_alici.group(1).strip()

        # IBAN birleştirme
        m_top = re.search(r"^(TR[0-9 ]{10,34})\s*$", t, flags=re.M)
        m_bottom = re.search(r"^\s*([0-9]{2,}\s*[0-9]{2,})\s*$", t, flags=re.M)
        if m_top and m_bottom:
            self.data["aliciiban"] = (m_top.group(1).replace(" ", "") + m_bottom.group(1).replace(" ", "")).strip()

        # Maskeli gönderen
        lines = [ln.strip() for ln in t.splitlines()]
        for i, ln in enumerate(lines):
            if re.search(r"TR[0-9 ]*\*+", ln):
                if i > 0:
                    prev = lines[i-1].strip()
                    if re.search(r"[A-Za-zÇĞİÖŞÜçğışöüİ]", prev):
                        self.data["gonderen"] = prev
                break

        # ----------------------------------------------------
        # FORMAT TÜR 2 (eski kod - aynen duruyor)
        # ----------------------------------------------------
        if self.data["gonderen"] == "":
            lines = [l.strip() for l in t.splitlines() if l.strip()]

            for i, ln in enumerate(lines):
                if re.match(r"^TR\d[\d ]+$", ln):
                    iban_part1 = ln.replace(" ", "")
                    
                    if i+1 < len(lines) and "ADSOYAD/UNVAN1" in to_turkish_upper(lines[i+1]):
                        name = re.sub(r"HESAP NUMARASI|ADSOYAD/UNVAN1|ADSOYAD|UNVAN1", "", lines[i+1], flags=re.I).strip()
                        
                        self.data["gonderen"] = name
                        
                        if i+2 < len(lines) and re.fullmatch(r"[0-9 ]+", lines[i+2]):
                            self.data["gondereniban"] = iban_part1 + lines[i+2].replace(" ", "")
                        else:
                            self.data["gondereniban"] = iban_part1
                        
                        self.data["alici"] = ""
                        self.data["aliciiban"] = ""
                        break

        # ----------------------------------------------------
        # ✅ FORMAT TÜR 3 (YENİ EKLENEN - ALT SATIR İSİM)
        # ----------------------------------------------------
        if self.data["gonderen"] == "" and self.data["alici"] == "":
            lines = [l.strip() for l in t.splitlines() if l.strip()]
            
            for i, ln in enumerate(lines):
                if "GÖNDEREN AD SOYAD" in to_turkish_upper(ln):
                    
                    if i + 1 < len(lines):
                        raw_line = lines[i + 1].strip()
                        words = raw_line.split()
                        
                        if len(words) >= 4:
                            gonderen_words = []
                            alici_words = []
                            mode = "gonderen"
                            
                            for w in words:
                                if w.islower():
                                    mode = "alici"
                                
                                if mode == "gonderen":
                                    gonderen_words.append(w)
                                else:
                                    alici_words.append(w)
                            
                            self.data["gonderen"] = " ".join(gonderen_words)
                            self.data["alici"] = " ".join(alici_words)
                        else:
                            self.data["gonderen"] = raw_line
                    
                    break

        # 5. Gelen işlem
        if self.data["is_gelen"]:
            m_mus = re.search(r"MÜŞTERİ\s+ÜNVANI\s*[:\-]?\s*([^\n\r]+)", t, flags=re.I)
            if m_mus: self.data["alici"] = m_mus.group(1).strip()

        # 6. Final
        self.data["gonderen"] = to_turkish_upper(self.data.get("gonderen", ""))
        self.data["alici"] = to_turkish_upper(self.data.get("alici", ""))
        
        return self.finalize()
