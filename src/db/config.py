import os
from enum import StrEnum
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경변수에서 DB 주소 읽기, 없으면 로컬 기본값 사용
# 로컬 Docker 기본값: postgresql+psycopg://postgres:password@localhost:5432/game_db
CONNECTION_URL = os.getenv("DATABASE_URL", "postgresql://postgres.mjyjbkjqvjyneqrgebsy:Wanted11!!@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres")

class DBCollectionName(StrEnum):
    # 몬스터 관련
    MONSTER = "monsters"
    
    # 아이템 관련
    ITEM = "items"
    
    # 이벤트 관련
    EVENT_TEMPLATE = "event_templates"
    
    # 유저 관련
    USER_ACTION_MAPPING = "user_action_mappings"
    USER_PLAY_STYLE = "user_play_styles"
    BOSS_ROOM_ENTRY_LOG = "boss_room_entry_logs"
    
    # 대화 관련
    HEROINE_CONVERSATION = "heroine_conversations"
    SAGE_CONVERSATION = "sage_conversations"
    HEROINE_HEROINE_CONVERSATION = "heroine_heroine_conversations"
    
    # 시나리오/데이터 관련
    DUNGEON_GENERATION_INPUT = "dungeon_generation_input"
    WORLD_SCENARIO = "world_scenarios"
    HEROINE_SCENARIO = "heroine_scenarios"
    WORLD_UNLOCK_STAGE = "world_scenario_unlock_stages"
    HEROINE_MEMORY_UNLOCK_STAGE = "heroine_memory_unlock_stages"
    ROMANCE_DOC = "romance_docs"

    HEROINE_MEMORY = "heroine_memory"

