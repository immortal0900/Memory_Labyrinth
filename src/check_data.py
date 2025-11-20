from db.DBRepository import DBRepository
from db.config import DBCollectionName
import json

def check_data():
    print("=== DB 데이터 확인 ===\n")

    # 1. 몬스터 목록 확인
    print("[몬스터 목록]")
    repo = DBRepository(DBCollectionName.MONSTER)
    monsters = repo.select_data()
    
    for m in monsters:
        print(f"- 이름: {m['name']}")
        # JSON 데이터는 딕셔너리로 변환해서 보기 좋게 출력
        data = m['data']
        if isinstance(data, str):
            data = json.loads(data)
        print(f"  정보: {data}")
        print("")

    # 2. 아이템 목록 확인
    print("[아이템 목록]")
    repo = DBRepository(DBCollectionName.ITEM)
    items = repo.select_data()

    for i in items:
        print(f"- 이름: {i['name']}")
        data = i['data']
        if isinstance(data, str):
            data = json.loads(data)
        print(f"  정보: {data}")
        print("")

if __name__ == "__main__":
    check_data()

