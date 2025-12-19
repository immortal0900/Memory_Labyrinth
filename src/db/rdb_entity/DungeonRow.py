from pydantic import BaseModel
from typing import Optional, Any, Dict, List

class DungeonEvent(BaseModel):
    room_id: int
    event_type: int
    event_title: str
    event_code: str
    scenario_text: str
    scenario_narrative: str
    choices: List[Dict[str, Any]] = []
    expected_outcome: str
    
class DungeonRow(BaseModel):
    raw_map: Optional[Dict[str, Any]] = None
    balanced_map: Optional[Dict[str, Any]] = None
    is_finishing: Optional[bool] = None
    summary_info: Optional[str] = None

    player1: Optional[str] = None
    player2: Optional[str] = None
    player3: Optional[str] = None
    player4: Optional[str] = None

    heroine1: Optional[str] = None
    heroine2: Optional[str] = None
    heroine3: Optional[str] = None
    heroine4: Optional[str] = None

    event: Optional[DungeonEvent] = None

    # 선택: floor 컬럼이 있다면 추가
    floor: Optional[int] = None

    class Config:
        orm_mode = True

