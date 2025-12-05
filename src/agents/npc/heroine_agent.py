"""
히로인 NPC Agent

기억을 잃은 3명의 히로인(레티아, 루파메스, 로코)과의 대화를 처리합니다.

주요 기능:
1. 호감도(affection), 정신력(sanity), 기억진척도(memoryProgress) 관리
2. 키워드 기반 호감도 변화 계산 (좋아하는것 +10, 트라우마 -10)
3. 의도 분류에 따른 컨텍스트 검색 (기억/시나리오)
4. 캐릭터 페르소나 기반 응답 생성

스트리밍/비스트리밍 동일 응답:
- 둘 다 동일한 컨텍스트(기억/시나리오)를 사용
- 둘 다 동일한 프롬프트로 응답 생성
- LLM 호출은 1번만

저장 위치:
- Redis: 세션 상태 (affection, sanity, memoryProgress, conversation_buffer)
- Mem0: User-NPC 장기 기억 (대화 내용)
"""

import json
import yaml
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional, Tuple
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import START, END, StateGraph

from agents.npc.npc_state import HeroineState, IntentType
from agents.npc.base_npc_agent import (
    BaseNPCAgent,
    calculate_memory_progress,
    calculate_affection_change,
)
from agents.npc.emotion_mapper import heroine_emotion_to_int
from db.redis_manager import redis_manager
from db.mem0_manager import mem0_manager
from db.agent_memory import agent_memory_manager
from db.session_checkpoint_manager import session_checkpoint_manager
from services.heroine_scenario_service import heroine_scenario_service
from agents.npc.heroine_heroine_agent import heroine_heroine_agent


# ============================================
# 페르소나 데이터 로드
# ============================================

# 페르소나 YAML 파일 경로
PERSONA_PATH = (
    Path(__file__).parent.parent.parent
    / "prompts"
    / "prompt_type"
    / "npc"
    / "heroine_persona.yaml"
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
            "affection_responses": {
                "low": {"description": "경계", "examples": ["...뭐야."]},
                "mid": {"description": "중립", "examples": ["흠..."]},
                "high": {"description": "친근", "examples": ["...고마워."]},
                "max": {"description": "애정", "examples": ["...바보."]},
            },
            "sanity_responses": {"zero": {"description": "우울", "examples": ["..."]}},
            "liked_keywords": ["검", "훈련", "강해지기"],
            "trauma_keywords": ["화재", "불", "가족"],
        }
    }


# 페르소나 데이터 로드 (모듈 로드시 1회)
PERSONA_DATA = load_persona_data()

# 히로인 ID -> 페르소나 키 매핑
HEROINE_KEY_MAP = {1: "letia", 2: "lupames", 3: "roco"}  # 레티아  # 루파메스  # 로코


