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
        
        # 1. Tür Tespiti
        if "MAAŞ" in up or "MAAS" in up: self.data["is_maas"] = True
        if "FAST" in up: self.data["is_fast"] = True
        if "HVL" in up or "EFT" in up: self.data["is_havale"] = True
        self.data["is_giden"] = True

        # 2. Tutar Yakalama (Hatasız)
        # Sadece rakam ve ayırıcılardan oluşan, TRY/TL öncesindeki kısmı alıyoruz
        m_tutar = re.search(r"(?:İşlem\s+)?Tutar(?:ı)?\s*:\s*([\d\.,]+)", raw, re.I)
        if m_tutar:
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. Tarih Yakalama
        m_date = re.search(r"Dekont\s*Tarihi\s*:\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
        if m_date: self.data["islemtarihi"] = m_date.group(1)

        # 4. Gönderen Yakalama
        if "Gönderici İsim/Ünvan" in raw:
            # Maaş Dekontu Formatı
            m_g = re.search(r"Gönderici\s+İsim/Ünvan\s*:\s*(.+)", raw, re.I)
            if m_g: self.data["gonderen"] = m_g.group(1).strip()
        else:
            # e-Dekont Formatı (Doküman Numarasından sonraki satırın sol tarafı)
            m_g = re.search(r"Doküman\s+Numarası\s*:\s*\d+\s*\n(.+?)(?=İşlem Yeri|$)", raw, re.I | re.S)
            if m_g: self.data["gonderen"] = m_g.group(1).strip()

        # 5. ALICI YAKALAMA (Hibrit ve Kesin)
        # Regex Açıklaması: Alıcı kelimesinden sonra İsim/Unvan veya Isim\Unvan gelirse sonuna kadar al
        m_alici = re.search(r"Alıcı\s+(?:Isim\\Unvan|İsim\s*/Ünvan)\s*:\s*(.+)", raw, re.I)
        if m_alici:
            alici_val = m_alici.group(1).strip()
            # Eğer satırın sonunda başka bir şey varsa (Açıklama vb.) temizlemek için:
            self.data["alici"] = alici_val.split("Açıklama")[0].strip()

        # 6. IBAN'LAR
        # Alıcı IBAN (Sadece TR ile başlayan kısmı cımbızla çeker)
        m_a_iban = re.search(r"Alıcı\s+IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
        if m_a_iban:
            self.data["aliciiban"] = m_a_iban.group(1).replace(" ", "").strip()[:26]

        # Gönderen IBAN (Başında 'Alıcı' olmayan ilk IBAN etiketi)
        m_g_iban = re.search(r"(?<!Alıcı\s)IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
        if m_g_iban:
            self.data["gondereniban"] = m_g_iban.group(1).replace(" ", "").strip()[:26]

        return self.finalize()