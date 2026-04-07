# -*- coding: utf-8 -*-
import re
import unicodedata
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class TebParser(BaseParser):
    def __init__(self, text):
        normalized_text = unicodedata.normalize("NFKC", text)
        super().__init__(normalized_text, "teb")

    def parse(self):
        t = self.text
        TU = self.up

        # 1. Tür tespiti
        if re.search(r"\bHAVALE\b", TU): self.data["is_havale"] = True
        if re.search(r"\bEFT\b", TU): self.data["is_eft"] = True
        if re.search(r"\bMAAŞ\b|\bMAAS\b", TU): self.data["is_maas"] = True
        if re.search(r"\bGELEN\b", TU): self.data["is_gelen"] = True
        if re.search(r"\bGÖNDERILEN\b|\bGONDERILEN\b|\bGİDEN\b", TU): self.data["is_giden"] = True

        # 2. Tarih
        m_date = re.search(r"Tarih[- ]Saat:\s*([0-9]{2}[./][0-9]{2}[./][0-9]{4})", t, flags=re.I)
        if m_date:
            self.data["islemtarihi"] = m_date.group(1).replace("/", ".")

        # 3. Tutar (eksi varsa temizle)
        m_tutar = re.search(r"TL\s*([0-9\.,]+)-?", t)
        if m_tutar:
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 4. Gönderen (Hesap Sahibi)
        m_gonderen = re.search(r"Hesap Sahibi:\s*([^\n\r]+)", t, flags=re.I)
        if m_gonderen:
            self.data["gonderen"] = m_gonderen.group(1).strip()

        # 5. Gönderen IBAN
        m_g_ib = re.search(r"IBAN:\s*(TR[0-9 ]+)", t, flags=re.I)
        if m_g_ib:
            self.data["gondereniban"] = m_g_ib.group(1).replace(" ", "")

        # 6. Alıcı
        m_alici = re.search(r"Alacaklı Adı:\s*([^\n\r]+)", t, flags=re.I)
        if m_alici:
            self.data["alici"] = m_alici.group(1).strip()

        # 7. Alıcı IBAN
        m_a_ib = re.search(r"Alacaklı Hesap:\s*(TR[0-9 ]+)", t, flags=re.I)
        if m_a_ib:
            self.data["aliciiban"] = m_a_ib.group(1).replace(" ", "")

        # 8. Açıklama
        m_aciklama = re.search(r"Açıklama:\s*([^\n\r]+)", t, flags=re.I)
        if m_aciklama:
            self.data["aciklama"] = m_aciklama.group(1).strip()

        # 9. Banka adı (net set)
        self.data["banka"] = "teb"

        # 10. Final temizlik
        self.data["gonderen"] = to_turkish_upper(self.data.get("gonderen", ""))
        self.data["alici"] = to_turkish_upper(self.data.get("alici", ""))

        return self.finalize()
