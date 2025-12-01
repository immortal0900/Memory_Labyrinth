from enum import Enum
from pathlib import Path


class HeroinePromptType(Enum):
    """히로인 NPC 프롬프트 타입"""
    HEROINE_SYSTEM = str(Path(__file__).parent / "heroine_system.yaml")
    HEROINE_INTENT = str(Path(__file__).parent / "heroine_system.yaml")


class SagePromptType(Enum):
    """대현자 NPC 프롬프트 타입"""
    SAGE_SYSTEM = str(Path(__file__).parent / "sage_system.yaml")
    SAGE_INTENT = str(Path(__file__).parent / "sage_system.yaml")

