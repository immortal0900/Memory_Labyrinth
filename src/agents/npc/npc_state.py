from typing import TypedDict, List, Optional, Literal
from langchain_core.messages import BaseMessage
from enum import StrEnum


class IntentType(StrEnum):
    """NPC 대화 의도 분류"""
    GENERAL = "general"              # 일반 대화
    MEMORY_RECALL = "memory_recall"  # 과거 회상 (Mem0 검색)
    SCENARIO_INQUIRY = "scenario_inquiry"  # 시나리오 질문 (DB 검색)


class EmotionType(StrEnum):
    """NPC 감정 상태"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SHY = "shy"
    FEAR = "fear"
    TRAUMA = "trauma"
    # 대현자 전용
    AMUSED = "amused"
    MYSTERIOUS = "mysterious"
    SERIOUS = "serious"
    WARM = "warm"
    WARNING = "warning"


class NPCState(TypedDict, total=False):
    """NPC LangGraph 상태"""
    # 기본 정보
    player_id: int
    npc_id: int
    npc_type: Literal["heroine", "sage"]
    
    # 대화 메시지
    messages: List[BaseMessage]
    
    # 히로인 상태 (히로인 NPC용)
    affection: int           # 호감도 0-100
    sanity: int              # 정신력 0-100
    memoryProgress: int      # 기억 진척도 0-100
    
    # 대현자 상태 (대현자 NPC용)
    scenarioLevel: int       # 시나리오 레벨 1-10
    
    # 공통 상태
    emotion: str             # 현재 감정
    
    # 의도 분류
    intent: str
    
    # 검색 결과
    retrieved_facts: Optional[str]       # Mem0 검색 결과
    unlocked_scenarios: Optional[str]    # DB 시나리오 검색 결과
    
    # 대화 버퍼
    conversation_buffer: List[dict]
    short_term_summary: str
    
    # 응답
    response_text: str
    affection_delta: int     # 호감도 변화량
    sanity_delta: int        # 정신력 변화량


class HeroineState(NPCState):
    """히로인 NPC 상태 (NPCState 확장)"""
    recent_used_keywords: List[str]   # 최근 5턴 내 사용된 좋아하는 키워드
    used_liked_keyword: Optional[str]  # 이번 턴에 사용된 좋아하는 키워드


class SageState(NPCState):
    """대현자 NPC 상태 (NPCState 확장)"""
    info_revealed: bool      # 정보 공개 여부

