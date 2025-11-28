
from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from agents.fairy.fairy_state import FairyIntentOutput, FairyState, FairyIntentType
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command, interrupt
from agents.fairy.cache_data import reverse_questions
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
import random, asyncio
from agents.fairy.util import add_ai_message, add_human_message, str_to_bool
from agents.fairy.util import get_small_talk_history
from core.common import get_inventory_items
from core.game_dto.DungeonPlayerData import DungeonPlayerData


helper_llm = init_chat_model(model=LLM.GPT4_1_MINI, temperature=0)
small_talk_llm = init_chat_model(model=LLM.GPT4_1_MINI, temperature=0.4)


async def monster_rag():
    return "asd"


async def item_list():
    return ""


async def get_event_info():
    return "asdasd"


async def dungeon_navigator():
    return "dungeon_navi"

async def create_interaction(inventory_ids):
    #  items_descriptions = []
    #  for item in get_inventory_items(inventory_ids):
    #      items_descriptions.append(item.model_dump_json(indent=2))    
     inventory_prompt = f"\n        <인벤토리 내의 아이템 설명>\n{get_inventory_items(inventory_ids)}\n        </인벤토리 내의 아이템 설명>"
     result = inventory_prompt 
     return result 


async def clarify_intent(query):
    intent_prompt = PromptManager(FairyPromptType.FAIRY_INTENT).get_prompt(
        question=query
    )
    parser_intent_llm = helper_llm.with_structured_output(FairyIntentOutput)
    intent_output: FairyIntentOutput = await parser_intent_llm.ainvoke(intent_prompt)
    return intent_output


async def check_memory_question(query: str):
    prompt = PromptManager(FairyPromptType.QUESTION_HISTORY_CHECK).get_prompt(
        question=query
    )
    reponse = await helper_llm.ainvoke(prompt)
    return str_to_bool(reponse.content)


async def analyze_intent(state: FairyState):
    last = state["messages"][-1]
    last_message = last.content

    clarify_intent_type, is_question_memory = await asyncio.gather(
        clarify_intent(last_message), check_memory_question(last_message)
    )

    if clarify_intent_type.intents[0] == FairyIntentType.UNKNOWN_INTENT:
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

    return {
        "intent_types": clarify_intent_type.intents,
        "is_multi_small_talk": clarify_intent_type.intents[0]
        == FairyIntentType.SMALLTALK
        and is_question_memory,
    }


def check_condition(state: FairyState):
    intent_types = state.get("intent_types", [])
    is_multi_small_talk = state.get("is_multi_small_talk", False)
    if intent_types[0] == FairyIntentType.UNKNOWN_INTENT:
        return "retry"

    if intent_types[0] == FairyIntentType.SMALLTALK and is_multi_small_talk:
        return "multi_small_talk"

    return "continue"


from agents.fairy.util import get_small_talk_history
def multi_small_talk_node(state: FairyState):
    intent_types = state.get("intent_types")
    player = state["dungenon_player"]
    histories = get_small_talk_history(state["messages"])
    question = state["messages"][-1]
    prompt = PromptManager(FairyPromptType.FAIRY_MULTI_SMALL_TALK).get_prompt(
        location="던전", dungenon_player=player, histories=histories, question=question
    )
    ai_answer = small_talk_llm.invoke(prompt)
    return {
        "messages": [
            add_ai_message(content=ai_answer.content, intent_types=intent_types)
        ]
    }


async def fairy_action(state: FairyState):
    intent_types = state.get("intent_types")
    dungenon_player = state["dungenon_player"]
    INTENT_HANDLERS = {
        FairyIntentType.MONSTER_GUIDE: monster_rag,
        FairyIntentType.EVENT_GUIDE: get_event_info,
        FairyIntentType.DUNGEON_NAVIGATOR: dungeon_navigator,
        FairyIntentType.INTERACTION_HANDLER: lambda: create_interaction(dungenon_player.inventory),
    }

    INTENT_LABELS = {
        FairyIntentType.MONSTER_GUIDE: "몬스터 공략",
        FairyIntentType.EVENT_GUIDE: "이벤트",
        FairyIntentType.DUNGEON_NAVIGATOR: "길안내",
        FairyIntentType.INTERACTION_HANDLER: "상호작용",
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


    pretty_dungenon_player =  dungenon_player.model_dump_json(indent=2)
    prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_SYSTEM).get_prompt(
        dungenon_player=pretty_dungenon_player,
        use_intents=[rt.value if hasattr(rt, "value") else rt for rt in intent_types],
        info=prompt_info,
        question=state["messages"][-1].content,
    )
    ai_answer = await helper_llm.ainvoke(prompt)
    print(prompt)
    print("*" * 100)
    print(f"\n{ai_answer}")
    return {
        "messages": [
            add_ai_message(content=ai_answer.content, intent_types=intent_types)
        ]
    }


from langgraph.graph import START, END, StateGraph

dungeon_graph_builder = StateGraph(FairyState)

dungeon_graph_builder.add_node("analyze_intent", analyze_intent)
dungeon_graph_builder.add_node("fairy_action", fairy_action)
dungeon_graph_builder.add_node("multi_small_talk", multi_small_talk_node)

dungeon_graph_builder.add_edge(START, "analyze_intent")

dungeon_graph_builder.add_conditional_edges(
    "analyze_intent",
    check_condition,
    {
        "retry": "analyze_intent",
        "multi_small_talk": "multi_small_talk",
        "continue": "fairy_action",
    },
)
dungeon_graph_builder.add_edge("fairy_action", END)
