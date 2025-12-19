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
    max_keyword_score FLOAT;
BEGIN
    -- 키워드 검색 최대 점수 계산 (정규화용)
    SELECT MAX(pgroonga_score(tableoid, ctid))
    INTO max_keyword_score
    FROM user_memories m
    WHERE m.player_id = p_player_id
      AND m.heroine_id = p_heroine_id
      AND m.invalid_at IS NULL
      AND m.content &@~ p_query_text;
    
    -- 최대값이 없으면 1로 설정 (0 나누기 방지)
    IF max_keyword_score IS NULL OR max_keyword_score = 0 THEN
        max_keyword_score := 1.0;
    END IF;

    RETURN QUERY
    WITH combined AS (
        SELECT 
            m.id,
            m.player_id,
            m.heroine_id,
            m.speaker,
            m.subject,
            m.content,
            m.content_type,
            m.importance,
            m.created_at,
            -- Recency: 지수 감쇠 (30일 기준)
            EXP(-EXTRACT(EPOCH FROM (NOW() - m.created_at)) / (p_decay_days * 86400)) AS recency,
            -- Importance: 1~10 -> 0~1 정규화
            m.importance::FLOAT / 10.0 AS importance_norm,
            -- Relevance: 코사인 유사도 (1 - 거리)
            -- importance_norm = "normalized importance"의 약자로, 정규화된 중요도를 의미
            1 - (m.embedding <=> p_query_embedding) AS relevance,
            -- Keyword: PGroonga BM25 정규화
            COALESCE(pgroonga_score(m.tableoid, m.ctid) / max_keyword_score, 0) AS keyword
            -- tableoid: 해당 행이 속한 테이블의 OID (Object Identifier)상속 테이블 구조에서 어느 테이블에서 왔는지 식별할 때 사용
            -- ctid: 행의 물리적 위치를 나타내는 tuple identifier (페이지 번호, 페이지 내 오프셋). 각 행의 고유한 물리적 주소
        FROM user_memories m
        WHERE m.player_id = p_player_id
          AND m.heroine_id = p_heroine_id
          AND m.invalid_at IS NULL
    )
    SELECT 
        c.id,
        c.player_id,
        c.heroine_id,
        c.speaker,
        c.subject,
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

-- 3. 취향 변화 이력 조회 (content 패턴 기반)
CREATE OR REPLACE FUNCTION get_preference_history(
    p_player_id TEXT,
    p_heroine_id TEXT,
    p_keyword TEXT
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
      AND m.content &@~ p_keyword
    ORDER BY m.valid_at ASC;
$$;

-- 4. 최근 N일 동안 생성된 기억
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

