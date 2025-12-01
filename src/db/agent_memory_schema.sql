-- ============================================
-- Generative Agents Memory System (NPC간 기억 전용)
-- PostgreSQL + pgvector 기반
-- 
-- NPC간 기억만 관리 (User-NPC는 Mem0 사용):
-- - NPC간 개별 기억 (npc_memory)
-- - NPC간 대화 (npc_conversation)
-- 
-- ※ User-NPC 대화는 Mem0에서 관리
-- ============================================

-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 기존 테이블 삭제 (개발용)
DROP TABLE IF EXISTS agent_memories CASCADE;
DROP TABLE IF EXISTS heroine_heroine_conversations CASCADE;

-- 통합 메모리 테이블 생성
CREATE TABLE agent_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,           -- 기억 주체 (npc_1_about_2, player_10001_npc_1, conv_1_2 등)
    memory_type VARCHAR(50) NOT NULL,         -- npc_memory, npc_conversation, user_npc
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    importance_score INTEGER NOT NULL DEFAULT 5 CHECK (importance_score BETWEEN 1 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb        -- 추가 정보 (speakers, situation, emotions 등)
);

-- 인덱스 생성

-- 1. HNSW 인덱스 (코사인 거리 기반 벡터 검색)
CREATE INDEX idx_memories_embedding_hnsw ON agent_memories 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 2. agent_id + created_at 복합 인덱스 (특정 에이전트의 최신 기억 조회용)
CREATE INDEX idx_memories_agent_created ON agent_memories (agent_id, created_at DESC);

-- 3. agent_id 단일 인덱스 (에이전트별 필터링용)
CREATE INDEX idx_memories_agent_id ON agent_memories (agent_id);

-- 4. memory_type 인덱스 (타입별 필터링용)
CREATE INDEX idx_memories_type ON agent_memories (memory_type);

-- 5. importance_score 인덱스 (중요도 기반 필터링용)
CREATE INDEX idx_memories_importance ON agent_memories (importance_score DESC);

-- 6. memory_type + agent_id 복합 인덱스
CREATE INDEX idx_memories_type_agent ON agent_memories (memory_type, agent_id);

-- ============================================
-- 하이브리드 스코어링 검색 함수
-- ============================================
-- Score = (w_recency * Recency) + (w_importance * Importance) + (w_relevance * Relevance)
-- 
-- Recency: 지수 감쇠 함수 exp(-decay_rate * hours_since_creation)
-- Importance: importance_score / 10 (0~1 정규화)
-- Relevance: 1 - cosine_distance (코사인 유사도)

