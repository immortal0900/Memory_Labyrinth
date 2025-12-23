"""
기존 중복 취향 데이터 정리 마이그레이션

문제: 같은 주제에 대한 취향이 여러 개 활성화되어 있음
예: "귤을 좋아함"과 "사과를 더 좋아함" 둘 다 invalid_at = NULL

해결: LLM으로 충돌 여부 판단 후 오래된 기억 무효화

사용법:
    python -m src.db.migrations.fix_duplicate_preferences
"""

import asyncio
from sqlalchemy import create_engine, text
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from enums.LLM import LLM

load_dotenv()

from db.config import CONNECTION_URL


class DuplicatePreferenceFixer:
    """중복 취향 데이터 정리 도구"""

    def __init__(self):
        self.engine = create_engine(CONNECTION_URL, pool_pre_ping=True)
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = init_chat_model(model=LLM.GPT5_1, temperature=0)

    def get_all_preference_memories(self) -> list:
        """content_type = preference인 모든 유효한 기억 조회"""
        sql = text(
            """
            SELECT id, player_id, heroine_id, content, embedding, created_at
            FROM user_memories
            WHERE content_type = 'preference'
              AND invalid_at IS NULL
            ORDER BY player_id, heroine_id, created_at ASC
        """
        )

        results = []
        with self.engine.connect() as conn:
            for row in conn.execute(sql):
                results.append(
                    {
                        "id": str(row.id),
                        "player_id": row.player_id,
                        "heroine_id": row.heroine_id,
                        "content": row.content,
                        "embedding": row.embedding,
                        "created_at": row.created_at,
                    }
                )
        return results

    async def check_conflict(self, old_content: str, new_content: str) -> bool:
        """LLM으로 두 기억이 충돌하는지 판단"""
        prompt = f"""다음 두 기억이 충돌하거나 대체 관계인지 판단하세요.

[기존 기억]
{old_content}

[새 기억]
{new_content}

[판단 기준]
- 같은 주제에 대해 취향/선호도가 바뀌었으면 충돌
- 새 기억이 기존 기억을 부정하거나 수정하면 충돌
- 서로 다른 주제면 충돌 아님
- 추가 정보면 충돌 아님

충돌이면 "yes", 아니면 "no"만 응답하세요."""

        response = await self.llm.ainvoke(prompt)
        answer = response.content.strip().lower()
        return answer == "yes"

    def invalidate_memory(self, memory_id: str) -> None:
        """기억 무효화"""
        sql = text(
            """
            UPDATE user_memories
            SET invalid_at = NOW(), updated_at = NOW()
            WHERE id = :memory_id
        """
        )
        with self.engine.connect() as conn:
            conn.execute(sql, {"memory_id": memory_id})
            conn.commit()

    async def fix_duplicates(self, dry_run: bool = True) -> dict:
        """중복 취향 정리 실행

        Args:
            dry_run: True면 실제 무효화하지 않고 결과만 출력

        Returns:
            처리 결과 통계
        """
        memories = self.get_all_preference_memories()
        print(f"[INFO] preference 기억 {len(memories)}개 조회됨")

        # (player_id, heroine_id)별로 그룹화
        groups = {}
        for mem in memories:
            key = (mem["player_id"], mem["heroine_id"])
            if key not in groups:
                groups[key] = []
            groups[key].append(mem)

        stats = {"checked": 0, "conflicts_found": 0, "invalidated": 0}

        for key, mems in groups.items():
            if len(mems) < 2:  # 기억이 1개면 비교대상이 없음, 충돌 없음
                continue

            print(f"\n[GROUP] player={key[0]}, heroine={key[1]}, count={len(mems)}")

            # 시간순으로 정렬된 상태, 나중 기억과 이전 기억 비교
            for i in range(len(mems)):
                for j in range(i + 1, len(mems)):
                    old_mem = mems[i]
                    new_mem = mems[j]

                    stats["checked"] += 1

                    is_conflict = await self.check_conflict(
                        old_mem["content"], new_mem["content"]
                    )

                    if is_conflict:
                        stats["conflicts_found"] += 1
                        print(f"  [CONFLICT] 기존: {old_mem['content'][:40]}...")
                        print(f"             새로: {new_mem['content'][:40]}...")

                        if not dry_run:
                            self.invalidate_memory(old_mem["id"])
                            stats["invalidated"] += 1
                            print(f"             -> 기존 기억 무효화됨")

        return stats


async def main():
    fixer = DuplicatePreferenceFixer()

    print("=" * 60)
    print("중복 취향 데이터 정리 마이그레이션")
    print("=" * 60)

    # 1단계: dry_run으로 확인
    print("\n[1단계] Dry Run - 충돌 확인만 수행")
    stats = await fixer.fix_duplicates(dry_run=True)

    print(f"\n[결과] 검사: {stats['checked']}쌍, 충돌: {stats['conflicts_found']}개")

    if stats["conflicts_found"] == 0:
        print("\n충돌 없음. 종료합니다.")
        return

    # 2단계: 실제 무효화 확인
    print("\n" + "=" * 60)
    answer = input("실제로 무효화를 진행하시겠습니까? (yes/no): ")

    if answer.lower() == "yes":
        print("\n[2단계] 실제 무효화 진행")
        stats = await fixer.fix_duplicates(dry_run=False)
        print(f"\n[완료] 무효화된 기억: {stats['invalidated']}개")
    else:
        print("\n취소되었습니다.")


if __name__ == "__main__":
    asyncio.run(main())
