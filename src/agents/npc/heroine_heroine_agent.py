"""
히로인간 대화 Agent

두 히로인 사이의 대화를 생성하고 저장합니다.

주요 기능:
1. 두 히로인간의 자연스러운 대화 생성
2. 대화 내용을 agent_memories 테이블에 저장 (npc_conversation)
3. 양방향 기억 저장 (npc_memory: A가 B에 대해, B가 A에 대해)

스트리밍/비스트리밍 동일 응답:
- 둘 다 동일한 프롬프트 사용
- 둘 다 DB에 저장
- 출력 형식만 다름 (스트리밍: 텍스트, 비스트리밍: JSON)

저장 위치:
- agent_memories 테이블 (npc_conversation): 대화 전체
- agent_memories 테이블 (npc_memory): 각 히로인의 관점에서 상대방에 대한 기억
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, AsyncIterator, Optional, Dict, Any, Tuple
from langchain.chat_models import init_chat_model

from agents.npc.emotion_mapper import heroine_emotion_to_int
from db.agent_memory import agent_memory_manager


# ============================================
# 페르소나 데이터 로드
# ============================================

# 페르소나 YAML 파일 경로
PERSONA_PATH = (
    Path(__file__).parent.parent.parent / "data" / "persona" / "heroine_persona.yaml"
)


def load_persona_data() -> Dict[str, Any]:
    """페르소나 YAML 파일 로드

    파일이 없거나 오류가 있으면 기본값 반환

    Returns:
        페르소나 데이터 딕셔너리
    """
    try:
        with open(PERSONA_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"경고: 페르소나 파일을 찾을 수 없습니다: {PERSONA_PATH}")
        return _get_default_persona()
    except Exception as e:
        print(f"경고: 페르소나 로드 실패: {e}")
        return _get_default_persona()


def _get_default_persona() -> Dict[str, Any]:
    """기본 페르소나 데이터 (파일 없을 때 사용)"""
    return {
        "letia": {
            "name": "레티아",
            "personality": {"base": "차갑고 무뚝뚝하지만 속정이 깊음"},
            "speech_style": {"honorific": False},
        },
        "lupames": {
            "name": "루파메스",
            "personality": {"base": "활발하고 호탕함"},
            "speech_style": {"honorific": False},
        },
        "roco": {
            "name": "로코",
            "personality": {"base": "순수하고 어린아이 같음"},
            "speech_style": {"honorific": True},
        },
    }


# 페르소나 데이터 로드 (모듈 로드시 1회)
PERSONA_DATA = load_persona_data()

# 히로인 ID -> 페르소나 키 매핑
HEROINE_KEY_MAP = {1: "letia", 2: "lupames", 3: "roco"}  # 레티아  # 루파메스  # 로코


class HeroineHeroineAgent:
    """히로인간 대화 Agent

    두 히로인 사이의 대화를 생성하고 저장합니다.
    스트리밍과 비스트리밍 모두 동일한 대화를 생성하고 DB에 저장합니다.

    사용 예시:
        agent = HeroineHeroineAgent()

        # 비스트리밍 (JSON 배열 반환)
        result = await agent.generate_and_save_conversation(1, 2)

        # 스트리밍 (텍스트 스트림 + DB 저장)
        async for chunk in agent.generate_conversation_stream(1, 2):
            print(chunk, end="")
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """초기화

        Args:
            model_name: 사용할 LLM 모델명
        """
        # 대화 생성용 LLM (temperature=0.8로 다양한 대화)
        self.llm = init_chat_model(model=model_name, temperature=0.8)
        self.streaming_llm = init_chat_model(
            model=model_name, temperature=0.8, streaming=True
        )

    # ============================================
    # 페르소나 및 관계 헬퍼 메서드
    # ============================================

    def _get_persona(self, heroine_id: int) -> Dict[str, Any]:
        """히로인 페르소나 가져오기

        Args:
            heroine_id: 히로인 ID (1=레티아, 2=루파메스, 3=로코)

        Returns:
            페르소나 딕셔너리
        """
        key = HEROINE_KEY_MAP.get(heroine_id, "letia")
        return PERSONA_DATA.get(key, PERSONA_DATA.get("letia", {}))

    def _get_relationship(self, heroine1_id: int, heroine2_id: int) -> str:
        """두 히로인간의 관계 설명

        각 히로인이 상대방을 어떻게 생각하는지 반환합니다.

        Args:
            heroine1_id: 관점의 주체 히로인 ID
            heroine2_id: 관계 대상 히로인 ID

        Returns:
            관계 설명 문자열
        """
        relationships = {
            (
                1,
                2,
            ): "라이벌이자 동료. 레티아는 루파메스를 시끄럽지만 믿을 수 있다고 생각함",
            (1, 3): "레티아는 로코를 보호해야 할 순수한 존재로 봄",
            (2, 1): "루파메스는 레티아를 재수없게 강하지만 믿을 수 있다고 생각함",
            (2, 3): "루파메스는 로코를 귀여운 동생처럼 대함. 맛있는 것을 많이 줌",
            (3, 1): "로코는 레티아 언니를 동경하지만 약간 무서워함",
            (3, 2): "로코는 루파메스 언니가 따뜻하다고 느낌. 맛있는 것도 많이 줌",
        }
        return relationships.get((heroine1_id, heroine2_id), "동료 관계")

    async def generate_situation(self) -> str:
        """대화 상황 자동 생성

        미리 정의된 상황 목록 중 하나를 선택하여 구체화합니다.

        Returns:
            구체적인 상황 설명 문자열
        """
        situations = [
            "셀레파이스 길드 휴게실에서 쉬는 중",
            "던전 탐험을 마치고 돌아온 직후",
            "함께 식사를 하는 중",
            "훈련장에서 훈련을 마친 후",
            "밤에 길드 옥상에서 별을 보는 중",
            "비가 와서 실내에 갇힌 상황",
            "새로운 의뢰를 기다리는 중",
            "멘토가 잠시 자리를 비운 사이",
        ]

        situations_text = "\n".join([f"- {s}" for s in situations])

        prompt = f"""다음 상황 목록 중 하나를 선택하고, 구체적인 상황 설명을 만들어주세요.

상황 목록:
{situations_text}

출력 형식:
선택한 상황과 함께 2-3문장으로 구체적인 상황을 설명하세요."""

        response = await self.llm.ainvoke(prompt)
        return response.content

    # ============================================
    # 프롬프트 생성 (스트리밍/비스트리밍 공통)
    # ============================================

    def _build_conversation_prompt(
        self,
        heroine1_id: int,
        heroine2_id: int,
        situation: str,
        turn_count: int,
        for_streaming: bool = False,
    ) -> str:
        """대화 생성 프롬프트 (스트리밍/비스트리밍 공통)

        동일한 프롬프트로 동일한 품질의 대화를 생성합니다.

        Args:
            heroine1_id: 첫 번째 히로인 ID
            heroine2_id: 두 번째 히로인 ID
            situation: 대화 상황
            turn_count: 대화 턴 수
            for_streaming: 스트리밍용이면 텍스트 형식, 아니면 JSON 형식

        Returns:
            프롬프트 문자열
        """
        persona1 = self._get_persona(heroine1_id)
        persona2 = self._get_persona(heroine2_id)

        relationship1to2 = self._get_relationship(heroine1_id, heroine2_id)
        relationship2to1 = self._get_relationship(heroine2_id, heroine1_id)

        honorific1 = (
            "존댓말"
            if persona1.get("speech_style", {}).get("honorific", False)
            else "반말"
        )
        honorific2 = (
            "존댓말"
            if persona2.get("speech_style", {}).get("honorific", False)
            else "반말"
        )

        name1 = persona1.get("name", "히로인1")
        name2 = persona2.get("name", "히로인2")

        # 출력 형식 (스트리밍은 텍스트, 비스트리밍은 JSON)
        if for_streaming:
            output_format = f"""[출력 형식]
각 대화를 다음 형식으로 출력하세요:
[{name1}] (감정) 대사
[{name2}] (감정) 대사
..."""
        else:
            output_format = f"""[출력 형식]
JSON 배열로 출력하세요:
[
    {{"speaker_id": {heroine1_id}, "speaker_name": "{name1}", "text": "대사", "emotion": "neutral|joy|fun|sorrow|angry|surprise|mysterious"}},
    {{"speaker_id": {heroine2_id}, "speaker_name": "{name2}", "text": "대사", "emotion": "neutral|joy|fun|sorrow|angry|surprise|mysterious"}},
    ...
]"""

        prompt = f"""두 히로인 사이의 자연스러운 대화를 생성해주세요.

[상황]
{situation}

[히로인 1: {name1}]
- 성격: {persona1.get('personality', {}).get('base', '')}
- 말투: {honorific1}
- {name2}에 대한 관계: {relationship1to2}

[히로인 2: {name2}]
- 성격: {persona2.get('personality', {}).get('base', '')}
- 말투: {honorific2}
- {name1}에 대한 관계: {relationship2to1}

[규칙]
- 각 히로인의 성격과 말투를 일관되게 유지
- 서로의 관계를 반영한 자연스러운 대화
- 총 {turn_count}번의 대화 턴 (각 히로인이 번갈아 말함)

{output_format}"""

        return prompt

    def _parse_streaming_response(
        self, response_text: str, heroine1_id: int, heroine2_id: int
    ) -> List[Dict[str, Any]]:
        """스트리밍 응답을 JSON 형식으로 파싱

        [레티아] (neutral) 대사 형식을 JSON으로 변환합니다.

        Args:
            response_text: 스트리밍 전체 응답
            heroine1_id: 첫 번째 히로인 ID
            heroine2_id: 두 번째 히로인 ID

        Returns:
            대화 리스트 (각 항목: speaker_id, speaker_name, text, emotion)
        """
        persona1 = self._get_persona(heroine1_id)
        persona2 = self._get_persona(heroine2_id)
        name1 = persona1.get("name", "히로인1")
        name2 = persona2.get("name", "히로인2")

        conversation = []
        lines = response_text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # [이름] (감정) 대사 형식 파싱
            if line.startswith(f"[{name1}]"):
                speaker_id = heroine1_id
                speaker_name = name1
                rest = line[len(f"[{name1}]") :].strip()
            elif line.startswith(f"[{name2}]"):
                speaker_id = heroine2_id
                speaker_name = name2
                rest = line[len(f"[{name2}]") :].strip()
            else:
                continue

            # (감정) 대사 파싱
            emotion = "neutral"
            text = rest

            if rest.startswith("("):
                end_paren = rest.find(")")
                if end_paren > 0:
                    emotion = rest[1:end_paren].strip()
                    text = rest[end_paren + 1 :].strip()

            conversation.append(
                {
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_name,
                    "text": text,
                    "emotion": heroine_emotion_to_int(emotion),
                }
            )

        return conversation

    def _save_conversation_to_db(
        self,
        heroine1_id: int,
        heroine2_id: int,
        conversation: List[Dict[str, Any]],
        situation: str,
        importance_score: int = 5,
    ) -> str:
        """대화를 DB에 저장

        저장 내용:
        1. npc_conversation: 대화 전체 (agent_id = "conv_{작은ID}_{큰ID}")
        2. npc_memory: 각 히로인의 관점에서 상대방에 대한 기억

        Args:
            heroine1_id: 첫 번째 히로인 ID
            heroine2_id: 두 번째 히로인 ID
            conversation: 대화 리스트
            situation: 대화 상황
            importance_score: 중요도 (1-10)

        Returns:
            저장된 대화 ID
        """
        # 대화 내용을 하나의 텍스트로 변환
        content_parts = []
        for msg in conversation:
            content_parts.append(f"{msg['speaker_name']}: {msg['text']}")
        content_text = "\n".join(content_parts)

        if not content_text:
            return None

        # 메타데이터 구성
        metadata = {
            "situation": situation,
            "turn_count": len(conversation),
            "speakers": [heroine1_id, heroine2_id],
            "emotions": [msg.get("emotion", "neutral") for msg in conversation],
            "conversation": conversation,  # 전체 대화를 JSON으로 저장
        }

        # 1. NPC간 대화 저장 (npc_conversation 타입)
        # agent_id = "conv_{작은ID}_{큰ID}" 형식
        conv_id = agent_memory_manager.add_npc_conversation(
            npc1_id=heroine1_id,
            npc2_id=heroine2_id,
            content=content_text,
            importance=importance_score,
            metadata=metadata,
        )

        # 2. 양방향 기억 저장 (npc_memory 타입)
        # 각 히로인의 관점에서 상대방과의 대화를 기억
        persona1 = self._get_persona(heroine1_id)
        persona2 = self._get_persona(heroine2_id)

        content_preview = content_text[:200]

        agent_memory_manager.add_mutual_npc_memory(
            npc1_id=heroine1_id,
            npc2_id=heroine2_id,
            content=content_text,
            npc1_perspective=f"{persona2.get('name', '상대방')}와 대화함: {content_preview}...",
            npc2_perspective=f"{persona1.get('name', '상대방')}와 대화함: {content_preview}...",
            importance=importance_score,
            metadata={"conversation_id": conv_id, "situation": situation},
        )

        return conv_id

    # ============================================
    # 대화 생성 메서드
    # ============================================

    async def generate_conversation(
        self,
        heroine1_id: int,
        heroine2_id: int,
        situation: str = None,
        turn_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """대화 생성 (비스트리밍, 저장 안함)

        DB 저장 없이 대화만 생성합니다.

        Args:
            heroine1_id: 첫 번째 히로인 ID
            heroine2_id: 두 번째 히로인 ID
            situation: 대화 상황 (None이면 자동 생성)
            turn_count: 대화 턴 수

        Returns:
            대화 리스트 (각 항목: speaker_id, speaker_name, text, emotion)
        """
        if situation is None:
            situation = await self.generate_situation()

        prompt = self._build_conversation_prompt(
            heroine1_id, heroine2_id, situation, turn_count, for_streaming=False
        )

        response = await self.llm.ainvoke(prompt)

        # JSON 파싱
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            conversation = json.loads(content.strip())

            # emotion 문자열을 정수로 변환
            for msg in conversation:
                if "emotion" in msg and isinstance(msg["emotion"], str):
                    msg["emotion"] = heroine_emotion_to_int(msg["emotion"])
        except (json.JSONDecodeError, IndexError):
            persona1 = self._get_persona(heroine1_id)
            conversation = [
                {
                    "speaker_id": heroine1_id,
                    "speaker_name": persona1.get("name", "히로인"),
                    "text": "...",
                    "emotion": 0,  # neutral
                }
            ]

        return conversation

    async def generate_and_save_conversation(
        self,
        heroine1_id: int,
        heroine2_id: int,
        situation: str = None,
        turn_count: int = 5,
        importance_score: int = 5,
    ) -> Dict[str, Any]:
        """대화 생성 후 DB에 저장 (비스트리밍)

        Args:
            heroine1_id: 첫 번째 히로인 ID
            heroine2_id: 두 번째 히로인 ID
            situation: 대화 상황 (None이면 자동 생성)
            turn_count: 대화 턴 수
            importance_score: 중요도 (1-10)

        Returns:
            저장 결과 (id, heroine1_id, heroine2_id, content, conversation, timestamp)
        """
        if situation is None:
            situation = await self.generate_situation()

        # 대화 생성
        conversation = await self.generate_conversation(
            heroine1_id, heroine2_id, situation, turn_count
        )

        # DB에 저장
        conv_id = self._save_conversation_to_db(
            heroine1_id, heroine2_id, conversation, situation, importance_score
        )

        # 대화 내용 텍스트
        content_parts = []
        for msg in conversation:
            content_parts.append(f"{msg['speaker_name']}: {msg['text']}")
        content_text = "\n".join(content_parts)

        return {
            "id": conv_id,
            "heroine1_id": heroine1_id,
            "heroine2_id": heroine2_id,
            "content": content_text,
            "conversation": conversation,
            "importance_score": importance_score,
            "timestamp": datetime.now().isoformat(),
        }

    async def generate_conversation_stream(
        self,
        heroine1_id: int,
        heroine2_id: int,
        situation: str = None,
        turn_count: int = 5,
        importance_score: int = 5,
    ) -> AsyncIterator[str]:
        """대화 스트리밍 생성 + DB 저장

        비스트리밍과 동일하게 DB에 저장합니다.

        Args:
            heroine1_id: 첫 번째 히로인 ID
            heroine2_id: 두 번째 히로인 ID
            situation: 대화 상황 (None이면 자동 생성)
            turn_count: 대화 턴 수
            importance_score: 중요도 (1-10)

        Yields:
            대화 토큰
        """
        if situation is None:
            situation = await self.generate_situation()

        prompt = self._build_conversation_prompt(
            heroine1_id, heroine2_id, situation, turn_count, for_streaming=True
        )

        # 스트리밍으로 응답 생성
        full_response = ""
        async for chunk in self.streaming_llm.astream(prompt):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        # 응답을 JSON으로 파싱
        conversation = self._parse_streaming_response(
            full_response, heroine1_id, heroine2_id
        )

        # DB에 저장 (비스트리밍과 동일하게)
        if conversation:
            self._save_conversation_to_db(
                heroine1_id, heroine2_id, conversation, situation, importance_score
            )

    # ============================================
    # 조회 메서드
    # ============================================

    def get_conversations(
        self, heroine1_id: int = None, heroine2_id: int = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """저장된 대화 조회 (최신순)

        Args:
            heroine1_id: 첫 번째 히로인 ID로 필터링 (None이면 필터 없음)
            heroine2_id: 두 번째 히로인 ID로 필터링 (None이면 필터 없음)
            limit: 최대 개수

        Returns:
            대화 목록
        """
        memories = agent_memory_manager.get_npc_conversations(
            npc1_id=heroine1_id, npc2_id=heroine2_id, limit=limit
        )

        conversations = []
        for mem in memories:
            conversations.append(
                {
                    "id": mem.id,
                    "agent_id": mem.agent_id,
                    "content": mem.content,
                    "importance_score": mem.importance_score,
                    "metadata": mem.metadata,
                    "created_at": (
                        mem.created_at.isoformat() if mem.created_at else None
                    ),
                }
            )

        return conversations

    def search_conversations(
        self, heroine_id: int, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """벡터 검색으로 관련 대화 조회

        Args:
            heroine_id: 히로인 ID (해당 히로인이 참여한 대화만)
            query: 검색 쿼리
            top_k: 최대 개수

        Returns:
            검색된 대화 목록 (relevance_score 포함)
        """
        memories = agent_memory_manager.search_npc_conversations(
            npc_id=heroine_id, query=query, top_k=top_k
        )

        conversations = []
        for mem in memories:
            conversations.append(
                {
                    "id": mem.id,
                    "agent_id": mem.agent_id,
                    "content": mem.content,
                    "importance_score": mem.importance_score,
                    "metadata": mem.metadata,
                    "created_at": (
                        mem.created_at.isoformat() if mem.created_at else None
                    ),
                    "relevance_score": mem.relevance_score,
                }
            )

        return conversations


# 싱글톤 인스턴스 (앱 전체에서 하나만 사용)
heroine_heroine_agent = HeroineHeroineAgent()
