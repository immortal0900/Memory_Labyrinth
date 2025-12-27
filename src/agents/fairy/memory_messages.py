from db.RDBRepository import RDBRepository
from typing import Dict, Any,List
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
import json

def get_fairy_messages_dungeon(
    player_id:str,
    heroine_id:str,
    limit: int = 20,
) -> List[BaseMessage]:
    rows = RDBRepository().get_fairy_messages_for_memory(
        player_id=player_id,
        heroine_id=heroine_id,
        context_type = "DUNGEON",
        limit= limit
    )
    rows = list(reversed(rows))

    messages: List[BaseMessage] = []

    for r in rows:
        sender = (r.get("sender_type") or "").upper()
        content = r.get("message") or ""

    
        additional_kwargs: Dict[str, Any] = {}

        created_at = r.get("created_at")
        if created_at is not None:
            additional_kwargs["created_at"] = (
                created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
            )

        intent_raw = r.get("intent_type")
        if intent_raw:
            try:
                additional_kwargs["intent_types"] = json.loads(intent_raw)
            except Exception:
                additional_kwargs["intent_types"] = intent_raw  # 깨진 경우 raw로라도 넣기

        if sender == "AI":
            messages.append(AIMessage(content=content, additional_kwargs=additional_kwargs))
        else:
            # 기본 USER로 처리
            messages.append(HumanMessage(content=content, additional_kwargs=additional_kwargs))

    return messages