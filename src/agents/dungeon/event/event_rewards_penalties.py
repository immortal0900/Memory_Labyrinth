from typing import List, Dict, Any, Optional
import random


# Static reward / penalty pools (snapshot generated)
# All rewards/penalties target all players (`target: "all"`)

# Spawnable monsters
SPAWN_MONSTER_REWARDS: List[Dict[str, Any]] = [
    {
        "id": "spawn_monster_0",
        "type": "spawn_monster",
        "monster_id": 0,
        "count": 1,
        "description": "스켈레톤 1마리 등장",
        "target": "all",
    },
    {
        "id": "spawn_monster_1",
        "type": "spawn_monster",
        "monster_id": 1,
        "count": 1,
        "description": "저주받은 고사지 1마리 등장",
        "target": "all",
    },
    {
        "id": "spawn_monster_2",
        "type": "spawn_monster",
        "monster_id": 2,
        "count": 1,
        "description": "거미 1마리 등장",
        "target": "all",
    },
    {
        "id": "spawn_monster_3",
        "type": "spawn_monster",
        "monster_id": 3,
        "count": 1,
        "description": "언데드 1마리 등장",
        "target": "all",
    },
    {
        "id": "spawn_monster_4",
        "type": "spawn_monster",
        "monster_id": 4,
        "count": 1,
        "description": "스켈레톤 석궁병 1마리 등장",
        "target": "all",
    },
    {
        "id": "spawn_monster_5",
        "type": "spawn_monster",
        "monster_id": 5,
        "count": 1,
        "description": "천번찔린 언데드 1마리 등장",
        "target": "all",
    },
]


# Item drops (weapons + accessories)
DROP_ITEM_REWARDS: List[Dict[str, Any]] = [
    {
        "id": "drop_weapon_0",
        "type": "drop_item",
        "item_id": 0,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 숏소드 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_1",
        "type": "drop_item",
        "item_id": 1,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 숏소드 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_2",
        "type": "drop_item",
        "item_id": 2,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 숏소드 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_3",
        "type": "drop_item",
        "item_id": 3,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 숏소드 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_4",
        "type": "drop_item",
        "item_id": 4,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 한손검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_5",
        "type": "drop_item",
        "item_id": 5,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 한손검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_6",
        "type": "drop_item",
        "item_id": 6,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 한손검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_7",
        "type": "drop_item",
        "item_id": 7,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 한손검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_20",
        "type": "drop_item",
        "item_id": 20,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 쌍검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_21",
        "type": "drop_item",
        "item_id": 21,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 쌍검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_22",
        "type": "drop_item",
        "item_id": 22,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 쌍검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_23",
        "type": "drop_item",
        "item_id": 23,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 쌍검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_24",
        "type": "drop_item",
        "item_id": 24,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 양손 메서 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_25",
        "type": "drop_item",
        "item_id": 25,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 양손 메서 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_26",
        "type": "drop_item",
        "item_id": 26,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 양손 메서 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_27",
        "type": "drop_item",
        "item_id": 27,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 양손 메서 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_40",
        "type": "drop_item",
        "item_id": 40,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 대검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_41",
        "type": "drop_item",
        "item_id": 41,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 대검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_42",
        "type": "drop_item",
        "item_id": 42,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 대검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_43",
        "type": "drop_item",
        "item_id": 43,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 대검 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_44",
        "type": "drop_item",
        "item_id": 44,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 드레곤슬레이어 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_45",
        "type": "drop_item",
        "item_id": 45,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 드레곤슬레이어 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_46",
        "type": "drop_item",
        "item_id": 46,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 드레곤슬레이어 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_47",
        "type": "drop_item",
        "item_id": 47,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 드레곤슬레이어 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_60",
        "type": "drop_item",
        "item_id": 60,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 드워프 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_61",
        "type": "drop_item",
        "item_id": 61,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 드워프 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_62",
        "type": "drop_item",
        "item_id": 62,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 드워프 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_63",
        "type": "drop_item",
        "item_id": 63,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 드워프 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_64",
        "type": "drop_item",
        "item_id": 64,
        "count": 1,
        "item_type": "weapon",
        "description": "일반 바이킹 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_65",
        "type": "drop_item",
        "item_id": 65,
        "count": 1,
        "item_type": "weapon",
        "description": "고급 바이킹 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_66",
        "type": "drop_item",
        "item_id": 66,
        "count": 1,
        "item_type": "weapon",
        "description": "레어 바이킹 망치 드랍",
        "target": "all",
    },
    {
        "id": "drop_weapon_67",
        "type": "drop_item",
        "item_id": 67,
        "count": 1,
        "item_type": "weapon",
        "description": "레전드 바이킹 망치 드랍",
        "target": "all",
    },
]


