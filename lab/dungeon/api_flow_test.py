import requests
import json
import sys
import os

# Add project root to path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

BASE_URL = "http://127.0.0.1:8000/api/dungeon"


def print_step(step_name):
    print(f"\n{'='*20} {step_name} {'='*20}")


def test_entrance():
    print_step("1. Entrance (던전 입장)")

    # Mock Raw Map (Unreal)
    raw_map = {
        "playerIds": [0, 1],
        "heroineIds": [1, 2],
        "rooms": [
            {"roomId": 0, "type": 0, "size": 1, "neighbors": [1]},  # Start
            {"roomId": 1, "type": 1, "size": 1, "neighbors": [0, 2]},  # Monster
            {"roomId": 2, "type": 2, "size": 1, "neighbors": [1, 3]},  # Event
            {"roomId": 3, "type": 4, "size": 1, "neighbors": [2]},  # Boss
        ],
        "rewards": [],
    }

    payload = {
        "rawMap": raw_map,
        "heroineData": {
            "heroine_id": 1,
            "name": "레티아",
            "event_room": 2,
            "memory_progress": 50,
        },
        "usedEvents": [],
    }

    try:
        response = requests.post(f"{BASE_URL}/entrance", json=payload)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception as e:
        print(f"Entrance Failed: {e}")
        if hasattr(e, "response") and e.response:
            print(e.response.text)
        return None


def test_balance(first_player_id):
    print_step("2. Balance (밸런싱)")

    payload = {
        "firstPlayerId": first_player_id,
        "heroineData": {
            "heroine_id": 1,
            "name": "레티아",
            "event_room": 2,
            "memory_progress": 50,
        },
        "heroineStat": {
            "hp": 100,
            "strength": 10,
            "dexterity": 10,
            "attackSpeed": 1.0,
            "critChance": 5.0,
            "skillDamageMultiplier": 1.0,
        },
        "heroineMemories": [],
        "dungeonPlayerData": {"affection": 50, "sanity": 100, "difficulty_level": 1},
        "usedEvents": [],
    }

    try:
        response = requests.post(f"{BASE_URL}/balance", json=payload)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception as e:
        print(f"Balance Failed: {e}")
        if hasattr(e, "response") and e.response:
            print(e.response.text)
        return None


def test_clear(player_ids):
    print_step("3. Clear (층 완료)")

    payload = {"playerIds": player_ids}

    try:
        response = requests.put(f"{BASE_URL}/clear", json=payload)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception as e:
        print(f"Clear Failed: {e}")
        if hasattr(e, "response") and e.response:
            print(e.response.text)
        return None


def test_next(first_player_id):
    print_step("4. Next Floor (다음 층 준비)")

    payload = {
        "firstPlayerId": first_player_id,
        "heroineData": {
            "heroine_id": 1,
            "name": "레티아",
            "event_room": 2,
            "memory_progress": 50,
        },
        "usedEvents": [],
    }

    try:
        response = requests.post(f"{BASE_URL}/next", json=payload)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception as e:
        print(f"Next Floor Failed: {e}")
        if hasattr(e, "response") and e.response:
            print(e.response.text)
        return None


def test_event_select(first_player_id):
    print_step("5. Event Select (이벤트 선택)")

    payload = {
        "firstPlayerId": first_player_id,
        "selectingPlayerId": first_player_id,
        "roomId": 2,
        "choice": "조심스럽게 다가간다",
    }

    try:
        response = requests.post(f"{BASE_URL}/event/select", json=payload)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception as e:
        print(f"Event Select Failed: {e}")
        if hasattr(e, "response") and e.response:
            print(e.response.text)
        return None


if __name__ == "__main__":
    # 1. Entrance
    entrance_res = test_entrance()
    if not entrance_res:
        sys.exit(1)

    first_player_id = entrance_res["firstPlayerId"]

    # 2. Balance
    balance_res = test_balance(first_player_id)

    # 3. Clear
    test_clear([first_player_id, 1])

    # 4. Next Floor
    test_next(first_player_id)

    # 5. Event Select
    test_event_select(first_player_id)
