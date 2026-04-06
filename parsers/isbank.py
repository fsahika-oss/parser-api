# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class IsBankParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "isbankasi")

    def parse(self):
        raw = self.text
        up = self.up
        clean_raw = raw.replace("\n", " ")

        # 🎯 YENİ FORMAT (İŞ BANKASI - PARA AKTARMA)
        if "PARA AKTARMA" in up:

            self.data["is_giden"] = True

            if "MAAŞ" in up or "MAAS" in up:
                self.data["is_maas"] = True

            # tutar
            m_t = re.search(r"Aktarılan\s+Tutar\s*:\s*([\d\.,]+)", raw, re.I)
            if m_t:
                self.data["tutar"] = parse_amount(m_t.group(1))

            # tarih
            m_dt = re.search(r"İşlem\s*Zam.*?:\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
            if m_dt:
                self.data["islemtarihi"] = m_dt.group(1)

            # gönderen + alıcı (AYNI SATIR FIX)
            m_line = re.search(r"Gönderici\s+Hesap\s*:\s*(.+)", raw, re.I)
            if m_line:
                line = m_line.group(1)

                parts = re.split(r"Alıcı\s+Hesap\s*:\s*", line, flags=re.I)

                if len(parts) == 2:
                    self.data["gonderen"] = to_turkish_upper(parts[0].strip())
                    self.data["alici"] = to_turkish_upper(parts[1].strip())

            # IBAN
            m_ibans = re.findall(r"TR[0-9 ]{20,34}", raw)
            if len(m_ibans) >= 2:
                self.data["gondereniban"] = m_ibans[0].replace(" ", "")[:26]
                self.data["aliciiban"] = m_ibans[1].replace(" ", "")[:26]

            return self.finalize()

        # --- ESKİ KODUN (AYNEN) ---
        if "MAAŞ" in up or "MAAS" in up: self.data["is_maas"] = True
        if "FAST" in up: self.data["is_fast"] = True
        if "HVL" in up or "EFT" in up: self.data["is_havale"] = True
        self.data["is_giden"] = True

        m_tutar = re.search(r"(?:İşlem\s+)?Tutar(?:ı)?\s*:\s*([\d\.,]+)", raw, re.I)
        if m_tutar:
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        m_date = re.search(r"Dekont\s*Tarihi\s*:\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
        if m_date:
            self.data["islemtarihi"] = m_date.group(1)

        if "Gönderici İsim/Ünvan" in raw:
            m_g = re.search(r"Gönderici\s+İsim/Ünvan\s*:\s*(.+)", raw, re.I)
            if m_g:
                self.data["gonderen"] = to_turkish_upper(m_g.group(1).strip())
        else:
            m_g = re.search(r"Doküman\s+Numarası\s*:\s*\d+\s*\n(.+?)(?=İşlem Yeri|$)", raw, re.I | re.S)
            if m_g:
                self.data["gonderen"] = to_turkish_upper(m_g.group(1).strip())

        m_alici = re.search(r"Alıcı\s+(?:Isim\\Unvan|İsim\s*/Ünvan)\s*:\s*(.+)", raw, re.I)
        if m_alici:
            alici_val = m_alici.group(1).strip()
            self.data["alici"] = to_turkish_upper(alici_val.split("Açıklama")[0].strip())

        m_a_iban = re.search(r"Alıcı\s+IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
        if m_a_iban:
            self.data["aliciiban"] = m_a_iban.group(1).replace(" ", "").strip()[:26]

        m_g_iban = re.search(r"(?<!Alıcı\s)IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
        if m_g_iban:
            self.data["gondereniban"] = m_g_iban.group(1).replace(" ", "").strip()[:26]

        return self.finalize()
