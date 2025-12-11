from agents.fairy.util import measure_latency
import time
from agents.fairy.fairy_state import (
    FairyInteractionState,
    FairyInterationIntentType,
    FairyInterationIntentOutput,
)
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
from enums.LLM import LLM
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from typing import List
from core.common import get_inventory_items
from agents.fairy.util import get_groq_llm_lc
from agents.fairy.fairy_state import FairyItemUseOutput
from agents.fairy.interaction.fairy_interaction_model_logics import ItemEmbeddingLogic, IsItemUseEmbeddingLogic, FairyInteractionIntentModel

item_embedding_logic = ItemEmbeddingLogic()
is_item_use_embedding_logic = IsItemUseEmbeddingLogic()
fairy_interaction_intent_model = FairyInteractionIntentModel()

llm = get_groq_llm_lc(max_token=2)
def _clarify_intent(query):
    # interation_intent_prompt = PromptManager(
    #     FairyPromptType.FAIRY_INTERACTION_INTENT
    # ).get_prompt(question=query)
    # parser_llm = llm.with_structured_output(FairyInterationIntentOutput)
    # intent_output: FairyInterationIntentOutput = parser_llm.invoke(
    #     interation_intent_prompt
    # )

    raw_labels, _ = fairy_interaction_intent_model.predict(query)
    enum_list = FairyInteractionIntentModel.parse_intents_to_enum(raw_labels)    
    intent_output = FairyInterationIntentOutput(intents=enum_list)
    return intent_output


def analyze_intent(state: FairyInteractionState):
    start = time.perf_counter()

    last = state["messages"][-1]
    last_message = last.content
    intent_output: FairyInterationIntentOutput = _clarify_intent(last_message)

    latency = time.perf_counter() - start
    return {
        "intent_types": intent_output.intents,
        "latency_analyze_intent": latency,
    }


# LLM Call을 한번이라도 줄이기 위해 의도 분석과 함께 병렬 호출 Node
def create_temp_use_item_id(state: FairyInteractionState):
    start = time.perf_counter()
    last = state["messages"][-1]
    last_message = last.content
    inventory = state["inventory"]
    my_items = get_inventory_items(inventory)
    item_use_prompt = PromptManager(FairyPromptType.FAIRY_ITEM_USE).get_prompt(
        inventory_items=my_items, question=last_message
    )

    # parser_llm = llm.with_structured_output(FairyItemUseOutput)
    output = FairyItemUseOutput(item_id=int(llm.invoke(item_use_prompt).content))  # for type hinting
    latency = time.perf_counter() - start
    return {"temp_use_item_id": output.item_id,
            "latency_create_temp_use_item_id": latency}
    # item_id = item_embedding_logic.pick_items(last_message, inventory, top_k=1)[0]
    # latency = time.perf_counter() - start
    # return {
    #     "temp_use_item_id": item_id,
    #     "latency_create_temp_use_item_id": latency,
    # }

def check_use_item(state:FairyInteractionState): 
    start = time.perf_counter()
    last = state["messages"][-1]
    last_message = last.content
    is_item_use = is_item_use_embedding_logic.is_item_use(last_message)
    latency = time.perf_counter() - start
    return {
        "is_item_use": is_item_use,
        "latency_check_use_item": latency,
    }


def create_interation(state: FairyInteractionState):
    intent_types: List[FairyInterationIntentType] = state["intent_types"]
    is_item_use = state["is_item_use"]

    item_id = None
    if FairyInterationIntentType.INVENTORY_ITEM_USE in intent_types and (is_item_use != False):
        item_id = state["temp_use_item_id"]

    room_light = 0
    if FairyInterationIntentType.LIGHT_ON_ROOM in intent_types:
        room_light = 1

    if FairyInterationIntentType.LIGHT_OFF_ROOM in intent_types:
        room_light = 2

    isCheckNextRoom = FairyInterationIntentType.MOVE_NEXT_ROOM in intent_types

    return {
        "useItemId": item_id,
        "roomLight": room_light,
        "isCheckNextRoom": isCheckNextRoom,
    }


graph_builder = StateGraph(FairyInteractionState)
graph_builder.add_node("analyze_intent", analyze_intent)
graph_builder.add_node("create_temp_use_item_id", create_temp_use_item_id)
graph_builder.add_node("create_interation", create_interation)
graph_builder.add_node("check_use_item", check_use_item)


graph_builder.add_edge(START, "analyze_intent")
graph_builder.add_edge(START, "create_temp_use_item_id")
graph_builder.add_edge(START, "check_use_item")

graph_builder.add_edge("analyze_intent", "create_interation")
graph_builder.add_edge("create_temp_use_item_id", "create_interation")
graph_builder.add_edge("check_use_item", "create_interation")

graph_builder.add_edge("create_interation", END)
graph = graph_builder.compile()
