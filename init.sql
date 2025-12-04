-- pgvector 확장 기능 활성화 (벡터 기능을 사용하기 위해 필수)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 몬스터 정보 테이블
CREATE TABLE IF NOT EXISTS monsters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    data JSONB -- 스테이터스, 패턴, 공략 등 모든 정보를 담는 JSON
);

-- 2. 아이템 정보 테이블
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    data JSONB -- 스탯, 스킬, 등급별 범위 등
);

-- 3. 이벤트 템플릿 테이블
CREATE TABLE IF NOT EXISTS event_templates (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100),
    data JSONB -- 기본상황, 선택지, 결과범위 등
);

-- 4. 유저 행동 매핑 테이블
CREATE TABLE IF NOT EXISTS user_action_mappings (
    id SERIAL PRIMARY KEY,
    user_action TEXT,
    mapped_choice TEXT,
    similarity FLOAT
);

-- 5. 유저 플레이 성향 테이블
CREATE TABLE IF NOT EXISTS user_play_styles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    style VARCHAR(50),
    data JSONB
);

-- 6. 보스방 입장 로그 테이블
CREATE TABLE IF NOT EXISTS boss_room_entry_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSONB -- 스탯, 장비 목록 등
);

-- 7. 히로인 대화 내역
CREATE TABLE IF NOT EXISTS heroine_conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    heroine_id VARCHAR(100),
    input_text TEXT,
    output_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 대현자 대화 내역
CREATE TABLE IF NOT EXISTS sage_conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    input_text TEXT,
    output_text TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. 히로인끼리의 대화 내역 
-- 통합 메모리 테이블(agent_memories)로 이전됨
-- 스키마: src/db/agent_memory_schema.sql 참조

-- 10. 던전 생성 입력 데이터
CREATE TABLE IF NOT EXISTS dungeon_generation_input (
    id SERIAL PRIMARY KEY,
    floor INT,
    room_type VARCHAR(50),
    data JSONB
);

-- 11. 세계관 시나리오
CREATE TABLE IF NOT EXISTS world_scenarios (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200),
    content TEXT
);

-- 12. 히로인별 시나리오
CREATE TABLE IF NOT EXISTS heroine_scenarios (
    id SERIAL PRIMARY KEY,
    heroine_id VARCHAR(100),
    title VARCHAR(200),
    content TEXT
);

-- 13. 세계관 해금 단계
CREATE TABLE IF NOT EXISTS world_scenario_unlock_stages (
    id SERIAL PRIMARY KEY,
    stage INT,
    content TEXT
);

-- 14. 히로인 기억 해금 단계
CREATE TABLE IF NOT EXISTS heroine_memory_unlock_stages (
    id SERIAL PRIMARY KEY,
    heroine_id VARCHAR(100),
    stage INT,
    content TEXT
);

-- 15. 연애 관련 문서
CREATE TABLE IF NOT EXISTS romance_docs (
    id SERIAL PRIMARY KEY,
    heroine_id VARCHAR(100),
    data JSONB -- 좋아하는 키워드 등
);

-- ============================================
-- NPC Agent System 테이블
-- ============================================

-- 16. 세션 체크포인트 (Redis 백업용)
-- 매 대화마다 conversation 저장, 20턴/1시간마다 summary_list 업데이트
DROP TABLE IF EXISTS session_checkpoints CASCADE;
CREATE TABLE session_checkpoints (
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

-- 17. 히로인 시나리오 (벡터 검색용) 

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

-- 18. 대현자 시나리오
CREATE TABLE IF NOT EXISTS sage_scenarios (
    id SERIAL PRIMARY KEY,
    scenario_level INT NOT NULL,
    title VARCHAR(200),
    content TEXT NOT NULL,
    content_embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sage_level ON sage_scenarios(scenario_level);

-- 19. 히로인 시나리오 검색 함수
-- hs -> heroine_scenarios
-- p_match_count -> 반환할 최대 결과 개수수
-- p_ -> 파라미터의 약자
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

-- 20. 대현플레이어 진행도 → Redis 세션에 저장
-- 대현자 대화 시 → 세션에서 레벨 조회자 시나리오 검색 함수
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

