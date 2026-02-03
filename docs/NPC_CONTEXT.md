# NPC 대화 기능 종합 정리

## 1. 시스템 아키텍처 개요

- **Core Framework:** LangGraph (State management, Workflow)
    
- **API Interface:** FastAPI (Streaming & Sync Support)
    
- **Database:**
    
    - **Short-term:** Redis (최근 20턴 대화 버퍼, 상태값, 24시간 TTL)
        
    - **Long-term:** Supabase PostgreSQL (pgvector + PGroonga)
        
- **LLM:** 
	- 의도분류 : "grok-4-fast-non-reasoning"
	- 답변생성 : "grok-4-fast-non-reasoning"
	- 중복감지 : "GPT5-mini"
	    
- **TTS:** Typecast API (WAV -> Base64 encoding)
    

# 2. 메모리 시스템 (Memory System)

단순 벡터 검색의 한계를 극복하기 위해 **하이브리드 검색**과 **구조화된 저장 방식**을 채택했습니다.

## **long-term memory**Mem0 대체 및 자체 구축

초기에는 `Mem0` 라이브러리가 locomo 벤치마크 결과  OpenAI의 메모리와 비교했을 때 응답 정확도가 26% 더 높았고langmem(langchain), MemGPT, A-Mem 보다 우수한 성능을 보여서 `Mem0` 라이브러리를 고려했으나 아래의 이유로 **PostgreSQL 기반 자체 하이브리드 시스템**으로 전환했습니다.

### 메타데이터의 부재 (Contextual Ambiguity):
- Mem0는 단순히 텍스트를 저장하므로 `Speaker`(화자)와 `Subject`(대상)를 명확히 구분하기 어렵습니다. "누가 누구에 대해 말한 것인지" 불분명하여 NPC가 유저의 정보를 자신의 정보로 착각하는 등의 할루시네이션 위험이 있었습니다.
        
### 검색 로직의 한계 (Search Flexibility):
- Mem0는 벡터 유사도(Relevance) 중심입니다. 
- 하지만 대화 시스템에서는 **최신성(Recency)**, **중요도(Importance)**, **키워드 일치(Keyword)** 또한 복합적으로 고려되어야 자연스러운 회상이 가능합니다.
### 속도
- 같은 "grok-4-fast-non-reasoning" 모델을 활용할 경우 자체 하이브리드 시스템에서 속도가 3초 초반대에서 2~3초 대로 단축됨

# A. 저장 방식 (Fact Extraction)

- 장기기억은 RAG로 가져오며, playerId별로 저장됩니다.

## USER-NPC 대화
- **테이블:** `user_memories`
	- 기억검색 테이블
- **구조:** 
player_id, heroine_id, Speaker(화자), Subject(대상), Content
(내용), **keywords(TEXT[])**, Content_type(취향/사건/평가 등), importance(중요도), created_at
(생성시간), valid_at(활성화된 시간), invalid_at(비활성화된 시간), 
updated_at(수정시간: 임베딩 재생성이나 중요도 재평가시)
- **특징:**
    - LLM이 content+keywords(JSON) 추출: 주어/목적어/관계/주제 + **상위 카테고리** 포함
    - 임베딩 입력: `"content (Keywords: ...)"`로 결합 후 생성해 의미 확장
    - keywords 배열을 그대로 저장, PGroonga 인덱스 `(content, keywords)`로 검색
    - **취향 변화 감지:** 새로운 취향이 들어오면 기존 데이터(`invalid_at`) 무효화 최신성 유지지
    - **중복 방지:** 임베딩 유사도 0.55 이상 시 LLM 판단, 0.9 이상 시 무조건 중복 처리

## NPC-NPC 대화
- **테이블:** `npc_npc_checkpoints`
	- NPC 간 대화 전체 기록 저장 (인터럽트 처리용)
	- conversation 컬럼에 JSON 형식으로 전체 대화 저장
- **테이블:** `npc_npc_memories`
	- NPC 간 장기기억 (Fact 추출 후 저장)
	- speaker_id, subject_id 포함하여 4요소 하이브리드 검색 지원
        
- **테이블:** `session_checkpoint`
	- 체크포인트에 저장되는 대화 원문 저장
	- state(상태) 정보 저장
	- 요약 목록(summary_list) 저장
# B. 검색 알고리즘 (Hybrid Retrieval)

4가지 요소를 가중합산하여 기억을 인출합니다.

$$Score = (w_{recency} \times Recency) + (w_{importance} \times Importance) + (w_{relevance} \times Relevance) + (w_{keyword} \times Keyword)$$

- **Recency (최신성):** 지수 감쇠 함수 적용 (exp(-days/30)), 가중치 0.15.
- **Importance (중요도):** 1~10점 척도 정규화 (importance/10), 가중치 0.15.
- **Relevance (관련도):** `pgvector` (Cosine Similarity), 가중치 0.50.
- **Keyword (키워드):** `PGroonga` (content+keywords BM25, 한국어 형태소 검색 최적화), 가중치 0.20.

**기본 가중치:**
- Recency: 0.15
- Importance: 0.15
- Relevance: 0.50
- Keyword: 0.20
    
