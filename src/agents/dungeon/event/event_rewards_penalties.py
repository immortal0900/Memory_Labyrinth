
# 몬스터 스폰 보상 예시
SPAWN_MONSTER_REWARDS = [
    {"id": "spawn_slime_1", "type": "spawn_monster", "monster_id": 1, "count": 1, "description": "이벤트방에 슬라임 1마리 등장"},
    {"id": "spawn_goblin_2", "type": "spawn_monster", "monster_id": 2, "count": 2, "description": "이벤트방에 고블린 2마리 등장"},
]

# 아이템 드랍 보상 예시
DROP_ITEM_REWARDS = [
    {"id": "drop_weapon_101", "type": "drop_item", "item_id": 101, "count": 1, "item_type": "weapon", "description": "무기 아이템 1개 드랍"},
    {"id": "drop_accessory_201", "type": "drop_item", "item_id": 201, "count": 1, "item_type": "accessory", "description": "장신구 아이템 1개 드랍"},
]

# statData와 로코 성장치(체력+10, 근력+3, 기량+1) 기준으로 밸런스 있게 value 설정
CHANGE_STAT_REWARDS = [
    # 체력: 기본 200, 성장치 +10 → 보상은 +10, +20, 패널티는 -10, -20 등
    {"id": "hp_up_10", "type": "change_stat", "stat": "hp", "value": 10, "duration": 0, "target": "all", "description": "모든 플레이어 최대 체력 +10"},
    {"id": "hp_up_20", "type": "change_stat", "stat": "hp", "value": 20, "duration": 0, "target": "all", "description": "모든 플레이어 최대 체력 +20"},
    {"id": "hp_heal_50", "type": "change_stat", "stat": "hp", "value": 50, "duration": 0, "target": "all", "description": "모든 플레이어 체력 50 회복"},
    # 근력: 성장치 +3 → 보상은 +3, +6, 패널티는 -3, -6 등
    {"id": "str_up_3", "type": "change_stat", "stat": "strength", "value": 3, "duration": 0, "target": "all", "description": "모든 플레이어 근력 +3"},
    {"id": "str_up_6", "type": "change_stat", "stat": "strength", "value": 6, "duration": 0, "target": "all", "description": "모든 플레이어 근력 +6"},
    # 기량: 성장치 +1 → 보상은 +1, +2, 패널티는 -1, -2 등
    {"id": "dex_up_1", "type": "change_stat", "stat": "dexterity", "value": 1, "duration": 0, "target": "all", "description": "모든 플레이어 기량 +1"},
    {"id": "dex_up_2", "type": "change_stat", "stat": "dexterity", "value": 2, "duration": 0, "target": "all", "description": "모든 플레이어 기량 +2"},
    # 기타 주요 스탯(표 참고, 적정 범위 내 value)
    {"id": "move_up_10p", "type": "change_stat", "stat": "moveSpeed", "value": 0.1, "duration": 0, "target": "all", "description": "모든 플레이어 이동속도 +10%"},
    {"id": "crit_up_10p", "type": "change_stat", "stat": "critChance", "value": 10.0, "duration": 0, "target": "all", "description": "모든 플레이어 치명타 확률 +10%"},
    {"id": "atkspd_up_10p", "type": "change_stat", "stat": "attackSpeed", "value": 0.1, "duration": 0, "target": "all", "description": "모든 플레이어 공격속도 +10%"},
    {"id": "cd_down_10p", "type": "change_stat", "stat": "cooldownReduction", "value": 0.1, "duration": 0, "target": "all", "description": "모든 플레이어 쿨타임 -10%"},
    {"id": "skilldmg_up_10p", "type": "change_stat", "stat": "skillDamageMultiplier", "value": 0.1, "duration": 0, "target": "all", "description": "모든 플레이어 스킬 데미지 +10%"},
]

