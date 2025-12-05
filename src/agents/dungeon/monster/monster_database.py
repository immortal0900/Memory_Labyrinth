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
MONSTER_DATABASE: Dict[int, MonsterData] = {
    # 스켈레톤
    0: MonsterData(
        monster_id=0,
        monster_type=0,  # 일반
        monster_name="스켈레톤",
        hp=300,
        speed=350,
        attack=10,
        attack_speed=1.0,
        attack_range=100.0,
        stagger_gage=10,
        weaknesses=None,
        strengths=None,
    ),
    # 슬라임
    1: MonsterData(
        monster_id=1,
        monster_type=0,  # 일반
        monster_name="슬라임",
        hp=250,
        speed=200,
        attack=10,
        attack_speed=1.0,
        attack_range=100.0,
        stagger_gage=5,
        weaknesses=None,
        strengths=None,
    ),
    # TODO: 더 많은 몬스터 추가
    # 보스 몬스터 예시
    100: MonsterData(
        monster_id=100,
        monster_type=2,  # 보스
        monster_name="던전 보스",
        hp=1000,
        speed=300,
        attack=50,
        attack_speed=1.5,
        attack_range=150.0,
        stagger_gage=50,
        weaknesses=[1, 3],  # 예시
        strengths=[2],  # 예시
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
