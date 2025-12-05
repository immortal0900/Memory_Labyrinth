test = {
    "rawMap": {
        "playerIds": [0],
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
                "size": 4,
                "neighbors": [0, 2],
                "monsters": [],
                "eventType": 0,
            },
            {
                "roomId": 2,
                "type": 1,
                "size": 10,
                "neighbors": [3, 1],
                "monsters": [{"monsterId": 0, "posX": 0.5, "posY": 8.5}],
                "eventType": 1,
            },
            {
                "roomId": 3,
                "type": 1,
                "size": 12,
                "neighbors": [4, 2],
                "monsters": [{"monsterId": 0, "posX": 10.5, "posY": 14.5}],
                "eventType": 2,
            },
            {
                "roomId": 4,
                "type": 4,
                "size": 12,
                "neighbors": [3],
                "monsters": [],
                "eventType": 0,
            },
        ],
        "rewards": [],
    }
}


test2 = {
    "dungeonId": 1,
    "heroineData": {
        "heroine_id": "1",
        "name": "레티아",
        "event_room": 3,
        "memory_progress": 50,
    },
    "heroineStat": {
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
    "dungeonPlayerData": {"affection": 50, "sanity": 80, "difficulty_level": "normal"},
}
