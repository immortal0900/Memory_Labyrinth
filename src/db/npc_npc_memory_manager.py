"""NPC-NPC 장기기억 + 체크포인트 매니저

목표:
- npc_npc_checkpoints: NPC-NPC 대화 전체 기록
- npc_npc_memories: NPC-NPC 장기기억(핵심)

주의:
- (npcA, npcB) 쌍은 항상 (min,max)로 저장합니다.
- interrupted_turn 이후의 장기기억은 invalid_at으로 무효화합니다.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import init_chat_model

from db.config import CONNECTION_URL


def _normalize_pair(a: int, b: int) -> Tuple[int, int]:
    if a < b:
        return a, b
    return b, a


class NpcNpcMemoryManager:
    """NPC-NPC 저장/조회 담당 클래스"""

    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        if not CONNECTION_URL:
            raise RuntimeError("DATABASE_URL이 비어있습니다 (.env 확인)")

        self.engine = create_engine(CONNECTION_URL, pool_pre_ping=True)
        self.embeddings = OpenAIEmbeddings(model=embedding_model)

        # 아주 단순한 fact 추출용 (필요 최소)
        self.extract_llm = init_chat_model(model="gpt-4o-mini", temperature=0)

    # ============================================
    # 체크포인트 저장/조회
    # ============================================

    def save_checkpoint(
        self,
        user_id: int,
        npc1_id: int,
        npc2_id: int,
        situation: Optional[str],
        conversation: List[Dict[str, Any]],
    ) -> str:
        heroine_id_1, heroine_id_2 = _normalize_pair(npc1_id, npc2_id)
        checkpoint_id = str(uuid.uuid4())

        sql = text(
            """
            INSERT INTO npc_npc_checkpoints (
                id, user_id, heroine_id_1, heroine_id_2,
                situation, conversation, turn_count, interrupted_turn,
                created_at, updated_at, last_turn_at
            )
            VALUES (
                :id, :user_id, :heroine_id_1, :heroine_id_2,
                :situation, CAST(:conversation AS jsonb), :turn_count, NULL,
                NOW(), NOW(), NOW()
            )
            """
        )

        with self.engine.connect() as conn:
            conn.execute(
                sql,
                {
                    "id": checkpoint_id,
                    "user_id": int(user_id),
                    "heroine_id_1": heroine_id_1,
                    "heroine_id_2": heroine_id_2,
                    "situation": situation,
                    "conversation": json.dumps(conversation, ensure_ascii=False),
                    "turn_count": len(conversation),
                },
            )
            conn.commit()

        return checkpoint_id

    def get_checkpoints(
        self,
        user_id: int,
        npc1_id: Optional[int] = None,
        npc2_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        where_pair = ""
        params: Dict[str, Any] = {"user_id": int(user_id), "limit": int(limit)}

        if npc1_id is not None and npc2_id is not None:
            heroine_id_1, heroine_id_2 = _normalize_pair(npc1_id, npc2_id)
            where_pair = (
                "AND heroine_id_1 = :heroine_id_1 AND heroine_id_2 = :heroine_id_2"
            )
            params["heroine_id_1"] = heroine_id_1
            params["heroine_id_2"] = heroine_id_2

        sql = text(
            f"""
            SELECT id, user_id, heroine_id_1, heroine_id_2, situation,
                   conversation, turn_count, interrupted_turn, created_at
            FROM npc_npc_checkpoints
            WHERE user_id = :user_id
            {where_pair}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )

        results: List[Dict[str, Any]] = []
        with self.engine.connect() as conn:
            for row in conn.execute(sql, params):
                results.append(
                    {
                        "id": str(row.id),
                        "user_id": row.user_id,
                        "heroine_id_1": row.heroine_id_1,
                        "heroine_id_2": row.heroine_id_2,
                        "situation": row.situation,
                        "conversation": row.conversation,
                        "turn_count": row.turn_count,
                        "interrupted_turn": row.interrupted_turn,
                        "created_at": (
                            row.created_at.isoformat() if row.created_at else None
                        ),
                    }
                )

        return results

    def truncate_checkpoint(
        self, checkpoint_id: str, interrupted_turn: int
    ) -> Optional[Dict[str, Any]]:
        # 1) 조회
        sql_select = text(
            """
            SELECT conversation
            FROM npc_npc_checkpoints
            WHERE id = :id
            """
        )

        with self.engine.connect() as conn:
            row = conn.execute(sql_select, {"id": checkpoint_id}).fetchone()
            if not row:
                return None

            conversation = row.conversation or []
            truncated = conversation[:interrupted_turn]

            sql_update = text(
                """
                UPDATE npc_npc_checkpoints
                SET conversation = CAST(:conversation AS jsonb),
                    turn_count = :turn_count,
                    interrupted_turn = :interrupted_turn,
                    last_turn_at = NOW()
                WHERE id = :id
                """
            )

            conn.execute(
                sql_update,
                {
                    "id": checkpoint_id,
                    "conversation": json.dumps(truncated, ensure_ascii=False),
                    "turn_count": len(truncated),
                    "interrupted_turn": int(interrupted_turn),
                },
            )
            conn.commit()

        return {
            "id": checkpoint_id,
            "conversation": truncated,
            "turn_count": len(truncated),
        }

    # ============================================
    # 장기기억 저장/조회
    # ============================================

    async def extract_facts(self, conversation_text: str) -> List[Dict[str, Any]]:
        """대화에서 장기기억으로 남길 fact를 아주 단순하게 추출합니다."""

        prompt = f"""다음은 NPC 두 명의 대화입니다.

[대화]
{conversation_text}

[요청]
장기기억으로 저장할 만한 핵심 사실만 0~5개 추출하세요.
너무 사소한 잡담은 제외하세요.

[출력]
반드시 JSON 배열로만 출력하세요.
각 요소는 아래 키를 포함하세요:
- content: 사실 내용 (짧게)
- importance: 1~10 숫자
"""

        resp = await self.extract_llm.ainvoke(prompt)
        content = resp.content

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            data = json.loads(content.strip())
        except Exception:
            data = []

        facts: List[Dict[str, Any]] = []
        for item in data:
            fact_content = item.get("content")
            if not fact_content:
                continue
            importance = item.get("importance")
            if not isinstance(importance, int):
                importance = 5
            facts.append({"content": fact_content, "importance": importance})

        return facts

    def save_turn_memories(
        self,
        user_id: int,
        npc1_id: int,
        npc2_id: int,
        checkpoint_id: str,
        situation: Optional[str],
        conversation: List[Dict[str, Any]],
    ) -> int:
        """턴 단위로 장기기억을 저장합니다(가장 단순한 형태).

        - speaker_id는 각 턴의 speaker_id를 사용
        - subject_id는 반대 NPC로 저장
        """
        heroine_id_1, heroine_id_2 = _normalize_pair(npc1_id, npc2_id)

        inserted = 0
        with self.engine.connect() as conn:
            for idx, msg in enumerate(conversation):
                speaker_id = msg.get("speaker_id")
                text_content = msg.get("text")
                if speaker_id is None or not text_content:
                    continue

                if int(speaker_id) == int(npc1_id):
                    subject_id = int(npc2_id)
                else:
                    subject_id = int(npc1_id)

                embed = self.embeddings.embed_query(str(text_content))

                sql_insert = text(
                    """
                    INSERT INTO npc_npc_memories (
                        conversation_id, turn_index,
                        user_id, heroine_id_1, heroine_id_2,
                        speaker_id, subject_id,
                        content, content_type,
                        embedding, importance,
                        created_at,
                        metadata
                    )
                    VALUES (
                        :conversation_id, :turn_index,
                        :user_id, :heroine_id_1, :heroine_id_2,
                        :speaker_id, :subject_id,
                        :content, :content_type,
                        CAST(:embedding AS vector), :importance,
                        NOW(),
                        CAST(:metadata AS jsonb)
                    )
                    """
                )

                conn.execute(
                    sql_insert,
                    {
                        "conversation_id": checkpoint_id,
                        "turn_index": idx + 1,
                        "user_id": int(user_id),
                        "heroine_id_1": heroine_id_1,
                        "heroine_id_2": heroine_id_2,
                        "speaker_id": int(speaker_id),
                        "subject_id": int(subject_id),
                        "content": str(text_content),
                        "content_type": "turn",
                        "embedding": str(embed),
                        "importance": 5,
                        "metadata": json.dumps(
                            {"situation": situation}, ensure_ascii=False
                        ),
                    },
                )
                inserted += 1

            conn.commit()

        return inserted

    def invalidate_memories_after_turn(
        self, checkpoint_id: str, interrupted_turn: int
    ) -> int:
        sql = text(
            """
            UPDATE npc_npc_memories
            SET invalid_at = NOW(), updated_at = NOW()
            WHERE conversation_id = :conversation_id
              AND turn_index > :interrupted_turn
              AND invalid_at IS NULL
            """
        )

        with self.engine.connect() as conn:
            result = conn.execute(
                sql,
                {
                    "conversation_id": checkpoint_id,
                    "interrupted_turn": int(interrupted_turn),
                },
            )
            conn.commit()

        return result.rowcount

    def search_memories(
        self,
        user_id: int,
        npc1_id: int,
        npc2_id: int,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        heroine_id_1, heroine_id_2 = _normalize_pair(npc1_id, npc2_id)
        query_embedding = self.embeddings.embed_query(query)

        sql = text(
            """
            SELECT * FROM search_npc_npc_memories_hybrid(
                :user_id,
                :heroine_id_1,
                :heroine_id_2,
                :query_text,
                CAST(:query_embedding AS vector),
                :top_k
            )
            """
        )

        results: List[Dict[str, Any]] = []
        with self.engine.connect() as conn:
            for row in conn.execute(
                sql,
                {
                    "user_id": int(user_id),
                    "heroine_id_1": heroine_id_1,
                    "heroine_id_2": heroine_id_2,
                    "query_text": query,
                    "query_embedding": str(query_embedding),
                    "top_k": int(limit),
                },
            ):
                results.append(
                    {
                        "id": str(row.id),
                        "content": row.content,
                        "score": float(row.final_score),
                        "speaker_id": row.speaker_id,
                        "subject_id": row.subject_id,
                        "turn_index": row.turn_index,
                    }
                )

        return results


npc_npc_memory_manager = NpcNpcMemoryManager()
