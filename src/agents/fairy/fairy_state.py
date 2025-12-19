from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from enum import StrEnum
from langgraph.graph import MessagesState
from core.game_dto.WeaponData import WeaponData

# ==== START 던전 =====
class DungeonPlayerState(BaseModel):
    playerId: str
    heroineId: int
    currRoomId: int
    difficulty: int 
    hp: int = 250,
    moveSpeed: float = 1,
    attackSpeed: float = 1.0,
    weapon: Optional[WeaponData] = None
    sub_weapon:Optional[WeaponData] = None
    inventory: List[int] = []

class FairyDungeonIntentType(StrEnum):
    MONSTER_GUIDE = "MONSTER_GUIDE"
    EVENT_GUIDE = "EVENT_GUIDE"
    DUNGEON_NAVIGATOR = "DUNGEON_NAVIGATOR"
    INTERACTION_HANDLER = "INTERACTION_HANDLER"
    USAGE_GUIDE = "USAGE_GUIDE"
    SMALLTALK = "SMALLTALK"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"

class FairyDungeonIntentOutput(BaseModel):
    intents: List[FairyDungeonIntentType] = Field(
        description="선택된 의도 타입들의 목록 (질문에 여러 의도가 섞여있으면 다중 선택 가능)"
    )

class FairyDungeonState(MessagesState):
    intent_types: List[FairyDungeonIntentType] = []
    dungenon_player: Optional[DungeonPlayerState] = None
    target_monster_ids: List[int] = []
    player_id:Optional[int] = None
    next_room_ids: List[int] = []
    latency_analyze_intent: float = 0.0
    latency_fairy_action:float = 0.0

class FairyInterationIntentType(StrEnum):
    INVENTORY_ITEM_USE = "INVENTORY_ITEM_USE"
    LIGHT_ON_ROOM = "LIGHT_ON_ROOM"
    LIGHT_OFF_ROOM = "LIGHT_OFF_ROOM"
    NONE = "NONE"

class FairyInterationIntentOutput(BaseModel):
    intents: List[FairyInterationIntentType] = Field(
        description="선택된 요청 타입들의 목록 (질문에 여러 의도가 섞여있으면 다중 선택 가능)"
    )

class FairyInteractionState(MessagesState):
    inventory: List[int] = []
    weapon: Optional[WeaponData] = None
    sub_weapon:Optional[WeaponData] = None
    # 0 은 미행동, 1은 불키기, 2은 불끄기
    roomLight: int = 0
    useItemId: Optional[int] = None
    is_item_use: bool = False
    intent_types: List[FairyInterationIntentType]
    temp_use_item_id: Optional[int] = None
    latency_analyze_intent: float = 0.0
    latency_create_temp_use_item_id:float = 0.0
    latency_check_use_item:float = 0.0 

class FairyItemUseOutput(BaseModel):
    item_id: Optional[int] = Field(description="사용하려는 item의 id", default=None)
# ==== END 던전 =====

# ==== START 길드 =====
class FairyGuildIntentType(StrEnum):
    GAME_SYSTEM_INFO = "GAME_SYSTEM_INFO"
    HEROINE_MEMORY_INFO = "HEROINE_MEMORY_INFO"
    SMALLTALK = "SMALLTALK"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"

class FairyGuildIntentOutput(BaseModel):
    intents: List[FairyGuildIntentType] = Field(
        description="선택된 의도 타입들의 목록 (질문에 여러 의도가 섞여있으면 다중 선택 가능)"
    )

class FairyGuildState(MessagesState):
    reasoning_required:bool = False
# ==== END 길드 =====