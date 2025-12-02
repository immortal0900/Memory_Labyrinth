from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from agents.dungeon.dungeon_state import DungeonMonsterState, MonsterStrategyParser
from agents.dungeon.monster.monster_database import MONSTER_DATABASE, MonsterData
from core.game_dto.StatData import StatData
from typing import Dict, List, Tuple, Any
import random

llm = init_chat_model(model=LLM.GPT5_MINI, temperature=0.7)

from prompts.promptmanager import PromptManager
from prompts.prompt_type.dungeon.DungeonPromptType import DungeonPromptType


def calculate_combat_score_node(state: DungeonMonsterState) -> DungeonMonsterState:
    """
    전투력을 계산하는 노드 (단일/멀티 플레이어 자동 감지)

    전투력 계산식:
    - HP 가중치: 0.3
    - 공격력(strength + dexterity) 가중치: 0.4
    - 공격속도 가중치: 0.15
    - 치명타 확률 가중치: 0.1
    - 스킬 데미지 배율 가중치: 0.05

    Returns:
        - 단일 플레이어: 해당 플레이어의 전투력
        - 멀티 플레이어: 파티 평균 전투력
    """
    heroine_stat = state["heroine_stat"]

    if not heroine_stat:
        print("[calculate_combat_score_node] 히로인 스탯 없음, 기본값 100.0 사용")
        return {"combat_score": 100.0}

    # 멀티 플레이어 감지 (List인 경우)
    is_party = isinstance(heroine_stat, list)

    if is_party:
        # TODO: 멀티 플레이어 - 파티 전투력 계산
        stats_list = heroine_stat
        if not stats_list:
            return {"combat_score": 100.0}

        # StatData 객체로 변환
        if isinstance(stats_list[0], dict):
            stats_objects = [StatData(**stat) for stat in stats_list]
        else:
            stats_objects = stats_list

        total_score = 0.0
        for stat in stats_objects:
            score = _calculate_single_combat_score(stat)
            total_score += score

        combat_score = total_score / len(stats_objects)
        print(f"[calculate_combat_score_node] 파티 평균 전투력: {combat_score:.2f}")
        print(f"[calculate_combat_score_node] 파티 인원: {len(stats_objects)}명")
    else:
        # 단일 플레이어
        if isinstance(heroine_stat, dict):
            stat = StatData(**heroine_stat)
        else:
            stat = heroine_stat

        combat_score = _calculate_single_combat_score(stat)
        print(f"[calculate_combat_score_node] 플레이어 전투력: {combat_score:.2f}")
        print(
            f"[calculate_combat_score_node] HP: {stat.hp}, STR: {stat.strength}, DEX: {stat.dexterity}"
        )

    return {"combat_score": combat_score}


def _calculate_single_combat_score(stat: StatData) -> float:
    """개별 히로인의 전투력을 계산하는 헬퍼 함수"""
    hp_score = stat.hp * 0.3
    attack_score = (stat.strength + stat.dexterity) * 0.4
    attack_speed_score = stat.attackSpeed * 15.0
    crit_score = stat.critChance * 0.1
    skill_damage_score = stat.skillDamageMultiplier * 5.0

    return (
        hp_score + attack_score + attack_speed_score + crit_score + skill_damage_score
    )


