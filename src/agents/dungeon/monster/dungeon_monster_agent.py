from langchain.chat_models import init_chat_model
from enums.LLM import LLM
from agents.dungeon.dungeon_state import DungeonMonsterState, MonsterStrategyParser
from agents.dungeon.monster.monster_database import MONSTER_DATABASE, MonsterData
from core.game_dto.StatData import StatData
from typing import Dict, List, Tuple, Any
import random
from agents.dungeon.monster.monster_tags import KEYWORD_MAP, keywords_to_tags

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
    heroine_stat = state.get("heroine_stat")

    if not heroine_stat:
        print("[calculate_combat_score_node] 히로인 스탯 없음, 기본값 100.0 사용")
        return {"combat_score": 100.0}

    # 멀티 플레이어 감지 (List인 경우)
    is_party = isinstance(heroine_stat, list)

    if is_party:
        stats_list = heroine_stat
        if not stats_list:
            return {"combat_score": 100.0}

        # StatData 객체로 변환
        if isinstance(stats_list[0], dict):
            stats_objects = [StatData(**_ensure_stat_dict(stat)) for stat in stats_list]
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
            stat = StatData(**_ensure_stat_dict(heroine_stat))
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
    # 기본 가중치
    hp_score = stat.hp * 0.25
    attack_score = (stat.strength + stat.dexterity) * 0.45
    attack_speed_score = stat.attackSpeed * 12.0
    crit_score = stat.critChance * 0.12
    skill_damage_score = stat.skillDamageMultiplier * 6.0

    base = (
        hp_score + attack_score + attack_speed_score + crit_score + skill_damage_score
    )

    # 추가: 스킬/키워드 보정 (stat.keywords: List[str] 또는 stat.skill_keywords)
    bonus = 0.0
    hero_keywords = []
    if hasattr(stat, "keywords") and stat.keywords:
        hero_keywords = list(stat.keywords)
    elif hasattr(stat, "skill_keywords") and stat.skill_keywords:
        hero_keywords = list(stat.skill_keywords)

    # 간단한 규칙: 원거리/근거리/빠른공격 등 키워드에 따라 보정
    hero_keywords_lower = [k.lower() for k in hero_keywords]
    if any("fast" in k or "빠른" in k for k in hero_keywords_lower):
        bonus += attack_speed_score * 0.15
    if any("strong" in k or "한방" in k or "강한" in k for k in hero_keywords_lower):
        bonus += attack_score * 0.15
    if any("many" in k or "타수" in k for k in hero_keywords_lower):
        bonus += skill_damage_score * 0.1

    return base + bonus


def _ensure_stat_dict(stat: dict) -> dict:
    """
    Ensure the provided heroine stat dict contains required keys for StatData.
    Fill sensible defaults for any missing fields to avoid Pydantic validation errors.
    """
    if stat is None:
        stat = {}
    s = dict(stat)
    s.setdefault("strength", 1)
    s.setdefault("dexterity", 1)
    s.setdefault("intelligence", 1)
    s.setdefault("hp", 100)
    s.setdefault("attackSpeed", 1.0)
    s.setdefault("critChance", 0.0)
    s.setdefault("skillDamageMultiplier", 1.0)
    # optional: skill/keyword list provided by caller
    s.setdefault("keywords", [])
    s.setdefault("skill_keywords", [])
    return s


