from state import DungeonState
from monster_agent_with_llm import MonsterCompositionAgent
from enums.LLM import LLM
# from .event_agent import EventPlanningAgent


def monster_balancing_node(state: DungeonState) -> DungeonState:
    print("\n[System] 몬스터 밸런싱 노드 시작...")
    # hero_stats = state["hero_stats"]
    # monster_db = state["monster_db"]
    # floor = state["floor"]
    # room_count = state["room_count"]
    
    # Monster Agent 생성 및 실행

    selected_model = LLM.GPT4_1_MINI

    agent = MonsterCompositionAgent(state["hero_stats"], state["monster_db"], model_name = selected_model)
    filled_json, log = agent.process_dungeon(state["dungeon_data"])

    print(f"[System] ✅ 밸런싱 완료 (Model: {log.get('model_used', 'Unknown')})")
    print(f"   - AI 분석: {log.get('ai_reasoning', 'N/A')}")
    print(f"   - 전략 배율: x{log.get('ai_multiplier', 1.0)}")
    print(f"   - 타겟 점수: {log.get('target_score', 0):.1f}")
    
    return {
        "dungeon_data": filled_json,
        "difficulty_log": log
    }


# def event_planning_node(state: DungeonState) -> Dict[str, Any]:
#     """
#     Event Agent를 호출하여 이벤트 계획 생성
    
#     통신 프로토콜:
#     - 입력: hero_stats, rooms, difficulty_context (Monster Agent 출력)
#     - 출력: event_rooms
    
#     Args:
#         state: 현재 던전 상태 (rooms, difficulty_context 포함)
    
#     Returns:
#         업데이트할 State 딕셔너리
#     """
#     hero_stats = state["hero_stats"]
#     heroine_ids = state["heroine_ids"]
#     rooms: List[RoomData] = state.get("rooms", [])
#     difficulty_context: DifficultyContext = state.get("difficulty_context", {})
    
#     # Event Agent 생성 및 실행
#     agent = EventPlanningAgent(hero_stats, heroine_ids)
#     event_rooms, event_data = agent.update_rooms_with_events(rooms, difficulty_context)
    
#     return {
#         "event_rooms": event_rooms,
#         "event_data": event_data
#     }


# def item_planning_node(state: DungeonState) -> Dict[str, Any]:
#     """
#     Item Agent를 호출하여 아이템 계획 생성 및 최종 던전 데이터 생성
    
#     통신 프로토콜:
#     - 입력: player_ids, heroine_ids, event_rooms, difficulty_context
#     - 출력: dungeon_data (보상 포함)
    
#     Args:
#         state: 현재 던전 상태
    
#     Returns:
#         업데이트할 State 딕셔너리
#     """
#     player_ids = state["player_ids"]
#     heroine_ids = state["heroine_ids"]
#     event_rooms = state.get("event_rooms", state.get("rooms", []))
    
#     # TODO: Item Agent 구현 - 보상 테이블 생성
#     # 현재는 빈 보상 테이블로 생성
#     rewards: List[RewardTable] = []
    
#     # 최종 던전 데이터 생성
#     dungeon_data = DungeonData(
#         player_ids=player_ids,
#         heroine_ids=heroine_ids,
#         rooms=event_rooms,
#         rewards=rewards
#     )
    
#     return {
#         "dungeon_data": dungeon_data
#     }