def llm_strategy_node(state: DungeonMonsterState) -> DungeonMonsterState:
    """
    LLM에게 히로인 정보를 전달하고 밸런싱 전략을 받아오는 노드

    LLM은 다음을 결정:
    1. difficulty_multiplier: 난이도 배율 (0.5~2.0)
    2. preferred_monster_types: 추천 몬스터 타입 리스트 [0: 일반, 1: 엘리트, 2: 보스]
    3. reasoning: 전략 선택 이유
    """
    combat_score = state["combat_score"]
    floor = state.get("floor", 1)
    heroine_stat = state["heroine_stat"]
    dungeon_player_data = state.get("dungeon_player_data", {})

    # 디버그: 입력 데이터 확인
    print(f"[llm_strategy_node DEBUG] combat_score: {combat_score}")
    print(f"[llm_strategy_node DEBUG] heroine_stat type: {type(heroine_stat)}")
    print(f"[llm_strategy_node DEBUG] heroine_stat: {heroine_stat}")
    print(f"[llm_strategy_node DEBUG] dungeon_player_data: {dungeon_player_data}")

    # 멀티 플레이어 감지
    is_party = isinstance(heroine_stat, list)

    if is_party:
        # TODO: 멀티 플레이어 - 대표 히로인 선택 로직 개선 가능
        # 현재: 첫 번째 히로인 사용
        # 개선안: 최고 전투력, 리더 역할 등 고려
        first_stat = heroine_stat[0]
        if isinstance(first_stat, dict):
            hero = StatData(**first_stat)
        else:
            hero = first_stat
        player_count = len(heroine_stat)
    else:
        # 단일 플레이어
        if isinstance(heroine_stat, dict):
            hero = StatData(**heroine_stat)
        else:
            hero = heroine_stat
        player_count = 1

    # 던전 진행 정보
    current_floor = dungeon_player_data.get("scenarioLevel", floor)
    difficulty_level = dungeon_player_data.get("difficulty", 1)
    affection = dungeon_player_data.get("affection", 50)
    sanity = dungeon_player_data.get("sanity", 50)

    # 히로인 요약 정보 생성
    player_type = "파티 평균" if is_party else "플레이어"
    player_info = f" ({player_count}명)" if is_party else ""

    hero_summary = f"""
전투 스탯{player_info}:
- HP: {hero.hp}
- 근력(Strength): {hero.strength}
- 기량(Dexterity): {hero.dexterity}
- 치명타 확률: {hero.critChance:.1f}%
- 공격 속도: {hero.attackSpeed:.2f}x
- 스킬 데미지 배율: {hero.skillDamageMultiplier:.2f}x
- 종합 전투력: {combat_score:.1f} ({player_type})

던전 진행 상황:
- 현재 층: {current_floor}
- 난이도: {difficulty_level}
- 호감도: {affection}
- 정신력: {sanity}
"""

    # TODO: 멀티 플레이어 - 파티원별 상세 정보를 프롬프트에 추가 가능
    # 예: 각 히로인의 역할(탱커/딜러/힐러), 시너지 효과 등

    try:
        # 디버그: hero_summary 출력
        print(f"[llm_strategy_node DEBUG] hero_summary:\n{hero_summary}")
        
        # 프롬프트 생성
        prompts = PromptManager(DungeonPromptType.MONSTER_STRATEGY).get_prompt(
            hero_summary=hero_summary, floor=current_floor
        )
        
        # 디버그: 생성된 프롬프트 전체 출력
        print(f"[llm_strategy_node DEBUG] prompts type: {type(prompts)}")
        print(f"[llm_strategy_node DEBUG] prompts 내용:\n{prompts}\n")
        
        # hero_summary가 프롬프트에 포함되었는지 확인
        if isinstance(prompts, str):
            if "hero_summary" in prompts or "{hero_summary}" in prompts:
                print("[llm_strategy_node ERROR] 프롬프트에 hero_summary 치환 실패!")
            elif "HP: 500" in prompts:
                print("[llm_strategy_node DEBUG] ✅ hero_summary 정상 치환됨")
            else:
                print("[llm_strategy_node WARNING] hero_summary 확인 불가")

        # LLM 호출 (Structured Output)
        parser_llm = llm.with_structured_output(MonsterStrategyParser)
        response = parser_llm.invoke(prompts)

        strategy = {
            "difficulty_multiplier": response.difficulty_multiplier,
            "preferred_tags": response.preferred_tags,
            "monster_preferences": response.monster_preferences,
            "avoid_conditions": response.avoid_conditions,
            "reasoning": response.reasoning,
        }

        print(f"[llm_strategy_node] 난이도 배율: {response.difficulty_multiplier:.2f}")
        print(f"[llm_strategy_node] 추천 태그: {response.preferred_tags}")
        print(f"[llm_strategy_node] 전략 이유: {response.reasoning}")

        return {"llm_strategy": strategy}

    except Exception as e:
        print(f"[llm_strategy_node] LLM 오류 발생, 기본 전략 사용: {e}")
        # Fallback 전략
        fallback_strategy = {
            "difficulty_multiplier": 1.0,
            "preferred_tags": [],
            "reasoning": "LLM 응답 실패로 기본값 적용",
        }
        return {"llm_strategy": fallback_strategy}


