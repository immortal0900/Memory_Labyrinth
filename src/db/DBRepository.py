import json
from typing import List, Any, Dict
from sqlalchemy import create_engine, text
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from db.config import CONNECTION_URL, DBCollectionName
from enums.EmbeddingModel import EmbeddingModel

class DBRepository:
    def __init__(self, collection_name: DBCollectionName, embedding_model: EmbeddingModel):
        """
        초기화 메서드
        :param collection_name: 작업할 테이블 이름 (DBCollectionName Enum 사용)
        :param embedding_model: 벡터 검색을 사용할 경우 임베딩 모델 지정
        """
        self.collection_name = collection_name
        self.db_url = CONNECTION_URL
        
        # 일반 DB 작업용 엔진 생성
        self.engine = create_engine(self.db_url)
        
        # RAG용 벡터 저장소 (모델이 지정된 경우에만 생성)
        self.store = None
        if embedding_model:
            self.store = PGVector(
                embeddings=self._resolve_embedding(embedding_model),
                collection_name=collection_name,
                connection=self.db_url,
                use_jsonb=True,
            )

    def _resolve_embedding(self, model: EmbeddingModel):
        """임베딩 모델 Enum을 실제 객체로 변환하는 내부 함수"""
        if model in {
            EmbeddingModel.TEXT_EMBEDDING_3_LARGE,
            EmbeddingModel.TEXT_EMBEDDING_3_MEDIUM,
            EmbeddingModel.TEXT_EMBEDDING_3_SMALL,
        }:
            # OpenAI API Key가 환경변수에 있어야 함
            return OpenAIEmbeddings(model=model.value)

        if model in {
            EmbeddingModel.BGE_M3,
            EmbeddingModel.BGE_UPSKYY_KOREAN,
        }:
            return HuggingFaceEmbeddings(model_name=model.value)

        raise ValueError(f"지원하지 않는 임베딩 모델입니다: {model}")

    # ---------------------------------------------------------
    # 일반 DB CRUD 메서드
    # ---------------------------------------------------------

    def insert_data(self, data: Dict[str, Any]):
        """
        데이터를 DB에 저장합니다.
        예시: repo.insert_data({"name": "슬라임", "data": {"hp": 10}})
        """
        # 딕셔너리의 키를 컬럼명으로, 값을 데이터로 사용
        columns = list(data.keys())
        
        # SQL 쿼리 생성: INSERT INTO table (col1, col2) VALUES (:col1, :col2)
        column_str = ", ".join(columns)
        value_placeholders = ", ".join([f":{col}" for col in columns])
        
        sql = f"INSERT INTO {self.collection_name} ({column_str}) VALUES ({value_placeholders})"
        
        # 딕셔너리나 리스트 타입의 값은 JSON 문자열로 변환 (JSONB 컬럼 호환성 위해)
        processed_data = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                processed_data[k] = json.dumps(v, ensure_ascii=False)
            else:
                processed_data[k] = v
        
        # 실행 (자동 커밋)
        with self.engine.connect() as conn:
            conn.execute(text(sql), processed_data)
            conn.commit()
            
    def select_data(self, condition: str = None, params: Dict = None) -> List[Dict]:
        """
        데이터를 조회합니다.
        :param condition: SQL WHERE 조건절 (예: "id = :id")
        :param params: 조건절에 들어갈 파라미터 (예: {"id": 1})
        """
        sql = f"SELECT * FROM {self.collection_name}"
        if condition:
            sql += f" WHERE {condition}"
            
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            # 결과를 딕셔너리 리스트로 변환
            return [dict(row._mapping) for row in result]

    def update_data(self, update_values: Dict[str, Any], condition: str, params: Dict = None):
        """
        데이터를 수정합니다.
        :param update_values: 수정할 컬럼과 값 (예: {"name": "새이름"})
        :param condition: 수정할 대상 조건 (예: "id = :id") 
        """
        set_clause = ", ".join([f"{key} = :{key}" for key in update_values.keys()])
        sql = f"UPDATE {self.collection_name} SET {set_clause} WHERE {condition}"
        
        # 딕셔너리나 리스트 타입의 값은 JSON 문자열로 변환
        processed_update_values = {}
        for k, v in update_values.items():
            if isinstance(v, (dict, list)):
                processed_update_values[k] = json.dumps(v, ensure_ascii=False)
            else:
                processed_update_values[k] = v

        # update_values와 params를 합쳐서 실행 파라미터 생성
        execution_params = {**processed_update_values, **(params or {})}
        
        with self.engine.connect() as conn:
            conn.execute(text(sql), execution_params)
            conn.commit()

    def delete_data(self, condition: str, params: Dict = None):
        """
        데이터를 삭제합니다.
        :param condition: 삭제할 대상 조건 (예: "id = :id")
        """
        sql = f"DELETE FROM {self.collection_name} WHERE {condition}"
        
        with self.engine.connect() as conn:
            conn.execute(text(sql), params or {})
            conn.commit()

    # ---------------------------------------------------------
    # RAG 벡터 검색 메서드 (기존 기능)
    # ---------------------------------------------------------

    def add_documents(self, docs: List[Document]):
        """문서(텍스트)를 벡터로 변환하여 저장합니다."""
        if not self.store:
            raise ValueError("임베딩 모델이 설정되지 않았습니다.")
        self.store.add_documents(docs)

    def search(self, query: str, k=5):
        return self.store.similarity_search(query, k=k)
    
    

def resolve_embedding(model: EmbeddingModel):
    """모델 Enum → 실제 Embedding 객체로 변환"""

    # OpenAI 계열
    if model in {
        EmbeddingModel.TEXT_EMBEDDING_3_LARGE,
        EmbeddingModel.TEXT_EMBEDDING_3_MEDIUM,
        EmbeddingModel.TEXT_EMBEDDING_3_SMALL,
    }:
        return OpenAIEmbeddings(model=model.value)

    # HuggingFace 계열
    if model in {
        EmbeddingModel.BGE_M3,
        EmbeddingModel.BGE_UPSKYY_KOREAN,
    }:
        return HuggingFaceEmbeddings(model_name=model.value)

    raise ValueError(f"Unknown embedding model: {model}")
