from fastapi import FastAPI, UploadFile, File
import tempfile
import os
from main import parse_dekont 

app = FastAPI()

@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        # Yeni kurguladığımız main.py'deki fonksiyonu çağırıyoruz
        result = parse_dekont(tmp_path)
    except Exception as e:
        result = {"error": str(e)}
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return result

@app.get("/")
def home():
    return {"status": "API modular system alive", "endpoint": "/parse"}
