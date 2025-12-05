-- pgvector 확장 기능 활성화 (벡터 기능을 사용하기 위해 필수)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 몬스터 정보 테이블
CREATE TABLE IF NOT EXISTS monsters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    data JSONB
);

-- 2. 히로인 기억 해금 단계
CREATE TABLE IF NOT EXISTS heroine_memory_unlock_stages (
    id SERIAL PRIMARY KEY,
    heroine_id VARCHAR(100),
    stage INT,
    content TEXT
);

-- 3. 연애 관련 문서
CREATE TABLE IF NOT EXISTS romance_docs (
    id SERIAL PRIMARY KEY,
    heroine_id VARCHAR(100),
    data JSONB
);

-- ============================================
-- NPC Agent System 테이블
-- ============================================

-- 4. 세션 체크포인트 (Redis 백업용)
CREATE TABLE IF NOT EXISTS session_checkpoints (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    npc_id INT NOT NULL,
    conversation JSONB,
    summary_list JSONB DEFAULT '[]'::jsonb,
    state JSONB,
    last_chat_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkpoint_user_npc ON session_checkpoints(user_id, npc_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_last_chat ON session_checkpoints(last_chat_at DESC);

-- 5. 히로인 시나리오 (벡터 검색용)
CREATE TABLE IF NOT EXISTS heroine_scenarios (
    id SERIAL PRIMARY KEY,
    heroine_id INT NOT NULL,
    memory_progress INT NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_heroine_scenarios_filter ON heroine_scenarios(heroine_id, memory_progress);

-- 6. 대현자 시나리오
CREATE TABLE IF NOT EXISTS sage_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_level INT NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sage_level ON sage_scenarios(scenario_level);

-- 7. 히로인 시나리오 검색 함수
CREATE OR REPLACE FUNCTION match_heroine_scenarios(
    query_embedding VECTOR(1536),
    p_heroine_id INT,
    p_max_progress INT,
    p_match_count INT
) RETURNS TABLE (id INT, content TEXT, memory_progress INT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        hs.id,
        hs.content,
        hs.memory_progress,
        1 - (hs.content_embedding <=> query_embedding) AS similarity
    FROM heroine_scenarios hs
    WHERE hs.heroine_id = p_heroine_id
      AND hs.memory_progress <= p_max_progress
    ORDER BY hs.content_embedding <=> query_embedding
    LIMIT p_match_count;
END;
$$;

-- 8. 대현자 시나리오 검색 함수
CREATE OR REPLACE FUNCTION match_sage_scenarios(
    query_embedding VECTOR(1536),
    p_max_level INT,
    p_match_count INT
) RETURNS TABLE (id INT, content TEXT, scenario_level INT, similarity FLOAT)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ss.id,
        ss.content,
        ss.scenario_level,
        1 - (ss.content_embedding <=> query_embedding) AS similarity
    FROM sage_scenarios ss
    WHERE ss.scenario_level <= p_max_level
    ORDER BY ss.content_embedding <=> query_embedding
    LIMIT p_match_count;
END;
$$;
