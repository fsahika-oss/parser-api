# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class VakifKatilimParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "vakifkatilim")

    def parse(self):
        raw = self.text
        up = self.up

        # 1. Tür Tespiti
        if "HAVALE" in up: self.data["is_havale"] = True
        if "EFT" in up or "FAST" in up: self.data["is_havale"] = True
        if "MAAŞ" in up or "MAAS" in up: self.data["is_maas"] = True
        self.data["is_giden"] = True

        # 2. İşlem Tarihi Yakalama (Satır kırılımına duyarlı)
        # 'İşlem :' ile başlayıp tarih formatına (03/11/2025) odaklanır
        m_date = re.search(r"İşlem\s*:\s*(\d{2}/\d{2}/\d{4})", raw, re.I)
        if m_date:
            self.data["islemtarihi"] = m_date.group(1).replace("/", ".")

        # 3. Tutar Yakalama
        m_tutar = re.search(r"Tutar\s*([\d\.,]+)\s*TL", raw, re.I)
        if m_tutar:
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 4. Gönderen Kişi
        # 'Gönderen Kişi :' etiketinden satır sonuna kadar olan kısmı alır
        m_gond = re.search(r"Gönderen Kişi\s*:\s*(.+)", raw, re.I)
        if m_gond:
            self.data["gonderen"] = m_gond.group(1).strip()

        # 5. Gönderilen (Alıcı) Kişi
        m_alici = re.search(r"Gönderilen Kişi\s*:\s*(.+)", raw, re.I)
        if m_alici:
            self.data["alici"] = m_alici.group(1).strip()

        # 6. IBAN / Hesap No (Vakıf Katılım'da genellikle Hesap No yazar)
        m_hno = re.search(r"Gönderilen\s+Hesap No\s*:\s*([\d-]+)", raw, re.I)
        if m_hno:
            self.data["aliciiban"] = m_hno.group(1).strip()

        return self.finalize()