import json
from typing import List, Any, Dict
from sqlalchemy import create_engine, text
from db.config import CONNECTION_URL
from enums.EmbeddingModel import EmbeddingModel

# 이때 summary_info는 그냥 던전 밸런싱 요약내용을 text로.


class RDBRepository:
    def __init__(self):
        self.db_url = CONNECTION_URL
        self.engine = create_engine(self.db_url)

    def insert_dungeon(self, floor, raw_map):

        # raw_map에서 playerIds와 heroineIds 파싱
        raw_map_dict = raw_map if isinstance(raw_map, dict) else json.loads(raw_map)
        player_ids = raw_map_dict.get("playerIds", [])
        heroine_ids = raw_map_dict.get("heroineIds", [])

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

        # JSON 데이터를 문자열로 변환
        params = {
            "floor": floor,
            "raw_map": (
                json.dumps(raw_map) if isinstance(raw_map, (dict, list)) else raw_map
            ),
            "balanced_map": None,
            "summary_info": None,
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

    def get_unfinished_dungeons(self, player_ids):

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
                raw_map = json.loads(row._mapping["raw_map"])
                row_players = set(map(str, raw_map.get("playerIds", [])))

                if target.issubset(row_players):
                    return dict(row._mapping)

            return None

    def balanced_dungeon(self, balanced_map, dungeon_id, summary_info):
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
                raw_map = json.loads(row._mapping["raw_map"])
                row_players = set(map(str, raw_map.get("playerIds", [])))

                if target.issubset(row_players):
                    dungeon_id = row._mapping["id"]

                    # update
                    conn.execute(
                        text("UPDATE dungeon SET is_finishing = TRUE WHERE id = :id"),
                        {"id": dungeon_id},
                    )
                    conn.commit()

                    # updated row 반환
                    updated = conn.execute(
                        text("SELECT * FROM dungeon WHERE id = :id"), {"id": dungeon_id}
                    ).fetchone()

                    return dict(updated._mapping)

            return None
