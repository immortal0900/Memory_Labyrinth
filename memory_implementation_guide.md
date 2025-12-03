# System Architecture: Real-Time NPC with Hybrid Memory (Production-Ready)

본 프로젝트는 언리얼 엔진 기반 게임의 NPC(히로인 3명 + 대현자)를 위한 백엔드 시스템입니다.
응답 속도(Latency)와 장기 기억(Long-term Memory), 데이터 안정성(Persistence)을 모두 충족하기 위해
**LangGraph, Redis, Supabase(Mem0)**를 결합한 하이브리드 아키텍처를 채택합니다.

---

## 1. Core Philosophy

```
Speed First        → 읽기(Read) 작업은 무조건 Redis(In-Memory)에서 수행하여 응답 지연 0ms 달성
Persistence        → 쓰기(Write) 작업은 응답 후 백그라운드에서 DB로 동기화, 서버 재부팅 시에도 데이터 손실 0%
Context-Aware      → 대화의 유효 기간(1시간)과 토큰 길이(20턴)를 모두 고려하여 문맥 관리
Real-Time Fact     → 중요 정보는 대화 종료를 기다리지 않고 즉시 Mem0에 저장
Memory Boundary    → 해금되지 않은 기억/비밀은 절대 말하지 않음 (memoryProgress 기반 필터)
```

---

## 2. Tech Stack & Role Definition

| Component | Tech Stack | Primary Role | Data Lifecycle |
|:---|:---|:---|:---|
| **State Controller** | **LangGraph** | 대화 흐름 제어, 노드 분기, Tool 호출 | 전 구간 |
| **Hot Storage** | **Redis (RAM)** | 현재 세션의 대화(10~20턴), 상태(Affection/Sanity), 1시간 내 요약본 저장 | 세션 중 + 백업 동기화 |
| **Cold Storage** | **Supabase (직접 구현)** | Redis 전체 상태의 스냅샷 백업 (서버/클라이언트 재시작 복구용) | 대화 종료 시 자동 |
| **Knowledge Base** | **Mem0 (Supabase pgvector)** | 추출된 사실(Fact) 정보의 영구 저장 및 벡터 검색 | 실시간 + 세션 종료 시 |
| **Scenario DB** | **pgvector** | 히로인/대현자 정적 시나리오 (memoryProgress/scenario_level 필터) | 정적 |
| **LLM** | **Grok API (Streaming)** | 페르소나 연기, 답변 생성 | 각 턴마다 호출 |

---

## 3. Data Workflow (Complete Lifecycle)

### Phase 0. Session Initialization (게임 접속)

**Trigger:** 유저가 게임에 로그인 (EVERY_LOGIN 프로토콜)

**Process:**

1. Redis에서 `session:{player_id}:{heroine_id}` 키로 상태 조회.

2. **[Case A] Redis에 데이터 존재 (정상 케이스):**
   - 그대로 사용. (빠른 경로)

3. **[Case B] Redis에 데이터 없음 (서버 재시작/유저 오래 안 옴):**
   - Supabase `session_checkpoints` 테이블에서 마지막 저장된 상태를 조회.
   - `last_active_at` (마지막 활동 시간)을 확인:
     - **1시간 이내:** 상태를 Redis로 로드(Hydration). 대화 이어가기 모드.
     - **1시간 초과:** 
       - 기존 상태를 Mem0로 아카이빙(Archive) 후 삭제.
       - Redis를 빈 상태(Clean Slate)로 초기화.
       - NPC는 "오랜만이야!" 같은 재회 인사로 새 대화 시작.

