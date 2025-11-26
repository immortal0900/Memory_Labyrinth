from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from state import DungeonState
from nodes import monster_balancing_node
from models import MonsterMetadata, StatData
# from core.common import get_project_root, write_json, get_today_str
# from db.DBRepository import DBRepository
# from db.config import DBCollectionName


def build_dungeon_graph():
    workflow = StateGraph(DungeonState)
    
    # 노드 추가
    workflow.add_node("monster_balancing", monster_balancing_node)

    # 엣지 추가
    workflow.set_entry_point("monster_balancing")
    workflow.add_edge("monster_balancing", END)

    # 그래프 컴파일
    app = workflow.compile()
    return app

def create_mock_monster_db() -> Dict[int, MonsterMetadata]:
    """
    테스트용 Mock 몬스터 DB 생성
    
    Returns:
        monsterId -> MonsterMetadata 매핑 딕셔너리
    """
    return {
        0: MonsterMetadata(
            monster_id=0,
            name="Skeleton",
            hp=300,
            speed=350,
            attack=10,
            attack_speed=1.0,
            attack_range=100.0,
            weaknesses=None,
            strengths=None
        ),
        1: MonsterMetadata(
            monster_id=1,
            name="Slime",
            hp=250,
            speed=200,
            attack=10,
            attack_speed=1.0,
            attack_range=100.0,
            weaknesses=None,
            strengths=None
        ),
        2: MonsterMetadata(
            monster_id=2,
            name="Goblin",
            hp=150,
            speed=250,
            attack=15,
            attack_speed=1.2,
            attack_range=0.0,  # 근거리
            weaknesses=[1],  # 예시: 약점 속성 ID 1
            strengths=None
        ),
        3: MonsterMetadata(
            monster_id=3,
            name="Archer",
            hp=120,
            speed=300,
            attack=20,
            attack_speed=0.8,
            attack_range=500.0,  # 원거리
            weaknesses=None,
            strengths=[2]  # 예시: 강점 속성 ID 2
        ),
    }


def create_mock_data(use_db: bool = True) -> Dict[str, Any]:
    """
    테스트용 Mock 데이터 생성
    엑셀 데이터 스프레드시트 구조를 기반으로 작성
    
    Returns:
        초기 State 딕셔너리
    """
    # 플레이어 및 히로인 데이터
    player_ids = [10001]
    heroine_ids = [1]
    
    # 히로인 스탯 생성 (엑셀 statData 구조)
    hero_stats = [
        StatData(
            hp=500,
            move_speed=1.5,
            cooldown_reduction=1.2,
            strength=50,
            dexterity=30,
            crit_chance=25.0,
            skill_damage_multiplier=1.5,
            auto_attack_multiplier=1.2,
            attack_speed=1.3
        )
    ]
    
    # 몬스터 DB 로드 (DB 우선, 실패 시 Mock 데이터 사용)
    monster_db = None
    if use_db:
        monster_db = load_monster_db_from_db()
    
    if monster_db is None:
        print("Mock 몬스터 데이터 사용")
        monster_db = create_mock_monster_db()
    else:
        print(f"✓ DB에서 {len(monster_db)}종의 몬스터 데이터 로드 완료")
    
    # 초기 State (통신 프로토콜 구조)
    initial_state: DungeonState = {
        "player_ids": player_ids,
        "heroine_ids": heroine_ids,
        "hero_stats": hero_stats,
        "monster_db": monster_db,
        "floor": 3,
        "room_count": 5,
        "rooms": [],
        "difficulty_context": {},
        "event_rooms": None,
        "event_data": None,
        "dungeon_data": None
    }
    
    return initial_state


