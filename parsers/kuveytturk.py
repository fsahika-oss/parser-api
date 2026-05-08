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
        if "FAST" in up:
            self.data["is_fast"] = True

        if "GİDEN" in up or "GIDEN" in up:
            self.data["is_giden"] = True

        # 🔥 EKLENDİ
        if "HAVALE" in up:
            self.data["is_havale"] = True

        # 2. Tutar Yakalama (Örn: Tutar 5.975,00TL)
        m_tutar = re.search(r"Tutar\s*([\d\.,]+)", raw, re.I)

        # 🔥 YENİ FORMAT DESTEĞİ
        if not m_tutar:
            m_tutar = re.search(
                r"Tutar\s*:?\s*([0-9\.\,]+)\s*TL",
                raw,
                re.I
            )

        if m_tutar:
            # Kuveyt Türk'te nokta binlik, virgül kuruş ayırıcıdır
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. Tarih Yakalama

        # ESKİ FORMAT
        m_date = re.search(
            r"İşlemTarihi\s*(\d{2}\.\d{2}\.\d{4})",
            raw,
            re.I
        )

        # 🔥 YENİ FORMAT DESTEĞİ
        if not m_date:
            m_date = re.search(
                r"BelgeTarihi\s*:?\s*(\d{2}[-./]\d{2}[-./]\d{4})",
                raw,
                re.I
            )

        if m_date:
            self.data["islemtarihi"] = (
                m_date.group(1)
                .replace("-", ".")
                .replace("/", ".")
            )

        # 4. Gönderen Kişi
        # 'GönderenKişi' etiketinden başlayıp 'Alıcı' etiketine kadar olan kısmı alır

        m_g = re.search(
            r"GönderenKişi\s*(.*?)\s*(?=Alıcı)",
            raw,
            re.I | re.S
        )

        # 🔥 YENİ FORMAT : işaretli alanlar
        if not m_g:
            m_g = re.search(
                r"GönderenKişi\s*:?\s*(.*?)\s*(?=Alıcı)",
                raw,
                re.I | re.S
            )

        if m_g:
            # İçindeki alt satırları temizleyip tek satıra indirir
            temiz = " ".join(m_g.group(1).split()).strip()

            self.data["gonderen"] = to_turkish_upper(temiz)

        # 5. Alıcı İsmi
        # 'Alıcı' etiketinden başlayıp 'GönderilenIBAN' etiketine kadar olan kısmı alır

        m_a = re.search(
            r"Alıcı\s*(.*?)\s*(?=GönderilenIBAN)",
            raw,
            re.I | re.S
        )

        # 🔥 YENİ FORMAT
        if not m_a:
            m_a = re.search(
                r"Alıcı\s*:?\s*(.*?)\s*(?=GönderilenIBAN)",
                raw,
                re.I | re.S
            )

        if m_a:
            temiz = " ".join(m_a.group(1).split()).strip()

            self.data["alici"] = to_turkish_upper(temiz)

        # 6. Alıcı IBAN

        m_iban = re.search(
            r"GönderilenIBAN\s*(TR[0-9 ]+)",
            raw,
            re.I
        )

        # 🔥 YENİ FORMAT
        if not m_iban:
            m_iban = re.search(
                r"GönderilenIBAN\s*:?\s*(TR[0-9 ]+)",
                raw,
                re.I
            )

        if m_iban:
            self.data["aliciiban"] = (
                m_iban.group(1)
                .replace(" ", "")
                .strip()
            )

        return self.finalize()
