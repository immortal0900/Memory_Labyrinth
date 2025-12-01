# NPC Agent System 구현 문서

## 1. 작업 내역 요약

### Phase 1: 환경 설정

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`pyproject.toml`](pyproject.toml) | 신규 | uv 환경 의존성 정의 (langchain, langgraph, redis, mem0ai, fastapi 등) |
| [`docker-compose.yml`](docker-compose.yml) | 수정 | Redis 서비스 추가 (6379 포트) |
| [`src/db/redis_manager.py`](src/db/redis_manager.py) | 신규 | Redis 세션 관리 클래스 (Hot Storage) |
| [`src/db/mem0_manager.py`](src/db/mem0_manager.py) | 신규 | Mem0 장기 기억 관리 클래스 |

### Phase 2: DB 스키마

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`init.sql`](init.sql) | 수정 | session_checkpoints, heroine_scenarios, sage_scenarios 테이블 및 벡터 검색 함수 추가 |

### Phase 3: 공통 구조

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/agents/npc/npc_state.py`](src/agents/npc/npc_state.py) | 신규 | NPCState, HeroineState, SageState TypedDict 정의 |
| [`src/agents/npc/base_npc_agent.py`](src/agents/npc/base_npc_agent.py) | 신규 | BaseNPCAgent 추상 클래스, 호감도/기억진척도 계산 함수 |
| [`src/prompts/prompt_type/npc/heroine_system.yaml`](src/prompts/prompt_type/npc/heroine_system.yaml) | 신규 | 히로인 시스템 프롬프트 템플릿 |
| [`src/prompts/prompt_type/npc/sage_system.yaml`](src/prompts/prompt_type/npc/sage_system.yaml) | 신규 | 대현자 시스템 프롬프트 템플릿 |
| [`src/prompts/prompt_type/npc/NPCPromptType.py`](src/prompts/prompt_type/npc/NPCPromptType.py) | 신규 | 프롬프트 타입 Enum |
| [`src/data/persona/heroine_persona.yaml`](src/data/persona/heroine_persona.yaml) | 신규 | 히로인 3명(레티아, 루파메스, 로코) 페르소나 정의 |
| [`src/data/persona/sage_persona.yaml`](src/data/persona/sage_persona.yaml) | 신규 | 대현자 사트라 페르소나 및 레벨별 정보공개 규칙 |

### Phase 4: 히로인 NPC

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/services/heroine_scenario_service.py`](src/services/heroine_scenario_service.py) | 신규 | 히로인 시나리오 벡터 검색 서비스 |
| [`src/agents/npc/heroine_agent.py`](src/agents/npc/heroine_agent.py) | 신규 | LangGraph 기반 히로인 Agent (의도분류, 기억검색, 응답생성) |

### Phase 5: 대현자 NPC

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/services/sage_scenario_service.py`](src/services/sage_scenario_service.py) | 신규 | 대현자 시나리오 벡터 검색 서비스 |
| [`src/agents/npc/sage_agent.py`](src/agents/npc/sage_agent.py) | 신규 | LangGraph 기반 대현자 Agent (정보공개 규칙 적용) |

### Phase 6: 히로인간 대화

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/agents/npc/heroine_heroine_agent.py`](src/agents/npc/heroine_heroine_agent.py) | 수정 | 히로인간 대화 생성 + 벡터 임베딩 저장 + 스트리밍 |

