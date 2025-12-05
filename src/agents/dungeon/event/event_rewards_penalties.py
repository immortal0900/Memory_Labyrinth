"""
던전 이벤트에서 사용 가능한 보상/패널티 목록
실제 게임 DTO(StatData, ItemData, RoomData 등)를 기반으로 구현 가능한 것들만 정의
"""

# =============================================================================
# 보상 (Rewards)
# =============================================================================
REWARDS = {
    # 스탯 증가 (StatData 기반)
    "hp_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 최대 체력이 50 증가한다",
        "effect": {"stat": "hp", "value": 50, "target": "all"},
    },
    "strength_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 근력이 5 증가한다",
        "effect": {"stat": "strength", "value": 5, "target": "all"},
    },
    "dexterity_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 기량이 5 증가한다",
        "effect": {"stat": "dexterity", "value": 5, "target": "all"},
    },
    "move_speed_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 이동속도가 10% 증가한다 (moveSpeed +0.1)",
        "effect": {"stat": "moveSpeed", "value": 0.1, "target": "all"},
    },
    "crit_chance_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 치명타 확률이 10% 증가한다",
        "effect": {"stat": "critChance", "value": 10.0, "target": "all"},
    },
    "attack_speed_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 공격 속도가 15% 증가한다 (attackSpeed +0.15)",
        "effect": {"stat": "attackSpeed", "value": 0.15, "target": "all"},
    },
    "cooldown_reduction_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 쿨타임이 10% 감소한다 (cooldownReduction +0.1)",
        "effect": {"stat": "cooldownReduction", "value": 0.1, "target": "all"},
    },
    "skill_damage_increase_all": {
        "type": "stat_buff",
        "description": "모든 플레이어의 스킬 데미지가 20% 증가한다 (skillDamageMultiplier +0.2)",
        "effect": {"stat": "skillDamageMultiplier", "value": 0.2, "target": "all"},
    },
    # 체력 회복
    "hp_recovery_all": {
        "type": "recovery",
        "description": "모든 플레이어의 체력이 100 회복된다",
        "effect": {"stat": "hp", "value": 100, "target": "all"},
    },
    # 아이템 보상 (ItemData 기반 - 레어도 지정)
    "item_reward_common": {
        "type": "item",
        "description": "모든 플레이어가 커먼(rarity=0) 아이템을 1개 획득한다",
        "effect": {"action": "add_item", "rarity": 0, "count": 1, "target": "all"},
    },
    "item_reward_uncommon": {
        "type": "item",
        "description": "모든 플레이어가 언커먼(rarity=1) 아이템을 1개 획득한다",
        "effect": {"action": "add_item", "rarity": 1, "count": 1, "target": "all"},
    },
    "item_reward_rare": {
        "type": "item",
        "description": "모든 플레이어가 레어(rarity=2) 아이템을 1개 획득한다",
        "effect": {"action": "add_item", "rarity": 2, "count": 1, "target": "all"},
    },
}

# =============================================================================
# 패널티 (Penalties)
# =============================================================================
PENALTIES = {
    # 스탯 감소 (StatData 기반)
    "hp_decrease_all": {
        "type": "stat_debuff",
        "description": "모든 플레이어의 최대 체력이 30 감소한다",
        "effect": {"stat": "hp", "value": -30, "target": "all"},
    },
    "strength_decrease_all": {
        "type": "stat_debuff",
        "description": "모든 플레이어의 근력이 3 감소한다",
        "effect": {"stat": "strength", "value": -3, "target": "all"},
    },
    "dexterity_decrease_all": {
        "type": "stat_debuff",
        "description": "모든 플레이어의 기량이 3 감소한다",
        "effect": {"stat": "dexterity", "value": -3, "target": "all"},
    },
    "move_speed_decrease_all": {
        "type": "stat_debuff",
        "description": "모든 플레이어의 이동속도가 10% 감소한다 (moveSpeed -0.1)",
        "effect": {"stat": "moveSpeed", "value": -0.1, "target": "all"},
    },
    "crit_chance_decrease_all": {
        "type": "stat_debuff",
        "description": "모든 플레이어의 치명타 확률이 10% 감소한다",
        "effect": {"stat": "critChance", "value": -10.0, "target": "all"},
    },
    "attack_speed_decrease_all": {
        "type": "stat_debuff",
        "description": "모든 플레이어의 공격 속도가 15% 감소한다 (attackSpeed -0.15)",
        "effect": {"stat": "attackSpeed", "value": -0.15, "target": "all"},
    },
    # 즉시 데미지
    "instant_damage_low": {
        "type": "damage",
        "description": "모든 플레이어가 50의 고정 피해를 입는다",
        "effect": {"damage_type": "fixed", "value": 50, "target": "all"},
    },
    "instant_damage_medium": {
        "type": "damage",
        "description": "모든 플레이어가 100의 고정 피해를 입는다",
        "effect": {"damage_type": "fixed", "value": 100, "target": "all"},
    },
    "instant_damage_high": {
        "type": "damage",
        "description": "모든 플레이어가 150의 고정 피해를 입는다",
        "effect": {"damage_type": "fixed", "value": 150, "target": "all"},
    },
    # 디버프 (지속 효과)
    "slow_debuff": {
        "type": "debuff",
        "description": "모든 플레이어에게 '감속' 디버프가 적용된다 (2분간 이동속도 20% 감소)",
        "effect": {
            "debuff_id": "slow",
            "duration": 120,
            "stat": "moveSpeed",
            "value": -0.2,
            "target": "all",
        },
    },
    "weakness_debuff": {
        "type": "debuff",
        "description": "모든 플레이어에게 '허약' 디버프가 적용된다 (3분간 근력 5 감소)",
        "effect": {
            "debuff_id": "weakness",
            "duration": 180,
            "stat": "strength",
            "value": -5,
            "target": "all",
        },
    },
    "curse_debuff": {
        "type": "debuff",
        "description": "모든 플레이어에게 '저주' 디버프가 적용된다 (3분간 모든 스킬 데미지 20% 감소)",
        "effect": {
            "debuff_id": "curse",
            "duration": 180,
            "stat": "skillDamageMultiplier",
            "value": -0.2,
            "target": "all",
        },
    },
}

# =============================================================================
# 중립 결과 (Neutral - 정보/힌트만 제공)
# =============================================================================
NEUTRAL_OUTCOMES = {
    "hint_only": {
        "type": "information",
        "description": "유용한 정보나 힌트를 획득하지만, 즉각적인 보상이나 패널티는 없다",
        "effect": {"action": "add_hint", "target": "player"},
    },
    "nothing": {
        "type": "none",
        "description": "아무 일도 일어나지 않는다",
        "effect": None,
    },
}


def get_reward(reward_id: str):
    """보상 정보 가져오기"""
    return REWARDS.get(reward_id)


def get_penalty(penalty_id: str):
    """패널티 정보 가져오기"""
    return PENALTIES.get(penalty_id)


def get_all_reward_ids():
    """모든 보상 ID 리스트"""
    return list(REWARDS.keys())


def get_all_penalty_ids():
    """모든 패널티 ID 리스트"""
    return list(PENALTIES.keys())
