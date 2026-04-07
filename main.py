import pdfplumber
import re
from utils import normalize_text, dbg

from parsers.enpara import EnparaParser
from parsers.garanti import GarantiParser
from parsers.vakif import VakifBankParser
from parsers.yapikredi import YapiKrediParser
from parsers.ziraat import ZiraatParser
from parsers.akbank import AkbankParser
from parsers.isbank import IsBankParser
from parsers.denizbank import DenizbankParser
from parsers.halkbank import HalkbankParser
from parsers.ing import IngParser
from parsers.kuveytturk import KuveytTurkParser
from parsers.vakifkatilim import VakifKatilimParser
from parsers.generic import GenericParser

def extract_text(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            p = page.extract_text()
            if p:
                text += p + "\n"
    return normalize_text(text)

def banka_tespit(text):
    # 1. Metni satırlara böl
    lines = text.split('\n')



    # 🔥 YENİ: HEADER (ilk 10 satır) kontrolü
    head_lines = lines[:10]
    head_text = "\n".join(head_lines).upper()
    
    # HEADER bazlı güçlü tespit
    if "VAKIFBANK" in head_text:
        return "vakif"
    if "GARANTI" in head_text or "GARANTİ" in head_text:
        return "garanti"
    if "ZIRAAT" in head_text or "ZİRAAT" in head_text:
        return "ziraat"
    if "AKBANK" in head_text:
        return "akbank"
    if "YAPI KREDI" in head_text or "YAPIKREDI" in head_text:
        return "yapikredi"
    if "IS BANKASI" in head_text or "İŞ BANKASI" in head_text:
        return "isbank"
    if "ENPARA" in head_text or "QNB" in head_text:
        return "enpara"
    if "KUVEYT" in head_text:
        return "kuveytturk"
    if "HALKBANK" in head_text:
        return "halkbank"
    if "ING" in head_text:
        return "ing"
    if "VAKIF KATILIM" in head_text or "VAKIFKATILIM" in head_text:
        return "vakifkatilim"





    
    # 2. Yanıltıcı satırları (AlıcıBanka gibi) temizle
    # Boşluksuz kontrol yaparak "AlıcıBanka" ve "Alıcı Banka" versiyonlarını eliyoruz.
    filtered_lines = []
    for line in lines:
        line_up_no_space = line.upper().replace(" ", "")
        if any(x in line_up_no_space for x in ["ALICIBANKA", "ALICI BANKA", "ALICI", "KATILIMCI"]):
            continue
        filtered_lines.append(line)
    
    clean_text = "\n".join(filtered_lines)
    up = clean_text.upper()
    
    # Senin eski kodundaki tespit mantığının özeti:
    if "KUVEYT" in up: 
        return "kuveytturk"    
    if "WWW. ZIRAATBANK.COM.TR" in up or  "T.C. ZİRAAT BANKASI A.Ş." in up or "ZİRAAT MOBİL" in up:
        return "ziraat"     
    if "WWW.ISBANK.COM.TR" in up or "İŞCEP" in up or "ISCEP" in up or "TÜRKİYE İŞ BANKASI A.Ş." in up:
        return "isbank"     
    if "DENIZBANK" in up or "DENİZBANK" in up or "DENIZ GAYRIMENKUL" in up:
        return "denizbank"     
    if any(x in up for x in ["ENPARA", "FINANSBANK", "FİNANSBANK", "QNB"]):
        return "enpara"
    if "WWW.GARANTIBBVA.COM.TR" in up or "T. GARANTİ BANKASI A.Ş." in up or "GARANTI" in up or "GARANTİ" in up:
        return "garanti"  
    if "VAKIFBANK" in up or "TÜRKİYE VAKIFLAR BANKASI T.A.O" in up or "WWW.VAKIFBANK.COM.TR" in up or "SİCİL NUMARASI: 776444" in up:
        return "vakif"     
    if "WWW.YAPIKREDI.COM.TR" in up or "YAPI VE KREDİ BANKASI A.Ş." in  up or "MERSIS NO: 0937002089200741" in up:
        return "yapikredi"   
    if "4560004685" in up or "0456000468500132" in up or "HALKBANK.COM.TR" in up:
        return "halkbank" 
    if "ZIRAATBANK" in up or "ZİRAAT BANKASI" in up or "ZIRAAT MOBIL" in up:
        return "ziraat"       
    if "WWW. ING.COM.TR" in up or "ING BANK A.Ş." in up: 
        return "ing"    
    if any(x in up for x in ["VAKIF KATILIM", "VAKIFKATILIM"]): 
        return "vakifkatilim"       
    if ("AKBANK" in up or "AKBANK T.A.Ş" in up or "WWW.AKBANK.COM" 
        or "GENEL MÜDÜRLÜK: SABANCI CENTER" in up or "VERGİ NO: 0150015264" in up):
        return "akbank"    
               
    # Diğer banka tespitlerini (Garanti, Vakıf vb.) buraya sırayla ekleyeceğiz
    return "bilinmiyor"

def parse_dekont(filepath):
    text = extract_text(filepath)
    banka_key = banka_tespit(text)
    
    # Parser eşleştirme sözlüğü
    parsers = {
        "enpara": EnparaParser,
        "garanti": GarantiParser,
        "vakif": VakifBankParser,
        "yapikredi": YapiKrediParser,
        "ziraat": ZiraatParser,
        "akbank": AkbankParser,
        "isbank": IsBankParser,
        "denizbank": DenizbankParser,
        "halkbank": HalkbankParser,
        "ing": IngParser,
        "kuveytturk": KuveytTurkParser,
        "vakifkatilim": VakifKatilimParser,  
        "bilinmiyor": GenericParser      
    }
    
    parser_class = parsers.get(banka_key)
    if parser_class:
        instance = parser_class(text)
        return instance.parse()
    
    return {
        "banka": banka_key, 
        "_debug": "parser_dosyasi_henuz_yok",
        "raw_preview": text[:200]
    }
