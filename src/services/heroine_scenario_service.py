from typing import List, Optional
from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings

from db.config import CONNECTION_URL


# 동의어 사전 (쿼리 확장용)
SYNONYM_MAP = {
    "고향": [
        "어린 시절",
        "태어난 곳",
        "자란 곳",
        "출신",
        "가족과 살던 곳",
        "어렸을 때",
    ],
    "가족": ["부모", "아버지", "어머니", "형제", "자매", "가문", "집안"],
    "친구": ["우정", "동료", "함께", "친한 사람"],
    "과거": ["예전", "옛날", "이전", "그때", "어린 시절"],
    "트라우마": ["상처", "아픔", "고통", "슬픔", "두려움"],
    "비밀": ["숨기고 있는", "감추고 있는", "말하지 못한"],
}


class HeroineScenarioService:
    """히로인 시나리오 검색 서비스"""

    def __init__(self):
        self.engine = create_engine(CONNECTION_URL)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    def _expand_query(self, query: str) -> str:
        """쿼리 확장 - 동의어 추가

        사용자 질문에 동의어를 추가하여 검색 정확도를 높입니다.
        예: "고향" -> "고향 어린 시절 태어난 곳 자란 곳"

        Args:
            query: 원본 쿼리

        Returns:
            확장된 쿼리
        """
        expanded_terms = [query]

        for keyword, synonyms in SYNONYM_MAP.items():
            if keyword in query:
                expanded_terms.extend(synonyms)

        expanded_query = " ".join(expanded_terms)
        print(f"[DEBUG] 쿼리 확장: {query} -> {expanded_query}")
        return expanded_query

    def search_scenarios(
        self, query: str, heroine_id: int, max_memory_progress: int, limit: int = 3
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
        # 쿼리 확장 (동의어 추가)
        expanded_query = self._expand_query(query)

        # 확장된 쿼리 임베딩
        query_embedding = self.embeddings.embed_query(expanded_query)

        # 벡터 검색 SQL
        sql = text(
            """
            SELECT id, content, memory_progress,
                   1 - (content_embedding <=> CAST(:embedding AS vector)) as similarity
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress <= :max_progress
            ORDER BY content_embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "embedding": str(query_embedding),
                    "heroine_id": heroine_id,
                    "max_progress": max_memory_progress,
                    "limit": limit,
                },
            )

            scenarios = []
            for row in result:
                scenarios.append(
                    {
                        "id": row.id,
                        "content": row.content,
                        "memory_progress": row.memory_progress,
                        "similarity": row.similarity,
                    }
                )

            return scenarios

    def get_scenarios_by_progress(
        self, heroine_id: int, memory_progress: int
    ) -> List[dict]:
        """특정 진척도의 시나리오 조회"""
        sql = text(
            """
            SELECT id, title, content, memory_progress
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress = :progress
            ORDER BY id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql, {"heroine_id": heroine_id, "progress": memory_progress}
            )

            return [dict(row._mapping) for row in result]

    def get_all_unlocked_scenarios(
        self, heroine_id: int, max_memory_progress: int
    ) -> List[dict]:
        """해금된 모든 시나리오 조회"""
        sql = text(
            """
            SELECT id, title, content, memory_progress
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress <= :max_progress
            ORDER BY memory_progress, id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql, {"heroine_id": heroine_id, "max_progress": max_memory_progress}
            )

            return [dict(row._mapping) for row in result]


# 싱글톤 인스턴스
heroine_scenario_service = HeroineScenarioService()
