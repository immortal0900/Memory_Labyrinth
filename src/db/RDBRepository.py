import json
from typing import List, Any, Dict
from sqlalchemy import create_engine, text
from db.config import CONNECTION_URL
from enums.EmbeddingModel import EmbeddingModel

class RDBRepository:
    def __init__(self):
        self.db_url = CONNECTION_URL
        self.engine = create_engine(self.db_url)
        

    def select_first_row(self, heroine_id, memory_progress):
        """
        테이블에서 id 오름차순 기준으로 가장 처음 1개 row를 반환합니다.
        """
        
        sql = f"""SELECT *
    FROM heroine_memory
    WHERE heroine_id = {heroine_id}
    AND memory_progress BETWEEN 10 AND {memory_progress};"""

        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            row = result.fetchone()

            return dict(row._mapping) if row else None
        