```python
async def initialize_session(player_id: int, heroine_id: int) -> dict:
    key = f"session:{player_id}:{heroine_id}"
    
    # Step 1: Redis 확인 (0ms)
    redis_data = await redis.get(key)
    if redis_data:
        return json.loads(redis_data)
    
    # Step 2: Supabase Checkpoint 확인
    checkpoint = await supabase.table("session_checkpoints") \
        .select("*") \
        .eq("player_id", player_id) \
        .eq("heroine_id", heroine_id) \
        .single()
    
    if checkpoint.data:
        last_active = datetime.fromisoformat(checkpoint.data["last_active_at"])
        
        if datetime.now() - last_active < timedelta(hours=1):
            # Case B-1: 1시간 이내 → Redis로 복원
            session = checkpoint.data["session_data"]
            await redis.setex(key, 86400, json.dumps(session))
            return session
        else:
            # Case B-2: 1시간 초과 → 아카이빙 후 새 시작
            await archive_to_mem0(player_id, heroine_id, checkpoint.data)
            await supabase.table("session_checkpoints").delete() \
                .eq("player_id", player_id).eq("heroine_id", heroine_id)
    
    # Case C: 완전 새 유저 또는 아카이빙 완료 → 빈 세션
    return create_empty_session(player_id, heroine_id)
```

---

### Phase 1. User Input Processing (유저 발화)

**Trigger:** 언리얼 엔진이 `/api/chat` 엔드포인트로 유저 메시지 전송 (REQUEST 프로토콜)

**Process:**

1. **Context Loading (0ms):** Redis에서 즉시 로드
   - `conversation_buffer`: 최근 대화 10~20턴 (Raw Text)
   - `short_term_summary`: 최근 1시간 내 요약본 (이미 요약됨)
   - `state`: affection, sanity, memoryProgress, emotion

2. **Router Node (LangGraph):** 유저 질문 분석
   - **일반 대화 (예: "오늘 날씨 좋다"):** 검색 없이 Redis 컨텍스트만 사용 → `GenerateNode`로 직행.
   - **과거 회상 (예: "지난번 숲 기억나?"):** `RetrieveNode`로 분기.
   - **해금 기억 질문 (예: "네 과거가 궁금해"):** `ScenarioRetrieveNode`로 분기.

3. **[조건부] RetrieveNode (Mem0 검색):**
   - Redis의 `short_term_summary`를 먼저 확인.
     - 여기 있으면? 검색 생략 (최근 이야기니까).
     - 없으면? Mem0(Supabase)에 벡터 검색 수행 (0.1~0.2초 소요).
   - 검색 결과를 `retrieved_facts`에 저장.

4. **[조건부] ScenarioRetrieveNode (pgvector 검색):**
   - 현재 `memoryProgress` 확인.
   - `heroine_scenarios.memoryProgress <= 현재 memoryProgress` 조건으로 해금된 시나리오만 검색.
   - 검색 결과를 `unlocked_scenarios`에 저장.

```python
# LangGraph Router 분기 로직 (LLM Intent Classification)
async def route_by_intent(state: ConversationState) -> str:
    """
    키워드 기반 분기는 취약함. LLM이 의도를 판단해야 함.
    예: "어제 뭐 먹었어?" → 키워드 "어제"가 있지만 시나리오가 아닌 대화 기억
    예: "네가 마법을 쓸 수 있었던 이유가 뭐야?" → 키워드 없지만 시나리오 질문
    """
    user_message = state["messages"][-1].content
    conversation_context = state.get("short_term_summary", "")
    
    # LLM으로 Intent 분류 (가벼운 모델 사용 권장)
    intent_prompt = f"""
    다음 유저 메시지의 의도를 분류하세요.
    
    [최근 대화 맥락]
    {conversation_context}
    
    [유저 메시지]
    {user_message}
    
    [분류 기준]
    - general: 일상 대화, 감정 표현, 질문 없는 대화
    - memory_recall: 플레이어와 히로인이 함께 나눈 과거 대화/경험을 물어봄
    - scenario_inquiry: 히로인의 과거, 기억 상실 전 이야기, 비밀, 정체성에 대해 물어봄
    
    [출력]
    반드시 general, memory_recall, scenario_inquiry 중 하나만 출력하세요.
    """
    
    intent = await llm.invoke(intent_prompt)  # 가벼운 모델로 빠르게
    intent = intent.strip().lower()
    
    intent_to_node = {
        "general": "generate",
        "memory_recall": "memory_retrieve",
        "scenario_inquiry": "scenario_retrieve"
    }
    
    return intent_to_node.get(intent, "generate")
```

