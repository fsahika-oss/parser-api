# -*- coding: utf-8 -*-
import re
from parsers.base import BaseParser
from utils import dbg, parse_amount, to_turkish_upper

class AkbankParser(BaseParser):
    def __init__(self, text):
        super().__init__(text, "akbank")

    def parse(self):
        raw = self.text
        up = self.up

        # 1. Tür Tespiti
        if "MAAŞ ÖDEMESİ" in up or "MAAS ODEMESI" in up:
            self.data["is_maas"] = True
        self.data["is_giden"] = True

        # 2. Tarih ve Tutar
        m = re.search(r"İşlem Tarihi/Saati\s*:\s*(\d{2}\.\d{2}\.\d{4})", raw, re.I)
        if m: self.data["islemtarihi"] = m.group(1)

        m = re.search(r"TOPLAM\s*([\d\.,]+)\s*TL", raw, re.I)
        if m: self.data["tutar"] = parse_amount(m.group(1))

        # 3. İsim Algoritması (Senin özel mantığın)
        lines = raw.split("\n")
        for i, ln in enumerate(lines):
            if "Adı Soyadı/Unvan" in ln or "Adi Soyadi/Unvan" in ln:
                parts = re.split(r"Adı Soyadı/Unvan\s*:", ln, flags=re.I)
                parts = [p.strip() for p in parts if p.strip()]

                if len(parts) == 1:
                    sender = parts[0]
                    # Alt satır kontrolü (Şirket ünvanı devamı mı?)
                    if i+1 < len(lines):
                        nxt = lines[i+1].strip()
                        if nxt and not nxt.startswith(("Adres", "TR", "ÜRN", "Hesap")):
                            sender += " " + nxt
                    self.data["gonderen"] = sender

                elif len(parts) == 2:
                    sender, receiver = parts[0], parts[1]
                    if i+1 < len(lines):
                        nxt = lines[i+1].strip()
                        if nxt and not nxt.startswith(("Adres", "TR", "ÜRN", "Hesap")):
                            sender += " " + nxt
                    self.data["gonderen"] = sender
                    self.data["alici"] = receiver

        # 4. IBAN Yakalama
        raw_clean = raw.replace("\n", " ")
        ibans = [re.sub(r"\s+", "", x) for x in re.findall(r"(TR[0-9][0-9\s]{20,34})", raw_clean, flags=re.I)]
        if len(ibans) >= 1: self.data["gondereniban"] = ibans[0]
        if len(ibans) >= 2: self.data["aliciiban"] = ibans[1]

        return self.finalize()