### Phase 7: FastAPI

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/api/npc_router.py`](src/api/npc_router.py) | 신규 | NPC API 엔드포인트 (SSE 스트리밍 포함) |
| [`main.py`](main.py) | 수정 | FastAPI 앱 설정, CORS, 라우터 등록 |
| [`src/agents/npc/__init__.py`](src/agents/npc/__init__.py) | 수정 | 모듈 exports 정의 |
| [`src/services/__init__.py`](src/services/__init__.py) | 수정 | 서비스 모듈 exports 정의 |

### Phase 8: 통합 메모리 시스템 (신규)

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/db/agent_memory.py`](src/db/agent_memory.py) | 신규 | 통합 메모리 매니저 (하이브리드 스코어링) |
| [`src/db/agent_memory_schema.sql`](src/db/agent_memory_schema.sql) | 신규 | agent_memories 통합 테이블 + 검색 함수 |
| [`src/agents/npc/heroine_agent.py`](src/agents/npc/heroine_agent.py) | 수정 | 통합 메모리 검색 사용, 키워드 분석 노드 |
| [`src/agents/npc/heroine_heroine_agent.py`](src/agents/npc/heroine_heroine_agent.py) | 수정 | 대화 후 통합 테이블에 저장 + 스트리밍 |

**저장소 구조:**
| 저장소 | memory_type | 용도 | agent_id 예시 |
|--------|-------------|------|---------------|
| **Mem0** | - | User-NPC 대화 | `player_10001_npc_1` |
| **agent_memories** | `npc_memory` | NPC A가 B에 대한 기억 | `npc_1_about_2` |
| **agent_memories** | `npc_conversation` | NPC간 대화 | `conv_1_2` |

