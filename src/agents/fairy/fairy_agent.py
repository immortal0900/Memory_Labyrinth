
from langchain_core.chat_history import InMemoryChatMessageHistory, BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from agents.fairy.fairy_state import FairyIntentOutput, FairyState, FairyIntentType
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command, interrupt
from agents.fairy.temp_string import reverse_questions
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
import random
from agents.fairy.util import add_ai_message, add_human_message, str_to_bool
import asyncio
from core.game_dto.z_muck_factory import MockFactory

helper_llm = init_chat_model(model=LLM.GPT4_1_MINI,temperature=0)
small_talk_llm = init_chat_model(model=LLM.GPT4_1_MINI,temperature=0.4)


async def monster_rag():
    return "asd"

async def get_event_info():
    return "asdasd"

async def dungeon_navigator():
    return "dungeon_navi"

async def create_interaction():
    return "뿌뿌뿌"

async def clarify_intent(query):
    intent_prompt = PromptManager(FairyPromptType.FAIRY_INTENT).get_prompt(question=query)
    parser_intent_llm = helper_llm.with_structured_output(FairyIntentOutput)
    intent_output: FairyIntentOutput = await parser_intent_llm.ainvoke(intent_prompt)
    return intent_output


async def check_memory_question(query:str):
    prompt = PromptManager(FairyPromptType.QUESTION_HISTORY_CHECK).get_prompt(question=query)
    reponse = await helper_llm.ainvoke(prompt)
    return str_to_bool(reponse.content)


async def analyze_intent(state: FairyState):
    last = state["messages"][-1]
    last_message = last.content

    clarify_intent_type, is_question_memory = await asyncio.gather(
        clarify_intent(last_message),
        check_memory_question(last_message)
    )

    if len(clarify_intent_type.intents) == 1 and clarify_intent_type.intents[0] == FairyIntentType.UNKNOWN_INTENT:
        clarification = reverse_questions[random.randint(0, 49)]
        user_resp = interrupt(clarification)
        return {
            "messages": [
                add_ai_message(content=clarification, intent_types=clarify_intent_type.intents),
                add_human_message(content=user_resp), # 유저 답변 추가
            ],
            "intent_types": clarify_intent_type.intents, # 여전히 Unknown 상태
        }

    return {"intent_types": clarify_intent_type.intents}

def check_condition(state: FairyState):
    intent_types = state.get("intent_types", [])
    if len(intent_types) == 1 and intent_types[0] == FairyIntentType.UNKNOWN_INTENT:
        return "retry"

    return "continue"


INTENT_HANDLERS = {
    FairyIntentType.MONSTER_GUIDE:       monster_rag,
    FairyIntentType.EVENT_GUIDE:         get_event_info,
    FairyIntentType.DUNGEON_NAVIGATOR:   dungeon_navigator,
    FairyIntentType.INTERACTION_HANDLER: create_interaction,
}

INTENT_LABELS = {
    FairyIntentType.MONSTER_GUIDE: "몬스터 공략",
    FairyIntentType.EVENT_GUIDE: "이벤트",
    FairyIntentType.DUNGEON_NAVIGATOR: "길안내",
    FairyIntentType.INTERACTION_HANDLER: "상호작용",
}

async def fairy_action(state: FairyState) -> Command:
    intent_types = state.get("intent_types")
    if intent_types is None:
        raise Exception("fairy_action 호출 전에 intent_type이 설정되지 않았습니다.")

    handlers = [INTENT_HANDLERS[i]() for i in intent_types if i in INTENT_HANDLERS]
    results = await asyncio.gather(*handlers)

    prompt_info = ""
    idx = 0
    for i,index in enumerate(intent_types):
        handler = INTENT_HANDLERS.get(index)
        if not handler:
            continue

        value = results[idx]
        label = INTENT_LABELS.get(index, "정보")
        if i == 0:
            prompt_info += f"    <{label}>\n{value}\n    </{label}>"
        else:
            prompt_info += f"\n    <{label}>\n{value}\n    </{label}>"
        idx+=1

    prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_SYSTEM).get_prompt(
        state_data = MockFactory.create_dungeon_player(1).model_dump_json(indent=2),
        use_intents = [rt.value if hasattr(rt, "value") else rt for rt in intent_types],
        info = prompt_info,
        question = state['messages'][-1].content
    )
    ai_answer = await helper_llm.ainvoke(prompt)
    print(prompt)
    print("*"*100)
    print(f"\n{ai_answer}")
    return {"messages": [add_ai_message(content = ai_answer.content, intent_types = intent_types)]}


from langgraph.graph import START, END, StateGraph
graph_builder = StateGraph(FairyState)

graph_builder.add_node("analyze_intent", analyze_intent)
graph_builder.add_node("fairy_action", fairy_action)

graph_builder.add_edge(START, "analyze_intent")

graph_builder.add_conditional_edges(
    "analyze_intent",      
    check_condition,         
    {
        "retry": "analyze_intent",  
        "continue": "fairy_action"  
    }
)
graph_builder.add_edge("fairy_action", END)
