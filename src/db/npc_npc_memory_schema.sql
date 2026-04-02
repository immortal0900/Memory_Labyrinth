-- ============================================
-- NPC-NPC 장기기억 + 대화 체크포인트 (Supabase)
-- PostgreSQL + pgvector + PGroonga 기반
--
-- 목표:
-- 1) NPC-NPC 대화 전체 기록은 npc_npc_checkpoints
-- 2) NPC-NPC 장기기억(핵심)은 npc_npc_memories
-- 3) 인터럽트(interrupted_turn) 이후 기억은 invalid_at으로 무효화
-- 4) 4요소 하이브리드 검색 지원
-- ============================================

-- 확장
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgroonga;

-- 기존 테이블 삭제 (개발용)
-- DROP TABLE IF EXISTS npc_npc_memories CASCADE;
-- DROP TABLE IF EXISTS npc_npc_checkpoints CASCADE;

-- ============================================
-- 1) NPC-NPC 대화 체크포인트 (대화 전체)
-- ============================================
CREATE TABLE npc_npc_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 플레이어별 분리 저장
    player_id TEXT NOT NULL,

    -- (A,B) 쌍은 항상 (min,max)로 저장
    heroine_id_1 INT NOT NULL,
    heroine_id_2 INT NOT NULL,

    situation TEXT,

    -- 턴 배열(JSON)
    conversation JSONB NOT NULL DEFAULT '[]'::jsonb,
    turn_count INT NOT NULL DEFAULT 0,
    interrupted_turn INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_turn_at TIMESTAMPTZ
);

-- 조회/세션 분리용
CREATE INDEX idx_npc_npc_checkpoints_pair ON npc_npc_checkpoints (player_id, heroine_id_1, heroine_id_2, created_at DESC);
CREATE INDEX idx_npc_npc_checkpoints_created ON npc_npc_checkpoints (created_at DESC);

-- ============================================
-- 2) NPC-NPC 장기기억 (핵심)
-- ============================================
CREATE TABLE npc_npc_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 어떤 대화에서 나온 기억인지
    conversation_id UUID NOT NULL REFERENCES npc_npc_checkpoints(id) ON DELETE CASCADE,
    turn_index INT NOT NULL,

    -- 플레이어별 분리 저장
    player_id TEXT NOT NULL,

    -- (A,B) 쌍은 항상 (min,max)로 저장
    heroine_id_1 INT NOT NULL,
    heroine_id_2 INT NOT NULL,

    speaker_id INT NOT NULL,
    subject_id INT NOT NULL,

    content TEXT NOT NULL,
    content_type TEXT DEFAULT 'fact',

    embedding VECTOR(1536),
    importance INT DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),

    valid_at TIMESTAMPTZ DEFAULT NOW(),
    invalid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    metadata JSONB DEFAULT '{}'::jsonb
);

-- 인터럽트 무효화 / 조회용
CREATE INDEX idx_npc_npc_memories_conv_turn ON npc_npc_memories (conversation_id, turn_index);

-- 세션 분리용
CREATE INDEX idx_npc_npc_memories_pair ON npc_npc_memories (player_id, heroine_id_1, heroine_id_2, invalid_at);

-- 벡터 검색
CREATE INDEX idx_npc_npc_memories_vector ON npc_npc_memories
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 키워드 검색 (한국어)
CREATE INDEX idx_npc_npc_memories_pgroonga ON npc_npc_memories USING pgroonga (content);

-- 필터
CREATE INDEX idx_npc_npc_memories_speaker ON npc_npc_memories (speaker_id);
CREATE INDEX idx_npc_npc_memories_subject ON npc_npc_memories (subject_id);
CREATE INDEX idx_npc_npc_memories_created ON npc_npc_memories (created_at DESC);

-- ============================================
-- updated_at 자동 갱신 트리거
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_npc_npc_checkpoints_updated_at
    BEFORE UPDATE ON npc_npc_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trigger_npc_npc_memories_updated_at
    BEFORE UPDATE ON npc_npc_memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- 4요소 하이브리드 검색 함수
