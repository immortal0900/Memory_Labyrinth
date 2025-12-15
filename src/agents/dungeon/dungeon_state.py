from typing import TypedDict, Annotated, Dict, List, Any, Optional, Union
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field, ConfigDict


# ===== Event Agent용 State =====
class DungeonEventState(TypedDict):
    """Event Agent 내부에서 사용하는 State"""

    messages: Annotated[list, add_messages]
    heroine_data: dict
    heroine_memories: list
    event_room: int
    next_floor: int
    used_events: list  # 이전 층에서 사용한 event_template_id 리스트 (중복 방지용)

    selected_main_event: str
    sub_event: str
    final_answer: str
    player_id: Optional[int]  # 플레이어 ID 추가


class EventChoice(BaseModel):
    """이벤트 선택지 모델"""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(description="선택지 텍스트 (명확하고 구체적인 행동)")
    reward_id: Optional[str] = Field(
        default=None,
        description="보상 ID (event_rewards_penalties.py의 REWARDS에서 선택, 없으면 null)",
    )
    penalty_id: Optional[str] = Field(
        default=None,
        description="패널티 ID (event_rewards_penalties.py의 PENALTIES에서 선택, 없으면 null)",
    )


class DungeonEventParser(BaseModel):
    """Event Agent의 LLM 응답 파서 - 서브 이벤트 생성"""

    model_config = ConfigDict(extra="forbid")

    sub_event_narrative: str = Field(
        description="선택된 메인 이벤트를 기반으로 히로인의 기억과 연결된 구체적인 서브 이벤트 내러티브. 세계관과 히로인의 과거를 반영하여 풍부하게 작성."
    )
    event_choices: List[EventChoice] = Field(
        description="플레이어에게 제시할 선택지 목록 (2~4개). 선택지마다 보상 또는 패널티 중 하나만 있거나, 둘 다 있을 수 있음. 메인 이벤트와 연관된 보상/패널티를 선택해야 함.",
        min_length=2,
        max_length=4,
    )
    expected_outcome: str = Field(
        description="각 선택지별로 어떤 보상/패널티가 적용되는지, 그리고 그것이 게임 플레이에 어떤 영향을 미치는지 설명."
    )


# ===== Monster Agent용 State =====
class DungeonMonsterState(TypedDict):
    """
    Monster Agent 내부에서 사용하는 State
    
    단일/멀티 플레이어 지원:
    - heroine_stat: Dict 타입이면 단일 플레이어
    - heroine_stat: List[Dict] 타입이면 멀티 플레이어 (파티)
    """

    # Input
    heroine_stat: Union[Dict[str, Any], List[Dict[str, Any]]]  # 히로인 스탯 - 단일(Dict) 또는 파티(List[Dict])
    monster_db: Dict[int, Any]  # 몬스터 DB
    dungeon_data: Dict[str, Any]  # 언리얼에서 받은 던전 데이터
    dungeon_player_data: Dict[str, Any]  # 던전 플레이어 정보 (보스방 입장 시)
    floor: int  # 현재 층

    # Intermediate
    combat_score: float  # 계산된 전투력 (단일: 플레이어 전투력, 파티: 평균 전투력)
    llm_strategy: Dict[str, Any]  # LLM이 제안한 전략

    # Output
    filled_dungeon_data: Dict[str, Any]  # 몬스터가 배치된 던전 데이터
    difficulty_log: Dict[str, Any]  # 난이도 로그


class MonsterPreference(BaseModel):
    """몬스터 선호도 설정"""

    model_config = ConfigDict(extra="forbid")

    monster_type: Optional[str] = Field(
        description="선호하는 몬스터 타입 (예: 'Skeleton', 'Slime')", default=None
    )
    min_hp: Optional[int] = Field(description="최소 HP", default=None)
    max_hp: Optional[int] = Field(description="최대 HP", default=None)
    min_attack: Optional[int] = Field(description="최소 공격력", default=None)
    max_attack: Optional[int] = Field(description="최대 공격력", default=None)
    min_speed: Optional[int] = Field(description="최소 이동속도", default=None)
    max_speed: Optional[int] = Field(description="최대 이동속도", default=None)
    weight: float = Field(
        description="이 조건의 가중치 (0.0~1.0)", ge=0.0, le=1.0, default=1.0
    )


class MonsterStrategyParser(BaseModel):
    """Monster Agent의 LLM 응답 파서 - 고급 밸런싱 전략"""

    model_config = ConfigDict(extra="forbid")

    difficulty_multiplier: float = Field(
        description="난이도 배율 (0.5~2.0). 히로인이 강하면 높게, 약하면 낮게 설정",
        ge=0.5,
        le=2.0,
    )
    monster_preferences: List[MonsterPreference] = Field(
        description="선호하는 몬스터 조건 리스트 (HP, 공격력, 속도 범위 등)",
        default_factory=list,
    )
    avoid_conditions: List[str] = Field(
        description="피해야 할 몬스터 특성 (예: 'Slow', 'LowHP', 'Ranged')",
        default_factory=list,
    )
    preferred_tags: List[str] = Field(
        description="추천 몬스터 태그 리스트 (하위호환용)",
        default_factory=list,
    )
    reasoning: str = Field(description="전략 선택 이유를 1-2문장으로 설명")


# ===== Super Agent용 State (전체 던전 생성 통합) =====
class SuperDungeonState(TypedDict):
    # ===== Input Data =====
    # 언리얼에서 받아온 초기 던전 데이터
    dungeon_base_data: Dict[str, Any]  # 던전 기본 맵 구조 (rooms, floor_count 등)
    # 히로인 관련 데이터
    heroine_data: Dict[
        str, Any
    ]  # 히로인 정보 (heroine_id, memory_progress, event_room 포함)
    heroine_stat: Union[Dict[str, Any], List[Dict[str, Any]]]  # 히로인 스탯 (단일/멀티)
    heroine_memories: List[Any]  # 히로인 해금 정보
    # DB 및 설정
    monster_db: Dict[int, Any]  # 몬스터 DB (몬스터 에이전트에서 사용)
    dungeon_player_data: Dict[str, Any]  # 던전 플레이어 데이터 (affection, sanity 등)
    # 이벤트 중복 방지용 (세션 전체에서 사용된 이벤트 추적)
    used_events: List[
        Dict[str, Any]
    ]  # [{"event_template_id": 13, "room_id": 5, "floor": 1, "choice_id": "..."}]
    # ===== Agent 결과물 =====
    # Event Agent 결과
    event_result: Dict[str, Any]  # 이벤트 생성 결과
    # Monster Agent 결과
    filled_dungeon_data: Dict[str, Any]  # 몬스터가 배치된 던전 데이터
    difficulty_log: Dict[str, Any]  # 난이도 로그
    # ===== Final Output =====
    # 최종 병합된 JSON
    final_dungeon_json: Dict[str, Any]
