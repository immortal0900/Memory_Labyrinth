import sys
from pathlib import Path
import json
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.dungeon_service import DungeonService


async def test_entrance_logic():
    service = DungeonService()

    # Dummy data from user request
    raw_map = {
        "playerIds": [1],
        "heroineIds": [1],
        "rooms": [
            {
                "roomId": 0,
                "type": 0,
                "size": 4,
                "neighbors": [1],
                "monsters": [],
                "eventType": 0,
            },
            {
                "roomId": 1,
                "type": 2,
                "size": 8,
                "neighbors": [2, 0],
                "monsters": [],
                "eventType": 2,
            },
            {
                "roomId": 2,
                "type": 1,
                "size": 6,
                "neighbors": [1, 4],
                "monsters": [
                    {
                        "monsterId": 0,
                        "posX": 0.071239590644836426,
                        "posY": 0.49437010288238525,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.64459884166717529,
                        "posY": 0.63561642169952393,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.3811793327331543,
                        "posY": 0.9721304178237915,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.557853102684021,
                        "posY": 0.66655290126800537,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.83782792091369629,
                        "posY": 0.44205427169799805,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.83236396312713623,
                        "posY": 0.7380518913269043,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.74639761447906494,
                        "posY": 0.73493218421936035,
                    },
                    {
                        "monsterId": 0,
                        "posX": 0.44071531295776367,
                        "posY": 0.50277876853942871,
                    },
                ],
                "eventType": 0,
            },
            {
                "roomId": 3,
                "type": 2,
                "size": 8,
                "neighbors": [4],
                "monsters": [],
                "eventType": 2,
            },
            {
                "roomId": 4,
                "type": 4,
                "size": 12,
                "neighbors": [2, 3],
                "monsters": [],
                "eventType": 0,
            },
        ],
        "rewards": [],
    }

    heroine_data = {
        "playerId": 0,
        "heroineId": 0,
        "memoryProgress": 0,
        "heroineStat": {
            "hp": 0,
            "atk": 0,
            "def": 0,
            "spd": 0,
            "strength": 0,
            "dexterity": 0,
            "intelligence": 0,
        },
        "heroineMemories": [],
        "dungeonPlayerData": {"level": 0, "exp": 0},
    }

    print("Testing Entrance...")
    try:
        result = service.entrance(
            player_ids=[1],
            heroine_ids=[1],
            raw_map=raw_map,
            heroine_data=heroine_data,
            used_events=[],
        )

        print("Entrance Result:")
        events = result.get("events", [])
        print(f"Generated Events Count: {len(events)}")
        for evt in events:
            print(
                f" - Room ID: {evt.get('room_id')}, Type: {evt.get('event_type')}, Title: {evt.get('event_title')}"
            )

        # Verify Room 1 and 3 have events
        room_ids = [evt.get("room_id") for evt in events]
        if 1 in room_ids and 3 in room_ids:
            print("SUCCESS: Events generated for Room 1 and 3.")
        else:
            print(f"FAILURE: Expected events in Room 1 and 3, but got {room_ids}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_entrance_logic())
