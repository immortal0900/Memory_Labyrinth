"""
User-NPC 장기 기억 매니저

Mem0를 대체하는 직접 구현
PostgreSQL + pgvector + PGroonga 기반 4요소 하이브리드 검색

사용 예시:
    # 대화 후 기억 저장
    await user_memory_manager.save_conversation(
        user_id="10001",
        heroine_id="letia",
        user_message="나는 고양이 좋아해",
        npc_response="저도 고양이 좋아해요"
    )
    
    # 기억 검색
    memories = await user_memory_manager.search_memories(
        user_id="10001",
        heroine_id="letia",
        query="고양이"
    )
"""

import json
import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

from db.config import CONNECTION_URL
from db.user_memory_models import (
    Speaker,
    Subject,
    ContentType,
    ExtractedFact,
    SearchWeights,
    UserMemory,
    NPC_ID_TO_HEROINE,
    HEROINE_TO_SPEAKER,
)


class UserMemoryManager:
    """User-NPC 장기 기억 매니저
    
    Mem0를 대체하여 직접 PostgreSQL에 기억을 저장하고 검색합니다.
    
    주요 기능:
    1. LLM으로 대화에서 fact 추출
    2. 중복/충돌 검사 후 저장
    3. 4요소 하이브리드 검색 (최신도, 중요도, 관련도, 키워드)
    """
    
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        """초기화
        
        Args:
            embedding_model: OpenAI 임베딩 모델명
        """
        # DB 연결
        self.engine = create_engine(CONNECTION_URL, pool_pre_ping=True)
        
        # 임베딩 모델
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Fact 추출용 LLM (temperature=0으로 일관된 추출)
        self.extract_llm = init_chat_model(
            model="gpt-4o-mini",
            temperature=0
        )
        
        # 기본 검색 가중치
        self.default_weights = SearchWeights()
        
        # 중복 판정 임계값 (90% 유사도 이상이면 중복)
        self.duplicate_threshold = 0.9
    
    # ============================================
    # Fact 추출
    # ============================================
    
    async def extract_facts(
        self,
        conversation: str,
        heroine_id: str
    ) -> List[ExtractedFact]:
        """대화에서 장기 기억할 fact 추출
        
        LLM을 사용하여 대화에서 중요한 사실을 추출합니다.
        
        Args:
            conversation: 대화 내용 (예: "플레이어: 고양이 좋아해\n레티아: 저도요")
            heroine_id: 히로인 ID (letia, lupames, roco)
        
        Returns:
            추출된 ExtractedFact 리스트
        """
        prompt = f"""다음 대화에서 장기 기억으로 저장할 중요한 사실을 추출하세요.

[대화]
{conversation}

[히로인 ID]
{heroine_id}

[추출 기준]
- 플레이어의 선호도 (좋아하는 것, 싫어하는 것)
- 플레이어의 개인 정보 (이름, 직업, 취미 등)
- 히로인이 플레이어에 대해 내린 평가
- 함께한 이벤트나 경험
- 세계관에 대한 새로운 정보

[speaker 값]
- "user": 플레이어가 말한 내용
- "{heroine_id}": 히로인이 말한 내용

[subject 값]
- "user": 플레이어에 대한 사실
- "{heroine_id}": 히로인에 대한 사실
- "world": 세계에 대한 사실

[content_type 값]
- "preference": 선호도 (좋아함, 싫어함)
- "trait": 특성 (성격, 외모)
- "event": 이벤트 (함께한 경험)
- "opinion": 평가 (누군가에 대한 의견)
- "personal": 개인정보 (이름, 직업)

[중요도 기준]
- 1-3: 사소한 정보
- 4-6: 일반적인 정보
- 7-8: 중요한 정보
- 9-10: 매우 중요한 정보 (트라우마, 비밀 등)

JSON 배열로 응답하세요. 저장할 사실이 없으면 빈 배열 []을 반환하세요.
예시:
[
    {{"speaker": "user", "subject": "user", "content_type": "preference", "content": "고양이를 좋아함", "importance": 6}},
    {{"speaker": "{heroine_id}", "subject": "user", "content_type": "opinion", "content": "따뜻한 사람이라고 생각함", "importance": 7}}
]"""

        response = await self.extract_llm.ainvoke(prompt)
        
        # JSON 파싱
        try:
            content = response.content.strip()
            # 코드 블록 제거
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            facts_data = json.loads(content.strip())
            
            # ExtractedFact 객체로 변환
            facts = []
            for item in facts_data:
                fact = ExtractedFact(
                    speaker=Speaker(item["speaker"]),
                    subject=Subject(item["subject"]),
                    content_type=ContentType(item["content_type"]),
                    content=item["content"],
                    importance=item.get("importance", 5)
                )
                facts.append(fact)
            
            return facts
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[ERROR] Fact 추출 파싱 실패: {e}")
            return []
    
    # ============================================
    # 기억 저장
    # ============================================
    
    async def add_memory(
        self,
        user_id: str,
        heroine_id: str,
        fact: ExtractedFact
    ) -> Optional[str]:
        """단일 fact 저장 (중복/충돌 처리 포함)
        
        Args:
            user_id: 플레이어 ID
            heroine_id: 히로인 ID
            fact: 저장할 fact
        
        Returns:
            생성된 메모리 ID 또는 None (중복시)
        """
        # 1. 임베딩 생성
        embedding = self.embeddings.embed_query(fact.content)
        
        # 2. 중복 검사
        similar = await self._find_similar_memory(user_id, heroine_id, embedding)
        
        if similar:
            # 중복 발견 -> 기존 기억 무효화 후 새로 저장
            await self._invalidate_memory(similar["id"])
            print(f"[INFO] 기존 기억 무효화: {similar['content'][:50]}...")
        
        # 3. 새 기억 저장
        memory_id = str(uuid.uuid4())
        
        sql = text("""
            INSERT INTO user_memories 
            (id, user_id, heroine_id, speaker, subject, content, content_type, embedding, importance)
            VALUES (:id, :user_id, :heroine_id, :speaker, :subject, :content, :content_type, 
                    CAST(:embedding AS vector), :importance)
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            conn.execute(sql, {
                "id": memory_id,
                "user_id": user_id,
                "heroine_id": heroine_id,
                "speaker": fact.speaker.value,
                "subject": fact.subject.value,
                "content": fact.content,
                "content_type": fact.content_type.value,
                "embedding": str(embedding),
                "importance": fact.importance
            })
            conn.commit()
        
        return memory_id
    
    async def save_conversation(
        self,
        user_id: str,
        heroine_id: str,
        user_message: str,
        npc_response: str
    ) -> List[str]:
        """대화를 분석하여 fact 추출 후 저장
        
        Mem0의 add_memory를 대체하는 메인 메서드
        
        Args:
            user_id: 플레이어 ID
            heroine_id: 히로인 ID
            user_message: 플레이어 메시지
            npc_response: NPC 응답
        
        Returns:
            저장된 메모리 ID 리스트
        """
        # 대화 포맷
        conversation = f"플레이어: {user_message}\n{heroine_id}: {npc_response}"
        
        # Fact 추출
        facts = await self.extract_facts(conversation, heroine_id)
        
        if not facts:
            return []
        
        # 각 fact 저장
        memory_ids = []
        for fact in facts:
            memory_id = await self.add_memory(user_id, heroine_id, fact)
            if memory_id:
                memory_ids.append(memory_id)
        
        return memory_ids
    
    # ============================================
    # 기억 검색
    # ============================================
    
    async def search_memories(
        self,
        user_id: str,
        heroine_id: str,
        query: str,
        limit: int = 5,
        weights: SearchWeights = None
    ) -> List[UserMemory]:
        """4요소 하이브리드 검색
        
        Mem0의 search_memory를 대체하는 메인 검색 메서드
        
        Args:
            user_id: 플레이어 ID
            heroine_id: 히로인 ID
            query: 검색어
            limit: 최대 결과 수
            weights: 검색 가중치 (None이면 기본값)
        
        Returns:
            UserMemory 리스트 (점수 높은 순)
        """
        weights = weights or self.default_weights
        
        # 검색어 임베딩
        query_embedding = self.embeddings.embed_query(query)
        
        # DB 검색 함수 호출
        sql = text("""
            SELECT * FROM search_user_memories_hybrid(
                :user_id,
                :heroine_id,
                :query_text,
                CAST(:query_embedding AS vector),
                :top_k,
                :w_recency,
                :w_importance,
                :w_relevance,
                :w_keyword
            )
        """)
        
        memories = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "user_id": user_id,
                "heroine_id": heroine_id,
                "query_text": query,
                "query_embedding": str(query_embedding),
                "top_k": limit,
                "w_recency": weights.recency,
                "w_importance": weights.importance,
                "w_relevance": weights.relevance,
                "w_keyword": weights.keyword
            })
            
            for row in result:
                memory = UserMemory(
                    id=str(row.id),
                    user_id=row.user_id,
                    heroine_id=row.heroine_id,
                    speaker=row.speaker,
                    subject=row.subject,
                    content=row.content,
                    content_type=row.content_type,
                    importance=row.importance,
                    created_at=row.created_at,
                    recency_score=row.recency_score,
                    importance_score=row.importance_score,
                    relevance_score=row.relevance_score,
                    keyword_score=row.keyword_score,
                    final_score=row.final_score
                )
                memories.append(memory)
        
        return memories
    
    def search_memory_sync(
        self,
        player_id: int,
        npc_id: int,
        query: str,
        limit: int = 5
    ) -> List[dict]:
        """동기 검색 (기존 Mem0 인터페이스 호환용)
        
        heroine_agent.py의 기존 코드와 호환되도록 dict 리스트 반환
        
        Args:
            player_id: 플레이어 ID (숫자)
            npc_id: NPC ID (숫자)
            query: 검색어
            limit: 최대 결과 수
        
        Returns:
            기억 dict 리스트 (Mem0 형식 호환)
        """
        # ID 변환
        user_id = str(player_id)
        heroine_id = NPC_ID_TO_HEROINE.get(npc_id, "letia")
        
        # 검색어 임베딩
        query_embedding = self.embeddings.embed_query(query)
        
        sql = text("""
            SELECT * FROM search_user_memories_hybrid(
                :user_id,
                :heroine_id,
                :query_text,
                CAST(:query_embedding AS vector),
                :top_k,
                :w_recency,
                :w_importance,
                :w_relevance,
                :w_keyword
            )
        """)
        
        results = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "user_id": user_id,
                "heroine_id": heroine_id,
                "query_text": query,
                "query_embedding": str(query_embedding),
                "top_k": limit,
                "w_recency": self.default_weights.recency,
                "w_importance": self.default_weights.importance,
                "w_relevance": self.default_weights.relevance,
                "w_keyword": self.default_weights.keyword
            })
            
            for row in result:
                # Mem0 형식과 유사하게 반환
                results.append({
                    "memory": row.content,
                    "text": row.content,
                    "score": row.final_score,
                    "metadata": {
                        "speaker": row.speaker,
                        "subject": row.subject,
                        "content_type": row.content_type
                    }
                })
        
        return results
    
    # ============================================
    # 내부 메서드
    # ============================================
    
    async def _find_similar_memory(
        self,
        user_id: str,
        heroine_id: str,
        embedding: list
    ) -> Optional[dict]:
        """유사 기억 검색 (중복 검사용)"""
        sql = text("""
            SELECT * FROM find_similar_memory(
                :user_id,
                :heroine_id,
                CAST(:embedding AS vector),
                :threshold
            )
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "user_id": user_id,
                "heroine_id": heroine_id,
                "embedding": str(embedding),
                "threshold": self.duplicate_threshold
            })
            
            row = result.fetchone()
            if row:
                return {
                    "id": str(row.id),
                    "content": row.content,
                    "similarity": row.similarity
                }
        
        return None
    
    async def _invalidate_memory(self, memory_id: str) -> None:
        """기억 무효화 (soft delete)"""
        sql = text("SELECT invalidate_memory(:memory_id)")
        
        with self.engine.connect() as conn:
            conn.execute(sql, {"memory_id": memory_id})
            conn.commit()
    
    # ============================================
    # 유틸리티 메서드
    # ============================================
    
    def format_memories_for_prompt(self, memories: List[UserMemory]) -> str:
        """프롬프트용 문자열 포맷
        
        Args:
            memories: UserMemory 리스트
        
        Returns:
            포맷된 문자열
        """
        if not memories:
            return "관련 기억 없음"
        
        lines = []
        for i, mem in enumerate(memories, 1):
            score_info = f"[점수: {mem.final_score:.2f}]" if mem.final_score > 0 else ""
            lines.append(f"{i}. {mem.content} {score_info}")
        
        return "\n".join(lines)
    
    def get_all_memories(self, player_id: int, npc_id: int) -> List[dict]:
        """모든 유효한 기억 조회 (Mem0 호환용)"""
        user_id = str(player_id)
        heroine_id = NPC_ID_TO_HEROINE.get(npc_id, "letia")
        
        sql = text("""
            SELECT id, content, speaker, subject, content_type, importance, created_at
            FROM user_memories
            WHERE user_id = :user_id
              AND heroine_id = :heroine_id
              AND invalid_at IS NULL
            ORDER BY created_at DESC
        """)
        
        results = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "user_id": user_id,
                "heroine_id": heroine_id
            })
            
            for row in result:
                results.append({
                    "id": str(row.id),
                    "memory": row.content,
                    "text": row.content,
                    "metadata": {
                        "speaker": row.speaker,
                        "subject": row.subject,
                        "content_type": row.content_type,
                        "importance": row.importance
                    }
                })
        
        return results


# 싱글톤 인스턴스
user_memory_manager = UserMemoryManager()

