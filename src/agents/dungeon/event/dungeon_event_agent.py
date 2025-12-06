from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from agents.dungeon.dungeon_state import DungeonEventParser
import random

llm = init_chat_model(model=LLM.GPT5_1, temperature=0.5)

from prompts.promptmanager import PromptManager
from prompts.prompt_type.dungeon.DungeonPromptType import DungeonPromptType
from agents.dungeon.dungeon_state import DungeonEventState
from db.RDBRepository import RDBRepository
from langchain_core.messages import HumanMessage


def heroine_memories_node(state: DungeonEventState) -> DungeonEventState:
    """
    히로인의 기억 데이터 로드
    heroine_scenarios.py에서 heroine_id와 memory_progress에 맞는 기억을 필터링
    """
    from agents.dungeon.event.heroine_scenarios import HEROINE_SCENARIOS

    heroine_id = state["heroine_data"]["heroine_id"]
    memory_progress = state["heroine_data"]["memory_progress"]

    # 타입 통일 (문자열 → 정수)
    heroine_id = int(heroine_id) if isinstance(heroine_id, str) else heroine_id

    # 해당 히로인의 해금된 기억들을 필터링 (memory_progress 이하)
    heroine_memories = [
        scenario
        for scenario in HEROINE_SCENARIOS
        if scenario["heroine_id"] == heroine_id
        and scenario["memory_progress"] <= memory_progress
    ]

    print(f"[heroine_memories_node] 히로인 ID: {heroine_id}")
    print(f"[heroine_memories_node] 기억 진척도: {memory_progress}")
    print(f"[heroine_memories_node] 해금된 기억 개수: {len(heroine_memories)}")

    return {"heroine_memories": heroine_memories}


def selected_main_event_node(state: DungeonEventState) -> DungeonEventState:
    """
    메인 이벤트 선택 로직
    1. main_event_scenarios.py에서 이벤트 목록 로드
    2. used_events 중복 제거
    3. 랜덤으로 최종 선택

    Note: is_personal=True인 개별 이벤트는 모든 플레이어가 같이 경험하지만,
          각 플레이어의 히로인 기억에 따라 다른 내러티브가 생성됨
    """
    from agents.dungeon.event.main_event_scenarios import MAIN_EVENT_SCENARIOS

    next_floor = state.get("next_floor", 1)
    used_events = state.get("used_events", [])

    # 이미 사용한 event_code 추출
    used_event_codes = [
        evt.get("event_code") for evt in used_events if "event_code" in evt
    ]

    # 사용 가능한 이벤트 필터링 (중복 제외)
    available_events = []
    for event in MAIN_EVENT_SCENARIOS:
        # 이미 사용한 이벤트 제외
        if event["event_code"] in used_event_codes:
            continue

        available_events.append(event)

    # 사용 가능한 이벤트가 없으면 모든 이벤트 풀에서 선택 (중복 허용)
    if not available_events:
        available_events = MAIN_EVENT_SCENARIOS

    # 랜덤 선택
    selected_event = random.choice(available_events)

    # 시나리오 텍스트 치환 (히로인 이름 등)
    scenario_text = selected_event['scenario_text']
    heroine_name = state["heroine_data"].get("name", "그녀")
    if "{heroine_name}" in scenario_text:
        scenario_text = scenario_text.format(heroine_name=heroine_name)

    # 선택된 이벤트를 구조화된 dict로 반환
    event_data = {
        "title": selected_event['title'],
        "event_code": selected_event['event_code'],
        "is_personal": selected_event['is_personal'],
        "scenario_text": scenario_text
    }

    print(f"[selected_main_event_node] 선택된 이벤트: {selected_event['title']}")
    print(
        f"[selected_main_event_node] 개별 이벤트 여부: {selected_event['is_personal']}"
    )

    return {"selected_main_event": event_data}


def create_sub_event_node(state: DungeonEventState) -> DungeonEventState:
    """
    서브 이벤트 생성 로직
    - 개별 이벤트(is_personal=True)의 경우: 히로인 기억에 맞춤화된 내러티브 생성
    - 공통 이벤트(is_personal=False)의 경우: 일반적인 내러티브 생성

    Note: 개별 이벤트는 보상/패널티는 동일하지만, 각 플레이어에게 다른 텍스트가 표시됨
    """
    prompts = PromptManager(DungeonPromptType.DUNGEON_SUB_EVENT).get_prompt(
        heroine_data=state["heroine_data"],
        heroine_memories=state["heroine_memories"],
        selected_main_event=state["selected_main_event"],
        event_room=state["event_room"],
        next_floor=state["next_floor"],
    )

    parser_llm = llm.with_structured_output(DungeonEventParser)
    response = parser_llm.invoke(prompts)

    # 서브 이벤트를 구조화된 dict로 변환
    sub_event_data = {
        "narrative": response.sub_event_narrative,
        "choices": [
            {
                "action": choice.action,
                "reward_id": choice.reward_id,
                "penalty_id": choice.penalty_id
            }
            for choice in response.event_choices
        ],
        "expected_outcome": response.expected_outcome
    }

    print(f"[create_sub_event_node] 서브 이벤트 생성 완료")
    print(response)

    # 하위 호환성을 위한 문자열 버전도 생성
    sub_event_text = f"""
=== 서브 이벤트 내러티브 ===
{response.sub_event_narrative}

=== 선택지 ===
{chr(10).join([f"{i+1}. action='{choice.action}' reward_id='{choice.reward_id}' penalty_id='{choice.penalty_id}'" for i, choice in enumerate(response.event_choices)])}

=== 예상 결과 ===
{response.expected_outcome}
"""

    return {
        "messages": [HumanMessage(sub_event_text)],
        "sub_event": sub_event_data,
        "final_answer": sub_event_data,
    }


from langgraph.graph import START, END, StateGraph


graph_builder = StateGraph(DungeonEventState)
graph_builder.add_node("heroine_memories_node", heroine_memories_node)
graph_builder.add_node("selected_main_event_node", selected_main_event_node)
graph_builder.add_node("create_sub_event_node", create_sub_event_node)

graph_builder.add_edge(START, "heroine_memories_node")
graph_builder.add_edge("heroine_memories_node", "selected_main_event_node")

graph_builder.add_edge("selected_main_event_node", "create_sub_event_node")
graph_builder.add_edge("create_sub_event_node", END)
graph_builder
