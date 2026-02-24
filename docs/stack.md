# Memory Labyrinth | Tech Stack

> **Stateful Multi-Agent System** — LangGraph 기반 상태 관리 NPC Agent, Hybrid RAG Search, 이중 메모리 아키텍처를 갖춘 AI Game Backend

---

## Agentic AI Core

![LangChain](https://img.shields.io/badge/LangChain-v0.3-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-v0.2-FF6F00?style=for-the-badge&logo=langchain&logoColor=white)

| Technology | Role in Project |
|:----------:|:----------------|
| **LangChain** | LLM Orchestration, RAG Pipeline, Embedding 통합 프레임워크 |
| **LangGraph** | NPC Agent의 Graph 기반 State Machine 워크플로우, Multi-step 대화 흐름 제어 |

---

## LLM Integration — Multi-Provider

![xAI](https://img.shields.io/badge/xAI_Grok-000000?style=for-the-badge&logo=x&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic_Claude-191919?style=for-the-badge&logo=anthropic&logoColor=white)
![Google](https://img.shields.io/badge/Google_Gemini-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)

| Model | Purpose |
|:-----:|:--------|
| **Grok-4-1 (xAI)** | Primary — NPC 의도 분류(Intent Classification) 및 응답 생성 |
| **GPT-5-mini (OpenAI)** | Fact Extraction, Duplicate Detection |
| **text-embedding-3-small** | Primary Embedding Model (Vector Search) |

---

## RAG & Hybrid Search Pipeline

![pgvector](https://img.shields.io/badge/pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![PGroonga](https://img.shields.io/badge/PGroonga-FF6600?style=for-the-badge&logo=postgresql&logoColor=white)


| Component | Role |
|:---------:|:-----|
| **pgvector** | Vector Similarity Search (Cosine Distance) |
| **PGroonga** | 한국어 형태소 분석 기반 Full-text Search |
| **Hybrid Scoring** | Vector + Keyword + Recency + Importance 4중 가중 결합 |


---

## Memory Architecture

![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

| Layer | Technology | Description |
|:-----:|:----------:|:------------|
| **Short-term** | Redis | 세션 기반 대화 컨텍스트 (24h TTL), 실시간 상태 관리 |
| **Long-term** | PostgreSQL + pgvector | 의미 기반 장기 기억 저장, Fact 추출 및 중복 탐지 후 영구 보관 |

---

## Observability & Evaluation

![Langfuse](https://img.shields.io/badge/Langfuse-000000?style=for-the-badge&logoColor=white)
![DeepEval](https://img.shields.io/badge/DeepEval-4A90D9?style=for-the-badge&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

| Tool | Purpose |
|:----:|:--------|
| **Langfuse** | LLM 호출 Tracing, 토큰 사용량 모니터링, 비용 분석 대시보드 |
| **DeepEval** | NPC Persona 일관성 평가 (Automated LLM Evaluation) |
| **pytest** | 단위/통합 테스트 프레임워크 |

---

## Multimodal — Audio Processing

![Whisper](https://img.shields.io/badge/OpenAI_Whisper-412991?style=for-the-badge&logo=openai&logoColor=white)
![Typecast](https://img.shields.io/badge/Typecast_TTS-FF4081?style=for-the-badge&logoColor=white)

| Technology | Role |
|:----------:|:-----|
| **OpenAI Whisper** | Speech-to-Text (한국어 음성 인식) |
| **Typecast API** | Text-to-Speech (NPC 캐릭터별 음성 합성) |

---

## Backend & API

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic_v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy_2.0-D71F00?style=for-the-badge&logoColor=white)


| Technology | Role |
|:----------:|:-----|
| **FastAPI** | Async REST API 서버 (ASGI) |
| **Pydantic v2** | Request/Response 데이터 Validation & Serialization |
| **SQLAlchemy 2.0** | ORM 및 Database Connection Pool 관리 |
| **Uvicorn** | Production ASGI Server |

---

## DevOps & Infrastructure

![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white)

| Technology | Role |
|:----------:|:-----|
| **Docker Compose** | PostgreSQL(ParadeDB) + Redis 컨테이너 오케스트레이션 |
| **GitHub Actions** | CI/CD — NPC Persona 자동 평가 파이프라인 |
| **uv** | 고속 Python 패키지 매니저 (pip 대체) |
| **Supabase** | Production PostgreSQL 호스팅 |