**Intent 분류 예시:**
| 유저 메시지 | Intent | 이유 |
|:---|:---|:---|
| "오늘 날씨 좋다" | general | 일상 대화 |
| "어제 우리 뭐 얘기했더라?" | memory_recall | 함께 나눈 대화 회상 |
| "저번에 던전 3층 갔을 때 기억나?" | memory_recall | 함께한 경험 회상 |
| "네가 마법을 잃기 전엔 어땠어?" | scenario_inquiry | 히로인 과거/비밀 |
| "왜 기억을 잃은 거야?" | scenario_inquiry | 히로인 정체성 |
| "뭐 먹고 싶어?" | general | 일상 대화 |

---

### Phase 2. Response Generation (답변 생성)

**Process:**

1. **Prompt Assembly (동적 조립):**

```python
prompt = f"""
# System Prompt
당신은 히로인 {heroine_name}입니다.

[현재 상태]
- Affection: {affection}
- Sanity: {sanity}
- MemoryProgress: {memory_progress} (해금 지점: 10, 50, 60, 70, 100)

[페르소나 규칙]
- 해금되지 않은 기억(memoryProgress > {memory_progress})은 절대 말하지 않습니다.
- 기억이 없는 질문에는 "잘 기억이 안 나..." 라고 답합니다.
- Sanity가 낮으면({sanity} < 30) 우울한 톤으로 대화합니다.

# [장기 기억] (Mem0 검색 결과 - 있을 경우만)
{retrieved_facts if retrieved_facts else "없음"}

# [해금된 시나리오] (있을 경우만)
{unlocked_scenarios if unlocked_scenarios else "없음"}

# [최근 요약] (1시간 내 대화의 핵심)
{short_term_summary}

# [최근 대화] (Raw History)
{conversation_buffer}

# [User Input]
{user_message}

[출력 형식]
응답 시 반드시 아래 JSON 형식으로 출력하세요:
{{
    "thought": "(내면의 생각 - 유저에게 보이지 않음)",
    "text": "(실제 대화 내용)",
    "emotion": "happy|sad|angry|shy|neutral|worried",
    "affection_delta": 0~5,
    "sanity_delta": -5~5
}}
"""
```

2. **LLM 호출 (Streaming):** 첫 토큰부터 즉시 전송. (TTFT 최소화)

3. **Response 파싱 및 전송:** 
   - `thought` 필드 제거 (유저에게 안 보임)
   - 언리얼 엔진으로 RESPONSE 프로토콜 전달:
     ```json
     {
         "text": "응, 기억나! 그때 재밌었지~",
         "emotion": "happy",
         "affection": 55,
         "sanity": 82,
         "memoryProgress": 50
     }
     ```

---

### Phase 3. Post-Processing (백그라운드 동기화)

**Trigger:** 유저에게 응답 완료 즉시, FastAPI `BackgroundTasks`로 비동기 실행

**Process (순서 무관, 병렬 수행):**

1. **Redis 업데이트 (즉시):**
   - `conversation_buffer`에 방금 나눈 대화 추가.
   - 20턴 초과 시 가장 오래된 것 1개 제거.
   - `state` 업데이트 (affection, sanity, emotion).
   - `last_active_at` 타임스탬프 갱신.

2. **Mem0 실시간 저장 (비동기):**
   - 방금 나눈 대화를 Mem0에 `add()`.
   - Mem0는 내부적으로 LLM을 돌려 중요한 사실만 추출하여 `memories` 테이블에 저장.
   - **예시:**
     - User: "나 내일 부산 가."
     - Mem0 저장: `User Plan: Visit Busan tomorrow`

