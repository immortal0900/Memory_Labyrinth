from core.common import get_src_path
from enum import Enum

BASE = get_src_path() / "prompts" / "prompt_type" / "dungeon"

class DungeonPromptType(Enum):
    """던전 밸런싱 Agent용 프롬프트 타입"""
    MONSTER_BALANCING = str(BASE / "monster_balancing.yaml")
    MONSTER_STRATEGY = str(BASE/ "monster_strategy.yaml")
    # EVENT_SCENARIO_GENERATION = str(BASE / "event_scenario_generation.yaml")
    # EVENT_INTERACTION_GENERATION = str(BASE / "event_interaction_generation.yaml")
    # EVENT_RESULT_GENERATION = str(BASE / "event_result_generation.yaml")
    # EVENT_TEXT_MAPPING = str(BASE / "event_text_mapping.yaml")

