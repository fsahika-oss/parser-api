from fastapi import FastAPI, UploadFile, File
import tempfile
import os
from dekontlar_parser import parse_dekont

app = FastAPI()

@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    # PDF'i geçici dizine kaydet
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Parser çalıştır
    try:
        result = parse_dekont(tmp_path)
    except Exception as e:
        return {"error": str(e)}

    # Geçici dosya sil
    os.remove(tmp_path)

    return result

@app.get("/")
def home():
    return {"status": "API alive", "endpoint": "/parse"}
