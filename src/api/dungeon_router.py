"""
Dungeon API Router
언리얼 엔진과의 던전 시스템 통신을 담당합니다.

엔드포인트:
- POST /api/dungeon/entrance: 던전 입장 (1,2,3층 생성)
- PUT /api/dungeon/raw-map: 다음 층의 raw_map 업데이트
- POST /api/dungeon/balance: 보스방 진입 (Super Agent 실행)
- PUT /api/dungeon/clear: 층 완료 처리 (is_finishing=TRUE)
- GET /api/dungeon/status: 현재 진행 중인 던전 상태 조회
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from services.dungeon_service import get_dungeon_service

# Router 생성
router = APIRouter(prefix="/api/dungeon", tags=["dungeon"])

# =============================================================================
# Pydantic Models (요청/응답 데이터 구조)
# =============================================================================


class RawMapRoom(BaseModel):
    """Unreal에서 보낸 room 구조"""

    roomId: int
    type: int  # 0=empty, 1=monster, 2=event, 3=treasure, 4=boss
    size: int
    neighbors: List[int]
    monsters: List[Dict[str, Any]] = []
    eventType: int = 0


class RawMapRequest(BaseModel):
    """Unreal에서 보낸 raw_map 구조"""

    playerIds: List[int]
    heroineIds: List[int]
    rooms: List[RawMapRoom]
    rewards: List[int] = []


class EntranceRequest(BaseModel):
    """던전 입장 요청"""

    rawMap: RawMapRequest


class EntranceResponse(BaseModel):
    """던전 입장 응답"""

    success: bool
    message: str
    floorIds: Optional[Dict[str, int]] = None  # {"floor1": 1, "floor2": 2, "floor3": 3}


class BalanceRequest(BaseModel):
    """밸런싱 요청 (보스방 입장)"""

    dungeonId: int
    heroineData: Dict[str, Any]  # {heroine_id, name, event_room, memory_progress}
    heroineStat: Dict[str, Any]  # {hp, strength, dexterity, ...}
    heroineMemories: List[Dict[str, Any]] = []
    dungeonPlayerData: Dict[str, Any]  # {affection, sanity, difficulty_level}
    usedEvents: List[Any] = []  # 이미 사용한 이벤트 리스트


class BalanceResponse(BaseModel):
    """밸런싱 응답"""

    success: bool
    message: str
    dungeonId: Optional[int]
    agentResult: Optional[Dict[str, Any]] = None


class ClearRequest(BaseModel):
    """층 완료 요청"""

    playerIds: List[int]


class ClearResponse(BaseModel):
    """층 완료 응답"""

    success: bool
    message: str
    finishedFloor: Optional[int] = None


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/entrance", response_model=EntranceResponse)
async def entrance(request: EntranceRequest):
    try:
        service = get_dungeon_service()

        # raw_map을 dict로 변환
        raw_map = request.rawMap.dict()

        # raw_map 정규화 (camelCase -> snake_case)
        from services.dungeon_service import _normalize_room_keys

        raw_map = _normalize_room_keys(raw_map)

        # 던전 입장
        result = service.entrance(
            player_ids=raw_map.get("player_ids") or raw_map.get("playerIds", []),
            heroine_ids=raw_map.get("heroine_ids") or raw_map.get("heroineIds", []),
            raw_map=raw_map,
        )

        return EntranceResponse(
            success=True,
            message="던전 입장 성공",
            floorIds={
                "floor1": result["floor1_id"],
                "floor2": result["floor2_id"],
                "floor3": result["floor3_id"],
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"던전 입장 실패: {str(e)}")


@router.post("/balance", response_model=BalanceResponse)
async def balance_dungeon(request: BalanceRequest):
    try:
        service = get_dungeon_service()

        # Monster DB 로드
        from agents.dungeon.monster.monster_database import MONSTER_DATABASE

        # 밸런싱 실행
        result = service.balance_dungeon(
            dungeon_id=request.dungeonId,
            heroine_data=request.heroineData,
            heroine_stat=request.heroineStat,
            heroine_memories=request.heroineMemories,
            dungeon_player_data=request.dungeonPlayerData,
            monster_db=MONSTER_DATABASE,
            used_events=request.usedEvents,
        )

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        # agent_result에서 playerIds, heroineIds 추출
        dungeon_data = result["agent_result"].get("dungeon_data", {})
        player_ids = dungeon_data.get("playerIds") or dungeon_data.get("player_ids", [])
        heroine_ids = dungeon_data.get("heroineIds") or dungeon_data.get(
            "heroine_ids", []
        )

        return BalanceResponse(
            success=True,
            message="밸런싱 완료",
            dungeonId=request.dungeonId,
            agentResult=result["agent_result"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"밸런싱 실패: {str(e)}")


@router.put("/clear", response_model=ClearResponse)
async def clear_floor(request: ClearRequest):
    try:
        service = get_dungeon_service()

        # 층 완료 처리
        result = service.clear_floor(player_ids=request.playerIds)

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        finished_floor = result["finished_dungeon"]["floor"]

        return ClearResponse(
            success=True,
            message=f"{finished_floor}층 완료",
            finishedFloor=finished_floor,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"층 완료 처리 실패: {str(e)}")