def select_monsters_node(state: DungeonMonsterState) -> DungeonMonsterState:
    combat_score = state["combat_score"]
    llm_strategy = state["llm_strategy"]
    monster_db = state.get("monster_db", MONSTER_DATABASE)
    dungeon_data = state.get("dungeon_data", {})

    difficulty_multiplier = llm_strategy["difficulty_multiplier"]
    preferred_tags = llm_strategy.get("preferred_tags", [])

    # 타겟 위협도 계산 (플레이어 전투력 * 난이도 배율)
    target_threat = combat_score * difficulty_multiplier

    print(f"\n[select_monsters_node] 타겟 위협도: {target_threat:.2f}")
    print(f"[select_monsters_node] 배율: {difficulty_multiplier:.2f}")

    # 보스방과 일반 전투방 분리
    rooms = dungeon_data.get("rooms", [])
    boss_rooms = [room for room in rooms if room.get("room_type") == "boss"]
    combat_rooms = [room for room in rooms if room.get("room_type") == "monster"]

    # LLM 전략에서 고급 선호도 추출
    monster_preferences = []
    avoid_conditions = []

    if "monster_preferences" in llm_strategy:
        # MonsterPreference 객체를 dict로 변환
        prefs = llm_strategy["monster_preferences"]
        if prefs:
            for pref in prefs:
                if hasattr(pref, "model_dump"):
                    monster_preferences.append(pref.model_dump())
                elif isinstance(pref, dict):
                    monster_preferences.append(pref)

    if "avoid_conditions" in llm_strategy:
        avoid_conditions = llm_strategy["avoid_conditions"]

    print(f"[select_monsters_node] 선호도 조건: {len(monster_preferences)}개")
    print(f"[select_monsters_node] 회피 조건: {avoid_conditions}")

    # 일반 몬스터 선택 (전투방용)
    selected_monsters = _select_monsters_by_strategy(
        monster_db, target_threat, preferred_tags, monster_preferences, avoid_conditions
    )

    # 던전 데이터에 몬스터 배치
    filled_dungeon = _place_monsters_in_rooms(
        dungeon_data, selected_monsters, combat_rooms, boss_rooms, monster_db
    )

    # 실제 배치된 총 위협도 계산 (보스 포함)
    actual_threat = sum(m.threat_level for m in selected_monsters)
    boss_threat = 0.0

    # 보스 위협도 추가
    if boss_rooms:
        boss_monsters = [m for m in monster_db.values() if m.monster_type == 2]
        if boss_monsters:
            boss_threat = boss_monsters[0].threat_level  # 첫 번째 보스 기준
            actual_threat += boss_threat

    # 난이도 로그 생성
    # TODO: 멀티 플레이어 - 파티 구성 정보 추가 가능
    difficulty_log = {
        "model_used": llm.model_name,
        "combat_score": combat_score,
        "is_party": isinstance(state["heroine_stat"], list),
        "player_count": (
            len(state["heroine_stat"]) if isinstance(state["heroine_stat"], list) else 1
        ),
        "ai_multiplier": difficulty_multiplier,
        "ai_reasoning": llm_strategy["reasoning"],
        "preferred_tags": preferred_tags,
        "target_threat": target_threat,
        "actual_threat": actual_threat,
        "boss_threat": boss_threat,
        "normal_monster_count": len(selected_monsters),
        "has_boss_room": len(boss_rooms) > 0,
        "monster_details": [
            {
                "id": m.monster_id,
                "name": m.monster_name,
                "type": m.monster_type,
                "threat": m.threat_level,
            }
            for m in selected_monsters
        ],
    }

    print(f"[select_monsters_node] 일반 몬스터 수: {len(selected_monsters)}")
    print(f"[select_monsters_node] 보스방 존재: {len(boss_rooms) > 0}")
    print(
        f"[select_monsters_node] 일반 몬스터 위협도: {sum(m.threat_level for m in selected_monsters):.2f}"
    )
    if boss_threat > 0:
        print(f"[select_monsters_node] 보스 위협도: {boss_threat:.2f}")
    print(f"[select_monsters_node] 총 위협도: {actual_threat:.2f}")
    print(f"[select_monsters_node] 달성률: {(actual_threat/target_threat*100):.1f}%")

    return {"filled_dungeon_data": filled_dungeon, "difficulty_log": difficulty_log}


