# LangFuse 토큰 추적 시스템

NPC 시스템의 모든 LLM 호출에 대한 토큰 사용량과 비용을 추적하는 시스템입니다.

## 설정 방법

### 1. LangFuse 계정 생성

1. [LangFuse Cloud](https://cloud.langfuse.com) 방문
2. 무료 계정 생성 (월 50,000 observations 무료)
3. 프로젝트 생성
4. Settings > API Keys에서 키 발급

### 2. 환경 변수 설정

`.env` 파일에 다음 설정 추가:

```bash
# LangFuse Token Tracking
LANGFUSE_SECRET_KEY=sk-lf-...  # 발급받은 Secret Key
LANGFUSE_PUBLIC_KEY=pk-lf-...  # 발급받은 Public Key
LANGFUSE_HOST=https://cloud.langfuse.com  # EU region
# LANGFUSE_HOST=https://us.cloud.langfuse.com  # US region (optional)
```

### 3. 의존성 설치

```bash
# UV 사용 시
uv sync

# pip 사용 시
pip install langfuse
```

## 추적되는 LLM 호출 지점

### NPC 대화 에이전트 (6개)
- **heroine_agent.py**
  - 의도 분류 (line 516)
  - 응답 생성 (line 1615)
- **sage_agent.py**
  - 의도 분류 (line 377)
  - 응답 생성 (line 966)
- **heroine_heroine_agent.py**
  - 상황 생성 (line 221)
  - 대화 생성 (line 603)

### 메모리 시스템 (4개)
- **user_memory_manager.py**
  - Fact 추출 (line 185)
  - 충돌 판단 (line 686)
- **npc_npc_memory_manager.py**
  - NPC-NPC Fact 추출 (line 267)
- **session_checkpoint_manager.py**
  - 대화 요약 (line 131)

### DeepEval 평가 (2개)
- **custom_llm.py**
  - 동기 평가 (generate)
  - 비동기 평가 (a_generate)

## LangFuse 대시보드 사용법

### 1. 트레이스 확인
- [LangFuse Dashboard](https://cloud.langfuse.com) 로그인
- Traces 탭에서 모든 LLM 호출 확인

### 2. 필터링
태그로 필터링:
- `npc:heroine` - 히로인 대화
- `npc:sage` - 대현자 대화
- `action:intent` - 의도 분류
- `action:response` - 응답 생성
- `action:fact_extraction` - Fact 추출
- `action:summary` - 대화 요약
- `character:letia`, `character:lupames`, `character:loco` - 특정 캐릭터
- `system:memory` - 메모리 시스템
- `system:deepeval` - DeepEval 평가

### 3. 비용 분석
- Dashboard > Metrics에서 일별/월별 토큰 사용량 확인
- Model별 비용 분석
- 세션별/유저별 토큰 사용량 확인

### 4. 커스텀 모델 가격 설정
Grok 모델은 LangFuse에 기본 등록되어 있지 않으므로 수동 설정 필요:

1. Settings > Models 클릭
2. "Add Model" 클릭
3. 모델 정보 입력:
   - **Model Name**: `grok-4-fast-non-reasoning`
   - **Input Price**: $0.0001 per 1K tokens (예시)
   - **Output Price**: $0.0002 per 1K tokens (예시)
   - **Match Pattern**: `(?i)^(grok-4-fast-non-reasoning)$`

## 로컬 디버깅

LangFuse가 비활성화되어도 NPC 시스템은 정상 작동합니다.

토큰 사용량은 콘솔에 로깅됩니다:
```
[TOKEN] heroine_response - input: 523, output: 187
[TOKEN] sage_response - input: 412, output: 156
```

## 비활성화

LangFuse 추적을 비활성화하려면:

1. `.env`에서 LangFuse 키 주석 처리 또는 삭제
2. 애플리케이션 재시작

시스템은 자동으로 LangFuse 없이 작동합니다.

## Self-Hosting (선택사항)

데이터 주권이 중요한 경우 Self-hosting 가능:

```yaml
# docker-compose.yml에 추가
services:
  langfuse:
    image: langfuse/langfuse:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://...
      - NEXTAUTH_SECRET=your-secret
      - NEXTAUTH_URL=http://localhost:3000
```

그 후 `.env`의 `LANGFUSE_HOST`를 `http://localhost:3000`으로 변경

## 문제 해결

### LangFuse 초기화 실패
```
[WARNING] LangFuse 비활성화: ...
```
- `.env`의 키가 올바른지 확인
- 인터넷 연결 확인
- LangFuse Cloud 상태 확인

### 토큰이 추적되지 않음
1. `.env`에 키가 설정되었는지 확인
2. `uv sync` 또는 `pip install langfuse` 실행 확인
3. 애플리케이션 재시작

### 비용이 계산되지 않음
- LangFuse Dashboard > Settings > Models에서 커스텀 모델 가격 설정
- Grok 모델은 수동 설정 필요

## 예상 비용 (참고용)

| 카테고리 | 예상 비중 | 모델 |
|---------|----------|------|
| NPC 응답 생성 | 50-60% | grok-4-fast-non-reasoning |
| Fact 추출 | 25-30% | gpt-5-mini |
| 의도 분류 | 10% | grok-4-fast-non-reasoning |
| 대화 요약 | 5-10% | gpt-5-mini |
| DeepEval | 10% | gpt-5-mini (테스트 시만) |

1회 NPC 대화당 예상 토큰: ~1,620 tokens

## 지원

- [LangFuse 공식 문서](https://langfuse.com/docs)
- [LangChain 통합 가이드](https://langfuse.com/docs/integrations/langchain/tracing)
