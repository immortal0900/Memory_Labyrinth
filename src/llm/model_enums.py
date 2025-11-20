from enum import Enum

class LLM(Enum):
    GPT4_1 = "gpt-4.1-2025-04-14"
    GPT4_1_MINI = "gpt-4.1-mini-2025-04-14"
    GPT4_1_NANO = "gpt-4.1-nano-2025-04-14"
    GPT4O = "gpt-4o-2024-08-06"
    GPT5_1 = "gpt-5.1-2025-11-13"
    GPT5_MINI = "gpt-5-mini-2025-08-07"
    GPT5_NANO = "gpt-5-nano-2025-08-07"
    
    # Claude (Anthropic)
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    
    # Gemini (Google)
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_PRO = "gemini-pro"
    GEMINI_ULTRA = "gemini-ultra"
    
    # Grok (xAI)
    GROK_2 = "grok-2"
    GROK_BETA = "grok-beta"
    GROK_VISION_BETA = "grok-vision-beta"
    