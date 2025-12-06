from pydantic import BaseModel
from typing import Optional, Any, Dict, List

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

    event: Optional[Dict[str, Any]] = None

    # 선택: floor 컬럼이 있다면 추가
    floor: Optional[int] = None

    class Config:
        orm_mode = True