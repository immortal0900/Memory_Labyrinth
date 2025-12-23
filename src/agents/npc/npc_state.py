from typing import TypedDict, List, Optional, Literal
from langchain_core.messages import BaseMessage
from enum import StrEnum


class IntentType(StrEnum):
    """NPC 대화 의도 분류"""

    GENERAL = "general"  # 일반 대화
    MEMORY_RECALL = "memory_recall"  # 과거 회상 (user_memories + npc_npc_memories 검색)
    SCENARIO_INQUIRY = "scenario_inquiry"  # 시나리오 질문 (heroine_scenarios 검색)
    HEROINE_RECALL = "heroine_recall"  # 다른 히로인과 나눈 대화 내용 질문 (npc_npc_checkpoints)


class EmotionType(StrEnum):
    """NPC 감정 상태 (통합 매핑)

    정수 매핑:
    - 0: neutral (평온)
    - 1: joy (기쁨)
    - 2: fun (재미)
    - 3: sorrow (슬픔)
    - 4: angry (분노)
    - 5: surprise (놀람)
    - 6: mysterious (신비로움)
    """

    NEUTRAL = "neutral"  # 0
    JOY = "joy"  # 1
    FUN = "fun"  # 2
    SORROW = "sorrow"  # 3
    ANGRY = "angry"  # 4
    SURPRISE = "surprise"  # 5
    MYSTERIOUS = "mysterious"  # 6


class NPCState(TypedDict, total=False):
    """NPC LangGraph 상태"""

    # 기본 정보
    player_id: int
    npc_id: int
    npc_type: Literal["heroine", "sage"]

    # 대화 메시지
    messages: List[BaseMessage]

    # 히로인 상태 (히로인 NPC용)
    affection: int  # 호감도 0-100
    sanity: int  # 정신력 0-100
    memoryProgress: int  # 기억 진척도 0-100

    # 대현자 상태 (대현자 NPC용)
    scenarioLevel: int  # 시나리오 레벨 1-10

    # 공통 상태
    emotion: str  # 현재 감정

    # 의도 분류
    intent: str

    # 검색 결과
    retrieved_facts: Optional[str]  # user_memories + npc_npc_memories 검색 결과
    unlocked_scenarios: Optional[str]  # heroine_scenarios 검색 결과
    heroine_conversation: Optional[str]  # npc_npc_checkpoints 대화 전체

    # 대화 버퍼
    conversation_buffer: List[dict]
    short_term_summary: str

    # 응답
    response_text: str
    affection_delta: int  # 호감도 변화량
    sanity_delta: int  # 정신력 변화량


class HeroineState(NPCState):
    """히로인 NPC 상태 (NPCState 확장)"""

    recent_used_keywords: List[str]  # 최근 5턴 내 사용된 좋아하는 키워드
    used_liked_keyword: Optional[str]  # 이번 턴에 사용된 좋아하는 키워드


class SageState(NPCState):
    """대현자 NPC 상태 (NPCState 확장)"""

    info_revealed: bool  # 정보 공개 여부
