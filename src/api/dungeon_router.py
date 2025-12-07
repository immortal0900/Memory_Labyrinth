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
    heroineData: Optional[Dict[str, Any]] = None
    usedEvents: Optional[List[Any]] = None


class EventChoice(BaseModel):
    """이벤트 선택지"""

    action: str
    rewardId: Optional[str] = None
    penaltyId: Optional[str] = None


class EventResponse(BaseModel):
    """이벤트 정보 응답"""

    roomId: int
    eventType: int
    eventTitle: str
    eventCode: str
    scenarioText: str
    scenarioNarrative: str
    choices: List[EventChoice] = []


class EntranceResponse(BaseModel):
    """던전 입장 응답"""

    success: bool
    message: str
    firstPlayerId: int
    events: Optional[List[EventResponse]] = None


class PlayerBalanceData(BaseModel):
    """플레이어별 밸런싱 데이터"""

    heroineData: Dict[
        str, Any
    ]  # playerId, heroineStat, heroineMemories, dungeonPlayerData 포함


class BalanceRequest(BaseModel):
    """밸런싱 요청 (보스방 입장)"""

    firstPlayerId: int  # 방장 ID로 던전 식별
    playerDataList: List[PlayerBalanceData]
    usedEvents: Optional[List[Any]] = None


class MonsterPlacement(BaseModel):
    """몬스터 배치 정보"""

    roomId: int
    monsterId: int
    count: int


class BalanceResponse(BaseModel):
    """밸런싱 응답"""

    success: bool
    message: str
    firstPlayerId: int
    monsterPlacements: List[MonsterPlacement] = []
    nextFloorEvent: Optional[EventResponse] = None


class ClearRequest(BaseModel):
    """층 완료 요청"""

    playerIds: List[int]


class ClearResponse(BaseModel):
    """층 완료 응답"""

    success: bool
    message: str
    finishedFloor: Optional[int] = None


class EventSelectRequest(BaseModel):
    """이벤트 선택 요청"""

    firstPlayerId: int
    selectingPlayerId: int
    roomId: int
    choice: str


class EventSelectResponse(BaseModel):
    """이벤트 선택 응답"""

    success: bool
    firstPlayerId: int
    selectingPlayerId: int
    roomId: int
    outcome: str  # 결과 텍스트 (현재는 TEXT, 나중에 보상 타입과 ID로 변경)


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
            # heroine_data=request.heroineData, # 임시 제거
            used_events=request.usedEvents or [],
        )

        # 이벤트 정보 매핑
        events_list = []
        if result.get("events"):
            events_data = result["events"]
            # 리스트인 경우 (여러 이벤트)
            if isinstance(events_data, list):
                for evt in events_data:
                    events_list.append(
                        EventResponse(
                            roomId=evt.get("room_id", 0),
                            eventType=evt.get("event_type", 0),
                            eventTitle=evt.get("event_title", ""),
                            eventCode=evt.get("event_code", ""),
                            scenarioText=evt.get("scenario_text", ""),
                            scenarioNarrative=evt.get("scenario_narrative", ""),
                            choices=[
                                EventChoice(
                                    action=c.get("action", ""),
                                    rewardId=c.get("reward_id"),
                                    penaltyId=c.get("penalty_id"),
                                )
                                for c in evt.get("choices", [])
                                if isinstance(c, dict)
                            ],
                        )
                    )
            # 단일 딕셔너리인 경우 (하위 호환성)
            elif isinstance(events_data, dict):
                evt = events_data
                events_list.append(
                    EventResponse(
                        roomId=evt.get("room_id", 0),
                        eventType=evt.get("event_type", 0),
                        eventTitle=evt.get("event_title", ""),
                        eventCode=evt.get("event_code", ""),
                        scenarioText=evt.get("scenario_text", ""),
                        scenarioNarrative=evt.get("scenario_narrative", ""),
                        choices=[
                            EventChoice(
                                action=c.get("action", ""),
                                rewardId=c.get("reward_id"),
                                penaltyId=c.get("penalty_id"),
                            )
                            for c in evt.get("choices", [])
                            if isinstance(c, dict)
                        ],
                    )
                )

        return EntranceResponse(
            success=True,
            message="던전 입장 성공",
            firstPlayerId=result.get("first_player_id", 0),
            events=events_list if events_list else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"던전 입장 실패: {str(e)}")


@router.post("/balance", response_model=BalanceResponse)
async def balance_dungeon(request: BalanceRequest):
    try:
        service = get_dungeon_service()

        # Monster DB 로드
        from agents.dungeon.monster.monster_database import MONSTER_DATABASE

        # 밸런싱 실행 (이벤트 생성 분리됨)
        result = service.balance_dungeon(
            first_player_id=request.firstPlayerId,
            player_data_list=[pd.dict() for pd in request.playerDataList],
            monster_db=MONSTER_DATABASE,
            used_events=request.usedEvents,
        )

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        # 몬스터 배치 정보 매핑
        monster_placements = []
        for mp in result.get("monster_placements", []):
            monster_placements.append(
                MonsterPlacement(
                    roomId=mp["roomId"], monsterId=mp["monsterId"], count=mp["count"]
                )
            )

        # 다음 층 이벤트 정보 매핑
        next_event_data = None
        if result.get("next_floor_event"):
            evt = result["next_floor_event"]
            next_event_data = EventResponse(
                roomId=evt.get("room_id", 0),
                eventType=evt.get("event_type", 0),
                eventTitle=evt.get("event_title", ""),
                eventCode=evt.get("event_code", ""),
                scenarioText=evt.get("scenario_text", ""),
                scenarioNarrative=evt.get("scenario_narrative", ""),
            )

        return BalanceResponse(
            success=True,
            message="던전 밸런싱 성공",
            firstPlayerId=request.firstPlayerId,
            monsterPlacements=monster_placements,
            nextFloorEvent=next_event_data,
            agentResult=result.get("agent_result"),
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
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


@router.post("/event/select", response_model=EventSelectResponse)
async def select_event(request: EventSelectRequest):
    """
    플레이어가 이벤트 선택지를 선택했을 때 처리
    """
    try:
        service = get_dungeon_service()

        # 이벤트 선택 처리
        result = service.select_event(
            first_player_id=request.firstPlayerId,
            selecting_player_id=request.selectingPlayerId,
            room_id=request.roomId,
            choice=request.choice,
        )

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        return EventSelectResponse(
            success=True,
            firstPlayerId=request.firstPlayerId,
            selectingPlayerId=request.selectingPlayerId,
            roomId=request.roomId,
            outcome=result.get("outcome", ""),
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"이벤트 선택 처리 실패: {str(e)}")
