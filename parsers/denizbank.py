# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class DenizbankParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "denizbank")

    def parse(self):
        raw = self.text
        clean_raw = raw.replace("\n", "  ")
        up = to_turkish_upper(clean_raw)

        # 1. Tür Tespiti
        if "FAST" in up:
            self.data["is_fast"] = True

        self.data["is_giden"] = True

        # 2. Tutar
        m_tutar = re.search(r"Tutar\s+([\d\.,]+)", clean_raw, re.I)
        if m_tutar:
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. Tarih
        m_date = re.search(r"İşlem\s*Tarihi\s*(\d{2}\.\d{2}\.\d{4})", clean_raw, re.I)
        if m_date:
            self.data["islemtarihi"] = m_date.group(1)

        # 4. Gönderen
        m_g = re.search(r"Adı\s*Soyadı\s+(.*?)(?=\s*İşlem\s*Türü)", clean_raw, re.I | re.S)
        if m_g:
            self.data["gonderen"] = to_turkish_upper(" ".join(m_g.group(1).split()).strip())

        # 5. Alıcı (YENİ + GERİ UYUMLU)
        m_a = re.search(
            r"Alıcı\s*Adı\s*Soyadı\s+(.*?)(?=\s*Alıcı\s*IBAN|\s*Alıcı\s*Şube|\s*Tutar|$)",
            clean_raw,
            re.I | re.S
        )
        if m_a:
            self.data["alici"] = to_turkish_upper(" ".join(m_a.group(1).split()).strip())

        # 6. Alıcı IBAN
        m_a_iban = re.search(r"Alıcı\s*IBAN\s*(TR[0-9 ]+)", clean_raw, re.I)
        if m_a_iban:
            self.data["aliciiban"] = m_a_iban.group(1).replace(" ", "").strip()

        # 7. Gönderen IBAN
        m_g_iban = re.search(r"(?<!Alıcı\s)IBAN\s*(TR[0-9 ]+)", clean_raw, re.I)
        if m_g_iban:
            self.data["gondereniban"] = m_g_iban.group(1).replace(" ", "").strip()

        return self.finalize()
