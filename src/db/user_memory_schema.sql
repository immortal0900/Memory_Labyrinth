-- ============================================
-- User-NPC 장기 기억 시스템
-- PostgreSQL + pgvector + PGroonga 기반
-- 
-- Mem0 대체용 직접 구현
-- 4요소 하이브리드 검색: 최신도 + 중요도 + 관련도 + 키워드
-- ============================================

-- 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgroonga;

-- 기존 테이블 삭제 (개발용)
-- DROP TABLE IF EXISTS user_memories CASCADE;

-- ============================================
-- 메인 테이블
-- ============================================
CREATE TABLE user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id TEXT NOT NULL,            -- 플레이어 ID
    heroine_id TEXT,                    -- 히로인 ID (letia, lupames, roco)
    
    -- Fact 메타데이터
    speaker TEXT NOT NULL,              -- 발화자: 'user' | 'letia' | 'lupames' | 'roco'
    subject TEXT NOT NULL,              -- 대상: 'user' | 'letia' | 'lupames' | 'roco' | 'world'
    content TEXT NOT NULL,              -- 추출된 사실 내용
    keywords TEXT[],                    -- 검색용 키워드/상위 개념
    content_type TEXT DEFAULT 'fact',   -- 'preference' | 'trait' | 'event' | 'opinion' | 'personal'
    
    -- 검색용
    embedding vector(1536),             -- OpenAI text-embedding-3-small
    importance INT DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
    
    -- Bi-temporal 시간 관리
    valid_at TIMESTAMPTZ DEFAULT NOW(),     -- 사실이 유효해진 시점
    invalid_at TIMESTAMPTZ,                 -- 사실이 무효화된 시점 (NULL이면 현재 유효)
    created_at TIMESTAMPTZ DEFAULT NOW(),   -- DB 레코드 생성 시점
    updated_at TIMESTAMPTZ DEFAULT NOW()    -- DB 레코드 수정 시점
);

-- ============================================
-- 인덱스
-- ============================================

-- 1. 세션 분리용 (player_id + heroine_id + invalid_at)
CREATE INDEX idx_user_memory_session ON user_memories (player_id, heroine_id, invalid_at);

-- 2. pgvector HNSW 인덱스 (코사인 유사도)
CREATE INDEX idx_user_memory_vector ON user_memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64); 
-- ef_construction = 64 인덱스 구축 시 탐색할 이웃 노드의 수, 커지면 정확도 향상 but 인덱스 구축 시간 증가
-- m = 16 각 노드가 연결할 최대 이웃 수, 커지면 정확도 향상 but 메모리 사용량 증가

-- 3. PGroonga 전문검색 인덱스 (한국어 키워드 검색)
CREATE INDEX idx_user_memory_pgroonga ON user_memories USING pgroonga (content);
CREATE INDEX IF NOT EXISTS ix_memories_content_keywords_pgroonga 
ON user_memories 
USING pgroonga (content, keywords);

-- 4. speaker/subject 필터용
CREATE INDEX idx_user_memory_speaker ON user_memories (speaker);
CREATE INDEX idx_user_memory_subject ON user_memories (subject);

-- 5. 시간순 조회용
CREATE INDEX idx_user_memory_created ON user_memories (created_at DESC);

-- ============================================
-- 하이브리드 검색 함수 (4요소 스코어링)
-- ============================================
-- Score = (w_recency * Recency) + (w_importance * Importance) 
--       + (w_relevance * Relevance) + (w_keyword * Keyword)

