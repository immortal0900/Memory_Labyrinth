from pydantic import BaseModel
from typing import List, Dict, Optional


class WeaponData(BaseModel):

    weaponId: Optional[int] = None

    # 무기 타입 0:한손검,1:쌍검,2:대검,3:둔기
    weaponType: int = 0

    # 무기명
    weaponName: Optional[str] = None

    # 등급 (0 : 장신구 1 : 한손검 2: 쌍검 3 : 대검 4: 두손둔기)
    rarity: int = 0

    # 무기 기본 공격력
    attackPower: int

    # 무기 그로기 공격력
    staggerPower: Optional[int] = None

    # 스탯별 보정치
    # 예: { "strength": 0.5, "dexterity": 0.5 }
    modifier: Dict[str, float] = {},

    

