from pydantic import BaseModel, Field
from typing import List, Optional, TypedDict
from enum import StrEnum
from core.game_dto.DungeonPlayerData import DungeonPlayerData
from langgraph.graph import MessagesState

class FairyState(TypedDict):
    player_id:Optional[str]
    hiroine_id:Optional[str]
    question:Optional[str]
    answer:Optional[str]

# ==== START 던전 =====
class FairyDungeonIntentType(StrEnum):
    MONSTER_GUIDE = "MONSTER_GUIDE"
    EVENT_GUIDE = "EVENT_GUIDE"
    DUNGEON_NAVIGATOR = "DUNGEON_NAVIGATOR"
    INTERACTION_HANDLER = "INTERACTION_HANDLER"
    GAME_SYSTEM_INFO = "GAME_SYSTEM_INFO"
    SMALLTALK = "SMALLTALK"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"

class FairyDungeonIntentOutput(BaseModel):
    intents: List[FairyDungeonIntentType] = Field(
        description="선택된 의도 타입들의 목록 (질문에 여러 의도가 섞여있으면 다중 선택 가능)"
    )

class FairyDungeonState(MessagesState):
    intent_types: List[FairyDungeonIntentType] = []
    dungenon_player: Optional[DungeonPlayerData] = None
    targetMonsterIds: List[int] = []
    is_multi_small_talk: bool = False

class FairyInterationIntentType(StrEnum):
    INVENTORY_ITEM_USE = "INVENTORY_ITEM_USE"
    LIGHT_ON_ROOM = "LIGHT_ON_ROOM"
    LIGHT_OFF_ROOM = "LIGHT_OFF_ROOM"
    MOVE_NEXT_ROOM = "MOVE_NEXT_ROOM"
    NONE = "NONE"

class FairyInterationIntentOutput(BaseModel):
    intents: List[FairyInterationIntentType] = Field(
        description="선택된 요청 타입들의 목록 (질문에 여러 의도가 섞여있으면 다중 선택 가능)"
    )

class FairyInteractionState(MessagesState):
    inventory: List[int] = []
    roomLight: Optional[bool] = None
    isCheckNextRoom: bool = False
    useItemId: Optional[int] = None
    intent_types: List[FairyInterationIntentType]
    temp_use_item_id: Optional[int] = None

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