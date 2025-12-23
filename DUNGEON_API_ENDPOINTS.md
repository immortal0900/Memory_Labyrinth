# 던전 API 명세서

## 1. 던전 입장
- **Endpoint:** `POST /api/dungeon/entrance`
- **Request Body:**
  - `playerIds` (List[str]): 플레이어 ID 목록
  - `heroineIds` (List[int]): 히로인 ID 목록
  - `heroineData` (Optional[List[Any]]): 히로인 데이터 (진행도 등)
  - `rawMaps` (List[RawMapRequest]): 각 층의 raw_map 정보
  - `usedEvents` (Optional[List[Any]]): 사용된 이벤트 목록
- **Response:**
  - `success` (bool)
  - `playerIds` (List[str])
  - `events` (Optional[List[EventResponse]])

- **Request Body 예시**
```json
{
  "playerIds": ["TEST0", "TEST1"],
  "heroineIds": [1, 1],
  "heroineData": [10, 50],
  "rawMaps": [
    {
      "floor": 1,
      "rooms": [ ... ],
      "rewards": [ ... ]
    },
    {
      "floor": 2,
      "rooms": [ ... ],
      "rewards": [ ... ]
    }
  ],
  "usedEvents": []
}
```
- **Response Body 예시**
```json
{
    "success": true,
    "playerIds": [
        "TEST0",
        "TEST1"
    ],
    "events": [
        {
            "roomId": 2,
            "eventType": 6,
            "eventTitle": "...",
            "scenarioText": "...",
            "scenarioNarrative": {
                "yoonjae22222": "...",
                "yoonjae11111": "..."
            } // 개별 이벤트 시, 두 히로인이 다르게 나옵니다. 공통이벤트에는 하나.
        }
    ]
}
```


---

## 2. 던전 밸런싱
- **Endpoint:** `POST /api/dungeon/balance`
- **Request Body:**
  - `firstPlayerId` (str): 방장 ID
  - `playerDataList` (List[PlayerBalanceData]): 플레이어별 밸런싱 데이터
  - `usedEvents` (Optional[List[Any]]): 사용된 이벤트 목록
- **Response:**
  - `success` (bool)
  - `firstPlayerId` (str)
  - `monsterPlacements` (List[MonsterPlacement])
  - `agentResult` (Optional[Any])


- **Request Body 예시**
```json
{
  "firstPlayerId": "TEST0",
  "playerDataList": [
    {
      "playerId": "TEST0",
      "heroineData": {
        "heroineId": 1,
        "affection": 10,
        "memoryProgress": 10,
        "scenarioLevel": 3,
        "heroineStat": {
          "hp": 100,
          "moveSpeed": 1,
          "attackSpeed": 1,
          "cooldownReduction": 0,
          "critChance": 0,
          "autoAttackMultiplier": 0,
          "skillDamageMultiplier": 0,
          "strength": 10,
          "dexterity": 10,
          "intelligence": 10
        },
        "weaponId" : 20,
        "skillIds": [2,3,1]
      }
    },
    {
      "playerId": "TEST1",
      "heroineData": {
        "heroineId": 2,
        "affection": 17,
        "memoryProgress": 50,
        "scenarioLevel": 2,
        "heroineStat": {
          "hp": 100,
          "moveSpeed": 1,
          "attackSpeed": 1,
          "cooldownReduction": 0,
          "critChance": 0,
          "autoAttackMultiplier": 0,
          "skillDamageMultiplier": 0,
          "strength": 22,
          "dexterity": 11,
          "intelligence": 8
        },
        "weaponId" : 20,
        "skillIds": [2,3,0]
      }
    }
  ],
  "usedEvents": []
}

```
- **Response Body 예시**
```json
{
    "success": true,
    "firstPlayerId": "TEST0",
    "monsterPlacements": [
        {
            "roomId": 1,
            "monsterIds": [
                2
            ]
        },
        {
            "roomId": 2,
            "monsterIds": [
                1,
                1,
                0
            ]
        },
        {
            "roomId": 4,
            "monsterIds": [
                1000
            ]
        }
    ]
}
```

---

## 3. 층 완료
- **Endpoint:** `PUT /api/dungeon/clear`
- **Request Body:**
  - `playerIds` (List[str]): 플레이어 ID 목록
- **Response:**
  - `success` (bool)
  - `finishedFloor` (Optional[int]): 완료된 층 번호


- **Request Body 예시**
```json
{
  "playerIds": ["TEST0", "TEST1"]
}
```
- **Response Body 예시**
```json
{
    "success": true,
    "message": "1층 완료",
    "finishedFloor": 1
}
```


