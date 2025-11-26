from db.VectorDBRepository import VectorDBRepository
from db.config import DBCollectionName
from enums.EmbeddingModel import EmbeddingModel
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter

def test_rag():
    print("=== RAG 기능 테스트 시작 ===")

    # 0. 설정
    # RAG용 DBRepository 생성 (임베딩 모델 지정 필수)
    # 유료 모델인 TEXT_EMBEDDING_3_SMALL 사용 (OpenAI 키 필요)
    repo = VectorDBRepository(
        collection_name=DBCollectionName.WORLD_SCENARIO,
        embedding_model=EmbeddingModel.TEXT_EMBEDDING_3_SMALL 
    )

    # 1. 문서 읽기 및 저장
    print("\n1. 문서 읽기 및 벡터 저장 중...")
    try:
        # 텍스트 파일 로드
        loader = TextLoader("src/data/world_setting.txt", encoding="utf-8")
        documents = loader.load()
        
        # 문서를 적절한 크기로 자르기 (너무 길면 검색 정확도가 떨어짐)
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)
        
        # DB에 저장 (벡터 변환은 내부에서 자동으로 처리됨)
        # 주의: add_documents는 계속 추가되므로, 테스트할 때는 중복 방지를 위해 
        # 실제로는 delete를 먼저 하거나 해야 하지만, 여기서는 단순히 추가만 합니다.
        repo.add_documents(docs)
        print(f"-> {len(docs)}개의 청크로 나누어 저장 완료!")
        
    except Exception as e:
        print(f"-> 저장 실패 (API Key 확인 필요): {e}")
        return

    # 2. 검색 테스트
    print("\n2. 검색 테스트 (질문: '던전 3층에는 누가 살아?')")
    
    query = "던전 3층에는 누가 살아?"
    results = repo.search(query, k=3) # 가장 유사한 문서 3개 가져오기

    if results:
        print("\n[검색 결과]")
        for i, doc in enumerate(results):
            print(f"{i+1}. {doc.page_content.strip()[:100]}...") # 100자만 출력
    else:
        print("-> 검색 결과가 없습니다.")

    print("\n=== 테스트 종료 ===")

if __name__ == "__main__":
    test_rag()