def _select_monsters_by_strategy(
    monster_db: Dict[int, MonsterData],
    target_threat: float,
    preferred_tags: List[str],
    monster_preferences: List[Dict[str, Any]] = None,
    avoid_conditions: List[str] = None,
) -> List[MonsterData]:
    """
    LLM 전략에 따라 몬스터를 선택

    전략:
    1. monster_preferences에 맞는 몬스터 필터링
    2. avoid_conditions에 해당하는 몬스터 제외
    3. 가중치에 따라 확률적 선택
    4. 타겟 위협도에 도달할 때까지 반복
    """
    # 일반 몬스터만 사용 (보스는 별도 처리)
    all_normal_monsters = [m for m in monster_db.values() if m.monster_type == 0]

    if not all_normal_monsters:
        print("[_select_monsters_by_strategy] 사용 가능한 일반 몬스터가 없습니다")
        return []

    # 선호도와 회피 조건으로 몬스터 필터링
    filtered_monsters = _filter_monsters_by_preferences(
        all_normal_monsters, monster_preferences, avoid_conditions
    )

    if not filtered_monsters:
        print("[_select_monsters_by_strategy] 조건에 맞는 몬스터가 없어 전체 풀 사용")
        filtered_monsters = all_normal_monsters

    selected = []
    current_threat = 0.0

    # 타겟 위협도의 90~110% 범위 내로 조정
    min_threat = target_threat * 0.9
    max_threat = target_threat * 1.1

    max_attempts = 100
    attempts = 0

    print(
        f"[_select_monsters_by_strategy] 타겟: {target_threat:.2f}, 필터된 몬스터 수: {len(filtered_monsters)}"
    )

    while current_threat < min_threat and attempts < max_attempts:
        # 가중치 기반 몬스터 선택
        monster = _select_weighted_monster(filtered_monsters, monster_preferences or [])

        # 추가했을 때 max_threat를 너무 초과하지 않는지 확인
        if current_threat + monster.threat_level <= max_threat * 1.2:
            selected.append(monster)
            current_threat += monster.threat_level

        attempts += 1

    return selected


def _filter_monsters_by_preferences(
    monsters: List[MonsterData],
    preferences: List[Dict[str, Any]],
    avoid_conditions: List[str],
) -> List[MonsterData]:
    """선호도와 회피 조건으로 몬스터 필터링"""
    if not preferences and not avoid_conditions:
        return monsters

    filtered = []

    for monster in monsters:
        # 회피 조건 체크
        if avoid_conditions and _should_avoid_monster(monster, avoid_conditions):
            continue

        # 선호도 조건 체크
        if preferences:
            if _matches_any_preference(monster, preferences):
                filtered.append(monster)
        else:
            filtered.append(monster)

    return filtered if filtered else monsters


def _should_avoid_monster(monster: MonsterData, avoid_conditions: List[str]) -> bool:
    """몬스터가 회피 조건에 해당하는지 확인"""
    for condition in avoid_conditions:
        condition_lower = condition.lower()

        if "slow" in condition_lower and monster.speed < 250:
            return True
        if "fast" in condition_lower and monster.speed > 400:
            return True
        if "weak" in condition_lower and monster.attack < 12:
            return True
        if "highattack" in condition_lower and monster.attack > 20:
            return True
        if "lowhp" in condition_lower and monster.hp < 200:
            return True

    return False


def _matches_any_preference(
    monster: MonsterData, preferences: List[Dict[str, Any]]
) -> bool:
    """몬스터가 하나 이상의 선호도 조건에 맞는지 확인"""
    for pref in preferences:
        if _matches_preference(monster, pref):
            return True
    return False


def _matches_preference(monster: MonsterData, preference: Dict[str, Any]) -> bool:
    """몬스터가 특정 선호도 조건에 맞는지 확인"""
    # 몬스터 타입 체크
    if "monster_type" in preference and preference["monster_type"] is not None:
        if monster.monster_name.lower() != preference["monster_type"].lower():
            return False

    # HP 범위 체크
    if "min_hp" in preference and preference["min_hp"] is not None:
        if monster.hp < preference["min_hp"]:
            return False
    if "max_hp" in preference and preference["max_hp"] is not None:
        if monster.hp > preference["max_hp"]:
            return False

    # 공격력 범위 체크
    if "min_attack" in preference and preference["min_attack"] is not None:
        if monster.attack < preference["min_attack"]:
            return False
    if "max_attack" in preference and preference["max_attack"] is not None:
        if monster.attack > preference["max_attack"]:
            return False

    # 이동속도 범위 체크
    if "min_speed" in preference and preference["min_speed"] is not None:
        if monster.speed < preference["min_speed"]:
            return False
    if "max_speed" in preference and preference["max_speed"] is not None:
        if monster.speed > preference["max_speed"]:
            return False

    return True


def _select_weighted_monster(
    monsters: List[MonsterData], preferences: List[Dict[str, Any]]
) -> MonsterData:
    """가중치를 고려하여 몬스터 선택"""
    if not preferences:
        return random.choice(monsters)

    # 각 몬스터의 가중치 계산
    weights = []
    for monster in monsters:
        weight = 0.0
        for pref in preferences:
            if _matches_preference(monster, pref):
                weight += pref.get("weight", 1.0)
        weights.append(weight if weight > 0 else 0.1)  # 최소 가중치

    # 가중치 기반 랜덤 선택
    return random.choices(monsters, weights=weights, k=1)[0]