class HeroineAgent(BaseNPCAgent):
    """히로인 NPC Agent

    기억을 잃은 히로인과의 대화를 처리합니다.
    스트리밍과 비스트리밍 모두 동일한 응답을 생성합니다.

    사용 예시:
        agent = HeroineAgent()

        # 비스트리밍
        result = await agent.process_message(state)

        # 스트리밍
        async for chunk in agent.generate_response_stream(state):
            print(chunk, end="")
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """초기화

        Args:
            model_name: 사용할 LLM 모델명
        """
        super().__init__(model_name)

        # 의도 분류용 LLM (temperature=0으로 일관된 분류)
        self.intent_llm = init_chat_model(model=model_name, temperature=0)

        # LangGraph 빌드 (비스트리밍용)
        self.graph = self._build_graph()

    # ============================================
    # 세션 및 페르소나 관련 메서드
    # ============================================

    def _create_initial_session(self, player_id: int, npc_id: int) -> dict:
        """히로인 초기 세션 생성

        Args:
            player_id: 플레이어 ID
            npc_id: 히로인 ID

        Returns:
            초기 세션 딕셔너리
        """
        return {
            "player_id": player_id,
            "npc_id": npc_id,
            "npc_type": "heroine",
            "conversation_buffer": [],  # 최근 대화 목록 (최대 20개)
            "short_term_summary": "",  # 단기 요약
            "recent_used_keywords": [],  # 최근 5턴 내 사용된 좋아하는 키워드
            "state": {
                "affection": 0,  # 호감도 (0-100)
                "sanity": 100,  # 정신력 (0-100)
                "memoryProgress": 0,  # 기억 진척도 (0-100)
                "emotion": "neutral",  # 현재 감정
            },
        }

    def _get_persona(self, heroine_id: int) -> Dict[str, Any]:
        """히로인 페르소나 가져오기

        Args:
            heroine_id: 히로인 ID (1=레티아, 2=루파메스, 3=로코)

        Returns:
            페르소나 딕셔너리
        """
        key = HEROINE_KEY_MAP.get(heroine_id, "letia")
        return PERSONA_DATA.get(key, PERSONA_DATA.get("letia", {}))

    def _get_affection_level(self, affection: int) -> str:
        """호감도 레벨 결정

        Args:
            affection: 호감도 (0-100)

        Returns:
            레벨 문자열 (low/mid/high/max)
        """
        if affection >= 90:
            return "max"
        elif affection >= 60:
            return "high"
        elif affection >= 30:
            return "mid"
        return "low"

    def _format_persona(
        self, persona: Dict[str, Any], affection: int, sanity: int
    ) -> str:
        """페르소나를 프롬프트용 문자열로 포맷

        Args:
            persona: 페르소나 딕셔너리
            affection: 현재 호감도
            sanity: 현재 정신력

        Returns:
            포맷된 문자열
        """
        level = self._get_affection_level(affection)

        # 기본 정보
        lines = [
            f"이름: {persona.get('name', '알 수 없음')}",
            f"성격: {persona.get('personality', {}).get('base', '알 수 없음')}",
            f"말투: {'존댓말' if persona.get('speech_style', {}).get('honorific', False) else '반말'}",
            "",
            f"[현재 호감도 레벨: {level}]",
        ]

        # 호감도 레벨별 반응
        affection_resp = persona.get("affection_responses", {}).get(level, {})
        lines.append(f"반응 스타일: {affection_resp.get('description', '')}")
        lines.append("예시 대사:")
        for example in affection_resp.get("examples", [])[:3]:
            lines.append(f"  - {example}")

        # 정신력 0이면 우울 상태 추가
        if sanity == 0:
            lines.append("")
            lines.append("[경고: 정신력 0 - 우울 상태]")
            sanity_resp = persona.get("sanity_responses", {}).get("zero", {})
            lines.append(f"반응: {sanity_resp.get('description', '우울함')}")
            for example in sanity_resp.get("examples", [])[:2]:
                lines.append(f"  - {example}")

        return "\n".join(lines)

    # ============================================
    # 컨텍스트 준비 메서드 (스트리밍/비스트리밍 공통)
    # ============================================

    async def _analyze_keywords(self, state: HeroineState) -> Tuple[int, Optional[str]]:
        """키워드 분석 - 호감도 변화량 사전 계산

        사용자 메시지에서 좋아하는 키워드/트라우마 키워드를 찾아
        호감도 변화량을 미리 계산합니다.

        Args:
            state: 현재 상태

        Returns:
            (호감도 변화량, 사용된 좋아하는 키워드 또는 None)
        """
        user_message = state["messages"][-1].content
        npc_id = state["npc_id"]
        persona = self._get_persona(npc_id)

        # 현재 상태
        affection = state.get("affection", 0)
        recent_used_keywords = state.get("recent_used_keywords", [])

        # 페르소나에서 키워드 가져오기
        liked_keywords = persona.get("liked_keywords", [])
        trauma_keywords = persona.get("trauma_keywords", [])

        # 호감도 변화량 계산 (5턴 내 반복 키워드 방지)
        affection_delta, used_keyword = calculate_affection_change(
            current_affection=affection,
            liked_keywords=liked_keywords,
            trauma_keywords=trauma_keywords,
            user_message=user_message,
            recent_used_keywords=recent_used_keywords,
        )

        return affection_delta, used_keyword

    async def _classify_intent(self, state: HeroineState) -> str:
        """의도 분류

        사용자 메시지의 의도를 분류합니다:
        - general: 일반 대화
        - memory_recall: 과거 대화/경험 질문 (Mem0 검색)
        - scenario_inquiry: 히로인 과거/비밀 질문 (시나리오 DB 검색)

        Args:
            state: 현재 상태

        Returns:
            의도 문자열
        """
        user_message = state["messages"][-1].content
        conversation_context = state.get("short_term_summary", "")

        prompt = f"""다음 플레이어 메시지의 의도를 분류하세요.

