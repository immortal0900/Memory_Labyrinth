from pydantic import BaseModel
from typing import List, Dict


class WeaponData(BaseModel):

    # 무기 타입 0:한손검,1:쌍검,2:대검,3:둔기
    weaponType: int = 0

    # 등급
    rarity: int = 0

    # 무기 기본 공격력
    attackPower: int

    # 스탯별 보정치
    # 예: { "strength": 0.5, "dexterity": 0.5 }
    modifier: Dict[str, float] = {}