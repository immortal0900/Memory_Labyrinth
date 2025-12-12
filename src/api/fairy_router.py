from pydantic import BaseModel, Field
from fastapi import APIRouter
from typing import List, Optional
from services.fairy_service import (
    fairy_interaction,
    fairy_guild_talk,
    fairy_dungeon_talk,
)
from agents.fairy.fairy_state import DungeonPlayerState
from core.game_dto.DungeonPlayerData import DungeonPlayerData
from core.game_dto.z_muck_factory import MockFactory
from core.game_dto.StatData import StatData
from core.game_dto.ItemData import ItemData
from core.game_dto.WeaponData import WeaponData
import random
from core.common import get_inventory_items, get_inventory_item


router = APIRouter(prefix="/api/fairy", tags=["Fairy"])
class DungeonPlayerDto(BaseModel):
    playerId: int
    heroineId: int
    currRoomId: int
    difficulty: int = 0
    hp: int = (250,)
    moveSpeed: float = (1,)
    attackSpeed: float = (1.0,)
    weaponId: int = None
    inventory: List[int] = []


def _create_dungeon_player_dto(player_id: int):
    return DungeonPlayerDto(
        playerId=player_id,
        heroineId=random.randint(0, 2),
        currRoomId=random.randint(0, 5),
        difficulty=0,
        hp=250,
        moveSpeed=1,
        attackSpeed=1.0,
        passiveSkillIds=[0, 1],
        weaponId=0,
        inventory=[21, 42],
    )


class TalkDungeonRequest(BaseModel):
    dungeonPlayer: DungeonPlayerDto = Field(
        ...,
        description="던전 플레이어의 실시간 상태",
        example=_create_dungeon_player_dto(1),
    )

    question: str = Field(
        ..., description="사용자의 질문", example="현재 방의 불좀 켜줘"
    )

    targetMonsterIds: List[int] = Field(
        default_factory=list,
        description="히로인 시야에 있는 몬스터들 (사실 1개면 됨, 혹시 몰라 리스트로 열어둠)",
    )

    nextRoomIds: List[int] = Field(
        ..., description="히로인이 이동 가능한 방 ID 목록", example=1
    )


class TalkGuildRequest(BaseModel):
    playerId: int = Field(..., description="사용자 ID")
    heroine_id: int = Field(..., description="히로인 ID")
    memory_progress: int = Field(..., description="히로인 기억 해금 진척도")
    affection: int = Field(..., description="히로인 호감도")
    sanity: int = Field(..., description="히로인 정신력")
    question: str = Field(..., description="사용자의 질문")


class TalkResponse(BaseModel):
    response_text: str = Field(
        ..., description="현재 던전의 불을 켜드리겠습니다. 방이 밝아졌어요!"
    )


class InteractionRequest(BaseModel):
    inventory: List[int] = Field(
        ...,
        description="인벤토리 아이템 id 목록",
        example=[21, 47],
    )
    question: str = Field(..., description="사용자의 질문", example="현재 방 불좀 켜봐")


class InteractionResponse(BaseModel):
    roomLight: int = Field(
        ...,
        description="방 밝기 On/Off 여부 (정령 행동 필요 없으면 :0 , 불키기: 1, 불끄기: 2)",
        example=0,
    )
    isCheckNextRoom: bool = Field(
        ...,
        description="다음방 확인 시키기 여부(정령 행동 필요 없으면 False)",
        example=True,
    )
    useItemId: Optional[int] = Field(
        ..., description="사용 하려는 아이템 (정령 행동 필요 없으면 Null)", example=None
    )


def dungeon_player_dto_to_state(player_dto: DungeonPlayerDto) -> DungeonPlayerState:
    playerId = player_dto.playerId
    heroineId = player_dto.heroineId
    currRoomId = player_dto.currRoomId
    difficulty = player_dto.difficulty
    hp = player_dto.hp
    moveSpeed = player_dto.moveSpeed
    attackSpeed = player_dto.attackSpeed
    inventory = player_dto.inventory

    weapon = None
    weaponId = player_dto.weaponId
    item: Optional[ItemData] = get_inventory_item(weaponId)
    if item is not None:
        weapon = item.weapon

    return DungeonPlayerState(
        playerId=playerId,
        heroineId=heroineId,
        currRoomId=currRoomId,
        difficulty=difficulty,
        hp=hp,
        moveSpeed=moveSpeed,
        attackSpeed=attackSpeed,
        inventory=inventory,
        weapon=weapon,
    )


@router.post("/dungeon/talk", response_model=TalkResponse)
async def talk_dungeon(request: TalkDungeonRequest):
    """정령 - 던전 대화"""
    player_dto: DungeonPlayerDto = request.dungeonPlayer
    player = dungeon_player_dto_to_state(player_dto)

    question = request.question
    target_monster_ids = request.targetMonsterIds
    next_room_ids = request.nextRoomIds

    result_text = await fairy_dungeon_talk(
        player, question, target_monster_ids, next_room_ids
    )
    return TalkResponse(response_text=result_text)


@router.post("/dungeon/interaction", response_model=InteractionResponse)
def interaction(request: InteractionRequest):
    """정령 - 던전 인터렉션 요청"""
    question = request.question
    inventory = request.inventory
    response = fairy_interaction(inventory, question)

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
        playerId, question, heroine_id, affection, memory_progress, sanity
    )
    return TalkResponse(response_text=result_text)
