"""
NPC API 라우터

언리얼 엔진과 NPC 시스템 간의 통신 프로토콜입니다.

스트리밍/비스트리밍 동일 응답:
- 둘 다 동일한 컨텍스트(기억/시나리오)를 사용
- 둘 다 동일한 프롬프트로 응답 생성
- LLM 호출은 1번만 (스트리밍에서 중복 호출 제거됨)
"""

import asyncio
import random
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage

from db.redis_manager import redis_manager
from db.session_checkpoint_manager import session_checkpoint_manager
from agents.npc.heroine_agent import heroine_agent
from agents.npc.sage_agent import sage_agent
from agents.npc.heroine_heroine_agent import heroine_heroine_agent


router = APIRouter(prefix="/api/npc", tags=["NPC"])

# 백그라운드 NPC 대화 태스크 관리
_background_tasks: Dict[int, asyncio.Task] = {}


# ============================================
# Request/Response 모델
# ============================================


class HeroineData(BaseModel):
    heroineId: int
    affection: int
    memoryProgress: int
    sanity: int


class LoginRequest(BaseModel):
    playerId: int
    scenarioLevel: int
    heroines: List[HeroineData]


class LoginResponse(BaseModel):
    success: bool
    message: str


class ChatRequest(BaseModel):
    playerId: int
    heroineId: int
    text: str


class ChatResponse(BaseModel):
    text: str
    emotion: int
    affection: int
    sanity: int
    memoryProgress: int


class SageChatRequest(BaseModel):
    playerId: int
    text: str


class SageChatResponse(BaseModel):
    text: str
    emotion: int
    scenarioLevel: int
    infoRevealed: bool


class HeroineConversationRequest(BaseModel):
    heroine1Id: int
    heroine2Id: int
    situation: Optional[str] = None
    turnCount: Optional[int] = 10


class GuildRequest(BaseModel):
    playerId: int


class GuildResponse(BaseModel):
    success: bool
    message: str
    activeConversation: Optional[Dict[str, Any]] = None


# ============================================
# 백그라운드 NPC 대화 태스크
# ============================================


async def background_npc_conversation_loop(player_id: int):
    """백그라운드에서 주기적으로 NPC간 대화 생성"""
    heroine_ids = [1, 2, 3]

    while redis_manager.is_in_guild(player_id):
        active_conv = redis_manager.get_active_npc_conversation(player_id)

        if not active_conv:
            pair = random.sample(heroine_ids, 2)
            npc1_id = pair[0]
            npc2_id = pair[1]

            redis_manager.start_npc_conversation(player_id, npc1_id, npc2_id)

            try:
                await heroine_heroine_agent.generate_and_save_conversation(
                    heroine1_id=npc1_id, heroine2_id=npc2_id, turn_count=10
                )
            except Exception as e:
                print(f"Background NPC conversation error: {e}")
            finally:
                if redis_manager.is_in_guild(player_id):
                    redis_manager.stop_npc_conversation(player_id)

        await asyncio.sleep(random.randint(30, 60))

    if player_id in _background_tasks:
        del _background_tasks[player_id]


# ============================================
# 로그인/세션 엔드포인트
# ============================================


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """게임 로그인시 세션 초기화 및 checkpoint 복원"""
    player_id = request.playerId
    scenario_level = request.scenarioLevel

    for heroine in request.heroines:
        checkpoint = session_checkpoint_manager.load_checkpoints(
            player_id, heroine.heroineId
        )

        conversation_buffer = []
        for conv in checkpoint.get("conversations", []):
            conversation_buffer.append(
                {"role": "user", "content": conv.get("user", "")}
            )
            conversation_buffer.append(
                {"role": "assistant", "content": conv.get("npc", "")}
            )

        session = {
            "player_id": player_id,
            "npc_id": heroine.heroineId,
            "npc_type": "heroine",
            "conversation_buffer": conversation_buffer[-20:],
            "short_term_summary": "",
            "summary_list": checkpoint.get("summary_list", []),
            "turn_count": len(checkpoint.get("conversations", [])),
            "last_summary_at": None,
            "recent_used_keywords": [],
            "state": {
                "affection": heroine.affection,
                "sanity": heroine.sanity,
                "memoryProgress": heroine.memoryProgress,
                "emotion": 0,
            },
            "last_chat_at": checkpoint.get("last_chat_at"),
        }
        redis_manager.save_session(player_id, heroine.heroineId, session)

    sage_checkpoint = session_checkpoint_manager.load_checkpoints(player_id, 0)

    sage_conversation_buffer = []
    for conv in sage_checkpoint.get("conversations", []):
        sage_conversation_buffer.append(
            {"role": "user", "content": conv.get("user", "")}
        )
        sage_conversation_buffer.append(
            {"role": "assistant", "content": conv.get("npc", "")}
        )

    sage_session = {
        "player_id": player_id,
        "npc_id": 0,
        "npc_type": "sage",
        "conversation_buffer": sage_conversation_buffer[-20:],
        "short_term_summary": "",
        "summary_list": sage_checkpoint.get("summary_list", []),
        "turn_count": len(sage_checkpoint.get("conversations", [])),
        "last_summary_at": None,
        "state": {"scenarioLevel": scenario_level, "emotion": 0},
        "last_chat_at": sage_checkpoint.get("last_chat_at"),
    }
    redis_manager.save_session(player_id, 0, sage_session)

    return LoginResponse(success=True, message="세션 초기화 완료")


