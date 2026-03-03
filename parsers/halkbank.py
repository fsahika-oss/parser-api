# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import parse_amount

class HalkbankParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "halkbank")

    def parse(self):
        raw = self.text
        up = self.up
        if "FAST" in up: self.data["is_fast"] = True
        if "PARA TRANSFERİ" in up or "HAVALE" in up: self.data["is_havale"] = True
        
        m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}/\d{2}/\d{4})", raw)
        if m: self.data["islemtarihi"] = m.group(1).replace("/", ".")
        
        # m = re.search(r"İŞLEM TUTARI\s*\(TL\)\s*:\s*([\d\.,]+)", raw, re.I)
        # if m: self.data["tutar"] = parse_amount(m.group(1))

        # Daha esnek tutar yakalama (Halkbank varyasyonları için)
        # 1. Seçenek: İŞLEM TUTARI (TL) : 1.000,00
        m = re.search(r"İŞLEM\s*TUTARI\s*(?:\(TL\))?\s*[:\-]?\s*([\d\.,]+)", raw, re.I)      
        # 2. Seçenek (Eğer yukarıdaki bulamazsa): Sadece tutar ve TL yan yanaysa
        if not m:
            m = re.search(r"([\d\.,]+)\s*TL", raw, re.I)            
        if m:
            self.data["tutar"] = parse_amount(m.group(1))        

        m = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw)
        if m: self.data["gonderen"] = m.group(1).strip()

        m = re.search(r"GÖNDEREN IBAN\s*:\s*(TR[0-9 ]+)", raw)
        if m: self.data["gondereniban"] = m.group(1).replace(" ", "")        
        
        m = re.search(r"ALICI\s*:\s*([^\n]+)", raw)
        if m: self.data["alici"] = m.group(1).strip()

        m = re.search(r"ALICI IBAN\s*:\s*(TR[0-9 ]+)", raw)
        if m: self.data["aliciiban"] = m.group(1).replace(" ", "")        
        
        return self.finalize()