### Phase 9: 키워드 반복 방지 (신규)

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/agents/npc/base_npc_agent.py`](src/agents/npc/base_npc_agent.py) | 수정 | `calculate_affection_change` 5턴 내 동일 키워드 반복 방지 |
| [`src/agents/npc/npc_state.py`](src/agents/npc/npc_state.py) | 수정 | `recent_used_keywords`, `used_liked_keyword` 필드 추가 |
| [`src/agents/npc/heroine_agent.py`](src/agents/npc/heroine_agent.py) | 수정 | `keyword_analyze` 노드 추가 (방식 B: 키워드 분석 먼저) |

### Phase 10: 스트리밍/비스트리밍 동일 응답 (신규)

| 파일 | 상태 | 작업 내용 |
|------|------|----------|
| [`src/agents/npc/heroine_agent.py`](src/agents/npc/heroine_agent.py) | 수정 | `_prepare_context()`, `_build_full_prompt()`, `_update_state_after_response()` 추가 |
| [`src/agents/npc/sage_agent.py`](src/agents/npc/sage_agent.py) | 수정 | `_prepare_context()`, `_build_full_prompt()`, `_update_state_after_response()` 추가 |
| [`src/agents/npc/heroine_heroine_agent.py`](src/agents/npc/heroine_heroine_agent.py) | 수정 | `_parse_streaming_response()`, `_save_conversation_to_db()` 추가, 스트리밍에서도 DB 저장 |
| [`src/api/npc_router.py`](src/api/npc_router.py) | 수정 | 스트리밍에서 중복 LLM 호출 제거 |

**주요 변경사항:**

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 스트리밍 컨텍스트 | 기억/시나리오 검색 안함 | 비스트리밍과 동일하게 검색 |
| LLM 호출 횟수 | 스트리밍 후 비스트리밍 재호출 (2번) | **1번만** |
| 응답 내용 | 스트리밍/비스트리밍 다름 | **동일** |
| NPC-NPC 스트리밍 저장 | 저장 안함 | **DB에 저장** |

---

## 2. 추가 필요 조치

### 필수 조치

#### 2.1 환경 변수 설정
`.env` 파일을 프로젝트 루트에 생성:

```env
# Database (Supabase)
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Mem0 (선택사항 - 없으면 로컬 pgvector 사용)
MEM0_API_KEY=your_mem0_api_key
```

#### 2.2 의존성 설치
```bash
uv sync
```

#### 2.3 Docker 서비스 시작
```bash
docker-compose up -d
```

#### 2.4 DB 마이그레이션
Supabase에서 스키마 적용:

**1. `init.sql` 실행 (기본 테이블):**
- `session_checkpoints`
- `heroine_scenarios`
- `sage_scenarios`
- `match_heroine_scenarios` 함수
- `match_sage_scenarios` 함수

**2. `src/db/agent_memory_schema.sql` 실행 (통합 메모리):**
- `agent_memories` (통합 메모리 테이블)
- `search_memories_hybrid` 함수
- `search_npc_memories` 함수

#### 2.5 시나리오 데이터 임베딩
`heroine_scenario_database.md`와 `sage_scenarios_detailed_v1.md`의 내용을 DB에 삽입하고 임베딩 생성 필요

### 선택 조치

#### 2.6 Mem0 설정 (선택)
- Mem0 클라우드 사용시: API 키 발급
- 로컬 사용시: pgvector 테이블 자동 생성됨

#### 2.7 LLM 모델 변경 (선택)
현재 `gpt-4o-mini` 사용 중. 변경 원하면:
- `heroine_agent.py`의 `model_name` 파라미터 수정
- `sage_agent.py`의 `model_name` 파라미터 수정

---

## 3. 언리얼 통신 프로토콜

### 3.1 게임 로그인 (매 접속시 1회)

**Endpoint:** `POST /api/npc/login`

**Request:**
```json
{
    "playerId": 10001,
    "scenarioLevel": 3,
    "heroines": [
        {
            "heroineId": 1,
            "affection": 50,
            "memoryProgress": 30,
            "sanity": 100
        },
        {
            "heroineId": 2,
            "affection": 10,
            "memoryProgress": 60,
            "sanity": 80
        },
        {
            "heroineId": 3,
            "affection": 30,
            "memoryProgress": 10,
            "sanity": 100
        }
    ]
}
```

**Response:**
```json
{
    "success": true,
    "message": "세션 초기화 완료"
}
```

---

### 3.2 히로인 대화 (스트리밍)

**Endpoint:** `POST /api/npc/heroine/chat`

**Request:**
```json
{
    "playerId": 10001,
    "heroineId": 1,
    "text": "오늘 기분이 어때?"
}
```

**Response:** SSE (Server-Sent Events)
```
data: 오늘
data: 은
data:  괜찮
data: 아요
data: ...
data: {"type": "final", "affection": 52, "sanity": 100, "memoryProgress": 30, "emotion": "neutral"}
data: [DONE]
```

---

### 3.3 히로인 대화 (비스트리밍)

**Endpoint:** `POST /api/npc/heroine/chat/sync`

**Request:**
```json
{
    "playerId": 10001,
    "heroineId": 1,
    "text": "오늘 기분이 어때?"
}
```

**Response:**
```json
{
    "text": "...뭐예요? 갑자기 그런 걸 물어보시다니.",
    "emotion": "neutral",
    "affection": 50,
    "sanity": 100,
    "memoryProgress": 30
}
```

---

### 3.4 대현자 대화 (스트리밍)

**Endpoint:** `POST /api/npc/sage/chat`

**Request:**
```json
{
    "playerId": 10001,
    "text": "이 세계는 어떤 곳이야?"
}
```

**Response:** SSE
```
data: 흐음
data: ,
data:  레테
data: 라는
data: ...
data: {"type": "final", "scenarioLevel": 3, "emotion": "mysterious", "infoRevealed": true}
data: [DONE]
```

---

### 3.5 대현자 대화 (비스트리밍)

**Endpoint:** `POST /api/npc/sage/chat/sync`

**Request:**
```json
{
    "playerId": 10001,
    "text": "이 세계는 어떤 곳이야?"
}
```

**Response:**
```json
{
    "text": "흐음, 이곳이 궁금한가? 레테는 기억과 망각이 뒤섞인 행성이지...",
    "emotion": "mysterious",
    "scenarioLevel": 3,
    "infoRevealed": true
}
```

---

### 3.6 히로인간 대화 생성 (비스트리밍)

**Endpoint:** `POST /api/npc/heroine-conversation/generate`

**Request:**
```json
{
    "heroine1Id": 1,
    "heroine2Id": 2,
    "situation": "셀레파이스 길드 휴게실에서",
    "turnCount": 5
}
```

**Response:**
```json
{
    "id": "uuid-xxxx",
    "heroine1_id": 1,
    "heroine2_id": 2,
    "content": "루파메스: 야, 레티아! 뭐해?\n레티아: ...보면 몰라요?",
    "conversation": [
        {"speaker_id": 2, "speaker_name": "루파메스", "text": "야, 레티아! 뭐해?", "emotion": "happy"},
        {"speaker_id": 1, "speaker_name": "레티아", "text": "...보면 몰라요?", "emotion": "neutral"}
    ],
    "importance_score": 5,
    "timestamp": "2025-11-28T12:00:00"
}
```

---

### 3.7 히로인간 대화 생성 (스트리밍)

**Endpoint:** `POST /api/npc/heroine-conversation/stream`

**Request:**
```json
{
    "heroine1Id": 1,
    "heroine2Id": 2,
    "situation": "셀레파이스 길드 휴게실에서",
    "turnCount": 5
}
```

**Response:** SSE (Server-Sent Events)
```
data: [루파메스]
data:  (happy)
data:  야,
data:  레티아!
data:  뭐해?
data: 
data: [레티아]
data:  (neutral)
data:  ...보면
data:  몰라요?
data: ...
data: [DONE]
```

---

### 3.8 히로인간 대화 조회

**Endpoint:** `GET /api/npc/heroine-conversation`

**Query Parameters:**
- `heroine1_id` (optional): 특정 히로인 포함 대화만
- `heroine2_id` (optional): 특정 히로인 포함 대화만
- `limit` (default: 10): 최대 조회 수

**Response:**
```json
{
    "conversations": [
        {
            "id": "uuid-xxxx",
            "agent_id": "conv_1_2",
            "content": "루파메스: 야, 레티아! 뭐해?...",
            "importance_score": 5,
            "metadata": {"situation": "...", "speakers": [1, 2]},
            "created_at": "2025-11-28T12:00:00"
        }
    ]
}
```

---

### 3.9 길드 진입 (NPC 대화 활성화)

**Endpoint:** `POST /api/npc/guild/enter`

**Request:**
```json
{
    "playerId": 10001
}
```

**Response:**
```json
{
    "success": true,
    "message": "길드에 진입했습니다. NPC 대화가 시작됩니다.",
    "activeConversation": null
}
```

**동작:**
- 길드에 있는 동안 30-60초 간격으로 랜덤한 히로인 페어가 자동 대화
- User가 특정 히로인과 대화 시작하면 해당 히로인의 NPC 대화 자동 중단

---

### 3.10 길드 퇴장 (NPC 대화 비활성화)

**Endpoint:** `POST /api/npc/guild/leave`

**Request:**
```json
{
    "playerId": 10001
}
```

**Response:**
```json
{
    "success": true,
    "message": "길드에서 퇴장했습니다. NPC 대화가 중단됩니다.",
    "activeConversation": {
        "active": true,
        "npc1_id": 1,
        "npc2_id": 2,
        "started_at": "2025-11-29T10:00:00"
    }
}
```

---

### 3.11 프로토콜 요약표

| 용도 | Method | Endpoint | 스트리밍 |
|------|--------|----------|---------|
| 로그인 | POST | `/api/npc/login` | X |
| **길드 진입** | POST | `/api/npc/guild/enter` | X |
| **길드 퇴장** | POST | `/api/npc/guild/leave` | X |
| 길드 상태 조회 | GET | `/api/npc/guild/status/{player_id}` | X |
| 히로인 대화 | POST | `/api/npc/heroine/chat` | O (SSE) |
| 히로인 대화 | POST | `/api/npc/heroine/chat/sync` | X |
| 대현자 대화 | POST | `/api/npc/sage/chat` | O (SSE) |
| 대현자 대화 | POST | `/api/npc/sage/chat/sync` | X |
| 히로인간 대화 생성 | POST | `/api/npc/heroine-conversation/generate` | X |
| 히로인간 대화 생성 | POST | `/api/npc/heroine-conversation/stream` | O (SSE) |
| 히로인간 대화 조회 | GET | `/api/npc/heroine-conversation` | X |
| 진행중 NPC대화 조회 | GET | `/api/npc/npc-conversation/active/{player_id}` | X |
| 세션 조회 (디버그) | GET | `/api/npc/session/{player_id}/{npc_id}` | X |

### 3.12 대화 인터럽트 동작

```
┌──────────────────────────────────────────────────────────────┐
│                User가 히로인과 대화 시작                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. /api/npc/heroine/chat 호출                               │
│                    │                                         │
│                    ▼                                         │
│  2. 해당 히로인이 NPC 대화 중인지 확인                        │
│     redis_manager.is_heroine_in_conversation(player, heroine)│
│                    │                                         │
│         ┌─────────┴─────────┐                               │
│         ▼                   ▼                               │
│      [Yes]               [No]                               │
│         │                   │                               │
│         ▼                   │                               │
│  3. NPC 대화 중단            │                               │
│     stop_npc_conversation   │                               │
│         │                   │                               │
│         └─────────┬─────────┘                               │
│                   ▼                                         │
│  4. User-히로인 대화 진행                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

