# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import dbg, parse_amount, to_turkish_upper

class EnparaParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "ENPARA")

    def parse(self):
        raw = self.text
        up = self.up

        # 1. Tür Tespiti
        if "FAST" in up: self.data["is_fast"] = True
        if "EFT" in up or "HAVALE" in up: self.data["is_havale"] = True
        if "GIDEN" in up or "GİDEN" in up: self.data["is_giden"] = True
        if "GELEN" in up: self.data["is_gelen"] = True
        if "MAAŞ" in up: self.data["is_maas"] = True

        # 2. Tarih Yakalama
        p1 = r"[İIıi]şlem\s+tarihi(?:\s+ve\s+saati)?\s*[:]\s*(\d{2}[./]\d{2}[./]\d{4})"
        m = re.search(p1, raw, flags=re.IGNORECASE)
        if m: 
            self.data["islemtarihi"] = m.group(1).replace("/", ".")
        else:
            m = re.search(r"(\d{2}[./]\d{2}[./]\d{4})", raw)
            if m: self.data["islemtarihi"] = m.group(1).replace("/", ".")

        # 3. Tutar Yakalama
        m = re.search(r"TL\s*([\d\.,]+)", raw)
        if m:
            # Enpara formatı için parse_amount zaten utils'te virgül/nokta temizliği yapacak
            self.data["tutar"] = parse_amount(m.group(1))

        # 4. Giden İşlem Mantığı (Alıcı Ünvanı ve Alıcı IBAN)
        if self.data["is_giden"]:
            m = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw)
            if m: self.data["gonderen"] = m.group(1).split("AÇIKLAMA")[0].strip()

            m = re.search(r"ALICI ÜNVANI\s*:\s*([^\n]+)", raw)
            if m:
                name = m.group(1).split("IBAN")[0].strip()
                self.data["alici"] = re.sub(r'[,\.\s]*\bALICI\b[,\.\s]*$', '', name, flags=re.I).strip()

            m = re.search(r"ALICI IBAN\s*:\s*(TR[0-9 ]+)", raw)
            if m: self.data["aliciiban"] = m.group(1).replace(" ", "")

            m = re.search(r"MÜŞTERİ ÜNVANI.*?IBAN\s*:\s*(TR[0-9 ]+)", raw, re.S)
            if m: self.data["gondereniban"] = m.group(1).replace(" ", "")

        # 5. Gelen İşlem Mantığı (Sayın... ve Vadesiz Hesap satırları)
        elif self.data["is_gelen"]:
            # Gelen işlemde alıcı ismi 'Sayın ...' kısmında yer alır
            m = re.search(r"Şube adı\s*:([^\n\r]+)", raw, flags=re.I)
            if m:
                line = m.group(1).strip()
                m2 = re.search(r"Sayın\s+(.+)", line, flags=re.I)
                if m2: self.data["alici"] = m2.group(1).strip()

            # Gelen işlemde gönderen IBAN 'Vadesiz TL' veya 'Günlük hesap' satırından alınır
            m_iban = re.search(r"(Vadesiz|Günlük)\s+TL\s+(TR[0-9 ]+)", raw, re.I)
            if m_iban:
                self.data["gondereniban"] = m_iban.group(2).replace(" ", "").strip()
            
            # Gelen işlemde gönderen ismi 'GÖNDEREN :' kısmından yakalanır
            m_g = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw, re.I)
            if m_g: self.data["gonderen"] = m_g.group(1).split("AÇIKLAMA")[0].strip()

        return self.finalize()