CREATE OR REPLACE FUNCTION search_memories_hybrid(
    p_agent_id VARCHAR(100),
    p_query_embedding VECTOR(1536),
    p_top_k INTEGER DEFAULT 5,
    p_w_recency FLOAT DEFAULT 1.0,
    p_w_importance FLOAT DEFAULT 1.0,
    p_w_relevance FLOAT DEFAULT 1.0,
    p_decay_rate FLOAT DEFAULT 0.01,
    p_memory_type VARCHAR(50) DEFAULT NULL  -- NULL이면 모든 타입 검색
) RETURNS TABLE (
    id UUID,
    agent_id VARCHAR(100),
    memory_type VARCHAR(50),
    content TEXT,
    importance_score INTEGER,
    created_at TIMESTAMPTZ,
    last_accessed_at TIMESTAMPTZ,
    metadata JSONB,
    recency_score FLOAT,
    importance_normalized FLOAT,
    relevance_score FLOAT,
    total_score FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH scored AS (
        SELECT 
            m.id,
            m.agent_id,
            m.memory_type,
            m.content,
            m.importance_score,
            m.created_at,
            m.last_accessed_at,
            m.metadata,
            EXP(-p_decay_rate * EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 3600) AS recency,
            m.importance_score::FLOAT / 10.0 AS importance,
            1 - (m.embedding <=> p_query_embedding) AS relevance
        FROM agent_memories m
        WHERE m.agent_id = p_agent_id
          AND (p_memory_type IS NULL OR m.memory_type = p_memory_type)
    )
    SELECT 
        s.id,
        s.agent_id,
        s.memory_type,
        s.content,
        s.importance_score,
        s.created_at,
        s.last_accessed_at,
        s.metadata,
        s.recency AS recency_score,
        s.importance AS importance_normalized,
        s.relevance AS relevance_score,
        (p_w_recency * s.recency + p_w_importance * s.importance + p_w_relevance * s.relevance) AS total_score
    FROM scored s
    ORDER BY total_score DESC
    LIMIT p_top_k;
END;
$$;

-- ============================================
-- NPC 관련 기억 통합 검색 함수
-- ============================================
-- 특정 NPC와 관련된 모든 기억을 검색 (대화 + 개별 기억)

CREATE OR REPLACE FUNCTION search_npc_memories(
    p_npc_id INTEGER,
    p_query_embedding VECTOR(1536),
    p_top_k INTEGER DEFAULT 5,
    p_w_recency FLOAT DEFAULT 1.0,
    p_w_importance FLOAT DEFAULT 1.0,
    p_w_relevance FLOAT DEFAULT 1.0,
    p_decay_rate FLOAT DEFAULT 0.01
) RETURNS TABLE (
    id UUID,
    agent_id VARCHAR(100),
    memory_type VARCHAR(50),
    content TEXT,
    importance_score INTEGER,
    created_at TIMESTAMPTZ,
    metadata JSONB,
    total_score FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH scored AS (
        SELECT 
            m.id,
            m.agent_id,
            m.memory_type,
            m.content,
            m.importance_score,
            m.created_at,
            m.metadata,
            EXP(-p_decay_rate * EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 3600) AS recency,
            m.importance_score::FLOAT / 10.0 AS importance,
            1 - (m.embedding <=> p_query_embedding) AS relevance
        FROM agent_memories m
        WHERE (
            -- NPC간 대화 (conv_X_Y 형식)
            (m.memory_type = 'npc_conversation' AND m.agent_id LIKE '%_' || p_npc_id || '_%')
            OR (m.memory_type = 'npc_conversation' AND m.agent_id LIKE '%_' || p_npc_id)
            -- NPC가 다른 NPC에 대해 기억 (npc_X_about_Y)
            OR (m.memory_type = 'npc_memory' AND m.agent_id LIKE 'npc_' || p_npc_id || '_about_%')
            -- 다른 NPC가 이 NPC에 대해 기억
            OR (m.memory_type = 'npc_memory' AND m.agent_id LIKE '%_about_' || p_npc_id)
        )
    )
    SELECT 
        s.id,
        s.agent_id,
        s.memory_type,
        s.content,
        s.importance_score,
        s.created_at,
        s.metadata,
        (p_w_recency * s.recency + p_w_importance * s.importance + p_w_relevance * s.relevance) AS total_score
    FROM scored s
    ORDER BY total_score DESC
    LIMIT p_top_k;
END;
$$;

-- ============================================
-- last_accessed_at 자동 업데이트 함수
-- ============================================
CREATE OR REPLACE FUNCTION update_memory_access_time(p_memory_ids UUID[])
RETURNS VOID
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE agent_memories
    SET last_accessed_at = NOW()
    WHERE id = ANY(p_memory_ids);
END;
$$;

-- ============================================
-- 통계 및 유틸리티 함수
-- ============================================

-- 에이전트별 메모리 통계
CREATE OR REPLACE FUNCTION get_memory_stats(p_agent_id VARCHAR(100))
RETURNS TABLE (
    total_memories BIGINT,
    avg_importance FLOAT,
    oldest_memory TIMESTAMPTZ,
    newest_memory TIMESTAMPTZ
)
LANGUAGE SQL AS $$
    SELECT 
        COUNT(*) AS total_memories,
        AVG(importance_score)::FLOAT AS avg_importance,
        MIN(created_at) AS oldest_memory,
        MAX(created_at) AS newest_memory
    FROM agent_memories
    WHERE agent_id = p_agent_id;
$$;

