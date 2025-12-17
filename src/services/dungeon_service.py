"""
Dungeon Service Layer
fairy_service.py 구조를 따라 던전 밸런싱을 통합 관리
"""

import json
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from db.RDBRepository import RDBRepository


# ============================================================
# Unreal JSON 정규화 (camelCase -> snake_case + type 변환)
# ============================================================
def _normalize_room_keys(raw_map: Dict[str, Any]) -> Dict[str, Any]:
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


def _normalize_heroine_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    히로인 데이터 키 정규화 (camelCase -> snake_case)
    """
    if not data:
        return {}

    normalized = data.copy()

    # heroineId -> heroine_id
    if "heroineId" in normalized:
        normalized["heroine_id"] = normalized.pop("heroineId")

    # memoryProgress -> memory_progress
    if "memoryProgress" in normalized:
        normalized["memory_progress"] = normalized.pop("memoryProgress")

    # 기본값 설정 (Agent에서 필수)
    if "heroine_id" not in normalized:
        normalized["heroine_id"] = 1  # 기본값
    if "memory_progress" not in normalized:
        normalized["memory_progress"] = 0  # 기본값

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
    def __init__(self):
        self.repo = RDBRepository()

    def entrance(
        self,
        player_ids: List[str],
        heroine_ids: List[int],
        raw_maps: List[Dict[str, Any]],  # 여러 층 raw_map
        heroine_data: Optional[List] = None,
        used_events: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        events_list = []
        floor_ids = []
        try:
            # Ensure used_events is a list for safe appends
            used_events = used_events or []

            # First pass: do DB existence checks / INSERTs inside a transaction,
            # but defer actual event generation (LLM, graph invokes) until after
            # the transaction to allow parallel execution across floors.
            floors_meta = []
            with self.repo.engine.begin() as conn:
                # heroine_data가 int 리스트면 dict로 변환
                normalized_heroines = []
                if heroine_data:
                    if all(isinstance(h, int) for h in heroine_data):
                        for hid, mp in zip(heroine_ids, heroine_data):
                            normalized_heroines.append(
                                {"heroine_id": hid, "memory_progress": mp}
                            )
                    elif isinstance(heroine_data, list):
                        for h in heroine_data:
                            normalized_heroines.append(_normalize_heroine_data(h))
                    else:
                        normalized_heroines.append(
                            _normalize_heroine_data(heroine_data)
                        )
                for idx, raw_map in enumerate(raw_maps):
                    floor_num = idx + 1
                    if floor_num > 2:
                        break  # 1,2층만 생성
                    normalized_raw_map = _normalize_room_keys(raw_map)
                    normalized_raw_map["floor"] = floor_num
                    # playerIds, heroineIds를 모든 층 raw_map에 주입
                    normalized_raw_map["player_ids"] = player_ids
                    normalized_raw_map["heroine_ids"] = heroine_ids

                    check_sql = text(
                        """
                        SELECT id, event FROM dungeon WHERE floor = :floor AND (
                            player1 = :player_id OR player2 = :player_id OR player3 = :player_id OR player4 = :player_id
                        )
                    """
                    )
                    player_id = player_ids[0] if player_ids else None
                    player_id_str = str(player_id) if player_id is not None else None
                    result = conn.execute(
                        check_sql, {"floor": floor_num, "player_id": player_id_str}
                    )
                    row = result.fetchone()
                    if row:
                        floor_id = row[0]
                        existing_event = row[1]
                    else:
                        floor_id = self._insert_dungeon_in_transaction(
                            conn, floor=floor_num, raw_map=normalized_raw_map
                        )
                        existing_event = None
                    floor_ids.append(floor_id)

                    # 이벤트 룸 목록만 수집 (실제 이벤트 생성은 트랜잭션 바깥에서 병렬 실행)
                    event_rooms = [
                        room
                        for room in normalized_raw_map.get("rooms", [])
                        if room.get("room_type") == "event"
                        or room.get("event_type", 0) != 0
                    ]

                    # store metadata for later parallel processing
                    floors_meta.append(
                        {
                            "floor_num": floor_num,
                            "normalized_raw_map": normalized_raw_map,
                            "event_rooms": event_rooms,
                            "floor_id": floor_id,
                            "existing_event": existing_event,
                            "normalized_heroines": normalized_heroines,
                        }
                    )

                # end with conn

            # Outside the DB transaction: generate events for each floor in parallel
            import concurrent.futures

            def process_floor_meta(meta):
                fn = meta["floor_num"]
                nmap = meta["normalized_raw_map"]
                rooms = meta["event_rooms"]
                floor_events = []
                # Use representative heroine list prepared earlier
                n_heroines = meta.get("normalized_heroines") or normalized_heroines
                for room in rooms:
                    room_id = room.get("room_id")
                    main_event_data = self._create_event_for_floor(
                        heroine_data=n_heroines[0],
                        player_id=player_ids[0] if player_ids else None,
                        next_floor=fn,
                        used_events=list(used_events),
                        room_id=room_id,
                    )
                    if not main_event_data:
                        continue
                    main_event_data["floor"] = fn
                    if main_event_data.get("is_personal", False):
                        heroine_narratives = []
                        for player_id_val, heroine in zip(player_ids, n_heroines):
                            indiv_event = self._create_event_for_floor(
                                heroine_data=heroine,
                                player_id=player_id_val,
                                next_floor=fn,
                                used_events=list(used_events),
                                room_id=room_id,
                            )
                            if indiv_event:
                                heroine_narratives.append(
                                    {
                                        "playerId": player_id_val,
                                        "heroineId": heroine["heroine_id"],
                                        "memoryProgress": heroine["memory_progress"],
                                        "narrative": indiv_event.get("scenario_narrative", ""),
                                    }
                                )
                        main_event_data["heroineNarratives"] = heroine_narratives
                    floor_events.append(main_event_data)

                summary_info_value = self._generate_raw_map_summary(nmap)
                return {"floor_num": fn, "events": floor_events, "summary": summary_info_value, "floor_id": meta["floor_id"], "existing_event": meta["existing_event"], "normalized_raw_map": nmap}

            # Run floor processing in parallel (max 2 workers)
            floor_results = []
            if floors_meta:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, len(floors_meta))) as ex:
                    futures = [ex.submit(process_floor_meta, m) for m in floors_meta]
                    for fut in concurrent.futures.as_completed(futures):
                        floor_results.append(fut.result())

            # Persist generated events & summaries back into DB in a single transaction
            with self.repo.engine.begin() as conn:
                for res in floor_results:
                    floor_id = res["floor_id"]
                    events_for_this_floor = res["events"]
                    summary_info_value = res["summary"]
                    nmap = res.get("normalized_raw_map")
                    existing_event = res.get("existing_event")
                    if existing_event:
                        conn.execute(
                            text(
                                "UPDATE dungeon SET event = :event, summary_info = :summary_info WHERE id = :id"
                            ),
                            {
                                "event": json.dumps(events_for_this_floor),
                                "summary_info": summary_info_value,
                                "id": floor_id,
                            },
                        )
                    else:
                        conn.execute(
                            text(
                                "UPDATE dungeon SET raw_map = :raw_map, event = :event, summary_info = :summary_info WHERE id = :id"
                            ),
                            {
                                "raw_map": json.dumps(nmap),
                                "event": json.dumps(events_for_this_floor),
                                "summary_info": summary_info_value,
                                "id": floor_id,
                            },
                        )
                    events_list.extend(events_for_this_floor)
                    if not existing_event:
                        conn.execute(
                            text(
                                "UPDATE dungeon SET event = :event, summary_info = :summary_info WHERE id = :id"
                            ),
                            {
                                "event": json.dumps(events_for_this_floor),
                                "summary_info": summary_info_value,
                                "id": floor_id,
                            },
                        )
                    else:
                        conn.execute(
                            text(
                                "UPDATE dungeon SET summary_info = :summary_info WHERE id = :id"
                            ),
                            {
                                "summary_info": summary_info_value,
                                "id": floor_id,
                            },
                        )
                    events_list.extend(events_for_this_floor)
        except Exception as e:
            print(f"[ERROR] entrance 트랜잭션 실패: {e}")
            raise
        return {
            "first_player_id": player_ids[0] if player_ids else 0,
            "floor_ids": floor_ids,
            "events": events_list,
        }

    def next_floor_entrance(
        self,
        player_ids: List[str],
        heroine_ids: List[int],
        raw_map: Dict[str, Any],
        heroine_data: Optional[List[Dict[str, Any]]] = None,
        used_events: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        nextfloor에서 n+1층 raw_map을 받으면, 해당 층 row가 없으면 생성하고, 이벤트/summary_info도 즉시 생성해서 저장.
        """
        events_list = []
        used_events = used_events or []
        try:
            with self.repo.engine.begin() as conn:
                normalized_raw_map = _normalize_room_keys(raw_map)
                # 항상 player_ids, heroine_ids를 주입하여 DB에 반영
                normalized_raw_map["player_ids"] = [str(pid) for pid in player_ids]
                normalized_raw_map["heroine_ids"] = list(heroine_ids)

                floor_num = normalized_raw_map.get("floor")
                print(f"[DEBUG] next_floor_entrance: floor_num={floor_num}")
                if not floor_num:
                    raise ValueError("raw_map에 floor 정보가 없습니다.")

                check_sql = text(
                    """
                    SELECT id, event FROM dungeon WHERE floor = :floor AND (
                        player1 = :player_id OR player2 = :player_id OR player3 = :player_id OR player4 = :player_id
                    )
                    """
                )
                player_id = str(player_ids[0]) if player_ids else None
                print(f"[DEBUG] next_floor_entrance: player_id_str={player_id}")
                result = conn.execute(
                    check_sql, {"floor": floor_num, "player_id": player_id}
                )
                row = result.fetchone()
                print(f"[DEBUG] next_floor_entrance: select row={row}")
                if row:
                    floor_id = row[0]
                    existing_event = row[1]
                    print(
                        f"[DEBUG] next_floor_entrance: row exists, floor_id={floor_id}"
                    )
                else:
                    print(
                        f"[DEBUG] next_floor_entrance: inserting new floor {floor_num}"
                    )
                    floor_id = self._insert_dungeon_in_transaction(
                        conn, floor=floor_num, raw_map=normalized_raw_map
                    )
                    print(f"[DEBUG] next_floor_entrance: inserted floor_id={floor_id}")
                    existing_event = None

                # 이벤트 생성 (이벤트 방이 있는 경우에만)
                event_rooms = [
                    room
                    for room in normalized_raw_map.get("rooms", [])
                    if room.get("room_type") == "event"
                    or room.get("event_type", 0) != 0
                ]
                print(f"[DEBUG] next_floor_entrance: event_rooms={event_rooms}")
                events_for_this_floor = []
                # 멀티 히로인/플레이어 지원: 각 이벤트룸마다 매칭되는 히로인/플레이어 데이터 사용
                normalized_heroines = []
                if heroine_data:
                    # If int list, pad or trim to match heroine_ids length
                    if all(isinstance(h, int) for h in heroine_data):
                        # Pad heroine_data if shorter than heroine_ids
                        padded = list(heroine_data)[:]
                        while len(padded) < len(heroine_ids):
                            padded.append(0)
                        for hid, mp in zip(heroine_ids, padded):
                            normalized_heroines.append(
                                {"heroine_id": hid, "memory_progress": mp}
                            )
                    elif isinstance(heroine_data, list):
                        for h in heroine_data:
                            normalized_heroines.append(_normalize_heroine_data(h))
                    else:
                        normalized_heroines.append(
                            _normalize_heroine_data(heroine_data)
                        )
                # Defensive: if normalized_heroines is empty, raise clear error
                if not normalized_heroines:
                    raise ValueError(
                        "heroineData가 비어 있거나 유효하지 않습니다. (nextfloor)"
                    )
                for room in event_rooms:
                    room_id = room.get("room_id")
                    # 대표 히로인/플레이어로 메인 이벤트 생성 (is_personal 여부 확인)
                    main_event_data = self._create_event_for_floor(
                        heroine_data=normalized_heroines[0],
                        player_id=player_ids[0] if player_ids else None,
                        next_floor=floor_num,
                        used_events=used_events,
                        room_id=room_id,
                    )
                    if not main_event_data:
                        continue
                    main_event_data["floor"] = floor_num
                    # 개별 이벤트면 각 히로인/플레이어별 내러티브 생성
                    if main_event_data.get("is_personal", False):
                        heroine_narratives = []
                        for player_id, heroine in zip(player_ids, normalized_heroines):
                            indiv_event = self._create_event_for_floor(
                                heroine_data=heroine,
                                player_id=player_id,
                                next_floor=floor_num,
                                used_events=used_events,
                                room_id=room_id,
                            )
                            if indiv_event:
                                heroine_narratives.append(
                                    {
                                        "playerId": player_id,
                                        "heroineId": heroine["heroine_id"],
                                        "memoryProgress": heroine["memory_progress"],
                                        "narrative": indiv_event.get(
                                            "scenario_narrative", ""
                                        ),
                                    }
                                )
                        main_event_data["heroineNarratives"] = heroine_narratives
                    events_for_this_floor.append(main_event_data)
                    used_events.append(main_event_data)

                summary_info_value = self._generate_raw_map_summary(normalized_raw_map)
                # event/summary_info만 항상 업데이트, raw_map은 새 row(INSERT)일 때만 저장
                if row:
                    # 기존 row: raw_map은 건드리지 않음
                    conn.execute(
                        text(
                            "UPDATE dungeon SET event = :event, summary_info = :summary_info WHERE id = :id"
                        ),
                        {
                            "event": json.dumps(events_for_this_floor),
                            "summary_info": summary_info_value,
                            "id": floor_id,
                        },
                    )
                else:
                    # 새 row: raw_map 포함 전체 저장 (INSERT 내부에서 처리)
                    conn.execute(
                        text(
                            "UPDATE dungeon SET raw_map = :raw_map, event = :event, summary_info = :summary_info WHERE id = :id"
                        ),
                        {
                            "raw_map": json.dumps(normalized_raw_map),
                            "event": json.dumps(events_for_this_floor),
                            "summary_info": summary_info_value,
                            "id": floor_id,
                        },
                    )
                print(f"[DEBUG] next_floor_entrance: updated dungeon row id={floor_id}")
                events_list.extend(events_for_this_floor)
            print(
                f"[DEBUG] next_floor_entrance: returning floor_id={floor_id}, events={events_list}"
            )
            return {
                "floor_id": floor_id,
                "events": events_list,
            }
        except Exception as e:
            print(f"[ERROR] next_floor_entrance 트랜잭션 실패: {e}")
            raise

    def _insert_dungeon_in_transaction(
        self, conn, floor: int, raw_map: Dict[str, Any]
    ) -> int:
        """트랜잭션 내에서 던전 삽입 (연결 재사용)"""

        raw_map_dict = raw_map if isinstance(raw_map, dict) else json.loads(raw_map)
        player_ids = [str(pid) for pid in raw_map_dict.get("player_ids", [])]
        heroine_ids = raw_map_dict.get("heroine_ids", [])

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
        balanced_map_value = raw_map_json if floor == 1 else None

        # floor 1일 때 raw_map 기반 summary_info 생성
        summary_info_value = ""
        if floor == 1:
            summary_info_value = self._generate_raw_map_summary(raw_map_dict)

        params = {
            "floor": floor,
            "raw_map": raw_map_json,
            "balanced_map": balanced_map_value,
            "is_finishing": False,
            "summary_info": summary_info_value,
            "player1": player_with_heroine[0][0],
            "player2": player_with_heroine[1][0],
            "player3": player_with_heroine[2][0],
            "player4": player_with_heroine[3][0],
            "heroine1": player_with_heroine[0][1],
            "heroine2": player_with_heroine[1][1],
            "heroine3": player_with_heroine[2][1],
            "heroine4": player_with_heroine[3][1],
        }

        result = conn.execute(text(sql), params)
        return result.fetchone()[0]

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

            with self.repo.engine.begin() as conn:
                conn.execute(
                    text("UPDATE dungeon SET raw_map = :raw_map WHERE id = :id"),
                    {"raw_map": json.dumps(normalized_raw_map), "id": dungeon_id},
                )
            return True
        except Exception as e:
            print(f"[ERROR] raw_map 업데이트 실패: {e}")
            return False

    def update_raw_map_and_event_for_floor(
        self, first_player_id: str, floor: int, raw_map: Dict[str, Any], event: Any
    ) -> bool:
        try:

            with self.repo.engine.begin() as conn:
                # 해당 플레이어의 진행 중인 던전 중 floor에 해당하는 row 찾기
                sql = text(
                    """
                    SELECT id FROM dungeon WHERE floor = :floor AND (
                        player1 = :player_id OR player2 = :player_id OR player3 = :player_id OR player4 = :player_id
                    )
                    """
                )
                player_id_str = (
                    str(first_player_id) if first_player_id is not None else None
                )
                result = conn.execute(sql, {"floor": floor, "player_id": player_id_str})
                row = result.fetchone()
                if not row:
                    print(
                        f"[ERROR] 해당 플레이어와 층에 대한 던전 row를 찾을 수 없음: player_id={first_player_id}, floor={floor}"
                    )
                    return False
                dungeon_id = row[0]
                # raw_map, event 업데이트
                update_sql = text(
                    """
                    UPDATE dungeon SET raw_map = :raw_map, event = :event WHERE id = :dungeon_id
                    """
                )
                conn.execute(
                    update_sql,
                    {
                        "raw_map": (
                            json.dumps(raw_map)
                            if isinstance(raw_map, (dict, list))
                            else raw_map
                        ),
                        "event": (
                            json.dumps(event)
                            if isinstance(event, (dict, list))
                            else event
                        ),
                        "dungeon_id": dungeon_id,
                    },
                )
            return True
        except Exception as e:
            print(f"[ERROR] update_raw_map_and_event_for_floor 실패: {e}")
            return False

    # ============================================================
    # 2-1. Summary Info 생성 헬퍼
    # ============================================================
    def _generate_raw_map_summary(self, raw_map: Dict[str, Any]) -> str:
        """
        Raw Map 정보로부터 간단한 요약 정보 생성 (1층용)
        """
        rooms = raw_map.get("rooms", [])
        rooms_count = len(rooms)

        room_types = {}
        total_monsters = 0
        event_room_ids = []

        for room in rooms:
            r_type = room.get("room_type", "unknown")
            room_types[r_type] = room_types.get(r_type, 0) + 1

            monsters = room.get("monsters", [])
            total_monsters += len(monsters)

            # 이벤트 방 확인
            if r_type == "event" or room.get("event_type", 0) != 0:
                event_room_ids.append(room.get("room_id"))

        type_summary = ", ".join([f"{k}: {v}" for k, v in room_types.items()])

        event_summary = "없음"
        if event_room_ids:
            event_summary = (
                f"{len(event_room_ids)}곳 (Room {', '.join(map(str, event_room_ids))})"
            )

        summary = (
            f"던전 1층 진입.\n"
            f"- 총 방 개수: {rooms_count}\n"
            f"- 방 구성: {type_summary}\n"
            f"- 감지된 몬스터 수: {total_monsters}\n"
            f"- 감지된 이벤트 지점: {event_summary}\n"
        )
        return summary

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
        first_player_id: str,
        player_data_list: List[Dict[str, Any]],
        monster_db: Dict[str, Any],
        used_events: List[Any] = None,
    ) -> Dict[str, Any]:
        """
        Args:
            first_player_id: 방장 ID (던전 식별용)
            player_data_list: 플레이어별 데이터 리스트 [{playerId, heroineData, heroineStat, ...}]
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
            host_data_wrapper = None
            for pd in player_data_list:
                # pd가 dict인지 확인
                if not isinstance(pd, dict):
                    continue

                h_data = pd.get("heroineData", {})
                if not isinstance(h_data, dict):
                    continue

                if h_data.get("playerId") == first_player_id:
                    host_data_wrapper = pd
                    break

            if not host_data_wrapper:
                host_data_wrapper = (
                    player_data_list[0]
                    if player_data_list and isinstance(player_data_list[0], dict)
                    else {}
                )

            host_data = (
                host_data_wrapper.get("heroineData", {})
                if isinstance(host_data_wrapper, dict)
                else {}
            )

            # heroine_data 정규화
            heroine_data = _normalize_heroine_data(host_data)

            heroine_stat = host_data.get("heroineStat", {})
            heroine_memories = host_data.get("heroineMemories", [])
            dungeon_player_data = host_data.get("dungeonPlayerData", {})

            # 1. 현재 진행 중인 던전 찾기 (first_player_id로)
            unfinished = self.repo.get_unfinished_dungeons(player_ids=[first_player_id])
            if not unfinished:
                return {
                    "success": False,
                    "error": f"플레이어 {first_player_id}의 진행 중인 던전을 찾을 수 없습니다",
                }

            dungeon_id = unfinished.get("id")
            current_floor = unfinished.get("floor", 1)

            # DB에서 현재 던전 조회 (연결 블록 외부에서)

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
            print(f"[DEBUG] balance_dungeon - raw_map keys: {raw_map.keys()}")

            print(f"\n[DEBUG] 던전 {dungeon_id} raw_map 읽음:")
            print(f"  - rooms count: {len(raw_map.get('rooms', []))}")
            for i, room in enumerate(raw_map.get("rooms", [])):
                monsters = room.get("monsters", [])
                print(
                    f"  - room {i}: type={room.get('room_type')}, monsters={monsters}"
                )
            # 다음 층 ID 조회
            next_floor = current_floor + 1
            next_floor_id = None

            # player_ids 추출
            player_ids_list = raw_map.get("player_ids") or raw_map.get("playerIds", [])

            # player_ids_list가 정수형 리스트일 경우 처리
            if isinstance(player_ids_list, int):
                player_ids_list = [player_ids_list]

            with self.repo.engine.connect() as conn:
                if (
                    player_ids_list
                    and isinstance(player_ids_list, list)
                    and len(player_ids_list) > 0
                ):
                    first_player_id_str = str(player_ids_list[0])
                    next_dungeon_query = """
                        SELECT id FROM dungeon 
                        WHERE floor = :next_floor 
                        AND player1 = :player1
                        LIMIT 1
                    """
                    next_result = conn.execute(
                        text(next_dungeon_query),
                        {"next_floor": next_floor, "player1": first_player_id_str},
                    ).fetchone()

                    if next_result:
                        next_floor_id = next_result[0]

            if not next_floor_id:
                return {
                    "success": False,
                    "error": f"다음 층({next_floor}층)을 찾을 수 없습니다.",
                }

            # 다음 층을 위한 raw_map 생성 (현재 층 구조 복사 + 몬스터 초기화)
            next_floor_raw_map = json.loads(json.dumps(raw_map))  # Deep copy
            for room in next_floor_raw_map.get("rooms", []):
                room["monsters"] = []

            agent_state = {
                "dungeon_base_data": {
                    "dungeon_id": next_floor_id,
                    "floor_count": next_floor,
                    "rooms": next_floor_raw_map.get("rooms", []),
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
                # 이벤트 노드 생략 플래그 (던전 밸런스 API에서는 True)
                "skip_event_node": True,
            }

            # Super Agent 실행 (연결 블록 외부에서 - DB 연결 점유 안함)
            print(
                f"\n[Dungeon {next_floor_id}] Super Agent 실행 중 (Floor {next_floor})..."
            )
            dungeon_graph = get_dungeon_graph()
            agent_result = dungeon_graph.invoke(agent_state)

            final_json = agent_result.get("final_dungeon_json", {})
            balanced_map_data = final_json.get("dungeon_data", {})

            # DEBUG: agent_result 구조 출력
            print(f"\n[DEBUG] final_json keys: {list(final_json.keys())}")
            print(f"[DEBUG] balanced_map_data keys: {list(balanced_map_data.keys())}")
            print(
                f"[DEBUG] balanced_map_data.get('rooms'): {len(balanced_map_data.get('rooms', []))} rooms"
            )
            print(f"[DEBUG] events keys: {list(final_json.get('events', {}).keys())}")
            print(f"[DEBUG] monster_stats: {final_json.get('monster_stats', {})}")

            # summary_info 생성 (다음 층 데이터 기반)
            summary_info = self._generate_summary_info(balanced_map_data, final_json)

            next_floor_events = None

            # DB 업데이트 (단일 연결 블록으로 통합)
            with self.repo.engine.begin() as conn:
                # 다음 층의 raw_map이 이미 존재하는지 확인 (NULL/빈 값만 업데이트)
                check_sql = text("SELECT raw_map FROM dungeon WHERE id = :id")
                result = conn.execute(check_sql, {"id": next_floor_id}).fetchone()
                raw_map_exists = False
                if result:
                    existing_raw_map = result[0]
                    if existing_raw_map not in [None, "", "{}", "null"]:
                        raw_map_exists = True

                update_params = {
                    "balanced_map": json.dumps(balanced_map_data),
                    "summary_info": summary_info,
                    "id": next_floor_id,
                }
                update_sql = None
                if not raw_map_exists:
                    update_params["raw_map"] = json.dumps(next_floor_raw_map)
                    if next_floor >= 3 or (next_floor_events not in [None, [], {}]):
                        update_params["event"] = json.dumps(next_floor_events)
                        update_sql = text(
                            "UPDATE dungeon SET raw_map = :raw_map, balanced_map = :balanced_map, event = :event, summary_info = :summary_info WHERE id = :id"
                        )
                    else:
                        update_sql = text(
                            "UPDATE dungeon SET raw_map = :raw_map, balanced_map = :balanced_map, summary_info = :summary_info WHERE id = :id"
                        )
                else:
                    # raw_map이 이미 있으면 raw_map은 건드리지 않음
                    if next_floor >= 3 or (next_floor_events not in [None, [], {}]):
                        update_params["event"] = json.dumps(next_floor_events)
                        update_sql = text(
                            "UPDATE dungeon SET balanced_map = :balanced_map, event = :event, summary_info = :summary_info WHERE id = :id"
                        )
                    else:
                        update_sql = text(
                            "UPDATE dungeon SET balanced_map = :balanced_map, summary_info = :summary_info WHERE id = :id"
                        )
                conn.execute(update_sql, update_params)
                print(
                    f"[SUCCESS] 다음 층({next_floor}층) 밸런싱 및 저장 완료 (raw_map {'업데이트' if not raw_map_exists else '유지'})"
                )

            # 몬스터 배치 정보 추출 (roomId, monsterId, count) - 다음 층 기준
            monster_placements = []
            for room in balanced_map_data.get("rooms", []):
                room_id = room.get("room_id")
                monsters = room.get("monsters", [])

                # 몬스터 ID별 카운트
                monster_counts = {}
                for m in monsters:
                    # m이 dict인지 int인지 확인
                    if isinstance(m, dict):
                        m_id = m.get("monster_id")
                    elif isinstance(m, int):
                        m_id = m
                    else:
                        continue  # 알 수 없는 형식이면 스킵

                    if m_id is not None:
                        monster_counts[m_id] = monster_counts.get(m_id, 0) + 1

                for m_id, count in monster_counts.items():
                    monster_placements.append(
                        {"roomId": room_id, "monsterId": m_id, "count": count}
                    )

            return {
                "success": True,
                "dungeon_id": dungeon_id,  # 요청한 던전 ID (현재 층)
                "agent_result": final_json,
                "summary": summary_info,
                "monster_placements": monster_placements,
                "next_floor_event": next_floor_events,
            }
        except Exception as e:
            print(f"[ERROR] 던전 밸런싱 실패: {e}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
            }

    # ============================================================
    # 4. 다음 층 준비 (Prepare Next Floor - 이벤트 생성)
    # ============================================================
    def prepare_next_floor(
        self,
        first_player_id: str,
        heroine_data: Dict[str, Any],
        used_events: List[Any] = None,
    ) -> Dict[str, Any]:
        try:
            # 1. 현재 진행 중인 던전 찾기
            unfinished = self.repo.get_unfinished_dungeons(player_ids=[first_player_id])
            if not unfinished:
                return {
                    "success": False,
                    "error": f"플레이어 {first_player_id}의 진행 중인 던전을 찾을 수 없습니다",
                }

            current_floor = unfinished.get("floor", 1)
            next_floor = current_floor + 1

            if next_floor > 3:
                return {
                    "success": False,
                    "error": "더 이상 진행할 층이 없습니다 (최대 3층)",
                }

            # 2. 다음 층 던전 ID 찾기

            next_floor_id = None

            with self.repo.engine.begin() as conn:
                next_dungeon_query = """
                    SELECT id FROM dungeon 
                    WHERE floor = :next_floor 
                    AND player1 = :player1
                    LIMIT 1
                """
                next_result = conn.execute(
                    text(next_dungeon_query),
                    {"next_floor": next_floor, "player1": str(first_player_id)},
                ).fetchone()

                if not next_result:
                    return {
                        "success": False,
                        "error": f"다음 층({next_floor}층) 던전을 찾을 수 없습니다",
                    }

                next_floor_id = next_result[0]

                # 3. 다음 층 이벤트 생성 및 저장
                events = self._create_event_for_floor(
                    heroine_data=heroine_data,
                    next_floor=next_floor,
                    used_events=used_events or [],
                )

                if events:
                    conn.execute(
                        text("UPDATE dungeon SET event = :event WHERE id = :id"),
                        {"event": json.dumps(events), "id": next_floor_id},
                    )

            return {"success": True, "next_floor_id": next_floor_id, "events": events}

        except Exception as e:
            print(f"[ERROR] 다음 층 준비 실패: {e}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
            }

    # ============================================================
    # 5. 층 완료 (Clear - is_finishing = TRUE)
    # ============================================================
    def clear_floor(self, player_ids: List[str]) -> Dict[str, Any]:
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
    def get_status(self, player_ids: List[str]) -> Dict[str, Any]:
        """플레이어의 현재 진행 중인 던전 상태 조회"""
        return self.repo.get_unfinished_dungeons(player_ids=player_ids)

    def get_all(self) -> List[Dict[str, Any]]:
        """모든 던전 조회 (관리자용)"""
        try:

            with self.repo.engine.connect() as conn:
                rows = conn.execute(
                    text("SELECT * FROM dungeon ORDER BY id DESC")
                ).fetchall()
                return [dict(row._mapping) for row in rows]
        except Exception as e:
            print(f"[ERROR] 던전 조회 실패: {e}")
            return []

    # ============================================================
    # 6. 이벤트 선택 (Event Select)
    # ============================================================
    def select_event(
        self, first_player_id: str, selecting_player_id: str, room_id: int, choice: str
    ) -> Dict[str, Any]:
        """
        플레이어의 이벤트 선택 처리
        """
        try:
            # 1. 현재 진행 중인 던전 찾기
            unfinished = self.repo.get_unfinished_dungeons(player_ids=[first_player_id])
            if not unfinished:
                return {
                    "success": False,
                    "error": f"플레이어 {first_player_id}의 진행 중인 던전을 찾을 수 없습니다",
                }

            dungeon_id = unfinished.get("id")

            # 2. DB에서 이벤트 정보 조회
            event_data = None

            with self.repo.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT event FROM dungeon WHERE id = :id"), {"id": dungeon_id}
                ).fetchone()

                if result and result[0]:
                    event_val = result[0]
                    event_data = (
                        json.loads(event_val)
                        if isinstance(event_val, str)
                        else event_val
                    )

            if not event_data:
                return {
                    "success": False,
                    "error": "이벤트 정보를 찾을 수 없습니다",
                }

            # 3. 해당 방의 이벤트 찾기
            target_event = None

            # DEBUG: 이벤트 데이터 확인
            print(
                f"[DEBUG] select_event - dungeon_id: {dungeon_id}, target room_id: {room_id}"
            )

            if isinstance(event_data, list):
                for evt in event_data:
                    # 타입 안전 비교 (str 변환)
                    # room_id(snake_case) 또는 roomId(camelCase) 모두 확인
                    evt_room_id = evt.get("room_id")
                    if evt_room_id is None:
                        evt_room_id = evt.get("roomId")

                    if str(evt_room_id) == str(room_id):
                        target_event = evt
                        break
            elif isinstance(event_data, dict):
                evt_room_id = event_data.get("room_id")
                if evt_room_id is None:
                    evt_room_id = event_data.get("roomId")

                if str(evt_room_id) == str(room_id):
                    target_event = event_data

            if not target_event:
                # 디버깅을 위해 현재 로드된 이벤트들의 room_id 목록을 에러 메시지에 포함
                loaded_room_ids = []
                if isinstance(event_data, list):
                    loaded_room_ids = [
                        e.get("room_id") or e.get("roomId") for e in event_data
                    ]
                elif isinstance(event_data, dict):
                    loaded_room_ids = [
                        event_data.get("room_id") or event_data.get("roomId")
                    ]

                print(f"[ERROR] Event not found. Loaded room_ids: {loaded_room_ids}")

                return {
                    "success": False,
                    "error": f"Room {room_id}에 해당하는 이벤트를 찾을 수 없습니다 (Loaded: {loaded_room_ids})",
                }

            # 4. 선택지에 따른 결과 도출 (LLM 사용)
            from langchain.chat_models import init_chat_model
            from enums.LLM import LLM
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = init_chat_model(model=LLM.GPT5_MINI, temperature=0.7)

            scenario_narrative = target_event.get("scenario_narrative", "")
            choices = target_event.get("choices", [])

            matched_action = ""
            is_unexpected = False

            # 선택지가 있는 경우 분류 로직 수행
            if choices:
                options_text = ""
                for idx, c in enumerate(choices):
                    options_text += f"{idx}. {c.get('action', '')}\n"

                classification_prompt = f"""
                [상황]
                {scenario_narrative}

                [가능한 선택지]
                {options_text}

                [플레이어 입력]
                {choice}

                플레이어의 입력이 위 [가능한 선택지] 중 어느 것과 가장 유사한지 판단해.
                1. 선택지와 의미가 유사하면 해당 번호(0, 1, 2...)를 반환해.
                2. 만약 선택지에 없는 돌발 행동이거나, 적대적인 행동, 혹은 전혀 다른 행동이라면 "UNEXPECTED"라고 반환해.

                오직 숫자 혹은 "UNEXPECTED" 만 출력해.
                """
                # 분류 실행
                try:
                    class_response = llm.invoke(
                        [HumanMessage(content=classification_prompt)]
                    )
                    class_result = class_response.content.strip()
                    print(f"[DEBUG] Event Classification Result: {class_result}")

                    if class_result.isdigit():
                        idx = int(class_result)
                        if 0 <= idx < len(choices):
                            selected = choices[idx]
                            matched_action = selected.get("action")
                        else:
                            is_unexpected = True
                    else:
                        is_unexpected = True
                except Exception as e:
                    print(f"[ERROR] 분류 중 오류 발생: {e}")
                    is_unexpected = True

            # 결과 서술 생성
            if is_unexpected:
                # 돌발 행동에 대한 패널티 및 서술
                penalty_id = "penalty_unexpected_action"  # 기본 패널티 ID 부여
                prompt = f"""
                [상황]
                {scenario_narrative}

                [플레이어 돌발 행동]
                {choice}

                플레이어가 예상치 못한 행동을 했습니다. 
                이 행동은 상황에 맞지 않거나 위험한 행동일 수 있습니다.
                이에 대한 부정적인 결과나 당황스러운 상황을 2~3문장으로 묘사해줘.
                플레이어에게 직접 이야기하듯이 서술해.
                """
            else:
                # 매칭된 행동에 대한 서술
                prompt = f"""
                [상황]
                {scenario_narrative}

                [플레이어 선택]
                {choice} (의도: {matched_action})

                위 상황에서 플레이어가 선택한 행동에 대한 결과를 2~3문장으로 묘사해줘. 
                플레이어에게 직접 이야기하듯이 서술해. (예: "당신은 ~했습니다. 그 결과...")
                """

            response = llm.invoke([HumanMessage(content=prompt)])
            outcome = response.content

            return {
                "success": True,
                "outcome": outcome,
            }

        except Exception as e:
            print(f"[ERROR] 이벤트 선택 처리 실패: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ============================================================
    # 7. 이벤트 생성 및 저장 헬퍼 메서드
    # ============================================================
    def _create_event_for_floor(
        self,
        heroine_data: Dict[str, Any],
        player_id: int = None,
        next_floor: int = 1,
        used_events: List[Any] = None,
        room_id: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        특정 층에 대한 이벤트 생성
        """

        try:
            print(
                f"[DEBUG] _create_event_for_floor: player_id={player_id}, heroine_data={heroine_data}"
            )
            from agents.dungeon.event.dungeon_event_agent import graph_builder
            from agents.dungeon.dungeon_state import DungeonEventState

            # 이벤트 에이전트 실행
            event_state: DungeonEventState = {
                "messages": [],
                "heroine_data": heroine_data,
                "player_id": player_id,
                "heroine_memories": [],
                "event_room": room_id,
                "next_floor": next_floor,
                "used_events": used_events,
                "selected_main_event": "",
                "sub_event": "",
                "final_answer": "",
            }
            print(f"[DEBUG] event_state: {event_state}")
            event_graph = graph_builder.compile()
            event_result = event_graph.invoke(event_state)

            # 전체 이벤트 JSON 구성
            main_event = event_result.get("selected_main_event", {})
            sub_event = event_result.get("sub_event", {})

            # sub_event가 dict가 아닐 수 있음 (문자열일 경우 처리)
            scenario_narrative = ""
            choices = []
            expected_outcome = ""

            if isinstance(sub_event, dict):
                scenario_narrative = sub_event.get("narrative", "")
                choices = sub_event.get("choices", [])
                expected_outcome = sub_event.get("expected_outcome", "")

            event_json = {
                "room_id": room_id,
                "event_type": main_event.get("event_id", 0),
                "event_title": main_event.get("title", ""),
                "event_code": main_event.get("event_code", ""),
                "scenario_text": main_event.get("scenario_text", ""),
                "scenario_narrative": scenario_narrative,
                "choices": choices,
                "expected_outcome": expected_outcome,
                "player_id": player_id,
                "is_personal": main_event.get("is_personal", False),
                "floor": next_floor,
            }

            return event_json

        except Exception as e:
            print(f"[ERROR] 이벤트 생성 실패: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _save_event_to_db(self, dungeon_id: int, event_data: Any) -> bool:
        """
        생성된 이벤트 JSON을 DB의 event 컬럼에 저장
        """
        if event_data is None:
            print(
                f"[WARNING] 이벤트 데이터가 None 입니다.저장을 건너뜁니다. (dungeon_id={dungeon_id}"
            )
            return False
        try:
            # 리스트인지 단일 객체인지 확인하여 JSON 변환
            event_json_str = (
                json.dumps(event_data)
                if isinstance(event_data, (dict, list))
                else event_data
            )

            with self.repo.engine.begin() as conn:
                conn.execute(
                    text("UPDATE dungeon SET event = :event WHERE id = :id"),
                    {"event": event_json_str, "id": dungeon_id},
                )

            print(f"[SUCCESS] 이벤트가 던전 {dungeon_id}에 저장되었습니다.")
            return True

        except Exception as e:
            print(f"[ERROR] 이벤트 DB 저장 실패: {e}")
            return False


# ============================================================
# 서비스 초기화 (매 요청마다 인스턴스 생성)
# ============================================================
def get_dungeon_service() -> DungeonService:
    """항상 새로운 DungeonService 인스턴스 반환"""
    return DungeonService()
