from pydantic import BaseModel
from typing import Optional

class StatData(BaseModel):
    
    # 최소 250
    hp: int = 250

    # 이동속도(500 x value) 1 ~ 2
    moveSpeed: float = 1

    # # 공격 속도(곱연산) 1 ~ 2.5
    attackSpeed: float = 1.0

    # # 쿨타임 감소량 (1.0 x value) 1 ~ 2
    cooldownReduction: float = 1

    # # 근력
    strength: int

    # # 기량
    dexterity: int

    # # 지능
    intelligence: Optional[int] = None

    # # 치명타 확률(합연산) 20 ~ 100
    critChance: float = 20.0

    # # 스킬 데미지 증가(곱연산) 1 ~ 5
    skillDamageMultiplier: float = 1.0

    # # 평타 데미지 증가(곱연산) 1 ~ 5
    autoAttackMultiplier: float = 1.0

    
