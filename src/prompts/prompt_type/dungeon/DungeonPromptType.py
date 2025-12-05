from core.common import get_src_path
from enum import Enum

BASE = get_src_path() / "prompts" / "prompt_type" / "dungeon"


class DungeonPromptType(Enum):
    """던전 밸런싱 Agent용 프롬프트 타입"""

    MONSTER_BALANCING = str(BASE / "monster_balancing.yaml")
    MONSTER_STRATEGY = str(BASE / "monster_strategy.yaml")
    DUNGEON_SUB_EVENT = str(BASE / "dungeon_sub_event.yaml")
    DUNGEON_MAIN_EVENT_SELECTION = str(BASE / "dungeon_main_event_selection.yaml")