from utils import to_turkish_upper

class BaseParser:
    def __init__(self, text, bank_name):
        self.text = text
        self.up = text.upper()
        self.data = {
            "banka": bank_name, "is_fast": False, "is_havale": False, "is_maas": False,
            "is_gelen": False, "is_giden": False, "gonderen": "", "gondereniban": "",
            "alici": "", "aliciiban": "", "tutar": "", "islemtarihi": "",
            "_debug_raw": text[:500]
        }

    def finalize(self):
        self.data["gonderen"] = to_turkish_upper(self.data.get("gonderen", ""))
        self.data["alici"] = to_turkish_upper(self.data.get("alici", ""))
        return self.data
