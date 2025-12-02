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

router = APIRouter(prefix="/api/fairy", tags=["Fairy"])

class TalkDungeonRequest(BaseModel):
    dungeonPlayer: DungeonPlayerData
    question: str
    targetMonsterIds: List[int] = Field(default_factory=list)
    nextRoomId: Optional[int] = None


class TalkGuildRequest(BaseModel):
    playerId: int
    heroine_id: int
    memory_progress: int
    sanity: int
    question: str


class TalkResponse(BaseModel):
    response_text: str


class InteractionRequest(BaseModel):
    player: DungeonPlayerData
    question: str


class InteractionResponse(BaseModel):
    roomLight: Optional[bool] = None
    isCheckNextRoom: bool = False
    useItemId: Optional[int] = None


@router.post("/dungeon/talk", response_model=TalkResponse)
async def talk_dungeon(request: TalkDungeonRequest):
    """정령 - 던전 대화"""
    player = request.dungeonPlayer 
    question = request.question
    targetMonsterIds = request.targetMonsterIds
    nextRoomId = request.nextRoomId
    result_text = fairy_dungeon_talk(player, question, targetMonsterIds, nextRoomId)

    return TalkResponse(response_text=result_text)


@router.post("/dungeon/interaction", response_model=InteractionResponse)
async def interaction(request: InteractionRequest):
    """정령 - 던전 인터렉션 요청"""
    player = request.player
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

    result_text = fairy_guild_talk(
        playerId, question, heroine_id, memory_progress, sanity
    )
    return TalkResponse(response_text=result_text)
