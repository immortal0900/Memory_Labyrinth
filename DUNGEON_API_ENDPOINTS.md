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
  - `message` (str)
  - `playerIds` (List[str])
  - `events` (Optional[List[EventResponse]])

---

## 2. 던전 밸런싱
- **Endpoint:** `POST /api/dungeon/balance`
- **Request Body:**
  - `firstPlayerId` (str): 방장 ID
  - `playerDataList` (List[PlayerBalanceData]): 플레이어별 밸런싱 데이터
  - `usedEvents` (Optional[List[Any]]): 사용된 이벤트 목록
- **Response:**
  - `success` (bool)
  - `message` (str)
  - `firstPlayerId` (str)
  - `monsterPlacements` (List[MonsterPlacement])
  - `agentResult` (Optional[Any])

---

## 3. 층 완료
- **Endpoint:** `PUT /api/dungeon/clear`
- **Request Body:**
  - `playerIds` (List[str]): 플레이어 ID 목록
- **Response:**
  - `success` (bool)
  - `message` (str)
  - `finishedFloor` (Optional[int]): 완료된 층 번호

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
  - `message` (str)
  - `playerIds` (List[str])
  - `events` (Optional[List[EventResponse]])

---

## 6. 데이터 구조 예시

### RawMapRoom
```json
{
  "roomId": 1,
  "type": 2,
  "size": 3,
  "neighbors": [2,3],
  "monsters": [{"monsterId": 101, "count": 2}],
  "eventType": 1
}
```

### EventResponse
```json
{
  "roomId": 1,
  "eventType": 2,
  "eventTitle": "보물 발견",
  "scenarioText": "방 안에서 빛나는 상자를 발견했다.",
  "scenarioNarrative": "상자를 열면 보상을 획득합니다."
}
```

### MonsterPlacement
```json
{
  "roomId": 1,
  "monsterId": 101,
  "count": 2
}
```

---

## 7. 참고 사항
- 모든 엔드포인트는 JSON 형식의 요청/응답을 사용합니다.
- 각 엔드포인트의 상세 동작 및 데이터 구조는 실제 구현에 따라 확장될 수 있습니다.
- 오류 발생 시 HTTP 4xx/5xx 코드와 함께 상세 메시지가 반환됩니다.
