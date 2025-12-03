"""
대현자 NPC Agent

대현자 사트라(Satra)와의 대화를 처리합니다.
세계관과 시나리오 정보를 제공하는 역할입니다.

주요 기능:
1. 시나리오 레벨(scenarioLevel) 기반 정보 공개 관리
2. 레벨에 따른 태도 변화 (거리감 -> 친근함)
3. 허용된 정보만 제공, 금지된 정보는 회피

스트리밍/비스트리밍 동일 응답:
- 둘 다 동일한 컨텍스트(시나리오)를 사용
- 둘 다 동일한 프롬프트로 응답 생성
- LLM 호출은 1번만

저장 위치:
- Redis: 세션 상태 (scenarioLevel, emotion, conversation_buffer)
- Mem0: User-NPC 장기 기억 (대화 내용)
"""

import json
import yaml
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Tuple
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import START, END, StateGraph

from agents.npc.npc_state import SageState
from agents.npc.base_npc_agent import BaseNPCAgent
from agents.npc.emotion_mapper import sage_emotion_to_int
from db.redis_manager import redis_manager
from db.mem0_manager import mem0_manager
from services.sage_scenario_service import sage_scenario_service


# ============================================
# 페르소나 데이터 로드
# ============================================

# 페르소나 YAML 파일 경로
PERSONA_PATH = (
    Path(__file__).parent.parent.parent
    / "prompts"
    / "prompt_type"
    / "npc"
    / "sage_persona.yaml"
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
        "satra": {
            "name": "사트라",
            "basic_info": {
                "apparent_age": "20대 중반 외모",
                "appearance": "은발, 붉은 눈, 하얀 피부",
                "role": "셀레파이스의 대현자",
            },
            "speech_style": {"tone": "기품 있는 하대", "mentor_address": "멘토"},
            "level_attitudes": {
                "low": {
                    "description": "거리감 있음, 수수께끼처럼 말함",
                    "examples": ["흠, 그건 아직 알 필요 없어."],
                },
                "mid": {
                    "description": "조금 친밀해짐",
                    "examples": ["그건... 때가 되면 알려줄게."],
                },
                "high": {
                    "description": "친근함, 솔직해짐",
                    "examples": ["좋아, 솔직히 말해볼게."],
                },
            },
            "personality": {"surface": ["알 수 없는 미소", "기품 있음", "지혜로움"]},
            "info_rules": {
                "level_1": {
                    "allowed": ["기초 세계관", "길드 정보"],
                    "forbidden": ["플레이어 과거", "히로인 비밀"],
                    "evasion": "아직 때가 아니야.",
                }
            },
        }
    }


# 페르소나 데이터 로드 (모듈 로드시 1회)
PERSONA_DATA = load_persona_data()


