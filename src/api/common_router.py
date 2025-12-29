import os
import re
import time
import wave
import logging
from logging.handlers import RotatingFileHandler
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
import whisper
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Request, APIRouter
from fastapi.responses import JSONResponse

SAVE_UPLOADS = True                      
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")  
LOG_DIR = os.getenv("LOG_DIR", "./logs")
LOG_FILE = os.path.join(LOG_DIR, "stt_app.log")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 로깅 설정 (파일+콘솔, 로그 로테이션)
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

router = APIRouter(prefix="/stt", tags=["stt"])
model = whisper.load_model("large")
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     logger.info("Starting up... warming up whisper model")
#     dummy = np.zeros(16000, dtype=np.float32)
#     t0 = time.perf_counter()
#     _ = model.transcribe(dummy, language="ko")
#     logger.info(f"Warmup done in {time.perf_counter() - t0:.3f}s")
#     yield
#     logger.info("Shutting down...")


_CJK_OR_KANA = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
_HANGUL = re.compile(r'[가-힣]')
_LETTERS = re.compile(r'[A-Za-z가-힣]')

def _is_valid_text(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 2:
        return False
    if _CJK_OR_KANA.search(t):
        return False

    letters = _LETTERS.findall(t)
    if letters:
        hangul = _HANGUL.findall(t)
        if (len(hangul) / len(letters)) < 0.85:   # 필요시 0.9로 더 빡세게
            return False
    else:
        return False

    return True
    
def _is_suspicious_segment(seg: dict) -> bool:
    if seg.get("no_speech_prob", 0) > 0.6:
        return True
    if seg.get("avg_logprob", 0) < -1.0:
        return True
    if seg.get("compression_ratio", 0) > 2.4:
        return True
    return False

DOMAIN_REPLACE_MAP = {
    # 몬스터 / 시스템
    "공격복종": "공략법좀",
    "저 모니터": "저 몬스터",
    "다음 번 뭐야?": "다음방 뭐야?",
    "인벤트로" : "인벤토리",

    #아이템
    "고급 등기": "고급 둔기",
    "일반 등기": "일반 둔기",
    "우리 둔질": "고급 둔기",
    "보급 등기": "고급 둔기",
    "9급 둔기": "고급 둔기",
    "1반 쌍검": "일반 쌍검",
    "1번 쌍검": "일반 쌍검",
    '고무 누워프':'고급 드워프',
    '고급 두업으로':'고급 드워프',
    '고급 드로크':'고급 드워프',
    '양솜에서':'양손 메서',
    '고급한 손검': '고급 한손검',
    '1번 한손검':'일반 한손검',
    '레어스 숏소드': '레어 숏소드',
    '쇼스토드':'숏소드',
    '1번 도어퍼':'일반 드워프',
    '9급':'고급',
    '드래곤 플레이어':'드래곤 슬레이어',
    '슬레이오':'슬레이어',
    '레오상검': '레어 쌍검',
    '고급 상품': '고급 쌍검',
    '고급 더프의 망치':'고급 드워프의 망치',
    '한 손 검':'한손검',
    '부어프':'드워프',
    '궁극 두어프': '고급 드워프',
        
    # UI / 명령
    "물 좀 켜줄래?": "불좀 켜줄래?",
    "불좀 구워줄래?": "불좀 켜줄래?"
    
    #캐릭터
    #기타 
}

def _domain_replace(text: str) -> str:
    if not text:
        return ""

    t = text
    for src, dst in DOMAIN_REPLACE_MAP.items():
        if src in t:
            t = t.replace(src, dst)

    return t

@router.post("/wav")
async def stt_wav(request: Request, file: UploadFile = File(...)):
    rid = getattr(request.state, "request_id", "noid")

    if not file.filename:
        raise HTTPException(400, "No file uploaded")

    # 1️⃣ 파일 먼저 읽기
    data = await file.read()
    size = len(data)

    suffix = os.path.splitext(file.filename)[-1].lower() or ".wav"

    # 2️⃣ 임시 파일에 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    logger.info(
        f"[{rid}] upload filename={file.filename} "
        f"content_type={file.content_type} bytes={size}"
    )

    # 3️⃣ STT
    t0 = time.perf_counter()
    result = model.transcribe(tmp_path, language="ko")
    segments = result.get("segments", [])

    final_text = " ".join(
        seg["text"].strip()
        for seg in segments
        if not _is_suspicious_segment(seg)
    ).strip()

    dur = time.perf_counter() - t0
    transfer_text = _domain_replace(final_text)

    logger.info(
        f"[{rid}] transcribe done in {dur:.3f}s text_len={len(final_text)}"
    )

    is_valid = bool(transfer_text) and _is_valid_text(transfer_text)
    saved_path = None

    if SAVE_UPLOADS:
        saved_path = _make_save_path("stt", file.filename, suffix)
        with open(saved_path, "wb") as f:
            f.write(data)
        logger.info(f"[{rid}] saved upload -> {saved_path}")

    return JSONResponse({
        "transferText": transfer_text,
        "isValid": is_valid
    })
    
@router.post("/pcm")
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

        transfer_text =  _domain_replace(final_text)
        is_valid = bool(transfer_text) and _is_valid_text(transfer_text)
        logger.info(f"[{rid}] transcribe done in {dur:.3f}s text_len={len(transfer_text)}")

        return JSONResponse({
            "transferText": transfer_text,
            "isValid":is_valid
        })
    except Exception:
        logger.exception(f"[{rid}] /stt_pcm failed")
        raise