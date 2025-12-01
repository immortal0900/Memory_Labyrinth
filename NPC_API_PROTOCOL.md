# NPC API 프로토콜 문서

언리얼 엔진과 NPC 시스템 간의 통신 프로토콜입니다.

**Base URL**: `http://localhost:8090`

---

## 목차

1. [로그인/세션](#1-로그인세션)
2. [히로인 대화](#2-히로인-대화)
3. [대현자 대화](#3-대현자-대화)
4. [히로인간 대화](#4-히로인간-대화)
5. [길드 시스템](#5-길드-시스템)
6. [스트리밍 응답 처리](#6-스트리밍-응답-처리)

---

## 1. 로그인/세션

### POST /api/npc/login

게임 접속시 **1번만** 호출합니다. 플레이어의 모든 NPC 세션을 초기화합니다.

#### Request

```json
{
    "playerId": 10001,
    "scenarioLevel": 3,
    "heroines": [
        {
            "heroineId": 1,
            "affection": 45,
            "memoryProgress": 30,
            "sanity": 80
        },
        {
            "heroineId": 2,
            "affection": 60,
            "memoryProgress": 50,
            "sanity": 100
        },
        {
            "heroineId": 3,
            "affection": 25,
            "memoryProgress": 20,
            "sanity": 90
        }
    ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| playerId | int | 플레이어 고유 ID |
| scenarioLevel | int | 현재 시나리오 레벨 (1-10) |
| heroines | array | 히로인들의 상태 배열 |
| heroines[].heroineId | int | 히로인 ID (1=레티아, 2=루파메스, 3=로코) |
| heroines[].affection | int | 호감도 (0-100) |
| heroines[].memoryProgress | int | 기억 진척도 (0-100) |
| heroines[].sanity | int | 정신력 (0-100) |

#### Response

```json
{
    "success": true,
    "message": "세션 초기화 완료"
}
```

---

## 2. 히로인 대화

> **스트리밍/비스트리밍 동일 응답**: 둘 다 동일한 컨텍스트(기억/시나리오 검색)를 사용하며, LLM은 1번만 호출됩니다.

### POST /api/npc/heroine/chat (스트리밍)

히로인과 대화합니다. **SSE(Server-Sent Events) 스트리밍**으로 응답합니다.

#### Request

```json
{
    "playerId": 10001,
    "heroineId": 1,
    "text": "안녕, 오늘 기분이 어때?"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| playerId | int | 플레이어 ID |
| heroineId | int | 대화할 히로인 ID |
| text | string | 플레이어 메시지 |

#### Response (SSE 스트리밍)

```
data: 안
data: 녕
data: ...
data: 별로야
data: .
data: {"type": "final", "affection": 50, "sanity": 85, "memoryProgress": 35, "emotion": "neutral"}
data: [DONE]
```

| 이벤트 | 설명 |
|--------|------|
| `data: {토큰}` | 응답 텍스트 (토큰 단위) |
| `data: {"type": "final", ...}` | 최종 상태 (JSON) |
| `data: [DONE]` | 스트리밍 종료 |

**최종 상태 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| type | string | 항상 "final" |
| affection | int | 변경된 호감도 |
| sanity | int | 변경된 정신력 |
| memoryProgress | int | 변경된 기억 진척도 |
| emotion | string | 현재 감정 |

---

### POST /api/npc/heroine/chat/sync (비스트리밍)

히로인과 대화합니다. **전체 응답을 한번에** 반환합니다.

#### Request

```json
{
    "playerId": 10001,
    "heroineId": 1,
    "text": "안녕, 오늘 기분이 어때?"
}
```

#### Response

```json
{
    "text": "...별로야.",
    "emotion": "neutral",
    "affection": 50,
    "sanity": 85,
    "memoryProgress": 35
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| text | string | NPC 응답 텍스트 |
| emotion | string | 감정 상태 |
| affection | int | 변경된 호감도 |
| sanity | int | 변경된 정신력 |
| memoryProgress | int | 변경된 기억 진척도 |

---

### 히로인별 ID

| ID | 이름 | 성격 |
|----|------|------|
| 1 | 레티아 | 차갑고 무뚝뚝, 반말 |
| 2 | 루파메스 | 활발하고 호탕, 반말 |
| 3 | 로코 | 순수하고 어린아이 같음, 존댓말 |

---

### 감정 종류 (emotion)

| 값 | 설명 |
|----|------|
| neutral | 평온 |
| happy | 기쁨 |
| sad | 슬픔 |
| angry | 분노 |
| shy | 수줍음 |
| fear | 두려움 |
| trauma | 트라우마 |

---

## 3. 대현자 대화

> **스트리밍/비스트리밍 동일 응답**: 둘 다 동일한 컨텍스트(시나리오 검색)를 사용하며, LLM은 1번만 호출됩니다.

### POST /api/npc/sage/chat (스트리밍)

대현자 사트라와 대화합니다. SSE 스트리밍으로 응답합니다.

#### Request

```json
{
    "playerId": 10001,
    "text": "이 세계에 대해 알려줘"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| playerId | int | 플레이어 ID |
| text | string | 플레이어 메시지 |

#### Response (SSE 스트리밍)

```
data: 이
data: 세계는
data: ...
data: {"type": "final", "scenarioLevel": 3, "emotion": "mysterious", "infoRevealed": true}
data: [DONE]
```

---

### POST /api/npc/sage/chat/sync (비스트리밍)

대현자 사트라와 대화합니다. 전체 응답을 한번에 반환합니다.

#### Request

```json
{
    "playerId": 10001,
    "text": "이 세계에 대해 알려줘"
}
```

#### Response

```json
{
    "text": "이 세계는 디멘시움이라는 물질로 인해...",
    "emotion": "mysterious",
    "scenarioLevel": 3,
    "infoRevealed": true
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| text | string | NPC 응답 텍스트 |
| emotion | string | 감정 상태 |
| scenarioLevel | int | 현재 시나리오 레벨 |
| infoRevealed | bool | 정보 공개 여부 |

---

### 대현자 감정 종류

| 값 | 설명 |
|----|------|
| neutral | 평온 |
| amused | 즐거움 |
| mysterious | 신비로움 |
| serious | 진지함 |
| warm | 따뜻함 |
| warning | 경고 |

---

## 4. 히로인간 대화

> **스트리밍/비스트리밍 동일 저장**: 둘 다 동일하게 `agent_memories` 테이블에 저장됩니다.

### POST /api/npc/heroine-conversation/generate (비스트리밍)

두 히로인 사이의 대화를 생성합니다.

#### Request

```json
{
    "heroine1Id": 1,
    "heroine2Id": 2,
    "situation": "길드 휴게실에서 쉬는 중",
    "turnCount": 5
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| heroine1Id | int | O | 첫 번째 히로인 ID |
| heroine2Id | int | O | 두 번째 히로인 ID |
| situation | string | X | 상황 설명 (없으면 자동 생성) |
| turnCount | int | X | 대화 턴 수 (기본값 5) |

#### Response

```json
{
    "id": "uuid-string",
    "heroine1_id": 1,
    "heroine2_id": 2,
    "content": "레티아: ...뭐해.\n루파메스: 아 심심해서...",
    "conversation": [
        {
            "speaker_id": 1,
            "speaker_name": "레티아",
            "text": "...뭐해.",
            "emotion": "neutral"
        },
        {
            "speaker_id": 2,
            "speaker_name": "루파메스",
            "text": "아 심심해서 왔지~",
            "emotion": "happy"
        }
    ],
    "importance_score": 5,
    "timestamp": "2025-01-15T10:30:00.000Z"
}
```

---

### POST /api/npc/heroine-conversation/stream (스트리밍)

두 히로인 사이의 대화를 스트리밍으로 생성합니다.

#### Request

```json
{
    "heroine1Id": 1,
    "heroine2Id": 2,
    "situation": null,
    "turnCount": 5
}
```

#### Response (SSE 스트리밍)

```
data: [레티아] (neutral) ...뭐해.
data: [루파메스] (happy) 아 심심해서 왔지~
data: ...
data: [DONE]
```

---

### GET /api/npc/heroine-conversation

저장된 히로인간 대화 기록을 조회합니다.

#### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| heroine1_id | int | X | 첫 번째 히로인 ID |
| heroine2_id | int | X | 두 번째 히로인 ID |
| limit | int | X | 최대 조회 수 (기본값 10) |

#### Response

```json
{
    "conversations": [
        {
            "id": "uuid-string",
            "agent_id": "conv_1_2",
            "content": "레티아: ...뭐해.\n루파메스: 아 심심해서...",
            "importance_score": 5,
            "metadata": {...},
            "created_at": "2025-01-15T10:30:00.000Z"
        }
    ]
}
```

---

## 5. 길드 시스템

User가 길드에 있는 동안 NPC들이 자동으로 대화합니다.

### POST /api/npc/guild/enter

길드에 진입합니다. **NPC간 백그라운드 대화가 시작**됩니다.

#### Request

```json
{
    "playerId": 10001
}
```

#### Response

```json
{
    "success": true,
    "message": "길드에 진입했습니다. NPC 대화가 시작됩니다.",
    "activeConversation": null
}
```

---

### POST /api/npc/guild/leave

길드에서 퇴장합니다. **NPC간 대화가 중단**됩니다.

#### Request

```json
{
    "playerId": 10001
}
```

#### Response

```json
{
    "success": true,
    "message": "길드에서 퇴장했습니다. NPC 대화가 중단됩니다.",
    "activeConversation": {
        "active": true,
        "npc1_id": 1,
        "npc2_id": 2,
        "started_at": "2025-01-15T10:30:00.000Z"
    }
}
```

---

### GET /api/npc/guild/status/{player_id}

길드 상태를 조회합니다.

#### Response

```json
{
    "in_guild": true,
    "active_conversation": {
        "active": true,
        "npc1_id": 1,
        "npc2_id": 2,
        "started_at": "2025-01-15T10:30:00.000Z"
    },
    "has_background_task": true
}
```

---

## 6. 스트리밍 응답 처리

### 언리얼에서 SSE 처리 예시 (C++)

```cpp
// HTTP 요청 설정
TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
Request->SetURL(TEXT("http://localhost:8090/api/npc/heroine/chat"));
Request->SetVerb(TEXT("POST"));
Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
Request->SetContentAsString(JsonBody);

// 스트리밍 응답 처리
Request->OnRequestProgress().BindLambda([](FHttpRequestPtr Request, int32 BytesSent, int32 BytesReceived)
{
    // 수신된 데이터 파싱
    FString ResponseContent = Request->GetResponse()->GetContentAsString();
    
    // "data: " 접두사 제거 후 처리
    TArray<FString> Lines;
    ResponseContent.ParseIntoArray(Lines, TEXT("\n"));
    
    for (const FString& Line : Lines)
    {
        if (Line.StartsWith(TEXT("data: ")))
        {
            FString Data = Line.Mid(6);  // "data: " 제거
            
            if (Data == TEXT("[DONE]"))
            {
                // 스트리밍 완료
            }
            else if (Data.StartsWith(TEXT("{")))
            {
                // JSON 파싱 (최종 상태)
            }
            else
            {
                // 텍스트 토큰 추가
            }
        }
    }
});

Request->ProcessRequest();
```

---

## 7. 호출 흐름도

```
[게임 시작]
    |
    v
POST /api/npc/login  (1회)
    |
    v
[길드 진입]
    |
    v
POST /api/npc/guild/enter
    |
    +---> [백그라운드] NPC간 자동 대화 (30-60초 간격)
    |
    v
[히로인과 대화]
    |
    v
POST /api/npc/heroine/chat  또는  /chat/sync
    |
    +---> 해당 히로인이 NPC 대화 중이면 자동 인터럽트
    |
    v
[대현자와 대화]
    |
    v
POST /api/npc/sage/chat  또는  /chat/sync
    |
    v
[길드 퇴장]
    |
    v
POST /api/npc/guild/leave
    |
    +---> 백그라운드 NPC 대화 중단
```

---

## 8. 에러 응답

### 404 Not Found

```json
{
    "detail": "세션을 찾을 수 없습니다"
}
```

### 500 Internal Server Error

```json
{
    "detail": "서버 내부 오류가 발생했습니다"
}
```

---

## 9. 프로토콜 요약표

| 기능 | Method | Endpoint | Request Body | Response |
|------|--------|----------|--------------|----------|
| 로그인 | POST | /api/npc/login | playerId, scenarioLevel, heroines[] | success, message |
| 히로인 대화 (스트리밍) | POST | /api/npc/heroine/chat | playerId, heroineId, text | SSE 스트림 |
| 히로인 대화 (비스트리밍) | POST | /api/npc/heroine/chat/sync | playerId, heroineId, text | text, emotion, affection, sanity, memoryProgress |
| 대현자 대화 (스트리밍) | POST | /api/npc/sage/chat | playerId, text | SSE 스트림 |
| 대현자 대화 (비스트리밍) | POST | /api/npc/sage/chat/sync | playerId, text | text, emotion, scenarioLevel, infoRevealed |
| 히로인간 대화 생성 | POST | /api/npc/heroine-conversation/generate | heroine1Id, heroine2Id, situation?, turnCount? | id, content, conversation[] |
| 히로인간 대화 스트리밍 | POST | /api/npc/heroine-conversation/stream | heroine1Id, heroine2Id, situation?, turnCount? | SSE 스트림 |
| 히로인간 대화 조회 | GET | /api/npc/heroine-conversation | heroine1_id?, heroine2_id?, limit? | conversations[] |
| 길드 진입 | POST | /api/npc/guild/enter | playerId | success, message |
| 길드 퇴장 | POST | /api/npc/guild/leave | playerId | success, message, activeConversation |
| 길드 상태 조회 | GET | /api/npc/guild/status/{player_id} | - | in_guild, active_conversation |
| 세션 조회 | GET | /api/npc/session/{player_id}/{npc_id} | - | 세션 정보 |

