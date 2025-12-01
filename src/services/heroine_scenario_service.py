from typing import List, Optional
from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings

from db.config import CONNECTION_URL


class HeroineScenarioService:
    """히로인 시나리오 검색 서비스"""
    
    def __init__(self):
        self.engine = create_engine(CONNECTION_URL)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    def search_scenarios(
        self,
        query: str,
        heroine_id: int,
        max_memory_progress: int,
        limit: int = 3
    ) -> List[dict]:
        """해금된 시나리오 검색
        
        Args:
            query: 검색 쿼리
            heroine_id: 히로인 ID
            max_memory_progress: 현재 기억 진척도 (이하만 검색)
            limit: 최대 결과 수
        
        Returns:
            검색된 시나리오 목록
        """
        # 쿼리 임베딩
        query_embedding = self.embeddings.embed_query(query)
        
        # 벡터 검색 SQL
        sql = text("""
            SELECT id, content, memory_progress,
                   1 - (content_embedding <=> :embedding::vector) as similarity
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress <= :max_progress
            ORDER BY content_embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "embedding": str(query_embedding),
                "heroine_id": heroine_id,
                "max_progress": max_memory_progress,
                "limit": limit
            })
            
            scenarios = []
            for row in result:
                scenarios.append({
                    "id": row.id,
                    "content": row.content,
                    "memory_progress": row.memory_progress,
                    "similarity": row.similarity
                })
            
            return scenarios
    
    def get_scenarios_by_progress(
        self,
        heroine_id: int,
        memory_progress: int
    ) -> List[dict]:
        """특정 진척도의 시나리오 조회"""
        sql = text("""
            SELECT id, title, content, memory_progress
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress = :progress
            ORDER BY id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "heroine_id": heroine_id,
                "progress": memory_progress
            })
            
            return [dict(row._mapping) for row in result]
    
    def get_all_unlocked_scenarios(
        self,
        heroine_id: int,
        max_memory_progress: int
    ) -> List[dict]:
        """해금된 모든 시나리오 조회"""
        sql = text("""
            SELECT id, title, content, memory_progress
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress <= :max_progress
            ORDER BY memory_progress, id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "heroine_id": heroine_id,
                "max_progress": max_memory_progress
            })
            
            return [dict(row._mapping) for row in result]


# 싱글톤 인스턴스
heroine_scenario_service = HeroineScenarioService()

