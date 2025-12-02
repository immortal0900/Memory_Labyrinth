"""
Super Dungeon Agent
Event Agent와 Monster Agent를 병렬로 실행하고 결과를 병합하는 최상위 Agent
"""

from typing import Dict, Any
from datetime import datetime
from langgraph.graph import START, END, StateGraph
from agents.dungeon.dungeon_state import SuperDungeonState


# ===== Node 1: Event Processing =====
def event_node(state: SuperDungeonState) -> Dict[str, Any]:
    """
    Event Agent를 실행하는 노드
    - 히로인 정보와 던전 정보를 기반으로 이벤트 생성
    """
    print("\n[Event Node] 이벤트 생성 시작...")

    # 실제 Event Agent 호출
    from agents.dungeon.event.dungeon_event_agent import (
        graph_builder as event_graph_builder,
    )

    event_graph = event_graph_builder.compile()

    event_state = {
        "heroine_data": state.get("heroine_data"),
        "heroine_memories": state.get("heroine_memories"),
        "event_room": state.get("heroine_data", {}).get("event_room", 3),
        "next_floor": state.get("dungeon_base_data", {}).get("floor_count", 1),
        "used_events": state.get("used_events", []),
    }

    event_result = event_graph.invoke(event_state)

    print(f"[Event Node] 완료:")
    print(f"  - Main Event: {event_result.get('selected_main_event', 'N/A')[:80]}...")
    print(f"  - Sub Event: {event_result.get('sub_event', 'N/A')[:80]}...")

    return {"event_result": event_result}


# ===== Node 2: Monster Balancing =====
def monster_node(state: SuperDungeonState) -> Dict[str, Any]:
    """
    Monster Agent를 실행하는 노드
    - 던전 맵에 몬스터를 배치하고 밸런싱
    """
    print("\n[Monster Node] 몬스터 밸런싱 시작...")

    # 실제 Monster Agent 호출
    from agents.dungeon.monster.dungeon_monster_agent import monster_graph

    # Monster Agent 입력 state 구성
    monster_state = {
        "heroine_stat": state.get("heroine_stat"),
        "monster_db": state.get("monster_db"),
        "dungeon_data": state.get("dungeon_base_data"),
        "dungeon_player_data": state.get("dungeon_player_data"),
        "floor": state.get("dungeon_base_data", {}).get("floor_count", 1),
    }

    # Monster Graph 실행
    monster_result = monster_graph.invoke(monster_state)

    filled_dungeon_data = monster_result.get("filled_dungeon_data", {})
    
    print(f"[Monster Node] 완료:")
    print(f"  - 전투력: {monster_result.get('combat_score', 0):.2f}")
    print(
        f"  - 난이도 배율: {monster_result['difficulty_log'].get('ai_multiplier', 1.0):.2f}x"
    )
    print(
        f"  - 배치된 몬스터: {monster_result['difficulty_log'].get('normal_monster_count', 0)}마리"
    )
    print(
        f"  - 보스방: {'있음' if monster_result['difficulty_log'].get('has_boss_room') else '없음'}"
    )
    
    # 디버그: 반환 데이터 확인
    print(f"[Monster Node DEBUG] filled_dungeon_data type: {type(filled_dungeon_data)}")
    print(f"[Monster Node DEBUG] filled_dungeon_data keys: {list(filled_dungeon_data.keys()) if isinstance(filled_dungeon_data, dict) else 'Not a dict'}")
    print(f"[Monster Node DEBUG] rooms count: {len(filled_dungeon_data.get('rooms', []))}")
    
    # 각 방의 몬스터 수 확인
    total_monsters_in_rooms = 0
    for idx, room in enumerate(filled_dungeon_data.get("rooms", [])):
        monster_count = len(room.get("monsters", []))
        total_monsters_in_rooms += monster_count
        if monster_count > 0:
            print(f"[Monster Node DEBUG] Room {idx} ({room.get('room_type')}): {monster_count} monsters")
    print(f"[Monster Node DEBUG] Total monsters in all rooms: {total_monsters_in_rooms}")

    return {
        "filled_dungeon_data": filled_dungeon_data,
        "difficulty_log": monster_result.get("difficulty_log"),
    }


