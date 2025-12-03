from agents.fairy.fairy_state import (
    FairyInteractionState,
    FairyInterationIntentType,
    FairyInterationIntentOutput,
    FairyItemUseOutput,
)
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from typing import List
from core.common import get_inventory_items
from agents.fairy.util import (
    get_groq_llm_lc
)

llm = get_groq_llm_lc(max_token=40)


def _clarify_intent(query):
    interation_intent_prompt = PromptManager(FairyPromptType.FAIRY_INTERACTION_INTENT).get_prompt(question=query)
    parser_llm = llm.with_structured_output(FairyInterationIntentOutput)
    intent_output: FairyInterationIntentOutput = parser_llm.invoke(interation_intent_prompt)
    return intent_output


def analyze_intent(state: FairyInteractionState):
    last = state["messages"][-1]
    last_message = last.content
    intent_output: FairyInterationIntentOutput = _clarify_intent(last_message)
    return {"intent_types": intent_output.intents}


# LLM Call을 한번이라도 줄이기 위해 의도 분석과 함께 병렬 호출 Node
def create_temp_use_item_id(state: FairyInteractionState):
    last = state["messages"][-1]
    last_message = last.content
    inventory = state["inventory"]
    my_items = get_inventory_items(inventory)
    item_use_prompt = PromptManager(FairyPromptType.FAIRY_ITEM_USE).get_prompt(
        inventory_items=my_items, question=last_message
    )
    parser_llm = llm.with_structured_output(FairyItemUseOutput)
    output: FairyItemUseOutput = parser_llm.invoke(item_use_prompt)
    return {"temp_use_item_id": output.item_id}


def create_interation(state: FairyInteractionState):
    intent_types: List[FairyInterationIntentType] = state["intent_types"]

    item_id = None
    if FairyInterationIntentType.INVENTORY_ITEM_USE in intent_types:
        item_id = state["temp_use_item_id"]

    is_room_light = None
    if FairyInterationIntentType.LIGHT_ON_ROOM in intent_types:
        is_room_light = True
    if FairyInterationIntentType.LIGHT_OFF_ROOM in intent_types:
        is_room_light = False

    isCheckNextRoom = FairyInterationIntentType.MOVE_NEXT_ROOM in intent_types

    return {
        "useItemId": item_id,
        "roomLight": is_room_light,
        "isCheckNextRoom": isCheckNextRoom,
    }


graph_builder = StateGraph(FairyInteractionState)
graph_builder.add_node("analyze_intent", analyze_intent)
graph_builder.add_node("create_temp_use_item_id", create_temp_use_item_id)
graph_builder.add_node("create_interation", create_interation)

graph_builder.add_edge(START, "analyze_intent")
graph_builder.add_edge(START, "create_temp_use_item_id")

graph_builder.add_edge("analyze_intent", "create_interation")
graph_builder.add_edge("create_temp_use_item_id", "create_interation")

graph_builder.add_edge("create_interation", END)
graph = graph_builder.compile()
