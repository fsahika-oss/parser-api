import re
import unicodedata
import os

def to_turkish_upper(text):
    if not text: return text
    mapping = {"i": "İ", "ı": "I", "ğ": "Ğ", "ü": "Ü", "ş": "Ş", "ö": "Ö", "ç": "Ç"}
    return "".join(mapping.get(c, c.upper()) for c in text)

def normalize_text(t):
    if not t: return ""
    t = unicodedata.normalize("NFKC", t)
    t = t.replace("\u00A0", " ")
    return re.sub(r"[ \t]+", " ", t).strip()

def parse_amount(s):
    if not s:
        return None

    s = str(s).strip()

    # Para dışı karakterleri temizle
    s = re.sub(r"[^\d,.\-]", "", s)

    if not s:
        return None

    # negatif kontrol
    neg = s.startswith("-")
    if neg:
        s = s[1:]

    # hem nokta hem virgül varsa
    if "," in s and "." in s:
        # hangisi en sonda ise ondalık odur
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    # sadece virgül varsa
    elif "," in s:
        parts = s.split(",")
        if len(parts[-1]) == 2:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    # sadece nokta varsa
    elif "." in s:
        parts = s.split(".")
        if len(parts[-1]) == 2:
            s = s.replace(",", "")
        else:
            s = s.replace(".", "")

    try:
        val = float(s)
        return -val if neg else val
    except:
        return None

def dbg(msg):
    log_path = os.path.join(os.path.dirname(__file__), "parser_debug.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
