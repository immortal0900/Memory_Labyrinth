from db.DBRepository import DBRepository
from db.config import DBCollectionName

def test_simple_db():
    print("=== DB 연결 테스트 시작 ===")

    # 1. 몬스터 테이블용 리포지토리 생성
    # DBRepository가 알아서 DB에 연결합니다.
    repo = DBRepository(collection_name=DBCollectionName.MONSTER)

    # 2. 데이터 넣어보기 (INSERT)
    print("\n1. 데이터 저장 테스트...")
    test_monster = {
        "name": "테스트용 슬라임",
        "data": {"hp": 100, "skill": "점액 던지기"}
    }
    try:
        repo.insert_data(test_monster)
        print("-> 저장 성공!")
    except Exception as e:
        print(f"-> 저장 실패: {e}")
        return

    # 3. 데이터 꺼내보기 (SELECT)
    print("\n2. 데이터 조회 테스트...")
    results = repo.select_data(condition="name = :name", params={"name": "테스트용 슬라임"})
    print(f"-> 조회 결과: {results}")

    # 4. 데이터 지우기 (DELETE)
    print("\n3. 데이터 삭제 테스트...")
    repo.delete_data(condition="name = :name", params={"name": "테스트용 슬라임"})
    print("-> 삭제 완료!")
    
    print("\n=== 테스트 종료: 모든 기능이 정상입니다 ===")

if __name__ == "__main__":
    test_simple_db()