3. **Checkpoint 백업 (비동기):**
   - Redis의 현재 상태 전체를 Supabase `session_checkpoints` 테이블에 Upsert.
   - 이 백업본은 서버가 꺼져도 살아남음.

4. **[조건부] 세션 아카이빙 (1시간 OR 20턴 초과 시):**
   - **Condition Check:**
     - `현재 시간 - last_active_at > 1시간` OR `conversation_buffer 길이 >= 20턴`
   - **Action:**
     - Redis의 `conversation_buffer` 전체를 LLM으로 요약.
     - 요약본을 `short_term_summary`에 덮어쓰기 (또는 Mem0에 추가 저장).
     - `conversation_buffer`를 비움.

```python
async def post_process(
    player_id: int,
    heroine_id: int,
    user_message: str,
    assistant_response: dict,
    background_tasks: BackgroundTasks
):
    # 1. Redis 즉시 업데이트
    session = await redis_manager.load_session(player_id, heroine_id)
    session["conversation_buffer"].append({
        "role": "user", "content": user_message
    })
    session["conversation_buffer"].append({
        "role": "assistant", 
        "content": assistant_response["text"],
        "emotion": assistant_response["emotion"]
    })
    session["state"]["affection"] = assistant_response["affection"]
    session["state"]["sanity"] = assistant_response["sanity"]
    session["last_active_at"] = datetime.now().isoformat()
    await redis_manager.save_session(player_id, heroine_id, session)
    
    # 2~4. 백그라운드 작업 등록
    background_tasks.add_task(save_to_mem0, player_id, heroine_id, user_message, assistant_response["text"])
    background_tasks.add_task(save_checkpoint, player_id, heroine_id, session)
    
    # 20턴 초과 체크
    if len(session["conversation_buffer"]) >= 20:
        background_tasks.add_task(summarize_and_clear, player_id, heroine_id, session)
```

---

## 4. Edge Case Handling (엣지 케이스 대응)

### Case 1: 유저가 1시간 안 돼서 게임을 끔
- **Result:** 
  - 중요 정보는 이미 Mem0에 실시간 저장되어 있음. (손실 0)
  - Redis는 날아가지만 Supabase Checkpoint에 백업 존재.
- **Next Login:** 1시간 이내라면 백업에서 복구하여 이어하기.

### Case 2: 유저가 짧은 대화(3턴)만 하고 1주일 뒤 접속
- **Result:**
  - 1시간 초과 판정 → Redis 내용을 Mem0로 이관 후 비움.
  - 대화 양이 적어도 "시간 기준"으로 세션을 종료함. (자연스러움 확보)
- **NPC 반응:** "오랜만이네! 그동안 어떻게 지냈어?"

### Case 3: 유저가 1시간 내내 대화하면서 100턴 진행
- **Result:**
  - 20턴마다 자동으로 요약 후 버퍼 정리.
  - 프롬프트는 항상 "최근 20턴 + 요약본"만 들어가므로 토큰 폭발 방지.
- **LLM Input Token:** 상한 유지 (예: 5,000 토큰 이하).

### Case 4: 유저가 해금되지 않은 기억을 물어봄
- **Result:**
  - 현재 `memoryProgress` < 시나리오의 `memoryProgress` → 시나리오 검색 결과 없음.
  - NPC는 "음... 잘 기억이 안 나..." 또는 "아직은 말할 수 없어..." 로 응답.
- **보안:** LLM 프롬프트에 해금 티어 명시, 검색 자체도 필터링.

### Case 5: 던전에서 히로인 사망
- **Result:**
  - `sanity` 감소 (affection 증가량과 동일 비율로 감소).
  - 다음 대화에서 우울한 톤 적용.
- **복구:** 플레이어와 대화하며 affection 올리면 sanity도 함께 회복.

### Case 6: memoryProgress 해금 이벤트 발생
- **해금 지점:** affection 10, 50, 60, 70, 100 도달 시
- **Result:**
  - `memoryProgress` 증가 (한번 오르면 절대 감소 안 함).
  - 새로운 tier의 시나리오가 검색 가능해짐.
