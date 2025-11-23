from fastapi import FastAPI, UploadFile, File
import subprocess
import tempfile
import os

app = FastAPI()

@app.post("/parse")
async def parse_file(file: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    cmd = ["python3", "dekontlar_parser.py", temp_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "stdout": result.stdout,
        "stderr": result.stderr
    }
