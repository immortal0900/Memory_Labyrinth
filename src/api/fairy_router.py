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
    playerId: str
    heroineId: int
    currRoomId: int
    difficulty: int = 0
    stats: StatData
    skillIds: List[int]
    weaponId: int = None
    subWeaponId: int = None
    inventory: List[int] = []


def _create_dungeon_player_dto(player_id: str):
    return DungeonPlayerDto(
        playerId=player_id,
        heroineId=random.randint(0, 2),
        currRoomId=random.randint(0, 5),
        difficulty=0,
        stats=StatData(strength=1, dexterity=1, intelligence=None),
        skillIds=[0, 1],
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
        example=_create_dungeon_player_dto("1"),
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
    playerId: str = Field(..., description="사용자 ID")
    heroine_id: int = Field(..., description="히로인 ID")
    memory_progress: int = Field(..., description="히로인 기억 해금 진척도")
    affection: int = Field(..., description="히로인 호감도")
    sanity: int = Field(..., description="히로인 정신력")
    question: str = Field(..., description="사용자의 질문")


class TalkResponse(BaseModel):
    responseText: str = Field(
        ..., description="현재 던전의 불을 켜드리겠습니다. 방이 밝아졌어요!"
    )


class InteractionRequest(BaseModel):
    inventory: List[int] = Field(
        ...,
        description="인벤토리 아이템 id 목록",
        example=[21, 47],
    )
    weapon_id: Optional[int] = None
    sub_weapon_id: Optional[int] = None
    question: str = Field(..., description="사용자의 질문", example="현재 방 불좀 켜봐")


class InteractionResponse(BaseModel):
    roomLight: int = Field(
        ...,
        description="방 밝기 On/Off 여부 (정령 행동 필요 없으면 :0 , 불키기: 1, 불끄기: 2)",
        example=0,
    )
    useItemId: Optional[int] = Field(
        ..., description="사용 하려는 아이템 (정령 행동 필요 없으면 Null)", example=None
    )


def _weapon_id_to_data(weapon_id: Optional[int]) -> Optional[WeaponData]:
    weapon = None
    weapon_id = weapon_id
    item: Optional[ItemData] = get_inventory_item(weapon_id)
    if item is not None:
        weapon = item.weapon
    return weapon


def dungeon_player_dto_to_state(player_dto: DungeonPlayerDto) -> DungeonPlayerState:
    playerId = player_dto.playerId
    heroineId = player_dto.heroineId
    currRoomId = player_dto.currRoomId
    difficulty = player_dto.difficulty
    stats = player_dto.stats
    hp = stats.hp
    moveSpeed = stats.moveSpeed
    attackSpeed = stats.attackSpeed
    cooldownReduction = stats.cooldownReduction
    strength = stats.strength
    dexterity = stats.dexterity
    intelligence = stats.intelligence
    critChance = stats.critChance
    skillDamageMultiplier = stats.skillDamageMultiplier
    autoAttackMultiplier = stats.autoAttackMultiplier
    skillIds = player_dto.skillIds
    inventory = player_dto.inventory
    weapon = _weapon_id_to_data(player_dto.weaponId)
    sub_weapon = _weapon_id_to_data(player_dto.subWeaponId)

    return DungeonPlayerState(
        playerId=playerId,
        heroineId=heroineId,
        currRoomId=currRoomId,
        difficulty=difficulty,
        hp=hp,
        moveSpeed=moveSpeed,
        attackSpeed=attackSpeed,
        cooldownReduction=cooldownReduction,
        strength=strength,
        dexterity=dexterity,
        intelligence=intelligence,
        critChance=critChance,
        skillDamageMultiplier=skillDamageMultiplier,
        autoAttackMultiplier=autoAttackMultiplier,
        skillIds=skillIds,
        inventory=inventory,
        weapon=weapon,
        sub_weapon=sub_weapon,
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
    return TalkResponse(responseText=result_text)


@router.post("/dungeon/interaction", response_model=InteractionResponse)
def interaction(request: InteractionRequest):
    """정령 - 던전 인터렉션 요청"""
    question = request.question
    inventory = request.inventory
    weapon = _weapon_id_to_data(request.weapon_id)
    sub_weapon = _weapon_id_to_data(request.sub_weapon_id)
    response = fairy_interaction(inventory, question, weapon, sub_weapon)

    useItemId = response["useItemId"]
    roomLight = response["roomLight"]

    return InteractionResponse(
        useItemId=useItemId,
        roomLight=roomLight,
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
    return TalkResponse(responseText=result_text)


from fastapi import UploadFile, File
import time


@router.post("/upload-wav")
async def upload_wav(file: UploadFile = File(...)):
    start_time = time.time()

    # WAV 파일인지 최소 체크
    if not file.filename.endswith(".wav"):
        return {"error": "Only .wav files are allowed"}

    contents = await file.read()

    # (선택) 파일 저장
    elapsed_ms = (time.time() - start_time) * 1000

    return {
        "filename": file.filename,
        "size_bytes": len(contents),
        "server_elapsed_ms": round(elapsed_ms, 2),
    }