# Accessories
DROP_ITEM_REWARDS += [
    {
        "id": "drop_accessory_100",
        "type": "drop_item",
        "item_id": 100,
        "count": 1,
        "item_type": "accessory",
        "description": "용표식 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_101",
        "type": "drop_item",
        "item_id": 101,
        "count": 1,
        "item_type": "accessory",
        "description": "투검의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_102",
        "type": "drop_item",
        "item_id": 102,
        "count": 1,
        "item_type": "accessory",
        "description": "회복의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_103",
        "type": "drop_item",
        "item_id": 103,
        "count": 1,
        "item_type": "accessory",
        "description": "축복의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_104",
        "type": "drop_item",
        "item_id": 104,
        "count": 1,
        "item_type": "accessory",
        "description": "증오의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_105",
        "type": "drop_item",
        "item_id": 105,
        "count": 1,
        "item_type": "accessory",
        "description": "라다곤의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_106",
        "type": "drop_item",
        "item_id": 106,
        "count": 1,
        "item_type": "accessory",
        "description": "윤여민의 손가락 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_107",
        "type": "drop_item",
        "item_id": 107,
        "count": 1,
        "item_type": "accessory",
        "description": "광전사의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_108",
        "type": "drop_item",
        "item_id": 108,
        "count": 1,
        "item_type": "accessory",
        "description": "마누라니의 반지 드랍",
        "target": "all",
    },
    {
        "id": "drop_accessory_109",
        "type": "drop_item",
        "item_id": 109,
        "count": 1,
        "item_type": "accessory",
        "description": "켈빈 클라인 드랍",
        "target": "all",
    },
]


# Stat change rewards
CHANGE_STAT_REWARDS: List[Dict[str, Any]] = [
    {
        "id": "hp_up_10",
        "type": "change_stat",
        "stat": "hp",
        "value": 10,
        "duration": 0,
        "target": "all",
        "description": "Max HP +10",
    },
    {
        "id": "hp_up_20",
        "type": "change_stat",
        "stat": "hp",
        "value": 20,
        "duration": 0,
        "target": "all",
        "description": "Max HP +20",
    },
    {
        "id": "str_up_3",
        "type": "change_stat",
        "stat": "strength",
        "value": 3,
        "duration": 0,
        "target": "all",
        "description": "Strength +3",
    },
    {
        "id": "str_up_6",
        "type": "change_stat",
        "stat": "strength",
        "value": 6,
        "duration": 0,
        "target": "all",
        "description": "Strength +6",
    },
    {
        "id": "dex_up_1",
        "type": "change_stat",
        "stat": "dexterity",
        "value": 1,
        "duration": 0,
        "target": "all",
        "description": "Dexterity +1",
    },
    {
        "id": "dex_up_2",
        "type": "change_stat",
        "stat": "dexterity",
        "value": 2,
        "duration": 0,
        "target": "all",
        "description": "Dexterity +2",
    },
    {
        "id": "skilldmg_up_10p",
        "type": "change_stat",
        "stat": "skillDamageMultiplier",
        "value": 0.1,
        "duration": 60,
        "target": "all",
        "description": "Skill damage +10% (60s)",
    },
    {
        "id": "autoatk_up_10p",
        "type": "change_stat",
        "stat": "autoAttackMultiplier",
        "value": 0.1,
        "duration": 60,
        "target": "all",
        "description": "Auto-attack multiplier +10% (60s)",
    },
    {
        "id": "atkspd_up_10p",
        "type": "change_stat",
        "stat": "attackSpeed",
        "value": 0.1,
        "duration": 30,
        "target": "all",
        "description": "Attack speed +10% (30s)",
    },
]


# Penalties
SPAWN_MONSTER_PENALTIES: List[Dict[str, Any]] = [
    {
        "id": "pen_spawn_monster_0",
        "type": "spawn_monster",
        "monster_id": 0,
        "count": 1,
        "description": "스켈레톤 1마리 등장(패널티)",
        "target": "all",
    },
    {
        "id": "pen_spawn_monster_1",
        "type": "spawn_monster",
        "monster_id": 1,
        "count": 1,
        "description": "저주받은 고사지 등장(패널티)",
        "target": "all",
    },
    {
        "id": "pen_spawn_monster_2",
        "type": "spawn_monster",
        "monster_id": 2,
        "count": 1,
        "description": "거미 등장(패널티)",
        "target": "all",
    },
]

