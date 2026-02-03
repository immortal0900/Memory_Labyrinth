# Docker & Supabase 배포 가이드

> 최종 업데이트: 2026-02-03

이 문서는 NPC 시스템의 로컬 Docker 환경 설정과 Supabase 프로덕션 배포 방법을 다룹니다.

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [로컬 Docker 환경](#2-로컬-docker-환경)
3. [Supabase 프로덕션 배포](#3-supabase-프로덕션-배포)
4. [데이터베이스 스키마](#4-데이터베이스-스키마)
5. [환경별 차이점](#5-환경별-차이점)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. 아키텍처 개요

### 1.1 인프라 구성

```mermaid
flowchart TB
    subgraph Local["로컬 개발 환경"]
        A[FastAPI Server<br/>localhost:8000]
        B[(ParadeDB<br/>Docker<br/>localhost:5435)]
        C[(Redis<br/>Docker<br/>localhost:6379)]
    end
    
    subgraph Production["프로덕션 환경"]
        D[FastAPI Server<br/>Cloud Run / EC2]
        E[(Supabase PostgreSQL<br/>pgvector + PGroonga)]
        F[(Redis Cloud<br/>Upstash / ElastiCache)]
    end
    
    A <--> B
    A <--> C
    D <--> E
    D <--> F
    
    style A fill:#fff3e0,color:#000
    style B fill:#e8f5e9,color:#000
    style C fill:#ffecb3,color:#000
    style D fill:#fff3e0,color:#000
    style E fill:#e8f5e9,color:#000
    style F fill:#ffecb3,color:#000
```

### 1.2 환경별 기술 스택

| 구분 | 로컬 (Docker) | 프로덕션 (Supabase) |
|-----|--------------|-------------------|
| PostgreSQL | ParadeDB (Docker) | Supabase PostgreSQL |
| Vector Search | pgvector (내장) | pgvector (확장) |
| Full-text Search | ParadeDB BM25 | PGroonga |
| Redis | redis:7-alpine | Upstash / ElastiCache |
| Port (PostgreSQL) | 5435 | 6543 (Supavisor) |

---

## 2. 로컬 Docker 환경

### 2.1 사전 요구사항

- Docker Desktop 설치
- Docker Compose v2.x
- Python ≥3.12
- uv (Python 패키지 매니저)

### 2.2 Docker Compose 구성

**파일 위치:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: paradedb/paradedb:latest
    container_name: game_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: game_db
      PGDATA: /var/lib/postgresql/data
    ports:
      - "5435:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    container_name: game_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  postgres_data:
  redis_data:
```

### 2.3 ParadeDB 선택 이유

| 기능 | 일반 PostgreSQL | ParadeDB |
|-----|----------------|----------|
| pgvector | 수동 설치 필요 | 기본 내장 |
| Full-text Search | 제한적 (영어 위주) | BM25 기반 고품질 |
| 한국어 검색 | 별도 설정 필요 | 기본 지원 |

> **ParadeDB**는 Elasticsearch 수준의 Full-text Search를 PostgreSQL 내에서 제공하는 확장판입니다.

### 2.4 실행 명령어

```bash
# 1. Docker 컨테이너 시작
docker compose up -d

# 2. 컨테이너 상태 확인
docker compose ps

# 3. PostgreSQL 로그 확인
docker compose logs postgres

# 4. Redis 로그 확인
docker compose logs redis

# 5. 컨테이너 중지
docker compose down

# 6. 볼륨 포함 완전 삭제 (데이터 초기화)
docker compose down -v
```

### 2.5 데이터베이스 접속

```bash
# Docker 컨테이너 내부 psql 접속
docker exec -it game_db psql -U postgres -d game_db

# 외부 클라이언트로 접속
psql -h localhost -p 5435 -U postgres -d game_db
```

### 2.6 환경 변수 설정 (로컬)

```bash
# .env 파일 생성
cp .env.example .env
```

**로컬 환경용 `.env` 설정:**

```bash
# PostgreSQL (로컬 Docker)
DATABASE_URL=postgresql://postgres:password@localhost:5435/game_db

# Redis (로컬 Docker)
REDIS_URL=redis://localhost:6379/0

# LLM API Keys
OPENAI_API_KEY=sk-proj-your-key
XAI_API_KEY=xai-your-key
```

### 2.7 초기 데이터 시딩

Docker 컨테이너가 시작되면 `init.sql`이 자동 실행됩니다. 추가 데이터 시딩이 필요한 경우:

```bash
# 시나리오 데이터 시딩
uv run python src/scripts/seed_scenarios.py
```

### 2.8 BM25 인덱스 생성 (선택)

데이터 시딩 후 Full-text Search 인덱스를 생성합니다:

```sql
-- 히로인 시나리오 BM25 인덱스
CALL paradedb.create_bm25(
    index_name => 'heroine_scenarios_bm25',
    table_name => 'heroine_scenarios',
    key_field => 'id',
    text_fields => paradedb.field('content') || paradedb.field('title')
);

-- 대현자 시나리오 BM25 인덱스
CALL paradedb.create_bm25(
    index_name => 'sage_scenarios_bm25',
    table_name => 'sage_scenarios',
    key_field => 'id',
    text_fields => paradedb.field('content') || paradedb.field('title')
);
```

---

## 3. Supabase 프로덕션 배포

### 3.1 Supabase 프로젝트 생성

1. [Supabase Dashboard](https://supabase.com/dashboard)에서 새 프로젝트 생성
2. Region: `Northeast Asia (ap-northeast-1)` 권장 (한국 기준)
3. Database Password 안전하게 보관

### 3.2 필수 확장 활성화

Supabase Dashboard → Database → Extensions에서 다음 확장을 활성화합니다:

| 확장 | 용도 | 활성화 방법 |
|-----|------|------------|
| **vector** | pgvector 벡터 검색 | Dashboard에서 검색 후 Enable |
| **pgroonga** | 한국어 Full-text Search | Dashboard에서 검색 후 Enable |

```sql
-- SQL Editor에서 확인
SELECT * FROM pg_extension WHERE extname IN ('vector', 'pgroonga');
```

### 3.3 연결 문자열 확인

Supabase Dashboard → Settings → Database → Connection string

**두 가지 연결 방식:**

| 방식 | 포트 | 용도 | 권장 |
|-----|------|------|-----|
| Direct | 5432 | 직접 연결 (마이그레이션) | 초기 설정 |
| **Supavisor** | 6543 | 커넥션 풀링 | **프로덕션** |

```bash
# 프로덕션 환경 변수 (Supavisor 사용)
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
```

### 3.4 테이블 생성

Supabase SQL Editor에서 다음 스키마를 순서대로 실행합니다:

#### 3.4.1 기본 테이블 (`init.sql`)

```sql
-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 세션 체크포인트
CREATE TABLE IF NOT EXISTS session_checkpoints (
    id SERIAL PRIMARY KEY,
    player_id TEXT NOT NULL,
    npc_id INT NOT NULL,
    conversation JSONB,
    summary_list JSONB DEFAULT '[]'::jsonb,
    state JSONB,
    last_chat_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkpoint_player_npc 
ON session_checkpoints(player_id, npc_id);

-- 히로인 시나리오
CREATE TABLE IF NOT EXISTS heroine_scenarios (
    id SERIAL PRIMARY KEY,
    heroine_id INT NOT NULL,
    memory_progress INT NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_heroine_scenarios_filter 
ON heroine_scenarios(heroine_id, memory_progress);

-- 대현자 시나리오
CREATE TABLE IF NOT EXISTS sage_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_level INT NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sage_level ON sage_scenarios(scenario_level);
```

#### 3.4.2 User Memory 테이블 (`user_memory_schema.sql`)

```sql
-- PGroonga 확장 활성화
CREATE EXTENSION IF NOT EXISTS pgroonga;

-- 장기 기억 테이블
CREATE TABLE user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id TEXT NOT NULL,
    heroine_id TEXT,
    speaker TEXT NOT NULL,
    subject TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT[],
    content_type TEXT DEFAULT 'fact',
    embedding vector(1536),
    importance INT DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    valid_at TIMESTAMPTZ DEFAULT NOW(),
    invalid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성
CREATE INDEX idx_user_memory_session 
ON user_memories (player_id, heroine_id, invalid_at);

CREATE INDEX idx_user_memory_vector 
ON user_memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_user_memory_pgroonga 
ON user_memories USING pgroonga (content);

CREATE INDEX ix_memories_content_keywords_pgroonga 
ON user_memories USING pgroonga (content, keywords);
```

#### 3.4.3 검색 함수

```sql
-- 히로인 시나리오 벡터 검색
CREATE OR REPLACE FUNCTION match_heroine_scenarios(
    query_embedding VECTOR(1536),
    p_heroine_id INT,
    p_max_progress INT,
    p_match_count INT
) RETURNS TABLE (id INT, content TEXT, memory_progress INT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        hs.id,
        hs.content,
        hs.memory_progress,
        1 - (hs.content_embedding <=> query_embedding) AS similarity
    FROM heroine_scenarios hs
    WHERE hs.heroine_id = p_heroine_id
      AND hs.memory_progress <= p_max_progress
    ORDER BY hs.content_embedding <=> query_embedding
    LIMIT p_match_count;
END;
$$;

-- 대현자 시나리오 벡터 검색
CREATE OR REPLACE FUNCTION match_sage_scenarios(
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

### 3.5 PGroonga 인덱스 (Supabase 전용)

```sql
-- 시나리오 Full-text Search 인덱스
CREATE INDEX ix_heroine_content_pgroonga 
ON heroine_scenarios USING pgroonga(content);

CREATE INDEX ix_heroine_title_pgroonga 
ON heroine_scenarios USING pgroonga(title);

CREATE INDEX ix_sage_content_pgroonga 
ON sage_scenarios USING pgroonga(content);

CREATE INDEX ix_sage_title_pgroonga 
ON sage_scenarios USING pgroonga(title);
```

### 3.6 환경 변수 설정 (프로덕션)

```bash
# Supabase PostgreSQL (Supavisor)
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres

# Redis (Upstash 예시)
REDIS_URL=rediss://default:[password]@[host].upstash.io:6379

# LLM API Keys
OPENAI_API_KEY=sk-proj-your-key
XAI_API_KEY=xai-your-key

# LangFuse (선택)
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

### 3.7 백엔드 서버 배포 옵션

#### Option A: Google Cloud Run

```bash
# Dockerfile 생성 필요
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Cloud Run 배포
gcloud run deploy npc-api \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

#### Option B: AWS EC2 / Lightsail

```bash
# 서버에서 직접 실행
nohup uv run uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
```

#### Option C: Railway / Render

- `pyproject.toml`과 `main.py`만 있으면 자동 감지
- 환경 변수는 대시보드에서 설정

---

## 4. 데이터베이스 스키마

### 4.1 테이블 목록

| 테이블 | 설명 | 주요 용도 |
|-------|------|----------|
| `session_checkpoints` | 세션 체크포인트 | 대화 기록 영구 저장 |
| `heroine_scenarios` | 히로인 시나리오 | 기억 해금 콘텐츠 |
| `sage_scenarios` | 대현자 시나리오 | 세계관 정보 |
| `user_memories` | 장기 기억 | 4요소 하이브리드 검색 |
| `heroine_memory_unlock_stages` | 기억 해금 단계 | 진척도별 콘텐츠 |
| `romance_docs` | 연애 문서 | 히로인별 로맨스 데이터 |

### 4.2 핵심 함수

| 함수 | 입력 | 출력 | 용도 |
|-----|------|------|------|
| `match_heroine_scenarios` | embedding, heroine_id, max_progress, count | id, content, similarity | 히로인 시나리오 검색 |
| `match_sage_scenarios` | embedding, max_level, count | id, content, similarity | 대현자 시나리오 검색 |
| `search_user_memories_hybrid` | player_id, heroine_id, query, embedding | 기억 목록 + 점수 | 4요소 하이브리드 검색 |
| `find_similar_memory` | player_id, heroine_id, embedding | 유사 기억 | 중복 검사 |

---

## 5. 환경별 차이점

### 5.1 Full-text Search 차이

| 환경 | 엔진 | 인덱스 생성 | 쿼리 문법 |
|-----|------|-----------|----------|
| **로컬 (ParadeDB)** | BM25 | `CALL paradedb.create_bm25(...)` | `@@@ 'query'` |
| **Supabase** | PGroonga | `USING pgroonga(column)` | `&@~ 'query'` |

### 5.2 코드 분기 처리

현재 코드는 PGroonga 기준으로 작성되어 있습니다. 로컬에서 ParadeDB BM25를 사용하려면 쿼리 수정이 필요합니다.

```python
# user_memory_schema.sql 내 PGroonga 쿼리
WHERE m.content &@~ p_query_text OR m.keywords &@ p_query_text

# ParadeDB BM25 쿼리 (로컬용, 필요시)
WHERE m.content @@@ p_query_text
```

### 5.3 연결 포트

| 환경 | PostgreSQL 포트 | Redis 포트 |
|-----|----------------|------------|
| 로컬 Docker | 5435 | 6379 |
| Supabase (Direct) | 5432 | - |
| Supabase (Supavisor) | 6543 | - |
| Upstash Redis | 6379 (TLS) | - |

---

## 6. 트러블슈팅

### 6.1 Docker 관련

#### 컨테이너 시작 실패

```bash
# 로그 확인
docker compose logs postgres

# 포트 충돌 확인
lsof -i :5435
lsof -i :6379

# 기존 볼륨 삭제 후 재시작
docker compose down -v
docker compose up -d
```

#### init.sql 실행 안됨

```bash
# 원인: 이미 볼륨에 데이터가 있으면 init.sql 무시됨
# 해결: 볼륨 삭제 후 재시작
docker compose down -v
docker compose up -d
```

### 6.2 Supabase 관련

#### pgvector 확장 오류

```sql
-- 확장 상태 확인
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 수동 활성화 (권한 필요)
CREATE EXTENSION IF NOT EXISTS vector;
```

#### PGroonga 인덱스 생성 실패

```sql
-- 확장 먼저 활성화
CREATE EXTENSION IF NOT EXISTS pgroonga;

-- 그 후 인덱스 생성
CREATE INDEX ... USING pgroonga(...);
```

#### 연결 타임아웃

```bash
# Supavisor (커넥션 풀링) 사용 권장
# Direct 연결은 동시 연결 수 제한 있음
DATABASE_URL=...pooler.supabase.com:6543/postgres
```

### 6.3 일반적인 문제

#### 환경 변수 로드 안됨

```bash
# .env 파일 위치 확인 (프로젝트 루트)
ls -la .env

# Python에서 확인
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('DATABASE_URL'))"
```

#### Redis 연결 실패

```bash
# 로컬 Redis 상태 확인
docker compose ps redis

# Redis CLI 접속
docker exec -it game_redis redis-cli ping
# 응답: PONG
```

---

## 부록

### A. 명령어 요약

```bash
# === 로컬 개발 ===
# Docker 시작/중지
docker compose up -d
docker compose down

# 서버 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# === 데이터베이스 ===
# Docker PostgreSQL 접속
docker exec -it game_db psql -U postgres -d game_db

# 시나리오 시딩
uv run python src/scripts/seed_scenarios.py

# === 테스트 ===
# NPC 페르소나 테스트
uv run pytest src/tests/npc/persona_eval/test_npc_persona.py -v
```

### B. 파일 구조

```
Memory_Labyrinth/
├── docker-compose.yml      # Docker Compose 설정
├── init.sql                # 초기 DB 스키마
├── .env.example            # 환경 변수 템플릿
├── .env                    # 실제 환경 변수 (gitignore)
├── main.py                 # FastAPI 엔트리포인트
├── src/
│   ├── db/
│   │   ├── config.py              # DB 연결 설정
│   │   ├── user_memory_schema.sql # User Memory 스키마
│   │   └── ...
│   └── scripts/
│       └── seed_scenarios.py      # 데이터 시딩
└── docs/
    ├── API_FLOW.md         # API 문서
    └── DOCKER.md           # 이 문서
```

### C. 참고 링크

- [ParadeDB 문서](https://docs.paradedb.com/)
- [Supabase pgvector 가이드](https://supabase.com/docs/guides/ai/vector-columns)
- [PGroonga 문서](https://pgroonga.github.io/)
- [Upstash Redis](https://upstash.com/)