# ============================================
# 히로인 대화 엔드포인트
# ============================================


@router.post("/heroine/chat")
async def heroine_chat(request: ChatRequest):
    """히로인과 대화 (스트리밍)

    비스트리밍과 동일한 컨텍스트/응답 생성
    LLM 호출 1번만 (중복 호출 없음)
    """
    player_id = request.playerId
    heroine_id = request.heroineId
    user_message = request.text

    # 해당 히로인이 NPC 대화 중이면 인터럽트
    if redis_manager.is_heroine_in_conversation(player_id, heroine_id):
        redis_manager.stop_npc_conversation(player_id)

    # 세션 로드
    session = redis_manager.load_session(player_id, heroine_id)
    if session is None:
        session = heroine_agent._create_initial_session(player_id, heroine_id)
        redis_manager.save_session(player_id, heroine_id, session)

    # 상태 안전하게 가져오기
    session_state = session.get("state", {})

    # LangGraph 상태 구성
    state = {
        "player_id": player_id,
        "npc_id": heroine_id,
        "npc_type": "heroine",
        "messages": [HumanMessage(content=user_message)],
        "affection": session_state.get("affection", 0),
        "sanity": session_state.get("sanity", 100),
        "memoryProgress": session_state.get("memoryProgress", 0),
        "emotion": session_state.get("emotion", 0),
        "conversation_buffer": session.get("conversation_buffer", []),
        "short_term_summary": session.get("short_term_summary", ""),
        "recent_used_keywords": session.get("recent_used_keywords", []),
    }

    # 컨텍스트 준비 (기억/시나리오 검색)
    context = await heroine_agent._prepare_context(state)

    async def generate():
        """SSE 스트리밍 생성기"""
        # 전체 프롬프트 생성
        prompt = heroine_agent._build_full_prompt(state, context, for_streaming=True)

        # 스트리밍으로 응답 생성 (LLM 1번만 호출)
        full_response = ""
        async for chunk in heroine_agent.streaming_llm.astream(prompt):
            if chunk.content:
                full_response += chunk.content
                yield f"data: {chunk.content}\n\n"

        # 상태 업데이트 (LLM 재호출 없이)
        result = await heroine_agent._update_state_after_response(
            state, context, full_response, 0
        )

        # 최종 상태 전송
        final_data = {
            "type": "final",
            "affection": result["affection"],
            "sanity": result["sanity"],
            "memoryProgress": result["memoryProgress"],
            "emotion": result["emotion"],
        }
        yield f"data: {str(final_data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/heroine/chat/sync", response_model=ChatResponse)
