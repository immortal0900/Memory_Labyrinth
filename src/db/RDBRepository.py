import json
from typing import List, Any, Dict, Optional,Sequence
from sqlalchemy import create_engine, text
from db.config import CONNECTION_URL
from enums.EmbeddingModel import EmbeddingModel
from db.rdb_entity.DungeonRow import DungeonRow

# 이때 summary_info는 그냥 던전 밸런싱 요약내용을 text로.


# 전역 엔진 인스턴스 (싱글톤 패턴)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            CONNECTION_URL,
            pool_pre_ping=True,  # 연결 유효성 사전 체크
            pool_recycle=3600,  # 1시간마다 연결 재생성
            pool_size=10,  # 최대 연결 수
            max_overflow=0,  # 오버플로우 방지
            pool_timeout=10,  # 연결 대기 시간 단축
            echo=False,  # SQL 쿼리 로깅 비활성화
        )
    return _engine


class RDBRepository:
    def __init__(self):
        self.db_url = CONNECTION_URL
        self.engine = get_engine()
    def insert_dungeon(self, floor: int, raw_map: dict | str) -> int:
        """
        던전 생성

        Args:
            floor: 던전 층수 (1, 2, 3, ...)
            raw_map: 던전 맵 원본 데이터 (dict 또는 JSON 문자열)

        Returns:
            생성된 던전의 ID

        Note:
            1층: raw_map과 balanced_map에 동일한 초기값 설정 (언리얼이 보낸 맵)
            2층, 3층: balanced_map은 None으로 시작 (이전 층의 balance_dungeon() 후 자동 업데이트)
        """
        raw_map_dict = raw_map if isinstance(raw_map, dict) else json.loads(raw_map)
        player_ids = raw_map_dict.get("player_ids") or raw_map_dict.get("playerIds", [])
        heroine_ids = raw_map_dict.get("heroine_ids") or raw_map_dict.get("heroineIds", [])

        player_with_heroine = []
        for i in range(0, 4):
            player_id = str(player_ids[i]) if i < len(player_ids) else None
            heroine_id = str(heroine_ids[i]) if i < len(heroine_ids) else None
            player_with_heroine.append((player_id, heroine_id))

        sql = """
        INSERT INTO dungeon 
        (floor, raw_map, balanced_map, is_finishing, summary_info,
         player1, player2, player3, player4, 
         heroine1, heroine2, heroine3, heroine4)
        VALUES 
        (:floor, :raw_map, :balanced_map, :is_finishing, :summary_info,
         :player1, :player2, :player3, :player4,
         :heroine1, :heroine2, :heroine3, :heroine4)
        RETURNING id
        """

        raw_map_json = (
            json.dumps(raw_map) if isinstance(raw_map, (dict, list)) else raw_map
        )

        if floor == 1:
            balanced_map_value = raw_map_json
        else:
            balanced_map_value = None

        params = {
            "floor": floor,
            "raw_map": raw_map_json,
            "balanced_map": balanced_map_value,
            "is_finishing": False,
            "summary_info": "",
            "player1": player_with_heroine[0][0],
            "player2": player_with_heroine[1][0],
            "player3": player_with_heroine[2][0],
            "player4": player_with_heroine[3][0],
            "heroine1": player_with_heroine[0][1],
            "heroine2": player_with_heroine[1][1],
            "heroine3": player_with_heroine[2][1],
            "heroine4": player_with_heroine[3][1],
        }

        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params)
            conn.commit()
            inserted_id = result.fetchone()[0]
            return inserted_id

    def get_unfinished_dungeons(self, player_ids: List[int]) -> Dict[str, Any] | None:
        """
        미완료 던전 조회

        Args:
            player_ids: 플레이어 ID 리스트

        Returns:
            미완료 던전 정보 (dict) 또는 None
        """
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                SELECT *
                FROM dungeon
                WHERE is_finishing = FALSE
                ORDER BY floor ASC
            """
                )
            ).fetchall()

            if not rows:
                return None

            target = set(map(str, player_ids))

            for row in rows:
                raw_map_value = row._mapping["raw_map"]
                raw_map = (
                    json.loads(raw_map_value)
                    if isinstance(raw_map_value, str)
                    else raw_map_value
                )
                # playerIds와 player_ids 모두 체크 (정규화 여부와 무관하게)
                row_players = set(
                    map(str, raw_map.get("playerIds") or raw_map.get("player_ids", []))
                )

                # raw_map에 없으면 컬럼에서 확인
                if not row_players:
                    for i in range(1, 5):
                        p_id = row._mapping[f"player{i}"]
                        if p_id:
                            row_players.add(str(p_id))

                if target.issubset(row_players):
                    return dict(row._mapping)

            return None

    def balanced_dungeon(
        self,
        balanced_map: dict | str,
        dungeon_id: int,
        agent_result: Dict[str, Any] | None = None,
    ) -> None:
        """
        던전 밸런싱 업데이트 + summary_info 자동 생성

        Args:
            balanced_map: 밸런싱된 맵 데이터 (dict 또는 JSON 문자열)
            dungeon_id: 던전 ID
            agent_result: Super Dungeon Agent의 최종 결과 dict (선택사항)
                - meta: {generated_at, dungeon_id, floor_count, total_rooms}
                - events: {main_event, sub_event, event_room_index}
                - monster_stats: {total_count, boss_count, normal_count, ...}
                - difficulty_info: {combat_score, ai_multiplier, ...}
        """
        # Agent 결과에서 summary_info 생성
        summary_info = ""
        if agent_result:
            events = agent_result.get("events", {})
            monster_stats = agent_result.get("monster_stats", {})
            difficulty_info = agent_result.get("difficulty_info", {})

            # 맵 설명 생성
            raw_map_value = None
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT raw_map FROM dungeon WHERE id = :id"),
                    {"id": dungeon_id},
                ).fetchone()
                if result:
                    raw_map_value = result[0]

            raw_map = (
                (
                    json.loads(raw_map_value)
                    if isinstance(raw_map_value, str)
                    else raw_map_value
                )
                if raw_map_value
                else {}
            )

            rooms_count = len(raw_map.get("rooms", []))
            room_types = {}
            for room in raw_map.get("rooms", []):
                room_type = room.get("type", "unknown")
                room_types[room_type] = room_types.get(room_type, 0) + 1

            room_type_str = ", ".join(
                [f"{k}실 {v}개" for k, v in sorted(room_types.items())]
            )

            # Summary 정보 구성
            # 이벤트 정보 추출 (dict 형식)
            main_event = events.get("main_event", {})
            sub_event = events.get("sub_event", {})

            main_event_title = (
                main_event.get("title", "N/A")
                if isinstance(main_event, dict)
                else str(main_event)[:80]
            )
            sub_event_narrative = (
                sub_event.get("narrative", "N/A")
                if isinstance(sub_event, dict)
                else str(sub_event)[:80]
            )

            summary_lines = [
                f"[맵 구성]",
                f"  - 총 방: {rooms_count}개 ({room_type_str})",
                f"",
                f"[몬스터 배치]",
                f"  - 총 {monster_stats.get('total_count', 0)}마리 (보스: {monster_stats.get('boss_count', 0)}, 일반: {monster_stats.get('normal_count', 0)})",
                f"  - 위협도 달성률: {monster_stats.get('achievement_rate', 0):.1f}%",
                f"",
                f"[난이도]",
                f"  - 전투력: {difficulty_info.get('combat_score', 0):.2f}",
                f"  - AI 배율: x{difficulty_info.get('ai_multiplier', 1.0):.2f}",
                f"",
                f"[이벤트]",
                f"  - 주요: {main_event_title}",
                f"  - 보조: {str(sub_event_narrative)[:80]}...",
            ]
            summary_info = "\n".join(summary_lines)

        sql = """
        UPDATE dungeon
        SET balanced_map = :balanced_map,
            summary_info = :summary_info
        WHERE id = :dungeon_id
        """

        params = {
            "balanced_map": (
                json.dumps(balanced_map)
                if isinstance(balanced_map, (dict, list))
                else balanced_map
            ),
            "summary_info": summary_info,
            "dungeon_id": dungeon_id,
        }

        with self.engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()

    def is_finishing_dungeon(self, player_ids: List[int]) -> Dict[str, Any] | None:
        """
        현재 진행 중인 던전을 완료 처리

        Args:
            player_ids: 플레이어 ID 리스트

        Returns:
            완료 처리된 던전 정보 (dict) 또는 None
        """
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                SELECT *
                FROM dungeon
                WHERE is_finishing = FALSE
                ORDER BY floor ASC
            """
                )
            ).fetchall()

            if not rows:
                return None

            target = set(map(str, player_ids))

            for row in rows:
                raw_map_value = row._mapping["raw_map"]
                raw_map = (
                    json.loads(raw_map_value)
                    if isinstance(raw_map_value, str)
                    else raw_map_value
                )
                # playerIds와 player_ids 모두 체크 (정규화 여부와 무관하게)
                row_players = set(
                    map(str, raw_map.get("playerIds") or raw_map.get("player_ids", []))
                )

                # raw_map에 없으면 컬럼에서 확인 (get_unfinished_dungeons와 동일 로직)
                if not row_players:
                    for i in range(1, 5):
                        p_id = row._mapping[f"player{i}"]
                        if p_id:
                            row_players.add(str(p_id))

                # 부분집합(issubset) 대신 교집합(intersection) 확인으로 변경
                # 요청한 플레이어 중 한 명이라도 던전에 포함되어 있으면 해당 던전으로 간주
                if not target.isdisjoint(row_players):
                    dungeon_id = row._mapping["id"]

                    # 현재 던전을 완료 처리
                    conn.execute(
                        text("UPDATE dungeon SET is_finishing = TRUE WHERE id = :id"),
                        {"id": dungeon_id},
                    )
                    conn.commit()

                    # 완료 처리된 던전 조회
                    updated = conn.execute(
                        text("SELECT * FROM dungeon WHERE id = :id"), {"id": dungeon_id}
                    ).fetchone()
                    updated_dict = dict(updated._mapping)
                    return updated_dict

            return None

    def get_current_dungeon_by_player(
        self, player_id: str, heroine_id: int
    ) -> DungeonRow | None:
        sql = """
        SELECT *
        FROM dungeon
        WHERE is_finishing = false
        AND (
                (player1 = :player_id AND heroine1 = :heroine_id) OR
                (player2 = :player_id AND heroine2 = :heroine_id) OR
                (player3 = :player_id AND heroine3 = :heroine_id) OR
                (player4 = :player_id AND heroine4 = :heroine_id)
            )
        ORDER BY floor ASC
        LIMIT 1
        """

        params = {"player_id": str(player_id), "heroine_id": str(heroine_id)}

        with self.engine.connect() as conn:
            row = conn.execute(text(sql), params).fetchone()
            if not row:
                return None

            row_dict = dict(row._mapping)
            event_value = row_dict.get("event")
            if isinstance(event_value, list):
                row_dict["event"] = event_value[0] if event_value else None

            return DungeonRow(**row_dict)

    def get_event_by_floor(self, player_id: str, floor: int) -> Optional[Any]:
        """
        특정 플레이어가 참여한, 특정 층의 던전 이벤트를 반환
        """
        sql = """
        SELECT event
        FROM dungeon
        WHERE is_finishing = false
        AND (
            player1 = :player_id OR player2 = :player_id OR player3 = :player_id OR player4 = :player_id
        )
        AND floor = :floor
        LIMIT 1
        """
        params = {"player_id": str(player_id), "floor": floor}
        with self.engine.connect() as conn:
            row = conn.execute(text(sql), params).fetchone()
            if not row:
                return None
            event_value = row[0]
            if isinstance(event_value, str):
                try:
                    return json.loads(event_value)
                except Exception:
                    return event_value
            return event_value
        
    def insert_fairy_message(
        self,
        sender_type: str,        # 'AI' | 'USER'
        message: str,
        context_type: str,       # 'DUNGEON' | 'GUILD'
        player_id: str,          # <= 100 chars
        heroine_id: int,         # <= 2 digits
        intent_type: Optional[Sequence[str]] = None,  # ← list 허용
    ) -> None:
        sql = """
        INSERT INTO fairy_messages
            (sender_type, message, context_type, player_id, heroine_id, intent_type)
        VALUES
            (:sender_type, :message, :context_type, :player_id, :heroine_id, :intent_type)
        """

        params = {
            "sender_type": sender_type,
            "message": message[:100],  # DB 제약 보호
            "context_type": context_type,
            "player_id": str(player_id)[:100],
            "heroine_id": str(heroine_id)[:2],
            "intent_type": json.dumps(intent_type) if intent_type else None,
        }

        with self.engine.connect() as conn:
            conn.execute(text(sql), params)
            conn.commit()

    def get_fairy_messages_for_memory(
        self,
        player_id: str,
        heroine_id: str,
        context_type:str = "DUNGEON",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        fairy_messages 조회 (메모리 적재용)
        """
        sql = f"""
        SELECT
            sender_type,
            message,
            player_id,
            intent_type,
            created_at
        FROM fairy_messages
        WHERE player_id = :player_id
          AND context_type = :context_type
          AND heroine_id = :heroine_id
        ORDER BY created_at DESC
        LIMIT {limit}
        """
        params = {
            "player_id": player_id,
            "context_type": context_type,
            "heroine_id": str(heroine_id),
        }

        with self.engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
            return [dict(r._mapping) for r in rows]
