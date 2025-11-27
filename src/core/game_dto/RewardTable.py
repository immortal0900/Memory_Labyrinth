from pydantic import BaseModel
from typing import List
class RewardTable(BaseModel):
    # 아이템 레어도 
    rarity:int 
    itemTable:List[int] = []