- 검색대상
	- `user_memories`: USER-NPC 대화 기억
	- `npc_npc_memories`: NPC-NPC 대화 기억
# C. 시간 기반 쿼리

사용자 발화에 시간 관련 키워드("어제", "최근", "전부")가 포함될 경우, 벡터 검색 대신 특정 SQL 함수를 호출하여 정확도를 높입니다.

1. "어제" -> `get_memories_days_ago(1)`
2. "그제/그저께" -> `get_memories_days_ago(2)`
3. "N일 전" -> `get_memories_days_ago(N)`
4. "최근/요즘/며칠" -> `get_recent_memories(7)`
5. "전부/다/모든/기억하는 거" -> `get_valid_memories`
6. "N월 N일" -> `get_memories_at_point`
7. "지지난주 X요일" -> `get_memories_at_point`
8. "지난주 X요일" -> `get_memories_at_point` 
9. 기본 -> `search_memory_sync` (하이브리드 검색)

# D. 호감도 및 기억 진척도

## 호감도(affection)의 변화에 따른 기억 해금
- 호감도(affection)가 기억진척도(memoryProgress)와 같거나 높을때만 호감도(affection)가 오를때 기억진척도(memoryProgress)가 오른다.
- 기억진척도 임계값 돌파시(10, 50, 60, 70, 80, 100) 해당 기억 DB에 접근할 수 있음(RAG로 가져와 프롬프트에 삽입함)
- 기억진척도 임계점에 돌파하면 원래는 scenario DB로 분류하지 않을 내용(예시: "그때 그 숲엔 왜간거야?")을 의도분류시에 삽입되는 최근대화 3턴(1턴: USER-NPC대화 1쌍)과 최근해금된 메모리 정보(직후 5턴까지 유효)로 scenario로 분류되게 만들어서 꼬리질문에 대답 가능하게 됨      


## 호감도(affection)의 변화에 따른 태도 변화
- 0-29 / 30-59 / 60-89 구간 별 태도 변화
- 정신력(sanity) 0일시 우울 모드

#  E. 단기기억
- 프롬프트에 포함
- 최근 5턴의 대화 프롬프트에 삽입
- 요약 대화 프롬프트에 삽입

## 단기기억 요약생성 방식
### 기존 요약의 문제점
- 모든 내용을 요약하다 보면 내용의 소실이 발생하고, 결국 알 수 없는 예전의 쓰레기 데이터가 누적되고, 컨텍스트창을 낭비하게된다
- 따라서 비워줘야 하는데 한벙에 다 비우면 완전히 비운 타이밍에는 요약이 없는 상태로 대화를 하게 된다.

### 해결방법
- 대화 턴 10턴 이상일때 첫 요약 생성(1턴: USER-NPC 대화 1쌍)
- 이후 20턴 이상일때 요약 생성 or 1시간 이상일때 요약 생성 : 20턴만 고려하면 수십일 지나도 요약 안생길 수 있음/ 1시간 이상만 고려하면 너무 많은 대화가 쌓인 뒤 요약이 생성될 가능성 있음
- 요약은 시간순 리스트로 관리되며 5개 초과일시 OR 3시간 이상 경과하고 중요도 2 이하인 경우 삭제
- 단 중요도가 같이 저장되어 중요도가 가장 높으면 가장 높은 항목의 중요도를 1감소 하고 그 다음 오래된거 삭제

---

# 3. 대화 파이프라인 (Conversation Pipeline)

사용자가 메시지를 보낼 때 NPC가 응답하는 과정

### Step 1: 입력 분석 및 상태 업데이트

- **키워드 분석:** Python 코드로 '좋아하는 단어(+)'와 '트라우마 단어(-)'를 감지하여 `Affection`(호감도) 및 `Sanity`(정신력) 즉시 반영.
    
- **기억 해금 감지:** `MemoryProgress`가 특정 임계값(10, 50, 60, 70, 80, 100 등)을 넘으면 `newly_unlocked_scenario`를 활성화.
    

### Step 2: 의도 분류 (Intent Classification)

- LLM을 통해 사용자 발화의 의도를 분류합니다. 히로인과 대현자는 서로 다른 의도 분류를 사용합니다.
- **최적화:** `max_tokens=20` 설정으로 속도 최적화.

**히로인 의도 분류 (4가지):**
1. **General:** 일상 대화 (검색 최소화).
    
2. **Memory_recall:** 과거 대화 회상 ("우리 전에 뭐 먹었지?", "루파메스를 어떻게 생각해?").
    
3. **Scenario_inquiry:** 설정/과거/비밀 질문 ("고향이 어디야?", "그때 숲에 왜 갔어?", "최근에 돌아온 기억").
    
    - 꼬리 질문 처리: 최근 해금된 기억에 대한 지시어("그때", "그거", "방금 말한 거")가 있으면 즉시 해당 시나리오를 매핑.
        
4. **Heroine_recall:** 다른 NPC와의 대화 질문 ("루파메스랑 무슨 얘기 했어?", "레티아와 무슨 대화 했어?").