DROP_ITEM_PENALTIES: List[Dict[str, Any]] = [
    {
        "id": "drop_cursed_301",
        "type": "drop_item",
        "item_id": 301,
        "count": 1,
        "item_type": "cursed",
        "description": "저주 아이템 드랍",
        "target": "all",
    },
]

CHANGE_STAT_PENALTIES: List[Dict[str, Any]] = [
    {
        "id": "hp_down_10",
        "type": "change_stat",
        "stat": "hp",
        "value": -10,
        "duration": 0,
        "target": "all",
        "description": "Max HP -10",
    },
    {
        "id": "hp_down_20",
        "type": "change_stat",
        "stat": "hp",
        "value": -20,
        "duration": 0,
        "target": "all",
        "description": "Max HP -20",
    },
    {
        "id": "str_down_3",
        "type": "change_stat",
        "stat": "strength",
        "value": -3,
        "duration": 0,
        "target": "all",
        "description": "Strength -3",
    },
    {
        "id": "dex_down_1",
        "type": "change_stat",
        "stat": "dexterity",
        "value": -1,
        "duration": 0,
        "target": "all",
        "description": "Dexterity -1",
    },
    {
        "id": "skilldmg_down_10p",
        "type": "change_stat",
        "stat": "skillDamageMultiplier",
        "value": -0.1,
        "duration": 60,
        "target": "all",
        "description": "Skill damage -10% (60s)",
    },
    {
        "id": "atkspd_down_10p",
        "type": "change_stat",
        "stat": "attackSpeed",
        "value": -0.1,
        "duration": 30,
        "target": "all",
        "description": "Attack speed -10% (30s)",
    },
]

ALL_REWARDS = SPAWN_MONSTER_REWARDS + DROP_ITEM_REWARDS + CHANGE_STAT_REWARDS
ALL_PENALTIES = SPAWN_MONSTER_PENALTIES + DROP_ITEM_PENALTIES + CHANGE_STAT_PENALTIES


def _find_by_id(collection: List[Dict[str, Any]], rid: str) -> Optional[Dict[str, Any]]:
    for r in collection:
        if r.get("id") == rid:
            return r
    return None


def get_reward_dict(reward_id: str) -> Optional[Dict[str, Any]]:
    """Return a copy of reward dict by id (or None)."""
    r = _find_by_id(ALL_REWARDS, reward_id)
    return dict(r) if r else None


def get_penalty_dict(penalty_id: str) -> Optional[Dict[str, Any]]:
    r = _find_by_id(ALL_PENALTIES, penalty_id)
    return dict(r) if r else None


def pick_random_reward(kind: str = "any") -> Optional[Dict[str, Any]]:
    """Pick random reward. kind: 'monster'|'item'|'stat'|'any'"""
    if kind == "monster":
        pool = SPAWN_MONSTER_REWARDS
    elif kind == "item":
        pool = DROP_ITEM_REWARDS
    elif kind == "stat":
        pool = CHANGE_STAT_REWARDS
    else:
        pool = ALL_REWARDS
    if not pool:
        return None
    return dict(random.choice(pool))


def pick_random_penalty(kind: str = "any") -> Optional[Dict[str, Any]]:
    if kind == "monster":
        pool = SPAWN_MONSTER_PENALTIES
    elif kind == "item":
        pool = DROP_ITEM_PENALTIES
    elif kind == "stat":
        pool = CHANGE_STAT_PENALTIES
    else:
        pool = ALL_PENALTIES
    if not pool:
        return None
    return dict(random.choice(pool))