# ===== Node 3: Merge Results =====
def merge_results_node(state: SuperDungeonState) -> Dict[str, Any]:
    """
    Event와 Monster 결과를 알고리즘적으로 병합
    LLM 사용 없이 순수 로직으로 구현
    """
    print("\n[Merge Node] 결과 병합 시작...")

    # 1. 각 Agent 결과 가져오기
    filled_dungeon = state.get("filled_dungeon_data", {})
    event_result = state.get("event_result", {})
    difficulty_log = state.get("difficulty_log", {})

    # 디버그: state 키 확인
    print(f"[Merge Node DEBUG] State keys: {list(state.keys())}")
    print(
        f"[Merge Node DEBUG] filled_dungeon_data exists: {'filled_dungeon_data' in state}"
    )
    print(f"[Merge Node DEBUG] filled_dungeon type: {type(filled_dungeon)}")
    print(
        f"[Merge Node DEBUG] filled_dungeon keys: {list(filled_dungeon.keys()) if isinstance(filled_dungeon, dict) else 'Not a dict'}"
    )
    print(
        f"[Merge Node DEBUG] filled_dungeon rooms count: {len(filled_dungeon.get('rooms', []))}"
    )

    # 각 방의 몬스터 수 확인
    if filled_dungeon.get("rooms"):
        for idx, room in enumerate(filled_dungeon.get("rooms", [])):
            print(
                f"[Merge Node DEBUG] Room {idx} ({room.get('room_type')}): {len(room.get('monsters', []))} monsters"
            )

    # 2. 몬스터 통계 계산
    total_monsters = 0
    boss_count = 0
    normal_monster_count = 0

    for room in filled_dungeon.get("rooms", []):
        monsters = room.get("monsters", [])
        total_monsters += len(monsters)
        for monster in monsters:
            if monster.get("monster_type") == 2:
                boss_count += 1
            else:
                normal_monster_count += 1

    # 3. 최종 JSON 구조 생성
    final_json = {
        # 몬스터가 배치된 완전한 던전 데이터
        "dungeon_data": filled_dungeon,
        # Event 정보
        "events": {
            "main_event": event_result.get("selected_main_event", ""),
            "sub_event": event_result.get("sub_event", ""),
            "event_room_index": event_result.get("event_room", -1),
            "final_answer": event_result.get("final_answer", ""),
        },
        # Monster 통계
        "monster_stats": {
            "total_count": total_monsters,
            "boss_count": boss_count,
            "normal_count": normal_monster_count,
            "actual_threat": difficulty_log.get("actual_threat", 0),
            "target_threat": difficulty_log.get("target_threat", 0),
            "boss_threat": difficulty_log.get("boss_threat", 0),
            "achievement_rate": (
                difficulty_log.get("actual_threat", 0)
                / difficulty_log.get("target_threat", 1)
                * 100
                if difficulty_log.get("target_threat", 0) > 0
                else 0
            ),
        },
        # 난이도 정보
        "difficulty_info": {
            "combat_score": difficulty_log.get("combat_score", 0),
            "is_party": difficulty_log.get("is_party", False),
            "player_count": difficulty_log.get("player_count", 1),
            "ai_multiplier": difficulty_log.get("ai_multiplier", 1.0),
            "ai_reasoning": difficulty_log.get("ai_reasoning", ""),
            "model_used": difficulty_log.get("model_used", "unknown"),
            "preferred_tags": difficulty_log.get("preferred_tags", []),
            "has_boss_room": difficulty_log.get("has_boss_room", False),
        },
        # 메타 정보
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "dungeon_id": filled_dungeon.get("dungeon_id", "unknown"),
            "floor_count": filled_dungeon.get("floor_count", 1),
            "total_rooms": len(filled_dungeon.get("rooms", [])),
        },
    }

    print(f"[Merge Node] 병합 완료:")
    print(f"  - Event: {final_json['events']['main_event'][:50]}...")
    print(
        f"  - 총 몬스터: {total_monsters}마리 (보스: {boss_count}, 일반: {normal_monster_count})"
    )
    print(f"  - AI 난이도 배율: x{final_json['difficulty_info']['ai_multiplier']:.2f}")
    print(f"  - 전투력: {final_json['difficulty_info']['combat_score']:.2f}")
    print(f"  - 위협도 달성률: {final_json['monster_stats']['achievement_rate']:.1f}%")

    return {"final_dungeon_json": final_json}


