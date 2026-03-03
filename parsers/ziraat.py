# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class ZiraatParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "ziraat")

    def parse(self):
        raw = self.text
        up = self.up

        # 1. Tür Tespiti
        is_fast = "HESAPTAN FAST" in up or "FAST İŞLEMİ" in up
        is_havale = "HESAPTAN HESABA HAVALE" in up or "HAVALE TUTARI" in up
        
        # 2. Tarih ve Tutar (Format Düzeltmeli)
        m_date = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}[./]\d{2}[./]\d{4})", raw, re.I)
        if m_date:
            # 31/10/2025 -> 31.10.2025 dönüşümü
            self.data["islemtarihi"] = m_date.group(1).replace("/", ".")

        # Tutar yakalama (Havale vs FAST etiket farkı)
        t_label = "Havale Tutarı" if is_havale else "İşlem Tutarı"
        m_tutar = re.search(rf"{t_label}\s*:\s*([\d\.,]+)", raw, re.I)
        if m_tutar: 
            self.data["tutar"] = parse_amount(m_tutar.group(1))

        # 3. GÖNDEREN BİLGİLERİ (Şube Kodunun Altındaki IBAN)
        # Ziraat'te gönderen IBAN her zaman belgenin üst bloğundaki 'IBAN :' etiketindedir.
        m_gib = re.search(r"IBAN\s*:\s*(TR[0-9 ]{20,34})", raw, re.I)
        if m_gib:
            self.data["gondereniban"] = m_gib.group(1).replace(" ", "").strip()[:26]

        # Gönderen İsim (Şube adının yanındaki unvan)
        if is_havale:
            lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
            for ln in lines:
                if "ŞUBE KODU/ADI" in ln.upper() and "ŞUBESİ" in ln.upper():
                    self.data["gonderen"] = ln.upper().split("ŞUBESİ", 1)[1].strip()
                    break
        else:
            m_g = re.search(r"Gönderen\s*:\s*([^\n\r]+)", raw, re.I)
            if m_g: self.data["gonderen"] = m_g.group(1).strip()

        # 4. ALICI BİLGİLERİ (Alacaklı IBAN Etiketi)
        if is_havale:
            # Havale dekontu: Alacaklı Adı Soyadı ve Alacaklı IBAN
            m_alici = re.search(r"Alacaklı Adı Soyadı\s*:\s*([^\n\r]+)", raw, re.I)
            if m_alici: self.data["alici"] = m_alici.group(1).strip()
            
            m_aib = re.search(r"Alacaklı IBAN\s*:\s*(TR[0-9 ]+)", raw, re.I)
            if m_aib: self.data["aliciiban"] = m_aib.group(1).replace(" ", "").strip()[:26]
        else:
            # FAST dekontu: Alıcı ve Alıcı Hesap etiketleri
            m_alici = re.search(r"Alıcı\s*:\s*([^\n\r/]+)", raw, re.I)
            if m_alici: self.data["alici"] = m_alici.group(1).strip()
            
            m_aib = re.search(r"Alıcı Hesap\s*:\s*(TR[0-9 ]+)", raw, re.I)
            if m_aib: self.data["aliciiban"] = m_aib.group(1).replace(" ", "").strip()[:26]

        return self.finalize()