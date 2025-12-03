from pydantic import BaseModel, Field
from agents.fairy.fairy_guild_agent import graph_builder as guild_builder
from agents.fairy.fairy_dungeon_agent import graph_builder as dungeon_builder
from agents.fairy.fairy_interaction_agent import graph_builder as interaction_builder
from fastapi import APIRouter
from typing import List, Optional
from services.fairy_service import (
    fairy_interaction,
    fairy_guild_talk,
    fairy_dungeon_talk,
)
from core.game_dto.DungeonPlayerData import DungeonPlayerData
from core.game_dto.z_muck_factory import MockFactory

router = APIRouter(prefix="/api/fairy", tags=["Fairy"])


class TalkDungeonRequest(BaseModel):
    dungeonPlayer: DungeonPlayerData = Field(
        ...,
        description="(통신 프로토콜 기준 - dungeonPlayerData) 던전 플레이어의 실시간 상태",
        example=MockFactory.create_dungeon_player(1),
    )
    question: str = Field(..., description="사용자의 질문", example="현재 방의 불좀 켜줘")
    targetMonsterIds: List[int] = Field(
        default_factory=list,
        description="히로인 시야에 있는 몬스터들 (사실 1개면 됨, 혹시 몰라 리스트로 열어둠)",
    )
    nextRoomId: int = Field(..., description="히로인이 이동해야할 다음방 ID", example=1)


class TalkGuildRequest(BaseModel):
    playerId: int = Field(..., description="사용자 ID")
    heroine_id: int = Field(..., description="히로인 ID")
    memory_progress: int = Field(..., description="히로인 기억 해금 진척도")
    affection:int = Field(..., description="히로인 호감도")
    sanity: int = Field(..., description="히로인 정신력")
    question: str = Field(..., description="사용자의 질문")


class TalkResponse(BaseModel):
    response_text: str = Field(..., description="현재 던전의 불을 켜드리겠습니다. 방이 밝아졌어요!")

class InteractionRequest(BaseModel):
    dungeonPlayer: DungeonPlayerData = Field(
        ...,
        description="(통신 프로토콜 기준 - dungeonPlayerData) 던전 플레이어의 실시간 상태",
        example = MockFactory.create_dungeon_player(1)
    )
    question: str = Field(..., description="사용자의 질문", example='현재 방 불좀 켜봐')

class InteractionResponse(BaseModel):
    roomLight: Optional[bool] = Field(..., description="방 밝기 On/Off 여부 (정령 행동 필요 없으면 Null)", example=None)
    isCheckNextRoom: bool = Field(..., description="다음방 확인 시키기 여부(정령 행동 필요 없으면 False)", example=True) 
    useItemId: Optional[int] = Field(..., description="사용 하려는 아이템 (정령 행동 필요 없으면 Null)", example=None) 


@router.post("/dungeon/talk", response_model=TalkResponse)
async def talk_dungeon(request: TalkDungeonRequest):
    """정령 - 던전 대화"""
    player = request.dungeonPlayer
    question = request.question
    targetMonsterIds = request.targetMonsterIds
    nextRoomId = request.nextRoomId
    result_text = await fairy_dungeon_talk(player, question, targetMonsterIds, nextRoomId)
    return TalkResponse(response_text=result_text)

@router.post("/dungeon/interaction", response_model=InteractionResponse)
def interaction(request: InteractionRequest):
    """정령 - 던전 인터렉션 요청"""
    player = request.dungeonPlayer
    question = request.question
    response = fairy_interaction(player, question)
    useItemId = response["useItemId"]
    roomLight = response["roomLight"]
    isCheckNextRoom = response["isCheckNextRoom"]
    return InteractionResponse(
        useItemId=useItemId,
        roomLight=roomLight,
        isCheckNextRoom=isCheckNextRoom,
    )

@router.post("/guild/talk", response_model=TalkResponse)
async def talk_guild(request: TalkGuildRequest):
    """정령 - 길드 대화"""
    playerId = request.playerId
    question = request.question

    heroine_id = request.heroine_id
    memory_progress = request.memory_progress
    sanity = request.sanity
    affection = request.affection

    result_text = await fairy_guild_talk(
        playerId, question, heroine_id, affection, memory_progress,  sanity
    )
    return TalkResponse(response_text=result_text)
