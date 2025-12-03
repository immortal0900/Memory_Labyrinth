
# Fairy API Documentation

정령(Fairy) 에이전트와 관련된 API 명세서입니다. 던전 내 상호작용 및 대화, 길드 내 대화를 처리합니다.

- **Base URL**: `/api/fairy`

## 1. 던전 (Dungeon)

** 주의사항 (Usage Note)**
> `/api/fairy/dungeon/talk`와 `/api/fairy/dungeon/interaction` API는 **반드시 함께 호출**되어야 합니다.  
> 하나의 사용자 입력에 대해 대화 응답(Talk)과 게임 내 행동(Interaction)을 각각 병렬로 처리하여 결과를 클라이언트에 반영해야 합니다.

### 1-1. 정령 - 던전 대화 (Talk)

던전 탐험 중 플레이어와 정령 간의 대화를 처리합니다.

- **Endpoint**: `POST /dungeon/talk`
- **Description**: 
  - 사용자의 질문에 대한 정령의 텍스트 응답을 반환합니다.
  - **성능 특이사항**:
    - **과거 회상/기억 관련 질문**: 응답 생성에 시간이 오래 걸릴 수 있습니다 (Latency High).
    - **일반/현재 상황 질문**: 응답 속도가 매우 빠릅니다 (Latency Low).

### 요청 방식 (Body)

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `dungeonPlayer` | Object | Yes | (통신 프로토콜 기준) 던전 플레이어의 실시간 상태 데이터 |
| `question` | String | Yes | 사용자의 질문 (예: "현재 방의 불 좀 켜줘") |
| `targetMonsterIds` | List[int] | No | 히로인 시야에 있는 몬스터 ID 목록 (기본값: `[]`) |
| `nextRoomId` | Integer | Yes | 히로인이 이동해야 할 다음 방 ID |

```json
{
  "dungeonPlayer": {
    "playerId": 1,
    "hp": 100,
    "currentRoomId": 5,
    "status": "normal"
  },
  "question": "방에 불좀 켜줘",
  "targetMonsterIds": [101, 102],
  "nextRoomId": 6
}
```

### 응답 방식 (Body)
| Field | Type | Description |
| :--- | :--- | :--- |
| `response_text` | String | 정령의 답변 텍스트 |
```json
{
  "response_text": "현재 던전의 불을 켜드리겠습니다. 방이 밝아졌어요!"
}
```

### 1-2. 정령 - 던전 인터렉션 (Interaction)

던전 탐험 중 사용자의 말에 따른 게임 시스템적 행동(불 켜기, 아이템 사용 등)을 판단합니다.

- **Endpoint**: `POST /dungeon/interaction`
- **Description**: 정령이 수행해야 할 게임 내 행동을 반환합니다. 대화 API와 함께 호출하여 행동을 동기화해야 합니다.

#### 요청 방식 (Body)

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `dungeonPlayer` | Object | Yes | (통신 프로토콜 기준) 던전 플레이어의 실시간 상태 데이터 |
| `question` | String | Yes | 사용자의 질문 |

```json
{
  "dungeonPlayer": {
    "playerId": 1,
    "currentRoomId": 5
  },
  "question": "여기 너무 어두워, 불 좀 켜줘"
}
```

#### 응답 방식 (Body)

| Field | Type | Description |
| :--- | :--- | :--- |
| `roomLight` | Boolean (Optional) | 방 밝기 조절 여부 (`true`: 켜기, `false`: 끄기, `null`: 행동 없음) |
| `isCheckNextRoom` | Boolean | 다음 방 확인 필요 여부 (정령 행동 필요 없으면 `false`) |
| `useItemId` | Integer (Optional) | 사용할 아이템의 ID (`null`: 사용 안 함) |

```json
{
  "roomLight": true,
  "isCheckNextRoom": false,
  "useItemId": null
}
```

## 2. 길드 (Guild)

### 정령 - 길드 대화

길드(로비/거점)에서 히로인과 나누는 일상 대화를 처리합니다.

- **Endpoint**: `POST /guild/talk`
- **Description**: 히로인의 호감도, 정신력, 기억 해금 상태를 반영하여 대화를 생성합니다.

#### 요청 방식 (Body)

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `playerId` | Integer | Yes | 사용자 ID |
| `heroine_id` | Integer | Yes | 대화 대상 히로인 ID |
| `memory_progress` | Integer | Yes | 히로인 기억 해금 진척도 |
| `affection` | Integer | Yes | 히로인 호감도 수치 |
| `sanity` | Integer | Yes | 히로인 정신력 수치 |
| `question` | String | Yes | 사용자의 질문 |
```json
{
  "playerId": 1001,
  "heroine_id": 1,
  "memory_progress": 50,
  "affection": 85,
  "sanity": 90,
  "question": "오늘 기분은 좀 어때?"
}
```
#### 응답 방식 (Body)

| Field | Type | Description |
| :--- | :--- | :--- |
| `response_text` | String | 히로인의 답변 텍스트 |

**Example JSON:**
```json
{
  "response_text": "덕분에 기분이 아주 좋아요! 오늘 임무도 같이 힘내요."
}
