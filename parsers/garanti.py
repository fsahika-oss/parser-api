# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import dbg, parse_amount

class GarantiParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "garanti")

    def parse(self):
        t = self.text
        TU = self.up
        
        # --- Dahili Yardımcı Fonksiyon ---
        def clean_name_line(s):
            if not s: return s
            s = s.strip()
            s = re.sub(r"\s+", " ", s)
            s = re.sub(r"\*{2,}\s*/\s*\*{2,}", "", s)
            s = re.sub(r"\*{2,}", "", s)
            s = re.sub(r"\bMÜŞTERİ(?:\s*NUMARASI|\s*NO)?\s*[:\-]?\s*\d+\b", "", s, flags=re.I)
            s = re.sub(r"\b(TC|TCKN|VKN|SIRA\s*NO|SIRA)\s*[:\-]?\s*[\d\w\-\/]+\b", "", s, flags=re.I)
            s = re.sub(r"^[\*\s\/\-\d]+", "", s)
            s = re.sub(r"\b\d{2,6}\s*\/\s*\d{3,10}\b", "", s)
            s = re.sub(r"\*{2,}.*?(?=[A-ZÇĞİÖŞÜ])", "", s)
            s = re.split(r"\b(MAH|MAH\.|SOK|SOK\.|CAD|CAD\.|SK|SK\.|NO:|NO|KAPI|BULVAR|BLV|APT|DAIRE|DAİRE)\b", s, flags=re.I)[0].strip()
            s = re.sub(r"\bIBAN\b.*", "", s, flags=re.I).strip()
            return s

        # 1. Genel Bilgiler
        # IBAN: Hem tek satır hem de etiketli aramayı kapsar
        m = re.search(r"IBAN\s*[:]?\s*(TR[0-9 ]{20,34})", t, re.I)
        top_iban = m.group(1).replace(" ", "") if m else None

        m = re.search(r"(İŞLEM|ISLEM)\s*TAR(İ|I)H(İ|I)\s*[: ]+(\d{2}[./]\d{2}[./]\d{4})", t, re.I)
        if m: 
            self.data["islemtarihi"] = m.group(4).replace("/", ".")
        else:
            m = re.search(r"DÜZENLENME TARİHİ\s*[:]\s*(\d{2}[./]\d{2}[./]\d{4})", t, re.I)
            if m: self.data["islemtarihi"] = m.group(1).replace("/", ".")

        # Tutar Yakalama: SIRA NO içeren yeni satır yapısı için esnetildi
        m = re.search(r"TUTAR\s*[:]?\s*[+\- ]*\s*([\d\.,]+)", t, re.I)
        if m: self.data["tutar"] = parse_amount(m.group(1))

        sayin = None
        m = re.search(r"SAYIN\s+([^\n\r]+)", t, re.I)
        if m: sayin = clean_name_line(m.group(1))

        # 2. Format Tespiti
        is_fast = "FAST" in TU
        is_gelen_fast = "GELEN FAST" in TU # Yeni formatın anahtarı
        is_maas = (("MAAŞ" in TU or "MAAS" in TU) and ("KURUM" in TU or "MAAS ÖDEMESİ" in TU))
        has_borclu = ("BORÇLU" in TU) or ("BORCLU" in TU)
        has_alacakli = "ALACAKLI" in TU

        # 3. Branşlara Göre Ayrıştırma
        if is_gelen_fast:
            # --- YENİ GELEN FAST FORMATI ---
            # Bu formatta 'SAYIN' olan kişi ALICI'dır.
            if sayin: self.data["alici"] = sayin
            self.data["aliciiban"] = top_iban
            
            m = re.search(r"GÖNDEREN\s*:\s*([^\n\r]+)", t, re.I)
            if m: self.data["gonderen"] = clean_name_line(m.group(1))
            
            # Gönderen IBAN bu dekontta genellikle yer almaz, alıcı IBAN'ı kaydedilir.
            self.data["gondereniban"] = ""

        elif is_fast:
            # --- ESKİ GİDEN FAST FORMATI ---
            if sayin: self.data["gonderen"] = sayin
            if top_iban: self.data["gondereniban"] = top_iban
            
            m = re.search(r"ALACAKLI\s*:\s*([^\n\r]+)", t, re.I)
            if m: self.data["alici"] = clean_name_line(m.group(1))
            m = re.search(r"ALACAKLI IBAN\s*:\s*(TR[0-9 ]+)", t)
            self.data["aliciiban"] = m.group(1).replace(" ", "") if m else top_iban
        
        elif is_maas:
            # --- MAAŞ FORMATI ---
            if sayin: self.data["alici"] = sayin
            m = re.search(r"KURUM\s*:\s*([^\n\r]+)", t, re.I)
            if m: self.data["gonderen"] = clean_name_line(m.group(1))
            m = re.search(r"ALICI\s*IBAN\s*:\s*(TR[0-9 ]+)", t)
            self.data["aliciiban"] = m.group(1).replace(" ", "") if m else top_iban
            self.data["gondereniban"] = ""
            
        else: # Havale Branch
            if has_borclu:
                m = re.search(r"BOR[ÇC]LU HESAP\s*:\s*([^\n\r]+)", t, re.I)
                if m: self.data["gonderen"] = clean_name_line(m.group(1))
                if sayin: self.data["alici"] = sayin
                self.data["aliciiban"] = top_iban
                self.data["gondereniban"] = ""
            elif has_alacakli:
                m = re.search(r"ALACAKLI HESAP\s*:\s*([^\n\r]+)", t, re.I)
                if m: self.data["alici"] = clean_name_line(m.group(1))
                m = re.search(r"ALACAKLI IBAN\s*:\s*(TR[0-9 ]+)", t)
                self.data["aliciiban"] = m.group(1).replace(" ", "") if m else top_iban
                if sayin: self.data["gonderen"] = sayin
                m = re.search(r"BORÇLU IBAN\s*:\s*(TR[0-9 *]+)", t, re.I)
                if m: self.data["gondereniban"] = m.group(1).replace(" ", "").replace("*", "")
            else:
                if sayin: self.data["alici"] = sayin
                self.data["aliciiban"] = top_iban

        return self.finalize()
