from typing import List
from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings

from db.config import CONNECTION_URL

# 하이브리드 검색 가중치
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6


class SageScenarioService:
    """대현자 시나리오 검색 서비스"""

    def __init__(self):
        self.engine = create_engine(CONNECTION_URL, pool_pre_ping=True)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    def search_scenarios(
        self, query: str, max_scenario_level: int, limit: int = 3
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
        sql = text(
            """
            SELECT id, content, scenario_level,
                   1 - (content_embedding <=> CAST(:embedding AS vector)) as similarity
            FROM sage_scenarios
            WHERE scenario_level <= :max_level
            ORDER BY content_embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "embedding": str(query_embedding),
                    "max_level": max_scenario_level,
                    "limit": limit,
                },
            )

            scenarios = []
            for row in result:
                scenarios.append(
                    {
                        "id": row.id,
                        "content": row.content,
                        "scenario_level": row.scenario_level,
                        "similarity": row.similarity,
                    }
                )

            return scenarios

    def search_scenarios_hybrid(
        self, query: str, max_scenario_level: int, limit: int = 3
    ) -> List[dict]:
        """BM25 + Vector 하이브리드 검색

        ParadeDB pg_search를 사용한 BM25 검색과 벡터 유사도 검색을 결합합니다.

        Args:
            query: 검색 쿼리
            max_scenario_level: 현재 시나리오 레벨 (이하만 검색)
            limit: 최대 결과 수

        Returns:
            검색된 시나리오 목록 (combined_score 기준 정렬)
        """
        # 쿼리 임베딩
        query_embedding = self.embeddings.embed_query(query)

        # 하이브리드 검색 SQL (BM25 + Vector)
        sql = text(
            """
            WITH bm25_results AS (
                SELECT id, paradedb.score(id) as bm25_score
                FROM sage_scenarios.search(
                    :query,
                    limit_rows => 100
                )
                WHERE scenario_level <= :max_level
            ),
            vector_results AS (
                SELECT id, 
                       1 - (content_embedding <=> CAST(:embedding AS vector)) as vector_score
                FROM sage_scenarios
                WHERE scenario_level <= :max_level
            )
            SELECT 
                s.id, 
                s.content, 
                s.scenario_level,
                s.metadata,
                COALESCE(b.bm25_score, 0) as bm25_score,
                v.vector_score,
                (COALESCE(b.bm25_score, 0) * :bm25_weight + v.vector_score * :vector_weight) as combined_score
            FROM sage_scenarios s
            LEFT JOIN bm25_results b ON s.id = b.id
            JOIN vector_results v ON s.id = v.id
            WHERE s.scenario_level <= :max_level
            ORDER BY combined_score DESC
            LIMIT :limit
        """
        )

        # self.engine.connect(): SQLAlchemy 엔진에서 데이터베이스 연결 객체를 생성
        # with 문: 컨텍스트 매니저로 연결을 자동으로 열고 닫음 (예외 발생 시에도 안전하게 종료)
        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "query": query,
                    "embedding": str(query_embedding),
                    "max_level": max_scenario_level,
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
                        "scenario_level": row.scenario_level,
                        "metadata": row.metadata,
                        "bm25_score": row.bm25_score,
                        "vector_score": row.vector_score,
                        "combined_score": row.combined_score,
                    }
                )

            return scenarios

    def search_scenarios_with_keywords(
        self, query: str, max_scenario_level: int, limit: int = 3
    ) -> List[dict]:
        """키워드 메타데이터 기반 검색 (BM25 인덱스 없을 때 대안)

        metadata의 keywords 필드를 JSONB 검색으로 활용합니다.

        Args:
            query: 검색 쿼리
            max_scenario_level: 현재 시나리오 레벨 (이하만 검색)
            limit: 최대 결과 수

        Returns:
            검색된 시나리오 목록
        """
        query_embedding = self.embeddings.embed_query(query)

        # 쿼리에서 키워드 추출 (공백으로 분리)
        keywords = query.split()

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
                FROM sage_scenarios
                WHERE scenario_level <= :max_level
            )
            SELECT 
                s.id, 
                s.content, 
                s.scenario_level,
                s.metadata,
                ks.keyword_match_count,
                1 - (s.content_embedding <=> CAST(:embedding AS vector)) as vector_score,
                (CAST(ks.keyword_match_count AS FLOAT) / 10.0 * :bm25_weight + 
                 (1 - (s.content_embedding <=> CAST(:embedding AS vector))) * :vector_weight) as combined_score
            FROM sage_scenarios s
            JOIN keyword_scores ks ON s.id = ks.id
            WHERE s.scenario_level <= :max_level
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
                    "max_level": max_scenario_level,
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
                        "scenario_level": row.scenario_level,
                        "metadata": row.metadata,
                        "keyword_match_count": row.keyword_match_count,
                        "vector_score": row.vector_score,
                        "combined_score": row.combined_score,
                    }
                )

            return scenarios

    def search_scenarios_pgroonga(
        self, query: str, max_scenario_level: int, limit: int = 3
    ) -> List[dict]:
        """PGroonga + Vector 하이브리드 검색 (Supabase용)

        PGroonga의 다국어 Full Text Search와 벡터 유사도 검색을 결합합니다.
        참고: https://supabase.com/docs/guides/database/extensions/pgroonga

        Args:
            query: 검색 쿼리
            max_scenario_level: 현재 시나리오 레벨 (이하만 검색)
            limit: 최대 결과 수

        Returns:
            검색된 시나리오 목록 (combined_score 기준 정렬)
        """
        query_embedding = self.embeddings.embed_query(query)

        # PGroonga + Vector 하이브리드 검색
        sql = text(
            """
            WITH pgroonga_results AS (
                SELECT id,
                       pgroonga_score(tableoid, ctid) as pgroonga_score
                FROM sage_scenarios
                WHERE content &@~ :query
                  AND scenario_level <= :max_level
            ),
            vector_results AS (
                SELECT id, 
                       1 - (content_embedding <=> CAST(:embedding AS vector)) as vector_score
                FROM sage_scenarios
                WHERE scenario_level <= :max_level
            )
            SELECT 
                s.id, 
                s.content, 
                s.scenario_level,
                s.metadata,
                COALESCE(p.pgroonga_score, 0) as pgroonga_score,
                v.vector_score,
                (COALESCE(p.pgroonga_score, 0) / 10.0 * :bm25_weight + v.vector_score * :vector_weight) as combined_score
            FROM sage_scenarios s
            LEFT JOIN pgroonga_results p ON s.id = p.id
            JOIN vector_results v ON s.id = v.id
            WHERE s.scenario_level <= :max_level
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
                    "max_level": max_scenario_level,
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
                        "scenario_level": row.scenario_level,
                        "metadata": row.metadata,
                        "pgroonga_score": row.pgroonga_score,
                        "vector_score": row.vector_score,
                        "combined_score": row.combined_score,
                    }
                )

            return scenarios

    def get_scenarios_by_level(self, scenario_level: int) -> List[dict]:
        """특정 레벨의 시나리오 조회"""
        sql = text(
            """
            SELECT id, title, content, scenario_level
            FROM sage_scenarios
            WHERE scenario_level = :level
            ORDER BY id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(sql, {"level": scenario_level})
            return [dict(row._mapping) for row in result]

    def get_all_unlocked_scenarios(self, max_scenario_level: int) -> List[dict]:
        """해금된 모든 시나리오 조회"""
        sql = text(
            """
            SELECT id, title, content, scenario_level
            FROM sage_scenarios
            WHERE scenario_level <= :max_level
            ORDER BY scenario_level, id
        """
        )

        with self.engine.connect() as conn:
            result = conn.execute(sql, {"max_level": max_scenario_level})
            return [dict(row._mapping) for row in result]


# 싱글톤 인스턴스
sage_scenario_service = SageScenarioService()
