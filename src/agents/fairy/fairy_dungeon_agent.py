from agents.fairy.fairy_state import (
    FairyDungeonIntentOutput,
    FairyDungeonState,
    FairyDungeonIntentType,
)
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import interrupt
from agents.fairy.cache_data import reverse_questions, GAME_SYSTEM_INFO
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
import random, asyncio
from agents.fairy.util import (
    add_ai_message,
    add_human_message,
    str_to_bool,
    get_groq_llm_lc,
    find_monsters_info,
)
from core.common import get_inventory_items
from enums.LLM import LLM
from langchain.chat_models import init_chat_model
from typing import List
from db.RDBRepository import RDBRepository
from db.rdb_entity.DungeonRow import DungeonRow
from agents.fairy.dynamic_prompt import dungeon_spec_prompt

intent_llm = get_groq_llm_lc(model=LLM.LLAMA_3_1_8B_INSTANT, max_token=43)
action_llm = get_groq_llm_lc(max_token=80,temperature=0)
small_talk_llm = init_chat_model(model=LLM.GROK_4_FAST_NON_REASONING)
rdb_repository = RDBRepository()

async def get_monsters_info(target_monster_ids: List[int]):
    return find_monsters_info(target_monster_ids)


async def get_event_info(dungeon_row: DungeonRow, curr_room_id: int):
    curr_room_id
    return dungeon_row.event


async def dungeon_navigator(dungeon_row: DungeonRow, curr_room_id: int):
    summary_info = dungeon_row.summary_info
    dungeon_json_prompt = dungeon_spec_prompt.format(
        balanced_map_json=dungeon_row.balanced_map
    )
    dungeon_map_prompt = f"        <던전맵>\n{dungeon_json_prompt}\n        </던전맵>"
    dungeon_summary_prompt = f"        <던전요약>\n{summary_info}\n        </던전요약>"
    dungeon_current_prompt = (
        f"        <현재 Room Id>\n{curr_room_id}\n        </현재 Room Id>"
    )
    total_prompt = (
        dungeon_map_prompt
        + "\n"
        + dungeon_summary_prompt
        + "\n"
        + dungeon_current_prompt
    )
    return total_prompt


async def create_interaction(inventory_ids):

    inventory_prompt = f"        <인벤토리 내의 아이템 설명>\n{get_inventory_items(inventory_ids)}\n        </인벤토리 내의 아이템 설명>"
    result = inventory_prompt
    return result


async def get_system_info():
    return GAME_SYSTEM_INFO


async def _clarify_intent(query) -> FairyDungeonIntentOutput:
    intent_prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_INTENT).get_prompt()
    messages = [SystemMessage(content=intent_prompt), HumanMessage(content=query)]
    parser_llm = intent_llm.with_structured_output(FairyDungeonIntentOutput)
    intent_output: FairyDungeonIntentOutput = await parser_llm.ainvoke(messages)
    print("전체 의도::", intent_output)
    return intent_output


async def analyze_intent(state: FairyDungeonState):
    last = state["messages"][-1]
    last_message = last.content
    clarify_intent_type: FairyDungeonIntentOutput = await _clarify_intent(last_message)

    if clarify_intent_type.intents[0] == FairyDungeonIntentType.UNKNOWN_INTENT:
        clarification = reverse_questions[random.randint(0, 148)]
        user_resp = interrupt(clarification)
        return {
            "messages": [
                add_ai_message(
                    content=clarification, intent_types=clarify_intent_type.intents
                ),
                add_human_message(content=user_resp),
            ],
            "intent_types": clarify_intent_type.intents,
            "is_multi_small_talk": False,
        }

    return {
        "intent_types": clarify_intent_type.intents,
    }


def check_condition(state: FairyDungeonState):
    intent_types = state.get("intent_types", [])
    if intent_types[0] == FairyDungeonIntentType.UNKNOWN_INTENT:
        return "retry"
    return "continue"


async def fairy_action(state: FairyDungeonState):
    intent_types = state.get("intent_types")
    dungenon_player = state["dungenon_player"]
    target_monster_ids = state.get("target_monster_ids", [])
    currRoomId = dungenon_player.currRoomId
    dungeon_row = rdb_repository.get_current_dungeon_by_player(
        dungenon_player.playerId, dungenon_player.heroineId
    )
    messages = state["messages"]
    INTENT_HANDLERS = {
        FairyDungeonIntentType.MONSTER_GUIDE: lambda: get_monsters_info(
            target_monster_ids
        ),
        FairyDungeonIntentType.EVENT_GUIDE: lambda: get_event_info(
            dungeon_row, currRoomId
        ),
        FairyDungeonIntentType.DUNGEON_NAVIGATOR: lambda: dungeon_navigator(
            dungeon_row, currRoomId
        ),
        FairyDungeonIntentType.INTERACTION_HANDLER: lambda: create_interaction(
            dungenon_player.inventory
        ),
        FairyDungeonIntentType.USAGE_GUIDE: get_system_info,
    }

    INTENT_LABELS = {
        FairyDungeonIntentType.MONSTER_GUIDE: "몬스터 정보",
        FairyDungeonIntentType.EVENT_GUIDE: "이벤트",
        FairyDungeonIntentType.DUNGEON_NAVIGATOR: "던전 안내",
        FairyDungeonIntentType.INTERACTION_HANDLER: "상호작용",
        FairyDungeonIntentType.USAGE_GUIDE: "사용 방법·조작 안내",
    }

    handlers = [INTENT_HANDLERS[i]() for i in intent_types if i in INTENT_HANDLERS]
    results = await asyncio.gather(*handlers)

    prompt_info = ""
    idx = 0
    for i, index in enumerate(intent_types):
        handler = INTENT_HANDLERS.get(index)
        if not handler:
            continue

        value = results[idx]
        label = INTENT_LABELS.get(index, "정보")
        if i == 0:
            prompt_info += f"    <{label}>\n{value}\n    </{label}>"
        else:
            prompt_info += f"\n    <{label}>\n{value}\n    </{label}>"
        idx += 1

    pretty_dungenon_player = dungenon_player.model_dump_json(indent=2)
    system_prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_SYSTEM).get_prompt()

    question = messages[-1].content
    human_prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_HUMAN).get_prompt(
        dungenon_player=pretty_dungenon_player,
        use_intents=[rt.value if hasattr(rt, "value") else rt for rt in intent_types],
        info=prompt_info,
        question=question,
    )

    print("check_prompt::", human_prompt)

    if intent_types[0] == FairyDungeonIntentType.SMALLTALK and len(intent_types) == 1:
        ai_answer = small_talk_llm.invoke(
            [SystemMessage(content=system_prompt)]
            + messages
            + [HumanMessage(content=human_prompt)]
        )
    else:
        ai_answer = action_llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]
        )
    return {
        "messages": [
            add_ai_message(content=ai_answer.content, intent_types=intent_types)
        ]
    }


from langgraph.graph import START, END, StateGraph

graph_builder = StateGraph(FairyDungeonState)

graph_builder.add_node("analyze_intent", analyze_intent)
graph_builder.add_node("fairy_action", fairy_action)
# graph_builder.add_node("multi_small_talk", multi_small_talk_node)

graph_builder.add_edge(START, "analyze_intent")

graph_builder.add_conditional_edges(
    "analyze_intent",
    check_condition,
    {
        "retry": "analyze_intent",
        "continue": "fairy_action",
    },
)
graph_builder.add_edge("fairy_action", END)
