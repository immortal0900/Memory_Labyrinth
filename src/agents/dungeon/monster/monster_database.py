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
    stagger_gage: int  # 일시정으로 비틀거리며 공격이 캔슬되고, 행동이 제한되는 상태
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
# 프로토타입용: 일반 몬스터 1종, 보스 몬스터 1종만 존재
MONSTER_DATABASE: Dict[int, MonsterData] = {
    # 일반 몬스터 1
    1: MonsterData(
        monster_id=1,
        monster_type=0,
        monster_name="슬라임",
        hp=150,
        speed=200,
        attack=8,
        attack_speed=1.2,
        attack_range=50.0,
        stagger_gage=5,
        weaknesses=[1],
        strengths=[2],
    ),
    # 일반 몬스터 2
    2: MonsterData(
        monster_id=2,
        monster_type=0,
        monster_name="고블린",
        hp=220,
        speed=300,
        attack=12,
        attack_speed=1.0,
        attack_range=80.0,
        stagger_gage=8,
        weaknesses=[2],
        strengths=[1],
    ),
    # 일반 몬스터 3
    3: MonsterData(
        monster_id=3,
        monster_type=0,
        monster_name="스켈레톤",
        hp=180,
        speed=250,
        attack=10,
        attack_speed=1.1,
        attack_range=60.0,
        stagger_gage=7,
        weaknesses=[3],
        strengths=[2],
    ),
    # 보스 몬스터 1
    100: MonsterData(
        monster_id=100,
        monster_type=2,
        monster_name="오우거 보스",
        hp=1200,
        speed=180,
        attack=40,
        attack_speed=1.3,
        attack_range=120.0,
        stagger_gage=60,
        weaknesses=[1, 2],
        strengths=[3],
    ),
    # 보스 몬스터 2
    101: MonsterData(
        monster_id=101,
        monster_type=2,
        monster_name="드래곤",
        hp=2000,
        speed=220,
        attack=60,
        attack_speed=1.7,
        attack_range=200.0,
        stagger_gage=100,
        weaknesses=[2, 3],
        strengths=[1],
    ),
}


def get_monster_by_id(monster_id: int) -> Optional[MonsterData]:
    """몬스터 ID로 데이터 조회"""
    return MONSTER_DATABASE.get(monster_id)


def get_monsters_by_type(monster_type: int) -> List[MonsterData]:
    """몬스터 타입으로 필터링"""
    return [m for m in MONSTER_DATABASE.values() if m.monster_type == monster_type]


def get_all_normal_monsters() -> List[MonsterData]:
    """일반 몬스터 목록"""
    return get_monsters_by_type(0)


def get_all_elite_monsters() -> List[MonsterData]:
    """엘리트 몬스터 목록"""
    return get_monsters_by_type(1)


def get_all_boss_monsters() -> List[MonsterData]:
    """보스 몬스터 목록"""
    return get_monsters_by_type(2)