[최근 대화 맥락]
{conversation_context}

[플레이어 메시지]
{user_message}

[분류 기준]
- general: 일상 대화, 감정 표현, 질문 없는 대화
- memory_recall: "우리 전에 뭐 얘기했지?", "나 기억해?" 등 플레이어와 히로인이 함께 나눈 과거 대화/경험을 물어봄
- scenario_inquiry: 히로인의 과거, 기억 상실 전 이야기, 비밀, 정체성에 대해 물어봄

반드시 general, memory_recall, scenario_inquiry 중 하나만 출력하세요."""

        response = await self.intent_llm.ainvoke(prompt)
        intent = response.content.strip().lower()

        # 유효하지 않으면 기본값
        if intent not in ["general", "memory_recall", "scenario_inquiry"]:
            intent = "general"

        return intent

    async def _retrieve_memory(self, state: HeroineState) -> str:
        """기억 검색

        1. Mem0에서 플레이어-NPC 대화 기억 검색 (항상)
        2. 다른 히로인 이름 언급시 NPC-NPC 대화 검색

        Args:
            state: 현재 상태

        Returns:
            검색된 기억 텍스트
        """
        user_message = state["messages"][-1].content
        player_id = state["player_id"]
        npc_id = state["npc_id"]

        facts_parts = []

        # 1. Mem0에서 플레이어-NPC 대화 기억 검색
        user_memories = mem0_manager.search_memory(
            player_id, npc_id, user_message, limit=3
        )
        if user_memories:
            facts_parts.append("[플레이어와의 기억]")
            for m in user_memories:
                memory_text = m.get("memory", m.get("text", ""))
                facts_parts.append(f"- {memory_text}")

        # 2. 다른 히로인 이름 언급시 NPC-NPC 대화 검색
        other_heroine_names = ["레티아", "루파메스", "로코"]
        mentioned = any(name in user_message for name in other_heroine_names)

        if mentioned:
            npc_conversations = heroine_heroine_agent.search_conversations(
                heroine_id=npc_id, query=user_message, top_k=2
            )
            if npc_conversations:
                facts_parts.append("\n[다른 히로인과의 대화 기억]")
                for conv in npc_conversations:
                    content_preview = conv["content"][:200]
                    facts_parts.append(f"- {content_preview}...")

        return "\n".join(facts_parts) if facts_parts else "관련 기억 없음"

    async def _retrieve_scenario(self, state: HeroineState) -> str:
        """시나리오 DB 검색

        현재 기억진척도 이하로 해금된 시나리오를 검색합니다.

        Args:
            state: 현재 상태

        Returns:
            검색된 시나리오 텍스트
        """
        user_message = state["messages"][-1].content
        npc_id = state["npc_id"]
        memory_progress = state.get("memoryProgress", 0)

        scenarios = heroine_scenario_service.search_scenarios(
            query=user_message,
            heroine_id=npc_id,
            max_memory_progress=memory_progress,
            limit=2,
        )

        if scenarios:
            return "\n\n".join([s["content"] for s in scenarios])
        return "해금된 시나리오 없음"

    async def _prepare_context(self, state: HeroineState) -> Dict[str, Any]:
        """컨텍스트 준비 (스트리밍/비스트리밍 공통)

        LLM 호출 전에 필요한 모든 정보를 준비합니다:
        1. 키워드 분석 (호감도 변화량 계산)
        2. 의도 분류
        3. 의도에 따른 검색 (기억/시나리오)

        Args:
            state: 현재 상태

        Returns:
            컨텍스트 딕셔너리 (affection_delta, used_liked_keyword, intent, retrieved_facts, unlocked_scenarios)
        """
        import time

        total_start = time.time()

        # 1. 키워드 분석
        t1 = time.time()
        affection_delta, used_keyword = await self._analyze_keywords(state)
        print(f"[TIMING] 키워드 분석: {time.time() - t1:.3f}s")

        # 2. 의도 분류
        t2 = time.time()
        intent = await self._classify_intent(state)
        print(f"[TIMING] 의도 분류: {time.time() - t2:.3f}s")

        user_message = state["messages"][-1].content
        print(f"[DEBUG] 의도 분류 결과: {intent}")

        # 3. 시나리오 관련 키워드 확인 (의도 분류 보완)
        """
        scenario_keywords = [
            "고향",
            "과거",
            "기억",
            "옛날",
            "가족",
            "어렸을",
            "예전",
            "해금",
            "비밀",
            "정체",
        ]
        has_scenario_keyword = any(kw in user_message for kw in scenario_keywords)

        if has_scenario_keyword and intent != "scenario_inquiry":
            intent = "scenario_inquiry"
            print(f"[DEBUG] 키워드 감지로 의도 변경: scenario_inquiry")
        """
        # 4. 의도에 따른 검색
        retrieved_facts = "없음"
        unlocked_scenarios = "없음"

        if intent == "memory_recall":
            # 기억 회상 -> Mem0 + NPC간 기억 검색
            t3 = time.time()
            retrieved_facts = await self._retrieve_memory(state)
            print(f"[TIMING] 기억 검색: {time.time() - t3:.3f}s")
            print(
                f"[DEBUG] 기억 검색 결과: {retrieved_facts[:200] if retrieved_facts else 'None'}..."
            )
        elif intent == "scenario_inquiry":
            # 시나리오 질문 -> 시나리오 DB 검색
            t3 = time.time()
            unlocked_scenarios = await self._retrieve_scenario(state)
            print(f"[TIMING] 시나리오 검색: {time.time() - t3:.3f}s")
            print(
                f"[DEBUG] 시나리오 검색 결과: {unlocked_scenarios[:200] if unlocked_scenarios else 'None'}..."
            )
        else:
            print(f"[DEBUG] general 의도 - 검색 안 함")

        print(f"[TIMING] 컨텍스트 준비 총합: {time.time() - total_start:.3f}s")
        return {
            "affection_delta": affection_delta,
            "used_liked_keyword": used_keyword,
            "intent": intent,
            "retrieved_facts": retrieved_facts,
            "unlocked_scenarios": unlocked_scenarios,
        }

    def _build_full_prompt(
        self, state: HeroineState, context: Dict[str, Any], for_streaming: bool = False
    ) -> str:
        """전체 프롬프트 생성 (스트리밍/비스트리밍 공통)

        동일한 컨텍스트로 동일한 프롬프트를 생성합니다.

        Args:
            state: 현재 상태
            context: 컨텍스트 (검색 결과 등)
            for_streaming: 스트리밍용이면 JSON 형식 요청 안함

        Returns:
            프롬프트 문자열
        """
        npc_id = state["npc_id"]
        persona = self._get_persona(npc_id)

        affection = state.get("affection", 0)
        sanity = state.get("sanity", 100)
        memory_progress = state.get("memoryProgress", 0)

        # 호감도 변화 힌트 (LLM에게 알려줌)
        pre_calculated_delta = context.get("affection_delta", 0)
        if pre_calculated_delta > 0:
            affection_hint = f"플레이어가 당신이 좋아하는 것에 대해 말했습니다. 기분이 좋아집니다. (호감도 +{pre_calculated_delta})"
        elif pre_calculated_delta < 0:
            affection_hint = f"플레이어가 당신의 트라우마를 건드렸습니다. 불쾌합니다. (호감도 {pre_calculated_delta})"
        else:
            affection_hint = "특별한 호감도 변화 없음"

        # 출력 형식 (스트리밍은 텍스트만, 비스트리밍은 JSON)
        if for_streaming:
            output_format = "캐릭터로서 자연스럽게 대답하세요. 대화만 출력하세요."
        else:
            output_format = """[출력 형식]
