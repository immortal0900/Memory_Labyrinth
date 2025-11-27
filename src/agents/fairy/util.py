from langchain_core.messages import AIMessage,HumanMessage
from agents.fairy.fairy_state import FairyIntentType
from datetime import datetime
from typing import List

def add_ai_message(content:str, intent_types:List[FairyIntentType]):
    return AIMessage(
        content=content,
        additional_kwargs={
            "created_at": datetime.now().isoformat(),
            "intent_types": [i.value for i in intent_types]
        }
    )

def add_human_message(content:str):
    return HumanMessage(
        content=content,
        additional_kwargs={
            "created_at": datetime.now().isoformat()
        }
    )

def str_to_bool(text):
    if text == "True":
        return True
    else:
        return False

def get_small_talk_history(msgs):
    return [
        msg 
        for prev, curr in zip(msgs, msgs[1:]) 
        if isinstance(curr, AIMessage) and "SMALLTALK" in curr.additional_kwargs.get("intent_types", [])
        for msg in (prev, curr)
    ]