-- Score = (w_recency * Recency) + (w_importance * Importance)
--       + (w_relevance * Relevance) + (w_keyword * Keyword)
-- ============================================
-- 2-Stage Retrieve-then-Rerank 하이브리드 검색
-- Stage 1: HNSW 벡터 인덱스 + PGroonga 키워드 인덱스로 후보 추출
-- Stage 2: 후보에 대해서만 4요소 가중합 (recency, importance, relevance, keyword)
CREATE OR REPLACE FUNCTION search_npc_npc_memories_hybrid(
    p_player_id TEXT,
    p_heroine_id_1 INT,
    p_heroine_id_2 INT,
    p_query_text TEXT,
    p_query_embedding VECTOR(1536),
    p_top_k INTEGER DEFAULT 10,
    p_w_recency FLOAT DEFAULT 0.15,
    p_w_importance FLOAT DEFAULT 0.15,
    p_w_relevance FLOAT DEFAULT 0.50,
    p_w_keyword FLOAT DEFAULT 0.20,
    p_decay_days FLOAT DEFAULT 30.0
) RETURNS TABLE (
    id UUID,
    conversation_id UUID,
    turn_index INT,
    player_id TEXT,
    heroine_id_1 INT,
    heroine_id_2 INT,
    speaker_id INT,
    subject_id INT,
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
    v_candidate_limit := GREATEST(p_top_k * 3, 20);

    -- HNSW 인덱스 탐색 범위 확대 (post-filter 후 충분한 후보 보장)
    PERFORM set_config('hnsw.ef_search', '100', true);

    RETURN QUERY

    -- =============================================
    -- Stage 1: 후보 추출 (인덱스 활용)
    -- =============================================
    WITH

    -- 1a. 벡터 검색 후보 (HNSW 인덱스 활용)
    vector_candidates AS (
        SELECT m.id,
               1 - (m.embedding <=> p_query_embedding) AS vec_score
        FROM npc_npc_memories m
        WHERE m.player_id = p_player_id
          AND m.heroine_id_1 = p_heroine_id_1
          AND m.heroine_id_2 = p_heroine_id_2
          AND m.invalid_at IS NULL
        ORDER BY m.embedding <=> p_query_embedding
        LIMIT v_candidate_limit
    ),

    -- 1b. 키워드 검색 후보 (PGroonga BM25 인덱스 활용)
    keyword_candidates AS (
        SELECT m.id,
               pgroonga_score(m.tableoid, m.ctid) AS kw_raw_score
        FROM npc_npc_memories m
        WHERE m.player_id = p_player_id
          AND m.heroine_id_1 = p_heroine_id_1
          AND m.heroine_id_2 = p_heroine_id_2
          AND m.invalid_at IS NULL
          AND m.content &@~ p_query_text
        ORDER BY pgroonga_score(m.tableoid, m.ctid) DESC
        LIMIT v_candidate_limit
    ),

    -- 1c. 두 결과 합치기 (중복 자동 제거)
    all_candidate_ids AS (
        SELECT vc.id FROM vector_candidates vc
        UNION
        SELECT kc.id FROM keyword_candidates kc
    ),

    -- 키워드 점수 정규화 기준값
    kw_max AS (
        SELECT COALESCE(MAX(kc.kw_raw_score), 1.0) AS val
        FROM keyword_candidates kc
    ),

    -- =============================================
    -- Stage 2: 후보만 대상으로 점수 매기기 (Rerank)
    -- =============================================
    scored AS (
        SELECT
            m.id, m.conversation_id, m.turn_index,
            m.player_id, m.heroine_id_1, m.heroine_id_2,
            m.speaker_id, m.subject_id,
            m.content, m.content_type, m.importance, m.created_at,
            -- Recency: 지수 감쇠
            EXP(-EXTRACT(EPOCH FROM (NOW() - m.created_at))
                / (p_decay_days * 86400)) AS recency,
            -- Importance: 1~10 -> 0~1 정규화
            m.importance::FLOAT / 10.0 AS importance_norm,
            -- Relevance: 벡터 후보는 캐시값, 키워드 전용 후보만 재계산
            COALESCE(vc.vec_score,
                     1 - (m.embedding <=> p_query_embedding)) AS relevance,
            -- Keyword: 키워드 후보는 정규화, 벡터 전용 후보는 0점
            COALESCE(kc.kw_raw_score / km.val, 0) AS keyword
        FROM all_candidate_ids ac
        JOIN npc_npc_memories m ON m.id = ac.id
        LEFT JOIN vector_candidates vc ON vc.id = ac.id
        LEFT JOIN keyword_candidates kc ON kc.id = ac.id
        CROSS JOIN kw_max km
    )

    -- 최종 가중합 (기존과 동일한 공식)
    SELECT
        s.id, s.conversation_id, s.turn_index,
        s.player_id, s.heroine_id_1, s.heroine_id_2,
        s.speaker_id, s.subject_id,
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