예시:
- 레티아(1)와 루파메스(2)가 대화 중
- User가 레티아(1)에게 말을 걸면
- → 레티아-루파메스 대화 자동 중단
- → User-레티아 대화 시작
```

---

## 4. 사용 방법

### 4.1 서버 실행

```bash
# 1. 프로젝트 디렉토리로 이동
cd C:\ProjectML

# 2. 의존성 설치 (최초 1회)
uv sync

# 3. Docker 서비스 시작 (Redis)
docker-compose up -d

# 4. 서버 실행
python main.py
```

서버가 `http://localhost:8090`에서 실행됩니다.

### 4.2 API 테스트 (curl)

```bash
# 로그인
curl -X POST http://localhost:8090/api/npc/login \
  -H "Content-Type: application/json" \
  -d '{"playerId": 10001, "scenarioLevel": 3, "heroines": [{"heroineId": 1, "affection": 50, "memoryProgress": 30, "sanity": 100}]}'

# 히로인 대화 (비스트리밍)
curl -X POST http://localhost:8090/api/npc/heroine/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"playerId": 10001, "heroineId": 1, "text": "안녕?"}'

# 대현자 대화 (비스트리밍)
curl -X POST http://localhost:8090/api/npc/sage/chat/sync \
  -H "Content-Type: application/json" \
  -d '{"playerId": 10001, "text": "이 세계는 어떤 곳이야?"}'
```

