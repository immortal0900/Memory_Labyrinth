# NPC Agent System 면접 준비 문서

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [데이터 저장소 아키텍처](#2-데이터-저장소-아키텍처)
3. [시나리오 임베딩 및 청킹](#3-시나리오-임베딩-및-청킹)
4. [메모리 시스템](#4-메모리-시스템)
5. [Retriever 구현](#5-retriever-구현)
6. [하이브리드 스코어링 검색](#6-하이브리드-스코어링-검색)
7. [LangGraph 기반 에이전트 구조](#7-langgraph-기반-에이전트-구조)
8. [스트리밍/비스트리밍 동일 응답](#8-스트리밍비스트리밍-동일-응답)
9. [기술 선택 근거 총정리](#9-기술-선택-근거-총정리)

---

## 1. 프로젝트 개요

### 1.1 해결하려는 문제
기억을 잃은 NPC(히로인, 대현자)와 자연스러운 대화를 하면서, 플레이어의 행동에 따라 NPC의 상태(호감도, 기억진척도)가 변화하고, 점진적으로 과거 기억을 되찾는 시스템 구현

### 1.2 핵심 기능
| 기능 | 설명 |
|------|------|
| **호감도 시스템** | 좋아하는 키워드 +10, 트라우마 키워드 -10 |
| **기억 진척도** | 호감도가 memoryProgress를 넘어야 진척도 상승 |
| **점진적 시나리오 해금** | memoryProgress에 따라 NPC가 말할 수 있는 과거 기억 제한 |
| **NPC간 대화** | 히로인끼리 자동 대화 생성 및 저장 |
| **User-NPC 장기 기억** | 대화 내용을 Mem0에 저장하여 추후 검색 |

### 1.3 사용 기술 스택
```
- FastAPI: REST API 서버
- Redis: 세션 관리 (Hot Storage)
- PostgreSQL + pgvector: 벡터 검색 (Supabase)
- Mem0: User-NPC 장기 기억
- LangChain/LangGraph: LLM 에이전트 프레임워크
- OpenAI Embeddings: text-embedding-3-small (1536차원)
- SSE: 스트리밍 응답
```

---

## 2. 데이터 저장소 아키텍처

### 2.1 왜 3가지 저장소를 사용했는가?

```
┌─────────────────────────────────────────────────────────────────┐
│                    데이터 저장소 아키텍처                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Redis     │  │   Mem0      │  │   PostgreSQL + pgvector │ │
│  │ (Hot Data)  │  │ (User-NPC)  │  │   (NPC-NPC + 시나리오)  │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│        │                │                       │               │
│        ▼                ▼                       ▼               │
│  - 세션 상태       - 대화 기억           - agent_memories       │
│  - 최근 20턴       - 자동 요약            (NPC간 기억)         │
│  - TTL: 24시간     - 벡터 검색           - heroine_scenarios   │
│                                           - sage_scenarios      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 저장소별 역할과 선택 근거

| 저장소 | 저장 데이터 | 선택 근거 |
|--------|------------|----------|
| **Redis** | 세션 상태, 최근 대화 20턴, 최근 사용 키워드 | **빠른 읽기/쓰기** 필요, 휘발성 데이터, TTL 자동 만료 |
| **Mem0** | User-NPC 대화 장기 기억 | **자동 중요 정보 추출**, 벡터 검색, 라이브러리가 알아서 요약/저장 |
| **pgvector** | NPC-NPC 대화, 시나리오 DB, NPC간 개별 기억 | **하이브리드 스코어링** 필요, SQL 조건 + 벡터 검색 조합 |

### 2.3 Redis 저장 구조

```python
# 키 형식: session:{player_id}:{npc_id}
# 예: session:10001:1 (플레이어 10001과 히로인 1의 세션)

session = {
    "player_id": 10001,
    "npc_id": 1,
    "conversation_buffer": [          # 최근 20턴 (빠른 컨텍스트 조회)
        {"role": "user", "content": "안녕?"},
        {"role": "assistant", "content": "...뭐야."}
    ],
    "recent_used_keywords": ["검", "훈련"],  # 최근 5턴 내 사용된 좋아하는 키워드
    "state": {
        "affection": 50,
        "sanity": 100,
        "memoryProgress": 30,
        "emotion": "neutral"
    },
    "last_active_at": "2025-12-01T10:00:00"
}

# TTL: 24시간 후 자동 삭제
# 왜 20턴만? → LLM 컨텍스트 윈도우 + 비용 효율성
# 왜 5턴 키워드? → 동일 키워드 반복 호감도 증가 방지
```

### 2.4 Mem0 저장 구조

```python
# user_id 형식: player_{player_id}_npc_{npc_id}
# 예: player_10001_npc_1

# 저장 시점: 매 대화마다 자동 저장
mem0_manager.add_memory(
    player_id=10001,
    npc_id=1,
    content="플레이어: 고양이 좋아해?\n히로인: ...그래, 좋아해."
)

# Mem0가 자동으로:
# 1. 중요한 정보 추출 ("플레이어는 고양이를 좋아함")
# 2. 벡터 임베딩 생성
# 3. 저장

# 검색 시
memories = mem0_manager.search_memory(
    player_id=10001,
    npc_id=1,
    query="고양이",  # 벡터 유사도로 검색
    limit=5
)
```

**Mem0를 선택한 이유:**
1. **자동 정보 추출**: 대화 전체가 아닌 핵심 정보만 저장
2. **중복 제거**: 같은 내용 반복 저장 방지
3. **벡터 검색 내장**: 별도 구현 없이 유사도 검색 가능
4. **Local/Cloud 선택**: API 키 없으면 로컬 pgvector 사용

---

## 3. 시나리오 임베딩 및 청킹

### 3.1 청킹 전략: 시나리오 단위 (Scenario-level Chunking)

```python
# src/scripts/seed_scenarios.py

HEROINE_SCENARIOS = [
    {
        "heroine_id": 1,
        "memory_progress": 10,
        "title": "레티아 회상 1: 귀족의 어린 시절",
        "content": """[회상 1: 귀족의 어린 시절]
■ 육하원칙
- 누가: 레티아 루크(당시 7세)가
- 언제: 창세기 약 14년 전...
...(전체 시나리오 텍스트)..."""
    },
    # ... 총 18개 (히로인 3명 × 6단계)
]
```

### 3.2 청킹 방식 선택 근거

| 방식 | 설명 | 채택 여부 |
|------|------|----------|
| **문장 단위** | 문장별로 분리 | ❌ 맥락 손실 |
| **고정 토큰** | 500토큰씩 분리 | ❌ 시나리오 중간에 잘림 |
| **시나리오 단위** | 하나의 회상 전체를 하나의 청크로 | ✅ **채택** |

**시나리오 단위를 선택한 이유:**
1. **맥락 보존**: 하나의 회상 단위가 완전한 스토리를 담고 있음
2. **해금 로직 연동**: `memory_progress` 필터링이 청크 단위와 일치
3. **검색 정확도**: "리라와의 만남"을 검색하면 해당 회상 전체가 반환됨

### 3.3 임베딩 방식

```python
# OpenAI text-embedding-3-small 사용 (1536차원)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 시나리오 전체 텍스트를 임베딩
embedding = embeddings.embed_query(scenario["content"])

# DB에 저장
sql = """
    INSERT INTO heroine_scenarios 
    (heroine_id, memory_progress, title, content, content_embedding)
    VALUES (:heroine_id, :memory_progress, :title, :content, :embedding::vector)
"""
```

**text-embedding-3-small 선택 이유:**
1. **비용 효율**: ada-002 대비 5배 저렴
2. **성능**: MTEB 벤치마크에서 ada-002보다 우수
3. **차원**: 1536차원으로 충분한 표현력

### 3.4 시나리오 검색 로직

```sql
-- 검색 시 memory_progress 필터링 + 벡터 유사도 정렬
SELECT id, content, memory_progress,
       1 - (content_embedding <=> query_embedding) AS similarity
FROM heroine_scenarios
WHERE heroine_id = 1
  AND memory_progress <= 50  -- 해금된 것만
ORDER BY content_embedding <=> query_embedding
LIMIT 2;
```

**해금 로직:**
- `memory_progress <= 현재 플레이어의 memoryProgress`인 시나리오만 검색
- NPC는 해금되지 않은 기억에 대해 "잘 모르겠어요..."로 응답

---

## 4. 메모리 시스템

### 4.1 메모리 타입 분류

```
┌─────────────────────────────────────────────────────────────────┐
│                    메모리 타입별 저장소                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [User-NPC 대화]                                                │
│  ├─ 저장소: Mem0                                                │
│  ├─ user_id: player_10001_npc_1                                │
│  └─ 내용: "플레이어는 고양이를 좋아한다"                         │
│                                                                 │
│  [NPC-NPC 개별 기억]                                            │
│  ├─ 저장소: agent_memories (PostgreSQL)                        │
│  ├─ agent_id: npc_1_about_2 (레티아가 루파메스에 대해)          │
│  ├─ memory_type: npc_memory                                    │
│  └─ 내용: "오늘 루파메스가 맛있는 쿠키를 줬다"                   │
│                                                                 │
│  [NPC-NPC 대화]                                                 │
│  ├─ 저장소: agent_memories (PostgreSQL)                        │
│  ├─ agent_id: conv_1_2 (레티아-루파메스 대화)                   │
│  ├─ memory_type: npc_conversation                              │
│  └─ 내용: "루파메스: 야, 뭐해?\n레티아: ...보면 몰라?"          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 agent_memories 테이블 구조

```sql
CREATE TABLE agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,      -- npc_1_about_2, conv_1_2 등
    memory_type VARCHAR(50) NOT NULL,    -- npc_memory, npc_conversation
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    importance_score INTEGER NOT NULL DEFAULT 5,  -- 1-10
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'          -- speakers, situation 등
);
```

### 4.3 메모리 저장 예시

```python
# NPC간 개별 기억 저장
agent_memory_manager.add_npc_memory(
    observer_id=1,           # 레티아가
    target_id=2,             # 루파메스에 대해
    content="오늘 같이 훈련했다. 의외로 진지한 모습이었다.",
    importance=7
)
# → agent_id: npc_1_about_2

# NPC간 대화 저장
agent_memory_manager.add_npc_conversation(
    npc1_id=1,
    npc2_id=2,
    content="[루파메스] (happy) 야, 레티아! 뭐해?\n[레티아] (neutral) ...보면 몰라?",
    importance=5,
    metadata={"situation": "길드 휴게실에서", "speakers": [1, 2]}
)
# → agent_id: conv_1_2
```

---

## 5. Retriever 구현

### 5.1 Retriever 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                    Retriever 아키텍처                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [의도 분류 결과]                                                │
│        │                                                         │
│        ├─── memory_recall ───▶ MemoryRetriever                  │
│        │                       ├─ Mem0 (User-NPC 대화)          │
│        │                       └─ pgvector (NPC-NPC 대화/기억)  │
│        │                                                         │
│        └─── scenario_inquiry ─▶ ScenarioRetriever               │
│                                 └─ pgvector (시나리오 DB)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 왜 LangChain Retriever를 사용하지 않았나?

| 비교 | LangChain Retriever | 직접 SQL 구현 |
|------|---------------------|--------------|
| **필터링** | 제한적 metadata 필터 | **SQL WHERE 자유로움** |
| **복합 조건** | 어려움 | **memory_progress <= X AND heroine_id = Y** |
| **하이브리드 스코어** | 별도 구현 필요 | **SQL 함수로 한 번에** |
| **다중 소스 검색** | Ensemble 복잡 | **UNION으로 간단 조합** |

**선택 이유:**
1. `memory_progress` 해금 조건 같은 **게임 로직 필터링** 필요
2. 최신성+중요도+관련성 **하이브리드 스코어링** 필요
3. Mem0 + pgvector **두 소스 동시 검색** 필요

### 5.3 시나리오 Retriever 구현

```python
# src/services/heroine_scenario_service.py

class HeroineScenarioService:
    """히로인 시나리오 검색 서비스 (Retriever 역할)"""
    
    def __init__(self):
        self.engine = create_engine(CONNECTION_URL)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    def search_scenarios(
        self,
        query: str,
        heroine_id: int,
        max_memory_progress: int,  # 해금 조건 필터
        limit: int = 3
    ) -> List[dict]:
        # 1. 쿼리를 벡터로 변환
        query_embedding = self.embeddings.embed_query(query)
        
        # 2. SQL로 필터링 + 벡터 검색 동시 수행
        sql = text("""
            SELECT id, content, memory_progress,
                   1 - (content_embedding <=> :embedding::vector) as similarity
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress <= :max_progress  -- 해금 조건
            ORDER BY content_embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        # 3. 결과 반환
        with self.engine.connect() as conn:
            result = conn.execute(sql, {...})
            return [{"content": row.content, "similarity": row.similarity} for row in result]
```

**핵심 포인트:**
- `<=>` 연산자: pgvector의 **코사인 거리** 계산
- `1 - distance`: 거리를 **유사도로 변환** (0~1)
- `memory_progress <= :max_progress`: **해금 조건 필터링**

### 5.4 메모리 Retriever 구현

```python
# src/agents/npc/heroine_agent.py

async def _retrieve_memory(self, state: HeroineState) -> str:
    """기억 검색 - 다중 소스 Retriever"""
    
    user_message = state["messages"][-1].content
    player_id = state["player_id"]
    npc_id = state["npc_id"]
    
    facts_parts = []
    
    # 1. Mem0에서 User-NPC 대화 기억 검색
    user_memories = mem0_manager.search_memory(
        player_id, npc_id, user_message, limit=3
    )
    if user_memories:
        facts_parts.append("[플레이어와의 기억]")
        for m in user_memories:
            facts_parts.append(f"- {m.get('memory', '')}")
    
    # 2. pgvector에서 NPC-NPC 대화 검색
    npc_conversations = heroine_heroine_agent.search_conversations(
        heroine_id=npc_id,
        query=user_message,
        top_k=2
    )
    if npc_conversations:
        facts_parts.append("\n[다른 히로인과의 대화 기억]")
        for conv in npc_conversations:
            facts_parts.append(f"- {conv['content'][:200]}...")
    
    # 3. pgvector에서 NPC간 개별 기억 검색
    for other_id in [1, 2, 3]:
        if other_id != npc_id:
            agent_id = f"npc_{npc_id}_about_{other_id}"
            npc_memories = agent_memory_manager.search_memories(
                agent_id=agent_id,
                query=user_message,
                top_k=1,
                memory_type="npc_memory"
            )
            # ...
    
    return "\n".join(facts_parts)
```

**핵심 포인트:**
- **3개 소스 동시 검색**: Mem0 + NPC대화 + NPC기억
- **소스별 라벨링**: `[플레이어와의 기억]`, `[다른 히로인과의 대화]`
- **결과 병합**: 문자열로 합쳐서 프롬프트에 주입

### 5.5 Retriever 비교표

| Retriever | 저장소 | 검색 방식 | 필터 조건 | 반환 형식 |
|-----------|--------|----------|----------|----------|
| **ScenarioRetriever** | pgvector | 코사인 유사도 | `heroine_id`, `memory_progress` | 시나리오 텍스트 |
| **MemoryRetriever (User)** | Mem0 | Mem0 내장 검색 | `player_id`, `npc_id` | 요약된 기억 |
| **MemoryRetriever (NPC)** | pgvector | 하이브리드 스코어링 | `agent_id`, `memory_type` | 기억/대화 텍스트 |

### 5.6 검색 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│              User 질문: "리라가 누구야?"                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 의도 분류: scenario_inquiry                                  │
│                    │                                             │
│                    ▼                                             │
│  2. ScenarioRetriever 호출                                       │
│     ┌─────────────────────────────────────┐                     │
│     │ query: "리라가 누구야?"              │                     │
│     │ heroine_id: 1 (레티아)              │                     │
│     │ max_memory_progress: 60             │                     │
│     └─────────────────────────────────────┘                     │
│                    │                                             │
│                    ▼                                             │
│  3. SQL 실행                                                     │
│     SELECT content FROM heroine_scenarios                        │
│     WHERE heroine_id = 1                                         │
│       AND memory_progress <= 60                                  │
│     ORDER BY embedding <=> query_embedding                       │
│                    │                                             │
│                    ▼                                             │
│  4. 결과: [회상 3: 굶주린 소녀와의 만남] (memory_progress=60)    │
│           → "리라는 레티아가 구해준 망각자 소녀..."              │
│                    │                                             │
│                    ▼                                             │
│  5. LLM 프롬프트에 주입 → 응답 생성                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 하이브리드 스코어링 검색

### 6.1 왜 하이브리드 스코어링인가?

단순 벡터 유사도만으로는 부족한 이유:
- **최신 기억이 더 중요**: 어제 대화가 1년 전 대화보다 관련성 높음
- **중요한 기억이 더 중요**: "트라우마 발생" > "날씨 이야기"
- **관련성도 중요**: 검색어와 의미적으로 가까운 기억

### 6.2 스코어링 공식

```
Total Score = (w_recency × Recency) + (w_importance × Importance) + (w_relevance × Relevance)
```

| 요소 | 계산 방식 | 범위 |
|------|----------|------|
| **Recency** (최신성) | `exp(-decay_rate × hours)` | 0~1 |
| **Importance** (중요도) | `importance_score / 10` | 0~1 |
| **Relevance** (관련성) | `1 - cosine_distance` | 0~1 |

### 6.3 SQL 구현

```sql
CREATE OR REPLACE FUNCTION search_memories_hybrid(
    p_agent_id VARCHAR(100),
    p_query_embedding VECTOR(1536),
    p_top_k INTEGER DEFAULT 5,
    p_w_recency FLOAT DEFAULT 1.0,
    p_w_importance FLOAT DEFAULT 1.0,
    p_w_relevance FLOAT DEFAULT 1.0,
    p_decay_rate FLOAT DEFAULT 0.01
)
RETURNS TABLE (...)
AS $$
BEGIN
    RETURN QUERY
    WITH scored AS (
        SELECT 
            m.*,
            -- Recency: 지수 감쇠 (3일이면 약 0.5)
            EXP(-p_decay_rate * EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 3600) AS recency,
            -- Importance: 0~1 정규화
            m.importance_score::FLOAT / 10.0 AS importance,
            -- Relevance: 코사인 유사도
            1 - (m.embedding <=> p_query_embedding) AS relevance
        FROM agent_memories m
        WHERE m.agent_id = p_agent_id
    )
    SELECT *,
        (p_w_recency * recency + p_w_importance * importance + p_w_relevance * relevance) AS total_score
    FROM scored
    ORDER BY total_score DESC
    LIMIT p_top_k;
END;
$$;
```

### 6.4 decay_rate 설정 근거

```python
# decay_rate = 0.01
# → 약 3일 후 recency ≈ 0.5
# → 약 1주일 후 recency ≈ 0.18

# 게임 특성상:
# - 하루 플레이 기준 최근 대화가 매우 중요
# - 1주일 전 대화는 중요도/관련성이 높아야 검색됨
```

---

## 7. LangGraph 기반 에이전트 구조

### 7.1 왜 LangGraph인가?

| 비교 | 단순 함수 체인 | LangGraph |
|------|---------------|-----------|
| 조건부 분기 | 복잡한 if-else | 선언적 라우팅 |
| 상태 관리 | 수동 전달 | TypedDict 자동 관리 |
| 디버깅 | 어려움 | 노드별 상태 확인 가능 |
| 확장성 | 코드 수정 필요 | 노드 추가만으로 확장 |

### 7.2 히로인 에이전트 노드 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                    HeroineAgent LangGraph                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  START                                                           │
│    │                                                             │
│    ▼                                                             │
│  [keyword_analyze]  ←── 좋아하는 키워드/트라우마 분석            │
│    │                     호감도 변화량 사전 계산                  │
│    ▼                                                             │
│  [router]  ←── 의도 분류 (LLM 호출)                              │
│    │            general / memory_recall / scenario_inquiry       │
│    │                                                             │
│    ├─── general ──────────────────────────────┐                 │
│    │                                           │                 │
│    ├─── memory_recall ───▶ [memory_retrieve]  │                 │
│    │                       Mem0 + NPC간 검색   │                 │
│    │                              │            │                 │
│    └─── scenario_inquiry ▶ [scenario_retrieve]│                 │
│                            시나리오 DB 검색    │                 │
│                                   │            │                 │
│                                   ▼            ▼                 │
│                            [generate]  ←── LLM 응답 생성         │
│                                   │                              │
│                                   ▼                              │
│                            [post_process]  ←── 상태 업데이트     │
│                                   │             Redis 저장       │
│                                   │             Mem0 저장        │
│                                   ▼                              │
│                                  END                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 의도 분류 기준

```python
# LLM이 분류하는 의도 타입
IntentType = Literal["general", "memory_recall", "scenario_inquiry"]

# general: 일상 대화, 감정 표현
#   예: "오늘 날씨 좋네", "기분 어때?"
#   → 검색 없이 바로 응답 생성

# memory_recall: 과거 대화/경험 회상
#   예: "지난번에 뭐라고 했더라?", "어제 무슨 얘기 했지?"
#   → Mem0에서 User-NPC 대화 검색
#   → agent_memories에서 NPC-NPC 대화 검색

# scenario_inquiry: NPC의 과거/비밀 질문
#   예: "네 과거가 궁금해", "기억나는 게 있어?"
#   → heroine_scenarios에서 해금된 시나리오 검색
```

---

## 8. 스트리밍/비스트리밍 동일 응답

### 8.1 문제 상황 (Before)

```
[Before]
스트리밍:    검색 없음 → LLM 호출 → 스트리밍 출력
비스트리밍:  검색 → LLM 호출 → JSON 반환

문제점:
1. 스트리밍은 기억/시나리오 없이 응답 → 내용이 다름
2. 스트리밍 후 상태 업데이트를 위해 LLM 재호출 → 2번 호출
```

### 8.2 해결 방법 (After)

```
[After]
공통: _prepare_context() → _build_full_prompt() → LLM 호출 → _update_state_after_response()

스트리밍:    context 준비 → 동일 프롬프트 → streaming_llm.astream() → 상태 업데이트
비스트리밍:  context 준비 → 동일 프롬프트 → llm.ainvoke() → 상태 업데이트
```

### 8.3 구현 코드

```python
# 공통 컨텍스트 준비
async def _prepare_context(self, state: HeroineState) -> Dict[str, Any]:
    # 1. 키워드 분석 (호감도 변화량)
    affection_delta, used_keyword = await self._analyze_keywords(state)
    
    # 2. 의도 분류
    intent = await self._classify_intent(state)
    
    # 3. 의도에 따른 검색
    retrieved_facts = "없음"
    unlocked_scenarios = "없음"
    
    if intent == "memory_recall":
        retrieved_facts = await self._retrieve_memory(state)
    elif intent == "scenario_inquiry":
        unlocked_scenarios = await self._retrieve_scenario(state)
    
    return {
        "affection_delta": affection_delta,
        "used_liked_keyword": used_keyword,
        "intent": intent,
        "retrieved_facts": retrieved_facts,
        "unlocked_scenarios": unlocked_scenarios
    }

# 스트리밍 응답 (동일 컨텍스트 사용)
async def generate_response_stream(self, state: HeroineState) -> AsyncIterator[str]:
    # 1. 컨텍스트 준비 (비스트리밍과 동일)
    context = await self._prepare_context(state)
    
    # 2. 동일한 프롬프트 생성
    prompt = self._build_full_prompt(state, context, for_streaming=True)
    
    # 3. 스트리밍으로 응답 생성 (LLM 1번만 호출)
    full_response = ""
    async for chunk in self.streaming_llm.astream(prompt):
        full_response += chunk.content
        yield chunk.content
    
    # 4. 상태 업데이트 (LLM 재호출 없이)
    await self._update_state_after_response(state, context, full_response, "neutral")
```

### 8.4 개선 효과

| 항목 | Before | After |
|------|--------|-------|
| LLM 호출 횟수 | 스트리밍 시 2번 | **1번** |
| 응답 내용 | 스트리밍/비스트리밍 다름 | **동일** |
| 기억/시나리오 반영 | 스트리밍은 미반영 | **둘 다 반영** |

---

## 9. 기술 선택 근거 총정리

### 9.1 저장소 선택

| 요구사항 | 선택 | 근거 |
|----------|------|------|
| 세션 상태 빠른 조회 | Redis | 인메모리, TTL 지원, JSON 저장 |
| User-NPC 대화 기억 | Mem0 | 자동 요약, 중복 제거, 벡터 검색 내장 |
| NPC간 기억 + 조건 검색 | pgvector | SQL 필터 + 벡터 검색 조합 가능 |

### 9.2 청킹 전략

| 요구사항 | 선택 | 근거 |
|----------|------|------|
| 시나리오 맥락 보존 | 시나리오 단위 청킹 | 하나의 회상이 완전한 스토리 |
| 해금 로직 연동 | memory_progress 필터 | 청크 = 해금 단위 |

### 9.3 검색 전략

| 요구사항 | 선택 | 근거 |
|----------|------|------|
| 다차원 관련성 평가 | 하이브리드 스코어링 | 최신성 + 중요도 + 유사도 조합 |
| 시간 가중치 | 지수 감쇠 (exp) | 자연스러운 망각 모델링 |

### 9.4 Retriever 구현

| 요구사항 | 선택 | 근거 |
|----------|------|------|
| 복합 필터 + 벡터 검색 | 직접 SQL 구현 | LangChain Retriever는 `memory_progress <= X` 같은 복합 조건 제한적 |
| 다중 소스 검색 | 개별 호출 후 병합 | Mem0 + pgvector 두 소스 동시 검색 필요 |
| 임베딩 모델 | text-embedding-3-small | 비용 효율적, 1536차원으로 충분 |
| 벡터 DB | pgvector (Supabase) | SQL 조건 + 벡터 검색 조합 가능 |

### 9.5 에이전트 구조

| 요구사항 | 선택 | 근거 |
|----------|------|------|
| 조건부 검색 | LangGraph | 선언적 라우팅, 상태 자동 관리 |
| 스트리밍 지원 | SSE | 실시간 타이핑 효과, HTTP 호환 |

### 9.6 응답 일관성

| 요구사항 | 선택 | 근거 |
|----------|------|------|
| 스트리밍/비스트리밍 동일 | 컨텍스트 선준비 | LLM 1번 호출, 동일 프롬프트 |

---

## 면접 예상 질문 및 답변

### Q1. 왜 Redis + Mem0 + pgvector 3가지를 다 사용했나요?

**A:** 각 저장소가 해결하는 문제가 다릅니다.
- **Redis**: 세션 상태처럼 자주 읽고 쓰는 휘발성 데이터에 적합합니다. TTL로 자동 만료도 가능합니다.
- **Mem0**: User-NPC 대화에서 중요 정보를 자동 추출해주고, 벡터 검색도 내장되어 있어 별도 구현이 필요 없습니다.
- **pgvector**: NPC간 기억은 `agent_id` 필터 + 벡터 유사도 검색이 동시에 필요한데, SQL의 조건절과 벡터 검색을 조합할 수 있어서 선택했습니다.

### Q2. 시나리오를 문장 단위로 나누지 않고 전체로 임베딩한 이유는?

**A:** 게임의 시나리오 구조 때문입니다. 하나의 "회상"은 육하원칙, 핵심 기억, NPC 응답 가이드가 모두 포함된 완결된 단위입니다. 문장 단위로 나누면 "레티아가 리라를 만났다"와 "리라가 죽었다"가 분리되어 맥락이 손실됩니다. 또한 `memory_progress`로 해금하는 단위가 회상 단위이므로, 청크와 해금 단위를 일치시켰습니다.

### Q3. 하이브리드 스코어링에서 가중치는 어떻게 정했나요?

**A:** 초기에는 모든 가중치를 1.0으로 설정하고, 실제 테스트하면서 조정했습니다. 게임 특성상 "어제 대화"가 "1년 전 대화"보다 중요하므로 최신성 가중치를 높일 수도 있고, "트라우마 언급"같은 중요 이벤트를 우선하려면 중요도 가중치를 높입니다. decay_rate=0.01은 약 3일 후 최신성이 절반이 되는 값으로, 일일 플레이 기준으로 적절했습니다.

### Q4. 스트리밍에서 LLM을 2번 호출했던 이유와 해결 방법은?

**A:** 원래는 스트리밍으로 텍스트를 출력한 후, 감정/상태 업데이트를 위해 비스트리밍으로 다시 호출했습니다. 이를 해결하기 위해 `_prepare_context()`에서 기억/시나리오 검색과 키워드 분석을 미리 수행하고, 그 결과를 스트리밍과 비스트리밍 모두에서 동일하게 사용했습니다. 상태 업데이트는 이미 계산된 `affection_delta`를 사용하므로 LLM 재호출이 필요 없습니다.

### Q5. 길드 시스템에서 User가 NPC에게 말 걸면 NPC-NPC 대화가 중단되는 로직은?

**A:** Redis에 `npc_conv:{player_id}` 키로 현재 진행 중인 NPC-NPC 대화 정보를 저장합니다. User가 `/heroine/chat` API를 호출하면, 먼저 `is_heroine_in_conversation()`으로 해당 히로인이 NPC 대화 중인지 확인하고, 대화 중이면 `stop_npc_conversation()`으로 중단합니다. 이후 User-히로인 대화가 진행됩니다.

### Q6. LangChain Retriever를 사용하지 않고 직접 SQL로 구현한 이유는?

**A:** 게임 로직에 필요한 **복합 조건 필터링** 때문입니다.
- 히로인 시나리오는 `heroine_id = 1 AND memory_progress <= 60` 같은 **해금 조건**이 필요합니다.
- NPC간 기억은 `agent_id = 'npc_1_about_2'` 필터 + **하이브리드 스코어링**(최신성+중요도+관련성)이 필요합니다.
- LangChain Retriever는 metadata 필터가 제한적이고, 하이브리드 스코어링을 구현하려면 별도 로직이 필요합니다.
- 직접 SQL로 구현하면 `WHERE`, `ORDER BY`, 사용자 정의 함수를 자유롭게 조합할 수 있습니다.

### Q7. Retriever에서 검색 결과를 프롬프트에 어떻게 주입했나요?

**A:** 의도(intent)에 따라 검색 소스가 달라지고, 결과를 **라벨링된 문자열**로 합쳐서 프롬프트의 특정 위치에 주입했습니다.

```
[장기 기억 (검색 결과)]
[플레이어와의 기억]
- 플레이어는 고양이를 좋아한다
[다른 히로인과의 대화 기억]
- 루파메스: 야, 레티아! ...
[루파메스에 대한 기억]
- 오늘 같이 훈련했다
```

이렇게 라벨링하면 LLM이 **어떤 소스에서 온 정보인지** 구분할 수 있고, 응답 생성 시 적절히 활용합니다.

### Q8. text-embedding-3-small과 large의 차이점과 선택 기준은?

**A:**
| 항목 | small | large |
|------|-------|-------|
| 기본 차원 | 1536 | 3072 |
| 품질 (MTEB) | 62.3% | 64.6% |
| 비용 | 기준 | 동일 (토큰 기반) |

- **small 선택 이유**: 시나리오 검색은 해금 조건으로 1차 필터링되므로 후보가 적고, 1536차원으로도 충분한 정확도가 나왔습니다.
- **large를 쓴다면**: 차원을 1024로 축소하면 small보다 품질이 좋으면서 검색 속도도 빨라집니다. OpenAI는 Matryoshka 학습으로 차원 축소 시에도 품질이 유지됩니다.

---

*이 문서는 NPC Agent System 개발 과정을 면접용으로 정리한 것입니다.*