class SageAgent(BaseNPCAgent):
    """대현자 NPC Agent

    대현자 사트라와의 대화를 처리합니다.
    시나리오 레벨에 따라 공개할 수 있는 정보가 달라집니다.

    스트리밍과 비스트리밍 모두 동일한 응답을 생성합니다.

    사용 예시:
        agent = SageAgent()

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
        """대현자 초기 세션 생성

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID (대현자는 0)

        Returns:
            초기 세션 딕셔너리
        """
        return {
            "player_id": player_id,
            "npc_id": npc_id,
            "npc_type": "sage",
            "conversation_buffer": [],  # 최근 대화 목록
            "short_term_summary": "",  # 단기 요약
            "state": {
                "scenarioLevel": 1,  # 시나리오 레벨 (1-10)
                "emotion": "neutral",  # 현재 감정
            },
        }

    def _get_attitude(self, scenario_level: int) -> str:
        """레벨에 따른 태도 설명

        Args:
            scenario_level: 시나리오 레벨 (1-10)

        Returns:
            태도 설명 문자열
        """
        if scenario_level <= 3:
            return "거리감 있음, 수수께끼처럼 말함"
        elif scenario_level <= 6:
            return "조금 친밀해짐, 정보 제공 늘어남"
        return "친근함, 솔직해짐"

    def _get_attitude_key(self, scenario_level: int) -> str:
        """레벨에 따른 태도 키

        Args:
            scenario_level: 시나리오 레벨 (1-10)

        Returns:
            태도 키 (low/mid/high)
        """
        if scenario_level <= 3:
            return "low"
        elif scenario_level <= 6:
            return "mid"
        return "high"

    def _format_persona(self, scenario_level: int) -> str:
        """페르소나를 프롬프트용 문자열로 포맷

        Args:
            scenario_level: 시나리오 레벨

        Returns:
            포맷된 문자열
        """
        persona = PERSONA_DATA.get("satra", {})
        attitude_key = self._get_attitude_key(scenario_level)

        # 기본 정보
        basic = persona.get("basic_info", {})
        speech = persona.get("speech_style", {})
        level_attitudes = persona.get("level_attitudes", {})
        attitude_data = level_attitudes.get(attitude_key, {})

        lines = [
            f"이름: {persona.get('name', '사트라')}",
            f"외형: {basic.get('apparent_age', '')}, {basic.get('appearance', '')}",
            f"역할: {basic.get('role', '대현자')}",
            "",
            "[말투 특징]",
            f"- 기본: {speech.get('tone', '기품 있는 하대')}",
            f"- 호칭: {speech.get('mentor_address', '멘토')}",
            "",
            f"[현재 레벨 {scenario_level} 태도]",
            f"스타일: {attitude_data.get('description', '')}",
            "예시 대사:",
        ]

        for example in attitude_data.get("examples", [])[:3]:
            lines.append(f"  - {example}")

        # 성격 특성
        personality = persona.get("personality", {})
        lines.append("")
        lines.append("[성격]")
        for trait in personality.get("surface", [])[:3]:
            lines.append(f"  - {trait}")

        return "\n".join(lines)

    def _get_info_rules(self, scenario_level: int) -> dict:
        """현재 레벨의 정보 공개 규칙

        Args:
            scenario_level: 시나리오 레벨

        Returns:
            정보 규칙 딕셔너리 (allowed, forbidden, evasion)
        """
        persona = PERSONA_DATA.get("satra", {})
        info_rules = persona.get("info_rules", {})
        level_key = f"level_{scenario_level}"
        return info_rules.get(level_key, info_rules.get("level_1", {}))

    # ============================================
    # 컨텍스트 준비 메서드 (스트리밍/비스트리밍 공통)
    # ============================================

    async def _classify_intent(self, state: SageState) -> str:
        """의도 분류

        사용자 메시지의 의도를 분류합니다:
        - general: 일반 대화
        - worldview_inquiry: 세계관 질문 (시나리오 DB 검색)
        - personal_inquiry: 대현자 개인 질문
        - player_inquiry: 플레이어 관련 질문 (시나리오 DB 검색)

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
- general: 일상 대화, 안부, 농담
- worldview_inquiry: 세계관, 국가, 종족, 던전, 디멘시움 등에 대한 질문
- personal_inquiry: 사트라 본인에 대한 질문 (정체, 나이, 능력 등)
- player_inquiry: 플레이어(멘토) 본인에 대한 질문 (과거, 능력 등)

반드시 general, worldview_inquiry, personal_inquiry, player_inquiry 중 하나만 출력하세요."""

        response = await self.intent_llm.ainvoke(prompt)
        intent = response.content.strip().lower()

        # 유효하지 않으면 기본값
        valid_intents = [
            "general",
            "worldview_inquiry",
            "personal_inquiry",
            "player_inquiry",
        ]
        if intent not in valid_intents:
            intent = "general"

        return intent

    async def _retrieve_scenario(self, state: SageState) -> str:
        """시나리오 DB 검색

        현재 시나리오 레벨 이하로 해금된 시나리오를 검색합니다.

        Args:
            state: 현재 상태

        Returns:
            검색된 시나리오 텍스트
        """
        user_message = state["messages"][-1].content
        scenario_level = state.get("scenarioLevel", 1)

        scenarios = sage_scenario_service.search_scenarios(
            query=user_message, max_scenario_level=scenario_level, limit=2
        )

        if scenarios:
            return "\n\n".join([s["content"] for s in scenarios])
        return "해금된 정보 없음"

    async def _prepare_context(self, state: SageState) -> Dict[str, Any]:
        """컨텍스트 준비 (스트리밍/비스트리밍 공통)

        LLM 호출 전에 필요한 모든 정보를 준비합니다:
        1. 의도 분류
        2. 의도에 따른 검색 (시나리오)

        Args:
            state: 현재 상태

        Returns:
            컨텍스트 딕셔너리 (intent, unlocked_scenarios)
        """
        # 1. 의도 분류
        intent = await self._classify_intent(state)

        # 2. 의도에 따른 검색
        unlocked_scenarios = "없음"

        if intent in ["worldview_inquiry", "player_inquiry"]:
            # 세계관 또는 플레이어 질문 -> 시나리오 DB 검색
            unlocked_scenarios = await self._retrieve_scenario(state)

        return {"intent": intent, "unlocked_scenarios": unlocked_scenarios}

    def _build_full_prompt(
        self, state: SageState, context: Dict[str, Any], for_streaming: bool = False
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
        scenario_level = state.get("scenarioLevel", 1)
        info_rules = self._get_info_rules(scenario_level)

        # 금지 정보와 회피 응답
        forbidden_info = info_rules.get("forbidden", [])
        evasion_response = info_rules.get("evasion", "아직 때가 아니야.")

        # 출력 형식 (스트리밍은 텍스트만, 비스트리밍은 JSON)
        if for_streaming:
            output_format = "캐릭터로서 자연스럽게 대답하세요. 대화만 출력하세요."
        else:
            output_format = """[출력 형식]
