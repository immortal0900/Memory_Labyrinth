import sys
from pathlib import Path

# src 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.npc_router import router as npc_router
from api.fairy_router import router as fairy_router
from api.dungeon_router import router as dungeon_router
from db.RDBRepository import RDBRepository

# FastAPI 앱 생성
app = FastAPI(
    title="AI Agent System",
    description="AI 에이전트 시스템 API 입니다.",
    version="1.0.0_alpha"
)

# CORS 설정 (언리얼 엔진에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(npc_router)
app.include_router(fairy_router)
app.include_router(dungeon_router)


@app.get("/")
async def root():
    """헬스 체크"""
    return {"status": "ok", "message": "AI Agent System is running"}


@app.get("/health")
async def health():
    """상세 헬스 체크"""
    return {
        "status": "healthy",
        "services": {
            "api": "ok",
            "redis": "check required",
            "database": "check required"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8090,
        reload=True
    )
