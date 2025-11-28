from pydantic import BaseModel, Field
from typing import List, Optional,Dict
from enum import StrEnum
from core.game_dto.DungeonPlayerData import DungeonPlayerData



class FairyIntentType(StrEnum):
    MONSTER_GUIDE = "MONSTER_GUIDE"
    EVENT_GUIDE = "EVENT_GUIDE"
    DUNGEON_NAVIGATOR = "DUNGEON_NAVIGATOR"
    INTERACTION_HANDLER = "INTERACTION_HANDLER"
    SMALLTALK = "SMALLTALK"
    UNKNOWN_INTENT = "UNKNOWN_INTENT"


class FairyIntentOutput(BaseModel):
    intents: List[FairyIntentType] = Field(
        description="선택된 라우터 타입들의 목록 (질문에 여러 의도가 섞여있으면 다중 선택 가능)"
    )


from langgraph.graph import MessagesState
from pydantic import BaseModel, Field


class FairyState(MessagesState):
    intent_types: List[FairyIntentType] = []
    dungenon_player:Optional[DungeonPlayerData] = None
    targetMonsterIds:List[int] = []
    is_multi_small_talk: bool = False

class FairyInteractionState(BaseModel):
    roomRightOn: Optional[bool] = None
    isCheckNextRoom:bool = False


    




