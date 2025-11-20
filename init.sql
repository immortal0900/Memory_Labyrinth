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
CREATE TABLE IF NOT EXISTS heroine_heroine_conversations (
    id SERIAL PRIMARY KEY,
    heroine1_id VARCHAR(100),
    heroine2_id VARCHAR(100),
    conversation TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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

