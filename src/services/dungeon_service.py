"""
Dungeon Service Layer
fairy_service.py 구조를 따라 던전 밸런싱을 통합 관리
"""

import json
from typing import Dict, Any, List, Optional

from db.RDBRepository import RDBRepository


# ============================================================
# Unreal JSON 정규화 (camelCase -> snake_case + type 변환)
# ============================================================
def _normalize_room_keys(raw_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unreal에서 보낸 JSON의 room 구조를 내부 형식으로 변환
    - roomId -> room_id
    - monsterId -> monster_id
    - posX -> pos_x, posY -> pos_y
    - eventType -> event_type
    - type (숫자) -> room_type (문자열):
      * 0 -> "empty" (빈방)
      * 1 -> "monster" (전투방)
      * 2 -> "event" (이벤트방)
      * 3 -> "treasure" (보물방)
      * 4 -> "boss" (보스방)
    """
    if not isinstance(raw_map, dict) or "rooms" not in raw_map:
        return raw_map

    normalized = json.loads(json.dumps(raw_map))  # deep copy

    # room type 매핑
    # Unreal: 0=빈방, 1=전투방, 2=이벤트방, 3=보물방, 4=보스방
    TYPE_MAP = {
        0: "empty",  # 빈방 - 몬스터 없음
        1: "monster",  # 전투방 - 일반 몬스터
        2: "event",  # 이벤트방
        3: "treasure",  # 보물방
        4: "boss",  # 보스방
    }

    # 최상위 playerIds, heroineIds 정규화
    if "playerIds" in normalized:
        normalized["player_ids"] = normalized.pop("playerIds")
    if "heroineIds" in normalized:
        normalized["heroine_ids"] = normalized.pop("heroineIds")

    for room in normalized.get("rooms", []):
        # roomId -> room_id
        if "roomId" in room and "room_id" not in room:
            room["room_id"] = room.pop("roomId")

        # type (숫자) -> room_type (문자열)
        if "type" in room:
            room_type_num = room.pop("type")
            room["room_type"] = TYPE_MAP.get(room_type_num, "monster")

        # eventType -> event_type
        if "eventType" in room and "event_type" not in room:
            room["event_type"] = room.pop("eventType")

        # monsters 내 필드 정규화
        for monster in room.get("monsters", []):
            if "monsterId" in monster and "monster_id" not in monster:
                monster["monster_id"] = monster.pop("monsterId")
            if "posX" in monster and "pos_x" not in monster:
                monster["pos_x"] = monster.pop("posX")
            if "posY" in monster and "pos_y" not in monster:
                monster["pos_y"] = monster.pop("posY")

    return normalized


# ============================================================
# Dungeon Balancing Graph - Lazy Loading
# ============================================================
_dungeon_graph = None


def get_dungeon_graph():
    """Lazy initialization으로 Super Agent Graph 반환"""
    global _dungeon_graph
    if _dungeon_graph is None:
        from agents.dungeon.super.dungeon_agent import create_super_dungeon_graph

        _dungeon_graph = create_super_dungeon_graph()
    return _dungeon_graph


class DungeonService:
    """던전 서비스 계층"""

    def __init__(self):
        self.repo = RDBRepository()

    # ============================================================
    # 1. 던전 입장 (Entrance)
    # ============================================================
    def entrance(
        self, player_ids: List[int], heroine_ids: List[int], raw_map: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        던전 입장: 1층, 2층, 3층 모두 생성

        Args:
            player_ids: 플레이어 ID 리스트
            heroine_ids: 영웅 ID 리스트
            raw_map: Unreal에서 보낸 1층 raw_map (camelCase)

        Returns:
            {
                "floor1_id": int,
                "floor2_id": int,
                "floor3_id": int,
                "floor1_data": dict,
            }
        """
        # Unreal JSON 정규화 (camelCase -> snake_case)
        normalized_raw_map = _normalize_room_keys(raw_map)

        # 1층 생성 (완전한 데이터)
        floor1_id = self.repo.insert_dungeon(floor=1, raw_map=normalized_raw_map)

        # 2층, 3층 생성 (placeholder - Unreal이 나중에 업데이트)
        placeholder_raw_map = {
            "player_ids": normalized_raw_map.get("player_ids", []),
            "heroine_ids": normalized_raw_map.get("heroine_ids", []),
            "rooms": [],
            "rewards": [],
        }
        floor2_id = self.repo.insert_dungeon(
            floor=2,
            raw_map=placeholder_raw_map,
        )
        floor3_id = self.repo.insert_dungeon(
            floor=3,
            raw_map=placeholder_raw_map,
        )

        return {
            "floor1_id": floor1_id,
            "floor2_id": floor2_id,
            "floor3_id": floor3_id,
        }

    # ============================================================
    # 2. 다음 층 raw_map 업데이트
    # ============================================================
    def update_raw_map(self, dungeon_id: int, raw_map: Dict[str, Any]) -> bool:
        """
        다음 층의 raw_map 업데이트 (Unreal이 생성 후 전달)

        Args:
            dungeon_id: 업데이트할 던전 ID
            raw_map: Unreal이 생성한 raw_map (camelCase)

        Returns:
            성공 여부
        """
        try:
            # Unreal JSON 정규화
            normalized_raw_map = _normalize_room_keys(raw_map)

            from sqlalchemy import text

            with self.repo.engine.connect() as conn:
                conn.execute(
                    text("UPDATE dungeon SET raw_map = :raw_map WHERE id = :id"),
                    {"raw_map": json.dumps(normalized_raw_map), "id": dungeon_id},
                )
                conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] raw_map 업데이트 실패: {e}")
            return False

    # ============================================================
    # 2-1. Summary Info 생성 헬퍼
    # ============================================================
    def _generate_summary_info(
        self, balanced_map: Dict[str, Any], agent_result: Dict[str, Any]
    ) -> str:
        """
        Super Agent 결과로부터 summary_info 생성

        Args:
            balanced_map: 밸런싱된 맵 데이터
            agent_result: Super Agent 최종 결과

        Returns:
            생성된 summary_info 문자열
        """
        events = agent_result.get("events", {})
        monster_stats = agent_result.get("monster_stats", {})
        difficulty_info = agent_result.get("difficulty_info", {})

        rooms = balanced_map.get("rooms", [])
        rooms_count = len(rooms)
        room_types = {}
        for room in rooms:
            room_type = room.get("room_type", "unknown")
            room_types[room_type] = room_types.get(room_type, 0) + 1

        room_type_str = ", ".join(
            [f"{k}실 {v}개" for k, v in sorted(room_types.items())]
        )

        # 이벤트 정보 추출 (이제 dict 형식)
        main_event = events.get("main_event", {})
        sub_event = events.get("sub_event", {})

        main_event_title = (
            main_event.get("title", "N/A") if isinstance(main_event, dict) else "N/A"
        )
        sub_event_narrative = (
            sub_event.get("narrative", "N/A") if isinstance(sub_event, dict) else "N/A"
        )

        # 문자열로 변환 후 슬라이싱
        sub_event_preview = (
            str(sub_event_narrative)[:80] if sub_event_narrative != "N/A" else "N/A"
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
            f"  - 보조: {sub_event_preview}...",
        ]
        return "\n".join(summary_lines)

    # ============================================================
    # 3. 던전 밸런싱 (Boss Room - Super Agent 실행)
    # ============================================================
    def balance_dungeon(
        self,
        dungeon_id: int,
        heroine_data: Dict[str, Any],
        heroine_stat: Dict[str, Any],
        heroine_memories: List[Dict[str, Any]],
        dungeon_player_data: Dict[str, Any],
        monster_db: Dict[str, Any],
        used_events: List[Any] = None,
    ) -> Dict[str, Any]:
        """
        보스방 입장 시 Super Agent 실행하여 balanced_map 생성 및 저장

        Args:
            dungeon_id: 던전 ID
            heroine_data: 히로인 정보 {heroine_id, name, event_room, memory_progress}
            heroine_stat: 히로인 스탯 {hp, strength, dexterity, ...}
            heroine_memories: 히로인 메모리 리스트
            dungeon_player_data: 플레이어 던전 정보 {affection, sanity, difficulty_level}
            monster_db: 몬스터 데이터베이스
            used_events: 이미 사용한 이벤트 리스트

        Returns:
            {
                "success": bool,
                "dungeon_id": int,
                "agent_result": dict (super_agent 최종 결과),
                "summary": str,
            }
        """
        try:
            # DB에서 현재 던전 조회 (연결 블록 외부에서)
            from sqlalchemy import text

            with self.repo.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM dungeon WHERE id = :id"), {"id": dungeon_id}
                ).fetchone()
                if not result:
                    return {
                        "success": False,
                        "error": f"던전 {dungeon_id}를 찾을 수 없습니다",
                    }
                dungeon_row = dict(result._mapping)

            # raw_map 파싱 (연결 블록 외부에서)
            raw_map_value = dungeon_row.get("raw_map")
            raw_map = (
                json.loads(raw_map_value)
                if isinstance(raw_map_value, str)
                else raw_map_value
            )
            
            # DEBUG: raw_map 확인
            print(f"\n[DEBUG] 던전 {dungeon_id} raw_map 읽음:")
            print(f"  - rooms count: {len(raw_map.get('rooms', []))}")
            for i, room in enumerate(raw_map.get("rooms", [])):
                monsters = room.get("monsters", [])
                print(f"  - room {i}: type={room.get('room_type')}, monsters={monsters}")

            # Super Agent 입력 State 구성
            agent_state = {
                "dungeon_base_data": {
                    "dungeon_id": dungeon_id,
                    "floor_count": dungeon_row.get("floor", 1),
                    "rooms": raw_map.get("rooms", []),
                },
                "heroine_data": heroine_data,
                "heroine_stat": heroine_stat,
                "heroine_memories": heroine_memories,
                "monster_db": monster_db,
                "dungeon_player_data": dungeon_player_data,
                "used_events": used_events if used_events is not None else [],
                "event_result": {},
                "filled_dungeon_data": {},
                "difficulty_log": {},
                "final_dungeon_json": {},
            }

            # Super Agent 실행 (연결 블록 외부에서 - DB 연결 점유 안함)
            print(f"\n[Dungeon {dungeon_id}] Super Agent 실행 중...")
            dungeon_graph = get_dungeon_graph()
            agent_result = dungeon_graph.invoke(agent_state)

            final_json = agent_result.get("final_dungeon_json", {})
            balanced_map_data = final_json.get("dungeon_data", {})

            # 현재 층 정보 조회
            current_floor = dungeon_row.get("floor", 1)

            # DEBUG: agent_result 구조 출력
            print(f"\n[DEBUG] final_json keys: {list(final_json.keys())}")
            print(f"[DEBUG] balanced_map_data keys: {list(balanced_map_data.keys())}")
            print(f"[DEBUG] balanced_map_data.get('rooms'): {len(balanced_map_data.get('rooms', []))} rooms")
            print(f"[DEBUG] events keys: {list(final_json.get('events', {}).keys())}")
            print(f"[DEBUG] monster_stats: {final_json.get('monster_stats', {})}")

            # summary_info 생성 (현재 층의 데이터 기반)
            summary_info = self._generate_summary_info(balanced_map_data, final_json)

            # 다음 층 조회 (같은 player_ids를 가진 floor+1인 던전)
            next_floor = current_floor + 1
            # 정규화된 또는 원본 필드명으로 player_ids 추출
            player_ids_list = raw_map.get("player_ids") or raw_map.get("playerIds", [])

            # DB 업데이트 (단일 연결 블록으로 통합)
            with self.repo.engine.begin() as conn:
                # player_ids의 첫 번째 항목으로 다음 층 찾기
                # (같은 플레이어 그룹은 player1 값으로 식별)
                if player_ids_list:
                    first_player_id = str(player_ids_list[0])

                    next_dungeon_query = """
                        SELECT id FROM dungeon 
                        WHERE floor = :next_floor 
                        AND player1 = :player1
                        LIMIT 1
                    """

                    next_result = conn.execute(
                        text(next_dungeon_query),
                        {"next_floor": next_floor, "player1": first_player_id},
                    ).fetchone()

                    if next_result:
                        next_dungeon_id = next_result[0]

                        # 다음 층에 넘길 balanced_map 메타데이터 업데이트
                        # floor_count와 dungeon_id를 다음 층 정보로 변경
                        next_balanced_map = json.loads(
                            json.dumps(balanced_map_data)
                        )  # deep copy

                        # 최상위 레벨의 메타데이터 업데이트
                        if "dungeon_id" in next_balanced_map:
                            next_balanced_map["dungeon_id"] = next_dungeon_id
                        if "floor_count" in next_balanced_map:
                            next_balanced_map["floor_count"] = next_floor

                        # 중첩된 메타데이터 업데이트 (있는 경우)
                        if "meta" in next_balanced_map:
                            next_balanced_map["meta"]["dungeon_id"] = next_dungeon_id
                            next_balanced_map["meta"]["floor_count"] = next_floor

                        if "dungeon_base_data" in next_balanced_map:
                            next_balanced_map["dungeon_base_data"][
                                "dungeon_id"
                            ] = next_dungeon_id
                            next_balanced_map["dungeon_base_data"][
                                "floor_count"
                            ] = next_floor

                        # 다음 층의 balanced_map에 업데이트된 데이터 저장
                        conn.execute(
                            text(
                                "UPDATE dungeon SET balanced_map = :balanced_map WHERE id = :id"
                            ),
                            {
                                "balanced_map": json.dumps(next_balanced_map),
                                "id": next_dungeon_id,
                            },
                        )
                        print(
                            f"\n✅ 다음 층(Floor {next_floor}) balanced_map 자동 업데이트 완료"
                        )

                # 현재 층의 balanced_map과 summary_info 저장
                print(f"\n[Dungeon {dungeon_id}] 현재 층 저장 중...")
                print(f"  - balanced_map_data keys: {list(balanced_map_data.keys())}")
                print(f"  - summary_info length: {len(summary_info)}")
                
                conn.execute(
                    text(
                        "UPDATE dungeon SET balanced_map = :balanced_map, summary_info = :summary_info WHERE id = :id"
                    ),
                    {
                        "balanced_map": json.dumps(balanced_map_data),
                        "summary_info": summary_info,
                        "id": dungeon_id,
                    },
                )
                print(f"✅ 던전 {dungeon_id} 저장 완료")

            return {
                "success": True,
                "dungeon_id": dungeon_id,
                "agent_result": final_json,
                "summary": summary_info,
            }
        except Exception as e:
            print(f"[ERROR] 던전 밸런싱 실패: {e}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "dungeon_id": dungeon_id,
                "error": str(e),
            }

    # ============================================================
    # 4. 층 완료 (Clear - is_finishing = TRUE)
    # ============================================================
    def clear_floor(self, player_ids: List[int]) -> Dict[str, Any]:
        """
        현재 층 완료 처리 및 balanced_map 반환
        (Unreal에 다음 층 raw_map 생성을 위해 전달할 데이터)

        Args:
            player_ids: 플레이어 ID 리스트

        Returns:
            {
                "success": bool,
                "finished_dungeon": dict,
                "balanced_map": dict,
            }
        """
        try:
            finished = self.repo.is_finishing_dungeon(player_ids=player_ids)

            if not finished:
                return {
                    "success": False,
                    "error": "완료할 던전을 찾을 수 없습니다",
                }

            # balanced_map 추출
            balanced_map_value = finished.get("balanced_map")
            balanced_map = (
                (
                    json.loads(balanced_map_value)
                    if isinstance(balanced_map_value, str)
                    else balanced_map_value
                )
                if balanced_map_value
                else {}
            )

            return {
                "success": True,
                "finished_dungeon": finished,
                "balanced_map": balanced_map,
            }
        except Exception as e:
            print(f"[ERROR] 층 완료 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ============================================================
    # 5. 상태 조회 (Status)
    # ============================================================
    def get_status(self, player_ids: List[int]) -> Dict[str, Any]:
        """플레이어의 현재 진행 중인 던전 상태 조회"""
        return self.repo.get_unfinished_dungeons(player_ids=player_ids)

    def get_all(self) -> List[Dict[str, Any]]:
        """모든 던전 조회 (관리자용)"""
        try:
            from sqlalchemy import text

            with self.repo.engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT * FROM dungeon ORDER BY id DESC")
                ).fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            print(f"[ERROR] 던전 조회 실패: {e}")
            return []


# ============================================================
# 서비스 초기화 (Singleton 패턴)
# ============================================================
_dungeon_service = None


def get_dungeon_service() -> DungeonService:
    """DungeonService 싱글톤 반환"""
    global _dungeon_service
    if _dungeon_service is None:
        _dungeon_service = DungeonService()
    return _dungeon_service
