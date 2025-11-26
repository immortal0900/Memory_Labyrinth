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


def xml_block(tag: str, content: str, indent: int = 0):
    pad = " " * indent
    inner_pad = " " * (indent + 4)
    # content의 모든 줄을 자동으로 들여쓰기 맞추기
    normalized = "\n".join(f"{inner_pad}{line}" for line in content.split("\n"))
    return f"{pad}<{tag}>\n{normalized}\n{pad}</{tag}>"