from core.common import get_src_path
from enum import Enum

BASE = get_src_path() / "prompts" / "prompt_type"

class FairyPromptType(Enum):
    FAIRY_SYSTEM = str(BASE / "fairy" / "fairy_system.yaml")