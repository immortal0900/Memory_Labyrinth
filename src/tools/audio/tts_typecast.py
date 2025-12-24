"""
Typecast TTS 서비스

Typecast API를 사용하여 텍스트를 음성으로 변환합니다.
NPC별로 다른 목소리를 사용하고, 감정에 따라 음성 톤을 조절합니다.

SDK 문서: https://github.com/neosapience/typecast-python
"""

import os
import re
from typecast.async_client import AsyncTypecast
from typecast.models import TTSRequest, LanguageCode


def sanitize_text_for_tts(text: str) -> str:
    """TTS용 텍스트 전처리

    Typecast가 처리 못하는 특수문자를 제거합니다.

    Args:
        text: 원본 텍스트

    Returns:
        전처리된 텍스트
    """
    # 제거할 특수문자 패턴
    remove_chars = r"[♡♥★☆◆◇○●□■△▽▲▼※『』「」【】〈〉《》〔〕｛｝（）［］]"
    text = re.sub(remove_chars, "", text)

    # 연속 공백 정리
    text = re.sub(r"\s+", " ", text)

    # 앞뒤 공백 제거
    text = text.strip()

    return text


class TypecastTTSService:
    """Typecast TTS 서비스 클래스

    NPC별 목소리와 감정 매핑을 관리하고,
    텍스트를 음성(wav 바이트)으로 변환합니다.
    """

    def __init__(self):
        """초기화

        환경변수 TYPECAST_API_KEY에서 API 키를 가져옵니다.
        """
        self.api_key = os.getenv("TYPECAST_API_KEY")

        # NPC ID -> Typecast voice_id 매핑
        # voice_id는 find_typecast_voices.py 스크립트로 조회 후 설정
        self.voice_map = {
            1: "tc_676cda78bde49be9d17f38e0",  # 레티아 - 미오
            2: "tc_61659cc118732016a95fe7c6",  # 루파메스 - 소라
            3: "tc_61f084d860b9b6b40388f868",  # 로코 - 새론
            0: "tc_64818789444a9ae3e2e9f89d",  # 사트라(대현자) - 유빈
        }

        # 게임 emotion (정수) -> Typecast emotion_preset 매핑
        # Options: normal, happy, sad, angry, tonemid, toneup
        self.emotion_preset_map = {
            0: "normal",  # neutral - 평온
            1: "happy",  # joy - 기쁨
            2: "happy",  # fun - 재미 (happy로 대체)
            3: "sad",  # sorrow - 슬픔
            4: "angry",  # angry - 분노
            5: "toneup",  # surprise - 놀람 (toneup으로 대체)
            6: "tonemid",  # mysterious - 신비로움 (tonemid로 대체)
        }

    def set_voice_id(self, npc_id: int, voice_id: str):
        """NPC의 voice_id를 설정합니다.

        Args:
            npc_id: NPC ID (0=사트라, 1=레티아, 2=루파메스, 3=로코)
            voice_id: Typecast voice_id (예: "tc_62a8975e695ad26f7fb514d1")
        """
        self.voice_map[npc_id] = voice_id

    async def text_to_speech(
        self,
        text: str,
        npc_id: int,
        emotion: int = 0,
        emotion_intensity: float = 1.0,
    ) -> bytes:
        """텍스트를 음성(wav)으로 변환합니다.

        Args:
            text: 변환할 텍스트
            npc_id: NPC ID (0=사트라, 1=레티아, 2=루파메스, 3=로코)
            emotion: 감정 (0~6)
            emotion_intensity: 감정 강도 (0.0~2.0)

        Returns:
            wav 형식의 오디오 바이트
        """
        if not self.api_key:
            raise ValueError("TYPECAST_API_KEY 환경변수가 설정되지 않았습니다.")

        voice_id = self.voice_map.get(npc_id)
        if not voice_id:
            raise ValueError(f"NPC ID {npc_id}에 해당하는 voice_id가 없습니다.")

        emotion_preset = self.emotion_preset_map.get(emotion, "normal")

        # emotion_intensity 범위 제한 (0.0~2.0)
        emotion_intensity = max(0.0, min(2.0, emotion_intensity))

        # 텍스트 전처리
        text = sanitize_text_for_tts(text)

        # 빈 텍스트 체크
        if not text:
            raise ValueError("TTS 입력 텍스트가 비어있습니다.")

        # Typecast SDK 사용
        async with AsyncTypecast(api_key=self.api_key) as client:
            response = await client.text_to_speech(
                TTSRequest(
                    text=text,
                    model="ssfm-v21",
                    voice_id=voice_id,
                    language=LanguageCode.KOR,
                    emotion=emotion_preset,
                    emotion_intensity=emotion_intensity,
                    audio_format="wav",
                )
            )

            return response.audio_data


# 싱글톤 인스턴스
typecast_tts_service = TypecastTTSService()
