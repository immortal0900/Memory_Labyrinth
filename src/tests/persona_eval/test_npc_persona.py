"""
NPC 페르소나 평가 테스트

DeepEval을 사용하여 NPC의 페르소나 일관성, 역할 몰입도, 지식 경계를 평가합니다.
"""

import pytest
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from .custom_metrics import ALL_METRICS
from .npc_client import NPCClient


# ============================================
# 레티아 테스트
# ============================================

@pytest.mark.asyncio
async def test_letia_persona(npc_client, letia_questions, letia_persona):
    """레티아 페르소나 일관성 테스트"""
    
    player_id = "test_letia_player"
    heroine_id = 1
    
    # 로그인
    await npc_client.login(player_id)
    
    test_cases = []
    
    for question in letia_questions:
        if question["type"] == "multi_turn_memory":
            # 멀티턴 테스트
            turns = question["turns"]
            
            # 첫 번째 턴 (정보 제공)
            await npc_client.chat_heroine(player_id, heroine_id, turns[0]["content"])
            
            # 두 번째 턴 (기억 확인)
            response = await npc_client.chat_heroine(player_id, heroine_id, turns[1]["content"])
            
            test_cases.append(LLMTestCase(
                input=f"{turns[0]['content']} -> {turns[1]['content']}",
                actual_output=response["text"],
                context=[letia_persona, question["expected_behavior"]]
            ))
        else:
            # 단일 턴 테스트
            response = await npc_client.chat_heroine(
                player_id,
                heroine_id,
                question["turns"][0]["content"]
            )
            
            test_cases.append(LLMTestCase(
                input=question["turns"][0]["content"],
                actual_output=response["text"],
                context=[letia_persona, question["expected_behavior"]]
            ))
    
    # 평가 실행
    evaluate(test_cases, metrics=ALL_METRICS, print_results=True)


# ============================================
# 루파메스 테스트
# ============================================

@pytest.mark.asyncio
async def test_lupames_persona(npc_client, lupames_questions, lupames_persona):
    """루파메스 페르소나 일관성 테스트"""
    
    player_id = "test_lupames_player"
    heroine_id = 2
    
    # 로그인
    await npc_client.login(player_id)
    
    test_cases = []
    
    for question in lupames_questions:
        if question["type"] == "multi_turn_memory":
            # 멀티턴 테스트
            turns = question["turns"]
            
            # 첫 번째 턴 (정보 제공)
            await npc_client.chat_heroine(player_id, heroine_id, turns[0]["content"])
            
            # 두 번째 턴 (기억 확인)
            response = await npc_client.chat_heroine(player_id, heroine_id, turns[1]["content"])
            
            test_cases.append(LLMTestCase(
                input=f"{turns[0]['content']} -> {turns[1]['content']}",
                actual_output=response["text"],
                context=[lupames_persona, question["expected_behavior"]]
            ))
        else:
            # 단일 턴 테스트
            response = await npc_client.chat_heroine(
                player_id,
                heroine_id,
                question["turns"][0]["content"]
            )
            
            test_cases.append(LLMTestCase(
                input=question["turns"][0]["content"],
                actual_output=response["text"],
                context=[lupames_persona, question["expected_behavior"]]
            ))
    
    # 평가 실행
    evaluate(test_cases, metrics=ALL_METRICS, print_results=True)


# ============================================
# 로코 테스트
# ============================================

@pytest.mark.asyncio
async def test_roco_persona(npc_client, roco_questions, roco_persona):
    """로코 페르소나 일관성 테스트"""
    
    player_id = "test_roco_player"
    heroine_id = 3
    
    # 로그인
    await npc_client.login(player_id)
    
    test_cases = []
    
    for question in roco_questions:
        if question["type"] == "multi_turn_memory":
            # 멀티턴 테스트
            turns = question["turns"]
            
            # 첫 번째 턴 (정보 제공)
            await npc_client.chat_heroine(player_id, heroine_id, turns[0]["content"])
            
            # 두 번째 턴 (기억 확인)
            response = await npc_client.chat_heroine(player_id, heroine_id, turns[1]["content"])
            
            test_cases.append(LLMTestCase(
                input=f"{turns[0]['content']} -> {turns[1]['content']}",
                actual_output=response["text"],
                context=[roco_persona, question["expected_behavior"]]
            ))
        else:
            # 단일 턴 테스트
            response = await npc_client.chat_heroine(
                player_id,
                heroine_id,
                question["turns"][0]["content"]
            )
            
            test_cases.append(LLMTestCase(
                input=question["turns"][0]["content"],
                actual_output=response["text"],
                context=[roco_persona, question["expected_behavior"]]
            ))
    
    # 평가 실행
    evaluate(test_cases, metrics=ALL_METRICS, print_results=True)


# ============================================
# 사트라 테스트
# ============================================

@pytest.mark.asyncio
async def test_satra_persona(npc_client, satra_questions, satra_persona):
    """사트라 페르소나 일관성 테스트"""
    
    player_id = "test_satra_player"
    
    # 로그인
    await npc_client.login(player_id, scenario_level=1)
    
    test_cases = []
    
    for question in satra_questions:
        if question["type"] == "multi_turn_memory":
            # 멀티턴 테스트
            turns = question["turns"]
            
            # 첫 번째 턴 (정보 제공)
            await npc_client.chat_sage(player_id, turns[0]["content"])
            
            # 두 번째 턴 (기억 확인)
            response = await npc_client.chat_sage(player_id, turns[1]["content"])
            
            test_cases.append(LLMTestCase(
                input=f"{turns[0]['content']} -> {turns[1]['content']}",
                actual_output=response["text"],
                context=[satra_persona, question["expected_behavior"]]
            ))
        else:
            # 단일 턴 테스트
            response = await npc_client.chat_sage(
                player_id,
                question["turns"][0]["content"]
            )
            
            test_cases.append(LLMTestCase(
                input=question["turns"][0]["content"],
                actual_output=response["text"],
                context=[satra_persona, question["expected_behavior"]]
            ))
    
    # 평가 실행
    evaluate(test_cases, metrics=ALL_METRICS, print_results=True)
