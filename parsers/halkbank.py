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

        if "FAST" in up:
            self.data["is_fast"] = True
        if "PARA TRANSFERİ" in up or "HAVALE" in up:
            self.data["is_havale"] = True

        # --- Tarih ---
        m = re.search(r"İŞLEM TARİHİ\s*:\s*(\d{2}/\d{2}/\d{4})", raw)
        if m:
            self.data["islemtarihi"] = m.group(1).replace("/", ".")

        # --- Tutar ---
        m = re.search(r"İŞLEM\s*TUTARI\s*(?:\(TL\))?\s*[:\-]?\s*([\d\.,]+)", raw, re.I)
        if not m:
            m = re.search(r"([\d\.,]+)\s*TL", raw, re.I)

        if m:
            self.data["tutar"] = parse_amount(m.group(1))

        # --- Gönderen ---
        m = re.search(r"GÖNDEREN\s*:\s*([^\n]+)", raw)
        if m:
            self.data["gonderen"] = m.group(1).strip()

        # --- Gönderen IBAN ---
        m = re.search(r"GÖNDEREN IBAN\s*:\s*(TR[0-9 ]+)", raw)
        if m:
            self.data["gondereniban"] = m.group(1).replace(" ", "")

        # --- Alıcı ---
        m = re.search(r"ALICI\s*:\s*([^\n]+)", raw)
        if m:
            self.data["alici"] = m.group(1).strip()

        # --- Alıcı IBAN ---
        m = re.search(r"ALICI IBAN\s*:\s*(TR[0-9 ]+)", raw)
        if m:
            self.data["aliciiban"] = m.group(1).replace(" ", "")

        # ======================================================
        # YENİ HALKBANK DEKONT FORMATLARI (AMİR / LEHDAR)
        # ======================================================

        # IBAN'ları sırayla yakala
        ibans = re.findall(r"IBAN\s*:\s*(TR[0-9 ]+)", raw)

        if ibans:
            if not self.data["gondereniban"]:
                self.data["gondereniban"] = ibans[0].replace(" ", "")
            if len(ibans) > 1 and not self.data["aliciiban"]:
                self.data["aliciiban"] = ibans[1].replace(" ", "")

        # LEHDAR → alıcı
        if not self.data["alici"]:
            m = re.search(r"LEHDAR\s*:\s*\d+\s*\n([^\n]+)", raw)
            if m:
                name = m.group(1).strip()
                name = re.sub(r"^\d+\s+", "", name)   # baştaki sayıyı sil
                self.data["alici"] = name

        # AMİR → gönderen
        if not self.data["gonderen"]:
            m = re.search(r"AM[İIıi]R\s*:[^\n]*\n([^\n]+)", raw)
            if m:
                line = m.group(1).strip()

                # baştaki müşteri numarasını sil
                line = re.sub(r"^\d+\s+", "", line)

                # sondaki şube kodunu sil
                line = re.sub(r"\s+\d{3,}$", "", line)

                self.data["gonderen"] = line

        # TOPLAM satırından tutar fallback
        if not self.data["tutar"]:
            m = re.search(r"TOPLAM\s+([\d\.,]+)", raw)
            if m:
                self.data["tutar"] = parse_amount(m.group(1))

        # Tarih fallback
        if not self.data["islemtarihi"]:
            m = re.search(r"Tarih\s*:\s*(\d{2}/\d{2}/\d{4})", raw)
            if m:
                self.data["islemtarihi"] = m.group(1).replace("/", ".")

        return self.finalize()
