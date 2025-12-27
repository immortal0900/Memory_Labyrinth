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

def get_last_human_message(messages):
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content
    return None

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

from groq import Groq
from langchain_core.messages import BaseMessage
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
def lc_messages_to_groq(messages: List[BaseMessage]) -> List[Dict]:
    groq_messages = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, ToolMessage):
            role = "tool"
        else:
            raise ValueError(f"Unsupported message type: {type(msg)}")

        groq_messages.append({
            "role": role,
            "content": msg.content
        })

    return groq_messages

def get_groq_gpt(messeages:List[BaseMessage]):
    groq_messages = lc_messages_to_groq(messeages)
    client = Groq()
    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=groq_messages
    )
    return completion.choices[0].message.content

from agents.fairy.cache_data import HEROINE_SCENARIOS, HEROINE_INFOS, MONSTER_INFOS, SKILL_INFOS
from typing import List, Dict, Any

def find_scenarios(heroine_id: int, memory_progress: int) -> List[Dict[str, Any]]:
    progresses = list(range(10, memory_progress + 1, 10))
    return [
        s for s in HEROINE_SCENARIOS
        if s["heroine_id"] == heroine_id and s["memory_progress"] in progresses
    ]


def find_skill_info(skill_ids: list[int]):
    results = []
    for skil in SKILL_INFOS:
        if skil["monsterId"] in skill_ids:
            results.append(skil)
    return results

def find_monsters_info(monster_ids: list[int]):
    results = []
    for monster in MONSTER_INFOS:
        if monster["monsterId"] in monster_ids:
            results.append(monster)
    return results

def find_heroine_info(heroine_id: int):
    for hero in HEROINE_INFOS:
        if hero["heroine_id"] == heroine_id:
            return hero
    return None

def contains_hanja(text: str) -> bool:
    # CJK Unified Ideographs 범위 (대부분의 한자/칸지)
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)

def replace_hanja_naively(text: str) -> str:
    # 일단 한자 자체는 제거하거나, 특수 토큰으로 바꿀 수 있음
    # 여기서는 일단 제거 예시
    return ''.join(ch for ch in text if not ('\u4e00' <= ch <= '\u9fff'))

from agents.fairy.dynamic_prompt import FAIRY_DUNGEON_FEW_SHOTS
from typing import Iterable
from agents.fairy.fairy_state import FairyDungeonIntentType
def get_human_few_shot_prompts(use_intents: Iterable[FairyDungeonIntentType]) -> str:
    """
    use_intents 리스트에 들어 있는 능력(MONSTER_GUIDE 등)에 해당하는
    예시 블록만 골라서 하나의 문자열로 합쳐서 반환한다.
    """
    blocks: list[str] = []
    
    for ability in use_intents:
        text = FAIRY_DUNGEON_FEW_SHOTS.get(ability)
        if not text:
            continue

        header = f"### [{ability.value} - Answer Example]"
        formatted = f"{header}\n{text.strip()}"
        blocks.append(formatted)

    if not blocks:
        return ""

    return "\n\n".join(blocks)


