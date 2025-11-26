from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from agents.fairy.fairy_state import FairyIntentOutput, FairyState, FairyIntentType
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command, interrupt
from agents.fairy.temp_string import reverse_questions
from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
import random

llm = init_chat_model(model=LLM.GPT4_1_MINI,temperature=0.2)
intent_llm = init_chat_model(model=LLM.GPT4_1_MINI,temperature=0)



def memory_question(state:FairyState):
    last = state["messages"][-1]
    last_message = last.content

    """

    """


def analyze_intent(state: FairyState):
    last = state["messages"][-1]
    last_message = last.content

    parser_intent_llm = intent_llm.with_structured_output(FairyIntentOutput)
    intent_output: FairyIntentOutput = parser_intent_llm.invoke(last_message)

    if len(intent_output.intents) == 1 and intent_output.intents[0] == FairyIntentType.UNKNOWN_INTENT:
        clarification = reverse_questions[random.randint(0, 49)]
        user_resp = interrupt(clarification)
        return {
            "messages": [
                AIMessage(content=clarification),
                HumanMessage(content=user_resp), # 유저 답변 추가
            ],
            "intent_types": intent_output.intents, # 여전히 Unknown 상태
        }

    return {"intent_types": intent_output.intents}

def check_clarity(state: FairyState):
    intent_types = state.get("intent_types", [])

    # Unknown이면 다시 analyze_intent로 돌아가서 재분석(Loop)
    if len(intent_types) == 1 and intent_types[0] == FairyIntentType.UNKNOWN_INTENT:
        return "retry"

    return "continue"


def monster_rag():
    return "\nasd"


def get_event_info():
    return "\nasdasd"

def dungeon_navigator():
    return "\ndungeon_navi"


def create_interaction():
    return "\n뿌뿌뿌"


def fairy_action(state: FairyState) -> Command:
    intent_types = state.get("intent_types")
    if intent_types is None:
        raise Exception("fairy_action 호출 전에 intent_type이 설정되지 않았습니다.")

    prompt_info = ""
    for intent in intent_types:
        if intent == FairyIntentType.MONSTER_GUIDE:
            prompt_info = f"""\n몬스터 공략:{monster_rag()}"""

        elif intent == FairyIntentType.EVENT_GUIDE:
            prompt_info = f"""\n이벤트:{get_event_info()}"""

        elif intent == FairyIntentType.DUNGEON_NAVIGATOR:
            prompt_info = f"""\n길안내:{dungeon_navigator()}"""

        elif intent == FairyIntentType.INTERACTION_HANDLER:
            action_detail = create_interaction()

        else:
            info = "SMALLTALK"

    prompt = PromptManager(FairyPromptType.FAIRY_DUNGEON_SYSTEM).get_prompt(
        heroine_info = "테스트",
        use_intents = [rt.value if hasattr(rt, "value") else rt for rt in intent_types],
        info = prompt_info,
        question = state['messages'][-1].content
    )
    ai_answer = intent_llm.invoke(prompt)
    print(prompt)
    print("*"*100)
    print(f"\n{ai_answer}")
    return {"messages": [ai_answer]}


from langgraph.graph import START, END, StateGraph
graph_builder = StateGraph(FairyState)

graph_builder.add_node("analyze_intent", analyze_intent)
graph_builder.add_node("fairy_action", fairy_action)

graph_builder.add_edge(START, "analyze_intent")

graph_builder.add_conditional_edges(
    "analyze_intent",      
    check_clarity,         
    {
        "retry": "analyze_intent",  
        "continue": "fairy_action"  
    }
)
graph_builder.add_edge("fairy_action", END)
