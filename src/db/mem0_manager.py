"""
Mem0 장기 기억 관리 (User-NPC 대화용)

이 모듈은 User와 NPC 사이의 대화 기억을 관리합니다.
Mem0 라이브러리를 사용하여 자동으로 중요한 정보를 추출하고 저장합니다.

Mem0란?
- 대화에서 중요한 정보를 자동으로 추출하여 저장하는 라이브러리
- 벡터 검색을 지원하여 관련 기억을 빠르게 찾을 수 있음

저장소 구분:
- User-NPC 대화: Mem0 (이 모듈)
- NPC-NPC 대화: agent_memory.py (직접 pgvector 사용)

사용 예시:
    # 기억 추가
    mem0_manager.add_memory(
        player_id=10001,
        npc_id=1,
        content="플레이어가 레티아에게 고양이를 좋아한다고 말함"
    )

    # 기억 검색
    results = mem0_manager.search_memory(
        player_id=10001,
        npc_id=1,
        query="고양이"
    )
"""

import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class Mem0Manager:
    """Mem0 장기 기억 관리 클래스

    플레이어와 NPC 사이의 대화 기억을 Mem0를 통해 관리합니다.

    초기화 모드:
    1. 클라우드 모드: MEM0_API_KEY가 있으면 Mem0 클라우드 사용
    2. 로컬 모드: API 키가 없으면 로컬 pgvector 사용

    user_id 형식: player_{player_id}_npc_{npc_id}
    이렇게 하면 각 플레이어-NPC 조합별로 기억이 분리됩니다.
    """

    def __init__(self):
        """초기화

        MEM0_API_KEY 환경변수가 있으면 클라우드 모드,
        없으면 로컬 pgvector 모드로 초기화합니다.
        """
        self.mem0_api_key = os.getenv("MEM0_API_KEY")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Mem0 클라이언트 초기화

        API 키 유무에 따라 클라우드/로컬 모드 결정
        """
        try:
            from mem0 import Memory

            # API 키가 있으면 클라우드 모드
            if self.mem0_api_key and self.mem0_api_key != "your_mem0_api_key_here":
                self.client = Memory(api_key=self.mem0_api_key)
                print("Mem0 클라우드 모드로 초기화됨")
            else:
                # 로컬 모드 (Supabase pgvector 사용)
                from db.config import CONNECTION_URL

                config = {
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "connection_string": CONNECTION_URL,
                            "collection_name": "npc_memories",
                            "embedding_model_dims": 1536,
                        },
                    },
                    "disable_telemetry": True,
                }

                try:
                    self.client = Memory.from_config(config)
                    print("Mem0 로컬 모드로 초기화됨 (pgvector)")
                except Exception as init_error:
                    # 마이그레이션 중복 에러 등은 무시하고 재시도
                    if "duplicate key" in str(init_error) or "already exists" in str(
                        init_error
                    ):
                        print(f"Mem0 마이그레이션 이미 완료됨, 연결 재시도...")
                        # 테이블이 이미 있으므로 다시 연결 시도
                        self.client = Memory.from_config(config)
                    else:
                        raise init_error

        except ImportError:
            # mem0ai 라이브러리가 없는 경우
            print(
                "경고: mem0ai 라이브러리가 설치되지 않았습니다. pip install mem0ai 실행 필요"
            )
            self.client = None
        except Exception as e:
            print(f"Mem0 초기화 실패: {e}")
            self.client = None

    def _get_user_id(self, player_id: int, npc_id: int) -> str:
        """Mem0 user_id 생성

        플레이어-NPC 조합별로 고유한 ID를 생성합니다.

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID

        Returns:
            user_id 문자열 (예: player_10001_npc_1)
        """
        return f"player_{player_id}_npc_{npc_id}"

    def add_memory(
        self, player_id: int, npc_id: int, content: str, metadata: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """기억 추가

        대화 내용을 Mem0에 저장합니다.
        Mem0가 자동으로 중요한 정보를 추출하여 저장합니다.

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            content: 저장할 대화 내용
            metadata: 추가 메타데이터 (선택)

        Returns:
            저장 결과 또는 None (실패시)
        """
        # 클라이언트가 없으면 종료
        if self.client is None:
            return None

        user_id = self._get_user_id(player_id, npc_id)

        try:
            # Mem0에 추가
            result = self.client.add(content, user_id=user_id, metadata=metadata or {})
            return result
        except Exception as e:
            print(f"Mem0 저장 실패 (무시됨): {e}")
            return None

    def search_memory(
        self, player_id: int, npc_id: int, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """기억 검색

        검색어와 관련된 기억을 벡터 검색으로 찾습니다.

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID
            query: 검색어
            limit: 최대 결과 수 (기본값 5)

        Returns:
            검색된 기억 리스트
        """
        if self.client is None:
            return []

        user_id = self._get_user_id(player_id, npc_id)

        try:
            # Mem0 검색
            results = self.client.search(query, user_id=user_id, limit=limit)

            # 결과 형식 통일 (dict 또는 list)
            if isinstance(results, dict):
                return results.get("results", [])
            return results
        except Exception as e:
            print(f"Mem0 검색 실패 (무시됨): {e}")
            return []

    def get_all_memories(self, player_id: int, npc_id: int) -> List[Dict[str, Any]]:
        """모든 기억 조회

        해당 플레이어-NPC 조합의 모든 기억을 가져옵니다.

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID

        Returns:
            기억 리스트
        """
        if self.client is None:
            return []

        user_id = self._get_user_id(player_id, npc_id)

        try:
            results = self.client.get_all(user_id=user_id)

            if isinstance(results, dict):
                return results.get("results", [])
            return results
        except Exception as e:
            print(f"Mem0 조회 실패 (무시됨): {e}")
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """특정 기억 삭제

        Args:
            memory_id: 삭제할 기억 ID

        Returns:
            삭제 성공 여부
        """
        if self.client is None:
            return False

        try:
            self.client.delete(memory_id)
            return True
        except Exception:
            return False

    def delete_all_memories(self, player_id: int, npc_id: int) -> bool:
        """특정 플레이어-NPC의 모든 기억 삭제

        Args:
            player_id: 플레이어 ID
            npc_id: NPC ID

        Returns:
            삭제 성공 여부
        """
        if self.client is None:
            return False

        user_id = self._get_user_id(player_id, npc_id)

        try:
            self.client.delete_all(user_id=user_id)
            return True
        except Exception:
            return False


# 싱글톤 인스턴스 (앱 전체에서 하나만 사용)
mem0_manager = Mem0Manager()