---

## 4. 이벤트 선택
- **Endpoint:** `POST /api/dungeon/event/select`
- **Request Body:**
  - `firstPlayerId` (str): 방장 ID
  - `selectingPlayerId` (str): 선택한 플레이어 ID
  - `roomId` (int): 방 ID
  - `choice` (str): 선택지
- **Response:**
  - `success` (bool)
  - `firstPlayerId` (str)
  - `selectingPlayerId` (str)
  - `roomId` (int)
  - `outcome` (str)
  - `rewardId` (Optional[Any])
  - `penaltyId` (Optional[Any])


- **Request Body 예시**
```json
{
"firstPlayerId": "TEST0",
"selectingPlayerId": "TEST0",
"roomId": 2,
"choice": "무시한다"
}
```
- **Response Body 예시**
```json
{
    "success": true,
    "firstPlayerId": "TEST0",
    "selectingPlayerId": "TEST0",
    "roomId": 2,
    "outcome": "...",
    "rewardId": {
        "stat": {
            "name": "hp",
            "value": 20,
            "duration": 0
        }
    },
    "penaltyId": {
        "stat": {
            "name": "hp",
            "value": -10,
            "duration": 0
        }
    }
}
```


---

## 5. 다음 층 입장
- **Endpoint:** `POST /api/dungeon/nextfloor`
- **Request Body:**
  - `playerIds` (List[str]): 플레이어 ID 목록
  - `heroineIds` (List[int]): 히로인 ID 목록
  - `heroineData` (Optional[List[Any]]): 히로인 데이터
  - `rawMap` (RawMapRequest): 다음 층 raw_map 정보
  - `usedEvents` (Optional[List[Any]]): 사용된 이벤트 목록
- **Response:**
  - `success` (bool)
  - `playerIds` (List[str])
  - `events` (Optional[List[EventResponse]])




- **Request Body 예시**
```json
{
    "playerIds": ["TEST0", "TEST1"],
    "heroineIds": [1, 2],
    "heroineData": [10, 50],
    "rawMap": 
    {
      "floor": 3,
      "rooms": [
        {
          "roomId": 0,
          "type": 0,
          "size": 4,
          "neighbors": [1],
          "monsters": [],
          "eventType": 0
        },
        {
          "roomId": 1,
          "type": 1,
          "size": 10,
          "neighbors": [2, 0],
          "monsters": [
            {"monsterId": 3, "posX": 0.74515354633331299, "posY": 0.68286144733428955},
            {"monsterId": 4, "posX": 0.94996154308319092, "posY": 0.33496296405792236},
            {"monsterId": 0, "posX": 0.023660063743591309, "posY": 0.85452032089233398}
          ],
          "eventType": 0
        },
        {
          "roomId": 2,
          "type": 2,
          "size": 8,
          "neighbors": [1, 3],
          "monsters": [],
          "eventType": 1
        },
        {
          "roomId": 3,
          "type": 1,
          "size": 8,
          "neighbors": [4, 2],
          "monsters": [
            {"monsterId": 3, "posX": 0.86954891681671143, "posY": 0.28466427326202393},
            {"monsterId": 2, "posX": 0.54249989986419678, "posY": 0.89185011386871338},
            {"monsterId": 0, "posX": 0.30901765823364258, "posY": 0.014132380485534668},
            {"monsterId": 3, "posX": 0.35072934627532959, "posY": 0.18600237369537354},
            {"monsterId": 0, "posX": 0.24587619304656982, "posY": 0.60887575149536133},
            {"monsterId": 3, "posX": 0.56324088573455811, "posY": 0.41939854621887207},
            {"monsterId": 0, "posX": 0.25108706951141357, "posY": 0.72293758392333984},
            {"monsterId": 1, "posX": 0.99383068084716797, "posY": 0.88348150253295898}
          ],
          "eventType": 0
        },
        {
          "roomId": 4,
          "type": 4,
          "size": 12,
          "neighbors": [3],
          "monsters": [],
          "eventType": 0
        }
      ],
      "rewards": []
    }
}

```
- **Response Body 예시**
```json
{
    "success": true,
    "playerIds": [
        "TEST0",
        "TEST1"
    ],
    "events": [
        {
            "roomId": 3,
            "eventType": 1,
            "eventTitle": "...",
            "scenarioText": "...",
            "scenarioNarrative": "..."
        }
    ]
}
```

---

## 참고 사항
- 모든 엔드포인트는 JSON 형식의 요청/응답을 사용합니다.
- 각 엔드포인트의 상세 동작 및 데이터 구조는 실제 구현에 따라 확장될 수 있습니다.
