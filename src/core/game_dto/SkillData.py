from pydantic import BaseModel
from typing_extensions import Optional

class SkillData(BaseModel):
    skillId: int
    skillName: str
    skillDescription: Optional[str] = None
    skillCoolTime: float = 1.0
    IsWeaponSkill:bool = False
    typeOrId:Optional[int] = None
    keyword:str 

# 0	높은 방어력
# 1	낮은 방어력
# 2	빠른 이동속도
# 3	느린 이동속도
# 4	빠른 공격속도
# 5	느린 공격속도
# 6	강한 한방 
# 7	많은 타수
# 8	높은 그로기 수치
# 9	낮은 그로기 수치
# 10	넉백
# 11	넉다운
# 12	타격
# 13	관통
# 14	높은 방어력
# 15	낮은 방어력
# 16	높은 체력
# 17	낮은 체력
# 18	원거리
# 19	근거리