- **NPC 반응:** 해금된 기억을 자연스럽게 대화에 녹여냄.

---

## 5. Persona Consistency Rules

### 5.1 Dynamic Few-Shot (Sanity 기반)
> **참조:** `C:\ProjectML\src\data\heroin_detail_information.md`
> 
> Sanity 구간별(0~30, 31~79, 80~100) 어조 예시는 위 파일에 히로인별로 정의되어 있음.

```python
def get_sanity_examples(heroine_id: int, sanity: int) -> str:
    """
    heroin_detail_information.md에서 해당 히로인의 sanity별 예시를 로드
    """
    heroine_data = load_heroine_detail(heroine_id)  # YAML/MD 파싱
    
    if sanity <= 30:
        return heroine_data["sanity_examples"]["depressed"]
    elif sanity >= 80:
        return heroine_data["sanity_examples"]["happy"]
    else:
        return heroine_data["sanity_examples"]["neutral"]
```

### 5.2 Knowledge Boundary
- Mem0 검색 결과가 없으면 → "기억이 안 나" 라고 답변 강제.
- 시나리오 검색 결과가 없으면 (해금 안 됨) → "아직은... 말할 수 없어" 로 답변 강제.

### 5.3 Inner Monologue (할루시네이션 방지)
- LLM이 답변 전 "속마음(thought)"을 먼저 생성.
- 출력 형식: `{"thought": "...", "text": "..."}` → thought 부분은 유저에게 안 보임.
- 이를 통해 LLM이 "무엇을 알고 있는지" 먼저 정리하게 함.

### 5.4 히로인별 특성
> **참조:** `C:\ProjectML\src\data\heroin_detail_information.md`
> 
> 히로인별 성격, 말투, 기억상실 배경, Sanity별 어조 변화 등은 위 파일에 정의되어 있음.
> 프롬프트 생성 시 해당 파일에서 동적으로 로드하여 사용.

---

## 6. Database Schema

### 6.1 session_checkpoints (Cold Storage)
```sql
CREATE TABLE session_checkpoints (
    id SERIAL PRIMARY KEY,
    player_id INT NOT NULL,
    heroine_id INT NOT NULL,
    session_data JSONB NOT NULL,
    last_active_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_id, heroine_id)
);

CREATE INDEX idx_checkpoint_player_heroine ON session_checkpoints(player_id, heroine_id);
CREATE INDEX idx_checkpoint_last_active ON session_checkpoints(last_active_at);
```

### 6.2 heroine_scenarios (Scenario DB)
```sql
CREATE TABLE heroine_scenarios (
    id SERIAL PRIMARY KEY,
    heroine_id INT NOT NULL,
    memoryProgress INT NOT NULL,  -- 해금 티어 (1~6)
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- memoryProgress 매핑: 1=affection10, 2=50, 3=60, 4=70, 5=100, 6=100+
CREATE INDEX idx_heroine_scenarios_tier ON heroine_scenarios(heroine_id, memoryProgress);
```

### 6.3 sage_scenarios (대현자용)
```sql
CREATE TABLE sage_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_level INT NOT NULL,  -- 1~10
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sage_level ON sage_scenarios(scenario_level);
```

