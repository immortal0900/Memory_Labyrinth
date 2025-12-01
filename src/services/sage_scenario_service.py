from typing import List
from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings

from db.config import CONNECTION_URL


class SageScenarioService:
    """대현자 시나리오 검색 서비스"""
    
    def __init__(self):
        self.engine = create_engine(CONNECTION_URL)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    def search_scenarios(
        self,
        query: str,
        max_scenario_level: int,
        limit: int = 3
    ) -> List[dict]:
        """해금된 시나리오 검색
        
        Args:
            query: 검색 쿼리
            max_scenario_level: 현재 시나리오 레벨 (이하만 검색)
            limit: 최대 결과 수
        
        Returns:
            검색된 시나리오 목록
        """
        # 쿼리 임베딩
        query_embedding = self.embeddings.embed_query(query)
        
        # 벡터 검색 SQL
        sql = text("""
            SELECT id, content, scenario_level,
                   1 - (content_embedding <=> :embedding::vector) as similarity
            FROM sage_scenarios
            WHERE scenario_level <= :max_level
            ORDER BY content_embedding <=> :embedding::vector
            LIMIT :limit
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "embedding": str(query_embedding),
                "max_level": max_scenario_level,
                "limit": limit
            })
            
            scenarios = []
            for row in result:
                scenarios.append({
                    "id": row.id,
                    "content": row.content,
                    "scenario_level": row.scenario_level,
                    "similarity": row.similarity
                })
            
            return scenarios
    
    def get_scenarios_by_level(self, scenario_level: int) -> List[dict]:
        """특정 레벨의 시나리오 조회"""
        sql = text("""
            SELECT id, title, content, scenario_level
            FROM sage_scenarios
            WHERE scenario_level = :level
            ORDER BY id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {"level": scenario_level})
            return [dict(row._mapping) for row in result]
    
    def get_all_unlocked_scenarios(self, max_scenario_level: int) -> List[dict]:
        """해금된 모든 시나리오 조회"""
        sql = text("""
            SELECT id, title, content, scenario_level
            FROM sage_scenarios
            WHERE scenario_level <= :max_level
            ORDER BY scenario_level, id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {"max_level": max_scenario_level})
            return [dict(row._mapping) for row in result]


# 싱글톤 인스턴스
sage_scenario_service = SageScenarioService()