async def heroine_chat_sync(request: ChatRequest, background_tasks: BackgroundTasks):
    """히로인과 대화 (비스트리밍)"""
    player_id = request.playerId
    heroine_id = request.heroineId
    user_message = request.text

    # 해당 히로인이 NPC 대화 중이면 인터럽트
    if redis_manager.is_heroine_in_conversation(player_id, heroine_id):
        redis_manager.stop_npc_conversation(player_id)

    # 세션 로드
    session = redis_manager.load_session(player_id, heroine_id)
    if session is None:
        session = heroine_agent._create_initial_session(player_id, heroine_id)
        redis_manager.save_session(player_id, heroine_id, session)

    # 상태 안전하게 가져오기
    session_state = session.get("state", {})

    # 상태 구성
    state = {
        "player_id": player_id,
        "npc_id": heroine_id,
        "npc_type": "heroine",
        "messages": [HumanMessage(content=user_message)],
        "affection": session_state.get("affection", 0),
        "sanity": session_state.get("sanity", 100),
        "memoryProgress": session_state.get("memoryProgress", 0),
        "emotion": session_state.get("emotion", 0),
        "conversation_buffer": session.get("conversation_buffer", []),
        "short_term_summary": session.get("short_term_summary", ""),
        "recent_used_keywords": session.get("recent_used_keywords", []),
    }

    # 메시지 처리 (LangGraph 전체 파이프라인)
    result = await heroine_agent.process_message(state)

    response_text = result.get("response_text", "")
    new_state = {
        "affection": result.get("affection", state["affection"]),
        "sanity": result.get("sanity", state["sanity"]),
        "memoryProgress": result.get("memoryProgress", state["memoryProgress"]),
        "emotion": result.get("emotion", 0),
    }

    background_tasks.add_task(
        session_checkpoint_manager.save_checkpoint_background,
        player_id,
        heroine_id,
        user_message,
        response_text,
        new_state,
    )

    return ChatResponse(
        text=response_text,
        emotion=new_state["emotion"],
        affection=new_state["affection"],
        sanity=new_state["sanity"],
        memoryProgress=new_state["memoryProgress"],
    )


# ============================================
# 대현자 대화 엔드포인트
# ============================================


@router.post("/sage/chat")
async def sage_chat(request: SageChatRequest):
    """대현자와 대화 (스트리밍)

    비스트리밍과 동일한 컨텍스트/응답 생성
    """
    player_id = request.playerId
    user_message = request.text
    npc_id = 0

    # 세션 로드
    session = redis_manager.load_session(player_id, npc_id)
    if session is None:
        session = sage_agent._create_initial_session(player_id, npc_id)
        redis_manager.save_session(player_id, npc_id, session)

    # 상태 안전하게 가져오기
    session_state = session.get("state", {})
    scenario_level = session_state.get("scenarioLevel", 1)

    # 상태 구성
    state = {
        "player_id": player_id,
        "npc_id": npc_id,
        "npc_type": "sage",
        "messages": [HumanMessage(content=user_message)],
        "scenarioLevel": scenario_level,
        "emotion": session_state.get("emotion", 0),
        "conversation_buffer": session.get("conversation_buffer", []),
        "short_term_summary": session.get("short_term_summary", ""),
    }

    # 컨텍스트 준비 (시나리오 검색)
    context = await sage_agent._prepare_context(state)

    async def generate():
        """SSE 스트리밍 생성기"""
        prompt = sage_agent._build_full_prompt(state, context, for_streaming=True)

        # 스트리밍으로 응답 생성 (LLM 1번만 호출)
        full_response = ""
        async for chunk in sage_agent.streaming_llm.astream(prompt):
            if chunk.content:
                full_response += chunk.content
                yield f"data: {chunk.content}\n\n"

        # 상태 업데이트 (LLM 재호출 없이)
        await sage_agent._update_state_after_response(
            state, context, full_response, 0, False  # 0 = neutral
        )

        final_data = {
            "type": "final",
            "scenarioLevel": scenario_level,
            "emotion": 0,  # neutral
            "infoRevealed": False,
        }
        yield f"data: {str(final_data)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/sage/chat/sync", response_model=SageChatResponse)
async def sage_chat_sync(request: SageChatRequest, background_tasks: BackgroundTasks):
    """대현자와 대화 (비스트리밍)"""
    player_id = request.playerId
    user_message = request.text
    npc_id = 0

    session = redis_manager.load_session(player_id, npc_id)
    if session is None:
        session = sage_agent._create_initial_session(player_id, npc_id)
        redis_manager.save_session(player_id, npc_id, session)

    # 상태 안전하게 가져오기
    session_state = session.get("state", {})
    scenario_level = session_state.get("scenarioLevel", 1)

    state = {
        "player_id": player_id,
        "npc_id": npc_id,
        "npc_type": "sage",
        "messages": [HumanMessage(content=user_message)],
        "scenarioLevel": scenario_level,
        "emotion": session_state.get("emotion", 0),
        "conversation_buffer": session.get("conversation_buffer", []),
        "short_term_summary": session.get("short_term_summary", ""),
    }

    result = await sage_agent.process_message(state)

    response_text = result.get("response_text", "")
    new_state = {
        "scenarioLevel": scenario_level,
        "emotion": result.get("emotion", 0),
    }

    background_tasks.add_task(
        session_checkpoint_manager.save_checkpoint_background,
        player_id,
        npc_id,
        user_message,
        response_text,
        new_state,
    )

    return SageChatResponse(
        text=response_text,
        emotion=new_state["emotion"],
        scenarioLevel=new_state["scenarioLevel"],
        infoRevealed=result.get("info_revealed", False),
    )