### 6.4 Scenario 검색 함수
```sql
-- 히로인 시나리오 검색 (해금된 것만)
CREATE FUNCTION match_heroine_scenarios(
    query_embedding VECTOR(1536),
    p_heroine_id INT,
    p_max_tier INT,
    p_match_count INT
) RETURNS TABLE (id INT, content TEXT, memoryProgress INT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        hs.id,
        hs.content,
        hs.memoryProgress,
        1 - (hs.content_embedding <=> query_embedding) AS similarity
    FROM heroine_scenarios hs
    WHERE hs.heroine_id = p_heroine_id
      AND hs.memoryProgress <= p_max_tier
    ORDER BY hs.content_embedding <=> query_embedding
    LIMIT p_match_count;
END;
$$;

-- 대현자 시나리오 검색
CREATE FUNCTION match_sage_scenarios(
    query_embedding VECTOR(1536),
    p_max_level INT,
    p_match_count INT
) RETURNS TABLE (id INT, content TEXT, scenario_level INT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ss.id,
        ss.content,
        ss.scenario_level,
        1 - (ss.content_embedding <=> query_embedding) AS similarity
    FROM sage_scenarios ss
    WHERE ss.scenario_level <= p_max_level
    ORDER BY ss.content_embedding <=> query_embedding
    LIMIT p_match_count;
END;
$$;
```

---

## 7. Performance Metrics (목표 수치)

| Metric | Target | Strategy |
|:---|:---|:---|
| **Response Time (TTFT)** | < 500ms | Redis 읽기 0ms + LLM Streaming |
| **Data Loss Rate** | 0% | Checkpoint 백업 + Mem0 실시간 저장 |
| **Token Efficiency** | < 6,000 tokens | 20턴 버퍼 + 요약본 조합 |
| **Retrieval Latency (Mem0)** | < 200ms | pgvector HNSW 인덱스 |
| **Session Recovery** | < 100ms | Supabase → Redis Hydration |

---

## 8. Implementation Notes

### 8.1 Checkpoint는 LangGraph Checkpointer가 아닌 직접 구현
```
[LangGraph PostgresSaver 미사용 이유]
- 매 노드마다 DB Write 발생 (대화 1회당 ~100 rows 생성)
- 전체 State 직렬화/역직렬화 오버헤드
- 게임에서 Time-travel/장애 복구 기능 불필요
- 직접 구현: 대화 종료 시 1회 Write로 충분

[직접 구현 방식]
- Redis: 실시간 상태 (0ms 읽기)
- Supabase session_checkpoints: 주기적 백업 (1회/대화)
- 단순 JSONB Upsert로 충분
```

### 8.2 "1시간" 기준은 조정 가능
게임의 플레이 패턴에 따라 30분, 2시간 등으로 변경하세요.

### 8.2 Redis 메모리 부족 시
TTL(Time To Live)을 설정하여 오래된 세션은 자동 삭제되도록 합니다.
```python
self.SESSION_TTL = 3600 * 24  # 24시간 후 자동 삭제
```

### 8.3 Mem0 비용 관리
모든 대화를 다 넣지 말고, "중요도 점수(Importance Score)"를 매겨 일정 점수 이상만 저장하는 필터링을 추가하세요.

### 8.4 유저별 데이터 격리 필수
```python
# Redis 키: session:{player_id}:{heroine_id}
# Mem0 user_id: {player_id}_{heroine_id}
# 모든 쿼리에 player_id 필터 포함
```

### 8.5 memoryProgress 불변 규칙
```python
# 한번 오른 memoryProgress는 절대 감소하지 않음
new_progress = max(current_progress, calculate_memory_progress(affection))

# 해금 지점 계산
def calculate_memory_progress(affection: int) -> int:
    if affection >= 100: return 5
    if affection >= 70: return 4
    if affection >= 60: return 3
    if affection >= 50: return 2
    if affection >= 10: return 1
    return 0
```

---

## 9. API Protocol Summary

### EVERY_LOGIN (접속 시 1회)
```json
// Response
{
    "affection": 50,
    "sanity": 80,
    "memoryProgress": 30,
    "emotion": "happy",
    "greeting": "오늘도 왔구나! 반가워~"
}
```

### REQUEST/RESPONSE (이후 통신)
```json
// Request
{
    "player_id": 10001,
    "heroine_id": 1,
    "message": "안녕!"
}

// Response
{
    "text": "응, 안녕! 오늘은 뭐 할 거야?",
    "emotion": "happy",
    "affection": 52,
    "sanity": 80,
    "memoryProgress": 30
}
```

---


