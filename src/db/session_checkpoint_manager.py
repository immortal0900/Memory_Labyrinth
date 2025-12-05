"""
Session Checkpoint Manager

매 대화 후 Redis 세션을 Supabase session_checkpoints 테이블에 저장합니다.
20턴 또는 1시간마다 요약을 생성합니다.

주요 기능:
1. save_checkpoint_background(): 백그라운드로 대화 저장
2. generate_summary(): LLM으로 요약 생성
3. prune_summary_list(): 중요도 기반 가지치기
4. calculate_time_diff(): 마지막 대화 시간 차이 계산
5. load_checkpoints(): 로그인시 checkpoint 로드
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from langchain.chat_models import init_chat_model

from db.config import CONNECTION_URL


class SessionCheckpointManager:
    """세션 체크포인트 관리 클래스"""

    def __init__(self):
        """초기화"""
        self.engine = create_engine(CONNECTION_URL)
        self.llm = init_chat_model(model="gpt-4o-mini", temperature=0.3)

    def save_checkpoint_background(
        self,
        user_id: int,
        npc_id: int,
        user_message: str,
        npc_response: str,
        state: Dict[str, Any],
    ) -> None:
        """백그라운드로 체크포인트 저장

        매 대화마다 호출됩니다.
        conversation에 방금 한 대화만 저장합니다.

        Args:
            user_id: 유저 ID
            npc_id: NPC ID
            user_message: 유저 메시지
            npc_response: NPC 응답
            state: 현재 상태 (affection, sanity, memoryProgress, emotion)
        """
        try:
            conversation = {"user": user_message, "npc": npc_response}

            sql = text(
                """
                INSERT INTO session_checkpoints (user_id, npc_id, conversation, state, last_chat_at)
                VALUES (:user_id, :npc_id, :conversation, :state, NOW())
            """
            )

            with self.engine.connect() as conn:
                conn.execute(
                    sql,
                    {
                        "user_id": user_id,
                        "npc_id": npc_id,
                        "conversation": json.dumps(conversation, ensure_ascii=False),
                        "state": json.dumps(state, ensure_ascii=False),
                    },
                )
                conn.commit()

        except Exception as e:
            print(f"[ERROR] save_checkpoint_background 실패: {e}")

    async def generate_summary(
        self, user_id: int, npc_id: int, conversations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """LLM으로 요약 생성

        20턴 또는 1시간 경과시 호출됩니다.

        Args:
            user_id: 유저 ID
            npc_id: NPC ID
            conversations: 대화 목록

        Returns:
            요약 딕셔너리 (summary, importance, created_at)
        """
        try:
            conversation_text = ""
            for conv in conversations:
                conversation_text += f"유저: {conv.get('user', '')}\n"
                conversation_text += f"NPC: {conv.get('npc', '')}\n\n"

            prompt = f"""다음 대화를 2-3문장으로 요약하고, 중요도를 1-5점으로 평가하세요.

[대화 내용]
{conversation_text}