-- 2-Stage Retrieve-then-Rerank 하이브리드 검색
-- Stage 1: HNSW 벡터 인덱스 + PGroonga 키워드 인덱스로 후보 추출
-- Stage 2: 후보에 대해서만 4요소 가중합 (recency, importance, relevance, keyword)
CREATE OR REPLACE FUNCTION search_user_memories_hybrid(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_query_text TEXT,                      -- 키워드 검색용
    p_query_embedding vector(1536),         -- 벡터 검색용
    p_top_k INTEGER DEFAULT 10,
    p_w_recency FLOAT DEFAULT 0.15,
    p_w_importance FLOAT DEFAULT 0.15,
    p_w_relevance FLOAT DEFAULT 0.50,
    p_w_keyword FLOAT DEFAULT 0.20,
    p_decay_days FLOAT DEFAULT 30.0         -- 30일 기준 감쇠
) RETURNS TABLE (
    id UUID,
    player_id TEXT,
    heroine_id TEXT,
    speaker TEXT,
    subject TEXT,
    content TEXT,
    content_type TEXT,
    importance INT,
    created_at TIMESTAMPTZ,
    recency_score FLOAT,
    importance_score FLOAT,
    relevance_score FLOAT,
    keyword_score FLOAT,
    final_score FLOAT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_candidate_limit INTEGER;
BEGIN
    -- 각 채널(벡터/키워드)에서 가져올 후보 수
    -- GREATEST: 둘 중 큰 값 선택 (최소 20개는 가져옴)
    v_candidate_limit := GREATEST(p_top_k * 3, 20);

    -- ef_search: HNSW 인덱스가 탐색할 이웃 노드 수
    -- WHERE 필터로 일부가 걸러지므로 기본값(40)보다 높게 설정
    -- true: 이 트랜잭션에서만 적용 (다른 쿼리에 영향 없음)
    PERFORM set_config('hnsw.ef_search', '100', true);

    RETURN QUERY

    -- =============================================
    -- Stage 1: 후보 추출 (인덱스 활용)
    -- =============================================
    WITH

    -- 1a. 벡터 검색 후보 (HNSW 인덱스 활용)
    -- ORDER BY <=> LIMIT 패턴이어야 HNSW 인덱스를 탄다
    vector_candidates AS (
        SELECT m.id,
               1 - (m.embedding <=> p_query_embedding) AS vec_score
        FROM user_memories m
        WHERE m.player_id = p_player_id
          AND m.heroine_id = p_heroine_id
          AND m.invalid_at IS NULL
        ORDER BY m.embedding <=> p_query_embedding
        LIMIT v_candidate_limit
    ),

    -- 1b. 키워드 검색 후보 (PGroonga BM25 인덱스 활용)
    -- &@~ : PGroonga 쿼리 매칭 (형태소 분석 포함)
    -- &@  : PGroonga 배열 요소 매칭
    keyword_candidates AS (
        SELECT m.id,
               pgroonga_score(m.tableoid, m.ctid) AS kw_raw_score
        FROM user_memories m
        WHERE m.player_id = p_player_id
          AND m.heroine_id = p_heroine_id
          AND m.invalid_at IS NULL
          AND (m.content &@~ p_query_text OR m.keywords &@ p_query_text)
        ORDER BY pgroonga_score(m.tableoid, m.ctid) DESC
        LIMIT v_candidate_limit
    ),

    -- 1c. 두 결과 합치기 (UNION: 중복 자동 제거)
    all_candidate_ids AS (
        SELECT vc.id FROM vector_candidates vc
        UNION
        SELECT kc.id FROM keyword_candidates kc
    ),

    -- 키워드 점수 정규화를 위한 최대값 (후보 내에서만 계산)
    -- COALESCE: NULL이면 1.0 사용 (키워드 매칭 0건일 때 0 나누기 방지)
    kw_max AS (
        SELECT COALESCE(MAX(kc.kw_raw_score), 1.0) AS val
        FROM keyword_candidates kc
    ),

    -- =============================================
    -- Stage 2: 후보만 대상으로 점수 매기기 (Rerank)
    -- =============================================
    scored AS (
        SELECT
            m.id, m.player_id, m.heroine_id, m.speaker, m.subject,
            m.content, m.content_type, m.importance, m.created_at,
            -- Recency: 지수 감쇠 (오늘=1.0, 30일전=0.37, 60일전=0.14)
            EXP(-EXTRACT(EPOCH FROM (NOW() - m.created_at))
                / (p_decay_days * 86400)) AS recency,
            -- Importance: 1~10 -> 0~1 정규화
            m.importance::FLOAT / 10.0 AS importance_norm,
            -- Relevance: 벡터 후보는 Stage 1 캐시값, 키워드 전용 후보만 재계산
            COALESCE(vc.vec_score,
                     1 - (m.embedding <=> p_query_embedding)) AS relevance,
            -- Keyword: 키워드 후보는 정규화, 벡터 전용 후보는 0점
            COALESCE(kc.kw_raw_score / km.val, 0) AS keyword
        FROM all_candidate_ids ac
        JOIN user_memories m ON m.id = ac.id
        LEFT JOIN vector_candidates vc ON vc.id = ac.id
        LEFT JOIN keyword_candidates kc ON kc.id = ac.id
        CROSS JOIN kw_max km
    )

    -- 최종 가중합 (기존과 동일한 공식)
    SELECT
        s.id, s.player_id, s.heroine_id, s.speaker, s.subject,
        s.content, s.content_type, s.importance, s.created_at,
        s.recency AS recency_score,
        s.importance_norm AS importance_score,
        s.relevance AS relevance_score,
        s.keyword AS keyword_score,
        (p_w_recency * s.recency +
         p_w_importance * s.importance_norm +
         p_w_relevance * s.relevance +
         p_w_keyword * s.keyword) AS final_score
    FROM scored s
    ORDER BY final_score DESC
    LIMIT p_top_k;
END;
$$;

-- ============================================
-- 중복 검사 함수 (유사도 기반)
-- ============================================
CREATE OR REPLACE FUNCTION find_similar_memory(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_embedding vector(1536),
    p_threshold FLOAT DEFAULT 0.9          -- 90% 이상이면 중복
) RETURNS TABLE (
    id UUID,
    content TEXT,
    similarity FLOAT
)
LANGUAGE SQL AS $$
    SELECT 
        m.id,
        m.content,
        1 - (m.embedding <=> p_embedding) AS similarity
        -- p_embedding 파라미터가 새로 저장하려는 데이터의 임베딩
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.invalid_at IS NULL
      AND 1 - (m.embedding <=> p_embedding) >= p_threshold
      -- 유사도가 임계값(기본 0.9) 이상인 것만 필터링
    ORDER BY similarity DESC
    LIMIT 1;
$$;

-- ============================================
-- 기억 무효화 함수 (충돌 처리용)
-- ============================================
CREATE OR REPLACE FUNCTION invalidate_memory(p_memory_id UUID)
RETURNS VOID
LANGUAGE SQL AS $$
    UPDATE user_memories
    SET invalid_at = NOW(),
        updated_at = NOW()
    WHERE id = p_memory_id;
$$;

-- ============================================
-- updated_at 자동 갱신 트리거
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    -- NEW.updated_at = NOW(): 수정되는 행(NEW)의 updated_at 컬럼을 현재 시간으로 설정
    RETURN NEW;
    -- RETURN NEW: 수정된 행을 반환 (이 값이 실제로 DB에 저장됨)
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_memories_updated_at
    BEFORE UPDATE ON user_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- 시간 기반 기억 조회 함수들
-- ============================================

-- 1. 현재 유효한 사실만 조회
CREATE OR REPLACE FUNCTION get_valid_memories(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE (
    id UUID,
    player_id TEXT,
    heroine_id TEXT,
    speaker TEXT,
    subject TEXT,
    content TEXT,
    content_type TEXT,
    importance INT,
    valid_at TIMESTAMPTZ,
    invalid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE SQL AS $$
    SELECT 
        m.id,
        m.player_id,
        m.heroine_id,
        m.speaker,
        m.subject,
        m.content,
        m.content_type,
        m.importance,
        m.valid_at,
        m.invalid_at,
        m.created_at
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.invalid_at IS NULL
    ORDER BY m.created_at DESC
    LIMIT p_limit;
$$;

-- 2. 특정 시점에 유효했던 사실 조회 (Bi-temporal)
CREATE OR REPLACE FUNCTION get_memories_at_point(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_point_in_time TIMESTAMPTZ,
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE (
    id UUID,
    player_id TEXT,
    heroine_id TEXT,
    speaker TEXT,
    subject TEXT,
    content TEXT,
    content_type TEXT,
    importance INT,
    valid_at TIMESTAMPTZ,
    invalid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE SQL AS $$
    SELECT 
        m.id,
        m.player_id,
        m.heroine_id,
        m.speaker,
        m.subject,
        m.content,
        m.content_type,
        m.importance,
        m.valid_at,
        m.invalid_at,
        m.created_at
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.valid_at <= p_point_in_time
      AND (m.invalid_at IS NULL OR m.invalid_at > p_point_in_time)
    ORDER BY m.created_at DESC
    LIMIT p_limit;
$$;

-- 3. 최근 N일 동안 생성된 기억
CREATE OR REPLACE FUNCTION get_recent_memories(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_days INTEGER,
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE (
    id UUID,
    player_id TEXT,
    heroine_id TEXT,
    speaker TEXT,
    subject TEXT,
    content TEXT,
    content_type TEXT,
    importance INT,
    valid_at TIMESTAMPTZ,
    invalid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE SQL AS $$
    SELECT 
        m.id,
        m.player_id,
        m.heroine_id,
        m.speaker,
        m.subject,
        m.content,
        m.content_type,
        m.importance,
        m.valid_at,
        m.invalid_at,
        m.created_at
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.created_at >= NOW() - (p_days || ' days')::INTERVAL
      AND m.invalid_at IS NULL
    ORDER BY m.created_at DESC
    LIMIT p_limit;
$$;

-- 5. N일 전에 했던 이야기 조회
CREATE OR REPLACE FUNCTION get_memories_days_ago(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_days_ago INTEGER,
    p_limit INTEGER DEFAULT 50
) RETURNS TABLE (
    id UUID,
    player_id TEXT,
    heroine_id TEXT,
    speaker TEXT,
    subject TEXT,
    content TEXT,
    content_type TEXT,
    importance INT,
    valid_at TIMESTAMPTZ,
    invalid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)
LANGUAGE SQL AS $$
    SELECT 
        m.id,
        m.player_id,
        m.heroine_id,
        m.speaker,
        m.subject,
        m.content,
        m.content_type,
        m.importance,
        m.valid_at,
        m.invalid_at,
        m.created_at
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.created_at >= NOW() - (p_days_ago || ' days')::INTERVAL
      AND m.created_at < NOW() - ((p_days_ago - 1) || ' days')::INTERVAL
      AND m.invalid_at IS NULL
    ORDER BY m.created_at DESC
    LIMIT p_limit;
$$;

-- ============================================
-- 6. 충돌 후보 검색 (하이브리드 취향 변경 감지용)
-- 임베딩 유사도 0.65 이상 + 같은 content_type + 현재 유효한 기억
-- ============================================
CREATE OR REPLACE FUNCTION find_conflict_candidates(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_embedding vector(1536),
    p_content_type TEXT,
    p_threshold FLOAT DEFAULT 0.55
) RETURNS TABLE (
    id UUID,
    content TEXT,
    content_type TEXT,
    similarity FLOAT
)
LANGUAGE SQL AS $$
    SELECT 
        m.id,
        m.content,
        m.content_type,
        1 - (m.embedding <=> p_embedding) AS similarity
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.content_type = p_content_type
      AND m.invalid_at IS NULL
      AND 1 - (m.embedding <=> p_embedding) >= p_threshold
    ORDER BY similarity DESC;
$$;