def _to_client_payload(entry: Dict[str, Any]) -> Any:
    """Convert internal reward/penalty entry to client-friendly payload.
    - spawn_monster -> {"monsterId": [id, ...]}
    - drop_item (weapon) -> {"weaponId": id}
    - drop_item (accessory) -> {"accessoryId": id}
    - change_stat -> {"stat": {"name": stat, "value": value, "duration": duration}}
    If entry is None, return None.
    """
    if not entry:
        return None
    t = entry.get("type")
    if t == "spawn_monster":
        mid = entry.get("monster_id")
        if isinstance(mid, list):
            return {"monsterId": mid}
        return {"monsterId": [mid]}
    if t == "drop_item":
        item_id = entry.get("item_id")
        itype = entry.get("item_type")
        if itype == "weapon":
            return {"weaponId": item_id}
        if itype == "accessory":
            return {"accessoryId": item_id}
        return {"itemId": item_id}
    if t == "change_stat":
        return {
            "stat": {
                "name": entry.get("stat"),
                "value": entry.get("value"),
                "duration": entry.get("duration", 0),
            }
        }
    # fallback: expose internal id
    if "id" in entry:
        return {"id": entry.get("id")}
    return entry


def normalize_reward_payload(raw: Any) -> Any:
    """Normalize reward representation (raw from event choice) into client payload.
    Accepts: None, string id, dict with id, list, or already-structured client payload.
    """
    if raw is None:
        return None
    # If it's already in client payload shape (contains keys like monsterId/weaponId)
    if isinstance(raw, dict) and (
        "monsterId" in raw or "weaponId" in raw or "accessoryId" in raw or "stat" in raw
    ):
        return raw

    # If it's a list of numeric ids for monsters
    if isinstance(raw, list):
        # assume monster ids
        return {"monsterId": raw}

    # If it's a string id mapping to internal reward
    if isinstance(raw, str):
        r = get_reward_dict(raw)
        if r:
            return _to_client_payload(r)
        # unknown string: return as id wrapper
        return {"id": raw}

    # If it's a dict with an 'id' key
    if isinstance(raw, dict) and "id" in raw:
        r = get_reward_dict(raw.get("id"))
        if r:
            return _to_client_payload(r)
        # if contains type-like fields, try to convert directly
        return _to_client_payload(raw)

    return None


def normalize_penalty_payload(raw: Any) -> Any:
    """Same as normalize_reward_payload but for penalties."""
    if raw is None:
        return None
    if isinstance(raw, dict) and (
        "monsterId" in raw or "weaponId" in raw or "accessoryId" in raw or "stat" in raw
    ):
        return raw
    if isinstance(raw, list):
        return {"monsterId": raw}
    if isinstance(raw, str):
        # special token: deterministic default penalty for unexpected actions
        if raw == "penalty_unexpected_action":
            # Default: apply HP -10 and spawn 1 skeleton (both target: all)
            default_stat = get_penalty_dict("hp_down_10")
            default_spawn = get_penalty_dict("pen_spawn_monster_0")
            payloads = []
            if default_stat:
                payloads.append(_to_client_payload(default_stat))
            if default_spawn:
                payloads.append(_to_client_payload(default_spawn))
            # Return list so client can process multiple applied penalties
            return payloads if payloads else {"id": raw}
        p = get_penalty_dict(raw)
        if p:
            return _to_client_payload(p)
        return {"id": raw}
    if isinstance(raw, dict) and "id" in raw:
        p = get_penalty_dict(raw.get("id"))
        if p:
            return _to_client_payload(p)
        return _to_client_payload(raw)
    return None


def select_best_reward(raw: Any, action_text: str = "", scenario_text: str = "") -> Any:
    """Rule-based selection for reward when explicit reward is not provided.

    Returns a client payload (same shape as normalize_reward_payload).
    """
    act = (action_text or "").lower()

    # keyword groups
    HELP_KW = ["치료", "도움", "구해"]
    TRADE_KW = ["거래", "교환"]
    LOOT_KW = ["훔치", "습득", "상자", "찾다", "탐색"]
    ATTACK_KW = ["공격", "죽", "찔", "타격", "팬다", "좆", "썅"]
    INVEST_KW = ["조사", "살펴", "확인", "검사"]

    # Prefer kinds: item > stat > monster (for rewards)
    try:
        if any(k in act for k in HELP_KW + INVEST_KW):
            # stat buff
            return _to_client_payload(pick_random_reward(kind="stat"))
        if any(k in act for k in TRADE_KW + LOOT_KW):
            # drop item preferred
            return _to_client_payload(pick_random_reward(kind="item"))
        if any(k in act for k in ATTACK_KW):
            # attacking may yield items (loot) first, then stat
            item = pick_random_reward(kind="item")
            if item:
                return _to_client_payload(item)
            return _to_client_payload(pick_random_reward(kind="stat"))

        # default: prefer item, fallback to stat
        item = pick_random_reward(kind="item")
        if item:
            return _to_client_payload(item)
        return _to_client_payload(pick_random_reward(kind="stat"))
    except Exception:
        return None


