from core.common import get_src_path
from enum import Enum

BASE = get_src_path() / "prompts" / "prompt_type"

class FairyPromptType(Enum):    
    FAIRY_DUNGEON_SYSTEM = str(BASE / "fairy" / "fairy_dungeon_system.yaml")
    FAIRY_DUNGEON_INTENT = str(BASE / "fairy" / "fairy_dungeon_intent.yaml")
    FAIRY_GUILD_SYSTEM = str(BASE / "fairy" / "fairy_guild_system.yaml")
    FAIRY_GUILD_INTENT = str(BASE / "fairy" / "fairy_guild_intent.yaml")
    FAIRY_REASONING_REQUIRED = str(BASE / "fairy" / "fairy_reasoning_required.yaml")
    FAIRY_MULTI_SMALL_TALK = str(BASE / "fairy" / "fairy_multi_small_talk.yaml")
    QUESTION_HISTORY_CHECK = str(BASE / "fairy" / "question_history_check.yaml")
    FAIRY_INTERACTION_INTENT = str(BASE / "fairy" / "fairy_interaction_intent.yaml")
    FAIRY_ITEM_USE = str(BASE / "fairy" / "fairy_item_use.yaml")
    