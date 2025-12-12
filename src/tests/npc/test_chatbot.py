# test_chatbot.py

from dotenv import load_dotenv
load_dotenv() 
import pytest
from deepeval import assert_test
# 수정된 부분: LLMTestCaseParams 위치 변경
from deepeval.test_case import LLMTestCase, LLMTestCaseParams 
from deepeval.metrics import GEval


# 1. 평가 기준(채점표) 만들기
# "답변이 무례해야 통과"라는 기준
rude_metric = GEval(
    name="Rude Persona",
    criteria="The answer must be rude and sarcastic.",
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT]
)

# 2. 테스트 함수 만들기 (함수 이름도 test_ 로 시작해야 함)
def test_rude_npc():
    # 상황: NPC에게 질문을 던짐
    input_query = "안녕? 반가워"
    
    # 실제로는 여기서 내 챗봇을 호출해서 답변을 받아야 함
    # actual_response = my_chatbot.chat(input_query)
    actual_response = "뭐가 반가워? 저리 가."  # (가정: 챗봇이 이렇게 답했다고 치자)
    
    # 평가 케이스 포장
    test_case = LLMTestCase(
        input=input_query,
        actual_output=actual_response
    )
    
    # 3. 채점 실행 (DeepEval이 채점하고 점수가 낮으면 에러를 냄)
    assert_test(test_case, [rude_metric])
