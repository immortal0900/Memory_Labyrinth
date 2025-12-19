from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MonsterData:
    """몬스터 기본 정보"""

    monster_id: int
    monster_type: int  # 0: 일반, 1: 엘리트, 2: 보스
    monster_name: str
    hp: int
    speed: int
    attack: int
    attack_speed: float
    attack_range: float
    stagger_gage: int  # 일시적으로 비틀거리며 공격이 캔슬되고, 행동이 제한되는 상태
    weaknesses: Optional[List[int]] = None  # 약점 속성 ID 리스트
    strengths: Optional[List[int]] = None  # 강점 속성 ID 리스트

    @property
    def threat_level(self) -> float:
        """
        몬스터의 위협도 계산
        (HP * 공격력 * 공격속도 * (이동속도/100)) / 100
        """
        return (
            self.hp * self.attack * self.attack_speed * (self.speed / 100.0)
        ) / 100.0


# ===== 몬스터 데이터베이스 =====
MONSTER_DATABASE: Dict[int, MonsterData] = {
    0: MonsterData(
        monster_id=0,
        monster_type=0,
        monster_name="스켈레톤",
        hp=350,
        speed=350,
        attack=30,
        attack_speed=1.0,
        attack_range=300.0,
        stagger_gage=10,
        weaknesses=None,
        strengths=None,
    ),
    1: MonsterData(
        monster_id=1,
        monster_type=0,
        monster_name="저주받은 고사지",
        hp=150,
        speed=400,
        attack=75,
        attack_speed=1.0,
        attack_range=250.0,
        stagger_gage=50,
        # TSV: 넉백, 빠른 이동속도, 강한 한방
        weaknesses=[10, 2, 6],
        # TSV: 타격
        strengths=[12],
    ),
    # 일반 몬스터 2
    2: MonsterData(
        monster_id=2,
        monster_type=0,
        monster_name="거미",
        hp=400,
        speed=250,
        attack=40,
        attack_speed=0.7,
        attack_range=200.0,
        stagger_gage=100,
        # TSV: 타격
        weaknesses=[12],
        # TSV: 넉백, 느린 이동속도
        strengths=[10, 3],
    ),
    # 일반 몬스터 3
    4: MonsterData(
        monster_id=4,
        monster_type=0,
        monster_name="스켈레톤 석궁병",
        hp=300,
        speed=350,
        attack=30,
        attack_speed=1.0,
        attack_range=2000.0,
        stagger_gage=10,
        weaknesses=None,
        strengths=None,
    ),
    # ======================
    # 엘리트 몬스터
    # ======================
    3: MonsterData(
        monster_id=3,
        monster_type=1,
        monster_name="언데드",
        hp=800,
        speed=150,
        attack=50,
        attack_speed=1.5,
        attack_range=170.0,
        stagger_gage=100,
        # TSV: 넉백
        weaknesses=[10],
        # TSV: 타격, 느린 공격속도
        strengths=[12, 5],
    ),
    # ======================
    # 보스 몬스터
    # ======================
    1000: MonsterData(
        monster_id=1000,
        monster_type=2,
        monster_name="광란",
        hp=3500,
        speed=300,
        attack=45,
        attack_speed=2.0,
        attack_range=500.0,
        stagger_gage=55,
        weaknesses=None,
        strengths=None,
    ),
    1001: MonsterData(
        monster_id=1001,
        monster_type=2,
        monster_name="공포",
        hp=8000,
        speed=350,
        attack=100,
        attack_speed=1.0,
        attack_range=500.0,
        stagger_gage=100,
        weaknesses=None,
        strengths=None,
    ),
}


def get_monster_by_id(monster_id: int) -> Optional[MonsterData]:
    return MONSTER_DATABASE.get(monster_id)


def get_monsters_by_type(monster_type: int) -> List[MonsterData]:
    return [m for m in MONSTER_DATABASE.values() if m.monster_type == monster_type]


def get_all_normal_monsters() -> List[MonsterData]:
    return get_monsters_by_type(0)


def get_all_elite_monsters() -> List[MonsterData]:
    return get_monsters_by_type(1)


def get_all_boss_monsters() -> List[MonsterData]:
    return get_monsters_by_type(2)
