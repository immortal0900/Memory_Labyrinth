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
    """Unreal에서 보낸 raw_map 구조 (방 정보만)"""

    floor: int
    rooms: List[RawMapRoom]
    rewards: List[int] = []


class EntranceRequest(BaseModel):
    """던전 입장 요청 (최상위에 playerIds, heroineIds, heroineData, rawMaps)"""

    playerIds: List[str]
    heroineIds: List[int]
    heroineData: Optional[List[Any]] = None
    rawMaps: List[RawMapRequest]
    usedEvents: Optional[List[Any]] = None


class EventChoice(BaseModel):
    """이벤트 선택지"""

    action: str
    reward: Optional[dict] = None  # 보상 dict (id/description 제외)
    penalty: Optional[dict] = None  # 패널티 dict (id/description 제외)


class EventResponse(BaseModel):
    """이벤트 정보 응답 (클라 요구: reward/penalty dict)"""

    roomId: int
    eventType: int
    eventTitle: str
    scenarioText: str
    scenarioNarrative: Any  # str(공용) 또는 dict(개인)


class EntranceResponse(BaseModel):
    """던전 입장 응답 (클라 요구: 최상위 배열)"""

    success: bool
    message: str
    playerIds: List[str]
    events: Optional[List[EventResponse]] = None


class PlayerBalanceData(BaseModel):
    """플레이어별 밸런싱 데이터"""

    heroineData: Dict[
        str, Any
    ]  # playerId, heroineStat, heroineMemories, dungeonPlayerData 포함


class BalanceRequest(BaseModel):
    """밸런싱 요청 (보스방 입장)"""

    firstPlayerId: str  # 방장 ID로 던전 식별
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
    firstPlayerId: str
    monsterPlacements: List[MonsterPlacement] = []


class ClearRequest(BaseModel):
    """층 완료 요청"""

    playerIds: List[str]


class ClearResponse(BaseModel):
    """층 완료 응답"""

    success: bool
    message: str
    finishedFloor: Optional[int] = None


class EventSelectRequest(BaseModel):
    """이벤트 선택 요청"""

    firstPlayerId: str
    selectingPlayerId: str
    roomId: int
    choice: str


class EventSelectResponse(BaseModel):
    """이벤트 선택 응답"""

    success: bool
    firstPlayerId: str
    selectingPlayerId: str
    roomId: int
    outcome: str
    rewardId: Optional[Any] = None
    penaltyId: Optional[Any] = None


class NextFloorRequest(BaseModel):
    """다음 층 입장 요청 (playerIds, heroineIds 최상위)"""

    playerIds: List[str]
    heroineIds: List[int]
    heroineData: Optional[List[Any]] = None  # int/dict 모두 허용
    rawMap: RawMapRequest  # 다음 층 raw_map
    usedEvents: Optional[List[Any]] = None


class NextFloorResponse(BaseModel):
    """다음 층 입장 응답 (클라 요구: 최상위 배열)"""

    success: bool
    message: str
    playerIds: List[str]
    events: Optional[List[EventResponse]] = None


# =============================================================================
# API Endpoints
# =============================================================================


import time


