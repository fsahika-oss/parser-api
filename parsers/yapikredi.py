# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount, to_turkish_upper

class YapiKrediParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "yapikredi")

    def parse(self):
        raw = self.text
        lines = raw.split('\n')
        clean_raw = raw.replace("\n", "  ").replace("\t", " ")
        up = to_turkish_upper(clean_raw)

        # 🎯 YENİ FORMAT: HESAPTAN HESABA HAVALE-BORÇ (2026 e-dekont)
        if "HESAPTAN HESABA HAVALE-BORÇ" in up:

            self.data["is_giden"] = True

            # tutar
            m_t = re.search(r"ISLEM TUTARI\s*:\s*-?([\d\.,]+)", clean_raw, re.I)
            if m_t:
                self.data["tutar"] = parse_amount(m_t.group(1))

            # tarih
            m_dt = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}\.\d{2}\.\d{4})", clean_raw, re.I)
            if m_dt:
                self.data["islemtarihi"] = m_dt.group(1)

            # gönderen (footer’dan kesin yakalama)
            m_g = re.search(r"\n([A-ZÇĞİÖŞÜ\s]+)\s+Ticari Unvan", raw, re.I)
            if m_g:
                self.data["gonderen"] = to_turkish_upper(m_g.group(1).strip())

            # alıcı (net alan var)
            m_a = re.search(r"ALACAKLI ADI\s*:\s*([^\n\r]+)", raw, re.I)
            if m_a:
                self.data["alici"] = to_turkish_upper(m_a.group(1).strip())

            # IBAN
            m_gi = re.search(r"IBAN NO\s*:\s*(TR[0-9 ]+)", clean_raw, re.I)
            if m_gi:
                self.data["gondereniban"] = m_gi.group(1).replace(" ", "")[:26]

            m_ai = re.search(r"ALACAKLI HESAP\s*:[^:]*IBAN\s*:\s*(TR[0-9 ]+)", clean_raw, re.I)
            if m_ai:
                self.data["aliciiban"] = m_ai.group(1).replace(" ", "")[:26]

            return self.finalize()

        # --- BURADAN AŞAĞISI SENİN ESKİ KODUN ---
        if "MAAŞ ÖDEME RAPORU" in up or "FIRMA ÜNVANI" in up:
            self.data["is_maas"] = True
            self.data["is_giden"] = True
            
            m_firma = re.search(r"Firma Ünvanı\s*:\s*([^\n\r]+)", raw, re.I)
            if m_firma: self.data["gonderen"] = to_turkish_upper(m_firma.group(1).strip())
            
            for line in lines:
                if "ÖDENDİ" in line.upper() or "ÖDEMESİ" in line.upper():
                    m_val = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                    if m_val: self.data["tutar"] = parse_amount(m_val.group(1))
                    
                    m_dt = re.search(r"(\d{2}/\d{2}/\d{4})", line)
                    if m_dt: self.data["islemtarihi"] = m_dt.group(1).replace("/", ".")
                    
                    m_name = re.search(r"TL\s+([A-ZÇĞİÖŞÜ\s]+?)\s+\d+", line, re.I)
                    if m_name: self.data["alici"] = to_turkish_upper(m_name.group(1).strip())
            
            return self.finalize()

        # --- STANDART DEKONT ---
        if "FAST" in up: self.data["is_fast"] = True
        if "EFT" in up: self.data["is_eft"] = True
        if "MAAŞ" in up or "MAAS" in up: self.data["is_maas"] = True
        
        if "ALACAK DEKONTU" in up or "ÖDEME YAPAN" in up:
            self.data["is_gelen"] = True
            self.data["is_giden"] = False
        else:
            self.data["is_giden"] = True

        m_date = re.search(r"İŞLEM\s*TARİHİ\s*:\s*(\d{2}\.\d{2}\.\d{4})", clean_raw, re.I)
        if m_date: self.data["islemtarihi"] = m_date.group(1)

        m_tutar = re.search(r"TUTARI?\s*:\s*(-?[\d\.,]+)", clean_raw, re.I)
        if m_tutar:
            val = m_tutar.group(1).replace("-", "").strip()
            self.data["tutar"] = parse_amount(val)

        m_g1 = re.search(r"GÖNDEREN\s*ADI\s*:\s*(.+?)(?=\s*ÖDEMENİN|\s*ALICI|$)", clean_raw, re.I)
        m_g2 = re.search(r"ÖDEME\s*YAPAN\s*İSİM/ÜNVAN\s*:\s*(.+?)(?=\s*YUKARIDAKİ|$)", clean_raw, re.I)
        self.data["gonderen"] = to_turkish_upper((m_g1.group(1) if m_g1 else m_g2.group(1) if m_g2 else "").strip())

        m_a1 = re.search(r"ALICI\s*ADI\s*:\s*(.+?)(?=\s*ALICI\s*TCKN|\s*AÇIKLAMA|$)", clean_raw, re.I)
        m_a2 = re.search(r"AÇIKLAMA:.*?/\s*([A-ZÇĞİÖŞÜ\s]+?)(?=\s*Ticari\s*Unvan|$)", clean_raw, re.I)
        self.data["alici"] = to_turkish_upper((m_a1.group(1) if m_a1 else m_a2.group(1) if m_a2 else "").strip())

        m_sender_iban = re.search(r"GÖNDEREN\s+HESAP\s+NO\s*:[^:]*IBAN\s*:\s*(TR[0-9 ]+)", clean_raw, re.I)
        m_receiver_iban = re.search(r"ALICI\s+HESAP\s*:\s*(TR[0-9 ]+)", clean_raw, re.I)

        if m_sender_iban:
            self.data["gondereniban"] = m_sender_iban.group(1).replace(" ", "").strip()[:26]
        if m_receiver_iban:
            self.data["aliciiban"] = m_receiver_iban.group(1).replace(" ", "").strip()[:26]

        if not self.data["is_giden"]:
            current_ibans = re.findall(r"TR[0-9 ]{20,34}", clean_raw)
            if current_ibans:
                self.data["gondereniban"] = current_ibans[0].replace(" ", "").strip()[:26]
                self.data["aliciiban"] = ""

        return self.finalize()