### 4.3 Swagger UI

브라우저에서 `http://localhost:8090/docs` 접속하면 API 문서 및 테스트 UI 사용 가능

### 4.4 언리얼 엔진 연동 (C++ 예시)

```cpp
// HTTP 요청 예시 (UE5)
void ANPCController::SendChatRequest(int32 PlayerId, int32 HeroineId, FString Text)
{
    TSharedRef<IHttpRequest> Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(TEXT("http://localhost:8090/api/npc/heroine/chat/sync"));
    Request->SetVerb(TEXT("POST"));
    Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    
    FString JsonBody = FString::Printf(
        TEXT("{\"playerId\": %d, \"heroineId\": %d, \"text\": \"%s\"}"),
        PlayerId, HeroineId, *Text
    );
    Request->SetContentAsString(JsonBody);
    
    Request->OnProcessRequestComplete().BindUObject(this, &ANPCController::OnChatResponse);
    Request->ProcessRequest();
}
```

### 4.5 히로인 ID 참조

| ID | 이름 | 설명 |
|----|------|------|
| 0 | 사트라 | 대현자 NPC |
| 1 | 레티아 | 쌍검 딜러, 원칙적, 존댓말 |
| 2 | 루파메스 | 대검 딜러, 열정적, 반말 |
| 3 | 로코 | 망치 탱커, 소심함, 존댓말 |