def llm_strategy_node(state: DungeonMonsterState) -> DungeonMonsterState:
    combat_score = state["combat_score"]
    floor = state.get("floor", 1)
    heroine_stat = state.get("heroine_stat")
    dungeon_player_data = state.get("dungeon_player_data", {})

    # 멀티 플레이어 감지
    is_party = isinstance(heroine_stat, list)

    if is_party:
        first_stat = heroine_stat[0] if heroine_stat else None
        if isinstance(first_stat, dict):
            hero = StatData(**_ensure_stat_dict(first_stat))
        elif first_stat is None:
            hero = StatData(**_ensure_stat_dict({}))
        else:
            hero = first_stat
        player_count = len(heroine_stat)
    else:
        # 단일 플레이어
        if isinstance(heroine_stat, dict):
            hero = StatData(**_ensure_stat_dict(heroine_stat))
        elif heroine_stat is None:
            hero = StatData(**_ensure_stat_dict({}))
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

    # DEBUG: hero_summary와 floor 값 및 타입 출력
    print("[llm_strategy_node DEBUG] hero_summary type:", type(hero_summary))
    print("[llm_strategy_node DEBUG] hero_summary value:\n", hero_summary)
    print("[llm_strategy_node DEBUG] floor type:", type(current_floor))
    print("[llm_strategy_node DEBUG] floor value:", current_floor)

    try:
        # 프롬프트 생성
        try:
            prompts = PromptManager(DungeonPromptType.MONSTER_STRATEGY).get_prompt(
                hero_summary=hero_summary, floor=current_floor
            )
        except ValueError as ve:
            print("[llm_strategy_node ERROR] PromptManager ValueError:", ve)
            raise
        # hero_summary가 프롬프트에 포함되었는지 확인 (치환 실패만 에러로 출력)
        if isinstance(prompts, str):
            if "hero_summary" in prompts or "{hero_summary}" in prompts:
                print("[llm_strategy_node ERROR] 프롬프트에 hero_summary 치환 실패!")

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

    # 보스방과 일반 전투방 분리 (더 관대한 타입 판별)
    rooms = dungeon_data.get("rooms", [])

    def _is_boss_room(room: Dict[str, Any]) -> bool:
        rt = room.get("room_type") or room.get("roomType") or room.get("type")
        # Normalize and be permissive: accept 'boss', 'boss_room', numeric 4
        if isinstance(rt, str):
            v = rt.strip().lower()
            return v in ("boss", "boss_room", "b") or "boss" in v
        if isinstance(rt, int):
            return rt == 4
        return False

    def _is_monster_room(room: Dict[str, Any]) -> bool:
        rt = room.get("room_type") or room.get("roomType") or room.get("type")
        if isinstance(rt, str):
            v = rt.strip().lower()
            return (
                v in ("monster", "combat", "battle") or "monster" in v or "combat" in v
            )
        if isinstance(rt, int):
            return rt == 1
        return False

    boss_rooms = [room for room in rooms if _is_boss_room(room)]
    combat_rooms = [room for room in rooms if _is_monster_room(room)]

    # Debug: 현재 rooms와 판별된 타입 로그
    try:
        print(
            f"[select_monsters_node] rooms: {[ (r.get('room_id'), r.get('room_type') or r.get('roomType') or r.get('type')) for r in rooms ]}"
        )
        print(
            f"[select_monsters_node] identified boss_rooms: {[r.get('room_id') for r in boss_rooms]}"
        )
        print(
            f"[select_monsters_node] identified combat_rooms: {[r.get('room_id') for r in combat_rooms]}"
        )
    except Exception:
        pass

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

    # preference and avoid-condition summary logging removed per user request

    # 일반 몬스터 선택 (전투방용)
    # 히로인 키워드/라벨 추출 (숫자 ID 또는 문자열 모두 허용)
    # 클라에서 제공한 라벨 ID(0..19)를 사용하려면 `keywords` 또는 `keyword_ids` 필드에 숫자 리스트를 넣어주세요.
    hero_tags = []
    heroine_stat_state = state.get("heroine_stat")

    def _normalize_hero_keywords(raw):
        out = []
        if not raw:
            return out
        # list of ints or strings
        for it in raw:
            if isinstance(it, int):
                # convert numeric id to tag via keywords_to_tags
                mapped = keywords_to_tags([it])
                if mapped:
                    out.extend([m.lower() for m in mapped])
            elif isinstance(it, str):
                # try to parse numeric string
                s = it.strip()
                if s.isdigit():
                    mapped = keywords_to_tags([int(s)])
                    out.extend([m.lower() for m in mapped])
                else:
                    out.append(s.lower())
        return out

    if isinstance(heroine_stat_state, list):
        for hs in heroine_stat_state:
            if isinstance(hs, dict):
                # accept multiple possible field names from client
                raw_kw = (
                    hs.get("keywords")
                    or hs.get("keyword_ids")
                    or hs.get("tags")
                    or hs.get("labels")
                    or []
                )
                hero_tags.extend(_normalize_hero_keywords(raw_kw))
    elif isinstance(heroine_stat_state, dict):
        raw_kw = (
            heroine_stat_state.get("keywords")
            or heroine_stat_state.get("keyword_ids")
            or heroine_stat_state.get("tags")
            or heroine_stat_state.get("labels")
            or []
        )
        hero_tags = _normalize_hero_keywords(raw_kw)

    # DEBUG: hero tag summary
    try:
        print(f"[select_monsters_node] hero_tags: {hero_tags}")
    except Exception:
        pass

    # Analyze how hero_tags map to monster weaknesses/strengths across DB
    try:
        tag_weak_counts = {t: 0 for t in hero_tags}
        tag_strong_counts = {t: 0 for t in hero_tags}
        all_monsters = list(monster_db.values())
        for m in all_monsters:
            try:
                m_weak = (
                    keywords_to_tags(m.weaknesses)
                    if getattr(m, "weaknesses", None)
                    else []
                )
                m_strong = (
                    keywords_to_tags(m.strengths)
                    if getattr(m, "strengths", None)
                    else []
                )
            except Exception:
                m_weak = []
                m_strong = []
            m_weak_l = [x.lower() for x in m_weak]
            m_strong_l = [x.lower() for x in m_strong]
            for ht in hero_tags:
                if ht in m_weak_l:
                    tag_weak_counts[ht] = tag_weak_counts.get(ht, 0) + 1
                if ht in m_strong_l:
                    tag_strong_counts[ht] = tag_strong_counts.get(ht, 0) + 1

        print(
            f"[select_monsters_node] hero tag -> monster weakness counts: {tag_weak_counts}"
        )
        print(
            f"[select_monsters_node] hero tag -> monster strength counts: {tag_strong_counts}"
        )
    except Exception:
        pass

    selected_monsters = _select_monsters_by_strategy(
        monster_db,
        target_threat,
        preferred_tags,
        monster_preferences,
        avoid_conditions,
        hero_tags,
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
        "hero_tags": hero_tags,
        "hero_tag_weakness_counts": (
            tag_weak_counts if "tag_weak_counts" in locals() else {}
        ),
        "hero_tag_strength_counts": (
            tag_strong_counts if "tag_strong_counts" in locals() else {}
        ),
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
    hero_tags: List[str] = None,
) -> List[MonsterData]:
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

    try:
        print("[_select_monsters_by_strategy] 후보 몬스터 목록 (id, name, threat, hp, attack, speed):")
        for m in filtered_monsters:
            try:
                print(
                    f"  - {m.monster_id}, {m.monster_name}, threat={m.threat_level:.2f}, hp={m.hp}, atk={m.attack}, spd={m.speed}"
                )
            except Exception:
                print(f"  - {getattr(m,'monster_id', '?')} (failed to print details)")
    except Exception:
        pass

    while current_threat < min_threat and attempts < max_attempts:
        # 가중치 기반 몬스터 선택 (히로인 키워드 반영)
        monster = _select_weighted_monster(
            filtered_monsters, monster_preferences or [], hero_tags or []
        )

        # 추가했을 때 max_threat를 너무 초과하지 않는지 확인
        if current_threat + monster.threat_level <= max_threat * 1.2:
            selected.append(monster)
            current_threat += monster.threat_level

        attempts += 1

    if not selected:
        sorted_monsters = sorted(filtered_monsters, key=lambda m: m.threat_level)
        for m in sorted_monsters:
            if current_threat >= min_threat:
                break
            selected.append(m)
            current_threat += m.threat_level

        try:
            print("[_select_monsters_by_strategy] Fallback 적용: 작은 위협도 몬스터로 채움")
            for m in selected:
                print(f"  -> {m.monster_id} {m.monster_name} threat={m.threat_level:.2f}")
        except Exception:
            pass

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
    monsters: List[MonsterData], preferences: List[Dict[str, Any]], hero_tags: List[str]
) -> MonsterData:
    """가중치를 고려하여 몬스터 선택"""
    if not preferences:
        # 히로인 태그가 있으면 약점이 있는 몬스터 우선
        if hero_tags:
            candidates = []
            for m in monsters:
                m_tags = (
                    keywords_to_tags(m.weaknesses)
                    if getattr(m, "weaknesses", None)
                    else []
                )
                if any(ht.lower() in [t.lower() for t in m_tags] for ht in hero_tags):
                    candidates.append(m)
            if candidates:
                return random.choice(candidates)
        return random.choice(monsters)

    # 각 몬스터의 가중치 계산
    weights = []
    for monster in monsters:
        weight = 0.0
        for pref in preferences:
            if _matches_preference(monster, pref):
                weight += pref.get("weight", 1.0)

        # 히로인 태그와 몬스터 약점/강점으로 가중치 보정
        try:
            monster_weak_tags = (
                keywords_to_tags(monster.weaknesses)
                if getattr(monster, "weaknesses", None)
                else []
            )
            monster_strong_tags = (
                keywords_to_tags(monster.strengths)
                if getattr(monster, "strengths", None)
                else []
            )
        except Exception:
            monster_weak_tags = []
            monster_strong_tags = []

        if hero_tags:
            # 약점과 일치하면 가중치 상승
            if any(
                ht.lower() in [t.lower() for t in monster_weak_tags] for ht in hero_tags
            ):
                weight *= 1.6 if weight > 0 else 1.6
            # 강점과 일치하면 가중치 감소
            if any(
                ht.lower() in [t.lower() for t in monster_strong_tags]
                for ht in hero_tags
            ):
                weight *= 0.6

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

                # filled_dungeon의 실제 room에 배치 (monster_id만 저장)
                room_id = boss_room_ref.get("room_id")
                if room_id in rooms_by_id:
                    rooms_by_id[room_id]["monsters"] = [boss.monster_id]
                    print(f"[보스방] 방 {room_id}: 몬스터 ID {boss.monster_id} 배치")
    else:
        print("[_place_monsters_in_rooms] 경고: 보스방이 없습니다")

    # 전투방에 일반 몬스터 배치
    if not combat_rooms:
        # Fallback: detect rooms by numeric 'type' == 1 or 'roomType' == 1
        fallback_combat = [
            r
            for r in filled_dungeon.get("rooms", [])
            if r.get("type") == 1 or r.get("roomType") == 1
        ]
        if fallback_combat:
            combat_rooms = fallback_combat
            print(
                "[_place_monsters_in_rooms] 전투방이 탐지되지 않아 'type==1' 룸들을 전투방으로 처리합니다",
                [r.get("room_id") for r in combat_rooms],
            )
        else:
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

            # monster_id만 저장
            room_monsters.append(monster.monster_id)

        # filled_dungeon의 실제 room에 배치
        room_id = combat_room_ref.get("room_id")
        if room_id in rooms_by_id:
            rooms_by_id[room_id]["monsters"] = room_monsters
            print(f"[전투방] 방 {room_id}: {len(room_monsters)}마리 배치")

    return filled_dungeon


def _generate_random_position() -> Dict[str, float]:
    """방 내 랜덤 위치 생성"""
    # 0.0 ~ 1.0 범위의 정규화된 좌표 반환 (언리얼 배치용)
    return {"x": random.random(), "y": random.random(), "z": random.random()}


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