def main(use_db: bool = True):
    """
    메인 실행 함수
    
    Args:
        use_db: DB에서 몬스터 데이터를 로드할지 여부 (기본값: True)
    """
    print("=== 던전 밸런싱 AI Agent 테스트 ===\n")
    
    # 그래프 빌드
    app = build_dungeon_graph()
    print("✓ LangGraph 빌드 완료\n")
    
    # Mock 데이터 생성
    initial_state = create_mock_data(use_db=use_db)
    print("✓ Mock 데이터 생성 완료")
    print(f"  - 플레이어 ID: {initial_state['player_ids']}")
    print(f"  - 히로인 ID: {initial_state['heroine_ids']}")
    print(f"  - 히로인 수: {len(initial_state['hero_stats'])}")
    print(f"  - 히로인 HP: {initial_state['hero_stats'][0].hp}, 전투력: {initial_state['hero_stats'][0].combat_score:.2f}")
    print(f"  - 층: {initial_state['floor']}층")
    print(f"  - 방 개수: {initial_state['room_count']}개")
    print(f"  - 몬스터 종류: {len(initial_state['monster_db'])}종\n")
    
    # 그래프 실행
    print("=== 그래프 실행 시작 ===\n")
    result = app.invoke(initial_state)
    
    # 결과 출력
    print("\n=== 실행 결과 ===\n")
    
    # Monster Agent 결과
    print(" Monster Agent 결과:")
    print(f"  - 총 예산 할당: {result['difficulty_context']['total_budget_allocated']:.0f}")
    print(f"  - 총 예산 사용: {result['difficulty_context']['total_budget_used']:.0f}")
    print(f"  - 예산 사용률: {result['difficulty_context']['budget_utilization']:.2%}\n")
    
    # 각 방별 상세 정보
    print(" 방별 상세 정보:")
    for room in result['rooms']:
        room_type_names = {0: "빈방", 1: "전투", 2: "이벤트", 3: "보물"}
        print(f"\n  방 {room.room_id} ({room_type_names[room.room_type]}, 크기: {room.size}):")
        if room.monsters:
            print(f"    몬스터 수: {len(room.monsters)}")
            for monster in room.monsters:
                monster_info = result['monster_db'][monster.monster_id]
                print(f"      - {monster_info.name} (위치: ({monster.pos_x:.2f}, {monster.pos_y:.2f}), 비용: {monster_info.cost_point:.0f})")
        if room.event_type is not None:
            event_names = {0: "빈 이벤트", 1: "회복의 샘", 2: "상인", 3: "신비한 사건"}
            print(f"    이벤트 타입: {event_names[room.event_type]}")
    
    # Event Agent 상세 결과
    if result.get('event_data'):
        print("\n\n Event Agent 상세 결과:")
        for event_data in result['event_data']:
            print(f"\n  방 {event_data['room_id']} 이벤트:")
            print(f"    이벤트 소스: {event_data['event_source_type']}")
            print(f"    메인 시나리오: {event_data['scenario']['main_scenario']}")
            print(f"    히로인 반응: {event_data['scenario']['heroine_reaction']}")
            print(f"    상호작용 수: {len(event_data['interactions'])}")
            for interaction in event_data['interactions']:
                print(f"      - {interaction['text']} (반복 가능: {interaction['is_repeatable']})")
    
    # 최종 던전 데이터
    if result.get('dungeon_data'):
        print("\n\n🎮 최종 던전 데이터:")
        dungeon_data = result['dungeon_data']
        print(f"  - 플레이어 ID: {dungeon_data.player_ids}")
        print(f"  - 히로인 ID: {dungeon_data.heroine_ids}")
        print(f"  - 방 개수: {len(dungeon_data.rooms)}")
        print(f"  - 보상 테이블 개수: {len(dungeon_data.rewards)}")
    
    print("\n=== 테스트 완료 ===")
    
    # 결과를 JSON 파일로 저장 (선택적)
    try:
        output_dir = get_project_root() / "src" / "lab" / "dungeon" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"dungeon_result_{get_today_str('%Y%m%d_%H%M%S')}.json"
        
        # 결과를 딕셔너리로 변환
        result_dict = {
            "player_ids": result.get("player_ids", []),
            "heroine_ids": result.get("heroine_ids", []),
            "floor": result.get("floor", 0),
            "room_count": result.get("room_count", 0),
            "difficulty_context": result.get("difficulty_context", {}),
            "rooms": [room.to_dict() for room in result.get("rooms", [])],
            "dungeon_data": result.get("dungeon_data").to_dict() if result.get("dungeon_data") else None
        }
        
        write_json(output_file, result_dict)
        print(f"\n결과 저장: {output_file}")
    except Exception as e:
        print(f"\n결과 저장 실패: {e}")


if __name__ == "__main__":
    import sys
    
    # 명령줄 인자로 DB 사용 여부 제어
    use_db = True
    if len(sys.argv) > 1 and sys.argv[1] == "--no-db":
        use_db = False
    
    main(use_db=use_db)

