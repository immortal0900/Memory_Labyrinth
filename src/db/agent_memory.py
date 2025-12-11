"""
NPC간 메모리 시스템 (Generative Agents 스타일)
PostgreSQL + pgvector 기반

이 모듈은 NPC간 기억만 관리합니다:
- npc_memory: NPC가 다른 NPC에 대해 가지는 개별 기억 (예: A가 B에 대해)
- npc_conversation: NPC간 대화 내용

User-NPC 대화는 user_memory_manager.py에서 별도로 관리합니다

하이브리드 검색 공식:
Score = (w_recency * Recency) + (w_importance * Importance) + (w_relevance * Relevance)
- Recency: 시간이 지남에 따라 감쇠 (지수 감쇠 함수)
- Importance: 1~10 점수를 0~1로 정규화
- Relevance: 벡터 코사인 유사도
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Literal
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

from db.config import CONNECTION_URL


# 메모리 타입 정의 (npc_memory: NPC간 기억, npc_conversation: NPC간 대화)
MemoryType = Literal["npc_memory", "npc_conversation"]


@dataclass
class Memory:
    """메모리 데이터 클래스
    
    DB에서 조회한 메모리 정보를 담는 컨테이너입니다.
    
    Attributes:
        id: 메모리 고유 ID (UUID)
        agent_id: 기억 주체 ID (예: npc_1_about_2, conv_1_2)
        memory_type: 메모리 타입 (npc_memory 또는 npc_conversation)
        content: 기억 내용 텍스트
        importance_score: 중요도 점수 (1-10)
        created_at: 생성 시간
        last_accessed_at: 마지막 조회 시간
        metadata: 추가 메타데이터 (JSON)
        recency_score: 최신성 점수 (0-1, 검색시 계산됨)
        importance_normalized: 정규화된 중요도 (0-1, 검색시 계산됨)
        relevance_score: 관련성 점수 (0-1, 검색시 계산됨)
        total_score: 총합 점수 (검색시 계산됨)
    """
    id: str
    agent_id: str
    memory_type: str
    content: str
    importance_score: int
    created_at: datetime
    last_accessed_at: datetime
    metadata: dict
    recency_score: float = 0.0
    importance_normalized: float = 0.0
    relevance_score: float = 0.0
    total_score: float = 0.0


class AgentMemoryManager:
    """NPC간 메모리 매니저
    
    하나의 테이블(agent_memories)에서 NPC간 기억을 관리합니다.
    
    주요 기능:
    1. 메모리 추가 (add_memory, add_npc_memory, add_npc_conversation)
    2. 하이브리드 검색 (search_memories, search_npc_all_memories)
    3. 최근 메모리 조회 (get_recent_memories, get_npc_conversations)
    
    사용 예시:
        manager = AgentMemoryManager()
        
        # NPC 1이 NPC 2에 대한 기억 추가
        manager.add_npc_memory(
            observer_id=1, 
            target_id=2, 
            content="오늘 레티아가 나한테 맛있는 쿠키를 줬다",
            importance=7
        )
        
        # 검색
        memories = manager.search_npc_all_memories(npc_id=1, query="쿠키")
    """
    
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        """초기화
        
        Args:
            embedding_model: OpenAI 임베딩 모델명
        """
        # DB 연결
        self.engine = create_engine(CONNECTION_URL, pool_pre_ping=True)
        
        # 임베딩 모델 (텍스트를 벡터로 변환)
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # 검색시 사용할 기본 가중치
        self.default_weights = {
            "recency": 1.0,      # 최신성 가중치
            "importance": 1.0,   # 중요도 가중치
            "relevance": 1.0     # 관련성 가중치
        }
        
        # 시간 감쇠율 (0.01 = 약 3일이 지나면 점수 절반)
        self.decay_rate = 0.01
    
    # ============================================
    # 기억 추가 메서드
    # ============================================
    
    def add_memory(
        self,
        agent_id: str,
        memory_type: MemoryType,
        content: str,
        importance: int = 5,
        metadata: dict = None
    ) -> str:
        """기본 기억 추가 메서드
        
        Args:
            agent_id: 기억 주체 ID (예: npc_1_about_2, conv_1_2)
            memory_type: 기억 타입 (npc_memory 또는 npc_conversation)
            content: 기억 내용
            importance: 중요도 (1-10, 기본값 5)
            metadata: 추가 메타데이터 (선택)
        
        Returns:
            생성된 메모리 ID (UUID 문자열)
        """
        # 중요도 범위 제한 (1~10)
        importance = max(1, min(10, importance))
        
        # 메타데이터 기본값 설정
        if metadata is None:
            metadata = {}
        
        # 텍스트를 벡터로 변환 (임베딩)
        embedding = self.embeddings.embed_query(content)
        
        # 고유 ID 생성
        memory_id = str(uuid.uuid4())
        
        # DB에 저장하는 SQL
        sql = text("""
            INSERT INTO agent_memories 
            (id, agent_id, memory_type, content, embedding, importance_score, metadata)
            VALUES (:id, :agent_id, :memory_type, :content, CAST(:embedding AS vector), CAST(:importance AS integer), CAST(:metadata AS jsonb))
            RETURNING id
        """)
        
        # DB 실행
        with self.engine.connect() as conn:
            conn.execute(sql, {
                "id": memory_id,
                "agent_id": agent_id,
                "memory_type": memory_type,
                "content": content,
                "embedding": str(embedding),
                "importance": importance,
                "metadata": json.dumps(metadata, ensure_ascii=False)  # JSON 문자열로 변환
            })
            conn.commit()
        
        return memory_id
    
    def add_npc_memory(
        self,
        observer_id: int,
        target_id: int,
        content: str,
        importance: int = 5,
        metadata: dict = None
    ) -> str:
        """NPC간 개별 기억 추가 (A가 B에 대해 기억)
        
        예: 레티아(1)가 루파메스(2)에 대해 "오늘 같이 훈련했다" 기억
        
        Args:
            observer_id: 기억하는 NPC ID (관찰자)
            target_id: 기억되는 NPC ID (대상)
            content: 기억 내용
            importance: 중요도 (1-10)
            metadata: 추가 정보
        
        Returns:
            생성된 메모리 ID
        """
        # agent_id 형식: npc_[관찰자ID]_about_[대상ID]
        agent_id = f"npc_{observer_id}_about_{target_id}"
        
        # 메타데이터에 NPC ID 정보 추가
        if metadata is None:
            metadata = {}
        metadata["observer_id"] = observer_id
        metadata["target_id"] = target_id
        
        return self.add_memory(agent_id, "npc_memory", content, importance, metadata)
    
    def add_npc_conversation(
        self,
        npc1_id: int,
        npc2_id: int,
        content: str,
        importance: int = 5,
        metadata: dict = None
    ) -> str:
        """NPC간 대화 추가
        
        두 NPC 사이의 대화 내용을 저장합니다.
        
        Args:
            npc1_id: 첫 번째 NPC ID
            npc2_id: 두 번째 NPC ID
            content: 대화 내용 전체
            importance: 중요도 (1-10)
            metadata: 추가 정보 (situation, emotions 등)
        
        Returns:
            생성된 메모리 ID
        """
        # ID가 작은 쪽을 먼저 배치 (일관성 유지)
        # 예: conv_1_2 (1과 2의 대화)
        id1 = min(npc1_id, npc2_id)
        id2 = max(npc1_id, npc2_id)
        agent_id = f"conv_{id1}_{id2}"
        
        # 메타데이터에 NPC ID 정보 추가
        if metadata is None:
            metadata = {}
        metadata["npc1_id"] = npc1_id
        metadata["npc2_id"] = npc2_id
        
        return self.add_memory(agent_id, "npc_conversation", content, importance, metadata)
    
    def add_mutual_npc_memory(
        self,
        npc1_id: int,
        npc2_id: int,
        content: str,
        npc1_perspective: str = None,
        npc2_perspective: str = None,
        importance: int = 5,
        metadata: dict = None
    ) -> tuple:
        """양방향 NPC 기억 추가
        
        두 NPC가 서로에 대해 기억을 저장합니다.
        대화 후 양쪽에 기억을 남길 때 사용합니다.
        
        Args:
            npc1_id: 첫 번째 NPC ID
            npc2_id: 두 번째 NPC ID
            content: 공통 기억 내용 (개별 관점이 없을 때 사용)
            npc1_perspective: NPC1의 관점에서 본 내용 (선택)
            npc2_perspective: NPC2의 관점에서 본 내용 (선택)
            importance: 중요도
            metadata: 추가 정보
        
        Returns:
            (npc1의 메모리 ID, npc2의 메모리 ID) 튜플
        """
        # NPC1이 NPC2에 대해 기억
        mem1_id = self.add_npc_memory(
            observer_id=npc1_id,
            target_id=npc2_id,
            content=npc1_perspective or content,  # 개별 관점이 없으면 공통 내용 사용
            importance=importance,
            metadata=metadata
        )
        
        # NPC2가 NPC1에 대해 기억
        mem2_id = self.add_npc_memory(
            observer_id=npc2_id,
            target_id=npc1_id,
            content=npc2_perspective or content,
            importance=importance,
            metadata=metadata
        )
        
        return (mem1_id, mem2_id)
    
    # ============================================
    # 검색 메서드
    # ============================================
    
    def search_memories(
        self,
        agent_id: str,
        query: str,
        top_k: int = 5,
        memory_type: MemoryType = None,
        w_recency: float = None,
        w_importance: float = None,
        w_relevance: float = None,
        update_access_time: bool = True
    ) -> List[Memory]:
        """하이브리드 검색 (메인 검색 메서드)
        
        최신성, 중요도, 관련성을 모두 고려한 검색을 수행합니다.
        
        Args:
            agent_id: 검색할 기억 주체 ID
            query: 검색어
            top_k: 최대 결과 수 (기본값 5)
            memory_type: 타입 필터 (None이면 모든 타입)
            w_recency: 최신성 가중치 (None이면 기본값 1.0)
            w_importance: 중요도 가중치 (None이면 기본값 1.0)
            w_relevance: 관련성 가중치 (None이면 기본값 1.0)
            update_access_time: 조회 시간 업데이트 여부
        
        Returns:
            Memory 객체 리스트 (점수 높은 순)
        """
        # 가중치 설정 (None이면 기본값 사용)
        w_recency = w_recency if w_recency is not None else self.default_weights["recency"]
        w_importance = w_importance if w_importance is not None else self.default_weights["importance"]
        w_relevance = w_relevance if w_relevance is not None else self.default_weights["relevance"]
        
        # 검색어를 벡터로 변환
        query_embedding = self.embeddings.embed_query(query)
        
        # DB의 하이브리드 검색 함수 호출
        sql = text("""
            SELECT * FROM search_memories_hybrid(
                :agent_id,
                CAST(:query_embedding AS vector),
                :top_k,
                :w_recency,
                :w_importance,
                :w_relevance,
                :decay_rate,
                :memory_type
            )
        """)
        
        memories = []
        memory_ids = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "agent_id": agent_id,
                "query_embedding": str(query_embedding),
                "top_k": top_k,
                "w_recency": w_recency,
                "w_importance": w_importance,
                "w_relevance": w_relevance,
                "decay_rate": self.decay_rate,
                "memory_type": memory_type
            })
            
            # 결과를 Memory 객체로 변환
            for row in result:
                memory = Memory(
                    id=str(row.id),
                    agent_id=row.agent_id,
                    memory_type=row.memory_type,
                    content=row.content,
                    importance_score=row.importance_score,
                    created_at=row.created_at,
                    last_accessed_at=row.last_accessed_at,
                    metadata=row.metadata or {},
                    recency_score=row.recency_score,
                    importance_normalized=row.importance_normalized,
                    relevance_score=row.relevance_score,
                    total_score=row.total_score
                )
                memories.append(memory)
                memory_ids.append(row.id)
            
            # 조회 시간 업데이트 (선택적)
            if update_access_time and memory_ids:
                # UUID 리스트를 문자열 리스트로 변환
                id_strings = [str(mid) for mid in memory_ids]
                update_sql = text("""
                    UPDATE agent_memories
                    SET last_accessed_at = NOW()
                    WHERE id::text = ANY(:ids)
                """)
                conn.execute(update_sql, {"ids": id_strings})
                conn.commit()
        
        return memories
    
    def search_npc_all_memories(
        self,
        npc_id: int,
        query: str,
        top_k: int = 5,
        w_recency: float = None,
        w_importance: float = None,
        w_relevance: float = None
    ) -> List[Memory]:
        """특정 NPC와 관련된 모든 기억 검색
        
        해당 NPC가 참여한 대화와 다른 NPC에 대한 기억을 모두 검색합니다.
        
        Args:
            npc_id: NPC ID
            query: 검색어
            top_k: 최대 결과 수
            w_recency, w_importance, w_relevance: 가중치
        
        Returns:
            Memory 객체 리스트
        """
        # 가중치 설정
        w_recency = w_recency if w_recency is not None else self.default_weights["recency"]
        w_importance = w_importance if w_importance is not None else self.default_weights["importance"]
        w_relevance = w_relevance if w_relevance is not None else self.default_weights["relevance"]
        
        # 검색어를 벡터로 변환
        query_embedding = self.embeddings.embed_query(query)
        
        # DB의 NPC 통합 검색 함수 호출
        sql = text("""
            SELECT * FROM search_npc_memories(
                :npc_id,
                CAST(:query_embedding AS vector),
                :top_k,
                :w_recency,
                :w_importance,
                :w_relevance,
                :decay_rate
            )
        """)
        
        memories = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "npc_id": npc_id,
                "query_embedding": str(query_embedding),
                "top_k": top_k,
                "w_recency": w_recency,
                "w_importance": w_importance,
                "w_relevance": w_relevance,
                "decay_rate": self.decay_rate
            })
            
            for row in result:
                memory = Memory(
                    id=str(row.id),
                    agent_id=row.agent_id,
                    memory_type=row.memory_type,
                    content=row.content,
                    importance_score=row.importance_score,
                    created_at=row.created_at,
                    last_accessed_at=None,
                    metadata=row.metadata or {},
                    total_score=row.total_score
                )
                memories.append(memory)
        
        return memories
    
    def search_npc_conversations(
        self,
        npc_id: int,
        query: str,
        top_k: int = 5
    ) -> List[Memory]:
        """NPC간 대화만 검색 (관련성 기반)
        
        특정 NPC가 참여한 대화 중 검색어와 관련된 것을 찾습니다.
        
        Args:
            npc_id: NPC ID (이 NPC가 참여한 대화 검색)
            query: 검색어
            top_k: 최대 결과 수
        
        Returns:
            Memory 객체 리스트
        """
        query_embedding = self.embeddings.embed_query(query)
        
        # conv_X_Y 형식에서 X 또는 Y가 npc_id인 것 검색
        sql = text("""
            WITH scored AS (
                SELECT 
                    m.*,
                    1 - (m.embedding <=> CAST(:query_embedding AS vector)) AS relevance
                FROM agent_memories m
                WHERE m.memory_type = 'npc_conversation'
                  AND (
                      m.agent_id LIKE 'conv_%_' || CAST(:npc_id AS TEXT)
                      OR m.agent_id LIKE 'conv_' || CAST(:npc_id AS TEXT) || '_%'
                  )
            )
            SELECT * FROM scored
            ORDER BY relevance DESC
            LIMIT :top_k
        """)
        
        memories = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {
                "npc_id": npc_id,
                "query_embedding": str(query_embedding),
                "top_k": top_k
            })
            
            for row in result:
                memory = Memory(
                    id=str(row.id),
                    agent_id=row.agent_id,
                    memory_type=row.memory_type,
                    content=row.content,
                    importance_score=row.importance_score,
                    created_at=row.created_at,
                    last_accessed_at=row.last_accessed_at,
                    metadata=row.metadata or {},
                    relevance_score=row.relevance
                )
                memories.append(memory)
        
        return memories
    
    # ============================================
    # 조회 메서드 (검색 없이 최신순 등)
    # ============================================
    
    def get_recent_memories(
        self,
        agent_id: str,
        limit: int = 10,
        memory_type: MemoryType = None
    ) -> List[Memory]:
        """최신 기억 조회 (시간순)
        
        Args:
            agent_id: 기억 주체 ID
            limit: 최대 조회 수
            memory_type: 타입 필터 (선택)
        
        Returns:
            Memory 객체 리스트 (최신순)
        """
        # 타입 필터 조건 추가
        type_filter = "AND memory_type = :memory_type" if memory_type else ""
        
        sql = text(f"""
            SELECT id, agent_id, memory_type, content, importance_score, 
                   created_at, last_accessed_at, metadata
            FROM agent_memories
            WHERE agent_id = :agent_id {type_filter}
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        params = {"agent_id": agent_id, "limit": limit}
        if memory_type:
            params["memory_type"] = memory_type
        
        memories = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, params)
            
            for row in result:
                memory = Memory(
                    id=str(row.id),
                    agent_id=row.agent_id,
                    memory_type=row.memory_type,
                    content=row.content,
                    importance_score=row.importance_score,
                    created_at=row.created_at,
                    last_accessed_at=row.last_accessed_at,
                    metadata=row.metadata or {}
                )
                memories.append(memory)
        
        return memories
    
    def get_npc_conversations(
        self,
        npc1_id: int = None,
        npc2_id: int = None,
        limit: int = 10
    ) -> List[Memory]:
        """NPC간 대화 조회 (최신순)
        
        Args:
            npc1_id: 첫 번째 NPC ID (선택)
            npc2_id: 두 번째 NPC ID (선택)
            limit: 최대 조회 수
        
        Returns:
            Memory 객체 리스트
        """
        # WHERE 조건 구성
        conditions = ["memory_type = 'npc_conversation'"]
        params = {"limit": limit}
        
        # NPC ID 필터 추가
        if npc1_id is not None:
            conditions.append(f"(agent_id LIKE 'conv_%_{npc1_id}' OR agent_id LIKE 'conv_{npc1_id}_%')")
        
        if npc2_id is not None:
            conditions.append(f"(agent_id LIKE 'conv_%_{npc2_id}' OR agent_id LIKE 'conv_{npc2_id}_%')")
        
        where_clause = " AND ".join(conditions)
        
        sql = text(f"""
            SELECT id, agent_id, memory_type, content, importance_score, 
                   created_at, last_accessed_at, metadata
            FROM agent_memories
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        memories = []
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, params)
            
            for row in result:
                memory = Memory(
                    id=str(row.id),
                    agent_id=row.agent_id,
                    memory_type=row.memory_type,
                    content=row.content,
                    importance_score=row.importance_score,
                    created_at=row.created_at,
                    last_accessed_at=row.last_accessed_at,
                    metadata=row.metadata or {}
                )
                memories.append(memory)
        
        return memories
    
    # ============================================
    # 삭제/유틸리티 메서드
    # ============================================
    
    def delete_memory(self, memory_id: str) -> bool:
        """특정 메모리 삭제
        
        Args:
            memory_id: 삭제할 메모리 ID
        
        Returns:
            삭제 성공 여부
        """
        sql = text("DELETE FROM agent_memories WHERE id = :id")
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {"id": memory_id})
            conn.commit()
            return result.rowcount > 0
    
    def delete_all_memories(self, agent_id: str) -> int:
        """특정 agent_id의 모든 메모리 삭제
        
        Args:
            agent_id: 삭제할 agent_id
        
        Returns:
            삭제된 메모리 수
        """
        sql = text("DELETE FROM agent_memories WHERE agent_id = :agent_id")
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, {"agent_id": agent_id})
            conn.commit()
            return result.rowcount
    
    def get_stats(self, agent_id: str = None) -> dict:
        """메모리 통계 조회
        
        Args:
            agent_id: 특정 agent_id 통계 (None이면 전체)
        
        Returns:
            통계 정보 딕셔너리
        """
        if agent_id:
            sql = text("""
                SELECT 
                    COUNT(*) AS total_memories,
                    AVG(importance_score)::FLOAT AS avg_importance,
                    MIN(created_at) AS oldest_memory,
                    MAX(created_at) AS newest_memory
                FROM agent_memories
                WHERE agent_id = :agent_id
            """)
            params = {"agent_id": agent_id}
        else:
            sql = text("""
                SELECT 
                    COUNT(*) AS total_memories,
                    AVG(importance_score)::FLOAT AS avg_importance,
                    MIN(created_at) AS oldest_memory,
                    MAX(created_at) AS newest_memory,
                    COUNT(DISTINCT agent_id) AS unique_agents
                FROM agent_memories
            """)
            params = {}
        
        with self.engine.connect() as conn:
            result = conn.execute(sql, params)
            row = result.fetchone()
            
            if row:
                stats = {
                    "total_memories": row.total_memories or 0,
                    "avg_importance": row.avg_importance or 0,
                    "oldest_memory": row.oldest_memory,
                    "newest_memory": row.newest_memory
                }
                if not agent_id and hasattr(row, 'unique_agents'):
                    stats["unique_agents"] = row.unique_agents
                return stats
            
            return {"total_memories": 0}
    
    def format_memories_for_prompt(self, memories: List[Memory]) -> str:
        """프롬프트용 문자열 포맷
        
        검색된 메모리를 LLM 프롬프트에 넣기 좋은 형태로 변환합니다.
        
        Args:
            memories: Memory 객체 리스트
        
        Returns:
            포맷된 문자열
        """
        if not memories:
            return "관련 기억 없음"
        
        lines = []
        for i, mem in enumerate(memories, 1):
            # 점수 정보 (있으면 표시)
            score_info = f"[점수: {mem.total_score:.2f}]" if mem.total_score > 0 else ""
            type_info = f"({mem.memory_type})" if mem.memory_type else ""
            lines.append(f"{i}. {mem.content} {score_info} {type_info}")
        
        return "\n".join(lines)


# 싱글톤 인스턴스 (앱 전체에서 하나만 사용)
agent_memory_manager = AgentMemoryManager()
