

from core.game_dto.ItemData import ItemData
from core.game_dto.WeaponData import WeaponData
from core.game_dto.AccessoryItemData import AccessoryItemData

cache_items = [
    # weaponType 1 : 숏소드 / 한손검
    ItemData(itemId=0, itemName="일반 숏소드", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=0, weaponType=1, weaponName="일반 숏소드",
            rarity=0, attackPower=10, staggerPower=2,
            modifier={"strength": 0.7, "dexterity": 0.3, "intelligence": 0}
        )
    ),
    ItemData(itemId=1, itemName="고급 숏소드", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=1, weaponType=1, weaponName="고급 숏소드",
            rarity=1, attackPower=12, staggerPower=2,
            modifier={"strength": 0.7, "dexterity": 0.3, "intelligence": 0}
        )
    ),
    ItemData(itemId=2, itemName="레어 숏소드", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=2, weaponType=1, weaponName="레어 숏소드",
            rarity=2, attackPower=15, staggerPower=2,
            modifier={"strength": 0.7, "dexterity": 0.3, "intelligence": 0}
        )
    ),
    ItemData(itemId=3, itemName="레전드 숏소드", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=3, weaponType=1, weaponName="레전드 숏소드",
            rarity=3, attackPower=20, staggerPower=2,
            modifier={"strength": 0.7, "dexterity": 0.3, "intelligence": 0}
        )
    ),
    ItemData(itemId=4, itemName="일반 한손검", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=4, weaponType=1, weaponName="일반 한손검",
            rarity=0, attackPower=13, staggerPower=2,
            modifier={"strength": 0.5, "dexterity": 0.5, "intelligence": 0}
        )
    ),
    ItemData(itemId=5, itemName="고급 한손검", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=5, weaponType=1, weaponName="고급 한손검",
            rarity=1, attackPower=16, staggerPower=2,
            modifier={"strength": 0.5, "dexterity": 0.5, "intelligence": 0}
        )
    ),
    ItemData(itemId=6, itemName="레어 한손검", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=6, weaponType=1, weaponName="레어 한손검",
            rarity=2, attackPower=18, staggerPower=2,
            modifier={"strength": 0.5, "dexterity": 0.5, "intelligence": 0}
        )
    ),
    ItemData(itemId=7, itemName="레전드 한손검", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=7, weaponType=1, weaponName="레전드 한손검",
            rarity=3, attackPower=22, staggerPower=2,
            modifier={"strength": 0.5, "dexterity": 0.5, "intelligence": 0}
        )
    ),

    # weaponType 2 : 쌍검 / 양손 메서
    ItemData(itemId=20, itemName="일반 쌍검", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=20, weaponType=2, weaponName="일반 쌍검",
            rarity=0, attackPower=6, staggerPower=1,
            modifier={"strength": 0.1, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=21, itemName="고급 쌍검", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=21, weaponType=2, weaponName="고급 쌍검",
            rarity=1, attackPower=9, staggerPower=1,
            modifier={"strength": 0.1, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=22, itemName="레어 쌍검", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=22, weaponType=2, weaponName="레어 쌍검",
            rarity=2, attackPower=11, staggerPower=1,
            modifier={"strength": 0.1, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=23, itemName="레전드 쌍검", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=23, weaponType=2, weaponName="레전드 쌍검",
            rarity=3, attackPower=14, staggerPower=1,
            modifier={"strength": 0.1, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=24, itemName="일반 양손 메서", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=24, weaponType=2, weaponName="일반 양손 메서",
            rarity=0, attackPower=9, staggerPower=1,
            modifier={"strength": 0.3, "dexterity": 0.55, "intelligence": 0}
        )
    ),
    ItemData(itemId=25, itemName="고급 양손 메서", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=25, weaponType=2, weaponName="고급 양손 메서",
            rarity=1, attackPower=11, staggerPower=1,
            modifier={"strength": 0.3, "dexterity": 0.55, "intelligence": 0}
        )
    ),
    ItemData(itemId=26, itemName="레어 양손 메서", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=26, weaponType=2, weaponName="레어 양손 메서",
            rarity=2, attackPower=13, staggerPower=1,
            modifier={"strength": 0.3, "dexterity": 0.55, "intelligence": 0}
        )
    ),
    ItemData(itemId=27, itemName="레전드 양손 메서", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=27, weaponType=2, weaponName="레전드 양손 메서",
            rarity=3, attackPower=17, staggerPower=1,
            modifier={"strength": 0.3, "dexterity": 0.55, "intelligence": 0}
        )
    ),

    # weaponType 3 : 대검 / 드래곤슬레이어
    ItemData(itemId=40, itemName="일반 대검", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=40, weaponType=3, weaponName="일반 대검",
            rarity=0, attackPower=15, staggerPower=5,
            modifier={"strength": 0.75, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=41, itemName="고급 대검", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=41, weaponType=3, weaponName="고급 대검",
            rarity=1, attackPower=21, staggerPower=5,
            modifier={"strength": 0.75, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=42, itemName="레어 대검", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=42, weaponType=3, weaponName="레어 대검",
            rarity=2, attackPower=25, staggerPower=5,
            modifier={"strength": 0.75, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=43, itemName="레전드 대검", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=43, weaponType=3, weaponName="레전드 대검",
            rarity=3, attackPower=32, staggerPower=5,
            modifier={"strength": 0.75, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=44, itemName="일반 드래곤슬레이어", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=44, weaponType=3, weaponName="일반 드래곤슬레이어",
            rarity=0, attackPower=12, staggerPower=5,
            modifier={"strength": 0.2, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=45, itemName="고급 드래곤슬레이어", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=45, weaponType=3, weaponName="고급 드래곤슬레이어",
            rarity=1, attackPower=16, staggerPower=5,
            modifier={"strength": 0.2, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=46, itemName="레어 드래곤슬레이어", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=46, weaponType=3, weaponName="레어 드래곤슬레이어",
            rarity=2, attackPower=21, staggerPower=5,
            modifier={"strength": 0.2, "dexterity": 0.8, "intelligence": 0}
        )
    ),
    ItemData(itemId=47, itemName="레전드 드래곤슬레이어", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=47, weaponType=3, weaponName="레전드 드래곤슬레이어",
            rarity=3, attackPower=26, staggerPower=5,
            modifier={"strength": 0.2, "dexterity": 0.8, "intelligence": 0}
        )
    ),

    # weaponType 4 : 드워프의 망치 / 바이킹의 망치
    ItemData(itemId=60, itemName="일반 드워프의 망치", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=60, weaponType=4, weaponName="일반 드워프의 망치",
            rarity=0, attackPower=22, staggerPower=6,
            modifier={"strength": 0.8, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=61, itemName="고급 드워프의 망치", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=61, weaponType=4, weaponName="고급 드워프의 망치",
            rarity=1, attackPower=24, staggerPower=6,
            modifier={"strength": 0.8, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=62, itemName="레어 드워프의 망치", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=62, weaponType=4, weaponName="레어 드워프의 망치",
            rarity=2, attackPower=27, staggerPower=6,
            modifier={"strength": 0.8, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=63, itemName="레전드 드워프의 망치", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=63, weaponType=4, weaponName="레전드 드워프의 망치",
            rarity=3, attackPower=30, staggerPower=6,
            modifier={"strength": 0.8, "dexterity": 0.2, "intelligence": 0}
        )
    ),
    ItemData(itemId=64, itemName="일반 바이킹의 망치", itemType=1, rarity=0,
        weapon=WeaponData(
            weaponId=64, weaponType=4, weaponName="일반 바이킹의 망치",
            rarity=0, attackPower=20, staggerPower=6,
            modifier={"strength": 0.85, "dexterity": 0.15, "intelligence": 0}
        )
    ),
    ItemData(itemId=65, itemName="고급 바이킹의 망치", itemType=1, rarity=1,
        weapon=WeaponData(
            weaponId=65, weaponType=4, weaponName="고급 바이킹의 망치",
            rarity=1, attackPower=23, staggerPower=6,
            modifier={"strength": 0.85, "dexterity": 0.15, "intelligence": 0}
        )
    ),
    ItemData(itemId=66, itemName="레어 바이킹의 망치", itemType=1, rarity=2,
        weapon=WeaponData(
            weaponId=66, weaponType=4, weaponName="레어 바이킹의 망치",
            rarity=2, attackPower=25, staggerPower=6,
            modifier={"strength": 0.85, "dexterity": 0.15, "intelligence": 0}
        )
    ),
    ItemData(itemId=67, itemName="레전드 바이킹의 망치", itemType=1, rarity=3,
        weapon=WeaponData(
            weaponId=67, weaponType=4, weaponName="레전드 바이킹의 망치",
            rarity=3, attackPower=28, staggerPower=6,
            modifier={"strength": 0.85, "dexterity": 0.15, "intelligence": 0}
        )
    ),
     
    ItemData(
        itemId=100, itemName="바위 목걸이", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=100, accessoryName="바위 목걸이",
            description="데미지 감소 -15%"
        )
    ),
    ItemData(
        itemId=101, itemName="귀족의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=101, accessoryName="귀족의 반지",
            description="체력 최대시 데미지 증가 +20%"
        )
    ),
    ItemData(
        itemId=102, itemName="회복의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=102, accessoryName="회복의 반지",
            description="5초마다 체력 +5"
        )
    ),
    ItemData(
        itemId=103, itemName="다곤의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=103, accessoryName="다곤의 반지",
            description="힘, 기량, 지능 +3"
        )
    ),
    ItemData(
        itemId=104, itemName="증오의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=104, accessoryName="증오의 반지",
            description="받는 데미지 +20% 주는 데미지 +20%"
        )
    ),
    ItemData(
        itemId=105, itemName="기민함의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=105, accessoryName="기민함의 반지",
            description="이동속도 +20%"
        )
    ),
    ItemData(
        itemId=106, itemName="중량의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=106, accessoryName="중량의 반지",
            description="공격속도 -50% 주는 데미지 +100%"
        )
    ),
    ItemData(
        itemId=107, itemName="마법사의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=107, accessoryName="마법사의 반지",
            description="지능 +7"
        )
    ),
    ItemData(
        itemId=108, itemName="전사의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=108, accessoryName="전사의 반지",
            description="힘 +7"
        )
    ),
    ItemData(
        itemId=109, itemName="도적의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=109, accessoryName="도적의 반지",
            description="기량 +7"
        )
    ),
    ItemData(
        itemId=110, itemName="고양이의 털", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=110, accessoryName="고양이의 털",
            description="공격 속도 +20%"
        )
    ),
    ItemData(
        itemId=111, itemName="사슬 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=111, accessoryName="사슬 반지",
            description="스킬 데미지 +30%"
        )
    ),
    ItemData(
        itemId=112, itemName="광전사의 팔찌", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=112, accessoryName="광전사의 팔찌",
            description="체력이 적을수록 데미지 증가 (체력 10%에서 최대 50% 증가)"
        )
    ),
    ItemData(
        itemId=113, itemName="활력의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=113, accessoryName="활력의 반지",
            description="최대 체력 증가 50"
        )
    ),
    ItemData(
        itemId=114, itemName="심연의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=114, accessoryName="심연의 반지",
            description="최대체력 -100, 힘, 기량, 지능 +5"
        )
    ),
    ItemData(
        itemId=115, itemName="귀감 브로치", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=115, accessoryName="귀감 브로치",
            description="이동속도 -20%, 받는 데미지 -20%"
        )
    ),
    ItemData(
        itemId=116, itemName="마녀의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=116, accessoryName="마녀의 반지",
            description="받는 데미지 +30%, 가하는 피해 흡혈 5%"
        )
    ),
    ItemData(
        itemId=117, itemName="근력의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=117, accessoryName="근력의 반지",
            description="힘 +10, 기량 -7"
        )
    ),
    ItemData(
        itemId=118, itemName="연결의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=118, accessoryName="연결의 반지",
            description="기량 +10, 힘 -7"
        )
    ),
    ItemData(
        itemId=119, itemName="불굴의 반지", itemType=1, rarity=None,
        accessory=AccessoryItemData(
            accessoryId=119, accessoryName="불굴의 반지",
            description="상시 슈퍼아머, 공격속도 -20%, 이동속도 -20%"
        )
    ),
]