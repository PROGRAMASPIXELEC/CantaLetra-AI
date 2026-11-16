from pathlib import Path
from uuid import uuid4
import json, os, shutil, subprocess

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
FRONTEND = BASE.parent / "frontend"
DATA = Path(os.getenv("UPLOAD_DIR", str(BASE / "data"))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "80"))
ALLOWED = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}

app = FastAPI(title="CantaLetra AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

class LyricsProject(BaseModel):
    track_id: str
    title: str = "Mi canción"
    original_lyrics: str = ""
    new_lyrics: str = ""
    consent_confirmed: bool = False

def track_dir(track_id: str) -> Path:
    if not track_id.isalnum():
        raise HTTPException(400, "Identificador inválido")
    folder = DATA / track_id
    if not folder.exists():
        raise HTTPException(404, "Proyecto no encontrado")
    return folder

@app.get("/", response_class=HTMLResponse)
def home():
    return (FRONTEND / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"ok": True, "app": "CantaLetra AI",
            "demucs": shutil.which("demucs") is not None,
            "ffmpeg": shutil.which("ffmpeg") is not None}

@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, "Formato no admitido. Usa MP3, WAV, M4A, FLAC u OGG.")
    track_id = uuid4().hex[:12]
    folder = DATA / track_id
    folder.mkdir(parents=True)
    target = folder / ("original" + suffix)
    size = 0
    with target.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_MB * 1024 * 1024:
                shutil.rmtree(folder, ignore_errors=True)
                raise HTTPException(413, f"El archivo supera {MAX_MB} MB.")
            out.write(chunk)
    return {"track_id": track_id, "filename": file.filename,
            "audio_url": f"/api/audio/{track_id}/original"}

@app.get("/api/audio/{track_id}/{kind}")
def audio(track_id: str, kind: str):
    folder = track_dir(track_id)
    if kind == "original":
        matches = list(folder.glob("original.*"))
    elif kind in ("vocals", "instrumental"):
        matches = list(folder.glob(f"separated/*/{kind}.*"))
    else:
        raise HTTPException(404, "Pista desconocida")
    if not matches:
        raise HTTPException(404, "La pista todavía no está disponible")
    return FileResponse(matches[0])

@app.post("/api/lyrics")
def save_lyrics(project: LyricsProject):
    folder = track_dir(project.track_id)
    if not project.consent_confirmed:
        raise HTTPException(400, "Confirma que tienes autorización para usar el audio y la voz.")
    payload = project.model_dump()
    (folder / "lyrics.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True}

@app.post("/api/separate/{track_id}")
def separate(track_id: str):
    folder = track_dir(track_id)
    if shutil.which("demucs") is None:
        raise HTTPException(503, "Demucs no está instalado en el servidor.")
    source = next(iter(folder.glob("original.*")), None)
    if source is None:
        raise HTTPException(404, "Audio original no encontrado")
    outdir = folder / "separated"
    cmd = ["demucs", "--two-stems=vocals", "-o", str(outdir), str(source)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "La separación tardó demasiado.")
    if proc.returncode != 0:
        raise HTTPException(500, "Falló Demucs: " + (proc.stderr[-1200:] or proc.stdout[-1200:]))
    if not list(outdir.rglob("vocals.wav")) or not list(outdir.rglob("no_vocals.wav")):
        raise HTTPException(500, "No se encontraron las pistas separadas.")
    return {"separated": True,
            "vocals_url": f"/api/audio/{track_id}/vocals",
            "instrumental_url": f"/api/audio/{track_id}/instrumental"}

@app.post("/api/render-vocals/{track_id}")
def render_vocals(track_id: str):
    folder = track_dir(track_id)
    lyrics_file = folder / "lyrics.json"
    if not lyrics_file.exists():
        raise HTTPException(400, "Guarda primero la nueva letra.")
    data = json.loads(lyrics_file.read_text(encoding="utf-8"))
    if not data.get("consent_confirmed"):
        raise HTTPException(403, "No se confirmó la autorización de voz.")
    raise HTTPException(501, "Motor de canto no configurado. Falta integrar un modelo autorizado de singing voice conversion con control de melodía/F0 y alineación temporal.")
