import sys
import os
import json
from typing import Dict, Any
from datetime import datetime

# Add project root to path
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_path)
sys.path.append(os.path.join(root_path, "src"))

from services.dungeon_service import get_dungeon_service
from agents.dungeon.monster.monster_database import MONSTER_DATABASE


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def print_step(step_name):
    print(f"\n{'='*20} {step_name} {'='*20}")


import random


def test_service_flow():
    service = get_dungeon_service()

    # Generate random player IDs to avoid conflict with existing data
    p1 = random.randint(10000, 99999)
    p2 = random.randint(10000, 99999)
    print(f"Testing with Player IDs: {p1}, {p2}")

    # 1. Entrance
    print_step("1. Entrance")
    raw_map = {
        "playerIds": [p1, p2],
        "heroineIds": [1, 2],
        "rooms": [
            {"roomId": 0, "type": 0, "size": 1, "neighbors": [1]},
            {"roomId": 1, "type": 1, "size": 1, "neighbors": [0, 2]},
            {"roomId": 2, "type": 2, "size": 1, "neighbors": [1, 3]},
            {"roomId": 3, "type": 4, "size": 1, "neighbors": [2]},
        ],
        "rewards": [],
    }

    entrance_res = service.entrance(
        player_ids=[p1, p2],
        heroine_ids=[1, 2],
        raw_map=raw_map,
        heroine_data={
            "heroine_id": 1,
            "name": "레티아",
            "event_room": 2,
            "memory_progress": 50,
        },
        used_events=[],
    )
    print(json.dumps(entrance_res, indent=2, ensure_ascii=False))

    first_player_id = entrance_res["first_player_id"]

    # 2. Balance (Triggered at Floor 1 Boss Room -> Generates Floor 2)
    print_step("2. Balance (Next Floor Generation)")
    balance_res = service.balance_dungeon(
        first_player_id=first_player_id,
        player_data_list=[
            {
                "heroineData": {
                    "playerId": first_player_id,
                    "heroine_id": 1,
                    "name": "레티아",
                    "event_room": 2,
                    "memory_progress": 50,
                    "heroineStat": {
                        "hp": 100,
                        "strength": 10,
                        "dexterity": 10,
                        "intelligence": 10,
                        "attackSpeed": 1.0,
                        "critChance": 5.0,
                        "skillDamageMultiplier": 1.0,
                    },
                    "heroineMemories": [],
                    "dungeonPlayerData": {"affection": 50, "sanity": 100, "difficulty_level": 1}
                }
            }
        ],
        monster_db=MONSTER_DATABASE,
    )
    print(json.dumps(balance_res, indent=2, ensure_ascii=False, default=json_serial))

    if "monster_placements" in balance_res:
        print("\n[Verified] monster_placements (for Next Floor) found:")
        print(json.dumps(balance_res["monster_placements"], indent=2, ensure_ascii=False))
    else:
        print("\n[FAILED] monster_placements NOT found")

    if "next_floor_event" in balance_res:
        print("\n[Verified] next_floor_event (for Next Floor) found:")
        print(json.dumps(balance_res["next_floor_event"], indent=2, ensure_ascii=False))
    else:
        print("\n[FAILED] next_floor_event NOT found")

    # 3. Clear
    print_step("3. Clear")
    clear_res = service.clear_floor(player_ids=[first_player_id, p2])
    print(json.dumps(clear_res, indent=2, ensure_ascii=False, default=json_serial))

    # 5. Event Select
    print_step("5. Event Select")
    select_res = service.select_event(
        first_player_id=first_player_id,
        selecting_player_id=first_player_id,
        room_id=2,
        choice="조심스럽게 다가간다",
    )
    print(json.dumps(select_res, indent=2, ensure_ascii=False, default=json_serial))


if __name__ == "__main__":
    try:
        test_service_flow()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback

        traceback.print_exc()
