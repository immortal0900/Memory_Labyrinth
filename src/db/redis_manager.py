"""
Redis 세션 및 길드 상태 관리

이 모듈은 다음을 관리합니다:
1. 플레이어-NPC 대화 세션 (conversation_buffer, 상태 등)
2. 길드 진입/퇴장 상태
3. NPC간 백그라운드 대화 상태

Redis 키 구조:
- session:{player_id}:{npc_id} - 대화 세션
- guild:{player_id} - 길드 진입 상태
- npc_conv:{player_id} - 진행 중인 NPC간 대화
- npc_npc_session:{player_id}:{min_npc_id}:{max_npc_id} - NPC-NPC 세션(쌍 단위)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis
from dotenv import load_dotenv

load_dotenv()

# Redis 연결 URL (기본값: 로컬 Redis)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 세션 유효 시간 (24시간)
SESSION_TTL = 3600 * 24


class RedisManager:
    """Redis 세션 및 상태 관리 클래스

    주요 기능:
    1. 대화 세션 관리 (저장/로드/업데이트/삭제)
    2. 길드 진입/퇴장 상태 관리
    3. NPC간 대화 상태 관리

    사용 예시:
        manager = RedisManager()

        # 세션 저장
        session = {"player_id": 1, "npc_id": 1, "state": {...}}
        manager.save_session(1, 1, session)

        # 세션 로드
        session = manager.load_session(1, 1)

        # 길드 진입
        manager.enter_guild(1)
    """

    def __init__(self):
        """Redis 클라이언트 초기화"""
        # decode_responses=True: 바이트 대신 문자열로 반환
        self.client = redis.from_url(REDIS_URL, decode_responses=True)

    # ============================================
    # 키 생성 헬퍼 메서드
    # ============================================

    def _get_session_key(self, player_id: str, npc_id: int) -> str:
        """대화 세션 키 생성

        형식: session:{player_id}:{npc_id}
        """
        return f"session:{player_id}:{npc_id}"

    def _get_guild_key(self, player_id: str) -> str:
        """길드 상태 키 생성

        형식: guild:{player_id}
        """
        return f"guild:{player_id}"

    def _get_npc_conversation_key(self, player_id: str) -> str:
        """진행 중인 NPC 대화 키 생성

        형식: npc_conv:{player_id}
        """
        return f"npc_conv:{player_id}"

    def _get_npc_npc_session_key(
        self, player_id: str, npc1_id: int, npc2_id: int
    ) -> str:
        """NPC-NPC 세션 키 생성

        (A,B) 쌍은 항상 (min,max)로 정규화합니다.

        형식: npc_npc_session:{player_id}:{min_npc_id}:{max_npc_id}
        """
        min_id = npc1_id if npc1_id < npc2_id else npc2_id
        max_id = npc2_id if npc1_id < npc2_id else npc1_id
        return f"npc_npc_session:{player_id}:{min_id}:{max_id}"

    # ============================================
    # 세션 관리 메서드
    # ============================================

    def load_session(self, player_id: str, npc_id: int) -> Optional[Dict[str, Any]]:
        """Redis에서 세션 로드

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID

        Returns:
            세션 딕셔너리 또는 None (없으면)
        """
        key = self._get_session_key(player_id, npc_id)
        data = self.client.get(key)

        if data:
            return json.loads(data)
        return None

    def save_session(
        self, player_id: str, npc_id: int, session_data: Dict[str, Any]
    ) -> None:
        """Redis에 세션 저장

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            session_data: 저장할 세션 데이터
        """
        key = self._get_session_key(player_id, npc_id)

        # 마지막 활성 시간 업데이트
        session_data["last_active_at"] = datetime.now().isoformat()

        # TTL과 함께 저장 (24시간 후 자동 삭제)
        self.client.setex(
            key, SESSION_TTL, json.dumps(session_data, ensure_ascii=False)
        )

    def update_session(
        self, player_id: str, npc_id: int, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """세션 부분 업데이트

        기존 세션에 updates 내용을 병합합니다.

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            updates: 업데이트할 필드들

        Returns:
            업데이트된 세션
        """
        session = self.load_session(player_id, npc_id)

        # 세션이 없으면 새로 생성
        if session is None:
            session = self._create_empty_session(player_id, npc_id)

        # updates 내용 병합
        session.update(updates)

        # 저장
        self.save_session(player_id, npc_id, session)
        return session

    def delete_session(self, player_id: str, npc_id: int) -> None:
        """세션 삭제

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
        """
        key = self._get_session_key(player_id, npc_id)
        self.client.delete(key)

    def _create_empty_session(self, player_id: str, npc_id: int) -> Dict[str, Any]:
        """빈 세션 생성 (기본값)

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID

        Returns:
            기본 세션 딕셔너리
        """
        return {
            "player_id": player_id,
            "npc_id": npc_id,
            "conversation_buffer": [],  # 최근 대화 목록
            "short_term_summary": "",  # 단기 요약
            "summary_list": [],  # 요약 목록 (checkpoint용)
            "turn_count": 0,  # 대화 턴 카운트 (요약 생성 조건용)
            "last_summary_at": None,  # 마지막 요약 생성 시간
            "state": {
                "affection": 0,  # 호감도
                "sanity": 100,  # 정신력
                "memoryProgress": 0,  # 기억 진척도
                "emotion": "neutral",  # 현재 감정
            },
            "last_active_at": datetime.now().isoformat(),
            "last_chat_at": None,  # 마지막 대화 시간 (시간 차이 계산용)
        }

    def is_session_expired(self, session_data: Dict[str, Any], hours: int = 1) -> bool:
        """세션 만료 여부 확인

        Args:
            session_data: 세션 데이터
            hours: 만료 기준 시간 (기본 1시간)

        Returns:
            만료 여부 (True면 만료됨)
        """
        last_active = session_data.get("last_active_at")

        if not last_active:
            return True

        last_active_dt = datetime.fromisoformat(last_active)
        return datetime.now() - last_active_dt > timedelta(hours=hours)

    def add_conversation(
        self, player_id: str, npc_id: int, role: str, content: str
    ) -> None:
        """대화 내용 추가

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            role: 역할 ("user" 또는 "assistant")
            content: 대화 내용
        """
        session = self.load_session(player_id, npc_id)

        if session is None:
            session = self._create_empty_session(player_id, npc_id)

        # 대화 추가
        session["conversation_buffer"].append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )

        # 20턴 초과시 가장 오래된 것 제거 (최근 20개만 유지)
        if len(session["conversation_buffer"]) > 20:
            session["conversation_buffer"] = session["conversation_buffer"][-20:]

        self.save_session(player_id, npc_id, session)

    # ============================================
    # 길드 상태 관리
    # ============================================

    def enter_guild(self, player_id: str) -> None:
        """길드 진입 상태 설정

        플레이어가 길드에 들어왔을 때 호출합니다.
        이후 백그라운드에서 NPC간 대화가 자동으로 생성됩니다.

        Args:
            player_id: 플레이어 ID
        """
        key = self._get_guild_key(player_id)

        # 길드 상태 저장
        guild_data = {"in_guild": True, "entered_at": datetime.now().isoformat()}
        self.client.set(key, json.dumps(guild_data))

    def leave_guild(self, player_id: str) -> None:
        """길드 퇴장 상태 설정

        플레이어가 길드에서 나갔을 때 호출합니다.
        진행 중인 NPC 대화도 함께 중단됩니다.

        Args:
            player_id: 플레이어 ID
        """
        key = self._get_guild_key(player_id)
        self.client.delete(key)

        # 진행 중인 NPC 대화도 중단
        self.stop_npc_conversation(player_id)

    def is_in_guild(self, player_id: str) -> bool:
        """길드 내 여부 확인

        Args:
            player_id: 플레이어 ID

        Returns:
            길드 내 여부 (True면 길드 안에 있음)
        """
        key = self._get_guild_key(player_id)
        data = self.client.get(key)

        if data:
            guild_data = json.loads(data)
            return guild_data.get("in_guild", False)

        return False

    # ============================================
    # NPC간 대화 상태 관리
    # ============================================

    def start_npc_conversation(
        self, player_id: str, npc1_id: int, npc2_id: int
    ) -> None:
        """NPC간 대화 시작 등록

        두 NPC가 대화를 시작할 때 호출합니다.
        User가 히로인에게 말 걸면 이 상태를 확인해서 인터럽트합니다.

        Args:
            player_id: 플레이어 ID
            npc1_id: 첫 번째 NPC ID
            npc2_id: 두 번째 NPC ID
        """
        key = self._get_npc_conversation_key(player_id)

        conv_data = {
            "active": True,
            "npc1_id": npc1_id,
            "npc2_id": npc2_id,
            "started_at": datetime.now().isoformat(),
        }
        self.client.set(key, json.dumps(conv_data))

    def stop_npc_conversation(self, player_id: str) -> Optional[Dict[str, Any]]:
        """NPC간 대화 중단

        Args:
            player_id: 플레이어 ID

        Returns:
            중단된 대화 정보 (없었으면 None)
        """
        key = self._get_npc_conversation_key(player_id)

        # 기존 데이터 읽기
        data = self.client.get(key)

        # 키 삭제
        self.client.delete(key)

        if data:
            return json.loads(data)
        return None

    def get_active_npc_conversation(self, player_id: str) -> Optional[Dict[str, Any]]:
        """현재 진행 중인 NPC 대화 정보 조회

        Args:
            player_id: 플레이어 ID

        Returns:
            대화 정보 딕셔너리 또는 None
        """
        key = self._get_npc_conversation_key(player_id)
        data = self.client.get(key)

        if data:
            return json.loads(data)
        return None

    def is_heroine_in_conversation(self, player_id: str, heroine_id: int) -> bool:
        """특정 히로인이 NPC 대화 중인지 확인

        User가 히로인에게 말 걸기 전에 확인합니다.
        대화 중이면 인터럽트가 필요합니다.

        Args:
            player_id: 플레이어 ID
            heroine_id: 확인할 히로인 ID

        Returns:
            대화 중 여부 (True면 현재 NPC 대화 중)
        """
        conv = self.get_active_npc_conversation(player_id)

        if conv and conv.get("active"):
            # npc1_id 또는 npc2_id에 해당 히로인이 있는지 확인
            return heroine_id in [conv.get("npc1_id"), conv.get("npc2_id")]

        return False

    # ============================================
    # NPC-NPC 세션 관리 (쌍 단위)
    # ============================================

    def load_npc_npc_session(
        self, player_id: str, npc1_id: int, npc2_id: int
    ) -> Optional[Dict[str, Any]]:
        """NPC-NPC 세션 로드

        Args:
            player_id: 플레이어 ID
            npc1_id: 첫 번째 NPC ID
            npc2_id: 두 번째 NPC ID

        Returns:
            세션 딕셔너리 또는 None
        """
        key = self._get_npc_npc_session_key(player_id, npc1_id, npc2_id)
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def save_npc_npc_session(
        self, player_id: str, npc1_id: int, npc2_id: int, session_data: Dict[str, Any]
    ) -> None:
        """NPC-NPC 세션 저장

        Args:
            player_id: 플레이어 ID
            npc1_id: 첫 번째 NPC ID
            npc2_id: 두 번째 NPC ID
            session_data: 저장할 세션 데이터
        """
        key = self._get_npc_npc_session_key(player_id, npc1_id, npc2_id)
        session_data["last_active_at"] = datetime.now().isoformat()
        self.client.setex(
            key, SESSION_TTL, json.dumps(session_data, ensure_ascii=False)
        )

    def truncate_npc_npc_session(
        self, player_id: str, npc1_id: int, npc2_id: int, interrupted_turn: int
    ) -> Optional[Dict[str, Any]]:
        """NPC-NPC 세션을 interrupted_turn 까지만 남기고 자르기

        Args:
            player_id: 플레이어 ID
            npc1_id: 첫 번째 NPC ID
            npc2_id: 두 번째 NPC ID
            interrupted_turn: 유효 턴 (이 턴까지)

        Returns:
            잘린 세션 또는 None
        """
        session = self.load_npc_npc_session(player_id, npc1_id, npc2_id)
        if session is None:
            return None

        buffer = session.get("conversation_buffer", [])
        session["conversation_buffer"] = buffer[:interrupted_turn]
        session["interrupted_turn"] = interrupted_turn
        session["turn_count"] = len(session.get("conversation_buffer", []))

        self.save_npc_npc_session(player_id, npc1_id, npc2_id, session)
        return session


# 싱글톤 인스턴스 (앱 전체에서 하나만 사용)
redis_manager = RedisManager()