# ===== Graph Construction =====
def create_super_dungeon_graph():
    """
    Super Dungeon Agent의 LangGraph 생성
    Event와 Monster를 병렬 실행하고 결과를 병합
    """
    graph_builder = StateGraph(SuperDungeonState)

    # 노드 추가
    graph_builder.add_node("event_node", event_node)
    graph_builder.add_node("monster_node", monster_node)
    graph_builder.add_node("merge_results_node", merge_results_node)

    # Edge 연결 (병렬 실행)
    graph_builder.add_edge(START, "event_node")
    graph_builder.add_edge(START, "monster_node")

    # 두 노드가 완료되면 merge로 이동
    graph_builder.add_edge("event_node", "merge_results_node")
    graph_builder.add_edge("monster_node", "merge_results_node")

    # 최종 종료
    graph_builder.add_edge("merge_results_node", END)

    return graph_builder.compile()


# ===== Main Execution (for testing) =====
if __name__ == "__main__":
    print("=" * 70)
    print("Super Dungeon Agent - Test Execution")
    print("=" * 70)

    # Monster DB import
    from agents.dungeon.monster.monster_database import MONSTER_DATABASE

    # 테스트용 초기 State
    initial_state: SuperDungeonState = {
        "dungeon_base_data": {
            "dungeon_id": 1,
            "floor_count": 3,
            "rooms": [
                {"room_id": 1, "room_type": "start", "position": {"x": 0, "y": 0}},
                {"room_id": 2, "room_type": "monster", "position": {"x": 10, "y": 0}},
                {"room_id": 3, "room_type": "monster", "position": {"x": 20, "y": 0}},
                {"room_id": 4, "room_type": "treasure", "position": {"x": 30, "y": 0}},
                {"room_id": 5, "room_type": "monster", "position": {"x": 40, "y": 0}},
                {"room_id": 6, "room_type": "boss", "position": {"x": 50, "y": 0}},
            ],
        },
        "heroine_data": {
            "heroine_id": "hero_001",
            "name": "테스트 히로인",
            "event_room": 3,
            "memory_progress": 0,
        },
        "heroine_stat": {
            "hp": 500,
            "strength": 20,
            "dexterity": 15,
            "intelligence": 10,
            "defense": 10,
            "critChance": 15.0,
            "attackSpeed": 1.5,
            "moveSpeed": 400,
            "skillDamageMultiplier": 1.2,
        },
        "heroine_memories": [],
        "monster_db": MONSTER_DATABASE,
        "dungeon_player_data": {
            "affection": 50,
            "sanity": 80,
            "difficulty_level": "normal",
        },
        "used_events": [],
        "event_result": {},
        "filled_dungeon_data": {},
        "difficulty_log": {},
        "final_dungeon_json": {},
    }

    # Graph 생성 및 실행
    graph = create_super_dungeon_graph()
    result = graph.invoke(initial_state)

    print("\n" + "=" * 70)
    print("Final Result Summary:")
    print("=" * 70)

    import json

    final_json = result.get("final_dungeon_json", {})

    print("\n📊 Dungeon Info:")
    print(f"  - ID: {final_json.get('meta', {}).get('dungeon_id')}")
    print(f"  - Floors: {final_json.get('meta', {}).get('floor_count')}")
    print(f"  - Rooms: {final_json.get('meta', {}).get('total_rooms')}")

    print("\n👹 Monster Stats:")
    monster_stats = final_json.get("monster_stats", {})
    print(f"  - Total: {monster_stats.get('total_count')}마리")
    print(f"  - Boss: {monster_stats.get('boss_count')}마리")
    print(f"  - Normal: {monster_stats.get('normal_count')}마리")
    print(f"  - Threat Achievement: {monster_stats.get('achievement_rate', 0):.1f}%")

    print("\n🎯 Difficulty Info:")
    difficulty_info = final_json.get("difficulty_info", {})
    print(f"  - Combat Score: {difficulty_info.get('combat_score', 0):.2f}")
    print(f"  - AI Multiplier: x{difficulty_info.get('ai_multiplier', 1.0):.2f}")
    print(f"  - Player Count: {difficulty_info.get('player_count', 1)}")
    print(f"  - Model: {difficulty_info.get('model_used', 'unknown')}")

    print("\n🎭 Events:")
    events = final_json.get("events", {})
    print(f"  - Main: {events.get('main_event', 'N/A')[:60]}...")
    print(f"  - Sub: {events.get('sub_event', 'N/A')[:60]}...")

    print("\n" + "=" * 70)
    print("✅ Test Complete")
    print("=" * 70)
