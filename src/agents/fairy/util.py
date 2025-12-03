from langchain_core.messages import AIMessage, HumanMessage
from agents.fairy.fairy_state import FairyDungeonIntentType
from datetime import datetime
from typing import List, Optional, Dict, Any


def add_ai_message(content: str, intent_types: List[FairyDungeonIntentType]):
    return AIMessage(
        content=content,
        additional_kwargs={
            "created_at": datetime.now().isoformat(),
            "intent_types": [i.value for i in intent_types],
        },
    )

def add_human_message(content: str):
    return HumanMessage(
        content=content, additional_kwargs={"created_at": datetime.now().isoformat()}
    )


def str_to_bool(text):
    if text == "True" or text == "true":
        return True
    else:
        return False

def get_small_talk_history(msgs):
    return [
        msg
        for prev, curr in zip(msgs, msgs[1:])
        if isinstance(curr, AIMessage)
        and "SMALLTALK" in curr.additional_kwargs.get("intent_types", [])
        for msg in (prev, curr)
    ]

def stream_action_llm(
    model="llama-3.3-70b-versatile", system_prompt=None, question=None
):
    if system_prompt is None or question is None:
        raise RuntimeError("시스템 프롬프트 혹은 질문 프롬프트가 필요합니다.")

    import os
    from dotenv import load_dotenv

    load_dotenv()
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_completion_tokens=200,
        top_p=1,
        stream=True,
        stop=None,
    )

    for chunk in completion:
        content = chunk.choices[0].delta.content
        if content:
            yield content


from langchain_groq import ChatGroq
from enums.LLM import LLM
def get_groq_llm_lc(
    model: LLM = LLM.LLAMA_3_3_70B_VERSATILE, max_token=200, temperature=0
):
    import os
    from dotenv import load_dotenv
    load_dotenv()
    llm = ChatGroq(
        model=model,
        api_key=os.environ.get("GROQ_API_KEY"),
        temperature=temperature,
        max_tokens=max_token,
        top_p=1,
    )
    return llm

from agents.fairy.cache_data import HEROINE_SCENARIOS, HEROINE_INFOS
from typing import List, Dict, Any

def find_scenarios(heroine_id: int, memory_progress: int) -> List[Dict[str, Any]]:
    progresses = list(range(10, memory_progress + 1, 10))

    return [
        s for s in HEROINE_SCENARIOS
        if s["heroine_id"] == heroine_id and s["memory_progress"] in progresses
    ]




def find_heroine_info(heroine_id: int):
    for hero in HEROINE_INFOS:
        if hero["heroine_id"] == heroine_id:
            return hero
    return None
