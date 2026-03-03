# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class IngParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "ing")

    def parse(self):
        raw = self.text
        up = to_turkish_upper(raw)
        
        # 1. Tür Tespiti
        if "MAAŞ" in up: self.data["is_maas"] = True
        self.data["is_giden"] = True
        
        # 2. Tarih Yakalama (Örn: İşlem Tarihi : 27/02/2026)
        m_date = re.search(r"İŞLEM\s*TARİHİ\s*[:\-]?\s*(\d{2}[./]\d{2}[./]\d{4})", raw, re.I)
        if m_date: self.data["islemtarihi"] = m_date.group(1).replace("/", ".")
        
        # 3. Tutar Yakalama (Örn: İŞLEM TUTARI : 9,826.42 TL)
        m_tutar = re.search(r"İŞLEM\s*TUTARI\s*:\s*([\d\.,]+)", raw, re.I)
        if m_tutar:
            # ING dekontunda virgül binlik ayırıcı ise onu temizleyip parse ediyoruz
            val = m_tutar.group(1).replace(",", "")
            self.data["tutar"] = float(val)

        # 4. Gönderen (SAYIN ifadesinden sonra gelen kurum adı)
        m_g = re.search(r"SAYIN\s+([^\n]+)", raw, re.I)
        if m_g: self.data["gonderen"] = m_g.group(1).strip()

        # 5. Alıcı ve İsim Düzenleme (SOYİSİM İSİM -> İSİM SOYİSİM)
        m_a = re.search(r"HESAP\s*:\s*([A-ZÇĞİÖŞÜ ]+)", raw, re.I)
        if m_a:
            tam_isim = m_a.group(1).strip()
            parcalar = tam_isim.split()
            if len(parcalar) >= 2:
                # 'ÖZEN FATİH' -> 'FATİH ÖZEN'
                # Son parçayı (Fatih) başa al, ilk parçayı (Özen) sona koy
                soyisim = parcalar[0]
                isim = " ".join(parcalar[1:])
                self.data["alici"] = f"{isim} {soyisim}"
            else:
                self.data["alici"] = tam_isim

        # 6. IBAN
        m_iban = re.search(r"IBAN:\s*(TR[0-9 ]+)", raw, re.I)
        if m_iban: self.data["aliciiban"] = m_iban.group(1).replace(" ", "").strip()
        
        return self.finalize()