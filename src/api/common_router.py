import os
import re
import time
import uuid
import wave
import logging
from logging.handlers import RotatingFileHandler
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
import whisper
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Request
from fastapi.responses import JSONResponse

SAVE_UPLOADS = True                      
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")  
LOG_DIR = os.getenv("LOG_DIR", "./logs")
LOG_FILE = os.path.join(LOG_DIR, "stt_app.log")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# =========================
# 로깅 설정 (파일+콘솔, 로그 로테이션)
# =========================
logger = logging.getLogger("stt")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 파일 핸들러 (10MB * 5개 보관)
fh = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
fh.setFormatter(_fmt)
logger.addHandler(fh)

# 콘솔 핸들러 (nohup stdout에도 찍힘)
ch = logging.StreamHandler()
ch.setFormatter(_fmt)
logger.addHandler(ch)

def _safe_filename(name: str) -> str:
    name = os.path.basename(name or "upload.wav")
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:120]

def _make_save_path(prefix: str, original_name: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe = _safe_filename(original_name)
    base, _ = os.path.splitext(safe)
    return os.path.join(UPLOAD_DIR, f"{prefix}_{ts}_{base}{ext}")

model = whisper.load_model("large")
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up... warming up whisper model")
    dummy = np.zeros(16000, dtype=np.float32)
    t0 = time.perf_counter()
    _ = model.transcribe(dummy, language="ko")
    logger.info(f"Warmup done in {time.perf_counter() - t0:.3f}s")
    yield
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:10]
    request.state.request_id = request_id

    start = time.perf_counter()
    client = request.client.host if request.client else "unknown"
    logger.info(f"[{request_id}] -> {client} {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        dur = time.perf_counter() - start
        logger.info(f"[{request_id}] <- {response.status_code} ({dur:.3f}s)")
        return response
    except Exception:
        dur = time.perf_counter() - start
        logger.exception(f"[{request_id}] !! unhandled error ({dur:.3f}s)")
        raise

def _is_suspicious_segment(seg: dict) -> bool:
    if seg.get("no_speech_prob", 0) > 0.6:
        return True
    if seg.get("avg_logprob", 0) < -1.0:
        return True
    if seg.get("compression_ratio", 0) > 2.4:
        return True
    return False


@app.post("/stt")
async def stt(request: Request, file: UploadFile = File(...)):
    rid = getattr(request.state, "request_id", "noid")

    if not file.filename:
        raise HTTPException(400, "No file uploaded")

    suffix = os.path.splitext(file.filename)[-1].lower() or ".wav"
    tmp_path = None
    saved_path = None

    data = await file.read()
    size = len(data)

    logger.info(f"[{rid}] upload filename={file.filename} content_type={file.content_type} bytes={size}")

    # 1) 원본 파일 저장 (원하면 영구 보관)
    if SAVE_UPLOADS:
        saved_path = _make_save_path("stt", file.filename, suffix)
        with open(saved_path, "wb") as f:
            f.write(data)
        logger.info(f"[{rid}] saved upload -> {saved_path}")

    # 2) whisper에 넣을 임시 파일 생성(업로드 확장자 유지)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    t0 = time.perf_counter()
    result = model.transcribe(tmp_path, language="ko")
    segments = result.get("segments", [])

    final_text = " ".join(
        seg["text"].strip()
        for seg in segments
        if not _is_suspicious_segment(seg)
    ).strip()
    is_valid = bool(final_text)
    dur = time.perf_counter() - t0
    
    text = (result.get("text") or "").strip()
    logger.info(f"[{rid}] transcribe done in {dur:.3f}s text_len={len(text)}")

                                
    return JSONResponse({
        "transferText": text,
        "isValid":is_valid
    })

    
@app.post("/stt_pcm")
async def stt_pcm(request: Request, pcm: bytes = Body(...)):
    rid = getattr(request.state, "request_id", "noid")

    if not pcm:
        raise HTTPException(400, "empty body")

    logger.info(f"[{rid}] pcm bytes={len(pcm)}")

    saved_path = None
    try:
        # PCM을 wav로 저장(확인용)
        if SAVE_UPLOADS:
            saved_path = _make_save_path("pcm", "mic_stream", ".wav")
            with wave.open(saved_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)      # int16
                wf.setframerate(16000)  # 너희 포맷 가정 (16kHz mono)
                wf.writeframes(pcm)
            logger.info(f"[{rid}] saved pcm wav -> {saved_path}")

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

        t0 = time.perf_counter()
        result = model.transcribe(audio, language="ko")
        dur = time.perf_counter() - t0

        segments = result.get("segments", [])
        final_text = " ".join(
        seg["text"].strip()
        for seg in segments
            if not _is_suspicious_segment(seg)
        ).strip()
        is_valid = bool(final_text)

        text = (result.get("text") or "").strip()
        logger.info(f"[{rid}] transcribe done in {dur:.3f}s text_len={len(text)}")

        return JSONResponse({
            "transferText": text,
            "isValid":is_valid
        })
    except Exception:
        logger.exception(f"[{rid}] /stt_pcm failed")
        raise