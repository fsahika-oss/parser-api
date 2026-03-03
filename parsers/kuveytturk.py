# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class KuveytTurkParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "kuveytturk")

    def parse(self):
        raw = self.text
        up = self.up

        # 1. Tür Tespiti
        if "FAST" in up: self.data["is_fast"] = True
        if "GİDEN" in up or "GIDEN" in up: self.data["is_giden"] = True
        
        # 2. Tutar Yakalama (Örn: Tutar 5.975,00TL)
        m_tutar = re.search(r"Tutar\s*([\d\.,]+)", raw, re.I)
        if m_tutar:
            # Kuveyt Türk'te nokta binlik, virgül kuruş ayırıcıdır
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. Tarih Yakalama (Örn: İşlemTarihi 04.11.202509:22)
        # Tarih ve saat birleşik olduğu için sadece ilk 10 karakteri (gün.ay.yıl) alıyoruz
        m_date = re.search(r"İşlemTarihi\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
        if m_date: self.data["islemtarihi"] = m_date.group(1)

        # 4. Gönderen Kişi
        # 'GönderenKişi' etiketinden başlayıp 'Alıcı' etiketine kadar olan kısmı alır
        m_g = re.search(r"GönderenKişi\s*(.*?)\s*(?=Alıcı)", raw, re.I | re.S)
        if m_g:
            # İçindeki alt satırları temizleyip tek satıra indirir
            self.data["gonderen"] = " ".join(m_g.group(1).split()).strip()

        # 5. Alıcı İsmi
        # 'Alıcı' etiketinden başlayıp 'GönderilenIBAN' etiketine kadar olan kısmı alır
        m_a = re.search(r"Alıcı\s*(.*?)\s*(?=GönderilenIBAN)", raw, re.I | re.S)
        if m_a:
            self.data["alici"] = " ".join(m_a.group(1).split()).strip()

        # 6. Alıcı IBAN
        m_iban = re.search(r"GönderilenIBAN\s*(TR[0-9 ]+)", raw, re.I)
        if m_iban:
            self.data["aliciiban"] = m_iban.group(1).replace(" ", "").strip()

        return self.finalize()