def select_best_penalty(
    raw: Any, action_text: str = "", scenario_text: str = ""
) -> Any:
    """Rule-based selection for penalty when explicit penalty absent.

    Returns client payload (may be list if multiple penalties applied).
    """
    act = (action_text or "").lower()

    HOSTILE_KW = ["파괴", "공격", "죽", "훔치", "도둑", "씨발", "개새끼", "좆", "썅"]
    CARELESS_KW = ["만지", "집어", "건드"]

    try:
        if any(k in act for k in HOSTILE_KW):
            # spawn monster + small stat down
            spawn = pick_random_penalty(kind="monster")
            stat = get_penalty_dict("hp_down_10")
            payloads = []
            if spawn:
                payloads.append(_to_client_payload(spawn))
            if stat:
                payloads.append(_to_client_payload(stat))
            return payloads if payloads else None
        if any(k in act for k in CARELESS_KW):
            # minor stat down
            return _to_client_payload(get_penalty_dict("hp_down_10"))

        # default: small stat down
        return _to_client_payload(get_penalty_dict("hp_down_10"))
    except Exception:
        return None


def parse_expected_outcome_to_choices(eo_text: str) -> List[Dict[str, Any]]:
    import re

    if not eo_text or not isinstance(eo_text, str):
        return []

    # Split into numbered or newline-separated candidate outcomes
    parts = re.split(r"\s*(?:\d+\)|\d+\.|\n\- )\s*", eo_text)
    choices: List[Dict[str, Any]] = []

    # token pattern for internal ids like drop_accessory_100, pen_spawn_monster_0, hp_down_10
    token_pat = re.compile(r"([A-Za-z0-9_]+(?:_[A-Za-z0-9_]+)*)")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # action label — prefer text before ':' or first sentence
        if ":" in part:
            action_label = part.split(":", 1)[0].strip()
        else:
            # first sentence ending with '.' or ')' or end
            m_sent = re.match(r"^(.{1,120}?)[\.|\)|$]", part)
            action_label = (
                m_sent.group(1).strip() if m_sent and m_sent.group(1) else part[:80]
            )

        reward_id = None
        penalty_id = None

        # 1) Look for explicit token patterns anywhere in the part
        tokens = token_pat.findall(part)
        # Heuristic classification of tokens
        for t in tokens:
            tl = t.lower()
            # skip generic Korean words captured by token_pat by requiring underscore or known prefixes
            if not (
                "_" in tl
                or tl.startswith("drop")
                or tl.startswith("pen")
                or tl.startswith("hp")
                or tl.startswith("atk")
                or tl.startswith("spawn")
            ):
                continue

            if (
                any(
                    k in tl
                    for k in (
                        "cursed",
                        "curse",
                        "pen_",
                        "penalty",
                        "hp_down",
                        "down",
                        "atk_down",
                        "spawn_pen",
                        "pen_spawn",
                    )
                )
                or tl.startswith("pen_")
                or tl.startswith("penalty_")
            ):
                if penalty_id is None:
                    penalty_id = t
            elif (
                any(
                    k in tl
                    for k in (
                        "drop_",
                        "dropaccessory",
                        "dropweapon",
                        "drop_item",
                        "drop",
                        "spawn",
                        "drop_accessory",
                        "drop_weapon",
                    )
                )
                or tl.startswith("drop_")
                or tl.startswith("spawn_")
            ):
                if reward_id is None:
                    reward_id = t
            else:
                # fallback: treat as reward first
                if reward_id is None:
                    reward_id = t

        # 2) If no explicit tokens, try to identify text markers indicating reward/penalty
        if reward_id is None and penalty_id is None:
            low = part.lower()
            # simple keyword heuristics
            if any(
                k in low
                for k in ("획득", "획득 가능", "드랍", "얻", "보상", "획득함", "획득할")
            ):
                # mark as generic reward placeholder
                reward_id = "drop_item_unknown"
            if any(
                k in low
                for k in (
                    "저주",
                    "감염",
                    "hp -",
                    "hp -10",
                    "피해",
                    "피해를",
                    "패널티",
                    "벌",
                )
            ):
                penalty_id = penalty_id or "hp_down_10"

        choices.append(
            {
                "action": action_label or f"선택지 {len(choices) + 1}",
                "reward_id": reward_id,
                "penalty_id": penalty_id,
            }
        )

    return choices