@router.post("/entrance", response_model=EntranceResponse)
def entrance(request: EntranceRequest):
    total_start = time.time()
    try:
        service = get_dungeon_service()

        # 여러 층 raw_map을 dict로 변환 (playerIds, heroineIds는 최상위에서 받음)
        raw_maps = [raw_map.model_dump() for raw_map in request.rawMaps]

        # 던전 입장
        result = service.entrance(
            player_ids=request.playerIds,
            heroine_ids=request.heroineIds,
            raw_maps=raw_maps,
            heroine_data=request.heroineData,
            used_events=request.usedEvents or [],
        )

        # 이벤트 정보 매핑 (floor 구분 포함, reward/penalty dict)
        events_list = []
        if result.get("events"):
            events_data = result["events"]
            # 1층 이벤트만 추출
            if isinstance(events_data, list):
                for evt in events_data:
                    if evt.get("floor", 1) != 1:
                        continue
                    scenario_narrative = evt.get("scenario_narrative", "")
                    if evt.get("is_personal") and evt.get("heroineNarratives"):
                        scenario_narrative = {
                            str(n["playerId"]): n["narrative"]
                            for n in evt["heroineNarratives"]
                            if isinstance(n, dict)
                            and "playerId" in n
                            and "narrative" in n
                        }
                    events_list.append(
                        EventResponse(
                            roomId=evt.get("room_id", 0),
                            eventType=evt.get("event_type", 0),
                            eventTitle=evt.get("event_title", ""),
                            scenarioText=evt.get("scenario_text", ""),
                            scenarioNarrative=scenario_narrative,
                            choices=[
                                EventChoice(
                                    action=c.get("action", ""),
                                    reward=c.get("reward"),
                                    penalty=c.get("penalty"),
                                )
                                for c in evt.get("choices", [])
                                if isinstance(c, dict)
                            ],
                        )
                    )
            elif isinstance(events_data, dict):
                evt = events_data
                if evt.get("floor", 1) == 1:
                    scenario_narrative = evt.get("scenario_narrative", "")
                    if evt.get("is_personal") and evt.get("heroineNarratives"):
                        scenario_narrative = {
                            str(n["playerId"]): n["narrative"]
                            for n in evt["heroineNarratives"]
                            if isinstance(n, dict)
                            and "playerId" in n
                            and "narrative" in n
                        }
                    events_list.append(
                        EventResponse(
                            roomId=evt.get("room_id", 0),
                            eventType=evt.get("event_type", 0),
                            eventTitle=evt.get("event_title", ""),
                            scenarioText=evt.get("scenario_text", ""),
                            scenarioNarrative=scenario_narrative,
                            choices=[
                                EventChoice(
                                    action=c.get("action", ""),
                                    reward=c.get("reward"),
                                    penalty=c.get("penalty"),
                                )
                                for c in evt.get("choices", [])
                                if isinstance(c, dict)
                            ],
                        )
                    )

        # 최상위 배열 추출 (중복 없이)
        player_ids = request.playerIds
        heroine_ids = request.heroineIds
        heroine_data = request.heroineData or []
        heroine_memory_progress = []
        for h in heroine_data:
            if isinstance(h, dict):
                mp = h.get("memory_progress")
                if mp is None:
                    mp = h.get("memoryProgress", 0)
                heroine_memory_progress.append(mp)
            elif isinstance(h, int):
                heroine_memory_progress.append(h)
            else:
                heroine_memory_progress.append(0)
        while len(heroine_memory_progress) < len(heroine_ids):
            heroine_memory_progress.append(0)
        total_elapsed = time.time() - total_start
        print(f"[TIMING] 던전 입장~이벤트 생성 전체 처리 시간: {total_elapsed:.3f}s")
        return EntranceResponse(
            success=True,
            message="던전 입장 성공",
            playerIds=player_ids,
            events=events_list if events_list else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"던전 입장 실패: {str(e)}")


@router.post("/balance", response_model=BalanceResponse)
def balance_dungeon(request: BalanceRequest):
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
                scenarioText=evt.get("scenario_text", ""),
                scenarioNarrative=evt.get("scenario_narrative", ""),
            )

        return BalanceResponse(
            success=True,
            message="던전 밸런싱 성공",
            firstPlayerId=request.firstPlayerId,
            monsterPlacements=monster_placements,
            agentResult=result.get("agent_result"),
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"밸런싱 실패: {str(e)}")


@router.put("/clear", response_model=ClearResponse)
def clear_floor(request: ClearRequest):
    try:
        service = get_dungeon_service()

        # 층 완료 처리
        result = service.clear_floor(player_ids=request.playerIds)

        if not result["success"]:
            raise Exception(result.get("error", "Unknown error"))

        finished_floor = result["finished_dungeon"]["floor"]

        # balanced_map 반환 제거, 완료 처리만 응답
        return ClearResponse(
            success=True,
            message=f"{finished_floor}층 완료",
            finishedFloor=finished_floor,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"층 완료 처리 실패: {str(e)}")


@router.post("/event/select", response_model=EventSelectResponse)
def select_event(request: EventSelectRequest):
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
            rewardId=result.get("rewardId"),
            penaltyId=result.get("penaltyId"),
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"이벤트 선택 처리 실패: {str(e)}")