반드시 아래 JSON 형식으로 출력하세요:
{
    "thought": "(내면의 생각 - 플레이어에게 보이지 않음)",
    "text": "(실제 대화 내용)",
    "emotion": "neutral|joy|fun|sorrow|angry|surprise|mysterious",
    "info_revealed": true 또는 false
}"""

        prompt = f"""당신은 대현자 사트라(Satra)입니다.

[현재 상태]
- 시나리오 레벨(ScenarioLevel): {scenario_level}
- 태도: {self._get_attitude(scenario_level)}

[페르소나]
{self._format_persona(scenario_level)}

[정보 공개 규칙]
- 허용된 정보: {', '.join(info_rules.get('allowed', []))}
- 금지된 정보: {', '.join(forbidden_info) if forbidden_info else '없음'}
- 금지 정보 질문시 회피: "{evasion_response}"

[페르소나 규칙]
- 해금되지 않은 정보는 절대 말하지 않습니다.
- 기본적으로 하대하며 기품 있는 어조를 유지합니다.
- 감정을 크게 드러내지 않고 항상 알 수 없는 미소를 띱니다.
- 거짓말은 하지 않지만, 말하지 않을 수는 있습니다.

[해금된 세계관 정보]
{context.get('unlocked_scenarios', '없음')}

[최근 대화 기록]
{self.format_conversation_history(state.get('conversation_buffer', []))}

[플레이어 메시지]
{state['messages'][-1].content}

