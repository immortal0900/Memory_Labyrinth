import json
from typing import List, Any, Dict
from sqlalchemy import create_engine, text
from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from db.config import CONNECTION_URL, DBCollectionName
from enums.EmbeddingModel import EmbeddingModel


class VectorDBRepository:
    def __init__(
        self, collection_name: DBCollectionName, embedding_model: EmbeddingModel = None
    ):
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
