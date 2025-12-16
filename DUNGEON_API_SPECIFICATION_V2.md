# Dungeon API Specification V2 (Unreal Engine Integration)

## Base URL
`http://<server_ip>:8090/api/dungeon`

---

## 1. 던전 입장 (1층 생성)
**Endpoint:** `POST /entrance`
**Description:** 플레이어가 던전(1층)에 입장할 때 호출됩니다. 던전 세션을 초기화하고, 참여하는 플레이어들의 이전 미완료 세션을 정리하며, 제공된 맵 구조를 기반으로 1층,2층 이벤트를 생성합니다.

### Request Body (`application/json`)

| 필드명        | 타입    | 필수 | 설명                                 |
| :------------ | :------ | :--- | :----------------------------------- |
| `playerIds`   | Array   | Yes  | 참여 플레이어 ID 목록                |
| `heroineIds`  | Array   | Yes  | 참여 히로인 ID 목록                  |
| `heroineData` | Array   | No   | 히로인별 상태 정보(리스트, 각 히로인 1개 객체) |
| `rawMaps`     | Array   | Yes  | 각 층의 맵 구조 데이터 (방 정보만 포함) |
| `usedEvents`  | Array   | No   | 이전에 사용된 이벤트 ID 목록 (중복 방지용) |

```json
{
  "playerIds": [220, 221],
  "heroineIds": [1, 1],
  "heroineData": [
    { "heroineId": 1, "memoryProgress": 0 },
    { "heroineId": 1, "memoryProgress": 0 }
  ],
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
- floor: 각 층의 고유 번호(1, 2, ...). 각 rawMaps 항목에 반드시 포함되어야 함.
- heroineData: 여러 히로인 지원. 각 히로인별로 객체 1개씩 리스트로 전달.
- playerIds, heroineIds: 최상위에서 한 번만 전달, 각 층에 자동 반영됨.
- rawMaps 내부에는 방 정보(rooms, rewards 등)만 포함, playerIds/heroineIds는 포함하지 않음.


### Response Body (`application/json`)

| 필드명                | 타입      | 설명                                 |
| :-------------------- | :-------- | :----------------------------------- |
| `success`             | Boolean   | 요청 처리 성공 여부                  |
| `message`             | String    | 결과 메시지                          |
| `firstPlayerId`       | Integer   | 방장(Host) 플레이어 ID (세션 키)     |
| `playerIds`           | Array     | 참여 플레이어 ID 목록                |
| `heroineIds`          | Array     | 참여 히로인 ID 목록                  |
| `heroineMemoryProgress` | Array   | 각 히로인별 memoryProgress 값        |
| `events`              | Array     | 생성된 이벤트 목록                   |

```json
{
  "success": true,
  "message": "던전 입장 성공",
  "firstPlayerId": 1,
  "playerIds": [101, 102],
  "heroineIds": [1, 2],
  "heroineMemoryProgress": [50, 30],
  "events": [
    {
      "roomId": 1,
      "eventType": 4,
      "eventTitle": "미치광이 상인",
      "eventCode": "MAD_MERCHANT",
      "scenarioText": "장면 묘사 텍스트...",
      "scenarioNarrative": "UI 표시용 서술 텍스트...",
      "choices": [
        {
          "action": "말을 건다",
          "reward": { "id": "item_common", "desc": "일반 아이템" },
          "penalty": null
        },
        {
          "action": "공격한다",
          "reward": { "id": "item_rare", "desc": "희귀 아이템" },
          "penalty": { "id": "hp_damage", "desc": "HP 감소" }
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

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| `firstPlayerId` | Integer | Yes | 방장(Host) 플레이어 ID |
| `playerDataList` | Array | Yes | 각 플레이어들의 현재 상태 정보(각 항목에 heroineData 포함) |
| `usedEvents` | Array | No | (선택)이전에 사용된 이벤트 ID 목록 |

```json
{
  "firstPlayerId": 101,
  "playerDataList": [
    {
      "heroineData": {
        "playerId": 101,
        "heroineId": 1,
        "memoryProgress": 50,
        "scenarioLevel": 3,
        "heroineStat": { ... },
        "dungeonPlayerData": { ... }
      }
    },
    {
      "heroineData": {
        "playerId": 102,
        "heroineId": 2,
        "memoryProgress": 30,
        "scenarioLevel": 2,
        "heroineStat": { ... },
        "dungeonPlayerData": { ... }
      }
    }
  ],
  "usedEvents": []
}
```

### Response Body (`application/json`)

| 필드명            | 타입    | 설명                                 |
| :---------------- | :------ | :----------------------------------- |
| `success`         | Boolean | 요청 처리 성공 여부                  |
| `message`         | String  | 결과 메시지                          |
| `firstPlayerId`   | Integer | 방장(Host) 플레이어 ID               |
| `monsterPlacements` | Array | 다음 층에 배치될 몬스터 정보 목록    |
| `nextFloorEvent`  | Object  | 다음 층을 위해 생성된 이벤트 정보    |
| `agentResult`     | Object  | (디버깅용) AI 분석 결과              |

```json
{
  "success": true,
  "message": "던전 밸런싱 성공",
  "firstPlayerId": 1,
  "monsterPlacements": [
    { "roomId": 4, "monsterId": 101, "count": 1 }
  ],
  "nextFloorEvent": {
    "roomId": 3,
    "eventType": 5,
    "eventTitle": "미지의 기억",
    "eventCode": "UNKNOWN_MEMORY",
    "scenarioText": "...",
    "scenarioNarrative": "..."
  },
  "agentResult": { /* AI 분석 결과 */ }
}
```

---

## 3. 층 클리어 (상태 업데이트)
**Endpoint:** `PUT /clear`
**Description:** 플레이어가 현재 층을 클리어(보스 처치)했을 때 호출됩니다. 현재 층을 "종료 중(`is_finishing = true`)" 상태로 표시하여, 클라이언트가 다음 층의 맵 생성을 요청할 수 있도록 합니다.

### Request Body (`application/json`)

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| `playerIds` | Array | Yes | 층을 클리어한 플레이어 ID 목록 |

```json
{
  "playerIds": [1] // 방장만      // 층을 클리어한 플레이어 ID 목록
}
```

### Response Body (`application/json`)

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `success` | Boolean | 요청 처리 성공 여부 |
| `message` | String | 결과 메시지 |
| `finishedFloor` | Integer | 완료된 층 번호 |

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
**Description:** 플레이어가 이벤트 방에서 선택지를 골랐을 때 호출됩니다. 사용자의 입력(텍스트)을 분석하여 가장 유사한 선택지의 보상/패널티를 적용하거나, 돌발 행동을 감지합니다.

### Request Body (`application/json`)

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| `firstPlayerId` | Integer | Yes | 방장(Host) 플레이어 ID |
| `selectingPlayerId` | Integer | Yes | 선택을 한 플레이어 ID |
| `roomId` | Integer | Yes | 이벤트가 발생한 방 ID |
| `choice` | String | Yes | 선택한 선택지의 텍스트 (자유 입력 가능) |

```json
{
  "firstPlayerId": 1,       // 방장(Host) 플레이어 ID
  "selectingPlayerId": 1,   // 선택을 한 플레이어 ID
  "roomId": 1,              // 이벤트가 발생한 방 ID
  "choice": "상인을 공격한다" // 선택한 선택지의 텍스트 (자유 입력 가능)
}
```

### Response Body (`application/json`)

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| `success` | Boolean | 요청 처리 성공 여부 |
| `firstPlayerId` | Integer | 방장(Host) 플레이어 ID |
| `selectingPlayerId` | Integer | 선택을 한 플레이어 ID |
| `roomId` | Integer | 이벤트가 발생한 방 ID |
| `outcome` | String | LLM이 생성한 결과 서술 |
| `rewardId` | String | 획득한 보상 ID (없으면 null) |
| `penaltyId` | String | 적용된 패널티 ID (없으면 null) |
| `isUnexpected` | Boolean | 돌발 행동 여부 |

```json
{
  "success": true,
  "firstPlayerId": 1,
  "selectingPlayerId": 1,
  "roomId": 1,
  "outcome": "상인이 회피하고 반격합니다! 10의 피해를 입었습니다.",
  "rewardId": "item_rare",
  "penaltyId": "hp_damage"
}
```
---
## 5. 다음 층 입장
**Endpoint:** `POST /nextfloor`
**Description:** 플레이어가 다음 층을 입장할 때 호출됩니다. 예를 들어, 1층을 클리어한 후, 2층으로 입장할 시, 3층의 raw_map 정보를 받아 밸런스를 진행하고 3층의 event를 반환해줍니다.

### Request Body (`application/json`)

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| `rawMap` | Object | Yes | 언리얼에서 생성한 맵 구조 데이터 |
| `heroineData` | Object | Yes | 히로인별 상태 정보(리스트, 각 히로인 1개 객체) |
| `usedEvents` | Array | No | (선택)이전에 사용된 이벤트 ID 목록 |

```json
{
  "rawMap": {
    "floor": 3, // 이때, floor 가 반드시 포함되어야 합니다.
    "playerIds": [101, 102],
    "heroineIds": [1, 2],
    "rooms": [ ... ],
    "rewards": [ ... ]
  },
  "heroineData": [
    { "heroineId": 1, "memoryProgress": 50 },
    { "heroineId": 2, "memoryProgress": 30 }
  ],
  "usedEvents": []
}
```

### Response Body (`application/json`)

| 필드명                | 타입      | 설명                                 |
| :-------------------- | :-------- | :----------------------------------- |
| `success`             | Boolean   | 요청 처리 성공 여부                  |
| `message`             | String    | 결과 메시지                          |
| `floorId`             | Integer   | 생성될 층 id                         |
| `playerIds`           | Array     | 참여 플레이어 ID 목록                |
| `heroineIds`          | Array     | 참여 히로인 ID 목록                  |
| `heroineMemoryProgress` | Array   | 각 히로인별 memoryProgress 값        |
| `events`              | Array     | 생성된 이벤트 목록                   |

```json
{
  "success": true,
  "message": "다음 층 입장 및 이벤트 생성 성공",
  "floorId": 3,
  "playerIds": [101, 102],
  "heroineIds": [1, 2],
  "heroineMemoryProgress": [50, 30],
  "events": [
    {
      "roomId": 5,
      "eventType": 2,
      "eventTitle": "수상한 방",
      "eventCode": "SUSPICIOUS_ROOM",
      "scenarioText": "방 안이 어둡고 조용하다...",
      "scenarioNarrative": "UI 표시용 서술 텍스트...",
      "choices": [
        {
          "action": "탐색한다",
          "reward": { "id": "item_key", "desc": "열쇠" },
          "penalty": null
        }
      ]
    }
  ]
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