@router.post("/nextfloor", response_model=NextFloorResponse)
def nextfloor(request: NextFloorRequest):
    """
    다음 층 입장 시 raw_map과 heroineData를 받아 이벤트 생성 및 DB 저장
    """
    try:
        service = get_dungeon_service()
        raw_map = (
            request.rawMap.model_dump()
            if hasattr(request.rawMap, "model_dump")
            else dict(request.rawMap)
        )
        print(f"[DEBUG] API nextfloor raw_map: {raw_map}")
        # Patch: ensure 'floor' is present in raw_map
        if "floor" not in raw_map:
            # Try to extract from request or rooms if possible
            if hasattr(request.rawMap, "floor"):
                raw_map["floor"] = request.rawMap.floor
            # If still not found, raise clear error
            if "floor" not in raw_map:
                raise HTTPException(
                    status_code=400, detail="raw_map에 floor 정보가 없습니다. (API)"
                )
        heroine_data = request.heroineData
        if heroine_data is None or (
            isinstance(heroine_data, list) and len(heroine_data) == 0
        ):
            raise HTTPException(
                status_code=400,
                detail="heroineData가 비어 있거나 유효하지 않습니다. (API)",
            )
        if heroine_data is not None and not isinstance(heroine_data, list):
            heroine_data = [heroine_data]
        result = service.next_floor_entrance(
            player_ids=request.playerIds,
            heroine_ids=request.heroineIds,
            raw_map=raw_map,
            heroine_data=heroine_data,
            used_events=request.usedEvents or [],
        )

        # 현재 입장해야 하는 층(가장 낮은 is_finishing=False인 floor) 구하기
        repo = service.repo
        player_id = request.playerIds[0] if request.playerIds else None
        unfinished_row = repo.get_unfinished_dungeons([player_id])
        current_floor = None
        if unfinished_row:
            current_floor = unfinished_row.get("floor")

        events_list = []
        if player_id and current_floor is not None:
            # DB에서 해당 층 이벤트 조회
            previous_events = repo.get_event_by_floor(player_id, current_floor)
            if previous_events:
                if isinstance(previous_events, list):
                    for evt in previous_events:
                        events_list.append(
                            EventResponse(
                                roomId=evt.get("room_id", 0),
                                eventType=evt.get("event_type", 0),
                                eventTitle=evt.get("event_title", ""),
                                scenarioText=evt.get("scenario_text", ""),
                                scenarioNarrative=evt.get("scenario_narrative", ""),
                                choices=[
                                    EventChoice(
                                        action=c.get("action", ""),
                                        reward=c.get("reward"),
                                        penalty=c.get("penalty"),
                                    )
                                    for c in evt.get("choices", [])
                                    if isinstance(c, dict)
                                ],
                            )
                        )
                elif isinstance(previous_events, dict):
                    evt = previous_events
                    events_list.append(
                        EventResponse(
                            roomId=evt.get("room_id", 0),
                            eventType=evt.get("event_type", 0),
                            eventTitle=evt.get("event_title", ""),
                            scenarioText=evt.get("scenario_text", ""),
                            scenarioNarrative=evt.get("scenario_narrative", ""),
                            choices=[
                                EventChoice(
                                    action=c.get("action", ""),
                                    reward=c.get("reward"),
                                    penalty=c.get("penalty"),
                                )
                                for c in evt.get("choices", [])
                                if isinstance(c, dict)
                            ],
                        )
                    )

        player_ids = request.playerIds
        heroine_ids = request.heroineIds
        heroine_data = heroine_data or []
        heroine_memory_progress = []
        for h in heroine_data:
            if isinstance(h, dict):
                mp = h.get("memory_progress")
                if mp is None:
                    mp = h.get("memoryProgress", 0)
                heroine_memory_progress.append(mp)
            elif isinstance(h, int):
                heroine_memory_progress.append(h)
            else:
                heroine_memory_progress.append(0)
        while len(heroine_memory_progress) < len(heroine_ids):
            heroine_memory_progress.append(0)
        return NextFloorResponse(
            success=True,
            message="다음 층 입장 및 이벤트 생성 성공",
            playerIds=player_ids,
            events=events_list if events_list else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"다음 층 입장 실패: {str(e)}")
