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

# 하이브리드 검색 가중치
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6


class HeroineScenarioService:
    """히로인 시나리오 검색 서비스"""

    def __init__(self):
        self.engine = create_engine(CONNECTION_URL, pool_pre_ping=True)
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

    def search_scenarios_hybrid(
        self, query: str, heroine_id: int, max_memory_progress: int, limit: int = 3
    ) -> List[dict]:
        """BM25 + Vector 하이브리드 검색

        ParadeDB pg_search를 사용한 BM25 검색과 벡터 유사도 검색을 결합합니다.

        Args:
            query: 검색 쿼리
            heroine_id: 히로인 ID
            max_memory_progress: 현재 기억 진척도 (이하만 검색)
            limit: 최대 결과 수

        Returns:
            검색된 시나리오 목록 (combined_score 기준 정렬)
        """
        # 쿼리 확장 (동의어 추가)
        expanded_query = self._expand_query(query)

        # 확장된 쿼리 임베딩
        query_embedding = self.embeddings.embed_query(expanded_query)

        # 하이브리드 검색 SQL (BM25 + Vector)
        sql = text(
            """
            WITH bm25_results AS (
                SELECT id, paradedb.score(id) as bm25_score
                FROM heroine_scenarios.search(
                    :query,
                    limit_rows => 100
                )
                WHERE heroine_id = :heroine_id 
                  AND memory_progress <= :max_progress
            ),
            vector_results AS (
                SELECT id, 
                       1 - (content_embedding <=> CAST(:embedding AS vector)) as vector_score
                FROM heroine_scenarios
                WHERE heroine_id = :heroine_id 
                  AND memory_progress <= :max_progress
            )
            SELECT 
                h.id, 
                h.content, 
                h.memory_progress,
                h.metadata,
                COALESCE(b.bm25_score, 0) as bm25_score,
                v.vector_score,
                (COALESCE(b.bm25_score, 0) * :bm25_weight + v.vector_score * :vector_weight) as combined_score
            FROM heroine_scenarios h
            LEFT JOIN bm25_results b ON h.id = b.id
            JOIN vector_results v ON h.id = v.id
            WHERE h.heroine_id = :heroine_id 
              AND h.memory_progress <= :max_progress
            ORDER BY combined_score DESC
            LIMIT :limit
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "query": expanded_query,
                    "embedding": str(query_embedding),
                    "heroine_id": heroine_id,
                    "max_progress": max_memory_progress,
                    "bm25_weight": BM25_WEIGHT,
                    "vector_weight": VECTOR_WEIGHT,
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
                        "metadata": row.metadata,
                        "bm25_score": row.bm25_score,
                        "vector_score": row.vector_score,
                        "combined_score": row.combined_score,
                    }
                )

            return scenarios

    def search_scenarios_with_keywords(
        self, query: str, heroine_id: int, max_memory_progress: int, limit: int = 3
    ) -> List[dict]:
        """키워드 메타데이터 기반 검색 (BM25 인덱스 없을 때 대안)

        metadata의 keywords 필드를 JSONB 검색으로 활용합니다.

        Args:
            query: 검색 쿼리
            heroine_id: 히로인 ID
            max_memory_progress: 현재 기억 진척도 (이하만 검색)
            limit: 최대 결과 수

        Returns:
            검색된 시나리오 목록
        """
        # 쿼리 확장
        expanded_query = self._expand_query(query)
        query_embedding = self.embeddings.embed_query(expanded_query)

        # 쿼리에서 키워드 추출 (공백으로 분리)
        keywords = expanded_query.split()

        # JSONB 키워드 매칭 + 벡터 검색
        sql = text(
            """
            WITH keyword_scores AS (
                SELECT id,
                       COALESCE(
                           (SELECT COUNT(*) 
                            FROM jsonb_array_elements_text(metadata->'keywords') as kw
                            WHERE kw = ANY(:keywords)
                           ), 0
                       ) as keyword_match_count
                FROM heroine_scenarios
                WHERE heroine_id = :heroine_id 
                  AND memory_progress <= :max_progress
            )
            SELECT 
                h.id, 
                h.content, 
                h.memory_progress,
                h.metadata,
                ks.keyword_match_count,
                1 - (h.content_embedding <=> CAST(:embedding AS vector)) as vector_score,
                (CAST(ks.keyword_match_count AS FLOAT) / 10.0 * :bm25_weight + 
                 (1 - (h.content_embedding <=> CAST(:embedding AS vector))) * :vector_weight) as combined_score
            FROM heroine_scenarios h
            JOIN keyword_scores ks ON h.id = ks.id
            WHERE h.heroine_id = :heroine_id 
              AND h.memory_progress <= :max_progress
            ORDER BY combined_score DESC
            LIMIT :limit
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "keywords": keywords,
                    "embedding": str(query_embedding),
                    "heroine_id": heroine_id,
                    "max_progress": max_memory_progress,
                    "bm25_weight": BM25_WEIGHT,
                    "vector_weight": VECTOR_WEIGHT,
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
                        "metadata": row.metadata,
                        "keyword_match_count": row.keyword_match_count,
                        "vector_score": row.vector_score,
                        "combined_score": row.combined_score,
                    }
                )

            return scenarios

    def search_scenarios_pgroonga(
        self, query: str, heroine_id: int, max_memory_progress: int, limit: int = 3
    ) -> List[dict]:
        """PGroonga + Vector 하이브리드 검색 (Supabase용)

        PGroonga의 다국어 Full Text Search와 벡터 유사도 검색을 결합합니다.
        참고: https://supabase.com/docs/guides/database/extensions/pgroonga

        Args:
            query: 검색 쿼리
            heroine_id: 히로인 ID
            max_memory_progress: 현재 기억 진척도 (이하만 검색)
            limit: 최대 결과 수

        Returns:
            검색된 시나리오 목록 (combined_score 기준 정렬)
        """
        # 쿼리 확장 (동의어 추가)
        expanded_query = self._expand_query(query)
        query_embedding = self.embeddings.embed_query(expanded_query)

        # PGroonga + Vector 하이브리드 검색
        # PGroonga는 &@~ 연산자로 full text search 수행
        sql = text(
            """
            WITH pgroonga_results AS (
                SELECT id,
                       pgroonga_score(tableoid, ctid) as pgroonga_score
                FROM heroine_scenarios
                WHERE content &@~ :query
                  AND heroine_id = :heroine_id 
                  AND memory_progress <= :max_progress
            ),
            vector_results AS (
                SELECT id, 
                       1 - (content_embedding <=> CAST(:embedding AS vector)) as vector_score
                FROM heroine_scenarios
                WHERE heroine_id = :heroine_id 
                  AND memory_progress <= :max_progress
            )
            SELECT 
                h.id, 
                h.content, 
                h.memory_progress,
                h.metadata,
                COALESCE(p.pgroonga_score, 0) as pgroonga_score,
                v.vector_score,
                (COALESCE(p.pgroonga_score, 0) / 10.0 * :bm25_weight + v.vector_score * :vector_weight) as combined_score
            FROM heroine_scenarios h
            LEFT JOIN pgroonga_results p ON h.id = p.id
            JOIN vector_results v ON h.id = v.id
            WHERE h.heroine_id = :heroine_id 
              AND h.memory_progress <= :max_progress
            ORDER BY combined_score DESC
            LIMIT :limit
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "query": query,
                    "embedding": str(query_embedding),
                    "heroine_id": heroine_id,
                    "max_progress": max_memory_progress,
                    "bm25_weight": BM25_WEIGHT,
                    "vector_weight": VECTOR_WEIGHT,
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
                        "metadata": row.metadata,
                        "pgroonga_score": row.pgroonga_score,
                        "vector_score": row.vector_score,
                        "combined_score": row.combined_score,
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

    def get_latest_unlocked_scenario(
        self, heroine_id: int, max_memory_progress: int
    ) -> Optional[dict]:
        """가장 최근에 해금된 시나리오 조회

        현재 기억진척도 이하에서 가장 높은 memory_progress를 가진 시나리오를 반환합니다.
        "최근에 돌아온 기억" 같은 질문에 사용됩니다.

        Args:
            heroine_id: 히로인 ID
            max_memory_progress: 현재 기억 진척도 (이하만 검색)

        Returns:
            가장 최근 해금된 시나리오 또는 None
        """
        sql = text(
            """
            SELECT id, title, content, memory_progress
            FROM heroine_scenarios
            WHERE heroine_id = :heroine_id
              AND memory_progress <= :max_progress
            ORDER BY memory_progress DESC
            LIMIT 1
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql, {"heroine_id": heroine_id, "max_progress": max_memory_progress}
            )
            row = result.fetchone()

            if row:
                return dict(row._mapping)
            return None


# 싱글톤 인스턴스
heroine_scenario_service = HeroineScenarioService()
