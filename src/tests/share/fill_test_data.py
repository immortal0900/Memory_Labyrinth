from db.VectorDBRepository import VectorDBRepository
from db.config import DBCollectionName

def fill_data():
    print("=== 데이터 채워넣기 시작 ===")

    # ---------------------------------------------------------
    # 1. 몬스터 데이터 추가
    # ---------------------------------------------------------
    monster_repo = VectorDBRepository(DBCollectionName.MONSTER)
    
    # 기존 데이터 삭제 (중복 방지)
    monster_repo.delete_data(condition="1=1") 
    print("-> 기존 몬스터 데이터 초기화 완료")

    monsters = [
        {
            "name": "초보자용 슬라임",
            "data": {
                "type": "일반",
                "level": 1,
                "hp": 50,
                "atk": 5,
                "def": 0,
                "pattern": "점프 공격",
                "drop_items": ["점액", "10골드"],
                "desc": "던전 1층에서 흔히 볼 수 있는 약한 몬스터"
            }
        },
        {
            "name": "해골 병사",
            "data": {
                "type": "정예",
                "level": 10,
                "hp": 300,
                "atk": 25,
                "def": 10,
                "pattern": "검 휘두르기",
                "drop_items": ["녹슨 칼", "50골드"],
                "desc": "죽어서도 던전을 지키는 병사"
            }
        },
        {
            "name": "레드 드래곤 (보스)",
            "data": {
                "type": "보스",
                "level": 99,
                "hp": 50000,
                "atk": 500,
                "def": 300,
                "pattern": ["화염 숨결", "꼬리 치기", "날아오르기"],
                "drop_items": ["드래곤의 심장", "전설의 검", "10000골드"],
                "desc": "던전 최하층의 지배자"
            }
        }
    ]

    for m in monsters:
        monster_repo.insert_data(m)
        print(f"-> 몬스터 추가: {m['name']}")

    # ---------------------------------------------------------
    # 2. 아이템 데이터 추가
    # ---------------------------------------------------------
    item_repo = VectorDBRepository(DBCollectionName.ITEM)
    
    # 기존 데이터 삭제
    item_repo.delete_data(condition="1=1")
    print("\n-> 기존 아이템 데이터 초기화 완료")

    items = [
        {
            "name": "녹슨 검",
            "data": {
                "type": "무기",
                "grade": "일반",
                "atk": 5,
                "desc": "오래되어 녹이 슨 검. 베기 힘들다."
            }
        },
        {
            "name": "회복 물약",
            "data": {
                "type": "소모품",
                "grade": "일반",
                "effect": "hp_recover",
                "value": 50,
                "desc": "체력을 50 회복시켜주는 빨간 물약"
            }
        },
        {
            "name": "용사지검",
            "data": {
                "type": "무기",
                "grade": "전설",
                "atk": 100,
                "skill": "용의 분노 (액티브)",
                "desc": "전설적인 용사가 사용했다는 빛나는 검"
            }
        }
    ]

    for i in items:
        item_repo.insert_data(i)
        print(f"-> 아이템 추가: {i['name']}")

    print("\n=== 모든 데이터 저장 완료 ===")

if __name__ == "__main__":
    fill_data()

