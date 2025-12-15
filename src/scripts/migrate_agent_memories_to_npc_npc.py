"""agent_memories -> npc_npc_* 마이그레이션 (1회용)

목표:
- agent_memories의 NPC-NPC 대화/기억을 새 테이블로 옮깁니다.
- 기존 UUID(id)는 그대로 유지합니다.

주의:
- 기존 데이터에는 user_id가 없을 수 있어 기본값 0으로 저장합니다.
- npc_memory에 conversation_id가 없으면 해당 row는 스킵합니다.
"""

import json

from sqlalchemy import create_engine, text

from src.db.config import CONNECTION_URL


def _parse_conv_agent_id(agent_id: str):
    # conv_1_2 형태
    if not agent_id:
        return None

    if not agent_id.startswith("conv_"):
        return None

    parts = agent_id.replace("conv_", "").split("_")
    if len(parts) != 2:
        return None

    try:
        a = int(parts[0])
        b = int(parts[1])
    except ValueError:
        return None

    if a < b:
        return (a, b)
    return (b, a)


def _parse_npc_about_agent_id(agent_id: str):
    # npc_1_about_2 형태
    if not agent_id:
        return None

    if not agent_id.startswith("npc_"):
        return None

    if "_about_" not in agent_id:
        return None

    parts = agent_id.replace("npc_", "").split("_about_")
    if len(parts) != 2:
        return None

    try:
        a = int(parts[0])
        b = int(parts[1])
    except ValueError:
        return None

    if a < b:
        return (a, b)
    return (b, a)


def migrate():
    if not CONNECTION_URL:
        raise RuntimeError("DATABASE_URL이 비어있습니다 (.env 확인)")

    engine = create_engine(CONNECTION_URL, pool_pre_ping=True)

    sql_select = text(
        """
        SELECT id, agent_id, memory_type, content, embedding, importance_score, metadata, created_at
        FROM agent_memories
        WHERE memory_type IN ('npc_conversation', 'npc_memory')
        ORDER BY created_at ASC
        """
    )

    inserted_checkpoints = 0
    inserted_memories = 0
    skipped_memories = 0

    with engine.connect() as conn:
        rows = conn.execute(sql_select).fetchall()

        for row in rows:
            memory_type = row.memory_type
            metadata = row.metadata or {}

            # user_id는 기존 데이터에 없을 수 있어서 0
            user_id = metadata.get("user_id")
            if user_id is None:
                user_id = 0

            if memory_type == "npc_conversation":
                pair = _parse_conv_agent_id(row.agent_id)
                if pair is None:
                    continue

                heroine_id_1, heroine_id_2 = pair

                situation = metadata.get("situation")
                conversation = metadata.get("conversation")
                if conversation is None:
                    conversation = []

                turn_count = metadata.get("turn_count")
                if turn_count is None:
                    turn_count = len(conversation)

                interrupted_turn = metadata.get("interrupted_at")

                sql_insert_checkpoint = text(
                    """
                    INSERT INTO npc_npc_checkpoints (
                        id, user_id, heroine_id_1, heroine_id_2,
                        situation, conversation, turn_count, interrupted_turn,
                        created_at, updated_at, last_turn_at
                    )
                    VALUES (
                        :id, :user_id, :heroine_id_1, :heroine_id_2,
                        :situation, CAST(:conversation AS jsonb), :turn_count, :interrupted_turn,
                        :created_at, NOW(), :last_turn_at
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                )

                conn.execute(
                    sql_insert_checkpoint,
                    {
                        "id": str(row.id),
                        "user_id": int(user_id),
                        "heroine_id_1": heroine_id_1,
                        "heroine_id_2": heroine_id_2,
                        "situation": situation,
                        "conversation": json.dumps(conversation, ensure_ascii=False),
                        "turn_count": int(turn_count),
                        "interrupted_turn": interrupted_turn,
                        "created_at": row.created_at,
                        "last_turn_at": row.created_at,
                    },
                )
                inserted_checkpoints += 1

            if memory_type == "npc_memory":
                pair = _parse_npc_about_agent_id(row.agent_id)
                if pair is None:
                    continue

                heroine_id_1, heroine_id_2 = pair

                # npc_X_about_Y 에서 speaker=X, subject=Y
                # (쌍 정규화는 (min,max), 관점은 별도 컬럼)
                try:
                    speaker_id = int(
                        row.agent_id.replace("npc_", "").split("_about_")[0]
                    )
                    subject_id = int(row.agent_id.split("_about_")[1])
                except Exception:
                    continue

                conversation_id = metadata.get("conversation_id")
                if not conversation_id:
                    skipped_memories += 1
                    continue

                embedding = row.embedding
                if embedding is not None:
                    embedding = str(embedding)

                sql_insert_memory = text(
                    """
                    INSERT INTO npc_npc_memories (
                        id, conversation_id, turn_index,
                        user_id, heroine_id_1, heroine_id_2,
                        speaker_id, subject_id,
                        content, content_type,
                        embedding, importance,
                        created_at, updated_at,
                        metadata
                    )
                    VALUES (
                        :id, :conversation_id, :turn_index,
                        :user_id, :heroine_id_1, :heroine_id_2,
                        :speaker_id, :subject_id,
                        :content, :content_type,
                        CAST(:embedding AS vector), :importance,
                        :created_at, NOW(),
                        CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                )

                conn.execute(
                    sql_insert_memory,
                    {
                        "id": str(row.id),
                        "conversation_id": str(conversation_id),
                        "turn_index": 0,
                        "user_id": int(user_id),
                        "heroine_id_1": heroine_id_1,
                        "heroine_id_2": heroine_id_2,
                        "speaker_id": speaker_id,
                        "subject_id": subject_id,
                        "content": row.content,
                        "content_type": "fact",
                        "embedding": embedding,
                        "importance": int(row.importance_score or 5),
                        "created_at": row.created_at,
                        "metadata": json.dumps({"migrated": True}, ensure_ascii=False),
                    },
                )
                inserted_memories += 1

        conn.commit()

    print("migrate done")
    print("inserted_checkpoints:", inserted_checkpoints)
    print("inserted_memories:", inserted_memories)
    print("skipped_memories:", skipped_memories)


if __name__ == "__main__":
    migrate()