[출력 형식]
요약: (2-3문장 요약)
중요도: (1-5 숫자만)"""

            response = await self.llm.ainvoke(prompt)
            content = response.content

            lines = content.strip().split("\n")
            summary = ""
            importance = 3

            for line in lines:
                if line.startswith("요약:"):
                    summary = line.replace("요약:", "").strip()
                elif line.startswith("중요도:"):
                    importance_str = line.replace("중요도:", "").strip()
                    importance = int(importance_str)

            return {
                "summary": summary,
                "importance": importance,
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[ERROR] generate_summary 실패: {e}")
            return {
                "summary": "요약 생성 실패",
                "importance": 1,
                "created_at": datetime.now().isoformat(),
            }

    def save_summary(
        self, user_id: int, npc_id: int, summary_item: Dict[str, Any]
    ) -> None:
        """요약을 summary_list에 추가

        Args:
            user_id: 유저 ID
            npc_id: NPC ID
            summary_item: 요약 항목 (summary, importance, created_at)
        """
        try:
            sql = text(
                """
                UPDATE session_checkpoints
                SET summary_list = summary_list || CAST(:summary_item AS jsonb)
                WHERE user_id = :user_id AND npc_id = :npc_id
                AND id = (
                    SELECT id FROM session_checkpoints
                    WHERE user_id = :user_id AND npc_id = :npc_id
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            """
            )

            with self.engine.connect() as conn:
                conn.execute(
                    sql,
                    {
                        "user_id": user_id,
                        "npc_id": npc_id,
                        "summary_item": json.dumps([summary_item], ensure_ascii=False),
                    },
                )
                conn.commit()

        except Exception as e:
            print(f"[ERROR] save_summary 실패: {e}")

    def prune_summary_list(
        self, summary_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """중요도 기반 가지치기

        규칙:
        1. 시간 기준: 현재 시간 - 요소 시간 > 3시간 -> 삭제 후보
        2. 개수 기준: 리스트 길이 > 5개 -> 삭제 후보
        3. 중요도 기반: 가장 낮은 중요도 중 가장 오래된 것 삭제

        Args:
            summary_list: 요약 목록

        Returns:
            가지치기된 요약 목록
        """
        # 요약 목록이 5개 이하면 가지치기 불필요, 그대로 반환
        if len(summary_list) <= 5:
            return summary_list

        # 현재 시간 저장 (시간 차이 계산용)
        now = datetime.now()

        # 요약 목록을 중요도(importance) 내림차순, 생성시간(created_at)(최신순) 내림차순으로 정렬
        # 중요도가 높고 최신인 것이 앞에 오도록 정렬
        sorted_list = sorted(
            summary_list,
            key=lambda x: (x.get("importance", 3), x.get("created_at", "")),
            reverse=True,
        )

        # 최종 결과를 담을 빈 리스트 생성
        result = []
        # 정렬된 리스트를 순회하며 필터링
        for item in sorted_list:
            # 요약 항목의 생성 시간 문자열 추출
            created_at_str = item.get("created_at", "")
            # 생성 시간이 존재하는 경우
            if created_at_str:
                # ISO 형식 문자열을 datetime 객체로 변환
                created_at = datetime.fromisoformat(created_at_str)
                # 현재 시간과의 차이 계산
                time_diff = now - created_at

                # 3시간 이상 경과했고 중요도가 2 이하인 경우 스킵 (삭제)
                if time_diff > timedelta(hours=3) and item.get("importance", 3) <= 2:
                    continue

            # 필터링을 통과한 항목을 결과 리스트에 추가
            result.append(item)

            # 결과 리스트가 5개에 도달하면 반복 종료
            if len(result) >= 5:
                break

        # 가지치기된 요약 목록 반환 (최대 5개, 중요도 높고 최신 순)
        return result

    def calculate_time_diff(self, last_chat_at: Optional[str]) -> str:
        """마지막 대화와 현재 시간 차이 계산

        Args:
            last_chat_at: 마지막 대화 시간 (ISO 형식)

        Returns:
            한국어로 변환된 시간 차이 문자열
        """
        if not last_chat_at:
            return "처음 대화"

        try:
            if isinstance(last_chat_at, str):
                last_time = datetime.fromisoformat(last_chat_at.replace("Z", "+00:00"))
            else:
                last_time = last_chat_at

            now = datetime.now(last_time.tzinfo) if last_time.tzinfo else datetime.now()
            diff = now - last_time

            total_minutes = int(diff.total_seconds() / 60)

            if total_minutes < 1:
                return "방금 전"
            elif total_minutes < 60:
                return f"{total_minutes}분 전"
            elif total_minutes < 1440:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if minutes > 0:
                    return f"{hours}시간 {minutes}분 전"
                return f"{hours}시간 전"
            else:
                days = total_minutes // 1440
                return f"{days}일 전"

        except Exception as e:
            print(f"[ERROR] calculate_time_diff 실패: {e}")
            return "알 수 없음"

    def load_checkpoints(self, user_id: int, npc_id: int) -> Dict[str, Any]:
        """로그인시 checkpoint 로드

        최근 20개의 conversation과 summary_list를 로드합니다.

        Args:
            user_id: 유저 ID
            npc_id: NPC ID

        Returns:
            로드된 데이터 (conversations, summary_list, state, last_chat_at)
        """
        try:
            sql = text(
                """
                SELECT conversation, summary_list, state, last_chat_at
                FROM session_checkpoints
                 WHERE user_id = :user_id AND npc_id = :npc_id
                ORDER BY created_at DESC
                LIMIT 20
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(sql, {"user_id": user_id, "npc_id": npc_id})
                rows = result.fetchall()

            if not rows:
                return {
                    "conversations": [],
                    "summary_list": [],
                    "state": None,
                    "last_chat_at": None,
                }

            conversations = []
            for row in reversed(rows):
                if row.conversation:
                    conversations.append(row.conversation)

            latest_row = rows[0]
            summary_list = latest_row.summary_list if latest_row.summary_list else []
            state = latest_row.state if latest_row.state else None
            last_chat_at = (
                latest_row.last_chat_at.isoformat() if latest_row.last_chat_at else None
            )

            return {
                "conversations": conversations,
                "summary_list": summary_list,
                "state": state,
                "last_chat_at": last_chat_at,
            }

        except Exception as e:
            print(f"[ERROR] load_checkpoints 실패: {e}")
            return {
                "conversations": [],
                "summary_list": [],
                "state": None,
                "last_chat_at": None,
            }

    def get_last_chat_at(self, user_id: int, npc_id: int) -> Optional[str]:
        """마지막 대화 시간 조회

        Args:
            user_id: 유저 ID
            npc_id: NPC ID

        Returns:
            마지막 대화 시간 (ISO 형식) 또는 None
        """
        try:
            sql = text(
                """
                SELECT last_chat_at
                FROM session_checkpoints
                WHERE user_id = :user_id AND npc_id = :npc_id
                ORDER BY created_at DESC
                LIMIT 1
            """
            )

            with self.engine.connect() as conn:
                result = conn.execute(sql, {"user_id": user_id, "npc_id": npc_id})
                row = result.fetchone()

            if row and row.last_chat_at:
                return row.last_chat_at.isoformat()
            return None

        except Exception as e:
            print(f"[ERROR] get_last_chat_at 실패: {e}")
            return None


session_checkpoint_manager = SessionCheckpointManager()