반드시 아래 JSON 형식으로 출력하세요:
{
    "thought": "(내면의 생각 - 플레이어에게 보이지 않음)",
    "text": "(실제 대화 내용)",
    "emotion": "neutral|joy|fun|sorrow|angry|surprise|mysterious"
}"""

        time_since_last_chat = self.get_time_since_last_chat(state["player_id"], npc_id)

        prompt = f"""당신은 히로인 {persona.get('name', '알 수 없음')}입니다.

[마지막 대화로부터 경과 시간]
{time_since_last_chat}

[현재 상태]
- 호감도(Affection): {affection}
- 정신력(Sanity): {sanity}
- 기억진척도(MemoryProgress): {memory_progress}

[페르소나]
{self._format_persona(persona, affection, sanity)}

[페르소나 규칙]
- 해금되지 않은 기억(memoryProgress > {memory_progress})은 절대 말하지 않습니다.
- [해금된 시나리오]에 내용이 있으면 이를 바탕으로 자세히 답변하세요.
- [해금된 시나리오]가 "없음"일 때만 "잘 기억이 안 나..." 라고 답합니다.
- Sanity가 0이면 매우 우울한 상태로 대화합니다.
- 캐릭터의 말투와 성격을 일관되게 유지합니다.

[호감도 변화 정보]
{affection_hint}

