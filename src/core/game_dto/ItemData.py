from pydantic import BaseModel
from typing import  Optional
from core.game_dto.WeaponData import WeaponData


class ItemData(BaseModel):
    # 아이템 명 
    itemName:Optional[str] = None
    # Id
    itemId: int = 0

    # 타입 : 장신구 1 : 한손검 2: 쌍검 3 : 대검 4: 두손둔기
    itemType: int = 0

    # 등급 0~3 (커먼, 언커먼, 레어, 레전드)
    rarity: int

    # 무기일 경우 무기 공격력 및 보정치
    weapon: Optional[WeaponData]