### 4.6 감정(emotion) 타입

**히로인:**
- `neutral`, `happy`, `sad`, `angry`, `shy`, `fear`, `trauma`

**대현자:**
- `neutral`, `amused`, `mysterious`, `serious`, `warm`, `warning`

---

## 5. 아키텍처 다이어그램

```
┌─────────────────┐     ┌─────────────────┐
│   Unreal Engine │────▶│   FastAPI       │
│   (클라이언트)    │◀────│   (main.py)     │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │ Heroine   │ │ Sage      │ │ H-H       │
            │ Agent     │ │ Agent     │ │ Agent     │
            └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                  │             │             │
    ┌─────────────┴─────────────┴─────────────┴─────────────┐
    │                                                        │
    ▼                                                        ▼
┌──────────┐  ┌──────────┐  ┌──────────────────┐  ┌──────────┐
│  Redis   │  │  Mem0    │  │  PostgreSQL      │  │   LLM    │
│ (Session)│  │(User-NPC)│  │  (pgvector)      │  │ (OpenAI) │
└──────────┘  └──────────┘  └────────┬─────────┘  └──────────┘
                                     │
                        ┌────────────┴────────────┐
                        ▼                         ▼
                ┌─────────────────┐       ┌─────────────┐
                │  agent_memories │       │  scenarios  │
                │  (통합 메모리)  │       │  (heroine/  │
                │                 │       │   sage)     │
                │  - npc_memory   │       └─────────────┘
                │  - npc_conversation
                │  - user_npc     │
                └─────────────────┘
```

### 메모리 저장소 구조

```
┌───────────────────────────────────────────────────────────┐
│                    Memory Storage                          │
├───────────────────────────────────────────────────────────┤
│                                                            │
│  1. Redis (Hot Storage)                                    │
│     └── session:{player_id}:{npc_id}                      │
│         ├── conversation_buffer (최근 20턴)               │
│         ├── recent_used_keywords (5턴 내 키워드)          │
│         └── state (affection, sanity, memoryProgress)     │
│                                                            │
│  2. Mem0 (User-NPC 장기기억) ★ 중요                        │
│     └── player_{player_id}_npc_{npc_id}                   │
│         └── 자동 필터링된 중요 사실/선호도                 │
│                                                            │
│  3. PostgreSQL + pgvector (NPC간 메모리)                   │
│     │                                                      │
│     ├── agent_memories (NPC간 기억 전용)                  │
│     │   ├── memory_type: 'npc_memory'     → npc_1_about_2 │
│     │   └── memory_type: 'npc_conversation' → conv_1_2    │
│     │                                                      │
│     └── scenarios (시나리오 DB)                           │
│         ├── heroine_scenarios                             │
│         └── sage_scenarios                                │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### 스트리밍/비스트리밍 처리 흐름

```
┌───────────────────────────────────────────────────────────────┐
│              스트리밍/비스트리밍 동일 응답 구조                  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  [User-NPC 대화] (heroine_agent.py / sage_agent.py)          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. _prepare_context()                                   │ │
│  │    ├── 키워드 분석 (호감도 변화량)                       │ │
│  │    ├── 의도 분류                                        │ │
│  │    └── 기억/시나리오 검색                               │ │
│  │                                                         │ │
│  │ 2. _build_full_prompt()                                 │ │
│  │    └── 동일한 프롬프트 (출력 형식만 다름)               │ │
│  │                                                         │ │
│  │ 3. LLM 호출 (1번만!)                                    │ │
│  │    ├── 스트리밍: streaming_llm.astream()                │ │
│  │    └── 비스트리밍: llm.ainvoke()                        │ │
│  │                                                         │ │
│  │ 4. _update_state_after_response()                       │ │
│  │    ├── Redis 세션 저장                                  │ │
│  │    └── Mem0 기억 저장                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  [NPC-NPC 대화] (heroine_heroine_agent.py)                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. 상황 생성 (generate_situation)                       │ │
│  │                                                         │ │
│  │ 2. _build_conversation_prompt()                         │ │
│  │    └── 동일한 프롬프트 (출력 형식만 다름)               │ │
│  │                                                         │ │
│  │ 3. LLM 호출 (1번만!)                                    │ │
│  │                                                         │ │
│  │ 4. _save_conversation_to_db()                           │ │
│  │    ├── 스트리밍: 텍스트→JSON 파싱 후 저장               │ │
│  │    └── 비스트리밍: JSON 직접 저장                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

