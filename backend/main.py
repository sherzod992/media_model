from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import base64
import uuid
import logging
from pathlib import Path
from final_inference import run

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="MediAI-FX Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def get_base64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "MediAI-FX Backend"}

def _safe_upload_suffix(filename: str) -> str:
    """ASCII 경로로 저장해 Linux 컨테이너 등에서 이미지 I/O 불일치 방지."""
    ext = Path(filename or "").suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"):
        ext = ".jpg"
    return ext


@app.post("/api/analyze")
async def analyze_xray(files: list[UploadFile] = File(...)):
    paths = []
    for file in files:
        file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{_safe_upload_suffix(file.filename)}"
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        paths.append(str(file_path))
    
    results = run(paths)
    
    for r in results:
        try:
            r["original_base64"] = get_base64(r["file"])
            if "heatmap_path" in r and os.path.exists(r["heatmap_path"]):
                r["heatmap_base64"] = get_base64(r["heatmap_path"])
        except Exception as e:
            log.warning("Base64 인코딩 실패: %s", e, exc_info=True)
    
    # cleanup
    for p in paths:
        try:
            os.remove(p)
            if os.path.exists(p + "_heatmap.jpg"):
                os.remove(p + "_heatmap.jpg")
        except:
            pass
            
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