# 패널티도 동일하게 구조화 (공통 적용)
SPAWN_MONSTER_PENALTIES = [
    {"id": "spawn_skeleton_1", "type": "spawn_monster", "monster_id": 3, "count": 1, "description": "스켈레톤 1마리 등장(패널티)"},
]
DROP_ITEM_PENALTIES = [
    {"id": "drop_cursed_301", "type": "drop_item", "item_id": 301, "count": 1, "item_type": "cursed", "description": "저주 아이템 드랍(패널티)"},
]
CHANGE_STAT_PENALTIES = [
    {"id": "hp_down_10", "type": "change_stat", "stat": "hp", "value": -10, "duration": 0, "target": "all", "description": "모든 플레이어 최대 체력 -10(패널티)"},
    {"id": "hp_down_20", "type": "change_stat", "stat": "hp", "value": -20, "duration": 0, "target": "all", "description": "모든 플레이어 최대 체력 -20(패널티)"},
    {"id": "str_down_3", "type": "change_stat", "stat": "strength", "value": -3, "duration": 0, "target": "all", "description": "모든 플레이어 근력 -3(패널티)"},
    {"id": "str_down_6", "type": "change_stat", "stat": "strength", "value": -6, "duration": 0, "target": "all", "description": "모든 플레이어 근력 -6(패널티)"},
    {"id": "dex_down_1", "type": "change_stat", "stat": "dexterity", "value": -1, "duration": 0, "target": "all", "description": "모든 플레이어 기량 -1(패널티)"},
    {"id": "dex_down_2", "type": "change_stat", "stat": "dexterity", "value": -2, "duration": 0, "target": "all", "description": "모든 플레이어 기량 -2(패널티)"},
    {"id": "move_down_10p", "type": "change_stat", "stat": "moveSpeed", "value": -0.1, "duration": 0, "target": "all", "description": "모든 플레이어 이동속도 -10%(패널티)"},
    {"id": "crit_down_10p", "type": "change_stat", "stat": "critChance", "value": -10.0, "duration": 0, "target": "all", "description": "모든 플레이어 치명타 확률 -10%(패널티)"},
    {"id": "atkspd_down_10p", "type": "change_stat", "stat": "attackSpeed", "value": -0.1, "duration": 0, "target": "all", "description": "모든 플레이어 공격속도 -10%(패널티)"},
    {"id": "cd_up_10p", "type": "change_stat", "stat": "cooldownReduction", "value": -0.1, "duration": 0, "target": "all", "description": "모든 플레이어 쿨타임 +10%(패널티)"},
    {"id": "skilldmg_down_10p", "type": "change_stat", "stat": "skillDamageMultiplier", "value": -0.1, "duration": 0, "target": "all", "description": "모든 플레이어 스킬 데미지 -10%(패널티)"},
]

# def get_all_reward_ids():
#     """모든 보상 ID 리스트"""
#     return list(SPAWN_MONSTER_REWARDS.keys()) + list(DROP_ITEM_REWARDS.keys()) + list(CHANGE_STAT_REWARDS.keys())

# def get_all_penalty_ids():
#     """모든 패널티 ID 리스트"""
#     return list(SPAWN_MONSTER_PENALTIES.keys()) + list(DROP_ITEM_PENALTIES.keys()) + list(CHANGE_STAT_PENALTIES.keys())

def get_reward_dict(reward_id: str):
    """보상 id로 반환용 dict"""
    for r in SPAWN_MONSTER_REWARDS + DROP_ITEM_REWARDS + CHANGE_STAT_REWARDS:
        if r["id"] == reward_id:
            return {k: v for k, v in r.items() if k not in ("id", "description")}
    return None

def get_penalty_dict(penalty_id: str):
    """패널티 id로 반환용 dict"""
    for p in SPAWN_MONSTER_PENALTIES + DROP_ITEM_PENALTIES + CHANGE_STAT_PENALTIES:
        if p["id"] == penalty_id:
            return {k: v for k, v in p.items() if k not in ("id", "description")}
    return None