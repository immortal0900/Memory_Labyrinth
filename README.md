# Memory Labyrinth

![Python](https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-1C3C3C?logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF4154)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Langfuse](https://img.shields.io/badge/Langfuse-2.0-FF6F00?logo=langfuse&logoColor=white)
![DeepEval](https://img.shields.io/badge/DeepEval-0.1-8A2BE2?logo=python&logoColor=white)
---
# 목차

- [1. 프로젝트 소개](#1-프로젝트-소개)
- [2. 주요 기능](#2-주요-기능)
- [3. 기술 스택](#3-기술-스택)
- [4. 빠른 시작](#4-빠른-시작)
- [5. 환경 변수 설정](#5-환경-변수-설정)
- [6. 프로젝트 구조](#6-프로젝트-구조)
- [7. 아키텍처](#7-아키텍처)
- [8. API 엔드포인트](#8-api-엔드포인트)
- [9. 개발 가이드](#9-개발-가이드)
- [10. 코드 컨벤션](#10-코드-컨벤션)
- [11. 관련 문서](#11-관련-문서)
- [12. 문의](#12-문의)

---

# 1. 프로젝트 소개

[![Memory Labyrinth Demo](https://img.youtube.com/vi/EnXhQHyzOe4/maxresdefault.jpg)](https://www.youtube.com/watch?v=EnXhQHyzOe4)


- 프로젝트명 : MEMORIA LABYRINTH(기억의 던전)
- 장르 : 서브컬처 멀티플레이 로그라이크 게임
- 진행 기간 : 2025.11 ~ 2026.01 (2개월)
- 기획의도 : 기존게임의 문제점을 AI를 이용해서 타파하고자 함
    - 기존 서브컬쳐 게임 문제:
        - 선택지가 한정되어 있음 → 틀이 없는 대화
        - 낮은 자유도 → 높은 자유도
    - 기존 로그라이크 게임 문제:
        - 패턴화된 콘텐츠 → 변화하는 콘텐츠
        - 제작 비용의 한계 → 자동생성으로 효율적 개발
- 타겟 :
    - 히로인과 정서적 유대감을 원하는 유저
    - 끝없는 선택지를 원하는 유저
    - 매 순간 새로운 경험을 원하는 유저

---
# 2. 주요 기능

## NPC AI Agent

### 나를 기억하는 npc

[!["내가 좋아하는 과일이 뭔지 알아?"](https://img.youtube.com/vi/IE9S_yssxEg/sddefault.jpg)](https://youtu.be/IE9S_yssxEg)
- 의미없는 단순 일상대화가 저장될시 RAG 검색성능이 떨어지므로 장기기억엔 핵심만저장(하지만 전체 대화를 저장하는 check point 따로 존재)
- redis를 이용해 단기 기억을 구축하고 pgvector로 장기기억을 구축한뒤 단기기억을 요약할때 중요도와 저장시간을 기준으로 list 형태로 저장하여 쓰레기 데이터가 계속에서 요약에 들어오는 것을 방지함
- 기억 저장시 상위개념을 함께 저장하여 단어를 특정하지 않더라도 인간이 기억할때 범주를 나누듯 기억함 
- 중복되는 내용의 경우 과거의 내용을 비활성화하여 RAG검색시 데이터의 편향과 취향에 대한 혼란을 방지함
- 단순 의미 + 키워드 기반 하이브리드 검색에서 나아가 "시간"과 "중요도"까지 포함하여 인간처럼 최신의기억과 중요한 내용을 더 잘기억하도록 함

### 한정되지 않은 선택지
[!["길드에서는 살만해?"](https://img.youtube.com/vi/Dib6eY1wCRk/sddefault.jpg)](https://youtu.be/Dib6eY1wCRk)
- 의도분류를 통해 일상대화는 빠르게 장기기억으로 분류될시 그것과 맞는 기억만 검색해서 효율적임(RAG검색시)

### 호감도 증가에 따른 태도 변화와 기억해금
[![호감도 증가에 따른 태도변화와 기억해금](https://img.youtube.com/vi/dYacAGct7Go/sddefault.jpg)](https://youtu.be/dYacAGct7Go)
- 유저에게 해금되지 않은 기억은 말하지 않음
- 시나리오(히로인의 과거기억)로 분류될시 대충 말해도 기억을 잘 가져오도록 DB에 메타데이터를 함께 저장함
- 기억이 돌아왔다고 플레이어에게 말하게 되면 꼬리질문을 하게 될텐데 그에 대응하기 위해 의도분류프롬프트에 최근 3턴의 대화가 동적으로 들어오고 해금직후 5턴간 해금된 기억이 삽입됨

### NPC-NPC 대화 도중 끊어도 자연스럽게 기억 유지
[![NPC-NPC 대화](https://img.youtube.com/vi/MaeQMhavXXY/sddefault.jpg)](https://youtu.be/MaeQMhavXXY)
- 상황도 생성되고 상황에 따른 대화도 히로인의 기억진척도, 정신력, 좋아하는 단어, 최근대화 등에 따라 생성됨
- 전체대화를 클라이언트에 보내지만 플레이어입장에서는 끊은 이후는 일어나지 않은 일이므로 끊은 이후 턴을 체크포인트 장기기억 세션버퍼에서 삭제함

### 감정표현과 감정의 정도까지 표현 가능한 TTS
[![내 이름을 불러주는 NPC](https://img.youtube.com/vi/PmAdAOp1Soc/sddefault.jpg)](https://youtu.be/PmAdAOp1Soc)
- 미리 녹음된 소리가 아니므로 내 이름을 불러주는게 가능함(기존게임은 "자네" 혹은 "모험가"라고 불림)
- Typecast를 이용해 감정의 상태와 정도를 반영하는 목소리
- 동적 프롬프트와 CoT를 활용해 페르소나 일관성을 유지

## Dungeon AI Agent

### 던전이벤트
- 히로인의 기억 진척도(기억해금정도), 세계관 시나리오 해금정도에 따라 이벤트가 달라지며 자연어로 어떻게 할지 선택하고 선택에 따른 보상은 몬스터, 디버프, 버프, 아이템 등이 될 수 있음
- 생성 시간이 있어서 1층의 경우 1,2 층 동시에 생성되며 2층에 도달시 부터는 해당층에 도달했을때 다음층 이벤트가 생성됨 

### 던전밸런싱
- 보스방에 도착했을때(가장 강해졌을때)를 기준으로 다음층의 밸런싱이 진행됨
- 히로인의 남은 체력에 따라 스킬의 키워드, 무기의 키워드에 따른 몬스터가 다음층에 배치됨 (예시: "느린공격", "넉백"이라는 키워드를 가진 히로인 체력이 많을 경우 카운터 칠 수 있는 "빠른공격", "넉백저항", "원거리" 몬스터가 배정됨 )

## Fairy AI Agent

### 던전 길잡이 역할
- 던전 정보를 받아서 던전내에서 진행등에 대해 물어볼 수 있음(예시: "이제 어디로 가야돼?", "저 몬스터 공략법 알려줘", "다음방에 뭐가 있어?", "인벤토리에 뭐있어?" 등)

### STT로 던전내 상호작용 가능
- 음성으로 간편하게 상호작용 가능(예시: "불 켜줘", "OO무기로 바꿔줘", "제일 센 무기로 바꿔줘" 등)


---

# 3. 기술 스택

## AI Framework
- **LangChain** 0.3.0+ / **LangGraph** 0.2.0+ (State Management, Workflow)
- **X.AI Grok-4-1-fast-non-reasoning** (주요 LLM, 의도 분류 + 응답 생성)
- **OpenAI** (GPT-5-mini, text-embedding-3-small)
- **Groq Llama 3.3 70B** (Fairy 가이드용)
- **KoBERT** (한국어 의도 분류)
- **BGE-M3** (임베딩 기반 아이템 매칭)
- **Langfuse** 3.0.0+ (LLM 추적, 토큰 사용량/비용 분석)
- **DeepEval** 0.21+ (NPC 페르소나 평가)

## Backend
- **FastAPI** 0.115.0+ (API 서버)
- **Uvicorn** 0.32.0+ (ASGI 서버)
- **Pydantic** 2.0+ (Data Validation)
- **Python** 3.12+

## Database
- **PostgreSQL** (ParadeDB: pgvector + PGroonga)
  - `pgvector`: HNSW 인덱스 기반 벡터 검색
  - `PGroonga`: 한국어 형태소 분석 + BM25 키워드 검색
- **Redis** 7 (단기 메모리, 세션 관리, 24시간 TTL)
- **ChromaDB** 0.5.0+ (실험용 벡터 DB)

## Audio
- **Typecast API** (TTS 음성 합성)
- **OpenAI Whisper** (STT, 음성 인식)
- **Pydub** (오디오 파일 변환)
- **SoundFile** (WAV 파일 읽기/쓰기)

## Infrastructure
- **Docker Compose** (PostgreSQL + Redis)
- **uv** (Python 패키지 관리자)

---

# 4. 빠른 시작

## 사전 요구사항

- **Python** 3.12 이상
- **Docker** & **Docker Compose**
- **uv** 패키지 관리자

```bash
# uv 설치 (pip 사용)
pip install uv
```

## 설치 및 실행

```bash
# 1. 저장소 클론
git clone https://github.com/your-username/Memory_Labyrinth.git
cd Memory_Labyrinth

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 입력 (아래 "환경 변수 설정" 섹션 참조)

# 3. Docker 컨테이너 시작 (PostgreSQL + Redis)
docker-compose up -d

# 4. 데이터베이스 초기화
docker exec -i game_db psql -U postgres -d game_db < init.sql

# 5. 의존성 설치
uv sync

# 6. 서버 실행
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 서버 확인
# http://localhost:8000 접속
# API 문서: http://localhost:8000/docs
```

---

# 5. 환경 변수 설정

`.env` 파일에 다음 환경 변수를 설정하세요.

## 필수 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 키<br/>- 임베딩: text-embedding-3-small<br/>- 보조 LLM: GPT-4o-mini | `sk-proj-...` |
| `XAI_API_KEY` | X.AI API 키<br/>- 주요 LLM: grok-4-1-fast-non-reasoning<br/>- NPC 의도 분류 및 응답 생성 | `xai-...` |
| `DATABASE_URL` | PostgreSQL 연결 문자열<br/>- 로컬: `postgresql://postgres:password@localhost:5435/game_db`<br/>- Supabase: `postgresql://user:pass@host:6543/postgres` | `postgresql://postgres:password@localhost:5435/game_db` |
| `REDIS_URL` | Redis 연결 문자열<br/>- 단기 메모리, 세션 관리 | `redis://localhost:6379/0` |

## 선택 변수 (기능별)

### TTS 음성 합성

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `TYPECAST_API_KEY` | Typecast API 키<br/>- NPC 음성 생성<br/>- 없으면 텍스트만 반환 (음성 없음) | `your-typecast-api-key-here` |

### LLM 추적 (Langfuse)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `LANGFUSE_SECRET_KEY` | Langfuse Secret 키<br/>- 토큰 사용량, 비용, 지연시간 추적 | `sk-lf-...` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Public 키 | `pk-lf-...` |
| `LANGFUSE_HOST` | Langfuse 호스트 | `https://us.cloud.langfuse.com` |

### 추가 LLM 플랫폼

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `GROQ_API_KEY` | Groq API 키<br/>- Llama 3.3 70B 실행 플랫폼<br/>- Fairy 가이드 시스템에서 사용 | `gsk_...` |

---

# 6. 프로젝트 구조

```
Memory_Labyrinth/
├── src/
│   ├── agents/                    # LangGraph 기반 AI 에이전트
│   │   ├── npc/                   # NPC 대화 시스템 (17개 모듈)
│   │   │   ├── base_npc_agent.py           # 기본 NPC 클래스
│   │   │   ├── heroine_agent.py            # 히로인 에이전트
│   │   │   ├── sage_agent.py               # 대현자 에이전트
│   │   │   ├── heroine_heroine_agent.py    # NPC 간 대화
│   │   │   ├── memory_retriever.py         # 메모리 검색
│   │   │   ├── npc_conversation_manager.py # 대화 관리
│   │   │   ├── *_intent_classifier.py      # 의도 분류
│   │   │   ├── *_prompt_builder.py         # 프롬프트 생성
│   │   │   └── emotion_mapper.py           # 감정 매핑
│   │   ├── fairy/                 # 요정 가이드 AI
│   │   │   ├── dungeon/                    # 던전 내비게이션
│   │   │   ├── guild/                      # 길드 시스템
│   │   │   └── interaction/                # 상호작용 핸들러
│   │   └── dungeon/               # 던전 AI
│   │       ├── event/                      # 이벤트 생성
│   │       ├── monster/                    # 몬스터 전투 AI
│   │       └── super/                      # 통합 던전 에이전트
│   ├── api/                       # FastAPI 라우터
│   │   ├── npc_router.py                   # NPC 대화 API
│   │   ├── fairy_router.py                 # 요정 가이드 API
│   │   ├── dungeon_router.py               # 던전 API
│   │   └── common_router.py                # 공통 API
│   ├── db/                        # 데이터베이스 매니저
│   │   ├── user_memory_manager.py          # User-NPC 장기 기억
│   │   ├── npc_npc_memory_manager.py       # NPC-NPC 장기 기억
│   │   ├── session_checkpoint_manager.py   # 세션 체크포인트
│   │   ├── redis_manager.py                # Redis 단기 메모리
│   │   ├── RDBRepository.py                # PostgreSQL 저장소
│   │   └── VectorDBRepository.py           # 벡터 DB 저장소
│   ├── services/                  # 비즈니스 로직
│   │   ├── heroine_scenario_service.py     # 히로인 시나리오
│   │   └── sage_scenario_service.py        # 대현자 시나리오
│   ├── core/                      # 게임 데이터 DTO
│   │   └── game_dto/                       # Stat, Item, Dungeon 등
│   ├── prompts/                   # LLM 프롬프트 템플릿
│   │   ├── prompt_type/npc/                # NPC 프롬프트 (YAML)
│   │   ├── prompt_type/fairy/              # 요정 프롬프트 (YAML)
│   │   └── prompt_type/dungeon/            # 던전 프롬프트 (YAML)
│   ├── tools/                     # 유틸리티 도구
│   │   ├── audio/                          # TTS, STT
│   │   └── rag/                            # RAG 도구
│   ├── tests/                     # 테스트
│   │   ├── npc/persona_eval/               # DeepEval NPC 평가
│   │   └── share/                          # 공통 테스트
│   └── utils/                     # 공통 유틸리티
│       └── langfuse_tracker.py             # Langfuse 추적
├── main.py                        # FastAPI 앱 진입점
├── docker-compose.yml             # PostgreSQL + Redis
├── init.sql                       # DB 스키마 초기화
├── pyproject.toml                 # uv 의존성 관리 (55개)
├── .env.example                   # 환경 변수 템플릿
├── README.md                      # 이 문서
└── docs/                          # 문서
    ├── NPC_API_PROTOCOL.md                 # API 프로토콜
    ├── NPC_CONTEXT.md                      # 시스템 아키텍처
    ├── NEW_LONGMEMORY_SYSTEM.MD            # 메모리 시스템
    └── SESSION_CHECKPOINT_SUMMARY_SYSTEM.md # 세션 관리
```


---
# 7. 아키텍처

## NPC AI Agent 아키텍처

```mermaid
flowchart TB
    subgraph CLIENT["🎮 Unreal Engine Client"]
        A[게임 시작] --> B[길드 진입]
    end

    subgraph HEROINE_CHAT["👩 히로인 대화"]
        C["/api/npc/heroine/chat/sync/voice"]
        C --> C1[의도 분류 LLM]
        C1 --> C2{의도 타입}
        C2 -->|general| C3[바로 응답 생성]
        C2 -->|memory_recall| C4[User Memory 검색]
        C2 -->|scenario_inquiry| C5[시나리오 DB 검색]
        C2 -->|heroine_recall| C6[NPC-NPC 기억 검색]
        C3 & C4 & C5 & C6 --> C7[응답 생성 LLM]
        C7 --> C8[TTS 생성]
        C8 --> C9[text + emotion + audio_base64 반환]
    end

    subgraph SAGE_CHAT["🧙 대현자 대화"]
        D["/api/npc/sage/chat/sync/voice"]
        D --> D1[의도 분류 LLM]
        D1 --> D2{의도 타입}
        D2 -->|general| D3[바로 응답 생성]
        D2 -->|memory_recall| D4[User Memory 검색]
        D2 -->|worldview_inquiry| D5[세계관 DB 검색]
        D3 & D4 & D5 --> D6[응답 생성 LLM]
        D6 --> D7[TTS 생성]
        D7 --> D8[text + emotion + audio_base64 반환]
    end

    subgraph NPC_CONV["👥 NPC-NPC 대화"]
        E["/api/npc/heroine-conversation/generate/voice"]
        E --> E1[두 NPC 상태 조회]
        E1 --> E2[memoryProgress별 해금 기억 주입]
        E2 --> E3[멀티턴 대화 생성 LLM]
        E3 --> E4[각 턴별 TTS 생성]
        E4 --> E5[conversation 배열 + audio_base64 반환]
    end

    subgraph INTERRUPT["⚡ 인터럽트 처리"]
        F["/api/npc/heroine-conversation/interrupt"]
        F --> F1[interruptedTurn 이후 체크포인트 삭제]
        F1 --> F2[interruptedTurn 이후 장기기억 무효화]
        F2 --> F3[Redis 세션 버퍼 자르기]
        F3 --> F4[중단 시점까지만 기억 유지]
    end

    B --> C
    B --> D
    B --> E
    E5 -->|유저 개입시| F

    style CLIENT fill:#e1f5fe
    style HEROINE_CHAT fill:#fff3e0
    style SAGE_CHAT fill:#f3e5f5
    style NPC_CONV fill:#e8f5e9
    style INTERRUPT fill:#ffebee
```

## NPC Memory 아키텍처

```mermaid
flowchart TB
    subgraph Input["💬 대화 입력"]
        A["User: 나는 고양이 좋아해<br/>NPC: 저도 고양이 좋아해요"]
    end

    subgraph ShortTerm["⚡ 단기 기억 (Redis)"]
        direction TB
        R1["conversation_buffer<br/>(최근 20턴)"]
        R2["short_term_summary"]
        R3["session_state<br/>(호감도, 정신력, 기억진척도)"]
        R4["TTL: 24시간"]
    end

    subgraph FactExtract["🔍 Fact 추출 (LLM)"]
        direction TB
        F1["핵심만 추출"]
        F2["Speaker: user"]
        F3["Subject: user"]
        F4["Content: 고양이를 좋아함"]
        F5["Keywords: [고양이, 동물, 반려동물]"]
        F6["Importance: 7/10"]
    end

    subgraph DuplicateCheck["🔄 중복 검사"]
        direction TB
        D1{유사도 검사}
        D2["0.9 이상<br/>→ 즉시 중복 처리"]
        D3["0.55~0.9<br/>→ LLM 충돌 판단"]
        D4["0.55 미만<br/>→ 새로 저장"]
        D1 --> D2
        D1 --> D3
        D1 --> D4
    end

    subgraph LongTerm["💾 장기 기억 (PostgreSQL)"]
        direction TB
        subgraph UserMem["user_memories"]
            U1["player_id + heroine_id"]
            U2["content + embedding"]
            U3["valid_at / invalid_at<br/>(Bi-temporal)"]
        end
        subgraph NpcNpcMem["npc_npc_memories"]
            N1["player_id + heroine_id_1 + heroine_id_2"]
            N2["speaker + content"]
            N3["conversation_id 참조"]
        end
    end

    subgraph Checkpoint["📝 Checkpoint (PostgreSQL)"]
        direction TB
        subgraph SessionCP["session_checkpoints"]
            S1["매 턴 전체 대화 저장"]
            S2["summary_list<br/>(20턴마다 요약)"]
            S3["state 스냅샷"]
        end
        subgraph NpcNpcCP["npc_npc_checkpoints"]
            NC1["NPC-NPC 전체 대화"]
            NC2["interrupted_turn<br/>(끊긴 시점)"]
        end
    end

    subgraph Summary["📋 요약 시스템"]
        direction TB
        SM1["20턴마다 LLM 요약 생성"]
        SM2["중요도 1~5점 평가"]
        SM3["summary_list에 추가"]
        SM4["가지치기: 3시간+낮은중요도 삭제<br/>최대 5개 유지"]
    end

    subgraph HybridSearch["🔎 4요소 하이브리드 검색"]
        direction TB
        H1["Recency 15%<br/>exp(-days/30)"]
        H2["Importance 15%<br/>1~10 정규화"]
        H3["Relevance 50%<br/>pgvector 코사인"]
        H4["Keyword 20%<br/>PGroonga BM25"]
        H5["Score = 0.15R + 0.15I + 0.50V + 0.20K"]
    end

    A --> R1
    R1 -->|"매 턴"| FactExtract
    FactExtract --> DuplicateCheck
    DuplicateCheck -->|"충돌시 기존 invalid_at 설정"| LongTerm
    DuplicateCheck -->|"신규"| LongTerm

    A -->|"매 턴 전체 저장"| Checkpoint
    R1 -->|"20턴마다"| Summary
    Summary --> SessionCP

    LongTerm --> HybridSearch
    HybridSearch -->|"검색 결과"| A

    style Input fill:#e3f2fd,color:#000
    style ShortTerm fill:#fff3e0,color:#000
    style FactExtract fill:#f3e5f5,color:#000
    style DuplicateCheck fill:#ffebee,color:#000
    style LongTerm fill:#e8f5e9,color:#000
    style Checkpoint fill:#e0f7fa,color:#000
    style Summary fill:#fce4ec,color:#000
    style HybridSearch fill:#fff8e1,color:#000
```

### Memory 저장 흐름

| 단계 | 저장소 | 내용 | 특징 |
|-----|-------|------|------|
| **1. 단기 기억** | Redis | 최근 20턴 대화 버퍼 | TTL 24시간, 빠른 접근 |
| **2. Fact 추출** | LLM | 핵심만 추출 (SPO 구조) | Speaker/Subject/Content 분리 |
| **3. 중복 검사** | PostgreSQL | 유사도 0.55~0.9 → LLM 판단 | 취향 변화 시 기존 기억 무효화 |
| **4. 장기 기억** | PostgreSQL | user_memories / npc_npc_memories | Bi-temporal (valid_at/invalid_at) |
| **5. Checkpoint** | PostgreSQL | 전체 대화 + 요약 리스트 | 로그인 시 복원용 |
| **6. 요약** | LLM | 20턴마다 요약 생성 | 중요도 기반 가지치기 (최대 5개) |

### 검색 가중치

$$
Score = (0.15 \times Recency) + (0.15 \times Importance) + (0.50 \times Relevance) + (0.20 \times Keyword)
$$

| 요소 | 가중치 | 계산 방식 |
|-----|--------|----------|
| **Recency** | 15% | `exp(-days_since_created / 30)` - 최근일수록 높음 |
| **Importance** | 15% | `importance / 10` - LLM이 1~10점 평가 |
| **Relevance** | 50% | pgvector 코사인 유사도 |
| **Keyword** | 20% | PGroonga BM25 점수 (한국어 형태소 분석) |



## Dungeon AI Agent
```mermaid
flowchart TB
    C([🎮 클라이언트]) --> E1[" 던전 입장<br/>POST /entrance"]
    
    E1 --> A1["🤖 Event Agent<br/> 1층, 2층 동시에 이벤트 생성"]
    A1 --> P["🎮 해당층 진행"]
    
    P --> EV{이벤트 방<br/>입장}
    EV -->|YES| ES["이벤트 선택<br/>POST /event/select<br/>(선택지 입력 → 보상/패널티)"]
    ES --> P
    EV -->|NO| P
    
    P --> B1["보스방 입장<br/>POST /balance"]
    B1 --> A2["🤖 Monster Agent<br/>다음층 몬스터 밸런싱 조절<br/>"]
    A2 --> CL[" 해당층 클리어<br/>PUT /clear"]
    
    CL --> N["다음층 입장<br/>POST /nextfloor"]
    N --> A3["🤖 Event Agent<br/> 다다음층 이벤트 생성"]
    
    A3 -.-> |"🔄 반복"| B1
```

## Fairy AI Agent
```mermaid
flowchart LR
    subgraph Input["입력"]
        Q["질문:<br/>저 몬스터는 뭐야?<br/>무기도 교체해줘"]
    end

    subgraph IntentClassify["의도 분류"]
        direction TB
        IC0["모델: Groq<br/>레이턴시: 0.3s"]
        IC1["병렬 의도 분류"]
        IC2["몬스터 정보"]
        IC3["아이템 사용"]
        IC0 --- IC1
        IC1 --> IC2
        IC1 --> IC3
    end

    subgraph LocalModel["로컬 모델 추론"]
        direction TB
        LM0["모델: KoBERT, BGE-M3<br/>레이턴시: 0.1s"]
        LM1["병렬 모델 추론"]
        LM2["밝기 조절"]
        LM3["아이템 사용 판단"]
        LM0 --- LM1
        LM1 --> LM2
        LM1 --> LM3
    end

    subgraph RAG["병렬 검색"]
        RAG1["몬스터 정보 RAG"]
        RAG2["몬스터 정책"]
        RAG3["인벤토리 정보 조회"]
        RAG4["아이템 사용 정책"]
    end

    subgraph PromptBuild["프롬프트 생성"]
        PB["...(생략)...<br/>{몬스터 정보}<br/>{몬스터 정책}<br/>{아이템 사용 정책}<br/>...(생략)...<br/>질문:{질문}"]
    end

    subgraph ItemSelect["아이템 선택"]
        direction TB
        IS0["모델: Groq<br/>레이턴시: 0.3s"]
        IS["아이템 선택"]
        IS0 --- IS
    end

    subgraph Response["응답 생성"]
        direction TB
        R0["모델: Grok4 Fast<br/>레이턴시: 0.8~1.5s"]
        R["응답:<br/>저건 스켈레톤이야!<br/>가장 센 대검을 장착했어!"]
        R0 --- R
    end

    subgraph Cost["토큰 비용"]
        C1["(아이템 미사용)<br/>비용 없음"]
        C2["(아이템 사용)<br/>0.015 달러"]
    end

    subgraph Output["응답 포맷"]
        O["{아이템 사용 ID:20,<br/>던전 밝기: 미사용}"]
    end

    Q --> IntentClassify
    Q -->|"상호 작용"| LocalModel
    
    IntentClassify -->|"아이템 미사용"| RAG
    RAG --> PromptBuild
    PromptBuild --> Response
    
    LocalModel -->|"아이템 사용"| ItemSelect
    ItemSelect --> Output
    ItemSelect --> Cost
    
    Response --> Output

    style Q fill:#8B4513,color:#fff
    style IC0 fill:#555,color:#fff
    style IC1 fill:#333,color:#fff
    style IC2 fill:#333,color:#fff
    style IC3 fill:#333,color:#fff
    style LM0 fill:#555,color:#fff
    style LM1 fill:#333,color:#fff
    style LM2 fill:#333,color:#fff
    style LM3 fill:#333,color:#fff
    style RAG1 fill:#333,color:#fff
    style RAG2 fill:#333,color:#fff
    style RAG3 fill:#333,color:#fff
    style RAG4 fill:#333,color:#fff
    style PB fill:#333,color:#fff
    style IS0 fill:#555,color:#fff
    style IS fill:#333,color:#fff
    style R0 fill:#555,color:#fff
    style R fill:#D4A574,color:#000
    style O fill:#D4A574,color:#000
    style C1 fill:#D4A574,color:#000
    style C2 fill:#D4A574,color:#000
```

---

# 8. API 엔드포인트

## NPC API (`/api/npc/...`)

| Method | Endpoint | 설명 | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/login` | 게임 접속 시 세션 초기화<br/>(1회 호출) | `playerId`, `scenarioLevel`, `heroines[]` | `success`, `message` |
| POST | `/heroine/chat/sync` | 히로인 대화 (텍스트만) | `playerId`, `heroineId`, `text` | `text`, `emotion`, `affection`, `sanity`, `memoryProgress` |
| POST | `/heroine/chat/sync/voice` | 히로인 대화 (TTS 포함) | `playerId`, `heroineId`, `text` | `text`, `emotion`, `affection`, `audio_base64` |
| POST | `/sage/chat/sync/voice` | 대현자 대화 (TTS 포함) | `playerId`, `text` | `text`, `emotion`, `scenarioLevel`, `audio_base64` |
| POST | `/heroine-conversation/generate/voice` | NPC 간 대화 생성 (TTS) | `playerId`, `heroine1Id`, `heroine2Id`, `turnCount` | `conversation[]`, `audio_base64` (per turn) |
| POST | `/heroine-conversation/interrupt` | NPC 간 대화 인터럽트<br/>(User 개입 시) | `playerId`, `conversationId`, `interruptedTurn` | `success`, `message`, `updated_memories` |
| GET | `/session/{player_id}/{npc_id}` | 세션 정보 조회 (디버그용) | - | `conversation_buffer`, `state`, `turn_count` |

**상세 문서**: [API_FLOW.md](docs/API_FLOW.md)

---

## Dungeon API (`/api/dungeon/...`)

| Method | Endpoint | 설명 | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/entrance` | 던전 진입<br/>(raw_map 제출) | `playerIds[]`, `heroineIds[]`, `rawMaps[]` | `dungeonIds[]`, `events[]` |
| POST | `/balance` | AI 밸런싱 실행<br/>(이벤트 + 몬스터) | `firstPlayerId`, `playerDataList[]`, `monsterDb` | `balancedMap`, `summaryInfo`, `events`, `monsterStats` |
| PUT | `/clear` | 현재 층 클리어 | `playerIds[]` | `success`, `balancedMap` (다음 층용) |
| POST | `/event/select` | 이벤트 선택지 처리 | `firstPlayerId`, `roomId`, `choice` | `success`, `rewards[]`, `penalties[]` |
| POST | `/nextfloor` | 다음 층 진입 | `playerIds[]`, `heroineIds[]`, `rawMap` | `dungeonId`, `event` |

**상세 문서**: [DUNGEON_API_SPECIFICATION_V2.md](docs/DUNGEON_API_SPECIFICATION_V2.md)

---

## Fairy API (`/api/fairy/...`)

| Method | Endpoint | 설명 | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/dungeon/talk` | 던전 가이드 대화 | `dungeonPlayer`, `question`, `targetMonsterIds[]`, `nextRoomIds[]` | `responseText` |
| POST | `/dungeon/interaction` | 던전 상호작용<br/>(아이템, 조명) | `dungeonPlayer`, `question` | `useItemId`, `roomLight` (0/1/2) |
| POST | `/guild/talk` | 길드 가이드 대화 | `playerId`, `heroine_id`, `memory_progress`, `affection`, `sanity`, `question` | `responseText` |

**상세 문서**: [FAIRY_API_PROTOCOL.md](docs/FAIRY_API_PROTOCOL.md)

---

# 9. 개발 가이드

## 테스트 실행

```bash
# NPC 페르소나 평가 (DeepEval)
uv run pytest src/tests/npc/persona_eval/test_npc_persona.py -v

# 전체 테스트
uv run pytest src/tests/ -v
```

---

## DeepEval 페르소나 평가 메트릭

NPC 대화 시스템은 **4개의 커스텀 메트릭**으로 페르소나 일관성을 평가합니다.

### 메트릭 구성

| 메트릭 | 임계값 | 설명 | 주요 테스트 유형 |
|--------|--------|------|------------------|
| **PersonaConsistency** | 70% | 캐릭터 성격 일관성 (말투, 성격, 선호도 유지) | general, persona_test |
| **RoleAdherence** | 90% | 롤플레이 유지 (AI 여부 숨김, 캐릭터 몰입) | persona_break |
| **KnowledgeBoundary** | 80% | 지식 경계 준수 (해금되지 않은 정보 차단) | knowledge_boundary, memory |
| **ConversationMemory** | 80% | 대화 맥락 기억 (이전 대화 내용 참조) | multi_turn_memory |

### 테스트 유형 구성 (6가지)

| 테스트 유형 | 비율 | 주요 메트릭 (60%) | 보조 메트릭 (40% 균등) | 설명 |
|------------|------|-------------------|----------------------|------|
| **general** | 20% | PersonaConsistency | RoleAdherence, KnowledgeBoundary | 일반 대화 (기분, 취향) |
| **persona_test** | 20% | PersonaConsistency | RoleAdherence | 트라우마/성격 테스트 |
| **persona_break** | 20% | RoleAdherence | PersonaConsistency, KnowledgeBoundary | AI 여부 확인 시도 |
| **memory** | 20% | KnowledgeBoundary | PersonaConsistency | 캐릭터 과거 기억 해금도 |
| **knowledge_boundary** | 10% | KnowledgeBoundary | PersonaConsistency, RoleAdherence | 알 수 없는 지식 차단 |
| **multi_turn_memory** | 10% | ConversationMemory | PersonaConsistency, RoleAdherence | 대화 맥락 기억 |

### 테스트 예시

```bash
# 레티아(히로인 1) 페르소나 테스트 실행
uv run pytest src/tests/npc/persona_eval/test_npc_persona.py::test_letia_persona -v

# 전체 히로인 페르소나 평가
uv run pytest src/tests/npc/persona_eval/ -v

# 특정 테스트 유형만 실행
uv run pytest src/tests/npc/persona_eval/ -k "persona_break" -v
```


## 데이터베이스 관리

**초기화 (모든 데이터 삭제):**

```bash
docker-compose down -v
docker-compose up -d
# init.sql이 자동 실행되어 테이블 재생성
```

**시나리오 시딩:**

```bash
# 히로인 시나리오 데이터 삽입
uv run python src/scripts/seed_scenarios.py
```

**Langfuse 토큰 분석:**

```bash
# 토큰 사용량, 비용 분석
uv run python src/scripts/analyze_langfuse_tokens.py
```

---

# 10. 코드 컨벤션

- **[CONVENTION.md](CONVENTION.md)** 참조
- **SOLID 원칙** 준수
- **Docstring**: Google Style
- **Type Hints** 필수

**예시:**

```python
def calculate_affection_change(
    user_message: str,
    liked_keywords: List[str],
    trauma_keywords: List[str]
) -> int:
    """키워드 기반 호감도 변화량을 계산합니다.

    Args:
        user_message: 사용자 메시지
        liked_keywords: 좋아하는 키워드 리스트
        trauma_keywords: 트라우마 키워드 리스트

    Returns:
        호감도 변화량 (양수: 증가, 음수: 감소)
    """
    change = 0
    for keyword in liked_keywords:
        if keyword in user_message:
            change += 10
    for keyword in trauma_keywords:
        if keyword in user_message:
            change -= 10
    return change
```

---

# 11. 관련 문서

## API 프로토콜
- [API_FLOW.md](docs/NPC_API_PROTOCOL.md): NPC 대화 API 상세 (Request/Response 예시, 호출 흐름도)
- [FAIRY_API_PROTOCOL.md](docs/FAIRY_API_PROTOCOL.md): Fairy 가이드 API 상세 (추정)
- [DUNGEON_API_SPECIFICATION_V2.md](docs/DUNGEON_API_SPECIFICATION_V2.md): Dungeon 생성 API 상세

## 기술 문서
- [NPC_CONTEXT.md](docs/NPC_CONTEXT.md): NPC 시스템 아키텍처
- [핵심기술 정리.md](docs/핵심기술%20정리.md): 10가지 핵심 기술 선택 이유 및 구현 방법
- [NPC_DATA_FLOW.md](docs/NPC_DATA_FLOW.md): 데이터 흐름도
- [CONVENTION.md](CONVENTION.md): 코드 컨벤션

## 추가 리소스

- [LangChain 공식 문서](https://python.langchain.com/)
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PGroonga 공식 문서](https://pgroonga.github.io/)
- [langfuse 공식 문서](https://langfuse.com/docs)
- [deepeval 공식 문서](https://deepeval.com/docs/getting-started)
---

## 12. 문의
- **Email**: immortal0900@gmail.com