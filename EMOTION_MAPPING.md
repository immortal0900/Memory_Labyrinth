# Emotion 매핑 가이드

## 개요

NPC 시스템의 emotion 값은 **정수형(int, 0-6)**으로 출력됩니다.

- **LLM 내부**: 문자열 emotion을 이해하고 생성 (예: "neutral", "joy")
- **최종 API 응답**: 정수값으로 자동 변환되어 전달 (예: 0, 1)

이 변환은 [`src/agents/npc/emotion_mapper.py`](src/agents/npc/emotion_mapper.py)에서 자동으로 처리됩니다.

---

## 통합 Emotion 매핑

**적용 대상**: 히로인(레티아, 루파메스, 로코) 및 대현자(사트라)

| 정수값 | 문자열 | 설명 |
|--------|--------|------|
| 0 | neutral | 평온한 상태 |
| 1 | joy | 기쁨, 즐거움 |
| 2 | fun | 재미있는 상태 |
| 3 | sorrow | 슬픔, 우울함 |
| 4 | angry | 분노, 화남 |
| 5 | surprise | 놀람, 당황 |
| 6 | mysterious | 신비로움, 수수께끼 같은 |

---

## API 응답 예시

### 히로인 대화

```json
{
  "text": "...뭐예요? 갑자기 그런 걸 물어보시다니.",
  "emotion": 0,
  "affection": 50,
  "sanity": 100,
  "memoryProgress": 30
}
```

### 대현자 대화

```json
{
  "text": "흐음, 이곳이 궁금한가? 레테는 기억과 망각이 뒤섞인 행성이지...",
  "emotion": 6,
  "scenarioLevel": 3,
  "infoRevealed": true
}
```

### 히로인간 대화

```json
{
  "conversation": [
    {
      "speaker_id": 1,
      "speaker_name": "레티아",
      "text": "...보면 몰라요? 검을 닦고 있잖아요.",
      "emotion": 0
    },
    {
      "speaker_id": 2,
      "speaker_name": "루파메스",
      "text": "아 심심해서 왔지~",
      "emotion": 1
    }
  ]
}
```

---

## LLM 프롬프트 (내부)

LLM은 여전히 다음과 같이 문자열 emotion을 사용합니다:

```json
{
  "thought": "...",
  "text": "...",
  "emotion": "neutral|joy|fun|sorrow|angry|surprise|mysterious"
}
```

이 문자열 값이 코드 레벨에서 자동으로 정수로 변환됩니다.

---

## 변환 함수 사용법

### Python

```python
from agents.npc.emotion_mapper import (
    emotion_to_int,
    int_to_emotion,
    heroine_emotion_to_int,
    sage_emotion_to_int,
)

# 통합 emotion 변환
emotion_int = emotion_to_int("joy")  # 1
emotion_str = int_to_emotion(1)      # "joy"

# 히로인 emotion 변환 (동일)
heroine_emotion_int = heroine_emotion_to_int("mysterious")  # 6

# 대현자 emotion 변환 (동일)
sage_emotion_int = sage_emotion_to_int("mysterious")  # 6
```

### 언리얼 엔진 (C++)

```cpp
// emotion 정수값을 문자열로 매핑 (언리얼 측에서 필요시)
enum class ENPCEmotion : uint8
{
    Neutral = 0,
    Joy = 1,
    Fun = 2,
    Sorrow = 3,
    Angry = 4,
    Surprise = 5,
    Mysterious = 6
};
```

---

## 사용 사례별 emotion

### 히로인 NPC
- **neutral**: 평소 대화
- **joy**: 좋아하는 것을 언급했을 때
- **fun**: 재미있는 이야기나 농담
- **sorrow**: 슬픈 이야기, 트라우마 언급
- **angry**: 화나는 상황, 트라우마 직접 건드림
- **surprise**: 예상치 못한 질문이나 상황
- **mysterious**: 기억을 되찾을 때, 중요한 깨달음

### 대현자 NPC
- **neutral**: 평소 대화
- **joy**: 플레이어의 성장을 기뻐할 때
- **fun**: 재미있는 질문에 답할 때
- **sorrow**: 과거의 비극을 이야기할 때
- **angry**: 경고를 줄 때 (드물게)
- **surprise**: 플레이어의 특별한 능력을 발견할 때
- **mysterious**: 비밀을 암시하거나 수수께끼 같은 답변

---

## 참고 파일

- [src/agents/npc/emotion_mapper.py](src/agents/npc/emotion_mapper.py): 변환 로직
- [src/agents/npc/heroine_agent.py](src/agents/npc/heroine_agent.py): 히로인 에이전트
- [src/agents/npc/sage_agent.py](src/agents/npc/sage_agent.py): 대현자 에이전트
- [src/agents/npc/heroine_heroine_agent.py](src/agents/npc/heroine_heroine_agent.py): 히로인간 대화
- [src/prompts/prompt_type/npc/heroine_system.yaml](src/prompts/prompt_type/npc/heroine_system.yaml): 히로인 프롬프트
- [src/prompts/prompt_type/npc/sage_system.yaml](src/prompts/prompt_type/npc/sage_system.yaml): 대현자 프롬프트
