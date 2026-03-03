# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class YapiKrediParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "yapikredi")

    def parse(self):
        raw = self.text
        # Satır sonlarını boşluğa çevirerek etiket aramayı garantiye alıyoruz
        clean_raw = raw.replace("\n", "  ").replace("\t", " ")
        up = to_turkish_upper(clean_raw)

        # 1. Tür ve Yön Tespiti
        if "FAST" in up: self.data["is_fast"] = True
        if "EFT" in up: self.data["is_eft"] = True
        if "MAAŞ" in up or "MAAS" in up: self.data["is_maas"] = True
        
        if "ALACAK DEKONTU" in up or "ÖDEME YAPAN" in up:
            self.data["is_gelen"] = True
            self.data["is_giden"] = False
        else:
            self.data["is_giden"] = True

        # 2. Tarih Yakalama
        m_date = re.search(r"İŞLEM\s*TARİHİ\s*:\s*(\d{2}\.\d{2}\.\d{4})", clean_raw, re.I)
        if m_date: self.data["islemtarihi"] = m_date.group(1)

        # 3. Tutar Yakalama
        m_tutar = re.search(r"TUTARI?\s*:\s*(-?[\d\.,]+)", clean_raw, re.I)
        if m_tutar:
            val = m_tutar.group(1).replace("-", "").strip()
            self.data["tutar"] = parse_amount(val)

        # 4. İsimleri Yakalama
        # Gönderen
        m_g1 = re.search(r"GÖNDEREN\s*ADI\s*:\s*(.+?)(?=\s*ÖDEMENİN|\s*ALICI|$)", clean_raw, re.I)
        m_g2 = re.search(r"ÖDEME\s*YAPAN\s*İSİM/ÜNVAN\s*:\s*(.+?)(?=\s*YUKARIDAKİ|$)", clean_raw, re.I)
        self.data["gonderen"] = to_turkish_upper((m_g1.group(1) if m_g1 else m_g2.group(1) if m_g2 else "").strip())

        # Alıcı
        m_a1 = re.search(r"ALICI\s*ADI\s*:\s*(.+?)(?=\s*ALICI\s*TCKN|\s*AÇIKLAMA|$)", clean_raw, re.I)
        m_a2 = re.search(r"AÇIKLAMA:.*?/\s*([A-ZÇĞİÖŞÜ\s]+?)(?=\s*Ticari\s*Unvan|$)", clean_raw, re.I)
        self.data["alici"] = to_turkish_upper((m_a1.group(1) if m_a1 else m_a2.group(1) if m_a2 else "").strip())

        # 5. IBAN Yakalama (Etiket Bazlı Kesin Çözüm)
        # Giden FAST dekontu için etiketlerden çek
        m_sender_iban = re.search(r"GÖNDEREN\s+HESAP\s+NO\s*:[^:]*IBAN\s*:\s*(TR[0-9 ]+)", clean_raw, re.I)
        m_receiver_iban = re.search(r"ALICI\s+HESAP\s*:\s*(TR[0-9 ]+)", clean_raw, re.I)

        if m_sender_iban:
            self.data["gondereniban"] = m_sender_iban.group(1).replace(" ", "").strip()[:26]
        if m_receiver_iban:
            self.data["aliciiban"] = m_receiver_iban.group(1).replace(" ", "").strip()[:26]

        # Maaş/Alacak Dekontu (Gelen) için özel kural
        if not self.data["is_giden"]:
            # Eğer alıcı IBAN doluysa ama gönderen boşsa (Maaş dekontunda genelde tek IBAN olur)
            # Senin sistem kurgun için o tek IBAN'ı gönderene çekip alıcıyı boşaltıyoruz.
            current_ibans = re.findall(r"TR[0-9 ]{20,34}", clean_raw)
            if current_ibans:
                self.data["gondereniban"] = current_ibans[0].replace(" ", "").strip()[:26]
                self.data["aliciiban"] = ""

        return self.finalize()