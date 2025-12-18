from prompts.promptmanager import PromptManager
from prompts.prompt_type.fairy.FairyPromptType import FairyPromptType
from langchain_core.messages import SystemMessage
from agents.fairy.util import get_groq_llm_lc
from langgraph.graph import START, END, StateGraph
from agents.fairy.fairy_state import FairyGuildState

from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from agents.fairy.util import find_scenarios, str_to_bool, find_heroine_info, get_last_human_message
from agents.fairy.cache_data import GAME_SYSTEM_INFO
from db.RDBRepository import RDBRepository
import asyncio

rdb_repository = RDBRepository()

fast_llm = init_chat_model(
    model=LLM.GROK_4_FAST_NON_REASONING, model_provider="xai", max_tokens=120
)

reasoning_llm = init_chat_model(
    model=LLM.GROK_4_FAST_REASONING, model_provider="xai", max_tokens=120
)


def _rdb_fairy_messages_bg(user_args, ai_args):
    try:
        rdb_repository.insert_fairy_message(**user_args)
        rdb_repository.insert_fairy_message(**ai_args)
    except Exception as e:
        print("fairy_message insert failed:", e)


@tool
def get_scenarios(config: RunnableConfig):
    """히로인의 과거 데이터 입니다. 히로인 정보에 있는 히로인 일때만 데이터를 찾습니다."""
    heroine_id = config.get("configurable", {}).get("heroine_id")
    memory_progress = config.get("configurable", {}).get("memory_progress")
    return f"""[히로인의 과거]\n{find_scenarios(heroine_id, memory_progress)}"""


@tool
def get_game_system():
    """사용자가 현재 게임의 시스템적 기능, 구조, 진행 방식, 옵션, 조작 방식 등에 대해 질문할 때 선택됩니다."""
    return GAME_SYSTEM_INFO


@tool
def get_heroine_info(config: RunnableConfig):
    """(루파메스,레티아,로코 중 1명) 히로인의 현재 상태에 대한 데이터 입니다."""
    memory_progress = config.get("configurable", {}).get("memory_progress")
    affection = config.get("configurable", {}).get("affection")
    sanity = config.get("configurable", {}).get("sanity")
    heroine_data = {
        "affection": affection,
        "memoryProcess": memory_progress,
        "sanity": sanity,
    }
    return f"""
    ## 데이터 설명
    | 수치 | 범위 | 설명 |
    | ----- | ----- | ----- |
    | **affection** | 0\~100 | 호감도. 대화/행동으로 증감 |
    | **memoryProgress** | 0\~100 | 기억진척도. 해금 단계별로 갱신 |
    | **sanity** | 0\~100 | 정신 안정도. 0이면 우울 상태 |

    ## 현재 히로인의 데이터(JSON)
    {heroine_data}
    """


def reasoning_required(state: FairyGuildState):
    last_meesage = state["messages"][-1].content
    reasoning_required_prompt = PromptManager(
        FairyPromptType.FAIRY_REASONING_REQUIRED
    ).get_prompt(question=last_meesage)
    return {
        "reasoning_required": str_to_bool(
            get_groq_llm_lc(LLM.LLAMA_3_1_8B_INSTANT)
            .invoke(reasoning_required_prompt)
            .content
        )
    }


def call_llm(state: FairyGuildState, config: RunnableConfig):
    player_id = config.get("configurable", {}).get("thread_id")
    heroine_id = config.get("configurable", {}).get("heroine_id")
    heroine_info = find_heroine_info(heroine_id=heroine_id)

    messages = state["messages"]

    if state["reasoning_required"]:
        llm = reasoning_llm.bind_tools(
            [get_scenarios, get_game_system, get_heroine_info]
        )
    else:
        llm = fast_llm

    system_prompt = PromptManager(FairyPromptType.FAIRY_GUILD_SYSTEM).get_prompt(
        heroine_info=heroine_info
    )
    new_messages = [SystemMessage(content=system_prompt)] + messages
    ai_answer = llm.invoke(new_messages)
    has_tool_call = bool(
        getattr(ai_answer, "tool_calls", None)
        or ai_answer.response_metadata.get("tool_calls")
    )
    last_user_message = get_last_human_message(messages)
    if not has_tool_call and last_user_message:
        asyncio.create_task(
            asyncio.to_thread(
                _rdb_fairy_messages_bg,
                {
                    "sender_type": "USER",
                    "message": last_user_message,
                    "context_type": "GUILD",
                    "player_id": player_id,
                    "heroine_id": heroine_id,
                    "intent_type": None,
                },
                {
                    "sender_type": "AI",
                    "message": ai_answer.content,
                    "context_type": "GUILD",
                    "player_id": player_id,
                    "heroine_id": heroine_id,
                    "intent_type": None,
                },
            )
        )

    return {"messages": [ai_answer]}


graph_builder = StateGraph(FairyGuildState)

graph_builder.add_node("reasoning_required", reasoning_required)
graph_builder.add_node("call_llm", call_llm)
tool_node = ToolNode([get_scenarios, get_game_system, get_heroine_info])
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "reasoning_required")
graph_builder.add_edge("reasoning_required", "call_llm")
graph_builder.add_edge("call_llm", END)

graph_builder.add_conditional_edges("call_llm", tools_condition)
graph_builder.add_edge("tools", "call_llm")
graph_builder
