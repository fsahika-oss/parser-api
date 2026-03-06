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

        # 1. Tür Tespiti (Her iki format için ortak)
        if "FAST" in up: self.data["is_fast"] = True
        if "EFT" in up or "HAVALE" in up: self.data["is_havale"] = True
        if "GIDEN" in up or "GİDEN" in up: self.data["is_giden"] = True
        if "GELEN" in up: self.data["is_gelen"] = True
        if "MAAŞ" in up or "MAAS" in up: self.data["is_maas"] = True

        # --- SEÇİCİ MANTIK: QNB / YENİ FORMAT MI? ---
        # Eğer metinde QNB geçiyorsa veya GÖNDEREN'den sonra iki nokta yoksa yeni kodu çalıştır
        is_qnb_format = "QNB" in up or re.search(r"GONDEREN\s+[^:]", raw, re.I)

        if is_qnb_format:
            # ---------------------------------------------------------
            # YENİ QNB FORMATI İÇİN ÇALIŞAN KODUN (İKİNCİ KOD)
            # ---------------------------------------------------------
            # 2. Tarih
            m_tarih = re.search(r"İşlem\s+Tarihi\s+(\d{2}/\d{2}/\d{4})", raw, re.I)
            if m_tarih:
                self.data["islemtarihi"] = m_tarih.group(1).replace("/", ".")
            else:
                m = re.search(r"(\d{2}[./]\d{2}[./]\d{4})", raw)
                if m: self.data["islemtarihi"] = m.group(1).replace("/", ".")

            # 3. Tutar
            # Önce gerçek EFT tutarı
            m_tutar = re.search(r"EFT\s*TUTARI\s*:\s*([\d\.,]+)", raw, re.I)

            # yoksa genel TUTARI
            if not m_tutar:
                m_tutar = re.search(r"TUTARI\s*:\s*([\d\.,]+)", raw, re.I)

            # son fallback
            if not m_tutar:
                m_tutar = re.search(r"TL\s+([\d\.,]+)", raw)

            if m_tutar:
                amount = m_tutar.group(1)

                # binlik ayıracı temizle
                amount = amount.replace(",", "")

                self.data["tutar"] = parse_amount(amount)

            # 4. Giden İşlem
            if self.data["is_giden"]:
                m_g = re.search(r"G[ÖO]NDEREN\s*[:\s]\s*([^\n]+)", raw, re.I)
                if m_g:
                    self.data["gonderen"] = re.split(r"AÇIKLAMA|IBAN", m_g.group(1), flags=re.I)[0].strip()

                m_g_iban = re.search(r"TR10\d{22}", raw.replace(" ", ""))
                if m_g_iban:
                    self.data["gondereniban"] = m_g_iban.group(0)
                else:
                    m_alt_iban = re.search(r"MUSTERI\s+UNVANI.*?IBAN\s*:\s*(TR[0-9 ]+)", raw, re.S | re.I)
                    if m_alt_iban: self.data["gondereniban"] = m_alt_iban.group(1).replace(" ", "").strip()

                m_alici = re.search(r"ALICI\s+Ü?NVANI\s*:\s*([^\n]+)", raw, re.I)
                if m_alici:
                    self.data["alici"] = re.split(r"ALICI\s+IBAN|IBAN", m_alici.group(1), flags=re.I)[0].strip()
                else:
                    m_alici2 = re.search(r"Alıcı\s*:\s*([^\n]+?)(?:\s+Türkiye|\s+TL|\s+IBAN|$)", raw, re.I)
                    if m_alici2: self.data["alici"] = m_alici2.group(1).strip()

                m_a_iban = re.search(r"ALICI\s+IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
                if m_a_iban:
                    self.data["aliciiban"] = m_a_iban.group(1).replace(" ", "").strip()

        else:
            # ---------------------------------------------------------
            # 3 FARKLI DEKONTU OKUYAN ESKİ KODUN (BİRİNCİ KOD)
            # ---------------------------------------------------------
            # 2. Tarih
            p1 = r"[İIıi]şlem\s+tarihi(?:\s+ve\s+saati)?\s*[:]\s*(\d{2}[./]\d{2}[./]\d{4})"
            m = re.search(p1, raw, flags=re.IGNORECASE)
            if m: 
                self.data["islemtarihi"] = m.group(1).replace("/", ".")
            else:
                m = re.search(r"(\d{2}[./]\d{2}[./]\d{4})", raw)
                if m: self.data["islemtarihi"] = m.group(1).replace("/", ".")

            # 3. Tutar
            m = re.search(r"TL\s*([\d\.,]+)", raw)
            if m:
                self.data["tutar"] = parse_amount(m.group(1))

            # 4. Giden İşlem
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

            # 5. Gelen İşlem
            elif self.data["is_gelen"]:
                m = re.search(r"Şube adı\s*:([^\n\r]+)", raw, flags=re.I)
                if m:
                    line = m.group(1).strip()
                    m2 = re.search(r"Sayın\s+(.+)", line, flags=re.I)
                    if m2: self.data["alici"] = m2.group(1).strip()

                m_iban = re.search(r"(Vadesiz|Günlük)\s+TL\s+(TR[0-9 ]+)", raw, re.I)
                if m_iban:
                    self.data["gondereniban"] = m_iban.group(2).replace(" ", "").strip()
                
                m_g = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw, re.I)
                if m_g: self.data["gonderen"] = m_g.group(1).split("AÇIKLAMA")[0].strip()

        return self.finalize()
