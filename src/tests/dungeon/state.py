from typing import TypedDict, List, Dict, Any, Optional
from models import MonsterMetadata, StatData, RoomData, DungeonData


class DungeonState(TypedDict):
    # input data
    hero_stats: List[StatData] # 히로인 스탯 리스트
    monster_db: Dict[int, MonsterMetadata] # 몬스터 DB

    # payload
    dungeon_data: Dict[str, Any] # 언리얼이 보내온 json 데이터

    # context
    difficulty_log: Dict[str, Any]



# class DungeonState(TypedDict):
#     """
#     던전 생성 상태 - 통신 프로토콜 구조
    
#     Agent 간 데이터 전달 형식:
#     - Monster Agent -> Event Agent: room_plans, difficulty_context 전달
#     - Event Agent -> Item Agent: event_plans 추가 전달
#     """
#     # 입력 데이터 (통신 프로토콜)
#     player_ids: List[int]  # 참여 플레이어 ID 리스트
#     heroine_ids: List[int]  # 각 플레이어가 선택한 히로인 ID 리스트
#     hero_stats: List[StatData]  # 히로인 스탯 리스트 (각 히로인별)
#     monster_db: Dict[int, MonsterMetadata]  # 몬스터 DB (monsterId -> MonsterMetadata 매핑)
    
#     # 층 정보
#     floor: int  # 현재 층
#     room_count: int  # 해당 층의 방 개수
    
#     # Monster Agent 출력 (통신 프로토콜)
#     rooms: List[RoomData]  # 생성된 방 데이터 리스트
#     difficulty_context: Dict[str, Any]  # 난이도 컨텍스트
    
#     # Event Agent 출력 (통신 프로토콜)
#     # event_rooms: Optional[List[RoomData]]  # 이벤트가 추가된 방 데이터 리스트
#     # event_data: Optional[List[Dict[str, Any]]]  # 이벤트 상세 데이터 (시나리오, 상호작용, 결과)
    
#     # Item Agent 출력 (통신 프로토콜) - 향후 구현
#     # dungeon_data: Optional[DungeonData]  # 최종 던전 데이터 (보상 포함)


# # 통신 프로토콜 타입 정의
# class DifficultyContext(TypedDict):
#     """난이도 컨텍스트 구조"""
#     total_budget_allocated: float  # 총 할당 예산
#     total_budget_used: float  # 총 사용 예산
#     budget_utilization: float  # 예산 사용률 (0.0~1.0)
#     floor: int  # 층 수
#     room_count: int  # 방 개수
#     hero_combat_scores: List[float]  # 히로인별 전투력 점수 리스트

