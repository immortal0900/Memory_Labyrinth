from pydantic import BaseModel, Field
from typing import List, Optional
from enum import StrEnum


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
    intent_types: List[FairyIntentType]
    is_multi_turn: bool = False


class FairyInteraction(BaseModel):
    room_right_on: Optional[bool] = Field(description="던전 방 불 밝히기 여부")


class FairyOutput(BaseModel):
    response: str = Field(description="요정의 대답")
    use_intents: List[FairyIntentType] = Field(
        description="사용하려는 정령의 능력 목록"
    )
    interation: Optional[FairyInteraction] = Field(
        description="사용하려는 능력 중 'INTERACTION_HANDLER'가 포함되어 있을 시 정보 (기본 None)"
    )
