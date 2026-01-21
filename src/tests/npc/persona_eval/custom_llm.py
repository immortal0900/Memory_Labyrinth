"""
DeepEval용 커스텀 LLM 래퍼

GPT-5-mini 모델을 DeepEval의 평가 모델로 사용하기 위한 래퍼 클래스
"""

from dotenv import load_dotenv
load_dotenv()

from deepeval.models.base_model import DeepEvalBaseLLM
from langchain.chat_models import init_chat_model


class GPT5MiniEvaluator(DeepEvalBaseLLM):
    """
    DeepEval 평가용 GPT-5-mini 모델 래퍼
    
    DeepEvalBaseLLM을 상속하여 GPT-5-mini를 평가 모델로 사용할 수 있게 합니다.
    """
    
    def __init__(self, temperature: float = 0):
        """
        Args:
            temperature: LLM 온도 설정 (기본값 0으로 일관된 평가)
        """
        self.model = init_chat_model(model="gpt-5-mini", temperature=temperature)
        super().__init__()
    
    def generate(self, prompt: str) -> str:
        """
        동기 방식으로 프롬프트에 대한 응답 생성
        
        Args:
            prompt: 평가를 위한 프롬프트
            
        Returns:
            생성된 응답 텍스트
        """
        response = self.model.invoke(prompt)
        return response.content
    
    async def a_generate(self, prompt: str) -> str:
        """
        비동기 방식으로 프롬프트에 대한 응답 생성
        
        Args:
            prompt: 평가를 위한 프롬프트
            
        Returns:
            생성된 응답 텍스트
        """
        response = await self.model.ainvoke(prompt)
        return response.content
    
    def load_model(self):
        """
        모델 로드 (이미 __init__에서 로드됨)

        Returns:
            로드된 모델 인스턴스
        """
        return self.model

    def get_model_name(self) -> str:
        """
        모델 이름 반환

        Returns:
            모델 이름 문자열
        """
        return "gpt-5-mini"


# 싱글톤 인스턴스 (테스트 전체에서 재사용)
evaluator_llm = GPT5MiniEvaluator()
