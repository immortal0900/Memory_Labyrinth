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
    user_id BIGINT NOT NULL,

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
CREATE INDEX idx_npc_npc_checkpoints_pair ON npc_npc_checkpoints (user_id, heroine_id_1, heroine_id_2, created_at DESC);
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
    user_id BIGINT NOT NULL,

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
CREATE INDEX idx_npc_npc_memories_pair ON npc_npc_memories (user_id, heroine_id_1, heroine_id_2, invalid_at);

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
CREATE OR REPLACE FUNCTION search_npc_npc_memories_hybrid(
    p_user_id BIGINT,
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
    user_id BIGINT,
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
    max_keyword_score FLOAT;
BEGIN
    SELECT MAX(pgroonga_score(tableoid, ctid))
    INTO max_keyword_score
    FROM npc_npc_memories m
    WHERE m.user_id = p_user_id
      AND m.heroine_id_1 = p_heroine_id_1
      AND m.heroine_id_2 = p_heroine_id_2
      AND m.invalid_at IS NULL
      AND m.content &@~ p_query_text;

    IF max_keyword_score IS NULL OR max_keyword_score = 0 THEN
        max_keyword_score := 1.0;
    END IF;

    RETURN QUERY
    WITH combined AS (
        SELECT
            m.id,
            m.conversation_id,
            m.turn_index,
            m.user_id,
            m.heroine_id_1,
            m.heroine_id_2,
            m.speaker_id,
            m.subject_id,
            m.content,
            m.content_type,
            m.importance,
            m.created_at,
            EXP(-EXTRACT(EPOCH FROM (NOW() - m.created_at)) / (p_decay_days * 86400)) AS recency,
            m.importance::FLOAT / 10.0 AS importance_norm,
            1 - (m.embedding <=> p_query_embedding) AS relevance,
            COALESCE(pgroonga_score(m.tableoid, m.ctid) / max_keyword_score, 0) AS keyword
        FROM npc_npc_memories m
        WHERE m.user_id = p_user_id
          AND m.heroine_id_1 = p_heroine_id_1
          AND m.heroine_id_2 = p_heroine_id_2
          AND m.invalid_at IS NULL
    )
    SELECT
        c.id,
        c.conversation_id,
        c.turn_index,
        c.user_id,
        c.heroine_id_1,
        c.heroine_id_2,
        c.speaker_id,
        c.subject_id,
        c.content,
        c.content_type,
        c.importance,
        c.created_at,
        c.recency AS recency_score,
        c.importance_norm AS importance_score,
        c.relevance AS relevance_score,
        c.keyword AS keyword_score,
        (p_w_recency * c.recency +
         p_w_importance * c.importance_norm +
         p_w_relevance * c.relevance +
         p_w_keyword * c.keyword) AS final_score
    FROM combined c
    ORDER BY final_score DESC
    LIMIT p_top_k;
END;
$$;