def _place_monsters_in_rooms(
    dungeon_data: Dict,
    normal_monsters: List[MonsterData],
    combat_rooms: List[Dict],
    boss_rooms: List[Dict],
    monster_db: Dict[int, MonsterData],
) -> Dict:
    """
    몬스터를 전투방과 보스방에 배치

    - 전투방(room_type == "monster"): 일반 몬스터 1~3마리 배치
    - 보스방(room_type == "boss"): 보스 몬스터 1마리 배치
    """
    import copy

    filled_dungeon = copy.deepcopy(dungeon_data)
    
    # filled_dungeon의 rooms에서 room_id로 매칭하여 직접 수정
    rooms_by_id = {room["room_id"]: room for room in filled_dungeon["rooms"]}

    # 보스방에 보스 몬스터 배치 (최우선)
    if boss_rooms:
        boss_monsters = [m for m in monster_db.values() if m.monster_type == 2]

        if not boss_monsters:
            print("[_place_monsters_in_rooms] 경고: 보스 몬스터가 DB에 없습니다")
        else:
            for boss_room_ref in boss_rooms:
                # 보스 몬스터 선택 (여러 개 있으면 랜덤)
                boss = random.choice(boss_monsters)

                boss_spawn_data = {
                    "monster_id": boss.monster_id,
                    "monster_name": boss.monster_name,
                    "monster_type": boss.monster_type,
                    "position": _generate_random_position(),
                    "hp": boss.hp,
                    "attack": boss.attack,
                    "threat_level": boss.threat_level,
                }

                # filled_dungeon의 실제 room에 배치
                room_id = boss_room_ref.get("room_id")
                if room_id in rooms_by_id:
                    rooms_by_id[room_id]["monsters"] = [boss_spawn_data]
                    print(
                        f"[보스방] 방 {room_id}: {boss.monster_name} 배치"
                    )
    else:
        print("[_place_monsters_in_rooms] 경고: 보스방이 없습니다")

    # 전투방에 일반 몬스터 배치
    if not combat_rooms:
        print("[_place_monsters_in_rooms] 전투방이 없습니다")
        return filled_dungeon

    if not normal_monsters:
        print("[_place_monsters_in_rooms] 배치할 일반 몬스터가 없습니다")
        return filled_dungeon

    # 몬스터를 각 전투방에 분배
    monster_index = 0

    for combat_room_ref in combat_rooms:
        if monster_index >= len(normal_monsters):
            break

        # 방당 몬스터 수 (1~3마리)
        monsters_per_room = min(
            random.randint(1, 3), len(normal_monsters) - monster_index
        )
        room_monsters = []

        for _ in range(monsters_per_room):
            if monster_index >= len(normal_monsters):
                break

            monster = normal_monsters[monster_index]
            monster_index += 1

            # 몬스터 배치 데이터 생성
            spawn_data = {
                "monster_id": monster.monster_id,
                "monster_name": monster.monster_name,
                "monster_type": monster.monster_type,
                "position": _generate_random_position(),
                "hp": monster.hp,
                "attack": monster.attack,
                "threat_level": monster.threat_level,
            }
            room_monsters.append(spawn_data)

        # filled_dungeon의 실제 room에 배치
        room_id = combat_room_ref.get("room_id")
        if room_id in rooms_by_id:
            rooms_by_id[room_id]["monsters"] = room_monsters
            print(f"[전투방] 방 {room_id}: {len(room_monsters)}마리 배치")

    return filled_dungeon


def _generate_random_position() -> Dict[str, float]:
    """방 내 랜덤 위치 생성"""
    return {"x": random.uniform(-10, 10), "y": 0, "z": random.uniform(-10, 10)}


# ===== LangGraph 구성 =====
from langgraph.graph import START, END, StateGraph

graph_builder = StateGraph(DungeonMonsterState)

# 노드 추가
graph_builder.add_node("calculate_combat_score_node", calculate_combat_score_node)
graph_builder.add_node("llm_strategy_node", llm_strategy_node)
graph_builder.add_node("select_monsters_node", select_monsters_node)

# 엣지 연결
graph_builder.add_edge(START, "calculate_combat_score_node")
graph_builder.add_edge("calculate_combat_score_node", "llm_strategy_node")
graph_builder.add_edge("llm_strategy_node", "select_monsters_node")
graph_builder.add_edge("select_monsters_node", END)

# 그래프 컴파일
monster_graph = graph_builder.compile()