from typing import Any, Dict
def describe_dungeon_row(
    curr_room_id: int,
    balanced_map: Dict[str, Any],
    floor: int,
) -> str:
    rooms = balanced_map.get("rooms", [])
    curr = next(r for r in rooms if r.get("room_id") == curr_room_id)

    room_type_map = {
        "empty": "an empty room with nothing inside",
        "monster": "a room where combat occurs",
        "event": "an event room where something special happens",
        "treasure": "a room containing treasure",
        "boss": "a room where a boss awaits",
    }

    room_type_short = {
        "empty": "Empty Room",
        "monster": "Combat Room",
        "event": "Event Room",
        "treasure": "Treasure Room",
        "boss": "Boss Room",
    }

    room_type = curr.get("room_type", "unknown")
    room_type_en = room_type_map.get(room_type, "a room of unknown nature")

    neighbor_ids = curr.get("neighbors", []) or []
    neighbor_rooms = [r for r in rooms if r.get("room_id") in neighbor_ids]

    if not neighbor_rooms:
        move_text = "There is no defined information about rooms connected to the current room."
    else:
        lines: list[str] = []
        for nr in neighbor_rooms:
            n_type = nr.get("room_type", "unknown")
            n_type_en = room_type_short.get(n_type, "Unknown Room")
            size = nr.get("size")

            # Monster count hint only for combat/boss rooms
            monsters = nr.get("monsters") or []
            monster_hint = ""
            if n_type in ("monster", "boss") and monsters:
                monster_hint = f", {len(monsters)} monster(s) deployed"

            lines.append(f"- {n_type_en} (size {size}{monster_hint})")

        move_text = "\n".join(lines)

    total_rooms = len(rooms)
    type_counts = {"empty": 0, "monster": 0, "event": 0, "boss": 0}
    for room in rooms:
        t = room.get("room_type")
        if t in type_counts:
            type_counts[t] += 1

    dungeon_lines: list[str] = []
    dungeon_lines.append(
        "This information describes the overall structure of the dungeon, "
        "including room types, connections, and monster placements."
    )
    dungeon_lines.append("")
    dungeon_lines.append(f"- Current dungeon floor: Floor {floor}")
    dungeon_lines.append(f"- Total number of rooms: {total_rooms}")
    dungeon_lines.append(
        "- Room type counts: "
        "Empty Rooms {empty}, Combat Rooms {monster}, "
        "Event Rooms {event}, Boss Rooms {boss}".format(**type_counts)
    )

    dungeon_lines.append("")
    dungeon_lines.append("[Current Room]")
    dungeon_lines.append(f"- Room type: {room_type_en}")
    dungeon_lines.append(f"- Room size: {curr.get('size')}")

    dungeon_lines.append("")
    dungeon_lines.append("[Rooms Connected to the Current Room]")
    if not neighbor_rooms:
        dungeon_lines.append("- No connected rooms are defined.")
    else:
        dungeon_lines.append(move_text)

    dungeon_lines.append("")
    dungeon_lines.append("[Overall Room Structure Summary]")
    dungeon_lines.append(
        "The following information summarizes each room, its type, "
        "and what kinds of rooms it is connected to."
    )

    # Multiple rooms of the same type may exist, so distinguish them
    seen_count: Dict[str, int] = {
        "empty": 0,
        "monster": 0,
        "event": 0,
        "treasure": 0,
        "boss": 0,
    }

    for room in rooms:
        r_type = room.get("room_type", "unknown")
        if r_type not in room_type_short:
            continue

        seen_count[r_type] += 1
        base_name = room_type_short[r_type]

        if seen_count[r_type] == 1:
            name = f"One {base_name}"
        else:
            name = f"Another {base_name}"

        size = room.get("size")
        n_ids = room.get("neighbors", []) or []
        n_rooms = [rr for rr in rooms if rr.get("room_id") in n_ids]

        # Monster hint for combat/boss rooms only
        monsters = room.get("monsters") or []
        monster_hint = ""
        if r_type in ("monster", "boss") and monsters:
            monster_hint = f", {len(monsters)} monster(s) deployed"

        if not n_rooms:
            line = (
                f"- {name} (size {size}{monster_hint}) has no defined connections to other rooms."
            )
        else:
            neighbor_types = []
            for nr in n_rooms:
                nt = nr.get("room_type", "unknown")
                if nt in room_type_short:
                    neighbor_types.append(room_type_short[nt])

            # Remove duplicates while preserving order
            neighbor_types = list(dict.fromkeys(neighbor_types))
            neighbor_text = ", ".join(neighbor_types)

            line = (
                f"- {name} (size {size}{monster_hint}) is connected to "
                f"{neighbor_text}."
            )

        dungeon_lines.append(line)

    return "\n".join(dungeon_lines)


import time

def measure_latency(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        latency = (end - start)
        return result, latency
    return wrapper
