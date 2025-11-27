from pydantic import BaseModel
from typing import List,Optional
from core.game_dto.MonsterSpawnData import MonsterSpawnData

class RoomData(BaseModel):
    # 방 ID
    roomId: int

    # 방 타입 (0:빈방, 1:전투, 2:이벤트, 3:보물)
    type: int

    # 방 변 길이
    size: int

    # 연결된 방 ID 목록 (기본값 빈 리스트)
    neighbors: List[int] = []

    # 전투일 경우 몬스터 데이터
    # 전투방이 아닐 땐 없을 수 있으므로 Optional 처리
    monsters: List[MonsterSpawnData] = []

    # 이벤트 타입 (이벤트 방에서만 존재)
    # 표에 'int/null'로 되어 있으므로 Optional[int] 사용
    eventType: Optional[int] = None