[장기 기억 (검색 결과)]
{context.get('retrieved_facts', '없음')}

[해금된 시나리오]
{context.get('unlocked_scenarios', '없음')}

[최근 대화 기록]
{self.format_conversation_history(state.get('conversation_buffer', []))}

[플레이어 메시지]
{state['messages'][-1].content}

{output_format}"""

        return prompt

    async def _update_state_after_response(
        self,
        state: HeroineState,
        context: Dict[str, Any],
        response_text: str,
        emotion_int: int = 0,
    ) -> Dict[str, Any]:
        """응답 후 상태 업데이트 (LLM 재호출 없이)

        스트리밍/비스트리밍 모두 이 메서드로 상태를 업데이트합니다.

        저장 위치:
        - Redis: 세션 상태 (affection, sanity, memoryProgress, conversation_buffer)
        - Mem0: User-NPC 대화 기억

        Args:
            state: 현재 상태
            context: 컨텍스트 (affection_delta 등)
            response_text: 생성된 응답 텍스트
            emotion_int: 감정 정수값 (기본값 0=neutral)

        Returns:
            업데이트된 상태 값들
        """
        player_id = state["player_id"]
        npc_id = state["npc_id"]

        # 현재 상태
        affection = state.get("affection", 0)
        sanity = state.get("sanity", 100)
        memory_progress = state.get("memoryProgress", 0)

        # 변화량
        affection_delta = context.get("affection_delta", 0)
        sanity_delta = affection_delta if affection_delta > 0 else 0

        # 새 값 계산
        new_affection = max(0, min(100, affection + affection_delta))
        new_sanity = max(0, min(100, sanity + sanity_delta))
        new_memory_progress = calculate_memory_progress(
            new_affection, memory_progress, affection_delta
        )

        # Redis 세션 업데이트
        session = redis_manager.load_session(player_id, npc_id)
        if session:
            # 상태 업데이트
            session["state"]["affection"] = new_affection
            session["state"]["sanity"] = new_sanity
            session["state"]["memoryProgress"] = new_memory_progress
            session["state"]["emotion"] = emotion_int

            # 대화 버퍼에 추가
            session["conversation_buffer"].append(
                {"role": "user", "content": state["messages"][-1].content}
            )
            session["conversation_buffer"].append(
                {"role": "assistant", "content": response_text}
            )

            # 최근 사용된 좋아하는 키워드 업데이트 (5개 유지)
            used_keyword = context.get("used_liked_keyword")
            recent_keywords = session.get("recent_used_keywords", [])
            if used_keyword:
                recent_keywords.append(used_keyword)
            session["recent_used_keywords"] = recent_keywords[-5:]

            # turn_count 업데이트
            turn_count = session.get("turn_count", 0) + 1
            session["turn_count"] = turn_count

            # last_chat_at 업데이트
            session["last_chat_at"] = datetime.now().isoformat()

            # 요약 생성 조건 확인 (20턴 또는 1시간 경과)
            last_summary_at = session.get("last_summary_at")
            should_generate_summary = False

            if turn_count >= 20:
                should_generate_summary = True
            elif last_summary_at:
                last_summary_time = datetime.fromisoformat(last_summary_at)
                if datetime.now() - last_summary_time > timedelta(hours=1):
                    should_generate_summary = True
            elif turn_count >= 10:
                should_generate_summary = True

            if should_generate_summary:
                session["turn_count"] = 0
                session["last_summary_at"] = datetime.now().isoformat()

                conversations = []
                for i in range(0, len(session["conversation_buffer"]), 2):
                    if i + 1 < len(session["conversation_buffer"]):
                        conversations.append(
                            {
                                "user": session["conversation_buffer"][i].get(
                                    "content", ""
                                ),
                                "npc": session["conversation_buffer"][i + 1].get(
                                    "content", ""
                                ),
                            }
                        )

                asyncio.create_task(
                    self._generate_and_save_summary(player_id, npc_id, conversations)
                )

            # 세션 저장
            redis_manager.save_session(player_id, npc_id, session)

        # Mem0에 대화 저장 (백그라운드)
        user_msg = state["messages"][-1].content
        asyncio.create_task(
            self._save_to_mem0_background(player_id, npc_id, user_msg, response_text)
        )

        return {
            "affection": new_affection,
            "sanity": new_sanity,
            "memoryProgress": new_memory_progress,
            "emotion": emotion_int,
            "response_text": response_text,
        }

    async def _save_to_mem0_background(
        self, player_id: int, npc_id: int, user_msg: str, npc_response: str
    ) -> None:
        """백그라운드로 Mem0에 대화 저장

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            user_msg: 유저 메시지
            npc_response: NPC 응답
        """
        try:
            mem0_manager.add_memory(
                player_id, npc_id, f"플레이어: {user_msg}\n히로인: {npc_response}"
            )
        except Exception as e:
            print(f"[ERROR] Mem0 저장 실패: {e}")

    async def _generate_and_save_summary(
        self, player_id: int, npc_id: int, conversations: list
    ) -> None:
        """백그라운드로 요약 생성 및 저장

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            conversations: 대화 목록
        """
        try:
            summary_item = await session_checkpoint_manager.generate_summary(
                player_id, npc_id, conversations
            )

            session = redis_manager.load_session(player_id, npc_id)
            if session:
                summary_list = session.get("summary_list", [])
                summary_list.append(summary_item)

                summary_list = session_checkpoint_manager.prune_summary_list(
                    summary_list
                )
                session["summary_list"] = summary_list

                redis_manager.save_session(player_id, npc_id, session)

            session_checkpoint_manager.save_summary(player_id, npc_id, summary_item)

        except Exception as e:
            print(f"[ERROR] _generate_and_save_summary 실패: {e}")

    # ============================================
    # LangGraph 빌드 (비스트리밍용)
    # ============================================

    def _build_graph(self) -> StateGraph:
        """LangGraph 빌드

        노드 흐름:
        START -> keyword_analyze -> router
        router -> (분기)
            - general -> generate
            - memory_recall -> memory_retrieve -> generate
            - scenario_inquiry -> scenario_retrieve -> generate
        generate -> post_process -> END

        Returns:
            컴파일된 StateGraph
        """
        graph = StateGraph(HeroineState)

        # 노드 추가
        graph.add_node("keyword_analyze", self._keyword_analyze_node)
        graph.add_node("router", self._router_node)
        graph.add_node("memory_retrieve", self._memory_retrieve_node)
        graph.add_node("scenario_retrieve", self._scenario_retrieve_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("post_process", self._post_process_node)

        # 엣지 추가
        graph.add_edge(START, "keyword_analyze")
        graph.add_edge("keyword_analyze", "router")

        # 조건부 분기
        graph.add_conditional_edges(
            "router",
            self._route_by_intent,
            {
                "general": "generate",
                "memory_recall": "memory_retrieve",
                "scenario_inquiry": "scenario_retrieve",
            },
        )

        graph.add_edge("memory_retrieve", "generate")
        graph.add_edge("scenario_retrieve", "generate")
        graph.add_edge("generate", "post_process")
        graph.add_edge("post_process", END)

        return graph.compile()

    # ============================================
    # LangGraph 노드 구현
    # ============================================

    async def _keyword_analyze_node(self, state: HeroineState) -> dict:
        """키워드 분석 노드"""
        import time

        t = time.time()
        affection_delta, used_keyword = await self._analyze_keywords(state)
        print(f"[TIMING] 키워드 분석: {time.time() - t:.3f}s")
        return {"affection_delta": affection_delta, "used_liked_keyword": used_keyword}

    async def _router_node(self, state: HeroineState) -> dict:
        """의도 분류 노드"""
        import time

        t = time.time()
        intent = await self._classify_intent(state)
        print(f"[TIMING] 의도 분류: {time.time() - t:.3f}s")
        user_message = state["messages"][-1].content
        print(f"[DEBUG] 의도 분류 결과: {intent}")

        # 시나리오 관련 키워드 확인 (의도 분류 보완)
        """
        scenario_keywords = [
            "고향",
            "과거",
            "기억",
            "전에",
            "옛날",
            "가족",
            "어렸을",
            "예전",
            "해금",
            "비밀",
            "정체",
        ]
        has_scenario_keyword = any(kw in user_message for kw in scenario_keywords)

        if has_scenario_keyword and intent != "scenario_inquiry":
            intent = "scenario_inquiry"
            print(f"[DEBUG] 키워드 감지로 의도 변경: scenario_inquiry")
        """
        return {"intent": intent}

    def _route_by_intent(self, state: HeroineState) -> str:
        """의도에 따라 라우팅"""
        return state.get("intent", "general")

    async def _memory_retrieve_node(self, state: HeroineState) -> dict:
        """기억 검색 노드"""
        import time

        t = time.time()
        facts = await self._retrieve_memory(state)
        print(f"[TIMING] 기억 검색: {time.time() - t:.3f}s")
        return {"retrieved_facts": facts}

    async def _scenario_retrieve_node(self, state: HeroineState) -> dict:
        """시나리오 DB 검색 노드"""
        import time

        t = time.time()
        scenarios = await self._retrieve_scenario(state)
        print(f"[TIMING] 시나리오 검색: {time.time() - t:.3f}s")
        print(
            f"[DEBUG] 시나리오 검색 결과: {scenarios[:200] if scenarios else 'None'}..."
        )
        return {"unlocked_scenarios": scenarios}

    async def _generate_node(self, state: HeroineState) -> dict:
        """응답 생성 노드"""
        import time

        total_start = time.time()

        # 컨텍스트 구성
        context = {
            "affection_delta": state.get("affection_delta", 0),
            "retrieved_facts": state.get("retrieved_facts", "없음"),
            "unlocked_scenarios": state.get("unlocked_scenarios", "없음"),
        }
        print(
            f"[DEBUG] generate 노드 - unlocked_scenarios: {context['unlocked_scenarios'][:200] if context['unlocked_scenarios'] != '없음' else '없음'}..."
        )

        # 프롬프트 생성 및 LLM 호출
        t1 = time.time()
        prompt = self._build_full_prompt(state, context, for_streaming=False)
        print(f"[TIMING] 프롬프트 빌드: {time.time() - t1:.3f}s")

        t2 = time.time()
        response = await self.llm.ainvoke(prompt)
        print(f"[TIMING] LLM 호출: {time.time() - t2:.3f}s")

        # JSON 파싱
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            result = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            result = {"thought": "", "text": response.content, "emotion": "neutral"}

        emotion_str = result.get("emotion", "neutral")
        print(f"[TIMING] generate 노드 총합: {time.time() - total_start:.3f}s")
        return {
            "response_text": result.get("text", ""),
            "emotion": heroine_emotion_to_int(emotion_str),
            "emotion_str": emotion_str,
        }

    async def _post_process_node(self, state: HeroineState) -> dict:
        """후처리 노드 - 상태 업데이트"""
        import time

        t = time.time()

        context = {
            "affection_delta": state.get("affection_delta", 0),
            "used_liked_keyword": state.get("used_liked_keyword"),
        }

        result = await self._update_state_after_response(
            state,
            context,
            state.get("response_text", ""),
            state.get("emotion", 0),
        )

        print(f"[TIMING] 상태 업데이트: {time.time() - t:.3f}s")
        return {
            "affection": result["affection"],
            "sanity": result["sanity"],
            "memoryProgress": result["memoryProgress"],
        }

    # ============================================
    # 공개 메서드
    # ============================================

    async def process_message(self, state: HeroineState) -> HeroineState:
        """메시지 처리 (비스트리밍)

        LangGraph 전체 파이프라인을 실행합니다.

        Args:
            state: 입력 상태

        Returns:
            처리 후 상태
        """
        result = await self.graph.ainvoke(state)
        return result

    async def generate_response_stream(self, state: HeroineState) -> AsyncIterator[str]:
        """스트리밍 응답 생성 (컨텍스트 포함)

        비스트리밍과 동일한 컨텍스트를 사용합니다.
        LLM은 1번만 호출됩니다.

        Args:
            state: 입력 상태

        Yields:
            응답 토큰
        """
        import time

        total_start = time.time()

        # 1. 컨텍스트 준비 (기억/시나리오 검색)
        context = await self._prepare_context(state)

        # 2. 전체 프롬프트 생성 (비스트리밍과 동일한 컨텍스트)
        t1 = time.time()
        prompt = self._build_full_prompt(state, context, for_streaming=True)
        print(f"[TIMING] 프롬프트 빌드: {time.time() - t1:.3f}s")

        # 3. 스트리밍으로 응답 생성 (LLM 1번만 호출)
        t2 = time.time()
        first_token = True
        full_response = ""
        async for chunk in self.streaming_llm.astream(prompt):
            if chunk.content:
                if first_token:
                    print(f"[TIMING] LLM 첫 토큰: {time.time() - t2:.3f}s")
                    first_token = False
                full_response += chunk.content
                yield chunk.content
        print(f"[TIMING] LLM 전체 응답: {time.time() - t2:.3f}s")

        # 4. 상태 업데이트 (LLM 재호출 없이)
        # 스트리밍에서는 emotion 추출 불가, 기본값 사용
        t3 = time.time()
        await self._update_state_after_response(
            state, context, full_response, 0  # neutral
        )
        print(f"[TIMING] 상태 업데이트: {time.time() - t3:.3f}s")
        print(f"[TIMING] === 총 소요시간: {time.time() - total_start:.3f}s ===")


# 싱글톤 인스턴스 (앱 전체에서 하나만 사용)
heroine_agent = HeroineAgent()
