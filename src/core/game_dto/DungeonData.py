from pydantic import BaseModel
from typing import List
from core.game_dto.RoomData import RoomData
from core.game_dto.RewardTable import RewardTable


class DungeonData(BaseModel):
    playerIds: List[int]
    heroineId: List[int]
    rooms: List[RoomData] = [] 
    rewards: List[RewardTable] = [] 