{output_format}"""

        return prompt

    async def _update_state_after_response(
        self,
        state: SageState,
        context: Dict[str, Any],
        response_text: str,
        emotion_int: int = 0,
        info_revealed: bool = False,
    ) -> Dict[str, Any]:
        """응답 후 상태 업데이트 (LLM 재호출 없이)

        스트리밍/비스트리밍 모두 이 메서드로 상태를 업데이트합니다.

        저장 위치:
        - Redis: 세션 상태 (emotion, conversation_buffer)
        - Mem0: User-NPC 대화 기억

        Args:
            state: 현재 상태
            context: 컨텍스트
            response_text: 생성된 응답 텍스트
            emotion_int: 감정 정수값 (기본값 0=neutral)
            info_revealed: 정보 공개 여부

        Returns:
            업데이트된 상태 값들
        """
        player_id = state["player_id"]
        npc_id = state["npc_id"]

        # Redis 세션 업데이트
        session = redis_manager.load_session(player_id, npc_id)
        if session:
            # 상태 업데이트
            session["state"]["emotion"] = emotion_int

            # 대화 버퍼에 추가
            session["conversation_buffer"].append(
                {"role": "user", "content": state["messages"][-1].content}
            )
            session["conversation_buffer"].append(
                {"role": "assistant", "content": response_text}
            )

            # 세션 저장
            redis_manager.save_session(player_id, npc_id, session)

        # Mem0에 대화 저장 (User-NPC 장기 기억)
        user_msg = state["messages"][-1].content
        mem0_manager.add_memory(
            player_id, npc_id, f"플레이어: {user_msg}\n사트라: {response_text}"
        )

        return {
            "response_text": response_text,
            "emotion": emotion_int,
            "info_revealed": info_revealed,
        }

    # ============================================
    # LangGraph 빌드 (비스트리밍용)
    # ============================================

    def _build_graph(self) -> StateGraph:
        """LangGraph 빌드

        노드 흐름:
        START -> router
        router -> (분기)
            - general -> generate
            - worldview_inquiry -> scenario_retrieve -> generate
            - personal_inquiry -> generate
            - player_inquiry -> scenario_retrieve -> generate
        generate -> post_process -> END

        Returns:
            컴파일된 StateGraph
        """
        graph = StateGraph(SageState)

        # 노드 추가
        graph.add_node("router", self._router_node)
        graph.add_node("scenario_retrieve", self._scenario_retrieve_node)
        graph.add_node("generate", self._generate_node)
        graph.add_node("post_process", self._post_process_node)

        # 엣지 추가
        graph.add_edge(START, "router")

        # 조건부 분기
        graph.add_conditional_edges(
            "router",
            self._route_by_intent,
            {
                "general": "generate",
                "worldview_inquiry": "scenario_retrieve",
                "personal_inquiry": "generate",
                "player_inquiry": "scenario_retrieve",
            },
        )

        graph.add_edge("scenario_retrieve", "generate")
        graph.add_edge("generate", "post_process")
        graph.add_edge("post_process", END)

        return graph.compile()

    # ============================================
    # LangGraph 노드 구현
    # ============================================

    async def _router_node(self, state: SageState) -> dict:
        """의도 분류 노드"""
        intent = await self._classify_intent(state)
        return {"intent": intent}

    def _route_by_intent(self, state: SageState) -> str:
        """의도에 따라 라우팅"""
        return state.get("intent", "general")

    async def _scenario_retrieve_node(self, state: SageState) -> dict:
        """시나리오 DB 검색 노드"""
        scenarios = await self._retrieve_scenario(state)
        return {"unlocked_scenarios": scenarios}

    async def _generate_node(self, state: SageState) -> dict:
        """응답 생성 노드"""
        # 컨텍스트 구성
        context = {"unlocked_scenarios": state.get("unlocked_scenarios", "없음")}

        # 프롬프트 생성 및 LLM 호출
        prompt = self._build_full_prompt(state, context, for_streaming=False)
        response = await self.llm.ainvoke(prompt)

        # JSON 파싱
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            result = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            result = {
                "thought": "",
                "text": response.content,
                "emotion": "neutral",
                "info_revealed": False,
            }

        emotion_str = result.get("emotion", "neutral")
        return {
            "response_text": result.get("text", ""),
            "emotion": sage_emotion_to_int(emotion_str),
            "info_revealed": result.get("info_revealed", False),
        }

    async def _post_process_node(self, state: SageState) -> dict:
        """후처리 노드 - 상태 업데이트"""
        context = {}

        emotion_int = state.get("emotion", 0)
        await self._update_state_after_response(
            state,
            context,
            state.get("response_text", ""),
            emotion_int,
            state.get("info_revealed", False),
        )

        return {"info_revealed": state.get("info_revealed", False)}

    # ============================================
    # 공개 메서드
    # ============================================

    async def process_message(self, state: SageState) -> SageState:
        """메시지 처리 (비스트리밍)

        LangGraph 전체 파이프라인을 실행합니다.

        Args:
            state: 입력 상태

        Returns:
            처리 후 상태
        """
        result = await self.graph.ainvoke(state)
        return result

    async def generate_response_stream(self, state: SageState) -> AsyncIterator[str]:
        """스트리밍 응답 생성 (컨텍스트 포함)

        비스트리밍과 동일한 컨텍스트를 사용합니다.
        LLM은 1번만 호출됩니다.

        Args:
            state: 입력 상태

        Yields:
            응답 토큰
        """
        # 1. 컨텍스트 준비 (시나리오 검색)
        context = await self._prepare_context(state)

        # 2. 전체 프롬프트 생성 (비스트리밍과 동일한 컨텍스트)
        prompt = self._build_full_prompt(state, context, for_streaming=True)

        # 3. 스트리밍으로 응답 생성 (LLM 1번만 호출)
        full_response = ""
        async for chunk in self.streaming_llm.astream(prompt):
            if chunk.content:
                full_response += chunk.content
                yield chunk.content

        # 4. 상태 업데이트 (LLM 재호출 없이)
        # 스트리밍에서는 emotion 추출 불가, 기본값 사용
        await self._update_state_after_response(
            state, context, full_response, 0, False  # 0=neutral
        )


# 싱글톤 인스턴스 (앱 전체에서 하나만 사용)
sage_agent = SageAgent()
