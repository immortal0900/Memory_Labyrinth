from pydantic import BaseModel
from typing import List, Dict
from core.game_dto.StatData import StatData
from core.game_dto.SkillData import SkillData
from core.game_dto.WeaponData import WeaponData

class DungeonPlayerData(BaseModel):

    # 플레이어 ID
    playerId: int

    # 히로인 ID 0 ~ 2
    heroineId: int

    # 히로인 호감도 1 ~ 10
    affection:int

    # 히로인 정신력 0 ~ 100
    sanity: int

    # 시나리오 레벨 1 ~ 10
    scenarioLevel: int

    # 던전 난이도 0 ~ 2
    difficulty: int = 0 

    # 히로인의 스탯
    stats: StatData

    # 스킬 데이터
    skills: SkillData

    # 무기 데이터
    weapon: WeaponData

    # 인벤 토리
    inventory: List[int] = []
