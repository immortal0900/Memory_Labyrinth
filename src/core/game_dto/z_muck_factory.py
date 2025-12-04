import random
from typing import List
from core.game_dto.DungeonData import DungeonData
from core.game_dto.DungeonPlayerData import DungeonPlayerData
from core.game_dto.RoomData import RoomData
from core.game_dto.RewardTable import RewardTable
from core.game_dto.SkillData import SkillData
from core.game_dto.StatData import StatData
from core.game_dto.WeaponData import WeaponData
from core.game_dto.MonsterSpawnData import MonsterSpawnData


class MockFactory:

    @staticmethod
    def create_monster_spawn():
        return MonsterSpawnData(
            monsterId=random.randint(1, 10),
            posX=random.random(),
            posY=random.random()
        )

    @staticmethod
    def create_reward():
        return RewardTable(
            rarity=random.randint(1, 5),
            itemTable=[random.randint(100, 200) for _ in range(3)]
        )

    @staticmethod
    def create_room(room_id: int):
        room_type = random.choice([0, 1, 2, 3])

        return RoomData(
            roomId=room_id,
            type=room_type,
            size=random.randint(5, 15),
            neighbors=[room_id - 1 if room_id > 1 else 0],
            monsters=[MockFactory.create_monster_spawn() for _ in range(3)] if room_type == 1 else [],
            eventType=random.randint(1, 3) if room_type == 2 else None
        )

    @staticmethod
    def create_stat():
        return StatData(
            hp=random.randint(250, 500),
            moveSpeed=round(random.uniform(1.0, 2.0), 2),
            cooldownReduction=round(random.uniform(1.0, 2.0), 2),
            strength=random.randint(10, 20),
            dexterity=random.randint(10, 20),
            intelligence=random.choice([None, random.randint(1, 10)]),
            critChance=round(random.uniform(20, 50), 2),
            skillDamageMultiplier=round(random.uniform(1, 3), 2),
            autoAttackMultiplier=round(random.uniform(1, 3), 2),
            attackSpeed=round(random.uniform(1.0, 2.5), 2)
        )

    @staticmethod
    def create_skill():
        return SkillData(
            passiveSkillId=random.randint(1, 10),
            passiveSkillLevel=random.randint(1, 4),
            activeSkillId=random.randint(1, 10),
            activeSkillLevel=random.randint(1, 4)
        )

    # 디폴트는 레어 쌍검 기준으로 맞춤
    @staticmethod
    def create_weapon():
        return WeaponData(
            weaponId=22, weaponType=2, weaponName="레어 쌍검",
            rarity=2, attackPower=11, staggerPower=1,
            modifier={"strength": 0.1, "dexterity": 0.8, "intelligence": 0.1}
        )

    @staticmethod
    def create_dungeon_player(player_id: int):
        return DungeonPlayerData(
            playerId=player_id,
            heroineId=random.randint(1, 3),
            affection=random.randint(1, 10),
            sanity=random.randint(0, 100),
            scenarioLevel=random.randint(1, 10),
            difficulty=random.randint(0, 2),
            stats=MockFactory.create_stat(),
            skills=MockFactory.create_skill(),
            weapon=MockFactory.create_weapon(),
            inventory=[0,21,42]
        )

    @staticmethod
    def create_dungeon_data(player_count: int, room_count: int):
        return DungeonData(
            playerIds=list(range(1, player_count + 1)),
            heroineId=[1],
            rooms=[MockFactory.create_room(i + 1) for i in range(room_count)],
            rewards=[MockFactory.create_reward() for _ in range(3)]
        )


