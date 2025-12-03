"""
Emotion 문자열 <-> 정수 변환 유틸리티

LLM은 여전히 문자열 emotion을 이해하고 출력하지만,
최종 응답에서는 int 형태로 변환됩니다.

통합 매핑 (히로인 & 대현자 공통):
- 0: neutral (평온)
- 1: joy (기쁨)
- 2: fun (즐거움)
- 3: sorrow (슬픔)
- 4: angry (분노)
- 5: surprise (놀람)
- 6: mysterious (신비로움)
"""

from typing import Optional


# 통합 emotion 매핑 (히로인 & 대현자 공통)
EMOTION_TO_INT = {
    "neutral": 0,
    "joy": 1,
    "fun": 2,
    "sorrow": 3,
    "angry": 4,
    "surprise": 5,
    "mysterious": 6,
}

INT_TO_EMOTION = {v: k for k, v in EMOTION_TO_INT.items()}

# 히로인 emotion 매핑 (하위 호환성)
HEROINE_EMOTION_TO_INT = EMOTION_TO_INT
HEROINE_INT_TO_EMOTION = INT_TO_EMOTION

# 대현자 emotion 매핑 (하위 호환성)
SAGE_EMOTION_TO_INT = EMOTION_TO_INT
SAGE_INT_TO_EMOTION = INT_TO_EMOTION


def emotion_to_int(emotion: str) -> int:
    """emotion 문자열을 정수로 변환

    Args:
        emotion: emotion 문자열 (neutral, joy, fun, sorrow, angry, surprise, mysterious)

    Returns:
        emotion 정수 (0-6), 매핑에 없으면 0 (neutral)
    """
    return EMOTION_TO_INT.get(emotion.lower().strip(), 0)


def int_to_emotion(emotion_int: int) -> str:
    """emotion 정수를 문자열로 변환

    Args:
        emotion_int: emotion 정수 (0-6)

    Returns:
        emotion 문자열, 범위 밖이면 "neutral"
    """
    return INT_TO_EMOTION.get(emotion_int, "neutral")


# 히로인용 함수 (하위 호환성)
def heroine_emotion_to_int(emotion: str) -> int:
    """히로인 emotion 문자열을 정수로 변환

    Args:
        emotion: emotion 문자열 (neutral, joy, fun, sorrow, angry, surprise, mysterious)

    Returns:
        emotion 정수 (0-6), 매핑에 없으면 0 (neutral)
    """
    return emotion_to_int(emotion)


def heroine_int_to_emotion(emotion_int: int) -> str:
    """히로인 emotion 정수를 문자열로 변환

    Args:
        emotion_int: emotion 정수 (0-6)

    Returns:
        emotion 문자열, 범위 밖이면 "neutral"
    """
    return int_to_emotion(emotion_int)


# 대현자용 함수 (하위 호환성)
def sage_emotion_to_int(emotion: str) -> int:
    """대현자 emotion 문자열을 정수로 변환

    Args:
        emotion: emotion 문자열 (neutral, joy, fun, sorrow, angry, surprise, mysterious)

    Returns:
        emotion 정수 (0-6), 매핑에 없으면 0 (neutral)
    """
    return emotion_to_int(emotion)


def sage_int_to_emotion(emotion_int: int) -> str:
    """대현자 emotion 정수를 문자열로 변환

    Args:
        emotion_int: emotion 정수 (0-6)

    Returns:
        emotion 문자열, 범위 밖이면 "neutral"
    """
    return int_to_emotion(emotion_int)
