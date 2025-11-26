from core.common import get_src_path
from enum import Enum

BASE = get_src_path() / "prompts" / "prompt_type"

class FairyPromptType(Enum):    
    FAIRY_DUNGEON_SYSTEM = str(BASE / "fairy" / "fairy_dungeon_system.yaml")
    FAIRY_GUILD_SYSTEM = str(BASE / "fairy" / "fairy_guild_system.yaml")
    FAIRY_ROUTER = str(BASE / "fairy" / "fairy_router.yaml")
    QUESTION_HISTORY_CHECK = str(BASE / "fairy" / "question_history_check.yaml")