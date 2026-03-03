# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount

class GenericParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "bilinmiyor")

    def parse(self):
        t = self.text
        
        # 1. Genel Tarih Yakalama (31.10.2025 veya 31/10/2025)
        m_date = re.search(r"(\d{2}[./]\d{2}[./]\d{4})", t)
        if m_date:
            self.data["islemtarihi"] = m_date.group(1).replace("/", ".")

        # 2. Genel Tutar Yakalama (TL/TRY ibaresinden önceki rakamlar)
        m_tutar = re.search(r"([\d\.,]+)\s*(?:TL|TRY|TUTAR)", t, re.I)
        if m_tutar:
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. Genel IBAN Yakalama (İlk iki IBAN'ı gönderen/alıcı olarak ata)
        ibans = re.findall(r"TR[0-9 ]{20,34}", t)
        if ibans:
            self.data["gondereniban"] = ibans[0].replace(" ", "").strip()[:26]
            if len(ibans) > 1:
                self.data["aliciiban"] = ibans[1].replace(" ", "").strip()[:26]

        return self.finalize()