# ============================================
# 히로인간 대화 엔드포인트
# ============================================


@router.post("/heroine-conversation/generate")
async def generate_heroine_conversation(request: HeroineConversationRequest):
    """히로인간 대화 생성 (비스트리밍)"""
    result = await heroine_heroine_agent.generate_and_save_conversation(
        heroine1_id=request.heroine1Id,
        heroine2_id=request.heroine2Id,
        situation=request.situation,
        turn_count=request.turnCount or 10,
    )
    return result


@router.post("/heroine-conversation/stream")
async def generate_heroine_conversation_stream(request: HeroineConversationRequest):
    """히로인간 대화 생성 (스트리밍)

    비스트리밍과 동일하게 DB에 저장
    """

    async def generate():
        async for chunk in heroine_heroine_agent.generate_conversation_stream(
            heroine1_id=request.heroine1Id,
            heroine2_id=request.heroine2Id,
            situation=request.situation,
            turn_count=request.turnCount or 10,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/heroine-conversation")
async def get_heroine_conversations(
    heroine1_id: Optional[int] = None,
    heroine2_id: Optional[int] = None,
    limit: int = 10,
):
    """히로인간 대화 기록 조회"""
    conversations = heroine_heroine_agent.get_conversations(
        heroine1_id=heroine1_id, heroine2_id=heroine2_id, limit=limit
    )
    return {"conversations": conversations}


# ============================================
# 길드 시스템 엔드포인트
# ============================================


@router.post("/guild/enter", response_model=GuildResponse)
async def enter_guild(request: GuildRequest, background_tasks: BackgroundTasks):
    """길드 진입 - NPC간 백그라운드 대화 시작"""
    player_id = request.playerId

    if redis_manager.is_in_guild(player_id):
        return GuildResponse(
            success=True,
            message="이미 길드에 있습니다",
            activeConversation=redis_manager.get_active_npc_conversation(player_id),
        )

    redis_manager.enter_guild(player_id)

    if player_id not in _background_tasks:
        task = asyncio.create_task(background_npc_conversation_loop(player_id))
        _background_tasks[player_id] = task

    return GuildResponse(
        success=True, message="길드에 진입했습니다. NPC 대화가 시작됩니다."
    )


@router.post("/guild/leave", response_model=GuildResponse)
async def leave_guild(request: GuildRequest):
    """길드 퇴장 - NPC간 백그라운드 대화 중단"""
    player_id = request.playerId

    if not redis_manager.is_in_guild(player_id):
        return GuildResponse(success=True, message="길드에 있지 않습니다")

    active_conv = redis_manager.get_active_npc_conversation(player_id)
    redis_manager.leave_guild(player_id)

    if player_id in _background_tasks:
        _background_tasks[player_id].cancel()
        del _background_tasks[player_id]

    return GuildResponse(
        success=True,
        message="길드에서 퇴장했습니다. NPC 대화가 중단됩니다.",
        activeConversation=active_conv,
    )


@router.get("/guild/status/{player_id}")
async def get_guild_status(player_id: int):
    """길드 상태 조회"""
    return {
        "in_guild": redis_manager.is_in_guild(player_id),
        "active_conversation": redis_manager.get_active_npc_conversation(player_id),
        "has_background_task": player_id in _background_tasks,
    }


# ============================================
# 디버그 엔드포인트
# ============================================


@router.get("/session/{player_id}/{npc_id}")
async def get_session(player_id: int, npc_id: int):
    """세션 정보 조회 (디버그용)"""
    session = redis_manager.load_session(player_id, npc_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return session


@router.get("/npc-conversation/active/{player_id}")
async def get_active_npc_conversation(player_id: int):
    """현재 진행 중인 NPC 대화 조회"""
    conv = redis_manager.get_active_npc_conversation(player_id)
    if conv is None:
        return {"active": False, "conversation": None}
    return {"active": True, "conversation": conv}
