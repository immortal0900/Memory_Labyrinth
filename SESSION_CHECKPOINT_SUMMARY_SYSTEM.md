# Session Checkpoint Summary System 구현 기획

## 개요

- 매 대화 후 Redis 세션을 Supabase `session_checkpoints` 테이블에 백그라운드로 저장
- NPC 별로 다르게 처리해야 함
- 매 대화마다 질문과 답변을 `conversation`에 저장 (방금 한 대화만)
- 로그인시 `session_checkpoints` 테이블에서 각 npc별 최근 20개의 `conversation` 대화 내용과 `summary_list`를 redis session으로 가져옴
- state 정보(affection, sanity, memoryProgress, emotion) 저장
- 요약(summary_list) 기능 추가: 20턴 또는 1시간마다 LLM으로 요약 생성 (백그라운드)
- 마지막 대화 시간(`last_chat_at`)과 현재 시간 차이를 계산하여 프롬프트에 삽입
- 중요도 기반 스마트 가지치기로 summary_list 관리

## 1. 데이터베이스 스키마 수정

### 1-1. `init.sql` 수정

`session_checkpoints` 테이블에 다음 컬럼 추가:

- `user_id` (varcher): (유저 id)
- `npc_id` (varcher): (npc id)
- `summary_list` (JSONB): 요약 목록 배열
- `conversation` (JSONB): 방금 한 대화만 저장 (질문과 답변, 최대 2개)
- `last_chat_at` (TIMESTAMPTZ): 마지막 대화 시간 (시간 차이 계산용)
- `state` (JSONB): 게임 상태 정보 (affection, sanity, memoryProgress, emotion)


## 2. Redis 세션 구조 확장

### 2-1. `src/db/redis_manager.py` 수정

- `user_id` 필드 추가
- `npc_id` 필드 추가
- `summary_list` 필드 추가 (초기값: 빈 리스트)
- `last_chat_at` 필드 추가 (마지막 대화 시간, 매 대화마다 업데이트)
- `_create_empty_session` 메서드에 새 필드 추가

## 3. 요약 생성 및 관리 모듈

### 3-1. `src/db/session_checkpoint_manager.py` 생성 (새 파일)

주요 기능:

- `save_checkpoint_background()`: 백그라운드로 Supabase에 저장
  - conversation 저장 (방금 한 대화만, 질문과 답변)
  - state 저장 (affection, sanity, memoryProgress, emotion)
  - last_chat_at 업데이트 (현재 시간)
- `generate_summary()`: LLM으로 요약 생성 및 중요도 평가 (백그라운드)
- `prune_summary_list()`: 중요도 기반 가지치기 (시간/개수 제한)
- `calculate_time_diff()`: 마지막 대화(`last_chat_at`)와 현재 시간 차이 계산 (한국어로 변환)
- `load_checkpoint()`: 로그인시 `session_checkpoints` 테이블에서 각 npc별 최근 20개의 `conversation` 대화 내용과 `summary_list`를 redis session으로 가져옴

요약 생성 조건 (백그라운드에서 처리):
- 대화가 20턴 이상 경과 했을 경우
- 또는 마지막 요약 생성 후 1시간 경과

가지치기 로직:

1. 시간 기준: 현재 시간 - 요소 시간 > 3시간 → 삭제 후보
2. 개수 기준: 리스트 길이 > 5개 → 삭제 후보
3. 중요도 기반 선정:
   - 중요도가 가장 낮은 항목 중 가장 오래된 것 삭제
   - 중요도가 가장 높은 항목은 삭제하지 않고 점수 1 감소 후 유지

## 4. 백그라운드 저장 통합

### 4-1. `src/api/npc_router.py` 수정

- `heroine_chat()`, `heroine_chat_sync()`, `sage_chat()`, `sage_chat_sync()` 엔드포인트에 백그라운드 태스크 추가
- **사용자에게 응답을 먼저 전송한 후**, `BackgroundTasks`로 `save_checkpoint_background()` 호출
- 저장 내용:
  - conversation (방금 한 대화만, 질문과 답변)
  - state (affection, sanity, memoryProgress, emotion)
  - last_chat_at (현재 시간)
  - `user_id` (유저 id)
  - `npc_id` (npc id)
- 에러 발생 시 로그만 출력 (예외 처리)

### 4-2. `src/agents/npc/heroine_agent.py` 수정

- `_update_state_after_response()` 메서드에서 요약 생성 조건 확인
- 조건 만족 시 백그라운드로 `generate_summary()` 호출
- `summary_list` 업데이트 및 가지치기 실행

### 4-3. `src/agents/npc/sage_agent.py` 수정

- 동일하게 요약 생성 로직 추가 (백그라운드)

## 5. 시간 차이 계산 및 프롬프트 삽입

### 5-1. `src/agents/npc/base_npc_agent.py` 수정

- `_build_full_prompt()` 메서드에 시간 정보 삽입
- `calculate_time_diff()` 호출하여 "마지막 대화로부터 X시간 Y분 지남" 형식으로 변환
- 시스템 프롬프트 최상단에 삽입

### 5-2. `src/prompts/prompt_type/npc/heroine_system.yaml` 수정

- 프롬프트 최상단에 `{time_since_last_chat}` 변수 추가
- 예: "마지막 대화로부터 2시간 30분 경과."

### 5-3. `src/prompts/prompt_type/npc/sage_system.yaml` 수정

- 동일하게 시간 정보 변수 추가

## 6. 세션 로드 시 복원

### 6-1. `src/api/npc_router.py` 수정

- `login()` 엔드포인트에서 Supabase에서 체크포인트 로드
- `load_checkpoint()`가 - `user_id` 와 `npc_id` 별 conversation 의 최근 20개 행의 대화 내용만 반환
- `summary_list`, `state`도 함께 로드
- Redis 세션에 복원

### 6-2. `src/db/redis_manager.py` 수정

- `load_session()` 메서드에서 Supabase 체크포인트 확인 로직 추가 (선택사항)

## 7. 저장 흐름

### 7-1. 매 대화마다 저장 (백그라운드)

1. 사용자 질문 수신
2. NPC 응답 생성
3. **사용자에게 응답 즉시 전송** (딜레이 없음)
4. 백그라운드에서 저장:
   - conversation에 방금 한 대화 저장 (질문과 답변)
   - state 업데이트 (affection, sanity, memoryProgress, emotion)
   - last_chat_at 업데이트
   - Supabase에 저장

### 7-2. 요약 생성 (백그라운드, 조건부)

- 20턴이 차거나 1시간이 지났을 때만 실행
- 요약 생성 후 summary_list에 추가
- 가지치기 실행

## 8. 에러 처리

모든 백그라운드 작업에서:

- try-except로 예외 처리
- 에러 발생 시 `print()` 또는 로깅으로만 출력
- 사용자 응답에는 영향 없음





