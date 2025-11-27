from pydantic import BaseModel
from typing import List


class MonsterSpawnData(BaseModel):
    # 몬스터 ID
    monsterId: int

    # 위치 X - 0 ~ 1
    posX: float

    # 위치 Y - 0 ~ 1
    posY: float