## 6. 파일 구조

```
C:\ProjectML\
├── main.py                          # FastAPI 진입점
├── pyproject.toml                   # 의존성 정의
├── docker-compose.yml               # Redis + PostgreSQL
├── init.sql                         # DB 스키마
├── .env                             # 환경 변수 (생성 필요)
│
└── src/
    ├── agents/
    │   └── npc/
    │       ├── __init__.py
    │       ├── npc_state.py         # 상태 정의
    │       ├── base_npc_agent.py    # 베이스 클래스
    │       ├── heroine_agent.py     # 히로인 Agent
    │       ├── sage_agent.py        # 대현자 Agent
    │       └── heroine_heroine_agent.py  # 히로인간 대화
    │
    ├── api/
    │   └── npc_router.py            # API 엔드포인트
    │
    ├── db/
    │   ├── config.py
    │   ├── redis_manager.py         # Redis 관리
    │   ├── mem0_manager.py          # Mem0 관리 (User-NPC 대체 가능)
    │   ├── agent_memory.py          # 통합 메모리 매니저 (하이브리드 스코어링)
    │   └── agent_memory_schema.sql  # agent_memories 통합 테이블 스키마
    │
    ├── services/
    │   ├── heroine_scenario_service.py
    │   └── sage_scenario_service.py
    │
    ├── prompts/
    │   └── prompt_type/
    │       └── npc/
    │           ├── heroine_system.yaml
    │           ├── sage_system.yaml
    │           └── NPCPromptType.py
    │
    └── data/
        └── persona/
            ├── heroine_persona.yaml
            └── sage_persona.yaml
```

```
src/
  agents/
    npc/
      __init__.py              # 모듈 exports
      npc_state.py             # NPCState, HeroineState, SageState 정의
      base_npc_agent.py        # 공통 베이스 클래스
      heroine_agent.py         # 히로인 NPC (LangGraph + 스트리밍)
      sage_agent.py            # 대현자 NPC (LangGraph + 스트리밍)
      heroine_heroine_agent.py # 히로인간 대화 생성
  api/
    npc_router.py              # FastAPI 라우터 (SSE 스트리밍)
  db/
    redis_manager.py           # Redis 세션 관리
    mem0_manager.py            # Mem0 장기 기억 관리
  services/
    heroine_scenario_service.py  # 히로인 시나리오 검색
    sage_scenario_service.py     # 대현자 시나리오 검색
  prompts/
    prompt_type/
      npc/
        heroine_system.yaml    # 히로인 시스템 프롬프트
        sage_system.yaml       # 대현자 시스템 프롬프트
        NPCPromptType.py       # 프롬프트 타입 Enum
  data/
    persona/
      heroine_persona.yaml     # 히로인 페르소나 (레티아, 루파메스, 로코)
      sage_persona.yaml        # 대현자 페르소나 (사트라)
main.py                        # FastAPI 앱 진입점
pyproject.toml                 # 의존성 정의
docker-compose.yml             # Redis 포함
init.sql                       # DB 스키마 (session_checkpoints, 시나리오 테이블)
```