**대현자 의도 분류 (3가지):**
1. **General:** 일상 대화, 안부, 농담, 사트라 본인에 대한 질문.
2. **Memory_recall:** 플레이어와 대현자가 함께 나눈 과거 대화/경험 질문 ("우리 전에 뭐 얘기했지?", "어제 뭐 했어?").
3. **Worldview_inquiry:** 세계관, 국가, 종족, 던전, 디멘시움, 플레이어(멘토)의 과거/능력 등에 대한 질문.
    

### Step 3: 컨텍스트 구성 (Context Construction)

- **Persona:** 현재 호감도/Sanity 상태에 따른 동적 페르소나 주입.
    
- **Scenarios:** `heroine_scenarios` 테이블에서 PGroonga+Vector 하이브리드 검색.
    
- **Retrieved Memories:** 의도 분류에 따라 가져온 장기 기억.
    
- **Recent Dialogue:** Redis에서 가져온 최근 대화 (Short-term).
    

### Step 4: 응답 생성 (LLM Generation)

- 설정된 `max_token` 내에서 페르소나 말투를 반영하여 Text 출력.
    
- 감정 상태(`emotion`), 감정 강도(emotion_intensity)를 0~6(neutral, joy, sorrow 등)의 정수값으로 도출.
- **토큰 최적화 (Token Capping):** 응답 속도 보장을 위해 `max_tokens=200` 설정.
    

### Step 5: TTS 생성 (Optional)

- Typecast API를 호출하여 텍스트를 음성(WAV)으로 변환 후 Base64로 인코딩하여 응답에 포함.
- Base64 인코딩 사용 이유: JSON 응답에 바이너리 데이터를 문자열로 포함하여 단일 요청으로 텍스트+상태+음성 전송 가능.
- 감정과 감정 강도 포함
- 감정(`emotion`) 값을 TTS 감정 프리셋(joy->happy, sorrow->sad 등)에 매핑.
- 감정 강도(emotion_intensity) : 0~2
- NPC별 음성 매핑: 레티아(1)=Mio, 루파메스(2)=Sora, 로코(3)=Saeron, 사트라(0)=Yubin
    

---

# 4. NPC-NPC 대화 시스템

플레이어 개입 없이 NPC끼리 대화하며 세계관을 확장하는 기능입니다.
- NPC_A NPC_B / NPC_B NPC_C / NPC_A NAP_C 마다 다른 대화창 존재
- **모델 최적화:** 경량화 모델 및 엄격한 프롬프트 전략으로 생성 시간 단축 (50초 -> 6초대)
- **생성 방식:** `POST /api/npc/heroine-conversation/generate` 호출 시 한 번에 멀티 턴(예: 10턴) 대화 생성 및 DB 저장.
    
- **독립적 메모리:** `npc_npc_memories`, `npc_npc_checkpoints` 테이블 사용.
    
- **동적 프롬프트:**
    
    - 두 NPC의 현재 상태(MemoryProgress)를 조회하여 각자 해금된 기억 범위 내에서 대화하도록 프롬프트에 `[전용 정보]` 섹션 분리 주입.
        
- **User 개입 (Interruption):**
    
    - NPC 간 대화 도중 User가 말을 걸면 `interruptedTurn`을 기록.
        
    - 인터럽트 처리 과정:
        1. 체크포인트 자르기: `npc_npc_checkpoints` 테이블에서 interruptedTurn 이후 대화 삭제
        2. 장기기억 무효화: `npc_npc_memories` 테이블에서 interruptedTurn 이후 기억의 `invalid_at` 설정
        3. Redis 세션 자르기: `npc_npc_session`에서 interruptedTurn 이후 대화 버퍼 삭제
        
    - 이후 해당 턴 이후의 대화 내용은 "일어나지 않은 일"로 처리(Invalidate).
        
    - User가 "방금 쟤랑 무슨 얘기 했어?"라고 물으면(`Heroine_recall`), 중단된 시점까지의 내용만 요약하여 답변.
        
## 정신력에 따른 태도변화
- 정신력 0일시 우울모드
- 
# 5. 주요 구현 특징 및 최적화

- **비동기/백그라운드 저장:** 응답 속도(Latency) 개선을 위해 Redis 저장을 제외한 DB 저장(User Memory, Checkpoint)은 응답 반환 후 백그라운드 태스크로 처리.
    
- **Supabase 최적화:** `prepare_threshold=0` 설정을 통해 Transaction Mode Pooler에서의 쿼리 충돌 방지.
    
- **ORM 미사용:** `pgvector` 및 복잡한 하이브리드 스코어링 쿼리의 정확한 제어를 위해 Raw SQL(`SQLAlchemy text()`) 사용.
    
- **시나리오 시딩:** `metadata` 컬럼을 활용해 키워드/동의어 기반 검색률 향상.

- **세션 관리:** Redis에 최근 20턴 대화 버퍼 저장 (24시간 TTL), 로그인 시 `session_checkpoint` 테이블에서 복원.
이 구조는 **"기억하는 NPC"**, **"변화하는 관계"**, **"유기적인 상호작용"**을 구현하기 위해 설계되었습니다.
