from pydantic import BaseModel

class SkillData(BaseModel):
    # 패시브 스킬 ID
    passiveSkillId: int
    # 호감도 기반 레벨 1 ~ 4
    passiveSkillLevel: int = 1

    # 액티브 스킬 ID
    activeSkillId: int
    # 호감도 기반 레벨 1 ~ 4
    activeSkillLevel: int = 1