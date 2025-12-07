# Dungeon API Specification V2 (Unreal Engine Integration)

## Base URL
`http://<server_ip>:8090/api/dungeon`

---

## 1. 던전 입장 (1층 생성)
**Endpoint:** `POST /entrance`
**Description:** 플레이어가 던전(1층)에 입장할 때 호출됩니다. 던전 세션을 초기화하고, 참여하는 플레이어들의 이전 미완료 세션을 정리하며, 제공된 맵 구조를 기반으로 1층 이벤트를 생성합니다.

### Request Body (`application/json`)
```json
{
  "rawMap": {
    "playerIds": [1, 2],
    "heroineIds": [1, 1],
    "rooms": [
      {
        "roomId": 0,
        "type": 0,          // 0: 빈방, 1: 전투방, 2: 이벤트방, 3: 보물방, 4: 보스방
        "size": 4,
        "neighbors": [1],
        "monsters": [],
        "eventType": 0      // 0: 없음, >0: 언리얼에서 지정한 특정 이벤트 ID
      },
      {
        "roomId": 1,
        "type": 2,
        "size": 8,
        "neighbors": [0, 2],
        "monsters": [],
        "eventType": 2      // 예시: 이벤트 타입 2
      }
    ],
    "rewards": []
  },
  "heroineData": {          // 선택 사항
    "heroineId": 1,
    "memoryProgress": 0
  },
  "usedEvents": []          // 선택 사항: 이미 경험한 이벤트 ID 목록
}
```

### Response Body (`application/json`)
```json
{
  "success": true,
  "message": "던전 입장 성공",
  "firstPlayerId": 1,       // 방장(Host) 플레이어 ID (세션 키로 사용됨)
  "events": [
    {
      "roomId": 1,
      "eventType": 4,       // 생성된 이벤트 ID
      "eventTitle": "미치광이 상인",
      "eventCode": "MAD_MERCHANT",
      "scenarioText": "장면 묘사 텍스트...",
      "scenarioNarrative": "UI 표시용 서술 텍스트...",
      "choices": [
        {
          "action": "말을 건다",
          "rewardId": "item_common",
          "penaltyId": null
        },
        {
          "action": "공격한다",
          "rewardId": "item_rare",
          "penaltyId": "hp_damage"
        }
      ]
    }
  ]
}
```

---

## 2. 던전 밸런싱 (보스방 / 다음 층 준비)
**Endpoint:** `POST /balance`
**Description:** 플레이어가 현재 층의 보스방에 입장할 때 호출됩니다. **다음 층**의 밸런싱(몬스터, 난이도)을 수행하고 다음 층의 이벤트를 생성합니다.

### Request Body (`application/json`)
```json
{
  "firstPlayerId": 1,       // 방장(Host) 플레이어 ID
  "playerDataList": [
    {
      "heroineData": {
        "playerId": 1,
        "heroineStat": { "str": 10, "int": 5 },
        "heroineMemories": [],
        "dungeonPlayerData": { "hp": 100, "level": 5 }
      }
    }
  ],
  "usedEvents": []
}
```

### Response Body (`application/json`)
```json
{
  "success": true,
  "message": "던전 밸런싱 성공",
  "firstPlayerId": 1,
  "monsterPlacements": [    // 다음 층에 스폰될 몬스터 정보 (또는 로직 변경 시 현재 보스방)
    {
      "roomId": 4,
      "monsterId": 101,
      "count": 1
    }
  ],
  "nextFloorEvent": {       // 다음 층을 위해 생성된 이벤트
    "roomId": 3,
    "eventType": 5,
    "eventTitle": "미지의 기억",
    "eventCode": "UNKNOWN_MEMORY",
    "scenarioText": "...",
    "scenarioNarrative": "..."
  }
}
```

---

## 3. 층 클리어 (상태 업데이트)
**Endpoint:** `PUT /clear`
**Description:** 플레이어가 현재 층을 클리어(보스 처치)했을 때 호출됩니다. 현재 층을 "종료 중(`is_finishing = true`)" 상태로 표시하여, 클라이언트가 다음 층의 맵 생성을 요청할 수 있도록 합니다.

### Request Body (`application/json`)
```json
{
  "playerIds": [1, 2]       // 층을 클리어한 플레이어 ID 목록
}
```

### Response Body (`application/json`)
```json
{
  "success": true,
  "message": "1층 완료",
  "finishedFloor": 1
}
```
*참고: 제공된 `playerIds` 중 **한 명이라도** 활성 던전에 포함되어 있으면 해당 세션을 식별합니다.*

---

## 4. 이벤트 선택
**Endpoint:** `POST /event/select`
**Description:** 플레이어가 이벤트 방에서 선택지를 골랐을 때 호출됩니다.

### Request Body (`application/json`)
```json
{
  "firstPlayerId": 1,       // 방장(Host) 플레이어 ID
  "selectingPlayerId": 1,   // 선택을 한 플레이어 ID
  "roomId": 1,              // 이벤트가 발생한 방 ID
  "choice": "상인을 공격한다" // 선택한 선택지의 텍스트
}
```

### Response Body (`application/json`)
```json
{
  "success": true,
  "firstPlayerId": 1,
  "selectingPlayerId": 1,
  "roomId": 1,
  "outcome": "상인이 회피하고 반격합니다! 10의 피해를 입었습니다." // LLM이 생성한 결과 서술
}
```

---

## 데이터 타입 및 열거형 (Enums)

### Room Types (Integer)
| 값 | 타입 | 설명 |
| :--- | :--- | :--- |
| 0 | Empty | 몬스터 없음, 이벤트 없음 |
| 1 | Monster | 일반 전투방 |
| 2 | Event | 서사적 이벤트 방 |
| 3 | Treasure | 보상 방 |
| 4 | Boss | 보스 전투방 |

### Event Types
- **0**: 이벤트 없음
- **>0**: 특정 이벤트 ID (내부적으로 이벤트 시나리오와 매핑됨)

### 참고 사항
- **세션 관리**: `firstPlayerId`(방장)는 던전 세션을 식별하는 기본 키(Primary Key) 역할을 합니다.
- **정리(Cleanup)**: `/entrance`를 호출하면 참여하는 모든 플레이어의 "좀비" 세션(미완료 던전)을 자동으로 정리하여 DB 잠금을 방지합니다.
