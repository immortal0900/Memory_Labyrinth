
from agents.fairy.fairy_state import FairyDungeonIntentOutput, FairyDungeonState, FairyDungeonIntentType
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import interrupt
from agents.fairy.cache_data import reverse_questions, GAME_SYSTEM_INFO
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
import random, asyncio
from agents.fairy.util import (
    add_ai_message,
    add_human_message,
    str_to_bool,
    get_small_talk_history,
    get_groq_llm_lc,
)
from core.common import get_inventory_items
from enums.LLM import LLM
from langchain.chat_models import init_chat_model


check_multi_llm = get_groq_llm_lc(model=LLM.LLAMA_3_1_8B_INSTANT, max_token=8)
intent_llm = get_groq_llm_lc(model=LLM.LLAMA_3_1_8B_INSTANT, max_token=43)
action_llm = get_groq_llm_lc()
# small_talk_llm = get_groq_llm_lc(temperature=0.4)
small_talk_llm = init_chat_model(model=LLM.GPT4_1_MINI, temperature=0.4)


async def monster_rag():
    return "asd"

async def get_event_info():
    return "asdasd"

async def dungeon_navigator():
    return "dungeon_navi"


async def create_interaction(inventory_ids):
    #  items_descriptions = []
    #  for item in get_inventory_items(inventory_ids):
    #      items_descriptions.append(item.model_dump_json(indent=2))
    inventory_prompt = f"        <인벤토리 내의 아이템 설명>\n{get_inventory_items(inventory_ids)}\n        </인벤토리 내의 아이템 설명>"

    result = inventory_prompt
    return result

async def get_system_info():
    return GAME_SYSTEM_INFO

async def _clarify_intent(query):
    intent_prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_INTENT).get_prompt()
    messages = [SystemMessage(content=intent_prompt), HumanMessage(content=query)]
    parser_llm = intent_llm.with_structured_output(FairyDungeonIntentOutput)
    intent_output: FairyDungeonIntentOutput = await parser_llm.ainvoke(messages)
    return intent_output


async def check_memory_question(query: str) -> bool:
    prompt = PromptManager(FairyPromptType.QUESTION_HISTORY_CHECK).get_prompt(
        question=query
    )
    reponse = await check_multi_llm.ainvoke(prompt)
    return str_to_bool(reponse.content)



async def analyze_intent(state: FairyDungeonState):
    last = state["messages"][-1]
    last_message = last.content
    print("질문",last_message)
    clarify_intent_type, is_question_memory = await asyncio.gather(
        _clarify_intent(last_message), check_memory_question(last_message)
    )

    if clarify_intent_type.intents[0] == FairyDungeonIntentType.UNKNOWN_INTENT:
        clarification = reverse_questions[random.randint(0, 49)]
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
    print("의도 포함",FairyDungeonIntentType.SMALLTALK in clarify_intent_type.intents)
    print("체크 메모리",is_question_memory)
    is_multi_small_talk = (
        FairyDungeonIntentType.SMALLTALK in clarify_intent_type.intents
    ) and is_question_memory
    print("멀티턴", is_multi_small_talk)
    return {
        "intent_types": clarify_intent_type.intents,
        "is_multi_small_talk": is_multi_small_talk,
    }


def check_condition(state: FairyDungeonState):
    intent_types = state.get("intent_types", [])
    is_multi_small_talk = state.get("is_multi_small_talk", False)
    if intent_types[0] == FairyDungeonIntentType.UNKNOWN_INTENT:
        return "retry"

    if is_multi_small_talk:
        print("아래의 멀티턴", is_multi_small_talk)
        return "multi_small_talk"

    print("2")
    return "continue"


from agents.fairy.util import get_small_talk_history


def multi_small_talk_node(state: FairyDungeonState):
    intent_types = state.get("intent_types")
    player = state["dungenon_player"]
    histories = get_small_talk_history(state["messages"])
    prompt = PromptManager(FairyPromptType.FAIRY_MULTI_SMALL_TALK).get_prompt(
        location="던전", dungenon_player=player, histories=histories
    )
    question = state["messages"][-1].content
    action_llm.invoke([SystemMessage(content=prompt), HumanMessage(content=question)])

    ai_answer = small_talk_llm.invoke(prompt)
    return {
        "messages": [
            add_ai_message(content=ai_answer.content, intent_types=intent_types)
        ]
    }


async def fairy_action(state: FairyDungeonState):
    intent_types = state.get("intent_types")
    dungenon_player = state["dungenon_player"]
    INTENT_HANDLERS = {
        FairyDungeonIntentType.MONSTER_GUIDE: monster_rag,
        FairyDungeonIntentType.EVENT_GUIDE: get_event_info,
        FairyDungeonIntentType.DUNGEON_NAVIGATOR: dungeon_navigator,
        FairyDungeonIntentType.INTERACTION_HANDLER: lambda: create_interaction(
            dungenon_player.inventory
        ),
        FairyDungeonIntentType.GAME_SYSTEM_INFO: get_system_info
    }

    INTENT_LABELS = {
        FairyDungeonIntentType.MONSTER_GUIDE: "몬스터 공략",
        FairyDungeonIntentType.EVENT_GUIDE: "이벤트",
        FairyDungeonIntentType.DUNGEON_NAVIGATOR: "길안내",
        FairyDungeonIntentType.INTERACTION_HANDLER: "상호작용",
        FairyDungeonIntentType.GAME_SYSTEM_INFO: "게임 시스템 정보"
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
    prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_SYSTEM).get_prompt(
        dungenon_player=pretty_dungenon_player,
        use_intents=[rt.value if hasattr(rt, "value") else rt for rt in intent_types],
        info=prompt_info,
    )

    ai_answer = action_llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=state["messages"][-1].content),
        ]
    )

    # print(prompt)
    # print("*" * 100)
    # print(f"\n{ai_answer}")
    return {
        "messages": [
            add_ai_message(content=ai_answer.content, intent_types=intent_types)
        ]
    }


from langgraph.graph import START, END, StateGraph

graph_builder = StateGraph(FairyDungeonState)

graph_builder.add_node("analyze_intent", analyze_intent)
graph_builder.add_node("fairy_action", fairy_action)
graph_builder.add_node("multi_small_talk", multi_small_talk_node)

graph_builder.add_edge(START, "analyze_intent")

graph_builder.add_conditional_edges(
    "analyze_intent",
    check_condition,
    {
        "retry": "analyze_intent",
        "multi_small_talk": "multi_small_talk",
        "continue": "fairy_action",
    },
)
graph_builder.add_edge("fairy_action", END)
