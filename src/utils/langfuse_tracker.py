"""
LangFuse 토큰 추적 유틸리티

모든 LLM 호출 지점에서 사용할 수 있는 공통 콜백 핸들러 생성기

이 모듈이 없을 경우 발생하는 문제:
- 각 LLM 호출 지점에서 개별적으로 콜백을 설정해야 함
- 일관된 태깅/세션 관리가 어려움
- 코드 중복 발생
- 토큰 사용량 및 비용 추적 불가
"""

import os
from typing import Optional, Dict, Any, List

# LangFuse 초기화 (환경 변수 기반)
try:
    from langfuse import Langfuse, get_client
    from langfuse.langchain import CallbackHandler
    
    # 싱글톤 클라이언트 초기화
    # 환경 변수: LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST
    _langfuse_client = Langfuse()
    LANGFUSE_ENABLED = True
    print("[INFO] LangFuse 토큰 추적 활성화됨")
except Exception as e:
    _langfuse_client = None
    LANGFUSE_ENABLED = False
    print(f"[WARNING] LangFuse 비활성화: {e}")


class TokenTracker:
    """
    LangFuse 토큰 추적을 위한 유틸리티 클래스
    
    이 클래스가 없을 경우 발생하는 문제:
    - 각 LLM 호출 지점에서 개별적으로 콜백을 설정해야 함
    - 일관된 태깅/세션 관리가 어려움
    - 코드 중복 발생
    
    사용 예시:
        from utils.langfuse_tracker import tracker
        
        handler = tracker.get_callback_handler(
            trace_name="npc_response",
            tags=["npc", "heroine"],
            session_id=session_id,
            user_id=user_id,
        )
        
        config = {"callbacks": [handler]} if handler else {}
        response = await llm.ainvoke(prompt, config=config)
    """
    
    @staticmethod
    def get_callback_handler(
        trace_name: str,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[CallbackHandler]:
        """
        LangFuse 콜백 핸들러 생성
        
        이 메서드가 없을 경우 발생하는 문제:
        - LangFuse에서 토큰 사용량을 추적할 수 없음
        - API 비용 분석 불가
        - 디버깅 시 프롬프트 히스토리 확인 불가
        - 세션별/유저별 필터링 불가
        
        Args:
            trace_name: 트레이스 이름 (예: "fact_extraction", "npc_response")
                       LangFuse 대시보드에서 이 이름으로 필터링 가능
            tags: 태그 리스트 (예: ["npc", "heroine", "letia"])
                 LangFuse 대시보드에서 태그로 필터링 가능
            session_id: 세션 ID (게임 세션과 연결)
                       동일 세션의 모든 LLM 호출을 그룹화
            user_id: 사용자 ID
                    유저별 토큰 사용량 분석에 사용
            metadata: 추가 메타데이터
                     동적인 컨텍스트 정보(예: 히로인 이름, 현재 의도, 호감도 등)를 기록하기 위한 것(예:누가,어떤 상태일때 토큰소모가 많았는지)
            
        Returns:
            LangFuse CallbackHandler 또는 None (비활성화 시)
            None이 반환되면 LLM 호출은 정상 작동하지만 추적하지 않음
        """
        if not LANGFUSE_ENABLED:
            return None
            
        return CallbackHandler(
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
            metadata={
                "trace_name": trace_name,
                **(metadata or {})
            }
        )
    
    @staticmethod
    def get_langfuse_config(
        trace_name: str,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        LangChain invoke용 config 딕셔너리 반환
        
        이 메서드는 ainvoke/invoke 호출을 더 간결하게 만듭니다.
        
        사용 예시:
            # 방법 1: get_callback_handler 사용 (명시적)
            handler = tracker.get_callback_handler("npc_chat")
            config = {"callbacks": [handler]} if handler else {}
            response = await llm.ainvoke(prompt, config=config)
            
            # 방법 2: get_langfuse_config 사용 (간결)
            response = await llm.ainvoke(
                prompt, 
                **tracker.get_langfuse_config("npc_chat")
            )
            
        Args:
            (get_callback_handler와 동일)
            
        Returns:
            {"config": {"callbacks": [handler]}} 또는 {} (비활성화 시)
        """
        handler = TokenTracker.get_callback_handler(
            trace_name=trace_name,
            tags=tags,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
        )
        
        if handler:
            return {"config": {"callbacks": [handler]}}
        return {}
    
    @staticmethod
    def flush():
        """
        보류 중인 모든 이벤트를 LangFuse에 전송
        
        이 메서드가 없을 경우 발생하는 문제:
        - 단기 실행 스크립트에서 이벤트가 전송되지 않을 수 있음
        - 서버 종료 시 일부 이벤트가 유실될 수 있음
        
        사용 시점:
        - 테스트 종료 시
        - 스크립트 종료 전
        - 중요한 이벤트 직후 (선택적)
        """
        if LANGFUSE_ENABLED and _langfuse_client:
            _langfuse_client.flush()
    
    @staticmethod
    def shutdown():
        """
        LangFuse 클라이언트 종료
        
        이 메서드가 없을 경우 발생하는 문제:
        - 백그라운드 스레드가 정리되지 않을 수 있음
        - 리소스 누수 가능성
        
        사용 시점:
        - 애플리케이션 종료 시 (FastAPI shutdown 이벤트 등)
        - 테스트 스위트 종료 시
        """
        if LANGFUSE_ENABLED and _langfuse_client:
            _langfuse_client.shutdown()


# 편의를 위한 싱글톤 인스턴스
# 모든 모듈에서 "from utils.langfuse_tracker import tracker"로 임포트
tracker = TokenTracker()
